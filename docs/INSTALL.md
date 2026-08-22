# Setup — Step by Step (fresh machine)

This guide takes a **fresh Linux machine** from zero to a working setup: native
app → make devices readable → register (your own) hardware → map/test →
Wine-side SimConnect bridge → fly.

Work through the steps **in order**. Each step ends with a **✓ Checkpoint** — if
it passes, move on; otherwise the [Troubleshooting](#8-troubleshooting) section
below helps.

> **Two kinds of user:**
> - **My exact hardware** (Fulcrum yoke, VirtualFly TQ6+, Saitek panels/
>   pedals/trim wheel) → **skip Step 3**; the bundled rules and catalog already fit.
> - **Other hardware** → **Steps 2b + 3** are mandatory for you (register the
>   devices); everything else is identical.

Copy-paste commands: [`cheatsheet.md`](cheatsheet.md) ·
Operating/iterating: [`running.md`](running.md). New or non-technical? The
one-command installer path is [`QUICKSTART.md`](QUICKSTART.md).

---

## 0. Overview: the two processes

There are **two** programs, and only **one** touches Wine:

| Process | Where | Purpose |
|---|---|---|
| **`msfs-bridge`** (this app) | **natively on Linux** (Python via `uv`) | reads the USB peripherals (evdev/hidraw), applies the aircraft profile, sends events/SimVars to the bridge |
| **`bridge.py`** | **inside the MSFS Proton/Wine prefix** | links `SimConnect.dll` and exposes it over TCP `127.0.0.1:7842` to the Linux app |

Important: you do **not** start `msfs-bridge` through Wine. You only need the
bridge (Steps 5–6) for **real sim operation** — for mapping/teaching/testing,
the native app in dry-run (Step 4) is enough.

---

## 1. Install the native app

**Requirement:** Linux with udev and `/dev/hidraw` (recent kernel).
[`uv`](https://docs.astral.sh/uv/) pulls Python (**≥ 3.11**) and all
dependencies itself — no manual venv needed.

```bash
# 1. Install uv (if not already present)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Get the repo + dependencies into a local venv
git clone https://github.com/creativeSloth/msfs-peripherals-bridge.git
cd msfs-peripherals-bridge
uv sync --extra dev

# 3. Check that everything loads
uv run msfs-bridge validate       # validate catalog + profiles
uv run msfs-bridge list-profiles  # available aircraft profiles
```

> `$MSFS_BRIDGE_HOME` overrides which directory `profiles/` and `config/` are
> loaded from (default: the repo checkout).

**✓ Checkpoint:** `validate` reports the catalog and profiles **without errors**,
and `list-profiles` lists at least one aircraft (e.g. `piper_arrow`, `cessna_172`).

---

## 2. Make devices readable for Linux (udev, one-time, root)

Without udev rules your normal user may not open the USB/hidraw nodes, and the
panels are wrongly detected as a mouse by the X server (pointer jumps).

> **Distro note (Mint/Ubuntu · Fedora · Arch/CachyOS):** udev works the same
> everywhere — the rule path `/etc/udev/rules.d/` and the commands
> `udevadm control --reload-rules` / `udevadm trigger` are **identical**, and
> `TAG+="uaccess"` (session-based permissions) only needs systemd-logind, which
> is the default on all four. There is **no** distro-specific rule variant. The
> only difference: `lsusb` comes from `usbutils` and may need installing —
> Mint/Ubuntu `sudo apt install usbutils`, Fedora `sudo dnf install usbutils`,
> Arch/CachyOS `sudo pacman -S usbutils`. (Groups like `input`/`plugdev` don't
> matter here, because the rules set `MODE="0666"`.)

### 2a. My hardware — just take the rules

```bash
sudo cp 999-flightsim-override.rules /etc/udev/rules.d/99-flightsim.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
# then unplug and replug the devices once
```

**What the rules do** (`999-flightsim-override.rules`):
- **Open hidraw nodes** (`MODE="0666"`, `TAG+="uaccess"`) for the panel vendors
  (Saitek `06a3`, VirtualFly `16d0`, Fulcrum yoke `0000`) — required for raw-HID
  access.
- **Isolate the panels from the X server** (`LIBINPUT_IGNORE_DEVICE="1"`),
  otherwise the mouse pointer jumps.
- **Mark axis hardware as a joystick** (`ID_INPUT_JOYSTICK`) and make
  `js*`/`event*` readable.

### 2b. Register your own / unknown hardware

The bundled rules cover **only my devices**. For other hardware, first find the
USB IDs:

```bash
lsusb        # find your device's line: "ID 1234:5678 Vendor Product"
```

Enter vendor (`1234`) and product (`5678`) into
`/etc/udev/rules.d/99-flightsim.rules` — copy the matching template:

- **Panel / raw-HID** (buttons, LEDs, display):
  ```
  SUBSYSTEM=="hidraw", KERNEL=="hidraw*", ATTRS{idVendor}=="1234", MODE="0666", TAG+="uaccess"
  SUBSYSTEM=="input",  ATTRS{idVendor}=="1234", ATTRS{idProduct}=="5678", ENV{LIBINPUT_IGNORE_DEVICE}="1"
  ```
- **Axis device** (yoke, quadrant, pedals):
  ```
  SUBSYSTEM=="input", ATTRS{idVendor}=="1234", ATTRS{idProduct}=="5678", ENV{ID_INPUT_JOYSTICK}="1", MODE="0666", TAG+="uaccess"
  SUBSYSTEM=="input", ATTRS{idVendor}=="1234", ATTRS{idProduct}=="5678", KERNEL=="js*",    MODE="0666", TAG+="uaccess"
  SUBSYSTEM=="input", ATTRS{idVendor}=="1234", ATTRS{idProduct}=="5678", KERNEL=="event*", MODE="0666", TAG+="uaccess"
  ```

Then reload the rules and replug the device:

```bash
sudo udevadm control --reload-rules && sudo udevadm trigger
```

**✓ Checkpoint:** `ls -l /dev/hidraw*` (or `/dev/input/js*`) shows the nodes with
read/write permission for your user (`rw`) once the device is plugged in.

---

## 3. Register a device + teach its building blocks — *only for other hardware*

> If you have **my exact hardware**, everything is already registered →
> **continue with Step 4.** For foreign devices this is the systematic "from
> scratch" chain (details: [`geraete-workflow.md`](geraete-workflow.md)):
> **detect → register → teach inputs/outputs → (calibrate) → map.** Two layers
> cleanly separated: *what the device physically has* (here) vs. *what it does in
> the aircraft* (Step 4).

### 3a. In the GUI (recommended) — Device Explorer

```bash
uv run python -m msfs_peripherals_bridge.gui
```

In the **Mapper tab** (button labels are quoted as they appear in the app —
German by default; an English gloss follows in parentheses):
1. **„🔍 Geräte-Explorer…"** (Device Explorer) → lists **all** connected
   evdev/hidraw devices, even unknown ones. Select yours → **„Registrieren…"**
   (Register) and give it a short id. This writes to the **user overlay**
   `~/.config/msfs-peripherals-bridge/devices.local.yaml` (the versioned
   `config/devices.yaml` stays untouched).
2. On the registered device, **„Geräteelemente…"** (Device elements) → create
   **inputs (read)** and **displays (write)** separately:
   - **„+ Input anlernen…"** (teach an input; button/switch/axis/encoder):
     actuate it on the device → the code is detected live (axes capture their raw
     range at the same time) → name it.
   - **„+ Anzeige hinzufügen…"** (add a display; LED/display): name + cell count.
     The **report address** (which byte/bit) is found by the **🔦 output scan** in
     the „+ Ausgabe" (+ Output) dialog (Step 4), or you enter it by hand.
   - **„Aus Vorlage füllen…"** (fill from template) projects a known pattern
     (Saitek/Yoke/TQ6) into the element list in one go.

### 3b. Alternatively, manually — `config/devices.yaml`

Find USB IDs with `lsusb`, then enter them (`id` = stable key for profiles):

```yaml
devices:
  - id: my_yoke             # free to choose, referenced by profiles
    name: Vendor Product
    vendor: "1234"          # from lsusb (hex, without 0x)
    product: "5678"
    transport: evdev        # evdev = axes/joystick · hidraw = raw-HID panels
    # name_match: "Fulcrum" # only needed if the USB id is ambiguous (e.g. 0000:0000)
```

Check (CLI): `uv run msfs-bridge list-devices` (catalog devices that are
connected) · `uv run msfs-bridge inventory` (**all** devices raw, incl.
unregistered) · `uv run msfs-bridge scan` / `monitor <id>` (read codes live).

**✓ Checkpoint:** The device shows as **registered** in the Device Explorer (or
`list-devices` shows it as **connected**), and its inputs/outputs are created as
elements.

---

## 4. Map & test — without a sim (dry-run)

From here you **don't need MSFS yet**. In the GUI (Mapper tab):

1. Select the device on the left — the **replica** shows switches/axes/displays
   at their physical positions. With **„✎ Anordnen"** (Arrange) you drag the
   elements into the grid (saved per device).
2. **Map inputs** — **„+ Eingabe"** (+ Input) (or click an element in the
   replica) → pick the source via **„📋 Benannt"** (Named) from the taught inputs
   (instead of raw codes), set the target SimVar/event via **„Wählen…"**
   (Choose…), then **„Übernehmen"** (Apply). Codes can be (re)taught afterwards
   via **🪄 / 🎚 Anlernen** (teach) in the editor.
3. **Map displays** — **„+ Ausgabe ▾" → LED… / Display…** (+ Output): pick a
   variable and scan the report address via **„🔦 Adresse finden…"** (find
   address) — a test pulse moves around and you confirm "that's it!". The
   **generic runtime** then drives LEDs (one bit) and 7-segment displays
   (var → cells) directly from the sim.
