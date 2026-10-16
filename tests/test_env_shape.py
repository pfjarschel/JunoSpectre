from spectre.core import env_shape
from spectre.core.patch_state import ToneState


def _tvf(tone, times, levels):
    tone.set_env_curve("tvf", times, levels)


def test_groups_follow_the_peak():
    # Peak at L1: attack = T1, decay = T2 + T3
    assert env_shape.group("attack", [10, 20, 30, 40], [0, 127, 90, 60, 0], 0) == [0]
    assert env_shape.group("decay", [10, 20, 30, 40], [0, 127, 90, 60, 0], 0) == [1, 2]
    # A swell peaking at L2: attack = T1 + T2, decay = T3
    assert env_shape.group("attack", [10, 20, 30, 40], [0, 60, 127, 90, 0], 0) == [0, 1]
    assert env_shape.group("decay", [10, 20, 30, 40], [0, 60, 127, 90, 0], 0) == [2]
    # Zero times are steps, not segments
    assert env_shape.group("decay", [10, 20, 0, 40], [0, 127, 90, 90, 0], 0) == [1]
    assert env_shape.group("decay", [10, 0, 0, 40], [0, 127, 90, 90, 0], 0) == [1]
    # Pitch: the peak is the level furthest from the centre (64)
    assert env_shape.peak_index([64, 70, 20, 64, 64], 64) == 2


def test_group_moves_keep_the_shape_and_never_flatten():
    tone = ToneState()
    _tvf(tone, [10, 30, 50, 40], [0, 127, 90, 60, 0])
    assert tone.tvf_decay == 50                      # the group's longest time
    tone.tvf_decay = 70                              # +20 on both decay segments
    assert (tone.tvf_t2, tone.tvf_t3) == (50, 70)
    tone.tvf_decay = 127                             # T3 clamps, T2 keeps going
    assert (tone.tvf_t2, tone.tvf_t3) == (107, 127)
    tone.tvf_decay = 50                              # back: the snapshot, not the clamped curve
    assert (tone.tvf_t2, tone.tvf_t3) == (30, 50)
    tone.tvf_attack = 25                             # other groups and levels untouched
    assert tone.env_curve("tvf") == ([25, 30, 50, 40], [0, 127, 90, 60, 0])
    # An edit made elsewhere becomes the new snapshot
    tone.tvf_t2 = 5
    tone.tvf_decay = 60
    assert (tone.tvf_t2, tone.tvf_t3) == (15, 60)


def test_plain_adsr_controls_are_direct():
    tone = ToneState()
    _tvf(tone, [10, 20, 0, 30], [0, 127, 80, 80, 0])
    tone.tvf_attack, tone.tvf_decay, tone.tvf_sustain, tone.tvf_release = 1, 2, 3, 4
    assert tone.env_curve("tvf") == ([1, 2, 0, 4], [0, 127, 3, 3, 0])
    assert tone.env_is_adsr("tvf")


def test_adsr_switch_keeps_and_restores_the_original():
    tone = ToneState()
    original = ([10, 30, 50, 40], [0, 127, 90, 60, 0])
    _tvf(tone, *original)
    assert not tone.env_is_adsr("tvf")
    tone.env_to_adsr("tvf")
    assert tone.env_curve("tvf") == ([10, 50, 0, 40], [0, 127, 60, 60, 0])
    assert tone.env_is_adsr("tvf") and "tvf" in tone.env_originals
    tone.tvf_sustain = 100                           # ADSR edits keep the original...
    tone.env_forget_broken_original("tvf")
    assert "tvf" in tone.env_originals
    assert tone.env_restore("tvf")                   # ...and are dropped on the way back
    assert tone.env_curve("tvf") == original
    assert not tone.env_originals
    # Breaking the ADSR shape by hand makes it Normal: the original is gone
    tone.env_to_adsr("tvf")
    tone.tvf_t3 = 20
    tone.env_forget_broken_original("tvf")
    assert not tone.env_originals
    assert not tone.env_restore("tvf")


def test_pitch_adsr_is_bipolar_and_tva_ends_are_fixed():
    tone = ToneState()
    tone.set_env_curve("pitch", [20, 40, 50, 35], [64, 88, 74, 64, 64])
    tone.env_to_adsr("pitch")
    assert tone.env_curve("pitch") == ([20, 50, 0, 35], [64, 127, 64, 64, 64])
    tone.pitch_env_sustain = 80
    assert (tone.pitch_env_l2, tone.pitch_env_l3) == (80, 80)
    tone.set_env_curve("tva", [0, 10, 10, 10], [0, 127, 127, 127, 0])
    tone.env_to_adsr("tva")
    assert tone.tva_env_block() == [0, 10, 0, 10, 127, 127, 127]
    assert tone.env_is_adsr("tva")


def test_originals_survive_save_and_load():
    from spectre.core.patch_state import PatchState
    from spectre.core.spectre_format import patch_state_from_dict, patch_state_to_dict

    ps = PatchState()
    ps.tones[0].set_env_curve("tvf", [10, 30, 50, 40], [0, 127, 90, 60, 0])
    ps.tones[0].env_to_adsr("tvf")
    back = patch_state_from_dict(patch_state_to_dict(ps))
    assert back.tones[0].env_originals == {"tvf": [10, 30, 50, 40, 0, 127, 90, 60, 0]}
    assert back.tones[0].env_restore("tvf")
