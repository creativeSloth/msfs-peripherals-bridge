"""Physical-layout reconstruction of the Saitek panels for the Mapper tab.

Turns one profile's bindings/outputs for a panel device into positioned,
display-ready :class:`PanelElement` records the GUI paints on a canvas at *~their
real position* on the hardware — so a switch/LED/selector can be found by where
it physically sits, not by scanning a table. Pure and tkinter-free (positions
are normalised ``0..1``), so it unit-tests without a display.

Only the three Saitek panels earn a hand-drawn layout (positions read off the
hardware); any other device falls back to an auto-grid so the view still works.

The live overlay reuses the Mapper tab's existing state dict: an element's
``live_key`` is the same ``(kind, code)`` key the evdev/hidraw ``live_state_reader``
emits (see :func:`gui_mapper.live_row_map`), so a flicked switch highlights live.
LED glow-from-sim and display values are a later increment (they need the sim
value monitor, not the raw hidraw state).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from math import ceil, sqrt

from .gui_mapper import describe_action, output_groups, output_nodes
from .models import GearLedOutput, Profile, RadioPanelOutput

# --- element kinds (what the canvas draws) --------------------------------- #
SWITCH = "switch"  # two-position toggle / momentary — highlights when live-on
BUTTON = "button"  # push-button (yoke/multi/radio) — same live behaviour
SELECTOR = "selector"  # rotary detent group (e.g. magnetos) — one wide element
LED = "led"  # indicator lamp driven by an output (glow-from-sim = later)
LEVER = "lever"  # gear lever and the like — two momentary edges in one element
AXIS = "axis"  # analog control — drawn as a live-filling bar with a value readout
HAT = "hat"  # POV hat — one element grouping its direction actions
ENCODER = "encoder"  # a rotary encoder knob (radio outer/inner + mode selector)
HEADER = "header"  # a group heading (title + separator line) — not interactive
# --- output/display element types (driven BY the sim, mapped like inputs) ---- #
SEGMENT = "segment"  # a 7-seg display cell (selector/bank value)
DOT = "dot"  # a display decimal-point / annunciator dot
BUTTON_LIGHT = "button_light"  # a button's backlight LED (bool_leds)

# Element kinds shown in the DISPLAY zone (everything else = the controls zone).
_DISPLAY_KINDS = frozenset({LED, SEGMENT, DOT, BUTTON_LIGHT})


@dataclass(frozen=True)
class PanelElement:
    """One drawable control at a normalised position on the panel canvas."""

    kind: str
    label: str  # hardware silkscreen caption (always present — recognise the panel)
    x: float  # normalised 0..1 top-left / size, canvas multiplies by its px extent
    y: float
    w: float
    h: float
    name: str = ""  # mapped binding/output name ("" = the profile leaves it unmapped)
    action: str = ""  # one-line action summary (shown as the element's tooltip)
    code: int | None = None  # switch/button bit code, else None
    ref: str | None = None  # detail-tree iid the GUI opens on click ("bind:i" / "out:i")
    mapped: bool = False  # False = physical control with no profile mapping (drawn muted)
    live_key: tuple[str, int] | None = None  # ("switch"/"button"/"axis", code) for the overlay
    raw_min: int | None = None  # AXIS only: calibrated bar range (None -> live range/default)
    raw_max: int | None = None
    # Source kind to pre-fill when an EMPTY element is clicked to create a binding.
    # "" = derive from `kind`; set explicitly where the visual kind differs from the
    # physical source (e.g. a magneto detent drawn as a bar but sourced as a switch).
    source_kind: str = ""
    # Glow-from-sim: the variable whose live value drives this display element and
    # the lamp on-threshold. `var` None = no sim readout (an input control, or a
    # display type not wired to the value monitor yet); `on_at` None = numeric
    # segment (show the value) rather than a boolean lamp.
    var: str | None = None
    on_at: float | None = None
    # Controller-faithful text format for a numeric SEGMENT's live value (glow):
    # "" = compact raw, "int" = rounded (like format_row), "dec:N" = N decimals with
    # a negative/None blanked (like format_measure/format_frequency). See format_segment.
    fmt: str = ""


def format_segment(value: object, fmt: str = "") -> str:
    """Controller-faithful text for a display segment's live value (glow-from-sim).

    ``fmt`` mirrors the Saitek 7-segment encoding so the reconstruction reads like
    the hardware instead of a raw float: ``"int"`` rounds (like ``format_row``),
    ``"dec:N"`` shows N decimals and blanks a negative value (like
    ``format_measure``/``format_frequency`` — a radio freq is ``"dec:2"`` -> 118.00),
    ``""`` is a compact raw readout. ``None`` (no reading yet) -> ``""`` (blank cell).
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)
    if fmt == "int":
        return str(round(v))
    if fmt.startswith("dec:"):
        try:
            n = int(fmt[4:])
        except ValueError:
            n = 1
        return "" if v < 0 else f"{v:.{n}f}"
    return f"{v:.4g}"


