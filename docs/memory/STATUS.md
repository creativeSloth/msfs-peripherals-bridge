# STATUS — Resume-Anker

> Kurzer Einstiegspunkt: was läuft, was offen ist, wie es weitergeht.
> Stand: **2026-06-29**. Branch: `refactor/calibration-profile-split` (viel uncommitted, noch nicht auf `main`).

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

## Gerade fertig codiert — IN-SIM-TEST OFFEN
- **Switch Panel Gear-LEDs (Ausgabe)** — 2026-06-29, Tests+ruff grün, **noch nicht
  in-sim**. Sim→Panel: grün=down&locked / rot=in transit / aus=up, dunkel ohne Batterie.
  Logik 1:1 aus SPAD `Arrow (Turbo).xml`. Dateien: `models.GearLedOutput` +
  `Profile.outputs`, `mapping/leds.py`, `hidraw_reader.write_feature_report`
  (ioctl HIDIOCSFEATURE), `outputs.OutputManager`, `runtime._start_outputs`,
  `BridgeClient.send` lock-guarded, `piper_arrow.yaml` `outputs:`-Block.
  **Test:** `msfs-bridge piper_arrow` → Fahrwerk ein/aus → N/L/R beobachten;
  Batterie aus → alle dunkel.

## Roadmap (geordnet)
1. **Gear-LEDs in-sim verifizieren** (s.o.), dann committen.
2. **RpnAction-Typ** sauber einbauen (models+protocol+engine) und Avionics-Switch
   (Code 2) verdrahten — Multi-Step-Sequenz (AVIONICS_MASTER + L:KN62_POWER + COM-Vol
   + TRANSPONDER). RPN-String steht schon in der Saitek-Memory.
3. **Cowl Flaps** mappen — Switch braucht 0..16383 statt 1/0 (skalierte Switch-Action).
4. **Multi + Radio Panel** — Encoder (relative Ticks → Event N×, neues Source-Verhalten)
   + 7-Segment-Displays (SimVar→Ziffern, Feature-Report). Output-Plumbing steht schon.
5. **Magneto-L-Detent-Bug** am Switch Panel fixen (hidraw-Bit-Map/Edge bei Code 15/16).

## Pointer
- **Detail-Memory** (persönlich, ausführlich): `~/.claude/projects/.../memory/`
  → `project-saitek-panels.md` (Panel-Detail), `project-open-threads.md` (Voll-State).
- **SPAD-Profile = Quelle der Wahrheit** für SimVars/Events/LVars **und** LED-Logik:
  `/home/familie/Dokumente/SPAD.neXt/profiles/*.xml` (Arrow: `Arrow (Turbo).xml`).
- **Architektur/Bridge/Devices**: siehe Geschwister-Docs in `docs/memory/`.
- Tests: `pytest` (alle grün), Lint: `ruff check`, `msfs-bridge validate`.
