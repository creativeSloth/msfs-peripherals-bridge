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

from .i18n import tr
from .models import (
    Action,
    AdfBank,
    Binding,
    CurveKind,
    DeviceCatalog,
    DeviceDef,
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
    # Total hardware INPUTS the device drives = plain bindings + the input codes
    # living inside its panel controllers (encoders, swap, mode-selector, dimmer).
    # Shown in the "Bind" column so a Saitek panel reads as the input-heavy device
    # it is, instead of "0 bindings, 1 output".
    inputs: int = 0

    @property
    def status(self) -> str:
        """Human status word for the ``present`` tri-state."""
        if self.present is None:
            return "?"
        return tr("verbunden") if self.present else tr("nicht erkannt")


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
                # Atomic element counts (per user: individual LEDs/cells & controls,
                # not top-level blocks) — see atomic_{output,input}_count below.
                outputs=atomic_output_count(dev, profile),
                inputs=atomic_input_count(dev, profile),
            )
        )
    return rows


def panel_input_elements(output: Output) -> int:
    """Physical READ controls on a legacy panel controller, counted as ELEMENTS.

    An encoder is one control (its CW/CCW are the same knob), a rotary selector
    one control (not one per position) — per user: 1 encoder → 1 input. This is
    the element view; :func:`output_input_codes` stays the raw-code view used for
    live matching.
    """
    if isinstance(output, MultiPanelOutput):
        n = 1  # the value encoder (CW/CCW = one knob)
        if output.selector:
            n += 1  # one mode selector, regardless of position count
        if output.dimmer is not None:
            n += 1  # the trim/dimmer wheel
        return n
    if isinstance(output, RadioPanelOutput):
        n = 0
        for u in output.units:
            n += 3  # outer encoder + inner encoder + swap button
            if u.banks:
                n += 1  # the mode selector (one knob), not one per bank
        return n
    return 0


def atomic_output_count(ddef: DeviceDef, profile: Profile) -> int:
    """Atomic WRITE elements a device has: individual LEDs + display cells.

    Legacy Saitek panels via :func:`~..mapping.panel_probe.probe_targets`; user
    devices via their :class:`~..models.OutputBlock`s (LED = 1, display = its cell
    count). Per user: 1 LED → 1 output; count atoms, not top-level blocks.
    """
    from .mapping.panel_probe import probe_targets

    n = sum(len(probe_targets(o)) for o in profile.outputs.get(ddef.id, []))
    for ob in ddef.outputs:
        n += ob.cells if ob.kind == "display" else 1
    return n


def atomic_input_count(ddef: DeviceDef, profile: Profile) -> int:
    """Atomic READ elements a device has.

    Plain bindings + panel-controller input *controls* (:func:`panel_input_elements`,
    encoder = 1) + the controls captured by the device explorer (each InputBlock
    once). Per user: 1 encoder → 1 input.
    """
    n = len(profile.bindings.get(ddef.id, []))
    for o in profile.outputs.get(ddef.id, []):
        n += panel_input_elements(o)
    return n + len(ddef.inputs)


def device_input_sources(ddef: DeviceDef) -> list[tuple[str, str, int]]:
    """Named ``(label, kind, code)`` sources from a device's scanned InputBlocks.

    Bridges the device-explorer input scan (Schritt B) to the binding editor:
    picking a name fills the binding's source kind+code, so a stranger maps by
    name instead of raw codes. Encoders yield two directional entries; blocks
    without a usable code are skipped.
    """
    out: list[tuple[str, str, int]] = []
    for b in ddef.inputs:
        if b.kind == "encoder":
            if b.cw is not None:
                out.append((f"{b.name} · CW", "button", b.cw))
            if b.ccw is not None:
                out.append((f"{b.name} · CCW", "button", b.ccw))
        elif b.code is not None:
            out.append((b.name, b.kind, b.code))
    return out


