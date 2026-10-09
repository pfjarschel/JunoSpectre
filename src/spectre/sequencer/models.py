"""Data models for the Juno Spectre 8-track polymetric sequencer & clip launcher."""

from __future__ import annotations

import copy
import dataclasses
import uuid
from typing import Any, Dict, List, Optional

# Most notes one step can hold (fills the pad's 3 x 4 note grid)
MAX_STEP_NOTES = 12
NUM_TRACKS = 8
# Dice (humanize) ranges: timing in +/- clock ticks, velocity in +/- % of 127
MAX_DICE_TIMING = 24
MAX_DICE_VELOCITY = 50
# Performance part of the JUNO-DS rhythm set: tracks sending to it are drum tracks
DRUM_PART = 10
MAX_TRACK_NAME = 12


@dataclasses.dataclass
class NoteEvent:
    """A single note event within a sequencer step."""
    pitch: int = 60          # 0..127 MIDI note number
    velocity: int = 100      # 1..127 MIDI velocity

    def to_dict(self) -> Dict[str, Any]:
        return {"pitch": int(self.pitch), "velocity": int(self.velocity)}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> NoteEvent:
        return cls(
            pitch=max(0, min(127, int(d.get("pitch", 60)))),
            velocity=max(1, min(127, int(d.get("velocity", 100)))),
        )


@dataclasses.dataclass
class Step:
    """A single step in a pattern grid supporting timing, probability and chord notes."""
    gate_length: float = 0.75       # 0.01 .. 1.0 (fraction of step duration)
    micro_timing: int = 0           # -24 .. +24 clock ticks offset
    strum: int = 0                  # Strum / flam delay in ticks (<0 down, >0 up, 0 instant)
    probability: float = 1.0        # 0.0 .. 1.0 (trigger probability)
    tie: bool = False               # Sustain active notes without retriggering envelopes
    notes: List[NoteEvent] = dataclasses.field(default_factory=list)

    @property
    def is_active(self) -> bool:
        """True if the step has active note triggers or is tied."""
        return bool(self.notes or self.tie)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gate_length": float(self.gate_length),
            "micro_timing": int(self.micro_timing),
            "strum": int(self.strum),
            "probability": float(self.probability),
            "tie": bool(self.tie),
            "notes": [n.to_dict() for n in self.notes],
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> Step:
        notes_data = d.get("notes", [])
        notes = [NoteEvent.from_dict(n) for n in notes_data] if isinstance(notes_data, list) else []
        return cls(
            gate_length=max(0.01, min(1.0, float(d.get("gate_length", 0.75)))),
            micro_timing=max(-24, min(24, int(d.get("micro_timing", 0)))),
            strum=max(-24, min(24, int(d.get("strum", 0)))),
            probability=max(0.0, min(1.0, float(d.get("probability", 1.0)))),
            tie=bool(d.get("tie", False)),
            notes=sorted(notes[:MAX_STEP_NOTES], key=lambda n: n.pitch),
        )


@dataclasses.dataclass
class MotionStep:
    """Automation payload for a continuous parameter track."""
    value: float = 0.0              # 0.0 .. 1.0 normalized value
    glide: bool = False             # True if interpolating / slewing to next step

    def to_dict(self) -> Dict[str, Any]:
        return {"value": float(self.value), "glide": bool(self.glide)}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> MotionStep:
        return cls(
            value=max(0.0, min(1.0, float(d.get("value", 0.0)))),
            glide=bool(d.get("glide", False)),
        )


