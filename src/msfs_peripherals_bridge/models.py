"""Pydantic data models for devices, mappings and aircraft profiles.

These models are the schema for the YAML files in ``config/`` and
``profiles/``. They are intentionally pure data (no I/O), so they can be
validated and unit-tested in isolation.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Discriminator, Field, Tag, field_validator, model_validator


class SourceKind(StrEnum):
    """The kind of physical input on a device."""

    AXIS = "axis"
    BUTTON = "button"
    HAT = "hat"
    SWITCH = "switch"


class CurveKind(StrEnum):
    """Response curve applied to a normalised axis value."""

    LINEAR = "linear"
    EXPO = "expo"
    SQUARED = "squared"


class Transform(BaseModel):
    """Shaping applied to a raw axis value before it becomes an action value.

    The pipeline is: raw -> normalise to [-1, 1] -> deadzone -> curve ->
    invert -> rescale to [out_min, out_max].
    """

    deadzone: float = Field(0.0, ge=0.0, lt=1.0)
    curve: CurveKind = CurveKind.LINEAR
    expo: float = Field(0.0, ge=0.0, le=1.0, description="Strength of the expo curve.")
    invert: bool = False
    out_min: float = 0.0
    out_max: float = 1.0


class EventAction(BaseModel):
    """Trigger a SimConnect client event (K: / H: event)."""

    type: Literal["event"] = "event"
    event: str = Field(..., description="SimConnect event name, e.g. THROTTLE1_SET.")
    # For buttons: the fixed value sent on press. For axes: omit and let the
    # transformed axis value supply the data parameter.
    value: int | None = None


class SimVarAction(BaseModel):
    """Set a SimVar via the bridge (uses the MobiFlight WASM channel)."""

    type: Literal["simvar"] = "simvar"
    simvar: str = Field(..., description="SimVar name, e.g. 'L:MyAircraft_Trim'.")
    unit: str = "number"
    # Swap 0<->1 before writing. For a stateful switch whose LVar uses the
    # opposite polarity (e.g. the JF Arrow fuel pump, where switch-on writes 0).
    invert: bool = Field(False, description="Write 1-value (swap a 0/1 switch state).")


class EventFromVarAction(BaseModel):
    """On a button press, read a SimVar and fire an event with that value.

    Models the SPAD.neXt-style "dynamic" mapping where one control copies a live
    value somewhere — e.g. the heading-bug-sync button:
    ``read: "PLANE HEADING DEGREES MAGNETIC"`` (unit ``degrees``) →
    ``event: HEADING_BUG_SET``. The bridge reads ``read`` in the chosen ``unit``
    at the moment of the press and transmits ``event`` with the rounded value.
    """

    type: Literal["event_from_var"] = "event_from_var"
    read: str = Field(..., description="SimVar to read, e.g. 'PLANE HEADING DEGREES MAGNETIC'.")
    event: str = Field(..., description="Event to fire with the read value, e.g. HEADING_BUG_SET.")
    unit: str = "number"


class WriteStep(BaseModel):
    """One write inside a :class:`SequenceAction` — fire an event *or* set a var.

    Exactly one of ``event`` / ``simvar`` is given. ``value`` is the event data
    parameter (e.g. ``COM1_VOLUME_SET`` 100) or the SimVar/LVar value to write
    (e.g. ``L:AUTOPILOT_MODE`` 2). LVar writes go through the MobiFlight WASM
    channel, same as :class:`SimVarAction`.
    """

    event: str | None = Field(None, description="SimConnect event to fire, e.g. COM1_VOLUME_SET.")
    simvar: str | None = Field(None, description="SimVar/LVar to set, e.g. 'L:AUTOPILOT_MODE'.")
    value: float = Field(0.0, description="Event data parameter or SimVar value.")
    unit: str = "number"

    @model_validator(mode="after")
    def _exactly_one_target(self) -> WriteStep:
        if (self.event is None) == (self.simvar is None):
            raise ValueError("WriteStep needs exactly one of 'event' or 'simvar'.")
        return self


class SequenceAction(BaseModel):
    """Run a list of writes on a switch's edges — for multi-step panel controls.

    A single ``*_SET`` event or one SimVar is not enough for some cockpit
    controls: the JF Arrow's avionics master flips several events + an LVar at
    once, and its heading-hold engages via ``L:AUTOPILOT_MODE=2`` *and*
    ``L:AUTOPILOT_HDG=1`` together. This action fires ``on_edge`` on the press /
    switch-on edge and ``off_edge`` on the release / switch-off edge (``off_edge``
    empty = nothing on release, i.e. a momentary multi-write). Mirrors a SPAD.neXt
    VALUEON/VALUEOFF macro. For momentary buttons only ``on_edge`` runs (on the
    press edge). (Named ``*_edge`` rather than ``on``/``off`` because YAML parses
    those bare keys as booleans.)
    """

    type: Literal["sequence"] = "sequence"
    on_edge: list[WriteStep] = Field(
        ..., min_length=1, description="Writes on the on/press edge."
    )
    off_edge: list[WriteStep] = Field(
        default_factory=list, description="Writes on the off edge."
    )


class RpnAction(BaseModel):
    """Run a raw RPN (MobiFlight calculator) expression on a button press.

    For controls a fixed set/event can't express. The headline case is a stateless
    bool toggle: ``(L:JF_PA28_AP_alt) ! (>L:JF_PA28_AP_alt)`` flips the LVar and,
    because ``!`` is a logical NOT, always writes exactly 0 or 1 — no drift into
    other values however it is pressed. Momentary: fires once on the press edge.
    """

    type: Literal["rpn"] = "rpn"
    code: str = Field(..., description="RPN expression, e.g. '(L:X) ! (>L:X)'.")


Action = EventAction | SimVarAction | EventFromVarAction | SequenceAction | RpnAction


class GearLedOutput(BaseModel):
    """Drive the three gear-indicator LEDs on a Saitek switch panel.

    Each wheel light is bi-colour: green when its gear is *down & locked*, red
    while it is *in transit*, and off when *up*. Mirrors the SPAD.neXt Arrow
    logic — the driving SimVars are the per-wheel gear positions
    (``Percent Over 100``, 0 = up … 1 = down); a wheel is green at/above
    ``down_at`` (0.95 leaves locking tolerance), off at exactly 0, red between.
    On MSFS the nose wheel is the *centre* gear, hence the default for ``nose``.

    When ``power`` is set, all three LEDs go dark while that SimVar reads 0 — so
    the gear lights only glow with the battery on, like the real panel.
    """

    type: Literal["gear_leds"] = "gear_leds"
    nose: str = Field("GEAR CENTER POSITION", description="Nose-wheel position SimVar.")
    left: str = Field("GEAR LEFT POSITION", description="Left-main position SimVar.")
    right: str = Field("GEAR RIGHT POSITION", description="Right-main position SimVar.")
    # A wheel counts as down (green) at/above this position, up (off) at 0.
    down_at: float = Field(0.95, gt=0.0, le=1.0, description="Position treated as down & locked.")
    # Bool SimVar gating the LEDs (0 = no power = all off). None disables gating.
    power: str | None = Field(
        "ELECTRICAL MASTER BATTERY", description="Bool SimVar; LEDs dark when 0."
    )

    def positions(self) -> tuple[str, str, str]:
        """The three position SimVars in (nose, left, right) order."""
        return (self.nose, self.left, self.right)

    def simvars(self) -> list[str]:
        """Every SimVar this output needs subscribed (positions + power)."""
        names = list(self.positions())
        if self.power is not None:
            names.append(self.power)
        return names


class SelectorSource(BaseModel):
    """An alternate value source a selector position can cycle to (e.g. CRS2).

    The selector position's own ``simvar``/``set_event`` are source #1; each
    :class:`SelectorSource` adds another the encoder/display switch between when
    an off-panel toggle steps the active source.
    """

    simvar: str = Field(..., description="Value SimVar, e.g. 'NAV OBS:2'.")
    set_event: str | None = Field(None, description="Event to set it; None = write SimVar.")


class SelectorEntry(BaseModel):
    """One position of the Multi Panel mode selector (ALT/VS/IAS/HDG/CRS).

    The selector picks which value the encoder edits and the display shows.
    ``code`` is the hardware bit (0=ALT, 1=VS, 2=IAS, 3=HDG, 4=CRS — see the
    measured map in docs/memory/multi-panel-hid.md). The encoder reads the live
    ``simvar`` value and writes ``simvar ± step`` back: as a ``set_event`` (e.g.
    ``HEADING_BUG_SET``) when given, otherwise straight to the SimVar.
    """

    code: int = Field(..., ge=0, le=4, description="Selector bit code 0..4.")
    label: str = Field(..., description="Human label, e.g. 'ALT' (logging only).")
    simvar: str = Field(..., description="Value SimVar read for display + encoder base.")
    set_event: str | None = Field(None, description="Event to set the value; None = write SimVar.")
    unit: str = "number"
    step: float = Field(1.0, gt=0, description="Encoder step per detent.")
    # Bigger step once the knob is spun fast for a few detents in a row. None =
    # no acceleration. Kept gentle: it only kicks in after a short fast streak
    # (see MultiPanelController), so a couple of quick clicks stay at `step`.
    fast_step: float | None = Field(None, gt=0, description="Step when spun fast (None = off).")
    min: float
    max: float
    rollover: bool = Field(False, description="Wrap min<->max instead of clamping (HDG/CRS).")
    # Keep a local, encoder-owned value instead of showing the live SimVar. Use for
    # values the aircraft gauge overwrites out-of-band: on the JF Arrow, engaging a
    # vertical mode drives AUTOPILOT ALTITUDE LOCK VAR / VERTICAL HOLD VAR to 0 /
    # 80000, which would otherwise clobber the target the user dialed in. A sticky
    # value starts at 0 (or `min` if 0 is out of range) and only the encoder changes
    # it, so the display holds the last set value across mode switches.
    sticky: bool = Field(False, description="Encoder-owned value; ignore live SimVar (ALT/VS).")
    # Which display row this value lives on. Rows are persistent: ALT on top and
    # VS on the bottom stay visible together, the selector only re-points the
    # encoder. The selected value owns its row; the other row keeps its last value.
    display_row: Literal["top", "bottom"] = Field(
        "top", description="Display row this value is shown on."
    )
    # Extra value sources this position cycles through, beyond simvar/set_event
    # above (which is source #1). An off-panel toggle (MultiPanelOutput.
    # source_toggle) steps the active source — e.g. CRS switching NAV1<->NAV2 OBS.
    # While the position is selected the 1-based source index shows on the *other*
    # display row. Empty = a plain single-source position.
    alt_sources: list[SelectorSource] = Field(default_factory=list)


class AuxInput(BaseModel):
    """An off-panel button (e.g. a yoke rocker) wired to a controller action."""

    device: str = Field(..., description="Device id the button is on, e.g. 'yoke'.")
    code: int = Field(..., description="Button/switch code that triggers the action.")


class DimmerTarget(BaseModel):
    """One light the dimmer drives, with its own full-scale value.

    The dimmer tracks a shared **percent** (0..100); each target is set to
    ``percent/100 * full`` so lights on different scales move together in even
    steps. Set exactly one of ``var`` (write a SimVar/LVar) or ``event`` (fire a
    K: event with the scaled value) — e.g. the Piper's panel light is the LVar
    ``L:CENTRE_LOWER_PANEL_LIGHT`` (full 10) while the radio/instrument lighting
    is the ``LIGHT_POTENTIOMETER_2_SET`` event (full 100).
    """

    var: str | None = Field(None, description="SimVar/LVar set to the scaled value.")
    event: str | None = Field(None, description="K: event fired with the scaled value.")
    full: float = Field(100.0, gt=0, description="Value at 100% brightness.")
    unit: str = "number"

    @model_validator(mode="after")
    def _exactly_one_target(self) -> DimmerTarget:
        if (self.var is None) == (self.event is None):
            raise ValueError("DimmerTarget needs exactly one of 'var' or 'event'.")
        return self


class MultiPanelDimmer(BaseModel):
    """A rotary dimmer (the Multi Panel trim wheel) driving light brightness.

    Each detent steps a shared **percent** (``step`` per detent, default 10 =
    even 10% stops) and applies it to every :class:`DimmerTarget`, each scaled to
    its own ``full`` value — so lights on different scales (the radio
    potentiometer 0..100 and the panel-light LVar 0..10) brighten together off
    one knob. ``follow_event``, when set, switches an on/off light (the Piper nav
    light) on whenever the percent is above ``min`` and off at ``min``.
    """

    cw: int = Field(..., description="Detent code that brightens (e.g. trim-wheel up).")
    ccw: int = Field(..., description="Detent code that dims.")
    step: float = Field(10.0, gt=0, description="Percent change per detent.")
    min: float = 0.0
    max: float = 100.0
    targets: list[DimmerTarget] = Field(
        ..., min_length=1, description="Lights driven by the dimmer (each with its own scale)."
    )
    follow_event: str | None = Field(
        None, description="On/off light event that follows percent>min (the nav light)."
    )


class MultiPanelOutput(BaseModel):
    """Multi Panel controller: encoder/selector input + display/LED output.

    Bidirectional, unlike the one-way gear LEDs: the selector + encoder edit
    autopilot reference values, while the display shows the selected value and
    the button LEDs reflect the autopilot master + active mode.
    """

    type: Literal["multi_panel"] = "multi_panel"
    selector: list[SelectorEntry] = Field(..., min_length=1)
    ap_master: str = Field("AUTOPILOT MASTER", description="Bool SimVar for the AP-master LED.")
    mode_var: str = Field("L:AUTOPILOT_MODE", description="Active-mode var for the mode LEDs.")
    # Buttons lit straight from a bool var, independent of mode_var — for the
    # ALT/VS *hold* modes, which coexist with a lateral mode and so can't ride the
    # single-value mode enum. Maps a Multi Panel button name (alt, vs, …) to its
    # bool SimVar; the LED mirrors that var whatever engaged it.
    bool_leds: dict[str, str] = Field(
        default_factory=dict, description="Button name -> bool var lit directly."
    )
    # Off-panel button that steps the active source of a selector position with
    # alt_sources (e.g. a yoke rocker flipping the CRS knob between NAV1/NAV2 OBS).
    source_toggle: AuxInput | None = Field(
        None, description="Button that cycles a position's alt_sources."
    )
    # The trim wheel repurposed as a light dimmer (radio + panel lights).
    dimmer: MultiPanelDimmer | None = Field(None, description="Trim-wheel light dimmer.")
    # Optional power gate: when set, the display + LEDs light only while this bool
    # var is on (e.g. ELECTRICAL MASTER BATTERY). Default None = always lit, so this
    # breaks no render behaviour for panels that don't set it. Matches the gear
    # LEDs, which already go dark without battery.
    power: str | None = Field(
        None, description="Bool var gating the display/LEDs (None = always on)."
    )

    @field_validator("bool_leds")
    @classmethod
    def _known_led_buttons(cls, v: dict[str, str]) -> dict[str, str]:
        from .mapping.leds import MULTI_LED_BUTTONS

        unknown = set(v) - MULTI_LED_BUTTONS
        if unknown:
            raise ValueError(
                f"unknown Multi Panel LED button(s) {sorted(unknown)}; "
                f"known: {sorted(MULTI_LED_BUTTONS)}"
            )
        return v

    def simvars(self) -> list[str]:
        """Every SimVar this controller needs subscribed."""
        names: list[str] = []
        for entry in self.selector:
            names.append(entry.simvar)
            names += [s.simvar for s in entry.alt_sources]
        names += [self.ap_master, self.mode_var]
        names += list(self.bool_leds.values())
        if self.dimmer is not None:
            names += [t.var for t in self.dimmer.targets if t.var is not None]
        if self.power is not None:
            names.append(self.power)
        return names


class RadioBank(BaseModel):
    """One selector position (COM1/COM2/NAV1/NAV2) on a Radio Panel unit.

    Tuning is *event-based*, mirroring SPAD.neXt and the real panel: the encoders
    don't compute a frequency, they fire the standard MSFS step events and the sim
    echoes the new STANDBY value back for the display. ``active``/``standby`` are
    the frequency SimVars shown on the unit's two display rows; the outer (coarse)
    knob fires ``whole_inc``/``whole_dec`` (whole MHz), the inner (fine) knob fires
    ``fract_inc``/``fract_dec`` — or the ``fract_fast_*`` variants once spun fast,
    so a slow turn steps fine (COM 8.33 kHz) and a fast turn steps coarse (25 kHz).
    Pushing the encoder swaps active<->standby (``swap_event``).
    """

    kind: Literal["freq"] = "freq"
    code: int = Field(..., ge=0, description="Selector bit code for this position.")
    label: str = Field(..., description="Human label, e.g. 'COM1' (logging only).")
    active: str = Field(..., description="ACTIVE frequency SimVar (top row).")
    standby: str = Field(..., description="STANDBY frequency SimVar (tuned, bottom row).")
    swap_event: str = Field(..., description="ACT/STBY swap event, e.g. COM1_RADIO_SWAP.")
    whole_inc: str = Field(..., description="Outer-knob CW event (whole MHz up).")
    whole_dec: str = Field(..., description="Outer-knob CCW event (whole MHz down).")
    fract_inc: str = Field(..., description="Inner-knob CW event, fine step (kHz up).")
    fract_dec: str = Field(..., description="Inner-knob CCW event, fine step (kHz down).")
    # Coarse fractional step fired when the inner knob is spun fast (COM 25 kHz vs
    # the fine 8.33 kHz). None = no fast distinction (e.g. NAV) -> reuse fract_*.
    fract_fast_inc: str | None = Field(None, description="Inner-knob CW when spun fast.")
    fract_fast_dec: str | None = Field(None, description="Inner-knob CCW when spun fast.")
    # Whether the inner knob shifts the STANDBY row to the 3-decimal fine view
    # (NN.NNN). Only COM 8.33 kHz has a meaningful third decimal; NAV steps 50 kHz
    # (third decimal always 0), so its fine view would just roll the lead digit off
    # for nothing. Opt-in per bank: COM -> true, NAV/ADF/XPDR -> false.
    fine_view: bool = Field(False, description="Inner knob shifts standby to NN.NNN (COM 8.33).")


class DmeSource(BaseModel):
    """One DME readout source (a NAV radio's distance + ground speed)."""

    label: str = Field(..., description="Shown source digit, e.g. '1' or '2' (NAV index).")
    distance: str = Field(..., description="DME distance SimVar, e.g. 'NAV DME:1' (nmiles).")
    speed: str = Field(..., description="DME ground-speed SimVar, e.g. 'NAV DMESPEED:1' (knots).")


class DmeBank(BaseModel):
    """DME selector position — a *display-only* readout (no tuning).

    The Saitek DME position shows the distance + ground speed of a NAV's DME. Unlike
    SPAD's fixed NAV1 readout, the push (swap) cycles the active :class:`DmeSource`
    (NAV1<->NAV2), so one position covers both. The encoders do nothing here.
    """

    kind: Literal["dme"] = "dme"
    code: int = Field(..., ge=0, description="Selector bit code for this position.")
    label: str = Field("DME", description="Human label (logging only).")
    sources: list[DmeSource] = Field(
        ..., min_length=1, description="DME sources the push cycles through (NAV1, NAV2)."
    )


class AdfBank(BaseModel):
    """ADF selector position — set the kHz frequency a digit-pair at a time.

    The 4-digit kHz frequency is edited with the two encoders + the push: the push
    toggles a two-digit cursor between the high pair (1000s, 100s) and the low pair
    (10s, 1s); the outer knob steps the active pair's left digit, the inner its
    right (each 0-9, wrapping), and the whole value is clamped to
    ``[min_khz, max_khz]`` so no out-of-range frequency can be dialled. Two dots in
    the display mark the active pair. The value is read/written on ``freq`` — the
    STANDBY var, which reads cleanly (ACTIVE reads garbage on the JF Arrow);
    ``scale`` converts the SimVar to kHz (measured 2026-07-08: reads Hz, so 0.001).
    """

    kind: Literal["adf"] = "adf"
    code: int = Field(..., ge=0, description="Selector bit code for this position.")
    label: str = Field("ADF", description="Human label (logging only).")
    freq: str = Field("ADF STANDBY FREQUENCY:1", description="Freq SimVar (reads Hz).")
    scale: float = Field(0.001, description="Multiply the SimVar to get kHz (Hz->kHz).")
    min_khz: int = Field(190, ge=0, description="Lowest dialable kHz (clamp floor).")
    max_khz: int = Field(1799, ge=0, description="Highest dialable kHz (clamp ceiling).")


class XpdrBank(BaseModel):
    """Transponder selector position — edit the squawk (top), set the QNH (bottom).

    The 4-octal-digit squawk is edited a digit at a time: the push walks an edit
    cursor across the four digits (a dot in the display marks the active one) and
    the inner knob steps the digit under the cursor (0-7, wrapping). The controller
    reads the current code, applies the step locally and writes it back via
    ``set_event`` (XPNDR_SET, BCD16).

    The otherwise-idle *outer* knob doubles as the altimeter (QNH) setting: it fires
    ``baro_inc`` / ``baro_dec`` and the bottom display row shows ``baro_var`` (hPa,
    a 4-digit integer). Leave ``baro_var`` None to keep the bottom row blank.
    """

    kind: Literal["xpdr"] = "xpdr"
    code: int = Field(..., ge=0, description="Selector bit code for this position.")
    label: str = Field("XPDR", description="Human label (logging only).")
    code_var: str = Field("TRANSPONDER CODE:1", description="Squawk SimVar (BCD16).")
    set_event: str = Field("XPNDR_SET", description="Event to set the squawk (BCD16 data).")
    # Outer knob = altimeter/QNH setting on the bottom row (None = bottom stays blank).
    # Shown as NN.NN with the dot on the 2nd digit (e.g. 29.92 inHg for the Piper).
    baro_var: str | None = Field(None, description="QNH SimVar for the bottom row (inHg).")
    baro_scale: float = Field(1.0, description="Multiply baro_var to inHg (already inHg = 1).")
    baro_inc: str = Field("KOHLSMAN_INC", description="Outer-knob-CW event (QNH up).")
    baro_dec: str = Field("KOHLSMAN_DEC", description="Outer-knob-CCW event (QNH down).")


# A selector position is one of the bank kinds, told apart by ``kind``. A callable
# discriminator lets COM/NAV entries omit ``kind`` (the common case) and default to
# "freq", while DME/XPDR (and later ADF) tag themselves explicitly.
def _bank_kind(value: object) -> str:
    if isinstance(value, dict):
        return value.get("kind", "freq")
    return getattr(value, "kind", "freq")


RadioBankT = Annotated[
    Annotated[RadioBank, Tag("freq")]
    | Annotated[DmeBank, Tag("dme")]
    | Annotated[XpdrBank, Tag("xpdr")]
    | Annotated[AdfBank, Tag("adf")],
    Discriminator(_bank_kind),
]


class RadioUnit(BaseModel):
    """One half (upper or lower) of the Saitek Radio Panel.

    Each half is an independent radio: a mode selector picking a :class:`RadioBank`,
    a dual concentric encoder (outer coarse + inner fine, pushable = swap) and a
    two-row display (ACTIVE over STANDBY). ``row`` places it in the 20-cell feature
    report — ``upper`` = cells 0..9, ``lower`` = cells 10..19 (see
    docs/memory/radio-panel-hid.md). The int codes are hardware input bits (to be
    measured at the device, like the Multi Panel).
    """

    name: str = Field(..., description="Human label, 'upper'/'lower' (logging only).")
    row: Literal["upper", "lower"] = Field(..., description="Display half this unit drives.")
    banks: list[RadioBankT] = Field(
        ..., min_length=1, description="Selectable positions (COM/NAV freq, DME, …)."
    )
    outer_cw: int = Field(..., description="Outer (coarse/whole) encoder CW code.")
    outer_ccw: int = Field(..., description="Outer encoder CCW code.")
    inner_cw: int = Field(..., description="Inner (fine/fract) encoder CW code.")
    inner_ccw: int = Field(..., description="Inner encoder CCW code.")
    swap: int = Field(..., description="ACT/STBY push (pushable encoder) code.")


class RadioPanelOutput(BaseModel):
    """Saitek Radio Panel: two independent radio units (COM/NAV), event-tuned.

    Bidirectional like the Multi Panel: the encoders fire step events while the
    displays show the ACTIVE/STANDBY frequencies streamed back from the sim. Banks are
    a discriminated union by ``kind`` covering all seven selector positions:
    COM/NAV freq (:class:`RadioBank`, event-tuned), ADF (:class:`AdfBank`, local-echo
    tuned), DME (:class:`DmeBank`, display-only) and XPDR (:class:`XpdrBank`, squawk).
    For freq banks the display follows the encoder —
    the fine encoder shifts the tuned row to ``NN.NNN`` to expose the third decimal,
    the coarse encoder back to ``NNN.NN`` — see :class:`RadioPanelController`.
    """

    type: Literal["radio_panel"] = "radio_panel"
    units: list[RadioUnit] = Field(..., min_length=1, description="Radio units (upper/lower).")
    # Optional power gate: when set, the display lights only while this bool var is
    # on (e.g. ELECTRICAL MASTER BATTERY). Default None = always lit, so this breaks
    # no render behaviour for panels that don't set it. Matches the gear LEDs, which
    # already go dark without battery. Use AVIONICS MASTER SWITCH here for a bus gate.
    power: str | None = Field(
        None, description="Bool var gating the display (None = always on)."
    )

    def simvars(self) -> list[str]:
        """Every SimVar the displays need subscribed (per bank kind)."""
        names: list[str] = []
        for unit in self.units:
            for bank in unit.banks:
                if isinstance(bank, DmeBank):
                    for src in bank.sources:
                        names += [src.distance, src.speed]
                elif isinstance(bank, XpdrBank):
                    names.append(bank.code_var)
                    if bank.baro_var is not None:
                        names.append(bank.baro_var)
                elif isinstance(bank, AdfBank):
                    names.append(bank.freq)
                else:  # freq (COM/NAV) — active + standby
                    names += [bank.active, bank.standby]
        if self.power is not None:
            names.append(self.power)
        return names


Output = Annotated[
    GearLedOutput | MultiPanelOutput | RadioPanelOutput, Field(discriminator="type")
]


class Source(BaseModel):
    """Identifies one physical control on a device.

    For axes, ``raw_min``/``raw_max`` are *optional overrides*: when omitted
    they are filled from ``config/calibration.yaml`` by ``apply_calibration``
    (matched on device id + code) before the mapping engine runs. Set them
    explicitly only to pin a deliberate semantic sub-range — e.g. clamping a
    TQ6+ lever at its detent rather than using the full hardware travel.
    """

    kind: SourceKind
    code: int = Field(..., description="evdev code (ABS_*/BTN_*) or logical index.")
    # Raw range for axes; None means "take it from calibration at load time".
    raw_min: int | None = None
    raw_max: int | None = None


class Binding(BaseModel):
    """Connects one physical Source to one Action, with optional shaping."""

    name: str = Field(..., description="Human label, shown in the CLI.")
    source: Source
    action: Action = Field(..., discriminator="type")
    transform: Transform = Field(default_factory=Transform)

    @model_validator(mode="after")
    def _buttons_need_value(self) -> Binding:
        if (
            self.source.kind is SourceKind.BUTTON
            and isinstance(self.action, EventAction)
            and self.action.value is None
        ):
            # A button mapped to an event must send a concrete value on press.
            self.action.value = 1
        return self


class DeviceDef(BaseModel):
    """A known physical device, matched by USB vendor/product id."""

    id: str = Field(..., description="Stable key used by profiles, e.g. 'tq6'.")
    name: str
    vendor: str = Field(..., description="USB idVendor, hex string e.g. '16d0'.")
    product: str = Field(..., description="USB idProduct, hex string e.g. '0da2'.")
    # How the device is read. Axis hardware (yokes, pedals, quadrants) presents
    # as evdev joysticks; the Saitek panels are raw-HID (button/LED report
    # frames) and are read through /dev/hidraw instead.
    transport: Literal["evdev", "hidraw"] = "evdev"
    # Some devices report a useless USB id (the Fulcrum yoke is genuinely
    # 0000:0000, shared with audio nodes). An optional case-insensitive
    # substring of the evdev device name disambiguates those.
    name_match: str | None = None

    @property
    def usb_key(self) -> tuple[int, int]:
        return (int(self.vendor, 16), int(self.product, 16))

    def matches(self, vendor: int, product: int, name: str) -> bool:
        if (vendor, product) != self.usb_key:
            return False
        if self.name_match is not None:
            return self.name_match.lower() in name.lower()
        return True


class DeviceCatalog(BaseModel):
    """Top-level model for ``config/devices.yaml``."""

    devices: list[DeviceDef]

    def by_id(self, device_id: str) -> DeviceDef | None:
        return next((d for d in self.devices if d.id == device_id), None)


class Profile(BaseModel):
    """A per-aircraft mapping profile (one YAML file in ``profiles/``)."""

    name: str
    description: str = ""
    # Title substrings used to auto-select this profile from the loaded
    # aircraft ('TITLE' SimVar reported by the sim). Case-insensitive.
    aircraft_match: list[str] = Field(default_factory=list)
    # device id -> its bindings for this aircraft.
    bindings: dict[str, list[Binding]] = Field(default_factory=dict)
    # device id -> output declarations (e.g. switch-panel gear LEDs). The device
    # must support output (a hidraw panel); SimVar-driven, streamed back from the
    # bridge. Empty for most profiles.
    outputs: dict[str, list[Output]] = Field(default_factory=dict)
