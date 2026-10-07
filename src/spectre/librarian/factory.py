"""Shipped read-only factory catalog (ROM presets, drums, performances).

Why a separate DB: the factory catalog is static data dumped once from
hardware. Every install would otherwise have to run the hours-long full
dump. Instead we ship a prebuilt SQLite file in the repo and copy it to the
data dir on first boot. User data (files index, synth-user slots, favorites)
lives in the separate writable user DB; per-row user favorites/ratings/tags
on factory rows live in the user DB overlay table, never in this file.

DS vs XPS: preset ROM differs per model and the SysEx identity reply does
NOT distinguish them (same family code), so rows carry a model_variant
('xps30', 'juno-ds', ...). The app filters by the configured variant. Only
variants actually dumped exist here; a missing variant yields zero factory
rows (user DB still works) instead of wrong names.
"""

from __future__ import annotations

import logging
import shutil
import sqlite3
from importlib.resources import files as _res_files
from pathlib import Path
from typing import Any, Iterable

logger = logging.getLogger(__name__)

FACTORY_DB_NAME = "factory.db"
CATALOG_VERSION = 1


def factory_key(variant: str, kind: str, msb: int, lsb: int, pc: int) -> str:
    kind = kind if kind in ("patch", "drum", "performance") else "patch"
    return f"factory:{variant}:{kind}:{int(msb)}:{int(lsb)}:{int(pc)}"


def shipped_factory_db() -> Path | None:
    """Repo-shipped factory DB, or None (e.g. source checkout without it)."""
    try:
        p = _res_files("spectre.assets.librarian") / FACTORY_DB_NAME
        if p.is_file():
            return Path(str(p))
    except (ImportError, TypeError, ValueError) as e:
        logger.debug(f"shipped factory db lookup failed: {e}")
    # Fallback for plain source checkouts (no installed package data).
    here = Path(__file__).resolve()
    for cand in [
        here.parent.parent / "assets" / "librarian" / FACTORY_DB_NAME,
        here.parent / "assets" / FACTORY_DB_NAME,
    ]:
        if cand.is_file():
            return cand
    return None


def ensure_shipped_factory(data_root: Path) -> Path | None:
    """Copy the shipped factory.db into the data dir when missing/stale.

    Returns the data-dir path, or None when nothing is shipped.
    Never overwrites a newer copy (compare catalog_version in meta).
    """
    src = shipped_factory_db()
    data_root.mkdir(parents=True, exist_ok=True)
    dest = data_root / FACTORY_DB_NAME
    if src is None:
        return dest if dest.is_file() else None
    try:
        if dest.is_file():
            try:
                have = factory_catalog_version(dest)
            except Exception:
                have = -1
            if have >= CATALOG_VERSION:
                return dest
        shutil.copy2(src, dest)
        logger.info(f"Installed factory catalog v{CATALOG_VERSION} -> {dest}")
    except OSError as e:
        logger.warning(f"Could not install factory catalog: {e}")
        return dest if dest.is_file() else None
    return dest


def factory_catalog_version(path: str | Path) -> int:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        row = conn.execute("SELECT value FROM meta WHERE key='catalog_version'").fetchone()
        return int(row[0]) if row else 0
    finally:
        conn.close()


def factory_variants(path: str | Path) -> list[str]:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        rows = conn.execute("SELECT DISTINCT model_variant FROM patches ORDER BY 1").fetchall()
        return [r[0] for r in rows if r[0]]
    finally:
        conn.close()


def build_factory_db(path: str | Path, rows: Iterable[dict[str, Any]],
                     model_variant: str) -> int:
    """(Re)build a shippable factory.db from dump rows. Returns row count."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(str(path))
    try:
        conn.executescript(
            """
            CREATE TABLE patches (
              path TEXT PRIMARY KEY,
              model_variant TEXT NOT NULL DEFAULT '',
              source TEXT NOT NULL DEFAULT 'factory',
              kind TEXT NOT NULL DEFAULT 'patch',
              name TEXT NOT NULL DEFAULT '',
              category TEXT NOT NULL DEFAULT '',
              tags TEXT NOT NULL DEFAULT '[]',
              msb INTEGER, lsb INTEGER, pc INTEGER
            );
            CREATE INDEX idx_factory_variant ON patches(model_variant);
            CREATE INDEX idx_factory_name ON patches(name);
            CREATE INDEX idx_factory_cat ON patches(category);
            CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
            """
        )
        n = 0
        for r in rows:
            if str(r.get("source", "factory")) != "factory":
                continue
            kind = str(r.get("kind", "patch"))
            msb, lsb, pc = int(r["msb"]), int(r["lsb"]), int(r["pc"])
            import json as _json
            tags = r.get("tags", [])
            conn.execute(
                "INSERT OR REPLACE INTO patches"
                "(path, model_variant, source, kind, name, category, tags, msb, lsb, pc)"
                " VALUES(?,?,?,?,?,?,?,?,?,?)",
                (factory_key(model_variant, kind, msb, lsb, pc), model_variant,
                 "factory", kind if kind in ("patch", "drum", "performance") else "patch",
                 str(r.get("name", "")), str(r.get("category", "")),
                 _json.dumps([str(t) for t in tags]) if isinstance(tags, list) else "[]",
                 msb, lsb, pc),
            )
            n += 1
        conn.execute("INSERT INTO meta(key, value) VALUES('catalog_version', ?)",
                     (str(CATALOG_VERSION),))
        conn.execute("INSERT INTO meta(key, value) VALUES('model_variant', ?)",
                     (model_variant,))
        conn.commit()
        return n
    finally:
        conn.close()
