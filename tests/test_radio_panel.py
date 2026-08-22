from msfs_peripherals_bridge.mapping.display import BLANK, DOT
from msfs_peripherals_bridge.mapping.radio_panel import (
    RadioPanelController,
    _squawk_step_digit,
)
from msfs_peripherals_bridge.models import (
    AdfBank,
    DmeBank,
    DmeSource,
    RadioBank,
    RadioPanelOutput,
    RadioUnit,
    XpdrBank,
)
from msfs_peripherals_bridge.simconnect.protocol import SendEvent, SetSimVar


def _com1() -> RadioBank:
    return RadioBank(
        code=0,
        label="COM1",
        fine_view=True,
        active="COM ACTIVE FREQUENCY:1",
        standby="COM STANDBY FREQUENCY:1",
        swap_event="COM1_RADIO_SWAP",
        whole_inc="COM_RADIO_WHOLE_INC",
        whole_dec="COM_RADIO_WHOLE_DEC",
        fract_inc="COM_RADIO_FRACT_INC",
        fract_dec="COM_RADIO_FRACT_DEC",
        fract_fast_inc="COM_RADIO_25_INC",
        fract_fast_dec="COM_RADIO_25_DEC",
    )


def _nav1() -> RadioBank:
    # NAV has no 8.33 distinction -> no fast events (fine == coarse).
    return RadioBank(
        code=1,
        label="NAV1",
        active="NAV ACTIVE FREQUENCY:1",
        standby="NAV STANDBY FREQUENCY:1",
        swap_event="NAV1_RADIO_SWAP",
        whole_inc="NAV1_RADIO_WHOLE_INC",
        whole_dec="NAV1_RADIO_WHOLE_DEC",
        fract_inc="NAV1_RADIO_FRACT_INC",
        fract_dec="NAV1_RADIO_FRACT_DEC",
    )


def _dme() -> DmeBank:
    return DmeBank(
        code=2,
        sources=[
            DmeSource(label="1", distance="NAV DME:1", speed="NAV DMESPEED:1"),
            DmeSource(label="2", distance="NAV DME:2", speed="NAV DMESPEED:2"),
        ],
    )


def _upper() -> RadioUnit:
    return RadioUnit(
        name="upper",
        row="upper",
        banks=[_com1(), _nav1(), _dme(), XpdrBank(code=3), AdfBank(code=4)],
        outer_cw=5,
        outer_ccw=6,
        inner_cw=7,
        inner_ccw=8,
        swap=9,
    )


def _lower() -> RadioUnit:
    return RadioUnit(
        name="lower",
        row="lower",
        banks=[
            RadioBank(
                code=10,
                label="COM2",
                active="COM ACTIVE FREQUENCY:2",
                standby="COM STANDBY FREQUENCY:2",
                swap_event="COM2_RADIO_SWAP",
                whole_inc="COM2_RADIO_WHOLE_INC",
                whole_dec="COM2_RADIO_WHOLE_DEC",
                fract_inc="COM2_RADIO_FRACT_INC",
                fract_dec="COM2_RADIO_FRACT_DEC",
            ),
        ],
        outer_cw=15,
        outer_ccw=16,
        inner_cw=17,
        inner_ccw=18,
        swap=19,
    )


def make_config() -> RadioPanelOutput:
    return RadioPanelOutput(units=[_upper(), _lower()])


def test_default_selection_is_first_bank():
    c = RadioPanelController(make_config())
    assert c.consumes(0) and c.consumes(15)
    assert not c.consumes(99)


def test_subscriptions_cover_active_and_standby_of_all_banks():
    subs = set(RadioPanelController(make_config()).subscriptions())
    assert {
        "COM ACTIVE FREQUENCY:1",
        "COM STANDBY FREQUENCY:1",
        "NAV ACTIVE FREQUENCY:1",
        "NAV STANDBY FREQUENCY:1",
        "COM ACTIVE FREQUENCY:2",
        "COM STANDBY FREQUENCY:2",
    } <= subs


