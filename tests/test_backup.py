"""Tests for the backup/restore bundle (export -> import round-trip)."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from msfs_peripherals_bridge import backup


def _make_source(tmp_path: Path) -> tuple[Path, Path]:
    """A fake repo (profiles + calibration) and a fake per-user config dir."""
    root = tmp_path / "repo"
    (root / "profiles").mkdir(parents=True)
    (root / "profiles" / "piper_arrow.yaml").write_text("name: piper\n")
    (root / "profiles" / "cessna_172.yaml").write_text("name: c172\n")
    (root / "config").mkdir()
    (root / "config" / "calibration.yaml").write_text("cal: 1\n")

    udir = tmp_path / "userconf"
    (udir / "sub").mkdir(parents=True)
    (udir / "panel-layouts.yaml").write_text("layout: x\n")
    (udir / "sub" / "gui-settings.json").write_text("{}")
    return root, udir


def test_export_import_roundtrip(tmp_path):
    root, udir = _make_source(tmp_path)

    dest = tmp_path / "backup"  # no .zip suffix — export must add it
    res = backup.export_config(dest, root=root, user_dir=udir)
    assert res.path.suffix == ".zip"
    assert res.path.is_file()
    assert res.profiles == 2
    assert res.calibration is True
    assert res.user_files == 2

    # Restore into fresh, empty destinations.
    root2 = tmp_path / "repo2"
    udir2 = tmp_path / "userconf2"
    r = backup.import_config(res.path, root=root2, user_dir=udir2)

    assert (root2 / "profiles" / "piper_arrow.yaml").read_text() == "name: piper\n"
    assert (root2 / "profiles" / "cessna_172.yaml").read_text() == "name: c172\n"
    assert (root2 / "config" / "calibration.yaml").read_text() == "cal: 1\n"
    assert (udir2 / "panel-layouts.yaml").read_text() == "layout: x\n"
    assert (udir2 / "sub" / "gui-settings.json").read_text() == "{}"
    assert set(r.profiles) == {"piper_arrow.yaml", "cessna_172.yaml"}
    assert r.calibration is True
    assert "panel-layouts.yaml" in r.user_files
    assert "sub/gui-settings.json" in r.user_files


def test_import_overwrites_existing(tmp_path):
    root, udir = _make_source(tmp_path)
    res = backup.export_config(tmp_path / "b.zip", root=root, user_dir=udir)

    # A stale profile already present at the destination gets overwritten.
    root2 = tmp_path / "repo2"
    (root2 / "profiles").mkdir(parents=True)
    (root2 / "profiles" / "piper_arrow.yaml").write_text("name: STALE\n")
    backup.import_config(res.path, root=root2, user_dir=tmp_path / "u2")
    assert (root2 / "profiles" / "piper_arrow.yaml").read_text() == "name: piper\n"


def test_read_manifest(tmp_path):
    root, udir = _make_source(tmp_path)
    res = backup.export_config(tmp_path / "b.zip", root=root, user_dir=udir)
    m = backup.read_manifest(res.path)
    assert m["version"] == backup.MANIFEST_VERSION
    assert m["profiles"] == 2
    assert m["calibration"] is True


def test_import_rejects_non_backup(tmp_path):
    z = tmp_path / "random.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("foo.txt", "bar")
    with pytest.raises(ValueError):
        backup.import_config(z, root=tmp_path / "r", user_dir=tmp_path / "u")


def test_import_blocks_path_traversal(tmp_path):
    z = tmp_path / "evil.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr(backup.MANIFEST_NAME, json.dumps({"version": 1}))
        zf.writestr("profiles/../../escape.yaml", "pwned")
    with pytest.raises(ValueError):
        backup.import_config(z, root=tmp_path / "r", user_dir=tmp_path / "u")
    assert not (tmp_path / "escape.yaml").exists()


def test_export_skips_missing_pieces(tmp_path):
    # A repo with no calibration and no user dir still exports the profiles.
    root = tmp_path / "repo"
    (root / "profiles").mkdir(parents=True)
    (root / "profiles" / "a.yaml").write_text("name: a\n")
    res = backup.export_config(tmp_path / "b.zip", root=root, user_dir=tmp_path / "absent")
    assert res.profiles == 1
    assert res.calibration is False
    assert res.user_files == 0
