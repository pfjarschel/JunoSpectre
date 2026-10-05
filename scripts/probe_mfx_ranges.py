"""Probe real MFX raw parameter ranges from a connected JUNO-DS.

For every MFX type, reads default raw values after the type change, then
writes extreme values to each parameter and reads back the clamped result.
Output: JSON {type: {"def": [...], "min": [...], "max": [...]}} (raw offsets
relative to 32768).
"""
import json
import sys
import time

sys.path.insert(0, "src")
from spectre.core.midi import MidiDeviceManager  # noqa: E402
from spectre.core.protocol import JunoClient  # noqa: E402

LO, HI = -20000, 20000


def main(out_path):
    midi = MidiDeviceManager()
    midi.connect_juno()
    juno = JunoClient(midi)
    result = {}
    for t in range(1, 81):
        juno.set_mfx(t)
        time.sleep(0.15)
        _, _, _, _, defaults = juno.read_mfx()
        for i in range(32):
            juno.set_mfx_param(i, HI)
        time.sleep(0.1)
        _, _, _, _, mx = juno.read_mfx()
        for i in range(32):
            juno.set_mfx_param(i, LO)
        time.sleep(0.1)
        _, _, _, _, mn = juno.read_mfx()
        result[t] = {"def": defaults, "min": mn, "max": mx}
        print(t, defaults[:6], mn[:6], mx[:6], flush=True)
    juno.set_mfx(0)
    with open(out_path, "w") as f:
        json.dump(result, f)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/mfx_ranges.json")
