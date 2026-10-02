"""High-level Roland JUNO-DS / XPS-30 client protocol.

Provides typed, safe methods to query and control synth parameters
targeting the Temporary RAM Edit Buffers exclusively.
"""

from __future__ import annotations

import enum
import time
from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

from .midi import MidiDeviceManager
from .sysex import (
    ADDR_SETUP,
    ADDR_TEMP_PATCH_PART_1,
    ADDR_TEMP_PERF_PART_1,
    DEFAULT_DEVICE_ID,
    JUNO_DS_MODEL_ID,
    OFFSET_PATCH_TONE_1,
    OFFSET_PATCH_TONE_2,
    OFFSET_PATCH_TONE_3,
    OFFSET_PATCH_TONE_4,
    PATCH_PARAM_ATTACK_OFFSET,
    PATCH_PARAM_CHORUS_SEND,
    PATCH_PARAM_CUTOFF_OFFSET,
    PATCH_PARAM_LEVEL,
    PATCH_PARAM_NAME,
    PATCH_PARAM_PAN,
    PATCH_PARAM_RELEASE_OFFSET,
    PATCH_PARAM_RESONANCE_OFFSET,
    PATCH_PARAM_REVERB_SEND,
    TONE_PARAM_CHORUS_SEND,
    TONE_PARAM_COARSE_TUNE,
    TONE_PARAM_DRY_SEND,
    TONE_PARAM_FINE_TUNE,
    TONE_PARAM_LEVEL,
    TONE_PARAM_LFO1_PAN_DEPTH,
    TONE_PARAM_LFO1_PITCH_DEPTH,
    TONE_PARAM_LFO1_RATE,
    TONE_PARAM_LFO1_TVA_DEPTH,
    TONE_PARAM_LFO1_TVF_DEPTH,
    TONE_PARAM_LFO1_WAVEFORM,
    TONE_PARAM_LFO2_PAN_DEPTH,
    TONE_PARAM_LFO2_PITCH_DEPTH,
    TONE_PARAM_LFO2_RATE,
    TONE_PARAM_LFO2_TVA_DEPTH,
    TONE_PARAM_LFO2_TVF_DEPTH,
    TONE_PARAM_LFO2_WAVEFORM,
    TONE_PARAM_PAN,
    TONE_PARAM_PITCH_ENV_DEPTH,
    TONE_PARAM_PITCH_ENV_T1,
    TONE_PARAM_PITCH_ENV_T2,
    TONE_PARAM_PITCH_ENV_T3,
    TONE_PARAM_PITCH_ENV_T4,
    TONE_PARAM_REVERB_SEND,
    TONE_PARAM_TVA_ENV_L1,
    TONE_PARAM_TVA_ENV_L2,
    TONE_PARAM_TVA_ENV_L3,
    TONE_PARAM_TVA_ENV_T1,
    TONE_PARAM_TVA_ENV_T2,
    TONE_PARAM_TVA_ENV_T3,
    TONE_PARAM_TVA_ENV_T4,
    TONE_PARAM_TVA_LEVEL,
    TONE_PARAM_TVA_PAN,
    TONE_PARAM_TVF_CUTOFF,
    TONE_PARAM_TVF_CUTOFF_KEYFOLLOW,
    TONE_PARAM_TVF_ENV_DEPTH,
    TONE_PARAM_TVF_ENV_L1,
    TONE_PARAM_TVF_ENV_L2,
    TONE_PARAM_TVF_ENV_L3,
    TONE_PARAM_TVF_ENV_L4,
    TONE_PARAM_TVF_ENV_T1,
    TONE_PARAM_TVF_ENV_T2,
    TONE_PARAM_TVF_ENV_T3,
    TONE_PARAM_TVF_ENV_T4,
    TONE_PARAM_TVF_ENV_VEL_SENS,
    TONE_PARAM_TVF_FILTER_TYPE,
    TONE_PARAM_TVF_RESONANCE,
    TONE_PARAM_WAVE_FXM_COLOR,
    TONE_PARAM_WAVE_FXM_DEPTH,
    TONE_PARAM_WAVE_FXM_SWITCH,
    TONE_PARAM_WAVE_GAIN,
    TONE_PARAM_WAVE_GROUP_ID,
    TONE_PARAM_WAVE_GROUP_TYPE,
    TONE_PARAM_WAVE_NUM_L,
    TONE_PARAM_WAVE_NUM_R,
    RolandSysEx,
    add_address,
    pack_2nibbles,
    pack_4nibbles,
)


