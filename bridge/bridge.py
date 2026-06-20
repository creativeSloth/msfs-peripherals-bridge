#!/usr/bin/env python3
"""Wine-side SimConnect bridge.

Runs **inside the same Proton/Wine prefix as MSFS** (under a Windows Python),
links SimConnect via the Python-SimConnect package, and relays the Linux app's
newline-delimited JSON protocol to/from SimConnect over a local TCP socket.

    Linux app ──TCP 127.0.0.1:7842 (newline JSON)──► bridge (Wine) ──► SimConnect ──► MSFS
                                                  ◄── state frames ◄──

Protocol (mirrors src/msfs_peripherals_bridge/simconnect/protocol.py):
    Linux → bridge  {"op":"event","name":"THROTTLE1_SET","data":8192}
    Linux → bridge  {"op":"simvar","name":"L:Trim","unit":"number","value":0.5}
    Linux → bridge  {"op":"subscribe","name":"TITLE","unit":"string"}
    bridge → Linux  {"op":"hello","sim":"MSFS","version":"python-simconnect"}
    bridge → Linux  {"op":"state","name":"TITLE","value":"Cessna 172"}

This file has no dependency on the Linux package; it is copied into the prefix
and run there. Keep it self-contained.
"""

from __future__ import annotations

import argparse
import json
import logging
import socket
import threading
import time

# Python-SimConnect bundles SimConnect.dll, so no MSFS SDK is needed. The
# import only works under Windows/Wine where that DLL can load.
from SimConnect import AircraftRequests, Event, SimConnect

log = logging.getLogger("bridge")

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7842
POLL_INTERVAL = 1.0  # seconds between subscribed-variable polls (e.g. TITLE)

# SimVar prefixes that standard SimConnect cannot set; they need the MobiFlight
# WASM channel (not yet wired). Plain writable A: vars go through SetData.
_LOCAL_PREFIXES = {"L", "H", "B"}


class SimConnectBridge:
    """Thin façade over Python-SimConnect for the three protocol verbs."""

    def __init__(self) -> None:
        self.sc = SimConnect()
        # _time=0 disables the request cache so polled values are always fresh.
        self.requests = AircraftRequests(self.sc, _time=0)
        self._events: dict[str, Event] = {}

    def send_event(self, name: str, data: int) -> None:
        """Map (once) and transmit a SimConnect client event by name."""
        event = self._events.get(name)
        if event is None:
            event = Event(name.encode("ascii"), self.sc)
            self._events[name] = event
        # Axis *_SET events expect a signed value; ctypes wraps it into the
        # 32-bit dwData, which the sim reads back as signed. Buttons send 1.
        event(int(data))

    def set_simvar(self, name: str, value: float) -> None:
        prefix = name.split(":", 1)[0].upper() if ":" in name else ""
        if prefix in _LOCAL_PREFIXES:
            log.warning(
                "simvar %s needs the MobiFlight WASM channel (L:/H:/B:); not yet supported",
                name,
            )
            return
        self.requests.set(name, value)

    def read_simvar(self, name: str) -> object | None:
        """Read a known SimVar (e.g. TITLE). Returns None if unavailable."""
        try:
            value = self.requests.get(name)
        except Exception as exc:  # noqa: BLE001 - library raises broadly
            log.debug("read %s failed: %s", name, exc)
            return None
        if isinstance(value, bytes):
            return value.decode("utf-8", "replace").rstrip("\x00")
        return value

    def close(self) -> None:
        try:
            self.sc.exit()
        except Exception:  # noqa: BLE001
            pass


class ClientSession:
    """Handles one connected Linux client: read commands, stream state back."""

    def __init__(self, conn: socket.socket, sim: SimConnectBridge) -> None:
        self.conn = conn
        self.sim = sim
        self._subscriptions: dict[str, object] = {}  # name -> last sent value
        self._lock = threading.Lock()
        self._stop = threading.Event()

    def serve(self) -> None:
        self._send({"op": "hello", "sim": "MSFS", "version": "python-simconnect"})
        poller = threading.Thread(target=self._poll_loop, daemon=True)
        poller.start()
        try:
            self._read_loop()
        finally:
            self._stop.set()

    # -- inbound ---------------------------------------------------------
    def _read_loop(self) -> None:
        buffer = b""
        while not self._stop.is_set():
            chunk = self.conn.recv(4096)
            if not chunk:
                log.info("Client disconnected")
                return
            buffer += chunk
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                if line.strip():
                    self._dispatch(line.decode("utf-8", "replace"))

    def _dispatch(self, line: str) -> None:
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            log.warning("Ignoring malformed frame: %r", line)
            return
        op = msg.get("op")
        try:
            if op == "event":
                self.sim.send_event(msg["name"], int(msg.get("data", 0)))
            elif op == "simvar":
                self.sim.set_simvar(msg["name"], float(msg["value"]))
            elif op == "subscribe":
                with self._lock:
                    self._subscriptions.setdefault(msg["name"], None)
                log.info("Subscribed to %s", msg["name"])
            else:
                log.warning("Unknown op: %r", op)
        except Exception as exc:  # noqa: BLE001 - never let one bad frame kill us
            log.error("Failed to handle %s: %s", op, exc)

    # -- outbound --------------------------------------------------------
    def _poll_loop(self) -> None:
        while not self._stop.is_set():
            with self._lock:
                names = list(self._subscriptions)
            for name in names:
                value = self.sim.read_simvar(name)
                if value is None:
                    continue
                with self._lock:
                    changed = self._subscriptions.get(name) != value
                    if changed:
                        self._subscriptions[name] = value
                if changed:
                    self._send({"op": "state", "name": name, "value": value})
            self._stop.wait(POLL_INTERVAL)

    def _send(self, frame: dict[str, object]) -> None:
        try:
            self.conn.sendall((json.dumps(frame) + "\n").encode("utf-8"))
        except OSError:
            self._stop.set()


def connect_sim(retries: int = 30, delay: float = 2.0) -> SimConnectBridge:
    """Wait for MSFS's SimConnect server to accept us (it may start later)."""
    for attempt in range(1, retries + 1):
        try:
            sim = SimConnectBridge()
            log.info("Connected to SimConnect")
            return sim
        except Exception as exc:  # noqa: BLE001 - ConnectionError variants
            log.info("SimConnect not ready (%d/%d): %s", attempt, retries, exc)
            time.sleep(delay)
    raise SystemExit("Could not connect to SimConnect — is MSFS running?")


def main() -> None:
    parser = argparse.ArgumentParser(description="Wine-side SimConnect bridge")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    sim = connect_sim()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((args.host, args.port))
    server.listen(1)
    log.info("Bridge listening on %s:%s", args.host, args.port)
    try:
        while True:
            conn, addr = server.accept()
            log.info("Linux app connected from %s", addr)
            try:
                ClientSession(conn, sim).serve()
            finally:
                conn.close()
    except KeyboardInterrupt:
        log.info("Shutting down")
    finally:
        server.close()
        sim.close()


if __name__ == "__main__":
    main()
