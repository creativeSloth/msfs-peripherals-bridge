from msfs_peripherals_bridge.mapping.display import DOT
from msfs_peripherals_bridge.mapping.multi_panel import ENCODER_CW
from msfs_peripherals_bridge.models import (
    AuxInput,
    GearLedOutput,
    MultiPanelOutput,
    RadioBank,
    RadioPanelOutput,
    RadioUnit,
    SelectorEntry,
    SelectorSource,
)
from msfs_peripherals_bridge.outputs import OutputManager
from msfs_peripherals_bridge.simconnect.protocol import ReadNow, SendEvent, Subscribe


def _fire_now(delay, fn):
    """Test scheduler: run the refresh synchronously for deterministic assertions."""
    fn()

NOSE_GREEN = 1 << 0
LEFT_GREEN = 1 << 1
RIGHT_GREEN = 1 << 2
LEFT_RED = 1 << 4


class FakeDispatcher:
    def __init__(self) -> None:
        self.sent: list[object] = []

    def send(self, command: object) -> None:
        self.sent.append(command)

    def states(self):  # pragma: no cover - not used in these unit tests
        return iter(())


def _manager(writer, power="ELECTRICAL MASTER BATTERY"):
    output = GearLedOutput(power=power)
    return OutputManager(
        {"switch_panel": [output]},
        {"switch_panel": "/dev/hidrawX"},
        FakeDispatcher(),
        writer=writer,
    )


def test_subscribes_to_every_needed_simvar():
    dispatcher = FakeDispatcher()
    manager = OutputManager(
        {"switch_panel": [GearLedOutput()]}, {"switch_panel": "/dev/hidrawX"}, dispatcher
    )
    manager.subscribe_all()
    subscribed = {c.name for c in dispatcher.sent if isinstance(c, Subscribe)}
    assert subscribed == {
        "GEAR CENTER POSITION",
        "GEAR LEFT POSITION",
        "GEAR RIGHT POSITION",
        "ELECTRICAL MASTER BATTERY",
    }


def test_writes_feature_report_on_state_change():
    writes: list[tuple[str, bytes]] = []
    manager = _manager(lambda path, report: writes.append((path, report)))

    manager.on_state("ELECTRICAL MASTER BATTERY", 1)
    manager.on_state("GEAR CENTER POSITION", 1.0)
    manager.on_state("GEAR LEFT POSITION", 1.0)
    manager.on_state("GEAR RIGHT POSITION", 1.0)

    assert writes[-1] == ("/dev/hidrawX", bytes([0x00, NOSE_GREEN | LEFT_GREEN | RIGHT_GREEN]))


def test_no_redundant_write_when_report_unchanged():
    writes: list[bytes] = []
    manager = _manager(lambda path, report: writes.append(report))

    manager.on_state("ELECTRICAL MASTER BATTERY", 1)
    manager.on_state("GEAR CENTER POSITION", 1.0)
    before = len(writes)
    # A second identical update for the nose wheel must not rewrite.
    manager.on_state("GEAR CENTER POSITION", 1.0)
    assert len(writes) == before


def test_battery_off_forces_all_leds_dark():
    writes: list[bytes] = []
    manager = _manager(lambda path, report: writes.append(report))

    manager.on_state("ELECTRICAL MASTER BATTERY", 1)
    manager.on_state("GEAR LEFT POSITION", 0.5)  # in transit -> red
    assert writes[-1] == bytes([0x00, LEFT_RED])
    manager.on_state("ELECTRICAL MASTER BATTERY", 0)  # power lost -> dark
    assert writes[-1] == bytes([0x00, 0x00])


def test_write_failure_is_swallowed_and_retried():
    attempts: list[bytes] = []

    def flaky(path, report):
        attempts.append(report)
        raise OSError("device busy")

    manager = _manager(flaky)
    manager.on_state("ELECTRICAL MASTER BATTERY", 1)
    manager.on_state("GEAR LEFT POSITION", 1.0)
    # Both updates attempted a write (failure did not cache the report).
    assert len(attempts) == 2


# --- Multi Panel controller routed through the OutputManager ---------------


def _multi_manager(writer):
    output = MultiPanelOutput(
        selector=[
            SelectorEntry(
                code=3, label="HDG", simvar="AUTOPILOT HEADING LOCK DIR",
                set_event="HEADING_BUG_SET", step=1,
                min=0, max=359, rollover=True,
            )
        ],
    )
    return OutputManager(
        {"multi_panel": [output]},
        {"multi_panel": "/dev/hidrawM"},
        FakeDispatcher(),
        writer=writer,
    )


