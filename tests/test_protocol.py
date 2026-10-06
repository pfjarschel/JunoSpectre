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


def test_mfx_catalog_integrity():
    from src.spectre.core.mfx_catalog import get_mfx_catalog, get_mfx_algo, get_mfx_categories

    catalog = get_mfx_catalog()
    assert len(catalog) == 80
    ids = [a["id"] for a in catalog]
    assert ids == list(range(1, 81))

    categories = set(get_mfx_categories())
    for algo in catalog:
        assert algo["cat"] in categories
        assert len(algo["params"]) >= 4
        for p in algo["params"]:
            assert "idx" in p
            assert "label" in p
            assert "min" in p
            assert "max" in p

    # Test lookup
    algo1 = get_mfx_algo(1)
    assert algo1 is not None
    assert "EQUALIZER" in algo1["name"]

    algo80 = get_mfx_algo(80)
    assert algo80 is not None
    assert "BIT CRUSHER" in algo80["name"]


def test_juno_client_set_mfx_param(mock_midi_mgr):
    from src.spectre.core.sysex import pack_4nibbles

    client = JunoClient(mock_midi_mgr)
    client._cached_sound_mode = SoundMode.PATCH

    # Test setting param 0 (Param 1) to value 10
    client.set_mfx_param(0, 10)
    assert mock_midi_mgr.send_juno_sysex.call_count == 2
    # First call targets Patch MFX (1F 00 02 11), second mirrors to Perf Common MFX1 (10 00 02 11)
    call1 = mock_midi_mgr.send_juno_sysex.call_args_list[-2][0][0]
    call2 = mock_midi_mgr.send_juno_sysex.call_args_list[-1][0][0]
    assert call1[6:10] == [0x1F, 0x00, 0x02, 0x11]
    assert call2[6:10] == [0x10, 0x00, 0x02, 0x11]
    expected_nibbles = pack_4nibbles(10 + 32768)
    assert call1[10:14] == expected_nibbles
    assert call2[10:14] == expected_nibbles

    # Test setting param 1 (Param 2)
    mock_midi_mgr.send_juno_sysex.reset_mock()
    client.set_mfx_param(1, -5)
    call1 = mock_midi_mgr.send_juno_sysex.call_args_list[-2][0][0]
    call2 = mock_midi_mgr.send_juno_sysex.call_args_list[-1][0][0]
    assert call1[6:10] == [0x1F, 0x00, 0x02, 0x15]
    assert call2[6:10] == [0x10, 0x00, 0x02, 0x15]
    assert call1[10:14] == pack_4nibbles(-5 + 32768)

    # Test bulk setting
    mock_midi_mgr.send_juno_sysex.reset_mock()
    client.set_mfx_params_bulk([10, 20, 30])
    assert mock_midi_mgr.send_juno_sysex.call_count == 2
    bulk_call1 = mock_midi_mgr.send_juno_sysex.call_args_list[-2][0][0]
    bulk_call2 = mock_midi_mgr.send_juno_sysex.call_args_list[-1][0][0]
    assert bulk_call1[6:10] == [0x1F, 0x00, 0x02, 0x11]
    assert bulk_call2[6:10] == [0x10, 0x00, 0x02, 0x11]
    expected_bulk_payload = pack_4nibbles(10 + 32768) + pack_4nibbles(20 + 32768) + pack_4nibbles(30 + 32768)
    assert bulk_call1[10:22] == expected_bulk_payload


def test_juno_client_read_mfx(mock_midi_mgr):
    from src.spectre.core.sysex import pack_4nibbles

    client = JunoClient(mock_midi_mgr)
    client._cached_sound_mode = SoundMode.PATCH

    # Construct mock 145-byte MFX response
    # bytes 0..3: Type (4), Dry (127), Chorus (10), Reverb (20)
    # bytes 4..16: controls (dummy)
    # bytes 17..144: 32 params (4 nibbles each)
    mock_resp = [4, 127, 10, 20] + [0] * 13
    for i in range(32):
        mock_resp.extend(pack_4nibbles(i + 32768))

    client.request_data = MagicMock(return_value=bytes(mock_resp))
    mfx_type, dry, cho, rev, params = client.read_mfx()
    assert mfx_type == 4
    assert dry == 127
    assert cho == 10
    assert rev == 20
    assert len(params) == 32
    assert params[0] == 0
    assert params[5] == 5
    assert params[31] == 31


