import pytest
from pydantic import ValidationError

from msfs_peripherals_bridge.mapping.display import BLANK, MINUS
from msfs_peripherals_bridge.mapping.multi_panel import (
    ENCODER_CCW,
    ENCODER_CW,
    MultiPanelController,
)
from msfs_peripherals_bridge.models import (
    DimmerTarget,
    MultiPanelDimmer,
    MultiPanelOutput,
    SelectorEntry,
    SelectorSource,
)
from msfs_peripherals_bridge.simconnect.protocol import SendEvent, SetSimVar


def make_config() -> MultiPanelOutput:
    return MultiPanelOutput(
        selector=[
            # ALT (code 0): no set_event -> writes the SimVar directly, clamps.
            SelectorEntry(
                code=0,
                label="ALT",
                simvar="AUTOPILOT ALTITUDE LOCK VAR",
                step=100,
                min=0,
                max=99999,
            ),
            # HDG (code 3): set_event + rollover at 359/0.
            SelectorEntry(
                code=3,
                label="HDG",
                simvar="AUTOPILOT HEADING LOCK DIR",
                set_event="HEADING_BUG_SET",
                step=1,
                min=0,
                max=359,
                rollover=True,
            ),
        ],
        ap_master="AUTOPILOT MASTER",
        mode_var="L:AUTOPILOT_MODE",
    )


def test_default_selector_is_first_entry():
    c = MultiPanelController(make_config())
    assert c.selector == 0


def test_subscriptions_cover_values_and_leds():
    c = MultiPanelController(make_config())
    subs = set(c.subscriptions())
    assert "AUTOPILOT ALTITUDE LOCK VAR" in subs
    assert "AUTOPILOT HEADING LOCK DIR" in subs
    assert "AUTOPILOT MASTER" in subs
    assert "L:AUTOPILOT_MODE" in subs


def test_encoder_without_base_value_does_nothing():
    c = MultiPanelController(make_config())
    assert c.on_encoder(clockwise=True) == []


def test_encoder_writes_simvar_when_no_event():
    c = MultiPanelController(make_config())
    c.on_state("AUTOPILOT ALTITUDE LOCK VAR", 5000)
    cmds = c.on_encoder(clockwise=True)
    assert cmds == [SetSimVar(name="AUTOPILOT ALTITUDE LOCK VAR", unit="number", value=5100)]


def test_encoder_fires_event_when_configured():
    c = MultiPanelController(make_config())
    c.on_selector(3)  # HDG
    c.on_state("AUTOPILOT HEADING LOCK DIR", 90)
    assert c.on_encoder(clockwise=True) == [SendEvent(name="HEADING_BUG_SET", data=91)]


def _accel_config() -> MultiPanelOutput:
    return MultiPanelOutput(
        selector=[
            SelectorEntry(
                code=0, label="ALT", simvar="V", step=100, fast_step=500, min=0, max=99999
            ),
        ],
    )


def test_encoder_two_quick_detents_stay_at_base_step():
    # The "weaker" part: a brief quick turn must NOT accelerate.
    t = [0.0]
    c = MultiPanelController(_accel_config(), clock=lambda: t[0])
    c.on_state("V", 5000)
    c.on_encoder(clockwise=True)  # base -> 5100
    t[0] += 0.02
    c.on_encoder(clockwise=True)  # fast streak 1 (< _FAST_AFTER) -> base -> 5200
    assert c.values["V"] == 5200


def test_encoder_accelerates_after_sustained_fast_spin():
    t = [0.0]
    c = MultiPanelController(_accel_config(), clock=lambda: t[0])
    c.on_state("V", 5000)
    # detents 1-3 stay base (streak 0,1,2 < _FAST_AFTER); detent 4 (streak 3) -> fast.
    for _ in range(4):
        c.on_encoder(clockwise=True)
        t[0] += 0.02
    assert c.values["V"] == 5800  # 5100, 5200, 5300, +500
    t[0] += 1.0  # a slow detent resets the streak
    c.on_encoder(clockwise=True)
    assert c.values["V"] == 5900  # back to base step


