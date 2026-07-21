import yaml

from msfs_peripherals_bridge.mapping.loader import (
    add_device_overlay,
    load_device_catalog,
    merge_device_catalog,
)
from msfs_peripherals_bridge.models import DeviceCatalog, DeviceDef


def _cat(*defs: DeviceDef) -> DeviceCatalog:
    return DeviceCatalog(devices=list(defs))


A = DeviceDef(id="a", name="Base A", vendor="0001", product="0001")
B = DeviceDef(id="b", name="Base B", vendor="0002", product="0002")
C = DeviceDef(id="c", name="Overlay C", vendor="0003", product="0003", transport="hidraw")
A2 = DeviceDef(id="a", name="Overridden A", vendor="0001", product="00ff")


def test_merge_appends_new_ids_preserving_order():
    merged = merge_device_catalog(_cat(A, B), _cat(C))
    assert [d.id for d in merged.devices] == ["a", "b", "c"]


def test_merge_overrides_matching_id_in_place():
    merged = merge_device_catalog(_cat(A, B), _cat(A2))
    assert [d.id for d in merged.devices] == ["a", "b"]  # order kept
    assert merged.by_id("a").name == "Overridden A"
    assert merged.by_id("a").product == "00ff"


def test_add_device_overlay_creates_and_reloads(tmp_path):
    overlay = tmp_path / "sub" / "devices.local.yaml"
    add_device_overlay(C, overlay=overlay)
    assert overlay.exists()
    data = yaml.safe_load(overlay.read_text())
    reloaded = DeviceCatalog.model_validate(data)
    assert reloaded.by_id("c").transport == "hidraw"


def test_add_device_overlay_appends_second_device(tmp_path):
    overlay = tmp_path / "devices.local.yaml"
    add_device_overlay(C, overlay=overlay)
    add_device_overlay(B, overlay=overlay)
    reloaded = DeviceCatalog.model_validate(yaml.safe_load(overlay.read_text()))
    assert {d.id for d in reloaded.devices} == {"c", "b"}


def test_load_device_catalog_merges_overlay(tmp_path):
    base = tmp_path / "devices.yaml"
    base.write_text(yaml.safe_dump({"devices": [A.model_dump(exclude_none=True)]}))
    overlay = tmp_path / "devices.local.yaml"
    add_device_overlay(C, overlay=overlay)
    catalog = load_device_catalog(base, overlay=overlay)
    assert {d.id for d in catalog.devices} == {"a", "c"}


def test_load_device_catalog_can_skip_overlay(tmp_path):
    base = tmp_path / "devices.yaml"
    base.write_text(yaml.safe_dump({"devices": [A.model_dump(exclude_none=True)]}))
    catalog = load_device_catalog(base, merge_overlay=False)
    assert {d.id for d in catalog.devices} == {"a"}
