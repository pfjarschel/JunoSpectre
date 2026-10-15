"""Audio worker: its own process owns the sound device and mixes the clips.

Keeping audio out of the app process means a slow Qt frame or Python GC
pause there can never click or drop out. The app talks to it over pipes:
JSON commands in on stdin, JSON events out on stdout, one per line.

Times are time.perf_counter() seconds (CLOCK_MONOTONIC on Linux, shared by
every process), so the app schedules "start this clip on the next bar" ahead
and the mixer places it on the exact sample at which that moment leaves the DAC.

Commands:
  {"cmd": "load", "key": k, "path": "/cache/k.npy"}       memory-map a cache entry
  {"cmd": "unload", "key": k}
  {"cmd": "play", "slot": s, "key": k, "at": t|null, "begin": f, "end": f,
   "loop": bool, "gain": g, "offset": f, "id": n}          a new voice (replaces the slot's at t;
                                                           cancels its voices still waiting)
  {"cmd": "retarget", "slot": s, "key": k, "begin": f, "end": f}
                                                           the slot's voices play another slice /
                                                           source, as far past its start as before
  {"cmd": "stop", "slot": s, "at": t|null}                 fade the slot's voice out at t
  {"cmd": "stop_all"}
  {"cmd": "gain", "slot": s, "gain": g}                    ramped over one block
  {"cmd": "master", "gain": g}
  {"cmd": "quit"}
Events:
  {"ev": "ready", "device": name, "rate": 44100, "latency": s, "block": n}
  {"ev": "error", "msg": text}
  {"ev": "started" | "ended", "slot": s, "id": n}
  {"ev": "clock", "frames": n, "dac": t, "xruns": n, "slots": {slot: frame}}  (4 per second)

Only stdlib + numpy (+ sounddevice for a real device): this file runs as a script.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
import threading
import time
from typing import Dict, List, Optional

import numpy as np

SAMPLE_RATE = 44100
FADE_IN = 44            # 1 ms: hides the click of a slice starting mid-wave
FADE_OUT = 220          # 5 ms: stop / replace without a click
CLOCK_EVERY_S = 0.25


class Voice:
    """One clip playing (or waiting to start) in a slot."""

    def __init__(self, slot: str, source: np.ndarray, at: Optional[float], begin: int, end: int,
                 loop: bool, gain: float, offset: int = 0, vid: int = 0):
        frames = len(source)
        self.slot = slot
        self.vid = vid
        self.source = source
        self.at = at                          # None = as soon as possible
        self.begin = max(0, min(frames, int(begin)))
        self.end = max(self.begin, min(frames, int(end) if end > 0 else frames))
        self.loop = bool(loop) and self.end > self.begin
        self.gain = float(gain)
        self.target_gain = float(gain)
        self.pos = self.begin + max(0, int(offset))
        self.started = False
        self.start_off = 0                    # frame of the current block it starts on
        self.stop_at: Optional[float] = None
        self.faded_in = 0                     # frames of the fade-in done
        self.release = -1                     # fade-out frames left (-1 = not stopping)
        self.release_from = 0                 # frame of the current block the fade-out starts on
        self.done = False

    def wrap(self) -> None:
        if self.loop and self.pos >= self.end:
            self.pos = self.begin + (self.pos - self.begin) % (self.end - self.begin)

    def set_region(self, source: np.ndarray, begin: int, end: int) -> None:
        """Play another slice / source, keeping how far past its start the voice is."""
        frames = len(source)
        rel = self.pos - self.begin
        self.source = source
        self.begin = max(0, min(frames, int(begin)))
        self.end = max(self.begin, min(frames, int(end) if end > 0 else frames))
        self.loop = self.loop and self.end > self.begin
        self.pos = self.begin + rel
        self.wrap()


class Mixer:
    """Sample-accurate voice scheduling and mixing (no I/O; the device calls render)."""

    def __init__(self, rate: int = SAMPLE_RATE):
        self.rate = rate
        self.sources: Dict[str, np.ndarray] = {}
        self.voices: List[Voice] = []
        self.commands: collections.deque = collections.deque()
        self.events: collections.deque = collections.deque()
        self.master = 1.0
        self.frames_out = 0                   # frames rendered so far
        self.last_block = (0, 0.0)            # (frames_out, dac time) of the last block start

    # -- commands (any thread: queued, applied at the next block) ---------------

    def load(self, key: str, path: str) -> None:
        self.sources[key] = np.load(path, mmap_mode="r")

    def unload(self, key: str) -> None:
        self.sources.pop(key, None)

    def submit(self, cmd: dict) -> None:
        self.commands.append(cmd)

    def _apply(self, cmd: dict) -> None:
        kind = cmd.get("cmd")
        if kind == "play":
            src = self.sources.get(str(cmd.get("key")))
            if src is None:
                self.events.append({"ev": "error", "msg": f"not loaded: {cmd.get('key')}"})
                return
            slot = str(cmd.get("slot"))
            for v in self.voices:
                if v.slot == slot and not v.started:
                    v.done = True             # a newer launch wins
            self.voices.append(Voice(slot, src, cmd.get("at"), int(cmd.get("begin", 0)),
                                     int(cmd.get("end", 0)), bool(cmd.get("loop")), float(cmd.get("gain", 1.0)),
                                     int(cmd.get("offset", 0)), int(cmd.get("id", 0))))
        elif kind == "retarget":
            src = self.sources.get(str(cmd.get("key")))
            if src is None:
                self.events.append({"ev": "error", "msg": f"not loaded: {cmd.get('key')}"})
                return
            self._retarget(str(cmd.get("slot")), src, int(cmd.get("begin", 0)), int(cmd.get("end", 0)))
        elif kind == "stop":
            slot, at = str(cmd.get("slot")), cmd.get("at")
            for v in self.voices:
                if v.slot != slot:
                    continue
                if not v.started and (at is None or v.at is None or v.at >= at):
                    v.done = True             # never started: just drop it
                elif v.stop_at is None or (at is not None and at < v.stop_at):
                    v.stop_at = at if at is not None else 0.0
        elif kind == "stop_all":
            for v in self.voices:
                if v.started:
                    v.stop_at = 0.0
                else:
                    v.done = True
        elif kind == "gain":
            for v in self.voices:
                if v.slot == str(cmd.get("slot")):
                    v.target_gain = float(cmd.get("gain", 1.0))
        elif kind == "master":
            self.master = max(0.0, float(cmd.get("gain", 1.0)))

    def _retarget(self, slot: str, src: np.ndarray, begin: int, end: int) -> None:
        """Slice edits while the slot plays: a waiting voice just takes the new
        slice; a sounding one continues on it in place when only its end moved,
        else crossfades to a copy at the same distance past the new start."""
        for v in list(self.voices):
            if v.slot != slot or v.done:
                continue
            if not v.started:
                v.set_region(src, begin, end)
                continue
            if v.stop_at is not None or v.release >= 0:
                continue                      # already on its way out
            new = Voice(slot, src, None, 0, 0, v.loop, v.gain, 0, v.vid)
            new.pos = v.pos
            new.begin = v.begin
            new.set_region(src, begin, end)
            if src is v.source and new.begin == v.begin and new.pos == v.pos:
                v.end, v.loop = new.end, new.loop     # same audio here: no jump
                continue
            v.stop_at = 0.0
            if not new.loop and new.pos >= new.end:
                continue                      # already past the new end: it just ends
            new.target_gain = v.target_gain
            new.started = True
            v.vid = -1                        # its fade-out isn't the slot's end
            self.voices.append(new)

    # -- rendering (device thread) ----------------------------------------------

    def _frame_of(self, t: Optional[float], t0: float) -> int:
        return 0 if t is None or t <= 0 else int(round((t - t0) * self.rate))

    def render(self, n: int, t0: float) -> np.ndarray:
        """The next n frames; frame 0 leaves the DAC at perf time t0."""
        while self.commands:
            self._apply(self.commands.popleft())
        out = np.zeros((n, 2), dtype=np.float32)

        # Pass 1: voices starting in this block, and the voices they replace
        for v in self.voices:
            if v.started or v.done:
                continue
            off = self._frame_of(v.at, t0)
            if off >= n:
                continue
            if off < 0:                       # late: skip ahead so it stays in time
                v.pos -= off
                v.wrap()
                off = 0
            v.started = True
            v.start_off = off
            self.events.append({"ev": "started", "slot": v.slot, "id": v.vid})
            for old in self.voices:
                if old is not v and old.slot == v.slot and old.started and not old.done:
                    stop = t0 + off / self.rate
                    if old.stop_at is None or old.stop_at > stop:
                        old.stop_at = stop

        # Pass 2: mix
        for v in self.voices:
            if v.started and not v.done:
                self._mix(v, out, n, t0)
                if v.done and v.vid >= 0:        # -1: replaced by a retarget
                    self.events.append({"ev": "ended", "slot": v.slot, "id": v.vid})
        self.voices = [v for v in self.voices if not v.done]
        if self.master != 1.0:
            out *= self.master
        np.clip(out, -1.0, 1.0, out=out)
        self.last_block = (self.frames_out, t0)
        self.frames_out += n
        return out

    def _mix(self, v: Voice, out: np.ndarray, n: int, t0: float) -> None:
        off, v.start_off = v.start_off, 0
        need = n - off
        buf = np.zeros((need, 2), dtype=np.float32)
        k = 0
        while k < need and v.pos < v.end:
            chunk = min(need - k, v.end - v.pos)
            buf[k:k + chunk] = v.source[v.pos:v.pos + chunk]
            v.pos += chunk
            k += chunk
            if v.pos >= v.end and v.loop:
                v.pos = v.begin
        filled = k

        env = np.full(need, v.gain, dtype=np.float32)
        if v.target_gain != v.gain:
            env = np.linspace(v.gain, v.target_gain, need, dtype=np.float32)
            v.gain = v.target_gain
        if v.faded_in < FADE_IN:
            m = min(need, FADE_IN - v.faded_in)
            env[:m] *= (np.arange(v.faded_in, v.faded_in + m, dtype=np.float32) + 1) / FADE_IN
            v.faded_in += m
        if not v.loop and v.pos >= v.end and v.end < len(v.source):
            # A one-shot slice ending before the file does: fade its tail
            tail = min(filled, FADE_OUT)
            env[filled - tail:filled] *= np.linspace(1.0, 0.0, tail, dtype=np.float32)
        # Stop: fade out from the stop frame
        if v.release < 0 and v.stop_at is not None:
            s = max(0, self._frame_of(v.stop_at, t0 + off / self.rate))
            if s < need:
                v.release = FADE_OUT
                v.release_from = s
        if v.release >= 0:
            s, v.release_from = v.release_from, 0
            m = min(need - s, v.release)
            ramp = np.arange(v.release, v.release - m, -1, dtype=np.float32) / FADE_OUT
            env[s:s + m] *= ramp
            env[s + m:] = 0.0
            v.release -= m
            if v.release <= 0:
                v.done = True
        if filled < need or (not v.loop and v.pos >= v.end):
            env[filled:] = 0.0
            if not v.loop and v.pos >= v.end:
                v.done = True
        out[off:] += buf * env[:, None]

    def positions(self) -> Dict[str, int]:
        return {v.slot: int(v.pos) for v in self.voices if v.started}


# -- process -------------------------------------------------------------------

def _emit(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def _pick_device(sd, name: str):
    """Output device by name substring; '' = the JUNO if present, else the default."""
    wanted = [name] if name else ["JUNO"]
    for want in wanted:
        for i, d in enumerate(sd.query_devices()):
            if d["max_output_channels"] >= 2 and want.lower() in d["name"].lower():
                return i, d["name"]
    if name:
        raise RuntimeError(f"audio device not found: {name}")
    d = sd.query_devices(kind="output")
    return None, d["name"]


def _read_commands(mixer: Mixer, stop: threading.Event) -> None:
    for line in sys.stdin:
        try:
            cmd = json.loads(line)
        except ValueError:
            continue
        kind = cmd.get("cmd")
        try:
            if kind == "quit":
                break
            if kind == "load":
                mixer.load(str(cmd["key"]), str(cmd["path"]))
            elif kind == "unload":
                mixer.unload(str(cmd["key"]))
            else:
                mixer.submit(cmd)
        except Exception as e:
            mixer.events.append({"ev": "error", "msg": f"{kind}: {e}"})
    stop.set()                                # stdin closed: the app is gone


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="JunoSpectre audio worker")
    ap.add_argument("--device", default="", help="output device name part ('' = JUNO, else default)")
    ap.add_argument("--block", type=int, default=512, help="frames per block")
    ap.add_argument("--latency", type=float, default=0.03, help="device latency (s)")
    ap.add_argument("--null", action="store_true", help="no device: render on a timer (tests)")
    args = ap.parse_args(argv)

    mixer = Mixer()
    stop = threading.Event()
    xruns = [0]
    stream = None
    try:
        if args.null:
            def null_loop():
                period = args.block / SAMPLE_RATE
                nxt = time.perf_counter()
                while not stop.is_set():
                    mixer.render(args.block, nxt + args.latency)
                    nxt += period
                    time.sleep(max(0.0, nxt - time.perf_counter()))
            threading.Thread(target=null_loop, daemon=True).start()
            _emit({"ev": "ready", "device": "null", "rate": SAMPLE_RATE, "latency": args.latency,
                   "block": args.block})
        else:
            import sounddevice as sd

            dev, dev_name = _pick_device(sd, args.device)

            def callback(outdata, frames, tinfo, status):
                if status.output_underflow:
                    xruns[0] += 1
                now = time.perf_counter()
                dac = tinfo.outputBufferDacTime
                t0 = (dac - tinfo.currentTime) + now if dac > 0 else now + args.latency
                outdata[:] = mixer.render(frames, t0)

            stream = sd.OutputStream(samplerate=SAMPLE_RATE, channels=2, dtype="float32", device=dev,
                                     blocksize=args.block, latency=args.latency, callback=callback)
            stream.start()
            _emit({"ev": "ready", "device": dev_name, "rate": SAMPLE_RATE, "latency": float(stream.latency),
                   "block": args.block})
    except Exception as e:
        _emit({"ev": "error", "msg": f"audio device: {e}"})
        return 1

    threading.Thread(target=_read_commands, args=(mixer, stop), daemon=True).start()
    last_clock = 0.0
    while not stop.is_set():
        stop.wait(0.02)
        while mixer.events:
            _emit(mixer.events.popleft())
        now = time.perf_counter()
        if now - last_clock >= CLOCK_EVERY_S:
            last_clock = now
            frames, dac = mixer.last_block
            _emit({"ev": "clock", "frames": frames, "dac": dac, "xruns": xruns[0], "slots": mixer.positions()})
    if stream is not None:
        stream.stop()
        stream.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
