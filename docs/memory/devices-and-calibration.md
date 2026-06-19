# Sub-memory: Devices & calibration

Parent: [../../MEMORY.md](../../MEMORY.md)

## The four peripherals (see docs/research/ for full specs)
| id | device | USB id | analog axes | digital |
|----|--------|--------|:-----------:|---------|
| `yoke` | Fulcrum One Yoke | **❓ placeholder `0000:0000`** | 2 (pitch, roll) | 8-way hat, 4 buttons, 2 rockers |
| `tq6` | VirtualFly TQ6+ | `16d0:0da2` | 6 levers | mechanical detents only |
| `trim` | Saitek Cessna Trim Wheel | `06a3:0bd4` | 1 (trim) | – |
| `pedals` | Saitek Rudder Pedals | `06a3:0763` | 3 (rudder + 2 toe brakes) | – |

## ⚠️ OPEN TASK — discovery & calibration (blocked on hardware)
As of **2026-06-19** none of the four devices were connected (the machine only
had a Logitech headset + 2 Razer mice/keyboards + a webcam). Before mapping can
be finalised we must, **with the hardware plugged in**:

1. `uv run msfs-bridge scan`
   - confirm each device's real **axis codes**, **ranges**, **button codes** and
     **hat** (`ABS_HAT0X/Y`);
   - capture the **Fulcrum yoke's real USB id** (it is a placeholder now) and
     update both `config/devices.yaml` and `999-flightsim-override.rules`.
2. `uv run msfs-bridge monitor <id>` — identify which code is which physical
   pot/button/hat direction (esp. TQ6+ lever order, pedal toe-brake polarity).
3. `uv run msfs-bridge calibrate <id>` — record raw min/max/center per axis into
   `config/calibration.yaml`; then transcribe ranges into the profile bindings
   (or wire calibration auto-merge — see [roadmap.md](roadmap.md)).

Notes:
- Saitek devices are **potentiometer-based** → add small deadzones, expect drift.
- TQ6+ is Hall-effect, 12-bit, factory-calibrated (still record to be safe).
- Trim wheel: 9 revolutions over one bounded axis → consider delta/incremental
  mapping (`ELEV_TRIM_UP/DN`) rather than absolute.

This is the user's explicit "don't forget" item from 2026-06-19.
