"""Core modules for SysEx communication, MIDI transport, and hardware control."""

from .sysex import RolandSysEx, calculate_checksum
from .midi import MidiDeviceManager
from .protocol import JunoClient, SoundMode
from ..control.smooth_scaler import SmoothScaler
from ..control.midi_learn import MidiLearnEngine

__all__ = [
    "RolandSysEx",
    "calculate_checksum",
    "MidiDeviceManager",
    "JunoClient",
    "SoundMode",
    "SmoothScaler",
    "MidiLearnEngine",
]

