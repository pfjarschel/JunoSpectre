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


def test_juno_client_set_tone_tvf_adsr_atomic(mock_midi_mgr):
    client = JunoClient(mock_midi_mgr)
    mode_msg = mido.Message(
        "sysex",
        data=[0x41, 0x10, 0x00, 0x00, 0x3A, 0x12, 0x01, 0x00, 0x00, 0x00, 0x00, 0x7F],
    )
    mock_midi_mgr.iter_juno_messages.return_value = [mode_msg]

    # Set all 4 ADSR params
    client.set_tone_tvf(1, attack=10, decay=20, sustain=90, release=40)

    # Address for Tone 1 TVF T1: 1F 00 20 55
    # Data: [10, 20, 0, 40, 0, 127, 90, 90, 0] (9 bytes)
    sent_packet = mock_midi_mgr.send_juno_sysex.call_args[0][0]
    assert sent_packet[6:10] == [0x1F, 0x00, 0x20, 0x55]
    assert sent_packet[10:19] == [10, 20, 0, 40, 0, 127, 90, 90, 0]


def test_juno_client_set_tone_tva_adsr_atomic(mock_midi_mgr):
    client = JunoClient(mock_midi_mgr)
    mode_msg = mido.Message(
        "sysex",
        data=[0x41, 0x10, 0x00, 0x00, 0x3A, 0x12, 0x01, 0x00, 0x00, 0x00, 0x00, 0x7F],
    )
    mock_midi_mgr.iter_juno_messages.return_value = [mode_msg]

    # Set all 4 ADSR params
    client.set_tone_tva(1, attack=15, decay=25, sustain=85, release=45)

    # Address for Tone 1 TVA T1: 1F 00 20 66
    # Data: [15, 25, 0, 45, 127, 85, 85] (7 bytes)
    sent_packet = mock_midi_mgr.send_juno_sysex.call_args[0][0]
    assert sent_packet[6:10] == [0x1F, 0x00, 0x20, 0x66]
    assert sent_packet[10:17] == [15, 25, 0, 45, 127, 85, 85]


def test_juno_client_read_tone_sustain_offsets(mock_midi_mgr):
    client = JunoClient(mock_midi_mgr)
    mode_msg = mido.Message(
        "sysex",
        data=[0x41, 0x10, 0x00, 0x00, 0x3A, 0x12, 0x01, 0x00, 0x00, 0x00, 0x00, 0x7F],
    )

    # Build chunk 1 mock response (0x7B bytes)
    # Set 0x5B (L2) to 50, and 0x5C (L3 / Sustain) to 88
    # Set 0x6C (TVA L3 / Sustain) to 99
    chunk1_data = [0] * 0x7B
    chunk1_data[0x5B] = 50
    chunk1_data[0x5C] = 88
    chunk1_data[0x6C] = 99
    addr1 = [0x1F, 0x00, 0x20, 0x00]
    csum1 = calculate_checksum(addr1 + chunk1_data)
    msg1 = mido.Message("sysex", data=[0x41, 0x10, 0x00, 0x00, 0x3A, 0x12] + addr1 + chunk1_data + [csum1])

    # LFO2 Chunk A (4 bytes)
    addr2a = [0x1F, 0x00, 0x20, 0x7B]
    data2a = [0, 0, 0, 0]
    csum2a = calculate_checksum(addr2a + data2a)
    msg2a = mido.Message("sysex", data=[0x41, 0x10, 0x00, 0x00, 0x3A, 0x12] + addr2a + data2a + [csum2a])

    # LFO2 Chunk B (26 bytes: LFO2 params + Step Type + 16 Steps)
    addr2b = [0x1F, 0x00, 0x21, 0x00]
    data2b = [0] * 26
    data2b[9] = 1        # Step Type: GLIDE
    data2b[10] = 100     # Step 1: 100 - 64 = +36
    data2b[11] = 28      # Step 2: 28 - 64 = -36
    csum2b = calculate_checksum(addr2b + data2b)
    msg2b = mido.Message("sysex", data=[0x41, 0x10, 0x00, 0x00, 0x3A, 0x12] + addr2b + data2b + [csum2b])

    mock_midi_mgr.iter_juno_messages.return_value = [mode_msg, msg1, msg2a, msg2b]

    tone_state = client.read_tone(1, timeout=0.1)
    # TVF Sustain must be 88 (from 0x5C), not 50 (from 0x5B)
    assert tone_state.tvf_sustain == 88
    # TVA Sustain must be 99 (from 0x6C)
    assert tone_state.tva_sustain == 99
    # Step LFO params
    assert tone_state.step_lfo_type == 1
    assert tone_state.step_lfo_type_str == "GLIDE"
    assert tone_state.step_lfo_steps[0] == 36
    assert tone_state.step_lfo_steps[1] == -36


def test_juno_client_set_tone_step_lfo(mock_midi_mgr):
    client = JunoClient(mock_midi_mgr)
    client._cached_sound_mode = SoundMode.PATCH

    # Test set_tone_step_lfo_type: Tone 1, TYP2 (1) -> addr 1F 00 21 09
    client.set_tone_step_lfo_type(1, 1)
    mock_midi_mgr.send_juno_sysex.assert_called()
    pkt = mock_midi_mgr.send_juno_sysex.call_args[0][0]
    assert pkt[6:10] == [0x1F, 0x00, 0x21, 0x09]
    assert pkt[10] == 1

    # Test set_tone_step_lfo_step: Tone 1, step 0, val +36 -> raw 100 at 1F 00 21 0A
    client.set_tone_step_lfo_step(1, 0, 36)
    pkt = mock_midi_mgr.send_juno_sysex.call_args[0][0]
    assert pkt[6:10] == [0x1F, 0x00, 0x21, 0x0A]
    assert pkt[10] == 100

    # Test set_tone_step_lfo_steps: 16 steps at 1F 00 21 0A
    steps = [0] * 16
    steps[0] = 36
    steps[15] = -36
    client.set_tone_step_lfo_steps(1, steps)
    pkt = mock_midi_mgr.send_juno_sysex.call_args[0][0]
    assert pkt[6:10] == [0x1F, 0x00, 0x21, 0x0A]
    # Check payload (16 bytes)
    payload = pkt[10:-1]
    assert len(payload) == 16
    assert payload[0] == 100
    assert payload[15] == 28


def test_juno_client_set_tone_matrix_switch(mock_midi_mgr):
    client = JunoClient(mock_midi_mgr)
    client._cached_sound_mode = SoundMode.PATCH
    # Tone 1, Ctrl 1, Dest 1 -> offset 0x0017
    client.set_tone_matrix_switch(tone_index=1, ctrl_index=1, dest_index=1, switch_val=1)
    mock_midi_mgr.send_juno_sysex.assert_called()
    sent_packet = mock_midi_mgr.send_juno_sysex.call_args[0][0]
    # Header: 41 10 00 00 3A 12
    assert sent_packet[0:6] == [0x41, 0x10, 0x00, 0x00, 0x3A, 0x12]
    # Address: 1F 00 20 17
    assert sent_packet[6:10] == [0x1F, 0x00, 0x20, 0x17]
    # Payload value: 1
    assert sent_packet[10] == 1





