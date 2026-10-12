#!/usr/bin/env python3
"""Does a tone at level 0 still cost a voice? Polyphony-exhaustion test.

The JUNO-DS has 128 voices and, with Patch Priority = LAST, steals the oldest
note when they run out. The test holds a low probe note (C2, sine), then adds
quiet high filler notes one by one and records when the probe is cut off:

    probe lost at filler k  ->  the patch costs about 128 / (k - 1) voices per note

Three versions of the same patch are measured (tone 1 is always ON, level 127):

    all4    tones 2-4 ON, level 127   control: expect ~4 voices/note (lost at ~33)
    level0  tones 2-4 ON, level 0     the question
    off     tones 2-4 switched OFF    control: expect 1 voice/note (never lost)

If level0 behaves like all4, level 0 still uses voices and switching silent
tones off would save polyphony. If it behaves like off, nothing to gain.

Uses the temporary patch (PATCH mode): re-select your patch afterwards.

    python tools/voice_count_test.py              # record from the USB audio input
    python tools/voice_count_test.py --listen     # no recording: listen for C2 dropping out
"""

from __future__ import annotations

import argparse
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import mido

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.spectre.core.midi import MidiDeviceManager
from src.spectre.core.protocol import JunoClient, SoundMode
from src.spectre.core.sysex import (
    ADDR_SYSTEM,
    OFFSET_PATCH_COMMON_CHORUS,
    OFFSET_PATCH_COMMON_MFX,
    OFFSET_PATCH_COMMON_REVERB,
    OFFSET_PATCH_TMT,
    OFFSET_PATCH_TONE_1,
    OFFSET_PATCH_TONE_2,
    OFFSET_PATCH_TONE_3,
    OFFSET_PATCH_TONE_4,
    PATCH_PARAM_ATTACK_OFFSET,
    PATCH_PARAM_CUTOFF_OFFSET,
    PATCH_PARAM_LEVEL,
    PATCH_PARAM_MONO_POLY,
    PATCH_PARAM_RELEASE_OFFSET,
    PATCH_PARAM_RESONANCE_OFFSET,
    TONE_PARAM_CHORUS_SEND,
    TONE_PARAM_COARSE_TUNE,
    TONE_PARAM_DRY_SEND,
    TONE_PARAM_FINE_TUNE,
    TONE_PARAM_LEVEL,
    TONE_PARAM_LFO1_PAN_DEPTH,
    TONE_PARAM_LFO1_PITCH_DEPTH,
    TONE_PARAM_LFO1_TVA_DEPTH,
    TONE_PARAM_LFO1_TVF_DEPTH,
    TONE_PARAM_LFO2_PAN_DEPTH,
    TONE_PARAM_LFO2_PITCH_DEPTH,
    TONE_PARAM_LFO2_TVA_DEPTH,
    TONE_PARAM_LFO2_TVF_DEPTH,
    TONE_PARAM_PAN,
    TONE_PARAM_PITCH_ENV_DEPTH,
    TONE_PARAM_REVERB_SEND,
    TONE_PARAM_TVA_VEL_CURVE,
    TONE_PARAM_TVA_VEL_SENS,
    TONE_PARAM_TVF_CUTOFF,
    TONE_PARAM_TVF_ENV_DEPTH,
    TONE_PARAM_TVF_FILTER_TYPE,
    TONE_PARAM_TVF_RESONANCE,
    TONE_PARAM_WAVE_FXM_SWITCH,
    TONE_PARAM_WAVE_GAIN,
    TONE_PARAM_WAVE_GROUP_ID,
    TONE_PARAM_WAVE_GROUP_TYPE,
    TONE_PARAM_WAVE_NUM_L,
    TONE_PARAM_WAVE_NUM_R,
    add_address,
    pack_4nibbles,
)

PATCH_PARAM_PRIORITY = 0x0010  # 0 = LAST (oldest note stolen first), 1 = LOUDEST
TONES = (OFFSET_PATCH_TONE_1, OFFSET_PATCH_TONE_2, OFFSET_PATCH_TONE_3, OFFSET_PATCH_TONE_4)
SINE_WAVE = 625                # INT-A "Sine": mono, so one voice per tone
PROBE_NOTE, PROBE_VEL = 36, 127
FILLERS = list(range(60, 128))  # 68 notes, all well above the probe's 65 Hz
FILLER_VEL = 8
VOICES = 128
SCENARIOS = {
    "all4": ("tones 2-4 ON at level 127", True, 127),
    "level0": ("tones 2-4 ON at level 0", True, 0),
    "off": ("tones 2-4 switched OFF", False, 127),
}


