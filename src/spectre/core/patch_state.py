"""Synth patch data model for Roland JUNO-DS / XPS-30 and JunoSpectre.

Encapsulates complete Patch Common, 4 Tones (TVA, TVF, Pitch, Pitch Env, LFO 1/2),
Effects (MFX, Chorus, Reverb, Master EQ), Step LFO, and Performance Parts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence, Tuple


# Conversion helper maps
TVF_TYPE_NAMES = ["OFF", "LPF", "BPF", "HPF", "PKG", "LPF2", "LPF3"]
LFO_WAVE_NAMES = [
    "SIN",
    "TRI",
    "SAW-UP",
    "SAW-DW",
    "SQR",
    "RND",
    "BEND-UP",
    "BEND-DW",
    "TRP",
    "S&H",
    "CHS",
    "VSIN",
    "STEP",
]
LFO_FADE_MODE_NAMES = ["ON-IN", "ON-OUT", "OFF-IN", "OFF-OUT"]


@dataclass
class ToneState:
    """Complete parameter state for one Roland PCM Tone (Tone 1..4)."""
    tone_index: int = 1

    # TVA (Amplifier) & Level/Pan
    level: int = 127             # 0..127
    pan: int = 64                # 0..127 (L64 .. 63R, 64=Center)
    tva_velo_sens: int = 64      # 1..127 (-63 .. +63, 64=0)
    tva_env_t1_vel_sens: int = 64 # 1..127 (-63 .. +63, 64=0)
    tva_env_t4_vel_sens: int = 64 # 1..127 (-63 .. +63, 64=0)
    tva_env_time_keyfollow: int = 64 # 54..74 (-100 .. +100, 64=0)
    tva_t1: int = 0              # 0..127 (Attack time)
    tva_t2: int = 0              # 0..127 (Decay 1 time)
    tva_t3: int = 0              # 0..127 (Decay 2 time)
    tva_t4: int = 0              # 0..127 (Release time)
    tva_l1: int = 127            # 0..127 (Attack peak level)
    tva_l2: int = 127            # 0..127 (Decay break level)
    tva_l3: int = 127            # 0..127 (Sustain level)
    muted: bool = False

    # Tone Routing & Sends
    output_assign: int = 0       # 0: MFX, 1: DIRECT (L+R), 2: L, 3: R
    output_level: int = 127      # 0..127 (Tone Dry Send)
    chorus_send: int = 0         # 0..127
    reverb_send: int = 0         # 0..127

    # TVF (Filter)
    tvf_filter_type: int = 1     # 0..6 (OFF, LPF, BPF, HPF, PKG, LPF2, LPF3)
    tvf_cutoff: int = 127        # 0..127
    tvf_resonance: int = 0       # 0..127
    tvf_cutoff_keyfollow: int = 64 # 44..84 (-200 .. +200, 64=0)
    tvf_env_depth: int = 64      # 1..127 (-63 .. +63, 64=0)
    tvf_env_velo_sens: int = 64  # 1..127 (-63 .. +63, 64=0)
    tvf_env_t1_vel_sens: int = 64 # 1..127 (-63 .. +63, 64=0)
    tvf_env_t4_vel_sens: int = 64 # 1..127 (-63 .. +63, 64=0)
    tvf_env_time_keyfollow: int = 64 # 54..74 (-100 .. +100, 64=0)
    tvf_t1: int = 0              # 0..127 (Attack time)
    tvf_t2: int = 0              # 0..127 (Decay 1 time)
    tvf_t3: int = 0              # 0..127 (Decay 2 time)
    tvf_t4: int = 0              # 0..127 (Release time)
    tvf_l0: int = 0              # 0..127 (Start level)
    tvf_l1: int = 127            # 0..127 (Attack peak level)
    tvf_l2: int = 127            # 0..127 (Decay 1 break level)
    tvf_l3: int = 127            # 0..127 (Sustain level)
    tvf_l4: int = 0              # 0..127 (Release end level)

    # Pitch & Tuning
    coarse_tune: int = 64        # 16..112 (-48 .. +48, 64=0)
    fine_tune: int = 64          # 14..114 (-50 .. +50, 64=0)
    wave_bank_l: str = "INTA"
    wave_num_l: int = 579
    wave_bank_r: str = "INTA"
    wave_num_r: int = 0
    wave_gain: int = 1           # 0..3 (-6, 0, +6, +12 dB)
    wave_fxm_switch: bool = False
    wave_fxm_color: int = 0      # 0..3 (1..4)
    wave_fxm_depth: int = 0      # 0..16

    # Pitch Envelope
    pitch_env_depth: int = 76    # 52..76 (-12 .. +12, 64=0 -> +12)
    pitch_env_vel_sens: int = 94 # 1..127 (-63 .. +63, 64=0 -> +30)
    pitch_env_time_keyfollow: int = 64 # 54..74 (-100 .. +100, 64=0)
    pitch_env_t1_vel_sens: int = 64 # 1..127 (-63 .. +63, 64=0)
    pitch_env_t4_vel_sens: int = 64 # 1..127 (-63 .. +63, 64=0)
    pitch_env_t1: int = 20       # 0..127
    pitch_env_t2: int = 40       # 0..127
    pitch_env_t3: int = 50       # 0..127
    pitch_env_t4: int = 35       # 0..127
    pitch_env_l0: int = 64       # 1..127 (-63 .. +63, 64=0)
    pitch_env_l1: int = 88       # 1..127 (-63 .. +63, 64=0 -> +24)
    pitch_env_l2: int = 74       # 1..127 (-63 .. +63, 64=0 -> +10)
    pitch_env_l3: int = 64       # 1..127 (-63 .. +63, 64=0)
    pitch_env_l4: int = 64       # 1..127 (-63 .. +63, 64=0)

    # Tone LFO 1
    lfo1_waveform: int = 1       # 0..12 (1=TRI)
    lfo1_rate: int = 64          # 0..127
    lfo1_pitch_depth: int = 64   # 1..127 (-63 .. +63, 64=0)
    lfo1_tvf_depth: int = 64     # 1..127 (-63 .. +63, 64=0)
    lfo1_tva_depth: int = 64     # 1..127 (-63 .. +63, 64=0)
    lfo1_pan_depth: int = 64     # 1..127 (-63 .. +63, 64=0)
    lfo1_delay_time: int = 0     # 0..127
    lfo1_fade_mode: int = 0      # 0..3 (0: ON-IN)
    lfo1_fade_time: int = 0      # 0..127

    # Tone LFO 2
    lfo2_waveform: int = 0       # 0..12 (0=SIN)
    lfo2_rate: int = 45          # 0..127
    lfo2_pitch_depth: int = 64   # 1..127 (-63 .. +63, 64=0)
    lfo2_tvf_depth: int = 64     # 1..127 (-63 .. +63, 64=0)
    lfo2_tva_depth: int = 64     # 1..127 (-63 .. +63, 64=0)
    lfo2_pan_depth: int = 64     # 1..127 (-63 .. +63, 64=0)
    lfo2_delay_time: int = 0     # 0..127
    lfo2_fade_mode: int = 0      # 0..3 (0: ON-IN)
    lfo2_fade_time: int = 0      # 0..127

    # Tone Step LFO (Waveform #12 shape table: offsets 0x0109..0x0119)
    step_lfo_type: int = 0       # 0=TYP1 (STEP / HOLD), 1=TYP2 (GLIDE / LINEAR)
    step_lfo_steps: list[int] = field(default_factory=lambda: [0] * 16)  # -36 .. +36 (raw 28..100)

    # Tone Control 1..4 Destination 1..4 Switches (4 controllers x 4 destinations: 0=OFF, 1=ON, 2=REVERSE)
    matrix_switches: list[list[int]] = field(
        default_factory=lambda: [
            [1, 1, 1, 1],  # Ctrl 1: Dest 1..4
            [1, 1, 1, 1],  # Ctrl 2: Dest 1..4
            [1, 1, 1, 1],  # Ctrl 3: Dest 1..4
            [1, 1, 1, 1],  # Ctrl 4: Dest 1..4
        ]
    )

    # Convenience properties for UI bipolar representations
    @property
    def coarse_st(self) -> int:
        return self.coarse_tune - 64

    @property
    def fine_cents(self) -> int:
        return self.fine_tune - 64

    @property
    def pan_bipolar(self) -> int:
        return self.pan - 64

    @property
    def tvf_env_depth_bipolar(self) -> int:
        return self.tvf_env_depth - 64

    @property
    def tvf_keyfollow_percent(self) -> int:
        return (self.tvf_cutoff_keyfollow - 64) * 10

    @property
    def tvf_velo_sens_bipolar(self) -> int:
        return self.tvf_env_velo_sens - 64

    @property
    def tvf_env_t1_vel_sens_bipolar(self) -> int:
        return self.tvf_env_t1_vel_sens - 64

    @property
    def tvf_env_t4_vel_sens_bipolar(self) -> int:
        return self.tvf_env_t4_vel_sens - 64

    @property
    def tvf_env_time_kf_bipolar(self) -> int:
        return (self.tvf_env_time_keyfollow - 64) * 10

    @property
    def tva_velo_sens_bipolar(self) -> int:
        return self.tva_velo_sens - 64

    @property
    def tva_env_t1_vel_sens_bipolar(self) -> int:
        return self.tva_env_t1_vel_sens - 64

    @property
    def tva_env_t4_vel_sens_bipolar(self) -> int:
        return self.tva_env_t4_vel_sens - 64

    @property
    def tva_env_time_kf_bipolar(self) -> int:
        return (self.tva_env_time_keyfollow - 64) * 10

    # --- TVF envelope: ADSR quick controls as a lossless projection of the ---
    # --- real 4-time / 5-level hardware MSEG (T1..T4 / L0..L4).           ---
    @property
    def tvf_attack(self) -> int:
        return self.tvf_t1

    @tvf_attack.setter
    def tvf_attack(self, val: int) -> None:
        self.tvf_t1 = max(0, min(127, int(val)))

    @property
    def tvf_decay(self) -> int:
        return self.tvf_t2

    @tvf_decay.setter
    def tvf_decay(self, val: int) -> None:
        self.tvf_t2 = max(0, min(127, int(val)))

    @property
    def tvf_sustain(self) -> int:
        return self.tvf_l3

    @tvf_sustain.setter
    def tvf_sustain(self, val: int) -> None:
        val = max(0, min(127, int(val)))
        if self.tvf_l2 == self.tvf_l3:
            self.tvf_l2 = val
        self.tvf_l3 = val

    @property
    def tvf_release(self) -> int:
        return self.tvf_t4

    @tvf_release.setter
    def tvf_release(self, val: int) -> None:
        self.tvf_t4 = max(0, min(127, int(val)))

    @property
    def tvf_env_custom(self) -> bool:
        """True when TVF shape deviates from the canonical ADSR projection."""
        return bool(
            self.tvf_t3 != 0
            or self.tvf_l0 != 0
            or self.tvf_l1 != 127
            or self.tvf_l2 != self.tvf_l3
            or self.tvf_l4 != 0
        )

    def tvf_env_block(self) -> list[int]:
        """Raw contiguous hardware block: [T1..T4, L0..L4]."""
        return [self.tvf_t1, self.tvf_t2, self.tvf_t3, self.tvf_t4,
                self.tvf_l0, self.tvf_l1, self.tvf_l2, self.tvf_l3, self.tvf_l4]

    def set_tvf_env_block(self, block: Sequence[int]) -> None:
        self.tvf_t1, self.tvf_t2, self.tvf_t3, self.tvf_t4 = (int(v) for v in block[0:4])
        self.tvf_l0, self.tvf_l1, self.tvf_l2, self.tvf_l3, self.tvf_l4 = (int(v) for v in block[4:9])

    # --- TVA envelope: ADSR projection of 4-time / 3-level hardware MSEG ---
    @property
    def tva_attack(self) -> int:
        return self.tva_t1

    @tva_attack.setter
    def tva_attack(self, val: int) -> None:
        self.tva_t1 = max(0, min(127, int(val)))

    @property
    def tva_decay(self) -> int:
        return self.tva_t2

    @tva_decay.setter
    def tva_decay(self, val: int) -> None:
        self.tva_t2 = max(0, min(127, int(val)))

    @property
    def tva_sustain(self) -> int:
        return self.tva_l3

    @tva_sustain.setter
    def tva_sustain(self, val: int) -> None:
        val = max(0, min(127, int(val)))
        if self.tva_l2 == self.tva_l3:
            self.tva_l2 = val
        self.tva_l3 = val

    @property
    def tva_release(self) -> int:
        return self.tva_t4

    @tva_release.setter
    def tva_release(self, val: int) -> None:
        self.tva_t4 = max(0, min(127, int(val)))

    @property
    def tva_env_custom(self) -> bool:
        """True when TVA shape deviates from the canonical ADSR projection."""
        return bool(
            self.tva_t3 != 0
            or self.tva_l1 != 127
            or self.tva_l2 != self.tva_l3
        )

    def tva_env_block(self) -> list[int]:
        """Raw contiguous hardware block: [T1..T4, L1..L3]."""
        return [self.tva_t1, self.tva_t2, self.tva_t3, self.tva_t4,
                self.tva_l1, self.tva_l2, self.tva_l3]

    def set_tva_env_block(self, block: Sequence[int]) -> None:
        self.tva_t1, self.tva_t2, self.tva_t3, self.tva_t4 = (int(v) for v in block[0:4])
        self.tva_l1, self.tva_l2, self.tva_l3 = (int(v) for v in block[4:7])

    @property
    def tvf_type_str(self) -> str:
        if 0 <= self.tvf_filter_type < len(TVF_TYPE_NAMES):
            return TVF_TYPE_NAMES[self.tvf_filter_type]
        return "LPF"

    @property
    def pitch_env_depth_st(self) -> int:
        return self.pitch_env_depth - 64

    @property
    def pitch_env_vel_sens_bipolar(self) -> int:
        return self.pitch_env_vel_sens - 64

    @property
    def pitch_env_time_kf_bipolar(self) -> int:
        return (self.pitch_env_time_keyfollow - 64) * 10

    @property
    def pitch_env_t1_vel_sens_bipolar(self) -> int:
        return self.pitch_env_t1_vel_sens - 64

    @property
    def pitch_env_t4_vel_sens_bipolar(self) -> int:
        return self.pitch_env_t4_vel_sens - 64

    @property
    def pitch_env_l0_bipolar(self) -> int:
        return self.pitch_env_l0 - 64

    @property
    def pitch_env_l1_bipolar(self) -> int:
        return self.pitch_env_l1 - 64

    @property
    def pitch_env_l2_bipolar(self) -> int:
        return self.pitch_env_l2 - 64

    @property
    def pitch_env_l3_bipolar(self) -> int:
        return self.pitch_env_l3 - 64

    @property
    def pitch_env_l4_bipolar(self) -> int:
        return self.pitch_env_l4 - 64

    @property
    def lfo1_wave_str(self) -> str:
        if 0 <= self.lfo1_waveform < len(LFO_WAVE_NAMES):
            return LFO_WAVE_NAMES[self.lfo1_waveform]
        return "TRI"

    @property
    def lfo2_wave_str(self) -> str:
        if 0 <= self.lfo2_waveform < len(LFO_WAVE_NAMES):
            return LFO_WAVE_NAMES[self.lfo2_waveform]
        return "SIN"

    @property
    def lfo1_fade_mode_str(self) -> str:
        if 0 <= self.lfo1_fade_mode < len(LFO_FADE_MODE_NAMES):
            return LFO_FADE_MODE_NAMES[self.lfo1_fade_mode]
        return "ON-IN"

    @property
    def lfo2_fade_mode_str(self) -> str:
        if 0 <= self.lfo2_fade_mode < len(LFO_FADE_MODE_NAMES):
            return LFO_FADE_MODE_NAMES[self.lfo2_fade_mode]
        return "ON-IN"

    @property
    def step_lfo_type_str(self) -> str:
        return "GLIDE" if self.step_lfo_type == 1 else "STEP"


@dataclass
class MatrixCtrlState:
    """State for one Roland Patch Matrix Controller (1..4)."""
    source: int = 0              # 0..109
    dest1: int = 0               # 0..33
    sens1: int = 64              # 1..127 (-63 .. +63)
    dest2: int = 0
    sens2: int = 64
    dest3: int = 0
    sens3: int = 64
    dest4: int = 0
    sens4: int = 64


@dataclass
class PatchCommonState:
    """State for Roland Patch Common parameters."""
    name: str = "JUNO SPECTRE"
    category: int = 0
    level: int = 100             # 0..127
    pan: int = 64                # 0..127 (64=Center)
    cutoff_offset: int = 64      # 1..127 (64=0)
    resonance_offset: int = 64   # 1..127 (64=0)
    attack_offset: int = 64      # 1..127 (64=0)
    release_offset: int = 64     # 1..127 (64=0)
    portamento_switch: bool = False
    portamento_time: int = 20    # 0..127
    portamento_mode: int = 0     # 0=NORMAL, 1=LEGATO
    legato_switch: bool = False
    mono_poly: int = 1           # 0=MONO, 1=POLY
    analog_feel: int = 0         # 0..127
    chorus_send: int = 0         # 0..127
    reverb_send: int = 0         # 0..127
    patch_output_assign: int = 4 # 0: MFX, 1: L+R, 2: L, 3: R, 4: TONE (respect per-tone assign)
    matrix_ctrls: list[MatrixCtrlState] = field(default_factory=lambda: [
        MatrixCtrlState(source=1, dest1=1, sens1=94),   # CC01 Mod Wheel (id 1) -> PITCH (+30)
        MatrixCtrlState(source=96, dest1=2, sens1=39),  # Pitch Bend (id 96) -> TVF CUT (-25)
        MatrixCtrlState(source=102, dest1=4, sens1=64), # Velocity (id 102) -> TVA LEVEL (0)
        MatrixCtrlState(source=105, dest1=2, sens1=64), # LFO 1 (id 105) -> TVF CUT (0)
    ])


@dataclass
class EffectsState:
    """State for Roland MFX, Chorus, Reverb, and Master EQ."""
    # MFX Studio
    mfx_type: int = 15           # 15: Tape Echo
    mfx_dry_send: int = 127      # 0..127
    mfx_chorus_send: int = 0     # 0..127
    mfx_reverb_send: int = 0     # 0..127
    mfx_bypassed: bool = False
    mfx_last_active_type: int = 15 # 15: Tape Echo
    mfx_params: list[int] = field(default_factory=lambda: [0] * 32)

    # Clean Routing Topologies
    routing_preset: str = ""  # "" (none / raw patch), SERIAL_CHAIN, STUDIO_AUX, VINTAGE_SYNTH, AMBIENT_WASH, CUSTOM
    manual_routing_unlocked: bool = False

    # Master Chorus
    chorus_type: int = 1         # 0=OFF, 1=Chorus 1, 2=Delay, 3=GM2
    chorus_level: int = 80       # 0..127
    chorus_to_reverb: int = 0    # 0=MAIN, 1=REV, 2=MAIN+REV
    chorus_rate: int = 40        # 0..127
    chorus_depth: int = 65       # 0..127
    chorus_predelay: int = 12    # 0..127
    chorus_feedback: int = 20    # 0..127

    # Master Reverb
    reverb_type: int = 4         # 0=OFF, 1=Room 1, 2=Room 2, 3=Stage 1, 4=Hall 1, 5=Hall 2
    reverb_level: int = 60       # 0..127
    reverb_time: int = 70        # 0..127
    reverb_damp: int = 45        # 0..127
    reverb_predelay: int = 15    # 0..127
    reverb_diffusion: int = 60   # 0..127
    reverb_tone: int = 64        # 0..127

    # Master / System 3-Band Parametric EQ
    eq_switch: bool = True       # Master EQ Switch (ON / OFF)
    eq_low_gain: int = 2         # -15 .. +15 dB
    eq_low_freq: int = 400       # 200 or 400 Hz
    eq_mid_gain: int = -3        # -15 .. +15 dB
    eq_mid_freq: int = 1200      # 200 .. 8000 Hz
    eq_mid_q: float = 1.0        # 0.5, 1.0, 2.0, 4.0, 8.0
    eq_high_gain: int = 4        # -15 .. +15 dB
    eq_high_freq: int = 4000     # 2000, 4000, 8000 Hz
    eq_master_level: int = 100   # 0..127


@dataclass
class StepLfoState:
    """State for 16-Step Pattern Modulator."""
    steps: list[int] = field(default_factory=lambda: [0] * 16)
    curve_type: int = 0          # 0: STEP (HOLD), 1: GLIDE (LINEAR)
    sync_rate_idx: int = 2       # 2 = 1/16
    dest_idx: int = 1            # 0: PITCH, 1: TVF CUTOFF, 2: TVA LEVEL, 3: PAN
    depth: int = 48              # 0..127


@dataclass
class PerfPartState:
    """State for a single Performance Mode Part (Part 1..16)."""
    part_index: int = 1
    name: str = "Part 1"
    volume: int = 100            # 0..127
    pan: int = 64                # 0..127
    muted: bool = False
    solo: bool = False


@dataclass
class PatchState:
    """Master in-memory state representing the active synth patch and workstation settings."""
    sound_mode: str = "PATCH"
    common: PatchCommonState = field(default_factory=PatchCommonState)
    tones: list[ToneState] = field(default_factory=lambda: [
        ToneState(tone_index=1, wave_bank_l="INTA", wave_num_l=579), # Juno Saw HD
        ToneState(tone_index=2, wave_bank_l="INTA", wave_num_l=600), # Juno Sqr HD
        ToneState(tone_index=3, wave_bank_l="INTA", wave_num_l=622), # JD Triangle
        ToneState(tone_index=4, wave_bank_l="INTA", wave_num_l=625), # Sine
    ])
    effects: EffectsState = field(default_factory=EffectsState)
    step_lfo: StepLfoState = field(default_factory=StepLfoState)
    perf_parts: list[PerfPartState] = field(default_factory=lambda: [
        PerfPartState(part_index=i, name=f"Part {i}", volume=110 if i == 1 else (85 if i == 2 else 0))
        for i in range(1, 17)
    ])
    macros: list[int] = field(default_factory=lambda: [64, 64, 64, 64, 20, 0, 0, 25])

    # Workstation / VA state
    va_unison: bool = False  # Auto-detune disabled by default
    va_unison_detune: int = 15   # 0..50 cents
    va_custom_detunes: list[int] = field(default_factory=lambda: [64, 64, 64, 64])  # Cached raw Roland fine tune 14..114 (-50..+50 cents)
    va_pw: list[int] = field(default_factory=lambda: [50, 50, 50, 50])
    va_pwm: list[int] = field(default_factory=lambda: [0, 0, 0, 0])

    def get_tone(self, tone_number: int) -> ToneState:
        """Get ToneState by 1-based tone number (1..4)."""
        idx = max(1, min(4, tone_number)) - 1
        return self.tones[idx]

    @classmethod
    def create_init_patch(cls) -> "PatchState":
        """Generate a pristine, unmodulated JUNO SPECTRE initialization patch."""
        state = cls()
        state.sound_mode = "PATCH"
        state.common = PatchCommonState(
            name="JUNO SPECTRE",
            level=100,
            pan=64,
            cutoff_offset=64,
            resonance_offset=64,
            attack_offset=64,
            release_offset=64,
            portamento_switch=False,
            portamento_time=20,
            portamento_mode=0,
            legato_switch=False,
            mono_poly=1,
            analog_feel=0,
            chorus_send=0,
            reverb_send=25,
            matrix_ctrls=[
                MatrixCtrlState(source=1, dest1=1, sens1=94),   # CC01 Mod Wheel (id 1) -> PITCH (+30)
                MatrixCtrlState(source=96, dest1=2, sens1=39),  # Pitch Bend (id 96) -> TVF CUT (-25)
                MatrixCtrlState(source=102, dest1=4, sens1=64), # Velocity (id 102) -> TVA LEVEL (0)
                MatrixCtrlState(source=105, dest1=2, sens1=64), # LFO 1 (id 105) -> TVF CUT (0)
            ]
        )
        state.macros = [64, 64, 64, 64, 20, 0, 0, 25]

        init_waves = [
            ("INTA", 579), # Juno Saw HD
            ("INTA", 600), # Juno Sqr HD
            ("INTA", 622), # JD Triangle
            ("INTA", 625), # Sine
        ]

        state.tones = [
            ToneState(
                tone_index=idx,
                level=127,
                pan=64,
                coarse_tune=64,
                fine_tune=64,
                wave_bank_l=bank,
                wave_num_l=wnum,
                wave_gain=1, # 0 dB
                wave_fxm_switch=False,
                wave_fxm_depth=0,
                # TVF wide open LPF, 0 resonance, 0 env depth
                tvf_filter_type=1,
                tvf_cutoff=127,
                tvf_resonance=0,
                tvf_cutoff_keyfollow=64,
                tvf_env_depth=64,
                tvf_env_velo_sens=64,
                # TVF envelope raw segments (canonical flat gate shape)
                tvf_t1=0, tvf_t2=0, tvf_t3=0, tvf_t4=0,
                tvf_l0=0, tvf_l1=127, tvf_l2=127, tvf_l3=127, tvf_l4=0,
                # TVA envelope raw segments (canonical clean gate shape)
                tva_velo_sens=64,
                tva_t1=0, tva_t2=0, tva_t3=0, tva_t4=0,
                tva_l1=127, tva_l2=127, tva_l3=127,
                # Pitch Env neutral
                pitch_env_depth=64,
                pitch_env_vel_sens=64,
                pitch_env_time_keyfollow=64,
                pitch_env_t1=0,
                pitch_env_t2=0,
                pitch_env_t3=0,
                pitch_env_t4=0,
                pitch_env_l0=64,
                pitch_env_l1=64,
                pitch_env_l2=64,
                pitch_env_l3=64,
                pitch_env_l4=64,
                # LFO 1 & 2 neutral depths
                lfo1_waveform=1, # TRI
                lfo1_rate=64,
                lfo1_pitch_depth=64,
                lfo1_tvf_depth=64,
                lfo1_tva_depth=64,
                lfo1_pan_depth=64,
                lfo1_delay_time=0,
                lfo1_fade_time=0,
                lfo2_waveform=0, # SIN
                lfo2_rate=45,
                lfo2_pitch_depth=64,
                lfo2_tvf_depth=64,
                lfo2_tva_depth=64,
                lfo2_pan_depth=64,
                lfo2_delay_time=0,
                lfo2_fade_time=0,
                muted=False,
            )
            for idx, (bank, wnum) in enumerate(init_waves, start=1)
        ]

        state.effects = EffectsState(
            mfx_type=0, # Bypassed
            mfx_dry_send=127,
            mfx_chorus_send=0,
            mfx_reverb_send=0,
            mfx_bypassed=True,
            mfx_last_active_type=15,
            chorus_type=0, # OFF
            chorus_level=0,
            reverb_type=0, # OFF
            reverb_level=0,
            eq_switch=True,
            eq_low_gain=0,
            eq_low_freq=400,
            eq_mid_gain=0,
            eq_mid_freq=1200,
            eq_mid_q=1.0,
            eq_high_gain=0,
            eq_high_freq=4000,
            eq_master_level=100,
        )

        state.step_lfo = StepLfoState(
            steps=[0] * 16,
            curve_type=0,
            sync_rate_idx=2,
            dest_idx=1,
            depth=0,
        )

        state.macros = [64] * 8
        state.va_unison = False
        state.va_unison_detune = 15
        state.va_custom_detunes = [64, 64, 64, 64]
        state.va_pw = [50, 50, 50, 50]
        state.va_pwm = [0, 0, 0, 0]

        return state
