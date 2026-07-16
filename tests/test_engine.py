import pytest
from pydantic import ValidationError

from msfs_peripherals_bridge.devices.base import DeviceEvent
from msfs_peripherals_bridge.mapping.engine import MappingEngine
from msfs_peripherals_bridge.models import (
    AxisSplit,
    Binding,
    Condition,
    EventAction,
    EventFromVarAction,
    HatMap,
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


# --------------------------------------------------------------------------- #
# detent split: one axis binding, two logical ranges
# --------------------------------------------------------------------------- #
def _split_profile() -> Profile:
    # TQ6-like throttle: full travel 0..1000, detent at 200. Above the detent the
    # normal THROTTLE1_SET range; below it a reverse-throttle SimVar 0..1.
    return Profile(
        name="t",
        bindings={
            "tq6": [
                Binding(
                    name="Throttle mit Reverse",
                    source=Source(kind=SourceKind.AXIS, code=0, raw_min=0, raw_max=1000),
                    action=EventAction(event="THROTTLE1_SET"),
                    transform=Transform(out_min=0, out_max=16383),
                    split=AxisSplit(
                        at=200,
                        action=SimVarAction(simvar="TURB ENG REVERSE NOZZLE PERCENT:1"),
                        transform=Transform(invert=True),
                    ),
                )
            ]
        },
    )


def test_split_axis_upper_range_normalises_from_the_detent():
    engine = MappingEngine(_split_profile())
    # At the detent the upper range starts: out_min (0).
    assert engine.resolve(DeviceEvent("tq6", SourceKind.AXIS, 0, 200)) == [
        SendEvent(name="THROTTLE1_SET", data=0)
    ]
    # Full travel = out_max.
    assert engine.resolve(DeviceEvent("tq6", SourceKind.AXIS, 0, 1000)) == [
        SendEvent(name="THROTTLE1_SET", data=16383)
    ]
    # Halfway between detent and max -> mid output.
    assert engine.resolve(DeviceEvent("tq6", SourceKind.AXIS, 0, 600)) == [
        SendEvent(name="THROTTLE1_SET", data=8192)
    ]


def test_split_axis_lower_range_uses_its_own_action_and_transform():
    engine = MappingEngine(_split_profile())
    # Below the detent the split action fires; invert=True makes full-back = 1.
    cmds = engine.resolve(DeviceEvent("tq6", SourceKind.AXIS, 0, 0))
    assert cmds == [SetSimVar(name="TURB ENG REVERSE NOZZLE PERCENT:1", unit="number", value=1.0)]
    # Just below the detent -> lower range's top -> inverted to ~0.
    (cmd,) = engine.resolve(DeviceEvent("tq6", SourceKind.AXIS, 0, 199))
    assert cmd.value == pytest.approx(0.0, abs=0.01)


def test_split_requires_an_axis_source():
    with pytest.raises(ValidationError):
        Binding(
            name="x",
            source=Source(kind=SourceKind.BUTTON, code=1),
            action=EventAction(event="X", value=1),
            split=AxisSplit(at=1, action=EventAction(event="Y")),
        )


# --------------------------------------------------------------------------- #
# direction-aware hat: one binding, four direction actions
# --------------------------------------------------------------------------- #
def _hat_profile() -> Profile:
    return Profile(
        name="t",
        bindings={
            "yoke": [
                Binding(
                    name="Trim-Hat",
                    source=Source(kind=SourceKind.HAT, code=16),
                    hat=HatMap(
                        up=EventAction(event="ELEV_TRIM_UP"),
                        down=EventAction(event="ELEV_TRIM_DN"),
                        left=SimVarAction(simvar="L:PAN_LEFT"),
                        # right deliberately unmapped
                    ),
                )
            ]
        },
    )


def test_hat_directions_resolve_on_both_channels():
    engine = MappingEngine(_hat_profile())
    # Y channel = base+1: -1 = up, +1 = down
    assert engine.resolve(DeviceEvent("yoke", SourceKind.HAT, 17, -1)) == [
        SendEvent(name="ELEV_TRIM_UP", data=1)
    ]
    assert engine.resolve(DeviceEvent("yoke", SourceKind.HAT, 17, 1)) == [
        SendEvent(name="ELEV_TRIM_DN", data=1)
    ]
    # X channel = base: -1 = left (simvar set to 1.0)
    assert engine.resolve(DeviceEvent("yoke", SourceKind.HAT, 16, -1)) == [
        SetSimVar(name="L:PAN_LEFT", unit="number", value=1.0)
    ]
    # unmapped direction + centring do nothing
    assert engine.resolve(DeviceEvent("yoke", SourceKind.HAT, 16, 1)) == []
    assert engine.resolve(DeviceEvent("yoke", SourceKind.HAT, 16, 0)) == []
    # a different hat's channels never match
    assert engine.resolve(DeviceEvent("yoke", SourceKind.HAT, 18, 1)) == []


def test_hat_model_validation():
    with pytest.raises(ValidationError):  # hat only on hat sources
        Binding(name="x", source=Source(kind=SourceKind.BUTTON, code=1),
                hat=HatMap(up=EventAction(event="X")))
    with pytest.raises(ValidationError):  # hat needs at least one direction
        Binding(name="x", source=Source(kind=SourceKind.HAT, code=16), hat=HatMap())
    with pytest.raises(ValidationError):  # non-hat bindings still need an action
        Binding(name="x", source=Source(kind=SourceKind.BUTTON, code=1))


# --------------------------------------------------------------------------- #
# when: conditions gate bindings on live values (fail-closed)
# --------------------------------------------------------------------------- #
def _gated_profile() -> Profile:
    return Profile(
        name="t",
        bindings={
            "yoke": [
                Binding(
                    name="Nur mit Avionik",
                    source=Source(kind=SourceKind.BUTTON, code=288),
                    action=EventAction(event="GEAR_TOGGLE", value=1),
                    when=[Condition(var="AVIONICS MASTER SWITCH"),
                          Condition(var="L:AUTOPILOT_MODE", op="<", value=3)],
                )
            ]
        },
    )


def test_conditions_gate_and_pass():
    values = {"AVIONICS MASTER SWITCH": 1.0, "L:AUTOPILOT_MODE": 2}
    engine = MappingEngine(_gated_profile(), values=values.get)
    press = DeviceEvent("yoke", SourceKind.BUTTON, 288, 1)
    assert engine.resolve(press) == [SendEvent(name="GEAR_TOGGLE", data=1)]
    values["L:AUTOPILOT_MODE"] = 3  # second condition (< 3) now fails
    assert engine.resolve(press) == []
    values["L:AUTOPILOT_MODE"] = 2
    values["AVIONICS MASTER SWITCH"] = 0.0  # first (== 1) fails
    assert engine.resolve(press) == []


def test_conditions_unknown_value_blocks():
    engine = MappingEngine(_gated_profile())  # no value provider at all
    assert engine.resolve(DeviceEvent("yoke", SourceKind.BUTTON, 288, 1)) == []


def test_condition_equality_tolerates_float_noise():
    prof = Profile(name="t", bindings={"yoke": [Binding(
        name="x", source=Source(kind=SourceKind.BUTTON, code=1),
        action=EventAction(event="X", value=1),
        when=[Condition(var="A", value=29.92)])]})
    engine = MappingEngine(prof, values={"A": 29.920000001}.get)
    assert engine.resolve(DeviceEvent("yoke", SourceKind.BUTTON, 1, 1)) != []
