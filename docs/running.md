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
| **`bridge.exe`** (SimConnect bridge) | **Inside the MSFS Proton/Wine prefix** | ⛔ **spec only, not built yet** |

> You do **not** start `msfs-bridge` through Wine or Proton. It reads the USB
> peripherals with native Linux `evdev` and sends commands over a local TCP
> socket (`127.0.0.1:7842`) to the Wine-side `bridge.exe`.
> — see [`README.md`](../README.md) and
> [`bridge/README.md`](../bridge/README.md).

**Consequence today:** because `bridge.exe` is not implemented yet
([`bridge/README.md`](../bridge/README.md) header: *"specification only — not yet
implemented. This is the main missing runtime piece"*), the app cannot actually
move anything in the sim. What you **can** do right now is run it in
**`--dry-run`** mode and watch the mapping resolve live (section 2). That is the
current feedback loop.

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

### Run it for real (once `bridge.exe` exists — not yet)
The app side is already wired for this; only the Wine bridge is missing.
`bridge.exe` must run **in the same Proton prefix _and_ with the same Proton
version as MSFS**, so it links the matching `SimConnect.dll` and Wine runtime.

**Find your MSFS prefix and Proton version** (MSFS 2020 = Steam AppID `1250410`;
MSFS 2024 = `2537590`):
```bash
APPID=1250410
PFX=~/.steam/steam/steamapps/compatdata/$APPID
# (a) which Proton last BUILT/RAN the prefix:
cat "$PFX/version"                       # e.g. GE-Proton10-28
# (b) which Proton Steam is SET to force right now (authoritative going forward):
grep -A3 "\"$APPID\"" ~/.steam/steam/config/config.vdf | grep -m1 name
#   -> "name" "proton_experimental"      # = Proton Experimental
```
> These two can disagree: the `version` file only changes when the game is next
> launched. On **this machine** Steam is set to **Proton Experimental** for MSFS,
> while the prefix still shows `GE-Proton10-28` from an earlier run — so the
> *effective* version after the next MSFS launch will be Experimental. Use
> whatever (b) reports.

**Launch the bridge in that environment.** Valve Proton's `proton run` needs the
compat env vars set (not just `WINEPREFIX`); the Proton script lives in the
tool's folder:
```bash
APPID=1250410
export STEAM_COMPAT_DATA_PATH=~/.steam/steam/steamapps/compatdata/$APPID
export STEAM_COMPAT_CLIENT_INSTALL_PATH=~/.steam/steam
# Proton Experimental (Valve): under steamapps/common
PROTON=~/.steam/steam/steamapps/common/"Proton - Experimental"/proton
# …or a GE build: PROTON=~/.steam/steam/compatibilitytools.d/GE-Proton10-28/proton
"$PROTON" run path/to/bridge.exe
```
(For a non-Steam/Lutris install, point the same env at that prefix instead.)

Then start the Linux app pointing at the bridge (defaults shown):
```bash
uv run msfs-bridge run --profile piper_arrow --host 127.0.0.1 --port 7842
```
Host/port default to `127.0.0.1:7842`
([`simconnect/client.py`](../src/msfs_peripherals_bridge/simconnect/client.py)).

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
- **Closed-loop with the sim** (move control → see the aircraft react, and read
  SimVars/`TITLE` back): this needs `bridge.exe`. The return channel already
  exists in the client (`BridgeClient.states()` streams `state` frames —
  [`simconnect/client.py`](../src/msfs_peripherals_bridge/simconnect/client.py),
  [`bridge/README.md`](../bridge/README.md)); it just has nothing to talk to yet.

---

## Sources / Quellen

- [`README.md`](../README.md) — architecture overview, native-Linux app + Wine
  bridge, data flow.
- [`bridge/README.md`](../bridge/README.md) — Wine bridge spec, **"not yet
  implemented"** status, intended `WINEPREFIX … proton run bridge.exe` launch,
  TCP/JSON protocol on `127.0.0.1:7842`.
- [`src/msfs_peripherals_bridge/cli.py`](../src/msfs_peripherals_bridge/cli.py)
  — `run` (`--profile`/`--aircraft`/`--dry-run`/`-v`/`--host`/`--port`),
  `monitor`, `snapshot`, profile resolution.
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
