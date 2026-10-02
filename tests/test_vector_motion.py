"""Unit tests for touch trajectory motion recorder and orbital automators."""

import pytest

from src.spectre.vector.motion import (
    AutomatorType,
    LoopMode,
    MotionRecorder,
    RecorderState,
    TrajectoryPoint,
)


def test_motion_recorder_record_and_playback():
    rec = MotionRecorder(bpm=120.0)
    assert rec.state == RecorderState.STOPPED

    rec.start_recording()
    assert rec.state == RecorderState.RECORDING

    rec.record_point(0.0, 0.0, timestamp=0.0)
    rec.record_point(1.0, 1.0, timestamp=1.0)
    rec.stop_recording()

    assert rec.state == RecorderState.PLAYING
    assert rec.duration == 1.0

    # Interpolation at midpoint (t=0.5)
    pos = rec.get_position_at(0.5)
    assert pytest.approx(pos[0], 0.01) == 0.5
    assert pytest.approx(pos[1], 0.01) == 0.5


def test_motion_loop_modes():
    rec = MotionRecorder(bpm=120.0)
    rec.start_recording()
    rec.record_point(0.0, 0.0, timestamp=0.0)
    rec.record_point(1.0, 1.0, timestamp=2.0)
    rec.stop_recording()

    # Forward loop: at t=0.5, pos is 0.25
    pos = rec.update(0.5)
    assert pos is not None
    assert pytest.approx(pos[0], 0.01) == 0.25

    # Reverse loop
    rec.loop_mode = LoopMode.REVERSE
    rec.stop()
    rec.play()
    # At t=0, reverse wraps from end
    pos = rec.update(0.5)
    assert pos is not None
    assert pos[0] > 0.5  # moving backward from 1.0


def test_motion_ping_pong():
    rec = MotionRecorder(bpm=120.0)
    rec.loop_mode = LoopMode.PING_PONG
    rec.start_recording()
    rec.record_point(0.0, 0.0, timestamp=0.0)
    rec.record_point(1.0, 1.0, timestamp=1.0)
    rec.stop_recording()

    # Step forward to end
    rec.update(1.0)
    # Step backward
    pos = rec.update(0.5)
    assert pos is not None
    assert pytest.approx(pos[0], 0.01) == 0.5


def test_orbital_automator_gravity():
    rec = MotionRecorder(bpm=120.0)
    rec.automator = AutomatorType.CIRCLE
    rec.play()

    pos1 = rec.update(0.0)
    assert pos1 is not None
    # Circle starts around (0.78, 0.5) with radius 0.28 centered at (0.5, 0.5)
    assert pytest.approx(pos1[0], 0.05) == 0.78
    assert pytest.approx(pos1[1], 0.05) == 0.5

    # Stepping time causes orbital motion around center (0.5, 0.5)
    pos2 = rec.update(0.05)
    assert pos2 is not None
    assert pos2 != pos1
    assert 0.0 <= pos2[0] <= 1.0
    assert 0.0 <= pos2[1] <= 1.0

    # Test fling gesture
    rec.fling(0.3, 0.3, 0.5, -0.5)
    pos3 = rec.update(0.0)
    assert pytest.approx(pos3[0], 0.01) == 0.3
    assert pytest.approx(pos3[1], 0.01) == 0.3

    # Stepping time applies velocity and gravity pull towards attractor
    pos4 = rec.update(0.05)
    assert pos4[0] > 0.3  # vx was positive


def test_wavetable_sweeps():
    from src.spectre.vector.motion import WavetableSweepMode
    rec = MotionRecorder(bpm=120.0)
    
    # MANUAL
    rec.wavetable_sweep = WavetableSweepMode.MANUAL
    assert rec.step_wavetable(0.1) is None

    # SINE
    rec.wavetable_sweep = WavetableSweepMode.SINE
    val = rec.step_wavetable(0.1)
    assert 0.0 <= val <= 1.0

    # TRIANGLE
    rec.wavetable_sweep = WavetableSweepMode.TRIANGLE
    val2 = rec.step_wavetable(0.1)
    assert 0.0 <= val2 <= 1.0

    # RAMP
    rec.wavetable_sweep = WavetableSweepMode.RAMP
    val3 = rec.step_wavetable(0.1)
    assert 0.0 <= val3 <= 1.0

    # RANDOM_STEP
    rec.wavetable_sweep = WavetableSweepMode.RANDOM_STEP
    val4 = rec.step_wavetable(0.1)
    assert 0.0 <= val4 <= 1.0



def test_serialization():
    rec = MotionRecorder(bpm=130.0)
    rec.start_recording()
    rec.record_point(0.1, 0.2, timestamp=0.0)
    rec.record_point(0.8, 0.9, timestamp=1.5)
    rec.stop_recording()

    d = rec.to_dict()
    assert d["bpm"] == 130.0
    assert len(d["points"]) == 2

    restored = MotionRecorder.from_dict(d)
    assert restored.bpm == 130.0
    assert len(restored.points) == 2
    assert restored.points[1].x == 0.8
