"""QAbstractListModel over PatchRepository for LibrarianView.qml.

Replaces the hardcoded JS `patchList` array with a filterable model:
QML binds to roles (name, category, source, favorite, ...) and drives
filtering through `refresh()` (wired to a QSortFilterProxyModel if needed).

Audition itself stays in Python (Bank Select + PC for factory/synth-user,
full DT1 push for files) — the model only carries the address (msb/lsb/pc)
and file path.
"""

from __future__ import annotations

from typing import Any, Optional

from PyQt6.QtCore import QAbstractListModel, QModelIndex, Qt, pyqtSlot

from ..librarian.repository import PatchRepository


class PatchListModel(QAbstractListModel):
    PathRole = Qt.ItemDataRole.UserRole + 1
    SourceRole = Qt.ItemDataRole.UserRole + 2
    NameRole = Qt.ItemDataRole.UserRole + 3
    CategoryRole = Qt.ItemDataRole.UserRole + 4
    TagsRole = Qt.ItemDataRole.UserRole + 5
    FavoriteRole = Qt.ItemDataRole.UserRole + 6
    RatingRole = Qt.ItemDataRole.UserRole + 7
    MsbRole = Qt.ItemDataRole.UserRole + 8
    LsbRole = Qt.ItemDataRole.UserRole + 9
    PcRole = Qt.ItemDataRole.UserRole + 10
    KindRole = Qt.ItemDataRole.UserRole + 11

    _ROLE_NAMES = {
        PathRole: b"path",
        SourceRole: b"source",
        NameRole: b"name",
        CategoryRole: b"category",
        TagsRole: b"tags",
        FavoriteRole: b"favorite",
        RatingRole: b"rating",
        MsbRole: b"msb",
        LsbRole: b"lsb",
        PcRole: b"pc",
        KindRole: b"kind",
    }

    def __init__(self, repository: Optional[PatchRepository] = None, parent=None):
        super().__init__(parent)
        self._repo = repository
        self._rows: list[dict[str, Any]] = []
        self._query = ""
        self._category = "ALL"
        self._categories: list[str] = []
        self._favorites_only = False
        self._source: Optional[str] = None
        self._kind: Optional[str] = None

    # ------------------------------------------------------------- Qt basics
    def roleNames(self) -> dict[int, bytes]:
        return dict(self._ROLE_NAMES)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None
        row = self._rows[index.row()]
        if role == self.PathRole:
            return row["path"]
        if role == self.SourceRole:
            return row["source"]
        if role == self.NameRole:
            return row["name"]
        if role == self.CategoryRole:
            return row["category"]
        if role == self.TagsRole:
            return ", ".join(row.get("tags", []))
        if role == self.FavoriteRole:
            return bool(row.get("favorite", False))
        if role == self.RatingRole:
            return int(row.get("rating", 0))
        if role == self.MsbRole:
            return row.get("msb") if row.get("msb") is not None else -1
        if role == self.LsbRole:
            return row.get("lsb") if row.get("lsb") is not None else -1
        if role == self.PcRole:
            return row.get("pc") if row.get("pc") is not None else -1
        if role == self.KindRole:
            return row.get("kind", "patch")
        if role == Qt.ItemDataRole.DisplayRole:
            return row["name"]
        return None

    # ------------------------------------------------------------------ API
    @pyqtSlot(str, str, bool, str, int, str, str)
    def refresh(self, query: str = "", category: str = "ALL",
                favorites_only: bool = False, source: str = "",
                limit: int = 500, categoriesCsv: str = "",
                kind: str = "") -> int:
        """Re-query the repository; returns row count. Empty source = all.

        categoriesCsv is a comma-separated list of Roland 3-letter codes
        (e.g. "HLD,SLD") used by the touch chips; it wins over `category`.
        kind filters 'patch'|'drum'|'performance' (empty = all).
        """
        self._query = query or ""
        self._category = category or "ALL"
        self._categories = [c.strip() for c in (categoriesCsv or "").split(",") if c.strip()]
        self._favorites_only = bool(favorites_only)
        self._source = source or None
        self._kind = kind or None
        return self._reload(limit=limit)

    def _reload(self, limit: int = 500) -> int:
        rows = self._repo.search(
            query=self._query, category=self._category,
            favorites_only=self._favorites_only, source=self._source, limit=limit,
            categories=self._categories or None, kind=self._kind,
        ) if self._repo is not None else []
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()
        return len(self._rows)

    @pyqtSlot(int, result="QVariantMap")
    def get(self, row: int) -> dict[str, Any]:
        if 0 <= row < len(self._rows):
            return dict(self._rows[row])
        return {}

    @pyqtSlot(int, bool, result=bool)
    def setFavorite(self, row: int, favorite: bool) -> bool:
        if self._repo is None or not (0 <= row < len(self._rows)):
            return False
        ok = self._repo.set_favorite(self._rows[row]["path"], bool(favorite))
        if ok:
            self._rows[row]["favorite"] = bool(favorite)
            idx = self.index(row, 0)
            self.dataChanged.emit(idx, idx, [self.FavoriteRole])
        return ok

    @pyqtSlot(int, result=bool)
    def toggleFavorite(self, row: int) -> bool:
        if not (0 <= row < len(self._rows)):
            return False
        return self.setFavorite(row, not bool(self._rows[row].get("favorite", False)))

    def setRepository(self, repository: PatchRepository) -> None:
        self._repo = repository
        self._reload()