def lamp_lit(value: object, on_at: float | None) -> bool:
    """Whether a lamp element glows for a sim ``value`` and its ``on_at`` threshold.

    A bool is taken as-is; a number lights the lamp at/above ``on_at`` (default
    0.5). ``None`` (no reading yet) stays dark, so a lamp only glows on a real
    positive reading from the running bridge."""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    try:
        return float(value) >= (0.5 if on_at is None else on_at)
    except (TypeError, ValueError):
        return bool(value)


def _live_key(kind: str, code: int) -> tuple[str, int] | None:
    """The live-state key for a source kind, mirroring gui_mapper.live_row_map."""
    if kind in ("axis", "hat"):
        return ("axis", code)
    if kind == "button":
        return ("button", code)
    if kind == "switch":
        return ("switch", code)
    return None


def _action_summary(binding) -> str:
    """Short action text for a binding's tooltip (hats have no single action)."""
    if binding.hat is not None:
        return "hat"
    return describe_action(binding.action)


# --------------------------------------------------------------------------- #
# Saitek Pro Flight Switch Panel — hand layout (positions read off the device)
# --------------------------------------------------------------------------- #
# One long row of 13 two-position toggle switches across the top; the physical
# silkscreen order (left -> right) with the hidraw bit code the panel sends. The
# short caption is the hardware label, so the reconstruction is recognisable
# even where the profile maps a code to something else (or not at all).
_SP_TOGGLES: tuple[tuple[int, str], ...] = (
    (0, "BAT"), (1, "ALT"), (2, "AVION"), (3, "FUEL"), (4, "DE-ICE"),
    (5, "PITOT"), (6, "COWL"), (7, "PANEL"), (8, "BEACON"), (9, "NAV"),
    (10, "STROBE"), (11, "TAXI"), (12, "LAND"),
)
# Magneto / starter rotary detents (spring-loaded START), left -> right on the knob.
_SP_MAGNETO: tuple[tuple[int, str], ...] = (
    (13, "OFF"), (14, "R"), (15, "L"), (16, "BOTH"), (17, "START"),
)
# Gear lever edges.
_SP_GEAR: tuple[tuple[int, str], ...] = ((18, "UP"), (19, "DN"))
# Gear indicator lamps: (caption, gear_leds field) — each maps its OWN SimVar via
# the output's solo field (nose/left/right), so every LED is mapped individually.
_SP_GEAR_LEDS: tuple[tuple[str, str], ...] = (("N", "nose"), ("L", "left"), ("R", "right"))


def _index_bindings(binds) -> dict[int, tuple[int, object]]:
    """{switch/button code -> (binding index, binding)} — first binding wins."""
    by_code: dict[int, tuple[int, object]] = {}
    for i, b in enumerate(binds):
        by_code.setdefault(b.source.code, (i, b))
    return by_code


def _switch_element(hw_label: str, x: float, y: float, w: float, h: float,
                    code: int, hit: tuple[int, object] | None) -> PanelElement:
    """Build a toggle element, filling name/action/ref from its binding if mapped."""
    if hit is None:
        return PanelElement(SWITCH, hw_label, x, y, w, h, code=code, mapped=False,
                            live_key=("switch", code))
    idx, b = hit
    return PanelElement(
        SWITCH, hw_label, x, y, w, h,
        name=b.name, action=_action_summary(b), code=code,
        ref=f"bind:{idx}", mapped=True, live_key=("switch", code),
    )


