"""The self-healing BridgeClient survives a bridge restart (reconnect=True)."""

from __future__ import annotations

import json
import socket
import threading
import time

from msfs_peripherals_bridge.simconnect.client import BridgeClient
from msfs_peripherals_bridge.simconnect.protocol import SendEvent, Subscribe


def _recv_line(conn: socket.socket) -> bytes:
    buf = b""
    while b"\n" not in buf:
        chunk = conn.recv(4096)
        if not chunk:
            return buf
        buf += chunk
    return buf.split(b"\n", 1)[0]


def test_client_reconnects_and_replays_subscriptions() -> None:
    # One persistent listener stands in for the bridge whose supervisor keeps the
    # port up across a restart: the session (conn1) drops, a fresh one (conn2)
    # is accepted on the same port.
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]

    client = BridgeClient("127.0.0.1", port, reconnect=True, retry_delay=0.05)
    client.connect()
    conn1, _ = listener.accept()

    client.send(Subscribe("TITLE"))
    assert json.loads(_recv_line(conn1))["name"] == "TITLE"

    got: list[tuple[str, object]] = []
    streamer = threading.Thread(target=lambda: got.extend(client.states()), daemon=True)
    streamer.start()

    conn1.sendall(b'{"op":"state","name":"TITLE","value":"A"}\n')
    conn1.close()  # drop the session -> client must redial, not give up

    conn2, _ = listener.accept()  # the client reconnected on its own
    # Subscriptions are replayed on the fresh socket (the restarted bridge forgot them).
    assert json.loads(_recv_line(conn2))["name"] == "TITLE"
    conn2.sendall(b'{"op":"state","name":"TITLE","value":"B"}\n')

    time.sleep(0.2)
    client.close()
    streamer.join(timeout=2)
    conn2.close()
    listener.close()

    assert ("TITLE", "A") in got  # before the drop
    assert ("TITLE", "B") in got  # after the automatic reconnect


def test_send_dials_when_not_connected() -> None:
    # With reconnect set, a send before/without a live socket must dial the bridge
    # itself (and keep retrying) rather than raise — so a command issued while the
    # bridge is mid-restart is delivered once it returns, not dropped on the floor.
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]

    client = BridgeClient("127.0.0.1", port, reconnect=True, retry_delay=0.05)
    # Deliberately do NOT connect() first: _sock is None.
    sender = threading.Thread(
        target=lambda: client.send(SendEvent("THROTTLE1_SET", 5)), daemon=True
    )
    sender.start()
    conn, _ = listener.accept()  # send() dialled on its own
    assert json.loads(_recv_line(conn))["name"] == "THROTTLE1_SET"

    sender.join(timeout=2)
    client.close()
    conn.close()
    listener.close()
