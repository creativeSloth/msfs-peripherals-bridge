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

## scan_radio.py — input scanner (Radio Panel, 06a3:0d05)
Same as scan_multi.py for the Radio Panel. Operate one control at a time to read
off the selector / encoder / swap bits (3-byte input, 24 bits). Feed the codes
into the profile's `radio_panel` output block (RadioBank.code, RadioUnit
outer/inner cw/ccw + swap):

    python3 -u tools/panel-scan/scan_radio.py

## out_radio.py — output tester (Radio Panel)
Walks the 20 display cells + 2 flag bytes so you can confirm the cell layout,
digit glyphs, the decimal-point encoding (the one Chunk A assumption), and hunt
the brightness flags:

    python3 -u tools/panel-scan/out_radio.py positions  # cell 0..19 -> row/column
    python3 -u tools/panel-scan/out_radio.py digits     # byte value 0..15 glyph
    python3 -u tools/panel-scan/out_radio.py dot        # VERIFY digit+0xD0 = dot
    python3 -u tools/panel-scan/out_radio.py freq       # sample 118.00 / 118.30
    python3 -u tools/panel-scan/out_radio.py flags      # bytes 20..21 -> brightness?
    python3 -u tools/panel-scan/out_radio.py clear

## TODO (see memory project-panel-tools-folder)
Per-panel copies for now (scan_multi/out_multi, scan_radio/out_radio). Could be
merged into one `scan_panel.py` + `out_panel.py` with a device argument later.
