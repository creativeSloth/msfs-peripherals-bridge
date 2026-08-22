"""Linux-side client that talks to the Wine SimConnect bridge over TCP."""

from __future__ import annotations

import contextlib
import logging
import socket
import threading
from collections.abc import Iterator

from .protocol import Command, Subscribe, decode_state, encode

log = logging.getLogger(__name__)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7842


class BridgeClient:
    """Thin, blocking TCP client for the SimConnect bridge.

    With ``reconnect=True`` it self-heals: if the bridge process drops the
    session (its Wine-side supervisor relaunches it after an MSFS CTD, or the
    SimConnect link faulted and the session ended), both :meth:`send` and
    :meth:`states` transparently redial it and replay the output subscriptions.
    The mapper keeps running across a bridge restart instead of dying and having
    to be started by hand.

    Designed to be swapped for a no-op in tests and dry runs via the
    ``Dispatcher`` protocol below.
    """

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        *,
        reconnect: bool = False,
        retry_delay: float = 2.0,
    ) -> None:
        self.host = host
        self.port = port
        self._reconnect = reconnect
        self._retry_delay = retry_delay
        self._sock: socket.socket | None = None
        # Mapping commands and output subscriptions are sent from different
        # threads on this one socket; serialise sends so frames don't interleave.
        self._send_lock = threading.Lock()
        # Only one thread may (re)dial at a time; the others wait on it and then
        # see the bumped generation and reuse the fresh socket.
        self._dial_lock = threading.Lock()
        # Guards _sock / _generation / _subscriptions / _closed.
        self._conn_lock = threading.Lock()
        # Bumped on every successful (re)connect so a thread that saw the socket
        # break can tell whether someone else already reconnected.
        self._generation = 0
        # Output subscriptions, replayed after every reconnect (the restarted
        # bridge is a fresh process that has forgotten them).
        self._subscriptions: dict[str, Subscribe] = {}
        self._closed = False
        # Lets close() cut short a retry-loop sleep for a prompt shutdown.
        self._wake = threading.Event()

    # -- connection management ---------------------------------------------
    def connect(self) -> None:
        """Open the connection. With ``reconnect`` set, wait for the bridge."""
        with self._conn_lock:
            self._closed = False
            self._wake.clear()
            gen = self._generation
        if self._reconnect:
            self._dial_forever(gen)
        else:
            self._dial_once()

    def _dial_once(self) -> None:
        sock = socket.create_connection((self.host, self.port), timeout=5.0)
        # The 5 s timeout was only for dialling; streaming reads should block.
        sock.settimeout(None)
        with self._conn_lock:
            self._sock = sock
            self._generation += 1
        log.info("Connected to SimConnect bridge at %s:%s", self.host, self.port)

    def _dial_forever(self, failed_generation: int) -> bool:
        """Redial until it works (or the client is closed), then replay subs.

        ``failed_generation`` is the connection generation the caller was using
        when it broke. Returns ``True`` once a live socket is in place — either
        because we reconnected, or because another thread already did (the
        generation moved past ``failed_generation``). Returns ``False`` only if
        the client was closed meanwhile.
        """
        with self._dial_lock:
            with self._conn_lock:
                if self._closed:
                    return False
                if self._generation != failed_generation:
                    return True  # someone else reconnected while we waited
                old, self._sock = self._sock, None
            _close(old)
            attempt = 0
            while True:
                with self._conn_lock:
                    if self._closed:
                        return False
                try:
                    sock = socket.create_connection((self.host, self.port), timeout=5.0)
                    sock.settimeout(None)
                except OSError as exc:
                    attempt += 1
                    if attempt == 1 or attempt % 15 == 0:
                        log.warning(
                            "Bridge unreachable at %s:%s (%s); retrying every %.0fs…",
                            self.host,
                            self.port,
                            exc,
                            self._retry_delay,
                        )
                    if self._wake.wait(self._retry_delay):
                        return False  # close() woke us
                    continue
                with self._conn_lock:
                    if self._closed:
                        sock.close()
                        return False
                    self._sock = sock
                    self._generation += 1
                    gen = self._generation
                    subs = list(self._subscriptions.values())
                self._replay(sock, subs)
                log.info(
                    "Connected to SimConnect bridge at %s:%s (resubscribed %d, gen %d)",
                    self.host,
                    self.port,
                    len(subs),
                    gen,
                )
                return True

    def _replay(self, sock: socket.socket, subs: list[Subscribe]) -> None:
        """Re-send remembered subscriptions on a freshly dialled socket."""
        for sub in subs:
            try:
                with self._send_lock:
                    sock.sendall(encode(sub))
            except OSError:
                return  # broke again; the next send/recv will trigger a redial

    def settimeout(self, timeout: float | None) -> None:
        """Bound subsequent ``states()`` reads (None = block forever)."""
        with self._conn_lock:
            sock = self._sock
        if sock is None:
            raise RuntimeError("BridgeClient is not connected")
        sock.settimeout(timeout)

    def send(self, command: Command) -> None:
        if isinstance(command, Subscribe):
            with self._conn_lock:
                self._subscriptions[command.name] = command
        data = encode(command)
        while True:
            with self._conn_lock:
                sock, gen = self._sock, self._generation
            if sock is None:
                if not self._reconnect:
                    raise RuntimeError("BridgeClient is not connected")
                if not self._dial_forever(gen):
                    return  # closed
                continue
            try:
                with self._send_lock:
                    sock.sendall(data)
                return
            except OSError as exc:
                if not self._reconnect:
                    raise
                log.warning("Bridge send failed (%s); reconnecting…", exc)
                if not self._dial_forever(gen):
                    return  # closed

    def states(self) -> Iterator[tuple[str, object]]:
        """Yield (name, value) updates streamed back from the bridge.

        With ``reconnect`` set, a dropped stream is redialled (and subscriptions
        replayed) instead of ending the iterator, so output rendering survives a
        bridge restart. A configured read timeout still surfaces as
        ``TimeoutError`` for the one-shot ``read`` command.
        """
        buffer = b""
        while True:
            with self._conn_lock:
                sock, gen = self._sock, self._generation
            if sock is None:
                if not self._reconnect:
                    raise RuntimeError("BridgeClient is not connected")
                if not self._dial_forever(gen):
                    return
                buffer = b""
                continue
            try:
                chunk = sock.recv(4096)
            except TimeoutError:
                raise
            except OSError as exc:
                if not self._reconnect:
                    raise
                log.warning("Bridge stream error (%s); reconnecting…", exc)
                if not self._dial_forever(gen):
                    return
                buffer = b""
                continue
            if not chunk:
                if not self._reconnect:
                    return
                log.warning("Bridge closed the stream; reconnecting…")
                if not self._dial_forever(gen):
                    return
                buffer = b""
                continue
            buffer += chunk
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                parsed = decode_state(line.decode("utf-8"))
                if parsed is not None:
                    yield parsed

    def close(self) -> None:
        with self._conn_lock:
            self._closed = True
            sock, self._sock = self._sock, None
        self._wake.set()  # cut short any retry-loop sleep
        _close(sock)

    def __enter__(self) -> BridgeClient:
        self.connect()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def _close(sock: socket.socket | None) -> None:
    """Best-effort shutdown+close; unblocks a peer parked in recv."""
    if sock is None:
        return
    with contextlib.suppress(OSError):
        sock.shutdown(socket.SHUT_RDWR)
    with contextlib.suppress(OSError):
        sock.close()


class DryRunDispatcher:
    """Logs commands instead of sending them. Used by ``--dry-run``."""

    def __init__(self) -> None:
        self.sent: list[Command] = []

    def connect(self) -> None:  # pragma: no cover - trivial
        log.info("[dry-run] bridge connection skipped")

    def send(self, command: Command) -> None:
        self.sent.append(command)
        log.info("[dry-run] %s", command)

    def close(self) -> None:  # pragma: no cover - trivial
        pass
