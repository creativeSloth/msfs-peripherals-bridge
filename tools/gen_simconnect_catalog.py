#!/usr/bin/env python3
"""Generate the bundled SimVar/Event catalog for the GUI picker.

Source of the names, units and settable flags: **Python-SimConnect** (MIT),
https://github.com/odwdinc/Python-SimConnect — its ``RequestList.py`` (SimVars)
and ``EventList.py`` (Key events). We parse those two files with regexes (no
import, they pull in the SimConnect DLL) and emit a flat JSON that
``gui_catalog.py`` loads. This keeps the derivation reproducible and records
provenance for a future community release.

Usage:
    python tools/gen_simconnect_catalog.py REQUESTLIST.py EVENTLIST.py [-o OUT.json]

Fetch the inputs first, e.g.:
    base=https://raw.githubusercontent.com/odwdinc/Python-SimConnect/master/SimConnect
    curl -fsSL $base/RequestList.py -o RequestList.py
    curl -fsSL $base/EventList.py  -o EventList.py
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ATTRIBUTION = (
    "SimVar/Event names, units and settable flags derived from Python-SimConnect "
    "(MIT License), https://github.com/odwdinc/Python-SimConnect"
)

# A data class header, e.g.  `class __AircraftEngineData(RequestHelper):`
_SIMVAR_CLASS = re.compile(r"class\s+_+(\w+?)(?:Data)?\((?:RequestHelper|.*Helper)\):")
_EVENT_CLASS = re.compile(r"class\s+_+(\w+)\(EventHelper\):")
# A SimVar row: "KEY": ["desc", b'NAME', b'UNIT', 'Y'|'N'],
_SIMVAR_ROW = re.compile(r"b'([^']*)',\s*b'([^']*)',\s*'([YN])'")
# An event row: (b'NAME', "desc", ...),
_EVENT_ROW = re.compile(r"\(\s*b'([^']*)'")


def _humanise(class_name: str) -> str:
    """`AircraftEngine` -> `Aircraft Engine`, `Fuel_Selection_Keys` -> `Fuel Selection Keys`."""
    spaced = class_name.replace("_", " ")
    spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", spaced)
    spaced = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", spaced)
    # Join words glued to a trailing lowercase "and" (Positionand -> Position and).
    spaced = re.sub(r"(?<=[a-z])and(?=\s)", " and", spaced)
    return re.sub(r"\s+", " ", spaced).strip()


def parse_simvars(text: str) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    category = "SimVar"
    for line in text.splitlines():
        if (m := _SIMVAR_CLASS.search(line)) and "Helper" not in m.group(1):
            category = _humanise(m.group(1))
            continue
        if m := _SIMVAR_ROW.search(line):
            name, unit, settable = m.group(1), m.group(2), m.group(3)
            # ":index" is a placeholder for an instance number; default to :1 so
            # the name resolves out of the box (engine 1, nav 1, ...).
            name = name.replace(":index", ":1")
            if not name or name in seen:
                continue
            seen.add(name)
            out.append(
                {
                    "name": name,
                    "unit": unit,
                    "settable": settable == "Y",
                    "category": category,
                }
            )
    return out


def parse_events(text: str) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    category = "Event"
    in_list = False
    for line in text.splitlines():
        if m := _EVENT_CLASS.search(line):
            category = _humanise(m.group(1))
            in_list = True
            continue
        if not in_list:
            continue
        if m := _EVENT_ROW.search(line):
            name = m.group(1)
            if not name or name in seen:
                continue
            seen.add(name)
            out.append({"name": name, "category": category})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("request_list", type=Path, help="Python-SimConnect RequestList.py")
    ap.add_argument("event_list", type=Path, help="Python-SimConnect EventList.py")
    default_out = Path(__file__).resolve().parents[1] / (
        "src/msfs_peripherals_bridge/data/simconnect_catalog.json"
    )
    ap.add_argument("-o", "--out", type=Path, default=default_out)
    args = ap.parse_args()

    simvars = parse_simvars(args.request_list.read_text(encoding="utf-8"))
    events = parse_events(args.event_list.read_text(encoding="utf-8"))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(
            {"attribution": ATTRIBUTION, "simvars": simvars, "events": events},
            indent=1,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.out}")
    print(f"  {len(simvars)} SimVars, {len(events)} events")
    cats = sorted({v["category"] for v in simvars})
    print(f"  SimVar categories ({len(cats)}): {', '.join(cats)}")


if __name__ == "__main__":
    main()
