"""Sequencer bridge mixin exposing multi-track playback, clip launching and step editing to QML."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtProperty, pyqtSignal, pyqtSlot

from ...sequencer.engine import SequencerEngine
from ...sequencer.models import NoteEvent, default_sequencer_song
from ...sequencer.recording import SequencerRecorder
from .base import BridgeBaseMixin

logger = logging.getLogger(__name__)


class SequencerBridgeMixin(BridgeBaseMixin):
    """Bridge mixin for 5-track sequencer, session matrix, and step editor."""

    seqStateChanged = pyqtSignal()
    seqPlayheadsChanged = pyqtSignal()
    seqTracksChanged = pyqtSignal()
    seqActiveTrackChanged = pyqtSignal()
    seqActiveClipChanged = pyqtSignal()
    seqRecordModeChanged = pyqtSignal()
    seqCursorStepChanged = pyqtSignal()
    # Internal: carries engine/recorder notifications from the clock and MIDI
    # threads to the GUI thread (QML bindings must only update there).
    _seqUiSync = pyqtSignal(int)

    _SYNC_PLAYHEADS = 1
    _SYNC_RECORDER = 2
    _SYNC_CLIPS = 3

    def _init_sequencer(self) -> None:
        """Initialize sequencer engine, recorder, and subscriptions."""
        midi_mgr = getattr(self.engine, "juno", None)
        midi_mgr = getattr(midi_mgr, "midi", None) if midi_mgr else None

        self.sequencer = SequencerEngine(
            song=default_sequencer_song(),
            midi_mgr=midi_mgr,
            channel_resolver=self._part_rx_channel,
        )
        self.recorder = SequencerRecorder(self.sequencer)

        self._active_seq_track: int = 0
        self._active_seq_clip: int = 0

        self._seqUiSync.connect(self._apply_seq_ui_sync, Qt.ConnectionType.QueuedConnection)

        # Subscribe engine UI updates to Qt signals
        self.sequencer.subscribe_ui(self._on_seq_ui_update)
        # Subscribe recorder UI updates to Qt signals
        self.recorder.subscribe_ui(self._on_rec_ui_update)

        # Connect note listener to recorder if midi manager supports it
        if hasattr(midi_mgr, "add_note_listener"):
            midi_mgr.add_note_listener(self.recorder.handle_midi_message)
        if hasattr(midi_mgr, "start_input_worker"):
            midi_mgr.start_input_worker()

    def _on_seq_ui_update(self, snapshot: dict) -> None:
        """Receive downsampled playback updates from SequencerEngine (clock thread)."""
        clips = (tuple(snapshot.get("active_clips", ())), tuple(snapshot.get("queued_clips", ())))
        if clips != getattr(self, "_last_seq_clips", None):
            # A queued launch/stop took effect on the bar: refresh clip states too.
            self._last_seq_clips = clips
            self._seqUiSync.emit(self._SYNC_CLIPS)
        self._seqUiSync.emit(self._SYNC_PLAYHEADS)

    def _on_rec_ui_update(self, event_type: str, data: Any = None) -> None:
        """Receive recording/audition/step updates from SequencerRecorder (MIDI thread)."""
        self._seqUiSync.emit(self._SYNC_RECORDER)

    def _apply_seq_ui_sync(self, kind: int) -> None:
        """Emit QML notify signals on the GUI thread."""
        if kind == self._SYNC_PLAYHEADS:
            self.seqPlayheadsChanged.emit()
        elif kind == self._SYNC_CLIPS:
            self.seqTracksChanged.emit()
        elif kind == self._SYNC_RECORDER:
            self.seqCursorStepChanged.emit()
            self.seqActiveClipChanged.emit()
            self.seqTracksChanged.emit()

    def _part_rx_channel(self, part_num: int) -> int:
        """MIDI receive channel (0..15) of a performance part, defaulting to part - 1."""
        parts = getattr(getattr(self, "patch_state", None), "perf_parts", None)
        if parts and 1 <= part_num <= len(parts):
            rx = int(getattr(parts[part_num - 1], "rx_channel", -1))
            if 0 <= rx <= 15:
                return rx
        return (int(part_num) - 1) % 16

    # -------------------------------------------------------------------------
    # QML Properties
    # -------------------------------------------------------------------------

    @pyqtProperty(bool, notify=seqStateChanged)
    def seqIsPlaying(self) -> bool:
        return self.sequencer.is_playing if hasattr(self, "sequencer") else False

    @pyqtProperty(float, notify=seqStateChanged)
    def seqBpm(self) -> float:
        return self.sequencer.bpm if hasattr(self, "sequencer") else 120.0

    @pyqtProperty(int, notify=seqStateChanged)
    def seqMasterResync(self) -> int:
        return self.sequencer.song.master_resync_bars if hasattr(self, "sequencer") else 0

    @pyqtProperty(int, notify=seqActiveTrackChanged)
    def seqActiveTrack(self) -> int:
        return getattr(self, "_active_seq_track", 0)

    @pyqtProperty(int, notify=seqActiveClipChanged)
    def seqActiveClip(self) -> int:
        return getattr(self, "_active_seq_clip", 0)

    @pyqtProperty("QVariantList", notify=seqPlayheadsChanged)
    def seqPlayheads(self) -> list:
        if not hasattr(self, "sequencer"):
            return [0, 0, 0, 0, 0]
        return list(self.sequencer.track_steps)

    @pyqtProperty("QVariantList", notify=seqTracksChanged)
    def seqTracks(self) -> list:
        if not hasattr(self, "sequencer"):
            return []
        out = []
        for i, t in enumerate(self.sequencer.song.tracks):
            target_part = t.target_parts[0] if t.target_parts else (i + 1)
            kbd_on = getattr(t, "keybed_enabled", True)
            out.append({
                "trackId": t.track_id,
                "name": t.name,
                "targetParts": list(t.target_parts),
                "targetPart": target_part,
                "partIsActive": self._part_is_active(target_part),
                "keybedEnabled": bool(kbd_on),
                "clockDivider": t.clock_divider,
                "swing": t.swing,
                "activeClipIdx": t.active_clip_idx,
                "queuedClipIdx": t.queued_clip_idx,
                "clipCount": len(t.clips),
                "clips": [
                    {
                        "clipId": c.clip_id,
                        "name": c.name,
                        "length": c.length,
                        "hasNotes": any(s.is_active for s in c.steps),
                    }
                    for c in t.clips
                ],
            })
        return out

    @pyqtProperty("QVariantList", notify=seqActiveClipChanged)
    def seqActiveClipSteps(self) -> list:
        if not hasattr(self, "sequencer"):
            return []
        t_idx = getattr(self, "_active_seq_track", 0)
        c_idx = getattr(self, "_active_seq_clip", 0)
        if 0 <= t_idx < len(self.sequencer.song.tracks):
            track = self.sequencer.song.tracks[t_idx]
            if 0 <= c_idx < len(track.clips):
                clip = track.clips[c_idx]
                return [
                    {
                        "index": i,
                        "gateLength": s.gate_length,
                        "microTiming": s.micro_timing,
                        "strum": s.strum,
                        "probability": s.probability,
                        "tie": s.tie,
                        "isActive": s.is_active,
                        "noteCount": len(s.notes),
                        "notes": [n.to_dict() for n in s.notes],
                        "primaryPitch": s.notes[0].pitch if s.notes else -1,
                        "primaryVelocity": s.notes[0].velocity if s.notes else 0,
                    }
                    for i, s in enumerate(clip.steps)
                ]
        return []

    @pyqtProperty(bool, notify=seqRecordModeChanged)
    def seqStepRecordEnabled(self) -> bool:
        return self.recorder.step_record_enabled if hasattr(self, "recorder") else False

    @pyqtProperty(bool, notify=seqRecordModeChanged)
    def seqLiveRecordEnabled(self) -> bool:
        return self.recorder.live_record_enabled if hasattr(self, "recorder") else False

    @pyqtProperty(bool, notify=seqTracksChanged)
    def seqLiveRecordWaiting(self) -> bool:
        """Overdub armed, selected clip queued but not playing yet."""
        return self.recorder.live_record_waiting if hasattr(self, "recorder") else False

    @pyqtProperty(int, notify=seqCursorStepChanged)
    def seqCursorStep(self) -> int:
        return self.recorder.cursor_step if hasattr(self, "recorder") else 0

    # -------------------------------------------------------------------------
    # QML Transport & Session Slots
    # -------------------------------------------------------------------------

    @pyqtSlot()
    def seqPlay(self) -> None:
        if hasattr(self, "sequencer"):
            self.sequencer.play()
            self.seqStateChanged.emit()

    @pyqtSlot()
    def seqPause(self) -> None:
        if hasattr(self, "sequencer"):
            self.sequencer.pause()
            self.seqStateChanged.emit()

    @pyqtSlot()
    def seqStop(self) -> None:
        if hasattr(self, "sequencer"):
            self.sequencer.stop()
            self.seqStateChanged.emit()
            self.seqPlayheadsChanged.emit()

    @pyqtSlot()
    def seqTogglePlay(self) -> None:
        if hasattr(self, "sequencer"):
            if self.sequencer.is_playing:
                self.seqStop()
            else:
                self.seqPlay()

    @pyqtSlot(float)
    def seqSetBpm(self, bpm: float) -> None:
        if hasattr(self, "sequencer"):
            self.sequencer.set_bpm(bpm)
            self.seqStateChanged.emit()

    @pyqtSlot(int)
    def seqSetMasterResync(self, bars: int) -> None:
        if hasattr(self, "sequencer"):
            self.sequencer.song.master_resync_bars = max(0, min(64, int(bars)))
            self.seqStateChanged.emit()

    def _part_is_active(self, part_num: int) -> bool:
        """Check if part exists / has sounding content in the current performance."""
        if not hasattr(self, "patch_state") or not hasattr(self.patch_state, "perf_parts"):
            return False
        if not 1 <= part_num <= len(self.patch_state.perf_parts):
            return False
        p = self.patch_state.perf_parts[part_num - 1]
        name = str(p.patch_name or "").strip()
        has_real_name = bool(name and not name.startswith("Part "))
        return bool(p.volume > 0 or has_real_name or p.patch_file or (p.patch_msb != 0 and p.patch_pc != 0))

    def _sync_keybed_routing(self) -> None:
        """Arbitrate Roland Performance Zone Switches (PERF_ZONE_SWITCH DT1).

        Dynamic keyboard routing:
        - The focused sequencer track's target part receives ZONE = ON if and only if
          the track's keybed_enabled is True AND the part actually exists in the performance.
        - ALL OTHER parts (1..16) receive ZONE = OFF to prevent keyboard notes triggering
          unselected or backing parts.
        """
        if not hasattr(self, "sequencer"):
            return
        active_t_idx = getattr(self, "_active_seq_track", 0)
        tracks = self.sequencer.song.tracks
        if not 0 <= active_t_idx < len(tracks):
            return
        active_track = tracks[active_t_idx]
        target_part = active_track.target_parts[0] if active_track.target_parts else (active_t_idx + 1)
        active_kbd_on = getattr(active_track, "keybed_enabled", True)

        for p_idx in range(1, 17):
            # Hardware safety: NEVER send SysEx to inactive/nonexistent parts!
            # Touching an unallocated part's address causes the Roland firmware to create an Init Patch.
            if not self._part_is_active(p_idx):
                continue

            if p_idx == target_part:
                should_arm = bool(active_kbd_on)
                if hasattr(self, "setPartZoneSwitch"):
                    try:
                        self.setPartZoneSwitch(target_part, should_arm)
                    except Exception as e:
                        logger.debug(f"_sync_keybed_routing: failed to set part {target_part} to {should_arm}: {e}")
            else:
                if hasattr(self, "setPartZoneSwitch"):
                    try:
                        cur_sw = True
                        if hasattr(self, "patch_state") and hasattr(self.patch_state, "perf_parts"):
                            if 0 <= p_idx - 1 < len(self.patch_state.perf_parts):
                                cur_sw = bool(self.patch_state.perf_parts[p_idx - 1].zone_switch)
                        if cur_sw:
                            self.setPartZoneSwitch(p_idx, False)
                    except Exception as e:
                        logger.debug(f"_sync_keybed_routing: failed to disable part {p_idx}: {e}")

    @pyqtSlot(int)
    def seqSelectTrack(self, track_idx: int) -> None:
        self._active_seq_track = max(0, min(4, int(track_idx)))
        if hasattr(self, "recorder"):
            self.recorder.set_target(self._active_seq_track, self._active_seq_clip, self.seqCursorStep)
        self._sync_keybed_routing()
        self.seqActiveTrackChanged.emit()
        self.seqActiveClipChanged.emit()
        self.seqTracksChanged.emit()

    @pyqtSlot(int, int)
    def seqSetTrackTargetPart(self, track_idx: int, part_num: int) -> None:
        """Assign which Roland performance part (1..16) this track sends to."""
        if hasattr(self, "sequencer") and 0 <= track_idx < len(self.sequencer.song.tracks):
            part = max(1, min(16, int(part_num)))
            self.sequencer.song.tracks[track_idx].target_parts = [part]
            self._sync_keybed_routing()
            self.seqTracksChanged.emit()

    @pyqtSlot(int)
    def seqToggleTrackKeybed(self, track_idx: int) -> None:
        """Toggle Roland keyboard trigger routing (Zone Switch) for a track."""
        if hasattr(self, "sequencer") and 0 <= track_idx < len(self.sequencer.song.tracks):
            track = self.sequencer.song.tracks[track_idx]
            track.keybed_enabled = not getattr(track, "keybed_enabled", True)
            self._sync_keybed_routing()
            self.seqTracksChanged.emit()

    @pyqtSlot(int)
    def seqSelectClip(self, clip_idx: int) -> None:
        self._active_seq_clip = max(0, int(clip_idx))
        if hasattr(self, "recorder"):
            self.recorder.set_target(self._active_seq_track, self._active_seq_clip, 0)
        self.seqActiveClipChanged.emit()

    @pyqtSlot(int, int)
    def seqLaunchClip(self, track_idx: int, clip_idx: int) -> None:
        if hasattr(self, "sequencer"):
            self.sequencer.launch_clip(track_idx, clip_idx)
            self.seqTracksChanged.emit()

    @pyqtSlot(int)
    def seqLaunchScene(self, scene_idx: int) -> None:
        if hasattr(self, "sequencer"):
            self.sequencer.launch_scene(scene_idx)
            self.seqTracksChanged.emit()

    @pyqtSlot(int)
    def seqStopTrack(self, track_idx: int) -> None:
        if hasattr(self, "sequencer"):
            self.sequencer.stop_track(track_idx)
            self.seqTracksChanged.emit()

    # -------------------------------------------------------------------------
    # QML Step Editing Slots
    # -------------------------------------------------------------------------

    @pyqtSlot(int, int, int)
    def seqToggleStepNote(self, step_idx: int, pitch: int, velocity: int = 100) -> None:
        """Toggle a note on or off on a step."""
        t_idx = getattr(self, "_active_seq_track", 0)
        c_idx = getattr(self, "_active_seq_clip", 0)
        if hasattr(self, "sequencer") and 0 <= t_idx < len(self.sequencer.song.tracks):
            track = self.sequencer.song.tracks[t_idx]
            if 0 <= c_idx < len(track.clips):
                clip = track.clips[c_idx]
                if 0 <= step_idx < len(clip.steps):
                    step = clip.steps[step_idx]
                    matching = [n for n in step.notes if n.pitch == pitch]
                    if matching:
                        step.notes = [n for n in step.notes if n.pitch != pitch]
                    else:
                        if len(step.notes) < 6:
                            step.notes.append(NoteEvent(pitch=pitch, velocity=velocity))
                    self.seqActiveClipChanged.emit()
                    self.seqTracksChanged.emit()

    @pyqtSlot(int, str, float)
    def seqSetStepParam(self, step_idx: int, param: str, value: float) -> None:
        t_idx = getattr(self, "_active_seq_track", 0)
        c_idx = getattr(self, "_active_seq_clip", 0)
        if hasattr(self, "sequencer") and 0 <= t_idx < len(self.sequencer.song.tracks):
            track = self.sequencer.song.tracks[t_idx]
            if 0 <= c_idx < len(track.clips):
                clip = track.clips[c_idx]
                if 0 <= step_idx < len(clip.steps):
                    step = clip.steps[step_idx]
                    if param == "gateLength":
                        step.gate_length = max(0.01, min(1.0, float(value)))
                    elif param == "microTiming":
                        step.micro_timing = max(-24, min(24, int(value)))
                    elif param == "strum":
                        step.strum = max(-24, min(24, int(value)))
                    elif param == "probability":
                        step.probability = max(0.0, min(1.0, float(value)))
                    elif param == "tie":
                        step.tie = bool(value)
                    elif param == "velocity":
                        vel = max(1, min(127, int(value)))
                        if step.notes:
                            for n in step.notes:
                                n.velocity = vel
                        else:
                            default_pitch = 36 if t_idx == 4 else 60
                            step.notes.append(NoteEvent(pitch=default_pitch, velocity=vel))
                        self.seqTracksChanged.emit()
                    elif param == "pitch":
                        p = max(0, min(127, int(value)))
                        if step.notes:
                            step.notes[0].pitch = p
                        else:
                            step.notes.append(NoteEvent(pitch=p, velocity=100))
                        self.seqTracksChanged.emit()
                    self.seqActiveClipChanged.emit()

    @pyqtSlot(int)
    def seqClearStep(self, step_idx: int) -> None:
        t_idx = getattr(self, "_active_seq_track", 0)
        c_idx = getattr(self, "_active_seq_clip", 0)
        if hasattr(self, "recorder"):
            self.recorder.clear_step(step_idx)
            self.seqActiveClipChanged.emit()
            self.seqTracksChanged.emit()

    @pyqtSlot()
    def seqClearActiveClip(self) -> None:
        """Clear all notes and ties from all steps in the current active clip."""
        t_idx = getattr(self, "_active_seq_track", 0)
        c_idx = getattr(self, "_active_seq_clip", 0)
        if hasattr(self, "recorder"):
            self.recorder.clear_clip()
        elif hasattr(self, "sequencer") and 0 <= t_idx < len(self.sequencer.song.tracks):
            track = self.sequencer.song.tracks[t_idx]
            if 0 <= c_idx < len(track.clips):
                for s in track.clips[c_idx].steps:
                    s.notes.clear()
                    s.tie = False
        self.seqActiveClipChanged.emit()
        self.seqTracksChanged.emit()

    @pyqtSlot(int, int)
    def seqSetStepPitch(self, step_idx: int, pitch: int) -> None:
        """Set primary pitch of a step (adds note if empty, clamps 0..127)."""
        t_idx = getattr(self, "_active_seq_track", 0)
        c_idx = getattr(self, "_active_seq_clip", 0)
        if hasattr(self, "sequencer") and 0 <= t_idx < len(self.sequencer.song.tracks):
            track = self.sequencer.song.tracks[t_idx]
            if 0 <= c_idx < len(track.clips):
                clip = track.clips[c_idx]
                if 0 <= step_idx < len(clip.steps):
                    step = clip.steps[step_idx]
                    p = max(0, min(127, int(pitch)))
                    if step.notes:
                        step.notes[0].pitch = p
                    else:
                        step.notes.append(NoteEvent(pitch=p, velocity=100))
                    self.seqActiveClipChanged.emit()
                    self.seqTracksChanged.emit()

    @pyqtSlot(int, int)
    def seqNudgeStepPitch(self, step_idx: int, semitones: int) -> None:
        """Nudge primary pitch of step by semitones (+1, -1, +12, -12)."""
        t_idx = getattr(self, "_active_seq_track", 0)
        c_idx = getattr(self, "_active_seq_clip", 0)
        if hasattr(self, "sequencer") and 0 <= t_idx < len(self.sequencer.song.tracks):
            track = self.sequencer.song.tracks[t_idx]
            if 0 <= c_idx < len(track.clips):
                clip = track.clips[c_idx]
                if 0 <= step_idx < len(clip.steps):
                    step = clip.steps[step_idx]
                    curr_pitch = step.notes[0].pitch if step.notes else (36 if t_idx == 4 else 60)
                    new_pitch = max(0, min(127, curr_pitch + int(semitones)))
                    if step.notes:
                        step.notes[0].pitch = new_pitch
                    else:
                        step.notes.append(NoteEvent(pitch=new_pitch, velocity=100))
                    self.seqActiveClipChanged.emit()
                    self.seqTracksChanged.emit()

    @pyqtSlot(int)
    def seqSetClipLength(self, length: int) -> None:
        t_idx = getattr(self, "_active_seq_track", 0)
        c_idx = getattr(self, "_active_seq_clip", 0)
        if hasattr(self, "sequencer") and 0 <= t_idx < len(self.sequencer.song.tracks):
            track = self.sequencer.song.tracks[t_idx]
            if 0 <= c_idx < len(track.clips):
                track.clips[c_idx].set_length(length)
                self.seqActiveClipChanged.emit()
                self.seqTracksChanged.emit()

    @pyqtSlot(int, str)
    def seqSetTrackClockDivider(self, track_idx: int, divider: str) -> None:
        if hasattr(self, "sequencer") and 0 <= track_idx < len(self.sequencer.song.tracks):
            self.sequencer.song.tracks[track_idx].clock_divider = str(divider)
            self.seqTracksChanged.emit()

    @pyqtSlot(int, float)
    def seqSetTrackSwing(self, track_idx: int, swing: float) -> None:
        if hasattr(self, "sequencer") and 0 <= track_idx < len(self.sequencer.song.tracks):
            self.sequencer.song.tracks[track_idx].swing = max(0.50, min(0.75, float(swing)))
            self.seqTracksChanged.emit()

    @pyqtSlot(int)
    def seqSetCursorStep(self, step_idx: int) -> None:
        if hasattr(self, "recorder"):
            self.recorder.cursor_step = max(0, int(step_idx))
            self.seqCursorStepChanged.emit()

    # -------------------------------------------------------------------------
    # QML Recording Slots
    # -------------------------------------------------------------------------

    @pyqtSlot(bool)
    def seqToggleStepRecord(self, enabled: bool) -> None:
        if hasattr(self, "recorder"):
            self.recorder.toggle_step_record(enabled)
            self.seqRecordModeChanged.emit()

    @pyqtSlot(bool)
    def seqToggleLiveRecord(self, enabled: bool) -> None:
        if hasattr(self, "recorder"):
            self.recorder.toggle_live_record(enabled)
            self.seqRecordModeChanged.emit()
            self.seqTracksChanged.emit()

    @pyqtSlot()
    def seqRecordRest(self) -> None:
        if hasattr(self, "recorder"):
            self.recorder.record_rest()
            self.seqCursorStepChanged.emit()

    @pyqtSlot()
    def seqRecordTie(self) -> None:
        if hasattr(self, "recorder"):
            self.recorder.record_tie()
            self.seqCursorStepChanged.emit()
            self.seqActiveClipChanged.emit()
