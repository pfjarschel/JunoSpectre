"""Scan JUNO-DS patches via program change; record MFX type + raw params."""
import json
import sys
import time

import mido

sys.path.insert(0, "src")
from spectre.core.midi import MidiDeviceManager  # noqa: E402
from spectre.core.protocol import JunoClient  # noqa: E402


def main(out_path):
    midi = MidiDeviceManager()
    midi.connect_juno()
    juno = JunoClient(midi)
    found = {}
    banks = [(87, lsb) for lsb in range(64, 72)] + [(85, 0), (85, 1)]
    for msb, lsb in banks:
        n_banks = 0
        for pc in range(128):
            midi.juno_out.send(mido.Message("control_change", channel=0, control=0, value=msb))
            midi.juno_out.send(mido.Message("control_change", channel=0, control=32, value=lsb))
            midi.juno_out.send(mido.Message("program_change", channel=0, program=pc))
            time.sleep(0.08)
            juno._cached_patch_base = None
            try:
                t, _, _, _, params = juno.read_mfx(timeout=0.5)
                name = juno.get_patch_name(timeout=0.5)
            except Exception as e:  # noqa: BLE001
                print("err", msb, lsb, pc, e, flush=True)
                continue
            if t > 0:
                found.setdefault(t, []).append({"name": name, "bank": [msb, lsb], "pc": pc, "p": params})
                n_banks += 1
        print("bank", msb, lsb, "mfx patches:", n_banks, "types so far:", len(found), flush=True)
        with open(out_path, "w") as f:
            json.dump(found, f)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/mfx_patches.json")
