from pathlib import Path

import pytest

from msfs_peripherals_bridge.devices.calibration import (
    AxisCalibration,
    CalibrationFile,
    DeviceCalibration,
    load_calibration,
)
from msfs_peripherals_bridge.mapping.loader import (
    apply_calibration,
    load_device_catalog,
    load_profiles,
    select_profile,
)
from msfs_peripherals_bridge.models import (
    Binding,
    EventAction,
    Profile,
    Source,
    SourceKind,
)

REPO = Path(__file__).resolve().parents[1]


def test_device_catalog_loads_and_parses_usb_ids():
    catalog = load_device_catalog(REPO / "config" / "devices.yaml")
    tq6 = catalog.by_id("tq6")
    assert tq6 is not None
    assert tq6.usb_key == (0x16D0, 0x0DA2)


def test_profiles_load_and_skip_underscore_files():
    profiles = load_profiles(REPO / "profiles")
    names = {p.name for p in profiles}
    assert "Cessna 172 Skyhawk (G1000)" in names
    # _schema.md and _-prefixed yaml files must not be loaded.
    assert all(not p.name.startswith("_") for p in profiles)


def test_select_profile_prefers_longest_match():
    profiles = load_profiles(REPO / "profiles")
    selected = select_profile(profiles, "Cessna 172 Skyhawk")
    assert selected is not None
    assert "172" in selected.name


def test_select_profile_returns_none_when_no_match():
    profiles = load_profiles(REPO / "profiles")
    assert select_profile(profiles, "Boeing 747") is None


def _axis_binding(code: int, raw_min=None, raw_max=None) -> Binding:
    return Binding(
        name=f"axis {code}",
        source=Source(kind=SourceKind.AXIS, code=code, raw_min=raw_min, raw_max=raw_max),
        action=EventAction(event="TEST_SET"),
    )


def _calibration() -> CalibrationFile:
    return CalibrationFile(
        devices={
            "yoke": DeviceCalibration(
                device_id="yoke",
                axes={0: AxisCalibration(code=0, raw_min=7, raw_max=4089, center=2114)},
            )
        }
    )


def test_apply_calibration_fills_missing_ranges():
    profile = Profile(name="p", bindings={"yoke": [_axis_binding(0)]})
    resolved = apply_calibration(profile, _calibration())
    source = resolved.bindings["yoke"][0].source
    assert (source.raw_min, source.raw_max) == (7, 4089)


def test_apply_calibration_keeps_explicit_overrides():
    profile = Profile(name="p", bindings={"yoke": [_axis_binding(0, raw_min=0, raw_max=3275)]})
    resolved = apply_calibration(profile, _calibration())
    source = resolved.bindings["yoke"][0].source
    assert (source.raw_min, source.raw_max) == (0, 3275)


def test_apply_calibration_errors_when_no_range_and_no_calibration():
    profile = Profile(name="p", bindings={"yoke": [_axis_binding(99)]})
    with pytest.raises(ValueError, match="no raw range"):
        apply_calibration(profile, _calibration())


def test_shipped_profiles_resolve_against_calibration():
    calibration = load_calibration(REPO / "config" / "calibration.yaml")
    for profile in load_profiles(REPO / "profiles"):
        resolved = apply_calibration(profile, calibration)
        for bindings in resolved.bindings.values():
            for binding in bindings:
                if binding.source.kind is SourceKind.AXIS:
                    assert binding.source.raw_min is not None
                    assert binding.source.raw_max is not None
