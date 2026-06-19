# Saitek / Logitech Pro Flight Rudder Pedals

Self-centering rudder pedals with differential toe brakes. USB id
**`06a3:0763`**.

## Sensing & mechanics
- Smooth rudder travel with **adjustable damping** (centre tension wheel).
- Self-centering.
- Potentiometer-based — apply a `deadzone` on the rudder centre to avoid creep.

## Controls (HID)
**3 analog axes, no buttons:**

| # | Axis | Use |
|---|------|-----|
| 1 | Rudder (slide left/right) | `RUDDER_SET` / `AXIS_RUDDER_SET` |
| 2 | Left toe brake | `AXIS_LEFT_BRAKE_SET` |
| 3 | Right toe brake | `AXIS_RIGHT_BRAKE_SET` |

The centre rotary wheel adjusts **mechanical tension only** — it is not an axis
and not reported to the PC.

## Mapping notes
- **Rudder:** centred axis → `RUDDER_SET`, range `-16383..16383`, deadzone
  ~0.05.
- **Toe brakes:** unidirectional `0..max`. Map to `AXIS_LEFT_BRAKE_SET` /
  `AXIS_RIGHT_BRAKE_SET` (range `-16383..16383`, where −16383 = no brake).
  Brakes idle at the resting (0) end — verify polarity with `calibrate`, invert
  if pressing the pedal moves the value the wrong way.

## Linux / evdev notes
- Vendor `06a3` already handled by the udev rules.
- Three `ABS_*` axes. The toe-brake axes are sometimes reported as `ABS_Z` /
  `ABS_RZ` and the rudder as `ABS_X` — confirm with `msfs-bridge monitor pedals`.
- Common community gripe: toe-brake axes occasionally not detected by some sims;
  reading raw evdev (as we do) sidesteps that.

## Sources
- [Saitek Pro Flight Rudder Pedals page](https://www.saitek.com/uk/prod-bak/pedals.html)
- [Setting up Pro Flight Rudder pedals (Saitek blog)](https://www.saitek.com/uk/blog/index.php/setting-up-your-pro-flight-rudder-pedals-in-fsx/)
- [GigaParts product spec](https://www.gigaparts.com/saitek-flight-rudder-pedals-professional-simulation-rudder-pedals-with-toe-brake-945-000024.html)
