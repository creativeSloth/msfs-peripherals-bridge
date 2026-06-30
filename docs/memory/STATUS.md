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
- 🔧 **Chunk E läuft** — 1. In-Sim-Runde 2026-06-30 gemacht, daraus folgende
  Fixes umgesetzt (UNCOMMITTED, 86 Tests grün, ruff clean, alle Profile valide;
  **Bridge muss für Test neu gestartet werden**):
  - **Encoder-Beschleunigung RAUS** (war zu sensibel): immer 1×`step`, `fast_step`
    aus Model+Profil entfernt.
  - **Display 2-zeilig persistent**: jede Selector-Position hat `display_row`
    (top/bottom); ALT oben + VS unten bleiben gleichzeitig stehen, Selector
    re-pointet nur den Encoder. VS in Profil → `display_row: bottom`.
  - **Switch-Debounce** (`runtime._bounced`, 50 ms) gegen AP-Taste die
    „zurückspringt" (Kontaktprellen → Doppel-Toggle). Nur Engine-Pfad,
    Encoder/Selector unberührt.
  - **Pitch-Trimrad** (codes 18/19) → `ELEV_TRIM_UP/DN` (Doppelung mit Saitek-
    Trimrad bewusst).
  - **`SequenceAction`** (neuer Action-Typ, `models`+`engine`): Switch feuert
    Liste fester Writes (`on_edge`/`off_edge`; YAML-Bool-Falle → `*_edge`-Namen).
    Damit: **Auto-Throttle-Switch → HDG-Einkuppeln** (`L:AUTOPILOT_MODE=2` +
    `L:AUTOPILOT_HDG=1` an, `=0` aus) **und Avionics-Master** (volle SPAD-Sequenz
    inkl. `COM1/2_VOLUME_SET 100`, `L:KN62_POWER`).
  - **`SimVarAction.invert`**: Fuel-Pump (`L:CENTRE_LOWER_FUELPUMP`) Polarität
    gedreht (switch-on→0), in-sim bestätigt.
  - **CRS1/CRS2-Umschaltung**: `SelectorEntry.alt_sources` + `MultiPanelOutput.
    source_toggle` (Aux-Input, off-panel). Yoke-Rocker-down (code 291) togglet
    CRS-Quelle NAV1↔NAV2; im CRS-Modus zeigt die untere Zeile den Index 1/2.
    `outputs.OutputManager._aux` routet das Cross-Device.
  - **Piper-Beleuchtung realistisch** (kein Kippschalter, nur Dimmer):
    - Switch-Panel **code 7** (war PANEL_LIGHTS) → **CABIN_LIGHTS_SET**
      (rotes Center/Kabinenlicht). **code 9** (Nav) → **entfernt**.
    - Trimrad (codes 18/19) **nicht mehr Trim**, sondern **Light-Dimmer**
      (`MultiPanelDimmer` im Controller): jede Rastung ±step% → schreibt alle
      `brightness`-Vars (Radio+Panel-Light); `follow_event: NAV_LIGHTS_SET` =
      Nav-Light an, wenn Helligkeit > 0. Seedet aus erster *bekannter* Var.
      Trim-Codes laufen jetzt über den Controller (`consumes()` statt Engine).
    - ⚠️ **VERIFY-Var**: `L:CENTRE_LOWER_PANEL_LIGHT` ist aus SPAD; den
      **Radio-Light-LVar-Namen** (`L:CENTRE_LOWER_RADIO_LIGHT`?) + **Skala**
      (0–100 vs 0–10) muss User bestätigen — sonst bleibt das Licht dunkel.
  - **Encoder-Beschleunigung wieder rein, aber SANFT** (User wollte sie doch, nur
    schwächer): `fast_step` optional pro `SelectorEntry`; greift erst nach
    `_FAST_AFTER` schnellen Rastungen in Folge (`_FAST_WINDOW`=0.06s), ~halber
    Sprung (ALT 500, HDG/IAS/CRS 5). Controller bekam `clock`-Param (testbar).
  - **AP-Mode-Buttons** (codes 8/9/13/14) gemappt: Piper-AP hat keine Toggle-
    Knöpfe, sondern `L:AUTOPILOT_MODE`-Werte (NAV=0/HDG=2/APR=3/REV=4 + HDG-Puls),
    als SequenceActions 1:1 aus SPAD. **Tasten-LEDs fehlen weiter** (brauchen
    LVar-READ = Chunk C).
  - **Dimmer-Fix**: L:-Vars sind (noch) NICHT lesbar → Dimmer **self-tracked**
    seinen Wert (`_dimmer_value`, Start=min) statt aus dem Sim zu seeden; Var =
    `L:CENTRE_LOWER_PANEL_LIGHT` (SPAD-Panel-Switch). Center-Light (code 7) ist
    auch ein 0–100%-Dimmer → SequenceAction `LIGHT CABIN` 100/0.

