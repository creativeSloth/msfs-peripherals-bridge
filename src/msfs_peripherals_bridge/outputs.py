"""Drive panel outputs (LEDs, later 7-seg) from SimVars streamed by the bridge.

The mapping engine is one-directional (device -> sim). Outputs are the reverse:
subscribe to the SimVars an output needs, consume the ``state`` updates the
bridge streams back on the *same* socket, render them to a HID feature report
and write it to the panel. The only output today is the switch-panel gear LEDs.

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
from .models import GearLedOutput, Output
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
        # Only keep outputs for devices that are actually present (have a path).
        self._outputs = {d: outs for d, outs in outputs.items() if d in device_paths}
        self._paths = device_paths
        self._dispatcher = dispatcher
        self._writer = writer
        self._values: dict[str, float | None] = {}
        self._last_report: dict[str, bytes] = {}  # device_id -> last bytes written

    def needed_simvars(self) -> set[str]:
        names: set[str] = set()
        for outs in self._outputs.values():
            for output in outs:
                names.update(output.simvars())
        return names

    def subscribe_all(self) -> None:
        for name in sorted(self.needed_simvars()):
            self._dispatcher.send(Subscribe(name))
            log.debug("Output subscribed to %s", name)

    def on_state(self, name: str, value: object) -> None:
        """Record a SimVar update and rewrite any device whose report changed."""
        self._values[name] = _as_float(value)
        for device_id in self._outputs:
            self._write_if_changed(device_id)

    def _write_if_changed(self, device_id: str) -> None:
        report = self._render(self._outputs[device_id])
        if self._last_report.get(device_id) == report:
            return
        try:
            self._writer(self._paths[device_id], report)
        except OSError as exc:
            log.error("Could not write LEDs to %s: %s", device_id, exc)
            return
        self._last_report[device_id] = report
        log.debug("Wrote %s LED report %s", device_id, report.hex())

    def _render(self, outputs: list[Output]) -> bytes:
        """Aggregate every output for one device into its feature-report bytes."""
        byte = 0
        for output in outputs:
            if isinstance(output, GearLedOutput):
                positions = [self._values.get(n) for n in output.positions()]
                powered = output.power is None or (self._values.get(output.power) or 0) >= 0.5
                byte |= gear_led_byte(positions, output.down_at, powered)
        return bytes([_REPORT_ID, byte])

    def run(self, stop: threading.Event) -> None:
        """Subscribe, then write reports as state updates arrive until ``stop``.

        Writes an initial (all-off) report so the panel starts in a known state,
        then blocks on the bridge's state stream. Daemon-friendly: the stream
        ends when the socket closes on shutdown.
        """
        self.subscribe_all()
        for device_id in self._outputs:
            self._write_if_changed(device_id)
        for name, value in self._dispatcher.states():
            if stop.is_set():
                return
            self.on_state(name, value)
