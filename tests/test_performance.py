"""Performance mode: address map, mixer SysEx, playlist links, state round-trip."""

from pathlib import Path
from unittest.mock import MagicMock

import mido
import pytest

from src.spectre.core.midi import MidiDeviceManager
from src.spectre.core.patch_state import PatchState, PerfPartState
from src.spectre.core.protocol import JunoClient, SoundMode
from src.spectre.core.spectre_format import (
    load_spectre,
    make_playlist_entry,
    patch_state_from_dict,
    patch_state_to_dict,
    playlist_entry_status,
    refresh_entry_snapshot,
    save_spectre,
)
from src.spectre.core.sysex import (
    ADDR_TEMP_PERFORMANCE,
    perf_part_base,
    perf_zone_base,
    temp_perf_patch_base,
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


def test_patch_file_link_round_trip():
    state = PatchState()
    state.perf_parts[2].patch_file = "/tmp/x.spectre"
    state.perf_parts[2].patch_name = "Linked"
    restored = patch_state_from_dict(patch_state_to_dict(state))
    assert restored.perf_parts[2].patch_file == "/tmp/x.spectre"
    assert restored.perf_parts[2].patch_name == "Linked"


def test_playlist_entry_unsaved_snapshot_only():
    entry = make_playlist_entry("Jam", patch_state_to_dict(PatchState()))
    assert playlist_entry_status(entry) == "unsaved"


# --- bridge: file loads, pick mode, performance saves -----------------------

def _bridge_rig(tmp_path):
    from src.spectre.core.sysex import DEFAULT_DEVICE_ID, JUNO_DS_MODEL_ID, RolandSysEx
    from src.spectre.librarian.repository import PatchRepository
    from src.spectre.ui.bridge import SpectreBridge
    from src.spectre.vector.engine import VectorEngine
    from tests.test_librarian_bridge import FakeJuno

    engine = VectorEngine()
    juno = FakeJuno()
    # FakeJuno skips JunoClient.__init__: attach identity for blob encoding.
    juno.device_id = DEFAULT_DEVICE_ID
    juno.model_id = tuple(JUNO_DS_MODEL_ID)
    juno.sysex = RolandSysEx(device_id=DEFAULT_DEVICE_ID, model_id=JUNO_DS_MODEL_ID)
    juno._cached_patch_part = None
    juno._active_perf_part = 1
    engine.juno = juno
    bridge = SpectreBridge(engine)
    repo = PatchRepository(user_dir=tmp_path / "patches", db_path=tmp_path / "lib.db",
                           factory_db_path=False)
    bridge._librarian_repo = repo
    return bridge, juno, repo


def _raw_image_state(name="TEST LD"):
    state = PatchState()
    state.common.name = name
    state.raw_regions = {
        "common": [bytes(80)],
        "mfx": [bytes(145)],
        "chorus": [bytes(84)],
        "reverb": [bytes(83)],
        "tmt": [bytes(41)],
        **{f"tone_{i}": [bytes(154), bytes(26)] for i in range(1, 5)},
    }
    return state


def test_engine_view_mapping():
    from src.spectre.ui.bridge import SpectreBridge
    m = SpectreBridge._engine_view_for
    assert m({"engine_mode": "VECTOR"}) == "VECTOR"
    assert m({"engine_mode": "vector"}) == "VECTOR"
    assert m({"engine_mode": "4-OSC VA"}) == "VA"
    assert m({"engine_mode": "MFX"}) == "JUNO PCM"
    assert m({}) == "JUNO PCM"
    assert m(None) == "JUNO PCM"


def test_load_patch_file_pushes_and_navigates(tmp_path):
    bridge, juno, _ = _bridge_rig(tmp_path)
    state = _raw_image_state("FILE SND")
    perf_file = tmp_path / "snd.spectre"
    save_spectre(perf_file, state, meta={"name": "FILE SND"},
                 spectre={"engine_mode": "VECTOR"}, kind="patch")
    assert bridge.loadSpectreFile(str(perf_file)) is True
    assert bridge._sound_mode == "PATCH"
    # Stays put; OK proposes the saved engine view.
    assert bridge._pending_view == "VECTOR"
    assert bridge._active_view == "JUNO PCM"
    bridge.setActiveView("LIBRARIAN")
    bridge.toggleLibrarian()
    assert bridge._active_view == "VECTOR"
    assert bridge.patch_state.common.name == "FILE SND"
    assert bridge._current_ref["kind"] == "patch"
    # Image reached the Patch-mode temp buffer (DT1 push, not a rename).
    assert bytes(juno._store[(0x1F, 0x00, 0x00, 0x00)][:12]) == b"FILE SND    "


def test_load_performance_file_navigates_mixer(tmp_path):
    bridge, juno, _ = _bridge_rig(tmp_path)
    state = _raw_image_state("GIG")
    state.sound_mode = "PERFORM"
    state.perf_name = "GIG NIGHT"
    state.perf_parts[0].volume = 77
    perf_file = tmp_path / "gig.spectre"
    save_spectre(perf_file, state, kind="performance")
    assert bridge.loadSpectreFile(str(perf_file)) is True
    assert bridge._sound_mode == "PERFORM"
    assert bridge._pending_view == "PERFORMANCE"
    bridge.setActiveView("LIBRARIAN")
    bridge.toggleLibrarian()
    assert bridge._active_view == "PERFORMANCE"
    assert bridge.patch_state.perf_name == "GIG NIGHT"
    assert juno._store[(0x10, 0x00, 0x20, 0x07)] == bytes([77])


def test_pick_part_hw_row(tmp_path):
    bridge, juno, _ = _bridge_rig(tmp_path)
    bridge.openPartPicker(3)
    assert bridge.librarianPickTarget == 3
    assert bridge._active_view == "LIBRARIAN"
    assert bridge.pickPartPatch(87, 0, 5, "", "Picked LD", "patch") is True
    part = bridge.patch_state.perf_parts[2]
    assert (part.patch_msb, part.patch_lsb, part.patch_pc) == (87, 0, 5)
    assert part.patch_name == "Picked LD"
    assert bridge.librarianPickTarget == 3  # still picking: next tap auditions on P3
    assert bridge.pickPartPatch(87, 0, 6, "", "Second LD", "patch") is True
    assert bridge.patch_state.perf_parts[2].patch_pc == 6
    # Assign stays in the Librarian; OK proposes the mixer.
    assert bridge._active_view == "LIBRARIAN"
    assert bridge._pending_view == "PERFORMANCE"
    bridge.toggleLibrarian()
    assert bridge._active_view == "PERFORMANCE"
    assert juno._store[(0x10, 0x00, 0x22, 0x04)] == bytes([87, 0, 6])


def test_pick_part_pi_only_file_pushes(tmp_path):
    import time
    bridge, juno, _ = _bridge_rig(tmp_path)
    state = _raw_image_state("FILELD")
    f = tmp_path / "lead.spectre"
    save_spectre(f, state, kind="patch")  # no synth_ref -> Pi-only
    bridge.openPartPicker(2)
    assert bridge.pickPartPatch(-1, -1, -1, str(f), "FILELD", "patch") is True
    part = bridge.patch_state.perf_parts[1]
    assert part.patch_file == str(f)
    assert part.patch_name == "FILELD"
    # Image reaches the Part 2 temp patch buffer via background push.
    deadline = time.time() + 10.0
    while float(bridge.perfPushProgress) >= 0.0 and time.time() < deadline:
        time.sleep(0.05)
    assert (0x11, 0x20, 0x00, 0x00) in juno._store
    assert bridge._active_view == "LIBRARIAN"
    assert bridge._pending_view == "PERFORMANCE"


def _wait_push_idle(bridge, timeout=10.0):
    import time
    deadline = time.time() + timeout
    while float(bridge.perfPushProgress) >= 0.0 and time.time() < deadline:
        time.sleep(0.05)
    assert float(bridge.perfPushProgress) < 0.0, "push worker did not finish"


def test_pick_rejects_containers(tmp_path):
    bridge, _, _ = _bridge_rig(tmp_path)
    bridge.openPartPicker(1)
    assert bridge.pickPartPatch(85, 0, 0, "", "Perf", "performance") is False
    assert bridge.librarianPickTarget == 1  # still picking
    bridge.cancelPartPick()
    assert bridge.librarianPickTarget == 0
    # Cancel returns to the view open before the picker (default PCM here).
    assert bridge._active_view == "JUNO PCM"


def test_save_performance_kind(tmp_path):
    from src.spectre.core.spectre_format import load_spectre
    bridge, _, _ = _bridge_rig(tmp_path)
    bridge.setSoundMode("PERFORM")
    bridge.patch_state.perf_name = "GIGSAVE"
    bridge.patch_state.perf_parts[4].volume = 66
    out = bridge.saveCurrentToFile("GIGSAVE", "", "", False, "")
    assert out.endswith(".spectre")
    loaded = load_spectre(out)
    assert loaded["kind"] == "performance"
    assert loaded["meta"]["name"] == "GIGSAVE"
    assert loaded["patch_state"].perf_parts[4].volume == 66
    assert bridge._current_ref["kind"] == "performance"


def test_save_embeds_part_snapshots(tmp_path):
    from src.spectre.core.spectre_format import load_spectre
    bridge, _, _ = _bridge_rig(tmp_path)
    lead = tmp_path / "lead.spectre"
    save_spectre(lead, _raw_image_state("LEAD"), meta={"name": "LEAD"}, kind="patch")
    bridge.setSoundMode("PERFORM")
    bridge.patch_state.perf_name = "SNAPS"
    bridge.patch_state.perf_parts[2].patch_file = str(lead)
    bridge.patch_state.perf_parts[2].patch_name = "LEAD"
    out = bridge.saveCurrentToFile("SNAPS", "", "", False, "")
    snaps = load_spectre(out)["spectre"].get("part_snapshots", {})
    assert "3" in snaps
    assert snaps["3"]["common"]["name"] == "LEAD"


def test_part_status_lifecycle(tmp_path):
    bridge, _, _ = _bridge_rig(tmp_path)
    lead = tmp_path / "lead.spectre"
    save_spectre(lead, _raw_image_state("LEAD"), meta={"name": "LEAD"}, kind="patch")
    bridge.setSoundMode("PERFORM")
    bridge.patch_state.perf_parts[0].patch_file = str(lead)
    bridge.refreshPartFileStatus()
    assert bridge.partFileStatus[0] == "ok"  # linked, no snapshot: fresh
    # Embed a snapshot via performance save, then change the file.
    bridge.patch_state.perf_name = "ST"
    out = bridge.saveCurrentToFile("ST", "", "", False, "")
    assert bridge.loadSpectreFile(out) is True
    _wait_push_idle(bridge)
    assert bridge.partFileStatus[0] == "ok"
    save_spectre(lead, _raw_image_state("LEAD V2"), meta={"name": "LEAD V2"}, kind="patch")
    bridge.refreshPartFileStatus()
    assert bridge.partFileStatus[0] == "updated"
    assert bridge.refreshPartFile(1) is True
    _wait_push_idle(bridge)
    lead.unlink()
    bridge.refreshPartFileStatus()
    assert bridge.partFileStatus[0] == "missing"
    # Missing file with snapshot still restores sound from the snapshot.
    assert bridge.refreshPartFile(1) is True
    _wait_push_idle(bridge)


def _offline_bridge(tmp_path):
    from src.spectre.librarian.repository import PatchRepository
    from src.spectre.ui.bridge import SpectreBridge
    from src.spectre.vector.engine import VectorEngine

    engine = VectorEngine()  # no juno: offline
    bridge = SpectreBridge(engine)
    repo = PatchRepository(user_dir=tmp_path / "patches", db_path=tmp_path / "lib.db",
                           factory_db_path=False)
    bridge._librarian_repo = repo
    return bridge, repo


def test_offline_perf_audition_proposes_mixer(tmp_path):
    bridge, _ = _offline_bridge(tmp_path)
    assert bridge.selectLibraryPerformance(85, 0, 3) is True
    assert bridge._sound_mode == "PERFORM"
    assert bridge.patch_state.sound_mode == "PERFORM"
    # Stays in the Librarian; OK confirms the proposed destination.
    assert bridge._pending_view == "PERFORMANCE"
    bridge.setActiveView("LIBRARIAN")
    bridge.toggleLibrarian()
    assert bridge._active_view == "PERFORMANCE"
    assert bridge._pending_view == ""


def test_offline_patch_audition_proposes_pcm(tmp_path):
    bridge, _ = _offline_bridge(tmp_path)
    assert bridge.selectLibraryPatch(87, 64, 0) is True
    assert bridge._pending_view == "JUNO PCM"
    bridge.setActiveView("LIBRARIAN")
    bridge.toggleLibrarian()
    assert bridge._active_view == "JUNO PCM"


def test_librarian_cancel_returns_to_previous(tmp_path):
    bridge, _ = _offline_bridge(tmp_path)
    bridge.setActiveView("VECTOR")
    bridge.setActiveView("LIBRARIAN")
    bridge.selectLibraryPatch(87, 64, 0)
    assert bridge._pending_view == "JUNO PCM"
    bridge.cancelLibrarian()
    assert bridge._active_view == "VECTOR"
    assert bridge._pending_view == ""


def test_playlist_load_navigates_to_mixer(tmp_path):
    bridge, _ = _offline_bridge(tmp_path)
    assert bridge.addCurrentToPlaylist() is True
    assert bridge.savePlaylistAuto() is True
    path = bridge._playlist_path
    bridge.setActiveView("LIBRARIAN")
    assert bridge.loadPlaylist(path) is True
    assert bridge.playlistCount == 1
    assert bridge._pending_view == "PERFORMANCE"
    bridge.toggleLibrarian()
    assert bridge._active_view == "PERFORMANCE"


def test_playlist_save_new_cycle(tmp_path):
    bridge, _, _ = _bridge_rig(tmp_path)
    assert bridge.playlistPath == ""
    assert bridge.addCurrentToPlaylist() is True
    assert bridge.savePlaylistAuto() is True
    assert bridge.playlistPath.endswith(".spectre")
    assert bridge.newPlaylist() is None
    assert bridge.playlistCount == 0
    assert bridge.playlistPath == ""


def test_setlist_filter_finds_saved_playlist(tmp_path):
    bridge, _, repo = _bridge_rig(tmp_path)
    assert bridge.addCurrentToPlaylist() is True
    assert bridge.savePlaylistAuto() is True
    hits = repo.search("", kind="playlist")
    assert any(h["path"] == bridge._playlist_path for h in hits)
    # A patch file must not leak into the setlist filter.
    out = bridge.saveCurrentToFile("PLAIN", "", "", False, "")
    assert out
    hits = repo.search("", kind="playlist")
    assert all(h["path"] != out for h in hits)


def test_offline_audition_sets_header_names(tmp_path):
    bridge, _ = _offline_bridge(tmp_path)
    assert bridge.selectLibraryPatch(87, 64, 0, "Warm Pad") is True
    assert bridge._patch_name == "Warm Pad"
    assert bridge.patch_state.common.name == "Warm Pad"
    assert bridge.selectLibraryPerformance(85, 0, 3, "Stage Set") is True
    assert bridge._patch_name == "Stage Set"


def test_cancel_reverts_patch_audition(tmp_path):
    bridge, _ = _offline_bridge(tmp_path)
    bridge.setActiveView("LIBRARIAN")
    assert bridge.selectLibraryPatch(87, 64, 5, "Auditioned") is True
    assert bridge._patch_name == "Auditioned"
    bridge.cancelLibrarian()
    assert bridge._patch_name != "Auditioned"
    assert bridge._sound_mode == "PATCH"
    assert bridge._active_view == "JUNO PCM"
    assert bridge._pending_view == ""


def test_cancel_reverts_part_pick(tmp_path):
    bridge, _, _ = _bridge_rig(tmp_path)
    bridge.setActiveView("PERFORMANCE")
    bridge.openPartPicker(3)
    before = (bridge.patch_state.perf_parts[2].patch_msb,
              bridge.patch_state.perf_parts[2].patch_lsb,
              bridge.patch_state.perf_parts[2].patch_pc)
    assert bridge.pickPartPatch(87, 0, 5, "", "Picked LD", "patch") is True
    after = (bridge.patch_state.perf_parts[2].patch_msb,
             bridge.patch_state.perf_parts[2].patch_lsb,
             bridge.patch_state.perf_parts[2].patch_pc)
    assert after == (87, 0, 5) and after != before
    bridge.cancelLibrarian()
    restored = (bridge.patch_state.perf_parts[2].patch_msb,
                bridge.patch_state.perf_parts[2].patch_lsb,
                bridge.patch_state.perf_parts[2].patch_pc)
    assert restored == before
    assert bridge._active_view == "PERFORMANCE"


def test_cancel_reselects_slot_on_synth(tmp_path):
    bridge, juno, _ = _bridge_rig(tmp_path)
    juno.midi.juno_out.closed = False
    bridge._set_current_slot_ref(87, 0, 11, "patch")
    bridge.setActiveView("LIBRARIAN")
    assert bridge.selectLibraryPatch(87, 0, 12, "Other") is True
    juno.midi.juno_out.send.reset_mock()
    bridge.cancelLibrarian()
    sent = [c.args[0] for c in juno.midi.juno_out.send.call_args_list]
    pcs = [m.program for m in sent if m.type == "program_change"]
    assert 11 in pcs  # previous slot re-selected on Cancel
    assert bridge._active_view == "JUNO PCM"


def test_ok_keeps_auditioned_sound(tmp_path):
    bridge, _ = _offline_bridge(tmp_path)
    bridge.setActiveView("LIBRARIAN")
    assert bridge.selectLibraryPatch(87, 64, 5, "Auditioned") is True
    bridge.toggleLibrarian()  # OK
    assert bridge._patch_name == "Auditioned"
    assert bridge._active_view == "JUNO PCM"


def _three_song_bridge(tmp_path):
    bridge, _, _ = _bridge_rig(tmp_path)
    for title in ("Song A", "Song B", "Song C"):
        bridge.patch_state.perf_name = title
        assert bridge.addCurrentToPlaylist() is True
    assert bridge.playlistCount == 3
    return bridge


def _pl_names(bridge):
    return [e["name"] for e in bridge.playlistEntries]


def test_playlist_move_keeps_highlight(tmp_path):
    bridge = _three_song_bridge(tmp_path)
    bridge._playlist_index = 1  # Song B highlighted
    assert bridge.movePlaylistEntry(0, 2) is True
    assert _pl_names(bridge) == ["Song B", "Song C", "Song A"]
    assert bridge.playlistIndex == 0  # highlight followed Song B
    assert bridge.movePlaylistEntry(2, 0) is True
    assert _pl_names(bridge) == ["Song A", "Song B", "Song C"]
    assert bridge.movePlaylistEntry(0, 0) is False
    assert bridge.movePlaylistEntry(5, 0) is False
    assert bridge.movePlaylistEntry(0, 9) is False
    assert _pl_names(bridge) == ["Song A", "Song B", "Song C"]


def test_playlist_remove_tracks_highlight(tmp_path):
    bridge = _three_song_bridge(tmp_path)
    assert bridge.removePlaylistEntry(5) is False
    bridge._playlist_index = 2  # Song C highlighted
    assert bridge.removePlaylistEntry(0) is True
    assert _pl_names(bridge) == ["Song B", "Song C"]
    assert bridge.playlistIndex == 1  # highlight followed Song C
    assert bridge.removePlaylistEntry(1) is True  # remove highlighted
    assert _pl_names(bridge) == ["Song B"]
    assert bridge.playlistIndex == 0


def _sysex_addr(mock_midi_mgr):
    pkt = mock_midi_mgr.send_juno_sysex.call_args[0][0]
    assert pkt[0:6] == [0x41, 0x10, 0x00, 0x00, 0x3A, 0x12]
    return tuple(pkt[6:10]), pkt[10:-1]


def test_zone_write_addresses():
    from unittest.mock import MagicMock

    from src.spectre.core.midi import MidiDeviceManager
    from src.spectre.core.protocol import JunoClient
    client = JunoClient(MagicMock(spec=MidiDeviceManager))
    client.set_perf_zone(1, 36, 72)
    addr, payload = _sysex_addr(client.midi)
    assert addr == (0x10, 0x00, 0x50, 0x0C)
    assert payload == [36, 72]
    client.set_perf_zone(16, switch=True, octave=67)
    addr, payload = _sysex_addr(client.midi)
    assert addr == (0x10, 0x00, 0x5F, 0x00)
    assert payload == [67]
    assert client.midi.send_juno_sysex.call_args_list[-2][0][0][6:10] == [0x10, 0x00, 0x5F, 0x01]
    # Inverted bounds auto-order; out-of-range clamps.
    client.set_perf_zone(2, 90, 40)
    addr, payload = _sysex_addr(client.midi)
    assert payload == [40, 90]
    client.set_perf_zone(2, -5, 200)
    _, payload = _sysex_addr(client.midi)
    assert payload == [0, 127]
    with pytest.raises(ValueError):
        client.set_perf_zone(0, 0, 127)
    with pytest.raises(ValueError):
        client.set_perf_zone(17, 0, 127)


def test_zone_read_defaults_offline():
    from unittest.mock import MagicMock

    from src.spectre.core.midi import MidiDeviceManager
    from src.spectre.core.protocol import JunoClient
    client = JunoClient(MagicMock(spec=MidiDeviceManager))
    client.midi.iter_juno_messages.return_value = []
    zones = client.get_perf_zones(timeout=0.05)
    assert len(zones) == 16
    assert all(z == {"low": 0, "high": 127, "switch": True, "octave": 64} for z in zones)
    with pytest.raises(TimeoutError):
        client.get_perf_zone_block(1, timeout=0.05)


def test_bridge_zone_setters(tmp_path):
    bridge, juno, _ = _bridge_rig(tmp_path)
    bridge.setPartZone(1, 36, 72)
    p = bridge.patch_state.perf_parts[0]
    assert (p.key_low, p.key_high) == (36, 72)
    assert juno._store[(0x10, 0x00, 0x50, 0x0C)] == bytes([36, 72])
    bridge.setPartZone(2, 90, 40)  # auto-ordered
    assert (bridge.patch_state.perf_parts[1].key_low,
            bridge.patch_state.perf_parts[1].key_high) == (40, 90)
    bridge.setPartZoneSwitch(1, False)
    assert bridge.patch_state.perf_parts[0].zone_switch is False
    assert juno._store[(0x10, 0x00, 0x50, 0x01)] == bytes([0])
    bridge.setPartZoneOctave(1, 99)  # clamped to 67
    assert bridge.patch_state.perf_parts[0].zone_octave == 67
    assert juno._store[(0x10, 0x00, 0x50, 0x00)] == bytes([67])
    exposed = bridge.perfParts[0]
    assert (exposed["keyLow"], exposed["keyHigh"]) == (36, 72)
    assert exposed["zoneOn"] is False and exposed["zoneOctave"] == 67


def test_zone_fields_round_trip():
    state = PatchState()
    state.perf_parts[0].key_low = 36
    state.perf_parts[0].key_high = 72
    state.perf_parts[0].zone_switch = False
    state.perf_parts[0].zone_octave = 62
    restored = patch_state_from_dict(patch_state_to_dict(state))
    p = restored.perf_parts[0]
    assert (p.key_low, p.key_high, p.zone_switch, p.zone_octave) == (36, 72, False, 62)


# --- performance FX (phase 3: shared MFX1-3 / chorus / reverb) ----------------

def test_perf_part_fx_addresses(mock_midi_mgr):
    client = JunoClient(mock_midi_mgr)
    client.set_perf_part_fx(2, dry=90, chorus=40, reverb=70)
    calls = mock_midi_mgr.send_juno_sysex.call_args_list
    addrs = [tuple(c[0][0][6:10]) for c in calls[-3:]]
    assert addrs == [(0x10, 0x00, 0x21, 0x1C), (0x10, 0x00, 0x21, 0x1D), (0x10, 0x00, 0x21, 0x1E)]
    client.set_perf_part_output(4, assign=13, mfx_select=2)
    calls = mock_midi_mgr.send_juno_sysex.call_args_list
    addrs = [tuple(c[0][0][6:10]) for c in calls[-2:]]
    assert addrs == [(0x10, 0x00, 0x23, 0x1F), (0x10, 0x00, 0x23, 0x20)]
    with __import__("pytest").raises(ValueError):
        client.set_perf_part_output(17, assign=0)


def test_perf_common_fx_addresses(mock_midi_mgr):
    client = JunoClient(mock_midi_mgr)
    client.set_perf_mfx(2, mfx_type=15, dry_send=100, chorus_send=20, reverb_send=30)
    addrs = [tuple(c[0][0][6:10]) for c in mock_midi_mgr.send_juno_sysex.call_args_list[-4:]]
    assert addrs[0] == (0x10, 0x00, 0x08, 0x00)
    client.set_perf_chorus(1, level=80, output_select=2)
    addr, _ = _sysex_addr(client.midi)
    assert addr == (0x10, 0x00, 0x04, 0x03)
    client.set_perf_reverb(4, level=60)
    addr, _ = _sysex_addr(client.midi)
    assert addr == (0x10, 0x00, 0x06, 0x01)
    client.set_perf_source("mfx1", 3)
    addr, payload = _sysex_addr(client.midi)
    assert addr == (0x10, 0x00, 0x00, 0x30) and payload == [3]
    client.set_perf_structure(5)
    addr, payload = _sysex_addr(client.midi)
    assert addr == (0x10, 0x00, 0x00, 0x37) and payload == [5]


def test_get_perf_parts_decodes_fx():
    from unittest.mock import MagicMock

    from src.spectre.core.midi import MidiDeviceManager
    client = JunoClient(MagicMock(spec=MidiDeviceManager))
    blk = bytearray(0x31)
    blk[0x07] = 100; blk[0x1C] = 90; blk[0x1D] = 11; blk[0x1E] = 22
    blk[0x1F] = 13; blk[0x20] = 2
    client.get_perf_part_block = lambda part, timeout=1.0: bytes(blk)
    client.request_data = MagicMock(return_value=None)
    client.get_perf_zones = lambda timeout=1.0: [{"low": 0, "high": 127, "switch": True, "octave": 64}] * 16
    parts = client.get_perf_parts(timeout=0.05)
    assert (parts[0].dry_send, parts[0].chorus_send, parts[0].reverb_send) == (90, 11, 22)
    assert (parts[0].output_assign, parts[0].mfx_select) == (13, 2)


def test_perf_fx_state_round_trip():
    state = PatchState()
    state.perf_parts[0].dry_send = 90
    state.perf_parts[0].mfx_select = 2
    state.perf_fx.mfx2.mfx_type = 15
    state.perf_fx.mfx2.source = 3
    state.perf_fx.mfx_structure = 5
    state.perf_fx.chorus_source = 2
    restored = patch_state_from_dict(patch_state_to_dict(state))
    assert restored.perf_parts[0].dry_send == 90
    assert restored.perf_parts[0].mfx_select == 2
    assert restored.perf_fx.mfx2.mfx_type == 15
    assert restored.perf_fx.mfx2.source == 3
    assert restored.perf_fx.mfx_structure == 5
    assert restored.perf_fx.chorus_source == 2


def test_bridge_part_fx_setters(tmp_path):
    bridge, juno, _ = _bridge_rig(tmp_path)
    bridge.setPartFx(1, 0, 90)
    assert bridge.patch_state.perf_parts[0].dry_send == 90
    assert juno._store[(0x10, 0x00, 0x20, 0x1C)] == bytes([90])
    bridge.setPartFx(1, 1, 40)
    assert juno._store[(0x10, 0x00, 0x20, 0x1D)] == bytes([40])
    bridge.setPartMfxSelect(1, 2)
    assert bridge.patch_state.perf_parts[0].mfx_select == 2
    assert juno._store[(0x10, 0x00, 0x20, 0x20)] == bytes([2])
    bridge.setPartOutput(2, 13, 2)
    assert bridge.patch_state.perf_parts[1].mfx_select == 2
    exposed = bridge.perfParts[0]
    assert exposed["drySend"] == 90 and exposed["mfxSelect"] == 2


def test_bridge_perf_sources_and_editing(tmp_path):
    bridge, juno, _ = _bridge_rig(tmp_path)
    assert bridge.editingPerfMfx == 1
    bridge.setEditingPerfMfx(3)
    assert bridge.editingPerfMfx == 3
    assert bridge.perfFxSlots[2]["editing"] is True
    bridge.setPerfSource("mfx1", 4)
    assert bridge.patch_state.perf_fx.mfx1.source == 4
    assert juno._store[(0x10, 0x00, 0x00, 0x30)] == bytes([4])
    bridge.setPerfStructure(7)
    assert bridge.patch_state.perf_fx.mfx_structure == 7
    assert bridge.perfFxSources["structure"] == 7
    # copy-to-PERFORM head-start: PARTn -> PERFORM
    bridge.patch_state.effects.mfx_type = 15
    assert bridge.copyOriginToPerform("mfx1") is True
    assert bridge.patch_state.perf_fx.mfx1.source == 0
    assert bridge.patch_state.perf_fx.mfx1.mfx_type == 15


def test_bridge_perf_mfx_live_edit(tmp_path):
    bridge, juno, _ = _bridge_rig(tmp_path)
    bridge.setSoundMode("PERFORM")
    bridge.setPerfSource("mfx1", 0)
    bridge.setEditingPerfMfx(1)
    bridge.setPerfMfx(1, 15, 100, 20, 30)
    assert bridge.patch_state.perf_fx.mfx1.mfx_type == 15
    assert juno._store[(0x10, 0x00, 0x02, 0x00)] == bytes([15])
    assert juno._store[(0x10, 0x00, 0x02, 0x01)] == bytes([100])


def test_part_mfx_select_indexing(tmp_path):
    """Regression: strip taps 0/1/2 must land on MFX1/2/3 (not shift by one)."""
    bridge, juno, _ = _bridge_rig(tmp_path)
    for tap, expect in ((0, 0), (1, 1), (2, 2)):
        bridge.setPartMfxSelect(1, tap)
        assert bridge.patch_state.perf_parts[0].mfx_select == expect
        assert juno._store[(0x10, 0x00, 0x20, 0x20)] == bytes([expect])


def test_playlist_load_pushes_part_and_common_fx(tmp_path):
    bridge, juno, _ = _bridge_rig(tmp_path)
    bridge.patch_state.perf_name = "FXGIG"
    bridge.patch_state.perf_parts[0].dry_send = 90
    bridge.patch_state.perf_parts[0].mfx_select = 2
    bridge.patch_state.perf_fx.mfx1.source = 4
    bridge.patch_state.perf_fx.mfx_structure = 7
    bridge.patch_state.perf_fx.chorus_type = 2
    assert bridge.addCurrentToPlaylist() is True
    assert bridge.savePlaylistAuto() is True
    path = bridge._playlist_path
    # Reset hardware store markers, reload from file
    juno._store.pop((0x10, 0x00, 0x20, 0x1C), None)
    juno._store.pop((0x10, 0x00, 0x20, 0x20), None)
    assert bridge.loadPlaylist(path) is True
    assert bridge.loadPlaylistEntry(0) is True
    assert juno._store[(0x10, 0x00, 0x20, 0x1C)] == bytes([90])
    assert juno._store[(0x10, 0x00, 0x20, 0x20)] == bytes([2])
    assert juno._store[(0x10, 0x00, 0x00, 0x30)] == bytes([4])
    assert juno._store[(0x10, 0x00, 0x00, 0x37)] == bytes([7])
    assert bridge.patch_state.perf_fx.chorus_type == 2
    assert bridge.perfFxSources["mfx1"] == 4


# --- origin-resolved editors: MFX Studio / Master FX follow rail selection ---

def _perform_bridge(tmp_path):
    bridge, juno, _ = _bridge_rig(tmp_path)
    bridge.setSoundMode("PERFORM")
    return bridge, juno


def test_mfx_studio_shows_perf_slot(tmp_path):
    bridge, _ = _perform_bridge(tmp_path)
    assert bridge.mfxEditTargetLabel == "MFX1\u00b7PERF"
    bridge.setPerfMfx(2, 15, 100, 20, 30)
    bridge.setEditingPerfMfx(2)
    assert bridge.mfxAlgoId == 15
    assert bridge.mfxDrySend == 100
    assert bridge.mfxChorusSend == 20
    assert bridge.mfxReverbSend == 30
    assert "Tape" in bridge.mfxAlgoName or "15" in bridge.mfxAlgoName
    # Active-part patch state untouched: exclusive routing, no clobber.
    assert bridge.patch_state.effects.mfx_dry_send == 127
    assert bridge.patch_state.effects.mfx_chorus_send == 0


def test_mfx_studio_writes_perf_slot(tmp_path):
    bridge, juno = _perform_bridge(tmp_path)
    bridge.setEditingPerfMfx(1)
    bridge.setMfxSend("dry", 77)
    assert bridge.patch_state.perf_fx.mfx1.dry_send == 77
    assert juno._store[(0x10, 0x00, 0x02, 0x01)] == bytes([77])
    assert bridge.mfxDrySend == 77
    bridge.setMfxAlgoId(15)
    assert bridge.patch_state.perf_fx.mfx1.mfx_type == 15
    assert bridge.mfxAlgoId == 15
    bridge.setMfxParam(0, 40)
    assert bridge.patch_state.perf_fx.mfx1.params[0] == 40
    assert bridge.mfxParamValues[0] == 40
    bridge.setMfxBypass(True)
    assert bridge.mfxBypassed is True
    assert bridge.patch_state.perf_fx.mfx1.mfx_type == 0
    bridge.setMfxBypass(False)
    assert bridge.patch_state.perf_fx.mfx1.mfx_type == 15


def test_master_fx_follows_chorus_origin(tmp_path):
    bridge, juno = _perform_bridge(tmp_path)
    assert bridge.choEditTargetLabel == "CHO\u00b7PERF"
    bridge.setChorusParam("level", 64)
    assert bridge.patch_state.perf_fx.chorus_level == 64
    assert juno._store[(0x10, 0x00, 0x04, 0x01)] == bytes([64])
    assert bridge.chorusLevel == 64
    # Part patch state untouched.
    assert bridge.patch_state.effects.chorus_level != 64
    bridge.setReverbParam("level", 80)
    assert bridge.patch_state.perf_fx.reverb_level == 80
    assert bridge.reverbLevel == 80


def test_part_origin_routes_to_part_patch(tmp_path):
    bridge, juno = _perform_bridge(tmp_path)
    bridge._part_fx_cache[3] = {
        "mfx": {"type": 20, "dry": 90, "chorus": 10, "reverb": 10,
                "params": [5] * 32, "lastActive": 20},
        "chorus": {"type": 2, "level": 70, "toReverb": 1, "predelay": 1,
                   "rate": 2, "depth": 3, "feedback": 4},
        "reverb": {"type": 3, "level": 71, "predelay": 1, "time": 2,
                   "damp": 3, "diffusion": 4, "tone": 5},
    }
    bridge.setPerfSource("mfx1", 3)
    assert bridge.mfxEditTargetLabel == "MFX1\u00b7P3"
    assert bridge.mfxAlgoId == 20
    assert bridge.mfxParamValues[0] == 5
    bridge.setMfxSend("dry", 50)
    assert bridge._part_fx_cache[3]["mfx"]["dry"] == 50
    # Part 3 temp patch MFX dry: 11 40 00 00 + 00 00 02 01.
    assert juno._store[(0x11, 0x40, 0x02, 0x01)] == bytes([50])
    # Perf-common slot untouched.
    assert (0x10, 0x00, 0x02, 0x01) not in juno._store
    bridge.setPerfSource("chorus", 3)
    assert bridge.choEditTargetLabel == "CHO\u00b7P3"
    assert bridge.chorusLevel == 70
    bridge.setChorusParam("level", 33)
    assert bridge._part_fx_cache[3]["chorus"]["level"] == 33
    assert juno._store[(0x11, 0x40, 0x04, 0x01)] == bytes([33])


def test_patch_mode_editors_unchanged(tmp_path):
    bridge, juno = _perform_bridge(tmp_path)
    bridge.setSoundMode("PATCH")
    assert bridge.mfxEditTargetLabel == "PATCH"
    bridge.setMfxSend("dry", 85)
    assert bridge.patch_state.effects.mfx_dry_send == 85
    bridge.setChorusParam("level", 64)
    assert bridge.patch_state.effects.chorus_level == 64


def test_read_part_fx_decode():
    from unittest.mock import MagicMock

    from src.spectre.core.midi import MidiDeviceManager
    from src.spectre.core.sysex import pack_4nibbles
    client = JunoClient(MagicMock(spec=MidiDeviceManager))
    mfx = bytes([15, 100, 20, 30] + [0] * 13 + pack_4nibbles(32768 + 40) + [0] * (145 - 21))
    cho = bytes([1, 80, 0, 2] + [0] * 8 + pack_4nibbles(32768 + 12) + [0] * (84 - 16))
    rev = bytes([4, 60, 0] + pack_4nibbles(32768 + 15) + [0] * (83 - 7))
    assert len(mfx) == 145 and len(cho) == 84 and len(rev) == 83
    client.request_data = MagicMock(side_effect=[mfx, cho, rev])
    out = client.read_part_fx(3)
    assert out["mfx"]["type"] == 15 and out["mfx"]["params"][0] == 40
    assert out["chorus"]["level"] == 80 and out["chorus"]["predelay"] == 12
    assert out["reverb"]["level"] == 60 and out["reverb"]["predelay"] == 15


def test_sync_performance_resolves_part_names(tmp_path):
    bridge, juno, repo = _bridge_rig(tmp_path)
    repo.upsert_entry(
        source="synth-user",
        kind="patch",
        msb=87,
        lsb=64,
        pc=5,
        name="Custom Lead",
        category="SYNTH",
    )

    mock_parts = [
        PerfPartState(part_index=1, patch_msb=87, patch_lsb=64, patch_pc=5, volume=100),
        PerfPartState(part_index=2, patch_msb=121, patch_lsb=0, patch_pc=0, volume=80),
        PerfPartState(part_index=3, patch_msb=87, patch_lsb=64, patch_pc=99, volume=90),
    ] + [PerfPartState(part_index=i) for i in range(4, 17)]

    juno.get_perf_parts = MagicMock(return_value=mock_parts)
    juno.get_perf_part_patch_name = MagicMock(side_effect=lambda idx, timeout=0.25: "Live Hardware 3" if idx == 3 else "")

    bridge.syncPerformanceFromSynth(async_mode=False)

    parts = bridge.patch_state.perf_parts
    assert parts[0].patch_name == "Custom Lead"
    assert parts[2].patch_name == "Live Hardware 3"


def test_edit_perf_part_refreshes_editors(tmp_path):
    bridge, juno, _ = _bridge_rig(tmp_path)

    new_state = PatchState()
    new_state.common.name = "PART2 PATCH"
    new_state.tones[0].level = 95
    new_state.tones[1].level = 60
    new_state.tones[2].level = 40
    new_state.tones[3].level = 0
    new_state.tones[0].wave_bank_l = "INTA"
    new_state.tones[0].wave_num_l = 123

    juno.read_full_patch = MagicMock(return_value=new_state)
    juno.set_active_perf_part = MagicMock()

    bridge.patch_state.active_perf_part = 2
    bridge._refresh_editors_for_part(2, async_mode=False)

    assert bridge.patch_state.common.name == "PART2 PATCH"
    assert bridge.engine.tone_levels == (95, 60, 40, 0)
    assert bridge._tone_waves[0] == ("INTA", 123)



def test_performance_file_carries_the_song(tmp_path):
    """One file = the whole song: performance, part sounds, sequence and tempo."""
    bridge, _, _ = _bridge_rig(tmp_path)
    bridge.setSoundMode("PERFORM")
    bridge.patch_state.perf_name = "SONG"
    bridge.setBpm(101.0)
    bridge.seqSetTrackTargetPart(0, 3)
    bridge.seqToggleTrackLayer(0, 5)
    out = bridge.saveCurrentToFile("SONG", "", "", False, "")
    assert load_spectre(out)["spectre"]["sequencer"]["bpm"] == 101.0

    bridge.setBpm(140.0)
    bridge.seqSetTrackTargetPart(0, 1)
    bridge.seqToggleTrackLayer(0, 5)
    assert bridge.loadSpectreFile(out) is True
    assert bridge._sound_mode == "PERFORM"
    assert bridge.bpm == 101.0
    assert bridge.sequencer.song.tracks[0].target_parts == [3, 5]


def test_performance_file_without_sequence_keeps_current_one(tmp_path):
    bridge, _, _ = _bridge_rig(tmp_path)
    state = _raw_image_state("OLD")
    state.sound_mode = "PERFORM"
    old = tmp_path / "old.spectre"
    save_spectre(old, state, kind="performance")
    bridge.setBpm(133.0)
    bridge.seqSetTrackTargetPart(2, 9)
    assert bridge.loadSpectreFile(str(old)) is True
    assert bridge.bpm == 133.0
    assert bridge.sequencer.song.tracks[2].target_parts == [9]


def test_save_keeps_held_snapshot_for_missing_link(tmp_path):
    bridge, _, _ = _bridge_rig(tmp_path)
    bridge.setSoundMode("PERFORM")
    bridge.patch_state.perf_parts[1].patch_file = str(tmp_path / "gone.spectre")
    bridge._part_snapshots = {"2": patch_state_to_dict(_raw_image_state("HELD"))}
    out = bridge.saveCurrentToFile("MISS", "", "", False, "")
    assert load_spectre(out)["spectre"]["part_snapshots"]["2"]["common"]["name"] == "HELD"


def test_pick_part_turns_kbd_switch_on(tmp_path):
    bridge, _, _ = _bridge_rig(tmp_path)
    bridge.setPartZoneSwitch(6, False)
    bridge.openPartPicker(6)
    assert bridge.pickPartPatch(87, 0, 5, "", "Picked", "patch") is True
    assert bridge.patch_state.perf_parts[5].zone_switch is True
    assert bridge.perfParts[5]["zoneOn"] is True


def test_leaving_librarian_ends_part_pick(tmp_path):
    bridge, _, _ = _bridge_rig(tmp_path)
    bridge.openPartPicker(4)
    assert bridge.pickPartPatch(87, 0, 5, "", "LD", "patch") is True
    bridge.toggleLibrarian()  # OK
    assert bridge.librarianPickTarget == 0
    bridge.openPartPicker(4)
    bridge.setActiveView("SEQUENCER")  # navigated away
    assert bridge.librarianPickTarget == 0
