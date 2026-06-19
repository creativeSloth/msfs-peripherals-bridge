# Sub-memory: Devices & calibration

Parent: [../../MEMORY.md](../../MEMORY.md)

## The four peripherals (see docs/research/ for full specs)
| id | device | USB id | analog axes | digital |
|----|--------|--------|:-----------:|---------|
| `yoke` | Fulcrum One Yoke | **❓ placeholder `0000:0000`** | 2 (pitch, roll) | 8-way hat, 4 buttons, 2 rockers |
| `tq6` | VirtualFly TQ6+ | `16d0:0da2` | 6 levers | mechanical detents only |
| `trim` | Saitek Cessna Trim Wheel | `06a3:0bd4` | 1 (trim) | – |
| `pedals` | Saitek Rudder Pedals | `06a3:0763` | 3 (rudder + 2 toe brakes) | – |

## ✅ CONFIRMED LAYOUT (scanned 2026-06-19, all 4 connected)
| id | evdev name | USB | axes (code · range · rest) | hats | buttons |
|----|-----------|-----|----------------------------|------|---------|
| `yoke` | Vitaly … Fulcrum One Yoke | **0000:0000** | ABS_X(0) 0–4095 rest 2741 = roll; ABS_Y(1) 0–4095 rest 1870 = pitch | HAT0X, HAT0Y | 8 |
| `tq6` | VirtualFly - TQ6+ | 16d0:0da2 | 6 levers ABS_X..ABS_RZ (codes 0–5), each 0–4096 | – | 0 |
| `trim` | Saitek Pro Flight Cessna Trim Wheel | 06a3:0bd4 | ABS_X(0) 0–1023 | – | 0 |
| `pedals` | Saitek Pro Flight Rudder Pedals | 06a3:0763 | ABS_RZ(5) 0–511 rest 249 = **rudder**; ABS_X(0) & ABS_Y(1) 0–127 = **toe brakes** | – | 0 |

Key facts learned:
- **Fulcrum yoke truly reports 0000:0000** (not a placeholder typo) — shared
  with audio nodes, so the catalog matches it by `name_match: "Fulcrum"`
  (new `DeviceDef.name_match` field + `DeviceDef.matches()`).
- Yoke **rest is off-centre** (roll 2741, pitch 1870 of 0–4095) → needs
  centre-aware calibration, not just min/max.
- Pedals/trim/throttle have **no buttons** → the `scan` heuristic was fixed to
  detect pure-axis controllers (standard joystick axis code < 0x10, or hats).
- TQ6+ sometimes fails to enumerate on first plug; a re-plug fixed it.

## ⚠️ STILL OPEN — semantics + precise calibration
Codes/ranges are known; still to confirm **with the user moving controls**:
1. **TQ6+ lever→function**: which of codes 0–5 is throttle1/2, prop1/2,
   mixture1/2 → `monitor tq6`, move one lever at a time.
2. **Pedals L/R**: which of ABS_X(0)/ABS_Y(1) is left vs right toe brake;
   rudder polarity → `monitor pedals`.
3. **Yoke directions**: pitch/roll invert + hat directions.
4. Then `calibrate <id>` per device for exact min/max/centre.

`profiles/cessna_172.yaml` now uses the confirmed codes/ranges but marks the
lever→function and L/R brake assignments TENTATIVE.

Notes:
- Saitek devices are **potentiometer-based** → add small deadzones, expect drift.
- TQ6+ is Hall-effect, 12-bit, factory-calibrated (still record to be safe).
- Trim wheel: 9 revolutions over one bounded axis → consider delta/incremental
  mapping (`ELEV_TRIM_UP/DN`) rather than absolute.

This is the user's explicit "don't forget" item from 2026-06-19.
