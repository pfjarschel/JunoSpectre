"""Audio tracks' player: the sequencer engine's AudioSink.

Keeps the state of every file the song uses (cached and loaded into the
worker, converting, missing...), converts files one at a time in the
background, starts the worker on demand and turns clip launches into worker
commands. No Qt: on_change() / on_ended(track) are called from background
threads, so a GUI listener must hand them to its own thread.
"""

from __future__ import annotations

import logging
import queue
import threading
from pathlib import Path
from typing import Callable, Dict, Optional

from . import media
from .client import AudioClient

logger = logging.getLogger(__name__)

# File states
READY, CONVERTING, MISSING, ERROR = "ready", "converting", "missing", "error"


class AudioPlayer:
    def __init__(self, folder: Path, cache: Optional[Path] = None, client: Optional[AudioClient] = None,
                 on_change: Optional[Callable[[], None]] = None,
                 on_ended: Optional[Callable[[int], None]] = None):
        self.folder = Path(folder)
        self.cache = Path(cache) if cache else media.cache_dir()
        self.client = client or AudioClient()
        self.client.on_event = self._on_event
        self.on_change = on_change
        self.on_ended = on_ended
        self.offset_s = 0.0                  # audio offset: + plays audio later
        self.files: Dict[str, dict] = {}     # rel path -> {state, key, frames, error}
        self._lock = threading.Lock()
        self._loaded: set = set()            # cache keys the worker has mapped
        self._voice: Dict[int, int] = {}     # track -> id of its current voice
        self._next_vid = 1
        self._starting = False
        self._jobs: "queue.Queue[str]" = queue.Queue()
        threading.Thread(target=self._convert_loop, daemon=True, name="AudioConvert").start()

    # -- worker --------------------------------------------------------------

    @property
    def ready(self) -> bool:
        return self.client.ready and self.client.running

    def ensure_worker(self) -> None:
        """Start the worker in the background if it isn't running."""
        with self._lock:
            if self._starting or self.ready:
                return
            self._starting = True
        threading.Thread(target=self._start_worker, daemon=True, name="AudioWorkerStart").start()

    def _start_worker(self) -> None:
        try:
            ok = self.client.start()
            with self._lock:
                self._loaded.clear()
            if ok:
                for rel, st in list(self.files.items()):
                    if st["state"] == READY:
                        self._load(st["key"])
        finally:
            self._starting = False
            self._changed()

    def close(self) -> None:
        """Stop the worker and stop calling listeners (their owner may be going away)."""
        self.on_change = self.on_ended = None
        self.client.close()

    def _load(self, key: str) -> None:
        if key not in self._loaded and self.client.load(key, media.cache_paths(key, self.cache)["audio"]):
            self._loaded.add(key)

    # -- files ---------------------------------------------------------------

    def file_state(self, rel: str) -> dict:
        return dict(self.files.get(rel) or {"state": MISSING if rel else "", "frames": 0, "error": ""})

    def prepare(self, rel: str) -> None:
        """Make a file playable: load its cache entry, or convert it first."""
        if not rel:
            return
        with self._lock:
            st = self.files.get(rel)
            if st is not None and st["state"] in (READY, CONVERTING):
                if st["state"] == READY:
                    self._load(st["key"])
                return
            path = media.resolve(self.folder, rel)
            if path is None:
                self.files[rel] = {"state": MISSING, "key": "", "frames": 0, "error": ""}
                changed = True
            else:
                key = media.cache_key(path)
                info = media.cache_info(key, self.cache)
                if info is not None:
                    self.files[rel] = {"state": READY, "key": key, "frames": int(info["frames"]), "error": ""}
                    self._load(key)
                else:
                    self.files[rel] = {"state": CONVERTING, "key": key, "frames": 0, "error": ""}
                    self._jobs.put(rel)
                changed = True
        if changed:
            self._changed()

    def forget_missing(self) -> None:
        """Let missing/failed files be looked up again (e.g. after copying them in)."""
        with self._lock:
            for rel in [r for r, st in self.files.items() if st["state"] in (MISSING, ERROR)]:
                del self.files[rel]

    def _convert_loop(self) -> None:
        while True:
            rel = self._jobs.get()
            st = self.files.get(rel)
            path = media.resolve(self.folder, rel)
            if st is None or path is None:
                continue
            proc = media.convert_in_subprocess(path, st["key"], self.cache)
            err = proc.stderr.read().decode(errors="replace").strip() if proc.stderr else ""
            code = proc.wait()
            info = media.cache_info(st["key"], self.cache) if code == 0 else None
            with self._lock:
                if info is not None:
                    self.files[rel] = {"state": READY, "key": st["key"], "frames": int(info["frames"]), "error": ""}
                    self._load(st["key"])
                else:
                    self.files[rel] = {"state": ERROR, "key": st["key"], "frames": 0,
                                       "error": err.splitlines()[-1] if err else f"exit {code}"}
                    logger.warning("audio: converting %s failed: %s", rel, self.files[rel]["error"])
            self._changed()

    # -- AudioSink (engine lock held: never block) ----------------------------

    def clip_frames(self, clip) -> int:
        a = clip.audio
        st = self.files.get(a.file) if a is not None else None
        if st is None or st["state"] != READY:
            return 0
        frames = st["frames"]
        begin = min(a.start, frames)
        end = min(a.end, frames) if a.end > 0 else frames
        return max(0, end - begin)

    def start(self, track_idx: int, clip, at: Optional[float], loop: bool) -> None:
        a = clip.audio
        st = self.files.get(a.file)
        if st is None or st["state"] != READY:
            self.stop(track_idx, at)          # nothing to play yet: the slot goes quiet
            return
        if not self.ready:
            self.ensure_worker()
            return
        self._load(st["key"])
        vid = self._next_vid
        self._next_vid += 1
        self._voice[track_idx] = vid
        self.client.play(f"t{track_idx}", st["key"], at=self._shift(at), begin=a.start, end=a.end, loop=loop,
                         gain=10 ** (a.gain_db / 20.0), vid=vid)

    def stop(self, track_idx: int, at: Optional[float]) -> None:
        self._voice.pop(track_idx, None)
        self.client.stop(f"t{track_idx}", self._shift(at))

    def stop_all(self) -> None:
        self._voice.clear()
        self.client.stop_all()

    def set_gain(self, track_idx: int, gain_db: float) -> None:
        self.client.set_gain(f"t{track_idx}", 10 ** (gain_db / 20.0))

    def _shift(self, at: Optional[float]) -> Optional[float]:
        return None if at is None else at + self.offset_s

    # -- events --------------------------------------------------------------

    def _on_event(self, ev: dict) -> None:
        kind = ev.get("ev")
        if kind == "ended":
            slot = str(ev.get("slot", ""))
            if slot.startswith("t") and slot[1:].isdigit():
                t = int(slot[1:])
                if self._voice.get(t) == ev.get("id"):
                    self._voice.pop(t, None)
                    if self.on_ended is not None:
                        self.on_ended(t)
        elif kind in ("ready", "error", "exit"):
            self._changed()

    def _changed(self) -> None:
        if self.on_change is not None:
            try:
                self.on_change()
            except Exception:
                logger.exception("audio change listener failed")
