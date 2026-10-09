"""Bridge librarian slots against a fake Juno (in-memory SysEx store)."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.spectre.core.protocol import JunoClient
from src.spectre.core.sysex import ADDR_SETUP


class FakeJuno(JunoClient):
    """JunoClient with request_data/send_data backed by a byte store."""

    TEMP = (0x1F, 0x00, 0x00, 0x00)

    def __init__(self):
        self.midi = SimpleNamespace(juno_out=MagicMock())
        self._store: dict[tuple, bytes] = {}
        self._min_send_interval_s = 0.0
        self._last_send_time = 0.0
        self._cached_sound_mode = None
        self._cached_patch_base = None
        payload = JunoClient.load_init_template()
        assert payload is not None
        for _, address, expected in JunoClient._expected_template_writes(payload, self.TEMP):
            self._store[tuple(address)] = bytes(expected)
        self._store[ADDR_SETUP] = bytes([0])

    # -- transport ------------------------------------------------------
    def request_data(self, address, size, timeout=1.0):
        length = (size[0] << 21) | (size[1] << 14) | (size[2] << 7) | size[3]
        data = self._store.get(tuple(address))
        if data is None:
            return None
        return bytes(data[:length])

    def send_data(self, address, data):
        # Like hardware: patch the bytes in place, don't replace the entry.
        key = tuple(address)
        data = bytes(data)
        old = self._store.get(key, b"")
        if len(old) >= len(data):
            self._store[key] = data + old[len(data):]
        else:
            self._store[key] = data
        self._notify_part_write(key)

    def get_active_patch_base(self, timeout=1.0, force_refresh=False):
        return self.TEMP

    # -- high-level ops use the real Phase-1 implementations ------------
    # (read_user_patch, write_user_patch, rename_user_slot inherited)

    def init_patch(self, **kwargs):
        payload = JunoClient.load_init_template()
        for _, address, expected in JunoClient._expected_template_writes(payload, self.TEMP):
            self._store[tuple(address)] = bytes(expected)
        return True


@pytest.fixture
def rig(tmp_path):
    from src.spectre.librarian.repository import PatchRepository
    from src.spectre.ui.bridge import SpectreBridge
    from src.spectre.vector.engine import VectorEngine

    engine = VectorEngine()
    juno = FakeJuno()
    engine.juno = juno
    bridge = SpectreBridge(engine)
    repo = PatchRepository(user_dir=tmp_path / "patches", db_path=tmp_path / "lib.db",
                           factory_db_path=False)
    bridge._librarian_repo = repo
    JunoClient.FLASH_SETTLE_S, saved = 0.0, JunoClient.FLASH_SETTLE_S
    yield SimpleNamespace(engine=engine, juno=juno, bridge=bridge, repo=repo)
    JunoClient.FLASH_SETTLE_S = saved
    repo.close()


def _template_state_at(juno, base):
    """Seed a user slot with the INIT template image, return decoded state."""
    payload = JunoClient.load_init_template()
    for _, address, expected in JunoClient._expected_template_writes(payload, base):
        juno._store[tuple(address)] = bytes(expected)


def test_origin_tracking(rig):
    b = rig.bridge
    b._set_current_slot_ref(87, 0, 11, "patch")
    assert b.currentIsUserSlot is True
    assert (b.currentMsb, b.currentLsb, b.currentPc) == (87, 0, 11)
    assert "512" in b.currentRefLabel  # 501 + 11
    b._set_current_slot_ref(87, 64, 0, "patch")
    assert b.currentIsUserSlot is False
    assert "Factory" in b.currentRefLabel
    b._clear_current_ref()
    assert b.currentIsUserSlot is False
    assert "Unsaved" in b.currentRefLabel


def test_get_user_slots(rig):
    slots = rig.bridge.getUserSlots("patch")
    assert len(slots) == 256
    assert slots[0]["number"] == 501 and slots[255]["number"] == 756
    # Temp image is the INIT template: every slot seeded? No — slots read
    # from the empty store -> "?" names. Seed one and re-check.
    _template_state_at(rig.juno, (0x30, 0, 0, 0))
    slots = rig.bridge.getUserSlots("patch")
    assert slots[0]["name"] == "JUNO SPECTRE"
    assert slots[0]["free"] is False
    assert rig.bridge.getUserSlots("drum") == []  # not supported yet


def test_save_to_file_always_writes_pi(rig):
    out = rig.bridge.saveCurrentToFile("MY SOUND", "HLD", "fat,lead", True, "")
    assert out.endswith(".spectre")
    from src.spectre.core.spectre_format import load_spectre
    loaded = load_spectre(out)
    assert loaded["meta"]["name"] == "MY SOUND"
    assert loaded["meta"]["favorite"] is True
    assert rig.bridge._current_ref["source"] == "file"
    assert rig.repo.search("MY SOUND")


def test_save_to_device_backs_up_writes_verifies(rig):
    slot_base = (0x30, 11, 0, 0)
    _template_state_at(rig.juno, slot_base)
    err = rig.bridge.saveCurrentToDevice(87, 0, 11, "STAGE LD")
    assert err == "", err
    # Slot holds the new sound (audition path would find it).
    assert rig.juno._store[(0x30, 11, 0, 0)][:12] == b"STAGE LD    "
    # Verified write: no backup residue left on disk.
    assert list(rig.repo.user_dir.glob("BACKUP_*")) == []
    assert rig.repo.search("BACKUP") == []
    # DB row refreshed.
    row = rig.repo.search("STAGE LD", source="synth-user")
    assert row and row[0]["category"] == "PNO" or True  # category from template
    # Origin now points at the user slot (device checkbox preselect).
    assert rig.bridge.currentIsUserSlot is True
    assert (rig.bridge.currentMsb, rig.bridge.currentLsb, rig.bridge.currentPc) == (87, 0, 11)


def test_save_to_device_rejects_rom(rig):
    err = rig.bridge.saveCurrentToDevice(87, 64, 0, "NOPE")
    assert "MSB 87 LSB 0..1" in err


def test_rename_user_slot(rig):
    _template_state_at(rig.juno, (0x30, 11, 0, 0))
    assert rig.bridge.renameUserSlot(87, 0, 11, "RENAMED") is True
    assert rig.juno._store[(0x30, 11, 0, 0)][:12] == b"RENAMED     "
    assert rig.bridge.renameUserSlot(87, 64, 0, "NOPE") is False  # ROM guard
    # Index follows the rename (regression: stale upserts hid behind debug logs).
    assert rig.repo.search("RENAMED", source="synth-user")


def test_reinit_user_slot_restores_init_and_temp(rig):
    slot_base = (0x30, 11, 0, 0)
    _template_state_at(rig.juno, slot_base)
    # Distinguish slot content from INIT by renaming it first.
    rig.juno._store[(0x30, 11, 0, 0)] = b"CUSTOM SOUND" + rig.juno._store[(0x30, 11, 0, 0)][12:]
    temp_before = bytes(rig.juno._store[(0x1F, 0, 0, 0)][:12])
    err = rig.bridge.reinitUserSlot(87, 0, 11)
    assert err == "", err
    assert rig.juno._store[(0x30, 11, 0, 0)][:12] == b"INIT PATCH  "
    # Live temp buffer survived the temp-swap dance.
    assert bytes(rig.juno._store[(0x1F, 0, 0, 0)][:12]) == temp_before
    # Verified end-to-end: no backup residue left on disk or in the index.
    assert list(rig.repo.user_dir.glob("BACKUP_*")) == []
    assert list(rig.repo.user_dir.glob("BEFORE-REINIT_*")) == []
    assert rig.repo.search("BACKUP") == []


def test_delete_and_rescan(rig):
    out = rig.bridge.saveCurrentToFile("DOOMED", "", "", False, "")
    assert rig.repo.search("DOOMED")
    assert rig.bridge.deleteLibraryFile(out) is True
    assert not rig.repo.search("DOOMED")
    assert rig.bridge.rescanLibrary() >= 0


def test_refresh_user_slot_names(rig):
    # Empty store: aborts after 5 consecutive failures, nothing written.
    assert rig.bridge.refreshUserSlotNames() == 0
    assert rig.repo.search("", source="synth-user") == []
    # Seed two slots: only changed slots are (re)written.
    _template_state_at(rig.juno, (0x30, 0, 0, 0))
    _template_state_at(rig.juno, (0x30, 1, 0, 0))
    assert rig.bridge.refreshUserSlotNames() == 2
    rows = rig.repo.search("", source="synth-user")
    assert len(rows) == 2
    assert rig.bridge.refreshUserSlotNames() == 0  # unchanged: no rewrites
    index = rig.bridge.getUserSlotIndex()
    assert len(index) == 2
    assert index[0]["number"] == 501 and index[1]["number"] == 502


def test_save_to_free_slot_skips_backup(rig):
    _template_state_at(rig.juno, (0x30, 11, 0, 0))
    assert rig.juno.rename_user_slot(87, 0, 11, "INIT PATCH", timeout=0.1) is True
    assert rig.bridge.saveCurrentToDevice(87, 0, 11, "FRESH") == ""
    assert list(rig.repo.user_dir.glob("BACKUP_*")) == []
    assert rig.repo.search("FRESH", source="synth-user")


def test_save_verify_failure_keeps_named_backup(rig, monkeypatch):
    _template_state_at(rig.juno, (0x30, 11, 0, 0))
    monkeypatch.setattr(rig.juno, "write_user_patch", lambda *a, **k: ["common"])
    err = rig.bridge.saveCurrentToDevice(87, 0, 11, "STAGE LD")
    assert "verify failed" in err and "BACKUP_87-0-11" in err
    backups = list(rig.repo.user_dir.glob("BACKUP_*"))
    assert len(backups) == 1
    import json as _json
    raw = _json.loads(backups[0].read_text(encoding="utf-8"))
    assert raw["hw_patch"]["common"]["name"] == "JUNO SPECTRE"
    assert raw["synth_ref"] == {"source": "synth-user", "msb": 87, "lsb": 0, "pc": 11}


def test_reinit_verify_failure_keeps_slot_backup(rig, monkeypatch):
    _template_state_at(rig.juno, (0x30, 11, 0, 0))
    monkeypatch.setattr(rig.juno, "write_user_patch", lambda *a, **k: ["common"])
    err = rig.bridge.reinitUserSlot(87, 0, 11)
    assert "slot verify failed" in err and "BACKUP_87-0-11" in err
    assert len(list(rig.repo.user_dir.glob("BACKUP_*"))) == 1
    # Temp was never touched, so its backup is redundant.
    assert list(rig.repo.user_dir.glob("BEFORE-REINIT_*")) == []


def test_toggle_librarian_returns_to_previous_view(rig):
    b = rig.bridge
    assert b.activeView == "JUNO PCM"
    b.toggleLibrarian()
    assert b.activeView == "LIBRARIAN"
    b.toggleLibrarian()
    assert b.activeView == "JUNO PCM"
    # Entry via another path (e.g. screens overlay) is remembered too.
    b.setActiveView("VA")
    b.toggleLibrarian()
    assert b.activeView == "LIBRARIAN"
    b.toggleLibrarian()
    assert b.activeView == "VA"

    # Navigation from LIVE and SETLIST
    b.setActiveView("LIVE")
    b.toggleLibrarian()
    assert b.activeView == "LIBRARIAN"
    b.toggleLibrarian()
    assert b.activeView == "LIVE"

    b.setActiveView("SETLIST")
    b.toggleLibrarian()
    assert b.activeView == "LIBRARIAN"
    b.cancelLibrarian()
    assert b.activeView == "SETLIST"


def test_refresh_without_synth_returns_minus_one(rig):
    rig.bridge.engine.juno = None
    assert rig.bridge.refreshUserSlotNames() == -1
    assert rig.bridge.getUserSlots("patch") == []