def test_selector_only_repoints_no_command():
    c = RadioPanelController(make_config())
    assert c.on_event(code=1, value=1) == []  # upper -> NAV1
    # now the encoders act on NAV1
    assert c.on_event(code=5, value=1) == [SendEvent(name="NAV1_RADIO_WHOLE_INC")]


def test_release_edges_ignored():
    c = RadioPanelController(make_config())
    assert c.on_event(code=5, value=0) == []


def test_outer_encoder_fires_whole_events():
    c = RadioPanelController(make_config())
    assert c.on_event(code=5, value=1) == [SendEvent(name="COM_RADIO_WHOLE_INC")]
    assert c.on_event(code=6, value=1) == [SendEvent(name="COM_RADIO_WHOLE_DEC")]


def test_inner_encoder_fine_fires_fract_events():
    c = RadioPanelController(make_config())
    assert c.on_event(code=7, value=1) == [SendEvent(name="COM_RADIO_FRACT_INC")]
    assert c.on_event(code=8, value=1) == [SendEvent(name="COM_RADIO_FRACT_DEC")]


def test_swap_button_fires_swap_event():
    c = RadioPanelController(make_config())
    assert c.on_event(code=9, value=1) == [SendEvent(name="COM1_RADIO_SWAP")]


def test_inner_knob_always_fires_fine_step():
    # Acceleration removed 2026-07-05 (isolating encoder bounce): a fast inner spin
    # no longer switches to a coarse fract_fast_* event — every detent is the fine
    # 8.33 kHz step, regardless of spin speed.
    t = [0.0]
    c = RadioPanelController(make_config(), clock=lambda: t[0])
    fine = SendEvent(name="COM_RADIO_FRACT_INC")
    for _ in range(6):  # even a sustained fast spin stays fine
        assert c.on_event(code=7, value=1) == [fine]
        t[0] += 0.02


def test_nav_without_fast_events_stays_fine_when_spun_fast():
    t = [0.0]
    c = RadioPanelController(make_config(), clock=lambda: t[0])
    c.on_event(code=1, value=1)  # select NAV1 (no fract_fast_*)
    fine = SendEvent(name="NAV1_RADIO_FRACT_INC")
    for _ in range(6):  # even a sustained fast spin has no coarse event to switch to
        assert c.on_event(code=7, value=1) == [fine]
        t[0] += 0.02


def test_render_active_coarse_standby_follows_view():
    c = RadioPanelController(make_config())
    c.on_state("COM ACTIVE FREQUENCY:1", 118.00)
    c.on_state("COM STANDBY FREQUENCY:1", 118.30)
    report = c.render()
    assert len(report) == 23  # report id + 20 cells + 2 flag bytes
    assert report[0] == 0x00
    # coarse view (default): both rows NNN.NN
    assert list(report[1:6]) == [1, 1, 8 + DOT, 0, 0]  # active 118.00
    assert list(report[6:11]) == [1, 1, 8 + DOT, 3, 0]  # standby 118.30
    # turning the inner (fine) knob shifts only the tuned standby row to NN.NNN
    c.on_event(code=7, value=1)
    report = c.render()
    assert list(report[1:6]) == [1, 1, 8 + DOT, 0, 0]  # active stays coarse
    assert list(report[6:11]) == [1, 8 + DOT, 3, 0, 0]  # standby 18.300
    # the coarse knob shifts it back
    c.on_event(code=5, value=1)
    assert list(c.render()[6:11]) == [1, 1, 8 + DOT, 3, 0]


def test_nav_inner_knob_keeps_coarse_view():
    # NAV steps 50 kHz (third decimal always 0), so its bank has fine_view=False:
    # the inner knob still tunes but the standby row must NOT shift to NN.NNN.
    c = RadioPanelController(make_config())
    c.on_event(code=1, value=1)  # upper -> NAV1 (fine_view defaults False)
    c.on_state("NAV STANDBY FREQUENCY:1", 110.50)
    coarse = [1, 1, 0 + DOT, 5, 0]  # 110.50
    assert list(c.render()[6:11]) == coarse
    assert c.on_event(code=7, value=1) == [SendEvent(name="NAV1_RADIO_FRACT_INC")]
    assert list(c.render()[6:11]) == coarse  # still NNN.NN, no fine shift


