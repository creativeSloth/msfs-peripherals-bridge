#!/usr/bin/env bash
# Install the flight-sim udev rules. Must run as root — the GUI runs it via
# `pkexec` (graphical password prompt), or you can run it yourself:
#
#     sudo ./tools/install-udev-rules.sh
#
# It copies the shipped rule file into /etc/udev/rules.d and reloads udev, so
# your panels/yoke become readable for a normal user without a reboot.
set -euo pipefail

ROOT="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
SRC="$ROOT/999-flightsim-override.rules"
DST="/etc/udev/rules.d/99-flightsim.rules"

[[ -f "$SRC" ]] || { echo "✗ Rule file not found: $SRC" >&2; exit 1; }

install -m 0644 "$SRC" "$DST"
udevadm control --reload-rules
udevadm trigger

echo "✓ Installed device rules → $DST"
echo "→ Now unplug and replug your devices once."
