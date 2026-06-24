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


def _kind_for(ev_type: int) -> SourceKind | None:
    if ev_type == ecodes.EV_ABS:
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


def read_device(device_id: str, path: str) -> Iterator[DeviceEvent]:
    """Blocking generator of normalised events from one device node."""
    if not _HAS_EVDEV:
        raise RuntimeError("python-evdev is required to read devices (Linux only).")
    dev = evdev.InputDevice(path)
    for ev in dev.read_loop():
        kind = _kind_for(ev.type)
        if kind is None:
            continue
        yield DeviceEvent(device_id=device_id, kind=kind, code=ev.code, value=ev.value)
