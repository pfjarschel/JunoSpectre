"""Unit tests for Roland SysEx protocol engine."""

from src.spectre.core.sysex import (
    ADDR_SETUP,
    ADDR_TEMP_PATCH_PART_1,
    CMD_DT1,
    OFFSET_PATCH_TONE_1,
    OFFSET_PATCH_TONE_2,
    OFFSET_PATCH_TONE_3,
    OFFSET_PATCH_TONE_4,
    RolandSysEx,
    add_address,
    calculate_checksum,
)


def test_roland_manual_checksum_example():
    """Verify checksum against the official Roland MIDI implementation guide (page 64).

    Address: 10 00 04 00
    Data:    02
    Expected Checksum: 0x6A (106)
    """
    payload = [0x10, 0x00, 0x04, 0x00, 0x02]
    assert calculate_checksum(payload) == 0x6A


def test_checksum_boundary_zero():
    """Verify checksum when sum % 128 == 0."""
    # Sum of [0x40, 0x40] is 128 -> (128 - (128 % 128)) % 128 = 0
    payload = [0x40, 0x40]
    assert calculate_checksum(payload) == 0


def test_build_dt1():
    """Verify DT1 packet matches the Roland manual specification."""
    sysex = RolandSysEx(device_id=0x10, model_id=(0x00, 0x00, 0x3A))
    address = (0x10, 0x00, 0x04, 0x00)
    data = [0x02]

    packet = sysex.build_dt1(address, data)
    expected = [0x41, 0x10, 0x00, 0x00, 0x3A, 0x12, 0x10, 0x00, 0x04, 0x00, 0x02, 0x6A]
    assert packet == expected


def test_build_rq1():
    """Verify RQ1 packet for querying Sound Mode (Setup 01 00 00 00, size 00 00 00 01)."""
    sysex = RolandSysEx(device_id=0x10, model_id=(0x00, 0x00, 0x3A))
    address = ADDR_SETUP
    size = (0x00, 0x00, 0x00, 0x01)

    packet = sysex.build_rq1(address, size)
    # Checksum: 128 - ((1 + 1) % 128) = 126 = 0x7E
    expected = [0x41, 0x10, 0x00, 0x00, 0x3A, 0x11, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x7E]
    assert packet == expected


def test_parse_sysex_dt1():
    """Test parsing an incoming DT1 response."""
    raw = [0xF0, 0x41, 0x10, 0x00, 0x00, 0x3A, 0x12, 0x01, 0x00, 0x00, 0x00, 0x00, 0x7F, 0xF7]
    parsed = RolandSysEx.parse(raw)

    assert parsed is not None
    assert parsed.device_id == 0x10
    assert parsed.model_id == (0x00, 0x00, 0x3A)
    assert parsed.command == CMD_DT1
    assert parsed.address == (0x01, 0x00, 0x00, 0x00)
    assert parsed.payload == b"\x00"
    assert parsed.checksum == 0x7F
    assert parsed.is_valid_checksum is True


def test_parse_sysex_invalid_checksum():
    """Test parser detecting invalid checksum."""
    raw = [0xF0, 0x41, 0x10, 0x00, 0x00, 0x3A, 0x12, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0xF7]
    parsed = RolandSysEx.parse(raw)

    assert parsed is not None
    assert parsed.is_valid_checksum is False


def test_tone_address_calculation():
    """Test calculating 4 Tone TVA Level addresses in Patch Mode."""
    base = ADDR_TEMP_PATCH_PART_1

    t1_addr = add_address(base, OFFSET_PATCH_TONE_1)
    t2_addr = add_address(base, OFFSET_PATCH_TONE_2)
    t3_addr = add_address(base, OFFSET_PATCH_TONE_3)
    t4_addr = add_address(base, OFFSET_PATCH_TONE_4)

    assert t1_addr == (0x1F, 0x00, 0x20, 0x00)
    assert t2_addr == (0x1F, 0x00, 0x22, 0x00)
    assert t3_addr == (0x1F, 0x00, 0x24, 0x00)
    assert t4_addr == (0x1F, 0x00, 0x26, 0x00)


def test_lfo2_address_calculation():
    """Test calculating LFO2 addresses beyond 0x007F threshold."""
    base = ADDR_TEMP_PATCH_PART_1
    t1_base = add_address(base, OFFSET_PATCH_TONE_1)

    # LFO2 Delay Time is 0x0100
    addr_delay = add_address(t1_base, 0x0100)
    assert addr_delay == (0x1F, 0x00, 0x21, 0x00)

    # LFO2 Pitch Depth is 0x0105
    addr_pitch = add_address(t1_base, 0x0105)
    assert addr_pitch == (0x1F, 0x00, 0x21, 0x05)

