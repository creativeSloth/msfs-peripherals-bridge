"""Pure panel-reconstruction layout (positions + mapping, no display needed)."""

from msfs_peripherals_bridge.models import Profile
from msfs_peripherals_bridge.panel_layout import (
    AXIS,
    BUTTON,
    DOT,
    ENCODER,
    HAT,
    HEADER,
    LED,
    SEGMENT,
    SELECTOR,
    SWITCH,
    format_segment,
    has_hand_layout,
    lamp_lit,
    led_condition_text,
    panel_layout,
)

# A switch panel with a few toggles + one magneto detent + a gear_leds output,
# deliberately leaving some hardware codes unmapped (COWL=6, NAV=9).
PROFILE = Profile.model_validate(
    {
        "name": "Test",
        "bindings": {
            "switch_panel": [
                {
                    "name": "Battery master",
                    "source": {"kind": "switch", "code": 0},
                    "action": {"type": "event", "event": "MASTER_BATTERY_SET"},
                },
                {
                    "name": "Strobe lights",
                    "source": {"kind": "switch", "code": 10},
                    "action": {"type": "event", "event": "STROBES_SET"},
                },
                {
                    "name": "Magneto BOTH",
                    "source": {"kind": "switch", "code": 16},
                    "action": {"type": "event", "event": "MAGNETO1_BOTH", "value": 1},
                },
                {
                    "name": "Gear up",
                    "source": {"kind": "switch", "code": 18},
                    "action": {"type": "event", "event": "GEAR_UP", "value": 1},
                },
            ],
            "yoke": [
                {
                    "name": "Trim up",
                    "source": {"kind": "button", "code": 288},
                    "action": {"type": "event", "event": "ELEV_TRIM_UP"},
                },
                {
                    "name": "AP",
                    "source": {"kind": "button", "code": 289},
                    "action": {"type": "event", "event": "AP_MASTER"},
                },
                {
                    "name": "Aileron",
                    "source": {"kind": "axis", "code": 0, "raw_min": 0, "raw_max": 4095},
                    "action": {"type": "event", "event": "AILERON_SET"},
                },
                {
                    "name": "Elevator",
                    "source": {"kind": "axis", "code": 1},
                    "action": {"type": "event", "event": "ELEVATOR_SET"},
                },
                {
                    "name": "View",
                    "source": {"kind": "hat", "code": 16},
                    "hat": {
                        "up": {"type": "event", "event": "VIEW_UP", "value": 1},
                        "down": {"type": "event", "event": "VIEW_DOWN", "value": 1},
                    },
                },
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


def test_is_static_panel_flags_saitek_not_generic_devices():
    from msfs_peripherals_bridge.panel_layout import is_static_panel

    # hand-laid Saitek panels are static regardless of the profile's outputs
    assert is_static_panel(PROFILE, "switch_panel") is True
    assert is_static_panel(RADIO_PROFILE, "radio_panel") is True
    assert is_static_panel(None, "radio_panel") is True  # hand layout, no profile needed
    # multi_panel is static via its dedicated controller output block
    assert is_static_panel(OUT_PROFILE, "multi_panel") is True
    # a generic device (yoke, plain bindings) is NOT static -> encoder-add allowed
    assert is_static_panel(PROFILE, "yoke") is False
    assert is_static_panel(PROFILE, "tq6") is False  # unknown, no outputs
    assert is_static_panel(None, "yoke") is False


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
    detents = [
        e
        for e in panel_layout(PROFILE, "switch_panel")
        if e.kind == BUTTON and e.code in range(13, 18)
    ]
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


def test_gear_leds_carry_glow_from_sim_var():
    by_ref = {e.ref: e for e in panel_layout(PROFILE, "switch_panel") if e.kind == LED}
    # each lamp knows the gear-position var it glows from + a lamp threshold
    assert by_ref["out:0:nose"].var == "GEAR CENTER POSITION"
    assert by_ref["out:0:left"].var == "GEAR LEFT POSITION"
    assert by_ref["out:0:right"].var == "GEAR RIGHT POSITION"
    assert all(e.on_at == 0.5 for e in by_ref.values())


def test_lamp_lit_reads_bool_number_and_threshold():
    assert lamp_lit(None, 0.5) is False  # no reading yet -> dark
    assert lamp_lit(True, 0.5) is True and lamp_lit(False, 0.5) is False
    assert lamp_lit(1.0, 0.5) is True and lamp_lit(0.0, 0.5) is False
    assert lamp_lit(0.4, 0.5) is False and lamp_lit(0.5, 0.5) is True
    assert lamp_lit("on", None) is True  # non-numeric truthy string -> lit


def test_lamp_lit_window_and_below():
    # below-only (no lower bound): lit under the ceiling, dark at/above it
    assert lamp_lit(20, None, 30) is True and lamp_lit(30, None, 30) is False
    # window: lit strictly inside, dark past either edge
    assert lamp_lit(0.5, 0.01, 0.95) is True
    assert lamp_lit(1.0, 0.01, 0.95) is False and lamp_lit(0.0, 0.01, 0.95) is False


def test_led_condition_text_describes_each_shape():
    assert led_condition_text("V", 0.5, None) == "V >= 0.5"
    assert led_condition_text("V", None, 30) == "V < 30"
    assert led_condition_text("POS", 0.01, 0.95) == "POS >= 0.01 und POS < 0.95"
    assert led_condition_text("M", 2, None, on_op="==") == "M == 2"


def test_generic_led_appended_below_switch_panel_hand_layout():
    """A generic_panel LED added to the switch panel is shown (below the hand layout)
    even though the hand builder only knows its own controls + gear LEDs."""
    prof = Profile.model_validate(
        {
            "name": "T",
            "outputs": {
                "switch_panel": [
                    {"type": "gear_leds"},
                    {
                        "type": "generic_panel",
                        "length": 1,
                        "leds": [
                            {"name": "AP warn", "var": "W", "bit": 0, "on_at": None, "off_at": 30}
                        ],
                    },
                ]
            },
        }
    )
    els = panel_layout(prof, "switch_panel")
    extra = [e for e in els if e.ref == "out:1:leds/0"]
    assert len(extra) == 1  # the generic LED IS in the layout (ref = real output index 1)
    led = extra[0]
    assert led.kind == LED and led.var == "W" and led.off_at == 30
    assert led.y > 1.0  # placed below the normalised hand layout (canvas scrolls to it)


def test_format_segment_is_controller_faithful():
    assert format_segment(None) == ""  # no reading yet -> blank cell
    assert format_segment(118.0, "dec:2") == "118.00"  # freq keeps trailing zeros
    assert format_segment(12.34, "dec:1") == "12.3"  # gauge measure rounds to N decimals
    assert format_segment(-500.0, "dec:2") == ""  # negative freq/measure blanks
    assert format_segment(3000.4, "int") == "3000"  # integer readout rounds (format_row)
    assert format_segment(-750.0, "int") == "-750"  # ints keep their sign (e.g. VS)
    assert format_segment(True, "int") == "1" and format_segment(False, "int") == "0"
    assert format_segment(118.005, "") == "118"  # raw compact (.4g), unchanged default
    assert format_segment("ALT", "int") == "ALT"  # non-numeric passes through


def test_gear_lever_positions_are_individual_bars():
    gears = [
        e
        for e in panel_layout(PROFILE, "switch_panel")
        if e.source_kind == "switch" and e.code in (18, 19)
    ]
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
    els = [e for e in panel_layout(PROFILE, "yoke") if e.kind != HEADER]
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


ROCKER_PROFILE = Profile.model_validate(
    {
        "name": "R",
        "bindings": {
            "multi_panel": [
                {
                    "name": "Flaps up",
                    "source": {"kind": "switch", "code": 16},
                    "action": {"type": "event", "event": "FLAPS_DECR", "value": 1},
                },
                {
                    "name": "Flaps down",
                    "source": {"kind": "switch", "code": 17},
                    "action": {"type": "event", "event": "FLAPS_INCR", "value": 1},
                },
                {
                    "name": "AP master",
                    "source": {"kind": "switch", "code": 7},
                    "action": {"type": "event", "event": "AP_MASTER", "value": 1},
                },
            ]
        },
    }
)


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
    # the unrelated AP switch stays its own single tile (ignoring group headings)
    tiles = [e for e in els if e.kind != HEADER]
    assert len(tiles) == 3 and tiles[-1].label == "AP master"


OUT_PROFILE = Profile.model_validate(
    {
        "name": "O",
        "outputs": {
            "multi_panel": [
                {
                    "type": "multi_panel",
                    "selector": [
                        {
                            "code": 0,
                            "label": "ALT",
                            "simvar": "AUTOPILOT ALTITUDE LOCK VAR",
                            "min": 0,
                            "max": 99999,
                        },
                        {
                            "code": 1,
                            "label": "VS",
                            "simvar": "AUTOPILOT VERTICAL HOLD VAR",
                            "min": -9999,
                            "max": 9999,
                        },
                    ],
                }
            ]
        },
    }
)


def test_outputs_become_typed_clickable_elements_like_inputs():
    els = panel_layout(OUT_PROFILE, "multi_panel")  # a device with ONLY outputs
    segs = [e for e in els if e.kind == SEGMENT]
    assert len(segs) == 2  # one display cell per selector position
    assert {e.ref for e in segs} == {"out:0:selector/0", "out:0:selector/1"}
    assert {e.label for e in segs} == {"ALT", "VS"}  # short mode name, no simvar/BANK
    assert all(e.mapped for e in segs)  # click opens THAT output field's mapping
    # glow-from-sim: each cell reads its selector position's simvar (numeric, no on_at)
    by_ref = {e.ref: e for e in segs}
    assert by_ref["out:0:selector/0"].var == "AUTOPILOT ALTITUDE LOCK VAR"
    assert by_ref["out:0:selector/1"].var == "AUTOPILOT VERTICAL HOLD VAR"
    assert all(e.on_at is None for e in segs)  # segments show the value, not a lamp
    assert all(e.fmt == "int" for e in segs)  # multi selector value = integer (format_row)


ZONE_PROFILE = Profile.model_validate(
    {
        "name": "Z",
        "bindings": {
            "multi_panel": [
                {
                    "name": "AP master",
                    "source": {"kind": "switch", "code": 7},
                    "action": {"type": "event", "event": "AP_MASTER", "value": 1},
                },
            ]
        },
        "outputs": {
            "multi_panel": [
                {
                    "type": "multi_panel",
                    "selector": [{"code": 0, "label": "ALT", "simvar": "X", "min": 0, "max": 9}],
                }
            ]
        },
    }
)


def test_controls_and_displays_are_separated_into_zones():
    els = panel_layout(ZONE_PROFILE, "multi_panel")
    controls = [e for e in els if e.kind == SWITCH]  # the AP-master button
    displays = [e for e in els if e.kind == SEGMENT]  # the ALT display cell
    assert controls and displays
    # every control sits above every display (separate zones, clear gap)
    assert max(e.y + e.h for e in controls) <= min(e.y for e in displays) + 1e-9


GENERIC_PROFILE = Profile.model_validate(
    {
        "name": "G",
        "outputs": {
            "my_panel": [
                {
                    "type": "generic_panel",
                    "length": 4,
                    "leds": [
                        {
                            "name": "Gear",
                            "var": "GEAR HANDLE POSITION",
                            "byte": 0,
                            "bit": 2,
                            "on_at": 0.5,
                        }
                    ],
                    "displays": [
                        {"name": "Alt", "var": "INDICATED ALTITUDE", "offset": 1, "cells": 3},
                        {
                            "name": "Fuel",
                            "var": "FUEL TOTAL QUANTITY",
                            "offset": 2,
                            "cells": 1,
                            "decimals": 1,
                        },
                    ],
                }
            ]
        },
    }
)


def test_generic_panel_leds_and_displays_glow_from_sim():
    els = panel_layout(GENERIC_PROFILE, "my_panel")  # a user's own declared panel
    lamps = [e for e in els if e.kind == LED]
    segs = [e for e in els if e.kind == SEGMENT]
    # the declared LED glows from its var at its threshold (like the Saitek gear LEDs)
    assert len(lamps) == 1
    assert lamps[0].var == "GEAR HANDLE POSITION" and lamps[0].on_at == 0.5
    # each declared 7-seg display reads its var; decimals -> dec:N, else integer readout
    by_var = {e.var: e for e in segs}
    assert by_var["INDICATED ALTITUDE"].fmt == "int"
    assert by_var["FUEL TOTAL QUANTITY"].fmt == "dec:1"
    assert all(e.mapped and e.on_at is None for e in segs)


RADIO_PROFILE = Profile.model_validate(
    {
        "name": "R2",
        "outputs": {
            "radio_panel": [
                {
                    "type": "radio_panel",
                    "units": [
                        {
                            "name": "upper",
                            "row": "upper",
                            "outer_cw": 0,
                            "outer_ccw": 1,
                            "inner_cw": 2,
                            "inner_ccw": 3,
                            "swap": 4,
                            "banks": [
                                {
                                    "kind": "freq",
                                    "code": 0,
                                    "label": "COM1",
                                    "active": "A",
                                    "standby": "S",
                                    "swap_event": "SW",
                                    "whole_inc": "WI",
                                    "whole_dec": "WD",
                                    "fract_inc": "FI",
                                    "fract_dec": "FD",
                                },
                                {
                                    "kind": "freq",
                                    "code": 1,
                                    "label": "NAV1",
                                    "active": "A2",
                                    "standby": "S2",
                                    "swap_event": "SW2",
                                    "whole_inc": "WI2",
                                    "whole_dec": "WD2",
                                    "fract_inc": "FI2",
                                    "fract_dec": "FD2",
                                },
                            ],
                        }
                    ],
                }
            ]
        },
    }
)


def test_radio_panel_mode_row_is_mode_plus_act_stby_and_dot():
    els = panel_layout(RADIO_PROFILE, "radio_panel")
    # a bank row = the mode cell + Act/Stby displays + dot (encoder/swap are per-unit)
    row = [e for e in els if e.ref and e.ref.split("|")[0] == "out:0:units/0/banks/0"]
    assert sorted(e.kind for e in row) == sorted([SELECTOR, SEGMENT, SEGMENT, DOT])
    mode = next(e for e in row if e.kind == SELECTOR)
    assert "Selektor-Code 0" in mode.action  # selector code lives in the tooltip
    assert mode.ref == "out:0:units/0/banks/0"  # opens the whole bank editor
    assert {e.label for e in row if e.kind == SEGMENT} == {"Act", "Stby"}  # not the mode name
    active = next(e for e in row if e.kind == SEGMENT and e.ref.endswith("|active"))
    assert active.ref == "out:0:units/0/banks/0|active"


def test_radio_freq_segments_glow_from_active_standby_vars():
    els = panel_layout(RADIO_PROFILE, "radio_panel")
    row = [e for e in els if e.ref and e.ref.split("|")[0] == "out:0:units/0/banks/0"]
    active = next(e for e in row if e.kind == SEGMENT and e.ref.endswith("|active"))
    standby = next(e for e in row if e.kind == SEGMENT and e.ref.endswith("|standby"))
    # a freq bank's cells read the frequency vars (numeric readout, no lamp threshold)
    assert active.var == "A" and standby.var == "S"
    assert active.on_at is None and standby.on_at is None
    # controller-faithful: freq shows NNN.NN (dec:2), the coarse view of format_frequency
    assert active.fmt == "dec:2" and standby.fmt == "dec:2"


def test_radio_panel_unit_has_two_rings_and_a_separate_swap_button():
    els = panel_layout(RADIO_PROFILE, "radio_panel")
    unit = [e for e in els if e.ref and e.ref.split("|")[0] == "out:0:units/0"]
    # the encoder is TWO rings (no push); the swap is a SEPARATE normal button
    outer = next(e for e in unit if e.kind == ENCODER and e.label == "außen")
    assert outer.ref == "out:0:units/0|outer_cw,outer_ccw"
    inner = next(e for e in unit if e.kind == ENCODER and e.label == "innen")
    assert inner.ref == "out:0:units/0|inner_cw,inner_ccw"
    swap = next(e for e in unit if e.kind == BUTTON)
    assert swap.ref == "out:0:units/0|swap" and swap.label == "SWAP-Taster"
    assert any(e.kind == HEADER and "upper" in e.label for e in els)


def test_unknown_device_is_empty():
    assert panel_layout(PROFILE, "does_not_exist") == []


# --------------------------------------------------------------------------- #
# Edit mode: element_key / snap / apply_layout_overrides
# --------------------------------------------------------------------------- #
def test_element_key_prefers_physical_then_ref_then_label():
    from msfs_peripherals_bridge.panel_layout import PanelElement, element_key

    phys = PanelElement(SWITCH, "BAT", 0, 0, 0.1, 0.1, code=0, live_key=("switch", 0))
    assert element_key(phys) == "switch:0"  # physical code -> stable across reorder
    out = PanelElement(LED, "N", 0, 0, 0.1, 0.1, ref="out:2")
    assert element_key(out) == "out:2"
    bare = PanelElement(HEADER, "Schalter", 0, 0, 1.0, 0.05)
    assert element_key(bare) == "header:Schalter"


def test_snap_rounds_to_nearest_step():
    from msfs_peripherals_bridge.panel_layout import snap

    assert abs(snap(0.10, 0.05) - 0.10) < 1e-9
    assert abs(snap(0.12, 0.05) - 0.10) < 1e-9
    assert abs(snap(0.13, 0.05) - 0.15) < 1e-9
    assert snap(0.42, 0) == 0.42  # step<=0 -> passthrough (no clamping)


def test_apply_layout_overrides_moves_only_matching_elements():
    from msfs_peripherals_bridge.panel_layout import PanelElement, apply_layout_overrides

    els = [
        PanelElement(SWITCH, "BAT", 0.0, 0.0, 0.1, 0.1, code=0, live_key=("switch", 0)),
        PanelElement(SWITCH, "ALT", 0.1, 0.0, 0.1, 0.1, code=1, live_key=("switch", 1)),
    ]
    moved = apply_layout_overrides(els, {"switch:0": (0.5, 0.5)})
    assert (moved[0].x, moved[0].y) == (0.5, 0.5)  # BAT moved
    assert (moved[1].x, moved[1].y) == (0.1, 0.0)  # ALT untouched
    assert els[0].x == 0.0  # original list is not mutated (frozen dataclass)


def test_panel_layout_persistence_round_trip(tmp_path):
    from msfs_peripherals_bridge.mapping.loader import (
        clear_panel_layout,
        load_panel_layout,
        save_panel_layout_override,
    )

    path = tmp_path / "panel-layouts.yaml"
    assert load_panel_layout("switch_panel", path) == {}
    save_panel_layout_override("switch_panel", "switch:0", 0.5, 0.25, path=path)
    save_panel_layout_override("switch_panel", "out:1", 0.1, 0.9, path=path)
    save_panel_layout_override("multi_panel", "button:7", 0.2, 0.2, path=path)
    loaded = load_panel_layout("switch_panel", path)
    assert loaded == {"switch:0": (0.5, 0.25), "out:1": (0.1, 0.9)}

    clear_panel_layout("switch_panel", path=path)
    assert load_panel_layout("switch_panel", path) == {}
    assert load_panel_layout("multi_panel", path) == {"button:7": (0.2, 0.2)}  # kept


def test_apply_layout_overrides_resizes_with_four_tuple():
    from msfs_peripherals_bridge.panel_layout import PanelElement, apply_layout_overrides

    els = [PanelElement(SWITCH, "BAT", 0.0, 0.0, 0.1, 0.1, code=0, live_key=("switch", 0))]
    out = apply_layout_overrides(els, {"switch:0": (0.5, 0.25, 0.3, 0.2)})
    assert (out[0].x, out[0].y, out[0].w, out[0].h) == (0.5, 0.25, 0.3, 0.2)


def test_panel_layout_persists_size_and_move_keeps_it(tmp_path):
    from msfs_peripherals_bridge.mapping.loader import (
        load_panel_layout,
        save_panel_layout_override,
    )

    path = tmp_path / "panel-layouts.yaml"
    # resize -> full (x, y, w, h) stored
    save_panel_layout_override("dev", "switch:0", 0.1, 0.2, 0.3, 0.4, path=path)
    assert load_panel_layout("dev", path) == {"switch:0": (0.1, 0.2, 0.3, 0.4)}
    # a later plain move (no w/h) keeps the previously stored size
    save_panel_layout_override("dev", "switch:0", 0.5, 0.6, path=path)
    assert load_panel_layout("dev", path) == {"switch:0": (0.5, 0.6, 0.3, 0.4)}


def test_panel_decorations_round_trip_and_clean(tmp_path):
    from msfs_peripherals_bridge.mapping.loader import (
        load_panel_decorations,
        save_panel_decorations,
    )

    path = tmp_path / "panel-layouts.yaml"
    assert load_panel_decorations("dev", path) == []
    save_panel_decorations(
        "dev",
        [
            {"t": "box", "x": 0.1, "y": 0.1, "w": 0.3, "h": 0.2, "text": "Zündung"},
            {"t": "line", "x": 0.0, "y": 0.5, "w": 0.4, "h": 0.0, "text": ""},
            {"t": "nope", "x": 0, "y": 0, "w": 0, "h": 0},  # unknown type dropped
        ],
        path=path,
    )
    decos = load_panel_decorations("dev", path)
    assert [d["t"] for d in decos] == ["box", "line"]
    assert decos[0]["text"] == "Zündung"
    # empty list removes the device's entry entirely
    save_panel_decorations("dev", [], path=path)
    assert load_panel_decorations("dev", path) == []


def test_hidden_elements_round_trip(tmp_path):
    from msfs_peripherals_bridge.mapping.loader import (
        load_hidden_elements,
        save_hidden_elements,
    )

    path = tmp_path / "panel-layouts.yaml"
    assert load_hidden_elements("dev", path) == set()
    save_hidden_elements("dev", {"header:Schalter", "switch:3"}, path=path)
    assert load_hidden_elements("dev", path) == {"header:Schalter", "switch:3"}
    save_hidden_elements("dev", set(), path=path)  # empty clears it
    assert load_hidden_elements("dev", path) == set()


def test_element_label_override_round_trip(tmp_path):
    from msfs_peripherals_bridge.mapping.loader import (
        load_element_labels,
        save_element_label,
    )

    path = tmp_path / "panel-layouts.yaml"
    assert load_element_labels("dev", path) == {}
    save_element_label("dev", "header:Schalter", "Meine Schalter", path=path)
    assert load_element_labels("dev", path) == {"header:Schalter": "Meine Schalter"}
    save_element_label("dev", "header:Schalter", "  ", path=path)  # blank drops it
    assert load_element_labels("dev", path) == {}


def test_clear_panel_layout_wipes_all_sections(tmp_path):
    from msfs_peripherals_bridge.mapping.loader import (
        clear_panel_layout,
        load_element_labels,
        load_hidden_elements,
        load_panel_decorations,
        load_panel_layout,
        save_element_label,
        save_hidden_elements,
        save_panel_decorations,
        save_panel_layout_override,
    )

    path = tmp_path / "panel-layouts.yaml"
    save_panel_layout_override("dev", "switch:0", 0.1, 0.2, path=path)
    save_panel_decorations("dev", [{"t": "line", "x": 0, "y": 0.5, "w": 0.4, "h": 0}], path=path)
    save_hidden_elements("dev", {"header:Schalter"}, path=path)
    save_element_label("dev", "header:Schalter", "X", path=path)
    clear_panel_layout("dev", path=path)
    assert load_panel_layout("dev", path) == {}
    assert load_panel_decorations("dev", path) == []
    assert load_hidden_elements("dev", path) == set()
    assert load_element_labels("dev", path) == {}
