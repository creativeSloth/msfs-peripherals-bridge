"""Device-agnostic event type shared by readers and the mapping engine."""

from __future__ import annotations

from dataclasses import dataclass

from ..models import SourceKind


@dataclass(frozen=True, slots=True)
class DeviceEvent:
    """One normalised input event from a physical device.

    ``device_id`` is the catalog key (e.g. 'tq6'), not the OS device path,
    so the mapping engine stays independent of how the device was opened.
    """

    device_id: str
    kind: SourceKind
    code: int
    value: int
