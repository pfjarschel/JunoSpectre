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


def test_chaos_automator_smoothness_and_spread():
    rec = MotionRecorder(bpm=120.0)
    rec.automator = AutomatorType.CHAOS
    rec.play()

    xs = []
    ys = []
    prev = None
    max_step = 0.0

    # Advance 500 frames of 16ms (8 seconds)
    for _ in range(500):
        pos = rec.update(0.016)
        assert pos is not None
        assert 0.0 <= pos[0] <= 1.0
        assert 0.0 <= pos[1] <= 1.0
        xs.append(pos[0])
        ys.append(pos[1])
        if prev is not None:
            step = ((pos[0] - prev[0]) ** 2 + (pos[1] - prev[1]) ** 2) ** 0.5
            if step > max_step:
                max_step = step
        prev = pos

    # Max step per frame should be continuous and smooth (no jittery spikes)
    assert max_step < 0.015, f"Step too jittery: {max_step}"

    # Wide organic dynamic range (covers significant portion of the pad)
    assert (max(xs) - min(xs)) > 0.35
    assert (max(ys) - min(ys)) > 0.35


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

    # CHAOS
    rec.wavetable_sweep = WavetableSweepMode.CHAOS
    positions = []
    for _ in range(1200):
        c_val = rec.step_wavetable(0.016)
        assert c_val is not None
        assert 0.0 <= c_val <= 1.0
        positions.append(c_val)
    # Check that it moves across a wide range without flatlining at 0.0 or 1.0
    assert min(positions) < 0.25
    assert max(positions) > 0.75
    # Check that positions are smooth and never pegged at exact bounds
    assert not all(p == 0.0 for p in positions)
    assert not all(p == 1.0 for p in positions)



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


def test_auto_trim_removes_idle_edges():
    rec = MotionRecorder(bpm=120.0)
    assert rec.auto_trim is True
    rec.smoothing = False
    rec.auto_close = False

    rec.start_recording()
    rec.record_point(0.2, 0.2, timestamp=0.0)   # idle lead-in
    rec.record_point(0.2, 0.2, timestamp=0.2)   # idle lead-in
    rec.record_point(0.5, 0.5, timestamp=0.6)
    rec.record_point(0.8, 0.8, timestamp=1.0)
    rec.record_point(0.8, 0.8, timestamp=1.2)   # idle tail-off
    rec.record_point(0.8, 0.8, timestamp=1.4)   # idle tail-off
    rec.stop_recording()

    pts = rec.points
    assert len(pts) == 3
    assert (pts[0].x, pts[0].y) == (0.2, 0.2)
    assert (pts[-1].x, pts[-1].y) == (0.8, 0.8)
    assert pts[0].timestamp == pytest.approx(0.0)
    assert rec.duration == pytest.approx(0.8)


def test_auto_trim_disabled_keeps_idle_edges():
    rec = MotionRecorder(bpm=120.0)
    rec.auto_trim = False
    rec.auto_close = False

    rec.start_recording()
    rec.record_point(0.3, 0.3, timestamp=0.0)
    rec.record_point(0.3, 0.3, timestamp=0.2)
    rec.record_point(0.7, 0.7, timestamp=0.6)
    rec.stop_recording()

    assert len(rec.points) == 3
    assert rec.duration == pytest.approx(0.6)


def test_auto_trim_leaves_fully_idle_recording_intact():
    rec = MotionRecorder(bpm=120.0)
    rec.start_recording()
    for i in range(5):
        rec.record_point(0.5, 0.5, timestamp=float(i))
    rec.stop_recording()

    assert len(rec.points) == 5
    assert rec.state == RecorderState.PLAYING


def test_auto_trim_preserves_slow_final_motion():
    rec = MotionRecorder(bpm=120.0)
    rec.smoothing = False
    rec.auto_close = False

    rec.start_recording()
    rec.record_point(0.0, 0.0, timestamp=0.0)
    rec.record_point(0.5, 0.5, timestamp=0.5)
    rec.record_point(0.504, 0.5, timestamp=0.7)   # slow taper (< eps per step)
    rec.record_point(0.508, 0.5, timestamp=0.9)
    rec.record_point(0.512, 0.5, timestamp=1.1)
    rec.record_point(0.512, 0.5, timestamp=1.3)   # settled
    rec.record_point(0.512, 0.5, timestamp=1.5)   # settled
    rec.stop_recording()

    pts = rec.points
    assert len(pts) == 4
    assert pts[-1].x == pytest.approx(0.508, abs=0.001)


def test_auto_close_appends_seamless_return_points():
    rec = MotionRecorder(bpm=120.0)
    rec.start_recording()
    rec.record_point(0.0, 0.0, timestamp=0.0)
    rec.record_point(0.5, 0.0, timestamp=0.5)
    rec.record_point(1.0, 0.0, timestamp=1.0)
    rec.stop_recording()

    pts = rec.points
    assert len(pts) == 5
    assert (pts[-1].x, pts[-1].y) == (0.0, 0.0)
    assert pts[-1].timestamp > pts[-2].timestamp
    assert rec.duration == pytest.approx(2.0)