def output_input_codes(output: Output) -> set[int]:
    """Hardware INPUT codes a panel controller consumes — the physical inputs that
    live *inside* an output block: encoder detents, the swap push, mode-selector
    positions and the dimmer. A pure-output block (the gear LEDs) has none.

    These are inputs even though they sit in an ``outputs:`` block (the Saitek
    panels are bidirectional), so the device overview counts them under "Bind".
    ``source_toggle`` is deliberately excluded — it lives on another device (a yoke
    rocker), not the panel.
    """
    from .mapping.multi_panel import ENCODER_CCW, ENCODER_CW

    if isinstance(output, MultiPanelOutput):
        codes = {e.code for e in output.selector} | {ENCODER_CW, ENCODER_CCW}
        if output.dimmer is not None:
            codes |= {output.dimmer.cw, output.dimmer.ccw}
        return codes
    if isinstance(output, RadioPanelOutput):
        codes = set()
        for u in output.units:
            codes |= {u.outer_cw, u.outer_ccw, u.inner_cw, u.inner_ccw, u.swap}
            codes |= {b.code for b in u.banks}
        return codes
    return set()


def describe_source(source: Source) -> str:
    """Short label for a physical control, e.g. ``Taste 288`` / ``Achse 0``."""
    return f"{tr(_KIND_LABEL.get(source.kind, str(source.kind)))} {source.code}"


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
    if binding.hat is not None:
        parts = [f"{sym} {describe_action(a.action)}"
                 for sym, a in (("▲", binding.hat.up), ("▼", binding.hat.down),
                                ("◀", binding.hat.left), ("▶", binding.hat.right))
                 if a is not None]
        action = tr("Hat") + ": " + " · ".join(parts)
    else:
        action = describe_action(binding.action)
        if binding.split is not None:
            action += (f" · {tr('unter')} {binding.split.at}: "
                       f"{describe_action(binding.split.action)}")
    if binding.when:  # gated bindings are recognisable in the table
        action = f"⚑{len(binding.when)} · " + action
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
        f"{tr('Rad-LEDs')}: nose={o.nose}, left={o.left}, right={o.right}",
        f"{tr('grün ab Position')} {o.down_at:g}",
        f"{tr('Power-Gate')}: {o.power}" if o.power else tr("Power-Gate") + ": —",
    ]


def _describe_selector(e: SelectorEntry) -> str:
    step = f"{tr('Schritt')} {e.step:g}" + (f"/{tr('schnell')} {e.fast_step:g}"
                                            if e.fast_step else "")
    target = f"event {e.set_event}" if e.set_event else tr("SimVar-Write")
    flags = [f for f, on in (("rollover", e.rollover), ("sticky", e.sticky)) if on]
    tail = (", " + ", ".join(flags)) if flags else ""
    return (f"{tr('Selektor')} {e.code} {e.label}: {e.simvar} "
            f"[{step}, {e.min:g}…{e.max:g}, {target}, {tr('Zeile')} {e.display_row}{tail}]")


def _describe_multi(o: MultiPanelOutput) -> list[str]:
    lines: list[str] = []
    for e in o.selector:
        lines.append(_describe_selector(e))
        for s in e.alt_sources:
            evt = f" (event {s.set_event})" if s.set_event else ""
            lines.append(f"    ↳ {tr('Alt-Quelle')} {s.simvar}{evt}")
    lines.append(f"{tr('AP-Master-LED')}: {o.ap_master}")
    lines.append(f"{tr('Mode-Var')}: {o.mode_var}")
    lines += [f"LED {btn} ← {var}" for btn, var in o.bool_leds.items()]
    if o.source_toggle is not None:
        lines.append(f"{tr('Quellen-Umschalter')}: "
                     f"{o.source_toggle.device} code {o.source_toggle.code}")
    if o.dimmer is not None:
        tgts = ", ".join((t.var or t.event or "?") for t in o.dimmer.targets)
        lines.append(f"{tr('Dimmer')} (cw {o.dimmer.cw}/ccw {o.dimmer.ccw}, "
                     f"{o.dimmer.step:g}%): {tgts}")
    if o.power:
        lines.append(f"{tr('Power-Gate')}: {o.power}")
    return lines