def patch_channel(client: JunoClient) -> int:
    """System Kbd Patch Rx/Tx channel (mido numbering), channel 1 if unreadable."""
    data = client.request_data(add_address(ADDR_SYSTEM, 0x000A), (0, 0, 0, 1), timeout=0.5)
    return int(data[0]) if data and 0 <= data[0] <= 15 else 0


def setup_patch(client: JunoClient) -> None:
    """Four identical dry sine tones, no FX, flat gate envelope, steep velocity."""
    base = client.get_active_patch_base()
    send = lambda off, vals: client.send_data(add_address(base, off), vals)
    for p in (PATCH_PARAM_CUTOFF_OFFSET, PATCH_PARAM_RESONANCE_OFFSET,
              PATCH_PARAM_ATTACK_OFFSET, PATCH_PARAM_RELEASE_OFFSET):
        send(p, [64])
    send(PATCH_PARAM_LEVEL, [100])
    send(PATCH_PARAM_PRIORITY, [0])
    send(PATCH_PARAM_MONO_POLY, [1])
    client.send_data(add_address(base, OFFSET_PATCH_COMMON_MFX), [0, 127, 0, 0])
    client.send_data(add_address(base, OFFSET_PATCH_COMMON_CHORUS), [0, 0])
    client.send_data(add_address(base, OFFSET_PATCH_COMMON_REVERB), [0, 0])

    tmt = add_address(base, OFFSET_PATCH_TMT)
    client.send_data(add_address(tmt, 0x0000), [0, 0, 0, 0])  # structures, boosters
    client.send_data(add_address(tmt, 0x0004), [0])           # velocity control OFF
    for i in range(4):  # switch, key range 0..127, fade 0, velocity range 1..127, fade 0
        client.send_data(add_address(tmt, 0x0005 + 9 * i), [1, 0, 127, 0, 0, 1, 127, 0, 0])

    for off in TONES:
        t = add_address(base, off)
        tsend = lambda p, vals: client.send_data(add_address(t, p), vals)
        tsend(TONE_PARAM_LEVEL, [127])
        tsend(TONE_PARAM_COARSE_TUNE, [64])
        tsend(TONE_PARAM_FINE_TUNE, [64])
        tsend(TONE_PARAM_PAN, [64])
        tsend(0x0008, [1, 0, 0, 0])            # env mode SUSTAIN, no delay
        tsend(TONE_PARAM_DRY_SEND, [127])
        tsend(TONE_PARAM_CHORUS_SEND, [0])
        tsend(TONE_PARAM_REVERB_SEND, [0])
        tsend(0x0011, [0])                     # output assign MFX (thru)
        tsend(TONE_PARAM_WAVE_GROUP_TYPE, [0])
        tsend(TONE_PARAM_WAVE_GROUP_ID, pack_4nibbles(1))  # INT-A
        tsend(TONE_PARAM_WAVE_NUM_L, pack_4nibbles(SINE_WAVE))
        tsend(TONE_PARAM_WAVE_NUM_R, pack_4nibbles(0))     # mono
        tsend(TONE_PARAM_WAVE_GAIN, [1])       # 0 dB
        tsend(TONE_PARAM_WAVE_FXM_SWITCH, [0])
        tsend(TONE_PARAM_PITCH_ENV_DEPTH, [64])
        tsend(TONE_PARAM_TVF_FILTER_TYPE, [0])
        tsend(TONE_PARAM_TVF_CUTOFF, [127])
        tsend(TONE_PARAM_TVF_RESONANCE, [0])
        tsend(TONE_PARAM_TVF_ENV_DEPTH, [64])
        tsend(TONE_PARAM_TVA_VEL_CURVE, [1])
        tsend(TONE_PARAM_TVA_VEL_SENS, [127])  # +63: fillers at velocity 8 stay quiet
        tsend(0x0066, [0, 0, 0, 0])            # TVA T1..T4
        tsend(0x006A, [127, 127, 127])         # TVA L1..L3
        for p in (TONE_PARAM_LFO1_PITCH_DEPTH, TONE_PARAM_LFO1_TVF_DEPTH, TONE_PARAM_LFO1_TVA_DEPTH,
                  TONE_PARAM_LFO1_PAN_DEPTH, TONE_PARAM_LFO2_PITCH_DEPTH, TONE_PARAM_LFO2_TVF_DEPTH,
                  TONE_PARAM_LFO2_TVA_DEPTH, TONE_PARAM_LFO2_PAN_DEPTH):
            tsend(p, [64])
    time.sleep(0.1)


def apply_scenario(client: JunoClient, switch: bool, level: int) -> None:
    base = client.get_active_patch_base()
    tmt = add_address(base, OFFSET_PATCH_TMT)
    for i, off in enumerate(TONES[1:], start=1):
        client.send_data(add_address(tmt, 0x0005 + 9 * i), [1 if switch else 0])
        client.send_data(add_address(add_address(base, off), TONE_PARAM_LEVEL), [level])
    time.sleep(0.1)


