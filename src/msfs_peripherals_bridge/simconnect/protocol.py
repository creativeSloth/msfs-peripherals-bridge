"""Wire protocol between the Linux app and the Wine-side SimConnect bridge.

The bridge speaks newline-delimited JSON over a TCP socket (default
127.0.0.1:7842). This keeps the Windows/Wine side as small as possible:
it only has to translate these messages into SimConnect SDK calls.

Linux -> bridge:
    {"op": "event",  "name": "THROTTLE1_SET", "data": 8192}
    {"op": "simvar", "name": "L:Trim", "unit": "number", "value": 0.5}
    {"op": "subscribe", "name": "TITLE", "unit": "string"}

bridge -> Linux:
    {"op": "state", "name": "TITLE", "value": "Cessna 172"}
    {"op": "hello", "sim": "MSFS", "version": "..."}
"""

from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SendEvent:
    """Trigger a SimConnect client event (K:/H: event)."""

    name: str
    data: int = 0

    def to_wire(self) -> dict[str, object]:
        return {"op": "event", "name": self.name, "data": self.data}


@dataclass(frozen=True, slots=True)
class SetSimVar:
    """Set a SimVar (routed through the MobiFlight WASM channel)."""

    name: str
    unit: str
    value: float

    def to_wire(self) -> dict[str, object]:
        return {"op": "simvar", "name": self.name, "unit": self.unit, "value": self.value}


@dataclass(frozen=True, slots=True)
class Subscribe:
    """Request continuous updates for a SimVar (e.g. TITLE for auto-profile)."""

    name: str
    unit: str = "number"

    def to_wire(self) -> dict[str, object]:
        return {"op": "subscribe", "name": self.name, "unit": self.unit}


Command = SendEvent | SetSimVar | Subscribe


def encode(command: Command) -> bytes:
    """Serialise a command to a newline-terminated JSON frame."""
    return (json.dumps(command.to_wire()) + "\n").encode("utf-8")


def decode_state(line: str) -> tuple[str, object] | None:
    """Parse a 'state' frame from the bridge into (name, value)."""
    try:
        msg = json.loads(line)
    except json.JSONDecodeError:
        return None
    if msg.get("op") != "state":
        return None
    return str(msg["name"]), msg["value"]
