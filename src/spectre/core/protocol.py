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
    ADDR_SETUP,
    ADDR_TEMP_PATCH_PART_1,
    ADDR_TEMP_PERF_PART_1,
    CHORUS_PARAM_DATA_START,
    CHORUS_PARAM_LEVEL,
    CHORUS_PARAM_OUTPUT_SELECT,
    CHORUS_PARAM_TYPE,
    DEFAULT_DEVICE_ID,
    JUNO_DS_MODEL_ID,
    MFX_PARAM_CHORUS_SEND,
    MFX_PARAM_DATA_START,
    MFX_PARAM_DRY_SEND,
    MFX_PARAM_REVERB_SEND,
    MFX_PARAM_TYPE,
    OFFSET_PATCH_COMMON,
    OFFSET_PATCH_COMMON_CHORUS,
    OFFSET_PATCH_COMMON_MFX,
    OFFSET_PATCH_COMMON_REVERB,
    OFFSET_PATCH_TMT,
    OFFSET_PATCH_TONE_1,
    OFFSET_PATCH_TONE_2,
    OFFSET_PATCH_TONE_3,
    OFFSET_PATCH_TONE_4,
    PATCH_PARAM_ATTACK_OFFSET,
    PATCH_PARAM_CHORUS_SEND,
    PATCH_PARAM_CUTOFF_OFFSET,
    PATCH_PARAM_LEGATO_SWITCH,
    PATCH_PARAM_LEVEL,
    PATCH_PARAM_MATRIX_CTRL_1,
    PATCH_PARAM_MATRIX_CTRL_2,
    PATCH_PARAM_MATRIX_CTRL_3,
    PATCH_PARAM_MATRIX_CTRL_4,
    PATCH_PARAM_NAME,
    PATCH_PARAM_PAN,
    PATCH_PARAM_PORTAMENTO_SWITCH,
    PATCH_PARAM_PORTAMENTO_TIME,
    PATCH_PARAM_RELEASE_OFFSET,
    PATCH_PARAM_RESONANCE_OFFSET,
    PATCH_PARAM_REVERB_SEND,
    REVERB_PARAM_DATA_START,
    REVERB_PARAM_LEVEL,
    REVERB_PARAM_TYPE,
    TONE_PARAM_CHORUS_SEND,
    TONE_PARAM_COARSE_TUNE,
    TONE_PARAM_DRY_SEND,
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

    def ensure_tone_enabled(self, tone_index: int) -> None:
        """Ensure tone switch is enabled (ON) in the Tone Mix Table and routed to dry send."""
        if tone_index not in (1, 2, 3, 4):
            raise ValueError(f"Tone index must be 1..4, got {tone_index}")
        tmt_switch_offsets = {
            1: 0x0005,
            2: 0x000E,
            3: 0x0017,
            4: 0x0020,
        }
        base = self.get_active_patch_base()
        tmt_base = add_address(base, OFFSET_PATCH_TMT)
        switch_addr = add_address(tmt_base, tmt_switch_offsets[tone_index])
        self.send_data(switch_addr, [1])

        # Also ensure tone dry send is non-zero (127) so it reaches the main output
        offsets = {
            1: OFFSET_PATCH_TONE_1,
            2: OFFSET_PATCH_TONE_2,
            3: OFFSET_PATCH_TONE_3,
            4: OFFSET_PATCH_TONE_4,
        }
        t_addr = add_address(base, offsets[tone_index])
        self.send_data(add_address(t_addr, TONE_PARAM_DRY_SEND), [127])

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

    def set_portamento(self, enabled: bool, time: Optional[int] = None) -> None:
        """Set Portamento switch and optional time."""
        base = self.get_active_patch_base()
        self.send_data(add_address(base, PATCH_PARAM_PORTAMENTO_SWITCH), [1 if enabled else 0])
        if time is not None:
            self.send_data(add_address(base, PATCH_PARAM_PORTAMENTO_TIME), [max(0, min(127, int(time)))])

    def set_legato(self, enabled: bool) -> None:
        """Set Legato switch."""
        base = self.get_active_patch_base()
        self.send_data(add_address(base, PATCH_PARAM_LEGATO_SWITCH), [1 if enabled else 0])

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
        if dry_send is not None:
            self.send_data(add_address(mfx_base, MFX_PARAM_DRY_SEND), [max(0, min(127, int(dry_send)))])
        if chorus_send is not None:
            self.send_data(add_address(mfx_base, MFX_PARAM_CHORUS_SEND), [max(0, min(127, int(chorus_send)))])
        if reverb_send is not None:
            self.send_data(add_address(mfx_base, MFX_PARAM_REVERB_SEND), [max(0, min(127, int(reverb_send)))])

    def set_chorus(
        self,
        chorus_type: int,
        level: Optional[int] = None,
        output_select: Optional[int] = None,
    ) -> None:
        """Set Master Chorus type and level."""
        base = self.get_active_patch_base()
        cho_base = add_address(base, OFFSET_PATCH_COMMON_CHORUS)
        self.send_data(add_address(cho_base, CHORUS_PARAM_TYPE), [max(0, min(3, int(chorus_type)))])
        if level is not None:
            self.send_data(add_address(cho_base, CHORUS_PARAM_LEVEL), [max(0, min(127, int(level)))])
        if output_select is not None:
            self.send_data(add_address(cho_base, CHORUS_PARAM_OUTPUT_SELECT), [max(0, min(2, int(output_select)))])

    def set_reverb(
        self,
        reverb_type: int,
        level: Optional[int] = None,
    ) -> None:
        """Set Master Reverb type and level."""
        base = self.get_active_patch_base()
        rev_base = add_address(base, OFFSET_PATCH_COMMON_REVERB)
        self.send_data(add_address(rev_base, REVERB_PARAM_TYPE), [max(0, min(5, int(reverb_type)))])
        if level is not None:
            self.send_data(add_address(rev_base, REVERB_PARAM_LEVEL), [max(0, min(127, int(level)))])

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
        tvf_l3 = res1[0x5B]

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
        res2b = self.request_data(lfo2_addr_b, (0x00, 0x00, 0x00, 0x09), timeout=timeout)
        lfo2_delay = res2b[0] if res2b and len(res2b) > 0 else 0
        lfo2_fade_m = res2b[2] if res2b and len(res2b) > 2 else 0
        lfo2_fade_t = res2b[3] if res2b and len(res2b) > 3 else 0
        lfo2_p_dep = res2b[5] if res2b and len(res2b) > 5 else 64
        lfo2_f_dep = res2b[6] if res2b and len(res2b) > 6 else 64
        lfo2_a_dep = res2b[7] if res2b and len(res2b) > 7 else 64
        lfo2_pan_dep = res2b[8] if res2b and len(res2b) > 8 else 64

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
        )

    def read_all_tones(self, timeout: float = 1.0) -> list[ToneState]:
        """Read parameter states for all 4 tones."""
        tones = []
        for i in (1, 2, 3, 4):
            tones.append(self.read_tone(i, timeout=timeout))
        return tones

    def read_mfx(self, timeout: float = 1.0) -> Tuple[int, int, int, int]:
        """Read MFX Type, Dry Send, Chorus Send, Reverb Send."""
        base = self.get_active_patch_base(timeout=timeout)
        mfx_addr = add_address(base, OFFSET_PATCH_COMMON_MFX)
        res = self.request_data(mfx_addr, (0x00, 0x00, 0x00, 0x04), timeout=timeout)
        if res is None or len(res) < 4:
            raise TimeoutError("Timed out reading MFX block.")
        return (res[0], res[1], res[2], res[3])

    def read_chorus(self, timeout: float = 1.0) -> Tuple[int, int, int]:
        """Read Chorus Type, Level, Output Select."""
        base = self.get_active_patch_base(timeout=timeout)
        cho_addr = add_address(base, OFFSET_PATCH_COMMON_CHORUS)
        res = self.request_data(cho_addr, (0x00, 0x00, 0x00, 0x04), timeout=timeout)
        if res is None or len(res) < 4:
            raise TimeoutError("Timed out reading Chorus block.")
        return (res[0], res[1], res[3])

    def read_reverb(self, timeout: float = 1.0) -> Tuple[int, int]:
        """Read Reverb Type and Level."""
        base = self.get_active_patch_base(timeout=timeout)
        rev_addr = add_address(base, OFFSET_PATCH_COMMON_REVERB)
        res = self.request_data(rev_addr, (0x00, 0x00, 0x00, 0x02), timeout=timeout)
        if res is None or len(res) < 2:
            raise TimeoutError("Timed out reading Reverb block.")
        return (res[0], res[1])

    def read_full_patch(self, timeout: float = 1.0) -> PatchState:
        """Read complete patch state from Roland synth RAM."""
        common = self.read_patch_common(timeout=timeout)
        tones = self.read_all_tones(timeout=timeout)

        mfx_type, dry, cho, rev = (0, 127, 0, 0)
        try:
            mfx_type, dry, cho, rev = self.read_mfx(timeout=timeout)
        except Exception as e:
            logger.warning(f"Could not read MFX: {e}")

        c_type, c_lvl, c_out = (0, 0, 0)
        try:
            c_type, c_lvl, c_out = self.read_chorus(timeout=timeout)
        except Exception as e:
            logger.warning(f"Could not read Chorus: {e}")

        r_type, r_lvl = (0, 0)
        try:
            r_type, r_lvl = self.read_reverb(timeout=timeout)
        except Exception as e:
            logger.warning(f"Could not read Reverb: {e}")

        effects = EffectsState(
            mfx_type=mfx_type,
            mfx_dry_send=dry,
            mfx_chorus_send=cho,
            mfx_reverb_send=rev,
            mfx_bypassed=(mfx_type == 0),
            chorus_type=c_type,
            chorus_level=c_lvl,
            chorus_to_reverb=c_out,
            reverb_type=r_type,
            reverb_level=r_lvl,
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

