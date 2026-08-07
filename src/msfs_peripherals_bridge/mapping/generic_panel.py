"""Generic panel controller — Schritt E, first slice (indicator LEDs).

Drives a user-declared device's LEDs straight from sim variables, without a
bespoke controller: each :class:`~..models.GenericLed` is one bit in the feature
report, lit when its var crosses a threshold. This is the generalisation of the
hardcoded Saitek controllers — it implements the same :class:`~..outputs.
PanelController` interface, so the :class:`~..outputs.OutputManager` drives it
uniformly, and it activates only for profiles carrying a ``generic_panel`` output
(the Saitek panels are untouched).

Pure and hardware-free (var states in, report bytes out), so it unit-tests without
a device. A generic panel has no *special* inputs — its buttons/switches are plain
bindings handled by the mapping engine — so ``consumes`` is always False.
"""

from __future__ import annotations

from ..models import GenericPanelOutput
from ..simconnect.protocol import Command
from .display import format_measure, format_row

_REPORT_ID = 0x00


class GenericPanelController:
    """Render a ``generic_panel`` output's feature report from sim-var state."""

    def __init__(self, output: GenericPanelOutput) -> None:
        self._o = output
        self._values: dict[str, float | None] = {}

    def subscriptions(self) -> list[str]:
        return self._o.simvars()

    def consumes(self, code: int) -> bool:
        return False  # a generic panel's inputs are ordinary bindings

    def on_event(self, code: int, value: int) -> list[Command]:
        return []

    def refresh_after(self, code: int) -> list[str]:
        return []

    def on_state(self, name: str, value: object) -> None:
        try:
            self._values[name] = float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            self._values[name] = None

    def render(self, blink_on: bool = True) -> bytes:
        """Full feature report: report id + ``length`` data bytes. Each lit LED sets
        its bit; each display renders its var into its cells. Dark/blank when the
        optional power gate is off."""
        data = bytearray(self._o.length)
        gate = self._o.power
        powered = gate is None or (self._values.get(gate) or 0) >= 0.5
        if powered:
            for led in self._o.leds:
                v = self._values.get(led.var)
                if v is not None and v >= led.on_at and 0 <= led.byte < self._o.length:
                    data[led.byte] |= 1 << led.bit
        for disp in self._o.displays:
            # Unpowered -> value None so the cells render blank, not stale/zero.
            value = self._values.get(disp.var) if powered else None
            cells = (format_measure(value, decimals=disp.decimals, width=disp.cells)
                     if disp.decimals else format_row(value, width=disp.cells))
            for i, cell in enumerate(cells):
                pos = disp.offset + i
                if 0 <= pos < self._o.length:
                    data[pos] = cell
        return bytes([_REPORT_ID, *data])
