"""UI-thread stall logger (diagnostics; enable with SPECTRE_STALL_LOG=1).

SPECTRE_STALL_LOG=1 uses a 100 ms threshold; a larger number sets it in ms.
Lines also go to ~/spectre_stalls.log (SPECTRE_STALL_FILE overrides).

A QTimer on the UI thread stamps a heartbeat; a watcher thread samples the
UI thread's Python stack while the heartbeat is late. When the stall ends,
one log line reports its length and the most frequent sampled location in
our code. A stall whose samples sit outside Python (Qt/QML binding work or
rendering) is reported as such.
"""

from __future__ import annotations

import collections
import logging
import os
import sys
import threading
import time
import traceback

from PyQt6.QtCore import QObject, QTimer

logger = logging.getLogger("spectre.stall")

_OUR_CODE = os.sep + "spectre" + os.sep


class StallWatchdog(QObject):
    def __init__(self, threshold_ms: float = 100.0, parent=None):
        super().__init__(parent)
        self._threshold = threshold_ms / 1000.0
        self._beat = time.monotonic()
        self._ui_ident = threading.get_ident()
        self._timer = QTimer(self)
        self._timer.setInterval(15)
        self._timer.timeout.connect(self._stamp)
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._watch, name="stall-watchdog", daemon=True)

    def start(self) -> None:
        self._timer.start()
        self._thread.start()
        logger.info(f"UI stall logging on (threshold {self._threshold * 1000:.0f} ms)")

    def stop(self) -> None:
        self._stop.set()
        self._timer.stop()

    def _stamp(self) -> None:
        self._beat = time.monotonic()

    def _sample(self) -> str:
        frame = sys._current_frames().get(self._ui_ident)
        if frame is None:
            return "(no Python frame)"
        stack = traceback.extract_stack(frame)
        ours = [f for f in stack if _OUR_CODE in f.filename]
        if not ours:
            return "Qt/QML (outside Python)"
        # Innermost frame of ours, with its caller for context
        tail = ours[-2:]
        return " <- ".join(f"{os.path.basename(f.filename)}:{f.lineno} {f.name}"
                           for f in reversed(tail))

    def _watch(self) -> None:
        samples: collections.Counter = collections.Counter()
        stall_start = None
        while not self._stop.wait(0.02):
            late = time.monotonic() - self._beat
            if late > self._threshold:
                if stall_start is None:
                    stall_start = self._beat
                    samples.clear()
                samples[self._sample()] += 1
            elif stall_start is not None:
                ms = (self._beat - stall_start) * 1000
                top = ", ".join(f"{where} x{n}" for where, n in samples.most_common(3))
                logger.warning(f"UI stall {ms:.0f} ms: {top}")
                stall_start = None


def maybe_start(parent=None):
    """Start the watchdog when SPECTRE_STALL_LOG is set (value = threshold ms)."""
    flag = os.environ.get("SPECTRE_STALL_LOG", "")
    if not flag or flag == "0":
        return None
    try:
        threshold = float(flag) if float(flag) > 1 else 100.0
    except ValueError:
        threshold = 100.0
    path = os.path.expanduser(os.environ.get("SPECTRE_STALL_FILE", "~/spectre_stalls.log"))
    try:
        handler = logging.FileHandler(path)
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        logger.addHandler(handler)
    except OSError as e:
        logger.warning(f"stall log file unavailable ({path}): {e}")
    wd = StallWatchdog(threshold, parent)
    wd.start()
    return wd
