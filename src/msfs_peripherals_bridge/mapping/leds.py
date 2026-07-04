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

from collections.abc import Mapping, Sequence

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
# 2026-06-30. This map is the single source of truth for the byte layout.
_MULTI_BUTTON_BIT: dict[str, int] = {
    "ap": 0, "hdg": 1, "nav": 2, "ias": 3, "alt": 4, "vs": 5, "apr": 6, "rev": 7,
}
# Button names a profile may drive directly via a bool var (see bool_leds below).
MULTI_LED_BUTTONS = frozenset(_MULTI_BUTTON_BIT)
_MULTI_AP_BIT = _MULTI_BUTTON_BIT["ap"]
_MULTI_IAS_BIT = _MULTI_BUTTON_BIT["ias"]  # IAS button LED — blinks to flag OMNI
# JF Arrow autopilot mode (L:AUTOPILOT_MODE, from SPAD Arrow profile) -> lit LED
# bit. The mode enum carries one lateral mode at a time; the ALT/VS *hold* modes
# coexist with it and so are lit separately from their own bools (bool_leds).
_MULTI_MODE_BIT = {0: 2, 1: 2, 2: 1, 3: 6, 4: 7}  # NAV, OMNI(=NAV), HDG, APR, REV
# OMNI (mode 1) tracks like NAV but must be tellable apart from plain NAV
# (mode 0): light NAV solid AND blink the IAS LED. Maps mode -> the extra bit
# that blinks, on top of that mode's solid _MULTI_MODE_BIT entry.
_MULTI_MODE_BLINK_BIT = {1: _MULTI_IAS_BIT}


def multi_button_led_byte(
    ap_master: bool,
    mode: int | None,
    blink_on: bool = True,
    bool_leds: Mapping[str, bool] | None = None,
) -> int:
    """Map autopilot master + active mode to the Multi Panel LED byte.

    The AP light tracks the master switch. The active-mode light (NAV/HDG/APR/REV)
    tracks ``L:AUTOPILOT_MODE`` *independently of the master*, so the selected mode
    stays visible with the AP off — feedback on which mode the buttons have armed.
    OMNI (mode 1) additionally blinks the IAS LED (``blink_on`` is the current
    blink phase) so it reads differently from plain NAV.

    ``bool_leds`` lights extra buttons straight from their own bool state (button
    name -> on) — for the ALT/VS *hold* modes, which coexist with a lateral mode
    and so can't ride the single-value mode enum. Their bit is OR'd on top.
    """
    byte = 0
    if ap_master:
        byte |= 1 << _MULTI_AP_BIT
    if mode is not None:
        solid = _MULTI_MODE_BIT.get(mode)
        if solid is not None:
            byte |= 1 << solid
        blink = _MULTI_MODE_BLINK_BIT.get(mode)
        if blink is not None and blink_on:
            byte |= 1 << blink
    if bool_leds:
        for name, on in bool_leds.items():
            if on:
                byte |= 1 << _MULTI_BUTTON_BIT[name]
    return byte
