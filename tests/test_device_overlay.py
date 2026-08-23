import yaml

from msfs_peripherals_bridge.mapping.loader import (
    add_device_overlay,
    hide_device,
    load_device_catalog,
    load_hidden_devices,
    merge_device_catalog,
    set_device_inputs,
    set_device_outputs,
    unhide_device,
)
from msfs_peripherals_bridge.models import (
    DeviceCatalog,
    DeviceDef,
    InputBlock,
    OutputBlock,
)


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


def _base(tmp_path):
    base = tmp_path / "devices.yaml"
    base.write_text(
        yaml.safe_dump(
            {"devices": [A.model_dump(exclude_none=True), B.model_dump(exclude_none=True)]}
        )
    )
    return base


def test_hide_device_filters_bundled_entry(tmp_path):
    base = _base(tmp_path)
    overlay = tmp_path / "devices.local.yaml"
    hide_device("a", overlay=overlay)
    catalog = load_device_catalog(base, overlay=overlay)
    assert {d.id for d in catalog.devices} == {"b"}  # 'a' hidden, versioned base intact
    assert yaml.safe_load(base.read_text())["devices"][0]["id"] == "a"


def test_hide_device_drops_overlay_copy(tmp_path):
    base = _base(tmp_path)
    overlay = tmp_path / "devices.local.yaml"
    add_device_overlay(C, overlay=overlay)
    hide_device("c", overlay=overlay)
    data = yaml.safe_load(overlay.read_text())
    assert all(d["id"] != "c" for d in data.get("devices") or [])
    assert "c" in data["hidden"]
    assert {d.id for d in load_device_catalog(base, overlay=overlay).devices} == {"a", "b"}


def test_unhide_restores_bundled_device(tmp_path):
    base = _base(tmp_path)
    overlay = tmp_path / "devices.local.yaml"
    hide_device("a", overlay=overlay)
    unhide_device("a", overlay=overlay)
    assert {d.id for d in load_device_catalog(base, overlay=overlay).devices} == {"a", "b"}
    assert load_hidden_devices(overlay=overlay) == set()


def test_add_device_overlay_preserves_hidden(tmp_path):
    overlay = tmp_path / "devices.local.yaml"
    hide_device("a", overlay=overlay)
    add_device_overlay(C, overlay=overlay)  # register an unrelated device
    assert "a" in load_hidden_devices(overlay=overlay)
    data = yaml.safe_load(overlay.read_text())
    assert any(d["id"] == "c" for d in data["devices"])


def test_re_registering_a_hidden_device_unhides_it(tmp_path):
    base = _base(tmp_path)
    overlay = tmp_path / "devices.local.yaml"
    hide_device("a", overlay=overlay)
    add_device_overlay(A, overlay=overlay)  # user plugs it back in and re-registers
    assert load_hidden_devices(overlay=overlay) == set()
    assert {d.id for d in load_device_catalog(base, overlay=overlay).devices} == {"a", "b"}


def test_load_hidden_devices_missing_file(tmp_path):
    assert load_hidden_devices(overlay=tmp_path / "nope.yaml") == set()


def test_devicedef_without_inputs_defaults_empty():
    d = DeviceDef.model_validate({"id": "x", "name": "X", "vendor": "1", "product": "2"})
    assert d.inputs == []


def test_set_device_inputs_persists_captured_controls(tmp_path):
    overlay = tmp_path / "devices.local.yaml"
    blocks = [
        InputBlock(kind="button", name="AP", code=12),
        InputBlock(kind="encoder", name="Heading", cw=40, ccw=41),
        InputBlock(kind="axis", name="Throttle", code=0, raw_min=0, raw_max=4095),
    ]
    set_device_inputs(C, blocks, overlay=overlay)
    reloaded = DeviceCatalog.model_validate(yaml.safe_load(overlay.read_text()))
    dev = reloaded.by_id("c")
    assert [b.name for b in dev.inputs] == ["AP", "Heading", "Throttle"]
    assert dev.inputs[1].cw == 40 and dev.inputs[1].ccw == 41
    assert dev.inputs[2].raw_max == 4095


def test_set_device_inputs_overwrites_previous(tmp_path):
    overlay = tmp_path / "devices.local.yaml"
    set_device_inputs(C, [InputBlock(name="Old", code=1)], overlay=overlay)
    set_device_inputs(C, [InputBlock(name="New", code=2)], overlay=overlay)
    reloaded = DeviceCatalog.model_validate(yaml.safe_load(overlay.read_text()))
    assert [b.name for b in reloaded.by_id("c").inputs] == ["New"]


def test_set_device_outputs_persists_and_keeps_inputs(tmp_path):
    overlay = tmp_path / "devices.local.yaml"
    ddef = C.model_copy(update={"inputs": [InputBlock(name="AP", code=12)]})
    set_device_outputs(
        ddef,
        [
            OutputBlock(kind="led", name="AP-Lampe"),
            OutputBlock(kind="display", name="COM", cells=5, display_kind="7segment"),
        ],
        overlay=overlay,
    )
    reloaded = DeviceCatalog.model_validate(yaml.safe_load(overlay.read_text()))
    dev = reloaded.by_id("c")
    assert [b.name for b in dev.inputs] == ["AP"]  # READ elements kept
    assert [b.kind for b in dev.outputs] == ["led", "display"]
    assert dev.outputs[1].cells == 5


def test_devicedef_without_outputs_defaults_empty():
    d = DeviceDef.model_validate({"id": "x", "name": "X", "vendor": "1", "product": "2"})
    assert d.outputs == []


def test_output_templates_round_trip(tmp_path):
    from msfs_peripherals_bridge.mapping.loader import (
        delete_output_template,
        load_output_templates,
        save_output_template,
    )

    path = tmp_path / "output-templates.yaml"
    assert load_output_templates(path) == {}  # missing file -> empty

    block = {"type": "gear_leds"}
    save_output_template("Mein Fahrwerk", block, path=path)
    save_output_template("Multi", {"type": "multi_panel", "selector": []}, path=path)
    loaded = load_output_templates(path)
    assert loaded["Mein Fahrwerk"] == block
    assert loaded["Multi"]["type"] == "multi_panel"

    delete_output_template("Multi", path=path)
    assert set(load_output_templates(path)) == {"Mein Fahrwerk"}