def _stacked_bars(x: float, y: float, w: float, h: float,
                  positions, by_code, src_kind: str = "switch") -> list[PanelElement]:
    """K stacked, INDIVIDUALLY clickable sub-bars filling (x, y, w, h).

    One bar per ``(code, label)`` position of a multi-position control (magneto
    detents, gear up/down, a flaps rocker) — so every switch position gets its own
    mapping / click target instead of the whole control sharing one. A mapped
    position opens its binding; an empty one is a placeholder to map (its physical
    ``src_kind`` is carried so the created binding has the right source kind)."""
    out: list[PanelElement] = []
    n = len(positions)
    if n == 0:
        return out
    gap = 0.008
    bh = (h - gap * (n - 1)) / n
    for k, (code, label) in enumerate(positions):
        yy = y + k * (bh + gap)
        hit = by_code.get(code)
        if hit is None:
            out.append(PanelElement(BUTTON, label, x, yy, w, bh, code=code,
                                    mapped=False, source_kind=src_kind,
                                    live_key=_live_key(src_kind, code)))
        else:
            idx, b = hit
            # mapped bars show the clear binding name (not the terse detent code);
            # live_key lights the bar when that position is pressed at the device.
            out.append(PanelElement(
                BUTTON, b.name or label, x, yy, w, bh, name=b.name,
                action=_action_summary(b), code=code, ref=f"bind:{idx}",
                mapped=True, source_kind=src_kind, live_key=_live_key(src_kind, code)))
    return out


def _switch_panel(binds, outs) -> list[PanelElement]:
    """Hand-drawn Saitek Switch Panel: toggle row + magneto rotary + gear, each in
    a titled group (Schalter / Magnetos / Fahrwerk) so the layout reads clearly."""
    by_code = _index_bindings(binds)
    els: list[PanelElement] = []

    # 13 toggle switches evenly spread across the top row, under a group heading.
    els.append(PanelElement(HEADER, "Schalter", 0.02, 0.005, 0.55, 0.045, mapped=True))
    n = len(_SP_TOGGLES)
    margin, gap = 0.02, 0.006
    cw = (1.0 - 2 * margin - (n - 1) * gap) / n
    for j, (code, hw) in enumerate(_SP_TOGGLES):
        x = margin + j * (cw + gap)
        els.append(_switch_element(hw, x, 0.07, cw, 0.30, code, by_code.get(code)))

    # Magneto rotary (bottom-left): each of the 5 detents its own clickable bar.
    els.append(PanelElement(HEADER, "Magnetos", 0.05, 0.46, 0.42, 0.045, mapped=True))
    els.append(PanelElement(HEADER, "Fahrwerk", 0.60, 0.42, 0.37, 0.045, mapped=True))
    els += _stacked_bars(0.05, 0.52, 0.42, 0.38, _SP_MAGNETO, by_code)

    # Gear indicator LEDs (three lamps) — driven by a gear_leds output if present.
    gear_out = next(((k, o) for k, o in enumerate(outs)
                     if isinstance(o, GearLedOutput)), None)
    for j, (lbl, field) in enumerate(_SP_GEAR_LEDS):
        x = 0.60 + j * 0.13
        els.append(PanelElement(
            LED, lbl, x, 0.49, 0.11, 0.15,
            name=(f"LED {field}" if gear_out else ""),
            action=(f"gear_leds · {field}" if gear_out else ""),
            # ref targets the output's SOLO field -> click opens THAT LED's mapping
            ref=(f"out:{gear_out[0]}:{field}" if gear_out else None),
            mapped=gear_out is not None,
            # glow-from-sim: the gear-position var lights the lamp when extended
            var=(getattr(gear_out[1], field, None) if gear_out else None),
            on_at=(0.5 if gear_out else None),
        ))

    # Gear lever (bottom-right): up + down each its own clickable bar.
    els += _stacked_bars(0.60, 0.68, 0.37, 0.23, _SP_GEAR, by_code)
    return els


