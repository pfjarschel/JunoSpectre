import os
import sys
import time
import subprocess
from pathlib import Path
import numpy as np
from scipy.io import wavfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.spectre.core.midi import MidiDeviceManager
from src.spectre.core.protocol import JunoClient
from src.spectre.core.sysex import (
    add_address,
    OFFSET_PATCH_TONE_1,
    OFFSET_PATCH_TONE_2,
    OFFSET_PATCH_TONE_3,
    OFFSET_PATCH_TONE_4,
    TONE_PARAM_LEVEL,
    TONE_PARAM_WAVE_GROUP_TYPE,
    TONE_PARAM_WAVE_GROUP_ID,
    TONE_PARAM_WAVE_NUM_L,
    TONE_PARAM_WAVE_NUM_R,
    TONE_PARAM_WAVE_GAIN,
    TONE_PARAM_TVF_FILTER_TYPE,
    TONE_PARAM_TVF_CUTOFF,
    TONE_PARAM_TVF_RESONANCE,
    TONE_PARAM_TVA_LEVEL,
    TONE_PARAM_DRY_SEND,
    TONE_PARAM_CHORUS_SEND,
    TONE_PARAM_REVERB_SEND,
    pack_4nibbles,
)
import mido


def prepare_feeder_patch(client: JunoClient):
    """Configure Tone 1 as flat pure wave feeder, mute Tones 2, 3, 4."""
    base = client.get_active_patch_base()
    
    # 1. Mute Tones 2, 3, 4
    for offset in [OFFSET_PATCH_TONE_2, OFFSET_PATCH_TONE_3, OFFSET_PATCH_TONE_4]:
        addr = add_address(base, offset)
        client.send_data(add_address(addr, TONE_PARAM_LEVEL), [0])

    # 2. Configure Tone 1 as 100% clean feeder
    t1_addr = add_address(base, OFFSET_PATCH_TONE_1)
    
    # Level = 127
    client.send_data(add_address(t1_addr, TONE_PARAM_LEVEL), [127])
    # Wave Gain = 1 (0 dB)
    client.send_data(add_address(t1_addr, TONE_PARAM_WAVE_GAIN), [1])
    # Filter Type = 0 (OFF / Bypass)
    client.send_data(add_address(t1_addr, TONE_PARAM_TVF_FILTER_TYPE), [0])
    # Cutoff = 127
    client.send_data(add_address(t1_addr, TONE_PARAM_TVF_CUTOFF), [127])
    # Resonance = 0
    client.send_data(add_address(t1_addr, TONE_PARAM_TVF_RESONANCE), [0])
    # Dry Send = 127, Chorus = 0, Reverb = 0
    client.send_data(add_address(t1_addr, TONE_PARAM_DRY_SEND), [127])
    client.send_data(add_address(t1_addr, TONE_PARAM_CHORUS_SEND), [0])
    client.send_data(add_address(t1_addr, TONE_PARAM_REVERB_SEND), [0])
    
    print("Feeder patch configured (Tone 1 pure, Tones 2-4 muted, filter bypassed).")


def sample_wave(mgr: MidiDeviceManager, client: JunoClient, bank_id: int, wave_num: int, out_wav: Path, note: int = 60, dur: float = 0.5):
    """Select wave on Tone 1, trigger note, and record audio via Scarlett Solo."""
    base = client.get_active_patch_base()
    t1_addr = add_address(base, OFFSET_PATCH_TONE_1)

    # Set Wave Group Type = 0 (INT), Group ID = bank_id (0: INTA, 1: INTB)
    client.send_data(add_address(t1_addr, TONE_PARAM_WAVE_GROUP_TYPE), [0])
    client.send_data(add_address(t1_addr, TONE_PARAM_WAVE_GROUP_ID), pack_4nibbles(bank_id))
    client.send_data(add_address(t1_addr, TONE_PARAM_WAVE_NUM_L), pack_4nibbles(wave_num))
    client.send_data(add_address(t1_addr, TONE_PARAM_WAVE_NUM_R), pack_4nibbles(0))
    time.sleep(0.04) # DSP latch

    rec_time = dur + 0.2
    proc = subprocess.Popen([
        "arecord", "-D", "sysdefault:CARD=USB",
        "-d", str(int(rec_time + 1)),
        "-f", "S32_LE", "-r", "48000",
        str(out_wav)
    ], stderr=subprocess.PIPE)
    time.sleep(0.05)

    # Note On
    mgr.juno_out.send(mido.Message("note_on", note=note, velocity=100, channel=0))
    time.sleep(dur)
    mgr.juno_out.send(mido.Message("note_off", note=note, velocity=0, channel=0))
    
    time.sleep(0.15)
    proc.terminate()
    proc.wait()


if __name__ == "__main__":
    mgr = MidiDeviceManager()
    in_n, out_n = mgr.connect_juno()
    client = JunoClient(mgr)
    
    prepare_feeder_patch(client)
    
    out_dir = Path(__file__).resolve().parent.parent / "src" / "spectre" / "assets" / "samples"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Test sample Wave 1 from INTA
    test_wav = out_dir / "test_INTA_0001.wav"
    print(f"Sampling INTA Wave 1 to {test_wav}...")
    sample_wave(mgr, client, bank_id=0, wave_num=1, out_wav=test_wav)
    
    if test_wav.exists():
        sr, data = wavfile.read(test_wav)
        peak = np.max(np.abs(data)) / (2**31 - 1)
        print(f"Recorded successfully! Size: {len(data)} samples ({len(data)/sr:.2f}s), Peak: {peak*100:.1f}%")
