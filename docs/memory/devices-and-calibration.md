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

## ▶️ RESUME HERE (paused 2026-06-20) — ALL 4 DEVICES CALIBRATED; 2 follow-ups
**All four devices' hardware calibration is DONE** (TQ6+, pedals, yoke, trim) and
recorded in `config/calibration.yaml`; both profiles `validate` green.
- Trim wheel (Saitek, confirmed 2026-06-20): single axis ABS_X 0..1023, BOUNDED
  (saturates both ends, NO wrap) → absolute mapping. Wheel forward ("nose down")=0,
  back ("nose up")=1023. Pot-based, no self-centre (calibration centre 512 is just
  nominal/unused for absolute mapping). Profile maps raw 0→-16383, 1023→+16383.
- Pedals: rudder ABS_RZ(5)=0..508 centre 252 (full LEFT 0, RIGHT 508); toe brakes
  ABS_X(0)=LEFT, ABS_Y(1)=RIGHT, both 0..127.
- Yoke (Fulcrum, confirmed 2026-06-20): ABS_X(0)=roll 7..4089 rest 2114 (raw 0 =
  full LEFT), ABS_Y(1)=pitch 6..4080 rest 2059 (raw RISES pulling back = nose up,
  so elevator invert:true). Self-centres near the 2047 mid → 0.03 deadzone covers
  it, no centre-aware mapping needed. **8 buttons + hat identified & LABELLED** in
  `config/calibration.yaml` (new `button_labels`/`hat_labels` fields, preserved
  across re-`calibrate`): 288 left-red, 289 left-black, 290/291 left rocker up/down,
  292/293 right grip black lower/upper, 294/295 right rocker left/right. Hat = axes
  16(X: -1 left/+1 right) & 17(Y: -1 up/+1 down), diagonals = X+Y together,
  CENTRE PUSH gives no event. Per user: labels only for now, **sim-event mapping
  comes later**.

▶️ **NEXT: the two follow-ups below** (yoke button sim-mapping + the separation
refactor). Hardware calibration is complete. Heads-up: the trim wheel's event node
re-enumerates (`OSError: [Errno 19] No such device` on a stale path) — re-run, the
catalog re-discovers it by USB id.

`snapshot` bug fixed: it read a stale, frozen `absinfo` value (idle USB HID only
streams once opened for reading), e.g. 506 for a centred rudder. `live_axis_values()`
now wakes the device + drains events like `monitor`. New flag `snapshot --save-center`
saves current positions as axis centres (mirrors `--save-detent`). NOTE: a
*held-steady* axis emits no change events → for "which axis moved" use `monitor`
and PUMP. Also: `calibrate` overwrites the whole button list each run, so a sweep
that misses a button drops it (button 288 was re-added to yoke by hand).

**Follow-ups after the trim wheel (not hardware):**
1. **Map the yoke buttons (288-295) + hat (16/17) to sim events** in
   `profiles/cessna_172.yaml` — codes+labels are captured, functions deferred by
   the user ("nichts jetzt mappen"). NOTE: the hat needs direction-aware mapping
   (one binding currently fires the same event for every hat direction — engine
   work needed if the hat drives trim/views through this bridge).
2. **Refactor the user explicitly asked for:** profiles should hold ONLY the
   semantic mapping (source device+code → SimVar/event + transform); the
   hardware ranges/centre/detent should come from `config/calibration.yaml`,
   merged at load time. Today `runtime.py` never loads calibration.yaml and the
   profile carries its own `raw_min/raw_max` (duplicated). Plan: make
   `Source.raw_min/raw_max` optional overrides, add a merge step in the profile
   loader / `runtime.run` keyed by (device_id, code), engine keeps using the
   resolved range. Calibration data is already captured, so nothing is wasted.

Reminder: run commands via `cd ~/Dokumente/Projekte/msfs-peripherals-bridge &&
uv run msfs-bridge …` over Claude Code's `!`.

Notes:
- Saitek devices are **potentiometer-based** → add small deadzones, expect drift.
- TQ6+ is Hall-effect, 12-bit, factory-calibrated (still record to be safe).
- Trim wheel: 9 revolutions over one bounded axis → consider delta/incremental
  mapping (`ELEV_TRIM_UP/DN`) rather than absolute.

This is the user's explicit "don't forget" item from 2026-06-19.
