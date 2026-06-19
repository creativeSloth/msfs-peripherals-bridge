from msfs_peripherals_bridge.devices.base import DeviceEvent
from msfs_peripherals_bridge.mapping.engine import MappingEngine
from msfs_peripherals_bridge.models import (
    Binding,
    EventAction,
    Profile,
    SimVarAction,
    Source,
    SourceKind,
    Transform,
)
from msfs_peripherals_bridge.simconnect.protocol import SendEvent, SetSimVar


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
