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
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from .config import profiles_dir, project_root

BRIDGE_PORT = 7842
_POLL_MS = 1000  # status refresh cadence


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


def _snapshot_values(
    names, *, host: str = "127.0.0.1", port: int = BRIDGE_PORT, window: float = 0.8
):
    """Open a short-lived bridge connection, subscribe to ``names`` and collect the
    latest streamed value for each over ~``window`` seconds. Returns {name: value}.

    The bridge is single-client, so the caller must ensure the mapper is stopped —
    otherwise this connect fights it."""
    import json
    import socket

    result: dict[str, object] = {}
    try:
        sock = socket.create_connection((host, port), timeout=2)
    except OSError:
        return result
    with sock:
        for name in names:
            sock.sendall((json.dumps({"op": "subscribe", "name": name}) + "\n").encode())
        sock.settimeout(window)
        end = time.monotonic() + window
        buf = b""
        while time.monotonic() < end:
            try:
                chunk = sock.recv(65536)
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
                    result[msg.get("name")] = msg.get("value")
    return result


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

    win = tk.Tk()
    win.title("MSFS Peripherals Bridge — Control")
    win.minsize(480, 400)
    win.columnconfigure(0, weight=1)
    win.rowconfigure(1, weight=1)  # the notebook grows

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

    tree = ttk.Treeview(stab, columns=("kind", "name", "unit", "value"),
                        show="headings", height=10)
    for col, head, w, anchor in (
        ("kind", "Typ", 44, "center"), ("name", "Variable", 260, "w"),
        ("unit", "Einheit", 74, "center"), ("value", "Wert", 90, "center"),
    ):
        tree.heading(col, text=head)
        tree.column(col, width=w, anchor=anchor)
    tree.grid(row=1, column=0, columnspan=3, sticky="nsew", pady=6)
    tsb = ttk.Scrollbar(stab, orient="vertical", command=tree.yview)
    tsb.grid(row=1, column=3, sticky="ns", pady=6)
    tree.config(yscrollcommand=tsb.set)

    def add_var(v):
        key = f"{v.kind}\t{v.name}"
        if tree.exists(key):
            return
        tree.insert("", "end", iid=key, values=(v.kind, v.name, v.unit, "—"))

    def remove_selected():
        for iid in tree.selection():
            tree.delete(iid)

    def read_values():
        names = [tree.set(iid, "name") for iid in tree.get_children("")]
        if not names:
            return
        if mapper["ctl"] is not None and mapper["ctl"].is_running():
            messagebox.showinfo(
                "Werte lesen",
                "Der Mapper hält die (single-client-)Bridge belegt.\n"
                "Für einen Snapshot bitte kurz den Mapper stoppen.\n\n"
                "Dauerhaftes Mitlesen während des Mappens braucht eine "
                "Multi-Client-Bridge (siehe Konzept).",
            )
            return
        if not _port_listening(BRIDGE_PORT):
            messagebox.showinfo("Werte lesen", "Bridge läuft nicht (Port 7842 ist zu).")
            return
        vals = _snapshot_values(names)
        for iid in tree.get_children(""):
            nm = tree.set(iid, "name")
            if nm in vals:
                tree.set(iid, "value", _fmt_value(vals[nm]))

    sbtn = ttk.Frame(stab)
    sbtn.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(6, 0))
    b_add = ttk.Button(sbtn, text="Variable hinzufügen …",
                       command=lambda: _open_var_picker(win, catalog, add_var))
    b_rm = ttk.Button(sbtn, text="Entfernen", command=remove_selected)
    b_read = ttk.Button(sbtn, text="Werte lesen (Snapshot)", command=read_values)
    b_add.pack(side="left")
    b_rm.pack(side="left", padx=6)
    b_read.pack(side="left")
    _attach_tooltip(b_add, "Popup: nach Typ (A:/K:/L:) filtern + Namen suchen")
    _attach_tooltip(b_read, "Kurz subscriben + aktuellen Wert lesen (Mapper muss aus sein)")

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
        _set_lamp("Bridge", _port_listening(BRIDGE_PORT))
        _set_lamp("Mapper", mapper["ctl"] is not None and mapper["ctl"].is_running())
        win.after(_POLL_MS, refresh)

    def _on_close():
        # Don't orphan the mapper this GUI started (it would keep stealing the
        # single-client bridge slot). Leave the bridge up — it is meant to persist.
        stop_mapper()
        win.destroy()

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
