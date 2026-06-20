# msfs-peripherals-bridge

Map Linux USB flight-sim peripherals to **Microsoft Flight Simulator 2020**
SimVars and events — with **per-aircraft mapping profiles**.

MSFS runs under **Proton/Wine** on Linux. The peripherals (Fulcrum One yoke,
VirtualFly TQ6+, Saitek Cessna trim wheel, Saitek rudder pedals) are read
natively on Linux via `evdev`. Because `SimConnect.dll` only lives inside the
Wine prefix, a tiny **bridge process runs in Wine** and exposes SimConnect over
a local TCP socket. The Linux app reads the hardware, applies the active
aircraft profile, and streams the resulting events/SimVars to that bridge.

> Status: early scaffold. The mapping engine, profile system, transforms and
> CLI are implemented and tested. The Wine-side bridge is specified in
> [`bridge/README.md`](bridge/README.md) and is the main remaining piece.

---

## Why a bridge?

| Approach | SimVars/Events | Linux-native | Chosen |
|----------|:-------------:|:------------:|:------:|
| Virtual `uinput` joystick | ❌ axes/buttons only | ✅ | no |
| **SimConnect bridge in Wine** | ✅ full access | ⚠️ needs Wine helper | **yes** |

Joystick passthrough can't reach named SimVars or H-events, which is exactly
what differentiated per-aircraft mappings need — hence the bridge.

---

## Architecture

```mermaid
flowchart LR
    subgraph HW["USB hardware"]
        Y[Fulcrum One Yoke]
        T[VirtualFly TQ6+]
        W[Saitek Trim Wheel]
        P[Saitek Rudder Pedals]
    end

    subgraph LINUX["Linux app (this repo)"]
        EV["devices/evdev_reader<br/>raw events"]
        EN["mapping/engine<br/>+ transforms"]
        PR["profiles/*.yaml<br/>per-aircraft"]
        CL["simconnect/client<br/>TCP, JSON"]
        CLI["cli (typer)"]
    end

    subgraph WINE["Wine / Proton prefix"]
        BR["bridge.exe<br/>SimConnect SDK<br/>+ MobiFlight WASM"]
        MSFS["MSFS 2020"]
    end

    Y & T & W & P -->|evdev| EV
    EV -->|DeviceEvent| EN
    PR -.active profile.-> EN
    CLI -.controls.-> EN
    EN -->|Command| CL
    CL <-->|"127.0.0.1:7842<br/>newline JSON"| BR
    BR <-->|SimConnect| MSFS
    MSFS -.TITLE SimVar.-> BR -.auto-select.-> CL
```

<details>
<summary>ASCII fallback</summary>

```
 USB devices            Linux app (native)                  Wine/Proton prefix
 ───────────            ──────────────────                  ──────────────────
 Yoke   ┐                                                    ┌───────────────┐
 TQ6+   ├─ evdev ─▶ evdev_reader ─▶ mapping engine ─▶ bridge client
 Trim   │                 ▲              ▲                │  socket 7842   │
 Pedals ┘                 │         profiles/*.yaml       │  bridge.exe    │
                          │         (per aircraft)        │   │ SimConnect  │
                          └──── aircraft TITLE ◀──────────┤   ▼             │
                                  (auto-select)           │  MSFS 2020      │
                                                          └───────────────┘
```
</details>

### Data flow

1. `evdev_reader` discovers catalog devices (`config/devices.yaml`) by USB id
   and emits normalised `DeviceEvent`s (one thread per device).
2. `MappingEngine` looks up the bindings of the **active aircraft profile** for
   that device + control, shapes axis values (`deadzone → curve → invert →
   rescale`), and produces `SendEvent` / `SetSimVar` commands.
3. `BridgeClient` sends those commands as newline-delimited JSON to the Wine
   bridge, which calls the SimConnect SDK (and the MobiFlight WASM module for
   SimVars/H-events).
4. The bridge streams the aircraft `TITLE` SimVar back so the app can
   **auto-select** the matching profile.

---

## Quick start

```bash
# 1. Install uv (https://docs.astral.sh/uv/)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install deps into a local venv
uv sync --extra dev

# 3. Install the udev rules so the devices are readable (one-time)
sudo cp 999-flightsim-override.rules /etc/udev/rules.d/99-flightsim.rules
sudo udevadm control --reload-rules && sudo udevadm trigger

# 4. Explore
uv run msfs-bridge list-devices     # which configured devices are connected
uv run msfs-bridge list-profiles    # available aircraft profiles
uv run msfs-bridge validate         # check catalog + profiles

# 5. Try the mapping without a sim (logs commands instead of sending them)
uv run msfs-bridge run --profile cessna_172 --dry-run -v

# 6. Real run (needs the Wine bridge running, see bridge/README.md)
uv run msfs-bridge run --aircraft "Cessna 172 Skyhawk"
```

See [`docs/running.md`](docs/running.md) for a full run/iterate guide: what runs
natively vs. in Wine/Proton, finding your MSFS Proton prefix + version, and
tuning a mapping live with `--dry-run -v`.

---

## Configuration

- **`config/devices.yaml`** — the device catalog (USB vendor/product → stable
  `id`). The Fulcrum yoke id is still a placeholder; confirm it with `lsusb`.
- **`profiles/<aircraft>.yaml`** — one profile per aircraft. Schema and a fully
  commented example are in [`profiles/_schema.md`](profiles/_schema.md).
  Auto-selection matches `aircraft_match` substrings against the loaded
  aircraft's `TITLE`.

Finding the right axis/button codes for your hardware:

```bash
sudo apt install evtest && sudo evtest   # pick a device, wiggle a control
```

---

## Project layout

```
src/msfs_peripherals_bridge/
  models.py            Pydantic schema for devices, bindings, profiles
  config.py            path resolution (profiles/, config/)
  devices/             evdev discovery + normalised DeviceEvent
  mapping/             transforms, engine, YAML loader + profile selection
  simconnect/          bridge client + JSON wire protocol
  runtime.py           threaded glue: read → map → dispatch
  cli.py               `msfs-bridge` command (typer)
profiles/              per-aircraft YAML profiles
config/devices.yaml    device catalog
bridge/                Wine-side SimConnect bridge spec
tests/                 pytest suite (pure logic, no hardware needed)
docs/memory/           project knowledge base (see MEMORY.md)
```

---

## Development

```bash
uv run pytest          # tests
uv run ruff check .    # lint
uv run ruff format .   # format
uv run mypy            # type-check
```

CI (`.github/workflows/ci.yml`) runs lint, type-check and tests on every push
and pull request.

## Knowledge base

Project background, decisions and component notes live in
[`MEMORY.md`](MEMORY.md), which links to the sub-memories under
[`docs/memory/`](docs/memory/).

## License

MIT — see [LICENSE](LICENSE).
