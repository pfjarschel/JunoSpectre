#!/usr/bin/env python3
"""Automated Waveform Dumper & Empirical Periodicity Classifier for Roland XPS-30 / JUNO-DS.

Automates SysEx patch initialization, wave selection, note triggering (80 ms burst),
and empirical audio analysis via USB audio interface.
Classifies waves into single-cycle synth oscillators vs acoustic multi-samples based on
cycle-to-cycle cross-correlation and autocorrelation periodicity.
Saves standard 1024-sample wavetables and 64-point UI preview curves for single cycles.
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

import mido
import numpy as np
from scipy.io import wavfile

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.spectre.core.midi import MidiDeviceManager
from src.spectre.core.protocol import JunoClient
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("dump_waveforms")

BANK_MAP = {
    "INTA": 1,  # Group ID 1 = INTA
    "INTB": 2,  # Group ID 2 = INTB
}

BANK_TOTALS = {
    "INTA": 2198,
    "INTB": 184,
}


def detect_synth_midi_channel(client: JunoClient) -> int:
    """Query synth System parameters to detect configured Patch MIDI receive channel."""
    try:
        # Address 0x02 0x00 0x00 0x0A is Kbd Patch Rx/Tx Channel in Roland System Setup
        addr = add_address(ADDR_SYSTEM, 0x000A)
        data = client.request_data(addr, (0, 0, 0, 1), timeout=0.5)
        if data and len(data) > 0:
            ch = int(data[0])
            if 0 <= ch <= 15:
                logger.info(f"Auto-detected synth Patch MIDI receive channel: {ch + 1} (mido ch={ch})")
                return ch
    except Exception as e:
        logger.warning(f"Could not auto-detect MIDI channel via SysEx ({e}). Falling back to Channel 1.")
    return 0  # Default to channel 1 (mido 0)


def init_feeder_patch(client: JunoClient) -> None:
    """Initialize Roland temporary patch buffer to clean, uncolored feeder state.

    Bypasses MFX, Chorus, Reverb, sets Tone 1 to pure flat sustain gate with filter
    bypassed, neutralizes all envelopes/LFOs, and completely mutes Tones 2, 3, and 4.
    """
    logger.info("Initializing temporary patch buffer to raw feeder state...")
    base = client.get_active_patch_base()

    # 1. Reset Patch Common Offsets (Neutralize any macro tweaks)
    client.send_data(add_address(base, PATCH_PARAM_CUTOFF_OFFSET), [64])
    client.send_data(add_address(base, PATCH_PARAM_RESONANCE_OFFSET), [64])
    client.send_data(add_address(base, PATCH_PARAM_ATTACK_OFFSET), [64])
    client.send_data(add_address(base, PATCH_PARAM_RELEASE_OFFSET), [64])

    # 2. Bypass Master Effects (MFX Type = 0 / Thru, Dry Send = 127, Chorus/Reverb = 0)
    mfx_addr = add_address(base, OFFSET_PATCH_COMMON_MFX)
    client.send_data(add_address(mfx_addr, 0x0000), [0, 127, 0, 0])

    chorus_addr = add_address(base, OFFSET_PATCH_COMMON_CHORUS)
    client.send_data(add_address(chorus_addr, 0x0000), [0, 0])  # Chorus OFF

    reverb_addr = add_address(base, OFFSET_PATCH_COMMON_REVERB)
    client.send_data(add_address(reverb_addr, 0x0000), [0, 0])  # Reverb OFF

    # 3. Tone Mix Table (TMT): Tone 1 ON, Tones 2..4 OFF
    tmt_addr = add_address(base, OFFSET_PATCH_TMT)
    client.send_data(add_address(tmt_addr, 0x0000), [0, 0, 0, 0])  # Struct 0, Booster 0
    client.send_data(add_address(tmt_addr, 0x0004), [0])            # Velocity Control = OFF
    # TMT1: Tone Switch = 1 (ON), Key Range C-1..G9 (0..127), Vel Range 1..127
    client.send_data(add_address(tmt_addr, 0x0005), [1, 0, 127, 0, 0, 1, 127, 0, 0])
    # TMT2, TMT3, TMT4: Tone Switch = 0 (OFF)
    client.send_data(add_address(tmt_addr, 0x000E), [0])  # Tone 2 OFF
    client.send_data(add_address(tmt_addr, 0x0017), [0])  # Tone 3 OFF
    client.send_data(add_address(tmt_addr, 0x0020), [0])  # Tone 4 OFF

    # 4. Tone 1: 100% Raw Bypass Feeder
    t1_addr = add_address(base, OFFSET_PATCH_TONE_1)
    client.send_data(add_address(t1_addr, TONE_PARAM_LEVEL), [127])
    client.send_data(add_address(t1_addr, TONE_PARAM_COARSE_TUNE), [64])  # 0 semitones
    client.send_data(add_address(t1_addr, TONE_PARAM_FINE_TUNE), [64])    # 0 cents
    client.send_data(add_address(t1_addr, TONE_PARAM_PAN), [64])          # Center
    client.send_data(add_address(t1_addr, 0x0008), [1, 0, 0, 0])          # Env Mode = 1 (SUSTAIN), Delay = 0
    client.send_data(add_address(t1_addr, TONE_PARAM_DRY_SEND), [127])
    client.send_data(add_address(t1_addr, TONE_PARAM_CHORUS_SEND), [0])
    client.send_data(add_address(t1_addr, TONE_PARAM_REVERB_SEND), [0])
    client.send_data(add_address(t1_addr, 0x0011), [0])                   # Output Assign = 0 (MFX / Main output)
    client.send_data(add_address(t1_addr, TONE_PARAM_WAVE_GAIN), [2])     # +6 dB
    client.send_data(add_address(t1_addr, TONE_PARAM_WAVE_FXM_SWITCH), [0])  # FXM OFF
    client.send_data(add_address(t1_addr, TONE_PARAM_PITCH_ENV_DEPTH), [64]) # Pitch Env Depth = 0

    # TVF: Fully open and bypassed
    client.send_data(add_address(t1_addr, TONE_PARAM_TVF_FILTER_TYPE), [0])  # Filter Bypass
    client.send_data(add_address(t1_addr, TONE_PARAM_TVF_CUTOFF), [127])
    client.send_data(add_address(t1_addr, TONE_PARAM_TVF_RESONANCE), [0])
    client.send_data(add_address(t1_addr, TONE_PARAM_TVF_ENV_DEPTH), [64])   # TVF Env Depth = 0

    # TVA: Flat instant sustain gate (no attack delay, instant release)
    client.send_data(add_address(t1_addr, 0x0066), [0, 0, 0, 0])     # T1..T4 = 0
    client.send_data(add_address(t1_addr, 0x006A), [127, 127, 127]) # L1..L3 = 127

    # LFO 1 & 2: Neutralize all modulation depths
    for p in [TONE_PARAM_LFO1_PITCH_DEPTH, TONE_PARAM_LFO1_TVF_DEPTH, TONE_PARAM_LFO1_TVA_DEPTH, TONE_PARAM_LFO1_PAN_DEPTH]:
        client.send_data(add_address(t1_addr, p), [64])
    for p in [TONE_PARAM_LFO2_PITCH_DEPTH, TONE_PARAM_LFO2_TVF_DEPTH, TONE_PARAM_LFO2_TVA_DEPTH, TONE_PARAM_LFO2_PAN_DEPTH]:
        client.send_data(add_address(t1_addr, p), [64])

    # 5. Completely Mute Tones 2, 3, 4
    for off in [OFFSET_PATCH_TONE_2, OFFSET_PATCH_TONE_3, OFFSET_PATCH_TONE_4]:
        t_addr = add_address(base, off)
        client.send_data(add_address(t_addr, TONE_PARAM_LEVEL), [0])
        client.send_data(add_address(t_addr, TONE_PARAM_DRY_SEND), [0])
        client.send_data(add_address(t_addr, TONE_PARAM_CHORUS_SEND), [0])
        client.send_data(add_address(t_addr, TONE_PARAM_REVERB_SEND), [0])

    time.sleep(0.05)
    logger.info("Feeder patch active: 100% dry, flat, neutral sound path (Tone 1 ON, Tones 2-4 OFF).")


def extract_single_cycle(
    audio_data: np.ndarray,
    sample_rate: int = 48000,
    target_samples: int = 1024,
    min_peak: float = 0.0001,
) -> Tuple[Optional[np.ndarray], float, float, bool, float, float, float, Optional[list[float]]]:
    """Detect fundamental cycle, extract single-cycle wave, and compute 64-point UI preview.

    Uses direct time-domain zero-crossing adaptive extraction:
    1. Dynamic onset detection to skip leading silence or latency.
    2. Autocorrelation over stable burst to find fundamental pitch (60 Hz to 1500 Hz).
    3. Cycle-to-cycle cross-correlation to measure periodicity (cycle_sim, peak_corr, score).
    4. Positive zero-crossing alignment to slice a true physical wave cycle.
       (Falls back to period slice from onset for unpitched/percussive sounds).
    5. Normalizes to -0.5 dB peak (~0.94).
    6. Resamples to target_samples (default 1024) for 32-bit float WAV output.
    7. Downsamples to 64 points for fast QML UI rendering.

    Returns:
        (resampled_1024, detected_freq_hz, peak, is_single_cycle, score, cycle_sim, peak_corr, preview_64)
    """
    if len(audio_data) < 500:
        return None, 0.0, 0.0, False, 0.0, 0.0, 0.0, None

    # Handle various integer/float audio formats
    if audio_data.dtype == np.int16:
        audio = audio_data.astype(np.float64) / 32768.0
    elif audio_data.dtype == np.int32:
        audio = audio_data.astype(np.float64) / 2147483648.0
    else:
        audio = audio_data.astype(np.float64)

    # If stereo, select the channel with the active signal
    if audio.ndim == 2:
        peak0 = float(np.max(np.abs(audio[:, 0])))
        peak1 = float(np.max(np.abs(audio[:, 1])))
        norm = audio[:, 1] if peak1 >= peak0 else audio[:, 0]
        peak = max(peak0, peak1)
    else:
        norm = audio
        peak = float(np.max(np.abs(norm)))

    if peak < min_peak:  # Dead wave or silence
        return None, 0.0, peak, False, 0.0, 0.0, 0.0, None

    # Normalize audio buffer for analysis
    norm_signal = norm / peak

    # 1. Dynamic onset detection (skip leading silence)
    onsets = np.where(np.abs(norm_signal) > 0.08)[0]
    start = int(onsets[0]) if len(onsets) > 0 else 0

    # 2. Extract stable burst region for pitch detection
    # Skip initial transient (200 samples ~ 4ms) and analyze up to 2600 samples (~50ms)
    burst_start = start + 200
    burst_end = burst_start + 2400
    if len(norm_signal) > burst_start + 600:
        burst = norm_signal[burst_start : min(len(norm_signal), burst_end)]
    else:
        burst = norm_signal[start:]

    # 3. Autocorrelation pitch detection (between 60 Hz and 1500 Hz)
    corr = np.correlate(burst, burst, mode="full")[len(burst) - 1 :]
    min_lag = max(10, int(sample_rate / 1500))  # 32 samples at 48kHz
    max_lag = min(len(corr) - 1, int(sample_rate / 60))  # 800 samples at 48kHz

    if min_lag >= max_lag:
        lag = 184  # Default to C4 period (48000 / 261.63 ~ 183.5 samples)
        detected_freq = 261.6
        peak_corr = 0.0
    else:
        lag_idx = min_lag + int(np.argmax(corr[min_lag:max_lag]))
        lag = lag_idx
        detected_freq = float(sample_rate / max(1, lag))
        peak_corr = float(corr[lag] / max(1e-9, corr[0]))

    # 4. Adjacent-cycle cross-correlation test
    c1 = norm_signal[burst_start : burst_start + lag]
    c2 = norm_signal[burst_start + lag : burst_start + 2 * lag]
    if len(c1) == len(c2) and len(c1) > 10:
        std1 = np.std(c1)
        std2 = np.std(c2)
        if std1 > 1e-6 and std2 > 1e-6:
            cc = np.corrcoef(c1, c2)[0, 1]
            cycle_sim = float(cc) if not np.isnan(cc) else 0.0
        else:
            cycle_sim = 0.0
    else:
        cycle_sim = 0.0

    is_pitched = bool(cycle_sim >= 0.50 and peak_corr >= 0.60)
    score = round(float((cycle_sim + peak_corr) / 2.0), 3)

    # 5. Positive zero-crossing alignment
    region = norm[burst_start : burst_start + lag * 4]
    if len(region) < lag + 10:
        region = norm[start:]

    zcs = np.where((region[:-1] <= 0) & (region[1:] > 0))[0]

    if len(zcs) > 0 and is_pitched:
        zc0 = zcs[0]
        # Search for matching positive zero-crossing approximately 1 period later
        cands = [z for z in zcs if z > zc0 + lag * 0.75]
        if cands:
            zc1 = min(cands, key=lambda z: abs(z - (zc0 + lag)))
        else:
            zc1 = zc0 + lag
        raw_cycle = region[zc0:zc1]
    else:
        # Fallback for unpitched (percussion/drums) or weak zero-crossings:
        # slice 1 fundamental period directly from onset
        slice_end = min(len(norm), start + lag)
        raw_cycle = norm[start:slice_end]

    if len(raw_cycle) < 4:
        raw_cycle = norm[start : start + min(184, len(norm) - start)]

    # 6. Normalize extracted cycle to -0.5 dB (~0.94)
    max_c = np.max(np.abs(raw_cycle))
    if max_c > 1e-6:
        raw_cycle = (raw_cycle / max_c) * 0.94

    # 7. Resample to target_samples (e.g. 1024) for 32-bit float WAV output
    x_old = np.linspace(0.0, 1.0, len(raw_cycle))
    x_new = np.linspace(0.0, 1.0, target_samples)
    resampled_1024 = np.interp(x_new, x_old, raw_cycle)

    # 8. Downsample to 64 points for fast QML UI rendering
    x_qml = np.linspace(0.0, 1.0, 64)
    preview_64 = np.interp(x_qml, x_old, raw_cycle).round(3).tolist()

    return resampled_1024, detected_freq, peak, True, score, cycle_sim, peak_corr, preview_64


class AudioCaptureSession:
    """Manages audio capture via RAM-disk across PipeWire (pw-record) and ALSA (arecord)."""

    def __init__(self, preferred_device: Optional[str] = None):
        shm_dir = Path("/dev/shm")
        self.rec_file = (shm_dir / "dump_rec.wav") if shm_dir.is_dir() else Path("/tmp/dump_rec.wav")
        self.cmd, self.backend_desc = self._detect_backend(preferred_device)

    def _detect_backend(self, preferred: Optional[str]) -> Tuple[list[str], str]:
        # 1. User manual override (if not "auto")
        if preferred and preferred.lower() != "auto":
            if "alsa_input" in preferred or "scarlett" in preferred.lower():
                if shutil.which("pw-record"):
                    return [
                        "pw-record", "--target", preferred, str(self.rec_file)
                    ], f"pw-record ({preferred})"
            return [
                "arecord", "-D", preferred,
                "-c", "2", "-f", "S16_LE", "-r", "48000", "-t", "wav", str(self.rec_file)
            ], f"arecord ({preferred})"

        # 2. Check for PipeWire / pw-record with Focusrite/Scarlett/USB source
        if shutil.which("pw-record"):
            target_source = None
            if shutil.which("pactl"):
                try:
                    out = subprocess.check_output(["pactl", "list", "sources", "short"], text=True)
                    candidates = []
                    for line in out.splitlines():
                        parts = line.split()
                        if len(parts) >= 2 and "monitor" not in parts[1].lower():
                            candidates.append(parts[1])
                    for name in candidates:
                        if any(k in name.lower() for k in ["scarlett", "focusrite", "usb"]):
                            target_source = name
                            break
                    if not target_source and candidates:
                        target_source = candidates[0]
                except Exception:
                    pass

            cmd = ["pw-record"]
            if target_source:
                cmd += ["--target", target_source]
            cmd.append(str(self.rec_file))

            # Test pw-record
            try:
                if self.rec_file.exists():
                    self.rec_file.unlink()
                p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(0.04)
                p.terminate()
                p.wait(timeout=0.5)
                if self.rec_file.exists() and self.rec_file.stat().st_size > 44:
                    return cmd, f"pw-record -> {target_source or 'default'}"
            except Exception:
                pass

        # 3. Test ALSA devices with arecord
        for dev in ["hw:CARD=USB,DEV=0", "sysdefault:CARD=USB", "pipewire", "default"]:
            cmd = ["arecord", "-D", dev, "-c", "2", "-f", "S16_LE", "-r", "48000", "-t", "wav", str(self.rec_file)]
            try:
                if self.rec_file.exists():
                    self.rec_file.unlink()
                p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(0.04)
                p.send_signal(signal.SIGINT)
                p.wait(timeout=0.5)
                if self.rec_file.exists() and self.rec_file.stat().st_size > 44:
                    return cmd, f"arecord -> {dev}"
            except Exception:
                pass

        raise RuntimeError(
            "No working audio recording device found.\n"
            "If using Scarlett Solo, ensure it is connected and check 'arecord -l' or 'wpctl status'."
        )

    def record_burst(self, trigger_fn) -> np.ndarray:
        """Launch recorder, execute note trigger, and return captured stereo audio array."""
        if self.rec_file.exists():
            try:
                self.rec_file.unlink()
            except Exception:
                pass

        proc = subprocess.Popen(self.cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.02)  # Pre-roll

        trigger_fn()
        time.sleep(0.04)  # Ringing/decay capture

        try:
            proc.send_signal(signal.SIGINT)
            proc.wait(timeout=1.0)
        except Exception:
            proc.terminate()
            try:
                proc.wait(timeout=0.5)
            except Exception:
                proc.kill()

        if not self.rec_file.exists():
            return np.empty((0, 2), dtype=np.int16)

        try:
            _, data = wavfile.read(str(self.rec_file))
            return data
        except Exception as e:
            logger.warning(f"Could not read captured audio WAV: {e}")
            return np.empty((0, 2), dtype=np.int16)


def dump_bank(
    bank_name: str,
    start_num: int,
    end_num: int,
    note: int,
    midi_channel: Optional[int],
    table_size: int,
    out_dir: Path,
    audio_device: str,
    force: bool = False,
    missing_only: bool = False,
    force_detect: bool = False,
    min_peak: float = 0.0001,
) -> None:
    """Run automated wave capture & audio periodicity classification loop."""
    bank_id = BANK_MAP[bank_name]
    bank_out = out_dir / bank_name.lower()
    bank_out.mkdir(parents=True, exist_ok=True)

    catalog_path = out_dir / f"{bank_name.lower()}_catalog.json"
    catalog: dict[str, dict] = {}
    if catalog_path.exists():
        try:
            with open(catalog_path, "r", encoding="utf-8") as f:
                catalog = json.load(f)
            logger.info(f"Loaded existing catalog with {len(catalog)} entries.")
        except Exception as e:
            logger.warning(f"Could not load catalog: {e}")

    if not catalog:
        try:
            from scripts.build_wave_catalog import build_catalogs
            logger.info("Catalog empty or missing. Building base catalog from Parameter Guide...")
            build_catalogs()
            if catalog_path.exists():
                with open(catalog_path, "r", encoding="utf-8") as f:
                    catalog = json.load(f)
        except Exception as e:
            logger.warning(f"Could not auto-generate base catalog: {e}")

    # Build target wave list
    if missing_only:
        wave_nums = [
            int(k) for k in sorted(catalog.keys(), key=lambda x: int(x))
            if start_num <= int(k) <= end_num and catalog[k].get("samples_64") is None
        ]
        logger.info(f"Targeting {len(wave_nums)} missing waves without preview in bank {bank_name}.")
    else:
        wave_nums = list(range(start_num, end_num + 1))

    # Initialize audio capture session
    try:
        capture_session = AudioCaptureSession(preferred_device=audio_device)
        logger.info(f"Audio capture active: {capture_session.backend_desc}")
    except Exception as e:
        logger.error(f"Cannot initialize audio capture: {e}")
        return

    mgr = MidiDeviceManager()
    in_n, out_n = mgr.connect_juno()
    logger.info(f"Connected to Roland synth: In='{in_n}', Out='{out_n}'")
    client = JunoClient(mgr)

    if midi_channel is None:
        midi_channel = detect_synth_midi_channel(client)

    init_feeder_patch(client)
    base = client.get_active_patch_base()
    t1_addr = add_address(base, OFFSET_PATCH_TONE_1)

    # Interruption handler for clean note-off & catalog save
    interrupted = False
    def sig_handler(sig, frame):
        nonlocal interrupted
        interrupted = True
        print("\n\nStopping gracefully... sending note off and saving catalog.")
        try:
            mgr.juno_out.send(mido.Message("note_off", note=note, velocity=0, channel=midi_channel))
        except Exception:
            pass
    signal.signal(signal.SIGINT, sig_handler)

    total_count = len(wave_nums)
    processed = 0
    single_cycle_count = 0
    silent_count = 0
    effective_min_peak = 1e-6 if force_detect else min_peak
    t_start = time.time()

    print("\n=======================================================")
    print(f" DUMPING & ANALYZING BANK {bank_name}: {total_count} waves (#{start_num:04d} to #{end_num:04d})")
    print(f" Audio Device: {capture_session.backend_desc}")
    print(f" MIDI Channel: {midi_channel + 1} | Note: {note} (C4) | Table Size: {table_size} pts")
    print(f" Mode: {'MISSING-ONLY RESCAN' if missing_only else 'STANDARD DUMP'}{' [FORCE-DETECT ON]' if force_detect else ''}")
    print("=======================================================\n")

    for w_num in wave_nums:
        if interrupted:
            break

        str_key = str(w_num)
        wav_file = bank_out / f"{bank_name.lower()}_{w_num:04d}.wav"
        wave_name = catalog.get(str_key, {}).get("name", f"Wave {w_num}")

        # Resume support: skip if already captured with preview points and force=False
        if not force and not missing_only and str_key in catalog and catalog[str_key].get("samples_64") is not None:
            processed += 1
            single_cycle_count += 1
            continue

        # 1. Send SysEx to select Wave
        client.send_data(add_address(t1_addr, TONE_PARAM_WAVE_GROUP_TYPE), [0])  # INT
        client.send_data(add_address(t1_addr, TONE_PARAM_WAVE_GROUP_ID), pack_4nibbles(bank_id))
        client.send_data(add_address(t1_addr, TONE_PARAM_WAVE_NUM_L), pack_4nibbles(w_num))
        client.send_data(add_address(t1_addr, TONE_PARAM_WAVE_NUM_R), pack_4nibbles(0))
        time.sleep(0.02)  # DSP latch time

        # 2. Record audio burst
        def trigger(trig_note):
            mgr.juno_out.send(mido.Message("note_on", note=trig_note, velocity=127, channel=midi_channel))
            time.sleep(0.08)
            mgr.juno_out.send(mido.Message("note_off", note=trig_note, velocity=0, channel=midi_channel))

        arr = capture_session.record_burst(lambda: trigger(note))

        if len(arr) == 0:
            print(f"[{w_num:04d}/{end_num:04d}] {wave_name:16s} -> NO AUDIO CAPTURED (Check audio device)")
            processed += 1
            continue

        # Check peak amplitude
        if arr.dtype == np.int16:
            audio_test = arr.astype(np.float64) / 32768.0
        elif arr.dtype == np.int32:
            audio_test = arr.astype(np.float64) / 2147483648.0
        else:
            audio_test = arr.astype(np.float64)
        peak_val = float(np.max(np.abs(audio_test)))

        # Multi-octave probe fallback: if primary note yielded very weak signal (< 1%),
        # probe alternate octaves [48, 36, 72] to catch samples mapped outside C4 (e.g. bass, ethnic)
        if peak_val < 0.01:
            for probe_note in [48, 36, 72]:
                arr_probe = capture_session.record_burst(lambda: trigger(probe_note))
                if len(arr_probe) > 0:
                    if arr_probe.dtype == np.int16:
                        p_test = arr_probe.astype(np.float64) / 32768.0
                    else:
                        p_test = arr_probe.astype(np.float64)
                    p_pk = float(np.max(np.abs(p_test)))
                    if p_pk > peak_val:
                        arr = arr_probe
                        peak_val = p_pk
                    if p_pk > 0.05:
                        break

        # 3. Extract single-cycle and evaluate periodicity
        try:
            cycle, freq, peak, is_sc, score, cycle_sim, peak_corr, preview_64 = extract_single_cycle(
                arr, sample_rate=48000, target_samples=table_size, min_peak=effective_min_peak
            )

            if str_key not in catalog:
                catalog[str_key] = {"id": w_num, "bank": bank_name, "name": wave_name}

            catalog[str_key]["periodicity_score"] = score
            catalog[str_key]["cycle_sim"] = round(cycle_sim, 3)
            catalog[str_key]["peak_corr"] = round(peak_corr, 3)
            catalog[str_key]["peak"] = round(peak, 3)

            if cycle is not None and preview_64 is not None:
                single_cycle_count += 1
                catalog[str_key]["is_single_cycle"] = True
                catalog[str_key]["freq_hz"] = round(freq, 1)
                catalog[str_key]["samples_64"] = preview_64

                # Save 1024-sample wavetable cycle WAV (32-bit float)
                wavfile.write(wav_file, 48000, cycle.astype(np.float32))

                # Pitch status: periodic synth vs acoustic sample
                type_label = "SYNTH" if (cycle_sim >= 0.50 and peak_corr >= 0.60) else "SAMPLE"
                color = "\033[36m" if type_label == "SYNTH" else "\033[33m"
                print(
                    f"{color}[{w_num:04d}/{end_num:04d}]\033[0m {wave_name:16s} "
                    f"-> \033[1;32m1-CYCLE EXTRACTED\033[0m [{type_label:6s}] "
                    f"(sim: {cycle_sim:.2f}, corr: {peak_corr:.2f}, {freq:5.1f} Hz, peak: {peak*100:3.0f}%)"
                )
            else:
                silent_count += 1
                catalog[str_key]["is_single_cycle"] = False
                catalog[str_key]["freq_hz"] = 0.0
                catalog[str_key]["samples_64"] = None
                print(
                    f"\033[90m[{w_num:04d}/{end_num:04d}] {wave_name:16s} "
                    f"-> SILENCE / DEAD WAVE (peak: {peak*100:3.1f}%)\033[0m"
                )

        except Exception as e:
            logger.error(f"Error processing wave {w_num}: {e}")

        processed += 1

        # Periodic catalog save every 20 waves
        if processed % 20 == 0:
            with open(catalog_path, "w", encoding="utf-8") as f:
                json.dump(catalog, f, indent=2)

    # Final catalog save
    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2)

    elapsed = time.time() - t_start
    print("\n=======================================================")
    print(f" DUMP & ANALYSIS COMPLETE: {bank_name}")
    print(f" Processed: {processed} waves in {elapsed:.1f}s ({processed/max(0.1, elapsed):.1f} w/s)")
    print(f" Waveform Previews Captured: {single_cycle_count}")
    print(f" Silent / Dead Waves:        {silent_count}")
    print(f" Updated Catalog: {catalog_path}")
    print(f" Single-Cycle WAVs: {bank_out}/")
    print("=======================================================\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Roland XPS-30 / JUNO-DS Automated Waveform Dumper & Periodicity Classifier")
    parser.add_argument("--bank", choices=["INTA", "INTB", "ALL"], default="INTA", help="Wave bank to dump (default: INTA)")
    parser.add_argument("--start", type=int, default=1, help="Starting wave number (default: 1)")
    parser.add_argument("--end", type=int, default=None, help="Ending wave number (default: max for bank)")
    parser.add_argument("--note", type=int, default=60, help="MIDI note number to trigger (default: 60 = C4)")
    parser.add_argument("--midi-ch", type=int, default=None, help="MIDI channel 1-16 (default: auto-detect from synth)")
    parser.add_argument("--table-size", type=int, default=1024, help="Single-cycle sample length (default: 1024)")
    parser.add_argument("--device", type=str, default="auto", help="Audio capture device ('auto', or ALSA/PipeWire device name)")
    parser.add_argument(
        "--out-dir",
        type=str,
        default=str(PROJECT_ROOT / "src" / "spectre" / "assets" / "waveforms"),
        help="Output directory",
    )
    parser.add_argument("--force", action="store_true", help="Re-sample waves even if already analyzed")
    parser.add_argument("--missing-only", action="store_true", help="Only re-scan waveforms that lack 64-sample preview data")
    parser.add_argument("--force-detect", action="store_true", help="Force cycle detection even on very quiet or noisy waves")
    parser.add_argument("--min-peak", type=float, default=0.0001, help="Minimum peak amplitude threshold (default: 0.0001 = 0.01%)")
    args = parser.parse_args()

    out_path = Path(args.out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    midi_channel = args.midi_ch - 1 if args.midi_ch is not None else None
    banks_to_dump = ["INTA", "INTB"] if args.bank == "ALL" else [args.bank]

    for b in banks_to_dump:
        start_n = args.start
        end_n = args.end or BANK_TOTALS[b]
        dump_bank(
            bank_name=b,
            start_num=start_n,
            end_num=end_n,
            note=args.note,
            midi_channel=midi_channel,
            table_size=args.table_size,
            out_dir=out_path,
            audio_device=args.device,
            force=args.force,
            missing_only=args.missing_only,
            force_detect=args.force_detect,
            min_peak=args.min_peak,
        )


if __name__ == "__main__":
    main()

