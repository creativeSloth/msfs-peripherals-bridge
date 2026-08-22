#!/usr/bin/env python3
"""Stage 1 SPAD.neXt importer — extract mapping *semantics* from a SPAD profile.

This is the low-risk half of "turn a SPAD.neXt profile into one of ours" (see
docs/spadnext-import.md). It does NOT try to auto-generate final bindings,
because SPAD identifies inputs by symbolic HID channel names (``TUNER_INNER_
CLOCKWISE``, ``ACTIVATESHORT``) that have no automatic translation to the raw
Linux evdev/hidraw codes our profiles use. What *is* portable is the semantics:
which control does what SimVar/event, with which conditions.

So this tool reads a ``*.xml`` SPAD profile and emits a per-device, per-control
catalog of translated actions (event / set / increment / decrement, plus
``when`` conditions) in OUR naming conventions. Feed that catalog into the
mapper's action picker (or just read it) so the tedious "what should this fire"
is pre-filled; the human still points at the physical input.

Namespaces are translated to our subscription conventions:
    SIMCONNECT:/MSFS:<NAME>[:idx]  -> bare SimVar / event name
    LVAR:<NAME>                    -> L:<NAME>
    LOCAL:<NAME>                   -> V:<NAME>   (SPAD-internal; flagged)

Usage:
    python tools/spadnext_import.py "Arrow III.xml"            # Markdown report
    python tools/spadnext_import.py "Arrow III.xml" -o out.md  # save report
    python tools/spadnext_import.py "Arrow III.xml" --json catalog.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEVICES_YAML = REPO_ROOT / "config" / "devices.yaml"

# ---------------------------------------------------------------------------
# Translation tables
# ---------------------------------------------------------------------------

# SPAD ConditionComparator -> our `when` op. (Values seen across all sample
# profiles: Equals, Unequal, Less, Greater, GreaterOrEqual, LessOrEqual, Always,
# Range. "Always" and "Range" have no single-op equivalent and are kept verbatim.)
_COMPARATOR = {
    "Equals": "==",
    "Unequal": "!=",
    "Less": "<",
    "Greater": ">",
    "GreaterOrEqual": ">=",
    "LessOrEqual": "<=",
}

# Trigger -> (input kind hint, edge). Anything not listed is reported verbatim
# and classed as "review".
_TRIGGER_INPUT = {
    "PRESS": ("button", "press"),
    "PRESSSHORT": ("button", "press"),
    "PRESSLONG": ("button", "long-press"),
    "ACTIVATESHORT": ("button", "press"),
    "ACTIVATELONG": ("button", "long-press"),
    "ACTIVATE": ("button", "press"),
    "RELEASE": ("button", "release"),
    "VALUE": ("switch", "value"),
    "VALUEON": ("switch", "on"),
    "VALUEOFF": ("switch", "off"),
    "VALUEOFFSHORT": ("switch", "off"),
    "TUNER_INNER_CLOCKWISE": ("encoder", "inner-cw"),
    "TUNER_INNER_COUNTERCLOCKWISE": ("encoder", "inner-ccw"),
    "TUNER_OUTER_CLOCKWISE": ("encoder", "outer-cw"),
    "TUNER_OUTER_COUNTERCLOCKWISE": ("encoder", "outer-ccw"),
    "TUNER_CLOCKWISE": ("encoder", "cw"),
    "TUNER_COUNTERCLOCKWISE": ("encoder", "ccw"),
    "NOSEUP": ("switch", "up"),
    "NOSEDOWN": ("switch", "down"),
}

# Triggers that describe an OUTPUT (display / lamp), not an input.
_TRIGGER_OUTPUT = {"LEFTDISPLAY", "RIGHTDISPLAY", "DISPLAY", "BUTTONLIGHT"}

# VALUEON_MODE1 etc. — mode-qualified switch states.
_MODE_TRIGGER = re.compile(r"^(VALUEON|VALUEOFF|VALUE)_MODE(\d+)$")


def translate_target(raw: str) -> str:
    """SPAD ``NAMESPACE:NAME[:idx]`` -> our subscription/event name."""
    if not raw:
        return raw
    ns, _, rest = raw.partition(":")
    ns = ns.upper()
    if ns == "LVAR":
        return f"L:{rest}"
    if ns == "LOCAL":
        return f"V:{rest}"  # SPAD-internal script var; no sim equivalent
    # SIMCONNECT / MSFS: bare SimVar or event name (keep any trailing :idx).
    return rest


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class Action:
    """One translated SPAD EventAction."""

    verb: str  # event | set | increment | decrement | display | led | command | axis
    target: str  # translated name (or SPAD command name)
    value: str | None = None
    portable: bool = True  # False -> no clean equivalent in our model
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"verb": self.verb, "target": self.target}
        if self.value is not None:
            d["value"] = self.value
        if not self.portable:
            d["portable"] = False
        if self.note:
            d["note"] = self.note
        return d


@dataclass
class Condition:
    var: str
    op: str
    value: str

    def to_dict(self) -> dict[str, Any]:
        return {"var": self.var, "op": self.op, "value": self.value}


@dataclass
class Entry:
    """One (control, trigger) row: what fires and under which conditions."""

    control: str  # SPAD BoundTo
    trigger: str  # SPAD Trigger (verbatim)
    kind: str  # input | output | review
    hint: str  # e.g. "encoder inner-cw"
    actions: list[Action] = field(default_factory=list)
    when: list[Condition] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "control": self.control,
            "trigger": self.trigger,
            "kind": self.kind,
            "hint": self.hint,
            "actions": [a.to_dict() for a in self.actions],
        }
        if self.when:
            d["when"] = [c.to_dict() for c in self.when]
        return d


@dataclass
class DeviceCatalog:
    vendor: str
    product: str
    serial: str
    our_id: str | None
    our_name: str | None
    entries: list[Entry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "vendor": self.vendor,
            "product": self.product,
            "serial": self.serial,
            "our_id": self.our_id,
            "our_name": self.our_name,
            "entries": [e.to_dict() for e in self.entries],
        }


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def _strip_ns(root: ET.Element) -> None:
    """Drop the default XML namespace so we can match on plain tag names."""
    for el in root.iter():
        if "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]


def _norm_hex(raw: str) -> str:
    """``0x06A3`` / ``06A3`` -> ``06a3`` (4 lowercase hex, matching devices.yaml)."""
    v = raw.lower().removeprefix("0x")
    return v.zfill(4)


def load_device_map() -> dict[tuple[str, str], tuple[str, str]]:
    """(vendor, product) -> (our id, our name) from config/devices.yaml."""
    out: dict[tuple[str, str], tuple[str, str]] = {}
    if not DEVICES_YAML.exists():
        return out
    try:
        import yaml

        data = yaml.safe_load(DEVICES_YAML.read_text()) or {}
        for dev in data.get("devices", []):
            v = _norm_hex(str(dev.get("vendor", "")))
            p = _norm_hex(str(dev.get("product", "")))
            out[(v, p)] = (dev.get("id", ""), dev.get("name", ""))
    except Exception:  # pragma: no cover - best-effort enrichment only
        pass
    return out


def _parse_action(el: ET.Element) -> Action | None:
    tag = el.tag
    target = translate_target(el.get("TargetDataDefinition", ""))
    if tag == "EventActionControl":
        val = el.get("Value") or None
        return Action("event", target, value=val)
    if tag == "EventActionChangeValue":
        op = (el.get("ValueOperation") or "").lower()
        val = el.get("Value")
        verb = {"increment": "increment", "decrement": "decrement"}.get(op, "set")
        note = ""
        portable = True
        if verb in ("increment", "decrement"):
            note = "relative change — map to an INC/DEC event or a stepped simvar write"
        return Action(verb, target, value=val, portable=portable, note=note)
    if tag == "EventActionDisplayValue":
        fmt = el.get("DisplayFormat") or ""
        return Action("display", target, value=fmt or None, note="output: show value on a display")
    if tag == "EventActionButtonLight":
        return Action(
            "led",
            el.get("TargetName", ""),
            value=el.get("ButtonLight"),
            note="output: button lamp",
        )
    if tag == "EventActionLEDColor":
        return Action("led", "", value=el.get("Color"), note="output: LED colour")
    if tag == "EventActionCommand":
        return Action(
            "command",
            el.get("CommandName", ""),
            portable=False,
            note="SPAD-internal command — no equivalent, handled natively by us",
        )
    if tag == "EventActionRangedAxis":
        return Action(
            "axis",
            el.get("ConfigID", ""),
            portable=False,
            note="axis — configure the range in our mapper, not importable 1:1",
        )
    return None


def _classify(trigger: str) -> tuple[str, str]:
    """Return (kind, hint) for a trigger name.

    Falls back through general suffix rules so device-specific position names
    (``SEL_ALL_VALUEON``, ``POV_NORTH_PRESS``, ``VALUEONLONG``) still land as
    inputs instead of "review".
    """
    if trigger in _TRIGGER_OUTPUT:
        return "output", trigger.lower()
    if trigger in _TRIGGER_INPUT:
        kind, edge = _TRIGGER_INPUT[trigger]
        return "input", f"{kind} {edge}"
    m = _MODE_TRIGGER.match(trigger)
    if m:
        state, mode = m.group(1), m.group(2)
        edge = {"VALUEON": "on", "VALUEOFF": "off", "VALUE": "value"}[state]
        return "input", f"switch {edge} (mode {mode})"
    # General suffix rules -------------------------------------------------
    if trigger.endswith("DISPLAY"):
        return "output", trigger.lower()
    long = "LONG" in trigger
    if "VALUEON" in trigger:
        pos = trigger.replace("VALUEON", "").replace("LONG", "").strip("_")
        edge = "on" + (" (long)" if long else "")
        return "input", f"switch {edge}" + (f" @{pos.lower()}" if pos else "")
    if "VALUEOFF" in trigger:
        pos = trigger.replace("VALUEOFF", "").replace("LONG", "").strip("_")
        edge = "off" + (" (long)" if long else "")
        return "input", f"switch {edge}" + (f" @{pos.lower()}" if pos else "")
    if trigger.endswith("_PRESS"):
        name = trigger[: -len("_PRESS")].lower()
        return "input", f"button press ({name})"
    return "review", trigger.lower()


def parse_profile(path: Path) -> list[DeviceCatalog]:
    tree = ET.parse(path)
    root = tree.getroot()
    _strip_ns(root)
    devmap = load_device_map()

    catalogs: list[DeviceCatalog] = []
    for dev in root.iter("Device"):
        vendor = _norm_hex(dev.get("VendorID", ""))
        product = _norm_hex(dev.get("ProductID", ""))
        our = devmap.get((vendor, product))
        cat = DeviceCatalog(
            vendor=vendor,
            product=product,
            serial=dev.get("Serial", ""),
            our_id=our[0] if our else None,
            our_name=our[1] if our else None,
        )
        for event in dev.iter("Event"):
            control = event.get("BoundTo", "")
            for edef in event.iter("EventDefinition"):
                trigger = edef.get("Trigger", "")
                kind, hint = _classify(trigger)
                entry = Entry(control=control, trigger=trigger, kind=kind, hint=hint)
                cond_parent = edef.find("EventConditions")
                if cond_parent is not None:
                    for c in cond_parent.iter("EventCondition"):
                        comp = c.get("ConditionComparator", "Equals")
                        entry.when.append(
                            Condition(
                                var=translate_target(c.get("ConditionValueSource", "")),
                                op=_COMPARATOR.get(comp, comp),
                                value=c.get("ConditionTargetValue", ""),
                            )
                        )
                act_parent = edef.find("EventActions")
                if act_parent is not None:
                    for a in list(act_parent):
                        parsed = _parse_action(a)
                        if parsed is not None:
                            entry.actions.append(parsed)
                # Only keep rows that actually do something.
                if entry.actions:
                    cat.entries.append(entry)
        if cat.entries:
            catalogs.append(cat)
    return catalogs


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def _fmt_action(a: Action) -> str:
    if a.verb == "event":
        s = f"`event {a.target}`" + (f" = {a.value}" if a.value else "")
    elif a.verb == "set":
        s = f"`set {a.target} = {a.value}`"
    elif a.verb in ("increment", "decrement"):
        sign = "+" if a.verb == "increment" else "-"
        s = f"`{a.target} {sign}= {a.value}`"
    elif a.verb == "display":
        s = f"display `{a.target}`" + (f" ({a.value})" if a.value else "")
    elif a.verb == "led":
        s = f"led `{a.target or a.value}`"
    elif a.verb == "command":
        s = f"SPAD command `{a.target}`"
    elif a.verb == "axis":
        s = f"axis `{a.target}`"
    else:
        s = f"{a.verb} {a.target}"
    if not a.portable:
        s = "⚠ " + s
    return s


def _fmt_when(when: list[Condition]) -> str:
    return " AND ".join(f"{c.var} {c.op} {c.value}" for c in when)


def render_markdown(catalogs: list[DeviceCatalog], src: str) -> str:
    lines: list[str] = []
    lines.append("# SPAD.neXt import — semantic catalog\n")
    lines.append(f"Source: `{src}`\n")

    # Summary
    tot = sum(len(c.entries) for c in catalogs)
    n_in = sum(1 for c in catalogs for e in c.entries if e.kind == "input")
    n_out = sum(1 for c in catalogs for e in c.entries if e.kind == "output")
    n_rev = sum(1 for c in catalogs for e in c.entries if e.kind == "review")
    n_warn = sum(1 for c in catalogs for e in c.entries for a in e.actions if not a.portable)
    lines.append("## Summary\n")
    lines.append(f"- Devices with mappings: **{len(catalogs)}**")
    lines.append(f"- Matched to one of our devices: **{sum(1 for c in catalogs if c.our_id)}**")
    lines.append(
        f"- Rows (control x trigger): **{tot}** — inputs {n_in}, outputs {n_out}, review {n_rev}"
    )
    lines.append(f"- Rows needing manual handling (⚠, SPAD-internal/relative/axis): **{n_warn}**\n")
    lines.append(
        "> Inputs are the portable gold: physical control → event/simvar with "
        "`when` conditions. Outputs (displays/LEDs) map to our output concepts "
        "but are wired via panel controllers, not per-binding. ⚠ rows have no "
        "clean 1:1 equivalent — see the note.\n"
    )

    for cat in catalogs:
        head = f"0x{cat.vendor}:0x{cat.product}"
        if cat.our_id:
            head += f" → **our `{cat.our_id}`** ({cat.our_name})"
        else:
            head += " → *(no matching device in config/devices.yaml)*"
        lines.append(f"## {head}\n")
        # group by control
        by_control: dict[str, list[Entry]] = {}
        for e in cat.entries:
            by_control.setdefault(e.control, []).append(e)
        for control, entries in by_control.items():
            lines.append(f"### {control}\n")
            lines.append("| Trigger | Input | Action(s) | When |")
            lines.append("|---|---|---|---|")
            for e in entries:
                acts = "<br>".join(_fmt_action(a) for a in e.actions)
                when = _fmt_when(e.when)
                lines.append(f"| `{e.trigger}` | {e.hint} | {acts} | {when} |")
            lines.append("")
    return "\n".join(lines)


def to_payload(catalogs: list[DeviceCatalog], source: str) -> dict[str, Any]:
    """The machine-readable catalog (same shape as ``--json``).

    Kept separate from ``main`` so the GUI can build it directly from
    ``parse_profile`` without going through a temp file.
    """
    return {"source": source, "devices": [c.to_dict() for c in catalogs]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("xml", type=Path, help="SPAD.neXt profile .xml")
    ap.add_argument("-o", "--out", type=Path, help="write Markdown report here")
    ap.add_argument("--json", type=Path, help="also write a machine-readable catalog")
    args = ap.parse_args(argv)

    if not args.xml.exists():
        print(f"error: {args.xml} not found", file=sys.stderr)
        return 2

    catalogs = parse_profile(args.xml)
    report = render_markdown(catalogs, args.xml.name)

    if args.out:
        args.out.write_text(report)
        print(f"wrote {args.out} ({len(report)} bytes)")
    else:
        print(report)

    if args.json:
        payload = to_payload(catalogs, args.xml.name)
        args.json.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
        print(f"wrote {args.json}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
