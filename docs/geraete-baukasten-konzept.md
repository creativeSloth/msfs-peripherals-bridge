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

## Zielbild: zentraler Geräte-Hub, Funktionsparität, ohne KI

Der Maßstab: ein Fremder — **keine Geräteliste, kein einziger gemappter Knopf** —
steckt sein Saitek-Panel (oder einen Arduino, s. u.) an, lässt es **erkennen**
und mappt danach **selbstständig, ohne KI, zentral am Gerät** genau das, was der
Autor heute kann. „Zentral am Gerät" = EIN geräte-eigener Arbeitsplatz (aus dem
Geräte-Explorer geöffnet), der alles bündelt:

| Funktion (Parität) | Baustein | heute |
|---|---|---|
| Achse anlegen + kalibrieren | axis + Roh-Bereich | teils (`calibration.py`, Profil) |
| Knopf/Schalter anlegen + benennen | button/switch + Alias | Input-Scan (Schritt B) |
| Encoder anlegen (2 Ringe/Richtungen) | encoder | Radio-Capture da, zu generalisieren |
| Selektor-Positionen anlegen | selector | Capture da |
| **LED setzen je nach Sim-Output** | led ← Var/Bedingung | hardcodiert (`bool_leds`/`gear_leds`/`mode_leds`) → generalisieren |
| **Display anlegen + Werte aus Sim setzen** | sevenseg/display-bank ← Var | hardcodiert (Radio/Multi-Render) → generalisieren |

Der Knackpunkt für echte Parität sind die **Ausgänge** (LED-aus-Sim,
Display-Werte): heute stecken sie in Saitek-spezifischem Code
(`MultiPanelOutput`/`RadioPanelOutput`, DME/ADF/XPDR-Renderlogik). Für ein
selbst-angelegtes Gerät müssen dieselben Fähigkeiten **datengetrieben über die
GUI** erreichbar sein — „diese LED leuchtet, wenn Var X = Y" und „diese
Display-Zelle zeigt Var Z". Das ist **Schritt E** (generische Output-Modelle):
der größte Brocken, aber für „ohne KI selbst durchmappen" der entscheidende.

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

## Wie erkennt man Knöpfe & Anzeigen eines WIRKLICH unbekannten Geräts?

Der Kern: **Der Nutzer bekommt NIE HID-Bytes oder Bit-Nummern zu sehen.** Die
Technik läuft im Hintergrund; erlebt wird ein geführter Assistent mit
Klartext-Ergebnis („Gefunden: **12 Knöpfe, 2 Achsen, 3 Lämpchen, 1 Display mit 5
Stellen**"). Das geht in **zwei Schichten**:

### Schicht 1 — „Das Gerät stellt sich selbst vor" (automatisch)

Jedes USB-Gerät trägt eine **maschinenlesbare Selbstbeschreibung** in sich (den
HID-Report-Descriptor), auf Linux lesbar unter
`/sys/class/hidraw/*/device/report_descriptor` (bestätigt vorhanden). Ihn zu
parsen liefert **ohne jede Nutzer-Aktion**:

- Anzahl **Knöpfe / Achsen / Hats** (Standard-Usages: Button-Page, Generic
  Desktop) + ihre Bit-/Byte-Position im Report,
- Anzahl **LEDs / Lämpchen** (Standard-LED-Usage-Page),
- die Report-Längen (die wir intern zum Ansteuern brauchen).

Bei evdev-Geräten (Yokes/Pedale/Quadranten) ist das noch einfacher:
`InputDevice.capabilities()` gibt Knöpfe+Achsen+Bereiche direkt her (das nutzt
`capabilities.describe()` schon). ⇒ **Klartext-Ausgabe an den Nutzer, keine
Bytes.**

**Ehrliche Grenze:** Der Descriptor beschreibt Standard-Knöpfe/-Achsen/-LEDs
zuverlässig, aber **herstellereigene Teile — besonders 7-Segment-Displays —
oft nur als undurchsichtigen „Vendor-Block" von N Bytes** ohne Bedeutung. Genau
das ist der Saitek-Fall (deshalb mussten die Display-Bytes von Hand vermessen
werden). Schicht 1 findet also das Skelett; die Display-Semantik fehlt noch.

### Schicht 2 — „Zeig es mir" (geführt, für alles, was Schicht 1 nicht benennt)

Ein **Assistent ohne Code** macht den Nutzer zum Sensor:

**Knöpfe/Achsen/Encoder (= Eingänge, Schritt B):**
- „**Drücke jetzt einen Knopf.**" → System sieht, welches Signal sich ändert
  (Flankenzählung, `edge_count_reader` — existiert) → „Erkannt ✓. **Wie soll er
  heißen?**" → Nutzer tippt „AP" / „Fahrwerk aus" oder wählt aus einer Liste.
- Achse: „Hebel **ganz vor** … jetzt **ganz zurück**" → nimmt den Bereich auf
  (Kalibrierung). Encoder: „**Im Uhrzeigersinn** … jetzt **dagegen**."
- Ergebnis: eine **benannte Liste** von Bedienelementen. Kein Byte sichtbar.

**LEDs & Displays (= Ausgänge, der schwierige Teil):**
- Software kann NICHT von allein wissen, was eine Anzeige zeigt, wenn der
  Descriptor schweigt — **irgendwer muss aufs Gerät schauen.** Also:
- „**Ich schalte jetzt der Reihe nach jedes Ausgangssignal ein — sag mir, was
  passiert.**" → System sendet EINEN Testimpuls (verallgemeinertes
  `panel_probe`) → Nutzer schaut aufs echte Gerät → „oben links leuchtet grün" →
  **klickt die Stelle auf einem Bild/Nachbau des Geräts an** oder tippt ein
  Label.
