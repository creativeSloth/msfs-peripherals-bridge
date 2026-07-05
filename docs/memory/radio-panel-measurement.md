# Radio Panel — Mess-Session (Byte-Mapping verifizieren)

> Ziel: die **geratenen** Input-Bits + Output-Annahmen am echten Gerät
> (`06a3:0d05`, `/dev/hidraw5`) bestätigen und die Platzhalter im Profil ersetzen.
> **MSFS wird NICHT gebraucht** — beide Tools reden direkt mit `/dev/hidraw`.
> Rechte sind offen (`crw-rw-rw-`), **kein sudo**. Ergebnisse hier eintragen.

## ✅ ERGEBNIS PHASE 1 — INPUT gemessen 2026-07-05 (im Profil eingepflegt)
| Kontrolle | Bit(s) |
|---|---|
| Oberer Selektor COM1/COM2/NAV1/NAV2 | 0 / 1 / 2 / 3 (ADF/DME/XPDR 4/5/6) |
| Unterer Selektor COM1/COM2/NAV1/NAV2 | 7 / 8 / 9 / 10 (ADF/DME/XPDR 11/12/13) |
| ACT/STBY-Druck oben / unten (swap) | **14 / 15** |
| Oberer INNER enc cw/ccw | 16 / 17 |
| Oberer OUTER enc cw/ccw | **18 / 19** |
| Unterer INNER enc cw/ccw | 20 / 21 |
| Unterer OUTER enc cw/ccw | **22 / 23** |

Alle 24 Bit gehen auf. Selektoren + innere Encoder = wie Platzhalter; **äußere Encoder
+ Swaps korrigiert** (fett). `validate` + 125 Tests grün. Details: `radio-panel-hid.md`.

## ✅ ERGEBNIS PHASE 2 — OUTPUT/Display verifiziert 2026-07-05 (kein Code-Change nötig)
- **Zell-Order** bestätigt: `0–4`=oben-links (upper ACTIVE), `5–9`=oben-rechts (upper
  STANDBY), `10–14`=unten-links (lower ACTIVE), `15–19`=unten-rechts (lower STANDBY).
  Geometrie ist **links=ACTIVE / rechts=STANDBY pro Radio-Zeile** (nicht gestapelt).
- **Dezimalpunkt** `digit+0xD0` ✅ leuchtet korrekt (`118.00`).
- **Helligkeit**: `flags=0x00 0x00` → Display voll hell, kein Extra-Byte nötig.
- `render()`/`display.py` stimmen exakt → keine Anpassung.

**⏳ Bleibt: nur noch In-Sim** (Event-Namen `fract_fast_*` / COM-Swap am fliegenden Arrow).

## Vorbedingungen (schon geprüft)
- [x] Panel erkannt: `/dev/hidraw5` = „Saitek Pro Flight Radio Panel"
- [x] Kein Mapper/Bridge hält den Node (sonst würde er Scan-Events klauen)
- [x] Tools da: `tools/panel-scan/scan_radio.py` (Input) + `out_radio.py` (Output)
- Terminal im Repo-Root: `cd /home/familie/Dokumente/Projekte/msfs-peripherals-bridge`

---

## PHASE 1 — INPUT scannen (der wichtige Teil)

```bash
python3 tools/panel-scan/scan_radio.py
```
Läuft weiter und druckt pro Report-Änderung `hex[...]` + geänderte Bits
(`bit3↑` = gesetzt, `bit3↓` = gelöscht; Index = `byte*8+bit`). **Immer nur EIN
Bedienelement, langsam.** Ctrl-C beendet.

**Leseregeln:**
- **Selektor** (Drehschalter) = *Pegel*: beim Reindrehen geht 1 Bit ↑ und bleibt,
  beim Rausdrehen ↓. → notiere das Bit, das in **jeder** Stellung gesetzt ist.
- **Encoder** = *Puls*: pro Rastung 1 Bit ↑ dann ↓. Langsam einzeln drehen, sonst
  verschmelzen die Pulse. CW und CCW getrennt erfassen.
- **Encoder-Druck** (ACT/STBY) = ↑ beim Drücken, ↓ beim Loslassen.

### 1a) Oberer Mode-Selektor (7 Stellungen, one-hot) — nacheinander reindrehen
| Stellung | gesetztes Bit | → Profil-Feld |
|---|---|---|
| COM1 | `bit__` | `units[upper].banks` COM1 `code` |
| COM2 | `bit__` | COM2 `code` |
| NAV1 | `bit__` | NAV1 `code` |
| NAV2 | `bit__` | NAV2 `code` |
| ADF  | `bit__` | (out-of-scope, nur notieren) |
| DME  | `bit__` | (out-of-scope) |
| XPDR | `bit__` | (out-of-scope) |

### 1b) Unterer Mode-Selektor (7 Stellungen)
| Stellung | gesetztes Bit | → Profil-Feld |
|---|---|---|
| COM1 | `bit__` | `units[lower].banks` COM1 `code` |
| COM2 | `bit__` | COM2 `code` |
| NAV1 | `bit__` | NAV1 `code` |
| NAV2 | `bit__` | NAV2 `code` |
| ADF  | `bit__` | (out-of-scope) |
| DME  | `bit__` | (out-of-scope) |
| XPDR | `bit__` | (out-of-scope) |

