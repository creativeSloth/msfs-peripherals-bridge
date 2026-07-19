"""Pure panel-reconstruction layout (positions + mapping, no display needed)."""

from msfs_peripherals_bridge.models import Profile
from msfs_peripherals_bridge.panel_layout import (
    AXIS,
    BUTTON,
    HAT,
    LED,
    LEVER,
    ROCKER,
    SELECTOR,
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


def test_magneto_is_one_selector_referencing_its_mapped_detent():
    mag = _by_label(panel_layout(PROFILE, "switch_panel"))["MAGNETOS"]
    assert mag.kind == SELECTOR
    assert mag.mapped is True  # code 16 (BOTH) is mapped
    assert mag.ref == "bind:2"
    assert "BOTH" in mag.name


def test_gear_leds_reference_the_output():
    els = _by_label(panel_layout(PROFILE, "switch_panel"))
    leds = [els[k] for k in ("N", "L", "R")]
    assert all(e.kind == LED for e in leds)
    assert all(e.mapped and e.ref == "out:0" for e in leds)


def test_gear_lever_present():
    gear = _by_label(panel_layout(PROFILE, "switch_panel"))["GEAR"]
    assert gear.kind == LEVER
    assert gear.mapped is True  # gear-up (code 18) is mapped
    assert gear.ref == "bind:3"


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


def test_flaps_up_down_merge_into_one_rocker():
    els = panel_layout(ROCKER_PROFILE, "multi_panel")
    rockers = [e for e in els if e.kind == ROCKER]
    assert len(rockers) == 1  # the up/down pair became ONE element
    r = rockers[0]
    assert r.label == "flaps"  # common base
    assert r.live_key == ("switch", 16) and r.live_key2 == ("switch", 17)
    assert r.ref == "bind:0" and r.ref2 == "bind:1"
    # the unrelated AP switch stays its own tile; no stray extra rocker
    others = [e for e in els if e.kind != ROCKER]
    assert len(els) == 2 and [e.kind for e in others] == [SWITCH]


def test_unknown_device_is_empty():
    assert panel_layout(PROFILE, "does_not_exist") == []
