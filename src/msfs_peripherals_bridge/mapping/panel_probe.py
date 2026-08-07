"""Build *isolated* feature-report buffers to identify one physical panel element.

The GUI's output editor offers a 🔦 "test send" per element: it writes a report
that lights ONLY that element so the user can see, on the real hardware, which
LED / display cell a field maps to (the same idea as ``tools/panel-scan/out_*``,
but per element and driven from the GUI).

Everything here is pure (bytes in, bytes out) so it is unit-tested without
hardware. The buffers are the full feature report **including the leading
report-id byte**, ready for :func:`devices.hidraw_reader.write_feature_report`.

Report layouts (report id 0, then data bytes):

* switch panel — 1 byte: the gear-LED bitmask (see :mod:`.leds`).
* multi panel  — 12 bytes: 10 display cells, 1 LED byte, 1 spare.
* radio panel  — 22 bytes: 20 display cells, 2 flag bytes.

A cell shows digit ``8`` (all seven segments lit → unmistakable); ``dot=True``
adds the trailing decimal point (``+DOT``), the same mechanism the frequency
display uses, so the user can also locate each cell's decimal point.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..models import GearLedOutput, MultiPanelOutput, Output, RadioPanelOutput
from .display import BLANK, DOT, ROW_WIDTH
from .leds import MULTI_BUTTON_ORDER, gear_led_byte, multi_button_led_byte

_REPORT_ID = 0x00
# "8" lights every segment of a 7-segment cell — the clearest identify glyph.
TEST_GLYPH = 8
_MULTI_CELLS = ROW_WIDTH * 2  # 10: two display rows of five
_RADIO_CELLS = ROW_WIDTH * 4  # 20: two units x (active + standby)
_FLAG_BYTES = (0x00, 0x00)  # radio trailing flags; 0x00 leaves the display lit

# Physical wheel order of the switch-panel gear LEDs (matches leds._WHEEL_BITS).
_WHEELS = ("nose", "left", "right")
_WHEEL_LABEL = {"nose": "Bugrad", "left": "links", "right": "rechts"}
_MULTI_LED_LABEL = {
    "ap": "AP", "hdg": "HDG", "nav": "NAV", "ias": "IAS",
    "alt": "ALT", "vs": "VS", "apr": "APR", "rev": "REV",
}


def switch_led_report(wheel: str, colour: str = "green") -> bytes:
    """Light exactly one gear LED (bi-colour): ``green`` = down, ``red`` = transit."""
    positions: list[float | None] = [None, None, None]
    positions[_WHEELS.index(wheel)] = 1.0 if colour == "green" else 0.5
    return bytes([_REPORT_ID, gear_led_byte(positions)])


def multi_led_report(button: str) -> bytes:
    """Light exactly one Multi Panel button LED, display blank."""
    led = multi_button_led_byte(False, None, False, {button: True})
    return bytes([_REPORT_ID, *([BLANK] * _MULTI_CELLS), led, 0x00])


def multi_cell_report(cell: int, *, dot: bool = False) -> bytes:
    """Show ``8`` in one Multi Panel display cell (0..9), everything else blank."""
    cells = [BLANK] * _MULTI_CELLS
    cells[cell] = TEST_GLYPH + (DOT if dot else 0)
    return bytes([_REPORT_ID, *cells, 0x00, 0x00])


def radio_cell_report(cell: int, *, dot: bool = False) -> bytes:
    """Show ``8`` in one Radio Panel display cell (0..19), everything else blank."""
    cells = [BLANK] * _RADIO_CELLS
    cells[cell] = TEST_GLYPH + (DOT if dot else 0)
    return bytes([_REPORT_ID, *cells, *_FLAG_BYTES])


def blank_report(device_type: str) -> bytes:
    """The all-off report for a panel type — sent to clear a test send."""
    if device_type == "gear_leds":
        return bytes([_REPORT_ID, 0x00])
    if device_type == "multi_panel":
        return bytes([_REPORT_ID, *([BLANK] * _MULTI_CELLS), 0x00, 0x00])
    if device_type == "radio_panel":
        return bytes([_REPORT_ID, *([BLANK] * _RADIO_CELLS), *_FLAG_BYTES])
    raise ValueError(f"unknown panel type {device_type!r}")


@dataclass(frozen=True)
class TestTarget:
    """One identifiable physical element and the report that isolates it.

    ``dot_report`` is set for radio display cells so the GUI can also flash the
    cell's decimal point (``8.``); ``None`` where a dot makes no sense (LEDs).
    """

    key: str        # stable id, e.g. "cell:3" or "led:hdg"
    label: str      # short German label for the element
    group: str      # section header (e.g. "Display oben — Aktiv")
    report: bytes   # send this to light only this element
    dot_report: bytes | None = None


def probe_targets(output: Output) -> list[TestTarget]:
    """Every physical element of ``output`` that the 🔦 test-send can isolate.

    Order is physical (left→right, top→bottom) so a walk down the list traces the
    hardware. The display cells are fixed by the panel, independent of how many
    banks/units the profile configures — the point is to reveal that layout.
    """
    if isinstance(output, GearLedOutput):
        return [
            TestTarget(
                key=f"gear:{wheel}:{colour}",
                label=f"LED {_WHEEL_LABEL[wheel]} {word}",
                group="Fahrwerks-LEDs",
                report=switch_led_report(wheel, colour),
            )
            for wheel in _WHEELS
            for colour, word in (("green", "grün"), ("red", "rot"))
        ]
    if isinstance(output, MultiPanelOutput):
        targets = [
            TestTarget(f"led:{b}", f"LED {_MULTI_LED_LABEL[b]}", "Knopf-LEDs",
                       multi_led_report(b))
            for b in MULTI_BUTTON_ORDER
        ]
        for cell in range(_MULTI_CELLS):
            row = "oben" if cell < ROW_WIDTH else "unten"
            targets.append(TestTarget(
                key=f"cell:{cell}",
                label=f"{row} · Stelle {cell % ROW_WIDTH + 1}",
                group="Display-Zellen",
                report=multi_cell_report(cell),
                dot_report=multi_cell_report(cell, dot=True),
            ))
        return targets
    if isinstance(output, RadioPanelOutput):
        targets = []
        # Fixed HID cell map: 0..9 = upper half, 10..19 = lower half; within a
        # half the ACTIVE row is first (0..4), STANDBY second (5..9).
        rows = (("oben", "Aktiv", 0), ("oben", "Standby", ROW_WIDTH),
                ("unten", "Aktiv", 2 * ROW_WIDTH), ("unten", "Standby", 3 * ROW_WIDTH))
        for half, kind, base in rows:
            for k in range(ROW_WIDTH):
                cell = base + k
                targets.append(TestTarget(
                    key=f"cell:{cell}",
                    label=f"Stelle {k + 1}",
                    group=f"Display {half} — {kind}",
                    report=radio_cell_report(cell),
                    dot_report=radio_cell_report(cell, dot=True),
                ))
        return targets
    return []


# --------------------------------------------------------------------------- #
# Schritt D — output scan for UNKNOWN devices: walk the report address space,
# light one candidate at a time, let the user confirm which element it is. The
# builders are parameterised by the device's report length (the Saitek probes
# above are the special case where the layout is already known).
# --------------------------------------------------------------------------- #
def generic_blank(length: int) -> bytes:
    """All-off feature report for a device with ``length`` data bytes."""
    return bytes([_REPORT_ID, *([0x00] * length)])


def generic_led_report(length: int, byte: int, bit: int) -> bytes:
    """Set ONLY ``bit`` of data ``byte`` (everything else 0x00) — probe one LED."""
    data = bytearray(length)
    if 0 <= byte < length and 0 <= bit <= 7:
        data[byte] |= 1 << bit
    return bytes([_REPORT_ID, *data])


def generic_cell_report(length: int, offset: int, *, dot: bool = False) -> bytes:
    """Show ``8`` in the cell at data-byte ``offset`` (others 0x00) — probe one cell."""
    data = bytearray(length)
    if 0 <= offset < length:
        data[offset] = TEST_GLYPH + (DOT if dot else 0)
    return bytes([_REPORT_ID, *data])


def generic_led_targets(length: int) -> list[tuple[int, int]]:
    """Every ``(byte, bit)`` address to walk when hunting an LED (byte-major)."""
    return [(b, bit) for b in range(length) for bit in range(8)]


def generic_cell_targets(length: int) -> list[int]:
    """Every data-byte ``offset`` to walk when hunting a display cell."""
    return list(range(length))
