"""Patch bridge mixin: Tone TVF, TVA, pitch, envelopes, waves, MFX, master FX and sculptor."""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Optional

from PyQt6.QtCore import QTimer, pyqtProperty, pyqtSignal, pyqtSlot

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
    chain_outputs,
    is_direct,
    mfx_chain,
    tone_send_attrs,
)
from ...core.sysex import ADDR_SETUP
from ...core.waves import WaveCatalogManager
from .base import BridgeBaseMixin

logger = logging.getLogger(__name__)

# VA oscillator chips: INTA wave numbers each chip covers. SQR includes the
# JP8 pulse widths and the PWM waves the PULSE WIDTH / PWM faders pick.
VA_WAVE_CHIPS = (
    (579,),                                                       # SAW
    (600, 612, 613, 614, 615, 616, 617, 1326, 1327, 1328, 1329),  # SQR
    (621, 622),                                                   # TRI
    (625, 1322),                                                  # SIN
    (637,),                                                       # NOISE
)
VA_WAVE_PLUS = len(VA_WAVE_CHIPS)  # any other wave, picked in the wave browser
VA_SQR = 1
VA_CHIP_WAVES = (579, None, 621, 1322, 637)  # SQR follows PULSE WIDTH / PWM
VA_PW_WAVES = {10: 612, 15: 613, 25: 614, 30: 615, 40: 616, 45: 617, 50: 600}
VA_PWM_ON = 20  # PWM depth from which a PWM wave replaces the fixed pulse


def va_wave_chip(bank: str, wave_num: int) -> int:
    """VA chip index for a tone's wave (VA_WAVE_PLUS for any other wave)."""
    if (bank or "").upper() == "INTA":
        for i, nums in enumerate(VA_WAVE_CHIPS):
            if wave_num in nums:
                return i
    return VA_WAVE_PLUS


