"""Drive panel outputs from SimVars streamed by the bridge.

The mapping engine is one-directional (device -> sim). Outputs are the reverse:
subscribe to the SimVars an output needs, consume the ``state`` updates the
bridge streams back on the *same* socket, render them to a HID feature report
and write it to the panel.

Two kinds of output live here:

* **Gear LEDs** (switch panel) — pure one-way: SimVar state -> one feature byte.
* **Stateful panel controllers** (Multi Panel, Radio Panel) — whose display/LEDs
  depend on both SimVar state *and* device input (selector + encoder). Their state
  is touched from two threads — the output thread (``on_state``) and the mapping
  loop (``handle_input``) — so all controller access is guarded by one lock. Both
  expose the same interface (:class:`PanelController`), so they route uniformly.

Kept separate from ``runtime`` so the render/track logic can be unit-tested with
a fake dispatcher and a fake writer (no socket, no hardware).
"""

from __future__ import annotations

import contextlib
import logging
import threading
from collections.abc import Callable, Iterator
from typing import Protocol

from .devices.hidraw_reader import write_feature_report
from .mapping.leds import gear_led_byte
from .mapping.multi_panel import MultiPanelController
from .mapping.radio_panel import RadioPanelController
from .models import GearLedOutput, MultiPanelOutput, Output, RadioPanelOutput
from .simconnect.protocol import Command, ReadNow, Subscribe

log = logging.getLogger(__name__)

# Switch-panel LED feature report: report id 0, then one data byte.
_REPORT_ID = 0x00

# Blink phase half-period: a blinking LED (the OMNI-mode IAS light) toggles every
# this-many seconds, so a full on/off cycle is ~1 s (1 Hz).
_BLINK_HALF_PERIOD = 0.5

# Delay before a post-input ReadNow, so the sim has applied the event we just fired
# (it processes client events on its next frame). ~90 ms is a few frames — instant
# to the eye, still far under the 1 s poll. A burst of detents coalesces to one
# ReadNow this-long after the last one (see _schedule_refresh).
_REFRESH_DELAY = 0.09


def _default_schedule(delay: float, fn: Callable[[], None]) -> None:
    """Run ``fn`` after ``delay`` seconds on a daemon timer (real-clock default)."""
    timer = threading.Timer(delay, fn)
    timer.daemon = True
    timer.start()


class StateDispatcher(Protocol):
    """A dispatcher that can both send commands and stream SimVar state back."""

    def send(self, command: Command) -> None: ...
    def states(self) -> Iterator[tuple[str, object]]: ...


class PanelController(Protocol):
    """A stateful panel controller (Multi Panel / Radio Panel) the manager drives.

    Both own display/input state and expose this shared interface, so the output
    manager tracks and renders them uniformly. ``render`` takes the shared blink
    phase (a controller with no blinking LED just ignores it).
    """

    def subscriptions(self) -> list[str]: ...
    def consumes(self, code: int) -> bool: ...
    def on_event(self, code: int, value: int) -> list[Command]: ...
    def refresh_after(self, code: int) -> list[str]: ...
    def on_state(self, name: str, value: object) -> None: ...
    def render(self, blink_on: bool = ...) -> bytes: ...


def _as_float(value: object) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


