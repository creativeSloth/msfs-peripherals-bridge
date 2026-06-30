from msfs_peripherals_bridge.models import GearLedOutput
from msfs_peripherals_bridge.outputs import OutputManager
from msfs_peripherals_bridge.simconnect.protocol import Subscribe

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
