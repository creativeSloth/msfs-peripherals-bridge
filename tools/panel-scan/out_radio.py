#!/usr/bin/env python3
"""Interactive HID *output* tester for the Saitek Pro Flight Radio Panel (06a3:0d05).

The report descriptor declares 20 display digits (FEATURE #1) + 14 flag bits
(FEATURE #2). With no report id in the descriptor we prepend report nr 0 and send
one combined buffer [report_id=0] + 20 digit cells + 2 flag bytes = 23 bytes via
HIDIOCSFEATURE (same ioctl as the Multi Panel / switch-panel LEDs). Expected cell
layout (confirm with `positions` — see docs/memory/radio-panel-hid.md):
    bytes 0..4   -> upper display, top row    (upper radio ACTIVE)
    bytes 5..9   -> upper display, bottom row  (upper radio STANDBY)
    bytes 10..14 -> lower display, top row     (lower radio ACTIVE)
    bytes 15..19 -> lower display, bottom row  (lower radio STANDBY)
    bytes 20..21 -> flag bits (brightness / segment extras — purpose unknown)

Digit encoding is shared with the Multi Panel (mapping/display.py): 0x00..0x09 =
digit 0..9, 0x0F = blank, 0xEE = minus, digit+0xD0 = digit with a trailing
decimal point. The `dot` command VERIFIES that last one on the real hardware — it
is the one open assumption behind Chunk A's format_frequency().

Sub-commands:
    positions   show "8" in one cell at a time 0..19   -> note row/column order
    digits      show value v in ALL cells, v = 0..15   -> confirm glyph per value
    dot         show "8." (8 + 0xD0) in each cell 0..19 -> VERIFY the decimal point
    freq        show a sample 118.00 / 118.30 like the controller renders it
    flags       toggle flag bytes 20..21, bit 0..7      -> find brightness control
    raw HEX...  send literal data bytes (hex, space sep), pad/truncate to 22
    clear       blank everything

Linux-only; reads /dev/hidraw directly (06a3 nodes are 0666). Ctrl-C to quit.
"""

from __future__ import annotations

import os
import sys
import time

VENDOR, PRODUCT = 0x06A3, 0x0D05
SYS = "/sys/class/hidraw"
N_DATA = 22  # 20 display cells + 2 flag bytes
DOT = 0xD0  # digit byte offset that lights the trailing decimal point
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
    sys.exit(f"Radio Panel ({VENDOR:#06x}:{PRODUCT:#06x}) not found")


def send(path: str, data: bytes) -> None:
    import fcntl

    payload = (bytes(data) + bytes(N_DATA))[:N_DATA]  # pad/truncate to 22
    buf = bytearray([0x00]) + payload  # report id 0 + data
    request = _HIDIOCSFEATURE_BASE | (len(buf) << 16)
    fd = os.open(path, os.O_RDWR)
    try:
        fcntl.ioctl(fd, request, buf)
    finally:
        os.close(fd)


def clear(path: str) -> None:
    send(path, bytes(N_DATA))


def test_positions(path: str) -> None:
    print("Position walk: one display cell = '8' at a time, index 0..19.")
    print("Note display (upper/lower), row (active/standby) and column for each.\n")
    for i in range(20):
        data = bytearray(N_DATA)
        data[i] = 8
        send(path, bytes(data))
        print(f"  cell index {i} = 8  -> where does it show?")
        time.sleep(2.0)
    clear(path)


def test_digits(path: str) -> None:
    print("Digit walk: ALL 20 cells = value v, v = 0..15. Confirm the glyph per value.")
    print("(expect 0..9 = digits, 0x0f = blank, 0x0e/0xee = minus)\n")
    for v in range(16):
        send(path, bytes([v] * 20 + [0, 0]))
        print(f"  all cells = {v} (0x{v:02x})  -> what glyph?")
        time.sleep(2.0)
    clear(path)


def test_dot(path: str) -> None:
    print(f"Decimal-point walk: '8.' (8 + 0x{DOT:02x}) in each cell 0..19.")
    print("VERIFY a trailing dot lights on the digit (the Chunk A assumption).\n")
    for i in range(20):
        data = bytearray(N_DATA)
        data[i] = 8 + DOT
        send(path, bytes(data))
        print(f"  cell {i} = 8+dot (0x{8 + DOT:02x})  -> does a decimal point show?")
        time.sleep(2.0)
    clear(path)


def test_freq(path: str) -> None:
    print("Frequency sample: upper 118.00 over 118.30, lower blank. Reads right?\n")
    row_active = [1, 1, 8 + DOT, 0, 0]  # 118.00
    row_standby = [1, 1, 8 + DOT, 3, 0]  # 118.30
    data = row_active + row_standby + [0x0F] * 10 + [0, 0]
    send(path, bytes(data))
    print("  showing 118.00 / 118.30 — Ctrl-C to clear")
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        clear(path)
        raise


def test_flags(path: str) -> None:
    print("Flag walk: bytes 20..21, bit 0..7 one at a time. Note ANY effect")
    print("(brightness? segment test? display on/off?).\n")
    for byte in (20, 21):
        for bit in range(8):
            data = bytearray(N_DATA)
            data[byte] = 1 << bit
            send(path, bytes(data))
            print(f"  byte{byte} bit{bit} (0x{1 << bit:02x}) ON  -> any effect?")
            time.sleep(2.0)
    clear(path)


def test_raw(path: str, args: list[str]) -> None:
    data = bytes(int(x, 16) for x in args)
    print(f"raw -> {' '.join(f'{b:02x}' for b in (data + bytes(N_DATA))[:N_DATA])}")
    send(path, data)


def main() -> None:
    path = find_node()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "positions"
    print(f"Radio Panel at {path}. Test: {cmd}\n")
    try:
        if cmd == "positions":
            test_positions(path)
        elif cmd == "digits":
            test_digits(path)
        elif cmd == "dot":
            test_dot(path)
        elif cmd == "freq":
            test_freq(path)
        elif cmd == "flags":
            test_flags(path)
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
