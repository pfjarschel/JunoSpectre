"""JUNO-DS arpeggiator settings and the app's MIDI clock output.

The arpeggiator lives in the Setup block (01 00 00 17..33, MIDI
Implementation p.21): it is global, and the keyboard can't save it
("The arpeggio settings cannot be saved", owner's manual p.8). The app
keeps these settings in patch and performance files and pushes them on load.

In PERFORM the part the arp plays is set on the Juno's ARPEGGIO screen only:
no SysEx sets or reads it (tested 2026-10-11). The documented Arpeggio Zone
Number (10 00 60 18) is never applied, not even on a performance load, and
with Transmit Edit Data on the Juno sends nothing when Part changes.

The arp runs on the Juno's tempo, which SysEx can't set. MidiClockOut
sends 24 PPQN Timing Clock at the app's tempo; with the Juno's
SYSTEM > SYNC/TEMPO Sync Mode on SLAVE (Clock Source USB) the arp follows it.
"""

from __future__ import annotations

import dataclasses
import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

ADDR_SETUP_ARP = (0x01, 0x00, 0x00, 0x17)   # first arp byte (Grid)
ARP_SETUP_SIZE = 0x33 - 0x17 + 1

# Setup byte offset of each field (01 00 00 xx)
SETUP_OFFSETS = {
    "grid": 0x17, "duration": 0x18, "switch": 0x19, "style": 0x1B, "motif": 0x1C,
    "octave": 0x1D, "hold": 0x1E, "accent": 0x1F, "velocity": 0x20, "step": 0x33,
}

# Arpeggio Style List (Parameter Guide p.86); (n) = notes to press,
# (a) = as desired, (p) = one note with Motif "Phrase"
STYLE_NAMES = (
    ["Basic 1 (a)", "Basic 2 (a)", "Basic 3 (a)", "Basic 4 (a)", "Basic 5 (a)", "Basic 6 (a)"]
    + [f"Seq Ptn {n} ({c})" for n, c in zip(range(1, 33), "2" * 5 + "3" * 12 + "4" * 12 + "556")]
    + [f"Seq Ptn {n} (p)" for n in range(33, 61)]
    + [f"Bassline {n} ({c})" for n, c in zip(range(1, 22), "111111111222222333333")]
    + [f"Bassline {n} (p)" for n in range(22, 42)]
    + [f"Sliced {n} (a)" for n in range(1, 11)]
    + ["Gtr Arp 1 (4)", "Gtr Arp 2 (5)", "Gtr Arp 3 (6)", "Gtr Backing 1 (a)", "Gtr Backing 2 (a)",
       "Key Bckng1 (a)", "Key Bckng2 (a)", "Key Bckng3 (1-3)",
       "1/1 Note Trg (1)", "1/2 Note Trg (1)", "1/4 Note Trg (1)"]
)
assert len(STYLE_NAMES) == 128

MOTIFS = ["Up (L)", "Up (L&H)", "Up (_)", "Down (L)", "Down (L&H)", "Down (_)",
          "U/D (L)", "U/D (L&H)", "U/D (_)", "Rand (L)", "Rand (_)", "Phrase"]
GRIDS = ["1/4", "1/8", "1/8 L", "1/8 H", "1/12", "1/16", "1/16 L", "1/16 H", "1/24"]
DURATIONS = ["30%", "40%", "50%", "60%", "70%", "80%", "90%", "100%", "120%", "Full"]


