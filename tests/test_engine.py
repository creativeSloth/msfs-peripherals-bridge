import pytest
from pydantic import ValidationError

from msfs_peripherals_bridge.devices.base import DeviceEvent
from msfs_peripherals_bridge.mapping.engine import MappingEngine
from msfs_peripherals_bridge.models import (
    Binding,
    EventAction,
    EventFromVarAction,
    Profile,
    RpnAction,
    SequenceAction,
    SimVarAction,
    Source,
    SourceKind,
    Transform,
    WriteStep,
)
from msfs_peripherals_bridge.simconnect.protocol import (
    RpnExec,
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


def test_rpn_action_is_momentary_toggle():
    # An RPN action (e.g. an LVar NOT toggle) fires once on the press edge only —
    # firing on both edges would toggle twice and net out to nothing.
    rpn = "(L:JF_PA28_AP_alt) ! (>L:JF_PA28_AP_alt)"
    engine = MappingEngine(_switch_binding(RpnAction(code=rpn)))
    assert engine.resolve(DeviceEvent("switch_panel", SourceKind.SWITCH, 9, 1)) == [
        RpnExec(code=rpn)
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


def test_stateful_switch_simvar_invert_swaps_polarity():
    engine = MappingEngine(_switch_binding(SimVarAction(simvar="L:Pump", invert=True)))
    assert engine.resolve(DeviceEvent("switch_panel", SourceKind.SWITCH, 9, 1)) == [
        SetSimVar(name="L:Pump", unit="number", value=0.0)
    ]
    assert engine.resolve(DeviceEvent("switch_panel", SourceKind.SWITCH, 9, 0)) == [
        SetSimVar(name="L:Pump", unit="number", value=1.0)
    ]


def test_sequence_switch_runs_on_and_off_lists():
    # Heading-hold engage: two LVar writes on the arm edge, one on the off edge.
    action = SequenceAction(
        on_edge=[
            WriteStep(simvar="L:AUTOPILOT_MODE", value=2),
            WriteStep(simvar="L:AUTOPILOT_HDG", value=1),
        ],
        off_edge=[WriteStep(simvar="L:AUTOPILOT_HDG", value=0)],
    )
    engine = MappingEngine(_switch_binding(action))
    assert engine.resolve(DeviceEvent("switch_panel", SourceKind.SWITCH, 9, 1)) == [
        SetSimVar(name="L:AUTOPILOT_MODE", unit="number", value=2),
        SetSimVar(name="L:AUTOPILOT_HDG", unit="number", value=1),
    ]
    assert engine.resolve(DeviceEvent("switch_panel", SourceKind.SWITCH, 9, 0)) == [
        SetSimVar(name="L:AUTOPILOT_HDG", unit="number", value=0),
    ]


def test_sequence_mixes_events_and_simvars():
    action = SequenceAction(
        on_edge=[
            WriteStep(event="AVIONICS_MASTER_SET", value=1),
            WriteStep(simvar="L:KN62_POWER", value=1),
            WriteStep(event="COM1_VOLUME_SET", value=100),
        ],
    )
    engine = MappingEngine(_switch_binding(action))
    assert engine.resolve(DeviceEvent("switch_panel", SourceKind.SWITCH, 9, 1)) == [
        SendEvent(name="AVIONICS_MASTER_SET", data=1),
        SetSimVar(name="L:KN62_POWER", unit="number", value=1),
        SendEvent(name="COM1_VOLUME_SET", data=100),
    ]
    # Default (empty) off list -> nothing on the off edge.
    assert engine.resolve(DeviceEvent("switch_panel", SourceKind.SWITCH, 9, 0)) == []


def test_sequence_on_momentary_button_press_only():
    action = SequenceAction(on_edge=[WriteStep(event="ATC", value=1)])
    profile = Profile(
        name="t",
        bindings={
            "yoke": [
                Binding(name="b", source=Source(kind=SourceKind.BUTTON, code=5), action=action)
            ]
        },
    )
    engine = MappingEngine(profile)
    assert engine.resolve(DeviceEvent("yoke", SourceKind.BUTTON, 5, 1)) == [
        SendEvent(name="ATC", data=1)
    ]
    assert engine.resolve(DeviceEvent("yoke", SourceKind.BUTTON, 5, 0)) == []


def test_write_step_requires_exactly_one_target():
    with pytest.raises(ValidationError):
        WriteStep(value=1)  # neither event nor simvar
    with pytest.raises(ValidationError):
        WriteStep(event="X", simvar="Y", value=1)  # both


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
