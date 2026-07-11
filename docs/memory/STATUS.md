# STATUS — Resume-Anker

> Kurzer Einstiegspunkt: was läuft, was offen ist, wie es weitergeht.
> Stand: **2026-07-09** (ALT/VS-Mode-Input IN-SIM GEFUNDEN + verdrahtet, Sticky-Wert-Fix
> für ALT/VS, Barometer geklärt (2 Höhenmesser) — s. 🆕-Abschnitt ganz oben).
> Multi-Panel ist auf **`main`** gemerged.
> Aktueller Branch: **`refactor/light-dimmers`**. Diese Session: **ALLES UNCOMMITTED**
> (Battery-Gating + die 🆕-Threads). **172 Tests grün, ruff clean, 4 Profile valide.**
> Ältere „UNCOMMITTED"-Marker weiter unten sind historisch (Code steht/committet).

## 🆕 SESSION 2026-07-11 (spät) — Streaming IN-SIM VERIFIZIERT + Index-Kollisions-Regression GEFIXT
**Branch `feat/gui-var-monitor`.** Der Streaming-Push aus dem Abschnitt unten wurde committet
(`e258e8a`) und **diese Session in-sim bestätigt:** Yoke glatt + Multi-Panel-Werte gut (User),
ADF- + Barometer-Displays gut, `Streaming SimVar …`-Zeilen im Log, keine AV/Reconnect-Flut.
`POLL_INTERVAL`-→-0.1-Schritt (10 Hz) ist noch **offen** (kann jetzt gemacht werden, s. u.).