### 🔴 ABSTURZ-URSACHE GEFUNDEN + GEFIXT (2026-06-30, 3.+4. Runde, sauberes Log)
**Es war NIE ein MSFS-CTD.** Saubere isolierte Logs zeigen jedes Mal: `access
violation writing 0x10` in der SimConnect-DLL → Bridge re-connectete in **1 s**,
danach `SIM OPEN`/`SIM Paused` (MSFS lebt weiter, kein `X connection broken`).
**Gemeinsame Ursache = nebenläufiger DLL-Zugriff:** In `bridge.py` rufen ZWEI
Threads ungeschützt in die nicht-thread-sichere `SimConnect.dll`: der **Poll-Thread**
liest SimVars, der **Dispatch-Thread** feuert Events/setzt Vars. Unter einem Schwall
(Dimmer am Anschlag = `SetClientData`-Flut; ODER Yoke ziehen = `ELEVATOR_SET`-Strom +
Gear/Flaps) überlappen Lesen+Schreiben → AV. (K-Events werden NICHT geloggt → Log sah
„idle" aus, war es nicht.) **DREI Fixes (uncommitted, 93 Tests grün, ruff clean):**
- ✅ **Bridge-DLL-Lock (Kern-Fix):** `SimConnectBridge._lock` (RLock) serialisiert
  ALLE DLL-Touches (`send_event`/`set_simvar`/`_mf_exec`/`read_var`/`read_simvar`/
  `close`). Lese-/Schreibzugriff überlappen nicht mehr → keine AV mehr.
- ✅ **Mapper-Reconnect (Recovery):** `BridgeClient(reconnect=True)` aus `cli.run`:
  merkt Subscriptions, wählt bei OSError/EOF neu (gen-Counter + dial-Lock, mehrere
  Threads), replay'd Subs. `bridge.py connect_sim` wartet jetzt ENDLOS (statt exit 1)
  → ein Bridge-Prozess übersteht beliebige MSFS-Downtime. Tests: `test_client_reconnect.py`.
- ✅ **Dimmer-Rail-Guard (Trigger-Reduktion):** `_on_dimmer`/`on_encoder` senden am
  Anschlag (Wert unverändert) nichts mehr → keine Wiederhol-Flut. Test
  `test_dimmer_emits_nothing_at_rail`.
- ℹ️ **Bridge wirklich stoppen:** `pkill -f run-bridge.sh` (Supervisor); `pkill -f
  bridge.py` killt nur das Kind, Supervisor startet in 2 s neu.
- ⏳ **ZU VERIFIZIEREN in-sim:** Mapper neu starten (neuer Code!), dann hart fliegen
  (Yoke + Gear + Flaps + Dimmer am Anschlag) → darf nicht mehr wegbrechen; falls
  doch ein AV kommt, muss Mapper jetzt in ~1 s selbst zurückkommen. ⚠️ Restliche
  Trigger evtl. ungültige Requests (`L:KN62_POWER`→NAME_UNRECOGNIZED, `NAV OBS:2`→
  UNRECOGNIZED_ID) — wenn nach Lock noch AVs, diese Requests unterdrücken.

### 🐞 In-Sim-Test 2026-06-30 (2. Runde) — BEFUNDE (offen, der Reihe nach)
### ✅ ERLEDIGT (diese Session, 2026-06-30, UNCOMMITTED, 90 Tests grün, ruff+validate ok)
- **Bridge-Robustheit Teil 2 — Supervisor-Loop** in `run-bridge.sh`: stirbt
  `bridge.py` hart (SIGSEGV/Kill durch CTD), startet das Skript sie nach 2 s neu
  (`while`-Loop + `wait`; SIGTERM/INT beendet sauber). `connect_sim()` wartet eh
  auf MSFS → Bridge kommt allein zurück. (1. In-Sim-CTD-Test: Log SAUBER, keine
  Access-Violation-Lawine mehr; Prozess war aber hart gekillt → genau dafür der Loop.)
- **Dimmer-Umbau** (radio + panel gemeinsam, 10%-Stufen): `MultiPanelDimmer` neu =
  Prozent 0–100/step 10 + Liste `DimmerTarget{var|event, full}` (Pro-Ziel-Skala).
  Profil: `LIGHT_POTENTIOMETER_2_SET` (full 100, Radio/Instrument) + `L:CENTRE_
  LOWER_PANEL_LIGHT` (full 10, Panel). ⚠️ Potentiometer-Event-Skala in-sim prüfen
  (evtl. `full: 10` statt 100, s.o. SPAD-Param 10).
- **HDG-Bug:** `L:AUTOPILOT_HDG=1` aus ALLEN 5 Modus-Tasten RAUS; HDG-Master-Arm
  jetzt NUR auf dem Autothrottle-Schalter (Multi-Panel code 15, maintained on=1/off=0).
- **Encoder-Beschleunigung sanfter:** `_FAST_AFTER` 2→3 (greift 1 Rastung später)
  + `fast_step` kleiner (ALT/VS 500→300, IAS/HDG/CRS 5→3).
- **OMNI bestätigt** = `L:AUTOPILOT_MODE=1` (SPAD: NAV-Langdruck), liegt auf IAS-Taste code 10.
- **Avionics „geht erst nach Batterie aus/an" — Ursache:** Maintained-Switches werden
  beim Start NICHT geprimt (Runtime reagiert nur auf Flanken). Batterie/Avionics
  physisch AN bei Bridge-Start → Sim weiß es nicht → Avionics-Bus stromlos, bis man
  toggelt. Avionics-Sequenz selbst ist 1:1 SPAD und korrekt. FIX-Idee (offen):
  Switch-Priming beim Start (aktuellen hidraw-Zustand lesen + synthetische Flanke).

### 🐞 In-Sim-Test 2026-06-30 (2. Runde) — BEFUNDE
1. **🔴 Bridge bricht weg (WICHTIGSTE) — Ursache gefunden.** Sim-CTD → SimConnect
   schickt `QUIT`, Lib setzt `quit=1`, Dispatch-Thread endet. **`bridge.py` prüft
   das nicht** → `send_event()` ruft weiter `TransmitClientEvent` auf totem Handle
   → `access violation writing 0x0000000000000010`, pro Event als ERROR geloggt
   (Log-Spam + zerschossener Log mit Müll-Bytes), irgendwann segfaultet die
   Wine-Python → Bridge weg; `run-bridge.sh` ist Single-Shot → kein Restart.
   **FIX UMGESETZT (uncommitted, live noch zu verifizieren):** in `bridge.py`
   `SimDisconnected`-Exception + `_check_alive()` (prüft `sc.quit`/`sc.ok`/`_dead`)
   vor jedem DLL-Call; jeder DLL-Call (`send_event`/`set_simvar`/`_mf_exec`/reads)
   in `try/except OSError` → `_mark_lost()` fängt schon die ERSTE Access-Violation
   (harter CTD ohne QUIT). Session loggt 1× (`_on_sim_lost`), stoppt Loops,
   `conn.shutdown` weckt idle `recv`; `serve()` gibt `sim_lost` zurück; `main()`
   macht dann `sim.close()` + `connect_sim()` → Bridge hängt sich nach MSFS-Restart
   SELBST wieder an. py_compile+ruff grün. **TEST: CTD provozieren / MSFS neu
   starten → Bridge darf nicht mehr wegbrechen, kein Log-Spam, re-attached allein.**
2. **✅ CRS OBS1↔2-Toggle funktioniert** (in-sim bestätigt: Werte ±1°/±beschl.,
   Wrap 359→0). „Warum lief's erst nicht / 100er-Sprünge": Selector war anfangs
   nicht auf CRS → Encoder editierte ALT (step 100); sobald CRS gewählt + NAV2
   verfügbar war, lief's. **OBS-Feedback: USER-ENTSCHEID = KEINS** (wechselnder
   Kurswert reicht als implizite Rückmeldung). `NAV OBS:2`-`UNRECOGNIZED_ID` ist
   transient (Var erst da, wenn NAV2 getunt) + harmlos → nicht gefixt, low-prio.
