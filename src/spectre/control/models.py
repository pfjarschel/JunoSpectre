"""Data models and enums for hardware profiles, controls, and parameter bindings."""

from __future__ import annotations

import enum
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class ControlType(str, enum.Enum):
    """Type of physical controller hardware element."""
    FADER = "fader"
    POTENTIOMETER = "potentiometer"
    ENCODER = "encoder"
    BUTTON_MOMENTARY = "button_momentary"
    BUTTON_TOGGLE = "button_toggle"


class MidiMessageType(str, enum.Enum):
    """MIDI message type used by a control."""
    CC = "cc"
    NOTE = "note"


class ScaleMode(str, enum.Enum):
    """Parameter tracking and value scaling behavior."""
    SMOOTH = "smooth"                     # Proportional scaling (convergence at extremes)
    CATCH_UP = "catch_up"                 # Pickup threshold (waits until crossed)
    JUMP = "jump"                         # Direct 1:1 takeover
    RELATIVE_DELTA = "relative_delta"     # Delta offset calculated from absolute CC movements
    RELATIVE_CENTER_RESET = "relative_center_reset"  # Endless offset mode centering at 64
    RELATIVE_ENCODER = "relative_encoder" # Hardware relative CC messages


class RelativeEncoderEncoding(str, enum.Enum):
    """Encoding format for hardware relative encoders."""
    BINARY_OFFSET = "binary_offset"       # 65 = +1, 63 = -1 (64 +/- delta)
    TWOS_COMPLEMENT = "twos_complement"   # 1..63 = positive, 127..64 = negative
    SIGN_MAGNITUDE = "sign_magnitude"     # 1..63 = positive, 65..127 = negative


class TargetCategory(str, enum.Enum):
    """Category of destination target."""
    PATCH_COMMON = "patch_common"
    TONE_TVF = "tone_tvf"
    TONE_TVA = "tone_tva"
    TONE_PITCH = "tone_pitch"
    TONE_WAVE = "tone_wave"
    TONE_LFO = "tone_lfo"
    NORMALIZED_PARAM = "normalized_param"
    CUSTOM_SYSEX = "custom_sysex"
    CALLBACK = "callback"


class ParameterTarget(BaseModel):
    """Specification of an internal synth destination."""
    category: TargetCategory
    param_name: str
    tone_index: Optional[int] = Field(default=None, ge=1, le=4)
    display_name: Optional[str] = None
    min_value: float = 0.0
    max_value: float = 127.0
    default_value: float = 64.0
    unit: Optional[str] = None

    @field_validator("tone_index")
    @classmethod
    def validate_tone_index(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 1 or v > 4):
            raise ValueError(f"tone_index must be 1..4, got {v}")
        return v

    @property
    def target_key(self) -> str:
        """Unique identifier key for this parameter target."""
        if self.tone_index is not None:
            return f"tone_{self.tone_index}_{self.param_name}"
        return f"{self.category.value}_{self.param_name}"


class ControlDefinition(BaseModel):
    """Definition of a physical control on a hardware controller."""
    id: str
    name: str
    control_type: ControlType = ControlType.POTENTIOMETER
    message_type: MidiMessageType = MidiMessageType.CC
    channel: Optional[int] = Field(default=None, ge=0, le=15)
    number: int = Field(ge=0, le=127)
    min_value: int = Field(default=0, ge=0, le=127)
    max_value: int = Field(default=127, ge=0, le=127)
    supports_feedback: bool = True


class ParameterBinding(BaseModel):
    """Mapping between a physical control/MIDI event and a parameter target."""
    control_id: Optional[str] = None
    channel: Optional[int] = Field(default=None, ge=0, le=15)
    message_type: MidiMessageType = MidiMessageType.CC
    number: int = Field(ge=0, le=127)
    target: ParameterTarget
    scale_mode: ScaleMode = ScaleMode.SMOOTH
    sensitivity: float = 1.0
    encoder_encoding: RelativeEncoderEncoding = RelativeEncoderEncoding.BINARY_OFFSET
    feedback_enabled: bool = True

    @property
    def match_key(self) -> tuple[Optional[int], str, int]:
        """Lookup key: (channel, message_type, number)."""
        return (self.channel, self.message_type.value, self.number)


class HardwareProfile(BaseModel):
    """Complete hardware controller profile."""
    profile_name: str
    manufacturer: str
    model: str
    version: str = "1.0"
    description: str = ""
    device_match_keywords: List[str] = Field(default_factory=list)
    default_channel: int = Field(default=0, ge=0, le=15)
    controls: Dict[str, ControlDefinition] = Field(default_factory=dict)
    default_bindings: List[ParameterBinding] = Field(default_factory=list)

    def find_control(self, channel: Optional[int], msg_type: MidiMessageType, number: int) -> Optional[ControlDefinition]:
        """Find control definition matching incoming message."""
        for ctrl in self.controls.values():
            if ctrl.message_type == msg_type and ctrl.number == number:
                if ctrl.channel is None or channel is None or ctrl.channel == channel:
                    return ctrl
        return None