def test_clamp_does_not_exceed_max():
    c = MultiPanelController(make_config())
    c.on_state("AUTOPILOT ALTITUDE LOCK VAR", 99950)
    c.on_encoder(clockwise=True)
    assert c.values["AUTOPILOT ALTITUDE LOCK VAR"] == 99999


def test_rollover_wraps_heading():
    c = MultiPanelController(make_config())
    c.on_selector(3)
    c.on_state("AUTOPILOT HEADING LOCK DIR", 359)
    assert c.on_encoder(clockwise=True) == [SendEvent(name="HEADING_BUG_SET", data=0)]
    c.on_state("AUTOPILOT HEADING LOCK DIR", 0)
    assert c.on_encoder(clockwise=False) == [SendEvent(name="HEADING_BUG_SET", data=359)]


def test_on_event_routes_selector_and_encoder():
    c = MultiPanelController(make_config())
    c.on_state("AUTOPILOT HEADING LOCK DIR", 90)
    # selector to HDG (code 3); enter edge only
    assert c.on_event(code=3, value=1) == []
    assert c.selector == 3
    # encoder CW tick
    assert c.on_event(code=ENCODER_CW, value=1) == [SendEvent(name="HEADING_BUG_SET", data=91)]
    # release edges ignored
    assert c.on_event(code=ENCODER_CCW, value=0) == []


def test_render_shows_selected_value_top_row():
    c = MultiPanelController(make_config())
    c.on_selector(3)  # HDG
    c.on_state("AUTOPILOT HEADING LOCK DIR", 90)
    report = c.render()
    assert report[0] == 0x00  # report id
    assert list(report[1:6]) == [BLANK, BLANK, BLANK, 9, 0]  # top row "  90"
    assert list(report[6:11]) == [BLANK] * 5  # bottom row blank


def test_display_rows_persist_alt_top_vs_bottom():
    cfg = MultiPanelOutput(
        selector=[
            SelectorEntry(code=0, label="ALT", simvar="AP ALT", step=100, min=0, max=99999),
            SelectorEntry(
                code=1,
                label="VS",
                simvar="AP VS",
                step=100,
                min=-9999,
                max=9999,
                display_row="bottom",
            ),
        ],
    )
    c = MultiPanelController(cfg)
    c.on_state("AP ALT", 3000)
    c.on_state("AP VS", -500)
    # Selecting VS still leaves ALT on the top row; only the encoder re-points.
    c.on_selector(1)
    report = c.render()
    assert list(report[1:6]) == [BLANK, 3, 0, 0, 0]  # top " 3000"
    assert list(report[6:11]) == [BLANK, MINUS, 5, 0, 0]  # bottom "-500"


def _sticky_config() -> MultiPanelOutput:
    return MultiPanelOutput(
        selector=[
            SelectorEntry(
                code=0,
                label="ALT",
                simvar="AUTOPILOT ALTITUDE LOCK VAR",
                set_event="AP_ALT_VAR_SET_ENGLISH",
                step=100,
                min=0,
                max=99999,
                sticky=True,
            ),
            SelectorEntry(
                code=1,
                label="VS",
                simvar="AUTOPILOT VERTICAL HOLD VAR",
                set_event="AP_VS_VAR_SET_ENGLISH",
                step=100,
                min=-9999,
                max=9999,
                display_row="bottom",
                sticky=True,
            ),
        ],
    )


def test_sticky_value_starts_at_zero_and_edits_without_state():
    # Encoder-owned: it starts at 0 and the encoder works immediately, without
    # waiting for a SimVar to stream in.
    c = MultiPanelController(_sticky_config())
    assert c.on_encoder(clockwise=True) == [SendEvent(name="AP_ALT_VAR_SET_ENGLISH", data=100)]
    assert list(c.render()[1:6]) == [BLANK, BLANK, 1, 0, 0]  # top "  100"


