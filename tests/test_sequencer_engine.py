"""Tests for SequencerClock, SequencerEngine, and SequencerRecorder."""

import time
from unittest.mock import MagicMock

import mido
import pytest

from src.spectre.sequencer import (
    Clip,
    NoteEvent,
    SequencerClock,
    SequencerEngine,
    SequencerRecorder,
    Step,
    default_sequencer_song,
)


def test_clock_lifecycle_and_ticks():
    clock = SequencerClock(bpm=240.0)
    ticks = []

    def on_tick(tick, total):
        ticks.append((tick, total))

    clock.register_tick_callback(on_tick)
    clock.start()
    time.sleep(0.06)
    clock.stop()

    assert len(ticks) > 0
    assert clock.is_running is False


def test_engine_note_scheduling():
    song = default_sequencer_song()
    # Put a note on Track 1 Step 0
    clip = song.tracks[0].clips[0]
    clip.steps[0].notes.append(NoteEvent(pitch=60, velocity=100))
    clip.steps[0].gate_length = 0.5  # half duration

    mock_midi = MagicMock()
    mock_midi.juno_out.closed = False
    mock_midi.juno_out.send = MagicMock()

    clock = SequencerClock(bpm=120.0)
    engine = SequencerEngine(song=song, midi_mgr=mock_midi, clock=clock)

    # Simulate tick 0
    engine._on_clock_tick(tick_in_bar=0, total_ticks=0)

    # NoteOn should be sent for channel 0 (Part 1 - 1)
    calls = mock_midi.juno_out.send.call_args_list
    assert len(calls) == 1
    sent_msg = calls[0][0][0]
    assert sent_msg.type == "note_on"
    assert sent_msg.note == 60
    assert sent_msg.velocity == 100

    # Advance until gate length (24 * 0.5 = 12 ticks) expires
    for t in range(1, 13):
        engine._on_clock_tick(tick_in_bar=t, total_ticks=t)

    # NoteOff should now have been sent
    assert mock_midi.juno_out.send.call_count == 2
    sent_off = mock_midi.juno_out.send.call_args_list[1][0][0]
    assert sent_off.type == "note_off"
    assert sent_off.note == 60


def test_engine_launch_quantization():
    song = default_sequencer_song()
    engine = SequencerEngine(song=song)

    # Queue clip 2 on Track 0
    engine.launch_clip(0, 2)
    assert song.tracks[0].queued_clip_idx == 2
    assert song.tracks[0].active_clip_idx == 0

    # Ticking mid-bar does not switch clip
    engine._on_clock_tick(tick_in_bar=50, total_ticks=50)
    assert song.tracks[0].active_clip_idx == 0

    # Downbeat of master bar (tick_in_bar=0) switches clip
    engine._on_clock_tick(tick_in_bar=0, total_ticks=384)
    assert song.tracks[0].active_clip_idx == 2
    assert song.tracks[0].queued_clip_idx == -1


def test_engine_scene_launch():
    song = default_sequencer_song()
    engine = SequencerEngine(song=song)

    # Launch scene 3 across all tracks
    engine.launch_scene(3)
    for t in song.tracks:
        assert t.queued_clip_idx == 3

    # On next bar downbeat, all tracks switch to scene 3
    engine._on_clock_tick(tick_in_bar=0, total_ticks=384)
    for t in song.tracks:
        assert t.active_clip_idx == 3
        assert t.queued_clip_idx == -1


def test_recorder_step_entry():
    song = default_sequencer_song()
    engine = SequencerEngine(song=song)
    recorder = SequencerRecorder(engine)

    recorder.set_target(track_idx=0, clip_idx=0, step_idx=0)
    recorder.toggle_step_record(True)

    # Press note 60 and note 64 (chord)
    recorder.handle_midi_message(mido.Message("note_on", note=60, velocity=100))
    recorder.handle_midi_message(mido.Message("note_on", note=64, velocity=95))

    # Release note 60 (note 64 still held)
    recorder.handle_midi_message(mido.Message("note_off", note=60, velocity=0))
    # Step should not be committed yet
    clip = song.tracks[0].clips[0]
    assert len(clip.steps[0].notes) == 0

    # Release note 64 (all keys up) -> commit and advance
    recorder.handle_midi_message(mido.Message("note_off", note=64, velocity=0))

    assert len(clip.steps[0].notes) == 2
    assert {n.pitch for n in clip.steps[0].notes} == {60, 64}
    assert recorder.cursor_step == 1  # auto-advanced


