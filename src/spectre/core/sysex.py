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

# Patch Common Parameter Offsets
PATCH_PARAM_NAME = 0x0000          # 12 ASCII chars (size 12)
PATCH_PARAM_LEVEL = 0x000E         # 0..127
PATCH_PARAM_PAN = 0x000F           # 0..127
PATCH_PARAM_CUTOFF_OFFSET = 0x0022 # 1..127 (-63 .. +63)
PATCH_PARAM_RESONANCE_OFFSET = 0x0023 # 1..127 (-63 .. +63)
PATCH_PARAM_ATTACK_OFFSET = 0x0024 # 1..127 (-63 .. +63)
PATCH_PARAM_RELEASE_OFFSET = 0x0025 # 1..127 (-63 .. +63)


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
