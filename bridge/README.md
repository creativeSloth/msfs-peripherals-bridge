# Wine-side SimConnect bridge

> Status: **first implementation** (`bridge.py`, Python-SimConnect under Wine).
> `event` (all K: events) works; `subscribe`/`state` polls TITLE for
> auto-profile; `simvar` covers writable `A:` vars (`L:/H:/B:` still need the
> MobiFlight WASM channel). **Not yet validated in-sim.** The Linux client and
> protocol live in `src/msfs_peripherals_bridge/simconnect/`.

## Purpose
MSFS runs under Proton/Wine, so `SimConnect.dll` lives inside the Wine prefix
and cannot be linked from native Linux. This small program runs **inside the
same Wine prefix as MSFS**, links SimConnect, and bridges it to the Linux app
over a local TCP socket.

```
Linux app  ──TCP 127.0.0.1:7842 (newline JSON)──►  bridge (Wine)  ──►  SimConnect  ──►  MSFS
                                               ◄── state frames ◄──
```

## Protocol
Exactly what `simconnect/protocol.py` emits/accepts:

| Direction | Frame |
|-----------|-------|
| Linux → bridge | `{"op":"event","name":"<K_EVENT>","data":<int>}` |
| Linux → bridge | `{"op":"simvar","name":"<A:/L: var>","unit":"<unit>","value":<num>}` |
| Linux → bridge | `{"op":"subscribe","name":"<simvar>","unit":"<unit>"}` |
| bridge → Linux | `{"op":"state","name":"<simvar>","value":<any>}` |
| bridge → Linux | `{"op":"hello","sim":"MSFS","version":"..."}` |

## SimConnect mapping
- `event`  → `SimConnect_MapClientEventToSimEvent` + `SimConnect_TransmitClientEvent`.
- `subscribe` → `SimConnect_AddToDataDefinition` + `SimConnect_RequestDataOnSimObject`
  (period = on change). Stream changes back as `state` frames (esp. `TITLE`).
- `simvar` (set) for **`L:`/`H:`/`B:` vars** → route through the **MobiFlight
  WASM module** (standard SimConnect can't set local vars). Plain writable `A:`
  SimVars can use `SimConnect_SetDataOnSimObject`.

## Implementation (chosen)
**Python + [Python-SimConnect](https://pypi.org/project/SimConnect/) under Wine.**
The pip package bundles `SimConnect.dll`, so no MSFS SDK or C++ toolchain is
needed. `bridge.py` runs under a Windows Python installed into the Proton prefix;
TCP/JSON keeps it decoupled from the Linux app. (A C++/MinGW `bridge.exe` was the
alternative — more robust but needs the SDK and a fiddly MinGW import lib.)

Files:
- `bridge.py` — the bridge itself (self-contained; copied into the prefix).
- `setup-prefix.sh` — one-time: installs Windows Python + SimConnect into the prefix.
- `run-bridge.sh` — launches `bridge.py` under Proton Experimental.

## Running
One-time setup (downloads Windows Python + SimConnect into the MSFS prefix):
```sh
./bridge/setup-prefix.sh
```
Each session — start MSFS, load a flight, then:
```sh
./bridge/run-bridge.sh                       # listens on 127.0.0.1:7842
uv run msfs-bridge run --profile piper_arrow  # in another terminal
```
The defaults assume MSFS 2020 Steam (AppID 1250410) under Proton Experimental;
override via `MSFS_APPID`, `STEAM_ROOT`, `PROTON_NAME`/`PROTON_PATH`, `WIN_PYTHON`.

`L:/H:/B:` add-on LVars additionally need the **MobiFlight WASM module** in the
MSFS Community folder (not yet routed by the bridge).

See [../docs/memory/simconnect-bridge.md](../docs/memory/simconnect-bridge.md).
