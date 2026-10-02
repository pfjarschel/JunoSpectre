"""Hardware Profile Manager for discovering, loading, and matching controller profiles."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union

from .models import HardwareProfile

logger = logging.getLogger(__name__)

# Default directory for bundled hardware profiles
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_PROFILE_DIR = _PROJECT_ROOT / "config" / "hardware_profiles"


class ProfileManager:
    """Manages loading, saving, and auto-detecting hardware profiles."""

    def __init__(self, profile_dir: Optional[Union[str, Path]] = None):
        self.profile_dir = Path(profile_dir) if profile_dir else DEFAULT_PROFILE_DIR
        self._cache: Dict[str, HardwareProfile] = {}

    def ensure_profile_dir(self) -> Path:
        """Ensure profile directory exists."""
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        return self.profile_dir

    def list_profiles(self) -> List[HardwareProfile]:
        """List all valid profiles found in the profile directory."""
        if not self.profile_dir.exists():
            return []

        profiles: List[HardwareProfile] = []
        for path in sorted(self.profile_dir.glob("*.json")):
            try:
                prof = self.load_profile(path)
                profiles.append(prof)
            except Exception as e:
                logger.warning(f"Could not load hardware profile from '{path}': {e}")

        return profiles

    def load_profile(self, target: Union[str, Path]) -> HardwareProfile:
        """Load a profile by file path, file name, or profile name."""
        path = Path(target)
        if not path.is_file():
            # Try appending .json in profile_dir
            candidate = self.profile_dir / f"{target}.json"
            if candidate.is_file():
                path = candidate
            else:
                candidate2 = self.profile_dir / target
                if candidate2.is_file():
                    path = candidate2

        if path.is_file():
            cache_key = str(path.resolve())
            if cache_key in self._cache:
                return self._cache[cache_key]

            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            profile = HardwareProfile.model_validate(data)
            self._cache[cache_key] = profile
            return profile

        # Search by profile_name inside loaded profiles
        for prof in self.list_profiles():
            if prof.profile_name.lower() == str(target).lower():
                return prof

        raise FileNotFoundError(f"Hardware profile '{target}' not found in {self.profile_dir}")

    def save_profile(self, profile: HardwareProfile, filename_or_path: Optional[Union[str, Path]] = None) -> Path:
        """Serialize and save a hardware profile to disk."""
        self.ensure_profile_dir()
        if filename_or_path is None:
            slug = profile.profile_name.lower().replace(" ", "_").replace("/", "_")
            path = self.profile_dir / f"{slug}.json"
        else:
            path = Path(filename_or_path)
            if not path.suffix:
                path = path.with_suffix(".json")
            if not path.is_absolute():
                path = self.profile_dir / path

        with open(path, "w", encoding="utf-8") as f:
            json.dump(profile.model_dump(exclude_none=True), f, indent=2)

        cache_key = str(path.resolve())
        self._cache[cache_key] = profile
        logger.info(f"Saved hardware profile '{profile.profile_name}' to {path}")
        return path

    def match_profile_for_device(self, port_name: str) -> Optional[HardwareProfile]:
        """Auto-detect hardware profile matching a connected MIDI port name.
        
        Prioritizes the longest, most specific keyword match.
        """
        if not port_name:
            return None

        clean_name = port_name.lower()
        profiles = self.list_profiles()

        # Collect all matches with their keyword length
        matches: List[tuple[int, HardwareProfile, str]] = []
        for prof in profiles:
            for kw in prof.device_match_keywords:
                if kw.lower() in clean_name:
                    matches.append((len(kw), prof, kw))

        if matches:
            # Sort by keyword length descending: longest match takes precedence
            matches.sort(key=lambda x: x[0], reverse=True)
            _, best_prof, best_kw = matches[0]
            logger.info(f"Matched port '{port_name}' to profile '{best_prof.profile_name}' (keyword '{best_kw}')")
            return best_prof

        return None

