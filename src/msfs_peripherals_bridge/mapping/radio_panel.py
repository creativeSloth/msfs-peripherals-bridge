"""Stateful controller for the Saitek Radio Panel (pure logic).

Two independent radio units (upper + lower). Each has a mode selector picking a
:class:`RadioBank`, a dual concentric encoder (outer coarse, inner fine, pushable
= swap) and a two-row display (ACTIVE over STANDBY). Tuning is *event-based*,
mirroring SPAD.neXt and the real panel: the encoders fire the standard MSFS step
events and the sim echoes the new STANDBY frequency back on the state stream for
the display (no local frequency math). Two implicit UI layers, decided 2026-07-04
(see docs/memory/radio-panel-hid.md):

* **which encoder = which view** — the display follows the last-turned encoder:
  the inner (fine) knob shifts the tuned STANDBY row to ``NN.NNN`` (third decimal
  visible, the implied leading MHz digit rolls off), the outer (coarse) knob back
  to ``NNN.NN``. Sticky per unit, default coarse. The ACTIVE row stays coarse — a
  reference you read at a glance.
* **how fast the inner knob = step size** — a sustained fast spin swaps the fine
  fract event (COM 8.33 kHz) for the coarse one (25 kHz), reusing the Multi
  Panel's gentle acceleration (same ``_FAST_WINDOW``/``_FAST_AFTER``). A bank with
  no ``fract_fast_*`` (e.g. NAV) just keeps firing its fine event.

Pure: input methods return SimConnect ``Command``s and ``render`` returns the
feature-report bytes, so the whole behaviour is unit-testable. The runtime feeds
it device events + state updates and performs the I/O (Chunk C).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from ..models import RadioBank, RadioPanelOutput
from ..simconnect.protocol import Command, SendEvent
from .display import BLANK, ROW_WIDTH, format_frequency

# Report id 0, then 20 display cells + 2 trailing flag bytes (brightness/segment
# extras — value to verify in-sim; 0 is safe/blank). See radio-panel-hid.md.
_REPORT_ID = 0x00
_FLAG_BYTES = (0x00, 0x00)
_HALF_CELLS = ROW_WIDTH * 2  # a unit owns two display rows (active + standby)

# View decimals: coarse NNN.NN vs fine NN.NNN. The fine view exposes the 8.33 kHz
# third decimal by rolling the implied leading MHz digit off the 5-cell row.
_COARSE_DECIMALS = 2
_FINE_DECIMALS = 3

# Gentle inner-encoder acceleration — mirrors MultiPanelController: a detent is
# "fast" when it lands within _FAST_WINDOW of the previous one, and the coarse
# (25 kHz) event only kicks in after _FAST_AFTER fast detents in a row, so a brief
# quick turn stays fine (8.33 kHz).
_FAST_WINDOW = 0.06
_FAST_AFTER = 3


def _as_float(value: object) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


@dataclass
class _UnitState:
    """Mutable runtime state for one radio unit (selection + view + spin)."""

    selected: int  # currently selected bank code
    fine_view: bool = False  # True = inner-encoder view (NN.NNN); False = coarse
    last_tick: float | None = None
    fast_streak: int = 0


class RadioPanelController:
    """Owns per-unit selector/view/spin state; turns encoder events into commands."""

    def __init__(
        self, config: RadioPanelOutput, *, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self.config = config
        self._clock = clock
        self.values: dict[str, float | None] = {}
        self._units = config.units
        # Per-unit bank lookup + mutable state, parallel to config.units.
        self._banks: list[dict[int, RadioBank]] = [
            {b.code: b for b in u.banks} for u in self._units
        ]
        self._state: list[_UnitState] = [
            _UnitState(selected=u.banks[0].code) for u in self._units
        ]
        # code -> (unit index, role). All input codes are unique across units
        # (different physical bits), so one flat map routes every event.
        self._routes: dict[int, tuple[int, str]] = {}
        for i, u in enumerate(self._units):
            for b in u.banks:
                self._routes[b.code] = (i, "select")
            self._routes[u.outer_cw] = (i, "outer_cw")
            self._routes[u.outer_ccw] = (i, "outer_ccw")
            self._routes[u.inner_cw] = (i, "inner_cw")
            self._routes[u.inner_ccw] = (i, "inner_ccw")
            self._routes[u.swap] = (i, "swap")

    def subscriptions(self) -> list[str]:
        """Frequency SimVars this controller needs streamed from the bridge."""
        return self.config.simvars()

    def consumes(self, code: int) -> bool:
        """True if ``code`` is one of this panel's own inputs."""
        return code in self._routes

    # -- input -------------------------------------------------------------
    def on_event(self, code: int, value: int) -> list[Command]:
        """Route a raw radio_panel DeviceEvent by bit code; return command(s).

        Only the press/enter edge (value 1) acts: selector positions and encoder
        detents both report a 1 then a 0. A selector move just re-points the unit
        (no command); the encoders fire step events and the push fires the swap.
        """
        if value != 1:
            return []
        route = self._routes.get(code)
        if route is None:
            return []
        i, role = route
        st = self._state[i]
        if role == "select":
            st.selected = code
            return []
        bank = self._banks[i].get(st.selected)
        if bank is None:  # selector parked on an out-of-scope position (ADF/DME/…)
            return []
        if role == "outer_cw":
            st.fine_view = False
            return [SendEvent(name=bank.whole_inc)]
        if role == "outer_ccw":
            st.fine_view = False
            return [SendEvent(name=bank.whole_dec)]
        if role == "inner_cw":
            st.fine_view = True
            return [self._fract_event(st, bank, up=True)]
        if role == "inner_ccw":
            st.fine_view = True
            return [self._fract_event(st, bank, up=False)]
        # role == "swap"
        return [SendEvent(name=bank.swap_event)]

    def _fract_event(self, st: _UnitState, bank: RadioBank, *, up: bool) -> SendEvent:
        """Pick the inner-knob event: fine normally, coarse on a sustained fast spin.

        The coarse ``fract_fast_*`` event only applies once the spin has been fast
        for a few detents in a row; a bank without one (NAV) stays on the fine
        event throughout.
        """
        if self._tick_is_fast(st):
            name = (bank.fract_fast_inc if up else bank.fract_fast_dec) or (
                bank.fract_inc if up else bank.fract_dec
            )
        else:
            name = bank.fract_inc if up else bank.fract_dec
        return SendEvent(name=name)

    def _tick_is_fast(self, st: _UnitState) -> bool:
        """Update ``st``'s spin streak for this detent; True once it's sustained-fast."""
        now = self._clock()
        gap = None if st.last_tick is None else now - st.last_tick
        st.last_tick = now
        st.fast_streak = st.fast_streak + 1 if (gap is not None and gap < _FAST_WINDOW) else 0
        return st.fast_streak >= _FAST_AFTER

    # -- output ------------------------------------------------------------
    def on_state(self, name: str, value: object) -> None:
        """Record a SimVar update streamed from the bridge."""
        self.values[name] = _as_float(value)

    def render(self, blink_on: bool = True) -> bytes:
        """Build the full feature-report buffer (20 display cells + 2 flag bytes).

        Each unit fills its display half (``upper`` = cells 0..9, ``lower`` =
        10..19). The ACTIVE row is always coarse ``NNN.NN``; the tuned STANDBY row
        follows the unit's view (fine ``NN.NNN`` while the inner knob was last
        used). Unconfigured halves stay blank.

        ``blink_on`` is accepted for interface parity with the other panel
        controllers (the output manager passes its shared blink phase); the Radio
        Panel has no blinking LED, so it is ignored.
        """
        halves: dict[str, list[int]] = {
            "upper": [BLANK] * _HALF_CELLS,
            "lower": [BLANK] * _HALF_CELLS,
        }
        for i, unit in enumerate(self._units):
            st = self._state[i]
            bank = self._banks[i].get(st.selected)
            if bank is None:
                continue  # leave the half blank
            stby_decimals = _FINE_DECIMALS if st.fine_view else _COARSE_DECIMALS
            halves[unit.row] = format_frequency(
                self.values.get(bank.active), decimals=_COARSE_DECIMALS
            ) + format_frequency(self.values.get(bank.standby), decimals=stby_decimals)
        cells = halves["upper"] + halves["lower"]
        return bytes([_REPORT_ID, *cells, *_FLAG_BYTES])
