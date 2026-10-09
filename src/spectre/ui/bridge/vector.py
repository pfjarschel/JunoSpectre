"""Vector bridge mixin: transport, motion recorder, automator, and macro engine."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from PyQt6.QtCore import pyqtProperty, pyqtSignal, pyqtSlot

from ...core.macro_targets import (
    filter_macro_targets,
    get_macro_catalog,
    get_macro_categories,
    macro_delta,
    resolve_sounding,
)
from ...core.patch_state import ToneState
from ...vector.engine import MorphMode, VectorState
from ...vector.math import CrossfadeCurve
from ...vector.motion import AutomatorType, LoopMode, RecorderState, WavetableSweepMode
from .base import BridgeBaseMixin

logger = logging.getLogger(__name__)


class VectorBridgeMixin(BridgeBaseMixin):
    """Vector pad coordinates, playback transport, automator loops, and macros."""

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
    macrosChanged = pyqtSignal()
    curveChanged = pyqtSignal(str)
    activeViewChanged = pyqtSignal(str)

    requestOpenScreensOverlay = pyqtSignal()
    requestOpenWaveBrowser = pyqtSignal(int)
    requestOpenMacroAssign = pyqtSignal(int)
    requestOpenInitPatchModal = pyqtSignal()
    requestOpenSavePatchModal = pyqtSignal()
    requestOpenEnvOverlay = pyqtSignal(str)

    _macro_catalog_by_key: dict | None = None

    def _on_timer_tick(self) -> None:
        """Tick engine time forward to update motion loops and automators."""
        now = time.perf_counter()
        dt = now - self._last_tick_time
        self._last_tick_time = now
        self.engine.update(dt)
        if self.engine.motion.state == RecorderState.RECORDING:
            self.motionPointsChanged.emit()

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

    @classmethod
    def _macroEntry(cls, key: str) -> dict | None:
        if cls._macro_catalog_by_key is None:
            cls._macro_catalog_by_key = {e["key"]: e for e in get_macro_catalog()}
        return cls._macro_catalog_by_key.get(key)

    @staticmethod
    def _expandKey(key: str) -> list[str]:
        if key.startswith("tone.all."):
            suffix = key[len("tone.all."):]
            return [f"tone.{i}.{suffix}" for i in range(1, 5)]
        return [key]

    def _macroLinksFor(self, key: str) -> list[tuple[int, object]]:
        """All (macro_idx, link) pairs addressing a concrete key (incl. via tone.all.*)."""
        out = []
        for mi, slot in enumerate(self.patch_state.macros):
            for link in slot.links:
                if key in self._expandKey(link.target_key):
                    out.append((mi, link))
        return out

    def _readAbsolute(self, key: str) -> float:
        ps = self.patch_state
        try:
            if key == "common.level":
                return float(ps.common.level)
            if key == "common.pan":
                return float(ps.common.pan)
            if key == "common.cutoff_offset":
                return float(ps.common.cutoff_offset)
            if key == "common.resonance_offset":
                return float(ps.common.resonance_offset)
            if key == "common.attack_offset":
                return float(ps.common.attack_offset)
            if key == "common.release_offset":
                return float(ps.common.release_offset)
            if key == "common.portamento_time":
                return float(ps.common.portamento_time)
            if key == "common.analog_feel":
                return float(ps.common.analog_feel)
            if key.startswith("effects."):
                return float(getattr(ps.effects, key.split(".", 1)[1], 0.0))
            if key.startswith("tone."):
                _, idx, param = key.split(".", 2)
                t = ps.get_tone(int(idx))
                return float(self._toneParam(t, param))
            if key == "vector.x":
                return float(self.engine.x)
            if key == "vector.y":
                return float(self.engine.y)
            if key == "vector.w":
                return float(self.engine.w)
            if key == "vector.speed":
                return float(self.engine.motion.speed)
            if key == "vector.bpm":
                return float(self.bpm)
        except (ValueError, AttributeError, IndexError):
            pass
        return 0.0

    @staticmethod
    def _toneParam(t: ToneState, param: str) -> float:
        mapping = {
            "tvf_cutoff": t.tvf_cutoff, "tvf_resonance": t.tvf_resonance,
            "tvf_env_depth": t.tvf_env_depth, "tvf_attack": t.tvf_t1,
            "tvf_decay": t.tvf_t2, "tvf_sustain": t.tvf_l3, "tvf_release": t.tvf_t4,
            "tva_level": t.level, "tva_pan": t.pan,
            "tva_attack": t.tva_t1, "tva_decay": t.tva_t2,
            "tva_sustain": t.tva_l3, "tva_release": t.tva_t4,
            "pitch_coarse": t.coarse_tune, "pitch_fine": t.fine_tune,
            "lfo1_rate": t.lfo1_rate, "lfo1_pitch_depth": t.lfo1_pitch_depth,
            "lfo1_tvf_depth": t.lfo1_tvf_depth, "lfo1_tva_depth": t.lfo1_tva_depth,
            "lfo1_pan_depth": t.lfo1_pan_depth, "lfo2_rate": t.lfo2_rate,
            "lfo2_pitch_depth": t.lfo2_pitch_depth, "lfo2_tvf_depth": t.lfo2_tvf_depth,
            "lfo2_tva_depth": t.lfo2_tva_depth, "lfo2_pan_depth": t.lfo2_pan_depth,
            "chorus_send": t.chorus_send, "reverb_send": t.reverb_send,
            "output_level": t.output_level,
        }
        return float(mapping.get(param, 0.0))

    def _ensureBase(self, key: str) -> float:
        bases = self.patch_state.macro_bases
        if key not in bases:
            bases[key] = float(self._readAbsolute(key))
        return float(bases[key])

    def _contributions(self, key: str) -> list[float]:
        entry = self._macroEntry(key)
        span = float(entry["span"]) if entry else 127.0
        out = []
        for mi, link in self._macroLinksFor(key):
            v = self.patch_state.macros[mi].value
            out.append(macro_delta(span, link.polarity, link.depth, v))
        return out

    def _recomputeTarget(self, key: str) -> float:
        entry = self._macroEntry(key)
        lo = float(entry["min"]) if entry else 0.0
        hi = float(entry["max"]) if entry else 127.0
        base = self._ensureBase(key)
        sounding = resolve_sounding(base, self._contributions(key), lo, hi)
        self._applyAbsolute(key, sounding)
        return sounding

    def _applyAbsolute(self, key: str, sounding: float) -> None:
        """Write sounding value to patch_state + synth. Never touches bases."""
        ps = self.patch_state
        juno = self.engine.juno
        is_int = not key.startswith("vector.")
        val = sounding
        if key.startswith("vector."):
            if key == "vector.x":
                self.engine.set_coordinates(max(0.0, min(1.0, val)), self.engine.y)
            elif key == "vector.y":
                self.engine.set_coordinates(self.engine.x, max(0.0, min(1.0, val)))
            elif key == "vector.w":
                self.engine.set_wavetable_pos(max(0.0, min(1.0, val)))
            elif key == "vector.speed":
                self.engine.motion.speed = max(0.25, min(4.0, val))
                self.speedChanged.emit(self.engine.motion.speed)
            elif key == "vector.bpm":
                self._apply_tempo(val)
            return
        iv = int(round(max(0, val))) if is_int else val
        try:
            if key == "common.level":
                ps.common.level = max(0, min(127, iv))
                if juno:
                    juno.set_patch_param("level", ps.common.level)
            elif key == "common.pan":
                ps.common.pan = max(0, min(127, iv))
            elif key == "common.cutoff_offset":
                ps.common.cutoff_offset = max(1, min(127, iv))
                for t in ps.tones:
                    pass
                if juno:
                    juno.set_patch_offsets(cutoff=ps.common.cutoff_offset)
            elif key == "common.resonance_offset":
                ps.common.resonance_offset = max(1, min(127, iv))
                if juno:
                    juno.set_patch_offsets(resonance=ps.common.resonance_offset)
            elif key == "common.attack_offset":
                ps.common.attack_offset = max(1, min(127, iv))
                if juno:
                    juno.set_patch_offsets(attack=ps.common.attack_offset)
            elif key == "common.release_offset":
                ps.common.release_offset = max(1, min(127, iv))
                if juno:
                    juno.set_patch_offsets(release=ps.common.release_offset)
            elif key == "common.portamento_time":
                ps.common.portamento_time = max(0, min(127, iv))
                if juno:
                    juno.set_portamento(ps.common.portamento_switch, time=ps.common.portamento_time)
            elif key == "common.analog_feel":
                ps.common.analog_feel = max(0, min(127, iv))
                if juno:
                    juno.set_patch_analog_feel(ps.common.analog_feel)
            elif key.startswith("effects."):
                field = key.split(".", 1)[1]
                if hasattr(ps.effects, field):
                    setattr(ps.effects, field, max(0, min(127, iv)))
                    self._pushEffect(key, iv)
            elif key.startswith("tone."):
                _, idx, param = key.split(".", 2)
                self._applyToneParam(int(idx), param, iv)
        except (ValueError, AttributeError, IndexError) as e:
            logger.debug(f"macro apply failed for {key}: {e}")

    def _pushEffect(self, key: str, iv: int) -> None:
        juno = self.engine.juno
        if not juno:
            return
        try:
            eff = self.patch_state.effects
            if key == "effects.chorus_level":
                juno.set_chorus(eff.chorus_type, level=eff.chorus_level)
            elif key == "effects.reverb_level":
                juno.set_reverb(eff.reverb_type, level=eff.reverb_level)
            elif key.startswith("effects.chorus_"):
                juno.set_chorus_param(key.split("_", 1)[1], iv)
            elif key.startswith("effects.reverb_"):
                juno.set_reverb_param(key.split("_", 1)[1], iv)
            elif key.startswith("effects.mfx_"):
                send = {"effects.mfx_dry_send": "dry", "effects.mfx_chorus_send": "chorus",
                        "effects.mfx_reverb_send": "reverb"}.get(key)
                if send:
                    juno.set_mfx_send(send, iv)
        except Exception as e:
            logger.debug(f"macro effect push failed for {key}: {e}")

    def _applyToneParam(self, tone_idx: int, param: str, iv: int) -> None:
        ps = self.patch_state
        t = ps.get_tone(tone_idx)
        juno = self.engine.juno
        if param == "tvf_cutoff":
            t.tvf_cutoff = max(0, min(127, iv))
            if juno:
                juno.set_tone_tvf(tone_idx, cutoff=t.tvf_cutoff)
        elif param == "tvf_resonance":
            t.tvf_resonance = max(0, min(127, iv))
            if juno:
                juno.set_tone_tvf(tone_idx, resonance=t.tvf_resonance)
        elif param == "tvf_env_depth":
            t.tvf_env_depth = max(1, min(127, iv))
            if juno:
                juno.set_tone_tvf(tone_idx, env_depth=t.tvf_env_depth)
        elif param in ("tvf_attack", "tvf_decay", "tvf_sustain", "tvf_release"):
            setattr(t, param, max(0, min(127, iv)))
            self._push_tvf_env(t)
        elif param == "tva_level":
            t.level = max(0, min(127, iv))
            if not t.muted:
                self.engine.set_tone_level(tone_idx, t.level)
                if juno:
                    juno.set_tone_level(tone_idx, t.level)
        elif param == "tva_pan":
            t.pan = max(0, min(127, iv))
            if juno:
                juno.set_tone_tva(tone_idx, pan=t.pan)
        elif param in ("tva_attack", "tva_decay", "tva_sustain", "tva_release"):
            setattr(t, {"tva_attack": "tva_t1", "tva_decay": "tva_t2",
                        "tva_sustain": "tva_l3", "tva_release": "tva_t4"}[param],
                    max(0, min(127, iv)))
            self._push_tva_env(t)
        elif param == "pitch_coarse":
            t.coarse_tune = max(16, min(112, iv))
            if juno:
                juno.set_tone_pitch(tone_idx, coarse=t.coarse_tune)
        elif param == "pitch_fine":
            t.fine_tune = max(14, min(114, iv))
            if juno:
                juno.set_tone_pitch(tone_idx, fine=t.fine_tune)
        elif param.startswith("lfo1_") or param.startswith("lfo2_"):
            self._applyLfoParam(t, param, iv)
        elif param == "chorus_send":
            t.chorus_send = max(0, min(127, iv))
            if juno:
                juno.set_tone_param(tone_idx, 0x000D, t.chorus_send)
        elif param == "reverb_send":
            t.reverb_send = max(0, min(127, iv))
            if juno:
                juno.set_tone_param(tone_idx, 0x000E, t.reverb_send)
        elif param == "output_level":
            t.output_level = max(0, min(127, iv))
            if juno:
                juno.set_tone_param(tone_idx, 0x000C, t.output_level)

    def _applyLfoParam(self, t: ToneState, param: str, iv: int) -> None:
        juno = self.engine.juno
        lfo = 1 if param.startswith("lfo1_") else 2
        kind = param.split("_", 1)[1]
        if kind == "rate":
            if lfo == 1:
                t.lfo1_rate = max(0, min(127, iv))
            else:
                t.lfo2_rate = max(0, min(127, iv))
            if juno:
                juno.set_tone_lfo(t.tone_index, lfo_index=lfo,
                                  rate=t.lfo1_rate if lfo == 1 else t.lfo2_rate)
        else:
            depth = max(1, min(127, iv))
            attr = f"lfo{lfo}_{kind}"
            if hasattr(t, attr):
                setattr(t, attr, depth)
            if juno:
                juno.set_tone_lfo(t.tone_index, lfo_index=lfo, **{kind: depth})

    def _rebaseDirect(self, keys_bases: list[tuple[str, float]]) -> None:
        """Treat direct edits as new bases (semantics ii). No-op for unlinked keys."""
        touched: set[str] = set()
        for key, new_base in keys_bases:
            if not self._macroLinksFor(key):
                continue
            entry = self._macroEntry(key)
            lo = float(entry["min"]) if entry else 0.0
            hi = float(entry["max"]) if entry else 127.0
            self.patch_state.macro_bases[key] = max(lo, min(hi, float(new_base)))
            self._recomputeTarget(key)
            touched.add(key)
        if touched:
            self._emitForMacroKeys(touched)

    def _rebaseLfoParam(self, lfo_idx: int, param: str, targets: list) -> None:
        """Rebase helper for setLfoParam (depths raw=centered, rate absolute)."""
        if param in ("wave", "delay_time", "fade_mode", "fade_time"):
            return
        pairs = []
        for t in targets:
            if param == "rate":
                key = f"tone.{t.tone_index}.lfo{lfo_idx}_rate"
                base = t.lfo1_rate if lfo_idx == 1 else t.lfo2_rate
            else:
                key = f"tone.{t.tone_index}.lfo{lfo_idx}_{param}"
                attr = f"lfo{lfo_idx}_{param}"
                base = float(getattr(t, attr, 64))
            pairs.append((key, base))
        if pairs:
            self._rebaseDirect(pairs)

    def _rebaseChorusParam(self, param: str) -> None:
        mapping = {"level": ("effects.chorus_level", self.patch_state.effects.chorus_level),
                   "rate": ("effects.chorus_rate", self.patch_state.effects.chorus_rate),
                   "depth": ("effects.chorus_depth", self.patch_state.effects.chorus_depth),
                   "preDelay": ("effects.chorus_predelay", self.patch_state.effects.chorus_predelay),
                   "feedback": ("effects.chorus_feedback", self.patch_state.effects.chorus_feedback)}
        if param in mapping:
            key, base = mapping[param]
            self._rebaseDirect([(key, base)])

    def _rebaseReverbParam(self, param: str) -> None:
        mapping = {"level": ("effects.reverb_level", self.patch_state.effects.reverb_level),
                   "time": ("effects.reverb_time", self.patch_state.effects.reverb_time),
                   "damp": ("effects.reverb_damp", self.patch_state.effects.reverb_damp),
                   "preDelay": ("effects.reverb_predelay", self.patch_state.effects.reverb_predelay),
                   "diffusion": ("effects.reverb_diffusion", self.patch_state.effects.reverb_diffusion),
                   "tone": ("effects.reverb_tone", self.patch_state.effects.reverb_tone)}
        if param in mapping:
            key, base = mapping[param]
            self._rebaseDirect([(key, base)])

    def _emitForMacroKeys(self, keys: set[str]) -> None:
        if any(k.startswith("tone.") and ".tvf_" in k or k.startswith("common.cutoff") or k.startswith("common.resonance") for k in keys):
            try:
                self.masterCutoffChanged.emit(self.masterCutoff)
                self.masterResoChanged.emit(self.masterReso)
            except Exception:
                pass
        if any("tva_" in k or "tva-level" in k or k.endswith("tva_level") or "attack" in k or "release" in k for k in keys):
            try:
                self.masterAttackChanged.emit(self.masterAttack)
                self.masterReleaseChanged.emit(self.masterRelease)
                self.tvaLevelChanged.emit(self.tvaLevel)
            except Exception:
                pass
        if any(k.startswith("effects.chorus") for k in keys):
            self.chorusParamsChanged.emit()
        if any(k.startswith("effects.reverb") for k in keys):
            self.reverbParamsChanged.emit()
        if any(k.startswith("effects.mfx") for k in keys):
            self.mfxParamsChanged.emit()
        if any(k.startswith("tone.") for k in keys):
            try:
                self.toneLevelsChanged.emit(*[t.level for t in self.patch_state.tones])
            except Exception:
                pass
            self.lfoParamsChanged.emit()
            self.pitchCoarseChanged.emit(self.pitchCoarse)
            self.pitchFineChanged.emit(self.pitchFine)
        self.macrosChanged.emit()

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
        self.mfxParamsChanged.emit()
        self.mfxValuesChanged.emit()
        self.matrixCtrlChanged.emit()
        self.stepLfoChanged.emit()
        self.perfPartsChanged.emit()
        try:
            self.perfFxChanged.emit()
        except Exception:
            pass
        self.vaParamsChanged.emit()
        try:
            self.playlistChanged.emit()
        except Exception:
            pass
        self.macrosChanged.emit()
        self.routingChanged.emit()

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
        """The one global tempo, owned by the sequencer song (saved with songs/setlists)."""
        if hasattr(self, "sequencer"):
            return self.sequencer.bpm
        return self.engine.motion.bpm

    def _apply_tempo(self, bpm_val: float) -> float:
        """Set the global tempo: sequencer clock and vector motion follow the same value."""
        bpm_val = max(20.0, min(300.0, float(bpm_val)))
        if hasattr(self, "sequencer"):
            self.sequencer.set_bpm(bpm_val)
            bpm_val = self.sequencer.bpm
        self.engine.motion.bpm = bpm_val
        self.bpmChanged.emit(bpm_val)
        return bpm_val

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

    @activeView.setter
    def activeView(self, view: str) -> None:
        self.setActiveView(view)


    @pyqtProperty(str, notify=curveChanged)
    def curve(self) -> str:
        return self.engine.curve.value


    @pyqtProperty("QVariantList", notify=macrosChanged)
    def macroNames(self) -> list:
        return [s.name for s in self.patch_state.macros]

    @pyqtProperty("QVariantList", notify=macrosChanged)
    def macroValues(self) -> list:
        return [float(s.value) for s in self.patch_state.macros]

    @pyqtProperty("QVariantList", notify=macrosChanged)
    def macroLinkCounts(self) -> list:
        return [len(s.links) for s in self.patch_state.macros]

    @pyqtSlot(int, result="QVariantList")
    def getMacroLinks(self, index: int) -> list:
        """Assigned targets for macro 1..8 with live sounding values."""
        if not (1 <= index <= len(self.patch_state.macros)):
            return []
        out = []
        for pos, link in enumerate(self.patch_state.macros[index - 1].links):
            entry = self._macroEntry(link.target_key)
            for concrete in self._expandKey(link.target_key):
                out.append({
                    "pos": pos,
                    "key": link.target_key,
                    "concrete": concrete,
                    "title": entry["title"] if entry else link.target_key,
                    "category": entry["category"] if entry else "",
                    "polarity": link.polarity,
                    "depth": link.depth,
                    "span": float(entry["span"]) if entry else 127.0,
                    "min": float(entry["min"]) if entry else 0.0,
                    "max": float(entry["max"]) if entry else 127.0,
                    "liveValue": self._readAbsolute(concrete),
                })
                break  # one row per link (all-variant shows first live value)
        return out

    @pyqtSlot(str, str, result="QVariantList")
    def getMacroTargets(self, category: str = "ALL", query: str = "") -> list:
        return filter_macro_targets(category, query)

    @pyqtSlot(result="QVariantList")
    def getMacroCategories(self) -> list:
        return get_macro_categories()

    @pyqtSlot(int, str)
    def setMacroName(self, index: int, name: str) -> None:
        if 1 <= index <= len(self.patch_state.macros):
            clean = (name or "").strip().upper()[:14] or f"M{index}"
            self.patch_state.macros[index - 1].name = clean
            self.macrosChanged.emit()

    @pyqtSlot(int, str)
    def addMacroTarget(self, index: int, key: str) -> None:
        """Add link with defaults (polarity +, depth 50%). No duplicates."""
        if not (1 <= index <= len(self.patch_state.macros)):
            return
        if self._macroEntry(key) is None:
            return
        slot = self.patch_state.macros[index - 1]
        if any(li.target_key == key for li in slot.links):
            return
        from ...core.patch_state import MacroLink

        slot.links.append(MacroLink(key, 1, 0.5))
        for concrete in self._expandKey(key):
            self._ensureBase(concrete)
        self._recomputeForMacro(index - 1)
        self.macrosChanged.emit()

    @pyqtSlot(int, int)
    def removeMacroTarget(self, index: int, pos: int) -> None:
        if 1 <= index <= len(self.patch_state.macros):
            slot = self.patch_state.macros[index - 1]
            if 0 <= pos < len(slot.links):
                slot.links.pop(pos)
                self.macrosChanged.emit()

    @pyqtSlot(int, int, int, float)
    def setMacroLink(self, index: int, pos: int, polarity: int, depth: float) -> None:
        if 1 <= index <= len(self.patch_state.macros):
            slot = self.patch_state.macros[index - 1]
            if 0 <= pos < len(slot.links):
                link = slot.links[pos]
                link.polarity = 1 if polarity >= 0 else -1
                link.depth = max(0.0, min(1.0, float(depth)))
                self._recomputeForMacro(index - 1)
                self.macrosChanged.emit()

    @pyqtSlot(int, float)
    def setMacro(self, index: int, value: float) -> None:
        """Drive macro knob 1..8 (value in [-1, 1]) with summed fan-out."""
        if not (1 <= index <= len(self.patch_state.macros)):
            return
        slot = self.patch_state.macros[index - 1]
        slot.value = max(-1.0, min(1.0, float(value)))
        self._recomputeForMacro(index - 1)
        self.macrosChanged.emit()

    def _recomputeForMacro(self, macro_idx: int) -> None:
        touched: set[str] = set()
        for link in self.patch_state.macros[macro_idx].links:
            for concrete in self._expandKey(link.target_key):
                self._ensureBase(concrete)
                self._recomputeTarget(concrete)
                touched.add(concrete)
        if touched:
            self._emitForMacroKeys(touched)

    @pyqtSlot(int)
    def openMacroAssign(self, index: int) -> None:
        self.requestOpenMacroAssign.emit(max(1, min(8, int(index))))

    @pyqtSlot(float, float)
    def setCoordinates(self, x: float, y: float) -> None:
        """Update 2D vector coordinates or guide automator orbit center."""
        if self.engine.motion.automator != AutomatorType.NONE and self.engine.motion.automator != AutomatorType.CIRCLE:
            self.engine.motion.set_orbit_center(x, y)
            self.attractorChanged.emit(self.engine.motion.center_x, self.engine.motion.center_y)
        self.engine.set_coordinates(x, y, record_gesture=True)
        self._rebaseDirect([("vector.x", self.engine.x), ("vector.y", self.engine.y)])

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
        self._rebaseDirect([("vector.w", self.engine.w)])

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
        self._rebaseDirect([("vector.speed", self.engine.motion.speed)])
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
        """Update the global tempo BPM."""
        bpm_val = self._apply_tempo(bpm_val)
        self._rebaseDirect([("vector.bpm", bpm_val)])

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
        elif v in ("PERF-MIXER", "PERFMIXER", "PERF MIXER"):
            v = "PERFORMANCE"
        elif v in ("MIDI-LEARN", "MIDILEARN"):
            v = "MIDI LEARN"
        elif v in ("HARDWARE CONFIG", "HARDWARE_CONFIG"):
            v = "HARDWARE"
        elif v in ("LIVE MODE", "LIVE-MODE", "SESSION", "SESSION MATRIX"):
            v = "LIVE"
        elif v in ("SET LIST", "SET-LIST", "SET_LIST", "PLAYLIST"):
            v = "SETLIST"
        elif v in ("STEP EDITOR", "STEP-EDITOR", "STEP_EDITOR", "SEQ", "STEP SEQUENCER"):
            v = "SEQUENCER"

        if self._active_view != v:
            if v == "LIBRARIAN" and self._active_view != "LIBRARIAN":
                self._view_before_librarian = self._active_view
                self._capture_librarian_entry()
            elif self._active_view == "LIBRARIAN" and self._pick_target:
                # Leaving the Librarian any other way ends part picking too.
                self._pick_target = 0
                self.librarianPickChanged.emit()

            self._active_view = v
            if v == "VECTOR":
                self.setMorphMode("vector_2d")
            elif v == "WAVETABLE":
                self.setMorphMode("wavetable_1d")
            if hasattr(self, "recorder"):
                self.recorder.audition_enabled = v == "SEQUENCER"
            self.activeViewChanged.emit(self._active_view)
            self._update_telemetry_polling()

    def _capture_librarian_entry(self) -> None:
        """Snapshot the sounding state so Cancel can revert auditions."""
        try:
            import copy

            from ...core.spectre_format import patch_state_to_dict
            self._librarian_entry_snapshot = {
                "state": patch_state_to_dict(self.patch_state),
                "patch_name": str(self._patch_name or ""),
                "sound_mode": str(self._sound_mode or "PATCH"),
                "current_ref": copy.deepcopy(self._current_ref),
                "part_snapshots": copy.deepcopy(self._part_snapshots or {}),
            }
        except Exception as e:
            logger.debug(f"librarian entry snapshot failed: {e}")
            self._librarian_entry_snapshot = None

    def _discard_librarian_entry(self) -> None:
        self._librarian_entry_snapshot = None

    @pyqtSlot()
    def toggleLibrarian(self) -> None:
        """Enter the Librarian, or confirm-close it (OK semantics).

        Closing goes to the pending view proposed by the last audition
        (mixer for performances, engine view for patches), else back to
        the view open before the Librarian. OK keeps auditioned sounds.
        """
        if self._active_view == "LIBRARIAN":
            dest = str(self._pending_view or "") or getattr(self, "_view_before_librarian", "") or "JUNO PCM"
            self._pending_view = ""
            self._pick_target = 0
            self._discard_librarian_entry()
            try:
                self.librarianPickChanged.emit()
            except Exception:
                pass
            self.setActiveView(dest)
        else:
            self.setActiveView("LIBRARIAN")

    @pyqtSlot()
    def cancelLibrarian(self) -> None:
        """Close the Librarian reverting auditioned sounds (Cancel).

        Restores the entry snapshot in app state and on the synth, then
        returns to the previous view.
        """
        if self._active_view == "LIBRARIAN":
            self._pending_view = ""
            self._pick_target = 0
            try:
                self.librarianPickChanged.emit()
            except Exception:
                pass
            try:
                self._restore_librarian_entry()
            except Exception as e:
                logger.debug(f"librarian cancel restore failed: {e}")
            self._discard_librarian_entry()
            self.setActiveView(getattr(self, "_view_before_librarian", "") or "JUNO PCM")

    def _restore_librarian_entry(self) -> None:
        """Revert app + synth sound to the Librarian-entry snapshot."""
        snap = self._librarian_entry_snapshot
        if not isinstance(snap, dict) or not isinstance(snap.get("state"), dict):
            return
        from ...core.spectre_format import patch_state_from_dict
        state = patch_state_from_dict(snap["state"])
        self.patch_state = state
        self._patch_name = str(snap.get("patch_name") or state.common.name or "")
        self._sound_mode = str(snap.get("sound_mode") or "PATCH")
        self.patch_state.sound_mode = self._sound_mode
        self._current_ref = snap.get("current_ref")
        try:
            self.currentRefChanged.emit()
        except Exception:
            pass
        self._part_snapshots = dict(snap.get("part_snapshots") or {})
        juno = self.juno
        if juno is not None:
            ref = self._current_ref or {}
            if ref.get("source") in ("factory", "synth-user"):
                # Slot sounds reload fully on the hardware via reselect.
                self._reselect_slot_sound(ref, self._sound_mode)
            elif (ref.get("source"), ref.get("kind")) == ("file", "performance"):
                self._restore_performance_sound(state, self._part_snapshots)
            else:
                # File patch or unsaved edit: re-push the entry image.
                if self._sound_mode == "PERFORM":
                    self._restore_performance_sound(state, self._part_snapshots)
                elif getattr(state, "raw_regions", None):
                    try:
                        from ...core.protocol import SoundMode
                        juno.set_sound_mode(SoundMode.PATCH)
                        blob = juno.encode_patch_sysex(state)
                        juno.apply_sysex_blob(blob)
                    except Exception as e:
                        logger.debug(f"cancel restore: patch push failed: {e}")
        try:
            self.refreshPartFileStatus()
        except Exception:
            pass
        self._emit_all_state_signals()

    def _reselect_slot_sound(self, ref: dict, sound_mode: str) -> bool:
        """Lean Bank/PC reselect of a slot sound (no reads, no navigation)."""
        juno = self.juno
        if juno is None:
            return False
        try:
            import mido as _mido

            from ...core.protocol import SoundMode
            midi = getattr(juno, "midi", None)
            out = getattr(midi, "juno_out", None) if midi is not None else None
            if out is None or getattr(out, "closed", False):
                return False
            kind = str(ref.get("kind") or "patch")
            msb, lsb, pc = int(ref.get("msb", 0)), int(ref.get("lsb", 0)), int(ref.get("pc", 0))
            if kind == "performance":
                juno.set_sound_mode(SoundMode.PERFORM)
                out.send(_mido.Message("control_change", channel=15, control=0, value=msb))
                out.send(_mido.Message("control_change", channel=15, control=32, value=lsb))
                out.send(_mido.Message("program_change", channel=15, program=pc))
            else:
                try:
                    juno.set_sound_mode(SoundMode[str(sound_mode).upper()])
                except (KeyError, ValueError):
                    juno.set_sound_mode(SoundMode.PATCH)
                out.send(_mido.Message("control_change", channel=0, control=0, value=msb))
                out.send(_mido.Message("control_change", channel=0, control=32, value=lsb))
                out.send(_mido.Message("program_change", channel=0, program=pc))
            try:
                juno.invalidate_cache()
            except AttributeError:
                pass
            return True
        except Exception as e:
            logger.debug(f"cancel restore: slot reselect failed: {e}")
            return False

    def _restore_performance_sound(self, state, part_snapshots: dict) -> None:
        """Restore a performance sound: mixer selects sync, images queued."""
        from ...core.spectre_format import load_spectre, patch_state_from_dict
        juno = self.juno
        if juno is None:
            return
        try:
            from ...core.protocol import SoundMode
            juno.set_sound_mode(SoundMode.PERFORM)
        except Exception as e:
            logger.debug(f"cancel restore: mode switch failed: {e}")
        for p in state.perf_parts:
            try:
                juno.set_perf_part_patch(p.part_index, p.patch_msb, p.patch_lsb, p.patch_pc)
                juno.set_perf_part_level(p.part_index, p.volume)
                juno.set_perf_part_pan(p.part_index, p.pan)
                juno.set_perf_part_mute(p.part_index, p.muted)
                juno.set_perf_zone(p.part_index,
                                   p.key_low, p.key_high, p.zone_switch, p.zone_octave)
            except Exception as e:
                logger.debug(f"cancel restore: part {p.part_index} failed: {e}")
                break
        try:
            solos = [p.part_index for p in state.perf_parts if p.solo]
            juno.set_perf_solo(solos[-1] if solos else 0)
        except Exception as e:
            logger.debug(f"cancel restore: solo failed: {e}")
        jobs = []
        jobbed = set()
        for p in state.perf_parts:
            link = str(getattr(p, "patch_file", "") or "")
            image = None
            if link and Path(link).is_file():
                try:
                    image = load_spectre(link)["patch_state"]
                except Exception as e:
                    logger.debug(f"cancel restore: link unreadable: {e}")
            if image is None:
                snap = (part_snapshots or {}).get(str(p.part_index))
                if isinstance(snap, dict):
                    try:
                        image = patch_state_from_dict(snap)
                    except Exception as e:
                        logger.debug(f"cancel restore: bad snapshot: {e}")
            if image is not None:
                jobs.append(("image", p.part_index, image))
                jobbed.add(p.part_index)
        if getattr(state, "raw_regions", None):
            try:
                active = max(1, min(16, int(getattr(state, "active_perf_part", 1))))
                if active not in jobbed:
                    jobs.append(("image", active, state))
            except Exception as e:
                logger.debug(f"cancel restore: active image failed: {e}")
        self._queue_push_jobs(jobs)

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
        self._rebaseDirect([(f"tone.{max(1, min(4, tone_number))}.tva_level", clamped)])
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
        self._rebaseDirect([(f"tone.{t.tone_index}.tva_level", clamped) for t in targets])
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


