"""Drift lock: how fast the audio device's clock runs against the Pi's.

The sequencer times notes with the Pi clock; audio plays at the JUNO's
44.1 kHz crystal. Two crystals differ by tens of ppm, which over a long
backing track adds up to an audible flam. The worker reports (frames played,
time that block left the DAC) four times a second; the slope of frames over
time is the device's real rate. The sequencer clock is trimmed by that ratio
so notes and audio advance together.

DAC timestamps jitter by up to about a millisecond, so the estimate uses a
long window (up to 10 minutes) and only counts after 30 s of data. An
underrun breaks the frames/time line, so it starts the measurement over.
"""

from __future__ import annotations

import collections
from typing import Optional

import numpy as np

WINDOW_S = 600.0       # use the last 10 minutes
MIN_SPAN_S = 30.0      # before this, no correction
MAX_PPM = 500.0        # a real crystal is far inside this; anything beyond is a bad estimate


class DriftEstimator:
    def __init__(self, rate: int = 44100):
        self.rate = rate
        self.points: collections.deque = collections.deque()   # (dac time, frames)
        self._xruns = -1

    def reset(self) -> None:
        self.points.clear()

    def add(self, frames: int, dac: float, xruns: int = 0) -> None:
        if dac <= 0:
            return
        if xruns != self._xruns:
            self._xruns = xruns
            self.reset()                      # a dropout (or a fresh worker): start over
        if self.points and (frames <= self.points[-1][1] or dac <= self.points[-1][0]):
            self.reset()                      # the worker restarted
        self.points.append((float(dac), int(frames)))
        while self.points and dac - self.points[0][0] > WINDOW_S:
            self.points.popleft()

    @property
    def span(self) -> float:
        return self.points[-1][0] - self.points[0][0] if len(self.points) > 1 else 0.0

    def ppm(self) -> Optional[float]:
        """The device clock's error in ppm (+ = fast), None until MIN_SPAN_S of data."""
        if self.span < MIN_SPAN_S:
            return None
        t = np.array([p[0] for p in self.points])
        f = np.array([p[1] for p in self.points], dtype=np.float64)
        t -= t.mean()
        f -= f.mean()
        slope = float((t * f).sum() / (t * t).sum())
        ppm = (slope / self.rate - 1.0) * 1e6
        return ppm if abs(ppm) <= MAX_PPM else None

    def ratio(self) -> float:
        """Device rate / nominal rate (1.0 while unknown)."""
        ppm = self.ppm()
        return 1.0 if ppm is None else 1.0 + ppm * 1e-6
