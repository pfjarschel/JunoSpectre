"""Tests for PatchRepository: files as truth, SQLite as rebuildable cache."""

from src.spectre.core.patch_state import PatchState
from src.spectre.core.spectre_format import save_spectre
from src.spectre.librarian.repository import PatchRepository


def _make_repo(tmp_path):
    return PatchRepository(user_dir=tmp_path / "patches", db_path=tmp_path / "lib.db")


def test_rescan_search_and_rebuild(tmp_path):
    repo = _make_repo(tmp_path)
    ps = PatchState.create_init_patch()
    ps.common.name = "MY LEAD"
    save_spectre(repo.user_dir / "lead.spectre", ps,
                 meta={"name": "MY LEAD", "category": "SYNTH LEAD", "tags": ["fat"], "favorite": True})
    ps2 = PatchState.create_init_patch()
    ps2.common.name = "MY PAD"
    save_spectre(repo.user_dir / "pad.spectre", ps2, meta={"name": "MY PAD", "category": "SYNTH PAD"})

    stats = repo.rescan_files()
    assert stats == {"added": 2, "updated": 0, "removed": 0}
    assert repo.count("file") == 2

    assert len(repo.search("lead")) == 1
    assert repo.search("lead")[0]["favorite"] is True
    assert len(repo.search("", category="SYNTH PAD")) == 1
    assert len(repo.search("", favorites_only=True)) == 1

    # DB is a cache: delete it and rebuild from files without loss
    repo.close()
    (tmp_path / "lib.db").unlink()
    repo2 = _make_repo(tmp_path)
    assert repo2.count("file") == 0
    repo2.rescan_files()
    assert repo2.count("file") == 2
    assert repo2.search("MY PAD")[0]["category"] == "SYNTH PAD"
    repo2.close()


def test_favorite_travels_with_file(tmp_path):
    repo = _make_repo(tmp_path)
    ps = PatchState.create_init_patch()
    ps.common.name = "STAR"
    p = save_spectre(repo.user_dir / "star.spectre", ps, meta={"name": "STAR"})
    repo.rescan_files()
    assert repo.search("STAR")[0]["favorite"] is False
    assert repo.set_favorite(str(p), True) is True
    assert repo.search("STAR")[0]["favorite"] is True
    # File itself carries the flag (portable across machines/pCloud/git)
    from src.spectre.core.spectre_format import load_spectre
    assert load_spectre(p)["meta"]["favorite"] is True
    repo.close()


def test_factory_rows_metadata_only_and_searchable(tmp_path):
    repo = _make_repo(tmp_path)
    repo.bulk_upsert_factory([
        {"msb": 87, "lsb": 64, "pc": 0, "name": "Grand Pno DS", "category": "PIANO"},
        {"msb": 87, "lsb": 64, "pc": 1, "name": "88StageGrand", "category": "PIANO"},
    ])
    assert repo.count("factory") == 2
    hits = repo.search("grand", source="factory")
    assert len(hits) == 2
    # favorite on factory rows is DB-only (no file to carry it)
    assert repo.set_favorite(hits[0]["path"], True) is True
    assert repo.search("", favorites_only=True, source="factory")[0]["path"] == hits[0]["path"]
    repo.close()


def test_synth_user_slots_indexed(tmp_path):
    repo = _make_repo(tmp_path)
    repo.upsert_synth_user(87, 0, 0, "Grand Pno DS", "PNO")
    repo.upsert_synth_user(87, 1, 0, "INIT PATCH")
    hits = repo.search("", source="synth-user")
    assert len(hits) == 2
    assert hits[0]["kind"] == "patch"
    repo.close()


def test_kinds_and_category_lists(tmp_path):
    repo = _make_repo(tmp_path)
    repo.bulk_upsert_factory([
        {"msb": 87, "lsb": 64, "pc": 0, "name": "Grand Pno DS", "category": "PNO"},
        {"msb": 87, "lsb": 68, "pc": 0, "name": "J-Pop Brass", "category": "SBR"},
        {"source": "factory", "kind": "drum", "msb": 86, "lsb": 64, "pc": 0,
         "name": "Pop Kit 1", "category": "DRM"},
        {"source": "factory", "kind": "performance", "msb": 85, "lsb": 64, "pc": 0,
         "name": "Bass / Piano", "category": ""},
    ])
    assert repo.count(kind="drum") == 1
    assert repo.count(kind="performance") == 1
    assert len(repo.search("", categories=["PNO", "SBR"])) == 2
    assert len(repo.search("", categories=["PNO"])) == 1
    assert repo.search("", kind="drum")[0]["name"] == "Pop Kit 1"
    # paths carry the kind infix so drums/perfs never collide with patches
    assert repo.search("", kind="drum")[0]["path"].startswith("factory:drum:")
    repo.close()


def test_legacy_db_migrates_kind(tmp_path):
    import sqlite3
    db = tmp_path / "legacy.db"
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE patches (path TEXT PRIMARY KEY, source TEXT, name TEXT,"
        " category TEXT, tags TEXT DEFAULT '[]', favorite INTEGER DEFAULT 0,"
        " rating INTEGER DEFAULT 0, mtime INTEGER DEFAULT 0, hash TEXT DEFAULT '',"
        " msb INTEGER, lsb INTEGER, pc INTEGER, format_version INTEGER DEFAULT 1)")
    conn.execute("INSERT INTO patches(path, source, name) VALUES('factory:87:64:0','factory','Old')")
    conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()
    conn.close()
    repo = PatchRepository(user_dir=tmp_path / "p", db_path=db)
    row = repo.get("factory:87:64:0")
    assert row is not None and row["kind"] == "patch"
    repo.close()


def test_syx_indexed_by_filename(tmp_path):
    repo = _make_repo(tmp_path)
    (repo.user_dir / "raw.syx").write_bytes(bytes([0xF0, 0x41, 0xF7]))
    stats = repo.rescan_files()
    assert stats["added"] == 1
    assert repo.search("raw")[0]["name"] == "raw"
    repo.close()
