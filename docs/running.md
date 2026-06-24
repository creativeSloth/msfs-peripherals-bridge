# Running the bridge & working on mappings live

A practical guide to (1) starting the app — and where Wine/Proton does and does
**not** come in — and (2) iterating on a mapping with live feedback while the
simulator is running.

Sources are cited inline and collected at the bottom.

---

## 0. What runs where (read this first)

There are **two** processes, and only one of them touches Wine:

| Process | Where it runs | Status |
|---|---|---|
| **This app** (`msfs-bridge`) | **Natively on Linux** (Python via `uv`) | ✅ implemented |
| **`bridge.py`** (SimConnect bridge) | **Inside the MSFS Proton/Wine prefix** | ✅ **working in-sim** (axes + K: events; SimVar read via subscribe) |

> You do **not** start `msfs-bridge` through Wine or Proton. It reads the USB
> peripherals with native Linux `evdev` and sends commands over a local TCP
> socket (`127.0.0.1:7842`) to the Wine-side bridge (`bridge.py`, launched via
> `bridge/run-bridge.sh`). — see [`README.md`](../README.md) and
> [`bridge/README.md`](../bridge/README.md).

**Status today:** the full chain works in-sim. The Wine bridge
(`bridge/bridge.py`, Python-SimConnect) is set up in the MSFS prefix and
validated against MSFS — axes and K: events reach the sim and the per-aircraft
profiles fly real flights (Piper Arrow, Cessna 152/172). Reading SimVars back
(`msfs-bridge read`) goes through the subscribe/state channel. Still open:
`L:/H:/B:` add-on LVars need the MobiFlight WASM channel, and TITLE auto-profile
is not yet wired into `run`. The **dry-run loop** (section 2) stays the offline
way to tune a profile without the sim; section 1 is the real run.

> Looking for just the commands? [`cheatsheet.md`](cheatsheet.md) lists every one
> as a copy-paste line.

---

## 1. Starting the app

### One-time setup
```bash
uv sync --extra dev                      # install deps into .venv
# make the devices readable without root (one-time):
sudo cp 999-flightsim-override.rules /etc/udev/rules.d/99-flightsim.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
```

### Check everything is wired up
```bash
uv run msfs-bridge list-devices    # which catalog devices are connected now
uv run msfs-bridge list-profiles   # available aircraft profiles
uv run msfs-bridge validate        # catalog + profiles parse cleanly
```

### Run it (dry-run — works today, no sim/bridge needed)
```bash
# Pick a profile explicitly…
uv run msfs-bridge run --profile piper_arrow --dry-run -v
# …or select it by aircraft title (substring match against aircraft_match):
uv run msfs-bridge run --aircraft "Turbo Arrow III" --dry-run -v
```
`--profile` takes a file name (without `.yaml`) or a path; `--aircraft` matches
the string **you pass** against each profile's `aircraft_match` substrings
(`_resolve_profile` in [`cli.py`](../src/msfs_peripherals_bridge/cli.py)).

### Run it for real (Wine bridge — needs one-time setup first)
The app side is wired for this and the Wine bridge (`bridge/bridge.py`) now
exists. It must run **in the same Proton prefix _and_ with the same Proton
version as MSFS**, so it links the matching `SimConnect.dll` and Wine runtime.
The two helper scripts handle the env vars and Proton lookup for you — you do
**not** call `proton run` by hand.

**One-time:** install Windows Python + SimConnect into the MSFS prefix:
```bash
./bridge/setup-prefix.sh        # creates drive_c/pybridge/python.exe in the prefix
```

**Each session:** start MSFS, load a flight, then in two terminals:
```bash
./bridge/run-bridge.sh                          # Wine bridge, listens on 127.0.0.1:7842
uv run msfs-bridge run --profile piper_arrow     # Linux app, in another terminal
```
`run-bridge.sh` defaults to MSFS 2020 Steam (AppID `1250410`) under **Proton
Experimental** and finds the prefix at `~/.steam/steam/steamapps/compatdata/$APPID/pfx`.
Override via `MSFS_APPID`, `STEAM_ROOT`, `PROTON_NAME`/`PROTON_PATH`, `WIN_PYTHON`
if your layout differs.

**One-command launcher (this setup).** `~/.local/bin/msfs-bridge` wraps both halves
into a single command, consistent with the other cockpit launchers (`spadnext`,
`lnm`, `airm`): it starts the Wine bridge in the background **only if** `7842` isn't
already up, waits for the port, then runs the Linux mapper in the foreground.
```bash
msfs-bridge                 # default profile (piper_arrow)
msfs-bridge cessna_152      # override profile by name
```
Ctrl-C stops only the mapper; the SimConnect server stays up, so a repeat
`msfs-bridge` reattaches instantly. If `pybridge` is missing it runs
`setup-prefix.sh` once automatically.

