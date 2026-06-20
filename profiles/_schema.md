# Profile schema

Each aircraft profile is one YAML file in `profiles/`. Files starting with
`_` (like this one) are ignored by the loader. Validate with
`uv run msfs-bridge validate`.

```yaml
name: "Human readable profile name"
description: "Optional notes"

# Substrings matched (case-insensitive) against the loaded aircraft's TITLE
# SimVar for auto-selection (`msfs-bridge run --aircraft "<title>"`).
# The longest matching token wins.
aircraft_match:
  - "C172"
  - "Cessna 172"

# device id (from config/devices.yaml) -> list of bindings
bindings:
  tq6:
    - name: "Throttle 1"
      source: { kind: axis, code: 0, raw_min: 0, raw_max: 1023 }
      action: { type: event, event: THROTTLE1_SET }   # axis value -> event data
      transform: { deadzone: 0.02, curve: expo, expo: 0.3, out_min: -16384, out_max: 16384 }

    - name: "Reverser button"
      source: { kind: button, code: 288 }
      action: { type: event, event: THROTTLE1_FULL }   # value defaults to 1 on press
```

## Source `kind`
- `axis`   - continuous. `raw_min`/`raw_max` are optional: when omitted they
  are filled from `config/calibration.yaml` (matched on device id + code) at
  load time. Set them explicitly only to pin a deliberate sub-range (e.g.
  clamping a TQ6+ lever at its detent).
- `button` - press/release; fires on press (value != 0).
- `hat`    - directional; treated like a button per direction code.

## Action types
- `event`  - SimConnect client event (K:/H: event). For axes the shaped value
  becomes the event `data`; for buttons a fixed `value` (default 1) is sent.
- `simvar` - set a SimVar through the MobiFlight WASM channel
  (`{ type: simvar, simvar: "L:Name", unit: number }`).

## Transform pipeline (axes only)
`raw -> normalise [-1,1] -> deadzone -> curve (linear|expo|squared) ->
invert -> rescale to [out_min, out_max]`.

Finding event names: see the MSFS SDK "Event IDs" list and the MobiFlight
event/preset database. SimVars: the SDK "Simulation Variables" reference.
```
