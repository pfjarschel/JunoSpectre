"""Audio files: the media folder, USB import and the playback cache.

Clips name their file by its path inside the media folder (~/SpectreAudio by
default), so songs move between machines. Every file is converted once into
a cache entry the audio worker can memory-map: 44.1 kHz stereo float32 (.npy)
plus a small peaks file for waveform drawing. Conversion is CPU heavy, so it
runs in its own process (`python media.py convert SRC DST`), never in the app.

Only numpy/scipy/soundfile at module level: this file also runs as a script.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path
from typing import List, Optional

import numpy as np

SAMPLE_RATE = 44100          # the JUNO-DS USB audio rate (the only one it takes)
CHANNELS = 2
PEAK_COLUMNS = 2048          # waveform overview resolution (min/max pairs)
AUDIO_EXTENSIONS = (".wav", ".flac", ".ogg", ".mp3", ".aif", ".aiff")
DEFAULT_AUDIO_DIR = Path.home() / "SpectreAudio"
# Where USB sticks get mounted (desktop automount, then manual mounts)
USB_MOUNT_ROOTS = (Path("/media") / os.environ.get("USER", ""), Path("/run/media") / os.environ.get("USER", ""),
                   Path("/media"), Path("/mnt"))


def audio_dir(settings: Optional[dict] = None) -> Path:
    """The media folder ("audio_dir" in hardware.json, else ~/SpectreAudio)."""
    custom = str((settings or {}).get("audio_dir") or "").strip()
    return Path(custom).expanduser() if custom else DEFAULT_AUDIO_DIR


def cache_dir() -> Path:
    from ..librarian.repository import data_root

    return data_root() / "audio_cache"


def is_audio_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS and not path.name.startswith(".")


def list_audio(folder: Path, sub: str = "") -> dict:
    """One folder level for the file browser: {"dirs": [...], "files": [...]}, names sorted."""
    base = (folder / sub) if sub else folder
    dirs: List[str] = []
    files: List[str] = []
    try:
        for p in sorted(base.iterdir(), key=lambda q: q.name.lower()):
            if p.name.startswith("."):
                continue
            if p.is_dir():
                dirs.append(p.name)
            elif is_audio_file(p):
                files.append(p.name)
    except OSError:
        pass
    return {"dirs": dirs, "files": files}


def relative_name(folder: Path, path: Path) -> str:
    """A file's name as clips store it: its posix path inside the media folder."""
    return path.resolve().relative_to(folder.resolve()).as_posix()


def resolve(folder: Path, rel: str) -> Optional[Path]:
    """The file a clip names, or None when it is missing (or points outside the folder)."""
    if not rel:
        return None
    path = (folder / rel).resolve()
    try:
        path.relative_to(folder.resolve())
    except ValueError:
        return None
    return path if path.is_file() else None


def usb_volumes() -> List[Path]:
    """Mounted removable volumes to import from."""
    found: List[Path] = []
    for root in USB_MOUNT_ROOTS:
        try:
            if not root.is_dir():
                continue
            for p in sorted(root.iterdir()):
                if p.is_dir() and os.path.ismount(p) and p not in found:
                    found.append(p)
        except OSError:
            continue
    return found


def import_file(src: Path, folder: Path, sub: str = "") -> Path:
    """Copy src into the media folder (sub folder optional); a name clash gets ' (2)'."""
    dest_dir = (folder / sub) if sub else folder
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    n = 2
    while dest.exists():
        dest = dest_dir / f"{src.stem} ({n}){src.suffix}"
        n += 1
    shutil.copy2(src, dest)
    return dest


# -- cache ---------------------------------------------------------------------

def cache_key(path: Path, render: str = "") -> str:
    """Cache entry name: changes when the file changes, or for another render
    (e.g. a stretch/transpose setting)."""
    st = path.stat()
    raw = f"{path.resolve()}|{st.st_size}|{st.st_mtime_ns}|{render}"
    return hashlib.sha1(raw.encode()).hexdigest()[:20]


def cache_paths(key: str, folder: Optional[Path] = None) -> dict:
    base = folder or cache_dir()
    return {"audio": base / f"{key}.npy", "peaks": base / f"{key}.peaks.npy", "info": base / f"{key}.json"}


def cache_info(key: str, folder: Optional[Path] = None) -> Optional[dict]:
    """The entry's info ({frames, seconds, source_rate, source_channels}), None if not cached."""
    paths = cache_paths(key, folder)
    if not (paths["audio"].is_file() and paths["info"].is_file()):
        return None
    try:
        return dict(json.loads(paths["info"].read_text()))
    except (OSError, ValueError):
        return None


def to_stereo_44k(data: np.ndarray, rate: int) -> np.ndarray:
    """(frames, channels) float -> (frames, 2) float32 at SAMPLE_RATE."""
    if data.ndim == 1:
        data = data[:, None]
    if data.shape[1] == 1:
        data = np.repeat(data, 2, axis=1)
    elif data.shape[1] > 2:
        data = data[:, :2]
    if rate != SAMPLE_RATE and len(data):
        from scipy.signal import resample_poly

        ratio = Fraction(SAMPLE_RATE, int(rate)).limit_denominator(1000)
        data = resample_poly(data, ratio.numerator, ratio.denominator, axis=0)
    return np.ascontiguousarray(data, dtype=np.float32)


def peaks(data: np.ndarray, columns: int = PEAK_COLUMNS) -> np.ndarray:
    """(columns, 2) min/max of both channels mixed, for drawing the waveform."""
    if not len(data):
        return np.zeros((columns, 2), dtype=np.float32)
    mono = data.mean(axis=1)
    # Column starts; files shorter than `columns` frames repeat frames
    starts = np.minimum(np.linspace(0, len(mono), columns, endpoint=False).astype(np.int64), len(mono) - 1)
    return np.stack([np.minimum.reduceat(mono, starts), np.maximum.reduceat(mono, starts)], axis=1).astype(np.float32)


def convert(src: Path, key: str, folder: Optional[Path] = None) -> dict:
    """Decode src into cache entry `key`; returns its info. Writes atomically."""
    import soundfile as sf

    paths = cache_paths(key, folder)
    paths["audio"].parent.mkdir(parents=True, exist_ok=True)
    raw, rate = sf.read(str(src), dtype="float32", always_2d=True)
    data = to_stereo_44k(raw, rate)
    info = {"frames": int(len(data)), "seconds": len(data) / SAMPLE_RATE,
            "source_rate": int(rate), "source_channels": int(raw.shape[1]), "source": str(src)}
    for name, arr in (("audio", data), ("peaks", peaks(data))):
        tmp = paths[name].with_suffix(".tmp.npy")
        np.save(tmp, arr)
        tmp.replace(paths[name])
    tmp = paths["info"].with_suffix(".tmp")
    tmp.write_text(json.dumps(info))
    tmp.replace(paths["info"])
    return info


def convert_in_subprocess(src: Path, key: str, folder: Optional[Path] = None) -> subprocess.Popen:
    """Start a conversion in its own process (keeps the app's threads free)."""
    folder = folder or cache_dir()
    return subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "convert", str(src), key, str(folder)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[1] == "convert":
        try:
            convert(Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4]))
        except Exception as e:  # reported to the app through stderr + exit code
            print(f"{type(e).__name__}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print("usage: media.py convert SRC KEY CACHE_DIR", file=sys.stderr)
        sys.exit(2)
