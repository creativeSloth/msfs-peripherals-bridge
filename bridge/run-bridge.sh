#!/usr/bin/env bash
# Launch bridge.py inside the MSFS Proton/Wine prefix so it can link SimConnect.
#
# Run this AFTER MSFS is up (or it will retry-wait for SimConnect). It keeps
# running and listens on 127.0.0.1:7842 for the Linux app:
#     ./bridge/run-bridge.sh
#     uv run msfs-bridge run --profile piper_arrow
#
# One-time setup of the Windows Python + SimConnect lib: ./bridge/setup-prefix.sh
set -euo pipefail

# --- MSFS 2020 Steam layout (override via env if yours differs) -------------
APPID="${MSFS_APPID:-1250410}"
STEAM_ROOT="${STEAM_ROOT:-$HOME/.steam/steam}"
COMPAT_DATA="${STEAM_COMPAT_DATA_PATH:-$STEAM_ROOT/steamapps/compatdata/$APPID}"
PREFIX="$COMPAT_DATA/pfx"
# Windows Python installed into the prefix by setup-prefix.sh.
WIN_PYTHON="${WIN_PYTHON:-$PREFIX/drive_c/pybridge/python.exe}"

# Proton build to use — the prefix migrated to Proton Experimental.
PROTON_NAME="${PROTON_NAME:-Proton - Experimental}"
PROTON=""
for base in \
  "$STEAM_ROOT/steamapps/common" \
  "$HOME/.local/share/Steam/steamapps/common" \
  "$HOME/.steam/root/steamapps/common"; do
  if [[ -x "$base/$PROTON_NAME/proton" ]]; then
    PROTON="$base/$PROTON_NAME/proton"
    break
  fi
done
PROTON="${PROTON_PATH:-$PROTON}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRIDGE_PY="$SCRIPT_DIR/bridge.py"

# --- sanity checks ----------------------------------------------------------
[[ -d "$PREFIX" ]]      || { echo "✗ Prefix not found: $PREFIX" >&2; exit 1; }
[[ -n "$PROTON" ]]      || { echo "✗ Proton '$PROTON_NAME' not found. Set PROTON_PATH." >&2; exit 1; }
[[ -f "$WIN_PYTHON" ]]  || { echo "✗ Windows Python not found: $WIN_PYTHON. Run ./bridge/setup-prefix.sh first." >&2; exit 1; }

export STEAM_COMPAT_DATA_PATH="$COMPAT_DATA"
export STEAM_COMPAT_CLIENT_INSTALL_PATH="$STEAM_ROOT"
# Windows Python pipes its output through Wine, which block-buffers it so logs
# never appear; force unbuffered so bridge.py's logging shows up live.
export PYTHONUNBUFFERED=1

echo "→ Proton:  $PROTON"
echo "→ Prefix:  $PREFIX"
echo "→ Python:  $WIN_PYTHON"
echo "→ Bridge:  $BRIDGE_PY  (listening on 127.0.0.1:7842)"
exec "$PROTON" run "$WIN_PYTHON" "$BRIDGE_PY" "$@"
