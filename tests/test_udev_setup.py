"""Tests for the in-app udev rule installer (pure PATH/filesystem logic)."""

from __future__ import annotations

from pathlib import Path

from msfs_peripherals_bridge import udev_setup


def _make_repo(tmp_path: Path, rule_body: str = "RULE\n") -> Path:
    root = tmp_path / "repo"
    (root / "tools").mkdir(parents=True)
    (root / udev_setup.RULE_FILENAME).write_text(rule_body)
    (root / "tools" / "install-udev-rules.sh").write_text("#!/usr/bin/env bash\n")
    return root


def test_paths_point_into_repo(tmp_path):
    repo = _make_repo(tmp_path)
    assert udev_setup.source_rule(repo).name == udev_setup.RULE_FILENAME
    assert udev_setup.install_script(repo) == repo / "tools" / "install-udev-rules.sh"


def test_is_installed_false_when_dest_missing(tmp_path):
    repo = _make_repo(tmp_path)
    assert not udev_setup.is_installed(repo, dest=tmp_path / "absent.rules")


def test_is_installed_true_on_byte_match(tmp_path):
    repo = _make_repo(tmp_path, "SAME\n")
    dest = tmp_path / "installed.rules"
    dest.write_text("SAME\n")
    assert udev_setup.is_installed(repo, dest=dest)


def test_is_installed_false_on_content_drift(tmp_path):
    repo = _make_repo(tmp_path, "NEW VERSION\n")
    dest = tmp_path / "installed.rules"
    dest.write_text("OLD VERSION\n")
    assert not udev_setup.is_installed(repo, dest=dest)


def test_install_argv_uses_pkexec_when_present(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    monkeypatch.setattr(udev_setup.shutil, "which", lambda _n: "/usr/bin/pkexec")
    argv = udev_setup.install_argv(repo)
    assert argv == ["/usr/bin/pkexec", str(udev_setup.install_script(repo))]


def test_install_argv_none_without_pkexec(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    monkeypatch.setattr(udev_setup.shutil, "which", lambda _n: None)
    assert udev_setup.install_argv(repo) is None
    assert not udev_setup.has_pkexec()
