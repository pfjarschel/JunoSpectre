"""Sequencer automation lanes: 8 tracks that each drive one parameter.

A lane writes its parameter the way a controller knob bound to it would
(controllers._ctl_apply): an absolute value, which becomes the base when
macros drive it, so macros keep adding on top. In PERFORM a part-scoped
parameter is written to each of the lane's parts (a linked lane uses its
track's parts). While a lane drives a parameter, knobs bound to it are
ignored. When the lane lets go (transport stop, lane stop, new target or
parts) each parameter gets back the value it had before.

Recording (REC arms a lane): an armed lane keeps playing and its knobs work.
The first change to its parameter (knob or screen) starts recording at the
lane's current step: each step it reaches gets the value at its start, with
glide on, until the loop comes back to that first step. Then REC disarms
and the lane plays the new values.

Step recording (STEP REC, the selected lane, transport or not): every change
to the parameter overwrites the cursor step (the latest value stays); PREV /
NEXT move the cursor, wrapping around the clip.

The header REC arms what is selected: the active note track (overdub) in
NOTES mode, the active lane in MOTION mode.
"""

from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, pyqtProperty, pyqtSignal, pyqtSlot

from ...control.lcxl3 import format_value
from ...core.macro_targets import filter_macro_targets
from ...sequencer import automation as auto
from ...sequencer.engine import DIVIDER_TICKS
from .base import BridgeBaseMixin

logger = logging.getLogger(__name__)

# Armed lanes watch their parameter this often (~60 Hz)
REC_POLL_MS = 16
# A change bigger than this (of the parameter's range) is a hand on it
REC_TOUCH = 2.5 / auto.LEVELS


