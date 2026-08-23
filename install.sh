#!/usr/bin/env bash
# One-shot installer for msfs-peripherals-bridge — made for people who are new to
# Linux and just want to copy-paste. Run it once after cloning the project:
#
#     ./install.sh
#
# It does everything the app needs, in order:
#   1. install a few base tools (curl, unzip, usbutils)  — asks for your password
#   2. install "uv"  — which also brings the correct Python (no Python knowledge needed)
#   3. create the virtual environment and install ALL packages  (uv sync)
#   4. install the device rules so Linux can read your panels/yoke (udev, needs sudo)
#
# It is safe to run again — every step just re-checks/repairs what's there.
set -euo pipefail

say()  { printf '\n\033[1;34m→ %s\033[0m\n' "$*"; }
ok()   { printf '\033[1;32m✓ %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m! %s\033[0m\n' "$*"; }
die()  { printf '\033[1;31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

# Work from the project folder no matter where the script was called from.
cd "$(dirname "$(readlink -f "$0")")"

# --- 1. base tools ---------------------------------------------------------
pkgs=(curl unzip)
command -v lsusb >/dev/null 2>&1 || pkgs+=(usbutils)

install_pkgs() {
  if   command -v apt-get >/dev/null 2>&1; then sudo apt-get update && sudo apt-get install -y "$@"
  elif command -v dnf     >/dev/null 2>&1; then sudo dnf install -y "$@"
  elif command -v pacman  >/dev/null 2>&1; then sudo pacman -S --needed --noconfirm "$@"
  else return 1; fi
}

say "Installing base tools (${pkgs[*]}) — you may be asked for your password"
if install_pkgs "${pkgs[@]}"; then
  ok "Base tools ready"
else
  warn "Could not auto-install base tools (unknown distribution or no network)."
  warn "Please install these yourself, then re-run: ${pkgs[*]}"
fi

# --- 2. uv (brings the right Python) ---------------------------------------
if ! command -v uv >/dev/null 2>&1; then
  say "Installing uv (this also provides Python — nothing else to install)"
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
# Make uv usable within THIS run, even right after installing it.
export PATH="$HOME/.local/bin:$PATH"
command -v uv >/dev/null 2>&1 \
  || die "uv is still not on the PATH. Close this terminal, open a new one, and run ./install.sh again."
ok "uv ready ($(uv --version 2>/dev/null || echo installed))"

# --- 3. virtual environment + all packages ---------------------------------
say "Creating the virtual environment and installing all packages (uv sync)"
uv sync --extra dev
ok "Environment ready (.venv)"

# --- 4. device rules (make panels/yoke readable) ---------------------------
RULE_SRC="999-flightsim-override.rules"
RULE_DST="/etc/udev/rules.d/99-flightsim.rules"
if [[ -f "$RULE_SRC" ]]; then
  say "Installing device rules so Linux can read your panels/yoke (needs your password)"
  sudo cp "$RULE_SRC" "$RULE_DST"
  sudo udevadm control --reload-rules && sudo udevadm trigger
  ok "Device rules installed — now unplug and replug your devices once"
else
  warn "$RULE_SRC not found — skipped device rules (you can install them later)"
fi

# --- done ------------------------------------------------------------------
cat <<'EOF'

──────────────────────────────────────────────────────────────
✓ All set!

  Start the program (graphical interface):

      uv run python -m msfs_peripherals_bridge.gui

  Want to fly in MSFS? Follow docs/HANDBUCH.md, Steps 9–10
  (set up the bridge, then fly).
──────────────────────────────────────────────────────────────
EOF
