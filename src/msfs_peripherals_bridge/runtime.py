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
from .models import DeviceCatalog, Profile, SourceKind
from .simconnect.protocol import Command

if TYPE_CHECKING:
    from .outputs import OutputManager

log = logging.getLogger(__name__)

# A hidraw switch can report several enter edges when its contacts bounce; on a
# momentary *toggle* button (e.g. AP master) an even number of fires nets no
# change, so a dirty press looks dead and you have to press again. The window is
# retriggerable: every enter edge — even a suppressed one — pushes it forward, so
# a whole bounce burst collapses to one action as long as the flicker stays
# quicker than this. Deliberate re-presses of the same button come far slower.
# Detents/other buttons are keyed separately; the encoder/selector bypass this.
_SWITCH_DEBOUNCE_S = 0.12


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
    last_press: dict[tuple[str, int], float] = {}
    while not stop.is_set():
        try:
            event = events.get(timeout=0.5)
        except queue.Empty:
            continue
        # The Multi Panel's selector/encoder are owned by its controller (display
        # + value state); everything else goes through the stateless engine.
        if outputs is not None and outputs.handles(event.device_id, event.code):
            commands = outputs.handle_input(event.device_id, event.code, event.value)
        else:
            if _bounced(event, last_press):
                continue
            commands = engine.resolve(event)
        for command in commands:
            dispatcher.send(command)


def _bounced(
    event: DeviceEvent,
    last_press: dict[tuple[str, int], float],
    now: float | None = None,
) -> bool:
    """True if this is a hidraw switch enter edge too soon after the last one.

    Suppresses contact-bounce double-fires on momentary panel buttons (see
    ``_SWITCH_DEBOUNCE_S``). Only enter edges (value 1) of SWITCH events are
    rate-limited; everything else passes straight through. The window is
    retriggerable: the timestamp advances on *every* enter edge, suppressed ones
    included, so a sustained bounce burst is collapsed rather than letting a late
    edge slip through as a second toggle. ``now`` is injectable for tests.
    """
    if event.kind is not SourceKind.SWITCH or event.value != 1:
        return False
    key = (event.device_id, event.code)
    now = time.monotonic() if now is None else now
    prev = last_press.get(key)
    last_press[key] = now
    return prev is not None and (now - prev) < _SWITCH_DEBOUNCE_S


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
