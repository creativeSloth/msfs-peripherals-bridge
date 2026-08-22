"""Load and select YAML profiles and the device catalog."""

from __future__ import annotations

from pathlib import Path

import yaml

from ..devices.calibration import CalibrationFile, DeviceCalibration
from ..models import Binding, DeviceCatalog, DeviceDef, Profile, SourceKind


def merge_device_catalog(base: DeviceCatalog, overlay: DeviceCatalog) -> DeviceCatalog:
    """Overlay devices onto base: new ids appended, matching ids overridden. Pure."""
    by_id = {d.id: d for d in base.devices}
    order = [d.id for d in base.devices]
    for d in overlay.devices:
        if d.id not in by_id:
            order.append(d.id)
        by_id[d.id] = d
    return DeviceCatalog(devices=[by_id[i] for i in order])


def load_device_catalog(
    path: Path, *, overlay: Path | None = None, merge_overlay: bool = True
) -> DeviceCatalog:
    """Parse ``config/devices.yaml`` and merge the user device overlay on top.

    User-added devices live in ``devices.local.yaml`` (see
    :func:`..config.devices_overlay_file`) so a stranger's hardware never touches
    the versioned catalog. Overlay entries with a new ``id`` are appended; a
    matching ``id`` overrides the bundled one. Pass ``merge_overlay=False`` to
    read only ``path`` (used by tests).
    """
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    catalog = DeviceCatalog.model_validate(data)
    if not merge_overlay:
        return catalog
    if overlay is None:
        from .. import config

        overlay = config.devices_overlay_file()
    if overlay.exists():
        extra = yaml.safe_load(overlay.read_text(encoding="utf-8")) or {}
        catalog = merge_device_catalog(catalog, DeviceCatalog.model_validate(extra))
    return catalog


def add_device_overlay(ddef: DeviceDef, overlay: Path | None = None) -> Path:
    """Append/replace a device in the user overlay YAML, creating it if needed."""
    if overlay is None:
        from .. import config

        overlay = config.devices_overlay_file()
    existing = DeviceCatalog(devices=[])
    if overlay.exists():
        data = yaml.safe_load(overlay.read_text(encoding="utf-8")) or {}
        existing = DeviceCatalog.model_validate(data)
    merged = merge_device_catalog(existing, DeviceCatalog(devices=[ddef]))
    overlay.parent.mkdir(parents=True, exist_ok=True)
    overlay.write_text(
        yaml.safe_dump(
            merged.model_dump(exclude_none=True), sort_keys=False, allow_unicode=True
        ),
        encoding="utf-8",
    )
    return overlay


def set_device_inputs(ddef: DeviceDef, blocks, overlay: Path | None = None) -> Path:
    """Persist the device explorer's READ elements (inputs) into the user overlay.

    Keeps the device's WRITE elements (outputs) untouched — pass the current
    ``ddef`` (as loaded from the merged catalog) so its outputs ride along.
    """
    return add_device_overlay(
        ddef.model_copy(update={"inputs": list(blocks)}), overlay=overlay
    )


def set_device_outputs(ddef: DeviceDef, blocks, overlay: Path | None = None) -> Path:
    """Persist the device explorer's WRITE elements (LEDs/displays) into the overlay.

    Counterpart to :func:`set_device_inputs`; keeps the READ elements untouched.
    """
    return add_device_overlay(
        ddef.model_copy(update={"outputs": list(blocks)}), overlay=overlay
    )


def load_output_templates(path: Path | None = None) -> dict[str, dict]:
    """Load the user's saved output-block templates ``{name: block_dict}``.

    Empty dict when the file is missing. Blocks are kept as plain dicts (the same
    shape as :data:`..gui_mapper.OUTPUT_BLOCK_TEMPLATES`) so they can be dropped
    straight onto a device via ``profile_writer.add_output``.
    """
    if path is None:
        from .. import config

        path = config.output_templates_file()
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return dict(data.get("templates", {}))


def save_output_template(name: str, block: dict, path: Path | None = None) -> Path:
    """Add/replace a named output-block template in the user templates file."""
    if path is None:
        from .. import config

        path = config.output_templates_file()
    templates = load_output_templates(path)
    templates[name] = dict(block)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump({"templates": templates}, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return path


def delete_output_template(name: str, path: Path | None = None) -> Path:
    """Remove a named user template (no-op if absent)."""
    if path is None:
        from .. import config

        path = config.output_templates_file()
    templates = load_output_templates(path)
    if name in templates:
        del templates[name]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.safe_dump({"templates": templates}, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
    return path


def load_panel_layout(device_id: str, path: Path | None = None) -> dict[str, tuple[float, ...]]:
    """Load one device's Nachbau layout overrides.

    Each value is ``(x, y)`` (repositioned only) or ``(x, y, w, h)`` (also resized
    in arrange mode). Empty dict when nothing was rearranged. Consumed by
    :func:`..panel_layout.apply_layout_overrides`.
    """
    if path is None:
        from .. import config

        path = config.panel_layouts_file()
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    dev = (data.get("devices", {}) or {}).get(device_id, {}) or {}
    return {k: tuple(float(n) for n in v) for k, v in dev.items()}


def save_panel_layout_override(
    device_id: str, key: str, x: float, y: float,
    w: float | None = None, h: float | None = None, path: Path | None = None
) -> Path:
    """Persist where one element sits (and, when given, its size).

    ``w``/``h`` ``None`` = a plain move: only x/y change, and any previously saved
    size for this element is preserved. With ``w``/``h`` the full ``[x, y, w, h]`` is
    stored (arrange-mode resize / px dialog)."""
    if path is None:
        from .. import config

        path = config.panel_layouts_file()
    data = {}
    if path.exists():
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    dev = data.setdefault("devices", {}).setdefault(device_id, {})
    if w is None and h is None:
        prev = dev.get(key)
        if isinstance(prev, list) and len(prev) >= 4:  # keep the existing size
            dev[key] = [round(x, 4), round(y, 4), prev[2], prev[3]]
        else:
            dev[key] = [round(x, 4), round(y, 4)]
    else:
        dev[key] = [round(x, 4), round(y, 4), round(float(w), 4), round(float(h), 4)]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
                    encoding="utf-8")
    return path


def clear_panel_layout(device_id: str, path: Path | None = None) -> Path:
    """Drop all layout overrides for a device (reset to the generated layout)."""
    if path is None:
        from .. import config

        path = config.panel_layouts_file()
    if path.exists():
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if device_id in data.get("devices", {}):
            del data["devices"][device_id]
            path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
                            encoding="utf-8")
    return path


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
