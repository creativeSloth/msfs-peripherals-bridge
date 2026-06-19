"""Linux-side client that talks to the Wine SimConnect bridge over TCP."""

from __future__ import annotations

import logging
import socket
from collections.abc import Iterator

from .protocol import Command, decode_state, encode

log = logging.getLogger(__name__)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7842


class BridgeClient:
    """Thin, blocking TCP client for the SimConnect bridge.

    Designed to be swapped for a no-op in tests and dry runs via the
    ``Dispatcher`` protocol below.
    """

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
        self.host = host
        self.port = port
        self._sock: socket.socket | None = None

    def connect(self) -> None:
        self._sock = socket.create_connection((self.host, self.port), timeout=5.0)
        log.info("Connected to SimConnect bridge at %s:%s", self.host, self.port)

    def send(self, command: Command) -> None:
        if self._sock is None:
            raise RuntimeError("BridgeClient is not connected")
        self._sock.sendall(encode(command))

    def states(self) -> Iterator[tuple[str, object]]:
        """Yield (name, value) updates streamed back from the bridge."""
        if self._sock is None:
            raise RuntimeError("BridgeClient is not connected")
        buffer = b""
        while True:
            chunk = self._sock.recv(4096)
            if not chunk:
                return
            buffer += chunk
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                parsed = decode_state(line.decode("utf-8"))
                if parsed is not None:
                    yield parsed

    def close(self) -> None:
        if self._sock is not None:
            self._sock.close()
            self._sock = None

    def __enter__(self) -> BridgeClient:
        self.connect()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


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
