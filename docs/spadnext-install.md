# SPAD.neXt im MSFS-Proton-Prefix (Linux)

SPAD.neXt im **selben Proton-Prefix wie MSFS 2020** installieren (SimConnect läuft
dann über die lokale Pipe, ohne Netzwerk-Setup). Getestet: SPAD.neXt 0.9.12.123,
MSFS 2020 (Steam AppID 1250410), Proton Experimental, Ubuntu wine 9.0 als Helfer.

Kernpunkte: **.NET 4.8 nur mit System-Wine installieren** (Protons wine 11 scheitert
an der Cabinet-Extraktion); SPAD-Installer **still über `proton run`** aus `C:`.

```bash
# Variablen für alle Schritte
PFX="$HOME/.steam/steam/steamapps/compatdata/1250410/pfx"
PROTON="$HOME/.steam/steam/steamapps/common/Proton - Experimental/proton"
SETUP="$HOME/Dokumente/Sicherungen/Flightsim/SPAD.neXt/SPAD.neXt.0.9.12.123.Setup.exe"
export STEAM_COMPAT_DATA_PATH="$HOME/.steam/steam/steamapps/compatdata/1250410"
export STEAM_COMPAT_CLIENT_INSTALL_PATH="$HOME/.steam/steam"
export DISPLAY=:0
```

## 1. Prefix sichern (MSFS + Steam vorher schließen)

```bash
tar czf ~/Dokumente/Sicherungen/msfs-pfx-backup-$(date +%Y%m%d-%H%M).tar.gz \
  -C "$HOME/.steam/steam/steamapps/compatdata/1250410" pfx
```

## 2. .NET 4.8 + gdiplus + vcrun2022 (System-Wine!)

```bash
env -u WINE -u WINESERVER -u WINEDLLOVERRIDES -u WINEDEBUG \
  WINEPREFIX="$PFX" /usr/bin/winetricks -q dotnet48 gdiplus vcrun2022
```

Prüfen (Release `0x80eb1` = 528049 = .NET 4.8, keine `FDICopy`-Fehler):

```bash
tail -4 "$PFX/winetricks.log"          # dotnet40 / dotnet48 / gdiplus / vcrun2022
ls "$PFX/drive_c/windows/Microsoft.NET/Framework64/v4.0.30319/clr.dll"
grep -ac '00080eb1' "$PFX/system.reg"  # > 0
```

## 3. Windows-Version zurück auf win10 (winetricks setzt sie auf win7 → MSFS startet sonst nicht!)

```bash
env -u WINE -u WINESERVER WINEPREFIX="$PFX" /usr/bin/winetricks -q win10
grep -aA6 'Windows NT\\\\CurrentVersion\]' "$PFX/system.reg" | grep -ai ProductName
# -> "Microsoft Windows 10"
```

## 4. SPAD.neXt installieren (still, aus C:)

```bash
cp "$SETUP" "$PFX/drive_c/spad-setup.exe"
"$PROTON" run "C:\\spad-setup.exe" \
  /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /NOICONS /LOG="C:\\spad-install.log"

grep -a "Installation process succeeded" "$PFX/drive_c/spad-install.log"
ls "$PFX/drive_c/Program Files/SPAD.neXt/SPAD.neXt.exe"
pkill -f vc_redist          # gebündelter vc_redist hängt ggf. – gefahrlos killen
rm "$PFX/drive_c/spad-setup.exe"
```

## 5. Starten

```bash
"$PROTON" run "C:\\Program Files\\SPAD.neXt\\SPAD.neXt.exe"
```

Erststart: Wizard → **Local PC** (findet MSFS-SimConnect automatisch).
Lizenz-/Versionsstatus prüfen:

```bash
LOG="$PFX/drive_c/users/steamuser/AppData/Roaming/SPAD.neXt/logs/spad.log"
grep -aE "START SPAD.neXt, Version=|: Licensed|Set ActiveProfile" "$LOG" | tail
```

## 6. Alte Profile importieren (SPAD vorher schließen)

Quelle und Ziel haben dieselbe Struktur (`profiles/`, `gauges/`, `scripts/`):

```bash
DST="$PFX/drive_c/users/steamuser/Documents/SPAD.neXt/profiles"
SRC="$HOME/Dokumente/Sicherungen/Flightsim/SPAD.neXt/profiles"
# nur benannte Profile, ohne __autosave/.bak/.zip:
for f in "$SRC"/*.xml; do [ "$(basename "$f")" = "__autosave.xml" ] || cp "$f" "$DST/"; done
```

## 7. Auf neueren Build aktualisieren

Der In-App-Updater klemmt unter Proton → Vollinstaller nutzen. **Lizenz-Obergrenze
beachten:** ohne aktive Update-Subscription bleibt die Lizenz nur bis zum letzten
abgedeckten Build (hier 0.9.12.x). Neuere Builds laufen sonst nur im Trial.
Verfügbare Archiv-Versionen: <https://www.spadnext.com/download-old-versions.html>

```bash
# Beispiel: Build laden, entpacken, wie Schritt 4 still installieren
curl -sL "https://www.spadnext.com/files/download/SPAD.neXt.0.9.12.123.Setup.zip" -o /tmp/spad.zip
unzip -o /tmp/spad.zip -d /tmp/spad && cp /tmp/spad/*.exe "$PFX/drive_c/spad-setup.exe"
"$PROTON" run "C:\\spad-setup.exe" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /NOICONS
```

Config/Profile/Aktivierung (in `AppData` + `Documents`) bleiben dabei erhalten.

## Fehlerbilder

| Symptom | Ursache / Fix |
|---|---|
| `FDICopy failed` / `netfx_core.mzz` / status 67 | dotnet48 mit Proton-Wine → **System-Wine** (Schritt 2) |
| MSFS startet nicht (.NET-Browser-Fehler `osver=5`) | Prefix steht auf win7/winxp → **win10 setzen** (Schritt 3) |
| `run_process Failed to create process … : 2` | Installer auf `Z:` mit Leerzeichen → erst nach `C:` kopieren |
| Installer „läuft", installiert aber nichts | `proton run` killt das Inno-Fenster → `/VERYSILENT` |
| `pkill -f "…"` bricht ab (exit 144) | Selbsttreffer – PID direkt killen oder `[b]racket`-Trick |
