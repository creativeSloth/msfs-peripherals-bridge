# Sicherung der Geräte-Mappings — 2026-08-07

Vollständige Momentaufnahme aller Mapping-relevanten Dateien, **bevor** wir das
„Geräte bei null neu erkennen" durchspielen. Angst vor Datenverlust = unbegründet:
hier liegt alles doppelt, und die Profile sind zusätzlich in git eingecheckt.

## Was hier drin ist
- `profiles/` — alle Flugzeug-Profile (inkl. `piper_arrow.yaml` = deine
  Hauptbelegung, plus deine eigenen Kopien `_kopie`/`_sicherung`).
- `config/` — `devices.yaml` (Geräte-Katalog) + `calibration.yaml` (Achsen-Kalibrierung).
- `user-config/` — `devices.local.yaml` (User-Overlay, **nicht** in git!) +
  `gui-settings.json`.
- `device-functions.md` — **lesbarer Funktions-Report**: was jedes Gerät heute kann
  (Bindings, Anzeigen, atomare Elemente). Die Checkliste für einen Neuaufbau.
  Neu erzeugen: `uv run python tools/dump-device-functions.py --all > out.md`.

## Wiederherstellen (falls doch mal was schiefgeht)
```bash
# Profile + Katalog zurückspielen:
cp -a backups/2026-08-07/profiles/. profiles/
cp -a backups/2026-08-07/config/.   config/
# User-Overlay zurückspielen:
cp -a backups/2026-08-07/user-config/devices.local.yaml \
      ~/.config/msfs-peripherals-bridge/
```
Alternativ (nur die in git verfolgten Dateien): `git checkout -- profiles config`.

## Von null simulieren — ohne Risiko
`tools/simulate-from-scratch.sh` legt eine **Sandbox** an (leerer Katalog + leeres
Profil, eigenes Config-Verzeichnis) und startet das GUI dagegen. Der komplette
Ablauf (Explorer → registrieren → Ein-/Ausgänge scannen → mappen) läuft dort auf
Wegwerf-Dateien; deine echten Mappings werden dabei **nie geöffnet**.
