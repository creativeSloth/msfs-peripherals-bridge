"""Glue the pieces together: read devices, resolve mappings, send commands.

This module wires the device readers to the mapping engine and the bridge
client. Device reading is blocking per device, so each device runs in its
own thread and pushes events onto a shared queue.
"""

from __future__ import annotations

import logging
import queue
import threading
from typing import Protocol

from .devices import evdev_reader
from .devices.base import DeviceEvent
from .mapping.engine import MappingEngine
from .models import DeviceCatalog, Profile
from .simconnect.protocol import Command

log = logging.getLogger(__name__)


class Dispatcher(Protocol):
    """Anything that can accept resolved commands (real bridge or dry-run)."""

    def send(self, command: Command) -> None: ...


def run(
    profile: Profile,
    catalog: DeviceCatalog,
    dispatcher: Dispatcher,
    stop: threading.Event | None = None,
) -> None:
    """Run the mapping loop until ``stop`` is set (or KeyboardInterrupt)."""
    stop = stop or threading.Event()
    engine = MappingEngine(profile)
    events: queue.Queue[DeviceEvent] = queue.Queue(maxsize=1024)

    present = evdev_reader.discover(catalog)
    if not present:
        raise RuntimeError("None of the catalog devices were found on this system.")

    for device_id, path in present.items():
        if device_id not in profile.bindings:
            log.warning(
                "Device %s present but has no bindings in profile '%s'", device_id, profile.name
            )
        threading.Thread(target=_pump, args=(device_id, path, events, stop), daemon=True).start()

    log.info("Mapping loop started for profile '%s' (%d devices)", profile.name, len(present))
    while not stop.is_set():
        try:
            event = events.get(timeout=0.5)
        except queue.Empty:
            continue
        for command in engine.resolve(event):
            dispatcher.send(command)


def _pump(
    device_id: str, path: str, events: queue.Queue[DeviceEvent], stop: threading.Event
) -> None:
    try:
        for event in evdev_reader.read_device(device_id, path):
            events.put(event)
            if stop.is_set():
                return
    except OSError as exc:  # device unplugged etc.
        log.error("Reader for %s stopped: %s", device_id, exc)
