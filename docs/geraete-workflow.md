# Geräte-Workflow — von null zum fertig gemappten Gerät

> Die **systematische Kette**, wie ein beliebiges Gerät erkannt, in seine
> Funktionen zerlegt, kalibriert und gemappt wird. Sie ist die Referenz, an der
> sich die GUI (Geräte-Explorer, Geräteelemente-Editor, Mapper) ausrichtet — jeder
> Knopf gehört zu genau einer Phase. Grundprinzip: **zwei Schichten sauber
> trennen.**

## Zwei Schichten (das Ordnungsprinzip)

| | ① STRUKTUR — „Was *hat* das Gerät?" | ② FUNKTION — „Was *macht* es in DIESEM Flugzeug?" |
|---|---|---|
| Frage | welche Knöpfe/Achsen/LEDs/Displays existieren physisch | welches Element löst welches Event / zeigt welche Variable |
| Gültigkeit | **einmal pro Gerät**, flugzeug-unabhängig | **pro Flugzeug** |
| Datenablage | Geräte-Overlay `~/.config/.../devices.local.yaml` (`ddef.inputs`/`ddef.outputs` = `InputBlock`/`OutputBlock`) | Profil `profiles/<flugzeug>.yaml` (`bindings` + `outputs`) |
| Ort in der GUI | Geräte-Explorer → **„Geräteelemente…"** | **Mapper** (Tabelle / Nachbau) |
| Hinzufügen/Entfernen betrifft | das **Element** (die Hardware-Beschreibung) | das **Mapping** (die Belegung) — das Element bleibt |

**Merksatz:** Elemente legt man in ① an und entfernt sie dort. Im Mapper (②)
*belegt* man sie und *löst* Belegungen — man löscht dort nie das Element selbst.

---

## Die Kette — 5 Phasen

### Phase 0 · Erkennen (Enumeration)
- **Ziel:** das angesteckte Gerät sichtbar und registrierbar machen.
- **Wie:** Geräte-Explorer listet **alle** evdev+hidraw-Nodes (`devices/inventory.py`
  `classify()`), auch unbekannte. Unregistriertes Gerät → „Registrieren…" (Kurz-ID)
  → Overlay-Eintrag; Transport (`evdev`/`hidraw`) wird automatisch bestimmt.
- **Automatisch:** Enumeration, USB-Ids, Transport, Dedup (evdev-Schatten eines
  hidraw-Panels wird unterdrückt).
- **Manuell:** die Entscheidung „dieses Gerät will ich" + ein Kurzname.
- **Ergebnis:** Gerät ist im Katalog, aber **leer** (0 Elemente).
- **Stand:** ✅ gebaut.

### Phase 1 · Funktionen erkennen (Struktur — Elemente anlernen)
- **Ziel:** **systematisch jeden** physischen Baustein erfassen. Reihenfolge egal,
  aber vollständig — das ist die „muss ich alles erkennen?"-Phase: **ja, hier, einmal.**
- **Wo:** Geräteelemente-Editor. Zwei getrennte Gruppen: **Eingaben (Lesen)** und
  **Anzeigen (Schreiben)**.
- **Eingaben** — „+ Input anlernen…": am Gerät betätigen → Live-Capture erkennt den
  Code, dann Name.
  - Taster/Schalter: eine Flanke (hidraw `edge_count_reader`+`winning_code` bzw.
    evdev `button_edge_reader`+`key_edges`).
  - Encoder: zwei Schritte (CW/CCW).
  - Achse: Bewegung von Anschlag zu Anschlag (evdev `winning_axis` — erfasst
    zugleich den **Rohbereich**, s. Phase 2).
  - Selektor/Hat: mehrere Positionen (Follow-up bzw. über „Aus Vorlage füllen").
- **Anzeigen** — „+ Anzeige hinzufügen…": LED (1 Lampe) oder Display (Zellenzahl,
  jede Zelle einzeln adressierbar wie beim DME) → Name.
- **Abkürzung:** „Aus Vorlage füllen…" projiziert ein bekanntes Muster
  (`gui_mapper.template_elements`: Saitek-Panels, Yoke, TQ6, Pedale) in einem Rutsch
  in die Element-Listen.
