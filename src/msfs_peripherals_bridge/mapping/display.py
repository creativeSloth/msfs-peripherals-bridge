"""Render the Saitek Multi Panel 7-segment display (pure logic).

The Multi Panel shows two rows of five digit cells, driven by a single HID
feature report whose first ten data bytes are the cells (indices 0..4 = top row
left-to-right, 5..9 = bottom row). Each cell takes one byte:

    0x00..0x09  digit 0..9
    0x0F        blank   (used to suppress leading zeros)
    0xEE        minus   (for negative values, e.g. vertical speed)

(Encoding measured 2026-06-30 on the hardware — see docs/memory/multi-panel-hid.md.)

This module turns a numeric value into the five cell bytes for a row, right
justified and blank padded. It is pure so it can be unit-tested without hardware.
"""

from __future__ import annotations

ROW_WIDTH = 5
BLANK = 0x0F
MINUS = 0xEE

# A character (from str(int)) -> its cell byte.
_GLYPH = {str(d): d for d in range(10)} | {"-": MINUS, " ": BLANK}


def format_row(value: float | None, width: int = ROW_WIDTH) -> list[int]:
    """Encode a numeric ``value`` into ``width`` right-justified cell bytes.

    ``None`` (value not yet known) and any value too wide for the row render as
    all-blank — better a blank row than a wrong/truncated number. Negative values
    carry a leading minus cell; the integer part is shown (values are rounded).
    """
    if value is None:
        return [BLANK] * width
    text = str(round(value))
    if len(text) > width:  # would overflow the row -> blank rather than mislead
        return [BLANK] * width
    text = text.rjust(width)
    return [_GLYPH[ch] for ch in text]


def display_cells(top: float | None, bottom: float | None) -> list[int]:
    """Assemble the ten display cell bytes (top row then bottom row)."""
    return format_row(top) + format_row(bottom)