def play(mgr: MidiDeviceManager, ch: int, lead: float, step: float, verbose: bool) -> None:
    out = mgr.juno_out
    out.send(mido.Message("note_on", note=PROBE_NOTE, velocity=PROBE_VEL, channel=ch))
    if verbose:
        print(f"  probe C2 on (note {PROBE_NOTE})", flush=True)
    time.sleep(lead)
    for k, n in enumerate(FILLERS, start=1):
        out.send(mido.Message("note_on", note=n, velocity=FILLER_VEL, channel=ch))
        if verbose:
            print(f"  filler {k:2d}  (~{VOICES / k:.1f} voices/note if C2 drops now)", flush=True)
        time.sleep(step)
    time.sleep(0.5)
    for n in [PROBE_NOTE] + FILLERS:
        out.send(mido.Message("note_off", note=n, velocity=0, channel=ch))
    mgr.send_all_notes_off(cut_sound=True)
    time.sleep(0.3)


def record(session, fn):
    import numpy as np
    from scipy.io import wavfile

    if session.rec_file.exists():
        session.rec_file.unlink()
    proc = subprocess.Popen(session.cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.4)
    try:
        fn()
    finally:
        proc.send_signal(signal.SIGINT)
        try:
            proc.wait(timeout=2.0)
        except Exception:
            proc.kill()
    sr, data = wavfile.read(str(session.rec_file))
    x = data.astype(np.float64)
    return sr, x.mean(axis=1) if x.ndim > 1 else x


def probe_envelope(sr: int, x, hop_s: float = 0.01, win_s: float = 0.08):
    """Amplitude of the probe's fundamental over time (Hann-windowed single DFT bin)."""
    import numpy as np

    f = 440.0 * 2 ** ((PROBE_NOTE - 69) / 12)
    win, hop = int(win_s * sr), int(hop_s * sr)
    if len(x) < win:
        return np.array([]), np.array([])
    w = np.hanning(win)
    kern = w * np.exp(-2j * np.pi * f * np.arange(win) / sr)
    starts = np.arange(0, len(x) - win, hop)
    frames = np.lib.stride_tricks.sliding_window_view(x, win)[starts]
    return (starts + win / 2) / sr, np.abs(frames @ kern)


