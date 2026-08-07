# Geräte-Funktionen — Profil `cessna_152`

## Fulcrum One Yoke  
`id=yoke` · USB 0000:0000 · evdev

### Bindings (6)

| Name | Quelle | Aktion | Transform |
|---|---|---|---|
| Aileron (roll) | Achse 0 | event AILERON_SET | dz=0.03, expo=0.25, invert, out[-16383,16383] |
| Elevator (pitch) | Achse 1 | event ELEVATOR_SET | dz=0.03, expo=0.25, invert, out[-16383,16383] |
| ATC window | Taste 288 | event ATC = 1 | — |
| Parking brake | Taste 289 | event PARKING_BRAKES = 1 | — |
| Fuel selector LEFT | Taste 294 | event FUEL_SELECTOR_LEFT = 1 | — |
| Fuel selector RIGHT | Taste 295 | event FUEL_SELECTOR_RIGHT = 1 | — |

### Atomare Elemente (aus Vorlage projiziert) — 6 Inputs · 0 Anzeigen

**Inputs (Lesen):**
- **Aileron (roll)** · Achse code 0
- **Elevator (pitch)** · Achse code 1
- **ATC window** · button code 288
- **Parking brake** · button code 289
- **Fuel selector LEFT** · button code 294
- **Fuel selector RIGHT** · button code 295

---

## VirtualFly TQ6+  
`id=tq6` · USB 16d0:0da2 · evdev

### Bindings (2)

| Name | Quelle | Aktion | Transform |
|---|---|---|---|
| Throttle 1 | Achse 0 | event THROTTLE1_SET | invert, out[-16383,16383] |
| Mixture 1 | Achse 4 | event MIXTURE1_SET | invert, out[-16383,16383] |

### Atomare Elemente (aus Vorlage projiziert) — 2 Inputs · 0 Anzeigen

**Inputs (Lesen):**
- **Throttle 1** · Achse code 0 [0..3260]
- **Mixture 1** · Achse code 4 [0..4096]

---

## Saitek Cessna Trim Wheel  
`id=trim` · USB 06a3:0bd4 · evdev

### Bindings (1)

| Name | Quelle | Aktion | Transform |
|---|---|---|---|
| Elevator trim | Achse 0 | event ELEVATOR_TRIM_SET | out[-16383,16383] |

### Atomare Elemente (aus Vorlage projiziert) — 1 Inputs · 0 Anzeigen

**Inputs (Lesen):**
- **Elevator trim** · Achse code 0

---

## Saitek Pro Flight Rudder Pedals  
`id=pedals` · USB 06a3:0763 · evdev

### Bindings (3)

| Name | Quelle | Aktion | Transform |
|---|---|---|---|
| Rudder | Achse 5 | event RUDDER_SET | dz=0.05, invert, out[-16383,16383] |
| Brake left | Achse 0 | event AXIS_LEFT_BRAKE_SET | out[-16383,16383] |
| Brake right | Achse 1 | event AXIS_RIGHT_BRAKE_SET | out[-16383,16383] |

### Atomare Elemente (aus Vorlage projiziert) — 3 Inputs · 0 Anzeigen

**Inputs (Lesen):**
- **Rudder** · Achse code 5
- **Brake left** · Achse code 0
- **Brake right** · Achse code 1

---


# Geräte-Funktionen — Profil `cessna_172`

## Fulcrum One Yoke  
`id=yoke` · USB 0000:0000 · evdev

### Bindings (6)

| Name | Quelle | Aktion | Transform |
|---|---|---|---|
| Aileron (roll) | Achse 0 | event AILERON_SET | dz=0.03, expo=0.25, invert, out[-16383,16383] |
| Elevator (pitch) | Achse 1 | event ELEVATOR_SET | dz=0.03, expo=0.25, invert, out[-16383,16383] |
| ATC window | Taste 288 | event ATC = 1 | — |
| Parking brake | Taste 289 | event PARKING_BRAKES = 1 | — |
| Fuel selector LEFT | Taste 294 | event FUEL_SELECTOR_LEFT = 1 | — |
| Fuel selector RIGHT | Taste 295 | event FUEL_SELECTOR_RIGHT = 1 | — |

### Atomare Elemente (aus Vorlage projiziert) — 6 Inputs · 0 Anzeigen

**Inputs (Lesen):**
- **Aileron (roll)** · Achse code 0
- **Elevator (pitch)** · Achse code 1
- **ATC window** · button code 288
- **Parking brake** · button code 289
- **Fuel selector LEFT** · button code 294
- **Fuel selector RIGHT** · button code 295

---

## VirtualFly TQ6+  
`id=tq6` · USB 16d0:0da2 · evdev

### Bindings (2)

| Name | Quelle | Aktion | Transform |
|---|---|---|---|
| Throttle 1 | Achse 0 | event THROTTLE1_SET | invert, out[-16383,16383] |
| Mixture 1 | Achse 4 | event MIXTURE1_SET | invert, out[-16383,16383] |

### Atomare Elemente (aus Vorlage projiziert) — 2 Inputs · 0 Anzeigen

**Inputs (Lesen):**
- **Throttle 1** · Achse code 0 [0..3260]
- **Mixture 1** · Achse code 4 [0..4096]

---

## Saitek Cessna Trim Wheel  
`id=trim` · USB 06a3:0bd4 · evdev

### Bindings (1)

| Name | Quelle | Aktion | Transform |
|---|---|---|---|
| Elevator trim | Achse 0 | event ELEVATOR_TRIM_SET | out[-16383,16383] |

### Atomare Elemente (aus Vorlage projiziert) — 1 Inputs · 0 Anzeigen

**Inputs (Lesen):**
- **Elevator trim** · Achse code 0

---

## Saitek Pro Flight Rudder Pedals  
`id=pedals` · USB 06a3:0763 · evdev

### Bindings (3)

| Name | Quelle | Aktion | Transform |
|---|---|---|---|
| Rudder | Achse 5 | event RUDDER_SET | dz=0.05, invert, out[-16383,16383] |
| Brake left | Achse 0 | event AXIS_LEFT_BRAKE_SET | out[-16383,16383] |
| Brake right | Achse 1 | event AXIS_RIGHT_BRAKE_SET | out[-16383,16383] |

### Atomare Elemente (aus Vorlage projiziert) — 3 Inputs · 0 Anzeigen

**Inputs (Lesen):**
- **Rudder** · Achse code 5
- **Brake left** · Achse code 0
- **Brake right** · Achse code 1

---


# Geräte-Funktionen — Profil `default`

## Fulcrum One Yoke  
`id=yoke` · USB 0000:0000 · evdev

### Bindings (2)

| Name | Quelle | Aktion | Transform |
|---|---|---|---|
| Aileron | Achse 0 | event AILERON_SET | dz=0.04, out[-16383,16383] |
| Elevator | Achse 1 | event ELEVATOR_SET | dz=0.04, invert, out[-16383,16383] |

