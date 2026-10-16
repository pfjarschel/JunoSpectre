"""Header SYNC: read the sounding patch or performance from the synth."""

from __future__ import annotations

import logging

from PyQt6.QtCore import pyqtSlot

from ...core.patch_state import PatchState
from .base import BridgeBaseMixin

logger = logging.getLogger(__name__)


class SyncBridgeMixin(BridgeBaseMixin):
    """Patch and performance SYNC (the worker reads, the UI thread applies)."""

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

    @pyqtSlot()
    @pyqtSlot(bool)
    def syncPerformanceFromSynth(self, async_mode: bool = False) -> None:
        """Read the performance name, 16 part mixer blocks and shared FX from
        the synth. async_mode reads on the job worker and applies on the UI
        thread. Never touches the patch editors directly (the edited part is
        re-read after)."""
        juno = self.juno
        if juno is None:
            logger.info("Cannot sync performance: no synthesizer connected.")
            return
        if self._sync_busy:
            logger.info("Hardware sync already in progress, ignoring request.")
            return
        self._set_sync_busy(True)
        kept_names = [p.patch_name or p.name for p in self.patch_state.perf_parts]
        active = int(self.patch_state.active_perf_part)

        def read(progress=None) -> dict:
            return self._read_synth_performance(juno, kept_names, active)

        if not async_mode:
            self._apply_synth_performance(read(), wait_editors=True)
        elif not self._start_job("sync", "Reading the performance…", read,
                                 done=self._apply_synth_performance):
            logger.info("Sync skipped: another synth job is running.")
            self._set_sync_busy(False)

    def _read_synth_performance(self, juno, kept_names: list, active: int) -> dict:
        """The synth's performance name, parts (names resolved) and FX (worker)."""
        out: dict = {}
        try:
            out["name"] = juno.get_perf_name(timeout=1.0)
        except Exception as e:
            logger.debug(f"syncPerformance: name read failed: {e}")
        try:
            parts = juno.get_perf_parts(timeout=1.0)
            if parts and len(parts) == 16:
                repo = self._librarian_repo
                for i, p in enumerate(parts):
                    if repo is not None:
                        p.patch_name = repo.resolve_patch_name(p.patch_msb, p.patch_lsb, p.patch_pc)
                    # The edited part, or one the library doesn't know: ask the synth
                    if p.part_index == active or not p.patch_name:
                        try:
                            p.patch_name = juno.get_perf_part_patch_name(p.part_index, timeout=0.25) \
                                or p.patch_name
                        except Exception as e:
                            logger.debug(f"part {p.part_index} name read failed: {e}")
                    if not p.patch_name and kept_names[i] and not kept_names[i].startswith("Part "):
                        p.patch_name = kept_names[i]
                    p.patch_name = p.patch_name or f"Part {p.part_index}"
                out["parts"] = parts
        except Exception as e:
            logger.debug(f"syncPerformance: parts read failed: {e}")
        try:
            out["fx"] = juno.get_perf_fx(timeout=1.0)
        except Exception as e:
            logger.debug(f"syncPerformance: fx read failed: {e}")
        return out

    def _apply_synth_performance(self, out, wait_editors: bool = False) -> None:
        """Take a performance read from the synth into the app (UI thread)."""
        try:
            if not isinstance(out, dict):
                return
            name = out.get("name")
            if isinstance(name, str) and name:
                self.patch_state.perf_name = name[:12]
                self._patch_name = name
            if out.get("parts"):
                self.patch_state.perf_parts = out["parts"]
            if out.get("fx") is not None:
                self.patch_state.perf_fx = out["fx"]
            self._sound_mode = "PERFORM"
            self.patch_state.sound_mode = "PERFORM"
            self.patchInfoChanged.emit(self._patch_name, self._sound_mode)
            self.perfPartsChanged.emit()
            self._emit_fx_editor_signals()
            self._refresh_editors_for_part(self.patch_state.active_perf_part, async_mode=not wait_editors)
        finally:
            self._set_sync_busy(False)