# --------------------------------------------------------------------------- #
# Generic device layout — used for anything without a hand layout (yoke, TQ6,
# trim, pedals, and the multi/radio panels' buttons). The point is a *consistent*
# picture across device types: analog axes become live-filling bars stacked at
# the top; buttons/switches/hats become a tile grid below. Same click->editor and
# live overlay as the hand-drawn panels.
# --------------------------------------------------------------------------- #
def _grid_cells(n: int, x0: float, y0: float, x1: float,
                y1: float) -> list[tuple[float, float, float, float]]:
    """``n`` (x, y, w, h) cells filling the box, in a roughly landscape grid."""
    cols = max(1, min(n, round(sqrt(n * 1.8)) or 1))
    rows = ceil(n / cols)
    gap = 0.014
    cw = (x1 - x0 - (cols - 1) * gap) / cols
    ch = (y1 - y0 - (rows - 1) * gap) / rows
    return [(x0 + c * (cw + gap), y0 + r * (ch + gap), cw, ch)
            for r, c in (divmod(i, cols) for i in range(n))]


def _axis_element(i: int, b, x: float, y: float, w: float, h: float) -> PanelElement:
    return PanelElement(
        AXIS, b.name or f"Achse {b.source.code}", x, y, w, h,
        name=b.name, action=_action_summary(b), code=b.source.code,
        ref=f"bind:{i}", mapped=True, live_key=("axis", b.source.code),
        raw_min=b.source.raw_min, raw_max=b.source.raw_max,
    )


# Direction words at the END of a binding name pair a momentary (on)-off-(on)
# rocker (e.g. "Flaps up" / "Flaps down"); same base + opposite word = one rocker.
_UP_WORDS = ("up", "auf", "hoch", "inc", "incr", "+")
_DOWN_WORDS = ("down", "dn", "ab", "runter", "dec", "decr", "-")


def _direction_of(name: str) -> tuple[str, str] | None:
    """(base, 'up'|'down') if ``name`` ends in a direction word, else None."""
    words = name.strip().lower().split()
    if not words:
        return None
    last = words[-1]
    base = " ".join(words[:-1])
    if not base:
        return None  # a bare "up"/"down" has no base to pair on
    if last in _UP_WORDS:
        return (base, "up")
    if last in _DOWN_WORDS:
        return (base, "down")
    return None


def _pair_rockers(keys):
    """Merge 'X up' / 'X down' momentary button pairs into (up, down) rockers.

    Returns (rockers, singles) preserving order; a control only pairs when the
    SAME base has both an up- and a down-named binding."""
    by_base: dict[str, dict[str, tuple]] = {}
    for i, b in keys:
        d = _direction_of(b.name)
        if d is not None:
            by_base.setdefault(d[0], {})[d[1]] = (i, b)
    paired_ids = set()
    rockers = []
    for dirs in by_base.values():
        if "up" in dirs and "down" in dirs:
            rockers.append((dirs["up"], dirs["down"]))
            paired_ids.add(id(dirs["up"][1]))
            paired_ids.add(id(dirs["down"][1]))
    singles = [(i, b) for i, b in keys if id(b) not in paired_ids]
    return rockers, singles


def _output_element_text(o, path, g) -> tuple[str, str]:
    """(SHORT tile label, hover detail) for a display element. The label is just
    the mode/bank name (no "Bank", no lowercase kind); the detail explains WHICH
    var is shown + HOW it changes (read-var = display + encoder base)."""
    try:
        if len(path) == 2 and path[0] == "selector":
            e = o.selector[path[1]]
            setter = e.set_event or f"SimVar {e.simvar} direkt schreiben"
            extra = ("  · Quellen: " + ", ".join([e.simvar]
                     + [s.simvar for s in e.alt_sources])) if e.alt_sources else ""
            return e.label, (f"Anzeige liest {e.simvar} ({e.unit}) · ändern via "
                             f"{setter} (±{e.step:g}, {e.min:g}..{e.max:g}){extra}")
        if len(path) == 4 and path[0] == "units" and path[2] == "banks":
            bank = o.units[path[1]].banks[path[3]]
            return getattr(bank, "label", g.label), g.label
    except (IndexError, AttributeError, TypeError):
        pass
    return g.label, str(g.value)


def _display_var(o, p) -> str | None:
    """The sim var a display element reads (glow-from-sim), or None if not wired."""
    try:
        if len(p) == 1 and p[0] in ("nose", "left", "right"):
            return getattr(o, p[0], None)
        if len(p) == 2 and p[0] == "selector":
            return o.selector[p[1]].simvar
    except (IndexError, AttributeError, TypeError):
        pass
    return None


