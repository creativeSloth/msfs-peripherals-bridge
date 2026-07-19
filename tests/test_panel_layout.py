"""Pure panel-reconstruction layout (positions + mapping, no display needed)."""

from msfs_peripherals_bridge.models import Profile
from msfs_peripherals_bridge.panel_layout import (
    AXIS,
    BUTTON,
    HAT,
    LED,
    SEGMENT,
    SWITCH,
    has_hand_layout,
    panel_layout,
)

# A switch panel with a few toggles + one magneto detent + a gear_leds output,
# deliberately leaving some hardware codes unmapped (COWL=6, NAV=9).
PROFILE = Profile.model_validate(
    {
        "name": "Test",
        "bindings": {
            "switch_panel": [
                {"name": "Battery master", "source": {"kind": "switch", "code": 0},
                 "action": {"type": "event", "event": "MASTER_BATTERY_SET"}},
                {"name": "Strobe lights", "source": {"kind": "switch", "code": 10},
                 "action": {"type": "event", "event": "STROBES_SET"}},
                {"name": "Magneto BOTH", "source": {"kind": "switch", "code": 16},
                 "action": {"type": "event", "event": "MAGNETO1_BOTH", "value": 1}},
                {"name": "Gear up", "source": {"kind": "switch", "code": 18},
                 "action": {"type": "event", "event": "GEAR_UP", "value": 1}},
            ],
            "yoke": [
                {"name": "Trim up", "source": {"kind": "button", "code": 288},
                 "action": {"type": "event", "event": "ELEV_TRIM_UP"}},
                {"name": "AP", "source": {"kind": "button", "code": 289},
                 "action": {"type": "event", "event": "AP_MASTER"}},
                {"name": "Aileron", "source": {"kind": "axis", "code": 0,
                 "raw_min": 0, "raw_max": 4095},
                 "action": {"type": "event", "event": "AILERON_SET"}},
                {"name": "Elevator", "source": {"kind": "axis", "code": 1},
                 "action": {"type": "event", "event": "ELEVATOR_SET"}},
                {"name": "View", "source": {"kind": "hat", "code": 16},
                 "hat": {"up": {"type": "event", "event": "VIEW_UP", "value": 1},
                         "down": {"type": "event", "event": "VIEW_DOWN", "value": 1}}},
            ],
        },
        "outputs": {"switch_panel": [{"type": "gear_leds"}]},
    }
)


def _by_label(els):
    return {e.label: e for e in els}


def test_switch_panel_has_hand_layout():
    assert has_hand_layout("switch_panel") is True
    assert has_hand_layout("yoke") is False


def test_switch_panel_renders_all_13_toggles():
    els = panel_layout(PROFILE, "switch_panel")
    toggles = [e for e in els if e.kind == SWITCH]
    assert len(toggles) == 13
    codes = {e.code for e in toggles}
    assert codes == set(range(13))  # codes 0..12


def test_mapped_toggle_carries_binding_and_live_key():
    bat = _by_label(panel_layout(PROFILE, "switch_panel"))["BAT"]
    assert bat.mapped is True
    assert bat.name == "Battery master"
    assert "MASTER_BATTERY_SET" in bat.action
    assert bat.ref == "bind:0"
    assert bat.live_key == ("switch", 0)


def test_unmapped_toggle_is_muted_but_still_live_capable():
    cowl = _by_label(panel_layout(PROFILE, "switch_panel"))["COWL"]  # code 6, unmapped
    assert cowl.mapped is False
    assert cowl.name == ""
    assert cowl.ref is None
    assert cowl.live_key == ("switch", 6)  # still highlights when flicked


def test_magneto_detents_are_individually_clickable_bars():
    # (looked up by code — the gear LEDs reuse the "L"/"R" labels by position)
    detents = [e for e in panel_layout(PROFILE, "switch_panel")
               if e.kind == BUTTON and e.code in range(13, 18)]
    assert {e.code for e in detents} == set(range(13, 18))  # codes 13..17
    assert all(e.source_kind == "switch" for e in detents)
    both = next(e for e in detents if e.code == 16)
    assert both.mapped and both.ref == "bind:2"  # code 16 (BOTH) is mapped
    off = next(e for e in detents if e.code == 13)
    assert off.mapped is False and off.live_key == ("switch", 13)


def test_gear_leds_map_each_field_individually():
    leds = [e for e in panel_layout(PROFILE, "switch_panel") if e.kind == LED]
    assert len(leds) == 3
    # each LED opens its OWN gear_leds field (solo path), not the whole output
    assert {e.ref for e in leds} == {"out:0:nose", "out:0:left", "out:0:right"}
    assert all(e.mapped for e in leds)


def test_gear_lever_positions_are_individual_bars():
    gears = [e for e in panel_layout(PROFILE, "switch_panel")
             if e.source_kind == "switch" and e.code in (18, 19)]
    up = next(e for e in gears if e.code == 18)
    dn = next(e for e in gears if e.code == 19)
    assert up.mapped and up.ref == "bind:3" and up.label == "Gear up"  # clear label
    assert up.live_key == ("switch", 18)  # lights when pressed at the device
    assert dn.mapped is False and dn.live_key == ("switch", 19)


