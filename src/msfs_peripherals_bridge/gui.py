"""Tkinter control panel for the bridge, the mapper and a live variable monitor.

Layout: a profile selector on top (always visible, above the tabs), a ttk.Notebook
with tabs, and a small status bar with lamps pinned to the bottom edge.

* **Connection** tab — start/stop the bridge (supervisor → bridge.py → Proton) and
  the mapper, plus a one-click "stop everything". Buttons carry a tooltip with the
  actual command they run.
* **Statistik** tab — assemble a live value list: pick variables from a searchable,
  type-filterable catalog (popup) and read their current values (snapshot).
* **Gauges** tab — click a panel together from round instruments (ported from the
  user's Air Manager gauges): pick a template/library gauge, map its needles to
  variables first, then it renders live on the panel canvas (gauge_model.py).
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

from . import env_check
from .config import calibration_file, gui_settings_file, profiles_dir, project_root
from .i18n import tr

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


def load_language(path: Path | None = None) -> str:
    """Restore the saved GUI language code (defaults to German)."""
    from .i18n import DEFAULT_LANG, LANGUAGES
    code = load_gui_settings(path).get("language")
    return code if code in LANGUAGES else DEFAULT_LANG


def save_language(code: str, path: Path | None = None) -> None:
    """Persist the GUI language code, preserving the rest of the settings file."""
    data = load_gui_settings(path)
    data["language"] = code
    save_gui_settings(data, path)


def load_prefix_path(path: Path | None = None) -> str:
    """Restore the saved MSFS Proton prefix path ("" = auto-detect)."""
    value = load_gui_settings(path).get("prefix_path")
    return value if isinstance(value, str) else ""


def save_prefix_path(prefix: str, path: Path | None = None) -> None:
    """Persist the prefix path, preserving the rest of the settings file."""
    data = load_gui_settings(path)
    data["prefix_path"] = prefix
    save_gui_settings(data, path)


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
    """Subscription name: A: bare, L:/V: prefixed, K: events carry no value."""
    if kind in ("L:", "V:"):
        return name if name.startswith(kind) else kind + name
    if kind == "A:":
        return name
    return None


def _local_vars_as_dicts(prof) -> list[dict]:
    """A profile's local V: vars as plain dicts (for profile_writer.set_local_vars)."""
    out: list[dict] = []
    for lv in prof.local_vars:
        d: dict = {"name": lv.name}
        if lv.unit != "number":
            d["unit"] = lv.unit
        if lv.initial:
            d["initial"] = lv.initial
        if lv.description:
            d["description"] = lv.description
        if lv.persist:
            d["persist"] = True
        out.append(d)
    return out


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