def _output_items(outs) -> tuple[list, list]:
    """(control_items, display_items) — encoders/swap vs displays/lamps.

    Each item is ('out', out_index, path, kind, label, detail, var, on_at, fmt). The
    two lists are laid in SEPARATE zones so buttons and displays are shown apart.
    Abstract config groups (bool_leds/alt_sources/dimmer) are skipped — mapped in the
    editor. Generic-panel LEDs/displays (a user's own device, Schritt E) glow too."""
    controls: list = []
    displays: list = []
    for k, o in enumerate(outs):
        for g in output_groups(output_nodes(o)):
            p = g.path
            if len(p) == 1 and p[0] in ("nose", "left", "right"):
                displays.append(("out", k, p, LED, g.label, str(g.value),
                                 _display_var(o, p), 0.5, ""))
            elif (len(p) == 2 and p[0] == "selector") or (
                    len(p) == 4 and p[0] == "units" and p[2] == "banks"):
                lbl, det = _output_element_text(o, p, g)  # display cell (segment)
                # multi selector cell = integer readout (format_row); radio banks fall
                # back here only without a hand layout (per-digit -> not glow-formatted).
                fmt = "int" if len(p) == 2 else ""
                displays.append(("out", k, p, SEGMENT, lbl, det, _display_var(o, p),
                                 None, fmt))
            elif len(p) == 2 and p[0] == "leds":  # generic_panel LED (glow lamp)
                led = o.leds[p[1]]
                displays.append(("out", k, p, LED, led.name or f"LED {p[1] + 1}",
                                 f"{led.var} ≥ {led.on_at:g}", led.var, led.on_at, ""))
            elif len(p) == 2 and p[0] == "displays":  # generic_panel 7-seg display
                d = o.displays[p[1]]
                fmt = f"dec:{d.decimals}" if d.decimals else "int"
                displays.append(("out", k, p, SEGMENT, d.name or f"Anzeige {p[1] + 1}",
                                 f"Anzeige liest {d.var}", d.var, None, fmt))
            elif len(p) == 2 and p[0] == "units":  # a radio unit's controls
                try:
                    name = o.units[p[1]].name
                except (IndexError, AttributeError):
                    name = str(p[1])
                controls.append(("out", k, p, ENCODER, f"Encoder {name}",
                                 f"Außen-/Innen-Drehknopf + Mode-Selektor · Einheit {name}",
                                 None, None, ""))
                controls.append(("out", k, p, BUTTON, f"Swap {name}",
                                 f"ACT/STBY-Swap-Taste · Einheit {name}", None, None, ""))
    return controls, displays


def _lay_tiles(items, x0: float, y0: float, x1: float, y1: float) -> list[PanelElement]:
    """Grid ``items`` into the box (x0,y0)-(x1,y1); return the built elements."""
    out: list[PanelElement] = []
    if not items or (y1 - y0) < 0.02 or (x1 - x0) < 0.02:
        return out
    for (cx0, cy0, w, h), it in zip(_grid_cells(len(items), x0, y0, x1, y1),
                                    items, strict=True):
        if it[0] == "rocker":
            (ui, ub), (di, db) = it[1], it[2]
            base = ub.name.rsplit(" ", 1)[0] or ub.name
            positions = [(ub.source.code, base), (db.source.code, base)]
            local = {ub.source.code: (ui, ub), db.source.code: (di, db)}
            out += _stacked_bars(cx0, cy0, w, h, positions, local,
                                 src_kind=str(ub.source.kind))
        elif it[0] == "out":
            _, k, p, okind, label, detail, evar, on_at, efmt = it
            out.append(PanelElement(okind, label, cx0, cy0, w, h, action=detail,
                                    ref=f"out:{k}:" + "/".join(map(str, p)), mapped=True,
                                    var=evar, on_at=on_at, fmt=efmt))
        else:  # key / hat binding
            _, i, b = it
            kk = str(b.source.kind)
            kind = HAT if it[0] == "hat" else (BUTTON if kk == "button" else SWITCH)
            out.append(PanelElement(
                kind, b.name or f"#{i}", cx0, cy0, w, h, name=b.name,
                action=_action_summary(b), code=b.source.code, ref=f"bind:{i}",
                mapped=True, live_key=(None if kk == "hat" else _live_key(kk, b.source.code))))
    return out


