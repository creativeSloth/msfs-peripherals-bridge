# Sub-memory: Architecture

Parent: [../../MEMORY.md](../../MEMORY.md)

## Components (src/msfs_peripherals_bridge/)
- `models.py` — pydantic schema (Source, Binding, Action, Profile, DeviceDef).
  The single source of truth for the YAML format.
- `devices/` — `capabilities.py` (scan/describe), `evdev_reader.py` (read into
  `DeviceEvent`), `calibration.py` (record ranges), `base.py` (DeviceEvent).
- `mapping/` — `transforms.py` (pure axis math), `engine.py` (DeviceEvent +
  Profile → commands), `loader.py` (YAML load + profile selection).
- `simconnect/` — `protocol.py` (JSON wire frames), `client.py` (TCP client +
  DryRunDispatcher).
- `runtime.py` — threaded glue: one reader thread per device → queue → engine →
  dispatcher.
- `cli.py` — typer app, entry point `msfs-bridge`.

## Data flow
hardware → evdev_reader → DeviceEvent → MappingEngine.resolve(active profile)
→ Command (SendEvent/SetSimVar) → BridgeClient → (TCP/JSON) → Wine bridge →
SimConnect → MSFS. The bridge streams the `TITLE` SimVar back for auto-profile.

## Key design properties
- **Pure core:** models, transforms and engine have no I/O, so they are unit
  tested without hardware or a sim (see `tests/`).
- **evdev is optional at import time** — guarded imports keep the package
  importable on non-Linux/CI for the pure tests.
- **Range convention:** transforms output to match the event's expected range,
  usually `-16383..16383`.

See the diagram in [../../README.md](../../README.md#architecture).
