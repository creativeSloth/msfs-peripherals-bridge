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
from collections.abc import Callable, Iterator

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

try:
    # The reply struct MobiFlight streams LVar values on (RECV_ID_CLIENT_DATA).
    # Needed to decode the LVar read channel; absent on very old lib builds, in
    # which case LVar reads are simply unavailable (the LEDs stay dark, no crash).
    from SimConnect.Enum import SIMCONNECT_RECV_CLIENT_DATA
except ImportError:  # pragma: no cover - depends on the installed lib version
    SIMCONNECT_RECV_CLIENT_DATA = None

try:
    # The reply struct the sim pushes periodic SimVar data on (RECV_ID_SIMOBJECT_DATA).
    # Subscribed A: vars are registered as standing per-second requests so their values
    # arrive here (pushed onto the dispatch thread) instead of being pulled under the
    # DLL lock — see _start_stream. Absent on old lib builds, in which case reads simply
    # stay on the on-demand pull path (no crash, just the old contention).
    from SimConnect.Enum import SIMCONNECT_RECV_SIMOBJECT_DATA
except ImportError:  # pragma: no cover - depends on the installed lib version
    SIMCONNECT_RECV_SIMOBJECT_DATA = None

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

# MobiFlight LVar READ channel. Writing `MF.SimVars.Add.(<expr>)` to the command
# area makes the module evaluate <expr> (e.g. `(L:AUTOPILOT_MODE)`) every frame
# and stream the float result into the "MobiFlight.LVars" ClientData area, at the
# slot index assigned in add-order (slot i → byte offset i*4). We map that area,
# RequestClientData one float per registered var (change-driven), and decode the
# RECV_ID_CLIENT_DATA replies. `MF.SimVars.Clear` resets the list so our indices
# line up after a reconnect. Assumes the bridge is the sole user of the shared
# MobiFlight areas (true here — SPAD.neXt uses its own channel).
_MF_LVAR_AREA = b"MobiFlight.LVars"
_MF_LVAR_AREA_ID = 0x4D47
_MF_LVAR_DEF_BASE = 0x4D470000  # + slot index; distinct from _MF_DEF_ID
_MF_LVAR_REQ_BASE = 0x4D480000  # + slot index; far from the lib's own request ids
_MF_FLOAT_SIZE = 4
_RECV_ID_CLIENT_DATA = 16  # SIMCONNECT_RECV_ID_CLIENT_DATA
_CLIENT_DATA_PERIOD_ON_SET = 3  # SIMCONNECT_CLIENT_DATA_PERIOD_ON_SET
_CLIENT_DATA_REQUEST_FLAG_CHANGED = 1  # send only when the value changes

# MobiFlight LVar ENUMERATION channel. Sending `MF.LVars.List` to the command
# area makes the module write every registered LVar name (one message each) into
# the "MobiFlight.Response" string area, bracketed by the marker lines
# `MF.LVars.List.Start` / `MF.LVars.List.End` (both verified in the module DLL on
# disk). We map that area, RequestClientData a 1024-byte string on every set, and
# collect the names on the dispatch thread until the End marker (or a timeout).
# One-shot discovery tool — the streamed values still come over the LVars area.
_MF_RESPONSE_AREA = b"MobiFlight.Response"
_MF_RESPONSE_AREA_ID = 0x4D49
_MF_RESPONSE_DEF_ID = 0x4D49
_MF_RESPONSE_REQ_ID = 0x4D4A0001  # far from _MF_LVAR_REQ_BASE (0x4D480000+idx)
_MF_LVARS_LIST_START = "MF.LVars.List.Start"
_MF_LVARS_LIST_END = "MF.LVars.List.End"

