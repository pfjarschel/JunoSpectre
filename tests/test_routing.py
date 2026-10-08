"""Unit tests for FX and Tone Routing engine, presets, and pitfall detector."""

from unittest.mock import MagicMock

import pytest

from src.spectre.core.midi import MidiDeviceManager
from src.spectre.core.patch_state import PatchState
from src.spectre.core.protocol import JunoClient, SoundMode


@pytest.fixture
def mock_midi_mgr():
    mgr = MagicMock(spec=MidiDeviceManager)
    return mgr


def test_juno_client_set_tone_output(mock_midi_mgr):
    client = JunoClient(mock_midi_mgr)
    client._cached_sound_mode = SoundMode.PATCH

    # Set Tone 1 output assign = 0 (MFX), level = 100, chorus_send = 30, reverb_send = 40
    client.set_tone_output(
        tone_index=1,
        output_assign=0,
        output_level=100,
        chorus_send=30,
        reverb_send=40,
    )

    assert mock_midi_mgr.send_juno_sysex.call_count == 4
    sent_packets = [c[0][0] for c in mock_midi_mgr.send_juno_sysex.call_args_list]

    # Roland DT1 header: 41 10 00 00 3A 12 <addr 4 bytes> <data> <checksum>
    assert all(p[0:6] == [0x41, 0x10, 0x00, 0x00, 0x3A, 0x12] for p in sent_packets)


def test_juno_client_set_patch_output_assign(mock_midi_mgr):
    client = JunoClient(mock_midi_mgr)
    client._cached_sound_mode = SoundMode.PATCH

    # Set Patch Output Assign to TONE (4)
    client.set_patch_output_assign(4)

    assert mock_midi_mgr.send_juno_sysex.call_count == 1
    packet = mock_midi_mgr.send_juno_sysex.call_args[0][0]
    # Addr: 1F 00 00 27, Data: 04
    assert packet[6:10] == [0x1F, 0x00, 0x00, 0x27]
    assert packet[10] == 4


def test_patch_state_routing_defaults():
    state = PatchState()
    assert len(state.tones) == 4
    for t in state.tones:
        assert t.output_assign == 0
        assert t.output_level == 127
        assert t.chorus_send == 0
        assert t.reverb_send == 0
    assert state.effects.routing_preset == ""
    assert state.effects.manual_routing_unlocked is False


def test_bridge_routing_presets_and_pitfalls():
    from src.spectre.ui.bridge import SpectreBridge
    from src.spectre.vector.engine import VectorEngine

    engine = VectorEngine()
    bridge = SpectreBridge(engine)
    assert bridge.routingPreset == ""  # Initially no preset selected

    # 1. Apply SERIAL_CHAIN preset
    bridge.applyRoutingPreset("SERIAL_CHAIN")
    assert bridge.routingPreset == "SERIAL_CHAIN"
    assert bridge.manualRoutingUnlocked is False
    assert bridge.toneOutputAssigns == [0, 0, 0, 0]
    assert bridge.toneOutputLevels == [127, 127, 127, 127]
    assert bridge.toneChorusSends == [0, 0, 0, 0]
    assert bridge.toneReverbSends == [0, 0, 0, 0]
    assert bridge.mfxDrySend == 0
    assert bridge.mfxChorusSend == 127
    assert bridge.mfxReverbSend == 0
    assert bridge.chorusToReverb == 1  # REV only (pure serial cascade)

    # In SERIAL_CHAIN, no duplicate reverb sends exist
    pitfalls = bridge.detectRoutingPitfalls()
    # It will only have info note that chorus is sending to reverb in mono
    reverb_overloads = [p for p in pitfalls if p["type"] == "REVERB_OVERLOAD"]
    assert len(reverb_overloads) == 0

    # 2. Trigger REVERB_OVERLOAD intentionally
    bridge.setToneRoutingParam(1, "reverbSend", 80)
    bridge.setMfxSend("reverb", 75)
    pitfalls = bridge.detectRoutingPitfalls()
    reverb_overloads = [p for p in pitfalls if p["type"] == "REVERB_OVERLOAD"]
    assert len(reverb_overloads) == 1
    assert "Tones" in reverb_overloads[0]["description"]
    assert "MFX" in reverb_overloads[0]["description"]

    # 3. Apply STUDIO_AUX preset
    bridge.applyRoutingPreset("STUDIO_AUX")
    assert bridge.routingPreset == "STUDIO_AUX"
    assert bridge.mfxDrySend == 127
    assert bridge.mfxChorusSend == 60
    assert bridge.mfxReverbSend == 60
    assert bridge.chorusToReverb == 0  # MAIN only

    pitfalls = bridge.detectRoutingPitfalls()
    warnings = [p for p in pitfalls if p["severity"] == "warning"]
    assert len(warnings) == 0  # No dangerous parallel overload warnings

    # 4. Apply VINTAGE_SYNTH preset
    bridge.applyRoutingPreset("VINTAGE_SYNTH")
    assert bridge.routingPreset == "VINTAGE_SYNTH"
    assert bridge.toneOutputAssigns == [1, 1, 1, 1]  # DIRECT L+R
    assert bridge.mfxDrySend == 0
    assert bridge.mfxChorusSend == 0
    assert bridge.mfxReverbSend == 0

    # 5. Apply AMBIENT_WASH preset
    bridge.applyRoutingPreset("AMBIENT_WASH")
    assert bridge.routingPreset == "AMBIENT_WASH"
    assert bridge.chorusToReverb == 1  # REV only

    # 6. Test Ganged Tone Parameter Update (tone_idx = 0) and BOTH assign (mode 2)
    bridge.setToneRoutingParam(0, "level", 95)
    assert bridge.toneOutputLevels == [95, 95, 95, 95]
    assert bridge.routingPreset == "CUSTOM"

    bridge.setMfxSend("dry", 0)
    bridge.setToneRoutingParam(1, "assign", 2)
    assert bridge.toneOutputAssigns[0] == 2
    assert bridge.mfxDrySend == 0  # Setting tone assign to BOTH does not alter MFX main out level

    # 7. Test Name Properties
    assert isinstance(bridge.mfxAlgoName, str)
    assert isinstance(bridge.chorusTypeName, str)
    assert isinstance(bridge.reverbTypeName, str)

    # 8. Test Manual Unlock Toggle
    bridge.setManualRoutingUnlocked(True)
    assert bridge.manualRoutingUnlocked is True
    bridge.setManualRoutingUnlocked(False)
    assert bridge.manualRoutingUnlocked is False


