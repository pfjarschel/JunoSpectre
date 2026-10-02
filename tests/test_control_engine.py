"""Integration tests for MidiControllerEngine linking MIDI, Scaler, and JunoClient."""

from unittest.mock import MagicMock
import mido
import pytest
from src.spectre.core.midi import MidiDeviceManager
from src.spectre.core.protocol import JunoClient
from src.spectre.control.engine import MidiControllerEngine, ControlEvent
from src.spectre.control.models import ScaleMode, ParameterTarget, TargetCategory, ParameterBinding, MidiMessageType


@pytest.fixture
def mock_midi():
    midi = MagicMock(spec=MidiDeviceManager)
    midi.find_launch_control_ports.return_value = ("Launch Control XL In", "Launch Control XL Out")
    midi.get_input_names.return_value = ["Launch Control XL In"]
    return midi


@pytest.fixture
def mock_juno():
    juno = MagicMock(spec=JunoClient)
    juno.get_tone_levels.return_value = (80, 70, 60, 50)
    return juno


def test_controller_engine_profile_loading_and_dispatch(mock_midi, mock_juno):
    """Test loading Novation LC XL profile and dispatching fader movements to JunoClient."""
    engine = MidiControllerEngine(midi_mgr=mock_midi, juno_client=mock_juno)
    profile = engine.load_profile("novation_lc_xl")
    assert profile.profile_name == "Novation Launch Control XL"

    # Subscriber spy
    received_events = []
    engine.subscribe(lambda evt: received_events.append(evt))

    # Send Fader 1 (CC 77 on Channel 0) = 100
    msg = mido.Message("control_change", channel=0, control=77, value=100)
    event = engine.process_message(msg)

    assert event is not None
    assert event.physical_value == 100
    assert event.target.target_key == "tone_1_level"
    assert len(received_events) == 1

    # JunoClient set_tone_level should have been called
    mock_juno.set_tone_level.assert_called_with(1, event.synth_value)


def test_controller_engine_center_reset_mode(mock_midi, mock_juno):
    """Test endless knob in center-reset mode triggers synth update and CC 64 feedback."""
    engine = MidiControllerEngine(midi_mgr=mock_midi, juno_client=mock_juno)
    engine.load_profile("novation_lc_xl")

    # Knob Send A 1 is CC 13 (Tone 1 Cutoff, relative_center_reset mode)
    # User turns clockwise: controller sends 66 (+2)
    msg = mido.Message("control_change", channel=0, control=13, value=66)
    event = engine.process_message(msg)

    assert event is not None
    assert event.physical_value == 66
    assert event.target.param_name == "cutoff"

    # Verify JunoClient received cutoff change
    mock_juno.set_tone_tvf.assert_called_with(1, cutoff=event.synth_value)

    # Verify CC 64 feedback was sent back to the controller
    mock_midi.send_controller_cc.assert_called_with(13, 64, channel=0)


def test_controller_engine_sync_from_synth(mock_midi, mock_juno):
    """Test synchronizing scalers with synth tone levels and updating controller."""
    engine = MidiControllerEngine(midi_mgr=mock_midi, juno_client=mock_juno)
    engine.load_profile("novation_lc_xl")

    # Tone levels from mock: (80, 70, 60, 50)
    engine.sync_from_synth()

    mock_juno.get_tone_levels.assert_called_once()

    # Check scaler for tone 1 level has been initialized to 80
    scaler1 = engine.get_scaler_for_target("tone_1_level")
    assert scaler1 is not None
    assert scaler1.synth_value == 80

    # Check scaler for tone 2 level has been initialized to 70
    scaler2 = engine.get_scaler_for_target("tone_2_level")
    assert scaler2 is not None
    assert scaler2.synth_value == 70

    # Controller feedback should have been sent for faders 1..4 (CC 77..80)
    mock_midi.send_controller_cc.assert_any_call(77, 80, channel=0)
    mock_midi.send_controller_cc.assert_any_call(78, 70, channel=0)
    mock_midi.send_controller_cc.assert_any_call(79, 60, channel=0)
    mock_midi.send_controller_cc.assert_any_call(80, 50, channel=0)
