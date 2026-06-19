# Project memory — msfs-peripherals-bridge

This is the **main memory** (Hauptgedächtnis) for the project: a durable index
of *why* things are the way they are, decisions made, and open threads. It does
not duplicate the code or the README — it points to **sub-memories** under
[`docs/memory/`](docs/memory/) and to the reference docs under [`docs/`](docs/).

> Convention: keep each sub-memory focused on one topic. Link to a sub-memory
> from here with a one-line hook. Update the relevant sub-memory instead of
> writing prose here. Convert relative dates to absolute (YYYY-MM-DD).

## Sub-memories

- [Architecture](docs/memory/architecture.md) — components, data flow, threading
  model and why the Wine SimConnect bridge exists.
- [Decisions](docs/memory/decisions.md) — the choices made on 2026-06-19
  (bridge vs uinput, YAML+CLI, private repo) and their rationale.
- [Devices & calibration](docs/memory/devices-and-calibration.md) — the four
  peripherals, their USB ids, and the **OPEN** discovery/calibration task that
  needs the hardware connected.
- [SimConnect bridge](docs/memory/simconnect-bridge.md) — the Wine-side bridge
  spec, wire protocol, and the WASM (MobiFlight) requirement for L:/H:/B: vars.
- [Profiles](docs/memory/profiles.md) — how per-aircraft mapping profiles work
  and auto-selection by aircraft TITLE.
- [Roadmap](docs/memory/roadmap.md) — what is done and what is next.

## Reference docs (not memory, but linked)

- [Hardware research](docs/research/) — per-device specs and mapping hints.
- [SimVar & event reference](docs/simvars-reference.md) — the catalog of MSFS
  variables/events to map controls to (the "SPAD.neXt list").

## Current status (2026-06-19)

Scaffold complete and green (tests, ruff, mypy). Mapping engine, transforms,
profile system and CLI (`scan`/`monitor`/`calibrate`/`run`/`validate`) work.
**Not yet done:** the Wine SimConnect bridge process, and capturing the real
device layout/calibration — blocked on the hardware being connected.
See [Roadmap](docs/memory/roadmap.md).
