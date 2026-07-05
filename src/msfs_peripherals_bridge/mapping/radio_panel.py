"""Stateful controller for the Saitek Radio Panel (pure logic).

Two independent radio units (upper + lower). Each has a mode selector picking a
:class:`RadioBank`, a dual concentric encoder (outer coarse, inner fine, pushable
= swap) and a two-row display (ACTIVE over STANDBY). Tuning is *event-based*,
mirroring SPAD.neXt and the real panel: the encoders fire the standard MSFS step
events and the sim echoes the new STANDBY frequency back on the state stream for
the display (no local frequency math). Two implicit UI layers, decided 2026-07-04
(see docs/memory/radio-panel-hid.md):

* **which encoder = which view** — on a bank with ``fine_view`` (COM 8.33 kHz), the
  inner (fine) knob shifts the tuned STANDBY row to ``NN.NNN`` (third decimal
  visible, the implied leading MHz digit rolls off) and the outer (coarse) knob
  shifts it back to ``NNN.NN``. NAV (50 kHz, third decimal always 0) has
  ``fine_view=False`` and stays ``NNN.NN`` throughout. Sticky per unit, reset to
  coarse on a selector move. The ACTIVE row stays coarse — a reference at a glance.
* **every inner detent = one fine step** — the inner knob always fires the fine
  fract event (COM 8.33 kHz). The spin-speed acceleration (a sustained fast spin
  switching to a coarse ``fract_fast_*`` event) was removed 2026-07-05: it was inert
  in piper_arrow.yaml and confused the encoder-bounce investigation. The model keeps
  the ``fract_fast_*`` fields so it can be reinstated later.

Because tuning is a read-back, the display would otherwise lag the 1 s subscription
poll; :meth:`refresh_after` names the tuned var so the output manager can ReadNow it
off-cycle, and a swap is mirrored locally (:meth:`on_event`) for an instant flip.

Pure: input methods return SimConnect ``Command``s and ``render`` returns the
feature-report bytes, so the whole behaviour is unit-testable. The runtime feeds
it device events + state updates and performs the I/O (Chunk C).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from ..models import DmeBank, RadioBank, RadioPanelOutput
from ..simconnect.protocol import Command, SendEvent
from .display import BLANK, ROW_WIDTH, format_frequency, format_measure, format_row

# Report id 0, then 20 display cells + 2 trailing flag bytes (brightness/segment
# extras — verified 2026-07-05: 0x00 leaves the display fully lit). See
# radio-panel-hid.md.
_REPORT_ID = 0x00
_FLAG_BYTES = (0x00, 0x00)
_HALF_CELLS = ROW_WIDTH * 2  # a unit owns two display rows (active + standby)

# View decimals: coarse NNN.NN vs fine NN.NNN. The fine view exposes the 8.33 kHz
# third decimal by rolling the implied leading MHz digit off the 5-cell row.
_COARSE_DECIMALS = 2
_FINE_DECIMALS = 3

# Swap-button debounce. The runtime's engine debounce does NOT cover this path
# (runtime.py routes controller inputs straight to handle_input), and a momentary
# pushbutton genuinely chatters, so the swap double-fired. A repeat within the
# window is dropped; the window slides (each press re-arms it) so a whole bounce
# burst collapses to one swap. 200 ms is well under any deliberate double-swap.
#
# The *encoders* are NOT debounced: measuring real bounce timing at the device
# (tools/panel-scan/scan_radio.py, 2026-07-05) proved they don't bounce in any way
# a time guard can catch. The panel polls over USB every 8 ms, and with a mandatory
# release frame between two rising edges the fastest a bit can repeat is 16 ms —
# the measured minimum, with a smooth 16→300 ms spread and no short-gap cluster
# (bounce would be bimodal). The earlier "detent jumps .015" was not bounce but
# display-latency overshoot (the read-back lagged up to a second, so the user kept
# turning); ReadNow now refreshes the tuned var within tens of ms to fix that. See
# docs/memory/radio-panel-measurement.md.
_SWAP_DEBOUNCE = 0.20


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
    dme_source: int = 0  # index into a DmeBank's sources (swap cycles NAV1/NAV2)


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
        self._banks: list[dict[int, RadioBank | DmeBank]] = [
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
        # code -> last accepted/seen press time, for the contact-bounce guard.
        self._last_fire: dict[int, float] = {}

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
        # Only the swap button is debounced (a momentary contact chatters); selector
        # moves are idempotent and the encoders don't bounce (measured — see above).
        if role == "swap" and self._bounced(code):
            return []
        st = self._state[i]
        if role == "select":
            st.selected = code
            st.fine_view = False  # a fresh bank starts coarse (NN.NNN is per-bank)
            return []
        bank = self._banks[i].get(st.selected)
        if bank is None:  # selector parked on an out-of-scope position (ADF/XPDR/…)
            return []
        if isinstance(bank, DmeBank):
            # DME is display-only: the push cycles NAV1<->NAV2, the encoders do
            # nothing. No sim command — the manager re-renders from cached values.
            if role == "swap":
                st.dme_source = (st.dme_source + 1) % len(bank.sources)
            return []
        if role == "outer_cw":
            st.fine_view = False
            return [SendEvent(name=bank.whole_inc)]
        if role == "outer_ccw":
            st.fine_view = False
            return [SendEvent(name=bank.whole_dec)]
        # Inner knob = fine (8.33 kHz) fract step. The spin-speed acceleration (a
        # sustained fast spin switching to a coarse 25 kHz fract_fast_* event) was
        # removed 2026-07-05 while isolating encoder contact-bounce. It was inert in
        # piper_arrow.yaml anyway (no fract_fast_* defined there). The model keeps
        # the fract_fast_* fields, so it can be reinstated once bounce is solved.
        if role == "inner_cw":
            st.fine_view = bank.fine_view  # COM shifts to NN.NNN; NAV stays coarse
            return [SendEvent(name=bank.fract_inc)]
        if role == "inner_ccw":
            st.fine_view = bank.fine_view
            return [SendEvent(name=bank.fract_dec)]
        # role == "swap": mirror the swap locally so the display flips instantly,
        # then fire the sim event (the poll / a scheduled ReadNow reconciles truth).
        active, standby = bank.active, bank.standby
        self.values[active], self.values[standby] = (
            self.values.get(standby),
            self.values.get(active),
        )
        st.fine_view = False  # the swapped-in standby reads plainly, not mid-fine-tune
        return [SendEvent(name=bank.swap_event)]

    def refresh_after(self, code: int) -> list[str]:
        """SimVars worth re-reading right after acting on ``code`` (low-latency echo).

        A tuning detent changes the selected bank's STANDBY frequency; a swap
        changes both rows. The output manager reads these off-cycle via ReadNow so
        the display catches up in tens of ms instead of waiting for the 1 s poll.
        Selector moves and out-of-scope banks change nothing → refresh nothing.
        """
        route = self._routes.get(code)
        if route is None:
            return []
        i, role = route
        if role == "select":
            return []
        bank = self._banks[i].get(self._state[i].selected)
        if bank is None or isinstance(bank, DmeBank):
            return []  # DME reads stream via the poll; nothing event-driven to refresh
        return [bank.active, bank.standby] if role == "swap" else [bank.standby]

    def _bounced(self, code: int) -> bool:
        """True if the swap button repeats within its debounce window (chatter).

        Sliding window: every press re-arms the guard, so a chatter burst collapses
        to one swap while a deliberate second press (>200 ms later) passes through.
        """
        now = self._clock()
        last = self._last_fire.get(code)
        self._last_fire[code] = now
        return last is not None and now - last < _SWAP_DEBOUNCE

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
            if isinstance(bank, DmeBank):
                halves[unit.row] = self._render_dme(bank, st)
                continue
            stby_decimals = _FINE_DECIMALS if st.fine_view else _COARSE_DECIMALS
            halves[unit.row] = format_frequency(
                self.values.get(bank.active), decimals=_COARSE_DECIMALS
            ) + format_frequency(self.values.get(bank.standby), decimals=stby_decimals)
        cells = halves["upper"] + halves["lower"]
        return bytes([_REPORT_ID, *cells, *_FLAG_BYTES])

    def _render_dme(self, bank: DmeBank, st: _UnitState) -> list[int]:
        """Render a DME half: distance on top, ``<nav> <ground-speed>`` below.

        The top row shows the selected source's DME distance (e.g. ``  12.3``); the
        bottom row leads with the 1-based NAV index (which source the push selected)
        then its ground speed (``2  180``). Both stream in via the poll.
        """
        src = bank.sources[st.dme_source % len(bank.sources)]
        top = format_measure(self.values.get(src.distance), decimals=1)
        speed = format_row(self.values.get(src.speed), width=ROW_WIDTH - 2)
        bottom = [*format_row(st.dme_source + 1, width=1), BLANK, *speed]
        return top + bottom