# Streamed SimVar READ channel. The stock read is a synchronous
# RequestDataOnSimObjectType + spin-wait (SimConnect.get_data) that holds the DLL lock
# across the whole Wine round-trip, so a polling client stalls the mapper's real-time
# axis writes. Instead we register each subscribed A: var *once* as a standing periodic
# RequestDataOnSimObject: the sim then pushes its value onto the library's dispatch
# thread (filling Request.outData), and the poll read becomes a lock-free attribute
# read that never competes with a write for the lock. Per SIM_FRAME + change-driven:
# the sim re-pushes a var only when it actually changes, within a frame of the change,
# so the cache stays as fresh as the old on-demand read — the poll loop's forward to
# the client keeps the same ~1 s latency, and an off-cycle read_now (the Radio Panel's
# post-tune echo) still sees the just-changed value. A once-per-second cadence
# (PERIOD_SECOND=4, flag=0) would instead add a second stage of up to 1 s and hand
# read_now a stale value, so the displays/LEDs would lag — hence per-frame. The first
# value (before any change) is covered by the warm-up pull fallback, so change-driven
# needing an actual change to emit is fine. Change-driven keeps traffic low: the Arrow's
# output vars are mostly discrete (gear, AP master, frequencies) and stay silent when idle.
_RECV_ID_SIMOBJECT_DATA = 8  # SIMCONNECT_RECV_ID_SIMOBJECT_DATA
_SIMOBJECT_ID_USER = 0  # SIMCONNECT_OBJECT_ID_USER
_STREAM_PERIOD = 3  # SIMCONNECT_PERIOD_SIM_FRAME — push when it changes, within a frame
_STREAM_FLAG = 1  # SIMCONNECT_DATA_REQUEST_FLAG_CHANGED — only on change (warm-up pull covers t0)


