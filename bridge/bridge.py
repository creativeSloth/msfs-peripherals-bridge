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
import contextlib
import ctypes
import json
import logging
import os
import socket
import threading
import time

# Python-SimConnect bundles SimConnect.dll, so no MSFS SDK is needed. The
# import only works under Windows/Wine where that DLL can load.
from SimConnect import AircraftRequests, Event, SimConnect

try:
    # Request lets us read a SimVar with an EXPLICIT unit (so heading-bug sync
    # gets degrees, not whatever default the predefined list uses). Import
    # defensively: if a given build doesn't export it, the rest of the bridge
    # (events, TITLE poll) must still work.
    from SimConnect import Request
except ImportError:  # pragma: no cover - depends on the installed lib version
    Request = None

log = logging.getLogger("bridge")


class SimDisconnected(Exception):
    """Raised when SimConnect is gone (sim CTD / shut down).

    Signals the session to stop and ``main()`` to reconnect, instead of letting
    the bridge keep calling into a dead DLL handle — which access-violates,
    spams the log, and eventually segfaults the Wine-Python process.
    """


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7842
POLL_INTERVAL = 1.0  # seconds between subscribed-variable polls (e.g. TITLE)

# SimVar prefixes that standard SimConnect cannot set; they are routed through
# the MobiFlight WASM channel below. Plain writable A: vars go through SetData.
_LOCAL_PREFIXES = {"L", "H", "B"}

# MobiFlight WASM module command channel. Writing `MF.SimVars.Set.<rpn>` to the
# "MobiFlight.Command" ClientData area makes the module run <rpn> as calculator
# code, which is how we set L:/H:/B: vars (`<value> (>L:NAME)`). Write-only for
# now; reading LVars (for LED output) can be added later via RequestClientData.
# Requires the mobiflight-event-module in the Community folder + an MSFS restart.
_MF_COMMAND_AREA = b"MobiFlight.Command"
_MF_MESSAGE_SIZE = 1024  # MOBIFLIGHT_MESSAGE_SIZE
_MF_AREA_ID = 0x4D46  # 'MF' — any id unique within our SimConnect client
_MF_DEF_ID = 0x4D46
_SIMCONNECT_UNUSED = 0xFFFFFFFF