def test_selector_move_resets_fine_view():
    # fine-tune COM1 (view shifts), then select NAV1: the view resets to coarse so
    # the new bank isn't stuck showing NN.NNN carried over from the previous one.
    c = RadioPanelController(make_config())
    c.on_state("COM STANDBY FREQUENCY:1", 118.30)
    c.on_event(code=7, value=1)  # COM1 inner -> fine view
    assert list(c.render()[6:11]) == [1, 8 + DOT, 3, 0, 0]  # 18.300 fine
    c.on_event(code=1, value=1)  # select NAV1 -> resets to coarse
    c.on_state("NAV STANDBY FREQUENCY:1", 110.50)
    assert list(c.render()[6:11]) == [1, 1, 0 + DOT, 5, 0]  # 110.50 coarse


def test_render_places_units_in_upper_and_lower_halves():
    c = RadioPanelController(make_config())
    c.on_state("COM STANDBY FREQUENCY:2", 121.90)
    report = c.render()
    assert list(report[1:11]) == [BLANK] * 10  # upper: no freqs yet -> blank
    assert list(report[11:16]) == [BLANK] * 5  # lower active unknown -> blank
    assert list(report[16:21]) == [1, 2, 1 + DOT, 9, 0]  # lower standby 121.90


def test_render_all_blank_without_state():
    report = RadioPanelController(make_config()).render()
    assert list(report[1:21]) == [BLANK] * 20
    assert list(report[21:23]) == [0x00, 0x00]


def _powered_config() -> RadioPanelOutput:
    return make_config().model_copy(update={"power": "ELECTRICAL MASTER BATTERY"})


def test_power_gate_in_subscriptions():
    c = RadioPanelController(_powered_config())
    assert "ELECTRICAL MASTER BATTERY" in c.subscriptions()


def test_render_blank_when_battery_off():
    c = RadioPanelController(_powered_config())
    c.on_state("COM STANDBY FREQUENCY:2", 121.90)  # would show on lower standby
    # Battery unknown -> dark; then explicitly off -> still dark.
    assert list(c.render()[1:21]) == [BLANK] * 20
    c.on_state("ELECTRICAL MASTER BATTERY", 0)
    assert list(c.render()[1:21]) == [BLANK] * 20


def test_render_lit_when_battery_on():
    c = RadioPanelController(_powered_config())
    c.on_state("COM STANDBY FREQUENCY:2", 121.90)
    c.on_state("ELECTRICAL MASTER BATTERY", 1)
    assert list(c.render()[16:21]) == [1, 2, 1 + DOT, 9, 0]  # lower standby 121.90


def test_encoder_is_never_debounced():
    # Measured 2026-07-05: the encoders don't bounce (8 ms USB poll floors any
    # repeat at 16 ms), so no time guard applies — even two detents at the same
    # instant both fire. Only the swap button is debounced.
    t = [0.0]
    c = RadioPanelController(make_config(), clock=lambda: t[0])
    inc = SendEvent(name="COM_RADIO_FRACT_INC")
    assert c.on_event(code=7, value=1) == [inc]
    assert c.on_event(code=7, value=1) == [inc]  # no clock advance -> still fires


def test_refresh_after_names_the_tuned_var():
    c = RadioPanelController(make_config())
    # an inner/outer detent changes the selected bank's STANDBY -> re-read that
    assert c.refresh_after(7) == ["COM STANDBY FREQUENCY:1"]  # inner cw
    assert c.refresh_after(5) == ["COM STANDBY FREQUENCY:1"]  # outer cw
    # a swap flips both rows -> re-read both
    assert c.refresh_after(9) == ["COM ACTIVE FREQUENCY:1", "COM STANDBY FREQUENCY:1"]
    # selector moves and unknown codes change nothing
    assert c.refresh_after(0) == []  # selector
    assert c.refresh_after(999) == []


