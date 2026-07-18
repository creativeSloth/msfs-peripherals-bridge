"""User-defined virtual variables: the LocalVar model + V: picker entries."""

import pytest
from pydantic import ValidationError

from msfs_peripherals_bridge.gui_catalog import KIND_VIRTUAL, local_var_catalog
from msfs_peripherals_bridge.models import LocalVar, Profile


def test_localvar_defaults():
    lv = LocalVar(name="MyMode")
    assert (lv.unit, lv.initial, lv.persist, lv.description) == ("number", 0.0, False, "")


def test_localvar_rejects_bad_names():
    with pytest.raises(ValidationError):
        LocalVar(name="")
    with pytest.raises(ValidationError):
        LocalVar(name="V:MyMode")  # the prefix is added at reference sites, not in the name
    with pytest.raises(ValidationError):
        LocalVar(name="my mode")  # no spaces


def test_profile_accepts_local_vars():
    prof = Profile.model_validate(
        {
            "name": "T",
            "local_vars": [
                {"name": "ModeA", "initial": 1, "description": "test mode"},
                {"name": "Counter", "unit": "number"},
            ],
        }
    )
    assert [lv.name for lv in prof.local_vars] == ["ModeA", "Counter"]
    assert prof.local_vars[0].initial == 1.0


def test_profile_rejects_duplicate_local_var_names():
    with pytest.raises(ValidationError):
        Profile.model_validate(
            {"name": "T", "local_vars": [{"name": "Dup"}, {"name": "Dup"}]}
        )


def test_local_var_catalog_makes_virtual_picker_entries():
    prof = Profile.model_validate(
        {"name": "T", "local_vars": [{"name": "ModeA", "unit": "bool", "description": "sub"}]}
    )
    cat = local_var_catalog(prof.local_vars)
    assert len(cat) == 1
    v = cat[0]
    assert v.kind == KIND_VIRTUAL
    assert v.name == "ModeA"
    assert v.unit == "bool"
    assert v.settable is True
    assert v.category == "sub"  # description feeds the picker category
    assert v.label.startswith("V: ModeA")


def test_local_var_catalog_empty_when_none_declared():
    prof = Profile.model_validate({"name": "T"})
    assert local_var_catalog(prof.local_vars) == []
