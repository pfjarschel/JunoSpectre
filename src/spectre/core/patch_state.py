"""Synth patch data model for Roland JUNO-DS / XPS-30 and JunoSpectre.

Encapsulates complete Patch Common, 4 Tones (TVA, TVF, Pitch, Pitch Env, LFO 1/2),
Effects (MFX, Chorus, Reverb), Step LFO, and Performance Parts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .sysex import TMT_TONE_RANGE_FIELDS, unpack_2nibbles, unpack_4nibbles

# Canonical initialization template (shared by protocol.init_patch,
# PatchState.from_template and bridge.initPatch).
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

    # Tone Mix Table: where on the keyboard / at which velocity the tone sounds
    key_range_lower: int = 0     # 0..127 (C-1..G9)
    key_range_upper: int = 127
    key_fade_lower: int = 0      # 0..127 (0 = hard edge)
    key_fade_upper: int = 0
    velo_range_lower: int = 1    # 1..127
    velo_range_upper: int = 127
    velo_fade_lower: int = 0     # 0..127
    velo_fade_upper: int = 0

    # Tone Routing & Sends
    output_assign: int = 0       # 0: MFX, 1: L+R, 5: L, 6: R (see core.routing)
    output_level: int = 127      # 0..127 (Tone Dry Send)
    chorus_send: int = 0         # 0..127, used while the sound goes into the MFX
    reverb_send: int = 0         # 0..127, used while the sound goes into the MFX
    chorus_send_direct: int = 0  # 0..127, used while the sound goes direct (0x0F)
    reverb_send_direct: int = 0  # 0..127, used while the sound goes direct (0x10)

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
    # Curves the envelope ADSR switch replaced: "tvf"/"tva"/"pitch" -> [T1..T4, L0..L4]
    env_originals: dict[str, list[int]] = field(default_factory=dict)

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

    # --- Envelopes: A/D/S/R controls over the 4-time / 5-level hardware ---
    # --- curves (core.env_shape). TVA levels are L1..L3 (L0 = L4 = 0).  ---
    _ENV_ATTRS = {
        "tvf": (("tvf_t1", "tvf_t2", "tvf_t3", "tvf_t4"),
                ("tvf_l0", "tvf_l1", "tvf_l2", "tvf_l3", "tvf_l4"), 0, (0, 127)),
        "tva": (("tva_t1", "tva_t2", "tva_t3", "tva_t4"),
                (None, "tva_l1", "tva_l2", "tva_l3", None), 0, (0, 127)),
        "pitch": (("pitch_env_t1", "pitch_env_t2", "pitch_env_t3", "pitch_env_t4"),
                  ("pitch_env_l0", "pitch_env_l1", "pitch_env_l2", "pitch_env_l3", "pitch_env_l4"), 64, (1, 127)),
    }

    def env_curve(self, env: str) -> tuple[list[int], list[int]]:
        """(times [T1..T4], levels [L0..L4]) of "tvf" / "tva" / "pitch"."""
        times, levels, center, _ = self._ENV_ATTRS[env]
        return ([getattr(self, a) for a in times],
                [getattr(self, a) if a else center for a in levels])

    def set_env_curve(self, env: str, times: Sequence[int], levels: Sequence[int]) -> None:
        t_attrs, l_attrs, _, _ = self._ENV_ATTRS[env]
        for a, v in zip(t_attrs, times):
            setattr(self, a, int(v))
        for a, v in zip(l_attrs, levels):
            if a:
                setattr(self, a, int(v))

    def env_stage(self, env: str, stage: str) -> int:
        from . import env_shape

        times, levels = self.env_curve(env)
        return env_shape.value(stage, times, levels, self._ENV_ATTRS[env][2])

    def set_env_stage(self, env: str, stage: str, val: int) -> None:
        """Move one A/D/S/R control. Moves are taken from a snapshot of the curve,
        kept until the curve changes some other way (editor, patch load)."""
        from . import env_shape

        _, _, center, level_range = self._ENV_ATTRS[env]
        cur = self.env_curve(env)
        snaps = self.__dict__.setdefault("_env_snaps", {})
        snap = snaps.get(env)
        if snap is None or snap[1] != cur:
            snap = snaps[env] = [cur, cur]
        new = env_shape.apply(stage, val, cur, snap[0], center, level_range)
        self.set_env_curve(env, *new)
        snap[1] = self.env_curve(env)

    def env_is_adsr(self, env: str) -> bool:
        from . import env_shape

        return env_shape.is_adsr(*self.env_curve(env), self._ENV_ATTRS[env][2])

    def env_to_adsr(self, env: str, keep_original: bool = True) -> None:
        """Make the curve a plain ADSR; the original is kept to switch back to."""
        from . import env_shape

        if self.env_is_adsr(env):
            return
        times, levels = self.env_curve(env)
        if keep_original:
            self.env_originals[env] = times + levels
        self.set_env_curve(env, *env_shape.to_adsr(times, levels, self._ENV_ATTRS[env][2]))

    def env_restore(self, env: str) -> bool:
        """Back to the curve the ADSR switch replaced (edits made since are dropped)."""
        block = self.env_originals.pop(env, None)
        if not block:
            return False
        self.set_env_curve(env, block[:4], block[4:9])
        return True

    def env_forget_broken_original(self, env: str) -> None:
        """A stored original lives only while the curve keeps the ADSR shape."""
        if env in self.env_originals and not self.env_is_adsr(env):
            del self.env_originals[env]

    tvf_attack = property(lambda s: s.env_stage("tvf", "attack"),
                          lambda s, v: s.set_env_stage("tvf", "attack", v))
    tvf_decay = property(lambda s: s.env_stage("tvf", "decay"),
                         lambda s, v: s.set_env_stage("tvf", "decay", v))
    tvf_sustain = property(lambda s: s.env_stage("tvf", "sustain"),
                           lambda s, v: s.set_env_stage("tvf", "sustain", v))
    tvf_release = property(lambda s: s.env_stage("tvf", "release"),
                           lambda s, v: s.set_env_stage("tvf", "release", v))
    tva_attack = property(lambda s: s.env_stage("tva", "attack"),
                          lambda s, v: s.set_env_stage("tva", "attack", v))
    tva_decay = property(lambda s: s.env_stage("tva", "decay"),
                         lambda s, v: s.set_env_stage("tva", "decay", v))
    tva_sustain = property(lambda s: s.env_stage("tva", "sustain"),
                           lambda s, v: s.set_env_stage("tva", "sustain", v))
    tva_release = property(lambda s: s.env_stage("tva", "release"),
                           lambda s, v: s.set_env_stage("tva", "release", v))
    pitch_env_attack = property(lambda s: s.env_stage("pitch", "attack"),
                                lambda s, v: s.set_env_stage("pitch", "attack", v))
    pitch_env_decay = property(lambda s: s.env_stage("pitch", "decay"),
                               lambda s, v: s.set_env_stage("pitch", "decay", v))
    pitch_env_sustain = property(lambda s: s.env_stage("pitch", "sustain"),
                                 lambda s, v: s.set_env_stage("pitch", "sustain", v))
    pitch_env_release = property(lambda s: s.env_stage("pitch", "release"),
                                 lambda s, v: s.set_env_stage("pitch", "release", v))

    @property
    def tvf_env_custom(self) -> bool:
        """True when the TVF curve is not a plain ADSR."""
        return not self.env_is_adsr("tvf")

    def tvf_env_block(self) -> list[int]:
        """Raw contiguous hardware block: [T1..T4, L0..L4]."""
        return [self.tvf_t1, self.tvf_t2, self.tvf_t3, self.tvf_t4,
                self.tvf_l0, self.tvf_l1, self.tvf_l2, self.tvf_l3, self.tvf_l4]

    def set_tvf_env_block(self, block: Sequence[int]) -> None:
        self.tvf_t1, self.tvf_t2, self.tvf_t3, self.tvf_t4 = (int(v) for v in block[0:4])
        self.tvf_l0, self.tvf_l1, self.tvf_l2, self.tvf_l3, self.tvf_l4 = (int(v) for v in block[4:9])

    @property
    def tva_env_custom(self) -> bool:
        """True when the TVA curve is not a plain ADSR."""
        return not self.env_is_adsr("tva")

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
    patch_output_assign: int = 13 # 0: MFX, 1: L+R, 5: L, 6: R, 13: TONE (respect per-tone assign)
    structure_12: int = 0        # TMT 0x00, 0..9 = TYPE1..10 (2..10 merge tone 1 into tone 2)
    structure_34: int = 0        # TMT 0x02, 0..9 = TYPE1..10 (2..10 merge tone 3 into tone 4)
    booster_12: int = 0          # TMT 0x01, 0..3 = 0/+6/+12/+18 dB (structure types 3, 4)
    booster_34: int = 0          # TMT 0x03
    tmt_velocity_control: int = 0  # TMT 0x04, 0..3 = OFF/ON/RANDOM/CYCLE
    tmt_control_switch: int = 0  # common 0x28, 0..1: Matrix Control picks the tones
    matrix_ctrls: list[MatrixCtrlState] = field(default_factory=lambda: [
        # Raw values captured from the user template patch (preserved as-is):
        MatrixCtrlState(source=98, dest1=9, sens1=74),
        MatrixCtrlState(source=99, dest1=4, sens1=64),
        MatrixCtrlState(source=100, dest1=4, sens1=64),
        MatrixCtrlState(source=101, dest1=4, sens1=64),
    ])


@dataclass
class EffectsState:
    """State for Roland MFX, Chorus and Reverb."""
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



# MFX / chorus / reverb blocks: the patch, performance common and part-patch
# blocks share one layout, so these decode all of them.

def _param4(block: bytes, offset: int) -> int:
    """A 4-nibble parameter without its 32768 bias (0 when the block is short)."""
    if len(block) < offset + 4:
        return 0
    return unpack_4nibbles(block[offset:offset + 4]) - 32768


def decode_mfx_block(b: bytes) -> Tuple[int, int, int, int, list[int]]:
    """(type, dry send, chorus send, reverb send, 32 params)."""
    return b[0], b[1], b[2], b[3], [_param4(b, 0x11 + 4 * i) for i in range(32)]


def decode_chorus_block(b: bytes) -> Tuple[int, int, int, int, int, int, int]:
    """(type, level, output select, pre-delay, rate, depth, feedback)."""
    return (b[0], b[1], b[3] if len(b) > 3 else 0,
            max(0, _param4(b, 0x0C)), max(0, _param4(b, 0x14)),
            max(0, _param4(b, 0x1C)), max(0, _param4(b, 0x24)))


def decode_reverb_block(b: bytes) -> Tuple[int, int, int, int, int, int, int]:
    """(type, level, pre-delay, time, HF damp, diffusion, tone)."""
    return (b[0], b[1],
            max(0, _param4(b, 0x03)), max(0, _param4(b, 0x07)), max(0, _param4(b, 0x0F)),
            max(0, _param4(b, 0x17)), max(0, _param4(b, 0x1B)))


def effects_from_blocks(mfx: bytes, cho: bytes, rev: bytes) -> "EffectsState":
    m_type, dry, m_cho, m_rev, params = decode_mfx_block(mfx)
    c_type, c_lvl, c_out, c_pre, c_rate, c_depth, c_fb = decode_chorus_block(cho)
    r_type, r_lvl, r_pre, r_time, r_damp, r_diff, r_tone = decode_reverb_block(rev)
    return EffectsState(
        mfx_type=m_type, mfx_dry_send=dry, mfx_chorus_send=m_cho, mfx_reverb_send=m_rev,
        mfx_bypassed=(m_type == 0), mfx_last_active_type=m_type or 15, mfx_params=params,
        routing_preset="",  # a raw synth image carries no routing preset
        chorus_type=c_type, chorus_level=c_lvl, chorus_to_reverb=c_out,
        chorus_predelay=c_pre, chorus_rate=c_rate, chorus_depth=c_depth, chorus_feedback=c_fb,
        reverb_type=r_type, reverb_level=r_lvl, reverb_predelay=r_pre, reverb_time=r_time,
        reverb_damp=r_damp, reverb_diffusion=r_diff, reverb_tone=r_tone,
    )


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
    """One customizable macro knob (relative, bipolar).

    name "" = automatic: named after its links (auto_macro_name).
    """

    name: str = ""
    value: float = 0.0         # -1..1, 0 = neutral
    links: list["MacroLink"] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.value = max(-1.0, min(1.0, float(self.value)))
        self.name = str(self.name or "")[:14]


MACRO_NAME_MAX = 14


def auto_macro_name(index: int, link_names: list[str]) -> str:
    """Name of macro `index` (1-based) from its links' short names.

    No link: "M1"; one: its name; several: joined with "+" while they fit,
    else the first one and a count ("CUTOFF +2").
    """
    names = [n.upper() for n in link_names if n]
    if not names:
        return f"M{index}"
    joined = "+".join(names)
    if len(joined) <= MACRO_NAME_MAX:
        return joined
    more = f" +{len(names) - 1}" if len(names) > 1 else ""
    return names[0][:MACRO_NAME_MAX - len(more)].rstrip() + more


def default_macro_slots() -> list["MacroSlot"]:
    """Factory default macro slots (relative macros)."""
    return [
        MacroSlot(links=[MacroLink("common.cutoff_offset", 1, 1.0)]),
        MacroSlot(links=[MacroLink("common.resonance_offset", 1, 1.0)]),
        MacroSlot(links=[MacroLink("common.attack_offset", 1, 1.0)]),
        MacroSlot(links=[MacroLink("common.release_offset", 1, 1.0)]),
        MacroSlot(links=[MacroLink("common.portamento_time", 1, 0.5)]),
        MacroSlot(links=[MacroLink("common.analog_feel", 1, 0.5)]),
        MacroSlot(links=[MacroLink("effects.chorus_level", 1, 0.5)]),
        MacroSlot(links=[MacroLink("effects.reverb_level", 1, 0.5)]),
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

    # ------------------------------------------------------------------
    # Golden init template: decode the captured hardware image (init_template.json)
    # ------------------------------------------------------------------

    @staticmethod
    def _region_bytes(payload_region: Dict[str, Any]) -> list[bytes]:
        return [bytes(c["bytes"]) for c in payload_region["chunks"]]

    @staticmethod
    def apply_tmt(tmt: bytes, common: PatchCommonState, tones: list,
                  mutes: bool = True) -> None:
        """TMT bytes -> structure/booster/velocity control, tone mutes
        (switches) and each tone's key/velocity range."""
        for attr, off in (("structure_12", 0x00), ("booster_12", 0x01), ("structure_34", 0x02),
                          ("booster_34", 0x03), ("tmt_velocity_control", 0x04)):
            if len(tmt) > off:
                setattr(common, attr, int(tmt[off]))
        for tone, off in zip(tones, (0x05, 0x0E, 0x17, 0x20)):
            if mutes and len(tmt) > off:
                tone.muted = (tmt[off] == 0)
            for i, attr in enumerate(TMT_TONE_RANGE_FIELDS, start=1):
                if len(tmt) > off + i:
                    setattr(tone, attr, int(tmt[off + i]))

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
            tmt_control_switch=b[0x28],
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
            chorus_send_direct=a[0x0F],
            reverb_send_direct=a[0x10],
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
    def from_template(cls, payload: Dict[str, Any]) -> "PatchState":
        """Build the canonical PatchState by decoding the captured hardware image blob."""
        regions = payload["regions"]
        common = cls._decode_common(cls._region_bytes(regions["common"])[0])

        tones = []
        for idx in range(1, 5):
            chunks = cls._region_bytes(regions[f"tone_{idx}"])
            tones.append(cls._decode_tone(chunks[0], chunks[1], idx))

        effects = effects_from_blocks(
            cls._region_bytes(regions["mfx"])[0],
            cls._region_bytes(regions["chorus"])[0],
            cls._region_bytes(regions["reverb"])[0],
        )

        cls.apply_tmt(cls._region_bytes(regions["tmt"])[0], common, tones)

        state = cls(common=common, tones=tones, effects=effects)
        state.sound_mode = "PATCH"
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
