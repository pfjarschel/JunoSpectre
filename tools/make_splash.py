#!/usr/bin/env python3
"""Build the app startup splash from the master picture.

Scales the master to cover 1024x600, centre-crops it and writes
src/spectre/assets/splash_1024x600.jpg (shown by main.qml while the UI loads).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MASTER = PROJECT_ROOT / "docs" / "images" / "JunoSpectre_splash.jpg"
APP_OUT = PROJECT_ROOT / "src" / "spectre" / "assets" / "splash_1024x600.jpg"
SIZE = (1024, 600)


def cover(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Scale to cover ``size`` and crop the centre."""
    w, h = size
    s = max(w / img.width, h / img.height)
    scaled = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    x = (scaled.width - w) // 2
    y = (scaled.height - h) // 2
    return scaled.crop((x, y, x + w, y + h))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("master", nargs="?", type=Path, default=MASTER)
    args = ap.parse_args()

    img = cover(Image.open(args.master).convert("RGB"), SIZE)
    img.save(APP_OUT, quality=90, optimize=True)
    print(f"app splash -> {APP_OUT.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
