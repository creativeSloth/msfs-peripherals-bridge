# Air-Manager-Gauges (Sicherung, 2026-07-16)

Selbst entwickelte Air-Manager-Instrumente/Panels für die **JF Piper Arrow III
(Turbo)** — gesichert von `/mnt/WinSys/Users/3441/Air Manager/` (altes
Windows-Benutzerprofil), bevor die Platte/Installation verschwindet. Ziel:
diese Anzeigen später evtl. in dieses Projekt integrieren.

Jedes Instrument ist ein Air-Manager-Ordner: `info.xml` (Metadaten),
`logic.lua` (die Gauge-Logik, teils „schlechter, aber cooler Code" mit
deutschen Kommentaren), `resources/` (Bilder), `preview.png`.

## instruments/ (Autor „ES")

| Ordner | Inhalt |
|---|---|
| `arrow-map-fuelconsumption__e8a9aa6d` | **Manifold Pressure + Fuel Consumption** — das parametrische Kreisskalen-Gauge (Skalen/Arcs komplett aus Parametern gerechnet) |
| `arrow-rpm__23196d1c` | Drehzahlmesser (RPM) |
| `arrow-egt__7ad11a48` | EGT |
| `arrow-airspeed__c5d2dcea` | Fahrtmesser |
| `arrow-fuel-left__6e2e08a3` | Tankanzeige links |
| `arrow-fuel-right__eaec1710` | Tankanzeige rechts |
| `arrow-fuel-lr-fuelpressure__f0d48168` | Tank links/rechts + Fuel Pressure kombiniert |
| `template-sicherung__0c43e4c7` | eigenes Gauge-Template („-- Sicherung") |
| `hintergrund-panel__2d9d75b9` | Panel-Hintergrund (großes Bild) |
| `unbenannt-leer__16a98697` | leeres/angefangenes Instrument |

## panels/

- `piper-arrow__286d0d9d` — das eigene „Piper / Arrow III (Turbo)"-Panel
  (Layout, das die Instrumente anordnet).

## dev-config/panels/

Die Air-Manager-Entwicklungs-Configs der Panels (JSON, Positionen/Properties).

> Quelle unverändert kopiert — Datei-Namen nur um lesbare Slugs ergänzt
> (`<slug>__<uuid-präfix>`); die UUIDs in `info.xml` sind unangetastet, die
> Ordner lassen sich also 1:1 nach Air Manager zurückkopieren.