def test_juno_client_chorus_sysex(mock_midi_mgr):
    from src.spectre.core.sysex import pack_4nibbles

    client = JunoClient(mock_midi_mgr)
    client._cached_sound_mode = SoundMode.PATCH

    mock_midi_mgr.send_juno_sysex.reset_mock()
    client.set_chorus(1, level=90, output_select=2)
    # Check sends to Patch common and Perf common
    patch_call = mock_midi_mgr.send_juno_sysex.call_args_list[-4][0][0]
    perf_call = mock_midi_mgr.send_juno_sysex.call_args_list[-3][0][0]
    assert patch_call[6:10] == [0x1F, 0x00, 0x04, 0x01]  # level
    assert patch_call[10] == 90
    assert perf_call[6:10] == [0x10, 0x00, 0x04, 0x01]
    assert perf_call[10] == 90

    # Rate 4-nibbles
    mock_midi_mgr.send_juno_sysex.reset_mock()
    client.set_chorus_param("rate", 55)
    call1 = mock_midi_mgr.send_juno_sysex.call_args_list[-2][0][0]
    call2 = mock_midi_mgr.send_juno_sysex.call_args_list[-1][0][0]
    assert call1[6:10] == [0x1F, 0x00, 0x04, 0x14]
    assert call2[6:10] == [0x10, 0x00, 0x04, 0x14]
    assert call1[10:14] == pack_4nibbles(55 + 32768)

    # Depth 4-nibbles
    mock_midi_mgr.send_juno_sysex.reset_mock()
    client.set_chorus_param("depth", 75)
    call1 = mock_midi_mgr.send_juno_sysex.call_args_list[-2][0][0]
    assert call1[6:10] == [0x1F, 0x00, 0x04, 0x1C]
    assert call1[10:14] == pack_4nibbles(75 + 32768)


def test_juno_client_reverb_sysex(mock_midi_mgr):
    from src.spectre.core.sysex import pack_4nibbles

    client = JunoClient(mock_midi_mgr)
    client._cached_sound_mode = SoundMode.PATCH

    mock_midi_mgr.send_juno_sysex.reset_mock()
    client.set_reverb(4, level=70)
    patch_call = mock_midi_mgr.send_juno_sysex.call_args_list[-2][0][0]
    assert patch_call[6:10] == [0x1F, 0x00, 0x06, 0x01]  # level
    assert patch_call[10] == 70

    # Time 4-nibbles
    mock_midi_mgr.send_juno_sysex.reset_mock()
    client.set_reverb_param("time", 65)
    call1 = mock_midi_mgr.send_juno_sysex.call_args_list[-2][0][0]
    call2 = mock_midi_mgr.send_juno_sysex.call_args_list[-1][0][0]
    assert call1[6:10] == [0x1F, 0x00, 0x06, 0x07]
    assert call2[6:10] == [0x10, 0x00, 0x06, 0x07]
    assert call1[10:14] == pack_4nibbles(65 + 32768)


