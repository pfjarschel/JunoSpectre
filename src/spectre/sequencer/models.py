"""Data models for the Juno Spectre 16-track polymetric sequencer & clip launcher."""

from __future__ import annotations

import copy
import dataclasses
import uuid
from typing import Any, Dict, List, Optional

# Most notes one step can hold (fills the pad's 3 x 4 note grid)
MAX_STEP_NOTES = 12
# Longest clip, in steps (also the longest a note can be held)
MAX_CLIP_STEPS = 128
NUM_TRACKS = 16
# Tracks shown at once (live grid columns, sequencer tabs, context knobs)
TRACK_BANK_SIZE = 8
NUM_AUTOMATION_LANES = 8
# Dice (humanize) ranges: timing in +/- clock ticks, velocity in +/- % of 127
MAX_DICE_TIMING = 24
MAX_DICE_VELOCITY = 50
# Performance part of the JUNO-DS rhythm set: tracks sending to it are drum tracks
DRUM_PART = 10
MAX_TRACK_NAME = 12
# Track kinds: note steps sent to Juno parts, or audio files played by the audio worker
TRACK_KINDS = ("notes", "audio")
# Audio clip modes: LOOP repeats, ONE-SHOT plays once, FULL plays once and
# keeps playing through scene launches (a backing track)
AUDIO_MODES = ("loop", "oneshot", "full")
# Whether a mode starts on the bar by default (one-shots fire at once, like pads)
AUDIO_MODE_SYNC = {"loop": True, "oneshot": False, "full": True}
AUDIO_GAIN_RANGE = (-60.0, 6.0)         # dB


@dataclasses.dataclass
class AudioClip:
    """The audio side of a clip (used when its track is an AUDIO track).
    Frames are 44.1 kHz frames of the converted file."""
    file: str = ""                      # path inside the media folder ("" = empty slot)
    mode: str = "loop"
    sync: bool = True                   # start on the bar and stay locked; False = start at once
    start: int = 0                      # slice start frame (beat 1 for synced clips)
    end: int = 0                        # slice end frame, 0 = end of file
    gain_db: float = 0.0
    bars: int = 0                       # slice length in bars, 0 = from the length at the song BPM

    def to_dict(self) -> Dict[str, Any]:
        return {"file": self.file, "mode": self.mode, "sync": self.sync, "start": self.start,
                "end": self.end, "gain_db": self.gain_db, "bars": self.bars}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> AudioClip:
        mode = str(d.get("mode", "loop"))
        lo, hi = AUDIO_GAIN_RANGE
        return cls(
            file=str(d.get("file", "")),
            mode=mode if mode in AUDIO_MODES else "loop",
            sync=bool(d.get("sync", True)),
            start=max(0, int(d.get("start", 0))),
            end=max(0, int(d.get("end", 0))),
            gain_db=max(lo, min(hi, float(d.get("gain_db", 0.0)))),
            bars=max(0, min(1024, int(d.get("bars", 0)))),
        )


@dataclasses.dataclass
class NoteEvent:
    """A single note event within a sequencer step."""
    pitch: int = 60          # 0..127 MIDI note number
    velocity: int = 100      # 1..127 MIDI velocity
    length: int = 1          # Steps the note is held (1 = its own step); the step's gate cuts the last one

    def to_dict(self) -> Dict[str, Any]:
        return {"pitch": int(self.pitch), "velocity": int(self.velocity), "length": int(self.length)}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> NoteEvent:
        return cls(
            pitch=max(0, min(127, int(d.get("pitch", 60)))),
            velocity=max(1, min(127, int(d.get("velocity", 100)))),
            length=max(1, min(MAX_CLIP_STEPS, int(d.get("length", 1)))),
        )


@dataclasses.dataclass
class Step:
    """A single step in a pattern grid supporting timing, probability and chord notes."""
    gate_length: float = 0.75       # 0.01 .. 1.0 (fraction of step duration)
    micro_timing: int = 0           # -24 .. +24 clock ticks offset
    strum: int = 0                  # Strum / flam delay in ticks (<0 down, >0 up, 0 instant)
    probability: float = 1.0        # 0.0 .. 1.0 (trigger probability)
    notes: List[NoteEvent] = dataclasses.field(default_factory=list)

    @property
    def is_active(self) -> bool:
        """True if notes start on the step."""
        return bool(self.notes)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gate_length": float(self.gate_length),
            "micro_timing": int(self.micro_timing),
            "strum": int(self.strum),
            "probability": float(self.probability),
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
            notes=sorted(notes[:MAX_STEP_NOTES], key=lambda n: n.pitch),
        )


