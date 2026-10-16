"""View bridge mixin: page navigation, librarian entry/exit and the edited tone."""

from __future__ import annotations

import logging

from PyQt6.QtCore import pyqtProperty, pyqtSignal, pyqtSlot

from .base import BridgeBaseMixin

logger = logging.getLogger(__name__)


class ViewBridgeMixin(BridgeBaseMixin):
    """Active page, librarian audition entry/cancel, selected tone and link mode."""

    activeViewChanged = pyqtSignal(str)
    requestOpenScreensOverlay = pyqtSignal()
    requestOpenWaveBrowser = pyqtSignal(int)
    requestOpenInitPatchModal = pyqtSignal()
    requestOpenSavePatchModal = pyqtSignal()
    requestOpenEnvOverlay = pyqtSignal(str)

    def _init_view(self) -> None:
        self._active_view: str = "JUNO PCM"
        self._view_before_librarian: str = "JUNO PCM"

    def _emit_all_state_signals(self) -> None:
        """Emit signals for all properties to trigger complete UI refresh.

        Called after every load and part switch: also keeps the loaded state
        controllers reset to (Shift + move)."""
        self._capture_loaded()
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
        self._tmt_emit()
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
        self.macrosChanged.emit()
        self.routingChanged.emit()

    @pyqtProperty(str, notify=activeViewChanged)
    def activeView(self) -> str:
        return self._active_view

    @activeView.setter
    def activeView(self, view: str) -> None:
        self.setActiveView(view)

    @pyqtSlot(str)
    def setActiveView(self, view: str) -> None:
        """Switch active workstation view tab."""
        v = view.upper().strip()
        if self._active_view != v:
            if v == "LIBRARIAN" and self._active_view != "LIBRARIAN":
                self._view_before_librarian = self._active_view
                self._capture_librarian_entry()
            elif self._active_view == "LIBRARIAN" and self._pick_target:
                # Leaving the Librarian any other way ends part picking too.
                self._pick_target = 0
                self.librarianPickChanged.emit()

            self._active_view = v
            if v == "SETLIST":
                self._setlist_recheck()  # song files may have changed meanwhile
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
        self._forget_loaded(self._loaded_slot())   # reverted: that is the loaded sound again
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
            from ...core.protocol import SoundMode
            if not juno.output_open:
                return False
            kind = str(ref.get("kind") or "patch")
            msb, lsb, pc = int(ref.get("msb", 0)), int(ref.get("lsb", 0)), int(ref.get("pc", 0))
            if kind == "performance":
                juno.set_sound_mode(SoundMode.PERFORM)
                return juno.select_program(15, msb, lsb, pc)
            try:
                juno.set_sound_mode(SoundMode[str(sound_mode).upper()])
            except (KeyError, ValueError):
                juno.set_sound_mode(SoundMode.PATCH)
            return juno.select_program(0, msb, lsb, pc)
        except Exception as e:
            logger.debug(f"cancel restore: slot reselect failed: {e}")
            return False

    def _restore_performance_sound(self, state, part_snapshots: dict) -> None:
        """Restore a performance sound: mixer selects sync, images queued."""
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
            image = self._part_restore_image(p, part_snapshots)
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