def test_recorder_rest_and_tie():
    song = default_sequencer_song()
    engine = SequencerEngine(song=song)
    recorder = SequencerRecorder(engine)
    recorder.set_target(track_idx=0, clip_idx=0, step_idx=0)

    # Rest advances cursor
    recorder.record_rest()
    assert recorder.cursor_step == 1

    # Tie sets tie on step 1 and advances to 2
    recorder.record_tie()
    clip = song.tracks[0].clips[0]
    assert clip.steps[1].tie is True
    assert recorder.cursor_step == 2


# ---------------------------------------------------------------------------
# Note scheduling: ties, micro-timing, strum, swing, channels, overdub
# ---------------------------------------------------------------------------

def _engine_with_log(song=None, **kwargs):
    """Engine whose MIDI output records (total_tick, type, channel, note)."""
    song = song or default_sequencer_song()
    log = []
    state = {"tick": 0}
    out = MagicMock()
    out.closed = False
    out.send = lambda m: log.append((state["tick"], m.type, m.channel, m.note))
    midi = MagicMock()
    midi.juno_out = out
    engine = SequencerEngine(song=song, midi_mgr=midi, clock=SequencerClock(bpm=120.0), **kwargs)

    def run(n_ticks, start=0):
        for t in range(start, start + n_ticks):
            state["tick"] = t
            engine._on_clock_tick(tick_in_bar=t % 384, total_ticks=t)

    return engine, song, log, run


def test_tie_extends_note_without_retrigger():
    engine, song, log, run = _engine_with_log()
    clip = song.tracks[0].clips[0]
    clip.steps[0].notes = [NoteEvent(60, 100)]
    clip.steps[0].gate_length = 0.5
    clip.steps[1].tie = True
    clip.steps[2].tie = True
    clip.steps[2].gate_length = 0.5
    run(24 * 4)
    ons = [e for e in log if e[1] == "note_on" and e[3] == 60]
    offs = [e for e in log if e[1] == "note_off" and e[3] == 60]
    assert [e[0] for e in ons] == [0]
    # 2 full tied steps + half of the last one
    assert [e[0] for e in offs] == [24 * 2 + 12]


def test_notes_follow_part_receive_channel():
    engine, song, log, run = _engine_with_log(channel_resolver=lambda part: 9 if part == 2 else part - 1)
    song.tracks[0].target_parts = [2]
    song.tracks[0].clips[0].steps[0].notes = [NoteEvent(60, 100)]
    run(1)
    assert log[0][1:] == ("note_on", 9, 60)


def test_positive_micro_timing_and_strum_delay_notes():
    engine, song, log, run = _engine_with_log()
    step = song.tracks[0].clips[0].steps[0]
    step.notes = [NoteEvent(64, 100), NoteEvent(60, 100)]
    step.micro_timing = 4
    step.strum = 3  # low -> high
    run(12)
    ons = [(e[0], e[3]) for e in log if e[1] == "note_on"]
    assert ons == [(4, 60), (7, 64)]


def test_negative_micro_timing_plays_early_via_lookahead():
    engine, song, log, run = _engine_with_log()
    step = song.tracks[0].clips[0].steps[2]
    step.notes = [NoteEvent(62, 100)]
    step.micro_timing = -6
    run(24 * 3)
    ons = [e[0] for e in log if e[1] == "note_on" and e[3] == 62]
    assert ons == [48 - 6]


