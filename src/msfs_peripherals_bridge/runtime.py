"""Glue the pieces together: read devices, resolve mappings, send commands.

This module wires the device readers to the mapping engine and the bridge
client. Device reading is blocking per device, so each device runs in its
own thread and pushes events onto a shared queue.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from typing import TYPE_CHECKING, Protocol

from .devices import evdev_reader, hidraw_reader
from .devices.base import DeviceEvent
from .mapping.engine import MappingEngine
from .models import DeviceCatalog, Profile
from .simconnect.protocol import Command

if TYPE_CHECKING:
    from .outputs import OutputManager

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

    present = {**evdev_reader.discover(catalog), **hidraw_reader.discover(catalog)}
    if not present:
        raise RuntimeError("None of the catalog devices were found on this system.")

    outputs = _start_outputs(profile, present, dispatcher, stop)

    for device_id, path in present.items():
        if device_id not in profile.bindings:
            log.warning(
                "Device %s present but has no bindings in profile '%s'", device_id, profile.name
            )
        definition = catalog.by_id(device_id)
        transport = definition.transport if definition is not None else "evdev"
        threading.Thread(
            target=_pump, args=(device_id, path, transport, events, stop), daemon=True
        ).start()

    log.info("Mapping loop started for profile '%s' (%d devices)", profile.name, len(present))
    while not stop.is_set():
        try:
            event = events.get(timeout=0.5)
        except queue.Empty:
            continue
        # The Multi Panel's selector/encoder are owned by its controller (display
        # + value state); everything else goes through the stateless engine.
        if outputs is not None and outputs.handles(event.device_id, event.code):
            commands = outputs.handle_input(
                event.device_id, event.code, event.value, time.monotonic()
            )
        else:
            commands = engine.resolve(event)
        for command in commands:
            dispatcher.send(command)


def _start_outputs(
    profile: Profile,
    present: dict[str, str],
    dispatcher: Dispatcher,
    stop: threading.Event,
) -> OutputManager | None:
    """Start the output manager if the profile declares any outputs.

    Returns the manager (so the mapping loop can route Multi Panel selector/
    encoder input to it) or None. Needs a dispatcher that can stream SimVar state
    back (the real bridge); the dry-run dispatcher has no ``states()``, so outputs
    are simply skipped there.
    """
    output_devices = {d: p for d, p in present.items() if d in profile.outputs}
    if not output_devices:
        return None
    if not callable(getattr(dispatcher, "states", None)):
        log.info("Profile has outputs but the dispatcher can't stream state; outputs disabled.")
        return None

    from .outputs import OutputManager

    manager = OutputManager(profile.outputs, output_devices, dispatcher)
    threading.Thread(target=manager.run, args=(stop,), daemon=True).start()
    log.info("Output manager started for %d device(s)", len(output_devices))
    return manager


def _pump(
    device_id: str,
    path: str,
    transport: str,
    events: queue.Queue[DeviceEvent],
    stop: threading.Event,
) -> None:
    reader = hidraw_reader if transport == "hidraw" else evdev_reader
    try:
        for event in reader.read_device(device_id, path):
            events.put(event)
            if stop.is_set():
                return
    except OSError as exc:  # device unplugged etc.
        log.error("Reader for %s stopped: %s", device_id, exc)
