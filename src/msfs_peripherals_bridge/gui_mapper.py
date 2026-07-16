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
    AdfBank,
    Binding,
    CurveKind,
    DeviceCatalog,
    DmeBank,
    EventAction,
    EventFromVarAction,
    GearLedOutput,
    MultiPanelOutput,
    Output,
    Profile,
    RadioBank,
    RadioPanelOutput,
    RpnAction,
    SelectorEntry,
    SequenceAction,
    SimVarAction,
    Source,
    Transform,
    WriteStep,
    XpdrBank,
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
    action = describe_action(binding.action)
    if binding.split is not None:
        action += f" · unter {binding.split.at}: {describe_action(binding.split.action)}"
    return BindingRow(
        name=binding.name,
        source=describe_source(binding.source),
        action=action,
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


def _describe_gear_leds(o: GearLedOutput) -> list[str]:
    return [
        f"Rad-LEDs: nose={o.nose}, left={o.left}, right={o.right}",
        f"grün ab Position {o.down_at:g}",
        f"Power-Gate: {o.power}" if o.power else "Power-Gate: —",
    ]


def _describe_selector(e: SelectorEntry) -> str:
    step = f"Schritt {e.step:g}" + (f"/schnell {e.fast_step:g}" if e.fast_step else "")
    target = f"event {e.set_event}" if e.set_event else "SimVar-Write"
    flags = [f for f, on in (("rollover", e.rollover), ("sticky", e.sticky)) if on]
    tail = (", " + ", ".join(flags)) if flags else ""
    return (f"Selektor {e.code} {e.label}: {e.simvar} "
            f"[{step}, {e.min:g}…{e.max:g}, {target}, Zeile {e.display_row}{tail}]")


def _describe_multi(o: MultiPanelOutput) -> list[str]:
    lines: list[str] = []
    for e in o.selector:
        lines.append(_describe_selector(e))
        for s in e.alt_sources:
            evt = f" (event {s.set_event})" if s.set_event else ""
            lines.append(f"    ↳ Alt-Quelle {s.simvar}{evt}")
    lines.append(f"AP-Master-LED: {o.ap_master}")
    lines.append(f"Mode-Var: {o.mode_var}")
    lines += [f"LED {btn} ← {var}" for btn, var in o.bool_leds.items()]
    if o.source_toggle is not None:
        lines.append(f"Quellen-Umschalter: {o.source_toggle.device} code {o.source_toggle.code}")
    if o.dimmer is not None:
        tgts = ", ".join((t.var or t.event or "?") for t in o.dimmer.targets)
        lines.append(f"Dimmer (cw {o.dimmer.cw}/ccw {o.dimmer.ccw}, {o.dimmer.step:g}%): {tgts}")
    if o.power:
        lines.append(f"Power-Gate: {o.power}")
    return lines


def _describe_bank(b: object) -> str:
    if isinstance(b, RadioBank):  # COM/NAV freq
        fine = ", fine-view" if b.fine_view else ""
        return (f"{b.code} {b.label} (freq): act={b.active}, stby={b.standby}, "
                f"swap {b.swap_event}{fine}")
    if isinstance(b, DmeBank):
        srcs = "/".join(s.label for s in b.sources)
        sv = f", src-var {b.source_var}" if b.source_var else ""
        return f"{b.code} {b.label} (DME, nur Anzeige): Quellen {srcs}{sv}"
    if isinstance(b, AdfBank):
        return (f"{b.code} {b.label} (ADF): {b.dig1_var}, {b.dig2_var}, {b.dig3_var} "
                f"[{b.min_khz}…{b.max_khz} kHz]")
    if isinstance(b, XpdrBank):
        baro = f", QNH {b.baro_var}" if b.baro_var else ""
        return f"{b.code} {b.label} (XPDR): code {b.code_var}, set {b.set_event}{baro}"
    return f"{getattr(b, 'code', '?')} {getattr(b, 'label', '?')}"


def _describe_radio(o: RadioPanelOutput) -> list[str]:
    lines: list[str] = []
    for u in o.units:
        lines.append(f"Einheit {u.name} ({u.row}): Encoder outer {u.outer_cw}/{u.outer_ccw}, "
                     f"inner {u.inner_cw}/{u.inner_ccw}, swap {u.swap}")
        lines += ["    " + _describe_bank(b) for b in u.banks]
    if o.power:
        lines.append(f"Power-Gate: {o.power}")
    return lines


def describe_output_detail(output: Output) -> list[str]:
    """Readable child lines exposing an output block's internal controls.

    The Mapper viewer renders these under each output so a panel's selector banks,
    encoder/swap input codes and LED/dimmer targets are visible — not just the
    terse ``type — N SimVars`` summary. Returns ``[]`` for an unknown type.
    """
    if isinstance(output, GearLedOutput):
        return _describe_gear_leds(output)
    if isinstance(output, MultiPanelOutput):
        return _describe_multi(output)
    if isinstance(output, RadioPanelOutput):
        return _describe_radio(output)
    return []


def device_bindings(profile: Profile, device_id: str) -> list[BindingRow]:
    """All bindings the profile assigns ``device_id``, flattened for display."""
    return [describe_binding(b) for b in profile.bindings.get(device_id, [])]


def device_outputs(profile: Profile, device_id: str) -> list[str]:
    """All output summaries the profile assigns ``device_id``."""
    return [describe_output(o) for o in profile.outputs.get(device_id, [])]


# --------------------------------------------------------------------------- #
# editor form <-> binding dict (pure, testable — the tkinter widgets in gui.py
# only shuttle values in and out of these two functions)
# --------------------------------------------------------------------------- #
SOURCE_KINDS = ("axis", "button", "switch", "hat")
# Action types the inline editor can build. ``sequence`` is shown but not
# constructed inline yet (its multi-step list needs its own editor) — an existing
# sequence is preserved on save; you cannot turn another type into one here.
ACTION_TYPES = ("event", "simvar", "event_from_var", "rpn", "sequence")
# The split (below-detent) range gets its own action, but no sequence — a
# sequence is edge-driven and makes no sense on a continuous axis range.
SPLIT_ACTION_TYPES = ("event", "simvar", "rpn")
CURVES = ("linear", "expo", "squared")


def _fmt_num(x: float) -> str:
    return f"{x:g}"


def _parse_int(value: object, label: str) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError(f"{label} muss eine ganze Zahl sein.") from None


def _parse_float(value: object, label: str, default: float) -> float:
    s = str(value).strip() if value is not None else ""
    if s == "":
        return default
    try:
        return float(s)
    except ValueError:
        raise ValueError(f"{label} muss eine Zahl sein.") from None


def _parse_num(value: object, label: str) -> float | int:
    """Parse a number, returning an int when it is whole (clean YAML scalars)."""
    s = str(value).strip() if value is not None else ""
    try:
        f = float(s)
    except (TypeError, ValueError):
        raise ValueError(f"{label} muss eine Zahl sein.") from None
    return int(f) if f.is_integer() else f


# --------------------------------------------------------------------------- #
# sequence action <-> editable step rows (pure; the GUI builds widgets around it)
# --------------------------------------------------------------------------- #
def seq_action_to_rows(action: SequenceAction) -> dict:
    """Split a sequence action into editable ``{on: [...], off: [...]}`` step rows.

    Each row is a flat ``{target, name, value, unit}`` (all strings) — ``target``
    is ``event`` or ``simvar``, ``name`` the event/var name.
    """
    def row(s: WriteStep) -> dict:
        return {
            "target": "event" if s.event else "simvar",
            "name": s.event or s.simvar or "",
            "value": _fmt_num(s.value),
            "unit": s.unit,
        }
    return {"on": [row(s) for s in action.on_edge],
            "off": [row(s) for s in action.off_edge]}


def rows_to_seq_action(on_rows: list[dict], off_rows: list[dict]) -> dict:
    """Build a sequence action dict from editor rows. Raises ``ValueError`` if invalid.

    A step needs a name and a numeric value; ``on`` must have at least one step
    (mirrors :class:`~..models.SequenceAction`). ``unit`` is emitted only for a
    non-default simvar step.
    """
    def step(r: dict) -> dict:
        name = (r.get("name") or "").strip()
        if not name:
            raise ValueError("Sequence-Schritt: Name fehlt.")
        val = _parse_num(r.get("value"), "Wert")
        if r.get("target") == "simvar":
            d: dict = {"simvar": name, "value": val}
            unit = (r.get("unit") or "").strip()
            if unit and unit != "number":
                d["unit"] = unit
            return d
        return {"event": name, "value": val}

    if not on_rows:
        raise ValueError("Sequence braucht mindestens einen on-Schritt.")
    action: dict = {"type": "sequence", "on_edge": [step(r) for r in on_rows]}
    off = [step(r) for r in off_rows]
    if off:
        action["off_edge"] = off
    return action


def _blank_action_fields(prefix: str = "") -> dict:
    """Blank editor fields for one action slot (``prefix`` = ``sp_`` for split)."""
    return {
        f"{prefix}ev_event": "", f"{prefix}ev_value": "",
        f"{prefix}sv_simvar": "", f"{prefix}sv_unit": "number", f"{prefix}sv_invert": False,
        f"{prefix}efv_read": "", f"{prefix}efv_event": "", f"{prefix}efv_unit": "number",
        f"{prefix}rpn_code": "",
    }


def _action_fields(a: Action, prefix: str = "") -> dict:
    """Editor fields for one action: only its own type carries real values."""
    form = _blank_action_fields(prefix)
    form[f"{prefix}action_type"] = a.type
    if a.type == "event":
        form[f"{prefix}ev_event"] = a.event
        form[f"{prefix}ev_value"] = "" if a.value is None else str(a.value)
    elif a.type == "simvar":
        form[f"{prefix}sv_simvar"], form[f"{prefix}sv_unit"] = a.simvar, a.unit
        form[f"{prefix}sv_invert"] = bool(a.invert)
    elif a.type == "event_from_var":
        form[f"{prefix}efv_read"], form[f"{prefix}efv_event"] = a.read, a.event
        form[f"{prefix}efv_unit"] = a.unit
    elif a.type == "rpn":
        form[f"{prefix}rpn_code"] = a.code
    return form


def _transform_fields(t: Transform, prefix: str = "tf_") -> dict:
    """Editor fields for one transform (``prefix`` = ``sp_tf_`` for split)."""
    return {
        f"{prefix}deadzone": _fmt_num(t.deadzone),
        f"{prefix}curve": str(t.curve),
        f"{prefix}expo": _fmt_num(t.expo),
        f"{prefix}invert": bool(t.invert),
        f"{prefix}out_min": _fmt_num(t.out_min),
        f"{prefix}out_max": _fmt_num(t.out_max),
    }


def binding_to_form(binding: Binding) -> dict:
    """Flatten a :class:`Binding` into flat form values (str/bool) for the editor.

    Only the fields relevant to the binding's actual action type carry real
    values; the rest get sensible blanks so switching type in the UI starts clean.
    A detent split fills the ``sp_``-prefixed second slot (action + transform).
    """
    s = binding.source
    form = {
        "name": binding.name,
        "kind": str(s.kind),
        "code": str(s.code),
        "raw_min": "" if s.raw_min is None else str(s.raw_min),
        "raw_max": "" if s.raw_max is None else str(s.raw_max),
        "is_axis": str(s.kind) == "axis",
    }
    form.update(_action_fields(binding.action))
    form.update(_transform_fields(binding.transform))
    sp = binding.split
    form["sp_enabled"] = sp is not None
    form["sp_at"] = "" if sp is None else str(sp.at)
    if sp is None:
        form.update(_blank_action_fields("sp_"))
        form["sp_action_type"] = "event"
        form.update(_transform_fields(Transform(), "sp_tf_"))
    else:
        form.update(_action_fields(sp.action, "sp_"))
        form.update(_transform_fields(sp.transform, "sp_tf_"))
    return form


def _form_action(atype: str, form: dict, original_action: dict | None) -> dict:
    if atype == "event":
        ev = (form.get("ev_event") or "").strip()
        if not ev:
            raise ValueError("Event-Name fehlt.")
        act: dict = {"type": "event", "event": ev}
        val = (form.get("ev_value") or "").strip()
        if val != "":
            act["value"] = _parse_int(val, "Wert")
        return act
    if atype == "simvar":
        sv = (form.get("sv_simvar") or "").strip()
        if not sv:
            raise ValueError("SimVar-Name fehlt.")
        act = {"type": "simvar", "simvar": sv}
        unit = (form.get("sv_unit") or "").strip()
        if unit and unit != "number":
            act["unit"] = unit
        if form.get("sv_invert"):
            act["invert"] = True
        return act
    if atype == "event_from_var":
        read = (form.get("efv_read") or "").strip()
        ev = (form.get("efv_event") or "").strip()
        if not read or not ev:
            raise ValueError("event_from_var braucht 'read' und 'event'.")
        act = {"type": "event_from_var", "read": read, "event": ev}
        unit = (form.get("efv_unit") or "").strip()
        if unit and unit != "number":
            act["unit"] = unit
        return act
    if atype == "rpn":
        code = (form.get("rpn_code") or "").strip()
        if not code:
            raise ValueError("RPN-Ausdruck fehlt.")
        return {"type": "rpn", "code": code}
    if atype == "sequence":
        if not original_action or original_action.get("type") != "sequence":
            raise ValueError("Sequence kann inline (noch) nicht angelegt werden.")
        return original_action
    raise ValueError(f"Unbekannter Aktions-Typ: {atype}")


def _form_transform(form: dict) -> dict:
    tf: dict = {}
    dz = _parse_float(form.get("tf_deadzone"), "Deadzone", 0.0)
    if dz:
        tf["deadzone"] = dz
    curve = form.get("tf_curve") or "linear"
    if curve != "linear":
        tf["curve"] = curve
    expo = _parse_float(form.get("tf_expo"), "Expo", 0.0)
    if expo:
        tf["expo"] = expo
    if form.get("tf_invert"):
        tf["invert"] = True
    omin = _parse_float(form.get("tf_out_min"), "out_min", 0.0)
    omax = _parse_float(form.get("tf_out_max"), "out_max", 1.0)
    if omin != 0.0:
        tf["out_min"] = omin
    if omax != 1.0:
        tf["out_max"] = omax
    return tf


def form_to_binding(form: dict, original_action: dict | None = None) -> dict:
    """Build a binding dict (for ``profile_writer``) from flat form values.

    Raises :class:`ValueError` with a German message on invalid input so the GUI
    can show it inline. ``original_action`` is reused when the action type is
    ``sequence`` (not editable inline yet). A transform is emitted only for axis
    sources, and only for its non-default fields.
    """
    name = (form.get("name") or "").strip()
    if not name:
        raise ValueError("Name darf nicht leer sein.")
    kind = form.get("kind")
    if kind not in SOURCE_KINDS:
        raise ValueError(f"Unbekannte Quell-Art: {kind}")
    source: dict = {"kind": kind, "code": _parse_int(form.get("code"), "Code")}
    if kind == "axis":
        if str(form.get("raw_min", "")).strip() != "":
            source["raw_min"] = _parse_int(form.get("raw_min"), "raw_min")
        if str(form.get("raw_max", "")).strip() != "":
            source["raw_max"] = _parse_int(form.get("raw_max"), "raw_max")

    binding: dict = {
        "name": name,
        "source": source,
        "action": _form_action(form.get("action_type"), form, original_action),
    }
    if kind == "axis":
        tf = _form_transform(form)
        if tf:
            binding["transform"] = tf
        if form.get("sp_enabled"):
            binding["split"] = _form_split(form)
    return binding


def _form_split(form: dict) -> dict:
    """Build the below-detent ``split`` block from the ``sp_``-prefixed fields.

    The sub-form trick: stripping the ``sp_`` prefix turns the split fields back
    into standard action/transform field names, so the same parsers apply.
    """
    sub = {k[3:]: v for k, v in form.items() if k.startswith("sp_")}
    atype = sub.get("action_type")
    if atype not in SPLIT_ACTION_TYPES:
        raise ValueError(f"Split: Aktions-Typ '{atype}' geht unterhalb des Detents nicht.")
    split: dict = {
        "at": _parse_int(form.get("sp_at"), "Detent (roh)"),
        "action": _form_action(atype, sub, None),
    }
    tf = _form_transform(sub)  # sp_tf_* stripped to tf_*
    if tf:
        split["transform"] = tf
    return split


def blank_binding_form(kind: str = "button") -> dict:
    """Flat form values for a brand-new binding (used by 'add')."""
    form = {
        "name": "Neues Binding", "kind": kind, "code": "0", "raw_min": "", "raw_max": "",
        "is_axis": kind == "axis", "action_type": "event",
        "sp_enabled": False, "sp_at": "", "sp_action_type": "event",
    }
    form.update(_blank_action_fields())
    form.update(_blank_action_fields("sp_"))
    form.update(_transform_fields(Transform()))
    form.update(_transform_fields(Transform(), "sp_tf_"))
    return form


# --------------------------------------------------------------------------- #
# Stufe C: output editor — a generic, model-driven field tree. Walks a pydantic
# Output instance into flat display/edit nodes so ONE editor covers gear_leds,
# multi_panel and radio_panel (incl. nested selector entries, banks, dimmer,
# LED maps). Pure: the tkinter window in gui.py only renders/apply-s these.
# --------------------------------------------------------------------------- #
UNSET = object()  # sentinel: "remove this key from the YAML" (fall back to default)

# str fields that are labels/units, NOT variable/event names -> no var picker
_NOT_PICKABLE = {"label", "name", "unit", "row", "display_row", "kind", "type", "device"}

# German blurbs for the container fields, shown as tree tooltips/labels.
FIELD_LABEL = {
    "selector": "Selektor-Positionen",
    "alt_sources": "Alternativ-Quellen",
    "bool_leds": "LEDs (Var-gesteuert)",
    "dimmer": "Dimmer",
    "source_toggle": "Quellen-Umschalter",
    "targets": "Dimmer-Ziele",
    "units": "Radio-Einheiten",
    "banks": "Bänke (Selektor)",
    "sources": "DME-Quellen",
}

# templates for "+ Eintrag" per list field; banks offer one template per kind.
_LIST_TEMPLATES: dict[str, dict] = {
    "selector": {"code": 0, "label": "NEU", "simvar": "", "min": 0, "max": 100},
    "alt_sources": {"simvar": ""},
    "sources": {"label": "1", "distance": "NAV DME:1", "speed": "NAV DMESPEED:1"},
    "targets": {"var": "", "full": 100},
}
_BANK_TEMPLATES: dict[str, dict] = {
    "COM/NAV-Frequenz": {
        "code": 0, "label": "NEU", "active": "", "standby": "", "swap_event": "",
        "whole_inc": "", "whole_dec": "", "fract_inc": "", "fract_dec": "",
    },
    "DME": {"kind": "dme", "code": 0,
            "sources": [{"label": "1", "distance": "NAV DME:1", "speed": "NAV DMESPEED:1"}]},
    "ADF (KR-85)": {"kind": "adf", "code": 0},
    "XPDR": {"kind": "xpdr", "code": 0},
}
# optional nested models, creatable when unset (None)
OPTIONAL_TEMPLATES: dict[str, dict] = {
    "dimmer": {"cw": 0, "ccw": 1, "targets": [{"var": "", "full": 100}]},
    "source_toggle": {"device": "yoke", "code": 0},
}


@dataclass(frozen=True)
class OutputNode:
    """One row of the output editor tree (leaf field or container)."""

    path: tuple
    label: str
    value: str
    kind: str  # str|int|float|bool|choice|ro|list|dict|entry|group|unset
    choices: tuple = ()
    optional: bool = False
    pickable: bool = False
    removable: bool = False
    addable: str | None = None  # container field name when entries can be added


def _leaf_kind(ann) -> tuple[str | None, tuple, bool]:
    """(scalar-kind, choices, optional) for an annotation; kind None = no scalar."""
    import types
    import typing
    from typing import Literal

    optional = False
    origin = typing.get_origin(ann)
    if origin in (typing.Union, types.UnionType):
        args = typing.get_args(ann)
        non_none = [a for a in args if a is not type(None)]
        optional = len(non_none) < len(args)
        if len(non_none) != 1:
            return "str", (), optional
        ann = non_none[0]
        origin = typing.get_origin(ann)
    if origin is Literal:
        return "choice", tuple(str(a) for a in typing.get_args(ann)), optional
    if ann is bool:
        return "bool", (), optional
    if ann is int:
        return "int", (), optional
    if ann is float:
        return "float", (), optional
    if ann is str:
        return "str", (), optional
    return None, (), optional


def _display(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "ja" if value else "nein"
    if isinstance(value, float):
        return _fmt_num(value)
    return str(value)


def _entry_label(name: str, i: int, item) -> str:
    tag = getattr(item, "label", None) or getattr(item, "name", None) \
        or getattr(item, "var", None) or getattr(item, "event", None) or ""
    kind = getattr(item, "kind", "")
    extra = f" · {kind}" if kind and name == "banks" else ""
    return f"{name}[{i}]" + (f" — {tag}{extra}" if tag or extra else "")


def _walk_output(model, path: tuple, nodes: list[OutputNode]) -> None:
    import typing

    from pydantic import BaseModel

    for name, field in type(model).model_fields.items():
        val = getattr(model, name)
        fpath = (*path, name)
        if name in ("type", "kind"):  # discriminators: fixed per block
            nodes.append(OutputNode(fpath, name, str(val), "ro"))
            continue
        kind, choices, optional = _leaf_kind(field.annotation)
        if kind is not None and not isinstance(val, BaseModel):
            nodes.append(OutputNode(
                fpath, name, _display(val), kind, choices=choices, optional=optional,
                pickable=(kind == "str" and name not in _NOT_PICKABLE),
            ))
            continue
        origin = typing.get_origin(field.annotation)
        if origin is list:
            addable = name if (name in _LIST_TEMPLATES or name == "banks") else None
            nodes.append(OutputNode(fpath, FIELD_LABEL.get(name, name),
                                    f"({len(val)})", "list", addable=addable))
            for i, item in enumerate(val):
                nodes.append(OutputNode((*fpath, i), _entry_label(name, i, item),
                                        "", "entry", removable=True))
                _walk_output(item, (*fpath, i), nodes)
            continue
        if origin is dict:  # bool_leds: button name -> var
            nodes.append(OutputNode(fpath, FIELD_LABEL.get(name, name),
                                    f"({len(val)})", "dict", addable=name))
            for key, v in val.items():
                nodes.append(OutputNode((*fpath, key), key, str(v), "str",
                                        pickable=True, removable=True))
            continue
        if isinstance(val, BaseModel):
            nodes.append(OutputNode(fpath, FIELD_LABEL.get(name, name), "", "group",
                                    removable=optional))
            _walk_output(val, fpath, nodes)
            continue
        if val is None and optional:  # unset optional model (dimmer/source_toggle)
            nodes.append(OutputNode(fpath, FIELD_LABEL.get(name, name), "—", "unset",
                                    addable=name if name in OPTIONAL_TEMPLATES else None))
            continue
        nodes.append(OutputNode(fpath, name, _display(val), "ro"))


def output_nodes(output: Output) -> list[OutputNode]:
    """Flatten one output block into editor tree nodes (depth-first order)."""
    nodes: list[OutputNode] = []
    _walk_output(output, (), nodes)
    return nodes


def _resolve_parent(output: Output, path: tuple):
    node = output
    for p in path[:-1]:
        node = node[p] if isinstance(p, int) or isinstance(node, dict) else getattr(node, p)
    return node


def parse_output_value(output: Output, path: tuple, raw) -> object:
    """Parse an editor input for the leaf at ``path``; German ValueError on junk.

    Returns the typed value, or :data:`UNSET` when an emptied optional field
    should fall back to its default (key removed from the YAML). An optional
    field whose default is not None gets an explicit ``None`` (YAML null)
    instead, so "aus" is expressible.
    """
    parent = _resolve_parent(output, path)
    name = path[-1]
    if isinstance(parent, dict):  # bool_leds entry -> plain str
        return str(raw).strip()
    field = type(parent).model_fields[name]
    kind, choices, optional = _leaf_kind(field.annotation)
    if isinstance(raw, bool):
        return raw
    s = str(raw).strip()
    if s in ("", "—"):
        if not optional:
            raise ValueError(f"{name}: Wert fehlt.")
        return UNSET if field.default is None else None
    if kind == "int":
        return _parse_int(s, name)
    if kind == "float":
        return _parse_num(s, name)
    if kind == "choice":
        if s not in choices:
            raise ValueError(f"{name}: muss eins von {', '.join(choices)} sein.")
        return s
    if kind == "bool":
        if s.lower() in ("1", "true", "ja", "an", "on"):
            return True
        if s.lower() in ("0", "false", "nein", "aus", "off"):
            return False
        raise ValueError(f"{name}: ja/nein erwartet.")
    return s


def output_add_options(output: Output, path: tuple) -> dict[str, dict]:
    """Menu-label -> template entry for the container at ``path``."""
    name = path[-1]
    if name == "banks":
        return {k: dict(v) for k, v in _BANK_TEMPLATES.items()}
    if name in _LIST_TEMPLATES:
        return {"Eintrag": dict(_LIST_TEMPLATES[name])}
    if name in OPTIONAL_TEMPLATES:
        return {"Anlegen": dict(OPTIONAL_TEMPLATES[name])}
    return {}


def output_dict_key_options(output: Output, path: tuple) -> list[str]:
    """Free keys for a dict container (bool_leds: LED buttons not yet mapped)."""
    if path[-1] != "bool_leds":
        return []
    from .mapping.leds import MULTI_LED_BUTTONS

    used = set(getattr(output, "bool_leds", {}) or {})
    return sorted(MULTI_LED_BUTTONS - used)


# --------------------------------------------------------------------------- #
# live view: map hardware events onto binding rows + render axis bars (pure)
# --------------------------------------------------------------------------- #
LIVE_BAR_CELLS = 8


def live_bar(value: float, lo: float, hi: float) -> str:
    """A filling text bar for an axis value, e.g. ``███░░░░░ 2047``."""
    span = (hi - lo) or 1
    frac = min(1.0, max(0.0, (value - lo) / span))
    filled = round(frac * LIVE_BAR_CELLS)
    return "█" * filled + "░" * (LIVE_BAR_CELLS - filled) + f" {value:g}"


def live_row_map(profile: Profile, device_id: str) -> dict[tuple[str, int], list[str]]:
    """{(evdev-kind, code): [detail-row iids]} for one device's bindings.

    evdev reports axes AND hats as EV_ABS ("axis") and buttons as EV_KEY
    ("button"); panel switches are hidraw-only and have no live source here.
    """
    rows: dict[tuple[str, int], list[str]] = {}
    for i, b in enumerate(profile.bindings.get(device_id, [])):
        kind = str(b.source.kind)
        if kind in ("axis", "hat"):
            key = ("axis", b.source.code)
        elif kind == "button":
            key = ("button", b.source.code)
        else:  # switch: hidraw panels, not readable via evdev
            continue
        rows.setdefault(key, []).append(f"bind:{i}")
    return rows
