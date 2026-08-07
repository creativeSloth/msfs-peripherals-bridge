"""Pure helpers of the evdev reader (no device / no python-evdev needed)."""

from msfs_peripherals_bridge.devices.evdev_reader import winning_axis


def test_winning_axis_picks_widest_span():
    # axis 5 travelled 0..1023, axis 0 barely twitched -> 5 wins.
    spans = {0: (500, 507), 5: (0, 1023)}
    assert winning_axis(spans) == 5


def test_winning_axis_none_when_nothing_moved():
    assert winning_axis({}) is None
    # idle jitter below the threshold is not a capture.
    assert winning_axis({3: (128, 130)}) is None


def test_winning_axis_filters_a_hat_by_span_threshold():
    # a hat reports as ABS too, but only spans -1..1 (=2) -> filtered out; the real
    # axis with a wide span wins.
    spans = {16: (-1, 1), 2: (0, 255)}
    assert winning_axis(spans) == 2


def test_winning_axis_respects_custom_min_span():
    assert winning_axis({1: (0, 10)}, min_span=20) is None
    assert winning_axis({1: (0, 30)}, min_span=20) == 1
