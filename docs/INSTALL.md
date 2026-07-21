# Einrichtung — Schritt für Schritt (frischer Rechner)

Diese Anleitung bringt einen **frischen Linux-Rechner** von null auf ein
funktionierendes Setup: native App → Geräte lesbar machen → (eigene) Hardware
registrieren → mappen/testen → Wine-seitige SimConnect-Bridge → fliegen.

Arbeite die Schritte **der Reihe nach** ab. Jeder Schritt endet mit einem
**✓ Checkpoint** — läuft der durch, geht's weiter; sonst hilft die
[Fehlersuche](#8-fehlersuche) unten.

> **Zwei Nutzer-Typen:**
> - **Genau meine Hardware** (Fulcrum-Yoke, VirtualFly TQ6+, Saitek-Panels/
>   -Pedale/-Trimmrad) → **Schritt 3 überspringen**, die mitgelieferten Regeln
>   und der Katalog passen schon.
> - **Andere Hardware** → **Schritt 2b + 3** sind für dich Pflicht (Geräte
>   eintragen), der Rest ist identisch.

Kurzbefehle zum Kopieren: [`cheatsheet.md`](cheatsheet.md) ·
Betrieb/Iteration: [`running.md`](running.md).

---

## 0. Überblick: die zwei Prozesse

Es gibt **zwei** Programme, und nur **eines** berührt Wine:

| Prozess | Wo | Zweck |
|---|---|---|
| **`msfs-bridge`** (diese App) | **nativ auf Linux** (Python via `uv`) | liest die USB-Peripherie (evdev/hidraw), wendet das Flugzeug-Profil an, schickt Events/SimVars an die Bridge |
| **`bridge.py`** | **im MSFS-Proton/Wine-Prefix** | linkt `SimConnect.dll` und reicht sie über TCP `127.0.0.1:7842` an die Linux-App |

Wichtig: Du startest `msfs-bridge` **nicht** über Wine. Die Bridge (Schritt 5–6)
brauchst du **nur für den echten Sim-Betrieb** — zum Mappen/Anlernen/Testen
reicht die native App im Dry-Run (Schritt 4).

---

## 1. Native App installieren

**Voraussetzung:** Linux mit udev und `/dev/hidraw` (aktueller Kernel).
[`uv`](https://docs.astral.sh/uv/) zieht Python (**≥ 3.11**) und alle
Abhängigkeiten selbst — ein manuelles venv ist nicht nötig.

```bash
# 1. uv installieren (falls noch nicht vorhanden)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Repo holen + Abhängigkeiten in ein lokales venv
git clone <repo-url> msfs-peripherals-bridge
cd msfs-peripherals-bridge
uv sync --extra dev

# 3. Prüfen, dass alles lädt
uv run msfs-bridge validate       # Katalog + Profile validieren
uv run msfs-bridge list-profiles  # verfügbare Flugzeug-Profile
```

> `$MSFS_BRIDGE_HOME` überschreibt, aus welchem Verzeichnis `profiles/` und
> `config/` geladen werden (Default: der Repo-Checkout).

**✓ Checkpoint:** `validate` meldet den Katalog und die Profile **ohne Fehler**,
`list-profiles` listet mindestens ein Flugzeug (z. B. `piper_arrow`, `cessna_172`).

---

## 2. Geräte für Linux lesbar machen (udev, einmalig, root)

Ohne udev-Regeln darf dein normaler User die USB-/hidraw-Knoten nicht öffnen,
und die Panels werden vom X-Server fälschlich als Maus erkannt (Zeiger zappelt).

> **Distro-Hinweis (Mint/Ubuntu · Fedora · Arch/CachyOS):** udev funktioniert
> auf allen gleich — der Regel-Pfad `/etc/udev/rules.d/` und die Befehle
> `udevadm control --reload-rules` / `udevadm trigger` sind **identisch**, und
> `TAG+="uaccess"` (session-basierte Rechte) braucht nur systemd-logind, das auf
> allen vier Standard ist. Es gibt **keine** distro-spezifische Regel-Variante.
> Einziger Unterschied: `lsusb` kommt aus `usbutils` und ist ggf. nachzuinstallieren —
> Mint/Ubuntu `sudo apt install usbutils`, Fedora `sudo dnf install usbutils`,
> Arch/CachyOS `sudo pacman -S usbutils`. (Gruppen wie `input`/`plugdev` sind
> hier egal, weil die Regeln `MODE="0666"` setzen.)

### 2a. Meine Hardware — Regeln einfach übernehmen

```bash
sudo cp 999-flightsim-override.rules /etc/udev/rules.d/99-flightsim.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
# danach die Geräte einmal ab- und wieder anstecken
```

**Was die Regeln tun** (`999-flightsim-override.rules`):
- **hidraw-Knoten öffnen** (`MODE="0666"`, `TAG+="uaccess"`) für die
  Panel-Vendor (Saitek `06a3`, VirtualFly `16d0`, Fulcrum-Yoke `0000`) — Pflicht
  für den Raw-HID-Zugriff.
- **Panels vom X-Server isolieren** (`LIBINPUT_IGNORE_DEVICE="1"`), sonst zappelt
  der Mauszeiger.
- **Achsen-Hardware als Joystick** markieren (`ID_INPUT_JOYSTICK`) und
  `js*`/`event*` lesbar machen.

### 2b. Eigene / unbekannte Hardware eintragen

Die mitgelieferten Regeln decken **nur meine Geräte** ab. Für andere Hardware
zuerst die USB-IDs finden:

```bash
lsusb        # Zeile deines Geräts finden: "ID 1234:5678 Hersteller Produkt"
```

Trage Vendor (`1234`) und Product (`5678`) in `/etc/udev/rules.d/99-flightsim.rules`
ein — kopiere dazu die passende Vorlage:

- **Panel / Raw-HID** (Knöpfe, LEDs, Display):
  ```
  SUBSYSTEM=="hidraw", KERNEL=="hidraw*", ATTRS{idVendor}=="1234", MODE="0666", TAG+="uaccess"
  SUBSYSTEM=="input",  ATTRS{idVendor}=="1234", ATTRS{idProduct}=="5678", ENV{LIBINPUT_IGNORE_DEVICE}="1"
  ```
- **Achsen-Gerät** (Yoke, Quadrant, Pedale):
  ```
  SUBSYSTEM=="input", ATTRS{idVendor}=="1234", ATTRS{idProduct}=="5678", ENV{ID_INPUT_JOYSTICK}="1", MODE="0666", TAG+="uaccess"
  SUBSYSTEM=="input", ATTRS{idVendor}=="1234", ATTRS{idProduct}=="5678", KERNEL=="js*",    MODE="0666", TAG+="uaccess"
  SUBSYSTEM=="input", ATTRS{idVendor}=="1234", ATTRS{idProduct}=="5678", KERNEL=="event*", MODE="0666", TAG+="uaccess"
  ```

Danach die Regeln neu laden und das Gerät neu einstecken:

```bash
sudo udevadm control --reload-rules && sudo udevadm trigger
```

**✓ Checkpoint:** `ls -l /dev/hidraw*` (bzw. `/dev/input/js*`) zeigt die Knoten
mit Lese-/Schreibrecht für deinen User (`rw`), nachdem das Gerät steckt.

---

## 3. Neues Gerät registrieren (Katalog) — *nur bei anderer Hardware*

> Hast du **genau meine Hardware**, ist das schon in `config/devices.yaml`
> eingetragen → **weiter mit Schritt 4.**

Damit die App das Gerät kennt, muss es in **`config/devices.yaml`** stehen. Die
`id` ist der stabile Schlüssel, auf den die Profile verweisen:

```yaml
devices:
  - id: mein_yoke            # frei wählbar, von Profilen referenziert
    name: Hersteller Produkt
    vendor: "1234"           # aus lsusb (hex, ohne 0x)
    product: "5678"
    transport: evdev         # evdev = Achsen/Joystick · hidraw = Raw-HID-Panels
    # name_match: "Fulcrum"  # nur nötig, wenn die USB-ID mehrdeutig ist (z. B. 0000:0000)
```

- `transport: evdev` für Yokes/Quadranten/Pedale (Achsen), `hidraw` für Panels
  mit Knöpfen/LEDs/Display.
- `name_match` nur setzen, wenn mehrere Geräte dieselbe (oder eine generische)
  USB-ID melden — dann wird über den Produktnamen unterschieden.

Jetzt Gerät anstecken und prüfen:

```bash
uv run msfs-bridge list-devices   # welche Katalog-Geräte hängen dran?
```

Die **Codes** (Achsen-/Knopf-Nummern) findest du live per:

```bash
uv run msfs-bridge scan           # alle Achsen/Knöpfe/Hats je Gerät
uv run msfs-bridge monitor <id>   # wie evtest: Code beim Bewegen ablesen
```

…oder komfortabel direkt in der GUI über **🪄 / 🎚 Anlernen** (Schritt 4).

**✓ Checkpoint:** `list-devices` zeigt dein Gerät als **verbunden**.

> Eine GUI zum Anlegen unbekannter Geräte (Geräte-Explorer) ist geplant; aktuell
> ist der Katalog diese eine YAML-Datei.

---

## 4. Mappen & testen — ohne Sim (Dry-Run)

Ab hier brauchst du **noch kein MSFS**. Starte die GUI:

```bash
uv run python -m msfs_peripherals_bridge.gui
```

Im **Mapper-Tab**:
1. Gerät links auswählen — der **Nachbau** zeigt Schalter/Achsen/Displays an
   physischer Position (Umschalter „Tabelle ↔ Nachbau").
2. Ein Element anklicken → Editor öffnet sich.
3. **🪄 Anlernen** (Knopf/Schalter) bzw. **🎚 Anlernen** (Encoder/Selektor):
   am Gerät betätigen → der Code wird flanken-fangend erkannt und eingetragen.
4. Ziel-SimVar/Event über **„Wählen…"** setzen, **Übernehmen**.

**Live-Kontrolle ohne Sim:** Bewege eine Achse / kippe einen Schalter — der
Nachbau-Balken füllt sich bzw. das Element glüht. So siehst du sofort, ob das
Gerät gelesen wird.

> Panel-Ausgänge (LEDs/Display) lassen sich mit **🔦 LEDs/Display testen…**
> gezielt ansteuern, um zu sehen, welche Zelle welches Feld treibt.

**✓ Checkpoint:** Beim Betätigen der Hardware reagiert der Nachbau live, und ein
angelernter Code landet im Editor.

---

## 5. Wine-Bridge einrichten (nur für den echten Sim-Betrieb)

**Voraussetzung:** **MSFS unter Steam+Proton mindestens einmal gestartet**,
damit das Proton-Prefix existiert (Proton Experimental empfohlen).

Einmalig Windows-Python + SimConnect **ins Prefix** installieren (braucht Netz):

```bash
./bridge/setup-prefix.sh
```

Das lädt ein embeddable Windows-Python + `pip install SimConnect` (bündelt
`SimConnect.dll`, **kein MSFS-SDK nötig**) nach `…/pfx/drive_c/pybridge`.
Details: [`bridge/README.md`](../bridge/README.md).

### Wo liegt dein Prefix? (Steam-Variante — wichtig, distro-übergreifend)

`setup-prefix.sh`/`run-bridge.sh` bilden den Prefix als
`$STEAM_ROOT/steamapps/compatdata/$MSFS_APPID/pfx`. **Passt der Default nicht,
setzt du `STEAM_ROOT` (oder direkt `STEAM_COMPAT_DATA_PATH`) — das ist der
einzige distro-/setup-abhängige Teil.** Steam bestimmt den Pfad, nicht die
Distribution (Mint/Fedora/Arch/CachyOS sind gleich; es zählt **wie** Steam
installiert ist):

| Steam-Variante | `STEAM_ROOT` setzen auf |
|---|---|
| **Nativ, Default** (Arch/CachyOS/Fedora/Mint) | *(nichts — Default `~/.steam/steam` passt)* |
| **Nativ, aber `.local/share`** | `~/.local/share/Steam` |
| **Flatpak-Steam** (oft Mint/Fedora) | `~/.var/app/com.valvesoftware.Steam/.local/share/Steam` |
| **Zweite Library / andere Platte** | am einfachsten direkt `STEAM_COMPAT_DATA_PATH=<Library>/steamapps/compatdata/1250410` |

```bash
# Beispiel Flatpak-Steam:
export STEAM_ROOT="$HOME/.var/app/com.valvesoftware.Steam/.local/share/Steam"
./bridge/setup-prefix.sh          # nimmt jetzt den richtigen Prefix
```

> **Prefix schnell finden:** `find ~ -type d -path '*steamapps/compatdata/1250410/pfx' 2>/dev/null`
> — der Elternpfad bis `steamapps` ist dein `STEAM_ROOT`. In der GUI erledigt das
> das **Prefix-Feld** im Connection-Tab (persistiert, wird als
> `STEAM_COMPAT_DATA_PATH` an die Skripte injiziert).

Weitere steuerbare Variablen (Defaults meist ok):
- `MSFS_APPID` (Default `1250410`, Steam-MSFS)
- `PROTON_NAME` (Default `Proton - Experimental`) / `PROTON_PATH` (voller Pfad,
  falls Proton woanders liegt — z. B. Flatpak/zweite Library).

> **Bequemer aus der GUI:** Der **Connection-Tab** hat eine
> **Voraussetzungs-Checkliste** (Prefix, Windows-Python, `SimConnect.dll`,
> Proton, Skripte — grün/rot) und einen Knopf **„Prefix einrichten…"**, der
> `setup-prefix.sh` mit Live-Log ausführt. Schritt 5 geht also auch dort.

**✓ Checkpoint:** Die Checkliste im Connection-Tab ist **komplett grün** (bzw.
`ls …/pfx/drive_c/pybridge` zeigt `pythonw.exe` + `SimConnect.dll`).

---

## 6. Fliegen

Jede Session: **MSFS starten, Flug laden**, dann:

```bash
./bridge/run-bridge.sh                       # Bridge im Prefix starten
uv run msfs-bridge run --profile piper_arrow # oder --aircraft "Piper Arrow"
```

> Der Bridge-Port `7842` geht erst **nach** SimConnect auf — die Bridge braucht
> also ein laufendes MSFS mit geladenem Flug. Prüfen: `ss -ltn | grep 7842`.

**✓ Checkpoint:** Achse bewegen / Schalter kippen → die Aktion passiert im Sim.
`uv run msfs-bridge read "<SimVar>"` liest zur Kontrolle einen Wert zurück.

---

## 7. Alltag (Kurzform)

```bash
# MSFS + Flug laden, dann:
./bridge/run-bridge.sh
uv run msfs-bridge run --profile <profil>
# oder komplett aus der GUI (Connection-Tab: Bridge/Mapper starten/stoppen)
uv run python -m msfs_peripherals_bridge.gui
```

Iterations-Details (nativ vs. Wine, live nachjustieren): [`running.md`](running.md).

---

## 8. Fehlersuche

- **Gerät nicht erkannt** → `lsusb` prüfen; udev-Regel **und**
  `devices.yaml`-Eintrag vorhanden? `sudo udevadm control --reload-rules &&
  sudo udevadm trigger`, neu einstecken.
- **„nicht live lesbar" in der GUI** → hidraw-Knoten nicht `0666` (udev fehlt),
  oder Gerät nicht angesteckt.
- **Mauszeiger zappelt** beim Panel → `LIBINPUT_IGNORE_DEVICE`-Zeile fehlt in
  der udev-Regel.
- **Bridge verbindet nicht** → läuft MSFS **mit geladenem Flug**? Port offen?
  `ss -ltn | grep 7842`. Die Bridge ist **single-client** — kein zweiter Mapper
  gleichzeitig.
- **`L:`/`H:`/`B:`-Vars gehen nicht** → brauchen den MobiFlight-WASM-Kanal (noch
  offen); Standard-`A:`-Vars und `K:`-Events funktionieren.
- **Panel-Test/Anlernen kollidiert** → der laufende Mapper „besitzt" das
  hidraw-Gerät; zum Testen/Anlernen den Mapper stoppen (Connection-Tab).

---

Verwandt: [`README.md`](../README.md) (Architektur), [`running.md`](running.md)
(nativ vs. Wine, live iterieren), [`cheatsheet.md`](cheatsheet.md) (alle Befehle).
