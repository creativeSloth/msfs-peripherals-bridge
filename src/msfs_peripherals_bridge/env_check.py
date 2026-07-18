"""Pure prerequisite checks for the bridge runtime.

The Connection tab shows a green-check / red-cross list of everything the bridge
needs to launch: the MSFS Proton prefix, the Windows Python installed into it,
``SimConnect.dll``, the Proton runtime and the repo-side launch scripts. All of
it is a plain filesystem probe with no tkinter dependency, so it is a testable
function returning :class:`CheckItem` records (``key`` is an i18n key resolved
by the GUI).

Mirrors the path layout of ``bridge/run-bridge.sh`` and ``bridge/setup-prefix.sh``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_APPID = "1250410"  # MSFS 2020 Steam
DEFAULT_PROTON = "Proton - Experimental"


@dataclass(frozen=True)
class CheckItem:
    """One prerequisite line: an i18n ``key``, whether it's satisfied, and the
    resolved path (or a short reason) to show muted beside it."""

    key: str
    ok: bool
    detail: str


def _steam_root() -> Path:
    return Path(os.environ.get("STEAM_ROOT", Path.home() / ".steam" / "steam"))


def default_prefix(appid: str = DEFAULT_APPID) -> Path:
    """The Steam/Proton pfx dir for ``appid`` under the default Steam root."""
    return _steam_root() / "steamapps" / "compatdata" / appid / "pfx"


def find_proton(name: str = DEFAULT_PROTON) -> Path | None:
    """Locate an executable Proton build across the usual Steam library roots."""
    env_path = os.environ.get("PROTON_PATH")
    if env_path:
        p = Path(env_path)
        return p if p.is_file() and os.access(p, os.X_OK) else None
    for base in (
        _steam_root() / "steamapps" / "common",
        Path.home() / ".local" / "share" / "Steam" / "steamapps" / "common",
        Path.home() / ".steam" / "root" / "steamapps" / "common",
    ):
        candidate = base / name / "proton"
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    return None


def normalise_prefix(path: str | os.PathLike[str]) -> Path:
    """Return the pfx directory whether the user pointed at it or its parent.

    Accepts the ``…/pfx`` dir itself, or the ``…/compatdata/<AppID>`` dir that
    contains it. If neither shape is on disk yet, the path is returned as given
    (so the checks can still report it missing).
    """
    p = Path(path).expanduser()
    if (p / "drive_c").is_dir():
        return p
    if (p / "pfx" / "drive_c").is_dir():
        return p / "pfx"
    return p


def resolve_prefix(prefix: str | os.PathLike[str] | None) -> Path:
    """The pfx dir to use: the (normalised) configured one, or the default."""
    if prefix:
        text = str(prefix).strip()
        if text:
            return normalise_prefix(text)
    return default_prefix()


def _simconnect_dll(pybridge: Path) -> Path | None:
    """Locate SimConnect.dll inside the prefix's site-packages (version-tolerant)."""
    direct = pybridge / "Lib" / "site-packages" / "SimConnect" / "SimConnect.dll"
    if direct.is_file():
        return direct
    matches = list(pybridge.glob("Lib/site-packages/SimConnect*/SimConnect.dll"))
    return matches[0] if matches else None


def check_prerequisites(
    prefix: str | os.PathLike[str] | None,
    repo_root: Path,
) -> list[CheckItem]:
    """Probe everything the bridge needs and return one CheckItem per condition."""
    pfx = resolve_prefix(prefix)
    drive_c = pfx / "drive_c"
    pybridge = drive_c / "pybridge"
    pythonw = pybridge / "pythonw.exe"
    python = pybridge / "python.exe"
    dll = _simconnect_dll(pybridge)
    proton = find_proton()
    run_bridge = repo_root / "bridge" / "run-bridge.sh"
    bridge_py = repo_root / "bridge" / "bridge.py"

    return [
        CheckItem("check.prefix", pfx.is_dir(), str(pfx)),
        CheckItem("check.drive_c", drive_c.is_dir(), str(drive_c)),
        CheckItem("check.pythonw", pythonw.is_file(), str(pythonw)),
        CheckItem("check.python", python.is_file(), str(python)),
        CheckItem("check.simconnect", dll is not None,
                  str(dll) if dll else str(pybridge / "Lib" / "site-packages" / "SimConnect")),
        CheckItem("check.proton", proton is not None, str(proton) if proton else "—"),
        CheckItem("check.run_bridge", run_bridge.is_file(), str(run_bridge)),
        CheckItem("check.bridge_py", bridge_py.is_file(), str(bridge_py)),
    ]


def bridge_env(prefix: str | os.PathLike[str] | None) -> dict[str, str]:
    """Environment overrides so ``run-bridge.sh`` targets the configured prefix.

    ``run-bridge.sh`` derives ``PREFIX = $STEAM_COMPAT_DATA_PATH/pfx`` (and Proton
    itself resolves the same path), so we point ``STEAM_COMPAT_DATA_PATH`` at the
    parent of the pfx dir. Empty/None configuration yields no overrides — the
    script keeps its built-in Steam auto-detection.
    """
    if not prefix or not str(prefix).strip():
        return {}
    pfx = normalise_prefix(str(prefix).strip())
    return {"STEAM_COMPAT_DATA_PATH": str(pfx.parent)}