def test_swap_mirrors_active_and_standby_locally():
    c = RadioPanelController(make_config())
    c.on_state("COM ACTIVE FREQUENCY:1", 118.00)
    c.on_state("COM STANDBY FREQUENCY:1", 121.30)
    assert c.on_event(code=9, value=1) == [SendEvent(name="COM1_RADIO_SWAP")]
    # the display flips instantly, before the sim confirms
    assert c.values["COM ACTIVE FREQUENCY:1"] == 121.30
    assert c.values["COM STANDBY FREQUENCY:1"] == 118.00
    assert list(c.render()[1:6]) == [1, 2, 1 + DOT, 3, 0]  # active now 121.30


def test_swap_bounce_within_window_dropped():
    t = [0.0]
    c = RadioPanelController(make_config(), clock=lambda: t[0])
    swap = SendEvent(name="COM1_RADIO_SWAP")
    assert c.on_event(code=9, value=1) == [swap]
    t[0] += 0.05  # button bounce, < _SWAP_DEBOUNCE (200 ms) -> swallowed
    assert c.on_event(code=9, value=1) == []
    t[0] += 0.30  # deliberate second swap -> fires
    assert c.on_event(code=9, value=1) == [swap]


def test_selector_not_debounced():
    t = [0.0]
    c = RadioPanelController(make_config(), clock=lambda: t[0])
    # a selector re-point is idempotent; back-to-back moves must always apply,
    # so selecting COM1 right after NAV1 (no clock advance) must still take effect.
    assert c.on_event(code=1, value=1) == []  # upper -> NAV1
    assert c.on_event(code=0, value=1) == []  # upper -> COM1 (not dropped as bounce)
    assert c.on_event(code=5, value=1) == [SendEvent(name="COM_RADIO_WHOLE_INC")]


# -- DME position (display-only, NAV1<->NAV2 source cycle) --------------------


def test_dme_renders_distance_over_nav_and_speed():
    c = RadioPanelController(make_config())
    c.on_event(code=2, value=1)  # upper -> DME
    c.on_state("NAV DME:1", 12.3)
    c.on_state("NAV DMESPEED:1", 180)
    report = c.render()
    assert list(report[1:6]) == [BLANK, BLANK, 1, 2 + DOT, 3]  # top: distance 12.3
    assert list(report[6:11]) == [1, BLANK, 1, 8, 0]  # bottom: nav 1, GS 180


def test_dme_swap_cycles_nav_source():
    c = RadioPanelController(make_config())
    c.on_event(code=2, value=1)  # DME
    c.on_state("NAV DME:1", 12.3)
    c.on_state("NAV DME:2", 5.0)
    c.on_state("NAV DMESPEED:1", 180)
    c.on_state("NAV DMESPEED:2", 90)
    assert list(c.render()[1:6]) == [BLANK, BLANK, 1, 2 + DOT, 3]  # NAV1 12.3
    assert c.on_event(code=9, value=1) == []  # push cycles source, no sim command
    assert list(c.render()[1:6]) == [BLANK, BLANK, BLANK, 5 + DOT, 0]  # NAV2 5.0
    assert list(c.render()[6:11]) == [2, BLANK, BLANK, 9, 0]  # nav 2, GS 90


def test_dme_encoders_are_inert():
    c = RadioPanelController(make_config())
    c.on_event(code=2, value=1)  # DME
    assert c.on_event(code=7, value=1) == []  # inner: nothing
    assert c.on_event(code=5, value=1) == []  # outer: nothing
    assert c.refresh_after(9) == []  # swap on DME: nothing to ReadNow


def test_dme_simvars_are_subscribed():
    names = set(make_config().simvars())
    assert {"NAV DME:1", "NAV DMESPEED:1", "NAV DME:2", "NAV DMESPEED:2"} <= names


