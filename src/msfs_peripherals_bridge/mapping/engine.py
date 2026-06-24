"""The mapping engine: DeviceEvent + active Profile -> SimConnect commands.

This is pure logic with no I/O, so the whole mapping behaviour can be
unit-tested without hardware or a running simulator.
"""

from __future__ import annotations

from ..devices.base import DeviceEvent
from ..models import (
    Binding,
    EventAction,
    EventFromVarAction,
    Profile,
    SimVarAction,
    Source,
    SourceKind,
)
from ..simconnect.protocol import Command, SendEvent, SendEventFromVar, SetSimVar
from .transforms import shape_axis


def _source_matches(source: Source, event: DeviceEvent) -> bool:
    return source.kind is event.kind and source.code == event.code


class MappingEngine:
    """Resolves device events against the bindings of the active profile."""

    def __init__(self, profile: Profile) -> None:
        self.profile = profile

    def set_profile(self, profile: Profile) -> None:
        self.profile = profile

    def resolve(self, event: DeviceEvent) -> list[Command]:
        """Return the SimConnect commands produced by one device event."""
        bindings = self.profile.bindings.get(event.device_id, [])
        commands: list[Command] = []
        for binding in bindings:
            if not _source_matches(binding.source, event):
                continue
            command = self._resolve_binding(binding, event)
            if command is not None:
                commands.append(command)
        return commands

    def _resolve_binding(self, binding: Binding, event: DeviceEvent) -> Command | None:
        if event.kind is SourceKind.AXIS:
            raw_min, raw_max = binding.source.raw_min, binding.source.raw_max
            if raw_min is None or raw_max is None:
                raise ValueError(
                    f"Axis binding '{binding.name}' has no raw range; the profile "
                    f"was not resolved against calibration (call apply_calibration)."
                )
            value = shape_axis(event.value, raw_min, raw_max, binding.transform)
            return self._command_for(binding, value)

        if binding.source.kind is SourceKind.SWITCH:
            # Maintained 2-state panel switch (hidraw bit). It reports both edges
            # (1 = on/entered, 0 = off/left). A fixed action value — or a dynamic
            # event_from_var — makes it *momentary*: act only on the press/enter
            # edge (rotary detents, the gear lever). Otherwise it is *stateful*:
            # forward the live 0/1 state on both edges so a toggle switch drives
            # a `*_SET` event or a SimVar to match the physical position.
            action = binding.action
            momentary = isinstance(action, EventFromVarAction) or (
                isinstance(action, EventAction) and action.value is not None
            )
            if momentary and event.value != 1:
                return None
            return self._command_for(binding, float(event.value))

        # Buttons / hats: fire on the press edge only (value == 1), ignoring
        # release (0) and kernel key autorepeat (2) so holding a button toggles
        # a state (e.g. parking brake) exactly once.
        if event.value != 1:
            return None
        return self._command_for(binding, float(event.value))

    @staticmethod
    def _command_for(binding: Binding, value: float) -> Command:
        action = binding.action
        if isinstance(action, SimVarAction):
            return SetSimVar(name=action.simvar, unit=action.unit, value=value)
        if isinstance(action, EventFromVarAction):
            # The value is computed on the bridge (fresh read at press time), so
            # the device value here is irrelevant — just carry the names/unit.
            return SendEventFromVar(event=action.event, read=action.read, unit=action.unit)
        if isinstance(action, EventAction):
            data = action.value if action.value is not None else round(value)
            return SendEvent(name=action.event, data=int(data))
        raise TypeError(f"Unsupported action: {action!r}")
