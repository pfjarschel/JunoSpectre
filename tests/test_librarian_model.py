"""Tests for PatchListModel (QML backing model)."""

import pytest

PyQt6 = pytest.importorskip("PyQt6.QtCore")
from PyQt6.QtCore import QCoreApplication

from src.spectre.core.patch_state import PatchState
from src.spectre.core.spectre_format import save_spectre
from src.spectre.librarian.repository import PatchRepository
from src.spectre.ui.librarian_model import PatchListModel


@pytest.fixture(scope="module")
def qapp():
    return QCoreApplication.instance() or QCoreApplication([])


def test_model_roles_filter_favorite(tmp_path, qapp):
    repo = PatchRepository(user_dir=tmp_path / "p", db_path=tmp_path / "d.db")
    ps = PatchState.create_init_patch()
    save_spectre(repo.user_dir / "a.spectre", ps, meta={"name": "ALPHA", "category": "BASS", "favorite": True})
    save_spectre(repo.user_dir / "b.spectre", ps, meta={"name": "BETA", "category": "BASS"})
    repo.rescan_files()
    repo.bulk_upsert_factory([{"msb": 87, "lsb": 64, "pc": 0, "name": "Grand Pno DS"}])

    model = PatchListModel(repo)
    assert model.refresh("", "ALL", False, "", 500) == 3
    assert model.rowCount() == 3
    idx = model.index(0, 0)
    assert model.data(idx, PatchListModel.NameRole) in ("ALPHA", "BETA", "Grand Pno DS")
    assert model.data(idx, PatchListModel.KindRole) == "patch"

    assert model.refresh("", "BASS", False, "", 500) == 2
    assert model.refresh("", "ALL", True, "", 500) == 1
    assert model.get(0)["name"] == "ALPHA"

    # categoriesCsv (chip codes) wins over single category
    assert model.refresh("", "ALL", False, "", 500, "BASS") == 2
    assert model.refresh("", "ALL", False, "", 500, "PNO") == 0
    assert model.refresh("", "BASS", False, "", 500, "PNO") == 0  # csv wins

    # toggle favorite writes through to file + DB
    model.refresh("", "ALL", False, "", 500)
    assert model.toggleFavorite(0) is True
    assert model.get(0)["favorite"] is False
    assert repo.search("ALPHA")[0]["favorite"] is False
    repo.close()
