# Hardware research

Per-device research notes for the four peripherals this project targets.
Each file lists the controls (analog axes, buttons, hats), the known USB id,
Linux/`evdev` notes and suggested MSFS mappings.

> ⚠️ The control counts below come from manufacturer specs and reviews. The
> **authoritative** axis/button/hat layout for *your* units must be captured
> with `uv run msfs-bridge scan` and `… calibrate <device>` once the hardware
> is connected. None of the four devices were attached when these notes were
> written (2026-06-19).

| Device | File | USB id | Analog axes | Digital |
|--------|------|--------|:-----------:|---------|
| Fulcrum One Yoke | [fulcrum-one-yoke.md](fulcrum-one-yoke.md) | ❓ TBD (placeholder `0000:0000`) | 2 (pitch, roll) | 8-way hat, 4 buttons, 2 rockers |
| VirtualFly TQ6+ | [virtualfly-tq6plus.md](virtualfly-tq6plus.md) | `16d0:0da2` | 6 levers | detent zones |
| Saitek Cessna Trim Wheel | [saitek-cessna-trim-wheel.md](saitek-cessna-trim-wheel.md) | `06a3:0bd4` | 1 (trim) | – |
| Saitek Pro Flight Rudder Pedals | [saitek-rudder-pedals.md](saitek-rudder-pedals.md) | `06a3:0763` | 3 (rudder + 2 toe brakes) | – |

See also [`../simvars-reference.md`](../simvars-reference.md) for the catalog of
SimVars and events these controls can be mapped to.
