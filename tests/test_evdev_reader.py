"""Pure helpers of the evdev reader (no device / no python-evdev needed)."""

from msfs_peripherals_bridge.devices.evdev_reader import key_edges, winning_axis


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


def test_key_edges_counts_presses_not_holds_or_releases():
    last: dict[int, int] = {}
    # press (0->1) counts; autorepeat (1->2) and release (1->0) do not.
    edges = key_edges(last, [(30, 1), (30, 2), (30, 0), (30, 1)])
    assert edges == {30: 2}
    assert last[30] == 1  # ends held -> a later value 1 without a 0 is no new edge


def test_key_edges_accumulates_across_drains_via_last():
    last: dict[int, int] = {}
    assert key_edges(last, [(5, 1), (5, 0)]) == {5: 1}  # first press
    assert key_edges(last, [(5, 1)]) == {5: 1}          # a second, later drain


def test_key_edges_no_edge_when_already_held():
    last = {7: 1}  # held from a previous drain -> value 1 now is not a new press
    assert key_edges(last, [(7, 1), (7, 0)]) == {}


def test_key_edges_winner_is_the_actuated_code():
    from msfs_peripherals_bridge.devices.hidraw_reader import winning_code

    last: dict[int, int] = {}
    counts: dict[int, int] = {}
    # code 12 tapped three times, code 9 brushed once -> 12 wins.
    for events in ([(12, 1), (12, 0)], [(9, 1), (9, 0)], [(12, 1), (12, 0)],
                   [(12, 1), (12, 0)]):
        for code, n in key_edges(last, events).items():
            counts[code] = counts.get(code, 0) + n
    assert counts == {12: 3, 9: 1}
    assert winning_code(counts) == 12
