"""Tests for SequencerBridgeMixin and SetlistBridgeMixin in SpectreBridge."""

from unittest.mock import MagicMock
import pytest

from src.spectre.ui.bridge import SpectreBridge
from src.spectre.vector.engine import VectorEngine


class DummyJuno:
    def __init__(self):
        self.midi = MagicMock()
        self.midi.juno_out.closed = False
        self.midi.is_juno_connected = True
        self.set_sound_mode = MagicMock()
        self.set_perf_part_patch = MagicMock()
        self.set_perf_part_level = MagicMock()
        self.set_perf_part_pan = MagicMock()
        self.set_perf_part_mute = MagicMock()
        self.set_perf_zone = MagicMock()
        self.set_perf_zone_switch = MagicMock()


@pytest.fixture
def bridge():
    engine = VectorEngine()
    engine.juno = DummyJuno()
    return SpectreBridge(engine)


def test_sequencer_transport_properties_and_slots(bridge):
    assert bridge.seqIsPlaying is False
    assert bridge.bpm == 120.0

    # One global tempo: sequencer clock and vector motion follow it
    bridge.setBpm(132.0)
    assert bridge.bpm == 132.0
    assert bridge.sequencer.clock.bpm == 132.0
    assert bridge.engine.motion.bpm == 132.0

    bridge.seqPlay()
    assert bridge.seqIsPlaying is True

    bridge.seqPause()
    assert bridge.seqIsPlaying is False

    bridge.seqPlay()
    assert bridge.seqIsPlaying is True
    bridge.seqStop()
    assert bridge.seqIsPlaying is False


def test_sequencer_tracks_and_step_editing(bridge):
    tracks = bridge.seqTracks
    assert len(tracks) == 5
    assert tracks[0]["name"] == "Track 1 (Lead)"
    assert tracks[4]["name"] == "Track 5 (Drums)"

    bridge.seqSelectTrack(1)
    assert bridge.seqActiveTrack == 1

    bridge.seqSelectClip(0)
    assert bridge.seqActiveClip == 0

    # Toggle note 60 on step 0
    bridge.seqToggleStepNote(0, 60, 110)
    steps = bridge.seqActiveClipSteps
    assert steps[0]["isActive"] is True
    assert steps[0]["noteCount"] == 1
    assert steps[0]["primaryPitch"] == 60

    # Toggle note 60 again (removes it)
    bridge.seqToggleStepNote(0, 60, 110)
    steps_after = bridge.seqActiveClipSteps
    assert steps_after[0]["isActive"] is False
    assert steps_after[0]["noteCount"] == 0

    # Test step params
    bridge.seqSetStepParam(0, "gateLength", 0.5)
    bridge.seqSetStepParam(0, "microTiming", -10)
    bridge.seqSetStepParam(0, "probability", 0.75)
    bridge.seqSetStepParam(0, "tie", True)

    steps_updated = bridge.seqActiveClipSteps
    assert steps_updated[0]["gateLength"] == pytest.approx(0.5)
    assert steps_updated[0]["microTiming"] == -10
    assert steps_updated[0]["probability"] == pytest.approx(0.75)
    assert steps_updated[0]["tie"] is True


def test_sequencer_clip_and_scene_launching(bridge):
    # Launch clip 3 on track 0
    bridge.seqLaunchClip(0, 3)
    assert bridge.seqTracks[0]["queuedClipIdx"] == 3

    # Launch scene 2 across all tracks
    bridge.seqLaunchScene(2)
    for t in bridge.seqTracks:
        assert t["queuedClipIdx"] == 2

    # Stop track 1
    bridge.seqStopTrack(1)
    assert bridge.seqTracks[1]["queuedClipIdx"] == -2


def test_setlist_crud_and_safe_transition(bridge, tmp_path):
    bridge.newSetlist()
    assert bridge.setlistCount == 0

    # Add current song
    assert bridge.addCurrentToSetlist("Song Alpha") is True
    assert bridge.addCurrentToSetlist("Song Beta") is True
    assert bridge.setlistCount == 2
    assert bridge.setlistEntries[0]["name"] == "Song Alpha"
    assert bridge.setlistEntries[1]["name"] == "Song Beta"

    # Reorder
    bridge.reorderSetlistEntry(0, 1)
    assert bridge.setlistEntries[0]["name"] == "Song Beta"
    assert bridge.setlistEntries[1]["name"] == "Song Alpha"

    # Save setlist
    pl_path = tmp_path / "gig.spectre"
    assert bridge.saveSetlist(str(pl_path)) is True

    # Activate song (Safe Transition Protocol)
    bridge.seqPlay()
    assert bridge.seqIsPlaying is True

    assert bridge.activateSong(0) is True
    # Transport must be stopped after song transition
    assert bridge.seqIsPlaying is False
    # Panic CC 123 + CC 121 sent
    assert bridge.engine.juno.midi.send_all_notes_off.called is True

    # Load setlist back
    bridge.newSetlist()
    assert bridge.setlistCount == 0
    assert bridge.loadSetlist(str(pl_path)) is True
    assert bridge.setlistCount == 2