class SimConnectBridge:
    """Thin façade over Python-SimConnect for the three protocol verbs."""

    def __init__(self) -> None:
        self.sc = SimConnect()
        # _time=0 disables the request cache so polled values are always fresh.
        self.requests = AircraftRequests(self.sc, _time=0)
        # SimConnect.dll is NOT safe to call from two threads at once. Two of our
        # threads do: the session's poll loop reads SimVars while the dispatch
        # loop fires events / sets vars. Under a burst (e.g. pulling the yoke =
        # a stream of ELEVATOR_SET, plus gear/flaps) an overlapping read+write
        # access-violates the DLL (writing 0x10) and drops the link. Serialise
        # every DLL touch through this reentrant lock so calls never overlap.
        self._lock = threading.RLock()
        self._events: dict[str, Event] = {}
        # Cache explicit-unit Request objects by (name, unit): building one
        # registers a SimConnect data definition, so we must not leak one per
        # button press.
        self._var_requests: dict[tuple[str, str], object] = {}
        # Lazily-mapped MobiFlight command channel (see _ensure_mobiflight).
        self._mf_ready = False
        # Set once SimConnect is detected gone, so we stop touching the DLL.
        self._dead = False

    def _check_alive(self) -> None:
        """Raise :class:`SimDisconnected` *before* touching the DLL if the sim
        is gone. Catches a graceful QUIT (``sc.quit``) or a closed/never-opened
        handle (``sc.ok``). A hard CTD that sends no QUIT is caught instead by
        the ``OSError`` guards around each DLL call (see :meth:`_mark_lost`)."""
        if self._dead or getattr(self.sc, "quit", 0) or not getattr(self.sc, "ok", False):
            self._dead = True
            raise SimDisconnected("SimConnect connection lost")

    def _mark_lost(self, exc: BaseException) -> None:
        """A DLL call faulted (e.g. access violation on a dead handle) — flag
        the sim as gone and surface it as :class:`SimDisconnected`."""
        self._dead = True
        raise SimDisconnected(str(exc)) from exc

    def send_event(self, name: str, data: int) -> None:
        """Map (once) and transmit a SimConnect client event by name."""
        with self._lock:
            self._check_alive()
            try:
                event = self._events.get(name)
                if event is None:
                    event = Event(name.encode("ascii"), self.sc)
                    self._events[name] = event
                # Axis *_SET events expect a signed value; ctypes wraps it into the
                # 32-bit dwData, which the sim reads back as signed. Buttons send 1.
                event(int(data))
            except OSError as exc:
                self._mark_lost(exc)

    def set_simvar(self, name: str, value: float) -> None:
        with self._lock:
            self._check_alive()
            prefix = name.split(":", 1)[0].upper() if ":" in name else ""
            if prefix in _LOCAL_PREFIXES:
                # L:/H:/B: vars can't be set by plain SimConnect — run calculator
                # code through MobiFlight: `<value> (>L:NAME)`. Integers stay clean
                # (RPN reads "1" fine, "1.0" too, but "1" avoids surprises on H:).
                num = int(value) if float(value).is_integer() else value
                self._mf_exec(f"{num} (>{name})")
                return
            try:
                self.requests.set(name, value)
            except OSError as exc:
                self._mark_lost(exc)

    def _ensure_mobiflight(self) -> bool:
        """Map the MobiFlight command ClientData area once. Returns False
        (logged) if the WASM module isn't loaded — e.g. not installed in the
        Community folder, or MSFS not restarted since it was."""
        if self._mf_ready:
            return True
        dll, h = self.sc.dll, self.sc.hSimConnect
        hr = dll.MapClientDataNameToID(h, _MF_COMMAND_AREA, _MF_AREA_ID)
        if hr != 0:
            log.error(
                "MobiFlight: MapClientDataNameToID failed (0x%08X); is the "
                "mobiflight-event-module in Community and MSFS restarted?",
                hr & 0xFFFFFFFF,
            )
            return False
        hr = dll.AddToClientDataDefinition(
            h, _MF_DEF_ID, 0, _MF_MESSAGE_SIZE, 0.0, _SIMCONNECT_UNUSED
        )
        if hr != 0:
            log.error("MobiFlight: AddToClientDataDefinition failed (0x%08X)", hr & 0xFFFFFFFF)
            return False
        self._mf_ready = True
        log.info("MobiFlight WASM channel ready")
        return True

    def _mf_exec(self, code: str) -> None:
        """Run RPN/calculator code in the sim via MobiFlight (fire-and-forget)."""
        with self._lock:
            self._check_alive()
            if not self._ensure_mobiflight():
                return
            cmd = ("MF.SimVars.Set." + code).encode("ascii")
            buf = ctypes.create_string_buffer(cmd, _MF_MESSAGE_SIZE)
            try:
                hr = self.sc.dll.SetClientData(
                    self.sc.hSimConnect, _MF_AREA_ID, _MF_DEF_ID, 0, 0,
                    _MF_MESSAGE_SIZE, ctypes.cast(buf, ctypes.c_void_p),
                )
            except OSError as exc:
                self._mark_lost(exc)
            if hr != 0:
                log.error("MobiFlight: SetClientData failed (0x%08X) for %r", hr & 0xFFFFFFFF, code)
            else:
                log.info("MobiFlight exec: %s", code)

    def read_var(self, name: str, unit: str) -> object | None:
        """Read a SimVar with an explicit unit (e.g. heading in 'degrees').

        Uses a cached ``Request`` so any SimVar name works (not just the
        predefined list) and the unit is honoured. Falls back to the predefined
        ``read_simvar`` path if this build of the library lacks ``Request``.
        """
        with self._lock:
            self._check_alive()
            if Request is None:
                return self.read_simvar(name)
            key = (name, unit or "number")
            req = self._var_requests.get(key)
            try:
                if req is None:
                    deff = (name.encode("ascii"), (unit or "number").encode("ascii"))
                    req = Request(deff, self.sc, _time=0)
                    self._var_requests[key] = req
                value = req.value
            except Exception as exc:
                log.debug("read %s [%s] failed: %s", name, unit, exc)
                return None
            if isinstance(value, bytes):
                return value.decode("utf-8", "replace").rstrip("\x00")
            return value

    def event_from_var(self, event: str, read: str, unit: str) -> None:
        """Read ``read`` (in ``unit``) right now, then fire ``event`` with it.

        The dynamic button action: e.g. read PLANE HEADING DEGREES MAGNETIC and
        send HEADING_BUG_SET so one button snaps the AP heading bug to the
        current heading. Skips silently (logged) if the value can't be read.
        """
        value = self.read_var(read, unit)
        if value is None:
            log.warning("event_from_var: could not read %s; %s not sent", read, event)
            return
        try:
            data = round(float(value))
        except (TypeError, ValueError):
            log.warning(
                "event_from_var: %s value %r is not numeric; %s not sent", read, value, event
            )
            return
        log.info("event_from_var: %s=%s -> %s(%d)", read, value, event, data)
        self.send_event(event, data)

    def read_simvar(self, name: str) -> object | None:
        """Read a known SimVar (e.g. TITLE). Returns None if unavailable.

        Python-SimConnect keys requests by their underscored name
        (``AUTOPILOT_HEADING_LOCK_DIR``), but the docs/profiles spell SimVars
        with spaces (``AUTOPILOT HEADING LOCK DIR``). Try the name as given,
        then the normalised form, so either spelling works.
        """
        with self._lock:
            self._check_alive()
            value = None
            for candidate in (name, name.strip().upper().replace(" ", "_")):
                try:
                    value = self.requests.get(candidate)
                except OSError as exc:
                    self._mark_lost(exc)
                except Exception as exc:
                    log.debug("read %s failed: %s", candidate, exc)
                    value = None
                if value is not None:
                    break
            if value is None:
                return None
            if isinstance(value, bytes):
                return value.decode("utf-8", "replace").rstrip("\x00")
            return value

    def close(self) -> None:
        with self._lock, contextlib.suppress(Exception):
            self.sc.exit()