def test_sticky_value_ignores_gauge_reset():
    # The JF gauge drives ALTITUDE LOCK VAR to 80000 / 0 on mode switches; a sticky
    # value must not follow it — the dialed target stays put.
    c = MultiPanelController(_sticky_config())
    c.on_encoder(clockwise=True)
    c.on_encoder(clockwise=True)  # -> 200
    c.on_state("AUTOPILOT ALTITUDE LOCK VAR", 80000)
    c.on_state("AUTOPILOT ALTITUDE LOCK VAR", 0)
    assert list(c.render()[1:6]) == [BLANK, BLANK, 2, 0, 0]  # still "  200"


def test_sticky_values_persist_across_selector_switch():
    c = MultiPanelController(_sticky_config())
    c.on_encoder(clockwise=True)  # ALT (top) -> 100
    c.on_selector(1)  # VS
    c.on_encoder(clockwise=False)  # VS (bottom) -> -100
    report = c.render()
    assert list(report[1:6]) == [BLANK, BLANK, 1, 0, 0]  # top ALT still "  100"
    assert list(report[6:11]) == [BLANK, MINUS, 1, 0, 0]  # bottom VS "-100"


def _off_above_config() -> MultiPanelOutput:
    return MultiPanelOutput(
        selector=[
            SelectorEntry(
                code=0,
                label="ALT",
                simvar="AP ALT",
                set_event="AP_ALT_VAR_SET_ENGLISH",
                step=100,
                min=0,
                max=99999,
                off_above=60000,
            ),
        ],
    )


def test_off_above_shows_zero_for_sentinel_and_missing():
    c = MultiPanelController(_off_above_config())
    # No state yet -> 0 (not blank).
    assert list(c.render()[1:6]) == [BLANK, BLANK, BLANK, BLANK, 0]
    # The JF "off" sentinel (ALT LOCK VAR parks at 80000) -> 0.
    c.on_state("AP ALT", 80000)
    assert list(c.render()[1:6]) == [BLANK, BLANK, BLANK, BLANK, 0]
    # A real target below the threshold shows through.
    c.on_state("AP ALT", 5000)
    assert list(c.render()[1:6]) == [BLANK, 5, 0, 0, 0]


def test_off_above_encoder_edits_up_from_zero_when_off():
    c = MultiPanelController(_off_above_config())
    c.on_state("AP ALT", 80000)  # off sentinel
    # Turning the knob edits up from 0, not from 80000.
    assert c.on_encoder(clockwise=True) == [SendEvent(name="AP_ALT_VAR_SET_ENGLISH", data=100)]


def _crs_config() -> MultiPanelOutput:
    return MultiPanelOutput(
        selector=[
            SelectorEntry(
                code=4,
                label="CRS",
                simvar="NAV OBS:1",
                set_event="VOR1_SET",
                step=1,
                min=0,
                max=359,
                rollover=True,
                alt_sources=[SelectorSource(simvar="NAV OBS:2", set_event="VOR2_SET")],
            ),
        ],
    )


def test_subscriptions_include_alt_sources():
    c = MultiPanelController(_crs_config())
    assert "NAV OBS:1" in c.subscriptions()
    assert "NAV OBS:2" in c.subscriptions()


def test_toggle_source_switches_encoder_target_and_event():
    c = MultiPanelController(_crs_config())
    c.on_selector(4)
    c.on_state("NAV OBS:1", 100)
    c.on_state("NAV OBS:2", 200)
    # Source 1: edits NAV OBS:1 via VOR1_SET.
    assert c.on_encoder(clockwise=True) == [SendEvent(name="VOR1_SET", data=101)]
    # Flip to source 2: edits NAV OBS:2 via VOR2_SET.
    c.toggle_source()
    assert c.on_encoder(clockwise=True) == [SendEvent(name="VOR2_SET", data=201)]
    # Flip back to source 1 (wraps).
    c.toggle_source()
    assert c.on_encoder(clockwise=True) == [SendEvent(name="VOR1_SET", data=102)]


def test_crs_source_index_shows_in_leftmost_top_cell():
    # The panel blanks the bottom row in CRS mode, so the index sits in the
    # leftmost top cell: [index][blank][hundreds][tens][ones].
    c = MultiPanelController(_crs_config())
    c.on_selector(4)
    c.on_state("NAV OBS:1", 90)
    c.on_state("NAV OBS:2", 270)
    # Source 1, course 90 -> [1, blank, "_90" in 3 cells].
    assert list(c.render()[1:6]) == [1, BLANK, BLANK, 9, 0]
    # Source 2, course 270 -> [2, blank, "270"].
    c.toggle_source()
    assert list(c.render()[1:6]) == [2, BLANK, 2, 7, 0]