def test_juno_client_master_eq_sysex(mock_midi_mgr):
    client = JunoClient(mock_midi_mgr)

    # Switch
    mock_midi_mgr.send_juno_sysex.reset_mock()
    client.set_master_eq_param("switch", True)
    call1 = mock_midi_mgr.send_juno_sysex.call_args_list[-2][0][0]
    call2 = mock_midi_mgr.send_juno_sysex.call_args_list[-1][0][0]
    assert call1[6:10] == [0x00, 0x00, 0x04, 0x00]
    assert call1[10] == 1
    assert call2[6:10] == [0x02, 0x00, 0x02, 0x00]
    assert call2[10] == 1

    # Low Freq
    mock_midi_mgr.send_juno_sysex.reset_mock()
    client.set_master_eq_param("lowFreq", 200)
    assert mock_midi_mgr.send_juno_sysex.call_args[0][0][6:11] == [0x00, 0x00, 0x04, 0x01, 0]
    client.set_master_eq_param("lowFreq", 400)
    assert mock_midi_mgr.send_juno_sysex.call_args[0][0][6:11] == [0x00, 0x00, 0x04, 0x01, 1]

    # Low Gain (offset 64: +3 -> 67)
    mock_midi_mgr.send_juno_sysex.reset_mock()
    client.set_master_eq_param("lowGain", 3)
    assert mock_midi_mgr.send_juno_sysex.call_args[0][0][6:11] == [0x00, 0x00, 0x04, 0x02, 67]

    # Mid Freq (1000 Hz is index 7)
    mock_midi_mgr.send_juno_sysex.reset_mock()
    client.set_master_eq_param("midFreq", 1000)
    assert mock_midi_mgr.send_juno_sysex.call_args[0][0][6:11] == [0x00, 0x00, 0x04, 0x03, 7]

    # Mid Q (2.0 is index 4)
    mock_midi_mgr.send_juno_sysex.reset_mock()
    client.set_master_eq_param("midQ", 2.0)
    assert mock_midi_mgr.send_juno_sysex.call_args[0][0][6:11] == [0x00, 0x00, 0x04, 0x04, 4]

    # Mid Gain (-5 -> 59)
    mock_midi_mgr.send_juno_sysex.reset_mock()
    client.set_master_eq_param("midGain", -5)
    assert mock_midi_mgr.send_juno_sysex.call_args[0][0][6:11] == [0x00, 0x00, 0x04, 0x05, 59]

    # High Freq (4000 Hz is index 1)
    mock_midi_mgr.send_juno_sysex.reset_mock()
    client.set_master_eq_param("highFreq", 4000)
    assert mock_midi_mgr.send_juno_sysex.call_args[0][0][6:11] == [0x00, 0x00, 0x04, 0x06, 1]

    # High Gain (+4 -> 68)
    mock_midi_mgr.send_juno_sysex.reset_mock()
    client.set_master_eq_param("highGain", 4)
    assert mock_midi_mgr.send_juno_sysex.call_args[0][0][6:11] == [0x00, 0x00, 0x04, 0x07, 68]

    # System Master Level
    mock_midi_mgr.send_juno_sysex.reset_mock()
    client.set_master_eq_param("masterLevel", 112)
    assert mock_midi_mgr.send_juno_sysex.call_args[0][0][6:11] == [0x02, 0x00, 0x00, 0x05, 112]


def test_juno_client_read_chorus_and_reverb(mock_midi_mgr):
    from src.spectre.core.sysex import pack_4nibbles

    client = JunoClient(mock_midi_mgr)
    client._cached_sound_mode = SoundMode.PATCH

    # Chorus mock response (40 bytes)
    c_resp = [1, 95, 0, 2] + [0] * 8
    c_resp.extend(pack_4nibbles(12 + 32768))  # predelay at 0x0C
    c_resp.extend([0] * 4)
    c_resp.extend(pack_4nibbles(45 + 32768))  # rate at 0x14
    c_resp.extend([0] * 4)
    c_resp.extend(pack_4nibbles(70 + 32768))  # depth at 0x1C
    c_resp.extend([0] * 4)
    c_resp.extend(pack_4nibbles(25 + 32768))  # feedback at 0x24

    client.request_data = MagicMock(return_value=bytes(c_resp))
    c_type, c_lvl, c_out, c_pre, c_rate, c_dep, c_fb = client.read_chorus()
    assert c_type == 1
    assert c_lvl == 95
    assert c_out == 2
    assert c_pre == 12
    assert c_rate == 45
    assert c_dep == 70
    assert c_fb == 25

    # Reverb mock response (32 bytes)
    r_resp = [4, 80, 0]
    r_resp.extend(pack_4nibbles(18 + 32768))  # predelay at 0x03
    r_resp.extend(pack_4nibbles(65 + 32768))  # time at 0x07
    r_resp.extend([0] * 4)
    r_resp.extend(pack_4nibbles(40 + 32768))  # damp at 0x0F
    r_resp.extend([0] * 4)
    r_resp.extend(pack_4nibbles(55 + 32768))  # diffusion at 0x17
    r_resp.extend(pack_4nibbles(60 + 32768))  # tone at 0x1B

    client.request_data = MagicMock(return_value=bytes(r_resp))
    r_type, r_lvl, r_pre, r_time, r_damp, r_diff, r_tone = client.read_reverb()
    assert r_type == 4
    assert r_lvl == 80
    assert r_pre == 18
    assert r_time == 65
    assert r_damp == 40
    assert r_diff == 55
    assert r_tone == 60







def test_juno_client_set_tone_tvf_env_block(mock_midi_mgr):
    client = JunoClient(mock_midi_mgr)
    client._cached_sound_mode = SoundMode.PATCH

    client.set_tone_tvf_env(1, [10, 20, 30, 40, 0, 127, 90, 90, 5])
    sent_packet = mock_midi_mgr.send_juno_sysex.call_args[0][0]
    # Tone 1 base + TVF T1 offset: 1F 00 20 55, contiguous 9-byte block
    assert sent_packet[6:10] == [0x1F, 0x00, 0x20, 0x55]
    assert sent_packet[10:19] == [10, 20, 30, 40, 0, 127, 90, 90, 5]

    with pytest.raises(ValueError):
        client.set_tone_tvf_env(1, [1, 2, 3])


