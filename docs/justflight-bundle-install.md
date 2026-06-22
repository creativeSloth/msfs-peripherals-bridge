# Just-Flight-Bundles unter Linux installieren (persönliche Anleitung)

> Für Edgar / diese Maschine. Konkret am Beispiel **PA-28 Arrow Bundle**, gilt
> aber gleich für jedes andere Just-Flight-MSFS-Add-on (Turbo Arrow, etc.).

## Warum dieser Umweg?

Der Just-Flight-Installer aktiviert das Produkt online und schreibt dabei eine
Aktivierungsdatei **in das Paket selbst** (`ContentInfo/<paket>/userinfo.txt`).
Unter **Wine/Proton** schlägt diese Aktivierung fehl. Funktionierender Weg:

1. **Unter Windows** installieren **und aktivieren** → erzeugt die `userinfo.txt`.
2. Das fertig aktivierte Paket **nach Linux in den Community-Ordner kopieren**.

Die Lizenz „klebt" an den Paketdateien (das WASM-Modul liest `userinfo.txt` zur
Laufzeit), darum reicht reines Kopieren – kein erneutes Aktivieren unter Linux.

## Pfade auf dieser Maschine

| Was | Pfad |
|---|---|
| Windows-Partition (Dual-Boot), unter Linux gemountet | `/mnt/Doppelt_Spaß` |
| **Windows**-MSFS-Community (= `E:\Steam\…\community`) | `/mnt/Doppelt_Spaß/Steam/steamapps/common/MicrosoftFlightSimulator/community` |
| **Linux**-MSFS-Community (Zielordner) | `/home/familie/src/MSFS2020/Community` |
| Installer + Lizenzkey (heruntergeladen) | `/mnt/Doppelt_Spaß/Downloads/` |

Der Lizenzschlüssel liegt in `/mnt/Doppelt_Spaß/Downloads/key.txt`, der
JustFlight-Account/-Login in der erzeugten `userinfo.txt` (nicht hier im Repo
ablegen).

---

## Schritt 1 – Unter Windows installieren & aktivieren

1. Nach **Windows** booten.
2. Installer aus dem Downloads-Ordner ausführen, z. B.
   `Install_ArrowBundle_MSFS_0.6.3_TP.exe`.
3. Als Zielordner den **Steam-MSFS-Community-Ordner** wählen:
   `E:\Steam\steamapps\common\MicrosoftFlightSimulator\community`
   (das ist unter Linux `/mnt/Doppelt_Spaß/…/community`).
4. **Aktivieren** mit JustFlight-Login + Lizenzkey (`key.txt`).
   - Ergebnis-Check: im Paket muss
     `…/<paket>/ContentInfo/<paket>/userinfo.txt` existieren und **heute**
     geschrieben worden sein. Das ist der Aktivierungs-Beweis.
5. Zurück nach **Linux** booten.

## Schritt 2 – Aktiviertes Paket nach Linux kopieren

`<paket>` = Ordnername, z. B. `justflight-aircraft-pa28-arrow-bundle`.

```bash
PKG="justflight-aircraft-pa28-arrow-bundle"
SRC="/mnt/Doppelt_Spaß/Steam/steamapps/common/MicrosoftFlightSimulator/community/$PKG"
DST="/home/familie/src/MSFS2020/Community/"

rsync -a --info=progress2 "$SRC" "$DST"
```

`rsync -a` erhält Rechte/Zeitstempel und kopiert **inkl.**
`ContentInfo/$PKG/userinfo.txt` – das ist entscheidend, sonst ist die Maschine
unter Linux nicht aktiviert.

## Schritt 3 – Verifizieren

```bash
PKG="justflight-aircraft-pa28-arrow-bundle"
SRC="/mnt/Doppelt_Spaß/Steam/steamapps/common/MicrosoftFlightSimulator/community/$PKG"
DST="/home/familie/src/MSFS2020/Community/$PKG"

# gleiche Dateizahl?
echo "src: $(find "$SRC" -type f | wc -l)  dst: $(find "$DST" -type f | wc -l)"
# byte-identisch?
echo "src bytes: $(du -sb "$SRC" | cut -f1)"
echo "dst bytes: $(du -sb "$DST" | cut -f1)"
# Aktivierung vorhanden?
cat "$DST/ContentInfo/$PKG/userinfo.txt"
# Paket-Metadaten da?
ls "$DST/manifest.json" "$DST/layout.json"
```

Erwartet: gleiche Dateizahl, gleiche Bytezahl, `userinfo.txt` mit deinem
JustFlight-Account, `manifest.json` + `layout.json` vorhanden.

## Schritt 4 – Im Sim testen

MSFS (Proton) starten, Flieger laden. Wenn das Add-on **ohne**
„Demo/Trial/Nicht aktiviert"-Hinweis fliegt, hat die Aktivierung den Umzug
überlebt. (Erstmaliger In-Sim-Test steht für die Arrow noch aus.)

---

## Updates & weitere Bundles

- **Neue Version / Update:** unter Windows den neuen Installer laufen lassen,
  neu aktivieren (schreibt `userinfo.txt` neu), dann Schritt 2–3 wiederholen.
  `rsync -a` aktualisiert nur geänderte Dateien.
- **Anderes Just-Flight-Add-on:** identisch, nur `PKG` anpassen.

## Wenn's klemmt

- **„nicht aktiviert" im Sim:** prüfen, ob `ContentInfo/<paket>/userinfo.txt`
  im **Linux**-Paket liegt und nicht leer ist. Fehlt sie → unter Windows war
  die Aktivierung nicht erfolgreich, oder `rsync` lief auf den falschen
  Unterordner.
- **`Doppelt_Spaß` nicht gemountet:** `lsblk -o NAME,LABEL,MOUNTPOINT` und ggf.
  einhängen, bevor `rsync` läuft.
- **Add-on taucht in MSFS nicht auf:** liegt es wirklich direkt unter
  `…/Community/<paket>/` (mit `manifest.json` eine Ebene darunter)? MSFS einmal
  neu starten / Content-Manager prüfen.
- **`L:/H:/B:`-LVars des Add-ons reagieren in der Bridge nicht:** das ist eine
  separate Baustelle (MobiFlight-WASM-Kanal), siehe `bridge/README.md`.

## Hintergrund-Dateien (zur Orientierung)

- `ContentInfo/<paket>/userinfo.txt` – Account + Aktivierungs-Token (geheim).
- `ContentInfo/<paket>/productdata.txt` – Produkt-ID (`J3F000300`), Update-/
  Auth-URLs, der bei der Windows-Installation gewählte Zielpfad.
- `key.txt` (im Downloads-Ordner) – der eingekaufte Lizenzschlüssel.