**Which Proton is MSFS actually using?** (the script assumes Experimental):
```bash
APPID=1250410
cat ~/.steam/steam/steamapps/compatdata/$APPID/version            # what last RAN the prefix
grep -A3 "\"$APPID\"" ~/.steam/steam/config/config.vdf | grep -m1 name  # what Steam is SET to
```
> These two can disagree: the `version` file only changes when the game is next
> launched. If Steam is set to something other than Proton Experimental, pass it
> via `PROTON_NAME=...` (Valve builds) or `PROTON_PATH=...` (GE builds under
> `~/.steam/steam/compatibilitytools.d/`).

Host/port for the Linux app default to `127.0.0.1:7842`; override with `--host`/`--port`.
Equivalently:
```bash
uv run msfs-bridge run --profile piper_arrow --host 127.0.0.1 --port 7842
```
(Defaults from
[`simconnect/client.py`](../src/msfs_peripherals_bridge/simconnect/client.py).)

---

## 2. Working on a mapping with live feedback

The point of `--dry-run -v` is exactly this: **move a control, see the command it
produces, immediately.** It logs every resolved `SendEvent` / `SetSimVar` instead
of sending it (`DryRunDispatcher` in
[`simconnect/client.py`](../src/msfs_peripherals_bridge/simconnect/client.py),
selected by `--dry-run` in [`cli.py`](../src/msfs_peripherals_bridge/cli.py)).

```bash
uv run msfs-bridge run --profile piper_arrow --dry-run -v
```
Now wiggle the yoke / push a TQ6+ lever — you'll see lines like:
```
[dry-run] SendEvent(name='AILERON_SET', data=-16383)
[dry-run] SendEvent(name='THROTTLE1_SET', data=16383)
```
This is the loop for tuning a profile **while the sim runs**:

1. Keep `run --dry-run -v` going in one terminal and watch the output.
2. Edit `profiles/<aircraft>.yaml` (deadzone, curve, `invert`, `raw_min/max`,
   event name).
3. `Ctrl-C` and re-run — startup is instant, so the iteration is tight.
4. Confirm directions: full left stick → `AILERON_SET` near `-16383`; full
   forward lever → the inverted value you expect, etc.

### Two narrower tools for the same job

- **Raw hardware, no mapping** — confirm which code/axis a control is, or check
  centre/range:
  ```bash
  uv run msfs-bridge monitor <device>   # live evdev stream (like evtest)
  uv run msfs-bridge snapshot <device>  # one-shot current axis values
  ```
  (`monitor` / `snapshot` in [`cli.py`](../src/msfs_peripherals_bridge/cli.py).)
- **Closed-loop with the sim** — move a control → see the aircraft react, and
  read SimVars/`TITLE` back. With the Wine bridge up, read any SimVar:
  ```bash
  uv run msfs-bridge read "AUTOPILOT HEADING LOCK DIR" -u degrees   # one-shot
  uv run msfs-bridge read "AUTOPILOT HEADING LOCK DIR" -u degrees -w  # live
  ```
  It subscribes over `BridgeClient.states()` and prints the `state` frames the
  bridge streams back
  ([`simconnect/client.py`](../src/msfs_peripherals_bridge/simconnect/client.py),
  [`bridge/README.md`](../bridge/README.md)). Handy for putting the AP heading
  bug on a rocker switch.

---

## Sources / Quellen

- [`README.md`](../README.md) — architecture overview, native-Linux app + Wine
  bridge, data flow.
- [`bridge/README.md`](../bridge/README.md) — Wine bridge **first
  implementation** (`bridge.py`, Python-SimConnect), `setup-prefix.sh` /
  `run-bridge.sh` launch flow, TCP/JSON protocol on `127.0.0.1:7842`.
- [`src/msfs_peripherals_bridge/cli.py`](../src/msfs_peripherals_bridge/cli.py)
  — `run` (`--profile`/`--aircraft`/`--dry-run`/`-v`/`--host`/`--port`),
  `monitor`, `snapshot`, `calibrate`, `scan`, `read` (SimVar from the sim),
  profile resolution.
- [`src/msfs_peripherals_bridge/simconnect/client.py`](../src/msfs_peripherals_bridge/simconnect/client.py)
  — `DEFAULT_HOST`/`DEFAULT_PORT`, `DryRunDispatcher`, `BridgeClient.states()`.
- [`docs/memory/architecture.md`](memory/architecture.md),
  [`docs/memory/simconnect-bridge.md`](memory/simconnect-bridge.md) — component
  and bridge notes.
- External: [Astral `uv`](https://docs.astral.sh/uv/); Steam Proton prefixes live
  under `~/.steam/steam/steamapps/compatdata/<AppID>/pfx` (MSFS 2020 Steam AppID
  `1250410`, MSFS 2024 `2537590`). The forced Proton tool per game is recorded in
  `~/.steam/steam/config/config.vdf` under `CompatToolMapping`; the prefix's
  `version`/`config_info` files record the Proton that last ran it. Custom builds
  (GE-Proton etc.) install under `~/.steam/steam/compatibilitytools.d/`.
