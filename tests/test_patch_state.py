"""Unit tests for PatchState data model and init patch generation."""

import pytest
from src.spectre.core.patch_state import (
    PatchState,
    ToneState,
    PatchCommonState,
    EffectsState,
    MatrixCtrlState,
)


def test_init_patch_creation():
    patch = PatchState.create_init_patch()
    assert patch.sound_mode == "PATCH"
    assert patch.common.name == "JUNO SPECTRE"
    assert patch.common.level == 100
    assert patch.common.pan == 64
    assert patch.common.cutoff_offset == 64
    assert patch.common.resonance_offset == 64
    assert patch.common.portamento_switch is False
    assert patch.common.portamento_time == 20
    assert patch.common.legato_switch is False

    # Check 4 tones
    assert len(patch.tones) == 4
    for idx, tone in enumerate(patch.tones, start=1):
        assert tone.tone_index == idx
        assert tone.level == 127
        assert tone.pan == 64
        assert tone.coarse_tune == 64
        assert tone.fine_tune == 64
        assert tone.coarse_st == 0
        assert tone.fine_cents == 0
        assert tone.tvf_cutoff == 127
        assert tone.tvf_resonance == 0
        assert tone.tvf_env_depth == 64
        assert tone.tvf_filter_type == 1
        assert tone.tvf_type_str == "LPF"
        assert tone.tva_attack == 0
        assert tone.tva_sustain == 127
        assert tone.pitch_env_depth == 64
        assert tone.pitch_env_depth_st == 0
        assert tone.lfo1_pitch_depth == 64
        assert tone.lfo2_pitch_depth == 64
        assert tone.muted is False

    # Specific wave defaults
    assert patch.tones[0].wave_bank_l == "INTA"
    assert patch.tones[0].wave_num_l == 579
    assert patch.tones[1].wave_num_l == 600
    assert patch.tones[2].wave_num_l == 622
    assert patch.tones[3].wave_num_l == 625

    # Effects
    assert patch.effects.mfx_bypassed is True
    assert patch.effects.chorus_level == 0
    assert patch.effects.reverb_level == 0
    assert patch.effects.eq_low_gain == 0
    assert patch.effects.eq_mid_gain == 0
    assert patch.effects.eq_high_gain == 0


def test_tone_state_bipolar_conversions():
    tone = ToneState(
        coarse_tune=76,       # +12 st
        fine_tune=44,         # -20 cents
        pan=32,               # L32
        tvf_env_depth=84,     # +20
        pitch_env_depth=76,   # +12 st
        pitch_env_l1=94,      # +30
    )
    assert tone.coarse_st == 12
    assert tone.fine_cents == -20
    assert tone.pan_bipolar == -32
    assert tone.tvf_env_depth_bipolar == 20
    assert tone.pitch_env_depth_st == 12
    assert tone.pitch_env_l1_bipolar == 30


def test_tvf_env_adsr_projection_is_lossless():
    tone = ToneState()
    # Canonical default maps cleanly to the 4-time / 5-level MSEG
    assert tone.tvf_attack == 0
    assert tone.tvf_decay == 0
    assert tone.tvf_sustain == 127
    assert tone.tvf_release == 0
    assert tone.tvf_env_custom is False

    # Moving ADSR sustain on a canonical shape reties L2 and L3
    tone.tvf_sustain = 80
    assert tone.tvf_l2 == 80
    assert tone.tvf_l3 == 80
    assert tone.tvf_env_custom is False

    # Editing a raw segment creates a custom shape but keeps ADSR readable
    tone.tvf_t3 = 50
    assert tone.tvf_env_custom is True
    assert tone.tvf_sustain == 80

    # Once L2 deviates, ADSR sustain must not stomp the break level
    tone.tvf_l2 = 30
    tone.tvf_sustain = 100
    assert tone.tvf_l2 == 30
    assert tone.tvf_l3 == 100

    # Raw 9-byte hardware block roundtrip
    block = tone.tvf_env_block()
    assert len(block) == 9
    other = ToneState()
    other.set_tvf_env_block([5, 10, 0, 20, 0, 127, 64, 64, 0])
    assert other.tvf_attack == 5
    assert other.tvf_decay == 10
    assert other.tvf_release == 20
    assert other.tvf_sustain == 64
    assert other.tvf_env_custom is False
    assert other.tvf_env_block() == [5, 10, 0, 20, 0, 127, 64, 64, 0]


def test_tva_env_adsr_projection_is_lossless():
    tone = ToneState()
    assert tone.tva_attack == 0
    assert tone.tva_sustain == 127
    assert tone.tva_env_custom is False

    tone.tva_attack = 40
    assert tone.tva_t1 == 40
    assert tone.tva_env_custom is False

    tone.tva_l2 = 60  # Break below sustain -> custom shape
    assert tone.tva_env_custom is True

    tone.tva_sustain = 90
    assert tone.tva_l2 == 60
    assert tone.tva_l3 == 90

    assert tone.tva_env_block() == [40, 0, 0, 0, 127, 60, 90]


def test_env_modifier_defaults_and_conversions():
    tone = ToneState()
    # Neutral raw 64 for all env modifiers
    assert tone.tvf_env_t1_vel_sens == 64
    assert tone.tvf_env_t4_vel_sens == 64
    assert tone.tvf_env_time_keyfollow == 64
    assert tone.tva_env_t1_vel_sens == 64
    assert tone.tva_env_t4_vel_sens == 64
    assert tone.tva_env_time_keyfollow == 64

    signed = ToneState(
        tvf_env_t1_vel_sens=94,       # +30
        tvf_env_time_keyfollow=69,    # +50 %
        tva_env_t4_vel_sens=54,       # -10
    )
    assert signed.tvf_env_t1_vel_sens_bipolar == 30
    assert signed.tvf_env_time_kf_bipolar == 50
    assert signed.tva_env_t4_vel_sens_bipolar == -10

    init = PatchState.create_init_patch()
    for t in init.tones:
        assert t.tvf_env_t1_vel_sens == 64
        assert t.tva_env_time_keyfollow == 64
