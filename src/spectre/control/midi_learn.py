"""Interactive MIDI Learn engine and dynamic routing table.

Allows listening to incoming CC/Note messages to dynamically bind external controls
to internal Roland synth and vector engine parameters.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Union

import mido

from .models import (
    HardwareProfile,
    MidiMessageType,
    ParameterBinding,
    ParameterTarget,
    ScaleMode,
    TargetCategory,
)

logger = logging.getLogger(__name__)


def build_standard_parameter_registry() -> List[ParameterTarget]:
    """Build the comprehensive catalog of all controllable Roland parameters."""
    registry: List[ParameterTarget] = []

    # 1. Patch Common
    commons = [
        ("level", "Master Level", 0.0, 127.0, 100.0, ""),
        ("pan", "Master Pan", 0.0, 127.0, 64.0, ""),
        ("cutoff_offset", "Filter Cutoff Offset", 1.0, 127.0, 64.0, ""),
        ("resonance_offset", "Filter Resonance Offset", 1.0, 127.0, 64.0, ""),
        ("attack_offset", "Amp Attack Offset", 1.0, 127.0, 64.0, ""),
        ("release_offset", "Amp Release Offset", 1.0, 127.0, 64.0, ""),
        ("chorus_send", "Chorus Send", 0.0, 127.0, 0.0, ""),
        ("reverb_send", "Reverb Send", 0.0, 127.0, 40.0, ""),
    ]
    for param, name, min_v, max_v, def_v, unit in commons:
        registry.append(
            ParameterTarget(
                category=TargetCategory.PATCH_COMMON,
                param_name=param,
                display_name=f"Patch {name}",
                min_value=min_v,
                max_value=max_v,
                default_value=def_v,
                unit=unit,
            )
        )

    # 2. Per-Tone Parameters (Tones 1 to 4)
    for tone in range(1, 5):
        # TVF (Filter)
        registry.append(ParameterTarget(category=TargetCategory.TONE_TVF, param_name="cutoff", tone_index=tone, display_name=f"Tone {tone} Cutoff", min_value=0, max_value=127, default_value=64))
        registry.append(ParameterTarget(category=TargetCategory.TONE_TVF, param_name="resonance", tone_index=tone, display_name=f"Tone {tone} Resonance", min_value=0, max_value=127, default_value=0))
        registry.append(ParameterTarget(category=TargetCategory.TONE_TVF, param_name="env_depth", tone_index=tone, display_name=f"Tone {tone} Filter Env Depth", min_value=1, max_value=127, default_value=64))
        registry.append(ParameterTarget(category=TargetCategory.TONE_TVF, param_name="filter_type", tone_index=tone, display_name=f"Tone {tone} Filter Type", min_value=0, max_value=6, default_value=1))
        registry.append(ParameterTarget(category=TargetCategory.TONE_TVF, param_name="attack", tone_index=tone, display_name=f"Tone {tone} Filter Attack", min_value=0, max_value=127, default_value=0))
        registry.append(ParameterTarget(category=TargetCategory.TONE_TVF, param_name="decay", tone_index=tone, display_name=f"Tone {tone} Filter Decay", min_value=0, max_value=127, default_value=64))
        registry.append(ParameterTarget(category=TargetCategory.TONE_TVF, param_name="sustain", tone_index=tone, display_name=f"Tone {tone} Filter Sustain", min_value=0, max_value=127, default_value=127))
        registry.append(ParameterTarget(category=TargetCategory.TONE_TVF, param_name="release", tone_index=tone, display_name=f"Tone {tone} Filter Release", min_value=0, max_value=127, default_value=64))

        # TVA (Amp)
        registry.append(ParameterTarget(category=TargetCategory.TONE_TVA, param_name="level", tone_index=tone, display_name=f"Tone {tone} TVA Level", min_value=0, max_value=127, default_value=100))
        registry.append(ParameterTarget(category=TargetCategory.TONE_TVA, param_name="pan", tone_index=tone, display_name=f"Tone {tone} Pan", min_value=0, max_value=127, default_value=64))
        registry.append(ParameterTarget(category=TargetCategory.TONE_TVA, param_name="attack", tone_index=tone, display_name=f"Tone {tone} Amp Attack", min_value=0, max_value=127, default_value=0))
        registry.append(ParameterTarget(category=TargetCategory.TONE_TVA, param_name="decay", tone_index=tone, display_name=f"Tone {tone} Amp Decay", min_value=0, max_value=127, default_value=64))
        registry.append(ParameterTarget(category=TargetCategory.TONE_TVA, param_name="sustain", tone_index=tone, display_name=f"Tone {tone} Amp Sustain", min_value=0, max_value=127, default_value=127))
        registry.append(ParameterTarget(category=TargetCategory.TONE_TVA, param_name="release", tone_index=tone, display_name=f"Tone {tone} Amp Release", min_value=0, max_value=127, default_value=64))

        # Pitch
        registry.append(ParameterTarget(category=TargetCategory.TONE_PITCH, param_name="coarse", tone_index=tone, display_name=f"Tone {tone} Coarse Tune", min_value=16, max_value=112, default_value=64))
        registry.append(ParameterTarget(category=TargetCategory.TONE_PITCH, param_name="fine", tone_index=tone, display_name=f"Tone {tone} Fine Tune", min_value=14, max_value=114, default_value=64))

        # Wave
        registry.append(ParameterTarget(category=TargetCategory.TONE_WAVE, param_name="wave_num", tone_index=tone, display_name=f"Tone {tone} Waveform Number", min_value=0, max_value=16384, default_value=1))
        registry.append(ParameterTarget(category=TargetCategory.TONE_WAVE, param_name="gain", tone_index=tone, display_name=f"Tone {tone} Wave Gain", min_value=0, max_value=3, default_value=1))

        # LFO 1 & 2
        registry.append(ParameterTarget(category=TargetCategory.TONE_LFO, param_name="lfo1_rate", tone_index=tone, display_name=f"Tone {tone} LFO 1 Rate", min_value=0, max_value=149, default_value=80))
        registry.append(ParameterTarget(category=TargetCategory.TONE_LFO, param_name="lfo1_tvf_depth", tone_index=tone, display_name=f"Tone {tone} LFO 1 Filter Depth", min_value=1, max_value=127, default_value=64))
        registry.append(ParameterTarget(category=TargetCategory.TONE_LFO, param_name="lfo1_pitch_depth", tone_index=tone, display_name=f"Tone {tone} LFO 1 Pitch Depth", min_value=1, max_value=127, default_value=64))

    # 3. Vector & Normalized Parameters (for Phase 3)
    registry.append(ParameterTarget(category=TargetCategory.NORMALIZED_PARAM, param_name="vector_x", display_name="2D Vector X (Crossfade)", min_value=0.0, max_value=1.0, default_value=0.5))
    registry.append(ParameterTarget(category=TargetCategory.NORMALIZED_PARAM, param_name="vector_y", display_name="2D Vector Y (Crossfade)", min_value=0.0, max_value=1.0, default_value=0.5))

    return registry


class MidiLearnEngine:
    """Manages dynamic parameter bindings and interactive MIDI learn mode."""

    def __init__(self):
        self._parameter_registry = {target.target_key: target for target in build_standard_parameter_registry()}
        # Primary lookup table: (channel, message_type_str, number) -> ParameterBinding
        self._bindings: Dict[Tuple[Optional[int], str, int], ParameterBinding] = {}

        # Interactive learn state
        self._is_learning: bool = False
        self._learn_target: Optional[ParameterTarget] = None
        self._learn_scale_mode: ScaleMode = ScaleMode.SMOOTH
        self._learn_callback: Optional[Callable[[ParameterBinding], None]] = None

    @property
    def is_learning(self) -> bool:
        """Whether MIDI learn is actively waiting for an incoming message."""
        return self._is_learning

    @property
    def current_learn_target(self) -> Optional[ParameterTarget]:
        """Target currently being learned."""
        return self._learn_target

    def get_registered_targets(self) -> List[ParameterTarget]:
        """Return list of all registered synth and vector targets."""
        return list(self._parameter_registry.values())

    def get_target_by_key(self, target_key: str) -> Optional[ParameterTarget]:
        """Look up target by key (e.g. 'tone_1_cutoff', 'patch_common_level')."""
        return self._parameter_registry.get(target_key)

    def start_learning(
        self,
        target: ParameterTarget,
        scale_mode: ScaleMode = ScaleMode.SMOOTH,
        on_learned: Optional[Callable[[ParameterBinding], None]] = None,
    ) -> None:
        """Enter interactive learn mode for a target parameter."""
        self._is_learning = True
        self._learn_target = target
        self._learn_scale_mode = scale_mode
        self._learn_callback = on_learned
        logger.info(f"MIDI Learn active: Waiting for control message for '{target.display_name or target.target_key}'")

    def cancel_learning(self) -> None:
        """Cancel active learn mode."""
        self._is_learning = False
        self._learn_target = None
        self._learn_callback = None
        logger.info("MIDI Learn canceled.")

    def bind(self, binding: ParameterBinding) -> None:
        """Register a parameter binding."""
        key = binding.match_key
        self._bindings[key] = binding
        logger.debug(f"Bound MIDI {key} -> {binding.target.target_key} ({binding.scale_mode.value})")

    def unbind(self, channel: Optional[int], message_type: MidiMessageType, number: int) -> bool:
        """Remove a binding by its MIDI signature."""
        key = (channel, message_type.value, number)
        if key in self._bindings:
            del self._bindings[key]
            return True
        return False

    def clear_bindings(self) -> None:
        """Remove all active bindings."""
        self._bindings.clear()

    def get_binding(self, channel: Optional[int], message_type: MidiMessageType, number: int) -> Optional[ParameterBinding]:
        """Look up binding for an incoming MIDI message."""
        # Check specific channel first
        exact_key = (channel, message_type.value, number)
        if exact_key in self._bindings:
            return self._bindings[exact_key]

        # Check wildcard channel
        wildcard_key = (None, message_type.value, number)
        if wildcard_key in self._bindings:
            return self._bindings[wildcard_key]

        return None

    def list_bindings(self) -> List[ParameterBinding]:
        """Return list of all active bindings."""
        return list(self._bindings.values())

    def load_bindings_from_profile(self, profile: HardwareProfile, overwrite: bool = True) -> None:
        """Load default bindings from a hardware profile."""
        if overwrite:
            self.clear_bindings()
        for b in profile.default_bindings:
            self.bind(b)

    def export_bindings_to_file(self, path: Union[str, Path]) -> None:
        """Save active bindings to a JSON file."""
        data = [b.model_dump(exclude_none=True) for b in self.list_bindings()]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def import_bindings_from_file(self, path: Union[str, Path], overwrite: bool = True) -> None:
        """Load bindings from a JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if overwrite:
            self.clear_bindings()
        for item in data:
            binding = ParameterBinding.model_validate(item)
            self.bind(binding)

    def process_midi_message(self, msg: mido.Message) -> Tuple[Optional[ParameterBinding], bool]:
        """Process incoming MIDI message through learn engine.

        Returns:
            Tuple of (binding_if_found_or_learned, was_consumed_by_learning)
        """
        if msg.type not in ("control_change", "note_on"):
            return None, False

        msg_type = MidiMessageType.CC if msg.type == "control_change" else MidiMessageType.NOTE
        number = msg.control if msg_type == MidiMessageType.CC else msg.note
        channel = msg.channel

        if self._is_learning and self._learn_target is not None:
            # Create binding
            binding = ParameterBinding(
                channel=channel,
                message_type=msg_type,
                number=number,
                target=self._learn_target,
                scale_mode=self._learn_scale_mode,
            )
            self.bind(binding)

            cb = self._learn_callback
            self.cancel_learning()
            if cb:
                try:
                    cb(binding)
                except Exception as e:
                    logger.error(f"Error in learn callback: {e}")

            return binding, True

        # Normal routing lookup
        return self.get_binding(channel, msg_type, number), False
