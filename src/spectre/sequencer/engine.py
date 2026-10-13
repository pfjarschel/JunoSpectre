"""Sequencer playback engine coordinating polymetric tracks, launch quantization, and MIDI output."""

from __future__ import annotations

import dataclasses
import logging
import random
import threading
import time
from typing import Callable, Dict, List, Optional, Set, Tuple

from ..core.midi import MidiDeviceManager
from . import automation as auto
from .clock import SequencerClock
from .models import (
    NUM_AUTOMATION_LANES,
    NUM_TRACKS,
    AutomationLane,
    Clip,
    NoteEvent,
    SequencerSong,
    Step,
    Track,
    default_sequencer_song,
)

logger = logging.getLogger(__name__)

# Ticks at 96 PPQN for metric dividers
DIVIDER_TICKS: Dict[str, int] = {
    "1/32": 12,
    "1/16": 24,
    "1/8": 48,
    "1/4": 96,
    "1/8T": 32,
    "1/16T": 16,
}


class SequencerEngine:
    """Core multi-track sequencer coordinating playback, quantization, and voice clearing."""

    def __init__(
        self,
        song: Optional[SequencerSong] = None,
        midi_mgr: Optional[MidiDeviceManager] = None,
        clock: Optional[SequencerClock] = None,
        channel_resolver: Optional[Callable[[int], int]] = None,
    ):
        self.song: SequencerSong = song or default_sequencer_song()
        self.midi: Optional[MidiDeviceManager] = midi_mgr
        self.clock: SequencerClock = clock or SequencerClock(bpm=self.song.bpm)
        # Maps a performance part (1..16) to its MIDI receive channel (0..15).
        # Without one, part N is assumed to listen on channel N.
        self.channel_resolver: Optional[Callable[[int], int]] = channel_resolver

        # Track runtime execution states
        self.track_steps: List[int] = [0] * NUM_TRACKS
        self._track_step_ticks: List[int] = [24] * NUM_TRACKS  # default 1/16
        self._track_tick_accum: List[int] = [24] * NUM_TRACKS
        self._track_step_started: List[bool] = [False] * NUM_TRACKS

        # Active sounding notes: list of (channel, pitch, note_off_tick)
        self._active_notes: List[Tuple[int, int, int]] = []
        # Scheduled note-ons: (fire_tick, channel, pitch, velocity, duration_ticks)
        self._pending_notes: List[Tuple[int, int, int, int, int]] = []
        # Per track: (clip_idx, step_idx, plays, notes) of the step whose early
        # (negative-offset) notes were already scheduled by the lookahead. The
        # notes keep their dice roll, so the rest of the step plays the same one.
        self._prescheduled: List[Optional[Tuple[int, int, bool, List[Tuple[NoteEvent, int]]]]] = [None] * NUM_TRACKS
        # (track, clip, step, pitch) just overdubbed ahead of the playhead;
        # skipped once so the live-played note isn't immediately doubled.
        self._overdub_suppress: Set[Tuple[int, int, int, int]] = set()
        self._lock = threading.Lock()

        # Automation lanes: tick their active clip's step 0 started on, the
        # level each one outputs (None = not driving its target), and when a
        # glide last sent. automation_listener() is called from the clock
        # thread whenever a level changes or a lane lets go.
        self._lane_anchor: List[int] = [0] * NUM_AUTOMATION_LANES
        # Tick each track's clip restarted on (linked lanes follow it)
        self._track_anchor: List[int] = [0] * NUM_TRACKS
        self.automation_levels: List[Optional[int]] = [None] * NUM_AUTOMATION_LANES
        self._lane_last_send: List[int] = [0] * NUM_AUTOMATION_LANES
        self._lane_segment: List[Optional[tuple]] = [None] * NUM_AUTOMATION_LANES
        self.lane_steps: List[int] = [0] * NUM_AUTOMATION_LANES
        self.automation_listener: Optional[Callable[[], None]] = None

        # UI updates downsampler (30-60 Hz)
        self._last_ui_dispatch: float = 0.0
        self._ui_subscribers: List[Callable[[dict], None]] = []

        # Connect clock tick
        self.clock.register_tick_callback(self._on_clock_tick)

    def subscribe_ui(self, callback: Callable[[dict], None]) -> None:
        if callback not in self._ui_subscribers:
            self._ui_subscribers.append(callback)

    def unsubscribe_ui(self, callback: Callable[[dict], None]) -> None:
        if callback in self._ui_subscribers:
            self._ui_subscribers.remove(callback)

    @property
    def is_playing(self) -> bool:
        return self.clock.is_running

    @property
    def bpm(self) -> float:
        return self.song.bpm

    def set_bpm(self, bpm: float) -> None:
        self.song.bpm = max(20.0, min(300.0, float(bpm)))
        self.clock.set_bpm(self.song.bpm)

    def play(self) -> None:
        """Start (or resume) the transport. From a full stop, every track
        starts on its selected clip, except tracks queued to stop."""
        if self.clock.is_stopped:
            with self._lock:
                for track in (*self.song.tracks, *self.song.automation):
                    if track.queued_clip_idx == -2:
                        track.active_clip_idx = -1
                    else:
                        track.active_clip_idx = track.selected_clip_idx
                    track.queued_clip_idx = -1
                self._lane_anchor = [0] * NUM_AUTOMATION_LANES
                self._track_anchor = [0] * NUM_TRACKS
                self._lane_segment = [None] * NUM_AUTOMATION_LANES
        self.clock.start()

    @property
    def lock(self) -> threading.Lock:
        """Lock guarding runtime state shared with the clock thread."""
        return self._lock

    def pause(self) -> None:
        self.clock.pause()
        with self._lock:
            self._silence_sounding_notes()

    def stop(self) -> None:
        self.clock.stop()
        with self._lock:
            self._silence_sounding_notes()
            self._prescheduled = [None] * len(self.song.tracks)
            self._overdub_suppress.clear()
            self.track_steps = [0] * NUM_TRACKS
            self._track_step_ticks = [DIVIDER_TICKS.get(t.clock_divider, 24) for t in self.song.tracks]
            self._track_tick_accum = list(self._track_step_ticks)
            self._track_step_started = [False] * NUM_TRACKS
            self.lane_steps = [0] * NUM_AUTOMATION_LANES
            released = any(v is not None for v in self.automation_levels)
            self.automation_levels = [None] * NUM_AUTOMATION_LANES
        if released:
            self._notify_automation()
        self._dispatch_ui(force=True)

    def launch_clip(self, track_idx: int, clip_idx: int) -> None:
        """Queue a specific clip on a track to launch on the next measure boundary."""
        if 0 <= track_idx < len(self.song.tracks):
            track = self.song.tracks[track_idx]
            if 0 <= clip_idx < len(track.clips):
                track.queued_clip_idx = clip_idx
                track.selected_clip_idx = clip_idx

    def launch_scene(self, scene_idx: int) -> None:
        """Queue every track and automation lane to the designated scene row."""
        for t in (*self.song.tracks, *self.song.automation):
            if 0 <= scene_idx < len(t.clips):
                t.queued_clip_idx = scene_idx
                t.selected_clip_idx = scene_idx

    def launch_lane_clip(self, lane_idx: int, clip_idx: int) -> None:
        """Queue an automation clip to launch on the next measure boundary."""
        if 0 <= lane_idx < len(self.song.automation):
            lane = self.song.automation[lane_idx]
            if 0 <= clip_idx < len(lane.clips):
                lane.queued_clip_idx = clip_idx
                lane.selected_clip_idx = clip_idx

    def stop_lane(self, lane_idx: int) -> None:
        """Queue an automation lane to stop (let go of its target) at the next bar."""
        if 0 <= lane_idx < len(self.song.automation):
            self.song.automation[lane_idx].queued_clip_idx = -2

    def stop_track(self, track_idx: int) -> None:
        """Queue a track to stop at the next measure boundary."""
        if 0 <= track_idx < len(self.song.tracks):
            self.song.tracks[track_idx].queued_clip_idx = -2  # -2 means queued stop

    def _on_clock_tick(self, tick_in_bar: int, total_ticks: int) -> None:
        """Executed on each PPQN pulse in the dedicated clock thread."""
        with self._lock:
            # 1. Process scheduled NoteOff events
            self._process_note_offs(total_ticks)

            # 2. Realign: every N bars all tracks restart from step 1 together
            is_bar_downbeat = (tick_in_bar == 0)
            if self.song.master_resync_bars > 0 and is_bar_downbeat:
                bar_ticks = self.clock.ppqn * 4 * self.song.master_resync_bars
                if total_ticks > 0 and total_ticks % bar_ticks == 0:
                    for i in range(len(self.song.tracks)):
                        self.track_steps[i] = 0
                        self._track_anchor[i] = total_ticks
                        self._track_tick_accum[i] = self._track_step_ticks[i]
                        self._track_step_started[i] = False

            # 3. Polymetric track step advancement
            for t_idx, track in enumerate(self.song.tracks):
                step_len_ticks = DIVIDER_TICKS.get(track.clock_divider, 24)
                self._track_step_ticks[t_idx] = step_len_ticks
                self._track_tick_accum[t_idx] += 1

                # Check launch quantization on master bar downbeat
                if is_bar_downbeat and track.queued_clip_idx != -1:
                    if track.queued_clip_idx == -2:
                        track.active_clip_idx = -1
                    else:
                        track.active_clip_idx = track.queued_clip_idx
                    track.queued_clip_idx = -1
                    self.track_steps[t_idx] = 0
                    self._track_anchor[t_idx] = total_ticks
                    self._track_tick_accum[t_idx] = step_len_ticks
                    self._track_step_started[t_idx] = False

                # If step duration elapsed, advance and trigger notes
                if self._track_tick_accum[t_idx] >= step_len_ticks:
                    self._track_tick_accum[t_idx] = 0
                    if track.active_clip_idx >= 0 and track.active_clip_idx < len(track.clips):
                        active_clip = track.clips[track.active_clip_idx]
                        if active_clip.length > 0:
                            # Advance playhead to next step only after previous step completed
                            if self._track_step_started[t_idx]:
                                self.track_steps[t_idx] = (self.track_steps[t_idx] + 1) % active_clip.length
                            else:
                                self._track_step_started[t_idx] = True
                            # Trigger current active step
                            self._trigger_step(
                                t_idx, track, track.active_clip_idx, active_clip,
                                self.track_steps[t_idx], total_ticks, tick_in_bar, step_len_ticks,
                            )

            # 4. Fire note-ons whose (swung / micro-timed / strummed) time has come
            self._fire_pending_notes(total_ticks)

            # 5. Automation lanes
            changed = self._run_automation(tick_in_bar, total_ticks)

        if changed:
            self._notify_automation()
        # 6. Dispatch UI status at 30-60 Hz
        self._dispatch_ui()

    # -- automation ------------------------------------------------------------

    def _tick_s(self) -> float:
        return 60.0 / (self.clock.bpm * self.clock.ppqn)

    def lane_driver(self, lane_idx: int):
        """What decides a lane's clip launches: its linked track, or itself."""
        lane = self.song.automation[lane_idx]
        if lane.is_linked and lane.link_track < len(self.song.tracks):
            return self.song.tracks[lane.link_track]
        return lane

    def _lane_anchor_at(self, lane_idx: int, lane: AutomationLane, tick_in_bar: int,
                        total_ticks: int, tick: int) -> Tuple[int, int]:
        """(clip_idx, anchor) lane `lane_idx` plays at `tick` (>= total_ticks),
        applying a launch, stop or realign that the next bar line brings."""
        driver = self.lane_driver(lane_idx)
        linked = driver is not lane
        clip_idx = driver.active_clip_idx
        anchor = self._track_anchor[lane.link_track] if linked else self._lane_anchor[lane_idx]
        bar = self.clock.ppqn * 4
        downbeat = total_ticks + (bar - tick_in_bar) % bar
        if downbeat <= tick:
            if driver.queued_clip_idx != -1:
                clip_idx = -1 if driver.queued_clip_idx == -2 else driver.queued_clip_idx
                anchor = downbeat
            elif self.song.master_resync_bars > 0 and downbeat > 0 \
                    and downbeat % (bar * self.song.master_resync_bars) == 0:
                anchor = downbeat
        return clip_idx, anchor

    def _run_automation(self, tick_in_bar: int, total_ticks: int) -> bool:
        """Advance the lanes (call under lock). True when a level changed."""
        tick_s = self._tick_s()
        ahead = total_ticks + int(round(auto.LOOKAHEAD_S / tick_s))
        cap = auto.seconds_to_ticks(auto.GLIDE_MIN_INTERVAL_S, tick_s)
        bar = self.clock.ppqn * 4
        resync = (self.song.master_resync_bars > 0 and tick_in_bar == 0 and total_ticks > 0
                  and total_ticks % (bar * self.song.master_resync_bars) == 0)
        changed = False
        for i, lane in enumerate(self.song.automation):
            # The bar line itself: launches and realigns take effect
            # (a linked lane's track already did this in step 3)
            if not lane.is_linked:
                if tick_in_bar == 0 and lane.queued_clip_idx != -1:
                    lane.active_clip_idx = -1 if lane.queued_clip_idx == -2 else lane.queued_clip_idx
                    lane.queued_clip_idx = -1
                    self._lane_anchor[i] = total_ticks
                    self._lane_segment[i] = None
                elif resync:
                    self._lane_anchor[i] = total_ticks
            level, mid_glide, step = self._lane_level(i, lane, tick_in_bar, total_ticks, ahead)
            self.lane_steps[i] = step
            if level == self.automation_levels[i]:
                continue
            # Mid-glide sends are rate capped; a lane taking its target sends at once
            if mid_glide and self.automation_levels[i] is not None \
                    and ahead - self._lane_last_send[i] < cap:
                continue
            self.automation_levels[i] = level
            self._lane_last_send[i] = ahead
            changed = True
        return changed

    def _lane_level(self, i: int, lane: AutomationLane, tick_in_bar: int,
                    total_ticks: int, tick: int) -> Tuple[Optional[int], bool, int]:
        """(level, mid_glide, step) of lane i at `tick`."""
        if not lane.target:
            return None, False, 0
        clip_idx, anchor = self._lane_anchor_at(i, lane, tick_in_bar, total_ticks, tick)
        if not 0 <= clip_idx < len(lane.clips):
            return None, False, 0
        clip = lane.clips[clip_idx]
        step_ticks = DIVIDER_TICKS.get(lane.clock_divider, 24)
        pos = max(0, tick - anchor) % (clip.length * step_ticks)
        step, in_step = divmod(pos, step_ticks)
        # Segments are found once per step (edits apply from the next step)
        key = (clip_idx, step, step_ticks, clip.length)
        cached = self._lane_segment[i]
        if cached is None or cached[0] != key:
            cached = (key, auto.segment_at(clip, step, step_ticks))
            self._lane_segment[i] = cached
        seg = cached[1]
        if seg is None:
            return None, False, step
        level, mid = auto.level_in_segment(seg, clip.length, step, in_step, step_ticks)
        return level, mid, step

    def _notify_automation(self) -> None:
        cb = self.automation_listener
        if cb is not None:
            try:
                cb()
            except Exception as e:
                logger.debug(f"automation listener failed: {e}")

    def automation_load(self, writes_per_change: Callable[[int], int]) -> List[float]:
        """Estimated SysEx writes/s per lane: what plays now, or what would
        play from a stop. writes_per_change(lane_idx) = DT1s per value change."""
        tick_s = self._tick_s()
        playing = not self.clock.is_stopped
        out = []
        for i, lane in enumerate(self.song.automation):
            driver = self.lane_driver(i)
            if playing:
                idx = driver.active_clip_idx
            else:
                idx = -1 if driver.queued_clip_idx == -2 else driver.selected_clip_idx
            if not lane.target or not 0 <= idx < len(lane.clips):
                out.append(0.0)
                continue
            step_ticks = DIVIDER_TICKS.get(lane.clock_divider, 24)
            rate = auto.clip_writes_per_second(lane.clips[idx], step_ticks, tick_s)
            out.append(rate * max(0, int(writes_per_change(i))))
        return out

    def _trigger_step(
        self,
        t_idx: int,
        track: Track,
        clip_idx: int,
        clip: Clip,
        step_idx: int,
        total_ticks: int,
        tick_in_bar: int,
        step_len_ticks: int,
    ) -> None:
        """Schedule the notes of the step starting now, plus the early notes of the next one."""
        if step_idx >= len(clip.steps):
            return
        step = clip.steps[step_idx]
        channels = self._channels_for(t_idx, track)

        suppressed = {k[3] for k in self._overdub_suppress if k[:3] == (t_idx, clip_idx, step_idx)}
        self._overdub_suppress -= {(t_idx, clip_idx, step_idx, p) for p in suppressed}

        pre = self._prescheduled[t_idx] if t_idx < len(self._prescheduled) else None
        early_done = pre is not None and pre[0] == clip_idx and pre[1] == step_idx
        plays = pre[2] if early_done else self._roll(step)
        if plays and step.notes:
            timed = pre[3] if early_done else self._note_offsets(track, step, step_idx, step_len_ticks)
            for note, offset in timed:
                if note.pitch in suppressed or (offset < 0 and early_done):
                    continue
                # Negative offsets not pre-scheduled (first step after start/launch) play on time.
                duration = self._note_duration(clip, step_idx, note, step_len_ticks)
                self._schedule_note(total_ticks + max(0, offset), channels, note, duration)

        # Lookahead: notes of the next step that sit *before* its grid position must be
        # scheduled now. Skipped when a clip change/stop lands on the next boundary.
        self._prescheduled[t_idx] = None
        next_boundary_is_bar = (tick_in_bar + step_len_ticks) % (self.clock.ppqn * 4) == 0
        if next_boundary_is_bar and track.queued_clip_idx != -1:
            return
        next_idx = (step_idx + 1) % max(1, clip.length)
        if next_idx >= len(clip.steps):
            return
        next_step = clip.steps[next_idx]
        next_plays = self._roll(next_step)
        next_timed = self._note_offsets(track, next_step, next_idx, step_len_ticks)
        self._prescheduled[t_idx] = (clip_idx, next_idx, next_plays, next_timed)
        if next_plays and next_step.notes:
            for note, offset in next_timed:
                if offset < 0:
                    duration = self._note_duration(clip, next_idx, note, step_len_ticks)
                    self._schedule_note(total_ticks + step_len_ticks + offset, channels, note, duration)

    @staticmethod
    def _roll(step: Step) -> bool:
        """Decide (once per pass) whether a step fires, honouring its probability."""
        return step.probability >= 1.0 or random.random() <= step.probability

    def _channels_for(self, t_idx: int, track: Track) -> List[int]:
        """MIDI channels (0..15) of the performance parts a track drives."""
        channels: List[int] = []
        for part in track.target_parts or [t_idx + 1]:
            ch = part - 1
            if self.channel_resolver is not None:
                try:
                    ch = int(self.channel_resolver(part))
                except Exception as e:
                    logger.debug(f"channel_resolver failed for part {part}: {e}")
            ch = max(0, min(15, ch))
            if ch not in channels:
                channels.append(ch)
        return channels

    @staticmethod
    def swing_delay(track: Track, step_idx: int, step_len_ticks: int) -> int:
        """Delay in ticks applied to off-beat (odd) steps by the track's swing (0.50 = straight)."""
        if step_idx % 2 == 0 or track.clock_divider.endswith("T"):
            return 0
        swing = max(0.50, min(0.75, float(track.swing)))
        return int(round((swing - 0.50) * 2.0 * step_len_ticks))

    def _note_offsets(
        self, track: Track, step: Step, step_idx: int, step_len_ticks: int
    ) -> List[Tuple[NoteEvent, int]]:
        """Per-note start offset (ticks from the step's grid position): swing + micro + strum,
        plus the track's dice, which also nudges each note's velocity (rolled per note)."""
        base = self.swing_delay(track, step_idx, step_len_ticks) + int(step.micro_timing)
        # Strum > 0 rolls low->high, < 0 high->low
        notes = sorted(step.notes, key=lambda n: n.pitch, reverse=step.strum < 0)
        spread = abs(int(step.strum))
        lo, hi = -(step_len_ticks - 1), 2 * step_len_ticks
        out: List[Tuple[NoteEvent, int]] = []
        for i, n in enumerate(notes):
            offset = base + i * spread + self._dice(track.dice_timing)
            if track.dice_velocity > 0:
                vel = n.velocity + self._dice(track.dice_velocity * 127 / 100)
                n = dataclasses.replace(n, velocity=max(1, min(127, vel)))
            out.append((n, max(lo, min(hi, offset))))
        return out

    @staticmethod
    def _dice(amount: float) -> int:
        """Random integer in [-amount, +amount], weighted toward 0 like a human player."""
        if amount <= 0:
            return 0
        return int(round(random.triangular(-amount, amount, 0.0)))

    @staticmethod
    def _note_duration(clip: Clip, step_idx: int, note: NoteEvent, step_len_ticks: int) -> int:
        """Gate length in ticks: the steps the note is held (cut at the clip end),
        the last one shortened by its starting step's gate."""
        held = max(1, min(int(note.length), clip.length - step_idx))
        gate = clip.steps[step_idx].gate_length
        return max(1, (held - 1) * step_len_ticks + int(gate * step_len_ticks))

    def _schedule_note(self, fire_tick: int, channels: List[int], note: NoteEvent, duration: int) -> None:
        for ch in channels:
            self._pending_notes.append((fire_tick, ch, note.pitch, note.velocity, duration))

    def _fire_pending_notes(self, current_total_ticks: int) -> None:
        """Send note-ons that are due; a re-struck pitch first releases its previous voice."""
        if not self._pending_notes:
            return
        due = [e for e in self._pending_notes if e[0] <= current_total_ticks]
        if not due:
            return
        self._pending_notes = [e for e in self._pending_notes if e[0] > current_total_ticks]
        for _, ch, pitch, vel, duration in due:
            still: List[Tuple[int, int, int]] = []
            for a_ch, a_pitch, a_off in self._active_notes:
                if a_ch == ch and a_pitch == pitch:
                    self._send_note_off(ch, pitch)
                else:
                    still.append((a_ch, a_pitch, a_off))
            self._active_notes = still
            self._send_note_on(ch, pitch, vel)
            self._active_notes.append((ch, pitch, current_total_ticks + duration))

    def suppress_overdub_note(self, t_idx: int, clip_idx: int, step_idx: int, pitch: int) -> None:
        """Skip one playback of a note just overdubbed onto an upcoming step (call under lock)."""
        self._overdub_suppress.add((t_idx, clip_idx, step_idx, pitch))

    def _process_note_offs(self, current_total_ticks: int) -> None:
        """Send NoteOff for notes whose gate length has expired."""
        remaining: List[Tuple[int, int, int]] = []
        for ch, pitch, off_tick in self._active_notes:
            if current_total_ticks >= off_tick:
                self._send_note_off(ch, pitch)
            else:
                remaining.append((ch, pitch, off_tick))
        self._active_notes = remaining

    def _silence_sounding_notes(self) -> None:
        """Send immediate NoteOff for all currently active notes."""
        for ch, pitch, _ in self._active_notes:
            self._send_note_off(ch, pitch)
        self._active_notes.clear()
        self._pending_notes.clear()

    def _send_note_on(self, channel: int, pitch: int, velocity: int) -> None:
        if self.midi and self.midi.juno_out and not getattr(self.midi.juno_out, "closed", False):
            import mido
            try:
                self.midi.juno_out.send(
                    mido.Message("note_on", channel=channel, note=pitch, velocity=velocity)
                )
            except Exception as e:
                logger.debug(f"Error sending note_on: {e}")

    def _send_note_off(self, channel: int, pitch: int) -> None:
        if self.midi and self.midi.juno_out and not getattr(self.midi.juno_out, "closed", False):
            import mido
            try:
                self.midi.juno_out.send(
                    mido.Message("note_off", channel=channel, note=pitch, velocity=0)
                )
            except Exception as e:
                logger.debug(f"Error sending note_off: {e}")

    def _dispatch_ui(self, force: bool = False) -> None:
        """Downsample UI notifications to ~40 Hz (25 ms) to keep the UI smooth and clock jitter-free."""
        now = time.perf_counter()
        if not force and (now - self._last_ui_dispatch < 0.025):
            return
        self._last_ui_dispatch = now

        snapshot = {
            "is_playing": self.is_playing,
            "playheads": list(self.track_steps),
            "bpm": self.song.bpm,
            "active_clips": [t.active_clip_idx for t in self.song.tracks],
            "queued_clips": [t.queued_clip_idx for t in self.song.tracks],
            "lane_steps": list(self.lane_steps),
            "lane_active_clips": [a.active_clip_idx for a in self.song.automation],
            "lane_queued_clips": [a.queued_clip_idx for a in self.song.automation],
        }

        for sub in list(self._ui_subscribers):
            try:
                sub(snapshot)
            except Exception as e:
                logger.debug(f"Error in sequencer UI dispatch: {e}")