### Atomare Elemente (aus Vorlage projiziert) — 2 Inputs · 0 Anzeigen

**Inputs (Lesen):**
- **Aileron** · Achse code 0
- **Elevator** · Achse code 1

---

## Saitek Pro Flight Rudder Pedals  
`id=pedals` · USB 06a3:0763 · evdev

### Bindings (1)

| Name | Quelle | Aktion | Transform |
|---|---|---|---|
| Rudder | Achse 5 | event RUDDER_SET | dz=0.05, invert, out[-16383,16383] |

### Atomare Elemente (aus Vorlage projiziert) — 1 Inputs · 0 Anzeigen

**Inputs (Lesen):**
- **Rudder** · Achse code 5

---


# Geräte-Funktionen — Profil `piper_arrow`

## Fulcrum One Yoke  
`id=yoke` · USB 0000:0000 · evdev

### Bindings (8)

| Name | Quelle | Aktion | Transform |
|---|---|---|---|
| Aileron (roll) | Achse 0 | event AILERON_SET | dz=0.03, expo=0.25, invert, out[-16383,16383] |
| Elevator (pitch) | Achse 1 | event ELEVATOR_SET | dz=0.03, expo=0.25, invert, out[-16383,16383] |
| ATC window | Taste 288 | event ATC_0 = 1 | — |
| Parking brake | Taste 289 | event PARKING_BRAKES = 1 | — |
| Fuel selector LEFT | Taste 294 | event FUEL_SELECTOR_LEFT = 1 | — |
| Fuel selector RIGHT | Taste 295 | event FUEL_SELECTOR_RIGHT = 1 | — |
| Heading bug = current heading | Taste 290 | HEADING_BUG_SET ← PLANE HEADING DEGREES MAGNETIC | — |
| Blick schwenken (Kopfbewegung) | Hat 16 | Hat: ▲ event PAN_UP · ▼ event PAN_DOWN · ◀ event PAN_LEFT · ▶ event PAN_RIGHT | — |

### Atomare Elemente (aus Vorlage projiziert) — 8 Inputs · 0 Anzeigen

**Inputs (Lesen):**
- **Aileron (roll)** · Achse code 0
- **Elevator (pitch)** · Achse code 1
- **ATC window** · button code 288
- **Parking brake** · button code 289
- **Fuel selector LEFT** · button code 294
- **Fuel selector RIGHT** · button code 295
- **Heading bug = current heading** · button code 290
- **Blick schwenken (Kopfbewegung)** · Selektor [16, 17]

---

## VirtualFly TQ6+  
`id=tq6` · USB 16d0:0da2 · evdev

### Bindings (6)

| Name | Quelle | Aktion | Transform |
|---|---|---|---|
| Throttle 1 | Achse 0 | event THROTTLE1_SET | out[0,16383] |
| Throttle 2 | Achse 1 | event THROTTLE2_SET | out[0,16383] |
| Propeller 1 | Achse 2 | event PROP_PITCH1_SET | out[0,16383] |
| Propeller 2 | Achse 3 | event PROP_PITCH2_SET | out[0,16383] |
| Mixture 1 | Achse 4 | event MIXTURE1_SET | out[0,16384] |
| Mixture 2 | Achse 5 | event MIXTURE2_SET | out[0,16384] |

### Atomare Elemente (aus Vorlage projiziert) — 6 Inputs · 0 Anzeigen

**Inputs (Lesen):**
- **Throttle 1** · Achse code 0 [3273..7]
- **Throttle 2** · Achse code 1 [3276..8]
- **Propeller 1** · Achse code 2 [3254..8]
- **Propeller 2** · Achse code 3 [3267..13]
- **Mixture 1** · Achse code 4 [3233..12]
- **Mixture 2** · Achse code 5 [3257..10]

---

## Saitek Cessna Trim Wheel  
`id=trim` · USB 06a3:0bd4 · evdev

### Bindings (1)

| Name | Quelle | Aktion | Transform |
|---|---|---|---|
| Elevator trim | Achse 0 | event ELEVATOR_TRIM_SET | out[-16383,16383] |

### Atomare Elemente (aus Vorlage projiziert) — 1 Inputs · 0 Anzeigen

**Inputs (Lesen):**
- **Elevator trim** · Achse code 0

---

## Saitek Pro Flight Rudder Pedals  
`id=pedals` · USB 06a3:0763 · evdev

### Bindings (3)

| Name | Quelle | Aktion | Transform |
|---|---|---|---|
| Rudder | Achse 5 | event RUDDER_SET | dz=0.05, invert, out[-16383,16383] |
| Brake left | Achse 0 | event AXIS_LEFT_BRAKE_SET | out[-16383,16383] |
| Brake right | Achse 1 | event AXIS_RIGHT_BRAKE_SET | out[-16383,16383] |

### Atomare Elemente (aus Vorlage projiziert) — 3 Inputs · 0 Anzeigen

**Inputs (Lesen):**
- **Rudder** · Achse code 5
- **Brake left** · Achse code 0
- **Brake right** · Achse code 1

---

## Saitek Pro Flight Switch Panel  
`id=switch_panel` · USB 06a3:0d67 · hidraw

### Bindings (17)

| Name | Quelle | Aktion | Transform |
|---|---|---|---|
| Battery master | Schalter 0 | event MASTER_BATTERY_SET | — |
| Alternator | Schalter 1 | event ALTERNATOR_SET | — |
| Electric fuel pump | Schalter 3 | set L:CENTRE_LOWER_FUELPUMP (invert) | — |
| Avionics master | Schalter 2 | sequence [14]: AVIONICS_MASTER_SET, AVIONICS_MASTER_1_ON … | — |
| De-ice / anti-ice | Schalter 4 | event ANTI_ICE_SET | — |
| Pitot heat | Schalter 5 | event PITOT_HEAT_SET | — |
| Beacon lights | Schalter 8 | event BEACON_LIGHTS_SET | — |
| Strobe lights | Schalter 10 | event STROBES_SET | — |
| Taxi lights | Schalter 11 | event TAXI_LIGHTS_SET | — |
| Landing lights | Schalter 12 | event LANDING_LIGHTS_SET | — |
| Magneto OFF | Schalter 13 | event MAGNETO1_OFF = 1 | — |
| Magneto RIGHT | Schalter 14 | event MAGNETO1_RIGHT = 1 | — |
| Magneto LEFT | Schalter 15 | event MAGNETO1_LEFT = 1 | — |
| Magneto BOTH | Schalter 16 | event MAGNETO1_BOTH = 1 | — |
| Magneto START | Schalter 17 | event MAGNETO1_START = 1 | — |
| Gear up | Schalter 18 | event GEAR_UP = 1 | — |
| Gear down | Schalter 19 | event GEAR_DOWN = 1 | — |

### Anzeigen / Ausgänge (1)

- **gear_leds — 4 SimVars**
  - Rad-LEDs: nose=GEAR CENTER POSITION, left=GEAR LEFT POSITION, right=GEAR RIGHT POSITION
  - grün ab Position 0.95
  - Power-Gate: ELECTRICAL MASTER BATTERY

