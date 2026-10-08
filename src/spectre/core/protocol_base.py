"""Base protocol definitions and transport mixin for Roland JUNO-DS / XPS-30."""

from __future__ import annotations

import enum
import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

from .midi import MidiDeviceManager
from .sysex import (
    ADDR_SETUP,
    ADDR_TEMP_PATCH_PART_1,
    DEFAULT_DEVICE_ID,
    JUNO_DS_MODEL_ID,
    RolandSysEx,
    temp_perf_patch_base,
)

logger = logging.getLogger(__name__)

INIT_WRITE_GAP_S = 0.012
INIT_MAX_VERIFY_REPAIRS = 1

class SoundMode(enum.IntEnum):
    PATCH = 0
    PERFORM = 1
    GM1 = 2
    GM2 = 3
    GS = 4


@dataclass(frozen=True)
class IdentityInfo:
    device_id: int
    family_code: Tuple[int, int]
    family_number: Tuple[int, int]
    software_revision: Tuple[int, int, int, int]

    @property
    def is_juno_ds_or_xps(self) -> bool:
        """Check if family code matches Roland JUNO-DS / XPS series (0x3A 0x02)."""
        return self.family_code == (0x3A, 0x02)


@dataclass(frozen=True)
class InitWriteMismatch:
    """One expected init byte sequence that did not read back correctly."""

    label: str
    address: Tuple[int, int, int, int]
    expected: bytes
    actual: Optional[bytes]


@dataclass
class InitVerification:
    """Outcome of post-init readback, including attempted selective repairs."""

    detected: List[InitWriteMismatch] = field(default_factory=list)
    repaired: List[InitWriteMismatch] = field(default_factory=list)
    failed: List[InitWriteMismatch] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failed