def test_multi_subscribes_to_value_and_led_vars():
    dispatcher = FakeDispatcher()
    manager = OutputManager(
        {"multi_panel": [MultiPanelOutput(
            selector=[SelectorEntry(
                code=3, label="HDG", simvar="AUTOPILOT HEADING LOCK DIR",
                set_event="HEADING_BUG_SET", min=0, max=359,
            )],
        )]},
        {"multi_panel": "/dev/hidrawM"},
        dispatcher,
    )
    manager.subscribe_all()
    subscribed = {c.name for c in dispatcher.sent if isinstance(c, Subscribe)}
    assert subscribed == {"AUTOPILOT HEADING LOCK DIR", "AUTOPILOT MASTER", "L:AUTOPILOT_MODE"}


def test_handles_only_selector_encoder_codes():
    manager = _multi_manager(lambda p, r: None)
    assert manager.handles("multi_panel", ENCODER_CW) is True
    assert manager.handles("multi_panel", 3) is True  # selector position
    assert manager.handles("multi_panel", 7) is False  # AP button -> engine
    assert manager.handles("switch_panel", ENCODER_CW) is False  # no controller


def test_handle_input_encoder_emits_event_and_writes_display():
    writes: list[bytes] = []
    manager = _multi_manager(lambda path, report: writes.append(report))
    manager.on_state("AUTOPILOT HEADING LOCK DIR", 90)

    commands = manager.handle_input("multi_panel", ENCODER_CW, value=1)
    assert commands == [SendEvent(name="HEADING_BUG_SET", data=91)]
    # Display top row now shows "   91" (blank,blank,blank,9,1) after the bump.
    assert list(writes[-1][1:6]) == [0x0F, 0x0F, 0x0F, 9, 1]


def test_handle_input_release_edge_does_nothing():
    manager = _multi_manager(lambda p, r: None)
    manager.on_state("AUTOPILOT HEADING LOCK DIR", 90)
    assert manager.handle_input("multi_panel", ENCODER_CW, value=0) == []


def test_omni_mode_blinks_ias_led_on_tick():
    writes: list[bytes] = []
    manager = _multi_manager(lambda path, report: writes.append(report))
    manager.on_state("AUTOPILOT MASTER", 1)
    manager.on_state("L:AUTOPILOT_MODE", 1)  # OMNI
    nav, ias = 1 << 2, 1 << 3
    led = writes[-1][11]  # report = [id, 10 cells, led, spare]
    assert led & nav and led & ias  # NAV solid + IAS on (blink phase up)
    manager._blink_tick()  # flip phase -> IAS off, NAV stays
    led = writes[-1][11]
    assert led & nav and not led & ias
    manager._blink_tick()  # flip back -> IAS on again
    assert writes[-1][11] & ias


def _crs_manager(writer):
    output = MultiPanelOutput(
        selector=[
            SelectorEntry(
                code=4, label="CRS", simvar="NAV OBS:1", set_event="VOR1_SET",
                step=1, min=0, max=359, rollover=True,
                alt_sources=[SelectorSource(simvar="NAV OBS:2", set_event="VOR2_SET")],
            )
        ],
        source_toggle=AuxInput(device="yoke", code=291),
    )
    return OutputManager(
        {"multi_panel": [output]},
        {"multi_panel": "/dev/hidrawM"},
        FakeDispatcher(),
        writer=writer,
    )


def test_aux_toggle_routes_to_controller_and_rewrites_panel():
    writes: list[bytes] = []
    manager = _crs_manager(lambda path, report: writes.append(report))
    manager.on_state("NAV OBS:1", 90)
    manager.on_state("NAV OBS:2", 270)
    # The yoke button is claimed even though it lives on another device.
    assert manager.handles("yoke", 291) is True
    # Press flips CRS to source 2 -> top row shows [index 2][blank][270].
    assert manager.handle_input("yoke", 291, value=1) == []
    assert list(writes[-1][1:6]) == [2, 0x0F, 2, 7, 0]
    # Release edge does nothing.
    before = len(writes)
    assert manager.handle_input("yoke", 291, value=0) == []
    assert len(writes) == before


# --- Radio Panel controller routed through the OutputManager ----------------


def _radio_output() -> RadioPanelOutput:
    return RadioPanelOutput(
        units=[
            RadioUnit(
                name="upper", row="upper",
                outer_cw=14, outer_ccw=15, inner_cw=16, inner_ccw=17, swap=22,
                banks=[
                    RadioBank(
                        code=0, label="COM1", fine_view=True,
                        active="COM ACTIVE FREQUENCY:1", standby="COM STANDBY FREQUENCY:1",
                        swap_event="COM1_RADIO_SWAP",
                        whole_inc="COM_RADIO_WHOLE_INC", whole_dec="COM_RADIO_WHOLE_DEC",
                        fract_inc="COM_RADIO_FRACT_INC", fract_dec="COM_RADIO_FRACT_DEC",
                    ),
                ],
            ),
        ],
    )


