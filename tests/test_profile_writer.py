"""Comment-preserving profile writer: ruamel round-trip + targeted edits."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from msfs_peripherals_bridge import profile_writer as pw
from msfs_peripherals_bridge.mapping.loader import load_profile

PROFILES = Path(__file__).resolve().parents[1] / "profiles"


# --------------------------------------------------------------------------- #
# round-trip fidelity
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name", ["cessna_172", "cessna_152", "default"])
def test_roundtrip_byte_identical(name):
    # These profiles carry no hand-wrapped multi-line flow maps, so a load→dump
    # must reproduce them exactly: comments, quotes, flow style and brace padding.
    p = PROFILES / f"{name}.yaml"
    assert pw.dumps(pw.load(p)) == p.read_text(encoding="utf-8")


@pytest.mark.parametrize("name", ["piper_arrow", "cessna_172", "cessna_152", "default"])
def test_roundtrip_semantically_identical(name):
    # Even piper_arrow (whose output banks reflow) loses no *data* on a round-trip.
    p = PROFILES / f"{name}.yaml"
    assert pw.validate(pw.load(p)) == load_profile(p)


def test_flow_style_comments_and_padding_preserved():
    out = pw.dumps(pw.load(PROFILES / "piper_arrow.yaml"))
    assert "source: { kind: axis, code: 0 }" in out  # flow map + inner padding
    assert "# --- Fulcrum One Yoke" in out  # a section comment survives
    assert "aircraft_match:" in out


def test_empty_flow_sequence_not_padded():
    # regression: aircraft_match: [] must not become [  ]
    out = pw.dumps(pw.load(PROFILES / "default.yaml"))
    assert "aircraft_match: []" in out


# --------------------------------------------------------------------------- #
# binding edits
# --------------------------------------------------------------------------- #
def test_apply_binding_edit_changes_only_the_target():
    data = pw.load(PROFILES / "piper_arrow.yaml")
    pw.apply_binding_edit(
        data,
        "yoke",
        0,
        {
            "name": "Aileron (roll)",
            "source": {"kind": "axis", "code": 0},
            "action": {"type": "event", "event": "AILERON_SET_X"},
            "transform": {"deadzone": 0.03, "curve": "expo", "expo": 0.25,
                          "invert": True, "out_min": -16383, "out_max": 16383},
        },
    )
    out = pw.dumps(data)
    assert "AILERON_SET_X" in out
    assert "# --- Fulcrum One Yoke" in out  # surrounding comment preserved
    assert "source: { kind: axis, code: 0 }" in out  # flow style preserved
    prof = pw.validate(data)
    assert prof.bindings["yoke"][0].action.event == "AILERON_SET_X"
    # the untouched second binding is unchanged
    assert prof.bindings["yoke"][1].action.event == "ELEVATOR_SET"


def test_apply_binding_edit_prunes_removed_keys():
    # switching an axis binding's action from event to simvar drops the old key
    data = pw.load(PROFILES / "default.yaml")
    pw.apply_binding_edit(
        data,
        "yoke",
        0,
        {
            "name": "Aileron",
            "source": {"kind": "axis", "code": 0},
            "action": {"type": "simvar", "simvar": "L:MyAileron"},
        },
    )
    prof = pw.validate(data)
    action = prof.bindings["yoke"][0].action
    assert action.type == "simvar"
    assert action.simvar == "L:MyAileron"
    assert "AILERON_SET" not in pw.dumps(data)  # old event key is gone


def test_add_and_remove_binding():
    data = pw.load(PROFILES / "default.yaml")
    before = len(data["bindings"]["yoke"])
    pw.add_binding(
        data,
        "yoke",
        {
            "name": "Test button",
            "source": {"kind": "button", "code": 300},
            "action": {"type": "event", "event": "PARKING_BRAKES", "value": 1},
        },
    )
    prof = pw.validate(data)
    assert len(prof.bindings["yoke"]) == before + 1
    assert prof.bindings["yoke"][-1].name == "Test button"
    assert "source: { kind: button, code: 300 }" in pw.dumps(data)  # flow style
    pw.remove_binding(data, "yoke", before)
    assert len(pw.validate(data).bindings["yoke"]) == before


def test_add_binding_creates_new_device_block():
    data = pw.load(PROFILES / "default.yaml")
    assert "trim" not in data.get("bindings", {})
    pw.add_binding(
        data,
        "trim",
        {
            "name": "Elevator trim",
            "source": {"kind": "axis", "code": 7, "raw_min": 0, "raw_max": 1023},
            "action": {"type": "event", "event": "ELEVATOR_TRIM_SET"},
        },
    )
    prof = pw.validate(data)
    assert prof.bindings["trim"][0].name == "Elevator trim"


# --------------------------------------------------------------------------- #
# local (virtual) vars + validation guard
# --------------------------------------------------------------------------- #
def test_set_local_vars_round_trips_and_clears():
    data = pw.load(PROFILES / "default.yaml")
    assert "local_vars" not in data
    pw.set_local_vars(data, [{"name": "MyMode", "initial": 1, "description": "t"}, {"name": "Cnt"}])
    prof = pw.validate(data)
    assert [lv.name for lv in prof.local_vars] == ["MyMode", "Cnt"]
    assert "local_vars:" in pw.dumps(data)
    pw.set_local_vars(data, [])  # empty list removes the block
    assert "local_vars" not in data


def test_validate_raises_on_bad_edit():
    data = pw.load(PROFILES / "default.yaml")
    pw.apply_binding_edit(
        data, "yoke", 0,
        {"name": "Broken", "source": {"kind": "axis", "code": 0}, "action": {"type": "nonsense"}},
    )
    with pytest.raises(ValidationError):
        pw.validate(data)


def test_missing_device_raises():
    data = pw.load(PROFILES / "default.yaml")
    with pytest.raises(KeyError):
        pw.apply_binding_edit(data, "no_such_device", 0, {"name": "x"})
