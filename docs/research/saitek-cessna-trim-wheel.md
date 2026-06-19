# Saitek / Logitech Pro Flight Cessna Trim Wheel

Officially licensed Cessna elevator trim wheel. USB id **`06a3:0bd4`**
(vendor `06a3` = Saitek/Logitech).

## Sensing & mechanics
- Replicates the trim wheel of the Cessna 172 / 182.
- **~9 full revolutions** end-to-end to mimic real trim travel.
- 2-position desk clamp.
- Potentiometer-based (older Saitek design) — expect some noise/drift, so a
  small `deadzone`/`fuzz` filter is sensible.

## Controls (HID)
| Control | Type | Count | Use |
|---------|------|:-----:|-----|
| Trim wheel | analog axis | **1** | elevator trim |

That's it — **1 axis, no buttons.**

## Mapping
Two viable strategies:

1. **Absolute axis → trim set** (simplest):
   `ELEVATOR_TRIM_SET` (or `AXIS_ELEV_TRIM_SET`) with the axis value rescaled to
   the trim range. Because the wheel has 9 turns but reports one bounded axis,
   absolute mapping can feel coarse.
2. **Incremental** (often nicer): detect rotation direction/delta and emit
   `ELEV_TRIM_UP` / `ELEV_TRIM_DN` pulses. This needs delta handling in the
   mapping engine (a future enhancement — see `docs/memory/`).

## Linux / evdev notes
- Vendor `06a3` is already covered by the udev rules (`MODE=0666`,
  `ID_INPUT_JOYSTICK=1`, isolated from libinput so it isn't treated as a mouse).
- Single `ABS_*` axis; confirm which code with `msfs-bridge monitor trim`.
- Known quirk: can be flaky when chained through a yoke's USB hub — plug
  **directly into the PC**.

## Sources
- [Saitek Pro Flight Cessna Trim Wheel manual (PDF)](https://www.saitek.com/manuals/cessna%20trim_manual.pdf)
- [FlightGear wiki: Saitek Pro Flight Cessna controls](https://wiki.flightgear.org/Hardware_Review:_Saitek_Pro_Flight_Cessna_controls)
- [Amazon product listing](https://www.amazon.com/Saitek-CES432110002-06-Flight-Cessna/dp/B0058FAFI4)