def test_sequencer_recording_and_track_controls(bridge):
    # Track clock divider and swing
    bridge.seqSetTrackClockDivider(0, "1/8")
    assert bridge.seqTracks[0]["clockDivider"] == "1/8"

    bridge.seqSetTrackSwing(0, 0.5)
    assert bridge.seqTracks[0]["swing"] == pytest.approx(0.5)

    # Step params: velocity & pitch
    bridge.seqSelectTrack(0)
    bridge.seqSelectClip(0)
    bridge.seqSetStepParam(2, "velocity", 115)
    bridge.seqSetStepParam(2, "pitch", 67)
    steps = bridge.seqActiveClipSteps
    assert steps[2]["isActive"] is True
    assert steps[2]["primaryVelocity"] == 115
    assert steps[2]["primaryPitch"] == 67

    # Clear step
    bridge.seqClearStep(2)
    assert bridge.seqActiveClipSteps[2]["isActive"] is False

    # Clip length
    bridge.seqSetClipLength(32)
    assert len(bridge.seqActiveClipSteps) == 32

    # Step recording toggles and cursor
    bridge.seqToggleStepRecord(True)
    assert bridge.seqStepRecordEnabled is True
    bridge.seqSetCursorStep(5)
    assert bridge.seqCursorStep == 5

    bridge.seqRecordRest()
    assert bridge.seqCursorStep == 6

    bridge.seqRecordTie()
    assert bridge.seqCursorStep == 7

    bridge.seqToggleStepRecord(False)
    assert bridge.seqStepRecordEnabled is False

    # Live recording toggle
    bridge.seqToggleLiveRecord(True)
    assert bridge.seqLiveRecordEnabled is True
    bridge.seqToggleLiveRecord(False)
    assert bridge.seqLiveRecordEnabled is False


def test_sequencer_operational_fixes(bridge):
    import mido

    # 1. Bulk Clear
    bridge.seqSelectTrack(0)
    bridge.seqSelectClip(0)
    bridge.seqToggleStepNote(0, 60, 100)
    bridge.seqToggleStepNote(1, 64, 100)
    assert bridge.seqActiveClipSteps[0]["isActive"] is True
    assert bridge.seqActiveClipSteps[1]["isActive"] is True

    bridge.seqClearActiveClip()
    assert bridge.seqActiveClipSteps[0]["isActive"] is False
    assert bridge.seqActiveClipSteps[1]["isActive"] is False

    # 2. Pitch Set and Nudge
    bridge.seqSetStepPitch(3, 72)
    assert bridge.seqActiveClipSteps[3]["isActive"] is True
    assert bridge.seqActiveClipSteps[3]["primaryPitch"] == 72

    bridge.seqNudgeStepPitch(3, 1)  # +1 semitone -> 73
    assert bridge.seqActiveClipSteps[3]["primaryPitch"] == 73

    bridge.seqNudgeStepPitch(3, -12)  # -1 octave -> 61
    assert bridge.seqActiveClipSteps[3]["primaryPitch"] == 61

    # Clamping test
    bridge.seqSetStepPitch(3, 150)
    assert bridge.seqActiveClipSteps[3]["primaryPitch"] == 127
    bridge.seqNudgeStepPitch(3, -200)
    assert bridge.seqActiveClipSteps[3]["primaryPitch"] == 0

    # 3. Track target part
    bridge.seqSetTrackTargetPart(0, 5)
    assert bridge.seqTracks[0]["targetPart"] == 5
    assert bridge.seqTracks[0]["targetParts"] == [5]

    # 4. Recorder UI notifications & MIDI Audition
    events = []
    bridge.recorder.subscribe_ui(lambda ev, data: events.append((ev, data)))

    # Audition only edits the cursor step while the step editor is on screen
    bridge.setActiveView("PATCH EDIT")
    bridge.recorder.cursor_step = 4
    bridge.recorder.handle_midi_message(mido.Message("note_on", note=65, velocity=90))
    assert bridge.seqActiveClipSteps[4]["isActive"] is False
    assert not any(ev == "pitch_set" for ev, _ in events)

    bridge.setActiveView("SEQUENCER")
    bridge.recorder.handle_midi_message(mido.Message("note_on", note=65, velocity=90))
    assert ("pitch_set", 65) in events
    assert bridge.seqActiveClipSteps[4]["primaryPitch"] == 65
    assert bridge.seqActiveClipSteps[4]["primaryVelocity"] == 90

    # Step record chord commitment
    events.clear()
    bridge.seqToggleStepRecord(True)
    bridge.recorder.handle_midi_message(mido.Message("note_on", note=60, velocity=100))
    bridge.recorder.handle_midi_message(mido.Message("note_on", note=64, velocity=100))
    bridge.recorder.handle_midi_message(mido.Message("note_off", note=60, velocity=0))
    bridge.recorder.handle_midi_message(mido.Message("note_off", note=64, velocity=0))
    assert any(ev[0] == "committed" for ev in events)