### Atomare Elemente (aus Vorlage projiziert) — 17 Inputs · 3 Anzeigen

**Inputs (Lesen):**
- **Battery master** · switch code 0
- **Alternator** · switch code 1
- **Electric fuel pump** · switch code 3
- **Avionics master** · switch code 2
- **De-ice / anti-ice** · switch code 4
- **Pitot heat** · switch code 5
- **Beacon lights** · switch code 8
- **Strobe lights** · switch code 10
- **Taxi lights** · switch code 11
- **Landing lights** · switch code 12
- **Magneto OFF** · switch code 13
- **Magneto RIGHT** · switch code 14
- **Magneto LEFT** · switch code 15
- **Magneto BOTH** · switch code 16
- **Magneto START** · switch code 17
- **Gear up** · switch code 18
- **Gear down** · switch code 19

**Anzeigen (Schreiben):**
- **LED Bugrad** · LED
- **LED links** · LED
- **LED rechts** · LED

---

## Saitek Pro Flight Multi Panel  
`id=multi_panel` · USB 06a3:0d06 · hidraw

### Bindings (11)

| Name | Quelle | Aktion | Transform |
|---|---|---|---|
| AP master | Taste 7 | sequence [2]: AP_MASTER, L:AUTOPILOT_MODE | — |
| HDG master arm (auto-throttle switch) | Schalter 15 | sequence [2]: L:AUTOPILOT_HDG | — |
| Flaps up | Schalter 16 | event FLAPS_DECR = 1 | — |
| Flaps down | Schalter 17 | event FLAPS_INCR = 1 | — |
| HDG | Taste 8 | sequence [1]: L:AUTOPILOT_MODE | — |
| NAV | Taste 9 | sequence [1]: L:AUTOPILOT_MODE | — |
| APR | Taste 13 | sequence [1]: L:AUTOPILOT_MODE | — |
| REV | Taste 14 | sequence [1]: L:AUTOPILOT_MODE | — |
| OMNI (IAS button) | Taste 10 | sequence [1]: L:AUTOPILOT_MODE | — |
| ALT hold | Taste 11 | sequence [1]: L:AUTOPILOT_alt | — |
| VS hold | Taste 12 | sequence [1]: L:AUTOPILOT_vs | — |

### Anzeigen / Ausgänge (1)

- **multi_panel — 13 SimVars**
  - Selektor 0 ALT: AUTOPILOT ALTITUDE LOCK VAR [Schritt 100/schnell 300, 0…99999, event AP_ALT_VAR_SET_ENGLISH, Zeile top]
  - Selektor 1 VS: AUTOPILOT VERTICAL HOLD VAR [Schritt 100/schnell 300, -9999…9999, event AP_VS_VAR_SET_ENGLISH, Zeile bottom]
  - Selektor 2 IAS: AUTOPILOT AIRSPEED HOLD VAR [Schritt 1/schnell 3, 0…360, event AP_SPD_VAR_SET, Zeile top]
  - Selektor 3 HDG: AUTOPILOT HEADING LOCK DIR [Schritt 1/schnell 3, 0…359, event HEADING_BUG_SET, Zeile top, rollover]
  - Selektor 4 CRS: NAV OBS:1 [Schritt 1/schnell 3, 0…359, event VOR1_SET, Zeile top, rollover]
  -     ↳ Alt-Quelle NAV OBS:2 (event VOR2_SET)
  - AP-Master-LED: AUTOPILOT MASTER
  - Mode-Var: L:AUTOPILOT_MODE
  - LED alt ← L:JF_PA28_AP_alt
  - LED vs ← L:JF_PA28_AP_vs
  - Quellen-Umschalter: yoke code 291
  - Dimmer (cw 18/ccw 19, 10%): L:CENTRE_LOWER_nav_light, L:CENTRE_LOWER_panel_light
  - Power-Gate: ELECTRICAL MASTER BATTERY

### Atomare Elemente (aus Vorlage projiziert) — 14 Inputs · 9 Anzeigen

**Inputs (Lesen):**
- **AP master** · button code 7
- **HDG master arm (auto-throttle switch)** · switch code 15
- **Flaps up** · switch code 16
- **Flaps down** · switch code 17
- **HDG** · button code 8
- **NAV** · button code 9
- **APR** · button code 13
- **REV** · button code 14
- **OMNI (IAS button)** · button code 10
- **ALT hold** · button code 11
- **VS hold** · button code 12
- **Wert-Encoder** · Encoder (cw 5 / ccw 6)
- **Modus-Wahl** · Selektor [0, 1, 2, 3, 4]
- **Helligkeit** · Encoder (cw 18 / ccw 19)

**Anzeigen (Schreiben):**
- **LED AP** · LED
- **LED HDG** · LED
- **LED NAV** · LED
- **LED IAS** · LED
- **LED ALT** · LED
- **LED VS** · LED
- **LED APR** · LED
- **LED REV** · LED
- **Display** · Display (10 Zellen, 7segment)

---

## Saitek Pro Flight Radio Panel  
`id=radio_panel` · USB 06a3:0d05 · hidraw

### Anzeigen / Ausgänge (1)

- **radio_panel — 37 SimVars**
  - Einheit upper (upper): Encoder outer 18/19, inner 16/17, swap 14
  -     0 COM1 (freq): act=COM ACTIVE FREQUENCY:1, stby=COM STANDBY FREQUENCY:1, swap COM1_RADIO_SWAP, fine-view
  -     1 COM2 (freq): act=COM ACTIVE FREQUENCY:2, stby=COM STANDBY FREQUENCY:2, swap COM2_RADIO_SWAP, fine-view
  -     2 NAV1 (freq): act=NAV ACTIVE FREQUENCY:1, stby=NAV STANDBY FREQUENCY:1, swap NAV1_RADIO_SWAP
  -     3 NAV2 (freq): act=NAV ACTIVE FREQUENCY:2, stby=NAV STANDBY FREQUENCY:2, swap NAV2_RADIO_SWAP
  -     4 ADF (ADF): L:KR85_dig1_counter, L:KR85_dig2_counter, L:KR85_dig3_counter [190…1799 kHz]
  -     5 DME (DME, nur Anzeige): Quellen 1/2, src-var L:RIGHT_MISC_dme_nav
  -     6 XPDR (XPDR): code TRANSPONDER CODE:1, set XPNDR_SET, QNH KOHLSMAN SETTING HG
  - Einheit lower (lower): Encoder outer 22/23, inner 20/21, swap 15
  -     7 COM1 (freq): act=COM ACTIVE FREQUENCY:1, stby=COM STANDBY FREQUENCY:1, swap COM1_RADIO_SWAP, fine-view
  -     8 COM2 (freq): act=COM ACTIVE FREQUENCY:2, stby=COM STANDBY FREQUENCY:2, swap COM2_RADIO_SWAP, fine-view
  -     9 NAV1 (freq): act=NAV ACTIVE FREQUENCY:1, stby=NAV STANDBY FREQUENCY:1, swap NAV1_RADIO_SWAP
  -     10 NAV2 (freq): act=NAV ACTIVE FREQUENCY:2, stby=NAV STANDBY FREQUENCY:2, swap NAV2_RADIO_SWAP
  -     12 DME (DME, nur Anzeige): Quellen 1/2, src-var L:RIGHT_MISC_dme_nav
  -     11 ADF (ADF): L:KR85_dig1_counter, L:KR85_dig2_counter, L:KR85_dig3_counter [190…1799 kHz]
  -     13 XPDR (XPDR): code TRANSPONDER CODE:1, set XPNDR_SET, QNH KOHLSMAN SETTING HG
  - Power-Gate: ELECTRICAL MASTER BATTERY