def _dme_bidir_config() -> RadioPanelOutput:
    """Config whose upper DME (code 2) is backed by a source_var (bidirectional)."""
    dme = DmeBank(
        code=2,
        source_var="L:DME_SRC",
        sources=[
            DmeSource(label="1", distance="NAV DME:1", speed="NAV DMESPEED:1"),
            DmeSource(label="2", distance="NAV DME:2", speed="NAV DMESPEED:2"),
        ],
    )
    return RadioPanelOutput(
        units=[
            RadioUnit(
                name="upper",
                row="upper",
                banks=[_com1(), dme],
                outer_cw=5,
                outer_ccw=6,
                inner_cw=7,
                inner_ccw=8,
                swap=9,
            )
        ]
    )


def test_dme_source_var_drives_display():
    # The shown source follows the cockpit switch var (so a cockpit flip drives us).
    c = RadioPanelController(_dme_bidir_config())
    c.on_event(code=2, value=1)  # DME
    c.on_state("NAV DME:1", 12.3)
    c.on_state("NAV DME:2", 5.0)
    c.on_state("NAV DMESPEED:2", 90)
    c.on_state("L:DME_SRC", 1)  # cockpit switch -> NAV2
    assert list(c.render()[1:6]) == [BLANK, BLANK, BLANK, 5 + DOT, 0]  # NAV2 5.0
    assert list(c.render()[6:11]) == [2, BLANK, BLANK, 9, 0]  # nav index 2
    c.on_state("L:DME_SRC", 0)  # cockpit switch -> NAV1
    assert list(c.render()[1:6]) == [BLANK, BLANK, 1, 2 + DOT, 3]  # NAV1 12.3


def test_dme_push_writes_source_var():
    # The push flips the source var (so the panel drives the cockpit switch).
    t = [0.0]
    c = RadioPanelController(_dme_bidir_config(), clock=lambda: t[0])
    c.on_event(code=2, value=1)  # DME
    c.on_state("L:DME_SRC", 0)
    assert c.on_event(code=9, value=1) == [SetSimVar(name="L:DME_SRC", unit="number", value=1)]
    t[0] += 1.0  # past the swap-debounce window
    # locally echoed to 1; the next push flips back to 0
    assert c.on_event(code=9, value=1) == [SetSimVar(name="L:DME_SRC", unit="number", value=0)]


def test_dme_source_var_subscribed():
    assert "L:DME_SRC" in _dme_bidir_config().simvars()


# -- XPDR position (mode-less squawk edit) -----------------------------------


def test_squawk_step_digit_wraps_octal_per_digit():
    assert _squawk_step_digit(0x1200, 3, 1) == 0x1201  # ones +1
    assert _squawk_step_digit(0x1207, 3, 1) == 0x1200  # ones wrap 7->0, no carry
    assert _squawk_step_digit(0x1200, 0, 1) == 0x2200  # thousands +1
    assert _squawk_step_digit(0x7200, 0, 1) == 0x0200  # thousands wrap 7->0
    assert _squawk_step_digit(0x1200, 1, -1) == 0x1100  # hundreds -1


def test_xpdr_inner_steps_cursor_digit_and_sets_and_echoes():
    c = RadioPanelController(make_config())
    c.on_event(code=3, value=1)  # upper -> XPDR (cursor starts at leftmost digit)
    c.on_state("TRANSPONDER CODE:1", 0x1200)
    assert c.on_event(code=7, value=1) == [SendEvent(name="XPNDR_SET", data=0x2200)]
    assert list(c.render()[1:6]) == [BLANK, 2 + DOT, 2, 0, 0]  # echo 2200, dot leftmost


def test_xpdr_push_walks_the_cursor_and_moves_the_dot():
    c = RadioPanelController(make_config())
    c.on_event(code=3, value=1)
    c.on_state("TRANSPONDER CODE:1", 0x1200)
    assert c.on_event(code=9, value=1) == []  # push -> cursor to 2nd digit, no command
    assert list(c.render()[1:6]) == [BLANK, 1, 2 + DOT, 0, 0]  # dot moved right
    # inner knob now edits the 2nd digit (hundreds)
    assert c.on_event(code=7, value=1) == [SendEvent(name="XPNDR_SET", data=0x1300)]


