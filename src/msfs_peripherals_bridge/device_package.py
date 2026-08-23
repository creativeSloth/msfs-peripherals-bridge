"""Export/import ONE device's whole setup as a portable, shareable package.

The whole-config backup (:mod:`.backup`) bundles *everything*; this is the
per-device counterpart a user shares with someone else. One device's

* **definition** — its :class:`~.models.DeviceDef` (USB id, transport, the
  scanned input/output elements) so the importer has the device registered;
* **mapping** — the ``bindings`` + ``outputs`` one profile assigns to it;
* **arrangement** — its Nachbau panel layout (button positions);
* **calibration** — its axis raw ranges,

go into a single ``.zip``. Import registers the device (into the *user overlay*,
never the versioned catalog), restores the layout + calibration, and copies the
mapping into a chosen target profile.

Pure filesystem/zip logic (``root`` and ``user_dir`` are injectable) so it is
unit-tested without touching the real home directory.
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from ruamel.yaml.comments import CommentedMap

from . import config, profile_writer
from .mapping.loader import add_device_overlay, load_device_catalog
from .models import DeviceDef

MANIFEST_NAME = "msfs-device-package.json"
MANIFEST_VERSION = 1
KIND = "device-package"

_DEVICE_NAME = "device.yaml"
_MAPPING_NAME = "mapping.yaml"
_LAYOUT_NAME = "layout.yaml"
_CALIBRATION_NAME = "calibration.yaml"


@dataclass
class DeviceExportResult:
    """What an :func:`export_device_package` wrote."""

    path: Path
    device_id: str
    bindings: int
    outputs: int
    has_layout: bool
    has_calibration: bool


@dataclass
class DeviceImportResult:
    """What an :func:`import_device_package` restored."""

    device_id: str
    device_name: str
    target_profile: str | None
    bindings: int
    outputs: int
    layout: bool
    calibration: bool


def _user_dir(user_dir: Path | None) -> Path:
    return user_dir if user_dir is not None else config._user_config_dir()


def _layout_file(udir: Path) -> Path:
    return udir / "panel-layouts.yaml"


def _overlay_file(udir: Path) -> Path:
    return udir / "devices.local.yaml"


def _read_device_section(path: Path, device_id: str) -> object | None:
    """The ``devices[device_id]`` node of a ``{devices: {...}}`` YAML file, or None."""
    if not path.is_file():
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return (data.get("devices") or {}).get(device_id)


def _merge_device_section(path: Path, device_id: str, section: object, *, sort_keys: bool) -> None:
    """Write ``section`` into ``devices[device_id]`` of a ``{devices: {...}}`` file."""
    data: dict[str, Any] = {}
    if path.is_file():
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    data.setdefault("devices", {})[device_id] = section
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=sort_keys, allow_unicode=True), encoding="utf-8")


def export_device_package(
    device_id: str,
    profile_name: str,
    dest: Path | str,
    *,
    root: Path | None = None,
    user_dir: Path | None = None,
) -> DeviceExportResult:
    """Bundle one device's def + mapping + layout + calibration into ``dest`` (.zip).

    ``profile_name`` is the profile the mapping is taken from (without the
    ``.yaml`` suffix). ``dest`` gains a ``.zip`` suffix if missing.
    """
    root = root or config.project_root()
    udir = _user_dir(user_dir)
    dest = Path(dest)
    if dest.suffix.lower() != ".zip":
        dest = dest.with_suffix(".zip")

    catalog = load_device_catalog(config.devices_file(root))
    ddef = catalog.by_id(device_id)
    if ddef is None:
        raise ValueError(f"unknown device '{device_id}'")

    prof_path = config.profiles_dir(root) / f"{profile_name}.yaml"
    if not prof_path.is_file():
        raise ValueError(f"unknown profile '{profile_name}'")
    src = profile_writer.load(prof_path)
    pkg_map: CommentedMap = CommentedMap()
    n_bind, n_out = profile_writer.copy_device_mappings(src, pkg_map, device_id)

    layout = _read_device_section(_layout_file(udir), device_id)
    calib = _read_device_section(config.calibration_file(root), device_id)

    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            _DEVICE_NAME,
            yaml.safe_dump(ddef.model_dump(exclude_none=True), sort_keys=False, allow_unicode=True),
        )
        z.writestr(_MAPPING_NAME, profile_writer.dumps(pkg_map))
        if layout is not None:
            z.writestr(
                _LAYOUT_NAME,
                yaml.safe_dump({device_id: layout}, sort_keys=False, allow_unicode=True),
            )
        if calib is not None:
            z.writestr(
                _CALIBRATION_NAME,
                yaml.safe_dump({device_id: calib}, sort_keys=True, allow_unicode=True),
            )
        z.writestr(
            MANIFEST_NAME,
            json.dumps(
                {
                    "version": MANIFEST_VERSION,
                    "kind": KIND,
                    "created": datetime.now(UTC).isoformat(),
                    "device_id": device_id,
                    "device_name": ddef.name,
                    "source_profile": profile_name,
                    "bindings": n_bind,
                    "outputs": n_out,
                    "layout": layout is not None,
                    "calibration": calib is not None,
                },
                indent=2,
            ),
        )
    return DeviceExportResult(dest, device_id, n_bind, n_out, layout is not None, calib is not None)


def read_manifest(src: Path | str) -> dict[str, object]:
    """The package's manifest dict, or raise ``ValueError`` if it isn't one."""
    with zipfile.ZipFile(src) as z:
        try:
            data: dict[str, object] = json.loads(z.read(MANIFEST_NAME))
        except KeyError as exc:
            raise ValueError("not a device package (manifest missing)") from exc
    if data.get("kind") != KIND:
        raise ValueError("not a device package (wrong kind)")
    return data


def import_device_package(
    src: Path | str,
    target_profile: str | None,
    *,
    root: Path | None = None,
    user_dir: Path | None = None,
    overwrite: bool = True,
) -> DeviceImportResult:
    """Restore a package made by :func:`export_device_package`.

    Registers the device into the user overlay (also un-hiding its id if it was
    deregistered), restores its panel layout + calibration, and copies its mapping
    into ``target_profile`` (skipped when the package carries no mapping or when
    ``target_profile`` is ``None``). Raises ``ValueError`` for a bad archive or an
    unknown target profile. The mapping write is validated before saving.
    """
    root = root or config.project_root()
    udir = _user_dir(user_dir)
    manifest = read_manifest(src)
    device_id = str(manifest.get("device_id") or "")
    if not device_id:
        raise ValueError("device package manifest has no device_id")

    n_bind = n_out = 0
    has_layout = has_calib = False
    with zipfile.ZipFile(src) as z:
        names = set(z.namelist())

        if _DEVICE_NAME not in names:
            raise ValueError("device package is missing its device definition")
        ddef = DeviceDef.model_validate(yaml.safe_load(z.read(_DEVICE_NAME)))
        device_name = ddef.name
        add_device_overlay(ddef, overlay=_overlay_file(udir))

        if _MAPPING_NAME in names and target_profile:
            dst_path = config.profiles_dir(root) / f"{target_profile}.yaml"
            if not dst_path.is_file():
                raise ValueError(f"unknown target profile '{target_profile}'")
            pkg_map = profile_writer.loads(z.read(_MAPPING_NAME).decode("utf-8"))
            if isinstance(pkg_map, CommentedMap):
                dst = profile_writer.load(dst_path)
                n_bind, n_out = profile_writer.copy_device_mappings(
                    pkg_map, dst, device_id, overwrite=overwrite
                )
                profile_writer.validate(dst)  # reject a broken result before writing
                profile_writer.dump(dst, dst_path)

        if _LAYOUT_NAME in names:
            section = (yaml.safe_load(z.read(_LAYOUT_NAME)) or {}).get(device_id)
            if section is not None:
                _merge_device_section(_layout_file(udir), device_id, section, sort_keys=False)
                has_layout = True

        if _CALIBRATION_NAME in names:
            section = (yaml.safe_load(z.read(_CALIBRATION_NAME)) or {}).get(device_id)
            if section is not None:
                _merge_device_section(
                    config.calibration_file(root), device_id, section, sort_keys=True
                )
                has_calib = True

    return DeviceImportResult(
        device_id, device_name, target_profile, n_bind, n_out, has_layout, has_calib
    )
