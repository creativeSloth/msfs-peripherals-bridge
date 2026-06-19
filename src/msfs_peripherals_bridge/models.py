"""Pydantic data models for devices, mappings and aircraft profiles.

These models are the schema for the YAML files in ``config/`` and
``profiles/``. They are intentionally pure data (no I/O), so they can be
validated and unit-tested in isolation.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class SourceKind(StrEnum):
    """The kind of physical input on a device."""

    AXIS = "axis"
    BUTTON = "button"
    HAT = "hat"


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


Action = EventAction | SimVarAction


class Source(BaseModel):
    """Identifies one physical control on a device."""

    kind: SourceKind
    code: int = Field(..., description="evdev code (ABS_*/BTN_*) or logical index.")
    # Raw range for axes; used to normalise. Defaults cover signed 16-bit axes.
    raw_min: int = -32768
    raw_max: int = 32767


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

    @property
    def usb_key(self) -> tuple[int, int]:
        return (int(self.vendor, 16), int(self.product, 16))


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