def test_track_swing_delays_odd_steps():
    engine, song, log, run = _engine_with_log()
    track = song.tracks[0]
    track.swing = 0.66
    for i in (0, 1):
        track.clips[0].steps[i].notes = [NoteEvent(60 + i, 100)]
    run(48)
    ons = {e[3]: e[0] for e in log if e[1] == "note_on"}
    assert ons[60] == 0
    assert ons[61] == 24 + round(0.16 * 2 * 24)


def test_retriggered_pitch_releases_previous_voice_first():
    engine, song, log, run = _engine_with_log()
    clip = song.tracks[0].clips[0]
    for i in (0, 1):
        clip.steps[i].notes = [NoteEvent(60, 100)]
        clip.steps[i].gate_length = 1.0
    run(30)
    seq = [(e[0], e[1]) for e in log if e[3] == 60]
    assert seq[:3] == [(0, "note_on"), (24, "note_off"), (24, "note_on")]


def test_live_overdub_snaps_to_nearest_step():
    engine, song, log, run = _engine_with_log()
    track = song.tracks[0]
    track.active_clip_idx = 2
    recorder = SequencerRecorder(engine)
    recorder.set_target(track_idx=0, clip_idx=2)
    recorder.toggle_live_record(True)
    engine.clock._running = True  # is_playing without a real clock thread

    run(24 + 20)  # ticks 0..43: 19 ticks into step 1, nearer to step 2
    recorder.handle_midi_message(mido.Message("note_on", note=67, velocity=90))
    clip = track.clips[2]
    assert [n.pitch for n in clip.steps[2].notes] == [67]
    assert clip.steps[2].micro_timing == -5

    # Not re-triggered on this pass (the player is already sounding it)...
    run(24 * 2, start=44)
    assert not [e for e in log if e[1] == "note_on" and e[3] == 67]
    # ...but plays (5 ticks early) on the next loop.
    run(24 * 16, start=92)
    ons = [e[0] for e in log if e[1] == "note_on" and e[3] == 67]
    assert ons == [16 * 24 + 48 - 5]


def test_live_overdub_launches_selected_clip_and_waits_for_it():
    engine, song, log, run = _engine_with_log()
    track = song.tracks[0]  # clip 0 playing
    recorder = SequencerRecorder(engine)
    recorder.set_target(track_idx=0, clip_idx=3)
    engine.clock._running = True
    run(10)

    # Arming overdub queues the selected clip for the next bar
    recorder.toggle_live_record(True)
    assert track.queued_clip_idx == 3
    assert recorder.live_record_waiting

    # Notes before the clip starts are not recorded anywhere
    recorder.handle_midi_message(mido.Message("note_on", note=60, velocity=90))
    assert not any(s.notes for c in track.clips for s in c.steps)

    run(384, start=10)  # crosses the bar line: clip 3 now plays
    assert track.active_clip_idx == 3
    assert not recorder.live_record_waiting
    recorder.handle_midi_message(mido.Message("note_on", note=62, velocity=90))
    assert [n.pitch for s in track.clips[3].steps for n in s.notes] == [62]


def test_selecting_another_clip_while_armed_launches_it():
    engine, song, log, run = _engine_with_log()
    recorder = SequencerRecorder(engine)
    recorder.set_target(track_idx=1, clip_idx=0)
    recorder.toggle_live_record(True)
    assert song.tracks[1].queued_clip_idx == -1  # already playing, nothing to do
    recorder.set_target(track_idx=1, clip_idx=5)
    assert song.tracks[1].queued_clip_idx == 5


def test_track_selected_clip_round_trip_and_legacy_default():
    from src.spectre.sequencer.models import Track

    t = Track(selected_clip_idx=5)
    assert Track.from_dict(t.to_dict()).selected_clip_idx == 5

    # Songs saved before per-track selection start on the clip that was playing
    legacy = t.to_dict()
    legacy.pop("selected_clip_idx")
    legacy["active_clip_idx"] = 3
    legacy["keybed_enabled"] = False  # old key is ignored
    assert Track.from_dict(legacy).selected_clip_idx == 3

    assert Track(selected_clip_idx=99).selected_clip_idx == 7