### Atomare Elemente (aus Vorlage projiziert) — 8 Inputs · 4 Anzeigen

**Inputs (Lesen):**
- **upper · außen** · Encoder (cw 18 / ccw 19)
- **upper · innen** · Encoder (cw 16 / ccw 17)
- **upper · SWAP** · button code 14
- **upper · Modus-Wahl** · Selektor [0, 1, 2, 3, 4, 5, 6]
- **lower · außen** · Encoder (cw 22 / ccw 23)
- **lower · innen** · Encoder (cw 20 / ccw 21)
- **lower · SWAP** · button code 15
- **lower · Modus-Wahl** · Selektor [7, 8, 9, 10, 12, 11, 13]

**Anzeigen (Schreiben):**
- **upper · Aktiv** · Display (5 Zellen, 7segment)
- **upper · Standby** · Display (5 Zellen, 7segment)
- **lower · Aktiv** · Display (5 Zellen, 7segment)
- **lower · Standby** · Display (5 Zellen, 7segment)

---


# Geräte-Funktionen — Profil `piper_arrow_kopie`

## Fulcrum One Yoke  
`id=yoke` · USB 0000:0000 · evdev

### Bindings (7)

| Name | Quelle | Aktion | Transform |
|---|---|---|---|
| Aileron (roll) | Achse 0 | event AILERON_SET | dz=0.03, expo=0.25, invert, out[-16383,16383] |
| Elevator (pitch) | Achse 1 | event ELEVATOR_SET | dz=0.03, expo=0.25, invert, out[-16383,16383] |
| ATC window | Taste 288 | event ATC_0 = 1 | — |
| Parking brake | Taste 289 | event PARKING_BRAKES = 1 | — |
| Fuel selector LEFT | Taste 294 | event FUEL_SELECTOR_LEFT = 1 | — |
| Fuel selector RIGHT | Taste 295 | event FUEL_SELECTOR_RIGHT = 1 | — |
| Heading bug = current heading | Taste 290 | HEADING_BUG_SET ← PLANE HEADING DEGREES MAGNETIC | — |

### Atomare Elemente (aus Vorlage projiziert) — 7 Inputs · 0 Anzeigen

**Inputs (Lesen):**
- **Aileron (roll)** · Achse code 0
- **Elevator (pitch)** · Achse code 1
- **ATC window** · button code 288
- **Parking brake** · button code 289
- **Fuel selector LEFT** · button code 294
- **Fuel selector RIGHT** · button code 295
- **Heading bug = current heading** · button code 290

---

## VirtualFly TQ6+  
`id=tq6` · USB 16d0:0da2 · evdev

### Bindings (3)

| Name | Quelle | Aktion | Transform |
|---|---|---|---|
| Throttle 1 | Achse 0 | event THROTTLE1_SET | invert, out[0,16383] |
| Propeller 1 (RPM) | Achse 2 | event PROP_PITCH1_SET | invert, out[0,16383] |
| Mixture 1 | Achse 4 | event MIXTURE1_SET | invert, out[0,16384] |

### Atomare Elemente (aus Vorlage projiziert) — 3 Inputs · 0 Anzeigen

**Inputs (Lesen):**
- **Throttle 1** · Achse code 0 [0..3275]
- **Propeller 1 (RPM)** · Achse code 2 [0..3261]
- **Mixture 1** · Achse code 4 [0..3227]

---

## Saitek Cessna Trim Wheel  
`id=trim` · USB 06a3:0bd4 · evdev

### Bindings (1)

| Name | Quelle | Aktion | Transform |
|---|---|---|---|
| Elevator trim | Achse 0 | event ELEVATOR_TRIM_SET | out[-16383,16383] |

### Atomare Elemente (aus Vorlage projiziert) — 1 Inputs · 0 Anzeigen

**Inputs (Lesen):**
- **Elevator trim** · Achse code 0

---

## Saitek Pro Flight Rudder Pedals  
`id=pedals` · USB 06a3:0763 · evdev

### Bindings (3)

| Name | Quelle | Aktion | Transform |
|---|---|---|---|
| Rudder | Achse 5 | event RUDDER_SET | dz=0.05, invert, out[-16383,16383] |
| Brake left | Achse 0 | event AXIS_LEFT_BRAKE_SET | out[-16383,16383] |
| Brake right | Achse 1 | event AXIS_RIGHT_BRAKE_SET | out[-16383,16383] |

### Atomare Elemente (aus Vorlage projiziert) — 3 Inputs · 0 Anzeigen

**Inputs (Lesen):**
- **Rudder** · Achse code 5
- **Brake left** · Achse code 0
- **Brake right** · Achse code 1

---

## Saitek Pro Flight Switch Panel  
`id=switch_panel` · USB 06a3:0d67 · hidraw

### Bindings (17)

| Name | Quelle | Aktion | Transform |
|---|---|---|---|
| Battery master | Schalter 0 | event MASTER_BATTERY_SET | — |
| Alternator | Schalter 1 | event ALTERNATOR_SET | — |
| Electric fuel pump | Schalter 3 | set L:CENTRE_LOWER_FUELPUMP (invert) | — |
| Avionics master | Schalter 2 | sequence [14]: AVIONICS_MASTER_SET, AVIONICS_MASTER_1_ON … | — |
| De-ice / anti-ice | Schalter 4 | event ANTI_ICE_SET | — |
| Pitot heat | Schalter 5 | event PITOT_HEAT_SET | — |
| Beacon lights | Schalter 8 | event BEACON_LIGHTS_SET | — |
| Strobe lights | Schalter 10 | event STROBES_SET | — |
| Taxi lights | Schalter 11 | event TAXI_LIGHTS_SET | — |
| Landing lights | Schalter 12 | event LANDING_LIGHTS_SET | — |
| Magneto OFF | Schalter 13 | event MAGNETO1_OFF = 1 | — |
| Magneto RIGHT | Schalter 14 | event MAGNETO1_RIGHT = 1 | — |
| Magneto LEFT | Schalter 15 | event MAGNETO1_LEFT = 1 | — |
| Magneto BOTH | Schalter 16 | event MAGNETO1_BOTH = 1 | — |
| Magneto START | Schalter 17 | event MAGNETO1_START = 1 | — |
| Gear up | Schalter 18 | event GEAR_UP = 1 | — |
| Gear down | Schalter 19 | event GEAR_DOWN = 1 | — |

