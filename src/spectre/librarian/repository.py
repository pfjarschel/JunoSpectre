"""PatchRepository: single access point for all patch sources.

Sources:
- `factory`: Juno-DS ROM presets. Metadata only (msb/lsb/pc). Read-only.
  Populated by tools/dump_factory_catalog.py. Audition via Bank Select + PC.
- `synth-user`: Juno-DS User bank (MSB 87, LSB 0..1, 256 slots). Metadata +
  optional cached full dump. Written via explicit "Sync from synth".
- `file`: `*.spectre` (v1 envelope) + `*.syx` under the user dir.
  Files are the source of truth; the DB only mirrors them and is rebuildable.

Only stdlib `sqlite3` is used. No ORM.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1

#: Auto-backup files are kept on disk (restorable by hand) but hidden from
#: the browser index so device saves don't clutter the user library.
AUTO_BACKUP_PREFIXES = ("BACKUP_", "BEFORE-REINIT_")


def is_auto_backup(path: str | Path) -> bool:
    """True for automatic slot-backup files (never indexed)."""
    from pathlib import Path as _P

    return _P(path).stem.startswith(AUTO_BACKUP_PREFIXES)


def data_root() -> Path:
    """Base dir for the librarian DB + user patch files.

    Overridable via JUNOSPECTRE_DATA_DIR (handy for services whose HOME
    is read-only or shared). Defaults to ~/.local/share/JunoSpectre.
    """
    override = os.environ.get("JUNOSPECTRE_DATA_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".local" / "share" / "JunoSpectre"


def default_user_dir() -> Path:
    return data_root() / "patches"


def default_db_path() -> Path:
    return data_root() / "librarian.db"


def factory_key(msb: int, lsb: int, pc: int, kind: str = "patch") -> str:
    kind = kind if kind in ("patch", "drum", "performance") else "patch"
    return f"factory:{kind}:{int(msb)}:{int(lsb)}:{int(pc)}"


def synth_user_key(msb: int, lsb: int, pc: int, kind: str = "patch") -> str:
    kind = kind if kind in ("patch", "drum", "performance") else "patch"
    return f"synth:{kind}:{int(msb)}:{int(lsb)}:{int(pc)}"


def legacy_factory_key(msb: int, lsb: int, pc: int) -> str:
    """Pre-kind key format (v1 dumps). Kept so old DB rows stay addressable."""
    return f"factory:{int(msb)}:{int(lsb)}:{int(pc)}"


def legacy_synth_user_key(msb: int, lsb: int, pc: int) -> str:
    return f"synth:{int(msb)}:{int(lsb)}:{int(pc)}"


def _tags_to_str(tags: Any) -> str:
    if isinstance(tags, str):
        return tags
    if isinstance(tags, (list, tuple)):
        return json.dumps([str(t) for t in tags])
    return "[]"


def _tags_from_str(s: Any) -> list[str]:
    if isinstance(s, list):
        return [str(t) for t in s]
    try:
        v = json.loads(s) if isinstance(s, str) and s else []
        return [str(t) for t in v] if isinstance(v, list) else []
    except (ValueError, TypeError):
        return []


class PatchRepository:
    """SQLite-backed index over factory/synth-user/file patch sources.

    Two databases:
    - user DB (writable): file index, synth-user slots, and the
      factory_meta overlay (user favorites/ratings/tags on factory rows).
    - factory DB (read-only, shipped with the app): static ROM catalog with
      a model_variant column ('xps30', 'juno-ds', ...). Resolved via
      ensure_shipped_factory() unless an explicit path is given.
    """

    def __init__(
        self,
        user_dir: str | Path | None = None,
        db_path: str | Path | None = None,
        factory_db_path: str | Path | bool | None = None,
        model_variant: str | None = None,
    ) -> None:
        import os as _os

        self.user_dir = Path(user_dir) if user_dir is not None else default_user_dir()
        self.db_path = Path(db_path) if db_path is not None else default_db_path()
        self.model_variant = (
            model_variant or _os.environ.get("JUNOSPECTRE_MODEL", "").strip() or "xps30"
        )
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.user_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Librarian data root: {self.db_path.parent} (db: {self.db_path.name})")
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self.ensure_schema()
        self._factory: sqlite3.Connection | None = None
        self._factory_path: Path | None = None
        self._attach_factory(factory_db_path)
        self._migrate_legacy_factory_rows()

    # ------------------------------------------------------------------ schema
    def ensure_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS patches (
              path TEXT PRIMARY KEY,
              source TEXT NOT NULL,
              name TEXT NOT NULL DEFAULT '',
              category TEXT NOT NULL DEFAULT '',
              tags TEXT NOT NULL DEFAULT '[]',
              favorite INTEGER NOT NULL DEFAULT 0,
              rating INTEGER NOT NULL DEFAULT 0,
              mtime INTEGER NOT NULL DEFAULT 0,
              hash TEXT NOT NULL DEFAULT '',
              msb INTEGER,
              lsb INTEGER,
              pc INTEGER,
              format_version INTEGER NOT NULL DEFAULT 1,
              kind TEXT NOT NULL DEFAULT 'patch'
            );
            CREATE INDEX IF NOT EXISTS idx_patches_source ON patches(source);
            CREATE INDEX IF NOT EXISTS idx_patches_name ON patches(name);
            CREATE INDEX IF NOT EXISTS idx_patches_category ON patches(category);
            CREATE INDEX IF NOT EXISTS idx_patches_fav ON patches(favorite);
            CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
            -- User customizations of shipped factory rows (the factory DB
            -- itself is read-only): keyed by factory path.
            CREATE TABLE IF NOT EXISTS factory_meta (
              path TEXT PRIMARY KEY,
              favorite INTEGER NOT NULL DEFAULT 0,
              rating INTEGER NOT NULL DEFAULT 0,
              tags TEXT NOT NULL DEFAULT '[]'
            );
            """
        )
        # Migration for DBs created before the kind column existed.
        # NOTE: the kind index is created after the ALTER, since CREATE INDEX
        # validates the column immediately and legacy tables lack it.
        try:
            cols = {r[1] for r in self._conn.execute("PRAGMA table_info(patches)").fetchall()}
            if "kind" not in cols:
                self._conn.execute("ALTER TABLE patches ADD COLUMN kind TEXT NOT NULL DEFAULT 'patch'")
            # Backfill legacy rows whose path lacks a kind infix.
            self._conn.execute(
                "UPDATE patches SET kind='patch' WHERE kind IS NULL OR kind=''")
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_patches_kind ON patches(kind)")
        except Exception as e:
            logger.warning(f"Librarian kind migration skipped: {e}")
        self._conn.execute(
            "INSERT OR IGNORE INTO meta(key, value) VALUES('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )
        self._conn.commit()

    # ------------------------------------------------- factory split DB
    def _attach_factory(self, factory_db_path: str | Path | bool | None) -> None:
        """Open the shipped read-only factory catalog (graceful when absent).

        factory_db_path=False explicitly disables the factory side (tests).
        """
        from .factory import ensure_shipped_factory

        if factory_db_path is False:
            return

        if factory_db_path is not None:
            cand = Path(factory_db_path)
            if not cand.is_file():
                logger.warning(f"Factory catalog not found: {cand}")
                return
        else:
            cand = ensure_shipped_factory(self.db_path.parent)
            if cand is None or not cand.is_file():
                logger.warning("No shipped factory catalog; factory search disabled.")
                return
        try:
            conn = sqlite3.connect(f"file:{cand}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            n = conn.execute("SELECT COUNT(*) AS n FROM patches").fetchone()["n"]
            self._factory = conn
            self._factory_path = cand
            logger.info(f"Factory catalog: {int(n)} rows from {cand}")
        except Exception as e:
            logger.warning(f"Could not open factory catalog {cand}: {e}")
            self._factory = None

    def _factory_variants(self) -> list[str]:
        if self._factory is None:
            return []
        try:
            rows = self._factory.execute(
                "SELECT DISTINCT model_variant FROM patches ORDER BY 1").fetchall()
            return [r[0] for r in rows if r[0]]
        except Exception:
            return []

    @staticmethod
    def _parse_legacy_factory_path(path: str) -> tuple[str, int, int, int] | None:
        """Legacy user-DB factory keys -> (kind, msb, lsb, pc)."""
        parts = (path or "").split(":")
        try:
            if len(parts) == 5 and parts[0] == "factory":
                _, kind, msb, lsb, pc = parts
                return kind, int(msb), int(lsb), int(pc)
            if len(parts) == 4 and parts[0] == "factory":
                _, msb, lsb, pc = parts
                return "patch", int(msb), int(lsb), int(pc)
        except (ValueError, TypeError):
            pass
        return None

    def _migrate_legacy_factory_rows(self) -> None:
        """Move pre-split factory rows out of the user DB.

        Only runs when the shipped factory DB actually contains our variant
        (else we'd delete sounds with nothing to replace them). User
        favorites/ratings/tags are preserved into the factory_meta overlay
        under the new variant-qualified path.
        """
        from .factory import factory_key

        try:
            legacy = self._conn.execute(
                "SELECT * FROM patches WHERE source='factory'").fetchall()
        except Exception:
            return
        if not legacy:
            return
        if self._factory is None or self.model_variant not in self._factory_variants():
            logger.warning(
                f"Keeping {len(legacy)} legacy factory rows: variant "
                f"'{self.model_variant}' not in shipped catalog.")
            return
        moved = kept = 0
        for r in legacy:
            parsed = self._parse_legacy_factory_path(r["path"])
            if parsed is None:
                continue
            kind, msb, lsb, pc = parsed
            new_path = factory_key(self.model_variant, kind, msb, lsb, pc)
            fav = int(r["favorite"] or 0)
            rating = int(r["rating"] or 0)
            tags = r["tags"] if r["tags"] not in (None, "[]", "") else "[]"
            # Overlay may already hold customizations under the legacy key
            # (set_favorite/set_tags on pre-split rows): remap them.
            old_ov = self._conn.execute(
                "SELECT * FROM factory_meta WHERE path=?", (r["path"],)).fetchone()
            if old_ov is not None:
                fav = fav or int(old_ov["favorite"] or 0)
                rating = max(rating, int(old_ov["rating"] or 0))
                if old_ov["tags"] not in (None, "[]", ""):
                    tags = old_ov["tags"]
                self._conn.execute("DELETE FROM factory_meta WHERE path=?", (r["path"],))
            if fav or rating or (tags not in ("[]", "")):
                self._conn.execute(
                    "INSERT INTO factory_meta(path, favorite, rating, tags)"
                    " VALUES(?,?,?,?)"
                    " ON CONFLICT(path) DO UPDATE SET favorite=excluded.favorite,"
                    " rating=excluded.rating, tags=excluded.tags",
                    (new_path, fav, rating, _tags_to_str(_tags_from_str(tags))),
                )
                kept += 1
            moved += 1
        self._conn.execute("DELETE FROM patches WHERE source='factory'")
        self._conn.commit()
        logger.info(f"Factory split migration: {moved} legacy rows removed, "
                    f"{kept} customizations kept in overlay.")

    def _overlay_map(self, paths: list[str] | None = None) -> dict[str, dict]:
        try:
            if paths:
                rows = self._conn.execute(
                    "SELECT * FROM factory_meta WHERE path IN (%s)" % ",".join("?" * len(paths)),
                    paths).fetchall()
            else:
                rows = self._conn.execute("SELECT * FROM factory_meta").fetchall()
        except Exception:
            return {}
        return {r["path"]: {"favorite": bool(r["favorite"]), "rating": int(r["rating"]),
                            "tags": _tags_from_str(r["tags"])} for r in rows}

    def _overlay_upsert(self, path: str, favorite: bool | None = None,
                        rating: int | None = None, tags: list[str] | None = None) -> None:
        cur = self._conn.execute(
            "SELECT * FROM factory_meta WHERE path=?", (path,)).fetchone()
        fav = int(bool(favorite)) if favorite is not None else (int(cur["favorite"]) if cur else 0)
        rat = int(rating) if rating is not None else (int(cur["rating"]) if cur else 0)
        tgs = _tags_to_str(tags) if tags is not None else (cur["tags"] if cur else "[]")
        self._conn.execute(
            "INSERT INTO factory_meta(path, favorite, rating, tags) VALUES(?,?,?,?)"
            " ON CONFLICT(path) DO UPDATE SET favorite=excluded.favorite,"
            " rating=excluded.rating, tags=excluded.tags",
            (path, fav, rat, tgs))
        self._conn.commit()

    def _factory_search(self, query: str, cats: list[str] | None, single_cat: str,
                        favorites_only: bool, kind: str | None,
                        limit: int) -> list[dict[str, Any]]:
        if self._factory is None:
            return []
        sql = ("SELECT path, kind, name, category, tags, msb, lsb, pc FROM patches"
               " WHERE model_variant=?")
        args: list[Any] = [self.model_variant]
        if kind:
            sql += " AND kind=?"
            args.append(kind)
        if cats:
            sql += " AND category IN (%s)" % ",".join("?" * len(cats))
            args += cats
        elif single_cat and single_cat.upper() != "ALL":
            sql += " AND category=? COLLATE NOCASE"
            args.append(single_cat)
        q = (query or "").strip()
        if q:
            sql += " AND (name LIKE ? ESCAPE '\\' OR tags LIKE ? ESCAPE '\\')"
            like = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            args += [like, like]
        sql += " ORDER BY name COLLATE NOCASE ASC LIMIT ?"
        args.append(int(limit))
        try:
            rows = self._factory.execute(sql, args).fetchall()
        except Exception as e:
            logger.warning(f"Factory search failed: {e}")
            return []
        overlay = self._overlay_map([r["path"] for r in rows])
        out = []
        for r in rows:
            ov = overlay.get(r["path"], {})
            out.append({
                "path": r["path"], "source": "factory", "name": r["name"],
                "category": r["category"], "tags": ov.get("tags", _tags_from_str(r["tags"])),
                "favorite": ov.get("favorite", False), "rating": ov.get("rating", 0),
                "mtime": 0, "hash": "", "msb": r["msb"], "lsb": r["lsb"], "pc": r["pc"],
                "format_version": 0, "kind": r["kind"] or "patch",
            })
        if favorites_only:
            out = [d for d in out if d["favorite"]]
        return out

    def close(self) -> None:
        try:
            self._conn.commit()
            self._conn.close()
        except Exception:
            pass
        try:
            if self._factory is not None:
                self._factory.close()
        except Exception:
            pass
        self._factory = None

    def __enter__(self) -> "PatchRepository":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    # ------------------------------------------------------------- file index
    @staticmethod
    def _hash_bytes(data: bytes) -> str:
        return hashlib.sha1(data).hexdigest()[:16]

    def _index_spectre_file(self, f: Path, st_mtime: int) -> None:
        from ..core.spectre_format import describe_for_index, load_spectre

        try:
            loaded = load_spectre(f)
        except Exception as e:
            logger.warning(f"Librarian: skipping unreadable {f}: {e}")
            return
        name, category, tags, fav, rating, version = describe_for_index(loaded)
        raw = f.read_bytes()
        file_kind = str(loaded.get("kind") or "patch")
        self._conn.execute(
            """INSERT INTO patches(path, source, name, category, tags, favorite,
                   rating, mtime, hash, msb, lsb, pc, format_version, kind)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(path) DO UPDATE SET
                 source='file', name=excluded.name, category=excluded.category,
                 tags=excluded.tags, favorite=excluded.favorite, rating=excluded.rating,
                 mtime=excluded.mtime, hash=excluded.hash,
                 msb=excluded.msb, lsb=excluded.lsb, pc=excluded.pc,
                 format_version=excluded.format_version, kind=excluded.kind""",
            (
                str(f), "file", name, category, _tags_to_str(tags),
                int(bool(fav)), int(rating or 0), int(st_mtime),
                self._hash_bytes(raw),
                (loaded["synth_ref"] or {}).get("msb") if loaded.get("synth_ref") else None,
                (loaded["synth_ref"] or {}).get("lsb") if loaded.get("synth_ref") else None,
                (loaded["synth_ref"] or {}).get("pc") if loaded.get("synth_ref") else None,
                int(version),
                file_kind,
            ),
        )

    def _index_syx_file(self, f: Path, st_mtime: int) -> None:
        # .syx has no embedded librarian meta: name = stem, fav/rating live in DB only.
        cur = self._conn.execute("SELECT favorite, rating FROM patches WHERE path=?", (str(f),)).fetchone()
        fav = int(cur["favorite"]) if cur else 0
        rating = int(cur["rating"]) if cur else 0
        raw = f.read_bytes()
        self._conn.execute(
            """INSERT INTO patches(path, source, name, category, tags, favorite,
                   rating, mtime, hash, format_version)
               VALUES(?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(path) DO UPDATE SET
                 source='file', name=excluded.name,
                 mtime=excluded.mtime, hash=excluded.hash""",
            (str(f), "file", f.stem, "", "[]", fav, rating, int(st_mtime), self._hash_bytes(raw), 0),
        )

    def rescan_files(self) -> dict[str, int]:
        """Rescan user_dir for *.spectre/*.syx. Returns {added, updated, removed}.

        Automatic slot backups (BACKUP_*, BEFORE-REINIT_*) live on disk but
        are never indexed, and stale rows for them are purged.
        """
        seen: set[str] = set()
        added = updated = 0
        for pattern in ("*.spectre", "*.syx"):
            for f in sorted(self.user_dir.rglob(pattern)):
                if not f.is_file() or is_auto_backup(f):
                    continue
                seen.add(str(f))
                try:
                    st_mtime = int(f.stat().st_mtime)
                except OSError:
                    continue
                cur = self._conn.execute(
                    "SELECT mtime, hash FROM patches WHERE path=?", (str(f),)
                ).fetchone()
                if cur is not None and int(cur["mtime"]) == st_mtime:
                    continue  # unchanged; trust cache
                is_new = cur is None
                if f.suffix == ".spectre":
                    self._index_spectre_file(f, st_mtime)
                else:
                    self._index_syx_file(f, st_mtime)
                if is_new:
                    added += 1
                else:
                    updated += 1
        # Remove entries whose files vanished (only source='file')
        removed = 0
        for row in self._conn.execute("SELECT path FROM patches WHERE source='file'").fetchall():
            if row["path"] not in seen:
                self._conn.execute("DELETE FROM patches WHERE path=?", (row["path"],))
                removed += 1
        self._conn.commit()
        return {"added": added, "updated": updated, "removed": removed}

    # ------------------------------------------------------- factory/synth DB
    def upsert_entry(
        self, source: str, kind: str, msb: int, lsb: int, pc: int,
        name: str, category: str = "", tags: Any = None,
    ) -> str:
        """Insert or refresh one ROM/synth row. Never clobbers favorite/rating.

        Returns the row path (PK). `source` is 'factory'|'synth-user',
        `kind` is 'patch'|'drum'|'performance'.
        """
        kind = kind if kind in ("patch", "drum", "performance") else "patch"
        path = factory_key(msb, lsb, pc, kind) if source == "factory" else synth_user_key(msb, lsb, pc, kind)
        self._conn.execute(
            """INSERT INTO patches(path, source, name, category, tags, favorite,
                   rating, mtime, hash, msb, lsb, pc, format_version, kind)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(path) DO UPDATE SET
                 name=excluded.name, category=excluded.category,
                 tags=excluded.tags, msb=excluded.msb, lsb=excluded.lsb,
                 pc=excluded.pc, kind=excluded.kind
               -- NOTE: never overwrite favorite/rating/mtime/hash here
            """,
            (path, source, str(name), str(category),
             _tags_to_str(tags or []), 0, 0, 0, "",
             int(msb), int(lsb), int(pc), 0, kind),
        )
        return path

    def upsert_factory(
        self, msb: int, lsb: int, pc: int, name: str, category: str = "",
        tags: Any = None, kind: str = "patch",
    ) -> None:
        self.upsert_entry("factory", kind, msb, lsb, pc, name, category, tags)

    def bulk_upsert_factory(self, rows: list[dict[str, Any]]) -> int:
        # Preserve user-set favorite/rating on existing rows: loop (dumps are ~2k rows).
        n = 0
        for r in rows:
            self.upsert_entry(
                str(r.get("source", "factory")), str(r.get("kind", "patch")),
                int(r["msb"]), int(r["lsb"]), int(r["pc"]),
                str(r.get("name", "")), str(r.get("category", "")),
                r.get("tags", []),
            )
            n += 1
        self._conn.commit()
        return n

    def upsert_synth_user(
        self, msb: int, lsb: int, pc: int, name: str, category: str = "",
        kind: str = "patch",
    ) -> None:
        self.upsert_entry("synth-user", kind, msb, lsb, pc, name, category)
        self._conn.commit()

    def count(self, source: Optional[str] = None, kind: Optional[str] = None) -> int:
        if source == "factory" and self._factory is not None:
            return self._factory_count(kind)
        sql = "SELECT COUNT(*) AS n FROM patches WHERE 1=1"
        args: list[Any] = []
        if source:
            sql += " AND source=?"
            args.append(source)
        elif self._factory is not None:
            # Union total: user rows (never factory post-migration) + factory.
            n = int(self._conn.execute("SELECT COUNT(*) AS n FROM patches"
                                       + (" WHERE kind=?" if kind else ""),
                                       ([kind] if kind else [])).fetchone()["n"])
            return n + self._factory_count(kind)
        if kind:
            sql += " AND kind=?"
            args.append(kind)
        return int(self._conn.execute(sql, args).fetchone()["n"])

    def _factory_count(self, kind: Optional[str] = None) -> int:
        if self._factory is None:
            return 0
        try:
            if kind:
                row = self._factory.execute(
                    "SELECT COUNT(*) AS n FROM patches WHERE model_variant=? AND kind=?",
                    (self.model_variant, kind)).fetchone()
            else:
                row = self._factory.execute(
                    "SELECT COUNT(*) AS n FROM patches WHERE model_variant=?",
                    (self.model_variant,)).fetchone()
            return int(row["n"])
        except Exception:
            return 0

    # ----------------------------------------------------------------- query
    def search(
        self,
        query: str = "",
        category: str = "ALL",
        favorites_only: bool = False,
        source: Optional[str] = None,
        limit: int = 500,
        categories: Optional[list[str]] = None,
        kind: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        cats = [c for c in (categories or []) if c]
        if source == "factory" and self._factory is not None:
            return self._factory_search(query, cats or None, category,
                                        favorites_only, kind, limit)
        sql = "SELECT * FROM patches WHERE 1=1"
        args: list[Any] = []
        if source:
            sql += " AND source=?"
            args.append(source)
        if kind:
            sql += " AND kind=?"
            args.append(kind)
        if favorites_only:
            sql += " AND favorite=1"
        if cats:
            sql += " AND category IN (%s)" % ",".join("?" * len(cats))
            args += cats
        elif category and category.upper() != "ALL":
            sql += " AND category=? COLLATE NOCASE"
            args.append(category)
        q = (query or "").strip()
        if q:
            sql += " AND (name LIKE ? ESCAPE '\\' OR tags LIKE ? ESCAPE '\\')"
            like = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            args += [like, like]
        sql += " ORDER BY favorite DESC, name COLLATE NOCASE ASC LIMIT ?"
        args.append(int(limit))
        rows = self._conn.execute(sql, args).fetchall()
        user_rows = [self._row_to_dict(r) for r in rows]
        if source is not None or self._factory is None:
            return user_rows
        # Union with the shipped factory catalog (user rows never hold
        # factory data post-migration, so no dedup needed).
        factory_rows = self._factory_search(query, cats or None, category,
                                            favorites_only, kind, limit)
        merged = user_rows + factory_rows
        merged.sort(key=lambda d: (not d["favorite"], d["name"].casefold()))
        return merged[: int(limit)]

    def get(self, path: str) -> Optional[dict[str, Any]]:
        row = self._conn.execute("SELECT * FROM patches WHERE path=?", (path,)).fetchone()
        if row:
            return self._row_to_dict(row)
        if self._factory is not None and (path or "").startswith("factory:"):
            try:
                r = self._factory.execute(
                    "SELECT * FROM patches WHERE path=? AND model_variant=?",
                    (path, self.model_variant)).fetchone()
            except Exception:
                return None
            if r is None:
                return None
            ov = self._overlay_map([path]).get(path, {})
            return {
                "path": r["path"], "source": "factory", "name": r["name"],
                "category": r["category"], "tags": ov.get("tags", _tags_from_str(r["tags"])),
                "favorite": ov.get("favorite", False), "rating": ov.get("rating", 0),
                "mtime": 0, "hash": "", "msb": r["msb"], "lsb": r["lsb"], "pc": r["pc"],
                "format_version": 0, "kind": r["kind"] or "patch",
            }
        return None

    def list_categories(self, source: Optional[str] = None) -> list[str]:
        cats: set[str] = set()
        if source != "factory":
            sql = "SELECT DISTINCT category FROM patches"
            args: list[Any] = []
            if source:
                sql += " WHERE source=?"
                args.append(source)
            rows = self._conn.execute(sql, args).fetchall()
            cats.update(r["category"] for r in rows if r["category"])
        if source in (None, "factory") and self._factory is not None:
            try:
                rows = self._factory.execute(
                    "SELECT DISTINCT category FROM patches WHERE model_variant=?",
                    (self.model_variant,)).fetchall()
                cats.update(r[0] for r in rows if r[0])
            except Exception:
                pass
        return sorted(cats)

    @staticmethod
    def _row_to_dict(r: sqlite3.Row) -> dict[str, Any]:
        try:
            kind = r["kind"]
        except (IndexError, KeyError):
            kind = "patch"
        return {
            "path": r["path"],
            "source": r["source"],
            "name": r["name"],
            "category": r["category"],
            "tags": _tags_from_str(r["tags"]),
            "favorite": bool(r["favorite"]),
            "rating": int(r["rating"]),
            "mtime": int(r["mtime"]),
            "hash": r["hash"],
            "msb": r["msb"],
            "lsb": r["lsb"],
            "pc": r["pc"],
            "format_version": int(r["format_version"]),
            "kind": kind or "patch",
        }

    # ------------------------------------------------------------------ write
    def touch_file_row(self, path: str) -> None:
        """Refresh DB row from file after an in-file meta edit."""
        f = Path(path)
        if is_auto_backup(f):
            return
        if f.suffix == ".spectre" and f.exists():
            try:
                st_mtime = int(f.stat().st_mtime)
            except OSError:
                return
            self._index_spectre_file(f, st_mtime)
            self._conn.commit()

    _touch_file_row = touch_file_row

    def set_favorite(self, path: str, favorite: bool) -> bool:
        row = self.get(path)
        if row is None:
            return False
        if row["source"] == "file" and Path(path).suffix == ".spectre":
            # Meta travels with the file: rewrite file, then re-index.
            try:
                from ..core.spectre_format import load_spectre, save_spectre

                loaded = load_spectre(path)
                loaded["meta"]["favorite"] = bool(favorite)
                save_spectre(
                    path, loaded["patch_state"], meta=loaded["meta"],
                    spectre=loaded["spectre"], synth_ref=loaded["synth_ref"],
                    kind=loaded["kind"], extra=loaded["extra"],
                )
                self._touch_file_row(path)
                return True
            except Exception as e:
                logger.warning(f"set_favorite file rewrite failed for {path}: {e}")
                return False
        if row["source"] == "factory":
            # Shipped DB is read-only: favorites live in the user overlay.
            # Rows still sitting in the user table (pre-migration) are
            # updated too so both read paths agree.
            self._overlay_upsert(path, favorite=bool(favorite))
            self._conn.execute(
                "UPDATE patches SET favorite=? WHERE path=?", (int(bool(favorite)), path)
            )
            self._conn.commit()
            return True
        self._conn.execute(
            "UPDATE patches SET favorite=? WHERE path=?", (int(bool(favorite)), path)
        )
        self._conn.commit()
        return True

    def set_tags(self, path: str, tags: list[str]) -> bool:
        row = self.get(path)
        if row is None:
            return False
        tags = [str(t)[:32] for t in (tags or [])[:16]]
        if row["source"] == "file" and Path(path).suffix == ".spectre":
            try:
                from ..core.spectre_format import load_spectre, save_spectre

                loaded = load_spectre(path)
                loaded["meta"]["tags"] = tags
                save_spectre(
                    path, loaded["patch_state"], meta=loaded["meta"],
                    spectre=loaded["spectre"], synth_ref=loaded["synth_ref"],
                    kind=loaded["kind"], extra=loaded["extra"],
                )
                self._touch_file_row(path)
                return True
            except Exception as e:
                logger.warning(f"set_tags file rewrite failed for {path}: {e}")
                return False
        if row["source"] == "factory":
            self._overlay_upsert(path, tags=tags)
            self._conn.execute("UPDATE patches SET tags=? WHERE path=?",
                               (_tags_to_str(tags), path))
            self._conn.commit()
            return True
        self._conn.execute("UPDATE patches SET tags=? WHERE path=?", (_tags_to_str(tags), path))
        self._conn.commit()
        return True

    def import_file(self, src: str | Path, dest_name: Optional[str] = None) -> Path:
        """Copy a .spectre/.syx from USB/disk into the user dir and index it."""
        s = Path(src)
        if s.suffix not in (".spectre", ".syx"):
            raise ValueError(f"unsupported import type: {s.suffix}")
        dest = self.user_dir / (dest_name or s.name)
        if dest.suffix != s.suffix:
            dest = dest.with_suffix(s.suffix)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(s, dest)
        self._touch_file_row(str(dest)) if dest.suffix == ".spectre" else self._index_and_commit(dest)
        return dest

    def _index_and_commit(self, f: Path) -> None:
        try:
            st_mtime = int(f.stat().st_mtime)
        except OSError:
            return
        if f.suffix == ".spectre":
            self._index_spectre_file(f, st_mtime)
        else:
            self._index_syx_file(f, st_mtime)
        self._conn.commit()

    def save_current_as(
        self,
        patch_state: Any,
        name: str,
        category: str = "",
        tags: Optional[list[str]] = None,
        favorite: bool = False,
        spectre: Optional[dict[str, Any]] = None,
        synth_ref: Optional[dict[str, Any]] = None,
        filename: Optional[str] = None,
        kind: str = "patch",
    ) -> Path:
        """Persist the live (possibly Pi-only) edit buffer as a .spectre file."""
        from ..core.spectre_format import save_spectre

        safe = "".join(c if (c.isalnum() or c in ("-", "_", " ")) else "_" for c in name).strip()
        safe = safe or "Untitled"
        target = self.user_dir / (filename or f"{safe}.spectre")
        meta = {
            "name": name[:12], "category": category, "tags": tags or [],
            "favorite": favorite, "rating": 0, "comment": "", "author": "",
        }
        out = save_spectre(target, patch_state, meta=meta, spectre=spectre,
                           synth_ref=synth_ref, kind=kind)
        self._touch_file_row(str(out))
        return out

    def delete_file(self, path: str) -> bool:
        row = self.get(path)
        if row is None or row["source"] != "file":
            return False
        try:
            Path(path).unlink(missing_ok=True)
        except OSError:
            return False
        self._conn.execute("DELETE FROM patches WHERE path=?", (path,))
        self._conn.commit()
        return True

    def backup_mtime(self) -> int:
        return int(time.time())
