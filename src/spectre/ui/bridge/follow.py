"""Panel following: the app picks up what is done on the JUNO-DS itself.

A performance picked on the panel loads into the app (like a library
load, as a background job). With Transmit Edit Data on, panel edits are
re-read shortly after they stop: part mixer/zone blocks, performance FX,
the edited part's sound (editors follow when it is the part they show)
and the PATCH-mode patch. A panel edit to a part's sound also marks the
part edited. Bursts are merged: one re-read per pause, at most every
FOLLOW_MAX_WAIT_S while a knob keeps turning.
"""

from __future__ import annotations

import logging
import threading
import time

from PyQt6.QtCore import QTimer, pyqtProperty, pyqtSignal, pyqtSlot

from ...core.panel_follow import FollowPlan, PanelFollower
from ...core.protocol import SoundMode
from ...core.sysex import ADDR_TEMP_PATCH_PART_1
from .base import BridgeBaseMixin
from .hardware import save_hardware_settings

logger = logging.getLogger(__name__)

FOLLOW_DEBOUNCE_MS = 350
FOLLOW_MAX_WAIT_S = 1.0


class FollowBridgeMixin(BridgeBaseMixin):
    followPanelChanged = pyqtSignal()
    _followEvent = pyqtSignal(object)    # MIDI thread -> UI thread
    _followRead = pyqtSignal(object)     # reader thread -> UI thread

    def _init_follow(self) -> None:
        self._follower = PanelFollower(is_own=self._follow_is_own)
        self._follow_plan = FollowPlan()
        self._follow_first = 0.0
        self._follow_reading = False
        self._follow_timer = QTimer(self)
        self._follow_timer.setSingleShot(True)
        self._follow_timer.timeout.connect(self._follow_fire)
        self._followEvent.connect(self._on_follow_event)
        self._followRead.connect(self._on_follow_read)

    def _follow_attach(self, midi_mgr) -> None:
        if midi_mgr is not None and hasattr(midi_mgr, "add_message_listener"):
            midi_mgr.add_message_listener(self._follow_on_midi)

    def _follow_is_own(self, address, data) -> bool:
        juno = self.juno
        return juno is not None and juno.is_own_traffic(address, data)

    @pyqtProperty(bool, notify=followPanelChanged)
    def followPanel(self) -> bool:
        return bool(self._hw_settings.get("follow_panel", True))

    @pyqtSlot(bool)
    def setFollowPanel(self, on: bool) -> None:

        self._hw_settings["follow_panel"] = bool(on)
        save_hardware_settings(self._hw_settings)
        self.followPanelChanged.emit()

    # -- events --------------------------------------------------------------

    def _follow_on_midi(self, msg) -> None:
        """MIDI input thread."""
        if not self._hw_settings.get("follow_panel", True):
            return
        event = self._follower.feed(msg)
        if event is not None:
            try:
                self._followEvent.emit(event)
            except RuntimeError:
                pass  # bridge gone

    def _on_follow_event(self, event) -> None:
        if event[0] == "edit":
            logger.debug(f"panel edit {bytes(event[1]).hex(' ')} = {bytes(event[2]).hex(' ')}")
        else:
            logger.info(f"panel {event[0]}: {event[1:]}")
        before = set(self._follow_plan.part_patches)
        self._follow_plan.add(event)
        for part in self._follow_plan.part_patches - before:
            self._on_perf_part_write(part)  # edited badge right away
        now = time.monotonic()
        if not self._follow_timer.isActive():
            self._follow_first = now
        if now - self._follow_first >= FOLLOW_MAX_WAIT_S:
            self._follow_timer.start(0)
        else:
            self._follow_timer.start(FOLLOW_DEBOUNCE_MS)

    def _follow_fire(self) -> None:
        plan = self._follow_plan
        if plan.empty():
            return
        if self._follow_reading or self._job_name or self._sync_busy:
            self._follow_timer.start(FOLLOW_DEBOUNCE_MS)
            return
        self._follow_plan = FollowPlan()
        juno = self.juno
        if juno is None:
            return

        if plan.mode in (0, 1):
            self._follow_mode("PATCH" if plan.mode == 0 else "PERFORM")
            if plan.mode == 1:
                plan.parts = plan.perf_fx = True
                plan.part_patches.add(int(self.patch_state.active_perf_part))
            else:
                plan.patch = True

        if plan.perf is not None:
            msb, lsb, pc = plan.perf
            self._start_job("follow", "Following the Juno…",
                            lambda p: self._adopt_synth_performance(msb, lsb, pc, navigate=False))
            return
        if plan.program is not None:
            _ch, msb, lsb, pc = plan.program
            if self._sound_mode == "PATCH":
                self._start_job("follow", "Following the Juno…",
                                lambda p: self._adopt_synth_patch(msb, lsb, pc, navigate=False))
                return
            plan.parts = True  # a part's sound changed: the part blocks say which
        if plan.arp:
            self.refreshArp()

        perform = self._sound_mode == "PERFORM"
        active = int(self.patch_state.active_perf_part)
        want = {
            "parts": perform and plan.parts,
            "fx": perform and plan.perf_fx,
            "part": active if perform and active in plan.part_patches else 0,
            "patch": not perform and plan.patch,
        }
        if not any(want.values()):
            return
        self._follow_reading = True
        threading.Thread(target=self._follow_read, args=(juno, want),
                         name="panel-follow", daemon=True).start()

    def _follow_mode(self, mode: str) -> None:
        """The panel switched sound mode: the app follows (no push either way)."""
        juno = self.juno
        try:
            juno.note_sound_mode(SoundMode[mode])
        except Exception:
            pass
        if mode == str(self._sound_mode).upper():
            return
        self._patch_origin = None
        self._resetMacroBases()
        self._sound_mode = mode
        self.patch_state.sound_mode = mode
        self._capture_loaded()
        self.patchInfoChanged.emit(self._patch_name, self._sound_mode)
        self.perfPartsChanged.emit()

    # -- reading -------------------------------------------------------------

    def _follow_read(self, juno, want: dict) -> None:
        """Reader thread: fetch what the plan needs, apply on the UI thread."""
        out: dict = {}
        try:
            if want["parts"]:
                parts = juno.get_perf_parts(timeout=1.0)
                current = list(self.patch_state.perf_parts)
                for new in parts:
                    old = current[new.part_index - 1] if new.part_index <= len(current) else None
                    if old is not None and _same_sound(old, new):
                        continue
                    new.patch_name = self._follow_patch_name(juno, new)
                out["parts"] = parts
            if want["fx"]:
                out["fx"] = juno.get_perf_fx(timeout=1.0)
                out["name"] = juno.get_perf_name(timeout=1.0)
            if want["part"]:
                out["part"] = (want["part"], self._read_part_image(want["part"]))
            if want["patch"]:
                out["patch"] = juno.read_patch_at(ADDR_TEMP_PATCH_PART_1)
        except Exception as e:
            logger.debug(f"panel follow read failed: {e}")
        try:
            self._followRead.emit(out)
        except RuntimeError:
            pass

    def _follow_patch_name(self, juno, part) -> str:
        repo = getattr(self, "_librarian_repo", None)
        if repo is not None:
            try:
                name = repo.resolve_patch_name(part.patch_msb, part.patch_lsb, part.patch_pc)
                if name:
                    return name
            except Exception:
                pass
        try:
            return juno.get_perf_part_patch_name(part.part_index, timeout=0.25) or ""
        except Exception:
            return ""

    def _on_follow_read(self, out: dict) -> None:
        self._follow_reading = False
        perform = self._sound_mode == "PERFORM"
        if perform and out.get("parts"):
            self._follow_merge_parts(out["parts"])
        if perform and out.get("fx") is not None:
            self.patch_state.perf_fx = out["fx"]
            if out.get("name"):
                self.patch_state.perf_name = self._patch_name = str(out["name"])[:12]
                self.patchInfoChanged.emit(self._patch_name, self._sound_mode)
            try:
                self._emit_fx_editor_signals()
            except Exception as e:
                logger.debug(f"panel follow fx signals: {e}")
        part = out.get("part")
        if perform and part and part[1] is not None \
                and int(self.patch_state.active_perf_part) == part[0]:
            self._apply_patch_state_to_editors(part[1], part[0])
        if not perform and out.get("patch") is not None:
            self._apply_patch_state_to_editors(out["patch"], int(self.patch_state.active_perf_part))
        if not self._follow_plan.empty():
            self._follow_timer.start(0)

    def _follow_merge_parts(self, parts: list) -> None:
        """Take the synth's part blocks, keeping what the app knows of unchanged sounds."""
        current = self.patch_state.perf_parts
        active = int(self.patch_state.active_perf_part)
        reload_active = False
        for new in parts:
            i = new.part_index - 1
            if not 0 <= i < len(current):
                continue
            old = current[i]
            new.solo = old.solo
            if _same_sound(old, new):
                new.name, new.patch_name = old.name, old.patch_name
                new.patch_file, new.modified, new.memory_only = old.patch_file, old.modified, old.memory_only
            else:
                # Another sound was picked for this part: nothing of the old one applies
                self._part_snapshots.pop(str(new.part_index), None)
                if i < len(self._part_file_status):
                    self._part_file_status[i] = ""
                new.patch_name = new.patch_name or f"Part {new.part_index}"
                reload_active = reload_active or new.part_index == active
                logger.info(f"panel: part {new.part_index} now plays {new.patch_name}")
            current[i] = new
        self.perfPartsChanged.emit()
        try:
            self.partFileStatusChanged.emit()
        except Exception:
            pass
        if reload_active:
            self._refresh_editors_for_part(active, async_mode=True)


def _same_sound(a, b) -> bool:
    return (a.patch_msb, a.patch_lsb, a.patch_pc) == (b.patch_msb, b.patch_lsb, b.patch_pc)