**🔴 REGRESSION gefunden + behoben (committet):** Streaming ließ **COM2/NAV2 die COM1/NAV1-Werte
anzeigen** (User: „radio com1/2 + nav1/2 werden nicht korrekt angezeigt, im Sim aber richtig
eingestellt"). Ursache: python-simconnect löst **jeden Index** einer SimVar (`COM ACTIVE
FREQUENCY:1/:2`, alle `NAV …:1/:2`) auf **ein geteiltes Request-Objekt** auf (`find()` setzt nur
den Index um). Der alte Pull-Read setzte den Index pro Read neu → korrekt; der neue **stehende
Stream** registriert ihn nur einmal → `:1` und `:2` teilten sich Request-ID + `outData` → beide
lasen den zuletzt registrierten Index. Deshalb liefen ADF (`:1` only) + Baro (kein Index) sauber,
nur die Mehrfach-Index-Paare kaputt. **Fix (`bridge/bridge.py` `_resolve_request`):** indexierte
Vars bekommen eine **eigene dedizierte `Request`** (eigene Req-/Def-ID, kanonische Einheit aus dem
Predefined-Eintrag); nicht-indexierte unverändert. Neuer Cache `_stream_var_requests`. **Belege:**
ruff+py_compile grün, 200 Tests grün; Offline-Stub-Test (`resolve_smoke.py` im Session-Scratchpad,
7/7 PASS); **live:** getrennte Req-IDs (COM 9/10, NAV 20/21 …) UND getrennte korrekte Werte
(COM1 123.815 ≠ COM2 135.235, NAV1 114.6 ≠ NAV2 111.0 — vorher beide identisch).

**✅ 1+2 FERTIG (Code + committet `b16699a` + am Panel in-sim verifiziert 2026-07-11):
ADF-Encoder tunt die echte Frequenz, DME-Push kippt den Cockpit-Schalter. Nur noch ③ (CRS-Anzeige) offen.**

**🚧 THREADS — Mechaniken IN-SIM GEKNACKT (2026-07-11):**
1. **✅ ADF — GELÖST via KR-85-LVars (nicht „ADF"-benannt!), VERDRAHTET+VERIFIZIERT.** Der JF-Arrow-ADF ist ein **KR-85**;
   die Frequenz liegt in **`L:KR85_dig1_counter/dig2_counter/dig3_counter`** (gefunden per
   727-LVar-**Vorher/Nachher-Diff**, während User die 3 Cockpit-Knöpfe drehte — mein „adf"-Grep
   fand sie nie). **Schreibbar + Gauge folgt visuell bestätigt** (Write dig3=5 → Anzeige 0247→245).
   **Formel: `F_kHz = (dig1+1)·100 + dig2·10 + dig3`**; Setzen: `dig1=F//100−1, dig2=(F//10)%10,
   dig3=F%10` (in-sim mit 468 verifiziert). Bereich 190–1799 → dig1 0–16, dig2/dig3 0–9. Andere KR85:
   `left_knob/mode_knob/right_inner_knob/right_outer_knob/vol_knob`, `RADIO_ANIM_KR85`.
   ⚠️ Die Standard-A:-SimVars `ADF ACTIVE/STANDBY FREQUENCY:1` + alle ADF-Events/SetData sind
   **entkoppelter Schrott** (Beweis: mein Write fror ACTIVE auf 1200 ein, Gauge zeigte 1516) → NICHT nutzen.
   **TODO Code:** `AdfBank` von `ADF STANDBY FREQUENCY:1`+SetSimVar auf die 3 KR85-Counter umbauen
   (KR85 ist Direkt-Tune, KEIN Standby/Swap; 3 Ziffern). simvars-reference.md ADF-Zeile korrigieren.
2. **DME-Bezug — GELÖST via `L:RIGHT_MISC_dme_nav`** (0=NAV1, 1=NAV2). **Bidirektional bestätigt:**
   lesen = Anzeige folgt Cockpit; schreiben (0↔1) = **Cockpit-Schalter springt sichtbar mit** (User
   bestätigt). **TODO Code:** `DmeBank.source_var` = `L:RIGHT_MISC_dme_nav`; render liest ihn für den
   Index, Push schreibt `1−current`, subscriben; lokalen `_UnitState.dme_source` raus.
3. **CRS-Quellen-Anzeige (NAV1/2) am Multi-Panel — ⛔ GEPARKT (2026-07-11, User „bin müde,
   parke wie den Cabin-Dimmer").** Hardware-Grenze bestätigt: die **linkeste Top-Ziffer ist
   tot** (dunkel/Halb-Ziffer — Software sendet `[1,␣,␣,9,0]`, kommt nicht an) UND die **zweite
   Display-Zeile ist am Panel physisch verdeckt**. Beide Wege (Ziffer links / andere Zeile)
   scheitern an der HW. **De-facto-Indikator, den der User akzeptiert:** die **Gradzahl selbst
   wechselt** beim 291-Umschalten zwischen NAV1-OBS und NAV2-OBS („kurswert switcht sauber") →
   reicht ihm, um zu sehen welchen OBS er dreht. CRS-Render bleibt auf dem committeten Stand
   (Index in Zelle 0 = unsichtbar, aber harmlos). Falls je gewünscht: Punkt-Indikator am Kurs
   (DOT auf einer Ziffer = NAV2) wäre der einzige HW-taugliche Weg — nicht gebaut.
- **Methoden-Merker:** Frisch-Read pro Verbindung (Persistent-Read staled!); unbekannte JF-Var per
  727-LVar-Diff finden; JF nutzt Instrumenten-Namen (KR85/KR62/KMA20/RIGHT_MISC), nicht generische.

## 🆕 IN ARBEIT (2026-07-11) — Yoke-Stutter: A:-Reads von Pull auf PUSH (Thread-Opt, Option 1)
**Branch `feat/gui-var-monitor`. Nur `bridge/bridge.py` geändert (+123/−6), UNCOMMITTED.
200 Tests grün, ruff clean, py_compile ok.** Offline-Stub-Smoke-Test grün (5 Checks:
Setup, Warm-up-Fallback, lock-freier Cache-Hit, Stream-Reuse, korrekte periodische Args,
L:-Routing, `:index`-Var) — liegt im Session-Scratchpad `stream_smoke.py` (bridge.py ist
auf Linux nicht importierbar → nicht in der Suite; Test stubbt das `SimConnect`-Paket).

**Warum:** Rest-Stutter seit Multi-Client kam von der **Read-Seite**: A:-Var-Polls
(`requests.get()` = `RequestDataOnSimObjectType` + Spin-Wait in `get_data`) hielten den
`_PriorityLock` über den **ganzen Wine-Roundtrip** → der nächste Achsen-`*_SET` wartete
dahinter. L:-Reads waren schon billig (MobiFlight-Async-Callback → Dict-Lookup). User will
**Yoke-Auflösung/Rate NICHT** anfassen → Nebenläufigkeit optimieren statt Datenrate.

**Was gebaut (Option 1 = Pull→Push, EINE Connection):** jede abonnierte A:-Var wird
**einmal** als stehende periodische `RequestDataOnSimObject` registriert (`_start_stream`);
der Sim **pusht** den Wert auf den Dispatch-Thread → Basis-`handle_simobject_event` füllt
`Request.outData`. Dafür fängt `_ReadingSimConnect.my_dispatch_proc` jetzt `dwID==8`
(`SIMCONNECT_RECV_ID_SIMOBJECT_DATA`) ab (Basis behandelt nur BYTYPE) und routet es durch
dieselbe Methode. **Poll-Read = lock-freier `outData`-Zugriff** (`read_subscribed` neu),
konkurriert nie mehr mit Writes um den DLL-Lock. `_resolve_request` erhält die **kanonische
Einheit** (predefined `AircraftRequests.find` zuerst, beide Schreibweisen) → identisches
Verhalten wie alt. **Fallback eingebaut:** solange `outData is None` (Warm-up) ODER falls
Streaming unter Wine nicht liefert → alter Pull (`_read_pull`, greift auf DASSELBE Request-
Objekt zu) → **kein Funktionsverlust möglich**, nur weniger Contention sobald der Stream läuft.
Lifecycle sauber: `_stream_reqs` lebt auf der `SimConnectBridge` (frisch pro Sim-Connection,
beim Reconnect neu). **Periode = `SIM_FRAME`(3) + `CHANGED`(1)** (`_STREAM_PERIOD/_STREAM_FLAG`):
Cache ist frame-frisch → Output-Latenz bleibt Poll-gebunden (~1s wie vorher, KEINE Regression)
und `read_now` (Radio-Echo nach Tuning) liest wieder frisch. **Warum nicht `PERIOD_SECOND`:**
das hätte ein zweites 1s-Stadium addiert (Push-Takt + Poll) → alle A:-Displays/LEDs bis ~2s
langsamer, und `read_now` bekäme einen bis 1s alten Cache (Radio-Echo würde ruckeln). Fast alle
piper_arrow-Displays/LEDs sind A:-Vars (Gear-LEDs, AP-Ref-Werte ALT/VS/IAS/HDG/CRS, AP-Master-
LED, Battery-Gates, ganzes Radio-Display COM/NAV/DME/XPDR/ADF/Baro) → sie alle liefen sonst
langsamer. L:-Vars (`L:AUTOPILOT_MODE`, `L:JF_PA28_AP_alt/_vs` = Mode/Hold-LEDs) unberührt
(MobiFlight). t0-Wert deckt der Warm-up-Pull ab, also ist change-driven ok. Change-driven hält
die Dispatch-Last klein (Arrow-Output-Vars meist diskret + still im Idle).

**🔴 NÄCHSTE SESSION = IN-SIM VERIFIZIEREN (das ist der Spike-Zweck, offline nicht prüfbar):**
1. **Bridge MUSS neu starten** (lädt neues `bridge.py`): `msfs-bridge piper_arrow` (oder nur
   `setsid bash bridge/run-bridge.sh &` + Mapper). MSFS an, JF Arrow.
2. **Fliegen + GUI-Panel/Statistik offen** (das war die Stutter-Quelle): laggt das Yoke noch?
   Erwartung: glatt, weil die Panel-Reads jetzt lock-frei aus dem Push-Cache kommen.
3. **`bridge/bridge.log` prüfen:** `Streaming SimVar <name> …`-Zeilen erscheinen (Setup ok);
   Panel-Werte + LEDs updaten weiter (≤~1s, wie vorher); **keine** AV/`SimConnect lost`/
   Reconnect-Flut. Wenn Werte **blank bleiben** → Push liefert nicht unter Wine → Fallback
   hält's funktional, aber Contention bleibt → **auf Option 2 (2. SimConnect-Connection nur
   für Reads) schwenken.** Wenn Werte da UND Yoke glatt → committen.
4. **DANACH (User-Entscheidung „erst verifizieren, dann 10 Hz", 2026-07-11): `POLL_INTERVAL`
   in `bridge/bridge.py` von `1.0` auf `0.1` setzen → ~10 Hz an Displays/LEDs.** Das ist JETZT
   sicher, weil der Poll-Read lock-frei aus dem Cache liest (10 Hz = 10× billige Cache-Reads,
   NICHT 10× lock-haltende Pulls). **Zwingend erst NACH dem Streaming-Verify:** liefert
   Streaming unter Wine nicht, bleibt alles im `_read_pull`-Fallback (lock-haltend) — ein
   10-Hz-Poll würde den Lock dann 10× härter hämmern und die Achsen SCHLIMMER stottern lassen.
   User will ~10 Hz (nicht 60); reicht völlig. (Cache selbst ist via SIM_FRAME schon frame-frisch.)
5. Optional: Suppress-unchanged/Deadband (Write-Seite, vom User zurückgestellt — Auflösung/Rate
   des Yokes NICHT anfassen), Stub-Smoke-Test als Repo-Test aufnehmen.

## 🚧 IN ARBEIT (2026-07-10) — GUI Statistik-Politur + volle Var-Liste + Kachel-Panel
**Branch `feat/gui-var-monitor`. 194 Tests grün, ruff clean, py_compile ok.** Alles Offline-Code
(kein Sim nötig); GUI VISUELL UNGEPRÜFT (kein Display/Xvfb in der Session) — User muss sichten.

**Committet (cf0a161) — Statistik-Politur:**
- Spalten `Typ · Variable · Wert · Einheit` (Wert vor Einheit getauscht).
- **Auswahl persistent** über Sessions: `config.gui_settings_file()`
  (`~/.config/msfs-peripherals-bridge/gui-settings.json`), Speichern bei Add/Remove, Restore beim Start.
- **Volle SDK-Var-Liste** statt kuratiert: `tools/gen_simconnect_catalog.py` parst Python-SimConnect
  (MIT) → `src/.../data/simconnect_catalog.json` = **850 A:** (Einheit+settable) + **987 K:** Events
  (je Kategorie). `gui_catalog.py` lädt daraus; L: (692) weiter aus simvars-reference.md. Picker ~2529.
  `:index`→`:1` normalisiert. Tests test_gui_catalog.py.

**Kachel-Panel (committet fff3f45 = Grid-Basis; Politur fc-neu):** `_PanelWindow`.
- **Grid-Basis (fff3f45):** loslösbares Fenster, Kacheln **rasten in Zellen ein**, Drop auf besetzte
  Zelle **tauscht**. Rastergröße Spinboxen **Spalten x Zeilen, max 20x20** (`PANEL_MAX`). Rechtsklick
  entfernt. Live über denselben `_ValueMonitor` (Subscription = Statistik ∪ **sichtbares** Panel).
  Reine Grid-Logik `_panel_first_free/_cell_from_point/_fit_tiles` unit-getestet (test_panel_grid.py).
- **Politur (User-Feedback nach Sicht, „Einrasten super"):** (a) Kacheln **kompakter** (2-Zeilen-
  Layout, Value 18→13, Unit inline) → ~halbe Höhe schrumpfbar; (b) Fenster **rahmenlos**
  (`overrideredirect`) — kein Titel/X: oben Zieh-Balken (bewegt via `_move_*`) + Spinboxen, Ecke
  unten rechts = Größe (`_resize_*`), minsize 160x80.
- **Close-Fix (User: „kann Panel nicht mehr schließen"):** `withdraw` auf overrideredirect-Fenstern
  zickte → **an/aus = ERZEUGEN/ZERSTÖREN** des Fensters (zuverlässig auf jedem WM). Gesteuert über
  **Toggle-Button in der Statistik-Leiste** (`ttk.Checkbutton style=Toolbutton "Panel"`, gedrückt =
  sichtbar; Menü „Ansicht" entfernt). „→ Ins Panel" öffnet nur noch (schließt nicht). run()-Helfer
  `_show_panel`/`_hide_panel`/`_toggle_panel`/`_persist_visible`; `visible`-Flag in `panel`
  persistiert → Panel öffnet beim Start wieder, wenn zuletzt an. `_PanelWindow` hat kein
  `show/hide/visible` mehr; Subscription = Statistik ∪ (Panel wenn `alive()`).
- **⏳ User MUSS visuell prüfen (riskant: overrideredirect ist WM-abhängig!):** erscheint/verschwindet
  das Fenster über den „Panel"-Button? Zieh-Balken bewegt? Ecke resized? Spinboxen klickbar (Fokus
  auf override-Fenstern zickt manchmal)? Kachel-Kompaktheit ok? Falls override-Fenster gar nicht
  geht → Plan B „Titelleiste behalten, X blendet aus".

**Danach offen:** Mapper-Tab (Stufe A Geräte-Viewer → B Editor+**ruamel.yaml**-Writer, Entscheidung
gesetzt). Community-Release (Prefix-Auswahl/Installer/Auto-Geräte-Erkennung) = weit hinten.
Details in Auto-Memory `project-process-gui`.

## 🚧 IN ARBEIT (2026-07-09 spät) — GUI-Live-Monitor + Bridge MULTI-CLIENT
**Branch `feat/gui-var-monitor`** (von `main` nach dem Merge). **174 Tests grün, ruff clean,
py_compile ok.** Geändert: `src/.../gui.py`, `bridge/bridge.py`.
**✅ MULTI-CLIENT IN-SIM VERIFIZIERT (2026-07-09):** zwei gleichzeitige Bridge-Verbindungen
bekamen BEIDE `state`-Frames (Test-Snippet: A=2/B=2, „MULTIT-CLIENT OK"). Der Bridge-Umbau steht.
**Offen nur noch:** GUI+Mapper VISUELL zusammen prüfen (Statistik-Werte updaten live, während der
Mapper läuft) — dann nach `main` mergen. GUI-Monitor subscribt gleich (L:-Präfix), sollte greifen.

**Was gebaut wurde:**
- **GUI Statistik-Live-Monitor** (`gui.py`): neue `_ValueMonitor`-Klasse = Hintergrund-Thread,
  der dauerhaft subscribed und `{wire_name: value}` hält; `refresh()` updatet die Tabelle 1×/s.
  Snapshot-Button raus. **L:-Präfix-Fix** (das war der „Strich": L:Vars müssen als `L:<name>`
  subscribt werden, A: bar, K: = kein Wert). set_names bei Add/Remove, Reconnect bei Listen-Änderung.
- **Bridge MULTI-CLIENT** (`bridge/bridge.py` `main()`): `listen(1)`→`listen(8)`, **Thread pro
  Client** (`handle_client`) + **Reconnect-Manager-Thread** (statt inline). DLL-Zugriffe bleiben
  durch `SimConnectBridge._lock` (RLock) serialisiert — **auditiert:** send_event/set_simvar/
  _mf_exec/read_lvar/read_var/read_simvar/list_lvars/close alle unter `_lock` → parallele Clients
  safe. Reconnect-Manager wirft einen **gesunden** Sim nicht weg (prüft `_check_alive()`).
  Damit können **Mapper UND GUI-Monitor gleichzeitig** subscriben (das war der User-Wunsch).

**🔴 NÄCHSTE SESSION = ERST VERIFIZIEREN, bevor man dem Multi-Client traut (fragile Wine-Komp.):**
1. Bridge neu starten (`msfs-bridge`/`run-bridge.sh` — lädt neuen `bridge.py`).
2. **Multi-Client-Test:** ZWEI gleichzeitige Verbindungen (z.B. 2× `tools/probe_altvs.py` in
   getrennten Terminals, oder das Snippet aus dem Session-Scratchpad `mc_test.py`) → BEIDE müssen
   `state`-Frames bekommen. Wenn nur eine kriegt was → Multi-Client greift nicht.
3. **GUI+Mapper gleichzeitig:** Mapper starten, GUI „Statistik" → Variablen adden → Werte müssen
   **live updaten, während der Mapper läuft** (kein „Strich" mehr, kein Connect/Reset-Geflacker
   im bridge.log). Falls AV/Crash im Log → Lock-Audit vertiefen.
4. Wenn stabil → nach `main` mergen. **Offen:** Tests für `gui_catalog`/Monitor fehlen noch.

**Ebenfalls offen (Konzept, wartet auf 2 User-Antworten):** Mapping-Tab (Geräte/Tasten mappen +
Sonderfunktionen). Stufenplan A(Viewer)/B(Editor+Learn+Speichern)/C(Sonderfunktions-Editoren).
Fragen: (1) `ruamel.yaml` als Dep ok (kommentarerhaltendes Speichern)? (2) Stufe A oder A+B zuerst?
`msfs-gui`-Launcher liegt user-lokal in `~/.local/bin` (nicht im Repo).

## 🆕 SESSION 2026-07-09 — ALT/VS-Input gefunden + Sticky-Fix + Barometer (gemerged nach main)
Bridge (nur, ohne Mapper) live am JF Arrow; per neuem Tool `tools/probe_altvs.py` (subscribe +
optional Write/RPN auf 1 Verbindung, stdout line-buffered) getrieben. **172 Tests grün, ruff
clean, 4 Profile valid.** MSFS ist einmal mittendrin **abgestürzt (CTD)**, vom User neu gestartet;
danach Sticky-Display in-sim bestätigt (s.u.). Geänderte Dateien: `models.py`,
`mapping/multi_panel.py`, `profiles/piper_arrow.yaml`, `tests/test_multi_panel.py`,
`docs/simvars-reference.md`; neu: `tools/probe_altvs.py`.

**✅ Bug #1 GELÖST — ALT/VS-Mode-Input gefunden (in-sim):** Schreiben von **`L:AUTOPILOT_alt = 1`
kuppelt ALT-Hold ein**, **`L:AUTOPILOT_vs = 1`** VS — beide **gegenseitig exklusiv** (die Gauge
klärt den anderen selbst). Beweis aus dem Probe: Klick auf den Cockpit-Spot flippt `JF_PA28_AP_alt`
*und* `AUTOPILOT_alt` zusammen; ein `AUTOPILOT_alt=1`-Write reproduziert das Einkuppeln.
**Wichtig: das sind ENGAGE/SELECT-Kommandos, KEINE Toggles** — `=1` nochmal oder `=0` schaltet
NICHT aus (beides verifiziert). Ausschalten nur via AP-Master oder Moduswechsel; ein echter
On/Off-Toggle bräuchte das JF-`H:`-Clickspot-Event (nicht enumerierbar). **Profil verdrahtet**
(codes 11/12 → `sequence on_edge: { simvar: L:AUTOPILOT_alt/_vs, value: 1 }`); LEDs lesen weiter
`JF_PA28_AP_*`. User bestätigte in-sim: „bindings passen" (Modi kuppeln ein).

**✅ NEU — Sticky-Wert-Fix für ALT/VS (gebaut+getestet, IN-SIM VERIFY OFFEN):** Beim Moduswechsel
treibt die JF-Gauge `AUTOPILOT ALTITUDE LOCK VAR`→**0** (ALT-Capture) bzw. **80000** (VS aktiv) und
`VERTICAL HOLD VAR`, was den vom User gedrehten Zielwert auf dem Panel überschrieb. Fix:
`SelectorEntry.sticky: bool` — der Wert ist **encoder-eigen** (startet 0, nur der Encoder ändert
ihn, `on_state` fasst ihn nicht mehr an) statt live die SimVar zu zeigen. In `multi_panel.py`:
`self._sticky`-Store + `_value_for()`; `_row_value`/`on_encoder` nutzen ihn. Profil: `sticky: true`
an ALT+VS. IAS/HDG/CRS bleiben live. Tests in `test_multi_panel.py`. **✅ IN-SIM (2026-07-09):
der Display-Wert BLEIBT jetzt beim gedrehten Stand (springt nicht mehr auf 0/80000).** ABER:
der **Sim-seitige AP-Zielwert geht beim Einkuppeln trotzdem auf 0** — die JF AutoControl IIIB
ist ein simpler AP, ALT-Hold **fängt die aktuelle Höhe** (am Boden 0), es gibt **keine
persistente Höhen-Vorwahl**. Mit diesem AP nicht sauber erzwingbar → **akzeptiert** (User: „lass
uns Schluss machen"). Das Panel-Display ist damit bewusst vom Sim-Ziel entkoppelt.
  **⏳ DISKUSSIONSPUNKT NÄCHSTE SESSION (ausdrücklicher User-Wunsch 2026-07-09):** ob Sticky so
  bleiben soll. Trade-off: Sticky zeigt den gedrehten Wert (schöne UX), stimmt aber **nicht** mit
  dem echten AP überein (der hält die aktuelle Höhe, keine Vorwahl) → evtl. irreführend.
  Alternativen: (a) Sticky lassen, (b) zurück auf Live-SimVar (ehrlich, aber zeigt 0/80000),
  (c) Hybrid (z.B. Live zeigen, sobald der Modus aktiv ist). Sticky ist mit dem Rest **committet**
  (User: „entscheide du"), Entscheidung aber offen — falls (b): `models.py sticky`,
  `multi_panel.py _sticky/_value_for`, Profil `sticky: true` an ALT+VS und die Sticky-Tests
  isoliert zurücknehmen (revert).
  **→ FINAL 2026-07-09: (b) immer live Sim-Wert, ABER `off_above`-Maske (vom User als „genial"
  abgenommen).** `sticky: true` bei ALT+VS raus → Display folgt der SimVar. Neu:
  `SelectorEntry.off_above` (models) — ein Live-Wert ≥ Schwelle *oder* ein fehlender (None) Wert
  wird als **0** angezeigt, und der Encoder editiert von 0 hoch. Profil: ALT `off_above: 60000`
  (fängt das JF-„aus"-Sentinel 80000 → 0), VS `off_above: 30000` (fängt None→0). In
  `multi_panel.py` (`_row_value` + `on_encoder`). Tests in `test_multi_panel.py`. Das `sticky`-
  Feature bleibt als ungenutzter Opt-in im Code.

**✅ Bug #4 GEKLÄRT — es sind ZWEI Höhenmesser (in-sim verifiziert), kein dritter:**
| # | Instrument | Var | Steuerbar |
|---|-----------|-----|-----------|
| 1 | Haupt-Höhenmesser | `ALTIMETER_baro_*` + `KOHLSMAN SETTING HG` | ✅ (hängt am XPDR-Außenknopf) |
| 2 | Standby-Höhenmesser | `STBY_ALTIMETER_baro_knob`/`_scale` | ❌ Gauge-verwaltet |
Drehen von Knopf #1 bewegt KOHLSMAN, #2 bewegt nur die STBY-Vars (unabhängig). **Standby ist
NICHT per LVar-Write setzbar:** `baro_scale`-Write wird jeden Frame überschrieben; `baro_knob`-Write
bleibt zwar stehen, treibt aber den Druck nicht und driftet selbst → Gauge-Output, wie ALT/VS.
Auto-Sync ans Haupt-QNH bräuchte das JF-`H:`-Knopf-Event → **nicht gemacht, Standby bleibt manuell**
(User ok: „nur Nr. 1 gesteuert").

**Prozess-Stand Ende:** MSFS CTD, vom User neu gestartet. Bridge läuft (wartet/reconnectet auf
7842), Mapper aus. Für den Sticky-Verify: Mapper starten (`msfs-bridge piper_arrow` oder nur den
Mapper), lädt das neue Profil. `tools/probe_altvs.py` ist der Weg für weitere LVar-Input-Jagd
(z.B. das ALT/VS-`H:`-Toggle-Event, falls je gewünscht).

## 🆕 SESSION 2026-07-08 — Radio-Feinschliff (In-Sim getestet, UNCOMMITTED)
Bridge+Mapper liefen live am JF Arrow; iterativ getestet. **169 Tests grün, ruff clean.**
Sim am Ende vom User ausgemacht. Geänderte Dateien: `models.py`, `mapping/radio_panel.py`,
`mapping/engine.py`, `simconnect/protocol.py`, `profiles/piper_arrow.yaml`, `tests/*`.

**✅ IN-SIM VERIFIZIERT:**
- **🔋 Battery-Gating** (Multi + Radio) — Batterie aus ⇒ alle Leuchteinheiten dunkel, an ⇒
  hell. **Bestätigt.** (Das war der letzte offene Punkt aus dem 🔋-Abschnitt unten.)
- **Radio DME** — Distanz oben, `<nav> <GS>` unten, Push cyclet NAV1↔NAV2. **Bestätigt.**
- **XPDR Squawk** — Digit-Cursor + Punkt + Push wandert + innerer Encoder editiert.
  **Bestätigt** (bleibt **oktal 0–7**, User zugestimmt — reale Squawks sind oktal).

**🆕 GEBAUT diese Session:**
- **XPDR neu** (`radio_panel.py`/`models.XpdrBank`): Squawk digit-weise editiert — Push walkt
  Cursor (Dot markiert Ziffer), **innerer** Encoder ±Ziffer oktal. **Äußerer** Encoder jetzt
  = **Barometer/QNH**: feuert `KOHLSMAN_INC/DEC`, **untere Zeile** zeigt `KOHLSMAN SETTING HG`
  als `NN.NN` inHg (Punkt auf 2. Ziffer, z.B. 29.92). Baro-Anzeige via **ReadNow** (kein Poll-
  Delay). Profil: `baro_var: "KOHLSMAN SETTING HG"` an beiden XPDR (codes 6/13).
- **ADF neu** (`models.AdfBank` komplett ersetzt): 4-stellige **kHz**-Freq, digit-**paar**-weise.
  Push togglet Cursor-Paar high(1000er,100er)↔low(10er,1er), **äußerer** Encoder = linke Ziffer
  des Paars, **innerer** = rechte, **zwei Dots** markieren das Paar. Jede Ziffer läuft **einzeln
  umlaufend** in ihrem gültigen Bereich (1000er 0–1, 100er 0–7 bei 1000er=1) — **kein Gesamt-
  Clamp** mehr. Liest/schreibt `ADF STANDBY FREQUENCY:1` (ACTIVE liest Müll, s.u.), scale
  Hz→kHz = 0.001 (gemessen). Local-echo Display + `SetSimVar`-Write.
- **RpnAction / RpnExec** (neu, generisch): `{type: rpn, code: "<RPN>"}` → Bridge-`rpn`-Op →
  `_mf_exec`. Momentary (Press-Flanke). `models.py`+`protocol.py`+`engine.py`+Tests.

**🔴 OFFENE BUGS / NÄCHSTE SESSION (Sim wieder an):**
1. **✅ GELÖST 2026-07-09 (Input = `L:AUTOPILOT_alt/_vs = 1`, s. Block ganz oben)** — ~~ALT/VS-Knöpfe stellen die Modi NICHT ein~~ (nur die LEDs stimmen, wenn man im Sim/
   Clickspot umschaltet). **DIAGNOSE (Bridge-Log):** der RPN `(L:JF_PA28_AP_alt) ! (>L:...)`
   **wird ausgeführt** (`MobiFlight exec:` steht im Log), aber die LVar ändert sich nicht →
   **`L:JF_PA28_AP_alt/_vs` sind Gauge-OUTPUTS, keine Inputs** (die JF-Gauge überschreibt sie
   jeden Frame). Der Cockpit-Clickspot triggert einen anderen **Input**. → **TODO: den echten
   Input finden** (714-LVar-Liste nach `_button`/`_sw`/`_toggle` grep; H:-Events prüfen; ggf.
   Gauge-Clickspot-Code). Profil codes 11/12 zeigen aktuell auf den (wirkungslosen) RPN-Toggle.
   **➜ OFFLINE-RECHERCHE 2026-07-09 (Sim aus, 714-LVar-Liste + SPAD-XMLs durchsucht):**
   - Die 714-LVar-Enumeration hat **KEINE** `_button`/`_toggle`/`_switch`-Inputvar für die
     AP-Modi. Nur: `JF_PA28_AP_alt/_vs` (Gauge-Output, bestätigt), `AUTOPILOT_alt/_vs`
     (generische *Mirrors*, ebenfalls Read-Seite), `AUTOPILOT_alt_up/_dn` +
     `AUTOPILOT_vs_up/_dn` (= ALT-Ziel- / VS-Raten-**Adjust** = der Encoder, NICHT der Mode-Toggle).
   - SPAD mappt Arrow ALT/VS **nicht** (Arrow-XMLs enthalten keine AP_ALT/VS/JF_PA28-Zeile) →
     kein Referenz-Eventname.
   - **⇒ Hypothese: der echte Mode-Toggle-Input ist ein JF `H:`-Event-Clickspot** (für
     `MF.LVars.List` unsichtbar). **In-sim-Experiment (nächste Session) mit dem NEUEN
     `RpnAction`/exec-Pfad:** Kandidaten `(>H:...)` feuern + `read_lvars.py` auf
     `JF_PA28_AP_alt` beobachten → welcher flippt die Gauge? Parallel `AUTOPILOT_alt` (bare)
     vs `JF_PA28_AP_alt` beim Cockpit-Klick mitlesen. **Nebengewinn:** Multi-Panel-Encoder in
     ALT/VS-Position auf `AUTOPILOT_alt_up/_dn` bzw. `_vs_up/_dn` legen (Ziel/Rate-Adjust).
2. **🟡 ADF Digit-Wrap-Fix + Baro-ReadNow-Fix** wurden NACH dem letzten In-Sim-Test committed-
   in-tree — **noch nicht in-sim verifiziert.** Nächste Session: ADF 100er läuft sauber 0→7→0
   ohne 10er/1er zu stören? QNH-Anzeige ohne Delay?
3. **🟡 ADF Sim-Write** (`SetSimVar` auf `ADF STANDBY FREQUENCY:1`) — ob der Sim die Frequenz
   wirklich übernimmt (Nadel folgt) ist UNGEPRÜFT. Falls nur das Display echot, aber der Sim
   nicht mitgeht → auf ein Event (`ADF_...SET`/RPN) umstellen.
4. **✅ GELÖST/GEKLÄRT 2026-07-09 (s. Block ganz oben)** — ~~2. Barometer~~: es ist der
   **Standby-Höhenmesser** (`STBY_ALTIMETER_baro_knob`/`_scale`), unabhängig vom Haupt-Kollsman.
   **NICHT per LVar-Write setzbar** (Gauge-verwaltet) → bleibt manuell, kein Auto-Sync.

**📐 MESSDATEN diese Session (Bridge-Probe, Mapper aus):**
- **A-Vars OHNE `A:`-Präfix** subscriben (bloßer Name)! Mit `A:`-Präfix → `UNRECOGNIZED_ID`.
- `ADF STANDBY FREQUENCY:1` [number/Hz] = **1400000 = sauber 1400 kHz** (÷1000). `ACTIVE` =
  Müll (0x17980000) in allen Einheiten → **STANDBY nutzen**. Max ADF = **1799 kHz** (User).
- COM/NAV/`TRANSPONDER CODE:1` lesen sauber mit `number` (124.85 / 112.8 / 4196=0x1064).
- **ALT/VS-Truth-Vars** (Scan bestätigt): `L:JF_PA28_AP_alt` / `L:JF_PA28_AP_vs` (0/1, gegen-
  seitig exklusiv). AP-Master = `L:JF_PA28_AP_master`(+`_roll`). **= die LED-Quelle, korrekt.**

**✅ ERLEDIGT (2026-07-09, offline):** grafische Var-Übersicht (Mermaid) in
`docs/simvars-reference.md` konsolidiert — neuer Abschnitt „Overview at a glance": (1) wie die
Bridge jede Var-Art erreicht (SimConnect-direkt K:/A: vs WASM L:/H:/B:), (2) welches Peripheral
im Arrow-Profil was treibt (Solid=write, gestrichelt=read), farbcodiert nach Var-Art. In-sim
render (GitHub) noch ungeprüft, Syntax aber sauber (Fences balanciert, alle Labels gequotet).

**Prozess-Stand Ende:** Sim aus (User). Bridge+Mapper liefen zuletzt (reconnect-loopen jetzt);
mit `msfs-kill` stoppen oder für nächsten Test `msfs-bridge piper_arrow` neu. **pkill-Falle:**
KEIN Literal `peripherals_bridge run` in derselben Kommandozeile (auch nicht im echo/pgrep) →
Exit 144 Selbsttreffer; read-only `pgrep`/`ss` nutzen oder Bracket-Trick `[ ]` durchgängig.

---


## 🎯 RADIO PANEL KOMPLETT (2026-07-05, 4. Runde) — HIER WEITER = NUR NOCH IN-SIM
Alles committet auf `refactor/light-dimmers` (noch nicht gepusht/gemergt). **151 Tests
grün, ruff clean, 4 Profile valide.** Diese Session gebaut:
- **B2 Low-Latency-Echo** (`606cda8`) — Prell-Theorie per Messung widerlegt (Encoder pollt
  8 ms, kein fangbares Prellen); No-Op-Encoder-Debounce raus, Swap-Debounce bleibt; `ReadNow`
  (Bridge-Verb) refresht die getunte Var ~90 ms nach dem Event → Anzeige folgt sofort.
- **NAV Fine-View aus** (`36657f1`) — pro Bank (`RadioBank.fine_view`); COM zeigt die 8.33-
  Stelle, NAV bleibt `NNN.NN`. COM-Tuning unverändert (die `.010`-Sprünge sind korrektes
  8.33, kein Bug — mit ofcom/ICAO belegt). 25-kHz-Umbau verworfen (User fliegt „mal hier mal da").
- **DME/XPDR/ADF** (`724053e`, `e31e1de`) — `kind`-diskriminierte Bank-Union. **DME** = reine
  Anzeige (Distanz oben, „<nav> <GS>" unten, Push cyclet NAV1↔NAV2). **XPDR** = mode-loser
  Squawk-Edit (äußerer Knopf linkes Ziffernpaar, innerer rechtes, oktal; `XPNDR_SET` BCD16).
  **ADF** = Standby via Local-Echo tunen + `ADF1_RADIO_SWAP`. Codes 4/5/6 (oben) + 11/12/13
  (unten). Cabin-Light **geparkt** (JF-Modellgrenze, s. u. / `radio-panel-measurement.md`).
- **ALT/VS** war schon vorher committet (`af3c4d4`): Tasten 11/12 → `AP_ALT_HOLD`/`AP_VS_HOLD`,
  LEDs via `bool_leds` aus `L:JF_PA28_AP_alt/_vs`. **In-sim noch nicht verifiziert.**

**⏳ NÄCHSTE SESSION = IN-SIM-VERIFY (Mapper neu starten, lädt neues Profil!):**
1. **DME**: zeigt Distanz/GS? Push toggelt NAV1↔NAV2 sichtbar?
2. **XPDR**: Squawk-Anzeige stimmt? (Annahme: `TRANSPONDER CODE` liest als **BCD16** — falls
   Anzeige Müll → Decode in `_render_xpdr`/`on_event` anpassen.) Encoder ändern Code sauber?
3. **ADF**: Anzeige-Einheit prüfen (SimVar liest kHz oder Hz?) → `coarse/fine/display_scale/
   decimals/tune` im Profil justieren. Tunen die Knöpfe? Swap?
4. **ALT/VS**: AP-Master an → ALT (code 11)/VS (code 12) drücken → LED an + hält die JF-Gauge?
   (Falls Event ignoriert → Fallback JF-Bool direkt, Kommentar im Profil.)
5. Wenn alles ok → **pushen + nach `main` mergen** + Branch löschen.
Mapper-Neustart: alten killen (`pgrep -f "msfs_peripherals_bridge run"`, MSFS+bridge.py NICHT
anfassen), dann `msfs-bridge piper_arrow` (oder nur den Mapper, wenn Bridge läuft).

## 🔋 BATTERY-GATING aller Panels — GEBAUT (2026-07-07, UNCOMMITTED, 158 Tests grün)
User-Wunsch: **Displays + LEDs an Multi + Radio Panel leuchten nur, wenn der Battery-Switch im
Game an ist** (wie die Gear-LEDs, `dunkel ohne Batterie` in-sim bestätigt). **Umgesetzt genau
nach dem Design:**
- **Modell:** `power: str | None = None` (opt-in) an `MultiPanelOutput` + `RadioPanelOutput`;
  in `simvars()` angehängt (⇒ automatisch abonniert, `subscriptions()` unverändert nötig).
  Default `None` = kein Gating → bestehende Render-Tests unberührt.
- **Controller** (`multi_panel.py` + `radio_panel.py`): `self._power = config.power`; neuer
  `_powered()`-Helper (`None` ODER `values.get(power) >= 0.5`); `render()` gibt ganz oben bei
  nicht-powered den **Blank-Report** zurück (Multi: `display_cells(None,None)` + LED-Byte 0 +
  Spare 0; Radio: 20×`BLANK` + `_FLAG_BYTES`). `on_state` der Power-Var re-rendert automatisch
  über den bestehenden `OutputManager`-Pfad → **kein OutputManager-/Protokoll-Change.**
- **Profil** (`piper_arrow.yaml`): `power: "ELECTRICAL MASTER BATTERY"` in beiden Output-Blöcken
  (Kommentar: für Avionics-Bus-Gate auf `AVIONICS MASTER SWITCH` umstellen).
- **Tests:** +4 Multi (`test_multi_panel.py`) / +3 Radio (`test_radio_panel.py`): Batterie
  unbekannt+aus → Blank, an → zeigt, ohne power-Feld immer hell. 158 Tests grün, ruff clean,
  4 Profile valide.
- **⏳ NUR NOCH In-Sim-Sichtprüfung** (nächste Session mit MSFS an): Batterie aus ⇒ Multi +
  Radio dunkel, Batterie an ⇒ leuchten wieder. Zusammen mit dem Radio-In-Sim-Verify unten
  abhaken, dann committen + mergen.

## 🎯 RADIO — PRELL-THEORIE WIDERLEGT + B2 GEBAUT (2026-07-05, 3. Runde) — HISTORISCH
**Stand: 135 Tests grün, ruff clean, 4 Profile valide, alles UNCOMMITTED auf
`refactor/light-dimmers`.** Danach: committen/pushen/**mergen nach main** + Branch löschen.
Offen bleibt Cabin-Light + ALT/VS + B2 IN-SIM (Credits vorher beachten).

**Durchbruch: der Fract-Encoder PRELLT NICHT.** `scan_radio.py` um Timing erweitert, User
hat beide Encoder × beide Richtungen im Normaltempo gedreht. 163 ↑→↑-Abstände: **Minimum
16 ms = USB-Poll-Boden** (8 ms Poll + Pflicht-↓-Frame → schneller unmöglich), glattes
Kontinuum ohne Lücke, metronomische Serien = echtes Drehen. Prellen wäre bimodal → ist es
nicht. **Das `.015 je Rastung` war Overshoot durch die 1-s-Display-Latenz**, kein Bounce.
Voll-Analyse: `radio-panel-measurement.md` §Phase 3.

**Konsequenz umgesetzt (UNCOMMITTED):**
- **Encoder-Debounce ENTFERNT** (`_ENCODER_DEBOUNCE` war No-Op: 16 ms > 8 ms → feuerte nie).
  **Swap-Debounce bleibt** (`_SWAP_DEBOUNCE=0.20`, echter Taster-Chatter, Runde-2-bestätigt).
- **B2 HYBRID gebaut** (User-Wahl) = sofortiges Anzeige-Echo, Sim bleibt Wahrheit, KEINE
  8.33/25-kHz-Kanalisierung lokal nachbauen:
  - **`ReadNow`-Command** (`simconnect/protocol.py`) + **`read_now`-Verb** (`bridge/bridge.py`
    `ClientHandler._read_now`): liest 1 abonnierte Var off-cycle, pusht sofort `state`,
    updatet Sent-Cache (Poll doppelt-frei). Wire-Test `test_protocol.py`.
  - **`RadioPanelController.refresh_after(code)`**: Encoder → getunte STANDBY-Var, Swap →
    active+standby. **Swap lokal gespiegelt** (Cache-Tausch + sofort rendern → Flip ohne
    Sim-Wartezeit). Tests `test_radio_panel.py`.
  - **`OutputManager`**: coalesced `ReadNow` **~90 ms** nach dem Event (Generation-Counter →
    Rast-Burst = 1 Read; 90 ms, damit der Sim das Event angewandt hat, sonst liest man den
    Vor-Event-Wert). Scheduler injizierbar; `_stop`-Gate gegen Late-Fire beim Shutdown.
    `MultiPanelController.refresh_after=[]`. Tests `test_output_manager.py`.
- **Beschleunigung war schon vorher raus** (2026-07-05): inner-Encoder feuert immer den
  feinen Schritt; `fract_fast_*`-Model-Felder bleiben (reversibel).

**⏳ NÄCHSTE SESSION — B2 IN-SIM verifizieren** (`msfs-bridge piper_arrow`, JF Arrow):
Folgt die Anzeige jetzt in ~100 ms statt bis 1 s (Overshoot weg)? Kommt der Swap-Flip
sofort? Falls der Read noch den Vor-Event-Wert erwischt → `_REFRESH_DELAY` (outputs.py, 90 ms)
hoch. **Bridge MUSS neu starten** (neuer `read_now`-Verb): `pkill -f run-bridge.sh` → neu.
Danach immer noch offen: exakte Event-Namen (`fract_fast_*` ungesetzt; COM1-Swap-Variante).

## 📻 RADIO PANEL — HARDWARE-BYTES VERMESSEN (2026-07-05, 125 Tests grün)
**Input+Output am Gerät (06a3:0d05) gemessen — nur noch In-Sim-Events offen.** Der
Code-Pfad steht komplett; die Profil-Input-Codes sind jetzt ECHT (waren Platzhalter):
Selektoren bit0-3/7-10, Swaps **bit14/15**, Encoder bit16-23 (CW=inc, äußere korrigiert);
Display-Zellorder (links=ACTIVE/rechts=STANDBY), Dezimalpunkt `0xD0`, Helligkeit
(`flags=0x00`=hell) alle bestätigt → kein Code-Change output-seitig. Mess-Log:
`docs/memory/radio-panel-measurement.md`. Scope: **COM/NAV zuerst**, Rest später.
- **Chunk A fertig:** `mapping/display.py` → `format_frequency()` + `DOT`-Konstante
  (0xD0, Dezimalpunkt reitet auf der Ziffer). COM/NAV zeigen `118.00`. `NN.NNN`-Shift
  (decimals=3, `18.005`) ist die Fähigkeit dahinter. Tests `test_display.py`. Display
  wird mit Multi Panel geteilt.
- **Chunk B fertig** (`mapping/radio_panel.py` `RadioPanelController` +
  `models.RadioBank/RadioUnit/RadioPanelOutput`, pure/getestet, `test_radio_panel.py`):
  - **Anzeige folgt dem Encoder (implizite Kommastellen):** innerer/feiner Encoder →
    STANDBY-Zeile springt auf `NN.NNN` (3. Nachkommast., führende MHz-Ziffer rollt weg);
    äußerer/grober → `NNN.NN`. Sticky pro Einheit, Default grob. **ACTIVE-Zeile bleibt
    immer grob** (Referenz), nur die getunte STANDBY-Zeile folgt.
  - **Tempo am inneren Encoder = Schrittweite:** langsam → feines Fract-Event (COM
    8.33 kHz), anhaltend schnell → grobes (`fract_fast_*`, 25 kHz). Exakt der Multi-
    Panel-Beschleunigungsmechanismus (`_FAST_WINDOW`/`_FAST_AFTER`, inline gespiegelt).
    NAV ohne `fract_fast_*` → bleibt fein. **Kein Umschaltknopf.**
  - **Event-basiert** wie SPAD: äußerer → `*_WHOLE_INC/DEC`, innerer → `*_FRACT_INC/DEC`,
    Druck → `*_RADIO_SWAP`. Zwei unabhängige Einheiten (upper/lower); `render()` = 20
    Display-Zellen (upper 0-9 / lower 10-19) + 2 Flag-Bytes. `RadioPanelOutput` ist in
    der `Output`-Union (validate OK). Interaktionsmodell-Details: `radio-panel-hid.md`.
- **Chunk C CODE fertig** (verdrahtet analog Multi-Panel-Chunk-D):
  - **Device-Katalog:** `config/devices.yaml` → `radio_panel` (06a3:0d05, hidraw).
  - **OutputManager** (`outputs.py`): neuer `PanelController`-Protocol; Multi + Radio
    laufen jetzt uniform durch `self._controllers`. `RadioPanelOutput` →
    `RadioPanelController` registriert. `runtime` brauchte **keine** Änderung (routet
    schon generisch über `outputs.handles()`/`handle_input()`). `render()` kriegt
    `blink_on` (Radio ignoriert es, hat keine Blink-LED). Tests in `test_output_manager.py`.
  - **Profil** (`piper_arrow.yaml`): `radio_panel`-Output-Block, 2 Einheiten (upper/lower)
    × 4 Bänke (COM1/COM2/NAV1/NAV2) mit echten SimVars + Standard-MSFS-Events.
  - **Scan-Tools:** `tools/panel-scan/scan_radio.py` (Input-Bits) + `out_radio.py`
    (Display/Dezimalpunkt/Flags), README aktualisiert.
- ✅ **Input-Bits gemessen** (2026-07-05, `scan_radio.py`): echte Codes im Profil, alle
  24 Bit gehen auf (Selektoren + innere Encoder trafen die Platzhalter, äußere Encoder
  + beide Swaps waren daneben → korrigiert). Bit-Karte in `radio-panel-hid.md`.
- ✅ **Output verifiziert** (2026-07-05, `out_radio.py`): Zell-Order links=ACTIVE/
  rechts=STANDBY, Dezimalpunkt `0xD0`, Helligkeit `flags=0x00`=hell. Kein Code-Change.
- **⏳ NUR NOCH In-Sim (NÄCHSTE SESSION):** exakte Event-Namen am fliegenden Arrow —
  `fract_fast_*` für echten 8.33- vs 25-kHz-Step (aktuell ungesetzt → schneller Dreh =
  fein wiederholt); COM1-Swap `COM1_RADIO_SWAP` vs `COM_STBY_RADIO_SWAP` gegenprüfen.
  WHOLE/FRACT/SWAP sind MSFS-Standard, sollten direkt laufen.

## 🎚️ ALT/VS-MODI GEMAPPT (2026-07-04, UNCOMMITTED, 106 Tests grün)
Multi-Panel-Tasten **ALT (code 11) / VS (code 12)** verdrahtet — die „versteckten"
Hold-Modi der JF-AutoControl.
- **LED-Read (sauber, sofort korrekt):** neuer generischer `bool_leds`-Mechanismus —
  `MultiPanelOutput.bool_leds` mappt Tastenname→Bool-Var, unabhängig vom `mode_var`-Enum
  (ALT/VS koexistieren mit einem Lateralmodus, passen nicht ins 1-Wert-Enum). Byte-Layout
  = Single-Source-of-Truth in `leds.py` (`_MULTI_BUTTON_BIT`, `MULTI_LED_BUTTONS`),
  `multi_button_led_byte(... , bool_leds=...)` OR't die Bits drauf; `render()` löst die
  Vars auf; `simvars()` abonniert sie; Model validiert Tastennamen. Profil: `bool_leds:
  { alt: L:JF_PA28_AP_alt, vs: L:JF_PA28_AP_vs }`. **LED spiegelt echten Hold-Zustand,
  egal wie eingekuppelt** → auch via Cockpit-Clickspot testbar.
- **Write (Best-Guess, VERIFY):** codes 11/12 → Standard-Toggle-Events `AP_ALT_HOLD`/
  `AP_VS_HOLD` (`value:1` = momentary, 1 Druck = 1 Toggle, kein Doppel). SPAD mappt ALT/VS
  beim Arrow NICHT (keine Referenz) → **⏳ in-sim prüfen:** bleibt die LED nach Druck dunkel,
  ignoriert die JF-Gauge das Event → Fallback im Profil-Kommentar (JF-Bool direkt schreiben).
- Tests: `test_leds.py` (bool_leds-Bits), `test_multi_panel.py` (subscribe/render/validate).

## 🖥️ PROZESS-GUI — PHASE 1 GEBAUT (2026-07-02, UNCOMMITTED)
**Tkinter-GUI** `src/msfs_peripherals_bridge/gui.py`, Start
`uv run python -m msfs_peripherals_bridge.gui`. Buttons Bridge/Mapper start+stop,
Statusampeln (MSFS/Bridge/Mapper), Profil-Dropdown (wirkt beim Mapper-(Neu)start).
**Kern:** jeder Prozess in eigener Prozessgruppe (`start_new_session=True`) +
`killpg`-Stop (SIGTERM→SIGKILL via `poll()`) → ganze Proton/Supervisor-Kette weg, kein
pkill-Selbsttreffer; Bridge-Stop zusätzlich /proc-Sweep nach `bridge/bridge.py` +
`run-bridge.sh`. Status: Port 7842 / Mapper-PID / `FlightSimulator.exe`.
ruff+py_compile clean, 102 Tests grün, Prozess-Logik headless smoke-getestet (Fenster
selbst noch NICHT visuell geprüft; tkinter 8.6 vorhanden). **Phase 2+ (Profil-Editor:
Geräte-Auto-Mapping, Var-Picker mit Kategorie, Bedingungen/CRS/Heading-Bug) in Memory
`project-process-gui`.**

## 🔦 DIMMER-REWORK — LICHT-VARS GEFUNDEN + VERDRAHTET (2026-07-02, alles UNCOMMITTED)

**Durchbruch: alle drei Licht-Vars per LVar-Enumeration gefunden, Profil verdrahtet.**
Ziel war Radio+Panel auf dem Trimrad; heute kam Center-Light dazu.

### ✅ LVar-Enumeration gebaut (der eigentliche Türöffner)
`bridge/bridge.py`: neuer **`MF.LVars.List`-Pfad** → listet ALLE JF-Arrow-L:Vars
(714 Stück) in die `MobiFlight.Response`-Area. Umgesetzt: Response-Area gemappt,
String-Dispatch im `_ReadingSimConnect.my_dispatch_proc` (Route per `dwRequestID`
in `_string_request_ids`; Float-Pfad unberührt), `list_lvars()`-Methode (sammelt
zwischen `.List.Start`/`.End`), TCP-Verb `list_lvars`. **In-sim fehlerfrei gelaufen**
(„Enumerated 714 LVars"). py_compile+ruff clean, 102 Tests grün (bridge.py nicht in Suite).
- **Volle 714er-Liste + kuratierte Tabellen: `docs/simvars-reference.md` §11.**
- Neue Tools: **`tools/list_lvars.py`** (auflisten/filtern), **`tools/read_lvars.py`**
  (mehrere LVars live mitlesen). Beide lint-clean.

### 🎯 LICHT-VARS (alle in-sim 2026-07-02 bestätigt)
- **Radio LTS (Backlight)** = **`L:CENTRE_LOWER_nav_light`** (0..10, schreibbar; read-back
  ok). Zwilling von `panel_light` — irreführender Name, aber der „Radio lts"-Knopf
  schreibt ihn (beim Drehen lief er 1:1 mit). Koppelt zugleich die Außen-Nav-Lights
  (`nav_light_on` folgt >0). **Spiegel (read-only):** `Radio_light_scaler`=(nav_light−1)/9,
  `A:LIGHT POTENTIOMETER:2`≈×10. → Das alte `LIGHT_POTENTIOMETER_2_SET`-Event war die
  Sackgasse (Spiegel, kein Hebel).
- **Panel-Licht** = `L:CENTRE_LOWER_panel_light` (0..10, schon vorher ok). Spiegel:
  `Panel_light_scaler`=/10, `A:LIGHT POTENTIOMETER:3`=×10.
- **Center Light (rotes Dome)** = **`L:LIGHTING_CABIN_0`** (0..100 Helligkeit) **+**
  **`A:LIGHT CABIN`** (0/1 An-Aus-Gate) — **braucht BEIDES.** Ein einzelner Cockpit-Rotary
  setzt beide zusammen; `LIGHTING_CABIN_0`=0 allein lässt ein Restglühen (Gate bleibt an).
  Der Schreibwert **hält** (read-back 0/100 blieb stehen), aber Voll-Aus braucht das Gate.

### ✅ Profil verdrahtet (`profiles/piper_arrow.yaml`, validate OK)
- **Trimrad-Dimmer** (multi_panel, codes 18/19): Ziele jetzt `L:CENTRE_LOWER_nav_light`
  (full 10) + `L:CENTRE_LOWER_panel_light` (full 10). Event-Ziel raus.
- **Switch-Panel code 7 „Cabin center light"** = `sequence`: on_edge
  `LIGHT CABIN=1` + `L:LIGHTING_CABIN_0=100`, off_edge beide=0.

### ⏳ MORGEN (User: „den Test machen wir morgen"), Sim ist AUS
1. **Center-Light-Kombi visuell verifizieren**: geht's mit Switch-Panel code 7 voll an
   **und** ganz aus? Prüfen ob `A:LIGHT CABIN` per SetData schreibbar ist — falls NICHT,
   im Profil auf `{ event: CABIN_LIGHTS_SET, value: 1/0 }` fürs Gate umstellen.
2. **Radio-Schreibtest visuell**: schreibt der Trimrad-Dimmer die Radio-Beleuchtung
   sichtbar? (Read-back war ok; Sim-Absturz kam dazwischen, visuell noch offen.)
3. **ALT/VS-Modi** (Roadmap): **`JF_PA28_AP_alt` / `JF_PA28_AP_vs`** sind die versteckten
   Modi (aus der Enumeration!) — Schreib-Ziel UND LED-Read. Multi-Panel codes 11/12.
   Ganze JF-AP-Familie: `JF_PA28_AP_{master,hdg,nav,omni,roll,alt,vs,loc_norm,loc_rev}`
   (evtl. sauberere Per-Taste-LED-Quelle als `AUTOPILOT_mode`). Siehe §11.

### ⚙️ Betriebsnotizen (weiter gültig)
- **Bridge ist Single-Client** (`server.listen(1)`): Mapper ODER ein Skript. Für direkte
  Reads/Writes **erst den Mapper stoppen**. (Ein 2. Verbinder landet im Listen-Backlog,
  ungelesen — deshalb wirkte ein paralleler Schreibtest wirkungslos.)
- **pkill-Selbsttreffer-Falle (Exit 144):** Muster steht in der eigenen Kommandozeile →
  **per PID killen** oder Bracket-Trick `pkill -f 'run-bridge[.]sh'` NUR wenn die eigene
  Zeile das Muster nicht enthält. Bridge-Start: `setsid bash bridge/run-bridge.sh &`.
- **Value-Read-Pfad (LVars via MobiFlight) ist zuverlässig** — Selbst-Test: geschriebene
  Werte streamten in ~1 s zurück. `_lvar_values` warm nach 1. Stream; frische Multi-Var-
  Subs haben kurze Anlauf-Verzögerung.
- **Prozess-Stand Session-Ende:** MSFS **aus** (User), Bridge+Mapper **gestoppt**. Neu
  hochziehen: `msfs-bridge piper_arrow`. Für Messungen: nur `setsid bash bridge/run-bridge.sh &`
  (ohne Mapper), dann Tools.
- Mess-Skripte lagen im Job-tmp (Session-flüchtig) — die **wiederverwendbaren** sind jetzt
  `tools/list_lvars.py` + `tools/read_lvars.py` im Repo.

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
- 🔧 **Chunk C — LVar-READ IMPLEMENTIERT (UNCOMMITTED, 2026-07-01), IN-SIM ZU TESTEN.**
  Ziel: `L:AUTOPILOT_MODE` lesen → Modus-Tasten-LEDs (NAV/HDG/APR/REV). Befund beim
  Lesen des Codes: der ganze LED-Renderpfad war schon fertig (`multi_button_led_byte`,
  `simvars()` abonniert `mode_var` + `ap_master`), **die AP-Master-LED leuchtet schon**
  (Standard-A:-Var, lesbar). Einziger Bruch: **Bridge konnte L:-Vars nicht LESEN** →
  `L:AUTOPILOT_MODE` kam nie an. **Fix komplett in `bridge/bridge.py`, Linux-Seite
  unberührt** (py_compile+ruff grün, 93 Tests grün — bridge.py ist nicht in der Suite):
  - `_ReadingSimConnect(SimConnect)` überschreibt `my_dispatch_proc` → liefert
    `RECV_ID_CLIENT_DATA` (MobiFlight-LVar-Stream) an `on_client_data`, Rest an super().
  - LVar-Read-Kanal: `MobiFlight.LVars`-Area gemappt; pro L:-Var `MF.SimVars.Add.(name)`
    + `AddToClientDataDefinition`/`RequestClientData` (ON_SET+CHANGED, Slot=Add-Reihenfolge,
    `MF.SimVars.Clear` beim Init → saubere Indizes nach Reconnect). Protokoll+ctypes-Sigs
    aus dem echten Modul/der Lib auf Platte verifiziert (kein Raten). Float32-Werte.
  - Dispatch-Thread schreibt Werte in `_lvar_values` (eigener `_lvar_lock`, **kein
    DLL-Zugriff** → kein Deadlock mit dem `_lock`). Poll-Loop ruft `read_subscribed`:
    `L:/H:/B:`→`read_lvar` (registriert+Cache), sonst `read_simvar` wie bisher.
  - **Annahme:** Bridge ist einziger Nutzer der shared MobiFlight-Areas (stimmt hier;
    SPAD.neXt nutzt eigenen Kanal). Falls je Index-Kollision → auf privaten
    `MF.Clients.Add.<name>`-Kanal umstellen (kleiner Umbau).
  - ⏳ **IN-SIM-TEST:** Bridge NEU starten (`pkill -f run-bridge.sh` → `run-bridge.sh`),
    `msfs-bridge piper_arrow`, JF Arrow, AP-Master an + Modus wählen → NAV/HDG/APR/REV-LED
    muss leuchten. Log: „MobiFlight LVar registered: L:AUTOPILOT_MODE (slot 0)". Bleibt's
    dunkel: (a) leuchtet AP-Master-LED überhaupt? (b) ist `L:AUTOPILOT_MODE` der richtige
    Var-Name für die JF-Arrow-Modi? via MobiFlight-Browser / SPAD gegenprüfen.
  - **NOCH OFFEN (separat):** Modus-Tasten HDG/NAV/APR/REV als Writes (codes 8/9/13/14)
    liegen schon als SequenceActions im Profil (SPAD-Werte NAV=0/HDG=2/APR=3/REV=4).
    Der neue Read-Pfad ist NUR für die LED-Rückmeldung. Siehe multi-panel-hid.md.
  - ✅ **In-sim bestätigt vom User (2026-07-01): Modus-LEDs leuchten** (Read-Pfad läuft).
- 🔧 **LED-Verfeinerungen (UNCOMMITTED, 2026-07-01, Linux-Seite, 97 Tests grün) — NUR
  MAPPER-RESTART nötig (Bridge läuft weiter):**
  - **OMNI (mode 1) = NAV solid + IAS blinkt** (1 Hz), damit OMNI von echtem NAV
    (mode 0) unterscheidbar ist. Neu: `_MULTI_MODE_BLINK_BIT={1:IAS}` in `leds.py`,
    `blink_on`-Param an `multi_button_led_byte`/`render`; **Blink-Ticker** in
    `outputs.OutputManager` (`_blink_on` + `_blink_loop`/`_blink_tick`, Toggle alle
    `_BLINK_HALF_PERIOD`=0.5 s, re-rendert alle Devices, dedup-Guard = keine HID-Flut).
  - **Modus-LEDs unabhängig vom AP-Master**: `ap_master==on`-Bedingung fürs Mode-
    Leuchten RAUS (nur die AP-LED selbst bleibt master-gekoppelt) → Positions-Feedback
    der Mode-Tasten auch im Off-Zustand. ⚠️ **In-sim prüfen:** wenn `L:AUTOPILOT_MODE`
    im „nichts gewählt"-Zustand 0 (=NAV) meldet, leuchtet NAV dann dauerhaft — dann
    bräuchte es einen Off-Sentinel. User beobachtet das beim Test.
- 🔧 **AP-Master-Prellen gefixt (UNCOMMITTED, 2026-07-01, Mapper-Restart) + JF-Verhalten
  geklärt.** In-Sim-Befund (2026-07-01):
  - **AP-Master-Taste (multi code 7) „muss mehrfach drücken / springt auf aus".** NICHT
    der Doppelflanken-Bug (Engine feuert `AP_MASTER` nur auf Enter, `engine.py:80`) →
    **Kontaktprellen**. `_bounced` maß bisher „seit letztem *akzeptierten* Druck" +
    stempelte nur akzeptierte Flanken → ein Prell-Edge >50 ms nach dem ersten rutschte
    als 2. Toggle durch (netto AUS). **Fix (`runtime.py`):** Debounce **retriggerbar**
    (jede Enter-Flanke, auch unterdrückte, schiebt das Fenster) + Fenster **50→120 ms**.
    Test `tests/test_runtime.py`. Falls in-sim noch Prellen: Fenster höher.
  - **Modusschalter springt auf HDG beim AP-Einkuppeln** = **JF-Arrow-Verhalten** (unsere
    AP-Taste sendet NUR `AP_MASTER`, setzt kein `L:AUTOPILOT_MODE`). Nicht unser Code.
  - **APR nicht direkt anwählbar** = **JF-Gauge-Logik BESTÄTIGT** (User in-sim
    2026-07-01: mit AP-Master ON **und HDG-Modus aktiv** nimmt APR direkt an; aus
    frisch-eingekuppeltem „leerem" `L:AUTOPILOT_MODE` nicht). **FIX (UNCOMMITTED):**
    AP-Master-Taste (code 7) ist jetzt eine `sequence` → `on_edge` feuert `AP_MASTER`
    **und** setzt `L:AUTOPILOT_MODE=2` (HDG), landet also immer in einem gültigen Modus,
    aus dem APR direkt geht. Momentary (nur Enter-Flanke), mode=2 auf der Aus-Presse
    harmlos. `piper_arrow.yaml`, valide. ⏳ in-sim bestätigen.
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