def _mapper_running() -> bool:
    """True while a mapper process is live — it owns the panel feature-report
    writes, so the GUI's 🔦 test-send must stand down (single-owner hardware)."""
    return any(m in cmd for _, cmd in _iter_proc_cmdlines() for m in _MAPPER_MATCHES)


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

    def __init__(self, name: str, argv: list[str], cwd: Path, log_path: Path | None = None,
                 env: dict[str, str] | None = None):
        self.name = name
        self.argv = argv
        self.cwd = cwd
        self.log_path = log_path
        # Extra environment overrides merged onto os.environ at launch. Kept
        # mutable so the Connection tab can retarget the prefix before start().
        self.env = env
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
        full_env = {**os.environ, **self.env} if self.env else None
        self.proc = subprocess.Popen(
            self.argv, cwd=str(self.cwd), stdout=stdout,
            stderr=subprocess.STDOUT, start_new_session=True, env=full_env,
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
            borderwidth=1, font=("TkDefaultFont", 8), padx=6, pady=3, wraplength=340,
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

    from .gui_catalog import (
        KIND_EVENT,
        KIND_LVAR,
        KIND_SIMVAR,
        KIND_VIRTUAL,
        filter_catalog,
    )

    kinds = {"Alle": None, "A: SimVar": KIND_SIMVAR, "K: Event": KIND_EVENT,
             "L: LVar": KIND_LVAR, "V: lokal": KIND_VIRTUAL}

    top = tk.Toplevel(parent)
    top.title("Variable auswählen")
    top.geometry("480x440")
    top.columnconfigure(0, weight=1)
    top.rowconfigure(1, weight=1)

    filt = ttk.Frame(top, padding=8)
    filt.grid(row=0, column=0, sticky="ew")
    ttk.Label(filt, text=tr("Typ:")).pack(side="left")
    kind_var = tk.StringVar(value="Alle")
    ttk.Combobox(filt, textvariable=kind_var, values=list(kinds), state="readonly",
                 width=12).pack(side="left", padx=(4, 10))
    ttk.Label(filt, text=tr("Suche:")).pack(side="left")
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
    count = ttk.Label(foot, text=tr(""))
    count.pack(side="left")
    ttk.Button(foot, text=tr("Schließen"), command=top.destroy).pack(side="right")
    ttk.Button(foot, text=tr("Hinzufügen"), command=add_selected).pack(side="right", padx=6)

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

    def __init__(self, master, monitor, on_change, on_close, catalog_provider=None) -> None:
        import tkinter as tk

        self._tk = tk
        self.monitor = monitor
        self._on_change = on_change
        self._on_close = on_close
        self._catalog_provider = catalog_provider or (lambda: [])
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
        handle = tk.Label(bar, text=tr("::"), background="#37474f", foreground="#b0bec5",
                          font=("TkDefaultFont", 10, "bold"), cursor="fleur")
        handle.pack(side="left", padx=(6, 4))
        add_btn = tk.Button(bar, text=tr("+ Variable"), background="#455a64",
                            foreground="#eceff1", relief="flat", cursor="hand2",
                            activebackground="#546e7a", activeforeground="#ffffff",
                            highlightthickness=0, borderwidth=0, padx=6,
                            command=self._pick_var)
        add_btn.pack(side="left", padx=(0, 8))
        tk.Label(bar, text=tr("Raster"), background="#37474f",
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
                tk.Label(bar, text=tr("x"), background="#37474f",
                         foreground="#eceff1").pack(side="left", padx=2)
        hint = tk.Label(bar, background="#37474f", foreground="#90a4ae",
                        text=tr("  ziehen = bewegen · Kacheln einrasten/tauschen · "
                                "Rechtsklick = weg"))
        hint.pack(side="left", padx=6)
        for wgt in (bar, handle, hint):
            wgt.bind("<ButtonPress-1>", self._move_start)
            wgt.bind("<B1-Motion>", self._move_drag)
            wgt.bind("<ButtonRelease-1>", self._move_end)

        self.canvas = tk.Canvas(self.win, highlightthickness=0, background="#cfd8dc")
        self.canvas.pack(side="top", fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _e: self._relayout())

        # Resize grip pinned to the bottom-right corner (overlays the canvas).
        grip = tk.Label(self.win, text=tr("/"), background="#cfd8dc", foreground="#546e7a",
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

    def _pick_var(self) -> None:
        """Open the shared var picker; each pick drops a tile into the grid."""
        def _on(v):
            if self.add(v.kind, v.name, getattr(v, "unit", "") or ""):
                self._on_change()
        _open_var_picker(self.win, self._catalog_provider(), _on)

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
        val = tk.Label(row, text=tr("—"), font=("TkDefaultFont", 13, "bold"), background="#ffffff")
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
        menu.add_command(label=tr("Kachel entfernen"), command=lambda: self._remove(key))
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
    from .i18n import set_language

    # Apply the persisted UI language before any widget text is built.
    set_language(load_language())

    root_dir = project_root()
    # The prefix path (persisted, "" = auto-detect) targets the bridge at a
    # specific MSFS Proton prefix via env overrides; recomputed before each start.
    prefix_var_holder: dict[str, str] = {"path": load_prefix_path()}
    bridge = ProcessController(
        "bridge", ["bash", str(root_dir / "bridge" / "run-bridge.sh")],
        cwd=root_dir, log_path=root_dir / "bridge" / "bridge.log",
        env=env_check.bridge_env(prefix_var_holder["path"]),
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
    win.rowconfigure(0, weight=1)  # the notebook grows

    # --- modern-ish theme: flat light palette + a blue accent + red danger ---- #
    BG, SURFACE, TEXT, MUTED = "#f4f5f7", "#ffffff", "#1f2430", "#6b7280"
    ACCENT, ACCENT_ACT = "#2563eb", "#1d4ed8"
    DANGER, DANGER_ACT = "#dc2626", "#b91c1c"
    style = ttk.Style(win)
    with contextlib.suppress(Exception):
        style.theme_use("clam")  # the only stock theme that honours custom colours
    win.configure(bg=BG)
    style.configure(".", background=BG, foreground=TEXT, fieldbackground=SURFACE,
                    bordercolor="#d1d5db", lightcolor=BG, darkcolor=BG)
    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, foreground=TEXT)
    style.configure("TLabelframe", background=BG, bordercolor="#d1d5db")
    style.configure("TLabelframe.Label", background=BG, foreground=MUTED)
    style.configure("TButton", padding=(10, 5), background="#e5e7eb", foreground=TEXT,
                    borderwidth=0, focuscolor=BG)
    style.map("TButton", background=[("active", "#d1d5db"), ("disabled", "#eef0f2")],
              foreground=[("disabled", "#9aa1ab")])
    style.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(6, 6, 6, 0))
    style.configure("TNotebook.Tab", padding=(14, 7), background="#e5e7eb",
                    foreground=MUTED, borderwidth=0)
    style.map("TNotebook.Tab", background=[("selected", SURFACE)],
              foreground=[("selected", ACCENT)], expand=[("selected", (0, 0, 0, 0))])
    style.configure("Treeview", background=SURFACE, fieldbackground=SURFACE, foreground=TEXT,
                    rowheight=25, borderwidth=0)
    style.configure("Treeview.Heading", background="#e5e7eb", foreground=MUTED,
                    relief="flat", padding=4)
    style.map("Treeview", background=[("selected", ACCENT)], foreground=[("selected", "#ffffff")])
    style.configure("TCombobox", padding=3)
    style.configure("TEntry", padding=3)
    # Primary/important actions and destructive actions get colour.
    style.configure("Accent.TButton", background=ACCENT, foreground="#ffffff",
                    padding=(12, 6), borderwidth=0)
    style.map("Accent.TButton", background=[("active", ACCENT_ACT), ("disabled", "#a9c1f6")],
              foreground=[("disabled", "#eef2ff")])
    # Inverted accent — used by the Panel toggle while the panel is open.
    style.configure("AccentInv.TButton", background=SURFACE, foreground=ACCENT,
                    padding=(12, 6), borderwidth=1)
    style.map("AccentInv.TButton", background=[("active", "#eef2ff")],
              foreground=[("disabled", "#a9c1f6")])
    style.configure("Danger.TButton", background=DANGER, foreground="#ffffff",
                    padding=(10, 5), borderwidth=0)
    style.map("Danger.TButton", background=[("active", DANGER_ACT), ("disabled", "#eab8b8")])
    # Success (green) — positive/add actions, e.g. pulling variables into the list.
    style.configure("Success.TButton", background="#2e7d32", foreground="#ffffff",
                    padding=(10, 5), borderwidth=0)
    style.map("Success.TButton", background=[("active", "#256a29"), ("disabled", "#a9d3ab")],
              foreground=[("disabled", "#eef7ee")])
    # Compact variants for dense groups (Connection tab): smaller padding, colours
    # re-declared explicitly so they don't depend on ttk style-map inheritance.
    style.configure("Small.TButton", padding=(8, 3))
    style.configure("SmallAccent.TButton", background=ACCENT, foreground="#ffffff",
                    padding=(8, 3), borderwidth=0)
    style.map("SmallAccent.TButton",
              background=[("active", ACCENT_ACT), ("disabled", "#a9c1f6")],
              foreground=[("disabled", "#eef2ff")])
    style.configure("SmallDanger.TButton", background=DANGER, foreground="#ffffff",
                    padding=(8, 3), borderwidth=0)
    style.map("SmallDanger.TButton", background=[("active", DANGER_ACT), ("disabled", "#eab8b8")])

    # On/off state of the (borderless) Panel window, mirrored by the toolbar
    # toggle button below. The panel is created when on and destroyed when off.
    panel_on = tk.BooleanVar(value=False)
    panel_btn_text = tk.StringVar(value="🖥  " + tr("Panel öffnen"))
    panel_btn: dict = {"w": None}  # holds the toggle button once built (for text/style)

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

    # The profile selector + management live in their own "Profile" tab (built
    # last, below) rather than a permanent row above the tabs.
    nb = ttk.Notebook(win)
    nb.grid(row=0, column=0, sticky="nsew", padx=10)

    # ===== Connection tab ================================================== #
    # A nested notebook keeps the tab tidy: "Control & status" carries the
    # process buttons (grouped by sense) and the prerequisite check-list; the
    # live bridge "terminal" is tucked onto its own "Bridge log" sub-tab.
    conn = ttk.Frame(nb, padding=0)
    nb.add(conn, text=tr("tab.connection"))
    conn.columnconfigure(0, weight=1)
    conn.rowconfigure(0, weight=1)
    conn_nb = ttk.Notebook(conn)
    conn_nb.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
    ctltab = ttk.Frame(conn_nb, padding=10)
    logtab = ttk.Frame(conn_nb, padding=10)
    conn_nb.add(ctltab, text=tr("conn.subtab.control"))
    conn_nb.add(logtab, text=tr("conn.subtab.log"))
    ctltab.columnconfigure(0, weight=1)

    def start_bridge():
        # Don't double-start: if 7842 already LISTENs (bridge up from a terminal
        # or an earlier run) a second supervisor's bridge.py just fails to bind
        # the port and crash-loops.
        if _port_listening(BRIDGE_PORT):
            return
        # Retarget the (possibly reconfigured) prefix before launching.
        bridge.env = env_check.bridge_env(prefix_var_holder["path"])
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

    # --- group 1: processes (Bridge / Mapper start-stop, compact) ---------- #
    proc_fr = ttk.Labelframe(ctltab, text=tr("conn.group.processes"), padding=10)
    proc_fr.grid(row=0, column=0, sticky="ew")
    proc_fr.columnconfigure(1, weight=1)
    proc_fr.columnconfigure(2, weight=1)

    ttk.Label(proc_fr, text=tr("conn.bridge")).grid(row=0, column=0, sticky="w",
                                                     padx=(0, 10), pady=2)
    b_bs = ttk.Button(proc_fr, text=tr("conn.start"), style="SmallAccent.TButton",
                      command=start_bridge)
    b_bx = ttk.Button(proc_fr, text=tr("conn.stop"), style="SmallDanger.TButton",
                      command=stop_bridge)
    b_bs.grid(row=0, column=1, sticky="ew", padx=3, pady=2)
    b_bx.grid(row=0, column=2, sticky="ew", padx=3, pady=2)

    ttk.Label(proc_fr, text=tr("conn.mapper")).grid(row=1, column=0, sticky="w",
                                                     padx=(0, 10), pady=2)
    b_ms = ttk.Button(proc_fr, text=tr("conn.start"), style="SmallAccent.TButton",
                      command=start_mapper)
    b_mx = ttk.Button(proc_fr, text=tr("conn.stop"), style="SmallDanger.TButton",
                      command=stop_mapper)
    b_ms.grid(row=1, column=1, sticky="ew", padx=3, pady=2)
    b_mx.grid(row=1, column=2, sticky="ew", padx=3, pady=2)

    b_all = ttk.Button(proc_fr, text=tr("conn.stop_all"), style="SmallDanger.TButton",
                       command=stop_all)
    b_all.grid(row=2, column=0, columnspan=3, sticky="ew", padx=3, pady=(8, 2))

    ttk.Label(proc_fr, text=tr("conn.single_client_note"), foreground=MUTED,
              font=("TkDefaultFont", 8)).grid(row=3, column=0, columnspan=3,
                                              sticky="w", pady=(6, 0))

    _attach_tooltip(b_bs, tr("bash bridge/run-bridge.sh   (Supervisor → bridge.py → Proton)"))
    _attach_tooltip(b_bx, tr("killpg SIGTERM + sweep 'bridge/bridge.py' / 'bridge/run-bridge.sh'"))
    _attach_tooltip(b_ms, mapper_cmd)  # dynamic: reflects the selected profile
    _attach_tooltip(b_mx,
                    tr("killpg SIGTERM (Mapper-Prozessgruppe) + sweep 'peripherals_bridge run'"))
    _attach_tooltip(b_all, tr("stop_mapper() + stop_bridge() — alle Strays wegräumen"))

    # --- group 2: environment & prerequisites (prefix + green/red checks) -- #
    env_fr = ttk.Labelframe(ctltab, text=tr("conn.group.environment"), padding=10)
    env_fr.grid(row=1, column=0, sticky="ew", pady=(10, 0))
    env_fr.columnconfigure(1, weight=1)

    ttk.Label(env_fr, text=tr("conn.prefix_label")).grid(row=0, column=0, sticky="w",
                                                         padx=(0, 8), pady=2)
    prefix_var = tk.StringVar(value=prefix_var_holder["path"])
    prefix_entry = ttk.Entry(env_fr, textvariable=prefix_var)
    prefix_entry.grid(row=0, column=1, sticky="ew", pady=2)
    prefix_btns = ttk.Frame(env_fr)
    prefix_btns.grid(row=0, column=2, sticky="e", padx=(6, 0))

    checks_fr = ttk.Frame(env_fr)
    summary_lbl = tk.Label(env_fr, text=tr(""), font=("TkDefaultFont", 9, "bold"),
                           bg=BG, anchor="w")

    def _render_checks() -> None:
        for w in checks_fr.winfo_children():
            w.destroy()
        items = env_check.check_prerequisites(prefix_var_holder["path"] or None, root_dir)
        n_bad = 0
        for i, item in enumerate(items):
            n_bad += 0 if item.ok else 1
            tk.Label(checks_fr, text=tr("✓") if item.ok else "✗", bg=BG,
                     fg="#2e7d32" if item.ok else "#c62828",
                     font=("TkDefaultFont", 10, "bold")).grid(row=i, column=0,
                                                              sticky="w", padx=(0, 6))
            tk.Label(checks_fr, text=tr(item.key), bg=BG, fg=TEXT, anchor="w"
                     ).grid(row=i, column=1, sticky="w")
            tk.Label(checks_fr, text=item.detail, bg=BG, fg=MUTED,
                     font=("TkDefaultFont", 8), anchor="w").grid(row=i, column=2,
                                                                 sticky="w", padx=(8, 0))
        if n_bad == 0:
            summary_lbl.config(text=tr("✓ ") + tr("conn.prereq_all_ok"), fg="#2e7d32")
        else:
            summary_lbl.config(text=tr("✗ ") + tr("conn.prereq_problems", n=n_bad), fg="#c62828")

    def _apply_prefix() -> None:
        prefix_var_holder["path"] = prefix_var.get().strip()
        save_prefix_path(prefix_var_holder["path"])
        bridge.env = env_check.bridge_env(prefix_var_holder["path"])
        _render_checks()

    def _browse_prefix() -> None:
        from tkinter import filedialog
        start = prefix_var.get().strip() or str(env_check.default_prefix())
        chosen = filedialog.askdirectory(initialdir=start, title=tr("conn.prefix_label"))
        if chosen:
            prefix_var.set(chosen)
            _apply_prefix()

    def _spawn_and_tail(*, title: str, argv: list[str], env: dict[str, str], on_done) -> None:
        """Run a one-shot setup subprocess and stream its output into a window."""
        top = tk.Toplevel(win)
        top.title(title)
        top.geometry("760x460")
        top.columnconfigure(0, weight=1)
        top.rowconfigure(1, weight=1)
        ttk.Label(top, text=tr("conn.setup_running"), padding=6).grid(row=0, column=0,
                                                                      columnspan=2, sticky="w")
        txt = tk.Text(top, wrap="none", background="#0f172a", foreground="#d1d5db",
                      font=("TkFixedFont", 9), borderwidth=0, highlightthickness=0)
        txt.grid(row=1, column=0, sticky="nsew")
        vsb = ttk.Scrollbar(top, orient="vertical", command=txt.yview)
        vsb.grid(row=1, column=1, sticky="ns")
        txt.config(yscrollcommand=vsb.set)
        setup_log = root_dir / "bridge" / "setup-prefix.log"
        fh = open(setup_log, "w", encoding="utf-8")  # noqa: SIM115 (closed when the child ends)
        full_env = {**os.environ, **env} if env else None
        proc = subprocess.Popen(argv, cwd=str(root_dir), stdout=fh,
                                stderr=subprocess.STDOUT, start_new_session=True, env=full_env)
        st = {"at": 0, "done": False}

        def _pump():
            with contextlib.suppress(OSError):
                with open(setup_log, encoding="utf-8", errors="replace") as r:
                    r.seek(st["at"])
                    chunk = r.read()
                    st["at"] = r.tell()
                if chunk:
                    txt.insert("end", chunk)
                    txt.see("end")
            if proc.poll() is None:
                top.after(500, _pump)
            elif not st["done"]:
                st["done"] = True
                with contextlib.suppress(Exception):
                    fh.close()
                txt.insert("end", f"\n— exit {proc.returncode} —\n")
                txt.see("end")
                with contextlib.suppress(Exception):
                    on_done()
        _pump()

    def _run_setup() -> None:
        if not messagebox.askyesno(tr("dialog.confirm"), tr("conn.setup_confirm")):
            return
        _spawn_and_tail(
            title=tr("conn.setup_title"),
            argv=["bash", str(root_dir / "bridge" / "setup-prefix.sh")],
            env=env_check.bridge_env(prefix_var_holder["path"]),
            on_done=_render_checks,
        )

    b_browse = ttk.Button(prefix_btns, text=tr("conn.browse"), style="Small.TButton",
                          command=_browse_prefix)
    b_save = ttk.Button(prefix_btns, text=tr("conn.save"), style="Small.TButton",
                        command=_apply_prefix)
    b_browse.pack(side="left", padx=(0, 4))
    b_save.pack(side="left")
    prefix_entry.bind("<Return>", lambda _e: _apply_prefix())
    _attach_tooltip(b_browse, tr("filedialog.askdirectory → prefix_path (gui-settings.json)"))
    _attach_tooltip(b_save,
                    tr("prefix_path speichern + Bridge-Env (STEAM_COMPAT_DATA_PATH) setzen"))

    ttk.Label(env_fr, text=tr("conn.prefix_hint"), foreground=MUTED,
              font=("TkDefaultFont", 8), wraplength=520, justify="left"
              ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 6))
    ttk.Separator(env_fr, orient="horizontal").grid(row=2, column=0, columnspan=3,
                                                     sticky="ew", pady=4)
    ttk.Label(env_fr, text=tr("conn.prereq_title")).grid(row=3, column=0, columnspan=3,
                                                          sticky="w")
    checks_fr.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(2, 4))
    checks_fr.columnconfigure(2, weight=1)
    summary_lbl.grid(row=5, column=0, columnspan=3, sticky="w", pady=(2, 4))

    env_btns = ttk.Frame(env_fr)
    env_btns.grid(row=6, column=0, columnspan=3, sticky="w", pady=(2, 0))
    b_recheck = ttk.Button(env_btns, text=tr("conn.recheck"), style="Small.TButton",
                           command=_render_checks)
    b_setup = ttk.Button(env_btns, text=tr("conn.setup_prefix"), style="Small.TButton",
                         command=_run_setup)
    b_recheck.pack(side="left", padx=(0, 4))
    b_setup.pack(side="left")
    _attach_tooltip(b_setup, tr("bash bridge/setup-prefix.sh  (Windows-Python + SimConnect)"))

    _render_checks()  # initial green/red status the moment the tab is built

    # --- log sub-tab: the tailed bridge "terminal" ------------------------- #
    # bridge.py logs every record to bridge/bridge.log (flushed per record — the
    # piped Wine stderr is block-buffered and unreliable). We tail that file so
    # the bridge "terminal" shows here instead of in a separate console.
    logtab.rowconfigure(1, weight=1)
    logtab.columnconfigure(0, weight=1)
    ttk.Label(logtab, text=tr("conn.log_label") + " —  bridge/bridge.log",
              foreground=MUTED).grid(row=0, column=0, sticky="w", pady=(0, 4))
    logfr = ttk.Frame(logtab)
    logfr.grid(row=1, column=0, sticky="nsew")
    logfr.rowconfigure(0, weight=1)
    logfr.columnconfigure(0, weight=1)
    log_txt = tk.Text(logfr, height=12, wrap="none", background="#0f172a",
                      foreground="#d1d5db", insertbackground="#d1d5db",
                      font=("TkFixedFont", 9), borderwidth=0, highlightthickness=0)
    log_txt.grid(row=0, column=0, sticky="nsew")
    log_vsb = ttk.Scrollbar(logfr, orient="vertical", command=log_txt.yview)
    log_vsb.grid(row=0, column=1, sticky="ns")
    log_hsb = ttk.Scrollbar(logfr, orient="horizontal", command=log_txt.xview)
    log_hsb.grid(row=1, column=0, sticky="ew")
    log_txt.config(yscrollcommand=log_vsb.set, xscrollcommand=log_hsb.set, state="disabled")
    _bridge_log_path = root_dir / "bridge" / "bridge.log"
    _log_pos = {"at": 0}

    def _log_append(text: str, follow: bool) -> None:
        log_txt.config(state="normal")
        log_txt.insert("end", text)
        # Cap the buffer so a long session can't grow it without bound.
        if int(log_txt.index("end-1c").split(".")[0]) > 2000:
            log_txt.delete("1.0", "end-1500l")
        log_txt.config(state="disabled")
        if follow:
            log_txt.see("end")

    def _tail_bridge_log():
        try:
            size = _bridge_log_path.stat().st_size
            if size < _log_pos["at"]:  # rotated/truncated → resync from start
                _log_pos["at"] = 0
                log_txt.config(state="normal")
                log_txt.delete("1.0", "end")
                log_txt.config(state="disabled")
            if size > _log_pos["at"]:
                follow = log_txt.yview()[1] > 0.999  # only autoscroll if pinned to bottom
                with open(_bridge_log_path, encoding="utf-8", errors="replace") as fh:
                    if _log_pos["at"] == 0:  # first load: show only the tail
                        fh.seek(max(0, size - 16384))
                        chunk = fh.read()
                        if size > 16384:
                            chunk = "… (älteres im bridge.log)\n" + chunk[chunk.find("\n") + 1:]
                        follow = True
                    else:
                        fh.seek(_log_pos["at"])
                        chunk = fh.read()
                    _log_pos["at"] = fh.tell()
                _log_append(chunk, follow)
        except OSError:
            pass  # log not there yet (bridge never started) — try again next tick
        win.after(700, _tail_bridge_log)

    _tail_bridge_log()

    # ===== Statistik tab =================================================== #
    stab = ttk.Frame(nb, padding=10)
    nb.add(stab, text=tr("tab.variables"))
    stab.rowconfigure(2, weight=1)  # the value table grows (buttons above it in row 1)
    stab.columnconfigure(0, weight=1)

    ttk.Label(stab, text=tr("Live-Wertliste — Variablen zum Beobachten zusammenstellen:")
              ).grid(row=0, column=0, columnspan=4, sticky="w")

    tree = ttk.Treeview(stab, columns=("kind", "name", "value", "unit"),
                        show="headings", height=10)
    for col, head, w, anchor in (
        ("kind", tr("Typ"), 44, "center"), ("name", tr("Variable"), 260, "w"),
        ("value", tr("Wert"), 90, "center"), ("unit", tr("Einheit"), 74, "center"),
    ):
        tree.heading(col, text=head)
        tree.column(col, width=w, anchor=anchor)
    tree.grid(row=2, column=0, columnspan=3, sticky="nsew", pady=6)
    tsb = ttk.Scrollbar(stab, orient="vertical", command=tree.yview)
    tsb.grid(row=2, column=3, sticky="ns", pady=6)
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

    # forward hook: the Gauges tab (built further down) contributes its needle
    # variables to the shared subscription while it is visible.
    gauge_hook: dict = {"wires": lambda: []}

    def _resubscribe():
        # Subscribe only to what's visible: the Statistik list while its tab is
        # shown, the detached panel's tiles while it's open, plus the Gauges
        # tab's needle vars while it is shown. Anything else would keep the
        # bridge reading vars nobody is looking at.
        wires = []
        if _statistik_shown():
            wires += [
                w for iid in tree.get_children("")
                if (w := _wire_name(tree.set(iid, "kind"), tree.set(iid, "name"))) is not None
            ]
        pw = panel_ref["win"]
        if pw is not None and pw.alive():
            wires += pw.wires()
        wires += gauge_hook["wires"]()
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
                tree.set(iid, "value", tr("(Event)"))
                continue
            w = _wire_name(kind, tree.set(iid, "name"))
            tree.set(iid, "value", _fmt_value(vals[w]) if w in vals else "—")

    def _persist_visible(value: bool):
        st = load_panel_state()
        st["visible"] = value
        save_panel_state(st)

    def _panel_btn_open(is_open: bool):
        panel_btn_text.set("🖥  " + (tr("Panel schließen") if is_open else tr("Panel öffnen")))
        if panel_btn["w"] is not None:
            panel_btn["w"].config(style="AccentInv.TButton" if is_open else "Accent.TButton")

    def _panel_closed():
        panel_ref["win"] = None
        panel_on.set(False)
        _panel_btn_open(False)
        _resubscribe()

    def _show_panel():
        pw = panel_ref["win"]
        if pw is None or not pw.alive():
            pw = _PanelWindow(win, monitor, on_change=_resubscribe, on_close=_panel_closed,
                              catalog_provider=_statistik_catalog)
            panel_ref["win"] = pw
        panel_on.set(True)
        _panel_btn_open(True)
        _persist_visible(True)
        _resubscribe()
        return pw

    def _hide_panel():
        pw = panel_ref["win"]
        if pw is not None and pw.alive():
            pw.destroy()  # borderless: destroy is the reliable "close" on any WM
        panel_ref["win"] = None
        panel_on.set(False)
        _panel_btn_open(False)
        _persist_visible(False)
        _resubscribe()

    def _toggle_panel():
        pw = panel_ref["win"]
        if pw is not None and pw.alive():
            _hide_panel()
        else:
            _show_panel()

    # Restore the var selection saved from the last session (before wiring buttons).
    for _saved in load_statistik_selection():
        add_var(
            gui_catalog.CatalogVar(
                name=_saved["name"], kind=_saved["kind"],
                unit=_saved.get("unit", ""), category="",
            ),
            persist=False,
        )

    def _statistik_catalog():
        # Base A:/K:/L: catalog + the current profile's own V: vars, read fresh so
        # a just-declared virtual shows up in the picker without a restart.
        lvs = []
        with contextlib.suppress(Exception):
            lvs = load_profile(profiles_dir(root_dir)
                               / f"{profile_var.get()}.yaml").local_vars
        return catalog + gui_catalog.local_var_catalog(lvs)

    sbtn = ttk.Frame(stab)
    sbtn.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(2, 4))
    b_add = ttk.Button(sbtn, text=tr("Variablen in die Liste holen"), style="Success.TButton",
                       command=lambda: _open_var_picker(win, _statistik_catalog(), add_var))
    b_rm = ttk.Button(sbtn, text=tr("Variablen aus Liste entfernen"), style="Danger.TButton",
                      command=remove_selected)
    b_toggle = ttk.Button(sbtn, textvariable=panel_btn_text, style="Accent.TButton",
                          command=_toggle_panel)
    panel_btn["w"] = b_toggle
    b_add.pack(side="left")
    b_rm.pack(side="left", padx=6)
    b_toggle.pack(side="left", padx=6)
    mon_state = ttk.Label(sbtn, text=tr(""), foreground="#666")
    mon_state.pack(side="right")
    _attach_tooltip(b_add, tr("Popup: nach Typ (A:/K:/L:/V:) filtern + Namen suchen"))
    _attach_tooltip(b_toggle, tr("Loslösbares Kachel-Panel öffnen/schließen (mit eigenem Picker)"))

    # --- V: overview: declare / remove the profile's own virtual variables --- #
    # Sits below the value table. Values live in the bridge's V: hub (seeded with
    # `initial` at mapper start); declared vars show up in every var-picker.
    vfr = ttk.Labelframe(stab, text=tr("Eigene V:-Variablen (Bridge-Hub, sim-unabhängig)"),
                         padding=6)
    vfr.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(10, 0))
    v_list = ttk.Treeview(vfr, columns=("initial", "desc"), show="tree headings",
                          height=4, selectmode="browse")
    v_list.heading("#0", text=tr("Name (V:…)"))
    v_list.column("#0", width=180, anchor="w")
    v_list.heading("initial", text=tr("Startwert"))
    v_list.column("initial", width=80, anchor="w")
    v_list.heading("desc", text=tr("Beschreibung"))
    v_list.column("desc", width=320, anchor="w")
    v_list.pack(fill="x")
    vrow = ttk.Frame(vfr)
    vrow.pack(anchor="w", pady=(6, 0))
    v_name, v_init, v_desc = tk.StringVar(), tk.StringVar(value="0"), tk.StringVar()
    ttk.Label(vrow, text=tr("Name")).pack(side="left")
    ttk.Entry(vrow, textvariable=v_name, width=16).pack(side="left", padx=(2, 8))
    ttk.Label(vrow, text=tr("Startwert")).pack(side="left")
    ttk.Entry(vrow, textvariable=v_init, width=7).pack(side="left", padx=(2, 8))
    ttk.Label(vrow, text=tr("Beschreibung")).pack(side="left")
    ttk.Entry(vrow, textvariable=v_desc, width=22).pack(side="left", padx=(2, 8))
    v_status = ttk.Label(vfr, text=tr(""), foreground=MUTED)
    v_status.pack(anchor="w", pady=(4, 0))

    def _vlist_load(*_):
        v_list.delete(*v_list.get_children())
        try:
            prof = load_profile(profiles_dir(root_dir) / f"{profile_var.get()}.yaml")
        except Exception:
            return
        for lv in prof.local_vars:
            v_list.insert("", "end", iid=lv.name, text=f"V:{lv.name}",
                          values=(f"{lv.initial:g}", lv.description))

    def _vlist_save(local_vars):
        path = profiles_dir(root_dir) / f"{profile_var.get()}.yaml"
        try:
            data = profile_writer.load(path)
            profile_writer.set_local_vars(data, local_vars)
            profile_writer.validate(data)
            profile_writer.dump(data, path)
            v_status.config(text=tr("Gespeichert") + " ✓", foreground="#15803d")
        except Exception as exc:
            v_status.config(text=f"{tr('dialog.error')}: {exc}", foreground=DANGER)
        _vlist_load()

    def _vlist_current():
        try:
            return _local_vars_as_dicts(
                load_profile(profiles_dir(root_dir) / f"{profile_var.get()}.yaml"))
        except Exception:
            return []

    def _vlist_add():
        name = v_name.get().strip()
        if not name:
            v_status.config(text=tr("Name fehlt."), foreground=DANGER)
            return
        try:
            initial = float(v_init.get() or 0)
        except ValueError:
            v_status.config(text=tr("Startwert muss eine Zahl sein."), foreground=DANGER)
            return
        entry: dict = {"name": name}
        if initial:
            entry["initial"] = initial
        if v_desc.get().strip():
            entry["description"] = v_desc.get().strip()
        kept = [lv for lv in _vlist_current() if lv["name"] != name]
        _vlist_save([*kept, entry])
        v_name.set("")
        v_desc.set("")

    def _vlist_remove():
        sel = v_list.selection()
        if not sel:
            v_status.config(text=tr("Erst eine V:-Variable markieren."), foreground=DANGER)
            return
        _vlist_save([lv for lv in _vlist_current() if lv["name"] != sel[0]])

    ttk.Button(vrow, text=tr("Anlegen"), style="Accent.TButton",
               command=_vlist_add).pack(side="left", padx=(4, 4))
    ttk.Button(vrow, text=tr("Entfernen"), style="Danger.TButton",
               command=_vlist_remove).pack(side="left")
    profile_var.trace_add("write", _vlist_load)
    win.after(400, _vlist_load)  # deferred: load_profile is imported just below

    # ===== Mapper tab (device viewer + inline binding editor) ============== #
    from . import gui_mapper, panel_layout, profile_writer
    from .mapping.loader import load_device_catalog, load_profile

    mtab = ttk.Frame(nb, padding=10)
    nb.add(mtab, text=tr("tab.mapper"))
    mtab.rowconfigure(1, weight=1)
    mtab.columnconfigure(0, weight=1)  # device list
    mtab.columnconfigure(1, weight=2)  # detail

    mhdr = ttk.Frame(mtab)
    mhdr.grid(row=0, column=0, columnspan=3, sticky="ew")
    ttk.Label(mhdr, text=tr("Geräte im Profil — was ist worauf gemappt:")).pack(side="left")
    m_state = ttk.Label(mhdr, text=tr(""), foreground="#666")
    m_state.pack(side="right")
    # View toggle: the detail table, or a panel *reconstruction* (switches/LEDs at
    # ~their physical position). Non-destructive — flips which of the two shares
    # the right-hand cell. Text flips with the mode; wired below where the canvas
    # and its renderer are defined.
    view_btn = ttk.Button(mhdr, text=tr("Nachbau"),
                          command=lambda: _toggle_view())
    view_btn.pack(side="right", padx=(0, 8))
    _attach_tooltip(view_btn, tr("Zwischen Tabelle und Panel-Nachbau umschalten "
                                 "(Schalter/LEDs an ihrer physischen Position)."))

    # left: one row per catalog device (bus, connected?, #bindings, #outputs)
    dev_tree = ttk.Treeview(mtab, columns=("bus", "status", "b", "o"),
                            show="tree headings", height=7, selectmode="browse")
    dev_tree.heading("#0", text=tr("Gerät"))
    dev_tree.column("#0", width=170, anchor="w")
    for col, head, w in (("bus", "Bus", 58), ("status", "Status", 96),
                         ("b", "Bind", 42), ("o", "Out", 38)):
        dev_tree.heading(col, text=head)
        dev_tree.column(col, width=w, anchor="center")
    dev_tree.grid(row=1, column=0, sticky="nsew", pady=6, padx=(0, 8))

    # right: bindings + outputs of the selected device. Double-click on a
    # binding/output row opens its settings window (per user: no extra edit
    # button, and single click must only select). The trailing Live column
    # mirrors the hardware while the device is attached: pressed buttons
    # show ●, axes a filling bar — so you can find a control fast.
    detail = ttk.Treeview(mtab, columns=("source", "action", "shape", "live"),
                          show="tree headings", height=7)
    detail.heading("#0", text=tr("Name"))
    detail.column("#0", width=150, anchor="w")
    for col, head, w in (("source", "Control", 92), ("action", "Aktion", 232),
                         ("shape", "Shaping", 100)):
        detail.heading(col, text=head)
        detail.column(col, width=w, anchor="w")
    detail.heading("live", text=tr("Live"))
    detail.column("live", width=118, anchor="w", stretch=False)
    detail.grid(row=1, column=1, sticky="nsew", pady=6)
    dsb = ttk.Scrollbar(mtab, orient="vertical", command=detail.yview)
    dsb.grid(row=1, column=2, sticky="ns", pady=6)
    detail.configure(yscrollcommand=dsb.set)

    # Panel reconstruction: a canvas sharing the detail's cell (shown instead of
    # the table in "panel" view). Elements are drawn from the pure panel_layout;
    # `pcanvas` maps canvas items back to elements for click->editor + the live
    # switch overlay. Starts hidden (grid_remove) — the table is the default view.
    panel_canvas = tk.Canvas(mtab, background=SURFACE, highlightthickness=1,
                             highlightbackground="#d1d5db")
    panel_canvas.grid(row=1, column=1, sticky="nsew", pady=6)
    panel_canvas.grid_remove()
    # Vertical scrollbar for tall reconstructions (radio panel scrolls row by row).
    panel_vsb = ttk.Scrollbar(mtab, orient="vertical", command=panel_canvas.yview)
    panel_vsb.grid(row=1, column=2, sticky="ns", pady=6)
    panel_vsb.grid_remove()
    panel_canvas.configure(yscrollcommand=panel_vsb.set)
    pcanvas: dict = {"by_index": {}, "live": {}, "device": None, "hint": None}

    # discovery is lazy (only when the tab is first shown) so startup stays fast.
    mstate: dict[str, object] = {"present": None, "discovered": False, "profile": None,
                                 "view": "panel"}  # reconstruction is the default view

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

    # Row 2 splits by scope so it's clear what each button acts on: DEVICE actions
    # under the device list (col 0); BINDING actions right-aligned directly under
    # the bindings table (col 1), distinct from the profile buttons in the top row.
    devbtn = ttk.Frame(mtab)
    devbtn.grid(row=2, column=0, sticky="w", pady=(6, 0))
    b_rescan = ttk.Button(devbtn, text=tr("Geräte neu erkennen"),
                          command=lambda: _mapper_reload(rediscover=True))
    b_rescan.pack(side="left")
    _attach_tooltip(b_rescan, tr("evdev + hidraw discovery — welche Geräte hängen jetzt dran"))

    bindbtn = ttk.Frame(mtab)
    bindbtn.grid(row=2, column=1, columnspan=2, sticky="ew", pady=(6, 0))
    # Packed right-to-left so they sit right-aligned under the table they act
    # on (per user: '+ Panel' creates content in THIS list, so it lives here):
    # + Panel  + Binding  Duplizieren  Entfernen
    ttk.Button(bindbtn, text=tr("Entfernen"), style="Danger.TButton",
               command=lambda: _remove_selected_row()).pack(side="right")
    ttk.Button(bindbtn, text=tr("Duplizieren"),
               command=lambda: _ed_duplicate()).pack(side="right", padx=6)
    ttk.Button(bindbtn, text=tr("+ Binding"), command=lambda: _new_binding()).pack(side="right")
    b_addpanel = ttk.Menubutton(bindbtn, text=tr("+ Saitek-Panel"))
    b_addpanel.pack(side="right", padx=6)
    _attach_tooltip(b_addpanel,
                    tr("Neuen Panel-Controller anlegen — nur für Saitek-Panels (hidraw) "
                    "und nur nötig, wenn das Profil das Panel noch gar nicht kennt. "
                    "Details danach über die Baum-Zeilen einstellen."))
    addpanel_menu = tk.Menu(b_addpanel, tearoff=0)

    def _add_panel(template_name):
        dev = _sel(dev_tree)
        if dev is None:
            m_state.config(text=tr("Kein Gerät gewählt — links ein Gerät markieren."))
            return
        cat_ = _device_catalog()
        ddef = cat_.by_id(dev) if cat_ else None
        if ddef is None or ddef.transport != "hidraw":
            m_state.config(text=f"„{dev}“ ist kein Panel — Panel-Controller gibt es "
                                "nur für die Saitek-Panels (hidraw).")
            return
        tpl = gui_mapper.OUTPUT_BLOCK_TEMPLATES[template_name]
        _edit_profile(lambda d: profile_writer.add_output(d, dev, dict(tpl)),
                      f"Panel-Block angelegt ({tpl['type']}) ✓")

    for _tname in gui_mapper.OUTPUT_BLOCK_TEMPLATES:
        addpanel_menu.add_command(label=_tname,
                                  command=lambda t=_tname: _add_panel(t))
    b_addpanel.configure(menu=addpanel_menu)
    ttk.Label(bindbtn, text=tr("Doppelklick auf eine Zeile öffnet den Editor · "
                            "Entfernen wirkt auf die markierte Zeile"),
              foreground="#666").pack(side="left")

    # --- editor: a separate, on-demand window (opened per element) -------- #
    # A ⚙-per-row / double-click / "Bearbeiten…" opens this Toplevel with the full
    # parameter set for one element; it is created hidden and shown on demand.
    ed_win = tk.Toplevel(win)
    ed_win.title("Binding bearbeiten")
    ed_win.withdraw()
    ed_win.transient(win)
    ed_win.protocol("WM_DELETE_WINDOW", lambda: _ed_close())
    ed = ttk.Frame(ed_win, padding=10)
    ed.pack(fill="both", expand=True)
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
        # detent split: the second (below-detent) mapping slot of an axis binding
        "sp_enabled": tk.BooleanVar(), "sp_at": tk.StringVar(),
        "sp_action_type": tk.StringVar(value="event"),
        "sp_ev_event": tk.StringVar(), "sp_ev_value": tk.StringVar(),
        "sp_sv_simvar": tk.StringVar(), "sp_sv_unit": tk.StringVar(),
        "sp_sv_invert": tk.BooleanVar(),
        "sp_efv_read": tk.StringVar(), "sp_efv_event": tk.StringVar(),
        "sp_efv_unit": tk.StringVar(), "sp_rpn_code": tk.StringVar(),
        "sp_tf_deadzone": tk.StringVar(), "sp_tf_curve": tk.StringVar(),
        "sp_tf_expo": tk.StringVar(), "sp_tf_invert": tk.BooleanVar(),
        "sp_tf_out_min": tk.StringVar(), "sp_tf_out_max": tk.StringVar(),
    }
    # hat: four direction slots (type follows the picked var, like everywhere)
    for _d, _sym in gui_mapper.HAT_DIRECTIONS:
        ev[f"hat_{_d}_type"] = tk.StringVar(value="event")
        ev[f"hat_{_d}_name"] = tk.StringVar()
        ev[f"hat_{_d}_value"] = tk.StringVar()

    def _var_catalog():
        extra = gui_catalog.local_var_catalog(mstate["profile"].local_vars) \
            if mstate["profile"] is not None else []
        return catalog + extra

    def _var_name(v):  # CatalogVar -> the string the engine/writer expect
        return (v.kind + v.name) if v.kind in ("L:", "V:") else v.name

    def _pick_into(var):
        _open_var_picker(win, _var_catalog(), lambda v: var.set(_var_name(v)))

    def _pick_seq_step(st):
        """Pick a sequence step's target — its event/simvar kind follows the var."""
        def on_pick(v):
            st["target"].set("event" if v.kind == "K:" else "simvar")
            st["name"].set(_var_name(v))
            _seq_render()  # refresh the row's grey kind label
        _open_var_picker(win, _var_catalog(), on_pick)

    def _pick_action():
        """Pick a variable and let it drive the action type (K:=event, else simvar).

        This is the main path: the user just picks from the filtered list and does
        not have to understand the event/simvar distinction (that follows the kind).
        """
        def on_pick(v):
            if v.kind == "K:":
                ev["action_type"].set("event")
                ev["ev_event"].set(_var_name(v))
            else:  # A: / L: / V: -> set a SimVar/LVar/virtual var
                ev["action_type"].set("simvar")
                ev["sv_simvar"].set(_var_name(v))
            _ed_show_fields()
        _open_var_picker(win, _var_catalog(), on_pick)

    def _info(parent, text):
        lbl = ttk.Label(parent, text=tr("ⓘ"), foreground="#1565c0", cursor="question_arrow")
        lbl.pack(side="left", padx=(0, 8))
        _attach_tooltip(lbl, text)

    # row 0: name
    ttk.Label(ed, text=tr("Name")).grid(row=0, column=0, sticky="w", padx=(0, 6), pady=2)
    ttk.Entry(ed, textvariable=ev["name"]).grid(row=0, column=1, columnspan=2, sticky="ew", pady=2)

    # row 1: source (kind + code + learn). The kind is NOT a free choice — it must
    # match the physical control (else the binding never fires), so the dropdown
    # speaks German and an ⓘ explains the one distinction that matters
    # (Taster fires on press; a maintained Schalter reports on AND off).
    _KIND_CHOICES = (
        ("axis", "Achse (Hebel/Drehregler)"),
        ("button", "Taster (feuert beim Drücken)"),
        ("switch", "Schalter (haltend, meldet Ein+Aus)"),
        ("hat", "Hat (Rundblick-Kreuz)"),
    )
    _kind_label = dict(_KIND_CHOICES)
    _kind_of_label = {label: k for k, label in _KIND_CHOICES}
    kind_disp = tk.StringVar()
    ev["kind"].trace_add(
        "write", lambda *_: kind_disp.set(_kind_label.get(ev["kind"].get(), ev["kind"].get()))
    )
    ttk.Label(ed, text=tr("Quelle")).grid(row=1, column=0, sticky="w", padx=(0, 6), pady=2)
    k1 = ttk.Frame(ed)
    k1.grid(row=1, column=1, sticky="w", pady=2)
    kind_cb = ttk.Combobox(k1, textvariable=kind_disp,
                           values=[label for _, label in _KIND_CHOICES],
                           state="readonly", width=28)
    kind_cb.pack(side="left", padx=(0, 4))
    _info(k1, "Muss zum physischen Bedienelement passen, sonst reagiert das Binding nicht: "
              "Achse = Hebel/Drehachse · Taster = Druckknopf (löst beim Drücken aus) · "
              "Schalter = haltender Kippschalter (meldet Einschalten UND Ausschalten — "
              "alle Saitek-Panel-Schalter) · Hat = Rundblick-Kreuz am Yoke.")
    srcfr = ttk.Frame(ed)
    srcfr.grid(row=1, column=2, sticky="w")
    ttk.Label(srcfr, text=tr("Code")).pack(side="left", padx=(0, 4))
    ttk.Entry(srcfr, textvariable=ev["code"], width=8).pack(side="left")
    # capture buttons are a wordless magic wand (user wish: 🪄, no "Lernen" label)
    b_learn = ttk.Button(srcfr, text=tr("🪄"), width=3, command=lambda: _learn_code())
    b_learn.pack(side="left", padx=6)
    _attach_tooltip(b_learn, tr("Bedienelement anlernen: lauscht live am angeschlossenen Gerät des "
                    "Bindings — gewünschten Knopf/Schalter EINMAL betätigen oder den Hebel "
                    "deutlich bewegen, dann werden Art (Taster/Schalter/Achse/Hat) und Code "
                    "erkannt und oben eingetragen.\n\nFunktioniert für Achsen-Hardware (evdev) "
                    "UND die Saitek-Panels (hidraw). Voraussetzung: das Gerät hängt am USB."))

    # row 2: action — ONE button. Pick from the list and everything follows the
    # picked kind: a K: entry fires that event, an A:/L:/V: entry sets that
    # variable; the user never chooses event-vs-simvar by hand (a grey note names
    # what will happen). "Mehrschritt" turns the action into a sequence (steps
    # edited below). RPN / event_from_var have NO create path here — they only
    # show up (read-only-ish, with an ⓘ) when the opened binding already uses them.
    _TYPE_NOTE = {
        "event": "→ Event feuern", "simvar": "→ Variable setzen",
        "event_from_var": "→ Spezial: Event aus Variable", "rpn": "→ Spezial: RPN",
        "sequence": "→ Schritte s. unten",
    }
    act_lbl = ttk.Label(ed, text=tr("Aktion"))
    act_lbl.grid(row=2, column=0, sticky="w", padx=(0, 6), pady=2)
    a1 = ttk.Frame(ed)
    a1.grid(row=2, column=1, sticky="w", pady=2)
    ttk.Button(a1, text=tr("Wählen…"), style="Accent.TButton",
               command=lambda: _pick_action()).pack(side="left", padx=(0, 4))
    _info(a1, "Aus der Liste wählen (oben nach A:/K:/L:/V: filtern). Was du wählst, bestimmt "
              "automatisch, was beim Auslösen passiert: ein K:-Event wird gefeuert, eine "
              "A:/L:/V:-Variable gesetzt — den Unterschied musst du nicht kennen.")
    type_note = ttk.Label(a1, text=tr(""), foreground="#666")
    type_note.pack(side="left", padx=(0, 8))
    seq_on = tk.BooleanVar(value=False)
    ttk.Checkbutton(a1, text=tr("Mehrschritt"), variable=seq_on,
                    command=lambda: _seq_toggle()).pack(side="left")
    _info(a1, "Mehrere Schritte je Flanke ausführen (z. B. beim Einschalten gleich mehrere "
              "Events/Variablen setzen) — die Schritte unten bearbeiten.")
    afh = ttk.Frame(ed)
    afh.grid(row=2, column=2, sticky="ew", pady=2)
    af: dict = {}
    fe = ttk.Frame(afh)
    ttk.Label(fe, text=tr("Event")).pack(side="left")
    ttk.Entry(fe, textvariable=ev["ev_event"], width=24,
              state="readonly").pack(side="left", padx=4)
    ttk.Label(fe, text=tr("Wert")).pack(side="left", padx=(8, 0))
    ttk.Entry(fe, textvariable=ev["ev_value"], width=6).pack(side="left", padx=(4, 2))
    _info(fe, "Leer = automatisch: ein Taster sendet 1 beim Drücken, ein Schalter seinen "
              "Zustand (1/0), eine Achse ihren Ausgangs-Wert. Eine Zahl hier erzwingt "
              "stattdessen immer genau diesen festen Wert.")
    af["event"] = fe
    fs = ttk.Frame(afh)
    ttk.Label(fs, text=tr("SimVar")).pack(side="left")
    ttk.Entry(fs, textvariable=ev["sv_simvar"], width=24,
              state="readonly").pack(side="left", padx=4)
    ttk.Label(fs, text=tr("Unit")).pack(side="left", padx=(8, 0))
    ttk.Entry(fs, textvariable=ev["sv_unit"], width=8).pack(side="left", padx=4)
    ttk.Checkbutton(fs, text=tr("invert"), variable=ev["sv_invert"]).pack(side="left", padx=6)
    af["simvar"] = fs
    ff = ttk.Frame(afh)
    _info(ff, "Spezialfall „Event aus Variable“: liest beim Auslösen die Read-Variable "
              "und feuert das Event mit deren Wert (z. B. Flaps-Stufe aus einer LVar).")
    ttk.Label(ff, text=tr("Read")).pack(side="left")
    ttk.Entry(ff, textvariable=ev["efv_read"], width=16,
              state="readonly").pack(side="left", padx=4)
    ttk.Button(ff, text=tr("…"), width=2,
               command=lambda: _pick_into(ev["efv_read"])).pack(side="left")
    ttk.Label(ff, text=tr("Event")).pack(side="left", padx=(8, 0))
    ttk.Entry(ff, textvariable=ev["efv_event"], width=16,
              state="readonly").pack(side="left", padx=4)
    ttk.Button(ff, text=tr("…"), width=2,
               command=lambda: _pick_into(ev["efv_event"])).pack(side="left")
    af["event_from_var"] = ff
    fr = ttk.Frame(afh)
    _info(fr, "RPN = Rechenausdruck (MobiFlight-Kalkulator) für Spezialfälle, z. B. eine "
              "LVar umschalten: (L:X) ! (>L:X). Nur für Fortgeschrittene — im Normalfall "
              "einfach „Wählen…“ benutzen.")
    ttk.Label(fr, text=tr("RPN")).pack(side="left")
    ttk.Entry(fr, textvariable=ev["rpn_code"], width=40).pack(side="left", padx=4)
    af["rpn"] = fr
    fq = ttk.Frame(afh)
    ttk.Label(fq, text=tr("mehrere Schritte je Flanke — unten bearbeiten ↓"),
              foreground="#444").pack(side="left")
    af["sequence"] = fq

    # row 3: axis shaping — stacked rows (Eingang / Verarbeitung / Ausgang) so the
    # window stays narrow; min/max labels are consistent on input AND output. The
    # detent split lives below as its own clearly-separated second mapping area.
    axfr = ttk.Frame(ed)
    axfr.grid(row=3, column=0, columnspan=3, sticky="ew", pady=2)

    cal_hint = tk.StringVar(value="")
    inrow = ttk.Frame(axfr)
    inrow.pack(anchor="w")
    ttk.Label(inrow, text=tr("Eingang (roh)")).pack(side="left", padx=(0, 2))
    _info(inrow,
          "Roh-Wertebereich der Hardware, den dieses Binding nutzt. Leer = der kalibrierte "
          "Bereich der Achse (steht rechts in grau). Roh-Werte außerhalb min…max werden "
          "geklemmt.")
    ttk.Label(inrow, text=tr("min")).pack(side="left")
    ttk.Entry(inrow, textvariable=ev["raw_min"], width=7).pack(side="left", padx=(2, 8))
    ttk.Label(inrow, text=tr("max")).pack(side="left")
    ttk.Entry(inrow, textvariable=ev["raw_max"], width=7).pack(side="left", padx=(2, 8))
    b_wand_raw = ttk.Button(inrow, text=tr("🪄"), width=3, command=lambda: _learn_raw())
    b_wand_raw.pack(side="left")
    _attach_tooltip(b_wand_raw,
                    tr("Öffnet ein Live-Fenster, das den ROHWERT dieser Achse direkt vom "
                    "angeschlossenen Gerät liest (evdev) — gelesen wird die Achse aus dem "
                    "Code-Feld oben am Gerät dieses Bindings.\n\n"
                    "Voraussetzung VORHER: Quelle = Achse, der Code stimmt und das Gerät "
                    "hängt am USB. Dann Hebel bewegen: der aktuelle Rohwert erscheint live "
                    "und lässt sich per Knopf als Eingang-min, Eingang-max oder Detent "
                    "übernehmen. Es wird nichts gesendet — nur gelesen."))
    ttk.Label(inrow, textvariable=cal_hint, foreground="#666").pack(side="left", padx=(4, 0))

    def _tf_rows(parent, p):
        """Verarbeitung + Ausgang rows for one transform slot (p = tf_/sp_tf_)."""
        procrow = ttk.Frame(parent)
        procrow.pack(anchor="w", pady=(2, 0))
        ttk.Label(procrow, text=tr("Verarbeitung")).pack(side="left", padx=(0, 2))
        _info(procrow,
              "Pipeline: Roh → auf -1…1 normieren (Eingang min/max) → Deadzone → Kurve/Expo "
              "→ invert → auf Ausgang min…max skalieren → an Event/SimVar.")
        ttk.Label(procrow, text=tr("dz")).pack(side="left")
        ttk.Entry(procrow, textvariable=ev[p + "deadzone"],
                  width=5).pack(side="left", padx=(2, 2))
        _info(procrow, "Deadzone (0…1): kleine Auslenkung um die Mitte ignorieren — gegen "
                       "Zittern/Drift der Mittelstellung. Leer = 0 (aus).")
        ttk.Label(procrow, text=tr("Kurve")).pack(side="left")
        ttk.Combobox(procrow, textvariable=ev[p + "curve"], values=list(gui_mapper.CURVES),
                     state="readonly", width=8).pack(side="left", padx=(2, 2))
        _info(procrow, "Kennlinie: linear (1:1), expo (weicher/feiner um die Mitte) "
                       "oder squared.")
        ttk.Label(procrow, text=tr("expo")).pack(side="left")
        ttk.Entry(procrow, textvariable=ev[p + "expo"], width=5).pack(side="left", padx=(2, 2))
        _info(procrow, "Stärke der Expo-Kurve (0…1): höher = weicher um die Mitte, spitzer "
                       "an den Enden. Nur bei Kurve=expo wirksam. Leer = 0.")
        ttk.Checkbutton(procrow, text=tr("invert"),
                        variable=ev[p + "invert"]).pack(side="left", padx=(0, 2))
        _info(procrow, "Richtung umkehren (Achse läuft andersherum).")
        outrow = ttk.Frame(parent)
        outrow.pack(anchor="w", pady=(2, 0))
        ttk.Label(outrow, text=tr("Ausgang (out)")).pack(side="left", padx=(0, 2))
        _info(outrow, "Wertebereich, der an Event/SimVar geht: min wird bei Eingang-min "
                      "gesendet, max bei Eingang-max. Leer = 0…1. Achsen-*_SET-Events "
                      "brauchen meist -16383…16383, ein SimVar oft 0…1.")
        ttk.Label(outrow, text=tr("min")).pack(side="left")
        ttk.Entry(outrow, textvariable=ev[p + "out_min"],
                  width=7).pack(side="left", padx=(2, 8))
        ttk.Label(outrow, text=tr("max")).pack(side="left")
        ttk.Entry(outrow, textvariable=ev[p + "out_max"],
                  width=7).pack(side="left", padx=(2, 2))

    _tf_rows(axfr, "tf_")

    # Detent split: ONE binding, two ranges. Enabling it opens a clearly separated
    # second mapping area for the range below the detent (its own action+shaping).
    sprow = ttk.Frame(axfr)
    sprow.pack(anchor="w", pady=(6, 0))
    ttk.Checkbutton(sprow, text=tr("Achse am Detent teilen"), variable=ev["sp_enabled"],
                    command=lambda: _ed_show_fields()).pack(side="left")
    _info(sprow, "Für Hebel mit Raste (Reverse/Feather/Cutoff): oberhalb des Detents gilt "
                 "die Aktion oben, unterhalb eine EIGENE Aktion — beides in EINEM Binding. "
                 "Jeder Teilbereich wird über seine eigene Spanne skaliert (der Detent ist "
                 "Ausgang-min des oberen und Ausgang-max des unteren Teils).")
    ttk.Label(sprow, text=tr("Detent (roh)")).pack(side="left", padx=(8, 0))
    ttk.Entry(sprow, textvariable=ev["sp_at"], width=7).pack(side="left", padx=(2, 2))
    b_wand_det = ttk.Button(sprow, text=tr("🪄"), width=3, command=lambda: _learn_raw())
    b_wand_det.pack(side="left", padx=(2, 0))
    _attach_tooltip(b_wand_det,
                    tr("Detent anlernen: liest den Rohwert der Achse live vom angeschlossenen "
                    "Gerät (evdev, Achse = Code-Feld oben). Voraussetzung: Quelle = Achse, "
                    "Code stimmt, Gerät angesteckt. Hebel an die Raste fahren und den "
                    "angezeigten Wert mit „→ als Detent“ übernehmen."))
    _info(sprow, "Roh-Wert der Raste = Grenze der beiden Bereiche — per 🪄 live ablesbar.")

    spfr = ttk.Labelframe(axfr, text=tr("⬇ Unterhalb des Detents — eigene Aktion"), padding=6)
    sp1 = ttk.Frame(spfr)
    sp1.pack(anchor="w")
    ttk.Button(sp1, text=tr("Wählen…"), style="Accent.TButton",
               command=lambda: _pick_sp_action()).pack(side="left", padx=(0, 4))
    sp_note = ttk.Label(sp1, text=tr(""), foreground="#666")
    sp_note.pack(side="left", padx=(0, 8))
    spah = ttk.Frame(sp1)
    spah.pack(side="left")
    spf: dict = {}
    sfe = ttk.Frame(spah)
    ttk.Label(sfe, text=tr("Event")).pack(side="left")
    ttk.Entry(sfe, textvariable=ev["sp_ev_event"], width=24,
              state="readonly").pack(side="left", padx=4)
    ttk.Label(sfe, text=tr("Wert")).pack(side="left", padx=(8, 0))
    ttk.Entry(sfe, textvariable=ev["sp_ev_value"], width=6).pack(side="left", padx=(4, 2))
    _info(sfe, "Leer = automatisch: die Achse sendet ihren Ausgangs-Wert (s. Ausgang unten).")
    spf["event"] = sfe
    sfs = ttk.Frame(spah)
    ttk.Label(sfs, text=tr("SimVar")).pack(side="left")
    ttk.Entry(sfs, textvariable=ev["sp_sv_simvar"], width=24,
              state="readonly").pack(side="left", padx=4)
    ttk.Label(sfs, text=tr("Unit")).pack(side="left", padx=(8, 0))
    ttk.Entry(sfs, textvariable=ev["sp_sv_unit"], width=8).pack(side="left", padx=4)
    ttk.Checkbutton(sfs, text=tr("invert"), variable=ev["sp_sv_invert"]).pack(side="left", padx=6)
    spf["simvar"] = sfs
    sfr = ttk.Frame(spah)
    _info(sfr, "RPN = Rechenausdruck für Spezialfälle (nur wenn schon im Profil so angelegt).")
    ttk.Label(sfr, text=tr("RPN")).pack(side="left")
    ttk.Entry(sfr, textvariable=ev["sp_rpn_code"], width=36).pack(side="left", padx=4)
    spf["rpn"] = sfr
    _tf_rows(spfr, "sp_tf_")

    # row 4: sequence step editor (only visible when action type = sequence).
    # A sequence fires several writes per edge — on_edge on press/switch-on,
    # off_edge on release. Each step fires an event OR sets a SimVar/LVar.
    seqfr = ttk.Frame(ed)
    seqfr.grid(row=4, column=0, columnspan=3, sticky="ew", pady=2)
    seq_state: dict[str, list] = {"on": [], "off": []}  # each item: dict of StringVars

    def _seq_step_vars(target="event", name="", value="0", unit="number"):
        return {"target": tk.StringVar(value=target), "name": tk.StringVar(value=name),
                "value": tk.StringVar(value=value), "unit": tk.StringVar(value=unit)}

    def _seq_rows(edge):
        return [{k: v.get() for k, v in st.items()} for st in seq_state[edge]]

    def _seq_add(edge):
        seq_state[edge].append(_seq_step_vars())
        _seq_render()

    def _seq_del(edge, index):
        del seq_state[edge][index]
        _seq_render()

    def _seq_render():
        for w in seqfr.winfo_children():
            w.destroy()
        ttk.Label(seqfr, foreground="#444",
                  text=tr("Sequence — mehrere Schritte je Flanke (Event feuern / SimVar setzen):")
                  ).pack(anchor="w")
        for edge, title in (("on", "Beim Einschalten / Drücken (on)"),
                            ("off", "Beim Ausschalten (off) — leer = momentan")):
            head = ttk.Frame(seqfr)
            head.pack(anchor="w", pady=(4, 0))
            ttk.Label(head, text=title, foreground="#555").pack(side="left")
            ttk.Button(head, text=tr("+ Schritt"),
                       command=lambda e=edge: _seq_add(e)).pack(side="left", padx=6)
            for i, st in enumerate(seq_state[edge]):
                row = ttk.Frame(seqfr)
                row.pack(anchor="w", padx=(16, 0))
                # target follows the picked var (K:=event else simvar) — no dropdown
                ttk.Label(row, width=9, foreground="#666",
                          text=tr("Event") if st["target"].get() == "event" else "Variable"
                          ).pack(side="left")
                ttk.Entry(row, textvariable=st["name"], width=26,
                          state="readonly").pack(side="left", padx=3)
                ttk.Button(row, text=tr("…"), width=2,
                           command=lambda s=st: _pick_seq_step(s)).pack(side="left")
                ttk.Label(row, text=tr("Wert")).pack(side="left", padx=(6, 0))
                ttk.Entry(row, textvariable=st["value"], width=7).pack(side="left", padx=3)
                ttk.Button(row, text=tr("✕"), width=2, style="Danger.TButton",
                           command=lambda e=edge, ix=i: _seq_del(e, ix)).pack(side="left")

    def _seq_load(action):
        rows = gui_mapper.seq_action_to_rows(action)
        seq_state["on"] = [_seq_step_vars(**r) for r in rows["on"]]
        seq_state["off"] = [_seq_step_vars(**r) for r in rows["off"]]
        _seq_render()

    def _seq_clear():
        seq_state["on"], seq_state["off"] = [], []
        _seq_render()

    # hat: four direction slots in ONE window (user wish) — the X/Y code pair
    # is automatic (Code = X/base, Y = base+1), each direction maps like the
    # main action (picker decides event vs simvar). Shown instead of the
    # action row while Quelle = Hat.
    hatfr = ttk.Frame(ed)
    hatfr.grid(row=2, column=1, columnspan=2, sticky="ew", pady=2)
    hh = ttk.Frame(hatfr)
    hh.pack(anchor="w")
    ttk.Label(hh, text=tr("Hat — vier Richtungen, ein Binding"),
              foreground="#444").pack(side="left")
    _info(hh, "Der Code oben ist die X-Achse des Hats (◀▶); die Y-Achse (▲▼) ist "
              "automatisch Code+1 — du musst nur den Basis-Code kennen (🪄 erkennt ihn "
              "beim Drücken des Hats). Je Richtung eine Aktion wählen; leere Richtungen "
              "tun nichts.")

    def _pick_hat(d):
        def on_pick(v):
            ev[f"hat_{d}_type"].set("event" if v.kind == "K:" else "simvar")
            ev[f"hat_{d}_name"].set(_var_name(v))
        _open_var_picker(win, _var_catalog(), on_pick)

    for _d, _sym in gui_mapper.HAT_DIRECTIONS:
        hrow = ttk.Frame(hatfr)
        hrow.pack(anchor="w", pady=1)
        ttk.Label(hrow, text=_sym, width=8).pack(side="left")
        ttk.Button(hrow, text=tr("Wählen…"),
                   command=lambda d=_d: _pick_hat(d)).pack(side="left", padx=(0, 4))
        ttk.Entry(hrow, textvariable=ev[f"hat_{_d}_name"], width=28,
                  state="readonly").pack(side="left")
        ttk.Label(hrow, text=tr("Wert")).pack(side="left", padx=(6, 0))
        ttk.Entry(hrow, textvariable=ev[f"hat_{_d}_value"], width=6
                  ).pack(side="left", padx=(2, 2))
        _info(hrow, "Nur bei Events: leer = 1 beim Auslösen; eine Zahl erzwingt diesen "
                    "festen Wert.")
        ttk.Button(hrow, text=tr("✕"), width=2,
                   command=lambda d=_d: (ev[f"hat_{d}_name"].set(""),
                                         ev[f"hat_{d}_value"].set(""))
                   ).pack(side="left", padx=4)

    # row 5: this window's actions (all act on THIS one binding) + feedback
    # conditions: a visually separated gate section (applies to EVERY source
    # kind) — per user: conditional settings must be recognisable at a glance.
    condfr = ttk.Labelframe(ed, text=tr("⚑ Bedingung — nur ausführen, wenn …"), padding=6)
    condfr.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(6, 2))
    cond_state: list[dict] = []

    def _cond_add(var="", op="==", value="1"):
        cond_state.append({"var": tk.StringVar(value=var), "op": tk.StringVar(value=op),
                           "value": tk.StringVar(value=value)})
        _cond_render()

    def _cond_del(index):
        del cond_state[index]
        _cond_render()

    def _cond_rows():
        return [{k: v.get() for k, v in row.items()} for row in cond_state]

    def _cond_render():
        for w in condfr.winfo_children():
            w.destroy()
        chead = ttk.Frame(condfr)
        chead.pack(anchor="w")
        ttk.Button(chead, text=tr("+ Bedingung"),
                   command=lambda: _cond_add()).pack(side="left", padx=(0, 4))
        _info(chead, "Das Binding löst nur aus, solange ALLE Bedingungen erfüllt sind — "
                     "geprüft gegen live gelesene Variablen (A:/L:) oder lokale "
                     "V:-Variablen. Solange ein Wert noch unbekannt ist, gilt die "
                     "Bedingung als NICHT erfüllt. Ohne Bedingungen läuft das Binding "
                     "immer.")
        if not cond_state:
            ttk.Label(chead, text=tr("keine — gilt immer"),
                      foreground="#666").pack(side="left", padx=4)
        for i, row in enumerate(cond_state):
            fr = ttk.Frame(condfr)
            fr.pack(anchor="w", pady=1)
            ttk.Button(fr, text=tr("Wählen…"),
                       command=lambda r=row: _pick_into(r["var"])).pack(side="left",
                                                                        padx=(0, 3))
            ttk.Entry(fr, textvariable=row["var"], width=28,
                      state="readonly").pack(side="left")
            ttk.Combobox(fr, textvariable=row["op"], values=list(gui_mapper.CONDITION_OPS),
                         state="readonly", width=4).pack(side="left", padx=3)
            ttk.Entry(fr, textvariable=row["value"], width=8).pack(side="left")
            ttk.Button(fr, text=tr("✕"), width=2, style="Danger.TButton",
                       command=lambda ix=i: _cond_del(ix)).pack(side="left", padx=4)

    def _cond_load(when):
        cond_state.clear()
        for r in gui_mapper.conditions_to_rows(when):
            _cond_add(r["var"], r["op"], r["value"])
        _cond_render()

    _cond_render()

    edbtn = ttk.Frame(ed)
    edbtn.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(6, 0))
    ttk.Button(edbtn, text=tr("Übernehmen"), style="Accent.TButton",
               command=lambda: _ed_apply()).pack(side="left")
    ttk.Button(edbtn, text=tr("Zurücksetzen"),
               command=lambda: _ed_reset()).pack(side="left", padx=6)
    ttk.Button(edbtn, text=tr("Abbrechen"), command=lambda: _ed_close()).pack(side="left")
    ed_status = ttk.Label(edbtn, text=tr(""), foreground="#666")
    ed_status.pack(side="left", padx=10)

    def _ed_status(msg, error=False):
        ed_status.config(text=msg, foreground="#c62828" if error else "#2e7d32" if msg else "#666")

    def _learn_code():
        """Listen to the binding's device and capture which control is actuated.

        Uses the same non-blocking live reader as the Live column: a button
        press shows up as an EV_KEY edge (-> Taster + code), a clear movement
        on an EV_ABS channel as an axis (hat when its range is the tiny ±1).
        The strongest recent change sticks until Übernehmen fills kind + code.
        """
        dev = etgt["device"]
        if dev is None:
            _ed_status("Erst ein Binding öffnen.", error=True)
            return
        opened = None
        is_panel = False
        with contextlib.suppress(Exception):
            from .devices import evdev_reader, hidraw_reader

            dcat = _device_catalog()
            ddef = dcat.by_id(dev) if dcat else None
            if ddef is not None and ddef.transport == "hidraw":
                is_panel = True
                path = hidraw_reader.discover(dcat).get(dev)
                opened = hidraw_reader.live_state_reader(path) if path else None
            else:
                path = evdev_reader.discover(dcat).get(dev) if dcat else None
                opened = evdev_reader.live_state_reader(path) if path else None
        if opened is None:
            _ed_status(f"„{dev}“ nicht live lesbar — Gerät angesteckt?", error=True)
            return
        reader, ranges = opened
        # Panels send no on-open snapshot, so their baseline is captured lazily from
        # the first frame (= the first flip); evdev state is seeded immediately.
        base = {"v": {} if is_panel else dict(reader() or {})}
        cap = tk.Toplevel(ed_win)
        cap.title(f"Anlernen — {dev}")
        cap.transient(ed_win)
        frm = ttk.Frame(cap, padding=12)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text=("Panel-Schalter EINMAL HIN UND ZURÜCK legen\n"
                             "(erst Baseline, dann steht der Code):"
                             if is_panel else
                             "Jetzt den gewünschten Knopf drücken\n"
                             "oder den Hebel deutlich bewegen:")).pack(anchor="w")
        found = tk.StringVar(value="— lausche —")
        ttk.Label(frm, textvariable=found,
                  font=("TkDefaultFont", 13, "bold")).pack(anchor="w", pady=6)
        st = {"kind": None, "code": None}
        _KIND_WORD = {"button": "Taster", "axis": "Achse", "hat": "Hat", "switch": "Schalter"}

        def _apply():
            if st["kind"] is None:
                return
            code = st["code"]
            if st["kind"] == "hat" and code % 2:
                code -= 1  # normalise to the hat's X (base) channel; Y = base+1
            ev["kind"].set(st["kind"])
            ev["code"].set(str(code))
            _ed_show_fields()
            _ed_status(f"Quelle angelernt: {_KIND_WORD[st['kind']]} {code} ✓")
            cap.destroy()

        btns = ttk.Frame(frm)
        btns.pack(anchor="w", pady=(8, 0))
        b_ok = ttk.Button(btns, text=tr("Übernehmen"), style="Accent.TButton",
                          command=_apply, state="disabled")
        b_ok.pack(side="left")
        ttk.Button(btns, text=tr("Schließen"), command=cap.destroy).pack(side="left", padx=6)

        def _tick():
            if not cap.winfo_exists():
                return
            state = reader()
            if state is None:
                found.set("Gerät getrennt.")
                return
            if is_panel and not base["v"]:  # panel: first frame is the baseline, no capture
                if state:
                    base["v"] = dict(state)
                    found.set("Baseline gesetzt — jetzt denselben Schalter ZURÜCK legen")
                cap.after(80, _tick)
                return
            b = base["v"]
            for (kind, code), val in state.items():
                if kind == "button":
                    if val and b.get((kind, code)) != val:
                        st.update(kind="button", code=code)
                elif kind == "switch":  # hidraw panel bit — either edge counts as a flip
                    if b.get((kind, code)) != val:
                        st.update(kind="switch", code=code)
                else:  # EV_ABS: axes and hats
                    lo, hi = ranges.get(code, (0, 255))
                    span = (hi - lo) or 1
                    # >= so a hat press (span ±1 -> delta exactly 1) registers too
                    if abs(val - b.get((kind, code), val)) >= max(span * 0.2, 1):
                        st.update(kind="hat" if span <= 2 else "axis", code=code)
            if st["kind"] is not None:
                found.set(f"{_KIND_WORD[st['kind']]} — Code {st['code']}")
                b_ok.config(state="normal")
            cap.after(80, _tick)

        _tick()
        cap.lift()

    def _learn_raw():
        """Live-capture window: read the axis and copy values into raw min/max.

        Poll the selected device's axis so the user can read the raw value at the
        detent / at the extremes and set it as min or max. Needs the device present
        (evdev); degrades gracefully otherwise.
        """
        dev = etgt["device"]
        if dev is None:
            _ed_status("Erst ein Achsen-Binding öffnen.", error=True)
            return
        try:
            code = int(str(ev["code"].get()).strip())
        except ValueError:
            _ed_status("Code ist keine Zahl.", error=True)
            return
        reader = None
        with contextlib.suppress(Exception):
            from .devices import evdev_reader

            dcat = _device_catalog()  # NOT `catalog` (that's the var catalog!)
            path = evdev_reader.discover(dcat).get(dev) if dcat else None
            reader = evdev_reader.axis_value_reader(path, code) if path else None
        if reader is None:
            _ed_status(f"Achse für „{dev}“ nicht live lesbar (Gerät an? evdev?).", error=True)
            return
        cap = tk.Toplevel(ed_win)
        cap.title(f"Achse anlernen — {dev} code {code}")
        cap.transient(ed_win)
        frm = ttk.Frame(cap, padding=12)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text=tr("Hebel/Achse bewegen — aktueller Rohwert:")).pack(anchor="w")
        cur = tk.StringVar(value="—")
        ttk.Label(frm, textvariable=cur, font=("TkDefaultFont", 18)).pack(anchor="w", pady=4)
        ttk.Label(frm, foreground="#666", wraplength=320, justify="left",
                  text=tr("Hebel an ein Ende / an die Raste fahren, Wert ablesen und übernehmen. "
                       "„als Detent“ füllt die Split-Grenze (Achse teilen).")).pack(anchor="w")
        st = {"val": None}

        _GRAB_LABEL = {"raw_min": "Eingang min", "raw_max": "Eingang max", "sp_at": "Detent"}

        def _grab(which):
            if st["val"] is not None:
                ev[which].set(str(st["val"]))
                _ed_status(f"{_GRAB_LABEL[which]} = {st['val']} übernommen ✓")

        btns = ttk.Frame(frm)
        btns.pack(anchor="w", pady=(8, 0))
        ttk.Button(btns, text=tr("→ als min"), command=lambda: _grab("raw_min")).pack(side="left")
        ttk.Button(btns, text=tr("→ als max"),
                   command=lambda: _grab("raw_max")).pack(side="left", padx=6)
        ttk.Button(btns, text=tr("→ als Detent"),
                   command=lambda: _grab("sp_at")).pack(side="left")
        ttk.Button(btns, text=tr("Schließen"), command=cap.destroy).pack(side="left", padx=6)

        def _tick():
            if not cap.winfo_exists():
                return
            v = reader()
            if v is not None:
                st["val"] = v
                cur.set(str(v))
            cap.after(80, _tick)

        _tick()
        cap.lift()

    def _cal_hint_text(device_id, code_str):
        """What raw min/max mean when left empty: the axis' calibrated range."""
        try:
            from .devices.calibration import load_calibration

            cal = load_calibration(calibration_file())
            axis = cal.devices[device_id].axes[int(str(code_str).strip())]
            return f"leer = Kalibrierung: {axis.raw_min}…{axis.raw_max}"
        except Exception:
            return "leer = Kalibrierung (kein Eintrag für diese Achse!)"

    def _ed_show_fields(*_):
        atype = ev["action_type"].get()
        for frame in af.values():
            frame.pack_forget()
        af.get(atype, af["event"]).pack(side="left", fill="x")
        type_note.config(text=_TYPE_NOTE.get(atype, ""))
        seq_on.set(atype == "sequence")
        # a hat maps its four directions instead of the single action row
        if ev["kind"].get() == "hat":
            a1.grid_remove()
            afh.grid_remove()
            act_lbl.config(text=tr("Richtungen"))
            hatfr.grid()
        else:
            a1.grid()
            afh.grid()
            act_lbl.config(text=tr("Aktion"))
            hatfr.grid_remove()
        if ev["kind"].get() == "axis":
            axfr.grid()
            if etgt["device"] is not None:
                cal_hint.set(_cal_hint_text(etgt["device"], ev["code"].get()))
            sp_type = ev["sp_action_type"].get()
            for frame in spf.values():
                frame.pack_forget()
            spf.get(sp_type, spf["event"]).pack(side="left", fill="x")
            sp_note.config(text=_TYPE_NOTE.get(sp_type, ""))
            if ev["sp_enabled"].get():
                spfr.pack(anchor="w", fill="x", pady=(2, 0))
            else:
                spfr.pack_forget()
        else:
            axfr.grid_remove()
        if atype == "sequence":
            seqfr.grid()
        else:
            seqfr.grid_remove()

    def _seq_toggle():
        """The "Mehrschritt" checkbox: on = sequence action, off = back to pick."""
        if seq_on.get():
            ev["action_type"].set("sequence")
            if not seq_state["on"] and not seq_state["off"]:
                _seq_add("on")  # seed one editable step
        else:
            ev["action_type"].set("event")  # empty until the user picks anew
        _ed_show_fields()

    def _pick_sp_action():
        """Pick the below-detent target; the action kind follows the picked var."""
        def on_pick(v):
            if v.kind == "K:":
                ev["sp_action_type"].set("event")
                ev["sp_ev_event"].set(_var_name(v))
            else:  # A: / L: / V: -> set a SimVar/LVar/virtual var
                ev["sp_action_type"].set("simvar")
                ev["sp_sv_simvar"].set(_var_name(v))
            _ed_show_fields()
        _open_var_picker(win, _var_catalog(), on_pick)

    def _ed_set_form(form):
        for key, var in ev.items():
            if key in form:
                var.set(form[key])
        _ed_show_fields()

    def _seq_original(binding):
        if binding.action is None or binding.action.type != "sequence":
            return None
        d = binding.action.model_dump(exclude_defaults=True)
        d["type"] = "sequence"  # excluded as a default, but the union needs it
        return d

    def _selected_bind():
        """(device_id, index) of the highlighted binding row, or (None, None)."""
        sel, dev = _sel(detail), _sel(dev_tree)
        if sel and str(sel).startswith("bind:") and dev:
            return dev, int(str(sel).split(":")[1])
        return None, None

    def _ed_close():
        ed_win.withdraw()
        etgt.update(device=None, index=None, original_action=None)

    def _ed_load(device_id, index):
        prof = mstate["profile"]
        binds = prof.bindings.get(device_id, []) if prof else []
        if not (0 <= index < len(binds)):
            return
        binding = binds[index]
        etgt.update(device=device_id, index=index, original_action=_seq_original(binding))
        _ed_set_form(gui_mapper.binding_to_form(binding))
        if binding.action is not None and binding.action.type == "sequence":
            _seq_load(binding.action)
        else:
            _seq_clear()
        _cond_load(binding.when)
        ed_win.title(f"Binding: {binding.name}  —  {device_id} #{index}")

    def _open_editor(device_id, index):
        """Populate + show the settings window for ONE binding (index None = new)."""
        if index is None:
            etgt.update(device=device_id, index=None, original_action=None)
            _ed_set_form(gui_mapper.blank_binding_form("button"))
            _seq_clear()
            _cond_load([])
            ed_win.title(f"Neues Binding — {device_id}")
            _ed_status("Felder ausfüllen, dann Übernehmen.")
        else:
            _ed_load(device_id, index)
            _ed_status("")
        ed_win.deiconify()
        ed_win.lift()
        ed_win.focus_set()

    def _new_binding():
        dev = _sel(dev_tree)
        if dev is None:
            m_state.config(text=tr("Kein Gerät gewählt — links ein Gerät markieren."))
            return
        _open_editor(dev, None)

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
            # A sequence's steps live in seq_state (not the flat form): build its
            # action fresh and hand it to form_to_binding (which passes it through).
            if ev["action_type"].get() == "sequence":
                override = gui_mapper.rows_to_seq_action(_seq_rows("on"), _seq_rows("off"))
            else:
                override = etgt["original_action"]
            binding = gui_mapper.form_to_binding(
                {k: var.get() for k, var in ev.items()}, override
            )
            conds = gui_mapper.rows_to_conditions(_cond_rows())
            if conds:
                binding["when"] = conds
        except ValueError as exc:
            _ed_status(str(exc), error=True)
            return
        dev, idx = etgt["device"], etgt["index"]
        if idx is None:  # new binding (opened via _new_binding): append at the end
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
        _ed_close()
        _reselect(dev, idx)
        m_state.config(text=msg)

    def _ed_duplicate():
        dev, idx = _selected_bind()
        if dev is None:
            m_state.config(text=tr("Kein Binding gewählt — rechts eine Binding-Zeile markieren."))
            return
        binding = mstate["profile"].bindings[dev][idx]
        dup = gui_mapper.form_to_binding(
            gui_mapper.binding_to_form(binding), _seq_original(binding))
        if binding.when:  # conditions ride along on duplicate
            dup["when"] = [c.model_dump(exclude_defaults=True) for c in binding.when]
        dup["name"] = binding.name + " (Kopie)"
        err = _ed_save(lambda d: profile_writer.add_binding(d, dev, dup, index=idx + 1))
        if err:
            m_state.config(text=f"Nicht dupliziert: {err}")
            return
        _reselect(dev, idx + 1)
        m_state.config(text=tr("Binding dupliziert ✓"))

    def _ed_remove():
        dev, idx = _selected_bind()
        if dev is None:
            m_state.config(text=tr("Kein Binding gewählt — rechts eine Binding-Zeile markieren."))
            return
        binding = mstate["profile"].bindings[dev][idx]
        if not messagebox.askyesno("Binding entfernen", f"Binding „{binding.name}“ entfernen?"):
            return
        err = _ed_save(lambda d: profile_writer.remove_binding(d, dev, idx))
        if err:
            m_state.config(text=f"Nicht entfernt: {err}")
            return
        _ed_close()
        _reselect(dev, max(0, idx - 1))
        m_state.config(text=tr("Binding entfernt ✓"))

    def _edit_profile(mutate, ok_msg):
        """Validated profile edit outside an editor window (status -> Mapper bar)."""
        path = profiles_dir() / f"{profile_var.get()}.yaml"
        try:
            doc = profile_writer.load(path)
            mutate(doc)
            profile_writer.validate(doc)
            profile_writer.dump(doc, path)
        except Exception as exc:
            m_state.config(text=f"Nicht gespeichert: {exc}")
            return
        _mapper_reload(rediscover=False, keep_device=_sel(dev_tree))
        m_state.config(text=ok_msg)

    def _open_panel_test(device_id, output):
        """A little in-GUI ``out_*`` tool: light ONE physical element at a time so
        the user sees which LED / display cell a field drives ("wo landet das
        Signal?"). Sends an isolated feature report per :func:`panel_probe`.

        Only safe when the mapper isn't holding the panel (single feature-report
        owner) — a live mapper would immediately overwrite the test frame, so we
        refuse and say so instead of fighting it.
        """
        from .devices import hidraw_reader
        from .mapping import panel_probe

        targets = panel_probe.probe_targets(output)
        if not targets:
            return
        otype = getattr(output, "type", "")
        tw = tk.Toplevel(win)
        tw.transient(win)
        tw.title(f"{tr('Panel testen')} — {device_id}")
        frm = ttk.Frame(tw, padding=12)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, wraplength=470, justify="left", foreground="#555",
                  text=tr("Ein Element aufleuchten lassen, um es am echten Panel zu "
                          "identifizieren. Geht nur, wenn der Mapper das Panel NICHT "
                          "steuert (er würde den Test sofort überschreiben).")
                  ).pack(anchor="w")
        warn = ttk.Label(frm, foreground="#c62828", wraplength=470, justify="left")
        warn.pack(anchor="w", pady=(4, 0))
        status = ttk.Label(frm, foreground="#2e7d32")
        status.pack(anchor="w", pady=(2, 6))

        def _path():
            with contextlib.suppress(Exception):
                return hidraw_reader.discover(_device_catalog()).get(device_id)
            return None

        job = {"id": None}

        def _write(report) -> bool:
            if _mapper_running():
                warn.config(text=tr("⚠ Der Mapper läuft und steuert das Panel — bitte "
                                    "erst im Connection-Tab stoppen."))
                return False
            path = _path()
            if path is None:
                warn.config(text=f"„{device_id}“ {tr('nicht gefunden — angesteckt?')}")
                return False
            try:
                hidraw_reader.write_feature_report(path, report)
            except OSError as exc:
                warn.config(text=f"{tr('Senden fehlgeschlagen:')} {exc}")
                return False
            warn.config(text="")
            return True

        def _send(report, label):
            if not _write(report):
                return
            status.config(text=f"▶ {label} — {tr('leuchtet ~2 s')}")
            if job["id"]:
                tw.after_cancel(job["id"])

            def _clear():
                _write(panel_probe.blank_report(otype))
                status.config(text="")

            job["id"] = tw.after(2000, _clear)

        def _all_off():
            if _write(panel_probe.blank_report(otype)):
                status.config(text=tr("alles aus"))

        # scrollable grouped list of elements (radio has 20 cells + headers)
        mid = ttk.Frame(frm)
        mid.pack(fill="both", expand=True)
        canvas = tk.Canvas(mid, highlightthickness=0, height=360, width=380)
        sb = ttk.Scrollbar(mid, orient="vertical", command=canvas.yview)
        body = ttk.Frame(canvas)
        body.bind("<Configure>",
                  lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=body, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))
        tw.bind("<Destroy>", lambda e: (canvas.unbind_all("<Button-4>"),
                                        canvas.unbind_all("<Button-5>"))
                if e.widget is tw else None)

        row, last_group = 0, None
        for t in targets:
            if t.group != last_group:
                ttk.Label(body, text=t.group, font=("TkDefaultFont", 9, "bold"),
                          foreground="#333").grid(row=row, column=0, columnspan=3,
                                                  sticky="w", pady=(8, 1))
                row += 1
                last_group = t.group
            ttk.Label(body, text=t.label).grid(row=row, column=0, sticky="w",
                                               padx=(14, 8))
            ttk.Button(body, text=tr("🔦"), width=3,
                       command=lambda r=t.report, la=t.label: _send(r, la)
                       ).grid(row=row, column=1)
            if t.dot_report is not None:  # radio/multi cell: also flash its dot ("8.")
                ttk.Button(body, text=tr("🔦."), width=3,
                           command=lambda r=t.dot_report, la=f"{t.label} .": _send(r, la)
                           ).grid(row=row, column=2, padx=3)
            row += 1

        foot = ttk.Frame(frm)
        foot.pack(anchor="w", pady=(8, 0))
        ttk.Button(foot, text=tr("Alles aus"), command=_all_off).pack(side="left")
        ttk.Button(foot, text=tr("Schließen"),
                   command=lambda: (_all_off(), tw.destroy())).pack(side="left", padx=6)
        tw.protocol("WM_DELETE_WINDOW", lambda: (_all_off(), tw.destroy()))
        tw.minsize(420, 300)
        tw.lift()

    # --- output settings: ONE context window per tree row ------------------ #
    # The structure (Panel -> Selektor-Position[x] -> …) lives in the main
    # detail tree; double-clicking a row opens the settings for exactly that
    # group — a form with German labels + ⓘ help per field. No second list
    # inside the window (per user: a context window refers to ONE row).
    def _open_output_editor(device_id, out_index, group_path=(), focus=None):
        # focus = a subset of the group's field names -> a FOCUSED context window
        # (each radio element opens just its own field(s), not the whole bank).
        prof = mstate["profile"]
        outs = prof.outputs.get(device_id, []) if prof else []
        if not (0 <= out_index < len(outs)):
            return
        ow = tk.Toplevel(win)
        ow.transient(win)
        frm = ttk.Frame(ow, padding=12)
        frm.pack(fill="both", expand=True)
        head = ttk.Label(frm, text=tr(""), font=("TkDefaultFont", 10, "bold"))
        head.pack(anchor="w")
        role_lbl = ttk.Label(frm, text=tr(""), foreground="#666")
        role_lbl.pack(anchor="w")
        form = ttk.Frame(frm)
        form.pack(fill="both", expand=True, pady=(8, 0))
        o_status = ttk.Label(frm, text=tr(""), foreground="#666")
        o_status.pack(anchor="w", pady=(6, 0))
        ost = {"output": None, "nodes": [], "group": None, "focus": focus}

        def _status(msg, error=False):
            o_status.config(
                text=msg, foreground="#c62828" if error else "#2e7d32" if msg else "#666"
            )

        def _save(mutate, ok_msg):
            path = profiles_dir() / f"{profile_var.get()}.yaml"
            try:
                doc = profile_writer.load(path)
                mutate(doc)
                profile_writer.validate(doc)
                profile_writer.dump(doc, path)
            except Exception as exc:  # show inline, never write a broken profile
                _status(f"Nicht gespeichert: {exc}", error=True)
                return
            _reload()
            _mapper_reload(rediscover=False, keep_device=device_id)
            _status(ok_msg)

        def _field_row(row, node):
            """One form line: German label · widget · ⓘ help. Returns a getter."""
            ttk.Label(form, text=node.label).grid(row=row, column=0,
                                                  sticky="w", padx=(0, 8), pady=2)
            cell = ttk.Frame(form)
            cell.grid(row=row, column=1, sticky="w", pady=2)
            if node.kind == "bool":
                var = tk.BooleanVar(value=(node.value == "ja"))
                ttk.Checkbutton(cell, variable=var).pack(side="left")
                getter = var.get
            elif node.kind == "choice":
                var = tk.StringVar(value=node.value)
                ttk.Combobox(cell, textvariable=var, values=list(node.choices),
                             state="readonly", width=10).pack(side="left")
                getter = var.get
            else:
                var = tk.StringVar(value="" if node.value == "—" else node.value)
                ttk.Entry(cell, textvariable=var, width=30,
                          state="readonly" if node.pickable else "normal"
                          ).pack(side="left")
                if node.pickable:  # same wording as the binding editor
                    ttk.Button(cell, text=tr("Wählen…"),
                               command=lambda v=var: _pick_into(v)).pack(side="left", padx=3)
                if node.optional:
                    ttk.Label(cell, text=tr("(leer = Standard)"),
                              foreground="#666").pack(side="left", padx=4)
                getter = var.get
            help_text = gui_mapper.output_field_help(node.path)
            if help_text:
                _info(cell, help_text)
            return getter

        def _fields_form(group):
            """The group's scalar fields + Übernehmen; returns the button row.

            When a ``focus`` was given, only those fields are shown — so clicking
            one radio element opens JUST its own setting, not the whole bank."""
            fields = gui_mapper.group_fields(ost["nodes"], group.path)
            if ost["focus"]:
                fields = [n for n in fields if n.path and n.path[-1] in ost["focus"]]
            getters = [(node, _field_row(row, node)) for row, node in enumerate(fields)]
            if not fields:
                ttk.Label(form, foreground="#666", wraplength=430, justify="left",
                          text=tr("Diese Gruppe hat keine direkten Felder — die "
                               "Untergruppen stehen im Baum der Haupttabelle.")
                          ).grid(row=0, column=0, columnspan=2, sticky="w")

            def _apply():
                changes = []
                try:
                    for node, getter in getters:
                        raw = getter()
                        if isinstance(raw, str) and raw == ("" if node.value == "—"
                                                            else node.value):
                            continue  # untouched
                        val = gui_mapper.parse_output_value(ost["output"], node.path, raw)
                        changes.append((node.path, val))
                except ValueError as exc:
                    _status(str(exc), error=True)
                    return
                if not changes:
                    _status("Nichts geändert.")
                    return

                def mutate(doc):
                    for path, val in changes:
                        v = profile_writer.UNSET if val is gui_mapper.UNSET else val
                        profile_writer.set_output_value(doc, device_id, out_index, path, v)

                _save(mutate, "Gespeichert ✓")

            btns = ttk.Frame(form)
            btns.grid(row=len(fields) + 1, column=0, columnspan=2,
                      sticky="w", pady=(10, 0))
            if fields:  # same button row as the binding editor
                ttk.Button(btns, text=tr("Übernehmen"), style="Accent.TButton",
                           command=_apply).pack(side="left")
                ttk.Button(btns, text=tr("Zurücksetzen"),
                           command=_reload).pack(side="left", padx=6)
            ttk.Button(btns, text=tr("Schließen"),
                       command=ow.destroy).pack(side="left", padx=(0, 6))
            ttk.Button(btns, text=tr("🔦 LEDs/Display testen…"),
                       command=lambda: _open_panel_test(device_id, ost["output"])
                       ).pack(side="left", padx=(6, 0))
            return btns

        def _render_group(group):
            if group.kind in ("root", "group", "entry", "solo"):
                btns = _fields_form(group)
                if group.kind == "root":
                    def _remove_block():
                        if messagebox.askyesno(
                                "Panel-Block entfernen",
                                "Diesen ganzen Panel-Block aus dem Profil entfernen?",
                                parent=ow):
                            ow.destroy()
                            _bg_remove_output()
                    ttk.Button(btns, text=tr("✕ Panel-Block entfernen"),
                               style="Danger.TButton",
                               command=_remove_block).pack(side="left", padx=8)
                elif group.kind == "group" and group.removable:
                    def _remove_opt():
                        if messagebox.askyesno("Block entfernen",
                                               f"„{group.label}“ entfernen?", parent=ow):
                            _save(lambda d: profile_writer.set_output_value(
                                d, device_id, out_index, group.path,
                                profile_writer.UNSET), f"{group.label} entfernt")
                    ttk.Button(btns, text=f"✕ {group.label} entfernen",
                               style="Danger.TButton",
                               command=_remove_opt).pack(side="left", padx=8)
                elif group.kind == "entry":
                    def _remove_entry():
                        if messagebox.askyesno(
                                "Eintrag entfernen",
                                f"„{group.label}“ wirklich entfernen?", parent=ow):
                            ow.destroy()
                            _bg_remove_entry(group.path)
                    ttk.Button(btns, text=tr("✕ Eintrag entfernen"), style="Danger.TButton",
                               command=_remove_entry).pack(side="left", padx=8)
            elif group.kind in ("list", "unset"):
                opts = gui_mapper.output_add_options(ost["output"], group.path)
                ttk.Label(form, foreground="#666", wraplength=430, justify="left",
                          text=(f"Die Einträge von „{group.label}“ stehen als eigene "
                                "Zeilen im Baum der Haupttabelle — hier neue anlegen:"
                                if group.kind == "list" else
                                f"„{group.label}“ ist noch nicht angelegt.")
                          ).grid(row=0, column=0, sticky="w")
                if opts:
                    labels = list(opts)
                    tv = tk.StringVar(value=labels[0])
                    row1 = ttk.Frame(form)
                    row1.grid(row=1, column=0, sticky="w", pady=(8, 0))
                    if len(labels) > 1:
                        ttk.Combobox(row1, textvariable=tv, values=labels,
                                     state="readonly", width=18).pack(side="left",
                                                                      padx=(0, 4))

                    def _add():
                        tpl = opts[tv.get()]
                        if group.kind == "unset":
                            _save(lambda d: profile_writer.set_output_value(
                                d, device_id, out_index, group.path, tpl),
                                f"{group.label} angelegt")
                        else:
                            _save(lambda d: profile_writer.add_output_entry(
                                d, device_id, out_index, group.path, tpl),
                                "Eintrag angelegt — neue Zeile im Baum")

                    ttk.Button(row1, text=tr("+ Eintrag") if group.kind == "list"
                               else "+ Anlegen", style="Accent.TButton",
                               command=_add).pack(side="left")
            elif group.kind == "dict":  # bool_leds: LED button -> variable
                entries = [n for n in ost["nodes"]
                           if len(n.path) == len(group.path) + 1
                           and n.path[:-1] == group.path]
                for row, node in enumerate(entries):
                    getter = _field_row(row, node)

                    def _set_led(nd=node, g=getter):
                        try:
                            val = gui_mapper.parse_output_value(ost["output"], nd.path, g())
                        except ValueError as exc:
                            _status(str(exc), error=True)
                            return
                        _save(lambda d: profile_writer.set_output_value(
                            d, device_id, out_index, nd.path, val), "Gespeichert ✓")

                    def _del_led(nd=node):
                        _save(lambda d: profile_writer.remove_output_entry(
                            d, device_id, out_index, nd.path[:-1], nd.path[-1]),
                            "LED-Eintrag entfernt")

                    cell = ttk.Frame(form)
                    cell.grid(row=row, column=2, sticky="w", padx=4)
                    ttk.Button(cell, text=tr("✓"), width=2,
                               command=_set_led).pack(side="left")
                    ttk.Button(cell, text=tr("✕"), width=2, style="Danger.TButton",
                               command=_del_led).pack(side="left", padx=2)
                free = gui_mapper.output_dict_key_options(ost["output"], group.path)
                addrow = ttk.Frame(form)
                addrow.grid(row=len(entries) + 1, column=0, columnspan=3,
                            sticky="w", pady=(10, 0))
                if free:
                    kv = tk.StringVar(value=free[0])
                    ttk.Label(addrow, text=tr("LED-Knopf:")).pack(side="left")
                    ttk.Combobox(addrow, textvariable=kv, values=free, state="readonly",
                                 width=10).pack(side="left", padx=4)
                    ttk.Button(addrow, text=tr("+ Eintrag"), style="Accent.TButton",
                               command=lambda: _save(
                                   lambda d: profile_writer.set_output_value(
                                       d, device_id, out_index,
                                       (*group.path, kv.get()), ""),
                                   f"LED {kv.get()} angelegt — Variable wählen")
                               ).pack(side="left")
                else:
                    ttk.Label(addrow, text=tr("alle LED-Knöpfe belegt"),
                              foreground="#666").pack(side="left")

        def _bg_remove_entry(path):
            _edit_profile(lambda d: profile_writer.remove_output_entry(
                d, device_id, out_index, path[:-1], path[-1]), "Eintrag entfernt")

        def _bg_remove_output():
            _edit_profile(lambda d: profile_writer.remove_output(
                d, device_id, out_index), "Panel-Block entfernt")

        def _reload():
            prof2 = _current_profile()
            outs2 = prof2.outputs.get(device_id, []) if prof2 else []
            if not (0 <= out_index < len(outs2)):
                ow.destroy()
                return
            ost["output"] = outs2[out_index]
            ost["nodes"] = gui_mapper.output_nodes(ost["output"])
            group = next((g for g in gui_mapper.output_groups(ost["nodes"])
                          if g.path == tuple(group_path)), None)
            if group is None:  # this row is gone (entry removed elsewhere)
                ow.destroy()
                return
            ost["group"] = group
            title = (f"{group.label} {group.value}".strip() if group.path
                     else gui_mapper.describe_output(ost["output"]))
            ow.title(f"{title} — {device_id}")
            head.config(text=title)
            role = gui_mapper.group_role(tuple(group_path))
            role_lbl.config(text=f"Rolle: {role}" if role else "Allgemeine Einstellungen")
            for w in form.winfo_children():
                w.destroy()
            _render_group(group)

        _reload()
        ow.minsize(540, 320)
        ow.lift()
        ow.focus_set()

    def _remove_selected_row():
        """Remove whatever row is selected: binding, panel block or entry.

        The right-hand Entfernen button acts on the marked table row (per user:
        deleting must not require opening a window first).
        """
        sel, dev = _sel(detail), _sel(dev_tree)
        sid = str(sel) if sel else ""
        if sid.startswith("bind:"):
            _ed_remove()
            return
        if not sid.startswith("out:") or dev is None:
            m_state.config(text=tr("Erst rechts eine Zeile markieren."))
            return
        parts = sid.split(":", 2)
        idx = int(parts[1])
        gpath = tuple(int(s) if s.isdigit() else s
                      for s in parts[2].split("/")) if len(parts) > 2 else ()
        if not gpath:  # the panel block row itself
            if messagebox.askyesno(tr("Panel-Block entfernen"),
                                   tr("Diesen ganzen Panel-Block aus dem Profil entfernen?")):
                _edit_profile(lambda d: profile_writer.remove_output(d, dev, idx),
                              "Panel-Block entfernt ✓")
        elif isinstance(gpath[-1], int):  # a list entry (Position/Bank/Ziel/…)
            _edit_profile(lambda d: profile_writer.remove_output_entry(
                d, dev, idx, gpath[:-1], gpath[-1]), "Eintrag entfernt ✓")
        elif len(gpath) == 1 and gpath[0] in gui_mapper.OPTIONAL_TEMPLATES:
            if messagebox.askyesno("Block entfernen", f"„{gpath[0]}“ entfernen?"):
                _edit_profile(lambda d: profile_writer.set_output_value(
                    d, dev, idx, gpath, profile_writer.UNSET), "Block entfernt ✓")
        else:
            m_state.config(text=tr("Diese Zeile lässt sich nicht entfernen — Einträge oder "
                                "ganze Panel-Blöcke markieren."))

    def _open_row(row):
        """Open the editor for a detail row: bind:<i> or out:<i>[:<path>][|<fields>].

        A trailing ``|field,field`` (from a panel element's ref) opens a FOCUSED
        output window showing only those fields — so each radio display/encoder/
        swap gets its own context menu instead of the whole bank's."""
        dev = _sel(dev_tree)
        if dev is None or not row:
            return
        sid = str(row)
        if sid.startswith("bind:"):
            _open_editor(dev, int(sid.split(":")[1]))
        elif sid.startswith("out:"):
            body, _, foc = sid.partition("|")
            focus = [f for f in foc.split(",") if f] or None
            parts = body.split(":", 2)
            gpath = tuple(int(s) if s.isdigit() else s
                          for s in parts[2].split("/")) if len(parts) > 2 else ()
            _open_output_editor(dev, int(parts[1]), gpath, focus)

    def _on_detail_activate(_e=None):
        """Keyboard (Return) on a selected row -> open its settings window."""
        _open_row(_sel(detail))

    def _on_detail_double(event):
        """Double-click opens the row's editor; a single click only selects.

        Clicks on the expand/collapse triangle only toggle the branch; the
        header rows ("Bindings (n)"/"Outputs (n)") have nothing to open.
        """
        if "indicator" in detail.identify_element(event.x, event.y):
            return  # expand/collapse click — don't open an editor
        if detail.identify_region(event.x, event.y) not in ("tree", "cell"):
            return
        row = detail.identify_row(event.y)
        if not row:
            return
        detail.selection_set(row)
        _open_row(row)

    def _render_detail(device_id, reselect_index=None):
        detail.delete(*detail.get_children())
        prof = mstate["profile"]
        if prof is None or not device_id:
            return
        binds = gui_mapper.device_bindings(prof, device_id)
        bnode = detail.insert("", "end", text=f"Eingaben — Bindings ({len(binds)})",
                              open=True)
        for i, br in enumerate(binds):
            detail.insert(bnode, "end", iid=f"bind:{i}", text=br.name,
                          values=(br.source, br.action, br.transform, ""))
        out_objs = prof.outputs.get(device_id, [])
        if out_objs:
            # panel controllers as a REAL tree (per user): Panel -> Selektor-
            # Position[x] -> …, short labels, Eingabe/Anzeige role in the
            # Control column. Double-click a row = settings for THAT row only.
            onode = detail.insert("", "end", open=True,
                                  text=f"Panel-Controller ({len(out_objs)})")
            for i, o in enumerate(out_objs):
                detail.insert(onode, "end", iid=f"out:{i}", open=True,
                              text=gui_mapper.describe_output(o),
                              values=("", "", "", ""))
                for g in gui_mapper.output_groups(gui_mapper.output_nodes(o)):
                    if not g.path:
                        continue
                    parent = (f"out:{i}:" + "/".join(map(str, g.path[:-1]))
                              if len(g.path) > 1 else f"out:{i}")
                    if not detail.exists(parent):
                        parent = f"out:{i}"
                    detail.insert(parent, "end",
                                  iid=f"out:{i}:" + "/".join(map(str, g.path)),
                                  open=len(g.path) < 2,
                                  text=f"{g.label} {g.value}".strip(),
                                  values=(gui_mapper.group_role(g.path), "", "", ""))
        # Just highlight the row after a reload; editing is opened on demand only.
        if reselect_index is not None and binds:
            idx = min(reselect_index, len(binds) - 1)
            detail.selection_set(f"bind:{idx}")
            detail.see(f"bind:{idx}")
        if mstate["view"] == "panel":  # keep the reconstruction in sync
            _render_panel_canvas(device_id)

    # --- panel reconstruction view (canvas drawn from panel_layout) -------- #
    _PANEL_ON = "#22c55e"  # live "switch on" highlight (green)

    def _panel_fill(el):
        """(fill, outline) for an element in its resting (not-live) state."""
        if el.kind == panel_layout.LED:
            return "#334155", "#0f172a"
        if not el.mapped:
            return "#eceff1", "#cbd5e1"  # physical control the profile doesn't map
        if el.kind == panel_layout.SELECTOR:
            return "#eef2ff", ACCENT
        if el.kind == panel_layout.LEVER:
            return "#e2e8f0", "#94a3b8"
        if el.kind == panel_layout.HAT:
            return "#eef2f7", "#64748b"
        return SURFACE, "#94a3b8"  # mapped switch/button

    def _round_rect(c, x0, y0, x1, y1, rad, **kw):
        """A rounded rectangle / capsule as a smoothed polygon."""
        rad = max(0.0, min(rad, (x1 - x0) / 2, (y1 - y0) / 2))
        pts = [x0 + rad, y0, x1 - rad, y0, x1, y0, x1, y0 + rad, x1, y1 - rad,
               x1, y1, x1 - rad, y1, x0 + rad, y1, x0, y1, x0, y1 - rad,
               x0, y0 + rad, x0, y0]
        return c.create_polygon(pts, smooth=True, **kw)

    # Each control kind gets its OWN shape so the type reads at a glance (user:
    # "man erkennt nicht was es ist"): axis = slider w/ handle, button = pill,
    # switch = vertical toggle, hat = diamond, LED = disc, selector/lever = block.
    def _draw_axis(c, tag, el, x0, y0, x1, y1):
        midy = (y0 + y1) / 2 + 5
        trh = min((y1 - y0) * 0.45, 15)
        ty0, ty1 = midy - trh / 2, midy + trh / 2
        _round_rect(c, x0, ty0, x1, ty1, trh / 2, fill="#e2e8f0", outline="#94a3b8",
                    width=1, tags=(tag,))
        fill_id = c.create_rectangle(x0, ty0, x0, ty1, fill=ACCENT, outline="", tags=(tag,))
        hr = trh * 0.72
        handle = c.create_oval(x0 - hr, midy - hr, x0 + hr, midy + hr,
                               fill="#475569", outline="#f8fafc", width=1, tags=(tag,))
        c.create_text(x0 + 2, y0 + 7, anchor="w", text="⇔ " + (el.name or el.label),
                      fill=TEXT, font=("TkDefaultFont", 8, "bold"), tags=(tag,))
        val_id = c.create_text(x1 - 3, y0 + 7, anchor="e", text="—", fill=MUTED,
                               font=("TkDefaultFont", 8), tags=(tag,))
        if el.live_key is not None:
            pcanvas["live"].setdefault(el.live_key, []).append(
                {"kind": "axis", "fill": fill_id, "text": val_id, "handle": handle,
                 "x0": x0, "y0": ty0, "x1": x1, "y1": ty1, "midy": midy, "hr": hr,
                 "lo": el.raw_min, "hi": el.raw_max})

    def _draw_switch(c, tag, el, x0, y0, x1, y1):
        muted = not el.mapped
        body = "#eceff1" if muted else SURFACE
        edge = "#cbd5e1" if muted else "#94a3b8"
        # single caption above the toggle (full name is on hover / in the editor)
        c.create_text((x0 + x1) / 2, y0 + 7, text=el.label, fill=MUTED if muted else TEXT,
                      font=("TkDefaultFont", 8, "bold"), tags=(tag,))
        cxm = (x0 + x1) / 2
        bw = min((x1 - x0) * 0.55, 24)
        by0, by1 = y0 + 15, y1 - 4
        _round_rect(c, cxm - bw / 2, by0, cxm + bw / 2, by1, bw / 2, fill=body,
                    outline=edge, width=1, tags=(tag,))
        kr = bw * 0.40
        y_off, y_on = by1 - kr - 2, by0 + kr + 2
        knob = c.create_oval(cxm - kr, y_off - kr, cxm + kr, y_off + kr,
                             fill="#cfd8dc" if muted else "#78909c", outline="", tags=(tag,))
        if el.live_key is not None:
            pcanvas["live"].setdefault(el.live_key, []).append(
                {"kind": "toggle", "knob": knob, "cx": cxm, "kr": kr,
                 "y_off": y_off, "y_on": y_on,
                 "off": "#cfd8dc" if muted else "#78909c"})

    def _draw_button(c, tag, el, x0, y0, x1, y1):
        muted = not el.mapped
        fill = "#eceff1" if muted else SURFACE
        edge = "#cbd5e1" if muted else "#94a3b8"
        bx0, by0, bx1, by1 = x0 + 3, y0 + 3, x1 - 3, y1 - 3
        rect = _round_rect(c, bx0, by0, bx1, by1, (by1 - by0) / 2, fill=fill,
                           outline=edge, width=2, tags=(tag,))
        # single caption centred on the button (full name is on hover)
        c.create_text((bx0 + bx1) / 2, (by0 + by1) / 2, text=el.label,
                      fill=MUTED if muted else TEXT, font=("TkDefaultFont", 8, "bold"),
                      width=max(28.0, bx1 - bx0 - 6), tags=(tag,))
        if el.live_key is not None:
            pcanvas["live"].setdefault(el.live_key, []).append(
                {"kind": "onoff", "rect": rect, "off": fill})

    def _draw_hat(c, tag, el, x0, y0, x1, y1):
        muted = not el.mapped
        cxm, cym = (x0 + x1) / 2, (y0 + y1) / 2 + 5
        rr = min(x1 - x0, y1 - y0) * 0.34
        c.create_polygon(cxm, cym - rr, cxm + rr, cym, cxm, cym + rr, cxm - rr, cym,
                         fill="#eceff1" if muted else "#eef2f7",
                         outline="#cbd5e1" if muted else "#64748b", width=2, tags=(tag,))
        c.create_text(cxm, y0 + 7, text="✛ " + el.label, fill=MUTED if muted else TEXT,
                      font=("TkDefaultFont", 8, "bold"), tags=(tag,))

    def _draw_led(c, tag, el, x0, y0, x1, y1):
        fill, edge = _panel_fill(el)
        c.create_oval(x0, y0, x1, y1, fill=fill, outline=edge, width=2, tags=(tag,))
        c.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=el.label, fill="#e2e8f0",
                      font=("TkDefaultFont", 8, "bold"), tags=(tag,))

    def _draw_segment(c, tag, el, x0, y0, x1, y1):
        # a digital DISPLAY — unmistakably NOT a button: rectangular metal bezel,
        # black screen, amber 7-seg-style readout (sharp corners, no pill shape).
        c.create_rectangle(x0 + 2, y0 + 2, x1 - 2, y1 - 2, fill="#1c1c1c",
                           outline="#6b7280", width=1, tags=(tag,))  # metal bezel
        sx0, sy0, sx1, sy1 = x0 + 5, y0 + 5, x1 - 5, y1 - 5
        c.create_rectangle(sx0, sy0, sx1, sy1, fill="#050805", outline="#000000",
                           width=1, tags=(tag,))  # black screen
        c.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=el.label, fill="#ffb000",
                      font=("TkFixedFont", 9, "bold"),
                      width=max(26.0, sx1 - sx0 - 4), tags=(tag,))

    def _draw_button_light(c, tag, el, x0, y0, x1, y1):
        # a button backlight (amber), pill-shaped like a button
        bx0, by0, bx1, by1 = x0 + 3, y0 + 3, x1 - 3, y1 - 3
        _round_rect(c, bx0, by0, bx1, by1, (by1 - by0) / 2, fill="#3a2f10",
                    outline="#d4a418", width=2, tags=(tag,))
        c.create_text((bx0 + bx1) / 2, (by0 + by1) / 2, text=el.label, fill="#ffd45e",
                      font=("TkDefaultFont", 8, "bold"),
                      width=max(30.0, bx1 - bx0 - 8), tags=(tag,))

    def _draw_dot(c, tag, el, x0, y0, x1, y1):
        r = min(x1 - x0, y1 - y0) * 0.18
        cx2, cy2 = (x0 + x1) / 2, (y0 + y1) / 2
        c.create_oval(cx2 - r, cy2 - r, cx2 + r, cy2 + r, fill="#3ee08a",
                      outline="#1f7a4d", width=1, tags=(tag,))
        c.create_text(cx2, cy2 + r + 7, text=el.label, fill=MUTED,
                      font=("TkDefaultFont", 7), tags=(tag,))

    def _draw_encoder(c, tag, el, x0, y0, x1, y1):
        # a rotary encoder knob: a disc with a pointer notch, caption above
        c.create_text((x0 + x1) / 2, y0 + 7, text="⟳ " + el.label, fill=TEXT,
                      font=("TkDefaultFont", 8, "bold"),
                      width=max(30.0, x1 - x0 - 6), tags=(tag,))
        cx2, cy2 = (x0 + x1) / 2, (y0 + y1) / 2 + 6
        r = min(x1 - x0, y1 - y0) * 0.28
        c.create_oval(cx2 - r, cy2 - r, cx2 + r, cy2 + r, fill="#cfd8dc",
                      outline="#607d8b", width=2, tags=(tag,))
        c.create_line(cx2, cy2, cx2, cy2 - r, fill="#37474f", width=2, tags=(tag,))

    def _draw_header(c, tag, el, x0, y0, x1, y1):
        # a group heading: bold accent title + a separator line under it
        c.create_text(x0 + 2, (y0 + y1) / 2, anchor="w", text=el.label, fill=ACCENT,
                      font=("TkDefaultFont", 9, "bold"), tags=(tag,))
        c.create_line(x0, y1 - 1, x1, y1 - 1, fill="#94a3b8", width=1, tags=(tag,))

    def _draw_block(c, tag, el, x0, y0, x1, y1):
        fill, edge = _panel_fill(el)
        _round_rect(c, x0, y0, x1, y1, 8, fill=fill, outline=edge, width=2, tags=(tag,))
        glyph = "⟳" if el.kind == panel_layout.SELECTOR else "⭥"
        # single caption (full detail on hover), centred in the block
        c.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=f"{glyph} {el.label}",
                      fill=TEXT if el.mapped else MUTED,
                      font=("TkDefaultFont", 8, "bold"),
                      width=max(30.0, x1 - x0 - 6), tags=(tag,))

    _PANEL_DRAW = {panel_layout.AXIS: _draw_axis, panel_layout.SWITCH: _draw_switch,
                   panel_layout.BUTTON: _draw_button, panel_layout.HAT: _draw_hat,
                   panel_layout.LED: _draw_led, panel_layout.SEGMENT: _draw_segment,
                   panel_layout.BUTTON_LIGHT: _draw_button_light, panel_layout.DOT: _draw_dot,
                   panel_layout.ENCODER: _draw_encoder, panel_layout.HEADER: _draw_header}

    def _render_panel_canvas(device_id):
        c = panel_canvas
        c.delete("all")
        pcanvas["by_index"].clear()
        pcanvas["live"].clear()
        pcanvas["device"] = device_id
        pcanvas["hint"] = None
        prof = mstate["profile"]
        if prof is None or not device_id:
            return
        cw, ch = c.winfo_width(), c.winfo_height()
        if cw < 40 or ch < 40:
            return  # not laid out yet — the <Configure> bind re-renders once sized
        pad = 8
        els = panel_layout.panel_layout(prof, device_id)
        if not els:
            c.configure(scrollregion=(0, 0, cw, ch))
            c.create_text(pad, pad, anchor="nw", fill=MUTED,
                          text=tr("Für dieses Gerät gibt es noch keinen Nachbau."))
            return
        # y is in "viewport" units (1.0 = one canvas height): a layout taller than
        # 1.0 (the radio panel) becomes scrollable content below the fold.
        content = max(1.0, max(el.y + el.h for el in els))
        W, H = cw - 2 * pad, ch - 2 * pad
        for n, el in enumerate(els):
            tag = f"pel:{n}"
            pcanvas["by_index"][n] = el
            x0, y0 = pad + el.x * W, pad + el.y * H
            x1, y1 = x0 + el.w * W, y0 + el.h * H
            _PANEL_DRAW.get(el.kind, _draw_block)(c, tag, el, x0, y0, x1, y1)
        content_px = pad + content * H + pad
        c.configure(scrollregion=(0, 0, cw, content_px))
        if content <= 1.0:
            c.yview_moveto(0.0)  # nothing to scroll
        pcanvas["hint"] = c.create_text(
            pad, content_px - 4, anchor="sw", fill=MUTED, font=("TkDefaultFont", 8),
            text=tr("Klick: gemappt → Editor, leerer Platzhalter → neu mappen · "
                    "Schalter/Achsen live"))

    def _panel_el_at(_event):
        """The PanelElement under the cursor, via the shared per-element tag."""
        for t in panel_canvas.gettags("current"):
            if t.startswith("pel:"):
                return pcanvas["by_index"].get(int(t.split(":")[1]))
        return None

    def _panel_click(event):
        el = _panel_el_at(event)
        if el is None:
            return
        if el.ref:  # mapped -> open its editor
            _open_row(el.ref)
            return
        # empty placeholder with a physical code -> create a binding FOR it, with
        # the source (kind + code) pre-filled so the switch/button can be mapped.
        dev = _sel(dev_tree)
        src = el.source_kind or el.kind  # physical source kind may differ from visual
        if dev and el.code is not None and src in ("switch", "button", "axis", "hat"):
            _open_editor(dev, None)
            ev["kind"].set(src)
            ev["code"].set(str(el.code))
            ev["name"].set(el.label or tr("Neues Binding"))
            _ed_show_fields()
            ed_win.title(f"Neu mappen — {dev} · {el.label} (Code {el.code})")

    def _panel_hover(event):
        if pcanvas["hint"] is None:
            return
        el = _panel_el_at(event)
        if el is None:
            txt = tr("Klick: gemappt → Editor, leerer Platzhalter → neu mappen · "
                     "Schalter/Achsen live")
        elif el.kind == panel_layout.HEADER:
            txt = el.label  # a group heading, not a control
        elif el.mapped:
            txt = f"{el.label} — {el.name or el.action}"
            if el.name and el.action:
                txt += f"  ({el.action})"
        elif el.code is not None and (el.source_kind or el.kind) in ("switch", "button"):
            txt = f"{el.label} — " + tr("leer · Klick zum Mappen")
        else:
            txt = f"{el.label} — " + tr("nicht gemappt")
        panel_canvas.itemconfigure(pcanvas["hint"], text=txt)

    def _apply_view():
        """Show whichever of the table / reconstruction the current mode selects."""
        if mstate["view"] == "panel":
            detail.grid_remove()
            dsb.grid_remove()
            panel_canvas.grid()
            panel_vsb.grid()
            view_btn.config(text=tr("Tabelle"))
        else:
            panel_canvas.grid_remove()
            panel_vsb.grid_remove()
            detail.grid()
            dsb.grid()
            view_btn.config(text=tr("Nachbau"))

    def _panel_wheel(event):
        # scroll the tall reconstructions (radio); Linux = Button-4/5, else delta
        if event.num == 5 or event.delta < 0:
            panel_canvas.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0:
            panel_canvas.yview_scroll(-1, "units")

    for _seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
        panel_canvas.bind(_seq, _panel_wheel)

    def _toggle_view():
        mstate["view"] = "table" if mstate["view"] == "panel" else "panel"
        _apply_view()
        if mstate["view"] == "panel":
            _render_panel_canvas(_sel(dev_tree))

    panel_canvas.bind("<Button-1>", _panel_click)
    panel_canvas.bind("<Motion>", _panel_hover)
    panel_canvas.bind(
        "<Configure>",
        lambda _e: _render_panel_canvas(pcanvas["device"] or _sel(dev_tree))
        if mstate["view"] == "panel" else None)
    _apply_view()  # reconstruction is the default view (table stays a click away)

    def _mapper_reload(rediscover: bool = False, keep_device=None):
        prof = _current_profile()
        cat = _device_catalog()
        dev_tree.delete(*dev_tree.get_children())
        if prof is None or cat is None:
            mstate["profile"] = None
            _render_detail(None)
            m_state.config(text=tr("Profil oder Geräte-Katalog nicht lesbar"))
            return
        if rediscover:
            mstate["present"] = _discover_present(cat)
            mstate["discovered"] = True
        rows = gui_mapper.build_device_rows(cat, prof, mstate["present"])
        mstate["profile"] = prof
        ids = set()
        for r in rows:
            dev_tree.insert("", "end", iid=r.id, text=r.name,
                            values=(r.transport, r.status, r.inputs, r.outputs))
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

    def _on_kind_change(_e=None):
        ev["kind"].set(_kind_of_label.get(kind_disp.get(), kind_disp.get()))
        _ed_show_fields()

    kind_cb.bind("<<ComboboxSelected>>", _on_kind_change)
    dev_tree.bind("<<TreeviewSelect>>", lambda *_: _render_detail(_sel(dev_tree)))
    detail.bind("<Return>", _on_detail_activate)
    detail.bind("<Double-Button-1>", _on_detail_double)
    profile_var.trace_add("write", lambda *_: _mapper_reload(rediscover=False))

    # Switching tabs: the Statistik tab starts/stops its live reads; the Mapper
    # tab discovers devices the first time it is shown (lazy, keeps startup fast).
    def _on_tab_changed(_e=None):
        _resubscribe()
        if str(nb.select()) == str(mtab):
            _mapper_reload(rediscover=not mstate["discovered"])

    nb.bind("<<NotebookTabChanged>>", _on_tab_changed)

    # --- live view: mirror the attached device onto the Live column -------- #
    # One after()-loop for the whole Mapper tab: it (re)opens the selected
    # device lazily, drains its pending events each tick and paints the Live
    # cells (buttons/switches ●, axes a filling bar). The reader is picked by
    # transport — evdev for the yoke/pedals/quadrant, hidraw for the Saitek
    # panels — so panel switches light up live too. A missing/unplugged device
    # is retried every ~2 s, so plugging it in just starts the live view.
    live: dict = {"id": None, "read": None, "ranges": {}, "retry": 0}

    def _live_open(device_id):
        live.update(id=device_id, read=None, ranges={}, retry=0)
        if device_id is None:
            return
        with contextlib.suppress(Exception):
            from .devices import evdev_reader, hidraw_reader

            dcat = _device_catalog()
            ddef = dcat.by_id(device_id) if dcat else None
            if ddef is not None and ddef.transport == "hidraw":
                path = hidraw_reader.discover(dcat).get(device_id)
                opened = hidraw_reader.live_state_reader(path) if path else None
            else:
                path = evdev_reader.discover(dcat).get(device_id) if dcat else None
                opened = evdev_reader.live_state_reader(path) if path else None
            if opened:
                live["read"], live["ranges"] = opened

    def _live_tick():
        try:
            dev = _sel(dev_tree) if str(nb.select()) == str(mtab) else None
            if dev != live["id"]:
                _live_open(dev)
            elif dev is not None and live["read"] is None:
                live["retry"] += 1
                if live["retry"] >= 20:  # ~2 s — device may be attached by now
                    _live_open(dev)
            state = live["read"]() if live["read"] is not None else None
            if state is None and live["read"] is not None:
                live["read"] = None  # unplugged -> the retry loop takes over
            if state and dev and mstate["profile"] is not None:
                for key, iids in gui_mapper.live_row_map(mstate["profile"], dev).items():
                    val = state.get(key)
                    if val is None:
                        continue
                    if key[0] == "axis":
                        lo, hi = live["ranges"].get(key[1], (0, 255))
                        txt = gui_mapper.live_bar(val, lo, hi)
                    else:
                        txt = "●" if val else ""
                    for iid in iids:
                        if detail.exists(iid):
                            detail.set(iid, "live", txt)
                if mstate["view"] == "panel":  # switches toggle, axis handles slide
                    for key, entries in pcanvas["live"].items():
                        val = state.get(key)
                        if val is None:
                            continue
                        for e in entries:
                            if e["kind"] == "onoff":
                                if panel_canvas.type(e["rect"]) is not None:
                                    panel_canvas.itemconfigure(
                                        e["rect"], fill=_PANEL_ON if val else e["off"])
                            elif e["kind"] == "toggle":
                                if panel_canvas.type(e["knob"]) is not None:
                                    yy, kr = (e["y_on"] if val else e["y_off"]), e["kr"]
                                    panel_canvas.coords(e["knob"], e["cx"] - kr, yy - kr,
                                                        e["cx"] + kr, yy + kr)
                                    panel_canvas.itemconfigure(
                                        e["knob"], fill=_PANEL_ON if val else e["off"])
                            elif panel_canvas.type(e["fill"]) is not None:  # axis slider
                                lo, hi = e["lo"], e["hi"]
                                if lo is None or hi is None:
                                    lo, hi = live["ranges"].get(key[1], (0, 255))
                                span = (hi - lo) or 1
                                frac = min(1.0, max(0.0, (val - lo) / span))
                                fx = e["x0"] + frac * (e["x1"] - e["x0"])
                                panel_canvas.coords(e["fill"], e["x0"], e["y0"], fx, e["y1"])
                                hr = e["hr"]
                                panel_canvas.coords(e["handle"], fx - hr, e["midy"] - hr,
                                                    fx + hr, e["midy"] + hr)
                                panel_canvas.itemconfigure(e["text"], text=f"{val:g}")
        finally:
            win.after(100, _live_tick)

    _live_tick()

    # --- Profile tab (selector + management + metadata) -------------------- #
    ptab = ttk.Frame(nb, padding=12)
    nb.add(ptab, text=tr("tab.profile"))
    ptab.columnconfigure(1, weight=1)

    prow = ttk.Frame(ptab)
    prow.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
    ttk.Label(prow, text=tr("Aktives Profil:")).pack(side="left")
    profile_cb = ttk.Combobox(prow, textvariable=profile_var, values=profiles,
                              state="readonly", width=26)
    profile_cb.pack(side="left", padx=6)

    def _refresh_profiles(select=None):
        profile_cb["values"] = _list_profiles(root_dir)
        if select is not None:
            profile_var.set(select)  # fires the trace -> reloads everywhere

    def _ask_profile_name(title, initial=""):
        raw = simpledialog.askstring(title, "Profilname:", initialvalue=initial, parent=win)
        if raw is None:
            return None
        name = raw.strip()
        if not name or not all(c.isalnum() or c in "_-" for c in name):
            messagebox.showerror(tr("Ungültiger Name"), tr("Nur Buchstaben, Ziffern, '_' und '-'."))
            return None
        if (profiles_dir(root_dir) / f"{name}.yaml").exists():
            messagebox.showerror("Profil existiert", f"'{name}' gibt es schon.")
            return None
        return name

    def _profile_new():
        name = _ask_profile_name("Neues Profil")
        if name is None:
            return
        profile_writer.dump(profile_writer.new_profile(name),
                            profiles_dir(root_dir) / f"{name}.yaml")
        _refresh_profiles(select=name)

    def _profile_duplicate():
        src = profiles_dir(root_dir) / f"{profile_var.get()}.yaml"
        if not src.exists():
            messagebox.showerror(tr("Kein Profil"), tr("Aktuelles Profil nicht gefunden."))
            return
        name = _ask_profile_name("Profil duplizieren", initial=f"{profile_var.get()}_kopie")
        if name is None:
            return
        data = profile_writer.load(src)
        data["name"] = name  # keep the file's formatting/comments; just rename
        profile_writer.dump(data, profiles_dir(root_dir) / f"{name}.yaml")
        _refresh_profiles(select=name)

    def _profile_remove():
        name = profile_var.get()
        names = _list_profiles(root_dir)
        if len(names) <= 1:
            messagebox.showerror(tr("Nicht möglich"),
                                 tr("Das letzte Profil kann nicht entfernt werden."))
            return
        if not messagebox.askyesno("Profil entfernen",
                                   f"Profil '{name}' wirklich löschen? Das lässt sich nicht "
                                   "rückgängig machen."):
            return
        (profiles_dir(root_dir) / f"{name}.yaml").unlink(missing_ok=True)
        _refresh_profiles(select=next(n for n in names if n != name))

    ttk.Button(prow, text=tr("+ Neu"), style="Accent.TButton",
               command=_profile_new).pack(side="left", padx=(8, 0))
    ttk.Button(prow, text=tr("Duplizieren"), command=_profile_duplicate).pack(side="left", padx=6)
    ttk.Button(prow, text=tr("Entfernen"), style="Danger.TButton",
               command=_profile_remove).pack(side="left")

    ttk.Label(ptab, text=tr("Beschreibung")).grid(row=1, column=0, sticky="w", pady=2, padx=(0, 8))
    p_desc = tk.StringVar()
    ttk.Entry(ptab, textvariable=p_desc).grid(row=1, column=1, sticky="ew", pady=2)
    ttk.Label(ptab, text=tr("Auto-Auswahl")).grid(row=2, column=0, sticky="w", pady=2, padx=(0, 8))
    p_match = tk.StringVar()
    ttk.Entry(ptab, textvariable=p_match).grid(row=2, column=1, sticky="ew", pady=2)
    ttk.Label(ptab, text=tr("Flugzeug-Titel (Komma-getrennt) — wählt dieses Profil automatisch, "
                         "wenn der Titel passt."), foreground=MUTED).grid(
                             row=3, column=1, sticky="w")

    p_status = ttk.Label(ptab, text=tr(""), foreground=MUTED)

    def _profile_meta_load(*_):
        try:
            prof = load_profile(profiles_dir(root_dir) / f"{profile_var.get()}.yaml")
        except Exception:
            p_desc.set("")
            p_match.set("")
            return
        p_desc.set(prof.description)
        p_match.set(", ".join(prof.aircraft_match))
        p_status.config(text=tr(""))

    def _profile_meta_save():
        path = profiles_dir(root_dir) / f"{profile_var.get()}.yaml"
        match = [m.strip() for m in p_match.get().split(",") if m.strip()]
        try:
            data = profile_writer.load(path)
            profile_writer.set_meta(data, description=p_desc.get().strip(), aircraft_match=match)
            profile_writer.validate(data)
            profile_writer.dump(data, path)
            p_status.config(text=tr("Gespeichert ✓"), foreground="#15803d")
        except Exception as exc:
            p_status.config(text=f"Fehler: {exc}", foreground=DANGER)

    ttk.Button(ptab, text=tr("Beschreibung speichern"), style="Accent.TButton",
               command=_profile_meta_save).grid(row=4, column=1, sticky="w", pady=(10, 0))
    p_status.grid(row=5, column=1, sticky="w", pady=(4, 0))

    profile_var.trace_add("write", _profile_meta_load)
    _profile_meta_load()

    # --- Gauges tab: click a panel together from mapped gauges ------------- #
    # Round instruments ported from the user's Air Manager gauges (pure math in
    # gauge_model.py, scale parameters from docs/gauges-design.md). Flow per
    # user wish: "+ Gauge" -> pick a template or a LIBRARY gauge -> FIRST map
    # the needles to variables -> Übernehmen puts it on the panel AND saves it
    # by name into the library, so configured gauges can be called up again.
    from . import gauge_model

    gtab = ttk.Frame(nb, padding=8)
    nb.add(gtab, text=tr("tab.gauges"))
    gtab.rowconfigure(1, weight=1)
    gtab.columnconfigure(0, weight=1)

    gbar = ttk.Frame(gtab)
    gbar.grid(row=0, column=0, sticky="ew")
    g_add = ttk.Menubutton(gbar, text=tr("+ Gauge"))
    g_add.pack(side="left")
    _attach_tooltip(g_add, tr("Instrument hinzufügen: erst aus Bibliothek (bereits gemappte "
                           "Gauges) oder Vorlage wählen, dann die Zeiger auf Variablen "
                           "mappen — danach liegt es auf dem Panel."))
    ttk.Button(gbar, text=tr("✎ Mappen"), command=lambda: _g_edit_selected()
               ).pack(side="left", padx=6)
    ttk.Button(gbar, text=tr("✕ Entfernen"), style="Danger.TButton",
               command=lambda: _g_remove()).pack(side="left")
    g_hint = ttk.Label(gbar, text=tr("Klick wählt · Doppelklick mappt"), foreground="#666")
    g_hint.pack(side="left", padx=10)

    gcv = tk.Canvas(gtab, background="#232323", highlightthickness=0)
    gcv.grid(row=1, column=0, sticky="nsew", pady=(6, 0))

    # panel content + per-gauge canvas items: [(needle, line_id, text_id, cx, cy, r)]
    g_state: dict = {"specs": [], "sel": None, "items": []}

    def _g_load():
        data = load_gui_settings()
        with contextlib.suppress(Exception):  # a broken settings file must not kill the GUI
            g_state["specs"] = [gauge_model.from_dict(d) for d in data.get("gauges_panel", [])]

    def _g_persist():
        data = load_gui_settings()
        data["gauges_panel"] = [gauge_model.to_dict(g) for g in g_state["specs"]]
        save_gui_settings(data)

    def _g_library() -> dict:
        lib = load_gui_settings().get("gauge_library", {})
        return lib if isinstance(lib, dict) else {}

    def _g_lib_save(spec):
        data = load_gui_settings()
        data.setdefault("gauge_library", {})[spec.name] = gauge_model.to_dict(spec)
        save_gui_settings(data)

    def _g_lib_delete(name):
        data = load_gui_settings()
        if name in data.get("gauge_library", {}):
            del data["gauge_library"][name]
            save_gui_settings(data)

    def _g_wires():
        wires = []
        for g in g_state["specs"]:
            for n in g.needles:
                if (w := gauge_model.wire_name(n)) is not None:
                    wires.append(w)
        return wires

    gauge_hook["wires"] = (
        lambda: _g_wires() if str(nb.select()) == str(gtab) else []
    )

    def _g_layout() -> tuple[int, float]:
        """(cols, cell size) maximising the gauge size for the canvas."""
        count = max(1, len(g_state["specs"]))
        w = max(gcv.winfo_width(), 120)
        h = max(gcv.winfo_height(), 120)
        best = (1, 0.0)
        for cols in range(1, count + 1):
            rows = -(-count // cols)
            cell = min(w / cols, h / rows)
            if cell > best[1]:
                best = (cols, cell)
        return best

    def _g_paint(canvas, g, x, y, w, h, selected=False, sample=None):
        """Draw gauge ``g`` into (x, y, w, h); return per-needle live tuples.

        Shape-aware: aspect 1 = round face; wider = a cluster of sub-scales each
        at its own centre (cx/cy). ``sample`` (0..1) parks the needle at that
        fraction for the config preview; ``None`` parks it at v_min so the live
        loop moves it. Reused for the panel AND the parametrisation preview.
        """
        aspect = getattr(g, "aspect", 1.0) or 1.0
        if w / max(h, 1) > aspect:  # letterbox the face to its aspect inside the cell
            fw, fh = h * aspect, float(h)
        else:
            fw, fh = float(w), w / max(aspect, 0.01)
        fx, fy = x + (w - fw) / 2, y + (h - fh) / 2
        base_R = fh * 0.47
        round_face = abs(aspect - 1.0) < 0.05
        edge = "#64b5f6" if selected else "#3a3a3a"
        if round_face:
            mx, my = fx + fw / 2, fy + fh / 2
            canvas.create_oval(mx - base_R, my - base_R, mx + base_R, my + base_R,
                               fill="#141414", outline=edge, width=3 if selected else 2)
        else:
            canvas.create_rectangle(fx + 2, fy + 2, fx + fw - 2, fy + fh - 2,
                                    fill="#141414", outline=edge, width=3 if selected else 2)
        canvas.create_text(fx + fw / 2, fy + fh * 0.055, text=g.name, fill="#9e9e9e",
                           font=("TkDefaultFont", max(7, int(fh * 0.045))))
        needles = []
        for idx, n in enumerate(g.needles):
            ncx, ncy = fx + n.cx * fw, fy + n.cy * fh
            r = base_R * n.radius
            if not round_face:  # each sub-scale gets its own faint ring
                canvas.create_oval(ncx - r * 1.05, ncy - r * 1.05, ncx + r * 1.05,
                                   ncy + r * 1.05, outline="#2b2b2b", width=1)
            for arc in n.arcs:
                a1, a2 = gauge_model.arc_angles(n, arc)
                canvas.create_arc(ncx - r, ncy - r, ncx + r, ncy + r,
                                  start=90 - a2, extent=a2 - a1, style="arc",
                                  outline=arc.color, width=max(3, int(r * 0.07)))
            for value, ang, major in gauge_model.ticks(n):
                ln = r * (0.15 if major else 0.08)
                canvas.create_line(*gauge_model.polar(ncx, ncy, r - ln, ang),
                                   *gauge_model.polar(ncx, ncy, r, ang),
                                   fill="#e8e8e8", width=2 if major else 1)
                if major:
                    canvas.create_text(
                        *gauge_model.polar(ncx, ncy, r - ln - r * 0.13, ang),
                        text=f"{value:g}", fill="#d0d0d0",
                        font=("TkDefaultFont", max(6, int(r * 0.11))))
            frac = None if sample is None else max(0.0, min(1.0, sample))
            ang0 = n.omega + n.sweep * (frac ** n.h) if frac is not None \
                else gauge_model.angle_for(n, n.v_min)
            line = canvas.create_line(
                *gauge_model.polar(ncx, ncy, r * 0.14, ang0 + 180),
                *gauge_model.polar(ncx, ncy, r * 0.82, ang0),
                fill=n.color, width=max(2, int(r * 0.045)), capstyle="round")
            ry = ncy + r * (0.5 + 0.15 * idx) if round_face else ncy + r * 0.55
            text = canvas.create_text(ncx, ry, text=f"{n.label} —", fill=n.color,
                                      font=("TkDefaultFont", max(7, int(r * 0.13))))
            hub = max(2.0, r * 0.05)
            canvas.create_oval(ncx - hub, ncy - hub, ncx + hub, ncy + hub,
                               fill="#bdbdbd", outline="")
            needles.append((n, line, text, ncx, ncy, r))
        return needles

    def _g_redraw(_e=None):
        gcv.delete("all")
        g_state["items"] = []
        specs = g_state["specs"]
        if not specs:
            gcv.create_text(16, 16, anchor="nw", fill="#9e9e9e", justify="left",
                            text=tr("Noch keine Gauges.\n„+ Gauge“ → Vorlage/Bibliothek wählen "
                                 "→ Zeiger auf Variablen mappen → aufs Panel."))
            return
        cols, cell = _g_layout()
        for i, g in enumerate(specs):
            x, y = (i % cols) * cell, (i // cols) * cell
            g_state["items"].append(
                _g_paint(gcv, g, x, y, cell, cell, selected=(i == g_state["sel"]))
            )

    def _g_tick():
        try:
            if str(nb.select()) == str(gtab):
                vals = monitor.values()
                for needles in g_state["items"]:
                    for n, line, text, cx, cy, r in needles:
                        wire = gauge_model.wire_name(n)
                        value = vals.get(wire) if wire else None
                        if isinstance(value, (int, float)) and not isinstance(value, bool):
                            ang = gauge_model.angle_for(n, float(value))
                            gcv.coords(line, *gauge_model.polar(cx, cy, r * 0.14, ang + 180),
                                       *gauge_model.polar(cx, cy, r * 0.82, ang))
                            shown = gauge_model.display_value(n, float(value))
                            gcv.itemconfigure(text, text=f"{n.label} {n.fmt.format(shown)}")
                        else:
                            gcv.itemconfigure(text, text=f"{n.label} —")
        finally:
            win.after(150, _g_tick)

    def _g_index_at(x, y):
        if not g_state["specs"]:
            return None
        cols, cell = _g_layout()
        i = int(y // cell) * cols + int(x // cell)
        return i if int(x // cell) < cols and 0 <= i < len(g_state["specs"]) else None

    def _g_click(event):
        g_state["sel"] = _g_index_at(event.x, event.y)
        _g_redraw()

    def _g_double(event):
        i = _g_index_at(event.x, event.y)
        if i is not None:
            g_state["sel"] = i
            _g_config(g_state["specs"][i], existing_index=i)

    def _g_edit_selected():
        i = g_state["sel"]
        if i is None:
            g_hint.config(text=tr("Erst ein Gauge anklicken."))
            return
        _g_config(g_state["specs"][i], existing_index=i)

    def _g_remove():
        i = g_state["sel"]
        if i is None:
            g_hint.config(text=tr("Erst ein Gauge anklicken."))
            return
        del g_state["specs"][i]
        g_state["sel"] = None
        _g_persist()
        _resubscribe()
        _g_redraw()
        g_hint.config(text=tr("Gauge vom Panel entfernt (Bibliothek unberührt)."))

    def _g_config(spec, existing_index=None):
        """Parametrise ``spec``: map each needle's variable AND shape its scale +
        needle via sliders, with a live preview. A new gauge lands on the panel
        only on Übernehmen (which also saves it to the library by name); Abbrechen
        restores the gauge unchanged.
        """
        snapshot = gauge_model.to_dict(spec)  # for a faithful cancel/restore
        dlg = tk.Toplevel(win)
        dlg.title(f"Gauge parametrieren — {spec.name}")
        dlg.transient(win)
        outer = ttk.Frame(dlg, padding=12)
        outer.pack(fill="both", expand=True)
        left = ttk.Frame(outer)
        left.grid(row=0, column=0, sticky="nsew")
        right = ttk.Frame(outer)
        right.grid(row=0, column=1, sticky="n", padx=(14, 0))

        # live preview (right) — redrawn on every change, needle parked mid-scale
        pcv = tk.Canvas(right, width=300, height=300, background="#232323",
                        highlightthickness=0)
        pcv.pack()
        ttk.Label(right, text=tr("Live-Vorschau (Nadel bei ~65 %)"),
                  foreground="#666").pack(pady=(4, 0))

        def _preview(*_a):
            pcv.delete("all")
            w = max(pcv.winfo_width(), 300)
            h = max(pcv.winfo_height(), 300)
            _g_paint(pcv, spec, 6, 6, w - 12, h - 12, sample=0.65)

        pcv.bind("<Configure>", _preview)

        name_var = tk.StringVar(value=spec.name)
        top = ttk.Frame(left)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(top, text=tr("Name")).pack(side="left")
        ttk.Entry(top, textvariable=name_var, width=24).pack(side="left", padx=6)

        # one tab per needle; sliders mutate the needle live -> preview refreshes
        nbk = ttk.Notebook(left)
        nbk.grid(row=1, column=0, sticky="nsew")
        rows = []

        def _num_entry(parent, label, get, setter, width=7):
            """Labelled entry that writes ``setter`` on every valid keystroke."""
            ttk.Label(parent, text=tr(label)).pack(side="left", padx=(6, 1))
            var = tk.StringVar(value=f"{get():g}")

            def _on_write(*_a):
                try:
                    setter(float(var.get()))
                except ValueError:
                    return
                _preview()
            var.trace_add("write", _on_write)
            ttk.Entry(parent, textvariable=var, width=width).pack(side="left")
            return var

        def _slider(parent, label, lo, hi, get, setter, fmt="{:.0f}"):
            fr = ttk.Frame(parent)
            fr.pack(fill="x", pady=3)
            ttk.Label(fr, text=tr(label), width=14).pack(side="left")
            val = ttk.Label(fr, text=fmt.format(get()), width=6, foreground="#2563eb")
            val.pack(side="right")
            sc = ttk.Scale(fr, from_=lo, to=hi, value=get())

            def _cmd(v):
                fv = float(v)
                setter(fv)
                val.config(text=fmt.format(fv))
                _preview()
            sc.config(command=_cmd)
            sc.pack(side="left", fill="x", expand=True, padx=6)

        for n in spec.needles:
            tabf = ttk.Frame(nbk, padding=8)
            nbk.add(tabf, text=n.label or tr("Zeiger"))
            # --- variable + factor ---------------------------------------- #
            vrow = ttk.Frame(tabf)
            vrow.pack(fill="x", pady=(0, 4))
            v_kind = tk.StringVar(value=n.kind)
            v_var = tk.StringVar(value=n.var)
            v_factor = tk.StringVar(value=f"{n.factor:g}")
            ttk.Entry(vrow, textvariable=v_var, width=24, state="readonly").pack(side="left")

            def _pick(vk=v_kind, vv=v_var):
                _open_var_picker(win, catalog, lambda v: (vk.set(v.kind), vv.set(v.name)))
            ttk.Button(vrow, text=tr("Wählen…"), style="Accent.TButton",
                       command=_pick).pack(side="left", padx=4)
            ttk.Label(vrow, text=tr("Faktor")).pack(side="left", padx=(6, 1))
            ttk.Entry(vrow, textvariable=v_factor, width=6).pack(side="left")
            # --- value range + ticks (entries) ---------------------------- #
            r1 = ttk.Frame(tabf)
            r1.pack(fill="x", pady=2)

            def _set(attr, nn=n):
                return lambda val: setattr(nn, attr, val)
            _num_entry(r1, "min", lambda nn=n: nn.v_min, _set("v_min"))
            _num_entry(r1, "max", lambda nn=n: nn.v_max, _set("v_max"))
            _num_entry(r1, "Haupt", lambda nn=n: nn.major, _set("major"))
            _num_entry(r1, "Neben", lambda nn=n: nn.minor, _set("minor"))
            # --- scale + needle sliders (the core wish) ------------------- #
            _slider(tabf, "Winkelbereich", 20, 360, lambda nn=n: nn.sweep,
                    _set("sweep"), "{:.0f}°")
            _slider(tabf, "Startwinkel", -180, 360, lambda nn=n: nn.omega,
                    _set("omega"), "{:.0f}°")
            _slider(tabf, "Skalen-Verzerrung", 0.3, 3.0, lambda nn=n: nn.h,
                    _set("h"), "{:.2f}")
            _slider(tabf, "Radius (Nadel)", 0.2, 1.0, lambda nn=n: nn.radius,
                    _set("radius"), "{:.2f}")
            # --- placement inside a cluster face -------------------------- #
            r2 = ttk.Frame(tabf)
            r2.pack(fill="x", pady=2)
            _num_entry(r2, "Mitte X", lambda nn=n: nn.cx, _set("cx"))
            _num_entry(r2, "Mitte Y", lambda nn=n: nn.cy, _set("cy"))
            rows.append((n, v_kind, v_var, v_factor))

        # shape (whole gauge)
        srow = ttk.Frame(left)
        srow.grid(row=2, column=0, sticky="w", pady=(8, 0))
        _num_entry(srow, "Form (Breite:Höhe)", lambda: spec.aspect,
                   lambda v: setattr(spec, "aspect", v or 1.0))
        _info(srow, "1 = rund, 6 = breiter Cluster (Fuel L/R+Druck). Nadeln über "
                    "Mitte X/Y platzieren.")

        g_status = ttk.Label(left, text=tr(""), foreground="#c62828")
        g_status.grid(row=3, column=0, sticky="w", pady=(6, 0))
        btns = ttk.Frame(left)
        btns.grid(row=4, column=0, sticky="ew", pady=(8, 0))

        def _restore():
            r = gauge_model.from_dict(snapshot)
            spec.name, spec.aspect = r.name, r.aspect
            spec.needles[:] = r.needles  # keep the spec object identity

        def _cancel():
            if existing_index is not None:
                _restore()
                _g_redraw()
            dlg.destroy()

        def _apply():
            try:
                for n, vk, vv, vf in rows:
                    if n.v_min >= n.v_max:
                        raise ValueError(f"Zeiger „{n.label}“: min muss < max sein.")
                    n.kind, n.var = vk.get(), vv.get().strip()
                    n.factor = float(vf.get() or 1) or 1.0
            except ValueError as exc:
                g_status.config(text=str(exc))
                return
            spec.name = name_var.get().strip() or spec.name
            if existing_index is None:
                g_state["specs"].append(spec)
                g_state["sel"] = len(g_state["specs"]) - 1
            _g_lib_save(spec)  # callable again later by name
            _g_persist()
            _resubscribe()
            _g_redraw()
            dlg.destroy()

        ttk.Button(btns, text=tr("Übernehmen"), style="Accent.TButton",
                   command=_apply).pack(side="left")
        ttk.Button(btns, text=tr("Abbrechen"), command=_cancel).pack(side="left", padx=6)
        if spec.name in _g_library():
            def _unlib():
                _g_lib_delete(name_var.get().strip() or spec.name)
                g_status.config(text=tr("Aus der Bibliothek gelöscht (Panel unberührt)."))
            ttk.Button(btns, text=tr("Aus Bibliothek löschen"), style="Danger.TButton",
                       command=_unlib).pack(side="left", padx=6)
        dlg.protocol("WM_DELETE_WINDOW", _cancel)
        dlg.after(50, _preview)
        dlg.lift()
        dlg.focus_set()

    g_menu = tk.Menu(g_add, tearoff=0)

    def _g_menu_fill():
        g_menu.delete(0, "end")
        lib = _g_library()
        if lib:
            for name in sorted(lib):
                g_menu.add_command(
                    label=f"📚 {name}",
                    command=lambda nm=name: _g_config(gauge_model.from_dict(_g_library()[nm])),
                )
            g_menu.add_separator()
        for name in gauge_model.presets():
            g_menu.add_command(
                label=name,
                command=lambda nm=name: _g_config(gauge_model.presets()[nm]),
            )

    g_menu.configure(postcommand=_g_menu_fill)
    g_add.configure(menu=g_menu)

    gcv.bind("<Button-1>", _g_click)
    gcv.bind("<Double-Button-1>", _g_double)
    gcv.bind("<Configure>", _g_redraw)
    _g_load()
    _g_redraw()
    _g_tick()

    # ===== Settings tab ==================================================== #
    from .i18n import available_languages, code_for_name, get_language, language_name, set_language

    settab = ttk.Frame(nb, padding=12)
    nb.add(settab, text=tr("tab.settings"))
    settab.columnconfigure(0, weight=1)

    lang_fr = ttk.Labelframe(settab, text=tr("settings.language_group"), padding=12)
    lang_fr.grid(row=0, column=0, sticky="ew")
    lang_fr.columnconfigure(1, weight=1)

    ttk.Label(lang_fr, text=tr("settings.language_label")).grid(row=0, column=0,
                                                                sticky="w", padx=(0, 10))
    lang_var = tk.StringVar(value=language_name(get_language()))
    lang_box = ttk.Combobox(lang_fr, values=list(available_languages().values()),
                            textvariable=lang_var, state="readonly", width=18)
    lang_box.grid(row=0, column=1, sticky="w")

    ttk.Label(lang_fr, text=tr("settings.language_hint"), foreground=MUTED,
              font=("TkDefaultFont", 8), wraplength=520, justify="left"
              ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))
    restart_note = ttk.Label(lang_fr, text=tr(""), foreground=DANGER)
    restart_note.grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))

    def _on_lang_change(_e=None):
        code = code_for_name(lang_var.get())
        save_language(code)   # persist immediately so the choice is remembered
        set_language(code)
        restart_note.config(text=tr("settings.restart_needed"))

    lang_box.bind("<<ComboboxSelected>>", _on_lang_change)

    def _restart_gui():
        # The bridge/mapper run in their own process groups and survive the exec,
        # so a language restart never interrupts a running session.
        with contextlib.suppress(Exception):
            win.destroy()
        try:
            os.execv(sys.executable, [sys.executable, "-m", "msfs_peripherals_bridge.gui"])
        except OSError as exc:  # pragma: no cover - platform dependent
            messagebox.showinfo(tr("dialog.note"), str(exc))

    ttk.Button(lang_fr, text=tr("settings.apply_restart"), style="Accent.TButton",
               command=_restart_gui).grid(row=3, column=0, columnspan=2, sticky="w", pady=(10, 0))

    # tab order per user (2026-07-17): Mapper after Connection, then Statistik,
    # Gauges to its right, Profile, Settings last. nb.insert() on an already-managed
    # child just moves it.
    for pos, tab in enumerate((conn, mtab, stab, gtab, ptab, settab)):
        nb.insert(pos, tab)

    # --- bottom status bar (small lamps) ----------------------------------- #
    ttk.Separator(win, orient="horizontal").grid(row=2, column=0, sticky="ew", pady=(8, 0))
    bar = ttk.Frame(win, padding=(10, 3))
    bar.grid(row=3, column=0, sticky="ew")
    ttk.Label(bar, text=tr("status.label"), foreground="#666",
              font=("TkDefaultFont", 8)).pack(side="left", padx=(0, 8))
    lamps: dict[str, tk.Label] = {}
    for key in ("MSFS", "Bridge", "Mapper"):
        lamp = tk.Label(bar, text=f"● {key}", font=("TkDefaultFont", 8), fg="#999")
        lamp.pack(side="left", padx=(0, 12))
        lamps[key] = lamp

    # Active profile, always visible (right edge of the status bar + the window
    # title) — the selector itself lives on the Profile tab and can be hidden.
    prof_badge = tk.Label(bar, text=tr(""), font=("TkDefaultFont", 9, "bold"), fg="#1565c0")
    prof_badge.pack(side="right")
    ttk.Label(bar, text=tr("status.profile"), foreground="#666",
              font=("TkDefaultFont", 8)).pack(side="right", padx=(0, 4))

    def _update_profile_badge(*_):
        prof_badge.config(text=profile_var.get())
        win.title(f"MSFS Peripherals Bridge — {profile_var.get()}")

    profile_var.trace_add("write", _update_profile_badge)
    _update_profile_badge()

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
        mon_state.config(text=tr("● live") if bridge_up else "Bridge aus")
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
