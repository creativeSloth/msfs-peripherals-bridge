# Sub-memory: Roadmap

Parent: [../../MEMORY.md](../../MEMORY.md)

## Done (2026-06-19)
- Project scaffold: uv + hatchling, ruff + mypy (strict) + pytest, GitHub
  Actions CI, MIT license, README with architecture diagram.
- Data models, transforms, mapping engine, YAML loader, profile auto-select.
- Device tooling: `scan`, `monitor`, `calibrate` (evdev).
- SimConnect Linux client + JSON protocol + `--dry-run` dispatcher.
- Docs: per-device research, full SimVar/event reference, this memory tree.

## Next — high priority
1. **Hardware discovery & calibration** (blocked on devices being connected) —
   see [devices-and-calibration.md](devices-and-calibration.md). Capture real
   axis/button/hat codes + Fulcrum USB id.
2. **Wine SimConnect bridge** (`bridge.exe`) — see
   [simconnect-bridge.md](simconnect-bridge.md). The one big missing runtime
   piece. Include MobiFlight WASM routing for L:/H:/B: vars.

## Next — medium
3. Auto-merge `config/calibration.yaml` into profile axis ranges at runtime so
   profiles don't hard-code `raw_min/raw_max`.
4. Incremental/delta mapping mode for the trim wheel (`ELEV_TRIM_UP/DN`).
5. Hat-switch (`ABS_HAT0X/Y`) handling as discrete directions in the engine.
6. Live profile auto-switch from the streamed `TITLE` SimVar.

## Later
7. Optional GUI/TUI on top of the same models.
8. Feedback channel (read SimVars → device LEDs / displays).
9. H-event / B-event command types in the protocol for add-on aircraft.
