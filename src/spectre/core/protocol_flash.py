"""User flash slots, SysEx blobs, and initialization protocol mixin for Roland JUNO-DS / XPS-30."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from .patch_state import (
    TEMPLATE_ASSET_PATH,
    EffectsState,
    PatchCommonState,
    PatchState,
    StepLfoState,
    ToneState,
)
from .protocol_base import (
    INIT_MAX_VERIFY_REPAIRS,
    INIT_WRITE_GAP_S,
    InitVerification,
    InitWriteMismatch,
)
from .sysex import (
    ADDR_SETUP_CHORUS_SWITCH,
    ADDR_SETUP_REVERB_SWITCH,
    CHORUS_PARAM_LEVEL,
    CHORUS_PARAM_OUTPUT_SELECT,
    CHORUS_PARAM_TYPE,
    OFFSET_PATCH_COMMON,
    OFFSET_PATCH_COMMON_CHORUS,
    OFFSET_PATCH_COMMON_MFX,
    OFFSET_PATCH_COMMON_REVERB,
    OFFSET_PATCH_TMT,
    OFFSET_PATCH_TONE_1,
    OFFSET_PATCH_TONE_2,
    OFFSET_PATCH_TONE_3,
    OFFSET_PATCH_TONE_4,
    PATCH_PARAM_NAME,
    REVERB_PARAM_LEVEL,
    REVERB_PARAM_TYPE,
    TMT_PARAM_TONE1_SWITCH,
    TMT_PARAM_TONE2_SWITCH,
    TMT_PARAM_TONE3_SWITCH,
    TMT_PARAM_TONE4_SWITCH,
    TONE_PARAM_WAVE_GROUP_TYPE,
    RolandSysEx,
    add_address,
    pack_4nibbles,
    unpack_4nibbles,
)

logger = logging.getLogger(__name__)


class FlashProtocolMixin:
    """User flash slots, batch region transfers, SysEx blob parsing, and template init."""

    # ------------------------------------------------------------------
    # User flash slots (writable): MSB 87 LSB 0..1 -> 256 patches 501..756.
    # Same region layout as the temp buffer, so the canonical raw image
    # (PatchState.raw_regions) round-trips verbatim. Flash needs settle
    # time after writes: verification reads retry (see Phase-0 findings).
    # ------------------------------------------------------------------

    USER_SLOT_MSB = 87
    USER_SLOT_LSBS = (0, 1)

    #: raw_regions key -> patch offset (mirrors the init-template layout).
    USER_REGION_OFFSETS = {
        "common": OFFSET_PATCH_COMMON,
        "mfx": OFFSET_PATCH_COMMON_MFX,
        "chorus": OFFSET_PATCH_COMMON_CHORUS,
        "reverb": OFFSET_PATCH_COMMON_REVERB,
        "tmt": OFFSET_PATCH_TMT,
        "tone_1": OFFSET_PATCH_TONE_1,
        "tone_2": OFFSET_PATCH_TONE_2,
        "tone_3": OFFSET_PATCH_TONE_3,
        "tone_4": OFFSET_PATCH_TONE_4,
    }

    #: Chunk start offsets inside tone_N regions (154B main + 26B LFO2/step).
    TONE_CHUNK_STARTS = (0x0000, 0x0100)

    #: Post-write settle before flash read-back (seconds).
    FLASH_SETTLE_S = 0.6

    @classmethod
    def user_slot_base(cls, msb: int, lsb: int, pc: int) -> Tuple[int, int, int, int]:
        """Absolute base address of a writable user patch slot."""
        if int(msb) != cls.USER_SLOT_MSB or int(lsb) not in cls.USER_SLOT_LSBS:
            raise ValueError(
                f"User patch slots are MSB 87 LSB 0..1, got {msb}/{lsb}")
        if not 0 <= int(pc) <= 127:
            raise ValueError(f"PC must be 0..127, got {pc}")
        return (0x30 if int(lsb) == 0 else 0x31, int(pc), 0x00, 0x00)

    @staticmethod
    def _assemble_patch_state(
        raw_regions: dict[str, list[bytes]],
        common: "PatchCommonState",
        tones: list["ToneState"],
        mfx: Tuple[int, int, int, int, list[int]],
        chorus: Tuple[int, int, int, int, int, int, int],
        reverb: Tuple[int, int, int, int, int, int, int],
        mode_name: str,
    ) -> "PatchState":
        """Build a PatchState from gathered region bytes + decoded pieces.

        Shared by read_full_patch (temp RAM) and read_user_patch (flash) so
        both paths provably converge on the same decode.
        """
        mfx_type, dry, cho, rev, mfx_params = mfx
        c_type, c_lvl, c_out, c_pre, c_rate, c_dep, c_fb = chorus
        r_type, r_lvl, r_pre, r_time, r_damp, r_diff, r_tone = reverb
        effects = EffectsState(
            mfx_type=mfx_type,
            mfx_dry_send=dry,
            mfx_chorus_send=cho,
            mfx_reverb_send=rev,
            mfx_bypassed=(mfx_type == 0),
            mfx_last_active_type=mfx_type if mfx_type != 0 else 15,
            mfx_params=list(mfx_params) + [0] * (32 - len(mfx_params))
            if len(mfx_params) < 32
            else list(mfx_params[:32]),
            routing_preset="",
            manual_routing_unlocked=False,
            chorus_type=c_type,
            chorus_level=c_lvl,
            chorus_to_reverb=c_out,
            chorus_predelay=c_pre,
            chorus_rate=c_rate,
            chorus_depth=c_dep,
            chorus_feedback=c_fb,
            reverb_type=r_type,
            reverb_level=r_lvl,
            reverb_predelay=r_pre,
            reverb_time=r_time,
            reverb_damp=r_damp,
            reverb_diffusion=r_diff,
            reverb_tone=r_tone,
        )
        patch_state = PatchState(
            sound_mode=mode_name,
            common=common,
            tones=tones,
            effects=effects,
            raw_regions={k: [bytes(c) for c in v] for k, v in raw_regions.items()},
        )
        patch_state.step_lfo = StepLfoState(
            steps=[0] * 16,
            curve_type=0,
            sync_rate_idx=2,
            dest_idx=1,
            depth=0,
        )
        patch_state.custom_detune_cache = [t.fine_tune for t in tones]
        return patch_state

    def _read_patch_regions(self, base: Tuple[int, int, int, int],
                            timeout: float = 1.0) -> dict[str, list[bytes]]:
        """Gather the canonical raw image at any patch base (temp or flash)."""
        raw_regions: dict[str, list[bytes]] = {}
        raw_regions["common"] = [bytes(self._read_common_raw(base, timeout=timeout)[:80])]
        tone_offsets = (OFFSET_PATCH_TONE_1, OFFSET_PATCH_TONE_2,
                        OFFSET_PATCH_TONE_3, OFFSET_PATCH_TONE_4)
        for idx, off in enumerate(tone_offsets, start=1):
            main_raw, lfo_raw = self._read_tone_raws(add_address(base, off), timeout=timeout)
            raw_regions[f"tone_{idx}"] = [bytes(main_raw)] + (
                [bytes(lfo_raw)] if lfo_raw is not None else []
            )
        raw_regions["tmt"] = [bytes(self._read_tmt_raw(base, timeout=timeout))]
        raw_regions["mfx"] = [bytes(self._read_mfx_raw(base, timeout=timeout))]
        raw_regions["chorus"] = [bytes(self._read_chorus_raw(base, timeout=timeout))]
        raw_regions["reverb"] = [bytes(self._read_reverb_raw(base, timeout=timeout))]
        return raw_regions

    def read_user_patch(self, msb: int, lsb: int, pc: int,
                        timeout: float = 1.5) -> PatchState:
        """Read a full PatchState from a user flash slot (backup path).

        Strict canonical decode (no legacy fallback): raises TimeoutError or
        ValueError on short/corrupt replies.
        """
        return self.read_patch_at(self.user_slot_base(msb, lsb, pc),
                                  f"User slot {msb}/{lsb}/{pc}", timeout=timeout)

    def read_patch_at(self, base: Tuple[int, int, int, int], label: str,
                      timeout: float = 1.5) -> PatchState:
        """Read and strictly decode the patch image at any base (temp or flash)."""
        raw_regions = self._read_patch_regions(base, timeout=timeout)
        common = PatchState._decode_common(bytes(raw_regions["common"][0][:80]))
        tones = []
        for idx in range(1, 5):
            main_raw, lfo_raw = raw_regions[f"tone_{idx}"][0], raw_regions[f"tone_{idx}"][1]
            if len(main_raw) < 154 or len(lfo_raw) < 26:
                raise ValueError(f"{label} tone {idx}: short image")
            tones.append(PatchState._decode_tone(bytes(main_raw[:154]), bytes(lfo_raw[:26]), idx))
        tmt_raw = raw_regions["tmt"][0]
        for tone, sw in zip(tones, (
            tmt_raw[TMT_PARAM_TONE1_SWITCH], tmt_raw[TMT_PARAM_TONE2_SWITCH],
            tmt_raw[TMT_PARAM_TONE3_SWITCH], tmt_raw[TMT_PARAM_TONE4_SWITCH],
        )):
            tone.muted = (sw == 0)
        mfx_raw = raw_regions["mfx"][0]
        mfx_params = [0] * 32
        if len(mfx_raw) >= 0x11 + 4:
            for i in range(min(32, (len(mfx_raw) - 0x11) // 4)):
                mfx_params[i] = unpack_4nibbles(mfx_raw[0x11 + i * 4:0x11 + (i + 1) * 4]) - 32768
        mfx = (mfx_raw[0], mfx_raw[1], mfx_raw[2], mfx_raw[3], mfx_params)
        cho_raw = raw_regions["chorus"][0]
        chorus = (
            cho_raw[0], cho_raw[1], cho_raw[3],
            max(0, unpack_4nibbles(cho_raw[0x0C:0x10]) - 32768),
            max(0, unpack_4nibbles(cho_raw[0x14:0x18]) - 32768),
            max(0, unpack_4nibbles(cho_raw[0x1C:0x20]) - 32768),
            max(0, unpack_4nibbles(cho_raw[0x24:0x28]) - 32768),
        )
        rev_raw = raw_regions["reverb"][0]
        reverb = (
            rev_raw[0], rev_raw[1],
            max(0, unpack_4nibbles(rev_raw[0x03:0x07]) - 32768),
            max(0, unpack_4nibbles(rev_raw[0x07:0x0B]) - 32768),
            max(0, unpack_4nibbles(rev_raw[0x0F:0x13]) - 32768),
            max(0, unpack_4nibbles(rev_raw[0x17:0x1B]) - 32768),
            max(0, unpack_4nibbles(rev_raw[0x1B:0x1F]) - 32768),
        )
        return self._assemble_patch_state(raw_regions, common, tones, mfx, chorus, reverb, "PATCH")

    def write_patch_regions(self, state: PatchState,
                             base: Tuple[int, int, int, int],
                             write_gap: float = 0.02) -> int:
        """DT1-push a PatchState raw image to any patch base. Returns failures."""
        if not state.raw_regions:
            raise ValueError("No raw image: sync/read the patch first.")
        failures = 0
        common = bytearray(state.raw_regions["common"][0][:80])
        raw_name = state.common.name.encode("ascii", errors="replace")[:12].ljust(12, b" ")
        common[0:12] = raw_name  # name travels in the image, not beside it
        with self.paced_init_writes(write_gap):
            try:
                self.send_data(add_address(base, self.USER_REGION_OFFSETS["common"]), bytes(common))
            except Exception as e:
                failures += 1
                logger.warning(f"User write failed for common: {e}")
            for key in ("mfx", "chorus", "reverb", "tmt"):
                for chunk in state.raw_regions.get(key, []):
                    try:
                        self.send_data(add_address(base, self.USER_REGION_OFFSETS[key]), bytes(chunk))
                    except Exception as e:
                        failures += 1
                        logger.warning(f"User write failed for {key}: {e}")
            for idx in range(1, 5):
                chunks = state.raw_regions.get(f"tone_{idx}", [])
                for chunk, start in zip(chunks, self.TONE_CHUNK_STARTS):
                    try:
                        self.send_data(
                            add_address(add_address(base, self.USER_REGION_OFFSETS[f"tone_{idx}"]), start),
                            bytes(chunk),
                        )
                    except Exception as e:
                        failures += 1
                        logger.warning(f"User write failed for tone_{idx}@0x{start:03X}: {e}")
        return failures

    _write_patch_regions = write_patch_regions

    @staticmethod
    def patch_image_mismatches(state: PatchState, actual: dict) -> list[str]:
        """Compare a PatchState image with raw regions read back. [] = same sound."""
        mismatches: list[str] = []
        common = bytearray(state.raw_regions["common"][0][:80])
        raw_name = state.common.name.encode("ascii", errors="replace")[:12].ljust(12, b" ")
        common[0:12] = raw_name
        if bytes(actual.get("common", [b""])[0][:80]) != bytes(common):
            mismatches.append("common")
        for key in ("mfx", "chorus", "reverb", "tmt"):
            for i, chunk in enumerate(state.raw_regions.get(key, [])):
                got = actual.get(key, [])
                if i >= len(got) or bytes(got[i]) != bytes(chunk):
                    mismatches.append(f"{key}[{i}]")
        for idx in range(1, 5):
            for i, chunk in enumerate(state.raw_regions.get(f"tone_{idx}", [])):
                got = actual.get(f"tone_{idx}", [])
                if i >= len(got) or bytes(got[i]) != bytes(chunk):
                    mismatches.append(f"tone_{idx}[{i}]")
        return mismatches

    def verify_patch_regions(self, state: PatchState,
                              base: Tuple[int, int, int, int],
                              timeout: float = 1.5, retries: int = 3) -> list[str]:
        """Re-read a written image and compare. Returns mismatch labels ([] = ok).

        Flash needs settle time after writes: waits FLASH_SETTLE_S, then
        retries the whole read before declaring failure (Phase-0 finding).
        """
        time.sleep(self.FLASH_SETTLE_S)
        last_err: Optional[str] = None
        for _ in range(max(1, retries)):
            try:
                actual = self._read_patch_regions(base, timeout=timeout)
                break
            except Exception as e:
                last_err = str(e)
                time.sleep(0.4)
        else:
            return [f"unreadable after write: {last_err}"]
        return self.patch_image_mismatches(state, actual)

    _verify_patch_regions = verify_patch_regions

    def restore_temp_patch(self, state: PatchState,
                           base: Optional[Tuple[int, int, int, int]] = None,
                           timeout: float = 1.5) -> Tuple[int, list[str]]:
        """Restore a patch state to temporary buffer and verify. Returns (write_failures, mismatches)."""
        target_base = base or self.get_active_patch_base(timeout=1.0)
        write_fails = self.write_patch_regions(state, target_base)
        mismatches = self.verify_patch_regions(state, target_base, timeout=timeout)
        return write_fails, mismatches

    def write_user_patch(self, state: PatchState, msb: int, lsb: int, pc: int,
                         timeout: float = 1.5, write_gap: float = 0.02,
                         verify: bool = True) -> list[str]:
        """Copy a PatchState image into a user flash slot.

        Returns mismatch labels ([] = stored + verified). Temp buffer untouched.
        Raises ValueError for bad slots or imageless states.
        """
        base = self.user_slot_base(msb, lsb, pc)
        failures = self.write_patch_regions(state, base, write_gap=write_gap)
        if failures:
            return [f"{failures} DT1 send failures"]
        if verify:
            return self.verify_patch_regions(state, base, timeout=timeout)
        time.sleep(self.FLASH_SETTLE_S)
        return []

    def rename_user_slot(self, msb: int, lsb: int, pc: int, name: str,
                         timeout: float = 1.5, retries: int = 3) -> bool:
        """Rename a user flash slot (name-only DT1 + verified read-back)."""
        base = self.user_slot_base(msb, lsb, pc)
        raw_name = name.encode("ascii", errors="replace")[:12].ljust(12, b" ")
        self.send_data(add_address(base, PATCH_PARAM_NAME), list(raw_name))
        time.sleep(self.FLASH_SETTLE_S)
        want = bytes(raw_name)
        for _ in range(max(1, retries)):
            try:
                raw = self.request_data(
                    add_address(base, PATCH_PARAM_NAME), (0x00, 0x00, 0x00, 0x0C),
                    timeout=timeout,
                )
                if raw is not None and bytes(raw[:12]) == want:
                    return True
            except Exception as e:
                logger.debug(f"rename verify retry: {e}")
            time.sleep(0.4)
        return False

    # ------------------------------------------------------------------
    # .syx bulk files: DT1 sequences restoring a raw patch image.
    # Export reads nothing new (uses the raw image); import retargets the
    # file's patch base onto the live temp base so files recorded in Patch
    # mode also apply inside Performance parts.
    # ------------------------------------------------------------------

    def encode_patch_sysex(self, state: PatchState,
                           base: Optional[Tuple[int, int, int, int]] = None,
                           timeout: float = 1.0) -> bytes:
        """Encode a PatchState raw image as .syx bytes (F0..F7 DT1 messages)."""
        if not state.raw_regions:
            raise ValueError("No raw image: sync/read the patch first.")
        resolved = base if base is not None else self.get_active_patch_base(timeout=timeout)
        common = bytearray(state.raw_regions["common"][0][:80])
        raw_name = state.common.name.encode("ascii", errors="replace")[:12].ljust(12, b" ")
        common[0:12] = raw_name
        blob = bytearray()
        blob += bytes([0xF0] + self.sysex.build_dt1(
            add_address(resolved, self.USER_REGION_OFFSETS["common"]), bytes(common)) + [0xF7])
        for key in ("mfx", "chorus", "reverb", "tmt"):
            for chunk in state.raw_regions.get(key, []):
                blob += bytes([0xF0] + self.sysex.build_dt1(
                    add_address(resolved, self.USER_REGION_OFFSETS[key]), bytes(chunk)) + [0xF7])
        for idx in range(1, 5):
            for chunk, start in zip(state.raw_regions.get(f"tone_{idx}", []),
                                    self.TONE_CHUNK_STARTS):
                blob += bytes([0xF0] + self.sysex.build_dt1(
                    add_address(add_address(resolved, self.USER_REGION_OFFSETS[f"tone_{idx}"]),
                                start), bytes(chunk)) + [0xF7])
        return bytes(blob)

    @staticmethod
    def split_sysex_blob(blob: bytes) -> list[bytes]:
        """Split raw .syx bytes into individual F0..F7 messages."""
        messages: list[bytes] = []
        start: Optional[int] = None
        for i, byte in enumerate(blob):
            if byte == 0xF0:
                start = i
            elif byte == 0xF7 and start is not None:
                messages.append(bytes(blob[start:i + 1]))
                start = None
        return messages

    def apply_sysex_blob(self, blob: bytes,
                         base: Optional[Tuple[int, int, int, int]] = None,
                         timeout: float = 1.0, write_gap: float = 0.02) -> int:
        """Push a .syx DT1 blob into the live temp buffer. Returns messages applied.

        Only Roland DT1 messages with valid checksums are honored; anything
        else is skipped. Addresses are rebased onto the live temp base (high
        two bytes replaced), so Patch-mode captures apply in Performance mode.
        """
        from .sysex import CMD_DT1

        resolved = base if base is not None else self.get_active_patch_base(timeout=timeout)
        applied = 0
        with self.paced_init_writes(write_gap):
            for message in self.split_sysex_blob(bytes(blob)):
                parsed = RolandSysEx.parse(message)
                if (parsed is None or not parsed.is_valid_checksum
                        or parsed.command != CMD_DT1 or len(parsed.payload) == 0):
                    continue
                addr = (resolved[0], resolved[1], parsed.address[2], parsed.address[3])
                self.send_data(addr, parsed.payload)
                applied += 1
        return applied

    @staticmethod
    def load_init_template() -> Optional[dict]:
        """Read the golden init template captured by tools/capture_init_template.py."""
        import sys
        proto = sys.modules.get("src.spectre.core.protocol") or sys.modules.get("spectre.core.protocol")
        asset_path = getattr(proto, "TEMPLATE_ASSET_PATH", TEMPLATE_ASSET_PATH) if proto else TEMPLATE_ASSET_PATH
        try:
            payload = json.loads(Path(asset_path).read_text(encoding="utf-8"))
            if payload.get("version") != 1 or "regions" not in payload:
                return None
            return payload
        except (OSError, ValueError):
            return None

    @staticmethod
    def _expected_template_writes(
        payload: dict, base: Tuple[int, int, int, int]
    ) -> List[Tuple[str, Tuple[int, int, int, int], bytes]]:
        """Expand a golden template payload into absolute address expectations."""
        writes: List[Tuple[str, Tuple[int, int, int, int], bytes]] = []
        chorus_type = 0
        reverb_type = 0
        for key, region in payload["regions"].items():
            region_addr = add_address(base, tuple(region["offset"]))
            for chunk in region["chunks"]:
                start = int(chunk["start"])
                expected = bytes(chunk["bytes"])
                writes.append(
                    (f"{key}@0x{start:03X}", add_address(region_addr, start), expected)
                )
            if key == "chorus" and region["chunks"]:
                chorus_type = int(region["chunks"][0]["bytes"][0])
            if key == "reverb" and region["chunks"]:
                reverb_type = int(region["chunks"][0]["bytes"][0])

        # Mirror the Setup global FX switches to the image's chorus/reverb types
        # (same behavior as selecting the patch on the keyboard).
        writes.append(
            ("setup_chorus_switch", tuple(ADDR_SETUP_CHORUS_SWITCH), bytes([0 if chorus_type == 0 else 1]))
        )
        writes.append(
            ("setup_reverb_switch", tuple(ADDR_SETUP_REVERB_SWITCH), bytes([0 if reverb_type == 0 else 1]))
        )
        return writes

    def _read_write_mismatches(
        self,
        expected_writes: Sequence[Tuple[str, Tuple[int, int, int, int], bytes] | InitWriteMismatch],
        timeout: float,
    ) -> List[InitWriteMismatch]:
        """Read back expected addresses and report byte-level differences."""
        mismatches: List[InitWriteMismatch] = []
        for item in expected_writes:
            if isinstance(item, InitWriteMismatch):
                label, address, expected = item.label, item.address, item.expected
            else:
                label, address, expected = item
            try:
                actual = self.request_data(address, self._rq_size(len(expected)), timeout=timeout)
            except Exception as e:
                logger.warning(f"Init verification read failed for {label}: {e}")
                actual = None
            actual_bytes = None if actual is None else bytes(actual)
            if actual_bytes != bytes(expected):
                mismatches.append(
                    InitWriteMismatch(
                        label=label,
                        address=tuple(address),
                        expected=bytes(expected),
                        actual=actual_bytes,
                    )
                )
        return mismatches

    def verify_writes(
        self,
        expected_writes: Sequence[Tuple[str, Tuple[int, int, int, int], bytes]],
        timeout: float = 1.0,
        repair: bool = True,
        max_repair_rounds: int = INIT_MAX_VERIFY_REPAIRS,
        write_gap: float = INIT_WRITE_GAP_S,
    ) -> InitVerification:
        """Verify expected writes and selectively rewrite only mismatched chunks."""
        result = InitVerification()
        remaining = list(expected_writes)
        for attempt in range(max(0, int(max_repair_rounds)) + 1):
            mismatches = self._read_write_mismatches(remaining, timeout)
            seen = {m.label for m in result.detected}
            result.detected.extend([m for m in mismatches if m.label not in seen])
            if not mismatches or not repair or attempt >= max(0, int(max_repair_rounds)):
                result.failed.extend(mismatches)
                break
            with self.paced_init_writes(write_gap):
                for mismatch in mismatches:
                    try:
                        self.send_data(mismatch.address, mismatch.expected)
                    except Exception as e:
                        logger.warning(f"Init repair write failed for {mismatch.label}: {e}")
            result.repaired.extend(mismatches)
            remaining = mismatches
        if result.failed:
            labels = ", ".join(m.label for m in result.failed)
            logger.warning(f"Init verification failed for: {labels}")
        elif result.repaired:
            labels = ", ".join(m.label for m in result.repaired)
            logger.info(f"Init verification repaired: {labels}")
        return result

    def verify_init_template(
        self,
        payload: dict,
        base: Optional[Tuple[int, int, int, int]] = None,
        timeout: float = 1.0,
        repair: bool = True,
        max_repair_rounds: int = INIT_MAX_VERIFY_REPAIRS,
        write_gap: float = INIT_WRITE_GAP_S,
    ) -> InitVerification:
        """Verify a golden template payload byte-for-byte, repairing mismatches."""
        resolved_base = base if base is not None else self.get_active_patch_base(
            timeout=timeout, force_refresh=True
        )
        expected = self._expected_template_writes(payload, resolved_base)
        return self.verify_writes(
            expected,
            timeout=timeout,
            repair=repair,
            max_repair_rounds=max_repair_rounds,
            write_gap=write_gap,
        )

    def verify_init_fallback_subset(
        self,
        state: PatchState,
        base: Optional[Tuple[int, int, int, int]] = None,
        timeout: float = 1.0,
        repair: bool = True,
        max_repair_rounds: int = INIT_MAX_VERIFY_REPAIRS,
        write_gap: float = INIT_WRITE_GAP_S,
    ) -> InitVerification:
        """Verify the fallback path's highest-risk writes: name, waves, and FX headers."""
        resolved_base = base if base is not None else self.get_active_patch_base(
            timeout=timeout, force_refresh=True
        )
        expected: List[Tuple[str, Tuple[int, int, int, int], bytes]] = []
        raw_name = state.common.name.encode("ascii", errors="replace")[:12].ljust(12, b" ")
        expected.append(
            ("patch_name", add_address(resolved_base, PATCH_PARAM_NAME), bytes(raw_name))
        )

        tone_offsets = {
            1: OFFSET_PATCH_TONE_1,
            2: OFFSET_PATCH_TONE_2,
            3: OFFSET_PATCH_TONE_3,
            4: OFFSET_PATCH_TONE_4,
        }
        for tone in state.tones:
            bank_id = 1 if tone.wave_bank_l.upper() == "INTA" else 2
            wave_bytes = bytes(
                [0, *pack_4nibbles(bank_id), *pack_4nibbles(max(0, min(16384, tone.wave_num_l)))]
            )
            wave_addr = add_address(
                add_address(resolved_base, tone_offsets[tone.tone_index]),
                TONE_PARAM_WAVE_GROUP_TYPE,
            )
            expected.append((f"tone{tone.tone_index}_wave", wave_addr, wave_bytes))

        effects = state.effects
        mfx_base = add_address(resolved_base, OFFSET_PATCH_COMMON_MFX)
        expected.append(
            (
                "mfx_header",
                mfx_base,
                bytes(
                    [
                        max(0, min(80, int(effects.mfx_type))),
                        max(0, min(127, int(effects.mfx_dry_send))),
                        max(0, min(127, int(effects.mfx_chorus_send))),
                        max(0, min(127, int(effects.mfx_reverb_send))),
                    ]
                ),
            )
        )
        cho_base = add_address(resolved_base, OFFSET_PATCH_COMMON_CHORUS)
        expected.extend(
            [
                ("chorus_type", add_address(cho_base, CHORUS_PARAM_TYPE), bytes([max(0, min(3, int(effects.chorus_type)))])),
                ("chorus_level", add_address(cho_base, CHORUS_PARAM_LEVEL), bytes([max(0, min(127, int(effects.chorus_level)))])),
                (
                    "chorus_output",
                    add_address(cho_base, CHORUS_PARAM_OUTPUT_SELECT),
                    bytes([max(0, min(2, int(effects.chorus_to_reverb)))]),
                ),
            ]
        )
        rev_base = add_address(resolved_base, OFFSET_PATCH_COMMON_REVERB)
        expected.extend(
            [
                ("reverb_type", add_address(rev_base, REVERB_PARAM_TYPE), bytes([max(0, min(5, int(effects.reverb_type)))])),
                ("reverb_level", add_address(rev_base, REVERB_PARAM_LEVEL), bytes([max(0, min(127, int(effects.reverb_level)))])),
            ]
        )
        expected.extend(
            [
                (
                    "setup_chorus_switch",
                    tuple(ADDR_SETUP_CHORUS_SWITCH),
                    bytes([0 if int(effects.chorus_type) == 0 else 1]),
                ),
                (
                    "setup_reverb_switch",
                    tuple(ADDR_SETUP_REVERB_SWITCH),
                    bytes([0 if int(effects.reverb_type) == 0 else 1]),
                ),
            ]
        )
        return self.verify_writes(
            expected,
            timeout=timeout,
            repair=repair,
            max_repair_rounds=max_repair_rounds,
            write_gap=write_gap,
        )

    def write_init_template(
        self,
        payload: dict,
        timeout: float = 1.0,
        base: Optional[Tuple[int, int, int, int]] = None,
        write_gap: float = INIT_WRITE_GAP_S,
    ) -> int:
        """Restore the golden image into the active temp patch RAM with one DT1 per chunk.

        Returns the number of failed messages (0 = complete restore).
        """
        resolved_base = base if base is not None else self.get_active_patch_base(timeout=timeout)
        failures = 0
        with self.paced_init_writes(write_gap):
            for key, region in payload["regions"].items():
                region_addr = add_address(resolved_base, tuple(region["offset"]))
                for chunk in region["chunks"]:
                    try:
                        self.send_data(add_address(region_addr, chunk["start"]), chunk["bytes"])
                    except Exception as e:
                        failures += 1
                        logger.warning(f"Init template write failed for {key} @0x{chunk['start']:03X}: {e}")

            # Mirror the Setup global FX switches to the image's chorus/reverb types
            # (same behavior as selecting the patch on the keyboard).
            chorus_type = 0
            reverb_type = 0
            if payload["regions"].get("chorus", {}).get("chunks"):
                chorus_type = int(payload["regions"]["chorus"]["chunks"][0]["bytes"][0])
            if payload["regions"].get("reverb", {}).get("chunks"):
                reverb_type = int(payload["regions"]["reverb"]["chunks"][0]["bytes"][0])
            for addr, ftype, label in (
                (ADDR_SETUP_CHORUS_SWITCH, chorus_type, "chorus"),
                (ADDR_SETUP_REVERB_SWITCH, reverb_type, "reverb"),
            ):
                try:
                    self.send_data(addr, [0 if ftype == 0 else 1])
                except Exception as e:
                    failures += 1
                    logger.warning(f"Could not sync master {label} setup switch during init: {e}")
        return failures

    def init_patch(
        self,
        timeout: float = 1.0,
        *,
        write_gap: float = INIT_WRITE_GAP_S,
        verify: bool = True,
        max_repair_rounds: int = INIT_MAX_VERIFY_REPAIRS,
    ) -> bool:
        """Initialize the active temporary patch buffer to the golden JUNO SPECTRE template.

        Preferred path: single contiguous image restore per region (zero residue,
        including parameters the app does not model). Falls back to the per-parameter
        reset sequence when the template asset is unavailable.
        """
        self.invalidate_cache()
        payload = self.load_init_template()
        if payload is None:
            logger.info("init_template.json not found; using per-parameter fallback reset.")
            return self.init_patch_fallback(
                write_gap=write_gap,
                verify_subset=verify,
                timeout=timeout,
                max_repair_rounds=max_repair_rounds,
            )

        try:
            with self.paced_init_writes(write_gap):
                base = self.get_active_patch_base(timeout=timeout, force_refresh=True)
                failures = self.write_init_template(payload, timeout=timeout, base=base, write_gap=write_gap)
        except Exception as e:
            logger.error(f"Init template restore failed: {e}; falling back to per-parameter reset.")
            return self.init_patch_fallback(
                write_gap=write_gap,
                verify_subset=False,
                timeout=timeout,
                max_repair_rounds=max_repair_rounds,
            )
        if failures:
            logger.warning(f"Golden template restore reported {failures} failed message(s); verifying before giving up.")
        if not verify:
            if failures == 0:
                logger.info("Patch initialized from golden template image.")
                return True
            logger.warning(f"Golden template restore completed with {failures} failed message(s).")
            return False

        try:
            verification = self.verify_init_template(
                payload,
                base=base,
                timeout=timeout,
                repair=True,
                max_repair_rounds=max_repair_rounds,
                write_gap=write_gap,
            )
        except Exception as e:
            logger.error(f"Init template verification failed: {e}")
            return False
        if not verification.ok:
            labels = ", ".join(m.label for m in verification.failed)
            logger.warning(f"Golden template restore incomplete after repair: {labels}")
            return False
        if verification.repaired:
            labels = ", ".join(m.label for m in verification.repaired)
            logger.info(f"Patch initialized from golden template image after repairing: {labels}.")
        else:
            logger.info("Patch initialized from golden template image.")
        return True

    def init_patch_fallback(
        self,
        *,
        write_gap: float = INIT_WRITE_GAP_S,
        verify_subset: bool = True,
        timeout: float = 1.0,
        max_repair_rounds: int = INIT_MAX_VERIFY_REPAIRS,
    ) -> bool:
        """Per-parameter reset sequence, driven entirely by create_init_patch() state.

        Used only when the golden template asset is unavailable. Kept consistent with
        the template so both paths converge on the same patch.
        """
        self.invalidate_cache()
        st = PatchState.create_init_patch()
        failures: list[str] = []

        def _try(label: str, fn, *args, **kwargs) -> None:
            try:
                with self.paced_init_writes(write_gap):
                    fn(*args, **kwargs)
            except Exception as e:
                failures.append(label)
                logger.warning(f"Init fallback '{label}' failed: {e}")
            if write_gap > 0:
                time.sleep(write_gap)

        _try("patch name", self.set_patch_name, st.common.name)
        _try("level", self.set_patch_param, "level", st.common.level)
        _try("pan", self.set_patch_param, "pan", st.common.pan)
        _try("cutoff_offset", self.set_patch_param, "cutoff_offset", st.common.cutoff_offset)
        _try("resonance_offset", self.set_patch_param, "resonance_offset", st.common.resonance_offset)
        _try("attack_offset", self.set_patch_param, "attack_offset", st.common.attack_offset)
        _try("release_offset", self.set_patch_param, "release_offset", st.common.release_offset)
        _try("portamento", self.set_portamento, st.common.portamento_switch, st.common.portamento_time)
        _try("legato", self.set_legato, st.common.legato_switch)
        _try("analog_feel", self.set_patch_analog_feel, st.common.analog_feel)
        _try("output_assign", self.set_patch_output_assign, st.common.patch_output_assign)

        for i, m in enumerate(st.common.matrix_ctrls, start=1):
            _try(
                f"matrix_{i}",
                self.set_matrix_control,
                i,
                source=m.source,
                dest1=m.dest1, sens1=m.sens1,
                dest2=m.dest2, sens2=m.sens2,
                dest3=m.dest3, sens3=m.sens3,
                dest4=m.dest4, sens4=m.sens4,
            )

        eff = st.effects
        _try(
            "mfx",
            self.set_mfx,
            mfx_type=eff.mfx_type,
            dry_send=eff.mfx_dry_send,
            chorus_send=eff.mfx_chorus_send,
            reverb_send=eff.mfx_reverb_send,
        )
        if eff.mfx_type != 0:
            _try("mfx_params", self.set_mfx_params_bulk, eff.mfx_params[:14])
        _try("chorus", self.set_chorus, eff.chorus_type, level=eff.chorus_level, output_select=eff.chorus_to_reverb)
        for param, val in (
            ("preDelay", eff.chorus_predelay),
            ("rate", eff.chorus_rate),
            ("depth", eff.chorus_depth),
            ("feedback", eff.chorus_feedback),
        ):
            _try(f"chorus_{param}", self.set_chorus_param, param, val)
        _try("reverb", self.set_reverb, eff.reverb_type, level=eff.reverb_level)
        for param, val in (
            ("preDelay", eff.reverb_predelay),
            ("time", eff.reverb_time),
            ("damp", eff.reverb_damp),
            ("diffusion", eff.reverb_diffusion),
            ("tone", eff.reverb_tone),
        ):
            _try(f"reverb_{param}", self.set_reverb_param, param, val)

        for t in st.tones:
            idx = t.tone_index
            _try(f"tone{idx}_enable", self.ensure_tone_enabled, idx)
            _try(
                f"tone{idx}_wave",
                self.set_tone_wave,
                idx,
                bank=t.wave_bank_l,
                wave_num=t.wave_num_l,
                gain=t.wave_gain,
                fxm_switch=1 if t.wave_fxm_switch else 0,
                fxm_depth=t.wave_fxm_depth,
            )
            _try(
                f"tone{idx}_output",
                self.set_tone_output,
                idx,
                output_assign=t.output_assign,
                output_level=t.output_level,
                chorus_send=t.chorus_send,
                reverb_send=t.reverb_send,
            )
            _try(
                f"tone{idx}_tvf",
                self.set_tone_tvf,
                idx,
                cutoff=t.tvf_cutoff,
                resonance=t.tvf_resonance,
                env_depth=t.tvf_env_depth,
                filter_type=t.tvf_filter_type,
                attack=t.tvf_t1,
                decay=t.tvf_t2,
                sustain=t.tvf_l3,
                release=t.tvf_t4,
                key_follow=t.tvf_cutoff_keyfollow,
                env_vel_sens=t.tvf_env_velo_sens,
                env_t1_vel_sens=t.tvf_env_t1_vel_sens,
                env_t4_vel_sens=t.tvf_env_t4_vel_sens,
                env_time_keyfollow=t.tvf_env_time_keyfollow,
            )
            _try(
                f"tone{idx}_tva",
                self.set_tone_tva,
                idx,
                level=t.level,
                pan=t.pan,
                attack=t.tva_t1,
                decay=t.tva_t2,
                sustain=t.tva_l3,
                release=t.tva_t4,
                env_vel_sens=t.tva_velo_sens,
                env_t1_vel_sens=t.tva_env_t1_vel_sens,
                env_t4_vel_sens=t.tva_env_t4_vel_sens,
                env_time_keyfollow=t.tva_env_time_keyfollow,
            )
            _try(
                f"tone{idx}_pitch",
                self.set_tone_pitch,
                idx,
                coarse=t.coarse_tune,
                fine=t.fine_tune,
                env_depth=t.pitch_env_depth,
            )
            _try(
                f"tone{idx}_pitch_env",
                self.set_tone_pitch_env,
                idx,
                depth=t.pitch_env_depth,
                vel_sens=t.pitch_env_vel_sens,
                time_keyfollow=t.pitch_env_time_keyfollow,
                t1_vel_sens=t.pitch_env_t1_vel_sens,
                t4_vel_sens=t.pitch_env_t4_vel_sens,
                t1=t.pitch_env_t1, t2=t.pitch_env_t2, t3=t.pitch_env_t3, t4=t.pitch_env_t4,
                l0=t.pitch_env_l0, l1=t.pitch_env_l1, l2=t.pitch_env_l2,
                l3=t.pitch_env_l3, l4=t.pitch_env_l4,
            )
            _try(
                f"tone{idx}_lfo1",
                self.set_tone_lfo,
                idx,
                lfo_index=1,
                waveform=t.lfo1_waveform,
                rate=t.lfo1_rate,
                pitch_depth=t.lfo1_pitch_depth,
                tvf_depth=t.lfo1_tvf_depth,
                tva_depth=t.lfo1_tva_depth,
                pan_depth=t.lfo1_pan_depth,
                delay_time=t.lfo1_delay_time,
                fade_mode=t.lfo1_fade_mode,
                fade_time=t.lfo1_fade_time,
            )
            _try(
                f"tone{idx}_lfo2",
                self.set_tone_lfo,
                idx,
                lfo_index=2,
                waveform=t.lfo2_waveform,
                rate=t.lfo2_rate,
                pitch_depth=t.lfo2_pitch_depth,
                tvf_depth=t.lfo2_tvf_depth,
                tva_depth=t.lfo2_tva_depth,
                pan_depth=t.lfo2_pan_depth,
                delay_time=t.lfo2_delay_time,
                fade_mode=t.lfo2_fade_mode,
                fade_time=t.lfo2_fade_time,
            )
            _try(
                f"tone{idx}_step_lfo",
                self.set_tone_step_lfo_all,
                idx,
                step_type=t.step_lfo_type,
                steps=t.step_lfo_steps,
            )

        if failures:
            logger.warning(f"Init fallback completed with {len(failures)} failed parameter group(s).")
            return False
        if not verify_subset:
            return True
        try:
            verification = self.verify_init_fallback_subset(
                st,
                timeout=timeout,
                repair=True,
                max_repair_rounds=max_repair_rounds,
                write_gap=write_gap,
            )
        except Exception as e:
            logger.error(f"Init fallback verification failed: {e}")
            return False
        if not verification.ok:
            labels = ", ".join(m.label for m in verification.failed)
            logger.warning(f"Init fallback incomplete after repair: {labels}")
            return False
        if verification.repaired:
            labels = ", ".join(m.label for m in verification.repaired)
            logger.info(f"Init fallback completed after repairing: {labels}.")
        return True

