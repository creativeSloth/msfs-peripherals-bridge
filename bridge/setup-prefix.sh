#!/usr/bin/env bash
# One-time: install a Windows Python + the SimConnect package INTO the MSFS
# Proton prefix, so run-bridge.sh can launch bridge.py there.
#
# Uses the Windows embeddable Python zip (no installer GUI), enables pip, then
# `pip install SimConnect` (which bundles SimConnect.dll — no MSFS SDK needed).
#
#     ./bridge/setup-prefix.sh
#
# Network access is required (downloads Python + pip + SimConnect).
set -euo pipefail

PY_VERSION="${PY_VERSION:-3.11.9}"
APPID="${MSFS_APPID:-1250410}"
STEAM_ROOT="${STEAM_ROOT:-$HOME/.steam/steam}"
COMPAT_DATA="${STEAM_COMPAT_DATA_PATH:-$STEAM_ROOT/steamapps/compatdata/$APPID}"
PREFIX="$COMPAT_DATA/pfx"
DEST="$PREFIX/drive_c/pybridge"        # Linux path
DEST_WIN='C:\pybridge'                  # same dir, Windows path

PROTON_NAME="${PROTON_NAME:-Proton - Experimental}"
PROTON=""
for base in \
  "$STEAM_ROOT/steamapps/common" \
  "$HOME/.local/share/Steam/steamapps/common" \
  "$HOME/.steam/root/steamapps/common"; do
  [[ -x "$base/$PROTON_NAME/proton" ]] && { PROTON="$base/$PROTON_NAME/proton"; break; }
done
PROTON="${PROTON_PATH:-$PROTON}"

[[ -d "$PREFIX" ]] || { echo "✗ Prefix not found: $PREFIX (launch MSFS once first)." >&2; exit 1; }
[[ -n "$PROTON" ]] || { echo "✗ Proton '$PROTON_NAME' not found. Set PROTON_PATH." >&2; exit 1; }

export STEAM_COMPAT_DATA_PATH="$COMPAT_DATA"
export STEAM_COMPAT_CLIENT_INSTALL_PATH="$STEAM_ROOT"

run_in_prefix() { "$PROTON" run "$@"; }

echo "→ Installing Windows Python $PY_VERSION into $DEST"
mkdir -p "$DEST"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

zip="python-${PY_VERSION}-embed-amd64.zip"
curl -fL "https://www.python.org/ftp/python/${PY_VERSION}/${zip}" -o "$tmp/$zip"
unzip -oq "$tmp/$zip" -d "$DEST"

# The embeddable build disables site-packages by default; enable it so pip's
# installs are importable (uncomment "import site" in pythonXY._pth).
pth="$(find "$DEST" -maxdepth 1 -name 'python*._pth' | head -1)"
[[ -n "$pth" ]] && sed -i 's/^#import site/import site/' "$pth"

echo "→ Bootstrapping pip"
curl -fL "https://bootstrap.pypa.io/get-pip.py" -o "$DEST/get-pip.py"
run_in_prefix "$DEST_WIN\\python.exe" "$DEST_WIN\\get-pip.py"

echo "→ Installing SimConnect (bundles SimConnect.dll)"
run_in_prefix "$DEST_WIN\\python.exe" -m pip install --no-warn-script-location SimConnect

echo "✓ Done. Start the sim, then: ./bridge/run-bridge.sh"
