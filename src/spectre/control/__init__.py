"""spectre.control - Hardware profile, MIDI learn, and smooth scaling engine."""

from .models import (
    ControlDefinition,
    ControlType,
    HardwareProfile,
    MidiMessageType,
    ParameterBinding,
    ParameterTarget,
    RelativeEncoderEncoding,
    ScaleMode,
    TargetCategory,
)
from .profiles import DEFAULT_PROFILE_DIR, ProfileManager
from .smooth_scaler import SmoothScaler
from .midi_learn import MidiLearnEngine, build_standard_parameter_registry
from .engine import ControlEvent, MidiControllerEngine

__all__ = [
    "ControlDefinition",
    "ControlType",
    "HardwareProfile",
    "MidiMessageType",
    "ParameterBinding",
    "ParameterTarget",
    "RelativeEncoderEncoding",
    "ScaleMode",
    "TargetCategory",
    "ProfileManager",
    "DEFAULT_PROFILE_DIR",
    "SmoothScaler",
    "MidiLearnEngine",
    "build_standard_parameter_registry",
    "ControlEvent",
    "MidiControllerEngine",
]
