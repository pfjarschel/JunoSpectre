"""Patch Librarian: file-backed user patches + SQLite index/cache."""

from .factory import (
    build_factory_db,
    ensure_shipped_factory,
    factory_key,
    factory_variants,
    shipped_factory_db,
)
from .repository import (
    PatchRepository,
    default_db_path,
    default_user_dir,
)

__all__ = [
    "PatchRepository",
    "default_user_dir",
    "default_db_path",
    "build_factory_db",
    "ensure_shipped_factory",
    "factory_key",
    "factory_variants",
    "shipped_factory_db",
]
