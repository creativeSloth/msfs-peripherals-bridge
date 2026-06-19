# Wine-side SimConnect bridge

> Status: **specification only** — not yet implemented. This is the main missing
> runtime piece. The Linux client and protocol already exist
> (`src/msfs_peripherals_bridge/simconnect/`).

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

## Implementation options (to decide)
1. **C++** using the MSFS SimConnect SDK, compiled for Windows, run under the
   same Proton prefix. Most robust, matches SDK samples.
2. **Python under Wine** with a SimConnect ctypes wrapper (e.g. Python-SimConnect)
   — faster to prototype, heavier to deploy in the prefix.

TCP/JSON deliberately decouples this choice from the Linux app.

## Running (intended)
1. Install the MobiFlight WASM module into the MSFS Community folder.
2. Launch this bridge inside the Proton prefix that runs MSFS
   (`WINEPREFIX=… proton run bridge.exe`).
3. Start the Linux app: `uv run msfs-bridge run --aircraft "<title>"`.

See [../docs/memory/simconnect-bridge.md](../docs/memory/simconnect-bridge.md).
