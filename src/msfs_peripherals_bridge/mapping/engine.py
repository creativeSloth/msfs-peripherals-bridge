"""The mapping engine: DeviceEvent + active Profile -> SimConnect commands.

This is pure logic with no I/O, so the whole mapping behaviour can be
unit-tested without hardware or a running simulator.
"""

from __future__ import annotations

from ..devices.base import DeviceEvent
from ..models import Binding, EventAction, Profile, SimVarAction, Source, SourceKind
from ..simconnect.protocol import Command, SendEvent, SetSimVar
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
            value = shape_axis(
                event.value, binding.source.raw_min, binding.source.raw_max, binding.transform
            )
            return self._command_for(binding, value)

        # Buttons / hats: act on press (non-zero), ignore release.
        if event.value == 0:
            return None
        return self._command_for(binding, float(event.value))

    @staticmethod
    def _command_for(binding: Binding, value: float) -> Command:
        action = binding.action
        if isinstance(action, SimVarAction):
            return SetSimVar(name=action.simvar, unit=action.unit, value=value)
        if isinstance(action, EventAction):
            data = action.value if action.value is not None else round(value)
            return SendEvent(name=action.event, data=int(data))
        raise TypeError(f"Unsupported action: {action!r}")
