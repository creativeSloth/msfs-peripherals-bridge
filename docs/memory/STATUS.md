# STATUS — Resume-Anker

> Kurzer Einstiegspunkt: was läuft, was offen ist, wie es weitergeht.
> Stand: **2026-06-30**. Branch: `refactor/calibration-profile-split` (noch nicht auf `main`).

## Was funktioniert (in-sim bestätigt)
- **Wine-SimConnect-Bridge** (`bridge/bridge.py`): TCP-JSON, K:-Events, A:-SimVars,
  `subscribe`→`state`-Stream. Läuft unter Proton. Start via `msfs-bridge [profil]`.
- **Achsen-Mapping**: Yoke, Pedale, TQ6+ (Throttle/Prop/Mixture), Trim — kalibriert,
  in-sim geflogen. `AILERON_SET`/`RUDDER_SET` brauchen `invert: true`.
- **Yoke-Buttons**: Parking Brake, Fuel Selector, ATC, Heading-Bug-Sync
  (`event_from_var`). 290 = „AP-Heading = aktueller Kurs".
- **Saitek Switch Panel — Eingabe**: alle Schalter/Magnetos/Gear-Hebel nativ über
  hidraw (`SourceKind.SWITCH`). In-sim verifiziert. (Magneto-L-Detent: kleiner
  bekannter Bug, siehe piper_arrow.yaml.)
- **MobiFlight-WASM-Kanal** (commit b8be49d): L:/H:/B:-Vars + RPN schreibbar.
  Fuel pump (`L:CENTRE_LOWER_FUELPUMP`) validiert.
- **Profile**: default, cessna_152, cessna_172, piper_arrow (JF Arrow). Auto-Select
  per TITLE-Substring. Kalibrierung getrennt (`apply_calibration`).

## Switch Panel — KOMPLETT (in-sim bestätigt)
- **Gear-LEDs (Ausgabe)** — in-sim verifiziert 2026-06-30, committed (`2d1156b`).
  Sim→Panel: grün=down&locked / rot=in transit / aus=up, dunkel ohne Batterie.
  Logik 1:1 aus SPAD `Arrow (Turbo).xml`. Dateien: `models.GearLedOutput` +
  `Profile.outputs`, `mapping/leds.py`, `hidraw_reader.write_feature_report`
  (ioctl HIDIOCSFEATURE), `outputs.OutputManager`, `runtime._start_outputs`,
  `BridgeClient.send` lock-guarded, `piper_arrow.yaml` `outputs:`-Block.

## Multi Panel — IM BAU (Chunks A/B fertig, branch refactor/calibration-profile-split)
HID-Map komplett gemessen+verifiziert 2026-06-30 → `docs/memory/multi-panel-hid.md`
(Input: Selector one-hot bit0-4 ALT/VS/IAS/HDG/CRS, Encoder bit5/6, AP-Taste bit7,
Tasten HDG/NAV/IAS/ALT/VS/APR/REV bit8-14, AutoThrottle bit15, Flaps bit16/17,
Trim bit18/19. Output: 12-Byte Feature-Report = 10 Ziffern (2×5) + LED-Byte;
Ziffer 0-9, blank=0x0F, minus=0xEE; LED-Bits AP/HDG/NAV/IAS/ALT/VS/APR/REV).
- ✅ **Chunk A** (`ce9b683`): `multi_panel` im Katalog, `mapping/display.py`,
  `multi_button_led_byte` in `leds.py`, Tests.
- ✅ **Chunk B** (`4fa3829`): `mapping/multi_panel.py` `MultiPanelController` +
  `models.SelectorEntry/MultiPanelOutput` (pure, getestet). Encoder: Wert±Schritt
  mit Schnelldreh, Clamp/Rollover, feuert `*_SET` oder schreibt SimVar.
- ✅ **Chunk D** (`6e904d3`): verdrahtet. `outputs.OutputManager` besitzt den
  Controller (subscribe/on_state→render + `handle_input` für Selector/Encoder,
  1 Lock für beide Threads); `runtime` routet Selector/Encoder-Codes 0–6 zum
  Controller, Rest zur Engine. `piper_arrow.yaml`: multi_panel-Bindings (AP-Taste,
  AutoThrottle→AP_AIRSPEED_HOLD, Flaps) + multi_panel-Output (Selector 5×, Display,
  AP-LED). 76 Tests grün, ruff clean.
- ⏳ **Chunk C** (offen, riskant/sim-abhängig): **LVar-READ im Bridge**
  (`L:AUTOPILOT_MODE` lesen → Modus-Tasten-LEDs) **+ Modus-Tasten HDG/NAV/APR/REV**
  (codes 8/9/13/14) als L:AUTOPILOT_MODE/_HDG-Writes. Braucht: (a) fixe-Wert-
  SimVar-Action (neues `value`-Feld an `SimVarAction`, Engine = momentary), (b)
  LVar-Read-Pfad (RequestClientData/RECV_CLIENT_DATA über MobiFlight). SPAD-Werte:
  NAV=0, HDG=2, APR=3, REV=4 (+ AUTOPILOT_HDG pulse 1/0). Siehe multi-panel-hid.md.
- ⏳ **Chunk E** (NÄCHSTER SCHRITT empfohlen): **In-Sim-Test des fertigen Teils**
  VOR C, um zu de-risken. `msfs-bridge piper_arrow` → Selector→HDG, Encoder drehen
  (Display + Sim-Wert + Schnelldreh), ALT/VS/IAS/CRS durch (Minus bei VS prüfen),
  AP-Taste+LED, Flaps, AutoThrottle. Achten: welche `*_SET` greifen auf dem JF
  Arrow (v. a. AP_ALT_VAR_SET_ENGLISH, AP_VS_VAR_SET_ENGLISH, AP_SPD_VAR_SET,
  `NAV OBS:1`/VOR1_SET — Index-Syntax riskant). Greift ein Event nicht → set_event
  der Zeile entfernen (= direkter SimVar-Write).
SPAD-Recipe + Entscheidungen (AutoThrottle→AP_AIRSPEED_HOLD, Schnelldreh an,
Trim+Long-Press zurückgestellt) stehen in `docs/memory/multi-panel-hid.md`.
Mess-/Output-Tools liegen im **Scratchpad** (`scan_multi.py`, `out_multi.py`) →
TODO sie ins Repo (`tools/`) holen, siehe Memory `project-panel-tools-folder`.

## Roadmap danach
1. **Magneto-L-Detent-Bug** am Switch Panel fixen (hidraw-Bit-Map/Edge bei Code 15/16).
3. **Cowl Flaps** mappen — Switch braucht 0..16383 statt 1/0 (skalierte Switch-Action).
4. **RpnAction-Typ** (zurückgestellt — User sah Nutzen noch nicht): Avionics-Switch
   (Code 2) als Multi-Step-Sequenz. RPN-String steht in der Saitek-Memory / SPAD-Profil.

## Pointer
- **Detail-Memory** (persönlich, ausführlich): `~/.claude/projects/.../memory/`
  → `project-saitek-panels.md` (Panel-Detail), `project-open-threads.md` (Voll-State).
- **SPAD-Profile = Quelle der Wahrheit** für SimVars/Events/LVars **und** LED-Logik:
  `/home/familie/Dokumente/SPAD.neXt/profiles/*.xml` (Arrow: `Arrow (Turbo).xml`).
- **Architektur/Bridge/Devices**: siehe Geschwister-Docs in `docs/memory/`.
- Tests: `pytest` (alle grün), Lint: `ruff check`, `msfs-bridge validate`.
