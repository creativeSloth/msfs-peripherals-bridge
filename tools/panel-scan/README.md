# Panel scan / calibration helpers

Throwaway-ish Linux tools used to **empirically measure the Saitek panels' HID
maps** (input bit -> function, output feature-report layout). They read/write
`/dev/hidraw*` directly (the 06a3 nodes are mode 0666 via the udev rule).

The measured results are the source of truth in `docs/memory/*-hid.md`; these
scripts are kept so the maps can be re-checked and so the **Radio Panel** can be
measured the same way.

## scan_multi.py — input scanner
Prints every input report that changed plus the changed bit indices
(`code = byte*8 + bit`, matching `hidraw_reader`). Run it, then operate one
control at a time:

    python3 -u tools/panel-scan/scan_multi.py

## out_multi.py — output tester (Multi Panel)
Writes feature reports and walks LEDs / display cells / digit values so you can
read off the map by watching the panel:

    python3 -u tools/panel-scan/out_multi.py leds       # 8 button LEDs, bit 0..7
    python3 -u tools/panel-scan/out_multi.py positions  # display cell 0..9
    python3 -u tools/panel-scan/out_multi.py digits     # byte value 0..15 glyph
    python3 -u tools/panel-scan/out_multi.py raw 00 01 02 ...   # literal 12 data bytes
    python3 -u tools/panel-scan/out_multi.py clear

## TODO (see memory project-panel-tools-folder)
Generalise to `scan_panel.py` + `out_panel.py` with a device argument so the
Switch / Multi / Radio panels share one tool instead of per-panel copies.
