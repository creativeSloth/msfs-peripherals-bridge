"""The mapping engine: DeviceEvent + active Profile -> SimConnect commands.

This is pure logic with no I/O, so the whole mapping behaviour can be
unit-tested without hardware or a running simulator.
"""

from __future__ import annotations

from ..devices.base import DeviceEvent
from ..models import (
    Action,
    Binding,
    EventAction,
    EventFromVarAction,
    Profile,
    RpnAction,
    SequenceAction,
    SimVarAction,
    Source,
    SourceKind,
    WriteStep,
)
from ..simconnect.protocol import Command, RpnExec, SendEvent, SendEventFromVar, SetSimVar
from .transforms import shape_axis


def _source_matches(source: Source, event: DeviceEvent) -> bool:
    return source.kind is event.kind and source.code == event.code


def _step_command(step: WriteStep) -> Command:
    """One SequenceAction write -> its SimConnect command (event or SimVar set)."""
    if step.simvar is not None:
        return SetSimVar(name=step.simvar, unit=step.unit, value=step.value)
    return SendEvent(name=step.event, data=int(step.value))


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
            commands.extend(self._resolve_binding(binding, event))
        return commands

    def _resolve_binding(self, binding: Binding, event: DeviceEvent) -> list[Command]:
        if event.kind is SourceKind.AXIS:
            raw_min, raw_max = binding.source.raw_min, binding.source.raw_max
            if raw_min is None or raw_max is None:
                raise ValueError(
                    f"Axis binding '{binding.name}' has no raw range; the profile "
                    f"was not resolved against calibration (call apply_calibration)."
                )
            # A detent split cuts the axis in two logical ranges, each normalised
            # over its own raw span: at/above the detent the binding's own
            # action/transform apply, below it the split's (reverse/feather/cutoff).
            split = binding.split
            if split is not None and event.value < split.at:
                value = shape_axis(event.value, raw_min, split.at, split.transform)
                return [self._command_for(split.action, value)]
            if split is not None:
                raw_min = split.at
            value = shape_axis(event.value, raw_min, raw_max, binding.transform)
            return [self._command_for(binding.action, value)]

        if isinstance(binding.action, SequenceAction):
            return self._resolve_sequence(binding.action, event)

        if binding.source.kind is SourceKind.SWITCH:
            # Maintained 2-state panel switch (hidraw bit). It reports both edges
            # (1 = on/entered, 0 = off/left). A fixed action value — or a dynamic
            # event_from_var — makes it *momentary*: act only on the press/enter
            # edge (rotary detents, the gear lever). Otherwise it is *stateful*:
            # forward the live 0/1 state on both edges so a toggle switch drives
            # a `*_SET` event or a SimVar to match the physical position.
            action = binding.action
            momentary = isinstance(action, EventFromVarAction | RpnAction) or (
                isinstance(action, EventAction) and action.value is not None
            )
            if momentary and event.value != 1:
                return []
            return [self._command_for(binding.action, float(event.value))]

        # Buttons / hats: fire on the press edge only (value == 1), ignoring
        # release (0) and kernel key autorepeat (2) so holding a button toggles
        # a state (e.g. parking brake) exactly once.
        if event.value != 1:
            return []
        return [self._command_for(binding.action, float(event.value))]

    @staticmethod
    def _resolve_sequence(action: SequenceAction, event: DeviceEvent) -> list[Command]:
        """Pick the on/off write list for this edge and turn it into commands.

        A maintained switch runs ``on`` on its enter edge (1) and ``off`` on its
        leave edge (0). A momentary button/hat runs ``on`` on the press edge only.
        """
        if event.kind is SourceKind.SWITCH:
            steps = action.on_edge if event.value == 1 else action.off_edge
        elif event.value == 1:  # momentary button/hat press
            steps = action.on_edge
        else:
            steps = []
        return [_step_command(step) for step in steps]

    @staticmethod
    def _command_for(action: Action, value: float) -> Command:
        if isinstance(action, SimVarAction):
            data = 1.0 - value if action.invert else value
            return SetSimVar(name=action.simvar, unit=action.unit, value=data)
        if isinstance(action, EventFromVarAction):
            # The value is computed on the bridge (fresh read at press time), so
            # the device value here is irrelevant — just carry the names/unit.
            return SendEventFromVar(event=action.event, read=action.read, unit=action.unit)
        if isinstance(action, EventAction):
            data = action.value if action.value is not None else round(value)
            return SendEvent(name=action.event, data=int(data))
        if isinstance(action, RpnAction):
            return RpnExec(code=action.code)
        raise TypeError(f"Unsupported action: {action!r}")
