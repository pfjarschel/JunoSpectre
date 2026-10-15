"""Audio tracks' player: the sequencer engine's AudioSink.

Keeps the state of every file the song uses (cached and loaded into the
worker, converting, missing...) and of the stretch / transpose renders its
clips need, makes them one at a time in the background (each in its own
process), starts the worker on demand and turns clip launches into worker
commands. No Qt: on_change() / on_ended(track) are called from background
threads, so a GUI listener must hand them to its own thread.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from . import media
from .client import AudioClient
from .drift import DriftEstimator

logger = logging.getLogger(__name__)

# File / render states
READY, CONVERTING, RENDERING, MISSING, ERROR = "ready", "converting", "rendering", "missing", "error"
RATE = media.SAMPLE_RATE
STRETCH_RANGE = (0.5, 1.5)
PREVIEW_SLOT = "pv"


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
        self.song_bpm = 120.0                # MATCH SONG renders to this tempo
        self.files: Dict[str, dict] = {}     # rel path -> {state, key, frames, error}
        self.renders: Dict[str, dict] = {}   # render key -> {state, frames, error}
        self._clips: Dict[str, object] = {}  # clip_id -> Clip of the song (renders follow them)
        self._wanted: Dict[str, str] = {}    # clip_id -> render key it needs now
        self._last_ready: Dict[str, str] = {}  # clip_id -> last ready render (played while a new one renders)
        self._lock = threading.Lock()
        self._loaded: set = set()            # cache keys the worker has mapped
        self._voice: Dict[str, int] = {}     # slot -> id of its current voice
        self._slot_play: Dict[str, tuple] = {}  # slot -> (clip_id, key, begin, end) it plays
        self._next_vid = 1
        self._starting = False
        self.auditioning = ""                # clip_id playing in the preview slot
        self._audition_range = (0, 0)
        self._positions: Tuple[dict, float] = ({}, 0.0)
        self.drift = DriftEstimator(RATE)
        self._jobs: "queue.Queue[tuple]" = queue.Queue()
        threading.Thread(target=self._job_loop, daemon=True, name="AudioConvert").start()

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
                for st in list(self.files.values()) + list(self.renders.values()):
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
        return dict(self.files.get(rel) or {"state": MISSING if rel else "", "key": "", "frames": 0, "error": ""})

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
            else:
                key = media.cache_key(path)
                info = media.cache_info(key, self.cache)
                if info is not None:
                    self.files[rel] = {"state": READY, "key": key, "frames": int(info["frames"]), "error": ""}
                    self._load(key)
                else:
                    self.files[rel] = {"state": CONVERTING, "key": key, "frames": 0, "error": ""}
                    self._jobs.put(("convert", rel))
        self._changed()

    def forget_missing(self) -> None:
        """Let missing/failed files be looked up again (e.g. after copying them in)."""
        with self._lock:
            for rel in [r for r, st in self.files.items() if st["state"] in (MISSING, ERROR)]:
                del self.files[rel]

    # -- clips: tempo, renders -------------------------------------------------

    def set_clips(self, clips: List) -> None:
        """The audio clips of the song (renders are kept for these)."""
        self._clips = {c.clip_id: c for c in clips}
        for c in clips:
            self.prepare(c.audio.file)
        self.refresh_renders()

    def base_frames(self, clip) -> int:
        """Frames of the clip's slice in the source file (0 = not ready)."""
        a = clip.audio
        st = self.files.get(a.file) if a is not None else None
        if st is None or st["state"] != READY:
            return 0
        frames = st["frames"]
        begin = min(a.start, frames)
        end = min(a.end, frames) if a.end > 0 else frames
        return max(0, end - begin)

    def clip_bars(self, clip) -> int:
        """The slice's bars: set by the user, else its length rounded at the song tempo."""
        if clip.audio.bars > 0:
            return clip.audio.bars
        frames = self.base_frames(clip)
        return max(1, round(frames / RATE / (240.0 / max(1.0, self.song_bpm)))) if frames else 0

    def clip_bpm(self, clip) -> float:
        """The tempo the slice plays at unstretched (its bars over its length)."""
        frames, bars = self.base_frames(clip), self.clip_bars(clip)
        return bars * 240.0 / (frames / RATE) if frames and bars else 0.0

    def render_spec(self, clip) -> Optional[Tuple[float, float]]:
        """(tempo factor, semitones) the clip needs rendered, None = plays its source."""
        a = clip.audio
        tempo = 1.0
        if a.stretch:
            bpm = self.clip_bpm(clip)
            if bpm > 0:
                lo, hi = STRETCH_RANGE
                tempo = round(max(lo, min(hi, self.song_bpm / bpm)), 6)
        pitch = round(a.semitones + a.cents / 100.0, 4)
        if abs(tempo - 1.0) < 1e-5 and pitch == 0:
            return None
        return tempo, pitch

    def _render_key(self, clip, spec) -> Optional[str]:
        path = media.resolve(self.folder, clip.audio.file)
        if path is None:
            return None
        a = clip.audio
        return media.cache_key(path, f"{a.start}:{a.end}:{spec[0]:.6f}:{spec[1]:.4f}")

    def refresh_renders(self) -> None:
        """Queue the renders the clips need now (after an edit, a load or a tempo change)."""
        changed = False
        with self._lock:
            for cid, clip in self._clips.items():
                if clip.audio is None or not clip.audio.file:
                    self._wanted.pop(cid, None)
                    continue
                if (self.files.get(clip.audio.file) or {}).get("state") != READY:
                    continue                 # renders start once the source is converted
                spec = self.render_spec(clip)
                key = self._render_key(clip, spec) if spec is not None else None
                if key is None:
                    self._wanted.pop(cid, None)
                    continue
                self._wanted[cid] = key
                st = self.renders.get(key)
                if st is not None and st["state"] in (READY, RENDERING, ERROR):  # a failure isn't retried
                    if st["state"] == READY:
                        self._last_ready[cid] = key
                        self._load(key)
                    continue
                info = media.cache_info(key, self.cache)
                if info is not None:
                    self.renders[key] = {"state": READY, "key": key, "frames": int(info["frames"]), "error": ""}
                    self._last_ready[cid] = key
                    self._load(key)
                else:
                    base = self.files[clip.audio.file]
                    a = clip.audio
                    self.renders[key] = {"state": RENDERING, "key": key, "frames": 0, "error": ""}
                    self._jobs.put(("render", key, base["key"], a.start, a.end, spec[0], spec[1]))
                changed = True
        if changed:
            self._changed()
        self.retarget_all()

    def clip_state(self, clip) -> dict:
        """What the clip editor shows: {state, error} of what the clip plays."""
        st = self.file_state(clip.audio.file)
        if st["state"] != READY:
            return {"state": st["state"], "error": st["error"]}
        key = self._wanted.get(clip.clip_id) if self.render_spec(clip) is not None else None
        if key is None:
            return {"state": READY, "error": ""}
        r = self.renders.get(key) or {"state": RENDERING, "error": ""}
        return {"state": r["state"], "error": r["error"]}

    def _playable(self, clip) -> Optional[Tuple[str, int, int, int]]:
        """(cache key, begin, end, frames) the clip plays now, None = nothing yet."""
        a = clip.audio
        if a is None or not a.file:
            return None
        st = self.files.get(a.file)
        if st is None or st["state"] != READY:
            return None
        if self.render_spec(clip) is None:
            return st["key"], a.start, a.end, self.base_frames(clip)
        for key in (self._wanted.get(clip.clip_id), self._last_ready.get(clip.clip_id)):
            r = self.renders.get(key) if key else None
            if r is not None and r["state"] == READY:
                return key, 0, 0, r["frames"]
        return None

    def _job_loop(self) -> None:
        while True:
            job = self._jobs.get()
            if job[0] == "convert":
                self._run_convert(job[1])
            else:
                self._run_render(*job[1:])
            self.refresh_renders()           # a converted file may let renders start
            self._changed()

    def _finish(self, proc) -> Tuple[int, str]:
        err = proc.stderr.read().decode(errors="replace").strip() if proc.stderr else ""
        code = proc.wait()
        return code, (err.splitlines()[-1] if err else f"exit {code}")

    def _run_convert(self, rel: str) -> None:
        st = self.files.get(rel)
        path = media.resolve(self.folder, rel)
        if st is None or path is None:
            return
        code, err = self._finish(media.convert_in_subprocess(path, st["key"], self.cache))
        info = media.cache_info(st["key"], self.cache) if code == 0 else None
        with self._lock:
            if info is not None:
                self.files[rel] = {"state": READY, "key": st["key"], "frames": int(info["frames"]), "error": ""}
                self._load(st["key"])
            else:
                self.files[rel] = {"state": ERROR, "key": st["key"], "frames": 0, "error": err}
                logger.warning("audio: converting %s failed: %s", rel, err)

    def _run_render(self, key, base_key, begin, end, tempo, pitch) -> None:
        if key not in self._wanted.values():
            self.renders.pop(key, None)      # superseded by a newer edit
            return
        t = time.perf_counter()
        code, err = self._finish(media.render_in_subprocess(base_key, begin, end, tempo, pitch, key, self.cache))
        info = media.cache_info(key, self.cache) if code == 0 else None
        with self._lock:
            if info is not None:
                self.renders[key] = {"state": READY, "key": key, "frames": int(info["frames"]), "error": ""}
                for cid, k in self._wanted.items():
                    if k == key:
                        self._last_ready[cid] = key
                self._load(key)
                logger.info("audio: rendered x%.4f %+.2f st in %.1f s", tempo, pitch, time.perf_counter() - t)
            else:
                self.renders[key] = {"state": ERROR, "key": key, "frames": 0, "error": err}
                logger.warning("audio: render failed: %s", err)

    # -- AudioSink (engine lock held: never block) ----------------------------

    def clip_frames(self, clip) -> int:
        p = self._playable(clip)
        return p[3] if p else 0

    def start(self, track_idx: int, clip, at: Optional[float], loop: bool) -> None:
        p = self._playable(clip)
        if p is None:
            self.stop(track_idx, at)          # nothing to play yet: the slot goes quiet
            return
        if not self.ready:
            self.ensure_worker()
            return
        self._play(f"t{track_idx}", clip, p, self._shift(at), loop)

    def _play(self, slot: str, clip, p, at: Optional[float], loop: bool) -> None:
        key, begin, end, _frames = p
        self._load(key)
        vid = self._next_vid
        self._next_vid += 1
        self._voice[slot] = vid
        self._slot_play[slot] = (clip.clip_id, key, begin, end)
        self.client.play(slot, key, at=at, begin=begin, end=end, loop=loop,
                         gain=10 ** (clip.audio.gain_db / 20.0), vid=vid)

    def retarget(self, clip) -> None:
        """The clip's slice or render changed: what plays it now (or waits to)
        switches over at once, keeping its place since the slice start."""
        p = self._playable(clip)
        if p is None:
            return                            # a render is on its way: retargeted when ready
        for slot, (cid, key, begin, end) in list(self._slot_play.items()):
            if cid != clip.clip_id or slot not in self._voice or (key, begin, end) == p[:3]:
                continue
            self._load(p[0])
            self._slot_play[slot] = (cid,) + tuple(p[:3])
            self.client.retarget(slot, p[0], begin=p[1], end=p[2])

    def retarget_all(self) -> None:
        for cid in {v[0] for v in list(self._slot_play.values())}:
            clip = self._clips.get(cid)
            if clip is not None and clip.audio is not None:
                self.retarget(clip)

    def stop(self, track_idx: int, at: Optional[float]) -> None:
        self._voice.pop(f"t{track_idx}", None)
        self.client.stop(f"t{track_idx}", self._shift(at))

    def stop_all(self) -> None:
        self._voice.clear()
        self.auditioning = ""
        self.client.stop_all()

    def set_gain(self, track_idx: int, gain_db: float) -> None:
        self.client.set_gain(f"t{track_idx}", 10 ** (gain_db / 20.0))

    def _shift(self, at: Optional[float]) -> Optional[float]:
        return None if at is None else at + self.offset_s

    # -- audition (clip editor) ---------------------------------------------------

    def audition(self, clip, on: bool) -> bool:
        """Play the clip's slice at once on the preview slot (looped in LOOP mode)."""
        self.client.stop(PREVIEW_SLOT, None)
        self._voice.pop(PREVIEW_SLOT, None)
        self.auditioning = ""
        p = self._playable(clip) if on else None
        if p is None or not self.ready:
            if on:
                self.ensure_worker()
            return False
        self.auditioning = clip.clip_id
        self._audition_range = (p[1], p[1] + p[3])
        self._play(PREVIEW_SLOT, clip, p, None, clip.audio.mode == "loop")
        return True

    def position(self, slot: str) -> int:
        """Estimated frame of the slot's file now leaving the DAC (-1 = not playing)."""
        slots, dac = self._positions
        if slot not in slots or slot not in self._voice:
            return -1
        block = self.client.block
        return int(slots[slot] - block + (time.perf_counter() - dac) * RATE)

    # -- events --------------------------------------------------------------

    def _on_event(self, ev: dict) -> None:
        kind = ev.get("ev")
        if kind == "ended":
            slot = str(ev.get("slot", ""))
            if self._voice.get(slot) != ev.get("id"):
                return
            self._voice.pop(slot, None)
            if slot == PREVIEW_SLOT:
                self.auditioning = ""
                self._changed()
            elif slot.startswith("t") and slot[1:].isdigit() and self.on_ended is not None:
                self.on_ended(int(slot[1:]))
        elif kind == "clock":
            self._positions = (dict(ev.get("slots") or {}), float(ev.get("dac", 0.0)))
            self.drift.add(int(ev.get("frames", 0)), float(ev.get("dac", 0.0)), int(ev.get("xruns", 0)))
        elif kind in ("ready", "error", "exit"):
            self._changed()

    def _changed(self) -> None:
        if self.on_change is not None:
            try:
                self.on_change()
            except Exception:
                logger.exception("audio change listener failed")
