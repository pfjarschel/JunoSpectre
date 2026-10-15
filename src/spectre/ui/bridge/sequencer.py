"""Sequencer bridge mixin exposing multi-track playback, clip launching and step editing to QML."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtProperty, pyqtSignal, pyqtSlot

from ...sequencer.chords import chord_name
from ...sequencer.engine import SequencerEngine
from ...sequencer.models import (
    MAX_DICE_TIMING,
    MAX_DICE_VELOCITY,
    MAX_STEP_NOTES,
    MAX_TRACK_NAME,
    NUM_TRACKS,
    TRACK_BANK_SIZE,
    Clip,
    NoteEvent,
    Step,
    default_sequencer_song,
)
from ...sequencer.recording import SequencerRecorder
from .base import BridgeBaseMixin

logger = logging.getLogger(__name__)

# Pitches a new note on a drum step tries first: BD, SD, CH, OH, CP, CY
DRUM_ADD_ORDER = (36, 38, 42, 46, 39, 49)


class SequencerBridgeMixin(BridgeBaseMixin):
    """Bridge mixin for the sequencer, session matrix, and step editor."""

    seqStateChanged = pyqtSignal()
    seqPlayheadsChanged = pyqtSignal()
    seqTracksChanged = pyqtSignal()
    seqActiveTrackChanged = pyqtSignal()
    seqActiveClipChanged = pyqtSignal()
    seqRecordModeChanged = pyqtSignal()
    seqCursorStepChanged = pyqtSignal()
    seqKbdChannelChanged = pyqtSignal()
    # Internal: carries engine/recorder notifications from the clock and MIDI
    # threads to the GUI thread (QML bindings must only update there).
    _seqUiSync = pyqtSignal(int)

    _SYNC_PLAYHEADS = 1
    _SYNC_RECORDER = 2
    _SYNC_CLIPS = 3
    _SYNC_KBD = 4

    def _init_sequencer(self) -> None:
        """Initialize sequencer engine, recorder, and subscriptions."""
        midi_mgr = self.juno
        midi_mgr = getattr(midi_mgr, "midi", None) if midi_mgr else None

        self.sequencer = SequencerEngine(
            song=default_sequencer_song(),
            midi_mgr=midi_mgr,
            channel_resolver=self._part_rx_channel,
        )
        self.recorder = SequencerRecorder(self.sequencer)
        # One global tempo: vector motion follows the sequencer song's BPM
        self.vector.motion.bpm = self.sequencer.bpm

        self._active_seq_track: int = 0
        # Rx channel of the panel's current part, learned from keyboard notes
        # (the current part can't be read over SysEx). -1 until a key is played.
        self._kbd_channel: int = -1

        self._seqUiSync.connect(self._apply_seq_ui_sync, Qt.ConnectionType.QueuedConnection)
        # One part/track cursor: part edits made elsewhere move it too
        self.perfPartsChanged.connect(self._cursor_follow_part)

        # Subscribe engine UI updates to Qt signals
        self.sequencer.subscribe_ui(self._on_seq_ui_update)
        # Subscribe recorder UI updates to Qt signals
        self.recorder.subscribe_ui(self._on_rec_ui_update)

        self._attach_seq_midi(midi_mgr)

    def _attach_seq_midi(self, midi_mgr) -> None:
        """Play to and record from midi_mgr (also when the synth connects later)."""
        if midi_mgr is None:
            return
        self.sequencer.midi = midi_mgr
        # Connect note listener to recorder if midi manager supports it
        if hasattr(midi_mgr, "add_note_listener"):
            midi_mgr.add_note_listener(self.recorder.handle_midi_message)
            midi_mgr.add_note_listener(self._on_kbd_note)
        if hasattr(midi_mgr, "start_input_worker"):
            midi_mgr.start_input_worker()

    def _on_seq_ui_update(self, snapshot: dict) -> None:
        """Receive downsampled playback updates from SequencerEngine (clock thread)."""
        clips = tuple(tuple(snapshot.get(k, ())) for k in (
            "active_clips", "queued_clips", "lane_active_clips", "lane_queued_clips"))
        if clips != getattr(self, "_last_seq_clips", None):
            # A queued launch/stop took effect on the bar: refresh clip states too.
            self._last_seq_clips = clips
            self._seqUiSync.emit(self._SYNC_CLIPS)
        self._seqUiSync.emit(self._SYNC_PLAYHEADS)

    def _on_rec_ui_update(self, event_type: str, data: Any = None) -> None:
        """Receive recording/audition/step updates from SequencerRecorder (MIDI thread)."""
        self._seqUiSync.emit(self._SYNC_RECORDER)

    def _on_kbd_note(self, msg) -> None:
        """Learn the current part's channel from played keys (MIDI thread)."""
        if msg.type == "note_on" and msg.velocity > 0 and msg.channel != self._kbd_channel:
            self._kbd_channel = int(msg.channel)
            self._seqUiSync.emit(self._SYNC_KBD)

    def _apply_seq_ui_sync(self, kind: int) -> None:
        """Emit QML notify signals on the GUI thread."""
        if kind == self._SYNC_KBD:
            self.seqKbdChannelChanged.emit()
        elif kind == self._SYNC_PLAYHEADS:
            self.seqPlayheadsChanged.emit()
        elif kind == self._SYNC_CLIPS:
            self.seqTracksChanged.emit()
            self.seqAutomationChanged.emit()
            if hasattr(self, "_audio_release_tempo"):
                self._audio_release_tempo()   # synced audio may have stopped on the bar
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

    @pyqtProperty(int, notify=seqStateChanged)
    def seqMasterResync(self) -> int:
        return self.sequencer.song.master_resync_bars if hasattr(self, "sequencer") else 0

    @pyqtProperty(int, notify=seqKbdChannelChanged)
    def seqKbdChannel(self) -> int:
        """MIDI channel (0..15) the keyboard last played on, -1 when unknown."""
        return getattr(self, "_kbd_channel", -1)

    @pyqtProperty(int, notify=seqActiveTrackChanged)
    def seqActiveTrack(self) -> int:
        return getattr(self, "_active_seq_track", 0)

    @pyqtProperty(int, notify=seqActiveClipChanged)
    def seqActiveClip(self) -> int:
        """Selected clip of the active track (each track keeps its own)."""
        return self._seq_selected_clip(getattr(self, "_active_seq_track", 0))

    @pyqtProperty(int, notify=seqActiveTrackChanged)
    def seqTrackBank(self) -> int:
        """Part/track bank on every page (0 = 1-8, 1 = 9-16): the one holding the cursor."""
        return getattr(self, "_active_seq_track", 0) // TRACK_BANK_SIZE

    @pyqtSlot(int)
    def seqSetTrackBank(self, bank: int) -> None:
        """Show another bank by selecting the track in the same column there."""
        banks = NUM_TRACKS // TRACK_BANK_SIZE
        bank = max(0, min(banks - 1, int(bank)))
        if bank != self.seqTrackBank:
            self.seqSelectTrack(bank * TRACK_BANK_SIZE + getattr(self, "_active_seq_track", 0) % TRACK_BANK_SIZE)

    def _seq_selected_clip(self, track_idx: int) -> int:
        if hasattr(self, "sequencer") and 0 <= track_idx < len(self.sequencer.song.tracks):
            return self.sequencer.song.tracks[track_idx].selected_clip_idx
        return 0

    def _seq_is_drum(self, track_idx: int) -> bool:
        """Drum tracks are the ones sending to the rhythm part."""
        tracks = self.sequencer.song.tracks if hasattr(self, "sequencer") else []
        return 0 <= track_idx < len(tracks) and tracks[track_idx].is_drum

    def _seq_retarget_recorder(self, step_idx: int = 0) -> None:
        """Point the recorder at the active track's selected clip."""
        if hasattr(self, "recorder"):
            t_idx = getattr(self, "_active_seq_track", 0)
            self.recorder.set_target(t_idx, self._seq_selected_clip(t_idx), step_idx)

    @pyqtProperty("QVariantList", notify=seqPlayheadsChanged)
    def seqPlayheads(self) -> list:
        if not hasattr(self, "sequencer"):
            return [0, 0, 0, 0, 0]
        return list(self.sequencer.track_steps)

    @pyqtProperty("QVariantList", notify=seqPlayheadsChanged)
    def seqLanePlayheads(self) -> list:
        """Current step of each automation lane."""
        return list(self.sequencer.lane_steps)

    @pyqtProperty("QVariantList", notify=seqTracksChanged)
    def seqTracks(self) -> list:
        if not hasattr(self, "sequencer"):
            return []
        out = []
        for i, t in enumerate(self.sequencer.song.tracks):
            target_part = t.target_parts[0] if t.target_parts else (i + 1)
            out.append({
                "trackId": t.track_id,
                "name": t.name,
                "kind": t.kind,
                "isDrum": t.is_drum,
                "targetParts": list(t.target_parts),
                "targetPart": target_part,
                "layerParts": list(t.target_parts[1:]),
                "partIsActive": self._part_is_active(target_part),
                "clockDivider": t.clock_divider,
                "swing": t.swing,
                "diceTiming": t.dice_timing,
                "diceVelocity": t.dice_velocity,
                "activeClipIdx": t.active_clip_idx,
                "queuedClipIdx": t.queued_clip_idx,
                "selectedClipIdx": t.selected_clip_idx,
                "clipCount": len(t.clips),
                "clips": [
                    {
                        "clipId": c.clip_id,
                        "name": c.name,
                        "length": c.length,
                        "hasNotes": any(s.is_active for s in c.steps),
                        **(self._audio_clip_dict(c) if t.is_audio else {}),
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
        c_idx = self._seq_selected_clip(t_idx)
        if 0 <= t_idx < len(self.sequencer.song.tracks):
            track = self.sequencer.song.tracks[t_idx]
            if 0 <= c_idx < len(track.clips):
                clip = track.clips[c_idx]
                # Notes from earlier steps still held on each step
                held = [0] * len(clip.steps)
                for i, s in enumerate(clip.steps):
                    for n in s.notes:
                        for k in range(i + 1, min(len(held), i + n.length)):
                            held[k] += 1
                return [self._seq_step_dict(i, s, track.is_drum, held[i]) for i, s in enumerate(clip.steps)]
        return []

    @staticmethod
    def _seq_step_dict(i: int, s: Step, is_drum: bool, held: int = 0) -> Dict[str, Any]:
        notes = sorted(s.notes, key=lambda n: n.pitch)
        return {
            "index": i,
            "gateLength": s.gate_length,
            "microTiming": s.micro_timing,
            "strum": s.strum,
            "probability": s.probability,
            "held": held,
            "isActive": s.is_active,
            "noteCount": len(notes),
            "notes": [n.to_dict() for n in notes],  # low to high
            "chordName": "" if is_drum else chord_name(n.pitch for n in notes),
            "primaryPitch": notes[0].pitch if notes else -1,
            "primaryVelocity": notes[0].velocity if notes else 0,
            "maxVelocity": max((n.velocity for n in notes), default=0),
        }

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
            if self.sequencer.clock.is_stopped:
                self._arp_resync_clock()
            self.sequencer.play()
            self.seqStateChanged.emit()
            self.seqTracksChanged.emit()

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
            if hasattr(self, "_audio_release_tempo"):
                self._audio_release_tempo()

    @pyqtSlot()
    def seqTogglePlay(self) -> None:
        if hasattr(self, "sequencer"):
            if self.sequencer.is_playing:
                self.seqStop()
            else:
                self.seqPlay()

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

    @pyqtSlot(int)
    def seqSelectTrack(self, track_idx: int) -> None:
        """Move the part/track cursor: in PERFORM mode track n and part n are selected together."""
        self._seq_set_cursor(track_idx)
        part = self._active_seq_track + 1
        if self._in_perform() and int(self.patch_state.active_perf_part) != part:
            self.editPerfPart(part)

    def _seq_set_cursor(self, track_idx: int) -> None:
        """Select a track without touching the edited part (that side is already in place)."""
        self._active_seq_track = max(0, min(NUM_TRACKS - 1, int(track_idx)))
        self._seq_retarget_recorder(self.seqCursorStep)
        self.seqActiveTrackChanged.emit()
        self.seqActiveClipChanged.emit()
        self.seqTracksChanged.emit()

    def _cursor_follow_part(self, *_args) -> None:
        """PERFORM: the edited part changed elsewhere (song load, panel): the cursor follows."""
        if not self._in_perform():
            return
        track = int(self.patch_state.active_perf_part) - 1
        if 0 <= track < NUM_TRACKS and track != self._active_seq_track:
            self._seq_set_cursor(track)

    @pyqtSlot(int)
    def selectNextTrack(self, step: int) -> None:
        """Track ◀▶: the next/previous part/track; crossing slot 8/9 turns the bank."""
        self.seqSelectTrack(max(0, min(NUM_TRACKS - 1, self._active_seq_track + int(step))))

    @pyqtSlot(int, int)
    def seqSetTrackTargetPart(self, track_idx: int, part_num: int) -> None:
        """Assign the main Roland performance part (1..16) this track sends to (layers kept)."""
        if hasattr(self, "sequencer") and 0 <= track_idx < len(self.sequencer.song.tracks):
            part = max(1, min(16, int(part_num)))
            track = self.sequencer.song.tracks[track_idx]
            track.target_parts = [part] + [p for p in track.target_parts[1:] if p != part]
            self.seqTracksChanged.emit()
            self._auto_lane_edited()  # linked lanes write to the track's parts
            self.seqActiveClipChanged.emit()  # drum-ness (chord names) may have changed

    @pyqtSlot(int, str)
    def seqRenameTrack(self, track_idx: int, name: str) -> None:
        if hasattr(self, "sequencer") and 0 <= track_idx < len(self.sequencer.song.tracks):
            name = str(name).strip()[:MAX_TRACK_NAME]
            self.sequencer.song.tracks[track_idx].name = name or f"Track {track_idx + 1}"
            self.seqTracksChanged.emit()

    @pyqtSlot(int, int)
    def seqToggleTrackLayer(self, track_idx: int, part_num: int) -> None:
        """Add/remove an extra part the track also sends to (the main part stays)."""
        if hasattr(self, "sequencer") and 0 <= track_idx < len(self.sequencer.song.tracks):
            part = max(1, min(16, int(part_num)))
            track = self.sequencer.song.tracks[track_idx]
            main = track.target_parts[0] if track.target_parts else track_idx + 1
            layers = list(track.target_parts[1:])
            if part == main:
                return
            if part in layers:
                layers.remove(part)
            else:
                layers.append(part)
            track.target_parts = [main] + sorted(layers)
            self.seqTracksChanged.emit()
            self._auto_lane_edited()  # linked lanes write to the track's parts

    @pyqtSlot(int, bool)
    def seqSetTrackKbd(self, track_idx: int, enabled: bool) -> None:
        """Kbd switch for every part the track sends to (layers play together)."""
        if hasattr(self, "sequencer") and 0 <= track_idx < len(self.sequencer.song.tracks):
            for part in self.sequencer.song.tracks[track_idx].target_parts or [track_idx + 1]:
                self.setPartZoneSwitch(int(part), bool(enabled))

    @pyqtSlot(int)
    def seqSelectClip(self, clip_idx: int) -> None:
        """Select the clip to edit on the active track (kept per track)."""
        t_idx = getattr(self, "_active_seq_track", 0)
        if hasattr(self, "sequencer") and 0 <= t_idx < len(self.sequencer.song.tracks):
            track = self.sequencer.song.tracks[t_idx]
            track.selected_clip_idx = max(0, min(len(track.clips) - 1, int(clip_idx)))
        self._seq_retarget_recorder()
        self.seqActiveClipChanged.emit()
        self.seqTracksChanged.emit()

    @pyqtSlot(int, int)
    def seqLaunchClip(self, track_idx: int, clip_idx: int) -> None:
        if hasattr(self, "sequencer"):
            before = self.seqActiveClip
            self.sequencer.launch_clip(track_idx, clip_idx)
            self._seq_after_launch(before)

    @pyqtSlot(int)
    def seqLaunchScene(self, scene_idx: int) -> None:
        if hasattr(self, "sequencer"):
            before = self.seqActiveClip
            self.sequencer.launch_scene(scene_idx)
            self._seq_after_launch(before)

    def _seq_after_launch(self, selected_before: int) -> None:
        if self.seqActiveClip != selected_before:
            self._seq_retarget_recorder()
            self.seqActiveClipChanged.emit()
        self.seqTracksChanged.emit()
        self.seqAutomationChanged.emit()

    @pyqtSlot(int)
    def seqStopTrack(self, track_idx: int) -> None:
        if hasattr(self, "sequencer"):
            self.sequencer.stop_track(track_idx)
            self.seqTracksChanged.emit()

    @pyqtSlot()
    def seqStopAllClips(self) -> None:
        """Stop every playing clip at the next bar; the transport keeps running."""
        if hasattr(self, "sequencer"):
            self.sequencer.stop_all_clips()
            self.seqTracksChanged.emit()
            self.seqAutomationChanged.emit()

    def _seq_clip_state(self, track_idx: int, clip_idx: int) -> str:
        """"empty" / "loaded" / "queued" / "playing" for a clip slot (controller LEDs)."""
        tracks = self.sequencer.song.tracks if hasattr(self, "sequencer") else []
        if not 0 <= track_idx < len(tracks) or not 0 <= clip_idx < len(tracks[track_idx].clips):
            return "empty"
        track, seq = tracks[track_idx], self.sequencer
        if track.queued_clip_idx == clip_idx:
            return "queued"
        if track.active_clip_idx == clip_idx and (
                seq.is_playing or seq._audio_active_clip(track) is not None):
            return "playing"
        clip = track.clips[clip_idx]
        if track.is_audio:
            full = clip.audio is not None and bool(clip.audio.file)
        else:
            full = any(s.is_active for s in clip.steps)
        return "loaded" if full else "empty"

    # -------------------------------------------------------------------------
    # QML Step Editing Slots
    # -------------------------------------------------------------------------

    @pyqtSlot(int, int, int)
    def seqToggleStepNote(self, step_idx: int, pitch: int, velocity: int = 100) -> None:
        """Toggle a note on or off on a step."""
        t_idx = getattr(self, "_active_seq_track", 0)
        c_idx = self._seq_selected_clip(t_idx)
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
                        if len(step.notes) < MAX_STEP_NOTES:
                            step.notes.append(NoteEvent(pitch=pitch, velocity=velocity))
                            step.notes.sort(key=lambda n: n.pitch)
                    self.seqActiveClipChanged.emit()
                    self.seqTracksChanged.emit()

    @pyqtSlot(int, str, float)
    def seqSetStepParam(self, step_idx: int, param: str, value: float) -> None:
        t_idx = getattr(self, "_active_seq_track", 0)
        c_idx = self._seq_selected_clip(t_idx)
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
                    elif param == "velocity":
                        vel = max(1, min(127, int(value)))
                        if step.notes:
                            for n in step.notes:
                                n.velocity = vel
                        else:
                            default_pitch = 36 if self._seq_is_drum(t_idx) else 60
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
        c_idx = self._seq_selected_clip(t_idx)
        if hasattr(self, "recorder"):
            self.recorder.clear_step(step_idx)
            self.seqActiveClipChanged.emit()
            self.seqTracksChanged.emit()

    @pyqtSlot()
    def seqClearActiveClip(self) -> None:
        """Clear all notes from the current active clip."""
        t_idx = getattr(self, "_active_seq_track", 0)
        c_idx = self._seq_selected_clip(t_idx)
        if hasattr(self, "recorder"):
            self.recorder.clear_clip()
        elif hasattr(self, "sequencer") and 0 <= t_idx < len(self.sequencer.song.tracks):
            track = self.sequencer.song.tracks[t_idx]
            if 0 <= c_idx < len(track.clips):
                for s in track.clips[c_idx].steps:
                    s.notes.clear()
        self.seqActiveClipChanged.emit()
        self.seqTracksChanged.emit()

    @pyqtSlot(int, int)
    def seqSetStepPitch(self, step_idx: int, pitch: int) -> None:
        """Set primary pitch of a step (adds note if empty, clamps 0..127)."""
        t_idx = getattr(self, "_active_seq_track", 0)
        c_idx = self._seq_selected_clip(t_idx)
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
        c_idx = self._seq_selected_clip(t_idx)
        if hasattr(self, "sequencer") and 0 <= t_idx < len(self.sequencer.song.tracks):
            track = self.sequencer.song.tracks[t_idx]
            if 0 <= c_idx < len(track.clips):
                clip = track.clips[c_idx]
                if 0 <= step_idx < len(clip.steps):
                    step = clip.steps[step_idx]
                    curr_pitch = step.notes[0].pitch if step.notes else (36 if self._seq_is_drum(t_idx) else 60)
                    new_pitch = max(0, min(127, curr_pitch + int(semitones)))
                    if step.notes:
                        step.notes[0].pitch = new_pitch
                    else:
                        step.notes.append(NoteEvent(pitch=new_pitch, velocity=100))
                    self.seqActiveClipChanged.emit()
                    self.seqTracksChanged.emit()

    # -- Per-note editing (the pad's note grid). Notes are addressed by pitch,
    # since a step never holds the same pitch twice; slots that move a note
    # return its new pitch so the UI selection can follow it.

    def _seq_edit_clip(self) -> Optional[Clip]:
        """The active track's selected clip, if any."""
        t_idx = getattr(self, "_active_seq_track", 0)
        c_idx = self._seq_selected_clip(t_idx)
        if hasattr(self, "sequencer") and 0 <= t_idx < len(self.sequencer.song.tracks):
            track = self.sequencer.song.tracks[t_idx]
            if 0 <= c_idx < len(track.clips):
                return track.clips[c_idx]
        return None

    def _seq_edit_step(self, step_idx: int) -> Optional[Step]:
        """The step at step_idx in the active track's selected clip, if any."""
        clip = self._seq_edit_clip()
        if clip is not None and 0 <= step_idx < len(clip.steps):
            return clip.steps[step_idx]
        return None

    def _seq_step_edited(self, step: Step) -> None:
        step.notes.sort(key=lambda n: n.pitch)
        self.seqActiveClipChanged.emit()
        self.seqTracksChanged.emit()

    @pyqtSlot(int, result=int)
    def seqAddStepNote(self, step_idx: int) -> int:
        """Add a note to a step: a default pitch on an empty step, else the first
        free pitch above the highest note. Returns the new pitch, or -1 if full."""
        step = self._seq_edit_step(step_idx)
        if step is None or len(step.notes) >= MAX_STEP_NOTES:
            return -1
        used = {n.pitch for n in step.notes}
        is_drum = self._seq_is_drum(getattr(self, "_active_seq_track", 0))
        free_drums = [p for p in DRUM_ADD_ORDER if p not in used] if is_drum else []
        if free_drums:
            pitch = free_drums[0]
        elif not step.notes:
            pitch = 60
        else:
            top = max(used)
            above = [p for p in range(top + 1, 128) if p not in used]
            below = [p for p in range(top - 1, -1, -1) if p not in used]
            pitch = (above or below)[0]
        velocity = max(step.notes, key=lambda n: n.pitch).velocity if step.notes else 100
        step.notes.append(NoteEvent(pitch=pitch, velocity=velocity))
        self._seq_step_edited(step)
        return pitch

    @pyqtSlot(int, int)
    def seqDeleteStepNote(self, step_idx: int, pitch: int) -> None:
        step = self._seq_edit_step(step_idx)
        if step is not None and any(n.pitch == pitch for n in step.notes):
            step.notes = [n for n in step.notes if n.pitch != pitch]
            self._seq_step_edited(step)

    @pyqtSlot(int, int, int, result=int)
    def seqNudgeNotePitch(self, step_idx: int, pitch: int, semitones: int) -> int:
        """Move one note by semitones, skipping pitches the step already has.
        Returns its new pitch (unchanged if it can't move), or -1 if not found."""
        step = self._seq_edit_step(step_idx)
        note = next((n for n in step.notes if n.pitch == pitch), None) if step else None
        if note is None or not semitones:
            return pitch if note else -1
        used = {n.pitch for n in step.notes if n is not note}
        direction = 1 if semitones > 0 else -1
        new = pitch + int(semitones)
        while new in used:
            new += direction
        if not 0 <= new <= 127:
            return pitch
        note.pitch = new
        self._seq_step_edited(step)
        return new

    @pyqtSlot(int, int, int, result=int)
    def seqSetNotePitch(self, step_idx: int, pitch: int, new_pitch: int) -> int:
        """Change one note to new_pitch (drum quick buttons). If the step has no
        such note it gets one added; if new_pitch is already there nothing moves.
        Returns the pitch to select, or -1 if the step is missing or full."""
        step = self._seq_edit_step(step_idx)
        if step is None:
            return -1
        new_pitch = max(0, min(127, int(new_pitch)))
        if any(n.pitch == new_pitch for n in step.notes):
            return new_pitch
        note = next((n for n in step.notes if n.pitch == pitch), None)
        if note is not None:
            note.pitch = new_pitch
        elif len(step.notes) < MAX_STEP_NOTES:
            step.notes.append(NoteEvent(pitch=new_pitch, velocity=100))
        else:
            return -1
        self._seq_step_edited(step)
        return new_pitch

    @pyqtSlot(int, int, result=int)
    def seqAddRollNote(self, step_idx: int, pitch: int) -> int:
        """Add a one-step note at a pitch (piano roll tap), with the velocity of
        the step's top note. Returns the pitch, or -1 if taken or the step is full."""
        step = self._seq_edit_step(step_idx)
        pitch = int(pitch)
        if (step is None or not 0 <= pitch <= 127 or len(step.notes) >= MAX_STEP_NOTES
                or any(n.pitch == pitch for n in step.notes)):
            return -1
        velocity = max(step.notes, key=lambda n: n.pitch).velocity if step.notes else 100
        step.notes.append(NoteEvent(pitch=pitch, velocity=velocity))
        self._seq_step_edited(step)
        return pitch

    @pyqtSlot(int, int, int, result=int)
    def seqSetNoteLength(self, step_idx: int, pitch: int, length: int) -> int:
        """Hold one note for length steps, up to the clip end or the next note
        of the same pitch. Returns the length set, or -1 if the note is missing."""
        clip = self._seq_edit_clip()
        step = self._seq_edit_step(step_idx)
        note = next((n for n in step.notes if n.pitch == pitch), None) if step else None
        if note is None:
            return -1
        limit = clip.length - step_idx
        for k in range(step_idx + 1, min(len(clip.steps), clip.length)):
            if any(n.pitch == pitch for n in clip.steps[k].notes):
                limit = k - step_idx
                break
        new = max(1, min(limit, int(length)))
        if new != note.length:
            note.length = new
            self._seq_step_edited(step)
        return new

    @pyqtSlot(int, int, int)
    def seqSetNoteVelocity(self, step_idx: int, pitch: int, velocity: int) -> None:
        step = self._seq_edit_step(step_idx)
        note = next((n for n in step.notes if n.pitch == pitch), None) if step else None
        if note is not None:
            note.velocity = max(1, min(127, int(velocity)))
            self._seq_step_edited(step)

    @pyqtSlot(int)
    def seqSetClipLength(self, length: int) -> None:
        t_idx = getattr(self, "_active_seq_track", 0)
        c_idx = self._seq_selected_clip(t_idx)
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

    @pyqtSlot(int, int, int)
    def seqSetTrackDice(self, track_idx: int, timing: int, velocity: int) -> None:
        """Dice (humanize): random +/- ticks and +/- % of 127 velocity, rolled per note."""
        if hasattr(self, "sequencer") and 0 <= track_idx < len(self.sequencer.song.tracks):
            track = self.sequencer.song.tracks[track_idx]
            track.dice_timing = max(0, min(MAX_DICE_TIMING, int(timing)))
            track.dice_velocity = max(0, min(MAX_DICE_VELOCITY, int(velocity)))
            self.seqTracksChanged.emit()

    @pyqtSlot(int)
    def seqSetCursorStep(self, step_idx: int) -> None:
        if hasattr(self, "recorder"):
            self.recorder.cursor_step = max(0, int(step_idx))
            self.seqCursorStepChanged.emit()

    # -------------------------------------------------------------------------
    # QML Recording Slots
    # -------------------------------------------------------------------------

    def _seq_active_is_audio(self) -> bool:
        tracks = self.sequencer.song.tracks if hasattr(self, "sequencer") else []
        t_idx = getattr(self, "_active_seq_track", 0)
        return 0 <= t_idx < len(tracks) and tracks[t_idx].is_audio

    @pyqtSlot(bool)
    def seqToggleStepRecord(self, enabled: bool) -> None:
        if enabled and self._seq_active_is_audio():
            return  # audio tracks don't record notes
        if hasattr(self, "recorder"):
            self.recorder.toggle_step_record(enabled)
            self.seqRecordModeChanged.emit()

    @pyqtSlot(bool)
    def seqToggleLiveRecord(self, enabled: bool) -> None:
        if enabled and self._seq_active_is_audio():
            return
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
