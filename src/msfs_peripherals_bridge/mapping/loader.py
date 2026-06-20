"""Load and select YAML profiles and the device catalog."""

from __future__ import annotations

from pathlib import Path

import yaml

from ..devices.calibration import CalibrationFile, DeviceCalibration
from ..models import Binding, DeviceCatalog, Profile, SourceKind


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


def apply_calibration(profile: Profile, calibration: CalibrationFile) -> Profile:
    """Return a copy of ``profile`` with axis raw ranges filled from calibration.

    Profiles carry only the semantic mapping; the hardware travel of each axis
    lives in ``config/calibration.yaml``. For every axis binding whose
    ``raw_min``/``raw_max`` is unset, the value is taken from the calibration
    entry matched by (device id, code). An explicit value in the profile always
    wins — that is how a deliberate sub-range (e.g. a TQ6+ lever clamped at its
    detent) is expressed. Buttons and hats are returned unchanged.

    Raises ``ValueError`` if an axis binding has no range and no calibration
    entry to supply one, so a miscalibrated profile fails loudly at load time.
    """
    resolved: dict[str, list[Binding]] = {}
    for device_id, bindings in profile.bindings.items():
        device_cal = calibration.devices.get(device_id)
        resolved[device_id] = [
            _resolve_ranges(binding, device_id, device_cal, profile.name) for binding in bindings
        ]
    return profile.model_copy(update={"bindings": resolved})


def _resolve_ranges(
    binding: Binding, device_id: str, device_cal: DeviceCalibration | None, profile_name: str
) -> Binding:
    source = binding.source
    if source.kind is not SourceKind.AXIS:
        return binding
    if source.raw_min is not None and source.raw_max is not None:
        return binding

    axis_cal = device_cal.axes.get(source.code) if device_cal else None
    if axis_cal is None:
        raise ValueError(
            f"Profile '{profile_name}': axis binding '{binding.name}' on device "
            f"'{device_id}' (code {source.code}) has no raw range and no "
            f"calibration entry to supply one. Run `calibrate {device_id}` or set "
            f"raw_min/raw_max in the profile."
        )
    new_source = source.model_copy(
        update={
            "raw_min": source.raw_min if source.raw_min is not None else axis_cal.raw_min,
            "raw_max": source.raw_max if source.raw_max is not None else axis_cal.raw_max,
        }
    )
    return binding.model_copy(update={"source": new_source})


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