def test_xpdr_outer_knob_is_unused():
    c = RadioPanelController(make_config())
    c.on_event(code=3, value=1)
    c.on_state("TRANSPONDER CODE:1", 0x1200)
    assert c.on_event(code=5, value=1) == []  # outer knob does nothing on XPDR
    assert c.on_event(code=6, value=1) == []


def test_xpdr_render_preserves_leading_zeros():
    c = RadioPanelController(make_config())
    c.on_event(code=3, value=1)
    c.on_state("TRANSPONDER CODE:1", 0x0021)
    assert list(c.render()[1:6]) == [BLANK, 0 + DOT, 0, 2, 1]  # 0021 + cursor dot


def test_xpdr_cursor_wraps_after_four_pushes():
    t = [0.0]
    c = RadioPanelController(make_config(), clock=lambda: t[0])
    c.on_event(code=3, value=1)
    c.on_state("TRANSPONDER CODE:1", 0x1200)
    for _ in range(4):
        t[0] += 0.30  # clear the swap debounce between deliberate pushes
        c.on_event(code=9, value=1)  # four pushes -> back to leftmost
    assert list(c.render()[1:6]) == [BLANK, 1 + DOT, 2, 0, 0]
    assert c.refresh_after(7) == []  # local-echoed -> no ReadNow


def test_xpdr_code_var_subscribed():
    assert "TRANSPONDER CODE:1" in make_config().simvars()


# -- ADF position (KR-85 digit-pair kHz edit) --------------------------------

# KR-85 counters: F_kHz = (dig1+1)*100 + dig2*10 + dig3.
_D1, _D2, _D3 = "L:KR85_dig1_counter", "L:KR85_dig2_counter", "L:KR85_dig3_counter"


