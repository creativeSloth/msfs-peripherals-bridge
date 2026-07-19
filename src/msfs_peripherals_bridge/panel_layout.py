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

from dataclasses import dataclass
from math import ceil, sqrt

from .gui_mapper import describe_action
from .models import GearLedOutput, Profile

# --- element kinds (what the canvas draws) --------------------------------- #
SWITCH = "switch"  # two-position toggle / momentary — highlights when live-on
BUTTON = "button"  # push-button (yoke/multi/radio) — same live behaviour
SELECTOR = "selector"  # rotary detent group (e.g. magnetos) — one wide element
LED = "led"  # indicator lamp driven by an output (glow-from-sim = later)
LEVER = "lever"  # gear lever and the like — two momentary edges in one element
AXIS = "axis"  # analog control — drawn as a live-filling bar with a value readout
HAT = "hat"  # POV hat — one element grouping its direction actions


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
            out.append(PanelElement(
                BUTTON, label, x, yy, w, bh, name=b.name,
                action=_action_summary(b), code=code, ref=f"bind:{idx}",
                mapped=True, source_kind=src_kind, live_key=_live_key(src_kind, code)))
    return out


def _switch_panel(binds, outs) -> list[PanelElement]:
    """Hand-drawn Saitek Switch Panel: toggle row + magneto rotary + gear."""
    by_code = _index_bindings(binds)
    els: list[PanelElement] = []

    # 13 toggle switches evenly spread across the top row.
    n = len(_SP_TOGGLES)
    margin, gap = 0.02, 0.006
    cw = (1.0 - 2 * margin - (n - 1) * gap) / n
    for j, (code, hw) in enumerate(_SP_TOGGLES):
        x = margin + j * (cw + gap)
        els.append(_switch_element(hw, x, 0.07, cw, 0.30, code, by_code.get(code)))

    # Magneto rotary (bottom-left): each of the 5 detents its own clickable bar.
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


def _device_layout(binds, outs) -> list[PanelElement]:
    """Axes as stacked live bars (top) + buttons/switches/hats/rockers as tiles."""
    axes = [(i, b) for i, b in enumerate(binds) if str(b.source.kind) == "axis"]
    hats = [(i, b) for i, b in enumerate(binds) if str(b.source.kind) == "hat"]
    keys = [(i, b) for i, b in enumerate(binds)
            if str(b.source.kind) in ("button", "switch")]
    if not (axes or hats or keys):
        return []
    els: list[PanelElement] = []
    margin, gap = 0.03, 0.018

    # Axes: full-width horizontal bars, stacked from the top. Cap the zone so the
    # tiles keep room; the bar height shrinks to fit when there are many axes.
    y = margin
    if axes:
        zone_bottom = 0.62 if (hats or keys) else (1.0 - margin)
        avail = zone_bottom - margin
        ah = max(0.05, min(0.11, (avail - gap * (len(axes) - 1)) / len(axes)))
        for j, (i, b) in enumerate(axes):
            yy = margin + j * (ah + gap)
            els.append(_axis_element(i, b, margin, yy, 1.0 - 2 * margin, ah))
        y = margin + len(axes) * (ah + gap)

    # Buttons/switches (up/down pairs merged to rockers) + hats as a tile grid.
    rockers, singles = _pair_rockers(keys)
    items = ([("rocker", u, d) for u, d in rockers]
             + [("key", i, b) for i, b in singles]
             + [("hat", i, b) for i, b in hats])
    if items:
        gy0 = y + (gap if axes else 0.0)
        cells = _grid_cells(len(items), margin, gy0, 1.0 - margin, 1.0 - margin)
        for (x0, y0, w, h), it in zip(cells, items, strict=True):
            if it[0] == "rocker":
                # a momentary up/down pair -> two stacked clickable bars in ONE
                # cell (same footprint as a single tile), each its own mapping.
                (ui, ub), (di, db) = it[1], it[2]
                base = ub.name.rsplit(" ", 1)[0] or ub.name
                positions = [(ub.source.code, f"▲ {base}"), (db.source.code, f"▼ {base}")]
                local = {ub.source.code: (ui, ub), db.source.code: (di, db)}
                els += _stacked_bars(x0, y0, w, h, positions, local,
                                     src_kind=str(ub.source.kind))
                continue
            _, i, b = it
            k = str(b.source.kind)
            kind = HAT if it[0] == "hat" else (BUTTON if k == "button" else SWITCH)
            els.append(PanelElement(
                kind, b.name or f"#{i}", x0, y0, w, h,
                name=b.name, action=_action_summary(b), code=b.source.code,
                ref=f"bind:{i}", mapped=True,
                # hats report as two -1/0/+1 axes — no simple on/off overlay yet
                live_key=(None if k == "hat" else _live_key(k, b.source.code))))
    return els


# Device id -> hand-layout builder. Everything else uses the generic layout.
_HAND_LAYOUTS = {"switch_panel": _switch_panel}


def has_hand_layout(device_id: str) -> bool:
    """Whether ``device_id`` has a hand-drawn (vs auto-grid) reconstruction."""
    return device_id in _HAND_LAYOUTS


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
