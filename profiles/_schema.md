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

## Detent split (axis only)
A lever with a detent (reverse/feather/cutoff) stays ONE binding: `action`/
`transform` cover the range from the detent up, the optional `split` block maps
the range below it to its own action. Each part is normalised over its own raw
span (the detent is out-min of the upper and out-max of the lower part).

```yaml
    - name: "Throttle mit Reverse"
      source: { kind: axis, code: 0 }            # full travel from calibration
      action: { type: event, event: THROTTLE1_SET }
      transform: { out_min: 0, out_max: 16383 }
      split:
        at: 200                                   # raw value of the detent
        action: { type: simvar, simvar: "TURB ENG REVERSE NOZZLE PERCENT:1" }
        transform: { invert: true }
```

## Action types
- `event`  - SimConnect client event (K:/H: event). For axes the shaped value
  becomes the event `data`; for buttons a fixed `value` (default 1) is sent.
- `simvar` - set a SimVar through the MobiFlight WASM channel
  (`{ type: simvar, simvar: "L:Name", unit: number }`).
- `event_from_var` - **dynamic button action**: on press the bridge reads a
  SimVar (in `unit`) and fires `event` with that value. Use it to copy a live
  value, e.g. snap the AP heading bug to the current heading:
  ```yaml
  source: { kind: button, code: 290 }
  action:
    type: event_from_var
    read: "PLANE HEADING DEGREES MAGNETIC"
    unit: degrees
    event: HEADING_BUG_SET
  ```
  The read happens on the bridge at press time, so the value is fresh.

## Transform pipeline (axes only)
`raw -> normalise [-1,1] -> deadzone -> curve (linear|expo|squared) ->
invert -> rescale to [out_min, out_max]`.

Finding event names: see the MSFS SDK "Event IDs" list and the MobiFlight
event/preset database. SimVars: the SDK "Simulation Variables" reference.
```
