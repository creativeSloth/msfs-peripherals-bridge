# MSFS variable & event reference

A practical catalog of the variables and events you assign hardware to in
MSFS — the same universe SPAD.neXt / MobiFlight / FSUIPC expose when you map a
button or axis. Use it to fill in `action:` blocks in `profiles/*.yaml`.

> This is a curated working reference, not the full SDK. The authoritative,
> always-current lists are the MSFS SDK pages linked at the bottom. When in
> doubt, trust the SDK.

---

## 1. The five kinds of "variable"

| Prefix | Name | Direction | How we reach it | Needs WASM bridge? |
|--------|------|-----------|-----------------|:------------------:|
| `K:` | **Key Event** (event ID) | **write** (trigger an action) | SimConnect `TransmitClientEvent` | no |
| `A:` | **SimVar** (simulation variable) | **read**, some writable | SimConnect data definitions | no |
| `L:` | **Local var** (add-on aircraft) | read/write | WASM module (MobiFlight) | **yes** |
| `H:` | **HTML/JS gauge event** | write (pulse) | WASM module | **yes** |
| `B:` | **Input Event** (MSFS 2020+) | write (`_SET`) | WASM module | **yes** |

In this project:
- a **`{type: event}`** binding sends a `K:` event (the common case for
  throttles, trim, AP buttons, gear, flaps…),
- a **`{type: simvar}`** binding sets a value (used for `L:`/custom vars routed
  through the WASM channel).

**Units & index.** SimVars carry a *unit* (`percent`, `radians`, `knots`,
`bool`, `position 16k`…). Many events/vars are **indexed** for multi-engine
aircraft (`THROTTLE1_SET`, `…2…`; `ENG N1 RPM:1`). The `:N` index selects the
engine/tank/etc.

**Axis events come in two flavours:**
- `ELEVATOR_SET`, `THROTTLE1_SET` — expect **−16383..+16383** (or 0..16383).
- `AXIS_ELEVATOR_SET`, `AXIS_THROTTLE_SET` — the "raw axis" variants, also
  **−16383..+16383**, lower overhead, recommended for continuous axes.

Our `transform.out_min/out_max` should match the event's expected range
(usually `-16383 .. 16383`).

---

## 2. Primary flight controls (axes)

| Function | K: event | Axis variant | Range | Read SimVar (`A:`) | Unit |
|----------|----------|--------------|-------|--------------------|------|
| Aileron | `AILERON_SET` | `AXIS_AILERONS_SET` | ±16383 | `AILERON POSITION` | position |
| Elevator | `ELEVATOR_SET` | `AXIS_ELEVATOR_SET` | ±16383 | `ELEVATOR POSITION` | position |
| Rudder | `RUDDER_SET` | `AXIS_RUDDER_SET` | ±16383 | `RUDDER POSITION` | position |
| Elevator trim | `ELEVATOR_TRIM_SET` / `AXIS_ELEV_TRIM_SET` | – | ±16383 | `ELEVATOR TRIM POSITION` | radians |
| Aileron trim | `AILERON_TRIM_SET` | – | ±16383 | `AILERON TRIM PCT` | percent |
| Rudder trim | `RUDDER_TRIM_SET` | – | ±16383 | `RUDDER TRIM PCT` | percent |

Incremental trim (good for the Saitek trim wheel in delta mode):
`ELEV_TRIM_UP`, `ELEV_TRIM_DN`, `AILERON_TRIM_LEFT/RIGHT`,
`RUDDER_TRIM_LEFT/RIGHT`.

---

## 3. Engine: throttle, prop, mixture (TQ6+)

Indexed `1..4`. Drop the index for the "all engines" version.

| Function | K: event (per engine) | Range | Read SimVar | Unit |
|----------|-----------------------|-------|-------------|------|
| Throttle | `THROTTLE1_SET` … / `AXIS_THROTTLE1_SET` | 0..16383 or ±16383 | `GENERAL ENG THROTTLE LEVER POSITION:1` | percent |
| Prop pitch | `PROP_PITCH1_SET` / `AXIS_PROPELLER1_SET` | ±16383 | `GENERAL ENG PROPELLER LEVER POSITION:1` | percent |
| Mixture | `MIXTURE1_SET` / `AXIS_MIXTURE1_SET` | ±16383 | `GENERAL ENG MIXTURE LEVER POSITION:1` | percent |
| Throttle (all) | `THROTTLE_SET` (0..16383) | 0..16383 | – | – |
| Reverse thrust | `THROTTLE1_FULL` then reverse, or `AXIS_THROTTLE…` into reverse zone | – | `GENERAL ENG REVERSE THRUSTER:1` | bool |

Detent helpers (mapped from threshold zones, not separate switches):
- Mixture cut-off: `MIXTURE1_LEAN` / set value 0, or `MIXTURE_SET` to 0.
- Prop feather: `PROP_PITCH1_LO` / feather button events per aircraft.
- Idle/cutoff & start lever (turboprops) are often **`L:`/`B:` vars** per add-on.

### Engine start / magnetos / fuel
| Function | K: event | SimVar | Unit |
|----------|----------|--------|------|
| Magneto (per eng) | `MAGNETO1_SET` (0=off,1=R,2=L,3=both,4=start) | `RECIP ENG... ` / `MAGNETO SWITCH` | enum |
| Magneto all | `MAGNETO_OFF/_RIGHT/_LEFT/_BOTH/_START` | – | – |
| Starter | `STARTER1_SET` / `TOGGLE_STARTER1` | `GENERAL ENG STARTER:1` | bool |
| Fuel selector | `FUEL_SELECTOR_SET` / `FUEL_SELECTOR_ALL` | `FUEL TANK SELECTOR:1` | enum |
| Fuel pump | `FUEL_PUMP` / `TOGGLE_ELECT_FUEL_PUMP` | `GENERAL ENG FUEL PUMP SWITCH:1` | bool |
| Mixture rich/lean | `MIXTURE_RICH` / `MIXTURE_LEAN` | – | – |

---

## 4. Autopilot

