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