### Anzeigen / Ausgänge (1)

- **gear_leds — 4 SimVars**
  - Rad-LEDs: nose=GEAR CENTER POSITION, left=GEAR LEFT POSITION, right=GEAR RIGHT POSITION
  - grün ab Position 0.95
  - Power-Gate: ELECTRICAL MASTER BATTERY

### Atomare Elemente (aus Vorlage projiziert) — 17 Inputs · 3 Anzeigen

**Inputs (Lesen):**
- **Battery master** · switch code 0
- **Alternator** · switch code 1
- **Electric fuel pump** · switch code 3
- **Avionics master** · switch code 2
- **De-ice / anti-ice** · switch code 4
- **Pitot heat** · switch code 5
- **Beacon lights** · switch code 8
- **Strobe lights** · switch code 10
- **Taxi lights** · switch code 11
- **Landing lights** · switch code 12
- **Magneto OFF** · switch code 13
- **Magneto RIGHT** · switch code 14
- **Magneto LEFT** · switch code 15
- **Magneto BOTH** · switch code 16
- **Magneto START** · switch code 17
- **Gear up** · switch code 18
- **Gear down** · switch code 19

**Anzeigen (Schreiben):**
- **LED Bugrad** · LED
- **LED links** · LED
- **LED rechts** · LED

---

## Saitek Pro Flight Multi Panel  
`id=multi_panel` · USB 06a3:0d06 · hidraw

### Bindings (11)

| Name | Quelle | Aktion | Transform |
|---|---|---|---|
| AP master | Schalter 7 | sequence [2]: AP_MASTER, L:AUTOPILOT_MODE | — |
| HDG master arm (auto-throttle switch) | Schalter 15 | sequence [2]: L:AUTOPILOT_HDG | — |
| Flaps up | Schalter 16 | event FLAPS_DECR = 1 | — |
| Flaps down | Schalter 17 | event FLAPS_INCR = 1 | — |
| AP mode HDG | Schalter 8 | sequence [1]: L:AUTOPILOT_MODE | — |
| AP mode NAV | Schalter 9 | sequence [1]: L:AUTOPILOT_MODE | — |
| AP mode APR | Schalter 13 | sequence [1]: L:AUTOPILOT_MODE | — |
| AP mode REV | Schalter 14 | sequence [1]: L:AUTOPILOT_MODE | — |
| AP mode OMNI (IAS button) | Schalter 10 | sequence [1]: L:AUTOPILOT_MODE | — |
| AP mode ALT hold | Schalter 11 | sequence [1]: L:AUTOPILOT_alt | — |
| AP mode VS hold | Schalter 12 | sequence [1]: L:AUTOPILOT_vs | — |

### Anzeigen / Ausgänge (1)

- **multi_panel — 13 SimVars**
  - Selektor 0 ALT: AUTOPILOT ALTITUDE LOCK VAR [Schritt 100/schnell 300, 0…99999, event AP_ALT_VAR_SET_ENGLISH, Zeile top]
  - Selektor 1 VS: AUTOPILOT VERTICAL HOLD VAR [Schritt 100/schnell 300, -9999…9999, event AP_VS_VAR_SET_ENGLISH, Zeile bottom]
  - Selektor 2 IAS: AUTOPILOT AIRSPEED HOLD VAR [Schritt 1/schnell 3, 0…360, event AP_SPD_VAR_SET, Zeile top]
  - Selektor 3 HDG: AUTOPILOT HEADING LOCK DIR [Schritt 1/schnell 3, 0…359, event HEADING_BUG_SET, Zeile top, rollover]
  - Selektor 4 CRS: NAV OBS:1 [Schritt 1/schnell 3, 0…359, event VOR1_SET, Zeile top, rollover]
  -     ↳ Alt-Quelle NAV OBS:2 (event VOR2_SET)
  - AP-Master-LED: AUTOPILOT MASTER
  - Mode-Var: L:AUTOPILOT_MODE
  - LED alt ← L:JF_PA28_AP_alt
  - LED vs ← L:JF_PA28_AP_vs
  - Quellen-Umschalter: yoke code 291
  - Dimmer (cw 18/ccw 19, 10%): L:CENTRE_LOWER_nav_light, L:CENTRE_LOWER_panel_light
  - Power-Gate: ELECTRICAL MASTER BATTERY

### Atomare Elemente (aus Vorlage projiziert) — 14 Inputs · 9 Anzeigen

**Inputs (Lesen):**
- **AP master** · switch code 7
- **HDG master arm (auto-throttle switch)** · switch code 15
- **Flaps up** · switch code 16
- **Flaps down** · switch code 17
- **AP mode HDG** · switch code 8
- **AP mode NAV** · switch code 9
- **AP mode APR** · switch code 13
- **AP mode REV** · switch code 14
- **AP mode OMNI (IAS button)** · switch code 10
- **AP mode ALT hold** · switch code 11
- **AP mode VS hold** · switch code 12
- **Wert-Encoder** · Encoder (cw 5 / ccw 6)
- **Modus-Wahl** · Selektor [0, 1, 2, 3, 4]
- **Helligkeit** · Encoder (cw 18 / ccw 19)

**Anzeigen (Schreiben):**
- **LED AP** · LED
- **LED HDG** · LED
- **LED NAV** · LED
- **LED IAS** · LED
- **LED ALT** · LED
- **LED VS** · LED
- **LED APR** · LED
- **LED REV** · LED
- **Display** · Display (10 Zellen, 7segment)

---

## Saitek Pro Flight Radio Panel  
`id=radio_panel` · USB 06a3:0d05 · hidraw

### Anzeigen / Ausgänge (1)

