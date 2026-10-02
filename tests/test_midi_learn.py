"""Unit tests for MidiLearnEngine and parameter catalog."""

from unittest.mock import MagicMock
import mido
import pytest
from src.spectre.control.midi_learn import MidiLearnEngine, build_standard_parameter_registry
from src.spectre.control.models import (
    MidiMessageType,
    ParameterBinding,
    ParameterTarget,
    ScaleMode,
    TargetCategory,
)


def test_standard_parameter_registry_contents():
    """Verify registry contains expected Tone 1-4 and Patch Common parameters."""
    registry = build_standard_parameter_registry()
    keys = {t.target_key for t in registry}

    # Verify per-tone TVF, TVA, and Pitch parameters
    for tone in range(1, 5):
        assert f"tone_{tone}_cutoff" in keys
        assert f"tone_{tone}_resonance" in keys
        assert f"tone_{tone}_level" in keys
        assert f"tone_{tone}_pan" in keys
        assert f"tone_{tone}_coarse" in keys

    # Verify patch common
    assert "patch_common_level" in keys
    assert "patch_common_cutoff_offset" in keys
    assert "patch_common_resonance_offset" in keys

    # Verify normalized vector params
    assert "normalized_param_vector_x" in keys
    assert "normalized_param_vector_y" in keys


def test_interactive_midi_learn_cc():
    """Test learning a CC message and binding it to Tone 1 Cutoff."""
    engine = MidiLearnEngine()
    target = engine.get_target_by_key("tone_1_cutoff")
    assert target is not None

    callback_mock = MagicMock()
    engine.start_learning(target, scale_mode=ScaleMode.SMOOTH, on_learned=callback_mock)
    assert engine.is_learning

    # Incoming CC 13 on Channel 0
    msg = mido.Message("control_change", channel=0, control=13, value=64)
    binding, consumed = engine.process_midi_message(msg)

    assert consumed is True
    assert binding is not None
    assert binding.number == 13
    assert binding.message_type == MidiMessageType.CC
    assert binding.target.target_key == "tone_1_cutoff"
    assert not engine.is_learning
    callback_mock.assert_called_once_with(binding)

    # Now verify normal routing lookup
    msg2 = mido.Message("control_change", channel=0, control=13, value=75)
    found_binding, was_consumed = engine.process_midi_message(msg2)
    assert not was_consumed
    assert found_binding == binding


def test_interactive_midi_learn_note():
    """Test learning a Note message and binding it to a target."""
    engine = MidiLearnEngine()
    target = engine.get_target_by_key("patch_common_level")

    engine.start_learning(target, scale_mode=ScaleMode.JUMP)
    msg = mido.Message("note_on", channel=1, note=41, velocity=100)
    binding, consumed = engine.process_midi_message(msg)

    assert consumed is True
    assert binding.message_type == MidiMessageType.NOTE
    assert binding.number == 41
    assert binding.scale_mode == ScaleMode.JUMP


def test_bindings_export_and_import(tmp_path):
    """Test saving and loading user bindings to JSON."""
    engine = MidiLearnEngine()
    target = engine.get_target_by_key("tone_2_resonance")
    b1 = ParameterBinding(channel=0, message_type=MidiMessageType.CC, number=30, target=target, scale_mode=ScaleMode.SMOOTH)
    engine.bind(b1)

    export_file = tmp_path / "user_bindings.json"
    engine.export_bindings_to_file(export_file)
    assert export_file.is_file()

    # Create new engine and import
    engine2 = MidiLearnEngine()
    assert len(engine2.list_bindings()) == 0
    engine2.import_bindings_from_file(export_file)

    assert len(engine2.list_bindings()) == 1
    imported_b = engine2.get_binding(channel=0, message_type=MidiMessageType.CC, number=30)
    assert imported_b is not None
    assert imported_b.target.target_key == "tone_2_resonance"
