# VirtualFly TQ6+

All-metal 6-lever throttle quadrant by VirtualFly. USB id **`16d0:0da2`**
(confirmed from the udev rules).

## Sensing & mechanics
- **Hall-effect magnetic sensors** on all axes — "life-long", no wear.
- **12-bit resolution** (4096 steps) per axis; **factory-calibrated**, does not
  need calibration (but we should still record observed ranges to be safe).
- ~95 % metallic construction; adjustable lever friction.
- Dimensions: 125.4 × 226 × 172.5 mm. USB plug-and-play, driverless.
- Configurable via VirtualFly's "VFHub" tool on Windows (not needed on Linux —
  raw HID axes are what we read).

## Controls (HID)
**6 analog axes**, one per lever, arranged as a twin-engine quadrant:

| # | Lever | Detent zone | Suggested MSFS event |
|---|-------|-------------|----------------------|
| 1 | Throttle 1 | reverse | `THROTTLE1_SET` / `AXIS_THROTTLE1_SET` |
| 2 | Throttle 2 | reverse | `THROTTLE2_SET` / `AXIS_THROTTLE2_SET` |
| 3 | Prop 1 | feather | `PROP_PITCH1_SET` / `AXIS_PROPELLER1_SET` |
| 4 | Prop 2 | feather | `PROP_PITCH2_SET` / `AXIS_PROPELLER2_SET` |
| 5 | Mixture 1 | cut-off | `MIXTURE1_SET` / `AXIS_MIXTURE1_SET` |
| 6 | Mixture 2 | cut-off | `MIXTURE2_SET` / `AXIS_MIXTURE2_SET` |

The detents (reverse / feather / cut-off) are **mechanical only** — they are not
separate buttons. To react to them, define value thresholds in the transform /
mapping (e.g. bottom 5 % of mixture travel = cut-off → send `MIXTURE1_LEAN` or a
custom event).

## Single-engine aircraft (e.g. C172)
Map only the relevant levers:
- Lever 1 → `THROTTLE1_SET`
- Lever 3 → (no prop on fixed-pitch) — leave unmapped or use for a second func
- Lever 5 → `MIXTURE1_SET`

## Linux / evdev notes
- Appears as a HID joystick with 6 `ABS_*` axes (likely `ABS_X, Y, Z, RX, RY,
  RZ` or `ABS_0..5`). Confirm code↔lever assignment with `msfs-bridge monitor`.
- 12-bit means raw range ≈ `0..4095` (verify; some firmwares report signed).
  Set `raw_min`/`raw_max` from `scan`/`calibrate`, not assumptions.

## Sources
- [TQ6+ product page](https://www.virtual-fly.com/shop/controls/tq6-plus)
- [TQ6 / TQ6+ user manual (manuals.plus)](https://manuals.plus/virtualfly/tq6-and-tq6-plus-flight-sim-throttle-quadrant-manual)
- [User manual (ManualsLib)](https://www.manualslib.com/manual/1485630/Virtualfly-Tq6Plus.html)