def test_auto_close_skips_already_closed_path():
    rec = MotionRecorder(bpm=120.0)
    rec.start_recording()
    rec.record_point(0.0, 0.0, timestamp=0.0)
    rec.record_point(1.0, 0.0, timestamp=0.5)
    rec.record_point(1.0, 1.0, timestamp=1.0)
    rec.record_point(0.0, 1.0, timestamp=1.5)
    rec.record_point(0.0, 0.0, timestamp=2.0)
    rec.stop_recording()

    assert len(rec.points) == 5


def test_auto_close_disabled_keeps_open_path():
    rec = MotionRecorder(bpm=120.0)
    rec.auto_trim = False
    rec.auto_close = False
    rec.start_recording()
    rec.record_point(0.0, 0.0, timestamp=0.0)
    rec.record_point(0.5, 0.0, timestamp=0.5)
    rec.record_point(1.0, 0.0, timestamp=1.0)
    rec.stop_recording()

    assert len(rec.points) == 3
    assert rec.duration == pytest.approx(1.0)


def _l_shaped_recorder(relax: bool = False) -> "MotionRecorder":
    rec = MotionRecorder(bpm=120.0)
    rec.auto_trim = False
    rec.smoothing = relax
    rec.start_recording()
    path = [(0.2, 0.2), (0.35, 0.2), (0.5, 0.2), (0.65, 0.2), (0.8, 0.2),
            (0.8, 0.35), (0.8, 0.5), (0.8, 0.65), (0.8, 0.8)]
    for i, (x, y) in enumerate(path):
        rec.record_point(x, y, timestamp=i * 0.05)
    return rec


def test_auto_close_curve_exits_along_momentum():
    rec = _l_shaped_recorder()
    n_orig = len(rec.points)
    rec.stop_recording()

    pts = rec.points
    assert len(pts) > n_orig
    first_closing = pts[n_orig]
    assert first_closing.y > 0.8   # continues upward momentum before curving back
    assert first_closing.x < 0.8   # starts drifting toward the start point
    for i in range(1, len(pts)):
        assert pts[i].timestamp > pts[i - 1].timestamp


def test_auto_close_curve_arrives_on_start_direction():
    rec = _l_shaped_recorder()
    rec.stop_recording()

    pts = rec.points
    assert (pts[-1].x, pts[-1].y) == (0.2, 0.2)
    # Head momentum leaves the start toward +x, so the return must arrive
    # moving +x: the penultimate sample undershoots below the start x.
    assert pts[-2].x < 0.2


def _jittery_recorder(**flags) -> "MotionRecorder":
    rec = MotionRecorder(bpm=120.0)
    rec.auto_trim = flags.get("auto_trim", False)
    rec.auto_close = flags.get("auto_close", False)
    rec.smoothing = flags.get("smoothing", True)
    rec.start_recording()
    for i in range(9):
        y = 0.5 + (0.02 if i % 2 else -0.02)
        rec.record_point(0.1 + 0.1 * i, y, timestamp=i * 0.1)
    return rec


def test_smoothing_reduces_jitter_and_pins_endpoints():
    rec = _jittery_recorder()
    raw = list(rec.points)
    rec.stop_recording()

    pts = rec.points
    assert (pts[0].x, pts[0].y) == (raw[0].x, raw[0].y)
    assert (pts[-1].x, pts[-1].y) == (raw[-1].x, raw[-1].y)

    raw_dev = max(abs(p.y - 0.5) for p in raw[2:-2])
    smooth_dev = max(abs(p.y - 0.5) for p in pts[2:-2])
    assert smooth_dev < raw_dev * 0.5
    for i in range(1, len(pts)):
        assert pts[i].timestamp == pytest.approx(raw[i].timestamp)


def test_smoothing_disabled_keeps_raw_samples():
    rec = _jittery_recorder(smoothing=False)
    raw = list(rec.points)
    rec.stop_recording()

    assert [(p.x, p.y) for p in rec.points] == [(p.x, p.y) for p in raw]


def test_auto_close_closure_is_relaxed_when_smoothing_on():
    raw_rec = _l_shaped_recorder(relax=False)
    n_orig = len(raw_rec.points)
    raw_rec.stop_recording()

    smooth_rec = _l_shaped_recorder(relax=True)
    smooth_rec.stop_recording()

    raw_c1 = raw_rec.points[n_orig]
    smooth_c1 = smooth_rec.points[n_orig]
    # Junction relaxation pulls the first closure sample toward the chord
    chord_y = 0.8 + (0.2 - 0.8) / (len(raw_rec.points) - n_orig)
    assert raw_c1.y > 0.8
    assert smooth_c1.y < raw_c1.y
    assert smooth_c1.y > chord_y
    # Seam anchors stay pinned and timing intact
    assert (smooth_rec.points[-1].x, smooth_rec.points[-1].y) == (0.2, 0.2)
    assert len(smooth_rec.points) == len(raw_rec.points)
    for i in range(1, len(smooth_rec.points)):
        assert smooth_rec.points[i].timestamp == pytest.approx(raw_rec.points[i].timestamp)
