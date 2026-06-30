"""Render Saitek switch-panel gear LEDs to a feature-report byte (pure logic).

The Pro Flight Switch Panel drives its three gear-indicator lights with a single
HID feature report: report id 0, one data byte. Each wheel light is bi-colour
and occupies two bits — a green bit and a red bit. Setting both green and red
for a wheel makes green win on the hardware, so a wheel is rendered as exactly
one of green / red / off (never both).

Bit layout (measured 2026-06-24):
    0 = nose green   1 = left green   2 = right green
    3 = nose red     4 = left red     5 = right red

This module is pure so it can be unit-tested without hardware.
"""

from __future__ import annotations

from collections.abc import Sequence

# Float slack when comparing a 0..1 gear position against its end stops.
_EPS = 1e-6

# (green_bit, red_bit) for the wheels in (nose, left, right) order.
_WHEEL_BITS: tuple[tuple[int, int], ...] = ((0, 3), (1, 4), (2, 5))


def gear_led_byte(
    positions: Sequence[float | None], down_at: float = 0.95, powered: bool = True
) -> int:
    """Map (nose, left, right) gear positions to the LED feature-report byte.

    Each position is 0 (up) … 1 (down). A wheel is green at/above ``down_at``
    (down & locked), off at exactly 0 (up), and red anywhere in between (in
    transit). ``None`` positions — not yet known from the sim — render as off.
    With ``powered`` False (battery off) every LED is dark, matching the panel.
    """
    if not powered:
        return 0
    byte = 0
    for pos, (green_bit, red_bit) in zip(positions, _WHEEL_BITS, strict=True):
        if pos is None:
            continue
        if pos >= down_at - _EPS:
            byte |= 1 << green_bit
        elif pos > _EPS:
            byte |= 1 << red_bit
    return byte


# Multi Panel button LEDs (feature-report byte 10). Bit per button, measured
# 2026-06-30: 0=AP 1=HDG 2=NAV 3=IAS 4=ALT 5=VS 6=APR 7=REV.
_MULTI_AP_BIT = 0
# JF Arrow autopilot mode (L:AUTOPILOT_MODE, from SPAD Arrow profile) -> lit LED
# bit. The Arrow AP has no IAS/ALT/VS hold modes, so those LEDs stay dark.
_MULTI_MODE_BIT = {0: 2, 1: 2, 2: 1, 3: 6, 4: 7}  # NAV, NAV-arm, HDG, APR, REV


def multi_button_led_byte(ap_master: bool, mode: int | None) -> int:
    """Map autopilot master + active mode to the Multi Panel LED byte.

    The AP light tracks the master switch; the active-mode light (NAV/HDG/APR/REV)
    only glows while the master is on — matching the SPAD Arrow logic where a mode
    LED requires ``L:AUTOPILOT_MODE`` to equal that button *and* the master engaged.
    """
    byte = 0
    if ap_master:
        byte |= 1 << _MULTI_AP_BIT
        bit = _MULTI_MODE_BIT.get(mode) if mode is not None else None
        if bit is not None:
            byte |= 1 << bit
    return byte
