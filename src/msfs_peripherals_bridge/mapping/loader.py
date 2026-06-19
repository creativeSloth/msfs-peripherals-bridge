"""Load and select YAML profiles and the device catalog."""

from __future__ import annotations

from pathlib import Path

import yaml

from ..models import DeviceCatalog, Profile


def load_device_catalog(path: Path) -> DeviceCatalog:
    """Parse ``config/devices.yaml`` into a validated catalog."""
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return DeviceCatalog.model_validate(data)


def load_profile(path: Path) -> Profile:
    """Parse a single aircraft profile YAML file."""
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return Profile.model_validate(data)


def load_profiles(directory: Path) -> list[Profile]:
    """Load every ``*.yaml`` profile in a directory (skips files prefixed '_')."""
    profiles: list[Profile] = []
    for path in sorted(directory.glob("*.yaml")):
        if path.name.startswith("_"):
            continue
        profiles.append(load_profile(path))
    return profiles


def select_profile(profiles: list[Profile], aircraft_title: str) -> Profile | None:
    """Pick the profile whose ``aircraft_match`` fits the loaded aircraft.

    Matching is case-insensitive substring; the most specific (longest)
    matching token wins so a 'C172 G1000' profile beats a generic 'C172'.
    """
    title = aircraft_title.lower()
    best: tuple[int, Profile] | None = None
    for profile in profiles:
        for token in profile.aircraft_match:
            if token.lower() in title and (best is None or len(token) > best[0]):
                best = (len(token), profile)
    return best[1] if best else None
