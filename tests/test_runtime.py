import queue

from msfs_peripherals_bridge.devices.base import DeviceEvent
from msfs_peripherals_bridge.models import SourceKind
from msfs_peripherals_bridge.runtime import (
    _SWITCH_DEBOUNCE_S,
    _bounced,
    _coalesce_axes,
    _drain,
)


def _press(code: int = 7, value: int = 1, device: str = "multi_panel") -> DeviceEvent:
    return DeviceEvent(device_id=device, kind=SourceKind.SWITCH, code=code, value=value)


def _axis(code: int, value: int, device: str = "yoke") -> DeviceEvent:
    return DeviceEvent(device_id=device, kind=SourceKind.AXIS, code=code, value=value)


def _button(code: int = 289, value: int = 1, device: str = "yoke") -> DeviceEvent:
    return DeviceEvent(device_id=device, kind=SourceKind.BUTTON, code=code, value=value)


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


def test_drain_returns_first_plus_everything_buffered():
    q: queue.Queue[DeviceEvent] = queue.Queue()
    a, b, c = _axis(0, 1), _axis(0, 2), _axis(1, 3)
    q.put(b)
    q.put(c)
    assert _drain(q, a) == [a, b, c]
    assert q.empty()  # fully drained


def test_drain_of_a_lone_event_is_just_that_event():
    q: queue.Queue[DeviceEvent] = queue.Queue()
    a = _axis(0, 5)
    assert _drain(q, a) == [a]


def test_coalesce_keeps_only_the_newest_sample_per_axis():
    batch = [_axis(0, 1), _axis(0, 2), _axis(0, 3)]
    assert _coalesce_axes(batch) == [_axis(0, 3)]


def test_coalesce_keeps_axes_independent_by_device_and_code():
    a1, a2 = _axis(0, 1), _axis(0, 2)  # yoke aileron, superseded then latest
    e1 = _axis(1, 7)  # yoke elevator, different code
    rud = _axis(5, 4, device="pedals")  # different device, same-ish code space
    out = _coalesce_axes([a1, e1, a2, rud])
    # a1 dropped (superseded by a2); the surviving latest of each axis, in order.
    assert out == [e1, a2, rud]


def test_coalesce_never_drops_buttons_or_switches():
    btn = _button(code=289)
    sw = _press(code=7)
    batch = [_axis(0, 1), btn, _axis(0, 2), sw, _axis(0, 3)]
    # Every non-axis edge survives, in order; only the latest axis sample remains.
    assert _coalesce_axes(batch) == [btn, sw, _axis(0, 3)]


def test_coalesce_preserves_a_button_pressed_after_the_last_axis_move():
    # Order matters: a press that lands after the final axis sample must stay after
    # it, so a "move then click" isn't reordered into "click then move".
    batch = [_axis(0, 1), _axis(0, 2), _button(code=290)]
    assert _coalesce_axes(batch) == [_axis(0, 2), _button(code=290)]


def test_condition_vars_collects_all_when_vars():
    from msfs_peripherals_bridge.models import Binding, Condition, EventAction, Profile, Source
    from msfs_peripherals_bridge.runtime import ConditionWatcher, condition_vars

    prof = Profile(
        name="t",
        bindings={
            "yoke": [
                Binding(
                    name="a",
                    source=Source(kind="button", code=1),
                    action=EventAction(event="X", value=1),
                    when=[Condition(var="AVIONICS MASTER SWITCH")],
                ),
                Binding(
                    name="b",
                    source=Source(kind="button", code=2),
                    action=EventAction(event="Y", value=1),
                    when=[Condition(var="L:MODE"), Condition(var="AVIONICS MASTER SWITCH")],
                ),
            ]
        },
    )
    assert condition_vars(prof) == {"AVIONICS MASTER SWITCH", "L:MODE"}

    w = ConditionWatcher()
    assert w.get("L:MODE") is None  # unknown until the stream delivers
    w.update("L:MODE", 2)
    assert w.get("L:MODE") == 2


def test_seed_local_vars_builds_setsimvar_commands():
    from msfs_peripherals_bridge.models import Profile
    from msfs_peripherals_bridge.runtime import seed_local_vars
    from msfs_peripherals_bridge.simconnect.protocol import SetSimVar

    prof = Profile.model_validate(
        {
            "name": "t",
            "bindings": {},
            "local_vars": [{"name": "mode", "initial": 2}, {"name": "latch", "unit": "bool"}],
        }
    )
    cmds = seed_local_vars(prof)
    assert cmds == [
        SetSimVar(name="V:mode", unit="number", value=2.0),
        SetSimVar(name="V:latch", unit="bool", value=0.0),
    ]
    assert seed_local_vars(Profile(name="x", bindings={})) == []
