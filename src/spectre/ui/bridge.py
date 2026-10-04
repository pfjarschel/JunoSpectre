"""Python-QML bridge interfacing the VectorEngine with Qt Quick.

Exposes reactive properties, transport signals, and invokable slots for touch gestures.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from PyQt6.QtCore import QObject, QTimer, pyqtProperty, pyqtSignal, pyqtSlot

from ..core.waves import WaveCatalogManager
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
    toneWavesChanged = pyqtSignal()
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
    requestOpenWaveBrowser = pyqtSignal(int)
    requestOpenScreensOverlay = pyqtSignal()

    # Self-Contained Sound Sculptor & Advanced Mod Signals
    linkedModeChanged = pyqtSignal(bool)
    tvfEnvDepthChanged = pyqtSignal(int)
    tvfAttackChanged = pyqtSignal(int)
    tvfDecayChanged = pyqtSignal(int)
    tvfSustainChanged = pyqtSignal(int)
    tvfReleaseChanged = pyqtSignal(int)
    tvfTypeChanged = pyqtSignal(str)
    tvfKeyFollowChanged = pyqtSignal(int)
    tvfVeloSensChanged = pyqtSignal(int)
    tvaDecayChanged = pyqtSignal(int)
    tvaSustainChanged = pyqtSignal(int)
    tvaPanChanged = pyqtSignal(int)
    tvaVeloSensChanged = pyqtSignal(int)
    pitchCoarseChanged = pyqtSignal(int)
    pitchFineChanged = pyqtSignal(int)
    portamentoTimeChanged = pyqtSignal(int)
    portamentoSwitchChanged = pyqtSignal(bool)
    legatoSwitchChanged = pyqtSignal(bool)
    lfoParamsChanged = pyqtSignal()
    brightnessChanged = pyqtSignal(int)

    def __init__(self, engine: VectorEngine, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.engine = engine

        # Waveform catalog & active tone waveforms (Bank, WaveNum)
        self._wave_catalog = WaveCatalogManager.get_instance()
        self._tone_waves: list[tuple[str, int]] = [
            ("INTA", 579),  # Tone 1 (NW): Juno Saw HD
            ("INTA", 600),  # Tone 2 (NE): Juno Sqr HD
            ("INTA", 620),  # Tone 3 (SW): 700 Triangle
            ("INTA", 625),  # Tone 4 (SE): Sine
        ]
        self._cached_tone_wave_data: list[dict] = [
            self._wave_catalog.get_wave(b, n) for b, n in self._tone_waves
        ]

        # Cached properties
        self._patch_name: str = "0001 Grand Pno DS"
        self._sound_mode: str = "PATCH"
        self._last_tick_time: float = time.perf_counter()

        # Workstation Shell State
        self._active_view: str = "JUNO PCM"
        self._master_cutoff: int = 64
        self._master_reso: int = 64
        self._master_attack: int = 64
        self._master_release: int = 64
        self._master_level: int = 100
        self._macros: list[int] = [64, 64, 64, 64, 64, 64, 64, 64]

        # Sound Sculptor & Advanced Mod State
        self._linked_mode: bool = False
        self._tvf_env_depth: int = 0
        self._tvf_attack: int = 40
        self._tvf_decay: int = 50
        self._tvf_sustain: int = 70
        self._tvf_release: int = 50
        self._tvf_type: str = "LPF"
        self._tvf_key_follow: int = 0
        self._tvf_velo_sens: int = 0
        self._tva_decay: int = 50
        self._tva_sustain: int = 70
        self._tva_pan: int = 0
        self._tva_velo_sens: int = 0
        self._pitch_coarse: int = 0
        self._pitch_fine: int = 0
        self._portamento_time: int = 20
        self._portamento_switch: bool = False
        self._legato_switch: bool = False
        self._lfo1: dict = {
            "rate": 64, "wave": "TRI", "pitch_depth": 0, "tvf_depth": 0, "tva_depth": 0,
            "pan_depth": 0, "delay_time": 0, "fade_mode": "ON-IN", "fade_time": 0, "sync": False
        }
        self._lfo2: dict = {
            "rate": 45, "wave": "SIN", "pitch_depth": 0, "tvf_depth": 0, "tva_depth": 0,
            "pan_depth": 0, "delay_time": 0, "fade_mode": "ON-IN", "fade_time": 0, "sync": False
        }
        self._brightness: int = 85

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

    @pyqtProperty("QVariantList", notify=toneWavesChanged)
    def toneWaveData(self) -> list:
        return self._cached_tone_wave_data

    # Sound Sculptor & Advanced Mod Properties
    @pyqtProperty(bool, notify=linkedModeChanged)
    def linkedMode(self) -> bool:
        return self._linked_mode

    @pyqtProperty(int, notify=tvfEnvDepthChanged)
    def tvfEnvDepth(self) -> int:
        return self._tvf_env_depth

    @pyqtProperty(int, notify=tvfAttackChanged)
    def tvfAttack(self) -> int:
        return self._tvf_attack

    @pyqtProperty(int, notify=tvfDecayChanged)
    def tvfDecay(self) -> int:
        return self._tvf_decay

    @pyqtProperty(int, notify=tvfSustainChanged)
    def tvfSustain(self) -> int:
        return self._tvf_sustain

    @pyqtProperty(int, notify=tvfReleaseChanged)
    def tvfRelease(self) -> int:
        return self._tvf_release

    @pyqtProperty(int, notify=pitchCoarseChanged)
    def pitchCoarse(self) -> int:
        return self._pitch_coarse

    @pyqtProperty(int, notify=pitchFineChanged)
    def pitchFine(self) -> int:
        return self._pitch_fine

    @pyqtProperty(int, notify=portamentoTimeChanged)
    def portamentoTime(self) -> int:
        return self._portamento_time

    @pyqtProperty(bool, notify=portamentoSwitchChanged)
    def portamentoSwitch(self) -> bool:
        return self._portamento_switch

    @pyqtProperty(bool, notify=legatoSwitchChanged)
    def legatoSwitch(self) -> bool:
        return self._legato_switch

    @pyqtProperty(int, notify=brightnessChanged)
    def brightness(self) -> int:
        return self._brightness

    @pyqtProperty(int, notify=lfoParamsChanged)
    def lfo1Rate(self) -> int:
        return self._lfo1["rate"]

    @pyqtProperty(str, notify=lfoParamsChanged)
    def lfo1Wave(self) -> str:
        return self._lfo1["wave"]

    @pyqtProperty(int, notify=lfoParamsChanged)
    def lfo1PitchDepth(self) -> int:
        return self._lfo1["pitch_depth"]

    @pyqtProperty(int, notify=lfoParamsChanged)
    def lfo1TvfDepth(self) -> int:
        return self._lfo1["tvf_depth"]

    @pyqtProperty(int, notify=lfoParamsChanged)
    def lfo1TvaDepth(self) -> int:
        return self._lfo1["tva_depth"]

    @pyqtProperty(int, notify=lfoParamsChanged)
    def lfo2Rate(self) -> int:
        return self._lfo2["rate"]

    @pyqtProperty(str, notify=lfoParamsChanged)
    def lfo2Wave(self) -> str:
        return self._lfo2["wave"]

    @pyqtProperty(int, notify=lfoParamsChanged)
    def lfo2PitchDepth(self) -> int:
        return self._lfo2["pitch_depth"]

    @pyqtProperty(int, notify=lfoParamsChanged)
    def lfo2TvfDepth(self) -> int:
        return self._lfo2["tvf_depth"]

    @pyqtProperty(int, notify=lfoParamsChanged)
    def lfo2TvaDepth(self) -> int:
        return self._lfo2["tva_depth"]

    @pyqtProperty(str, notify=tvfTypeChanged)
    def tvfType(self) -> str:
        return self._tvf_type

    @pyqtProperty(int, notify=tvfKeyFollowChanged)
    def tvfKeyFollow(self) -> int:
        return self._tvf_key_follow

    @pyqtProperty(int, notify=tvfVeloSensChanged)
    def tvfVeloSens(self) -> int:
        return self._tvf_velo_sens

    @pyqtProperty(int, notify=tvaDecayChanged)
    def tvaDecay(self) -> int:
        return self._tva_decay

    @pyqtProperty(int, notify=tvaSustainChanged)
    def tvaSustain(self) -> int:
        return self._tva_sustain

    @pyqtProperty(int, notify=tvaPanChanged)
    def tvaPan(self) -> int:
        return self._tva_pan

    @pyqtProperty(int, notify=tvaVeloSensChanged)
    def tvaVeloSens(self) -> int:
        return self._tva_velo_sens

    @pyqtProperty(int, notify=lfoParamsChanged)
    def lfo1PanDepth(self) -> int:
        return self._lfo1.get("pan_depth", 0)

    @pyqtProperty(int, notify=lfoParamsChanged)
    def lfo1DelayTime(self) -> int:
        return self._lfo1.get("delay_time", 0)

    @pyqtProperty(str, notify=lfoParamsChanged)
    def lfo1FadeMode(self) -> str:
        return self._lfo1.get("fade_mode", "ON-IN")

    @pyqtProperty(int, notify=lfoParamsChanged)
    def lfo1FadeTime(self) -> int:
        return self._lfo1.get("fade_time", 0)

    @pyqtProperty(bool, notify=lfoParamsChanged)
    def lfo1Sync(self) -> bool:
        return self._lfo1.get("sync", False)

    @pyqtProperty(int, notify=lfoParamsChanged)
    def lfo2PanDepth(self) -> int:
        return self._lfo2.get("pan_depth", 0)

    @pyqtProperty(int, notify=lfoParamsChanged)
    def lfo2DelayTime(self) -> int:
        return self._lfo2.get("delay_time", 0)

    @pyqtProperty(str, notify=lfoParamsChanged)
    def lfo2FadeMode(self) -> str:
        return self._lfo2.get("fade_mode", "ON-IN")

    @pyqtProperty(int, notify=lfoParamsChanged)
    def lfo2FadeTime(self) -> int:
        return self._lfo2.get("fade_time", 0)

    @pyqtProperty(bool, notify=lfoParamsChanged)
    def lfo2Sync(self) -> bool:
        return self._lfo2.get("sync", False)

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
        v = view.upper().strip()
        if v in ("PATCH EDIT", "JUNO-DS", "JUNO_PCM"):
            v = "JUNO PCM"
        elif v in ("4-OSC VA", "4OSC VA", "VA ENGINE"):
            v = "VA"
        elif v in ("MACRO DECK", "MACRO"):
            v = "MACROS"
        elif v in ("MFX STUDIO", "EFFECTS", "EFFECTS STUDIO"):
            v = "MFX"
        elif v in ("MASTER EFFECTS", "MASTER_FX"):
            v = "MASTER FX"
        elif v in ("STEP-LFO", "STEPLFO"):
            v = "STEP LFO"
        elif v in ("PITCH-ENV", "PITCHENV"):
            v = "PITCH ENV"
        elif v in ("MOD-MATRIX", "MODMATRIX"):
            v = "MOD MATRIX"
        elif v in ("PERF-MIXER", "PERFMIXER"):
            v = "PERF MIXER"
        elif v in ("MIDI-LEARN", "MIDILEARN"):
            v = "MIDI LEARN"
        elif v in ("HARDWARE CONFIG", "HARDWARE_CONFIG"):
            v = "HARDWARE"

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

    @pyqtSlot(int, str, int)
    def setToneWave(self, tone_number: int, bank: str, wave_num: int) -> None:
        """Assign waveform to tone (1..4) and send SysEx to Roland hardware."""
        if 1 <= tone_number <= 4:
            self._tone_waves[tone_number - 1] = (bank.upper(), wave_num)
            self._cached_tone_wave_data = [
                self._wave_catalog.get_wave(b, n) for b, n in self._tone_waves
            ]
            if self.engine.juno:
                try:
                    self.engine.juno.set_tone_wave(tone_number, bank=bank.upper(), wave_num=wave_num)
                except Exception as e:
                    logger.error(f"Error setting wave on synth: {e}")
            self.toneWavesChanged.emit()

    @pyqtSlot(str, int, result="QVariantMap")
    def getWaveInfo(self, bank: str, wave_num: int) -> dict:
        """Get wave metadata from catalog."""
        return self._wave_catalog.get_wave(bank, wave_num)

    @pyqtSlot()
    def syncPatchFromSynth(self) -> None:
        """Query active patch name, sound mode, and all 4 tone waveforms from Roland hardware."""
        if not self.engine.juno:
            logger.info("Cannot sync: No Roland synthesizer connected.")
            return

        try:
            logger.info("Syncing patch info and tone waveforms from Roland hardware...")
            try:
                name = self.engine.juno.get_patch_name(timeout=0.8)
                if name:
                    self._patch_name = name
            except Exception as e:
                logger.warning(f"Could not read patch name: {e}")

            try:
                mode = self.engine.juno.get_sound_mode(timeout=0.8)
                self._sound_mode = mode.name
            except Exception as e:
                logger.warning(f"Could not read sound mode: {e}")

            self.patchInfoChanged.emit(self._patch_name, self._sound_mode)

            # Query 4 tone waveforms
            active_waves = self.engine.juno.get_all_tone_waves(timeout=0.8)
            for idx, (bank, wnum) in enumerate(active_waves):
                if idx < 4:
                    self._tone_waves[idx] = (bank, wnum)

            self._cached_tone_wave_data = [
                self._wave_catalog.get_wave(b, n) for b, n in self._tone_waves
            ]
            self.toneWavesChanged.emit()
            logger.info(
                f"Synced from synth: Patch='{self._patch_name}', "
                f"Waves={[w['name'] for w in self._cached_tone_wave_data]}"
            )
        except Exception as e:
            logger.error(f"Error syncing from synth: {e}")

    @pyqtSlot(str, str, str, result="QVariantList")
    def getFilteredWaves(self, category: str = "ALL", bank: str = "ALL", search: str = "") -> list:
        """Query waveform catalog filtered by category, bank, and search string."""
        return self._wave_catalog.get_filtered_waves(category=category, bank=bank, search=search)

    @pyqtSlot(int)
    def openWaveBrowser(self, tone_index: int) -> None:
        """Request the UI to open the Wave Browser modal for a target tone (1-4)."""
        logger.debug(f"UI requested wave browser for Tone {tone_index}")
        self.requestOpenWaveBrowser.emit(tone_index)

    @pyqtSlot()
    def openScreensOverlay(self) -> None:
        """Request UI to open the Screens Launcher overlay."""
        self.requestOpenScreensOverlay.emit()

    @pyqtSlot(bool)
    def setLinkedMode(self, linked: bool) -> None:
        """Toggle linked mode across all 4 tones."""
        if self._linked_mode != linked:
            self._linked_mode = linked
            self.linkedModeChanged.emit(self._linked_mode)

    @pyqtSlot(int)
    def setTvfEnvDepth(self, depth: int) -> None:
        """Set TVF envelope depth (-63..+63)."""
        clamped = max(-63, min(63, int(depth)))
        if self._tvf_env_depth != clamped:
            self._tvf_env_depth = clamped
            self.tvfEnvDepthChanged.emit(self._tvf_env_depth)

    @pyqtSlot(int)
    def setTvfAttack(self, val: int) -> None:
        clamped = max(0, min(127, int(val)))
        if self._tvf_attack != clamped:
            self._tvf_attack = clamped
            self.tvfAttackChanged.emit(self._tvf_attack)

    @pyqtSlot(int)
    def setTvfDecay(self, val: int) -> None:
        clamped = max(0, min(127, int(val)))
        if self._tvf_decay != clamped:
            self._tvf_decay = clamped
            self.tvfDecayChanged.emit(self._tvf_decay)

    @pyqtSlot(int)
    def setTvfSustain(self, val: int) -> None:
        clamped = max(0, min(127, int(val)))
        if self._tvf_sustain != clamped:
            self._tvf_sustain = clamped
            self.tvfSustainChanged.emit(self._tvf_sustain)

    @pyqtSlot(int)
    def setTvfRelease(self, val: int) -> None:
        clamped = max(0, min(127, int(val)))
        if self._tvf_release != clamped:
            self._tvf_release = clamped
            self.tvfReleaseChanged.emit(self._tvf_release)

    @pyqtSlot(str)
    def setTvfType(self, val: str) -> None:
        if self._tvf_type != val:
            self._tvf_type = val
            self.tvfTypeChanged.emit(self._tvf_type)

    @pyqtSlot(int)
    def setTvfKeyFollow(self, val: int) -> None:
        clamped = max(-100, min(100, int(val)))
        if self._tvf_key_follow != clamped:
            self._tvf_key_follow = clamped
            self.tvfKeyFollowChanged.emit(self._tvf_key_follow)

    @pyqtSlot(int)
    def setTvfVeloSens(self, val: int) -> None:
        clamped = max(0, min(127, int(val)))
        if self._tvf_velo_sens != clamped:
            self._tvf_velo_sens = clamped
            self.tvfVeloSensChanged.emit(self._tvf_velo_sens)

    @pyqtSlot(int)
    def setTvaDecay(self, val: int) -> None:
        clamped = max(0, min(127, int(val)))
        if self._tva_decay != clamped:
            self._tva_decay = clamped
            self.tvaDecayChanged.emit(self._tva_decay)

    @pyqtSlot(int)
    def setTvaSustain(self, val: int) -> None:
        clamped = max(0, min(127, int(val)))
        if self._tva_sustain != clamped:
            self._tva_sustain = clamped
            self.tvaSustainChanged.emit(self._tva_sustain)

    @pyqtSlot(int)
    def setTvaPan(self, val: int) -> None:
        clamped = max(-64, min(63, int(val)))
        if self._tva_pan != clamped:
            self._tva_pan = clamped
            self.tvaPanChanged.emit(self._tva_pan)

    @pyqtSlot(int)
    def setTvaVeloSens(self, val: int) -> None:
        clamped = max(0, min(127, int(val)))
        if self._tva_velo_sens != clamped:
            self._tva_velo_sens = clamped
            self.tvaVeloSensChanged.emit(self._tva_velo_sens)

    @pyqtSlot(int)
    def setPitchCoarse(self, val: int) -> None:
        clamped = max(-24, min(24, int(val)))
        if self._pitch_coarse != clamped:
            self._pitch_coarse = clamped
            self.pitchCoarseChanged.emit(self._pitch_coarse)

    @pyqtSlot(int)
    def setPitchFine(self, val: int) -> None:
        clamped = max(-50, min(50, int(val)))
        if self._pitch_fine != clamped:
            self._pitch_fine = clamped
            self.pitchFineChanged.emit(self._pitch_fine)

    @pyqtSlot(int)
    def setPortamentoTime(self, val: int) -> None:
        clamped = max(0, min(127, int(val)))
        if self._portamento_time != clamped:
            self._portamento_time = clamped
            self.portamentoTimeChanged.emit(self._portamento_time)

    @pyqtSlot(bool)
    def setPortamentoSwitch(self, enabled: bool) -> None:
        if self._portamento_switch != enabled:
            self._portamento_switch = enabled
            self.portamentoSwitchChanged.emit(self._portamento_switch)

    @pyqtSlot(bool)
    def setLegatoSwitch(self, enabled: bool) -> None:
        if self._legato_switch != enabled:
            self._legato_switch = enabled
            self.legatoSwitchChanged.emit(self._legato_switch)

    @pyqtSlot(int, str, "QVariant")
    def setLfoParam(self, lfo_idx: int, param: str, val) -> None:
        target = self._lfo1 if lfo_idx == 1 else self._lfo2
        if param in target:
            target[param] = val
            self.lfoParamsChanged.emit()

    @pyqtSlot(int)
    def setBrightness(self, val: int) -> None:
        clamped = max(10, min(100, int(val)))
        if self._brightness != clamped:
            self._brightness = clamped
            self.brightnessChanged.emit(self._brightness)

    @pyqtSlot()
    def restartApp(self) -> None:
        """Fast restart application."""
        import sys
        import os
        from PyQt6.QtGui import QGuiApplication
        logger.info("Restarting application...")
        app = QGuiApplication.instance()
        if app:
            app.quit()
        os.execv(sys.executable, [sys.executable] + sys.argv)

