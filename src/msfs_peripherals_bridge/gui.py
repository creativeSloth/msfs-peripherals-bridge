"""Minimal Tkinter control panel to start/stop the bridge and the mapper.

Phase 1 (see memory `project-process-gui`): four buttons + status lamps. Kept
deliberately small but structured to grow into a graphical profile editor later
(profile switching, device auto-mapping, a category-filtered var picker, condition
builder). Launch:  uv run python -m msfs_peripherals_bridge.gui

Process model: each managed process is started in its OWN process group
(``start_new_session=True``) and stopped with ``killpg`` — so the whole chain
(bridge supervisor -> bridge.py -> Proton/Wine) goes down cleanly, and we never
risk the pkill-hits-its-own-shell trap. A dependency-free ``/proc`` sweep mops up
any Proton child that escaped the group.
"""

from __future__ import annotations

import contextlib
import os
import signal
import socket
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


def _port_open(port: int, host: str = "127.0.0.1") -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.3):
            return True
    except OSError:
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
# GUI
# --------------------------------------------------------------------------- #
def _list_profiles(root: Path) -> list[str]:
    try:
        return sorted(p.stem for p in profiles_dir(root).glob("*.yaml"))
    except OSError:
        return ["piper_arrow"]


def run() -> None:
    import tkinter as tk
    from tkinter import ttk

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

    win = tk.Tk()
    win.title("MSFS Peripherals Bridge — Control")
    win.minsize(360, 240)
    win.columnconfigure(0, weight=1)

    profile_var = tk.StringVar(value=default_profile)
    mapper = {"ctl": None}  # rebuilt on start so a profile change takes effect

    def make_mapper() -> ProcessController:
        return ProcessController(
            "mapper",
            ["uv", "run", "python", "-m", "msfs_peripherals_bridge", "run",
             "--profile", profile_var.get()],
            cwd=root_dir,
        )

    # --- status row -------------------------------------------------------- #
    status = ttk.LabelFrame(win, text="Status", padding=8)
    status.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
    lamps: dict[str, tk.Label] = {}
    for i, key in enumerate(("MSFS", "Bridge", "Mapper")):
        ttk.Label(status, text=key).grid(row=i, column=0, sticky="w", pady=2)
        lamp = tk.Label(status, text="  ?  ", width=8, relief="ridge")
        lamp.grid(row=i, column=1, sticky="e", padx=6)
        lamps[key] = lamp
    status.columnconfigure(1, weight=1)

    # --- profile ----------------------------------------------------------- #
    prow = ttk.Frame(win, padding=(10, 0))
    prow.grid(row=1, column=0, sticky="ew")
    ttk.Label(prow, text="Profil:").pack(side="left")
    ttk.Combobox(prow, textvariable=profile_var, values=profiles, state="readonly",
                 width=18).pack(side="left", padx=6)
    ttk.Label(prow, text="(wirkt beim nächsten Mapper-Start)").pack(side="left")

    # --- buttons ----------------------------------------------------------- #
    btns = ttk.Frame(win, padding=10)
    btns.grid(row=2, column=0, sticky="ew")
    for c in range(2):
        btns.columnconfigure(c, weight=1)

    def start_bridge():
        bridge.start()

    def stop_bridge():
        bridge.stop()
        _sweep("bridge/bridge.py")      # mop up any escaped Proton child
        _sweep("bridge/run-bridge.sh")  # and the supervisor if started elsewhere

    def start_mapper():
        if mapper["ctl"] is None or not mapper["ctl"].is_running():
            mapper["ctl"] = make_mapper()
        mapper["ctl"].start()

    def stop_mapper():
        if mapper["ctl"] is not None:
            mapper["ctl"].stop()

    b_bs = ttk.Button(btns, text="Bridge starten", command=start_bridge)
    b_bx = ttk.Button(btns, text="Bridge stoppen", command=stop_bridge)
    b_ms = ttk.Button(btns, text="Mapper starten", command=start_mapper)
    b_mx = ttk.Button(btns, text="Mapper stoppen", command=stop_mapper)
    b_bs.grid(row=0, column=0, sticky="ew", padx=3, pady=3)
    b_bx.grid(row=0, column=1, sticky="ew", padx=3, pady=3)
    b_ms.grid(row=1, column=0, sticky="ew", padx=3, pady=3)
    b_mx.grid(row=1, column=1, sticky="ew", padx=3, pady=3)

    hint = ttk.Label(win, padding=(10, 0),
                     text="Hinweis: Bridge ist single-client — Mapper ODER ein Tool.")
    hint.grid(row=3, column=0, sticky="w", pady=(0, 8))

    def _set_lamp(lamp: tk.Label, on: bool, on_text="AN", off_text="AUS"):
        lamp.config(text=f" {on_text if on else off_text} ",
                    bg="#2e7d32" if on else "#c62828", fg="white")

    def refresh():
        bridge.poll()
        if mapper["ctl"] is not None:
            mapper["ctl"].poll()
        _set_lamp(lamps["MSFS"], _msfs_running())
        _set_lamp(lamps["Bridge"], _port_open(BRIDGE_PORT), on_text="LÄUFT", off_text="AUS")
        _set_lamp(lamps["Mapper"], mapper["ctl"] is not None and mapper["ctl"].is_running())
        win.after(_POLL_MS, refresh)

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
