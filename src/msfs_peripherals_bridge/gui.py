"""Tkinter control panel for the bridge, the mapper and a live variable monitor.

Layout: a profile selector on top (always visible, above the tabs), a ttk.Notebook
with tabs, and a small status bar with lamps pinned to the bottom edge.

* **Connection** tab — start/stop the bridge (supervisor → bridge.py → Proton) and
  the mapper, plus a one-click "stop everything". Buttons carry a tooltip with the
  actual command they run.
* **Statistik** tab — assemble a live value list: pick variables from a searchable,
  type-filterable catalog (popup) and read their current values (snapshot).

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
    from tkinter import messagebox, ttk

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
    win.minsize(480, 400)
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
    ttk.Combobox(prow, textvariable=profile_var, values=profiles, state="readonly",
                 width=22).pack(side="left", padx=6)
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
    # Switching to/from the Statistik tab immediately starts/stops its live reads.
    nb.bind("<<NotebookTabChanged>>", lambda _e: _resubscribe())

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
