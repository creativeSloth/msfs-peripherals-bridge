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
# The same buttons in their measured byte order (frozenset is unordered) — used
# where a stable left-to-right walk matters, e.g. the panel LED test-send.
MULTI_BUTTON_ORDER: tuple[str, ...] = tuple(_MULTI_BUTTON_BIT)
_MULTI_AP_BIT = _MULTI_BUTTON_BIT["ap"]
# Default JF Arrow map: L:AUTOPILOT_MODE value -> lit button NAME. The mode enum
# carries one lateral mode at a time; the ALT/VS *hold* modes coexist with it and
# so are lit separately from their own bools (bool_leds). Overridable per aircraft
# via MultiPanelOutput.mode_leds / .mode_blink_leds (name-based, panel-agnostic).
DEFAULT_MODE_LEDS = {0: "nav", 1: "nav", 2: "hdg", 3: "apr", 4: "rev"}
# OMNI (mode 1) tracks like NAV but must be tellable apart from plain NAV (mode 0):
# light NAV solid AND blink the IAS button on top. Maps mode -> the blinking button.
DEFAULT_MODE_BLINK_LEDS = {1: "ias"}


def multi_button_led_byte(
    ap_master: bool,
    mode: int | None,
    blink_on: bool = True,
    bool_leds: Mapping[str, bool] | None = None,
    mode_leds: Mapping[int, str] | None = None,
    mode_blink_leds: Mapping[int, str] | None = None,
) -> int:
    """Map autopilot master + active mode to the Multi Panel LED byte.

    The AP light tracks the master switch. The active-mode light tracks
    ``L:AUTOPILOT_MODE`` *independently of the master*, so the selected mode stays
    visible with the AP off. ``mode_leds`` maps the mode value to the lit button
    NAME (defaults to the JF Arrow map); ``mode_blink_leds`` maps a mode to a button
    that also BLINKS (``blink_on`` is the phase) — e.g. OMNI blinks IAS. Both are
    per-aircraft configurable so the LEDs work on any autopilot.

    ``bool_leds`` lights extra buttons straight from their own bool state (button
    name -> on) — for the ALT/VS *hold* modes, which coexist with a lateral mode
    and so can't ride the single-value mode enum. Their bit is OR'd on top.
    """
    if mode_leds is None:
        mode_leds = DEFAULT_MODE_LEDS
    if mode_blink_leds is None:
        mode_blink_leds = DEFAULT_MODE_BLINK_LEDS
    byte = 0
    if ap_master:
        byte |= 1 << _MULTI_AP_BIT
    if mode is not None:
        solid = mode_leds.get(mode)
        if solid is not None:
            byte |= 1 << _MULTI_BUTTON_BIT[solid]
        blink = mode_blink_leds.get(mode)
        if blink is not None and blink_on:
            byte |= 1 << _MULTI_BUTTON_BIT[blink]
    if bool_leds:
        for name, on in bool_leds.items():
            if on:
                byte |= 1 << _MULTI_BUTTON_BIT[name]
    return byte
