#!/usr/bin/env python3
"""Interactive HID *output* tester for the Saitek Pro Flight Multi Panel (06a3:0d06).

The HID report descriptor declares ONE feature report (report id 0) with 12 data
bytes:
    bytes 0..9  -> display: 10 digit cells (each 0..255), i.e. 2 rows x 5 digits
    byte  10    -> 8 button LEDs (bitmask: AP/HDG/NAV/IAS/ALT/VS/APR/REV)
    byte  11    -> 5 spare button-feature bits (+3 pad), purpose unknown

We send the full 13-byte buffer [report_id=0] + 12 data bytes via HIDIOCSFEATURE
(same ioctl as the switch-panel LEDs), then walk things one at a time so the map
can be read off empirically.

Sub-commands:
    leds        light LED bits 0..7 one at a time (~2s each) -> note button order
    spare       toggle byte-11 bits 0..4 one at a time       -> note any effect
    positions   show "8" in one display cell at a time 0..9   -> note row/column order
    digits      show value v in ALL cells, v = 0..15          -> note glyph per value
    raw HEX...  send literal data bytes (hex, space sep), pad/truncate to 12

Linux-only; reads /dev/hidraw directly (06a3 nodes are 0666). Ctrl-C to quit.
"""

from __future__ import annotations

import os
import sys
import time

VENDOR, PRODUCT = 0x06A3, 0x0D06
SYS = "/sys/class/hidraw"
N_DATA = 12  # display(10) + leds(1) + spare(1)
_HIDIOCSFEATURE_BASE = (3 << 30) | (ord("H") << 8) | 0x06


def find_node() -> str:
    for node in sorted(os.listdir(SYS)):
        try:
            with open(f"{SYS}/{node}/device/uevent", encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            continue
        for line in text.splitlines():
            if line.startswith("HID_ID="):
                _, v, p = line.split("=", 1)[1].split(":")
                if (int(v, 16), int(p, 16)) == (VENDOR, PRODUCT):
                    return f"/dev/{node}"
    sys.exit(f"Multi Panel ({VENDOR:#06x}:{PRODUCT:#06x}) not found")


def send(path: str, data: bytes) -> None:
    import fcntl

    payload = (bytes(data) + bytes(N_DATA))[:N_DATA]  # pad/truncate to 12
    buf = bytearray([0x00]) + payload  # report id 0 + data
    request = _HIDIOCSFEATURE_BASE | (len(buf) << 16)
    fd = os.open(path, os.O_RDWR)
    try:
        fcntl.ioctl(fd, request, buf)
    finally:
        os.close(fd)


def clear(path: str) -> None:
    send(path, bytes(N_DATA))


def test_leds(path: str) -> None:
    print("LED walk: byte 10, bit 0..7 one at a time. Note which BUTTON lights.\n")
    for bit in range(8):
        data = bytearray(N_DATA)
        data[10] = 1 << bit
        send(path, bytes(data))
        print(f"  byte10 bit{bit} (0x{1 << bit:02x}) ON  -> which button?")
        time.sleep(2.2)
    clear(path)


def test_spare(path: str) -> None:
    print("Spare walk: byte 11, bit 0..4 one at a time. Note ANY effect.\n")
    for bit in range(5):
        data = bytearray(N_DATA)
        data[11] = 1 << bit
        send(path, bytes(data))
        print(f"  byte11 bit{bit} (0x{1 << bit:02x}) ON  -> any effect?")
        time.sleep(2.2)
    clear(path)


def test_positions(path: str) -> None:
    print("Position walk: one display cell = '8' at a time, index 0..9.")
    print("Note row (top/bottom) and column (left..right) for each index.\n")
    for i in range(10):
        data = bytearray(N_DATA)
        data[i] = 8  # try literal 8; if blank, we'll learn the encoding in `digits`
        send(path, bytes(data))
        print(f"  display cell index {i} = value 8  -> where does it show?")
        time.sleep(2.2)
    clear(path)


def test_digits(path: str) -> None:
    print("Digit walk: ALL 10 cells = value v, v = 0..15. Note the glyph per value.\n")
    for v in range(16):
        send(path, bytes([v] * 10 + [0, 0]))
        print(f"  all cells = {v} (0x{v:02x})  -> what glyph?")
        time.sleep(2.2)
    clear(path)


def test_raw(path: str, args: list[str]) -> None:
    data = bytes(int(x, 16) for x in args)
    print(f"raw -> {' '.join(f'{b:02x}' for b in (data + bytes(N_DATA))[:N_DATA])}")
    send(path, data)


def main() -> None:
    path = find_node()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "leds"
    print(f"Multi Panel at {path}. Test: {cmd}\n")
    try:
        if cmd == "leds":
            test_leds(path)
        elif cmd == "spare":
            test_spare(path)
        elif cmd == "positions":
            test_positions(path)
        elif cmd == "digits":
            test_digits(path)
        elif cmd == "raw":
            test_raw(path, sys.argv[2:])
        elif cmd == "clear":
            clear(path)
        else:
            sys.exit(f"unknown test '{cmd}'")
    except KeyboardInterrupt:
        clear(path)
        print("\ncleared, bye")


if __name__ == "__main__":
    main()
