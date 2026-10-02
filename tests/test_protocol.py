"""Unit tests for JunoClient protocol logic using mock MIDI transport."""

from unittest.mock import MagicMock
import pytest
import mido

from src.spectre.core.midi import MidiDeviceManager
from src.spectre.core.protocol import JunoClient, SoundMode, IdentityInfo
from src.spectre.core.sysex import (
    ADDR_SETUP,
    ADDR_TEMP_PATCH_PART_1,
    OFFSET_PATCH_TONE_1,
    calculate_checksum,
)


@pytest.fixture
def mock_midi_mgr():
    mgr = MagicMock(spec=MidiDeviceManager)
    return mgr


def test_juno_client_ping(mock_midi_mgr):
    client = JunoClient(mock_midi_mgr)
    
    # Simulate Roland identity reply: 7E <dev> 06 02 41 3A 02 03 00 00 03 00 00
    mock_msg = mido.Message(
        "sysex",
        data=[0x7E, 0x10, 0x06, 0x02, 0x41, 0x3A, 0x02, 0x03, 0x00, 0x00, 0x03, 0x00, 0x00],
    )
    mock_midi_mgr.iter_juno_messages.return_value = [mock_msg]
    
    ident = client.ping(timeout=0.1)
    assert ident is not None
    assert ident.device_id == 0x10
    assert ident.family_code == (0x3A, 0x02)
    assert ident.is_juno_ds_or_xps is True


def test_juno_client_get_sound_mode(mock_midi_mgr):
    client = JunoClient(mock_midi_mgr)
    
    # Simulate DT1 reply for Setup (Sound mode = 0 = PATCH)
    # Addr: 01 00 00 00, Data: 00, Checksum: 7F
    mock_msg = mido.Message(
        "sysex",
        data=[0x41, 0x10, 0x00, 0x00, 0x3A, 0x12, 0x01, 0x00, 0x00, 0x00, 0x00, 0x7F],
    )
    mock_midi_mgr.iter_juno_messages.return_value = [mock_msg]
    
    mode = client.get_sound_mode(timeout=0.1)
    assert mode == SoundMode.PATCH


def test_juno_client_set_tone_level(mock_midi_mgr):
    client = JunoClient(mock_midi_mgr)
    
    # Mock sound mode query response
    mode_msg = mido.Message(
        "sysex",
        data=[0x41, 0x10, 0x00, 0x00, 0x3A, 0x12, 0x01, 0x00, 0x00, 0x00, 0x00, 0x7F],
    )
    mock_midi_mgr.iter_juno_messages.return_value = [mode_msg]
    
    client.set_tone_level(1, 100)
    
    # Verify DT1 packet was sent to MidiDeviceManager
    mock_midi_mgr.send_juno_sysex.assert_called()
    sent_packet = mock_midi_mgr.send_juno_sysex.call_args[0][0]
    
    # Verify header, command 0x12, address 1F 00 20 00, value 100 (0x64)
    assert sent_packet[0:6] == [0x41, 0x10, 0x00, 0x00, 0x3A, 0x12]
    assert sent_packet[6:10] == [0x1F, 0x00, 0x20, 0x00]
    assert sent_packet[10] == 100
