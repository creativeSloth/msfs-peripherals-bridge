"""Pure logic for the GUI Mapper tab (Stufe A device viewer)."""

import pytest

from msfs_peripherals_bridge.gui_mapper import (
    binding_to_form,
    blank_binding_form,
    build_device_rows,
    describe_action,
    describe_binding,
    describe_output,
    describe_output_detail,
    describe_source,
    describe_transform,
    device_bindings,
    device_outputs,
    form_to_binding,
    rows_to_seq_action,
    seq_action_to_rows,
)
from msfs_peripherals_bridge.models import (
    Binding,
    DeviceCatalog,
    EventAction,
    EventFromVarAction,
    GearLedOutput,
    MultiPanelOutput,
    Profile,
    RadioPanelOutput,
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
    # outputs = ATOMIC elements: the gear_leds block = 3 wheels x 2 colours = 6
    # (not "1 block", per user: count atoms, not Oberelemente).
    assert (by_id["multi_panel"].bindings, by_id["multi_panel"].outputs) == (0, 6)
    assert (by_id["pedals"].bindings, by_id["pedals"].outputs) == (1, 0)
    # inputs = bindings + panel-controller input codes; a pure-axis device (yoke)
    # equals its bindings. (This fixture's multi_panel output is a gear_leds stub,
    # which contributes no inputs — real panels are covered separately below.)
    assert by_id["yoke"].inputs == 2
    assert by_id["multi_panel"].inputs == 0
    assert by_id["multi_panel"].transport == "hidraw"
    assert by_id["pedals"].usb == "06a3:0763"


def test_output_input_codes_counts_encoders_swap_selector():
    from msfs_peripherals_bridge.gui_mapper import output_input_codes
    from msfs_peripherals_bridge.models import (
        GearLedOutput,
        MultiPanelOutput,
        RadioBank,
        RadioPanelOutput,
        RadioUnit,
        SelectorEntry,
    )

    assert output_input_codes(GearLedOutput()) == set()  # pure output
    m = MultiPanelOutput(selector=[
        SelectorEntry(code=0, label="ALT", simvar="X", min=0, max=9),
        SelectorEntry(code=3, label="HDG", simvar="Y", min=0, max=359),
    ])
    assert output_input_codes(m) == {0, 3, 5, 6}  # selector {0,3} + encoder CW/CCW
    bank = RadioBank(code=2, label="COM1", active="A", standby="S", swap_event="SW",
                     whole_inc="wi", whole_dec="wd", fract_inc="fi", fract_dec="fd")
    r = RadioPanelOutput(units=[RadioUnit(
        name="upper", row="upper", banks=[bank],
        outer_cw=10, outer_ccw=11, inner_cw=12, inner_ccw=13, swap=14)])
    assert output_input_codes(r) == {10, 11, 12, 13, 14, 2}  # encoder/swap + bank code


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


# --------------------------------------------------------------------------- #
# describe_output_detail — panel outputs/inputs expanded into readable rows
# --------------------------------------------------------------------------- #
def test_output_detail_gear_leds():
    lines = describe_output_detail(GearLedOutput())
    assert any("Rad-LEDs" in ln and "GEAR CENTER POSITION" in ln for ln in lines)
    assert any("Power-Gate: ELECTRICAL MASTER BATTERY" in ln for ln in lines)


def test_output_detail_multi_panel_selector_leds_dimmer():
    multi = MultiPanelOutput.model_validate({
        "selector": [
            {"code": 3, "label": "HDG", "simvar": "AUTOPILOT HEADING LOCK DIR",
             "set_event": "HEADING_BUG_SET", "min": 0, "max": 359, "rollover": True,
             "alt_sources": [{"simvar": "NAV OBS:2", "set_event": "VOR2_SET"}]},
        ],
        "bool_leds": {"alt": "L:JF_PA28_AP_alt"},
        "dimmer": {"cw": 12, "ccw": 13,
                   "targets": [{"var": "L:CENTRE_LOWER_PANEL_LIGHT", "full": 10}]},
    })
    lines = describe_output_detail(multi)
    assert any("Selektor 3 HDG" in ln and "HEADING_BUG_SET" in ln and "rollover" in ln
               for ln in lines)
    assert any("Alt-Quelle NAV OBS:2" in ln and "VOR2_SET" in ln for ln in lines)
    assert "LED alt ← L:JF_PA28_AP_alt" in lines
    assert any("Dimmer" in ln and "L:CENTRE_LOWER_PANEL_LIGHT" in ln for ln in lines)


def test_output_detail_radio_panel_all_bank_kinds():
    radio = RadioPanelOutput.model_validate({
        "units": [{
            "name": "upper", "row": "upper",
            "outer_cw": 1, "outer_ccw": 2, "inner_cw": 3, "inner_ccw": 4, "swap": 5,
            "banks": [
                {"code": 0, "label": "COM1", "active": "COM ACTIVE FREQUENCY:1",
                 "standby": "COM STANDBY FREQUENCY:1", "swap_event": "COM1_RADIO_SWAP",
                 "whole_inc": "A", "whole_dec": "B", "fract_inc": "C", "fract_dec": "D",
                 "fine_view": True},
                {"kind": "dme", "code": 5,
                 "sources": [{"label": "1", "distance": "NAV DME:1", "speed": "NAV DMESPEED:1"}]},
                {"kind": "adf", "code": 6},
                {"kind": "xpdr", "code": 7, "baro_var": "KOHLSMAN SETTING HG:1"},
            ],
        }],
    })
    lines = describe_output_detail(radio)
    assert any("Einheit upper (upper)" in ln and "outer 1/2" in ln and "swap 5" in ln
               for ln in lines)
    assert any("COM1 (freq)" in ln and "act=COM ACTIVE FREQUENCY:1" in ln and "fine-view" in ln
               for ln in lines)
    assert any("(DME, nur Anzeige)" in ln for ln in lines)
    assert any("(ADF)" in ln and "L:KR85_dig1_counter" in ln for ln in lines)
    assert any("(XPDR)" in ln and "QNH KOHLSMAN SETTING HG:1" in ln for ln in lines)


# --------------------------------------------------------------------------- #
# editor form <-> binding
# --------------------------------------------------------------------------- #
def _binding(d: dict) -> Binding:
    return Binding.model_validate(d)


def test_binding_to_form_axis_event():
    b = _binding({
        "name": "Aileron",
        "source": {"kind": "axis", "code": 0, "raw_min": 0, "raw_max": 4095},
        "action": {"type": "event", "event": "AILERON_SET"},
        "transform": {"curve": "expo", "expo": 0.25, "invert": True,
                      "out_min": -16383, "out_max": 16383},
    })
    f = binding_to_form(b)
    assert f["name"] == "Aileron"
    assert (f["kind"], f["code"], f["is_axis"]) == ("axis", "0", True)
    assert (f["raw_min"], f["raw_max"]) == ("0", "4095")
    assert (f["action_type"], f["ev_event"]) == ("event", "AILERON_SET")
    assert (f["tf_curve"], f["tf_expo"], f["tf_invert"]) == ("expo", "0.25", True)
    assert (f["tf_out_min"], f["tf_out_max"]) == ("-16383", "16383")


@pytest.mark.parametrize("binding_dict", [
    {"name": "A", "source": {"kind": "axis", "code": 0, "raw_min": 0, "raw_max": 4095},
     "action": {"type": "event", "event": "AILERON_SET"},
     "transform": {"deadzone": 0.03, "curve": "expo", "expo": 0.25, "invert": True,
                   "out_min": -16383, "out_max": 16383}},
    {"name": "Gear", "source": {"kind": "button", "code": 288},
     "action": {"type": "event", "event": "GEAR_TOGGLE", "value": 1}},
    {"name": "Pump", "source": {"kind": "switch", "code": 3},
     "action": {"type": "simvar", "simvar": "L:FuelPump", "invert": True}},
    {"name": "HdgSync", "source": {"kind": "button", "code": 290},
     "action": {"type": "event_from_var", "read": "PLANE HEADING DEGREES MAGNETIC",
                "event": "HEADING_BUG_SET", "unit": "degrees"}},
    {"name": "AltHold", "source": {"kind": "switch", "code": 11},
     "action": {"type": "rpn", "code": "(L:X) ! (>L:X)"}},
])
def test_form_round_trip_preserves_binding(binding_dict):
    # binding -> form -> binding must reparse to an equal model (no data loss).
    original = _binding(binding_dict)
    rebuilt = _binding(form_to_binding(binding_to_form(original)))
    assert rebuilt == original


def test_form_to_binding_preserves_sequence_via_original():
    original_action = {"type": "sequence", "on_edge": [{"simvar": "L:HDG", "value": 1}]}
    form = blank_binding_form("switch")
    form["action_type"] = "sequence"
    out = form_to_binding(form, original_action)
    assert out["action"] is original_action  # unchanged, carried through


def test_form_to_binding_rejects_bad_input():
    good = blank_binding_form("button")
    good["ev_event"] = "GEAR_TOGGLE"
    assert form_to_binding(good)["action"]["event"] == "GEAR_TOGGLE"

    with pytest.raises(ValueError, match="Name"):
        form_to_binding({**good, "name": "   "})
    with pytest.raises(ValueError, match="ganze Zahl"):
        form_to_binding({**good, "code": "xyz"})
    with pytest.raises(ValueError, match="Event"):
        form_to_binding({**good, "ev_event": ""})
    with pytest.raises(ValueError, match="Sequence"):
        form_to_binding({**good, "action_type": "sequence"})  # no original -> reject


def test_blank_form_builds_a_valid_button_binding():
    form = blank_binding_form("button")
    form["ev_event"] = "PARKING_BRAKES"
    b = _binding(form_to_binding(form))
    assert b.source.kind is SourceKind.BUTTON
    assert b.action.event == "PARKING_BRAKES"
    assert b.action.value == 1  # button event auto-gets value 1


# --------------------------------------------------------------------------- #
# sequence action <-> editor rows
# --------------------------------------------------------------------------- #
def test_seq_action_to_rows_splits_event_and_simvar_steps():
    action = SequenceAction.model_validate({
        "type": "sequence",
        "on_edge": [{"event": "AVIONICS_MASTER_1", "value": 1},
                    {"simvar": "L:AUTOPILOT_MODE", "value": 2}],
        "off_edge": [{"simvar": "L:AUTOPILOT_MODE", "value": 0}],
    })
    rows = seq_action_to_rows(action)
    assert rows["on"][0] == {"target": "event", "name": "AVIONICS_MASTER_1",
                             "value": "1", "unit": "number"}
    assert rows["on"][1]["target"] == "simvar" and rows["on"][1]["name"] == "L:AUTOPILOT_MODE"
    assert rows["off"][0] == {"target": "simvar", "name": "L:AUTOPILOT_MODE",
                              "value": "0", "unit": "number"}


def test_rows_to_seq_action_round_trips_through_the_model():
    on = [{"target": "event", "name": "AVIONICS_MASTER_1", "value": "1", "unit": "number"},
          {"target": "simvar", "name": "L:AUTOPILOT_MODE", "value": "2", "unit": "number"}]
    off = [{"target": "simvar", "name": "L:AUTOPILOT_MODE", "value": "0", "unit": "number"}]
    act = rows_to_seq_action(on, off)
    model = SequenceAction.model_validate(act)  # must validate
    assert [s.event for s in model.on_edge] == ["AVIONICS_MASTER_1", None]
    assert model.on_edge[1].simvar == "L:AUTOPILOT_MODE" and model.on_edge[1].value == 2
    assert model.off_edge[0].value == 0


def test_rows_to_seq_action_validates_inputs():
    with pytest.raises(ValueError, match="mindestens einen on-Schritt"):
        rows_to_seq_action([], [])
    with pytest.raises(ValueError, match="Name fehlt"):
        rows_to_seq_action([{"target": "event", "name": "  ", "value": "1"}], [])
    with pytest.raises(ValueError, match="Zahl"):
        rows_to_seq_action([{"target": "event", "name": "X", "value": "abc"}], [])


def test_form_round_trip_preserves_split():
    b = _binding({
        "name": "Throttle mit Reverse",
        "source": {"kind": "axis", "code": 0, "raw_min": 0, "raw_max": 1000},
        "action": {"type": "event", "event": "THROTTLE1_SET"},
        "transform": {"out_min": 0, "out_max": 16383},
        "split": {"at": 200,
                  "action": {"type": "simvar",
                             "simvar": "TURB ENG REVERSE NOZZLE PERCENT:1"},
                  "transform": {"invert": True}},
    })
    form = binding_to_form(b)
    assert form["sp_enabled"] is True
    assert form["sp_at"] == "200"
    assert form["sp_action_type"] == "simvar"
    assert form["sp_sv_simvar"] == "TURB ENG REVERSE NOZZLE PERCENT:1"
    assert form["sp_tf_invert"] is True
    rebuilt = _binding(form_to_binding(form))
    assert rebuilt == b


def test_form_split_disabled_emits_no_split():
    form = blank_binding_form("axis")
    form["ev_event"] = "THROTTLE1_SET"
    out = form_to_binding(form)
    assert "split" not in out
    # enabling it without a detent value must fail with a German message
    form["sp_enabled"] = True
    form["sp_ev_event"] = "X"
    with pytest.raises(ValueError, match="Detent"):
        form_to_binding(form)


def test_describe_binding_mentions_the_split():
    b = _binding({
        "name": "Prop", "source": {"kind": "axis", "code": 3, "raw_min": 0, "raw_max": 100},
        "action": {"type": "event", "event": "PROP_PITCH1_SET"},
        "split": {"at": 20, "action": {"type": "event", "event": "PROP_FEATHER"}},
    })
    row = describe_binding(b)
    assert "unter 20" in row.action and "PROP_FEATHER" in row.action


def test_live_bar_fills_proportionally():
    from msfs_peripherals_bridge.gui_mapper import live_bar

    assert live_bar(0, 0, 100) == "░░░░░░░░ 0"
    assert live_bar(100, 0, 100) == "████████ 100"
    assert live_bar(50, 0, 100) == "████░░░░ 50"
    assert live_bar(999, 0, 100).startswith("████████")  # clamped
    assert live_bar(5, 5, 5) == "░░░░░░░░ 5"  # degenerate range: no crash


def test_live_row_map_covers_axes_hats_buttons_and_switches():
    from msfs_peripherals_bridge.gui_mapper import live_row_map

    prof = PROFILE  # piper_arrow fixture from this module
    rows = live_row_map(prof, "yoke")
    assert rows, "yoke has axis/button bindings"
    kinds = {k for k, _ in rows}
    assert kinds <= {"axis", "button"}
    # every mapped iid points at a binding row
    for iids in rows.values():
        assert all(i.startswith("bind:") for i in iids)

    # hidraw panel switches now map to ("switch", code) keys — the same global
    # bit index the profile stores, so the Live column can light them up.
    panel = Profile.model_validate({
        "name": "SW",
        "bindings": {"switch_panel": [
            {"name": "Battery", "source": {"kind": "switch", "code": 0},
             "action": {"type": "event", "event": "MASTER_BATTERY_SET"}},
            {"name": "Cowl", "source": {"kind": "switch", "code": 6},
             "action": {"type": "event", "event": "COWL_FLAPS_SET"}},
        ]},
    })
    sw = live_row_map(panel, "switch_panel")
    assert {k for k, _ in sw} == {"switch"}
    assert ("switch", 0) in sw and ("switch", 6) in sw


def test_form_round_trip_preserves_hat():
    b = _binding({
        "name": "Trim-Hat",
        "source": {"kind": "hat", "code": 16},
        "hat": {"up": {"type": "event", "event": "ELEV_TRIM_UP"},
                "down": {"type": "event", "event": "ELEV_TRIM_DN", "value": 2},
                "left": {"type": "simvar", "simvar": "L:PAN_LEFT"}},
    })
    form = binding_to_form(b)
    assert form["hat_up_name"] == "ELEV_TRIM_UP"
    assert form["hat_down_value"] == "2"
    assert form["hat_left_type"] == "simvar"
    assert form["hat_right_name"] == ""
    rebuilt = _binding(form_to_binding(form))
    assert rebuilt == b


def test_form_hat_requires_a_direction():
    form = blank_binding_form("hat")
    with pytest.raises(ValueError, match="Richtung"):
        form_to_binding(form)
    form["hat_up_name"] = "ELEV_TRIM_UP"
    out = form_to_binding(form)
    assert "action" not in out and out["hat"]["up"]["event"] == "ELEV_TRIM_UP"


def test_condition_rows_round_trip():
    from msfs_peripherals_bridge.gui_mapper import conditions_to_rows, rows_to_conditions
    from msfs_peripherals_bridge.models import Condition

    when = [Condition(var="AVIONICS MASTER SWITCH"),
            Condition(var="L:AUTOPILOT_MODE", op="<", value=3)]
    rows = conditions_to_rows(when)
    assert rows[0] == {"var": "AVIONICS MASTER SWITCH", "op": "==", "value": "1"}
    out = rows_to_conditions(rows)
    assert out == [{"var": "AVIONICS MASTER SWITCH"},
                   {"var": "L:AUTOPILOT_MODE", "op": "<", "value": 3}]
    assert [Condition.model_validate(c) for c in out] == when

    with pytest.raises(ValueError, match="Variable fehlt"):
        rows_to_conditions([{"var": " ", "op": "==", "value": "1"}])
    with pytest.raises(ValueError, match="Zahl"):
        rows_to_conditions([{"var": "X", "op": "==", "value": "abc"}])


def test_device_input_sources_maps_blocks_to_kind_code():
    from msfs_peripherals_bridge.gui_mapper import device_input_sources
    from msfs_peripherals_bridge.models import DeviceDef, InputBlock

    ddef = DeviceDef(
        id="p", name="P", vendor="06a3", product="0d67", transport="hidraw",
        inputs=[
            InputBlock(kind="button", name="AP", code=12),
            InputBlock(kind="switch", name="BAT", code=0),
            InputBlock(kind="encoder", name="HDG", cw=40, ccw=41),
            InputBlock(kind="button", name="Kaputt"),  # no code -> skipped
        ],
    )
    assert device_input_sources(ddef) == [
        ("AP", "button", 12),
        ("BAT", "switch", 0),
        ("HDG · CW", "button", 40),
        ("HDG · CCW", "button", 41),
    ]


def test_device_input_sources_empty_without_inputs():
    from msfs_peripherals_bridge.gui_mapper import device_input_sources
    from msfs_peripherals_bridge.models import DeviceDef

    ddef = DeviceDef(id="x", name="X", vendor="1", product="2")
    assert device_input_sources(ddef) == []


def test_atomic_output_count_counts_leds_and_cells():
    from msfs_peripherals_bridge.gui_mapper import atomic_output_count

    assert atomic_output_count([]) == 0
    assert atomic_output_count([GearLedOutput()]) == 6  # 3 wheels x 2 colours
    assert atomic_output_count([GearLedOutput(), GearLedOutput()]) == 12


def test_atomic_input_count_counts_atoms_incl_scanned_inputs():
    from msfs_peripherals_bridge.gui_mapper import atomic_input_count
    from msfs_peripherals_bridge.models import DeviceDef, InputBlock

    # freshly-scanned custom device: inputs come from ddef.inputs, no profile
    ddef = DeviceDef(id="custom", name="Custom", vendor="1", product="2",
                     inputs=[InputBlock(kind="button", name="A", code=1),
                             InputBlock(kind="encoder", name="E", cw=2, ccw=3)])
    empty = Profile.model_validate({"name": "p"})
    assert atomic_input_count(ddef, empty) == 2  # encoder counts once, not twice

    # catalog device with bindings: counts those
    yoke = DeviceDef(id="yoke", name="Y", vendor="0000", product="0000", name_match="Fulcrum")
    assert atomic_input_count(yoke, PROFILE) == 2