3. **✅ Schubhebel nicht am Detent — URSACHE GEFUNDEN (kein Code-Bug):** MSFS hat
   das Gerät SELBST nochmal mit eigenen Achsen-Bindings belegt → Doppel-Mapping
   (Bridge `THROTTLE1_SET` kalibriert **vs.** MSFS-Rohachse parallel) → Achse
   springt/Detent verschoben. **FIX im Sim:** in MSFS-Steuerung die Bindings der
   bridge-bedienten Geräte (TQ6, Yoke, Pedale) LEEREN, damit die Bridge einzige
   Quelle ist. Reine Sim-Config, nichts an unserem Code.
4. **🟡 Avionics-Master ging nicht wie gewünscht** — SequenceAction (Avionics-Switch)
   verhält sich nicht korrekt; im Detail noch unklar, nach Fix 1 nachstellen.

### ⏸️ STAND beim Cut (2026-06-30, Credits leer) — HIER WEITER
Alles UNCOMMITTED auf `refactor/calibration-profile-split`, **91 Tests grün, ruff
clean, valide**. Mapper-Prozess `bujvb7cgf` läuft noch (ohne die OMNI-Zeile —
**Profil seit letztem Start geändert → für Test neu starten**: alten Mapper killen
[`pgrep -f "msfs_peripherals_bridge run"`, MSFS+bridge.py auf Port 7842 NICHT
anfassen], dann `msfs-bridge piper_arrow`).

