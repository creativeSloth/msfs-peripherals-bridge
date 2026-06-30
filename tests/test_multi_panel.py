from msfs_peripherals_bridge.mapping.display import BLANK, MINUS
from msfs_peripherals_bridge.mapping.multi_panel import (
    ENCODER_CCW,
    ENCODER_CW,
    MultiPanelController,
)
from msfs_peripherals_bridge.models import MultiPanelOutput, SelectorEntry
from msfs_peripherals_bridge.simconnect.protocol import SendEvent, SetSimVar


def make_config() -> MultiPanelOutput:
    return MultiPanelOutput(
        selector=[
            # ALT (code 0): no set_event -> writes the SimVar directly, clamps.
            SelectorEntry(
                code=0, label="ALT", simvar="AUTOPILOT ALTITUDE LOCK VAR",
                step=100, fast_step=1000, min=0, max=99999,
            ),
            # HDG (code 3): set_event + rollover at 359/0.
            SelectorEntry(
                code=3, label="HDG", simvar="AUTOPILOT HEADING LOCK DIR",
                set_event="HEADING_BUG_SET", step=1, fast_step=10,
                min=0, max=359, rollover=True,
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
    assert c.on_encoder(clockwise=True, now=0.0) == []


def test_encoder_writes_simvar_when_no_event():
    c = MultiPanelController(make_config())
    c.on_state("AUTOPILOT ALTITUDE LOCK VAR", 5000)
    cmds = c.on_encoder(clockwise=True, now=0.0)
    assert cmds == [SetSimVar(name="AUTOPILOT ALTITUDE LOCK VAR", unit="number", value=5100)]


def test_encoder_fires_event_when_configured():
    c = MultiPanelController(make_config())
    c.on_selector(3)  # HDG
    c.on_state("AUTOPILOT HEADING LOCK DIR", 90)
    assert c.on_encoder(clockwise=True, now=0.0) == [SendEvent(name="HEADING_BUG_SET", data=91)]


def test_fast_spin_uses_fast_step():
    c = MultiPanelController(make_config(), fast_window=0.2)
    c.on_state("AUTOPILOT ALTITUDE LOCK VAR", 5000)
    c.on_encoder(clockwise=True, now=0.0)  # first tick: slow (+100) -> 5100
    cmds = c.on_encoder(clockwise=True, now=0.05)  # 50ms later: fast (+1000) -> 6100
    assert cmds == [SetSimVar(name="AUTOPILOT ALTITUDE LOCK VAR", unit="number", value=6100)]


def test_clamp_does_not_exceed_max():
    c = MultiPanelController(make_config())
    c.on_state("AUTOPILOT ALTITUDE LOCK VAR", 99950)
    c.on_encoder(clockwise=True, now=0.0)
    assert c.values["AUTOPILOT ALTITUDE LOCK VAR"] == 99999


def test_rollover_wraps_heading():
    c = MultiPanelController(make_config())
    c.on_selector(3)
    c.on_state("AUTOPILOT HEADING LOCK DIR", 359)
    assert c.on_encoder(clockwise=True, now=0.0) == [SendEvent(name="HEADING_BUG_SET", data=0)]
    c.on_state("AUTOPILOT HEADING LOCK DIR", 0)
    assert c.on_encoder(clockwise=False, now=10.0) == [SendEvent(name="HEADING_BUG_SET", data=359)]


def test_on_event_routes_selector_and_encoder():
    c = MultiPanelController(make_config())
    c.on_state("AUTOPILOT HEADING LOCK DIR", 90)
    # selector to HDG (code 3); enter edge only
    assert c.on_event(code=3, value=1, now=0.0) == []
    assert c.selector == 3
    # encoder CW tick
    assert c.on_event(code=ENCODER_CW, value=1, now=1.0) == [
        SendEvent(name="HEADING_BUG_SET", data=91)
    ]
    # release edges ignored
    assert c.on_event(code=ENCODER_CCW, value=0, now=2.0) == []


def test_render_shows_selected_value_top_row():
    c = MultiPanelController(make_config())
    c.on_selector(3)  # HDG
    c.on_state("AUTOPILOT HEADING LOCK DIR", 90)
    report = c.render()
    assert report[0] == 0x00  # report id
    assert list(report[1:6]) == [BLANK, BLANK, BLANK, 9, 0]  # top row "  90"
    assert list(report[6:11]) == [BLANK] * 5  # bottom row blank


def test_render_led_byte_reflects_ap_and_mode():
    c = MultiPanelController(make_config())
    c.on_state("AUTOPILOT MASTER", 1)
    c.on_state("L:AUTOPILOT_MODE", 2)  # HDG mode -> bit 1
    led = c.render()[11]
    assert led == (1 << 0) | (1 << 1)  # AP + HDG


def test_render_minus_for_negative_value():
    cfg = MultiPanelOutput(
        selector=[
            SelectorEntry(
                code=1, label="VS", simvar="AUTOPILOT VERTICAL HOLD VAR",
                set_event="AP_VS_VAR_SET_ENGLISH", step=100, fast_step=1000,
                min=-9999, max=9999,
            )
        ],
    )
    c = MultiPanelController(cfg)
    c.on_state("AUTOPILOT VERTICAL HOLD VAR", -500)
    assert list(c.render()[1:6]) == [BLANK, MINUS, 5, 0, 0]