- Display: System schickt eine Test-Ziffer („**8.**") auf jede Zelle nacheinander
  → „**Welche Stelle zeigt jetzt eine 8?**" → Nutzer zeigt drauf.
- So entsteht die LED-/Display-Karte **durch Beobachtung**, komplett als
  „hinschauen & sagen" formuliert. (Kür-Ausbaustufe: Webcam erkennt selbst,
  welche LED angeht — dann entfällt der Mensch. Später.)

### Was der Nutzer am Ende hat (nicht-Programmierer-Form)

Nicht die YAML/`DeviceSpec` (die wird still im Hintergrund geschrieben), sondern:

- ein **Bild/Nachbau seines Geräts**, das sich beim Durchgehen füllt:
  „✓ 12 Knöpfe benannt · ✓ 3 Lämpchen · ✓ 1 Display (5 Stellen)",
- alles in **Klartext**, Schritt für Schritt, mit „Überspringen"/„Zurück",
- danach ist das Gerät ganz normal im Mapper bespielbar.

**Fazit für den Nutzer, ehrlich:** Knöpfe/Achsen = **fast automatisch** (Gerät
beschreibt sich selbst; Nutzer *benennt* + *kalibriert* nur durch Drücken/
Bewegen). LEDs = **automatisch gefunden, durch Hinschauen benannt**.
7-Segment-/Vendor-Displays = **rein per Software nicht ermittelbar**; hier ist
die „Testimpuls → Mensch bestätigt"-Schleife physikalisch nötig — aber als
einfacher Schau-&-Klick-Assistent, nie als Bytes.

---

## Beliebiges Gerät: anlegen → durchstrukturieren → mappen

Grundprinzip: **völlig custom** — ein selbstgebautes „Saitek-artiges" Panel, ein
Arduino, was auch immer denkbar ist — muss sich in **drei Schritten** bändigen
lassen, alle in der GUI, ohne Code:

1. **Anlegen** — Gerät erkennen/registrieren *(Schritt A, gebaut)*.
2. **Durchstrukturieren** — seine Bausteine festlegen: welche Knöpfe/Achsen/
   Encoder/Selektoren (Eingänge) und welche LEDs/Displays (Ausgänge) es hat
   (Schicht 1 automatisch, Schicht 2 per Schau-&-Klick-Assistent).
3. **Mappen** — jeden Baustein an Sim-Var/Event binden (Eingang→Event, LED←Var,
   Display-Zelle←Var), mit denselben Funktionen wie im heutigen Mapper.

Das `DeviceSpec`-Modell ist bewusst **transport- und hersteller-agnostisch** — es
kennt nur Bausteine. Deshalb passt „irgendein Gerät" grundsätzlich hinein; die
Arbeit steckt in den **Transport-Adaptern** und den **generischen
Output-Modellen** (Schritt E).

### Und ein Arduino / Selbstbau-Gerät? *(zurückgestellt — erst später)*

> Vom User bewusst **hinten angestellt.** Hier nur als Notiz, damit das
> Baukasten-Modell transport-agnostisch bleibt und der serielle Weg später ohne
> Umbau andockt. Fokus zuerst: HID-Geräte (Saitek & Custom-Panels).

1. **Arduino als Standard-USB-HID** (z. B. Leonardo/Micro/Pro Micro, ATmega32u4 +
   Joystick/HID-Library): meldet sich wie jedes Gerät als evdev-Joystick bzw.
   hidraw → **exakt derselbe Weg** (Auto-Enumeration + Descriptor + Scan);
   LEDs/Displays als HID-Output-Reports. **Empfohlen**, kein neuer Transport.
2. **Arduino als serielles Gerät** (CDC/ACM, `/dev/ttyACM*`): KEIN HID → die
   Selbstbeschreibung endet, der Sketch sendet ein **beliebiges eigenes
   Protokoll**. Nötig: neuer **`transport: serial`** + Reader/Writer + eine
   **Protokoll-Schicht**:
   - a. **Bekanntes, selbstbeschreibendes Protokoll** — wir liefern einen
        **Referenz-Sketch**, der beim Verbinden seine Pins/Fähigkeiten ansagt →
        Erkennung wieder automatisch, Assistent identisch. Vorbild: **MobiFlight**
        (Arduino-Firmware mit definiertem Protokoll, de-facto-Standard für
        Selbstbau-Sim-Panels) — Kompatibilität dazu wäre der Ökosystem-Anschluss.
   - b. **Völlig eigener Sketch** — keine Auto-Erkennung. Eingänge gehen per
        Scan-Assistent (Knopf → serielles Byte ändert sich → erfassen); Ausgänge:
        Nutzer gibt das Kommandoformat an. Meiste Handarbeit.

**Ehrlich für Nicht-Programmierer:** HID-Arduino = wie jedes Gerät (plug & scan).
Serieller Selbstbau = braucht einmalig eine Firmware mit bekanntem Protokoll
(unser Referenz-Sketch oder MobiFlight) — das **Flashen** ist die einzige
technische Hürde, danach wieder derselbe Assistent.

---

## Offene Konzeptfragen (Entscheidung beim User)

- **HID-Descriptor-Parser bauen.** Neue Fähigkeit (Schicht 1 oben): sysfs
  `report_descriptor` parsen → Knöpfe/Achsen/LEDs + Report-Längen automatisch.
  Reduziert die „Byte-für-Byte"-Handarbeit auf die vendor-opaken Display-Teile.
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
