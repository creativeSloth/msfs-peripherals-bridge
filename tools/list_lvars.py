#!/usr/bin/env python3
"""Enumerate every LVar the running sim knows, via the bridge's MF.LVars.List path.

The bridge (bridge/bridge.py) exposes an ``op: list_lvars`` verb that asks the
MobiFlight WASM module to dump all registered LVar names into its Response area;
this script connects over TCP, triggers it, and prints the names (filtered).

Usage:
    python tools/list_lvars.py                 # all LVars, sorted
    python tools/list_lvars.py radio light     # only names containing 'radio' OR 'light'

The bridge is single-client (server.listen(1)): STOP THE MAPPER FIRST, e.g.
    pkill -f 'msfs_peripherals_bridge[ ]run'
then run this, then bring the mapper back with `msfs-bridge piper_arrow`.

Linux-side; talks to 127.0.0.1:7842. Needs MSFS running with the MobiFlight
event module loaded (same requirement as any L:/H:/B: read or write).
"""

from __future__ import annotations

import json
import socket
import sys

HOST, PORT = "127.0.0.1", 7842
REQUEST_TIMEOUT = 8.0  # seconds the bridge waits for the module to finish listing


def fetch_lvars(host: str = HOST, port: int = PORT) -> list[str]:
    """Connect, trigger the enumeration, and return the LVar names."""
    with socket.create_connection((host, port), timeout=10) as sock:
        sock.settimeout(REQUEST_TIMEOUT + 8)
        sock.sendall((json.dumps({"op": "list_lvars", "timeout": REQUEST_TIMEOUT}) + "\n").encode())
        buf = b""
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                raise SystemExit("bridge closed the connection before replying")
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                if not line.strip():
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if msg.get("op") == "lvars":  # skip the initial 'hello' frame
                    return list(msg.get("names", []))


def main() -> int:
    filters = [a.lower() for a in sys.argv[1:]]
    try:
        names = fetch_lvars()
    except OSError as exc:  # socket.timeout is an OSError subclass
        print(
            f"Could not reach the bridge on {HOST}:{PORT} ({exc}).\n"
            "Is MSFS running, the bridge up, and the mapper stopped?",
            file=sys.stderr,
        )
        return 1
    total = len(names)
    if filters:
        names = [n for n in names if any(f in n.lower() for f in filters)]
    for name in sorted(names):
        print(name)
    shown = f"{len(names)} of {total}" if filters else str(total)
    print(f"\n{shown} LVar(s)", file=sys.stderr)
    if total == 0:
        print(
            "No LVars returned — is the MobiFlight event module loaded "
            "(Community folder + MSFS restarted)?",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
