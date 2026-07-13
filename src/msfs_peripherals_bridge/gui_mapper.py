"""Pure logic for the GUI's Mapper tab — Stufe A (device viewer).

Turns the loaded device catalog + one profile into flat, display-ready rows:
one per catalog device (with how many bindings/outputs the profile assigns it,
plus a live-present flag the GUI fills in), and one per binding/output when a
device is selected.

Kept dependency-free and pure (no tkinter, no device I/O) so it can be unit
tested without a display or attached hardware. Device *discovery* lives in the
GUI — it needs the Linux-only evdev/hidraw readers; this module only formats
what it is handed.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import (
    Action,
    Binding,
    CurveKind,
    DeviceCatalog,
    EventAction,
    EventFromVarAction,
    Output,
    Profile,
    RpnAction,
    SequenceAction,
    SimVarAction,
    Source,
    Transform,
)

# German labels for the physical control kinds (SourceKind values).
_KIND_LABEL = {
    "axis": "Achse",
    "button": "Taste",
    "hat": "Hat",
    "switch": "Schalter",
}


@dataclass(frozen=True)
class DeviceRow:
    """One row in the device list: a catalog device + its profile usage."""

    id: str
    name: str
    transport: str
    usb: str
    present: bool | None  # True/False detected, None = discovery unavailable
    bindings: int
    outputs: int

    @property
    def status(self) -> str:
        """Human status word for the ``present`` tri-state."""
        if self.present is None:
            return "?"
        return "verbunden" if self.present else "nicht erkannt"


@dataclass(frozen=True)
class BindingRow:
    """One binding rendered for the device-detail table."""

    name: str
    source: str
    action: str
    transform: str


def build_device_rows(
    catalog: DeviceCatalog,
    profile: Profile,
    present: set[str] | None,
) -> list[DeviceRow]:
    """One :class:`DeviceRow` per catalog device, in catalog order.

    ``present`` is the set of device ids discovered as attached right now, or
    ``None`` when discovery couldn't run (non-Linux, no python-evdev) — then
    every row's ``present`` is ``None`` and shows as unknown.
    """
    rows: list[DeviceRow] = []
    for dev in catalog.devices:
        rows.append(
            DeviceRow(
                id=dev.id,
                name=dev.name,
                transport=dev.transport,
                usb=f"{dev.vendor}:{dev.product}",
                present=None if present is None else (dev.id in present),
                bindings=len(profile.bindings.get(dev.id, [])),
                outputs=len(profile.outputs.get(dev.id, [])),
            )
        )
    return rows


def describe_source(source: Source) -> str:
    """Short label for a physical control, e.g. ``Taste 288`` / ``Achse 0``."""
    return f"{_KIND_LABEL.get(source.kind, str(source.kind))} {source.code}"


def describe_action(action: Action) -> str:
    """One-line summary of what an action does (its target event/var)."""
    if isinstance(action, EventAction):
        val = "" if action.value is None else f" = {action.value}"
        return f"event {action.event}{val}"
    if isinstance(action, SimVarAction):
        inv = " (invert)" if action.invert else ""
        return f"set {action.simvar}{inv}"
    if isinstance(action, EventFromVarAction):
        return f"{action.event} ← {action.read}"
    if isinstance(action, SequenceAction):
        n = len(action.on_edge) + len(action.off_edge)
        targets = [s.event or s.simvar or "?" for s in action.on_edge]
        head = ", ".join(targets[:2])
        more = " …" if len(targets) > 2 else ""
        return f"sequence [{n}]: {head}{more}"
    if isinstance(action, RpnAction):
        return f"rpn {action.code}"
    return type(action).__name__


def describe_transform(t: Transform) -> str:
    """Summary of any non-default axis shaping; ``''`` when all defaults."""
    parts: list[str] = []
    if t.deadzone:
        parts.append(f"dz={t.deadzone:g}")
    if t.curve == CurveKind.EXPO:
        # the expo strength belongs to the expo curve — fold it in, don't repeat it
        parts.append(f"expo={t.expo:g}" if t.expo else "expo")
    elif t.curve != CurveKind.LINEAR:
        parts.append(str(t.curve))
    elif t.expo:
        parts.append(f"expo={t.expo:g}")
    if t.invert:
        parts.append("invert")
    if (t.out_min, t.out_max) != (0.0, 1.0):
        parts.append(f"out[{t.out_min:g},{t.out_max:g}]")
    return ", ".join(parts)


def describe_binding(binding: Binding) -> BindingRow:
    """Flatten one :class:`Binding` into its four display columns."""
    return BindingRow(
        name=binding.name,
        source=describe_source(binding.source),
        action=describe_action(binding.action),
        transform=describe_transform(binding.transform),
    )


def describe_output(output: Output) -> str:
    """Concise summary of an output block: its type + how many SimVars it drives."""
    kind = getattr(output, "type", type(output).__name__)
    try:
        n = len(output.simvars())
    except Exception:
        return str(kind)
    return f"{kind} — {n} SimVar{'s' if n != 1 else ''}"


def device_bindings(profile: Profile, device_id: str) -> list[BindingRow]:
    """All bindings the profile assigns ``device_id``, flattened for display."""
    return [describe_binding(b) for b in profile.bindings.get(device_id, [])]


def device_outputs(profile: Profile, device_id: str) -> list[str]:
    """All output summaries the profile assigns ``device_id``."""
    return [describe_output(o) for o in profile.outputs.get(device_id, [])]
