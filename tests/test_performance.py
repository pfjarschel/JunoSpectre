"""Performance mode: address map, mixer SysEx, playlist links, state round-trip."""

from pathlib import Path
from unittest.mock import MagicMock

import mido
import pytest

from src.spectre.core.midi import MidiDeviceManager
from src.spectre.core.patch_state import PatchState, PerfPartState
from src.spectre.core.protocol import JunoClient, SoundMode
from src.spectre.core.sysex import (
    ADDR_TEMP_PERFORMANCE,
    perf_part_base,
    perf_zone_base,
    temp_perf_patch_base,
)
from src.spectre.core.spectre_format import (
    load_spectre,
    make_playlist_entry,
    patch_state_from_dict,
    patch_state_to_dict,
    playlist_entry_status,
    refresh_entry_snapshot,
    save_spectre,
)


@pytest.fixture
def mock_midi_mgr():
    return MagicMock(spec=MidiDeviceManager)


def _mode_msg(mode: int):
    # DT1 reply: addr 01 00 00 00, data [mode], valid checksum
    addr = [0x01, 0x00, 0x00, 0x00]
    data = [mode]
    chk = (128 - (sum(addr + data) % 128)) % 128
    return mido.Message("sysex", data=[0x41, 0x10, 0x00, 0x00, 0x3A, 0x12] + addr + data + [chk])


def _sent_address(mock_midi_mgr):
    pkt = mock_midi_mgr.send_juno_sysex.call_args[0][0]
    assert pkt[0:6] == [0x41, 0x10, 0x00, 0x00, 0x3A, 0x12]
    return tuple(pkt[6:10]), pkt[10:-1]


# --- address map (MIDI impl 5.1 + Performance tables) -----------------------

def test_perf_part_bases():
    assert perf_part_base(1) == (0x10, 0x00, 0x20, 0x00)
    assert perf_part_base(2) == (0x10, 0x00, 0x21, 0x00)
    assert perf_part_base(16) == (0x10, 0x00, 0x2F, 0x00)
    with pytest.raises(ValueError):
        perf_part_base(0)
    with pytest.raises(ValueError):
        perf_part_base(17)


def test_perf_zone_and_patch_buffer_bases():
    assert perf_zone_base(1) == (0x10, 0x00, 0x50, 0x00)
    assert perf_zone_base(16) == (0x10, 0x00, 0x5F, 0x00)
    assert temp_perf_patch_base(1) == (0x11, 0x00, 0x00, 0x00)
    assert temp_perf_patch_base(2) == (0x11, 0x20, 0x00, 0x00)
    assert temp_perf_patch_base(16) == (0x14, 0x60, 0x00, 0x00)


# --- mixer SysEx ------------------------------------------------------------

def test_set_perf_part_level_address(mock_midi_mgr):
    client = JunoClient(mock_midi_mgr)
    client.set_perf_part_level(3, 100)
    addr, payload = _sent_address(mock_midi_mgr)
    assert addr == (0x10, 0x00, 0x22, 0x07)  # Part 3 base + Level offset
    assert payload == [100]


def test_set_perf_part_pan_and_mute(mock_midi_mgr):
    client = JunoClient(mock_midi_mgr)
    client.set_perf_part_pan(1, 64)
    addr, payload = _sent_address(mock_midi_mgr)
    assert addr == (0x10, 0x00, 0x20, 0x08)
    assert payload == [64]
    client.set_perf_part_mute(5, True)
    addr, payload = _sent_address(mock_midi_mgr)
    assert addr == (0x10, 0x00, 0x24, 0x1B)
    assert payload == [1]


def test_set_perf_solo_targets_common(mock_midi_mgr):
    client = JunoClient(mock_midi_mgr)
    client.set_perf_solo(7)
    addr, payload = _sent_address(mock_midi_mgr)
    assert addr == (ADDR_TEMP_PERFORMANCE[0], ADDR_TEMP_PERFORMANCE[1],
                    ADDR_TEMP_PERFORMANCE[2], 0x0C)
    assert payload == [7]


def test_set_sound_mode_and_part_router(mock_midi_mgr):
    client = JunoClient(mock_midi_mgr)
    mock_midi_mgr.iter_juno_messages.return_value = [_mode_msg(0)]
    assert client.get_active_patch_base() == (0x1F, 0x00, 0x00, 0x00)
    # PERFORM routes deep edits to the selected part buffer
    mock_midi_mgr.iter_juno_messages.return_value = [_mode_msg(1)]
    client.invalidate_cache()
    client.set_active_perf_part(3)
    assert client.get_active_patch_base() == (0x11, 0x40, 0x00, 0x00)
    # Sound mode switch writes Setup 01 00 00 00
    client.set_sound_mode(SoundMode.PERFORM)
    addr, payload = _sent_address(mock_midi_mgr)
    assert addr == (0x01, 0x00, 0x00, 0x00)
    assert payload == [1]


def test_push_pi_only_patch_to_part(mock_midi_mgr):
    client = JunoClient(mock_midi_mgr)
    state = PatchState()
    # Minimal raw image (lengths mirror the canonical region layout).
    state.raw_regions = {
        "common": [bytes(80)],
        "mfx": [bytes(145)],
        "chorus": [bytes(84)],
        "reverb": [bytes(83)],
        "tmt": [bytes(41)],
        **{f"tone_{i}": [bytes(154), bytes(26)] for i in range(1, 5)},
    }
    failures = client.push_patch_to_perf_part(state, 2)
    assert failures == 0
    addr, _ = _sent_address(mock_midi_mgr)
    assert addr[0:2] == (0x11, 0x20)  # Part 2 temp patch buffer


# --- state model ------------------------------------------------------------

def test_perf_part_defaults():
    p = PerfPartState(part_index=4)
    assert p.rx_channel == 3
    assert p.rx_switch is True
    assert p.volume == 100 and p.pan == 64
    assert p.muted is False and p.solo is False


def test_patch_state_perf_fields_round_trip():
    state = PatchState()
    state.perf_name = "LIVE SET"
    state.active_perf_part = 5
    state.perf_parts[0].patch_msb = 85
    restored = patch_state_from_dict(patch_state_to_dict(state))
    assert restored.perf_name == "LIVE SET"
    assert restored.active_perf_part == 5
    assert restored.perf_parts[0].patch_msb == 85
    assert len(restored.perf_parts) == 16


# --- playlist hybrid links --------------------------------------------------

def test_playlist_entry_status_lifecycle(tmp_path: Path):
    state = PatchState()
    state.perf_name = "GIG"
    perf_file = tmp_path / "gig.spectre"
    save_spectre(perf_file, state, kind="performance")
    loaded = load_spectre(perf_file)
    assert loaded["kind"] == "performance"
    entry = make_playlist_entry("Opener", patch_state_to_dict(loaded["patch_state"]),
                                perf_path=str(perf_file))
    assert playlist_entry_status(entry) == "ok"
    # Touch the linked file -> stale badge until refreshed
    state2 = PatchState()
    state2.perf_name = "GIG V2"
    save_spectre(perf_file, state2, kind="performance")
    assert playlist_entry_status(entry) == "updated"
    refresh_entry_snapshot(entry)
    assert playlist_entry_status(entry) == "ok"
    # Missing file still playable from snapshot
    perf_file.unlink()
    assert playlist_entry_status(entry) == "missing"
    assert entry["cached"] is not None


def test_playlist_entry_unsaved_snapshot_only():
    entry = make_playlist_entry("Jam", patch_state_to_dict(PatchState()))
    assert playlist_entry_status(entry) == "unsaved"
