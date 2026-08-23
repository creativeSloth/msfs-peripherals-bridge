# Command cheat-sheet

Every user-facing command, as a copy-paste terminal line with a one-line note.
Run from the repo root. `uv run msfs-bridge …` is the app; the one-command
`msfs-bridge` launcher (in `~/.local/bin`) starts the Wine bridge **and** the
mapper together — see the [Manual](MANUAL.md).

```bash
uv run msfs-bridge --help          # list all commands
uv run msfs-bridge <cmd> --help    # options for one command
```

---

## Daily flying

```bash
msfs-bridge                    # launcher: Piper Arrow profile (start AFTER MSFS)
msfs-bridge cessna_152         # launcher: pick a profile by name
# Strg-C stops only the mapper; the SimConnect server keeps running.
```

Manual equivalent (two terminals, full control):

```bash
./bridge/run-bridge.sh                            # 1) Wine SimConnect bridge (port 7842)
uv run msfs-bridge run --profile piper_arrow      # 2) Linux mapper, another terminal
uv run msfs-bridge run --aircraft "Turbo Arrow"   #    …or auto-pick by aircraft title
```

---

## See what's connected / check config

```bash
uv run msfs-bridge list-devices    # catalog devices + connected/absent right now
uv run msfs-bridge list-profiles   # available aircraft profiles + what they match
uv run msfs-bridge validate        # catalog + every profile parse & calibrate cleanly
uv run msfs-bridge scan            # every controller with its axes/buttons/hats (find new USB ids)
```

---

## Calibrating a new device

The order to bring a new lever/yoke online. `<device>` is a catalog id
(`yoke`, `tq6`, `trim`, `pedals`) or a raw `/dev/input/eventX` path.

```bash
# 1) Find it + see its axes/codes. NEW = not in config/devices.yaml yet.
uv run msfs-bridge scan

# 2) Watch raw events live (like evtest) to learn which code is which control.
uv run msfs-bridge monitor tq6          # wiggle one control, read its code/value

# 3) Record full axis travel + seen buttons/hats into config/calibration.yaml.
#    Move EVERY axis end-to-end, work the hats/buttons, then Strg-C to save.
uv run msfs-bridge calibrate tq6
uv run msfs-bridge calibrate tq6 --seconds 20   # …or auto-stop after 20 s

# 4) One-shot: print current raw value of every axis (no movement needed).
uv run msfs-bridge snapshot tq6

# 5) Park the levers on their notch, then store that as the detent ('0' point):
uv run msfs-bridge snapshot tq6 --save-detent
# 6) Centre a spring-return axis (yoke/pedals) at its resting position:
uv run msfs-bridge snapshot pedals --save-center

uv run msfs-bridge validate              # confirm the new ranges resolve
```

A fresh `calibrate` keeps previously saved detents and control labels, so you
can re-sweep ranges without losing step 5/6.

---

## Heading-bug rocker switch — nothing to type

The Arrow's **left rocker-up button just works**: press it and the AP heading bug
snaps to the current heading (wired in `piper_arrow.yaml` as an `event_from_var`
button action). No terminal command needed.

## Reading SimVars out of the sim (diagnostics only)

You normally don't need this — it's for checking a value or finding a SimVar
name. Needs the Wine bridge up (`msfs-bridge` launcher or `./bridge/run-bridge.sh`)
and MSFS running with a flight loaded. Names may use spaces or underscores.

```bash
# One-shot read (waits up to 10 s for the first value):
uv run msfs-bridge read "AUTOPILOT HEADING LOCK DIR" --unit degrees   # heading bug
uv run msfs-bridge read TITLE --unit string                           # loaded aircraft
uv run msfs-bridge read "PLANE HEADING DEGREES MAGNETIC" -u degrees   # current heading

# Live stream — prints on every change (Strg-C to stop):
uv run msfs-bridge read "AUTOPILOT HEADING LOCK DIR" -u degrees --watch
```

More variable and event names: [simvars-reference.md](simvars-reference.md).

---

## Tuning a profile (no sim needed)

```bash
# Log the resolved commands instead of sending them; move a control, see the line.
uv run msfs-bridge run --profile piper_arrow --dry-run -v
```

Loop: keep `--dry-run -v` running, edit `profiles/<aircraft>.yaml`
(deadzone / curve / `invert` / `raw_min,raw_max` / event name), Strg-C, re-run.
Profile schema + a commented example: [`profiles/_schema.md`](../profiles/_schema.md).

---

## Maintenance

```bash
uv sync --extra dev    # install / update deps into .venv
uv run pytest          # tests
uv run ruff check .    # lint
uv run mypy            # type-check
```
