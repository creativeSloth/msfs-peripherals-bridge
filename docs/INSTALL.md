# Installation & Einrichtung (von Grund auf)

Diese Anleitung führt einen **frischen Linux-Rechner** durch die komplette
Einrichtung: die native App, die udev-Regeln (inkl. **eigener Hardware**), das
Registrieren neuer Geräte und die Wine-seitige SimConnect-Bridge.

Kurzbefehle als Copy-&-Paste: [`cheatsheet.md`](cheatsheet.md).
Betriebs-/Iterationsguide: [`running.md`](running.md).

---

## 0. Was läuft wo? (zuerst lesen)

Es gibt **zwei** Prozesse, und nur einer berührt Wine:

| Prozess | Wo | Zweck |
|---|---|---|
| **`msfs-bridge`** (diese App) | **nativ auf Linux** (Python via `uv`) | liest die USB-Peripherie (evdev/hidraw), wendet das Profil an, schickt Events/SimVars an die Bridge |
| **`bridge.py`** | **im MSFS-Proton/Wine-Prefix** | linkt `SimConnect.dll` und reicht sie über TCP `127.0.0.1:7842` an die Linux-App |

Du startest `msfs-bridge` **nicht** über Wine. Die Bridge braucht man nur für
den echten Sim-Betrieb; zum Mappen/Testen reicht die native App (Dry-Run).

---

## 1. Systemvoraussetzungen