@dataclasses.dataclass
class Clip:
    """A pattern of steps (16, 32, 64 or 128 in the editor)."""
    clip_id: str = dataclasses.field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Clip"
    length: int = 16                # Step count, 1..MAX_CLIP_STEPS
    steps: List[Step] = dataclasses.field(default_factory=list)
    audio: Optional[AudioClip] = None   # what it plays on an AUDIO track (kept on NOTES ones)

    def __post_init__(self):
        # Guarantee steps list matches length
        if len(self.steps) < self.length:
            self.steps.extend(Step() for _ in range(self.length - len(self.steps)))
        elif len(self.steps) > self.length:
            self.steps = self.steps[:self.length]

    def set_length(self, new_length: int) -> None:
        """Resize clip length non-destructively."""
        new_len = max(1, min(MAX_CLIP_STEPS, int(new_length)))
        if new_len > len(self.steps):
            self.steps.extend(Step() for _ in range(new_len - len(self.steps)))
        elif new_len < len(self.steps):
            self.steps = self.steps[:new_len]
        self.length = new_len

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "clip_id": self.clip_id,
            "name": self.name,
            "length": self.length,
            "steps": [s.to_dict() for s in self.steps],
        }
        if self.audio is not None:
            d["audio"] = self.audio.to_dict()
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> Clip:
        length = max(1, min(MAX_CLIP_STEPS, int(d.get("length", 16))))
        steps_data = d.get("steps", [])
        steps_data = steps_data if isinstance(steps_data, list) else []
        steps = [Step.from_dict(s) for s in steps_data]
        _fold_step_ties(steps_data, steps)
        audio = d.get("audio")

        return cls(
            clip_id=str(d.get("clip_id") or str(uuid.uuid4())[:8]),
            name=str(d.get("name", "Clip")),
            length=length,
            steps=steps,
            audio=AudioClip.from_dict(audio) if isinstance(audio, dict) else None,
        )


def _fold_step_ties(steps_data: List[Any], steps: List[Step]) -> None:
    """Songs saved before per-note lengths tied whole steps: a step with "tie"
    held the notes of the last untied step through it (its own notes were
    silent). Turn that into note lengths."""
    anchor: Optional[Step] = None
    span = 0
    for raw, step in zip(steps_data, steps):
        if isinstance(raw, dict) and raw.get("tie"):
            step.notes.clear()
            if anchor is not None:
                span += 1
                for n in anchor.notes:
                    n.length = span
        else:
            anchor, span = (step, 1) if step.notes else (None, 0)


