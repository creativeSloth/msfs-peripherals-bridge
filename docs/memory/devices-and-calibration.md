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

## TQ6+ lever→code (CONFIRMED 2026-06-19)
Left→right = codes 0–5: **0=Throttle1, 1=Throttle2, 2=Prop1, 3=Prop2,
4=Mixture1, 5=Mixture2** (ABS_X,Y,Z,RX,RY,RZ; user confirmed T1=code0=4096).
Each TQ6 lever has a mechanical **detent** ("0" notch); below it = special
zone (throttle→reverse, prop→feather, mixture→cut-off). These zones do NOT
work via in-game MSFS config (only VirtualFly's VFHub) — so our bridge must
implement them itself from the captured detent raw value. Raw 0/4096 are only
reached at the physical end stops, not at rest.

Turbo Arrow III (PA-28R-201T) context: single piston, constant-speed Hartzell
prop, turbo. No reverse, no feather (single-engine); only **mixture idle
cut-off** detent is functional. Reverse/feather detents matter for twins/turboprops.

## TQ6+ axis geometry (CONFIRMED 2026-06-19, calibrated)
Direction confirmed by the user ("die Null ist vorne"):
- **Forward (push lever forward) = raw ~0 = full power / rich / fine pitch.**
- Pulling back **increases** raw. So the axis is **inverted** vs raw (raw 0 = 100%).
- **Detent ≈ 3260** (~80% of 0..4096) = 0%/idle/lean boundary.
- **Beyond the detent (raw ~3260 → 4096) = special zone:** throttle→reverse,
  prop→feather, mixture→cut-off.

Per-lever calibrated min..max (sweep): all ≈ 3..9 (forward) .. 4086..4096 (back).
Detents (snapshot): all ≈ 3227..3278. Stored in `config/calibration.yaml`.

Implication for mapping (single-engine like C172 / Turbo Arrow III):
- **Throttle**: map raw [0..detent] → 100%..0% (invert), so the reverse zone
  past the detent harmlessly clamps to idle (no reverse on a piston single).
- **Mixture**: map raw [0..max] → 100%..0% (invert); the bottom naturally
  reaches idle cut-off (mixture 0%). Detent is mainly tactile here.
- True reverse/feather/cut-off **events** only matter for twins/turboprops →
  the general "detent-zone action" engine is a future feature (see roadmap).

## ⚠️ STILL OPEN — remaining devices
TQ6 done. Still to capture **with the user moving controls**:
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
