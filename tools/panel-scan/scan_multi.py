#!/usr/bin/env python3
"""Interactive HID input scanner for the Saitek Pro Flight Multi Panel (06a3:0d06).

Run it, then operate ONE control at a time on the panel. For every input report
that differs from the previous one it prints the full report in hex plus the
bit indices that changed (1 = set, 0 = cleared), using the same
"global bit index = byte*8 + bit" convention as hidraw_reader.iter_bit_changes.

That lets us read off the bit->function map empirically (the Multi Panel layout
is not derivable; it must be measured), exactly like the Switch Panel was done.

For rotary encoders (the big knob, the pitch-trim wheel) you'll see a bit that
pulses up then down on each detent; turn slowly one click at a time to capture
CW vs CCW. The function-selector knob (ALT/VS/IAS/HDG/CRS) is a 5-position
switch -> watch which bits change between positions.

Ctrl-C to quit. Linux-only, reads /dev/hidraw directly (06a3 nodes are 0666).
"""

from __future__ import annotations

import os
import select
import sys

PRODUCT = 0x0D06  # Multi Panel
VENDOR = 0x06A3
SYS = "/sys/class/hidraw"


def find_node() -> str:
    for node in sorted(os.listdir(SYS)):
        try:
            with open(f"{SYS}/{node}/device/uevent", encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            continue
        for line in text.splitlines():
            if line.startswith("HID_ID="):
                _, vendor, product = line.split("=", 1)[1].split(":")
                if (int(vendor, 16), int(product, 16)) == (VENDOR, PRODUCT):
                    return f"/dev/{node}"
    sys.exit(f"Multi Panel ({VENDOR:#06x}:{PRODUCT:#06x}) not found under {SYS}")


def fmt(data: bytes) -> str:
    return " ".join(f"{b:02x}" for b in data)


def bits(data: bytes) -> str:
    return " ".join(f"{b:08b}"[::-1] for b in data)  # LSB-first so bit0 is leftmost


def changed_bits(prev: bytes, cur: bytes) -> list[str]:
    out: list[str] = []
    for i in range(max(len(prev), len(cur))):
        p = prev[i] if i < len(prev) else 0
        c = cur[i] if i < len(cur) else 0
        diff = p ^ c
        for bit in range(8):
            mask = 1 << bit
            if diff & mask:
                out.append(f"bit{i * 8 + bit}{'↑' if c & mask else '↓'}")
    return out


def main() -> None:
    path = find_node()
    print(f"Reading {path} (Multi Panel). Operate one control at a time. Ctrl-C to quit.\n")
    fd = os.open(path, os.O_RDONLY)
    prev: bytes | None = None
    try:
        while True:
            select.select([fd], [], [])
            data = os.read(fd, 64)
            if not data:
                continue
            if prev is None:
                prev = data
                print(f"baseline (idle): hex[{fmt(data)}]  bits[{bits(data)}]\n")
                continue
            if data == prev:
                continue
            marks = ", ".join(changed_bits(prev, data)) or "(no bit diff — length/other)"
            print(f"hex[{fmt(data)}]  changed: {marks}")
            prev = data
    except KeyboardInterrupt:
        print("\nbye")
    finally:
        os.close(fd)


if __name__ == "__main__":
    main()
