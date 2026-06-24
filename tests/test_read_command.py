"""The `read` command against a fake bridge speaking the wire protocol."""

from __future__ import annotations

import json
import socket
import threading

from typer.testing import CliRunner

from msfs_peripherals_bridge.cli import app

runner = CliRunner()


def _fake_bridge(state_frames: list[dict[str, object]]) -> tuple[int, threading.Thread]:
    """A one-shot TCP server: greets, echoes subscriptions, then sends frames."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]

    def serve() -> None:
        conn, _ = server.accept()
        with conn:
            conn.sendall(b'{"op":"hello","sim":"MSFS","version":"fake"}\n')
            # Wait for the subscribe frame so the read is realistic.
            conn.recv(4096)
            for frame in state_frames:
                conn.sendall((json.dumps(frame) + "\n").encode("utf-8"))
        server.close()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    return port, thread


def test_read_one_shot_prints_first_matching_value() -> None:
    port, thread = _fake_bridge(
        [{"op": "state", "name": "AUTOPILOT HEADING LOCK DIR", "value": 270}]
    )
    result = runner.invoke(
        app,
        ["read", "AUTOPILOT HEADING LOCK DIR", "--unit", "degrees", "--port", str(port)],
    )
    thread.join(timeout=2)
    assert result.exit_code == 0, result.output
    assert "AUTOPILOT HEADING LOCK DIR = 270 degrees" in result.output


def test_read_ignores_other_state_names() -> None:
    port, thread = _fake_bridge(
        [
            {"op": "state", "name": "TITLE", "value": "Piper Arrow"},
            {"op": "state", "name": "AUTOPILOT HEADING LOCK DIR", "value": 90},
        ]
    )
    result = runner.invoke(app, ["read", "AUTOPILOT HEADING LOCK DIR", "--port", str(port)])
    thread.join(timeout=2)
    assert result.exit_code == 0, result.output
    assert "= 90" in result.output
    assert "Piper Arrow" not in result.output


def test_read_unreachable_bridge_errors_cleanly() -> None:
    # Port 1 is privileged and unused on a normal machine -> connection refused.
    result = runner.invoke(app, ["read", "TITLE", "--port", "1", "--timeout", "1"])
    assert result.exit_code == 1
    assert "Cannot reach the bridge" in result.output
