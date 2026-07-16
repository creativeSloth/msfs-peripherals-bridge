# Gauges-Tab — Design (aus den Air-Manager-Lua-Gauges extrahiert)

> Stand 2026-07-16, Vorbereitung für das eigene Feature (eigener Branch).
> Quelle: `reference/air-manager/instruments/*` (Autor „ES"), Analyse der
> `logic.lua`-Skalierungen. Ziel: die Gauges als **eigener GUI-Tab** mit frei
> auf Sim-Variablen mappbaren Zeigern, sauber in Python/Tk-Canvas portiert
> (der Lua-Code war Prototyp-Qualität — die *Parameter* sind das Wertvolle).

## Zeiger-Mathematik (aus den Luas)

Alle Gauges nutzen dieselbe Kern-Formel (0° = Norden, im Uhrzeigersinn):

```
winkel(v) = SWEEP / (v_max - v_min) * (v - v_min) + OMEGA          # linear
winkel(v) = (SWEEP/(v_max-v_min) * (v - v_min))^h + OMEGA          # Potenz-Skala (h≠1)
winkel(v) = interpolate(stützstellen, v)                           # frei (Fuel)
```

- `SWEEP` („ZWEI_PI" im Lua) = überstrichene Grad, `OMEGA` = Drehung der Skale.
- Ticks: Hauptstriche alle `MUV` Einheiten, Zwischenstriche (PHI2), Beschriftung
  auf Radius `R_Beschr`, Bögen (Arcs) als farbige Ringsegmente.
- Fuel nutzt `interpolate_linear(settings, v)` mit Glättung (`0.02`) —
  d. h. das System braucht **Stützstellen-Mapping + Zeiger-Smoothing**.

## Extrahierte Presets (JF Piper Arrow III Turbo)

| Gauge | Variable (Unit) | Bereich | SWEEP | OMEGA | Major | Arcs / Besonderes |
|---|---|---|---|---|---|---|
| MAP | `ENG MANIFOLD PRESSURE:1` (inHG) | 10…50 | 180° | −90° | 5 | grün 10…41; **2. Zeiger** Fuel Flow (eigene Skala, R kleiner, GPH — Subscription im Lua ab Z. ~179) |
| RPM | `GENERAL ENG RPM:1` (rpm) | 0…3500 | 290° | 215° | 500 | grün 500…2650 |
| Airspeed | `AIRSPEED INDICATED` (knots) | 20…190 | ~Vollkreis (360/(20·N)·Einheit) | −90 (impl.) | 20 | grün 65…100, gelb ab 100, „blau" 70…77 (Rotate-Band) |
| EGT | `GENERAL ENG EXHAUST GAS TEMPERATURE:1` (Fahrenheit) | 1200…1700 | 100°^(1/h), h=1 | −50° | 100 | grün 1200…1650; Potenz-Skala vorgesehen (h param.) |
| Fuel L/R | `FUEL LEFT/RIGHT QUANTITY` (Gallons) | 0…38.5 | 100° (h=1) | −50° | 10 | Stützstellen + Smoothing 0.02; Kombi-Gauge L/R+FuelPressure existiert |

## Architektur-Vorschlag

1. **`gauge_model.py`** (rein, testbar): `GaugeSpec` (name, var, unit,
   value_scale, v_min/v_max, sweep, omega, exponent h, major/minor, arcs
   [(von, bis, farbe)], stützstellen optional, fmt, smoothing) +
   `angle_for(spec, value)` + Tick-/Arc-Geometrie (reine Mathematik).
   Presets oben als Konstanten. **Mehrzeiger**: ein Gauge = Liste von
   Zeigern (je var+Skala) — MAP+FF ist der Beleg-Fall.
2. **GUI-Tab „Gauges"**: Canvas-Grid; „+ Gauge" → Preset wählen ODER
   „Eigenes…" (min/max/sweep) → **Variable über den Var-Picker mappen**
   (Kern-Wunsch: jede Zeigerfunktion frei auf eine auszulesende Sim-Var
   legbar). Rechtsklick entfernen. Persistenz in `gui-settings.json`
   (wie Statistik/Panel). Live-Werte über den bestehenden `_ValueMonitor`
   (Subscription = Statistik ∪ Panel ∪ Gauges).
3. Rendering pur mit `tk.Canvas` (Bogen `create_arc`, Striche `create_line`,
   Zeiger als Polygon, Rotation per Mathe — keine Bilddrehung nötig);
   die AM-Bilder (BG/needle/glass) bleiben Referenz-Optik, werden aber
   nicht 1:1 gebraucht.
4. Optional später: loslösbares Fenster wie das Kachel-Panel
   (`overrideredirect`-Erfahrung beachten: an/aus = erzeugen/zerstören).

## Lua-Review (Kurz-Befund „Code besser machen")

- Viel kopierte Trig-Blöcke (`sin/cos`-Paare je Radius) → in Python EINE
  `polar(cx, cy, r, deg)`-Helper-Funktion.
- Magic-Number-Korrekturen im MAP-Arc (`-0.2`, `50.2`, `-2*PHI1`) sind
  Pixel-Fummelei für Arc-Enden → im Port durch exakte Winkelrechnung ersetzen.
- EGT hat die Potenz-Skala vorbereitet (h), nutzt sie aber mit h=1 → als
  Feature übernehmen, Default linear.
- Airspeed-Formel weicht ab (eigene N-Herleitung, Start bei 20 kt) → im
  Modell einfach v_min=20 setzen, gleiche Kernformel.