@dataclass
class ArpSettings:
    switch: bool = False
    style: int = 0        # 0..127 = style 001..128
    motif: int = 2        # MOTIFS index
    grid: int = 5         # GRIDS index (1/16)
    duration: int = 7     # DURATIONS index (100%)
    octave: int = 0       # -3..+3
    hold: bool = False
    accent: int = 100     # 0..100
    velocity: int = 0     # 0 = REAL, 1..127 fixed
    step: int = 0         # 0 = AUTO, 1..32

    def clamped(self) -> "ArpSettings":
        def c(v, lo, hi):
            return max(lo, min(hi, int(v)))
        return ArpSettings(
            switch=bool(self.switch), style=c(self.style, 0, 127),
            motif=c(self.motif, 0, len(MOTIFS) - 1), grid=c(self.grid, 0, len(GRIDS) - 1),
            duration=c(self.duration, 0, len(DURATIONS) - 1), octave=c(self.octave, -3, 3),
            hold=bool(self.hold), accent=c(self.accent, 0, 100), velocity=c(self.velocity, 0, 127),
            step=c(self.step, 0, 32))

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: Any) -> Optional["ArpSettings"]:
        if not isinstance(d, dict):
            return None
        names = {f.name for f in dataclasses.fields(cls)}
        try:
            return cls(**{k: v for k, v in d.items() if k in names}).clamped()
        except (TypeError, ValueError):
            return None

    def setup_value(self, field: str) -> int:
        """Raw Setup byte of `field`."""
        v = getattr(self, field)
        if field == "octave":
            return 64 + int(v)
        return int(v)

    def setup_bytes(self) -> dict:
        """{Setup offset: raw byte} for every arp field."""
        return {off: self.setup_value(f) for f, off in SETUP_OFFSETS.items()}

    @classmethod
    def from_setup(cls, data: bytes) -> "ArpSettings":
        """Parse the Setup bytes read from 01 00 00 17 (ARP_SETUP_SIZE long)."""
        def b(field):
            return int(data[SETUP_OFFSETS[field] - 0x17])
        return cls(switch=bool(b("switch")), style=b("style"), motif=b("motif"), grid=b("grid"),
                   duration=b("duration"), octave=b("octave") - 64, hold=bool(b("hold")),
                   accent=b("accent"), velocity=b("velocity"), step=b("step")).clamped()


# Value labels per field, for knobs and the LCXL3 screen
FIELD_LABELS: dict[str, list[str]] = {
    "style": [f"{i + 1:03d} {n}" for i, n in enumerate(STYLE_NAMES)],
    "motif": MOTIFS,
    "grid": GRIDS,
    "duration": DURATIONS,
    "octave": [f"{o:+d}" if o else "0" for o in range(-3, 4)],
    "accent": [str(v) for v in range(101)],
    "velocity": ["REAL"] + [str(v) for v in range(1, 128)],
    "step": ["AUTO"] + [str(v) for v in range(1, 33)],
}
_FIELD_MIN = {"octave": -3}


def field_label(settings: ArpSettings, field: str) -> str:
    return FIELD_LABELS[field][int(getattr(settings, field)) - _FIELD_MIN.get(field, 0)]


def field_from_label(field: str, label: str) -> Optional[int]:
    try:
        return FIELD_LABELS[field].index(label) + _FIELD_MIN.get(field, 0)
    except ValueError:
        return None


class MidiClockOut:
    """Free-running 24 PPQN MIDI Timing Clock on a background thread.

    Sends only while enabled and the port is open. Deadlines accumulate,
    so jitter (plain sleeps, ~0.1-1 ms) never adds up to tempo drift.
    """

    PPQN = 24

    def __init__(self, send: Callable[[], bool], bpm: float = 120.0):
        self._send = send            # sends one clock byte; False when no port
        self._bpm = float(bpm)
        self._enabled = False
        self._next = 0.0
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_bpm(self, bpm: float) -> None:
        self._bpm = max(20.0, min(300.0, float(bpm)))

    def set_enabled(self, on: bool) -> None:
        self._enabled = bool(on)
        if self._enabled and self._thread is None:
            self._thread = threading.Thread(target=self._run, name="midi-clock-out", daemon=True)
            self._thread.start()
        self.resync()

    def resync(self) -> None:
        """Restart the pulse grid now (sequencer start: beats line up)."""
        self._next = time.perf_counter()
        self._wake.set()

    def close(self) -> None:
        self._stop.set()
        self._wake.set()

    def _run(self) -> None:
        self._next = time.perf_counter()
        while not self._stop.is_set():
            if not self._enabled:
                self._wake.wait(0.5)
                self._wake.clear()
                self._next = time.perf_counter()
                continue
            wait = self._next - time.perf_counter()
            if wait > 0:
                if self._wake.wait(wait):
                    self._wake.clear()
                    continue
            try:
                self._send()
            except Exception as e:
                logger.debug(f"MIDI clock send failed: {e}")
            self._next += 60.0 / (self._bpm * self.PPQN)
            if time.perf_counter() - self._next > 0.25:
                self._next = time.perf_counter()   # stalled (suspend, port gone): don't burst

