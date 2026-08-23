"""Round-trip tests for the per-device share package (device_package)."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest
import yaml

from msfs_peripherals_bridge import device_package as dp


def _make_root(tmp_path: Path) -> Path:
    """A minimal repo layout: config/devices.yaml, config/calibration.yaml, profiles/."""
    root = tmp_path / "repo"
    (root / "config").mkdir(parents=True)
    (root / "profiles").mkdir(parents=True)
    (root / "config" / "devices.yaml").write_text(
        yaml.safe_dump(
            {"devices": [{"id": "yoke", "name": "Test Yoke", "vendor": "1234", "product": "5678"}]}
        )
    )
    (root / "config" / "calibration.yaml").write_text(
        yaml.safe_dump(
            {
                "devices": {
                    "yoke": {
                        "device_id": "yoke",
                        "axes": {
                            0: {
                                "code": 0,
                                "name": "ABS_X",
                                "raw_min": 0,
                                "raw_max": 4095,
                                "center": 2048,
                            }
                        },
                        "buttons": [288],
                        "hats": [],
                    }
                }
            }
        )
    )
    (root / "profiles" / "src.yaml").write_text(
        "name: Src\n"
        "aircraft_match: [ TestPlane ]\n"
        "bindings:\n"
        "  yoke:\n"
        "    - { name: Aileron, source: { kind: axis, code: 0, raw_min: 0, raw_max: 4095 },"
        " action: { type: event, event: AILERON_SET } }\n"
    )
    (root / "profiles" / "dst.yaml").write_text(
        "name: Dst\naircraft_match: [ Other ]\nbindings: {}\n"
    )
    return root


def _make_user_dir(tmp_path: Path) -> Path:
    udir = tmp_path / "user"
    udir.mkdir()
    (udir / "panel-layouts.yaml").write_text(
        yaml.safe_dump(
            {"devices": {"yoke": {"btn:288": [0.5, 0.5], "axis:0": [0.1, 0.2, 0.3, 0.4]}}}
        )
    )
    return udir


def test_export_writes_all_four_parts(tmp_path):
    root, udir = _make_root(tmp_path), _make_user_dir(tmp_path)
    res = dp.export_device_package("yoke", "src", tmp_path / "pkg", root=root, user_dir=udir)
    assert res.path.name == "pkg.zip"
    assert (res.bindings, res.outputs) == (1, 0)
    assert res.has_layout and res.has_calibration
    with zipfile.ZipFile(res.path) as z:
        names = set(z.namelist())
    assert names == {
        dp._DEVICE_NAME,
        dp._MAPPING_NAME,
        dp._LAYOUT_NAME,
        dp._CALIBRATION_NAME,
        dp.MANIFEST_NAME,
    }


def test_manifest_records_device_and_source(tmp_path):
    root, udir = _make_root(tmp_path), _make_user_dir(tmp_path)
    pkg = dp.export_device_package("yoke", "src", tmp_path / "pkg", root=root, user_dir=udir).path
    m = dp.read_manifest(pkg)
    assert m["kind"] == "device-package"
    assert m["device_id"] == "yoke"
    assert m["device_name"] == "Test Yoke"
    assert m["source_profile"] == "src"


def test_round_trip_into_fresh_environment(tmp_path):
    src_root, src_udir = _make_root(tmp_path / "a"), _make_user_dir(tmp_path / "a")
    pkg = dp.export_device_package(
        "yoke", "src", tmp_path / "pkg", root=src_root, user_dir=src_udir
    ).path

    # A clean importer: no device catalog entry, empty target profile, empty user dir.
    dst_root = tmp_path / "b" / "repo"
    (dst_root / "config").mkdir(parents=True)
    (dst_root / "profiles").mkdir(parents=True)
    (dst_root / "config" / "devices.yaml").write_text(yaml.safe_dump({"devices": []}))
    (dst_root / "profiles" / "target.yaml").write_text(
        "name: Target\naircraft_match: [ X ]\nbindings: {}\n"
    )
    dst_udir = tmp_path / "b" / "user"
    dst_udir.mkdir(parents=True)

    res = dp.import_device_package(pkg, "target", root=dst_root, user_dir=dst_udir)
    assert (res.bindings, res.outputs) == (1, 0)
    assert res.layout and res.calibration
    assert res.device_name == "Test Yoke"

    # Device registered into the overlay (not the versioned catalog).
    overlay = yaml.safe_load((dst_udir / "devices.local.yaml").read_text())
    assert any(d["id"] == "yoke" for d in overlay["devices"])

    # Mapping landed in the target profile.
    target = yaml.safe_load((dst_root / "profiles" / "target.yaml").read_text())
    assert target["bindings"]["yoke"][0]["name"] == "Aileron"

    # Layout + calibration restored under the device id.
    layout = yaml.safe_load((dst_udir / "panel-layouts.yaml").read_text())
    assert layout["devices"]["yoke"]["axis:0"] == [0.1, 0.2, 0.3, 0.4]
    calib = yaml.safe_load((dst_root / "config" / "calibration.yaml").read_text())
    assert calib["devices"]["yoke"]["axes"][0]["raw_max"] == 4095


def test_import_unhides_a_deregistered_device(tmp_path):
    src_root, src_udir = _make_root(tmp_path / "a"), _make_user_dir(tmp_path / "a")
    pkg = dp.export_device_package(
        "yoke", "src", tmp_path / "pkg", root=src_root, user_dir=src_udir
    ).path

    dst_root = _make_root(tmp_path / "b")
    dst_udir = tmp_path / "b" / "user"
    dst_udir.mkdir(parents=True)
    (dst_root / "profiles" / "target.yaml").write_text(
        "name: Target\naircraft_match: [ X ]\nbindings: {}\n"
    )
    # Importer had hidden 'yoke' first.
    from msfs_peripherals_bridge.mapping.loader import (
        hide_device,
        load_device_catalog,
        load_hidden_devices,
    )

    overlay = dst_udir / "devices.local.yaml"
    hide_device("yoke", overlay=overlay)
    assert "yoke" in load_hidden_devices(overlay=overlay)

    dp.import_device_package(pkg, "target", root=dst_root, user_dir=dst_udir)
    assert load_hidden_devices(overlay=overlay) == set()
    cat = load_device_catalog(dst_root / "config" / "devices.yaml", overlay=overlay)
    assert cat.by_id("yoke") is not None


def test_import_without_target_profile_skips_mapping(tmp_path):
    src_root, src_udir = _make_root(tmp_path / "a"), _make_user_dir(tmp_path / "a")
    pkg = dp.export_device_package(
        "yoke", "src", tmp_path / "pkg", root=src_root, user_dir=src_udir
    ).path
    dst_root = _make_root(tmp_path / "b")
    dst_udir = tmp_path / "b" / "user"
    dst_udir.mkdir(parents=True)

    res = dp.import_device_package(pkg, None, root=dst_root, user_dir=dst_udir)
    assert (res.bindings, res.outputs) == (0, 0)
    assert res.layout and res.calibration  # non-mapping parts still restored


def test_export_unknown_device_or_profile_raises(tmp_path):
    root, udir = _make_root(tmp_path), _make_user_dir(tmp_path)
    with pytest.raises(ValueError):
        dp.export_device_package("nope", "src", tmp_path / "p", root=root, user_dir=udir)
    with pytest.raises(ValueError):
        dp.export_device_package("yoke", "nope", tmp_path / "p", root=root, user_dir=udir)


def test_read_manifest_rejects_non_package(tmp_path):
    bad = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad, "w") as z:
        z.writestr("hello.txt", "not a package")
    with pytest.raises(ValueError):
        dp.read_manifest(bad)