- **radio_panel — 37 SimVars**
  - Einheit upper (upper): Encoder outer 18/19, inner 16/17, swap 14
  -     0 COM1 (freq): act=COM ACTIVE FREQUENCY:1, stby=COM STANDBY FREQUENCY:1, swap COM1_RADIO_SWAP, fine-view
  -     1 COM2 (freq): act=COM ACTIVE FREQUENCY:2, stby=COM STANDBY FREQUENCY:2, swap COM2_RADIO_SWAP, fine-view
  -     2 NAV1 (freq): act=NAV ACTIVE FREQUENCY:1, stby=NAV STANDBY FREQUENCY:1, swap NAV1_RADIO_SWAP
  -     3 NAV2 (freq): act=NAV ACTIVE FREQUENCY:2, stby=NAV STANDBY FREQUENCY:2, swap NAV2_RADIO_SWAP
  -     4 ADF (ADF): L:KR85_dig1_counter, L:KR85_dig2_counter, L:KR85_dig3_counter [190…1799 kHz]
  -     5 DME (DME, nur Anzeige): Quellen 1/2, src-var L:RIGHT_MISC_dme_nav
  -     6 XPDR (XPDR): code TRANSPONDER CODE:1, set XPNDR_SET, QNH KOHLSMAN SETTING HG
  - Einheit lower (lower): Encoder outer 22/23, inner 20/21, swap 15
  -     7 COM1 (freq): act=COM ACTIVE FREQUENCY:1, stby=COM STANDBY FREQUENCY:1, swap COM1_RADIO_SWAP, fine-view
  -     8 COM2 (freq): act=COM ACTIVE FREQUENCY:2, stby=COM STANDBY FREQUENCY:2, swap COM2_RADIO_SWAP, fine-view
  -     9 NAV1 (freq): act=NAV ACTIVE FREQUENCY:1, stby=NAV STANDBY FREQUENCY:1, swap NAV1_RADIO_SWAP
  -     10 NAV2 (freq): act=NAV ACTIVE FREQUENCY:2, stby=NAV STANDBY FREQUENCY:2, swap NAV2_RADIO_SWAP
  -     12 DME (DME, nur Anzeige): Quellen 1/2, src-var L:RIGHT_MISC_dme_nav
  -     11 ADF (ADF): L:KR85_dig1_counter, L:KR85_dig2_counter, L:KR85_dig3_counter [190…1799 kHz]
  -     13 XPDR (XPDR): code TRANSPONDER CODE:1, set XPNDR_SET, QNH KOHLSMAN SETTING HG
  - Power-Gate: ELECTRICAL MASTER BATTERY

### Atomare Elemente (aus Vorlage projiziert) — 8 Inputs · 4 Anzeigen

**Inputs (Lesen):**
- **upper · außen** · Encoder (cw 18 / ccw 19)
- **upper · innen** · Encoder (cw 16 / ccw 17)
- **upper · SWAP** · button code 14
- **upper · Modus-Wahl** · Selektor [0, 1, 2, 3, 4, 5, 6]
- **lower · außen** · Encoder (cw 22 / ccw 23)
- **lower · innen** · Encoder (cw 20 / ccw 21)
- **lower · SWAP** · button code 15
- **lower · Modus-Wahl** · Selektor [7, 8, 9, 10, 12, 11, 13]

**Anzeigen (Schreiben):**
- **upper · Aktiv** · Display (5 Zellen, 7segment)
- **upper · Standby** · Display (5 Zellen, 7segment)
- **lower · Aktiv** · Display (5 Zellen, 7segment)
- **lower · Standby** · Display (5 Zellen, 7segment)

---


# Geräte-Funktionen — Profil `piper_arrow_sicherung`

## Fulcrum One Yoke  
`id=yoke` · USB 0000:0000 · evdev

### Bindings (7)

| Name | Quelle | Aktion | Transform |
|---|---|---|---|
| Aileron (roll) | Achse 0 | event AILERON_SET | dz=0.03, expo=0.25, invert, out[-16383,16383] |
| Elevator (pitch) | Achse 1 | event ELEVATOR_SET | dz=0.03, expo=0.25, invert, out[-16383,16383] |
| ATC window | Taste 288 | event ATC_0 = 1 | — |
| Parking brake | Taste 289 | event PARKING_BRAKES = 1 | — |
| Fuel selector LEFT | Taste 294 | event FUEL_SELECTOR_LEFT = 1 | — |
| Fuel selector RIGHT | Taste 295 | event FUEL_SELECTOR_RIGHT = 1 | — |
| Heading bug = current heading | Taste 290 | HEADING_BUG_SET ← PLANE HEADING DEGREES MAGNETIC | — |

### Atomare Elemente (aus Vorlage projiziert) — 7 Inputs · 0 Anzeigen

**Inputs (Lesen):**
- **Aileron (roll)** · Achse code 0
- **Elevator (pitch)** · Achse code 1
- **ATC window** · button code 288
- **Parking brake** · button code 289
- **Fuel selector LEFT** · button code 294
- **Fuel selector RIGHT** · button code 295
- **Heading bug = current heading** · button code 290

---

## VirtualFly TQ6+  
`id=tq6` · USB 16d0:0da2 · evdev

### Bindings (3)

| Name | Quelle | Aktion | Transform |
|---|---|---|---|
| Throttle 1 | Achse 0 | event THROTTLE1_SET | invert, out[0,16383] |
| Propeller 1 (RPM) | Achse 2 | event PROP_PITCH1_SET | invert, out[0,16383] |
| Mixture 1 | Achse 4 | event MIXTURE1_SET | invert, out[0,16384] |

### Atomare Elemente (aus Vorlage projiziert) — 3 Inputs · 0 Anzeigen

**Inputs (Lesen):**
- **Throttle 1** · Achse code 0 [0..3275]
- **Propeller 1 (RPM)** · Achse code 2 [0..3261]
- **Mixture 1** · Achse code 4 [0..3227]

---

## Saitek Cessna Trim Wheel  
`id=trim` · USB 06a3:0bd4 · evdev

### Bindings (1)

| Name | Quelle | Aktion | Transform |
|---|---|---|---|
| Elevator trim | Achse 0 | event ELEVATOR_TRIM_SET | out[-16383,16383] |

### Atomare Elemente (aus Vorlage projiziert) — 1 Inputs · 0 Anzeigen

**Inputs (Lesen):**
- **Elevator trim** · Achse code 0

---

## Saitek Pro Flight Rudder Pedals  
`id=pedals` · USB 06a3:0763 · evdev

### Bindings (3)

| Name | Quelle | Aktion | Transform |
|---|---|---|---|
| Rudder | Achse 5 | event RUDDER_SET | dz=0.05, invert, out[-16383,16383] |
| Brake left | Achse 0 | event AXIS_LEFT_BRAKE_SET | out[-16383,16383] |
| Brake right | Achse 1 | event AXIS_RIGHT_BRAKE_SET | out[-16383,16383] |

### Atomare Elemente (aus Vorlage projiziert) — 3 Inputs · 0 Anzeigen

**Inputs (Lesen):**
- **Rudder** · Achse code 5
- **Brake left** · Achse code 0
- **Brake right** · Achse code 1

---

## Saitek Pro Flight Switch Panel  
`id=switch_panel` · USB 06a3:0d67 · hidraw

### Bindings (17)