4. For the 3 Saitek panels there's also **„Vorlage ▾"** (Template) — a whole
   panel in one go; your own arrangements can be saved as a template.

**Live check without a sim:** move an axis / flip a switch — the replica bar
fills or the element glows. Panel outputs can be driven deliberately with
**🔦 LEDs/Display testen…** (test LEDs/display).

> **Nothing you can break:** `tools/simulate-from-scratch.sh` starts an isolated
> sandbox (empty catalog + empty profile) where you can safely rehearse the whole
> from-scratch flow — your real mappings are never touched.

**✓ Checkpoint:** When you actuate the hardware the replica reacts live, a taught
code lands in the editor, and a 🔦 test pulse lights the correct LED/cell.

---

## 5. Set up the Wine bridge (only for real sim operation)

**Requirement:** **MSFS started at least once under Steam+Proton**, so that the
Proton prefix exists (Proton Experimental recommended).

One-time, install Windows Python + SimConnect **into the prefix** (needs network):

```bash
./bridge/setup-prefix.sh
```

This downloads an embeddable Windows Python + `pip install SimConnect` (bundles
`SimConnect.dll`, **no MSFS SDK needed**) into `…/pfx/drive_c/pybridge`.
Details: [`bridge/README.md`](../bridge/README.md).

### Where is your prefix? (Steam variant — important, distro-independent)

