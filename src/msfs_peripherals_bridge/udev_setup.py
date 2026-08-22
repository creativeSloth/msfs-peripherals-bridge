"""Install the flight-sim udev rules from within the app.

The shipped rule file (``999-flightsim-override.rules``) is what makes the
panels/yoke readable for a normal user (and stops the panels being grabbed as a
mouse). Installing it needs root, so the GUI runs the privileged helper
``tools/install-udev-rules.sh`` through ``pkexec``, which pops a graphical
password prompt — the user never touches a terminal.

Everything here is a pure PATH/filesystem probe (no root, no tkinter) so it is
testable; the GUI owns the actual subprocess.
"""

from __future__ import annotations

import shutil
from pathlib import Path

RULE_FILENAME = "999-flightsim-override.rules"
DEST_PATH = Path("/etc/udev/rules.d/99-flightsim.rules")


def source_rule(repo_root: Path) -> Path:
    """The rule file shipped in the repo."""
    return repo_root / RULE_FILENAME


def install_script(repo_root: Path) -> Path:
    """The privileged helper that copies the rule file and reloads udev."""
    return repo_root / "tools" / "install-udev-rules.sh"


def is_installed(repo_root: Path, dest: Path = DEST_PATH) -> bool:
    """True only when the installed rules match the shipped file byte-for-byte.

    Byte-equality (not mere presence) so an outdated copy reads as *not* up to
    date and the user is prompted to re-install.
    """
    if not dest.is_file():
        return False
    try:
        return dest.read_bytes() == source_rule(repo_root).read_bytes()
    except OSError:
        return False


def has_pkexec() -> bool:
    """Whether a graphical privilege prompt (polkit's pkexec) is available."""
    return shutil.which("pkexec") is not None


def install_argv(repo_root: Path) -> list[str] | None:
    """Privileged command to install the rules with a graphical password prompt.

    Returns a ``pkexec …`` argv, or ``None`` when pkexec is unavailable — the
    caller then shows the manual ``sudo`` fallback instead.
    """
    pkexec = shutil.which("pkexec")
    if pkexec is None:
        return None
    return [pkexec, str(install_script(repo_root))]
