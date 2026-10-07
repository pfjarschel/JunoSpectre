"""PatchRepository: single access point for all patch sources.

Sources:
- `factory`: Juno-DS ROM presets. Metadata only (msb/lsb/pc). Read-only.
  Populated by scripts/dump_factory_catalog.py. Audition via Bank Select + PC.
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
import shutil
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1


def default_user_dir() -> Path:
    return Path.home() / ".local" / "share" / "JunoSpectre" / "patches"


def default_db_path() -> Path:
    return Path.home() / ".local" / "share" / "JunoSpectre" / "librarian.db"


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
    """SQLite-backed index over factory/synth-user/file patch sources."""

    def __init__(
        self,
        user_dir: str | Path | None = None,
        db_path: str | Path | None = None,
    ) -> None:
        self.user_dir = Path(user_dir) if user_dir is not None else default_user_dir()
        self.db_path = Path(db_path) if db_path is not None else default_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.user_dir.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self.ensure_schema()

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

    def close(self) -> None:
        try:
            self._conn.commit()
            self._conn.close()
        except Exception:
            pass

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
        self._conn.execute(
            """INSERT INTO patches(path, source, name, category, tags, favorite,
                   rating, mtime, hash, msb, lsb, pc, format_version)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(path) DO UPDATE SET
                 source='file', name=excluded.name, category=excluded.category,
                 tags=excluded.tags, favorite=excluded.favorite, rating=excluded.rating,
                 mtime=excluded.mtime, hash=excluded.hash,
                 msb=excluded.msb, lsb=excluded.lsb, pc=excluded.pc,
                 format_version=excluded.format_version""",
            (
                str(f), "file", name, category, _tags_to_str(tags),
                int(bool(fav)), int(rating or 0), int(st_mtime),
                self._hash_bytes(raw),
                (loaded["synth_ref"] or {}).get("msb") if loaded.get("synth_ref") else None,
                (loaded["synth_ref"] or {}).get("lsb") if loaded.get("synth_ref") else None,
                (loaded["synth_ref"] or {}).get("pc") if loaded.get("synth_ref") else None,
                int(version),
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
        """Rescan user_dir for *.spectre/*.syx. Returns {added, updated, removed}."""
        seen: set[str] = set()
        added = updated = 0
        for pattern in ("*.spectre", "*.syx"):
            for f in sorted(self.user_dir.rglob(pattern)):
                if not f.is_file():
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
        sql = "SELECT COUNT(*) AS n FROM patches WHERE 1=1"
        args: list[Any] = []
        if source:
            sql += " AND source=?"
            args.append(source)
        if kind:
            sql += " AND kind=?"
            args.append(kind)
        return int(self._conn.execute(sql, args).fetchone()["n"])

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
        cats = [c for c in (categories or []) if c]
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
        return [self._row_to_dict(r) for r in rows]

    def get(self, path: str) -> Optional[dict[str, Any]]:
        row = self._conn.execute("SELECT * FROM patches WHERE path=?", (path,)).fetchone()
        return self._row_to_dict(row) if row else None

    def list_categories(self, source: Optional[str] = None) -> list[str]:
        sql = "SELECT DISTINCT category FROM patches"
        args: list[Any] = []
        if source:
            sql += " WHERE source=?"
            args.append(source)
        rows = self._conn.execute(sql, args).fetchall()
        return sorted({r["category"] for r in rows if r["category"]})

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
    def _touch_file_row(self, path: str) -> None:
        """Refresh DB row from file after an in-file meta edit."""
        f = Path(path)
        if f.suffix == ".spectre" and f.exists():
            try:
                st_mtime = int(f.stat().st_mtime)
            except OSError:
                return
            self._index_spectre_file(f, st_mtime)
            self._conn.commit()

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
        out = save_spectre(target, patch_state, meta=meta, spectre=spectre, synth_ref=synth_ref)
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
