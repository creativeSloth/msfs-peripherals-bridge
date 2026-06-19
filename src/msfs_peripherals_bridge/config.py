"""Resolve project paths (config + profiles) with sensible defaults.

Order of precedence: explicit CLI argument > $MSFS_BRIDGE_HOME > the repo
checkout the package was installed from > the current working directory.
"""

from __future__ import annotations

import os
from pathlib import Path


def project_root() -> Path:
    env = os.environ.get("MSFS_BRIDGE_HOME")
    if env:
        return Path(env).expanduser()
    # src/msfs_peripherals_bridge/config.py -> repo root is three levels up.
    candidate = Path(__file__).resolve().parents[2]
    if (candidate / "profiles").is_dir():
        return candidate
    return Path.cwd()


def profiles_dir(root: Path | None = None) -> Path:
    return (root or project_root()) / "profiles"


def devices_file(root: Path | None = None) -> Path:
    return (root or project_root()) / "config" / "devices.yaml"


def calibration_file(root: Path | None = None) -> Path:
    return (root or project_root()) / "config" / "calibration.yaml"