class AutomationBridgeMixin(BridgeBaseMixin):
    """Bridge mixin for the sequencer's automation lanes."""

    seqAutomationChanged = pyqtSignal()
    seqMotionModeChanged = pyqtSignal()
    seqActiveLaneChanged = pyqtSignal()
    seqLaneRecChanged = pyqtSignal()
    # Header REC: armed state / label of note overdub + armed lanes
    seqRecChanged = pyqtSignal()
    # Internal: the clock thread reports new lane levels; applied on the GUI thread
    _autoLevelsPending = pyqtSignal()

    def _init_automation(self) -> None:
        # lane -> {concrete target: level last written};
        # lane -> {concrete target: t before the lane took it}
        self._auto_applied: dict[int, dict[str, int]] = {}
        self._auto_restore: dict[int, dict[str, Optional[float]]] = {}
        self._auto_pending = False
        self._motion_mode = False   # sequencer page shows the automation lanes
        self._active_lane = 0
        # lane -> recording state: {"state": "armed" | "recording", ...}
        self._auto_rec: dict[int, dict] = {}
        self._auto_rec_timer = QTimer(self)
        self._auto_rec_timer.setInterval(REC_POLL_MS)
        self._auto_rec_timer.timeout.connect(self._auto_rec_poll)
        # Step recording into the selected lane's selected clip
        self._auto_step_rec = False
        self._auto_cursor = 0
        self._auto_step_seen: Optional[float] = None
        for sig in (self.seqLaneRecChanged, self.seqRecordModeChanged, self.seqMotionModeChanged,
                    self.seqActiveLaneChanged, self.seqActiveTrackChanged, self.seqTracksChanged):
            sig.connect(self.seqRecChanged)
        self._autoLevelsPending.connect(self._auto_apply_levels, Qt.ConnectionType.QueuedConnection)
        self.sequencer.automation_listener = self._on_automation_levels
        for sig in (self.seqStateChanged, self.bpmChanged):
            sig.connect(self.seqAutomationChanged)

    def _auto_lane(self, lane_idx: int):
        lanes = self.sequencer.song.automation
        return lanes[lane_idx] if 0 <= lane_idx < len(lanes) else None

    def _auto_parts(self, lane_idx: int) -> list[int]:
        """Parts the lane acts on: its linked track's, or its own."""
        lane = self._auto_lane(lane_idx)
        if lane is None:
            return []
        driver = self.sequencer.lane_driver(lane_idx)
        if driver is not lane:
            return list(driver.target_parts or [lane.link_track + 1])
        return list(lane.parts)

    def _auto_concrete(self, lane_idx: int) -> list[str]:
        """Targets for _ctl_apply right now: tone.all fanned out, part-scoped
        keys pinned to each part in PERFORM (part.* only exists there)."""
        lane = self._auto_lane(lane_idx)
        target = lane.target if lane is not None else ""
        if not target or target.startswith("macro."):
            return [target] if target else []
        keys = self._expandKey(target)
        if not target.startswith(self._PART_SCOPED_PREFIXES):
            return keys
        if not self._in_perform():
            return [] if target.startswith("part.") else keys
        return [f"{k}@{n}" for n in self._auto_parts(lane_idx) for k in keys]

    def _auto_clip(self, lane_idx: int):
        lane = self._auto_lane(lane_idx)
        return lane.clips[lane.selected_clip_idx] if lane is not None else None

    # -- playback -> synth -------------------------------------------------------

    def _on_automation_levels(self) -> None:
        """Clock thread (or a stop): coalesce into one GUI-thread pass."""
        if self._auto_pending:
            return
        self._auto_pending = True
        try:
            self._autoLevelsPending.emit()
        except RuntimeError:
            pass  # bridge gone

    def _auto_kick(self) -> None:
        """Re-send every lane's level (e.g. a part mirror arrived)."""
        self._auto_applied.clear()
        self._on_automation_levels()

    @pyqtSlot()
    def _auto_apply_levels(self) -> None:
        self._auto_pending = False
        eng = self.sequencer
        with eng.lock:
            levels = list(eng.automation_levels)
        with self._macroWrites():
            for i, level in enumerate(levels):
                concrete = self._auto_concrete(i) if level is not None else []
                held = self._auto_restore.setdefault(i, {})
                applied = self._auto_applied.setdefault(i, {})
                for k in [k for k in held if k not in concrete]:
                    applied.pop(k, None)
                    self._auto_release(held, k)
                if self._auto_hand_on(i):
                    continue  # the hand on the parameter wins while recording
                for k in concrete:
                    if applied.get(k) == level:
                        continue
                    if not self._auto_target_ready(k):
                        continue  # a part mirror is loading; _onMacroPartLoaded kicks us
                    if k not in held:
                        held[k] = self._ctl_current(k)
                    self._ctl_apply(k, level / auto.LEVELS)
                    applied[k] = level

    def _auto_release(self, held: dict, target: str) -> None:
        """A lane let go of `target`: it gets back the value it had before."""
        before = held.pop(target)
        if before is not None and self._auto_target_ready(target):
            self._ctl_apply(target, before)

    def _auto_target_ready(self, target: str) -> bool:
        """False while a non-edited part's mirror loads (reads must not block
        the GUI thread). Macro targets handle that themselves."""
        if target.startswith("macro."):
            return True
        return all(self._macroKeyReady(k) for k in self._ctl_keys(target))

    def _auto_forget(self) -> None:
        """A new sound was loaded: the saved values belong to the old one."""
        getattr(self, "_auto_restore", {}).clear()
        getattr(self, "_auto_applied", {}).clear()

    def _auto_owns(self, target: str) -> bool:
        """True when a lane drives what a knob bound to `target` would write."""
        if not self._auto_applied:
            return False
        # Armed / step-recorded lanes leave their parameter to the hand that records it
        owned = {key for i, applied in self._auto_applied.items()
                 if i not in self._auto_rec and not self._auto_stepping(i)
                 for t in applied for key in self._ctl_keys(t)}
        return bool(owned.intersection(self._ctl_keys(target)))

    # -- recording ---------------------------------------------------------------

    def _auto_stepping(self, lane_idx: int) -> bool:
        return self._auto_step_rec and lane_idx == self._active_lane

    def _auto_hand_on(self, lane_idx: int) -> bool:
        """The lane doesn't play: its parameter is being recorded by hand."""
        return self._auto_stepping(lane_idx) or self._auto_rec.get(lane_idx, {}).get("state") == "recording"

    def _auto_rec_timer_update(self) -> None:
        if self._auto_rec or self._auto_step_rec:
            self._auto_rec_timer.start()
        else:
            self._auto_rec_timer.stop()

    @pyqtProperty(bool, notify=seqRecChanged)
    def seqRecArmed(self) -> bool:
        """Header REC lit: note overdub or any lane armed."""
        return bool(self.seqLiveRecordEnabled or self._auto_rec)

    @pyqtProperty(str, notify=seqRecChanged)
    def seqRecText(self) -> str:
        """What the header REC records into: "T1", "WAIT", "L1+3", "T1 L2"."""
        out = []
        if self.seqLiveRecordEnabled:
            out.append("WAIT" if self.seqLiveRecordWaiting else f"T{self.seqActiveTrack + 1}")
        if self._auto_rec:
            out.append("L" + "+".join(str(i + 1) for i in sorted(self._auto_rec)))
        return " ".join(out)

    @pyqtSlot()
    def seqToggleRecord(self) -> None:
        """Header REC / controller: arm what is selected (note track or lane)."""
        if self._motion_mode:
            self.seqToggleLaneRec(self._active_lane)
        else:
            self.seqToggleLiveRecord(not self.seqLiveRecordEnabled)

    @pyqtProperty(bool, notify=seqLaneRecChanged)
    def seqLaneStepRec(self) -> bool:
        return self._auto_step_rec

    @pyqtProperty(int, notify=seqLaneRecChanged)
    def seqLaneCursor(self) -> int:
        return self._auto_cursor

    @pyqtSlot(bool, int)
    def seqSetLaneStepRec(self, on: bool, start_step: int) -> None:
        """Step-record the selected lane from start_step (its selected clip)."""
        self._auto_step_rec = bool(on)
        if on:
            self._auto_cursor = max(0, int(start_step))
            self._auto_step_seen = None
        else:
            self._auto_applied.pop(self._active_lane, None)
            self._on_automation_levels()   # the lane plays again
        self._auto_rec_timer_update()
        self.seqLaneRecChanged.emit()

    @pyqtSlot(int)
    def seqSetLaneCursor(self, step_idx: int) -> None:
        clip = self._auto_clip(self._active_lane)
        if clip is not None and self._auto_step_rec:
            self._auto_cursor = max(0, int(step_idx)) % clip.length
            self.seqLaneRecChanged.emit()

    @pyqtSlot(int)
    def seqMoveLaneCursor(self, delta: int) -> None:
        clip = self._auto_clip(self._active_lane)
        if clip is not None:
            self._auto_cursor = (self._auto_cursor + int(delta)) % clip.length
            self.seqLaneRecChanged.emit()

    def _auto_step_poll(self) -> None:
        lane_idx = self._active_lane
        clip = self._auto_clip(lane_idx)
        concrete = self._auto_concrete(lane_idx)
        if clip is None or not concrete or not self._auto_target_ready(concrete[0]):
            self._auto_step_seen = None
            return
        now = self._ctl_current(concrete[0])
        if now is None:
            return
        seen, self._auto_step_seen = self._auto_step_seen, now
        if seen is not None and abs(now - seen) > 0.5 / auto.LEVELS:
            self._auto_rec_write(clip, self._auto_cursor % clip.length, now)

    @pyqtProperty("QVariantList", notify=seqLaneRecChanged)
    def seqLaneRecStates(self) -> list:
        """Per lane: "" | "armed" | "recording"."""
        return [self._auto_rec.get(i, {}).get("state", "")
                for i in range(len(self.sequencer.song.automation))]

    @pyqtSlot(int)
    def seqToggleLaneRec(self, lane_idx: int) -> None:
        """Arm / disarm a lane (disarming mid-recording keeps what was written)."""
        lane = self._auto_lane(lane_idx)
        if lane is None:
            return
        if lane_idx in self._auto_rec:
            self._auto_rec_end(lane_idx)
            return
        if not lane.target:
            return
        self._auto_rec[lane_idx] = {"state": "armed", "seen": None}
        self._auto_rec_timer_update()
        self.seqLaneRecChanged.emit()

    def _auto_rec_end(self, lane_idx: int) -> None:
        """Disarm; the lane plays (its new values) again."""
        if self._auto_rec.pop(lane_idx, None) is None:
            return
        self._auto_rec_timer_update()
        self._auto_applied.pop(lane_idx, None)
        self._on_automation_levels()
        self.seqLaneRecChanged.emit()

    def _auto_rec_poll(self) -> None:
        if self._auto_step_rec:
            self._auto_step_poll()
        eng = self.sequencer
        playing = eng.is_playing
        for i, rec in list(self._auto_rec.items()):
            lane = self._auto_lane(i)
            concrete = self._auto_concrete(i)
            clip_idx = eng.lane_driver(i).active_clip_idx
            if lane is None or not concrete or not playing or not 0 <= clip_idx < len(lane.clips):
                if rec["state"] == "recording":
                    self._auto_rec_end(i)   # the transport or the clip stopped
                else:
                    rec["seen"] = None
                continue
            if not self._auto_target_ready(concrete[0]):
                continue
            now = self._ctl_current(concrete[0])
            if now is None:
                continue
            clip = lane.clips[clip_idx]
            step = eng.lane_steps[i] % clip.length
            if rec["state"] == "armed":
                # What the parameter should be without a hand on it
                level = self._auto_applied.get(i, {}).get(concrete[0])
                expect = level / auto.LEVELS if level is not None else rec["seen"]
                rec["seen"] = now
                if expect is None or abs(now - expect) <= REC_TOUCH:
                    continue
                rec.update(state="recording", clip=clip_idx, start=step, last=step)
                self._auto_rec_write(clip, step, now)
                self.seqLaneRecChanged.emit()
                continue
            if clip_idx != rec["clip"]:
                self._auto_rec_end(i)       # another clip launched
                continue
            # Every step reached since the last poll gets the value at its start
            s, looped = rec["last"], False
            while s != step:
                s = (s + 1) % clip.length
                if s == rec["start"]:
                    looped = True
                    break
                self._auto_rec_write(clip, s, now)
            rec["last"] = step
            if looped:
                self._auto_rec_end(i)       # one full loop recorded

    def _auto_rec_write(self, clip, step_idx: int, t: float) -> None:
        if 0 <= step_idx < clip.length:
            step = clip.steps[step_idx]
            step.value, step.glide = max(0.0, min(1.0, float(t))), True
            self.seqAutomationChanged.emit()

    # -- load estimate -----------------------------------------------------------

    def _auto_key_cost(self, key: str) -> int:
        """DT1 writes one value change of a concrete key sends."""
        base, _ = self._splitPart(key)
        if base in ("vector.x", "vector.y", "vector.w"):
            return 4  # the pad mixes all four tone levels
        if base.startswith(("vector.", "seq.")):
            return 0  # app-side only
        return 1

    def _auto_writes_per_change(self, lane_idx: int) -> int:
        total = 0
        for target in self._auto_concrete(lane_idx):
            if target.startswith("macro."):
                try:
                    slot = self.patch_state.macros[int(target[6:]) - 1]
                except (ValueError, IndexError):
                    continue
                total += sum(self._auto_key_cost(k) for link in slot.links for k in self._concreteKeys(link))
            else:
                total += self._auto_key_cost(target)
        return total

    def _auto_load(self) -> list[float]:
        return self.sequencer.automation_load(self._auto_writes_per_change)

    @pyqtProperty(float, notify=seqAutomationChanged)
    def seqAutomationLoad(self) -> float:
        """Estimated SysEx writes per second of all playing lanes."""
        return round(sum(self._auto_load()), 1)

    @pyqtProperty(float, constant=True)
    def seqAutomationBudget(self) -> float:
        return float(auto.AUTOMATION_BUDGET_WPS)

    # -- QML: lanes ----------------------------------------------------------------

    @pyqtProperty(bool, notify=seqMotionModeChanged)
    def seqMotionMode(self) -> bool:
        return self._motion_mode

    @pyqtSlot(bool)
    def seqSetMotionMode(self, on: bool) -> None:
        if bool(on) != self._motion_mode:
            self._motion_mode = bool(on)
            self.seqMotionModeChanged.emit()

    @pyqtProperty(int, notify=seqActiveLaneChanged)
    def seqActiveLane(self) -> int:
        return self._active_lane

    @pyqtSlot(int)
    def seqSelectLane(self, lane_idx: int) -> None:
        before = self._active_lane
        self._active_lane = max(0, min(len(self.sequencer.song.automation) - 1, int(lane_idx)))
        if self._auto_step_rec and before != self._active_lane:
            # Step recording moves to the new lane; the old one plays again
            self._auto_step_seen = None
            self._auto_applied.pop(before, None)
            self._on_automation_levels()
        self.seqActiveLaneChanged.emit()

    @pyqtSlot(str, str, result="QVariantList")
    def getLaneTargets(self, category: str = "ALL", query: str = "") -> list:
        """What a lane can drive: the macro catalog plus the 8 macros."""
        q = (query or "").strip().lower()
        macros = []
        if category in ("ALL", "MACRO", ""):
            for i in range(1, len(self.patch_state.macros) + 1):
                title = self._ctl_target_title(f"macro.{i}")
                if not q or q in title.lower() or q in f"macro.{i}":
                    macros.append({"key": f"macro.{i}", "title": title, "category": "MACRO"})
        rest = [] if category == "MACRO" else filter_macro_targets(category, query)
        return macros + rest

    def _auto_tab_name(self, lane) -> str:
        """Short lane tab label: "T1 Cutoff", "M2 WOBBLE", "Reverb Level"."""
        return self._short_target_name(lane.target) if lane.target else ""

    @pyqtSlot(int, float, result=str)
    def seqLaneValueText(self, lane_idx: int, t: float) -> str:
        """A 0..1 lane value in the parameter's own units ("+6", "L24", "-50%")."""
        lane = self._auto_lane(lane_idx)
        if lane is None or not lane.target or t < 0:
            return "--"
        if lane.target.startswith("macro."):
            lo, hi = -1.0, 1.0
        else:
            entry = self._ctl_entry(lane.target)
            lo, hi = (float(entry["min"]), float(entry["max"])) if entry else (0.0, 127.0)
        level = auto.level_of(t) / auto.LEVELS
        return format_value(lane.target, lo + (hi - lo) * level, lo, hi)

    @pyqtSlot(int, str)
    def seqLaneShape(self, lane_idx: int, shape: str) -> None:
        """Fill the lane's selected clip: RAMP UP / RAMP DN / TRI / SINE / SQUARE / RANDOM."""
        clip = self._auto_clip(lane_idx)
        if clip is None:
            return
        for step, (value, glide) in zip(clip.steps, auto.shape_values(str(shape), clip.length)):
            step.value, step.glide = value, glide
        self.seqAutomationChanged.emit()

    @pyqtProperty("QVariantList", notify=seqAutomationChanged)
    def seqAutomationLanes(self) -> list:
        loads = self._auto_load()
        out = []
        for i, lane in enumerate(self.sequencer.song.automation):
            entry = self._ctl_entry(lane.target) if lane.target else None
            driver = self.sequencer.lane_driver(i)
            parts = self._auto_parts(i)
            out.append({
                "target": lane.target,
                "title": self._ctl_target_title(lane.target) if lane.target else "",
                "tabName": self._auto_tab_name(lane),
                "category": entry["category"] if entry else "",
                "min": float(entry["min"]) if entry else 0.0,
                "max": float(entry["max"]) if entry else 1.0,
                "partScoped": lane.target.startswith(self._PART_SCOPED_PREFIXES),
                "targetPart": parts[0] if parts else 1,
                "layerParts": parts[1:],
                "linkTrack": lane.link_track if lane.is_linked else -1,
                "clockDivider": lane.clock_divider,
                "activeClipIdx": driver.active_clip_idx,
                "queuedClipIdx": driver.queued_clip_idx,
                "selectedClipIdx": lane.selected_clip_idx,
                "load": round(loads[i], 1),
                "clips": [{"name": c.name, "length": c.length, "hasValues": c.has_values}
                          for c in lane.clips],
            })
        return out

    @pyqtSlot(int, result="QVariantList")
    def seqLaneSteps(self, lane_idx: int) -> list:
        """Steps of the lane's selected clip: value (0..1, -1 = empty), glide,
        and what plays across the step (start/end, -1 when nothing is set)."""
        clip = self._auto_clip(lane_idx)
        if clip is None:
            return []
        curve = auto.clip_curve(clip)
        return [{"value": -1.0 if s.value is None else s.value, "glide": s.glide,
                 "start": c[0] if c else -1.0, "end": c[1] if c else -1.0}
                for s, c in zip(clip.steps, curve)]

    def _auto_lane_edited(self) -> None:
        self.seqAutomationChanged.emit()
        self._on_automation_levels()  # let go of / take over parameters now

    @pyqtSlot(int, str)
    def seqSetLaneTarget(self, lane_idx: int, target: str) -> None:
        """A macro catalog key (parts are set apart), "macro.N", or "" to clear."""
        lane = self._auto_lane(lane_idx)
        if lane is None:
            return
        target = str(target or "")
        if "@" in target or (target and not (target.startswith("macro.") or self._ctl_entry(target))):
            return
        lane.target = target
        self._auto_lane_edited()

    @pyqtSlot(int, int)
    def seqSetLaneLink(self, lane_idx: int, track_idx: int) -> None:
        """Follow note track `track_idx` (its launches and parts), or -1 for none.
        Unlinking keeps the track's parts, so nothing jumps."""
        lane = self._auto_lane(lane_idx)
        if lane is None:
            return
        tracks = self.sequencer.song.tracks
        if 0 <= track_idx < len(tracks):
            lane.link_track = int(track_idx)
        elif lane.is_linked:
            lane.parts = self._auto_parts(lane_idx)
            lane.active_clip_idx = self.sequencer.lane_driver(lane_idx).active_clip_idx
            lane.queued_clip_idx = -1
            lane.link_track = -1
            lane.__post_init__()
        self._auto_lane_edited()

    @pyqtSlot(int, int)
    def seqSetLanePart(self, lane_idx: int, part: int) -> None:
        """Main part of an unlinked lane (layers kept)."""
        lane = self._auto_lane(lane_idx)
        if lane is None or lane.is_linked:
            return
        part = max(1, min(16, int(part)))
        lane.parts = [part] + [p for p in lane.parts[1:] if p != part]
        self._auto_lane_edited()

    @pyqtSlot(int, int)
    def seqToggleLaneLayer(self, lane_idx: int, part: int) -> None:
        """Add/remove an extra part of an unlinked lane (the main part stays)."""
        lane = self._auto_lane(lane_idx)
        if lane is None or lane.is_linked or not lane.parts:
            return
        part = max(1, min(16, int(part)))
        main, layers = lane.parts[0], list(lane.parts[1:])
        if part == main:
            return
        if part in layers:
            layers.remove(part)
        else:
            layers.append(part)
        lane.parts = [main] + sorted(layers)
        self._auto_lane_edited()

    @pyqtSlot(int, str)
    def seqSetLaneDivider(self, lane_idx: int, divider: str) -> None:
        lane = self._auto_lane(lane_idx)
        if lane is not None and divider in DIVIDER_TICKS:
            lane.clock_divider = divider
            self.seqAutomationChanged.emit()

    @pyqtSlot(int, int)
    def seqSelectLaneClip(self, lane_idx: int, clip_idx: int) -> None:
        lane = self._auto_lane(lane_idx)
        if lane is not None:
            lane.selected_clip_idx = max(0, min(len(lane.clips) - 1, int(clip_idx)))
            self.seqAutomationChanged.emit()

    @pyqtSlot(int, int)
    def seqLaunchLaneClip(self, lane_idx: int, clip_idx: int) -> None:
        """Unlinked lanes only: a linked lane follows its track."""
        lane = self._auto_lane(lane_idx)
        if lane is not None and not lane.is_linked:
            self.sequencer.launch_lane_clip(lane_idx, clip_idx)
            self.seqAutomationChanged.emit()

    @pyqtSlot(int)
    def seqStopLane(self, lane_idx: int) -> None:
        lane = self._auto_lane(lane_idx)
        if lane is not None and not lane.is_linked:
            self.sequencer.stop_lane(lane_idx)
            self.seqAutomationChanged.emit()

    @pyqtSlot(int, int, float)
    def seqSetLaneStep(self, lane_idx: int, step_idx: int, value: float) -> None:
        """Set a step's value (0..1); a negative value empties the step."""
        clip = self._auto_clip(lane_idx)
        if clip is None or not 0 <= step_idx < clip.length:
            return
        step = clip.steps[step_idx]
        if value < 0:
            step.value, step.glide = None, False
        else:
            if step.value is None:
                step.glide = True   # new values glide by default (like recorded ones)
            step.value = max(0.0, min(1.0, float(value)))
        self.seqAutomationChanged.emit()

    @pyqtSlot(int, int, bool)
    def seqSetLaneStepGlide(self, lane_idx: int, step_idx: int, glide: bool) -> None:
        clip = self._auto_clip(lane_idx)
        if clip is not None and 0 <= step_idx < clip.length and clip.steps[step_idx].is_set:
            clip.steps[step_idx].glide = bool(glide)
            self.seqAutomationChanged.emit()

    @pyqtSlot(int, int)
    def seqSetLaneClipLength(self, lane_idx: int, length: int) -> None:
        clip = self._auto_clip(lane_idx)
        if clip is not None:
            clip.set_length(length)
            self.seqAutomationChanged.emit()

    @pyqtSlot(int)
    def seqClearLaneClip(self, lane_idx: int) -> None:
        clip = self._auto_clip(lane_idx)
        if clip is not None:
            for s in clip.steps:
                s.value, s.glide = None, False
            self.seqAutomationChanged.emit()
