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


def test_juno_client_get_tone_wave(mock_midi_mgr):
    client = JunoClient(mock_midi_mgr)
    
    # Mock sound mode query response (PATCH mode)
    mode_msg = mido.Message(
        "sysex",
        data=[0x41, 0x10, 0x00, 0x00, 0x3A, 0x12, 0x01, 0x00, 0x00, 0x00, 0x00, 0x7F],
    )
    # Wave query response: Addr 1F 00 20 27
    # Data: type=0, group_id=1 (0,0,0,1), wave_num=579 (0x0243 -> nibbles 0,2,4,3)
    # Checksum calculation:
    from src.spectre.core.sysex import calculate_checksum
    addr = [0x1F, 0x00, 0x20, 0x27]
    payload = [0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x02, 0x04, 0x03]
    csum = calculate_checksum(addr + payload)
    wave_msg = mido.Message(
        "sysex",
        data=[0x41, 0x10, 0x00, 0x00, 0x3A, 0x12] + addr + payload + [csum],
    )
    mock_midi_mgr.iter_juno_messages.return_value = [mode_msg, wave_msg]

    bank, wave_num, gtype = client.get_tone_wave(1, timeout=0.1)
    assert bank == "INTA"
    assert wave_num == 579
    assert gtype == 0


def test_juno_client_ensure_tone_enabled(mock_midi_mgr):
    client = JunoClient(mock_midi_mgr)
    mode_msg = mido.Message(
        "sysex",
        data=[0x41, 0x10, 0x00, 0x00, 0x3A, 0x12, 0x01, 0x00, 0x00, 0x00, 0x00, 0x7F],
    )
    mock_midi_mgr.iter_juno_messages.return_value = [mode_msg]

    client.ensure_tone_enabled(2)
    # Should have sent switch=1 at 1F 00 10 0E and dry_send=127 at 1F 00 22 0C
    assert mock_midi_mgr.send_juno_sysex.call_count >= 2


def test_juno_client_set_patch_name(mock_midi_mgr):
    client = JunoClient(mock_midi_mgr)
    mode_msg = mido.Message(
        "sysex",
        data=[0x41, 0x10, 0x00, 0x00, 0x3A, 0x12, 0x01, 0x00, 0x00, 0x00, 0x00, 0x7F],
    )
    mock_midi_mgr.iter_juno_messages.return_value = [mode_msg]

    client.set_patch_name("JUNO SPECTRE")
    assert mock_midi_mgr.send_juno_sysex.called
    last_call = mock_midi_mgr.send_juno_sysex.call_args[0][0]
    # Check ASCII encoding of JUNO SPECTRE
    assert b"JUNO SPECTRE" in bytes(last_call)


def test_juno_client_init_patch(mock_midi_mgr):
    client = JunoClient(mock_midi_mgr)
    mode_msg = mido.Message(
        "sysex",
        data=[0x41, 0x10, 0x00, 0x00, 0x3A, 0x12, 0x01, 0x00, 0x00, 0x00, 0x00, 0x7F],
    )
    mock_midi_mgr.iter_juno_messages.return_value = [mode_msg]

    client.init_patch()
    # Verified multiple SysEx commands were dispatched for Patch Common and 4 tones
    assert mock_midi_mgr.send_juno_sysex.call_count >= 30