class OutputManager:
    """Tracks SimVar values and writes panel feature reports when they change."""

    def __init__(
        self,
        outputs: dict[str, list[Output]],
        device_paths: dict[str, str],
        dispatcher: StateDispatcher,
        writer: Callable[[str, bytes], None] = write_feature_report,
        schedule: Callable[[float, Callable[[], None]], None] = _default_schedule,
    ) -> None:
        self._paths = device_paths
        self._dispatcher = dispatcher
        self._writer = writer
        self._schedule = schedule
        self._lock = threading.Lock()
        self._values: dict[str, float | None] = {}
        self._last_report: dict[str, bytes] = {}  # device_id -> last bytes written
        self._blink_on = True  # shared blink phase, flipped by the blink ticker
        self._stop: threading.Event | None = None  # set in run(), gates late refreshes
        # Coalesced post-input ReadNow (B2 low-latency echo): pending var names +
        # a generation counter so only the last-armed timer of a burst flushes.
        self._refresh_lock = threading.Lock()
        self._refresh_pending: set[str] = set()
        self._refresh_gen = 0
        # Split outputs by kind, keeping only devices that are actually present.
        self._gear: dict[str, list[GearLedOutput]] = {}
        self._controllers: dict[str, PanelController] = {}
        # Off-panel buttons routed to a controller action: (device, code) ->
        # (controller's device_id, controller). E.g. a yoke rocker toggling CRS.
        self._aux: dict[tuple[str, int], tuple[str, MultiPanelController]] = {}
        for device_id, outs in outputs.items():
            if device_id not in device_paths:
                continue
            for output in outs:
                if isinstance(output, MultiPanelOutput):
                    controller = MultiPanelController(output)
                    self._controllers[device_id] = controller
                    if output.source_toggle is not None:
                        tog = output.source_toggle
                        self._aux[(tog.device, tog.code)] = (device_id, controller)
                elif isinstance(output, RadioPanelOutput):
                    self._controllers[device_id] = RadioPanelController(output)
                elif isinstance(output, GearLedOutput):
                    self._gear.setdefault(device_id, []).append(output)

    @property
    def _devices(self) -> set[str]:
        return set(self._gear) | set(self._controllers)

    def needed_simvars(self) -> set[str]:
        names: set[str] = set()
        for outs in self._gear.values():
            for output in outs:
                names.update(output.simvars())
        for controller in self._controllers.values():
            names.update(controller.subscriptions())
        return names

    def subscribe_all(self) -> None:
        for name in sorted(self.needed_simvars()):
            self._dispatcher.send(Subscribe(name))
            log.debug("Output subscribed to %s", name)

    # -- input (mapping loop thread) ---------------------------------------
    def handles(self, device_id: str, code: int) -> bool:
        """True if this input is consumed by a controller (its panel or an aux toggle)."""
        if (device_id, code) in self._aux:
            return True
        controller = self._controllers.get(device_id)
        return controller is not None and controller.consumes(code)

    def handle_input(self, device_id: str, code: int, value: int) -> list[Command]:
        """Feed a selector/encoder/aux event to the controller; rewrite its report."""
        aux = self._aux.get((device_id, code))
        if aux is not None:
            panel_id, controller = aux
            if value == 1:  # off-panel toggle: act on the press edge only
                with self._lock:
                    controller.toggle_source()
                    self._write_if_changed(panel_id)
            return []
        controller = self._controllers.get(device_id)
        if controller is None:
            return []
        with self._lock:
            commands = controller.on_event(code, value)
            self._write_if_changed(device_id)
            # Snapshot the vars to re-read under the same lock (consistent selection);
            # only when the input actually acted, so a dropped/idempotent one is quiet.
            refresh = controller.refresh_after(code) if commands else []
        self._schedule_refresh(refresh)
        return commands

    def _schedule_refresh(self, names: list[str]) -> None:
        """Arm a coalesced ReadNow for ``names`` after ``_REFRESH_DELAY``.

        A generation counter collapses a burst of detents into a single flush: each
        call re-arms, and only the timer carrying the latest generation flushes (the
        earlier ones fire, see they are superseded, and drop out).
        """
        if not names:
            return
        with self._refresh_lock:
            self._refresh_pending.update(names)
            self._refresh_gen += 1
            gen = self._refresh_gen
        self._schedule(_REFRESH_DELAY, lambda: self._flush_refresh(gen))

    def _flush_refresh(self, gen: int) -> None:
        if self._stop is not None and self._stop.is_set():
            return
        with self._refresh_lock:
            if gen != self._refresh_gen:
                return  # a later detent re-armed; its timer will flush the pending set
            names = sorted(self._refresh_pending)
            self._refresh_pending = set()
        for name in names:
            # A missed refresh only costs one poll of extra display lag, never state,
            # so a send failing on a shutting-down socket is not worth surfacing.
            with contextlib.suppress(OSError):
                self._dispatcher.send(ReadNow(name))

    # -- output (bridge state thread) --------------------------------------
    def on_state(self, name: str, value: object) -> None:
        """Record a SimVar update and rewrite any device whose report changed."""
        with self._lock:
            self._values[name] = _as_float(value)
            for controller in self._controllers.values():
                controller.on_state(name, value)
            for device_id in self._devices:
                self._write_if_changed(device_id)

    def _write_if_changed(self, device_id: str) -> None:
        """Render and write a device's report if it changed. Caller holds the lock."""
        report = self._render(device_id)
        if self._last_report.get(device_id) == report:
            return
        try:
            self._writer(self._paths[device_id], report)
        except OSError as exc:
            log.error("Could not write feature report to %s: %s", device_id, exc)
            return
        self._last_report[device_id] = report
        log.debug("Wrote %s report %s", device_id, report.hex())

    def _render(self, device_id: str) -> bytes:
        controller = self._controllers.get(device_id)
        if controller is not None:
            return controller.render(self._blink_on)
        byte = 0
        for output in self._gear.get(device_id, []):
            positions = [self._values.get(n) for n in output.positions()]
            powered = output.power is None or (self._values.get(output.power) or 0) >= 0.5
            byte |= gear_led_byte(positions, output.down_at, powered)
        return bytes([_REPORT_ID, byte])

    def _blink_tick(self) -> None:
        """Flip the blink phase and rewrite any device whose report changed.

        Cheap: with nothing blinking the rendered bytes are identical, so the
        change-guard skips the HID write; only a mode with a blinking LED (OMNI)
        actually toggles a bit here.
        """
        with self._lock:
            self._blink_on = not self._blink_on
            for device_id in self._devices:
                self._write_if_changed(device_id)

    def _blink_loop(self, stop: threading.Event) -> None:
        """Drive the blink phase every half-period until ``stop`` is set."""
        while not stop.wait(_BLINK_HALF_PERIOD):
            self._blink_tick()

    def run(self, stop: threading.Event) -> None:
        """Subscribe, then write reports as state updates arrive until ``stop``.

        Writes an initial report so each panel starts in a known state, starts the
        blink ticker (only when a stateful controller is present), then blocks on
        the bridge's state stream. Daemon-friendly: the stream ends when the
        socket closes on shutdown.
        """
        self._stop = stop
        self.subscribe_all()
        with self._lock:
            for device_id in self._devices:
                self._write_if_changed(device_id)
        if self._controllers:
            threading.Thread(target=self._blink_loop, args=(stop,), daemon=True).start()
        for name, value in self._dispatcher.states():
            if stop.is_set():
                return
            self.on_state(name, value)