def _device_layout(binds, outs) -> list[PanelElement]:
    """Axes (top bars) + a CONTROLS zone and a SEPARATE DISPLAYS zone.

    Buttons/switches/rockers/encoders/swap live in the controls zone; segments and
    lamps in the displays zone below it — kept apart (user: buttons and displays
    shown separately) with a clear gap between."""
    axes = [(i, b) for i, b in enumerate(binds) if str(b.source.kind) == "axis"]
    hats = [(i, b) for i, b in enumerate(binds) if str(b.source.kind) == "hat"]
    keys = [(i, b) for i, b in enumerate(binds)
            if str(b.source.kind) in ("button", "switch")]
    ctrl_out, disp_out = _output_items(outs)
    if not (axes or hats or keys or ctrl_out or disp_out):
        return []
    els: list[PanelElement] = []
    margin, gap = 0.03, 0.018

    # Axes: full-width horizontal live bars stacked at the very top.
    y = margin
    if axes:
        zone_bottom = 0.55 if (hats or keys or ctrl_out or disp_out) else (1.0 - margin)
        avail = zone_bottom - margin
        ah = max(0.05, min(0.11, (avail - gap * (len(axes) - 1)) / len(axes)))
        for j, (i, b) in enumerate(axes):
            els.append(_axis_element(i, b, margin, margin + j * (ah + gap),
                                     1.0 - 2 * margin, ah))
        y = margin + len(axes) * (ah + gap)

    rockers, singles = _pair_rockers(keys)
    controls = ([("rocker", u, d) for u, d in rockers]
                + [("key", i, b) for i, b in singles]
                + [("hat", i, b) for i, b in hats] + ctrl_out)
    displays = disp_out

    def _zone(title, items, y0, y1):  # a titled group + its tiles
        if not items or (y1 - y0) < 0.06:
            els.extend(_lay_tiles(items, margin, y0, 1.0 - margin, y1))
            return
        els.append(PanelElement(HEADER, title, margin, y0, 1.0 - 2 * margin, 0.05,
                                mapped=True))
        els.extend(_lay_tiles(items, margin, y0 + 0.058, 1.0 - margin, y1))

    top = y + (gap if axes else 0.0)
    bottom = 1.0 - margin
    if controls and displays:  # separate titled zones: controls up, displays down
        nc, nd = len(controls), len(displays)
        split = min(max(top + (bottom - top) * nc / (nc + nd), top + 0.18), bottom - 0.18)
        _zone("Bedienelemente", controls, top, split - gap)
        _zone("Anzeigen", displays, split + gap, bottom)
    else:
        _zone("Bedienelemente" if controls else "Anzeigen",
              controls or displays, top, bottom)
    return els


# --------------------------------------------------------------------------- #
# Saitek Pro Flight Radio Panel — faithful hand layout (scrolls when tall)
# --------------------------------------------------------------------------- #
def _bank_display_text(bank) -> tuple[str, str, str]:
    """(top-row caption, bottom-row caption, hover detail) per bank type."""
    kind = getattr(bank, "kind", "")
    if kind == "freq":
        return ("ACT", "STBY", f"ACT {bank.active} · STBY {bank.standby} · "
                f"außen {bank.whole_inc}/{bank.whole_dec} · innen "
                f"{bank.fract_inc}/{bank.fract_dec} · swap {bank.swap_event}")
    if kind == "dme":
        srcs = ", ".join(s.label for s in bank.sources)
        return "DME", srcs, f"DME (Anzeige) · Quellen {srcs} · Push wechselt"
    if kind == "adf":
        return ("ADF kHz", "cursor", f"ADF-Ziffern {bank.dig1_var} / {bank.dig2_var} / "
                f"{bank.dig3_var} · Punkt markiert aktive Ziffer (Push/Swap)")
    if kind == "xpdr":
        return ("SQUAWK", "QNH" if bank.baro_var else "—",
                f"XPDR {bank.code_var} (Punkt = aktive Ziffer, Push/Swap) · "
                f"QNH {bank.baro_var or '—'} auf außen")
    return bank.label, "", ""


