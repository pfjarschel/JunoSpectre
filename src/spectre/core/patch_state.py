"""Synth patch data model for Roland JUNO-DS / XPS-30 and JunoSpectre.

Encapsulates complete Patch Common, 4 Tones (TVA, TVF, Pitch, Pitch Env, LFO 1/2),
Effects (MFX, Chorus, Reverb, Master EQ), Step LFO, and Performance Parts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .sysex import unpack_2nibbles, unpack_4nibbles

# Canonical initialization template (single source of truth shared by
# protocol.init_patch, create_init_patch, PatchState.from_template, and bridge.initPatch).
INIT_PATCH_NAME = "JUNO SPECTRE"
INIT_TONE_WAVES: List[Tuple[str, int]] = [
    ("INTA", 579),  # Juno Saw HD
    ("INTA", 600),  # Juno Sqr HD
    ("INTA", 622),  # JD Triangle
    ("INTA", 625),  # Sine
]
TEMPLATE_ASSET_PATH = (
    Path(__file__).resolve().parent.parent / "assets" / "init_template.json"
)


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
    patch_output_assign: int = 13 # 0: MFX, 1: L+R, 2: L, 3: R, ... 13: TONE (respect per-tone assign)
    matrix_ctrls: list[MatrixCtrlState] = field(default_factory=lambda: [
        # Raw values captured from the user template patch (preserved as-is):
        MatrixCtrlState(source=98, dest1=9, sens1=74),
        MatrixCtrlState(source=99, dest1=4, sens1=64),
        MatrixCtrlState(source=100, dest1=4, sens1=64),
        MatrixCtrlState(source=101, dest1=4, sens1=64),
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



@dataclass
class StepLfoState:
    """State for 16-Step Pattern Modulator."""
    steps: list[int] = field(default_factory=lambda: [0] * 16)
    curve_type: int = 0          # 0: STEP (HOLD), 1: GLIDE (LINEAR)
    sync_rate_idx: int = 2       # 2 = 1/16
    dest_idx: int = 1            # 0: PITCH, 1: TVF CUTOFF, 2: TVA LEVEL, 3: PAN
    depth: int = 48              # 0..127


@dataclass
class MacroLink:
    """One macro -> param assignment (relative offset model).

    sounding = base + polarity * depth * span * macro_value
    macro_value in [-1, 1]; depth in [0, 1]; polarity in (+1, -1).
    Bases live in PatchState.macro_bases (per target key), captured lazily.
    """

    target_key: str = ""
    polarity: int = 1          # +1 | -1
    depth: float = 0.5         # 0..1 (stepped 25/50/75/100 in UI)
    # PERFORM only, for patch/part targets: [] = the edited part,
    # [0] = all sounding parts, else part numbers 1..16.
    parts: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.polarity not in (1, -1):
            self.polarity = 1 if self.polarity >= 0 else -1
        self.depth = max(0.0, min(1.0, float(self.depth)))
        try:
            nums = sorted({int(p) for p in (self.parts or []) if 0 <= int(p) <= 16})
        except (TypeError, ValueError):
            nums = []
        self.parts = [0] if 0 in nums else nums


@dataclass
class MacroSlot:
    """One customizable macro knob (relative, bipolar)."""

    name: str = "MACRO"
    value: float = 0.0         # -1..1, 0 = neutral
    links: list["MacroLink"] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.value = max(-1.0, min(1.0, float(self.value)))
        self.name = str(self.name)[:14] if self.name else "MACRO"


def default_macro_slots() -> list["MacroSlot"]:
    """Factory defaults replicating the legacy 8-knob deck as relative macros."""
    return [
        MacroSlot(name="CUTOFF", links=[MacroLink("common.cutoff_offset", 1, 1.0)]),
        MacroSlot(name="RESO", links=[MacroLink("common.resonance_offset", 1, 1.0)]),
        MacroSlot(name="ATTACK", links=[MacroLink("common.attack_offset", 1, 1.0)]),
        MacroSlot(name="RELEASE", links=[MacroLink("common.release_offset", 1, 1.0)]),
        MacroSlot(name="PORTA TIME", links=[MacroLink("common.portamento_time", 1, 0.5)]),
        MacroSlot(name="ANALOG FEEL", links=[MacroLink("common.analog_feel", 1, 0.5)]),
        MacroSlot(name="CHORUS", links=[MacroLink("effects.chorus_level", 1, 0.5)]),
        MacroSlot(name="REVERB", links=[MacroLink("effects.reverb_level", 1, 0.5)]),
    ]


@dataclass
class PerfMfxSlotState:
    """One shared Performance MFX (MFX1..MFX3) stored in Performance Common."""
    mfx_type: int = 0            # 0..80 (0 = bypass)
    dry_send: int = 127          # 0..127
    chorus_send: int = 0         # 0..127
    reverb_send: int = 0         # 0..127
    params: list[int] = field(default_factory=lambda: [0] * 32)
    source: int = 0              # 0=PERFORM, 1..16=PARTn (live reference)
    last_active_type: int = 15   # last nonzero type (restored on un-bypass)


@dataclass
class PerfFxState:
    """Shared Performance FX: 3x MFX + chorus + reverb + routing."""
    mfx1: PerfMfxSlotState = field(default_factory=PerfMfxSlotState)
    mfx2: PerfMfxSlotState = field(default_factory=PerfMfxSlotState)
    mfx3: PerfMfxSlotState = field(default_factory=PerfMfxSlotState)
    chorus_type: int = 1         # 0=OFF, 1..3
    chorus_level: int = 80       # 0..127
    chorus_to_reverb: int = 0    # 0=MAIN, 1=REV, 2=MAIN+REV
    chorus_source: int = 0       # 0=PERFORM, 1..16=PARTn
    chorus_rate: int = 40        # 0..127 (detail)
    chorus_depth: int = 65       # 0..127 (detail)
    chorus_predelay: int = 12    # 0..127 (detail)
    chorus_feedback: int = 20    # 0..127 (detail)
    reverb_type: int = 4         # 0=OFF, 1..5
    reverb_level: int = 60       # 0..127
    reverb_source: int = 0       # 0=PERFORM, 1..16=PARTn
    reverb_predelay: int = 15    # 0..127 (detail)
    reverb_time: int = 70        # 0..127 (detail)
    reverb_damp: int = 45        # 0..127 (detail)
    reverb_diffusion: int = 60   # 0..127 (detail)
    reverb_tone: int = 64        # 0..127 (detail)
    mfx_structure: int = 0       # 0..15 (TYPE01..TYPE16)


@dataclass
class PerfPartState:
    """State for a single Performance Mode Part (Part 1..16).

    Mixer fields map to the Performance Part block at 10 00 (0x20+N-1) 00
    (see JUNO-DS MIDI Implementation p.31). Patch refs select the sounding
    patch; rx_* control MIDI reception; key_low/high mirror the Performance
    Zone block for display (zones live per-channel at 10 00 (0x50+N-1) 00).
    """
    part_index: int = 1
    name: str = "Part 1"
    volume: int = 100            # 0..127 (Part Level, CC#7)
    pan: int = 64                # 0..127 (L64..63R)
    muted: bool = False          # Mute Switch (0=OFF sounding, 1=MUTE)
    solo: bool = False           # App-side; hardware solo is a single common select
    # Sounding patch selection (Bank Select + PC)
    patch_msb: int = 87          # 0..127 (87 = user bank default)
    patch_lsb: int = 64          # 0..127
    patch_pc: int = 0            # 0..127
    patch_name: str = ""         # Display cache (not on hardware part block)
    patch_file: str = ""         # Linked Pi .spectre file for Pi-only part sounds
    modified: bool = False       # Temp buffer differs from its slot/file (edited or Pi-only image)
    memory_only: bool = False    # Sound has no slot/file origin (e.g. INIT PERF template)
    # MIDI reception
    rx_channel: int = -1         # 0..15 (ch = rx_channel + 1); -1 = default to part
    rx_switch: bool = True       # Receive Switch OFF/ON
    # Tuning
    coarse_tune: int = 64        # 16..112 (-48..+48, 64=0)
    fine_tune: int = 64          # 14..114 (-50..+50, 64=0)
    octave_shift: int = 64       # 61..67 (-3..+3, 64=0)
    # Keyboard zone display mirror (actual zone block is per-channel)
    key_low: int = 0             # 0..127 (C-1..UPPER)
    key_high: int = 127          # 0..127 (LOWER..G9)
    zone_switch: bool = True     # Zone Switch OFF/ON (per-channel block)
    zone_octave: int = 64        # 61..67 (-3..+3, 64=0)
    # Performance output routing (Performance Part block 0x1C..0x20)
    dry_send: int = 127          # 0..127 (Part Dry Send Level)
    chorus_send: int = 0         # 0..127 (CC#93)
    reverb_send: int = 0         # 0..127 (CC#91)
    output_assign: int = 13      # 0..13 (PATCH=13 defers to tone assigns)
    mfx_select: int = 0          # 0..2 (MFX1, MFX2, MFX3)

    def __post_init__(self) -> None:
        if not 1 <= int(self.part_index) <= 16:
            self.part_index = max(1, min(16, int(self.part_index)))
        if int(self.rx_channel) < 0 or int(self.rx_channel) > 15:
            # Unset (-1) or out of range -> default musical mapping part N -> ch N.
            self.rx_channel = (int(self.part_index) - 1) % 16


@dataclass
class PatchState:
    """Master in-memory state representing the active synth patch and workstation settings."""
    sound_mode: str = "PATCH"
    common: PatchCommonState = field(default_factory=PatchCommonState)
    tones: list[ToneState] = field(default_factory=lambda: [
        ToneState(tone_index=i, wave_bank_l=bank, wave_num_l=wnum)
        for i, (bank, wnum) in enumerate(INIT_TONE_WAVES, start=1)
    ])
    effects: EffectsState = field(default_factory=EffectsState)
    step_lfo: StepLfoState = field(default_factory=StepLfoState)
    perf_parts: list[PerfPartState] = field(default_factory=lambda: [
        PerfPartState(part_index=i, name=f"Part {i}",
                      volume=110 if i == 1 else (85 if i == 2 else 0),
                      rx_channel=i - 1)
        for i in range(1, 17)
    ])
    # Display name of the temporary performance (Performance Common 12 chars).
    perf_name: str = "SPECTRE PERF"
    # Which performance part the patch editors target in PERFORM mode (1..16).
    active_perf_part: int = 1
    # Shared Performance FX (Performance Common MFX1-3 / chorus / reverb).
    perf_fx: PerfFxState = field(default_factory=PerfFxState)

    # Workstation / VA state (software-side only, never sent as a dedicated SysEx message)
    auto_detune: bool = False           # Auto Detune disabled by default
    auto_detune_cents: int = 15         # 0..50 cents
    custom_detune_cache: list[int] = field(default_factory=lambda: [64, 64, 64, 64])  # Cached raw Roland fine tune 14..114 (-50..+50 cents)
    va_pw: list[int] = field(default_factory=lambda: [50, 50, 50, 50])
    va_pwm: list[int] = field(default_factory=lambda: [0, 0, 0, 0])

    # Customizable relative macros (in-memory; plain data so future .spectre
    # save just serializes these). Bases are per-target sounding snapshots.
    macros: list[MacroSlot] = field(default_factory=default_macro_slots)
    macro_bases: Dict[str, float] = field(default_factory=dict)

    # Full device image snapshot (parity with init_template.json regions), even for
    # parameters the UI does not (yet) model. Snapshot-only: may go stale after
    # local per-parameter DT1 edits; refreshed on Sync (read_full_patch) and Init
    # (from_template). Layout: {"common": [80B], "mfx": [145B],
    # "chorus": [84B], "reverb": [83B], "tmt": [41B],
    # "tone_1": [154B, 26B], ...}.
    raw_regions: Dict[str, list[bytes]] = field(default_factory=dict)

    def get_tone(self, tone_number: int) -> ToneState:
        """Get ToneState by 1-based tone number (1..4)."""
        idx = max(1, min(4, tone_number)) - 1
        return self.tones[idx]

    @classmethod
    def create_init_patch(cls) -> "PatchState":
        """Offline fallback template matching the captured hardware image.

        When the init_template.json asset exists, prefer PatchState.from_template_file()
        so software state and hardware come from the exact same golden image.
        """
        state = cls()
        state.sound_mode = "PATCH"
        state.common = PatchCommonState(
            name=INIT_PATCH_NAME,
            level=127,
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
            patch_output_assign=13,
        )

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
                # Tone routing: serial chain (Tone -> MFX)
                output_assign=0,
                output_level=127,
                chorus_send=0,
                reverb_send=0,
                # TVF: LPF wide open, captured keyboard-init envelope shape
                tvf_filter_type=1,
                tvf_cutoff=127,
                tvf_resonance=0,
                tvf_cutoff_keyfollow=64,
                tvf_env_depth=64,
                tvf_env_velo_sens=64,
                tvf_env_t1_vel_sens=64,
                tvf_env_t4_vel_sens=64,
                tvf_env_time_keyfollow=64,
                tvf_t1=0, tvf_t2=10, tvf_t3=10, tvf_t4=64,
                tvf_l0=0, tvf_l1=127, tvf_l2=127, tvf_l3=127, tvf_l4=0,
                # TVA: captured keyboard-init envelope shape
                tva_velo_sens=96,
                tva_env_t1_vel_sens=64,
                tva_env_t4_vel_sens=64,
                tva_env_time_keyfollow=64,
                tva_t1=0, tva_t2=10, tva_t3=10, tva_t4=10,
                tva_l1=127, tva_l2=127, tva_l3=127,
                # Pitch Env: captured keyboard-init shape
                pitch_env_depth=64,
                pitch_env_vel_sens=64,
                pitch_env_t1_vel_sens=64,
                pitch_env_t4_vel_sens=64,
                pitch_env_time_keyfollow=64,
                pitch_env_t1=40,
                pitch_env_t2=80,
                pitch_env_t3=40,
                pitch_env_t4=0,
                pitch_env_l0=64,
                pitch_env_l1=34,
                pitch_env_l2=94,
                pitch_env_l3=64,
                pitch_env_l4=64,
                # LFO 1 & 2 neutral depths, captured defaults
                lfo1_waveform=1, # TRI
                lfo1_rate=92,
                lfo1_pitch_depth=64,
                lfo1_tvf_depth=64,
                lfo1_tva_depth=64,
                lfo1_pan_depth=64,
                lfo1_delay_time=0,
                lfo1_fade_time=0,
                lfo2_waveform=1, # TRI
                lfo2_rate=92,
                lfo2_pitch_depth=64,
                lfo2_tvf_depth=64,
                lfo2_tva_depth=64,
                lfo2_pan_depth=64,
                lfo2_delay_time=0,
                lfo2_fade_time=0,
                muted=False,
            )
            for idx, (bank, wnum) in enumerate(INIT_TONE_WAVES, start=1)
        ]

        state.effects = EffectsState(
            mfx_type=0, # Bypassed
            mfx_dry_send=127, # Tones feed the MFX block and pass through to Main (zero residue)
            mfx_chorus_send=0,
            mfx_reverb_send=0,
            mfx_bypassed=True,
            mfx_last_active_type=15,
            routing_preset="",
            manual_routing_unlocked=False,
            chorus_type=1, # Armed, but fed zero sends from the tones -> inaudible (template-true)
            chorus_level=127,
            chorus_to_reverb=0,
            chorus_rate=10,
            chorus_depth=20,
            chorus_predelay=20,
            chorus_feedback=0,
            reverb_type=3,
            reverb_level=127,
            reverb_predelay=10,
            reverb_time=64,
            reverb_damp=19,
            reverb_diffusion=127,
            reverb_tone=19,
        )

        state.step_lfo = StepLfoState(
            steps=[0] * 16,
            curve_type=0,
            sync_rate_idx=2,
            dest_idx=1,
            depth=0,
        )

        state.auto_detune = False
        state.auto_detune_cents = 15
        state.custom_detune_cache = [64, 64, 64, 64]
        state.va_pw = [50, 50, 50, 50]
        state.va_pwm = [0, 0, 0, 0]

        return state

    # ------------------------------------------------------------------
    # Golden init template: decode the captured hardware image (init_template.json)
    # ------------------------------------------------------------------

    @staticmethod
    def _region_bytes(payload_region: Dict[str, Any]) -> list[bytes]:
        return [bytes(c["bytes"]) for c in payload_region["chunks"]]

    @staticmethod
    def _param4v(block: bytes, offset: int) -> int:
        """Decode a 4-nibble parameter value and remove the 32768 bias."""
        return unpack_4nibbles(block[offset:offset + 4]) - 32768

    @classmethod
    def _decode_common(cls, b: bytes) -> PatchCommonState:
        matrices = []
        for off in (0x2B, 0x34, 0x3D, 0x46):
            matrices.append(MatrixCtrlState(
                source=b[off],
                dest1=b[off + 1], sens1=b[off + 2],
                dest2=b[off + 3], sens2=b[off + 4],
                dest3=b[off + 5], sens3=b[off + 6],
                dest4=b[off + 7], sens4=b[off + 8],
            ))
        return PatchCommonState(
            name=b[0:12].decode("latin1", errors="replace").strip(),
            category=b[0x0C],
            level=b[0x0E],
            pan=b[0x0F],
            analog_feel=b[0x15],
            mono_poly=b[0x16],
            legato_switch=bool(b[0x17]),
            portamento_switch=bool(b[0x19]),
            portamento_mode=b[0x1A],
            portamento_time=b[0x1D],
            cutoff_offset=b[0x22],
            resonance_offset=b[0x23],
            attack_offset=b[0x24],
            release_offset=b[0x25],
            patch_output_assign=b[0x27],
            matrix_ctrls=matrices,
        )

    @classmethod
    def _decode_tone(cls, a: bytes, b: bytes, tone_index: int) -> ToneState:
        return ToneState(
            tone_index=tone_index,
            level=a[0x00],
            coarse_tune=a[0x01],
            fine_tune=a[0x02],
            pan=a[0x04],
            output_level=a[0x0C],
            chorus_send=a[0x0D],
            reverb_send=a[0x0E],
            output_assign=a[0x11],
            matrix_switches=[
                list(a[0x17:0x1B]),
                list(a[0x1B:0x1F]),
                list(a[0x1F:0x23]),
                list(a[0x23:0x27]),
            ],
            wave_bank_l="INTA" if unpack_4nibbles(a[0x28:0x2C]) == 1 else "INTB",
            wave_num_l=unpack_4nibbles(a[0x2C:0x30]),
            wave_bank_r="INTA" if unpack_4nibbles(a[0x28:0x2C]) == 1 else "INTB",
            wave_num_r=unpack_4nibbles(a[0x30:0x34]),
            wave_gain=a[0x34],
            wave_fxm_switch=bool(a[0x35]),
            wave_fxm_color=a[0x36],
            wave_fxm_depth=a[0x37],
            pitch_env_depth=a[0x3A],
            pitch_env_vel_sens=a[0x3B],
            pitch_env_t1_vel_sens=a[0x3C],
            pitch_env_t4_vel_sens=a[0x3D],
            pitch_env_time_keyfollow=a[0x3E],
            pitch_env_t1=a[0x3F],
            pitch_env_t2=a[0x40],
            pitch_env_t3=a[0x41],
            pitch_env_t4=a[0x42],
            pitch_env_l0=a[0x43],
            pitch_env_l1=a[0x44],
            pitch_env_l2=a[0x45],
            pitch_env_l3=a[0x46],
            pitch_env_l4=a[0x47],
            tvf_filter_type=a[0x48],
            tvf_cutoff=a[0x49],
            tvf_cutoff_keyfollow=a[0x4A],
            tvf_resonance=a[0x4D],
            tvf_env_depth=a[0x4F],
            tvf_env_velo_sens=a[0x51],
            tvf_env_t1_vel_sens=a[0x52],
            tvf_env_t4_vel_sens=a[0x53],
            tvf_env_time_keyfollow=a[0x54],
            tvf_t1=a[0x55], tvf_t2=a[0x56], tvf_t3=a[0x57], tvf_t4=a[0x58],
            tvf_l0=a[0x59], tvf_l1=a[0x5A], tvf_l2=a[0x5B], tvf_l3=a[0x5C], tvf_l4=a[0x5D],
            tva_velo_sens=a[0x62],
            tva_env_t1_vel_sens=a[0x63],
            tva_env_t4_vel_sens=a[0x64],
            tva_env_time_keyfollow=a[0x65],
            tva_t1=a[0x66], tva_t2=a[0x67], tva_t3=a[0x68], tva_t4=a[0x69],
            tva_l1=a[0x6A], tva_l2=a[0x6B], tva_l3=a[0x6C],
            lfo1_waveform=a[0x6D],
            lfo1_rate=unpack_2nibbles(a[0x6E:0x70]),
            lfo1_delay_time=a[0x72],
            lfo1_fade_mode=a[0x74],
            lfo1_fade_time=a[0x75],
            lfo1_pitch_depth=a[0x77],
            lfo1_tvf_depth=a[0x78],
            lfo1_tva_depth=a[0x79],
            lfo1_pan_depth=a[0x7A],
            lfo2_waveform=a[0x7B],
            lfo2_rate=unpack_2nibbles(a[0x7C:0x7E]),
            lfo2_delay_time=b[0],
            lfo2_fade_mode=b[2],
            lfo2_fade_time=b[3],
            lfo2_pitch_depth=b[5],
            lfo2_tvf_depth=b[6],
            lfo2_tva_depth=b[7],
            lfo2_pan_depth=b[8],
            step_lfo_type=b[9],
            step_lfo_steps=[x - 64 for x in b[10:26]],
            muted=False,
        )

    @classmethod
    def _decode_effects(cls, mfx: bytes, cho: bytes, rev: bytes) -> EffectsState:
        eff = EffectsState()
        eff.mfx_type = mfx[0]
        eff.mfx_dry_send = mfx[1]
        eff.mfx_chorus_send = mfx[2]
        eff.mfx_reverb_send = mfx[3]
        eff.mfx_bypassed = (mfx[0] == 0)
        if mfx[0] != 0:
            eff.mfx_last_active_type = mfx[0]
        eff.mfx_params = [
            cls._param4v(mfx, 0x11 + 4 * i) for i in range(14)
        ]
        # The golden image is a raw patch: no routing preset was selected on it.
        eff.routing_preset = ""
        eff.manual_routing_unlocked = False
        eff.chorus_type = cho[0]
        eff.chorus_level = cho[1]
        eff.chorus_to_reverb = cho[3]
        eff.chorus_predelay = cls._param4v(cho, 0x0C)
        eff.chorus_rate = cls._param4v(cho, 0x14)
        eff.chorus_depth = cls._param4v(cho, 0x1C)
        eff.chorus_feedback = cls._param4v(cho, 0x24)
        eff.reverb_type = rev[0]
        eff.reverb_level = rev[1]
        eff.reverb_predelay = cls._param4v(rev, 0x03)
        eff.reverb_time = cls._param4v(rev, 0x07)
        eff.reverb_damp = cls._param4v(rev, 0x0F)
        eff.reverb_diffusion = cls._param4v(rev, 0x17)
        eff.reverb_tone = cls._param4v(rev, 0x1B)
        return eff

    @classmethod
    def from_template(cls, payload: Dict[str, Any]) -> "PatchState":
        """Build the canonical PatchState by decoding the captured hardware image blob."""
        regions = payload["regions"]
        common = cls._decode_common(cls._region_bytes(regions["common"])[0])

        tones = []
        for idx in range(1, 5):
            chunks = cls._region_bytes(regions[f"tone_{idx}"])
            tones.append(cls._decode_tone(chunks[0], chunks[1], idx))

        effects = cls._decode_effects(
            cls._region_bytes(regions["mfx"])[0],
            cls._region_bytes(regions["chorus"])[0],
            cls._region_bytes(regions["reverb"])[0],
        )

        # TMT tone switches -> mute state
        tmt = cls._region_bytes(regions["tmt"])[0]
        for idx, sw in enumerate((tmt[0x05], tmt[0x0E], tmt[0x17], tmt[0x20]), start=1):
            tones[idx - 1].muted = (sw == 0)

        state = cls(common=common, tones=tones, effects=effects)
        state.sound_mode = "PATCH"
        state.step_lfo = StepLfoState(
            steps=[0] * 16,
            curve_type=0,
            sync_rate_idx=2,
            dest_idx=1,
            depth=0,
        )
        state.custom_detune_cache = [t.fine_tune for t in tones]
        try:
            state.raw_regions = {
                key: [bytes(chunk) for chunk in cls._region_bytes(region)]
                for key, region in regions.items()
            }
        except (KeyError, IndexError, ValueError, TypeError):
            state.raw_regions = {}
        return state

    @classmethod
    def from_template_file(cls, path: Optional[Path] = None) -> Optional["PatchState"]:
        """Load and decode init_template.json; returns None when the asset is absent/corrupt."""
        asset = path or TEMPLATE_ASSET_PATH
        try:
            payload = json.loads(Path(asset).read_text(encoding="utf-8"))
            if payload.get("version") != 1 or "regions" not in payload:
                return None
            return cls.from_template(payload)
        except (OSError, ValueError, KeyError, IndexError):
            return None
