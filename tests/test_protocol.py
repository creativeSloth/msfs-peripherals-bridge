"""Wire-format guarantees the Wine bridge (bridge/bridge.py) depends on."""

from __future__ import annotations

import json

from msfs_peripherals_bridge.simconnect.protocol import (
    SendEvent,
    SendEventFromVar,
    SetSimVar,
    Subscribe,
    encode,
)


def _wire(command) -> dict:
    line = encode(command)
    assert line.endswith(b"\n")
    return json.loads(line)


def test_event_frame():
    assert _wire(SendEvent("THROTTLE1_SET", 8192)) == {
        "op": "event",
        "name": "THROTTLE1_SET",
        "data": 8192,
    }


def test_simvar_frame():
    assert _wire(SetSimVar("L:Trim", "number", 0.5)) == {
        "op": "simvar",
        "name": "L:Trim",
        "unit": "number",
        "value": 0.5,
    }


def test_subscribe_frame():
    assert _wire(Subscribe("TITLE", "string")) == {
        "op": "subscribe",
        "name": "TITLE",
        "unit": "string",
    }


def test_event_from_var_frame_matches_bridge_keys():
    # bridge.py reads msg["event"], msg["read"], msg.get("unit") under this op.
    assert _wire(
        SendEventFromVar(
            event="HEADING_BUG_SET", read="PLANE HEADING DEGREES MAGNETIC", unit="degrees"
        )
    ) == {
        "op": "event_from_var",
        "event": "HEADING_BUG_SET",
        "read": "PLANE HEADING DEGREES MAGNETIC",
        "unit": "degrees",
    }
