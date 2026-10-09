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


def test_sequencer_never_touches_kbd_switches():
    """Kbd switches are plain performance settings: sequencer navigation leaves them alone."""
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
    bridge.setPartZoneSwitch = MagicMock()
    bridge.patch_state.perf_parts[0].zone_switch = True
    bridge.patch_state.perf_parts[1].zone_switch = True

    bridge.setActiveView("SEQUENCER")
    for t in range(5):
        bridge.seqSelectTrack(t)
    bridge.seqSetTrackTargetPart(0, 2)
    bridge.setActiveView("LIVE")
    bridge.setActiveView("PERFORMANCE")

    bridge.setPartZoneSwitch.assert_not_called()
    engine.juno.set_perf_zone_switch.assert_not_called()
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
