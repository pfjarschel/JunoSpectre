"""Tests for sequencer data models and serialization."""

import pytest

from spectre.core.patch_state import PatchState
from spectre.core.spectre_format import (
    FORMAT_VERSION,
    load_performance,
    load_playlist,
    save_playlist,
    save_spectre,
)
from spectre.sequencer.models import (
    NUM_AUTOMATION_LANES,
    AutomationClip,
    AutomationLane,
    AutomationStep,
    Clip,
    NoteEvent,
    SequencerSong,
    Step,
    default_sequencer_song,
    default_tracks,
)


def test_note_event_roundtrip():
    n = NoteEvent(pitch=64, velocity=110)
    d = n.to_dict()
    assert d == {"pitch": 64, "velocity": 110, "length": 1}
    n2 = NoteEvent.from_dict(d)
    assert n2.pitch == 64
    assert n2.velocity == 110


def test_step_polyphony_and_roundtrip():
    step = Step(
        gate_length=0.5,
        micro_timing=-4,
        strum=2,
        probability=0.8,
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

    d = clip.to_dict()
    clip2 = Clip.from_dict(d)
    assert clip2.name == "Bassline"
    assert clip2.length == 16
    assert len(clip2.steps) == 16


def test_automation_lanes_roundtrip():
    song = default_sequencer_song()
    assert len(song.automation) == NUM_AUTOMATION_LANES
    lane = song.automation[2]
    lane.target = "tone.1.tvf_cutoff@3"
    lane.clock_divider = "1/8"
    clip = lane.clips[1]
    clip.set_length(12)
    clip.steps[0] = AutomationStep(value=0.25, glide=True)
    clip.steps[6] = AutomationStep(value=1.0)

    song2 = SequencerSong.from_dict(song.to_dict())
    lane2 = song2.automation[2]
    assert lane2.target == "tone.1.tvf_cutoff@3"
    assert lane2.clock_divider == "1/8"
    clip2 = lane2.clips[1]
    assert clip2.length == 12 and len(clip2.steps) == 12
    assert (clip2.steps[0].value, clip2.steps[0].glide) == (0.25, True)
    assert clip2.steps[6].value == 1.0
    assert clip2.steps[1].value is None and clip2.has_values
    assert not song2.automation[0].clips[0].has_values


def test_songs_without_automation_get_empty_lanes():
    d = default_sequencer_song().to_dict()
    del d["automation"]
    song = SequencerSong.from_dict(d)
    assert len(song.automation) == NUM_AUTOMATION_LANES
    assert all(lane.target == "" and len(lane.clips) == 8 for lane in song.automation)
    # Out-of-range values are clamped
    assert AutomationStep.from_dict({"value": 1.7}).value == 1.0
    assert AutomationClip.from_dict({"length": 500}).length == 128
    assert AutomationLane.from_dict({}).target == ""


def test_default_tracks_and_routing():
    tracks = default_tracks()
    assert len(tracks) == 16
    # Track N sends to part N; track 10 is the rhythm part
    assert [t.target_parts for t in tracks] == [[i] for i in range(1, 17)]
    assert [t.name for t in tracks] == [f"Track {i}" for i in range(1, 17)]
    assert [i for i, t in enumerate(tracks) if t.is_drum] == [9]


def test_songs_always_have_sixteen_tracks():
    short = default_sequencer_song().to_dict()
    short["tracks"] = short["tracks"][:5]
    short["tracks"][0]["name"] = "Bass"
    song = SequencerSong.from_dict(short)
    assert len(song.tracks) == 16
    assert song.tracks[0].name == "Bass"          # kept
    assert song.tracks[9].target_parts == [10]    # filled in with defaults
    assert song.tracks[15].target_parts == [16]


def test_sequencer_song_roundtrip():
    song = default_sequencer_song()
    song.bpm = 135.0
    song.master_resync_bars = 8
    song.tracks[0].clips[0].steps[0].notes.append(NoteEvent(72, 115))

    d = song.to_dict()
    song2 = SequencerSong.from_dict(d)
    assert song2.bpm == 135.0
    assert song2.master_resync_bars == 8
    assert len(song2.tracks) == 16
    assert song2.tracks[0].clips[0].steps[0].notes[0].pitch == 72


def test_performance_carries_sequence_roundtrip(tmp_path):
    ps = PatchState.from_template_file()
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
    save_spectre(f, PatchState.from_template_file(), kind="performance")
    assert load_performance(f)["sequencer_song"] is None
    with pytest.raises(ValueError):
        save_spectre(tmp_path / "s.spectre", PatchState.from_template_file(), kind="song")


def test_playlist_save_and_load_roundtrip(tmp_path):
    entries = [
        {"name": "Song 1", "song_path": "/path/1.spectre", "bpm": 120},
        {"name": "Song 2", "song_path": "/path/2.spectre", "bpm": 128},
    ]
    pl_file = tmp_path / "gig.spectre"
    save_playlist(pl_file, entries=entries, index=1, name="Friday Gig")

    loaded = load_playlist(pl_file)
    assert len(loaded["entries"]) == 2
    assert loaded["entries"][0]["name"] == "Song 1"
    assert loaded["index"] == 1
    assert loaded["meta"]["name"] == "Friday Gig"


def test_track_dice_roundtrip_and_clamping():
    from spectre.sequencer import Track
    t = Track(dice_timing=7, dice_velocity=15)
    t2 = Track.from_dict(t.to_dict())
    assert (t2.dice_timing, t2.dice_velocity) == (7, 15)
    t3 = Track.from_dict({"dice_timing": 99, "dice_velocity": -5})
    assert (t3.dice_timing, t3.dice_velocity) == (24, 0)
    # Songs saved before dice existed load with it off
    assert (Track.from_dict({}).dice_timing, Track.from_dict({}).dice_velocity) == (0, 0)


def test_old_step_ties_become_note_lengths():
    raw = {"length": 16, "steps": [
        {"notes": [{"pitch": 60, "velocity": 100}, {"pitch": 64, "velocity": 90}]},
        {"tie": True},
        {"tie": True, "notes": [{"pitch": 70, "velocity": 100}]},  # silent under a tie
        {"notes": [{"pitch": 62, "velocity": 100}]},
        {"tie": True},
    ]}
    clip = Clip.from_dict(raw)
    assert [n.length for n in clip.steps[0].notes] == [3, 3]
    assert clip.steps[2].notes == []
    assert [n.length for n in clip.steps[3].notes] == [2]
