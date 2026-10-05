"""High-level Roland JUNO-DS / XPS-30 client protocol.

Provides typed, safe methods to query and control synth parameters
targeting the Temporary RAM Edit Buffers exclusively.
"""

from __future__ import annotations

import enum
import logging
import time
from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

from .midi import MidiDeviceManager
from .patch_state import (
    EffectsState,
    MatrixCtrlState,
    PatchCommonState,
    PatchState,
    PerfPartState,
    StepLfoState,
    ToneState,
)
from .sysex import (
    ADDR_MASTER_EQ_BASE,
    ADDR_SETUP,
    ADDR_SETUP_CHORUS_SWITCH,
    ADDR_SETUP_REVERB_SWITCH,
    ADDR_SYSTEM_MASTER_LEVEL,
    ADDR_SYSTEM_PROCESSING_SWITCH,
    ADDR_TEMP_PATCH_PART_1,
    ADDR_TEMP_PERF_PART_1,
    CHORUS_PARAM_DATA_START,
    CHORUS_PARAM_DEPTH,
    CHORUS_PARAM_FEEDBACK,
    CHORUS_PARAM_LEVEL,
    CHORUS_PARAM_OUTPUT_SELECT,
    CHORUS_PARAM_PREDELAY,
    CHORUS_PARAM_RATE,
    CHORUS_PARAM_TYPE,
    DEFAULT_DEVICE_ID,
    JUNO_DS_MODEL_ID,
    MASTER_EQ_PARAM_HIGH_FREQ,
    MASTER_EQ_PARAM_HIGH_GAIN,
    MASTER_EQ_PARAM_LOW_FREQ,
    MASTER_EQ_PARAM_LOW_GAIN,
    MASTER_EQ_PARAM_MID_FREQ,
    MASTER_EQ_PARAM_MID_GAIN,
    MASTER_EQ_PARAM_MID_Q,
    MASTER_EQ_PARAM_SWITCH,
    MFX_PARAM_CHORUS_SEND,
    MFX_PARAM_DATA_START,
    MFX_PARAM_DRY_SEND,
    MFX_PARAM_REVERB_SEND,
    MFX_PARAM_TYPE,
    OFFSET_PATCH_COMMON,
    OFFSET_PATCH_COMMON_CHORUS,
    OFFSET_PATCH_COMMON_MFX,
    OFFSET_PATCH_COMMON_REVERB,
    REVERB_PARAM_DATA_START,
    REVERB_PARAM_DIFFUSION,
    REVERB_PARAM_HF_DAMP,
    REVERB_PARAM_LEVEL,
    REVERB_PARAM_PREDELAY,
    REVERB_PARAM_TIME,
    REVERB_PARAM_TONE,
    REVERB_PARAM_TYPE,
    OFFSET_PATCH_TMT,
    OFFSET_PATCH_TONE_1,
    OFFSET_PATCH_TONE_2,
    OFFSET_PATCH_TONE_3,
    OFFSET_PATCH_TONE_4,
    PATCH_PARAM_ANALOG_FEEL,
    PATCH_PARAM_ATTACK_OFFSET,
    PATCH_PARAM_CHORUS_SEND,
    PATCH_PARAM_CUTOFF_OFFSET,
    PATCH_PARAM_LEGATO_SWITCH,
    PATCH_PARAM_LEVEL,
    PATCH_PARAM_MATRIX_CTRL_1,
    PATCH_PARAM_MATRIX_CTRL_2,
    PATCH_PARAM_MATRIX_CTRL_3,
    PATCH_PARAM_MATRIX_CTRL_4,
    PATCH_PARAM_MONO_POLY,
    PATCH_PARAM_NAME,
    PATCH_PARAM_PAN,
    PATCH_PARAM_PORTAMENTO_MODE,
    PATCH_PARAM_PORTAMENTO_SWITCH,
    PATCH_PARAM_PORTAMENTO_TIME,
    PATCH_PARAM_RELEASE_OFFSET,
    PATCH_PARAM_RESONANCE_OFFSET,
    PATCH_PARAM_REVERB_SEND,
    REVERB_PARAM_DATA_START,
    REVERB_PARAM_LEVEL,
    REVERB_PARAM_TYPE,
    TMT_PARAM_TONE1_SWITCH,
    TMT_PARAM_TONE2_SWITCH,
    TMT_PARAM_TONE3_SWITCH,
    TMT_PARAM_TONE4_SWITCH,
    TONE_PARAM_CHORUS_SEND,
    TONE_PARAM_COARSE_TUNE,
    TONE_PARAM_DRY_SEND,
    TONE_PARAM_ENV_MODE,
    TONE_PARAM_FINE_TUNE,
    TONE_PARAM_LEVEL,
    TONE_PARAM_LFO1_DELAY_TIME,
    TONE_PARAM_LFO1_FADE_MODE,
    TONE_PARAM_LFO1_FADE_TIME,
    TONE_PARAM_LFO1_PAN_DEPTH,
    TONE_PARAM_LFO1_PITCH_DEPTH,
    TONE_PARAM_LFO1_RATE,
    TONE_PARAM_LFO1_TVA_DEPTH,
    TONE_PARAM_LFO1_TVF_DEPTH,
    TONE_PARAM_LFO1_WAVEFORM,
    TONE_PARAM_LFO2_DELAY_TIME,
    TONE_PARAM_LFO2_FADE_MODE,
    TONE_PARAM_LFO2_FADE_TIME,
    TONE_PARAM_LFO2_PAN_DEPTH,
    TONE_PARAM_LFO2_PITCH_DEPTH,
    TONE_PARAM_LFO2_RATE,
    TONE_PARAM_LFO2_TVA_DEPTH,
    TONE_PARAM_LFO2_TVF_DEPTH,
    TONE_PARAM_LFO2_WAVEFORM,
    TONE_PARAM_LFO_STEP_1,
    TONE_PARAM_LFO_STEP_TYPE,
    TONE_PARAM_MATRIX_CTRL_SW_BASE,
    TONE_PARAM_PAN,
    TONE_PARAM_PITCH_ENV_DEPTH,
    TONE_PARAM_PITCH_ENV_L0,
    TONE_PARAM_PITCH_ENV_L1,
    TONE_PARAM_PITCH_ENV_L2,
    TONE_PARAM_PITCH_ENV_L3,
    TONE_PARAM_PITCH_ENV_L4,
    TONE_PARAM_PITCH_ENV_T1,
    TONE_PARAM_PITCH_ENV_T1_VEL_SENS,
    TONE_PARAM_PITCH_ENV_T2,
    TONE_PARAM_PITCH_ENV_T3,
    TONE_PARAM_PITCH_ENV_T4,
    TONE_PARAM_PITCH_ENV_T4_VEL_SENS,
    TONE_PARAM_PITCH_ENV_TIME_KEYFOLLOW,
    TONE_PARAM_PITCH_ENV_VEL_SENS,
    TONE_PARAM_REVERB_SEND,
    TONE_PARAM_TVA_BIAS_LEVEL,
    TONE_PARAM_TVA_ENV_L1,
    TONE_PARAM_TVA_ENV_L2,
    TONE_PARAM_TVA_ENV_L3,
    TONE_PARAM_TVA_ENV_T1,
    TONE_PARAM_TVA_ENV_T2,
    TONE_PARAM_TVA_ENV_T3,
    TONE_PARAM_TVA_ENV_T4,
    TONE_PARAM_TVA_LEVEL,
    TONE_PARAM_TVA_PAN,
    TONE_PARAM_TVA_VEL_SENS,
    TONE_PARAM_TVF_CUTOFF,
    TONE_PARAM_TVF_CUTOFF_KEYFOLLOW,
    TONE_PARAM_TVF_ENV_DEPTH,
    TONE_PARAM_TVF_ENV_L0,
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
    unpack_2nibbles,
    unpack_4nibbles,
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

    def set_patch_name(self, name: str) -> None:
        """Write active patch name (up to 12 ASCII characters) to the temporary buffer."""
        base = self.get_active_patch_base()
        name_addr = add_address(base, PATCH_PARAM_NAME)
        raw_name = name.encode("ascii", errors="replace")[:12].ljust(12, b" ")
        self.send_data(name_addr, list(raw_name))

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
        """Set TVF (Filter) parameters for a tone with 4-stage simplified ADSR."""
        if cutoff is not None:
            self.set_tone_param(tone_index, TONE_PARAM_TVF_CUTOFF, max(0, min(127, cutoff)))
        if resonance is not None:
            self.set_tone_param(tone_index, TONE_PARAM_TVF_RESONANCE, max(0, min(127, resonance)))
        if env_depth is not None:
            self.set_tone_param(tone_index, TONE_PARAM_TVF_ENV_DEPTH, max(1, min(127, env_depth)))
        if filter_type is not None:
            self.set_tone_param(tone_index, TONE_PARAM_TVF_FILTER_TYPE, max(0, min(6, filter_type)))

        # ADSR Envelope mapping
        if attack is not None and decay is not None and sustain is not None and release is not None:
            a = max(0, min(127, int(attack)))
            d = max(0, min(127, int(decay)))
            s = max(0, min(127, int(sustain)))
            r = max(0, min(127, int(release)))
            # Contiguous 9-byte block: 0x0055 to 0x005D
            # [T1, T2, T3, T4, L0, L1, L2, L3, L4]
            # L0=0 (start at cutoff), L1=127 (peak), L2=s, L3=s (sustain), L4=0 (end at cutoff)
            self.set_tone_param(tone_index, TONE_PARAM_TVF_ENV_T1, [a, d, 0, r, 0, 127, s, s, 0])
        else:
            if attack is not None:
                self.set_tone_param(tone_index, TONE_PARAM_TVF_ENV_T1, max(0, min(127, int(attack))))
                self.set_tone_param(tone_index, TONE_PARAM_TVF_ENV_L0, [0, 127])
            if decay is not None:
                self.set_tone_param(tone_index, TONE_PARAM_TVF_ENV_T2, [max(0, min(127, int(decay))), 0])
            if sustain is not None:
                s = max(0, min(127, int(sustain)))
                self.set_tone_param(tone_index, TONE_PARAM_TVF_ENV_L2, [s, s, 0])
            if release is not None:
                self.set_tone_param(tone_index, TONE_PARAM_TVF_ENV_T4, max(0, min(127, int(release))))

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
        """Set TVA (Amp) parameters for a tone with 4-stage simplified ADSR."""
        if level is not None:
            self.set_tone_level(tone_index, level)
        if pan is not None:
            self.set_tone_param(tone_index, TONE_PARAM_TVA_PAN, max(0, min(127, pan)))

        # ADSR Envelope mapping
        if attack is not None and decay is not None and sustain is not None and release is not None:
            a = max(0, min(127, int(attack)))
            d = max(0, min(127, int(decay)))
            s = max(0, min(127, int(sustain)))
            r = max(0, min(127, int(release)))
            # Contiguous 7-byte block: 0x0066 to 0x006C
            # [T1, T2, T3, T4, L1, L2, L3]
            # L1=127 (peak), L2=s, L3=s (sustain)
            self.set_tone_param(tone_index, TONE_PARAM_TVA_ENV_T1, [a, d, 0, r, 127, s, s])
        else:
            if attack is not None:
                self.set_tone_param(tone_index, TONE_PARAM_TVA_ENV_T1, max(0, min(127, int(attack))))
                self.set_tone_param(tone_index, TONE_PARAM_TVA_ENV_L1, 127)
            if decay is not None:
                self.set_tone_param(tone_index, TONE_PARAM_TVA_ENV_T2, [max(0, min(127, int(decay))), 0])
            if sustain is not None:
                s = max(0, min(127, int(sustain)))
                self.set_tone_param(tone_index, TONE_PARAM_TVA_ENV_L2, [s, s])
            if release is not None:
                self.set_tone_param(tone_index, TONE_PARAM_TVA_ENV_T4, max(0, min(127, int(release))))

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

    def set_tone_switch(self, tone_index: int, enabled: bool) -> None:
        """Set tone switch (ON/OFF) in Tone Mix Table (TMT)."""
        if tone_index not in (1, 2, 3, 4):
            raise ValueError(f"Tone index must be 1..4, got {tone_index}")
        tmt_switch_offsets = {
            1: TMT_PARAM_TONE1_SWITCH,
            2: TMT_PARAM_TONE2_SWITCH,
            3: TMT_PARAM_TONE3_SWITCH,
            4: TMT_PARAM_TONE4_SWITCH,
        }
        base = self.get_active_patch_base()
        tmt_base = add_address(base, OFFSET_PATCH_TMT)
        switch_addr = add_address(tmt_base, tmt_switch_offsets[tone_index])
        self.send_data(switch_addr, [1 if enabled else 0])

    def ensure_tone_enabled(self, tone_index: int) -> None:
        """Ensure tone switch is enabled (ON) in Tone Mix Table, routed to dry send,
        Tone Env Mode is set to SUSTAIN, and TVA Bias is neutral."""
        self.set_tone_switch(tone_index, True)

        # Also ensure tone dry send is non-zero (127) so it reaches the main output
        base = self.get_active_patch_base()
        offsets = {
            1: OFFSET_PATCH_TONE_1,
            2: OFFSET_PATCH_TONE_2,
            3: OFFSET_PATCH_TONE_3,
            4: OFFSET_PATCH_TONE_4,
        }
        t_addr = add_address(base, offsets[tone_index])
        self.send_data(add_address(t_addr, TONE_PARAM_DRY_SEND), [127])
        self.send_data(add_address(t_addr, TONE_PARAM_ENV_MODE), [1])  # 1 = SUSTAIN (allow infinite hold)
        self.send_data(add_address(t_addr, TONE_PARAM_TVA_BIAS_LEVEL), [64])  # 64 = 0 neutral (no keyboard attenuation)
        self.send_data(add_address(t_addr, TONE_PARAM_MATRIX_CTRL_SW_BASE), [1] * 16)  # Default all 16 matrix switches to ON

    def get_tone_wave(self, tone_index: int, timeout: float = 1.0) -> Tuple[str, int, int]:
        """Query active wave (bank, wave_num, group_type) for a tone (1..4)."""
        if tone_index not in (1, 2, 3, 4):
            raise ValueError(f"Tone index must be 1..4, got {tone_index}")
        base = self.get_active_patch_base(timeout=timeout)
        offsets = {
            1: OFFSET_PATCH_TONE_1,
            2: OFFSET_PATCH_TONE_2,
            3: OFFSET_PATCH_TONE_3,
            4: OFFSET_PATCH_TONE_4,
        }
        t_addr = add_address(base, offsets[tone_index])
        wave_addr = add_address(t_addr, TONE_PARAM_WAVE_GROUP_TYPE)
        # Size 9: 1 byte group type, 4 nibbles group id, 4 nibbles wave num L
        res = self.request_data(wave_addr, (0x00, 0x00, 0x00, 0x09), timeout=timeout)
        if res is None or len(res) < 9:
            raise TimeoutError(f"Timed out querying Tone {tone_index} wave info.")
        group_type = res[0]
        group_id = unpack_4nibbles(res[1:5])
        wave_num = unpack_4nibbles(res[5:9])
        bank = "INTA" if group_id == 1 else "INTB" if group_id == 2 else f"GROUP_{group_id}"
        return (bank, wave_num, group_type)

    def get_all_tone_waves(self, timeout: float = 1.0) -> list[Tuple[str, int]]:
        """Query active waveform (bank, wave_num) for all 4 tones."""
        waves = []
        for i in (1, 2, 3, 4):
            try:
                bank, wnum, _ = self.get_tone_wave(i, timeout=timeout)
                waves.append((bank, wnum))
            except Exception:
                waves.append(("INTA", 0))
        return waves

    def set_tone_wave(
        self,
        tone_index: int,
        bank: Optional[str] = "INTA",
        wave_num: Optional[int] = None,
        gain: Optional[int] = None,
        fxm_switch: Optional[int] = None,
        fxm_depth: Optional[int] = None,
    ) -> None:
        """Set Wave generator parameters for a tone."""
        if bank is not None or wave_num is not None:
            self.ensure_tone_enabled(tone_index)
        if bank is not None:
            bank_id = 1 if bank.upper() == "INTA" else 2
            self.set_tone_param(tone_index, TONE_PARAM_WAVE_GROUP_TYPE, 0)
            self.set_tone_param(tone_index, TONE_PARAM_WAVE_GROUP_ID, pack_4nibbles(bank_id))
            self.set_tone_param(tone_index, TONE_PARAM_WAVE_NUM_R, pack_4nibbles(0))
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

    def set_tone_step_lfo_type(self, tone_index: int, step_type: int) -> None:
        """Set Tone LFO Step Type (0 = TYP1/STEP, 1 = TYP2/GLIDE)."""
        self.set_tone_param(tone_index, TONE_PARAM_LFO_STEP_TYPE, max(0, min(1, int(step_type))))

    def set_tone_step_lfo_step(self, tone_index: int, step_index: int, val: int) -> None:
        """Set a single Tone LFO Step (step_index: 0..15, val: -36..+36 -> raw 28..100)."""
        if not (0 <= step_index < 16):
            raise ValueError(f"step_index must be 0..15, got {step_index}")
        raw = max(28, min(100, int(val) + 64))
        self.set_tone_param(tone_index, TONE_PARAM_LFO_STEP_1 + step_index, raw)

    def set_tone_step_lfo_steps(self, tone_index: int, steps: Sequence[int]) -> None:
        """Set all 16 steps in a contiguous 16-byte block starting at 0x010A."""
        raw_steps = [max(28, min(100, int(s) + 64)) for s in steps[:16]]
        if len(raw_steps) < 16:
            raw_steps.extend([64] * (16 - len(raw_steps)))
        self.set_tone_param(tone_index, TONE_PARAM_LFO_STEP_1, raw_steps)

    def set_tone_step_lfo_all(self, tone_index: int, step_type: int, steps: Sequence[int]) -> None:
        """Set all 16 steps and Step Type in a single contiguous 17-byte block to 0x0109."""
        t_type = max(0, min(1, int(step_type)))
        raw_steps = [max(28, min(100, int(s) + 64)) for s in steps[:16]]
        if len(raw_steps) < 16:
            raw_steps.extend([64] * (16 - len(raw_steps)))
        self.set_tone_param(tone_index, TONE_PARAM_LFO_STEP_TYPE, [t_type] + raw_steps)

    def set_portamento(self, enabled: bool, time: Optional[int] = None) -> None:
        """Set Portamento switch and optional time."""
        base = self.get_active_patch_base()
        self.send_data(add_address(base, PATCH_PARAM_PORTAMENTO_SWITCH), [1 if enabled else 0])
        if time is not None:
            self.send_data(add_address(base, PATCH_PARAM_PORTAMENTO_TIME), [max(0, min(127, int(time)))])

    def set_legato(self, enabled: bool) -> None:
        """Set Legato switch and Mono/Poly mode.
        Roland synthesis engine requires Mono/Poly to be MONO (0) for Legato to function.
        """
        base = self.get_active_patch_base()
        if enabled:
            self.send_data(add_address(base, PATCH_PARAM_MONO_POLY), [0])  # 0 = MONO
            self.send_data(add_address(base, PATCH_PARAM_LEGATO_SWITCH), [1])
            self.send_data(add_address(base, PATCH_PARAM_PORTAMENTO_MODE), [1])  # 1 = LEGATO
        else:
            self.send_data(add_address(base, PATCH_PARAM_LEGATO_SWITCH), [0])
            self.send_data(add_address(base, PATCH_PARAM_MONO_POLY), [1])  # 1 = POLY
            self.send_data(add_address(base, PATCH_PARAM_PORTAMENTO_MODE), [0])  # 0 = NORMAL

    def set_patch_analog_feel(self, val: int) -> None:
        """Set Patch Analog Feel (0..127)."""
        base = self.get_active_patch_base()
        self.send_data(add_address(base, PATCH_PARAM_ANALOG_FEEL), [max(0, min(127, int(val)))])

    def set_patch_offsets(
        self,
        cutoff: Optional[int] = None,
        resonance: Optional[int] = None,
        attack: Optional[int] = None,
        release: Optional[int] = None,
    ) -> None:
        """Set Patch Common macro offsets (1..127, center 64=0)."""
        base = self.get_active_patch_base()
        if cutoff is not None:
            self.send_data(add_address(base, PATCH_PARAM_CUTOFF_OFFSET), [max(1, min(127, int(cutoff)))])
        if resonance is not None:
            self.send_data(add_address(base, PATCH_PARAM_RESONANCE_OFFSET), [max(1, min(127, int(resonance)))])
        if attack is not None:
            self.send_data(add_address(base, PATCH_PARAM_ATTACK_OFFSET), [max(1, min(127, int(attack)))])
        if release is not None:
            self.send_data(add_address(base, PATCH_PARAM_RELEASE_OFFSET), [max(1, min(127, int(release)))])

    def set_matrix_control(
        self,
        ctrl_index: int,
        source: int,
        dest1: int = 0,
        sens1: int = 64,
        dest2: int = 0,
        sens2: int = 64,
        dest3: int = 0,
        sens3: int = 64,
        dest4: int = 0,
        sens4: int = 64,
    ) -> None:
        """Set Roland Patch Matrix Controller (ctrl_index 1..4)."""
        if ctrl_index not in (1, 2, 3, 4):
            raise ValueError(f"Matrix Controller index must be 1..4, got {ctrl_index}")
        base_offsets = {
            1: PATCH_PARAM_MATRIX_CTRL_1,
            2: PATCH_PARAM_MATRIX_CTRL_2,
            3: PATCH_PARAM_MATRIX_CTRL_3,
            4: PATCH_PARAM_MATRIX_CTRL_4,
        }
        base = self.get_active_patch_base()
        addr = add_address(base, base_offsets[ctrl_index])
        data = [
            max(0, min(109, int(source))),
            max(0, min(33, int(dest1))),
            max(1, min(127, int(sens1))),
            max(0, min(33, int(dest2))),
            max(1, min(127, int(sens2))),
            max(0, min(33, int(dest3))),
            max(1, min(127, int(sens3))),
            max(0, min(33, int(dest4))),
            max(1, min(127, int(sens4))),
        ]
        self.send_data(addr, data)

    def set_tone_matrix_switch(
        self,
        tone_index: int,
        ctrl_index: int,
        dest_index: int,
        switch_val: int = 1,
    ) -> None:
        """Set Tone Control Switch (ctrl_index 1..4, dest_index 1..4) for tone 1..4.
        switch_val: 0 = OFF, 1 = ON, 2 = REVERSE.
        """
        if not (1 <= tone_index <= 4 and 1 <= ctrl_index <= 4 and 1 <= dest_index <= 4):
            raise ValueError(
                f"tone_index, ctrl_index, and dest_index must be 1..4, got ({tone_index}, {ctrl_index}, {dest_index})"
            )
        offset = TONE_PARAM_MATRIX_CTRL_SW_BASE + (ctrl_index - 1) * 4 + (dest_index - 1)
        base = self.get_active_patch_base()
        offsets = {
            1: OFFSET_PATCH_TONE_1,
            2: OFFSET_PATCH_TONE_2,
            3: OFFSET_PATCH_TONE_3,
            4: OFFSET_PATCH_TONE_4,
        }
        t_addr = add_address(base, offsets[tone_index])
        addr = add_address(t_addr, offset)
        self.send_data(addr, [max(0, min(2, int(switch_val)))])

    def set_mfx(
        self,
        mfx_type: int,
        dry_send: Optional[int] = None,
        chorus_send: Optional[int] = None,
        reverb_send: Optional[int] = None,
    ) -> None:
        """Set MFX type and optional sends."""
        base = self.get_active_patch_base()
        mfx_base = add_address(base, OFFSET_PATCH_COMMON_MFX)
        self.send_data(add_address(mfx_base, MFX_PARAM_TYPE), [max(0, min(80, int(mfx_type)))])
        # On Roland JUNO-DS, also sync Performance Common MFX1 (10 00 02 00)
        perf_type_addr = (0x10, 0x00, 0x02, MFX_PARAM_TYPE)
        if add_address(mfx_base, MFX_PARAM_TYPE) != perf_type_addr:
            self.send_data(perf_type_addr, [max(0, min(80, int(mfx_type)))])
        if dry_send is not None:
            self.send_data(add_address(mfx_base, MFX_PARAM_DRY_SEND), [max(0, min(127, int(dry_send)))])
            self.send_data((0x10, 0x00, 0x02, MFX_PARAM_DRY_SEND), [max(0, min(127, int(dry_send)))])
        if chorus_send is not None:
            self.send_data(add_address(mfx_base, MFX_PARAM_CHORUS_SEND), [max(0, min(127, int(chorus_send)))])
            self.send_data((0x10, 0x00, 0x02, MFX_PARAM_CHORUS_SEND), [max(0, min(127, int(chorus_send)))])
        if reverb_send is not None:
            self.send_data(add_address(mfx_base, MFX_PARAM_REVERB_SEND), [max(0, min(127, int(reverb_send)))])
            self.send_data((0x10, 0x00, 0x02, MFX_PARAM_REVERB_SEND), [max(0, min(127, int(reverb_send)))])

    def set_mfx_param(self, param_index: int, value: int) -> None:
        """Set an individual MFX parameter (0..31) via Roland 4-nibble SysEx."""
        if not (0 <= param_index <= 31):
            raise ValueError(f"MFX parameter index must be 0..31, got {param_index}")
        base = self.get_active_patch_base()
        mfx_base = add_address(base, OFFSET_PATCH_COMMON_MFX)
        param_addr = add_address(mfx_base, MFX_PARAM_DATA_START + param_index * 4)
        raw_val = int(value) + 32768
        nibbles = pack_4nibbles(raw_val)
        self.send_data(param_addr, nibbles)
        # Also mirror to Performance Common MFX1 (10 00 02 xx)
        perf_param_addr = (0x10, 0x00, param_addr[2], param_addr[3])
        if param_addr != perf_param_addr:
            self.send_data(perf_param_addr, nibbles)

    def set_mfx_params_bulk(self, param_values: Sequence[int], start_index: int = 0) -> None:
        """Set a contiguous sequence of MFX parameters in a single SysEx DT1 packet."""
        if not param_values:
            return
        nibbles = []
        for val in param_values:
            raw_val = int(val) + 32768
            nibbles.extend(pack_4nibbles(raw_val))
        base = self.get_active_patch_base()
        mfx_base = add_address(base, OFFSET_PATCH_COMMON_MFX)
        param_addr = add_address(mfx_base, MFX_PARAM_DATA_START + start_index * 4)
        self.send_data(param_addr, nibbles)
        perf_param_addr = (0x10, 0x00, param_addr[2], param_addr[3])
        if param_addr != perf_param_addr:
            self.send_data(perf_param_addr, nibbles)

    def set_chorus(
        self,
        chorus_type: int,
        level: Optional[int] = None,
        output_select: Optional[int] = None,
    ) -> None:
        """Set Master Chorus type, level, and output routing."""
        c_type = max(0, min(3, int(chorus_type)))
        base = self.get_active_patch_base()
        cho_base = add_address(base, OFFSET_PATCH_COMMON_CHORUS)
        self.send_data(add_address(cho_base, CHORUS_PARAM_TYPE), [c_type])
        perf_base = (0x10, 0x00, 0x04, 0x00)
        self.send_data(perf_base, [c_type])
        self.send_data(ADDR_SETUP_CHORUS_SWITCH, [0 if c_type == 0 else 1])
        if level is not None:
            lvl = max(0, min(127, int(level)))
            self.send_data(add_address(cho_base, CHORUS_PARAM_LEVEL), [lvl])
            self.send_data((perf_base[0], perf_base[1], perf_base[2], CHORUS_PARAM_LEVEL), [lvl])
        if output_select is not None:
            out = max(0, min(2, int(output_select)))
            self.send_data(add_address(cho_base, CHORUS_PARAM_OUTPUT_SELECT), [out])
            self.send_data((perf_base[0], perf_base[1], perf_base[2], CHORUS_PARAM_OUTPUT_SELECT), [out])

    def set_chorus_param(self, param: str, val: int) -> None:
        """Set an individual Master Chorus 4-nibble parameter (rate, depth, preDelay, feedback)."""
        offset_map = {
            "preDelay": CHORUS_PARAM_PREDELAY,
            "predelay": CHORUS_PARAM_PREDELAY,
            "rate": CHORUS_PARAM_RATE,
            "depth": CHORUS_PARAM_DEPTH,
            "feedback": CHORUS_PARAM_FEEDBACK,
        }
        if param not in offset_map:
            logger.warning(f"Unknown chorus parameter: {param}")
            return
        offset = offset_map[param]
        clamped_val = max(0, min(127, int(val)))
        nibbles = pack_4nibbles(clamped_val + 32768)
        base = self.get_active_patch_base()
        cho_base = add_address(base, OFFSET_PATCH_COMMON_CHORUS)
        self.send_data(add_address(cho_base, offset), nibbles)
        perf_param_addr = (0x10, 0x00, 0x04, offset)
        if add_address(cho_base, offset) != perf_param_addr:
            self.send_data(perf_param_addr, nibbles)

    def set_reverb(
        self,
        reverb_type: int,
        level: Optional[int] = None,
    ) -> None:
        """Set Master Reverb type and level."""
        r_type = max(0, min(5, int(reverb_type)))
        base = self.get_active_patch_base()
        rev_base = add_address(base, OFFSET_PATCH_COMMON_REVERB)
        self.send_data(add_address(rev_base, REVERB_PARAM_TYPE), [r_type])
        perf_base = (0x10, 0x00, 0x06, 0x00)
        self.send_data(perf_base, [r_type])
        self.send_data(ADDR_SETUP_REVERB_SWITCH, [0 if r_type == 0 else 1])
        if level is not None:
            lvl = max(0, min(127, int(level)))
            self.send_data(add_address(rev_base, REVERB_PARAM_LEVEL), [lvl])
            self.send_data((perf_base[0], perf_base[1], perf_base[2], REVERB_PARAM_LEVEL), [lvl])

    def set_reverb_param(self, param: str, val: int) -> None:
        """Set an individual Master Reverb 4-nibble parameter (time, damp, preDelay, diffusion, tone)."""
        offset_map = {
            "preDelay": REVERB_PARAM_PREDELAY,
            "predelay": REVERB_PARAM_PREDELAY,
            "time": REVERB_PARAM_TIME,
            "damp": REVERB_PARAM_HF_DAMP,
            "hfDamp": REVERB_PARAM_HF_DAMP,
            "diffusion": REVERB_PARAM_DIFFUSION,
            "tone": REVERB_PARAM_TONE,
            "lowCut": REVERB_PARAM_TONE,
        }
        if param not in offset_map:
            logger.warning(f"Unknown reverb parameter: {param}")
            return
        offset = offset_map[param]
        clamped_val = max(0, min(127, int(val)))
        nibbles = pack_4nibbles(clamped_val + 32768)
        base = self.get_active_patch_base()
        rev_base = add_address(base, OFFSET_PATCH_COMMON_REVERB)
        self.send_data(add_address(rev_base, offset), nibbles)
        perf_param_addr = (0x10, 0x00, 0x06, offset)
        if add_address(rev_base, offset) != perf_param_addr:
            self.send_data(perf_param_addr, nibbles)

    def set_master_eq_param(self, param: str, val: Any) -> None:
        """Set Master 3-Band Parametric EQ parameter via Roland SysEx."""
        MID_FREQS = [200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000]
        MID_QS = [0.5, 0.7, 1.0, 1.4, 2.0, 4.0, 8.0, 16.0]

        if param == "switch":
            sw = 1 if val else 0
            self.send_data(add_address(ADDR_MASTER_EQ_BASE, MASTER_EQ_PARAM_SWITCH), [sw])
            self.send_data(ADDR_SYSTEM_PROCESSING_SWITCH, [sw])
        elif param == "lowFreq":
            freq_idx = int(val) if int(val) in (0, 1) else (1 if int(val) >= 300 else 0)
            self.send_data(add_address(ADDR_MASTER_EQ_BASE, MASTER_EQ_PARAM_LOW_FREQ), [freq_idx])
        elif param == "lowGain":
            gain_val = max(49, min(79, int(val) + 64))
            self.send_data(add_address(ADDR_MASTER_EQ_BASE, MASTER_EQ_PARAM_LOW_GAIN), [gain_val])
        elif param == "midFreq":
            target_f = int(val)
            closest_idx = min(range(len(MID_FREQS)), key=lambda i: abs(MID_FREQS[i] - target_f))
            self.send_data(add_address(ADDR_MASTER_EQ_BASE, MASTER_EQ_PARAM_MID_FREQ), [closest_idx])
        elif param == "midQ":
            target_q = float(val)
            closest_idx = min(range(len(MID_QS)), key=lambda i: abs(MID_QS[i] - target_q))
            self.send_data(add_address(ADDR_MASTER_EQ_BASE, MASTER_EQ_PARAM_MID_Q), [closest_idx])
        elif param == "midGain":
            gain_val = max(49, min(79, int(val) + 64))
            self.send_data(add_address(ADDR_MASTER_EQ_BASE, MASTER_EQ_PARAM_MID_GAIN), [gain_val])
        elif param == "highFreq":
            if int(val) in (0, 1, 2):
                h_idx = int(val)
            else:
                f = int(val)
                if f <= 3000:
                    h_idx = 0
                elif f <= 6000:
                    h_idx = 1
                else:
                    h_idx = 2
            self.send_data(add_address(ADDR_MASTER_EQ_BASE, MASTER_EQ_PARAM_HIGH_FREQ), [h_idx])
        elif param == "highGain":
            gain_val = max(49, min(79, int(val) + 64))
            self.send_data(add_address(ADDR_MASTER_EQ_BASE, MASTER_EQ_PARAM_HIGH_GAIN), [gain_val])
        elif param == "masterLevel":
            lvl = max(0, min(127, int(val)))
            self.send_data(ADDR_SYSTEM_MASTER_LEVEL, [lvl])

    def set_tone_pitch_env(
        self,
        tone_index: int,
        depth: Optional[int] = None,
        vel_sens: Optional[int] = None,
        time_keyfollow: Optional[int] = None,
        t1_vel_sens: Optional[int] = None,
        t4_vel_sens: Optional[int] = None,
        t1: Optional[int] = None,
        t2: Optional[int] = None,
        t3: Optional[int] = None,
        t4: Optional[int] = None,
        l0: Optional[int] = None,
        l1: Optional[int] = None,
        l2: Optional[int] = None,
        l3: Optional[int] = None,
        l4: Optional[int] = None,
    ) -> None:
        """Set Pitch Envelope parameters for a tone."""
        if depth is not None:
            self.set_tone_param(tone_index, TONE_PARAM_PITCH_ENV_DEPTH, max(52, min(76, depth)))
        if vel_sens is not None:
            self.set_tone_param(tone_index, TONE_PARAM_PITCH_ENV_VEL_SENS, max(1, min(127, vel_sens)))
        if time_keyfollow is not None:
            self.set_tone_param(tone_index, TONE_PARAM_PITCH_ENV_TIME_KEYFOLLOW, max(54, min(74, time_keyfollow)))
        if t1_vel_sens is not None:
            self.set_tone_param(tone_index, TONE_PARAM_PITCH_ENV_T1_VEL_SENS, max(1, min(127, t1_vel_sens)))
        if t4_vel_sens is not None:
            self.set_tone_param(tone_index, TONE_PARAM_PITCH_ENV_T4_VEL_SENS, max(1, min(127, t4_vel_sens)))
        if t1 is not None:
            self.set_tone_param(tone_index, TONE_PARAM_PITCH_ENV_T1, max(0, min(127, t1)))
        if t2 is not None:
            self.set_tone_param(tone_index, TONE_PARAM_PITCH_ENV_T2, max(0, min(127, t2)))
        if t3 is not None:
            self.set_tone_param(tone_index, TONE_PARAM_PITCH_ENV_T3, max(0, min(127, t3)))
        if t4 is not None:
            self.set_tone_param(tone_index, TONE_PARAM_PITCH_ENV_T4, max(0, min(127, t4)))
        if l0 is not None:
            self.set_tone_param(tone_index, TONE_PARAM_PITCH_ENV_L0, max(1, min(127, l0)))
        if l1 is not None:
            self.set_tone_param(tone_index, TONE_PARAM_PITCH_ENV_L1, max(1, min(127, l1)))
        if l2 is not None:
            self.set_tone_param(tone_index, TONE_PARAM_PITCH_ENV_L2, max(1, min(127, l2)))
        if l3 is not None:
            self.set_tone_param(tone_index, TONE_PARAM_PITCH_ENV_L3, max(1, min(127, l3)))
        if l4 is not None:
            self.set_tone_param(tone_index, TONE_PARAM_PITCH_ENV_L4, max(1, min(127, l4)))

    def read_patch_common(self, timeout: float = 1.0) -> PatchCommonState:
        """Read Patch Common block from synth RAM (size 0x4E / 78 bytes)."""
        base = self.get_active_patch_base(timeout=timeout)
        addr = add_address(base, OFFSET_PATCH_COMMON)
        res = self.request_data(addr, (0x00, 0x00, 0x00, 0x4E), timeout=timeout)
        if res is None or len(res) < 0x26:
            raise TimeoutError("Timed out reading Patch Common block.")

        name = res[0:12].decode("latin1", errors="replace").strip()
        cat = res[0x0C] if len(res) > 0x0C else 0
        lvl = res[0x0E] if len(res) > 0x0E else 100
        pan = res[0x0F] if len(res) > 0x0F else 64
        legato = bool(res[0x17]) if len(res) > 0x17 else False
        porta_sw = bool(res[0x19]) if len(res) > 0x19 else False
        porta_time = res[0x1D] if len(res) > 0x1D else 20
        cut_off = res[0x22] if len(res) > 0x22 else 64
        res_off = res[0x23] if len(res) > 0x23 else 64
        atk_off = res[0x24] if len(res) > 0x24 else 64
        rel_off = res[0x25] if len(res) > 0x25 else 64

        m_ctrls = []
        for i, off in enumerate([0x2B, 0x34, 0x3D, 0x46]):
            if len(res) >= off + 9:
                m_ctrls.append(
                    MatrixCtrlState(
                        source=res[off],
                        dest1=res[off + 1],
                        sens1=res[off + 2],
                        dest2=res[off + 3],
                        sens2=res[off + 4],
                        dest3=res[off + 5],
                        sens3=res[off + 6],
                        dest4=res[off + 7],
                        sens4=res[off + 8],
                    )
                )
            else:
                m_ctrls.append(MatrixCtrlState())

        return PatchCommonState(
            name=name,
            category=cat,
            level=lvl,
            pan=pan,
            cutoff_offset=cut_off,
            resonance_offset=res_off,
            attack_offset=atk_off,
            release_offset=rel_off,
            portamento_switch=porta_sw,
            portamento_time=porta_time,
            legato_switch=legato,
            matrix_ctrls=m_ctrls,
        )

    def read_tone(self, tone_index: int, timeout: float = 1.0) -> ToneState:
        """Read all parameters for a specific tone (1..4) from synth RAM."""
        if tone_index not in (1, 2, 3, 4):
            raise ValueError(f"Tone index must be 1..4, got {tone_index}")
        base = self.get_active_patch_base(timeout=timeout)
        offsets = {
            1: OFFSET_PATCH_TONE_1,
            2: OFFSET_PATCH_TONE_2,
            3: OFFSET_PATCH_TONE_3,
            4: OFFSET_PATCH_TONE_4,
        }
        t_base = add_address(base, offsets[tone_index])

        # Chunk 1: from 0x0000 to 0x007A (size 123 bytes = 0x7B)
        res1 = self.request_data(t_base, (0x00, 0x00, 0x00, 0x7B), timeout=timeout)
        if res1 is None or len(res1) < 0x7B:
            raise TimeoutError(f"Timed out reading Tone {tone_index} chunk 1.")

        level = res1[0x00]
        coarse = res1[0x01]
        fine = res1[0x02]
        pan = res1[0x04]
        matrix_switches = [
            list(res1[0x17:0x1B]),
            list(res1[0x1B:0x1F]),
            list(res1[0x1F:0x23]),
            list(res1[0x23:0x27]),
        ]

        # Wave
        group_type = res1[0x27]
        group_id = unpack_4nibbles(res1[0x28:0x2C])
        bank = "INTA" if group_id == 1 else "INTB" if group_id == 2 else f"GROUP_{group_id}"
        wave_l = unpack_4nibbles(res1[0x2C:0x30])
        wave_r = unpack_4nibbles(res1[0x30:0x34])
        wave_gain = res1[0x34]
        fxm_sw = bool(res1[0x35])
        fxm_color = res1[0x36]
        fxm_depth = res1[0x37]

        # Pitch Env
        p_depth = res1[0x3A]
        p_vel_sens = res1[0x3B]
        p_t1_vel = res1[0x3C]
        p_t4_vel = res1[0x3D]
        p_time_kf = res1[0x3E]
        p_t1 = res1[0x3F]
        p_t2 = res1[0x40]
        p_t3 = res1[0x41]
        p_t4 = res1[0x42]
        p_l0 = res1[0x43]
        p_l1 = res1[0x44]
        p_l2 = res1[0x45]
        p_l3 = res1[0x46]
        p_l4 = res1[0x47]

        # TVF
        tvf_type = res1[0x48]
        tvf_cutoff = res1[0x49]
        tvf_kf = res1[0x4A]
        tvf_reso = res1[0x4D]
        tvf_env_depth = res1[0x4F]
        tvf_env_vel = res1[0x51]
        tvf_t1 = res1[0x55]
        tvf_t2 = res1[0x56]
        tvf_t4 = res1[0x58]
        tvf_l3 = res1[0x5C]

        # TVA
        tva_vel = res1[0x62]
        tva_t1 = res1[0x66]
        tva_t2 = res1[0x67]
        tva_t4 = res1[0x69]
        tva_l3 = res1[0x6C]

        # LFO 1
        lfo1_wave = res1[0x6D]
        lfo1_rate = unpack_2nibbles(res1[0x6E:0x70])
        lfo1_delay = res1[0x72]
        lfo1_fade_m = res1[0x74]
        lfo1_fade_t = res1[0x75]
        lfo1_p_dep = res1[0x77]
        lfo1_f_dep = res1[0x78]
        lfo1_a_dep = res1[0x79]
        lfo1_pan_dep = res1[0x7A]

        # LFO 2 Chunk
        lfo2_addr_a = add_address(t_base, 0x007B)
        res2a = self.request_data(lfo2_addr_a, (0x00, 0x00, 0x00, 0x04), timeout=timeout)
        lfo2_wave = res2a[0] if res2a and len(res2a) > 0 else 0
        lfo2_rate = unpack_2nibbles(res2a[1:3]) if res2a and len(res2a) >= 3 else 45

        lfo2_addr_b = add_address(t_base, 0x0100)
        res2b = self.request_data(lfo2_addr_b, (0x00, 0x00, 0x00, 0x1A), timeout=timeout)
        lfo2_delay = res2b[0] if res2b and len(res2b) > 0 else 0
        lfo2_fade_m = res2b[2] if res2b and len(res2b) > 2 else 0
        lfo2_fade_t = res2b[3] if res2b and len(res2b) > 3 else 0
        lfo2_p_dep = res2b[5] if res2b and len(res2b) > 5 else 64
        lfo2_f_dep = res2b[6] if res2b and len(res2b) > 6 else 64
        lfo2_a_dep = res2b[7] if res2b and len(res2b) > 7 else 64
        lfo2_pan_dep = res2b[8] if res2b and len(res2b) > 8 else 64
        step_lfo_type = res2b[9] if res2b and len(res2b) > 9 else 0
        step_lfo_steps = [b - 64 for b in res2b[10:26]] if res2b and len(res2b) >= 26 else [0] * 16

        return ToneState(
            tone_index=tone_index,
            level=level,
            pan=pan,
            tva_velo_sens=tva_vel,
            tva_attack=tva_t1,
            tva_decay=tva_t2,
            tva_sustain=tva_l3,
            tva_release=tva_t4,
            tvf_filter_type=tvf_type,
            tvf_cutoff=tvf_cutoff,
            tvf_resonance=tvf_reso,
            tvf_cutoff_keyfollow=tvf_kf,
            tvf_env_depth=tvf_env_depth,
            tvf_env_velo_sens=tvf_env_vel,
            tvf_attack=tvf_t1,
            tvf_decay=tvf_t2,
            tvf_sustain=tvf_l3,
            tvf_release=tvf_t4,
            coarse_tune=coarse,
            fine_tune=fine,
            wave_bank_l=bank,
            wave_num_l=wave_l,
            wave_bank_r="INTA",
            wave_num_r=wave_r,
            wave_gain=wave_gain,
            wave_fxm_switch=fxm_sw,
            wave_fxm_color=fxm_color,
            wave_fxm_depth=fxm_depth,
            pitch_env_depth=p_depth,
            pitch_env_vel_sens=p_vel_sens,
            pitch_env_time_keyfollow=p_time_kf,
            pitch_env_t1_vel_sens=p_t1_vel,
            pitch_env_t4_vel_sens=p_t4_vel,
            pitch_env_t1=p_t1,
            pitch_env_t2=p_t2,
            pitch_env_t3=p_t3,
            pitch_env_t4=p_t4,
            pitch_env_l0=p_l0,
            pitch_env_l1=p_l1,
            pitch_env_l2=p_l2,
            pitch_env_l3=p_l3,
            pitch_env_l4=p_l4,
            lfo1_waveform=lfo1_wave,
            lfo1_rate=lfo1_rate,
            lfo1_pitch_depth=lfo1_p_dep,
            lfo1_tvf_depth=lfo1_f_dep,
            lfo1_tva_depth=lfo1_a_dep,
            lfo1_pan_depth=lfo1_pan_dep,
            lfo1_delay_time=lfo1_delay,
            lfo1_fade_mode=lfo1_fade_m,
            lfo1_fade_time=lfo1_fade_t,
            lfo2_waveform=lfo2_wave,
            lfo2_rate=lfo2_rate,
            lfo2_pitch_depth=lfo2_p_dep,
            lfo2_tvf_depth=lfo2_f_dep,
            lfo2_tva_depth=lfo2_a_dep,
            lfo2_pan_depth=lfo2_pan_dep,
            lfo2_delay_time=lfo2_delay,
            lfo2_fade_mode=lfo2_fade_m,
            lfo2_fade_time=lfo2_fade_t,
            step_lfo_type=step_lfo_type,
            step_lfo_steps=step_lfo_steps,
            matrix_switches=matrix_switches,
        )

    def read_all_tones(self, timeout: float = 1.0) -> list[ToneState]:
        """Read parameter states for all 4 tones."""
        tones = []
        for i in (1, 2, 3, 4):
            tones.append(self.read_tone(i, timeout=timeout))
        return tones

    def read_mfx(self, timeout: float = 1.0) -> Tuple[int, int, int, int, list[int]]:
        """Read MFX Type, Dry Send, Chorus Send, Reverb Send, and Parameters 1..32."""
        base = self.get_active_patch_base(timeout=timeout)
        mfx_addr = add_address(base, OFFSET_PATCH_COMMON_MFX)
        # Size 0x0111 in 7-bit arithmetic (145 bytes) reads type, sends, controls, and 32 params
        res = self.request_data(mfx_addr, (0x00, 0x00, 0x01, 0x11), timeout=timeout)
        if res is None or len(res) < 4:
            # Fallback to Performance Common MFX1 (10 00 02 00)
            res = self.request_data((0x10, 0x00, 0x02, 0x00), (0x00, 0x00, 0x01, 0x11), timeout=timeout)
        if res is None or len(res) < 4:
            raise TimeoutError("Timed out reading MFX block.")
        mfx_type, dry, cho, rev = res[0], res[1], res[2], res[3]
        params = [0] * 32
        param_start = 0x11
        if len(res) >= param_start + 4:
            avail_params = min(32, (len(res) - param_start) // 4)
            for i in range(avail_params):
                chunk = res[param_start + i * 4 : param_start + (i + 1) * 4]
                params[i] = unpack_4nibbles(chunk) - 32768
        return (mfx_type, dry, cho, rev, params)

    def read_chorus(self, timeout: float = 1.0) -> Tuple[int, int, int, int, int, int, int]:
        """Read Chorus Type, Level, Output Select, Pre-Delay, Rate, Depth, Feedback."""
        base = self.get_active_patch_base(timeout=timeout)
        cho_addr = add_address(base, OFFSET_PATCH_COMMON_CHORUS)
        res = self.request_data(cho_addr, (0x00, 0x00, 0x00, 0x28), timeout=timeout)
        if res is None or len(res) < 4:
            raise TimeoutError("Timed out reading Chorus block.")
        c_type = res[0]
        c_lvl = res[1]
        c_out = res[3] if len(res) > 3 else 0
        predelay = unpack_4nibbles(res[0x0C:0x10]) - 32768 if len(res) >= 0x10 else 0
        rate = unpack_4nibbles(res[0x14:0x18]) - 32768 if len(res) >= 0x18 else 0
        depth = unpack_4nibbles(res[0x1C:0x20]) - 32768 if len(res) >= 0x20 else 0
        feedback = unpack_4nibbles(res[0x24:0x28]) - 32768 if len(res) >= 0x28 else 0
        return (c_type, c_lvl, c_out, max(0, predelay), max(0, rate), max(0, depth), max(0, feedback))

    def read_reverb(self, timeout: float = 1.0) -> Tuple[int, int, int, int, int, int, int]:
        """Read Reverb Type, Level, Pre-Delay, Time, HF Damp, Diffusion, Tone."""
        base = self.get_active_patch_base(timeout=timeout)
        rev_addr = add_address(base, OFFSET_PATCH_COMMON_REVERB)
        res = self.request_data(rev_addr, (0x00, 0x00, 0x00, 0x20), timeout=timeout)
        if res is None or len(res) < 2:
            raise TimeoutError("Timed out reading Reverb block.")
        r_type = res[0]
        r_lvl = res[1]
        predelay = unpack_4nibbles(res[0x03:0x07]) - 32768 if len(res) >= 0x07 else 0
        time_val = unpack_4nibbles(res[0x07:0x0B]) - 32768 if len(res) >= 0x0B else 0
        damp = unpack_4nibbles(res[0x0F:0x13]) - 32768 if len(res) >= 0x13 else 0
        diffusion = unpack_4nibbles(res[0x17:0x1B]) - 32768 if len(res) >= 0x1B else 0
        tone = unpack_4nibbles(res[0x1B:0x1F]) - 32768 if len(res) >= 0x1F else 0
        return (r_type, r_lvl, max(0, predelay), max(0, time_val), max(0, damp), max(0, diffusion), max(0, tone))

    def read_full_patch(self, timeout: float = 1.0) -> PatchState:
        """Read complete patch state from Roland synth RAM."""
        common = self.read_patch_common(timeout=timeout)
        tones = self.read_all_tones(timeout=timeout)

        mfx_type, dry, cho, rev, mfx_params = (0, 127, 0, 0, [0] * 32)
        try:
            mfx_type, dry, cho, rev, mfx_params = self.read_mfx(timeout=timeout)
        except Exception as e:
            logger.warning(f"Could not read MFX: {e}")

        c_type, c_lvl, c_out, c_pre, c_rate, c_dep, c_fb = (0, 0, 0, 0, 0, 0, 0)
        try:
            c_type, c_lvl, c_out, c_pre, c_rate, c_dep, c_fb = self.read_chorus(timeout=timeout)
        except Exception as e:
            logger.warning(f"Could not read Chorus: {e}")

        r_type, r_lvl, r_pre, r_time, r_damp, r_diff, r_tone = (0, 0, 0, 0, 0, 0, 0)
        try:
            r_type, r_lvl, r_pre, r_time, r_damp, r_diff, r_tone = self.read_reverb(timeout=timeout)
        except Exception as e:
            logger.warning(f"Could not read Reverb: {e}")

        effects = EffectsState(
            mfx_type=mfx_type,
            mfx_dry_send=dry,
            mfx_chorus_send=cho,
            mfx_reverb_send=rev,
            mfx_bypassed=(mfx_type == 0),
            mfx_params=mfx_params,
            chorus_type=c_type,
            chorus_level=c_lvl,
            chorus_to_reverb=c_out,
            chorus_predelay=c_pre,
            chorus_rate=c_rate,
            chorus_depth=c_dep,
            chorus_feedback=c_fb,
            reverb_type=r_type,
            reverb_level=r_lvl,
            reverb_predelay=r_pre,
            reverb_time=r_time,
            reverb_damp=r_damp,
            reverb_diffusion=r_diff,
            reverb_tone=r_tone,
        )

        mode = self.get_sound_mode(timeout=timeout)
        patch_state = PatchState(
            sound_mode=mode.name,
            common=common,
            tones=tones,
            effects=effects,
        )
        return patch_state

    def init_patch(self) -> None:
        """Initialize the active temporary patch buffer to clean JUNO SPECTRE template."""
        # 1. Patch Common
        try:
            self.set_patch_name("JUNO SPECTRE")
        except Exception as e:
            logger.warning(f"Could not set patch name during init: {e}")

        self.set_patch_param("level", 100)
        self.set_patch_param("pan", 64)
        self.set_patch_param("cutoff_offset", 64)
        self.set_patch_param("resonance_offset", 64)
        self.set_patch_param("attack_offset", 64)
        self.set_patch_param("release_offset", 64)
        self.set_portamento(False, 20)
        self.set_legato(False)

        # 2. Reset Matrix Controls 1..4
        for i in (1, 2, 3, 4):
            try:
                self.set_matrix_control(i, source=0, dest1=0, sens1=64)
            except Exception as e:
                logger.warning(f"Could not reset matrix control {i}: {e}")

        # 3. Effects: Bypass MFX, Turn Off Chorus & Reverb
        try:
            self.set_mfx(mfx_type=0, dry_send=127, chorus_send=0, reverb_send=0)
            self.set_chorus(chorus_type=0, level=0)
            self.set_reverb(reverb_type=0, level=0)
        except Exception as e:
            logger.warning(f"Could not reset effects: {e}")

        # 4. 4 Tones: User Preset 756 "JUNO SPECTRE" waveforms
        default_waves = [
            ("INTA", 579),  # Juno Saw HD
            ("INTA", 600),  # Juno Sqr HD
            ("INTA", 622),  # JD Triangle
            ("INTA", 625),  # Sine
        ]

        for idx, (bank, wnum) in enumerate(default_waves, start=1):
            self.ensure_tone_enabled(idx)
            self.set_tone_wave(idx, bank=bank, wave_num=wnum, gain=1)  # 0 dB
            # TVF: Max cutoff (127), reso 0, env depth 64 (0), LPF (1), full sustain
            self.set_tone_tvf(
                idx,
                cutoff=127,
                resonance=0,
                env_depth=64,
                filter_type=1,
                attack=0,
                decay=0,
                sustain=127,
                release=0,
            )
            # TVA: Attack 0, Decay 0, Sustain 127, Release 0, Pan center 64
            self.set_tone_tva(
                idx,
                level=127,
                pan=64,
                attack=0,
                decay=0,
                sustain=127,
                release=0,
            )
            # Pitch: Coarse 64 (0 st), Fine 64 (0 c), Depth 64 (0)
            self.set_tone_pitch(idx, coarse=64, fine=64, env_depth=64)
            # Pitch Env: Neutral
            self.set_tone_pitch_env(
                idx,
                depth=64,
                vel_sens=64,
                time_keyfollow=64,
                t1=0, t2=0, t3=0, t4=0,
                l0=64, l1=64, l2=64, l3=64, l4=64
            )
            # LFO 1 & 2: Depths = 64 (0)
            self.set_tone_lfo(idx, lfo_index=1, waveform=1, rate=64, pitch_depth=64, tvf_depth=64, tva_depth=64, pan_depth=64)
            self.set_tone_lfo(idx, lfo_index=2, waveform=0, rate=45, pitch_depth=64, tvf_depth=64, tva_depth=64, pan_depth=64)
            # Step LFO: TYP1 (STEP), all 16 steps 0
            self.set_tone_step_lfo_all(idx, step_type=0, steps=[0] * 16)

