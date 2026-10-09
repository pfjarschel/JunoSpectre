"""Performance mode protocol mixin for Roland JUNO-DS / XPS-30."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .patch_state import PatchState

from .patch_state import PerfFxState, PerfPartState
from .sysex import (
    ADDR_PERF_CHORUS,
    ADDR_PERF_REVERB,
    ADDR_SETUP_CHORUS_SWITCH,
    ADDR_SETUP_REVERB_SWITCH,
    ADDR_TEMP_PERFORMANCE,
    CHORUS_PARAM_DEPTH,
    CHORUS_PARAM_FEEDBACK,
    CHORUS_PARAM_LEVEL,
    CHORUS_PARAM_OUTPUT_SELECT,
    CHORUS_PARAM_PREDELAY,
    CHORUS_PARAM_RATE,
    CHORUS_PARAM_TYPE,
    MFX_PARAM_CHORUS_SEND,
    MFX_PARAM_DATA_START,
    MFX_PARAM_DRY_SEND,
    MFX_PARAM_REVERB_SEND,
    MFX_PARAM_TYPE,
    OFFSET_PATCH_COMMON_CHORUS,
    OFFSET_PATCH_COMMON_MFX,
    OFFSET_PATCH_COMMON_REVERB,
    PERF_CHORUS_BLOCK_SIZE,
    PERF_COMMON_CHORUS_SOURCE,
    PERF_COMMON_MFX1_SOURCE,
    PERF_COMMON_MFX2_SOURCE,
    PERF_COMMON_MFX3_SOURCE,
    PERF_COMMON_MFX_STRUCTURE,
    PERF_COMMON_NAME,
    PERF_COMMON_NAME_SIZE,
    PATCH_PARAM_NAME,
    PERF_COMMON_REVERB_SOURCE,
    PERF_COMMON_SOLO_PART,
    PERF_MFX_BLOCK_SIZE,
    PERF_PART_BLOCK_SIZE,
    PERF_PART_CHORUS_SEND,
    PERF_PART_COARSE_TUNE,
    PERF_PART_DRY_SEND,
    PERF_PART_FINE_TUNE,
    PERF_PART_LEVEL,
    PERF_PART_MUTE,
    PERF_PART_OCTAVE_SHIFT,
    PERF_PART_OUTPUT_ASSIGN,
    PERF_PART_OUTPUT_MFX_SELECT,
    PERF_PART_PAN,
    PERF_PART_PATCH_LSB,
    PERF_PART_PATCH_MSB,
    PERF_PART_PATCH_PC,
    PERF_PART_REVERB_SEND,
    PERF_PART_RX_CHANNEL,
    PERF_PART_RX_SWITCH,
    PERF_REVERB_BLOCK_SIZE,
    PERF_ZONE_BLOCK_SIZE,
    PERF_ZONE_KEY_HIGH,
    PERF_ZONE_KEY_LOW,
    PERF_ZONE_OCTAVE_SHIFT,
    PERF_ZONE_SWITCH,
    REVERB_PARAM_DIFFUSION,
    REVERB_PARAM_HF_DAMP,
    REVERB_PARAM_LEVEL,
    REVERB_PARAM_PREDELAY,
    REVERB_PARAM_TIME,
    REVERB_PARAM_TONE,
    REVERB_PARAM_TYPE,
    add_address,
    pack_4nibbles,
    perf_common_fx_base,
    perf_part_base,
    perf_zone_base,
    temp_perf_patch_base,
)

logger = logging.getLogger(__name__)


class PerformanceProtocolMixin:
    """Performance mixer, routing, FX origins, zones and part deep-edits."""

    @staticmethod
    def _check_part(part_index: int) -> int:
        part = int(part_index)
        if not 1 <= part <= 16:
            raise ValueError(f"Performance part must be 1..16, got {part_index}")
        return part

    def set_perf_part_level(self, part_index: int, level: int) -> None:
        part = self._check_part(part_index)
        addr = add_address(perf_part_base(part), PERF_PART_LEVEL)
        self.send_data(addr, [max(0, min(127, int(level)))])

    def set_perf_part_pan(self, part_index: int, pan: int) -> None:
        part = self._check_part(part_index)
        addr = add_address(perf_part_base(part), PERF_PART_PAN)
        self.send_data(addr, [max(0, min(127, int(pan)))])

    def set_perf_part_rx(self, part_index: int, channel: int | None = None,
                         enabled: bool | None = None) -> None:
        part = self._check_part(part_index)
        base = perf_part_base(part)
        if channel is not None:
            self.send_data(add_address(base, PERF_PART_RX_CHANNEL),
                            [max(0, min(15, int(channel)))])
        if enabled is not None:
            self.send_data(add_address(base, PERF_PART_RX_SWITCH),
                            [1 if enabled else 0])

    def set_perf_part_mute(self, part_index: int, muted: bool) -> None:
        """Mute Switch: 0 = sounding (OFF), 1 = MUTE."""
        part = self._check_part(part_index)
        addr = add_address(perf_part_base(part), PERF_PART_MUTE)
        self.send_data(addr, [1 if muted else 0])

    def set_perf_solo(self, part_index: int) -> None:
        """Solo Part Select in Performance Common: 0 = OFF, 1..16 = soloed part."""
        part = int(part_index)
        if not 0 <= part <= 16:
            raise ValueError(f"Solo part must be 0..16, got {part_index}")
        addr = add_address(ADDR_TEMP_PERFORMANCE, PERF_COMMON_SOLO_PART)
        self.send_data(addr, [part])

    def set_perf_part_patch(self, part_index: int, msb: int, lsb: int, pc: int) -> None:
        part = self._check_part(part_index)
        base = perf_part_base(part)
        self.send_data(add_address(base, PERF_PART_PATCH_MSB),
                       [max(0, min(127, int(msb))), max(0, min(127, int(lsb))),
                        max(0, min(127, int(pc)))])

    def set_perf_part_coarse_fine(self, part_index: int,
                                  coarse: int | None = None,
                                  fine: int | None = None) -> None:
        part = self._check_part(part_index)
        base = perf_part_base(part)
        if coarse is not None:
            self.send_data(add_address(base, PERF_PART_COARSE_TUNE),
                           [max(16, min(112, int(coarse)))])
        if fine is not None:
            self.send_data(add_address(base, PERF_PART_FINE_TUNE),
                           [max(14, min(114, int(fine)))])

    def set_perf_part_fx(self, part_index: int,
                         dry: int | None = None,
                         chorus: int | None = None,
                         reverb: int | None = None) -> None:
        """Write per-part sends: dry 0x1C, chorus 0x1D (CC#93), reverb 0x1E (CC#91)."""
        part = self._check_part(part_index)
        base = perf_part_base(part)
        if dry is not None:
            self.send_data(add_address(base, PERF_PART_DRY_SEND),
                           [max(0, min(127, int(dry)))])
        if chorus is not None:
            self.send_data(add_address(base, PERF_PART_CHORUS_SEND),
                           [max(0, min(127, int(chorus)))])
        if reverb is not None:
            self.send_data(add_address(base, PERF_PART_REVERB_SEND),
                           [max(0, min(127, int(reverb)))])

    def set_perf_part_output(self, part_index: int,
                             assign: int | None = None,
                             mfx_select: int | None = None) -> None:
        """Write per-part output assign 0x1F (PATCH=13) and MFX select 0x20 (0..2)."""
        part = self._check_part(part_index)
        base = perf_part_base(part)
        if assign is not None:
            self.send_data(add_address(base, PERF_PART_OUTPUT_ASSIGN),
                           [max(0, min(13, int(assign)))])
        if mfx_select is not None:
            self.send_data(add_address(base, PERF_PART_OUTPUT_MFX_SELECT),
                           [max(0, min(2, int(mfx_select)))])

    @staticmethod
    def _check_perf_mfx_slot(slot: int) -> int:
        s = int(slot)
        if not 1 <= s <= 3:
            raise ValueError(f"Performance MFX slot must be 1..3, got {slot}")
        return s

    @staticmethod
    def _check_perf_source(origin: int) -> int:
        o = int(origin)
        if not 0 <= o <= 16:
            raise ValueError(f"Performance FX source must be 0..16 (PERFORM=0), got {origin}")
        return o

    def set_perf_source(self, which: str, origin: int) -> None:
        """Set FX origin: which in mfx1/mfx2/mfx3/chorus/reverb, origin 0=PERFORM 1..16=PARTn."""
        key = str(which or "").lower()
        mapping = {
            "mfx1": PERF_COMMON_MFX1_SOURCE,
            "mfx2": PERF_COMMON_MFX2_SOURCE,
            "mfx3": PERF_COMMON_MFX3_SOURCE,
            "chorus": PERF_COMMON_CHORUS_SOURCE,
            "cho": PERF_COMMON_CHORUS_SOURCE,
            "reverb": PERF_COMMON_REVERB_SOURCE,
            "rev": PERF_COMMON_REVERB_SOURCE,
        }
        if key not in mapping:
            raise ValueError(f"Unknown perf FX source '{which}'. Use mfx1/mfx2/mfx3/chorus/reverb.")
        addr = add_address(ADDR_TEMP_PERFORMANCE, mapping[key])
        self.send_data(addr, [self._check_perf_source(origin)])

    def get_perf_sources(self, timeout: float = 1.0) -> dict:
        """Read the 5 FX origins + MFX structure (tolerant: defaults on timeout)."""
        out = {"mfx1": 0, "mfx2": 0, "mfx3": 0, "chorus": 0, "reverb": 0, "structure": 0}
        pairs = [
            ("mfx1", PERF_COMMON_MFX1_SOURCE), ("mfx2", PERF_COMMON_MFX2_SOURCE),
            ("mfx3", PERF_COMMON_MFX3_SOURCE), ("chorus", PERF_COMMON_CHORUS_SOURCE),
            ("reverb", PERF_COMMON_REVERB_SOURCE), ("structure", PERF_COMMON_MFX_STRUCTURE),
        ]
        for key, off in pairs:
            try:
                res = self.request_data(add_address(ADDR_TEMP_PERFORMANCE, off),
                                        (0x00, 0x00, 0x00, 0x01), timeout=timeout)
                if res:
                    v = int(res[0])
                    out[key] = max(0, min(15, v)) if key == "structure" else max(0, min(16, v))
            except Exception as e:
                logger.debug(f"get_perf_sources: read failed for '{key}': {e}")
                continue
        return out

    def set_perf_structure(self, structure: int) -> None:
        """Set MFX Structure TYPE01..16 (0..15 on the wire)."""
        addr = add_address(ADDR_TEMP_PERFORMANCE, PERF_COMMON_MFX_STRUCTURE)
        self.send_data(addr, [max(0, min(15, int(structure)))])

    def set_perf_mfx(self, slot: int, mfx_type: int | None = None,
                     dry_send: int | None = None,
                     chorus_send: int | None = None,
                     reverb_send: int | None = None) -> None:
        """Write Performance Common MFX slot type + sends (10 00 02/08/0A)."""
        s = self._check_perf_mfx_slot(slot)
        base = perf_common_fx_base(s)
        if mfx_type is not None:
            self.send_data(add_address(base, MFX_PARAM_TYPE), [max(0, min(80, int(mfx_type)))])
        if dry_send is not None:
            self.send_data(add_address(base, MFX_PARAM_DRY_SEND), [max(0, min(127, int(dry_send)))])
        if chorus_send is not None:
            self.send_data(add_address(base, MFX_PARAM_CHORUS_SEND), [max(0, min(127, int(chorus_send)))])
        if reverb_send is not None:
            self.send_data(add_address(base, MFX_PARAM_REVERB_SEND), [max(0, min(127, int(reverb_send)))])

    def set_perf_mfx_param(self, slot: int, param_index: int, value: int) -> None:
        """Write one 4-nibble MFX parameter into a Performance Common MFX slot."""
        s = self._check_perf_mfx_slot(slot)
        if not 0 <= int(param_index) <= 31:
            raise ValueError(f"MFX parameter index must be 0..31, got {param_index}")
        base = perf_common_fx_base(s)
        addr = add_address(base, MFX_PARAM_DATA_START + int(param_index) * 4)
        self.send_data(addr, pack_4nibbles(int(value) + 32768))

    def set_perf_chorus(self, chorus_type: int | None = None,
                        level: int | None = None,
                        output_select: int | None = None) -> None:
        """Write Performance Common chorus (10 00 04 00)."""
        if chorus_type is not None:
            self.send_data(add_address(ADDR_PERF_CHORUS, CHORUS_PARAM_TYPE),
                           [max(0, min(3, int(chorus_type)))])
            self.send_data(ADDR_SETUP_CHORUS_SWITCH, [0 if int(chorus_type) == 0 else 1])
        if level is not None:
            self.send_data(add_address(ADDR_PERF_CHORUS, CHORUS_PARAM_LEVEL),
                           [max(0, min(127, int(level)))])
        if output_select is not None:
            self.send_data(add_address(ADDR_PERF_CHORUS, CHORUS_PARAM_OUTPUT_SELECT),
                           [max(0, min(2, int(output_select)))])

    def set_perf_reverb(self, reverb_type: int | None = None,
                        level: int | None = None) -> None:
        """Write Performance Common reverb (10 00 06 00)."""
        if reverb_type is not None:
            self.send_data(add_address(ADDR_PERF_REVERB, REVERB_PARAM_TYPE),
                           [max(0, min(5, int(reverb_type)))])
            self.send_data(ADDR_SETUP_REVERB_SWITCH, [0 if int(reverb_type) == 0 else 1])
        if level is not None:
            self.send_data(add_address(ADDR_PERF_REVERB, REVERB_PARAM_LEVEL),
                           [max(0, min(127, int(level)))])

    def get_perf_mfx_block(self, slot: int, timeout: float = 1.0) -> bytes:
        """Read one raw Performance Common MFX block (145 bytes)."""
        s = self._check_perf_mfx_slot(slot)
        res = self.request_data(perf_common_fx_base(s), PERF_MFX_BLOCK_SIZE, timeout=timeout)
        if res is None or len(res) < 4:
            raise TimeoutError(f"Timed out reading performance MFX{s}.")
        return bytes(res)

    def get_perf_chorus_block(self, timeout: float = 1.0) -> bytes:
        """Read raw Performance Common chorus block (84 bytes)."""
        res = self.request_data(ADDR_PERF_CHORUS, PERF_CHORUS_BLOCK_SIZE, timeout=timeout)
        if res is None or len(res) < 4:
            raise TimeoutError("Timed out reading performance chorus.")
        return bytes(res)

    def get_perf_reverb_block(self, timeout: float = 1.0) -> bytes:
        """Read raw Performance Common reverb block (83 bytes)."""
        res = self.request_data(ADDR_PERF_REVERB, PERF_REVERB_BLOCK_SIZE, timeout=timeout)
        if res is None or len(res) < 2:
            raise TimeoutError("Timed out reading performance reverb.")
        return bytes(res)

    def get_perf_fx(self, timeout: float = 1.0) -> PerfFxState:
        """Read shared Performance FX into PerfFxState (tolerant per-block)."""
        from .patch_state import PatchState as _PS
        fx = PerfFxState()
        try:
            src = self.get_perf_sources(timeout=timeout)
            fx.mfx1.source = int(src.get("mfx1", 0))
            fx.mfx2.source = int(src.get("mfx2", 0))
            fx.mfx3.source = int(src.get("mfx3", 0))
            fx.chorus_source = int(src.get("chorus", 0))
            fx.reverb_source = int(src.get("reverb", 0))
            fx.mfx_structure = int(src.get("structure", 0))
        except Exception as e:
            logger.debug(f"get_perf_fx: sources read failed: {e}")
        for slot, holder in ((1, fx.mfx1), (2, fx.mfx2), (3, fx.mfx3)):
            try:
                blk = self.get_perf_mfx_block(slot, timeout=timeout)
                holder.mfx_type = int(blk[0]) if len(blk) > 0 else 0
                holder.dry_send = int(blk[1]) if len(blk) > 1 else 127
                holder.chorus_send = int(blk[2]) if len(blk) > 2 else 0
                holder.reverb_send = int(blk[3]) if len(blk) > 3 else 0
                try:
                    holder.params = [_PS._param4v(bytes(blk), 0x11 + 4 * i) for i in range(14)] + [0] * 18
                except Exception as e:
                    logger.debug(f"get_perf_fx: param decode failed for slot {slot}: {e}")
            except Exception as e:
                logger.debug(f"get_perf_fx: mfx block read failed for slot {slot}: {e}")
                continue
        try:
            cb = self.get_perf_chorus_block(timeout=timeout)
            c_type, c_lvl, c_out, c_pre, c_rate, c_depth, c_fb = self._decode_chorus_block(bytes(cb))
            fx.chorus_type = c_type
            fx.chorus_level = c_lvl
            fx.chorus_to_reverb = max(0, min(2, c_out))
            fx.chorus_predelay = max(0, min(127, c_pre))
            fx.chorus_rate = max(0, min(127, c_rate))
            fx.chorus_depth = max(0, min(127, c_depth))
            fx.chorus_feedback = max(0, min(127, c_fb))
        except Exception as e:
            logger.debug(f"get_perf_fx: chorus block read failed: {e}")
        try:
            rb = self.get_perf_reverb_block(timeout=timeout)
            r_type, r_lvl, r_pre, r_time, r_damp, r_diff, r_tone = self._decode_reverb_block(bytes(rb))
            fx.reverb_type = r_type
            fx.reverb_level = r_lvl
            fx.reverb_predelay = max(0, min(127, r_pre))
            fx.reverb_time = max(0, min(127, r_time))
            fx.reverb_damp = max(0, min(127, r_damp))
            fx.reverb_diffusion = max(0, min(127, r_diff))
            fx.reverb_tone = max(0, min(127, r_tone))
        except Exception as e:
            logger.debug(f"get_perf_fx: reverb block read failed: {e}")
        return fx

    def _part_patch_fx_base(self, part_index: int, which: str):
        """Base address of a part-patch MFX/chorus/reverb block."""
        part = self._check_part(part_index)
        base = temp_perf_patch_base(part)
        if which == "mfx":
            return add_address(base, OFFSET_PATCH_COMMON_MFX)
        if which == "chorus":
            return add_address(base, OFFSET_PATCH_COMMON_CHORUS)
        if which == "reverb":
            return add_address(base, OFFSET_PATCH_COMMON_REVERB)
        raise ValueError(f"Unknown part-patch FX block '{which}'.")

    def set_part_patch_mfx(self, part_index: int, mfx_type: int | None = None,
                           dry_send: int | None = None,
                           chorus_send: int | None = None,
                           reverb_send: int | None = None) -> None:
        """Write a part-patch MFX type + sends (no perf-common mirror)."""
        base = self._part_patch_fx_base(part_index, "mfx")
        if mfx_type is not None:
            self.send_data(add_address(base, MFX_PARAM_TYPE), [max(0, min(80, int(mfx_type)))])
        if dry_send is not None:
            self.send_data(add_address(base, MFX_PARAM_DRY_SEND), [max(0, min(127, int(dry_send)))])
        if chorus_send is not None:
            self.send_data(add_address(base, MFX_PARAM_CHORUS_SEND), [max(0, min(127, int(chorus_send)))])
        if reverb_send is not None:
            self.send_data(add_address(base, MFX_PARAM_REVERB_SEND), [max(0, min(127, int(reverb_send)))])

    def set_part_patch_mfx_param(self, part_index: int, param_index: int, value: int) -> None:
        """Write one 4-nibble MFX parameter into a part-patch MFX block."""
        if not 0 <= int(param_index) <= 31:
            raise ValueError(f"MFX parameter index must be 0..31, got {param_index}")
        base = self._part_patch_fx_base(part_index, "mfx")
        addr = add_address(base, MFX_PARAM_DATA_START + int(param_index) * 4)
        self.send_data(addr, pack_4nibbles(int(value) + 32768))

    def set_part_patch_chorus(self, part_index: int, chorus_type: int | None = None,
                              level: int | None = None,
                              output_select: int | None = None) -> None:
        """Write a part-patch chorus (no perf-common mirror)."""
        base = self._part_patch_fx_base(part_index, "chorus")
        if chorus_type is not None:
            self.send_data(add_address(base, CHORUS_PARAM_TYPE), [max(0, min(3, int(chorus_type)))])
        if level is not None:
            self.send_data(add_address(base, CHORUS_PARAM_LEVEL), [max(0, min(127, int(level)))])
        if output_select is not None:
            self.send_data(add_address(base, CHORUS_PARAM_OUTPUT_SELECT), [max(0, min(2, int(output_select)))])

    def set_part_patch_chorus_param(self, part_index: int, param: str, val: int) -> None:
        """Write one part-patch chorus detail parameter (rate/depth/preDelay/feedback)."""
        offset_map = {
            "preDelay": CHORUS_PARAM_PREDELAY, "predelay": CHORUS_PARAM_PREDELAY,
            "rate": CHORUS_PARAM_RATE, "depth": CHORUS_PARAM_DEPTH,
            "feedback": CHORUS_PARAM_FEEDBACK,
        }
        if param not in offset_map:
            logger.warning(f"Unknown chorus parameter: {param}")
            return
        base = self._part_patch_fx_base(part_index, "chorus")
        self.send_data(add_address(base, offset_map[param]),
                       pack_4nibbles(max(0, min(127, int(val))) + 32768))

    def set_part_patch_reverb(self, part_index: int, reverb_type: int | None = None,
                              level: int | None = None) -> None:
        """Write a part-patch reverb (no perf-common mirror)."""
        base = self._part_patch_fx_base(part_index, "reverb")
        if reverb_type is not None:
            self.send_data(add_address(base, REVERB_PARAM_TYPE), [max(0, min(5, int(reverb_type)))])
        if level is not None:
            self.send_data(add_address(base, REVERB_PARAM_LEVEL), [max(0, min(127, int(level)))])

    def set_part_patch_reverb_param(self, part_index: int, param: str, val: int) -> None:
        """Write one part-patch reverb detail parameter."""
        offset_map = {
            "preDelay": REVERB_PARAM_PREDELAY, "predelay": REVERB_PARAM_PREDELAY,
            "time": REVERB_PARAM_TIME, "damp": REVERB_PARAM_HF_DAMP,
            "hfDamp": REVERB_PARAM_HF_DAMP, "diffusion": REVERB_PARAM_DIFFUSION,
            "tone": REVERB_PARAM_TONE, "lowCut": REVERB_PARAM_TONE,
        }
        if param not in offset_map:
            logger.warning(f"Unknown reverb parameter: {param}")
            return
        base = self._part_patch_fx_base(part_index, "reverb")
        self.send_data(add_address(base, offset_map[param]),
                       pack_4nibbles(max(0, min(127, int(val))) + 32768))

    def set_perf_chorus_param(self, param: str, val: int) -> None:
        """Write one Performance Common chorus detail parameter (10 00 04 xx)."""
        offset_map = {
            "preDelay": CHORUS_PARAM_PREDELAY, "predelay": CHORUS_PARAM_PREDELAY,
            "rate": CHORUS_PARAM_RATE, "depth": CHORUS_PARAM_DEPTH,
            "feedback": CHORUS_PARAM_FEEDBACK,
        }
        if param not in offset_map:
            logger.warning(f"Unknown chorus parameter: {param}")
            return
        addr = add_address(ADDR_PERF_CHORUS, offset_map[param])
        self.send_data(addr, pack_4nibbles(max(0, min(127, int(val))) + 32768))

    def set_perf_reverb_param(self, param: str, val: int) -> None:
        """Write one Performance Common reverb detail parameter (10 00 06 xx)."""
        offset_map = {
            "preDelay": REVERB_PARAM_PREDELAY, "predelay": REVERB_PARAM_PREDELAY,
            "time": REVERB_PARAM_TIME, "damp": REVERB_PARAM_HF_DAMP,
            "hfDamp": REVERB_PARAM_HF_DAMP, "diffusion": REVERB_PARAM_DIFFUSION,
            "tone": REVERB_PARAM_TONE, "lowCut": REVERB_PARAM_TONE,
        }
        if param not in offset_map:
            logger.warning(f"Unknown reverb parameter: {param}")
            return
        addr = add_address(ADDR_PERF_REVERB, offset_map[param])
        self.send_data(addr, pack_4nibbles(max(0, min(127, int(val))) + 32768))

    def read_part_fx(self, part_index: int, timeout: float = 1.0) -> dict:
        """Read one part-patch MFX + chorus + reverb into decoded dicts.

        Raises TimeoutError when any block is unreadable (caller falls back).
        """
        part = self._check_part(part_index)
        base = temp_perf_patch_base(part)
        mfx_raw = self.request_data(add_address(base, OFFSET_PATCH_COMMON_MFX),
                                    PERF_MFX_BLOCK_SIZE, timeout=timeout)
        if mfx_raw is None or len(mfx_raw) < 4:
            raise TimeoutError(f"Timed out reading part {part} patch MFX.")
        cho_raw = self.request_data(add_address(base, OFFSET_PATCH_COMMON_CHORUS),
                                    PERF_CHORUS_BLOCK_SIZE, timeout=timeout)
        if cho_raw is None or len(cho_raw) < 4:
            raise TimeoutError(f"Timed out reading part {part} patch chorus.")
        rev_raw = self.request_data(add_address(base, OFFSET_PATCH_COMMON_REVERB),
                                    PERF_REVERB_BLOCK_SIZE, timeout=timeout)
        if rev_raw is None or len(rev_raw) < 2:
            raise TimeoutError(f"Timed out reading part {part} patch reverb.")
        m_type, m_dry, m_cho, m_rev, m_params = self._decode_mfx_block(bytes(mfx_raw))
        c_type, c_lvl, c_out, c_pre, c_rate, c_depth, c_fb = self._decode_chorus_block(bytes(cho_raw))
        r_type, r_lvl, r_pre, r_time, r_damp, r_diff, r_tone = self._decode_reverb_block(bytes(rev_raw))
        return {
            "mfx": {"type": m_type, "dry": m_dry, "chorus": m_cho, "reverb": m_rev, "params": m_params},
            "chorus": {"type": c_type, "level": c_lvl, "toReverb": c_out,
                       "predelay": c_pre, "rate": c_rate, "depth": c_depth, "feedback": c_fb},
            "reverb": {"type": r_type, "level": r_lvl, "predelay": r_pre, "time": r_time,
                       "damp": r_damp, "diffusion": r_diff, "tone": r_tone},
        }

    def get_perf_name(self, timeout: float = 1.0) -> str:
        res = self.request_data(add_address(ADDR_TEMP_PERFORMANCE, PERF_COMMON_NAME),
                                (0x00, 0x00, 0x00, PERF_COMMON_NAME_SIZE), timeout=timeout)
        if res is None:
            raise TimeoutError("Timed out reading performance name.")
        return bytes(res[:PERF_COMMON_NAME_SIZE]).decode("latin1", errors="replace").strip()

    def get_perf_part_patch_name(self, part_index: int, timeout: float = 0.5) -> str:
        """Read 12 ASCII character patch name from the temporary patch buffer of part 1..16."""
        part = self._check_part(part_index)
        base = temp_perf_patch_base(part)
        name_addr = add_address(base, PATCH_PARAM_NAME)
        res = self.request_data(name_addr, (0x00, 0x00, 0x00, 0x0C), timeout=timeout)
        if res is not None and len(res) >= 12:
            return bytes(res[:12]).decode("latin1", errors="replace").strip()
        return ""

    def get_perf_part_block(self, part_index: int, timeout: float = 1.0) -> bytes:
        part = self._check_part(part_index)
        res = self.request_data(perf_part_base(part), self._rq_size(PERF_PART_BLOCK_SIZE),
                                timeout=timeout)
        if res is None or len(res) < PERF_PART_BLOCK_SIZE:
            raise TimeoutError(f"Timed out reading performance part {part}.")
        return bytes(res[:PERF_PART_BLOCK_SIZE])

    def get_perf_parts(self, timeout: float = 1.0) -> list[PerfPartState]:
        """Read all 16 performance part mixer blocks into PerfPartState list."""
        solo_raw = self.request_data(add_address(ADDR_TEMP_PERFORMANCE, PERF_COMMON_SOLO_PART),
                                     (0x00, 0x00, 0x00, 0x01), timeout=timeout)
        solo_sel = int(solo_raw[0]) if solo_raw else 0
        parts: list[PerfPartState] = []
        for part in range(1, 17):
            try:
                blk = self.get_perf_part_block(part, timeout=timeout)
                state = PerfPartState(
                    part_index=part,
                    name=f"Part {part}",
                    volume=int(blk[PERF_PART_LEVEL]),
                    pan=int(blk[PERF_PART_PAN]),
                    muted=bool(blk[PERF_PART_MUTE]),
                    solo=(solo_sel == part),
                    patch_msb=int(blk[PERF_PART_PATCH_MSB]),
                    patch_lsb=int(blk[PERF_PART_PATCH_LSB]),
                    patch_pc=int(blk[PERF_PART_PATCH_PC]),
                    rx_channel=int(blk[PERF_PART_RX_CHANNEL]) & 0x0F,
                    rx_switch=bool(blk[PERF_PART_RX_SWITCH]),
                    coarse_tune=int(blk[PERF_PART_COARSE_TUNE]),
                    fine_tune=int(blk[PERF_PART_FINE_TUNE]),
                    octave_shift=int(blk[PERF_PART_OCTAVE_SHIFT]),
                    dry_send=int(blk[PERF_PART_DRY_SEND]),
                    chorus_send=int(blk[PERF_PART_CHORUS_SEND]),
                    reverb_send=int(blk[PERF_PART_REVERB_SEND]),
                    output_assign=max(0, min(13, int(blk[PERF_PART_OUTPUT_ASSIGN]))),
                    mfx_select=max(0, min(2, int(blk[PERF_PART_OUTPUT_MFX_SELECT]))),
                )
            except Exception as e:
                logger.debug(f"get_perf_parts: part {part} read failed: {e}")
                state = PerfPartState(part_index=part, name=f"Part {part}")
            parts.append(state)
        try:
            zones = self.get_perf_zones(timeout=timeout)
            for part_st, zone in zip(parts, zones):
                part_st.key_low = zone["low"]
                part_st.key_high = zone["high"]
                part_st.zone_switch = zone["switch"]
                part_st.zone_octave = zone["octave"]
        except Exception as e:
            logger.debug(f"get_perf_parts: zone read failed: {e}")
        return parts

    @staticmethod
    def _check_channel(channel: int) -> int:
        ch = int(channel)
        if not 1 <= ch <= 16:
            raise ValueError(f"Performance zone channel must be 1..16, got {channel}")
        return ch

    def set_perf_zone(self, channel: int, key_low: int | None = None,
                      key_high: int | None = None, switch: bool | None = None,
                      octave: int | None = None) -> None:
        """Write a Performance Zone block (10 00 (0x50+ch-1) 00, 0x1B bytes).

        Low/high are ordered automatically (swapped when inverted).
        Octave is 61..67 (-3..+3, 64 = 0).
        """
        ch = self._check_channel(channel)
        base = perf_zone_base(ch)
        if key_low is not None or key_high is not None:
            cur_lo, cur_hi = None, None
            if key_low is None or key_high is None:
                try:
                    blk = self.get_perf_zone_block(ch)
                    cur_lo, cur_hi = int(blk[PERF_ZONE_KEY_LOW]), int(blk[PERF_ZONE_KEY_HIGH])
                except Exception as e:
                    logger.debug(f"set_perf_zone: read zone block failed for ch {ch}: {e}")
                    cur_lo, cur_hi = 0, 127
            lo = max(0, min(127, int(key_low))) if key_low is not None else cur_lo
            hi = max(0, min(127, int(key_high))) if key_high is not None else cur_hi
            lo, hi = min(lo, hi), max(lo, hi)
            self.send_data(add_address(base, PERF_ZONE_KEY_LOW), [lo, hi])
        if switch is not None:
            self.send_data(add_address(base, PERF_ZONE_SWITCH), [1 if switch else 0])
        if octave is not None:
            self.send_data(add_address(base, PERF_ZONE_OCTAVE_SHIFT),
                           [max(61, min(67, int(octave)))])

    def set_perf_zone_switch(self, channel: int, enabled: bool) -> None:
        """Fast single-byte DT1 write to Performance Zone Switch (0=OFF, 1=ON).

        Used for dynamic keyboard routing arbitration: silences physical keybed input
        for sequenced backing parts while allowing external USB-MIDI to trigger sound.
        """
        ch = self._check_channel(channel)
        base = perf_zone_base(ch)
        self.send_data(add_address(base, PERF_ZONE_SWITCH), [1 if enabled else 0])

    def get_perf_zone_block(self, channel: int, timeout: float = 1.0) -> bytes:
        """Read one raw 0x1B Performance Zone block."""
        ch = self._check_channel(channel)
        res = self.request_data(perf_zone_base(ch), self._rq_size(PERF_ZONE_BLOCK_SIZE),
                                timeout=timeout)
        if res is None or len(res) < PERF_ZONE_BLOCK_SIZE:
            raise TimeoutError(f"Timed out reading performance zone {ch}.")
        return bytes(res[:PERF_ZONE_BLOCK_SIZE])

    def get_perf_zones(self, timeout: float = 1.0) -> list[dict]:
        """Read all 16 zone blocks as {low, high, switch, octave} dicts."""
        zones = []
        for ch in range(1, 17):
            try:
                blk = self.get_perf_zone_block(ch, timeout=timeout)
                zones.append({
                    "low": int(blk[PERF_ZONE_KEY_LOW]),
                    "high": int(blk[PERF_ZONE_KEY_HIGH]),
                    "switch": bool(blk[PERF_ZONE_SWITCH]),
                    "octave": max(61, min(67, int(blk[PERF_ZONE_OCTAVE_SHIFT]))),
                })
            except Exception as e:
                logger.debug(f"get_perf_zones: read zone failed for ch {ch}: {e}")
                zones.append({"low": 0, "high": 127, "switch": True, "octave": 64})
        return zones

    def push_patch_to_perf_part(self, state: PatchState, part_index: int,
                                write_gap: float = 0.02) -> int:
        """DT1-push a Pi-only patch image into a Performance Part temp buffer.

        Accepts the large transfer (~10 DT1 messages per part) so performances
        can sound Pi-only files without requiring hardware slots. Returns
        DT1 send failures (0 = ok). No flash writes, no verification reads.
        """
        part = self._check_part(part_index)
        with self.quiet_part_writes():
            return self.write_patch_regions(state, temp_perf_patch_base(part),
                                             write_gap=write_gap)

    def read_perf_part_patch(self, part_index: int, timeout: float = 1.5) -> PatchState:
        """Read a part's sounding image from its temp buffer (no part switch)."""
        part = self._check_part(part_index)
        return self.read_patch_at(temp_perf_patch_base(part), f"Part {part}", timeout=timeout)

    # ------------------------------------------------------------------
    # User performances (MSB 85 LSB 0, 001..128) at 20 nn 00 00: same block
    # layout as the temporary performance (MIDI Implementation p.19), so a
    # save copies the sounding performance block by block. Part blocks only
    # reference patches by Bank/PC: Pi-only part images are not carried.
    # ------------------------------------------------------------------

    USER_PERF_MSB = 85
    USER_PERF_LSB = 0

    #: (offset, size) of every block in a performance (MIDI Implementation p.20-27).
    PERF_BLOCKS = (
        [((0x00, 0x00, 0x00, 0x00), 0x38),    # Common
         ((0x00, 0x00, 0x02, 0x00), 0x91),    # MFX1
         ((0x00, 0x00, 0x04, 0x00), 0x54),    # Chorus
         ((0x00, 0x00, 0x06, 0x00), 0x53),    # Reverb
         ((0x00, 0x00, 0x08, 0x00), 0x91),    # MFX2
         ((0x00, 0x00, 0x0A, 0x00), 0x91)]    # MFX3
        + [((0x00, 0x00, 0x10 + ch, 0x00), 0x0C) for ch in range(16)]  # MIDI
        + [((0x00, 0x00, 0x20 + pt, 0x00), 0x31) for pt in range(16)]  # Part
        + [((0x00, 0x00, 0x50 + ch, 0x00), 0x1B) for ch in range(16)]  # Zone
        + [((0x00, 0x00, 0x60, 0x00), 0x5A)]  # Controller
    )

    @staticmethod
    def user_perf_base(number: int) -> tuple:
        """Base address of user performance 1..128."""
        n = int(number)
        if not 1 <= n <= 128:
            raise ValueError(f"User performance must be 1..128, got {number}")
        return (0x20, n - 1, 0x00, 0x00)

    def read_performance_image(self, base=ADDR_TEMP_PERFORMANCE,
                               timeout: float = 1.0) -> list:
        """Read every block of a performance as [(offset, bytes)]."""
        image = []
        for offset, size in self.PERF_BLOCKS:
            res = self.request_data(add_address(base, offset), self._rq_size(size), timeout=timeout)
            if res is None or len(res) < size:
                raise TimeoutError(f"Timed out reading performance block {offset[2]:02X}.")
            image.append((offset, bytes(res[:size])))
        return image

    def encode_performance_sysex(self, image: list, base) -> bytes:
        """Encode a performance image as .syx DT1 messages (slot backups)."""
        blob = bytearray()
        for offset, data in image:
            blob += bytes([0xF0] + self.sysex.build_dt1(add_address(base, offset), data) + [0xF7])
        return bytes(blob)

    def read_user_perf_name(self, number: int, timeout: float = 1.0) -> str:
        res = self.request_data(add_address(self.user_perf_base(number), PERF_COMMON_NAME),
                                (0x00, 0x00, 0x00, PERF_COMMON_NAME_SIZE), timeout=timeout)
        if res is None or len(res) < PERF_COMMON_NAME_SIZE:
            raise TimeoutError(f"Timed out reading user performance {number} name.")
        return bytes(res[:PERF_COMMON_NAME_SIZE]).decode("latin1", errors="replace").strip()

    def write_user_performance(self, number: int, name: str, timeout: float = 1.5,
                               write_gap: float = 0.02, retries: int = 3) -> list[str]:
        """Copy the sounding (temporary) performance into user performance 1..128.

        Returns mismatch labels ([] = stored + verified).
        """
        base = self.user_perf_base(number)
        image = self.read_performance_image(timeout=timeout)
        common = bytearray(image[0][1])
        common[0:PERF_COMMON_NAME_SIZE] = (
            str(name).encode("ascii", errors="replace")[:PERF_COMMON_NAME_SIZE]
            .ljust(PERF_COMMON_NAME_SIZE, b" "))
        image[0] = (image[0][0], bytes(common))
        failures = 0
        with self.paced_init_writes(write_gap):
            for offset, data in image:
                try:
                    self.send_data(add_address(base, offset), data)
                except Exception as e:
                    failures += 1
                    logger.warning(f"User performance write failed at {offset}: {e}")
        if failures:
            return [f"{failures} DT1 send failures"]
        time.sleep(self.FLASH_SETTLE_S)
        last_err = ""
        for _ in range(max(1, retries)):
            try:
                actual = self.read_performance_image(base, timeout=timeout)
                break
            except Exception as e:
                last_err = str(e)
                time.sleep(0.4)
        else:
            return [f"unreadable after write: {last_err}"]
        return [f"block {off[2]:02X}" for (off, want), (_, got) in zip(image, actual) if want != got]
