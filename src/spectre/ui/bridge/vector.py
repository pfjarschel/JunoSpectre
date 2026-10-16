"""Vector bridge mixin: pad, motion recorder, automators, tempo, tone mix and panic."""

from __future__ import annotations

import logging
import time

from PyQt6.QtCore import QTimer, pyqtProperty, pyqtSignal, pyqtSlot

from ...vector.engine import MorphMode, VectorState
from ...vector.math import CrossfadeCurve
from ...vector.motion import AutomatorType, LoopMode, RecorderState, WavetableSweepMode
from .base import BridgeBaseMixin

logger = logging.getLogger(__name__)


class VectorBridgeMixin(BridgeBaseMixin):
    """Vector pad coordinates, motion transport, automators and tone mix."""

    coordinatesChanged = pyqtSignal(float, float)
    attractorChanged = pyqtSignal(float, float)
    wavetablePosChanged = pyqtSignal(float)
    wavetableSweepModeChanged = pyqtSignal(str)
    morphModeChanged = pyqtSignal(str)
    transportStateChanged = pyqtSignal(str)
    loopModeChanged = pyqtSignal(str)
    speedChanged = pyqtSignal(float)
    bpmChanged = pyqtSignal(float)
    automatorChanged = pyqtSignal(str)
    autoTrimChanged = pyqtSignal(bool)
    autoCloseChanged = pyqtSignal(bool)
    smoothingChanged = pyqtSignal(bool)
    motionPointsChanged = pyqtSignal()
    curveChanged = pyqtSignal(str)

    def _init_vector(self) -> None:
        """Engine dirty-check state and the 60 FPS animation/transport tick."""
        self._last_tick_time: float = time.perf_counter()
        self._last_x: float = self.vector.x
        self._last_y: float = self.vector.y
        self._last_w: float = self.vector.w
        self._last_tone_levels: tuple[int, int, int, int] = self.vector.tone_levels
        self._last_transport: str = self.vector.motion.state.value
        self.vector.subscribe(self._on_vector_state_changed)
        self._timer = QTimer(self)
        self._timer.setInterval(16)  # ~60 Hz
        self._timer.timeout.connect(self._on_timer_tick)
        self._timer.start()

    def _on_timer_tick(self) -> None:
        """Tick engine time forward to update motion loops and automators."""
        now = time.perf_counter()
        dt = now - self._last_tick_time
        self._last_tick_time = now
        self.vector.update(dt)
        if self.vector.motion.state == RecorderState.RECORDING:
            self.motionPointsChanged.emit()

    def _on_vector_state_changed(self, state: VectorState) -> None:
        """Handle state notification from VectorEngine with dirty-change detection."""
        if abs(state.x - self._last_x) > 1e-4 or abs(state.y - self._last_y) > 1e-4:
            self._last_x = state.x
            self._last_y = state.y
            self.coordinatesChanged.emit(state.x, state.y)

        if abs(state.w - self._last_w) > 1e-4:
            self._last_w = state.w
            self.wavetablePosChanged.emit(state.w)

        if state.tone_levels != self._last_tone_levels:
            self._last_tone_levels = state.tone_levels
            for i in range(4):
                self.patch_state.tones[i].level = state.tone_levels[i]
            self.toneLevelsChanged.emit(
                state.tone_levels[0],
                state.tone_levels[1],
                state.tone_levels[2],
                state.tone_levels[3],
            )

        if state.recorder_state.value != self._last_transport:
            self._last_transport = state.recorder_state.value
            self.transportStateChanged.emit(state.recorder_state.value)

    @pyqtProperty(float, notify=coordinatesChanged)
    def vectorX(self) -> float:
        return self.vector.x

    @pyqtProperty(float, notify=coordinatesChanged)
    def vectorY(self) -> float:
        return self.vector.y

    @pyqtProperty(float, notify=wavetablePosChanged)
    def wavetablePos(self) -> float:
        return self.vector.w

    @pyqtProperty(str, notify=transportStateChanged)
    def recorderState(self) -> str:
        return self.vector.motion.state.value

    @pyqtProperty(str, notify=loopModeChanged)
    def loopMode(self) -> str:
        return self.vector.motion.loop_mode.value

    @pyqtProperty(float, notify=speedChanged)
    def speed(self) -> float:
        return self.vector.motion.speed

    @pyqtProperty(float, notify=bpmChanged)
    def bpm(self) -> float:
        """The one global tempo, owned by the sequencer song (saved with songs/setlists)."""
        return self.sequencer.bpm
        return self.vector.motion.bpm

    @pyqtProperty(str, notify=automatorChanged)
    def automator(self) -> str:
        return self.vector.motion.automator.value

    @pyqtProperty(bool, notify=autoTrimChanged)
    def autoTrim(self) -> bool:
        return self.vector.motion.auto_trim

    @pyqtProperty(bool, notify=autoCloseChanged)
    def autoClose(self) -> bool:
        return self.vector.motion.auto_close

    @pyqtProperty(bool, notify=smoothingChanged)
    def smoothing(self) -> bool:
        return self.vector.motion.smoothing

    @pyqtProperty(float, notify=attractorChanged)
    def attractorX(self) -> float:
        return self.vector.motion.center_x

    @pyqtProperty(float, notify=attractorChanged)
    def attractorY(self) -> float:
        return self.vector.motion.center_y

    @pyqtProperty(str, notify=wavetableSweepModeChanged)
    def wavetableSweepMode(self) -> str:
        return self.vector.motion.wavetable_sweep.value

    @pyqtProperty(str, notify=curveChanged)
    def curve(self) -> str:
        return self.vector.curve.value

    @pyqtSlot(float, float)
    def setCoordinates(self, x: float, y: float) -> None:
        """Update 2D vector coordinates or guide automator orbit center."""
        if self.vector.motion.automator != AutomatorType.NONE and self.vector.motion.automator != AutomatorType.CIRCLE:
            self.vector.motion.set_orbit_center(x, y)
            self.attractorChanged.emit(self.vector.motion.center_x, self.vector.motion.center_y)
        self.vector.set_coordinates(x, y, record_gesture=True)
        self._rebaseDirect([("vector.x", self.vector.x), ("vector.y", self.vector.y)])

    @pyqtSlot(float, float)
    def setOrbitAttractor(self, x: float, y: float) -> None:
        """Set the gravitational attractor center for orbital automators."""
        self.vector.motion.set_orbit_center(x, y)
        self.attractorChanged.emit(self.vector.motion.center_x, self.vector.motion.center_y)

    @pyqtSlot(float, float, float, float)
    def fling(self, x: float, y: float, vx: float, vy: float) -> None:
        """Launch puck into gravitational orbit with position and momentum velocity."""
        self.vector.motion.fling(x, y, vx, vy)
        self.vector.set_coordinates(x, y, record_gesture=False)

    @pyqtSlot(float)
    def setWavetablePos(self, w: float) -> None:
        """Update 1D wavetable morph position from slider."""
        self.vector.set_wavetable_pos(w)
        self._rebaseDirect([("vector.w", self.vector.w)])

    @pyqtSlot(str)
    def setWavetableSweepMode(self, mode_str: str) -> None:
        """Select 1D wavetable sweep generator mode."""
        try:
            mode = WavetableSweepMode(mode_str)
            self.vector.motion.wavetable_sweep = mode
            self.wavetableSweepModeChanged.emit(mode.value)
        except ValueError:
            logger.warning(f"Invalid wavetable sweep mode: {mode_str}")

    @pyqtSlot(str)
    def setMorphMode(self, mode_str: str) -> None:
        """Toggle between 2D Vector and 1D Wavetable."""
        try:
            mode = MorphMode(mode_str)
            self.vector.set_mode(mode)
            self.morphModeChanged.emit(mode.value)
            if mode == MorphMode.VECTOR_2D and self._active_view != "VECTOR":
                self._active_view = "VECTOR"
                self.activeViewChanged.emit(self._active_view)
            elif mode == MorphMode.WAVETABLE_1D and self._active_view != "WAVETABLE":
                self._active_view = "WAVETABLE"
                self.activeViewChanged.emit(self._active_view)
        except ValueError:
            logger.warning(f"Invalid morph mode: {mode_str}")

    @pyqtSlot()
    def startRecording(self) -> None:
        """Begin recording a gesture trajectory."""
        self.vector.motion.start_recording(clear_existing=True)
        self.transportStateChanged.emit(self.vector.motion.state.value)
        self.motionPointsChanged.emit()

    @pyqtSlot()
    def stopRecording(self) -> None:
        """Stop gesture recording and begin looping."""
        self.vector.motion.stop_recording()
        self.transportStateChanged.emit(self.vector.motion.state.value)
        self.motionPointsChanged.emit()

    @pyqtSlot()
    def playMotion(self) -> None:
        """Resume trajectory loop playback."""
        self.vector.motion.play()
        self.transportStateChanged.emit(self.vector.motion.state.value)

    @pyqtSlot()
    def pauseMotion(self) -> None:
        """Pause trajectory loop playback."""
        self.vector.motion.pause()
        self.transportStateChanged.emit(self.vector.motion.state.value)

    @pyqtSlot()
    def stopMotion(self) -> None:
        """Stop and rewind playback."""
        self.vector.motion.stop()
        self.transportStateChanged.emit(self.vector.motion.state.value)

    @pyqtSlot()
    def clearMotion(self) -> None:
        """Clear all trajectory points."""
        self.vector.motion.clear()
        self.transportStateChanged.emit(self.vector.motion.state.value)
        self.motionPointsChanged.emit()

    @pyqtSlot(result="QVariantList")
    def getMotionPath(self) -> list:
        """Return recorded trajectory points as [x, y] normalized pairs."""
        return [[pt.x, pt.y] for pt in self.vector.motion.points]

    @pyqtSlot(str)
    def setLoopMode(self, mode_str: str) -> None:
        """Set loop playback mode."""
        try:
            mode = LoopMode(mode_str)
            self.vector.motion.loop_mode = mode
            self.loopModeChanged.emit(mode.value)
        except ValueError:
            pass

    @pyqtSlot(float)
    def setSpeed(self, speed_val: float) -> None:
        """Set motion speed multiplier."""
        self.vector.motion.speed = max(0.1, min(4.0, speed_val))
        self._rebaseDirect([("vector.speed", self.vector.motion.speed)])
        self.speedChanged.emit(self.vector.motion.speed)

    @pyqtSlot(str)
    def setAutomator(self, auto_str: str) -> None:
        """Select algorithmic orbital automator."""
        try:
            auto = AutomatorType(auto_str)
            self.vector.motion.automator = auto
            self.automatorChanged.emit(auto.value)
            if auto != AutomatorType.NONE and self.vector.motion.state != RecorderState.PLAYING:
                self.vector.motion.play()
                self.transportStateChanged.emit(self.vector.motion.state.value)
        except ValueError:
            pass

    @pyqtSlot(bool)
    def setAutoTrim(self, enabled: bool) -> None:
        """Toggle automatic trimming of idle lead-in and tail-off samples."""
        self.vector.motion.auto_trim = bool(enabled)
        self.autoTrimChanged.emit(self.vector.motion.auto_trim)

    @pyqtSlot(bool)
    def setAutoClose(self, enabled: bool) -> None:
        """Toggle automatic closure of the loop back to the start point."""
        self.vector.motion.auto_close = bool(enabled)
        self.autoCloseChanged.emit(self.vector.motion.auto_close)

    @pyqtSlot(bool)
    def setSmoothing(self, enabled: bool) -> None:
        """Toggle low-pass smoothing of the trajectory on stop."""
        self.vector.motion.smoothing = bool(enabled)
        self.smoothingChanged.emit(self.vector.motion.smoothing)

    @pyqtSlot(int)
    def setTvaLevel(self, val: int) -> None:
        """Set active tone TVA Level (0..127). Ganged across all 4 tones if linked."""
        clamped = max(0, min(127, int(val)))
        targets = self._target_tones()
        for t in targets:
            t.level = clamped
            if not t.muted:
                self.vector.set_tone_level(t.tone_index, clamped)
                if self.juno:
                    try:
                        self.juno.set_tone_level(t.tone_index, clamped)
                    except Exception as e:
                        logger.error(f"Error setting tone level on synth: {e}")
        self._rebaseDirect([(f"tone.{t.tone_index}.tva_level", clamped) for t in targets])
        self.tvaLevelChanged.emit(self._active_tone().level)
        self.toneLevelsChanged.emit(*[t.level for t in self.patch_state.tones])

    @pyqtSlot(str)
    def setCurve(self, curve_str: str) -> None:
        """Set crossfade curve ('linear' or 'equal_power')."""
        try:
            curve = CrossfadeCurve(curve_str.lower())
            self.vector.set_curve(curve)
            self.curveChanged.emit(curve.value)
        except ValueError:
            logger.warning(f"Invalid curve: {curve_str}")
