"""User flash slots, SysEx blobs, and initialization protocol mixin for Roland JUNO-DS / XPS-30."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from .patch_state import (
    TEMPLATE_ASSET_PATH,
    PatchState,
    effects_from_blocks,
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
    PATCH_TONE_OFFSETS,
    RolandSysEx,
    add_address,
    encode_name,
)

logger = logging.getLogger(__name__)


def _named_common(state: PatchState) -> bytes:
    """The common region with the state's name in it (the name travels in the image)."""
    common = bytearray(state.raw_regions["common"][0][:80])
    common[0:12] = encode_name(state.common.name)
    return bytes(common)


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

    def _read_patch_regions(self, base: Tuple[int, int, int, int],
                            timeout: float = 1.0) -> dict[str, list[bytes]]:
        """Gather the canonical raw image at any patch base (temp or flash)."""
        raw_regions: dict[str, list[bytes]] = {}
        raw_regions["common"] = [self._read_common_raw(base, timeout=timeout)]
        for idx, off in PATCH_TONE_OFFSETS.items():
            main_raw, lfo_raw = self._read_tone_raws(add_address(base, off), timeout=timeout)
            raw_regions[f"tone_{idx}"] = [main_raw, lfo_raw]
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
        return self.read_patch_at(self.user_slot_base(msb, lsb, pc), timeout=timeout)

    def read_patch_at(self, base: Tuple[int, int, int, int],
                      timeout: float = 1.5) -> PatchState:
        """Read and decode the patch image at any base (temp or flash)."""
        raw_regions = self._read_patch_regions(base, timeout=timeout)
        common = PatchState._decode_common(raw_regions["common"][0])
        tones = []
        for idx in range(1, 5):
            main_raw, lfo_raw = raw_regions[f"tone_{idx}"]
            tones.append(PatchState._decode_tone(main_raw, lfo_raw, idx))
        PatchState.apply_tmt(raw_regions["tmt"][0], common, tones)
        effects = effects_from_blocks(raw_regions["mfx"][0], raw_regions["chorus"][0],
                                      raw_regions["reverb"][0])
        state = PatchState(sound_mode="PATCH", common=common, tones=tones, effects=effects,
                           raw_regions=raw_regions)
        state.custom_detune_cache = [t.fine_tune for t in tones]
        return state

    def write_patch_regions(self, state: PatchState,
                             base: Tuple[int, int, int, int],
                             write_gap: float = 0.02) -> int:
        """DT1-push a PatchState raw image to any patch base. Returns failures."""
        if not state.raw_regions:
            raise ValueError("No raw image: sync/read the patch first.")
        failures = 0
        common = _named_common(state)
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

    @staticmethod
    def patch_image_mismatches(state: PatchState, actual: dict) -> list[str]:
        """Compare a PatchState image with raw regions read back. [] = same sound."""
        mismatches: list[str] = []
        common = _named_common(state)
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
        raw_name = encode_name(name)
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
        common = _named_common(state)
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
        try:
            payload = json.loads(Path(TEMPLATE_ASSET_PATH).read_text(encoding="utf-8"))
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

        One contiguous image restore per region (zero residue, including
        parameters the app does not model), then a verify/repair pass.
        """
        self.invalidate_cache()
        payload = self.load_init_template()
        if payload is None:
            logger.error("init_template.json is missing or invalid; cannot initialize the patch.")
            return False

        try:
            with self.paced_init_writes(write_gap):
                base = self.get_active_patch_base(timeout=timeout, force_refresh=True)
                failures = self.write_init_template(payload, timeout=timeout, base=base, write_gap=write_gap)
        except Exception as e:
            logger.error(f"Init template restore failed: {e}")
            return False
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


