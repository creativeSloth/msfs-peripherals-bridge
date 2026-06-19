# Sub-memory: SimConnect bridge

Parent: [../../MEMORY.md](../../MEMORY.md)
Spec/impl notes also in [../../bridge/README.md](../../bridge/README.md).

## Why a bridge
MSFS runs under Proton/Wine on Linux. `SimConnect.dll` only exists inside the
Wine prefix, so native Linux code can't link it. A tiny **Windows program runs
inside the same Wine prefix**, links SimConnect, and relays messages to/from the
Linux app over a local TCP socket.

## Wire protocol (implemented Linux side: simconnect/protocol.py)
Newline-delimited JSON on `127.0.0.1:7842`.
- Linux → bridge: `{"op":"event","name":"THROTTLE1_SET","data":8192}`,
  `{"op":"simvar","name":"L:Trim","unit":"number","value":0.5}`,
  `{"op":"subscribe","name":"TITLE","unit":"string"}`.
- bridge → Linux: `{"op":"state","name":"TITLE","value":"Cessna 172"}`.

## WASM requirement
Standard `K:` events + `A:` SimVars work via plain SimConnect. **`L:`/`H:`/`B:`
vars (add-on aircraft) require the MobiFlight WASM module** loaded in MSFS — the
bridge should route simvar/L-var ops through it. Mirrors how SPAD.neXt needs its
"L:Var bridge". See [../simvars-reference.md](../simvars-reference.md) §1.

## Status: NOT YET BUILT
The Linux client (`BridgeClient`) and protocol exist and are tested via
`--dry-run`. The Wine-side `bridge.exe` is the main remaining deliverable.
Options to evaluate: C++ SimConnect SDK app run under the same Proton prefix, or
a Python build under Wine. TCP keeps the choice open.
