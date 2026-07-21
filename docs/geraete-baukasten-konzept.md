# Konzept: Geräte-Baukasten — fremde Geräte selbst anlegen, kalibrieren, mappen

> **Status: Entwurf (2026-07-21), noch nicht gebaut.** Dieses Dokument hält die
> Vision + den Ist-Zustand + einen umsetzbaren Weg fest, damit der Bau daran
> anknüpfen kann. Es ersetzt kein Ticket — es ist die Denkgrundlage.

## Vision (User)

Fremde User sollen ihre Geräte **selbst** einrichten — ohne YAML-Handedit, ohne
Code. Sie sollen ihr Gerät **wie aus Bausteinen zusammensetzen**:

- **Eingänge:** Knöpfe, Schalter, Achsen, Encoder, Selektoren, Hats.
- **Ausgänge:** LEDs, Displays, 7-Segment-Anzeigen.

…und diese Bausteine **konfigurieren, kalibrieren und mappen**, sodass das
selbst-angelegte Gerät danach ganz normal im Mapper benutzbar ist.

---

## Ist-Zustand & die zentrale Lücke (2026-07-21)

**Frage des Users: „Wird ein fremdes Gerät beim reinen USB-Anstecken sofort
erkannt?" → Antwort: NEIN, aktuell nicht.** Konkret:

- **Erkennung ist katalog-gebunden.** `evdev_reader.discover()` und
  `hidraw_reader.discover()` liefern **nur** Geräte, deren Vendor/Product (+
  optional Name) in `config/devices.yaml` steht. Ein unbekanntes Gerät taucht
  **nicht** als mappbar auf.
- **`DeviceDef` (models.py) beschreibt nur das USB-Match** — `id`, `vendor`,
  `product`, `transport`, `name_match`. Es sagt **nichts** darüber, welche
  Knöpfe/LEDs/Displays das Gerät physisch hat.
- **Die Panel-Struktur ist hartverdrahtet.** `MultiPanelOutput` /
  `RadioPanelOutput` (models.py), die Report-Layouts in
  `mapping/panel_probe.py` und die Bit-Tabellen in den Profilen sind
  Saitek-spezifisch. Für ein fremdes Panel gibt es **keine** Beschreibung.
- **`msfs-bridge scan` (`capabilities.scan()`)** listet zwar **alle** evdev-
  Controller roh (unabhängig vom Katalog) — aber nur evdev (Achsen/Knöpfe),
  **keine** hidraw-Panels, und es **legt/speichert nichts an**.

➡️ Der Baukasten braucht eine **neue Datenschicht**: eine
**Hardware-Beschreibung je Gerät** (welche Bausteine, an welcher HW-Adresse),
**getrennt** vom per-Flugzeug-Mapping.

---

## Die Bausteine (Primitive)

Vieles existiert schon als Enum/Modell — es muss nur **generisch** (statt
Saitek-hardcodiert) und **user-anlegbar** werden.

**Eingänge**

| Baustein | Was | heute im Code |
|---|---|---|
| Taster (button) | 1 Code, Press-Flanke | `SourceKind.BUTTON` |
| Schalter (switch) | 1 Code, Zustand an/aus | `SourceKind.SWITCH` (hidraw-Bit) |
| Achse (axis) | 1 Code, Rohbereich min..max + Kalibrierung | `SourceKind.AXIS` + `config/calibration.yaml` |
| Encoder-Ring | 2 Codes (cw/ccw) | `RadioUnit.outer_/inner_cw/ccw` |
| Selektor | n Codes (Positionen) | Multi-/Radio-Selektor |
| Hat | 4 Richtungen (code/value) | `HatMap` / `HatDirection` |

**Ausgänge**

| Baustein | Was | heute im Code |
|---|---|---|
| LED | 1 Bit in einem Feature-Report | `bool_leds`/`gear_leds` + `panel_probe.*_led_report` |
| 7-Segment-Zelle | 1 Ziffer an Report-Offset (+ Punkt) | `panel_probe.*_cell_report` |
| Display-Bank | n Zellen = 1 Wert (active/standby) | `RadioBank`/`DmeBank`/`AdfBank`/`XpdrBank` |
| Punkt/Flag | einzelnes Bit/Flag | `dot` in den cell-Reports |

**Ein Gerät = Liste solcher Bausteine + je Baustein die HW-Adresse** (evdev-Code
bzw. hidraw Report-Byte/Bit/Offset).

---

## Zielmodell (neu): geräte-eigene Hardware-Spec

Skizze eines neuen `DeviceSpec` — **getrennt** von der USB-`DeviceDef`,
**user-schreibbar** (Overlay, nicht die versionierte `devices.yaml`):

```yaml
# ~/.config/msfs-peripherals-bridge/devices.local.yaml  (Vorschlag)
id: mein_panel
usb: { vendor: "1234", product: "5678", transport: hidraw }
inputs:
  - { block: button,   name: "AP",       code: 12 }
  - { block: axis,     name: "Throttle", code: 0, raw: [0, 4095] }
  - { block: encoder,  name: "Heading",  cw: 40, ccw: 41 }
outputs:
  - { block: led,      name: "AP-Lampe", report: 3, bit: 2 }
  - { block: sevenseg, name: "COM act",  report_offset: 1, cells: 5 }
```

