"""High-level Vector Engine coordinating 2D/1D morphing, motion loops, and rate-limited SysEx.

Protects Roland USB-MIDI buffer from saturation via configurable rate throttling (50Hz default)
and dirty-state change detection.
"""

from __future__ import annotations

from dataclasses import dataclass
import enum
import logging
import time
from typing import Callable, List, Optional, Tuple

from ..core.protocol import JunoClient
from .math import (
    CrossfadeCurve,
    calculate_cartesian_levels,
    calculate_wavetable_levels,
    clamp_coordinate,
)
from .motion import AutomatorType, LoopMode, MotionRecorder, RecorderState

logger = logging.getLogger(__name__)


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
    tone_levels: Tuple[int, int, int, int]
    recorder_state: RecorderState
    loop_mode: LoopMode
    automator: AutomatorType
    is_converged: bool


class VectorEngine:
    """Coordinates vector morphing, motion playback, and Roland SysEx transmission."""

    def __init__(
        self,
        juno_client: Optional[JunoClient] = None,
        max_update_hz: float = 50.0,
        curve: CrossfadeCurve = CrossfadeCurve.NORMALIZED,
    ):
        self.juno = juno_client
        self.max_update_hz = max_update_hz
        self.curve = curve

        self.mode: MorphMode = MorphMode.VECTOR_2D
        self.x: float = 0.5
        self.y: float = 0.5
        self.w: float = 0.0

        self.motion = MotionRecorder()
        self.tone_levels: Tuple[int, int, int, int] = (32, 32, 32, 32)
        self.tone_mutes: List[bool] = [False, False, False, False]

        self._last_dispatch_time: float = 0.0
        self._last_dispatched_levels: Tuple[int, int, int, int] = (-1, -1, -1, -1)
        self._subscribers: List[Callable[[VectorState], None]] = []

        # Calculate initial levels
        self._recalculate_levels()

    def subscribe(self, callback: Callable[[VectorState], None]) -> None:
        """Register a subscriber callback for vector state changes."""
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[VectorState], None]) -> None:
        """Unregister a subscriber callback."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def set_mode(self, mode: MorphMode) -> None:
        """Switch between 2D Vector Pad and 1D Wavetable Scanner."""
        if self.mode != mode:
            self.mode = mode
            self._recalculate_levels()
            self._dispatch_if_needed(force=True)
            self._notify_subscribers()

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

    def set_curve(self, curve: CrossfadeCurve) -> None:
        """Set crossfade curve (Linear or Equal-Power)."""
        if self.curve != curve:
            self.curve = curve
            self._recalculate_levels()
            self._dispatch_if_needed(force=True)
            self._notify_subscribers()

    def toggle_tone_mute(self, tone_idx: int) -> bool:
        """Toggle mute state for tone 1..4. Returns new muted state."""
        if 1 <= tone_idx <= 4:
            self.tone_mutes[tone_idx - 1] = not self.tone_mutes[tone_idx - 1]
            self._recalculate_levels()
            self._dispatch_if_needed(force=True)
            self._notify_subscribers()
            return self.tone_mutes[tone_idx - 1]
        return False

    def set_tone_mute(self, tone_idx: int, muted: bool) -> None:
        """Set mute state for tone 1..4."""
        if 1 <= tone_idx <= 4:
            self.tone_mutes[tone_idx - 1] = muted
            self._recalculate_levels()
            self._dispatch_if_needed(force=True)
            self._notify_subscribers()

    def set_tone_level(self, tone_idx: int, level: int) -> None:
        """Directly adjust level of a single tone (1..4) from 0..127."""
        if 1 <= tone_idx <= 4:
            clamped = max(0, min(127, int(level)))
            levels = list(self.tone_levels)
            levels[tone_idx - 1] = 0 if self.tone_mutes[tone_idx - 1] else clamped
            self.tone_levels = (levels[0], levels[1], levels[2], levels[3])
            self._dispatch_if_needed(force=True)
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
        """Compute 4-tone TVA levels based on active mode and mutes."""
        if self.mode == MorphMode.VECTOR_2D:
            raw = calculate_cartesian_levels(self.x, self.y, curve=self.curve)
        else:
            raw = calculate_wavetable_levels(self.w, curve=self.curve)

        self.tone_levels = (
            0 if self.tone_mutes[0] else raw[0],
            0 if self.tone_mutes[1] else raw[1],
            0 if self.tone_mutes[2] else raw[2],
            0 if self.tone_mutes[3] else raw[3],
        )

    def _dispatch_if_needed(self, force: bool = False) -> None:
        """Send SysEx to synth with rate-limiting and change detection."""
        now = time.perf_counter()
        interval = 1.0 / max(1.0, self.max_update_hz)

        # Check rate limit
        if not force and (now - self._last_dispatch_time < interval):
            return

        # Check dirty state (only send if levels actually changed)
        if not force and self.tone_levels == self._last_dispatched_levels:
            return

        self._last_dispatch_time = now
        self._last_dispatched_levels = self.tone_levels

        # Dispatch SysEx to Roland synth
        if self.juno:
            try:
                # Send all 4 tone levels
                self.juno.set_tone_levels(self.tone_levels)
            except Exception as e:
                logger.error(f"Failed to dispatch vector levels to synth: {e}")

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
            is_converged=True,
        )
