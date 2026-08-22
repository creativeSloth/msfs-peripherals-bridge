"""Generic panel controller (Schritt E, LED slice) — pure + OutputManager wiring."""

from msfs_peripherals_bridge.mapping.generic_panel import GenericPanelController
from msfs_peripherals_bridge.models import GenericLed, GenericPanelOutput
from msfs_peripherals_bridge.outputs import OutputManager
from msfs_peripherals_bridge.simconnect.protocol import Subscribe


def _out(**kw):
    return GenericPanelOutput(
        leds=[
            GenericLed(name="A", var="VA", byte=0, bit=0),
            GenericLed(name="B", var="VB", byte=0, bit=3),
        ],
        length=1,
        **kw,
    )


class FakeDispatcher:
    def __init__(self):
        self.sent = []

    def send(self, command):
        self.sent.append(command)

    def states(self):  # pragma: no cover
        return iter(())


def test_render_sets_only_lit_bits():
    c = GenericPanelController(_out())
    assert c.render() == bytes([0x00, 0x00])  # nothing seen yet
    c.on_state("VA", 1)
    assert c.render() == bytes([0x00, 0b0000_0001])  # bit 0
    c.on_state("VB", 1)
    assert c.render() == bytes([0x00, 0b0000_1001])  # bits 0 + 3
    c.on_state("VA", 0)
    assert c.render() == bytes([0x00, 0b0000_1000])  # only bit 3 now


def test_threshold_and_nonnumeric():
    c = GenericPanelController(
        GenericPanelOutput(leds=[GenericLed(var="V", byte=0, bit=1, on_at=0.5)], length=1)
    )
    c.on_state("V", 0.4)
    assert c.render() == bytes([0x00, 0x00])  # below threshold
    c.on_state("V", 0.6)
    assert c.render() == bytes([0x00, 0b10])
    c.on_state("V", "n/a")  # non-numeric -> treated as unknown -> off
    assert c.render() == bytes([0x00, 0x00])


def test_power_gate_blanks_everything():
    c = GenericPanelController(_out(power="PWR"))
    c.on_state("VA", 1)
    c.on_state("VB", 1)
    assert c.render() == bytes([0x00, 0x00])  # no power yet -> dark
    c.on_state("PWR", 1)
    assert c.render() == bytes([0x00, 0b0000_1001])


def test_multibyte_report_length():
    c = GenericPanelController(
        GenericPanelOutput(leds=[GenericLed(var="X", byte=2, bit=5)], length=3)
    )
    c.on_state("X", 1)
    assert c.render() == bytes([0x00, 0x00, 0x00, 1 << 5])


def test_subscriptions_and_no_input_consumption():
    c = GenericPanelController(_out(power="PWR"))
    assert set(c.subscriptions()) == {"VA", "VB", "PWR"}
    assert c.consumes(5) is False
    assert c.on_event(5, 1) == []
    assert c.refresh_after(5) == []


def test_output_union_parses_generic_panel():
    from msfs_peripherals_bridge.models import Profile

    prof = Profile.model_validate(
        {
            "name": "p",
            "outputs": {
                "mypanel": [
                    {
                        "type": "generic_panel",
                        "length": 1,
                        "leds": [{"var": "V", "bit": 2}],
                    }
                ]
            },
        }
    )
    (o,) = prof.outputs["mypanel"]
    assert isinstance(o, GenericPanelOutput)
    assert o.leds[0].bit == 2


def test_output_manager_drives_generic_panel_end_to_end():
    writes = []
    dispatcher = FakeDispatcher()
    manager = OutputManager(
        {"mypanel": [_out(power="PWR")]},
        {"mypanel": "/dev/hidrawX"},
        dispatcher,
        writer=lambda path, report: writes.append((path, report)),
    )
    manager.subscribe_all()
    assert {c.name for c in dispatcher.sent if isinstance(c, Subscribe)} == {"VA", "VB", "PWR"}

    manager.on_state("PWR", 1)
    manager.on_state("VA", 1)
    assert writes[-1] == ("/dev/hidrawX", bytes([0x00, 0b0000_0001]))
    manager.on_state("VB", 1)
    assert writes[-1] == ("/dev/hidrawX", bytes([0x00, 0b0000_1001]))


def test_display_renders_integer_var_right_justified():
    from msfs_peripherals_bridge.mapping.display import BLANK
    from msfs_peripherals_bridge.models import GenericDisplay

    c = GenericPanelController(
        GenericPanelOutput(
            length=6, displays=[GenericDisplay(name="ALT", var="ALT", offset=0, cells=5)]
        )
    )
    # unknown value -> blank cells; the trailing spare byte stays 0
    assert c.render() == bytes([0x00, BLANK, BLANK, BLANK, BLANK, BLANK, 0x00])
    c.on_state("ALT", 123)
    assert c.render() == bytes([0x00, BLANK, BLANK, 1, 2, 3, 0x00])


def test_display_decimals_add_trailing_dot():
    from msfs_peripherals_bridge.mapping.display import BLANK, DOT
    from msfs_peripherals_bridge.models import GenericDisplay

    c = GenericPanelController(
        GenericPanelOutput(
            length=5, displays=[GenericDisplay(var="DME", offset=0, cells=5, decimals=1)]
        )
    )
    c.on_state("DME", 12.3)
    assert c.render() == bytes([0x00, BLANK, BLANK, 1, 2 + DOT, 3])  # "  12.3"


def test_display_and_led_share_report_and_power_and_subscriptions():
    from msfs_peripherals_bridge.mapping.display import BLANK
    from msfs_peripherals_bridge.models import GenericDisplay

    o = GenericPanelOutput(
        length=6,
        power="PWR",
        leds=[GenericLed(var="L", byte=5, bit=0)],
        displays=[GenericDisplay(var="N", offset=0, cells=5)],
    )
    c = GenericPanelController(o)
    assert set(c.subscriptions()) == {"L", "N", "PWR"}
    c.on_state("N", 7)
    c.on_state("L", 1)
    assert c.render() == bytes([0x00, BLANK, BLANK, BLANK, BLANK, BLANK, 0x00])  # no power
    c.on_state("PWR", 1)
    assert c.render() == bytes([0x00, BLANK, BLANK, BLANK, BLANK, 7, 1])  # N=7, LED bit0
