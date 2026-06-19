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
| Altitude hold | `AP_ALT_HOLD` | `AUTOPILOT ALTITUDE LOCK` | bool |
| Altitude set | `AP_ALT_VAR_SET_ENGLISH` (feet) | `AUTOPILOT ALTITUDE LOCK VAR` | feet |
| VS mode / set | `AP_VS_HOLD` / `AP_VS_VAR_SET_ENGLISH` (fpm) | `AUTOPILOT VERTICAL HOLD VAR` | feet/min |
| NAV hold | `AP_NAV1_HOLD` | `AUTOPILOT NAV1 LOCK` | bool |
| Approach | `AP_APR_HOLD` | `AUTOPILOT APPROACH HOLD` | bool |
| Backcourse | `AP_BC_HOLD` | `AUTOPILOT BACKCOURSE HOLD` | bool |
| Speed (FLC) | `AP_SPD_VAR_SET` (knots) | `AUTOPILOT AIRSPEED HOLD VAR` | knots |
| Yaw damper | `YAW_DAMPER_TOGGLE` | `AUTOPILOT YAW DAMPER` | bool |
| Flight director | `TOGGLE_FLIGHT_DIRECTOR` | `AUTOPILOT FLIGHT DIRECTOR ACTIVE` | bool |

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

## Sources
- [MSFS SDK — Event IDs](https://docs.flightsimulator.com/html/Programming_Tools/Event_IDs/Event_IDs.htm)
- [MSFS SDK — Simulation Variables](https://docs.flightsimulator.com/html/Programming_Tools/SimVars/Simulation_Variables.htm)
- [SPAD.neXt — L:Vars / H:Events / B:Events](https://docs.spadnext.com/guides-and-videos/videos-lvar-hevents)
- [MobiFlight HubHop preset database](https://hubhop.mobiflight.com)