| Function | K: event | SimVar | Unit |
|----------|----------|--------|------|
| AP master | `AP_MASTER` / `TOGGLE_FLIGHT_DIRECTOR` | `AUTOPILOT MASTER` | bool |
| Heading hold | `AP_HDG_HOLD` / `AP_PANEL_HEADING_HOLD` | `AUTOPILOT HEADING LOCK` | bool |
| Heading bug set | `HEADING_BUG_SET` (degrees) | `AUTOPILOT HEADING LOCK DIR` | degrees |
| Heading bug ± step | `HEADING_BUG_INC` / `HEADING_BUG_DEC` | `AUTOPILOT HEADING LOCK DIR` | degrees |
| Altitude hold | `AP_ALT_HOLD` | `AUTOPILOT ALTITUDE LOCK` | bool |
| Altitude set | `AP_ALT_VAR_SET_ENGLISH` (feet) | `AUTOPILOT ALTITUDE LOCK VAR` | feet |
| VS mode / set | `AP_VS_HOLD` / `AP_VS_VAR_SET_ENGLISH` (fpm) | `AUTOPILOT VERTICAL HOLD VAR` | feet/min |
| NAV hold | `AP_NAV1_HOLD` | `AUTOPILOT NAV1 LOCK` | bool |
| Approach | `AP_APR_HOLD` | `AUTOPILOT APPROACH HOLD` | bool |
| Backcourse | `AP_BC_HOLD` | `AUTOPILOT BACKCOURSE HOLD` | bool |
| Speed (FLC) | `AP_SPD_VAR_SET` (knots) | `AUTOPILOT AIRSPEED HOLD VAR` | knots |
| Yaw damper | `YAW_DAMPER_TOGGLE` | `AUTOPILOT YAW DAMPER` | bool |
| Flight director | `TOGGLE_FLIGHT_DIRECTOR` | `AUTOPILOT FLIGHT DIRECTOR ACTIVE` | bool |

**"Heading bug = current heading" (sync).** A common cockpit button (the Arrow's
left rocker-up; in SPAD.neXt the single mapping `AUTOPILOT HEADING LOCK DIR :=
PLANE HEADING DEGREES MAGNETIC`) copies the live magnetic heading into the AP
heading bug. It's a **read-then-set**: read `PLANE HEADING DEGREES MAGNETIC`
(degrees), then `HEADING_BUG_SET` with that value. This is wired in
`piper_arrow.yaml` as the `event_from_var` button action (see
[`profiles/_schema.md`](../profiles/_schema.md)) — just press the button, no
terminal command needed. The bridge reads the heading at press time so it's
always current.

---

## 5. Flaps, spoilers, gear, brakes

| Function | K: event | SimVar | Unit |
|----------|----------|--------|------|
| Flaps up/down (step) | `FLAPS_UP`, `FLAPS_DOWN`, `FLAPS_INCR`, `FLAPS_DECR` | `FLAPS HANDLE INDEX` | number |
| Flaps detent | `FLAPS_1`/`FLAPS_2`/`FLAPS_3`/`FLAPS_UP` | – | – |
| Flaps axis | `AXIS_FLAPS_SET` (±16383) | `TRAILING EDGE FLAPS LEFT PERCENT` | percent |
| Gear toggle/up/down | `GEAR_TOGGLE`, `GEAR_UP`, `GEAR_DOWN` | `GEAR HANDLE POSITION` | bool |
| Parking brake | `PARKING_BRAKES` (toggle) | `BRAKE PARKING POSITION` | bool |
| Brakes (L/R axis) | `AXIS_LEFT_BRAKE_SET`, `AXIS_RIGHT_BRAKE_SET` (±16383) | `BRAKE LEFT POSITION` | position |
| Spoilers/arm | `SPOILERS_TOGGLE`, `SPOILERS_ARM_TOGGLE`, `AXIS_SPOILER_SET` | `SPOILERS HANDLE POSITION` | percent |
| Tailwheel lock | `TOGGLE_TAILWHEEL_LOCK` | `TAILWHEEL LOCK ON` | bool |

---

## 6. Electrical, lights, anti-ice

| Function | K: event | SimVar | Unit |
|----------|----------|--------|------|
| Master battery | `TOGGLE_MASTER_BATTERY` | `ELECTRICAL MASTER BATTERY` | bool |
| Master alternator | `TOGGLE_MASTER_ALTERNATOR` | `GENERAL ENG MASTER ALTERNATOR:1` | bool |
| Avionics master | `AVIONICS_MASTER_SET` / `TOGGLE_AVIONICS_MASTER` | `AVIONICS MASTER SWITCH` | bool |
| Beacon | `TOGGLE_BEACON_LIGHTS` | `LIGHT BEACON` | bool |
| Nav lights | `TOGGLE_NAV_LIGHTS` | `LIGHT NAV` | bool |
| Strobe | `STROBES_TOGGLE` | `LIGHT STROBE` | bool |
| Taxi | `TOGGLE_TAXI_LIGHTS` | `LIGHT TAXI` | bool |
| Landing | `LANDING_LIGHTS_TOGGLE` | `LIGHT LANDING` | bool |
| Panel | `PANEL_LIGHTS_TOGGLE` | `LIGHT PANEL` | bool |
| Pitot heat | `PITOT_HEAT_TOGGLE` | `PITOT HEAT` | bool |
| Anti-ice | `ANTI_ICE_TOGGLE` | `STRUCTURAL DEICE SWITCH` | bool |
| De-ice / prop heat | `TOGGLE_STRUCTURAL_DEICE`, `TOGGLE_PROPELLER_DEICE` | – | bool |

---

## 7. Avionics & radios

| Function | K: event | SimVar | Unit |
|----------|----------|--------|------|
| COM1 standby set | `COM_STBY_RADIO_SET_HZ` | `COM STANDBY FREQUENCY:1` | Hz |
| COM1 swap | `COM_STBY_RADIO_SWAP` | `COM ACTIVE FREQUENCY:1` | MHz |
| COM2 | `COM2_RADIO_SWAP`, `COM2_STBY_RADIO_SET_HZ` | `COM ACTIVE FREQUENCY:2` | MHz |
| NAV1 swap/set | `NAV1_RADIO_SWAP`, `NAV1_STBY_SET_HZ` | `NAV ACTIVE FREQUENCY:1` | MHz |
| Transponder set | `XPNDR_SET` (BCD16) | `TRANSPONDER CODE:1` | number |
| XPDR mode | `XPNDR_STATE_SET` | `TRANSPONDER STATE:1` | enum |
| OBS/CRS | `VOR1_SET` (deg) | `NAV OBS:1` | degrees |
| ADF | `ADF_COMPLETE_SET` | `ADF ACTIVE FREQUENCY:1` | Hz |
| Heading bug | `HEADING_BUG_SET` | `AUTOPILOT HEADING LOCK DIR` | degrees |
| Baro set | `KOHLSMAN_SET` (millibars×16) | `KOHLSMAN SETTING HG` | inHg |

