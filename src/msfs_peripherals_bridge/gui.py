"""Tkinter control panel for the bridge, the mapper and a live variable monitor.

Layout: a profile selector on top (always visible, above the tabs), a ttk.Notebook
with tabs, and a small status bar with lamps pinned to the bottom edge.

* **Connection** tab — start/stop the bridge (supervisor → bridge.py → Proton) and
  the mapper, plus a one-click "stop everything". Buttons carry a tooltip with the
  actual command they run.
* **Statistik** tab — assemble a live value list: pick variables from a searchable,
  type-filterable catalog (popup) and read their current values (snapshot).
* **Mapper** tab — device viewer + inline binding editor: every catalog device with
  its live-connected status and, per device, the bindings/outputs the selected profile
  assigns it. Select a binding to edit it in the panel below (name/source/action/
  transform); Übernehmen writes back through the comment-preserving profile_writer.
  Discovery is lazy (first time the tab is shown).

Launch:  uv run python -m msfs_peripherals_bridge.gui   (or the `msfs-gui` script)

Process model: each managed process runs in its OWN process group
(``start_new_session=True``) and is stopped with ``killpg`` — the whole chain goes
down cleanly and we never hit the pkill-hits-its-own-shell trap. Status checks
never open a client connection (the bridge is single-client): the Bridge lamp
reads the kernel socket table, MSFS/Mapper come from a ``/proc`` scan.
"""

from __future__ import annotations

import contextlib
import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

from .config import gui_settings_file, profiles_dir, project_root

BRIDGE_PORT = 7842
_POLL_MS = 1000  # status refresh cadence
PANEL_MAX = 20  # max grid dimension (cols/rows) for the detachable value panel


# --------------------------------------------------------------------------- #
# persisted GUI state (Statistik var selection)
# --------------------------------------------------------------------------- #
def load_gui_settings(path: Path | None = None) -> dict:
    """Read the whole GUI settings dict; missing/malformed yields ``{}``."""
    p = path or gui_settings_file()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_gui_settings(data: dict, path: Path | None = None) -> None:
    """Write the whole GUI settings dict; failures are non-fatal (best-effort)."""
    p = path or gui_settings_file()
    with contextlib.suppress(OSError):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _clean_vars(items: object) -> list[dict[str, str]]:
    """Keep only well-formed ``{kind, name, unit}`` entries (unit defaults to "")."""
    out: list[dict[str, str]] = []
    if isinstance(items, list):
        for it in items:
            if isinstance(it, dict) and isinstance(it.get("kind"), str) \
                    and isinstance(it.get("name"), str):
                unit = it.get("unit")
                out.append({
                    "kind": it["kind"], "name": it["name"],
                    "unit": unit if isinstance(unit, str) else "",
                })
    return out


def load_statistik_selection(path: Path | None = None) -> list[dict[str, str]]:
    """Restore the saved Statistik var list as ``{kind, name, unit}`` dicts."""
    return _clean_vars(load_gui_settings(path).get("statistik_vars"))


def save_statistik_selection(vars_: list[dict[str, str]], path: Path | None = None) -> None:
    """Persist the Statistik var list, preserving the rest of the settings file."""
    data = load_gui_settings(path)
    data["statistik_vars"] = vars_
    save_gui_settings(data, path)


def load_panel_state(path: Path | None = None) -> dict:
    """Restore the panel: grid size, window geometry and tiles {kind,name,unit,col,row}."""
    st = load_gui_settings(path).get("panel")
    st = st if isinstance(st, dict) else {}
    raw = st.get("tiles")
    raw = raw if isinstance(raw, list) else []
    tiles: list[dict] = []
    for v in _clean_vars(raw):
        src = next(
            (it for it in raw if it.get("name") == v["name"] and it.get("kind") == v["kind"]),
            {},
        )
        col, row = src.get("col"), src.get("row")
        tiles.append({
            **v,
            "col": col if isinstance(col, int) and not isinstance(col, bool) else 0,
            "row": row if isinstance(row, int) and not isinstance(row, bool) else 0,
        })
    cols, rows = st.get("cols"), st.get("rows")
    geom, vis = st.get("geometry"), st.get("visible")
    return {
        "cols": cols if isinstance(cols, int) and 1 <= cols <= PANEL_MAX else 4,
        "rows": rows if isinstance(rows, int) and 1 <= rows <= PANEL_MAX else 3,
        "geometry": geom if isinstance(geom, str) else "",
        "visible": vis if isinstance(vis, bool) else False,
        "tiles": tiles,
    }


def save_panel_state(state: dict, path: Path | None = None) -> None:
    """Persist the panel state, preserving the rest of the settings file."""
    data = load_gui_settings(path)
    data["panel"] = state
    save_gui_settings(data, path)


def _wire_name(kind: str, name: str) -> str | None:
    """The name to subscribe to: A: bare, L: prefixed, K: events carry no value."""
    if kind == "L:":
        return "L:" + name
    if kind == "A:":
        return name
    return None


# --- pure grid helpers (unit-tested without a display) --------------------- #
def _panel_first_free(occupied, cols, rows):
    """First free (col, row) scanning row-major, or None if the grid is full."""
    for r in range(rows):
        for c in range(cols):
            if (c, r) not in occupied:
                return (c, r)
    return None


