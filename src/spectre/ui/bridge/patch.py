"""Patch bridge mixin: Tone TVF, TVA, pitch, envelopes, waves, MFX, master FX, EQ, and sculptor."""

from __future__ import annotations

import logging
import threading
from typing import Optional

from PyQt6.QtCore import pyqtProperty, pyqtSignal, pyqtSlot

from ...core.env_presets import env_preset_names, get_env_preset
from ...core.mfx_catalog import (
    EQ_PARAMETRIC_PRESETS,
    SPECTRUM_PRESETS,
    get_mfx_algo,
    get_mfx_categories,
    get_mfx_light_catalog,
)
from ...core.patch_state import (
    LFO_FADE_MODE_NAMES,
    LFO_WAVE_NAMES,
    TVF_TYPE_NAMES,
    PatchState,
    ToneState,
)
from ...core.routing import (
    ASSIGN_DEFER,
    TONE_ASSIGNS,
    TONE_SEND_ATTRS,
    build_graph,
    is_direct,
    mfx_chain,
    tone_send_attrs,
    tone_sends,
)
from .base import BridgeBaseMixin

logger = logging.getLogger(__name__)


class PatchBridgeMixin(BridgeBaseMixin):
    """Patch parameter editing, 4-tone sculpting, envelopes, master FX, and routing."""

    selectedToneChanged = pyqtSignal(int)
    linkedModeChanged = pyqtSignal(bool)
    toneLevelsChanged = pyqtSignal(int, int, int, int)
    toneWavesChanged = pyqtSignal()
    toneMutesChanged = pyqtSignal()
    tvfCutoffChanged = pyqtSignal(int)
    tvfResonanceChanged = pyqtSignal(int)
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
    pitchEnvChanged = pyqtSignal()
    envShapeChanged = pyqtSignal(str)
    chorusParamsChanged = pyqtSignal()
    reverbParamsChanged = pyqtSignal()
    mfxParamsChanged = pyqtSignal()
    mfxValuesChanged = pyqtSignal()
    matrixCtrlChanged = pyqtSignal()
    stepLfoChanged = pyqtSignal()
    vaParamsChanged = pyqtSignal()
    routingChanged = pyqtSignal()
    routingGraphChanged = pyqtSignal()
    masterCutoffChanged = pyqtSignal(int)
    masterResoChanged = pyqtSignal(int)
    masterAttackChanged = pyqtSignal(int)
    masterReleaseChanged = pyqtSignal(int)
    masterLevelChanged = pyqtSignal(int)
    patchInfoChanged = pyqtSignal(str, str)
    patchInitialized = pyqtSignal()
    syncBusyChanged = pyqtSignal(bool)

    @pyqtProperty(bool, notify=syncBusyChanged)
    def syncBusy(self) -> bool:
        return self._sync_busy

    def _set_sync_busy(self, busy: bool) -> None:
        if self._sync_busy != busy:
            self._sync_busy = busy
            try:
                self.syncBusyChanged.emit(busy)
            except Exception as e:
                logger.debug(f"Failed to emit syncBusyChanged: {e}")

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

    @pyqtProperty(int, notify=selectedToneChanged)
    def selectedTone(self) -> int:
        return self._selected_tone

    @pyqtProperty(bool, notify=linkedModeChanged)
    def linkedMode(self) -> bool:
        return self._linked_mode

    @pyqtProperty(str, notify=patchInfoChanged)
    def patchName(self) -> str:
        return self._patch_name

    @pyqtProperty(str, notify=patchInfoChanged)
    def soundMode(self) -> str:
        return self._sound_mode

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

    @pyqtProperty("QVariantList", notify=toneWavesChanged)
    def toneWaveData(self) -> list:
        return self._cached_tone_wave_data

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

    @pyqtProperty(int, notify=chorusParamsChanged)
    def chorusType(self) -> int:
        return self._cho_view()[0]

    @pyqtProperty(int, notify=chorusParamsChanged)
    def chorusLevel(self) -> int:
        return self._cho_view()[1]

    @pyqtProperty(int, notify=chorusParamsChanged)
    def chorusToReverb(self) -> int:
        return self._cho_view()[2]

    @pyqtProperty(int, notify=chorusParamsChanged)
    def chorusRate(self) -> int:
        return self._cho_view()[3]

    @pyqtProperty(int, notify=chorusParamsChanged)
    def chorusDepth(self) -> int:
        return self._cho_view()[4]

    @pyqtProperty(int, notify=chorusParamsChanged)
    def chorusPreDelay(self) -> int:
        return self._cho_view()[5]

    @pyqtProperty(int, notify=chorusParamsChanged)
    def chorusFeedback(self) -> int:
        return self._cho_view()[6]

    @pyqtProperty(int, notify=reverbParamsChanged)
    def reverbType(self) -> int:
        return self._rev_view()[0]

    @pyqtProperty(int, notify=reverbParamsChanged)
    def reverbLevel(self) -> int:
        return self._rev_view()[1]

    @pyqtProperty(int, notify=reverbParamsChanged)
    def reverbTime(self) -> int:
        return self._rev_view()[3]

    @pyqtProperty(int, notify=reverbParamsChanged)
    def reverbDamp(self) -> int:
        return self._rev_view()[4]

    @pyqtProperty(int, notify=reverbParamsChanged)
    def reverbPreDelay(self) -> int:
        return self._rev_view()[2]

    @pyqtProperty(int, notify=reverbParamsChanged)
    def reverbDiffusion(self) -> int:
        return self._rev_view()[5]

    @pyqtProperty(int, notify=reverbParamsChanged)
    def reverbTone(self) -> int:
        return self._rev_view()[6]

    @pyqtProperty("QVariantList", constant=True)
    def mfxCatalog(self) -> list:
        """Lightweight catalog (id, name, cat only); params are fetched per-algo."""
        return get_mfx_light_catalog("ALL")

    @pyqtProperty("QVariantList", constant=True)
    def mfxCategories(self) -> list:
        return get_mfx_categories()

    @pyqtProperty("QVariantList", constant=True)
    def eqParametricPresets(self) -> list:
        """Curve presets for MFX 01 EQUALIZER (see mfx_catalog)."""
        return [dict(p) for p in EQ_PARAMETRIC_PRESETS]

    @pyqtProperty("QVariantList", constant=True)
    def spectrumPresets(self) -> list:
        """Curve presets for MFX 02 SPECTRUM (see mfx_catalog)."""
        return [dict(p) for p in SPECTRUM_PRESETS]

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
        return list(self._mfx_view()[5])

    @pyqtProperty(int, notify=mfxParamsChanged)
    def mfxAlgoId(self) -> int:
        return self._mfx_view()[0]

    @pyqtProperty(bool, notify=mfxParamsChanged)
    def mfxBypassed(self) -> bool:
        return self._mfx_view()[1]

    @pyqtProperty(int, notify=mfxParamsChanged)
    def mfxDrySend(self) -> int:
        return self._mfx_view()[2]

    @pyqtProperty(int, notify=mfxParamsChanged)
    def mfxChorusSend(self) -> int:
        return self._mfx_view()[3]

    @pyqtProperty(int, notify=mfxParamsChanged)
    def mfxReverbSend(self) -> int:
        return self._mfx_view()[4]

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
        """Chorus sends in effect (the pair each tone's route uses)."""
        return [tone_sends(self.patch_state.common, t)[0] for t in self.patch_state.tones]

    @pyqtProperty("QVariantList", notify=routingChanged)
    def toneReverbSends(self) -> list:
        return [tone_sends(self.patch_state.common, t)[1] for t in self.patch_state.tones]

    @pyqtProperty("QVariantList", notify=routingGraphChanged)
    def routingPitfalls(self) -> list:
        return self.detectRoutingPitfalls()

    @pyqtProperty(str, notify=mfxParamsChanged)
    def mfxAlgoName(self) -> str:
        shown, bypassed, _d, _c, _r, _p = self._mfx_view()
        if bypassed:
            return "BYPASS / OFF"
        algo = get_mfx_algo(shown)
        return algo.get("name", f"MFX #{shown}") if algo else f"MFX #{shown}"

    @pyqtProperty(str, notify=chorusParamsChanged)
    def chorusTypeName(self) -> str:
        return self._name_of(self._CHORUS_NAMES, self._cho_view()[0])

    @pyqtProperty(str, notify=reverbParamsChanged)
    def reverbTypeName(self) -> str:
        return self._name_of(self._REVERB_NAMES, self._rev_view()[0])

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

    @pyqtProperty(int, notify=analogFeelChanged)
    def analogFeel(self) -> int:
        return self.patch_state.common.analog_feel

    @pyqtSlot(int)
    def setMasterCutoff(self, val: int) -> None:
        """Set TVF Cutoff (0..127). Ganged across all 4 tones if linked."""
        clamped = max(0, min(127, int(val)))
        targets = self._target_tones()
        for t in targets:
            t.tvf_cutoff = clamped
            if self.juno:
                try:
                    self.juno.set_tone_tvf(t.tone_index, cutoff=clamped)
                except Exception as e:
                    logger.error(f"Error setting cutoff on synth: {e}")
        self._rebaseDirect([(f"tone.{t.tone_index}.tvf_cutoff", clamped) for t in targets])
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
        self._rebaseDirect([(f"tone.{t.tone_index}.tvf_resonance", clamped) for t in targets])
        self.masterResoChanged.emit(clamped)

    @pyqtSlot(int)
    def setMasterLevel(self, val: int) -> None:
        """Set Master Patch Level (0..127)."""
        clamped = max(0, min(127, int(val)))
        if self.patch_state.common.level != clamped:
            self.patch_state.common.level = clamped
            self._rebaseDirect([("common.level", clamped)])
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
        self._rebaseDirect([(f"tone.{t.tone_index}.tvf_env_depth", raw_val) for t in targets])
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
        self._rebaseDirect([(f"tone.{t.tone_index}.tvf_attack", clamped) for t in targets])
        self.tvfAttackChanged.emit(clamped)
        self.envShapeChanged.emit("TVF")

    @pyqtSlot(int)
    def setTvfDecay(self, val: int) -> None:
        clamped = max(0, min(127, int(val)))
        targets = self._target_tones()
        for t in targets:
            t.tvf_decay = clamped
            self._push_tvf_env(t)
        self._rebaseDirect([(f"tone.{t.tone_index}.tvf_decay", clamped) for t in targets])
        self.tvfDecayChanged.emit(clamped)
        self.envShapeChanged.emit("TVF")

    @pyqtSlot(int)
    def setTvfSustain(self, val: int) -> None:
        clamped = max(0, min(127, int(val)))
        targets = self._target_tones()
        for t in targets:
            t.tvf_sustain = clamped
            self._push_tvf_env(t)
        self._rebaseDirect([(f"tone.{t.tone_index}.tvf_sustain", clamped) for t in targets])
        self.tvfSustainChanged.emit(clamped)
        self.envShapeChanged.emit("TVF")

    @pyqtSlot(int)
    def setTvfRelease(self, val: int) -> None:
        clamped = max(0, min(127, int(val)))
        targets = self._target_tones()
        for t in targets:
            t.tvf_release = clamped
            self._push_tvf_env(t)
        self._rebaseDirect([(f"tone.{t.tone_index}.tvf_release", clamped) for t in targets])
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
        self._rebaseDirect([(f"tone.{t.tone_index}.tva_attack", clamped) for t in targets])
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
        self._rebaseDirect([(f"tone.{t.tone_index}.tva_decay", clamped) for t in targets])
        self.tvaDecayChanged.emit(clamped)
        self.envShapeChanged.emit("TVA")

    @pyqtSlot(int)
    def setTvaSustain(self, val: int) -> None:
        clamped = max(0, min(127, int(val)))
        targets = self._target_tones()
        for t in targets:
            t.tva_sustain = clamped
            self._push_tva_env(t)
        self._rebaseDirect([(f"tone.{t.tone_index}.tva_sustain", clamped) for t in targets])
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
        self._rebaseDirect([(f"tone.{t.tone_index}.tva_release", clamped) for t in targets])
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
        self._rebaseDirect([(f"tone.{t.tone_index}.tva_pan", raw_val) for t in targets])
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
        self._rebaseDirect([(f"tone.{t.tone_index}.pitch_coarse", raw_val) for t in targets])
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
        self._rebaseDirect([(f"tone.{t.tone_index}.pitch_fine", raw_val) for t in targets])
        self.pitchFineChanged.emit(clamped)
        self.vaParamsChanged.emit()

    @pyqtSlot(int)
    def setPortamentoTime(self, val: int) -> None:
        """Set Patch Portamento Time (0..127)."""
        clamped = max(0, min(127, int(val)))
        if self.patch_state.common.portamento_time != clamped:
            self.patch_state.common.portamento_time = clamped
            self._rebaseDirect([("common.portamento_time", clamped)])
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
        """Set Patch Analog Feel / 1/f drift depth (0..127)."""
        clamped = max(0, min(127, int(val)))
        if self.patch_state.common.analog_feel != clamped:
            self.patch_state.common.analog_feel = clamped
            self._rebaseDirect([("common.analog_feel", clamped)])
            self.analogFeelChanged.emit(clamped)
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

        self._rebaseLfoParam(lfo_idx, param, targets)
        self.lfoParamsChanged.emit()

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
        self._rebaseDirect([(f"tone.{t.tone_index}.tvf_cutoff", clamped) for t in self.patch_state.tones])
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
        self._rebaseDirect([(f"tone.{t.tone_index}.tvf_resonance", clamped) for t in self.patch_state.tones])
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
        self._rebaseDirect([(f"tone.{t.tone_index}.tvf_env_depth", raw_val) for t in self.patch_state.tones])
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
        self._rebaseDirect([(f"tone.{t.tone_index}.tvf_attack", clamped) for t in self.patch_state.tones])
        self.tvfAttackChanged.emit(clamped)
        self.envShapeChanged.emit("TVF")

    @pyqtSlot(int)
    def sculptTvfDecay(self, val: int) -> None:
        """Sculpt TVF Decay across all 4 tones (0..127)."""
        clamped = max(0, min(127, int(val)))
        for t in self.patch_state.tones:
            t.tvf_decay = clamped
            self._push_tvf_env(t)
        self._rebaseDirect([(f"tone.{t.tone_index}.tvf_decay", clamped) for t in self.patch_state.tones])
        self.tvfDecayChanged.emit(clamped)
        self.envShapeChanged.emit("TVF")

    @pyqtSlot(int)
    def sculptTvfSustain(self, val: int) -> None:
        """Sculpt TVF Sustain across all 4 tones (0..127)."""
        clamped = max(0, min(127, int(val)))
        for t in self.patch_state.tones:
            t.tvf_sustain = clamped
            self._push_tvf_env(t)
        self._rebaseDirect([(f"tone.{t.tone_index}.tvf_sustain", clamped) for t in self.patch_state.tones])
        self.tvfSustainChanged.emit(clamped)
        self.envShapeChanged.emit("TVF")

    @pyqtSlot(int)
    def sculptTvfRelease(self, val: int) -> None:
        """Sculpt TVF Release across all 4 tones (0..127)."""
        clamped = max(0, min(127, int(val)))
        for t in self.patch_state.tones:
            t.tvf_release = clamped
            self._push_tvf_env(t)
        self._rebaseDirect([(f"tone.{t.tone_index}.tvf_release", clamped) for t in self.patch_state.tones])
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
        self._rebaseDirect([(f"tone.{t.tone_index}.tva_pan", raw_val) for t in self.patch_state.tones])
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
        self._rebaseDirect([(f"tone.{t.tone_index}.tva_attack", clamped) for t in self.patch_state.tones])
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
        self._rebaseDirect([(f"tone.{t.tone_index}.tva_decay", clamped) for t in self.patch_state.tones])
        self.tvaDecayChanged.emit(clamped)
        self.envShapeChanged.emit("TVA")

    @pyqtSlot(int)
    def sculptTvaSustain(self, val: int) -> None:
        """Sculpt TVA Sustain level across all 4 tones (0..127)."""
        clamped = max(0, min(127, int(val)))
        for t in self.patch_state.tones:
            t.tva_sustain = clamped
            self._push_tva_env(t)
        self._rebaseDirect([(f"tone.{t.tone_index}.tva_sustain", clamped) for t in self.patch_state.tones])
        self.tvaSustainChanged.emit(clamped)
        self.envShapeChanged.emit("TVA")

    @pyqtSlot(int)
    def sculptTvaRelease(self, val: int) -> None:
        """Sculpt TVA Release time across all 4 tones (0..127)."""
        clamped = max(0, min(127, int(val)))
        for t in self.patch_state.tones:
            t.tva_release = clamped
            self._push_tva_env(t)
        self._rebaseDirect([(f"tone.{t.tone_index}.tva_release", clamped) for t in self.patch_state.tones])
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

        self._rebaseLfoParam(lfo_idx, param, list(self.patch_state.tones))
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
        self._rebaseDirect([(f"tone.{t.tone_index}.pitch_coarse", raw_val) for t in self.patch_state.tones])
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
        self._rebaseDirect([(f"tone.{t.tone_index}.pitch_fine", raw_val) for t in self.patch_state.tones])
        self.pitchFineChanged.emit(clamped)
        self.vaParamsChanged.emit()

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

    CHORUS_PARAM_SPECS: dict[str, tuple[str, int, int, str]] = {
        "type": ("chorus_type", 0, 3, "type"),
        "level": ("chorus_level", 0, 127, "level"),
        "toReverb": ("chorus_to_reverb", 0, 2, "toReverb"),
        "rate": ("chorus_rate", 0, 127, "rate"),
        "depth": ("chorus_depth", 0, 127, "depth"),
        "preDelay": ("chorus_predelay", 0, 127, "predelay"),
        "feedback": ("chorus_feedback", 0, 127, "feedback"),
    }

    REVERB_PARAM_SPECS: dict[str, tuple[str, int, int, str]] = {
        "type": ("reverb_type", 0, 5, "type"),
        "level": ("reverb_level", 0, 127, "level"),
        "time": ("reverb_time", 0, 127, "time"),
        "damp": ("reverb_damp", 0, 127, "damp"),
        "preDelay": ("reverb_predelay", 0, 127, "predelay"),
        "diffusion": ("reverb_diffusion", 0, 127, "diffusion"),
        "tone": ("reverb_tone", 0, 127, "tone"),
    }

    @pyqtSlot(str, int)
    def setChorusParam(self, param: str, val: int) -> None:
        """Set Master Chorus parameter (origin-resolved in PERFORM mode)."""
        spec = self.CHORUS_PARAM_SPECS.get(param)
        if not spec:
            return
        attr, lo, hi, key = spec
        clamped = max(lo, min(hi, int(val)))
        tgt = self._cho_target()
        juno = self.juno

        if tgt[0] == "perf":
            fx = self.patch_state.perf_fx
            setattr(fx, attr, clamped)
            if juno is not None:
                try:
                    if param in ("type", "level", "toReverb") and hasattr(juno, "set_perf_chorus"):
                        juno.set_perf_chorus(fx.chorus_type, level=fx.chorus_level, output_select=fx.chorus_to_reverb)
                    elif hasattr(juno, "set_perf_chorus_param"):
                        juno.set_perf_chorus_param(param, clamped)
                except Exception as e:
                    logger.error(f"Error setting perf chorus on synth: {e}")
            self._rebasePerfFx("chorus", param, clamped)
            self.chorusParamsChanged.emit()
            self.routingChanged.emit()
            try:
                self.perfFxChanged.emit()
            except Exception:
                pass
            return

        if tgt[0] == "part":
            n = tgt[1]
            cached = self._part_cached(n)
            if cached is None:
                self._ensure_part_fx_cache(n)
                cached = self._part_cached(n)
            if cached is not None:
                c = cached["chorus"]
                c[key] = clamped
                if juno is not None:
                    try:
                        if param in ("type", "level", "toReverb") and hasattr(juno, "set_part_patch_chorus"):
                            juno.set_part_patch_chorus(n, chorus_type=c["type"], level=c["level"], output_select=c["toReverb"])
                        elif hasattr(juno, "set_part_patch_chorus_param"):
                            juno.set_part_patch_chorus_param(n, param, clamped)
                    except Exception as e:
                        logger.error(f"Error setting part {n} chorus on synth: {e}")
                self._rebasePerfFx("chorus", param, clamped)
                self.chorusParamsChanged.emit()
                self.routingChanged.emit()
                return

        eff = self.patch_state.effects
        setattr(eff, attr, clamped)
        if juno is not None:
            try:
                if param in ("type", "level", "toReverb"):
                    juno.set_chorus(eff.chorus_type, level=eff.chorus_level, output_select=eff.chorus_to_reverb)
                else:
                    juno.set_chorus_param(param, clamped)
            except Exception as e:
                logger.error(f"Error setting chorus on synth: {e}")

        self._rebaseChorusParam(param)
        self.chorusParamsChanged.emit()
        self.routingChanged.emit()
        self.macrosChanged.emit()

    @pyqtSlot(str, int)
    def setReverbParam(self, param: str, val: int) -> None:
        """Set Master Reverb parameter (origin-resolved in PERFORM mode)."""
        spec = self.REVERB_PARAM_SPECS.get(param)
        if not spec:
            return
        attr, lo, hi, key = spec
        clamped = max(lo, min(hi, int(val)))
        tgt = self._rev_target()
        juno = self.juno

        if tgt[0] == "perf":
            fx = self.patch_state.perf_fx
            setattr(fx, attr, clamped)
            if juno is not None:
                try:
                    if param in ("type", "level") and hasattr(juno, "set_perf_reverb"):
                        juno.set_perf_reverb(fx.reverb_type, level=fx.reverb_level)
                    elif hasattr(juno, "set_perf_reverb_param"):
                        juno.set_perf_reverb_param(param, clamped)
                except Exception as e:
                    logger.error(f"Error setting perf reverb on synth: {e}")
            self._rebasePerfFx("reverb", param, clamped)
            self.reverbParamsChanged.emit()
            self.routingChanged.emit()
            try:
                self.perfFxChanged.emit()
            except Exception:
                pass
            return

        if tgt[0] == "part":
            n = tgt[1]
            cached = self._part_cached(n)
            if cached is None:
                self._ensure_part_fx_cache(n)
                cached = self._part_cached(n)
            if cached is not None:
                r = cached["reverb"]
                r[key] = clamped
                if juno is not None:
                    try:
                        if param in ("type", "level") and hasattr(juno, "set_part_patch_reverb"):
                            juno.set_part_patch_reverb(n, reverb_type=r["type"], level=r["level"])
                        elif hasattr(juno, "set_part_patch_reverb_param"):
                            juno.set_part_patch_reverb_param(n, param, clamped)
                    except Exception as e:
                        logger.error(f"Error setting part {n} reverb on synth: {e}")
                self._rebasePerfFx("reverb", param, clamped)
                self.reverbParamsChanged.emit()
                self.routingChanged.emit()
                return

        eff = self.patch_state.effects
        setattr(eff, attr, clamped)
        if juno is not None:
            try:
                if param in ("type", "level"):
                    juno.set_reverb(eff.reverb_type, level=eff.reverb_level)
                else:
                    juno.set_reverb_param(param, clamped)
            except Exception as e:
                logger.error(f"Error setting reverb on synth: {e}")

        self._rebaseReverbParam(param)
        self.reverbParamsChanged.emit()
        self.routingChanged.emit()
        self.macrosChanged.emit()

    @pyqtSlot(str, str, int)
    def setEffectParam(self, block: str, param: str, val: int) -> None:
        """Unified table-driven effect param dispatch ('chorus' or 'reverb')."""
        b = str(block).lower().strip()
        if b == "chorus":
            self.setChorusParam(param, val)
        elif b == "reverb":
            self.setReverbParam(param, val)
        self.macrosChanged.emit()

    def _apply_mfx_algo(self, store, algo_id: int) -> int:
        """Shared algo-select onto an MFX-like store (EffectsState or PerfMfxSlotState).

        Returns the clamped id. Loads catalog default params when selecting
        a real algorithm; marks bypass when selecting 0.
        """
        clamped = max(0, min(80, int(algo_id)))
        store.mfx_type = clamped
        if clamped > 0:
            store.last_active_type = clamped
            if hasattr(store, "mfx_last_active_type"):
                store.mfx_last_active_type = clamped
            if hasattr(store, "mfx_bypassed"):
                store.mfx_bypassed = False
            algo = get_mfx_algo(clamped)
            if algo and "params" in algo:
                for pp in algo["params"]:
                    idx = pp["idx"]
                    if 0 <= idx < 32:
                        try:
                            store.params[idx] = pp.get("val", 0)
                        except Exception:
                            pass
                        if hasattr(store, "mfx_params"):
                            store.mfx_params[idx] = pp.get("val", 0)
        else:
            if hasattr(store, "mfx_bypassed"):
                store.mfx_bypassed = True
        return clamped

    def _push_mfx_algo(self, juno, kind, slot_or_part, store, clamped: int) -> None:
        """Push an algo-select to hardware (catalog defaults included)."""
        try:
            algo = get_mfx_algo(clamped) if clamped > 0 else None
            if kind == "perf":
                juno.set_perf_mfx(slot_or_part, mfx_type=store.mfx_type)
                if algo and "params" in algo:
                    for pp in algo["params"]:
                        try:
                            juno.set_perf_mfx_param(slot_or_part, pp["idx"], store.params[pp["idx"]])
                        except Exception:
                            pass
            elif kind == "part":
                juno.set_part_patch_mfx(slot_or_part, mfx_type=store.mfx_type)
                if algo and "params" in algo:
                    for pp in algo["params"]:
                        try:
                            juno.set_part_patch_mfx_param(slot_or_part, pp["idx"], store.params[pp["idx"]])
                        except Exception:
                            pass
            else:
                params = getattr(store, "mfx_params", getattr(store, "params", []))
                juno.set_mfx(store.mfx_type)
                if algo and "params" in algo:
                    vals = [params[pp["idx"]] for pp in algo["params"]]
                    juno.set_mfx_params_bulk(vals)
        except Exception as e:
            logger.error(f"Error setting MFX type on synth: {e}")

    @pyqtSlot(int)
    def setMfxAlgoId(self, algo_id: int) -> None:
        """Select active MFX Algorithm (0..80), origin-resolved in PERFORM mode."""
        tgt = self._mfx_target()
        juno = self.juno
        if tgt[0] == "perf":
            holder = self._perf_slot(tgt[1])
            clamped = self._apply_mfx_algo(holder, algo_id)
            if juno is not None and hasattr(juno, "set_perf_mfx"):
                self._push_mfx_algo(juno, "perf", tgt[1], holder, clamped)
            self._emit_fx_editor_signals()
            return
        if tgt[0] == "part":
            n = tgt[1]
            cached = self._part_cached(n)
            if cached is None:
                self._ensure_part_fx_cache(n)
                cached = self._part_cached(n)
            if cached is not None:
                entry = dict(cached["mfx"])
                store = type("M", (), {})()
                store.mfx_type = entry["type"]; store.params = list(entry["params"])
                store.last_active_type = entry.get("lastActive", 15)
                store.mfx_last_active_type = entry.get("lastActive", 15)
                clamped = self._apply_mfx_algo(store, algo_id)
                entry["type"] = store.mfx_type; entry["params"] = list(store.params[:32])
                entry["lastActive"] = int(getattr(store, "last_active_type", 15) or 15)
                cached["mfx"] = entry
                if juno is not None and hasattr(juno, "set_part_patch_mfx"):
                    self._push_mfx_algo(juno, "part", n, store, clamped)
                self._emit_fx_editor_signals()
                return
        eff = self.patch_state.effects
        clamped = self._apply_mfx_algo(eff, algo_id)
        if self.engine.juno:
            self._push_mfx_algo(self.engine.juno, "patch", 0, eff, clamped)

        self.mfxValuesChanged.emit()
        self.mfxParamsChanged.emit()
        self.routingChanged.emit()

    @pyqtSlot(int, int)
    def setMfxParam(self, param_index: int, val: int) -> None:
        """Set an individual MFX parameter (0..31), origin-resolved in PERFORM mode."""
        if not (0 <= param_index < 32):
            return
        tgt = self._mfx_target()
        juno = self.juno
        if tgt[0] == "perf":
            holder = self._perf_slot(tgt[1])
            holder.params[param_index] = int(val)
            if juno is not None:
                try:
                    if hasattr(juno, "set_perf_mfx_param"):
                        juno.set_perf_mfx_param(tgt[1], int(param_index), int(val))
                except Exception as e:
                    logger.error(f"Error setting perf MFX param on synth: {e}")
            self.mfxValuesChanged.emit()
            try:
                self.perfFxChanged.emit()
            except Exception:
                pass
            return
        if tgt[0] == "part":
            n = tgt[1]
            cached = self._part_cached(n)
            if cached is None:
                self._ensure_part_fx_cache(n)
                cached = self._part_cached(n)
            if cached is not None:
                cached["mfx"]["params"][param_index] = int(val)
                if juno is not None:
                    try:
                        if hasattr(juno, "set_part_patch_mfx_param"):
                            juno.set_part_patch_mfx_param(n, int(param_index), int(val))
                    except Exception as e:
                        logger.error(f"Error setting part MFX param on synth: {e}")
                self.mfxValuesChanged.emit()
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
        """Toggle MFX Bypass switch (origin-resolved in PERFORM mode)."""
        tgt = self._mfx_target()
        juno = self.juno
        if tgt[0] == "perf":
            holder = self._perf_slot(tgt[1])
            if bypassed:
                holder.mfx_type = 0
            else:
                holder.mfx_type = int(getattr(holder, "last_active_type", 15) or 15)
            if juno is not None:
                try:
                    if hasattr(juno, "set_perf_mfx"):
                        juno.set_perf_mfx(tgt[1], mfx_type=int(holder.mfx_type))
                except Exception as e:
                    logger.error(f"Error toggling perf MFX bypass on synth: {e}")
            self._emit_fx_editor_signals()
            return
        if tgt[0] == "part":
            n = tgt[1]
            cached = self._part_cached(n)
            if cached is None:
                self._ensure_part_fx_cache(n)
                cached = self._part_cached(n)
            if cached is not None:
                m = cached["mfx"]
                if bypassed:
                    m["type"] = 0
                else:
                    m["type"] = int(m.get("lastActive") or 15)
                if juno is not None:
                    try:
                        if hasattr(juno, "set_part_patch_mfx"):
                            juno.set_part_patch_mfx(n, mfx_type=int(m["type"]))
                    except Exception as e:
                        logger.error(f"Error toggling part MFX bypass on synth: {e}")
                self._emit_fx_editor_signals()
                return
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
        """Set MFX Dry, Chorus, or Reverb send level (0..127), origin-resolved."""
        tgt = self._mfx_target()
        clamped = max(0, min(127, int(val)))
        juno = self.juno
        if tgt[0] == "perf":
            holder = self._perf_slot(tgt[1])
            if send_type == "dry":
                holder.dry_send = clamped
            elif send_type == "chorus":
                holder.chorus_send = clamped
            elif send_type == "reverb":
                holder.reverb_send = clamped
            if juno is not None:
                try:
                    if hasattr(juno, "set_perf_mfx"):
                        juno.set_perf_mfx(tgt[1], dry_send=int(holder.dry_send),
                                          chorus_send=int(holder.chorus_send),
                                          reverb_send=int(holder.reverb_send))
                except Exception as e:
                    logger.error(f"Error setting perf MFX sends on synth: {e}")
            self._rebasePerfFx(f"mfx{tgt[1]}", send_type, clamped)
            self.mfxParamsChanged.emit()
            self.routingChanged.emit()
            try:
                self.perfFxChanged.emit()
            except Exception:
                pass
            return
        if tgt[0] == "part":
            n = tgt[1]
            cached = self._part_cached(n)
            if cached is None:
                self._ensure_part_fx_cache(n)
                cached = self._part_cached(n)
            if cached is not None:
                m = cached["mfx"]
                if send_type == "dry":
                    m["dry"] = clamped
                elif send_type == "chorus":
                    m["chorus"] = clamped
                elif send_type == "reverb":
                    m["reverb"] = clamped
                if juno is not None:
                    try:
                        if hasattr(juno, "set_part_patch_mfx"):
                            juno.set_part_patch_mfx(n, dry_send=int(m["dry"]),
                                                    chorus_send=int(m["chorus"]),
                                                    reverb_send=int(m["reverb"]))
                    except Exception as e:
                        logger.error(f"Error setting part MFX sends on synth: {e}")
                self._rebasePerfFx(f"mfx{self.editingPerfMfx}", send_type, clamped)
                self.mfxParamsChanged.emit()
                self.routingChanged.emit()
                return
        eff = self.patch_state.effects
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

        key = {"dry": "effects.mfx_dry_send", "chorus": "effects.mfx_chorus_send",
               "reverb": "effects.mfx_reverb_send"}.get(send_type)
        if key:
            self._rebaseDirect([(key, clamped)])
        self.mfxParamsChanged.emit()
        self.routingChanged.emit()

    # ------------------------------------------------------------------
    # Routing (model: core.routing; the schematic draws routingGraph)
    # ------------------------------------------------------------------

    _CHORUS_NAMES = ["OFF", "CHORUS", "DELAY", "GM2 CHORUS"]
    _REVERB_NAMES = ["OFF", "REVERB", "ROOM", "HALL", "PLATE", "GM2"]

    @staticmethod
    def _name_of(names: list, idx: int) -> str:
        return names[idx] if 0 <= idx < len(names) else "OFF"

    def _routing_mfx_slot(self) -> int:
        """PERFORM: the MFX whose outputs the edited part reaches (end of chain)."""
        part = self.patch_state.perf_parts[self.activePerfPart - 1]
        fx = self.patch_state.perf_fx
        return mfx_chain(int(part.mfx_select) + 1, int(getattr(fx, "mfx_structure", 0)))[-1]

    def _routing_inputs(self) -> dict:
        if self._in_perform():
            part = self.patch_state.perf_parts[self.activePerfPart - 1]
            fx = self.patch_state.perf_fx
            chain = mfx_chain(int(part.mfx_select) + 1, int(getattr(fx, "mfx_structure", 0)))
            m = self._rail_mfx_entry(chain[-1])
            c, r = self._rail_cho_entry(), self._rail_rev_entry()
            return {
                "part": part, "chain": chain, "mfxSource": int(m["source"]),
                "choSource": int(c["source"]), "revSource": int(r["source"]),
                "mfx": {"type": int(m["type"]), "dry": int(m["drySend"]),
                        "cho": int(m["chorusSend"]), "rev": int(m["reverbSend"])},
                "chorus": {"type": int(c["type"]), "level": int(c["level"]), "toReverb": int(c["toReverb"])},
                "reverb": {"type": int(r["type"]), "level": int(r["level"])},
            }
        shown, bypassed, dry, cho, rev, _ = self._mfx_view()
        c, r = self._cho_view(), self._rev_view()
        return {
            "part": None, "chain": [1], "mfxSource": 0, "choSource": 0, "revSource": 0,
            "mfx": {"type": 0 if bypassed else int(shown), "dry": dry, "cho": cho, "rev": rev},
            "chorus": {"type": c[0], "level": c[1], "toReverb": c[2]},
            "reverb": {"type": r[0], "level": r[1]},
        }

    def _build_routing_graph(self) -> dict:
        inp = self._routing_inputs()
        perform = inp["part"] is not None
        label = "→".join(f"MFX{n}" for n in inp["chain"]) if perform else "MFX"
        g = build_graph(self.patch_state, mfx=inp["mfx"], chorus=inp["chorus"],
                        reverb=inp["reverb"], part=inp["part"], mfx_label=label)
        mtype = inp["mfx"]["type"]
        algo = get_mfx_algo(mtype) if mtype > 0 else None
        g["nodes"]["mfx"]["sub"] = (algo.get("name", f"MFX #{mtype}") if algo else "THRU")
        g["nodes"]["cho"]["sub"] = self._name_of(self._CHORUS_NAMES, inp["chorus"]["type"])
        g["nodes"]["rev"]["sub"] = self._name_of(self._REVERB_NAMES, inp["reverb"]["type"])
        for key, src in (("mfx", "mfxSource"), ("cho", "choSource"), ("rev", "revSource")):
            g["nodes"][key]["source"] = self._origin_text(inp[src]) if perform else ""
        if perform:
            part = inp["part"]
            g["part"] = {"index": int(part.part_index), "assign": int(part.output_assign),
                         "mfxSelect": int(part.mfx_select) + 1, "level": int(part.dry_send),
                         "chorusSend": int(part.chorus_send), "reverbSend": int(part.reverb_send),
                         "muted": bool(part.muted), "volume": int(part.volume)}
            editing = self.editingPerfMfx
            g["editingMfx"] = editing
            g["mfxEnd"] = inp["chain"][-1]
            g["mfxMismatch"] = editing not in inp["chain"] and g["edges"]["in->mfx"]["active"]
            if g["mfxMismatch"]:
                g["notes"].insert(0, {
                    "type": "MFX_MISMATCH", "severity": "info",
                    "title": f"Editing MFX{editing}",
                    "description": f"Part {part.part_index} plays through {label}; "
                                   f"the MFX controls below edit MFX{editing}."})
        else:
            g["part"] = None
            g["editingMfx"] = 1
            g["mfxEnd"] = 1
            g["mfxMismatch"] = False
        return g

    def _emit_routing_graph(self, *_args) -> None:
        self.routingGraphChanged.emit()

    @pyqtProperty("QVariantMap", notify=routingGraphChanged)
    def routingGraph(self) -> dict:
        return self._build_routing_graph()

    @pyqtProperty(int, notify=routingGraphChanged)
    def patchOutputAssign(self) -> int:
        return int(self.patch_state.common.patch_output_assign)

    @pyqtSlot(result="QVariantList")
    def detectRoutingPitfalls(self) -> list:
        """Routing notes (warnings first) for the sound as it plays now."""
        order = {"warning": 0, "caution": 1, "info": 2}
        return sorted(self._build_routing_graph()["notes"], key=lambda n: order.get(n["severity"], 3))

    # Presets. Each tone gets (assign, chorus send, reverb send); sends go to
    # the pair the new route uses. mfx: (dry, chorus, reverb) or None = keep.
    # chorus: (level, output select) or None; reverb: level or None. A preset
    # that sends to chorus/reverb turns the unit on when it is OFF.
    ROUTING_PRESETS: dict[str, dict] = {
        # Tones -> MFX -> Chorus -> Reverb -> Out (fully wet serial chain)
        "SERIAL_CHAIN": {"tones": [(0, 0, 0)] * 4, "mfx": (0, 127, 0),
                         "chorus": (80, 1), "reverb": 60},
        # Tones -> MFX insert -> Out, MFX feeds chorus & reverb in parallel
        "STUDIO_AUX": {"tones": [(0, 0, 0)] * 4, "mfx": (127, 60, 60),
                       "chorus": (75, 0), "reverb": 65},
        # Tones direct to Out with their own chorus & reverb sends; MFX unused
        "VINTAGE_SYNTH": {"tones": [(1, 70, 50)] * 4, "mfx": None,
                          "chorus": (80, 0), "reverb": 60},
        # Tones -> MFX (mostly wet) -> Chorus entirely into a big Reverb
        "AMBIENT_WASH": {"tones": [(0, 0, 0)] * 4, "mfx": (30, 110, 40),
                         "chorus": (90, 1), "reverb": 95},
        # Tones 1-2 through MFX, tones 3-4 direct with chorus & reverb
        "SPLIT_PATH": {"tones": [(0, 0, 0), (0, 0, 0), (1, 40, 60), (1, 40, 60)],
                       "mfx": (127, 0, 0), "chorus": (80, 0), "reverb": 70},
        # Tones direct, no sends: the bare sound, no effects at all
        "CLEAN_DIRECT": {"tones": [(1, 0, 0)] * 4, "mfx": None,
                         "chorus": None, "reverb": None},
    }

    def _write_tone_routing(self, t, assign: int, cho: int, rev: int) -> None:
        """Assign + level 127 + the send pair that assign uses (state + SysEx)."""
        t.output_assign = assign
        t.output_level = 127
        cho_attr, rev_attr = TONE_SEND_ATTRS[is_direct(assign)]
        setattr(t, cho_attr, cho)
        setattr(t, rev_attr, rev)
        juno = self.juno
        if juno:
            try:
                juno.set_tone_output(t.tone_index, output_assign=assign, output_level=127,
                                     **{cho_attr: cho, rev_attr: rev})
            except Exception as e:
                logger.error(f"Error setting tone {t.tone_index} routing: {e}")

    @pyqtSlot(str)
    def applyRoutingPreset(self, preset_name: str) -> None:
        """Apply a routing preset to the edited sound.

        Sets the patch output to TONE (and, in PERFORM, the part output to
        PATCH) so the per-tone routes are the ones that play. MFX sends go
        to the MFX the sound actually reaches; chorus and reverb go through
        the origin-resolved setters.
        """
        preset = preset_name.upper().replace(" ", "_")
        spec = self.ROUTING_PRESETS.get(preset)
        if spec is None:
            return
        eff = self.patch_state.effects
        eff.routing_preset = preset
        juno = self.juno

        self._set_patch_assign(ASSIGN_DEFER)
        if self._in_perform():
            part = self.patch_state.perf_parts[self.activePerfPart - 1]
            if int(part.output_assign) != ASSIGN_DEFER:
                self.setPartOutput(part.part_index, ASSIGN_DEFER, part.mfx_select)
        for t, (assign, cho, rev) in zip(self.patch_state.tones, spec["tones"]):
            self._write_tone_routing(t, assign, cho, rev)

        if spec["mfx"] is not None:
            dry, m_cho, m_rev = spec["mfx"]
            if self._in_perform():
                saved = self._editing_perf_mfx
                self._editing_perf_mfx = self._routing_mfx_slot()
                try:
                    for send, v in (("dry", dry), ("chorus", m_cho), ("reverb", m_rev)):
                        self.setMfxSend(send, v)
                finally:
                    self._editing_perf_mfx = saved
            else:
                eff.mfx_dry_send, eff.mfx_chorus_send, eff.mfx_reverb_send = dry, m_cho, m_rev
                if juno:
                    try:
                        juno.set_mfx(eff.mfx_type, dry_send=dry, chorus_send=m_cho, reverb_send=m_rev)
                    except Exception as e:
                        logger.error(f"Error setting MFX sends on synth: {e}")
        if spec["chorus"] is not None:
            level, sel = spec["chorus"]
            if self._cho_view()[0] == 0:
                self.setChorusParam("type", 1)
            self.setChorusParam("level", level)
            self.setChorusParam("toReverb", sel)
        if spec["reverb"] is not None:
            if self._rev_view()[0] == 0:
                self.setReverbParam("type", 4)
            self.setReverbParam("level", spec["reverb"])

        self.routingChanged.emit()
        self.mfxParamsChanged.emit()
        self.chorusParamsChanged.emit()
        self.reverbParamsChanged.emit()
        self.macrosChanged.emit()

    @pyqtSlot(bool)
    def setManualRoutingUnlocked(self, unlocked: bool) -> None:
        """Kept for old layouts; routing controls are always editable now."""
        self.patch_state.effects.manual_routing_unlocked = bool(unlocked)
        self.routingChanged.emit()

    def _set_patch_assign(self, value: int) -> None:
        common = self.patch_state.common
        if int(common.patch_output_assign) == int(value):
            return
        common.patch_output_assign = int(value)
        if self.juno:
            try:
                self.juno.set_patch_output_assign(int(value))
            except Exception as e:
                logger.error(f"Error setting patch output assign: {e}")

    @pyqtSlot(int)
    def setPatchOutputAssign(self, value: int) -> None:
        """Patch output: 13 TONE (per-tone routes), 0 MFX, 1 L+R, 5 L, 6 R."""
        v = int(value)
        if v != ASSIGN_DEFER and v not in TONE_ASSIGNS:
            return
        self.patch_state.effects.routing_preset = "CUSTOM"
        self._set_patch_assign(v)
        self.routingChanged.emit()

    @pyqtSlot(int, str, int)
    def setToneRoutingParam(self, tone_idx: int, param: str, val: int) -> None:
        """Tone routing: assign (0 MFX, 1 L+R, 5 L, 6 R), level, chorusSend, reverbSend.

        tone_idx 1..4, or 0 for all four. Sends edit the pair the tone's
        current route uses, like the Juno panel.
        """
        tones = self.patch_state.tones if tone_idx == 0 else [self.patch_state.tones[tone_idx - 1]]
        juno = self.juno
        common = self.patch_state.common
        if param == "assign" and int(val) not in TONE_ASSIGNS:
            return
        self.patch_state.effects.routing_preset = "CUSTOM"

        for t in tones:
            if param == "assign":
                t.output_assign = int(val)
                if juno:
                    try:
                        juno.set_tone_output(t.tone_index, output_assign=t.output_assign)
                    except Exception as e:
                        logger.error(f"Error setting tone output assign: {e}")
            elif param == "level":
                t.output_level = max(0, min(127, int(val)))
                if juno:
                    try:
                        juno.set_tone_output(t.tone_index, output_level=t.output_level)
                    except Exception as e:
                        logger.error(f"Error setting tone output level: {e}")
                self._rebaseDirect([(f"tone.{t.tone_index}.output_level", t.output_level)])
            elif param in ("chorusSend", "reverbSend"):
                v = max(0, min(127, int(val)))
                cho_attr, rev_attr = tone_send_attrs(common, t)
                attr = cho_attr if param == "chorusSend" else rev_attr
                setattr(t, attr, v)
                if juno:
                    try:
                        juno.set_tone_output(t.tone_index, **{attr: v})
                    except Exception as e:
                        logger.error(f"Error setting tone {param}: {e}")
                key = "chorus_send" if param == "chorusSend" else "reverb_send"
                self._rebaseDirect([(f"tone.{t.tone_index}.{key}", v)])

        self.routingChanged.emit()

    @pyqtSlot(str, int)
    def setRoutingPartParam(self, param: str, val: int) -> None:
        """PERFORM: edited part's output (assign 13 PATCH/0/1/5/6, mfx 1..3,
        level, chorus, reverb)."""
        if not self._in_perform():
            return
        part = self.patch_state.perf_parts[self.activePerfPart - 1]
        v = int(val)
        if param == "assign":
            if v != ASSIGN_DEFER and v not in TONE_ASSIGNS:
                return
            self.setPartOutput(part.part_index, v, part.mfx_select)
        elif param == "mfxSelect":
            self.setPartOutput(part.part_index, part.output_assign, max(1, min(3, v)) - 1)
        elif param in ("level", "chorusSend", "reverbSend"):
            which = {"level": 0, "chorusSend": 1, "reverbSend": 2}[param]
            self.setPartFx(part.part_index, which, v)
        self.routingChanged.emit()

    @pyqtSlot()
    def editRoutedMfx(self) -> None:
        """PERFORM: point the MFX editing radio at the MFX the part reaches."""
        if self._in_perform():
            self.setEditingPerfMfx(self._routing_mfx_slot())

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

    @pyqtSlot(int, int)
    def setPartVolume(self, part_index: int, vol: int) -> None:
        """Set mixer level for Performance Part 1..16 (state + SysEx DT1)."""
        if 1 <= part_index <= 16:
            self.patch_state.perf_parts[part_index - 1].volume = max(0, min(127, int(vol)))
            juno = self.juno
            if juno is not None:
                try:
                    juno.set_perf_part_level(part_index, int(vol))
                except Exception as e:
                    logger.debug(f"setPartVolume: synth write failed: {e}")
            self._rebaseDirect([(f"part.level@{part_index}",
                                 self.patch_state.perf_parts[part_index - 1].volume)])
            self.perfPartsChanged.emit()

    @pyqtSlot(int, int)
    def setPartPan(self, part_index: int, pan: int) -> None:
        """Set pan for Performance Part 1..16 (state + SysEx DT1)."""
        if 1 <= part_index <= 16:
            self.patch_state.perf_parts[part_index - 1].pan = max(0, min(127, int(pan)))
            juno = self.juno
            if juno is not None:
                try:
                    juno.set_perf_part_pan(part_index, int(pan))
                except Exception as e:
                    logger.debug(f"setPartPan: synth write failed: {e}")
            self._rebaseDirect([(f"part.pan@{part_index}",
                                 self.patch_state.perf_parts[part_index - 1].pan)])
            self.perfPartsChanged.emit()

    @pyqtSlot()
    @pyqtSlot(bool)
    def syncPatchFromSynth(self, async_mode: bool = False) -> None:
        """Query active patch and all workstation parameters from Roland hardware."""
        if not self.engine.juno:
            logger.info("Cannot sync: No Roland synthesizer connected.")
            return

        if self._sync_busy:
            logger.info("Hardware sync already in progress, ignoring request.")
            return

        def _do_sync() -> None:
            self._set_sync_busy(True)
            try:
                logger.info("Syncing entire patch and workstation state from Roland hardware...")
                full_sync_ok = False
                if hasattr(self.engine.juno, "read_full_patch"):
                    try:
                        state = self.engine.juno.read_full_patch(timeout=1.0)
                        if isinstance(state, PatchState):
                            # Preserve customizable macro assignments (names/links/values);
                            # bases re-capture lazily from the fresh hardware truth.
                            kept_macros = self.patch_state.macros
                            self.patch_state = state
                            self.patch_state.macros = kept_macros
                            self._resetMacroBases()
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
            finally:
                self._set_sync_busy(False)

        if async_mode:
            threading.Thread(target=_do_sync, daemon=True).start()
        else:
            _do_sync()

    @pyqtSlot(str, str, str, result="QVariantList")
    def getFilteredWaves(self, category: str = "ALL", bank: str = "ALL", search: str = "") -> list:
        """Query waveform catalog filtered by category, bank, and search string."""
        return self._wave_catalog.get_filtered_waves(category=category, bank=bank, search=search)

    @pyqtSlot(int, int, int, result=bool)
    @pyqtSlot(int, int, int, str, result=bool)
    def selectLibraryPerformance(self, msb: int, lsb: int, pc: int, name: str = "") -> bool:
        """Audition a performance via PERFORM mode + control channel (ch 16).

        Switches the synth to PERFORM, selects via Bank Select + PC on the
        performance control channel, then follows the performance name at
        10 00 00 00. The synth stays in PERFORM mode afterwards.
        Offline (no synth): applies the mode + navigation state-only, using
        the library row name for the header.
        """
        juno = self.juno
        if juno is None:
            if str(name or ""):
                self._patch_name = str(name)[:12]
                self.patch_state.perf_name = str(name)[:12]
            self._apply_performance_selected(int(msb), int(lsb), int(pc))
            return True
        midi = getattr(juno, "midi", None)
        out = getattr(midi, "juno_out", None) if midi is not None else None
        if out is None or getattr(out, "closed", False):
            if str(name or ""):
                self._patch_name = str(name)[:12]
                self.patch_state.perf_name = str(name)[:12]
            self._apply_performance_selected(int(msb), int(lsb), int(pc))
            return True
        try:
            import time as _time

            import mido as _mido

            from ...core.sysex import ADDR_SETUP as _SETUP

            juno.send_data(_SETUP, [1])  # PERFORM
            _time.sleep(0.4)
            out.send(_mido.Message("control_change", channel=15, control=0, value=int(msb)))
            out.send(_mido.Message("control_change", channel=15, control=32, value=int(lsb)))
            out.send(_mido.Message("program_change", channel=15, program=int(pc)))
            _time.sleep(0.8)
            try:
                juno._cached_patch_base = None
                juno._cached_sound_mode = None
            except AttributeError:
                pass
            heard: str = ""
            try:
                raw = juno.request_data((0x10, 0x00, 0x00, 0x00),
                                        (0x00, 0x00, 0x00, 0x0C), timeout=0.8)
                if raw and len(raw) >= 12:
                    heard = bytes(raw[:12]).decode("latin1", errors="replace").strip()
            except Exception as e:
                logger.debug(f"selectLibraryPerformance: name re-read failed: {e}")
            # Synth truth wins; library row name is the offline/fallback.
            self._patch_name = (heard or str(name or ""))[:12] or self._patch_name
            self.patch_state.perf_name = str(self._patch_name)[:12]
            # The app's performance is what mode switches push back: take the
            # loaded one whole. Nothing of the previous one survives (sounds,
            # names, edits).
            self._part_snapshots = {}
            for p in self.patch_state.perf_parts:
                p.patch_name, p.name = "", f"Part {p.part_index}"
            try:
                self.syncPerformanceFromSynth(async_mode=False)
            except Exception as e:
                logger.warning(f"selectLibraryPerformance: performance read failed: {e}")
            self._apply_performance_selected(int(msb), int(lsb), int(pc))
            return True
        except Exception as e:
            logger.warning(f"selectLibraryPerformance failed: {e}")
            return False

    def _apply_performance_selected(self, msb: int, lsb: int, pc: int) -> None:
        """App-side half of a performance audition (mode + ref + OK destination)."""
        self._sound_mode = "PERFORM"
        self.patch_state.sound_mode = "PERFORM"
        self.patchInfoChanged.emit(self._patch_name, self._sound_mode)
        self.perfPartsChanged.emit()
        try:
            self._emit_fx_editor_signals()
        except Exception:
            pass
        self._set_current_slot_ref(int(msb), int(lsb), int(pc), "performance")
        self._pending_view = "PERFORMANCE"

    @pyqtSlot(int, int, int, result=bool)
    @pyqtSlot(int, int, int, str, result=bool)
    def selectLibraryPatch(self, msb: int, lsb: int, pc: int, name: str = "") -> bool:
        """Audition a factory/synth-user patch via Bank Select + Program Change.

        Clears the cached temp-buffer base/mode, then re-reads the patch name
        so the header follows the keyboard. Returns True on success.
        File patches with a synth_ref should call this with their stored
        msb/lsb/pc; pure Pi-only files go through loadSpectreFile (DT1 push).
        Offline (no synth): applies the mode + navigation state-only.
        """
        juno = self.juno
        if juno is None:
            logger.info("selectLibraryPatch: no synth connected (offline audition).")
            if str(name or ""):
                self._patch_name = str(name)[:12]
                self.patch_state.common.name = str(name)[:12]
            self._apply_patch_selected(int(msb), int(lsb), int(pc))
            return True
        midi = getattr(juno, "midi", None)
        out = getattr(midi, "juno_out", None) if midi is not None else None
        if out is None or getattr(out, "closed", False):
            logger.info("selectLibraryPatch: MIDI out not connected (offline audition).")
            if str(name or ""):
                self._patch_name = str(name)[:12]
                self.patch_state.common.name = str(name)[:12]
            self._apply_patch_selected(int(msb), int(lsb), int(pc))
            return True
        try:
            import mido as _mido

            out.send(_mido.Message("control_change", channel=0, control=0, value=int(msb)))
            out.send(_mido.Message("control_change", channel=0, control=32, value=int(lsb)))
            out.send(_mido.Message("program_change", channel=0, program=int(pc)))
            try:
                juno._cached_patch_base = None
                juno._cached_sound_mode = None
            except AttributeError:
                pass
            # Give the synth a moment to switch, then follow its display name.
            import time as _time

            _time.sleep(0.35)
            heard: str = ""
            try:
                heard = juno.get_patch_name(timeout=0.8)
            except Exception as e:
                logger.debug(f"selectLibraryPatch: name re-read failed: {e}")
            # Synth truth wins; library row name is the fallback.
            resolved = (heard if isinstance(heard, str) else "") or str(name or "")
            if resolved:
                self._patch_name = resolved[:12]
                self.patch_state.common.name = resolved[:12]
            try:
                mode = juno.get_sound_mode(timeout=0.5)
                mode_str = mode.name if hasattr(mode, "name") else str(mode)
                self._sound_mode = mode_str
                self.patch_state.sound_mode = mode_str
            except Exception:
                pass
            self.patchInfoChanged.emit(self._patch_name, self._sound_mode)
            # Pull the full sounding state so editors follow the auditioned patch.
            try:
                self.syncPatchFromSynth()
            except Exception as e:
                logger.debug(f"selectLibraryPatch: full sync failed: {e}")
            self._set_current_slot_ref(int(msb), int(lsb), int(pc),
                                       "drum" if int(msb) == 86 else "patch")
            self._pending_view = "JUNO PCM"
            return True
        except Exception as e:
            logger.warning(f"selectLibraryPatch failed: {e}")
            return False

    def _apply_patch_selected(self, msb: int, lsb: int, pc: int) -> None:
        """Offline half of a patch audition (mode + ref + OK destination)."""
        self._sound_mode = "PATCH"
        self.patch_state.sound_mode = "PATCH"
        self.patchInfoChanged.emit(self._patch_name, self._sound_mode)
        try:
            self._emit_fx_editor_signals()
        except Exception:
            pass
        self._set_current_slot_ref(int(msb), int(lsb), int(pc),
                                   "drum" if int(msb) == 86 else "patch")
        self._pending_view = "JUNO PCM"


