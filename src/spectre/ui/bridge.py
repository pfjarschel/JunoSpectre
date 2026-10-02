"""Python-QML bridge interfacing the VectorEngine with Qt Quick.

Exposes reactive properties, transport signals, and invokable slots for touch gestures.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from PyQt6.QtCore import QObject, QTimer, pyqtProperty, pyqtSignal, pyqtSlot

from ..vector.engine import MorphMode, VectorEngine, VectorState
from ..vector.math import CrossfadeCurve
from ..vector.motion import AutomatorType, LoopMode, RecorderState, WavetableSweepMode

logger = logging.getLogger(__name__)


class SpectreBridge(QObject):
    """Bridge exposing vector engine state and dispatching touch events to/from QML."""

    # Reactive signals emitted on property changes
    coordinatesChanged = pyqtSignal(float, float)
    attractorChanged = pyqtSignal(float, float)
    wavetablePosChanged = pyqtSignal(float)
    wavetableSweepModeChanged = pyqtSignal(str)
    morphModeChanged = pyqtSignal(str)
    toneLevelsChanged = pyqtSignal(int, int, int, int)
    transportStateChanged = pyqtSignal(str)
    loopModeChanged = pyqtSignal(str)
    speedChanged = pyqtSignal(float)
    bpmChanged = pyqtSignal(float)
    automatorChanged = pyqtSignal(str)
    patchInfoChanged = pyqtSignal(str, str)
    motionPointsChanged = pyqtSignal()

    # Workstation OS Shell signals
    activeViewChanged = pyqtSignal(str)
    toneMutesChanged = pyqtSignal()
    masterCutoffChanged = pyqtSignal(int)
    masterResoChanged = pyqtSignal(int)
    masterAttackChanged = pyqtSignal(int)
    masterReleaseChanged = pyqtSignal(int)
    masterLevelChanged = pyqtSignal(int)
    macrosChanged = pyqtSignal()
    curveChanged = pyqtSignal(str)

    def __init__(self, engine: VectorEngine, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.engine = engine

        # Cached properties
        self._patch_name: str = "0001 Grand Pno DS"
        self._sound_mode: str = "PATCH"
        self._last_tick_time: float = time.perf_counter()

        # Workstation Shell State
        self._active_view: str = "VECTOR"
        self._master_cutoff: int = 64
        self._master_reso: int = 64
        self._master_attack: int = 64
        self._master_release: int = 64
        self._master_level: int = 100
        self._macros: list[int] = [64, 64, 64, 64, 64, 64, 64, 64]

        # Engine state tracking for dirty checks
        self._last_x: float = self.engine.x
        self._last_y: float = self.engine.y
        self._last_w: float = self.engine.w
        self._last_tone_levels: tuple[int, int, int, int] = self.engine.tone_levels
        self._last_transport: str = self.engine.motion.state.value

        # Subscribe to engine state updates
        self.engine.subscribe(self._on_engine_state_changed)

        # 60 FPS animation/transport timer
        self._timer = QTimer(self)
        self._timer.setInterval(16)  # ~60 Hz
        self._timer.timeout.connect(self._on_timer_tick)
        self._timer.start()

    def _on_timer_tick(self) -> None:
        """Tick engine time forward to update motion loops and automators."""
        now = time.perf_counter()
        dt = now - self._last_tick_time
        self._last_tick_time = now

        self.engine.update(dt)

    def _on_engine_state_changed(self, state: VectorState) -> None:
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
            self.toneLevelsChanged.emit(
                state.tone_levels[0],
                state.tone_levels[1],
                state.tone_levels[2],
                state.tone_levels[3],
            )

        if state.recorder_state.value != self._last_transport:
            self._last_transport = state.recorder_state.value
            self.transportStateChanged.emit(state.recorder_state.value)

    # -------------------------------------------------------------------------
    # Properties for QML
    # -------------------------------------------------------------------------

    @pyqtProperty(float, notify=coordinatesChanged)
    def vectorX(self) -> float:
        return self.engine.x

    @pyqtProperty(float, notify=coordinatesChanged)
    def vectorY(self) -> float:
        return self.engine.y

    @pyqtProperty(float, notify=wavetablePosChanged)
    def wavetablePos(self) -> float:
        return self.engine.w

    @pyqtProperty(str, notify=morphModeChanged)
    def morphMode(self) -> str:
        return self.engine.mode.value

    @pyqtProperty(int, notify=toneLevelsChanged)
    def tone1Level(self) -> int:
        return self.engine.tone_levels[0]

    @pyqtProperty(int, notify=toneLevelsChanged)
    def tone2Level(self) -> int:
        return self.engine.tone_levels[1]

    @pyqtProperty(int, notify=toneLevelsChanged)
    def tone3Level(self) -> int:
        return self.engine.tone_levels[2]

    @pyqtProperty(int, notify=toneLevelsChanged)
    def tone4Level(self) -> int:
        return self.engine.tone_levels[3]

    @pyqtProperty(str, notify=transportStateChanged)
    def recorderState(self) -> str:
        return self.engine.motion.state.value

    @pyqtProperty(str, notify=loopModeChanged)
    def loopMode(self) -> str:
        return self.engine.motion.loop_mode.value

    @pyqtProperty(float, notify=speedChanged)
    def speed(self) -> float:
        return self.engine.motion.speed

    @pyqtProperty(float, notify=bpmChanged)
    def bpm(self) -> float:
        return self.engine.motion.bpm

    @pyqtProperty(str, notify=automatorChanged)
    def automator(self) -> str:
        return self.engine.motion.automator.value

    @pyqtProperty(str, notify=patchInfoChanged)
    def patchName(self) -> str:
        return self._patch_name

    @pyqtProperty(str, notify=patchInfoChanged)
    def soundMode(self) -> str:
        return self._sound_mode

    @pyqtProperty(float, notify=attractorChanged)
    def attractorX(self) -> float:
        return self.engine.motion.center_x

    @pyqtProperty(float, notify=attractorChanged)
    def attractorY(self) -> float:
        return self.engine.motion.center_y

    @pyqtProperty(str, notify=wavetableSweepModeChanged)
    def wavetableSweepMode(self) -> str:
        return self.engine.motion.wavetable_sweep.value

    # Workstation Shell Properties
    @pyqtProperty(str, notify=activeViewChanged)
    def activeView(self) -> str:
        return self._active_view

    @pyqtProperty(bool, notify=toneMutesChanged)
    def tone1Muted(self) -> bool:
        return self.engine.tone_mutes[0]

    @pyqtProperty(bool, notify=toneMutesChanged)
    def tone2Muted(self) -> bool:
        return self.engine.tone_mutes[1]

    @pyqtProperty(bool, notify=toneMutesChanged)
    def tone3Muted(self) -> bool:
        return self.engine.tone_mutes[2]

    @pyqtProperty(bool, notify=toneMutesChanged)
    def tone4Muted(self) -> bool:
        return self.engine.tone_mutes[3]

    @pyqtProperty(int, notify=masterCutoffChanged)
    def masterCutoff(self) -> int:
        return self._master_cutoff

    @pyqtProperty(int, notify=masterResoChanged)
    def masterReso(self) -> int:
        return self._master_reso

    @pyqtProperty(int, notify=masterAttackChanged)
    def masterAttack(self) -> int:
        return self._master_attack

    @pyqtProperty(int, notify=masterReleaseChanged)
    def masterRelease(self) -> int:
        return self._master_release

    @pyqtProperty(int, notify=masterLevelChanged)
    def masterLevel(self) -> int:
        return self._master_level

    @pyqtProperty(str, notify=curveChanged)
    def curve(self) -> str:
        return self.engine.curve.value

    @pyqtProperty(int, notify=macrosChanged)
    def macro1(self) -> int:
        return self._macros[0]

    @pyqtProperty(int, notify=macrosChanged)
    def macro2(self) -> int:
        return self._macros[1]

    @pyqtProperty(int, notify=macrosChanged)
    def macro3(self) -> int:
        return self._macros[2]

    @pyqtProperty(int, notify=macrosChanged)
    def macro4(self) -> int:
        return self._macros[3]

    @pyqtProperty(int, notify=macrosChanged)
    def macro5(self) -> int:
        return self._macros[4]

    @pyqtProperty(int, notify=macrosChanged)
    def macro6(self) -> int:
        return self._macros[5]

    @pyqtProperty(int, notify=macrosChanged)
    def macro7(self) -> int:
        return self._macros[6]

    @pyqtProperty(int, notify=macrosChanged)
    def macro8(self) -> int:
        return self._macros[7]

    # -------------------------------------------------------------------------
    # Invokable Slots from QML
    # -------------------------------------------------------------------------

    @pyqtSlot(float, float)
    def setCoordinates(self, x: float, y: float) -> None:
        """Update 2D vector coordinates or guide automator orbit center."""
        if self.engine.motion.automator != AutomatorType.NONE and self.engine.motion.automator != AutomatorType.CIRCLE:
            self.engine.motion.set_orbit_center(x, y)
            self.attractorChanged.emit(self.engine.motion.center_x, self.engine.motion.center_y)
        self.engine.set_coordinates(x, y, record_gesture=True)

    @pyqtSlot(float, float)
    def setOrbitAttractor(self, x: float, y: float) -> None:
        """Set the gravitational attractor center for orbital automators."""
        self.engine.motion.set_orbit_center(x, y)
        self.attractorChanged.emit(self.engine.motion.center_x, self.engine.motion.center_y)

    @pyqtSlot(float, float, float, float)
    def fling(self, x: float, y: float, vx: float, vy: float) -> None:
        """Launch puck into gravitational orbit with position and momentum velocity."""
        self.engine.motion.fling(x, y, vx, vy)
        self.engine.set_coordinates(x, y, record_gesture=False)

    @pyqtSlot(float)
    def setWavetablePos(self, w: float) -> None:
        """Update 1D wavetable morph position from slider."""
        self.engine.set_wavetable_pos(w)

    @pyqtSlot(str)
    def setWavetableSweepMode(self, mode_str: str) -> None:
        """Select 1D wavetable sweep generator mode."""
        try:
            mode = WavetableSweepMode(mode_str)
            self.engine.motion.wavetable_sweep = mode
            self.wavetableSweepModeChanged.emit(mode.value)
        except ValueError:
            logger.warning(f"Invalid wavetable sweep mode: {mode_str}")

    @pyqtSlot(str)
    def setMorphMode(self, mode_str: str) -> None:
        """Toggle between 2D Vector and 1D Wavetable."""
        try:
            mode = MorphMode(mode_str)
            self.engine.set_mode(mode)
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
        self.engine.motion.start_recording(clear_existing=True)
        self.transportStateChanged.emit(self.engine.motion.state.value)
        self.motionPointsChanged.emit()

    @pyqtSlot()
    def stopRecording(self) -> None:
        """Stop gesture recording and begin looping."""
        self.engine.motion.stop_recording()
        self.transportStateChanged.emit(self.engine.motion.state.value)
        self.motionPointsChanged.emit()

    @pyqtSlot()
    def playMotion(self) -> None:
        """Resume trajectory loop playback."""
        self.engine.motion.play()
        self.transportStateChanged.emit(self.engine.motion.state.value)

    @pyqtSlot()
    def pauseMotion(self) -> None:
        """Pause trajectory loop playback."""
        self.engine.motion.pause()
        self.transportStateChanged.emit(self.engine.motion.state.value)

    @pyqtSlot()
    def stopMotion(self) -> None:
        """Stop and rewind playback."""
        self.engine.motion.stop()
        self.transportStateChanged.emit(self.engine.motion.state.value)

    @pyqtSlot()
    def clearMotion(self) -> None:
        """Clear all trajectory points."""
        self.engine.motion.clear()
        self.transportStateChanged.emit(self.engine.motion.state.value)
        self.motionPointsChanged.emit()

    @pyqtSlot(str)
    def setLoopMode(self, mode_str: str) -> None:
        """Set loop playback mode."""
        try:
            mode = LoopMode(mode_str)
            self.engine.motion.loop_mode = mode
            self.loopModeChanged.emit(mode.value)
        except ValueError:
            pass

    @pyqtSlot(float)
    def setSpeed(self, speed_val: float) -> None:
        """Set motion speed multiplier."""
        self.engine.motion.speed = max(0.1, min(4.0, speed_val))
        self.speedChanged.emit(self.engine.motion.speed)

    @pyqtSlot(str)
    def setAutomator(self, auto_str: str) -> None:
        """Select algorithmic orbital automator."""
        try:
            auto = AutomatorType(auto_str)
            self.engine.motion.automator = auto
            self.automatorChanged.emit(auto.value)
            if auto != AutomatorType.NONE and self.engine.motion.state != RecorderState.PLAYING:
                self.engine.motion.play()
                self.transportStateChanged.emit(self.engine.motion.state.value)
        except ValueError:
            pass

    @pyqtSlot(float)
    def setBpm(self, bpm_val: float) -> None:
        """Update tempo BPM."""
        self.engine.motion.bpm = max(20.0, min(300.0, bpm_val))
        self.bpmChanged.emit(self.engine.motion.bpm)

    @pyqtSlot()
    def panic(self) -> None:
        """Send All Notes Off / Reset all controllers."""
        if self.engine.juno and self.engine.juno.midi:
            self.engine.juno.midi.send_all_notes_off()
        logger.info("PANIC: Sent All Notes Off")

    # -------------------------------------------------------------------------
    # Workstation Shell Slots
    # -------------------------------------------------------------------------

    @pyqtSlot(str)
    def setActiveView(self, view: str) -> None:
        """Switch active workstation view tab."""
        v = view.upper()
        if self._active_view != v:
            self._active_view = v
            if v == "VECTOR":
                self.setMorphMode("vector_2d")
            elif v == "WAVETABLE":
                self.setMorphMode("wavetable_1d")
            self.activeViewChanged.emit(self._active_view)

    @pyqtSlot(int)
    def toggleToneMute(self, tone_number: int) -> None:
        """Toggle mute state for tone 1..4."""
        self.engine.toggle_tone_mute(tone_number)
        self.toneMutesChanged.emit()
        self.toneLevelsChanged.emit(*self.engine.tone_levels)

    @pyqtSlot(int, bool)
    def setToneMute(self, tone_number: int, muted: bool) -> None:
        """Set mute state for tone 1..4."""
        self.engine.set_tone_mute(tone_number, muted)
        self.toneMutesChanged.emit()
        self.toneLevelsChanged.emit(*self.engine.tone_levels)

    @pyqtSlot(int)
    def setMasterCutoff(self, val: int) -> None:
        """Set Master Cutoff offset (1..127, 64 is neutral 0)."""
        clamped = max(1, min(127, int(val)))
        if self._master_cutoff != clamped:
            self._master_cutoff = clamped
            self.masterCutoffChanged.emit(self._master_cutoff)
            if self.engine.juno:
                try:
                    self.engine.juno.set_patch_cutoff_offset(self._master_cutoff)
                except Exception as e:
                    logger.error(f"Error setting cutoff offset: {e}")

    @pyqtSlot(int)
    def setMasterReso(self, val: int) -> None:
        """Set Master Resonance offset (1..127, 64 is neutral 0)."""
        clamped = max(1, min(127, int(val)))
        if self._master_reso != clamped:
            self._master_reso = clamped
            self.masterResoChanged.emit(self._master_reso)
            if self.engine.juno:
                try:
                    self.engine.juno.set_patch_resonance_offset(self._master_reso)
                except Exception as e:
                    logger.error(f"Error setting resonance offset: {e}")

    @pyqtSlot(int)
    def setMasterLevel(self, val: int) -> None:
        """Set Master Patch Level (0..127)."""
        clamped = max(0, min(127, int(val)))
        if self._master_level != clamped:
            self._master_level = clamped
            self.masterLevelChanged.emit(self._master_level)
            if self.engine.juno:
                try:
                    self.engine.juno.set_patch_param("level", self._master_level)
                except Exception as e:
                    logger.error(f"Error setting patch level: {e}")

    @pyqtSlot(str)
    def setCurve(self, curve_str: str) -> None:
        """Set crossfade curve ('linear' or 'equal_power')."""
        try:
            curve = CrossfadeCurve(curve_str.lower())
            self.engine.set_curve(curve)
            self.curveChanged.emit(curve.value)
        except ValueError:
            logger.warning(f"Invalid curve: {curve_str}")

    @pyqtSlot(int, int)
    def setMacro(self, index: int, value: int) -> None:
        """Set macro 1..8 value (0..127)."""
        if 1 <= index <= 8:
            clamped = max(0, min(127, int(value)))
            if self._macros[index - 1] != clamped:
                self._macros[index - 1] = clamped
                self.macrosChanged.emit()

    @pyqtSlot(int, int)
    def setToneLevel(self, tone_number: int, level: int) -> None:
        """Directly adjust level of a single tone (1..4) from touch mixer."""
        self.engine.set_tone_level(tone_number, level)
        self.toneLevelsChanged.emit(*self.engine.tone_levels)

    @pyqtSlot(int)
    def setMasterAttack(self, val: int) -> None:
        """Set Master Attack offset (1..127, 64 is neutral 0)."""
        clamped = max(1, min(127, int(val)))
        if self._master_attack != clamped:
            self._master_attack = clamped
            self.masterAttackChanged.emit(self._master_attack)
            if self.engine.juno:
                try:
                    self.engine.juno.set_patch_param("attack_offset", self._master_attack)
                except Exception as e:
                    logger.error(f"Error setting attack offset: {e}")

    @pyqtSlot(int)
    def setMasterRelease(self, val: int) -> None:
        """Set Master Release offset (1..127, 64 is neutral 0)."""
        clamped = max(1, min(127, int(val)))
        if self._master_release != clamped:
            self._master_release = clamped
            self.masterReleaseChanged.emit(self._master_release)
            if self.engine.juno:
                try:
                    self.engine.juno.set_patch_param("release_offset", self._master_release)
                except Exception as e:
                    logger.error(f"Error setting release offset: {e}")