### 1c) Encoder + Druck (je 1 Rastung / 1 Druck)
| Bedienung | Bit | → Profil-Feld |
|---|---|---|
| Oberer **äußerer** (groß) CW  | `bit__` | `units[upper].outer_cw` |
| Oberer äußerer CCW            | `bit__` | `units[upper].outer_ccw` |
| Oberer **innerer** (klein) CW | `bit__` | `units[upper].inner_cw` |
| Oberer innerer CCW           | `bit__` | `units[upper].inner_ccw` |
| Oberer Encoder **drücken**   | `bit__` | `units[upper].swap` |
| Unterer äußerer CW           | `bit__` | `units[lower].outer_cw` |
| Unterer äußerer CCW          | `bit__` | `units[lower].outer_ccw` |
| Unterer innerer CW           | `bit__` | `units[lower].inner_cw` |
| Unterer innerer CCW          | `bit__` | `units[lower].inner_ccw` |
| Unterer Encoder **drücken**  | `bit__` | `units[lower].swap` |

> **Struktur-Check (soll aufgehen):** 7+7 Selektor + 8 Encoder + 2 Druck = **24 Bit**
> (= 3 Byte). Falls ein Encoder statt eines Puls-Paars nur EIN Bit liefert oder ein
> Selektor mehrere Bits gleichzeitig setzt → hier vermerken, dann passen wir den
> Controller an.

---

## PHASE 2 — OUTPUT / Display verifizieren

Jeder Befehl schreibt direkt aufs Display (kein Sim). Ctrl-C bricht ab + löscht.

### 2a) Zell-Reihenfolge — die 20-Ziffern-Zuordnung
```bash
python3 tools/panel-scan/out_radio.py positions
```
Zeigt „8" nacheinander in Zell-Index 0..19 (2 s je). Trag ein, **wo** die 8 erscheint:
| Index | erwartet | tatsächlich (Display/Zeile/Spalte) |
|---|---|---|
| 0–4   | oberes Display, obere Zeile (upper ACTIVE)   | |
| 5–9   | oberes Display, untere Zeile (upper STANDBY)  | |
| 10–14 | unteres Display, obere Zeile (lower ACTIVE)   | |
| 15–19 | unteres Display, untere Zeile (lower STANDBY) | |

- [ ] Reihenfolge stimmt mit der Erwartung überein? Falls nicht: neue Zuordnung notieren.

### 2b) Ziffern-Glyphen
```bash
python3 tools/panel-scan/out_radio.py digits
```
Alle Zellen zeigen Wert 0..15. Bestätige: `0..9`=Ziffern, `0x0F`(15)=blank, `0xEE`=minus.
- [ ] 0–9 korrekt   - [ ] 15 = leer   - [ ] Minus ok

### 2c) **Dezimalpunkt** (die zentrale Chunk-A-Annahme `digit+0xD0`)
```bash
python3 tools/panel-scan/out_radio.py dot
```
Zeigt „8." in jeder Zelle. **Leuchtet ein Punkt rechts an der Ziffer?**
- [ ] Punkt erscheint mit `0xD0`  →  Annahme bestätigt (`display.py DOT` bleibt)
- [ ] KEIN Punkt / anders  →  echten Offset hier notieren: `______`

### 2d) Frequenz-Sanity
```bash
python3 tools/panel-scan/out_radio.py freq
```
Erwartung: oben `118.00`, darunter `118.30`. Liest es sich wie ein echtes Radio?
- [ ] ja   - [ ] nein → was steht da: `____________`

### 2e) **Flag-Bytes / Helligkeit** (byte 20/21) — wichtig!
```bash
python3 tools/panel-scan/out_radio.py flags
```
Schaltet nacheinander die Bits in Byte 20 und 21. **Achte auf jeden Effekt**
(Helligkeit, Display an/aus, Segment-Test). Der Controller schreibt aktuell `0x00`
— falls `0x00` = dunkel, brauchen wir hier einen Helligkeitswert.
| Byte.Bit | Effekt |
|---|---|
| 20.__ | |
| 21.__ | |
- [ ] Display ist mit Flags=`0x00` **hell genug** (dann nichts zu tun)
- [ ] Braucht Helligkeits-Bit: `byte__ bit__` → `_FLAG_BYTES` in `radio_panel.py` setzen

---

## PHASE 3 — Ergebnisse einpflegen (mache ich, sobald die Tabellen gefüllt sind)
1. **Profil** `profiles/piper_arrow.yaml` → gemessene Codes in den `radio_panel`-Block
   (die 8 Selektor-`code`s + 5 Encoder/Swap-Felder pro Unit) statt der Platzhalter.
2. Falls nötig: `display.py DOT`, `radio_panel.py _FLAG_BYTES`, Zell-Order in `render()`.
3. `docs/memory/radio-panel-hid.md` Input-Abschnitt mit den echten Bits füllen.
4. `uv run msfs-bridge validate` + `uv run pytest` → müssen grün bleiben.
5. Danach erst der **In-Sim-Teil** (Swap/WHOLE/FRACT-Events, `fract_fast_*` 8.33 vs 25 kHz).

## Bekannte Scope-Notiz (kein Bug)
Dreht man den Selektor auf **ADF/DME/XPDR** (nicht gemappt), ignoriert der Controller
das → die zuletzt gewählte COM/NAV-Bank bleibt aktiv (Display + Encoder tunen weiter
die alte Bank). Für „COM/NAV zuerst" ok; beim Testen nicht wundern.