def _describe_bank(b: object) -> str:
    if isinstance(b, RadioBank):  # COM/NAV freq
        fine = ", fine-view" if b.fine_view else ""
        return (f"{b.code} {b.label} (freq): act={b.active}, stby={b.standby}, "
                f"swap {b.swap_event}{fine}")
    if isinstance(b, DmeBank):
        srcs = "/".join(s.label for s in b.sources)
        sv = f", src-var {b.source_var}" if b.source_var else ""
        return f"{b.code} {b.label} (DME, {tr('nur Anzeige')}): {tr('Quellen')} {srcs}{sv}"
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
        lines.append(f"{tr('Einheit')} {u.name} ({u.row}): Encoder outer "
                     f"{u.outer_cw}/{u.outer_ccw}, inner {u.inner_cw}/{u.inner_ccw}, swap {u.swap}")
        lines += ["    " + _describe_bank(b) for b in u.banks]
    if o.power:
        lines.append(f"{tr('Power-Gate')}: {o.power}")
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
# Hat directions with their editor symbols — evdev sign convention:
# X (base code): left -1 / right +1; Y (base+1): up -1 / down +1.
HAT_DIRECTIONS = (("up", "▲ oben"), ("down", "▼ unten"),
                  ("left", "◀ links"), ("right", "▶ rechts"))


def _fmt_num(x: float) -> str:
    return f"{x:g}"


def _parse_int(value: object, label: str) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError(tr("{label} muss eine ganze Zahl sein.", label=label)) from None


def _parse_float(value: object, label: str, default: float) -> float:
    s = str(value).strip() if value is not None else ""
    if s == "":
        return default
    try:
        return float(s)
    except ValueError:
        raise ValueError(tr("{label} muss eine Zahl sein.", label=label)) from None


def _parse_num(value: object, label: str) -> float | int:
    """Parse a number, returning an int when it is whole (clean YAML scalars)."""
    s = str(value).strip() if value is not None else ""
    try:
        f = float(s)
    except (TypeError, ValueError):
        raise ValueError(tr("{label} muss eine Zahl sein.", label=label)) from None
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
            raise ValueError(tr("Sequence-Schritt: Name fehlt."))
        val = _parse_num(r.get("value"), "Wert")
        if r.get("target") == "simvar":
            d: dict = {"simvar": name, "value": val}
            unit = (r.get("unit") or "").strip()
            if unit and unit != "number":
                d["unit"] = unit
            return d
        return {"event": name, "value": val}

    if not on_rows:
        raise ValueError(tr("Sequence braucht mindestens einen on-Schritt."))
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


def _blank_hat_fields() -> dict:
    form = {}
    for d, _sym in HAT_DIRECTIONS:
        form[f"hat_{d}_type"] = "event"
        form[f"hat_{d}_name"] = ""
        form[f"hat_{d}_value"] = ""
    return form


def _hat_fields(hat) -> dict:
    """Editor fields for a hat map (event/simvar per direction)."""
    form = _blank_hat_fields()
    for d, _sym in HAT_DIRECTIONS:
        dirn = getattr(hat, d, None) if hat is not None else None
        a = dirn.action if dirn is not None else None  # unwrap HatDirection
        if a is None:
            continue
        if a.type == "event":
            form[f"hat_{d}_type"] = "event"
            form[f"hat_{d}_name"] = a.event
            form[f"hat_{d}_value"] = "" if a.value is None else str(a.value)
        elif a.type == "simvar":
            form[f"hat_{d}_type"] = "simvar"
            form[f"hat_{d}_name"] = a.simvar
    return form


def _form_hat(form: dict) -> dict:
    """Build the ``hat:`` block from the editor's direction slots."""
    hat: dict = {}
    for d, sym in HAT_DIRECTIONS:
        name = (form.get(f"hat_{d}_name") or "").strip()
        if not name:
            continue
        if form.get(f"hat_{d}_type") == "simvar":
            hat[d] = {"type": "simvar", "simvar": name}
        else:
            act: dict = {"type": "event", "event": name}
            val = str(form.get(f"hat_{d}_value") or "").strip()
            if val:
                act["value"] = _parse_int(val, f"Wert {sym}")
            hat[d] = act
    if not hat:
        raise ValueError(tr("Hat: mindestens eine Richtung (▲▼◀▶) belegen."))
    return hat


