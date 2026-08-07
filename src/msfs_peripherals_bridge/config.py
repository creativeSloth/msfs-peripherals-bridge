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


def _user_config_dir() -> Path:
    """Per-user config dir (``$XDG_CONFIG_HOME`` or ``~/.config``), outside repo."""
    base = os.environ.get("XDG_CONFIG_HOME")
    root = Path(base).expanduser() if base else Path.home() / ".config"
    return root / "msfs-peripherals-bridge"


def gui_settings_file() -> Path:
    """Per-user GUI state (e.g. the Statistik var selection), outside the repo.

    Honours ``$XDG_CONFIG_HOME`` and falls back to ``~/.config``; the file is
    user-specific and must not be committed with the checkout.
    """
    return _user_config_dir() / "gui-settings.json"


def devices_overlay_file() -> Path:
    """User-added devices (the device explorer writes here), outside the repo.

    Keeps a stranger's own hardware out of the versioned ``config/devices.yaml``;
    :func:`~..mapping.loader.load_device_catalog` merges this overlay on top of
    the bundled catalog automatically.
    """
    return _user_config_dir() / "devices.local.yaml"


def output_templates_file() -> Path:
    """User-created output-block templates (the mapper's "als Vorlage speichern").

    A whole panel arrangement (buttons + displays) saved under a name so it can be
    dropped onto another device in one go, alongside the bundled Saitek templates.
    Per-user, outside the repo.
    """
    return _user_config_dir() / "output-templates.yaml"
