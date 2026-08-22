"""Enumerate *all* connected USB HID / joystick devices — not just the catalog.

The catalog-bound ``discover()`` in :mod:`evdev_reader` / :mod:`hidraw_reader`
only returns devices that are already registered in ``config/devices.yaml``. The
device explorer needs to see **unregistered** hardware too, so a stranger can
plug a device in and actually find it (its USB id + name) before registering it.

Split for testability:

* :func:`classify` is **pure** — a list of :class:`RawDevice` plus a catalog in,
  a deduped, tagged list of :class:`InventoryItem` out — and is unit-tested.
* :func:`enumerate_raw` does the Linux-only I/O (evdev + ``/sys/class/hidraw``).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from ..models import DeviceCatalog, DeviceDef

_SYS_HIDRAW = "/sys/class/hidraw"


@dataclass(frozen=True, slots=True)
class RawDevice:
    """One connected input node as the OS sees it, before catalog matching."""

    vendor: int
    product: int
    name: str
    transport: str  # "evdev" | "hidraw"
    path: str

    @property
    def usb(self) -> str:
        return f"{self.vendor:04x}:{self.product:04x}"


@dataclass(slots=True)
class InventoryItem:
    """A physical device (deduped across its nodes), tagged registered-or-not."""

    vendor: int
    product: int
    name: str
    transport: str
    paths: list[str] = field(default_factory=list)
    catalog_id: str | None = None

    @property
    def registered(self) -> bool:
        return self.catalog_id is not None

    @property
    def usb(self) -> str:
        return f"{self.vendor:04x}:{self.product:04x}"


def _matches(raw: RawDevice, d: DeviceDef) -> bool:
    """True if a raw node is this catalog device (same transport, USB, name)."""
    if d.transport != raw.transport:
        return False
    if d.usb_key != (raw.vendor, raw.product):
        return False
    if d.name_match:
        return d.name_match.lower() in (raw.name or "").lower()
    return True


def classify(raws: list[RawDevice], catalog: DeviceCatalog) -> list[InventoryItem]:
    """Group raw nodes into physical devices, tag catalog registration. Pure.

    * Registered devices collapse by catalog id (all their nodes → one row).
    * Unregistered devices group by (USB id, transport, name), so two distinct
      ``0000:0000`` devices (e.g. the Fulcrum yoke vs. audio nodes) stay apart.
    * A hidraw panel also exposes a useless evdev node; that evdev shadow is
      dropped so the panel shows up once (as its hidraw entry), mirroring
      :func:`evdev_reader.discover`.
    """
    hidraw_usb = {d.usb_key for d in catalog.devices if d.transport == "hidraw"}
    items: dict[tuple[object, ...], InventoryItem] = {}
    order: list[tuple[object, ...]] = []
    for raw in raws:
        if raw.transport == "evdev" and (raw.vendor, raw.product) in hidraw_usb:
            # The panel's evdev shadow — it is meant to be read via hidraw.
            continue
        match = next((d for d in catalog.devices if _matches(raw, d)), None)
        if match is not None:
            key: tuple[object, ...] = ("id", match.id)
        else:
            key = ("raw", raw.vendor, raw.product, raw.transport, raw.name)
        item = items.get(key)
        if item is None:
            item = InventoryItem(
                vendor=raw.vendor,
                product=raw.product,
                name=(match.name if match else raw.name),
                transport=raw.transport,
                catalog_id=(match.id if match else None),
            )
            items[key] = item
            order.append(key)
        if raw.path not in item.paths:
            item.paths.append(raw.path)
    result = [items[k] for k in order]
    # Registered first, then unregistered; each alphabetical by name, then USB.
    result.sort(key=lambda it: (it.catalog_id is None, it.name.lower(), it.usb))
    return result


def _enumerate_evdev() -> list[RawDevice]:  # pragma: no cover - evdev I/O
    """Controller-like evdev nodes (reuses the ``scan`` heuristic)."""
    from . import capabilities

    try:
        caps = capabilities.scan()
    except RuntimeError:
        return []
    return [RawDevice(int(c.vendor, 16), int(c.product, 16), c.name, "evdev", c.path) for c in caps]


def _enumerate_hidraw() -> list[RawDevice]:  # pragma: no cover - sysfs I/O
    """Every ``/dev/hidrawN`` node with its USB id + HID name from sysfs."""
    out: list[RawDevice] = []
    try:
        nodes = sorted(os.listdir(_SYS_HIDRAW))
    except OSError:
        return out
    for node in nodes:
        vendor: int | None = None
        product: int | None = None
        name = ""
        try:
            with open(f"{_SYS_HIDRAW}/{node}/device/uevent", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line.startswith("HID_ID="):
                        # HID_ID=bus:vendor:product (hex), e.g. 0003:000006A3:00000D67
                        _, v, p = line.split("=", 1)[1].split(":")
                        vendor, product = int(v, 16), int(p, 16)
                    elif line.startswith("HID_NAME="):
                        name = line.split("=", 1)[1]
        except OSError:
            continue
        if vendor is None or product is None:
            continue
        out.append(RawDevice(vendor, product, name, "hidraw", f"/dev/{node}"))
    return out


def enumerate_raw() -> list[RawDevice]:  # pragma: no cover - thin I/O wrapper
    """All connected controller-like evdev nodes plus all hidraw nodes."""
    return _enumerate_evdev() + _enumerate_hidraw()


def inventory(catalog: DeviceCatalog) -> list[InventoryItem]:
    """Every connected device, deduped and tagged registered-or-not."""
    return classify(enumerate_raw(), catalog)
