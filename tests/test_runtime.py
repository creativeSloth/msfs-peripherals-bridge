from msfs_peripherals_bridge.devices.base import DeviceEvent
from msfs_peripherals_bridge.models import SourceKind
from msfs_peripherals_bridge.runtime import _SWITCH_DEBOUNCE_S, _bounced


def _press(code: int = 7, value: int = 1, device: str = "multi_panel") -> DeviceEvent:
    return DeviceEvent(device_id=device, kind=SourceKind.SWITCH, code=code, value=value)


def test_first_press_is_never_bounced():
    assert _bounced(_press(), {}, now=100.0) is False


def test_bounce_burst_collapses_to_one_press():
    # A dirty press: several enter edges whose gaps stay under the window. Only
    # the first fires; the retriggerable window keeps swallowing the rest even
    # though the burst spans longer than the window overall.
    last: dict[tuple[str, int], float] = {}
    w = _SWITCH_DEBOUNCE_S
    assert _bounced(_press(), last, now=0.0) is False  # accepted
    assert _bounced(_press(), last, now=w * 0.5) is True  # bounce, suppressed
    assert _bounced(_press(), last, now=w * 1.2) is True  # still <window since last edge
    assert _bounced(_press(), last, now=w * 1.9) is True


def test_deliberate_repress_after_window_passes():
    last: dict[tuple[str, int], float] = {}
    assert _bounced(_press(), last, now=0.0) is False
    # A real second press, well after the window, must register.
    assert _bounced(_press(), last, now=_SWITCH_DEBOUNCE_S * 3) is False


def test_release_and_non_switch_edges_pass_through():
    last: dict[tuple[str, int], float] = {}
    # Release edge (value 0) is never rate-limited...
    assert _bounced(_press(value=0), last, now=0.0) is False
    # ...and does not seed the debounce, so the following press is accepted.
    assert _bounced(_press(value=1), last, now=0.001) is False
    # A non-switch input (button) bypasses the switch debounce entirely.
    btn = DeviceEvent(device_id="yoke", kind=SourceKind.BUTTON, code=289, value=1)
    assert _bounced(btn, last, now=0.002) is False


def test_distinct_buttons_are_debounced_independently():
    last: dict[tuple[str, int], float] = {}
    assert _bounced(_press(code=8), last, now=0.0) is False
    # A different button pressed right after is its own key -> not suppressed.
    assert _bounced(_press(code=13), last, now=0.01) is False