def _adf_set(c: RadioPanelController, khz: int) -> None:
    """Seed the three KR-85 counters so the ADF reads ``khz``."""
    c.on_state(_D1, khz // 100 - 1)
    c.on_state(_D2, (khz // 10) % 10)
    c.on_state(_D3, khz % 10)


def test_adf_displays_khz_with_dots_on_high_pair():
    c = RadioPanelController(make_config())
    c.on_event(code=4, value=1)  # upper -> ADF (cursor starts on high pair)
    _adf_set(c, 350)
    assert list(c.render()[1:6]) == [BLANK, 0 + DOT, 3 + DOT, 5, 0]  # 0350, high dots


def test_adf_inner_steps_right_digit_of_pair_and_echoes():
    c = RadioPanelController(make_config())
    c.on_event(code=4, value=1)
    _adf_set(c, 350)  # dig1=2
    # inner cw -> right digit of the high pair = hundreds: 350 -> 450 (only dig1 changes)
    cmd = c.on_event(code=7, value=1)
    assert cmd == [SetSimVar(name=_D1, unit="number", value=3)]
    assert list(c.render()[1:6]) == [BLANK, 0 + DOT, 4 + DOT, 5, 0]


def test_adf_outer_steps_left_digit_of_pair():
    c = RadioPanelController(make_config())
    c.on_event(code=4, value=1)
    _adf_set(c, 350)  # dig1=2
    # outer cw -> left digit of the high pair = thousands: 350 -> 1350 (dig1 2->12)
    assert c.on_event(code=5, value=1) == [SetSimVar(name=_D1, unit="number", value=12)]


def test_adf_push_toggles_pair_and_moves_dots():
    t = [0.0]
    c = RadioPanelController(make_config(), clock=lambda: t[0])
    c.on_event(code=4, value=1)
    _adf_set(c, 350)  # dig3=0
    c.on_event(code=9, value=1)  # push -> low pair
    assert list(c.render()[1:6]) == [BLANK, 0, 3, 5 + DOT, 0 + DOT]  # dots on low pair
    # inner now edits the low pair's right digit = ones: 350 -> 351 (only dig3 changes)
    assert c.on_event(code=7, value=1) == [SetSimVar(name=_D3, unit="number", value=1)]


def test_adf_thousands_digit_wraps_0_1_at_ceiling():
    c = RadioPanelController(make_config())
    c.on_event(code=4, value=1)
    _adf_set(c, 1799)  # thousands = 1 (max), dig1=16
    # thousands wraps 1 -> 0 (0..1 only), the other digits untouched -> 0799 (dig1 16->6)
    assert c.on_event(code=5, value=1) == [SetSimVar(name=_D1, unit="number", value=6)]


def test_adf_hundreds_wraps_at_7_without_touching_low_digits():
    # Regression: the old whole-value clamp stuck hundreds at 7 and slammed the
    # tens/ones to 9. Now the hundreds digit wraps 0..7 (thousands=1) on its own.
    c = RadioPanelController(make_config())
    c.on_event(code=4, value=1)
    _adf_set(c, 1750)  # 1,7,5,0 -> dig1=16
    # inner cw = hundreds +1: 7 wraps to 0, tens/ones stay 5/0 -> 1050 (dig1 16->9)
    assert c.on_event(code=7, value=1) == [SetSimVar(name=_D1, unit="number", value=9)]


def test_adf_hundreds_reaches_8_9_when_thousands_zero():
    # With thousands = 0 the whole value stays <= 1799, so hundreds spans 0..9
    # (800-999 kHz must be dialable).
    c = RadioPanelController(make_config())
    c.on_event(code=4, value=1)
    _adf_set(c, 750)  # 0,7,5,0 -> dig1=6
    # hundreds 7 -> 8 -> 850 (dig1 6->7)
    assert c.on_event(code=7, value=1) == [SetSimVar(name=_D1, unit="number", value=7)]


def test_adf_freq_vars_subscribed():
    subs = make_config().simvars()
    assert _D1 in subs and _D2 in subs and _D3 in subs


# -- XPDR barometer (outer knob = QNH on the bottom row) ----------------------


def _xpdr_baro_config() -> RadioPanelOutput:
    return RadioPanelOutput(
        units=[
            RadioUnit(
                name="u",
                row="upper",
                banks=[XpdrBank(code=3, baro_var="KOHLSMAN SETTING HG")],
                outer_cw=5,
                outer_ccw=6,
                inner_cw=7,
                inner_ccw=8,
                swap=9,
            )
        ]
    )


def test_xpdr_outer_knob_fires_baro_events():
    c = RadioPanelController(_xpdr_baro_config())
    c.on_event(code=3, value=1)  # -> XPDR
    assert c.on_event(code=5, value=1) == [SendEvent(name="KOHLSMAN_INC")]  # outer cw
    assert c.on_event(code=6, value=1) == [SendEvent(name="KOHLSMAN_DEC")]  # outer ccw


def test_xpdr_baro_renders_inhg_with_dot_on_second_digit():
    c = RadioPanelController(_xpdr_baro_config())
    c.on_event(code=3, value=1)
    c.on_state("TRANSPONDER CODE:1", 0x1200)
    c.on_state("KOHLSMAN SETTING HG", 29.92)
    assert list(c.render()[6:11]) == [BLANK, 2, 9 + DOT, 9, 2]  # 29.92 on the bottom row


def test_xpdr_without_baro_leaves_outer_and_bottom_inert():
    c = RadioPanelController(make_config())  # XpdrBank(code=3) has no baro_var
    c.on_event(code=3, value=1)
    c.on_state("TRANSPONDER CODE:1", 0x1200)
    assert c.on_event(code=5, value=1) == []  # outer knob does nothing
    assert list(c.render()[6:11]) == [BLANK] * 5  # bottom row blank


def test_xpdr_baro_refreshes_off_cycle_but_squawk_does_not():
    c = RadioPanelController(_xpdr_baro_config())
    c.on_event(code=3, value=1)
    assert c.refresh_after(5) == ["KOHLSMAN SETTING HG"]  # outer knob -> ReadNow QNH
    assert c.refresh_after(7) == []  # inner knob (squawk) is local-echoed


def test_xpdr_baro_var_subscribed():
    assert "KOHLSMAN SETTING HG" in _xpdr_baro_config().simvars()
