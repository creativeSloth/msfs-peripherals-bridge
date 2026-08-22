"""Glue the pieces together: read devices, resolve mappings, send commands.

This module wires the device readers to the mapping engine and the bridge
client. Device reading is blocking per device, so each device runs in its
own thread and pushes events onto a shared queue.
"""

from __future__ import annotations

import contextlib
import logging
import queue
import threading
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol, cast

from .devices import evdev_reader, hidraw_reader
from .devices.base import DeviceEvent
from .mapping.engine import MappingEngine
from .models import DeviceCatalog, Profile, SourceKind
from .simconnect.protocol import Command

if TYPE_CHECKING:
    from .outputs import OutputManager, StateDispatcher

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


class ConditionWatcher:
    """Thread-safe latest-value store for the ``when:`` condition variables.

    Values arrive from the bridge's state stream (either as a tap on the
    OutputManager, which owns the socket's ``states()`` iterator, or via a
    dedicated reader thread when the profile has no outputs). The engine reads
    through :meth:`get`; unknown names return ``None`` = condition not met.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._values: dict[str, object] = {}

    def update(self, name: str, value: object) -> None:
        with self._lock:
            self._values[name] = value

    def get(self, name: str) -> object:
        with self._lock:
            return self._values.get(name)


def condition_vars(profile: Profile) -> set[str]:
    """Every variable referenced by a ``when:`` condition in the profile."""
    return {
        cond.var
        for bindings in profile.bindings.values()
        for binding in bindings
        for cond in binding.when
    }


def seed_local_vars(profile: Profile) -> list[Command]:
    """Commands seeding the profile's declared V: locals with their initials.

    Sent once at mapper start (the bridge holds the values in its V: hub, the
    profile stays the single source of the declarations). Restarting the mapper
    re-seeds — persistence across restarts is the LocalVar.persist follow-up.
    """
    from .simconnect.protocol import SetSimVar

    return [
        SetSimVar(name=f"V:{lv.name}", unit=lv.unit, value=lv.initial) for lv in profile.local_vars
    ]


def run(
    profile: Profile,
    catalog: DeviceCatalog,
    dispatcher: Dispatcher,
    stop: threading.Event | None = None,
) -> None:
    """Run the mapping loop until ``stop`` is set (or KeyboardInterrupt)."""
    stop = stop or threading.Event()
    events: queue.Queue[DeviceEvent] = queue.Queue(maxsize=1024)

    present = {**evdev_reader.discover(catalog), **hidraw_reader.discover(catalog)}
    if not present:
        raise RuntimeError("None of the catalog devices were found on this system.")

    # Seed declared V: locals BEFORE conditions/outputs subscribe, so a gate on
    # a local variable sees its initial value instead of an unknown (=blocked).
    for command in seed_local_vars(profile):
        dispatcher.send(command)
    if profile.local_vars:
        log.info("Seeded %d local V: variable(s)", len(profile.local_vars))

    watcher = _start_conditions(profile, present, dispatcher, stop)
    engine = MappingEngine(profile, values=watcher.get if watcher else None)
    outputs = _start_outputs(
        profile, present, dispatcher, stop, state_listener=watcher.update if watcher else None
    )

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
            first = events.get(timeout=0.5)
        except queue.Empty:
            continue
        # A moving yoke/rudder floods evdev with hundreds of ABS samples a second,
        # and each one becomes a synchronous *_SET sent over the socket to a single
        # serialised SimConnect DLL — so the sim can't keep up, the queue backs up,
        # and the axis arrives lagged and stuttering. Drain the whole backlog this
        # pass and drop superseded axis samples, sending only the newest position
        # per axis. Buttons and switch edges are never dropped (see _coalesce_axes).
        for event in _coalesce_axes(_drain(events, first)):
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


def _drain(events: queue.Queue[DeviceEvent], first: DeviceEvent) -> list[DeviceEvent]:
    """``first`` plus every event already buffered on the queue.

    Lets one loop pass see the whole backlog at once so :func:`_coalesce_axes`
    can collapse a burst of axis samples instead of the loop handling (and
    sending) each one individually.
    """
    batch = [first]
    while True:
        try:
            batch.append(events.get_nowait())
        except queue.Empty:
            return batch


def _coalesce_axes(batch: list[DeviceEvent]) -> list[DeviceEvent]:
    """Keep only the newest sample per (device, axis); pass everything else through.

    A yoke/rudder emits far more axis samples than the sim can consume, and every
    intermediate position is superseded the instant the next arrives — forwarding
    them all just backs the pipeline up and makes the axis stutter. Collapsing a
    batch to the last reading per axis sends the current position and drops the
    stale ones. Non-axis events (buttons, switch edges, encoder detents) are never
    dropped and keep their order: each edge means something a later one can't undo.
    """
    last_index: dict[tuple[str, int], int] = {}
    for i, event in enumerate(batch):
        if event.kind is SourceKind.AXIS:
            last_index[(event.device_id, event.code)] = i
    return [
        event
        for i, event in enumerate(batch)
        if event.kind is not SourceKind.AXIS or last_index[(event.device_id, event.code)] == i
    ]


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


def _start_conditions(
    profile: Profile,
    present: dict[str, str],
    dispatcher: Dispatcher,
    stop: threading.Event,
) -> ConditionWatcher | None:
    """Subscribe the ``when:`` condition vars and keep their latest values.

    Values ride on the same state stream the outputs use. When an OutputManager
    will run, it taps its ``on_state`` into the watcher (it owns the socket's
    ``states()`` iterator); without outputs a small reader thread consumes the
    stream here. A dispatcher that can't stream (dry-run) leaves the store
    empty, so gated bindings stay off — fail-closed, and loudly logged.
    """
    names = condition_vars(profile)
    if not names:
        return None
    watcher = ConditionWatcher()
    if not callable(getattr(dispatcher, "states", None)):
        log.warning(
            "Profile has when: conditions but this dispatcher can't stream state; "
            "gated bindings will stay OFF."
        )
        return watcher
    from .simconnect.protocol import Subscribe

    for name in sorted(names):
        dispatcher.send(Subscribe(name=name))
        log.info("Condition subscribed to %s", name)
    if not any(d in profile.outputs for d in present):

        def _pump_states() -> None:
            with contextlib.suppress(Exception):  # socket closes on shutdown
                for name, value in dispatcher.states():  # type: ignore[attr-defined]
                    if stop.is_set():
                        return
                    watcher.update(name, value)

        threading.Thread(target=_pump_states, name="conditions", daemon=True).start()
    return watcher


def _start_outputs(
    profile: Profile,
    present: dict[str, str],
    dispatcher: Dispatcher,
    stop: threading.Event,
    state_listener: Callable[[str, object], None] | None = None,
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

    manager = OutputManager(
        profile.outputs,
        output_devices,
        cast("StateDispatcher", dispatcher),
        state_listener=state_listener,
    )
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
