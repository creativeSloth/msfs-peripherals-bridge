#!/usr/bin/env python3
"""Interactive HID input scanner for the Saitek Pro Flight Radio Panel (06a3:0d05).

Run it, then operate ONE control at a time on the panel. For every input report
that differs from the previous one it prints the full report in hex plus the
bit indices that changed (1 = set, 0 = cleared), using the same
"global bit index = byte*8 + bit" convention as hidraw_reader.iter_bit_changes.

That lets us read off the bit->function map empirically (the Radio Panel layout
is not derivable; it must be measured), exactly like the Multi/Switch Panels.

The report descriptor says INPUT = 3 bytes = 24 button bits. Expected structure
(from docs/memory/radio-panel-hid.md — confirm which bit is which here):
  * upper mode selector: 7 positions one-hot (COM1/COM2/NAV1/NAV2/ADF/DME/XPDR)
  * lower mode selector: 7 positions one-hot (same set)
  * 4 encoders: each an outer (coarse) + inner (fine) knob, CW + CCW = 8 bits
  * 2 ACT/STBY push buttons (the pushable encoders) = 2 bits
  ⇒ 7+7+8+2 = 24.

Feed the measured codes into the profile's `radio_panel` output block
(RadioBank.code = selector bit; RadioUnit.outer_cw/ccw, inner_cw/ccw, swap).
For an encoder turn you'll see a bit pulse up then down per detent — turn slowly,
one click at a time, to capture CW vs CCW. For a selector, watch which bit is set
in each of its positions.

TIMING (for the contact-bounce hunt): each line prints the gap since the previous
change (``+N.Nms``), and every ``bitK↑`` carries the gap since that SAME bit last
went up (``Δ N.Nms``). Turn ONE encoder detent at a normal pace: a clean detent is
a single ``bitK↑``; contact bounce shows up as two or more ``bitK↑`` a few ms apart.
Read off the largest bounce gap you see and set the controller's _ENCODER_DEBOUNCE
just above it (in src/.../mapping/radio_panel.py). Stop the mapper first — it holds
the same hidraw node open.

Ctrl-C to quit. Linux-only, reads /dev/hidraw directly (06a3 nodes are 0666).
"""

from __future__ import annotations

import os
import select
import sys
import time

PRODUCT = 0x0D05  # Radio Panel
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
    sys.exit(f"Radio Panel ({VENDOR:#06x}:{PRODUCT:#06x}) not found under {SYS}")


def fmt(data: bytes) -> str:
    return " ".join(f"{b:02x}" for b in data)


def bits(data: bytes) -> str:
    return " ".join(f"{b:08b}"[::-1] for b in data)  # LSB-first so bit0 is leftmost


def changed_bits(prev: bytes, cur: bytes, last_up: dict[int, float], now: float) -> list[str]:
    """Format changed bit indices; annotate each ↑ with the gap since its last ↑.

    ``last_up`` maps bit index -> monotonic time of that bit's previous rising edge
    and is updated in place, so a bouncing detent (several ↑ a few ms apart on the
    same bit) prints small ``Δ`` gaps and the debounce window can be read off them.
    """
    out: list[str] = []
    for i in range(max(len(prev), len(cur))):
        p = prev[i] if i < len(prev) else 0
        c = cur[i] if i < len(cur) else 0
        diff = p ^ c
        for bit in range(8):
            mask = 1 << bit
            if not diff & mask:
                continue
            idx = i * 8 + bit
            if c & mask:  # rising edge
                gap = now - last_up[idx] if idx in last_up else None
                last_up[idx] = now
                out.append(f"bit{idx}↑" + (f" (Δ {gap * 1000:.1f}ms)" if gap is not None else ""))
            else:
                out.append(f"bit{idx}↓")
    return out


def main() -> None:
    path = find_node()
    print(f"Reading {path} (Radio Panel). Operate one control at a time. Ctrl-C to quit.\n")
    fd = os.open(path, os.O_RDONLY)
    prev: bytes | None = None
    last_up: dict[int, float] = {}  # bit index -> monotonic time of its last ↑
    last_change: float | None = None
    try:
        while True:
            select.select([fd], [], [])
            data = os.read(fd, 64)
            if not data:
                continue
            now = time.monotonic()
            if prev is None:
                prev = data
                print(f"baseline (idle): hex[{fmt(data)}]  bits[{bits(data)}]\n")
                continue
            if data == prev:
                continue
            marks = ", ".join(changed_bits(prev, data, last_up, now))
            marks = marks or "(no bit diff — length/other)"
            gap_ms = (now - last_change) * 1000 if last_change is not None else None
            since = f"+{gap_ms:6.1f}ms" if gap_ms is not None else "   start "
            print(f"{since}  hex[{fmt(data)}]  changed: {marks}")
            prev = data
            last_change = now
    except KeyboardInterrupt:
        print("\nbye")
    finally:
        os.close(fd)


if __name__ == "__main__":
    main()
