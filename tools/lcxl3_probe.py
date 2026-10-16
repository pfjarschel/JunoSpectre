#!/usr/bin/env python3
"""Launch Control XL3 DAW-mode probe (checks for docs/LCXL3_LAYOUT.md).

Puts the LCXL3 in DAW mode, optionally turns on touch events, and prints every
message it sends, on both its MIDI and DAW ports. Ctrl+C leaves DAW mode.
Close the app first: it uses the same ports.

    python tools/lcxl3_probe.py                 # DAW Control mode, print everything
    python tools/lcxl3_probe.py --touch         # + touch events (ch15 on/off)
    python tools/lcxl3_probe.py --led 116 5     # + palette colour 5 on Play (118 = Record)
    python tools/lcxl3_probe.py --screen "CTX - SCENE 3"   # + permanent screen title line
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import mido

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from spectre.control import lcxl3  # noqa: E402


def _port(names: list[str], key: str) -> str | None:
    return next((n for n in names if "LCXL3" in n and key in n), None)


def _hex(msg: mido.Message) -> str:
    return " ".join(f"{b:02X}" for b in msg.bytes())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--touch", action="store_true", help="enable DAW touch events (B6 47 7F)")
    ap.add_argument("--mixer", action="store_true", help="start in DAW Mixer mode instead of DAW Control")
    ap.add_argument("--led", nargs=2, type=int, metavar=("CC", "COLOUR"), action="append", default=[],
                    help="set a palette colour on a control's LED (repeatable)")
    ap.add_argument("--screen", help="text for the permanent screen's title line")
    args = ap.parse_args()

    daw_out = _port(mido.get_output_names(), "DAW")
    ins = [n for n in mido.get_input_names() if "LCXL3" in n]
    if not daw_out or not ins:
        print("LCXL3 not found. Inputs:", mido.get_input_names())
        return 1
    out = mido.open_output(daw_out)
    send = lambda hexstr: out.send(mido.Message.from_bytes(bytes.fromhex(hexstr)))  # noqa: E731

    send("9F 0C 7F")                                      # DAW mode on
    send("B6 1E 01" if args.mixer else "B6 1E 02")        # Mixer / Control
    if args.touch:
        send("B6 47 7F")
    for cc, colour in args.led:
        send(f"B0 {cc & 0x7F:02X} {colour & 0x7F:02X}")
    if args.screen:
        out.send(lcxl3.display_config(lcxl3.STATIONARY, stationary=True))
        out.send(lcxl3.display_text(lcxl3.STATIONARY, 0, args.screen))
        print(f"Screen title sent ({len(args.screen)} chars; the title field fits {lcxl3.TEXT_MAX[0]})")

    ports = [mido.open_input(n) for n in ins]
    print("Listening on:", ", ".join(ins), "- Ctrl+C to stop\n")
    try:
        while True:
            for p in ports:
                for msg in p.iter_pending():
                    ch = f"ch{msg.channel + 1:<2}" if hasattr(msg, "channel") else "    "
                    print(f"{p.name[:28]:<28} {ch} {_hex(msg)}   {msg}")
            time.sleep(0.002)
    except KeyboardInterrupt:
        pass
    finally:
        if args.touch:
            send("B6 47 00")
        send("9F 0C 00")                                  # DAW mode off
        out.close()
        for p in ports:
            p.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
