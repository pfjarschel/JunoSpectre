"""Tests for the shipped factory catalog split (factory.db + user overlay)."""


import pytest

from src.spectre.librarian.factory import (
    build_factory_db,
    factory_catalog_version,
    factory_key,
    factory_variants,
)
from src.spectre.librarian.repository import PatchRepository

ROWS = [
    {"source": "factory", "kind": "patch", "msb": 87, "lsb": 64, "pc": 0,
     "name": "Grand Pno DS", "category": "PNO", "tags": []},
    {"source": "factory", "kind": "patch", "msb": 87, "lsb": 68, "pc": 0,
     "name": "J-Pop Brass", "category": "SBR", "tags": []},
    {"source": "factory", "kind": "drum", "msb": 86, "lsb": 64, "pc": 0,
     "name": "Pop Kit 1", "category": "DRM", "tags": []},
    {"source": "synth-user", "kind": "patch", "msb": 87, "lsb": 0, "pc": 0,
     "name": "MY USER", "category": "PNO", "tags": []},
]


@pytest.fixture
def factory_db(tmp_path):
    path = tmp_path / "factory.db"
    assert build_factory_db(path, ROWS, "xps30") == 3  # synth-user rows skipped
    return path


def _repo(tmp_path, factory_db=None, variant="xps30"):
    return PatchRepository(user_dir=tmp_path / "patches",
                           db_path=tmp_path / "user.db",
                           factory_db_path=factory_db,
                           model_variant=variant)


def test_build_and_version(factory_db):
    assert factory_catalog_version(factory_db) == 1
    assert factory_variants(factory_db) == ["xps30"]
    assert factory_key("xps30", "patch", 87, 64, 0) == "factory:xps30:patch:87:64:0"


def test_union_search_and_counts(tmp_path, factory_db):
    repo = _repo(tmp_path, factory_db)
    repo.upsert_synth_user(87, 0, 0, "MY USER", "PNO")
    try:
        assert repo.count() == 4
        assert repo.count("factory") == 3
        assert repo.count("synth-user") == 1
        assert repo.count(kind="drum") == 1
        hits = repo.search("grand", limit=100)
        assert len(hits) == 1 and hits[0]["path"] == "factory:xps30:patch:87:64:0"
        assert repo.search("", kind="drum")[0]["name"] == "Pop Kit 1"
        assert repo.get("factory:xps30:patch:87:64:0")["category"] == "PNO"
    finally:
        repo.close()


def test_variant_filter(tmp_path, factory_db):
    repo = _repo(tmp_path, factory_db, variant="juno-ds")
    try:
        # No juno-ds rows shipped yet: factory side is empty, user side works.
        assert repo.count("factory") == 0
        assert repo.search("grand") == []
        assert repo.get("factory:xps30:patch:87:64:0") is None
    finally:
        repo.close()


def test_overlay_favorite_and_tags(tmp_path, factory_db):
    import os
    before = os.path.getmtime(factory_db)
    repo = _repo(tmp_path, factory_db)
    try:
        path = "factory:xps30:patch:87:64:0"
        assert repo.set_favorite(path, True) is True
        assert repo.set_tags(path, ["gig"]) is True
        hits = repo.search("", favorites_only=True)
        assert [h["path"] for h in hits] == [path]
        assert repo.get(path)["tags"] == ["gig"]
        # Shipped file untouched: overlay lives in the user DB.
        assert os.path.getmtime(factory_db) == before
        assert repo.set_favorite(path, False) is True
        assert repo.search("", favorites_only=True) == []
    finally:
        repo.close()


def test_legacy_migration(tmp_path, factory_db):
    repo = _repo(tmp_path, None)  # no factory yet: legacy rows stay put
    repo.upsert_entry("factory", "patch", 87, 64, 0, "Grand Pno DS", "PNO")
    repo.upsert_entry("factory", "patch", 87, 68, 0, "J-Pop Brass", "SBR")
    repo.set_favorite("factory:patch:87:64:0", True)
    repo.close()
    # Reopen against the shipped catalog: legacy rows migrate to overlay.
    repo2 = _repo(tmp_path, factory_db)
    try:
        assert repo2.count("factory") == 3  # from shipped db, not legacy
        assert repo2._conn.execute(
            "SELECT COUNT(*) AS n FROM patches WHERE source='factory'").fetchone()["n"] == 0
        row = repo2.get("factory:xps30:patch:87:64:0")
        assert row is not None and row["favorite"] is True  # kept
        assert repo2.get("factory:xps30:patch:87:68:0")["favorite"] is False
    finally:
        repo2.close()


def test_legacy_kept_without_matching_variant(tmp_path, factory_db):
    repo = _repo(tmp_path, None)
    repo.upsert_entry("factory", "patch", 87, 64, 0, "Grand Pno DS", "PNO")
    repo.close()
    repo2 = _repo(tmp_path, factory_db, variant="juno-ds")
    try:
        # Variant absent from shipped db: legacy rows preserved, nothing lost.
        assert repo2.count("factory") == 0  # shipped side empty...
        legacy = repo2._conn.execute(
            "SELECT COUNT(*) AS n FROM patches WHERE source='factory'").fetchone()["n"]
        assert legacy == 1
    finally:
        repo2.close()


def test_ensure_shipped_copies(tmp_path, monkeypatch):
    import src.spectre.librarian.factory as fac
    src = tmp_path / "src_factory.db"
    build_factory_db(src, ROWS, "xps30")
    monkeypatch.setattr(fac, "shipped_factory_db", lambda: src)
    dest = fac.ensure_shipped_factory(tmp_path / "data")
    assert dest is not None and dest.is_file()
    assert factory_variants(dest) == ["xps30"]
    # Second call keeps the copy (no clobber).
    dest.write_bytes(b"sentinel")
    assert fac.ensure_shipped_factory(tmp_path / "data") == dest
