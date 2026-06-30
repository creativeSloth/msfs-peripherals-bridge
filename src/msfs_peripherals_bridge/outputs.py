"""Drive panel outputs from SimVars streamed by the bridge.

The mapping engine is one-directional (device -> sim). Outputs are the reverse:
subscribe to the SimVars an output needs, consume the ``state`` updates the
bridge streams back on the *same* socket, render them to a HID feature report
and write it to the panel.

Two kinds of output live here:

* **Gear LEDs** (switch panel) — pure one-way: SimVar state -> one feature byte.
* **Multi Panel** — a stateful ``MultiPanelController`` whose display/LEDs depend
  on both SimVar state *and* device input (the selector + encoder). Its state is
  touched from two threads — the output thread (``on_state``) and the mapping
  loop (``handle_input``) — so all controller access is guarded by one lock.

Kept separate from ``runtime`` so the render/track logic can be unit-tested with
a fake dispatcher and a fake writer (no socket, no hardware).
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Iterator
from typing import Protocol

from .devices.hidraw_reader import write_feature_report
from .mapping.leds import gear_led_byte
from .mapping.multi_panel import MultiPanelController
from .models import GearLedOutput, MultiPanelOutput, Output
from .simconnect.protocol import Command, Subscribe

log = logging.getLogger(__name__)

# Switch-panel LED feature report: report id 0, then one data byte.
_REPORT_ID = 0x00


class StateDispatcher(Protocol):
    """A dispatcher that can both send commands and stream SimVar state back."""

    def send(self, command: Command) -> None: ...
    def states(self) -> Iterator[tuple[str, object]]: ...


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
    ) -> None:
        self._paths = device_paths
        self._dispatcher = dispatcher
        self._writer = writer
        self._lock = threading.Lock()
        self._values: dict[str, float | None] = {}
        self._last_report: dict[str, bytes] = {}  # device_id -> last bytes written
        # Split outputs by kind, keeping only devices that are actually present.
        self._gear: dict[str, list[GearLedOutput]] = {}
        self._controllers: dict[str, MultiPanelController] = {}
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
        return commands

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
            return controller.render()
        byte = 0
        for output in self._gear.get(device_id, []):
            positions = [self._values.get(n) for n in output.positions()]
            powered = output.power is None or (self._values.get(output.power) or 0) >= 0.5
            byte |= gear_led_byte(positions, output.down_at, powered)
        return bytes([_REPORT_ID, byte])

    def run(self, stop: threading.Event) -> None:
        """Subscribe, then write reports as state updates arrive until ``stop``.

        Writes an initial report so each panel starts in a known state, then
        blocks on the bridge's state stream. Daemon-friendly: the stream ends
        when the socket closes on shutdown.
        """
        self.subscribe_all()
        with self._lock:
            for device_id in self._devices:
                self._write_if_changed(device_id)
        for name, value in self._dispatcher.states():
            if stop.is_set():
                return
            self.on_state(name, value)
