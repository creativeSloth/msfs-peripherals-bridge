# Saitek Pro Flight Radio Panel — HID-Map (Recherche-Stand)

> Stand 2026-06-30. **Aus dem HID-Report-Deskriptor der Hardware abgeleitet**
> (exakt, kein Raten) — die genaue Bit-Zuordnung der Eingänge muss noch wie beim
> Multi Panel am Gerät **gemessen** werden (scan-Tool). Display-Bytes folgen der
> bekannten Saitek-Kodierung (siehe `mapping/display.py`).

## Identität
- USB **06a3:0d05** „Saitek Pro Flight Radio Panel", hidraw = **/dev/hidraw11**
  (Zuordnung kann nach Replug wechseln → über VID:PID/`HID_ID` auflösen).
- Report-Deskriptor (63 B) dekodiert:
  - **INPUT: 3 Byte = 24 Button-Bits** (`Report Size 1 × Count 24`, Usage Page
    Button 1..24). Hier stecken: 2 Mode-Selektoren, 4 Encoder (CW/CCW), 2 Tasten.
  - **FEATURE (write) #1: 20 Byte** (`Size 8 × Count 20`) = die **20 Ziffern**
    der zwei Displays.
  - **FEATURE #2: 14 Bit** (`Size 1 × Count 14`) + 2 Bit Padding = 2 Byte
    Steuer-/Flag-Bits (vmtl. Helligkeit/Segment-Extras — am Gerät prüfen).
  - Kein Report-ID im Deskriptor → beim `HIDIOCSFEATURE`-ioctl Report-Nr. **0**
    voranstellen ⇒ Schreibpuffer = `[0x00] + 20 Ziffern + 2 Flag-Byte = 23 B`.

## Eingänge (INPUT, 3 Byte / 24 Bits) — STRUKTUR sicher, BITS messen
Erwartete Belegung (Summe passt exakt auf 24):
- **Oberer Mode-Selektor**: 7 Positionen one-hot — COM1, COM2, NAV1, NAV2, ADF,
  DME, XPDR (7 Bits).
- **Unterer Mode-Selektor**: dieselben 7 Positionen one-hot (7 Bits).
- **4 Encoder** (je Radio ein großer/äußerer + kleiner/innerer Knopf):
  je CW + CCW = 8 Bits.
- **2 ACT/STBY-Tasten** (oberes + unteres Radio, drückbarer Encoder) = 2 Bits.
- ⇒ 7+7+8+2 = **24**. ✅ **TODO: exakte Bit-Indizes mit dem scan-Tool messen**
  (wie Multi Panel, Befund nach `multi-panel-hid.md`-Schema hier eintragen).

## Ausgänge / Display (FEATURE, 20 Ziffern)
Zwei physische Displays, je 2 Zeilen à 5 Sieben-Segment-Ziffern:
- Byte **0–4**  = oberes Display, obere Zeile  → **oberes Radio ACTIVE**
- Byte **5–9**  = oberes Display, untere Zeile  → **oberes Radio STANDBY**
- Byte **10–14**= unteres Display, obere Zeile  → **unteres Radio ACTIVE**
- Byte **15–19**= unteres Display, untere Zeile → **unteres Radio STANDBY**

Ziffern-Kodierung = identisch zum Multi Panel ⇒ **`mapping/display.py`
wiederverwenden** (`format_row`/`display_cells`):
- `0x00..0x09` = Ziffer 0–9, `0x0F` = blank, `0xEE` = Minus.
- **Dezimalpunkt** (COM/NAV brauchen `118.00`!): im Multi Panel nicht nötig →
  **am Gerät verifizieren** (gängig bei Saitek: Punkt = Ziffernbyte mit gesetztem
  High-Bit, z. B. `+0xD0`). `format_row` muss dafür erweitert werden (Punkt-Param).