class _ReadingSimConnect(SimConnect):
    """SimConnect that also delivers ``RECV_ID_CLIENT_DATA`` to a callback.

    The stock Python-SimConnect dispatch proc ignores CLIENT_DATA — the reply
    channel MobiFlight streams LVar values on — so LVar reads never arrive.
    ``my_dispatch_proc`` is a *bound method* the base wraps into the C callback
    at init, so overriding it here (and deferring to ``super()`` for every other
    message) is enough to fan CLIENT_DATA out. ``on_client_data`` runs on the
    library's dispatch thread and must not call back into the DLL.
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        # Set before super().__init__ starts the dispatch thread, so an early
        # frame finds the attribute (a no-op until the bridge wires it up).
        self.on_client_data: Callable[[int, float], None] | None = None
        # Request ids whose CLIENT_DATA payload is a NUL-terminated string (the
        # MobiFlight Response area) rather than a float — decoded via on_client_string.
        self.on_client_string: Callable[[int, str], None] | None = None
        self._string_request_ids: set[int] = set()
        super().__init__(*args, **kwargs)

    def my_dispatch_proc(self, pData, cbData, pContext):
        dwID = pData.contents.dwID
        if dwID == _RECV_ID_SIMOBJECT_DATA and SIMCONNECT_RECV_SIMOBJECT_DATA is not None:
            # A streamed SimVar push (a standing periodic RequestDataOnSimObject we set
            # up). The base proc fills Request.outData only for the one-shot BYTYPE
            # reply; route the periodic reply through the very same handler so the value
            # lands in the matching Request.outData, turning the poll read into a
            # lock-free attribute read. Runs on the dispatch thread and must not call
            # back into the DLL — handle_simobject_event only does dict/ctypes work.
            obj = ctypes.cast(pData, ctypes.POINTER(SIMCONNECT_RECV_SIMOBJECT_DATA)).contents
            self.handle_simobject_event(obj)
            return None
        if dwID == _RECV_ID_CLIENT_DATA and SIMCONNECT_RECV_CLIENT_DATA is not None:
            recv = ctypes.cast(
                pData, ctypes.POINTER(SIMCONNECT_RECV_CLIENT_DATA)
            ).contents
            if recv.dwRequestID in self._string_request_ids:
                cb = self.on_client_string
                if cb is not None:
                    raw = ctypes.cast(recv.dwData, ctypes.c_char_p).value or b""
                    cb(recv.dwRequestID, raw.decode("ascii", "replace"))
                return None
            cb = self.on_client_data
            if cb is not None:
                value = ctypes.cast(
                    recv.dwData, ctypes.POINTER(ctypes.c_float)
                ).contents.value
                cb(recv.dwRequestID, value)
            return None
        return super().my_dispatch_proc(pData, cbData, pContext)


class _PriorityLock:
    """Mutual exclusion over the DLL that lets writers preempt readers.

    SimConnect.dll must be touched by one thread at a time, so reads and writes
    are mutually exclusive. But the mapper's real-time control *writes* (events,
    SimVar sets) must not be starved by a client's continuous background *reads*
    (the per-session poll loop). With one client that was harmless — the mapper
    was the only one polling — but once a second client (the GUI value monitor)
    polls concurrently, its steady stream of SimVar reads kept grabbing the lock
    between the yoke/rudder writes, so the axes arrived choppy.

    A waiting writer is therefore served before any waiting reader, and readers
    take turns (``_read_turnstile``) so at most one is ever queued on the mutex
    ahead of a writer. A control write thus waits at most one in-flight read (a
    few ms) instead of a whole poll cycle. The write side is reentrant
    (``set_simvar`` nests ``_mf_exec``); both sides are exclusive. Readers may be
    deferred while writes keep coming — correct here: fresh control beats a
    slightly stale telemetry/LED read, and coalesced axis writes leave gaps.
    """

    def __init__(self) -> None:
        self._mutex = threading.RLock()  # the actual DLL guard (writer-reentrant)
        self._gate = threading.Condition(threading.Lock())
        self._writers_waiting = 0
        self._read_turnstile = threading.Lock()
        self._read_owner: int | None = None  # thread inside read(), for reentrancy

    @contextlib.contextmanager
    def write(self) -> Iterator[None]:
        # Reentrant via the RLock mutex (set_simvar nests _mf_exec); the counter
        # simply stays >0 across the nesting, which keeps readers deferred.
        with self._gate:
            self._writers_waiting += 1
        try:
            with self._mutex:
                yield
        finally:
            with self._gate:
                self._writers_waiting -= 1
                if self._writers_waiting == 0:
                    self._gate.notify_all()

    @contextlib.contextmanager
    def read(self) -> Iterator[None]:
        me = threading.get_ident()
        if self._read_owner == me:
            # Reentrant read (read_var falls back to read_simvar); this thread
            # already holds the mutex, so pass straight through — re-taking the
            # non-reentrant turnstile here would self-deadlock.
            yield
            return
        with self._read_turnstile:  # one reader queues on the mutex at a time
            with self._gate:
                while self._writers_waiting:
                    self._gate.wait()
            with self._mutex:
                self._read_owner = me
                try:
                    yield
                finally:
                    self._read_owner = None


class SimConnectBridge:
    """Thin façade over Python-SimConnect for the three protocol verbs."""

    def __init__(self) -> None:
        self.sc = _ReadingSimConnect()
        # Receive MobiFlight's LVar value stream (see the LVar read methods).
        self.sc.on_client_data = self._on_client_data
        # _time=0 disables the request cache so polled values are always fresh.
        self.requests = AircraftRequests(self.sc, _time=0)
        # SimConnect.dll is NOT safe to call from two threads at once. Several of
        # our threads do: each session's poll loop reads SimVars while dispatch
        # loops fire events / set vars. Under a burst (e.g. pulling the yoke =
        # a stream of ELEVATOR_SET, plus gear/flaps) an overlapping read+write
        # access-violates the DLL (writing 0x10) and drops the link. Serialise
        # every DLL touch through this lock so calls never overlap — and let the
        # real-time control *writes* preempt background poll *reads* so a second
        # client's polling can't make the axes stutter (see _PriorityLock).
        self._lock = _PriorityLock()
        self._events: dict[str, Event] = {}
        # Cache explicit-unit Request objects by (name, unit): building one
        # registers a SimConnect data definition, so we must not leak one per
        # button press.
        self._var_requests: dict[tuple[str, str], object] = {}
        # Streamed SimVar reads: subscribed-name -> the Request whose .outData the sim
        # now pushes into (see _start_stream / read_subscribed). Shared across client
        # poll threads; setup is guarded by the write lock, and .outData is an atomic
        # single-reference read, so steady-state reads take no lock and never stall a
        # control write.
        self._stream_reqs: dict[str, object] = {}
        # Dedicated per-name Request objects for *indexed* streamed vars. Indexed
        # SimVars (COM ACTIVE FREQUENCY:1 / :2) all resolve to one shared predefined
        # Request in python-simconnect, so each index needs its own object to stream
        # independently (see _resolve_request). Keyed by full name (with index).
        self._stream_var_requests: dict[str, object] = {}
        # Lazily-mapped MobiFlight command channel (see _ensure_mobiflight).
        self._mf_ready = False
        # MobiFlight LVar READ channel state. Registration (DLL calls) happens on
        # the poll thread under self._lock; the streamed values land from the
        # dispatch thread, so the two cross-thread dicts get their own light lock
        # (the dispatch callback must never take self._lock — it would stall the
        # library's dispatch loop behind a long DLL write).
        self._lvar_area_ready = False
        self._lvar_next = 0  # next free slot index in the LVars area
        self._lvar_index: dict[str, int] = {}  # name -> slot (poll thread only)
        self._lvar_lock = threading.Lock()
        self._lvar_by_req: dict[int, str] = {}  # request id -> name (cross-thread)
        self._lvar_values: dict[str, float] = {}  # name -> latest value (cross-thread)
        # MobiFlight LVar ENUMERATION channel (MF.LVars.List → Response area). The
        # module streams names on the dispatch thread; list_lvars() collects them.
        self.sc.on_client_string = self._on_client_string
        self._resp_ready = False
        self._resp_lock = threading.Lock()
        self._resp_names: list[str] = []  # collected between the List markers
        self._resp_collecting = False
        self._resp_done = threading.Event()  # set when the End marker arrives
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
        with self._lock.write():
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
        with self._lock.write():
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

    def _mf_command(self, cmd: str) -> bool:
        """Write one command string to the MobiFlight command area.

        The caller must hold ``self._lock`` and have checked the sim is alive.
        Returns False (logged) if the channel isn't ready or the write failed.
        """
        if not self._ensure_mobiflight():
            return False
        buf = ctypes.create_string_buffer(cmd.encode("ascii"), _MF_MESSAGE_SIZE)
        try:
            hr = self.sc.dll.SetClientData(
                self.sc.hSimConnect, _MF_AREA_ID, _MF_DEF_ID, 0, 0,
                _MF_MESSAGE_SIZE, ctypes.cast(buf, ctypes.c_void_p),
            )
        except OSError as exc:
            self._mark_lost(exc)  # raises SimDisconnected
        if hr != 0:
            log.error("MobiFlight: SetClientData failed (0x%08X) for %r", hr & 0xFFFFFFFF, cmd)
            return False
        return True

    def _mf_exec(self, code: str) -> None:
        """Run RPN/calculator code in the sim via MobiFlight (fire-and-forget)."""
        with self._lock.write():
            self._check_alive()
            if self._mf_command("MF.SimVars.Set." + code):
                log.info("MobiFlight exec: %s", code)

    # -- LVar read channel (see the _MF_LVAR_* constants) ------------------
    def _ensure_lvar_area(self) -> bool:
        """Map the MobiFlight LVars area once and start from an empty var list.

        Caller holds ``self._lock``. Clearing means the module's registration
        order (hence each var's slot index) matches our add order, even after a
        reconnect that left stale registrations behind.
        """
        if self._lvar_area_ready:
            return True
        if not self._ensure_mobiflight():
            return False
        hr = self.sc.dll.MapClientDataNameToID(self.sc.hSimConnect, _MF_LVAR_AREA, _MF_LVAR_AREA_ID)
        if hr != 0:
            log.error("MobiFlight: map LVars area failed (0x%08X)", hr & 0xFFFFFFFF)
            return False
        self._mf_command("MF.SimVars.Clear")
        self._lvar_next = 0
        self._lvar_index.clear()
        with self._lvar_lock:
            self._lvar_by_req.clear()
            self._lvar_values.clear()
        self._lvar_area_ready = True
        log.info("MobiFlight LVar read channel ready")
        return True

    def _register_lvar(self, name: str) -> None:
        """Subscribe ``name`` (e.g. ``L:AUTOPILOT_MODE``) to the LVar stream.

        Caller holds ``self._lock``. Sets up a change-driven RequestClientData on
        this var's slot, then tells the module to evaluate + stream it there.
        """
        if not self._ensure_lvar_area():
            return
        idx = self._lvar_next
        define_id = _MF_LVAR_DEF_BASE + idx
        request_id = _MF_LVAR_REQ_BASE + idx
        hr = self.sc.dll.AddToClientDataDefinition(
            self.sc.hSimConnect, define_id, idx * _MF_FLOAT_SIZE, _MF_FLOAT_SIZE, 0.0,
            _SIMCONNECT_UNUSED,
        )
        if hr != 0:
            log.error("MobiFlight: AddToClientDataDefinition failed (0x%08X) for %s",
                      hr & 0xFFFFFFFF, name)
            return
        hr = self.sc.dll.RequestClientData(
            self.sc.hSimConnect, _MF_LVAR_AREA_ID, request_id, define_id,
            _CLIENT_DATA_PERIOD_ON_SET, _CLIENT_DATA_REQUEST_FLAG_CHANGED, 0, 0, 0,
        )
        if hr != 0:
            log.error("MobiFlight: RequestClientData failed (0x%08X) for %s", hr & 0xFFFFFFFF, name)
            return
        # Register the expression last: only now does the module start streaming
        # into slot idx, which the request above is already watching.
        if not self._mf_command(f"MF.SimVars.Add.({name})"):
            return
        self._lvar_next += 1
        self._lvar_index[name] = idx
        with self._lvar_lock:
            self._lvar_by_req[request_id] = name
        log.info("MobiFlight LVar registered: %s (slot %d)", name, idx)

    def _on_client_data(self, request_id: int, value: float) -> None:
        """Store a streamed LVar value (runs on the library's dispatch thread)."""
        with self._lvar_lock:
            name = self._lvar_by_req.get(request_id)
            if name is not None:
                self._lvar_values[name] = value

    def read_lvar(self, name: str) -> float | None:
        """Latest streamed value of an L:/H:/B: var, registering it on first use.

        Returns None until the module has streamed at least one value (or if the
        MobiFlight channel isn't available), so the LEDs stay dark rather than
        guess — same contract as read_simvar.
        """
        with self._lock.read():
            self._check_alive()
            if name not in self._lvar_index:
                self._register_lvar(name)
        with self._lvar_lock:
            return self._lvar_values.get(name)

    # -- LVar enumeration channel (see the _MF_RESPONSE_* constants) --------
    def _ensure_response_area(self) -> bool:
        """Map the MobiFlight Response string area once and stream every set of
        it to :meth:`_on_client_string`. Caller holds ``self._lock``."""
        if self._resp_ready:
            return True
        if not self._ensure_mobiflight():
            return False
        hr = self.sc.dll.MapClientDataNameToID(
            self.sc.hSimConnect, _MF_RESPONSE_AREA, _MF_RESPONSE_AREA_ID
        )
        if hr != 0:
            log.error("MobiFlight: map Response area failed (0x%08X)", hr & 0xFFFFFFFF)
            return False
        hr = self.sc.dll.AddToClientDataDefinition(
            self.sc.hSimConnect, _MF_RESPONSE_DEF_ID, 0, _MF_MESSAGE_SIZE, 0.0,
            _SIMCONNECT_UNUSED,
        )
        if hr != 0:
            log.error("MobiFlight: Response AddToClientDataDefinition failed (0x%08X)",
                      hr & 0xFFFFFFFF)
            return False
        # Flag 0 (not CHANGED): deliver every write, so no name is dropped even
        # if two consecutive Response messages happen to be equal.
        hr = self.sc.dll.RequestClientData(
            self.sc.hSimConnect, _MF_RESPONSE_AREA_ID, _MF_RESPONSE_REQ_ID,
            _MF_RESPONSE_DEF_ID, _CLIENT_DATA_PERIOD_ON_SET, 0, 0, 0, 0,
        )
        if hr != 0:
            log.error("MobiFlight: Response RequestClientData failed (0x%08X)", hr & 0xFFFFFFFF)
            return False
        self.sc._string_request_ids.add(_MF_RESPONSE_REQ_ID)
        self._resp_ready = True
        log.info("MobiFlight Response channel ready")
        return True

    def _on_client_string(self, request_id: int, text: str) -> None:
        """Collect a Response line (runs on the library's dispatch thread).

        ``list_lvars`` primes ``_resp_collecting`` before sending the command, so
        this works whether or not the Start marker is seen; the End marker (or a
        timeout in ``list_lvars``) closes the batch.
        """
        with self._resp_lock:
            if text == _MF_LVARS_LIST_START:
                self._resp_names = []
                self._resp_collecting = True
            elif text == _MF_LVARS_LIST_END:
                self._resp_collecting = False
                self._resp_done.set()
            elif self._resp_collecting and text:
                self._resp_names.append(text)

    def list_lvars(self, timeout: float = 8.0) -> list[str]:
        """Enumerate every LVar the sim currently knows (``MF.LVars.List``).

        Returns the names MobiFlight reports (without the ``L:`` prefix), or ``[]``
        if the channel isn't available or nothing arrived in time. One-shot
        discovery helper — safe to call while the value stream is also running.
        """
        with self._lock.read():
            self._check_alive()
            if not self._ensure_response_area():
                return []
            with self._resp_lock:
                self._resp_names = []
                self._resp_collecting = True
                self._resp_done.clear()
            if not self._mf_command("MF.LVars.List"):
                return []
        self._resp_done.wait(timeout)
        with self._resp_lock:
            self._resp_collecting = False
            return list(self._resp_names)

    def read_subscribed(self, name: str, unit: str = "number") -> object | None:
        """Read a subscribed var: L:/H:/B: via the MobiFlight stream, else SimConnect.

        Plain SimVars are served from a standing per-frame, change-driven push (see
        :meth:`_start_stream`): the first read for a name sets the stream up (under the
        write lock), and every later read is a lock-free ``Request.outData`` access that
        no longer competes with the mapper's real-time axis writes for the DLL lock.
        Until the first value has been pushed — or if streaming isn't delivering on this
        Wine build — it falls back to the old synchronous pull, so a value is always
        returned and the change is only that steady-state reads stop taking the lock.
        """
        prefix = name.split(":", 1)[0].upper() if ":" in name else ""
        if prefix in _LOCAL_PREFIXES:
            return self.read_lvar(name)
        req = self._stream_reqs.get(name)
        if req is None:
            with self._lock.write():
                self._check_alive()
                req = self._stream_reqs.get(name)  # another poll thread may have set it up
                if req is None:
                    req = self._start_stream(name, unit)
                    if req is not None:
                        self._stream_reqs[name] = req
            if req is None:
                return self._read_pull(name, unit)  # streaming unavailable for this var
        out = req.outData
        if out is None:
            return self._read_pull(name, unit)  # no push yet (warming up) or not delivering
        if isinstance(out, bytes):
            return out.decode("utf-8", "replace").rstrip("\x00")
        return out

    def _read_pull(self, name: str, unit: str) -> object | None:
        """The old on-demand read: predefined canonical-unit list first, then an
        explicit-unit Request. Used as the streaming fallback (warm-up / undelivered);
        it targets the *same* Request object the stream feeds, so the two stay in sync.
        """
        value = self.read_simvar(name)
        if value is None:
            value = self.read_var(name, unit)
        return value

    def _resolve_request(self, name: str, unit: str) -> object | None:
        """The Request a streamed read should feed into.

        Non-indexed predefined vars map to a unique Request, reused directly (the pull
        fallback reads the very same object, so the two stay in sync). Indexed vars are
        the catch: python-simconnect resolves *every* index of ``COM ACTIVE FREQUENCY``
        to one shared Request (``find`` merely re-sets its index), which is fine for the
        pull path — it re-sets the index and re-reads on each call — but wrong for a
        *standing* stream: ``:1`` and ``:2`` would share one request/definition id and
        push into one ``outData``, so both would read the index registered last. Give
        every index its OWN dedicated Request. Returns None if this lib build lacks
        ``Request`` so the caller stays on the pull path.
        """
        indexed = ":" in name and name.rsplit(":", 1)[1].isdigit()
        if not indexed:
            for candidate in (name, name.strip().upper().replace(" ", "_")):
                found = self.requests.find(candidate)
                if found is not None:
                    return found
        if Request is None:
            return None
        if indexed:
            req = self._stream_var_requests.get(name)
            if req is None:
                # Recover the predefined canonical unit so the streamed value matches
                # read_simvar's pull (find() has substituted the concrete index into
                # definitions[0]); fall back to the caller's unit for unknown names.
                deff = (name.encode("ascii"), (unit or "number").encode("ascii"))
                for candidate in (name, name.strip().upper().replace(" ", "_")):
                    found = self.requests.find(candidate)
                    if found is not None:
                        deff = (
                            bytes(found.definitions[0][0]),
                            bytes(found.definitions[0][1]),
                        )
                        break
                req = Request(deff, self.sc, _time=0)
                self._stream_var_requests[name] = req
            return req
        key = (name, unit or "number")
        req = self._var_requests.get(key)
        if req is None:
            deff = (name.encode("ascii"), (unit or "number").encode("ascii"))
            req = Request(deff, self.sc, _time=0)
            self._var_requests[key] = req
        return req

    def _start_stream(self, name: str, unit: str) -> object | None:
        """Register ``name`` as a standing periodic push and return its Request.

        Caller holds the write lock. Defines the data (a quick ``AddToDataDefinition``,
        no spin-wait) and starts a repeating ``RequestDataOnSimObject`` so the sim pushes
        the value onto the dispatch thread from now on. Returns None (caller falls back
        to a pull) if the var can't be defined — an unresolved ``:index`` placeholder or
        a name SimConnect rejects.
        """
        req = self._resolve_request(name, unit)
        if req is None or not req._deff_test():
            return None
        try:
            hr = self.sc.dll.RequestDataOnSimObject(
                self.sc.hSimConnect,
                req.DATA_REQUEST_ID.value,
                req.DATA_DEFINITION_ID.value,
                _SIMOBJECT_ID_USER,
                _STREAM_PERIOD,
                _STREAM_FLAG,
                0, 0, 0,
            )
        except OSError as exc:
            self._mark_lost(exc)  # raises SimDisconnected
        if hr != 0:
            log.error("stream setup failed (0x%08X) for %s [%s]", hr & 0xFFFFFFFF, name, unit)
            return None
        log.info("Streaming SimVar %s [%s] (req %d)", name, unit, req.DATA_REQUEST_ID.value)
        return req

    def read_var(self, name: str, unit: str) -> object | None:
        """Read a SimVar with an explicit unit (e.g. heading in 'degrees').

        Uses a cached ``Request`` so any SimVar name works (not just the
        predefined list) and the unit is honoured. Falls back to the predefined
        ``read_simvar`` path if this build of the library lacks ``Request``.
        """
        with self._lock.read():
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
        with self._lock.read():
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
        with self._lock.write(), contextlib.suppress(Exception):
            self.sc.exit()


class ClientSession:
    """Handles one connected Linux client: read commands, stream state back."""

    def __init__(self, conn: socket.socket, sim: SimConnectBridge) -> None:
        self.conn = conn
        self.sim = sim
        self._subscriptions: dict[str, object] = {}  # name -> last sent value
        self._sub_units: dict[str, str] = {}  # name -> unit (for the read_var fallback)
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
                    self._sub_units[msg["name"]] = msg.get("unit") or "number"
                log.info("Subscribed to %s [%s]", msg["name"], self._sub_units[msg["name"]])
            elif op == "read_now":
                self._read_now(msg["name"], msg.get("unit"))
            elif op == "list_lvars":
                names = self.sim.list_lvars(float(msg.get("timeout", 8.0)))
                self._send({"op": "lvars", "names": names})
                log.info("Enumerated %d LVars", len(names))
            else:
                log.warning("Unknown op: %r", op)
        except SimDisconnected as exc:
            self._on_sim_lost(exc)
        except Exception as exc:
            log.error("Failed to handle %s: %s", op, exc)

    def _read_now(self, name: str, unit: str | None) -> None:
        """Read one subscribed var off the poll cycle and push its value now.

        Fires when the Linux side has just sent a tuning event and wants the
        read-back (e.g. the Radio Panel's tuned frequency) far sooner than the
        1 s poll. Updates the sent-value cache so the next poll won't re-emit the
        same value. The caller (mapper) delays this a few frames after the event
        so the sim has applied it — a stale read here just gets corrected by the
        next poll.
        """
        chosen = unit or self._sub_units.get(name) or "number"
        try:
            value = self.sim.read_subscribed(name, chosen)
        except SimDisconnected as exc:
            self._on_sim_lost(exc)
            return
        if value is None:
            return
        with self._lock:
            self._subscriptions[name] = value
        self._send({"op": "state", "name": name, "value": value})

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
                    value = self.sim.read_subscribed(name, self._sub_units.get(name, "number"))
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
    server.listen(8)  # multi-client: the mapper + monitors/tools subscribe at once
    log.info("Bridge listening on %s:%s", args.host, args.port)

    # One sim handle, shared by every client session and swapped out on a
    # reconnect. All DLL access goes through SimConnectBridge._lock (an RLock), so
    # concurrent sessions are serialized at the sim level — no extra locking here.
    sim_box = {"sim": sim}
    reconnect = threading.Event()

    def handle_client(conn: socket.socket, addr: object) -> None:
        log.info("Linux app connected from %s", addr)
        sim_lost = False
        try:
            sim_lost = ClientSession(conn, sim_box["sim"]).serve()
        except Exception:
            log.exception("Session from %s ended with an error", addr)
        finally:
            with contextlib.suppress(OSError):
                conn.close()
            log.info("Client %s disconnected", addr)
        # A sim CTD/shutdown leaves SimConnect dead — ask the manager to re-attach.
        if sim_lost:
            reconnect.set()

    def reconnect_manager() -> None:
        while True:
            reconnect.wait()
            reconnect.clear()
            try:
                sim_box["sim"]._check_alive()
                continue  # stale signal from an ending session — handle still healthy
            except SimDisconnected:
                pass
            log.warning("Reconnecting to SimConnect (waiting for MSFS)…")
            with contextlib.suppress(Exception):
                sim_box["sim"].close()
            sim_box["sim"] = connect_sim()
            log.info("Reconnected to SimConnect; ready for clients")

    threading.Thread(target=reconnect_manager, name="sim-reconnect", daemon=True).start()

    try:
        while True:
            conn, addr = server.accept()
            threading.Thread(
                target=handle_client, args=(conn, addr), name="client", daemon=True
            ).start()
    except KeyboardInterrupt:
        log.info("Shutting down")
    finally:
        server.close()
        sim_box["sim"].close()


if __name__ == "__main__":
    main()
