"""Pure logic for the GUI Mapper tab (Stufe A device viewer)."""

from msfs_peripherals_bridge.gui_mapper import (
    build_device_rows,
    describe_action,
    describe_binding,
    describe_output,
    describe_source,
    describe_transform,
    device_bindings,
    device_outputs,
)
from msfs_peripherals_bridge.models import (
    DeviceCatalog,
    EventAction,
    EventFromVarAction,
    GearLedOutput,
    Profile,
    RpnAction,
    SequenceAction,
    SimVarAction,
    Source,
    SourceKind,
    Transform,
    WriteStep,
)

CATALOG = DeviceCatalog.model_validate(
    {
        "devices": [
            {"id": "yoke", "name": "Fulcrum Yoke", "vendor": "0000", "product": "0000",
             "name_match": "Fulcrum"},
            {"id": "multi_panel", "name": "Multi Panel", "vendor": "06a3", "product": "0d06",
             "transport": "hidraw"},
            {"id": "pedals", "name": "Rudder Pedals", "vendor": "06a3", "product": "0763"},
        ]
    }
)

PROFILE = Profile.model_validate(
    {
        "name": "Test Arrow",
        "bindings": {
            "yoke": [
                {
                    "name": "Aileron",
                    "source": {"kind": "axis", "code": 0, "raw_min": 0, "raw_max": 4095},
                    "action": {"type": "event", "event": "AILERON_SET"},
                    "transform": {"invert": True, "out_min": -16383, "out_max": 16383},
                },
                {
                    "name": "Gear",
                    "source": {"kind": "button", "code": 288},
                    "action": {"type": "event", "event": "GEAR_TOGGLE", "value": 1},
                },
            ],
            "pedals": [
                {
                    "name": "Rudder",
                    "source": {"kind": "axis", "code": 5, "raw_min": 0, "raw_max": 1023},
                    "action": {"type": "event", "event": "RUDDER_SET"},
                },
            ],
        },
        "outputs": {"multi_panel": [{"type": "gear_leds"}]},
    }
)


# --------------------------------------------------------------------------- #
# build_device_rows
# --------------------------------------------------------------------------- #
def test_rows_keep_catalog_order_and_count_usage():
    rows = build_device_rows(CATALOG, PROFILE, present=set())
    assert [r.id for r in rows] == ["yoke", "multi_panel", "pedals"]
    by_id = {r.id: r for r in rows}
    assert (by_id["yoke"].bindings, by_id["yoke"].outputs) == (2, 0)
    assert (by_id["multi_panel"].bindings, by_id["multi_panel"].outputs) == (0, 1)
    assert (by_id["pedals"].bindings, by_id["pedals"].outputs) == (1, 0)
    assert by_id["multi_panel"].transport == "hidraw"
    assert by_id["pedals"].usb == "06a3:0763"


def test_present_tristate():
    # discovery unavailable -> unknown everywhere
    unknown = {r.id: r for r in build_device_rows(CATALOG, PROFILE, present=None)}
    assert unknown["yoke"].present is None
    assert unknown["yoke"].status == "?"

    # a concrete discovery set -> connected / not-detected
    some = {r.id: r for r in build_device_rows(CATALOG, PROFILE, present={"yoke"})}
    assert some["yoke"].present is True
    assert some["yoke"].status == "verbunden"
    assert some["pedals"].present is False
    assert some["pedals"].status == "nicht erkannt"


# --------------------------------------------------------------------------- #
# describe_* formatters
# --------------------------------------------------------------------------- #
def test_describe_source_labels():
    assert describe_source(Source(kind=SourceKind.AXIS, code=0)) == "Achse 0"
    assert describe_source(Source(kind=SourceKind.BUTTON, code=288)) == "Taste 288"
    assert describe_source(Source(kind=SourceKind.SWITCH, code=14)) == "Schalter 14"


def test_describe_action_per_type():
    assert describe_action(EventAction(event="AILERON_SET")) == "event AILERON_SET"
    assert describe_action(EventAction(event="GEAR_TOGGLE", value=1)) == "event GEAR_TOGGLE = 1"
    assert describe_action(SimVarAction(simvar="L:X", invert=True)) == "set L:X (invert)"
    assert describe_action(SimVarAction(simvar="L:X")) == "set L:X"
    efv = EventFromVarAction(read="PLANE HEADING DEGREES MAGNETIC", event="HEADING_BUG_SET")
    assert describe_action(efv) == "HEADING_BUG_SET ← PLANE HEADING DEGREES MAGNETIC"
    assert describe_action(RpnAction(code="(L:X) ! (>L:X)")) == "rpn (L:X) ! (>L:X)"


def test_describe_sequence_summarises_targets():
    seq = SequenceAction(
        on_edge=[
            WriteStep(event="E1", value=1),
            WriteStep(simvar="L:V", value=2),
            WriteStep(event="E3", value=0),
        ],
        off_edge=[WriteStep(event="OFF", value=0)],
    )
    out = describe_action(seq)
    assert out == "sequence [4]: E1, L:V …"  # 3 on + 1 off = 4; first two shown, then ellipsis


def test_describe_transform_defaults_and_shaping():
    assert describe_transform(Transform()) == ""  # all defaults -> nothing
    inv = Transform(invert=True, out_min=-1.0, out_max=1.0)
    assert describe_transform(inv) == "invert, out[-1,1]"
    assert describe_transform(Transform(deadzone=0.1)) == "dz=0.1"
    # the expo curve folds its strength in — no duplicate "expo, expo=0.25".
    yoke = Transform(deadzone=0.03, curve="expo", expo=0.25, invert=True,
                     out_min=-16383.0, out_max=16383.0)
    assert describe_transform(yoke) == "dz=0.03, expo=0.25, invert, out[-16383,16383]"


def test_describe_binding_flattens_all_columns():
    row = describe_binding(PROFILE.bindings["yoke"][0])
    assert row.name == "Aileron"
    assert row.source == "Achse 0"
    assert row.action == "event AILERON_SET"
    assert "invert" in row.transform and "out[-16383,16383]" in row.transform


# --------------------------------------------------------------------------- #
# describe_output / device_* accessors
# --------------------------------------------------------------------------- #
def test_describe_output_reports_type_and_simvar_count():
    # GearLedOutput.simvars() = 3 wheel positions + 1 power gate = 4.
    assert describe_output(GearLedOutput()) == "gear_leds — 4 SimVars"


def test_device_bindings_and_outputs_accessors():
    binds = device_bindings(PROFILE, "yoke")
    assert [b.name for b in binds] == ["Aileron", "Gear"]
    assert device_outputs(PROFILE, "multi_panel") == ["gear_leds — 4 SimVars"]
    assert device_bindings(PROFILE, "unknown") == []  # device not in profile
    assert device_outputs(PROFILE, "yoke") == []  # no outputs on the yoke