def _dimmer_config() -> MultiPanelOutput:
    return MultiPanelOutput(
        selector=[
            SelectorEntry(code=0, label="ALT", simvar="AP ALT", step=100, min=0, max=99999),
        ],
        dimmer=MultiPanelDimmer(
            cw=18,
            ccw=19,
            step=10,
            min=0,
            max=100,
            targets=[
                DimmerTarget(event="LIGHT_POTENTIOMETER_2_SET", full=100),
                DimmerTarget(var="L:PANEL_LIGHT", full=10),
            ],
            follow_event="NAV_LIGHTS_SET",
        ),
    )


def test_dimmer_subscriptions_and_consumes():
    c = MultiPanelController(_dimmer_config())
    subs = set(c.subscriptions())
    # Var targets are subscribed; the event target has nothing to read back.
    assert "L:PANEL_LIGHT" in subs
    assert c.consumes(18) and c.consumes(19)
    assert not c.consumes(99)


def test_dimmer_scales_each_target_and_nav_follow():
    # Self-tracks from min (0) — no sim read needed, since light LVars aren't readable.
    c = MultiPanelController(_dimmer_config())
    # One detent up -> 10%: potentiometer to 10 (full 100), panel to 1 (full 10), nav on.
    assert c.on_event(code=18, value=1) == [
        SendEvent(name="LIGHT_POTENTIOMETER_2_SET", data=10),
        SetSimVar(name="L:PANEL_LIGHT", unit="number", value=1),
        SendEvent(name="NAV_LIGHTS_SET", data=1),
    ]
    # Back down to 0: both off, nav off.
    assert c.on_event(code=19, value=1) == [
        SendEvent(name="LIGHT_POTENTIOMETER_2_SET", data=0),
        SetSimVar(name="L:PANEL_LIGHT", unit="number", value=0),
        SendEvent(name="NAV_LIGHTS_SET", data=0),
    ]


def test_dimmer_clamps_at_max():
    c = MultiPanelController(_dimmer_config())
    c._dimmer_value = 95
    c.on_event(code=18, value=1)  # 95 + 10 -> clamp 100
    assert c._dimmer_value == 100


def test_dimmer_emits_nothing_at_rail():
    # Held at the ceiling, more "up" detents must NOT re-send the same value —
    # the flood would access-violate the MobiFlight/SimConnect link.
    c = MultiPanelController(_dimmer_config())
    c._dimmer_value = 100
    assert c.on_event(code=18, value=1) == []  # already maxed -> no commands
    assert c._dimmer_value == 100
    c._dimmer_value = 0
    assert c.on_event(code=19, value=1) == []  # already at floor -> no commands


def test_render_led_byte_reflects_ap_and_mode():
    c = MultiPanelController(make_config())
    c.on_state("AUTOPILOT MASTER", 1)
    c.on_state("L:AUTOPILOT_MODE", 2)  # HDG mode -> bit 1
    led = c.render()[11]
    assert led == (1 << 0) | (1 << 1)  # AP + HDG


def test_render_mode_led_lit_with_ap_master_off():
    c = MultiPanelController(make_config())
    c.on_state("AUTOPILOT MASTER", 0)
    c.on_state("L:AUTOPILOT_MODE", 2)  # HDG selected while AP off
    assert c.render()[11] == (1 << 1)  # HDG lit, AP bit dark


def test_render_blinks_ias_in_omni_mode():
    c = MultiPanelController(make_config())
    c.on_state("AUTOPILOT MASTER", 1)
    c.on_state("L:AUTOPILOT_MODE", 1)  # OMNI
    assert c.render(blink_on=True)[11] == (1 << 0) | (1 << 2) | (1 << 3)  # AP+NAV+IAS
    assert c.render(blink_on=False)[11] == (1 << 0) | (1 << 2)  # AP+NAV


