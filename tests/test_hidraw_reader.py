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


# --- count_rising_edges: transient-pulse capture for encoders ---------------

def _edges(frames):
    from msfs_peripherals_bridge.devices.hidraw_reader import count_rising_edges
    return count_rising_edges(frames)


def test_rising_edges_first_frame_only_primes():
    # a single frame yields no edges (baseline only)
    assert _edges([b"\x01\x00\x00"]) == {}


def test_rising_edges_counts_transient_pulses():
    # bit 0 pulses 1->0->1->0 : two rising edges, even though it ends at rest.
    # This is the encoder case the state view loses (nets back to 0).
    frames = [b"\x00\x00\x00", b"\x01\x00\x00", b"\x00\x00\x00",
              b"\x01\x00\x00", b"\x00\x00\x00"]
    assert _edges(frames) == {0: 2}


def test_rising_edges_only_rising_not_falling():
    # bit 3 goes up then down -> exactly one rising edge counted
    assert _edges([b"\x00\x00\x00", b"\x08\x00\x00", b"\x00\x00\x00"]) == {3: 1}


def test_rising_edges_winner_is_the_turned_bit():
    # code 9 (byte1.bit1) pulsed 3x, code 0 once -> 9 is the clear winner
    frames = [b"\x00\x00\x00"]
    for _ in range(3):
        frames += [b"\x00\x02\x00", b"\x00\x00\x00"]
    frames += [b"\x01\x00\x00", b"\x00\x00\x00"]
    counts = _edges(frames)
    assert counts == {9: 3, 0: 1}
    assert max(counts, key=counts.get) == 9
