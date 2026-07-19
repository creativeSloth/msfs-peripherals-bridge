"""The mapping engine: DeviceEvent + active Profile -> SimConnect commands.

This is pure logic with no I/O, so the whole mapping behaviour can be
unit-tested without hardware or a running simulator. Live variable values for
``when:`` conditions come in through an injected ``values`` callable (the
runtime wires it to its condition watcher; tests pass a dict lookup).
"""

from __future__ import annotations

import logging
import math
import operator
from collections.abc import Callable

from ..devices.base import DeviceEvent
from ..models import (
    Action,
    Binding,
    Condition,
    EventAction,
    EventFromVarAction,
    Profile,
    RpnAction,
    SequenceAction,
    SimVarAction,
    SourceKind,
    WriteStep,
)
from ..simconnect.protocol import Command, RpnExec, SendEvent, SendEventFromVar, SetSimVar
from .transforms import shape_axis

log = logging.getLogger(__name__)

_OPS: dict[str, Callable[[float, float], bool]] = {
    "<": operator.lt, "<=": operator.le, ">": operator.gt, ">=": operator.ge,
}


def _condition_holds(cond: Condition, value: object) -> bool:
    """Whether one condition holds for the live value (None/junk = not met)."""
    try:
        v = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    if cond.op == "==":
        return math.isclose(v, cond.value, rel_tol=1e-9, abs_tol=1e-6)
    if cond.op == "!=":
        return not math.isclose(v, cond.value, rel_tol=1e-9, abs_tol=1e-6)
    return _OPS[cond.op](v, cond.value)


def _source_matches(binding: Binding, event: DeviceEvent) -> bool:
    source = binding.source
    if source.kind is SourceKind.HAT:
        # A hat may report as ABS_HAT axes (event kind HAT) OR as discrete buttons
        # (event kind BUTTON) — accept either, on any code this hat listens on.
        if event.kind not in (SourceKind.HAT, SourceKind.BUTTON):
            return False
        codes = (binding.hat.codes(source.code) if binding.hat is not None
                 else {source.code, source.code + 1})
        return event.code in codes
    if source.kind is not event.kind:
        return False
    return source.code == event.code


def _step_command(step: WriteStep) -> Command:
    """One SequenceAction write -> its SimConnect command (event or SimVar set)."""
    if step.simvar is not None:
        return SetSimVar(name=step.simvar, unit=step.unit, value=step.value)
    return SendEvent(name=step.event, data=int(step.value))


class MappingEngine:
    """Resolves device events against the bindings of the active profile.

    ``values`` supplies the latest value of a subscribed variable for ``when:``
    conditions (``None`` = unknown -> the condition is NOT met, fail-closed).
    """

    def __init__(
        self, profile: Profile, values: Callable[[str], object] | None = None
    ) -> None:
        self.profile = profile
        self._values = values or (lambda name: None)

    def set_profile(self, profile: Profile) -> None:
        self.profile = profile

    def resolve(self, event: DeviceEvent) -> list[Command]:
        """Return the SimConnect commands produced by one device event."""
        bindings = self.profile.bindings.get(event.device_id, [])
        commands: list[Command] = []
        for binding in bindings:
            if not _source_matches(binding, event):
                continue
            if binding.when and not self._conditions_met(binding):
                continue
            commands.extend(self._resolve_binding(binding, event))
        return commands

    def _conditions_met(self, binding: Binding) -> bool:
        for cond in binding.when:
            if not _condition_holds(cond, self._values(cond.var)):
                log.debug("Binding '%s' gated: %s %s %g not met",
                          binding.name, cond.var, cond.op, cond.value)
                return False
        return True

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

        if binding.source.kind is SourceKind.HAT and binding.hat is not None:
            # Direction-aware hat: fire the entered direction once; centring /
            # release (value 0) does nothing. Each direction matches its own
            # (code, value) — explicit (learned) or the ABS_HAT convention.
            if event.value == 0:
                return []
            for code, value, action in binding.hat.entries(binding.source.code):
                if event.code == code and event.value == value:
                    return [self._command_for(action, 1.0)]
            return []

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
