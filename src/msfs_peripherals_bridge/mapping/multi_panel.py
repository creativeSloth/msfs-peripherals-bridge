"""Stateful controller for the Saitek Multi Panel (pure logic).

The Multi Panel ties input and output together through one piece of shared
state — the mode selector — so it does not fit the stateless MappingEngine.
This controller owns that state:

* the **selector** position picks which autopilot value the encoder edits and
  the display shows;
* the **encoder** reads the live value (kept fresh from the bridge's state
  stream, same as any output) and writes ``value ± step`` back;
* the **display** shows one value per row — each selector value owns a fixed row
  (ALT top, VS bottom) so both stay visible while the encoder switches between
  them; the **button LEDs** show the autopilot master + active mode.

It is pure: input methods return SimConnect ``Command``s and ``render`` returns
the feature-report bytes, so the whole behaviour is unit-testable. The runtime
feeds it device events + state updates and performs the I/O (Chunk D).

See docs/memory/multi-panel-hid.md for the measured HID map.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from ..models import MultiPanelOutput, SelectorEntry
from ..simconnect.protocol import Command, SendEvent, SetSimVar
from .display import BLANK, ROW_WIDTH, display_cells, format_row
from .leds import multi_button_led_byte

# Input bit codes (byte*8+bit) on the Multi Panel, from the measured map.
SELECTOR_CODES = range(0, 5)  # 0=ALT 1=VS 2=IAS 3=HDG 4=CRS
ENCODER_CW = 5
ENCODER_CCW = 6

# Report id 0, then 12 data bytes (10 display cells + LED byte + 1 spare).
_REPORT_ID = 0x00

# Gentle encoder acceleration: a detent counts as "fast" when it follows the
# previous one within _FAST_WINDOW seconds, and the bigger fast_step only kicks
# in once _FAST_AFTER fast detents have stacked up in a row. So a couple of quick
# clicks stay at the base step — only sustained fast spinning ramps up.
_FAST_WINDOW = 0.06
_FAST_AFTER = 3


def _as_float(value: object) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


class MultiPanelController:
    """Owns selector + value state; turns encoder/selector events into actions."""

    def __init__(
        self, config: MultiPanelOutput, *, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self.config = config
        self._clock = clock
        # Optional battery/avionics gate: dark unless this bool var reads on. None =
        # always lit (its var is in subscriptions() via config.simvars()).
        self._power = config.power
        # Encoder spin tracking for gentle acceleration (timestamp of the last
        # detent + how many fast detents have stacked up in a row).
        self._last_tick: float | None = None
        self._fast_streak: int = 0
        self._by_code: dict[int, SelectorEntry] = {e.code: e for e in config.selector}
        self.selector: int = config.selector[0].code
        self.values: dict[str, float | None] = {}
        # Which entry each display row currently shows. Seeded with the first
        # entry assigned to each row so ALT (top) and VS (bottom) are visible
        # from the start; a selector move re-points only that entry's row.
        self._row_entry: dict[str, SelectorEntry | None] = {"top": None, "bottom": None}
        for entry in config.selector:
            if self._row_entry[entry.display_row] is None:
                self._row_entry[entry.display_row] = entry
        # Active source index per selector code (0 = the entry's own simvar; >0
        # picks alt_sources[i-1]). Only positions with alt_sources ever change.
        self._source_index: dict[int, int] = {}
        # The dimmer self-tracks its percent: the lights are L: vars the bridge
        # can write but not yet read back, so we can't seed from sim state.
        self._dimmer_value: float = config.dimmer.min if config.dimmer is not None else 0.0
        # Sticky selector values (e.g. ALT/VS): local, encoder-owned so the JF
        # gauge's out-of-band resets don't clobber the dialed target. Start at 0
        # (or min when 0 is out of range); only on_encoder changes them.
        self._sticky: dict[int, float] = {
            e.code: (0.0 if e.min <= 0 <= e.max else e.min)
            for e in config.selector
            if e.sticky
        }

    def subscriptions(self) -> list[str]:
        """SimVars this controller needs streamed from the bridge."""
        return self.config.simvars()

    def consumes(self, code: int) -> bool:
        """True if ``code`` is one of this panel's own inputs (selector/encoder/dimmer)."""
        if code in self._by_code or code in (ENCODER_CW, ENCODER_CCW):
            return True
        d = self.config.dimmer
        return d is not None and code in (d.cw, d.ccw)

    def refresh_after(self, code: int) -> list[str]:
        """No off-cycle read-back needed: this panel's display is driven by its own
        encoder value and mode LEDs, not by echoing a var it just nudged."""
        return []

    def _source(self, entry: SelectorEntry) -> tuple[str, str | None]:
        """The active ``(simvar, set_event)`` for ``entry`` given its source index."""
        idx = self._source_index.get(entry.code, 0)
        if idx == 0 or not entry.alt_sources:
            return entry.simvar, entry.set_event
        src = entry.alt_sources[idx - 1]
        return src.simvar, src.set_event

    # -- input -------------------------------------------------------------
    def on_selector(self, code: int) -> None:
        """Move the active selector to ``code`` (ignored if not a known position)."""
        entry = self._by_code.get(code)
        if entry is not None:
            self.selector = code
            self._row_entry[entry.display_row] = entry

    def toggle_source(self) -> None:
        """Step the active source of every position with alt_sources (e.g. CRS1<->2)."""
        for entry in self.config.selector:
            if entry.alt_sources:
                count = len(entry.alt_sources) + 1
                self._source_index[entry.code] = (self._source_index.get(entry.code, 0) + 1) % count

    def _encoder_step(self, entry: SelectorEntry) -> float:
        """Pick this detent's step, ramping to ``fast_step`` on a sustained fast spin.

        A detent is "fast" when it lands within ``_FAST_WINDOW`` of the previous
        one; ``fast_step`` only applies after ``_FAST_AFTER`` fast detents in a row,
        so brief quick turns stay at the base step.
        """
        now = self._clock()
        gap = None if self._last_tick is None else now - self._last_tick
        self._last_tick = now
        self._fast_streak = self._fast_streak + 1 if (gap is not None and gap < _FAST_WINDOW) else 0
        if entry.fast_step is not None and self._fast_streak >= _FAST_AFTER:
            return entry.fast_step
        return entry.step

    def on_encoder(self, clockwise: bool) -> list[Command]:
        """Edit the selected value by one detent; return the command(s) to send.

        Empty when the base value isn't known yet (no state received) — better
        to do nothing than to seed a guess. Updates the local value optimistically
        so a quick spin accumulates before the sim echoes the new value back.
        Uses ``step`` normally, ``fast_step`` once a fast spin is sustained.
        """
        entry = self._by_code.get(self.selector)
        if entry is None:
            return []
        simvar, set_event = self._source(entry)
        current = self._value_for(entry)
        if current is None:
            return []
        if entry.off_above is not None and current >= entry.off_above:
            current = 0.0  # editing up from an "off" sentinel (e.g. ALT 80000) starts at 0
        step = self._encoder_step(entry)
        new = _adjust(current, step if clockwise else -step, entry)
        if entry.sticky:
            self._sticky[entry.code] = new
        else:
            self.values[simvar] = new
        data = round(new)
        if set_event is not None:
            return [SendEvent(name=set_event, data=data)]
        # At a (non-wrapping) rail the value stops changing — don't re-send the
        # same SimVar write each detent (same flood guard as the dimmer above).
        if new == current:
            return []
        return [SetSimVar(name=simvar, unit=entry.unit, value=new)]

    def on_event(self, code: int, value: int) -> list[Command]:
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
            return self.on_encoder(clockwise=True)
        if code == ENCODER_CCW:
            return self.on_encoder(clockwise=False)
        d = self.config.dimmer
        if d is not None and code in (d.cw, d.ccw):
            return self._on_dimmer(1 if code == d.cw else -1)
        return []

    def _on_dimmer(self, direction: int) -> list[Command]:
        """Step the light dimmer by one detent; scale each target + nav follow.

        Self-tracks the percent (the light LVars can't be read back yet); each
        target is set to ``percent/100 * full`` so lights on different scales (the
        radio potentiometer 0..100, the panel LVar 0..10) move together, plus the
        nav-follow event when configured.
        """
        d = self.config.dimmer
        if d is None:
            return []
        prev = self._dimmer_value
        self._dimmer_value = max(d.min, min(d.max, prev + direction * d.step))
        # Already at the rail: emit nothing. A held (or overshooting) dimmer would
        # otherwise re-send the *same* value every detent, flooding the MobiFlight
        # channel — which access-violates the SimConnect link and drops the
        # connection (observed crash 2026-06-30, value pinned at 10).
        if self._dimmer_value == prev:
            return []
        pct = self._dimmer_value
        frac = pct / 100.0
        commands: list[Command] = []
        for t in d.targets:
            scaled = round(frac * t.full)
            if t.var is not None:
                commands.append(SetSimVar(name=t.var, unit=t.unit, value=scaled))
            elif t.event is not None:
                commands.append(SendEvent(name=t.event, data=scaled))
        if d.follow_event is not None:
            commands.append(SendEvent(name=d.follow_event, data=1 if pct > d.min else 0))
        return commands

    # -- output ------------------------------------------------------------
    def on_state(self, name: str, value: object) -> None:
        """Record a SimVar update streamed from the bridge."""
        self.values[name] = _as_float(value)

    def _value_for(self, entry: SelectorEntry) -> float | None:
        """The value to show/edit for ``entry``: local when sticky, else the live
        SimVar (kept fresh by ``on_state``)."""
        if entry.sticky:
            return self._sticky.get(entry.code)
        simvar, _ = self._source(entry)
        return self.values.get(simvar)

    def _row_value(self, row: str) -> float | None:
        """The value currently shown on ``row`` (None if nothing assigned).

        With ``off_above`` set, a live value at/above that sentinel — or a missing
        value — reads as 0 (e.g. the JF ALT target parks at 80000 when off)."""
        entry = self._row_entry.get(row)
        if entry is None:
            return None
        value = self._value_for(entry)
        if entry.off_above is not None and (value is None or value >= entry.off_above):
            return 0.0
        return value

    def render(self, blink_on: bool = True) -> bytes:
        """Build the full feature-report buffer (display cells + LED byte).

        ``blink_on`` is the shared blink phase (driven by the output manager's
        ticker) that flashes the OMNI-mode IAS LED.

        With a ``power`` gate configured, an off/unknown battery blanks the whole
        panel (all cells + LED byte 0), like the gear LEDs go dark without power.
        """
        if not self._powered():
            return bytes([_REPORT_ID, *display_cells(None, None), 0x00, 0x00])
        selected = self._by_code.get(self.selector)
        if selected is not None and selected.alt_sources:
            # The panel blanks the bottom row in CRS mode, so the 1-based source
            # index goes in the *leftmost* cell of the selected row, a blank
            # spacer, then the value right-justified in the remaining cells:
            #   [index][blank][hundreds][tens][ones]
            index = self._source_index.get(selected.code, 0) + 1
            value_cells = format_row(self._row_value(selected.display_row), width=ROW_WIDTH - 2)
            row = [index, BLANK, *value_cells]
            other = format_row(self._row_value(_other_row(selected.display_row)))
            cells = row + other if selected.display_row == "top" else other + row
        else:
            cells = display_cells(top=self._row_value("top"), bottom=self._row_value("bottom"))
        ap_master = (self.values.get(self.config.ap_master) or 0) >= 0.5
        mode = self.values.get(self.config.mode_var)
        bool_leds = {
            name: (self.values.get(var) or 0) >= 0.5
            for name, var in self.config.bool_leds.items()
        }
        led = multi_button_led_byte(
            ap_master, int(mode) if mode is not None else None, blink_on, bool_leds,
            mode_leds=self.config.mode_leds, mode_blink_leds=self.config.mode_blink_leds,
        )
        return bytes([_REPORT_ID, *cells, led, 0x00])

    def _powered(self) -> bool:
        """True unless a power gate is configured and reads off/unknown."""
        if self._power is None:
            return True
        return (self.values.get(self._power) or 0) >= 0.5


def _other_row(row: str) -> str:
    """The display row that isn't ``row``."""
    return "bottom" if row == "top" else "top"


def _adjust(current: float, delta: float, entry: SelectorEntry) -> float:
    """Apply ``delta`` to ``current``, clamping or rolling over per the entry."""
    value = current + delta
    if entry.rollover:
        span = entry.max - entry.min + 1
        return entry.min + (value - entry.min) % span
    return max(entry.min, min(entry.max, value))
