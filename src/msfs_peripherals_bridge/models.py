"""Pydantic data models for devices, mappings and aircraft profiles.

These models are the schema for the YAML files in ``config/`` and
``profiles/``. They are intentionally pure data (no I/O), so they can be
validated and unit-tested in isolation.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator


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


Action = EventAction | SimVarAction | EventFromVarAction


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
    step: float = Field(1.0, gt=0, description="Encoder step per detent (slow turn).")
    fast_step: float = Field(10.0, gt=0, description="Encoder step when spun quickly.")
    min: float
    max: float
    rollover: bool = Field(False, description="Wrap min<->max instead of clamping (HDG/CRS).")


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

    def simvars(self) -> list[str]:
        """Every SimVar this controller needs subscribed."""
        names = [e.simvar for e in self.selector]
        names += [self.ap_master, self.mode_var]
        return names


Output = Annotated[GearLedOutput | MultiPanelOutput, Field(discriminator="type")]


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