> COM/NAV radios in MSFS often use `…_SET_HZ` (full Hz) for 8.33 kHz spacing.
> Older BCD16 variants exist; prefer the `_HZ` events for new aircraft.

---

## 8. Trim wheel & view (hat switch ideas)

For the **Saitek trim wheel** and the **yoke POV hat**:

| Hardware | Mapping idea |
|----------|--------------|
| Trim wheel (absolute) | `ELEVATOR_TRIM_SET` (±16383) |
| Trim wheel (delta) | `ELEV_TRIM_UP` / `ELEV_TRIM_DN` pulses |
| Yoke hat up/down | `ELEV_TRIM_UP` / `ELEV_TRIM_DN` |
| Yoke hat left/right | `AILERON_TRIM_LEFT` / `_RIGHT`, or view pan |
| Hat (view) | camera events: `VIEW_FORWARD`, `PAN_LEFT/RIGHT/UP/DOWN`, `VIEW_RESET` |

---

## 9. Add-on aircraft (PMDG, Fenix, FBW A320…)

These expose their switches as **`L:`**, **`H:`** or **`B:`** vars, *not* the
generic K: events above. Examples (vary per aircraft):
- FlyByWire A32NX: `L:A32NX_…`, e.g. `A32NX_AUTOPILOT_1_PUSH` (H:event).
- Most glass-cockpit knobs: `H:` events from the JS gauges.

To use them you must:
1. run the **WASM bridge** (MobiFlight WASM module) so `L:/H:/B:` are reachable,
2. map them with a `{type: simvar}` action (for `L:` set) or a dedicated
   H-event command (future extension to the protocol).

Discover the names with MobiFlight's "Variables" explorer or SPAD.neXt's L:Var
browser while that aircraft is loaded.

---

## 10. Finding the exact name for a control

1. **MSFS SDK** → *Event IDs* (K:) and *Simulation Variables* (A:) references.
2. **MobiFlight Event/Preset DB** — community-maintained, searchable, includes
   add-on `L:/H:` presets: <https://hubhop.mobiflight.com>.
3. **SPAD.neXt** L:Var / Event browser (if you also run Windows tooling).
4. In-sim logging via the WASM bridge once it streams variable names.

---

---

## 11. Piper Arrow (JustFlight PA28R Turbo Arrow III) — L:Var catalog

The JF Arrow drives almost everything through **`L:` vars**, not the generic
K:/A: events above. This is the full set the aircraft exposes, enumerated live on
**2026-07-02** via the bridge's `MF.LVars.List` path (714 vars).

**Regenerate** (bridge up, sitting in the JF Arrow, mapper stopped — the bridge is
single-client):

```bash
pkill -f 'msfs_peripherals_bridge[ ]run'        # free the bridge
uv run python tools/list_lvars.py                # all names, sorted
uv run python tools/list_lvars.py radio light     # filter by substring(s)
```

Names come **without** the `L:` prefix (prepend `L:` to read/write). Under the
hood: bridge `{"op":"list_lvars"}` → module `MF.LVars.List` → `MobiFlight.Response`
area, bracketed by the `MF.LVars.List.Start` / `.End` markers.

### Lighting / dimmers
| Light | L:Var | Notes |
|-------|-------|-------|
| Panel (instrument) | `CENTRE_LOWER_panel_light` | **confirmed writable**, scale 0..10; `…_panel_light_on` = on/off flag |
| **Radio LTS (backlight)** | `CENTRE_LOWER_nav_light` | **confirmed writable** (in-sim 2026-07-02), scale 0..10 — the sibling of `panel_light`, despite the misleading name. The cockpit "Radio lts" knob writes this. ⚠️ **also gates the exterior nav lights**: `nav_light_on` follows (dimmer > 0 → on, 0 → off) — the coupling you see when turning the knob. |
| **Center light (red dome)** | `LIGHTING_CABIN_0` (0..100 brightness) **+** `A:LIGHT CABIN` (0/1 gate) | **needs BOTH** (in-sim 2026-07-02) — the one cockpit rotary sets brightness *and* the gate together. `LIGHTING_CABIN_0` alone leaves a residual glow (the gate stays on). Called "Center Light" in the sim. `GENERIC_CIRCUIT_LIGHTS_CABIN` / `switchLtsCabinPass` = unrelated circuit/switch; `CIRCUIT_BREAKERS_lts_ovhd` = overhead CB |
| Pilot / copilot reading | `GENERIC_CIRCUIT_LIGHTS_PILOT`, `GENERIC_CIRCUIT_LIGHTS_COPILOT` | overhead reading lights |
| Instrument-light dimmers | `GENERIC_LIGHTSWITCH_{LEFT_INST,LOWER_INST,ENGINE_INST,COMPASS,RFLT_INST,SIDE_CONSOLE}_1` | per-group light switches |
| Emissive scalers (read-only 0..1 mirrors) | `Panel_light_scaler`, `Radio_light_scaler`, `Yoke_light_scaler`, `GPS_light_scaler`, `GPS100_light_scaler`, `KN62_light_scaler` | computed brightness — see mirror note |
| Exterior | `CENTRE_LOWER_{nav,bcn,anticol,ldg}_light` (+ `nav_light_on` / `nav_light_bounce`) | |

> ⚠️ **Mirrored values — don't chase the wrong one.** Each backlight has **one
> writable master** plus downstream **read-only mirrors** that all move in lockstep,
> so several vars appear to "be" the light. Write the master; the mirrors are not
> independent write targets.
> - **Radio backlight**: master `CENTRE_LOWER_nav_light` (0..10). Mirrors:
>   `Radio_light_scaler` = (nav_light − 1) / 9 (0..1 emissive) and
>   `A:LIGHT POTENTIOMETER:2` ≈ nav_light × 10 (0..100). Verified in-sim: turning the
>   knob moved all three together; `SetSimVar`/`LIGHT_POTENTIOMETER_2_SET` on the
>   A:var/event never moved the light — that was the earlier dead end.
> - **Panel backlight**: master `CENTRE_LOWER_panel_light` (0..10). Mirrors:
>   `Panel_light_scaler` = panel_light / 10 (measured 0.5 at panel_light = 5) and
>   `A:LIGHT POTENTIOMETER:3` = panel_light × 10 (0..100).
> - **Center light**: master brightness `LIGHTING_CABIN_0` (0..100) **plus** its own
>   on/off gate `A:LIGHT CABIN` (0/1) — write **both** (see the Center-light row).
>
> **`A:LIGHT POTENTIOMETER:N` map** (0..100 read-mirrors): `:2` = radio backlight
> (`nav_light`), `:3` = panel light (`panel_light`). `:1`, `:4`, `:5`, `:6` were
> 100/100/50/100 at rest — not yet identified. `GENERIC_LIGHTSWITCH_RADIO_1` /
> `GENERIC_CIRCUIT_LIGHTS_RADIO` stayed 0 throughout — **not** the radio backlight.