def _panel_cell_from_point(px, py, cols, rows, cellw, cellh):
    """Clamp a pixel point to a grid (col, row)."""
    col = min(cols - 1, max(0, int(px // cellw))) if cellw > 0 else 0
    row = min(rows - 1, max(0, int(py // cellh))) if cellh > 0 else 0
    return (col, row)


def _panel_fit_tiles(tiles, cols, rows):
    """Keep in-range unique tiles; relocate the rest to free cells (mutates col/row).

    Returns the tiles that did not fit (grid smaller than the tile count).
    """
    occupied: set = set()
    overflow: list = []
    for t in tiles:
        cell = (t.get("col", 0), t.get("row", 0))
        if 0 <= cell[0] < cols and 0 <= cell[1] < rows and cell not in occupied:
            occupied.add(cell)
        else:
            overflow.append(t)
    dropped: list = []
    for t in overflow:
        cell = _panel_first_free(occupied, cols, rows)
        if cell is None:
            dropped.append(t)
        else:
            t["col"], t["row"] = cell
            occupied.add(cell)
    return dropped


# --------------------------------------------------------------------------- #
# process management
# --------------------------------------------------------------------------- #
def _iter_proc_cmdlines():
    """Yield (pid, cmdline_str) for every readable process. Dependency-free."""
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        pid = int(entry)
        if pid == os.getpid():
            continue
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as fh:
                raw = fh.read()
        except OSError:
            continue
        if raw:
            yield pid, raw.replace(b"\x00", b" ").decode("utf-8", "replace")


def _sweep(substr: str) -> int:
    """SIGTERM every process whose cmdline contains ``substr`` (best-effort)."""
    n = 0
    for pid, cmd in _iter_proc_cmdlines():
        if substr in cmd:
            try:
                os.kill(pid, signal.SIGTERM)
                n += 1
            except OSError:
                pass
    return n


# Any mapper process, however it was launched: the ``python -m ... run`` form the
# GUI uses, or the ``msfs-bridge run`` console script from a terminal. The bridge
# is single-client, so a stray/duplicate mapper silently steals the slot and
# commands stop getting through — we make sure exactly one ever runs.
_MAPPER_MATCHES = ("peripherals_bridge run", "msfs-bridge run")


def _sweep_mapper() -> int:
    """SIGTERM every mapper process, whichever way it was started."""
    return sum(_sweep(m) for m in _MAPPER_MATCHES)


def _port_listening(port: int) -> bool:
    """True if something is LISTENing on ``port`` locally — WITHOUT opening a
    connection. The bridge is single-client, so a once-a-second status probe must
    NOT connect (that would burn the client slot and fight the mapper, showing up
    as "Linux app connected / Client connection ended" churn). We read the kernel
    socket table instead: state 0A = TCP_LISTEN, address is hex ``IP:PORT``."""
    hexport = f"{port:04X}".upper()
    for path in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            with open(path) as fh:
                next(fh, None)  # skip header
                for line in fh:
                    cols = line.split()
                    if len(cols) < 4 or cols[3] != "0A":
                        continue
                    if cols[1].rsplit(":", 1)[-1].upper() == hexport:
                        return True
        except OSError:
            continue
    return False


def _msfs_running() -> bool:
    return any("FlightSimulator.exe" in cmd for _, cmd in _iter_proc_cmdlines())


def _discover_present(catalog) -> set[str] | None:
    """Device ids detected as attached now, or ``None`` if discovery can't run.

    Runs both hidraw (Saitek panels) and evdev (axis hardware) discovery, each
    guarded: python-evdev is optional and Linux-only, so its absence just means
    those devices read as unknown rather than crashing the viewer. Returns
    ``None`` only when neither reader could even attempt a scan.
    """
    present: set[str] = set()
    ran = False
    with contextlib.suppress(Exception):
        from .devices import hidraw_reader

        present |= set(hidraw_reader.discover(catalog))
        ran = True
    with contextlib.suppress(Exception):
        from .devices import evdev_reader

        present |= set(evdev_reader.discover(catalog))
        ran = True
    return present if ran else None


class ProcessController:
    """Owns one long-running subprocess, started in its own process group."""

    def __init__(self, name: str, argv: list[str], cwd: Path, log_path: Path | None = None):
        self.name = name
        self.argv = argv
        self.cwd = cwd
        self.log_path = log_path
        self.proc: subprocess.Popen | None = None
        self._pgid: int | None = None
        self._kill_deadline: float | None = None

    def start(self) -> None:
        if self.is_running():
            return
        if self.log_path is not None:
            stdout = open(self.log_path, "a", encoding="utf-8")  # noqa: SIM115 (child owns it)
        else:
            stdout = subprocess.DEVNULL
        self.proc = subprocess.Popen(
            self.argv, cwd=str(self.cwd), stdout=stdout,
            stderr=subprocess.STDOUT, start_new_session=True,
        )
        self._pgid = os.getpgid(self.proc.pid)
        self._kill_deadline = None

    def is_running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def stop(self) -> None:
        """Signal the whole process group; SIGKILL escalation happens in poll()."""
        if not self.is_running():
            self.proc = None
            return
        if self._pgid is not None:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(self._pgid, signal.SIGTERM)
        self._kill_deadline = time.time() + 4.0

    def poll(self) -> None:
        """Call periodically: escalate a pending stop and reap a finished child."""
        if (
            self._kill_deadline is not None
            and self.is_running()
            and time.time() > self._kill_deadline
            and self._pgid is not None
        ):
            with contextlib.suppress(ProcessLookupError):
                os.killpg(self._pgid, signal.SIGKILL)
            self._kill_deadline = None
        if not self.is_running():
            self.proc = None
            self._kill_deadline = None


# --------------------------------------------------------------------------- #
# GUI helpers (tooltips, value snapshot, variable picker)
# --------------------------------------------------------------------------- #
def _list_profiles(root: Path) -> list[str]:
    try:
        return sorted(p.stem for p in profiles_dir(root).glob("*.yaml"))
    except OSError:
        return ["piper_arrow"]


def _fmt_value(value: object) -> str:
    """Compact display of a streamed value (round floats, pass the rest through)."""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def _attach_tooltip(widget, text) -> None:
    """Show ``text`` (a str, or a zero-arg callable returning str) on hover."""
    import tkinter as tk

    state: dict[str, object] = {"tip": None}

    def show(_event=None):
        if state["tip"] is not None:
            return
        msg = text() if callable(text) else text
        tip = tk.Toplevel(widget)
        tip.wm_overrideredirect(True)
        tip.wm_geometry(
            f"+{widget.winfo_rootx() + 14}+{widget.winfo_rooty() + widget.winfo_height() + 4}"
        )
        tk.Label(
            tip, text=msg, justify="left", background="#ffffe0", relief="solid",
            borderwidth=1, font=("TkDefaultFont", 8), padx=6, pady=3,
        ).pack()
        state["tip"] = tip

    def hide(_event=None):
        tip = state["tip"]
        if tip is not None:
            tip.destroy()
            state["tip"] = None

    widget.bind("<Enter>", show)
    widget.bind("<Leave>", hide)


class _ValueMonitor:
    """Background bridge subscriber for the Statistik tab.

    A daemon thread keeps a live ``{wire_name: value}`` map for the current
    variable list, subscribing over the bridge and reconnecting when the list
    changes. It connects whenever the bridge port is listening — once the bridge
    is multi-client this coexists with the mapper. Thread-safe; poll ``values()``
    from the Tk loop, set the watch list with ``set_names()``.
    """

    def __init__(self, *, host: str = "127.0.0.1", port: int = BRIDGE_PORT):
        self._host, self._port = host, port
        self._lock = threading.Lock()
        self._names: list[str] = []
        self._values: dict[str, object] = {}
        self._gen = 0  # bumped on a name change -> the reader reconnects
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="value-monitor", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def set_names(self, names) -> None:
        names = list(names)
        with self._lock:
            if names != self._names:
                self._names = names
                self._gen += 1
                self._values = {k: v for k, v in self._values.items() if k in names}

    def values(self) -> dict[str, object]:
        with self._lock:
            return dict(self._values)

    def _run(self) -> None:
        import json
        import socket

        while not self._stop.is_set():
            with self._lock:
                names, gen = list(self._names), self._gen
            if not names or not _port_listening(self._port):
                self._stop.wait(0.5)
                continue
            try:
                sock = socket.create_connection((self._host, self._port), timeout=2)
            except OSError:
                self._stop.wait(1.0)
                continue
            try:
                sock.settimeout(0.5)
                for name in names:
                    sock.sendall((json.dumps({"op": "subscribe", "name": name}) + "\n").encode())
                buf = b""
                while not self._stop.is_set():
                    with self._lock:
                        if gen != self._gen:
                            break  # list changed -> reconnect with the new set
                    try:
                        chunk = sock.recv(65536)
                    except TimeoutError:
                        continue
                    except OSError:
                        break
                    if not chunk:
                        break
                    buf += chunk
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        try:
                            msg = json.loads(line)
                        except (json.JSONDecodeError, ValueError):
                            continue
                        if msg.get("op") == "state":
                            with self._lock:
                                self._values[msg.get("name")] = msg.get("value")
            finally:
                with contextlib.suppress(OSError):
                    sock.close()


def _open_var_picker(parent, catalog, on_add) -> None:
    """Popup: filter the catalog by kind + name search; add picked vars via on_add."""
    import tkinter as tk
    from tkinter import ttk

    from .gui_catalog import KIND_EVENT, KIND_LVAR, KIND_SIMVAR, filter_catalog

    kinds = {"Alle": None, "A: SimVar": KIND_SIMVAR, "K: Event": KIND_EVENT, "L: LVar": KIND_LVAR}

    top = tk.Toplevel(parent)
    top.title("Variable auswählen")
    top.geometry("480x440")
    top.columnconfigure(0, weight=1)
    top.rowconfigure(1, weight=1)

    filt = ttk.Frame(top, padding=8)
    filt.grid(row=0, column=0, sticky="ew")
    ttk.Label(filt, text="Typ:").pack(side="left")
    kind_var = tk.StringVar(value="Alle")
    ttk.Combobox(filt, textvariable=kind_var, values=list(kinds), state="readonly",
                 width=12).pack(side="left", padx=(4, 10))
    ttk.Label(filt, text="Suche:").pack(side="left")
    query_var = tk.StringVar()
    ttk.Entry(filt, textvariable=query_var).pack(side="left", fill="x", expand=True, padx=4)

    body = ttk.Frame(top, padding=(8, 0))
    body.grid(row=1, column=0, sticky="nsew")
    body.rowconfigure(0, weight=1)
    body.columnconfigure(0, weight=1)
    lb = tk.Listbox(body, activestyle="dotbox")
    lb.grid(row=0, column=0, sticky="nsew")
    sb = ttk.Scrollbar(body, orient="vertical", command=lb.yview)
    sb.grid(row=0, column=1, sticky="ns")
    lb.config(yscrollcommand=sb.set)

    shown: list = []

    def add_selected(_event=None):
        for i in lb.curselection():
            on_add(shown[i])

    foot = ttk.Frame(top, padding=8)
    foot.grid(row=2, column=0, sticky="ew")
    count = ttk.Label(foot, text="")
    count.pack(side="left")
    ttk.Button(foot, text="Schließen", command=top.destroy).pack(side="right")
    ttk.Button(foot, text="Hinzufügen", command=add_selected).pack(side="right", padx=6)

    def refresh(*_):
        vs = filter_catalog(catalog, kind=kinds[kind_var.get()], query=query_var.get())
        shown.clear()
        shown.extend(vs)
        lb.delete(0, "end")
        for v in vs:
            lb.insert("end", v.label)
        count.config(text=f"{len(vs)} Treffer")

    kind_var.trace_add("write", refresh)
    query_var.trace_add("write", refresh)
    lb.bind("<Double-Button-1>", add_selected)
    refresh()


class _PanelWindow:
    """Detachable, resizable window: a grid of live value tiles.

    Tiles snap to grid cells; dropping one on an occupied cell swaps the two.
    The grid size (up to ``PANEL_MAX``x``PANEL_MAX``) is set via the toolbar. The
    grid dimensions, window geometry and tile placement persist across sessions.
    Values come from the shared ``_ValueMonitor`` (the caller unions our
    subscription with the Statistik list via ``on_change``).
    """

    def __init__(self, master, monitor, on_change, on_close) -> None:
        import tkinter as tk

        self._tk = tk
        self.monitor = monitor
        self._on_change = on_change
        self._on_close = on_close
        self.tiles: dict[str, dict] = {}
        self._drag: dict = {"key": None, "dx": 0.0, "dy": 0.0}
        self._mv = (0, 0)
        self._rsz = (0, 0, 0, 0)
        self._after: str | None = None

        st = load_panel_state()
        self.cols, self.rows = st["cols"], st["rows"]

        self.win = tk.Toplevel(master)
        self.win.overrideredirect(True)  # borderless: no title bar / close button
        self.win.minsize(160, 80)
        with contextlib.suppress(tk.TclError):
            self.win.geometry(st["geometry"] or "440x260+140+140")

        # The top strip is the grid toolbar AND the drag handle for moving the
        # (border-less) window; the spinboxes stay clickable, the rest drags.
        bar = tk.Frame(self.win, background="#37474f")
        bar.pack(side="top", fill="x")
        handle = tk.Label(bar, text="::", background="#37474f", foreground="#b0bec5",
                          font=("TkDefaultFont", 10, "bold"), cursor="fleur")
        handle.pack(side="left", padx=(6, 4))
        tk.Label(bar, text="Raster", background="#37474f",
                 foreground="#eceff1").pack(side="left")
        self._cols_var = tk.IntVar(value=self.cols)
        self._rows_var = tk.IntVar(value=self.rows)
        for var in (self._cols_var, self._rows_var):
            sp = tk.Spinbox(bar, from_=1, to=PANEL_MAX, width=3, textvariable=var,
                            command=self._grid_changed)
            sp.pack(side="left", padx=(4, 0))
            sp.bind("<Return>", lambda _e: self._grid_changed())
            sp.bind("<FocusOut>", lambda _e: self._grid_changed())
            if var is self._cols_var:
                tk.Label(bar, text="x", background="#37474f",
                         foreground="#eceff1").pack(side="left", padx=2)
        hint = tk.Label(bar, background="#37474f", foreground="#90a4ae",
                        text="  ziehen = bewegen · Kacheln einrasten/tauschen · Rechtsklick = weg")
        hint.pack(side="left", padx=6)
        for wgt in (bar, handle, hint):
            wgt.bind("<ButtonPress-1>", self._move_start)
            wgt.bind("<B1-Motion>", self._move_drag)
            wgt.bind("<ButtonRelease-1>", self._move_end)

        self.canvas = tk.Canvas(self.win, highlightthickness=0, background="#cfd8dc")
        self.canvas.pack(side="top", fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _e: self._relayout())

        # Resize grip pinned to the bottom-right corner (overlays the canvas).
        grip = tk.Label(self.win, text="/", background="#cfd8dc", foreground="#546e7a",
                        font=("TkDefaultFont", 12, "bold"), cursor="bottom_right_corner")
        grip.place(relx=1.0, rely=1.0, anchor="se")
        grip.bind("<ButtonPress-1>", self._resize_start)
        grip.bind("<B1-Motion>", self._resize_move)
        grip.bind("<ButtonRelease-1>", self._resize_end)

        for t in st["tiles"]:
            key = f"{t['kind']}\t{t['name']}"
            self.tiles.setdefault(key, {**t, "item": None, "value": None})
        _panel_fit_tiles(list(self.tiles.values()), self.cols, self.rows)
        for key, t in self.tiles.items():
            self._create_item(key, t)
        self.win.lift()
        self._relayout()
        self._tick()

    # --- API used by run() ------------------------------------------------- #
    def alive(self) -> bool:
        try:
            return bool(self.win.winfo_exists())
        except self._tk.TclError:
            return False

    def __contains__(self, key) -> bool:
        return key in self.tiles

    def wires(self) -> list[str]:
        return [w for t in self.tiles.values()
                if (w := _wire_name(t["kind"], t["name"])) is not None]

    def add(self, kind: str, name: str, unit: str) -> bool:
        """Place a new tile in the first free cell; False if duplicate or grid full."""
        key = f"{kind}\t{name}"
        if key in self.tiles:
            return False
        occupied = {(t["col"], t["row"]) for t in self.tiles.values()}
        cell = _panel_first_free(occupied, self.cols, self.rows)
        if cell is None:
            return False
        t = {"kind": kind, "name": name, "unit": unit,
             "col": cell[0], "row": cell[1], "item": None, "value": None}
        self.tiles[key] = t
        self._create_item(key, t)
        self._place(t)
        self._save()
        return True

    def destroy(self) -> None:
        self._close()

    # --- window move / resize (no WM decorations) -------------------------- #
    def _move_start(self, ev) -> None:
        self._mv = (ev.x_root - self.win.winfo_x(), ev.y_root - self.win.winfo_y())

    def _move_drag(self, ev) -> None:
        self.win.geometry(f"+{ev.x_root - self._mv[0]}+{ev.y_root - self._mv[1]}")

    def _move_end(self, _ev) -> None:
        self._save()

    def _resize_start(self, ev) -> None:
        self._rsz = (ev.x_root, ev.y_root, self.win.winfo_width(), self.win.winfo_height())

    def _resize_move(self, ev) -> None:
        x0, y0, w0, h0 = self._rsz
        self.win.geometry(f"{max(160, w0 + ev.x_root - x0)}x{max(80, h0 + ev.y_root - y0)}")

    def _resize_end(self, _ev) -> None:
        self._relayout()
        self._save()

    # --- internals --------------------------------------------------------- #
    def _create_item(self, key, t) -> None:
        # Compact two-line layout (name; value + unit) so a tile can shrink to
        # roughly half the old height before its text is clipped.
        tk = self._tk
        fr = tk.Frame(self.canvas, bd=1, relief="raised", background="#ffffff",
                      cursor="fleur")
        tk.Label(fr, text=f"{t['kind']} {t['name']}", font=("TkDefaultFont", 8),
                 foreground="#607d8b", background="#ffffff").pack(anchor="w", padx=5, pady=(1, 0))
        row = tk.Frame(fr, background="#ffffff")
        row.pack(anchor="w", padx=5, pady=(0, 1))
        val = tk.Label(row, text="—", font=("TkDefaultFont", 13, "bold"), background="#ffffff")
        val.pack(side="left")
        tk.Label(row, text=t["unit"], font=("TkDefaultFont", 8), foreground="#90a4ae",
                 background="#ffffff").pack(side="left", padx=(4, 0), pady=(3, 0))
        t["item"] = self.canvas.create_window(0, 0, window=fr, anchor="nw")
        t["value"] = val
        for wgt in (fr, *fr.winfo_children(), *row.winfo_children()):
            wgt.bind("<ButtonPress-1>", lambda e, k=key: self._drag_start(e, k))
            wgt.bind("<B1-Motion>", lambda e, k=key: self._drag_move(e, k))
            wgt.bind("<ButtonRelease-1>", lambda e, k=key: self._drag_end(e, k))
            wgt.bind("<Button-3>", lambda e, k=key: self._menu(e, k))

    def _cell_size(self):
        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())
        return cw / self.cols, ch / self.rows

    def _canvas_xy(self, ev):
        return (self.canvas.canvasx(ev.x_root - self.canvas.winfo_rootx()),
                self.canvas.canvasy(ev.y_root - self.canvas.winfo_rooty()))

    def _place(self, t) -> None:
        if t["item"] is None:
            return
        cellw, cellh = self._cell_size()
        pad = 3
        self.canvas.coords(t["item"], t["col"] * cellw + pad, t["row"] * cellh + pad)
        self.canvas.itemconfigure(t["item"], width=max(1, int(cellw - 2 * pad)),
                                  height=max(1, int(cellh - 2 * pad)))

    def _draw_grid(self) -> None:
        self.canvas.delete("gridline")
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        cellw, cellh = self._cell_size()
        for c in range(1, self.cols):
            self.canvas.create_line(c * cellw, 0, c * cellw, ch, fill="#b0bec5", tags="gridline")
        for r in range(1, self.rows):
            self.canvas.create_line(0, r * cellh, cw, r * cellh, fill="#b0bec5", tags="gridline")
        self.canvas.tag_lower("gridline")

    def _relayout(self) -> None:
        self._draw_grid()
        for t in self.tiles.values():
            self._place(t)

    def _drag_start(self, ev, key) -> None:
        t = self.tiles.get(key)
        if t is None or t["item"] is None:
            return
        self.canvas.lift(t["item"])
        cx, cy = self._canvas_xy(ev)
        ix, iy = self.canvas.coords(t["item"])
        self._drag.update(key=key, dx=cx - ix, dy=cy - iy)

    def _drag_move(self, ev, key) -> None:
        if self._drag["key"] != key:
            return
        cx, cy = self._canvas_xy(ev)
        self.canvas.coords(self.tiles[key]["item"], cx - self._drag["dx"], cy - self._drag["dy"])

    def _drag_end(self, ev, key) -> None:
        if self._drag["key"] != key:
            return
        self._drag["key"] = None
        t = self.tiles[key]
        cellw, cellh = self._cell_size()
        cx, cy = self._canvas_xy(ev)
        col, row = _panel_cell_from_point(
            cx - self._drag["dx"] + cellw / 2, cy - self._drag["dy"] + cellh / 2,
            self.cols, self.rows, cellw, cellh,
        )
        other = next((o for o in self.tiles.values()
                      if o is not t and o["col"] == col and o["row"] == row), None)
        if other is not None:  # swap
            other["col"], other["row"] = t["col"], t["row"]
            self._place(other)
        t["col"], t["row"] = col, row
        self._place(t)
        self._save()

    def _menu(self, ev, key) -> None:
        menu = self._tk.Menu(self.canvas, tearoff=0)
        menu.add_command(label="Kachel entfernen", command=lambda: self._remove(key))
        menu.tk_popup(ev.x_root, ev.y_root)

    def _remove(self, key) -> None:
        t = self.tiles.pop(key, None)
        if t is not None:
            if t["item"] is not None:
                self.canvas.delete(t["item"])
            self._on_change()
            self._save()

    def _safe_int(self, var, fallback: int) -> int:
        try:
            return int(var.get())
        except (ValueError, self._tk.TclError):
            return fallback

    def _grid_changed(self) -> None:
        cols = max(1, min(PANEL_MAX, self._safe_int(self._cols_var, self.cols)))
        rows = max(1, min(PANEL_MAX, self._safe_int(self._rows_var, self.rows)))
        if cols * rows < len(self.tiles):  # too small to hold all tiles -> revert
            self._cols_var.set(self.cols)
            self._rows_var.set(self.rows)
            return
        self.cols, self.rows = cols, rows
        self._cols_var.set(cols)
        self._rows_var.set(rows)
        _panel_fit_tiles(list(self.tiles.values()), self.cols, self.rows)
        self._relayout()
        self._save()

    def _tick(self) -> None:
        vals = self.monitor.values()
        for t in self.tiles.values():
            if t["value"] is None:
                continue
            w = _wire_name(t["kind"], t["name"])
            t["value"].configure(text=_fmt_value(vals[w]) if w in vals else "—")
        self._after = self.win.after(_POLL_MS, self._tick)

    def _save(self) -> None:
        with contextlib.suppress(self._tk.TclError):
            save_panel_state({
                "cols": self.cols, "rows": self.rows,
                "geometry": self.win.winfo_geometry(),
                # The "visible" flag is owned by run() (show/hide); preserve it.
                "visible": load_panel_state()["visible"],
                "tiles": [{"kind": t["kind"], "name": t["name"], "unit": t["unit"],
                           "col": t["col"], "row": t["row"]} for t in self.tiles.values()],
            })

    def _close(self) -> None:
        if self._after is not None:
            with contextlib.suppress(self._tk.TclError):
                self.win.after_cancel(self._after)
            self._after = None
        self._save()
        with contextlib.suppress(self._tk.TclError):
            self.win.destroy()
        self._on_close()


# --------------------------------------------------------------------------- #
# main window
# --------------------------------------------------------------------------- #
def run() -> None:
    import tkinter as tk
    from tkinter import messagebox, simpledialog, ttk

    from . import gui_catalog

    root_dir = project_root()
    bridge = ProcessController(
        "bridge", ["bash", str(root_dir / "bridge" / "run-bridge.sh")],
        cwd=root_dir, log_path=root_dir / "bridge" / "bridge.log",
    )
    profiles = _list_profiles(root_dir)
    default_profile = (
        "piper_arrow" if "piper_arrow" in profiles
        else profiles[0] if profiles else "piper_arrow"
    )
    catalog = gui_catalog.load_catalog(root_dir / "docs" / "simvars-reference.md")
    monitor = _ValueMonitor()
    monitor.start()

    win = tk.Tk()
    win.title("MSFS Peripherals Bridge — Control")
    win.minsize(620, 460)
    win.columnconfigure(0, weight=1)
    win.rowconfigure(1, weight=1)  # the notebook grows

    # On/off state of the (borderless) Panel window, mirrored by the toolbar
    # toggle button below. The panel is created when on and destroyed when off.
    panel_on = tk.BooleanVar(value=False)

    profile_var = tk.StringVar(value=default_profile)
    mapper = {"ctl": None}  # rebuilt on start so a profile change takes effect

    def make_mapper() -> ProcessController:
        return ProcessController(
            "mapper",
            ["uv", "run", "python", "-m", "msfs_peripherals_bridge", "run",
             "--profile", profile_var.get()],
            cwd=root_dir,
        )

    def mapper_cmd() -> str:
        return "uv run python -m msfs_peripherals_bridge run --profile " + profile_var.get()

    # --- profile row (ABOVE the tabs, always visible) ---------------------- #
    prow = ttk.Frame(win, padding=(10, 10))
    prow.grid(row=0, column=0, sticky="ew")
    ttk.Label(prow, text="Profil:").pack(side="left")
    profile_cb = ttk.Combobox(prow, textvariable=profile_var, values=profiles,
                              state="readonly", width=22)
    profile_cb.pack(side="left", padx=6)

    def _refresh_profiles(select: str | None = None) -> None:
        profile_cb["values"] = _list_profiles(root_dir)
        if select is not None:
            profile_var.set(select)  # fires the trace -> mapper/statistik reload

    def _ask_profile_name(title: str, initial: str = "") -> str | None:
        """Prompt for a filesystem-safe profile stem, or None if cancelled/invalid."""
        raw = simpledialog.askstring(title, "Profilname:", initialvalue=initial, parent=win)
        if raw is None:
            return None
        name = raw.strip()
        if not name or not all(c.isalnum() or c in "_-" for c in name):
            messagebox.showerror("Ungültiger Name",
                                 "Nur Buchstaben, Ziffern, '_' und '-' erlaubt.")
            return None
        if (profiles_dir(root_dir) / f"{name}.yaml").exists():
            messagebox.showerror("Profil existiert", f"'{name}' gibt es schon.")
            return None
        return name

    def _profile_new() -> None:
        name = _ask_profile_name("Neues Profil")
        if name is None:
            return
        profile_writer.dump(profile_writer.new_profile(name),
                            profiles_dir(root_dir) / f"{name}.yaml")
        _refresh_profiles(select=name)

    def _profile_duplicate() -> None:
        src = profiles_dir(root_dir) / f"{profile_var.get()}.yaml"
        if not src.exists():
            messagebox.showerror("Kein Profil", "Aktuelles Profil nicht gefunden.")
            return
        name = _ask_profile_name("Profil duplizieren", initial=f"{profile_var.get()}_kopie")
        if name is None:
            return
        data = profile_writer.load(src)
        data["name"] = name  # keep the file's formatting/comments; just rename
        profile_writer.dump(data, profiles_dir(root_dir) / f"{name}.yaml")
        _refresh_profiles(select=name)

    def _profile_remove() -> None:
        name = profile_var.get()
        names = _list_profiles(root_dir)
        if len(names) <= 1:
            messagebox.showerror("Nicht möglich", "Das letzte Profil kann nicht entfernt werden.")
            return
        if not messagebox.askyesno("Profil entfernen",
                                   f"Profil '{name}' wirklich löschen?\nDas lässt sich nicht "
                                   "rückgängig machen."):
            return
        (profiles_dir(root_dir) / f"{name}.yaml").unlink(missing_ok=True)
        _refresh_profiles(select=next(n for n in names if n != name))

    ttk.Button(prow, text="Neu", width=5, command=_profile_new).pack(side="left")
    ttk.Button(prow, text="Duplizieren", command=_profile_duplicate).pack(side="left", padx=4)
    ttk.Button(prow, text="Entfernen", command=_profile_remove).pack(side="left", padx=(0, 8))
    ttk.Label(prow, text="(gilt für Mapper-Start; Basis für Statistik)",
              foreground="#666").pack(side="left")

    nb = ttk.Notebook(win)
    nb.grid(row=1, column=0, sticky="nsew", padx=10)

    # ===== Connection tab ================================================== #
    conn = ttk.Frame(nb, padding=10)
    nb.add(conn, text="Connection")
    for c in range(2):
        conn.columnconfigure(c, weight=1)

    def start_bridge():
        # Don't double-start: if 7842 already LISTENs (bridge up from a terminal
        # or an earlier run) a second supervisor's bridge.py just fails to bind
        # the port and crash-loops.
        if _port_listening(BRIDGE_PORT):
            return
        bridge.start()

    def stop_bridge():
        bridge.stop()
        _sweep("bridge/bridge.py")      # mop up any escaped Proton child
        _sweep("bridge/run-bridge.sh")  # and the supervisor if started elsewhere

    def start_mapper():
        # Single-client bridge: sweep any existing mapper (ours or a stray) first.
        _sweep_mapper()
        mapper["ctl"] = make_mapper()
        mapper["ctl"].start()

    def stop_mapper():
        if mapper["ctl"] is not None:
            mapper["ctl"].stop()
        _sweep_mapper()  # also catch strays this GUI didn't start

    def stop_all():
        stop_mapper()
        stop_bridge()

    b_bs = ttk.Button(conn, text="Bridge starten", command=start_bridge)
    b_bx = ttk.Button(conn, text="Bridge stoppen", command=stop_bridge)
    b_ms = ttk.Button(conn, text="Mapper starten", command=start_mapper)
    b_mx = ttk.Button(conn, text="Mapper stoppen", command=stop_mapper)
    b_all = ttk.Button(conn, text="Alles stoppen (Aufräumen)", command=stop_all)
    b_bs.grid(row=0, column=0, sticky="ew", padx=3, pady=3)
    b_bx.grid(row=0, column=1, sticky="ew", padx=3, pady=3)
    b_ms.grid(row=1, column=0, sticky="ew", padx=3, pady=3)
    b_mx.grid(row=1, column=1, sticky="ew", padx=3, pady=3)
    b_all.grid(row=2, column=0, columnspan=2, sticky="ew", padx=3, pady=(6, 3))

    _attach_tooltip(b_bs, "bash bridge/run-bridge.sh   (Supervisor → bridge.py → Proton)")
    _attach_tooltip(b_bx, "killpg SIGTERM + sweep 'bridge/bridge.py' / 'bridge/run-bridge.sh'")
    _attach_tooltip(b_ms, mapper_cmd)  # dynamic: reflects the selected profile
    _attach_tooltip(b_mx, "killpg SIGTERM (Mapper-Prozessgruppe) + sweep 'peripherals_bridge run'")
    _attach_tooltip(b_all, "stop_mapper() + stop_bridge() — alle Strays wegräumen")

    ttk.Label(conn, text="Bridge ist single-client — Mapper ODER ein Tool.",
              foreground="#666").grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 0))

    # ===== Statistik tab =================================================== #
    stab = ttk.Frame(nb, padding=10)
    nb.add(stab, text="Statistik")
    stab.rowconfigure(1, weight=1)
    stab.columnconfigure(0, weight=1)

    ttk.Label(stab, text="Live-Wertliste — Variablen zum Beobachten zusammenstellen:"
              ).grid(row=0, column=0, columnspan=4, sticky="w")

    tree = ttk.Treeview(stab, columns=("kind", "name", "value", "unit"),
                        show="headings", height=10)
    for col, head, w, anchor in (
        ("kind", "Typ", 44, "center"), ("name", "Variable", 260, "w"),
        ("value", "Wert", 90, "center"), ("unit", "Einheit", 74, "center"),
    ):
        tree.heading(col, text=head)
        tree.column(col, width=w, anchor=anchor)
    tree.grid(row=1, column=0, columnspan=3, sticky="nsew", pady=6)
    tsb = ttk.Scrollbar(stab, orient="vertical", command=tree.yview)
    tsb.grid(row=1, column=3, sticky="ns", pady=6)
    tree.config(yscrollcommand=tsb.set)

    # The detachable Panel window (opened on demand) shares this monitor; the
    # subscription is the union of the Statistik list and the open panel's tiles.
    panel_ref: dict = {"win": None}

    def _statistik_shown() -> bool:
        """True only while the Statistik tab is actually on screen (its tab is up
        and the window isn't minimized). Every subscribed var is a live SimConnect
        read on the shared bridge that competes with the mapper's real-time axis
        writes, so we poll the Statistik list only when the user can see it — not
        while flying with the window in the background."""
        try:
            return str(nb.select()) == str(stab) and win.state() != "iconic"
        except tk.TclError:
            return False

    def _resubscribe():
        # Subscribe only to what's visible: the Statistik list while its tab is
        # shown, plus the detached panel's tiles while it's open. Anything else
        # would keep the bridge reading vars nobody is looking at.
        wires = []
        if _statistik_shown():
            wires += [
                w for iid in tree.get_children("")
                if (w := _wire_name(tree.set(iid, "kind"), tree.set(iid, "name"))) is not None
            ]
        pw = panel_ref["win"]
        if pw is not None and pw.alive():
            wires += pw.wires()
        monitor.set_names(list(dict.fromkeys(wires)))

    def _persist_selection():
        save_statistik_selection([
            {"kind": tree.set(iid, "kind"), "name": tree.set(iid, "name"),
             "unit": tree.set(iid, "unit")}
            for iid in tree.get_children("")
        ])

    def add_var(v, *, persist=True):
        key = f"{v.kind}\t{v.name}"
        if tree.exists(key):
            return
        tree.insert("", "end", iid=key, values=(v.kind, v.name, "—", v.unit))
        _resubscribe()
        if persist:
            _persist_selection()

    def remove_selected():
        for iid in tree.selection():
            tree.delete(iid)
        _resubscribe()
        _persist_selection()

    def update_values():
        vals = monitor.values()
        for iid in tree.get_children(""):
            kind = tree.set(iid, "kind")
            if kind == "K:":
                tree.set(iid, "value", "(Event)")
                continue
            w = _wire_name(kind, tree.set(iid, "name"))
            tree.set(iid, "value", _fmt_value(vals[w]) if w in vals else "—")

    def _persist_visible(value: bool):
        st = load_panel_state()
        st["visible"] = value
        save_panel_state(st)

    def _panel_closed():
        panel_ref["win"] = None
        panel_on.set(False)
        _resubscribe()

    def _show_panel():
        pw = panel_ref["win"]
        if pw is None or not pw.alive():
            pw = _PanelWindow(win, monitor, on_change=_resubscribe, on_close=_panel_closed)
            panel_ref["win"] = pw
        panel_on.set(True)
        _persist_visible(True)
        _resubscribe()
        return pw

    def _hide_panel():
        pw = panel_ref["win"]
        if pw is not None and pw.alive():
            pw.destroy()  # borderless: destroy is the reliable "close" on any WM
        panel_ref["win"] = None
        panel_on.set(False)
        _persist_visible(False)
        _resubscribe()

    def _toggle_panel():
        _show_panel() if panel_on.get() else _hide_panel()

    def _transfer_to_panel():
        pw = _show_panel()
        full = False
        for iid in tree.selection() or tree.get_children(""):
            kind = tree.set(iid, "kind")
            if kind == "K:":  # events carry no value -> not a tile
                continue
            if f"{kind}\t{tree.set(iid, 'name')}" in pw:
                continue
            if not pw.add(kind, tree.set(iid, "name"), tree.set(iid, "unit")):
                full = True
        _resubscribe()
        if full:
            messagebox.showinfo(
                "Panel voll", "Das Raster ist voll — vergrößere es (Spalten x Zeilen).",
            )

    # Restore the var selection saved from the last session (before wiring buttons).
    for _saved in load_statistik_selection():
        add_var(
            gui_catalog.CatalogVar(
                name=_saved["name"], kind=_saved["kind"],
                unit=_saved.get("unit", ""), category="",
            ),
            persist=False,
        )

    sbtn = ttk.Frame(stab)
    sbtn.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(6, 0))
    b_add = ttk.Button(sbtn, text="Variable hinzufügen …",
                       command=lambda: _open_var_picker(win, catalog, add_var))
    b_rm = ttk.Button(sbtn, text="Entfernen", command=remove_selected)
    b_panel = ttk.Button(sbtn, text="→ Ins Panel", command=lambda: _transfer_to_panel())
    # Toolbutton-styled checkbutton: pressed (on) while the panel is visible.
    b_toggle = ttk.Checkbutton(sbtn, text="Panel", style="Toolbutton",
                               variable=panel_on, command=lambda: _toggle_panel())
    b_add.pack(side="left")
    b_rm.pack(side="left", padx=6)
    b_panel.pack(side="left")
    b_toggle.pack(side="left", padx=6)
    mon_state = ttk.Label(sbtn, text="", foreground="#666")
    mon_state.pack(side="right")
    _attach_tooltip(b_add, "Popup: nach Typ (A:/K:/L:) filtern + Namen suchen")
    _attach_tooltip(b_panel, "Ausgewählte (oder alle) Wert-Zeilen als Kacheln ins Panel legen")
    _attach_tooltip(b_toggle, "Panel-Fenster an/aus (gedrückt = sichtbar)")
    # ===== Mapper tab (device viewer + inline binding editor) ============== #
    from . import gui_mapper, profile_writer
    from .mapping.loader import load_device_catalog, load_profile

    mtab = ttk.Frame(nb, padding=10)
    nb.add(mtab, text="Mapper")
    mtab.rowconfigure(1, weight=1)
    mtab.columnconfigure(0, weight=1)  # device list
    mtab.columnconfigure(1, weight=2)  # detail

    mhdr = ttk.Frame(mtab)
    mhdr.grid(row=0, column=0, columnspan=3, sticky="ew")
    ttk.Label(mhdr, text="Geräte im Profil — was ist worauf gemappt:").pack(side="left")
    m_state = ttk.Label(mhdr, text="", foreground="#666")
    m_state.pack(side="right")

    # left: one row per catalog device (bus, connected?, #bindings, #outputs)
    dev_tree = ttk.Treeview(mtab, columns=("bus", "status", "b", "o"),
                            show="tree headings", height=7, selectmode="browse")
    dev_tree.heading("#0", text="Gerät")
    dev_tree.column("#0", width=170, anchor="w")
    for col, head, w in (("bus", "Bus", 58), ("status", "Status", 96),
                         ("b", "Bind", 42), ("o", "Out", 38)):
        dev_tree.heading(col, text=head)
        dev_tree.column(col, width=w, anchor="center")
    dev_tree.grid(row=1, column=0, sticky="nsew", pady=6, padx=(0, 8))

    # right: bindings + outputs of the selected device
    detail = ttk.Treeview(mtab, columns=("source", "action", "shape"),
                          show="tree headings", height=7)
    detail.heading("#0", text="Name")
    detail.column("#0", width=150, anchor="w")
    for col, head, w in (("source", "Control", 96), ("action", "Aktion", 250),
                         ("shape", "Shaping", 110)):
        detail.heading(col, text=head)
        detail.column(col, width=w, anchor="w")
    detail.grid(row=1, column=1, sticky="nsew", pady=6)
    dsb = ttk.Scrollbar(mtab, orient="vertical", command=detail.yview)
    dsb.grid(row=1, column=2, sticky="ns", pady=6)
    detail.configure(yscrollcommand=dsb.set)

    # discovery is lazy (only when the tab is first shown) so startup stays fast.
    mstate: dict[str, object] = {"present": None, "discovered": False, "profile": None}

    def _current_profile():
        try:
            return load_profile(profiles_dir() / f"{profile_var.get()}.yaml")
        except Exception:
            return None

    def _device_catalog():
        try:
            from . import config as _config

            return load_device_catalog(_config.devices_file())
        except Exception:
            return None

    def _sel(tree):
        s = tree.selection()
        return s[0] if s else None

    # rescan button + inline editor (built below), then the render/edit helpers.
    mbtn = ttk.Frame(mtab)
    mbtn.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(6, 0))
    b_rescan = ttk.Button(mbtn, text="Geräte neu erkennen",
                          command=lambda: _mapper_reload(rediscover=True))
    b_rescan.pack(side="left")
    ttk.Label(mbtn, text="Binding wählen zum Bearbeiten · Achsen zeigen Transform.",
              foreground="#666").pack(side="left", padx=8)
    _attach_tooltip(b_rescan, "evdev + hidraw discovery — welche Geräte hängen jetzt dran")

    # --- inline editor panel ---------------------------------------------- #
    ed = ttk.LabelFrame(mtab, text="Binding bearbeiten", padding=8)
    ed.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(8, 0))
    ed.columnconfigure(1, weight=1)
    ed.columnconfigure(2, weight=1)
    etgt: dict = {"device": None, "index": None, "original_action": None}
    ev = {
        "name": tk.StringVar(), "kind": tk.StringVar(), "code": tk.StringVar(),
        "raw_min": tk.StringVar(), "raw_max": tk.StringVar(),  # shown for axes only
        "action_type": tk.StringVar(),
        "ev_event": tk.StringVar(), "ev_value": tk.StringVar(),
        "sv_simvar": tk.StringVar(), "sv_unit": tk.StringVar(), "sv_invert": tk.BooleanVar(),
        "efv_read": tk.StringVar(), "efv_event": tk.StringVar(), "efv_unit": tk.StringVar(),
        "rpn_code": tk.StringVar(),
        "tf_deadzone": tk.StringVar(), "tf_curve": tk.StringVar(), "tf_expo": tk.StringVar(),
        "tf_invert": tk.BooleanVar(), "tf_out_min": tk.StringVar(), "tf_out_max": tk.StringVar(),
    }

    def _pick_into(var):
        def on_pick(v):  # v is a gui_catalog.CatalogVar
            var.set((v.kind + v.name) if v.kind in ("L:", "V:") else v.name)
        extra = gui_catalog.local_var_catalog(mstate["profile"].local_vars) \
            if mstate["profile"] is not None else []
        _open_var_picker(win, catalog + extra, on_pick)

    # row 0: name
    ttk.Label(ed, text="Name").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=2)
    ttk.Entry(ed, textvariable=ev["name"]).grid(row=0, column=1, columnspan=2, sticky="ew", pady=2)

    # row 1: source (kind + code + learn)
    ttk.Label(ed, text="Quelle").grid(row=1, column=0, sticky="w", padx=(0, 6), pady=2)
    kind_cb = ttk.Combobox(ed, textvariable=ev["kind"], values=list(gui_mapper.SOURCE_KINDS),
                           state="readonly", width=8)
    kind_cb.grid(row=1, column=1, sticky="w", pady=2)
    srcfr = ttk.Frame(ed)
    srcfr.grid(row=1, column=2, sticky="w")
    ttk.Label(srcfr, text="Code").pack(side="left", padx=(0, 4))
    ttk.Entry(srcfr, textvariable=ev["code"], width=8).pack(side="left")
    b_learn = ttk.Button(srcfr, text="Lernen", state="disabled")
    b_learn.pack(side="left", padx=6)
    _attach_tooltip(b_learn, "Hardware-Capture (Knopf drücken → Code) — folgt")

    # row 2: action type + type-specific fields (only the active one shown)
    ttk.Label(ed, text="Aktion").grid(row=2, column=0, sticky="w", padx=(0, 6), pady=2)
    type_cb = ttk.Combobox(ed, textvariable=ev["action_type"], values=list(gui_mapper.ACTION_TYPES),
                           state="readonly", width=14)
    type_cb.grid(row=2, column=1, sticky="w", pady=2)
    afh = ttk.Frame(ed)
    afh.grid(row=2, column=2, sticky="ew", pady=2)
    af: dict = {}
    fe = ttk.Frame(afh)
    ttk.Label(fe, text="Event").pack(side="left")
    ttk.Entry(fe, textvariable=ev["ev_event"], width=22).pack(side="left", padx=4)
    ttk.Button(fe, text="…", width=2, command=lambda: _pick_into(ev["ev_event"])).pack(side="left")
    ttk.Label(fe, text="Wert").pack(side="left", padx=(8, 0))
    ttk.Entry(fe, textvariable=ev["ev_value"], width=6).pack(side="left", padx=4)
    af["event"] = fe
    fs = ttk.Frame(afh)
    ttk.Label(fs, text="SimVar").pack(side="left")
    ttk.Entry(fs, textvariable=ev["sv_simvar"], width=22).pack(side="left", padx=4)
    ttk.Button(fs, text="…", width=2, command=lambda: _pick_into(ev["sv_simvar"])).pack(side="left")
    ttk.Label(fs, text="Unit").pack(side="left", padx=(8, 0))
    ttk.Entry(fs, textvariable=ev["sv_unit"], width=8).pack(side="left", padx=4)
    ttk.Checkbutton(fs, text="invert", variable=ev["sv_invert"]).pack(side="left", padx=6)
    af["simvar"] = fs
    ff = ttk.Frame(afh)
    ttk.Label(ff, text="Read").pack(side="left")
    ttk.Entry(ff, textvariable=ev["efv_read"], width=18).pack(side="left", padx=4)
    ttk.Button(ff, text="…", width=2, command=lambda: _pick_into(ev["efv_read"])).pack(side="left")
    ttk.Label(ff, text="Event").pack(side="left", padx=(8, 0))
    ttk.Entry(ff, textvariable=ev["efv_event"], width=16).pack(side="left", padx=4)
    ttk.Button(ff, text="…", width=2, command=lambda: _pick_into(ev["efv_event"])).pack(side="left")
    af["event_from_var"] = ff
    fr = ttk.Frame(afh)
    ttk.Label(fr, text="RPN").pack(side="left")
    ttk.Entry(fr, textvariable=ev["rpn_code"], width=44).pack(side="left", padx=4)
    af["rpn"] = fr
    fq = ttk.Frame(afh)
    ttk.Label(fq, text="Sequence — inline (noch) nicht editierbar; bleibt beim Speichern erhalten.",
              foreground="#a15").pack(side="left")
    af["sequence"] = fq

    # row 3: axis shaping — input (raw) range + transform pipeline (axis only)
    axfr = ttk.Frame(ed)
    axfr.grid(row=3, column=0, columnspan=3, sticky="ew", pady=2)

    inrow = ttk.Frame(axfr)
    inrow.pack(anchor="w")
    ttk.Label(inrow, text="Eingang (roh)").pack(side="left", padx=(0, 6))
    ttk.Label(inrow, text="min").pack(side="left")
    ttk.Entry(inrow, textvariable=ev["raw_min"], width=7).pack(side="left", padx=(2, 8))
    ttk.Label(inrow, text="max").pack(side="left")
    ttk.Entry(inrow, textvariable=ev["raw_max"], width=7).pack(side="left", padx=(2, 8))
    ttk.Label(inrow, text="(leer = aus Kalibrierung; raw_max am Detent klemmt dort)",
              foreground="#666").pack(side="left")

    tffr = ttk.Frame(axfr)
    tffr.pack(anchor="w", pady=(2, 0))
    ttk.Label(tffr, text="Transform").pack(side="left", padx=(0, 6))
    ttk.Label(tffr, text="dz").pack(side="left")
    ttk.Entry(tffr, textvariable=ev["tf_deadzone"], width=5).pack(side="left", padx=(2, 8))
    ttk.Label(tffr, text="Kurve").pack(side="left")
    ttk.Combobox(tffr, textvariable=ev["tf_curve"], values=list(gui_mapper.CURVES),
                 state="readonly", width=8).pack(side="left", padx=(2, 8))
    ttk.Label(tffr, text="expo").pack(side="left")
    ttk.Entry(tffr, textvariable=ev["tf_expo"], width=5).pack(side="left", padx=(2, 8))
    ttk.Checkbutton(tffr, text="invert", variable=ev["tf_invert"]).pack(side="left", padx=(0, 8))
    ttk.Label(tffr, text="Ausgang (out)").pack(side="left")
    ttk.Entry(tffr, textvariable=ev["tf_out_min"], width=7).pack(side="left", padx=2)
    ttk.Label(tffr, text="…").pack(side="left")
    ttk.Entry(tffr, textvariable=ev["tf_out_max"], width=7).pack(side="left", padx=2)

    ttk.Label(
        axfr, foreground="#666", wraplength=580, justify="left",
        text=(
            "Felder — Eingang (roh) min/max: Rohbereich der Hardware (aus Kalibrierung; "
            "leer = automatisch). dz (Deadzone): kleine Auslenkung um die Mitte ignorieren. "
            "Kurve: Kennlinie linear/expo/squared. expo: deren Stärke 0…1 (weicher um die "
            "Mitte). invert: Richtung umkehren. Ausgang (out) min/max: Wertebereich, der an "
            "die Sim geht.\n"
            "Pipeline: Roh → auf -1…1 normieren (min/max) → Deadzone → Kurve/Expo → Invert "
            "→ auf out_min…out_max skalieren → Event/SimVar (Achsen-*_SET z. B. "
            "-16383…16383). Roh-Werte außerhalb min…max klemmen automatisch.\n"
            "Am Detent teilen: »Duplizieren« → oberer Teil raw_min=Detent, raw_max=voll, "
            "out=0…max (Detent = Leerlauf/0); unterer Teil raw_min=ganz-zurück, "
            "raw_max=Detent + eigene Aktion (Reverse/Feather/Cutoff)."
        ),
    ).pack(anchor="w", pady=(2, 0))

    # row 4: actions + feedback
    edbtn = ttk.Frame(ed)
    edbtn.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(6, 0))
    ttk.Button(edbtn, text="Übernehmen", command=lambda: _ed_apply()).pack(side="left")
    ttk.Button(edbtn, text="Zurücksetzen", command=lambda: _ed_reset()).pack(side="left", padx=6)
    ttk.Button(edbtn, text="+ Neu", command=lambda: _ed_add()).pack(side="left")
    ttk.Button(edbtn, text="Duplizieren", command=lambda: _ed_duplicate()).pack(side="left", padx=6)
    ttk.Button(edbtn, text="Entfernen", command=lambda: _ed_remove()).pack(side="left")
    ed_status = ttk.Label(edbtn, text="", foreground="#666")
    ed_status.pack(side="left", padx=10)

    def _ed_status(msg, error=False):
        ed_status.config(text=msg, foreground="#c62828" if error else "#2e7d32" if msg else "#666")

    def _ed_show_fields(*_):
        for frame in af.values():
            frame.pack_forget()
        af.get(ev["action_type"].get(), af["event"]).pack(side="left", fill="x")
        if ev["kind"].get() == "axis":
            axfr.grid()
        else:
            axfr.grid_remove()

    def _ed_set_form(form):
        for key, var in ev.items():
            if key in form:
                var.set(form[key])
        _ed_show_fields()

    def _seq_original(binding):
        if binding.action.type != "sequence":
            return None
        d = binding.action.model_dump(exclude_defaults=True)
        d["type"] = "sequence"  # excluded as a default, but the union needs it
        return d

    def _ed_clear():
        etgt.update(device=None, index=None, original_action=None)
        for var in ev.values():
            var.set(False if isinstance(var, tk.BooleanVar) else "")
        ev["action_type"].set("event")
        ev["kind"].set("button")
        _ed_show_fields()
        ed.config(text="Binding bearbeiten")
        _ed_status("Wähle links ein Gerät und ein Binding.")

    def _ed_load(device_id, index):
        prof = mstate["profile"]
        binds = prof.bindings.get(device_id, []) if prof else []
        if not (0 <= index < len(binds)):
            _ed_clear()
            return
        binding = binds[index]
        etgt.update(device=device_id, index=index, original_action=_seq_original(binding))
        _ed_set_form(gui_mapper.binding_to_form(binding))
        ed.config(text=f"Binding bearbeiten — {device_id} #{index}: {binding.name}")

    def _ed_reset():
        if etgt["device"] is None:
            return
        if etgt["index"] is None:  # unsaved new binding -> back to a fresh blank form
            _ed_set_form(gui_mapper.blank_binding_form("button"))
            _ed_status("Felder ausfüllen, dann Übernehmen.")
        else:
            _ed_load(etgt["device"], etgt["index"])

    def _ed_save(mutate):
        """Load the profile doc, apply mutate, validate, dump. Error str or None."""
        path = profiles_dir() / f"{profile_var.get()}.yaml"
        try:
            data = profile_writer.load(path)
            mutate(data)
            profile_writer.validate(data)
            profile_writer.dump(data, path)
            return None
        except Exception as exc:  # show any failure inline instead of crashing
            return str(exc)

    def _reselect(device_id, index):
        mstate["reselect"] = (device_id, index)
        _mapper_reload(rediscover=False, keep_device=device_id)

    def _ed_apply():
        if etgt["device"] is None:
            _ed_status("Kein Binding gewählt.", error=True)
            return
        try:
            binding = gui_mapper.form_to_binding(
                {k: var.get() for k, var in ev.items()}, etgt["original_action"]
            )
        except ValueError as exc:
            _ed_status(str(exc), error=True)
            return
        dev, idx = etgt["device"], etgt["index"]
        if idx is None:  # new binding from _ed_add: append at the end
            prof = mstate["profile"]
            idx = len(prof.bindings.get(dev, [])) if prof else 0
            err = _ed_save(lambda d: profile_writer.add_binding(d, dev, binding))
            msg = "Neues Binding angelegt ✓"
        else:
            err = _ed_save(lambda d: profile_writer.apply_binding_edit(d, dev, idx, binding))
            msg = "Gespeichert ✓"
        if err:
            _ed_status(f"Nicht gespeichert: {err}", error=True)
            return
        _reselect(dev, idx)
        _ed_status(msg)

    def _ed_add():
        dev = _sel(dev_tree)
        if dev is None:
            _ed_status("Kein Gerät gewählt.", error=True)
            return
        # Don't write a half-filled stub (an empty form fails validation): enter
        # "new binding" mode (index=None) with a blank form and defer the append
        # + validation to Übernehmen, so nothing invalid is ever written.
        etgt.update(device=dev, index=None, original_action=None)
        _ed_set_form(gui_mapper.blank_binding_form("button"))
        ed.config(text=f"Neues Binding — {dev} (noch nicht gespeichert)")
        _ed_status("Felder ausfüllen, dann Übernehmen.")

    def _ed_duplicate():
        if etgt["device"] is None or etgt["index"] is None:
            _ed_status("Kein gespeichertes Binding gewählt.", error=True)
            return
        dev, idx = etgt["device"], etgt["index"]
        binding = mstate["profile"].bindings[dev][idx]
        dup = gui_mapper.form_to_binding(
            gui_mapper.binding_to_form(binding), _seq_original(binding))
        dup["name"] = binding.name + " (Kopie)"
        err = _ed_save(lambda d: profile_writer.add_binding(d, dev, dup, index=idx + 1))
        if err:
            _ed_status(f"Nicht dupliziert: {err}", error=True)
            return
        _reselect(dev, idx + 1)
        _ed_status("Dupliziert ✓")

    def _ed_remove():
        if etgt["device"] is None or etgt["index"] is None:
            _ed_status("Kein gespeichertes Binding gewählt.", error=True)
            return
        dev, idx = etgt["device"], etgt["index"]
        err = _ed_save(lambda d: profile_writer.remove_binding(d, dev, idx))
        if err:
            _ed_status(f"Nicht entfernt: {err}", error=True)
            return
        _reselect(dev, max(0, idx - 1))
        _ed_status("Entfernt ✓")

    def _ed_on_detail_select(*_):
        sel = _sel(detail)
        dev = _sel(dev_tree)
        if sel and str(sel).startswith("bind:") and dev:
            _ed_load(dev, int(str(sel).split(":")[1]))
        else:
            _ed_clear()

    def _render_detail(device_id, reselect_index=None):
        detail.delete(*detail.get_children())
        prof = mstate["profile"]
        if prof is None or not device_id:
            _ed_clear()
            return
        binds = gui_mapper.device_bindings(prof, device_id)
        bnode = detail.insert("", "end", text=f"Bindings ({len(binds)})", open=True)
        for i, br in enumerate(binds):
            detail.insert(bnode, "end", iid=f"bind:{i}", text=br.name,
                          values=(br.source, br.action, br.transform))
        out_objs = prof.outputs.get(device_id, [])
        if out_objs:
            onode = detail.insert("", "end", text=f"Outputs ({len(out_objs)})", open=True)
            for i, o in enumerate(out_objs):
                pnode = detail.insert(onode, "end", iid=f"out:{i}", open=True,
                                      text=gui_mapper.describe_output(o))
                for j, line in enumerate(gui_mapper.describe_output_detail(o)):
                    detail.insert(pnode, "end", iid=f"out:{i}:{j}", text=line)
        if reselect_index is not None and binds:
            idx = min(reselect_index, len(binds) - 1)
            detail.selection_set(f"bind:{idx}")
            detail.see(f"bind:{idx}")
            _ed_load(device_id, idx)
        else:
            _ed_clear()

    def _mapper_reload(rediscover: bool = False, keep_device=None):
        prof = _current_profile()
        cat = _device_catalog()
        dev_tree.delete(*dev_tree.get_children())
        if prof is None or cat is None:
            mstate["profile"] = None
            _render_detail(None)
            m_state.config(text="Profil oder Geräte-Katalog nicht lesbar")
            return
        if rediscover:
            mstate["present"] = _discover_present(cat)
            mstate["discovered"] = True
        rows = gui_mapper.build_device_rows(cat, prof, mstate["present"])
        mstate["profile"] = prof
        ids = set()
        for r in rows:
            dev_tree.insert("", "end", iid=r.id, text=r.name,
                            values=(r.transport, r.status, r.bindings, r.outputs))
            ids.add(r.id)
        target = keep_device if keep_device in ids else (rows[0].id if rows else None)
        if target:
            dev_tree.selection_set(target)
            dev_tree.focus(target)
        reselect = mstate.pop("reselect", None)
        ridx = reselect[1] if (reselect and reselect[0] == target) else None
        _render_detail(target, ridx)
        if mstate["present"] is None:
            m_state.config(text=f"{len(rows)} Geräte · Erkennung n/a · Profil „{prof.name}“")
        else:
            n = sum(1 for r in rows if r.present)
            m_state.config(text=f"{n}/{len(rows)} verbunden · Profil „{prof.name}“")

    kind_cb.bind("<<ComboboxSelected>>", _ed_show_fields)
    type_cb.bind("<<ComboboxSelected>>", _ed_show_fields)
    dev_tree.bind("<<TreeviewSelect>>", lambda *_: _render_detail(_sel(dev_tree)))
    detail.bind("<<TreeviewSelect>>", _ed_on_detail_select)
    profile_var.trace_add("write", lambda *_: _mapper_reload(rediscover=False))
    _ed_clear()

    # Switching tabs: the Statistik tab starts/stops its live reads; the Mapper
    # tab discovers devices the first time it is shown (lazy, keeps startup fast).
    def _on_tab_changed(_e=None):
        _resubscribe()
        if str(nb.select()) == str(mtab):
            _mapper_reload(rediscover=not mstate["discovered"])

    nb.bind("<<NotebookTabChanged>>", _on_tab_changed)

    # --- bottom status bar (small lamps) ----------------------------------- #
    ttk.Separator(win, orient="horizontal").grid(row=2, column=0, sticky="ew", pady=(8, 0))
    bar = ttk.Frame(win, padding=(10, 3))
    bar.grid(row=3, column=0, sticky="ew")
    ttk.Label(bar, text="Status:", foreground="#666",
              font=("TkDefaultFont", 8)).pack(side="left", padx=(0, 8))
    lamps: dict[str, tk.Label] = {}
    for key in ("MSFS", "Bridge", "Mapper"):
        lamp = tk.Label(bar, text=f"● {key}", font=("TkDefaultFont", 8), fg="#999")
        lamp.pack(side="left", padx=(0, 12))
        lamps[key] = lamp

    def _set_lamp(key: str, on: bool):
        lamps[key].config(fg="#2e7d32" if on else "#c62828")

    def refresh():
        bridge.poll()
        if mapper["ctl"] is not None:
            mapper["ctl"].poll()
        _set_lamp("MSFS", _msfs_running())
        bridge_up = _port_listening(BRIDGE_PORT)
        _set_lamp("Bridge", bridge_up)
        _set_lamp("Mapper", mapper["ctl"] is not None and mapper["ctl"].is_running())
        # Re-evaluate the live subscription each tick: cheap (set_names is a no-op
        # when unchanged) and self-correcting, so minimizing/restoring or hiding the
        # Statistik tab drops/re-adds its reads without needing extra event wiring.
        _resubscribe()
        update_values()
        mon_state.config(text="● live" if bridge_up else "Bridge aus")
        win.after(_POLL_MS, refresh)

    def _on_close():
        # Close the detached panel, stop the monitor thread, and don't orphan the
        # mapper this GUI started; leave the bridge up (it persists for reattach).
        pw = panel_ref["win"]
        if pw is not None and pw.alive():
            pw.destroy()
        monitor.stop()
        stop_mapper()
        win.destroy()

    # Reopen the panel if it was visible last session.
    if load_panel_state()["visible"]:
        _show_panel()

    win.protocol("WM_DELETE_WINDOW", _on_close)
    refresh()
    win.mainloop()


def main() -> None:
    try:
        run()
    except Exception as exc:  # pragma: no cover - GUI/display errors
        print(f"GUI konnte nicht starten: {exc}", file=sys.stderr)
        print("Läuft ein Display? Ist python3-tk installiert (import tkinter)?",
              file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
