"""Roland System Exclusive (SysEx) protocol engine.

Supports Roland DT1 (Data Set 1) and RQ1 (Data Request 1) protocols,
checksum calculation, memory addressing, and packet parsing for Roland
JUNO-DS and XPS-30 synthesizers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple


# Roland Manufacturer ID
ROLAND_MANUFACTURER_ID = 0x41

# Default Roland Device ID (16 decimal = 0x10 hex, corresponding to Roland UI ID 17)
DEFAULT_DEVICE_ID = 0x10
BROADCAST_DEVICE_ID = 0x7F

# Model IDs
# JUNO-DS 61/76/88 and XPS-30 share the same 3-byte model ID: 00H 00H 3AH
JUNO_DS_MODEL_ID = (0x00, 0x00, 0x3A)
XPS_30_MODEL_ID = JUNO_DS_MODEL_ID

# Command IDs
CMD_RQ1 = 0x11  # Data Request 1
CMD_DT1 = 0x12  # Data Set 1

# System-wide Base Addresses (7-bit address bytes)
ADDR_SETUP = (0x01, 0x00, 0x00, 0x00)
ADDR_SYSTEM = (0x02, 0x00, 0x00, 0x00)

# Temporary Buffers (Safe for real-time live editing, zero flash wear)
ADDR_TEMP_PERFORMANCE = (0x10, 0x00, 0x00, 0x00)
ADDR_TEMP_PERF_PART_1 = (0x11, 0x00, 0x00, 0x00)
ADDR_TEMP_PATCH_PART_1 = (0x1F, 0x00, 0x00, 0x00)
ADDR_TEMP_PATCH_PART_2 = (0x1F, 0x20, 0x00, 0x00)

# Patch Offset Addresses (Offsets from Patch Base)
OFFSET_PATCH_COMMON = (0x00, 0x00, 0x00, 0x00)
OFFSET_PATCH_COMMON_MFX = (0x00, 0x00, 0x02, 0x00)
OFFSET_PATCH_COMMON_CHORUS = (0x00, 0x00, 0x04, 0x00)
OFFSET_PATCH_COMMON_REVERB = (0x00, 0x00, 0x06, 0x00)
OFFSET_PATCH_TMT = (0x00, 0x00, 0x10, 0x00)

# 4-Tone Offsets inside a Patch
OFFSET_PATCH_TONE_1 = (0x00, 0x00, 0x20, 0x00)
OFFSET_PATCH_TONE_2 = (0x00, 0x00, 0x22, 0x00)
OFFSET_PATCH_TONE_3 = (0x00, 0x00, 0x24, 0x00)
OFFSET_PATCH_TONE_4 = (0x00, 0x00, 0x26, 0x00)

# Tone Parameter Offsets (relative to Tone Base)
TONE_PARAM_LEVEL = 0x0000          # 0..127
TONE_PARAM_COARSE_TUNE = 0x0001    # 16..112 (-48 .. +48 semitones)
TONE_PARAM_FINE_TUNE = 0x0002      # 14..114 (-50 .. +50 cents)
TONE_PARAM_PAN = 0x0004            # 0..127 (L64 .. 63R)
TONE_PARAM_DRY_SEND = 0x000C       # 0..127
TONE_PARAM_CHORUS_SEND = 0x000D    # 0..127
TONE_PARAM_REVERB_SEND = 0x000E    # 0..127

# Wave Generator
TONE_PARAM_WAVE_GROUP_TYPE = 0x0027   # 0..3 (INT, EXP, SAMP, MSAM)
TONE_PARAM_WAVE_GROUP_ID = 0x0028     # 4 nibbles (0..16384)
TONE_PARAM_WAVE_NUM_L = 0x002C        # 4 nibbles (0..16384)
TONE_PARAM_WAVE_NUM_R = 0x0030        # 4 nibbles (0..16384)
TONE_PARAM_WAVE_GAIN = 0x0034         # 0..3 (-6, 0, +6, +12 dB)
TONE_PARAM_WAVE_FXM_SWITCH = 0x0035   # 0..1 (OFF, ON)
TONE_PARAM_WAVE_FXM_COLOR = 0x0036    # 0..3 (1..4)
TONE_PARAM_WAVE_FXM_DEPTH = 0x0037    # 0..16

# Pitch Envelope
TONE_PARAM_PITCH_ENV_DEPTH = 0x003A    # 52..76 (-12 .. +12)
TONE_PARAM_PITCH_ENV_VEL_SENS = 0x003B # 1..127 (-63 .. +63)
TONE_PARAM_PITCH_ENV_T1_VEL_SENS = 0x003C # 1..127 (-63 .. +63)
TONE_PARAM_PITCH_ENV_T4_VEL_SENS = 0x003D # 1..127 (-63 .. +63)
TONE_PARAM_PITCH_ENV_TIME_KEYFOLLOW = 0x003E # 14..114 (-100 .. +100)
TONE_PARAM_PITCH_ENV_T1 = 0x003F       # 0..127 (Attack)
TONE_PARAM_PITCH_ENV_T2 = 0x0040       # 0..127 (Decay 1)
TONE_PARAM_PITCH_ENV_T3 = 0x0041       # 0..127 (Decay 2)
TONE_PARAM_PITCH_ENV_T4 = 0x0042       # 0..127 (Release)
TONE_PARAM_PITCH_ENV_L0 = 0x0043       # 1..127 (-63 .. +63)
TONE_PARAM_PITCH_ENV_L1 = 0x0044       # 1..127 (-63 .. +63)
TONE_PARAM_PITCH_ENV_L2 = 0x0045       # 1..127 (-63 .. +63)
TONE_PARAM_PITCH_ENV_L3 = 0x0046       # 1..127 (-63 .. +63)
TONE_PARAM_PITCH_ENV_L4 = 0x0047       # 1..127 (-63 .. +63)

# TVF (Time Variant Filter)
TONE_PARAM_TVF_FILTER_TYPE = 0x0048    # 0..6 (OFF, LPF, BPF, HPF, PKG, LPF2, LPF3)
TONE_PARAM_TVF_CUTOFF = 0x0049         # 0..127
TONE_PARAM_TVF_CUTOFF_KEYFOLLOW = 0x004A # 44..84 (-200 .. +200)
TONE_PARAM_TVF_RESONANCE = 0x004D      # 0..127
TONE_PARAM_TVF_ENV_DEPTH = 0x004F      # 1..127 (-63 .. +63)
TONE_PARAM_TVF_ENV_VEL_SENS = 0x0051   # 1..127 (-63 .. +63)
TONE_PARAM_TVF_ENV_T1 = 0x0055         # 0..127 (Attack)
TONE_PARAM_TVF_ENV_T2 = 0x0056         # 0..127 (Decay 1)
TONE_PARAM_TVF_ENV_T3 = 0x0057         # 0..127 (Decay 2)
TONE_PARAM_TVF_ENV_T4 = 0x0058         # 0..127 (Release)
TONE_PARAM_TVF_ENV_L1 = 0x0059         # 0..127
TONE_PARAM_TVF_ENV_L2 = 0x005A         # 0..127
TONE_PARAM_TVF_ENV_L3 = 0x005B         # 0..127 (Sustain)
TONE_PARAM_TVF_ENV_L4 = 0x005C         # 0..127

# TVA (Time Variant Amplifier)
TONE_PARAM_TVA_LEVEL = 0x005F          # 0..127 (alternate address to 0x0000)
TONE_PARAM_TVA_PAN = 0x0004            # 0..127
TONE_PARAM_TVA_VEL_SENS = 0x0062       # 1..127 (-63 .. +63)
TONE_PARAM_TVA_ENV_T1 = 0x0066         # 0..127 (Attack)
TONE_PARAM_TVA_ENV_T2 = 0x0067         # 0..127 (Decay 1)
TONE_PARAM_TVA_ENV_T3 = 0x0068         # 0..127 (Decay 2)
TONE_PARAM_TVA_ENV_T4 = 0x0069         # 0..127 (Release)
TONE_PARAM_TVA_ENV_L1 = 0x006A         # 0..127
TONE_PARAM_TVA_ENV_L2 = 0x006B         # 0..127
TONE_PARAM_TVA_ENV_L3 = 0x006C         # 0..127 (Sustain)

# Tone LFO 1
TONE_PARAM_LFO1_WAVEFORM = 0x006D      # 0..12
TONE_PARAM_LFO1_RATE = 0x006E          # 0..149 (2 nibbles: 00 6E, 00 6F)
TONE_PARAM_LFO1_PITCH_DEPTH = 0x0077   # 1..127 (-63 .. +63)
TONE_PARAM_LFO1_TVF_DEPTH = 0x0078     # 1..127 (-63 .. +63)
TONE_PARAM_LFO1_DELAY_TIME = 0x0072   # 0..127
TONE_PARAM_LFO1_FADE_MODE = 0x0074    # 0..3 (ON-IN, ON-OUT, OFF-IN, OFF-OUT)
TONE_PARAM_LFO1_FADE_TIME = 0x0075    # 0..127
TONE_PARAM_LFO1_TVA_DEPTH = 0x0079     # 1..127 (-63 .. +63)
TONE_PARAM_LFO1_PAN_DEPTH = 0x007A     # 1..127 (-63 .. +63)

# Tone LFO 2
TONE_PARAM_LFO2_WAVEFORM = 0x007B      # 0..12
TONE_PARAM_LFO2_RATE = 0x007C          # 0..149 (2 nibbles: 00 7C, 00 7D)
TONE_PARAM_LFO2_DELAY_TIME = 0x0100   # 0..127
TONE_PARAM_LFO2_FADE_MODE = 0x0102    # 0..3
TONE_PARAM_LFO2_FADE_TIME = 0x0103    # 0..127
TONE_PARAM_LFO2_PITCH_DEPTH = 0x0105   # 1..127 (-63 .. +63)
TONE_PARAM_LFO2_TVF_DEPTH = 0x0106     # 1..127 (-63 .. +63)
TONE_PARAM_LFO2_TVA_DEPTH = 0x0107     # 1..127 (-63 .. +63)
TONE_PARAM_LFO2_PAN_DEPTH = 0x0108     # 1..127 (-63 .. +63)

# Patch Common Parameter Offsets
PATCH_PARAM_NAME = 0x0000          # 12 ASCII chars (size 12)
PATCH_PARAM_LEVEL = 0x000E         # 0..127
PATCH_PARAM_PAN = 0x000F           # 0..127
PATCH_PARAM_LEGATO_SWITCH = 0x0017 # 0..1 (OFF, ON)
PATCH_PARAM_PORTAMENTO_SWITCH = 0x0019 # 0..1 (OFF, ON)
PATCH_PARAM_PORTAMENTO_TIME = 0x001D # 0..127
PATCH_PARAM_CHORUS_SEND = 0x0017   # Legacy alias for patch common
PATCH_PARAM_REVERB_SEND = 0x0018   # Legacy alias for patch common
PATCH_PARAM_CUTOFF_OFFSET = 0x0022 # 1..127 (-63 .. +63)
PATCH_PARAM_RESONANCE_OFFSET = 0x0023 # 1..127 (-63 .. +63)
PATCH_PARAM_ATTACK_OFFSET = 0x0024 # 1..127 (-63 .. +63)
PATCH_PARAM_RELEASE_OFFSET = 0x0025 # 1..127 (-63 .. +63)
PATCH_PARAM_MATRIX_CTRL_1 = 0x002B # Source, Dest 1..4, Sens 1..4 (size 9)
PATCH_PARAM_MATRIX_CTRL_2 = 0x0034 # Source, Dest 1..4, Sens 1..4 (size 9)
PATCH_PARAM_MATRIX_CTRL_3 = 0x003D # Source, Dest 1..4, Sens 1..4 (size 9)
PATCH_PARAM_MATRIX_CTRL_4 = 0x0046 # Source, Dest 1..4, Sens 1..4 (size 9)

# MFX Parameter Offsets (relative to OFFSET_PATCH_COMMON_MFX)
MFX_PARAM_TYPE = 0x0000
MFX_PARAM_DRY_SEND = 0x0001
MFX_PARAM_CHORUS_SEND = 0x0002
MFX_PARAM_REVERB_SEND = 0x0003
MFX_PARAM_DATA_START = 0x0011

# Chorus Parameter Offsets (relative to OFFSET_PATCH_COMMON_CHORUS)
CHORUS_PARAM_TYPE = 0x0000
CHORUS_PARAM_LEVEL = 0x0001
CHORUS_PARAM_OUTPUT_SELECT = 0x0003
CHORUS_PARAM_DATA_START = 0x0004

# Reverb Parameter Offsets (relative to OFFSET_PATCH_COMMON_REVERB)
REVERB_PARAM_TYPE = 0x0000
REVERB_PARAM_LEVEL = 0x0001
REVERB_PARAM_DATA_START = 0x0003


def pack_4nibbles(val: int) -> list[int]:
    """Convert an integer (0..16384) to 4 Roland 4-bit nibbles."""
    return [
        (val >> 12) & 0x0F,
        (val >> 8) & 0x0F,
        (val >> 4) & 0x0F,
        val & 0x0F,
    ]


def unpack_4nibbles(data: Sequence[int]) -> int:
    """Convert 4 Roland nibbles back to an integer."""
    if len(data) < 4:
        raise ValueError(f"Need 4 nibbles, got {len(data)}")
    return (
        ((data[0] & 0x0F) << 12)
        | ((data[1] & 0x0F) << 8)
        | ((data[2] & 0x0F) << 4)
        | (data[3] & 0x0F)
    )


def pack_2nibbles(val: int) -> list[int]:
    """Convert an integer (0..255) to 2 Roland 4-bit nibbles."""
    return [
        (val >> 4) & 0x0F,
        val & 0x0F,
    ]


def unpack_2nibbles(data: Sequence[int]) -> int:
    """Convert 2 Roland nibbles back to an integer."""
    if len(data) < 2:
        raise ValueError(f"Need 2 nibbles, got {len(data)}")
    return ((data[0] & 0x0F) << 4) | (data[1] & 0x0F)


def calculate_checksum(data: Sequence[int]) -> int:
    """Calculate Roland 7-bit checksum.
    
    Formula from Roland MIDI Implementation:
    sum = sum(address_bytes + data_or_size_bytes)
    remainder = sum % 128
    checksum = (128 - remainder) % 128
    """
    total = sum(data)
    remainder = total % 128
    return (128 - remainder) % 128


def add_address(
    base: Sequence[int],
    offset: Sequence[int] | int,
) -> Tuple[int, int, int, int]:
    """Add a 4-byte Roland address and offset using 7-bit arithmetic (0x00..0x7F per byte)."""
    if len(base) != 4:
        raise ValueError(f"Base address must be 4 bytes, got {len(base)}")
    
    if isinstance(offset, int):
        # Convert integer to 4 bytes in 7-bit chunks
        off_bytes = [
            (offset >> 21) & 0x7F,
            (offset >> 14) & 0x7F,
            (offset >> 7) & 0x7F,
            offset & 0x7F,
        ]
    elif len(offset) == 4:
        off_bytes = list(offset)
    elif len(offset) == 2:
        off_bytes = [0, 0, offset[0], offset[1]]
    else:
        raise ValueError(f"Unsupported offset format: {offset}")

    # Add from LSB to MSB with 7-bit carry
    result = [0, 0, 0, 0]
    carry = 0
    for i in range(3, -1, -1):
        s = base[i] + off_bytes[i] + carry
        result[i] = s & 0x7F
        carry = s >> 7

    return (result[0], result[1], result[2], result[3])


@dataclass(frozen=True)
class ParsedSysEx:
    """Parsed Roland System Exclusive message."""
    device_id: int
    model_id: Tuple[int, ...]
    command: int
    address: Tuple[int, int, int, int]
    payload: bytes
    checksum: int
    is_valid_checksum: bool


class RolandSysEx:
    """Helper for constructing and parsing Roland SysEx messages."""

    def __init__(
        self,
        device_id: int = DEFAULT_DEVICE_ID,
        model_id: Sequence[int] = JUNO_DS_MODEL_ID,
    ):
        self.device_id = device_id
        self.model_id = tuple(model_id)

    def build_dt1(
        self,
        address: Sequence[int],
        data: Sequence[int],
    ) -> list[int]:
        """Construct Roland DT1 (Data Set 1) message body (excluding F0/F7 for mido).
        
        Format:
        [0x41, device_id, model_id..., 0x12, addr[0..3]..., data..., checksum]
        """
        if len(address) != 4:
            raise ValueError(f"Address must be 4 bytes, got {len(address)}")
        
        addr_bytes = list(address)
        data_bytes = list(data)
        checksum = calculate_checksum(addr_bytes + data_bytes)
        
        packet = [ROLAND_MANUFACTURER_ID, self.device_id]
        packet.extend(self.model_id)
        packet.append(CMD_DT1)
        packet.extend(addr_bytes)
        packet.extend(data_bytes)
        packet.append(checksum)
        return packet

    def build_rq1(
        self,
        address: Sequence[int],
        size: Sequence[int],
    ) -> list[int]:
        """Construct Roland RQ1 (Data Request 1) message body (excluding F0/F7 for mido).
        
        Format:
        [0x41, device_id, model_id..., 0x11, addr[0..3]..., size[0..3]..., checksum]
        """
        if len(address) != 4:
            raise ValueError(f"Address must be 4 bytes, got {len(address)}")
        if len(size) != 4:
            raise ValueError(f"Size must be 4 bytes, got {len(size)}")
        
        addr_bytes = list(address)
        size_bytes = list(size)
        checksum = calculate_checksum(addr_bytes + size_bytes)
        
        packet = [ROLAND_MANUFACTURER_ID, self.device_id]
        packet.extend(self.model_id)
        packet.append(CMD_RQ1)
        packet.extend(addr_bytes)
        packet.extend(size_bytes)
        packet.append(checksum)
        return packet

    @staticmethod
    def parse(raw_data: Sequence[int]) -> ParsedSysEx | None:
        """Parse raw SysEx data bytes (excluding or including F0/F7)."""
        data = list(raw_data)
        if data and data[0] == 0xF0:
            data = data[1:]
        if data and data[-1] == 0xF7:
            data = data[:-1]

        # Minimum Roland packet: 0x41, dev, model(3), cmd, addr(4), data(>=1), checksum(1) = 12 bytes
        if len(data) < 12:
            return None
        
        if data[0] != ROLAND_MANUFACTURER_ID:
            return None

        device_id = data[1]
        
        # Check for 3-byte model ID (e.g. 00 00 3A)
        # If command byte is at index 5:
        if data[5] in (CMD_RQ1, CMD_DT1):
            model_id = tuple(data[2:5])
            cmd_index = 5
        # If command byte is at index 6 (4-byte model ID):
        elif len(data) >= 13 and data[6] in (CMD_RQ1, CMD_DT1):
            model_id = tuple(data[2:6])
            cmd_index = 6
        else:
            return None

        cmd = data[cmd_index]
        addr_start = cmd_index + 1
        addr = tuple(data[addr_start : addr_start + 4])
        payload_bytes = data[addr_start + 4 : -1]
        received_checksum = data[-1]

        # Verify checksum
        calc_check = calculate_checksum(list(addr) + payload_bytes)
        is_valid = (calc_check == received_checksum)

        return ParsedSysEx(
            device_id=device_id,
            model_id=model_id,
            command=cmd,
            address=addr,  # type: ignore[arg-type]
            payload=bytes(payload_bytes),
            checksum=received_checksum,
            is_valid_checksum=is_valid,
        )
