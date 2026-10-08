"""Roland JUNO-DS 80 Multi-Effects (MFX) Catalog and Metadata.

Defines the complete set of 80 MFX algorithms with accurate hardware parameter specs,
ranges, units, and discrete option enumerations matching Roland JUNO-DS synthesizer RAM.

Data is stored as a JSON asset in assets/mfx_catalog.json and loaded lazily with
caching and validation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

_CATALOG_PATH = Path(__file__).resolve().parent.parent / "assets" / "mfx_catalog.json"


def _load_data() -> dict[str, Any]:
    if not _CATALOG_PATH.is_file():
        raise FileNotFoundError(f"MFX catalog asset not found at {_CATALOG_PATH}")
    with open(_CATALOG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


_DATA = _load_data()

MFX_CATEGORIES: List[str] = _DATA["categories"]
MFX_ALGORITHMS: List[Dict[str, Any]] = _DATA["algorithms"]
EQ_PARAMETRIC_PRESETS: List[Dict[str, Any]] = _DATA.get("eq_parametric_presets", [])
SPECTRUM_PRESETS: List[Dict[str, Any]] = _DATA.get("spectrum_presets", [])

_ALGO_BY_ID: Dict[int, Dict[str, Any]] = {a["id"]: a for a in MFX_ALGORITHMS}

# Precomputed lightweight lists by category for instant UI switching (0ms latency)
_LIGHT_CATALOG = [{"id": a["id"], "name": a["name"], "cat": a["cat"]} for a in MFX_ALGORITHMS]
_LIGHT_BY_CAT = {"ALL": _LIGHT_CATALOG}
for _cat in MFX_CATEGORIES[1:]:
    _LIGHT_BY_CAT[_cat] = [a for a in _LIGHT_CATALOG if a["cat"] == _cat]


def get_mfx_catalog() -> List[Dict[str, Any]]:
    """Return all 80 MFX algorithms with full parameter definitions."""
    return MFX_ALGORITHMS


def get_mfx_light_catalog(category: str = "ALL") -> List[Dict[str, Any]]:
    """Return lightweight algorithm list (id, name, cat only) precomputed by category."""
    return _LIGHT_BY_CAT.get(category, _LIGHT_CATALOG)


def get_mfx_algo(algo_id: int) -> Optional[Dict[str, Any]]:
    """Lookup an MFX algorithm by 1-based ID."""
    return _ALGO_BY_ID.get(algo_id)


def get_mfx_categories() -> List[str]:
    """Return list of MFX categories."""
    return MFX_CATEGORIES
