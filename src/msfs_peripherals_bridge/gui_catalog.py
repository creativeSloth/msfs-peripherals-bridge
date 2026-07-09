"""Variable catalog for the GUI's Statistik picker.

Provides a searchable, type-filterable list of variables the user can pick from
to build a live value list. Sources:

* a curated set of the most useful ``A:`` SimVars (with units) and ``K:`` events,
* the full JustFlight Arrow ``L:`` var list, parsed from
  ``docs/simvars-reference.md`` at load time (no duplication of the 714 names).

Kept dependency-free and pure so it can be unit-tested without a display.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Variable "kind" tags, matching docs/simvars-reference.md §1.
KIND_SIMVAR = "A:"  # simulation variable (read, some writable)
KIND_EVENT = "K:"  # key event (write / trigger)
KIND_LVAR = "L:"  # add-on local var (read/write via WASM bridge)

KINDS = (KIND_SIMVAR, KIND_EVENT, KIND_LVAR)


@dataclass(frozen=True)
class CatalogVar:
    """One selectable variable."""

    name: str
    kind: str  # one of KINDS
    unit: str  # "" when not applicable (events)
    category: str

    @property
    def label(self) -> str:
        """Display label, e.g. ``A: AUTOPILOT ALTITUDE LOCK VAR  [feet]``."""
        tail = f"  [{self.unit}]" if self.unit else ""
        return f"{self.kind} {self.name}{tail}"


# --- curated A: SimVars ----------------------------------------------------- #
# (name, unit, category) — the values you most often want to watch in the panel.
_SIMVARS: tuple[tuple[str, str, str], ...] = (
    ("PLANE ALTITUDE", "feet", "Flight"),
    ("INDICATED ALTITUDE", "feet", "Flight"),
    ("AIRSPEED INDICATED", "knots", "Flight"),
    ("AIRSPEED TRUE", "knots", "Flight"),
    ("VERTICAL SPEED", "feet/min", "Flight"),
    ("PLANE HEADING DEGREES MAGNETIC", "degrees", "Flight"),
    ("PLANE BANK DEGREES", "degrees", "Flight"),
    ("PLANE PITCH DEGREES", "degrees", "Flight"),
    ("GROUND VELOCITY", "knots", "Flight"),
    ("SIM ON GROUND", "bool", "Flight"),
    ("STALL WARNING", "bool", "Flight"),
    ("FLAPS HANDLE INDEX", "number", "Controls"),
    ("GEAR HANDLE POSITION", "bool", "Controls"),
    ("GEAR CENTER POSITION", "percent", "Controls"),
    ("GEAR LEFT POSITION", "percent", "Controls"),
    ("GEAR RIGHT POSITION", "percent", "Controls"),
    ("ELEVATOR TRIM POSITION", "radians", "Controls"),
    ("BRAKE PARKING POSITION", "bool", "Controls"),
    ("GENERAL ENG RPM:1", "rpm", "Engine"),
    ("GENERAL ENG THROTTLE LEVER POSITION:1", "percent", "Engine"),
    ("GENERAL ENG PROPELLER LEVER POSITION:1", "percent", "Engine"),
    ("GENERAL ENG MIXTURE LEVER POSITION:1", "percent", "Engine"),
    ("ENG MANIFOLD PRESSURE:1", "inHg", "Engine"),
    ("FUEL TOTAL QUANTITY", "gallons", "Engine"),
    ("FUEL TANK LEFT MAIN LEVEL", "percent", "Engine"),
    ("FUEL TANK RIGHT MAIN LEVEL", "percent", "Engine"),
    ("ELECTRICAL MASTER BATTERY", "bool", "Electrical"),
    ("ELECTRICAL BATTERY VOLTAGE", "volts", "Electrical"),
    ("AVIONICS MASTER SWITCH", "bool", "Electrical"),
    ("AUTOPILOT MASTER", "bool", "Autopilot"),
    ("AUTOPILOT ALTITUDE LOCK VAR", "feet", "Autopilot"),
    ("AUTOPILOT VERTICAL HOLD VAR", "feet/min", "Autopilot"),
    ("AUTOPILOT HEADING LOCK DIR", "degrees", "Autopilot"),
    ("AUTOPILOT AIRSPEED HOLD VAR", "knots", "Autopilot"),
    ("COM ACTIVE FREQUENCY:1", "MHz", "Radio"),
    ("COM STANDBY FREQUENCY:1", "MHz", "Radio"),
    ("NAV ACTIVE FREQUENCY:1", "MHz", "Radio"),
    ("NAV STANDBY FREQUENCY:1", "MHz", "Radio"),
    ("NAV OBS:1", "degrees", "Radio"),
    ("NAV DME:1", "nmiles", "Radio"),
    ("TRANSPONDER CODE:1", "number", "Radio"),
    ("KOHLSMAN SETTING HG", "inHg", "Instruments"),
    ("LIGHT LANDING", "bool", "Lights"),
    ("LIGHT NAV", "bool", "Lights"),
    ("LIGHT BEACON", "bool", "Lights"),
)

# --- curated K: events ------------------------------------------------------ #
_EVENTS: tuple[tuple[str, str], ...] = (
    ("AP_MASTER", "Autopilot"),
    ("AP_ALT_HOLD", "Autopilot"),
    ("AP_VS_HOLD", "Autopilot"),
    ("HEADING_BUG_INC", "Autopilot"),
    ("HEADING_BUG_DEC", "Autopilot"),
    ("GEAR_TOGGLE", "Controls"),
    ("FLAPS_INCR", "Controls"),
    ("FLAPS_DECR", "Controls"),
    ("PARKING_BRAKES", "Controls"),
    ("TOGGLE_MASTER_BATTERY", "Electrical"),
    ("TOGGLE_AVIONICS_MASTER", "Electrical"),
    ("LANDING_LIGHTS_TOGGLE", "Lights"),
    ("TOGGLE_NAV_LIGHTS", "Lights"),
    ("COM_STBY_RADIO_SWAP", "Radio"),
    ("NAV1_RADIO_SWAP", "Radio"),
    ("KOHLSMAN_INC", "Instruments"),
    ("KOHLSMAN_DEC", "Instruments"),
)


def _parse_lvars(reference_md: Path) -> list[CatalogVar]:
    """Pull the JF Arrow L:vars out of the ```text block in simvars-reference.md.

    The doc holds the enumerated 714 names under a fenced ``text`` block; we take
    the names between that fence and the next ``` line. Best-effort: on any error
    (missing file, format drift) we simply return nothing.
    """
    try:
        lines = reference_md.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out: list[CatalogVar] = []
    in_block = False
    for line in lines:
        name = line.strip()
        if not in_block:
            if name == "```text":  # the one fenced text block = the 714-name list
                in_block = True
            continue
        if name == "```":
            break
        # LVar names are bare identifiers (letters/digits/underscore), one per line.
        if name and all(c.isalnum() or c == "_" for c in name):
            out.append(
                CatalogVar(name=name, kind=KIND_LVAR, unit="number", category="JF Arrow LVar")
            )
    return out


def load_catalog(reference_md: Path | None = None) -> list[CatalogVar]:
    """Full catalog: curated A:/K: plus parsed JF L:vars (deduped, stable order)."""
    cat: list[CatalogVar] = [
        CatalogVar(name=n, kind=KIND_SIMVAR, unit=u, category=c) for n, u, c in _SIMVARS
    ]
    cat += [CatalogVar(name=n, kind=KIND_EVENT, unit="", category=c) for n, c in _EVENTS]
    if reference_md is not None:
        seen = {(v.kind, v.name) for v in cat}
        for v in _parse_lvars(reference_md):
            if (v.kind, v.name) not in seen:
                cat.append(v)
                seen.add((v.kind, v.name))
    return cat


def filter_catalog(
    catalog: list[CatalogVar], *, kind: str | None = None, query: str = ""
) -> list[CatalogVar]:
    """Filter by ``kind`` (None = all) and a case-insensitive substring ``query``."""
    q = query.strip().lower()
    return [
        v
        for v in catalog
        if (kind is None or v.kind == kind) and (not q or q in v.name.lower())
    ]