def _radio_focus(bank) -> dict[str, list[str] | None]:
    """Per bank type: which model fields each row element maps (None = whole bank).

    So each element's ref carries just its own fields and opens a FOCUSED editor
    (top display -> the ACTIVE var, outer knob -> the whole-MHz events, …)."""
    kind = getattr(bank, "kind", "")
    if kind == "freq":
        return {"active": ["active"], "standby": ["standby"], "swap": ["swap_event"],
                "outer": ["whole_inc", "whole_dec"], "inner": ["fract_inc", "fract_dec"],
                "dot": ["fine_view"]}
    if kind == "dme":
        return {"active": ["source_var"], "standby": None, "swap": ["source_var"],
                "outer": None, "inner": None, "dot": None}
    if kind == "adf":
        return {"active": ["dig1_var", "dig2_var", "dig3_var"],
                "standby": ["min_khz", "max_khz"], "swap": None, "outer": None,
                "inner": None, "dot": None}
    if kind == "xpdr":
        return {"active": ["code_var", "set_event"], "standby": ["baro_var", "baro_scale"],
                "swap": None, "outer": ["baro_inc", "baro_dec"], "inner": None, "dot": None}
    return {k: None for k in ("active", "standby", "swap", "outer", "inner", "dot")}


def _focus_ref(base: str, fields: list[str] | None) -> str:
    """``base|f1,f2`` when fields are given, else ``base`` (the whole group)."""
    return f"{base}|{','.join(fields)}" if fields else base


def _radio_panel(binds, outs) -> list[PanelElement]:
    """Per selector unit: the outer + inner encoder rings and a SEPARATE swap
    button (the encoder itself has no push), then a column of mode rows — each a
    selector position (its code in the tooltip) with an Act/Stby display. Taller
    than the viewport (y > 1) so the canvas scrolls it row by row."""
    idx = next((i for i, oo in enumerate(outs) if isinstance(oo, RadioPanelOutput)), None)
    if idx is None:
        return _device_layout(binds, outs)
    o = outs[idx]
    els: list[PanelElement] = []
    margin, row_h, gap = 0.015, 0.11, 0.02
    y = margin
    for u, unit in enumerate(o.units):
        uref = f"out:{idx}:units/{u}"
        els.append(PanelElement(HEADER, f"Selektor {unit.name}",
                                margin, y, 1.0 - 2 * margin, 0.05, mapped=True))
        y += 0.058
        # the two encoder rings + the SEPARATE swap button, one control row per unit;
        # each opens its OWN focused capture (outer ring / inner ring / swap Taster).
        els.append(PanelElement(
            ENCODER, "außen", margin, y, 0.30, row_h * 0.8, name=unit.name, mapped=True,
            ref=_focus_ref(uref, ["outer_cw", "outer_ccw"]),
            action=f"Außen-Ring (grob) · Codes {unit.outer_cw}/{unit.outer_ccw}"))
        els.append(PanelElement(
            ENCODER, "innen", 0.33, y, 0.30, row_h * 0.8, name=unit.name, mapped=True,
            ref=_focus_ref(uref, ["inner_cw", "inner_ccw"]),
            action=f"Innen-Ring (fein) · Codes {unit.inner_cw}/{unit.inner_ccw}"))
        els.append(PanelElement(
            BUTTON, "SWAP-Taster", 0.66, y, 0.32, row_h * 0.8, mapped=True,
            ref=_focus_ref(uref, ["swap"]),
            action=f"SWAP-Taster (Code {unit.swap}) — normaler Taster, eigenständig mappbar"))
        y += row_h * 0.8 + gap
        for b, bank in enumerate(unit.banks):
            bref = f"out:{idx}:units/{u}/banks/{b}"
            _, _, det = _bank_display_text(bank)
            f = _radio_focus(bank)  # each display element opens ONLY its own field(s)
            # glow-from-sim: a freq bank's ACT/STBY cells read those frequency vars;
            # other bank types (dme/adf/xpdr) need per-digit formatting -> later.
            is_freq = getattr(bank, "kind", "") == "freq"
            act_var = getattr(bank, "active", None) if is_freq else None
            stby_var = getattr(bank, "standby", None) if is_freq else None
            # LEFT column: the selector position (mode); its code is in the tooltip.
            els.append(PanelElement(
                SELECTOR, bank.label, margin, y, 0.27, row_h, mapped=True, ref=bref,
                action=f"Selektor-Code {bank.code} · Mode {bank.label} · {det}"))
            # symbolic display: Act over Stby (labels only — the mode is the left cell);
            # freq cells read NNN.NN (dec:2), the resting/coarse view of format_frequency.
            fq_fmt = "dec:2" if is_freq else ""
            els.append(PanelElement(SEGMENT, "Act", 0.30, y, 0.30, row_h * 0.48,
                                    ref=_focus_ref(bref, f["active"]), mapped=True,
                                    action=det, var=act_var, fmt=fq_fmt))
            els.append(PanelElement(SEGMENT, "Stby", 0.30, y + row_h * 0.52, 0.30,
                                    row_h * 0.48, ref=_focus_ref(bref, f["standby"]),
                                    mapped=True, action=det, var=stby_var, fmt=fq_fmt))
            els.append(PanelElement(
                DOT, ".", 0.63, y + row_h * 0.25, 0.05, row_h * 0.5,
                ref=_focus_ref(bref, f["dot"]), mapped=True,
                action="Dezimalpunkt / Cursor (springt bei ADF/XPDR über Push)"))
            y += row_h + gap
    return els


