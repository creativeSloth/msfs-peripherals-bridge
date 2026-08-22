# Importing a SPAD.neXt profile (Stage 1: semantics)

If you already mapped an aircraft in **SPAD.neXt**, most of the hard thinking is
done: which knob changes which SimVar, which button fires which event, under
which conditions. `tools/spadnext_import.py` pulls that knowledge out of a
SPAD `.xml` profile and hands it to you in **our** naming conventions, so you
don't re-derive it by hand.

> **This is the low-risk half of a full importer, on purpose.** It extracts the
> *semantics* (what each control does), **not** finished bindings. See
> [Why not a full 1:1 importer?](#why-not-a-full-11-importer) below.

## TL;DR

```bash
# Markdown report to the terminal:
python tools/spadnext_import.py "/path/to/Arrow III.xml"

# Save the report, and also a machine-readable catalog:
python tools/spadnext_import.py "/path/to/Arrow III.xml" \
    -o arrow-import.md --json arrow-import.json
```

SPAD profiles live under your MSFS Proton prefix, e.g.
`~/Dokumente/SPAD.neXt/profiles/*.xml`. Point the tool at one of those.

## In the mapper (GUI)

You don't have to touch the command line. In the **Mapper** tab, the
**`SPAD.neXt…`** button (top-right) lets you pick a SPAD profile (`.xml`) — or a
catalog `.json` you saved with `--json`. The tool then harvests the distinct
**events and SimVars/LVars that aircraft actually uses** and drops them at the
**top of the variable picker**, so when you map a control you get that curated
shortlist above the 700+ generic names. You still point at the physical input
yourself; only the "what should it fire" is pre-filled.

The conversion (`gui_catalog.spad_catalog`) keeps only real variables: events
become `K:`, written vars become settable `A:`/`L:`/`V:`, and
`led`/`command`/`axis` actions are skipped. Entries are tagged `SPAD: <file>` so
you can tell them apart in the picker.

## What you get

A per-device, per-control catalog. Each row is one *(control × trigger)* pair —
the physical thing you'd move, and what SPAD made it do — translated to our
conventions. Example (Radio Panel, COM1 selector):

| Trigger | Input | Action(s) | When |
|---|---|---|---|
| `TUNER_INNER_CLOCKWISE` | encoder inner-cw | `COM STANDBY FREQUENCY:1 += 0.025` | V:RADIO_DIGIT_MODE == 0 |
| `ACTIVATESHORT` | button press | `event COM1_RADIO_SWAP` | |
| `LEFTDISPLAY` | leftdisplay | display `COM ACTIVE FREQUENCY:1` | V:RADIO_DIGIT_MODE == 0 |

The header of each device section tells you whether SPAD's device (matched by
USB **VendorID/ProductID** against `config/devices.yaml`) is one we already
know:

```
## 0x06a3:0x0d05 → our `radio_panel` (Saitek Pro Flight Radio Panel)
## 0x06a3:0x0bac → (no matching device in config/devices.yaml)
```

### Reading the columns

- **Trigger** — SPAD's verbatim trigger name (`ACTIVATESHORT`, `TUNER_*`, …).
- **Input** — our reading of what kind of physical action that is
  (`button press`, `encoder inner-cw`, `switch on @all`, …). This is a *hint*,
  not an evdev code — you still point at the real input in the mapper.
- **Action(s)** — the translated effect, one per SPAD `EventAction`:
  - `event NAME` — fire a key event (our `action: {type: event, event: NAME}`).
  - `set VAR = V` — write a value to a SimVar/LVar.
  - `VAR += V` / `VAR -= V` — relative change (⚠ see below).
  - `display VAR` / `led …` — an **output** (panel display / lamp).
  - `⚠ SPAD command NAME` / `⚠ axis …` — no clean equivalent (see below).
- **When** — SPAD `EventCondition`s, ANDed, in our `when:` form.

### The three row kinds

- **input** — the portable gold. A physical control → event/simvar with
  conditions. Drop these straight into the mapper's action picker.
- **output** — displays and lamps. The *semantics* (which var shows where) come
  through, but in our system outputs are wired via the panel controllers, not
  per-binding, so treat these as reference.
- **review** — a trigger we couldn't classify (rare — e.g. `GEAR_UP`). The
  Action column still tells you what it does; just decide the input yourself.

`⚠` marks an action with **no clean 1:1 equivalent**:

| ⚠ case | Why | What to do |
|---|---|---|
| `SPAD command` (e.g. `DIGITMARK`) | SPAD-internal display state machine | We implement the radio/multi panel display logic natively — ignore it. |
| `VAR += V` / `VAR -= V` | Relative change | Map to an INC/DEC key event, or a stepped SimVar write in the mapper. |
| `axis` | Axis range lives elsewhere in SPAD | Configure the axis range in our mapper directly. |

## How names are translated

SPAD namespaces → our subscription/event conventions:

| SPAD | Ours | Notes |
|---|---|---|
| `SIMCONNECT:NAME[:idx]` | `NAME[:idx]` | Bare SimVar or key event. |
| `MSFS:NAME[:idx]` | `NAME[:idx]` | Same. |
| `LVAR:NAME` | `L:NAME` | Aircraft L: variable. |
| `LOCAL:NAME` | `V:NAME` | **SPAD-internal** script var — no sim equivalent; you'll usually replace these with your own logic or drop them. |

Condition comparators: `Equals → ==`, `Unequal → !=`, `Less → <`,
`Greater → >`, `GreaterOrEqual → >=`, `LessOrEqual → <=`. `Always` and `Range`
are kept verbatim (no single-operator equivalent).

## Why not a full 1:1 importer?

SPAD identifies inputs by **symbolic HID channel names** derived from Windows
HID report descriptors — `TUNER_INNER_CLOCKWISE`, `ACTIVATESHORT`,
`SWITCH_MASTER_BAT`. Our profiles identify inputs by **raw Linux evdev/hidraw
codes** (`code: 288`). There is no automatic translation between the two: for a
generic yoke, "which SPAD channel equals which evdev code" simply isn't
derivable from the profile.

What *is* fully portable is the **semantics** — the SimVar/event/condition each
control drives. So Stage 1 extracts exactly that and leaves the "which physical
input" step to you (a human who can press the button), which is the safe,
reliable division of labour.

A **Stage 2** (full auto-binding) is feasible only for devices whose byte
layout we've already measured — the Saitek panels — via a per-model
channel-name → code table. That's device-specific and higher-maintenance, so
it's deliberately not built yet.

## Output for tooling

`--json` writes the same catalog as structured JSON
(`{source, devices:[{vendor, product, our_id, entries:[{control, trigger, kind,
hint, actions, when}]}]}`), ready to feed into the mapper's action picker or a
future Stage 2.
