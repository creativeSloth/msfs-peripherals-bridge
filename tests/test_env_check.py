"""Tests for the bridge prerequisite checker (pure filesystem probes)."""

from __future__ import annotations

from pathlib import Path

from msfs_peripherals_bridge import env_check


def _make_prefix(tmp_path: Path, *, with_python=True, with_dll=True) -> Path:
    """Build a fake pfx tree; return the pfx dir."""
    pfx = tmp_path / "compatdata" / "1250410" / "pfx"
    pybridge = pfx / "drive_c" / "pybridge"
    pybridge.mkdir(parents=True)
    if with_python:
        (pybridge / "pythonw.exe").write_text("")
        (pybridge / "python.exe").write_text("")
    if with_dll:
        sc = pybridge / "Lib" / "site-packages" / "SimConnect"
        sc.mkdir(parents=True)
        (sc / "SimConnect.dll").write_text("")
    return pfx


def _make_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "bridge").mkdir(parents=True)
    (root / "bridge" / "run-bridge.sh").write_text("")
    (root / "bridge" / "bridge.py").write_text("")
    return root


def test_normalise_prefix_accepts_pfx_or_parent(tmp_path):
    pfx = _make_prefix(tmp_path)
    assert env_check.normalise_prefix(pfx) == pfx
    # Pointing at the compatdata/<AppID> parent resolves down to pfx.
    assert env_check.normalise_prefix(pfx.parent) == pfx


def test_normalise_prefix_passes_through_unknown(tmp_path):
    ghost = tmp_path / "nope"
    assert env_check.normalise_prefix(ghost) == ghost


def test_all_prerequisites_present(tmp_path, monkeypatch):
    pfx = _make_prefix(tmp_path)
    repo = _make_repo(tmp_path)
    # find_proton() must succeed regardless of the host machine.
    proton = tmp_path / "proton"
    proton.write_text("")
    proton.chmod(0o755)
    monkeypatch.setenv("PROTON_PATH", str(proton))

    items = {c.key: c for c in env_check.check_prerequisites(pfx, repo)}
    assert all(c.ok for c in items.values()), {k: c.ok for k, c in items.items()}
    assert items["check.simconnect"].detail.endswith("SimConnect.dll")


def test_missing_python_and_dll_flagged(tmp_path, monkeypatch):
    pfx = _make_prefix(tmp_path, with_python=False, with_dll=False)
    repo = _make_repo(tmp_path)
    monkeypatch.delenv("PROTON_PATH", raising=False)

    items = {c.key: c for c in env_check.check_prerequisites(pfx, repo)}
    assert items["check.prefix"].ok
    assert not items["check.pythonw"].ok
    assert not items["check.python"].ok
    assert not items["check.simconnect"].ok


def test_bridge_env_points_at_parent(tmp_path):
    pfx = _make_prefix(tmp_path)
    env = env_check.bridge_env(pfx)
    assert env == {"STEAM_COMPAT_DATA_PATH": str(pfx.parent)}


def test_bridge_env_empty_for_blank():
    assert env_check.bridge_env(None) == {}
    assert env_check.bridge_env("") == {}
    assert env_check.bridge_env("   ") == {}


def test_simconnect_versioned_dir(tmp_path, monkeypatch):
    pfx = _make_prefix(tmp_path, with_dll=False)
    repo = _make_repo(tmp_path)
    # SimConnect installed under a version-suffixed package dir.
    sc = pfx / "drive_c" / "pybridge" / "Lib" / "site-packages" / "SimConnect-0.4.26"
    sc.mkdir(parents=True)
    (sc / "SimConnect.dll").write_text("")
    items = {c.key: c for c in env_check.check_prerequisites(pfx, repo)}
    assert items["check.simconnect"].ok
