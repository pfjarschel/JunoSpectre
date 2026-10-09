"""Tests for sequencer data models and serialization."""

import pytest

from src.spectre.core.patch_state import PatchState
from src.spectre.core.spectre_format import (
    FORMAT_VERSION,
    load_playlist,
    load_performance,
    save_playlist,
    save_spectre,
)
from src.spectre.sequencer.models import (
    Clip,
    MotionStep,
    NoteEvent,
    SequencerSong,
    Step,
    Track,
    default_sequencer_song,
    default_tracks,
)


def test_note_event_roundtrip():
    n = NoteEvent(pitch=64, velocity=110)
    d = n.to_dict()
    assert d == {"pitch": 64, "velocity": 110}
    n2 = NoteEvent.from_dict(d)
    assert n2.pitch == 64
    assert n2.velocity == 110


def test_step_polyphony_and_roundtrip():
    step = Step(
        gate_length=0.5,
        micro_timing=-4,
        strum=2,
        probability=0.8,
        tie=False,
        notes=[NoteEvent(60, 100), NoteEvent(64, 90), NoteEvent(67, 85)],
    )
    assert step.is_active is True
    d = step.to_dict()
    step2 = Step.from_dict(d)
    assert step2.gate_length == pytest.approx(0.5)
    assert step2.micro_timing == -4
    assert step2.strum == 2
    assert step2.probability == pytest.approx(0.8)
    assert len(step2.notes) == 3
    assert step2.notes[1].pitch == 64


def test_clip_resize_and_motion():
    clip = Clip(name="Bassline", length=8)
    assert len(clip.steps) == 8

    # Resize to 16
    clip.set_length(16)
    assert len(clip.steps) == 16
    assert clip.length == 16

    # Add motion
    clip.motion_tracks["filter_cutoff"] = [MotionStep(value=0.5, glide=True) for _ in range(16)]
    d = clip.to_dict()
    clip2 = Clip.from_dict(d)
    assert clip2.name == "Bassline"
    assert clip2.length == 16
    assert len(clip2.steps) == 16
    assert "filter_cutoff" in clip2.motion_tracks
    assert clip2.motion_tracks["filter_cutoff"][0].glide is True


def test_default_tracks_and_routing():
    tracks = default_tracks()
    assert len(tracks) == 8
    # Tracks 1-7 send to parts 1-7, Track 8 to the rhythm part
    assert [t.target_parts for t in tracks] == [[1], [2], [3], [4], [5], [6], [7], [10]]
    assert [t.name for t in tracks] == [f"Track {i}" for i in range(1, 9)]
    assert [t.is_drum for t in tracks] == [False] * 7 + [True]


def test_songs_always_have_eight_tracks():
    short = default_sequencer_song().to_dict()
    short["tracks"] = short["tracks"][:5]
    short["tracks"][0]["name"] = "Bass"
    song = SequencerSong.from_dict(short)
    assert len(song.tracks) == 8
    assert song.tracks[0].name == "Bass"          # kept
    assert song.tracks[7].target_parts == [10]    # filled in with defaults


def test_sequencer_song_roundtrip():
    song = default_sequencer_song()
    song.bpm = 135.0
    song.master_resync_bars = 8
    song.tracks[0].clips[0].steps[0].notes.append(NoteEvent(72, 115))

    d = song.to_dict()
    song2 = SequencerSong.from_dict(d)
    assert song2.bpm == 135.0
    assert song2.master_resync_bars == 8
    assert len(song2.tracks) == 8
    assert song2.tracks[0].clips[0].steps[0].notes[0].pitch == 72


def test_performance_carries_sequence_roundtrip(tmp_path):
    ps = PatchState.create_init_patch()
    ps.common.name = "MY SONG"
    song = default_sequencer_song()
    song.bpm = 128.0
    song.tracks[0].clips[0].steps[0].notes.append(NoteEvent(60, 100))

    song_file = tmp_path / "test_song.spectre"
    save_spectre(song_file, ps, meta={"name": "MY SONG", "tags": ["live"]},
                 spectre={"sequencer": song.to_dict(), "part_snapshots": {"2": {"x": 1}}},
                 kind="performance")

    loaded = load_performance(song_file)
    assert loaded["kind"] == "performance"
    assert loaded["format_version"] == FORMAT_VERSION
    assert loaded["meta"]["name"] == "MY SONG"
    assert loaded["sequencer_song"].bpm == 128.0
    assert loaded["sequencer_song"].tracks[0].clips[0].steps[0].notes[0].pitch == 60
    assert loaded["part_snapshots"] == {"2": {"x": 1}}


def test_performance_without_sequence_and_song_kind_gone(tmp_path):
    f = tmp_path / "perf.spectre"
    save_spectre(f, PatchState.create_init_patch(), kind="performance")
    assert load_performance(f)["sequencer_song"] is None
    with pytest.raises(ValueError):
        save_spectre(tmp_path / "s.spectre", PatchState.create_init_patch(), kind="song")


def test_playlist_save_and_load_roundtrip(tmp_path):
    entries = [
        {"name": "Song 1", "perf_path": "/path/1.spectre", "bpm": 120},
        {"name": "Song 2", "perf_path": "/path/2.spectre", "bpm": 128},
    ]
    pl_file = tmp_path / "gig.spectre"
    save_playlist(pl_file, entries=entries, index=1, name="Friday Gig")

    loaded = load_playlist(pl_file)
    assert len(loaded["entries"]) == 2
    assert loaded["entries"][0]["name"] == "Song 1"
    assert loaded["index"] == 1
    assert loaded["meta"]["name"] == "Friday Gig"


def test_track_dice_roundtrip_and_clamping():
    from src.spectre.sequencer import Track
    t = Track(dice_timing=7, dice_velocity=15)
    t2 = Track.from_dict(t.to_dict())
    assert (t2.dice_timing, t2.dice_velocity) == (7, 15)
    t3 = Track.from_dict({"dice_timing": 99, "dice_velocity": -5})
    assert (t3.dice_timing, t3.dice_velocity) == (24, 0)
    # Songs saved before dice existed load with it off
    assert (Track.from_dict({}).dice_timing, Track.from_dict({}).dice_velocity) == (0, 0)