class BaseProtocolMixin:
    """Client for bidirectional communication with Roland JUNO-DS / XPS-30."""

    def __init__(
        self,
        midi_mgr: MidiDeviceManager,
        device_id: int = DEFAULT_DEVICE_ID,
        model_id: Sequence[int] = JUNO_DS_MODEL_ID,
    ):
        self.midi = midi_mgr
        self.device_id = device_id
        self.model_id = tuple(model_id)
        self.sysex = RolandSysEx(device_id=self.device_id, model_id=self.model_id)
        self._cached_patch_base: Optional[Tuple[int, int, int, int]] = None
        self._cached_patch_part: Optional[int] = None
        self._cached_sound_mode: Optional[SoundMode] = None
        self._active_perf_part: int = 1
        self._min_send_interval_s: float = 0.0
        self._last_send_time: float = 0.0

    def invalidate_cache(self) -> None:
        """Clear cached state (call when changing synth patches or modes)."""
        self._cached_patch_base = None
        self._cached_patch_part = None
        self._cached_sound_mode = None

    @property
    def is_connected(self) -> bool:
        """True if underlying MIDI connection to synth is active."""
        if self.midi is None:
            return False
        if hasattr(self.midi, "is_juno_connected"):
            return bool(self.midi.is_juno_connected)
        return True

    def ensure_connected(self, force_reconnect: bool = False) -> bool:
        """Verify connection or attempt auto-recovery."""
        if not force_reconnect and self.is_connected:
            return True
        if hasattr(self.midi, "reconnect_juno"):
            if self.midi.reconnect_juno():
                self.invalidate_cache()
                return True
        return False

    @property
    def active_perf_part(self) -> int:
        return self._active_perf_part

    def set_active_perf_part(self, part: int) -> None:
        """Select which performance part patch editors target (1..16)."""
        self._active_perf_part = max(1, min(16, int(part)))
        if self._cached_patch_part != self._active_perf_part:
            self._cached_patch_base = None
            self._cached_patch_part = self._active_perf_part

    @contextmanager
    def paced_init_writes(self, gap: float = INIT_WRITE_GAP_S):
        """Temporarily enforce a minimum interval between outgoing DT1 writes."""
        previous_gap = self._min_send_interval_s
        self._min_send_interval_s = max(0.0, float(gap))
        try:
            yield self
        finally:
            self._min_send_interval_s = previous_gap

    def ping(self, timeout: float = 1.0) -> Optional[IdentityInfo]:
        """Send Universal Non-realtime Identity Request and wait for reply."""
        # F0 7E 7F 06 01 F7 (Broadcast)
        req_data = [0x7E, 0x7F, 0x06, 0x01]
        self.midi.send_juno_sysex(req_data)

        start = time.perf_counter()
        while time.perf_counter() - start < timeout:
            for msg in self.midi.iter_juno_messages():
                if msg.type == "sysex" and len(msg.data) >= 13:
                    # Check Universal Identity Reply: 7E <dev> 06 02 41 ...
                    d = msg.data
                    if d[0] == 0x7E and d[2] == 0x06 and d[3] == 0x02 and d[4] == 0x41:
                        return IdentityInfo(
                            device_id=d[1],
                            family_code=(d[5], d[6]),
                            family_number=(d[7], d[8]),
                            software_revision=(d[9], d[10], d[11], d[12]),
                        )
            time.sleep(0.005)
        return None

    @staticmethod
    def _rq_size(length: int) -> Tuple[int, int, int, int]:
        """Encode an RQ1 byte count as four Roland 7-bit size bytes."""
        if length < 0 or length > 0x0FFFFFFF:
            raise ValueError(f"RQ1 size out of range: {length}")
        return (
            (length >> 21) & 0x7F,
            (length >> 14) & 0x7F,
            (length >> 7) & 0x7F,
            length & 0x7F,
        )

    def request_data(
        self,
        address: Sequence[int],
        size: Sequence[int],
        timeout: float = 1.0,
    ) -> Optional[bytes]:
        """Send RQ1 data request and await matching DT1 response."""
        packet = self.sysex.build_rq1(address, size)
        self.midi.send_juno_sysex(packet)

        target_addr = tuple(address)
        start = time.perf_counter()
        while time.perf_counter() - start < timeout:
            for msg in self.midi.iter_juno_messages():
                if msg.type == "sysex":
                    parsed = RolandSysEx.parse(msg.data)
                    if (
                        parsed
                        and parsed.is_valid_checksum
                        and parsed.address == target_addr
                    ):
                        return parsed.payload
            time.sleep(0.005)
        return None

    def send_data(self, address: Sequence[int], data: Sequence[int]) -> None:
        """Send DT1 data set message directly to the synth."""
        if self._min_send_interval_s > 0.0:
            wait = self._min_send_interval_s - (time.monotonic() - self._last_send_time)
            if wait > 0.0:
                time.sleep(wait)
        packet = self.sysex.build_dt1(address, data)
        try:
            self.midi.send_juno_sysex(packet)
        except (ConnectionError, OSError, RuntimeError):
            if self.ensure_connected(force_reconnect=True):
                self.midi.send_juno_sysex(packet)
            else:
                raise
        self._last_send_time = time.monotonic()

    def get_sound_mode(self, timeout: float = 1.0, force_refresh: bool = False) -> SoundMode:
        """Query synth Sound Mode (Setup address 01 00 00 00)."""
        if not force_refresh and self._cached_sound_mode is not None:
            return self._cached_sound_mode
        res = self.request_data(ADDR_SETUP, (0x00, 0x00, 0x00, 0x01), timeout=timeout)
        if res is None or len(res) == 0:
            raise TimeoutError("Timed out waiting for Sound Mode response from synth.")
        self._cached_sound_mode = SoundMode(res[0])
        return self._cached_sound_mode

    def get_active_patch_base(
        self,
        timeout: float = 1.0,
        force_refresh: bool = False,
    ) -> Tuple[int, int, int, int]:
        """Determine base address for the current temporary patch buffer.

        PATCH mode -> 1F 00 00 00. PERFORM mode -> 11 00 00 00 +
        (active_perf_part - 1) * 0x20, so deep edits target the selected part.
        """
        if (not force_refresh and self._cached_patch_base is not None
                and self._cached_patch_part == self._active_perf_part):
            return self._cached_patch_base
        mode = self.get_sound_mode(timeout=timeout, force_refresh=force_refresh)
        if mode == SoundMode.PATCH:
            self._cached_patch_base = ADDR_TEMP_PATCH_PART_1
        else:
            self._cached_patch_base = temp_perf_patch_base(self._active_perf_part)
        self._cached_patch_part = self._active_perf_part
        return self._cached_patch_base

    def set_sound_mode(self, mode: SoundMode | int | str) -> None:
        """Switch the synth sound mode (Setup 01 00 00 00 = PATCH/PERFORM/GM1/GM2/GS)."""
        if isinstance(mode, str):
            mode = SoundMode[mode.upper()]
        else:
            mode = SoundMode(int(mode))
        self.send_data(ADDR_SETUP, [int(mode)])
        self._cached_sound_mode = mode
        self._cached_patch_base = None
