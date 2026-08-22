#!/usr/bin/env bash
# Find the MSFS 2020 Proton/Wine "prefix" on THIS machine and print how to use it.
#
#     ./tools/find-prefix.sh
#
# The bridge needs to know where MSFS keeps its Windows environment (the
# "prefix"). Its location depends on how Steam is installed — this script checks
# every common place (native Steam, ~/.local/share, Flatpak Steam, a second
# drive) so you don't have to know any of that.
#
# It prints the folder to paste into the app's Connection tab ("Prefix" field),
# and the two lines to run in a terminal before ./bridge/setup-prefix.sh.
set -euo pipefail

APPID="${MSFS_APPID:-1250410}"   # MSFS 2020 on Steam

# The usual Steam roots, in order of likelihood.
roots=(
  "$HOME/.steam/steam"
  "$HOME/.steam/root"
  "$HOME/.local/share/Steam"
  "$HOME/.var/app/com.valvesoftware.Steam/.local/share/Steam"   # Flatpak Steam
)

found=""; steam_root=""
for r in "${roots[@]}"; do
  p="$r/steamapps/compatdata/$APPID/pfx"
  if [[ -d "$p/drive_c" ]]; then found="$p"; steam_root="$r"; break; fi
done

# Fallback: MSFS installed on another drive / a custom Steam library. Scan the
# home dir and the usual mount points (errors from missing dirs are ignored).
if [[ -z "$found" ]]; then
  while IFS= read -r p; do
    [[ -d "$p/drive_c" ]] || continue
    found="$p"
    steam_root="${p%/steamapps/compatdata/$APPID/pfx}"
    break
  done < <(find "$HOME" /media /mnt /run/media -maxdepth 8 -type d \
             -path "*steamapps/compatdata/$APPID/pfx" 2>/dev/null)
fi

if [[ -z "$found" ]]; then
  cat >&2 <<EOF
✗ No MSFS prefix found (AppID $APPID).

  Make sure MSFS 2020 is installed via Steam with Proton and was started at
  least once (that first launch is what creates the prefix).

  If it lives on an unusual location, try a full search (can take a while):
      find / -type d -path '*steamapps/compatdata/$APPID/pfx' 2>/dev/null
EOF
  exit 1
fi

compat_data="$(dirname "$found")"

cat <<EOF
✓ Found your MSFS prefix:
    $found

── In the app (easiest) ─────────────────────────────────────────
Open the Connection tab, paste this into the "Prefix" field, press Save:
    $found

── In a terminal (for setup-prefix.sh / run-bridge.sh) ──────────
Run these two lines first, then the bridge scripts in the SAME terminal:
    export STEAM_ROOT="$steam_root"
    export STEAM_COMPAT_DATA_PATH="$compat_data"
EOF
