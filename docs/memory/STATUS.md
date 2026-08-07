# STATUS — Resume-Anker

> Kurzer Einstiegspunkt: was läuft, was offen ist, wie es weitergeht.
>
> ## CUT 2026-08-07 — SCHRITT A FERTIG + evdev-ACHSEN-CAPTURE, 390 Tests grün, ruff clean
> **COMMITTET (nicht gepusht):** `0c84e58` Schritt A (`template_elements`). Danach evdev-Achsen-Capture gebaut (uncommitted bis zum nächsten Commit).
> **① Schritt A (`0c84e58`):** reine **`gui_mapper.template_elements(ddef, profile) → (list[InputBlock], list[OutputBlock])`** — projiziert das HEUTIGE hartverdrahtete Mapping eines Geräts in atomare Bausteine: jedes Plain-Binding → 1 `InputBlock` (kind+code+Achsen-Kalibrierung aus `source`; **Hat → `selector`** über seine Richtungs-Codes); jeder Panel-Controller-Output → seine Input-CONTROLS als `InputBlock` (Wert-/Ring-Encoder, Modus-Wahl-Selektor, SWAP, Dimmer) **plus** physische WRITE-Atome als `OutputBlock` (Multi: 8 Knopf-LEDs + 1 Display cells=10; Radio je Unit: außen/innen-Encoder + SWAP + Modus-Selektor, dazu Aktiv+Standby-Display je 5 Zellen; Switch: 3 Fahrwerks-LEDs). **GUI:** im Elemente-Editor (`gui.py _open_input_scan`) Button **„Aus Vorlage füllen…"** → `_fill_from_template` merged NUR fehlende Blöcke (dedup per Name), Confirm-Dialog, `_persist`+`_refill`. 4 headless-Tests.
> **② evdev-Achsen-Live-Capture (NEU, uncommitted):** reine **`evdev_reader.winning_axis(spans, min_span=8)`** (Pendant zu `hidraw_reader.winning_code`: breiteste beobachtete Achsen-Spanne gewinnt; Hat-±1 wird per Schwelle gefiltert) + 4 Tests (`tests/test_evdev_reader.py`). **GUI:** `_open_input_scan` holt jetzt auch einen `evdev_path`; „Achse" im Input-Menü ruft neues **`_capture_axis`** (live `live_state_reader`, akkumuliert je ABS-Kanal min/max, zeigt „erkannt: Achse N [lo..hi]", „Fertig" → `InputBlock(kind=axis, code, raw_min, raw_max)`). Damit ist Yoke/Pedale/TQ6-Achsenscan komplett (vorher nur Meldung „folgt").
> **🔴 SOFORT nächste Session:** (1) **② committen + beide pushen** (User fragen). (2) **VISUELL prüfen** (Display+HW): Mapper → „🔍 Geräte-Explorer…" → Gerät → „Geräteelemente…" → **„Aus Vorlage füllen…"** (landen Encoder/Selektor/LEDs/Display in den 2 Baum-Gruppen?) und **„+ Input anlernen… → Achse"** an Yoke/Pedale (erkennt es die bewegte Achse + Range?). (3) **Schritt E** (Nordstern-Rest).
> **⚠️ TRANSITIONS-HINWEIS (bewusst so gelassen):** solange die Templates die Laufzeit treiben, zählt die Geräteübersicht geseedete Blöcke ZUSÄTZLICH zu den Template-Atomen (leichte Doppelzählung in `atomic_{in,out}put_count`). Löst sich mit **Schritt E** auf, der die Templates durch die generische Laufzeit über `ddef.inputs/outputs` ERSETZT (= echte Parität, großer Brocken, jetzt der Nordstern-Rest). Offene evdev-Lücke: Buttons/Switches eines FRISCHEN evdev-Geräts (ohne Bindings) noch nicht im Wizard scanbar (nur Achsen); Binding-Editor + „Aus Vorlage füllen" decken die bereits gemappten ab.
>
> ## CUT 2026-07-21 (spät) — alles committet+GEPUSHT (`3b56c2b`, origin), Tests grün, ruff clean
> **Diese Session gebaut+gepusht:** Baukasten A (inventory/Overlay/Explorer/CLI `inventory`) · B (Input-Scan `InputBlock`) · C-Kern („📋 Benannt" Alias→Quelle) · Eingang-Anlernen vereinheitlicht · **atomares Element-Mgmt** (`OutputBlock`, Lese/Schreib GETRENNT, 2 Menüs, `atomic_{in,out}put_count` Encoder=1) · Doku (INSTALL Schritt-für-Schritt+Distro/Prefix, `geraete-baukasten-konzept.md`) · Monitor-Tab-Rename · Achse ins Input-Menü · Elemente-Fenster Single-Instance/lift.
> **🔴 SOFORT-TODO nächste Session (visuell UNGEPRÜFT — User will live sichten):** GUI starten → Geräte-Explorer → Gerät registrieren → „Geräteelemente…" → Input/Anzeige anlegen. **Offene Bugs/Lücken:** evdev-**Achsen-Live-Capture** fehlt (Menü da, `_capture` nur hidraw → Meldung „folgt"); **A NICHT fertig** = `template_elements(ddef,profile)` (Vorlage→atomare `InputBlock`/`OutputBlock` für ALLE verbundenen Geräte) + „Aus Vorlage füllen"-Button — `InputBlock.selector`+`positions` als Groundwork schon da. **Danach Schritt E** (generische Laufzeit = echte Parität, Templates raus). Kontextuelle Sonderfunktionen (Encoder→Step, Achse→Detent, 7seg-Zellen) offen. Nordstern-Details siehe unten + `geraete-baukasten-konzept.md`.
>
> ## Stand 2026-07-21 — SAUBER + DOKU/ONBOARDING-BATCH (uncommitted)
> **Repo clean bis HEAD, alles committet & GEPUSHT** (`feat/mapper-panel-nachbau` = origin, 0 ahead/0 behind), **~358 Tests grün, ruff clean.** Der gesamte Radio-Redesign/Selektor-/Encoder-Capture-Batch ist committet (`775589e…af20633`) — die „uncommitted"-Absätze WEITER UNTEN sind damit ERLEDIGT (nur noch Historie).
> **Diese Session (NOCH UNCOMMITTED — User hat nicht „committen" gesagt):**
> - 📘 `docs/INSTALL.md` zur echten **Schritt-für-Schritt-Anleitung** für fremde User umgebaut (App → udev/eigene HW → Gerät registrieren → GUI-Mapping → Wine-Bridge → Fliegen, mit ✓-Checkpoints) + **Distro-Hinweis** (Mint/Fedora/Arch/CachyOS: udev identisch, nur `lsusb`=usbutils je Distro) + **Prefix-Pfad-Tabelle** (nativ / `.local/share` / Flatpak-Steam / zweite Library → `STEAM_ROOT`/`STEAM_COMPAT_DATA_PATH`).
> - 🏷️ GUI-Tab **„Variablen" → „Monitor"** (i18n-Key `tab.variables`→`tab.monitor`, gui.py:1309). **Offenes Konzept (User):** im Monitor-Tab sollen künftig ALLE Variablen auch **aus dem Sim geprüft** (live gelesen) werden — noch kein Konzept.
> - 📄 NEU `docs/geraete-baukasten-konzept.md` — Konzept **Geräte-Baukasten** (s. u.).
> - ✅ **BAUKASTEN-SCHRITT A GEBAUT** (Auto-Enumeration + Geräte-Explorer, 370 Tests grün, ruff clean, live+headless verifiziert): reines `devices/inventory.py` (`RawDevice`/`InventoryItem`, **pure `classify()`** = alle evdev+hidraw-Nodes → dedupt + katalog-getaggt registriert/unregistriert; evdev-Shadow eines hidraw-Panels wird unterdrückt; 6 Tests). CLI **`msfs-bridge inventory`** (zeigt ALLE Geräte inkl. fremder). **User-Overlay** `config.devices_overlay_file()` = `~/.config/msfs-peripherals-bridge/devices.local.yaml`; `loader.load_device_catalog` merged es transparent (neue id append, gleiche id override), `loader.add_device_overlay()` schreibt (6 Tests). GUI: **„🔍 Geräte-Explorer…"**-Button (Mapper, neben „Geräte neu erkennen") → Dialog listet inventory, „Registrieren…" → simpledialog Kurz-ID → schreibt Overlay → reload. **🔴 GUI visuell UNGEPRÜFT** (Dialog headless gebaut, kein Klick am Display). Entscheidung getroffen: Overlay in user-config (nicht versionierte `devices.yaml`).
> - ✅ **BAUKASTEN-SCHRITT B GEBAUT** (Eingänge scannen & benennen, 375 Tests grün, ruff clean, Modell/Persistenz headless verifiziert): **`models.InputBlock`** (kind button/switch/axis/encoder, name-Alias, code bzw. cw/ccw bzw. raw_min/max) + **`DeviceDef.inputs`** (optional, rückwärtskompatibel). Reine **`hidraw_reader.winning_code(counts,min_edges)`** (argmax der Flankenzähler, extrahiert). **`loader.set_device_inputs(ddef,blocks,overlay)`** persistiert via `add_device_overlay`. GUI: im Geräte-Explorer **„Eingänge scannen…"** (nur für registrierte) → Assistent `_open_input_scan`: **EIN vereinheitlichtes „+ Eingang anlernen…"-Menü** (Taster/Schalter/Encoder als gleichwertige Typen, datengetrieben `add_kinds`; Encoder = „spezielle Scan-Form" mit 2 Schritten cw/ccw — Knopf- und Encoder-Logik zusammengeführt per User) → geführte Capture (`edge_count_reader`+`winning_code`, „mehrmals drücken/drehen"→Gewinner) → Name (simpledialog) → InputBlock → Overlay → Liste + Mapper-Reload; jederzeit nachträglich erweiterbar; „Entfernen". **Nur hidraw-Live** (Saitek); evdev-Achsen-Capture = Follow-up (Meldung). **🔴 GUI visuell UNGEPRÜFT.** 5 neue Tests (winning_code 2, InputBlock/inputs-Persistenz 3).
> - ✅ **ATOMARES ELEMENT-MANAGEMENT GEBAUT** (User: „nicht nur die Statistik — das GANZE Input/Output-Management muss atomar sein; Lesen/Schreiben getrennt darstellen; ein Menü für Anzeigen, eins für Inputs; 1 LED→1 Output, 1 Encoder→1 Input", 382 Tests grün, ruff clean): **`models.OutputBlock`** (led/display mit `cells`/`display_kind` + optional report/bit/offset für späteren Output-Scan) als Gegenstück zu `InputBlock`; **`DeviceDef.outputs`** getrennt von `.inputs` (beide rückwärtskompatibel). `loader.set_device_outputs` (+ `set_device_inputs`, Wizard schreibt jetzt BEIDE Listen in EINEM `add_device_overlay`). Element-basierte Zählung: **`gui_mapper.panel_input_elements`** (Encoder=1, Selektor=1 — nicht Codes), `atomic_input_count`/`atomic_output_count(ddef,profile)` (LEDs+Zellen bzw. `OutputBlock`-Zellen). GUI: Explorer-Button **„Geräteelemente…"** → Editor mit **getrennten Baum-Gruppen „Inputs (Lesen)"/„Anzeigen (Schreiben)"** + **zwei konsistenten Menüs „+ Input anlernen…"** (Taster/Schalter/Encoder, geführte Capture) **/ „+ Anzeige hinzufügen…"** (LED/Display-7seg mit Zellenzahl, manuell — Live-Output-Scan = Schritt D). 6 neue/angepasste Tests. **🔴 GUI visuell UNGEPRÜFT.** **▶ OFFEN (dok. in konzept.md): kontextuelle Sonderfunktionen je Typ (Encoder→Step, Achse→Detent-Split nur auf Wunsch, 7seg frei vs. Multipanel-Display fix/selektor-getrieben); Nachbau-als-Editor (Tabelle weg, verschieben/größen/Sinngruppen, ein-/ausklappbares Menü rechts) = großer Batch nach E.**
> - ✅ **BAUKASTEN-SCHRITT C (Kern) GEBAUT** (Alias→Quelle-Brücke, 377 Tests grün, ruff clean): reine **`gui_mapper.device_input_sources(ddef)`** → `[(label,kind,code)]` aus `ddef.inputs` (Encoder → 2 Richtungen CW/CCW als button, code-lose übersprungen; 2 Tests). GUI: im **Binding-Editor** neuer Menubutton **„📋 Benannt"** neben dem 🪄 — baut sein Menü live aus den gescannten Eingängen des Binding-Geräts, Auswahl setzt `ev["kind"]`+`ev["code"]`. So mappt man per NAME statt rohem Code. **🔴 GUI visuell UNGEPRÜFT.** OFFEN in C: (b) benannte Inputs im Nachbau/Geräteliste anzeigen, (c) evdev-Achsen-Kalibrierung.
> **🔑 WICHTIGER BEFUND (User-Frage beantwortet):** Fremdes Gerät wird beim reinen USB-Anstecken **NICHT** automatisch erkannt — Erkennung ist **katalog-gebunden** (`evdev/hidraw_reader.discover` matchen nur `config/devices.yaml`; `DeviceDef` = nur USB-Match, kennt KEINE Bausteine; Panel-Struktur hardcodiert). `msfs-bridge scan`/`capabilities.scan()` zeigt nur evdev-Controller roh, legt nichts an.
> **▶ NÄCHSTE VISION (User, über mehrere Nachrichten präzisiert — noch KONZEPT, nicht gebaut): GERÄTE-BAUKASTEN.** Fremde User sollen ihre Geräte (Knöpfe + Anzeigen: LED/Display/7-Segment) selbst **anlegen, kalibrieren, mappen** wie aus Bausteinen. Bausteine: Ein = button/switch/axis/encoder/selector/hat, Aus = led/sevenseg/display-bank/dot. Braucht NEUE Datenschicht `DeviceSpec` (user-Overlay `devices.local.yaml`, getrennt vom Mapping) + GUI-**Geräte-Explorer** (Kontextmenü an der Geräteliste): Auto-Enumeration → „neues Gerät" → Input-Scan + **Alias** (`edge_count_reader`) → Kalibrieren → **Output-Scan** (generalisiertes `panel_probe`, LED/Zelle durchprobieren) → speichern. Reihenfolge-Vorschlag A→E + offene Entscheide (Overlay-Ort, udev per pkexec?, wie tief data-driven) in `docs/geraete-baukasten-konzept.md`.
> **🎯 NORDSTERN (User 2026-07-21): ALLE aktuell angeschlossenen Geräte mit dem NEUEN atomaren Gerätemanagement „nachbauen", sodass der User dieselben Funktionen hat wie heute über die hardcodierten Templates (Saitek switch/multi/radio, Yoke, TQ6, Pedale).** Zwei Schichten: (a) **STRUKTUR** = jedes Gerät als atomare `InputBlock`/`OutputBlock` ausdrücken (aus Profil-Bindings + `panel_probe.probe_targets` + Controller-Elementen ableitbar → reine Funktion `template_elements(ddef,profile)`, headless-testbar, „aus Vorlage füllen"-Button im Elemente-Editor). (b) **FUNKTION** = generische Laufzeit (Schritt E), die diese atomaren Elemente wirklich mappt/rendert/LED-aus-Sim treibt und die Templates ERSETZT. „Gleiche Funktionen" = BEIDE. Ohne E sind geseedete Elemente nur Labels. Reihenfolge: (a) seeden [jetzt baubar] → (b) E [großer Brocken].**
> **🔴 TODO nächste Session:** (1) **Geräte-Explorer + Geräteelemente visuell am Display prüfen** (Mapper → „🔍 Geräte-Explorer…" → Gerät registrieren → „Eingänge scannen…" → Knopf/Encoder am Saitek anlernen → landen die Aliase in der Liste/Overlay?). (2) **Schritt C:** die gescannten InputBlocks NUTZBAR machen — (a) im Nachbau/Mapper anzeigen, (b) beim Binding-Anlegen als benannte Quelle vorbelegen (heute referenzieren Bindings rohe Codes; Alias→Code-Brücke), (c) Achsen-Kalibrierung (evdev-Achsen-Capture, aktuell nur hidraw). (3) **Schritt D:** Output-Scan (LEDs/Display durchprobieren, generalisiertes `panel_probe`). (4) **Schritt E:** generische Output-Modelle (LED-aus-Sim + Display-Werte datengetrieben) = Paritäts-Knackpunkt. (5) Monitor-Sim-Prüf-Konzept. (6) Nachbau visuell/HW sichten. Optional zurückgestellt: Arduino/seriell.
> ---
> Stand: **2026-07-20 (spät) — TEST-SEND + ENCODER-CAPTURE gebaut & GEPUSHT; Radio-Editor/Nachbau-REDESIGN offen (voll spezifiziert).**
>
> **🟢 COMMITTET & GEPUSHT (`feat/mapper-panel-nachbau`, 351 Tests grün, ruff clean):**
> `62211e8` Test-Send 🔦 (Ausgänge identifizieren) + Encoder-Labels + „Bind"-Statistik + grüner Button ·
> `7454bd5` Doppelencoder-Capture (flanken-fangender `edge_count_reader` + geführte Sequenz + Invert) ·
> `70dc6c8` Capture verallgemeinert (Multi-Trimmrad + Radio) · **Redesign-Commit** (Außen/Innen/SWAP-Split + Nachbau).
> (Alle committet; ggf. `git push` prüfen, falls Session unterbrochen wurde.)
>
> **🟡 UNCOMMITTED, NICHT von mir, NICHT committet — ENTSCHEIDEN:** `profiles/piper_arrow.yaml` hat `kind: switch`→
> `kind: button` auf den **multi_panel-Bindings** (AP master/HDG/NAV/…). Laufzeit-relevant an fliegbarem Profil, Herkunft
> unklar (evtl. GUI-Test; passt zu „Multi-Knöpfe sind Taster"). **Bewusst nicht angefasst** — prüfen ob gewollt (button =
> nur Press-Flanke statt beider Flanken), dann committen oder `git checkout`.
>
> **🟢 REDESIGN RADIO-EDITOR + NACHBAU — GEBAUT (uncommitted; Wünsche 1–6 unten als Beleg, VISUELL/HW UNGEPRÜFT):**
> Die committete Encoder-Capture (`70dc6c8`) ist konzeptionell ÜBERHOLT und MUSS umgebaut werden. **HW-Fakten vom User:**
> der Radio-Doppelencoder hat **NUR 2 Ringe (außen+innen), KEINEN Druck**; der **SWAP ist ein SEPARATER, normaler Taster**
> (wie die Multi-Panel-Knöpfe). Konkrete Wünsche:
> 1. **Capture aufsplitten** (statt 1 „Doppelencoder" mit 5 Feldern inkl. „Druck"): **Außen-Ring** (outer_cw/ccw, 2 Richtungen
>    + Invert) · **Innen-Ring** (inner_cw/ccw, + Invert) · **SWAP-Taster** (swap, EIN Button-Code, `edge_count_reader`
>    „mehrmals drücken"→Gewinner). Modell bleibt (`RadioUnit.outer_cw/ccw/inner_cw/ccw/swap`), nur die GUI-Gruppierung ändert.
> 2. **Anlernen zieht in „außen"/„innen"-Elemente** — das obere „Doppelencoder"-Element muss KOMPLETT VERSCHWINDEN.
> 3. **🔦 „LEDs/Display testen…" NUR im Kontextmenü von Displays/LEDs**, NICHT bei Encoder/Swap/Selektor. Gate: 🔦 nur wenn
>    Gruppe KEINE Capture-Spec hat (kein Input-Control). Input-Controls zeigen NUR ihr „Anlernen…".
> 4. **Alle Knöpfe konsistente Menüs** (Swap, Multi-Knöpfe, Selektor-Positionen als Taster mappbar).
> 5. **Nachbau-Layout Radio:** LINKS eine Spalte mit dem gewählten **Mode** (Selektor-Position), NICHT im Symbol-Display;
>    Display zeigt nur **„Act"/„Stby"**; **Selektor-Code je Zeile im Tooltip**.
> 6. **Editor je Unit:** getrennte Blöcke Außen-Ring / Innen-Ring / SWAP-Taster (jeweils eigenes Capture; Ringe mit Invert).
> **✅ 1–6 GEBAUT (uncommitted, 352 Tests grün, ruff clean, headless verifiziert — VISUELL/HW UNGEPRÜFT):**
> (a) gui.py `_capture_spec`→**`_capture_specs`** (LISTE): **Außen-Ring** / **Innen-Ring** (je 2 Richtungen + 1 Invert) /
> **SWAP-Taster** (1 Button) / **Trimmrad** (Multi). `_fields_form` rendert je Block ein `_encoder_block` (Loop);
> **🔦 „LEDs/Display testen…" nur wenn `not specs`** (= Displays/LEDs, nicht Encoder/Swap/Trimmrad). (b) `panel_layout.
> _radio_panel` neu: oberes Element WEG; je Unit „außen"/„innen" (ENCODER, focus outer_cw/ccw bzw. inner_cw/ccw) +
> „SWAP-Taster" (BUTTON, focus swap); **Mode-Spalte links** (SELECTOR, ref=ganze Bank, Selektor-Code im `action`/Tooltip);
> Display **„Act"/„Stby"** (SEGMENT, focus active/standby); DOT. (c) Test in 2 gesplittet (mode-row + unit-rings/swap).
> **✅ SELEKTOR-CAPTURE GEBAUT:** jedes `code`-Feld (Selektor-Position, außer source_toggle) hat einen **„🎚 anlernen"**-Knopf
> → `_capture_code_into` (Ein-Code via `edge_count_reader`, „auf Position drehen"→Gewinner, setzt das Entry, Speichern mit dem
> Formular). Bank bleibt Display-Kontext (🔦 sichtbar), da `code` weiter ein Feld ist. **🔴 NOCH OFFEN:** **Multi-Panel-Knöpfe**
> (AP/HDG/NAV… = Bindings im binding-Editor) sollten dieselbe robuste Capture bekommen — d. h. `gui.py._learn_code` (nutzt noch
> den ZUSTANDS-`live_state_reader`, verschluckt transiente Tastendrücke) auf `edge_count_reader` umstellen.
> **`edge_count_reader` ist die Basis für ALLE Captures** (Encoder-Ringe, Swap, Selektor, künftig Multi-Knöpfe/Bindings).
> **🆕 #5 PRÄZISIERT (User): JEDE EINZELNE DISPLAY-ZIFFER/ZELLE muss mappbar sein** — nicht nur bank-weise active/standby,
> sondern pro Zelle (inkl. Konstante wie DME-Bindestrich + Punkt-als-Pointer). Das ist der große „Render-Logik→Modell"-Umbau
> (heute `_render_dme/_render_adf/_render_xpdr` + `format_*` hartverdrahtet). Test-Send (`panel_probe`) adressiert schon
> pro Zelle — die MAPPING-Seite (Zelle→Var/Konstante) fehlt noch.
> ---
> Stand: **2026-07-20 — TEST-SEND „wo landet das Signal?" GEBAUT (uncommitted), 346 Tests grün.**
> **🆕 NEU (User-Konzept geklärt: der Output-🪄 soll TESTSIGNALE auf ein Element schicken, damit man am
> echten Panel sieht, welche LED/Display-Zelle ein Feld treibt — wie `tools/panel-scan/out_*`, aber pro Element
> in der GUI):** (1) **Reine Schicht `mapping/panel_probe.py`** (8 Tests): isolierte Feature-Reports —
> `switch_led_report` (Fahrwerk grün/rot je Rad), `multi_led_report` (1 Knopf-LED), `multi_cell_report`/
> `radio_cell_report` (Ziffer „8" bzw. „8." mit Punkt auf EINE Zelle), `blank_report`, `probe_targets(output)`
> zählt alle physischen Elemente je Panel auf (Fahrwerk=6, Multi=8 LEDs+10 Zellen, Radio=20 Zellen mit dot_report).
> **⚠️ Modul heißt `panel_probe` (NICHT panel_test — matcht sonst pytest `*_test.py`), Fn `probe_targets` (NICHT
> test_targets — sonst als Test eingesammelt).** (2) **GUI-Fenster `_open_panel_test`** (gui.py, vor
> `_open_output_editor`): scrollbare, gruppierte Liste aller Elemente, je 🔦 (+🔦. für Zellen-Punkt) → sendet
> Report, leuchtet ~2 s, „Alles aus" + Auto-Clear beim Schließen. **Geräte-frei-Sperre** via neuem `_mapper_running()`
> (liest `/proc`, `_MAPPER_MATCHES`): läuft der Mapper, wird der Test verweigert (sonst überschreibt sein
> OutputManager sofort). (3) Start-Knopf **„🔦 Testen…"** in der Output-Editor-Knopfzeile (`_fields_form`). **NUR
> Test-Send gewählt** — der 🪄-LAUSCHEN-Modus für Eingang-Codes ist NICHT verdrahtet (Design steht: `_open_code_capture`
> aus `_learn_code` extrahieren, siehe Roadmap-Punkt 2). **🔴 VISUELL/HW UNGEPRÜFT** (Fenster braucht Display + Panel):
> beim Start GUI→Mapper→Output-Editor eines Panels öffnen→„🔦 Testen…"→Element wählen→leuchtet die richtige LED/Zelle?
> Ruff/F821/py_compile/Import-Smoke ok, `panel_probe`-Logik voll getestet.
>
> **▶ ROADMAP PANEL-AUSGABE (User-Vision, in einer Session ausgebreitet — nach Prio geordnet, aktuell gewählt = #1):**
> **1 · Test-Send** ✅ Fundament+GUI (dieser Stand). **2 · Output-LERNEN (🪄 Codes lauschen)** — Encoder/Selektor/
> Swap/Dimmer-Code-Felder am Gerät aufnehmen; Design steht (`_open_code_capture` aus `gui.py._learn_code` extrahieren,
> Code-Felder = {code,cw,ccw,outer_cw,outer_ccw,inner_cw,inner_ccw,swap}; source_toggle liest von seinem eigenen
> `device`). **3 · Live-Werte in Labels (Glow-aus-Sim)** — Output-Element abonniert seine Var via `_ValueMonitor`,
> zeigt gelesenen Wert im Label (User: „falls vorhanden"; „nur kühe"?? = unklar, evtl. „nur Kür"=optisch — NACHFRAGEN).
> **4 · Radio-Nachbau optisch treu** — ROTE 7-Segment-artige Schrift, PUNKT als Pointer/Selektor sichtbar, ADF-
> Doppelpunkt, DME-Bindestrich korrekt (Canvas-Rendering). **5 · ALLES per Profil konfigurierbar (großer Brocken,
> Umfang mit User klären):** ✅ **AP-Mode-LED-Map ERLEDIGT** — `MultiPanelOutput.mode_leds` (Mode→Button-Name) +
> `mode_blink_leds`, name-basiert & per-Flugzeug, Default = JF-Arrow-Map (kein Verhaltenswechsel); `multi_button_led_byte`
> nimmt beide Maps; im Editor read-only-Zusammenfassung (GUI-Editor dafür = Follow-up). NOCH HARTVERDRAHTET: DME-Layout
> (`_render_dme`, Bindestrich=BLANK-Spacer, „Konstante auf bestimmtem Segment" gewünscht), ADF-Zwei-Punkt-Paar
> (`_render_adf`) → ins Modell heben + Editoren; **jede Display-Ziffer einzeln mappbar** (s. #5 unten). Lohnt v. a. für
> FREMDE Flugzeuge. **Alles intuitiv.**
> **📌 SEPARAT ANGEFRAGT, ZURÜCKGESTELLT (User wählte erst STATUS-Batch):** (a) **Geräte-Registrierung für unbekannte
> Geräte** (fremde Rechner): heute nur statisch in `config/devices.yaml` (Vendor/Product), KEINE GUI zum Anlegen,
> `discover()` zeigt nur bekannte; geplant = Enumerator aller USB-Geräte + GUI „Neues Gerät" + user-schreibbarer
> Overlay + udev-Rule generieren (der „Geräte-Explorer"-TODO ist der halbe Weg). (b) ✅ **INSTALL-Guide GESCHRIEBEN**
> `docs/INSTALL.md` (uv/Python/udev inkl. EIGENE Hardware eintragen · Gerät registrieren · Wine-Bridge · Troubleshooting;
> im README verlinkt). — **Zifferweise Vars** (Frage geklärt):
> XPDR=gepackte BCD16 `TRANSPONDER CODE:1`+`XPNDR_SET` (Ziffern-Logik machen WIR, kein Sim-Feature); ADF=Krücke, 3
> Gauge-LVars `L:KR85_dig{1,2,3}_counter` weil Standard-ADF-SimVars kaputt; DME=nur Anzeige. Fremde Flugzeuge: Standard-
> Events zuerst, LVar-Enumeration (`MF.LVars.List`) als Fallback. Das ist der EINGABE-Pfad, getrennt vom Test-Send.
>
> **🔧 LIVE-FEEDBACK dieser Session (alles verifiziert grün, 347 Tests, ruff clean, uncommitted):**
> Test-Send funktioniert am ECHTEN Gerät (User bestätigt „testen der ziffern funzt"). Fixes:
> (a) **Encoder-Labels entwirrt** (`gui_mapper.OUTPUT_FIELD_HELP`): „Äußerer Knopf rechts/links" → **„Außen · im UZS/
> gegen UZS"**, „Innen · …"; swap = „Druck (Tausch)"; kein „Knopf"/„Drehknopf"/links-rechts mehr, überall „Encoder-Ring"
> (User: es gibt NUR oberen+unteren Doppelencoder, je außen+innen; keine Richtung links/rechts — das sind Drehrichtungen).
> (b) **„Bind"-Spalte der Geräteübersicht zählt jetzt Controller-Eingangscodes** (`gui_mapper.output_input_codes` +
> `DeviceRow.inputs` = bindings + Encoder/Swap/Selektor/Dimmer-Codes; dev_tree zeigt `.inputs`) — Radio/Multi lesen sich
> nicht mehr als „0 Bind, 1 Out" (User: Encoder/Swap/Mode-Selektor SIND Inputs). (c) **„Variablen in die Liste holen" grün**
> (neuer `Success.TButton`-Style). (d) **🔦-Knopf umbenannt „🔦 LEDs/Display testen…"** (er ist der AUSGANGS-Test; im
> Encoder/Eingang-Kontext war „Testen…" missverständlich).
> **📌 GEKLÄRT:** Live-Werte in Labels = „nur Kür" (rein optisch) → Roadmap #3. **Zifferweise-Vars** s. o. **Per-Zell-
> Mapping gibt es NICHT** — Display-Inhalt kommt aus Bank-Vars (die SIND mappbar: active/standby/code_var/dig_var); der
> Test-Send IDENTIFIZIERT nur Zellen. Beliebige Konstante pro Zelle (DME-Bindestrich, Punkt-als-Pointer) = Roadmap #5.
> **▶ #2 ENCODER-CAPTURE — GEBAUT (uncommitted, 351 Tests grün, HW-TEST OFFEN):**
> (1) **Flanken-fangender Reader** `hidraw_reader.count_rising_edges` (rein, 4 Tests) + `edge_count_reader(path)→(read,close)`:
> vergleicht JEDE aufeinanderfolgende Report-Frame und zählt steigende Flanken je Bit — fängt so die transienten
> Encoder-Impulse, die `live_state_reader` (Zustand) verschluckt; Mehrfach-Drehen macht das gewollte Bit zum klaren
> Gewinner (dedupliziert Bounce). (2) **Geführte Capture-UI** `_open_encoder_capture` (gui.py, in `_open_output_editor`):
> 5 Schritte (außen im/gegen UZS · innen im/gegen UZS · Druck), je „Weiter"/„Überspringen", live „erkannt: Code N (M Flanken)",
> **Invert-Checkbox außen/innen** (tauscht CW/CCW beim Speichern), schreibt alle 5 Codes in EINEM validierten Save.
> (3) **Konsolidiert:** die 5 Codefelder sind im Unit-Editor durch EINEN **„Doppelencoder"-Block** ersetzt (Zusammenfassung
> außen/innen/Druck + „🎚 Anlernen…"), `gui_mapper.ENCODER_FIELDS`. **🔴 HW-TEST NÖTIG:** GUI→Radio-Panel→Unit-Editor→
> „🎚 Anlernen…"→je Richtung drehen→wird der richtige Code erkannt? (Reader liest parallel zum Mapper, hidraw fanned out.)
> **✅ VERALLGEMEINERT:** `_capture_spec(field_names)` treibt die Capture generisch — **Radio-Doppelencoder** (5 Codes, 2
> Invert-Ringe) UND **Multi-Trimmrad** (dimmer cw/ccw, 2 Schritte + 1 Invert). Der Dimmer-Editor zeigt jetzt einen
> **„Trimmrad"-Block** (cw/ccw konsolidiert + „🎚 Anlernen…"). ⚠️ Trimmrad = dimmer-Block (optional) → falls im Profil noch
> kein `dimmer`, erst anlegen. **Multi-Value-Encoder** (ENCODER_CW/CCW=5/6) ist HARTVERDRAHTET (kein Modellfeld) → nicht
> capturebar; nur relevant, falls man das je konfigurierbar machen will (dann Modell-Änderung). HW-Test weiter offen. **⚠️ TECHNISCHER
> BLOCKER:** `hidraw_reader.live_state_reader` ist ZUSTANDS-basiert (letzter Wert je Bit) → eine Encoder-Rastung ist ein
> transienter ~8 ms-Impuls (Bit 1→0), der beim 80 ms-Tick verschluckt wird (Schalter=stabiler Zustand=ok, Encoder=Impuls=verloren).
> Braucht einen **flanken-fangenden Capture-Reader** (`iter_bit_changes`-Stil, akkumuliert geänderte Bits) — NICHT mit dem
> jetzigen 🪄-Reader machbar. `_open_code_capture` aus `_learn_code` extrahieren + Sequenz-UI + Invert-Toggle. HW-Test nötig.
> **▶ NACHBAU-CLEANUP `panel_layout._radio_panel` (User):** (a) das verwirrende **3. „Encoder-/Swap-Codes"-Element**
> (oben Mitte, `panel_layout.py` ~Z.480) ist nur eine SAMMEL-Zeile der 5 Codes — physisch gibt es nur 2 Doppelencoder →
> klarer machen/auflösen; (b) **links eine Spalte mit dem gewählten Mode** am Selektor (NICHT im Symbol-Display), Display
> nur „Act"/„Stby"; (c) **Selektor-Code je Zeile im Tooltip**.
> ---
> Stand davor: **2026-07-19 (spät) — RADIO-NACHBAU faithful + scrollbar + Gruppen. GEPUSHT bis `886a896`.**
> **✅ RADIO-LAYOUT FERTIG:** `_radio_panel`-Handlayout, pro Selektor-Einheit Gruppe (HEADER) + Encoder-/Swap-CODES;
> **pro Mode-Zeile: 2 Displays (act/stby) + Punkt links | 2 Encoder + Swap rechts** (Anzeige/Bedienung getrennt),
> je Element → Bank-/Unit-Editor (`out:i:units/u[/banks/b]`). **SCROLLBAR** (Canvas `scrollregion`, Content y>1,
> Scrollbar+Mausrad). **HEADER-Element** (Titel+Trennlinie) → **Gruppen-Überschriften + optische Trenner in ALLEN
> Panels** (Switch: Schalter/Magnetos/Fahrwerk; Multi/generisch: Bedienelemente/Anzeigen; Radio: Selektor upper/
> lower) → klar was Display vs. Knopf ist. Encoder als Drehknopf, Segment=LCD, Button=Pille. 338 Tests grün.
> **▶ NÄCHSTER BATCH — EDITOR/MAPPING-FUNKTIONEN (User mehrfach angefragt):**
> **(1) LERNFUNKTION (🪄) auch für OUTPUTS** (nicht nur die Binding-Source): im Output-Editor Codes/Vars per Gerät
> aufnehmen (Vorlage `gui.py._learn_code` ~Z.2196). **(2) SEGMENTE EINZELN setzbar „wie bei DME, ordentlich über
> die GUI"** — active/standby/dot je Bank direkt (evtl. Output-Editor feiner adressierbar: bank-Skalarfelder als
> eigene Gruppen). **(3) KNOPF-BELEUCHTUNG mappbar für ALLE Multi-Knöpfe** (bool_leds je Knopf + ap_master +
> mode_var; NICHT als Sammel-Kachel, sondern pro Knopf). **(4) GLOW-AUS-SIM:** Output-Elemente (LED/Segment/Button-
> Light) live vom `_ValueMonitor`-Wert einfärben/beschriften (Inputs glimmen schon von der Hardware). **(5) Hat-
> Capture-UI** (Modell/Engine stehen). Modelle: MultiPanelOutput(ap_master/mode_var/bool_leds/selector),
> RadioPanelOutput(units[].banks[] active/standby/…). Output-Editor: `_open_output_editor`/`group_fields` (gui_mapper).
> ---
> Stand davor: **2026-07-19 (spät) — Nachbau: Zonen-Trennung + Radio-Controls + saubere Labels.**
> **🆕 GANZ NEU:** **Knöpfe/Anzeigen GETRENNT** (`_device_layout`: Controls-Zone oben, Displays-Zone unten,
> `_lay_tiles`/`_output_items`→(controls,displays)); **Radio-Controls** pro Einheit = 1 ENCODER + 1 Swap-BUTTON
> (`_draw_encoder`); **saubere Display-Labels** (COM1/NAV1/ADF/DME/XPDR bzw. ALT/HDG — kein „Bank"/Kleinschreibung/
> SimVar; Anzeige-Var+Setz-Event im Hover). 337 Tests grün.
> **▶ NÄCHSTER FOKUS-SCHRITT — FAITHFUL RADIO-LAYOUT (User sehr detailliert, eigene Session empfohlen):**
> eigenes `_radio_panel`-Hand-Layout statt Auto-Grid. Pro **Mode-Zeile je Selektor**: **2 Displays (active/standby)**
> + **2 Encoder (außen/innen)** + **1 Swap-Button**. **Verschiebbarer PUNKT** (Dezimalpunkt) je Display — springt bei
> **ADF & XPDR** über den Swap; muss **direkt einstellbar** sein (eigenes DOT-Element, mappbar). **2 Selektoren
> (upper/lower)** getrennt mappbar (aktuell identisch). **Zeilenweise logische Gruppen, untereinander, SCROLLBAR**
> (gui.py: Canvas `scrollregion`+Scrollbar+Mausrad; `_render_panel_canvas` auf Content-Höhe statt Viewport
> normalisieren). Modell: **RadioPanelOutput.units[].banks[]** (active/standby-Vars, dot?), `outer_cw/ccw/inner_cw/
> ccw/swap` je Unit. Editor adressiert `out:i:units/u` + `.../banks/b`. **DANACH:** Glow-aus-Sim (Outputs live vom
> Sim), Hat-Capture-UI. HID-Maps in docs/memory/{multi,radio}-panel-hid.md.
> ---
> Stand davor: **2026-07-19 (spät) — Nachbau: Stapelbalken + OUTPUTS als getippte Elemente.**
> **🆕 SEITHER:** Magneto/GEAR/Flaps als EINZELN mappbare **Stapelbalken** (`_stacked_bars`, klare Binding-Namen als
> Label, leuchten grün beim Drücken am Gerät via live_key — headless verifiziert). **OUTPUTS = getippte Elemente wie
> Inputs** (`_classify_output`+`_output_items`, Typen LED/SEGMENT/BUTTON_LIGHT/DOT, je `ref=out:i:<pfad>` → Klick
> öffnet das eigene Output-Feld). **Radio-Panel-Nachbau existiert jetzt** (14 Display-Segmente, war vorher LEER);
> **Multi** = Knöpfe + 5 Selektor-Segmente. **Nur PHYSISCHES** wird gezeigt (Konfig-Container bool_leds/alt_sources/
> dimmer NICHT als Kachel — Var-Mapping nur im Editor). Segmente als schwarz-bernstein **LCD-Screen** (klar ≠ Knopf).
> „AP mode X"→„X". 336 Tests grün, ruff clean, GUI-Smoke ok.
> **🔴 OFFEN — NÄCHSTES:** **(1) GLOW-AUS-SIM** (User gefragt!): Output-Elemente (LED/Segment) leuchten/zeigen noch
> NICHT den gelesenen Sim-Wert — jedes Output-Element seine Var über `_ValueMonitor` abonnieren (wie Gauges) +
> Kachel live einfärben/beschriften (Inputs glimmen schon von der Hardware). **(2) Hat-Capture-UI** (Modell/Engine
> stehen). **(3) evtl. faithful physische Hand-Layouts** für multi/radio (aktuell Auto-Grid). HID-Maps in
> docs/memory/multi-panel-hid.md + radio-panel-hid.md. Panel-Output-Modelle: MultiPanelOutput/RadioPanelOutput.
> ---
> **▶ ODER (User-Auftrag: frische Session) — HAT-CAPTURE-UI:** pro Hat-Richtung
> Code+Wert per 🪄 aufnehmen, damit ein Hat für JEDEN Yoke ohne Code-Wissen anlegbar ist. **Modell+Engine stehen
> schon** (Commit `cd2b700`: `models.HatDirection` mit optional `code`/`value`; `HatMap.entries()/codes()`; Engine
> matcht Hat auf HAT+BUTTON-Events über (code,value)). **Nur der Editor fehlt.** Zu ändern:
> `gui_mapper.py` `_blank_hat_fields`/`_hat_fields`/`_form_hat` (~Z.422-465) + `gui.py` Hat-Slots (~Z.2080-2115).
> **⚠️ STOLPERFALLE:** das bestehende Formfeld `hat_{d}_value` = **Action**-Sendewert (EventAction.value), NICHT der
> Trigger-Wert! Für die Capture braucht es NEUE Felder `hat_{d}_code` + `hat_{d}_trigval`, und `_form_hat` muss dann
> die **nested** Form `{code, value, action:{…}}` erzeugen (nur wenn Code gesetzt; sonst flache Form = Konvention,
> bleibt rückwärtskompatibel). **🪄 je Richtung:** `gui.py._learn_code` (~Z.2196) als Vorlage — es öffnet den
> Live-Reader (evdev/hidraw) und nimmt die stärkste Änderung; für eine Hat-Richtung Code UND Wert (±1 bzw. 1)
> erfassen und in die neuen Felder schreiben. Danach: gui_mapper-Round-Trip-Test + Konstruktions-Smoke.
> **🆕 DIESE SESSION (mehrere Commits, 334 Tests grün ohne die 2 bekannten test_read_command-ENV-Fehler):**
> (1) **Nachbau-Typ-Formen** — jedes Control eigene Form (Achse=Slider m. Griff, Knopf=Pille, Schalter=vertikaler
> Kippschalter, Hat=Raute, LED=Scheibe, Selektor/Hebel=Block), Live: Knob springt/grünt, Achsen-Griff gleitet;
> (2) **leere Platzhalter anklickbar** → Klick auf ungemappten Schalter/Knopf öffnet Editor mit vorbelegter Quelle
> (kind+code+Name); (3) **nur EIN Label je Kachel** (Doppelbelegung raus, Rest im Hover/Editor); (4) **Yoke-Hat →
> Cockpit-Blick** (PAN_UP/DOWN/LEFT/RIGHT) im piper_arrow; (5) **HAT-MODELL GENERALISIERT** (User-Entscheid:
> „Hat = Knopf mit gelernten Codes"): neues `models.HatDirection` (pro Richtung optional `code`+`value`, sonst
> ABS_HAT-Konvention um `source.code`), `HatMap.entries()/codes()`; Engine matcht Hat auf HAT **und** BUTTON-Events
> (Button-Hats!), Auflösung über (code,value); **rückwärtskompatibel** (alte flache `up:{type:event,…}`-Form lädt
> via before-Validator). 2 neue Engine-Tests. `_schema.md` erweitert. GUI-Editor läuft weiter über die Konvention.
> **✅ (b) FLAPS-WIPPE ERLEDIGT:** `panel_layout` fasst „X up"/„X down"-Momentpaare (per Namens-Richtungswort,
> DE+EN) zu EINEM `ROCKER`-Element zusammen ((on)-off-(on): Kapsel mit oberer+unterer Lampe, beide Codes im
> Live-Overlay); `_pair_rockers`/`_direction_of` rein+getestet, `_draw_rocker` gerendert. Greift generisch (Flaps
> im multi_panel etc.). **🔴 OFFEN / NÄCHSTE SCHRITTE:** (a) **Hat-Capture-UI** — pro Richtung Code+Wert per 🪄
> aufnehmen (Modell/Engine stehen schon; nur noch Editor `_hat_fields`/`_form_hat`/gui.py-Hat-Slots + Lern-Knopf;
> ACHTUNG Trigger-Wert vs. Action-Wert nicht verwechseln → neues Formfeld, nested `{code,value,action}`);
> (c) **Multi-Panel-Nachbau inkl. Output** (Werte/Display zuordnen); (d) **Radio-Panel-Nachbau** — (c/d am besten
> zusammen = Hand-Layouts für multi_panel + radio_panel mit Output-Elementen). ⚠️ **Ganzer Nachbau + Gauges
> visuell weiterhin UNGEPRÜFT.**
> ---
> Stand davor: **2026-07-19 (später) — GAUGES-REWORK: lua-treue Skalierung + Formen + Regler-Parametrierung.**
> **🆕 GAUGES (uncommitted, 334 Tests grün, ruff clean):** **FIX der ignorierten Skalierung** — Fuel-Flow-Zeiger
> ist **potenz-gestaucht** (lua `h=1.8`: `Alpha=(ZWEI_PI/Δ·v)^1.8+100`), Preset hatte `h=1` (linear). Modell-
> Formel `omega+sweep·frac^h` reproduziert die Lua **exakt** (Test: 165·(v/25)^1.8+100; bei 12.5 GPH 147° statt
> linear 182°). MAP selbst ist linear+korrekt. **FORMEN:** `GaugeSpec.aspect` (1=rund, 6=Cluster) + `NeedleSpec.cx/cy`
> (eigene Zentren) → neues Preset **„Fuel L/R + Druck (Cluster)"** (1536×256 = 6:1, 3 Teil-Skalen bei cx=1/6,1/2,5/6,
> aus `arrow-fuel-lr-fuelpressure`); Rendering `_g_paint` formbewusst (rund=Kreis, breit=Rechteck+Teil-Ringe).
> **PARAMETRIERUNG 100% in der GUI:** `_g_config` neu = **Regler** (ttk.Scale) für Winkelbereich(sweep)/
> Startwinkel(omega)/Skalen-Verzerrung(h)/Radius + Entries min/max/Haupt/Neben/Faktor/Mitte X-Y/Form, **Live-
> Vorschau-Canvas** (Nadel bei 65 %, redraw bei jeder Änderung), Abbrechen restauriert aus Snapshot. Nadel jetzt
> mit Gegen-Stummel. **✅ VALIDIERT:** 16 gauge_model-Tests (inkl. FF-Potenzskala/Cluster/aspect) · GUI-Konstruktions-
> Smoke · isolierte tkinter-Draw/Widget-API (arc/line/Scale/Notebook/trace). **🔴 VISUELL UNGEPRÜFT** (Pixel-Optik +
> Regler-Interaktion + Vorschau brauchen gemapptes Fenster). **⏳ evtl. später:** Cluster-Layout (breite Zellen statt
> Letterbox in quadratischer Zelle), Gauges in den Geräte-Nachbau einbetten (falls „Form für Nachbau" so gemeint war).
> ---
> Stand davor: **2026-07-19 — Branch `feat/mapper-panel-nachbau`: NACHBAU jetzt für ALLE Geräte + Default-Ansicht (uncommitted).**
> **🆕 PANEL-NACHBAU (uncommitted, 330 Tests grün, ruff clean):** reines Modul `panel_layout.py`
> (`panel_layout(profile, device_id)` → positionierte `PanelElement`s in normierten 0..1-Koords, tkinter-frei,
> 13 Tests). **Hand-Layout Switch-Panel** (13 Kippschalter codes 0..12 mit HW-Silkscreen BAT/ALT/…, Magneto-
> Selektor 13-17, Fahrwerkshebel 18/19, 3 Gear-LEDs aus gear_leds-Output). **🆕 GENERISCHES Geräte-Layout**
> (`_device_layout`) für Yoke/TQ6/Trim/Pedale/Multi/Radio: **Achsen = gestapelte Live-Balken oben** (mit Wert-
> Anzeige, Skala aus source.raw_min/max bzw. Live-Range), **Buttons/Schalter/Hats = Kachel-Raster unten** —
> konsistente Optik über ALLE Gerätetypen (Wunsch des Users, „weg von der Tabelle"). **GUI (`gui.py` Mapper):**
> **NACHBAU = STANDARDANSICHT** (`mstate["view"]="panel"`, `_apply_view()`), Header-Toggle „Tabelle"↔„Nachbau"
> NON-destruktiv (Tabelle bleibt einen Klick entfernt). `_render_panel_canvas` + `_draw_axis` zeichnen; Klick→
> `_open_row(el.ref)` (bestehender Editor); **Live-Overlay:** Schalter glühen grün, **Achsen-Balken füllen live**
> (`_live_tick`, `pcanvas["live"]` als onoff/axis-Dicts, aus demselben evdev/hidraw-State wie die Live-Spalte).
> **✅ VALIDIERT:** 13 Layout-Unit-Tests · voller GUI-Konstruktions-Smoke · Mapper-Reload+Toggle-Round-Trip · alle
> tkinter-Zeichen-API-Aufrufe isoliert geprüft (withdrawn, KEIN Fenster gepoppt). **🔴 VISUELL/HW UNGEPRÜFT:**
> Canvas-Pixel-Geometrie (Balkenfüllung/Kachelgröße) + Live brauchen gemapptes Fenster + Gerät → beim Start:
> GUI→Mapper→Gerät wählen (Yoke/Switch-Panel) → Achse bewegen/Schalter kippen: füllt der Balken / glüht es?
> **⏳ NÄCHSTE INKREMENTE:** LED-Glühen-aus-Sim (via `_ValueMonitor`, gear_leds/AP-Mode) + Display-Werte
> (Multi/Radio) = „Schritt 2"; Hats live (melden als 2 Achsen -1/0/+1, aktuell kein Overlay); Hand-Layouts auch
> für Multi/Radio. **Installer-Frage des Users: BEREITS INTEGRIERT** — Connection-Tab hat Prefix-Feld +
> Voraussetzungs-Checkliste (grün/rot, `env_check.py`) + Button „Setup Prefix" der `setup-prefix.sh`
> (Windows-Python + SimConnect) mit Live-Log-Fenster startet und danach neu prüft. Nichts zu bauen; ggf. UX-Feinschliff.
> ---
> Stand davor: **2026-07-18 (spät) — `feat/gauges` → `main` GEMERGT + GEPUSHT; neuer Branch `feat/mapper-panel-nachbau`.**
> **🟢 MERGE:** `feat/gauges` (61 Commits: Mapper/Gauges/V:-Runtime/Connection-Umbau/i18n) via `--no-ff` in `main`
> (`3159ef0`) und **nach origin gepusht**. `feat/gauges` bleibt als Branch stehen.
> **🆕 AKTUELLER BRANCH `feat/mapper-panel-nachbau`** (von main, Commit `d263322`, **gepusht**, 318 Tests, ruff clean):
> **Live-Spalte im Mapper hidraw-fähig** — `_live_open` wählt Reader nach Transport (hidraw fürs Panel wie der
> Zauberstab), `live_row_map` nimmt switch-Bindings auf (Key `("switch", byte·8+bit)` = `source.code`). → ● jetzt
> auch für real gekippte Panel-Schalter (vorher nur evdev). **🔴 NÄCHSTE SESSION ZUERST TESTEN:** GUI starten,
> Mapper-Tab, Switch-Panel wählen, Schalter kippen → leuchtet die „Live"-Spalte ●? (braucht angestecktes Panel).
> **🎯 GEPLANT (User-Entscheid: Hybrid, Nachbau NUR für die 3 Saitek-Panels, Rest = Karten):** Panel-Nachbau =
> Canvas-Schema je Panel (Schalter/LEDs/Display/Selektor an ~physischer Position), Element zeigt gemappte Var/Event
> + **Live** (Schalter-Highlight ✓, LED-Glühen aus Sim via `_ValueMonitor`, Display-Werte), Klick → bestehender
> Editor. Reine Fn `panel_layout(profile, device)` (testbar) + Canvas rendert. **Hand-Layout je Panel (nur 3,
> Positionen aus HID-Docs), Auto-Raster als Fallback.** **⏳ OFFENE ENTSCHEIDE (User):** (1) Umschalter
> „Tabelle ↔ Nachbau" statt Ersetzen? (2) v1-Live-Umfang: Schalter+LED, Display als Schritt 2? **Nächster Bau-
> Schritt:** `panel_layout` + Switch-Panel als erstes Nachbau-Beispiel. **⚠️ GUI weiterhin visuell UNGEPRÜFT**
> (ganzer Connection/Settings/i18n-Batch) — beim Start alles live sichten + Sprachumschaltung testen.
> ---
> Stand davor: **Connection-Umbau + Settings-Tab + i18n-SPRACHPAKET VOLLSTÄNDIG (DE/EN/ES/FR).** 317 Tests grün.
> **🆕 GUI-Umbau `84915c0`** (visuell UNGEPRÜFT/headless, aber Konstruktions-Smoke DE/EN/ES/FR ok + Prefix-Checks
> gegen echtes Prefix verifiziert): Connection-Tab neu nach Sinngruppen — Sub-Notebook „Steuerung & Status" /
> „Bridge-Protokoll" (Log-Terminal ausgelagert), Gruppe „Prozesse" (kompakte Knöpfe, neue Styles Small*),
> Gruppe „Umgebung & Voraussetzungen": **Prefix-Pfad-Feld** (persistiert `gui-settings.json:prefix_path`,
> Durchsuchen/Speichern, beim Start geladen, als Env `STEAM_COMPAT_DATA_PATH` an run-bridge.sh injiziert via
> neuem `ProcessController.env`) + **Voraussetzungs-Checkliste ✓/✗** (Prefix, drive_c, pythonw/python.exe,
> SimConnect.dll, Proton, run-bridge.sh, bridge.py) mit Initial-Check + „Erneut prüfen" + „Prefix einrichten…".
> **Settings-Tab neu**: Sprach-Dropdown DE/EN/ES/FR (sofort gespeichert `:language`, Anwenden=os.execv-Neustart).
> **🆕 i18n-SPRACHPAKET (`567284a`+`18aa321`):** reines `i18n.py` (`tr()`, Fallback DE→Key) + `env_check.py`.
> **GANZ gui.py gewickelt+übersetzt** (DE/EN/ES/FR): alle text=/label=, _attach_tooltip, messagebox über alle Tabs
> (Variablen/Mapper/Gauges/Profile, Binding-/Output-Editor, Kachel-Panel, Var-Picker, Statusleiste). Schlüssel =
> DE-Quelltext (gettext-Stil). Auto-Wrap via Scratch-Skript `wrap_tr.py` (String-Run bleibt in tr() → Key=konkat.
> Wert). Bewusst NICHT übersetzt (in allen Sprachen gleich): Symbole (…/✓/🪄/min/max/dz/expo/Code/SimVar/RPN) +
> Roh-Kommando-Tooltips (bash …/killpg …/filedialog …). ruff: per-file-ignore E501 für i18n.py.
> **✅ i18n VOLLSTÄNDIG (`ceab706`+`1d0feeb`):** auch `gui_mapper.py` — Control-Labels (Achse/Taste/Hat/Schalter),
> Gerätestatus, describe_*-Ausgaben, FIELD_LABEL, alle ~55 OUTPUT_FIELD_HELP-Felder+Hilfen, _ENTRY_WORD/_SOLO/
> _GROUP_ROLE + 19 Validierungs-Fehler. `tr()` an Use-Sites (Dicts bleiben DE-Quelle=Key). ~145 Einträge; Tests
> grün via Default-DE-Fallback. **Scratch-Generatoren** `wrap_tr.py`/`gen_mapper_i18n.py` (Übersetzungen im Skript,
> Keys aus Import → exakt). **⏳ i18n-Rest bewusst offen:** Anwenden per **GUI-Neustart** (os.execv), kein Live-
> Retranslation der schon gebauten Widgets. **🔴 GUI weiterhin visuell UNGEPRÜFT** (headless) → beim nächsten
> Start Connection-Umbau + Sprachumschaltung live sichten.
> **✅ V: e2e bewiesen** (Seeding 0.0 · Cowl-Switch **Code 6** → 0↔1 · Hub-Runde) via Direkt-Client an
> Bridge :7842. **GUI-Batch committet** (Details Session unten): Variablen-Tab-Umbau (V:-Übersichtstabelle,
> Buttons ÜBER die Tabelle, V:-Editor aus Profile RAUS), Panel-Picker + Toggle-Button, Bridge-Log
> eingebettet, **🪄 Zauberstab hidraw-fähig**, pythonw-Fix. ⚠️ **GUI visuell UNGEPRÜFT** (headless).
> **🔴 WIEDEREINSTIEG:** (1) **GUI + Mapper + Bridge NEU STARTEN** (neuer Code: pythonw, GUI-Umbau) →
> alles live sichten; (2) ✅ **tq6-WIP ERLEDIGT** (`f64d979`): 6 Hebel T1/T2/P1/P2/M1/M2 (Motor 1&2),
> Inversion via `raw_min>raw_max`, „Mixture 1 (Kopie)"→„Mixture 2", Code-Reihenfolge + Kommentare geputzt,
> valide+Tests grün — **NUR noch in-sim fliegen/prüfen** (bes. ob Motor-2-Events T2/P2/M2 am Arrow gewollt
> sind, s. Frage unten); (3) pythonw-Fenster-Fix verifizieren (Wine-Konsole weg?); (4) danach
> Geräte-Explorer / Kette → main. ⚠️ **OFFENE FRAGE:** Arrow ist einmotorig — T2/P2/M2 auf Achse 1/3/5
> sind am Single-Engine no-ops; falls unerwünscht, die 3 Motor-2-Einträge wieder raus (Commit reverten).
> Frühere Zeile: 2026-07-16/17 Doppel-Mega (Stufe C, Split, V:-Runtime-Code, Gauges, HAT, ⚑), 2026-07-15/13.

## 🆕 SESSION 2026-07-17 (Abend) — V: e2e IN-SIM + GUI-Batch + hidraw-Zauberstab (Commits `3507407`,`ba8c332`)

**✅ V:-RUNTIME e2e IN-SIM VERIFIZIERT** (war laut STATUS „e2e ungetestet"). MSFS lief, Bridge mit V:-Hub.
Bewiesen via Direkt-Socket-Client an `127.0.0.1:7842` (Scratchpad, newline-JSON):
- **Hub-Runde:** set `V:TEST_FLAG`=42/7 → subscribe-Push + read_now liefern zurück (sim-unabhängig).
- **Seeding:** Mapper-Neustart mit temp `local_vars:[TEST_FLAG init 0]` → Hub-Wert 0.0 (überschrieb die
  7.0 aus dem Vortest) = `seed_local_vars` läuft beim Mapper-Start.
- **Hardware→V::** temp Binding `switch code 6 → simvar V:TEST_FLAG` (stateful) → User kippte **Cowl-Schalter**
  mehrfach → Watcher sah 0↔1 sauber. **Cowl = Switch-Panel Code 6** (Saitek „COWL CLOSE"; freie switch_panel-
  Codes: 6=Cowl, 9=Nav). Reihenfolge: 0 BAT,1 ALT,2 AVIONICS,3 FUEL PUMP,4 DE-ICE,5 PITOT,**6 COWL**,
  7 (Panel-Licht→AP master),8 BEACON,10 STROBE,11 TAXI,12 LANDING,13-17 Magneto,18/19 Gear.
- **Test-Gerüst wieder ENTFERNT** (profile_writer, chirurgisch — NICHT `git checkout`, das hätte die tq6-
  Arbeit gekillt). `piper_arrow.yaml` = HEAD + nur die tq6-Arbeit (uncommitted).
- **⚠️ Merker:** Bridge-Port 7842 geht erst NACH SimConnect auf (`connect_sim()` vor `bind()`) → auch reiner
  V:-Test braucht laufendes MSFS. Shell = **zsh** → `/dev/tcp` geht NICHT (Falsch-„zu"); Port mit `ss`/python.

**🖥️ GROSSER GUI-BATCH (Live-Feedback, 2 Commits, 302 Tests grün, ruff clean; visuell UNGEPRÜFT/headless):**
1. **Statistik-Tab → „Variablen".** Var-Picker zeigt jetzt **V:-Vars** (Filter „V: lokal" in
   `_open_var_picker`; `_statistik_catalog` mischt profileigene V: frisch dazu) — greift auch im Mapper-Picker.
2. **Variablen-Tab-Umbau:** Buttons **ÜBER** der Tabelle (row 1): „Variablen in die Liste holen" +
   „Variablen aus Liste entfernen" (rot). **V:-Übersicht = eigene Tabelle (row 3)** (Anlegen/Entfernen) —
   **aus dem Profile-Tab hierher migriert, Profile-V:-Editor ENTFERNT.** (Load deferred via `win.after`, da
   `load_profile` erst nach dem Tab-Aufbau importiert wird.) „+ V:-Variable"-Dialog wieder raus.
3. **Kachel-Panel:** eigener **„+ Variable"-Picker** neben „Raster" (`_PanelWindow.catalog_provider`);
   **„→ Ins Panel" entfernt.** **Panel-Toggle:** Text „Panel öffnen"↔„Panel schließen" + **invertierte Farben**
   (neuer Style `AccentInv`); `_toggle_panel` zustandsbasiert (`panel_btn`-Holder für Text/Style).
4. **Connection-Tab: Bridge-Log live eingebettet** (tailt `bridge/bridge.log`, `win.after`-Loop, autoscroll,
   gedeckelt) → kein loses Bridge-Terminal nötig. GUI-Mapper-Start ist fensterlos (DEVNULL).
5. **🪄 Zauberstab HIDRAW-FÄHIG** (war evdev-only → „Panels gehen nicht"): neu `hidraw_reader.live_state_reader`
   (nicht-blockierend, `{("switch",bit):value}`); `_learn_code` wählt Reader nach `ddef.transport`. Panel
   sendet **KEINEN On-Open-Snapshot** (empirisch) → **Lazy-Baseline** aus 1. Frame → UX: **Schalter HIN UND
   ZURÜCK** (1. Flip=Baseline, 2.=Code). Kind „switch"=„Schalter". `code=byte·8+bit`.
6. **pythonw.exe** in `run-bridge.sh` (statt python.exe) → Wine spawnt **kein Konsolenfenster** mehr; Log
   unberührt (FileHandler). **⚠️ UNGETESTET** — User prüft beim nächsten Bridge-Start. (pythonw.exe liegt im
   pybridge-Prefix.)
7. Kleinkram: „+ Panel" → **„+ Saitek-Panel"**; Gauges-Tab nach rechts
   (**Connection·Mapper·Variablen·Gauges·Profile**); Inline-✕ (Sequence/Bedingung) rot.

**🔴 NÄCHSTES:** GUI+Mapper+Bridge NEU STARTEN & alles live sichten; tq6-WIP im piper_arrow aufräumen+
committen; pythonw-Fenster prüfen; dann Geräte-Explorer (Wand-hidraw ist der halbe Weg) / Kette → main.

## 🆕 SESSION 2026-07-16 (fortges.) — GAUGES-TAB GEBAUT (Branch `feat/gauges`)
**Branch `feat/gauges`** (von `feat/mapper-tab` abgezweigt), Commit `c580928`. **284 Tests grün,
ruff clean, Konstruktions-Smoke ok. Visuell UNGEPRÜFT** (User konnte nicht testen).
- **`gauge_model.py`** (rein, 11 Tests): Rundinstrument-Mathematik aus den Air-Manager-Luas —
  `winkel(v) = omega + sweep·((v−v_min)/Δ)^h` (Lua-Form normalisiert: sweep = IMMER der volle
  Winkel), Ticks (major/minor), Arcs, `polar()` (0°=Norden, im UZS), Dict-Round-Trip für die
  Persistenz. **Presets aus den Original-Luas vermessen**: „MAP + Fuel Flow" (ZWEI Zeiger — äußere
  MAP-Skala 10–50/180°/−90°, innere FF-Skala 0–25/165°/+100°, radius 0.58), RPM (0–3500/290°/215°,
  grün 500–2650), Airspeed (20–190/306°, grün/gelb/blau-Arcs), EGT (1200–1700/100°/−50°),
  Fuel L/R (0–38.5/100°/−50°), „Eigenes…" (leer).
- **GUI-Tab „Gauges"** (Position 2, nach Statistik): Canvas-Panel, Gauges im automatischen Raster
  (Zellengröße maximiert). **User-Flow wie gewünscht:** „+ Gauge" → Menü zeigt **📚 Bibliothek**
  (bereits gemappte Gauges, per Name wieder aufrufbar) + Vorlagen → **ZUERST Mapping-Dialog**
  (je Zeiger: Variable über den Var-Picker (readonly-Feld), Faktor, min/max) → „Übernehmen" legt
  das Gauge aufs Panel UND speichert es in die Bibliothek (`gauge_library` in gui-settings.json;
  Panel-Inhalt = `gauges_panel`). Klick wählt (blauer Ring), Doppelklick remappt, „✕ Entfernen"
  nimmt nur vom Panel (Bibliothek bleibt; Löschen aus Bibliothek im Dialog). Zeiger rendern live
  aus dem geteilten `_ValueMonitor` (Subscription nur bei sichtbarem Tab via `gauge_hook` in
  `_resubscribe`; Zeiger-Update 150 ms, `canvas.coords`).
- **Offen:** visuelle Sichtung (Skalen-Optik, Schriftgrößen, Dark-Face); Mehr-Zeiger-Skalen-
  Beschriftung könnte bei kleinen Zellen gedrängt sein; evtl. loslösbares Gauge-Fenster (wie
  Kachel-Panel); Arcs/sweep im Dialog editierbar machen (aktuell nur Var/Faktor/min/max);
  Presets für weitere Vars. Design-Referenz: `docs/gauges-design.md`.

**➕ NACHTRAG 5 (Session-Ende, Commit `1f3dd59`, GEPUSHT): „+ Panel"-Fixes nach Live-Test.**
User hat live getestet: „+ Panel" erzeugte Blöcke auch auf dem Yoke (2 Test-multi_panel auf yoke
entstanden!), saß links statt rechts, Löschen ging nicht aus der Tabelle. Fixes: (a) Sperre —
nur hidraw-Geräte, sonst Meldung; (b) Knopf in die rechte Knopfzeile verschoben; Dropdown sagt
„Switch Panel"; (c) **„Entfernen" wirkt auf jede markierte Zeile** (Binding / ganzer Panel-Block
mit Rückfrage / Listeneintrag / optionaler Block) ohne Fenster. `piper_arrow.yaml`: Yoke-Testblöcke
entfernt, der **einmalige ruamel-Reflow vom ersten GUI-Speichern ist jetzt committet** (bewiesen:
HEAD~1↔HEAD semantisch identisch — Fliegen sicher; künftige GUI-Saves = saubere Diffs).

**➕ NACHTRAG 4 (gleiche Session, Commits `32aba6c`+`2ee8621`, 302 Tests, GEPUSHT): V:-RUNTIME FERTIG.**
- **Bridge-V:-Hub** (geparktes Design umgesetzt): `bridge.py` Modul-Level `_VIRTUAL_VARS`+Lock;
  `set_simvar`/`read_subscribed`/`read_var` erkennen `V:` ZUERST (kein Sim, kein DLL-Lock, Werte
  überleben Sim-Reconnects); Subscribe/Poll/read_now servieren V: automatisch an alle Clients.
  **Offline-Stub-Smoke 5/5** (SimConnect-Stub + `object.__new__`; Scratchpad `vhub_smoke.py`).
- **Seeding**: `runtime.seed_local_vars(profile)` → SetSimVar `V:<name>`=initial beim Mapper-Start,
  VOR Conditions/Outputs (Bedingung auf V: sieht den Startwert statt unbekannt=blockiert).
  Mapper-Neustart re-seeded (Persist = LocalVar.persist-Follow-up).
- **Wires**: GUI `_wire_name` + `gauge_model.wire_name` können V: → Statistik, Kachel-Panel,
  Gauges und ⚑-Bedingungen beobachten V: live.
- **V:-Editor-UI im Profile-Tab** (Lücke geschlossen): Labelframe „V: — eigene lokale Variablen"
  mit Liste + Anlegen (Name/Startwert/Beschreibung) + Entfernen via `profile_writer.set_local_vars`.
- Doku: simvars-reference §1 hat jetzt die V:-Zeile. **⚠️ In-sim/e2e ungetestet** (Bridge neu
  starten → V: anlegen → per Binding setzen → in Statistik/Bedingung sehen).
- **Alle 3 Branches GEPUSHT** (origin: gui-var-monitor, mapper-tab, gauges).

**➕ NACHTRAG 3 (gleiche Session, Commits `211a422`+`0608e7c`, 299 Tests): BEDINGUNGEN + LED-Fixes.**
- **`when:`-Bedingungen an Bindings** (lang geplant, jetzt KOMPLETT: Modell+Engine+Runtime+UI):
  `models.Condition {var, op, value}`, Liste = UND; Engine bekommt Value-Provider injiziert,
  unbekannter Wert = Bedingung NICHT erfüllt (fail-closed, ==/!= mit isclose); Runtime
  `ConditionWatcher` abonniert alle when:-Vars (Tap auf OutputManager-State-Stream via neuem
  `state_listener`, ohne Outputs eigener Reader-Thread); Binding-Editor hat eine **optisch
  abgesetzte „⚑ Bedingung"-Labelframe-Sektion** (Zeilen: Wählen…/readonly Var · Operator · Wert ·
  ✕, „+ Bedingung"); Tabelle zeigt ⚑n. V:-Vars stecken schon im Format (greifen sobald der
  Bridge-Hub existiert). Doku `_schema.md`. **⚠️ In-sim ungetestet** (Subscribe+Gating live prüfen).
- **Gear-LEDs = Solo-Zeilen**: LED Bugrad/links/rechts je eigene Baum-Zeile mit eigenem
  Mini-Fenster (User: drei Zeilen → immer dasselbe Sammel-Fenster war verwirrend); „Allgemein"
  behält down_at/power. **Dimmer-Rolle = „Eingabe (Drehrad)"** (User-Korrektur), Ziele =
  „Anzeige (Licht)". Hat-Binding-Crash im Editor gefixt (action None).
- **NÄCHSTES FEATURE (Task, noch nicht gebaut): Geräte-Explorer** — je Gerät alle Codes live
  auslesen, bei Panels Test-Werte je Code/Segment senden (LED/Segment identifizieren,
  wie tools/panel-scan out_*), Codes umlabeln (Label-Store: devices.yaml vs gui-settings offen).

**➕ NACHTRAG 2 (gleiche Session, Commits `e6d3ca7`+`359628e`, 293 Tests):**
- **Tab-Reihenfolge:** Connection · Mapper · Gauges · Statistik · Profile (User-Wunsch).
- **🪄 Code-Anlernen AKTIV** (war Stub): lauscht via `live_state_reader` am Gerät, erkennt
  Taster/Achse/Hat + Code (Hat → Basis-Code normalisiert), Übernehmen füllt Quelle.
- **HAT-Support GEBAUT** (war halb kaputt: evdev meldete Hats als Achse, nur eine Richtung hätte
  je gefeuert): `models.HatMap` (up/down/left/right je eigene Aktion, `Binding.action` jetzt
  optional, hat XOR action validiert), `source.code` = X-Basis-Kanal (Y implizit +1),
  evdev_reader klassifiziert ABS_HAT* als HAT, Engine matcht beide Kanäle + feuert je
  Richtungs-Flanke. Editor: Quelle=Hat zeigt VIER ▲▼◀▶-Slots im selben Fenster.
  Schema-Doku in `profiles/_schema.md`.
- **Mapper-Tabelle = echter Struktur-Baum** (User: „Darstellungsbaum output → selektor-mode[x]"):
  Panel-Controller als Baum-Zeilen (kurze deutsche Labels „Position ALT", „Bank COM1 · freq",
  „Einheit upper"), **Eingabe/Anzeige-Rolle** in der Control-Spalte (User: LEDs=Anzeige,
  Drücken/Schalten=Eingabe — beim Radio-Panel am deutlichsten). Abschnitte: „Eingaben — Bindings"
  / „Panel-Controller".
- **Output-Kontextfenster = genau EINE Zeile** (User: Fenster mit nochmal Liste = verwirrend):
  Doppelklick auf Baum-Zeile → Formular NUR für diese Gruppe, konsistent zum Binding-Editor
  (deutsches Label · Feld · ⓘ, „Wählen…" an Var-Feldern, Übernehmen/Zurücksetzen/Schließen,
  Danger-Entfernen). Kein Fenster-Baum mehr.
- **„+ Panel"** unter der Geräteliste: ganzen Panel-Controller aus 3 validierten Block-Vorlagen
  anlegen (`profile_writer.add_output/remove_output`, leere Stubs aufgeräumt); Wurzel-Fenster
  kann den ganzen Block entfernen. (User-Einschätzung bestätigt: für die Saiteks selten nötig —
  hauptsächlich für neue Flugzeug-Profile; bewusst einfach gehalten.)

**➕ NACHTRAG (gleiche Session, Commit `faa91d6`, 286 Tests): Output-Fenster in GRUPPEN statt
Feld-Baum.** User-Feedback: der rohe Feld-Baum im Output-Editor „sagt nichts" — jetzt links eine
schlanke Gruppen-Navigation (Allgemein · Selektor-Positionen (je Eintrag ein Knoten) · LEDs ·
Dimmer · Radio-Einheiten/Bänke …), rechts ein Formular mit **deutschen Feldnamen + ⓘ-Erklärung
je Feld** (neues `gui_mapper.OUTPUT_FIELD_HELP`, ~50 Felder erklärt, YAML-Name steht in der
Hilfe). Übernehmen speichert alle geänderten Felder der Gruppe in EINEM validierten Schreibvorgang;
Listen/optionale Blöcke: „+ Eintrag/Anlegen", „✕ Entfernen"; LED-Zeilen mit ✓/✕ inline. Die
technischen Output-Detailzeilen im Mapper-Baum sind default **eingeklappt**. **Inputs (Binding-
Editor) bewusst unverändert** — User: „bei den Inputs schon gut". Reine Helfer
`output_groups`/`group_fields`/`output_field_help` getestet.

## 🆕 SESSION 2026-07-16 — Stufe C fertig · Achsen-Split · Editor-UX v2 · Live-Spalte · Gauges gesichert
**Branch `feat/mapper-tab`, 7 neue Commits `f2c10ec`…`cdc7d2f` (NICHT gepusht). 273 Tests grün,
ruff clean, Konstruktions-Smoke OK (Fenster withdrawn). ⚠️ ALLE neuen GUI-Teile visuell UNGEPRÜFT.**

1. **✈️ FLUG-VERIFIKATION (User will fliegen):** `piper_arrow.yaml` + Runtime-Pfad unverändert
   gegenüber dem in-sim-verifizierten Stand — Diff vs `main` in Runtime-Dateien ist exakt die am
   2026-07-11 verifizierte Arbeit (bridge-Streaming, ADF/KR-85, DME source_var, Achsen-Koaleszenz).
   Die GUI-Arbeit berührt den Mapper-Laufzeitpfad nicht. Profil-Kopien des Users
   (`piper_arrow_kopie/_sicherung`) behalten, aber `aircraft_match: []` → Auto-Auswahl lädt
   IMMER das Original. `msfs-bridge piper_arrow` bleibt sowieso explizit.
2. **Achsen-Split in EINEM Binding** (User-Wunsch statt Duplizieren-Workflow): `models.AxisSplit`
   (`split: {at, action, transform}` am Binding, nur axis), Engine teilt am Detent (jeder Teil
   normalisiert über die eigene Roh-Spanne), Editor zeigt bei „Achse am Detent teilen" einen klar
   abgetrennten zweiten Aktions-Bereich (eigenes Wählen…/Felder/Verarbeitung/Ausgang), Learn-Fenster
   hat „→ als Detent". Doku `profiles/_schema.md`.
3. **Editor-UX v2 (Live-Feedback des Users):** (a) **Doppelklick** auf Tabellenzeile öffnet das
   Editor-Fenster (Einfachklick markiert nur; ✏-Spalte + „Bearbeiten…"-Knopf entfernt);
   (b) Aktions-Zeile **eingedampft auf EINEN „Wählen…"-Knopf** — kein Typ-Dropdown, kein „…"-Duplikat;
   Typ folgt der Auswahl (grauer Hinweis), **Sequence = „Mehrschritt"-Haken**, RPN/event_from_var
   erscheinen nur, wenn das Binding sie schon nutzt (deutsches ⓘ erklärt „was ist RPN");
   (c) Quelle-Dropdown deutsch: Achse/Taster/Schalter(haltend)/Hat + ⓘ (muss zur Hardware passen);
   (d) Achsen-Bereich **untereinander** (Eingang/Verarbeitung/Ausgang) mit konsistenten min/max-Labels;
   (e) Leer-Wert-Hinweise: grauer Kalibrier-Hinweis (leer = raw aus Kalibrierung, konkrete Werte),
   Event-Wert-ⓘ (leer = auto: Taster 1/Schalter-Zustand/Achsenwert); (f) **Picker-gefüllte Felder
   readonly** (Event/SimVar/Read/Sequence-Namen), Sequence-Schritte ohne event/simvar-Dropdown.
4. **Stufe C FERTIG — Panel-Outputs editierbar:** Doppelklick auf Output-Zeile → Editor-Fenster mit
   modellgetriebenem Feld-Baum (`gui_mapper.output_nodes` läuft generisch über die Pydantic-Modelle:
   gear_leds/multi_panel/radio_panel inkl. Selektoren, Bänke, bool_leds, Dimmer). Zeile anklicken →
   passende Edit-Leiste (Entry/Checkbox/Choice/Var-Picker readonly, „+ Eintrag" mit Bank-Vorlagen
   je Art, „✕ Entfernen", optionale Blöcke wie dimmer/source_toggle anleg-/entfernbar).
   `profile_writer.set_output_value/add_output_entry/remove_output_entry` = Punkt-Mutationen am
   Pfad (Kommentare bleiben), jeder Apply validiert VOR dem Schreiben. 13 Tests.
5. **Live-Spalte im Mapper** (User-Wunsch): gedrückte Tasten ●, Achsen als füllender Balken
   (`█░`-Zeichen + Rohwert), `evdev_reader.live_state_reader` (non-blocking drain, absinfo-Seed),
   after-Loop öffnet das gewählte Gerät lazy, Retry ~2 s. Hidraw-Panels bleiben leer (kein evdev).
   **Profil-Badge**: aktives Profil fett in der Statuszeile + im Fenstertitel.
   **🐞 Learn-Bugfix:** raw-Learn übergab den VAR-Katalog an `evdev_reader.discover()` (per
   suppress verschluckt → „nicht lesbar") — jetzt `_device_catalog()`.
6. **Air-Manager-Gauges GESICHERT** (User-Wunsch, viel Eigenarbeit): `reference/air-manager/` —
   7 „ES"-Instrumente (MAP+FuelConsumption, RPM, EGT, Airspeed, 3× Fuel), Template, Panel-BG,
   eigenes Piper-Panel + Dev-Configs (79 MB, größte Datei 14 MB → GitHub-safe). README dort.
   **Skalierungs-Analyse + Architektur: `docs/gauges-design.md`** (Zeiger-Formel, Presets, Plan).

**🔴 NÄCHSTES:**
1. **User sichtet die GUI live** (alles neu: Doppelklick-UX, Aktion-Eindampfung, Split-UI,
   Output-Editor, Live-Spalte, Badge, Theme) → Feedback-Fixes.
2. **Gauges-Tab** = EIGENES Feature (eigener Branch, `docs/gauges-design.md` liegt bereit):
   Canvas-Rundinstrumente, Zeiger frei auf Sim-Vars mappbar, Presets aus den Luas.
3. V:-Runtime-Verdrahtung (Design steht, s. 2026-07-13); HW-Capture „Lernen" für Source-Code
   (Live-Reader-Infrastruktur existiert jetzt!); Kette (gui-var-monitor + mapper-tab) → main.

## 🆕 SESSION 2026-07-15 (fortges.) — UX-Umbau aus Live-Feedback + modernes Theme
**Branch `feat/mapper-tab`, 251 Tests grün, ruff clean, Konstruktions-Smoke ok. Commits `9a46bfd`,
`fbbe9ff` (+`5b1d8c2`,`ece9403` s. u.). NICHT gepusht.** Weiteres Live-Feedback umgesetzt:
- **Editor = eigenes On-Demand-Fenster** (`ed_win` Toplevel, `withdraw`/`deiconify`): geöffnet per
  **„✏ Bearbeiten"-Zelle** in der Binding-Zeile, Doppelklick, oder „Bearbeiten…". Fenster-Knöpfe
  (Übernehmen/Zurücksetzen/Abbrechen) gelten für DAS eine Binding.
- **Knopf-Zuordnung klar**: Binding-Aktionen (Bearbeiten…/+Neu/Duplizieren/Entfernen) **rechtsbündig
  unter der Bindings-Tabelle**; Geräte-Rescan links; Profil-Aktionen im Profile-Tab.
- **Sequence-Schritt-Editor** (war Platzhalter): `gui_mapper.seq_action_to_rows`/`rows_to_seq_action`
  (rein, getestet) + `seqfr` mit on/off-Schritten (event/simvar, +Schritt/✕). `_ed_apply` baut die
  Aktion aus `seq_state`.
- **Aktion folgt der Variable**: prominenter „Wählen…" öffnet den (gefilterten) Var-Picker und setzt
  den Typ automatisch (K:=event, A:/L:/V:=simvar) — Typ-Dropdown nur noch für RPN/Sequence/event_from_var,
  ⓘ erklärt. (User wollte, dass man den Typ-Unterschied NICHT verstehen muss.)
- **Axis-Feldhilfe** auf **per-Feld-ⓘ-Tooltips** (statt Textblock) + **raw-Learn**: „Lernen…" liest die
  Achse live (`evdev_reader.axis_value_reader`), zeigt den Rohwert, „→ als min/max" übernimmt (Detent
  finden). Graceful ohne Gerät/evdev.
- **Profile-Tab** (letzter Tab, statt Dauer-Kopfzeile): Selector + Neu/Duplizieren/Entfernen +
  **Beschreibung + Auto-Auswahl** editierbar (`profile_writer.set_meta`, getestet).
- **Modernes Theme** (`clam` + helle Palette, flache Tabs mit Akzent) + **intuitiv gefärbte Knöpfe**:
  Accent(blau)=primär/Start, Danger(rot)=Stop/Entfernen.

**⚠️ NOCH VISUELL UNGEPRÜFT** (nur Konstruktions-Smoke, kein echtes Rendering): Layout/Optik von Theme,
Profile-Tab, Editor-Fenster, Sequence-Editor. **User sichtet beim nächsten Öffnen.** Offene Feature-Punkte
unverändert: Panel-Outputs inline editierbar (Stufe C), V:-Runtime, HW-Capture für Source-**Code**
(raw-Learn steht; Code-Capture-Stub `b_learn` noch disabled).

## 🆕 SESSION 2026-07-15 — Stufe B live gesichtet: Fixes + Profilverwaltung + Axis + Panel-Viewer
**Branch `feat/mapper-tab`. 247 Tests grün, ruff clean, py_compile ok. Committet (nicht gepusht).**
User hat die GUI live getestet, viel Feedback gegeben; alle Punkte umgesetzt (User: „ordentlich fertig,
ohne Nachfragerei"). **Achtung: GUI-Optik/Layout headless nicht prüfbar** (Xvfb fehlt, `DISPLAY=:0` ist der
Live-Desktop → kein Fenster ungefragt) — Absicherung war ruff-F821 + py_compile + reine Logik-Tests.
1. **🐞 „+ Neu"-Crash gefixt** (`gui.py`): rief sofort `form_to_binding(blank_form)` → `ValueError:
   Event-Name fehlt`. Neu: „+ Neu" geht in einen **„neues Binding"-Modus** (`etgt.index=None`) mit
   leerem Formular; **Validierung + Anhängen erst bei „Übernehmen"** → nie ein halbfertiger Stub im
   Profil. `_ed_apply` verzweigt bei `index None` → `add_binding`, sonst `apply_binding_edit`.
   `_ed_reset`/`_ed_duplicate`/`_ed_remove` gegen den Neu-Modus abgesichert.
2. **Profilverwaltung (neu, `gui.py` Profil-Zeile)**: Buttons **Neu / Duplizieren / Entfernen** neben
   dem Profil-Dropdown. `profile_writer.new_profile(name)` = minimales valides Skelett (+Start-Kommentar);
   Duplizieren = `load`+`name`-Rename+`dump` (Formatierung bleibt); Entfernen mit Bestätigung, letztes
   Profil geschützt. `_refresh_profiles(select=…)` setzt `profile_var` → Trace lädt Mapper/Statistik neu.
   Test `test_new_profile_validates_and_round_trips`.
3. **Axis-Editor erweitert + erklärt** (`gui.py`): Achsen zeigen jetzt **Eingang (roh) min/max**
   (= `raw_min`/`raw_max`) und **Ausgang (out) out_min/out_max** als Felder + ein **Feld-Glossar +
   Pipeline-Erklärung + Detent-Split-Anleitung**. **Detent-Split** braucht KEINE neue Modell-Funktion:
   `normalise()` klemmt Roh außerhalb min…max auf ±1 → zwei Bindings auf demselben Achsen-Code mit
   komplementären Roh-Bereichen decken „Detent=out 0" (oberer Teil) + „unter Detent = Reverse/Feather/
   Cutoff" (unterer Teil, eigene Aktion) ab. Workflow = »Duplizieren« + Roh-Bereiche setzen (im Text erklärt).
4. **Panel-Output-Detailviewer (neu)**: `gui_mapper.describe_output_detail(output)` entfaltet jeden Output
   in lesbare Kind-Zeilen — Selektor-Bänke, **Encoder-/Swap-Input-Codes**, LED-/Dimmer-Maps, alle Radio-
   Bank-Arten (freq/DME/ADF/XPDR). Der Mapper-Detailbaum rendert sie als Kinder je Output (`_render_detail`).
   Damit sind **Outputs UND Inputs der Panels sichtbar** (vorher nur „radio_panel — 37 SimVars"). 3 Tests.
   ⚠️ Panel-Outputs sind damit **sichtbar, aber noch nicht inline editierbar** (= Stufe C, s. u.).
5. **Test entkoppelt**: `test_apply_binding_edit_changes_only_the_target` hing an exakter Binding-
   Reihenfolge von `piper_arrow.yaml` — jetzt Sibling **vorher erfasst** statt hart-codiert (die Mapper-
   GUI editiert diese Profile ja als Live-Dateien).
6. **`piper_arrow.yaml` zurückgesetzt** (`git checkout`): der User hatte es beim Live-Testen verändert
   (Test-Duplikat „Aileron (roll) (Kopie)" + einmaliger Flow-Kollaps der hand-umbrochenen Bänke) — reine
   Test-Artefakte, zurückgesetzt → Handformatierung wieder da.

**🔴 NÄCHSTES (Reihenfolge):**
1. **Panel-Outputs inline EDITIERBAR** (Stufe C — jetzt sichtbar, aber read-only): Editor für multi/radio/
   switch outputs (Selektor-/Bank-/LED-/Dimmer-Felder), Sequence-Editor. **Vorlage = Vor-Mapper-Arrow-Profil**
   (git-History / alte SPAD-XMLs, s. [[reference-spadnext-profiles]]). Scope mit User klären.
2. **V:-Runtime-Verdrahtung** (Design steht, geparkt): Bridge = dummer geteilter `V:`-Hub in
   `bridge/bridge.py` (`set_simvar`/`read_subscribed` erkennen `V:`-Präfix → Dict, **sim-unabhängig**,
   vor `_check_alive`/DLL-Lock; Subscribe/Poll/read_now laufen dann automatisch). **Seeding** aus
   `profile.local_vars.initial` in `runtime.run` (Bridge bleibt profil-agnostisch). Reconnect-Reseed +
   Persist = Follow-up. Tests: Seeding als reine Funktion; Bridge-Store via sys.modules-Stub + `object.
   __new__`. simvars-reference.md §1 um V: ergänzen.
3. GUI weiter visuell sichten (Rest Stufe B), dann Kette (gui-var-monitor + mapper-tab) → main.
> Multi-Panel ist auf **`main`** gemerged. **`feat/gui-var-monitor` liegt vor `main` und ist
> verifiziert (Streaming/Index-Fix/Multi-Client/ADF/DME in-sim), aber NOCH NICHT nach main
> gemergt** (offene Enden: 10-Hz-Poll, Panel-Sichtprüfung).
> Aktueller Branch: **`feat/mapper-tab`** (von `feat/gui-var-monitor` abgezweigt, weil der Mapper
> die dortige GUI-Basis braucht). **243 Tests grün, ruff clean, 4 Profile valide, py_compile ok.**
> Ältere „UNCOMMITTED"-Marker weiter unten sind historisch (Code steht/committet).

## 🆕 SESSION 2026-07-13 (fortges.) — Mapper Stufe B: Inline-Editor + ruamel-Writer
**Branch `feat/mapper-tab`. Alles committet + getestet; GUI selbst VISUELL UNGEPRÜFT** (kein Fenster
ungefragt auf Live-Desktop `:0`). Commits: `f533b3e` Stufe A · `69a050b` V:-Deklaration · `24aa1a8`
Writer · `531dfef` Inline-Editor.

**User-Entscheidungen umgesetzt:** Edit-UX = **Inline-Editorpanel** (kein Popup); lokale Vars =
**mapper-interne Virtual-Vars** → als Art **`V:`** im Bridge-Hub geplant (Deklaration steht, Runtime offen).

**Gebaut (Reihenfolge = so morgen prüfen):**
1. **`profile_writer.py` (committet 24aa1a8)** — `ruamel.yaml`-Dep, kommentar-erhaltender Round-Trip.
   `_PaddedEmitter` polstert `{ }`-Flow-Maps → cessna_172/152/default **byte-identisch**, piper_arrow
   semantisch identisch (nur ~12 hand-umbrochene Output-Bänke kollabieren 1×). API: `load/dumps/dump/
   validate/apply_binding_edit/add_binding/remove_binding/set_local_vars`. 16 Tests.
2. **Inline-Editor (committet 531dfef)** in `gui.py` Mapper-Tab + reine Transforms in `gui_mapper.py`
   (`binding_to_form/form_to_binding/blank_binding_form`, 9 Tests): Binding in der Detail-Liste wählen →
   Panel unten (Name · Quelle kind+code · Aktion-Typ+Felder für event/simvar/event_from_var/rpn ·
   Transform bei Achsen). **Übernehmen** = `form_to_binding` → `profile_writer` load/apply/**validate**/
   dump (validate blockt kaputte Edits VOR dem Speichern). Auch **+Neu/Duplizieren/Entfernen**;
   Var-Picker (`…`) füllt Event/SimVar-Felder inkl. deklarierter `V:`-Vars. `sequence` bleibt erhalten,
   aber inline (noch) nicht editierbar; **„Lernen" (HW-Capture) = Stub** für später.
   **E2E-Rauchtest (offline) grün:** Editier-Pipeline an echtem piper_arrow → Event geändert, Kommentar
   + Flow-Style erhalten, re-parsed sauber.

**🔴 MORGEN — HIER WEITER (Reihenfolge):**
1. **GUI VISUELL SICHTEN** (das ist der offene Verify-Punkt, headless nicht prüfbar):
   `uv run python -m msfs_peripherals_bridge.gui` → Tab „Mapper". Prüfen: Binding wählen → Panel füllt
   sich? Aktions-Typ-Wechsel zeigt richtige Felder (event/simvar/…)? Transform nur bei Achsen sichtbar?
   `…`-Picker setzt Namen? **Test-Speichern**: ein Binding ändern → Übernehmen → `git diff profiles/…`
   = nur die eine Zeile geändert (+ ggf. 1× Output-Bank-Kollaps bei piper_arrow, harmlos)? +Neu/
   Duplizieren/Entfernen? Fenster groß genug (minsize 620x460)? Overrideredirect/WM-Zicken? Falls
   Event-Kaskaden (dev/detail `<<TreeviewSelect>>`) zicken → `_render_detail`/`_ed_on_detail_select`.
2. **Virtual-Vars Runtime-Verdrahtung**: Bridge-`V:`-Store + Protokoll (set/subscribe erkennt `V:`,
   serviert aus dem Hub) + Seeding aus `local_vars.initial` + optional Persist. Mit Bridge verifizieren.
   Editor-UI für `local_vars` (deklarieren/löschen) fehlt noch — `profile_writer.set_local_vars` steht.
3. Stufe C: Sequence-Editor, Bedingungen (V:/Sim), CRS/Heading-Bug; „Lernen" (HW-Capture).
4. **Separat:** `feat/gui-var-monitor` Restpunkte abnehmen → Kette (gui-var-monitor + mapper-tab) → main.

## 🆕 SESSION 2026-07-13 — Mapper-Tab Stufe A (Geräte-Viewer) GEBAUT
**Branch `feat/mapper-tab`** (neu, von `feat/gui-var-monitor`). **212 Tests grün, ruff clean,
4 Profile valide, py_compile ok.** Reiner Offline-Code; **GUI visuell UNGEPRÜFT** (kein Fenster
ungefragt auf den Live-Desktop `:0` geworfen — User sichtet selbst).

**Was gebaut (Stufe A = Nur-Lese-Übersicht, wie im Stufenplan A→B→C):**
- **Neues reines Logik-Modul `src/.../gui_mapper.py`** (dependency-frei, tkinter-los, testbar):
  `build_device_rows(catalog, profile, present)` → 1 Zeile je Katalog-Gerät (Transport, Present-
  Tri-State True/False/None, #bindings, #outputs); `describe_source/action/transform/binding` +
  `describe_output` (Typ + `len(simvars())`); `device_bindings/device_outputs`. Present-Tri-State:
  None = Erkennung n/a → Status „?", sonst „verbunden"/„nicht erkannt".
- **`gui.py` neuer „Mapper"-Tab:** links Geräte-Treeview (Gerät·Bus·Status·Bind·Out), rechts
  Detail-Treeview (Bindings mit Control/Aktion/Shaping + Outputs-Zusammenfassung) für das
  gewählte Gerät. Modul-Helfer `_discover_present(catalog)` = evdev+hidraw discovery, beide
  `contextlib.suppress`-geschützt (python-evdev optional) → None wenn gar nichts scannen konnte.
  **Discovery ist LAZY** (erst beim ersten Anzeigen des Tabs, `_on_tab_changed`) → Startup bleibt
  schnell. „Geräte neu erkennen"-Button = force rescan. Profil-Wechsel (`profile_var.trace_add`)
  lädt die Zeilen neu (ohne Rediscovery). Tab-Wechsel-Bind vereinigt (Statistik-`_resubscribe`
  + Mapper-Reload).
- **Tests `tests/test_gui_mapper.py` (12):** Zeilen-Reihenfolge/Zählung, Present-Tri-State,
  jede Action-Formatierung, Sequence-Summary, Transform (inkl. Expo-Kurve faltet Stärke ein —
  kein doppeltes „expo, expo=0.25"), Output-Summary. Plus Real-Profil-Smoke (piper_arrow):
  yoke 7 binds, switch_panel 17+gear_leds, multi 11+„13 SimVars", radio 0+„37 SimVars".

**🧩 USER-ENTSCHEIDUNGEN 2026-07-13 (für Stufe B/C):**
- **Edit-UX = Inline-Editorpanel** (kein Popup/Kontextmenü): Binding wählen → Felder erscheinen
  fest unter/neben der Detail-Liste (Name, Quelle kind+code + „Lernen", Aktions-Typ + typ-Felder,
  Transform bei Achsen), „Übernehmen"/„Zurücksetzen". „Lernen" (HW-Capture) = eigener späterer Schritt.
- **Lokale/eigene Variablen = mapper-interne Virtual-Vars** (User-Wahl: sim-unabhängig + persistent).
  Umsetzung als neue Var-Art **`V:`**, Werte **im Bridge-Werte-Hub** (nie in der Sim) → damit „setzen/
  auslesen wie jede andere Variable" für ALLE Clients gilt (inkl. GUI-Monitor). Set via `simvar`-Aktion
  mit `V:`-Namen, Read via Subscribe. ⚠️ Falls User strikt mapper-privat (für andere Tools unsichtbar)
  will → nur die Runtime-Verdrahtung ändert sich, das Deklarations-Modell bleibt.

**🆕 GEBAUT (Virtual-Var-Basis, committet 69a050b):** `models.LocalVar` (name[A-Za-z0-9_], unit,
initial, persist, description) + `Profile.local_vars` + Uniqueness-Validator; `gui_catalog.KIND_VIRTUAL
="V:"` + `local_var_catalog(local_vars)` speist deklarierte Vars in den Picker (settable). Tests
`tests/test_local_vars.py` (6). **Storage-agnostisch** — Speicherort erst bei der Runtime-Verdrahtung.

**🆕 GEBAUT (kommentar-erhaltender Writer, committet 24aa1a8):** `ruamel.yaml`-Dep + neues
`src/.../profile_writer.py`. Round-Trip erhält Kommentare/Quotes/Flow-Style; `_PaddedEmitter` polstert
Flow-**Map**-Klammern (`{ kind: axis }`) → **cessna_172/152/default byte-identisch**, piper_arrow
**semantisch** identisch (nur die ~12 hand-umbrochenen Output-Bank-Flow-Maps kollabieren einmalig auf
je 1 Zeile — Bindings/Kommentare byte-exakt; ruamel bewahrt keine manuellen Umbrüche IN Flow-Collections).
Flow-**Sequenzen** bewusst NICHT gepolstert (sonst `[]`→`[  ]`). Edits: `_sync` (in-place, erhält
Kommentare/Style, pruned entfernte Keys), `_node` (neue Nodes, Flow für all-scalar). API: `load/dumps/
dump/validate/apply_binding_edit/add_binding/remove_binding/set_local_vars`. Tests `test_profile_writer.py`
(16): byte+semantisch Round-Trip, Edits, Kommentar/Flow-Erhalt, local_vars, Validierungs-Guard.

**🔴 NÄCHSTE SESSION:**
1. **GUI visuell sichten** (`uv run python -m msfs_peripherals_bridge.gui` → Tab „Mapper"):
   Geräte-Liste + Detail lesbar? Status stimmt (Panels angesteckt → „verbunden")? „Neu erkennen"
   aktualisiert? Profil-Dropdown-Wechsel lädt die Liste um?
2. **Stufe B Inline-Editorpanel** (Writer STEHT): Panel unter der Detail-Liste — Binding wählen →
   Felder (Name, Quelle kind+code, Aktion-Typ + typ-Felder, Transform bei Achsen), „Übernehmen" ruft
   `profile_writer.apply_binding_edit` + `validate` + `dump`, dann Mapper-Reload. Add/Remove/Duplizieren.
   Var-Auswahl über `_open_var_picker` (jetzt inkl. V:). „Lernen" (HW-Capture) = eigener späterer Schritt.
3. **Virtual-Vars Runtime-Verdrahtung** (nach dem Panel): Bridge-`V:`-Store + Protokoll (set/subscribe
   erkennt `V:`-Präfix, serviert aus dem Hub) + Seeding aus `local_vars.initial` + optional Persist-
   Snapshot. Mit Bridge zu verifizieren. simvars-reference.md §1 um V: ergänzen.
4. Danach Stufe C (Sonderfunktionen: Bedingungen aus V:/Sim-Vars, CRS/Heading-Bug, Sequence-Editor).
5. **Separat (nicht Mapper):** `feat/gui-var-monitor` offene Enden abnehmen (10-Hz-Poll,
   Panel-overrideredirect-Sicht) → dann diese ganze Kette (gui-var-monitor + mapper-tab) nach main.

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