**In-sim bestätigt vom User:** Encoder-Beschleunigung sanft = gut; CRS-Toggle
(Yoke 291) schaltet NAV1↔NAV2; Mode-Rotary bewegt sich bei Mode-Buttons.

**Letzte Profil-Änderungen (gerade gemacht, brauchen Restart+Test):**
- Dimmer jetzt **0–10-Skala** (war 0–100 → „1000%"): `step:1 max:10` = 10%-Schritte.
- Dimmer schreibt **2 Vars**: `L:CENTRE_LOWER_PANEL_LIGHT` (sicher) + `L:CENTRE_LOWER_RADIO_LIGHT` (**VERIFY-Name!**).
- Auto-Throttle→HDG (code 15) **entfernt** (verwirrte HDG-State); Mode-Buttons ohne `off_edge` (HDG springt nicht zurück).
- **OMNI** = `L:AUTOPILOT_MODE=1` (= der langsam-blinkende Long-Press) → auf **IAS-Knopf code 10** gemappt.

**💡 LICHT/DIMMER — SPAD-BEFUND (2026-06-30, aus `Arrow III.xml`):**
`L:CENTRE_LOWER_RADIO_LIGHT` **EXISTIERT NICHT** (war geraten → Radio Lights tot).
Komplette JF-Arrow-Licht-Vars in SPAD nur diese:
- **Radio-/Instrumentenlicht** (in SPAD „panel light"): `LIGHT POTENTIOMETER:2`,
  gesetzt via Event **`LIGHT_POTENTIOMETER_2_SET`**. ⚠️ Skala unklar: SPAD setzt
  A-Var=100 **und** feuert Event mit Param **10** → Event-Skala evtl. 0–10, A-Var
  0–100. In-sim verifizieren (`full` pro Ziel konfigurierbar machen).
- **Panel-Light** (reagiert schon): `L:CENTRE_LOWER_PANEL_LIGHT`, Skala **0–10**.
- Cabin (Users 3. Dimmer, irrelevant): `LIGHT CABIN`/`CABIN_LIGHTS_ON`.
USER-WUNSCH: Radio Lights **+** Panel Lights über **dasselbe** Pitch-Trim-Rad,
gleichmäßig in **10%-Schritten**. → Dimmer braucht PRO-ZIEL-SKALA (Panel +1/Step
auf 0–10, Potentiometer +10/Step auf 0–100) + Event-Ziel-Support (nicht nur SimVar).

**ENTSCHIEDEN, NÄCHSTE SCHRITTE (User-Wahl):**
1. **🎯 LVar-READ-Pfad bauen (Chunk C, der große Brocken)** = Wahl B. Damit:
   Mode-Tasten-LEDs (HDG/NAV/APR/REV+OMNI leuchten via `L:AUTOPILOT_MODE`-Read),
   echte Dimmer/AP-Werte. bridge.py kann LVars schon SCHREIBEN (MobiFlight exec) →
   READ über RequestClientData/RECV_CLIENT_DATA. LED-Bits: AP/HDG/NAV/IAS/ALT/VS/
   APR/REV (multi-panel-hid.md). Mode→LED: MODE==Wert UND `A:AUTOPILOT MASTER`.
2. **Versteckte VS/ALT-Modi** mappen (JF AutoControl IIIB = nur Roll; JF hat
   ALT-Hold + VS-Hold als Clickspots nachgerüstet, VS nur bei aktivem ALT-Hold).
   **LVar-Namen unbekannt** → am Flieger via MobiFlight-Browser ermitteln, oder
   JF-Handbuch (PDF 10 MB, zu groß für WebFetch). ALT/VS-Tasten = M-Panel code 11/12.

**OFFENE VAR-FRAGEN an User (blockieren Funktion):**
- **Radio-Light-LVar**: stimmt `L:CENTRE_LOWER_RADIO_LIGHT`? (sonst Radio-Lichter tot)
- **Cabin/Center-Light** (sim zeigt 65%): welcher LVar? `LIGHT CABIN` greift nicht.

**ABGEHAKT / nicht weiterverfolgen:**
- **CRS-Index 1/2 im Display**: Bytes nachweislich korrekt (Repro), aber Panel
  steuert sein Display im CRS-Modus SELBST (wie das nicht-host-steuerbare Label) →
  weder untere Zeile noch oberes linkes Segment nehmen den Index an. **Hardware-
  Grenze, aufgegeben.**

OMNI/Mode-Recherche-Quelle: justflight.com Forum/Manual (AutoControl IIIB).
SPAD-Recipe steht in `docs/memory/multi-panel-hid.md`.
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