### Autopilot (AutoControl IIIB)
| Mode | JF-native bool | Generic mirror |
|------|----------------|----------------|
| Master | `JF_PA28_AP_master` | `AUTOPILOT_onoff`, `A:AUTOPILOT MASTER` |
| Roll | `JF_PA28_AP_roll` | `AUTOPILOT_roll` |
| HDG | `JF_PA28_AP_hdg` | `AUTOPILOT_hdg` |
| NAV | `JF_PA28_AP_nav` | `AUTOPILOT_nav` |
| OMNI | `JF_PA28_AP_omni` | (`AUTOPILOT_mode` = 1) |
| ALT hold | `JF_PA28_AP_alt` | `AUTOPILOT_alt` (+ `AUTOPILOT_alt_up` / `_dn`) |
| VS | `JF_PA28_AP_vs` | `AUTOPILOT_vs` (+ `AUTOPILOT_vs_up` / `_dn`) |
| APR (LOC) | `JF_PA28_AP_loc_norm` | — |
| REV (backcourse) | `JF_PA28_AP_loc_rev` | — |

The **per-mode `JF_PA28_AP_*` bools** are the cleanest LED-read source (one bool
per Multi-Panel button). `AUTOPILOT_mode` is the enum Chunk C currently reads.
`JF_PA28_AP_alt` / `_vs` answer the "hidden ALT/VS modes" roadmap item — each is
both the write target and the LED read.

### Full list (714 L:Vars, sorted, 2026-07-02)
<details><summary>expand — all 714 names</summary>