| Name | Quelle | Aktion | Transform |
|---|---|---|---|
| Battery master | Schalter 0 | event MASTER_BATTERY_SET | — |
| Alternator | Schalter 1 | event ALTERNATOR_SET | — |
| Electric fuel pump | Schalter 3 | set L:CENTRE_LOWER_FUELPUMP (invert) | — |
| Avionics master | Schalter 2 | sequence [14]: AVIONICS_MASTER_SET, AVIONICS_MASTER_1_ON … | — |
| De-ice / anti-ice | Schalter 4 | event ANTI_ICE_SET | — |
| Pitot heat | Schalter 5 | event PITOT_HEAT_SET | — |
| Beacon lights | Schalter 8 | event BEACON_LIGHTS_SET | — |
| Strobe lights | Schalter 10 | event STROBES_SET | — |
| Taxi lights | Schalter 11 | event TAXI_LIGHTS_SET | — |
| Landing lights | Schalter 12 | event LANDING_LIGHTS_SET | — |
| Magneto OFF | Schalter 13 | event MAGNETO1_OFF = 1 | — |
| Magneto RIGHT | Schalter 14 | event MAGNETO1_RIGHT = 1 | — |
| Magneto LEFT | Schalter 15 | event MAGNETO1_LEFT = 1 | — |
| Magneto BOTH | Schalter 16 | event MAGNETO1_BOTH = 1 | — |
| Magneto START | Schalter 17 | event MAGNETO1_START = 1 | — |
| Gear up | Schalter 18 | event GEAR_UP = 1 | — |
| Gear down | Schalter 19 | event GEAR_DOWN = 1 | — |

### Anzeigen / Ausgänge (1)

- **gear_leds — 4 SimVars**
  - Rad-LEDs: nose=GEAR CENTER POSITION, left=GEAR LEFT POSITION, right=GEAR RIGHT POSITION
  - grün ab Position 0.95
  - Power-Gate: ELECTRICAL MASTER BATTERY

### Atomare Elemente (aus Vorlage projiziert) — 17 Inputs · 3 Anzeigen

**Inputs (Lesen):**
- **Battery master** · switch code 0
- **Alternator** · switch code 1
- **Electric fuel pump** · switch code 3
- **Avionics master** · switch code 2
- **De-ice / anti-ice** · switch code 4
- **Pitot heat** · switch code 5
- **Beacon lights** · switch code 8
- **Strobe lights** · switch code 10
- **Taxi lights** · switch code 11
- **Landing lights** · switch code 12
- **Magneto OFF** · switch code 13
- **Magneto RIGHT** · switch code 14
- **Magneto LEFT** · switch code 15
- **Magneto BOTH** · switch code 16
- **Magneto START** · switch code 17
- **Gear up** · switch code 18
- **Gear down** · switch code 19

**Anzeigen (Schreiben):**
- **LED Bugrad** · LED
- **LED links** · LED
- **LED rechts** · LED

---

## Saitek Pro Flight Multi Panel  
`id=multi_panel` · USB 06a3:0d06 · hidraw

### Bindings (11)

| Name | Quelle | Aktion | Transform |
|---|---|---|---|
| AP master | Schalter 7 | sequence [2]: AP_MASTER, L:AUTOPILOT_MODE | — |
| HDG master arm (auto-throttle switch) | Schalter 15 | sequence [2]: L:AUTOPILOT_HDG | — |
| Flaps up | Schalter 16 | event FLAPS_DECR = 1 | — |
| Flaps down | Schalter 17 | event FLAPS_INCR = 1 | — |
| AP mode HDG | Schalter 8 | sequence [1]: L:AUTOPILOT_MODE | — |
| AP mode NAV | Schalter 9 | sequence [1]: L:AUTOPILOT_MODE | — |
| AP mode APR | Schalter 13 | sequence [1]: L:AUTOPILOT_MODE | — |
| AP mode REV | Schalter 14 | sequence [1]: L:AUTOPILOT_MODE | — |
| AP mode OMNI (IAS button) | Schalter 10 | sequence [1]: L:AUTOPILOT_MODE | — |
| AP mode ALT hold | Schalter 11 | sequence [1]: L:AUTOPILOT_alt | — |
| AP mode VS hold | Schalter 12 | sequence [1]: L:AUTOPILOT_vs | — |

### Anzeigen / Ausgänge (1)

- **multi_panel — 13 SimVars**
  - Selektor 0 ALT: AUTOPILOT ALTITUDE LOCK VAR [Schritt 100/schnell 300, 0…99999, event AP_ALT_VAR_SET_ENGLISH, Zeile top]
  - Selektor 1 VS: AUTOPILOT VERTICAL HOLD VAR [Schritt 100/schnell 300, -9999…9999, event AP_VS_VAR_SET_ENGLISH, Zeile bottom]
  - Selektor 2 IAS: AUTOPILOT AIRSPEED HOLD VAR [Schritt 1/schnell 3, 0…360, event AP_SPD_VAR_SET, Zeile top]
  - Selektor 3 HDG: AUTOPILOT HEADING LOCK DIR [Schritt 1/schnell 3, 0…359, event HEADING_BUG_SET, Zeile top, rollover]
  - Selektor 4 CRS: NAV OBS:1 [Schritt 1/schnell 3, 0…359, event VOR1_SET, Zeile top, rollover]
  -     ↳ Alt-Quelle NAV OBS:2 (event VOR2_SET)
  - AP-Master-LED: AUTOPILOT MASTER
  - Mode-Var: L:AUTOPILOT_MODE
  - LED alt ← L:JF_PA28_AP_alt
  - LED vs ← L:JF_PA28_AP_vs
  - Quellen-Umschalter: yoke code 291
  - Dimmer (cw 18/ccw 19, 10%): L:CENTRE_LOWER_nav_light, L:CENTRE_LOWER_panel_light
  - Power-Gate: ELECTRICAL MASTER BATTERY

### Atomare Elemente (aus Vorlage projiziert) — 14 Inputs · 9 Anzeigen

**Inputs (Lesen):**
- **AP master** · switch code 7
- **HDG master arm (auto-throttle switch)** · switch code 15
- **Flaps up** · switch code 16
- **Flaps down** · switch code 17
- **AP mode HDG** · switch code 8
- **AP mode NAV** · switch code 9
- **AP mode APR** · switch code 13
- **AP mode REV** · switch code 14
- **AP mode OMNI (IAS button)** · switch code 10
- **AP mode ALT hold** · switch code 11
- **AP mode VS hold** · switch code 12
- **Wert-Encoder** · Encoder (cw 5 / ccw 6)
- **Modus-Wahl** · Selektor [0, 1, 2, 3, 4]
- **Helligkeit** · Encoder (cw 18 / ccw 19)

**Anzeigen (Schreiben):**
- **LED AP** · LED
- **LED HDG** · LED
- **LED NAV** · LED
- **LED IAS** · LED
- **LED ALT** · LED
- **LED VS** · LED
- **LED APR** · LED
- **LED REV** · LED
- **Display** · Display (10 Zellen, 7segment)

---

## Saitek Pro Flight Radio Panel  
`id=radio_panel` · USB 06a3:0d05 · hidraw

### Anzeigen / Ausgänge (1)

