"""High-precision, low-jitter real-time PPQN clock for the Juno Spectre Sequencer."""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)

PPQN_96 = 96  # Standard pulses per quarter note


class SequencerClock:
    """Real-time clock emitting PPQN pulses on a dedicated background thread."""

    def __init__(self, bpm: float = 120.0, ppqn: int = PPQN_96):
        self.ppqn = ppqn
        self._bpm: float = max(20.0, min(300.0, float(bpm)))
        self._tick_interval: float = 60.0 / (self._bpm * self.ppqn)
        self._swing: float = 0.50  # 0.50 (neutral) .. 0.75 (max swing)
        # Drift lock: runs this much faster than nominal (audio device rate / nominal)
        self._rate_trim: float = 1.0

        self._running: bool = False
        self._paused: bool = False
        self._thread: Optional[threading.Thread] = None

        self._tick_counter: int = 0
        self._total_ticks: int = 0
        # perf_counter() time the tick being fired was due (callbacks schedule from it)
        self.tick_time: float = 0.0
        self._start_at: Optional[float] = None

        self._tick_callbacks: list[Callable[[int, int], None]] = []

    @property
    def bpm(self) -> float:
        return self._bpm

    def set_bpm(self, bpm: float) -> None:
        self._bpm = max(20.0, min(300.0, float(bpm)))
        self._tick_interval = 60.0 / (self._bpm * self.ppqn)

    @property
    def tick_interval(self) -> float:
        """Seconds per tick (without swing, with the drift trim)."""
        return self._tick_interval / self._rate_trim

    @property
    def rate_trim(self) -> float:
        return self._rate_trim

    def set_rate_trim(self, ratio: float) -> None:
        """Run `ratio` times the nominal speed (drift lock: a few ppm, clamped to 0.1%)."""
        self._rate_trim = max(0.999, min(1.001, float(ratio)))

    @property
    def swing(self) -> float:
        return self._swing

    def set_swing(self, swing: float) -> None:
        self._swing = max(0.50, min(0.75, float(swing)))

    @property
    def is_running(self) -> bool:
        return self._running and not self._paused

    @property
    def is_stopped(self) -> bool:
        """Fully stopped (not merely paused)."""
        return not self._running

    @property
    def current_tick(self) -> int:
        return self._tick_counter

    @property
    def total_ticks(self) -> int:
        return self._total_ticks

    def register_tick_callback(self, callback: Callable[[int, int], None]) -> None:
        if callback not in self._tick_callbacks:
            self._tick_callbacks.append(callback)

    def unregister_tick_callback(self, callback: Callable[[int, int], None]) -> None:
        if callback in self._tick_callbacks:
            self._tick_callbacks.remove(callback)

    def start(self, at: Optional[float] = None) -> None:
        """Run from tick 0, the first tick at perf_counter() time `at` (None = now)."""
        if self._running:
            self._paused = False
            return
        self._start_at = at
        self._running = True
        self._paused = False
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="SequencerPPQNClock")
        self._thread.start()

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        if self._running and self._paused:
            self._paused = False
        elif not self._running:
            self.start()

    def stop(self) -> None:
        self._running = False
        self._paused = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.2)
        self._thread = None
        self._tick_counter = 0
        self._total_ticks = 0

    def reset(self) -> None:
        self._tick_counter = 0
        self._total_ticks = 0

    def _run_loop(self) -> None:
        """Sleep-until-target loop.

        Linux sleeps are accurate to ~0.1 ms (finer than USB-MIDI's 1 ms
        frames), so the thread sleeps to ~0.2 ms before the tick and covers the
        rest with sleep(0), which releases the GIL instead of spinning on it.
        """
        target_time = self._start_at if self._start_at is not None else time.perf_counter()
        ticks_per_16th = self.ppqn // 4  # 24 ticks per 16th note at 96 PPQN

        while self._running:
            if self._paused:
                time.sleep(0.01)
                target_time = time.perf_counter()
                continue

            now = time.perf_counter()
            remaining = target_time - now
            if remaining > 0.0003:
                time.sleep(remaining - 0.0002)
                continue
            elif remaining > 0.0:
                time.sleep(0)
                continue

            # Calculate interval for this tick taking swing into account
            # Even 16th notes get prolonged, odd 16th notes get shortened
            step_16th = (self._tick_counter // ticks_per_16th) % 2
            if self._swing != 0.50:
                # Swing scaling: 0.5 is neutral, 0.67 is triplet swing
                swing_mult = (self._swing * 2.0) if step_16th == 0 else ((1.0 - self._swing) * 2.0)
                tick_step = self._tick_interval * swing_mult / self._rate_trim
            else:
                tick_step = self._tick_interval / self._rate_trim

            tick_num = self._tick_counter
            tot_num = self._total_ticks
            self.tick_time = target_time

            # Advance tick counters
            bar_ticks = self.ppqn * 4  # 384 ticks per 4/4 bar
            self._tick_counter = (self._tick_counter + 1) % bar_ticks
            self._total_ticks += 1
            target_time += tick_step

            # Fire tick callbacks
            for cb in list(self._tick_callbacks):
                try:
                    cb(tick_num, tot_num)
                except Exception as e:
                    logger.debug(f"Error in sequencer tick callback: {e}")
