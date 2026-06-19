# Sub-memory: Decisions

Parent: [../../MEMORY.md](../../MEMORY.md)

Decisions taken on **2026-06-19** with the user (creativeSloth / Edgar
Schwanebeck).

## D1 — SimConnect bridge in Wine (not uinput, not hybrid)
**Why:** the goal is to map to *named SimVars/events* per aircraft, not just
joystick axes. A virtual `uinput` controller can only feed axes/buttons and
cannot reach named SimVars/L-vars/H-events. MSFS runs under Proton, so
`SimConnect.dll` lives in the Wine prefix → a small bridge process there exposes
SimConnect over a local socket. See [simconnect-bridge.md](simconnect-bridge.md).

## D2 — YAML profiles + CLI (not TUI/GUI)
**Why:** profiles should be versionable in git and quick to build; a GUI can be
added later on top of the same models. CLI verbs: `scan`, `monitor`,
`calibrate`, `list-devices`, `list-profiles`, `validate`, `run`.

## D3 — Private GitHub repo `creativeSloth/msfs-peripherals-bridge`
Repo renamed by the user from the initial `msfs_peripherals-bridge` to
**`msfs-peripherals-bridge`**; the local folder was renamed to match. Tooling:
**uv** for env/build, hatchling backend, ruff + mypy + pytest, GitHub Actions CI.

## D4 — Python package name `msfs_peripherals_bridge`
Distribution name `msfs-peripherals-bridge`, console script `msfs-bridge`.
