#!/usr/bin/env python3
"""Watch several LVars live and print every value change — for identifying which
var a cockpit control drives.

Subscribes to each given name over the bridge's subscribe→state stream and prints
a line whenever one changes. Move the cockpit knob you're chasing; the name that
moves with it is your var.

Usage:
    python tools/read_lvars.py L:Radio_light_scaler L:GENERIC_LIGHTSWITCH_RADIO_1
    python tools/read_lvars.py L:LIGHTING_CABIN_0 L:GENERIC_CIRCUIT_LIGHTS_CABIN
    python tools/read_lvars.py --once L:CENTRE_LOWER_panel_light   # snapshot then exit

L: is optional — a bare name is treated as an L:var. The bridge is single-client,
so STOP THE MAPPER FIRST (pkill -f 'msfs_peripherals_bridge[ ]run'). Ctrl-C to stop.
"""

from __future__ import annotations

import json
import socket
import sys
import time

HOST, PORT = "127.0.0.1", 7842


def normalise(name: str) -> str:
    """Bare names default to the L: namespace (case-insensitive prefix check)."""
    return name if name[:2].upper() in ("L:", "H:", "B:", "A:") else "L:" + name


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--once"]
    once = "--once" in sys.argv
    if not args:
        print(__doc__, file=sys.stderr)
        return 2
    names = [normalise(a) for a in args]

    try:
        sock = socket.create_connection((HOST, PORT), timeout=10)
    except OSError as exc:
        print(
            f"Cannot reach the bridge on {HOST}:{PORT} ({exc}). MSFS up? mapper stopped?",
            file=sys.stderr,
        )
        return 1

    with sock:
        for name in names:
            sock.sendall((json.dumps({"op": "subscribe", "name": name}) + "\n").encode())
        print(
            f"Watching {len(names)} var(s). Move the control; the one that moves is it. "
            "Ctrl-C to stop.\n",
            file=sys.stderr,
        )
        seen: dict[str, object] = {}
        sock.settimeout(None)
        buf = b""
        start = time.monotonic()
        try:
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    print("bridge closed the connection", file=sys.stderr)
                    return 1
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
                        dt = time.monotonic() - start
                        print(f"[{dt:6.1f}s] {name} = {value}")
                        seen[name] = value
                    if once and len(seen) >= len(names):
                        return 0
        except KeyboardInterrupt:
            print("\nStopped.", file=sys.stderr)
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