def test_bridge_routing_hardware_sysex_transmission(mock_midi_mgr):
    from src.spectre.ui.bridge import SpectreBridge
    from src.spectre.vector.engine import VectorEngine

    client = JunoClient(mock_midi_mgr)
    client._cached_sound_mode = SoundMode.PATCH
    engine = VectorEngine(juno_client=client)
    bridge = SpectreBridge(engine)

    # 1. Preset application sends DT1 to synth
    mock_midi_mgr.send_juno_sysex.reset_mock()
    bridge.applyRoutingPreset("SERIAL_CHAIN")
    assert mock_midi_mgr.send_juno_sysex.call_count > 0

    # 2. Tone Routing controls send DT1 to synth
    mock_midi_mgr.send_juno_sysex.reset_mock()
    bridge.setToneRoutingParam(1, "assign", 0)  # MFX
    assert mock_midi_mgr.send_juno_sysex.call_count == 1
    pkt = mock_midi_mgr.send_juno_sysex.call_args[0][0]
    # Tone 1 base is 1F 00 20 00, offset 0x0011 -> 1F 00 20 11
    assert pkt[6:10] == [0x1F, 0x00, 0x20, 0x11]
    assert pkt[10] == 0

    mock_midi_mgr.send_juno_sysex.reset_mock()
    bridge.setToneRoutingParam(2, "level", 110)
    assert mock_midi_mgr.send_juno_sysex.call_count == 1
    pkt = mock_midi_mgr.send_juno_sysex.call_args[0][0]
    # Tone 2 base is 1F 00 22 00, offset 0x000C -> 1F 00 22 0C
    assert pkt[6:10] == [0x1F, 0x00, 0x22, 0x0C]
    assert pkt[10] == 110

    mock_midi_mgr.send_juno_sysex.reset_mock()
    bridge.setToneRoutingParam(3, "chorusSend", 75)
    assert mock_midi_mgr.send_juno_sysex.call_count == 1
    pkt = mock_midi_mgr.send_juno_sysex.call_args[0][0]
    # Tone 3 base is 1F 00 24 00, offset 0x000D -> 1F 00 24 0D
    assert pkt[6:10] == [0x1F, 0x00, 0x24, 0x0D]
    assert pkt[10] == 75

    mock_midi_mgr.send_juno_sysex.reset_mock()
    bridge.setToneRoutingParam(4, "reverbSend", 90)
    assert mock_midi_mgr.send_juno_sysex.call_count == 1
    pkt = mock_midi_mgr.send_juno_sysex.call_args[0][0]
    # Tone 4 base is 1F 00 26 00, offset 0x000E -> 1F 00 26 0E
    assert pkt[6:10] == [0x1F, 0x00, 0x26, 0x0E]
    assert pkt[10] == 90

    # 3. MFX send controls send DT1 to synth
    mock_midi_mgr.send_juno_sysex.reset_mock()
    bridge.setMfxSend("dry", 85)
    # Sends to Patch Common MFX + mirrors to Perf Common MFX1
    assert mock_midi_mgr.send_juno_sysex.call_count >= 2

    # 4. Chorus controls send DT1 to synth
    mock_midi_mgr.send_juno_sysex.reset_mock()
    bridge.setChorusParam("level", 64)
    assert mock_midi_mgr.send_juno_sysex.call_count >= 1

    mock_midi_mgr.send_juno_sysex.reset_mock()
    bridge.setChorusParam("toReverb", 2)  # MAIN+REV
    assert mock_midi_mgr.send_juno_sysex.call_count >= 1

    # 5. Reverb controls send DT1 to synth
    mock_midi_mgr.send_juno_sysex.reset_mock()
    bridge.setReverbParam("level", 80)
    assert mock_midi_mgr.send_juno_sysex.call_count >= 1

