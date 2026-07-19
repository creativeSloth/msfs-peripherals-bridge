"""Round-gauge model for the GUI's Gauges tab — pure math, no tkinter.

Ported from the user's Air Manager Lua gauges (backed up under
``reference/air-manager/``, analysis in ``docs/gauges-design.md``). The
valuable part of those prototypes is the *parametric scale*; this module
re-implements it cleanly:

    angle(v) = omega + sweep * ((v - v_min) / (v_max - v_min)) ** h

which is algebraically the Lua form ``(ZWEI_PI/Δ · x)^h + OMEGA`` with
``ZWEI_PI = sweep^(1/h)`` — i.e. ``sweep`` here is always the full swept
angle, whatever the exponent. ``h = 1`` is linear; the EGT gauge reserved
a compression exponent, kept as a first-class knob.

Angle convention (from the luas): degrees, 0° = north (12 o'clock),
increasing clockwise. :func:`polar` converts to screen coordinates
(y grows downwards).

A gauge is one face with one or more needles; every needle has its OWN
scale and its own variable — the MAP + Fuel-Flow combo instrument is the
canonical two-needle case (outer MAP scale, smaller inner FF scale). The
variable mapping is deliberately free: any readable A:/L: var can drive
any needle (the core user wish).
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field


@dataclass
class Arc:
    """A coloured range band on a scale (green arc etc.)."""

    v_from: float
    v_to: float
    color: str = "#2e7d32"


@dataclass
class NeedleSpec:
    """One needle: its scale geometry + the variable driving it."""

    label: str = ""
    kind: str = "A:"  # variable kind (A:/L:) — decides the wire name
    var: str = ""  # variable name; empty = unmapped (needle parks at v_min)
    unit: str = ""  # informational (bridge streams canonical units)
    factor: float = 1.0  # raw value * factor = displayed value
    v_min: float = 0.0
    v_max: float = 100.0
    sweep: float = 270.0  # full swept angle in degrees
    omega: float = -135.0  # scale rotation (0° = north, clockwise)
    h: float = 1.0  # power-law exponent (1 = linear)
    major: float = 10.0  # major tick step in display units (0 = none)
    minor: float = 0.0  # minor tick step (0 = none)
    arcs: list[Arc] = field(default_factory=list)
    radius: float = 0.92  # scale radius as a fraction of the face's base radius
    cx: float = 0.5  # needle centre X as a fraction of the face width
    cy: float = 0.5  # needle centre Y as a fraction of the face height
    fmt: str = "{:.0f}"  # digital readout format
    color: str = "#e53935"  # needle colour

    @property
    def span(self) -> float:
        return self.v_max - self.v_min


@dataclass
class GaugeSpec:
    """One instrument: a face with 1..n needles.

    ``aspect`` is the face's width/height ratio: 1.0 = round; the fuel cluster is
    a wide 6:1 face carrying three sub-scales side by side (each needle placed by
    its own ``cx``/``cy``). Keeping the aspect lets non-round instruments keep
    their shape on the panel and in the reconstruction.
    """

    name: str
    needles: list[NeedleSpec] = field(default_factory=list)
    aspect: float = 1.0  # face width / height (1 = round, 6 = wide fuel cluster)


# --------------------------------------------------------------------------- #
# geometry
# --------------------------------------------------------------------------- #
def polar(cx: float, cy: float, r: float, deg: float) -> tuple[float, float]:
    """Screen point at radius/angle from a centre (0° = north, clockwise)."""
    rad = math.radians(deg)
    return cx + r * math.sin(rad), cy - r * math.cos(rad)


def display_value(n: NeedleSpec, raw: float) -> float:
    """Raw var value -> displayed value (factor applied, clamped to the scale)."""
    v = raw * n.factor
    return min(n.v_max, max(n.v_min, v))


def angle_for(n: NeedleSpec, raw: float) -> float:
    """Needle angle in degrees for a raw variable value (clamped to the scale)."""
    span = n.span or 1.0
    frac = (display_value(n, raw) - n.v_min) / span
    return n.omega + n.sweep * (frac**n.h)


def _steps(n: NeedleSpec, step: float) -> list[float]:
    if step <= 0:
        return []
    out, v = [], n.v_min
    # walk in integer multiples to dodge float drift on long scales
    k = 0
    while (v := n.v_min + k * step) <= n.v_max + 1e-9:
        out.append(round(v, 10))
        k += 1
    return out


def ticks(n: NeedleSpec) -> list[tuple[float, float, bool]]:
    """(value, angle, is_major) for every tick on the scale, majors first."""
    majors = _steps(n, n.major)
    out = [(v, angle_for(n, v / (n.factor or 1.0)), True) for v in majors]
    for v in _steps(n, n.minor):
        if v not in majors:
            out.append((v, angle_for(n, v / (n.factor or 1.0)), False))
    return out


def arc_angles(n: NeedleSpec, arc: Arc) -> tuple[float, float]:
    """(start, end) needle angles of a range band, clamped to the scale."""
    a1 = angle_for(n, arc.v_from / (n.factor or 1.0))
    a2 = angle_for(n, arc.v_to / (n.factor or 1.0))
    return (a1, a2) if a1 <= a2 else (a2, a1)


def wire_name(n: NeedleSpec) -> str | None:
    """Subscription name for the monitor: A: bare, L:/V: prefixed, else None."""
    if not n.var:
        return None
    if n.kind in ("L:", "V:"):
        return n.var if n.var.startswith(n.kind) else n.kind + n.var
    if n.kind == "A:":
        return n.var
    return None


# --------------------------------------------------------------------------- #
# persistence (gui-settings.json carries plain dicts)
# --------------------------------------------------------------------------- #
def to_dict(g: GaugeSpec) -> dict:
    return asdict(g)


def from_dict(d: dict) -> GaugeSpec:
    needles = []
    known = set(NeedleSpec.__dataclass_fields__)
    for nd in d.get("needles", []):
        nd = {k: v for k, v in nd.items() if k in known}  # tolerate schema drift
        nd["arcs"] = [Arc(**a) for a in nd.get("arcs", [])]
        needles.append(NeedleSpec(**nd))
    return GaugeSpec(name=str(d.get("name", "Gauge")), needles=needles,
                     aspect=float(d.get("aspect", 1.0)) or 1.0)


# --------------------------------------------------------------------------- #
# presets — scale parameters measured from the user's Air Manager luas
# (docs/gauges-design.md). Var mapping stays editable per needle.
# --------------------------------------------------------------------------- #
def presets() -> dict[str, GaugeSpec]:
    return {
        # MAP outer scale is linear; the Fuel-Flow inner scale is power-law
        # compressed (h = 1.8 in the lua) — the crux the user flagged. sweep 165 /
        # omega 100 with h 1.8 reproduces the lua's (ZWEI_PI/Δ·v)^1.8 + 100 exactly.
        "MAP + Fuel Flow": GaugeSpec("MAP + Fuel Flow", [
            NeedleSpec(label="MAP", var="ENG MANIFOLD PRESSURE:1", unit="inHg",
                       v_min=10, v_max=50, sweep=180, omega=-90, h=1.0, major=5, minor=1,
                       arcs=[Arc(10, 41)], radius=0.95, fmt="{:.1f}"),
            NeedleSpec(label="FF", var="ENG FUEL FLOW GPH:1", unit="GPH",
                       v_min=0, v_max=25, sweep=165, omega=100, h=1.8, major=5, minor=1,
                       arcs=[Arc(0, 24), Arc(21.5, 24, "#66bb6a")],
                       radius=0.62, color="#fbc02d", fmt="{:.1f}"),
        ]),
        "RPM": GaugeSpec("RPM", [
            NeedleSpec(label="RPM", var="GENERAL ENG RPM:1", unit="rpm",
                       v_min=0, v_max=3500, sweep=290, omega=215, major=500, minor=100,
                       arcs=[Arc(500, 2650)], fmt="{:.0f}"),
        ]),
        "Airspeed": GaugeSpec("Airspeed", [
            NeedleSpec(label="IAS", var="AIRSPEED INDICATED", unit="kt",
                       v_min=20, v_max=190, sweep=306, omega=0, major=20, minor=5,
                       arcs=[Arc(65, 100), Arc(100, 190, "#f9a825"),
                             Arc(70, 77, "#1565c0")], fmt="{:.0f}"),
        ]),
        "EGT": GaugeSpec("EGT", [
            NeedleSpec(label="EGT", var="GENERAL ENG EXHAUST GAS TEMPERATURE:1",
                       unit="°F", v_min=1200, v_max=1700, sweep=100, omega=-50,
                       major=100, minor=25, arcs=[Arc(1200, 1650)], fmt="{:.0f}"),
        ]),
        "Fuel links": GaugeSpec("Fuel links", [
            NeedleSpec(label="FUEL L", var="FUEL LEFT QUANTITY", unit="gal",
                       v_min=0, v_max=38.5, sweep=100, omega=-50, major=10, minor=2,
                       fmt="{:.1f}"),
        ]),
        "Fuel rechts": GaugeSpec("Fuel rechts", [
            NeedleSpec(label="FUEL R", var="FUEL RIGHT QUANTITY", unit="gal",
                       v_min=0, v_max=38.5, sweep=100, omega=-50, major=10, minor=2,
                       fmt="{:.1f}"),
        ]),
        # Wide 6:1 cluster: L tank / fuel pressure / R tank, three sub-scales at
        # their own centres (cx = 1/6, 1/2, 5/6) — the non-round shape kept 1:1.
        "Fuel L/R + Druck (Cluster)": GaugeSpec("Fuel L/R + Druck", [
            NeedleSpec(label="FUEL L", var="FUEL LEFT QUANTITY", unit="gal",
                       v_min=0, v_max=38.5, sweep=100, omega=-50, major=10, minor=2,
                       cx=1 / 6, cy=0.5, fmt="{:.1f}"),
            NeedleSpec(label="PRESS", var="GENERAL ENG FUEL PRESSURE:1", unit="PSI",
                       v_min=0, v_max=50, sweep=100, omega=-50, major=25, minor=5,
                       cx=0.5, cy=0.5, color="#fbc02d", fmt="{:.0f}"),
            NeedleSpec(label="FUEL R", var="FUEL RIGHT QUANTITY", unit="gal",
                       v_min=0, v_max=38.5, sweep=100, omega=-50, major=10, minor=2,
                       cx=5 / 6, cy=0.5, fmt="{:.1f}"),
        ], aspect=6.0),
        "Eigenes…": GaugeSpec("Neues Gauge", [
            NeedleSpec(label="WERT", var="", v_min=0, v_max=100,
                       sweep=270, omega=-135, major=10, fmt="{:.0f}"),
        ]),
    }
