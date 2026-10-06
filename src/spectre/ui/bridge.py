"""Python-QML bridge interfacing the VectorEngine with Qt Quick.

Exposes reactive properties, transport signals, and invokable slots for touch gestures,
synthesizer parameters across all workstation screens, bidirectional hardware synchronization,
and full patch template initialization.
"""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, QTimer, pyqtProperty, pyqtSignal, pyqtSlot

from ..core.patch_state import (
    EffectsState,
    MatrixCtrlState,
    PatchCommonState,
    PatchState,
    PerfPartState,
    StepLfoState,
    ToneState,
    TVF_TYPE_NAMES,
    LFO_WAVE_NAMES,
    LFO_FADE_MODE_NAMES,
)
from ..core.env_presets import env_preset_names, get_env_preset
from ..core.updater import GitUpdater, UpdaterError
from ..core.waves import WaveCatalogManager
from ..core.mfx_catalog import get_mfx_catalog, get_mfx_algo, get_mfx_categories, get_mfx_light_catalog
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
    autoTrimChanged = pyqtSignal(bool)
    autoCloseChanged = pyqtSignal(bool)
    smoothingChanged = pyqtSignal(bool)
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
    requestOpenInitPatchModal = pyqtSignal()
    requestOpenEnvOverlay = pyqtSignal(str)
    patchInitialized = pyqtSignal()
    powerActionChanged = pyqtSignal(str)
    telemetryChanged = pyqtSignal()

    # Tone selection & linked mode
    selectedToneChanged = pyqtSignal(int)
    linkedModeChanged = pyqtSignal(bool)

    # Tone sculpting signals
    tvfEnvDepthChanged = pyqtSignal(int)
    tvfAttackChanged = pyqtSignal(int)
    tvfDecayChanged = pyqtSignal(int)
    tvfSustainChanged = pyqtSignal(int)
    tvfReleaseChanged = pyqtSignal(int)
    tvfTypeChanged = pyqtSignal(str)
    tvfKeyFollowChanged = pyqtSignal(int)
    tvfVeloSensChanged = pyqtSignal(int)
    tvaLevelChanged = pyqtSignal(int)
    tvaAttackChanged = pyqtSignal(int)
    tvaDecayChanged = pyqtSignal(int)
    tvaSustainChanged = pyqtSignal(int)
    tvaReleaseChanged = pyqtSignal(int)
    tvaPanChanged = pyqtSignal(int)
    tvaVeloSensChanged = pyqtSignal(int)
    pitchCoarseChanged = pyqtSignal(int)
    pitchFineChanged = pyqtSignal(int)
    portamentoTimeChanged = pyqtSignal(int)
    portamentoSwitchChanged = pyqtSignal(bool)
    legatoSwitchChanged = pyqtSignal(bool)
    analogFeelChanged = pyqtSignal(int)
    lfoParamsChanged = pyqtSignal()
    brightnessChanged = pyqtSignal(int)

    # Workstation views parameter signals
    pitchEnvChanged = pyqtSignal()
    envShapeChanged = pyqtSignal(str)
    chorusParamsChanged = pyqtSignal()
    reverbParamsChanged = pyqtSignal()
    masterEqChanged = pyqtSignal()
    mfxParamsChanged = pyqtSignal()
    mfxValuesChanged = pyqtSignal()
    matrixCtrlChanged = pyqtSignal()
    stepLfoChanged = pyqtSignal()
    perfPartsChanged = pyqtSignal()
    vaParamsChanged = pyqtSignal()
    routingChanged = pyqtSignal()

    # Appliance self-update signals (git release channel)
    versionChanged = pyqtSignal(str)
    updaterBusyChanged = pyqtSignal(bool)
    updaterLogChanged = pyqtSignal(str)
    updateAvailableChanged = pyqtSignal(bool)
    latestVersionChanged = pyqtSignal(str)
    updateAppliedChanged = pyqtSignal(bool)

    def __init__(self, engine: VectorEngine, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.engine = engine

        # Waveform catalog & active tone waveforms (Bank, WaveNum)
        self._wave_catalog = WaveCatalogManager.get_instance()

        # In-memory synth state
        self.patch_state: PatchState = PatchState()
        self._selected_tone: int = 1
        self._linked_mode: bool = False

        self._tone_waves: list[tuple[str, int]] = [
            (t.wave_bank_l, t.wave_num_l) for t in self.patch_state.tones
        ]
        self._cached_tone_wave_data: list[dict] = [
            self._wave_catalog.get_wave(b, n) for b, n in self._tone_waves
        ]

        # Cached properties
        self._patch_name: str = self.patch_state.common.name
        self._sound_mode: str = self.patch_state.sound_mode
        self._last_tick_time: float = time.perf_counter()

        # Workstation Shell State
        self._active_view: str = "JUNO PCM"
        self._brightness: int = 85
        try:
            from ..core.backlight import BacklightController

            self._backlight = BacklightController()
        except Exception as e:
            logger.debug(f"Backlight controller unavailable: {e}")
            self._backlight = None

        # Appliance git-release self updater
        self._updater = GitUpdater(Path(__file__).resolve().parents[3])
        self._updater_busy: bool = False
        self._updater_log: str = "IDLE • RELEASE CHANNEL: GIT TAGS"
        self._latest_version: str = ""
        self._update_available: bool = False
        self._update_applied: bool = False
        try:
            self._version: str = self._updater.version
        except UpdaterError as e:
            self._version = "DEV"
            logger.warning(f"Updater unavailable: {e}")

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

        # Hardware telemetry (System page only, ~1.5 s cadence)
        from ..core.telemetry import SystemTelemetry

        self._telemetry: SystemTelemetry = SystemTelemetry()
        self._telemetry_prev_cpu = None
        self._telemetry_timer = QTimer(self)
        self._telemetry_timer.setInterval(1500)
        self._telemetry_timer.timeout.connect(self._poll_telemetry)

    def _on_timer_tick(self) -> None:
        """Tick engine time forward to update motion loops and automators."""
        now = time.perf_counter()
        dt = now - self._last_tick_time
        self._last_tick_time = now
        self.engine.update(dt)
        if self.engine.motion.state == RecorderState.RECORDING:
            self.motionPointsChanged.emit()

    def _poll_telemetry(self) -> None:
        """Refresh host stats; timer-gated to the SYSTEM view only."""
        if self._active_view != "SYSTEM":
            return
        try:
            from ..core.telemetry import read_telemetry

            snap, self._telemetry_prev_cpu = read_telemetry(self._telemetry_prev_cpu)
            self._telemetry = snap
            self.telemetryChanged.emit()
        except Exception as e:
            logger.debug(f"Telemetry poll failed: {e}")

    def _update_telemetry_polling(self) -> None:
        """Start/stop the 1.5 s telemetry timer based on active view."""
        try:
            if self._active_view == "SYSTEM":
                self._poll_telemetry()  # immediate refresh, no stale mock
                if not self._telemetry_timer.isActive():
                    self._telemetry_timer.start()
            else:
                if self._telemetry_timer.isActive():
                    self._telemetry_timer.stop()
        except Exception as e:
            logger.debug(f"Telemetry timer update failed: {e}")

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

    def _active_tone(self) -> ToneState:
        """Return the ToneState currently active in the UI."""
        return self.patch_state.get_tone(self._selected_tone)

    def _target_tones(self, tone_index: Optional[int] = None) -> list[ToneState]:
        """Return list of target tones to mutate (single or all if linked)."""
        if tone_index is not None:
            return [self.patch_state.get_tone(tone_index)]
        if self._linked_mode:
            return self.patch_state.tones
        return [self._active_tone()]

    def _emit_all_state_signals(self) -> None:
        """Emit signals for all properties to trigger complete UI refresh."""
        self.patchInfoChanged.emit(self._patch_name, self._sound_mode)
        self.selectedToneChanged.emit(self._selected_tone)
        self.toneWavesChanged.emit()
        self.toneLevelsChanged.emit(
            self.patch_state.tones[0].level,
            self.patch_state.tones[1].level,
            self.patch_state.tones[2].level,
            self.patch_state.tones[3].level,
        )
        self.toneMutesChanged.emit()
        self.masterCutoffChanged.emit(self.masterCutoff)
        self.masterResoChanged.emit(self.masterReso)
        self.masterAttackChanged.emit(self.masterAttack)
        self.masterReleaseChanged.emit(self.masterRelease)
        self.masterLevelChanged.emit(self.masterLevel)
        self.portamentoSwitchChanged.emit(self.portamentoSwitch)
        self.portamentoTimeChanged.emit(self.portamentoTime)
        self.legatoSwitchChanged.emit(self.legatoSwitch)
        self.tvfTypeChanged.emit(self.tvfType)
        self.tvfKeyFollowChanged.emit(self.tvfKeyFollow)
        self.tvfEnvDepthChanged.emit(self.tvfEnvDepth)
        self.tvfVeloSensChanged.emit(self.tvfVeloSens)
        self.tvfAttackChanged.emit(self.tvfAttack)
        self.tvfDecayChanged.emit(self.tvfDecay)
        self.tvfSustainChanged.emit(self.tvfSustain)
        self.tvfReleaseChanged.emit(self.tvfRelease)
        self.tvaPanChanged.emit(self.tvaPan)
        self.tvaVeloSensChanged.emit(self.tvaVeloSens)
        self.tvaLevelChanged.emit(self.tvaLevel)
        self.tvaAttackChanged.emit(self.tvaAttack)
        self.tvaDecayChanged.emit(self.tvaDecay)
        self.tvaSustainChanged.emit(self.tvaSustain)
        self.tvaReleaseChanged.emit(self.tvaRelease)
        self.analogFeelChanged.emit(self.analogFeel)
        self.pitchCoarseChanged.emit(self.pitchCoarse)
        self.pitchFineChanged.emit(self.pitchFine)
        self.lfoParamsChanged.emit()
        self.pitchEnvChanged.emit()
        self.envShapeChanged.emit("TVF")
        self.envShapeChanged.emit("TVA")
        self.envShapeChanged.emit("PITCH")
        self.chorusParamsChanged.emit()
        self.reverbParamsChanged.emit()
        self.masterEqChanged.emit()
        self.mfxParamsChanged.emit()
        self.mfxValuesChanged.emit()
        self.matrixCtrlChanged.emit()
        self.stepLfoChanged.emit()
        self.perfPartsChanged.emit()
        self.vaParamsChanged.emit()
        self.macrosChanged.emit()
        self.routingChanged.emit()

    # -------------------------------------------------------------------------
    # Properties for QML: Transport, Vector, and Shell
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
        return self.patch_state.tones[0].level

    @pyqtProperty(int, notify=toneLevelsChanged)
    def tone2Level(self) -> int:
        return self.patch_state.tones[1].level

    @pyqtProperty(int, notify=toneLevelsChanged)
    def tone3Level(self) -> int:
        return self.patch_state.tones[2].level

    @pyqtProperty(int, notify=toneLevelsChanged)
    def tone4Level(self) -> int:
        return self.patch_state.tones[3].level

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

    @pyqtProperty(bool, notify=autoTrimChanged)
    def autoTrim(self) -> bool:
        return self.engine.motion.auto_trim

    @pyqtProperty(bool, notify=autoCloseChanged)
    def autoClose(self) -> bool:
        return self.engine.motion.auto_close

    @pyqtProperty(bool, notify=smoothingChanged)
    def smoothing(self) -> bool:
        return self.engine.motion.smoothing

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

    @pyqtProperty(str, notify=activeViewChanged)
    def activeView(self) -> str:
        return self._active_view

    @pyqtProperty(bool, notify=toneMutesChanged)
    def tone1Muted(self) -> bool:
        return self.patch_state.tones[0].muted

    @pyqtProperty(bool, notify=toneMutesChanged)
    def tone2Muted(self) -> bool:
        return self.patch_state.tones[1].muted

    @pyqtProperty(bool, notify=toneMutesChanged)
    def tone3Muted(self) -> bool:
        return self.patch_state.tones[2].muted

    @pyqtProperty(bool, notify=toneMutesChanged)
    def tone4Muted(self) -> bool:
        return self.patch_state.tones[3].muted

    @pyqtProperty(str, notify=curveChanged)
    def curve(self) -> str:
        return self.engine.curve.value

    @pyqtProperty("QVariantList", notify=toneWavesChanged)
    def toneWaveData(self) -> list:
        return self._cached_tone_wave_data

    # -------------------------------------------------------------------------
    # Properties for QML: Appliance Self-Update (git release channel)
    # -------------------------------------------------------------------------

    @pyqtProperty(str, notify=versionChanged)
    def version(self) -> str:
        return self._version

    @pyqtProperty(bool, notify=updaterBusyChanged)
    def updaterBusy(self) -> bool:
        return self._updater_busy

    @pyqtProperty(str, notify=updaterLogChanged)
    def updaterLog(self) -> str:
        return self._updater_log

    @pyqtProperty(bool, notify=updateAvailableChanged)
    def updateAvailable(self) -> bool:
        return self._update_available

    @pyqtProperty(str, notify=latestVersionChanged)
    def latestVersion(self) -> str:
        return self._latest_version

    @pyqtProperty(bool, notify=updateAppliedChanged)
    def updateApplied(self) -> bool:
        return self._update_applied

    @pyqtProperty(int, notify=brightnessChanged)
    def brightness(self) -> int:
        return self._brightness

    @pyqtProperty(str, notify=brightnessChanged)
    def brightnessMethod(self) -> str:
        return str(getattr(getattr(self, "_backlight", None), "method", "none"))

    # -------------------------------------------------------------------------
    # Properties for QML: Hardware telemetry (System page, 1.5 s poll)
    # -------------------------------------------------------------------------

    @pyqtProperty(str, notify=telemetryChanged)
    def cpuLoadText(self) -> str:
        return f"{self._telemetry.cpu_percent:.0f}%"

    @pyqtProperty(float, notify=telemetryChanged)
    def cpuLoadNorm(self) -> float:
        return max(0.0, min(1.0, self._telemetry.cpu_percent / 100.0))

    @pyqtProperty(str, notify=telemetryChanged)
    def cpuTempText(self) -> str:
        t = self._telemetry.cpu_temp_c
        return f"{t:.1f} °C" if t is not None else "N/A"

    @pyqtProperty(float, notify=telemetryChanged)
    def cpuTempNorm(self) -> float:
        t = self._telemetry.cpu_temp_c
        return max(0.0, min(1.0, t / 100.0)) if t is not None else 0.0

    @pyqtProperty(str, notify=telemetryChanged)
    def ramText(self) -> str:
        return f"{self._telemetry.mem_used_mb} MB / {self._telemetry.mem_total_mb} MB"

    @pyqtProperty(float, notify=telemetryChanged)
    def ramNorm(self) -> float:
        total = self._telemetry.mem_total_mb
        if total <= 0:
            return 0.0
        return max(0.0, min(1.0, self._telemetry.mem_used_mb / total))

    @pyqtProperty(str, notify=telemetryChanged)
    def diskText(self) -> str:
        return f"{self._telemetry.disk_free_gb:.1f} GB FREE"

    @pyqtProperty(float, notify=telemetryChanged)
    def diskNorm(self) -> float:
        total = self._telemetry.disk_total_gb
        if total <= 0:
            return 0.0
        used = max(0.0, total - self._telemetry.disk_free_gb)
        return max(0.0, min(1.0, used / total))

    # -------------------------------------------------------------------------
    # Properties for QML: MIDI & control link (System page, honest link status)
    # -------------------------------------------------------------------------

    @pyqtProperty(str, notify=telemetryChanged)
    def controlRateText(self) -> str:
        try:
            hz = float(getattr(self.engine, "max_update_hz", 50.0))
        except (TypeError, ValueError):
            hz = 50.0
        if hz <= 0:
            hz = 50.0
        return f"{hz:.0f} Hz SysEx dispatch ({1000.0 / hz:.0f} ms)"

    @pyqtProperty(str, notify=telemetryChanged)
    def midiLinkText(self) -> str:
        try:
            juno = getattr(getattr(self, "engine", None), "juno", None)
            midi = getattr(juno, "midi", None) if juno is not None else None
            out = getattr(midi, "juno_out", None) if midi is not None else None
            if out is None or getattr(out, "closed", True):
                return "MOCK / OFFLINE"
            name = str(getattr(out, "name", "") or "").strip()
            return f"USB-MIDI CONNECTED ({name})" if name else "USB-MIDI CONNECTED"
        except Exception:
            return "MOCK / OFFLINE"

    # -------------------------------------------------------------------------
    # Properties for QML: Tone Selection & Linked Mode
    # -------------------------------------------------------------------------

    @pyqtProperty(int, notify=selectedToneChanged)
    def selectedTone(self) -> int:
        return self._selected_tone

    @pyqtProperty(bool, notify=linkedModeChanged)
    def linkedMode(self) -> bool:
        return self._linked_mode

    # -------------------------------------------------------------------------
    # Properties for QML: Tone Parameters (reads from selected tone)
    # -------------------------------------------------------------------------

    @pyqtProperty(int, notify=masterCutoffChanged)
    def masterCutoff(self) -> int:
        return self._active_tone().tvf_cutoff

    @pyqtProperty(int, notify=masterResoChanged)
    def masterReso(self) -> int:
        return self._active_tone().tvf_resonance

    @pyqtProperty(int, notify=masterAttackChanged)
    def masterAttack(self) -> int:
        return self._active_tone().tva_attack

    @pyqtProperty(int, notify=masterReleaseChanged)
    def masterRelease(self) -> int:
        return self._active_tone().tva_release

    @pyqtProperty(int, notify=masterLevelChanged)
    def masterLevel(self) -> int:
        return self.patch_state.common.level

    @pyqtProperty(int, notify=tvfEnvDepthChanged)
    def tvfEnvDepth(self) -> int:
        return self._active_tone().tvf_env_depth_bipolar

    @pyqtProperty(int, notify=tvfAttackChanged)
    def tvfAttack(self) -> int:
        return self._active_tone().tvf_attack

    @pyqtProperty(int, notify=tvfDecayChanged)
    def tvfDecay(self) -> int:
        return self._active_tone().tvf_decay

    @pyqtProperty(int, notify=tvfSustainChanged)
    def tvfSustain(self) -> int:
        return self._active_tone().tvf_sustain

    @pyqtProperty(int, notify=tvfReleaseChanged)
    def tvfRelease(self) -> int:
        return self._active_tone().tvf_release

    @pyqtProperty(str, notify=tvfTypeChanged)
    def tvfType(self) -> str:
        return self._active_tone().tvf_type_str

    @pyqtProperty(int, notify=tvfKeyFollowChanged)
    def tvfKeyFollow(self) -> int:
        return self._active_tone().tvf_keyfollow_percent

    @pyqtProperty(int, notify=tvfVeloSensChanged)
    def tvfVeloSens(self) -> int:
        return self._active_tone().tvf_env_velo_sens

    @pyqtProperty(int, notify=tvaLevelChanged)
    def tvaLevel(self) -> int:
        return self._active_tone().level

    @pyqtProperty(int, notify=tvaAttackChanged)
    def tvaAttack(self) -> int:
        return self._active_tone().tva_attack

    @pyqtProperty(int, notify=tvaDecayChanged)
    def tvaDecay(self) -> int:
        return self._active_tone().tva_decay

    @pyqtProperty(int, notify=tvaSustainChanged)
    def tvaSustain(self) -> int:
        return self._active_tone().tva_sustain

    @pyqtProperty(int, notify=tvaReleaseChanged)
    def tvaRelease(self) -> int:
        return self._active_tone().tva_release

    @pyqtProperty(int, notify=tvaPanChanged)
    def tvaPan(self) -> int:
        return self._active_tone().pan_bipolar

    @pyqtProperty(int, notify=tvaVeloSensChanged)
    def tvaVeloSens(self) -> int:
        return self._active_tone().tva_velo_sens

    @pyqtProperty(int, notify=pitchCoarseChanged)
    def pitchCoarse(self) -> int:
        return self._active_tone().coarse_st

    @pyqtProperty(int, notify=pitchFineChanged)
    def pitchFine(self) -> int:
        return self._active_tone().fine_cents

    @pyqtProperty(int, notify=portamentoTimeChanged)
    def portamentoTime(self) -> int:
        return self.patch_state.common.portamento_time

    @pyqtProperty(bool, notify=portamentoSwitchChanged)
    def portamentoSwitch(self) -> bool:
        return self.patch_state.common.portamento_switch

    @pyqtProperty(bool, notify=legatoSwitchChanged)
    def legatoSwitch(self) -> bool:
        return self.patch_state.common.legato_switch

    # -------------------------------------------------------------------------
    # Properties for QML: LFO 1 & 2
    # -------------------------------------------------------------------------

    @pyqtProperty(int, notify=lfoParamsChanged)
    def lfo1Rate(self) -> int:
        return self._active_tone().lfo1_rate

    @pyqtProperty(str, notify=lfoParamsChanged)
    def lfo1Wave(self) -> str:
        return self._active_tone().lfo1_wave_str

    @pyqtProperty(int, notify=lfoParamsChanged)
    def lfo1PitchDepth(self) -> int:
        return self._active_tone().lfo1_pitch_depth - 64

    @pyqtProperty(int, notify=lfoParamsChanged)
    def lfo1TvfDepth(self) -> int:
        return self._active_tone().lfo1_tvf_depth - 64

    @pyqtProperty(int, notify=lfoParamsChanged)
    def lfo1TvaDepth(self) -> int:
        return self._active_tone().lfo1_tva_depth - 64

    @pyqtProperty(int, notify=lfoParamsChanged)
    def lfo1PanDepth(self) -> int:
        return self._active_tone().lfo1_pan_depth - 64

    @pyqtProperty(int, notify=lfoParamsChanged)
    def lfo1DelayTime(self) -> int:
        return self._active_tone().lfo1_delay_time

    @pyqtProperty(str, notify=lfoParamsChanged)
    def lfo1FadeMode(self) -> str:
        return self._active_tone().lfo1_fade_mode_str

    @pyqtProperty(int, notify=lfoParamsChanged)
    def lfo1FadeTime(self) -> int:
        return self._active_tone().lfo1_fade_time

    @pyqtProperty(bool, notify=lfoParamsChanged)
    def lfo1Sync(self) -> bool:
        return False

    @pyqtProperty(int, notify=lfoParamsChanged)
    def lfo2Rate(self) -> int:
        return self._active_tone().lfo2_rate

    @pyqtProperty(str, notify=lfoParamsChanged)
    def lfo2Wave(self) -> str:
        return self._active_tone().lfo2_wave_str

    @pyqtProperty(int, notify=lfoParamsChanged)
    def lfo2PitchDepth(self) -> int:
        return self._active_tone().lfo2_pitch_depth - 64

    @pyqtProperty(int, notify=lfoParamsChanged)
    def lfo2TvfDepth(self) -> int:
        return self._active_tone().lfo2_tvf_depth - 64

    @pyqtProperty(int, notify=lfoParamsChanged)
    def lfo2TvaDepth(self) -> int:
        return self._active_tone().lfo2_tva_depth - 64

    @pyqtProperty(int, notify=lfoParamsChanged)
    def lfo2PanDepth(self) -> int:
        return self._active_tone().lfo2_pan_depth - 64

    @pyqtProperty(int, notify=lfoParamsChanged)
    def lfo2DelayTime(self) -> int:
        return self._active_tone().lfo2_delay_time

    @pyqtProperty(str, notify=lfoParamsChanged)
    def lfo2FadeMode(self) -> str:
        return self._active_tone().lfo2_fade_mode_str

    @pyqtProperty(int, notify=lfoParamsChanged)
    def lfo2FadeTime(self) -> int:
        return self._active_tone().lfo2_fade_time

    @pyqtProperty(bool, notify=lfoParamsChanged)
    def lfo2Sync(self) -> bool:
        return False

    # -------------------------------------------------------------------------
    # Properties for QML: Pitch Envelope
    # -------------------------------------------------------------------------

    @pyqtProperty(int, notify=pitchEnvChanged)
    def pitchEnvDepth(self) -> int:
        return self._active_tone().pitch_env_depth_st

    @pyqtProperty(int, notify=pitchEnvChanged)
    def pitchEnvVelSens(self) -> int:
        return self._active_tone().pitch_env_vel_sens_bipolar

    @pyqtProperty(int, notify=pitchEnvChanged)
    def pitchEnvTimeKeyfollow(self) -> int:
        return self._active_tone().pitch_env_time_kf_bipolar

    @pyqtProperty(int, notify=pitchEnvChanged)
    def pitchEnvT1VelSens(self) -> int:
        return self._active_tone().pitch_env_t1_vel_sens_bipolar

    @pyqtProperty(int, notify=pitchEnvChanged)
    def pitchEnvT4VelSens(self) -> int:
        return self._active_tone().pitch_env_t4_vel_sens_bipolar

    @pyqtProperty(int, notify=pitchEnvChanged)
    def pitchEnvT1(self) -> int:
        return self._active_tone().pitch_env_t1

    @pyqtProperty(int, notify=pitchEnvChanged)
    def pitchEnvT2(self) -> int:
        return self._active_tone().pitch_env_t2

    @pyqtProperty(int, notify=pitchEnvChanged)
    def pitchEnvT3(self) -> int:
        return self._active_tone().pitch_env_t3

    @pyqtProperty(int, notify=pitchEnvChanged)
    def pitchEnvT4(self) -> int:
        return self._active_tone().pitch_env_t4

    @pyqtProperty(int, notify=pitchEnvChanged)
    def pitchEnvL0(self) -> int:
        return self._active_tone().pitch_env_l0_bipolar

    @pyqtProperty(int, notify=pitchEnvChanged)
    def pitchEnvL1(self) -> int:
        return self._active_tone().pitch_env_l1_bipolar

    @pyqtProperty(int, notify=pitchEnvChanged)
    def pitchEnvL2(self) -> int:
        return self._active_tone().pitch_env_l2_bipolar

    @pyqtProperty(int, notify=pitchEnvChanged)
    def pitchEnvL3(self) -> int:
        return self._active_tone().pitch_env_l3_bipolar

    @pyqtProperty(int, notify=pitchEnvChanged)
    def pitchEnvL4(self) -> int:
        return self._active_tone().pitch_env_l4_bipolar

    # -------------------------------------------------------------------------
    # Properties for QML: Master Effects & EQ
    # -------------------------------------------------------------------------

    @pyqtProperty(int, notify=chorusParamsChanged)
    def chorusType(self) -> int:
        return self.patch_state.effects.chorus_type

    @pyqtProperty(int, notify=chorusParamsChanged)
    def chorusLevel(self) -> int:
        return self.patch_state.effects.chorus_level

    @pyqtProperty(int, notify=chorusParamsChanged)
    def chorusToReverb(self) -> int:
        return self.patch_state.effects.chorus_to_reverb

    @pyqtProperty(int, notify=chorusParamsChanged)
    def chorusRate(self) -> int:
        return self.patch_state.effects.chorus_rate

    @pyqtProperty(int, notify=chorusParamsChanged)
    def chorusDepth(self) -> int:
        return self.patch_state.effects.chorus_depth

    @pyqtProperty(int, notify=chorusParamsChanged)
    def chorusPreDelay(self) -> int:
        return self.patch_state.effects.chorus_predelay

    @pyqtProperty(int, notify=chorusParamsChanged)
    def chorusFeedback(self) -> int:
        return self.patch_state.effects.chorus_feedback

    @pyqtProperty(int, notify=reverbParamsChanged)
    def reverbType(self) -> int:
        return self.patch_state.effects.reverb_type

    @pyqtProperty(int, notify=reverbParamsChanged)
    def reverbLevel(self) -> int:
        return self.patch_state.effects.reverb_level

    @pyqtProperty(int, notify=reverbParamsChanged)
    def reverbTime(self) -> int:
        return self.patch_state.effects.reverb_time

    @pyqtProperty(int, notify=reverbParamsChanged)
    def reverbDamp(self) -> int:
        return self.patch_state.effects.reverb_damp

    @pyqtProperty(int, notify=reverbParamsChanged)
    def reverbPreDelay(self) -> int:
        return self.patch_state.effects.reverb_predelay

    @pyqtProperty(int, notify=reverbParamsChanged)
    def reverbDiffusion(self) -> int:
        return self.patch_state.effects.reverb_diffusion

    @pyqtProperty(int, notify=reverbParamsChanged)
    def reverbTone(self) -> int:
        return self.patch_state.effects.reverb_tone

    @pyqtProperty(bool, notify=masterEqChanged)
    def eqSwitch(self) -> bool:
        return getattr(self.patch_state.effects, "eq_switch", True)

    @pyqtProperty(int, notify=masterEqChanged)
    def eqLowGain(self) -> int:
        return self.patch_state.effects.eq_low_gain

    @pyqtProperty(int, notify=masterEqChanged)
    def eqLowFreq(self) -> int:
        return self.patch_state.effects.eq_low_freq

    @pyqtProperty(int, notify=masterEqChanged)
    def eqMidGain(self) -> int:
        return self.patch_state.effects.eq_mid_gain

    @pyqtProperty(int, notify=masterEqChanged)
    def eqMidFreq(self) -> int:
        return self.patch_state.effects.eq_mid_freq

    @pyqtProperty(float, notify=masterEqChanged)
    def eqMidQ(self) -> float:
        return self.patch_state.effects.eq_mid_q

    @pyqtProperty(int, notify=masterEqChanged)
    def eqHighGain(self) -> int:
        return self.patch_state.effects.eq_high_gain

    @pyqtProperty(int, notify=masterEqChanged)
    def eqHighFreq(self) -> int:
        return self.patch_state.effects.eq_high_freq

    @pyqtProperty(int, notify=masterEqChanged)
    def eqMasterLevel(self) -> int:
        return self.patch_state.effects.eq_master_level

    # -------------------------------------------------------------------------
    # Properties for QML: MFX Studio
    # -------------------------------------------------------------------------

    @pyqtProperty("QVariantList", constant=True)
    def mfxCatalog(self) -> list:
        """Lightweight catalog (id, name, cat only); params are fetched per-algo."""
        return get_mfx_light_catalog("ALL")

    @pyqtProperty("QVariantList", constant=True)
    def mfxCategories(self) -> list:
        return get_mfx_categories()

    @pyqtSlot(str, str, result="QVariantList")
    def filterMfxAlgos(self, category: str, query: str) -> list:
        """Fast precomputed filtering: 0ms for category switch, simple string check for search."""
        q = (query or "").strip().lower()
        base_list = get_mfx_light_catalog(category)
        if not q:
            return base_list
        return [
            a for a in base_list
            if q in a["name"].lower() or q in a["cat"].lower() or q in str(a["id"])
        ]

    @pyqtSlot(int, result="QVariant")
    def getMfxAlgoInfo(self, algo_id: int):
        """Full info (including params) for a single algorithm."""
        return get_mfx_algo(int(algo_id)) or {}

    @pyqtProperty("QVariantList", notify=mfxValuesChanged)
    def mfxParamValues(self) -> list:
        return list(self.patch_state.effects.mfx_params)

    @pyqtProperty(int, notify=mfxParamsChanged)
    def mfxAlgoId(self) -> int:
        eff = self.patch_state.effects
        return eff.mfx_type if not eff.mfx_bypassed else eff.mfx_last_active_type

    @pyqtProperty(bool, notify=mfxParamsChanged)
    def mfxBypassed(self) -> bool:
        return self.patch_state.effects.mfx_bypassed

    @pyqtProperty(int, notify=mfxParamsChanged)
    def mfxDrySend(self) -> int:
        return self.patch_state.effects.mfx_dry_send

    @pyqtProperty(int, notify=mfxParamsChanged)
    def mfxChorusSend(self) -> int:
        return self.patch_state.effects.mfx_chorus_send

    @pyqtProperty(int, notify=mfxParamsChanged)
    def mfxReverbSend(self) -> int:
        return self.patch_state.effects.mfx_reverb_send

    # -------------------------------------------------------------------------
    # Properties for QML: Routing View
    # -------------------------------------------------------------------------

    @pyqtProperty(str, notify=routingChanged)
    def routingPreset(self) -> str:
        return self.patch_state.effects.routing_preset

    @pyqtProperty(bool, notify=routingChanged)
    def manualRoutingUnlocked(self) -> bool:
        return self.patch_state.effects.manual_routing_unlocked

    @pyqtProperty("QVariantList", notify=routingChanged)
    def toneOutputAssigns(self) -> list:
        return [t.output_assign for t in self.patch_state.tones]

    @pyqtProperty("QVariantList", notify=routingChanged)
    def toneOutputLevels(self) -> list:
        return [t.output_level for t in self.patch_state.tones]

    @pyqtProperty("QVariantList", notify=routingChanged)
    def toneChorusSends(self) -> list:
        return [t.chorus_send for t in self.patch_state.tones]

    @pyqtProperty("QVariantList", notify=routingChanged)
    def toneReverbSends(self) -> list:
        return [t.reverb_send for t in self.patch_state.tones]

    @pyqtProperty("QVariantList", notify=routingChanged)
    def routingPitfalls(self) -> list:
        return self.detectRoutingPitfalls()

    @pyqtProperty(str, notify=mfxParamsChanged)
    def mfxAlgoName(self) -> str:
        eff = self.patch_state.effects
        if eff.mfx_bypassed or eff.mfx_type == 0:
            return "BYPASS / OFF"
        algo = get_mfx_algo(eff.mfx_type)
        return algo.get("name", f"MFX #{eff.mfx_type}") if algo else f"MFX #{eff.mfx_type}"

    @pyqtProperty(str, notify=chorusParamsChanged)
    def chorusTypeName(self) -> str:
        names = ["OFF", "CHORUS", "DELAY", "GM2 CHORUS"]
        idx = self.patch_state.effects.chorus_type
        return names[idx] if 0 <= idx < len(names) else "OFF"

    @pyqtProperty(str, notify=reverbParamsChanged)
    def reverbTypeName(self) -> str:
        names = ["OFF", "REVERB", "ROOM", "HALL", "PLATE", "GM2"]
        idx = self.patch_state.effects.reverb_type
        return names[idx] if 0 <= idx < len(names) else "OFF"

    # -------------------------------------------------------------------------
    # Properties for QML: Mod Matrix (1..4)
    # -------------------------------------------------------------------------

    def _build_matrix_ctrl_dict(self, ctrl_idx: int) -> dict:
        """Helper to build dict representation of a matrix controller including tone switches."""
        c = self.patch_state.common.matrix_ctrls[ctrl_idx]
        sw1 = [self.patch_state.tones[t].matrix_switches[ctrl_idx][0] for t in range(4)]
        sw2 = [self.patch_state.tones[t].matrix_switches[ctrl_idx][1] for t in range(4)]
        sw3 = [self.patch_state.tones[t].matrix_switches[ctrl_idx][2] for t in range(4)]
        sw4 = [self.patch_state.tones[t].matrix_switches[ctrl_idx][3] for t in range(4)]
        return {
            "source": c.source,
            "dest1": c.dest1, "sens1": c.sens1 - 64, "dest1_sw": sw1,
            "dest2": c.dest2, "sens2": c.sens2 - 64, "dest2_sw": sw2,
            "dest3": c.dest3, "sens3": c.sens3 - 64, "dest3_sw": sw3,
            "dest4": c.dest4, "sens4": c.sens4 - 64, "dest4_sw": sw4,
            "dest_sw": [sw1, sw2, sw3, sw4],
        }

    @pyqtProperty("QVariantMap", notify=matrixCtrlChanged)
    def matrixCtrl1(self) -> dict:
        return self._build_matrix_ctrl_dict(0)

    @pyqtProperty("QVariantMap", notify=matrixCtrlChanged)
    def matrixCtrl2(self) -> dict:
        return self._build_matrix_ctrl_dict(1)

    @pyqtProperty("QVariantMap", notify=matrixCtrlChanged)
    def matrixCtrl3(self) -> dict:
        return self._build_matrix_ctrl_dict(2)

    @pyqtProperty("QVariantMap", notify=matrixCtrlChanged)
    def matrixCtrl4(self) -> dict:
        return self._build_matrix_ctrl_dict(3)

    # -------------------------------------------------------------------------
    # Properties for QML: Step LFO, VA Engine, Perf Mixer, Macros
    # -------------------------------------------------------------------------

    @pyqtProperty("QVariantList", notify=stepLfoChanged)
    def stepLfoSteps(self) -> list:
        return self._active_tone().step_lfo_steps

    @pyqtProperty(int, notify=stepLfoChanged)
    def stepLfoCurve(self) -> int:
        return self._active_tone().step_lfo_type

    @pyqtProperty(int, notify=stepLfoChanged)
    def stepLfoRateIdx(self) -> int:
        return self.patch_state.step_lfo.sync_rate_idx

    @pyqtProperty(int, notify=stepLfoChanged)
    def stepLfoDestIdx(self) -> int:
        return self.patch_state.step_lfo.dest_idx

    @pyqtProperty(int, notify=stepLfoChanged)
    def stepLfoDepth(self) -> int:
        return self.patch_state.step_lfo.depth

    @pyqtProperty(bool, notify=vaParamsChanged)
    def autoDetune(self) -> bool:
        return self.patch_state.auto_detune

    @pyqtProperty(int, notify=vaParamsChanged)
    def autoDetuneCents(self) -> int:
        return self.patch_state.auto_detune_cents

    @pyqtProperty(int, notify=vaParamsChanged)
    def vaOsc1Coarse(self) -> int:
        return self.patch_state.tones[0].coarse_st

    @pyqtProperty(int, notify=vaParamsChanged)
    def vaOsc2Coarse(self) -> int:
        return self.patch_state.tones[1].coarse_st

    @pyqtProperty(int, notify=vaParamsChanged)
    def vaOsc3Coarse(self) -> int:
        return self.patch_state.tones[2].coarse_st

    @pyqtProperty(int, notify=vaParamsChanged)
    def vaOsc4Coarse(self) -> int:
        return self.patch_state.tones[3].coarse_st

    @pyqtProperty(int, notify=vaParamsChanged)
    def vaOsc1Fine(self) -> int:
        return self.patch_state.tones[0].fine_cents

    @pyqtProperty(int, notify=vaParamsChanged)
    def vaOsc2Fine(self) -> int:
        return self.patch_state.tones[1].fine_cents

    @pyqtProperty(int, notify=vaParamsChanged)
    def vaOsc3Fine(self) -> int:
        return self.patch_state.tones[2].fine_cents

    @pyqtProperty(int, notify=vaParamsChanged)
    def vaOsc4Fine(self) -> int:
        return self.patch_state.tones[3].fine_cents

    @pyqtProperty(int, notify=vaParamsChanged)
    def vaOsc1Pw(self) -> int:
        return self.patch_state.va_pw[0]

    @pyqtProperty(int, notify=vaParamsChanged)
    def vaOsc2Pw(self) -> int:
        return self.patch_state.va_pw[1]

    @pyqtProperty(int, notify=vaParamsChanged)
    def vaOsc3Pw(self) -> int:
        return self.patch_state.va_pw[2]

    @pyqtProperty(int, notify=vaParamsChanged)
    def vaOsc4Pw(self) -> int:
        return self.patch_state.va_pw[3]

    @pyqtProperty(int, notify=vaParamsChanged)
    def vaOsc1Pwm(self) -> int:
        return self.patch_state.va_pwm[0]

    @pyqtProperty(int, notify=vaParamsChanged)
    def vaOsc2Pwm(self) -> int:
        return self.patch_state.va_pwm[1]

    @pyqtProperty(int, notify=vaParamsChanged)
    def vaOsc3Pwm(self) -> int:
        return self.patch_state.va_pwm[2]

    @pyqtProperty(int, notify=vaParamsChanged)
    def vaOsc4Pwm(self) -> int:
        return self.patch_state.va_pwm[3]

    @pyqtProperty(int, notify=vaParamsChanged)
    def vaOsc1Wave(self) -> int:
        w = self.patch_state.tones[0].wave_num_l
        return 0 if w == 579 else (1 if w in (600, 612, 613, 614, 615, 616, 617, 1326, 1327, 1328, 1329) else (2 if w in (621, 622) else (3 if w in (625, 1322) else 4)))

    @pyqtProperty(int, notify=vaParamsChanged)
    def vaOsc2Wave(self) -> int:
        w = self.patch_state.tones[1].wave_num_l
        return 0 if w == 579 else (1 if w in (600, 612, 613, 614, 615, 616, 617, 1326, 1327, 1328, 1329) else (2 if w in (621, 622) else (3 if w in (625, 1322) else 4)))

    @pyqtProperty(int, notify=vaParamsChanged)
    def vaOsc3Wave(self) -> int:
        w = self.patch_state.tones[2].wave_num_l
        return 0 if w == 579 else (1 if w in (600, 612, 613, 614, 615, 616, 617, 1326, 1327, 1328, 1329) else (2 if w in (621, 622) else (3 if w in (625, 1322) else 4)))

    @pyqtProperty(int, notify=vaParamsChanged)
    def vaOsc4Wave(self) -> int:
        w = self.patch_state.tones[3].wave_num_l
        return 0 if w == 579 else (1 if w in (600, 612, 613, 614, 615, 616, 617, 1326, 1327, 1328, 1329) else (2 if w in (621, 622) else (3 if w in (625, 1322) else 4)))


    @pyqtProperty("QVariantList", notify=perfPartsChanged)
    def perfParts(self) -> list:
        return [
            {
                "index": p.part_index,
                "name": p.name,
                "volume": p.volume,
                "pan": p.pan,
                "muted": p.muted,
                "solo": p.solo,
            }
            for p in self.patch_state.perf_parts[:8]
        ]

    # Macro deck values are READ-ONLY reflections of the underlying synth parameters.
    # setMacro() writes the parameters themselves; these getters always mirror truth.
    @pyqtProperty(int, notify=macrosChanged)
    def macro1(self) -> int:
        return self.patch_state.common.cutoff_offset

    @pyqtProperty(int, notify=macrosChanged)
    def macro2(self) -> int:
        return self.patch_state.common.resonance_offset

    @pyqtProperty(int, notify=macrosChanged)
    def macro3(self) -> int:
        return self.patch_state.common.attack_offset

    @pyqtProperty(int, notify=macrosChanged)
    def macro4(self) -> int:
        return self.patch_state.common.release_offset

    @pyqtProperty(int, notify=macrosChanged)
    def macro5(self) -> int:
        return self.patch_state.common.portamento_time

    @pyqtProperty(int, notify=macrosChanged)
    def macro6(self) -> int:
        return self.patch_state.common.analog_feel

    @pyqtProperty(int, notify=macrosChanged)
    def macro7(self) -> int:
        return self.patch_state.effects.chorus_level

    @pyqtProperty(int, notify=macrosChanged)
    def macro8(self) -> int:
        return self.patch_state.effects.reverb_level

    @pyqtProperty(int, notify=analogFeelChanged)
    def analogFeel(self) -> int:
        return self.patch_state.common.analog_feel

    # -------------------------------------------------------------------------
    # Invokable Slots from QML: Transport, Shell, Tone Selection
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

    @pyqtSlot(result="QVariantList")
    def getMotionPath(self) -> list:
        """Return recorded trajectory points as [x, y] normalized pairs."""
        return [[pt.x, pt.y] for pt in self.engine.motion.points]

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

    @pyqtSlot(bool)
    def setAutoTrim(self, enabled: bool) -> None:
        """Toggle automatic trimming of idle lead-in and tail-off samples."""
        self.engine.motion.auto_trim = bool(enabled)
        self.autoTrimChanged.emit(self.engine.motion.auto_trim)

    @pyqtSlot(bool)
    def setAutoClose(self, enabled: bool) -> None:
        """Toggle automatic closure of the loop back to the start point."""
        self.engine.motion.auto_close = bool(enabled)
        self.autoCloseChanged.emit(self.engine.motion.auto_close)

    @pyqtSlot(bool)
    def setSmoothing(self, enabled: bool) -> None:
        """Toggle low-pass smoothing of the trajectory on stop."""
        self.engine.motion.smoothing = bool(enabled)
        self.smoothingChanged.emit(self.engine.motion.smoothing)

    @pyqtSlot(float)
    def setBpm(self, bpm_val: float) -> None:
        """Update tempo BPM."""
        self.engine.motion.bpm = max(20.0, min(300.0, bpm_val))
        self.bpmChanged.emit(self.engine.motion.bpm)

    @pyqtSlot()
    def panic(self) -> None:
        """Send All Notes Off / Reset all controllers."""
        try:
            if self.engine.juno and self.engine.juno.midi:
                self.engine.juno.midi.send_all_notes_off()
            else:
                logger.warning("PANIC ignored: synth not connected (mock/no MIDI).")
        except Exception as e:
            logger.warning(f"PANIC failed: {e}")
            return
        logger.info("PANIC: Sent All Notes Off")

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
        elif v in ("PITCH-ENV", "PITCHENV", "PITCH ENV", "MSEG ENVELOPE", "ENVELOPE EDITOR", "ENV EDITOR"):
            v = "MSEG ENVELOPES"
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
            self._update_telemetry_polling()

    @pyqtSlot(int)
    def setSelectedTone(self, tone_number: int) -> None:
        """Select active tone (1..4) and refresh all tone-specific properties."""
        clamped = max(1, min(4, int(tone_number)))
        if self._selected_tone != clamped:
            self._selected_tone = clamped
            self.selectedToneChanged.emit(self._selected_tone)
            # Emit tone property changes so views bind to this tone's parameters
            self.pitchCoarseChanged.emit(self.pitchCoarse)
            self.pitchFineChanged.emit(self.pitchFine)
            self.tvfTypeChanged.emit(self.tvfType)
            self.masterCutoffChanged.emit(self.masterCutoff)
            self.masterResoChanged.emit(self.masterReso)
            self.tvfKeyFollowChanged.emit(self.tvfKeyFollow)
            self.tvfEnvDepthChanged.emit(self.tvfEnvDepth)
            self.tvfVeloSensChanged.emit(self.tvfVeloSens)
            self.tvfAttackChanged.emit(self.tvfAttack)
            self.tvfDecayChanged.emit(self.tvfDecay)
            self.tvfSustainChanged.emit(self.tvfSustain)
            self.tvfReleaseChanged.emit(self.tvfRelease)
            self.tvaLevelChanged.emit(self.tvaLevel)
            self.tvaPanChanged.emit(self.tvaPan)
            self.tvaVeloSensChanged.emit(self.tvaVeloSens)
            self.tvaAttackChanged.emit(self.tvaAttack)
            self.tvaDecayChanged.emit(self.tvaDecay)
            self.tvaSustainChanged.emit(self.tvaSustain)
            self.tvaReleaseChanged.emit(self.tvaRelease)
            self.masterAttackChanged.emit(self.masterAttack)
            self.masterReleaseChanged.emit(self.masterRelease)
            self.lfoParamsChanged.emit()
            self.pitchEnvChanged.emit()
            self.envShapeChanged.emit("TVF")
            self.envShapeChanged.emit("TVA")
            self.envShapeChanged.emit("PITCH")
            self.stepLfoChanged.emit()

    @pyqtSlot(bool)
    def setLinkedMode(self, linked: bool) -> None:
        """Toggle linked mode across all 4 tones."""
        if self._linked_mode != linked:
            self._linked_mode = linked
            self.linkedModeChanged.emit(self._linked_mode)

    @pyqtSlot(int)
    def toggleToneMute(self, tone_number: int) -> None:
        """Toggle mute state for tone 1..4 (disables/enables wave playback)."""
        idx = max(1, min(4, tone_number)) - 1
        new_muted = not self.patch_state.tones[idx].muted
        self.setToneMute(tone_number, new_muted)

    @pyqtSlot(int, bool)
    def setToneMute(self, tone_number: int, muted: bool) -> None:
        """Set mute state for tone 1..4."""
        idx = max(1, min(4, tone_number)) - 1
        self.patch_state.tones[idx].muted = muted
        self.engine.set_tone_mute(tone_number, muted)
        target_level = 0 if muted else self.patch_state.tones[idx].level
        if self.engine.juno:
            try:
                self.engine.juno.set_tone_switch(tone_number, not muted)
                self.engine.juno.set_tone_level(tone_number, target_level)
            except Exception as e:
                logger.error(f"Error setting tone mute on synth: {e}")
        self.toneMutesChanged.emit()
        self.toneLevelsChanged.emit(*self.engine.tone_levels)
        if tone_number == self._selected_tone:
            self.tvaLevelChanged.emit(self.tvaLevel)

    @pyqtSlot(int, int)
    def setToneLevel(self, tone_number: int, level: int) -> None:
        """Directly adjust level of a single tone (1..4)."""
        idx = max(1, min(4, tone_number)) - 1
        clamped = max(0, min(127, int(level)))
        self.patch_state.tones[idx].level = clamped
        if not self.patch_state.tones[idx].muted:
            self.engine.set_tone_level(tone_number, clamped)
            if self.engine.juno:
                try:
                    self.engine.juno.set_tone_level(tone_number, clamped)
                except Exception as e:
                    logger.error(f"Error setting tone level on synth: {e}")
        self.toneLevelsChanged.emit(*[t.level for t in self.patch_state.tones])
        if tone_number == self._selected_tone:
            self.tvaLevelChanged.emit(clamped)

    @pyqtSlot(int)
    def setTvaLevel(self, val: int) -> None:
        """Set active tone TVA Level (0..127). Ganged across all 4 tones if linked."""
        clamped = max(0, min(127, int(val)))
        targets = self._target_tones()
        for t in targets:
            t.level = clamped
            if not t.muted:
                self.engine.set_tone_level(t.tone_index, clamped)
                if self.engine.juno:
                    try:
                        self.engine.juno.set_tone_level(t.tone_index, clamped)
                    except Exception as e:
                        logger.error(f"Error setting tone level on synth: {e}")
        self.tvaLevelChanged.emit(self._active_tone().level)
        self.toneLevelsChanged.emit(*[t.level for t in self.patch_state.tones])

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
        """Drive the underlying synth parameter for macro knob 1..8 (0..127).

        Macro values are never stored: the macro1..8 properties read the parameters
        back, keeping the deck honest as the single reflection layer.
        """
        if not (1 <= index <= 8):
            return
        clamped = max(0, min(127, int(value)))

        juno = self.engine.juno
        try:
            if index == 1:
                offset_val = max(1, min(127, clamped))
                self.patch_state.common.cutoff_offset = offset_val
                self._active_tone().tvf_cutoff = offset_val
                self.masterCutoffChanged.emit(offset_val)
                if juno:
                    juno.set_patch_offsets(cutoff=offset_val)
            elif index == 2:
                offset_val = max(1, min(127, clamped))
                self.patch_state.common.resonance_offset = offset_val
                self._active_tone().tvf_resonance = offset_val
                self.masterResoChanged.emit(offset_val)
                if juno:
                    juno.set_patch_offsets(resonance=offset_val)
            elif index == 3:
                offset_val = max(1, min(127, clamped))
                self.patch_state.common.attack_offset = offset_val
                self._active_tone().tva_attack = offset_val
                self.masterAttackChanged.emit(offset_val)
                self.envShapeChanged.emit("TVA")
                if juno:
                    juno.set_patch_offsets(attack=offset_val)
            elif index == 4:
                offset_val = max(1, min(127, clamped))
                self.patch_state.common.release_offset = offset_val
                self._active_tone().tva_release = offset_val
                self.masterReleaseChanged.emit(offset_val)
                self.envShapeChanged.emit("TVA")
                if juno:
                    juno.set_patch_offsets(release=offset_val)
            elif index == 5:
                self.patch_state.common.portamento_time = clamped
                self.portamentoTimeChanged.emit(clamped)
                if juno:
                    juno.set_portamento(self.patch_state.common.portamento_switch, time=clamped)
            elif index == 6:
                self.patch_state.common.analog_feel = clamped
                self.analogFeelChanged.emit(clamped)
                if juno:
                    juno.set_patch_analog_feel(clamped)
            elif index == 7:
                self.patch_state.effects.chorus_level = clamped
                self.chorusParamsChanged.emit()
                if juno:
                    juno.set_chorus(self.patch_state.effects.chorus_type, level=clamped)
            elif index == 8:
                self.patch_state.effects.reverb_level = clamped
                self.reverbParamsChanged.emit()
                if juno:
                    juno.set_reverb(self.patch_state.effects.reverb_type, level=clamped)
        except Exception as e:
            logger.error(f"Error dispatching macro {index} to synth: {e}")
        finally:
            self.macrosChanged.emit()

    # -------------------------------------------------------------------------
    # Invokable Slots from QML: Tone TVF, TVA, Pitch, Portamento
    # -------------------------------------------------------------------------

    @pyqtSlot(int)
    def setMasterCutoff(self, val: int) -> None:
        """Set TVF Cutoff (0..127). Ganged across all 4 tones if linked."""
        clamped = max(0, min(127, int(val)))
        targets = self._target_tones()
        for t in targets:
            t.tvf_cutoff = clamped
            if self.engine.juno:
                try:
                    self.engine.juno.set_tone_tvf(t.tone_index, cutoff=clamped)
                except Exception as e:
                    logger.error(f"Error setting cutoff on synth: {e}")
        self.masterCutoffChanged.emit(clamped)

    @pyqtSlot(int)
    def setMasterReso(self, val: int) -> None:
        """Set TVF Resonance (0..127). Ganged across all 4 tones if linked."""
        clamped = max(0, min(127, int(val)))
        targets = self._target_tones()
        for t in targets:
            t.tvf_resonance = clamped
            if self.engine.juno:
                try:
                    self.engine.juno.set_tone_tvf(t.tone_index, resonance=clamped)
                except Exception as e:
                    logger.error(f"Error setting resonance on synth: {e}")
        self.masterResoChanged.emit(clamped)

    @pyqtSlot(int)
    def setMasterLevel(self, val: int) -> None:
        """Set Master Patch Level (0..127)."""
        clamped = max(0, min(127, int(val)))
        if self.patch_state.common.level != clamped:
            self.patch_state.common.level = clamped
            self.masterLevelChanged.emit(clamped)
            if self.engine.juno:
                try:
                    self.engine.juno.set_patch_param("level", clamped)
                except Exception as e:
                    logger.error(f"Error setting patch level: {e}")

    @pyqtSlot(str)
    def setTvfType(self, type_str: str) -> None:
        """Set TVF filter type (OFF, LPF, BPF, HPF, PKG, LPF2, LPF3)."""
        val_idx = 1
        if type_str in TVF_TYPE_NAMES:
            val_idx = TVF_TYPE_NAMES.index(type_str)
        targets = self._target_tones()
        for t in targets:
            t.tvf_filter_type = val_idx
            if self.engine.juno:
                try:
                    self.engine.juno.set_tone_tvf(t.tone_index, filter_type=val_idx)
                except Exception as e:
                    logger.error(f"Error setting TVF filter type on synth: {e}")
        self.tvfTypeChanged.emit(type_str)

    @pyqtSlot(int)
    def setTvfKeyFollow(self, val: int) -> None:
        """Set TVF Cutoff Keyfollow (-100..+100%)."""
        clamped = max(-100, min(100, int(val)))
        raw_val = 64 + (clamped // 10)
        targets = self._target_tones()
        for t in targets:
            t.tvf_cutoff_keyfollow = raw_val
            if self.engine.juno:
                try:
                    self.engine.juno.set_tone_param(t.tone_index, 0x004A, raw_val)
                except Exception as e:
                    logger.error(f"Error setting TVF keyfollow on synth: {e}")
        self.tvfKeyFollowChanged.emit(clamped)

    @pyqtSlot(int)
    def setTvfEnvDepth(self, depth: int) -> None:
        """Set TVF envelope depth (-63..+63)."""
        clamped = max(-63, min(63, int(depth)))
        raw_val = 64 + clamped
        targets = self._target_tones()
        for t in targets:
            t.tvf_env_depth = raw_val
            if self.engine.juno:
                try:
                    self.engine.juno.set_tone_tvf(t.tone_index, env_depth=raw_val)
                except Exception as e:
                    logger.error(f"Error setting TVF env depth on synth: {e}")
        self.tvfEnvDepthChanged.emit(clamped)
        self.envShapeChanged.emit("TVF")

    @pyqtSlot(int)
    def setTvfVeloSens(self, val: int) -> None:
        """Set TVF velocity sensitivity (0..127)."""
        clamped = max(0, min(127, int(val)))
        targets = self._target_tones()
        for t in targets:
            t.tvf_env_velo_sens = clamped
            if self.engine.juno:
                try:
                    self.engine.juno.set_tone_tvf(t.tone_index, env_vel_sens=clamped)
                except Exception as e:
                    logger.error(f"Error setting TVF velo sens on synth: {e}")
        self.tvfVeloSensChanged.emit(clamped)
        self.envShapeChanged.emit("TVF")

    @pyqtSlot(int)
    def setTvfAttack(self, val: int) -> None:
        clamped = max(0, min(127, int(val)))
        targets = self._target_tones()
        for t in targets:
            t.tvf_attack = clamped
            self._push_tvf_env(t)
        self.tvfAttackChanged.emit(clamped)
        self.envShapeChanged.emit("TVF")

    @pyqtSlot(int)
    def setTvfDecay(self, val: int) -> None:
        clamped = max(0, min(127, int(val)))
        targets = self._target_tones()
        for t in targets:
            t.tvf_decay = clamped
            self._push_tvf_env(t)
        self.tvfDecayChanged.emit(clamped)
        self.envShapeChanged.emit("TVF")

    @pyqtSlot(int)
    def setTvfSustain(self, val: int) -> None:
        clamped = max(0, min(127, int(val)))
        targets = self._target_tones()
        for t in targets:
            t.tvf_sustain = clamped
            self._push_tvf_env(t)
        self.tvfSustainChanged.emit(clamped)
        self.envShapeChanged.emit("TVF")

    @pyqtSlot(int)
    def setTvfRelease(self, val: int) -> None:
        clamped = max(0, min(127, int(val)))
        targets = self._target_tones()
        for t in targets:
            t.tvf_release = clamped
            self._push_tvf_env(t)
        self.tvfReleaseChanged.emit(clamped)
        self.envShapeChanged.emit("TVF")

    @pyqtSlot(int)
    def setTvaAttack(self, val: int) -> None:
        """Set TVA Attack time (0..127). Ganged if linked."""
        clamped = max(0, min(127, int(val)))
        targets = self._target_tones()
        for t in targets:
            t.tva_attack = clamped
            self._push_tva_env(t)
        self.tvaAttackChanged.emit(clamped)
        self.masterAttackChanged.emit(clamped)
        self.envShapeChanged.emit("TVA")

    @pyqtSlot(int)
    def setMasterAttack(self, val: int) -> None:
        self.setTvaAttack(val)

    @pyqtSlot(int)
    def setTvaDecay(self, val: int) -> None:
        clamped = max(0, min(127, int(val)))
        targets = self._target_tones()
        for t in targets:
            t.tva_decay = clamped
            self._push_tva_env(t)
        self.tvaDecayChanged.emit(clamped)
        self.envShapeChanged.emit("TVA")

    @pyqtSlot(int)
    def setTvaSustain(self, val: int) -> None:
        clamped = max(0, min(127, int(val)))
        targets = self._target_tones()
        for t in targets:
            t.tva_sustain = clamped
            self._push_tva_env(t)
        self.tvaSustainChanged.emit(clamped)
        self.envShapeChanged.emit("TVA")

    @pyqtSlot(int)
    def setTvaRelease(self, val: int) -> None:
        """Set TVA Release time (0..127). Ganged if linked."""
        clamped = max(0, min(127, int(val)))
        targets = self._target_tones()
        for t in targets:
            t.tva_release = clamped
            self._push_tva_env(t)
        self.tvaReleaseChanged.emit(clamped)
        self.masterReleaseChanged.emit(clamped)
        self.envShapeChanged.emit("TVA")

    @pyqtSlot(int)
    def setMasterRelease(self, val: int) -> None:
        self.setTvaRelease(val)

    @pyqtSlot(int)
    def setTvaPan(self, val: int) -> None:
        """Set Tone TVA Pan (-64..+63, 0=Center)."""
        clamped = max(-64, min(63, int(val)))
        raw_val = clamped + 64
        targets = self._target_tones()
        for t in targets:
            t.pan = raw_val
            if self.engine.juno:
                try:
                    self.engine.juno.set_tone_tva(t.tone_index, pan=raw_val)
                except Exception as e:
                    logger.error(f"Error setting TVA pan on synth: {e}")
        self.tvaPanChanged.emit(clamped)

    @pyqtSlot(int)
    def setTvaVeloSens(self, val: int) -> None:
        """Set Tone TVA Velocity Sensitivity (0..127)."""
        clamped = max(0, min(127, int(val)))
        targets = self._target_tones()
        for t in targets:
            t.tva_velo_sens = clamped
            if self.engine.juno:
                try:
                    self.engine.juno.set_tone_param(t.tone_index, 0x0062, clamped)
                except Exception as e:
                    logger.error(f"Error setting TVA velo sens on synth: {e}")
        self.tvaVeloSensChanged.emit(clamped)
        self.envShapeChanged.emit("TVA")

    @pyqtSlot(int)
    def setPitchCoarse(self, val: int) -> None:
        """Set Tone Coarse Tune in semitones (-48..+48)."""
        clamped = max(-48, min(48, int(val)))
        raw_val = clamped + 64
        targets = self._target_tones()
        for t in targets:
            t.coarse_tune = raw_val
            if self.engine.juno:
                try:
                    self.engine.juno.set_tone_pitch(t.tone_index, coarse=raw_val)
                except Exception as e:
                    logger.error(f"Error setting coarse tune on synth: {e}")
        self.pitchCoarseChanged.emit(clamped)

    @pyqtSlot(int)
    def setPitchFine(self, val: int) -> None:
        """Set Tone Fine Tune in cents (-50..+50)."""
        clamped = max(-50, min(50, int(val)))
        raw_val = clamped + 64
        targets = self._target_tones()
        for t in targets:
            t.fine_tune = raw_val
            if not self.patch_state.auto_detune:
                self.patch_state.custom_detune_cache[t.tone_index - 1] = raw_val
            if self.engine.juno:
                try:
                    self.engine.juno.set_tone_pitch(t.tone_index, fine=raw_val)
                except Exception as e:
                    logger.error(f"Error setting fine tune on synth: {e}")
        self.pitchFineChanged.emit(clamped)
        self.vaParamsChanged.emit()

    @pyqtSlot(int)
    def setPortamentoTime(self, val: int) -> None:
        """Set Patch Portamento Time (0..127)."""
        clamped = max(0, min(127, int(val)))
        if self.patch_state.common.portamento_time != clamped:
            self.patch_state.common.portamento_time = clamped
            self.portamentoTimeChanged.emit(clamped)
            self.macrosChanged.emit()
            if self.engine.juno:
                try:
                    self.engine.juno.set_portamento(self.patch_state.common.portamento_switch, time=clamped)
                except Exception as e:
                    logger.error(f"Error setting portamento time on synth: {e}")

    @pyqtSlot(bool)
    def setPortamentoSwitch(self, enabled: bool) -> None:
        """Toggle Patch Portamento Switch."""
        if self.patch_state.common.portamento_switch != enabled:
            self.patch_state.common.portamento_switch = enabled
            self.portamentoSwitchChanged.emit(enabled)
            if self.engine.juno:
                try:
                    self.engine.juno.set_portamento(enabled)
                except Exception as e:
                    logger.error(f"Error setting portamento switch on synth: {e}")

    @pyqtSlot(bool)
    def setLegatoSwitch(self, enabled: bool) -> None:
        """Toggle Patch Legato Switch (sets Mono/Poly to MONO when ON)."""
        if self.patch_state.common.legato_switch != enabled:
            self.patch_state.common.legato_switch = enabled
            self.patch_state.common.mono_poly = 0 if enabled else 1
            self.patch_state.common.portamento_mode = 1 if enabled else 0
            self.legatoSwitchChanged.emit(enabled)
            if self.engine.juno:
                try:
                    self.engine.juno.set_legato(enabled)
                except Exception as e:
                    logger.error(f"Error setting legato switch on synth: {e}")

    @pyqtSlot(int)
    def setAnalogFeel(self, val: int) -> None:
        """Set Patch Analog Feel / 1/f drift depth (0..127), keeping Macro 6 in sync."""
        clamped = max(0, min(127, int(val)))
        if self.patch_state.common.analog_feel != clamped:
            self.patch_state.common.analog_feel = clamped
            self.analogFeelChanged.emit(clamped)
            self.macrosChanged.emit()
            if self.engine.juno:
                try:
                    self.engine.juno.set_patch_analog_feel(clamped)
                except Exception as e:
                    logger.error(f"Error setting analog feel on synth: {e}")

    @pyqtSlot(int, str, "QVariant")
    def setLfoParam(self, lfo_idx: int, param: str, val) -> None:
        """Set LFO 1 or LFO 2 parameter for active tone (or all if linked)."""
        if param == "wave" and val == "SAW":
            val = "SAW-UP"
        targets = self._target_tones()
        for t in targets:
            if lfo_idx == 1:
                if param == "wave" and val in LFO_WAVE_NAMES:
                    t.lfo1_waveform = LFO_WAVE_NAMES.index(val)
                    if self.engine.juno:
                        self.engine.juno.set_tone_lfo(t.tone_index, lfo_index=1, waveform=t.lfo1_waveform)
                elif param == "rate":
                    t.lfo1_rate = max(0, min(127, int(val)))
                    if self.engine.juno:
                        self.engine.juno.set_tone_lfo(t.tone_index, lfo_index=1, rate=t.lfo1_rate)
                elif param == "pitch_depth":
                    t.lfo1_pitch_depth = max(1, min(127, int(val) + 64))
                    if self.engine.juno:
                        self.engine.juno.set_tone_lfo(t.tone_index, lfo_index=1, pitch_depth=t.lfo1_pitch_depth)
                elif param == "tvf_depth":
                    t.lfo1_tvf_depth = max(1, min(127, int(val) + 64))
                    if self.engine.juno:
                        self.engine.juno.set_tone_lfo(t.tone_index, lfo_index=1, tvf_depth=t.lfo1_tvf_depth)
                elif param == "tva_depth":
                    t.lfo1_tva_depth = max(1, min(127, int(val) + 64))
                    if self.engine.juno:
                        self.engine.juno.set_tone_lfo(t.tone_index, lfo_index=1, tva_depth=t.lfo1_tva_depth)
                elif param == "pan_depth":
                    t.lfo1_pan_depth = max(1, min(127, int(val) + 64))
                    if self.engine.juno:
                        self.engine.juno.set_tone_lfo(t.tone_index, lfo_index=1, pan_depth=t.lfo1_pan_depth)
                elif param == "delay_time":
                    t.lfo1_delay_time = max(0, min(127, int(val)))
                    if self.engine.juno:
                        self.engine.juno.set_tone_param(t.tone_index, 0x0072, t.lfo1_delay_time)
                elif param == "fade_mode" and val in LFO_FADE_MODE_NAMES:
                    t.lfo1_fade_mode = LFO_FADE_MODE_NAMES.index(val)
                    if self.engine.juno:
                        self.engine.juno.set_tone_param(t.tone_index, 0x0074, t.lfo1_fade_mode)
                elif param == "fade_time":
                    t.lfo1_fade_time = max(0, min(127, int(val)))
                    if self.engine.juno:
                        self.engine.juno.set_tone_param(t.tone_index, 0x0075, t.lfo1_fade_time)
            elif lfo_idx == 2:
                if param == "wave" and val in LFO_WAVE_NAMES:
                    t.lfo2_waveform = LFO_WAVE_NAMES.index(val)
                    if self.engine.juno:
                        self.engine.juno.set_tone_lfo(t.tone_index, lfo_index=2, waveform=t.lfo2_waveform)
                elif param == "rate":
                    t.lfo2_rate = max(0, min(127, int(val)))
                    if self.engine.juno:
                        self.engine.juno.set_tone_lfo(t.tone_index, lfo_index=2, rate=t.lfo2_rate)
                elif param == "pitch_depth":
                    t.lfo2_pitch_depth = max(1, min(127, int(val) + 64))
                    if self.engine.juno:
                        self.engine.juno.set_tone_lfo(t.tone_index, lfo_index=2, pitch_depth=t.lfo2_pitch_depth)
                elif param == "tvf_depth":
                    t.lfo2_tvf_depth = max(1, min(127, int(val) + 64))
                    if self.engine.juno:
                        self.engine.juno.set_tone_lfo(t.tone_index, lfo_index=2, tvf_depth=t.lfo2_tvf_depth)
                elif param == "tva_depth":
                    t.lfo2_tva_depth = max(1, min(127, int(val) + 64))
                    if self.engine.juno:
                        self.engine.juno.set_tone_lfo(t.tone_index, lfo_index=2, tva_depth=t.lfo2_tva_depth)
                elif param == "pan_depth":
                    t.lfo2_pan_depth = max(1, min(127, int(val) + 64))
                    if self.engine.juno:
                        self.engine.juno.set_tone_lfo(t.tone_index, lfo_index=2, pan_depth=t.lfo2_pan_depth)
                elif param == "delay_time":
                    t.lfo2_delay_time = max(0, min(127, int(val)))
                    if self.engine.juno:
                        self.engine.juno.set_tone_param(t.tone_index, 0x0100, t.lfo2_delay_time)
                elif param == "fade_mode" and val in LFO_FADE_MODE_NAMES:
                    t.lfo2_fade_mode = LFO_FADE_MODE_NAMES.index(val)
                    if self.engine.juno:
                        self.engine.juno.set_tone_param(t.tone_index, 0x0102, t.lfo2_fade_mode)
                elif param == "fade_time":
                    t.lfo2_fade_time = max(0, min(127, int(val)))
                    if self.engine.juno:
                        self.engine.juno.set_tone_param(t.tone_index, 0x0103, t.lfo2_fade_time)

        self.lfoParamsChanged.emit()

    # -------------------------------------------------------------------------
    # Invokable Slots from QML: Sculptor Panel (Mutates ALL 4 Tones Simultaneously)
    # -------------------------------------------------------------------------

    @pyqtSlot(int)
    def sculptCutoff(self, val: int) -> None:
        """Sculpt TVF Cutoff across all 4 tones (0..127)."""
        clamped = max(0, min(127, int(val)))
        for t in self.patch_state.tones:
            t.tvf_cutoff = clamped
            if self.engine.juno:
                try:
                    self.engine.juno.set_tone_tvf(t.tone_index, cutoff=clamped)
                except Exception as e:
                    logger.error(f"Error sculpting cutoff on synth: {e}")
        self.masterCutoffChanged.emit(clamped)

    @pyqtSlot(int)
    def sculptReso(self, val: int) -> None:
        """Sculpt TVF Resonance across all 4 tones (0..127)."""
        clamped = max(0, min(127, int(val)))
        for t in self.patch_state.tones:
            t.tvf_resonance = clamped
            if self.engine.juno:
                try:
                    self.engine.juno.set_tone_tvf(t.tone_index, resonance=clamped)
                except Exception as e:
                    logger.error(f"Error sculpting resonance on synth: {e}")
        self.masterResoChanged.emit(clamped)

    @pyqtSlot(str)
    def sculptTvfType(self, type_str: str) -> None:
        """Sculpt TVF filter type across all 4 tones."""
        val_idx = 1
        if type_str in TVF_TYPE_NAMES:
            val_idx = TVF_TYPE_NAMES.index(type_str)
        for t in self.patch_state.tones:
            t.tvf_filter_type = val_idx
            if self.engine.juno:
                try:
                    self.engine.juno.set_tone_tvf(t.tone_index, filter_type=val_idx)
                except Exception as e:
                    logger.error(f"Error sculpting TVF filter type on synth: {e}")
        self.tvfTypeChanged.emit(type_str)

    @pyqtSlot(int)
    def sculptTvfKeyFollow(self, val: int) -> None:
        """Sculpt TVF Cutoff Keyfollow across all 4 tones (-100..+100%)."""
        clamped = max(-100, min(100, int(val)))
        raw_val = 64 + (clamped // 10)
        for t in self.patch_state.tones:
            t.tvf_cutoff_keyfollow = raw_val
            if self.engine.juno:
                try:
                    self.engine.juno.set_tone_param(t.tone_index, 0x004A, raw_val)
                except Exception as e:
                    logger.error(f"Error sculpting TVF keyfollow on synth: {e}")
        self.tvfKeyFollowChanged.emit(clamped)

    @pyqtSlot(int)
    def sculptTvfEnvDepth(self, depth: int) -> None:
        """Sculpt TVF envelope depth across all 4 tones (-63..+63)."""
        clamped = max(-63, min(63, int(depth)))
        raw_val = 64 + clamped
        for t in self.patch_state.tones:
            t.tvf_env_depth = raw_val
            if self.engine.juno:
                try:
                    self.engine.juno.set_tone_tvf(t.tone_index, env_depth=raw_val)
                except Exception as e:
                    logger.error(f"Error sculpting TVF env depth on synth: {e}")
        self.tvfEnvDepthChanged.emit(clamped)
        self.envShapeChanged.emit("TVF")

    @pyqtSlot(int)
    def sculptTvfVeloSens(self, val: int) -> None:
        """Sculpt TVF velocity sensitivity across all 4 tones (0..127)."""
        clamped = max(0, min(127, int(val)))
        for t in self.patch_state.tones:
            t.tvf_env_velo_sens = clamped
            if self.engine.juno:
                try:
                    self.engine.juno.set_tone_param(t.tone_index, 0x0051, clamped)
                except Exception as e:
                    logger.error(f"Error sculpting TVF velo sens on synth: {e}")
        self.tvfVeloSensChanged.emit(clamped)
        self.envShapeChanged.emit("TVF")

    @pyqtSlot(int)
    def sculptTvfAttack(self, val: int) -> None:
        """Sculpt TVF Attack across all 4 tones (0..127)."""
        clamped = max(0, min(127, int(val)))
        for t in self.patch_state.tones:
            t.tvf_attack = clamped
            self._push_tvf_env(t)
        self.tvfAttackChanged.emit(clamped)
        self.envShapeChanged.emit("TVF")

    @pyqtSlot(int)
    def sculptTvfDecay(self, val: int) -> None:
        """Sculpt TVF Decay across all 4 tones (0..127)."""
        clamped = max(0, min(127, int(val)))
        for t in self.patch_state.tones:
            t.tvf_decay = clamped
            self._push_tvf_env(t)
        self.tvfDecayChanged.emit(clamped)
        self.envShapeChanged.emit("TVF")

    @pyqtSlot(int)
    def sculptTvfSustain(self, val: int) -> None:
        """Sculpt TVF Sustain across all 4 tones (0..127)."""
        clamped = max(0, min(127, int(val)))
        for t in self.patch_state.tones:
            t.tvf_sustain = clamped
            self._push_tvf_env(t)
        self.tvfSustainChanged.emit(clamped)
        self.envShapeChanged.emit("TVF")

    @pyqtSlot(int)
    def sculptTvfRelease(self, val: int) -> None:
        """Sculpt TVF Release across all 4 tones (0..127)."""
        clamped = max(0, min(127, int(val)))
        for t in self.patch_state.tones:
            t.tvf_release = clamped
            self._push_tvf_env(t)
        self.tvfReleaseChanged.emit(clamped)
        self.envShapeChanged.emit("TVF")

    @pyqtSlot(int)
    def sculptTvaPan(self, val: int) -> None:
        """Sculpt Tone TVA Pan across all 4 tones (-64..+63)."""
        clamped = max(-64, min(63, int(val)))
        raw_val = clamped + 64
        for t in self.patch_state.tones:
            t.pan = raw_val
            if self.engine.juno:
                try:
                    self.engine.juno.set_tone_tva(t.tone_index, pan=raw_val)
                except Exception as e:
                    logger.error(f"Error sculpting TVA pan on synth: {e}")
        self.tvaPanChanged.emit(clamped)

    @pyqtSlot(int)
    def sculptTvaVeloSens(self, val: int) -> None:
        """Sculpt Tone TVA Velocity Sensitivity across all 4 tones (0..127)."""
        clamped = max(0, min(127, int(val)))
        for t in self.patch_state.tones:
            t.tva_velo_sens = clamped
            if self.engine.juno:
                try:
                    self.engine.juno.set_tone_param(t.tone_index, 0x0062, clamped)
                except Exception as e:
                    logger.error(f"Error sculpting TVA velo sens on synth: {e}")
        self.tvaVeloSensChanged.emit(clamped)
        self.envShapeChanged.emit("TVA")

    @pyqtSlot(int)
    def sculptTvaAttack(self, val: int) -> None:
        """Sculpt TVA Attack time across all 4 tones (0..127)."""
        clamped = max(0, min(127, int(val)))
        for t in self.patch_state.tones:
            t.tva_attack = clamped
            self._push_tva_env(t)
        self.tvaAttackChanged.emit(clamped)
        self.masterAttackChanged.emit(clamped)
        self.envShapeChanged.emit("TVA")

    @pyqtSlot(int)
    def sculptTvaDecay(self, val: int) -> None:
        """Sculpt TVA Decay time across all 4 tones (0..127)."""
        clamped = max(0, min(127, int(val)))
        for t in self.patch_state.tones:
            t.tva_decay = clamped
            self._push_tva_env(t)
        self.tvaDecayChanged.emit(clamped)
        self.envShapeChanged.emit("TVA")

    @pyqtSlot(int)
    def sculptTvaSustain(self, val: int) -> None:
        """Sculpt TVA Sustain level across all 4 tones (0..127)."""
        clamped = max(0, min(127, int(val)))
        for t in self.patch_state.tones:
            t.tva_sustain = clamped
            self._push_tva_env(t)
        self.tvaSustainChanged.emit(clamped)
        self.envShapeChanged.emit("TVA")

    @pyqtSlot(int)
    def sculptTvaRelease(self, val: int) -> None:
        """Sculpt TVA Release time across all 4 tones (0..127)."""
        clamped = max(0, min(127, int(val)))
        for t in self.patch_state.tones:
            t.tva_release = clamped
            self._push_tva_env(t)
        self.tvaReleaseChanged.emit(clamped)
        self.masterReleaseChanged.emit(clamped)
        self.envShapeChanged.emit("TVA")

    @pyqtSlot(int, str, "QVariant")
    def sculptLfoParam(self, lfo_idx: int, param: str, val) -> None:
        """Sculpt LFO 1 or LFO 2 parameters across all 4 tones."""
        if param == "wave" and val == "SAW":
            val = "SAW-UP"
        for t in self.patch_state.tones:
            if lfo_idx == 1:
                if param == "wave" and val in LFO_WAVE_NAMES:
                    t.lfo1_waveform = LFO_WAVE_NAMES.index(val)
                    if self.engine.juno:
                        self.engine.juno.set_tone_lfo(t.tone_index, lfo_index=1, waveform=t.lfo1_waveform)
                elif param == "rate":
                    t.lfo1_rate = max(0, min(127, int(val)))
                    if self.engine.juno:
                        self.engine.juno.set_tone_lfo(t.tone_index, lfo_index=1, rate=t.lfo1_rate)
                elif param == "pitch_depth":
                    t.lfo1_pitch_depth = max(1, min(127, int(val) + 64))
                    if self.engine.juno:
                        self.engine.juno.set_tone_lfo(t.tone_index, lfo_index=1, pitch_depth=t.lfo1_pitch_depth)
                elif param == "tvf_depth":
                    t.lfo1_tvf_depth = max(1, min(127, int(val) + 64))
                    if self.engine.juno:
                        self.engine.juno.set_tone_lfo(t.tone_index, lfo_index=1, tvf_depth=t.lfo1_tvf_depth)
                elif param == "tva_depth":
                    t.lfo1_tva_depth = max(1, min(127, int(val) + 64))
                    if self.engine.juno:
                        self.engine.juno.set_tone_lfo(t.tone_index, lfo_index=1, tva_depth=t.lfo1_tva_depth)
                elif param == "pan_depth":
                    t.lfo1_pan_depth = max(1, min(127, int(val) + 64))
                    if self.engine.juno:
                        self.engine.juno.set_tone_lfo(t.tone_index, lfo_index=1, pan_depth=t.lfo1_pan_depth)
                elif param == "delay_time":
                    t.lfo1_delay_time = max(0, min(127, int(val)))
                    if self.engine.juno:
                        self.engine.juno.set_tone_param(t.tone_index, 0x0072, t.lfo1_delay_time)
                elif param == "fade_mode" and val in LFO_FADE_MODE_NAMES:
                    t.lfo1_fade_mode = LFO_FADE_MODE_NAMES.index(val)
                    if self.engine.juno:
                        self.engine.juno.set_tone_param(t.tone_index, 0x0074, t.lfo1_fade_mode)
                elif param == "fade_time":
                    t.lfo1_fade_time = max(0, min(127, int(val)))
                    if self.engine.juno:
                        self.engine.juno.set_tone_param(t.tone_index, 0x0075, t.lfo1_fade_time)
            elif lfo_idx == 2:
                if param == "wave" and val in LFO_WAVE_NAMES:
                    t.lfo2_waveform = LFO_WAVE_NAMES.index(val)
                    if self.engine.juno:
                        self.engine.juno.set_tone_lfo(t.tone_index, lfo_index=2, waveform=t.lfo2_waveform)
                elif param == "rate":
                    t.lfo2_rate = max(0, min(127, int(val)))
                    if self.engine.juno:
                        self.engine.juno.set_tone_lfo(t.tone_index, lfo_index=2, rate=t.lfo2_rate)
                elif param == "pitch_depth":
                    t.lfo2_pitch_depth = max(1, min(127, int(val) + 64))
                    if self.engine.juno:
                        self.engine.juno.set_tone_lfo(t.tone_index, lfo_index=2, pitch_depth=t.lfo2_pitch_depth)
                elif param == "tvf_depth":
                    t.lfo2_tvf_depth = max(1, min(127, int(val) + 64))
                    if self.engine.juno:
                        self.engine.juno.set_tone_lfo(t.tone_index, lfo_index=2, tvf_depth=t.lfo2_tvf_depth)
                elif param == "tva_depth":
                    t.lfo2_tva_depth = max(1, min(127, int(val) + 64))
                    if self.engine.juno:
                        self.engine.juno.set_tone_lfo(t.tone_index, lfo_index=2, tva_depth=t.lfo2_tva_depth)
                elif param == "pan_depth":
                    t.lfo2_pan_depth = max(1, min(127, int(val) + 64))
                    if self.engine.juno:
                        self.engine.juno.set_tone_lfo(t.tone_index, lfo_index=2, pan_depth=t.lfo2_pan_depth)
                elif param == "delay_time":
                    t.lfo2_delay_time = max(0, min(127, int(val)))
                    if self.engine.juno:
                        self.engine.juno.set_tone_param(t.tone_index, 0x0100, t.lfo2_delay_time)
                elif param == "fade_mode" and val in LFO_FADE_MODE_NAMES:
                    t.lfo2_fade_mode = LFO_FADE_MODE_NAMES.index(val)
                    if self.engine.juno:
                        self.engine.juno.set_tone_param(t.tone_index, 0x0102, t.lfo2_fade_mode)
                elif param == "fade_time":
                    t.lfo2_fade_time = max(0, min(127, int(val)))
                    if self.engine.juno:
                        self.engine.juno.set_tone_param(t.tone_index, 0x0103, t.lfo2_fade_time)

        self.lfoParamsChanged.emit()

    @pyqtSlot(int)
    def sculptPitchCoarse(self, val: int) -> None:
        """Sculpt Tone Coarse Tune across all 4 tones (-48..+48)."""
        clamped = max(-48, min(48, int(val)))
        raw_val = clamped + 64
        for t in self.patch_state.tones:
            t.coarse_tune = raw_val
            if self.engine.juno:
                try:
                    self.engine.juno.set_tone_pitch(t.tone_index, coarse=raw_val)
                except Exception as e:
                    logger.error(f"Error sculpting coarse tune on synth: {e}")
        self.pitchCoarseChanged.emit(clamped)

    @pyqtSlot(int)
    def sculptPitchFine(self, val: int) -> None:
        """Sculpt Tone Fine Tune across all 4 tones (-50..+50)."""
        clamped = max(-50, min(50, int(val)))
        raw_val = clamped + 64
        for t in self.patch_state.tones:
            t.fine_tune = raw_val
            if not self.patch_state.auto_detune:
                self.patch_state.custom_detune_cache[t.tone_index - 1] = raw_val
            if self.engine.juno:
                try:
                    self.engine.juno.set_tone_pitch(t.tone_index, fine=raw_val)
                except Exception as e:
                    logger.error(f"Error sculpting fine tune on synth: {e}")
        self.pitchFineChanged.emit(clamped)
        self.vaParamsChanged.emit()

    # -------------------------------------------------------------------------
    # Invokable Slots from QML: Pitch Envelope View
    # -------------------------------------------------------------------------

    @pyqtSlot(str, int)
    def setPitchEnvParam(self, param: str, val: int) -> None:
        """Set Pitch Envelope parameter on active tone (or all if linked)."""
        targets = self._target_tones()
        for t in targets:
            if param == "depth":
                t.pitch_env_depth = max(52, min(76, int(val) + 64))
            elif param == "velSens":
                t.pitch_env_vel_sens = max(1, min(127, int(val) + 64))
            elif param == "timeKeyfollow":
                t.pitch_env_time_keyfollow = max(54, min(74, int(val) // 10 + 64))
            elif param == "t1VelSens":
                t.pitch_env_t1_vel_sens = max(1, min(127, int(val) + 64))
            elif param == "t4VelSens":
                t.pitch_env_t4_vel_sens = max(1, min(127, int(val) + 64))
            elif param == "t1":
                t.pitch_env_t1 = max(0, min(127, int(val)))
            elif param == "t2":
                t.pitch_env_t2 = max(0, min(127, int(val)))
            elif param == "t3":
                t.pitch_env_t3 = max(0, min(127, int(val)))
            elif param == "t4":
                t.pitch_env_t4 = max(0, min(127, int(val)))
            elif param == "l0":
                t.pitch_env_l0 = max(1, min(127, int(val) + 64))
            elif param == "l1":
                t.pitch_env_l1 = max(1, min(127, int(val) + 64))
            elif param == "l2":
                t.pitch_env_l2 = max(1, min(127, int(val) + 64))
            elif param == "l3":
                t.pitch_env_l3 = max(1, min(127, int(val) + 64))
            elif param == "l4":
                t.pitch_env_l4 = max(1, min(127, int(val) + 64))

            self._push_pitch_env(t)

        self.pitchEnvChanged.emit()
        self.envShapeChanged.emit("PITCH")

    # -------------------------------------------------------------------------
    # Hardware Envelope Block Pushers
    # -------------------------------------------------------------------------

    def _push_tvf_env(self, t: ToneState) -> None:
        """Send the raw TVF MSEG block [T1..T4, L0..L4] for a tone."""
        if self.engine.juno:
            try:
                self.engine.juno.set_tone_tvf_env(t.tone_index, t.tvf_env_block())
            except Exception as e:
                logger.error(f"Error setting TVF envelope block on synth: {e}")

    def _push_tva_env(self, t: ToneState) -> None:
        """Send the raw TVA MSEG block [T1..T4, L1..L3] for a tone."""
        if self.engine.juno:
            try:
                self.engine.juno.set_tone_tva_env(t.tone_index, t.tva_env_block())
            except Exception as e:
                logger.error(f"Error setting TVA envelope block on synth: {e}")

    def _push_pitch_env(self, t: ToneState) -> None:
        """Send all Pitch Envelope parameters for a tone."""
        if self.engine.juno:
            try:
                kwargs = {
                    "depth": t.pitch_env_depth, "vel_sens": t.pitch_env_vel_sens,
                    "time_keyfollow": t.pitch_env_time_keyfollow,
                    "t1_vel_sens": t.pitch_env_t1_vel_sens, "t4_vel_sens": t.pitch_env_t4_vel_sens,
                    "t1": t.pitch_env_t1, "t2": t.pitch_env_t2, "t3": t.pitch_env_t3, "t4": t.pitch_env_t4,
                    "l0": t.pitch_env_l0, "l1": t.pitch_env_l1, "l2": t.pitch_env_l2,
                    "l3": t.pitch_env_l3, "l4": t.pitch_env_l4,
                }
                self.engine.juno.set_tone_pitch_env(t.tone_index, **kwargs)
            except Exception as e:
                logger.error(f"Error setting pitch env on synth: {e}")

    # -------------------------------------------------------------------------
    # Invokable API for QML: Generic Multi-Segment Envelope Editor
    # -------------------------------------------------------------------------

    @pyqtSlot(str, result="QVariantMap")
    def getEnvSegments(self, env: str) -> dict:
        """Return editable segment data for 'TVF' | 'TVA' | 'PITCH' (active tone).

        times: raw 0..127 [T1..T4].
        levels: TVF -> raw [L0..L4]; TVA -> raw [L1..L3]; PITCH -> signed [-63..63].
        mods: signed envelope modifiers (velSens/t1VelSens/t4VelSens -63..+63,
              timeKf -100..+100; TVF also envDepth -63..+63; PITCH also depth +-12 st).
        """
        env = env.upper()
        t = self._active_tone()
        if env == "TVF":
            return {
                "times": [t.tvf_t1, t.tvf_t2, t.tvf_t3, t.tvf_t4],
                "levels": [t.tvf_l0, t.tvf_l1, t.tvf_l2, t.tvf_l3, t.tvf_l4],
                "bipolar": False, "custom": t.tvf_env_custom,
                "mods": {
                    "envDepth": t.tvf_env_depth_bipolar,
                    "velSens": t.tvf_velo_sens_bipolar,
                    "t1VelSens": t.tvf_env_t1_vel_sens_bipolar,
                    "t4VelSens": t.tvf_env_t4_vel_sens_bipolar,
                    "timeKf": t.tvf_env_time_kf_bipolar,
                },
            }
        if env == "TVA":
            return {
                "times": [t.tva_t1, t.tva_t2, t.tva_t3, t.tva_t4],
                "levels": [t.tva_l1, t.tva_l2, t.tva_l3],
                "bipolar": False, "custom": t.tva_env_custom,
                "mods": {
                    "velSens": t.tva_velo_sens_bipolar,
                    "t1VelSens": t.tva_env_t1_vel_sens_bipolar,
                    "t4VelSens": t.tva_env_t4_vel_sens_bipolar,
                    "timeKf": t.tva_env_time_kf_bipolar,
                },
            }
        return {
            "times": [t.pitch_env_t1, t.pitch_env_t2, t.pitch_env_t3, t.pitch_env_t4],
            "levels": [
                t.pitch_env_l0_bipolar, t.pitch_env_l1_bipolar, t.pitch_env_l2_bipolar,
                t.pitch_env_l3_bipolar, t.pitch_env_l4_bipolar,
            ],
            "bipolar": True, "custom": False,
            "mods": {
                "depth": t.pitch_env_depth_st,
                "velSens": t.pitch_env_vel_sens_bipolar,
                "t1VelSens": t.pitch_env_t1_vel_sens_bipolar,
                "t4VelSens": t.pitch_env_t4_vel_sens_bipolar,
                "timeKf": t.pitch_env_time_kf_bipolar,
            },
        }

    @pyqtSlot(str, str, int)
    def setEnvModParam(self, env: str, param: str, val: int) -> None:
        """Set a signed envelope modifier on target tone(s).

        param: 'velSens' | 't1VelSens' | 't4VelSens' | 'timeKeyfollow'
               plus 'envDepth' (TVF) or 'depth' (PITCH). All values signed.
        """
        env = env.upper()
        val = int(val)
        if env == "PITCH":
            # Pitch keeps its established signed semantics
            self.setPitchEnvParam(param, val)
            self.envShapeChanged.emit("PITCH")
            return

        def signed_raw(v: int) -> int:
            return max(1, min(127, v + 64))

        def kf_raw(v: int) -> int:
            return max(54, min(74, v // 10 + 64))

        targets = self._target_tones()
        for t in targets:
            kwargs = {}
            if param == "velSens":
                raw = signed_raw(val)
                if env == "TVF":
                    t.tvf_env_velo_sens = raw
                    kwargs["env_vel_sens"] = raw
                else:
                    t.tva_velo_sens = raw
                    kwargs["env_vel_sens"] = raw
            elif param == "envDepth" and env == "TVF":
                t.tvf_env_depth = signed_raw(val)
                kwargs["env_depth"] = t.tvf_env_depth
            elif param == "t1VelSens":
                if env == "TVF":
                    t.tvf_env_t1_vel_sens = signed_raw(val)
                    kwargs["env_t1_vel_sens"] = t.tvf_env_t1_vel_sens
                else:
                    t.tva_env_t1_vel_sens = signed_raw(val)
                    kwargs["env_t1_vel_sens"] = t.tva_env_t1_vel_sens
            elif param == "t4VelSens":
                if env == "TVF":
                    t.tvf_env_t4_vel_sens = signed_raw(val)
                    kwargs["env_t4_vel_sens"] = t.tvf_env_t4_vel_sens
                else:
                    t.tva_env_t4_vel_sens = signed_raw(val)
                    kwargs["env_t4_vel_sens"] = t.tva_env_t4_vel_sens
            elif param == "timeKeyfollow":
                if env == "TVF":
                    t.tvf_env_time_keyfollow = kf_raw(val)
                    kwargs["env_time_keyfollow"] = t.tvf_env_time_keyfollow
                else:
                    t.tva_env_time_keyfollow = kf_raw(val)
                    kwargs["env_time_keyfollow"] = t.tva_env_time_keyfollow
            else:
                logger.warning(f"Unknown envelope modifier: {env}/{param}")
                return

            if self.engine.juno:
                try:
                    setter = (self.engine.juno.set_tone_tvf if env == "TVF"
                              else self.engine.juno.set_tone_tva)
                    setter(t.tone_index, **kwargs)
                except Exception as e:
                    logger.error(f"Error setting {env} env modifier {param} on synth: {e}")

        if env == "TVF":
            if param == "velSens":
                self.tvfVeloSensChanged.emit(t.tvf_env_velo_sens)
            elif param == "envDepth":
                self.tvfEnvDepthChanged.emit(t.tvf_env_depth_bipolar)
        elif env == "TVA" and param == "velSens":
            self.tvaVeloSensChanged.emit(t.tva_velo_sens)
        self.envShapeChanged.emit(env)

    @pyqtSlot(str, str, int)
    def setEnvSegment(self, env: str, param: str, val: int) -> None:
        """Set a raw envelope segment on target tone(s).

        param: 't1'..'t4' (0..127) or 'l0'..'l4'.
        Level semantics: TVF/TVA levels are raw 0..127; PITCH levels are signed
        (-63..+63) matching setPitchEnvParam.
        """
        env = env.upper()
        val = int(val)
        is_time = param.startswith("t")
        if is_time:
            clamped = max(0, min(127, val))
        elif env == "PITCH":
            clamped = max(-63, min(63, val))
        else:
            clamped = max(0, min(127, val))

        attr = "pitch_env_" + param if env == "PITCH" else env.lower() + "_" + param
        targets = self._target_tones()
        if not hasattr(targets[0], attr):
            logger.warning(f"Unknown envelope segment: {env}/{param}")
            return

        for t in targets:
            if not is_time and env == "PITCH":
                setattr(t, attr, clamped + 64)
            else:
                setattr(t, attr, clamped)

            if env == "TVF":
                self._push_tvf_env(t)
            elif env == "TVA":
                self._push_tva_env(t)
            else:
                self._push_pitch_env(t)

        if env == "TVF":
            self.envShapeChanged.emit("TVF")
            for sig, v in (
                (self.tvfAttackChanged, t.tvf_attack), (self.tvfDecayChanged, t.tvf_decay),
                (self.tvfSustainChanged, t.tvf_sustain), (self.tvfReleaseChanged, t.tvf_release),
            ):
                sig.emit(v)
        elif env == "TVA":
            self.envShapeChanged.emit("TVA")
            for sig, v in (
                (self.tvaAttackChanged, t.tva_attack), (self.tvaDecayChanged, t.tva_decay),
                (self.tvaSustainChanged, t.tva_sustain), (self.tvaReleaseChanged, t.tva_release),
            ):
                sig.emit(v)
            self.masterAttackChanged.emit(t.tva_attack)
            self.masterReleaseChanged.emit(t.tva_release)
        else:
            self.pitchEnvChanged.emit()
            self.envShapeChanged.emit("PITCH")

    @pyqtSlot(str, result="QVariantList")
    def envPresetNames(self, env: str) -> list:
        """List preset shape names available for an envelope."""
        return env_preset_names(env)

    @pyqtSlot(str, str)
    def applyEnvPreset(self, env: str, name: str) -> None:
        """Apply a preset shape (see core/env_presets.py) to target tone(s)."""
        env = env.upper()
        preset = get_env_preset(env, name)
        if not preset:
            logger.warning(f"Unknown envelope preset: {env}/{name}")
            return

        times = preset["t"]
        levels = preset["l"]
        targets = self._target_tones()
        for t in targets:
            if env == "TVF":
                t.tvf_t1, t.tvf_t2, t.tvf_t3, t.tvf_t4 = times
                t.tvf_l0, t.tvf_l1, t.tvf_l2, t.tvf_l3, t.tvf_l4 = levels
                self._push_tvf_env(t)
            elif env == "TVA":
                t.tva_t1, t.tva_t2, t.tva_t3, t.tva_t4 = times
                t.tva_l1, t.tva_l2, t.tva_l3 = levels
                self._push_tva_env(t)
            else:
                t.pitch_env_t1, t.pitch_env_t2, t.pitch_env_t3, t.pitch_env_t4 = times
                t.pitch_env_l0, t.pitch_env_l1, t.pitch_env_l2, t.pitch_env_l3, t.pitch_env_l4 = (
                    max(1, min(127, int(v) + 64)) for v in levels
                )
                self._push_pitch_env(t)

        if env == "TVF":
            for sig, v in (
                (self.tvfAttackChanged, t.tvf_attack), (self.tvfDecayChanged, t.tvf_decay),
                (self.tvfSustainChanged, t.tvf_sustain), (self.tvfReleaseChanged, t.tvf_release),
            ):
                sig.emit(v)
        elif env == "TVA":
            for sig, v in (
                (self.tvaAttackChanged, t.tva_attack), (self.tvaDecayChanged, t.tva_decay),
                (self.tvaSustainChanged, t.tva_sustain), (self.tvaReleaseChanged, t.tva_release),
            ):
                sig.emit(v)
        self.envShapeChanged.emit(env)
        if env == "PITCH":
            self.pitchEnvChanged.emit()

    @pyqtSlot(str)
    def openEnvOverlay(self, env: str) -> None:
        """Request the UI to open the quick-edit Envelope Overlay for an envelope."""
        self.requestOpenEnvOverlay.emit(env.upper())

    # -------------------------------------------------------------------------
    # Invokable Slots from QML: Master Effects & EQ View
    # -------------------------------------------------------------------------

    @pyqtSlot(str, int)
    def setChorusParam(self, param: str, val: int) -> None:
        """Set Master Chorus parameter."""
        eff = self.patch_state.effects
        if param == "type":
            eff.chorus_type = max(0, min(3, int(val)))
        elif param == "level":
            eff.chorus_level = max(0, min(127, int(val)))
        elif param == "toReverb":
            eff.chorus_to_reverb = max(0, min(2, int(val)))
        elif param == "rate":
            eff.chorus_rate = max(0, min(127, int(val)))
        elif param == "depth":
            eff.chorus_depth = max(0, min(127, int(val)))
        elif param == "preDelay":
            eff.chorus_predelay = max(0, min(127, int(val)))
        elif param == "feedback":
            eff.chorus_feedback = max(0, min(127, int(val)))

        if self.engine.juno:
            try:
                if param in ("type", "level", "toReverb"):
                    self.engine.juno.set_chorus(eff.chorus_type, level=eff.chorus_level, output_select=eff.chorus_to_reverb)
                elif param in ("rate", "depth", "preDelay", "feedback"):
                    self.engine.juno.set_chorus_param(param, int(val))
            except Exception as e:
                logger.error(f"Error setting chorus on synth: {e}")

        self.chorusParamsChanged.emit()
        self.routingChanged.emit()
        self.macrosChanged.emit()

    @pyqtSlot(str, int)
    def setReverbParam(self, param: str, val: int) -> None:
        """Set Master Reverb parameter."""
        eff = self.patch_state.effects
        if param == "type":
            eff.reverb_type = max(0, min(5, int(val)))
        elif param == "level":
            eff.reverb_level = max(0, min(127, int(val)))
        elif param == "time":
            eff.reverb_time = max(0, min(127, int(val)))
        elif param == "damp":
            eff.reverb_damp = max(0, min(127, int(val)))
        elif param == "preDelay":
            eff.reverb_predelay = max(0, min(127, int(val)))
        elif param == "diffusion":
            eff.reverb_diffusion = max(0, min(127, int(val)))
        elif param == "tone":
            eff.reverb_tone = max(0, min(127, int(val)))

        if self.engine.juno:
            try:
                if param in ("type", "level"):
                    self.engine.juno.set_reverb(eff.reverb_type, level=eff.reverb_level)
                elif param in ("time", "damp", "preDelay", "diffusion", "tone"):
                    self.engine.juno.set_reverb_param(param, int(val))
            except Exception as e:
                logger.error(f"Error setting reverb on synth: {e}")

        self.reverbParamsChanged.emit()
        self.routingChanged.emit()
        self.macrosChanged.emit()

    @pyqtSlot(str, "QVariant")
    def setMasterEqParam(self, param: str, val) -> None:
        """Set Master 3-Band Parametric EQ parameter."""
        eff = self.patch_state.effects
        if param == "switch":
            eff.eq_switch = bool(val)
        elif param == "lowGain":
            eff.eq_low_gain = int(val)
        elif param == "lowFreq":
            eff.eq_low_freq = int(val)
        elif param == "midGain":
            eff.eq_mid_gain = int(val)
        elif param == "midFreq":
            eff.eq_mid_freq = int(val)
        elif param == "midQ":
            eff.eq_mid_q = float(val)
        elif param == "highGain":
            eff.eq_high_gain = int(val)
        elif param == "highFreq":
            eff.eq_high_freq = int(val)
        elif param == "masterLevel":
            eff.eq_master_level = int(val)

        if self.engine.juno:
            try:
                self.engine.juno.set_master_eq_param(param, val)
            except Exception as e:
                logger.error(f"Error setting master EQ on synth: {e}")

        self.masterEqChanged.emit()

    # -------------------------------------------------------------------------
    # Invokable Slots from QML: MFX Studio View
    # -------------------------------------------------------------------------

    @pyqtSlot(int)
    def setMfxAlgoId(self, algo_id: int) -> None:
        """Select active MFX Algorithm (0..80)."""
        eff = self.patch_state.effects
        clamped = max(0, min(80, int(algo_id)))
        eff.mfx_type = clamped
        if clamped > 0:
            eff.mfx_last_active_type = clamped
            eff.mfx_bypassed = False
            # Load default parameter values from catalog
            algo = get_mfx_algo(clamped)
            if algo and "params" in algo:
                for p in algo["params"]:
                    idx = p["idx"]
                    if 0 <= idx < 32:
                        eff.mfx_params[idx] = p.get("val", 0)
        else:
            eff.mfx_bypassed = True

        if self.engine.juno:
            try:
                self.engine.juno.set_mfx(eff.mfx_type)
                if clamped > 0:
                    algo = get_mfx_algo(clamped)
                    if algo and "params" in algo:
                        vals = [eff.mfx_params[p["idx"]] for p in algo["params"]]
                        self.engine.juno.set_mfx_params_bulk(vals)
            except Exception as e:
                logger.error(f"Error setting MFX type on synth: {e}")

        self.mfxValuesChanged.emit()
        self.mfxParamsChanged.emit()
        self.routingChanged.emit()

    @pyqtSlot(int, int)
    def setMfxParam(self, param_index: int, val: int) -> None:
        """Set an individual MFX parameter (0..31) and transmit live SysEx to synth."""
        if not (0 <= param_index < 32):
            return
        eff = self.patch_state.effects
        eff.mfx_params[param_index] = int(val)

        if self.engine.juno:
            try:
                self.engine.juno.set_mfx_param(param_index, int(val))
            except Exception as e:
                logger.error(f"Error setting MFX param {param_index} on synth: {e}")

        self.mfxValuesChanged.emit()

    @pyqtSlot(bool)
    def setMfxBypass(self, bypassed: bool) -> None:
        """Toggle MFX Bypass switch."""
        eff = self.patch_state.effects
        eff.mfx_bypassed = bypassed
        target_type = 0 if bypassed else eff.mfx_last_active_type
        eff.mfx_type = target_type

        if self.engine.juno:
            try:
                self.engine.juno.set_mfx(target_type)
            except Exception as e:
                logger.error(f"Error toggling MFX bypass on synth: {e}")

        self.mfxParamsChanged.emit()
        self.routingChanged.emit()

    @pyqtSlot(str, int)
    def setMfxSend(self, send_type: str, val: int) -> None:
        """Set MFX Dry, Chorus, or Reverb send level (0..127)."""
        eff = self.patch_state.effects
        clamped = max(0, min(127, int(val)))
        if send_type == "dry":
            eff.mfx_dry_send = clamped
        elif send_type == "chorus":
            eff.mfx_chorus_send = clamped
        elif send_type == "reverb":
            eff.mfx_reverb_send = clamped

        if self.engine.juno:
            try:
                self.engine.juno.set_mfx(
                    eff.mfx_type,
                    dry_send=eff.mfx_dry_send,
                    chorus_send=eff.mfx_chorus_send,
                    reverb_send=eff.mfx_reverb_send,
                )
            except Exception as e:
                logger.error(f"Error setting MFX sends on synth: {e}")

        self.mfxParamsChanged.emit()
        self.routingChanged.emit()

    # -------------------------------------------------------------------------
    # Invokable Slots from QML: Routing View
    # -------------------------------------------------------------------------

    @pyqtSlot(result="QVariantList")
    def detectRoutingPitfalls(self) -> list:
        """Detect potential parallel routing pitfalls, phase cancellation, or reverb overloading."""
        eff = self.patch_state.effects
        tones = self.patch_state.tones
        pitfalls = []

        # 1. Multiple Reverb Injections
        has_tone_rev = any(t.reverb_send > 0 for t in tones)
        has_mfx_rev = (eff.mfx_reverb_send > 0) and not eff.mfx_bypassed
        has_cho_rev = (eff.chorus_to_reverb > 0) and (eff.chorus_type > 0) and (eff.chorus_level > 0)

        reverb_sources = 0
        sources_str = []
        if has_tone_rev:
            reverb_sources += 1
            sources_str.append("Tones")
        if has_mfx_rev:
            reverb_sources += 1
            sources_str.append("MFX")
        if has_cho_rev:
            reverb_sources += 1
            sources_str.append("Chorus")

        if reverb_sources >= 2:
            pitfalls.append({
                "type": "REVERB_OVERLOAD",
                "severity": "warning",
                "title": "Multiple Reverb Injections Active",
                "description": f"Reverb is receiving parallel audio feeds simultaneously from: {', '.join(sources_str)}. This can create an uncontrolled muddy reverb wash and phase smear."
            })

        # 2. Mono Chorus-to-Reverb Collapsing
        if eff.chorus_to_reverb in (1, 2) and eff.chorus_type > 0 and eff.chorus_level > 0:
            if eff.chorus_to_reverb == 1:
                desc = "Chorus output is routed EXCLUSIVELY into Reverb in mono, bypassing stereo Main Out."
            else:
                desc = "Chorus output feeds Main Out in stereo AND Reverb in mono. Note that the reverb feed is summed to mono."
            pitfalls.append({
                "type": "CHORUS_MONO_SUM",
                "severity": "info",
                "title": "Chorus Sent to Reverb (Mono Summed)",
                "description": desc
            })

        # 3. Comb Filtering Risk (Parallel Direct Dry + MFX Output)
        any_direct = any(t.output_assign == 1 for t in tones)
        if any_direct and eff.mfx_dry_send > 0 and not eff.mfx_bypassed:
            pitfalls.append({
                "type": "COMB_FILTERING",
                "severity": "caution",
                "title": "Parallel Direct & MFX Summing",
                "description": "Some tones are routed directly to Main Out while MFX also outputs dry signal to Main Out. This can cause phase cancellation or comb filtering."
            })

        # 4. Double Modulation (MFX Chorus + Master Chorus)
        if not eff.mfx_bypassed and eff.mfx_chorus_send > 0 and eff.chorus_type > 0 and eff.chorus_level > 0:
            pitfalls.append({
                "type": "DOUBLE_MODULATION",
                "severity": "info",
                "title": "Double Modulation / Cascaded Chorus",
                "description": "MFX output is feeding Master Chorus. If MFX is also an active delay/flanger/chorus, multiple modulation delays will overlap."
            })

        return pitfalls

    @pyqtSlot(str)
    def applyRoutingPreset(self, preset_name: str) -> None:
        """Apply a curated routing topology algorithm across Tones, MFX, Chorus, and Reverb."""
        preset = preset_name.upper().replace(" ", "_")
        eff = self.patch_state.effects
        tones = self.patch_state.tones
        juno = self.engine.juno if self.engine else None

        if preset == "SERIAL_CHAIN":
            # Tones (all) -> MFX -> Chorus -> Reverb -> Out
            eff.routing_preset = "SERIAL_CHAIN"
            eff.manual_routing_unlocked = False
            for t in tones:
                t.output_assign = 0  # MFX
                t.output_level = 127
                t.chorus_send = 0
                t.reverb_send = 0
                if juno:
                    try:
                        juno.set_tone_output(t.tone_index, output_assign=0, output_level=127, chorus_send=0, reverb_send=0)
                    except Exception as e:
                        logger.error(f"Error setting tone {t.tone_index} routing: {e}")
            eff.mfx_dry_send = 0      # All MFX audio cascades to Chorus
            eff.mfx_chorus_send = 127
            eff.mfx_reverb_send = 0   # No direct MFX leak to Reverb
            eff.chorus_level = 80
            eff.chorus_to_reverb = 1  # REV only: pure serial chain (Chorus cascades exclusively into Reverb)
            eff.reverb_level = 60
            # dry=0 routing depends on live FX units to reach Main; ensure the
            # chain has endpoints (a preset that plays no sound is a broken preset)
            if eff.chorus_type == 0:
                eff.chorus_type = 1
            if eff.reverb_type == 0:
                eff.reverb_type = 4

        elif preset == "STUDIO_AUX":
            # Tones -> MFX (Insert) -> Out; MFX sends parallel to Chorus & Reverb
            eff.routing_preset = "STUDIO_AUX"
            eff.manual_routing_unlocked = False
            for t in tones:
                t.output_assign = 0  # MFX
                t.output_level = 127
                t.chorus_send = 0
                t.reverb_send = 0
                if juno:
                    try:
                        juno.set_tone_output(t.tone_index, output_assign=0, output_level=127, chorus_send=0, reverb_send=0)
                    except Exception as e:
                        logger.error(f"Error setting tone {t.tone_index} routing: {e}")
            eff.mfx_dry_send = 127     # MFX direct to main
            eff.mfx_chorus_send = 60   # Parallel aux send
            eff.mfx_reverb_send = 60   # Parallel aux send
            eff.chorus_level = 75
            eff.chorus_to_reverb = 0   # MAIN only: no leak into reverb
            eff.reverb_level = 65

        elif preset == "VINTAGE_SYNTH":
            # Tones -> Direct Out (L+R) + Parallel Chorus & Reverb sends (MFX bypassed/muted)
            eff.routing_preset = "VINTAGE_SYNTH"
            eff.manual_routing_unlocked = False
            for t in tones:
                t.output_assign = 1  # DIRECT (L+R)
                t.output_level = 127
                t.chorus_send = 70
                t.reverb_send = 50
                if juno:
                    try:
                        juno.set_tone_output(t.tone_index, output_assign=1, output_level=127, chorus_send=70, reverb_send=50)
                    except Exception as e:
                        logger.error(f"Error setting tone {t.tone_index} routing: {e}")
            eff.mfx_dry_send = 0
            eff.mfx_chorus_send = 0
            eff.mfx_reverb_send = 0
            eff.chorus_level = 80
            eff.chorus_to_reverb = 0   # MAIN only
            eff.reverb_level = 60

        elif preset == "AMBIENT_WASH":
            # Tones -> MFX -> Chorus (100% to Reverb) -> Reverb -> Out
            eff.routing_preset = "AMBIENT_WASH"
            eff.manual_routing_unlocked = False
            for t in tones:
                t.output_assign = 0  # MFX
                t.output_level = 127
                t.chorus_send = 0
                t.reverb_send = 0
                if juno:
                    try:
                        juno.set_tone_output(t.tone_index, output_assign=0, output_level=127, chorus_send=0, reverb_send=0)
                    except Exception as e:
                        logger.error(f"Error setting tone {t.tone_index} routing: {e}")
            eff.mfx_dry_send = 30
            eff.mfx_chorus_send = 110
            eff.mfx_reverb_send = 40
            eff.chorus_level = 90
            eff.chorus_to_reverb = 1   # REV only: chorus is entirely submerged in reverb
            eff.reverb_level = 95
            if eff.chorus_type == 0:
                eff.chorus_type = 1
            if eff.reverb_type == 0:
                eff.reverb_type = 4

        elif preset in ("CUSTOM", "MANUAL"):
            eff.routing_preset = "CUSTOM"
            eff.manual_routing_unlocked = True

        # Send MFX, Chorus, Reverb updates to synth
        if juno:
            try:
                juno.set_mfx(
                    eff.mfx_type,
                    dry_send=eff.mfx_dry_send,
                    chorus_send=eff.mfx_chorus_send,
                    reverb_send=eff.mfx_reverb_send,
                )
                juno.set_chorus(
                    eff.chorus_type,
                    level=eff.chorus_level,
                    output_select=eff.chorus_to_reverb,
                )
                juno.set_reverb(
                    eff.reverb_type,
                    level=eff.reverb_level,
                )
            except Exception as e:
                logger.error(f"Error syncing effects routing on synth: {e}")

        self.routingChanged.emit()
        self.mfxParamsChanged.emit()
        self.chorusParamsChanged.emit()
        self.reverbParamsChanged.emit()
        self.macrosChanged.emit()

    @pyqtSlot(bool)
    def setManualRoutingUnlocked(self, unlocked: bool) -> None:
        """Unlock or lock manual sliders editing."""
        self.patch_state.effects.manual_routing_unlocked = bool(unlocked)
        if unlocked and self.patch_state.effects.routing_preset != "CUSTOM":
            self.patch_state.effects.routing_preset = "CUSTOM"
        self.routingChanged.emit()

    @pyqtSlot(int, str, int)
    def setToneRoutingParam(self, tone_idx: int, param: str, val: int) -> None:
        """Set tone routing parameter. tone_idx: 1..4 (or 0 for all 4 tones)."""
        tones = self.patch_state.tones if tone_idx == 0 else [self.patch_state.tones[tone_idx - 1]]
        juno = self.engine.juno if self.engine else None

        self.patch_state.effects.routing_preset = "CUSTOM"

        for t in tones:
            if param == "assign":
                val_int = max(0, min(2, int(val)))
                t.output_assign = val_int
                hw_assign = 0 if val_int in (0, 2) else 1
                if juno:
                    try:
                        juno.set_tone_output(t.tone_index, output_assign=hw_assign)
                    except Exception as e:
                        logger.error(f"Error setting tone output assign: {e}")
            elif param == "level":
                t.output_level = max(0, min(127, int(val)))
                if juno:
                    try:
                        juno.set_tone_output(t.tone_index, output_level=t.output_level)
                    except Exception as e:
                        logger.error(f"Error setting tone output level: {e}")
            elif param == "chorusSend":
                t.chorus_send = max(0, min(127, int(val)))
                if juno:
                    try:
                        juno.set_tone_output(t.tone_index, chorus_send=t.chorus_send)
                    except Exception as e:
                        logger.error(f"Error setting tone chorus send: {e}")
            elif param == "reverbSend":
                t.reverb_send = max(0, min(127, int(val)))
                if juno:
                    try:
                        juno.set_tone_output(t.tone_index, reverb_send=t.reverb_send)
                    except Exception as e:
                        logger.error(f"Error setting tone reverb send: {e}")

        self.routingChanged.emit()

    # -------------------------------------------------------------------------
    # Invokable Slots from QML: Mod Matrix View
    # -------------------------------------------------------------------------

    @pyqtSlot(int, str, int)
    def setMatrixCtrlParam(self, ctrl_index: int, param: str, val: int) -> None:
        """Set source, dest, or sens for Matrix Controller 1..4."""
        if 1 <= ctrl_index <= 4:
            c = self.patch_state.common.matrix_ctrls[ctrl_index - 1]
            if param == "source":
                c.source = max(0, min(109, int(val)))
            elif param == "dest1":
                c.dest1 = max(0, min(33, int(val)))
            elif param == "sens1":
                c.sens1 = max(1, min(127, int(val) + 64))
            elif param == "dest2":
                c.dest2 = max(0, min(33, int(val)))
            elif param == "sens2":
                c.sens2 = max(1, min(127, int(val) + 64))
            elif param == "dest3":
                c.dest3 = max(0, min(33, int(val)))
            elif param == "sens3":
                c.sens3 = max(1, min(127, int(val) + 64))
            elif param == "dest4":
                c.dest4 = max(0, min(33, int(val)))
            elif param == "sens4":
                c.sens4 = max(1, min(127, int(val) + 64))

            if self.engine.juno:
                try:
                    self.engine.juno.set_matrix_control(
                        ctrl_index,
                        source=c.source,
                        dest1=c.dest1, sens1=c.sens1,
                        dest2=c.dest2, sens2=c.sens2,
                        dest3=c.dest3, sens3=c.sens3,
                        dest4=c.dest4, sens4=c.sens4,
                    )
                except Exception as e:
                    logger.error(f"Error setting matrix control on synth: {e}")

            self.matrixCtrlChanged.emit()

    @pyqtSlot(int, int, int, bool)
    def setToneMatrixSwitch(self, tone_index: int, ctrl_index: int, dest_index: int, enable: bool) -> None:
        """Set Tone Control Switch (1..4) for a Matrix Controller (1..4) Destination (1..4)."""
        if 1 <= tone_index <= 4 and 1 <= ctrl_index <= 4 and 1 <= dest_index <= 4:
            sw_val = 1 if enable else 0
            self.patch_state.tones[tone_index - 1].matrix_switches[ctrl_index - 1][dest_index - 1] = sw_val
            if self.engine.juno:
                try:
                    self.engine.juno.set_tone_matrix_switch(tone_index, ctrl_index, dest_index, sw_val)
                except Exception as e:
                    logger.error(f"Error setting tone matrix switch on synth: {e}")
            self.matrixCtrlChanged.emit()

    # -------------------------------------------------------------------------
    # Invokable Slots from QML: Step LFO View
    # -------------------------------------------------------------------------

    @pyqtSlot(int, int)
    def setStepLfoStep(self, step_index: int, val: int) -> None:
        """Set bipolar value for one of the 16 steps (-36..+36) for active tone (or all if linked)."""
        if 0 <= step_index < 16:
            clamped = max(-36, min(36, int(val)))
            targets = self._target_tones()
            for tone in targets:
                new_steps = list(tone.step_lfo_steps)
                new_steps[step_index] = clamped
                tone.step_lfo_steps = new_steps
                if self.engine.juno:
                    try:
                        self.engine.juno.set_tone_step_lfo_step(tone.tone_index, step_index, clamped)
                    except Exception as e:
                        logger.error(f"Error setting Step LFO step {step_index} on tone {tone.tone_index}: {e}")
            self.stepLfoChanged.emit()

    @pyqtSlot("QVariantList")
    def setStepLfoAllSteps(self, steps: list) -> None:
        """Set all 16 steps at once for active tone (or all if linked) via contiguous SysEx."""
        clamped_steps = [max(-36, min(36, int(s))) for s in steps[:16]]
        if len(clamped_steps) < 16:
            clamped_steps.extend([0] * (16 - len(clamped_steps)))
        targets = self._target_tones()
        for tone in targets:
            tone.step_lfo_steps = list(clamped_steps)
            if self.engine.juno:
                try:
                    self.engine.juno.set_tone_step_lfo_steps(tone.tone_index, clamped_steps)
                except Exception as e:
                    logger.error(f"Error setting all Step LFO steps on tone {tone.tone_index}: {e}")
        self.stepLfoChanged.emit()

    @pyqtSlot(str, "QVariant")
    def setStepLfoParam(self, param: str, val) -> None:
        """Set curve (step type), rate, destination, or depth for the Step LFO."""
        if param == "curve":
            step_type = max(0, min(1, int(val)))
            targets = self._target_tones()
            for tone in targets:
                tone.step_lfo_type = step_type
                if self.engine.juno:
                    try:
                        self.engine.juno.set_tone_step_lfo_type(tone.tone_index, step_type)
                    except Exception as e:
                        logger.error(f"Error setting Step LFO type on tone {tone.tone_index}: {e}")
            self.stepLfoChanged.emit()
        elif param == "rateIdx":
            self.patch_state.step_lfo.sync_rate_idx = int(val)
            self.stepLfoChanged.emit()
        elif param == "destIdx":
            self.patch_state.step_lfo.dest_idx = int(val)
            self.stepLfoChanged.emit()
        elif param == "depth":
            self.patch_state.step_lfo.depth = max(0, min(127, int(val)))
            self.stepLfoChanged.emit()

    @pyqtSlot(int)
    def assignStepLfoToLfo(self, lfo_num: int) -> None:
        """Assign or toggle Step LFO (Wave 12) on LFO 1 or LFO 2 for active tone (or all if linked)."""
        if lfo_num not in (1, 2):
            return
        targets = self._target_tones()
        for tone in targets:
            if lfo_num == 1:
                new_wave = 1 if tone.lfo1_waveform == 12 else 12  # 1: TRI, 12: STEP
                tone.lfo1_waveform = new_wave
                if self.engine.juno:
                    try:
                        self.engine.juno.set_tone_lfo(tone.tone_index, lfo_index=1, waveform=new_wave)
                    except Exception as e:
                        logger.error(f"Error assigning LFO 1 wave on tone {tone.tone_index}: {e}")
            else:
                new_wave = 0 if tone.lfo2_waveform == 12 else 12  # 0: SIN, 12: STEP
                tone.lfo2_waveform = new_wave
                if self.engine.juno:
                    try:
                        self.engine.juno.set_tone_lfo(tone.tone_index, lfo_index=2, waveform=new_wave)
                    except Exception as e:
                        logger.error(f"Error assigning LFO 2 wave on tone {tone.tone_index}: {e}")
        self.lfoParamsChanged.emit()
        self.stepLfoChanged.emit()

    # -------------------------------------------------------------------------
    # Invokable Slots from QML: 4-OSC VA Engine View
    # -------------------------------------------------------------------------

    @pyqtSlot(int, int)
    def setVaOscWave(self, osc_index: int, wave_idx: int) -> None:
        """Assign VA bread-and-butter waveform to tone 1..4."""
        # Wave mapping: 0: Saw HD (579), 1: Sqr HD (600), 2: Tri (621), 3: Sin (1322), 4: Pink Noise (637)
        va_wave_map = {0: 579, 1: 600, 2: 621, 3: 1322, 4: 637}
        wnum = va_wave_map.get(wave_idx, 579)
        self.setToneWave(osc_index, "INTA", wnum)
        self.vaParamsChanged.emit()

    @pyqtSlot(int, int)
    def setVaOscCoarse(self, osc_index: int, val: int) -> None:
        """Set coarse tune in semitones for oscillator 1..4."""
        if 1 <= osc_index <= 4:
            clamped = max(-48, min(48, int(val)))
            raw = clamped + 64
            t = self.patch_state.tones[osc_index - 1]
            t.coarse_tune = raw
            if self.engine.juno:
                try:
                    self.engine.juno.set_tone_pitch(osc_index, coarse=raw)
                except Exception as e:
                    logger.error(f"Error setting OSC coarse on synth: {e}")
            self.pitchCoarseChanged.emit(self.pitchCoarse)
            self.vaParamsChanged.emit()

    @pyqtSlot(int, int)
    def setVaOscFine(self, osc_index: int, val: int) -> None:
        """Set fine tune in cents for oscillator 1..4."""
        if 1 <= osc_index <= 4:
            if self.patch_state.auto_detune:
                # Locked in Auto Detune mode
                return
            clamped = max(-50, min(50, int(val)))
            raw = clamped + 64
            t = self.patch_state.tones[osc_index - 1]
            t.fine_tune = raw
            self.patch_state.custom_detune_cache[osc_index - 1] = raw
            if self.engine.juno:
                try:
                    self.engine.juno.set_tone_pitch(osc_index, fine=raw)
                except Exception as e:
                    logger.error(f"Error setting OSC fine on synth: {e}")
            self.pitchFineChanged.emit(self.pitchFine)
            self.vaParamsChanged.emit()

    @pyqtSlot(int, int)
    def setVaOscLevel(self, osc_index: int, val: int) -> None:
        """Set level for oscillator 1..4."""
        self.setToneLevel(osc_index, val)
        self.vaParamsChanged.emit()

    @pyqtSlot(int, int)
    def setVaOscPw(self, osc_index: int, val: int) -> None:
        """Set Pulse Width for oscillator 1..4."""
        if 1 <= osc_index <= 4:
            self.patch_state.va_pw[osc_index - 1] = int(val)
            pw_map = {10: 612, 15: 613, 25: 614, 30: 615, 40: 616, 45: 617, 50: 600}
            wnum = pw_map.get(int(val), 600)
            self.setToneWave(osc_index, "INTA", wnum)
            self.vaParamsChanged.emit()

    @pyqtSlot(int, int)
    def setVaOscPwm(self, osc_index: int, val: int) -> None:
        """Set Pulse Width Modulation depth for oscillator 1..4."""
        if 1 <= osc_index <= 4:
            m = max(0, min(100, int(val)))
            self.patch_state.va_pwm[osc_index - 1] = m
            if m >= 20:
                wnum = 1326 if m < 40 else (1327 if m < 60 else (1328 if m < 80 else 1329))
                self.setToneWave(osc_index, "INTA", wnum)
            self.vaParamsChanged.emit()

    @pyqtSlot(bool)
    def setAutoDetune(self, active: bool) -> None:
        """Toggle software Auto Detune with custom detune memory cache.

        Auto Detune is a workstation-side feature: it writes per-tone fine pitch to
        the synth (the detune mechanism itself), but the on/off state is app-only.
        """
        if active:
            # Snapshot custom detuning before engaging Auto Detune
            self.patch_state.custom_detune_cache = [t.fine_tune for t in self.patch_state.tones]
            self.patch_state.auto_detune = True
            self.applyAutoDetune()
        else:
            self.patch_state.auto_detune = False
            # Restore cached custom fine detunings
            for idx, raw in enumerate(self.patch_state.custom_detune_cache, start=1):
                self.patch_state.tones[idx - 1].fine_tune = raw
                if self.engine.juno:
                    try:
                        self.engine.juno.set_tone_pitch(idx, fine=raw)
                    except Exception as e:
                        logger.error(f"Error restoring custom fine tune on synth: {e}")
        self.pitchFineChanged.emit(self.pitchFine)
        self.vaParamsChanged.emit()

    @pyqtSlot(int)
    def setAutoDetuneCents(self, cents: int) -> None:
        """Set Auto Detune spread (0..50 cents)."""
        if not self.patch_state.auto_detune:
            return
        self.patch_state.auto_detune_cents = max(0, min(50, int(cents)))
        self.applyAutoDetune()
        self.vaParamsChanged.emit()

    def applyAutoDetune(self) -> None:
        """Distribute symmetrical auto-detuning across all 4 oscillators."""
        if not self.patch_state.auto_detune:
            return
        d = self.patch_state.auto_detune_cents
        spreads = [-d, d, -(d // 2), (d // 2)]

        for idx, offset in enumerate(spreads, start=1):
            raw = max(14, min(114, 64 + offset))
            self.patch_state.tones[idx - 1].fine_tune = raw
            if self.engine.juno:
                try:
                    self.engine.juno.set_tone_pitch(idx, fine=raw)
                except Exception as e:
                    logger.error(f"Error applying auto detune on synth: {e}")
        self.pitchFineChanged.emit(self.pitchFine)
        self.vaParamsChanged.emit()

    # -------------------------------------------------------------------------
    # Invokable Slots from QML: Performance Mixer View
    # -------------------------------------------------------------------------

    @pyqtSlot(int, int)
    def setPartVolume(self, part_index: int, vol: int) -> None:
        """Set volume level for Performance Part 1..16."""
        if 1 <= part_index <= 16:
            self.patch_state.perf_parts[part_index - 1].volume = max(0, min(127, int(vol)))
            self.perfPartsChanged.emit()

    @pyqtSlot(int, int)
    def setPartPan(self, part_index: int, pan: int) -> None:
        """Set pan for Performance Part 1..16."""
        if 1 <= part_index <= 16:
            self.patch_state.perf_parts[part_index - 1].pan = max(0, min(127, int(pan)))
            self.perfPartsChanged.emit()

    @pyqtSlot(int, bool)
    def setPartMute(self, part_index: int, mute: bool) -> None:
        """Set mute switch for Performance Part 1..16."""
        if 1 <= part_index <= 16:
            self.patch_state.perf_parts[part_index - 1].muted = mute
            self.perfPartsChanged.emit()

    @pyqtSlot(int, bool)
    def setPartSolo(self, part_index: int, solo: bool) -> None:
        """Set solo switch for Performance Part 1..16."""
        if 1 <= part_index <= 16:
            self.patch_state.perf_parts[part_index - 1].solo = solo
            self.perfPartsChanged.emit()

    # -------------------------------------------------------------------------
    # Wave, Patch Name & Navigation Slots
    # -------------------------------------------------------------------------

    @pyqtSlot(int, str, int)
    def setToneWave(self, tone_number: int, bank: str, wave_num: int) -> None:
        """Assign waveform to tone (1..4) and send SysEx to Roland hardware."""
        if 1 <= tone_number <= 4:
            self._tone_waves[tone_number - 1] = (bank.upper(), wave_num)
            t = self.patch_state.tones[tone_number - 1]
            t.wave_bank_l = bank.upper()
            t.wave_num_l = wave_num
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

    @pyqtSlot(str)
    @pyqtSlot(str, str)
    def setPatchName(self, name: str, mode: str = "PATCH") -> None:
        """Set active patch name and sound mode."""
        self._patch_name = name
        self._sound_mode = mode
        self.patch_state.common.name = name
        self.patch_state.sound_mode = mode
        self.patchInfoChanged.emit(self._patch_name, self._sound_mode)
        if self.engine.juno:
            try:
                self.engine.juno.set_patch_name(name)
            except Exception as e:
                logger.warning(f"Could not set patch name on synth: {e}")

    @pyqtSlot()
    def syncPatchFromSynth(self) -> None:
        """Query active patch and all workstation parameters from Roland hardware."""
        if not self.engine.juno:
            logger.info("Cannot sync: No Roland synthesizer connected.")
            return

        try:
            logger.info("Syncing entire patch and workstation state from Roland hardware...")
            full_sync_ok = False
            if hasattr(self.engine.juno, "read_full_patch"):
                try:
                    state = self.engine.juno.read_full_patch(timeout=1.0)
                    if isinstance(state, PatchState):
                        self.patch_state = state
                        self.patch_state.effects.routing_preset = ""  # No algorithm preset selected on hardware sync
                        self._patch_name = state.common.name
                        self._sound_mode = state.sound_mode

                        for idx in range(4):
                            t = state.tones[idx]
                            self._tone_waves[idx] = (t.wave_bank_l, t.wave_num_l)
                        self.engine.tone_levels = (
                            state.tones[0].level,
                            state.tones[1].level,
                            state.tones[2].level,
                            state.tones[3].level,
                        )
                        self.patch_state.custom_detune_cache = [t.fine_tune for t in state.tones]
                        full_sync_ok = True
                except Exception as e:
                    logger.warning(f"Could not read full patch: {e}")

            # Legacy fallback only when the full image read failed/unavailable,
            # so partial queries never clobber the complete decoded state.
            if not full_sync_ok:
                if hasattr(self.engine.juno, "get_patch_name"):
                    try:
                        name = self.engine.juno.get_patch_name(timeout=0.8)
                        if isinstance(name, str):
                            self._patch_name = name
                            self.patch_state.common.name = name
                    except Exception as e:
                        logger.warning(f"Could not read patch name: {e}")

                if hasattr(self.engine.juno, "get_sound_mode"):
                    try:
                        mode = self.engine.juno.get_sound_mode(timeout=0.8)
                        mode_str = mode.name if hasattr(mode, "name") else str(mode)
                        if isinstance(mode_str, str):
                            self._sound_mode = mode_str
                            self.patch_state.sound_mode = mode_str
                    except Exception as e:
                        logger.warning(f"Could not read sound mode: {e}")

                self.patchInfoChanged.emit(str(self._patch_name), str(self._sound_mode))

                if hasattr(self.engine.juno, "get_all_tone_waves"):
                    try:
                        active_waves = self.engine.juno.get_all_tone_waves(timeout=0.8)
                        if isinstance(active_waves, (list, tuple)):
                            for idx, item in enumerate(active_waves):
                                if idx < 4 and isinstance(item, (list, tuple)) and len(item) == 2:
                                    bank, wnum = item
                                    self._tone_waves[idx] = (str(bank), int(wnum))
                                    self.patch_state.tones[idx].wave_bank_l = str(bank)
                                    self.patch_state.tones[idx].wave_num_l = int(wnum)
                    except Exception as e:
                        logger.warning(f"Could not read tone waves: {e}")
            else:
                self.patchInfoChanged.emit(str(self._patch_name), str(self._sound_mode))

            self._cached_tone_wave_data = [
                self._wave_catalog.get_wave(b, n) for b, n in self._tone_waves
            ]

            # Emit all signals to refresh every UI page
            self._emit_all_state_signals()
            logger.info(f"Sync complete. Synced patch: '{self._patch_name}'")
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

    @pyqtSlot()
    def openInitPatchModal(self) -> None:
        """Request UI to open the Patch Initialization confirmation modal."""
        logger.debug("UI requested openInitPatchModal")
        self.requestOpenInitPatchModal.emit()

    @pyqtSlot()
    def initPatch(self) -> None:
        """Initialize the active sound in RAM to the golden JUNO SPECTRE template."""
        logger.info("Initializing active patch in RAM to JUNO SPECTRE template...")

        # Pause motion playback without destroying the recorded trajectory, and hold
        # engine-driven SysEx for the whole critical section. Recording is left alone.
        motion_was_playing = self.engine.motion.state == RecorderState.PLAYING
        if motion_was_playing:
            self.engine.motion.pause()
            self.transportStateChanged.emit(self.engine.motion.state.value)

        try:
            with self.engine.hold_hardware_writes():
                # 1. Restore the golden image on hardware (one DT1 per region, zero residue).
                #    Falls back to the per-parameter reset sequence if the asset is missing.
                hw_ok = False
                if self.engine.juno:
                    try:
                        hw_ok = self.engine.juno.init_patch()
                    except Exception as e:
                        logger.error(f"Error sending init_patch to synth: {e}")
                if not hw_ok and not self.engine.juno:
                    logger.info("No synth connected; resetting in-memory state only.")

                # 2. Reset in-memory state from the SAME golden image the hardware received,
                #    so UI and synth provably match (decoded blob, or hand-built fallback).
                self.patch_state = PatchState.from_template_file() or PatchState.create_init_patch()

                # 3. Sync tone wave caches from the decoded template
                self._tone_waves = [
                    (t.wave_bank_l, t.wave_num_l) for t in self.patch_state.tones
                ]
                self._cached_tone_wave_data = [
                    self._wave_catalog.get_wave(b, n) for b, n in self._tone_waves
                ]

                # 4. Update patch name & mode
                self._patch_name = self.patch_state.common.name
                self._sound_mode = self.patch_state.sound_mode

                # 5. Reset Vector Engine position and tone levels
                self.engine.set_coordinates(0.5, 0.5)
                self.engine.tone_levels = tuple(t.level for t in self.patch_state.tones)
        finally:
            if motion_was_playing and self.engine.motion.state != RecorderState.PLAYING:
                self.engine.motion.play()
                self.transportStateChanged.emit(self.engine.motion.state.value)

        # 6. Emit all signals to trigger live UI refresh across all tabs and screens
        #    (macro deck values are derived getters, so they refresh automatically)
        self._emit_all_state_signals()
        self.patchInitialized.emit()
        logger.info("Active patch initialization complete.")

    @pyqtSlot(int)
    def setBrightness(self, val: int) -> None:
        clamped = max(10, min(100, int(val)))
        if self._brightness != clamped:
            self._brightness = clamped
            self.brightnessChanged.emit(self._brightness)
        try:
            backlight = getattr(self, "_backlight", None)
            if backlight is not None:
                if not backlight.set_percent(clamped):
                    logger.debug(
                        f"Brightness {clamped}% UI-only "
                        f"(method={getattr(backlight, 'method', 'none')})"
                    )
        except Exception as e:
            logger.debug(f"Brightness hardware apply failed: {e}")

    @pyqtSlot()
    def restartApp(self) -> None:
        """Graceful in-place restart: silence synth, close MIDI, then exec.

        Does NOT quit first — os.execv() replaces the process on success and
        never returns. If exec fails the app keeps running instead of
        black-screening the appliance.
        """
        import os
        import sys

        exe = sys.executable
        if not exe or not os.path.exists(exe):
            logger.error(f"Restart aborted: invalid python executable {exe!r}")
            return
        logger.info("Restarting application...")
        self.powerActionChanged.emit("restarting")
        self._perform_appliance_cleanup("restart")
        argv = [exe] + sys.argv
        try:
            os.execv(exe, argv)
        except Exception as e:
            logger.error(f"Restart execv failed ({argv}): {e}")
            self.powerActionChanged.emit("")
            try:
                if hasattr(self, "_timer") and not self._timer.isActive():
                    self._timer.start()
            except Exception:
                pass

    @pyqtSlot()
    def rebootSystem(self) -> None:
        """Reboot the host OS (Pi appliance). Safe no-op with warning off Linux."""
        self._host_power("reboot")

    @pyqtSlot()
    def shutdownSystem(self) -> None:
        """Power off the host OS (Pi appliance). Safe no-op with warning off Linux."""
        self._host_power("poweroff")

    def _perform_appliance_cleanup(self, reason: str) -> None:
        """Best-effort graceful teardown before restart/reboot/shutdown."""
        try:
            if hasattr(self, "_timer") and self._timer.isActive():
                self._timer.stop()
        except Exception as e:
            logger.debug(f"Cleanup ({reason}): timer stop failed: {e}")
        try:
            juno = getattr(getattr(self, "engine", None), "juno", None)
            midi = getattr(juno, "midi", None) if juno is not None else None
            if midi is not None:
                try:
                    if hasattr(midi, "send_all_notes_off"):
                        midi.send_all_notes_off()
                except Exception as e:
                    logger.debug(f"Cleanup ({reason}): panic failed: {e}")
                try:
                    if hasattr(midi, "close"):
                        midi.close()
                except Exception as e:
                    logger.debug(f"Cleanup ({reason}): MIDI close failed: {e}")
        except Exception as e:
            logger.debug(f"Cleanup ({reason}) failed: {e}")
        try:
            for handler in logging.getLogger().handlers:
                try:
                    handler.flush()
                except Exception:
                    pass
        except Exception:
            pass

    def _host_power(self, action: str, dry_run: bool = False) -> str:
        """Shared systemctl reboot/poweroff helper. Returns outcome string.

        `dry_run=True` performs cleanup-free validation only (for tests).
        """
        import subprocess
        import sys

        if action not in ("reboot", "poweroff"):
            raise ValueError(f"Unknown power action: {action}")
        if dry_run:
            return "dry-run"
        if sys.platform != "linux":
            logger.warning(
                f"{action.upper()} ignored: host power control is Linux-only "
                f"(running on {sys.platform})."
            )
            return "unsupported-platform"
        from PyQt6.QtGui import QGuiApplication

        logger.info(f"Host {action} requested...")
        self.powerActionChanged.emit(action + "ing")
        self._perform_appliance_cleanup(action)
        cmds = [["systemctl", action], ["sudo", "-n", "systemctl", action]]
        last_err = ""
        for cmd in cmds:
            try:
                proc = subprocess.run(cmd, timeout=15, capture_output=True, text=True)
            except FileNotFoundError as e:
                last_err = str(e)
                continue
            except subprocess.TimeoutExpired:
                last_err = f"{' '.join(cmd)} timed out"
                continue
            except Exception as e:
                last_err = str(e)
                continue
            if proc.returncode == 0:
                break
            last_err = (proc.stderr or proc.stdout or f"exit {proc.returncode}").strip()
        else:
            logger.error(f"Host {action} failed: {last_err}")
            self.powerActionChanged.emit("")
            try:
                if hasattr(self, "_timer") and not self._timer.isActive():
                    self._timer.start()
            except Exception:
                pass
            return f"failed: {last_err}"
        try:
            app = QGuiApplication.instance()
            if app:
                app.quit()
        except Exception as e:
            logger.debug(f"Qt quit after {action} failed: {e}")
        return "ok"

    # -------------------------------------------------------------------------
    # Appliance Self-Update slots (git release channel)
    # -------------------------------------------------------------------------

    def _set_updater_busy(self, val: bool) -> None:
        if self._updater_busy != val:
            self._updater_busy = val
            self.updaterBusyChanged.emit(val)

    def _set_updater_log(self, msg: str) -> None:
        if self._updater_log != msg:
            self._updater_log = msg
            self.updaterLogChanged.emit(msg)

    def _set_update_applied(self, val: bool) -> None:
        if self._update_applied != val:
            self._update_applied = val
            self.updateAppliedChanged.emit(val)

    def _refresh_version(self) -> None:
        new_version = self._updater.version
        if new_version != self._version:
            self._version = new_version
            self.versionChanged.emit(self._version)

    def _start_updater_task(self, action: str, work, on_success) -> None:
        """Run a blocking git updater call on a worker thread, reporting via signals."""
        if self._updater_busy:
            logger.debug("Updater task already running, ignoring request")
            return
        self._set_updater_busy(True)
        self._set_updater_log(f"$ {action} ...")

        def finish(log_line: str) -> None:
            self._set_updater_log(log_line)
            self._set_updater_busy(False)

        def runner() -> None:
            try:
                result = work()
            except UpdaterError as e:
                logger.warning(f"Updater '{action}' failed: {e}")
                finish(f"ERROR • {str(e).upper()}")
                return
            except Exception as e:
                logger.exception(f"Updater '{action}' crashed")
                finish(f"ERROR • {str(e).upper()}")
                return
            on_success(result)
            self._refresh_version()

        threading.Thread(target=runner, daemon=True).start()

    @pyqtSlot()
    def checkForUpdates(self) -> None:
        """Fetch origin tags and publish latest release availability to the UI."""

        def on_ok(info: dict) -> None:
            if self._latest_version != info["latest"]:
                self._latest_version = info["latest"]
                self.latestVersionChanged.emit(self._latest_version)
            if self._update_available != info["available"]:
                self._update_available = info["available"]
                self.updateAvailableChanged.emit(self._update_available)
            if info["available"]:
                self._set_updater_log(
                    f"UPDATE AVAILABLE • {info['current']} → {info['latest']} "
                    f"({info['behind_commits']} COMMITS)"
                )
            else:
                self._set_updater_log(f"UP TO DATE • {info['current']}")
            self._set_update_applied(False)
            self._set_updater_busy(False)

        self._start_updater_task("git fetch --tags", lambda: self._updater.check(), on_ok)

    @pyqtSlot()
    def applyLatestRelease(self) -> None:
        """Check out the newest release tag, then require an explicit app restart."""

        def on_ok(result: dict) -> None:
            self._update_available = False
            self.updateAvailableChanged.emit(False)
            if result["changed"]:
                self._set_updater_log(
                    f"RELEASE {result['to']} INSTALLED ({result['from']} → {result['to']}) "
                    f"• TAP RESTART APPLICATION"
                )
                self._set_update_applied(True)
            else:
                self._set_updater_log(f"ALREADY ON RELEASE {result['to']}")
            self._set_updater_busy(False)

        self._start_updater_task("git checkout release", self._updater.apply, on_ok)

    @pyqtSlot()
    def rollbackRelease(self) -> None:
        """Fall back to the previous release tag (detached HEAD checkout)."""

        def on_ok(result: dict) -> None:
            self._set_updater_log(
                f"ROLLED BACK {result['from']} → {result['to']} • TAP RESTART APPLICATION"
            )
            self._update_available = False
            self.updateAvailableChanged.emit(False)
            self._set_update_applied(True)
            self._set_updater_busy(False)

        self._start_updater_task("git rollback", self._updater.rollback, on_ok)