@dataclasses.dataclass
class Clip:
    """A pattern container with arbitrary step count for polymetric loops."""
    clip_id: str = dataclasses.field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Clip"
    length: int = 16                # Arbitrary step count (e.g. 3, 7, 16, 32, 64)
    steps: List[Step] = dataclasses.field(default_factory=list)
    motion_tracks: Dict[str, List[MotionStep]] = dataclasses.field(default_factory=dict)

    def __post_init__(self):
        # Guarantee steps list matches length
        if len(self.steps) < self.length:
            self.steps.extend(Step() for _ in range(self.length - len(self.steps)))
        elif len(self.steps) > self.length:
            self.steps = self.steps[:self.length]

    def set_length(self, new_length: int) -> None:
        """Resize clip length non-destructively."""
        new_len = max(1, min(128, int(new_length)))
        if new_len > len(self.steps):
            self.steps.extend(Step() for _ in range(new_len - len(self.steps)))
        elif new_len < len(self.steps):
            self.steps = self.steps[:new_len]
        self.length = new_len

    def to_dict(self) -> Dict[str, Any]:
        return {
            "clip_id": self.clip_id,
            "name": self.name,
            "length": self.length,
            "steps": [s.to_dict() for s in self.steps],
            "motion_tracks": {
                k: [ms.to_dict() for ms in v]
                for k, v in self.motion_tracks.items()
            },
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> Clip:
        length = max(1, min(128, int(d.get("length", 16))))
        steps_data = d.get("steps", [])
        steps = [Step.from_dict(s) for s in steps_data] if isinstance(steps_data, list) else []
        motion_raw = d.get("motion_tracks", {})
        motion_tracks: Dict[str, List[MotionStep]] = {}
        if isinstance(motion_raw, dict):
            for k, steps_list in motion_raw.items():
                if isinstance(steps_list, list):
                    motion_tracks[k] = [MotionStep.from_dict(ms) for ms in steps_list]

        return cls(
            clip_id=str(d.get("clip_id") or str(uuid.uuid4())[:8]),
            name=str(d.get("name", "Clip")),
            length=length,
            steps=steps,
            motion_tracks=motion_tracks,
        )


@dataclasses.dataclass
class Track:
    """One of the 5 fixed tracks in the performance sequencer."""
    track_id: int = 1                   # 1..NUM_TRACKS
    name: str = "Track"
    target_parts: List[int] = dataclasses.field(default_factory=lambda: [1])
    clock_divider: str = "1/16"         # "1/32", "1/16", "1/8", "1/4", "1/8T", "1/16T"
    swing: float = 0.50                 # 0.50 (neutral) .. 0.75 (max swing)
    dice_timing: int = 0                # 0..MAX_DICE_TIMING: random +/- ticks per note
    dice_velocity: int = 0              # 0..MAX_DICE_VELOCITY: random +/- % of 127 per note
    active_clip_idx: int = 0            # Current playing clip index (or -1 if stopped)
    queued_clip_idx: int = -1           # Staged clip for next measure (-1 if none)
    selected_clip_idx: int = 0          # Clip being edited; what Play starts from a stop
    clips: List[Clip] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        if not self.clips:
            self.clips = [Clip(name=f"Pattern {i+1}", length=16) for i in range(8)]
        self.selected_clip_idx = max(0, min(len(self.clips) - 1, int(self.selected_clip_idx)))

    @property
    def is_drum(self) -> bool:
        """True when the track's main part is the rhythm part (drum names, drum buttons)."""
        return bool(self.target_parts) and self.target_parts[0] == DRUM_PART

    def to_dict(self) -> Dict[str, Any]:
        return {
            "track_id": int(self.track_id),
            "name": self.name,
            "target_parts": list(self.target_parts),
            "clock_divider": self.clock_divider,
            "swing": float(self.swing),
            "dice_timing": int(self.dice_timing),
            "dice_velocity": int(self.dice_velocity),
            "active_clip_idx": int(self.active_clip_idx),
            "queued_clip_idx": int(self.queued_clip_idx),
            "selected_clip_idx": int(self.selected_clip_idx),
            "clips": [c.to_dict() for c in self.clips],
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> Track:
        clips_data = d.get("clips", [])
        clips = [Clip.from_dict(c) for c in clips_data] if isinstance(clips_data, list) else []
        return cls(
            track_id=max(1, min(NUM_TRACKS, int(d.get("track_id", 1)))),
            name=str(d.get("name", "Track"))[:MAX_TRACK_NAME],
            target_parts=[int(p) for p in d.get("target_parts", [1])] or [1],
            clock_divider=str(d.get("clock_divider", "1/16")),
            swing=max(0.50, min(0.75, float(d.get("swing", 0.50)))),
            dice_timing=max(0, min(MAX_DICE_TIMING, int(d.get("dice_timing", 0)))),
            dice_velocity=max(0, min(MAX_DICE_VELOCITY, int(d.get("dice_velocity", 0)))),
            active_clip_idx=int(d.get("active_clip_idx", 0)),
            queued_clip_idx=int(d.get("queued_clip_idx", -1)),
            # Older songs have no selection: start from the clip that was playing
            selected_clip_idx=max(0, int(d.get("selected_clip_idx", d.get("active_clip_idx", 0)))),
            clips=clips,
        )


@dataclasses.dataclass
class SequencerSong:
    """Complete 8-track sequencer state container."""
    bpm: float = 120.0
    master_resync_bars: int = 0         # Realign period: 0 = Off, 1, 2, 4, 8, 16, 32 bars
    tracks: List[Track] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        # Always NUM_TRACKS tracks: missing ones get their defaults, extras are dropped
        if len(self.tracks) != NUM_TRACKS:
            defaults = default_tracks()
            self.tracks = (list(self.tracks) + defaults[len(self.tracks):])[:NUM_TRACKS]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bpm": float(self.bpm),
            "master_resync_bars": int(self.master_resync_bars),
            "tracks": [t.to_dict() for t in self.tracks],
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> SequencerSong:
        if not isinstance(d, dict):
            return cls()
        tracks_data = d.get("tracks", [])
        tracks = [Track.from_dict(t) for t in tracks_data] if isinstance(tracks_data, list) else []

        return cls(
            bpm=max(20.0, min(300.0, float(d.get("bpm", 120.0)))),
            master_resync_bars=max(0, min(64, int(d.get("master_resync_bars", 0)))),
            tracks=tracks,
        )


def default_step() -> Step:
    """Build a default empty step."""
    return Step()


def default_clip(name: str = "Clip", length: int = 16) -> Clip:
    """Build a default clip initialized with empty steps."""
    return Clip(name=name, length=length)


def default_tracks() -> List[Track]:
    """Build the standard tracks: Tracks 1-7 send to Parts 1-7, Track 8 to the rhythm part."""
    tracks = []
    for i in range(NUM_TRACKS):
        t = Track(
            track_id=i + 1,
            name=f"Track {i + 1}",
            target_parts=[DRUM_PART] if i == NUM_TRACKS - 1 else [i + 1],
            clock_divider="1/16",
            swing=0.50,
            active_clip_idx=0,
            queued_clip_idx=-1,
            clips=[Clip(name=f"Scene {s+1}", length=16) for s in range(8)],
        )
        tracks.append(t)
    return tracks


def default_sequencer_song() -> SequencerSong:
    """Build a blank, ready-to-play SequencerSong container."""
    return SequencerSong(
        bpm=120.0,
        master_resync_bars=0,
        tracks=default_tracks(),
    )

