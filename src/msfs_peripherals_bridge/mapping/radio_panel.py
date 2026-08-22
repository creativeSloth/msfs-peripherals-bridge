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

from ..models import AdfBank, DmeBank, RadioBank, RadioPanelOutput, XpdrBank
from ..simconnect.protocol import Command, SendEvent, SetSimVar
from .display import BLANK, DOT, ROW_WIDTH, format_frequency, format_measure, format_row

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


def _squawk_digits(bcd: int) -> list[int]:
    """The four octal digits of a BCD16 squawk (each masked to 0-7)."""
    return [(bcd >> 12) & 7, (bcd >> 8) & 7, (bcd >> 4) & 7, bcd & 7]


def _squawk_step_digit(bcd: int, index: int, delta: int) -> int:
    """Step a single octal digit (0-7, wrapping) of a BCD16 squawk.

    ``index`` 0 = leftmost (thousands) .. 3 = rightmost (ones). Only that digit
    changes — squawk digits are independent, there is no carry into the neighbours.
    Squawk codes are octal (Mode A: 4096 codes = 8^4), so each digit wraps 0-7.
    Returns the new BCD16 code.
    """
    digits = _squawk_digits(bcd)
    digits[index] = (digits[index] + delta) % 8
    return (digits[0] << 12) | (digits[1] << 8) | (digits[2] << 4) | digits[3]