def test_render_minus_for_negative_value():
    cfg = MultiPanelOutput(
        selector=[
            SelectorEntry(
                code=1,
                label="VS",
                simvar="AUTOPILOT VERTICAL HOLD VAR",
                set_event="AP_VS_VAR_SET_ENGLISH",
                step=100,
                fast_step=1000,
                min=-9999,
                max=9999,
            )
        ],
    )
    c = MultiPanelController(cfg)
    c.on_state("AUTOPILOT VERTICAL HOLD VAR", -500)
    assert list(c.render()[1:6]) == [BLANK, MINUS, 5, 0, 0]


def _powered_config() -> MultiPanelOutput:
    cfg = make_config()
    return cfg.model_copy(update={"power": "ELECTRICAL MASTER BATTERY"})


def test_power_gate_in_subscriptions():
    c = MultiPanelController(_powered_config())
    assert "ELECTRICAL MASTER BATTERY" in c.subscriptions()


def test_render_blank_when_battery_off():
    c = MultiPanelController(_powered_config())
    c.on_state("AUTOPILOT ALTITUDE LOCK VAR", 5000)
    c.on_state("AUTOPILOT MASTER", 1)
    c.on_state("L:AUTOPILOT_MODE", 2)  # would light HDG if powered
    # Battery unknown -> dark; then explicitly off -> still dark.
    assert list(c.render()[1:13]) == [BLANK] * 10 + [0x00, 0x00]
    c.on_state("ELECTRICAL MASTER BATTERY", 0)
    assert list(c.render()[1:13]) == [BLANK] * 10 + [0x00, 0x00]


def test_render_lit_when_battery_on():
    c = MultiPanelController(_powered_config())
    c.on_state("AUTOPILOT ALTITUDE LOCK VAR", 5000)
    c.on_state("AUTOPILOT MASTER", 1)
    c.on_state("ELECTRICAL MASTER BATTERY", 1)
    report = c.render()
    assert list(report[1:6]) == [BLANK, 5, 0, 0, 0]  # ALT value shown (right-justified)
    assert report[11] == (1 << 0)  # AP LED lit


def test_no_power_gate_always_lit():
    # Default config has no power var -> renders without any battery state.
    c = MultiPanelController(make_config())
    c.on_state("AUTOPILOT ALTITUDE LOCK VAR", 5000)
    assert list(c.render()[1:6]) == [BLANK, 5, 0, 0, 0]


def _bool_led_config() -> MultiPanelOutput:
    return MultiPanelOutput(
        selector=[
            SelectorEntry(code=0, label="ALT", simvar="AP ALT", step=100, min=0, max=99999),
        ],
        bool_leds={"alt": "L:JF_PA28_AP_alt", "vs": "L:JF_PA28_AP_vs"},
    )


def test_bool_led_vars_are_subscribed():
    subs = set(MultiPanelController(_bool_led_config()).subscriptions())
    assert {"L:JF_PA28_AP_alt", "L:JF_PA28_AP_vs"} <= subs


def test_bool_leds_light_alt_vs_independent_of_mode():
    c = MultiPanelController(_bool_led_config())
    c.on_state("L:AUTOPILOT_MODE", 2)  # HDG (bit 1)
    c.on_state("L:JF_PA28_AP_alt", 1)  # ALT hold engaged (bit 4)
    assert c.render()[11] == (1 << 1) | (1 << 4)  # HDG + ALT together
    c.on_state("L:JF_PA28_AP_vs", 1)  # + VS hold (bit 5)
    assert c.render()[11] == (1 << 1) | (1 << 4) | (1 << 5)
    c.on_state("L:JF_PA28_AP_alt", 0)  # ALT off again
    assert c.render()[11] == (1 << 1) | (1 << 5)


def test_bool_leds_reject_unknown_button_name():
    with pytest.raises(ValidationError):
        MultiPanelOutput(
            selector=[SelectorEntry(code=0, label="ALT", simvar="AP ALT", step=1, min=0, max=9)],
            bool_leds={"bogus": "L:WHATEVER"},
        )
