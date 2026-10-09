"""Tests for Roland Zone Switch driver and MIDI input demuxer."""

from unittest.mock import MagicMock
import mido
import pytest
import time

from src.spectre.core.midi import MidiDeviceManager
from src.spectre.core.protocol import JunoClient


def test_set_perf_zone_switch():
    mock_midi = MagicMock()
    mock_midi.is_juno_connected = True
    client = JunoClient(mock_midi)
    client.send_data = MagicMock()

    # Part/Channel 1 enabled
    client.set_perf_zone_switch(1, True)
    client.send_data.assert_called_with((0x10, 0x00, 0x50, 0x01), [1])

    # Part/Channel 2 disabled
    client.set_perf_zone_switch(2, False)
    client.send_data.assert_called_with((0x10, 0x00, 0x51, 0x01), [0])

    # Part/Channel 10 (drums) disabled
    client.set_perf_zone_switch(10, False)
    client.send_data.assert_called_with((0x10, 0x00, 0x59, 0x01), [0])


def test_midi_input_demuxer_routes_notes_and_sysex():
    mgr = MidiDeviceManager()
    mock_in = MagicMock()
    mock_in.closed = False
    mgr.juno_in = mock_in

    captured_notes = []

    def note_handler(msg):
        captured_notes.append(msg)

    mgr.add_note_listener(note_handler)

    note_msg = mido.Message("note_on", channel=0, note=60, velocity=100)
    sysex_msg = mido.Message("sysex", data=[0x41, 0x10, 0x00, 0x00, 0x00, 0x37, 0x12, 0x00])

    mock_in.iter_pending.return_value = [note_msg, sysex_msg]

    mgr.start_input_worker()
    time.sleep(0.05)
    mgr.stop_input_worker()

    assert len(captured_notes) >= 1
    assert captured_notes[0].note == 60

    # Sysex message should be available in iter_juno_messages
    sysex_items = list(mgr.iter_juno_messages())
    assert any(m.type == "sysex" for m in sysex_items)


def test_sync_keybed_routing_avoids_inactive_parts():
    from src.spectre.ui.bridge import SpectreBridge
    from src.spectre.vector.engine import VectorEngine

    class DummyJuno:
        def __init__(self):
            self.midi = MagicMock()
            self.midi.juno_out.closed = False
            self.midi.is_juno_connected = True
            self.set_perf_zone = MagicMock()
            self.set_perf_zone_switch = MagicMock()

    engine = VectorEngine()
    engine.juno = DummyJuno()
    bridge = SpectreBridge(engine)

    # In default PatchState: Part 1 vol=110, Part 2 vol=85, Parts 3..16 vol=0 (inactive)
    assert bridge._part_is_active(1) is True
    assert bridge._part_is_active(2) is True
    assert bridge._part_is_active(3) is False
    assert bridge._part_is_active(4) is False

    called_parts = []
    def track_zone_switch(part_idx, enabled):
        called_parts.append((part_idx, enabled))

    bridge.setPartZoneSwitch = MagicMock(side_effect=track_zone_switch)

    # 1. Select Track 0 (target Part 1, keybed_enabled=True)
    called_parts.clear()
    bridge.seqSelectTrack(0)

    # Part 1 should be armed, Part 2 disarmed. Inactive parts (3..16) must NEVER be called!
    assert (1, True) in called_parts
    assert (2, False) in called_parts
    for p in range(3, 17):
        assert not any(call[0] == p for call in called_parts)

    # 2. Select Track 2 (default target Part 3, which is inactive)
    called_parts.clear()
    bridge.seqSelectTrack(2)

    # Part 1 and Part 2 must be disarmed (or kept False).
    # Part 3 and parts 4..16 must NEVER receive SysEx/zone calls!
    for p in range(3, 17):
        assert not any(call[0] == p for call in called_parts)

    # 3. Retarget Track 2 to active Part 2 and test keybed switch
    bridge.sequencer.song.tracks[2].keybed_enabled = False
    called_parts.clear()
    bridge.seqSetTrackTargetPart(2, 2)
    assert bridge.sequencer.song.tracks[2].keybed_enabled is False
    # Since keybed_enabled is False, Part 2 should NOT be armed
    assert not any(call[0] == 2 and call[1] is True for call in called_parts)

    # 4. Turn KBD ON for Track 2
    called_parts.clear()
    bridge.seqToggleTrackKeybed(2)
    assert bridge.sequencer.song.tracks[2].keybed_enabled is True
    assert (2, True) in called_parts
    assert (1, False) in called_parts


def test_view_transition_syncs_and_restores_zones():
    from src.spectre.ui.bridge import SpectreBridge
    from src.spectre.vector.engine import VectorEngine

    class DummyJuno:
        def __init__(self):
            self.midi = MagicMock()
            self.midi.juno_out.closed = False
            self.midi.is_juno_connected = True
            self.set_perf_zone = MagicMock()
            self.set_perf_zone_switch = MagicMock()

    engine = VectorEngine()
    engine.juno = DummyJuno()
    bridge = SpectreBridge(engine)

    # Start in PERFORMANCE view with Part 1 and Part 2 ON
    bridge._active_view = "PERFORMANCE"
    bridge.patch_state.perf_parts[0].zone_switch = True
    bridge.patch_state.perf_parts[1].zone_switch = True

    # Transition to SEQUENCER
    bridge.setActiveView("SEQUENCER")
    assert bridge.activeView == "SEQUENCER"

    # In SEQUENCER, Track 0 is focused (target Part 1), so Part 1 is ON, Part 2 is OFF
    assert bridge.patch_state.perf_parts[0].zone_switch is True
    assert bridge.patch_state.perf_parts[1].zone_switch is False

    # Transition back to PERFORMANCE
    bridge.setActiveView("PERFORMANCE")
    assert bridge.activeView == "PERFORMANCE"

    # Both Part 1 and Part 2 should be restored to True
    assert bridge.patch_state.perf_parts[0].zone_switch is True
    assert bridge.patch_state.perf_parts[1].zone_switch is True



def test_midi_input_demuxer_keeps_only_sysex_and_is_bounded():
    mgr = MidiDeviceManager()
    mock_in = MagicMock()
    mock_in.closed = False
    mgr.juno_in = mock_in
    cc = mido.Message("control_change", control=7, value=100)
    sysex = [mido.Message("sysex", data=[0x41, i % 128]) for i in range(300)]
    mock_in.iter_pending.side_effect = [[cc] + sysex] + [[]] * 1000

    mgr.start_input_worker()
    time.sleep(0.05)
    items = list(mgr.iter_juno_messages())  # drained from the queue while the worker runs
    mgr.stop_input_worker()

    assert all(m.type == "sysex" for m in items)
    assert len(items) == 256
    assert items[-1].data == sysex[-1].data  # oldest dropped, newest kept
