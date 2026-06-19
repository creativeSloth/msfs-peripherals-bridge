# Sub-memory: Profiles

Parent: [../../MEMORY.md](../../MEMORY.md)

## Model
One YAML file per aircraft in `profiles/`. Files prefixed `_` are ignored
(`_schema.md` documents the format). Schema lives in `models.Profile`:
`name`, `description`, `aircraft_match[]`, `bindings{device_id: [Binding]}`.

A `Binding` = `source` (kind axis/button/hat + evdev code + raw range) +
`action` (`event` → K:event, or `simvar` → set) + `transform` (deadzone, curve
linear/expo/squared, invert, out_min/out_max).

## Auto-selection
`loader.select_profile(profiles, aircraft_title)` matches `aircraft_match`
substrings (case-insensitive) against the loaded aircraft's `TITLE` SimVar
streamed back by the bridge; the **longest matching token wins** so a specific
variant beats a generic one. `run --aircraft "<title>"` uses this;
`run --profile <name>` forces one.

## Existing profiles
- `cessna_172.yaml` — full GA mapping across all four devices (axis codes are
  placeholders until calibration).
- `default.yaml` — minimal fallback, never auto-selected (`aircraft_match: []`).

## Buttons vs axes
Axes apply the transform pipeline; buttons/hats fire on press (value != 0),
release ignored. A button→event with no value defaults to sending `1`.