`setup-prefix.sh`/`run-bridge.sh` build the prefix as
`$STEAM_ROOT/steamapps/compatdata/$MSFS_APPID/pfx`. **If the default doesn't fit,
set `STEAM_ROOT` (or `STEAM_COMPAT_DATA_PATH` directly) — that's the only
distro-/setup-dependent part.** Steam determines the path, not the distribution
(Mint/Fedora/Arch/CachyOS are the same; what matters is **how** Steam is
installed):

| Steam variant | Set `STEAM_ROOT` to |
|---|---|
| **Native, default** (Arch/CachyOS/Fedora/Mint) | *(nothing — default `~/.steam/steam` fits)* |
| **Native, but `.local/share`** | `~/.local/share/Steam` |
| **Flatpak Steam** (often Mint/Fedora) | `~/.var/app/com.valvesoftware.Steam/.local/share/Steam` |
| **Second library / other drive** | easiest to set `STEAM_COMPAT_DATA_PATH=<Library>/steamapps/compatdata/1250410` directly |

```bash
# Example: Flatpak Steam:
export STEAM_ROOT="$HOME/.var/app/com.valvesoftware.Steam/.local/share/Steam"
./bridge/setup-prefix.sh          # now uses the correct prefix
```

> **Find the prefix quickly:** run `./tools/find-prefix.sh` — it searches every
> Steam variant (native, `.local/share`, Flatpak, a second drive) and prints the
> ready-to-paste prefix path plus the `export` lines. Manually:
> `find ~ -type d -path '*steamapps/compatdata/1250410/pfx' 2>/dev/null` — the
> parent path up to `steamapps` is your `STEAM_ROOT`. In the GUI the **Prefix
> field** on the Connection tab does this (persisted, injected as
> `STEAM_COMPAT_DATA_PATH` into the scripts).

