# Quick Start — for Beginners (copy-paste only)

This guide is for you if you **don't know Python or Linux** and just want to
**copy-paste a few commands**. After the setup, almost everything else is done
by **clicking buttons inside the app** — no more terminal needed.

You only ever paste **4 commands**. Each grey block: select it, copy it, paste it
into the terminal (`Ctrl`+`Shift`+`V`), press Enter. After each step there is a
**✓ How you know it worked**.

> **Which hardware?** This assumes you have **the supported devices** (Fulcrum
> yoke, VirtualFly TQ6+, Saitek panels/pedals/trim wheel). Different hardware?
> You still follow this guide — you just register your device with a click in
> the app later (see the box at the end, "Other hardware"). You never have to
> look up USB numbers by hand.

---

## Step 0 — Open a terminal

The "terminal" is a window where you paste commands.

- **Linux Mint / Ubuntu:** press `Ctrl`+`Alt`+`T`.
- **Fedora / GNOME:** press the `Super` key (Windows key), type `Terminal`, Enter.
- **CachyOS / KDE:** press `Super`, type `Konsole`, Enter.

---

## Step 1 — Install two small tools (git + curl)

Use **the one line for your distribution**:

**Linux Mint / Ubuntu:**
```bash
sudo apt update && sudo apt install -y git curl
```
**Fedora:**
```bash
sudo dnf install -y git curl
```
**Arch / CachyOS:**
```bash
sudo pacman -S --needed git curl
```

> `sudo` asks for your **password**. While you type it the screen stays blank —
> that's normal. Type it and press Enter.

**✓ How you know it worked:** the line finishes without a red error (or says
they're "already installed").

---

## Step 2 — Download the program and set everything up

Copy these **three lines together**. They download the program and then run its
installer, which does *everything* for you — it installs the right Python,
creates the environment, installs all packages, and unlocks your devices. This
can take a few minutes the first time, and it will ask for your password once.

```bash
git clone https://github.com/creativeSloth/msfs-peripherals-bridge.git
cd msfs-peripherals-bridge
./install.sh
```

**✓ How you know it worked:** at the end it prints a green box saying
**"All set!"** with the command to start the app.

> Coming back later in a new terminal? First go back into the folder with
> `cd ~/msfs-peripherals-bridge`, then use the commands below.

---

## Step 3 — Start the program

```bash
uv run python -m msfs_peripherals_bridge.gui
```

**✓ How you know it worked:** a **window** opens with several tabs. Plug in your
hardware and move an axis or flip a switch — in the **Mapper tab** you see the
device react (a bar fills up / an element lights up). **You don't need a
simulator for this yet.**

> **Tip — see the app in English:** open the **Settings** tab → **GUI language**
> → **English**, then restart the app. (A few buttons on the Mapper tab stay in
> German; where that matters this guide gives the German label.)

> If a device does **not** react: open the **Connection tab** and click
> **"Enable devices…"** — a password window appears, and it unlocks your devices
> (this is the same thing the installer already did in Step 2; the button just
> repeats it if needed). Then unplug and replug the device once.

**That's the whole setup.** For trying things out and building your mappings,
you're done. Continue below only when you want to **fly in the real MSFS**.

---

## Step 4 — Prepare the bridge for flying (one-time, all in the app)

The "bridge" is a small helper that connects the app to MSFS. Setting it up is
done with **buttons in the app**, not the terminal.

**Requirement:** MSFS 2020 is installed via **Steam with Proton** and was
**started at least once** (that first launch is what creates the environment the
bridge needs).

In the app, open the **Connection tab**. There is a **checklist** that shows
green/red for everything the bridge needs:

1. If the **prefix** line is red (the app can't find your MSFS), find it with one
   command in the terminal:
   ```bash
   ./tools/find-prefix.sh
   ```
   Copy the folder it prints, paste it into the **"Prefix"** field on the
   Connection tab, and click **Save**.
2. Click **"Set up prefix…"**. A window shows the progress (it downloads a few
   things — needs internet). Wait until it finishes.
3. Click **"Re-check"**.

**✓ How you know it worked:** the checklist on the Connection tab is **all
green**.

---

## Step 5 — Fly

Everything can be done from the **Connection tab**:

1. **Start MSFS and load a flight** (until you're sitting in the cockpit).
2. In the app's **Connection tab**, click **Start** for the **Bridge**, then
   **Start** for the **Mapper** (pick your aircraft profile if asked).

**✓ How you know it worked:** move an axis or flip a switch on your hardware —
and **it happens in the simulator**.

> Prefer the terminal? Two commands do the same (run them from the program
> folder): `./bridge/run-bridge.sh` in one terminal, then
> `uv run msfs-bridge run --profile piper_arrow` in a second one. See
> [`INSTALL.md`](INSTALL.md) Step 6.

---

## Other hardware (not the supported devices)?

You do **not** edit files or look up USB numbers by hand. In the app (these
Mapper-tab buttons are labelled in German):

1. **Mapper tab → "🔍 Geräte-Explorer…"** (Device Explorer) — it lists every
   plugged-in device, even unknown ones. Select yours and click
   **"Registrieren…"** (Register).
2. Then **"Geräteelemente…"** (Device elements) to teach it its
   buttons/switches/axes by simply pressing them on the hardware.

Full details are in [`INSTALL.md`](INSTALL.md), Step 3.

---

## If something doesn't work

- **"command not found: uv"** → close the terminal, open a new one, then
  `cd ~/msfs-peripherals-bridge` and try again.
- **A command says "No such file or directory"** → you're not in the program
  folder; run `cd ~/msfs-peripherals-bridge` first.
- **A device doesn't react in the app** → Connection tab → **"Enable devices…"**,
  then unplug/replug the device.
- **Mouse pointer jumps when you plug a panel in** → same fix: **"Enable
  devices…"** on the Connection tab.
- **Bridge won't connect** → is MSFS really running **with a flight loaded**? The
  bridge must be started **after** MSFS.

More detail and edge cases: [`INSTALL.md`](INSTALL.md).
