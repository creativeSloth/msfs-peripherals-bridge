# Little Navmap im MSFS-Proton-Prefix (Linux)

Little Navmap **im selben Proton-Prefix wie MSFS 2020** installieren — dann erreicht
das gebündelte **Little Navconnect** SimConnect über die lokale Pipe, ganz ohne
Netzwerk-Setup. Getestet: Little Navmap 3.0.18 (win64), MSFS 2020 (Steam AppID
1250410), Proton Experimental.

Anders als SPAD.neXt ist LNM self-contained (Qt/C++): **kein .NET, keine
Windows-Version-Umstellung** nötig. Die `vcrun2022`-Laufzeiten sind durch SPAD schon
im Prefix. SimConnect erlaubt mehrere Clients gleichzeitig — Bridge, SPAD.neXt und
LNM laufen parallel.

```bash
PFX="$HOME/.steam/steam/steamapps/compatdata/1250410/pfx"
PROTON="$HOME/.steam/steam/steamapps/common/Proton - Experimental/proton"
SETUP="$HOME/Dokumente/Sicherungen/Flightsim/LittleNavmap/LittleNavmap-win64-3.0.18-Install.exe"
export STEAM_COMPAT_DATA_PATH="$HOME/.steam/steam/steamapps/compatdata/1250410"
export STEAM_COMPAT_CLIENT_INSTALL_PATH="$HOME/.steam/steam"
export DISPLAY=:0
```

## 1. Prefix sichern (MSFS + Steam vorher schließen, NICHTS parallel an den Prefix schreiben)

```bash
cd "$HOME/.steam/steam/steamapps/compatdata/1250410"
tar czf "$HOME/Dokumente/Sicherungen/Steam/MSFS2020_prefixes/msfs-pfx-backup-$(date +%Y%m%d-%H%M).tar.gz" pfx
```

> Während `tar` läuft, nichts in `pfx/` kopieren/ändern — sonst bricht es mit
> „Datei hat sich beim Lesen geändert" (exit 1) ab und das Archiv ist unbrauchbar.

## 2. Installer nach C: kopieren (Inno-Installer mag Z:/Leerzeichen-Pfade nicht)

```bash
cp "$SETUP" "$PFX/drive_c/lnm-setup.exe"
```

## 3. Still installieren (aus C:)

```bash
"$PROTON" run "C:\\lnm-setup.exe" \
  /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /NOICONS /LOG="C:\\lnm-install.log"

grep -a "Installation process succeeded" "$PFX/drive_c/lnm-install.log"
ls "$PFX/drive_c/Program Files/Little Navmap/littlenavmap.exe"
rm "$PFX/drive_c/lnm-setup.exe"
```

Die `Xalia ... TaskCanceledException` beim `proton run` ist nur der
Accessibility-Helfer — harmlos, exit code 0 zählt.

## 4. Starten

```bash
"$PROTON" run "C:\\Program Files\\Little Navmap\\littlenavmap.exe"
```

Erststart: Sprache/Region wählen, dann **Scenery Library laden**
(*Scenery Library → Load Scenery Library*) — LNM scannt die MSFS-Installation aus
dem Prefix. MSFS muss im Prefix mindestens einmal gelaufen sein, damit Pfade/Content
gefunden werden.

Verbindung zum Sim: *Connect* → **Connect directly to a local Flight Simulator**
(nutzt das gebündelte Little Navconnect über die lokale SimConnect-Pipe). Falls
stattdessen über Netzwerk: Little Navconnect separat starten und LNM auf
`localhost:51968` zeigen lassen.

## Fehlerbilder

| Symptom | Ursache / Fix |
|---|---|
| `tar: … hat sich beim Lesen geändert` (exit 1) | Parallelzugriff auf `pfx/` während Backup → Backup allein laufen lassen |
| `run_process Failed to create process … : 2` | Installer auf `Z:` mit Leerzeichen → erst nach `C:` kopieren |
| Scenery Library findet MSFS nicht | MSFS einmal im Prefix starten, dann erneut laden |