def _radio_manager(writer):
    return OutputManager(
        {"radio_panel": [_radio_output()]},
        {"radio_panel": "/dev/hidrawR"},
        FakeDispatcher(),
        writer=writer,
    )


def test_radio_subscribes_to_frequency_vars():
    dispatcher = FakeDispatcher()
    manager = OutputManager(
        {"radio_panel": [_radio_output()]}, {"radio_panel": "/dev/hidrawR"}, dispatcher
    )
    manager.subscribe_all()
    subscribed = {c.name for c in dispatcher.sent if isinstance(c, Subscribe)}
    assert subscribed == {"COM ACTIVE FREQUENCY:1", "COM STANDBY FREQUENCY:1"}


def test_radio_handles_its_input_codes():
    manager = _radio_manager(lambda p, r: None)
    assert manager.handles("radio_panel", 0) is True  # selector COM1
    assert manager.handles("radio_panel", 16) is True  # inner encoder CW
    assert manager.handles("radio_panel", 22) is True  # ACT/STBY swap
    assert manager.handles("radio_panel", 99) is False  # not ours


def test_radio_outer_encoder_fires_event_and_writes_display():
    writes: list[bytes] = []
    manager = _radio_manager(lambda path, report: writes.append(report))
    manager.on_state("COM ACTIVE FREQUENCY:1", 118.00)
    manager.on_state("COM STANDBY FREQUENCY:1", 118.30)

    commands = manager.handle_input("radio_panel", 14, value=1)  # outer CW
    assert commands == [SendEvent(name="COM_RADIO_WHOLE_INC")]
    # 23-byte report; upper ACTIVE row (cells 0..4) shows 118.00.
    assert len(writes[-1]) == 23
    assert list(writes[-1][1:6]) == [1, 1, 8 + DOT, 0, 0]


def test_radio_inner_encoder_shifts_standby_to_fine_view():
    writes: list[bytes] = []
    manager = _radio_manager(lambda path, report: writes.append(report))
    manager.on_state("COM STANDBY FREQUENCY:1", 118.30)

    commands = manager.handle_input("radio_panel", 16, value=1)  # inner CW
    assert commands == [SendEvent(name="COM_RADIO_FRACT_INC")]
    # inner knob -> standby row (cells 5..9) shifts to the fine view 18.300
    assert list(writes[-1][6:11]) == [1, 8 + DOT, 3, 0, 0]


def _readnow_manager(dispatcher, schedule):
    return OutputManager(
        {"radio_panel": [_radio_output()]},
        {"radio_panel": "/dev/hidrawR"},
        dispatcher,
        writer=lambda p, r: None,
        schedule=schedule,
    )


def test_radio_encoder_schedules_readnow_of_tuned_var():
    dispatcher = FakeDispatcher()
    manager = _readnow_manager(dispatcher, _fire_now)
    manager.handle_input("radio_panel", 16, value=1)  # inner CW tunes standby
    reads = [c for c in dispatcher.sent if isinstance(c, ReadNow)]
    assert reads == [ReadNow("COM STANDBY FREQUENCY:1")]


def test_radio_swap_schedules_readnow_of_both_rows():
    dispatcher = FakeDispatcher()
    manager = _readnow_manager(dispatcher, _fire_now)
    manager.handle_input("radio_panel", 22, value=1)  # swap flips both rows
    reads = [c.name for c in dispatcher.sent if isinstance(c, ReadNow)]
    assert reads == ["COM ACTIVE FREQUENCY:1", "COM STANDBY FREQUENCY:1"]


def test_selector_move_schedules_no_readnow():
    dispatcher = FakeDispatcher()
    manager = _readnow_manager(dispatcher, _fire_now)
    manager.handle_input("radio_panel", 0, value=1)  # selector COM1: idempotent
    assert not [c for c in dispatcher.sent if isinstance(c, ReadNow)]


def test_detent_burst_coalesces_to_one_readnow():
    captured: list = []
    dispatcher = FakeDispatcher()
    manager = _readnow_manager(dispatcher, lambda delay, fn: captured.append(fn))
    for _ in range(3):  # three quick inner detents, each arms a timer
        manager.handle_input("radio_panel", 16, value=1)
    assert len(captured) == 3
    captured[0]()  # earlier (superseded) timers flush nothing
    captured[1]()
    assert not [c for c in dispatcher.sent if isinstance(c, ReadNow)]
    captured[2]()  # only the last-armed generation flushes, once
    reads = [c for c in dispatcher.sent if isinstance(c, ReadNow)]
    assert reads == [ReadNow("COM STANDBY FREQUENCY:1")]
