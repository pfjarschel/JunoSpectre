#!/usr/bin/env python3
"""Capture the active temporary patch RAM from the keyboard as the JUNO SPECTRE init template blob.

Select the template patch on the synth (PATCH mode), then run:
    python scripts/capture_init_template.py

The script reads every patch region (Common, MFX, Chorus, Reverb, TMT, Tones 1-4)
via RQR requests and writes the golden image to src/spectre/assets/init_template.json.
The patch is the source of truth: the image is preserved byte-for-byte; the only
overlays are the canonical name and a safety net enforcing tone SUSTAIN env mode.
Use --raw to skip even those.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.spectre.core.midi import MidiDeviceManager
from src.spectre.core.protocol import JunoClient
from src.spectre.core.sysex import (
    add_address,
    OFFSET_PATCH_COMMON,
    OFFSET_PATCH_COMMON_CHORUS,
    OFFSET_PATCH_COMMON_MFX,
    OFFSET_PATCH_COMMON_REVERB,
    OFFSET_PATCH_TMT,
    OFFSET_PATCH_TONE_1,
    OFFSET_PATCH_TONE_2,
    OFFSET_PATCH_TONE_3,
    OFFSET_PATCH_TONE_4,
    TONE_PARAM_ENV_MODE,
)

DEFAULT_OUTPUT = PROJECT_ROOT / "src" / "spectre" / "assets" / "init_template.json"
INIT_PATCH_NAME = "JUNO SPECTRE"

# region key -> (offset tuple relative to patch base, [(chunk start, nominal length), ...])
# Nominal lengths are overridden by the device-clamped readback when shorter (auto-detected).
REGIONS: dict[str, tuple[tuple[int, int, int, int], list[tuple[int, int]]]] = {
    "common": (OFFSET_PATCH_COMMON, [(0x000, 0x50)]),
    "mfx":    (OFFSET_PATCH_COMMON_MFX, [(0x000, 0x49)]),
    "chorus": (OFFSET_PATCH_COMMON_CHORUS, [(0x000, 0x28)]),
    "reverb": (OFFSET_PATCH_COMMON_REVERB, [(0x000, 0x27)]),
    "tmt":    (OFFSET_PATCH_TMT, [(0x000, 0x29)]),
    "tone_1": (OFFSET_PATCH_TONE_1, [(0x000, 0x9A), (0x100, 0x1A)]),
    "tone_2": (OFFSET_PATCH_TONE_2, [(0x000, 0x9A), (0x100, 0x1A)]),
    "tone_3": (OFFSET_PATCH_TONE_3, [(0x000, 0x9A), (0x100, 0x1A)]),
    "tone_4": (OFFSET_PATCH_TONE_4, [(0x000, 0x9A), (0x100, 0x1A)]),
}

# Generous request size used to discover each chunk's true extent (device clamps RQ1
# responses to the valid contiguous region and answers with the whole block in one RPD).
_PROBE_SIZE = 0x200


def size7(n: int) -> tuple[int, int, int, int]:
    """Encode a byte count as 4 Roland 7-bit size bytes."""
    return ((n >> 21) & 0x7F, (n >> 14) & 0x7F, (n >> 7) & 0x7F, n & 0x7F)


def read_region(client: JunoClient, base, offset, chunks, timeout=2.5, retries=2):
    """Read one region: probe each chunk's true extent (device clamps RQ1 to the
    valid contiguous area), then validate that it covers the nominal minimum."""
    out = []
    region_addr = add_address(base, offset)
    for start, length in chunks:
        addr = add_address(region_addr, start)
        data = None
        for attempt in range(retries + 1):
            data = client.request_data(addr, size7(_PROBE_SIZE), timeout=timeout)
            if data is not None and len(data) >= length:
                break
            time.sleep(0.05)
        if data is None or len(data) < length:
            got = 0 if data is None else len(data)
            raise RuntimeError(
                f"Region {offset} chunk 0x{start:03X}: need {length} bytes, area returned {got}"
            )
        if len(data) > _PROBE_SIZE:
            raise RuntimeError(
                f"Region {offset} chunk 0x{start:03X}: unclamped area {len(data)} bytes exceeds probe window"
            )
        out.append((start, bytes(data)))
    return out


def chunk0(regions: dict, key: str) -> bytearray:
    """Mutable view of a region's first chunk."""
    return bytearray(regions[key][0][1])


def overlay_name(regions: dict) -> str:
    b = chunk0(regions, "common")
    old = bytes(b[0:12])
    b[0:12] = INIT_PATCH_NAME.encode("ascii", errors="replace")[:12].ljust(12, b" ")
    regions["common"][0] = (0x000, bytes(b))
    return f"name {old!r} -> {INIT_PATCH_NAME!r}"


def overlay_force_sustain(regions: dict) -> str:
    changes = []
    for key in ("tone_1", "tone_2", "tone_3", "tone_4"):
        b = chunk0(regions, key)
        if b[TONE_PARAM_ENV_MODE] != 1:
            changes.append(f"{key} env_mode {b[TONE_PARAM_ENV_MODE]}->1")
            b[TONE_PARAM_ENV_MODE] = 1
            regions[key][0] = (0x000, bytes(b))
    return "; ".join(changes) if changes else "all tones already SUSTAIN"


OVERLAYS: list[Callable[[dict], str]] = [
    overlay_name,
    overlay_force_sustain,
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT, help="Output JSON asset path")
    parser.add_argument("--raw", action="store_true", help="Skip normalization overlays (pure snapshot)")
    args = parser.parse_args()

    mgr = MidiDeviceManager()
    mgr.connect_juno()
    client = JunoClient(mgr)
    try:
        mode = client.get_sound_mode(timeout=2.0)
        if mode.name != "PATCH":
            print(f"ERROR: synth must be in PATCH mode (currently {mode.name}).")
            return 1
        base = client.get_active_patch_base(timeout=2.0)
        source_name = client.get_patch_name(timeout=2.0)
        print(f"Capturing from patch {source_name!r} (base {[hex(b) for b in base]})...")

        regions = {}
        for key, (offset, chunks) in REGIONS.items():
            regions[key] = read_region(client, base, offset, chunks)
            total = sum(len(b) for _, b in regions[key])
            print(f"  {key:8s} offset={[hex(x) for x in offset]}  {total} bytes OK")

        if not args.raw:
            print("Applying overlays:")
            for overlay in OVERLAYS:
                print(f"  - {overlay(regions)}")

        payload = {
            "version": 1,
            "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source_patch_name": source_name,
            "sound_mode": "PATCH",
            "patch_base_address": list(base),
            "overlays_applied": not args.raw,
            "regions": {
                key: {
                    "offset": list(offset),
                    "chunks": [{"start": start, "bytes": list(data)} for start, data in chunks],
                }
                for key, (offset, _), chunks in (
                    (k, REGIONS[k], regions[k]) for k in REGIONS
                )
            },
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
        total_bytes = sum(len(b) for _, chunks in regions.items() for _, b in chunks)
        print(f"Wrote {args.out} ({total_bytes} bytes, {len(regions)} regions)")
        return 0
    finally:
        mgr.close()


if __name__ == "__main__":
    sys.exit(main())