Other tunable variables (defaults usually fine):
- `MSFS_APPID` (default `1250410`, Steam MSFS)
- `PROTON_NAME` (default `Proton - Experimental`) / `PROTON_PATH` (full path, if
  Proton lives elsewhere — e.g. Flatpak/second library).

> **More convenient from the GUI:** The **Connection tab** has a **prerequisites
> checklist** (prefix, Windows Python, `SimConnect.dll`, Proton, scripts —
> green/red) and a **„Prefix einrichten…"** (Set up prefix…) button that runs
> `setup-prefix.sh` with a live log — so Step 5 can be done there too. The same
> tab also has an **„Geräte freischalten…"** (Enable devices…) button that
> installs the udev rules from Step 2 via a graphical password prompt.

**✓ Checkpoint:** The checklist on the Connection tab is **all green** (or
`ls …/pfx/drive_c/pybridge` shows `pythonw.exe` + `SimConnect.dll`).

---

## 6. Fly

Each session: **start MSFS, load a flight**, then:

```bash
./bridge/run-bridge.sh                       # start the bridge in the prefix
uv run msfs-bridge run --profile piper_arrow # or --aircraft "Piper Arrow"
```

> The bridge port `7842` only opens **after** SimConnect — so the bridge needs a
> running MSFS with a loaded flight. Check: `ss -ltn | grep 7842`.

**✓ Checkpoint:** move an axis / flip a switch → the action happens in the sim.
`uv run msfs-bridge read "<SimVar>"` reads a value back to verify.

---

## 7. Everyday (short form)

```bash
# Load MSFS + flight, then:
./bridge/run-bridge.sh
uv run msfs-bridge run --profile <profile>
# or entirely from the GUI (Connection tab: start/stop bridge/mapper)
uv run python -m msfs_peripherals_bridge.gui
```

Iteration details (native vs. Wine, live tuning): [`running.md`](running.md).

---

## 8. Troubleshooting

- **Device not detected** → check `lsusb`; is the udev rule **and** the
  `devices.yaml` entry present? `sudo udevadm control --reload-rules &&
  sudo udevadm trigger`, then replug.
- **"not live-readable" in the GUI** → hidraw node not `0666` (udev missing), or
  device not plugged in.
- **Mouse pointer jumps** with the panel → the `LIBINPUT_IGNORE_DEVICE` line is
  missing from the udev rule.
- **Bridge doesn't connect** → is MSFS running **with a loaded flight**? Port
  open? `ss -ltn | grep 7842`. The bridge is **single-client** — no second
  mapper at the same time.
- **`L:`/`H:`/`B:` vars don't work** → they need the MobiFlight WASM channel
  (still open); standard `A:` vars and `K:` events work.
- **Panel test/teach collides** → the running mapper "owns" the hidraw device;
  to test/teach, stop the mapper (Connection tab).

---

Related: [`README.md`](../README.md) (architecture), [`running.md`](running.md)
(native vs. Wine, live iterating), [`cheatsheet.md`](cheatsheet.md) (all commands).