class PatchBridgeMixin(BridgeBaseMixin):
    """Patch parameter editing, 4-tone sculpting, envelopes, master FX, and routing."""

    selectedToneChanged = pyqtSignal(int)
    linkedModeChanged = pyqtSignal(bool)
    toneLevelsChanged = pyqtSignal(int, int, int, int)
    toneWavesChanged = pyqtSignal()
    toneMutesChanged = pyqtSignal()
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

    def _init_patch(self) -> None:
        """Editor state: selected tone, waves, header name/mode, routing redraws."""
        self._sync_busy: bool = False
        self._wave_catalog = WaveCatalogManager.get_instance()
        self._selected_tone: int = 1
        self._linked_mode: bool = False
        self._refresh_tone_waves()
        self._patch_name: str = self.patch_state.common.name
        self._sound_mode: str = self.patch_state.sound_mode
        # Routing schematic: anything that changes the signal path redraws it
        for sig in (self.routingChanged, self.perfPartsChanged, self.perfFxChanged,
                    self.mfxParamsChanged, self.chorusParamsChanged,
                    self.reverbParamsChanged, self.patchInfoChanged,
                    self.toneMutesChanged, self.toneLevelsChanged):
            sig.connect(self._emit_routing_graph)

    def _refresh_tone_waves(self) -> None:
        """Re-look up the 4 tones' wave info (call after a tone wave changes)."""
        self._cached_tone_wave_data: list[dict] = [
            self._wave_catalog.get_wave(t.wave_bank_l, t.wave_num_l) for t in self.patch_state.tones
        ]

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

    # Engine pages whose shared controls (the sculptor) always act on all 4 tones;
    # their per-tone controls (oscillators) act on one tone. The PCM page's
    # link switch does not apply there.
    SCULPT_VIEWS = ("VECTOR", "WAVETABLE", "VA")

    def _sculpt_view(self) -> bool:
        return str(getattr(self, "_active_view", "")) in self.SCULPT_VIEWS

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

    @pyqtProperty(int, notify=vaParamsChanged)
    def masterFine(self) -> int:
        """Master fine tune in cents: the 4 tones' average (their detune spreads around it)."""
        return round(sum(t.fine_tune for t in self.patch_state.tones) / 4) - 64

    @pyqtProperty(int, notify=portamentoTimeChanged)
    def portamentoTime(self) -> int:
        return self.patch_state.common.portamento_time

    @pyqtProperty(bool, notify=portamentoSwitchChanged)
    def portamentoSwitch(self) -> bool:
        return self.patch_state.common.portamento_switch

    @pyqtProperty(bool, notify=legatoSwitchChanged)
    def legatoSwitch(self) -> bool:
        return self.patch_state.common.legato_switch

    def _lfo_data(self, n: int) -> dict:
        t = self._active_tone()

        def g(field: str):
            return getattr(t, f"lfo{n}_{field}")

        return {"rate": g("rate"), "wave": g("wave_str"),
                "pitchDepth": g("pitch_depth") - 64, "tvfDepth": g("tvf_depth") - 64,
                "tvaDepth": g("tva_depth") - 64, "panDepth": g("pan_depth") - 64,
                "delayTime": g("delay_time"), "fadeMode": g("fade_mode_str"),
                "fadeTime": g("fade_time")}

    @pyqtProperty("QVariantMap", notify=lfoParamsChanged)
    def lfo1Data(self) -> dict:
        """The selected tone's LFO1 (depths -63..+63, wave and fade mode by name)."""
        return self._lfo_data(1)

    @pyqtProperty("QVariantMap", notify=lfoParamsChanged)
    def lfo2Data(self) -> dict:
        return self._lfo_data(2)

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
    def lfoWaveNames(self) -> list:
        return list(LFO_WAVE_NAMES)

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

    @pyqtProperty("QVariantList", notify=routingGraphChanged)
    def routingPitfalls(self) -> list:
        return self._sorted_notes(self._cached_routing_graph())

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

    @pyqtProperty(int, notify=toneWavesChanged)
    def vaOsc1Wave(self) -> int:
        t = self.patch_state.tones[0]
        return va_wave_chip(t.wave_bank_l, t.wave_num_l)

    @pyqtProperty(int, notify=toneWavesChanged)
    def vaOsc2Wave(self) -> int:
        t = self.patch_state.tones[1]
        return va_wave_chip(t.wave_bank_l, t.wave_num_l)

    @pyqtProperty(int, notify=toneWavesChanged)
    def vaOsc3Wave(self) -> int:
        t = self.patch_state.tones[2]
        return va_wave_chip(t.wave_bank_l, t.wave_num_l)

    @pyqtProperty(int, notify=toneWavesChanged)
    def vaOsc4Wave(self) -> int:
        t = self.patch_state.tones[3]
        return va_wave_chip(t.wave_bank_l, t.wave_num_l)

    @pyqtProperty(int, notify=analogFeelChanged)
    def analogFeel(self) -> int:
        return self.patch_state.common.analog_feel

    # Per-tone parameters: UI name -> (ToneState attr, UI min, UI max, raw offset
    # or raw(ui) function, synth writer, macro rebase key, signals, envelope).
    # The writer is ("tvf" | "tva" | "pitch", keyword of set_tone_<group>) or
    # "tvf_env" / "tva_env" (the whole envelope block).
    _TONE_PARAMS = {
        "cutoff": ("tvf_cutoff", 0, 127, 0, ("tvf", "cutoff"), "tvf_cutoff",
                   ("masterCutoffChanged",), None),
        "reso": ("tvf_resonance", 0, 127, 0, ("tvf", "resonance"), "tvf_resonance",
                 ("masterResoChanged",), None),
        "tvf_keyfollow": ("tvf_cutoff_keyfollow", -100, 100, lambda v: 64 + v // 10,
                          ("tvf", "key_follow"), "tvf_keyfollow", ("tvfKeyFollowChanged",), None),
        "tvf_env_depth": ("tvf_env_depth", -63, 63, 64, ("tvf", "env_depth"), "tvf_env_depth",
                          ("tvfEnvDepthChanged",), "TVF"),
        "tvf_velo": ("tvf_env_velo_sens", 0, 127, 0, ("tvf", "env_vel_sens"), None,
                     ("tvfVeloSensChanged",), "TVF"),
        "tvf_attack": ("tvf_attack", 0, 127, 0, "tvf_env", "tvf_attack", ("tvfAttackChanged",), "TVF"),
        "tvf_decay": ("tvf_decay", 0, 127, 0, "tvf_env", "tvf_decay", ("tvfDecayChanged",), "TVF"),
        "tvf_sustain": ("tvf_sustain", 0, 127, 0, "tvf_env", "tvf_sustain", ("tvfSustainChanged",), "TVF"),
        "tvf_release": ("tvf_release", 0, 127, 0, "tvf_env", "tvf_release", ("tvfReleaseChanged",), "TVF"),
        "tva_attack": ("tva_attack", 0, 127, 0, "tva_env", "tva_attack",
                       ("tvaAttackChanged", "masterAttackChanged"), "TVA"),
        "tva_decay": ("tva_decay", 0, 127, 0, "tva_env", "tva_decay", ("tvaDecayChanged",), "TVA"),
        "tva_sustain": ("tva_sustain", 0, 127, 0, "tva_env", "tva_sustain", ("tvaSustainChanged",), "TVA"),
        "tva_release": ("tva_release", 0, 127, 0, "tva_env", "tva_release",
                        ("tvaReleaseChanged", "masterReleaseChanged"), "TVA"),
        "tva_pan": ("pan", -64, 63, 64, ("tva", "pan"), "tva_pan", ("tvaPanChanged",), None),
        "tva_velo": ("tva_velo_sens", 0, 127, 0, ("tva", "env_vel_sens"), None,
                     ("tvaVeloSensChanged",), "TVA"),
        "pitch_coarse": ("coarse_tune", -48, 48, 64, ("pitch", "coarse"), "pitch_coarse",
                         ("pitchCoarseChanged",), None),
    }

    @contextmanager
    def _tone_writes(self):
        """Queue tone writes for the writer thread: a LINK or sculptor edit
        writes all 4 tones on every move, which must not block the UI."""
        if self.juno is None:
            yield
            return
        with self.juno.coalesced_writes():
            yield

    def _edit_tones(self, all_tones: bool) -> list[ToneState]:
        """All 4 tones (sculptor) or the selected / linked ones (PCM editors)."""
        return list(self.patch_state.tones) if all_tones else self._target_tones()

    def _set_tone_param(self, name: str, val: int, all_tones: bool = False) -> None:
        attr, lo, hi, raw_of, writer, rebase, signals, env = self._TONE_PARAMS[name]
        v = max(lo, min(hi, int(val)))
        raw = raw_of(v) if callable(raw_of) else v + raw_of
        targets = self._edit_tones(all_tones)
        with self._tone_writes():
            for t in targets:
                setattr(t, attr, raw)
                if writer == "tvf_env":
                    self._push_tvf_env(t)
                elif writer == "tva_env":
                    self._push_tva_env(t)
                elif self.juno:
                    try:
                        getattr(self.juno, f"set_tone_{writer[0]}")(t.tone_index, **{writer[1]: raw})
                    except Exception as e:
                        logger.error(f"Error setting {name} on synth: {e}")
        if rebase:
            self._rebaseDirect([(f"tone.{t.tone_index}.{rebase}", raw) for t in targets])
        for sig in signals:
            getattr(self, sig).emit(v)
        if env:
            self.envShapeChanged.emit(env)

    def _set_tvf_type(self, type_str: str, all_tones: bool) -> None:
        idx = TVF_TYPE_NAMES.index(type_str) if type_str in TVF_TYPE_NAMES else 1
        with self._tone_writes():
            for t in self._edit_tones(all_tones):
                t.tvf_filter_type = idx
                if self.juno:
                    try:
                        self.juno.set_tone_tvf(t.tone_index, filter_type=idx)
                    except Exception as e:
                        logger.error(f"Error setting TVF filter type on synth: {e}")
        self.tvfTypeChanged.emit(type_str)

    _LFO_DEPTHS = ("pitch_depth", "tvf_depth", "tva_depth", "pan_depth")

    def _set_lfo_param(self, lfo_idx: int, param: str, val, all_tones: bool) -> None:
        """LFO 1/2 field: wave (name), rate, depths (-63..+63), delay/fade time, fade mode (name)."""
        if lfo_idx not in (1, 2):
            return
        if param == "wave":
            val = "SAW-UP" if val == "SAW" else val
            if val not in LFO_WAVE_NAMES:
                return
            field, raw = "waveform", LFO_WAVE_NAMES.index(val)
        elif param == "fade_mode":
            if val not in LFO_FADE_MODE_NAMES:
                return
            field, raw = param, LFO_FADE_MODE_NAMES.index(val)
        elif param in self._LFO_DEPTHS:
            field, raw = param, max(1, min(127, int(val) + 64))
        elif param in ("rate", "delay_time", "fade_time"):
            field, raw = param, max(0, min(127, int(val)))
        else:
            return
        targets = self._edit_tones(all_tones)
        with self._tone_writes():
            for t in targets:
                setattr(t, f"lfo{lfo_idx}_{field}", raw)
                if self.juno:
                    try:
                        self.juno.set_tone_lfo(t.tone_index, lfo_index=lfo_idx, **{field: raw})
                    except Exception as e:
                        logger.error(f"Error setting LFO{lfo_idx} {param} on synth: {e}")
        self._rebaseLfoParam(lfo_idx, param, targets)
        self.lfoParamsChanged.emit()

    @pyqtSlot(int)
    def setMasterCutoff(self, val: int) -> None:
        """TVF cutoff (0..127): the selected tone, or all 4 when linked."""
        self._set_tone_param("cutoff", val)

    @pyqtSlot(int)
    def setMasterReso(self, val: int) -> None:
        """TVF resonance (0..127): the selected tone, or all 4 when linked."""
        self._set_tone_param("reso", val)

    @pyqtSlot(int)
    def setMasterLevel(self, val: int) -> None:
        """Set Master Patch Level (0..127)."""
        clamped = max(0, min(127, int(val)))
        if self.patch_state.common.level != clamped:
            self.patch_state.common.level = clamped
            self._rebaseDirect([("common.level", clamped)])
            self.masterLevelChanged.emit(clamped)
            if self.juno:
                try:
                    self.juno.set_patch_param("level", clamped)
                except Exception as e:
                    logger.error(f"Error setting patch level: {e}")

    @pyqtSlot(str)
    def setTvfType(self, type_str: str) -> None:
        """TVF filter type (OFF, LPF, BPF, HPF, PKG, LPF2, LPF3)."""
        self._set_tvf_type(type_str, all_tones=False)

    @pyqtSlot(int)
    def setTvfKeyFollow(self, val: int) -> None:
        """TVF cutoff keyfollow (-100..+100%): the selected tone, or all 4 when linked."""
        self._set_tone_param("tvf_keyfollow", val)

    @pyqtSlot(int)
    def setTvfEnvDepth(self, depth: int) -> None:
        """TVF envelope depth (-63..+63): the selected tone, or all 4 when linked."""
        self._set_tone_param("tvf_env_depth", depth)

    @pyqtSlot(int)
    def setTvfVeloSens(self, val: int) -> None:
        """TVF velocity sensitivity (0..127): the selected tone, or all 4 when linked."""
        self._set_tone_param("tvf_velo", val)

    @pyqtSlot(int)
    def setTvfAttack(self, val: int) -> None:
        self._set_tone_param("tvf_attack", val)

    @pyqtSlot(int)
    def setTvfDecay(self, val: int) -> None:
        self._set_tone_param("tvf_decay", val)

    @pyqtSlot(int)
    def setTvfSustain(self, val: int) -> None:
        self._set_tone_param("tvf_sustain", val)

    @pyqtSlot(int)
    def setTvfRelease(self, val: int) -> None:
        self._set_tone_param("tvf_release", val)

    @pyqtSlot(int)
    def setTvaAttack(self, val: int) -> None:
        self._set_tone_param("tva_attack", val)

    @pyqtSlot(int)
    def setTvaDecay(self, val: int) -> None:
        self._set_tone_param("tva_decay", val)

    @pyqtSlot(int)
    def setTvaSustain(self, val: int) -> None:
        self._set_tone_param("tva_sustain", val)

    @pyqtSlot(int)
    def setTvaRelease(self, val: int) -> None:
        self._set_tone_param("tva_release", val)

    @pyqtSlot(int)
    def setTvaPan(self, val: int) -> None:
        """Tone pan (-64..+63, 0 = centre): the selected tone, or all 4 when linked."""
        self._set_tone_param("tva_pan", val)

    @pyqtSlot(int)
    def setTvaVeloSens(self, val: int) -> None:
        """TVA velocity sensitivity (0..127): the selected tone, or all 4 when linked."""
        self._set_tone_param("tva_velo", val)

    @pyqtSlot(int)
    def setPitchCoarse(self, val: int) -> None:
        """Coarse tune in semitones (-48..+48): the selected tone, or all 4 when linked."""
        self._set_tone_param("pitch_coarse", val)

    @pyqtSlot(int)
    def setPitchFine(self, val: int) -> None:
        """Set Tone Fine Tune in cents (-50..+50). Auto Detune owns it while on."""
        if self.patch_state.auto_detune:
            return
        clamped = max(-50, min(50, int(val)))
        raw_val = clamped + 64
        targets = self._target_tones()
        for t in targets:
            t.fine_tune = raw_val
            if not self.patch_state.auto_detune:
                self.patch_state.custom_detune_cache[t.tone_index - 1] = raw_val
            if self.juno:
                try:
                    self.juno.set_tone_pitch(t.tone_index, fine=raw_val)
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
            if self.juno:
                try:
                    self.juno.set_portamento(self.patch_state.common.portamento_switch, time=clamped)
                except Exception as e:
                    logger.error(f"Error setting portamento time on synth: {e}")

    @pyqtSlot(bool)
    def setPortamentoSwitch(self, enabled: bool) -> None:
        """Toggle Patch Portamento Switch."""
        if self.patch_state.common.portamento_switch != enabled:
            self.patch_state.common.portamento_switch = enabled
            self.portamentoSwitchChanged.emit(enabled)
            if self.juno:
                try:
                    self.juno.set_portamento(enabled)
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
            if self.juno:
                try:
                    self.juno.set_legato(enabled)
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
            if self.juno:
                try:
                    self.juno.set_patch_analog_feel(clamped)
                except Exception as e:
                    logger.error(f"Error setting analog feel on synth: {e}")

    @pyqtSlot(int, str, "QVariant")
    def setLfoParam(self, lfo_idx: int, param: str, val) -> None:
        """LFO 1 or 2 parameter of the selected tone (or all 4 when linked)."""
        self._set_lfo_param(lfo_idx, param, val, all_tones=False)

    @pyqtSlot(int)
    def sculptCutoff(self, val: int) -> None:
        """TVF cutoff (0..127): all 4 tones (sculptor)."""
        self._set_tone_param("cutoff", val, all_tones=True)

    @pyqtSlot(int)
    def sculptReso(self, val: int) -> None:
        """TVF resonance (0..127): all 4 tones (sculptor)."""
        self._set_tone_param("reso", val, all_tones=True)

    @pyqtSlot(str)
    def sculptTvfType(self, type_str: str) -> None:
        self._set_tvf_type(type_str, all_tones=True)

    @pyqtSlot(int)
    def sculptTvfKeyFollow(self, val: int) -> None:
        """TVF cutoff keyfollow (-100..+100%): all 4 tones (sculptor)."""
        self._set_tone_param("tvf_keyfollow", val, all_tones=True)

    @pyqtSlot(int)
    def sculptTvfEnvDepth(self, depth: int) -> None:
        """TVF envelope depth (-63..+63): all 4 tones (sculptor)."""
        self._set_tone_param("tvf_env_depth", depth, all_tones=True)

    @pyqtSlot(int)
    def sculptTvfVeloSens(self, val: int) -> None:
        """TVF velocity sensitivity (0..127): all 4 tones (sculptor)."""
        self._set_tone_param("tvf_velo", val, all_tones=True)

    @pyqtSlot(int)
    def sculptTvfAttack(self, val: int) -> None:
        self._set_tone_param("tvf_attack", val, all_tones=True)

    @pyqtSlot(int)
    def sculptTvfDecay(self, val: int) -> None:
        self._set_tone_param("tvf_decay", val, all_tones=True)

    @pyqtSlot(int)
    def sculptTvfSustain(self, val: int) -> None:
        self._set_tone_param("tvf_sustain", val, all_tones=True)

    @pyqtSlot(int)
    def sculptTvfRelease(self, val: int) -> None:
        self._set_tone_param("tvf_release", val, all_tones=True)

    @pyqtSlot(int)
    def sculptTvaPan(self, val: int) -> None:
        """Tone pan (-64..+63, 0 = centre): all 4 tones (sculptor)."""
        self._set_tone_param("tva_pan", val, all_tones=True)

    @pyqtSlot(int)
    def sculptTvaVeloSens(self, val: int) -> None:
        """TVA velocity sensitivity (0..127): all 4 tones (sculptor)."""
        self._set_tone_param("tva_velo", val, all_tones=True)

    @pyqtSlot(int)
    def sculptTvaAttack(self, val: int) -> None:
        self._set_tone_param("tva_attack", val, all_tones=True)

    @pyqtSlot(int)
    def sculptTvaDecay(self, val: int) -> None:
        self._set_tone_param("tva_decay", val, all_tones=True)

    @pyqtSlot(int)
    def sculptTvaSustain(self, val: int) -> None:
        self._set_tone_param("tva_sustain", val, all_tones=True)

    @pyqtSlot(int)
    def sculptTvaRelease(self, val: int) -> None:
        self._set_tone_param("tva_release", val, all_tones=True)

    @pyqtSlot(int, str, "QVariant")
    def sculptLfoParam(self, lfo_idx: int, param: str, val) -> None:
        """LFO 1 or 2 parameter of all 4 tones (sculptor)."""
        self._set_lfo_param(lfo_idx, param, val, all_tones=True)

    @pyqtSlot(int)
    def sculptPitchCoarse(self, val: int) -> None:
        """Coarse tune in semitones (-48..+48): all 4 tones (sculptor)."""
        self._set_tone_param("pitch_coarse", val, all_tones=True)

    @pyqtSlot(int)
    def sculptPitchFine(self, val: int) -> None:
        """Master fine tune (-50..+50 cents): moves all 4 tones together, keeping
        their detune (manual or Auto Detune, whose saved manual one moves too)."""
        delta = max(-50, min(50, int(val))) - self.masterFine
        ps = self.patch_state
        for i, t in enumerate(ps.tones):
            t.fine_tune = max(14, min(114, t.fine_tune + delta))
            ps.custom_detune_cache[i] = (max(14, min(114, ps.custom_detune_cache[i] + delta))
                                         if ps.auto_detune else t.fine_tune)
            if self.juno:
                try:
                    self.juno.set_tone_pitch(t.tone_index, fine=t.fine_tune)
                except Exception as e:
                    logger.error(f"Error sculpting fine tune on synth: {e}")
        self._rebaseDirect([(f"tone.{t.tone_index}.pitch_fine", t.fine_tune) for t in ps.tones])
        self.pitchFineChanged.emit(self.pitchFine)
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
        t.env_forget_broken_original("tvf")
        if self.juno:
            try:
                self.juno.set_tone_tvf_env(t.tone_index, t.tvf_env_block())
            except Exception as e:
                logger.error(f"Error setting TVF envelope block on synth: {e}")

    def _push_tva_env(self, t: ToneState) -> None:
        """Send the raw TVA MSEG block [T1..T4, L1..L3] for a tone."""
        t.env_forget_broken_original("tva")
        if self.juno:
            try:
                self.juno.set_tone_tva_env(t.tone_index, t.tva_env_block())
            except Exception as e:
                logger.error(f"Error setting TVA envelope block on synth: {e}")

    def _push_pitch_env(self, t: ToneState) -> None:
        """Send all Pitch Envelope parameters for a tone (one block DT1, not 14)."""
        t.env_forget_broken_original("pitch")
        if self.juno:
            try:
                self.juno.set_tone_pitch_env_block(t.tone_index, [
                    t.pitch_env_depth, t.pitch_env_vel_sens,
                    t.pitch_env_t1_vel_sens, t.pitch_env_t4_vel_sens, t.pitch_env_time_keyfollow,
                    t.pitch_env_t1, t.pitch_env_t2, t.pitch_env_t3, t.pitch_env_t4,
                    t.pitch_env_l0, t.pitch_env_l1, t.pitch_env_l2, t.pitch_env_l3, t.pitch_env_l4])
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
        key = {"TVF": "tvf", "TVA": "tva"}.get(env, "pitch")
        # ADSR switch: on when the curve is a plain ADSR; it can go back when the switch made it
        mode = {"adsr": t.env_is_adsr(key), "restorable": key in t.env_originals}
        return {**self._envSegments(t, env), **mode}

    def _envSegments(self, t: ToneState, env: str) -> dict:
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
            "bipolar": True, "custom": not t.env_is_adsr("pitch"),
            "mods": {
                "depth": t.pitch_env_depth_st,
                "velSens": t.pitch_env_vel_sens_bipolar,
                "t1VelSens": t.pitch_env_t1_vel_sens_bipolar,
                "t4VelSens": t.pitch_env_t4_vel_sens_bipolar,
                "timeKf": t.pitch_env_time_kf_bipolar,
            },
        }

    @pyqtSlot(str, bool)
    def setEnvAdsr(self, env: str, on: bool) -> None:
        """ADSR switch of 'TVF' | 'TVA' | 'PITCH' (edited tone, or all when linked).

        On: the curve becomes a plain ADSR, the original is kept. Off: the
        original comes back exactly (ADSR edits since are dropped)."""
        env = env.upper()
        key = {"TVF": "tvf", "TVA": "tva"}.get(env, "pitch")
        push = {"tvf": self._push_tvf_env, "tva": self._push_tva_env, "pitch": self._push_pitch_env}[key]
        # The sculptor's envelopes are the 4 tones' together
        for t in (self.patch_state.tones if self._sculpt_view() else self._target_tones()):
            if on:
                t.env_to_adsr(key)
            elif not t.env_restore(key):
                continue
            push(t)
            self._rebaseDirect([(f"tone.{t.tone_index}.{p}", getattr(t, p)) for p in
                                ([f"{key}_{s}" for s in ("attack", "decay", "sustain", "release")]
                                 if key != "pitch" else
                                 [f"pitch_env_{s}" for s in ("attack", "decay", "sustain", "release")])])
        self._emit_env_signals(env)

    def _emit_env_signals(self, env: str) -> None:
        if env == "TVF":
            for sig, v in ((self.tvfAttackChanged, self.tvfAttack), (self.tvfDecayChanged, self.tvfDecay),
                           (self.tvfSustainChanged, self.tvfSustain), (self.tvfReleaseChanged, self.tvfRelease)):
                sig.emit(v)
        elif env == "TVA":
            for sig, v in ((self.tvaAttackChanged, self.tvaAttack), (self.tvaDecayChanged, self.tvaDecay),
                           (self.tvaSustainChanged, self.tvaSustain), (self.tvaReleaseChanged, self.tvaRelease)):
                sig.emit(v)
            self.masterAttackChanged.emit(self.masterAttack)
            self.masterReleaseChanged.emit(self.masterRelease)
        else:
            self.pitchEnvChanged.emit()
        self.envShapeChanged.emit(env)

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

            if self.juno:
                try:
                    setter = (self.juno.set_tone_tvf if env == "TVF"
                              else self.juno.set_tone_tva)
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

    CHORUS_PARAM_SPECS: dict[str, tuple[str, int, int]] = {
        "type": ("chorus_type", 0, 3),
        "level": ("chorus_level", 0, 127),
        "toReverb": ("chorus_to_reverb", 0, 2),
        "rate": ("chorus_rate", 0, 127),
        "depth": ("chorus_depth", 0, 127),
        "preDelay": ("chorus_predelay", 0, 127),
        "feedback": ("chorus_feedback", 0, 127),
    }

    REVERB_PARAM_SPECS: dict[str, tuple[str, int, int]] = {
        "type": ("reverb_type", 0, 5),
        "level": ("reverb_level", 0, 127),
        "time": ("reverb_time", 0, 127),
        "damp": ("reverb_damp", 0, 127),
        "preDelay": ("reverb_predelay", 0, 127),
        "diffusion": ("reverb_diffusion", 0, 127),
        "tone": ("reverb_tone", 0, 127),
    }

    @pyqtSlot(str, int)
    def setChorusParam(self, param: str, val: int) -> None:
        """Set a chorus parameter on the edit target (origin-resolved in PERFORM)."""
        self._set_master_fx_param("chorus", param, val)

    def _set_master_fx_param(self, block: str, param: str, val: int) -> None:
        spec = (self.CHORUS_PARAM_SPECS if block == "chorus" else self.REVERB_PARAM_SPECS).get(param)
        if not spec:
            return
        attr, lo, hi = spec
        clamped = max(lo, min(hi, int(val)))
        t = self._fx_edit_target(block)
        setattr(t.store, attr, clamped)
        juno = self.juno
        if juno is not None:
            try:
                if block == "chorus" and param in ("type", "level", "toReverb"):
                    t.write_chorus(juno)
                elif block == "chorus":
                    t.write_chorus_detail(juno, param, clamped)
                elif param in ("type", "level"):
                    t.write_reverb(juno)
                else:
                    t.write_reverb_detail(juno, param, clamped)
            except Exception as e:
                logger.error(f"Error setting {block} {param} on synth: {e}")
        if t.kind == "patch":
            (self._rebaseChorusParam if block == "chorus" else self._rebaseReverbParam)(param)
            self.macrosChanged.emit()
        else:
            self._rebasePerfFx(block, param, clamped)
            self.perfFxChanged.emit()
        (self.chorusParamsChanged if block == "chorus" else self.reverbParamsChanged).emit()
        self.routingChanged.emit()

    @pyqtSlot(str, int)
    def setReverbParam(self, param: str, val: int) -> None:
        """Set a reverb parameter on the edit target (origin-resolved in PERFORM)."""
        self._set_master_fx_param("reverb", param, val)

    @staticmethod
    def _apply_mfx_algo(t, algo_id: int) -> int:
        """Select an MFX algorithm on a target's store: 0 bypasses, a real one
        loads the catalog default params. Returns the clamped id."""
        clamped = max(0, min(80, int(algo_id)))
        t.set_mfx("type", clamped)
        if clamped > 0:
            t.set_mfx("last", clamped)
            algo = get_mfx_algo(clamped)
            params = t.mfx("params")
            for pp in (algo or {}).get("params", []):
                if 0 <= pp["idx"] < 32:
                    params[pp["idx"]] = pp.get("val", 0)
        return clamped

    @staticmethod
    def _push_mfx_algo(juno, t, clamped: int) -> None:
        """Push an algo-select to hardware (catalog defaults included)."""
        try:
            t.write_mfx(juno, mfx_type=clamped)
            algo = get_mfx_algo(clamped) if clamped > 0 else None
            idxs = [pp["idx"] for pp in (algo or {}).get("params", []) if 0 <= pp["idx"] < 32]
            if idxs:
                t.write_mfx_params(juno, list(t.mfx("params")[:max(idxs) + 1]))
        except Exception as e:
            logger.error(f"Error setting MFX type on synth: {e}")

    @pyqtSlot(int)
    def setMfxAlgoId(self, algo_id: int) -> None:
        """Select active MFX Algorithm (0..80), origin-resolved in PERFORM mode."""
        t = self._fx_edit_target("mfx")
        clamped = self._apply_mfx_algo(t, algo_id)
        if self.juno is not None:
            self._push_mfx_algo(self.juno, t, clamped)
        self._emit_fx_editor_signals()

    @pyqtSlot(int, int)
    def setMfxParam(self, param_index: int, val: int) -> None:
        """Set an individual MFX parameter (0..31), origin-resolved in PERFORM mode."""
        if not (0 <= param_index < 32):
            return
        t = self._fx_edit_target("mfx")
        t.mfx("params")[param_index] = int(val)
        if self.juno is not None:
            try:
                t.write_mfx_params(self.juno, [int(val)], int(param_index))
            except Exception as e:
                logger.error(f"Error setting MFX param {param_index} on synth: {e}")
        self.mfxValuesChanged.emit()
        if t.kind != "patch":
            self.perfFxChanged.emit()

    @pyqtSlot(bool)
    def setMfxBypass(self, bypassed: bool) -> None:
        """Toggle MFX Bypass switch (origin-resolved in PERFORM mode)."""
        t = self._fx_edit_target("mfx")
        mfx_type = 0 if bypassed else int(t.mfx("last") or 15)
        t.set_mfx("type", mfx_type)
        if self.juno is not None:
            try:
                t.write_mfx(self.juno, mfx_type=mfx_type)
            except Exception as e:
                logger.error(f"Error toggling MFX bypass on synth: {e}")
        self._emit_fx_editor_signals()

    @pyqtSlot(str, int)
    def setMfxSend(self, send_type: str, val: int) -> None:
        """Set MFX Dry, Chorus, or Reverb send level (0..127), origin-resolved."""
        if send_type not in ("dry", "chorus", "reverb"):
            return
        clamped = max(0, min(127, int(val)))
        t = self._fx_edit_target("mfx")
        t.set_mfx(send_type, clamped)
        if self.juno is not None:
            try:
                t.write_mfx_sends(self.juno)
            except Exception as e:
                logger.error(f"Error setting MFX sends on synth: {e}")
        if t.kind == "patch":
            self._rebaseDirect([(f"effects.mfx_{send_type}_send", clamped)])
        else:
            self._rebasePerfFx(f"mfx{self.editingPerfMfx}", send_type, clamped)
            self.perfFxChanged.emit()
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
            units = [dict(self._rail_mfx_entry(n), slot=n) for n in chain]
            m = units[-1]
            c, r = self._rail_cho_entry(), self._rail_rev_entry()
            return {
                "part": part, "chain": chain, "mfxSource": int(m["source"]),
                "choSource": int(c["source"]), "revSource": int(r["source"]),
                "mfx": chain_outputs([{"slot": u["slot"], "type": int(u["type"]),
                                       "dry": int(u["drySend"]), "cho": int(u["chorusSend"]),
                                       "rev": int(u["reverbSend"])} for u in units]),
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
        label = "MFX" + "→".join(map(str, inp["chain"])) if perform else "MFX"
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
            m, chain = inp["mfx"], inp["chain"]
            if g["edges"]["in->mfx"]["active"] and len(m["reached"]) < len(chain):
                cut = m["reached"][-1]
                g["notes"].insert(0, {
                    "type": "MFX_CHAIN_CUT", "severity": "caution",
                    "title": f"Chain stops at MFX{cut}",
                    "description": f"MFX{cut}'s output level is 0, so "
                                   + ", ".join(f"MFX{n}" for n in chain[len(m['reached']):])
                                   + " get no sound."})
            early = [f"MFX{n}" for n in dict.fromkeys(m["choUnits"] + m["revUnits"]) if n != chain[-1]]
            if g["edges"]["in->mfx"]["active"] and early:
                g["notes"].append({
                    "type": "MFX_CHAIN_SENDS", "severity": "info",
                    "title": "Every MFX in the chain sends",
                    "description": " and ".join(early) + " also feed chorus/reverb with their own "
                                   "sends, not only the last unit."})
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
        # Many signals feed this and one part switch fires most of them:
        # redraw once per event-loop pass (a redraw costs ~20 ms on the Pi)
        self._routing_graph_cache = None
        if not getattr(self, "_routing_emit_pending", False):
            self._routing_emit_pending = True
            QTimer.singleShot(0, self._flush_routing_graph)

    def _flush_routing_graph(self) -> None:
        self._routing_emit_pending = False
        self.routingGraphChanged.emit()

    def _cached_routing_graph(self) -> dict:
        # Built once per change; QML reads it from several bindings
        g = getattr(self, "_routing_graph_cache", None)
        if g is None:
            g = self._routing_graph_cache = self._build_routing_graph()
        return g

    @pyqtProperty("QVariantMap", notify=routingGraphChanged)
    def routingGraph(self) -> dict:
        return self._cached_routing_graph()

    @pyqtProperty(int, notify=routingGraphChanged)
    def patchOutputAssign(self) -> int:
        return int(self.patch_state.common.patch_output_assign)

    @staticmethod
    def _sorted_notes(graph: dict) -> list:
        order = {"warning": 0, "caution": 1, "info": 2}
        return sorted(graph["notes"], key=lambda n: order.get(n["severity"], 3))

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

            if self.juno:
                try:
                    self.juno.set_matrix_control(
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
            if self.juno:
                try:
                    self.juno.set_tone_matrix_switch(tone_index, ctrl_index, dest_index, sw_val)
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
                if self.juno:
                    try:
                        self.juno.set_tone_step_lfo_step(tone.tone_index, step_index, clamped)
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
            if self.juno:
                try:
                    self.juno.set_tone_step_lfo_steps(tone.tone_index, clamped_steps)
                except Exception as e:
                    logger.error(f"Error setting all Step LFO steps on tone {tone.tone_index}: {e}")
        self.stepLfoChanged.emit()

    @pyqtSlot(str, "QVariant")
    def setStepLfoParam(self, param: str, val) -> None:
        """Set the Step LFO curve (step type) of the target tones."""
        if param == "curve":
            step_type = max(0, min(1, int(val)))
            targets = self._target_tones()
            for tone in targets:
                tone.step_lfo_type = step_type
                if self.juno:
                    try:
                        self.juno.set_tone_step_lfo_type(tone.tone_index, step_type)
                    except Exception as e:
                        logger.error(f"Error setting Step LFO type on tone {tone.tone_index}: {e}")
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
                if self.juno:
                    try:
                        self.juno.set_tone_lfo(tone.tone_index, lfo_index=1, waveform=new_wave)
                    except Exception as e:
                        logger.error(f"Error assigning LFO 1 wave on tone {tone.tone_index}: {e}")
            else:
                new_wave = 0 if tone.lfo2_waveform == 12 else 12  # 0: SIN, 12: STEP
                tone.lfo2_waveform = new_wave
                if self.juno:
                    try:
                        self.juno.set_tone_lfo(tone.tone_index, lfo_index=2, waveform=new_wave)
                    except Exception as e:
                        logger.error(f"Error assigning LFO 2 wave on tone {tone.tone_index}: {e}")
        self.lfoParamsChanged.emit()
        self.stepLfoChanged.emit()

    @pyqtSlot(int, int)
    def setVaOscCoarse(self, osc_index: int, val: int) -> None:
        """Set coarse tune in semitones for oscillator 1..4."""
        if 1 <= osc_index <= 4:
            clamped = max(-48, min(48, int(val)))
            raw = clamped + 64
            t = self.patch_state.tones[osc_index - 1]
            t.coarse_tune = raw
            if self.juno:
                try:
                    self.juno.set_tone_pitch(osc_index, coarse=raw)
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
            if self.juno:
                try:
                    self.juno.set_tone_pitch(osc_index, fine=raw)
                except Exception as e:
                    logger.error(f"Error setting OSC fine on synth: {e}")
            self.pitchFineChanged.emit(self.pitchFine)
            self.vaParamsChanged.emit()

    @pyqtSlot(int, int)
    def setVaOscLevel(self, osc_index: int, val: int) -> None:
        """Set level for oscillator 1..4."""
        self.setToneLevel(osc_index, val)
        self.vaParamsChanged.emit()

    def _va_square_wave(self, i: int) -> int:
        """SQR wave for oscillator index 0..3: a PWM wave, else the fixed pulse width."""
        m = self.patch_state.va_pwm[i]
        if m >= VA_PWM_ON:
            return 1326 if m < 40 else (1327 if m < 60 else (1328 if m < 80 else 1329))
        return VA_PW_WAVES.get(self.patch_state.va_pw[i], 600)

    def _va_chip(self, osc_index: int) -> int:
        t = self.patch_state.tones[osc_index - 1]
        return va_wave_chip(t.wave_bank_l, t.wave_num_l)

    @pyqtSlot(int, int)
    def setVaOscWave(self, osc_index: int, chip: int) -> None:
        """Pick a VA chip wave (SAW/SQR/TRI/SIN/NOISE) for oscillator 1..4."""
        if 1 <= osc_index <= 4 and 0 <= chip < VA_WAVE_PLUS:
            wnum = self._va_square_wave(osc_index - 1) if chip == VA_SQR else VA_CHIP_WAVES[chip]
            self.setToneWave(osc_index, "INTA", wnum)

    @pyqtSlot(int, int)
    def setVaOscPw(self, osc_index: int, val: int) -> None:
        """Set Pulse Width for oscillator 1..4 (re-picks the SQR wave)."""
        if 1 <= osc_index <= 4:
            self.patch_state.va_pw[osc_index - 1] = int(val)
            if self._va_chip(osc_index) == VA_SQR:
                self.setVaOscWave(osc_index, VA_SQR)
            self.vaParamsChanged.emit()

    @pyqtSlot(int, int)
    def setVaOscPwm(self, osc_index: int, val: int) -> None:
        """Set Pulse Width Modulation depth for oscillator 1..4 (re-picks the SQR wave)."""
        if 1 <= osc_index <= 4:
            self.patch_state.va_pwm[osc_index - 1] = max(0, min(100, int(val)))
            if self._va_chip(osc_index) == VA_SQR:
                self.setVaOscWave(osc_index, VA_SQR)
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
                if self.juno:
                    try:
                        self.juno.set_tone_pitch(idx, fine=raw)
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
        """Distribute symmetrical auto-detuning across all 4 oscillators, around
        the master fine tune (their current average)."""
        if not self.patch_state.auto_detune:
            return
        d = self.patch_state.auto_detune_cents
        spreads = [-d, d, -(d // 2), (d // 2)]
        center = 64 + self.masterFine

        for idx, offset in enumerate(spreads, start=1):
            raw = max(14, min(114, center + offset))
            self.patch_state.tones[idx - 1].fine_tune = raw
            if self.juno:
                try:
                    self.juno.set_tone_pitch(idx, fine=raw)
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
        """Read the sounding patch from the synth into the editors.

        async_mode reads on the job worker and applies on the UI thread.
        """
        juno = self.juno
        if juno is None:
            logger.info("Cannot sync: No Roland synthesizer connected.")
            return
        if self._sync_busy:
            logger.info("Hardware sync already in progress, ignoring request.")
            return
        self._set_sync_busy(True)
        if not async_mode:
            self._apply_synced_patch(self._read_synced_patch(juno))
        elif not self._start_job("sync", "Reading the patch…",
                                 lambda progress: self._read_synced_patch(juno),
                                 done=self._apply_synced_patch):
            logger.info("Sync skipped: another synth job is running.")
            self._set_sync_busy(False)

    @staticmethod
    def _read_synced_patch(juno):
        try:
            return juno.read_full_patch(timeout=1.0)
        except Exception as e:
            logger.warning(f"Could not read full patch: {e}")
            return None

    def _apply_synced_patch(self, state) -> None:
        """Take a patch read from the synth into the editors (UI thread)."""
        try:
            if not isinstance(state, PatchState):
                return
            # Keep the macro assignments (bases re-capture from the new sound)
            # and the performance: a patch read carries neither.
            old = self.patch_state
            state.macros = old.macros
            state.perf_parts, state.perf_name = old.perf_parts, old.perf_name
            state.perf_fx, state.active_perf_part = old.perf_fx, old.active_perf_part
            self.patch_state = state
            self._resetMacroBases()
            state.effects.routing_preset = ""  # no routing preset is selected on the synth
            self._patch_name = state.common.name
            self._sound_mode = state.sound_mode
            self.vector.tone_levels = tuple(t.level for t in state.tones[:4])
            state.custom_detune_cache = [t.fine_tune for t in state.tones]
            self.patchInfoChanged.emit(str(self._patch_name), str(self._sound_mode))
            self._refresh_tone_waves()
            self._emit_all_state_signals()
            logger.info(f"Sync complete. Synced patch: '{self._patch_name}'")
        finally:
            self._set_sync_busy(False)

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
        if not juno.output_open:
            if str(name or ""):
                self._patch_name = str(name)[:12]
                self.patch_state.perf_name = str(name)[:12]
            self._apply_performance_selected(int(msb), int(lsb), int(pc))
            return True
        try:
            juno.send_data(ADDR_SETUP, [1])  # PERFORM
            time.sleep(0.4)
            juno.select_program(15, msb, lsb, pc)
            time.sleep(0.8)
            return self._adopt_synth_performance(int(msb), int(lsb), int(pc), str(name or ""))
        except Exception as e:
            logger.warning(f"selectLibraryPerformance failed: {e}")
            return False

    def _adopt_synth_performance(self, msb: int, lsb: int, pc: int, name: str = "",
                                 navigate: bool = True) -> bool:
        """Take the performance the synth just selected into the app, whole.

        Library loads (after their Bank/PC) and panel performance picks.
        """
        juno = self.juno
        juno.invalidate_cache()
        heard: str = ""
        try:
            raw = juno.request_data((0x10, 0x00, 0x00, 0x00),
                                    (0x00, 0x00, 0x00, 0x0C), timeout=0.8)
            if raw and len(raw) >= 12:
                heard = bytes(raw[:12]).decode("latin1", errors="replace").strip()
        except Exception as e:
            logger.debug(f"adopt performance: name re-read failed: {e}")
        # Synth truth wins; library row name is the offline/fallback.
        self._patch_name = (heard or str(name or ""))[:12] or self._patch_name
        self.patch_state.perf_name = str(self._patch_name)[:12]
        if str(self._sound_mode).upper() != "PERFORM":
            self._patch_origin = None
            self._resetMacroBases()
        # The app's performance is what mode switches push back: take the
        # loaded one whole. Nothing of the previous one survives (sounds,
        # names, edits).
        self._part_snapshots = {}
        self._part_file_status = [""] * 16
        for p in self.patch_state.perf_parts:
            p.patch_name, p.name = "", f"Part {p.part_index}"
        try:
            self.syncPerformanceFromSynth(async_mode=False)
        except Exception as e:
            logger.warning(f"adopt performance: performance read failed: {e}")
        self._apply_performance_selected(int(msb), int(lsb), int(pc), navigate)
        try:
            self.partFileStatusChanged.emit()
        except Exception:
            pass
        return True

    def _apply_performance_selected(self, msb: int, lsb: int, pc: int,
                                    navigate: bool = True) -> None:
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
        if navigate:
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
        if not juno.output_open:
            logger.info("selectLibraryPatch: MIDI out not connected (offline audition).")
            if str(name or ""):
                self._patch_name = str(name)[:12]
                self.patch_state.common.name = str(name)[:12]
            self._apply_patch_selected(int(msb), int(lsb), int(pc))
            return True
        try:
            juno.select_program(0, msb, lsb, pc)
            # Give the synth a moment to switch, then follow its display name.

            time.sleep(0.35)
            return self._adopt_synth_patch(int(msb), int(lsb), int(pc), str(name or ""))
        except Exception as e:
            logger.warning(f"selectLibraryPatch failed: {e}")
            return False

    def _adopt_synth_patch(self, msb: int, lsb: int, pc: int, name: str = "",
                           navigate: bool = True) -> bool:
        """Take the patch the synth just selected into the editors.

        Library loads (after their Bank/PC) and PATCH-mode panel picks.
        """
        juno = self.juno
        juno.invalidate_cache()
        heard: str = ""
        try:
            heard = juno.get_patch_name(timeout=0.8)
        except Exception as e:
            logger.debug(f"adopt patch: name re-read failed: {e}")
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
            logger.debug(f"adopt patch: full sync failed: {e}")
        self._set_current_slot_ref(int(msb), int(lsb), int(pc),
                                   "drum" if int(msb) == 86 else "patch")
        if navigate:
            self._pending_view = "JUNO PCM"
        return True

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