Damit werden **Mapping** (Binding referenziert `name`), **Kalibrierung** (`raw`
pro Achse) und **Output-Test** (report/bit/offset pro LED/Zelle)
**datengetrieben** statt Saitek-hardcodiert. Profile referenzieren dann `name`
statt roher Codes → dasselbe Profil-Format, nur mit eigener Hardware bestückt.

---

## Workflow im GUI-Geräte-Explorer (Kontextmenü an der Geräteliste)

1. **Anstecken → sehen.** Auto-Enumerator listet **alle** USB-HID/evdev-Geräte
   (bekannt + „nicht registriert"). Bausteine dafür existieren: evdev via
   `evdev.list_devices()`, hidraw via `/sys/class/hidraw` + `uevent`
   (`hidraw_reader._usb_ids`).
2. **Kontextmenü „Neues Gerät anlegen…"** → USB-IDs vorbefüllt, `transport`
   geraten (hidraw, wenn nur hidraw-Node; sonst evdev).
3. **Inputs scannen (Signal-Sicht).** „Alle Inputs anzeigen" = live **alle**
   Codes mit Wert/Flankenzähler (baut auf `edge_count_reader` /
   `live_state_reader`). User betätigt einen Knopf → Baustein `button@code`
   vorgeschlagen, **Alias** vergeben. Achse → `axis@code`, Rohbereich per
   Kalibrier-Schritt (bewegen → min/max). Encoder → beide Richtungen drehen →
   cw/ccw. **← das ist das „allgemeine Knopf-Alias-Mapping über Kontextmenü".**
4. **Outputs scannen (Anzeige-Identifikation).** „Ausgänge durchprobieren" =
   systematisch Feature-Report-Bytes/Bits variieren und senden (generalisiertes
   `panel_probe`); User bestätigt „diese LED ging an" / „Zelle 3 zeigte 8" →
   Baustein `led@report/bit` bzw. `sevenseg@offset`.
5. **Kalibrieren.** Achsen min/max/Mitte (`calibration.py` existiert),
   Encoder-Schrittweite, Selektor-Positionen als Einzel-Codes anlernen
   (`edge_count_reader`, gibt es schon für die Saiteks).
6. **Speichern.** In das **user-Overlay** (nicht die versionierte
   `devices.yaml`). Danach erscheint das Gerät regulär und ist im Mapper
   mappbar; Bindings/Outputs referenzieren die Alias-Namen.

---

## Offene Konzeptfragen (Entscheidung beim User)

- **Output-Struktur unbekannter Panels.** Report-Länge/-Aufbau eines FREMDEN
  Panels ist unbekannt → „Durchprobier-Modus" (Byte für Byte variieren, User
  bestätigt visuell) nötig; als Startpunkt evtl. den **HID-Report-Descriptor**
  auslesen (liefert Report-Längen). Das ist der schwierigste Teil.
- **Overlay-Speicherort.** `~/.config/msfs-peripherals-bridge/devices.local.yaml`
  (empfohlen) vs. `gui-settings.json`. Repo-`devices.yaml` bleibt „meine HW".
- **udev-Rechte.** Für hidraw/Joystick-Zugriff braucht es eine udev-Regel
  (root). Optionen: Regel generieren + via `pkexec` schreiben **oder** nur
  anzeigen zum Kopieren (sicherer). Ohne Rechte kein Live-Scan.
- **Wie tief data-driven?** Minimal reichen generische **Input**-Blocks +
  **LED**-Blocks fürs Mappen. Voll = auch die komplexen Multi-Zellen-Displays
  (DME/ADF/XPDR-Renderlogik) auf die generische `sevenseg`/`display-bank`-
  Beschreibung heben → großer Umbau der hardcodierten Panel-Controller.
  **Empfehlung: schrittweise** — erst Inputs + einfache LEDs generisch, komplexe
  Displays später.
- **Reihenfolge/Priorität** (Vorschlag): (A) Auto-Enumeration + Explorer →
  (B) Input-Scan + Alias → (C) Kalibrierung → (D) Output-Scan → (E) generische
  Output-Modelle.

---

## Wiederverwendbar (schon vorhanden)

- `capabilities.scan()` — evdev-Roh-Enumeration (unabhängig vom Katalog).
- `hidraw_reader._usb_ids` + `/sys/class/hidraw` — hidraw-Enumeration.
- `edge_count_reader` / `live_state_reader` — flanken-fangendes Input-Capture.
- `config/calibration.py` (+ `calibrate`-CLI) — Achsen-Kalibrierung.
- `mapping/panel_probe.py` — Output-Test je Zelle/LED (heute Saitek-spezifisch,
  zu generalisieren).
- GUI-Mapper (Editor + Nachbau) — die Ziel-Oberfläche, in die der Explorer
  eingebettet wird.

---

Verwandt: [`INSTALL.md`](INSTALL.md) (heutiger manueller Weg: Schritt 2b + 3),
[`running.md`](running.md), Panel-HID-Maps in
`docs/memory/{multi,radio}-panel-hid.md`.
