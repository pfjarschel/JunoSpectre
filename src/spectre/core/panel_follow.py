"""Following the JUNO-DS panel: what the synth reports, and what to re-read.

The synth tells us about panel actions in two ways (hardware, 2026-10-11):
- picking a performance sends Bank Select + Program Change on the
  performance control channel (16), bank 85;
- with SYSTEM > MIDI > Transmit Edit Data on, every panel edit goes out as
  a DT1 at the parameter's address (patch, performance and Setup edits).
Panel knobs send CCs on the current part's channel, not SysEx; they are
not followed here.

PanelFollower turns raw messages into events; FollowPlan collects them so
a burst (a knob turn sends one DT1 per value step) becomes one re-read.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence

from .sysex import CMD_DT1, RolandSysEx

PERF_CONTROL_CHANNEL = 15        # 0-based: MIDI channel 16
PERF_BANK_MSB = 85               # user (LSB 0) and preset (LSB 64) performances

SETUP_SOUND_MODE = 0x00
SETUP_ARP_FIRST, SETUP_ARP_LAST = 0x17, 0x33


@dataclass
class FollowPlan:
    """What the panel changed since the last re-read."""
    perf: Optional[tuple] = None      # (msb, lsb, pc): a performance was picked
    program: Optional[tuple] = None   # (channel, msb, lsb, pc): a patch was picked
    mode: Optional[int] = None        # Setup Sound Mode (0 PATCH, 1 PERFORM)
    parts: bool = False               # part/zone/MIDI blocks of the performance
    perf_fx: bool = False             # performance common, MFX1-3, chorus, reverb
    part_patches: set = field(default_factory=set)  # parts whose sound was edited
    patch: bool = False               # PATCH-mode temp patch edited
    arp: bool = False

    def empty(self) -> bool:
        return (self.perf is None and self.program is None and self.mode is None
                and not (self.parts or self.perf_fx or self.part_patches
                         or self.patch or self.arp))

    def add(self, event: tuple) -> None:
        kind = event[0]
        if kind == "perf":
            self.perf = event[1:]
        elif kind == "program":
            self.program = event[1:]
        elif kind == "edit":
            self.add_edit(event[1], event[2])

    def add_edit(self, address: Sequence[int], data: Sequence[int] = b"") -> None:
        a0, a1, a2, a3 = (int(a) for a in address)
        if a0 == 0x01 and a1 == 0x00 and a2 == 0x00:
            if a3 == SETUP_SOUND_MODE and len(data):
                self.mode = int(data[0])
            elif SETUP_ARP_FIRST <= a3 <= SETUP_ARP_LAST:
                self.arp = True
        elif a0 == 0x10 and a1 == 0x00:
            if a2 < 0x10:
                self.perf_fx = True
            elif a2 < 0x60:
                self.parts = True
        elif 0x11 <= a0 <= 0x14:
            self.part_patches.add(((a0 - 0x11) * 128 + a1) // 0x20 + 1)
        elif a0 == 0x1F and a1 < 0x20:
            self.patch = True


class PanelFollower:
    """Turns messages from the synth into panel events.

    Events: ("perf", msb, lsb, pc), ("program", channel, msb, lsb, pc) and
    ("edit", address, data). is_own(address, data) drops the app's own
    traffic (read replies, echoes of its writes).
    """

    def __init__(self, is_own: Optional[Callable[[Sequence[int], Sequence[int]], bool]] = None):
        self.is_own = is_own
        self._bank: dict[int, list[int]] = {}

    def feed(self, msg) -> Optional[tuple]:
        kind = getattr(msg, "type", "")
        if kind == "control_change":
            if msg.control in (0, 32):
                bank = self._bank.setdefault(msg.channel, [0, 0])
                bank[0 if msg.control == 0 else 1] = int(msg.value)
            return None
        if kind == "program_change":
            msb, lsb = self._bank.get(msg.channel, (0, 0))
            if msg.channel == PERF_CONTROL_CHANNEL and msb == PERF_BANK_MSB:
                return ("perf", msb, lsb, int(msg.program))
            return ("program", int(msg.channel), msb, lsb, int(msg.program))
        if kind == "sysex":
            parsed = RolandSysEx.parse(msg.data)
            if parsed is None or parsed.command != CMD_DT1 or not parsed.is_valid_checksum:
                return None
            if self.is_own is not None and self.is_own(parsed.address, parsed.payload):
                return None
            return ("edit", tuple(parsed.address), bytes(parsed.payload))
        return None
