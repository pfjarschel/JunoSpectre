"""Unit tests and benchmarks for SmoothScaler and relative processing modes."""

import time
import pytest
from src.spectre.control.models import RelativeEncoderEncoding, ScaleMode
from src.spectre.control.smooth_scaler import SmoothScaler


def test_smooth_scaler_upward_convergence():
    """Verify that moving upward from P=20, V=100 converges exactly to V=127 at P=127."""
    scaler = SmoothScaler(initial_physical=20, initial_synth=100.0, mode=ScaleMode.SMOOTH)
    assert not scaler.is_converged

    for p in range(21, 128):
        v, changed, _ = scaler.process(p)
        assert v >= 100
        assert v <= 127

    assert scaler.physical_pos == 127
    assert scaler.synth_value == 127
    assert scaler.is_converged


def test_smooth_scaler_downward_convergence():
    """Verify that moving downward from P=100, V=20 converges exactly to V=0 at P=0."""
    scaler = SmoothScaler(initial_physical=100, initial_synth=20.0, mode=ScaleMode.SMOOTH)
    assert not scaler.is_converged

    for p in range(99, -1, -1):
        v, changed, _ = scaler.process(p)
        assert v <= 20
        assert v >= 0

    assert scaler.physical_pos == 0
    assert scaler.synth_value == 0
    assert scaler.is_converged


def test_smooth_scaler_locked_1_to_1_after_convergence():
    """Once converged, physical position and synth parameter track 1:1 in both directions."""
    scaler = SmoothScaler(initial_physical=64, initial_synth=64.0, mode=ScaleMode.SMOOTH)
    assert scaler.is_converged

    # Move up
    v, _, _ = scaler.process(80)
    assert v == 80
    assert scaler.is_converged

    # Move down
    v, _, _ = scaler.process(40)
    assert v == 40
    assert scaler.is_converged


def test_smooth_scaler_direction_reversals():
    """Verify smooth behavior when changing movement direction midway through a stroke."""
    scaler = SmoothScaler(initial_physical=20, initial_synth=80.0, mode=ScaleMode.SMOOTH)

    # Move up halfway
    for p in range(21, 51):
        scaler.process(p)

    assert scaler.synth_value > 80
    v_mid = scaler.synth_value_float

    # Reverse direction down to 10
    for p in range(49, 9, -1):
        scaler.process(p)

    assert scaler.synth_value < v_mid
    assert scaler.synth_value >= 0


def test_smooth_scaler_sync_decoupling():
    """Verify that sync_synth_value updates synth target and decouples convergence."""
    scaler = SmoothScaler(initial_physical=64, initial_synth=64.0, mode=ScaleMode.SMOOTH)
    assert scaler.is_converged

    # Preset changes on synth, parameter jumps to 110
    scaler.sync_synth_value(110.0)
    assert not scaler.is_converged
    assert scaler.synth_value == 110

    # Moving physical controller now smoothly closes the gap
    scaler.process(65)
    assert scaler.synth_value >= 110


def test_catch_up_mode():
    """Verify CATCH_UP mode holds value until physical position crosses synth value."""
    scaler = SmoothScaler(initial_physical=20, initial_synth=80.0, mode=ScaleMode.CATCH_UP)
    assert not scaler.is_converged

    # Moving below 80 should not change synth value
    v, changed, _ = scaler.process(40)
    assert v == 80
    assert not changed
    assert not scaler.is_converged

    v, changed, _ = scaler.process(60)
    assert v == 80
    assert not changed

    # Crossing 80 triggers convergence
    v, changed, _ = scaler.process(85)
    assert v == 85
    assert changed
    assert scaler.is_converged


def test_jump_mode():
    """Verify JUMP mode immediately updates synth value 1:1."""
    scaler = SmoothScaler(initial_physical=20, initial_synth=100.0, mode=ScaleMode.JUMP)
    v, changed, _ = scaler.process(25)
    assert v == 25
    assert changed
    assert scaler.is_converged


def test_relative_delta_mode():
    """Verify RELATIVE_DELTA calculates physical delta and applies it to synth value."""
    scaler = SmoothScaler(initial_physical=50, initial_synth=80.0, mode=ScaleMode.RELATIVE_DELTA, sensitivity=1.0)
    v, changed, _ = scaler.process(55)
    assert v == 85
    assert changed

    v, changed, _ = scaler.process(52)
    assert v == 82
    assert changed


def test_relative_center_reset_mode():
    """Verify RELATIVE_CENTER_RESET calculates delta from 64 and flags needs_recenter."""
    scaler = SmoothScaler(initial_physical=64, initial_synth=50.0, mode=ScaleMode.RELATIVE_CENTER_RESET, sensitivity=1.0)

    # User turns knob clockwise, sending 66 (+2)
    v, changed, needs_recenter = scaler.process(66)
    assert v == 52
    assert changed
    assert needs_recenter is True
    assert scaler.physical_pos == 64

    # User turns knob counter-clockwise, sending 61 (-3)
    v, changed, needs_recenter = scaler.process(61)
    assert v == 49
    assert changed
    assert needs_recenter is True
    assert scaler.physical_pos == 64


def test_relative_encoder_modes():
    """Verify binary offset, twos complement, and sign magnitude relative encoder decoding."""
    # 1. Binary offset (65 = +1, 63 = -1)
    scaler_bin = SmoothScaler(initial_synth=50.0, mode=ScaleMode.RELATIVE_ENCODER, encoding=RelativeEncoderEncoding.BINARY_OFFSET)
    v, changed, _ = scaler_bin.process(65)
    assert v == 51

    v, changed, _ = scaler_bin.process(63)
    assert v == 50

    # 2. Twos complement (1 = +1, 127 = -1)
    scaler_tc = SmoothScaler(initial_synth=50.0, mode=ScaleMode.RELATIVE_ENCODER, encoding=RelativeEncoderEncoding.TWOS_COMPLEMENT)
    v, changed, _ = scaler_tc.process(2)
    assert v == 52

    v, changed, _ = scaler_tc.process(127)
    assert v == 51


def benchmark_scaling_throughput():
    """Benchmark processing 100,000 scaling operations."""
    scaler = SmoothScaler(initial_physical=20, initial_synth=100.0, mode=ScaleMode.SMOOTH)
    count = 100_000
    start = time.perf_counter()
    for i in range(count):
        p = (i % 128)
        scaler.process(p)
    elapsed = time.perf_counter() - start
    ops_per_sec = count / elapsed
    print(f"\nBenchmark: Processed {count:,} events in {elapsed*1000:.2f} ms ({ops_per_sec:,.0f} ops/sec)")
    return ops_per_sec


def test_performance_benchmark():
    """Assert scaling throughput exceeds 500,000 operations per second (< 2 µs latency)."""
    ops_per_sec = benchmark_scaling_throughput()
    assert ops_per_sec > 500_000, f"Throughput too low: {ops_per_sec} ops/sec"