class ClientSession:
    """Handles one connected Linux client: read commands, stream state back."""

    def __init__(self, conn: socket.socket, sim: SimConnectBridge) -> None:
        self.conn = conn
        self.sim = sim
        self._subscriptions: dict[str, object] = {}  # name -> last sent value
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._sim_lost = threading.Event()

    def serve(self) -> bool:
        """Run the session until the client or the sim drops.

        Returns ``True`` if it ended because SimConnect was lost (so ``main()``
        reconnects), ``False`` on a normal client disconnect.
        """
        self._send({"op": "hello", "sim": "MSFS", "version": "python-simconnect"})
        poller = threading.Thread(target=self._poll_loop, daemon=True)
        poller.start()
        try:
            self._read_loop()
        finally:
            self._stop.set()
        return self._sim_lost.is_set()

    # -- inbound ---------------------------------------------------------
    def _read_loop(self) -> None:
        buffer = b""
        while not self._stop.is_set():
            try:
                chunk = self.conn.recv(4096)
            except OSError as exc:
                # The Linux app dropping (e.g. Ctrl-C) must NOT kill the bridge;
                # just end this session and go back to waiting for a client.
                log.info("Client connection ended (%s)", exc)
                return
            if not chunk:
                log.info("Client disconnected")
                return
            buffer += chunk
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                if line.strip():
                    self._dispatch(line.decode("utf-8", "replace"))

    def _dispatch(self, line: str) -> None:
        if self._sim_lost.is_set():
            return
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            log.warning("Ignoring malformed frame: %r", line)
            return
        op = msg.get("op")
        try:
            if op == "event":
                self.sim.send_event(msg["name"], int(msg.get("data", 0)))
            elif op == "event_from_var":
                self.sim.event_from_var(
                    msg["event"], msg["read"], msg.get("unit", "number")
                )
            elif op == "simvar":
                self.sim.set_simvar(msg["name"], float(msg["value"]))
            elif op == "rpn":
                # Raw calculator/RPN code run via MobiFlight — fires K: events
                # and sets L: vars in one string (SPAD VALUEON/VALUEOFF style).
                self.sim._mf_exec(msg["code"])
            elif op == "subscribe":
                with self._lock:
                    self._subscriptions.setdefault(msg["name"], None)
                log.info("Subscribed to %s", msg["name"])
            else:
                log.warning("Unknown op: %r", op)
        except SimDisconnected as exc:
            self._on_sim_lost(exc)
        except Exception as exc:
            log.error("Failed to handle %s: %s", op, exc)

    def _on_sim_lost(self, exc: BaseException) -> None:
        """SimConnect went away mid-session: log once, stop the loops, and
        unblock a ``recv`` that may be parked waiting on an idle client."""
        if not self._sim_lost.is_set():
            log.warning("SimConnect lost (%s) — ending session to reconnect", exc)
        self._sim_lost.set()
        self._stop.set()
        with contextlib.suppress(OSError):
            self.conn.shutdown(socket.SHUT_RDWR)

    # -- outbound --------------------------------------------------------
    def _poll_loop(self) -> None:
        while not self._stop.is_set():
            with self._lock:
                names = list(self._subscriptions)
            for name in names:
                try:
                    value = self.sim.read_simvar(name)
                except SimDisconnected as exc:
                    self._on_sim_lost(exc)
                    return
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


