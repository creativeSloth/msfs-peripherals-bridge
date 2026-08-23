# User Manual — msfs-peripherals-bridge

The **one** document that takes you from zero to flying: install, set up devices,
map, share profiles, and the bridge to real MSFS. For **everyone** — no Python,
Linux or terminal experience required.

> **How to read this:**
> - Just get going? → **[Part A · Quick start](#part-a--quick-start)** (a handful of commands, then everything is buttons).
> - Full detail, your own hardware, real flying? → **[Part B](#part-b--the-full-guide)**.
> - **Every step** has a **🖱 in the app** *and* a **⌨ in the terminal** path — take whichever you prefer.
> - Green **✓** boxes tell you how to know a step worked.
> - The app's Mapper-tab buttons are German by default; this guide quotes the German label with an English gloss. Switch the app to English under **Settings → GUI language**.

---

## What this is

This program connects your **flight-sim hardware** (yoke, throttle, pedals,
switch panels …) on **Linux** to **Microsoft Flight Simulator 2020**. It reads
your devices, applies a **per-aircraft mapping** (which control does what) and
sends the result to the sim.

There are **two** programs — and only one runs in Wine:

| Program | Where it runs | Job |
|---|---|---|
| **`msfs-bridge`** (this app) | **natively on Linux** | reads the USB devices, applies the aircraft profile, sends events/variables to the bridge |
| **`bridge.py`** (the "bridge") | **inside the MSFS prefix (Proton/Wine)** | links `SimConnect.dll` and exposes it to the Linux app over `127.0.0.1:7842` |

Important: you **never** start the app through Wine. You only need the bridge
(Part B, steps 9–10) for **real flying** — setting up, teaching and testing
mappings works with the app alone.

---

# Part A · Quick start

For you if you **don't know Python/Linux** and just want to paste a few lines.
Afterwards almost everything runs via **buttons in the app**.

A "terminal" is a window you paste commands into (copy, then paste with
`Ctrl`+`Shift`+`V`, `Enter`):
- **Linux Mint / Ubuntu:** `Ctrl`+`Alt`+`T`
- **Fedora / GNOME:** `Super` key (Windows key) → type `Terminal` → Enter
- **CachyOS / KDE:** `Super` → type `Konsole` → Enter

**1. Install two small helpers** (the line for your distribution):

```bash
sudo apt update && sudo apt install -y git curl      # Mint / Ubuntu
sudo dnf install -y git curl                          # Fedora
sudo pacman -S --needed git curl                      # Arch / CachyOS
```
> `sudo` asks for your **password**. The screen stays blank while you type — that's
> normal. Type it, press Enter.

**2. Download the program and set everything up** (paste the three lines together):

```bash
git clone https://github.com/creativeSloth/msfs-peripherals-bridge.git
cd msfs-peripherals-bridge
./install.sh
```
The installer does **everything**: it fetches the right Python, builds the
environment, installs all packages and **unlocks your devices**. The first run
takes a few minutes and asks for your password once.

**✓ Worked if** a green **"All set!"** box appears at the end.

**3. Start the program:**

```bash
uv run python -m msfs_peripherals_bridge.gui
```

**✓ Worked if** a **window with several tabs** opens. Plug in your hardware and
move an axis / flip a switch — in the **Mapper tab** the device reacts (a bar
fills / an element lights up). **You don't need a simulator for this yet.**

> **Tip — language:** **Settings → GUI language**. (A few Mapper buttons stay
> German; this guide gives the German labels.)

**That's the whole setup for trying things out and mapping.** To fly in **real
MSFS**, continue at [Part B, step 9](#9-set-up-the-bridge-only-for-real-flying).

Coming back later in a new terminal? First go back into the folder:
`cd ~/msfs-peripherals-bridge`, then use the commands above.

---

# Part B · The full guide

Work through the steps **in order**. If you have **my exact hardware** (Fulcrum
yoke, VirtualFly TQ6+, Saitek panels/pedals/trim wheel), you can skip step 6 —
the catalog and unlock rules already fit.

## 1. Install

The standard path (git+curl → `git clone` → `./install.sh`) is in
[Part A](#part-a--quick-start); the script fetches uv+Python, builds
the venv and installs packages + udev rules.

Prefer to do it by hand? [`uv`](https://docs.astral.sh/uv/) fetches Python
(**≥ 3.11**) itself:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # if uv is missing
uv sync --extra dev                                # venv + all packages
uv run msfs-bridge validate                        # check catalog + profiles
```
> `$MSFS_BRIDGE_HOME` sets which folder `profiles/`/`config/` load from.

**✓ Checkpoint:** `validate` reports catalog + profiles **without errors**;
`list-profiles` lists at least one aircraft.

## 2. Start the app & language

```bash
uv run python -m msfs_peripherals_bridge.gui
```
Language: **Settings → GUI language**. Which tabs are visible is set under
**Settings → "Shown tabs"** (the Instruments/Gauges tab is off by default).

**✓ Checkpoint:** the window opens; in the **Mapper tab** a moved control/switch
reacts live. (No simulator needed yet.)

## 3. Make devices readable for Linux (udev)

So your normal user may open the USB/hidraw nodes — and the panels aren't
mistaken for a "mouse" (jumping pointer) — you need **udev rules** once.

**🖱 In the app:** **Connection tab → "Enable devices…"**. A graphical password
prompt appears and the rules are installed. Then unplug/replug the device once.

**⌨ In the terminal** (my hardware — just take the rules):
```bash
sudo cp 999-flightsim-override.rules /etc/udev/rules.d/99-flightsim.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
# then unplug and replug the device once
```

> **Distro note (Mint/Ubuntu · Fedora · Arch/CachyOS):** udev is the same
> everywhere — the path `/etc/udev/rules.d/` and the `udevadm` commands are
> identical. The only difference: `lsusb` lives in the `usbutils` package (install
> it via `apt`/`dnf`/`pacman` if needed).

**Unlock your own / unknown hardware:** first find the USB id, then add the
matching template to `/etc/udev/rules.d/99-flightsim.rules`:
```bash
lsusb        # your device's line: "ID 1234:5678 Vendor Product"
```
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
Then `sudo udevadm control --reload-rules && sudo udevadm trigger` and replug.

**✓ Checkpoint:** `ls -l /dev/hidraw*` or `/dev/input/js*` shows the nodes with
read/write permission (`rw`) for your user.

## 4. evdev or hidraw? (the `transport`)

Every device is read one of two ways — that's the `transport`. You almost never
choose it by hand; the app detects it on registration. For understanding:

| `transport` | For what | Typical |
|---|---|---|
| **`evdev`** | **axes & joystick buttons** — anything the system sees as a joystick/gamepad | yoke, throttle quadrant (TQ6+), pedals, joysticks |
| **`hidraw`** | **raw-HID panels** with their own report frames (buttons **and** LEDs/displays) | Saitek Switch/Multi/Radio panel |

Rule of thumb: **has displays (LEDs/7-segment) or is a switch panel → `hidraw`.
Just axes/buttons like a joystick → `evdev`.** The Device Explorer shows the
detected transport in the **"Transport"** column; a hidraw panel appears there
only **once** (its evdev "shadow" is suppressed).

## 5. My hardware: nothing to do

Fulcrum yoke, TQ6+, Saitek panels/pedals/trim wheel are already in the catalog
(`config/devices.yaml`) and the unlock rules → **continue with
[step 7](#7-map--test-no-simulator)**.

## 6. Set up other hardware (register & teach)

This is **all clicks** — no editing files, no typing USB numbers. The principle:
**① structure** (which buttons/axes/LEDs the device *has* — once per device)
separated from **② function** (what an element does in *this* aircraft — per
profile, [step 7](#7-map--test-no-simulator)). Details:
[`geraete-workflow.md`](geraete-workflow.md).

**🖱 In the app** (Mapper tab; labels partly German):
1. **„🔍 Geräte-Explorer…"** (Device Explorer) → lists **all** plugged-in devices,
   even unknown ones. Select yours → **„Registrieren…"** (Register), give it a
   short **id** (e.g. `my_yoke` — profiles reference the device by this id). This
   writes to the **user overlay**
   `~/.config/msfs-peripherals-bridge/devices.local.yaml` — the bundled
   `config/devices.yaml` stays untouched.
2. On the registered device, **„Geräteelemente…"** (Device elements) → create
   **inputs (read)** and **displays (write)** separately:
   - **„+ Input anlernen…"** (teach an input; button/switch/axis/encoder): actuate
     it on the device → the code is detected **live** (axes capture their raw
     range at the same time) → name it.
   - **„+ Anzeige hinzufügen…"** (add a display; LED/display): name + cell count.
     The exact hardware address (byte/bit) is found later by the **🔦 output scan**
     (step 7).
   - **„Aus Vorlage füllen…"** (fill from template) projects a known pattern
     (Saitek/Yoke/TQ6) into the element list in one go.

**⌨ In the terminal** (inspect/check):
```bash
uv run msfs-bridge inventory      # ALL devices raw, incl. unregistered
uv run msfs-bridge list-devices   # catalog devices connected right now
uv run msfs-bridge monitor <id>   # read a device's codes live (like evtest)
```
By hand you could also add an entry to `config/devices.yaml` (`id`, `name`,
`vendor`, `product`, `transport`) — but the GUI path is recommended.

**Get rid of a device (deregister/hide):** if you inherit foreign devices in the
list (e.g. the bundled sample devices), hide them — **non-destructively**; the
catalog and your profiles stay intact:
- **🖱 App:** Mapper → **right-click** a device → **„Aus der Geräteliste
  entfernen…"** (Remove from device list). Bring it back via **Device Explorer →
  „Ausgeblendete Geräte…"** (Hidden devices).
- **⌨ Terminal:** `uv run msfs-bridge deregister-device <id>` (undo: `--restore`,
  list: `--list`).

**✓ Checkpoint:** the device shows as **registered** in the Explorer, and its
inputs/displays are created as elements.

## 7. Map & test (no simulator)

From here you **don't need MSFS yet**. In the **Mapper tab**:

1. **Pick the device on the left** — the **replica** shows switches/axes/displays
   at their physical positions. With **„✎ Anordnen"** (Arrange) you drag elements
   into the grid; a **right-click → „Größe & Position…"** opens one dialog for exact
   **width / height / X / Y in pixels**, with a **„Raster ignorieren"** (ignore
   grid) box — off = snap to the grid, on = place pixel-exact. Saved per device.
2. **Map inputs** — **„+ Eingabe"** (+ Input) (or click an element) → pick the
   source via **„📋 Benannt"** (Named) from the taught inputs (instead of raw
   codes), set the target event/variable via **„Wählen…"** (Choose…), then
   **„Übernehmen"** (Apply). Codes can be (re)taught in the editor via **🪄 / 🎚
   Anlernen** (teach).
3. **Map displays** — **„+ Ausgabe ▾" → LED… / Display…** (+ Output): pick a
   variable and scan the report address via **„🔦 Adresse finden…"** (find address)
   — a test pulse moves around and you confirm "that's it!". Then the app drives
   LEDs and 7-segment displays straight from the sim.
4. For the 3 Saitek panels there's also **„Vorlage ▾"** (Template) — a whole panel
   in one go; your own arrangements can be saved as a template.

### Input types (what each does and how to map it)

Taught once as device *elements* (step 6), then mapped per profile here. Pick the
source by name via **„📋 Benannt"**; the special options live in the binding editor.

| Type | What it is | Special options |
|---|---|---|
| **Button** (Taster) | momentary — fires once on press | one event, or a list of events on press |
| **Switch** (Schalter) | two-position, holds its state | default: one stateful event (value 1 on, 0 off); optionally separate on- / off-edge event lists |
| **Axis** (Achse) | analog lever/stick — captured with its raw range | deadzone (as a raw min/max window), curve/expo, invert, output range (default −16383…16383); optional detent split for a lever notch |
| **Encoder** | rotary knob, taught in 2 directions | becomes two button bindings (CW → …_INC, CCW → …_DEC); on Saitek panels the inner ring / step speed comes from the template |
| **Hat** (POV) | 4/8-way view/trim hat | one binding grouping up/down/left/right |
| **Selector** | rotary detent group (e.g. magnetos) | each position is its own switch code, mapped individually |

### Output types (LEDs & displays)

Each output is driven **from a sim variable**. The hardware address (which
byte/bit or cell) is found by **„🔦 Adresse finden…"** — leave it, click, actuate,
confirm — or typed in by hand.

| Type | What it is | Key fields |
|---|---|---|
| **LED** (lamp) | one bit in the feature report, lit by a condition on a variable | byte, bit, and the **lit condition** (below) |
| **Display** (7-segment) | a numeric variable rendered into a run of digit cells | first byte (offset), number of cells, decimals |
| **Template** (Saitek) | a whole panel's LEDs/readouts in one go | via **„Vorlage ▾"** |

**The LED lit condition** — one entry covers every case, you never declare the
same LED twice:

- **„Leuchtet ab (≥)"** only → lit **at/above** that value — the usual indicator lamp (e.g. a warning on above 0.5).
- **„Leuchtet bis (<)"** only (clear „ab") → lit **below** that value — for something that must come on when a value *drops under* a limit.
- **both** → lit **within the window** `ab ≤ value < bis` — on between the two, off past either edge. This is a "gear in transit" lamp: it comes on once the gear leaves down-and-locked and goes dark again once it's fully up — exactly how the built-in Saitek gear LED drives red.

**Live test without a sim:** move an axis / flip a switch → the replica bar fills
or the element glows. Test displays deliberately with **🔦 LEDs/Display testen…**
(test LEDs/display).

> **Nothing to break:** `tools/simulate-from-scratch.sh` starts an isolated
> sandbox (empty catalog + empty profile) where you can safely rehearse the whole
> from-scratch flow — your real mappings are never touched.

**✓ Checkpoint:** actuating the hardware makes the replica react live, a taught
code lands in the editor, and a 🔦 test pulse lights the correct LED/cell.

## 8. Profiles: create, transfer, share

A **profile** (`profiles/<aircraft>.yaml`) holds the mapping **for one aircraft**.
When flying, the app auto-selects it via `aircraft_match` (substring of the
aircraft title). Schema + commented example:
[`../profiles/_schema.md`](../profiles/_schema.md).

There are **three** ways to pass mappings on — from small to large:

### a) Transfer/pull one device's mappings between profiles (same machine)
**🖱 App:** Mapper → **right-click** a device →
- **„Mappings in anderes Profil übertragen…"** (Transfer to another profile) — push
  this device's bindings + displays into a profile you pick; or
- **„Mappings aus einem anderen Profil holen…"** (Pull from another profile) — the
  reverse: copy them *from* another profile into the current one (only profiles that
  actually map the device are offered).

### b) Share a device package (with other people) — *new*
A **single device as a shareable `.zip`** — contains **device definition +
mapping + button arrangement + calibration**. Ideal for handing someone your
complete setup for one panel.

- **🖱 Export:** Mapper → **right-click** the device → **„Als Geräte-Paket
  exportieren…"** (Export as device package) — takes the mapping from the
  currently selected profile.
- **🖱 Import:** Mapper → **„📥 Geräte-Paket importieren…"** (Import device package)
  → pick the `.zip`. The device is registered, arrangement + calibration are
  restored, and the mapping is written into the **currently selected profile**.
- **⌨ Terminal:**
  ```bash
  uv run msfs-bridge export-device <id> my-panel.zip --profile piper_arrow
  uv run msfs-bridge import-device my-panel.zip --profile piper_arrow
  ```
  (Import without `--profile` only skips the mapping; device, arrangement and
  calibration still arrive.)

### c) Back up & restore everything (machine move, backup)
Bundles **all** profiles, the calibration and all GUI data (arrangement,
registered devices, templates) into **one** `.zip`.
- **🖱 App:** **Settings → "Backup & restore"** → **Export…** / **Import…**.
- **⌨ Terminal:** `uv run msfs-bridge export-config backup.zip` /
  `uv run msfs-bridge import-config backup.zip`.

**✓ Checkpoint:** an exported device package imports onto another setup; the
device then shows as registered and its mapping is in the target profile.

## 9. Set up the bridge (only for real flying)

**Requirement:** MSFS 2020 is installed via **Steam with Proton** and was
**started at least once** (that first launch creates the environment the bridge
needs; Proton Experimental recommended).

**🖱 In the app — everything is a button here, no terminal needed:**
**Connection tab.** It has a **checklist** (prefix, Windows Python,
`SimConnect.dll`, Proton, scripts — green/red):
1. If the **prefix** line is red, click **"Suchen…"** (Detect) — it auto-finds the
   MSFS Proton prefix across the usual Steam layouts (native, `.local/share`,
   Flatpak, a second drive) and fills the field; **Save**. (Or **"Durchsuchen…"**
   to pick the folder yourself.)
2. Click **"Set up prefix…"** (downloads Windows Python + SimConnect into the
   prefix — needs internet). Wait until it finishes.
3. Click **"Re-check"**.

**⌨ In the terminal** (the same by hand): `./tools/find-prefix.sh` prints the
prefix path, then
```bash
./bridge/setup-prefix.sh          # one-time: Windows Python + SimConnect into the prefix
```

**Where is your prefix? (Steam variant — important, distro-independent)** The
scripts look under `$STEAM_ROOT/steamapps/compatdata/1250410/pfx`. If the default
doesn't fit, set `STEAM_ROOT`:

| Steam variant | `STEAM_ROOT` |
|---|---|
| **Native, default** | *(nothing — `~/.steam/steam` fits)* |
| **Native, but `.local/share`** | `~/.local/share/Steam` |
| **Flatpak Steam** | `~/.var/app/com.valvesoftware.Steam/.local/share/Steam` |
| **Second library / other drive** | easiest: set `STEAM_COMPAT_DATA_PATH=<Library>/steamapps/compatdata/1250410` directly |

```bash
export STEAM_ROOT="$HOME/.var/app/com.valvesoftware.Steam/.local/share/Steam"  # Flatpak example
./bridge/setup-prefix.sh
```
`./tools/find-prefix.sh` searches every variant automatically and prints the
ready path plus the matching `export` lines. Other variables (defaults usually
fine): `MSFS_APPID` (Steam MSFS `1250410`), `PROTON_NAME` / `PROTON_PATH`.
Details: [`../bridge/README.md`](../bridge/README.md).

**✓ Checkpoint:** the checklist on the Connection tab is **all green** (or
`ls …/pfx/drive_c/pybridge` shows `pythonw.exe` + `SimConnect.dll`).

## 10. Fly

**🖱 In the app:** everything from the **Connection tab**:
1. **Start MSFS and load a flight** (until you're in the cockpit).
2. Click **„Alles starten"** (Start everything) — it starts the bridge and then the
   mapper as soon as the bridge is reachable. (The bridge only opens its port once
   MSFS runs with a flight loaded, which is why step 1 comes first; you can also
   start **Bridge** and **Mapper** separately.)

**⌨ In the terminal** (from the program folder, two terminals):
```bash
./bridge/run-bridge.sh                          # start the bridge in the prefix
uv run msfs-bridge run --profile piper_arrow    # or --aircraft "Piper Arrow"
```
> Port `7842` opens **only after** SimConnect — the bridge needs a running MSFS
> with a loaded flight. Check: `ss -ltn | grep 7842`.

**✓ Checkpoint:** move an axis / flip a switch → **it happens in the sim**.
Cross-check: `uv run msfs-bridge read "<SimVar>"` reads a value back.

## 11. Everyday (short form)

```bash
# Load MSFS + a flight, then:
./bridge/run-bridge.sh
uv run msfs-bridge run --profile <profile>
# or entirely from the GUI (Connection tab: start/stop bridge/mapper):
uv run python -m msfs_peripherals_bridge.gui
```

**Tune a mapping live (no sim needed):** `--dry-run -v` logs every command instead
of sending it — ideal for fine-tuning:
```bash
uv run msfs-bridge run --profile piper_arrow --dry-run -v
```
Move a control → you see lines like `SendEvent(name='AILERON_SET', data=-16383)`.
Edit `profiles/<aircraft>.yaml` (deadzone, curve, `invert`, `raw_min/max`, event),
`Ctrl`+`C`, re-run — startup is instant, so the loop is tight. All commands as
copy-paste lines: [`cheatsheet.md`](cheatsheet.md).

## 12. Troubleshooting

- **`command not found: uv`** → close the terminal, open a new one, `cd ~/msfs-peripherals-bridge`, try again.
- **"No such file or directory"** → you're not in the program folder: `cd ~/msfs-peripherals-bridge` first.
- **Device doesn't react in the app** → Connection tab → **"Enable devices…"**, then unplug/replug.
- **Mouse pointer jumps** when plugging in a panel → same fix: **"Enable devices…"** (the `LIBINPUT_IGNORE_DEVICE` rule is missing).
- **"not live-readable" in the GUI** → hidraw node not `0666` (udev missing), or device not plugged in.
- **Bridge won't connect** → is MSFS really running **with a loaded flight**? Port open? `ss -ltn | grep 7842`. The bridge is **single-client** — no second mapper at once.
- **Testing/teaching a panel collides** → the running mapper "owns" the hidraw device; stop the mapper (Connection tab) to test/teach.
- **`L:`/`H:`/`B:` variables do nothing** → they need the MobiFlight WASM channel (still open); standard `A:` variables and `K:` events work.

## 13. Where is my data?

| Location | What | Survives a re-clone? |
|---|---|---|
| **in the repo** | `profiles/*.yaml` (mappings), `config/calibration.yaml` | ❌ (recoverable via git if committed) |
| **`~/.config/msfs-peripherals-bridge/`** | `devices.local.yaml` (your devices), `panel-layouts.yaml` (arrangement), `output-templates.yaml`, `gui-settings.json` | ✅ |

The **full backup** from [step 8c](#c-back-up--restore-everything-machine-move-backup)
covers **both**.

## 14. Further reading

- [`cheatsheet.md`](cheatsheet.md) — every command as a copy-paste line.
- [`simvars-reference.md`](simvars-reference.md) — SimVars/events/LVars for mapping.
- [`bridge-concept.md`](bridge-concept.md) — how the bridge works (with diagrams).
- [`geraete-workflow.md`](geraete-workflow.md) — the systematic device chain behind setup.
- [`spadnext-import.md`](spadnext-import.md) — reuse an existing SPAD.neXt profile.
- All documents at a glance: [`README.md`](README.md).