def analyse(sr: int, x, lead: float, step: float) -> str:
    import numpy as np

    t, a = probe_envelope(sr, x)
    if not len(a) or a.max() <= 0:
        return "no audio captured"
    onset_i = int(np.argmax(a > 0.3 * a.max()))
    onset = t[onset_i]
    ref_mask = (t > onset + 0.1) & (t < onset + lead - 0.05)
    ref = float(np.median(a[ref_mask])) if ref_mask.any() else float(a[onset_i])
    after = (t > onset + lead) & (a < 0.5 * ref)
    if not after.any():
        return f"probe kept through all {len(FILLERS)} fillers  ->  ~1 voice/note (<= {VOICES / (len(FILLERS) + 1):.1f})"
    lost_t = t[int(np.argmax(after))]
    k = int((lost_t - onset - lead) // step) + 1
    vpn = VOICES / max(1, k - 1)
    return f"probe lost at filler {k}  ->  ~{vpn:.1f} voices/note"


def switch_test(client: JunoClient, mgr: MidiDeviceManager, ch: int, pause: float) -> None:
    """Listen: what a Tone Switch change does to notes already held.

    Tone 2 is a fifth above tone 1, so it is heard as a G over a held C.
    """
    base = client.get_active_patch_base()
    tmt = add_address(base, OFFSET_PATCH_TMT)
    t2 = add_address(base, OFFSET_PATCH_TONE_2)
    out = mgr.juno_out

    def tone2(switch=None, level=None):
        if switch is not None:
            client.send_data(add_address(tmt, 0x0005 + 9), [1 if switch else 0])
        if level is not None:
            client.send_data(add_address(t2, TONE_PARAM_LEVEL), [level])

    def note(n, on=True, vel=100):
        out.send(mido.Message("note_on" if on else "note_off", note=n, velocity=vel if on else 0, channel=ch))

    def step(text):
        print(f"  {text}", flush=True)
        time.sleep(pause)

    def reset():
        mgr.send_all_notes_off(cut_sound=True)
        time.sleep(0.5)

    setup_patch(client)
    for off in TONES[2:]:
        client.send_data(add_address(tmt, 0x0005 + 9 * TONES.index(off)), [0])
    client.send_data(add_address(t2, TONE_PARAM_COARSE_TUNE), [64 + 7])

    print("[A] level change on a held note (what the engines do today)")
    tone2(switch=True, level=0)
    note(60)
    step("holding C4, tone 2 ON at level 0: only C")
    tone2(level=127)
    step("tone 2 level -> 127: does G join the held C?")
    reset()

    print("[B] switch ON on a held note")
    tone2(switch=False, level=127)
    note(60)
    step("holding C4, tone 2 OFF: only C")
    tone2(switch=True)
    step("tone 2 switched ON: does G join the held C?")
    note(64)
    step("new note E4: should bring its B (proves tone 2 is on)")
    tone2(switch=False)
    step("tone 2 switched OFF: do G and B stop now, or ring until release?")
    note(60, on=False)
    note(64, on=False)
    reset()

    print("[C] does switching OFF free the held notes' voices?")
    tone2(switch=True, level=127)
    for off in TONES[2:]:
        client.send_data(add_address(tmt, 0x0005 + 9 * TONES.index(off)), [1])
    note(PROBE_NOTE, vel=127)
    for n in FILLERS[:31]:  # probe + 31 fillers = 32 notes x 4 tones = 128 voices
        note(n, vel=FILLER_VEL)
        time.sleep(0.05)
    step("holding C2 + 31 quiet notes on 4 tones: all 128 voices in use")
    for i in (1, 2, 3):
        client.send_data(add_address(tmt, 0x0005 + 9 * i), [0])
    step("tones 2-4 switched OFF")
    for k, n in enumerate(FILLERS[31:47], start=1):
        note(n, vel=FILLER_VEL)
        print(f"  extra note {k:2d}", flush=True)
        time.sleep(0.4)
    step("C2 still there = voices were freed; gone at extra note 1 = still held")
    reset()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--listen", action="store_true", help="No recording: play slowly, listen for C2 dropping out")
    ap.add_argument("--switch", action="store_true", help="Listen: Tone Switch changes on held notes")
    ap.add_argument("--pause", type=float, default=3.0, help="Seconds per --switch step (default 3)")
    ap.add_argument("--only", choices=list(SCENARIOS), action="append", help="Run only these scenarios")
    ap.add_argument("--midi-ch", type=int, default=None, help="Patch receive channel 1-16 (default: auto)")
    ap.add_argument("--device", default="auto", help="Audio capture device (as in dump_waveforms.py)")
    ap.add_argument("--step", type=float, default=None, help="Seconds between fillers (default 0.12, listen 0.4)")
    ap.add_argument("--keep-wav", default=None, help="Folder to keep each scenario's recording")
    args = ap.parse_args()
    step = args.step or (0.4 if args.listen else 0.12)
    lead = 1.0 if args.listen else 0.6

    mgr = MidiDeviceManager()
    mgr.connect_juno()
    client = JunoClient(mgr)
    if client.get_sound_mode(force_refresh=True) != SoundMode.PATCH:
        input("The synth is not in PATCH mode. Press Enter to switch it (Ctrl+C to stop)... ")
        client.set_sound_mode(SoundMode.PATCH)
        time.sleep(0.5)
        client.get_sound_mode(force_refresh=True)
    ch = args.midi_ch - 1 if args.midi_ch else patch_channel(client)
    if args.switch:
        print(f"MIDI channel {ch + 1}. This overwrites the temporary patch; re-select your patch afterwards.\n")
        try:
            switch_test(client, mgr, ch, args.pause)
        finally:
            mgr.send_all_notes_off(cut_sound=True)
        return
    session = None
    if not args.listen:  # numpy/scipy only needed for the recorded run
        from tools.dump_waveforms import AudioCaptureSession
        session = AudioCaptureSession(args.device)
    print(f"MIDI channel {ch + 1}" + ("" if session is None else f" | audio: {session.backend_desc}"))
    print("This overwrites the temporary patch; re-select your patch afterwards.\n")

    setup_patch(client)
    results = {}
    try:
        for name in args.only or list(SCENARIOS):
            desc, switch, level = SCENARIOS[name]
            print(f"[{name}] {desc}", flush=True)
            apply_scenario(client, switch, level)
            if session is None:
                play(mgr, ch, lead, step, verbose=True)
                continue
            sr, x = record(session, lambda: play(mgr, ch, lead, step, verbose=False))
            if args.keep_wav:
                Path(args.keep_wav).mkdir(parents=True, exist_ok=True)
                shutil.copy(session.rec_file, Path(args.keep_wav) / f"voices_{name}.wav")
            results[name] = analyse(sr, x, lead, step)
            print(f"  {results[name]}\n", flush=True)
    finally:
        mgr.send_all_notes_off(cut_sound=True)

    if results:
        print("Summary")
        for name, res in results.items():
            print(f"  {name:7s} {SCENARIOS[name][0]:28s} {res}")


if __name__ == "__main__":
    main()
