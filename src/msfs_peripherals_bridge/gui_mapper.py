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


def binding_to_form(binding: Binding) -> dict:
    """Flatten a :class:`Binding` into flat form values (str/bool) for the editor.

    Only the fields relevant to the binding's actual action type carry real
    values; the rest get sensible blanks so switching type in the UI starts clean.
    """
    s, a, t = binding.source, binding.action, binding.transform
    form = {
        "name": binding.name,
        "kind": str(s.kind),
        "code": str(s.code),
        "raw_min": "" if s.raw_min is None else str(s.raw_min),
        "raw_max": "" if s.raw_max is None else str(s.raw_max),
        "is_axis": str(s.kind) == "axis",
        "action_type": a.type,
        # action fields start blank; the active type fills its own below
        "ev_event": "", "ev_value": "",
        "sv_simvar": "", "sv_unit": "number", "sv_invert": False,
        "efv_read": "", "efv_event": "", "efv_unit": "number",
        "rpn_code": "",
        "tf_deadzone": _fmt_num(t.deadzone),
        "tf_curve": str(t.curve),
        "tf_expo": _fmt_num(t.expo),
        "tf_invert": bool(t.invert),
        "tf_out_min": _fmt_num(t.out_min),
        "tf_out_max": _fmt_num(t.out_max),
    }
    if a.type == "event":
        form["ev_event"] = a.event
        form["ev_value"] = "" if a.value is None else str(a.value)
    elif a.type == "simvar":
        form["sv_simvar"], form["sv_unit"], form["sv_invert"] = a.simvar, a.unit, bool(a.invert)
    elif a.type == "event_from_var":
        form["efv_read"], form["efv_event"], form["efv_unit"] = a.read, a.event, a.unit
    elif a.type == "rpn":
        form["rpn_code"] = a.code
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
    return binding


def blank_binding_form(kind: str = "button") -> dict:
    """Flat form values for a brand-new binding (used by 'add')."""
    return {
        "name": "Neues Binding", "kind": kind, "code": "0", "raw_min": "", "raw_max": "",
        "is_axis": kind == "axis", "action_type": "event",
        "ev_event": "", "ev_value": "", "sv_simvar": "", "sv_unit": "number", "sv_invert": False,
        "efv_read": "", "efv_event": "", "efv_unit": "number", "rpn_code": "",
        "tf_deadzone": "0", "tf_curve": "linear", "tf_expo": "0", "tf_invert": False,
        "tf_out_min": "0", "tf_out_max": "1",
    }
