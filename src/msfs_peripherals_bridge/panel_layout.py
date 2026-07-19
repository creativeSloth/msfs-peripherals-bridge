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
# Gear indicator lamps, driven by a gear_leds output (nose/left/right).
_SP_GEAR_LEDS: tuple[str, ...] = ("N", "L", "R")


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

    # Magneto rotary (bottom-left): one wide element covering all five detents.
    mag_hits = [(lbl, by_code.get(code)) for code, lbl in _SP_MAGNETO]
    mag_mapped = [h for _, h in mag_hits if h is not None]
    els.append(PanelElement(
        SELECTOR, "MAGNETOS", 0.05, 0.52, 0.42, 0.38,
        name=" · ".join(lbl for _code, lbl in _SP_MAGNETO),
        action=", ".join(f"{lbl}: {_action_summary(h[1])}" for lbl, h in mag_hits if h),
        ref=(f"bind:{mag_mapped[0][0]}" if mag_mapped else None),
        mapped=bool(mag_mapped),
    ))

    # Gear indicator LEDs (three lamps) — driven by a gear_leds output if present.
    gear_out = next(((k, o) for k, o in enumerate(outs)
                     if isinstance(o, GearLedOutput)), None)
    for j, lbl in enumerate(_SP_GEAR_LEDS):
        x = 0.60 + j * 0.13
        els.append(PanelElement(
            LED, lbl, x, 0.49, 0.11, 0.15,
            name=("Fahrwerks-LEDs" if gear_out else ""),
            action=("gear_leds" if gear_out else ""),
            ref=(f"out:{gear_out[0]}" if gear_out else None),
            mapped=gear_out is not None,
        ))

    # Gear lever (bottom-right): up/down momentary edges in one element.
    gear_hits = [(lbl, by_code.get(code)) for code, lbl in _SP_GEAR]
    gear_mapped = [h for _, h in gear_hits if h is not None]
    els.append(PanelElement(
        LEVER, "GEAR", 0.60, 0.68, 0.37, 0.23,
        name="Fahrwerkshebel",
        action=", ".join(f"{lbl}: {_action_summary(h[1])}" for lbl, h in gear_hits if h),
        ref=(f"bind:{gear_mapped[0][0]}" if gear_mapped else None),
        mapped=bool(gear_mapped),
    ))
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


def _device_layout(binds, outs) -> list[PanelElement]:
    """Axes as stacked live bars (top) + buttons/switches/hats as a tile grid."""
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

    # Buttons/switches/hats: a tile grid filling the space under the axes.
    rest = keys + hats
    if rest:
        gy0 = y + (gap if axes else 0.0)
        cells = _grid_cells(len(rest), margin, gy0, 1.0 - margin, 1.0 - margin)
        for (x0, y0, w, h), (i, b) in zip(cells, rest, strict=True):
            k = str(b.source.kind)
            kind = HAT if k == "hat" else (BUTTON if k == "button" else SWITCH)
            els.append(PanelElement(
                kind, b.name or f"#{i}", x0, y0, w, h,
                name=b.name, action=_action_summary(b), code=b.source.code,
                ref=f"bind:{i}", mapped=True,
                # hats report as two -1/0/+1 axes — no simple on/off overlay yet
                live_key=(None if k == "hat" else _live_key(k, b.source.code)),
            ))
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