def test_juno_client_set_tone_tva_env_block_clamps(mock_midi_mgr):
    client = JunoClient(mock_midi_mgr)
    client._cached_sound_mode = SoundMode.PATCH

    client.set_tone_tva_env(1, [15, 250, 0, 45, 127, -8, 85])
    sent_packet = mock_midi_mgr.send_juno_sysex.call_args[0][0]
    # Tone 1 base + TVA T1 offset: 1F 00 20 66, contiguous 7-byte block
    assert sent_packet[6:10] == [0x1F, 0x00, 0x20, 0x66]
    assert sent_packet[10:17] == [15, 127, 0, 45, 127, 0, 85]


def test_juno_client_single_adsr_param_writes_minimal_segment(mock_midi_mgr):
    """ADSR quick edits (e.g. MIDI-learned knobs) must not stomp custom levels."""
    client = JunoClient(mock_midi_mgr)
    client._cached_sound_mode = SoundMode.PATCH

    # Attack alone -> exactly one byte to T1 (0x55), no L0/L1 canonicalization
    mock_midi_mgr.reset_mock()
    client.set_tone_tvf(1, attack=7)
    assert mock_midi_mgr.send_juno_sysex.call_count == 1
    sent = mock_midi_mgr.send_juno_sysex.call_args[0][0]
    assert sent[6:10] == [0x1F, 0x00, 0x20, 0x55]
    assert sent[10] == 7

    # Release alone -> single byte at T4 (0x58)
    mock_midi_mgr.reset_mock()
    client.set_tone_tvf(1, release=66)
    assert mock_midi_mgr.send_juno_sysex.call_count == 1
    sent = mock_midi_mgr.send_juno_sysex.call_args[0][0]
    assert sent[6:10] == [0x1F, 0x00, 0x20, 0x58]
    assert sent[10] == 66

    # Decay alone -> single byte at TVA T2 (0x67), T3 untouched
    mock_midi_mgr.reset_mock()
    client.set_tone_tva(1, decay=33)
    assert mock_midi_mgr.send_juno_sysex.call_count == 1
    sent = mock_midi_mgr.send_juno_sysex.call_args[0][0]
    assert sent[6:10] == [0x1F, 0x00, 0x20, 0x67]
    assert sent[10] == 33


def test_juno_client_read_tone_populates_raw_segments(mock_midi_mgr):
    client = JunoClient(mock_midi_mgr)
    mode_msg = mido.Message(
        "sysex",
        data=[0x41, 0x10, 0x00, 0x00, 0x3A, 0x12, 0x01, 0x00, 0x00, 0x00, 0x00, 0x7F],
    )

    chunk1_data = [0] * 0x7B
    # TVF two-step shape: T1=5 T2=50 T3=60 T4=20, L0=0 L1=127 L2=30 L3=95 L4=0
    chunk1_data[0x55] = 5
    chunk1_data[0x56] = 50
    chunk1_data[0x57] = 60
    chunk1_data[0x58] = 20
    chunk1_data[0x59] = 0
    chunk1_data[0x5A] = 127
    chunk1_data[0x5B] = 30
    chunk1_data[0x5C] = 95
    chunk1_data[0x5D] = 0
    # TVA: T1=80 T2=30 T3=40 T4=60, L1=127 L2=96 L3=110
    chunk1_data[0x66] = 80
    chunk1_data[0x67] = 30
    chunk1_data[0x68] = 40
    chunk1_data[0x69] = 60
    chunk1_data[0x6A] = 127
    chunk1_data[0x6B] = 96
    chunk1_data[0x6C] = 110

    addr1 = [0x1F, 0x00, 0x20, 0x00]
    csum1 = calculate_checksum(addr1 + chunk1_data)
    msg1 = mido.Message("sysex", data=[0x41, 0x10, 0x00, 0x00, 0x3A, 0x12] + addr1 + chunk1_data + [csum1])

    addr2a = [0x1F, 0x00, 0x20, 0x7B]
    csum2a = calculate_checksum(addr2a)
    msg2a = mido.Message("sysex", data=[0x41, 0x10, 0x00, 0x00, 0x3A, 0x12] + addr2a + [csum2a])

    addr2b = [0x1F, 0x00, 0x21, 0x00]
    data2b = [0] * 26
    csum2b = calculate_checksum(addr2b + data2b)
    msg2b = mido.Message("sysex", data=[0x41, 0x10, 0x00, 0x00, 0x3A, 0x12] + addr2b + data2b + [csum2b])

    mock_midi_mgr.iter_juno_messages.return_value = [mode_msg, msg1, msg2a, msg2b]

    tone = client.read_tone(1, timeout=0.1)
    assert tone.tvf_env_block() == [5, 50, 60, 20, 0, 127, 30, 95, 0]
    assert tone.tvf_env_custom is True
    assert tone.tvf_sustain == 95
    assert tone.tva_env_block() == [80, 30, 40, 60, 127, 96, 110]
    assert tone.tva_env_custom is True


