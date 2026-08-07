#!/usr/bin/env python3
"""Dump every device's CURRENT functions from a profile as readable Markdown.

A safety-net + reference report: for each device the profile touches, list its
bindings (source -> action), its output blocks (LEDs/displays) and the atomic
InputBlock/OutputBlock projection (``gui_mapper.template_elements``). Use it to
capture "what does each device do today" before rebuilding a device from scratch,
so nothing is silently lost in the migration.

Usage:
    uv run python tools/dump-device-functions.py [--profile piper_arrow] > report.md
    uv run python tools/dump-device-functions.py --all > report.md

Pure read-only: it never writes profiles, catalog or overlay.
"""

from __future__ import annotations

import argparse
import sys

from msfs_peripherals_bridge import config, gui_mapper
from msfs_peripherals_bridge.mapping.loader import load_device_catalog, load_profile


def _fmt_input_block(b) -> str:
    if b.kind == "encoder":
        return f"- **{b.name}** · Encoder (cw {b.cw} / ccw {b.ccw})"
    if b.kind == "axis":
        rng = f" [{b.raw_min}..{b.raw_max}]" if b.raw_min is not None else ""
        return f"- **{b.name}** · Achse code {b.code}{rng}"
    if b.kind == "selector":
        return f"- **{b.name}** · Selektor {b.positions}"
    return f"- **{b.name}** · {b.kind} code {b.code}"


def _fmt_output_block(b) -> str:
    if b.kind == "display":
        extra = f", {b.display_kind}" if b.display_kind else ""
        return f"- **{b.name}** · Display ({b.cells} Zellen{extra})"
    return f"- **{b.name}** · LED"


def dump_profile(profile_name: str, catalog) -> list[str]:
    profile = load_profile(config.profiles_dir() / f"{profile_name}.yaml")
    out: list[str] = [f"# Geräte-Funktionen — Profil `{profile_name}`", ""]
    touched = set(profile.bindings) | set(profile.outputs)
    if not touched:
        out.append("_(keine gerätebezogenen Bindings/Outputs in diesem Profil)_")
        return out

    for dev in catalog.devices:
        binds = profile.bindings.get(dev.id, [])
        outs = profile.outputs.get(dev.id, [])
        if not binds and not outs:
            continue
        out.append(f"## {dev.name}  \n`id={dev.id}` · USB {dev.vendor}:{dev.product}"
                   f" · {dev.transport}")
        out.append("")

        if binds:
            out.append(f"### Bindings ({len(binds)})")
            out.append("")
            out.append("| Name | Quelle | Aktion | Transform |")
            out.append("|---|---|---|---|")
            for b in binds:
                r = gui_mapper.describe_binding(b)
                out.append(f"| {r.name} | {r.source} | {r.action} | {r.transform or '—'} |")
            out.append("")

        if outs:
            out.append(f"### Anzeigen / Ausgänge ({len(outs)})")
            out.append("")
            for o in outs:
                out.append(f"- **{gui_mapper.describe_output(o)}**")
                for line in gui_mapper.describe_output_detail(o):
                    out.append(f"  - {line}")
            out.append("")

        t_in, t_out = gui_mapper.template_elements(dev, profile)
        out.append(f"### Atomare Elemente (aus Vorlage projiziert) — "
                   f"{len(t_in)} Inputs · {len(t_out)} Anzeigen")
        out.append("")
        if t_in:
            out.append("**Inputs (Lesen):**")
            out.extend(_fmt_input_block(b) for b in t_in)
            out.append("")
        if t_out:
            out.append("**Anzeigen (Schreiben):**")
            out.extend(_fmt_output_block(b) for b in t_out)
            out.append("")
        out.append("---")
        out.append("")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile", default="piper_arrow",
                    help="profile name without .yaml (default: piper_arrow)")
    ap.add_argument("--all", action="store_true",
                    help="dump every *.yaml profile (except _schema)")
    args = ap.parse_args(argv)

    catalog = load_device_catalog(config.devices_file())  # incl. user overlay

    if args.all:
        names = sorted(p.stem for p in config.profiles_dir().glob("*.yaml"))
    else:
        names = [args.profile]

    lines: list[str] = []
    for name in names:
        path = config.profiles_dir() / f"{name}.yaml"
        if not path.exists():
            print(f"# Profil `{name}` nicht gefunden ({path})", file=sys.stderr)
            continue
        lines.extend(dump_profile(name, catalog))
        lines.append("")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
