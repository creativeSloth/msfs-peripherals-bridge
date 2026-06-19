# Fulcrum One Yoke

Premium desk-mounted flight sim yoke by Fulcrum Simulator Controls.

## Sensing & mechanics
- **Hall-effect digital sensors** on both axes (no potentiometers → no wear,
  no drift, no calibration creep). More sensitive/reliable than pots.
- **Pitch:** > 200 mm of linear travel (push/pull).
- **Roll:** 180° of rotation.
- Long travel, progressive resistance, smooth self-return feel.

## Controls (HID)
Presents as a **standard HID joystick** — no driver needed; axes and buttons
can be reassigned in any sim or remapping software.

| Control | Type | Count | Typical use |
|---------|------|:-----:|-------------|
| Pitch (elevator) | analog axis | 1 | `ELEVATOR_SET` / `AXIS_ELEVATOR_SET` |
| Roll (aileron) | analog axis | 1 | `AILERON_SET` / `AXIS_AILERONS_SET` |
| POV hat | 8-way hat switch | 1 | trim / view / AP nudges |
| Push buttons | momentary buttons | 4 | PTT, AP disconnect, flaps, etc. |
| Rocker switches | 2-way each | 2 | elevator/aileron trim, etc. |

So expect roughly **2 analog axes** + **1 hat (8 directions)** + **4 buttons**
+ **2 rockers (≈4 button events)** ≈ **8–10 digital inputs**.

## USB id — ACTION REQUIRED
The id in `config/devices.yaml` and the udev rules is a **placeholder
`0000:0000`**. Capture the real one with the hardware connected:

```bash
lsusb                       # read the real idVendor:idProduct
uv run msfs-bridge scan     # shows it flagged as "NEW" with full capabilities
```

Then update `config/devices.yaml` (the `yoke` entry) and the udev rule block
in `999-flightsim-override.rules`.

## Linux / evdev notes
- As a HID joystick it should appear under `/dev/input/js*` and `event*`.
- The hat will show up as `ABS_HAT0X` / `ABS_HAT0Y` (values -1/0/+1), **not** as
  buttons — the calibrate tool records these under `hats`.
- Rocker switches usually report as button pairs (e.g. `BTN_TRIGGER`, …).

## Suggested mapping (C172)
- Pitch → `ELEVATOR_SET` (consider `invert: true`).
- Roll → `AILERON_SET`.
- Hat up/down → `ELEV_TRIM_DN` / `ELEV_TRIM_UP` (or view).
- Buttons → AP master, PTT, flaps up/down.

## Sources
- [Fulcrum Yoke product page](https://www.fulcrumsim.com/product/fulcrum-yoke/)
- [Fulcrum One Yoke Instructions (PDF)](https://fulcrumsim.com/wp-content/uploads/2021/11/Fulcrum-One-Yoke-Instructions.pdf)
- [Key.Aero review](https://www.key.aero/article/fulcrum-one-yoke-review)
- [FSElite feature overview](https://fselite.net/content/fulcrum-simulator-controls-one-yoke-feature-overview-video/)
