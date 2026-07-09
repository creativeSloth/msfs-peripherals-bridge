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

## Eingänge (INPUT, 3 Byte / 24 Bits) — GEMESSEN 2026-07-05 (scan_radio.py)
Vollständig am Gerät vermessen (one-hot-Selektor-Sweep + sauberer CW-only-Encoder-
Durchgang). Alle 24 Bit gehen exakt auf; Bit-Index = `byte*8+bit` wie `hidraw_reader`.
- **Oberer Mode-Selektor** (one-hot, byte0): COM1=**0**, COM2=**1**, NAV1=**2**,
  NAV2=**3**, ADF=**4**, DME=**5**, XPDR=**6**. Ruhestellung = COM1 (bit0).
- **Unterer Mode-Selektor** (one-hot): COM1=**7**, COM2=**8**, NAV1=**9**,
  NAV2=**10**, ADF=**11**, DME=**12**, XPDR=**13**. Ruhestellung = COM1 (bit7).
- **ACT/STBY-Druck** (drückbarer Encoder): oberes Radio = **14**, unteres = **15**.
- **Encoder** (Puls je Rastung, byte2), CW = increment:
  - oberer **innerer** (fein): CW=**16**, CCW=**17**
  - oberer **äußerer** (grob): CW=**18**, CCW=**19**
  - unterer **innerer** (fein): CW=**20**, CCW=**21**
  - unterer **äußerer** (grob): CW=**22**, CCW=**23**
- ⇒ 7+7+2+8 = **24**. ✅ Ins Profil `piper_arrow.yaml radio_panel` eingepflegt.
  (Selektoren + innere Encoder trafen die alten Platzhalter; äußere Encoder + beide
  Swaps waren daneben und wurden korrigiert.)

## Ausgänge / Display (FEATURE, 20 Ziffern) — GEMESSEN 2026-07-05 (out_radio.py)
Zwei Radio-Zeilen; **pro Zeile links = ACTIVE, rechts = STANDBY** (5 Ziffern je Feld,
NEBENEINANDER — nicht ACTIVE-über-STANDBY gestapelt). Zell-Order am Gerät verifiziert:
- Byte **0–4**  = obere Zeile **links**  → **oberes Radio ACTIVE**
- Byte **5–9**  = obere Zeile **rechts** → **oberes Radio STANDBY**
- Byte **10–14**= untere Zeile **links** → **unteres Radio ACTIVE**
- Byte **15–19**= untere Zeile **rechts**→ **unteres Radio STANDBY**
(Deckt sich exakt mit `render()` in `mapping/radio_panel.py` — kein Code-Change nötig.)

Ziffern-Kodierung = identisch zum Multi Panel ⇒ **`mapping/display.py`
wiederverwenden** (`format_row`/`format_frequency`):
- `0x00..0x09` = Ziffer 0–9, `0x0F` = blank, `0xEE` = Minus.
- **Dezimalpunkt** ✅ **bestätigt 2026-07-05**: Ziffernbyte `+0xD0` zündet den Punkt
  rechts an der Ziffer (`0xD8` = `8.`), `118.00` liest sich korrekt.
- **Helligkeit** ✅: Flag-Bytes `0x00 0x00` → Display **voll hell** (kein Extra nötig).

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
✅ **Chunk A/B/C-Code fertig** (2026-07-04, committet): `mapping/display.py` Dezimalpunkt
(A); `mapping/radio_panel.py` `RadioPanelController` + `models.RadioBank/RadioUnit/
RadioPanelOutput` (B); OutputManager-Wiring + `config/devices.yaml` `radio_panel` +
Profil-`radio_panel`-Block + Scan-Tools (C). Getestet (`test_radio_panel.py`,
`test_output_manager.py`).
1. ✅ **INPUT-Bits gemessen** (2026-07-05, `scan_radio.py`) → echte Codes im Profil
   (`piper_arrow.yaml radio_panel`), siehe Input-Abschnitt oben. Platzhalter ersetzt.
2. ✅ **OUTPUT verifiziert** (2026-07-05, `out_radio.py`): Zell-Order (links=ACTIVE/
   rechts=STANDBY), Dezimalpunkt `digit+0xD0`, Helligkeit `flags=0x00` = hell. Kein
   Code-Change nötig.
3. ⏳ **NUR NOCH In-Sim:** exakte Event-Namen am fliegenden JF Arrow — `fract_fast_*`
   (echter 8.33- vs 25-kHz-Step, aktuell ungesetzt) + COM1-Swap (`COM1_RADIO_SWAP` vs
   `COM_STBY_RADIO_SWAP`). WHOLE/FRACT = MSFS-Standard, sollten direkt gehen.