- **Linux** (getestet unter einem aktuellen Kernel; udev + `/dev/hidraw` nötig).
- **[`uv`](https://docs.astral.sh/uv/)** — zieht Python (**≥ 3.11**) und alle
  Abhängigkeiten selbst; ein manuelles venv ist nicht nötig.
- Für den **Sim-Betrieb**: **MSFS 2020 unter Steam+Proton** (Proton Experimental
  empfohlen) und Netzzugang für die einmalige Bridge-Einrichtung.

Python-Abhängigkeiten (von `uv` verwaltet): pydantic, pyyaml, typer, rich,
`evdev` (nur Linux), ruamel-yaml.

---

## 2. Native App installieren

```bash
# 1. uv installieren (falls noch nicht vorhanden)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Repo holen + Abhängigkeiten in ein lokales venv
git clone <repo-url> msfs-peripherals-bridge
cd msfs-peripherals-bridge
uv sync --extra dev

# 3. Prüfen, dass alles lädt
uv run msfs-bridge validate          # Katalog + Profile validieren
uv run msfs-bridge list-devices      # welche konfigurierten Geräte hängen dran?
uv run msfs-bridge list-profiles     # verfügbare Flugzeug-Profile
```

> `$MSFS_BRIDGE_HOME` überschreibt, aus welchem Verzeichnis `profiles/` und
> `config/` geladen werden (Default: der Repo-Checkout).

---

## 3. udev-Regeln — Geräte lesbar machen (einmalig, root)

Ohne udev-Regeln darf der normale User die USB-/hidraw-Knoten nicht öffnen, und
die Panels werden vom X-Server fälschlich als Maus erkannt.

```bash
sudo cp 999-flightsim-override.rules /etc/udev/rules.d/99-flightsim.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
# danach die Geräte einmal ab- und wieder anstecken
```

**Was die Regeln tun** (`999-flightsim-override.rules`):
- **hidraw-Knoten öffnen** (`MODE="0666"`, `TAG+="uaccess"`) für die Panel-Vendor
  (Saitek `06a3`, TQ6+ `16d0`, Yoke `0000`) — Pflicht für den HID-Zugriff.
- **Panels vom X-Server isolieren** (`LIBINPUT_IGNORE_DEVICE="1"`), sonst zappelt
  der Mauszeiger.
- **Achsen-Hardware als Joystick** markieren (`ID_INPUT_JOYSTICK`) + `js*`/`event*`
  lesbar machen.

### 3a. Eigene / unbekannte Hardware eintragen

Die mitgelieferten Regeln decken **nur meine Geräte** ab. Für andere Hardware:

```bash
lsusb        # Zeile deines Geräts finden: "ID 1234:5678 Hersteller Produkt"
```

Trage Vendor (`1234`) und Product (`5678`) in `99-flightsim.rules` ein — als
Vorlage die passende Sektion kopieren:

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

Danach `udevadm control --reload-rules && udevadm trigger` und neu einstecken.

---

## 4. Ein neues Gerät registrieren (Katalog)

Damit die App das Gerät kennt, muss es in **`config/devices.yaml`** stehen — die
`id` ist der stabile Schlüssel, auf den die Profile verweisen:

```yaml
devices:
  - id: mein_yoke            # frei wählbar, von Profilen referenziert
    name: Hersteller Produkt
    vendor: "1234"           # aus lsusb (hex)
    product: "5678"
    transport: evdev         # evdev = Achsen/Joystick · hidraw = Saitek-Panels
    # name_match: "Fulcrum"  # nur nötig, wenn die USB-ID mehrdeutig ist (0000:0000)
```

- `transport: evdev` für Yokes/Quadranten/Pedale (Achsen), `hidraw` für Raw-HID-
  Panels (Knöpfe/LEDs/Display).
- Danach `uv run msfs-bridge list-devices` — das Gerät sollte als *verbunden*
  erscheinen. Die **Codes** (Achsen/Knöpfe) findest du live mit `sudo evtest`
  oder direkt in der GUI per **🪄/🎚 Anlernen** (Mapper-Tab).

> Eine GUI zum Anlegen unbekannter Geräte ist geplant (Geräte-Explorer); aktuell
> ist der Katalog eine YAML-Datei.

---

## 5. Wine-seitige Bridge (nur für den echten Sim-Betrieb)

Voraussetzung: **MSFS unter Proton mindestens einmal gestartet**, damit das
Prefix existiert.

```bash
# einmalig: Windows-Python + SimConnect INS Prefix installieren (braucht Netz)
./bridge/setup-prefix.sh
```

Das lädt ein embeddable Windows-Python + `pip install SimConnect` (bündelt
`SimConnect.dll`, kein MSFS-SDK nötig) nach `…/pfx/drive_c/pybridge`.
Details: [`bridge/README.md`](../bridge/README.md).

Steuerbare Umgebungsvariablen (Defaults meist ok):
- `MSFS_APPID` (Default `1250410`, Steam-MSFS)
- `STEAM_ROOT` (Default `~/.steam/steam`)
- `STEAM_COMPAT_DATA_PATH` / `PROTON_PATH` bei abweichendem Steam-Library-Pfad.

Jede Session: MSFS starten, Flug laden, dann:
```bash
./bridge/run-bridge.sh                       # Bridge im Prefix starten
uv run msfs-bridge run --profile cessna_172  # oder --aircraft "Cessna 172 Skyhawk"
```
> Der Bridge-Port `7842` geht erst **nach** SimConnect auf — die Bridge braucht
> also ein laufendes MSFS.

---

## 6. GUI

```bash
uv run python -m msfs_peripherals_bridge.gui
```

Der **Connection-Tab** enthält eine **Voraussetzungs-Checkliste** (Prefix,
Windows-Python, `SimConnect.dll`, Proton, Skripte) und einen Knopf **„Prefix
einrichten…"**, der `setup-prefix.sh` mit Live-Log ausführt — Schritt 5 lässt
sich also auch aus der GUI erledigen. Prozesse (Bridge/Mapper) werden hier
gestartet/gestoppt; Sprache im **Settings-Tab** (DE/EN/ES/FR).

---

## 7. Troubleshooting

- **Gerät nicht erkannt** → `lsusb` prüfen, udev-Regel + `devices.yaml`-Eintrag
  vorhanden? `udevadm control --reload-rules && udevadm trigger`, neu einstecken.
- **„nicht live lesbar"** in der GUI → hidraw-Knoten nicht 0666 (udev), oder
  Gerät nicht angesteckt.
- **Mauszeiger zappelt** beim Panel → `LIBINPUT_IGNORE_DEVICE`-Zeile fehlt.
- **Bridge verbindet nicht** → MSFS läuft + Flug geladen? Port 7842 offen?
  `ss -ltn | grep 7842`. Die Bridge ist **single-client** — kein zweiter Mapper.
- **`L:`/`H:`/`B:`-Vars gehen nicht** → brauchen den MobiFlight-WASM-Kanal (noch
  offen); Standard-`A:`-Vars und `K:`-Events funktionieren.
- **Panel-Test/Anlernen kollidiert** → der Mapper besitzt das hidraw-Gerät; zum
  Testen/Anlernen den Mapper stoppen (Connection-Tab).

---

Verwandt: [`README.md`](../README.md) (Architektur), [`running.md`](running.md)
(nativ vs. Wine, live iterieren), [`cheatsheet.md`](cheatsheet.md) (alle Befehle).