def test_all_positions_within_unit_square():
    for dev in ("switch_panel", "yoke"):
        for e in panel_layout(PROFILE, dev):
            assert 0.0 <= e.x <= 1.0 and 0.0 <= e.y <= 1.0
            assert 0.0 < e.w <= 1.0 and 0.0 < e.h <= 1.0
            assert e.x + e.w <= 1.0001 and e.y + e.h <= 1.0001


def test_device_layout_one_element_per_binding_with_right_kinds():
    els = panel_layout(PROFILE, "yoke")
    assert len(els) == 5  # one per binding (2 axes, 2 buttons, 1 hat)
    by_name = {e.name: e for e in els}
    assert by_name["Aileron"].kind == AXIS
    assert by_name["Aileron"].live_key == ("axis", 0)
    assert by_name["Trim up"].kind == BUTTON
    assert by_name["Trim up"].live_key == ("button", 288)
    assert by_name["View"].kind == HAT
    assert all(e.ref and e.ref.startswith("bind:") for e in els)


def test_axis_carries_calibrated_range_for_the_bar():
    by_name = {e.name: e for e in panel_layout(PROFILE, "yoke")}
    assert (by_name["Aileron"].raw_min, by_name["Aileron"].raw_max) == (0, 4095)
    # An axis without explicit calibration leaves the range None (canvas fills in).
    assert (by_name["Elevator"].raw_min, by_name["Elevator"].raw_max) == (None, None)


def test_hat_has_no_live_key():
    view = {e.name: e for e in panel_layout(PROFILE, "yoke")}["View"]
    assert view.live_key is None  # hats need their own overlay, not on/off


def test_axes_stack_above_the_button_tiles():
    els = panel_layout(PROFILE, "yoke")
    axes = [e for e in els if e.kind == AXIS]
    tiles = [e for e in els if e.kind in (BUTTON, HAT)]
    # every axis bar sits above every button/hat tile
    assert max(e.y + e.h for e in axes) <= min(e.y for e in tiles) + 1e-9


ROCKER_PROFILE = Profile.model_validate({
    "name": "R",
    "bindings": {"multi_panel": [
        {"name": "Flaps up", "source": {"kind": "switch", "code": 16},
         "action": {"type": "event", "event": "FLAPS_DECR", "value": 1}},
        {"name": "Flaps down", "source": {"kind": "switch", "code": 17},
         "action": {"type": "event", "event": "FLAPS_INCR", "value": 1}},
        {"name": "AP master", "source": {"kind": "switch", "code": 7},
         "action": {"type": "event", "event": "AP_MASTER", "value": 1}},
    ]},
})


def test_flaps_up_down_become_two_stacked_bars():
    els = panel_layout(ROCKER_PROFILE, "multi_panel")
    flaps = [e for e in els if "Flaps" in e.label]  # labels = binding names now
    assert len(flaps) == 2  # the up/down pair -> two stacked bars, not two tiles
    up = next(e for e in flaps if e.code == 16)
    dn = next(e for e in flaps if e.code == 17)
    assert up.ref == "bind:0" and up.source_kind == "switch"
    assert up.label == "Flaps up" and dn.label == "Flaps down"
    assert dn.ref == "bind:1"
    assert up.y + up.h <= dn.y + 1e-9  # up stacks above down within one cell
    # the unrelated AP switch stays its own single tile
    assert len(els) == 3 and els[-1].label == "AP master"


OUT_PROFILE = Profile.model_validate({
    "name": "O",
    "outputs": {"multi_panel": [{
        "type": "multi_panel",
        "selector": [
            {"code": 0, "label": "ALT", "simvar": "AUTOPILOT ALTITUDE LOCK VAR",
             "min": 0, "max": 99999},
            {"code": 1, "label": "VS", "simvar": "AUTOPILOT VERTICAL HOLD VAR",
             "min": -9999, "max": 9999},
        ],
    }]},
})


def test_outputs_become_typed_clickable_elements_like_inputs():
    els = panel_layout(OUT_PROFILE, "multi_panel")  # a device with ONLY outputs
    segs = [e for e in els if e.kind == SEGMENT]
    assert len(segs) == 2  # one display cell per selector position
    assert {e.ref for e in segs} == {"out:0:selector/0", "out:0:selector/1"}
    assert {e.label for e in segs} == {"ALT", "VS"}  # short mode name, no simvar/BANK
    assert all(e.mapped for e in segs)  # click opens THAT output field's mapping


ZONE_PROFILE = Profile.model_validate({
    "name": "Z",
    "bindings": {"multi_panel": [
        {"name": "AP master", "source": {"kind": "switch", "code": 7},
         "action": {"type": "event", "event": "AP_MASTER", "value": 1}},
    ]},
    "outputs": {"multi_panel": [{
        "type": "multi_panel",
        "selector": [{"code": 0, "label": "ALT", "simvar": "X", "min": 0, "max": 9}],
    }]},
})


def test_controls_and_displays_are_separated_into_zones():
    els = panel_layout(ZONE_PROFILE, "multi_panel")
    controls = [e for e in els if e.kind == SWITCH]  # the AP-master button
    displays = [e for e in els if e.kind == SEGMENT]  # the ALT display cell
    assert controls and displays
    # every control sits above every display (separate zones, clear gap)
    assert max(e.y + e.h for e in controls) <= min(e.y for e in displays) + 1e-9


def test_unknown_device_is_empty():
    assert panel_layout(PROFILE, "does_not_exist") == []
