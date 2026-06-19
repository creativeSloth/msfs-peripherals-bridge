"""Record and persist per-device axis calibration.

A calibration captures the observed raw range and resting centre of every
analog axis, plus which buttons and hat directions were seen. It is stored
in ``config/calibration.yaml`` keyed by device id and can be merged into a
profile's bindings so axis ``raw_min``/``raw_max`` reflect real hardware.
"""

from __future__ import annotations

import time
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from ..models import SourceKind


class AxisCalibration(BaseModel):
    code: int
    name: str = ""
    raw_min: int
    raw_max: int
    center: int
    # Raw value of a mechanical detent ("0" notch), if the axis has one.
    # On the TQ6+: throttle reverse, prop feather, mixture cut-off. Raw values
    # below the detent are the special zone; at/above it is the normal 0..100%
    # range. None for axes without a detent.
    detent: int | None = None


class DeviceCalibration(BaseModel):
    device_id: str
    axes: dict[int, AxisCalibration] = Field(default_factory=dict)
    buttons: list[int] = Field(default_factory=list)
    hats: list[int] = Field(default_factory=list)


class CalibrationFile(BaseModel):
    devices: dict[str, DeviceCalibration] = Field(default_factory=dict)


def load_calibration(path: Path) -> CalibrationFile:
    if not path.exists():
        return CalibrationFile()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return CalibrationFile.model_validate(data)


def save_calibration(path: Path, calibration: CalibrationFile) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(calibration.model_dump(), sort_keys=True, allow_unicode=True),
        encoding="utf-8",
    )


def current_axis_values(path: str) -> list[tuple[int, str, int]]:
    """Snapshot the current raw value of every analog axis: (code, name, value)."""
    from . import capabilities  # local import keeps evdev optional

    caps = capabilities.describe(path)
    return [(a.code, a.name, a.value) for a in caps.analog_axes]


def set_detents_from_current(
    store: CalibrationFile, device_id: str, path: str
) -> dict[int, int]:
    """Record the current axis positions as detents on the device calibration.

    Creates the device/axis calibration entries if missing (seeding raw_min/max
    from the driver-reported range). Returns {code: detent_value}.
    """
    from . import capabilities  # local import keeps evdev optional

    caps = capabilities.describe(path)
    device = store.devices.setdefault(device_id, DeviceCalibration(device_id=device_id))
    captured: dict[int, int] = {}
    for axis in caps.analog_axes:
        cal = device.axes.get(axis.code)
        if cal is None:
            cal = AxisCalibration(
                code=axis.code,
                name=axis.name,
                raw_min=axis.min,
                raw_max=axis.max,
                center=axis.value,
            )
            device.axes[axis.code] = cal
        cal.detent = axis.value
        captured[axis.code] = axis.value
    return captured


def record(device_id: str, path: str, seconds: float = 8.0) -> DeviceCalibration:
    """Read a device for ``seconds`` and build a calibration from what moved.

    The caller should move every axis through its full travel and press
    every button/hat during the window.
    """
    from . import capabilities  # local import keeps evdev optional
    from .capabilities import _HAS_EVDEV

    if not _HAS_EVDEV:
        raise RuntimeError("python-evdev is required (Linux only).")
    import evdev
    from evdev import ecodes

    caps = capabilities.describe(path)
    axis_names = {a.code: a.name for a in caps.axes}
    is_hat = {a.code: a.is_hat for a in caps.axes}

    # Seed ranges with the driver-reported absinfo, then widen with observed.
    cal = DeviceCalibration(device_id=device_id)
    for a in caps.analog_axes:
        cal.axes[a.code] = AxisCalibration(
            code=a.code, name=a.name, raw_min=a.value, raw_max=a.value, center=a.value
        )

    dev = evdev.InputDevice(path)
    buttons: set[int] = set()
    hats: set[int] = set()
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        for ev in dev.read():
            if ev.type == ecodes.EV_ABS:
                if is_hat.get(ev.code):
                    if ev.value != 0:
                        hats.add(ev.code)
                    continue
                ax = cal.axes.get(ev.code)
                if ax is None:
                    ax = AxisCalibration(
                        code=ev.code,
                        name=axis_names.get(ev.code, ""),
                        raw_min=ev.value,
                        raw_max=ev.value,
                        center=ev.value,
                    )
                    cal.axes[ev.code] = ax
                ax.raw_min = min(ax.raw_min, ev.value)
                ax.raw_max = max(ax.raw_max, ev.value)
            elif ev.type == ecodes.EV_KEY and ev.value == 1:
                buttons.add(ev.code)
        time.sleep(0.01)

    # Resting position = current value after the user lets go.
    for ax in cal.axes.values():
        for a in caps.axes:
            if a.code == ax.code:
                ax.center = evdev.InputDevice(path).absinfo(ax.code).value
                break
    cal.buttons = sorted(buttons)
    cal.hats = sorted(hats)
    return cal


def kind_for_code(calibration: DeviceCalibration, code: int) -> SourceKind:
    if code in calibration.axes:
        return SourceKind.AXIS
    if code in calibration.hats:
        return SourceKind.HAT
    return SourceKind.BUTTON
