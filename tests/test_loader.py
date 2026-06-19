from pathlib import Path

from msfs_peripherals_bridge.mapping.loader import (
    load_device_catalog,
    load_profiles,
    select_profile,
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