@dataclasses.dataclass
class Track:
    """One of the NUM_TRACKS fixed tracks in the performance sequencer."""
    track_id: int = 1                   # 1..NUM_TRACKS
    name: str = "Track"
    kind: str = "notes"                 # one of TRACK_KINDS
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
    def is_audio(self) -> bool:
        return self.kind == "audio"

    @property
    def is_drum(self) -> bool:
        """True when the track's main part is the rhythm part (drum names, drum buttons)."""
        return bool(self.target_parts) and self.target_parts[0] == DRUM_PART

    def to_dict(self) -> Dict[str, Any]:
        return {
            "track_id": int(self.track_id),
            "name": self.name,
            "kind": self.kind,
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
            kind=str(d.get("kind")) if d.get("kind") in TRACK_KINDS else "notes",
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
class AutomationStep:
    """One step of an automation clip."""
    value: Optional[float] = None   # 0..1 over the target's range; None = hold the last value
    glide: bool = False             # ramp from this value to the next set step's

    @property
    def is_set(self) -> bool:
        return self.value is not None

    def to_dict(self) -> Dict[str, Any]:
        return {"value": None if self.value is None else float(self.value), "glide": bool(self.glide)}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> AutomationStep:
        v = d.get("value") if isinstance(d, dict) else None
        return cls(
            value=None if v is None else max(0.0, min(1.0, float(v))),
            glide=bool(d.get("glide", False)) if isinstance(d, dict) else False,
        )


@dataclasses.dataclass
class AutomationClip:
    """A loop of automation steps (its own length, like a note clip)."""
    clip_id: str = dataclasses.field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Clip"
    length: int = 16
    steps: List[AutomationStep] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        self.set_length(self.length)

    def set_length(self, new_length: int) -> None:
        """Resize clip length non-destructively."""
        new_len = max(1, min(128, int(new_length)))
        if new_len > len(self.steps):
            self.steps.extend(AutomationStep() for _ in range(new_len - len(self.steps)))
        elif new_len < len(self.steps):
            self.steps = self.steps[:new_len]
        self.length = new_len

    @property
    def has_values(self) -> bool:
        return any(s.is_set for s in self.steps)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "clip_id": self.clip_id,
            "name": self.name,
            "length": self.length,
            "steps": [s.to_dict() for s in self.steps],
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> AutomationClip:
        steps_data = d.get("steps", [])
        steps = [AutomationStep.from_dict(s) for s in steps_data] if isinstance(steps_data, list) else []
        return cls(
            clip_id=str(d.get("clip_id") or str(uuid.uuid4())[:8]),
            name=str(d.get("name", "Clip")),
            length=max(1, min(128, int(d.get("length", 16)))),
            steps=steps,
        )


@dataclasses.dataclass
class AutomationLane:
    """An automation track: drives one parameter (a macro catalog key or
    "macro.N") independently of the note tracks. Its clips launch like note
    clips, or follow a note track's launches while linked to it."""
    target: str = ""                    # "" = unassigned
    # Performance parts a part-scoped target (common./tone./part.) acts on;
    # a linked lane uses its track's parts instead
    parts: List[int] = dataclasses.field(default_factory=lambda: [1])
    link_track: int = -1                # note track index it follows, -1 = none
    clock_divider: str = "1/16"
    active_clip_idx: int = 0
    queued_clip_idx: int = -1
    selected_clip_idx: int = 0
    clips: List[AutomationClip] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        if not self.clips:
            self.clips = [AutomationClip(name=f"Scene {i+1}") for i in range(8)]
        self.selected_clip_idx = max(0, min(len(self.clips) - 1, int(self.selected_clip_idx)))
        self.parts = sorted({max(1, min(16, int(p))) for p in self.parts}) or [1]

    @property
    def is_linked(self) -> bool:
        return 0 <= self.link_track < NUM_TRACKS

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target,
            "parts": list(self.parts),
            "link_track": int(self.link_track),
            "clock_divider": self.clock_divider,
            "active_clip_idx": int(self.active_clip_idx),
            "queued_clip_idx": int(self.queued_clip_idx),
            "selected_clip_idx": int(self.selected_clip_idx),
            "clips": [c.to_dict() for c in self.clips],
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> AutomationLane:
        clips_data = d.get("clips", [])
        clips = [AutomationClip.from_dict(c) for c in clips_data] if isinstance(clips_data, list) else []
        return cls(
            target=str(d.get("target", "") or ""),
            parts=[int(p) for p in d.get("parts", [1]) if isinstance(p, (int, float))] or [1],
            link_track=max(-1, min(NUM_TRACKS - 1, int(d.get("link_track", -1)))),
            clock_divider=str(d.get("clock_divider", "1/16")),
            active_clip_idx=int(d.get("active_clip_idx", 0)),
            queued_clip_idx=int(d.get("queued_clip_idx", -1)),
            selected_clip_idx=int(d.get("selected_clip_idx", 0)),
            clips=clips,
        )


@dataclasses.dataclass
class SequencerSong:
    """Complete sequencer state container (NUM_TRACKS tracks + automation lanes)."""
    bpm: float = 120.0
    master_resync_bars: int = 0         # Realign period: 0 = Off, 1, 2, 4, 8, 16, 32 bars
    tracks: List[Track] = dataclasses.field(default_factory=list)
    automation: List[AutomationLane] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        # Always NUM_TRACKS tracks: missing ones get their defaults, extras are dropped
        if len(self.tracks) != NUM_TRACKS:
            defaults = default_tracks()
            self.tracks = (list(self.tracks) + defaults[len(self.tracks):])[:NUM_TRACKS]
        # Lane N follows track N until told otherwise
        self.automation = (list(self.automation) + [
            AutomationLane(link_track=i % NUM_TRACKS)
            for i in range(len(self.automation), NUM_AUTOMATION_LANES)
        ])[:NUM_AUTOMATION_LANES]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bpm": float(self.bpm),
            "master_resync_bars": int(self.master_resync_bars),
            "tracks": [t.to_dict() for t in self.tracks],
            "automation": [a.to_dict() for a in self.automation],
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> SequencerSong:
        if not isinstance(d, dict):
            return cls()
        tracks_data = d.get("tracks", [])
        tracks = [Track.from_dict(t) for t in tracks_data] if isinstance(tracks_data, list) else []
        auto_data = d.get("automation", [])
        lanes = [AutomationLane.from_dict(a) for a in auto_data if isinstance(a, dict)] \
            if isinstance(auto_data, list) else []

        return cls(
            bpm=max(20.0, min(300.0, float(d.get("bpm", 120.0)))),
            master_resync_bars=max(0, min(64, int(d.get("master_resync_bars", 0)))),
            tracks=tracks,
            automation=lanes,
        )


def default_step() -> Step:
    """Build a default empty step."""
    return Step()


def default_clip(name: str = "Clip", length: int = 16) -> Clip:
    """Build a default clip initialized with empty steps."""
    return Clip(name=name, length=length)


def default_tracks() -> List[Track]:
    """Build the standard tracks: track N sends to part N (track 10 to the rhythm part)."""
    tracks = []
    for i in range(NUM_TRACKS):
        t = Track(
            track_id=i + 1,
            name=f"Track {i + 1}",
            target_parts=[i + 1],
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

