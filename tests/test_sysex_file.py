"""Tests for .syx bulk encode/apply (JunoClient) and USB bridge slots."""

from unittest.mock import MagicMock

import pytest

from src.spectre.core.patch_state import PatchState
from src.spectre.core.protocol import JunoClient
from src.spectre.core.sysex import CMD_DT1, RolandSysEx

TEMP = (0x1F, 0x00, 0x00, 0x00)


def _template_state():
    state = PatchState.from_template_file()
    assert state is not None and state.raw_regions
    return state


def _real_client():
    client = JunoClient(MagicMock())
    client.get_active_patch_base = MagicMock(return_value=TEMP)
    return client


def test_encode_produces_valid_dt1_sequence():
    client = _real_client()
    blob = client.encode_patch_sysex(_template_state())
    assert blob[0] == 0xF0 and blob[-1] == 0xF7
    messages = JunoClient.split_sysex_blob(blob)
    # common + mfx + chorus + reverb + tmt + 8 tone chunks
    assert len(messages) == 13
    for message in messages:
        parsed = RolandSysEx.parse(message)
        assert parsed is not None and parsed.is_valid_checksum
        assert parsed.command == CMD_DT1
        assert parsed.address[0] == 0x1F
    first = RolandSysEx.parse(messages[0])
    assert bytes(first.payload[:12]) == b"JUNO SPECTRE"


def test_encode_requires_raw_image():
    client = _real_client()
    state = PatchState.from_template_file()
    state.raw_regions = {}
    with pytest.raises(ValueError):
        client.encode_patch_sysex(state)


def test_split_handles_garbage():
    blob = b"\x00\x00" + b"\xF0\x41\xF7" + b"junk" + b"\xF0\x41\xF7trailing"
    assert len(JunoClient.split_sysex_blob(blob)) == 2


def test_apply_rebases_and_skips_invalid():
    client = _real_client()
    sent = []
    client.send_data = lambda address, data: sent.append((tuple(address), bytes(data)))
    blob = client.encode_patch_sysex(_template_state())
    # Corrupt one message's checksum: it must be skipped.
    messages = JunoClient.split_sysex_blob(blob)
    bad = bytearray(messages[0])
    bad[-2] ^= 0x01
    blob = bytes(bad) + b"".join(messages[1:])
    applied = client.apply_sysex_blob(blob, base=(0x11, 0x00, 0x00, 0x00))
    assert applied == len(messages) - 1
    # High two address bytes rebased onto the performance part base.
    assert all(a[0] == 0x11 and a[1] == 0x00 for a, _ in sent)
    # Low bytes (intra-patch offsets) preserved from the file.
    first_file = RolandSysEx.parse(messages[1])
    assert sent[0][0][2:] == first_file.address[2:]


