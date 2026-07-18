"""Read Linux evdev devices and emit normalised DeviceEvents.

Depends on python-evdev, which is Linux-only. The import is wrapped so the
rest of the package (models, engine, transforms) stays importable on any
platform and in CI for the pure-logic tests.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator

from ..models import DeviceCatalog, SourceKind
from .base import DeviceEvent

log = logging.getLogger(__name__)

try:  # pragma: no cover - exercised only on Linux with evdev installed
    import evdev
    from evdev import ecodes

    _HAS_EVDEV = True
except ImportError:  # pragma: no cover
    _HAS_EVDEV = False


def _kind_for(ev_type: int, code: int) -> SourceKind | None:
    if ev_type == ecodes.EV_ABS:
        # POV hats are ABS channels too (ABS_HAT0X..ABS_HAT3Y, ±1) — classify
        # them as HAT so direction-aware hat bindings can match them.
        if ecodes.ABS_HAT0X <= code <= ecodes.ABS_HAT3Y:
            return SourceKind.HAT
        return SourceKind.AXIS
    if ev_type == ecodes.EV_KEY:
        return SourceKind.BUTTON
    return None


def discover(catalog: DeviceCatalog) -> dict[str, str]:
    """Return {device_id: /dev/input/eventX} for catalog devices present now."""
    if not _HAS_EVDEV:
        raise RuntimeError("python-evdev is required to read devices (Linux only).")
    found: dict[str, str] = {}
    for path in evdev.list_devices():
        dev = evdev.InputDevice(path)
        for definition in catalog.devices:
            if definition.transport != "evdev" or definition.id in found:
                # hidraw panels also expose a (useless) evdev node; skip them so
                # only the hidraw reader claims them.
                continue
            if definition.matches(dev.info.vendor, dev.info.product, dev.name):
                found[definition.id] = path
                log.info("Found %s at %s", definition.id, path)
                break
    return found


def axis_value_reader(path: str, code: int):
    """Open ``path`` and return a zero-arg callable giving that axis's live raw value.

    Used by the GUI's "learn raw range": the callable polls the axis's current
    ``absinfo().value`` so the user can read the value at the detent / at the
    extremes and capture it. Returns ``None`` if evdev is unavailable or the
    device can't be opened; the callable returns ``None`` if a later read fails.
    """
    if not _HAS_EVDEV:
        return None
    try:
        dev = evdev.InputDevice(path)
    except OSError:
        return None

    def read() -> int | None:
        try:
            return dev.absinfo(code).value
        except (OSError, KeyError):
            return None

    return read


def read_device(device_id: str, path: str) -> Iterator[DeviceEvent]:
    """Blocking generator of normalised events from one device node."""
    if not _HAS_EVDEV:
        raise RuntimeError("python-evdev is required to read devices (Linux only).")
    dev = evdev.InputDevice(path)
    for ev in dev.read_loop():
        kind = _kind_for(ev.type, ev.code)
        if kind is None:
            continue
        yield DeviceEvent(device_id=device_id, kind=kind, code=ev.code, value=ev.value)


def live_state_reader(path: str):
    """Open ``path`` for the GUI's live view; ``(read, ranges)`` or ``None``.

    ``read()`` drains all pending events non-blocking and returns the current
    ``{("axis"|"button", code): value}`` state (axes seeded from ``absinfo`` so
    bars render before the first movement), or ``None`` once the device is gone.
    ``ranges`` maps axis code -> (min, max) for scaling the bars.
    """
    if not _HAS_EVDEV:
        return None
    try:
        dev = evdev.InputDevice(path)
        caps = dev.capabilities().get(ecodes.EV_ABS, [])
    except OSError:
        return None
    state: dict[tuple[str, int], int] = {
        ("axis", code): absinfo.value for code, absinfo in caps
    }
    ranges = {code: (absinfo.min, absinfo.max) for code, absinfo in caps}

    def read() -> dict[tuple[str, int], int] | None:
        try:
            while True:
                ev = dev.read_one()
                if ev is None:
                    return state
                if ev.type == ecodes.EV_ABS:
                    state[("axis", ev.code)] = ev.value
                elif ev.type == ecodes.EV_KEY:
                    state[("button", ev.code)] = ev.value
        except BlockingIOError:
            return state
        except OSError:
            return None  # unplugged

    return read, ranges
