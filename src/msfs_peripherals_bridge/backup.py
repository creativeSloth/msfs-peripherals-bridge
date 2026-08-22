"""Back up and restore all user data (mappings + arrangement + devices) as one zip.

User data is split across two places (see :mod:`.config`):

* the **repo checkout** — ``profiles/*.yaml`` (the mappings) and
  ``config/calibration.yaml`` (axis calibration);
* the **per-user config dir** ``~/.config/msfs-peripherals-bridge/`` —
  ``panel-layouts.yaml`` (the GUI "Anordnen" arrangement),
  ``devices.local.yaml`` (registered custom hardware), ``output-templates.yaml``
  and ``gui-settings.json``.

A fresh clone keeps the per-user dir but loses the repo-side profiles, so this
bundles **both** into a single portable archive and restores them — for a
re-clone, a machine move, or a plain backup.

Pure filesystem/zip logic (``root`` and ``user_dir`` are injectable) so it is
unit-tested without touching the real home directory.
"""

from __future__ import annotations

import json
import os
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from . import config

MANIFEST_NAME = "msfs-bridge-backup.json"
MANIFEST_VERSION = 1

_PROFILES_PREFIX = "profiles/"
_REPO_CONFIG_PREFIX = "repo-config/"
_USER_PREFIX = "user-config/"


@dataclass
class ExportResult:
    """What an :func:`export_config` wrote."""

    path: Path
    profiles: int
    calibration: bool
    user_files: int


@dataclass
class ImportResult:
    """What an :func:`import_config` restored (relative names)."""

    profiles: list[str] = field(default_factory=list)
    calibration: bool = False
    user_files: list[str] = field(default_factory=list)


def _user_dir(user_dir: Path | None) -> Path:
    return user_dir if user_dir is not None else config._user_config_dir()


def export_config(
    dest: Path | str, *, root: Path | None = None, user_dir: Path | None = None
) -> ExportResult:
    """Bundle the repo profiles/calibration and the whole per-user dir into ``dest``.

    ``dest`` gains a ``.zip`` suffix if missing. Returns counts of what went in.
    """
    root = root or config.project_root()
    udir = _user_dir(user_dir)
    dest = Path(dest)
    if dest.suffix.lower() != ".zip":
        dest = dest.with_suffix(".zip")

    prof_dir = config.profiles_dir(root)
    calib = config.calibration_file(root)
    n_profiles = 0
    has_calib = False
    n_user = 0

    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        if prof_dir.is_dir():
            for p in sorted(prof_dir.glob("*.yaml")):
                z.write(p, _PROFILES_PREFIX + p.name)
                n_profiles += 1
        if calib.is_file():
            z.write(calib, _REPO_CONFIG_PREFIX + calib.name)
            has_calib = True
        if udir.is_dir():
            for p in sorted(udir.rglob("*")):
                if p.is_file():
                    z.write(p, _USER_PREFIX + p.relative_to(udir).as_posix())
                    n_user += 1
        z.writestr(
            MANIFEST_NAME,
            json.dumps(
                {
                    "version": MANIFEST_VERSION,
                    "created": datetime.now(UTC).isoformat(),
                    "profiles": n_profiles,
                    "calibration": has_calib,
                    "user_files": n_user,
                },
                indent=2,
            ),
        )
    return ExportResult(dest, n_profiles, has_calib, n_user)


def read_manifest(src: Path | str) -> dict[str, object]:
    """The backup's manifest dict, or raise ``ValueError`` if it isn't one."""
    with zipfile.ZipFile(src) as z:
        try:
            data: dict[str, object] = json.loads(z.read(MANIFEST_NAME))
        except KeyError as exc:
            raise ValueError("not an msfs-bridge backup (manifest missing)") from exc
    return data


def import_config(
    src: Path | str, *, root: Path | None = None, user_dir: Path | None = None
) -> ImportResult:
    """Restore a backup made by :func:`export_config`, overwriting matching files.

    Guards against path traversal in a crafted archive (entries that escape their
    target directory are rejected). Returns the relative names that were written.
    """
    root = root or config.project_root()
    udir = _user_dir(user_dir)
    prof_dir = config.profiles_dir(root)
    repo_config_dir = config.calibration_file(root).parent
    result = ImportResult()

    with zipfile.ZipFile(src) as z:
        if MANIFEST_NAME not in z.namelist():
            raise ValueError("not an msfs-bridge backup (manifest missing)")
        for name in z.namelist():
            if name.endswith("/") or name == MANIFEST_NAME:
                continue
            if name.startswith(_PROFILES_PREFIX):
                rel = name[len(_PROFILES_PREFIX) :]
                _restore(z, name, prof_dir, rel)
                result.profiles.append(rel)
            elif name.startswith(_REPO_CONFIG_PREFIX):
                rel = name[len(_REPO_CONFIG_PREFIX) :]
                _restore(z, name, repo_config_dir, rel)
                result.calibration = True
            elif name.startswith(_USER_PREFIX):
                rel = name[len(_USER_PREFIX) :]
                _restore(z, name, udir, rel)
                result.user_files.append(rel)
    return result


def _restore(z: zipfile.ZipFile, name: str, base: Path, rel: str) -> None:
    """Write archive entry ``name`` to ``base/rel``, refusing to escape ``base``."""
    base = base.resolve()
    target = (base / rel).resolve()
    if target != base and not str(target).startswith(str(base) + os.sep):
        raise ValueError(f"unsafe path in archive: {name!r}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(z.read(name))