class SoundMode(enum.IntEnum):
    PATCH = 0
    PERFORM = 1
    GM1 = 2
    GM2 = 3
    GS = 4


@dataclass(frozen=True)
class IdentityInfo:
    device_id: int
    family_code: Tuple[int, int]
    family_number: Tuple[int, int]
    software_revision: Tuple[int, int, int, int]

    @property
    def is_juno_ds_or_xps(self) -> bool:
        """Check if family code matches Roland JUNO-DS / XPS series (0x3A 0x02)."""
        return self.family_code == (0x3A, 0x02)


class JunoClient:
    """Client for bidirectional communication with Roland JUNO-DS / XPS-30."""

    def __init__(
        self,
        midi_mgr: MidiDeviceManager,
        device_id: int = DEFAULT_DEVICE_ID,
        model_id: Sequence[int] = JUNO_DS_MODEL_ID,
    ):
        self.midi = midi_mgr
        self.device_id = device_id
        self.model_id = tuple(model_id)
        self.sysex = RolandSysEx(device_id=self.device_id, model_id=self.model_id)
        self._cached_patch_base: Optional[Tuple[int, int, int, int]] = None
        self._cached_sound_mode: Optional[SoundMode] = None

    def invalidate_cache(self) -> None:
        """Clear cached state (call when changing synth patches or modes)."""
        self._cached_patch_base = None
        self._cached_sound_mode = None

    def ping(self, timeout: float = 1.0) -> Optional[IdentityInfo]:
        """Send Universal Non-realtime Identity Request and wait for reply."""
        # F0 7E 7F 06 01 F7 (Broadcast)
        req_data = [0x7E, 0x7F, 0x06, 0x01]
        self.midi.send_juno_sysex(req_data)

        start = time.perf_counter()
        while time.perf_counter() - start < timeout:
            for msg in self.midi.iter_juno_messages():
                if msg.type == "sysex" and len(msg.data) >= 13:
                    # Check Universal Identity Reply: 7E <dev> 06 02 41 ...
                    d = msg.data
                    if d[0] == 0x7E and d[2] == 0x06 and d[3] == 0x02 and d[4] == 0x41:
                        return IdentityInfo(
                            device_id=d[1],
                            family_code=(d[5], d[6]),
                            family_number=(d[7], d[8]),
                            software_revision=(d[9], d[10], d[11], d[12]),
                        )
            time.sleep(0.005)
        return None

    def request_data(
        self,
        address: Sequence[int],
        size: Sequence[int],
        timeout: float = 1.0,
    ) -> Optional[bytes]:
        """Send RQ1 data request and await matching DT1 response."""
        packet = self.sysex.build_rq1(address, size)
        self.midi.send_juno_sysex(packet)

        target_addr = tuple(address)
        start = time.perf_counter()
        while time.perf_counter() - start < timeout:
            for msg in self.midi.iter_juno_messages():
                if msg.type == "sysex":
                    parsed = RolandSysEx.parse(msg.data)
                    if (
                        parsed
                        and parsed.is_valid_checksum
                        and parsed.address == target_addr
                    ):
                        return parsed.payload
            time.sleep(0.005)
        return None

    def send_data(self, address: Sequence[int], data: Sequence[int]) -> None:
        """Send DT1 data set message directly to the synth."""
        packet = self.sysex.build_dt1(address, data)
        self.midi.send_juno_sysex(packet)

    def get_sound_mode(self, timeout: float = 1.0, force_refresh: bool = False) -> SoundMode:
        """Query synth Sound Mode (Setup address 01 00 00 00)."""
        if not force_refresh and self._cached_sound_mode is not None:
            return self._cached_sound_mode
        res = self.request_data(ADDR_SETUP, (0x00, 0x00, 0x00, 0x01), timeout=timeout)
        if res is None or len(res) == 0:
            raise TimeoutError("Timed out waiting for Sound Mode response from synth.")
        self._cached_sound_mode = SoundMode(res[0])
        return self._cached_sound_mode

    def get_active_patch_base(
        self,
        timeout: float = 1.0,
        force_refresh: bool = False,
    ) -> Tuple[int, int, int, int]:
        """Determine base address for the current temporary patch buffer.
        
        Returns ADDR_TEMP_PATCH_PART_1 in Patch Mode, or ADDR_TEMP_PERF_PART_1 in Performance Mode.
        """
        if not force_refresh and self._cached_patch_base is not None:
            return self._cached_patch_base
        mode = self.get_sound_mode(timeout=timeout, force_refresh=force_refresh)
        if mode == SoundMode.PATCH:
            self._cached_patch_base = ADDR_TEMP_PATCH_PART_1
        else:
            self._cached_patch_base = ADDR_TEMP_PERF_PART_1
        return self._cached_patch_base

    def get_patch_name(self, timeout: float = 1.0) -> str:
        """Read active patch name (12 ASCII characters) from the temporary buffer."""
        base = self.get_active_patch_base(timeout=timeout)
        name_addr = add_address(base, PATCH_PARAM_NAME)
        res = self.request_data(name_addr, (0x00, 0x00, 0x00, 0x0C), timeout=timeout)
        if res is None:
            raise TimeoutError("Timed out waiting for patch name response.")
        return res.decode("latin1", errors="replace").strip()

    def get_tone_levels(self, timeout: float = 1.0) -> Tuple[int, int, int, int]:
        """Query current TVA Level for Tones 1, 2, 3, and 4."""
        base = self.get_active_patch_base(timeout=timeout)
        t_offsets = [
            OFFSET_PATCH_TONE_1,
            OFFSET_PATCH_TONE_2,
            OFFSET_PATCH_TONE_3,
            OFFSET_PATCH_TONE_4,
        ]
        levels = []
        for offset in t_offsets:
            addr = add_address(base, offset)
            res = self.request_data(addr, (0x00, 0x00, 0x00, 0x01), timeout=timeout)
            if res is None:
                raise TimeoutError(f"Timed out querying Tone level at {addr}")
            levels.append(res[0])

        return (levels[0], levels[1], levels[2], levels[3])

    def set_tone_level(self, tone_index: int, level: int) -> None:
        """Set TVA Level for a specific tone (tone_index 1..4, level 0..127)."""
        if tone_index not in (1, 2, 3, 4):
            raise ValueError(f"Tone index must be 1..4, got {tone_index}")
        clamped_level = max(0, min(127, int(level)))

        base = self.get_active_patch_base()
        offsets = {
            1: OFFSET_PATCH_TONE_1,
            2: OFFSET_PATCH_TONE_2,
            3: OFFSET_PATCH_TONE_3,
            4: OFFSET_PATCH_TONE_4,
        }
        addr = add_address(base, offsets[tone_index])
        self.send_data(addr, [clamped_level])

    def set_tone_levels(
        self,
        tone_levels: Tuple[int, int, int, int],
    ) -> None:
        """Set TVA Levels for all 4 tones sequentially in real time."""
        for idx, lvl in enumerate(tone_levels, start=1):
            self.set_tone_level(idx, lvl)

    def set_patch_cutoff_offset(self, offset_val: int) -> None:
        """Set Cutoff Frequency Offset (1..127, where 64 = 0 neutral)."""
        clamped = max(1, min(127, int(offset_val)))
        base = self.get_active_patch_base()
        addr = add_address(base, PATCH_PARAM_CUTOFF_OFFSET)
        self.send_data(addr, [clamped])

    def set_patch_resonance_offset(self, offset_val: int) -> None:
        """Set Resonance Offset (1..127, where 64 = 0 neutral)."""
        clamped = max(1, min(127, int(offset_val)))
        base = self.get_active_patch_base()
        addr = add_address(base, PATCH_PARAM_RESONANCE_OFFSET)
        self.send_data(addr, [clamped])

    def set_patch_param(self, param_name: str, value: int) -> None:
        """Set a Patch Common parameter by name."""
        base = self.get_active_patch_base()
        mapping = {
            "level": (PATCH_PARAM_LEVEL, 0, 127),
            "pan": (PATCH_PARAM_PAN, 0, 127),
            "cutoff_offset": (PATCH_PARAM_CUTOFF_OFFSET, 1, 127),
            "resonance_offset": (PATCH_PARAM_RESONANCE_OFFSET, 1, 127),
            "attack_offset": (PATCH_PARAM_ATTACK_OFFSET, 1, 127),
            "release_offset": (PATCH_PARAM_RELEASE_OFFSET, 1, 127),
            "chorus_send": (PATCH_PARAM_CHORUS_SEND, 0, 127),
            "reverb_send": (PATCH_PARAM_REVERB_SEND, 0, 127),
        }
        if param_name not in mapping:
            raise ValueError(f"Unknown patch param '{param_name}'. Supported: {list(mapping.keys())}")
        offset, min_v, max_v = mapping[param_name]
        clamped = max(min_v, min(max_v, int(value)))
        addr = add_address(base, offset)
        self.send_data(addr, [clamped])

    def set_tone_param(self, tone_index: int, offset: int, value: int | Sequence[int]) -> None:
        """Set an arbitrary Tone parameter by offset."""
        if tone_index not in (1, 2, 3, 4):
            raise ValueError(f"Tone index must be 1..4, got {tone_index}")
        base = self.get_active_patch_base()
        offsets = {
            1: OFFSET_PATCH_TONE_1,
            2: OFFSET_PATCH_TONE_2,
            3: OFFSET_PATCH_TONE_3,
            4: OFFSET_PATCH_TONE_4,
        }
        addr = add_address(add_address(base, offsets[tone_index]), offset)
        data = [value] if isinstance(value, int) else list(value)
        self.send_data(addr, data)

    def set_tone_tvf(
        self,
        tone_index: int,
        cutoff: Optional[int] = None,
        resonance: Optional[int] = None,
        env_depth: Optional[int] = None,
        filter_type: Optional[int] = None,
        attack: Optional[int] = None,
        decay: Optional[int] = None,
        sustain: Optional[int] = None,
        release: Optional[int] = None,
    ) -> None:
        """Set TVF (Filter) parameters for a tone."""
        if cutoff is not None:
            self.set_tone_param(tone_index, TONE_PARAM_TVF_CUTOFF, max(0, min(127, cutoff)))
        if resonance is not None:
            self.set_tone_param(tone_index, TONE_PARAM_TVF_RESONANCE, max(0, min(127, resonance)))
        if env_depth is not None:
            self.set_tone_param(tone_index, TONE_PARAM_TVF_ENV_DEPTH, max(1, min(127, env_depth)))
        if filter_type is not None:
            self.set_tone_param(tone_index, TONE_PARAM_TVF_FILTER_TYPE, max(0, min(6, filter_type)))
        if attack is not None:
            self.set_tone_param(tone_index, TONE_PARAM_TVF_ENV_T1, max(0, min(127, attack)))
        if decay is not None:
            self.set_tone_param(tone_index, TONE_PARAM_TVF_ENV_T2, max(0, min(127, decay)))
        if sustain is not None:
            self.set_tone_param(tone_index, TONE_PARAM_TVF_ENV_L3, max(0, min(127, sustain)))
        if release is not None:
            self.set_tone_param(tone_index, TONE_PARAM_TVF_ENV_T4, max(0, min(127, release)))

    def set_tone_tva(
        self,
        tone_index: int,
        level: Optional[int] = None,
        pan: Optional[int] = None,
        attack: Optional[int] = None,
        decay: Optional[int] = None,
        sustain: Optional[int] = None,
        release: Optional[int] = None,
    ) -> None:
        """Set TVA (Amp) parameters for a tone."""
        if level is not None:
            self.set_tone_level(tone_index, level)
        if pan is not None:
            self.set_tone_param(tone_index, TONE_PARAM_TVA_PAN, max(0, min(127, pan)))
        if attack is not None:
            self.set_tone_param(tone_index, TONE_PARAM_TVA_ENV_T1, max(0, min(127, attack)))
        if decay is not None:
            self.set_tone_param(tone_index, TONE_PARAM_TVA_ENV_T2, max(0, min(127, decay)))
        if sustain is not None:
            self.set_tone_param(tone_index, TONE_PARAM_TVA_ENV_L3, max(0, min(127, sustain)))
        if release is not None:
            self.set_tone_param(tone_index, TONE_PARAM_TVA_ENV_T4, max(0, min(127, release)))

    def set_tone_pitch(
        self,
        tone_index: int,
        coarse: Optional[int] = None,
        fine: Optional[int] = None,
        env_depth: Optional[int] = None,
    ) -> None:
        """Set Pitch parameters for a tone."""
        if coarse is not None:
            self.set_tone_param(tone_index, TONE_PARAM_COARSE_TUNE, max(16, min(112, coarse)))
        if fine is not None:
            self.set_tone_param(tone_index, TONE_PARAM_FINE_TUNE, max(14, min(114, fine)))
        if env_depth is not None:
            self.set_tone_param(tone_index, TONE_PARAM_PITCH_ENV_DEPTH, max(52, min(76, env_depth)))

    def set_tone_wave(
        self,
        tone_index: int,
        group_type: Optional[int] = None,
        wave_num: Optional[int] = None,
        gain: Optional[int] = None,
        fxm_switch: Optional[int] = None,
        fxm_depth: Optional[int] = None,
    ) -> None:
        """Set Wave generator parameters for a tone."""
        if group_type is not None:
            self.set_tone_param(tone_index, TONE_PARAM_WAVE_GROUP_TYPE, max(0, min(3, group_type)))
        if wave_num is not None:
            nibbles = pack_4nibbles(max(0, min(16384, wave_num)))
            self.set_tone_param(tone_index, TONE_PARAM_WAVE_NUM_L, nibbles)
        if gain is not None:
            self.set_tone_param(tone_index, TONE_PARAM_WAVE_GAIN, max(0, min(3, gain)))
        if fxm_switch is not None:
            self.set_tone_param(tone_index, TONE_PARAM_WAVE_FXM_SWITCH, 1 if fxm_switch else 0)
        if fxm_depth is not None:
            self.set_tone_param(tone_index, TONE_PARAM_WAVE_FXM_DEPTH, max(0, min(16, fxm_depth)))

    def set_tone_lfo(
        self,
        tone_index: int,
        lfo_index: int = 1,
        waveform: Optional[int] = None,
        rate: Optional[int] = None,
        pitch_depth: Optional[int] = None,
        tvf_depth: Optional[int] = None,
        tva_depth: Optional[int] = None,
        pan_depth: Optional[int] = None,
    ) -> None:
        """Set LFO 1 or LFO 2 parameters for a tone."""
        if lfo_index == 1:
            wf_off, rate_off, p_off, f_off, a_off, pan_off = (
                TONE_PARAM_LFO1_WAVEFORM,
                TONE_PARAM_LFO1_RATE,
                TONE_PARAM_LFO1_PITCH_DEPTH,
                TONE_PARAM_LFO1_TVF_DEPTH,
                TONE_PARAM_LFO1_TVA_DEPTH,
                TONE_PARAM_LFO1_PAN_DEPTH,
            )
        elif lfo_index == 2:
            wf_off, rate_off, p_off, f_off, a_off, pan_off = (
                TONE_PARAM_LFO2_WAVEFORM,
                TONE_PARAM_LFO2_RATE,
                TONE_PARAM_LFO2_PITCH_DEPTH,
                TONE_PARAM_LFO2_TVF_DEPTH,
                TONE_PARAM_LFO2_TVA_DEPTH,
                TONE_PARAM_LFO2_PAN_DEPTH,
            )
        else:
            raise ValueError(f"LFO index must be 1 or 2, got {lfo_index}")

        if waveform is not None:
            self.set_tone_param(tone_index, wf_off, max(0, min(12, waveform)))
        if rate is not None:
            self.set_tone_param(tone_index, rate_off, pack_2nibbles(max(0, min(149, rate))))
        if pitch_depth is not None:
            self.set_tone_param(tone_index, p_off, max(1, min(127, pitch_depth)))
        if tvf_depth is not None:
            self.set_tone_param(tone_index, f_off, max(1, min(127, tvf_depth)))
        if tva_depth is not None:
            self.set_tone_param(tone_index, a_off, max(1, min(127, tva_depth)))
        if pan_depth is not None:
            self.set_tone_param(tone_index, pan_off, max(1, min(127, pan_depth)))
