"""Tests for user flash slot read/write/rename (JunoClient, mock transport)."""

from unittest.mock import MagicMock

import pytest

from src.spectre.core.protocol import JunoClient


@pytest.fixture
def client():
    mgr = MagicMock()
    return JunoClient(mgr)


def test_user_slot_base_validation(client):
    assert JunoClient.user_slot_base(87, 0, 0) == (0x30, 0, 0, 0)
    assert JunoClient.user_slot_base(87, 1, 127) == (0x31, 127, 0, 0)
    with pytest.raises(ValueError):
        JunoClient.user_slot_base(87, 64, 0)  # preset bank is ROM
    with pytest.raises(ValueError):
        JunoClient.user_slot_base(86, 0, 0)
    with pytest.raises(ValueError):
        JunoClient.user_slot_base(87, 0, 128)


def _template_store(client, base):
    """Populate a fake device store from the golden template at `base`."""
    payload = JunoClient.load_init_template()
    assert payload is not None
    store = {}
    for _, address, expected in JunoClient._expected_template_writes(payload, base):
        store[tuple(address)] = bytes(expected)
    return store


def test_read_user_patch_assembles_template(client, monkeypatch):
    base = JunoClient.user_slot_base(87, 0, 75)
    store = _template_store(client, base)

    def fake_request(address, size, timeout=1.0):
        length = (size[0] << 21) | (size[1] << 14) | (size[2] << 7) | size[3]
        data = store.get(tuple(address))
        assert data is not None, f"unexpected RQ1 {tuple(address)}"
        return bytes(data[:length])

    monkeypatch.setattr(client, "request_data", fake_request)
    state = client.read_user_patch(87, 0, 75, timeout=0.1)
    assert state.common.name == "JUNO SPECTRE"
    assert [t.wave_num_l for t in state.tones] == [579, 600, 622, 625]
    assert set(state.raw_regions.keys()) >= {"common", "tone_1", "mfx", "chorus", "reverb", "tmt"}


def test_write_user_patch_targets_flash_and_verifies(client, monkeypatch):
    base = JunoClient.user_slot_base(87, 0, 75)
    store = _template_store(client, base)
    sent = []

    def fake_send(address, data):
        sent.append(tuple(address))
        store[tuple(address)] = bytes(data)

    def fake_request(address, size, timeout=1.0):
        length = (size[0] << 21) | (size[1] << 14) | (size[2] << 7) | size[3]
        return bytes(store.get(tuple(address), b"\x00" * length)[:length])

    monkeypatch.setattr(client, "send_data", fake_send)
    monkeypatch.setattr(client, "request_data", fake_request)
    monkeypatch.setattr(JunoClient, "FLASH_SETTLE_S", 0.0)

    state = client.read_user_patch(87, 0, 75, timeout=0.1)
    state.common.name = "SCRATCH WR"
    mismatches = client.write_user_patch(state, 87, 0, 75, timeout=0.1)
    assert mismatches == []
    # All writes went to the flash user area, never temp RAM.
    assert sent, "expected DT1 writes"
    assert all(a[0] == 0x30 for a in sent)
    assert all(a[0] not in (0x1F, 0x11) for a in sent)
    # Name traveled inside the image.
    assert store[(0x30, 75, 0, 0)][:12] == b"SCRATCH WR  "


def test_write_user_patch_detects_mismatch(client, monkeypatch):
    client.send_data = MagicMock()  # writes go nowhere
    client.request_data = MagicMock(return_value=bytes(80))  # flash reads back zeros
    monkeypatch.setattr(JunoClient, "FLASH_SETTLE_S", 0.0)
    from src.spectre.core.patch_state import PatchState
    state = PatchState.from_template_file() or PatchState.create_init_patch()
    # Give it a raw image so there is something to compare.
    base = JunoClient.user_slot_base(87, 0, 75)
    store = _template_store(client, base)
    import contextlib
    with contextlib.suppress(Exception):
        pass
    # Build raw_regions from the template store via a read with real data,
    # then verify against zeros.
    client.request_data = MagicMock(side_effect=lambda a, s, timeout=1.0: bytes(
        store.get(tuple(a), b"\x00" * 256))[:((s[0] << 21) | (s[1] << 14) | (s[2] << 7) | s[3])])
    state = client.read_user_patch(87, 0, 75, timeout=0.1)
    client.request_data = MagicMock(return_value=bytes(256))
    mismatches = client.write_user_patch(state, 87, 0, 75, timeout=0.1)
    assert mismatches, "expected mismatch labels against zeroed flash"


def test_write_requires_raw_image(client):
    from src.spectre.core.patch_state import PatchState
    state = PatchState.create_init_patch()
    state.raw_regions = {}
    with pytest.raises(ValueError):
        client.write_user_patch(state, 87, 0, 75)


def test_rename_user_slot_writes_name_only(client, monkeypatch):
    sent = {}

    def fake_send(address, data):
        sent[tuple(address)] = bytes(data)

    def fake_request(address, size, timeout=1.0):
        return sent.get(tuple(address), b" " * 12)

    monkeypatch.setattr(client, "send_data", fake_send)
    monkeypatch.setattr(client, "request_data", fake_request)
    monkeypatch.setattr(JunoClient, "FLASH_SETTLE_S", 0.0)
    assert client.rename_user_slot(87, 0, 75, "NEW NAME", timeout=0.1) is True
    assert sent[(0x30, 75, 0, 0)] == b"NEW NAME    "
    # Temp RAM untouched.
    assert all(a[0] != 0x1F for a in sent)