def test_juno_client_env_modifier_writes(mock_midi_mgr):
    """TVF/TVA signed envelope modifiers land on their documented offsets."""
    client = JunoClient(mock_midi_mgr)
    client._cached_sound_mode = SoundMode.PATCH

    sent = []
    mock_midi_mgr.send_juno_sysex.side_effect = lambda p: sent.append((p[6:10], p[10]))

    # TVF T1 vel sens -> 0x52, T4 vel sens -> 0x53, time keyfollow -> 0x54
    client.set_tone_tvf(1, env_t1_vel_sens=94, env_t4_vel_sens=54, env_time_keyfollow=69)
    addrs = [a[3] for a, _ in sent]
    assert addrs == [0x52, 0x53, 0x54]

    # Time keyfollow is clamped to the -100..+100 raw window 54..74
    sent.clear()
    client.set_tone_tvf(1, env_time_keyfollow=999)
    assert sent[0][1] == 74
    sent.clear()
    client.set_tone_tva(1, env_time_keyfollow=-999)
    assert sent[0][1] == 54

    # TVA env modifiers use the 0x62/0x63/0x64/0x65 cluster
    sent.clear()
    client.set_tone_tva(1, env_vel_sens=89, env_t1_vel_sens=64, env_t4_vel_sens=64, env_time_keyfollow=64)
    assert [a[3] for a, _ in sent] == [0x62, 0x63, 0x64, 0x65]


def test_juno_client_read_tone_env_modifiers(mock_midi_mgr):
    client = JunoClient(mock_midi_mgr)
    mode_msg = mido.Message(
        "sysex",
        data=[0x41, 0x10, 0x00, 0x00, 0x3A, 0x12, 0x01, 0x00, 0x00, 0x00, 0x00, 0x7F],
    )

    chunk1_data = [64] * 0x7B
    chunk1_data[0x52] = 100   # TVF T1 vel sens +36
    chunk1_data[0x53] = 30    # TVF T4 vel sens -34
    chunk1_data[0x54] = 69    # TVF time keyfollow +50%
    chunk1_data[0x63] = 80    # TVA T1 vel sens +16
    chunk1_data[0x65] = 59    # TVA time keyfollow -50%

    addr1 = [0x1F, 0x00, 0x20, 0x00]
    csum1 = calculate_checksum(addr1 + chunk1_data)
    msg1 = mido.Message("sysex", data=[0x41, 0x10, 0x00, 0x00, 0x3A, 0x12] + addr1 + chunk1_data + [csum1])

    addr2a = [0x1F, 0x00, 0x20, 0x7B]
    data2a = [0, 0, 0, 0]
    csum2a = calculate_checksum(addr2a + data2a)
    msg2a = mido.Message("sysex", data=[0x41, 0x10, 0x00, 0x00, 0x3A, 0x12] + addr2a + data2a + [csum2a])

    addr2b = [0x1F, 0x00, 0x21, 0x00]
    data2b = [0] * 26
    csum2b = calculate_checksum(addr2b + data2b)
    msg2b = mido.Message("sysex", data=[0x41, 0x10, 0x00, 0x00, 0x3A, 0x12] + addr2b + data2b + [csum2b])

    mock_midi_mgr.iter_juno_messages.return_value = [mode_msg, msg1, msg2a, msg2b]

    tone = client.read_tone(1, timeout=0.1)
    assert tone.tvf_env_t1_vel_sens_bipolar == 36
    assert tone.tvf_env_t4_vel_sens_bipolar == -34
    assert tone.tvf_env_time_kf_bipolar == 50
    assert tone.tva_env_t1_vel_sens_bipolar == 16
    assert tone.tva_env_time_kf_bipolar == -50
