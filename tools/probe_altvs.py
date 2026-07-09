#!/usr/bin/env python3
"""Probe the JustFlight Arrow ALT/VS *mode* input on one bridge connection.

Background (STATUS bug #1): the Multi-Panel ALT/VS buttons don't switch the JF
hold modes. `L:JF_PA28_AP_alt` / `_vs` turned out to be gauge *outputs* (the gauge
overwrites them every frame), so writing them is a no-op. The real toggle input is
unknown — likely a bare `AUTOPILOT_*` command LVar or a JF `H:` gauge event. This
tool finds it.

It watches a default set of ALT/VS candidate vars AND — on the *same* connection,
so it doesn't trip the bridge's single-client limit — can fire a candidate write
or RPN and let you watch what moves.

Two phases per run:
  1. baseline: subscribe + print changes for `--after` seconds (default 1.5),
  2. act: send every `--set` / `--rpn` action, then keep printing changes until Ctrl-C.

Usage:
    # OBSERVE only — no actions. Run this, then click the cockpit ALT / VS spot.
    # Whichever var flips is the real state; if a *writable* one flips, we can drive it.
    python tools/probe_altvs.py

    # Try writing the bare mirror LVar and see if JF_PA28_AP_alt follows:
    python tools/probe_altvs.py --set L:AUTOPILOT_alt=1

    # Try firing a candidate JF H: gauge event (H: must go through RPN):
    python tools/probe_altvs.py --rpn "(>H:AP_ALT)"

    # Extra / replacement watch vars:
    python tools/probe_altvs.py --watch L:JF_PA28_AP_master --watch L:AUTOPILOT_alt

The bridge is single-client, so STOP THE MAPPER FIRST
(pkill -f 'msfs_peripherals_bridge[ ]run'). Ctrl-C to stop.
"""

from __future__ import annotations

import argparse
import json
import select
import socket
import sys
import time

HOST, PORT = "127.0.0.1", 7842

# Default candidates for the ALT/VS mode toggle, most-likely first:
#   *_alt / *_vs   = gauge outputs (current LED source) — should flip when engaged
#   AUTOPILOT_alt/_vs        = bare "generic mirror" — write-candidate to test
#   AUTOPILOT_alt_up/_dn ... = ALT-target / VS-rate ADJUST (the encoder, not the toggle)
#   *_master / mode          = context (is the AP even armed / which lateral mode)
DEFAULT_WATCH = [
    "L:JF_PA28_AP_alt",
    "L:JF_PA28_AP_vs",
    "L:AUTOPILOT_alt",
    "L:AUTOPILOT_vs",
    "L:AUTOPILOT_alt_up",
    "L:AUTOPILOT_alt_dn",
    "L:AUTOPILOT_vs_up",
    "L:AUTOPILOT_vs_dn",
    "L:AUTOPILOT_mode",
    "L:JF_PA28_AP_master",
]


def normalise(name: str) -> str:
    """Prefix a bare name. LVar names have no spaces → L:; SimVar names contain
    spaces (e.g. 'KOHLSMAN SETTING HG') and the bridge wants them WITHOUT an A:
    prefix (a leading A: yields UNRECOGNIZED_ID), so leave those bare."""
    if name[:2].upper() in ("L:", "H:", "B:", "A:"):
        return name
    return name if " " in name else "L:" + name


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Probe the Arrow ALT/VS mode input.")
    p.add_argument("--watch", action="append", default=[], metavar="NAME",
                   help="watch this var too (repeatable; replaces defaults if given)")
    p.add_argument("--set", action="append", default=[], metavar="NAME=VALUE",
                   dest="sets", help="write a var after the baseline (repeatable)")
    p.add_argument("--rpn", action="append", default=[], metavar="EXPR",
                   help="run a MobiFlight RPN after the baseline, e.g. '(>H:AP_ALT)' (repeatable)")
    p.add_argument("--unit", default="number", help="unit for --set writes (default: number)")
    p.add_argument("--after", type=float, default=1.5,
                   help="seconds of baseline before firing actions (default: 1.5)")
    p.add_argument("--gap", type=float, default=0.0,
                   help="seconds to watch after each action before the next (default: 0)")
    return p.parse_args(argv)


def _drain(sock: socket.socket, seen: dict[str, object], start: float,
           buf: bytes, until: float | None) -> bytes:
    """Read state frames and print changes. Return once `until` passes (None = forever)."""
    while until is None or time.monotonic() < until:
        timeout = None if until is None else max(0.0, until - time.monotonic())
        ready, _, _ = select.select([sock], [], [], timeout)
        if not ready:
            return buf  # baseline window elapsed
        chunk = sock.recv(65536)
        if not chunk:
            print("bridge closed the connection", file=sys.stderr)
            raise SystemExit(1)
        buf += chunk
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            if not line.strip():
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("op") != "state":
                continue
            name, value = msg.get("name"), msg.get("value")
            if name not in seen or seen[name] != value:
                print(f"[{time.monotonic() - start:6.1f}s] {name} = {value}")
                seen[name] = value
    return buf


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    # Line-buffer stdout so change-lines flush immediately even when piped to a
    # file (block-buffered otherwise → events sit unseen in the buffer).
    sys.stdout.reconfigure(line_buffering=True)
    names = [normalise(n) for n in (args.watch or DEFAULT_WATCH)]

    try:
        sock = socket.create_connection((HOST, PORT), timeout=10)
    except OSError as exc:
        print(f"Cannot reach the bridge on {HOST}:{PORT} ({exc}). MSFS up? mapper stopped?",
              file=sys.stderr)
        return 1

    with sock:
        for name in names:
            sock.sendall((json.dumps({"op": "subscribe", "name": name}) + "\n").encode())
        acting = bool(args.sets or args.rpn)
        print(f"Watching {len(names)} var(s).", file=sys.stderr)
        if not acting:
            print("OBSERVE mode: click the cockpit ALT / VS spot — the var that flips is it.",
                  file=sys.stderr)
        print("Ctrl-C to stop.\n", file=sys.stderr)

        seen: dict[str, object] = {}
        start = time.monotonic()
        buf = b""
        try:
            # Phase 1: baseline (also lets the initial values stream in).
            buf = _drain(sock, seen, start, buf, until=start + args.after)

            # Phase 2: fire the candidate actions.
            for spec in args.sets:
                if "=" not in spec:
                    print(f"--set needs NAME=VALUE, got {spec!r}", file=sys.stderr)
                    return 2
                nm, _, val = spec.partition("=")
                frame = {"op": "simvar", "name": normalise(nm), "unit": args.unit,
                         "value": float(val)}
                sock.sendall((json.dumps(frame) + "\n").encode())
                print(f"--> SET {frame['name']} = {frame['value']}", file=sys.stderr)
                if args.gap > 0:
                    buf = _drain(sock, seen, start, buf, until=time.monotonic() + args.gap)
            for expr in args.rpn:
                sock.sendall((json.dumps({"op": "rpn", "code": expr}) + "\n").encode())
                print(f"--> RPN {expr}", file=sys.stderr)
                if args.gap > 0:
                    buf = _drain(sock, seen, start, buf, until=time.monotonic() + args.gap)
            if acting:
                print("(watching for the effect — Ctrl-C to stop)\n", file=sys.stderr)

            # Phase 3: observe the effect forever.
            _drain(sock, seen, start, buf, until=None)
        except KeyboardInterrupt:
            print("\nStopped.", file=sys.stderr)
        return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
