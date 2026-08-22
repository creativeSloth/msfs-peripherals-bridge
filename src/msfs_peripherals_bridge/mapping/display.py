"""Render the Saitek 7-segment displays (pure logic).

Shared by the Multi Panel and the Radio Panel, whose displays use the same cell
encoding. A row is five digit cells, one byte each:

    0x00..0x09  digit 0..9
    0x0F        blank   (used to suppress leading zeros)
    0xEE        minus   (for negative values, e.g. vertical speed)
    digit+0xD0  digit with a trailing decimal point (Radio Panel, e.g. 118.00)

(Digit/blank/minus measured 2026-06-30 on the Multi Panel — see
docs/memory/multi-panel-hid.md. The decimal-point offset was verified on the Radio
Panel 2026-07-05 — see docs/memory/radio-panel-hid.md.)

This module turns a numeric value into the five cell bytes for a row, right
justified and blank padded. It is pure so it can be unit-tested without hardware.
"""

from __future__ import annotations

ROW_WIDTH = 5
BLANK = 0x0F
MINUS = 0xEE
# Saitek lights a cell's trailing decimal point by adding 0xD0 to its digit byte
# (digit 8 with dot -> 0xD8); the dot rides on the digit, costing no extra cell.
# Verified on the Radio Panel 2026-07-05 (out_radio.py) — single source of truth.
DOT = 0xD0

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


def format_measure(value: float | None, *, decimals: int = 1, width: int = ROW_WIDTH) -> list[int]:
    """Right-justified number with a trailing decimal point, leading zeros blanked.

    For gauge readouts like DME distance (12.3). Unlike :func:`format_frequency`
    (fixed 3-digit, zero-padded freqs), this blanks leading zeros so 12.3 renders as
    ``  12.3`` — the dot rides on the last integer digit. ``None``/negative/overflow
    render all-blank.
    """
    if value is None or value < 0:
        return [BLANK] * width
    scaled = round(value * (10**decimals))
    digits = str(scaled).rjust(decimals + 1, "0")  # keep at least one integer digit
    int_str, frac_str = (digits[:-decimals], digits[-decimals:]) if decimals else (digits, "")
    cells = [_GLYPH[c] for c in int_str]
    if decimals:
        cells[-1] += DOT
        cells += [_GLYPH[c] for c in frac_str]
    if len(cells) > width:  # too wide for the row -> blank rather than mislead
        return [BLANK] * width
    return [BLANK] * (width - len(cells)) + cells


def format_frequency(mhz: float | None, *, decimals: int = 2, width: int = ROW_WIDTH) -> list[int]:
    """Encode a radio frequency (MHz) into ``width`` cells with a decimal point.

    The 5-cell line can't hold every significant digit of an 8.33 kHz COM channel
    (which needs three decimals, e.g. 118.005), so the view is shiftable:

    * ``decimals=2`` -> ``NNN.NN`` — the normal view (118.00), dot after digit 3;
    * ``decimals=3`` -> ``NN.NNN`` — the fine view (118.005 shows as ``18.005``);
      the implied leading digit (COM is always 1NN) rolls off so the third decimal
      fits. Only the low ``width`` digits are shown.

    The dot rides on the last integer digit (Saitek convention, adds ``DOT``), so
    it costs no cell. ``None`` renders all-blank.
    """
    if mhz is None or mhz < 0:
        return [BLANK] * width
    int_digits = width - decimals
    if int_digits < 1:  # need at least one integer cell to carry the dot
        return [BLANK] * width
    # Show only the low `width` digits; the implied high digit(s) roll off in the
    # shifted view (118.005 -> 18.005). Non-fine views keep the full number.
    scaled = round(mhz * (10**decimals)) % (10**width)
    text = str(scaled).rjust(width, "0")
    cells = [_GLYPH[ch] for ch in text]
    cells[int_digits - 1] += DOT  # light the dot on the last integer digit
    return cells


def display_cells(top: float | None, bottom: float | None) -> list[int]:
    """Assemble the ten display cell bytes (top row then bottom row)."""
    return format_row(top) + format_row(bottom)