def test_sequencer_ui_updates_are_delivered_on_gui_thread(bridge):
    import threading

    from PyQt6.QtCore import QCoreApplication, QThread

    app = QCoreApplication.instance() or QCoreApplication([])
    seen = []
    bridge.seqPlayheadsChanged.connect(
        lambda: seen.append(QThread.currentThread() is app.thread())
    )
    t = threading.Thread(target=bridge._on_seq_ui_update, args=({},))
    t.start()
    t.join()
    assert seen == []  # not emitted from the worker thread
    app.processEvents()
    assert seen == [True]


def test_sequencer_uses_part_receive_channel(bridge):
    bridge.patch_state.perf_parts[2].rx_channel = 5
    assert bridge._part_rx_channel(3) == 5
    assert bridge._part_rx_channel(4) == 3


def test_each_track_keeps_its_own_selected_clip(bridge):
    bridge.seqSelectTrack(0)
    bridge.seqSelectClip(3)
    bridge.seqToggleStepNote(0, 60, 100)

    # Switching track must not carry clip 3 over
    bridge.seqSelectTrack(1)
    assert bridge.seqActiveClip == 0
    assert bridge.seqActiveClipSteps[0]["isActive"] is False
    bridge.seqSelectClip(5)

    bridge.seqSelectTrack(0)
    assert bridge.seqActiveClip == 3
    assert bridge.seqActiveClipSteps[0]["isActive"] is True
    assert bridge.recorder.active_clip_idx == 3

    assert [t["selectedClipIdx"] for t in bridge.seqTracks] == [3, 5, 0, 0, 0]


def test_play_from_stop_starts_each_tracks_selected_clip(bridge):
    bridge.seqSelectTrack(0)
    bridge.seqSelectClip(2)
    bridge.seqSelectTrack(4)
    bridge.seqSelectClip(6)
    bridge.seqStopTrack(1)  # queued stop survives into Play

    bridge.seqPlay()
    try:
        assert [t["activeClipIdx"] for t in bridge.seqTracks] == [2, -1, 0, 0, 6]
    finally:
        bridge.seqStop()


def test_launches_move_the_selection(bridge):
    bridge.seqSelectTrack(2)
    bridge.seqLaunchScene(4)
    assert all(t["selectedClipIdx"] == 4 for t in bridge.seqTracks)
    assert bridge.seqActiveClip == 4
    assert bridge.recorder.active_clip_idx == 4

    bridge.seqLaunchClip(0, 7)
    assert bridge.seqTracks[0]["selectedClipIdx"] == 7
    assert bridge.seqActiveClip == 4  # active track (2) unaffected


def test_loading_a_performance_applies_its_sequence_and_tempo(bridge, tmp_path):
    from src.spectre.core.patch_state import PatchState
    from src.spectre.core.spectre_format import save_spectre
    from src.spectre.sequencer.models import default_sequencer_song

    song = default_sequencer_song()
    song.bpm = 97.0
    song.tracks[1].selected_clip_idx = 4
    path = tmp_path / "song.spectre"
    save_spectre(path, PatchState.create_init_patch(), meta={"name": "S"},
                 spectre={"sequencer": song.to_dict()}, kind="performance")

    assert bridge.loadSpectreFile(str(path)) is True
    assert bridge.sequencer.song.tracks[1].selected_clip_idx == 4
    assert bridge.bpm == 97.0
    assert bridge.sequencer.clock.bpm == 97.0
    assert bridge.engine.motion.bpm == 97.0


def test_track_layers(bridge):
    bridge.seqSetTrackTargetPart(1, 4)
    bridge.seqToggleTrackLayer(1, 9)
    bridge.seqToggleTrackLayer(1, 6)
    bridge.seqToggleTrackLayer(1, 4)  # the main part is never a layer
    assert bridge.seqTracks[1]["targetParts"] == [4, 6, 9]
    assert bridge.seqTracks[1]["layerParts"] == [6, 9]

    # Changing the main part keeps the layers (minus the new main)
    bridge.seqSetTrackTargetPart(1, 6)
    assert bridge.seqTracks[1]["targetParts"] == [6, 9]

    bridge.seqToggleTrackLayer(1, 9)
    assert bridge.seqTracks[1]["targetParts"] == [6]


def test_track_kbd_switch_covers_layers(bridge):
    bridge.seqSetTrackTargetPart(0, 2)
    bridge.seqToggleTrackLayer(0, 7)
    bridge.seqSetTrackKbd(0, False)
    parts = bridge.patch_state.perf_parts
    assert parts[1].zone_switch is False and parts[6].zone_switch is False
    bridge.seqSetTrackKbd(0, True)
    assert parts[1].zone_switch is True and parts[6].zone_switch is True


def test_kbd_channel_learned_from_played_keys(bridge):
    import mido
    assert bridge.seqKbdChannel == -1
    bridge._on_kbd_note(mido.Message("note_on", channel=2, note=60, velocity=0))
    assert bridge.seqKbdChannel == -1  # note-off in disguise
    bridge._on_kbd_note(mido.Message("note_on", channel=2, note=60, velocity=90))
    assert bridge.seqKbdChannel == 2
    bridge._on_kbd_note(mido.Message("note_off", channel=5, note=60))
    assert bridge.seqKbdChannel == 2
