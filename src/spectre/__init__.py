"""Juno Spectre - Open-Source Next-Gen Brain & Tactile Extension for Roland Juno-DS / XPS Synthesizers."""

from pathlib import Path

from . import control, core


def _get_version() -> str:
    version_file = Path(__file__).resolve().parent.parent.parent / "VERSION"
    if version_file.is_file():
        try:
            return version_file.read_text(encoding="utf-8").strip()
        except OSError:
            pass
    return "0.7.0"


__version__ = _get_version()
__all__ = ["core", "control", "__version__"]
