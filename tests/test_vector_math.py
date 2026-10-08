"""Unit tests for 2D Cartesian and 1D Wavetable crossfade math."""


from src.spectre.vector.math import (
    CrossfadeCurve,
    calculate_cartesian_levels,
    calculate_wavetable_levels,
    clamp_coordinate,
)


def test_clamp_coordinate():
    assert clamp_coordinate(0.5) == 0.5
    assert clamp_coordinate(-0.2) == 0.0
    assert clamp_coordinate(1.5) == 1.0


def test_cartesian_corners():
    # Corner NW: Tone 1 (X=0.0, Y=1.0)
    nw = calculate_cartesian_levels(0.0, 1.0)
    assert nw == (127, 0, 0, 0)

    # Corner NE: Tone 2 (X=1.0, Y=1.0)
    ne = calculate_cartesian_levels(1.0, 1.0)
    assert ne == (0, 127, 0, 0)

    # Corner SW: Tone 3 (X=0.0, Y=0.0)
    sw = calculate_cartesian_levels(0.0, 0.0)
    assert sw == (0, 0, 127, 0)

    # Corner SE: Tone 4 (X=1.0, Y=0.0)
    se = calculate_cartesian_levels(1.0, 0.0)
    assert se == (0, 0, 0, 127)


def test_cartesian_center():
    # Center (X=0.5, Y=0.5): All 4 tones equal
    center = calculate_cartesian_levels(0.5, 0.5, curve=CrossfadeCurve.LINEAR)
    assert center == (32, 32, 32, 32)

    # Equal power center has higher volume
    ep_center = calculate_cartesian_levels(0.5, 0.5, curve=CrossfadeCurve.EQUAL_POWER)
    assert ep_center == (64, 64, 64, 64)


def test_cartesian_edges():
    # Top edge (Y=1.0): Only Tones 1 and 2 active
    top = calculate_cartesian_levels(0.5, 1.0)
    assert top[0] == 64
    assert top[1] == 64
    assert top[2] == 0
    assert top[3] == 0

    # Bottom edge (Y=0.0): Only Tones 3 and 4 active
    bottom = calculate_cartesian_levels(0.5, 0.0)
    assert bottom[0] == 0
    assert bottom[1] == 0
    assert bottom[2] == 64
    assert bottom[3] == 64


def test_wavetable_transitions():
    # W=0.0: 100% Tone 1
    w0 = calculate_wavetable_levels(0.0)
    assert w0 == (127, 0, 0, 0)

    # W=1/3: 100% Tone 2
    w1_3 = calculate_wavetable_levels(1.0 / 3.0)
    assert w1_3 == (0, 127, 0, 0)

    # W=2/3: 100% Tone 3
    w2_3 = calculate_wavetable_levels(2.0 / 3.0)
    assert w2_3 == (0, 0, 127, 0)

    # W=1.0: 100% Tone 4
    w1 = calculate_wavetable_levels(1.0)
    assert w1 == (0, 0, 0, 127)


def test_wavetable_midpoints():
    # Midpoint between Tone 1 and Tone 2 (W = 1/6)
    mid_1_2 = calculate_wavetable_levels(1.0 / 6.0)
    assert mid_1_2[0] == 64
    assert mid_1_2[1] == 64
    assert mid_1_2[2] == 0
    assert mid_1_2[3] == 0

    # Midpoint between Tone 3 and Tone 4 (W = 5/6)
    mid_3_4 = calculate_wavetable_levels(5.0 / 6.0)
    assert mid_3_4[0] == 0
    assert mid_3_4[1] == 0
    assert mid_3_4[2] in (63, 64)
    assert mid_3_4[3] in (63, 64)


def test_normalized_curve():
    # In normalized mode, center balances 4 tones to prevent drop-off and level spikes on Roland TVA
    norm_center = calculate_cartesian_levels(0.5, 0.5, curve=CrossfadeCurve.NORMALIZED)
    assert norm_center == (85, 85, 85, 85)

    # 50/50 mix on edge
    norm_top = calculate_cartesian_levels(0.5, 1.0, curve=CrossfadeCurve.NORMALIZED)
    assert norm_top == (104, 104, 0, 0)

    # Wavetable midpoint
    norm_wt_mid = calculate_wavetable_levels(1.0 / 6.0, curve=CrossfadeCurve.NORMALIZED)
    assert norm_wt_mid == (104, 104, 0, 0)