# Device id -> hand-layout builder. Everything else uses the generic layout.
_HAND_LAYOUTS = {"switch_panel": _switch_panel, "radio_panel": _radio_panel}


def has_hand_layout(device_id: str) -> bool:
    """Whether ``device_id`` has a hand-drawn (vs auto-grid) reconstruction."""
    return device_id in _HAND_LAYOUTS


# Output blocks whose device is driven by a dedicated panel controller (as opposed
# to the generic ``generic_panel``): switch/multi/radio. These panels are static —
# encoders/swap/selectors come from the template, not from generic bindings.
_PANEL_CONTROLLER_TYPES = frozenset({"gear_leds", "multi_panel", "radio_panel"})


def is_static_panel(profile: Profile | None, device_id: str) -> bool:
    """Whether a device is a Saitek panel laid out statically by its own controller.

    True for the hand-laid panels (switch/radio) and any device carrying a
    gear_leds/multi_panel/radio_panel output. The Mapper uses this to hide the
    generic *add-encoder* step there: those panels drive their encoders from the
    template, so re-mapping them as plain bindings would only conflict.
    """
    if has_hand_layout(device_id):  # switch + radio panels
        return True
    outs = profile.outputs.get(device_id, []) if profile is not None else []
    return any(getattr(o, "type", "") in _PANEL_CONTROLLER_TYPES for o in outs)


def panel_layout(profile: Profile, device_id: str) -> list[PanelElement]:
    """Positioned panel elements for one device in ``profile``.

    Uses the hand-drawn layout for a known Saitek panel, otherwise the generic
    axes-and-tiles layout. Returns ``[]`` for an unknown/empty device.
    """
    binds = profile.bindings.get(device_id, [])
    outs = profile.outputs.get(device_id, [])
    builder = _HAND_LAYOUTS.get(device_id)
    if builder is not None:
        return builder(binds, outs)
    return _device_layout(binds, outs)


# --------------------------------------------------------------------------- #
# Edit mode ("Bearbeitungsmodus"): drag elements onto a grid, persist per device
# --------------------------------------------------------------------------- #
def element_key(el: PanelElement) -> str:
    """Stable id for storing a per-element layout override.

    Prefers the physical ``(kind, code)`` (survives binding reorder/removal), then
    the detail-tree ``ref`` (outputs), then kind+label. Pure.
    """
    if el.live_key is not None:
        return f"{el.live_key[0]}:{el.live_key[1]}"
    if el.ref:
        return el.ref
    return f"{el.kind}:{el.label}"


def snap(value: float, step: float) -> float:
    """Snap a coordinate to the nearest grid line. Pure; caller clamps the range
    (y is unbounded for the tall, scrollable radio panel)."""
    if step <= 0:
        return value
    return round(value / step) * step


def apply_layout_overrides(
    elements: list[PanelElement], overrides: dict[str, tuple[float, float]]
) -> list[PanelElement]:
    """Return elements with x/y replaced from ``{element_key: (x, y)}``. Pure.

    Elements without an override keep their generated position, so a partial
    rearrangement (or a stale override after the profile changed) degrades cleanly.
    """
    out: list[PanelElement] = []
    for el in elements:
        ov = overrides.get(element_key(el))
        out.append(replace(el, x=ov[0], y=ov[1]) if ov is not None else el)
    return out
