"""Touch trajectory motion recorder and geometric orbital automators.

Captures real-time continuous gesture paths, loops them with sub-millisecond
interpolation, and provides algorithmic modulation curves (Lissajous, Circle, Chaos).
"""

from __future__ import annotations

import enum
import json
import math
import random
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .math import clamp_coordinate


class RecorderState(str, enum.Enum):
    """Current transport state of the motion recorder."""
    STOPPED = "stopped"
    RECORDING = "recording"
    PLAYING = "playing"
    PAUSED = "paused"


class LoopMode(str, enum.Enum):
    """Looping playback direction."""
    FORWARD = "forward"
    PING_PONG = "ping_pong"
    REVERSE = "reverse"
    ONE_SHOT = "one_shot"


class AutomatorType(str, enum.Enum):
    """Geometric autonomous modulation generators."""
    NONE = "none"
    CIRCLE = "circle"
    LISSAJOUS = "lissajous"
    SPIRAL = "spiral"
    CHAOS = "chaos"


class WavetableSweepMode(str, enum.Enum):
    """1D progressive wavetable sweep generators."""
    MANUAL = "manual"
    SINE = "sine"
    TRIANGLE = "triangle"
    RAMP = "ramp"
    RANDOM_STEP = "random_step"
    CHAOS = "chaos"


@dataclass(frozen=True)
class TrajectoryPoint:
    """A timestamped 2D coordinate on the vector canvas."""
    timestamp: float  # Seconds relative to recording start
    x: float          # 0.0 .. 1.0
    y: float          # 0.0 .. 1.0


# Maximum consecutive-point distance (normalized pad units) treated as idle
IDLE_EDGE_EPSILON = 0.005

# Hermite tangent length as a fraction of the closing gap (curve tension)
HERMITE_TENSION = 0.7

# Weighted moving-average kernel applied to interior samples on stop
SMOOTHING_KERNEL = (1, 2, 3, 2, 1)


def _point_distance(a: TrajectoryPoint, b: TrajectoryPoint) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def _edge_momentum(
    points: List[TrajectoryPoint], *, from_end: bool
) -> Optional[Tuple[float, float]]:
    """Average unit direction of motion at a trajectory edge, or None if idle."""
    dirs: List[Tuple[float, float]] = []
    if from_end:
        rng = range(len(points) - 1, max(0, len(points) - 7), -1)
    else:
        rng = range(1, min(len(points), 7))
    for i in rng:
        dx = points[i].x - points[i - 1].x
        dy = points[i].y - points[i - 1].y
        d = math.hypot(dx, dy)
        if d <= IDLE_EDGE_EPSILON:
            continue
        dirs.append((dx / d, dy / d))
        if len(dirs) == 3:
            break
    if not dirs:
        return None
    ux = sum(v[0] for v in dirs) / len(dirs)
    uy = sum(v[1] for v in dirs) / len(dirs)
    norm = math.hypot(ux, uy)
    if norm < 1e-6:
        return None
    return (ux / norm, uy / norm)


