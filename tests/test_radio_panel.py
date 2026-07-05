from msfs_peripherals_bridge.mapping.display import BLANK, DOT
from msfs_peripherals_bridge.mapping.radio_panel import RadioPanelController
from msfs_peripherals_bridge.models import RadioBank, RadioPanelOutput, RadioUnit
from msfs_peripherals_bridge.simconnect.protocol import SendEvent


def _com1() -> RadioBank:
    return RadioBank(
        code=0, label="COM1", fine_view=True,
        active="COM ACTIVE FREQUENCY:1", standby="COM STANDBY FREQUENCY:1",
        swap_event="COM1_RADIO_SWAP",
        whole_inc="COM_RADIO_WHOLE_INC", whole_dec="COM_RADIO_WHOLE_DEC",
        fract_inc="COM_RADIO_FRACT_INC", fract_dec="COM_RADIO_FRACT_DEC",
        fract_fast_inc="COM_RADIO_25_INC", fract_fast_dec="COM_RADIO_25_DEC",
    )


def _nav1() -> RadioBank:
    # NAV has no 8.33 distinction -> no fast events (fine == coarse).
    return RadioBank(
        code=1, label="NAV1",
        active="NAV ACTIVE FREQUENCY:1", standby="NAV STANDBY FREQUENCY:1",
        swap_event="NAV1_RADIO_SWAP",
        whole_inc="NAV1_RADIO_WHOLE_INC", whole_dec="NAV1_RADIO_WHOLE_DEC",
        fract_inc="NAV1_RADIO_FRACT_INC", fract_dec="NAV1_RADIO_FRACT_DEC",
    )


def _upper() -> RadioUnit:
    return RadioUnit(
        name="upper", row="upper", banks=[_com1(), _nav1()],
        outer_cw=5, outer_ccw=6, inner_cw=7, inner_ccw=8, swap=9,
    )


def _lower() -> RadioUnit:
    return RadioUnit(
        name="lower", row="lower",
        banks=[
            RadioBank(
                code=10, label="COM2",
                active="COM ACTIVE FREQUENCY:2", standby="COM STANDBY FREQUENCY:2",
                swap_event="COM2_RADIO_SWAP",
                whole_inc="COM2_RADIO_WHOLE_INC", whole_dec="COM2_RADIO_WHOLE_DEC",
                fract_inc="COM2_RADIO_FRACT_INC", fract_dec="COM2_RADIO_FRACT_DEC",
            ),
        ],
        outer_cw=15, outer_ccw=16, inner_cw=17, inner_ccw=18, swap=19,
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
        "COM ACTIVE FREQUENCY:1", "COM STANDBY FREQUENCY:1",
        "NAV ACTIVE FREQUENCY:1", "NAV STANDBY FREQUENCY:1",
        "COM ACTIVE FREQUENCY:2", "COM STANDBY FREQUENCY:2",
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
