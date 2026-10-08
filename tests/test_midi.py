"""Unit tests for MidiDeviceManager port discovery, disconnect recovery, and reconnect."""

from unittest.mock import MagicMock, patch

import mido
import pytest

from src.spectre.core.midi import MidiDeviceManager
from src.spectre.core.protocol import JunoClient


def test_find_juno_ports_prefers_midi_1():
    with patch.object(MidiDeviceManager, "get_input_names", return_value=["JUNO-DS:JUNO-DS MIDI 2", "JUNO-DS:JUNO-DS MIDI 1"]), \
         patch.object(MidiDeviceManager, "get_output_names", return_value=["JUNO-DS:JUNO-DS MIDI 2", "JUNO-DS:JUNO-DS MIDI 1"]):
        in_p, out_p = MidiDeviceManager.find_juno_ports()
        assert in_p == "JUNO-DS:JUNO-DS MIDI 1"
        assert out_p == "JUNO-DS:JUNO-DS MIDI 1"


def test_find_juno_ports_fallback():
    with patch.object(MidiDeviceManager, "get_input_names", return_value=["Roland XPS-30"]), \
         patch.object(MidiDeviceManager, "get_output_names", return_value=["Roland XPS-30"]):
        in_p, out_p = MidiDeviceManager.find_juno_ports()
        assert in_p == "Roland XPS-30"
        assert out_p == "Roland XPS-30"


def test_find_juno_ports_none_found():
    with patch.object(MidiDeviceManager, "get_input_names", return_value=["Midi Through"]), \
         patch.object(MidiDeviceManager, "get_output_names", return_value=["Midi Through"]):
        in_p, out_p = MidiDeviceManager.find_juno_ports()
        assert in_p is None
        assert out_p is None


def test_find_launch_control_ports():
    with patch.object(MidiDeviceManager, "get_input_names", return_value=["Launch Control XL:Launch Control XL DAW", "Launch Control XL:Launch Control XL MIDI In"]), \
         patch.object(MidiDeviceManager, "get_output_names", return_value=["Launch Control XL:Launch Control XL DAW", "Launch Control XL:Launch Control XL MIDI Out"]):
        in_p, out_p = MidiDeviceManager.find_launch_control_ports()
        assert in_p == "Launch Control XL:Launch Control XL MIDI In"
        assert out_p == "Launch Control XL:Launch Control XL MIDI Out"


def test_connect_juno_not_found_raises():
    mgr = MidiDeviceManager()
    with patch.object(MidiDeviceManager, "find_juno_ports", return_value=(None, None)):
        with pytest.raises(ConnectionError, match="Could not find Roland synth ports"):
            mgr.connect_juno()


def test_connect_juno_success():
    mgr = MidiDeviceManager()
    mock_in = MagicMock(spec=mido.ports.BaseInput, closed=False)
    mock_out = MagicMock(spec=mido.ports.BaseOutput, closed=False)

    with patch.object(MidiDeviceManager, "find_juno_ports", return_value=("InPort", "OutPort")), \
         patch("mido.open_input", return_value=mock_in), \
         patch("mido.open_output", return_value=mock_out):
        in_n, out_n = mgr.connect_juno()
        assert in_n == "InPort"
        assert out_n == "OutPort"
        assert mgr.is_juno_connected is True


def test_close_and_reconnect_juno():
    mgr = MidiDeviceManager()
    mock_in = MagicMock(spec=mido.ports.BaseInput, closed=False)
    mock_out = MagicMock(spec=mido.ports.BaseOutput, closed=False)
    mgr.juno_in = mock_in
    mgr.juno_out = mock_out

    assert mgr.is_juno_connected is True
    mgr.close_juno()
    assert mgr.is_juno_connected is False
    mock_in.close.assert_called_once()
    mock_out.close.assert_called_once()

    # Reconnect
    mock_in2 = MagicMock(spec=mido.ports.BaseInput, closed=False)
    mock_out2 = MagicMock(spec=mido.ports.BaseOutput, closed=False)
    with patch.object(MidiDeviceManager, "find_juno_ports", return_value=("InPort", "OutPort")), \
         patch("mido.open_input", return_value=mock_in2), \
         patch("mido.open_output", return_value=mock_out2):
        assert mgr.reconnect_juno() is True
        assert mgr.is_juno_connected is True


def test_send_juno_sysex_disconnect_handling():
    mgr = MidiDeviceManager()
    mock_out = MagicMock(spec=mido.ports.BaseOutput, closed=False)
    mock_out.send.side_effect = OSError("ALSA port unplugged")
    mock_in = MagicMock(spec=mido.ports.BaseInput, closed=False)
    mgr.juno_in = mock_in
    mgr.juno_out = mock_out

    with pytest.raises(ConnectionError, match="Error sending SysEx"):
        mgr.send_juno_sysex([0x7E, 0x7F, 0x06, 0x01])

    # Should have closed broken port
    assert mgr.is_juno_connected is False


def test_send_all_notes_off_panic():
    mgr = MidiDeviceManager()
    mock_out = MagicMock(spec=mido.ports.BaseOutput, closed=False)
    mgr.juno_out = mock_out

    sent = mgr.send_all_notes_off(include_reset=True)
    assert sent == 32  # 16 channels * (CC 123 + CC 121)
    assert mock_out.send.call_count == 32


def test_juno_client_auto_reconnect():
    mgr = MagicMock(spec=MidiDeviceManager)
    mgr.is_juno_connected = True
    # First send fails with ConnectionError, then reconnect succeeds and second send succeeds
    mgr.send_juno_sysex.side_effect = [ConnectionError("Port closed"), None]
    mgr.reconnect_juno.return_value = True

    client = JunoClient(mgr)
    client.send_data([0x1F, 0x00, 0x00, 0x00], [0x42])

    assert mgr.reconnect_juno.call_count == 1
    assert mgr.send_juno_sysex.call_count == 2
