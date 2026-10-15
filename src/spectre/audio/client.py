"""App side of the audio worker: starts the process and talks to it (see worker.py)."""

from __future__ import annotations

import collections
import json
import logging
import subprocess
import sys
import threading
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

WORKER = Path(__file__).resolve().with_name("worker.py")


class AudioClient:
    """Owns one worker process. Events arrive on a reader thread: on_event(ev)
    is called there, so a GUI listener must hand them to its own thread."""

    def __init__(self, device: str = "", block: int = 512, latency: float = 0.03, null: bool = False,
                 on_event: Optional[Callable[[dict], None]] = None):
        self.device = device
        self.block = int(block)
        self.latency = float(latency)
        self.null = bool(null)
        self.on_event = on_event
        self.proc: Optional[subprocess.Popen] = None
        self.ready = False
        self.device_name = ""
        self.error = ""
        self.xruns = 0
        # Recent (frames, dac time) pairs: the DAC's real rate (drift lock)
        self.clock: collections.deque = collections.deque(maxlen=64)
        self._lock = threading.Lock()
        self._ready_evt = threading.Event()

    @property
    def running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def start(self, wait: float = 5.0) -> bool:
        """Start the worker; True once its device is open (False on error or timeout)."""
        self.close()
        self.ready, self.error, self.device_name = False, "", ""
        self._ready_evt.clear()
        cmd = [sys.executable, str(WORKER), "--block", str(self.block), "--latency", str(self.latency)]
        if self.device:
            cmd += ["--device", self.device]
        if self.null:
            cmd.append("--null")
        try:
            self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE, text=True, bufsize=1)
        except OSError as e:
            self.error = f"audio worker: {e}"
            return False
        threading.Thread(target=self._read_events, args=(self.proc,), daemon=True).start()
        threading.Thread(target=self._read_stderr, args=(self.proc,), daemon=True).start()
        self._ready_evt.wait(wait)
        return self.ready

    def close(self) -> None:
        proc, self.proc = self.proc, None
        self.ready = False
        if proc is None:
            return
        try:
            if proc.poll() is None:
                proc.stdin.write('{"cmd": "quit"}\n')
                proc.stdin.flush()
                proc.wait(2.0)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            proc.kill()

    # -- commands ------------------------------------------------------------

    def send(self, cmd: dict) -> bool:
        proc = self.proc
        if proc is None or proc.poll() is not None:
            return False
        try:
            with self._lock:
                proc.stdin.write(json.dumps(cmd) + "\n")
                proc.stdin.flush()
            return True
        except (OSError, ValueError):
            return False

    def load(self, key: str, path: Path) -> bool:
        return self.send({"cmd": "load", "key": key, "path": str(path)})

    def unload(self, key: str) -> bool:
        return self.send({"cmd": "unload", "key": key})

    def play(self, slot: str, key: str, at: Optional[float] = None, begin: int = 0, end: int = 0,
             loop: bool = False, gain: float = 1.0, offset: int = 0, vid: int = 0) -> bool:
        return self.send({"cmd": "play", "slot": slot, "key": key, "at": at, "begin": int(begin),
                          "end": int(end), "loop": bool(loop), "gain": float(gain), "offset": int(offset),
                          "id": int(vid)})

    def retarget(self, slot: str, key: str, begin: int = 0, end: int = 0) -> bool:
        return self.send({"cmd": "retarget", "slot": slot, "key": key, "begin": int(begin), "end": int(end)})

    def stop(self, slot: str, at: Optional[float] = None) -> bool:
        return self.send({"cmd": "stop", "slot": slot, "at": at})

    def stop_all(self) -> bool:
        return self.send({"cmd": "stop_all"})

    def set_gain(self, slot: str, gain: float) -> bool:
        return self.send({"cmd": "gain", "slot": slot, "gain": float(gain)})

    def set_master(self, gain: float) -> bool:
        return self.send({"cmd": "master", "gain": float(gain)})

    # -- events --------------------------------------------------------------

    def _read_events(self, proc: subprocess.Popen) -> None:
        for line in proc.stdout:
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            kind = ev.get("ev")
            if kind == "ready":
                self.ready, self.device_name = True, str(ev.get("device", ""))
                self.latency = float(ev.get("latency", self.latency))
                self._ready_evt.set()
            elif kind == "error":
                self.error = str(ev.get("msg", ""))
                logger.warning("audio worker: %s", self.error)
                if not self.ready:
                    self._ready_evt.set()
            elif kind == "clock":
                self.xruns = int(ev.get("xruns", 0))
                self.clock.append((int(ev.get("frames", 0)), float(ev.get("dac", 0.0))))
            if self.on_event is not None:
                try:
                    self.on_event(ev)
                except Exception:
                    logger.exception("audio event listener failed")
        if proc is self.proc:
            self.ready = False
            if not self.error:
                self.error = f"audio worker stopped (exit {proc.poll()})"
            self._ready_evt.set()
            if self.on_event is not None:
                self.on_event({"ev": "exit"})

    @staticmethod
    def _read_stderr(proc: subprocess.Popen) -> None:
        for line in proc.stderr:
            if line.strip():
                logger.warning("audio worker: %s", line.rstrip())
