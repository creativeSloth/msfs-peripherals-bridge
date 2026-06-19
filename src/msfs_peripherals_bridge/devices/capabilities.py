"""Inspect connected evdev devices: axes, buttons and hat switches.

Used by the ``scan`` CLI command to enumerate hardware and discover the
real USB ids of devices that are not in the catalog yet (e.g. the Fulcrum
yoke, whose ids are placeholders).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

try:  # pragma: no cover - Linux + evdev only
    import evdev
    from evdev import ecodes

    _HAS_EVDEV = True
except ImportError:  # pragma: no cover
    _HAS_EVDEV = False


@dataclass(slots=True)
class AxisInfo:
    code: int
    name: str
    min: int
    max: int
    flat: int
    fuzz: int
    value: int

    @property
    def is_hat(self) -> bool:
        return self.name.startswith("ABS_HAT")


@dataclass(slots=True)
class DeviceCaps:
    path: str
    name: str
    vendor: str
    product: str
    axes: list[AxisInfo] = field(default_factory=list)
    buttons: list[tuple[int, str]] = field(default_factory=list)

    @property
    def hats(self) -> list[AxisInfo]:
        return [a for a in self.axes if a.is_hat]

    @property
    def analog_axes(self) -> list[AxisInfo]:
        return [a for a in self.axes if not a.is_hat]

    @property
    def usb(self) -> str:
        return f"{self.vendor}:{self.product}"

    @property
    def looks_like_controller(self) -> bool:
        """Heuristic: has absolute axes and joystick/gamepad-style buttons."""
        if not self.axes:
            return False
        return any(
            name.startswith(("BTN_JOYSTICK", "BTN_GAMEPAD", "BTN_TRIGGER", "BTN_"))
            for _, name in self.buttons
        )


def _first_name(value: object, fallback: str) -> str:
    """evdev maps a code to a name that may be a str, list or tuple of aliases."""
    if value is None:
        return fallback
    if isinstance(value, (list, tuple)):
        return str(value[0]) if value else fallback
    return str(value)


def _key_name(code: int) -> str:
    return _first_name(ecodes.bytype[ecodes.EV_KEY].get(code), f"KEY_{code}")


def _abs_name(code: int) -> str:
    return _first_name(ecodes.ABS.get(code), f"ABS_{code}")


def describe(path: str) -> DeviceCaps:
    """Read full capabilities of a single /dev/input/eventX device."""
    if not _HAS_EVDEV:
        raise RuntimeError("python-evdev is required (Linux only).")
    dev = evdev.InputDevice(path)
    caps = DeviceCaps(
        path=path,
        name=dev.name,
        vendor=f"{dev.info.vendor:04x}",
        product=f"{dev.info.product:04x}",
    )
    capabilities = dev.capabilities(absinfo=True)
    # The absinfo=True variant yields (code, AbsInfo) pairs for EV_ABS, which the
    # evdev stub types only as list[int]; cast to the real runtime shape.
    abs_caps = cast("list[tuple[int, Any]]", capabilities.get(ecodes.EV_ABS, []))
    for code, absinfo in abs_caps:
        caps.axes.append(
            AxisInfo(
                code=code,
                name=_abs_name(code),
                min=absinfo.min,
                max=absinfo.max,
                flat=absinfo.flat,
                fuzz=absinfo.fuzz,
                value=absinfo.value,
            )
        )
    key_caps: list[int] = capabilities.get(ecodes.EV_KEY, [])
    for code in key_caps:
        caps.buttons.append((code, _key_name(code)))
    return caps


def scan() -> list[DeviceCaps]:
    """Describe every connected input device that looks like a controller."""
    if not _HAS_EVDEV:
        raise RuntimeError("python-evdev is required (Linux only).")
    result: list[DeviceCaps] = []
    for path in sorted(evdev.list_devices()):
        caps = describe(path)
        if caps.looks_like_controller:
            result.append(caps)
    return result
