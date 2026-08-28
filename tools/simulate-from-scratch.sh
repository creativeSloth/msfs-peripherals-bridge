#!/usr/bin/env bash
# Spin up an ISOLATED sandbox to rehearse "recognise devices from zero" without
# touching the real profiles, device catalog or user overlay.
#
# How it works: the app resolves its data dirs from two env vars —
#   MSFS_BRIDGE_HOME  -> repo root (profiles/, config/)
#   XDG_CONFIG_HOME   -> user config (devices.local.yaml overlay, gui-settings)
# Point both at a throwaway dir seeded with EMPTY catalog/profiles, and the whole
# from-scratch flow (explorer -> register -> scan inputs/displays -> map) runs on
# sandbox files. Your real mappings are never opened.
#
# Usage:
#   tools/simulate-from-scratch.sh          # create the sandbox, print launch cmd
#   tools/simulate-from-scratch.sh --launch # ... and launch the GUI in it
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
SANDBOX="${SANDBOX_DIR:-/tmp/msfs-bridge-sandbox}"

mkdir -p "$SANDBOX/profiles" "$SANDBOX/config" "$SANDBOX/xdg/msfs-peripherals-bridge"

# Empty catalog: nothing pre-known, so every connected device shows up in the
# explorer as UNREGISTERED and you register it by hand — the true zero state.
echo "devices: []" > "$SANDBOX/config/devices.yaml"
echo "devices: {}" > "$SANDBOX/config/calibration.yaml"
# A minimal empty profile to map into.
cat > "$SANDBOX/profiles/sandbox.yaml" <<'YAML'
name: sandbox
bindings: {}
outputs: {}
YAML
# No overlay/gui-settings: the app creates them fresh inside the sandbox XDG dir.

echo "Sandbox bereit: $SANDBOX"
echo "  profiles/sandbox.yaml (leer) · config/devices.yaml (leer) · eigenes XDG"
echo
LAUNCH="MSFS_BRIDGE_HOME=$SANDBOX XDG_CONFIG_HOME=$SANDBOX/xdg uv run python -m msfs_peripherals_bridge.gui"
echo "GUI in der Sandbox starten:"
echo "  $LAUNCH"
echo
echo "CLI inventory inside the sandbox (shows ALL plugged-in devices, raw):"
echo "  MSFS_BRIDGE_HOME=$SANDBOX XDG_CONFIG_HOME=$SANDBOX/xdg uv run msfs-bridge inventory"
echo
echo "Throw away: rm -rf $SANDBOX   (your real files stay untouched)"

if [[ "${1:-}" == "--launch" ]]; then
  echo; echo "Starte GUI…"
  cd "$REPO"
  MSFS_BRIDGE_HOME="$SANDBOX" XDG_CONFIG_HOME="$SANDBOX/xdg" \
    uv run python -m msfs_peripherals_bridge.gui
fi