## Interaktionsmodell — Anzeige folgt dem Encoder (entschieden 2026-07-04)
Problem: COM 8.33 kHz braucht **3 Nachkommastellen** (118.**005** vs .**010** vs
.**015**), aber die 5-Zellen-Zeile `NNN.NN` zeigt nur 2 → dritte Stelle nicht
darstellbar/unterscheidbar. NAV (50 kHz) und COM 25 kHz kommen mit 2 Stellen aus.
**Entscheidung (User):** KEIN Umschaltknopf, KEINE Tempo-Erkennung, sondern die
Anzeige **folgt dem zuletzt gedrehten Encoder**:
- **innerer (feiner) Encoder** gedreht → View springt auf **`NN.NNN`** (führende 1
  von COM 1NN.xxx impliziert weg, 3. Nachkommastelle sichtbar, z.B. `18.005`).
- **äußerer (grober) Encoder** gedreht → View springt auf **`NNN.NN`** (Hunderter/
  ganze MHz sichtbar).
- View ist **sticky** bis der andere Encoder benutzt wird; Default = grob `NNN.NN`.

**Zweite Ebene — Tempo steuert die Fract-Schrittweite** (User 2026-07-04): der
innere Encoder tunt **langsam = fein (8.33 kHz), schnell = grob (25 kHz)**. Das ist
exakt der Multi-Panel-Beschleunigungs-Mechanismus (`_encoder_step`: `step` vs
`fast_step`, `_FAST_WINDOW`/`_FAST_AFTER`) → wiederverwenden. Also zwei implizite
Ebenen, kein Umschaltknopf: *welcher* Encoder = **Ansicht**, *wie schnell* der
innere = **Schrittweite**.

Umsetzung: `format_frequency(mhz, decimals=2|3)` existiert schon (display.py);
Controller hält ein `view`-Flag pro Radio + den Beschleunigungs-Zustand.
**Reihenfolge:** COM/NAV mit Standard-Tuning zuerst; das exakte **8.33-Step/Event**
(was in der JF-Arrow einen echten 8.33-kHz-Schritt erzeugt) ist der Teil, der
**in-sim verifiziert** werden muss — die Velocity→Step-Logik selbst ist generisch
und jetzt schon testbar.

## Funktionen (aus SPAD `Arrow (Turbo).xml`, Quelle der Wahrheit)
SPAD nutzt für die ACT/STBY-Tasten die Swap-Events:
- `COM1_RADIO_SWAP`, `COM2_RADIO_SWAP`, `NAV1_RADIO_SWAP`, `NAV2_RADIO_SWAP`
- Transponder (`XPNDR`/`TRANSPONDER`-Vars), ADF (28× referenziert).
Anzuzeigende SimVars je Selektor-Position (Standard MSFS):
- COM1: `COM ACTIVE FREQUENCY:1` / `COM STANDBY FREQUENCY:1` (MHz), Swap-Event s.o.
- COM2: `:2`. NAV1/2: `NAV ACTIVE/STANDBY FREQUENCY:1|2`.
- ADF: `ADF ACTIVE FREQUENCY:1`. XPDR: `TRANSPONDER CODE:1` (BCD).
- DME: nur Anzeige (`NAV DME:1`), kein Standby.
Encoder: großer Knopf = ganze MHz/kHz grob, kleiner = fein; CW/CCW → die
`*_RADIO_WHOLE_INC/DEC` bzw. `*_RADIO_FRACT_INC/DEC`-Events.

## Nächste Schritte
1. scan-Tool gegen hidraw11 → exakte INPUT-Bits der Selektoren/Encoder/Tasten
   (Codes in `RadioUnit`/`RadioBank` eintragen; aktuell Platzhalter).
2. out-Tool gegen FEATURE → Ziffern-Reihenfolge + Dezimalpunkt-Kodierung
   bestätigen, Helligkeits-Flags (Feature #2) testen (`_FLAG_BYTES` noch 0x00).
3. ✅ **`mapping/display.py` um Dezimalpunkt erweitert (Chunk A) + Radio-Controller
   gebaut (Chunk B):** `mapping/radio_panel.py` `RadioPanelController` +
   `models.RadioBank/RadioUnit/RadioPanelOutput`, pure/getestet (`test_radio_panel.py`).
   Selektor wählt Bank, Encoder feuert WHOLE/FRACT-Events (View + Velocity→Step),
   Druck = SWAP. **Offen (Chunk C):** Device-Katalog + Runtime/Outputs-Wiring + Profil.