- **Ergebnis:** `ddef.inputs`/`ddef.outputs` = vollständige **Bausteinliste**.
- **Stand:** ✅ Eingaben komplett (hidraw + evdev Achse/Taster/Schalter/Encoder).
  ⚠️ **Ausgang-Scan** („welcher Report/Bit treibt *diese* LED/Zelle?") = **Phase 1b /
  Schritt D**, noch halb-manuell: Testimpuls (🔦 `panel_probe`) → Mensch bestätigt.
  Heute deklariert man Anzeigen von Hand (Name + Zellenzahl); die Hardware-Adresse
  füllt der Ausgang-Scan später.

### Phase 2 · Kalibrieren (nur analoge Achsen)
- **Ziel:** Rohwert-Bereich + Form einer Achse festlegen; digitale Elemente brauchen
  nichts (ihr Code genügt aus Phase 1).
- **Roh-Bereich:** wird beim Achsen-Anlernen (Phase 1) direkt miterfasst
  (`raw_min`/`raw_max`), zusätzlich `config/calibration.yaml` (`apply_calibration`).
- **Form:** Deadzone, Kurve/Expo, Invert, Detent-Split — beim **Mappen** der Achse
  (Transform im Binding-Editor); „→ als min/max/Detent" liest Live-Rohwerte
  (`axis_value_reader`).
- **Stand:** ✅ Rohbereich beim Anlernen; Transform im Binding-Editor.

### Phase 3 · Mappen (Funktion — pro Flugzeug)
- **Ziel:** jedem deklarierten Element eine Sim-Wirkung geben.
- **Eingabe → Event/Variable** (Binding): Quelle **per Name** aus den Phase-1-
  Elementen wählen (Binding-Editor „📋 Benannt" = `device_input_sources`), nicht über
  rohe Codes. Aktion = Event, SimVar-Write, Sequenz, EventFromVar, RPN.
- **Anzeige ← Variable:** die LED/Display-Zelle folgt einer Sim-Variablen.
- **Entfernen = Mapping lösen** (Element bleibt in ①).
- **Stand:** ✅ Eingabe-Mapping voll (inkl. Namens-Brücke). ⚠️ **Ausgabe-Mapping pro
  Element generisch = Schritt E** — heute treiben die **hardcodierten
  Panel-Controller** (Saitek Multi/Radio/Gear) die Anzeigen; „ein LED/eine Zelle ←
  Var" für Fremdgeräte fehlt noch. Deshalb wirkt die Ausgabe-Seite im Mapper heute
  weniger konsistent als die Eingabe-Seite.

### Phase 4 · Prüfen
- **Eingaben:** im **Nachbau** glimmen betätigte Schalter/Achsen live (aus dem
  rohen evdev/hidraw-State).
- **Anzeigen:** 🔦 Test-Send (`panel_probe`) identifiziert jede LED/Zelle am echten
  Gerät; **Glow-aus-Sim** (Anzeige zeigt den gelesenen Wert) = Ausbaustufe.
- **Anordnen:** Bearbeitungsmodus im Nachbau — Elemente ins Raster ziehen
  (`panel_layout` Overrides), pro Gerät gespeichert.
- **Stand:** ✅ Live-Eingaben, Test-Send, Nachbau-Editor. ⚠️ Glow-aus-Sim offen.

---

## Der Nachbau ist die einzige Mapper-Oberfläche (Entscheidung 2026-08-07)

Die **Tabellenansicht entfällt** — der **Nachbau** ist die eine, primäre Fläche.
Alles, was man mappt, tut man **am Element** (Klick / Rechtsklick), nicht über eine
separate Tabellenzeile. Das ist auch der Grund, warum „Entfernen" heute halb tot
wirkt: es hängt an einer Tabellen-Auswahl, die es im Nachbau gar nicht gibt.

**Konsistenz-Regel — jede Aktion hängt am Nachbau-Element:**

- **Elemente hinzufügen/entfernen → nur Geräteelemente-Editor (Phase 1).** Der
  Mapper legt keine Hardware-Bausteine an.
- **Klick auf ein Element:**
  - gemappt → Editor öffnen; leer (physisch, ungemappt) → **neu mappen** (Quelle
    vorbelegt) — beides existiert schon.
- **Rechtsklick auf ein Element → Kontextmenü:** *Bearbeiten · Duplizieren ·
  Mapping entfernen* (gemappt) bzw. *Neu mappen* (leer). So greifen Bearbeiten/
  Entfernen ohne Tabellen-Auswahl.
- **Kopf-Aktionen** wirken auf das zuletzt gewählte Element bzw. das ganze Gerät:
  **„+ Eingabe"** (Element belegen), **„+ Ausgabe"** (Anzeige belegen — generisch
  erst mit Schritt E; bis dahin Saitek-Controller/Vorlage), **„✎ Anordnen"**.
- **Kalibrieren** hängt an der Achse (Phase 2), nicht an einem eigenen Knopf.

Übergang: erst den Nachbau **selbst­tragend** machen (Kontextmenü + Element-Klick
decken Anlegen-Belegen-Ändern-Entfernen ab), **dann** Tabelle + „Tabelle↔Nachbau"-
Umschalter entfernen. Der `detail`-Baum darf intern als Datenquelle bleiben, muss
aber nicht mehr sichtbar sein.

## Was für volle Systematik noch fehlt
1. **Schritt D — Ausgang-Scan:** LED/Zelle → Report/Bit halb-automatisch
   (Testimpuls-Schleife) statt manueller Zellenzahl.
2. **Schritt E — generische Ausgabe-Laufzeit:** `ddef.outputs` (+ Var-Mapping)
   treiben Anzeigen direkt und ersetzen die hardcodierten Saitek-Controller. Erst
   damit ist „+ Ausgabe pro Element" im Mapper voll konsistent zur Eingabe-Seite.
3. **Selektor/Hat-Capture** im Elemente-Editor (heute über „Aus Vorlage füllen").
4. **Exotische evdev-Encoder** (melden als REL/Achse statt Key) — Capture-Sonderfall.
