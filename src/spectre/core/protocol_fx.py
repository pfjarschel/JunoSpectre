"""MFX / chorus / reverb block writers.

The patch, performance common and part-patch FX blocks share one layout, so
one set of writers serves all three. Each takes the block base addresses to
write (the block itself, plus a mirror such as the performance common MFX1
that PATCH mode keeps in step).
"""

from __future__ import annotations

import logging
from typing import Optional, Sequence, Tuple

from .sysex import (
    ADDR_SETUP_CHORUS_SWITCH,
    ADDR_SETUP_REVERB_SWITCH,
    CHORUS_PARAM_LEVEL,
    CHORUS_PARAM_OUTPUT_SELECT,
    CHORUS_PARAM_TYPE,
    MFX_PARAM_CHORUS_SEND,
    MFX_PARAM_DATA_START,
    MFX_PARAM_DRY_SEND,
    MFX_PARAM_REVERB_SEND,
    MFX_PARAM_TYPE,
    REVERB_PARAM_LEVEL,
    REVERB_PARAM_TYPE,
    add_address,
    pack_4nibbles,
)

logger = logging.getLogger(__name__)

Address = Tuple[int, int, int, int]


def _clamp(v: int, hi: int) -> list[int]:
    return [max(0, min(hi, int(v)))]


class FxBlockWriterMixin:
    """Writes into FX blocks at given base addresses."""

    def _fx_send(self, bases: Sequence[Address], offset: int, data: list[int]) -> None:
        for base in bases:
            self.send_data(add_address(base, offset), data)

    def write_mfx(self, bases: Sequence[Address], mfx_type: Optional[int] = None,
                  dry_send: Optional[int] = None, chorus_send: Optional[int] = None,
                  reverb_send: Optional[int] = None) -> None:
        """MFX type (0..80) and sends (0..127); None leaves a field alone."""
        for offset, val, hi in ((MFX_PARAM_TYPE, mfx_type, 80), (MFX_PARAM_DRY_SEND, dry_send, 127),
                                (MFX_PARAM_CHORUS_SEND, chorus_send, 127),
                                (MFX_PARAM_REVERB_SEND, reverb_send, 127)):
            if val is not None:
                self._fx_send(bases, offset, _clamp(val, hi))

    def write_mfx_params(self, bases: Sequence[Address], values: Sequence[int],
                         start_index: int = 0) -> None:
        """Contiguous MFX parameters (signed, 4-nibble) from start_index, in one DT1."""
        values = list(values)
        if not values:
            return
        start = int(start_index)
        if start < 0 or start + len(values) > 32:
            raise ValueError(f"MFX parameters {start}..{start + len(values) - 1} out of 0..31")
        nibbles = [n for v in values for n in pack_4nibbles(int(v) + 32768)]
        self._fx_send(bases, MFX_PARAM_DATA_START + start * 4, nibbles)

    def write_chorus(self, bases: Sequence[Address], chorus_type: Optional[int] = None,
                     level: Optional[int] = None, output_select: Optional[int] = None,
                     master_switch: bool = False) -> None:
        """Chorus type (0..3), level, output select (0..2). master_switch also sets
        the Setup chorus switch from the type (for the sounding FX)."""
        if chorus_type is not None:
            data = _clamp(chorus_type, 3)
            self._fx_send(bases, CHORUS_PARAM_TYPE, data)
            if master_switch:
                self.send_data(ADDR_SETUP_CHORUS_SWITCH, [0 if data[0] == 0 else 1])
        if level is not None:
            self._fx_send(bases, CHORUS_PARAM_LEVEL, _clamp(level, 127))
        if output_select is not None:
            self._fx_send(bases, CHORUS_PARAM_OUTPUT_SELECT, _clamp(output_select, 2))

    def write_reverb(self, bases: Sequence[Address], reverb_type: Optional[int] = None,
                     level: Optional[int] = None, master_switch: bool = False) -> None:
        """Reverb type (0..5) and level; master_switch as in write_chorus."""
        if reverb_type is not None:
            data = _clamp(reverb_type, 5)
            self._fx_send(bases, REVERB_PARAM_TYPE, data)
            if master_switch:
                self.send_data(ADDR_SETUP_REVERB_SWITCH, [0 if data[0] == 0 else 1])
        if level is not None:
            self._fx_send(bases, REVERB_PARAM_LEVEL, _clamp(level, 127))

    def write_fx_detail(self, bases: Sequence[Address], offsets: dict, param: str, val: int) -> None:
        """One chorus/reverb detail parameter (0..127, 4-nibble) by its UI name."""
        offset = offsets.get(param)
        if offset is None:
            logger.warning(f"Unknown FX parameter: {param}")
            return
        self._fx_send(bases, offset, pack_4nibbles(max(0, min(127, int(val))) + 32768))
