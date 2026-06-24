"""Read raw HID report frames from Saitek-style panels into DeviceEvents.

The Saitek Pro Flight panels are not joysticks: they expose a small fixed-length
input report whose bits are switch/rotary states, plus (on some panels) an LED
output report. They are reached through ``/dev/hidraw`` rather than evdev.

This reader diffs successive input reports and emits one ``DeviceEvent`` per
changed bit, with ``kind = SWITCH`` and ``code = byte_index * 8 + bit`` (the
"global bit index"). Both edges are reported (value 1 = bit set, 0 = cleared);
the mapping engine decides whether a binding cares about one edge or both.

Linux-only (``/sys/class/hidraw`` + ``/dev/hidraw``). Imported lazily by the
runtime so the pure-logic package stays importable on any platform.
"""

from __future__ import annotations

import logging
import os
import select
from collections.abc import Iterator

from ..models import DeviceCatalog, SourceKind
from .base import DeviceEvent

log = logging.getLogger(__name__)

_SYS_HIDRAW = "/sys/class/hidraw"


def _usb_ids(node: str) -> tuple[int, int] | None:
    """Return (vendor, product) for a hidraw node from its sysfs uevent."""
    try:
        with open(f"{_SYS_HIDRAW}/{node}/device/uevent", encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return None
    for line in text.splitlines():
        if line.startswith("HID_ID="):
            # HID_ID=0003:000006A3:00000D67  (bus:vendor:product, hex)
            _, vendor, product = line.split("=", 1)[1].split(":")
            return int(vendor, 16), int(product, 16)
    return None


def discover(catalog: DeviceCatalog) -> dict[str, str]:
    """Return {device_id: /dev/hidrawN} for hidraw catalog devices present now."""
    found: dict[str, str] = {}
    try:
        nodes = sorted(os.listdir(_SYS_HIDRAW))
    except OSError:  # pragma: no cover - no hidraw subsystem at all
        return found
    for node in nodes:
        ids = _usb_ids(node)
        if ids is None:
            continue
        for definition in catalog.devices:
            if definition.transport != "hidraw" or definition.id in found:
                continue
            if definition.usb_key == ids:
                path = f"/dev/{node}"
                found[definition.id] = path
                log.info("Found %s at %s", definition.id, path)
                break
    return found


def iter_bit_changes(device_id: str, prev: bytes, cur: bytes) -> Iterator[DeviceEvent]:
    """Yield one SWITCH event per bit that differs between two report frames."""
    for byte_index in range(max(len(prev), len(cur))):
        p = prev[byte_index] if byte_index < len(prev) else 0
        c = cur[byte_index] if byte_index < len(cur) else 0
        diff = p ^ c
        if not diff:
            continue
        for bit in range(8):
            mask = 1 << bit
            if diff & mask:
                yield DeviceEvent(
                    device_id=device_id,
                    kind=SourceKind.SWITCH,
                    code=byte_index * 8 + bit,
                    value=1 if c & mask else 0,
                )


def read_device(device_id: str, path: str) -> Iterator[DeviceEvent]:
    """Blocking generator of bit-change events from one hidraw panel.

    The first report after opening only primes the baseline (no events): the
    panel stays silent until something moves, so its first frame carries the
    *current* state of every switch. Emitting those would fire unrelated
    controls (e.g. retract the gear) the moment the user flips one switch, so we
    swallow the priming frame and report only genuine changes afterwards.
    """
    fd = os.open(path, os.O_RDONLY)
    prev: bytes | None = None
    try:
        while True:
            select.select([fd], [], [])
            data = os.read(fd, 64)
            if not data:
                continue
            if prev is None:
                prev = data
                continue
            yield from iter_bit_changes(device_id, prev, data)
            prev = data
    finally:
        os.close(fd)
