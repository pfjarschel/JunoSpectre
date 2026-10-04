"""Waveform catalog manager for Roland XPS-30 / JUNO-DS.

Provides fast cached lookup of waveform names, categories, icons,
single-cycle flags, and sampled 64-point vector curves for UI rendering.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets" / "waveforms"


class WaveCatalogManager:
    """Singleton managing in-memory access to INTA and INTB waveform catalogs."""

    _instance: Optional[WaveCatalogManager] = None

    def __init__(self, assets_dir: Optional[Path] = None):
        self.assets_dir = assets_dir or ASSETS_DIR
        self._catalogs: dict[str, dict[str, Any]] = {}
        self._load_catalogs()

    @classmethod
    def get_instance(cls) -> WaveCatalogManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_catalogs(self) -> None:
        for bank in ("INTA", "INTB"):
            cat_file = self.assets_dir / f"{bank.lower()}_catalog.json"
            if cat_file.exists():
                try:
                    with open(cat_file, "r", encoding="utf-8") as f:
                        self._catalogs[bank] = json.load(f)
                    logger.debug(f"Loaded {len(self._catalogs[bank])} waves from {cat_file.name}")
                except Exception as e:
                    logger.error(f"Failed to load {cat_file}: {e}")
                    self._catalogs[bank] = {}
            else:
                self._catalogs[bank] = {}

    def get_wave(self, bank: str = "INTA", wave_num: int = 1) -> dict[str, Any]:
        """Get wave metadata dictionary with safe fallbacks."""
        bank_upper = bank.upper()
        catalog = self._catalogs.get(bank_upper, {})
        key = str(wave_num)
        if key in catalog:
            return catalog[key]
        return {
            "id": wave_num,
            "bank": bank_upper,
            "name": f"Wave {wave_num:04d}",
            "category": "synth_wave",
            "icon": "wave",
            "is_single_cycle": False,
            "freq_hz": 0.0,
            "peak": 0.0,
            "samples_64": None,
        }

    # Classic bread-and-butter synth waveforms prioritized at top of ALL and SYNTH OSC views
    BASIC_SYNTH_WAVES: list[tuple[str, int]] = [
        ("INTA", 1322),  # 1. ARP Sine HD
        ("INTA", 625),   # 2. Sine
        ("INTA", 622),   # 3. JD Triangle
        ("INTA", 1321),  # 4. VS-Triangle
        ("INTA", 579),   # 5. Juno Saw HD
        ("INTA", 591),   # 6. JP-8 Saw
        ("INTA", 582),   # 7. MG Saw HD
        ("INTA", 585),   # 8. P5 Saw HD
        ("INTA", 600),   # 9. Juno Sqr HD
        ("INTA", 603),   # 10. JP-8 Square
        ("INTA", 1316),  # 11. MG Sqr HD
        ("INTA", 601),   # 12. P5 Sqr HD
        ("INTA", 612),   # 13. JP8 Pls 10HD
        ("INTA", 613),   # 14. JP8 Pls 15HD
        ("INTA", 614),   # 15. JP8 Pls 25HD
        ("INTA", 615),   # 16. JP8 Pls 30HD
        ("INTA", 616),   # 17. JP8 Pls 40HD
        ("INTA", 617),   # 18. JP8 Pls 45HD
        ("INTA", 1323),  # 19. JP-8 Pulse
        ("INTA", 1325),  # 20. JP8 Pls 30
    ]

    def get_filtered_waves(
        self,
        category: str = "ALL",
        bank: str = "ALL",
        search: str = "",
    ) -> list[dict[str, Any]]:
        """Filter waves across banks by category and optional search substring."""
        banks = ("INTA", "INTB") if bank.upper() == "ALL" else (bank.upper(),)
        cat_upper = category.upper()
        search_lower = search.strip().lower()

        results = []
        for b in banks:
            catalog = self._catalogs.get(b, {})
            for w in catalog.values():
                if cat_upper != "ALL" and w.get("category", "").upper() != cat_upper:
                    continue
                if search_lower:
                    w_name = w.get("name", "").lower()
                    w_id_str = str(w.get("id", ""))
                    if search_lower not in w_name and search_lower not in w_id_str:
                        continue
                results.append(w)

        # Prioritize bread-and-butter waveforms when ALL or SYNTH OSC category is active
        if cat_upper in ("ALL", "SYNTH_WAVE"):
            priority_map = {key: idx for idx, key in enumerate(self.BASIC_SYNTH_WAVES)}
            results.sort(key=lambda w: priority_map.get((w.get("bank", ""), w.get("id", 0)), 99999))

        return results
