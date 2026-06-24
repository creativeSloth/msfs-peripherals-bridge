from msfs_peripherals_bridge.devices.base import DeviceEvent
from msfs_peripherals_bridge.mapping.engine import MappingEngine
from msfs_peripherals_bridge.models import (
    Binding,
    EventAction,
    EventFromVarAction,
    Profile,
    SimVarAction,
    Source,
    SourceKind,
    Transform,
)
from msfs_peripherals_bridge.simconnect.protocol import (
    SendEvent,
    SendEventFromVar,
    SetSimVar,
)


def _axis_profile() -> Profile:
    return Profile(
        name="t",
        bindings={
            "tq6": [
                Binding(
                    name="Throttle",
                    source=Source(kind=SourceKind.AXIS, code=0, raw_min=0, raw_max=1023),
                    action=EventAction(event="THROTTLE1_SET"),
                    transform=Transform(out_min=-16383, out_max=16383),
                )
            ]
        },
    )


def test_axis_event_uses_shaped_value_as_data():
    engine = MappingEngine(_axis_profile())
    cmds = engine.resolve(DeviceEvent("tq6", SourceKind.AXIS, code=0, value=1023))
    assert cmds == [SendEvent(name="THROTTLE1_SET", data=16383)]


def test_unmatched_code_yields_nothing():
    engine = MappingEngine(_axis_profile())
    assert engine.resolve(DeviceEvent("tq6", SourceKind.AXIS, code=9, value=1)) == []


def test_unknown_device_yields_nothing():
    engine = MappingEngine(_axis_profile())
    assert engine.resolve(DeviceEvent("other", SourceKind.AXIS, code=0, value=1023)) == []


def test_button_press_sends_fixed_value_and_release_is_ignored():
    profile = Profile(
        name="t",
        bindings={
            "trim": [
                Binding(
                    name="AP",
                    source=Source(kind=SourceKind.BUTTON, code=288),
                    action=EventAction(event="AUTOPILOT_ON", value=1),
                )
            ]
        },
    )
    engine = MappingEngine(profile)
    assert engine.resolve(DeviceEvent("trim", SourceKind.BUTTON, 288, 1)) == [
        SendEvent(name="AUTOPILOT_ON", data=1)
    ]
    assert engine.resolve(DeviceEvent("trim", SourceKind.BUTTON, 288, 0)) == []
    # Kernel key autorepeat (value 2) must not re-fire while the button is held.
    assert engine.resolve(DeviceEvent("trim", SourceKind.BUTTON, 288, 2)) == []


def test_simvar_action_emits_setsimvar():
    profile = Profile(
        name="t",
        bindings={
            "trim": [
                Binding(
                    name="Custom trim",
                    source=Source(kind=SourceKind.AXIS, code=7, raw_min=0, raw_max=100),
                    action=SimVarAction(simvar="L:Trim", unit="number"),
                    transform=Transform(out_min=0, out_max=1),
                )
            ]
        },
    )
    engine = MappingEngine(profile)
    cmds = engine.resolve(DeviceEvent("trim", SourceKind.AXIS, 7, 100))
    assert cmds == [SetSimVar(name="L:Trim", unit="number", value=1.0)]


def _switch_binding(action) -> Profile:
    return Profile(
        name="t",
        bindings={
            "switch_panel": [
                Binding(name="s", source=Source(kind=SourceKind.SWITCH, code=9), action=action)
            ]
        },
    )


def test_stateful_switch_forwards_on_and_off_state():
    # A switch with no fixed value drives a *_SET event with its live 0/1 state.
    engine = MappingEngine(_switch_binding(EventAction(event="NAV_LIGHTS_SET")))
    assert engine.resolve(DeviceEvent("switch_panel", SourceKind.SWITCH, 9, 1)) == [
        SendEvent(name="NAV_LIGHTS_SET", data=1)
    ]
    assert engine.resolve(DeviceEvent("switch_panel", SourceKind.SWITCH, 9, 0)) == [
        SendEvent(name="NAV_LIGHTS_SET", data=0)
    ]


def test_momentary_switch_fires_only_on_enter_edge():
    # A fixed value makes the switch momentary (rotary detent / gear lever).
    engine = MappingEngine(_switch_binding(EventAction(event="GEAR_UP", value=1)))
    assert engine.resolve(DeviceEvent("switch_panel", SourceKind.SWITCH, 9, 1)) == [
        SendEvent(name="GEAR_UP", data=1)
    ]
    assert engine.resolve(DeviceEvent("switch_panel", SourceKind.SWITCH, 9, 0)) == []


def test_stateful_switch_simvar_sets_both_edges():
    engine = MappingEngine(_switch_binding(SimVarAction(simvar="L:Foo", unit="number")))
    assert engine.resolve(DeviceEvent("switch_panel", SourceKind.SWITCH, 9, 1)) == [
        SetSimVar(name="L:Foo", unit="number", value=1.0)
    ]
    assert engine.resolve(DeviceEvent("switch_panel", SourceKind.SWITCH, 9, 0)) == [
        SetSimVar(name="L:Foo", unit="number", value=0.0)
    ]


def test_event_from_var_button_emits_sendeventfromvar_on_press_only():
    profile = Profile(
        name="t",
        bindings={
            "yoke": [
                Binding(
                    name="Heading bug = current heading",
                    source=Source(kind=SourceKind.BUTTON, code=290),
                    action=EventFromVarAction(
                        read="PLANE HEADING DEGREES MAGNETIC",
                        unit="degrees",
                        event="HEADING_BUG_SET",
                    ),
                )
            ]
        },
    )
    engine = MappingEngine(profile)
    assert engine.resolve(DeviceEvent("yoke", SourceKind.BUTTON, 290, 1)) == [
        SendEventFromVar(
            event="HEADING_BUG_SET", read="PLANE HEADING DEGREES MAGNETIC", unit="degrees"
        )
    ]
    # Release / autorepeat must not re-fire the sync.
    assert engine.resolve(DeviceEvent("yoke", SourceKind.BUTTON, 290, 0)) == []
    assert engine.resolve(DeviceEvent("yoke", SourceKind.BUTTON, 290, 2)) == []
