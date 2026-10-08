"""Real-time MIDI controller dispatch engine.

Bridges physical controller inputs, smooth scalers, MIDI learn, and Roland SysEx output.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Dict, Generator, List, Optional, Union

import mido

from ..core.midi import MidiDeviceManager
from ..core.protocol import JunoClient
from .midi_learn import MidiLearnEngine
from .models import (
    HardwareProfile,
    MidiMessageType,
    ParameterBinding,
    ParameterTarget,
    TargetCategory,
)
from .profiles import ProfileManager
from .smooth_scaler import SmoothScaler

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ControlEvent:
    """Event emitted when a control parameter is updated."""
    binding: Optional[ParameterBinding]
    target: Optional[ParameterTarget]
    physical_value: int
    synth_value: int
    normalized_value: float
    is_converged: bool


class MidiControllerEngine:
    """High-level coordinator linking MIDI controller inputs to synth targets."""

    def __init__(
        self,
        midi_mgr: Optional[MidiDeviceManager] = None,
        juno_client: Optional[JunoClient] = None,
        profile_mgr: Optional[ProfileManager] = None,
    ):
        self.midi = midi_mgr
        self.juno = juno_client
        self.profile_mgr = profile_mgr or ProfileManager()
        self.learn = MidiLearnEngine()

        self.active_profile: Optional[HardwareProfile] = None
        self._scalers: Dict[str, SmoothScaler] = {}
        self._subscribers: List[Callable[[ControlEvent], None]] = []

    def subscribe(self, callback: Callable[[ControlEvent], None]) -> None:
        """Register a subscriber callback for control events."""
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[ControlEvent], None]) -> None:
        """Remove a subscriber callback."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def load_profile(self, profile_or_name: Union[HardwareProfile, str]) -> HardwareProfile:
        """Load a hardware profile and initialize its default bindings."""
        if isinstance(profile_or_name, HardwareProfile):
            profile = profile_or_name
        else:
            profile = self.profile_mgr.load_profile(profile_or_name)

        self.active_profile = profile
        self.learn.load_bindings_from_profile(profile, overwrite=True)
        self._scalers.clear()

        # Pre-initialize scalers for all bindings
        for binding in self.learn.list_bindings():
            self._get_or_create_scaler(binding)

        logger.info(f"Loaded hardware profile '{profile.profile_name}' with {len(profile.controls)} controls.")
        return profile

    def auto_detect_profile(self, port_name: Optional[str] = None) -> Optional[HardwareProfile]:
        """Attempt to match a connected controller port to an installed profile."""
        if not port_name and self.midi:
            in_port, _ = self.midi.find_launch_control_ports()
            port_name = in_port

        if not port_name and self.midi:
            inputs = self.midi.get_input_names()
            for inp in inputs:
                matched = self.profile_mgr.match_profile_for_device(inp)
                if matched:
                    return self.load_profile(matched)
            return None

        if port_name:
            matched = self.profile_mgr.match_profile_for_device(port_name)
            if matched:
                return self.load_profile(matched)

        return None

    def _get_or_create_scaler(self, binding: ParameterBinding) -> SmoothScaler:
        """Get or create the SmoothScaler instance for a specific binding."""
        key = binding.target.target_key
        if key not in self._scalers:
            self._scalers[key] = SmoothScaler(
                initial_physical=64,
                initial_synth=binding.target.default_value,
                mode=binding.scale_mode,
                min_value=binding.target.min_value,
                max_value=binding.target.max_value,
                sensitivity=binding.sensitivity,
                encoding=binding.encoder_encoding,
            )
        return self._scalers[key]

    def get_scaler_for_target(self, target_key: str) -> Optional[SmoothScaler]:
        """Retrieve scaler for a target key."""
        return self._scalers.get(target_key)

    def sync_from_synth(self) -> None:
        """Query synth parameter values and synchronize all active scalers."""
        if not self.juno:
            logger.warning("Cannot sync from synth: JunoClient not configured.")
            return

        try:
            # Query tone levels
            levels = self.juno.get_tone_levels(timeout=0.5)
            for idx, lvl in enumerate(levels, start=1):
                scaler = self.get_scaler_for_target(f"tone_{idx}_level")
                if scaler:
                    scaler.sync_synth_value(lvl)
                    if self.midi and self.active_profile:
                        self._send_feedback_for_target(f"tone_{idx}_level", lvl)

            logger.info(f"Synchronized with synth: Tone levels = {levels}")
        except Exception as e:
            logger.warning(f"Synth synchronization partially failed or timed out: {e}")

    def _send_feedback_for_target(self, target_key: str, value: int) -> None:
        """Send feedback message to controller for a target parameter."""
        if not self.midi or not self.active_profile:
            return

        for binding in self.learn.list_bindings():
            if binding.target.target_key == target_key and binding.feedback_enabled:
                if binding.message_type == MidiMessageType.CC:
                    ch = binding.channel if binding.channel is not None else 0
                    self.midi.send_controller_cc(binding.number, value, channel=ch)

    def process_message(self, msg: mido.Message) -> Optional[ControlEvent]:
        """Process incoming MIDI message from the controller."""
        binding, was_consumed = self.learn.process_midi_message(msg)
        if was_consumed and binding is not None:
            logger.info(f"Learned binding: {binding.target.target_key} on {binding.message_type.value} #{binding.number}")
            return None

        if not binding:
            return None

        # Extract incoming physical value
        if msg.type == "control_change":
            raw_val = msg.value
        elif msg.type == "note_on":
            raw_val = msg.velocity
        else:
            return None

        scaler = self._get_or_create_scaler(binding)
        synth_int, has_changed, needs_recenter = scaler.process(raw_val)

        # Handle center-reset mode for endless knobs
        if needs_recenter and self.midi and binding.feedback_enabled:
            ch = binding.channel if binding.channel is not None else 0
            self.midi.send_controller_cc(binding.number, 64, channel=ch)

        if not has_changed:
            return None

        # Dispatch value to target
        self._dispatch_to_synth(binding.target, synth_int)

        # Calculate normalized value (0.0 .. 1.0)
        span = max(1e-6, binding.target.max_value - binding.target.min_value)
        norm_val = (synth_int - binding.target.min_value) / span

        event = ControlEvent(
            binding=binding,
            target=binding.target,
            physical_value=raw_val,
            synth_value=synth_int,
            normalized_value=norm_val,
            is_converged=scaler.is_converged,
        )

        # Notify subscribers
        for sub in self._subscribers:
            try:
                sub(event)
            except Exception as e:
                logger.error(f"Error in control event subscriber: {e}")

        return event

    def _dispatch_to_synth(self, target: ParameterTarget, value: int) -> None:
        """Send SysEx command to the Roland synth."""
        if not self.juno:
            return

        try:
            cat = target.category
            param = target.param_name
            t_idx = target.tone_index

            if cat == TargetCategory.PATCH_COMMON:
                self.juno.set_patch_param(param, value)
            elif cat == TargetCategory.TONE_TVA and t_idx:
                if param == "level":
                    self.juno.set_tone_level(t_idx, value)
                elif param == "pan":
                    self.juno.set_tone_tva(t_idx, pan=value)
                elif param == "attack":
                    self.juno.set_tone_tva(t_idx, attack=value)
                elif param == "decay":
                    self.juno.set_tone_tva(t_idx, decay=value)
                elif param == "sustain":
                    self.juno.set_tone_tva(t_idx, sustain=value)
                elif param == "release":
                    self.juno.set_tone_tva(t_idx, release=value)
            elif cat == TargetCategory.TONE_TVF and t_idx:
                if param == "cutoff":
                    self.juno.set_tone_tvf(t_idx, cutoff=value)
                elif param == "resonance":
                    self.juno.set_tone_tvf(t_idx, resonance=value)
                elif param == "env_depth":
                    self.juno.set_tone_tvf(t_idx, env_depth=value)
                elif param == "attack":
                    self.juno.set_tone_tvf(t_idx, attack=value)
                elif param == "decay":
                    self.juno.set_tone_tvf(t_idx, decay=value)
                elif param == "sustain":
                    self.juno.set_tone_tvf(t_idx, sustain=value)
                elif param == "release":
                    self.juno.set_tone_tvf(t_idx, release=value)
            elif cat == TargetCategory.TONE_PITCH and t_idx:
                if param == "coarse":
                    self.juno.set_tone_pitch(t_idx, coarse=value)
                elif param == "fine":
                    self.juno.set_tone_pitch(t_idx, fine=value)
            elif cat == TargetCategory.TONE_LFO and t_idx:
                if param.startswith("lfo1_"):
                    sub_p = param.replace("lfo1_", "")
                    kwargs = {sub_p: value}
                    self.juno.set_tone_lfo(t_idx, lfo_index=1, **kwargs)
                elif param.startswith("lfo2_"):
                    sub_p = param.replace("lfo2_", "")
                    kwargs = {sub_p: value}
                    self.juno.set_tone_lfo(t_idx, lfo_index=2, **kwargs)
        except Exception as e:
            logger.error(f"Failed to dispatch parameter {target.target_key} to synth: {e}")

    def poll(self) -> Generator[ControlEvent, None, None]:
        """Poll and process any pending messages from the controller."""
        if not self.midi:
            return

        for msg in self.midi.iter_lcxl_messages():
            evt = self.process_message(msg)
            if evt:
                yield evt
