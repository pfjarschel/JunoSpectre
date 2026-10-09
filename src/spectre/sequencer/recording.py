"""Step entry and live recording engines for the Juno Spectre Sequencer."""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Set

import mido

from .engine import SequencerEngine
from .models import MAX_STEP_NOTES, Clip, NoteEvent, Step

logger = logging.getLogger(__name__)


class SequencerRecorder:
    """Manages paused step-entry chord capture and live overdub recording."""

    def __init__(self, engine: SequencerEngine):
        self.engine = engine
        self.step_record_enabled: bool = False
        self.live_record_enabled: bool = False
        # Keys set the cursor step's pitch while stopped only when the step editor
        # is on screen; elsewhere the keyboard is just played.
        self.audition_enabled: bool = False

        self.active_track_idx: int = 0
        self.active_clip_idx: int = 0
        self.cursor_step: int = 0

        # Step entry buffer: tracks currently held notes and captured velocities
        self._held_notes: Dict[int, int] = {}  # pitch -> velocity
        self._buffered_chord: List[NoteEvent] = []
        self._ui_callbacks: List[Callable[[str, Any], None]] = []

    def subscribe_ui(self, callback: Callable[[str, Any], None]) -> None:
        """Register a callback to receive recorder UI update notifications."""
        if callback not in self._ui_callbacks:
            self._ui_callbacks.append(callback)

    def _notify_ui(self, event_type: str, data: Any = None) -> None:
        """Dispatch update events to registered UI listeners."""
        for cb in self._ui_callbacks:
            try:
                cb(event_type, data)
            except Exception as e:
                logger.error(f"Error in recorder UI callback: {e}")

    def toggle_step_record(self, enabled: bool) -> None:
        self.step_record_enabled = bool(enabled)
        self._held_notes.clear()
        self._buffered_chord.clear()
        self._notify_ui("step_record_toggle", self.step_record_enabled)

    def toggle_live_record(self, enabled: bool) -> None:
        self.live_record_enabled = bool(enabled)
        if self.live_record_enabled:
            self._ensure_target_launched()
        self._notify_ui("live_record_toggle", self.live_record_enabled)

    def set_target(self, track_idx: int, clip_idx: int, step_idx: int = 0) -> None:
        self.active_track_idx = max(0, min(4, int(track_idx)))
        self.active_clip_idx = max(0, int(clip_idx))
        self.cursor_step = max(0, int(step_idx))
        if self.live_record_enabled:
            self._ensure_target_launched()
        self._notify_ui("target_changed", {"track": self.active_track_idx, "clip": self.active_clip_idx, "step": self.cursor_step})

    def _target_is_playing(self) -> bool:
        """True when the selected clip is the one sounding on its track."""
        tracks = self.engine.song.tracks
        if not 0 <= self.active_track_idx < len(tracks):
            return False
        return tracks[self.active_track_idx].active_clip_idx == self.active_clip_idx

    @property
    def live_record_waiting(self) -> bool:
        """Overdub is armed but the selected clip hasn't started playing yet (queued for the bar)."""
        return self.live_record_enabled and not self._target_is_playing()

    def _ensure_target_launched(self) -> None:
        """Queue the selected clip on its track (Ableton-style) so overdub can record into it."""
        if self._target_is_playing() or self._get_active_clip() is None:
            return
        track = self.engine.song.tracks[self.active_track_idx]
        if track.queued_clip_idx != self.active_clip_idx:
            self.engine.launch_clip(self.active_track_idx, self.active_clip_idx)

    def record_rest(self) -> int:
        """Advance cursor by one step without writing notes."""
        clip = self._get_active_clip()
        if clip:
            self.cursor_step = (self.cursor_step + 1) % clip.length
        self._notify_ui("rest", self.cursor_step)
        return self.cursor_step

    def record_tie(self) -> int:
        """Set tie flag on the active step and advance cursor."""
        clip = self._get_active_clip()
        if clip and self.cursor_step < len(clip.steps):
            clip.steps[self.cursor_step].tie = True
            self.cursor_step = (self.cursor_step + 1) % clip.length
        self._notify_ui("tie", self.cursor_step)
        return self.cursor_step

    def clear_step(self, step_idx: int) -> None:
        """Clear notes and tie on a designated step."""
        clip = self._get_active_clip()
        if clip and 0 <= step_idx < len(clip.steps):
            clip.steps[step_idx].notes.clear()
            clip.steps[step_idx].tie = False
            self._notify_ui("clear", step_idx)

    def clear_clip(self) -> None:
        """Clear all notes and ties across all steps on the active clip."""
        clip = self._get_active_clip()
        if clip:
            for s in clip.steps:
                s.notes.clear()
                s.tie = False
            self._notify_ui("clear_clip")

    def handle_midi_message(self, msg: mido.Message) -> None:
        """Process incoming MIDI note from keyboard or external controller."""
        if msg.type not in ("note_on", "note_off"):
            return

        pitch = msg.note
        vel = msg.velocity if msg.type == "note_on" else 0

        # 1. Step entry mode (when transport is halted or step entry is armed)
        if self.step_record_enabled and not self.engine.is_playing:
            self._handle_step_entry_note(pitch, vel)
            return

        # 2. Audition / keyboard pitch change on active step (when stopped and step rec is off)
        if (self.audition_enabled and not self.engine.is_playing and not self.step_record_enabled
                and msg.type == "note_on" and vel > 0):
            clip = self._get_active_clip()
            if clip and 0 <= self.cursor_step < len(clip.steps):
                step = clip.steps[self.cursor_step]
                step.notes = [NoteEvent(pitch=pitch, velocity=vel)]
                self._notify_ui("pitch_set", pitch)
            return

        # 3. Live overdub mode (when transport is running)
        if self.live_record_enabled and self.engine.is_playing and msg.type == "note_on" and vel > 0:
            if self._target_is_playing():
                self._handle_live_overdub_note(pitch, vel)
            else:
                # Selected clip not sounding yet: launch it; recording starts once it plays.
                self._ensure_target_launched()

    def _handle_step_entry_note(self, pitch: int, vel: int) -> None:
        """Buffer incoming chord until all keys are released, then commit to step."""
        clip = self._get_active_clip()
        if not clip or self.cursor_step >= len(clip.steps):
            return

        if vel > 0:
            # Key pressed
            self._held_notes[pitch] = vel
            self._buffered_chord.append(NoteEvent(pitch=pitch, velocity=vel))
            self._notify_ui("held", pitch)
        else:
            # Key released
            self._held_notes.pop(pitch, None)
            if not self._held_notes and self._buffered_chord:
                # All keys released: commit chord to step
                # Deduplicate notes by pitch keeping highest velocity
                unique_notes: Dict[int, int] = {}
                for n in self._buffered_chord:
                    if n.pitch not in unique_notes or n.velocity > unique_notes[n.pitch]:
                        unique_notes[n.pitch] = n.velocity
                clip.steps[self.cursor_step].notes = sorted(
                    (NoteEvent(p, v) for p, v in list(unique_notes.items())[:MAX_STEP_NOTES]),
                    key=lambda n: n.pitch,
                )
                self._buffered_chord.clear()
                # Auto-advance
                self.cursor_step = (self.cursor_step + 1) % clip.length
                self._notify_ui("committed", self.cursor_step)

    def _handle_live_overdub_note(self, pitch: int, vel: int) -> None:
        """Record a live note into the selected clip (which is playing), on the nearest step.

        Notes in the first half of a step land on it with a positive micro-offset;
        notes in the second half land on the next step with a negative one (played
        early via the engine's lookahead). The first note on an empty step sets its
        micro-timing; further notes join that timing.
        """
        eng = self.engine
        t_idx = self.active_track_idx
        target = -1
        with eng.lock:
            if not 0 <= t_idx < len(eng.song.tracks) or t_idx >= len(eng.track_steps):
                return
            track = eng.song.tracks[t_idx]
            c_idx = self.active_clip_idx
            if track.active_clip_idx != c_idx or not 0 <= c_idx < len(track.clips) or not eng._track_step_started[t_idx]:
                return
            clip = track.clips[c_idx]
            if clip.length <= 0:
                return

            step_len = eng._track_step_ticks[t_idx]
            current = eng.track_steps[t_idx] % clip.length
            elapsed = eng._track_tick_accum[t_idx]  # ticks since the current step's grid position
            ahead = elapsed > step_len // 2
            if ahead:
                target, micro = (current + 1) % clip.length, elapsed - step_len
            else:
                target, micro = current, elapsed
            if target >= len(clip.steps):
                return
            micro -= eng.swing_delay(track, target, step_len)

            step = clip.steps[target]
            if any(n.pitch == pitch for n in step.notes) or len(step.notes) >= MAX_STEP_NOTES:
                return
            if not step.notes:
                step.micro_timing = max(-24, min(24, micro))
            step.notes.append(NoteEvent(pitch=pitch, velocity=vel))
            step.notes.sort(key=lambda n: n.pitch)
            if ahead:
                # The player is already sounding it; don't retrigger it on this pass.
                eng.suppress_overdub_note(t_idx, c_idx, target, pitch)
        self._notify_ui("overdub", target)

    def _get_active_clip(self) -> Optional[Clip]:
        if 0 <= self.active_track_idx < len(self.engine.song.tracks):
            track = self.engine.song.tracks[self.active_track_idx]
            if 0 <= self.active_clip_idx < len(track.clips):
                return track.clips[self.active_clip_idx]
        return None