```text
AC_fan
ADF_card
ADF_knob
ADF_needle
AIRCON_HI_LOW_SWITCH
ALTIMETER_100
ALTIMETER_1000
ALTIMETER_10000
ALTIMETER_baro_knob
ALTIMETER_baro_scale
ALTIMETER_flag
ALT_baro_scale_InHG_vis
ALT_baro_scale_vis
AS04F_HELMET_MOUNTED_DISPLAY_BRIGHTNESS
AS225_Brightness_Manual_1
AS225_Brightness_Manual_2
AS225_Brightness_Manual_3
AS3000_Brightness
AS3000_IsLocalVarDefined
AS3X_Touch_Brightness
AS3X_Touch_Brightness_IsAuto
AS3X_Touch_IsLocalVarDefined
AS430_CDI_Source_1
AS430_ManualBrightness_Enabled_1
AS430_ManualBrightness_Value_1
AS430_MapZoomRange
AS430_SelectedSource
AS530_1_State
AS530_CDI_Source_1
AS530_Default_MapZoomRange
AS530_ManualBrightness_Enabled_1
AS530_ManualBrightness_Value_1
AS530_SelectedSource
ASDigiflo_Brightness
ASI_needle
ASI_tas_knob
ASVigilus_Brightness
ASVigilus_Brightness_Manual
ASVigilus_Fuel_Unit
ASVigilus_Mini_Brightness
ASVigilus_Pressure_Unit
ASVigilus_Temperature_Unit
ASwt430_CDI_Source_1
ASwt530_CDI_Source_1
ATTITUDE_INDICATOR_bank
ATTITUDE_INDICATOR_knob
ATTITUDE_INDICATOR_pitch
ATTITUDE_INDICATOR_turn
AUTOPILOT_alt
AUTOPILOT_alt_dn
AUTOPILOT_alt_up
AUTOPILOT_hdg
AUTOPILOT_mode
AUTOPILOT_nav
AUTOPILOT_onoff
AUTOPILOT_roll
AUTOPILOT_vs
AUTOPILOT_vs_dn
AUTOPILOT_vs_up
Aera_Brightness
Aera_Brightness_Manual
Aera_IsLocalVarDefined
AircraftState
AvionicsPower
Baggage_door
Baggage_flightbag
Baggage_holdall
Baggage_rucksack
CABIN_CALL_KNOB
CABIN_PRESSURIZATION_SWITCH
CENTRE_LOWER_alt
CENTRE_LOWER_anticol_light
CENTRE_LOWER_bat
CENTRE_LOWER_bcn_light
CENTRE_LOWER_fuelpump
CENTRE_LOWER_ldg_light
CENTRE_LOWER_nav_light
CENTRE_LOWER_nav_light_bounce
CENTRE_LOWER_nav_light_on
CENTRE_LOWER_panel_light
CENTRE_LOWER_panel_light_on
CENTRE_LOWER_pitotheat
CIRCUIT_BREAKERS_ac_blower
CIRCUIT_BREAKERS_adf
CIRCUIT_BREAKERS_altntr
CIRCUIT_BREAKERS_anticoll_lts
CIRCUIT_BREAKERS_audio_pnl
CIRCUIT_BREAKERS_autopilot
CIRCUIT_BREAKERS_beacon
CIRCUIT_BREAKERS_com1
CIRCUIT_BREAKERS_com2
CIRCUIT_BREAKERS_dme
CIRCUIT_BREAKERS_engine
CIRCUIT_BREAKERS_fuel_pump
CIRCUIT_BREAKERS_icomm
CIRCUIT_BREAKERS_inst_pnl
CIRCUIT_BREAKERS_ldg_gear_cont
CIRCUIT_BREAKERS_ldg_gear_lts
CIRCUIT_BREAKERS_ldg_lts
CIRCUIT_BREAKERS_lts_ovhd
CIRCUIT_BREAKERS_nav1
CIRCUIT_BREAKERS_nav2
CIRCUIT_BREAKERS_nav_lts
CIRCUIT_BREAKERS_pitch_trim
CIRCUIT_BREAKERS_pitot
CIRCUIT_BREAKERS_radio_lts
CIRCUIT_BREAKERS_stall
CIRCUIT_BREAKERS_start
CIRCUIT_BREAKERS_turn_bank
CIRCUIT_BREAKERS_xpdr
CONTROL_LOCK
Cabin_door
Cabin_door_sound
CoPilot_Vis
CoPilot_enabled
CustomReg_enabled
DHC2_PropSpinner
DHC2_TAB_CANOE
DHC2_TAB_CARGO
DHC2_TAB_CHOCKS
DHC2_TAB_COLDCOVER
DHC2_TAB_HIDE_COPILOT
DHC2_TAB_NAV
DHC2_TAB_PITOTCOVER
DHC2_TAB_RADIOS
DHC2_TAB_SHAKE_OFF
DHC2_TAB_TIEDOWNS
DIRECTION_INDICATOR_bug
DIRECTION_INDICATOR_card
DIRECTION_INDICATOR_card_knob
DOOR_door
DOOR_lower_latch
DOOR_lower_latch_old
DOOR_upper_latch
DOOR_upper_latch_old
Datafield0
Datafield1
Datafield2
Datafield3
EFBArrow3T_ScreenLuminosity
EFBArrow3T_State
EFB_Brt
EFB_HOME_RETURN
EFB_Home_LC
EFB_Home_SC
EFB_On
EFB_POSITION
EFB_PUSH_CHOCKS_1
EFB_PUSH_CHOCKS_2
EFB_PUSH_GPU
EFB_PUSH_PITOT
EFB_PUSH_PLUGS_1
EFB_PUSH_PLUGS_2
EFB_batt
EFB_down_LC
EFB_sound_enabled
EFB_status
EFB_up_LC
EFB_updown
Ext_chocks
Ext_tiedowns
Ext_towbar
FA18_DDI_HSI_BING_MAP_SHOWN
FuelPump_high
GENERIC_CIRCUIT_ADI_1
GENERIC_CIRCUIT_AUDIO_1
GENERIC_CIRCUIT_AUTO_PILOT_COMP
GENERIC_CIRCUIT_CABIN_FAN
GENERIC_CIRCUIT_CABIN_PRESS
GENERIC_CIRCUIT_COMM_NAV_1
GENERIC_CIRCUIT_COMM_NAV_2
GENERIC_CIRCUIT_COND_FAN
GENERIC_CIRCUIT_DME_1
GENERIC_CIRCUIT_DOOR_WARN
GENERIC_CIRCUIT_ELECT_CLOCK
GENERIC_CIRCUIT_ELECT_WSHIELD
GENERIC_CIRCUIT_FLAP
GENERIC_CIRCUIT_GLIDE_SLOPE_1
GENERIC_CIRCUIT_GLIDE_SLOPE_2
GENERIC_CIRCUIT_HOSKINS_FUEL_FLOW
GENERIC_CIRCUIT_LDG_HYD
GENERIC_CIRCUIT_LDG_WARN
GENERIC_CIRCUIT_LH_EVAP
GENERIC_CIRCUIT_LIGHTS_CABIN
GENERIC_CIRCUIT_LIGHTS_COPILOT
GENERIC_CIRCUIT_LIGHTS_PILOT
GENERIC_CIRCUIT_LIGHTS_RADIO
GENERIC_CIRCUIT_LIGHTS_WARN
GENERIC_CIRCUIT_L_ALT
GENERIC_CIRCUIT_L_EGT
GENERIC_CIRCUIT_L_ENG_GAGE
GENERIC_CIRCUIT_L_FUEL_PUMP
GENERIC_CIRCUIT_L_FUEL_QTY
GENERIC_CIRCUIT_L_LDG_GEAR
GENERIC_CIRCUIT_L_LOW_FUEL
GENERIC_CIRCUIT_L_PROP_DEICE
GENERIC_CIRCUIT_NAV_1
GENERIC_CIRCUIT_NAV_2
GENERIC_CIRCUIT_OAT
GENERIC_CIRCUIT_PITOT_1
GENERIC_CIRCUIT_PITOT_2
GENERIC_CIRCUIT_PROP_SYNC
GENERIC_CIRCUIT_RADAR
GENERIC_CIRCUIT_RH_EVAP
GENERIC_CIRCUIT_R_ALT
GENERIC_CIRCUIT_R_EGT
GENERIC_CIRCUIT_R_ENG_GAGE
GENERIC_CIRCUIT_R_FUEL_PUMP
GENERIC_CIRCUIT_R_FUEL_QTY
GENERIC_CIRCUIT_R_LDG_GEAR
GENERIC_CIRCUIT_R_LOW_FUEL
GENERIC_CIRCUIT_R_PROP_DEICE
GENERIC_CIRCUIT_STALL_WARN
GENERIC_CIRCUIT_START
GENERIC_CIRCUIT_SURFACE_DEICE
GENERIC_CIRCUIT_TURN_BANKCIRCUIT_TURN_BANK
GENERIC_CIRCUIT_XPDR_1
GENERIC_CIRCUIT_YAW_DAMPER
GENERIC_LIGHTSWITCH_COMPASS_1
GENERIC_LIGHTSWITCH_ENGINE_INST_1
GENERIC_LIGHTSWITCH_LEFT_INST_1
GENERIC_LIGHTSWITCH_LOWER_INST_1
GENERIC_LIGHTSWITCH_RADIO_1
GENERIC_LIGHTSWITCH_RFLT_INST_1
GENERIC_LIGHTSWITCH_SIDE_CONSOLE_1
GENERIC_Momentary_ADF1_AUDIO_SWITCH
GENERIC_Momentary_ADF2_AUDIO_SWITCH
GENERIC_Momentary_AIRCON_COOL_SWITCH_1
GENERIC_Momentary_CABIN_FAN
GENERIC_Momentary_COM1_AUDIO_SWITCH
GENERIC_Momentary_COM2_AUDIO_SWITCH
GENERIC_Momentary_COM3_AUDIO_SWITCH
GENERIC_Momentary_DAVTRON_SWITCH_FT
GENERIC_Momentary_DME1_AUDIO_SWITCH
GENERIC_Momentary_DME2_AUDIO_SWITCH
GENERIC_Momentary_DME_C1077B_BUTTON_POWER
GENERIC_Momentary_MARKER_AUDIO_SWITCH
GENERIC_Momentary_NAV1_AUDIO_SWITCH
GENERIC_Momentary_NAV2_AUDIO_SWITCH
GLOVEBOX
GNS430_BLANKING_VIZ
GNS430_VIZ
GNS530_VIZ
GPS100_ABC
GPS100_ARROWS
GPS100_AUTOSTO
GPS100_BLANKING_VIZ
GPS100_CLR
GPS100_DEF
GPS100_ENT
GPS100_GHI
GPS100_GOTO
GPS100_JKL
GPS100_MNO
GPS100_MSG
GPS100_NAV
GPS100_OFFON
GPS100_PQR
GPS100_RTE
GPS100_SET
GPS100_STU
GPS100_VIZ
GPS100_VWX
GPS100_WPT
GPS100_YZ
GPS100_ZERO
GPS100_fascia_scaler
GPS100_light_scaler
GPS_light_scaler
GTN650_INT_2_ScreenLuminosity
GTN650_INT_2_State
GTN650_VIZ
GTN650_Vol
GTN750_INT_ScreenLuminosity
GTN750_INT_State
GTN750_VIZ
GTN750_Vol
GYRO_SUCTION_needle
Garmin_Need_OBS_Convert_DirectTo
HANDLING_ElevatorTrim
HDG_click_sync
HOTSPOT_STATIC_WICKS_ELEVATOR_LEFT
HOTSPOT_STATIC_WICKS_ELEVATOR_RIGHT
HOTSPOT_STATIC_WICKS_ELEVATOR_TRIM
HOTSPOT_STATIC_WICKS_LEFT
HOTSPOT_STATIC_WICKS_RIGHT
HOTSPOT_TIE_DOWNS_LEFT
HOTSPOT_TIE_DOWNS_REAR
HOTSPOT_TIE_DOWNS_RIGHT
HSI_CRS_knob
HSI_HDG_tooltip
HSI_card
HSI_cdi
HSI_crs
HSI_enabled
HSI_from_flag
HSI_gsi
HSI_hdg_bug
HSI_hdg_flag
HSI_heading_knob
HSI_nav_flag
HSI_to_flag
HUD_AP_SELECTED_ALTITUDE
HUD_AP_SELECTED_SPEED
Hide_Pilot
INTERCOM_AUDIO_SWITCH
JF_PA28_AP_alt
JF_PA28_AP_hdg
JF_PA28_AP_loc_norm
JF_PA28_AP_loc_rev
JF_PA28_AP_master
JF_PA28_AP_nav
JF_PA28_AP_omni
JF_PA28_AP_roll
JF_PA28_AP_vs
JF_Visor_Position_1
JF_Visor_Position_2
KMA20_VIZ
KMA20_adf
KMA20_auto
KMA20_com1
KMA20_com2
KMA20_dme
KMA20_knob
KMA20_mkr
KMA20_mkr_airway
KMA20_mkr_hilo
KMA20_mkr_middle
KMA20_mkr_outer
KMA20_nav1
KMA20_nav2
KN62_inner_knob
KN62_inner_knob_Push
KN62_light_scaler
KN62_mode_knob
KN62_outer_knob
KN62_power
KR85_dig1_counter
KR85_dig2_counter
KR85_dig3_counter
KR85_left_knob
KR85_mode_knob
KR85_right_inner_knob
KR85_right_outer_knob
KR85_vol_knob
KT76_VIZ
KT76_dig1_counter
KT76_dig1_knob
KT76_dig2_counter
KT76_dig2_knob
KT76_dig3_counter
KT76_dig3_knob
KT76_dig4_counter
KT76_dig4_knob
KT76_ident_button
KT76_ident_button_IsDown
KT76_ident_button_LeftLeaveToRun
KT76_ident_button_MinReleaseTime
KT76_ident_light
KT76_mode_knob
KX170_COMM1_counter1
KX170_COMM1_counter2
KX170_COMM1_counter3
KX170_COMM1_inner_knob
KX170_COMM1_offon
KX170_COMM1_outer_knob
KX170_COMM1_vol_knob
KX170_NAV1_counter1
KX170_NAV1_counter2
KX170_NAV1_inner_knob
KX170_NAV1_offon
KX170_NAV1_outer_knob
KX170_NAV1_vol_knob
KX170_VIZ
KX175_COMM2_counter1
KX175_COMM2_counter2
KX175_COMM2_counter3
KX175_COMM2_inner_knob
KX175_COMM2_offon
KX175_COMM2_outer_knob
KX175_COMM2_vol_knob
KX175_NAV2_counter1
KX175_NAV2_counter2
KX175_NAV2_inner_knob
KX175_NAV2_offon
KX175_NAV2_outer_knob
KX175_NAV2_vol_knob
KX175_VIZ
LDG_GEAR_auto_ext
LDG_GEAR_brt
LDG_GEAR_left_gear
LDG_GEAR_lever
LDG_GEAR_lever_LC
LDG_GEAR_nose_gear
LDG_GEAR_right_gear
LEFT_LOWER_alt_amp
LEFT_LOWER_elec_trim
LEFT_LOWER_fuel_left
LEFT_LOWER_fuel_press
LEFT_LOWER_fuel_right
LEFT_LOWER_fuelflow
LEFT_LOWER_ignition
LEFT_LOWER_ignition_old
LEFT_LOWER_manifold
LEFT_LOWER_oil_press
LEFT_LOWER_oil_temp
LEFT_MISC_alt
LEFT_MISC_boost
LEFT_MISC_elt
LEFT_MISC_fuel_sel
LEFT_MISC_fuel_sel_old
LEFT_MISC_fuelpump
LEFT_MISC_lv
LEFT_MISC_lv_IsDown
LEFT_MISC_lv_LeftLeaveToRun
LEFT_MISC_lv_MinReleaseTime
LEFT_MISC_lv_light
LEFT_MISC_navgps
LEFT_MISC_oil
LEFT_MISC_press_test
LEFT_MISC_press_test_IsDown
LEFT_MISC_press_test_LeftLeaveToRun
LEFT_MISC_press_test_MinReleaseTime
LEFT_MISC_prime
LEFT_MISC_prime_IsDown
LEFT_MISC_prime_LeftLeaveToRun
LEFT_MISC_prime_MinReleaseTime
LEFT_MISC_starter_light
LEFT_MISC_vac
LEFT_MISC_warn_gear
LEFT_MISC_window
LEFT_MISC_window_LC
LEFT_MISC_window_latch
LIGHTING_CABIN_0
LOWER_Paper_chart_L_vis
LOWER_Paper_chart_R_vis
LOWER_emergency_gear
LOWER_flap_handle
LOWER_flap_handle_button
LOWER_park_brake
LOWER_rudder_trim
LOWER_trim_wheel
LeftYoke_hide
Map_BugIndicator_Mode
Oil_door
Oxygen_Needle
Oxygen_Refill
Oxygen_Valve
PA28_EFB_Theme
PMS50_GTN650_INSTALLED
PMS50_GTN750_INSTALLED
PRESSURIZATION_DUMP_LEVER
Panel_light_scaler
Paper_chart_pos
Paper_chart_rotate
Paper_chart_stow
ParkingBrake_Position
Pilot_vis
PitotCovers_vis
RADIO_ANIM_GNS430
RADIO_ANIM_GNS530
RADIO_ANIM_GPS100
RADIO_ANIM_GTN750
RADIO_ANIM_KN62
RADIO_ANIM_KR85
RADIO_ANIM_KX175
RIGHT_LOWER_altair
RIGHT_LOWER_cabin_heat_1
RIGHT_LOWER_cabin_heat_2
RIGHT_LOWER_egt_knob
RIGHT_LOWER_egt_needle
RIGHT_LOWER_egt_red_needle
RIGHT_LOWER_fan
RIGHT_MISC_datcon_dig1
RIGHT_MISC_datcon_dig2
RIGHT_MISC_datcon_dig3
RIGHT_MISC_datcon_dig4
RIGHT_MISC_datcon_dig5
RIGHT_MISC_datcon_dig6
RIGHT_MISC_dme_nav
RIGHT_MISC_icomm
RPM_dig_1
RPM_dig_2
RPM_dig_3
RPM_dig_4
RPM_dig_5
RPM_needle
RUDDER_LOCK_HANDLE
Radio_light_scaler
RightYoke_hide
SAVED_FUEL_QTY_L_pct
SAVED_FUEL_QTY_R_pct
SAVED_PAYLOAD_1_PAX_lbs
SAVED_PAYLOAD_2_PAX_lbs
SAVED_PAYLOAD_3_PAX_lbs
SAVED_PAYLOAD_4_PAX_lbs
SAVED_PAYLOAD_5_PAX_lbs
SAVED_PAYLOAD_6_PAX_lbs
SAVED_PAYLOAD_7_PAX_lbs
SAVED_PAYLOAD_8_PAX_lbs
SAVED_PAYLOAD_CABIN_CARGO_lbs
SAVED_PAYLOAD_CARGO_POD_1_lbs
SAVED_PAYLOAD_CARGO_POD_2_lbs
SAVED_PAYLOAD_CARGO_POD_3_lbs
SAVED_PAYLOAD_CARGO_POD_4_lbs
SAVED_PAYLOAD_COPILOT_lbs
SAVED_PAYLOAD_PILOT_lbs
STATIC_AIR_LEFT
STATIC_AIR_RIGHT
STBY_ALTIMETER_100
STBY_ALTIMETER_1000
STBY_ALTIMETER_10000
STBY_ALTIMETER_baro_knob
STBY_ALTIMETER_baro_scale
STBY_ALTIMETER_flag
STORED_LEFT_FUEL
STORED_RIGHT_FUEL
StallWarn_avail
TDSGTNXI650U2_DTOKey
TDSGTNXI650U2_HomeKey
TDSGTNXI650U2_LKnobCRSR
TDSGTNXI650U2_LKnobDec
TDSGTNXI650U2_LKnobInc
TDSGTNXI650U2_RKnobCRSR
TDSGTNXI650U2_RKnobInnerDec
TDSGTNXI650U2_RKnobInnerInc
TDSGTNXI650U2_RKnobOuterDec
TDSGTNXI650U2_RKnobOuterInc
TDSGTNXI750U1_DTOKey
TDSGTNXI750U1_HomeKey
TDSGTNXI750U1_LKnobCRSR
TDSGTNXI750U1_LKnobDec
TDSGTNXI750U1_LKnobInc
TDSGTNXI750U1_RKnobCRSR
TDSGTNXI750U1_RKnobInnerDec
TDSGTNXI750U1_RKnobInnerInc
TDSGTNXI750U1_RKnobOuterDec
TDSGTNXI750U1_RKnobOuterInc
TDSGTNXI_ACTIVE
TDSGTNXI_GlidePathValueActive
TDSGTNXI_GlidePathValueAngle
TDSGTNXI_GlideRatio
TDSGTNXI_InactiveVar
TDSGTNXI_InstrumentPanelSelfTest
TDSGTNXI_LateralValueActive
TDSGTNXI_ToFromFlag
TDSGTNXI_VGlide
TDS_GTN650_VIZ
TDS_GTN750_VIZ
THROTTLE_QUADRANT_friction
THROTTLE_QUADRANT_mixture_lock
TURN_COORD_flag
TURN_COORD_indicator
Towbar
TrimTab
UPPER_cabin_air
UPPER_compass
UPPER_oat
VOR1_cdi
VOR1_cdi_flag
VOR1_from_flag
VOR1_gsi
VOR1_gsi_flag
VOR1_knob
VOR1_to_flag
VOR2_cdi
VOR2_cdi_flag
VOR2_from_flag
VOR2_knob
VOR2_to_flag
VSI_needle
WT1000_AP_G1000_INSTALLED
WTAP_GP_Distance
WTAP_GP_FPA
WTAP_GP_Required_VS
WTAP_GP_Service_Level
WTAP_GP_Vertical_Deviation
WTAP_LNav_Along_Track_Speed
WTAP_LNav_Course_To_Steer
WTAP_LNav_DTK
WTAP_LNav_Is_Suspended
WTAP_LNav_Is_Tracking
WTAP_LNav_Leg_Distance_Along
WTAP_LNav_Leg_Distance_Remaining
WTAP_LNav_Obs_Active
WTAP_LNav_Obs_Course
WTAP_LNav_Tracked_Leg_Index
WTAP_LNav_Tracked_Vector_Index
WTAP_LNav_Transition_Mode
WTAP_LNav_Vector_Anticipation_Distance
WTAP_LNav_Vector_Distance_Along
WTAP_LNav_Vector_Distance_Remaining
WTAP_LNav_XTK
WTAP_VNAV_Required_VS
WTAP_VNav_Alt_Capture_Type
WTAP_VNav_Target_Altitude
WTGNS_ADSB_OPER
WTGarmin_LNavData_CDI_Scale_Label
WTGarmin_LNavData_Egress_Distance
WTGarmin_LNavData_Next_DTK_Mag
WTGarmin_LNavData_Next_DTK_True
WTGarmin_LNavData_ToFrom
WTT1_INT_ScreenLuminosity
WTT1_INT_State
WTT2_INT_ScreenLuminosity
WTT2_INT_State
WT_AP_FPA_Target:1
WT_GNS430_INSTALLED_1
WT_GNS530_INSTALLED_1
WT_Garmin_External_GPS_Steer_Command_Bank_Angle:0
WT_Garmin_External_GPS_Steer_Command_Dtk:0
WT_Garmin_External_GPS_Steer_Command_Is_Valid:0
WT_Garmin_External_GPS_Steer_Command_Tae:0
WT_Garmin_External_GPS_Steer_Command_Xtk:0
WT_Garmin_External_Glidepath_Approach_Has_Gp:0
WT_Garmin_External_Glidepath_Can_Capture:0
WT_Garmin_External_Glidepath_Is_Valid:0
WT_Garmin_External_VNav_Alt_Capture_Type:0
WT_Garmin_External_VNav_Alt_To_Capture:0
WT_Garmin_External_VNav_Armed_Climb_Mode:0
WT_Garmin_External_VNav_Is_Active:0
WT_Garmin_External_VNav_Path_Deviation:0
WT_Garmin_External_VNav_Path_Fpa:0
WT_Garmin_External_VNav_Path_Mode:0
WT_Garmin_External_VNav_Should_Activate_Climb_Mode:0
WT_Garmin_External_VNav_Should_Capture_Alt:0
WT_Garmin_External_VNav_State:0
WT_Garmin_External_Vertical_Path_Deviation:0
WT_Garmin_External_Vertical_Path_Fpa:0
WT_Garmin_External_Vertical_Path_Is_Valid:0
WT_LNavData_CDI_Scale
WT_LNavData_DTK_Mag
WT_LNavData_DTK_True
WT_LNavData_Destination_Distance
WT_LNavData_Waypoint_Bearing_Mag
WT_LNavData_Waypoint_Bearing_True
WT_LNavData_Waypoint_Distance
WT_LNavData_XTK
WasmInstrument_ScreenLuminosity
WasmInstrument_State
XMLVAR_ADF1_POWER_Position
XMLVAR_AIRCON_COOLER_KNOB_Position
XMLVAR_AS04F_EFD_1_Brightness
XMLVAR_AS04F_HUD_AOA_Indexer
XMLVAR_AS04F_HUD_Balance
XMLVAR_AS04F_HUD_Black_Level
XMLVAR_AS04F_UFCD_1_Brightness
XMLVAR_CABIN_AIR_AFT_Position
XMLVAR_CABIN_AIR_DEFROST_Position
XMLVAR_CABIN_AIR_FWD_Position
XMLVAR_CABIN_AIR_HEAT_Position
XMLVAR_COMM2_POWER_Position
XMLVAR_COPILOT_VISOR_ARM_Position
XMLVAR_COPILOT_VISOR_EXTEND_Position
XMLVAR_COPILOT_VISOR_TILT_Position
XMLVAR_COPILOT_VISOR_TWIST_Position
XMLVAR_GPS_DISABLED_AS430_1
XMLVAR_GPS_DISABLED_AS530_1
XMLVAR_GPS_DISABLED_GTN750
XMLVAR_HEAT_EXCHANGER_HANDLE_LEFT_Position
XMLVAR_HEAT_EXCHANGER_HANDLE_RIGHT_Position
XMLVAR_IE_Throttle_VR_Handled
XMLVAR_IE_Throttle_VR_Value
XMLVAR_LEAR_CABIN_CLIMB_RATE_Position
XMLVAR_LeverFlapsHidden
XMLVAR_LeverMixtureHidden1
XMLVAR_LeverPropellerHidden1
XMLVAR_LeverThrottleHidden1
XMLVAR_Magneto_Starter_IsHeld
XMLVAR_NEXTGEN_FLIGHTPLAN_ENABLED
XMLVAR_PILOT_VISOR_ARM_Position
XMLVAR_PILOT_VISOR_EXTEND_Position
XMLVAR_PILOT_VISOR_TILT_Position
XMLVAR_PILOT_VISOR_TWIST_Position
XMLVAR_PRESSURIZATION_CONTROL_LEFT_Position
XMLVAR_PRESSURIZATION_CONTROL_RIGHT_Position
XMLVAR_PRESSURIZATION_Knob_CabinAltitude_Position
XMLVAR_RCA2610_Screen_Brightness
XMLVAR_VARIOMETER_VOLUME
XMLVAR_VNAVButtonValue
XmsnPressCorr
XmsnPressInit
XmsnTempCorr
YOKE_mode
YOKE_mode_IsDown
YOKE_mode_LeftLeaveToRun
YOKE_mode_MinReleaseTime
YOKE_roll
YOKE_rst
YOKE_rst_IsDown
YOKE_rst_LeftLeaveToRun
YOKE_rst_MinReleaseTime
YOKE_stsp
YOKE_stsp_IsDown
YOKE_stsp_LeftLeaveToRun
YOKE_stsp_MinReleaseTime
YOKE_trim
Yoke_light_scaler
comAdjInit
exhaust
gearPosOld
isCompassDisplayed
isDataFieldActive
oilQty
sound_FuelSel_CW
sound_GearWarn
sound_Switch_Large_Dn
sound_Switch_Small_Up
switchAttGyro
switchAuxSys
switchGenerator
switchLtsCabinPass
switchPrimaryCompassAdjust
switchturnCoord
```
</details>

---

## Sources
- [MSFS SDK — Event IDs](https://docs.flightsimulator.com/html/Programming_Tools/Event_IDs/Event_IDs.htm)
- [MSFS SDK — Simulation Variables](https://docs.flightsimulator.com/html/Programming_Tools/SimVars/Simulation_Variables.htm)
- [SPAD.neXt — L:Vars / H:Events / B:Events](https://docs.spadnext.com/guides-and-videos/videos-lvar-hevents)
- [MobiFlight HubHop preset database](https://hubhop.mobiflight.com)