def connect_sim(retries: int | None = None, delay: float = 2.0) -> SimConnectBridge:
    """Wait for MSFS's SimConnect server to accept us (it may start later).

    Retries forever by default so a single bridge process rides out any MSFS
    downtime — a CTD plus however long it takes to restart the sim — and
    re-attaches on its own, instead of exiting and leaning on the supervisor to
    relaunch it (which loses the listening socket each time). Pass a finite
    ``retries`` to bound the wait.
    """
    attempt = 0
    while True:
        attempt += 1
        try:
            sim = SimConnectBridge()
            log.info("Connected to SimConnect")
            return sim
        except Exception as exc:
            if retries is not None and attempt >= retries:
                raise SystemExit("Could not connect to SimConnect — is MSFS running?") from exc
            # Quiet by default (this can loop for minutes): first try, then sparse.
            if attempt == 1 or attempt % 15 == 0:
                log.info("SimConnect not ready (attempt %d): %s", attempt, exc)
            time.sleep(delay)


def main() -> None:
    parser = argparse.ArgumentParser(description="Wine-side SimConnect bridge")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    # Log to a file next to this script as well as stderr: Wine block-buffers
    # the piped stderr so console logs can vanish, but the FileHandler flushes
    # each record straight to the real (Linux-visible) file.
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bridge.log")
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(),
            # Append (not truncate): a hard MSFS CTD kills this process and the
            # supervisor restarts it — truncating here would wipe the crash
            # evidence (and the supervisor's restart line) every time. Keep the
            # history so a recurring break can actually be diagnosed.
            logging.FileHandler(log_path, mode="a", encoding="utf-8"),
        ],
    )
    log.info("================ bridge starting (pid %d) ================", os.getpid())
    log.info("Logging to %s", log_path)

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
            sim_lost = False
            try:
                sim_lost = ClientSession(conn, sim).serve()
            except Exception:
                log.exception("Session ended with an error; waiting for next client")
            finally:
                conn.close()
            # A sim CTD/shutdown leaves SimConnect dead; drop the old handle and
            # wait for MSFS to come back so the bridge re-attaches on its own.
            if sim_lost or getattr(sim.sc, "quit", 0):
                log.warning("Reconnecting to SimConnect (waiting for MSFS)…")
                sim.close()
                sim = connect_sim()
            log.info("Ready for next client on %s:%s", args.host, args.port)
    except KeyboardInterrupt:
        log.info("Shutting down")
    finally:
        server.close()
        sim.close()


if __name__ == "__main__":
    main()
