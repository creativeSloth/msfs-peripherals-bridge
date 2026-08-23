# Handbuch — msfs-peripherals-bridge

Das **eine** Dokument, das dich von null bis zum Fliegen bringt: Installation,
Geräte einrichten, Mappen, Profile teilen und die Bridge zum echten MSFS. Für
**alle** gedacht — auch ohne Python-, Linux- oder Terminal-Erfahrung.

> **So liest du dieses Handbuch:**
> - Nur schnell loslegen? → **[Teil A · Schnellstart](#teil-a--schnellstart-4-befehle)** (4 Befehle, danach alles per Klick).
> - Alles im Detail, eigene Hardware, echtes Fliegen? → **[Teil B](#teil-b--alles-im-detail)**.
> - Für **jeden Schritt** gibt es den Weg **🖱 in der App** *und* **⌨ im Terminal** — nimm, was dir lieber ist.
> - Grüne **✓**-Kästchen sagen dir, woran du merkst, dass ein Schritt geklappt hat.

---

## Was ist das eigentlich?

Dieses Programm verbindet deine **Flugsimulator-Hardware** (Joke/Yoke, Schubhebel,
Pedale, Schalt-Panels …) unter **Linux** mit dem **Microsoft Flight Simulator
2020**. Es liest deine Geräte, wendet ein **Mapping pro Flugzeug** an (welcher
Knopf macht was) und schickt das Ergebnis an den Simulator.

Es gibt dabei **zwei Programme** — und nur eines läuft in Wine:

| Programm | Wo es läuft | Aufgabe |
|---|---|---|
| **`msfs-bridge`** (diese App) | **nativ unter Linux** | liest die USB-Geräte, wendet das Flugzeug-Profil an, schickt Events/Variablen an die Bridge |
| **`bridge.py`** (die „Bridge") | **im MSFS-Prefix (Proton/Wine)** | bindet `SimConnect.dll` und stellt sie der Linux-App über `127.0.0.1:7842` bereit |

Wichtig: Du startest die App **nie** über Wine. Die Bridge (Teil B, Schritt 9–10)
brauchst du **nur fürs echte Fliegen** — zum Einrichten, Anlernen und Testen von
Mappings reicht die App allein.

---

# Teil A · Schnellstart (4 Befehle)

Für dich, wenn du **kein Python/Linux** kannst und einfach ein paar Zeilen
einfügen willst. Danach läuft fast alles über **Knöpfe in der App**.

Ein „Terminal" ist ein Fenster, in das du Befehle einfügst (kopieren, dann mit
`Strg`+`Umschalt`+`V` einfügen, `Enter`):
- **Linux Mint / Ubuntu:** `Strg`+`Alt`+`T`
- **Fedora / GNOME:** `Super`-Taste (Windows-Taste) → `Terminal` tippen → Enter
- **CachyOS / KDE:** `Super` → `Konsole` tippen → Enter

**1. Zwei kleine Helfer installieren** (Zeile für deine Distribution):

```bash
sudo apt update && sudo apt install -y git curl      # Mint / Ubuntu
sudo dnf install -y git curl                          # Fedora
sudo pacman -S --needed git curl                      # Arch / CachyOS
```
> `sudo` fragt nach deinem **Passwort**. Während du tippst, bleibt der Bildschirm
> leer — das ist normal. Tippen, Enter.

**2. Programm laden und alles einrichten** (drei Zeilen zusammen einfügen):

```bash
git clone https://github.com/creativeSloth/msfs-peripherals-bridge.git
cd msfs-peripherals-bridge
./install.sh
```
Der Installer erledigt **alles**: er holt das passende Python, baut die Umgebung,
installiert alle Pakete und **schaltet deine Geräte frei**. Beim ersten Mal dauert
das ein paar Minuten und fragt einmal nach deinem Passwort.

**✓ Geschafft, wenn** am Ende ein grüner Kasten **„All set!"** erscheint.

**3. Programm starten:**

```bash
uv run python -m msfs_peripherals_bridge.gui
```

**✓ Geschafft, wenn** ein **Fenster mit mehreren Tabs** aufgeht. Stecke deine
Hardware an und bewege eine Achse / kippe einen Schalter — im **Mapper-Tab**
reagiert das Gerät (ein Balken füllt sich / ein Element leuchtet). **Einen
Simulator brauchst du dafür noch nicht.**

> **Tipp — App auf Deutsch/Englisch:** **Einstellungen** → **GUI-Sprache**. (Ein
> paar Mapper-Knöpfe bleiben deutsch; dieses Handbuch nennt die deutschen Labels.)

**Das war die komplette Einrichtung fürs Ausprobieren und Mappen.** Willst du im
**echten MSFS** fliegen, geht es in [Teil B, Schritt 9](#9-bridge-einrichten-nur-fürs-echte-fliegen) weiter.

Kommst du später in einem neuen Terminal zurück? Erst zurück in den Ordner:
`cd ~/msfs-peripherals-bridge`, dann die Befehle von oben.

---

# Teil B · Alles im Detail

Arbeite die Schritte **der Reihe nach** durch. Hast du **exakt meine Hardware**
(Fulcrum-Yoke, VirtualFly TQ6+, Saitek Panels/Pedale/Trimmrad), kannst du
Schritt 6 überspringen — Katalog und Freigabe-Regeln passen schon.

## 1. Terminal öffnen & Programm installieren

Terminal öffnen wie in [Teil A](#teil-a--schnellstart-4-befehle). Dann:

```bash
# git + curl (Zeile für deine Distribution, siehe Teil A)
git clone https://github.com/creativeSloth/msfs-peripherals-bridge.git
cd msfs-peripherals-bridge
./install.sh          # holt uv+Python, baut die venv, installiert Pakete, udev-Regeln
```

Lieber von Hand statt `install.sh`? [`uv`](https://docs.astral.sh/uv/) holt Python
(**≥ 3.11**) selbst:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # falls uv fehlt
uv sync --extra dev                                # venv + alle Pakete
uv run msfs-bridge validate                        # Katalog + Profile prüfen
```
> `$MSFS_BRIDGE_HOME` legt fest, aus welchem Ordner `profiles/` und `config/`
> geladen werden (Standard: dieser Ordner).

**✓ Checkpoint:** `uv run msfs-bridge validate` meldet Katalog + Profile **ohne
Fehler**; `uv run msfs-bridge list-profiles` zeigt mindestens ein Flugzeug.

## 2. Programm starten & Sprache

```bash
uv run python -m msfs_peripherals_bridge.gui
```
Sprache: **Einstellungen** → **GUI-Sprache**. Welche Tabs sichtbar sind, stellst
du unter **Einstellungen → „Angezeigte Tabs"** ein (der Instrumente-/Gauges-Tab
ist standardmäßig aus).

**✓ Checkpoint:** Das Fenster geht auf; im **Mapper-Tab** reagiert ein bewegter
Regler/Schalter live. (Simulator noch nicht nötig.)

## 3. Geräte für Linux freischalten (udev)

Damit dein normaler Benutzer die USB-/hidraw-Geräte öffnen darf — und die Panels
nicht als „Maus" erkannt werden (springender Mauszeiger) — braucht es einmalig
**udev-Regeln**.

**🖱 In der App:** **Verbindung**-Tab → **„Geräte freischalten…"**. Ein grafisches
Passwortfenster erscheint, die Regeln werden installiert. Danach das Gerät einmal
ab- und wieder anstecken.

**⌨ Im Terminal** (meine Hardware — Regeln einfach übernehmen):
```bash
sudo cp 999-flightsim-override.rules /etc/udev/rules.d/99-flightsim.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
# danach das Gerät einmal ab- und wieder anstecken
```

> **Distro-Hinweis (Mint/Ubuntu · Fedora · Arch/CachyOS):** udev ist überall
> gleich — Pfad `/etc/udev/rules.d/` und die `udevadm`-Befehle sind identisch. Der
> einzige Unterschied: `lsusb` steckt im Paket `usbutils` (ggf. per
> `apt`/`dnf`/`pacman` nachinstallieren).

**Eigene / unbekannte Hardware freischalten:** Erst die USB-Kennung finden, dann
die passende Vorlage in `/etc/udev/rules.d/99-flightsim.rules` eintragen:
```bash
lsusb        # Zeile deines Geräts: "ID 1234:5678 Hersteller Produkt"
```
- **Panel / Raw-HID** (Knöpfe, LEDs, Display):
  ```
  SUBSYSTEM=="hidraw", KERNEL=="hidraw*", ATTRS{idVendor}=="1234", MODE="0666", TAG+="uaccess"
  SUBSYSTEM=="input",  ATTRS{idVendor}=="1234", ATTRS{idProduct}=="5678", ENV{LIBINPUT_IGNORE_DEVICE}="1"
  ```
- **Achsen-Gerät** (Yoke, Schubquadrant, Pedale):
  ```
  SUBSYSTEM=="input", ATTRS{idVendor}=="1234", ATTRS{idProduct}=="5678", ENV{ID_INPUT_JOYSTICK}="1", MODE="0666", TAG+="uaccess"
  SUBSYSTEM=="input", ATTRS{idVendor}=="1234", ATTRS{idProduct}=="5678", KERNEL=="js*",    MODE="0666", TAG+="uaccess"
  SUBSYSTEM=="input", ATTRS{idVendor}=="1234", ATTRS{idProduct}=="5678", KERNEL=="event*", MODE="0666", TAG+="uaccess"
  ```
Dann `sudo udevadm control --reload-rules && sudo udevadm trigger` und neu anstecken.

**✓ Checkpoint:** `ls -l /dev/hidraw*` bzw. `/dev/input/js*` zeigt die Nodes mit
Schreib-/Leserecht (`rw`) für deinen Benutzer.

## 4. evdev oder hidraw? (der `transport`)

Jedes Gerät wird über **einen** von zwei Wegen gelesen — das ist der
`transport`. Du wählst ihn fast nie von Hand; die App erkennt ihn beim
Registrieren automatisch. Zum Verständnis:

| `transport` | Wofür | Typisch |
|---|---|---|
| **`evdev`** | **Achsen & Joystick-Buttons** — alles, was das System als Joystick/Gamepad sieht | Yoke, Schubquadrant (TQ6+), Pedale, Joysticks |
| **`hidraw`** | **Roh-HID-Panels** mit eigenen Report-Frames (Knöpfe **und** LEDs/Displays) | Saitek Switch/Multi/Radio-Panel |

Faustregel: **Hat es Anzeigen (LEDs/7-Segment) oder ist es ein Schalt-Panel →
`hidraw`. Sind es nur Achsen/Knöpfe wie an einem Joystick → `evdev`.** Im
Geräte-Explorer wird der erkannte Transport in der Spalte **„Transport"**
angezeigt; ein hidraw-Panel taucht dort nur **einmal** auf (sein evdev-„Schatten"
wird unterdrückt).

## 5. Meine Hardware: nichts weiter zu tun

Fulcrum-Yoke, TQ6+, Saitek Panels/Pedale/Trimmrad sind bereits im Katalog
(`config/devices.yaml`) und in den Freigabe-Regeln enthalten → **weiter mit
[Schritt 7](#7-mappen--testen-ohne-simulator)**.

## 6. Fremde Hardware einrichten (registrieren & anlernen)

Das läuft **komplett per Klick** — keine Dateien editieren, keine USB-Nummern
abtippen. Dahinter steckt eine saubere Trennung: **① Struktur** (welche
Knöpfe/Achsen/LEDs hat das Gerät — einmal pro Gerät) vs. **② Funktion** (was macht
ein Element in *diesem* Flugzeug — pro Profil, [Schritt 7](#7-mappen--testen-ohne-simulator)).
Die Systematik dahinter steht in [`geraete-workflow.md`](geraete-workflow.md).

**🖱 In der App** (Mapper-Tab; Labels teils deutsch):
1. **„🔍 Geräte-Explorer…"** → listet **alle** angesteckten Geräte, auch unbekannte.
   Deins markieren → **„Registrieren…"**, eine kurze **Id** vergeben (z. B.
   `mein_yoke` — Profile sprechen das Gerät über diese Id an). Das landet im
   **Benutzer-Overlay** `~/.config/msfs-peripherals-bridge/devices.local.yaml` —
   der mitgelieferte `config/devices.yaml` bleibt unangetastet.
2. Auf dem registrierten Gerät **„Geräteelemente…"** → **Eingaben (Lesen)** und
   **Anzeigen (Schreiben)** getrennt anlegen:
   - **„+ Input anlernen…"** (Taster/Schalter/Achse/Encoder): am Gerät betätigen →
     der Code wird **live erkannt** (Achsen erfassen dabei gleich ihren
     Rohbereich) → benennen.
   - **„+ Anzeige hinzufügen…"** (LED/Display): Name + Zellenzahl. Die genaue
     Hardware-Adresse (Byte/Bit) findet später der **🔦 Ausgang-Scan** (Schritt 7).
   - **„Aus Vorlage füllen…"** projiziert ein bekanntes Muster (Saitek/Yoke/TQ6)
     in einem Rutsch in die Element-Liste.

**⌨ Im Terminal** (nachsehen/prüfen):
```bash
uv run msfs-bridge inventory      # ALLE Geräte roh, auch unregistrierte
uv run msfs-bridge list-devices   # Katalog-Geräte, die gerade verbunden sind
uv run msfs-bridge monitor <id>   # Codes eines Geräts live mitlesen (wie evtest)
```
Von Hand ginge auch ein Eintrag in `config/devices.yaml` (`id`, `name`, `vendor`,
`product`, `transport`) — der GUI-Weg ist aber empfohlen.

**Ein Gerät wieder loswerden (deregistrieren/ausblenden):** Bekommst du fremde
Geräte in der Liste (z. B. die mitgelieferten Beispielgeräte), blende sie aus —
**nicht-destruktiv**, der Katalog und deine Profile bleiben unberührt:
- **🖱 App:** Mapper → **Rechtsklick** auf ein Gerät → **„Aus der Geräteliste
  entfernen…"**. Zurückholen über **Geräte-Explorer → „Ausgeblendete Geräte…"**.
- **⌨ Terminal:** `uv run msfs-bridge deregister-device <id>` (rückgängig:
  `--restore`, Liste: `--list`).

**✓ Checkpoint:** Das Gerät steht im Explorer als **registriert**, seine
Eingaben/Anzeigen sind als Elemente angelegt.

## 7. Mappen & testen (ohne Simulator)

Ab hier brauchst du **noch kein MSFS**. Im **Mapper-Tab**:

1. **Gerät links wählen** — der **Nachbau** zeigt Schalter/Achsen/Anzeigen an ihren
   Positionen. Mit **„✎ Anordnen"** ziehst du Elemente ins Raster (pro Gerät
   gespeichert).
2. **Eingaben mappen** — **„+ Eingabe"** (oder Klick auf ein Element) → Quelle über
   **„📋 Benannt"** aus den angelernten Eingaben wählen (statt roher Codes),
   Ziel-Event/-Variable über **„Wählen…"**, dann **„Übernehmen"**. Codes lassen sich
   im Editor jederzeit per **🪄 / 🎚 Anlernen** neu fangen.
3. **Anzeigen mappen** — **„+ Ausgabe ▾" → LED… / Display…**: eine Variable wählen
   und die Report-Adresse per **„🔦 Adresse finden…"** scannen (ein Testimpuls
   wandert durch, du bestätigst „das ist es!"). Danach treibt die App LEDs und
   7-Segment-Anzeigen direkt aus dem Sim.
4. Für die 3 Saitek-Panels gibt es zusätzlich **„Vorlage ▾"** — ein ganzes Panel in
   einem Rutsch; eigene Anordnungen kannst du als Vorlage speichern.

**Live-Test ohne Sim:** Achse bewegen / Schalter kippen → der Balken im Nachbau
füllt sich bzw. das Element glüht. Anzeigen gezielt testen mit **🔦 LEDs/Display
testen…**.

> **Nichts kaputtzumachen:** `tools/simulate-from-scratch.sh` startet eine
> isolierte Spielwiese (leerer Katalog + leeres Profil), in der du den ganzen
> „von null"-Ablauf gefahrlos üben kannst — deine echten Mappings bleiben unberührt.

**✓ Checkpoint:** Beim Betätigen der Hardware reagiert der Nachbau live, ein
angelernter Code landet im Editor, ein 🔦-Testimpuls leuchtet die richtige
LED/Zelle.

## 8. Profile: erstellen, übertragen, teilen

Ein **Profil** (`profiles/<flugzeug>.yaml`) hält das Mapping **für ein Flugzeug**.
Beim Fliegen wählt die App das Profil automatisch anhand von `aircraft_match`
(Teilstring des Flugzeug-Titels). Schema + kommentiertes Beispiel:
[`../profiles/_schema.md`](../profiles/_schema.md).

Es gibt **drei** Wege, Belegungen weiterzureichen — vom Kleinen zum Großen:

### a) Mappings eines Geräts in ein anderes Profil übertragen (auf demselben Rechner)
**🖱 App:** Mapper → **Rechtsklick** auf ein Gerät → **„Mappings in anderes Profil
übertragen…"** → Zielprofil wählen. Kopiert die Bindings + Anzeigen dieses Geräts.

### b) Geräte-Paket teilen (mit anderen Leuten) — *neu*
Ein **einzelnes Gerät als teilbare `.zip`** — enthält **Geräte-Definition +
Mapping + Knopf-Anordnung + Kalibrierung**. Ideal, um jemandem deine komplette
Einrichtung für ein Panel zu geben.

- **🖱 Exportieren:** Mapper → **Rechtsklick** auf das Gerät → **„Als Geräte-Paket
  exportieren…"** (nimmt das Mapping aus dem aktuell gewählten Profil).
- **🖱 Importieren:** Mapper → **„📥 Geräte-Paket importieren…"** → `.zip` wählen. Das
  Gerät wird registriert, Anordnung + Kalibrierung übernommen, das Mapping ins
  **aktuell gewählte Profil** geschrieben.
- **⌨ Terminal:**
  ```bash
  uv run msfs-bridge export-device <id> mein-panel.zip --profile piper_arrow
  uv run msfs-bridge import-device mein-panel.zip --profile piper_arrow
  ```
  (Beim Import ohne `--profile` wird nur das Mapping übersprungen; Gerät, Anordnung
  und Kalibrierung kommen trotzdem an.)

### c) Alles sichern & wiederherstellen (Rechnerwechsel, Backup)
Bündelt **alle** Profile, die Kalibrierung und alle GUI-Daten (Anordnung, eigene
Geräte, Vorlagen) in **eine** `.zip`.
- **🖱 App:** **Einstellungen → „Sichern & Wiederherstellen"** → **Exportieren…** /
  **Importieren…**.
- **⌨ Terminal:** `uv run msfs-bridge export-config backup.zip` bzw.
  `uv run msfs-bridge import-config backup.zip`.

**✓ Checkpoint:** Ein exportiertes Geräte-Paket lässt sich auf einem anderen Stand
importieren; das Gerät erscheint danach registriert und sein Mapping steht im
Zielprofil.

## 9. Bridge einrichten (nur fürs echte Fliegen)

**Voraussetzung:** MSFS 2020 ist über **Steam mit Proton** installiert und wurde
**mindestens einmal gestartet** (dieser erste Start legt die Umgebung an, die die
Bridge braucht; Proton Experimental empfohlen).

**🖱 In der App:** **Verbindung**-Tab. Dort gibt es eine **Checkliste** (Prefix,
Windows-Python, `SimConnect.dll`, Proton, Skripte — grün/rot):
1. Ist die **Prefix**-Zeile rot, finde den Pfad mit **einem** Terminal-Befehl:
   ```bash
   ./tools/find-prefix.sh
   ```
   Den ausgegebenen Ordner ins **„Prefix"**-Feld einfügen → **Speichern**.
2. **„Prefix einrichten…"** klicken (lädt Windows-Python + SimConnect in den
   Prefix — braucht Internet). Warten, bis fertig.
3. **„Erneut prüfen"**.

**⌨ Im Terminal** (dasselbe von Hand):
```bash
./bridge/setup-prefix.sh          # einmalig: Windows-Python + SimConnect in den Prefix
```

**Wo liegt dein Prefix? (Steam-Variante — wichtig, distro-unabhängig)** Die
Skripte suchen ihn unter `$STEAM_ROOT/steamapps/compatdata/1250410/pfx`. Passt der
Standard nicht, setze `STEAM_ROOT`:

| Steam-Variante | `STEAM_ROOT` |
|---|---|
| **Nativ, Standard** | *(nichts — `~/.steam/steam` passt)* |
| **Nativ, aber `.local/share`** | `~/.local/share/Steam` |
| **Flatpak-Steam** | `~/.var/app/com.valvesoftware.Steam/.local/share/Steam` |
| **Zweite Library / andere Platte** | am einfachsten `STEAM_COMPAT_DATA_PATH=<Library>/steamapps/compatdata/1250410` direkt setzen |

```bash
export STEAM_ROOT="$HOME/.var/app/com.valvesoftware.Steam/.local/share/Steam"  # Beispiel Flatpak
./bridge/setup-prefix.sh
```
`./tools/find-prefix.sh` sucht alle Varianten automatisch und druckt den fertigen
Pfad plus die passenden `export`-Zeilen. Weitere Variablen (Standard meist ok):
`MSFS_APPID` (Steam-MSFS `1250410`), `PROTON_NAME` / `PROTON_PATH`. Details:
[`../bridge/README.md`](../bridge/README.md).

**✓ Checkpoint:** Die Checkliste im Verbindung-Tab ist **komplett grün** (bzw.
`ls …/pfx/drive_c/pybridge` zeigt `pythonw.exe` + `SimConnect.dll`).

## 10. Fliegen

**🖱 In der App:** Alles vom **Verbindung**-Tab aus:
1. **MSFS starten und einen Flug laden** (bis du im Cockpit sitzt).
2. Im Tab **Start** für die **Bridge**, dann **Start** für den **Mapper** (Profil
   wählen, falls gefragt).

**⌨ Im Terminal** (aus dem Programmordner, zwei Terminals):
```bash
./bridge/run-bridge.sh                          # Bridge im Prefix starten
uv run msfs-bridge run --profile piper_arrow    # oder --aircraft "Piper Arrow"
```
> Port `7842` öffnet **erst nach** SimConnect — die Bridge braucht ein laufendes
> MSFS mit geladenem Flug. Prüfen: `ss -ltn | grep 7842`.

**✓ Checkpoint:** Achse bewegen / Schalter kippen → **es passiert im Simulator**.
Gegenprobe: `uv run msfs-bridge read "<SimVar>"` liest einen Wert zurück.

## 11. Alltag (Kurzform)

```bash
# MSFS + Flug laden, dann:
./bridge/run-bridge.sh
uv run msfs-bridge run --profile <profil>
# oder komplett aus der GUI (Verbindung-Tab: Bridge/Mapper starten/stoppen):
uv run python -m msfs_peripherals_bridge.gui
```

**Mapping live tunen (ohne Sim nötig):** `--dry-run -v` protokolliert jeden
Befehl, statt ihn zu senden — ideal zum Feinschliff:
```bash
uv run msfs-bridge run --profile piper_arrow --dry-run -v
```
Regler bewegen → du siehst Zeilen wie `SendEvent(name='AILERON_SET', data=-16383)`.
Profil in `profiles/<flugzeug>.yaml` anpassen (Deadzone, Kurve, `invert`,
`raw_min/max`, Event), `Strg`+`C`, neu starten — der Start ist sofort, die Schleife
also eng. Alle Befehle als Kopiervorlage: [`cheatsheet.md`](cheatsheet.md).

## 12. Problembehebung

- **`command not found: uv`** → Terminal schließen, neu öffnen, `cd ~/msfs-peripherals-bridge`, erneut versuchen.
- **„No such file or directory"** → du bist nicht im Programmordner: erst `cd ~/msfs-peripherals-bridge`.
- **Gerät reagiert nicht in der App** → Verbindung-Tab → **„Geräte freischalten…"**, dann Gerät ab-/anstecken.
- **Mauszeiger springt** beim Anstecken eines Panels → gleiche Lösung: **„Geräte freischalten…"** (die `LIBINPUT_IGNORE_DEVICE`-Regel fehlt).
- **„nicht live-lesbar" in der GUI** → hidraw-Node nicht `0666` (udev fehlt) oder Gerät nicht angesteckt.
- **Bridge verbindet nicht** → läuft MSFS wirklich **mit geladenem Flug**? Port offen? `ss -ltn | grep 7842`. Die Bridge ist **single-client** — kein zweiter Mapper gleichzeitig.
- **Panel testen/anlernen kollidiert** → der laufende Mapper „besitzt" das hidraw-Gerät; zum Testen/Anlernen den Mapper stoppen (Verbindung-Tab).
- **`L:`/`H:`/`B:`-Variablen tun nichts** → sie brauchen den MobiFlight-WASM-Kanal (noch offen); normale `A:`-Variablen und `K:`-Events funktionieren.

## 13. Wo liegen meine Daten?

| Ort | Was | Überlebt Neu-Clone? |
|---|---|---|
| **im Repo** | `profiles/*.yaml` (Mappings), `config/calibration.yaml` | ❌ (per git wiederherstellbar, wenn committet) |
| **`~/.config/msfs-peripherals-bridge/`** | `devices.local.yaml` (eigene Geräte), `panel-layouts.yaml` (Anordnung), `output-templates.yaml`, `gui-settings.json` | ✅ |

Das **Komplett-Backup** aus [Schritt 8c](#c-alles-sichern--wiederherstellen-rechnerwechsel-backup) deckt **beides** ab.

## 14. Weiterführend

- [`cheatsheet.md`](cheatsheet.md) — jeder Befehl als Kopiervorlage.
- [`simvars-reference.md`](simvars-reference.md) — SimVars/Events/LVars zum Mappen.
- [`bridge-concept.md`](bridge-concept.md) — wie die Bridge funktioniert (mit Diagrammen).
- [`geraete-workflow.md`](geraete-workflow.md) — die systematische Kette hinter der Geräte-Einrichtung.
- [`spadnext-import.md`](spadnext-import.md) — ein vorhandenes SPAD.neXt-Profil übernehmen.
- Alle Dokumente im Überblick: [`README.md`](README.md).