- **radio_panel — 37 SimVars**
  - Einheit upper (upper): Encoder outer 18/19, inner 16/17, swap 14
  -     0 COM1 (freq): act=COM ACTIVE FREQUENCY:1, stby=COM STANDBY FREQUENCY:1, swap COM1_RADIO_SWAP, fine-view
  -     1 COM2 (freq): act=COM ACTIVE FREQUENCY:2, stby=COM STANDBY FREQUENCY:2, swap COM2_RADIO_SWAP, fine-view
  -     2 NAV1 (freq): act=NAV ACTIVE FREQUENCY:1, stby=NAV STANDBY FREQUENCY:1, swap NAV1_RADIO_SWAP
  -     3 NAV2 (freq): act=NAV ACTIVE FREQUENCY:2, stby=NAV STANDBY FREQUENCY:2, swap NAV2_RADIO_SWAP
  -     4 ADF (ADF): L:KR85_dig1_counter, L:KR85_dig2_counter, L:KR85_dig3_counter [190…1799 kHz]
  -     5 DME (DME, nur Anzeige): Quellen 1/2, src-var L:RIGHT_MISC_dme_nav
  -     6 XPDR (XPDR): code TRANSPONDER CODE:1, set XPNDR_SET, QNH KOHLSMAN SETTING HG
  - Einheit lower (lower): Encoder outer 22/23, inner 20/21, swap 15
  -     7 COM1 (freq): act=COM ACTIVE FREQUENCY:1, stby=COM STANDBY FREQUENCY:1, swap COM1_RADIO_SWAP, fine-view
  -     8 COM2 (freq): act=COM ACTIVE FREQUENCY:2, stby=COM STANDBY FREQUENCY:2, swap COM2_RADIO_SWAP, fine-view
  -     9 NAV1 (freq): act=NAV ACTIVE FREQUENCY:1, stby=NAV STANDBY FREQUENCY:1, swap NAV1_RADIO_SWAP
  -     10 NAV2 (freq): act=NAV ACTIVE FREQUENCY:2, stby=NAV STANDBY FREQUENCY:2, swap NAV2_RADIO_SWAP
  -     12 DME (DME, nur Anzeige): Quellen 1/2, src-var L:RIGHT_MISC_dme_nav
  -     11 ADF (ADF): L:KR85_dig1_counter, L:KR85_dig2_counter, L:KR85_dig3_counter [190…1799 kHz]
  -     13 XPDR (XPDR): code TRANSPONDER CODE:1, set XPNDR_SET, QNH KOHLSMAN SETTING HG
  - Power-Gate: ELECTRICAL MASTER BATTERY

### Atomare Elemente (aus Vorlage projiziert) — 8 Inputs · 4 Anzeigen

**Inputs (Lesen):**
- **upper · außen** · Encoder (cw 18 / ccw 19)
- **upper · innen** · Encoder (cw 16 / ccw 17)
- **upper · SWAP** · button code 14
- **upper · Modus-Wahl** · Selektor [0, 1, 2, 3, 4, 5, 6]
- **lower · außen** · Encoder (cw 22 / ccw 23)
- **lower · innen** · Encoder (cw 20 / ccw 21)
- **lower · SWAP** · button code 15
- **lower · Modus-Wahl** · Selektor [7, 8, 9, 10, 12, 11, 13]

**Anzeigen (Schreiben):**
- **upper · Aktiv** · Display (5 Zellen, 7segment)
- **upper · Standby** · Display (5 Zellen, 7segment)
- **lower · Aktiv** · Display (5 Zellen, 7segment)
- **lower · Standby** · Display (5 Zellen, 7segment)

---


# Geräte-Funktionen — Profil `test`

## Saitek Pro Flight Multi Panel  
`id=multi_panel` · USB 06a3:0d06 · hidraw

### Anzeigen / Ausgänge (4)

- **multi_panel — 3 SimVars**
  - Selektor 0 ALT: AUTOPILOT ALTITUDE LOCK VAR [Schritt 1, 0…99999, SimVar-Write, Zeile top]
  - AP-Master-LED: AUTOPILOT MASTER
  - Mode-Var: L:AUTOPILOT_MODE
- **multi_panel — 3 SimVars**
  - Selektor 0 ALT: AUTOPILOT ALTITUDE LOCK VAR [Schritt 1, 0…99999, SimVar-Write, Zeile top]
  - AP-Master-LED: AUTOPILOT MASTER
  - Mode-Var: L:AUTOPILOT_MODE
- **multi_panel — 3 SimVars**
  - Selektor 0 ALT: AUTOPILOT ALTITUDE LOCK VAR [Schritt 1, 0…99999, SimVar-Write, Zeile top]
  - AP-Master-LED: AUTOPILOT MASTER
  - Mode-Var: L:AUTOPILOT_MODE
- **multi_panel — 3 SimVars**
  - Selektor 0 ALT: AUTOPILOT ALTITUDE LOCK VAR [Schritt 1, 0…99999, SimVar-Write, Zeile top]
  - AP-Master-LED: AUTOPILOT MASTER
  - Mode-Var: L:AUTOPILOT_MODE

### Atomare Elemente (aus Vorlage projiziert) — 8 Inputs · 36 Anzeigen

**Inputs (Lesen):**
- **Wert-Encoder** · Encoder (cw 5 / ccw 6)
- **Modus-Wahl** · Selektor [0]
- **Wert-Encoder** · Encoder (cw 5 / ccw 6)
- **Modus-Wahl** · Selektor [0]
- **Wert-Encoder** · Encoder (cw 5 / ccw 6)
- **Modus-Wahl** · Selektor [0]
- **Wert-Encoder** · Encoder (cw 5 / ccw 6)
- **Modus-Wahl** · Selektor [0]

**Anzeigen (Schreiben):**
- **LED AP** · LED
- **LED HDG** · LED
- **LED NAV** · LED
- **LED IAS** · LED
- **LED ALT** · LED
- **LED VS** · LED
- **LED APR** · LED
- **LED REV** · LED
- **Display** · Display (10 Zellen, 7segment)
- **LED AP** · LED
- **LED HDG** · LED
- **LED NAV** · LED
- **LED IAS** · LED
- **LED ALT** · LED
- **LED VS** · LED
- **LED APR** · LED
- **LED REV** · LED
- **Display** · Display (10 Zellen, 7segment)
- **LED AP** · LED
- **LED HDG** · LED
- **LED NAV** · LED
- **LED IAS** · LED
- **LED ALT** · LED
- **LED VS** · LED
- **LED APR** · LED
- **LED REV** · LED
- **Display** · Display (10 Zellen, 7segment)
- **LED AP** · LED
- **LED HDG** · LED
- **LED NAV** · LED
- **LED IAS** · LED
- **LED ALT** · LED
- **LED VS** · LED
- **LED APR** · LED
- **LED REV** · LED
- **Display** · Display (10 Zellen, 7segment)

---

## Razer Razer Huntsman V2  
`id=razer_razer_huntsman_v2` · USB 1532:026c · hidraw

### Bindings (1)

| Name | Quelle | Aktion | Transform |
|---|---|---|---|
| test | Taste 0 | event FUEL_SELECTOR_LEFT = 1 | — |

### Atomare Elemente (aus Vorlage projiziert) — 1 Inputs · 0 Anzeigen

**Inputs (Lesen):**
- **test** · button code 0

---


