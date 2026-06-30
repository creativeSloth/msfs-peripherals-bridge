"""Stateful controller for the Saitek Multi Panel (pure logic).

The Multi Panel ties input and output together through one piece of shared
state — the mode selector — so it does not fit the stateless MappingEngine.
This controller owns that state:

* the **selector** position picks which autopilot value the encoder edits and
  the display shows;
* the **encoder** reads the live value (kept fresh from the bridge's state
  stream, same as any output) and writes ``value ± step`` back, with a larger
  step when the knob is spun quickly;
* the **display** shows the selected value (top row); the **button LEDs** show
  the autopilot master + active mode.

It is pure: input methods return SimConnect ``Command``s and ``render`` returns
the feature-report bytes, so the whole behaviour is unit-testable. The runtime
feeds it device events + state updates and performs the I/O (Chunk D).

See docs/memory/multi-panel-hid.md for the measured HID map.
"""

from __future__ import annotations

from ..models import MultiPanelOutput, SelectorEntry
from ..simconnect.protocol import Command, SendEvent, SetSimVar
from .display import display_cells
from .leds import multi_button_led_byte

# Input bit codes (byte*8+bit) on the Multi Panel, from the measured map.
SELECTOR_CODES = range(0, 5)  # 0=ALT 1=VS 2=IAS 3=HDG 4=CRS
ENCODER_CW = 5
ENCODER_CCW = 6

# Report id 0, then 12 data bytes (10 display cells + LED byte + 1 spare).
_REPORT_ID = 0x00

# Two detents closer together than this (seconds) count as a fast spin.
_FAST_WINDOW = 0.12


def _as_float(value: object) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


class MultiPanelController:
    """Owns selector + value state; turns encoder/selector events into actions."""

    def __init__(self, config: MultiPanelOutput, *, fast_window: float = _FAST_WINDOW) -> None:
        self.config = config
        self._by_code: dict[int, SelectorEntry] = {e.code: e for e in config.selector}
        self.selector: int = config.selector[0].code
        self.values: dict[str, float | None] = {}
        self._last_tick: float | None = None
        self._fast_window = fast_window

    def subscriptions(self) -> list[str]:
        """SimVars this controller needs streamed from the bridge."""
        return self.config.simvars()

    # -- input -------------------------------------------------------------
    def on_selector(self, code: int) -> None:
        """Move the active selector to ``code`` (ignored if not a known position)."""
        if code in self._by_code:
            self.selector = code

    def on_encoder(self, clockwise: bool, now: float) -> list[Command]:
        """Edit the selected value by one detent; return the command(s) to send.

        Empty when the base value isn't known yet (no state received) — better
        to do nothing than to seed a guess. Updates the local value optimistically
        so a quick spin accumulates before the sim echoes the new value back.
        """
        entry = self._by_code.get(self.selector)
        if entry is None:
            return []
        current = self.values.get(entry.simvar)
        if current is None:
            return []
        fast = self._last_tick is not None and (now - self._last_tick) < self._fast_window
        self._last_tick = now
        step = entry.fast_step if fast else entry.step
        new = _adjust(current, step if clockwise else -step, entry)
        self.values[entry.simvar] = new
        data = round(new)
        if entry.set_event is not None:
            return [SendEvent(name=entry.set_event, data=data)]
        return [SetSimVar(name=entry.simvar, unit=entry.unit, value=new)]

    def on_event(self, code: int, value: int, now: float) -> list[Command]:
        """Route a raw multi_panel DeviceEvent (selector / encoder) by bit code.

        Only the press/enter edge (value 1) matters: selector positions and
        encoder detents both report a 1 then a 0.
        """
        if value != 1:
            return []
        if code in self._by_code:
            self.on_selector(code)
            return []
        if code == ENCODER_CW:
            return self.on_encoder(clockwise=True, now=now)
        if code == ENCODER_CCW:
            return self.on_encoder(clockwise=False, now=now)
        return []

    # -- output ------------------------------------------------------------
    def on_state(self, name: str, value: object) -> None:
        """Record a SimVar update streamed from the bridge."""
        self.values[name] = _as_float(value)

    def render(self) -> bytes:
        """Build the full feature-report buffer (display cells + LED byte)."""
        entry = self._by_code.get(self.selector)
        top = self.values.get(entry.simvar) if entry is not None else None
        cells = display_cells(top=top, bottom=None)
        ap_master = (self.values.get(self.config.ap_master) or 0) >= 0.5
        mode = self.values.get(self.config.mode_var)
        led = multi_button_led_byte(ap_master, int(mode) if mode is not None else None)
        return bytes([_REPORT_ID, *cells, led, 0x00])


def _adjust(current: float, delta: float, entry: SelectorEntry) -> float:
    """Apply ``delta`` to ``current``, clamping or rolling over per the entry."""
    value = current + delta
    if entry.rollover:
        span = entry.max - entry.min + 1
        return entry.min + (value - entry.min) % span
    return max(entry.min, min(entry.max, value))