def binding_to_form(binding: Binding) -> dict:
    """Flatten a :class:`Binding` into flat form values (str/bool) for the editor.

    Only the fields relevant to the binding's actual action type carry real
    values; the rest get sensible blanks so switching type in the UI starts clean.
    A detent split fills the ``sp_``-prefixed second slot (action + transform),
    a hat map the four ``hat_<dir>_*`` direction slots.
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
    form.update(_action_fields(binding.action) if binding.action is not None
                else {**_blank_action_fields(), "action_type": "event"})
    form.update(_transform_fields(binding.transform))
    form.update(_hat_fields(binding.hat))
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
            raise ValueError(tr("Event-Name fehlt."))
        act: dict = {"type": "event", "event": ev}
        val = (form.get("ev_value") or "").strip()
        if val != "":
            act["value"] = _parse_int(val, "Wert")
        return act
    if atype == "simvar":
        sv = (form.get("sv_simvar") or "").strip()
        if not sv:
            raise ValueError(tr("SimVar-Name fehlt."))
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
            raise ValueError(tr("event_from_var braucht 'read' und 'event'."))
        act = {"type": "event_from_var", "read": read, "event": ev}
        unit = (form.get("efv_unit") or "").strip()
        if unit and unit != "number":
            act["unit"] = unit
        return act
    if atype == "rpn":
        code = (form.get("rpn_code") or "").strip()
        if not code:
            raise ValueError(tr("RPN-Ausdruck fehlt."))
        return {"type": "rpn", "code": code}
    if atype == "sequence":
        if not original_action or original_action.get("type") != "sequence":
            raise ValueError(tr("Sequence kann inline (noch) nicht angelegt werden."))
        return original_action
    raise ValueError(tr("Unbekannter Aktions-Typ: {atype}", atype=atype))


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
        raise ValueError(tr("Name darf nicht leer sein."))
    kind = form.get("kind")
    if kind not in SOURCE_KINDS:
        raise ValueError(tr("Unbekannte Quell-Art: {kind}", kind=kind))
    source: dict = {"kind": kind, "code": _parse_int(form.get("code"), "Code")}
    if kind == "axis":
        if str(form.get("raw_min", "")).strip() != "":
            source["raw_min"] = _parse_int(form.get("raw_min"), "raw_min")
        if str(form.get("raw_max", "")).strip() != "":
            source["raw_max"] = _parse_int(form.get("raw_max"), "raw_max")

    binding: dict = {"name": name, "source": source}
    if kind == "hat":
        # a hat binding maps its four directions in one place — no single action
        binding["hat"] = _form_hat(form)
    else:
        binding["action"] = _form_action(form.get("action_type"), form, original_action)
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
        raise ValueError(
            tr("Split: Aktions-Typ '{atype}' geht unterhalb des Detents nicht.", atype=atype))
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
    form.update(_blank_hat_fields())
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

# Dict fields keyed by mode VALUE (not a button name) -> shown read-only in the
# editor (they are per-aircraft maps configured in YAML; a dedicated GUI editor is
# a follow-up). Rendering them as the bool_leds var-dict would mis-key them.
_RO_DICTS = {"mode_leds", "mode_blink_leds"}

# German blurbs for the container fields, shown as tree tooltips/labels.
FIELD_LABEL = {
    "selector": "Selektor-Positionen",
    "alt_sources": "Alternativ-Quellen",
    "bool_leds": "LEDs (Var-gesteuert)",
    "mode_leds": "Mode-LED-Zuordnung",
    "mode_blink_leds": "Mode-Blink-LED",
    "dimmer": "Dimmer",
    "source_toggle": "Quellen-Umschalter",
    "targets": "Dimmer-Ziele",
    "units": "Radio-Einheiten",
    "banks": "Bänke (Selektor)",
    "sources": "DME-Quellen",
}

# German label + explanation per output leaf field. The editor tree shows the
# label; the help line under the edit strip explains what the field means
# (per user: raw YAML names like `fast_step` said nothing). Keyed by field
# name — names are unique enough across the output models in practice.
OUTPUT_FIELD_HELP: dict[str, tuple[str, str]] = {
    "code": ("Hardware-Code", "Bit/Code des Schalters bzw. der Selektor-Position am Panel "
             "(gemessen, s. docs/memory/*-hid.md). Nur ändern, wenn die Hardware neu "
             "vermessen wurde."),
    "label": ("Bezeichnung", "Menschenlesbarer Name, nur für Anzeige/Logs."),
    "unit": ("Einheit", "Einheit für Lesen/Schreiben der Variable (meist number)."),
    "simvar": ("Variable", "Die Sim-Variable, deren Wert angezeigt/editiert wird."),
    "set_event": ("Setz-Event", "K:-Event zum Setzen des Werts; leer = Variable wird "
                  "direkt geschrieben."),
    "step": ("Schritt", "Wertänderung pro Encoder-Rastung."),
    "fast_step": ("Schnell-Schritt", "Größerer Schritt, wenn der Drehknopf schnell gedreht "
                  "wird. Leer = keine Beschleunigung."),
    "min": ("Minimum", "Kleinster einstellbarer Wert."),
    "max": ("Maximum", "Größter einstellbarer Wert."),
    "rollover": ("Umlauf", "Am Ende zum Anfang weiterdrehen (z. B. Heading 359→0) statt "
                 "anzuschlagen."),
    "sticky": ("Encoder-eigen", "Anzeige behält den zuletzt gedrehten Wert, statt der "
               "Live-Variable zu folgen (gegen Gauges, die den Wert überschreiben)."),
    "off_above": ("Aus-Schwelle", "Live-Werte ab dieser Schwelle (oder fehlende) werden als "
                  "0 angezeigt — fängt „Aus“-Parkwerte wie 80000 ab."),
    "display_row": ("Display-Zeile", "Obere oder untere Zeile des Panel-Displays."),
    "ap_master": ("AP-Master-Var", "Bool-Variable für die Autopilot-Master-LED."),
    "mode_var": ("Modus-Var", "Variable mit dem aktiven AP-Modus (steuert die Modus-LEDs)."),
    "power": ("Power-Gate", "Bool-Variable: bei 0 bleiben Display/LEDs dunkel (z. B. "
              "Batterie aus). Leer = immer an."),
    "device": ("Gerät", "Geräte-ID aus config/devices.yaml (z. B. yoke)."),
    "cw": ("Code rechtsdrehen", "Eingabe-Code für eine Rastung im Uhrzeigersinn (heller)."),
    "ccw": ("Code linksdrehen", "Eingabe-Code für eine Rastung gegen den Uhrzeigersinn "
            "(dunkler)."),
    "var": ("Variable", "Sim-/L-Variable, die auf den skalierten Wert gesetzt wird."),
    "event": ("Event", "K:-Event, das mit dem skalierten Wert gefeuert wird."),
    "full": ("Vollwert", "Wert der Lampe bei 100 % Helligkeit (Skala des Ziels)."),
    "follow_event": ("Folge-Event", "An/Aus-Licht, das mitschaltet, sobald der Dimmer über "
                     "dem Minimum steht."),
    "nose": ("Bugrad-Var", "Positions-Variable des Bugfahrwerks (0=oben … 1=unten)."),
    "left": ("Links-Var", "Positions-Variable des linken Hauptfahrwerks."),
    "right": ("Rechts-Var", "Positions-Variable des rechten Hauptfahrwerks."),
    "down_at": ("Grün ab", "Ab dieser Position gilt das Rad als ausgefahren (grüne LED)."),
    "name": ("Name", "Bezeichnung, nur für Anzeige/Logs."),
    "row": ("Display-Hälfte", "Obere oder untere Hälfte des Radio-Panel-Displays."),
    # A Radio unit has ONE dual-concentric encoder (outer + inner rings, pushable);
    # no left/right — the two directions are the rotation sense (CW/CCW).
    "outer_cw": ("Außen · im UZS",
                 "Eingabe-Code: äußerer (grober) Encoder-Ring im Uhrzeigersinn."),
    "outer_ccw": ("Außen · gegen UZS",
                  "Eingabe-Code: äußerer Encoder-Ring gegen den Uhrzeigersinn."),
    "inner_cw": ("Innen · im UZS",
                 "Eingabe-Code: innerer (feiner) Encoder-Ring im Uhrzeigersinn."),
    "inner_ccw": ("Innen · gegen UZS",
                  "Eingabe-Code: innerer Encoder-Ring gegen den Uhrzeigersinn."),
    "swap": ("Druck (Tausch)",
             "Eingabe-Code des Drückens auf den Doppelencoder (ACT↔STBY-Tausch)."),
    "active": ("Aktiv-Frequenz", "Variable der ACTIVE-Frequenz (obere Display-Zeile)."),
    "standby": ("Standby-Frequenz", "Variable der STANDBY-Frequenz (wird getunt, untere "
                "Zeile)."),
    "swap_event": ("Tausch-Event", "Event, das ACTIVE und STANDBY tauscht."),
    "whole_inc": ("MHz hoch", "Event des äußeren Encoder-Rings: ganze MHz aufwärts."),
    "whole_dec": ("MHz runter", "Event des äußeren Encoder-Rings: ganze MHz abwärts."),
    "fract_inc": ("kHz hoch", "Event des inneren Encoder-Rings: Fein-Schritt aufwärts."),
    "fract_dec": ("kHz runter", "Event des inneren Encoder-Rings: Fein-Schritt abwärts."),
    "fract_fast_inc": ("kHz hoch (schnell)", "Event bei schnellem Drehen (gröberer "
                       "Schritt). Leer = wie kHz hoch."),
    "fract_fast_dec": ("kHz runter (schnell)", "Event bei schnellem Drehen abwärts. "
                       "Leer = wie kHz runter."),
    "fine_view": ("Fein-Anzeige", "Innerer Encoder-Ring schaltet die Standby-Zeile auf 3 "
                  "Nachkommastellen (nur COM 8.33 sinnvoll)."),
    "distance": ("Distanz-Var", "DME-Entfernungs-Variable (nautische Meilen)."),
    "speed": ("Geschw.-Var", "DME-Geschwindigkeits-Variable (Knoten)."),
    "source_var": ("Quellen-Var", "LVar mit der DME-Quelle (0=NAV1, 1=NAV2) — bidirektional "
                   "mit dem Cockpit-Schalter. Leer = nur lokal durchschalten."),
    "code_var": ("Squawk-Var", "Variable des Transponder-Codes (BCD16)."),
    "dig1_var": ("Hunderter-Var", "KR-85-Zähler der Hunderter-Gruppe (0-16)."),
    "dig2_var": ("Zehner-Var", "KR-85-Zähler der Zehnerstelle (0-9)."),
    "dig3_var": ("Einer-Var", "KR-85-Zähler der Einerstelle (0-9)."),
    "min_khz": ("kHz-Minimum", "Kleinste einstellbare ADF-Frequenz."),
    "max_khz": ("kHz-Maximum", "Größte einstellbare ADF-Frequenz."),
    "baro_var": ("QNH-Var", "Variable des Luftdrucks für die untere Zeile (inHg). Leer = "
                 "Zeile bleibt dunkel."),
    "baro_scale": ("QNH-Faktor", "Multiplikator der QNH-Var nach inHg (schon inHg = 1)."),
    "baro_inc": ("QNH hoch", "Event des äußeren Encoder-Rings: Luftdruck aufwärts."),
    "baro_dec": ("QNH runter", "Event des äußeren Encoder-Rings: Luftdruck abwärts."),
}


def output_field_help(path: tuple) -> str:
    """German explanation for the leaf at ``path`` (plus its YAML name), or ''."""
    name = path[-1] if path else ""
    if not isinstance(name, str):
        return ""
    entry = OUTPUT_FIELD_HELP.get(name)
    return f"{tr(entry[1])}  (YAML: {name})" if entry else ""

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


# short German entry words so the tree's name column stays uncluttered
_ENTRY_WORD = {
    "selector": "Position",
    "banks": "Bank",
    "targets": "Ziel",
    "sources": "Quelle",
    "alt_sources": "Alt-Quelle",
    "units": "Einheit",
}


def _entry_label(name: str, i: int, item) -> str:
    tag = getattr(item, "label", None) or getattr(item, "name", None) \
        or getattr(item, "var", None) or getattr(item, "event", None) or ""
    kind = getattr(item, "kind", "")
    word = tr(_ENTRY_WORD.get(name, name))
    label = f"{word} {tag}" if tag else f"{word} {i + 1}"
    if kind and name == "banks":
        label += f" · {kind}"
    return label


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
            label = tr(OUTPUT_FIELD_HELP.get(name, (name, ""))[0])  # German where known
            nodes.append(OutputNode(
                fpath, label, _display(val), kind, choices=choices, optional=optional,
                pickable=(kind == "str" and name not in _NOT_PICKABLE),
            ))
            continue
        origin = typing.get_origin(field.annotation)
        if origin is list:
            addable = name if (name in _LIST_TEMPLATES or name == "banks") else None
            nodes.append(OutputNode(fpath, tr(FIELD_LABEL.get(name, name)),
                                    f"({len(val)})", "list", addable=addable))
            for i, item in enumerate(val):
                nodes.append(OutputNode((*fpath, i), _entry_label(name, i, item),
                                        "", "entry", removable=True))
                _walk_output(item, (*fpath, i), nodes)
            continue
        if origin is dict:
            if name in _RO_DICTS:  # mode->button maps: value-keyed, YAML-configured
                summary = ", ".join(f"{k}:{v}" for k, v in val.items()) or "—"
                nodes.append(OutputNode(fpath, tr(FIELD_LABEL.get(name, name)),
                                        summary, "ro"))
                continue
            nodes.append(OutputNode(fpath, tr(FIELD_LABEL.get(name, name)),  # bool_leds
                                    f"({len(val)})", "dict", addable=name))
            for key, v in val.items():
                nodes.append(OutputNode((*fpath, key), key, str(v), "str",
                                        pickable=True, removable=True))
            continue
        if isinstance(val, BaseModel):
            nodes.append(OutputNode(fpath, tr(FIELD_LABEL.get(name, name)), "", "group",
                                    removable=optional))
            _walk_output(val, fpath, nodes)
            continue
        if val is None and optional:  # unset optional model (dimmer/source_toggle)
            nodes.append(OutputNode(fpath, tr(FIELD_LABEL.get(name, name)), "—", "unset",
                                    addable=name if name in OPTIONAL_TEMPLATES else None))
            continue
        nodes.append(OutputNode(fpath, name, _display(val), "ro"))


def output_nodes(output: Output) -> list[OutputNode]:
    """Flatten one output block into editor tree nodes (depth-first order)."""
    nodes: list[OutputNode] = []
    _walk_output(output, (), nodes)
    return nodes


# The output editor groups fields into meaning-blocks (per user: no raw field
# tree): the tree lists containers, the window shows one group's scalar fields
# with German labels + help.
GROUP_KINDS = ("group", "entry", "list", "dict", "unset")
_SCALAR_KINDS = ("str", "int", "float", "bool", "choice")

# Fields that are distinct PHYSICAL things (the three gear LEDs) become their
# own tree rows with their own tiny window — per user: three LED rows must not
# all open the same collective window. Keyed by field name (root level only).
_SOLO_FIELDS = {"nose": "LED Bugrad", "left": "LED links", "right": "LED rechts"}


def output_groups(nodes: list[OutputNode]) -> list[OutputNode]:
    """Tree groups: root pseudo-group, containers, plus solo physical fields."""
    root = OutputNode((), "Allgemein", "", "root")
    groups = [root]
    for n in nodes:
        if n.kind in GROUP_KINDS:
            groups.append(n)
        elif len(n.path) == 1 and n.path[0] in _SOLO_FIELDS:
            groups.append(OutputNode(n.path, tr(_SOLO_FIELDS[n.path[0]]), n.value, "solo"))
    return groups


def group_fields(nodes: list[OutputNode], group_path: tuple) -> list[OutputNode]:
    """The scalar fields sitting directly inside one group (form content)."""
    group_path = tuple(group_path)
    if group_path and len(group_path) == 1 and group_path[0] in _SOLO_FIELDS:
        # a solo group's window edits exactly its own field
        return [n for n in nodes if n.path == group_path]
    depth = len(group_path) + 1
    return [
        n for n in nodes
        if len(n.path) == depth and n.path[:-1] == group_path
        and n.kind in _SCALAR_KINDS
        and not (depth == 1 and n.path[0] in _SOLO_FIELDS)  # solos live apart
    ]


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
            raise ValueError(tr("{name}: Wert fehlt.", name=name))
        return UNSET if field.default is None else None
    if kind == "int":
        return _parse_int(s, name)
    if kind == "float":
        return _parse_num(s, name)
    if kind == "choice":
        if s not in choices:
            raise ValueError(
                tr("{name}: muss eins von {choices} sein.", name=name, choices=", ".join(choices)))
        return s
    if kind == "bool":
        if s.lower() in ("1", "true", "ja", "an", "on"):
            return True
        if s.lower() in ("0", "false", "nein", "aus", "off"):
            return False
        raise ValueError(tr("{name}: ja/nein erwartet.", name=name))
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
    """{(live-kind, code): [detail-row iids]} for one device's bindings.

    evdev reports axes AND hats as EV_ABS ("axis") and buttons as EV_KEY
    ("button"); hidraw panel switches report as ("switch", byte*8+bit) — the same
    global bit index the profile stores as the switch's code, so those rows light
    up live too once the hidraw reader is wired in.
    """
    rows: dict[tuple[str, int], list[str]] = {}
    for i, b in enumerate(profile.bindings.get(device_id, [])):
        kind = str(b.source.kind)
        if kind in ("axis", "hat"):
            key = ("axis", b.source.code)
        elif kind == "button":
            key = ("button", b.source.code)
        elif kind == "switch":  # hidraw panel switches (live via hidraw_reader)
            key = ("switch", b.source.code)
        else:
            continue
        rows.setdefault(key, []).append(f"bind:{i}")
    return rows


# Whole-block templates so a panel controller can be CREATED per device (user
# wish), then filled in through the group windows. Each validates as-is.
OUTPUT_BLOCK_TEMPLATES: dict[str, dict] = {
    "Switch Panel: Fahrwerks-LEDs": {"type": "gear_leds"},
    "Multi Panel (Selektor + Display)": {
        "type": "multi_panel",
        "selector": [{"code": 0, "label": "ALT",
                      "simvar": "AUTOPILOT ALTITUDE LOCK VAR", "min": 0, "max": 99999}],
    },
    "Radio Panel (2 Einheiten möglich)": {
        "type": "radio_panel",
        "units": [{
            "name": "upper", "row": "upper",
            "outer_cw": 0, "outer_ccw": 1, "inner_cw": 2, "inner_ccw": 3, "swap": 4,
            "banks": [{"code": 0, "label": "COM1",
                       "active": "COM ACTIVE FREQUENCY:1",
                       "standby": "COM STANDBY FREQUENCY:1",
                       "swap_event": "COM_STBY_RADIO_SWAP",
                       "whole_inc": "COM_RADIO_WHOLE_INC",
                       "whole_dec": "COM_RADIO_WHOLE_DEC",
                       "fract_inc": "COM_RADIO_FRACT_INC",
                       "fract_dec": "COM_RADIO_FRACT_DEC"}],
        }],
    },
}

# Input/output role per container (user: LEDs glow = Anzeige, pressing and
# turning = Eingabe — the table must say which is which).
_GROUP_ROLE = {
    "nose": "Anzeige (LED)",
    "left": "Anzeige (LED)",
    "right": "Anzeige (LED)",
    "selector": "Eingabe→Anzeige",
    "alt_sources": "Anzeige-Quelle",
    "bool_leds": "Anzeige (LED)",
    "dimmer": "Eingabe (Drehrad)",
    "targets": "Anzeige (Licht)",
    "source_toggle": "Eingabe",
    "units": "Eingabe→Anzeige",
    "banks": "Eingabe→Anzeige",
    "sources": "Anzeige",
}


def group_role(path: tuple) -> str:
    """Eingabe/Anzeige classification for a group row (innermost container wins)."""
    for part in reversed(path):
        if isinstance(part, str) and part in _GROUP_ROLE:
            return tr(_GROUP_ROLE[part])
    return ""


# --------------------------------------------------------------------------- #
# conditions (when:) <-> editable rows (pure; the GUI renders widgets around it)
# --------------------------------------------------------------------------- #
CONDITION_OPS = ("==", "!=", "<", "<=", ">", ">=")


def conditions_to_rows(when) -> list[dict]:
    """Flatten ``when:`` conditions into editable string rows."""
    return [{"var": c.var, "op": c.op, "value": _fmt_num(c.value)} for c in when]


def rows_to_conditions(rows: list[dict]) -> list[dict]:
    """Editor rows -> ``when:`` dicts (defaults omitted); German ValueError."""
    out: list[dict] = []
    for row in rows:
        var = (row.get("var") or "").strip()
        if not var:
            raise ValueError(tr("Bedingung: Variable fehlt (über Wählen… setzen)."))
        op = row.get("op") or "=="
        if op not in CONDITION_OPS:
            raise ValueError(tr("Bedingung: unbekannter Vergleich '{op}'.", op=op))
        value = _parse_num(row.get("value"), "Bedingungs-Wert")
        cond: dict = {"var": var}
        if op != "==":
            cond["op"] = op
        if value != 1:
            cond["value"] = value
        out.append(cond)
    return out