class MotionRecorder:
    """Manages recording, looping playback, and algorithmic modulation of vector trajectories."""

    def __init__(self, bpm: float = 120.0):
        self.bpm = bpm
        self.state: RecorderState = RecorderState.STOPPED
        self.loop_mode: LoopMode = LoopMode.FORWARD
        self.speed: float = 1.0  # Speed multiplier (e.g. 0.25x .. 2.0x)
        self.automator: AutomatorType = AutomatorType.NONE
        self.auto_trim: bool = True  # Strip idle lead-in/tail-off on stop
        self.auto_close: bool = True  # Append linear points back to the start on stop
        self.smoothing: bool = True  # Low-pass interior samples on stop

        self.points: List[TrajectoryPoint] = []
        self._record_start_time: float = 0.0
        self._playback_time: float = 0.0
        self._ping_pong_forward: bool = True
        self._automator_phase: float = 0.0

        # Celestial attractor coordinates (center of orbit / gravity well)
        self.center_x: float = 0.5
        self.center_y: float = 0.5

        # Celestial body state (position and velocity in orbital physics)
        self._body_x: float = 0.5
        self._body_y: float = 0.5
        self._body_vx: float = 0.0
        self._body_vy: float = 0.0

        # Multi-harmonic incommensurate phase drift state (fluid, non-periodic chaos)
        self._chaos_phase1: float = 0.0
        self._chaos_phase2: float = 0.0
        self._chaos_phase3: float = 0.0
        self._chaos_phase4: float = 0.0
        self._chaos_phase5: float = 0.0
        self._chaos_phase6: float = 0.0

        # 1D Wavetable sweep state
        self.wavetable_sweep: WavetableSweepMode = WavetableSweepMode.MANUAL
        self._wt_phase: float = 0.0
        self._wt_target: float = 0.5
        self._wt_current: float = 0.5
        self._wt_step_timer: float = 0.0
        self._wt_chaos_phase1: float = 0.0
        self._wt_chaos_phase2: float = 0.0
        self._wt_chaos_phase3: float = 0.0
        self._wt_chaos_phase4: float = 0.0

        # Bar sync quantization (0 = free length, 1..16 = quantized bars)
        self.sync_bars: int = 0

    def set_orbit_center(self, x: float, y: float) -> None:
        """Set dynamic center attractor for orbital automators."""
        self.center_x = clamp_coordinate(x)
        self.center_y = clamp_coordinate(y)

    def fling(self, x: float, y: float, vx: float, vy: float) -> None:
        """Launch puck with position and momentum velocity vector into gravitational orbit."""
        self._body_x = clamp_coordinate(x)
        self._body_y = clamp_coordinate(y)
        self._body_vx = vx
        self._body_vy = vy

    @property
    def duration(self) -> float:
        """Total duration of recorded trajectory in seconds."""
        if not self.points:
            return 0.0
        if self.sync_bars > 0:
            return (4.0 * 60.0 / self.bpm) * self.sync_bars
        return self.points[-1].timestamp

    @property
    def is_empty(self) -> bool:
        """True if no trajectory points are currently stored."""
        return len(self.points) == 0

    def start_recording(self, clear_existing: bool = True) -> None:
        """Begin capturing touch trajectory points."""
        if clear_existing:
            self.points.clear()
        self.state = RecorderState.RECORDING
        self._record_start_time = time.perf_counter()
        self._playback_time = 0.0
        self._ping_pong_forward = True

    def record_point(self, x: float, y: float, timestamp: Optional[float] = None) -> None:
        """Record an (X, Y) coordinate sample."""
        if self.state != RecorderState.RECORDING:
            return

        if timestamp is None:
            t = max(0.0, time.perf_counter() - self._record_start_time)
        else:
            t = timestamp

        pt = TrajectoryPoint(
            timestamp=t,
            x=clamp_coordinate(x),
            y=clamp_coordinate(y),
        )
        self.points.append(pt)

    def stop_recording(self) -> None:
        """Finish recording and immediately transition to playing if points exist."""
        if self.state == RecorderState.RECORDING:
            if self.smoothing:
                self._apply_smoothing()
            if self.auto_trim:
                self._trim_stationary_edges()
            if self.auto_close:
                added = self._close_loop()
                if added and self.smoothing:
                    self._smooth_closure(len(self.points) - added)
            if len(self.points) > 1:
                self.state = RecorderState.PLAYING
                self._playback_time = 0.0
            else:
                self.state = RecorderState.STOPPED

    def _apply_smoothing(self) -> None:
        """Low-pass the trajectory with a weighted moving average.

        Endpoints (and the kernel-radius samples around them) are pinned so the
        manual start/end positions are respected; timestamps are preserved.
        """
        pts = self.points
        half = len(SMOOTHING_KERNEL) // 2
        if len(pts) < 2 * half + 1:
            return

        weight_sum = float(sum(SMOOTHING_KERNEL))
        smoothed = list(pts)
        for i in range(half, len(pts) - half):
            x_acc = 0.0
            y_acc = 0.0
            for offset, w in enumerate(SMOOTHING_KERNEL):
                sample = pts[i - half + offset]
                x_acc += sample.x * w
                y_acc += sample.y * w
            smoothed[i] = TrajectoryPoint(
                timestamp=pts[i].timestamp,
                x=clamp_coordinate(x_acc / weight_sum),
                y=clamp_coordinate(y_acc / weight_sum),
            )
        self.points = smoothed

    def _trim_stationary_edges(self) -> None:
        """Remove idle samples at the start and end of the recorded trajectory.

        The edge anchors (first/last sample position) define the settling zone:
        points are idle only while they stay within IDLE_EDGE_EPSILON of the
        anchor. Slow but real motion accumulates displacement past the epsilon
        and is therefore preserved. Surviving timestamps are re-based so the
        loop starts at t = 0.
        """
        pts = self.points
        if len(pts) < 3:
            return

        start = 0
        while start < len(pts) - 1 and _point_distance(pts[0], pts[start + 1]) <= IDLE_EDGE_EPSILON:
            start += 1

        end = len(pts) - 1
        while end > start and _point_distance(pts[-1], pts[end - 1]) <= IDLE_EDGE_EPSILON:
            end -= 1

        trimmed = pts[start : end + 1]
        if len(trimmed) < 2:
            return

        t0 = trimmed[0].timestamp
        self.points = [
            TrajectoryPoint(timestamp=max(0.0, p.timestamp - t0), x=p.x, y=p.y)
            for p in trimmed
        ]

    def _close_loop(self) -> int:
        """Sweep a momentum-matched Hermite curve from the last sample back to the first.

        The closing segment exits along the trajectory's final momentum and arrives
        along the direction the motion originally left the start point, so the loop
        restarts seamlessly instead of snapping onto a straight return line. The gap
        is traversed at the trajectory's average speed. Degenerate momentum falls
        back to a linear closure. Returns the number of closure points appended.
        """
        pts = self.points
        if len(pts) < 3:
            return 0

        first, last = pts[0], pts[-1]
        gap = _point_distance(first, last)
        if gap <= IDLE_EDGE_EPSILON:
            return 0

        total_t = last.timestamp - first.timestamp
        if total_t <= 0.0:
            return 0
        path_len = sum(_point_distance(pts[i - 1], pts[i]) for i in range(1, len(pts)))
        if path_len <= 0.0:
            return 0

        steps = sorted(pts[i].timestamp - pts[i - 1].timestamp for i in range(1, len(pts)))
        step = steps[len(steps) // 2]
        if step <= 1e-6:
            step = total_t / (len(pts) - 1)

        speed = path_len / total_t
        count = max(1, min(256, round((gap / speed) / step)))

        tail = _edge_momentum(pts, from_end=True)
        head = _edge_momentum(pts, from_end=False)
        t0x, t0y = (tail[0] * gap * HERMITE_TENSION, tail[1] * gap * HERMITE_TENSION) if tail else (0.0, 0.0)
        t1x, t1y = (head[0] * gap * HERMITE_TENSION, head[1] * gap * HERMITE_TENSION) if head else (0.0, 0.0)

        lx, ly = last.x, last.y
        fx, fy = first.x, first.y
        for k in range(1, count + 1):
            s = k / count
            s2 = s * s
            s3 = s2 * s
            h00 = 2.0 * s3 - 3.0 * s2 + 1.0
            h10 = s3 - 2.0 * s2 + s
            h01 = -2.0 * s3 + 3.0 * s2
            h11 = s3 - s2
            self.points.append(
                TrajectoryPoint(
                    timestamp=last.timestamp + step * k,
                    x=clamp_coordinate(h00 * lx + h10 * t0x + h01 * fx + h11 * t1x),
                    y=clamp_coordinate(h00 * ly + h10 * t0y + h01 * fy + h11 * t1y),
                )
            )
        return count

    def _smooth_closure(self, start: int) -> None:
        """Relax appended closure samples with the moving-average kernel.

        Recorded samples and both seam anchors (loop start and closure end) stay
        pinned; only the closure waypoints are averaged, easing the junctions
        between the Hermite curve and the manual path.
        """
        pts = self.points
        half = len(SMOOTHING_KERNEL) // 2
        weight_sum = float(sum(SMOOTHING_KERNEL))
        smoothed = list(pts)
        for i in range(start, len(pts) - 1):
            x_acc = 0.0
            y_acc = 0.0
            for offset, w in enumerate(SMOOTHING_KERNEL):
                j = min(max(i - half + offset, 0), len(pts) - 1)
                sample = pts[j]
                x_acc += sample.x * w
                y_acc += sample.y * w
            smoothed[i] = TrajectoryPoint(
                timestamp=pts[i].timestamp,
                x=clamp_coordinate(x_acc / weight_sum),
                y=clamp_coordinate(y_acc / weight_sum),
            )
        self.points = smoothed

    def play(self) -> None:
        """Start or resume looping playback."""
        if len(self.points) > 1 or self.automator != AutomatorType.NONE:
            self.state = RecorderState.PLAYING

    def pause(self) -> None:
        """Pause playback at the current position."""
        if self.state == RecorderState.PLAYING:
            self.state = RecorderState.PAUSED

    def stop(self) -> None:
        """Stop playback and rewind to the start."""
        self.state = RecorderState.STOPPED
        self._playback_time = 0.0
        self._ping_pong_forward = True

    def clear(self) -> None:
        """Clear all stored points and reset transport."""
        self.points.clear()
        self.state = RecorderState.STOPPED
        self._playback_time = 0.0

    def update(self, dt: float) -> Optional[Tuple[float, float]]:
        """Advance time by dt seconds and return current (X, Y) position."""
        if self.state == RecorderState.PLAYING:
            dur = self.duration
            if dur <= 0.0 and self.automator == AutomatorType.NONE:
                return None

            # Handle Algorithmic Automators
            if self.automator != AutomatorType.NONE:
                return self._step_automator(dt)

            # Advance playback accumulator with speed scaling
            scaled_dt = dt * max(0.01, self.speed)

            if self.loop_mode == LoopMode.FORWARD:
                self._playback_time = (self._playback_time + scaled_dt) % dur
            elif self.loop_mode == LoopMode.REVERSE:
                self._playback_time = (self._playback_time - scaled_dt) % dur
            elif self.loop_mode == LoopMode.PING_PONG:
                if self._ping_pong_forward:
                    self._playback_time += scaled_dt
                    if self._playback_time >= dur:
                        self._playback_time = dur
                        self._ping_pong_forward = False
                else:
                    self._playback_time -= scaled_dt
                    if self._playback_time <= 0.0:
                        self._playback_time = 0.0
                        self._ping_pong_forward = True
            elif self.loop_mode == LoopMode.ONE_SHOT:
                self._playback_time += scaled_dt
                if self._playback_time >= dur:
                    self._playback_time = dur
                    self.state = RecorderState.STOPPED

            return self.get_position_at(self._playback_time)

        elif self.state == RecorderState.RECORDING and self.points:
            return (self.points[-1].x, self.points[-1].y)

        elif self.state == RecorderState.PAUSED and self.points:
            return self.get_position_at(self._playback_time)

        return None

    def get_position_at(self, t: float) -> Tuple[float, float]:
        """Interpolate smooth (X, Y) coordinate at specific timestamp t."""
        if not self.points:
            return (0.5, 0.5)
        if len(self.points) == 1:
            return (self.points[0].x, self.points[0].y)

        dur = self.duration
        target_t = max(0.0, min(dur, t))

        # Binary search or scan for bounding bracket
        left_idx = 0
        for i in range(len(self.points) - 1):
            if self.points[i].timestamp <= target_t <= self.points[i + 1].timestamp:
                left_idx = i
                break
            if self.points[i + 1].timestamp > target_t:
                left_idx = i
                break
        else:
            left_idx = len(self.points) - 2

        p0 = self.points[left_idx]
        p1 = self.points[left_idx + 1]

        dt = p1.timestamp - p0.timestamp
        if dt <= 1e-6:
            alpha = 0.0
        else:
            alpha = max(0.0, min(1.0, (target_t - p0.timestamp) / dt))

        interp_x = p0.x + alpha * (p1.x - p0.x)
        interp_y = p0.y + alpha * (p1.y - p0.y)

        return (clamp_coordinate(interp_x), clamp_coordinate(interp_y))

    def _step_automator(self, dt: float) -> Tuple[float, float]:
        """Generate mathematical coordinates from selected algorithmic automator."""
        cx = self.center_x
        cy = self.center_y
        time_scale = (self.bpm / 120.0) * max(0.05, self.speed)
        effective_dt = dt * time_scale

        if self.automator == AutomatorType.CIRCLE:
            # Gravitational celestial N-body orbital physics around attractor (cx, cy)
            # Scaled to a graceful, hypnotic musical tempo (matching ~4 to 8-bar cycles)
            orbit_dt = effective_dt * 0.42
            px = self._body_x
            py = self._body_y

            dx = cx - px
            dy = cy - py
            dist_sq = dx * dx + dy * dy
            dist = math.sqrt(dist_sq)

            # If velocity is zero (initial launch without fling), initiate stable circular orbit
            v_mag = math.hypot(self._body_vx, self._body_vy)
            if v_mag < 0.05 or dist < 0.03:
                target_r = 0.28
                G_init = 0.35
                v_circ = math.sqrt(G_init / target_r)
                angle = math.atan2(py - cy, px - cx) if dist > 0.04 else 0.0
                px = cx + target_r * math.cos(angle)
                py = cy + target_r * math.sin(angle)
                self._body_vx = -v_circ * math.sin(angle)
                self._body_vy = v_circ * math.cos(angle)
                dx = cx - px
                dy = cy - py
                dist_sq = dx * dx + dy * dy
                dist = math.sqrt(dist_sq)

            # Gravitational attraction: a = G / (r^2 + epsilon)
            G = 0.35
            epsilon = 0.035  # Softening factor prevents extreme slingshot singularities
            force = G / (dist_sq + epsilon)
            ax = force * (dx / max(0.01, dist))
            ay = force * (dy / max(0.01, dist))

            # Numerical integration with orbit_dt
            self._body_vx += ax * orbit_dt
            self._body_vy += ay * orbit_dt

            # Subtle orbital drag/viscosity prevents perpetual energy buildup
            self._body_vx *= (1.0 - 0.02 * orbit_dt)
            self._body_vy *= (1.0 - 0.02 * orbit_dt)

            px += self._body_vx * orbit_dt
            py += self._body_vy * orbit_dt

            # Cushioned bounce at pad boundaries
            margin = 0.04
            if px < margin:
                px = margin
                self._body_vx = abs(self._body_vx) * 0.75
            elif px > 1.0 - margin:
                px = 1.0 - margin
                self._body_vx = -abs(self._body_vx) * 0.75

            if py < margin:
                py = margin
                self._body_vy = abs(self._body_vy) * 0.75
            elif py > 1.0 - margin:
                py = 1.0 - margin
                self._body_vy = -abs(self._body_vy) * 0.75

            self._body_x = px
            self._body_y = py
            return (clamp_coordinate(px), clamp_coordinate(py))

        elif self.automator == AutomatorType.LISSAJOUS:
            # 3:2 frequency ratio classic Lissajous bow centered on (cx, cy)
            freq = (self.bpm / 60.0) * (1.0 / 16.0) * self.speed
            self._automator_phase = (self._automator_phase + 2.0 * math.pi * freq * dt) % (2.0 * math.pi)
            radius = 0.28
            x = cx + radius * math.sin(self._automator_phase * 3.0)
            y = cy + radius * math.sin(self._automator_phase * 2.0)
            return (clamp_coordinate(x), clamp_coordinate(y))

        elif self.automator == AutomatorType.SPIRAL:
            freq = (self.bpm / 60.0) * (1.0 / 16.0) * self.speed
            self._automator_phase = (self._automator_phase + 2.0 * math.pi * freq * dt) % (2.0 * math.pi)
            dyn_radius = 0.08 + 0.22 * (0.5 + 0.5 * math.sin(self._automator_phase * 0.3))
            x = cx + dyn_radius * math.cos(self._automator_phase * 2.0)
            y = cy + dyn_radius * math.sin(self._automator_phase * 2.0)
            return (clamp_coordinate(x), clamp_coordinate(y))

        elif self.automator == AutomatorType.CHAOS:
            # Multi-harmonic incommensurate phase drift:
            # Combines irrational frequency ratios (golden ratio phi, sqrt(2), sqrt(3), sqrt(5))
            # into a completely smooth, continuous, non-repeating organic wander across all 4 quadrants.
            base_omega = 2.0 * math.pi * (self.bpm / 120.0) * 0.08 * max(0.05, self.speed)

            # Advancing phases with irrational speed ratios
            self._chaos_phase1 = (self._chaos_phase1 + base_omega * 1.00000 * dt) % (2.0 * math.pi)
            self._chaos_phase2 = (self._chaos_phase2 + base_omega * 1.61803 * dt) % (2.0 * math.pi)
            self._chaos_phase3 = (self._chaos_phase3 + base_omega * 2.41421 * dt) % (2.0 * math.pi)
            self._chaos_phase4 = (self._chaos_phase4 + base_omega * 1.41421 * dt) % (2.0 * math.pi)
            self._chaos_phase5 = (self._chaos_phase5 + base_omega * 1.73205 * dt) % (2.0 * math.pi)
            self._chaos_phase6 = (self._chaos_phase6 + base_omega * 2.23607 * dt) % (2.0 * math.pi)

            # Superposition excursion (up to +/- 0.42 from attractor center)
            dx = (
                0.22 * math.sin(self._chaos_phase1)
                + 0.13 * math.cos(self._chaos_phase2 + 0.9)
                + 0.07 * math.sin(self._chaos_phase3 + 2.1)
            )
            dy = (
                0.22 * math.cos(self._chaos_phase4)
                + 0.13 * math.sin(self._chaos_phase5 + 1.4)
                + 0.07 * math.cos(self._chaos_phase6 + 3.0)
            )

            x = cx + dx
            y = cy + dy
            return (clamp_coordinate(x), clamp_coordinate(y))

        return (0.5, 0.5)

    def step_wavetable(self, dt: float) -> Optional[float]:
        """Compute the next 1D wavetable morph position if sweep is active."""
        if self.wavetable_sweep == WavetableSweepMode.MANUAL:
            return None

        time_scale = (self.bpm / 120.0) * max(0.05, self.speed)
        # 1 full sweep cycle every 4 bars at 1x
        freq = (1.0 / 8.0) * time_scale

        if self.wavetable_sweep == WavetableSweepMode.SINE:
            self._wt_phase = (self._wt_phase + 2.0 * math.pi * freq * dt) % (2.0 * math.pi)
            return 0.5 + 0.5 * math.sin(self._wt_phase)

        elif self.wavetable_sweep == WavetableSweepMode.TRIANGLE:
            self._wt_phase = (self._wt_phase + freq * dt) % 1.0
            if self._wt_phase < 0.5:
                return self._wt_phase * 2.0
            else:
                return 2.0 - self._wt_phase * 2.0

        elif self.wavetable_sweep == WavetableSweepMode.RAMP:
            self._wt_phase = (self._wt_phase + freq * dt) % 1.0
            return self._wt_phase

        elif self.wavetable_sweep == WavetableSweepMode.RANDOM_STEP:
            beat_interval = 60.0 / (self.bpm * max(0.1, self.speed))
            self._wt_step_timer += dt
            if self._wt_step_timer >= beat_interval:
                self._wt_step_timer = 0.0
                self._wt_target = random.random()

            # Smooth exponential slew to target
            self._wt_current += (self._wt_target - self._wt_current) * min(1.0, 8.0 * dt)
            return max(0.0, min(1.0, self._wt_current))

        elif self.wavetable_sweep == WavetableSweepMode.CHAOS:
            # Multi-harmonic continuous irrational drift (never sticks or flatlines at edges)
            base_omega = 2.0 * math.pi * (self.bpm / 120.0) * 0.08 * max(0.05, self.speed)
            self._wt_chaos_phase1 = (self._wt_chaos_phase1 + base_omega * 1.00000 * dt) % (2.0 * math.pi)
            self._wt_chaos_phase2 = (self._wt_chaos_phase2 + base_omega * 1.61803 * dt) % (2.0 * math.pi)
            self._wt_chaos_phase3 = (self._wt_chaos_phase3 + base_omega * 2.41421 * dt) % (2.0 * math.pi)
            self._wt_chaos_phase4 = (self._wt_chaos_phase4 + base_omega * 1.73205 * dt) % (2.0 * math.pi)

            raw_excursion = (
                0.50 * math.sin(self._wt_chaos_phase1)
                + 0.30 * math.cos(self._wt_chaos_phase2 + 0.9)
                + 0.18 * math.sin(self._wt_chaos_phase3 + 2.1)
                + 0.10 * math.cos(self._wt_chaos_phase4 + 1.4)
            )
            # Smooth hyperbolic tangent compression provides organic turnaround without edge clipping
            pos = 0.5 + 0.48 * math.tanh(1.5 * raw_excursion)
            return max(0.0, min(1.0, pos))

        return None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize trajectory and metadata to dictionary."""
        return {
            "bpm": self.bpm,
            "speed": self.speed,
            "loop_mode": self.loop_mode.value,
            "sync_bars": self.sync_bars,
            "duration": self.duration,
            "points": [asdict(p) for p in self.points],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MotionRecorder:
        """Instantiate a MotionRecorder from serialized dictionary."""
        rec = cls(bpm=data.get("bpm", 120.0))
        rec.speed = data.get("speed", 1.0)
        rec.loop_mode = LoopMode(data.get("loop_mode", LoopMode.FORWARD.value))
        rec.sync_bars = data.get("sync_bars", 0)

        raw_points = data.get("points", [])
        rec.points = [
            TrajectoryPoint(
                timestamp=p["timestamp"],
                x=p["x"],
                y=p["y"],
            )
            for p in raw_points
        ]
        return rec

    def save_json(self, path: Path | str) -> None:
        """Save trajectory to JSON file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    def load_json(self, path: Path | str) -> None:
        """Load trajectory from JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        loaded = self.from_dict(data)
        self.bpm = loaded.bpm
        self.speed = loaded.speed
        self.loop_mode = loaded.loop_mode
        self.sync_bars = loaded.sync_bars
        self.points = loaded.points
