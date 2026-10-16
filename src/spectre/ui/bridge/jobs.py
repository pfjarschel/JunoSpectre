"""Background jobs: long synth round-trips off the UI thread.

Reading 128-256 slot names, writing + verifying a keyboard slot and
pulling a whole performance take seconds. They run one at a time on a
worker thread; QML shows jobText/jobProgress and gets the result from
jobFinished(name, result). Hardware access is safe alongside the UI:
the JunoClient serializes reads and the wire (_io_lock).
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable

from PyQt6.QtCore import pyqtProperty, pyqtSignal, pyqtSlot

from .base import BridgeBaseMixin

logger = logging.getLogger(__name__)


class JobsBridgeMixin(BridgeBaseMixin):
    jobChanged = pyqtSignal()
    jobFinished = pyqtSignal(str, "QVariant")
    _jobDone = pyqtSignal(str, object)        # worker -> UI thread
    _jobStep = pyqtSignal(float, str)         # worker -> UI thread

    _job_name: str = ""
    _job_progress: float = -1.0
    _job_text: str = ""

    def _init_jobs(self) -> None:
        self._jobDone.connect(self._on_job_done)
        self._jobStep.connect(self._on_job_step)

    @pyqtProperty(bool, notify=jobChanged)
    def jobBusy(self) -> bool:
        return self._job_name != ""

    @pyqtProperty(str, notify=jobChanged)
    def jobName(self) -> str:
        return self._job_name

    @pyqtProperty(float, notify=jobChanged)
    def jobProgress(self) -> float:
        """0..1, or -1 while the job can't tell how far it is."""
        return self._job_progress

    @pyqtProperty(str, notify=jobChanged)
    def jobText(self) -> str:
        return self._job_text

    def _start_job(self, name: str, text: str, fn: Callable[[Callable[[float, str], None]], Any]) -> bool:
        """Run fn(progress) on a worker; False when another job is running."""
        if self._job_name:
            return False
        self._job_name, self._job_progress, self._job_text = name, -1.0, text
        self.jobChanged.emit()

        def progress(fraction: float, label: str = "") -> None:
            self._jobStep.emit(float(fraction), str(label))

        def run() -> None:
            try:
                result = fn(progress)
            except Exception as e:
                logger.warning(f"job {name} failed: {e}")
                result = {"error": str(e)}
            try:
                self._jobDone.emit(name, result)
            except RuntimeError:
                pass  # bridge gone (shutdown)

        threading.Thread(target=run, name=f"job-{name}", daemon=True).start()
        return True

    @pyqtSlot(float, str)
    def _on_job_step(self, fraction: float, label: str) -> None:
        if not self._job_name:
            return
        self._job_progress = fraction
        if label:
            self._job_text = label
        self.jobChanged.emit()

    @pyqtSlot(str, object)
    def _on_job_done(self, name: str, result: Any) -> None:
        self._job_name, self._job_progress, self._job_text = "", -1.0, ""
        self.jobChanged.emit()
        if name == "save" and isinstance(result, dict) and result.get("saved"):
            self._saved_as_loaded()      # Shift + move now goes back to the saved state
        self.jobFinished.emit(name, result)

    # -- jobs ------------------------------------------------------------

    @pyqtSlot(str, result=bool)
    def startSlotNameRefresh(self, kind: str) -> bool:
        """Re-read keyboard user slot names ("patch": 256, "perf": 128).

        jobFinished("slotNames", count), count -1 when offline.
        """
        if kind == "perf":
            return self._start_job("slotNames", "Reading 128 user performances…",
                                   lambda p: self.refreshUserPerfNames(progress=p))
        return self._start_job("slotNames", "Reading 256 user slots…",
                               lambda p: self.refreshUserSlotNames(progress=p))

    @pyqtSlot("QVariantMap", result=bool)
    def startSave(self, opts: dict) -> bool:
        """The save dialog's whole sequence: write-back, Pi file, keyboard slot.

        opts: name, category, tags, favorite, updateSources, toDevice, isPerf,
        and the picked slot (number, msb, lsb, pc). jobFinished("save",
        {saved, srcErr, error}).
        """
        o = dict(opts or {})

        def run(progress):
            out = {"saved": False, "srcErr": "", "error": ""}
            if o.get("updateSources"):
                progress(-1.0, "Updating source patches…")
                out["srcErr"] = self.writeBackEditedParts()
            progress(-1.0, "Saving to the Pi…")
            path = self.saveCurrentToFile(str(o.get("name", "")), str(o.get("category", "")),
                                          str(o.get("tags", "")), bool(o.get("favorite", False)), "")
            if not path:
                out["error"] = "Pi save failed (no synth connected?)."
                return out
            out["saved"] = True
            if out["srcErr"] or not o.get("toDevice"):
                return out
            progress(-1.0, "Writing the keyboard slot… do not power off")
            if o.get("isPerf"):
                out["error"] = self.savePerfToDevice(int(o.get("number", 0)), str(o.get("name", "")))
            else:
                out["error"] = self.saveCurrentToDevice(int(o.get("msb", 0)), int(o.get("lsb", 0)),
                                                        int(o.get("pc", 0)), str(o.get("name", "")))
            return out

        return self._start_job("save", "Saving…", run)

    @pyqtSlot(str, int, int, int, str, result=bool)
    def startLibraryLoad(self, kind: str, msb: int, lsb: int, pc: int, name: str) -> bool:
        """Audition a keyboard patch or performance by Bank/PC and read it in.

        jobFinished("load", ok).
        """
        if kind == "performance":
            return self._start_job("load", f"Loading {name or 'performance'}…",
                                   lambda p: self.selectLibraryPerformance(msb, lsb, pc, name))
        return self._start_job("load", f"Loading {name or 'patch'}…",
                               lambda p: self.selectLibraryPatch(msb, lsb, pc, name))
