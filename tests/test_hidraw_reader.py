from msfs_peripherals_bridge.devices.base import DeviceEvent
from msfs_peripherals_bridge.devices.hidraw_reader import iter_bit_changes
from msfs_peripherals_bridge.models import SourceKind


def _changes(prev: bytes, cur: bytes) -> list[DeviceEvent]:
    return list(iter_bit_changes("switch_panel", prev, cur))


def test_single_bit_set_emits_one_switch_event():
    assert _changes(b"\x00\x00\x00", b"\x01\x00\x00") == [
        DeviceEvent("switch_panel", SourceKind.SWITCH, code=0, value=1)
    ]


def test_global_bit_index_spans_bytes():
    # byte1.bit1 -> code 9 ; byte2.bit2 -> code 18
    assert _changes(b"\x00\x00\x00", b"\x00\x02\x00") == [
        DeviceEvent("switch_panel", SourceKind.SWITCH, code=9, value=1)
    ]
    assert _changes(b"\x00\x00\x00", b"\x00\x00\x04") == [
        DeviceEvent("switch_panel", SourceKind.SWITCH, code=18, value=1)
    ]


def test_cleared_bit_reports_zero():
    assert _changes(b"\x01\x20\x08", b"\x00\x20\x08") == [
        DeviceEvent("switch_panel", SourceKind.SWITCH, code=0, value=0)
    ]


def test_identical_reports_emit_nothing():
    assert _changes(b"\x00\x20\x08", b"\x00\x20\x08") == []


def test_rotary_detent_move_clears_old_and_sets_new():
    # MAG OFF (byte1.bit5=code 13) -> MAG R (byte1.bit6=code 14)
    assert _changes(b"\x00\x20\x08", b"\x00\x40\x08") == [
        DeviceEvent("switch_panel", SourceKind.SWITCH, code=13, value=0),
        DeviceEvent("switch_panel", SourceKind.SWITCH, code=14, value=1),
    ]
