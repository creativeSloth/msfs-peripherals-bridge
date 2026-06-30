# Saitek Pro Flight Multi Panel — HID map (gemessen, Source of Truth)

USB `06a3:0d06`, gelesen/geschrieben über `/dev/hidraw*` (NICHT evdev). Node-Nummer
nicht stabil → per vendor/product entdecken. Empirisch gemessen 2026-06-30 am echten
Gerät (Scan-/Output-Tools), **nicht neu ableiten**. HID-Report-Descriptor bestätigt
die Größen (3 Byte Input; 12 Byte Feature-Output).

## Input — 3-Byte-Report, nur bei Änderung (Leerlauf still)
`code = byte_index * 8 + bit` (wie `hidraw_reader.iter_bit_changes`).

**Byte 0:**
| bit | hex | Funktion |
|----|------|----------|
| 0 | 0x01 | Selector **ALT** |
| 1 | 0x02 | Selector **VS** |
| 2 | 0x04 | Selector **IAS** |
| 3 | 0x08 | Selector **HDG** |
| 4 | 0x10 | Selector **CRS** |
| 5 | 0x20 | großer Encoder **CW** (Tick: ↑ dann ↓) |
| 6 | 0x40 | großer Encoder **CCW** |
| 7 | 0x80 | Taste **AP** |

**Byte 1:**
| bit (global) | hex | Funktion |
|----|------|----------|
| 8  | 0x01 | Taste **HDG** |
| 9  | 0x02 | Taste **NAV** |
| 10 | 0x04 | Taste **IAS** |
| 11 | 0x08 | Taste **ALT** |
| 12 | 0x10 | Taste **VS** |
| 13 | 0x20 | Taste **APR** |
| 14 | 0x40 | Taste **REV** |
| 15 | 0x80 | **AUTO THROTTLE** (ARM; Bit bleibt gesetzt = ein) |

**Byte 2:**
| bit (global) | hex | Funktion |
|----|------|----------|
| 16 | 0x01 | **Flaps UP** (momentary) |
| 17 | 0x02 | **Flaps DOWN** (momentary) |
| 18 | 0x04 | **Trimrad CW/hoch** (Tick) |
| 19 | 0x08 | **Trimrad CCW/runter** (Tick) |

- **Selector** = one-hot Position (Wechsel ALT→VS liefert 2 Events: bit↓ + bit↑).
  → aktueller Selector-Zustand = Encoder-Kontext.
- **Encoder + Trimrad** = 1 Bit-Puls pro Rastung (nur ↑-Flanke werten = 1 Tick).
- **Tasten** = momentary; **AutoThrottle** = Toggle (hält).

## Output — EIN Feature-Report, Report-ID 0, 12 Datenbytes
Buffer für HIDIOCSFEATURE = `[0x00] + 12 Datenbytes` (13 Byte). Gleicher ioctl wie
Switch-Panel-LEDs (`hidraw_reader.write_feature_report`).

**Bytes 0–9: Display** = 10 Stellen, je 1 Byte:
- **0–4 = obere Zeile** (links→rechts), **5–9 = untere Zeile** (links→rechts).
- 5 Ziffern pro Zeile. (Das fixe „6. Zeichen" links jeder Zeile ist nicht ansteuerbar.)
- **Kodierung pro Stelle:** `0x00`–`0x09` = Ziffer 0–9; **`0x0F` = blank** (auch 0x0A–0x0E
  blank); **`0xEE` = Minus**. (Führende Nullen → blank schreiben; VS-negativ → Minus.)

**Byte 10: 8 Tasten-LEDs** (Bitmaske):
| bit | hex | Taste-LED |
|----|------|-----------|
| 0 | 0x01 | AP |
| 1 | 0x02 | HDG |
| 2 | 0x04 | NAV |
| 3 | 0x08 | IAS |
| 4 | 0x10 | ALT |
| 5 | 0x20 | VS |
| 6 | 0x40 | APR |
| 7 | 0x80 | REV |

**Byte 11:** 5 „spare" Bits — **ohne sichtbare Wirkung** (getestet). Das 3-Buchstaben-
Label-Feld im LCD ist **nicht host-steuerbar** (kein Descriptor-Byte dafür). Kontext
kommt über Knopfstellung + leuchtende Mode-Taste.

## SPAD-Recipe (Arrow Turbo.xml, = Funktions-Mapping)
Selector wählt, was Encoder/Display betreffen (SPAD-Schrittweiten normal/Schnelldreh):
| Selector | SimVar | Schritt norm/schnell | Range |
|----------|--------|----------------------|-------|
| ALT | `AUTOPILOT ALTITUDE LOCK VAR` | ±100 / ±1000 | 0…99999 |
| VS  | `AUTOPILOT VERTICAL HOLD VAR` | ±100 / ±1000 | −9999…9999 |
| IAS | `AUTOPILOT AIRSPEED HOLD VAR` | ±1 / ±10 | 0…360 |
| HDG | `AUTOPILOT HEADING LOCK DIR` | ±1 / ±10 | 0…359 (rollover) |
| CRS | `NAV OBS:1` | ±1 / ±10 | 0…359 (rollover) |

Tasten (JF Arrow = eigener LVar-AP):
- **AP** → `K:AP_MASTER` toggle; LED = `A:AUTOPILOT MASTER`.
- **NAV/HDG/APR/REV** → `L:AUTOPILOT_MODE = 0/2/3/4` (+ `L:AUTOPILOT_HDG=1`);
  LED = (`L:AUTOPILOT_MODE` == eigener Wert) UND `A:AUTOPILOT MASTER`.
- **IAS/ALT/VS-Tasten**: in SPAD unbelegt (Arrow-AP hat keine solchen Hold-Modi).
- AUTO THROTTLE → entschieden: `AP_AIRSPEED_HOLD` toggle.
- Flaps-Wippe → UP: `FLAPS_DECR`(kurz)/`FLAPS_UP`(lang); DOWN: `FLAPS_INCR`/`FLAPS_DOWN`.
- (Long-Press-Blink & Pitch-Trim-Encoder: vorerst zurückgestellt.)

LED-Logik der Modus-Tasten braucht **L:AUTOPILOT_MODE gelesen** → LVar-READ-Pfad
(RequestClientData/RECV_CLIENT_DATA über MobiFlight) ist Voraussetzung.
