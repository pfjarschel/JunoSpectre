"""Vector engine: 2D/1D morphing and motion loops.

The pad sets the four tone levels only when it moves (a drag, a motion loop,
an automator or a wavetable sweep). Each new set of levels goes to the
subscribers at once and to `send` rate-limited (50 Hz default); a move that
falls inside the rate window is sent when the window ends, so the synth
always ends on the last position. Mutes and the patch's own levels belong to
the patch, not to the engine.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

from .math import (
    CrossfadeCurve,
    calculate_cartesian_levels,
    calculate_wavetable_levels,
    clamp_coordinate,
)
from .motion import AutomatorType, LoopMode, MotionRecorder, RecorderState, WavetableSweepMode

logger = logging.getLogger(__name__)

Levels = Tuple[int, int, int, int]


class MorphMode(str, enum.Enum):
    """Active sound morphing mode."""
    VECTOR_2D = "vector_2d"
    WAVETABLE_1D = "wavetable_1d"


@dataclass(frozen=True)
class VectorState:
    """Snapshot of current vector morphing state."""
    mode: MorphMode
    x: float
    y: float
    w: float
    tone_levels: Levels
    recorder_state: RecorderState
    loop_mode: LoopMode
    automator: AutomatorType


class VectorEngine:
    """Vector morphing and motion playback; the levels go out through `send`."""

    def __init__(
        self,
        send: Optional[Callable[[Levels], None]] = None,
        max_update_hz: float = 50.0,
        curve: CrossfadeCurve = CrossfadeCurve.NORMALIZED,
    ):
        self.send = send
        self.max_update_hz = max_update_hz
        self.curve = curve

        self.mode: MorphMode = MorphMode.VECTOR_2D
        self.x: float = 0.5
        self.y: float = 0.5
        self.w: float = 0.0

        self.motion = MotionRecorder()
        # The levels the last move produced (mode and curve apply from the next one)
        self.tone_levels: Levels = (32, 32, 32, 32)

        self._last_dispatch_time: float = 0.0
        self._last_dispatched_levels: Levels = (-1, -1, -1, -1)
        self._subscribers: List[Callable[[VectorState], None]] = []
        self._trailing: Optional[threading.Timer] = None

        self._recalculate_levels()

    def subscribe(self, callback: Callable[[VectorState], None]) -> None:
        """Register a subscriber callback for vector state changes."""
        self._subscribers.append(callback)

    @property
    def needs_tick(self) -> bool:
        """Whether update() has anything to advance (motion, recording or a sweep)."""
        if self.motion.state in (RecorderState.PLAYING, RecorderState.RECORDING):
            return True
        return self.mode == MorphMode.WAVETABLE_1D and self.motion.wavetable_sweep != WavetableSweepMode.MANUAL

    def set_mode(self, mode: MorphMode) -> None:
        """Switch between 2D Vector Pad and 1D Wavetable Scanner (applies from the next move)."""
        self.mode = mode

    def set_curve(self, curve: CrossfadeCurve) -> None:
        """Set the crossfade curve (applies from the next move)."""
        self.curve = curve

    def set_coordinates(self, x: float, y: float, record_gesture: bool = True) -> None:
        """Update 2D Cartesian coordinates (0.0 .. 1.0)."""
        cx = clamp_coordinate(x)
        cy = clamp_coordinate(y)

        if abs(self.x - cx) > 1e-4 or abs(self.y - cy) > 1e-4:
            self.x = cx
            self.y = cy

            if record_gesture and self.motion.state == RecorderState.RECORDING:
                self.motion.record_point(self.x, self.y)

            if self.mode == MorphMode.VECTOR_2D:
                self._recalculate_levels()
                self._dispatch_if_needed()
            self._notify_subscribers()

    def set_wavetable_pos(self, w: float) -> None:
        """Update 1D Wavetable morph position (0.0 .. 1.0)."""
        cw = clamp_coordinate(w)
        if abs(self.w - cw) > 1e-4:
            self.w = cw
            if self.mode == MorphMode.WAVETABLE_1D:
                self._recalculate_levels()
                self._dispatch_if_needed()
            self._notify_subscribers()

    def update(self, dt: float) -> None:
        """Tick engine by delta-time dt (advances motion loops / automators / wavetable sweeps)."""
        if self.mode == MorphMode.VECTOR_2D:
            if self.motion.state == RecorderState.PLAYING:
                pos = self.motion.update(dt)
                if pos is not None:
                    self.set_coordinates(pos[0], pos[1], record_gesture=False)
        else:
            new_w = self.motion.step_wavetable(dt)
            if new_w is not None:
                self.set_wavetable_pos(new_w)

    def _recalculate_levels(self) -> None:
        """Compute the 4 tone levels at the current position."""
        if self.mode == MorphMode.VECTOR_2D:
            raw = calculate_cartesian_levels(self.x, self.y, curve=self.curve)
        else:
            raw = calculate_wavetable_levels(self.w, curve=self.curve)
        self.tone_levels = (raw[0], raw[1], raw[2], raw[3])

    def _dispatch_if_needed(self, force: bool = False) -> None:
        """Send the levels, rate-limited and skipped when unchanged."""
        now = time.perf_counter()
        interval = 1.0 / max(1.0, self.max_update_hz)

        if not force and self.tone_levels == self._last_dispatched_levels:
            return

        # Rate limit: send the latest levels when the window ends
        wait = interval - (now - self._last_dispatch_time)
        if not force and wait > 0:
            if self._trailing is None:
                self._trailing = threading.Timer(wait, self._send_trailing)
                self._trailing.daemon = True
                self._trailing.start()
            return

        self._last_dispatch_time = now
        self._last_dispatched_levels = self.tone_levels
        if self.send:
            try:
                self.send(self.tone_levels)
            except Exception as e:
                logger.error(f"Failed to send vector levels: {e}")

    def _send_trailing(self) -> None:
        self._trailing = None
        self._dispatch_if_needed()

    def _notify_subscribers(self) -> None:
        """Notify UI subscribers immediately when state values change."""
        state = self.get_state()
        for sub in self._subscribers:
            try:
                sub(state)
            except Exception as e:
                logger.error(f"Error in vector state subscriber: {e}")

    def flush(self) -> None:
        """Force immediate transmission of current tone levels and notify subscribers."""
        self._dispatch_if_needed(force=True)
        self._notify_subscribers()

    def get_state(self) -> VectorState:
        """Return immutable snapshot of current engine state."""
        return VectorState(
            mode=self.mode,
            x=self.x,
            y=self.y,
            w=self.w,
            tone_levels=self.tone_levels,
            recorder_state=self.motion.state,
            loop_mode=self.motion.loop_mode,
            automator=self.motion.automator,
        )