def _khz_digits(khz: int) -> list[int]:
    """The four decimal digits (thousands, hundreds, tens, ones) of a kHz value."""
    return [(khz // 1000) % 10, (khz // 100) % 10, (khz // 10) % 10, khz % 10]


def _step_khz_digit(khz: int, index: int, delta: int, *, lo: int, hi: int) -> int:
    """Step one decimal digit of a 4-digit kHz value, wrapping *within that digit*.

    The digit wraps over only the range that keeps the whole frequency inside
    ``[lo, hi]`` while the other digits stay put — so at the top the thousands digit
    cycles 0..1 and, with thousands = 1, the hundreds cycle 0..7 (max 1799), each
    without disturbing its neighbours or clamping them to 9. ``index`` 0 = thousands.
    """
    place = (1000, 100, 10, 1)[index]
    digits = _khz_digits(khz)
    others = khz - digits[index] * place  # the value with this digit zeroed out
    hi_allow, lo_need = hi - others, lo - others  # digit*place must land in here
    dmax = min(9, hi_allow // place) if hi_allow >= 0 else -1
    dmin = max(0, (lo_need + place - 1) // place) if lo_need > 0 else 0  # ceil, clamped
    if dmin > dmax:  # no digit keeps the value in range (shouldn't happen) -> no change
        return khz
    span = dmax - dmin + 1
    digits[index] = dmin + (digits[index] - dmin + delta) % span
    return digits[0] * 1000 + digits[1] * 100 + digits[2] * 10 + digits[3]


def _adf_khz_from_counters(values: dict[str, float | None], bank: AdfBank) -> int | None:
    """The KR-85 ADF frequency in kHz from its three digit counters, or None if any
    counter hasn't streamed yet. ``F = (dig1 + 1)*100 + dig2*10 + dig3`` (see AdfBank).
    """
    d1, d2, d3 = (values.get(bank.dig1_var), values.get(bank.dig2_var), values.get(bank.dig3_var))
    if d1 is None or d2 is None or d3 is None:
        return None
    return (int(d1) + 1) * 100 + int(d2) * 10 + int(d3)


def _adf_counters_from_khz(khz: int) -> tuple[int, int, int]:
    """Decompose a kHz frequency into the KR-85 (dig1, dig2, dig3) counters
    (inverse of :func:`_adf_khz_from_counters`)."""
    return khz // 100 - 1, (khz // 10) % 10, khz % 10


@dataclass
class _UnitState:
    """Mutable runtime state for one radio unit (selection + view + spin)."""

    selected: int  # currently selected bank code
    fine_view: bool = False  # True = inner-encoder view (NN.NNN); False = coarse
    dme_source: int = 0  # index into a DmeBank's sources (swap cycles NAV1/NAV2)
    xpdr_cursor: int = 0  # XPDR digit under edit (0=leftmost..3); push walks it
    adf_pair: int = 0  # ADF cursor pair: 0 = high (1000s,100s), 1 = low (10s,1s)


class RadioPanelController:
    """Owns per-unit selector/view/spin state; turns encoder events into commands."""

    def __init__(
        self, config: RadioPanelOutput, *, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self.config = config
        self._clock = clock
        # Optional battery/avionics gate: dark unless this bool var reads on. None =
        # always lit (its var is in subscriptions() via config.simvars()).
        self._power = config.power
        self.values: dict[str, float | None] = {}
        self._units = config.units
        # Per-unit bank lookup + mutable state, parallel to config.units.
        self._banks: list[dict[int, RadioBank | DmeBank | XpdrBank | AdfBank]] = [
            {b.code: b for b in u.banks} for u in self._units
        ]
        self._state: list[_UnitState] = [_UnitState(selected=u.banks[0].code) for u in self._units]
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
            st.xpdr_cursor = 0  # a fresh XPDR landing starts at the leftmost digit
            st.adf_pair = 0  # a fresh ADF landing starts on the high digit pair
            return []
        bank = self._banks[i].get(st.selected)
        if bank is None:  # selector parked on an out-of-scope position (ADF/XPDR/…)
            return []
        if isinstance(bank, DmeBank):
            # The push cycles the NAV1<->NAV2 source; the encoders do nothing. With a
            # source_var (the cockpit's DME NAV switch, e.g. L:RIGHT_MISC_dme_nav) the
            # source *is* that var: the push writes 1-current so the cockpit switch
            # follows, and the display reads it back (fully bidirectional). Without it
            # the source is a local-only index the manager re-renders from.
            if role != "swap":
                return []
            if bank.source_var is not None:
                cur = int(self.values.get(bank.source_var) or 0)
                new = (cur + 1) % len(bank.sources)
                self.values[bank.source_var] = float(new)  # local echo -> instant flip
                return [SetSimVar(name=bank.source_var, unit="number", value=new)]
            st.dme_source = (st.dme_source + 1) % len(bank.sources)
            return []
        if isinstance(bank, XpdrBank):
            # Digit-at-a-time squawk edit on the top row: the push walks a cursor
            # across the four digits (a dot marks it); the inner knob steps the digit
            # under the cursor (octal 0-7, wrapping). The outer knob is the altimeter
            # (QNH) setting shown on the bottom row — it fires baro_inc/baro_dec.
            if role == "swap":
                st.xpdr_cursor = (st.xpdr_cursor + 1) % 4
                return []
            if role == "outer_cw":
                return [SendEvent(name=bank.baro_inc)] if bank.baro_var else []
            if role == "outer_ccw":
                return [SendEvent(name=bank.baro_dec)] if bank.baro_var else []
            delta = 1 if role == "inner_cw" else -1
            current = round(self.values.get(bank.code_var) or 0)
            new = _squawk_step_digit(current, st.xpdr_cursor, delta)
            self.values[bank.code_var] = float(new)  # local echo -> instant display
            return [SendEvent(name=bank.set_event, data=new)]
        if isinstance(bank, AdfBank):
            # Digit-pair edit: the push toggles a two-digit cursor between the high
            # pair (1000s,100s) and the low pair (10s,1s); the outer knob steps the
            # pair's left digit, the inner its right (0-9 wrap), the whole kHz value
            # clamped to [min_khz, max_khz]. Two dots mark the active pair. The new
            # frequency is written back through the KR-85 digit counters (the real
            # gauge control), not the decoupled ADF SimVar.
            if role == "swap":
                st.adf_pair ^= 1
                return []
            khz = _adf_khz_from_counters(self.values, bank)
            if khz is None:  # counters not streamed yet -> nothing to edit
                return []
            left = st.adf_pair * 2  # high pair -> digit 0, low pair -> digit 2
            idx = left if role in ("outer_cw", "outer_ccw") else left + 1
            delta = 1 if role in ("outer_cw", "inner_cw") else -1
            new_khz = _step_khz_digit(khz, idx, delta, lo=bank.min_khz, hi=bank.max_khz)
            d1, d2, d3 = _adf_counters_from_khz(new_khz)
            cmds: list[Command] = []
            for var, new in ((bank.dig1_var, d1), (bank.dig2_var, d2), (bank.dig3_var, d3)):
                if self.values.get(var) != new:  # only write the counters that changed
                    self.values[var] = float(new)  # local echo -> instant display
                    cmds.append(SetSimVar(name=var, unit="number", value=new))
            return cmds
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
        if isinstance(bank, XpdrBank):
            # The squawk is local-echoed, but the QNH (outer knob -> KOHLSMAN event)
            # is applied by the sim, so read it back off-cycle to kill the poll lag.
            if bank.baro_var is not None and role in ("outer_cw", "outer_ccw"):
                return [bank.baro_var]
            return []
        if bank is None or isinstance(bank, DmeBank | AdfBank):
            # DME streams via the poll; ADF is local-echoed on write — neither needs
            # an off-cycle ReadNow.
            return []
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

        With a ``power`` gate configured, an off/unknown battery blanks the whole
        display (all 20 cells), like the gear LEDs go dark without power.
        """
        if not self._powered():
            return bytes([_REPORT_ID, *[BLANK] * (_HALF_CELLS * 2), *_FLAG_BYTES])
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
            if isinstance(bank, XpdrBank):
                halves[unit.row] = self._render_xpdr(bank, st)
                continue
            if isinstance(bank, AdfBank):
                halves[unit.row] = self._render_adf(bank, st)
                continue
            stby_decimals = _FINE_DECIMALS if st.fine_view else _COARSE_DECIMALS
            halves[unit.row] = format_frequency(
                self.values.get(bank.active), decimals=_COARSE_DECIMALS
            ) + format_frequency(self.values.get(bank.standby), decimals=stby_decimals)
        cells = halves["upper"] + halves["lower"]
        return bytes([_REPORT_ID, *cells, *_FLAG_BYTES])

    def _powered(self) -> bool:
        """True unless a power gate is configured and reads off/unknown."""
        if self._power is None:
            return True
        return (self.values.get(self._power) or 0) >= 0.5

    def _render_dme(self, bank: DmeBank, st: _UnitState) -> list[int]:
        """Render a DME half: distance on top, ``<nav> <ground-speed>`` below.

        The top row shows the selected source's DME distance (e.g. ``  12.3``); the
        bottom row leads with the 1-based NAV index (which source the push selected)
        then its ground speed (``2  180``). Both stream in via the poll.
        """
        idx = self._dme_source(bank, st)
        src = bank.sources[idx]
        top = format_measure(self.values.get(src.distance), decimals=1)
        speed = format_row(self.values.get(src.speed), width=ROW_WIDTH - 2)
        bottom = [*format_row(idx + 1, width=1), BLANK, *speed]
        return top + bottom

    def _dme_source(self, bank: DmeBank, st: _UnitState) -> int:
        """The active DME source index: the ``source_var`` value if set and streamed
        (so a cockpit switch drives it), else the local push-cycled index."""
        if bank.source_var is not None:
            v = self.values.get(bank.source_var)
            if v is not None:
                return int(v) % len(bank.sources)
        return st.dme_source % len(bank.sources)

    def _render_xpdr(self, bank: XpdrBank, st: _UnitState) -> list[int]:
        """Render an XPDR half: 4-digit squawk on top, altimeter (QNH) below.

        The digit values (0-7) double as their cell bytes, so a leading blank plus
        the four digits gives ``  1200`` with leading zeros preserved (0021 stays
        0021). A DOT rides on the digit under the edit cursor (``st.xpdr_cursor``,
        0 = leftmost) to show which digit the inner knob will change. The bottom row
        shows the QNH as ``NN.NN`` (e.g. ``29.92`` inHg) when ``baro_var`` is set,
        else stays blank. ⏳ in-sim: assumes TRANSPONDER CODE reads as BCD16
        (0x1200 = squawk 1200); if it reads decimal, adjust the decode + the write.
        """
        val = self.values.get(bank.code_var)
        if val is None:
            top = [BLANK] * ROW_WIDTH
        else:
            digits = _squawk_digits(round(val))
            digits[st.xpdr_cursor] += DOT  # mark the digit currently being edited
            top = [BLANK, *digits]
        return top + self._render_baro(bank)

    def _render_baro(self, bank: XpdrBank) -> list[int]:
        """The QNH bottom row: ``NN.NN`` with the dot on the 2nd digit (e.g. 29.92).

        ``baro_var`` is read (scaled by ``baro_scale``), taken to hundredths and
        shown as four digits with the decimal point riding on the second one. No
        ``baro_var`` (or no value yet) leaves the row blank.
        """
        if bank.baro_var is None:
            return [BLANK] * ROW_WIDTH
        val = self.values.get(bank.baro_var)
        if val is None:
            return [BLANK] * ROW_WIDTH
        hundredths = round(val * bank.baro_scale * 100)
        if not 0 <= hundredths <= 9999:
            return [BLANK] * ROW_WIDTH
        d = [
            (hundredths // 1000) % 10,
            (hundredths // 100) % 10,
            (hundredths // 10) % 10,
            hundredths % 10,
        ]
        d[1] += DOT  # decimal point after the 2nd digit -> NN.NN
        return [BLANK, *d]

    def _render_adf(self, bank: AdfBank, st: _UnitState) -> list[int]:
        """Render an ADF half: the 4-digit kHz frequency on top (bottom blank).

        The value is computed from the KR-85 digit counters; its four digits fill the
        top row (leading zeros kept, e.g. ``0350``). Two DOTs mark the digit pair
        under the cursor (``st.adf_pair``: 0 = 1000s+100s, 1 = 10s+1s) — the pair the
        encoders are currently editing.
        """
        khz = _adf_khz_from_counters(self.values, bank)
        if khz is None:
            return [BLANK] * _HALF_CELLS
        khz = max(0, min(9999, khz))  # display-width guard
        digits = _khz_digits(khz)
        left = st.adf_pair * 2
        digits[left] += DOT  # two dots -> the active pair
        digits[left + 1] += DOT
        return [BLANK, *digits] + [BLANK] * ROW_WIDTH
