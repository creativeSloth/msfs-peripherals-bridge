"""The GUI's startup-failure path: a missing Tk must name the right package.

Tk is the one dependency ``uv sync`` cannot supply — it comes from the
distribution — so the crash message has to say which package to install on
*this* machine instead of guessing Debian's name everywhere.
"""

from __future__ import annotations

import pytest

from msfs_peripherals_bridge import gui


@pytest.mark.parametrize(
    ("tools", "expected"),
    [
        (["apt-get"], "sudo apt-get install python3-tk"),
        (["dnf"], "sudo dnf install python3-tkinter tk"),
        (["pacman"], "sudo pacman -S tk"),
        (["zypper"], "sudo zypper install python3-tk"),
        ([], "python3-tk / python3-tkinter / tk"),
    ],
)
def test_hint_matches_the_package_manager(monkeypatch, tools, expected):
    monkeypatch.setattr("shutil.which", lambda tool: tool if tool in tools else None)
    assert gui.tk_install_hint() == expected


def _raise(exc):
    def _run():
        raise exc

    return _run


def test_missing_tk_prints_the_install_command(monkeypatch, capsys):
    monkeypatch.setattr("shutil.which", lambda tool: tool if tool == "pacman" else None)
    monkeypatch.setattr(
        gui, "run", _raise(ImportError("libtk8.6.so: cannot open shared object file"))
    )

    with pytest.raises(SystemExit) as exc:
        gui.main()

    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "libtk8.6.so" in err  # the original cause stays visible
    assert "sudo pacman -S tk" in err
    assert "./install.sh" in err


def test_other_failures_point_at_the_display(monkeypatch, capsys):
    monkeypatch.setattr(gui, "run", _raise(RuntimeError("no display name and no $DISPLAY")))

    with pytest.raises(SystemExit):
        gui.main()

    err = capsys.readouterr().err
    assert "DISPLAY" in err
    assert "install" not in err.lower()  # not a package problem — don't send them shopping
