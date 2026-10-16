"""Performance bridge mixin: 16-part mixer, performance FX, routing, and song loads."""

from __future__ import annotations

import copy
import logging
import threading
from pathlib import Path

from PyQt6.QtCore import pyqtProperty, pyqtSignal, pyqtSlot

from ...core.mfx_catalog import get_mfx_algo
from ...core.patch_state import PatchState, PerfFxState, PerfPartState
from ...core.protocol import JunoClient, SoundMode
from ...core.routing import is_direct, mfx_structure_layout
from ...core.spectre_format import (
    file_patch_hash,
    load_spectre,
    patch_state_from_dict,
    patch_state_to_dict,
    save_spectre,
    snapshot_hash_of,
)
from ...core.sysex import (
    ADDR_TEMP_PATCH_PART_1,
    OFFSET_PATCH_COMMON_MFX,
    PERF_MFX_BLOCK_SIZE,
    add_address,
    perf_common_fx_base,
    temp_perf_patch_base,
)
from ...sequencer.models import SequencerSong, default_sequencer_song
from ...vector.motion import RecorderState
from .base import BridgeBaseMixin
from .fx_target import CHORUS_ATTRS, REVERB_ATTRS, FxTarget

logger = logging.getLogger(__name__)

_MFX_STRUCTURE_LAYOUTS = [mfx_structure_layout(s) for s in range(16)]

# INIT PERF: fresh song layout (Bank MSB, LSB, PC, display name)
INIT_PERF_NAME = "INIT PERF"
INIT_PERF_PIANO_PART = 2
INIT_PERF_PIANO = (87, 64, 0, "Grand Pno DS")
INIT_PERF_DRUM_PART = 10  # the sequencer's default drum track sends here
INIT_PERF_DRUMS = (86, 64, 0, "Pop Kit 1")


class PerformanceBridgeMixin(BridgeBaseMixin):
    """Performance 16-part mixer, common FX, part-pick mode, and song loads."""

    perfPartsChanged = pyqtSignal()
    perfFxChanged = pyqtSignal()
    librarianPickChanged = pyqtSignal()
    perfPushChanged = pyqtSignal(float)
    pushJobsFinished = pyqtSignal()  # from the push worker; refreshes on the UI thread
    # Background part read finished: (part index, PatchState) -> UI thread
    partStateRead = pyqtSignal(int, object)
    partFileStatusChanged = pyqtSignal()
    requestOpenEditTarget = pyqtSignal()

    def _init_performance(self) -> None:
        """Part file links, the part FX cache and the background push state."""
        # Embedded snapshots from the last loaded performance file (part index
        # str -> patch_state dict) and their link health
        self._part_snapshots: dict = {}
        self._snapshot_hashes: dict = {}  # part index -> (snapshot dict, its hash)
        self._part_file_status: list = [""] * 16
        # Part index -> that part patch's FX (EffectsState) for PARTn origins. Lets MFX Studio /
        # Master FX show a non-active part's patch FX without blocking QML
        # getters on hardware reads.
        self._part_fx_cache: dict = {}
        self._perf_push_progress: float = -1.0  # -1.0 = idle
        # Synth push jobs, run in order by one worker (see _queue_push_jobs)
        self._push_queue: list = []
        self._push_queue_lock = threading.Lock()
        self._push_thread: threading.Thread | None = None
        self._push_done = 0
        self._push_total = 0
        self.pushJobsFinished.connect(self.refreshPartFileStatus)
        self._editing_perf_mfx: int = 1
        self._push_lock = threading.Lock()
        self.partStateRead.connect(self._on_part_state_read)

    @pyqtProperty("QVariantList", notify=perfPartsChanged)
    def perfParts(self) -> list:
        return [
            {
                "index": p.part_index,
                "name": p.patch_name or p.name,
                "volume": p.volume,
                "pan": p.pan,
                "muted": p.muted,
                "solo": p.solo,
                "msb": p.patch_msb,
                "lsb": p.patch_lsb,
                "pc": p.patch_pc,
                "rxChannel": p.rx_channel,
                "rxOn": p.rx_switch,
                "keyLow": p.key_low,
                "keyHigh": p.key_high,
                "zoneOn": p.zone_switch,
                "zoneOctave": p.zone_octave,
                "drySend": getattr(p, "dry_send", 127),
                "chorusSend": getattr(p, "chorus_send", 0),
                "reverbSend": getattr(p, "reverb_send", 0),
                "outputAssign": getattr(p, "output_assign", 13),
                "mfxSelect": getattr(p, "mfx_select", 0),
                "hasFile": bool(p.patch_file),
            }
            for p in self.patch_state.perf_parts[:16]
        ]

    def _rail_fx_target(self, block: str, slot: int | None = None) -> FxTarget:
        """A rail card shows the sounding processor: the source part's FX when
        cached, else the performance common values."""
        t = self._fx_target(block, slot=slot)
        if t.kind == "part" and t.store is not None:
            return t
        fx = self.patch_state.perf_fx
        return FxTarget("perf", slot or 0, self._perf_slot(slot) if block == "mfx" else fx)

    def _rail_mfx_entry(self, n: int) -> dict:
        """Rail card content: the sounding processor (origin-resolved)."""
        t = self._rail_fx_target("mfx", n)
        shown = {"type": int(t.mfx("type")), "drySend": int(t.mfx("dry")),
                 "chorusSend": int(t.mfx("chorus")), "reverbSend": int(t.mfx("reverb"))}
        algo = get_mfx_algo(shown["type"])
        shown["name"] = algo["name"].split(" ", 1)[-1] if algo else "THRU"
        return {"kind": f"MFX{n}", "slot": n, **shown, "source": int(self._perf_slot(n).source),
                "editing": self._editing_perf_mfx == n}

    def _rail_cho_entry(self) -> dict:
        s = self._rail_fx_target("chorus").store
        return {"kind": "CHORUS", "type": int(s.chorus_type), "level": int(s.chorus_level),
                "toReverb": int(s.chorus_to_reverb),
                "source": int(self.patch_state.perf_fx.chorus_source)}

    def _rail_rev_entry(self) -> dict:
        s = self._rail_fx_target("reverb").store
        return {"kind": "REVERB", "type": int(s.reverb_type), "level": int(s.reverb_level),
                "source": int(self.patch_state.perf_fx.reverb_source)}

    @pyqtProperty("QVariantList", notify=perfFxChanged)
    def perfFxSlots(self) -> list:
        """5 shared FX cards: MFX1-3 + chorus + reverb (origin-resolved content)."""
        fx = getattr(self.patch_state, "perf_fx", None)
        if fx is None:
            return []
        return [self._rail_mfx_entry(1), self._rail_mfx_entry(2),
                self._rail_mfx_entry(3), self._rail_cho_entry(),
                self._rail_rev_entry()]

    @pyqtProperty(int, notify=perfFxChanged)
    def editingPerfMfx(self) -> int:
        return max(1, min(3, int(getattr(self, "_editing_perf_mfx", 1))))

    @staticmethod
    def _origin_text(origin: int) -> str:
        return "PERFORM" if int(origin) == 0 else f"PART {int(origin)}"

    @pyqtProperty(str, notify=perfFxChanged)
    def mfxEditTargetLabel(self) -> str:
        """MFX Studio context chip: which MFX + origin it shows/edits (compact)."""
        t = self._fx_target("mfx")
        if t.kind == "perf":
            return f"MFX{t.index}\u00b7PERF"
        if t.kind == "part":
            return f"MFX{self.editingPerfMfx}\u00b7P{t.index}"
        return "PATCH"

    @pyqtProperty(str, notify=perfFxChanged)
    def choEditTargetLabel(self) -> str:
        """Master FX chorus context chip (compact)."""
        t = self._fx_target("chorus")
        return {"perf": "CHO\u00b7PERF", "part": f"CHO\u00b7P{t.index}"}.get(t.kind, "PATCH")

    @pyqtProperty(str, notify=perfFxChanged)
    def revEditTargetLabel(self) -> str:
        """Master FX reverb context chip (compact)."""
        t = self._fx_target("reverb")
        return {"perf": "REV\u00b7PERF", "part": f"REV\u00b7P{t.index}"}.get(t.kind, "PATCH")

    @pyqtProperty("QVariantList", constant=True)
    def perfMfxStructures(self) -> list:
        """The 16 MFX Structure types as drawable layouts (core.routing)."""
        return _MFX_STRUCTURE_LAYOUTS

    @pyqtProperty(int, notify=perfFxChanged)
    def perfStructure(self) -> int:
        fx = getattr(self.patch_state, "perf_fx", None)
        return int(getattr(fx, "mfx_structure", 0)) if fx is not None else 0

    @pyqtProperty("QVariantMap", notify=perfPartsChanged)
    def perfHeader(self) -> dict:
        """Header pieces in PERFORM: performance name, edited part and its patch."""
        idx = max(1, min(16, int(getattr(self.patch_state, "active_perf_part", 1))))
        try:
            part = self.patch_state.perf_parts[idx - 1]
            patch = str(part.patch_name or part.name or f"Part {idx}")
        except IndexError:
            patch = f"Part {idx}"
        perf = str(getattr(self.patch_state, "perf_name", "") or self._patch_name or "")
        return {"perf": perf, "part": idx, "patch": patch}

    @pyqtProperty(str, notify=perfPartsChanged)
    def perfName(self) -> str:
        return getattr(self.patch_state, "perf_name", "SPECTRE PERF")

    @pyqtProperty(int, notify=perfPartsChanged)
    def activePerfPart(self) -> int:
        return max(1, min(16, int(getattr(self.patch_state, "active_perf_part", 1))))

    @pyqtProperty(float, notify=perfPushChanged)
    def perfPushProgress(self) -> float:
        """Background part-image push progress 0..1 (-1.0 = idle)."""
        return float(self._perf_push_progress)

    @pyqtProperty("QVariantList", notify=partFileStatusChanged)
    def partFileStatus(self) -> list:
        """Per-part file-link health: '' | 'ok' | 'updated' | 'missing'."""
        return list(self._part_file_status)

    def _set_push_progress(self, value: float) -> None:
        self._perf_push_progress = float(value)
        try:
            self.perfPushChanged.emit(float(value))
        except Exception:
            pass

    def refreshPartFileStatus(self) -> None:
        """Recompute file-link health for all 16 parts (call on load/save/pick)."""
        statuses = []
        for i, part in enumerate(self.patch_state.perf_parts[:16]):
            link = str(getattr(part, "patch_file", "") or "")
            if part.modified and (not link or Path(link).is_file()):
                statuses.append("edited")
                continue
            if not link:
                statuses.append("")
                continue
            snap = (self._part_snapshots or {}).get(str(part.part_index))
            if not Path(link).is_file():
                statuses.append("missing" if snap is not None else "missing-dead")
                continue
            if snap is None:
                statuses.append("ok")
                continue
            try:
                held = self._snapshot_hashes.get(part.part_index)
                if held is None or held[0] is not snap:  # snapshots are replaced, never edited
                    held = (snap, snapshot_hash_of(snap))
                    self._snapshot_hashes[part.part_index] = held
                statuses.append("ok" if file_patch_hash(link) == held[1] else "updated")
            except Exception:
                statuses.append("missing" if snap is not None else "missing-dead")
        self._part_file_status = statuses
        try:
            self.partFileStatusChanged.emit()
        except Exception:
            pass

    def _on_perf_part_write(self, part_index: int) -> None:
        """A DT1 reached a part's temp buffer: its sound now differs from its source."""
        parts = self.patch_state.perf_parts
        if not 1 <= int(part_index) <= len(parts) or parts[part_index - 1].modified:
            return
        parts[part_index - 1].modified = True
        try:
            self._part_file_status[part_index - 1] = "edited"
            self.partFileStatusChanged.emit()
        except Exception:
            pass

    def _read_part_image(self, part_index: int):
        """Read a part's sounding image from the synth, or None (offline/failed)."""
        juno = self.juno
        if juno is None or not hasattr(juno, "read_perf_part_patch"):
            return None
        # Don't read a buffer while a background push is still writing it.
        if not self._push_lock.acquire(timeout=10.0):
            return None
        try:
            return juno.read_perf_part_patch(int(part_index))
        except Exception as e:
            logger.debug(f"part {part_index} image read failed: {e}")
            return None
        finally:
            self._push_lock.release()

    def _capture_part_snapshots(self) -> dict:
        """Every part's sound, for saving: edits read from the synth, files as stored.

        Untouched slot parts need no image (the Bank/PC reference is the sound).
        Offline or on read failure an edited part keeps the image already held.
        """
        held = self._part_snapshots or {}
        snaps = {}
        for p in self.patch_state.perf_parts:
            key = str(p.part_index)
            link = str(getattr(p, "patch_file", "") or "")
            if p.modified:
                image = self._read_part_image(p.part_index)
                if image is not None:
                    snaps[key] = patch_state_to_dict(image)
                    continue
                if isinstance(held.get(key), dict):
                    snaps[key] = held[key]
                    continue
            if link and Path(link).is_file():
                try:
                    snaps[key] = patch_state_to_dict(load_spectre(link)["patch_state"])
                    continue
                except Exception as e:
                    logger.debug(f"part {key} snapshot: link unreadable: {e}")
            # Missing/unreadable link: keep the image we already hold.
            if link and isinstance(held.get(key), dict):
                snaps[key] = held[key]
        return snaps

    def _part_restore_image(self, part, part_snapshots: dict):
        """The image a part sounds on load, or None when its slot select suffices.

        Edits ride the snapshot; an untouched file part follows its (newer) file.
        """
        link = str(getattr(part, "patch_file", "") or "")
        snap = (part_snapshots or {}).get(str(part.part_index))
        if link and not part.modified and Path(link).is_file():
            try:
                return load_spectre(link)["patch_state"]
            except Exception as e:
                logger.debug(f"part {part.part_index}: link unreadable: {e}")
        if (link or part.modified) and isinstance(snap, dict):
            try:
                return patch_state_from_dict(snap)
            except Exception as e:
                logger.debug(f"part {part.part_index}: bad snapshot: {e}")
        return None

    @staticmethod
    def _part_write_target(part) -> tuple[str, str]:
        """Where an edited part's sound can be written back: ('file'|'slot'|'', label)."""
        link = str(getattr(part, "patch_file", "") or "")
        if link:
            if Path(link).is_file():
                return "file", f"file {Path(link).stem}"
            return "", "file missing, stays in the song"
        if getattr(part, "memory_only", False):
            return "", "memory only, stays in the song"
        try:
            JunoClient.user_slot_base(part.patch_msb, part.patch_lsb, part.patch_pc)
        except ValueError:
            return "", "no user slot, stays in the song"
        return "slot", f"keyboard {501 + int(part.patch_lsb) * 128 + int(part.patch_pc)}"

    @pyqtSlot(result="QVariantList")
    def perfEditedParts(self) -> list:
        """Edited parts and where 'update source patches' would write them."""
        out = []
        for p in self.patch_state.perf_parts:
            if not p.modified:
                continue
            target, label = self._part_write_target(p)
            out.append({"part": p.part_index, "name": p.patch_name or p.name,
                        "target": target, "label": label})
        return out

    @pyqtSlot(result=str)
    def writeBackEditedParts(self) -> str:
        """Overwrite each edited part's source (Pi file or keyboard user slot)
        with the part's current sound. Returns '' or a summary of failures.

        Written parts become clean; parts with no writable source stay edited
        (their sound lives in the song's snapshot).
        """
        errors = []
        for p in self.patch_state.perf_parts:
            if not p.modified:
                continue
            target, _ = self._part_write_target(p)
            if not target:
                continue
            key = str(p.part_index)
            image = self._read_part_image(p.part_index)
            if image is None and isinstance((self._part_snapshots or {}).get(key), dict):
                try:
                    image = patch_state_from_dict(self._part_snapshots[key])
                except Exception as e:
                    logger.debug(f"write back P{key}: bad snapshot: {e}")
            if image is None:
                errors.append(f"P{key}: sound unavailable")
                continue
            if target == "file":
                try:
                    old = load_spectre(p.patch_file)
                    # The file keeps its library identity (name, tags...); only the sound changes.
                    image.common.name = old["patch_state"].common.name
                    save_spectre(p.patch_file, image, meta=old["meta"], spectre=old["spectre"],
                                 synth_ref=old["synth_ref"], kind=old["kind"])
                    repo = getattr(self, "_librarian_repo", None)
                    if repo is not None:
                        repo.touch_file_row(p.patch_file)
                    self._part_snapshots[key] = patch_state_to_dict(
                        load_spectre(p.patch_file)["patch_state"])
                except Exception as e:
                    errors.append(f"P{key}: {e}")
                    continue
            else:
                err = self._write_user_slot(image, p.patch_msb, p.patch_lsb, p.patch_pc)
                if err:
                    errors.append(f"P{key}: {err}")
                    continue
                self._part_snapshots.pop(key, None)
            p.modified = False
        self.refreshPartFileStatus()
        self.perfPartsChanged.emit()
        return "; ".join(errors)

    def _queue_push_jobs(self, jobs: list, replace: bool = False) -> None:
        """Run synth push jobs on the push worker, in order (SysEx is slow).

        Jobs: ('perf', parts, fx) the mixer, zones and shared FX of a
        performance; ('image', part_index, PatchState) a part's sound;
        ('select', part_index, msb, lsb, pc). replace=True (a new performance)
        drops the jobs still waiting from the previous one.
        """
        if not jobs:
            return
        with self._push_queue_lock:
            if replace or not self._push_queue:
                self._push_done = self._push_total = 0
                self._push_queue.clear()
            self._push_queue.extend(jobs)
            self._push_total += len(jobs)
            start = self._push_thread is None
            if start:
                self._push_thread = threading.Thread(target=self._push_parts_worker,
                                                     name="part-push", daemon=True)
            progress = self._push_done / max(1, self._push_total)
        self._set_push_progress(progress)
        if start:
            self._push_thread.start()

    def _push_parts_worker(self) -> None:
        juno = self.juno
        while True:
            with self._push_queue_lock:
                if not self._push_queue or juno is None:
                    self._push_queue.clear()
                    self._push_thread = None
                    self._set_push_progress(-1.0)
                    break
                job = self._push_queue.pop(0)
            with self._push_lock:
                try:
                    if job[0] == "perf":
                        self._send_perf_mixer(juno, job[1], job[2])
                    elif job[0] == "image":
                        _, part, state = job
                        fails = juno.push_patch_to_perf_part(state, int(part))
                        if fails:
                            logger.warning(f"part {part}: {fails} DT1 failures")
                    elif job[0] == "select":
                        _, part, msb, lsb, pc = job
                        juno.set_perf_part_patch(int(part), int(msb), int(lsb), int(pc))
                except Exception as e:
                    logger.debug(f"push job {job[0]} failed: {e}")
            with self._push_queue_lock:
                self._push_done += 1
                progress = self._push_done / max(1, self._push_total)
            self._set_push_progress(progress)
        self.pushJobsFinished.emit()

    @pyqtSlot(int, result=bool)
    def refreshPartFile(self, part_index: int) -> bool:
        """Re-push a file-linked part: the file always wins (it is the newer
        sound, edits are dropped); a missing file falls back to the snapshot."""
        if not 1 <= int(part_index) <= 16:
            return False
        part = self.patch_state.perf_parts[int(part_index) - 1]
        link = str(getattr(part, "patch_file", "") or "")
        snap = (self._part_snapshots or {}).get(str(part.part_index))
        state = None
        if link and Path(link).is_file():
            try:
                state = load_spectre(link)["patch_state"]
                self._part_snapshots[str(part.part_index)] = patch_state_to_dict(state)
                part.modified = False
            except Exception as e:
                logger.debug(f"refreshPartFile: link unreadable: {e}")
        if state is None and isinstance(snap, dict):
            try:
                state = patch_state_from_dict(snap)
            except Exception as e:
                logger.debug(f"refreshPartFile: bad snapshot: {e}")
        if state is None:
            return False
        self._queue_push_jobs([("image", part.part_index, state)])
        self.refreshPartFileStatus()
        return True

    @pyqtSlot(int, bool)
    def setPartMute(self, part_index: int, mute: bool) -> None:
        """Set mute switch for Performance Part 1..16 (Mute Switch 0/1)."""
        if 1 <= part_index <= 16:
            self.patch_state.perf_parts[part_index - 1].muted = bool(mute)
            juno = self.juno
            if juno is not None:
                try:
                    juno.set_perf_part_mute(part_index, bool(mute))
                except Exception as e:
                    logger.debug(f"setPartMute: synth write failed: {e}")
            self.perfPartsChanged.emit()

    @pyqtSlot(int, bool)
    def setPartSolo(self, part_index: int, solo: bool) -> None:
        """Set solo for Performance Part 1..16.

        Hardware Solo Part Select is a single common value: soloing sets it to
        that part, unsoloing clears to OFF when no other part stays soloed.
        """
        if 1 <= part_index <= 16:
            self.patch_state.perf_parts[part_index - 1].solo = bool(solo)
            juno = self.juno
            if juno is not None:
                try:
                    if solo:
                        juno.set_perf_solo(part_index)
                    elif not any(p.solo for p in self.patch_state.perf_parts):
                        juno.set_perf_solo(0)
                except Exception as e:
                    logger.debug(f"setPartSolo: synth write failed: {e}")
            self.perfPartsChanged.emit()

    @pyqtSlot(int, int, int)
    def setPartZone(self, part_index: int, low: int, high: int) -> None:
        """Set key range for Performance Part 1..16 (auto-ordered)."""
        if 1 <= part_index <= 16:
            lo, hi = max(0, min(127, int(low))), max(0, min(127, int(high)))
            lo, hi = min(lo, hi), max(lo, hi)
            part = self.patch_state.perf_parts[part_index - 1]
            part.key_low, part.key_high = lo, hi
            juno = self.juno
            if juno is not None:
                try:
                    juno.set_perf_zone(part_index, lo, hi)
                except Exception as e:
                    logger.debug(f"setPartZone: synth write failed: {e}")
            self.perfPartsChanged.emit()

    @pyqtSlot(int, bool)
    def setPartZoneSwitch(self, part_index: int, enabled: bool) -> None:
        """Set zone on/off for Performance Part 1..16."""
        if 1 <= part_index <= 16:
            self.patch_state.perf_parts[part_index - 1].zone_switch = bool(enabled)
            juno = self.juno
            if juno is not None:
                try:
                    if hasattr(juno, "set_perf_zone_switch"):
                        juno.set_perf_zone_switch(part_index, bool(enabled))
                    else:
                        juno.set_perf_zone(part_index, switch=bool(enabled))
                except Exception as e:
                    logger.debug(f"setPartZoneSwitch: synth write failed: {e}")
            self.perfPartsChanged.emit()

    @pyqtSlot(int, int)
    def setPartZoneOctave(self, part_index: int, octave: int) -> None:
        """Set zone octave shift for Performance Part 1..16 (61..67, 64=0)."""
        if 1 <= part_index <= 16:
            octv = max(61, min(67, int(octave)))
            self.patch_state.perf_parts[part_index - 1].zone_octave = octv
            juno = self.juno
            if juno is not None:
                try:
                    juno.set_perf_zone(part_index, octave=octv)
                except Exception as e:
                    logger.debug(f"setPartZoneOctave: synth write failed: {e}")
            self.perfPartsChanged.emit()

    @pyqtSlot(int, int)
    def setPartFx(self, part_index: int, which: int, val: int) -> None:
        """Set per-part sends: which 0=dry 1=chorus 2=reverb (state + SysEx)."""
        if not 1 <= int(part_index) <= 16:
            return
        part = self.patch_state.perf_parts[int(part_index) - 1]
        v = max(0, min(127, int(val)))
        kwargs = {}
        if int(which) == 0:
            part.dry_send = v; kwargs["dry"] = v
        elif int(which) == 1:
            part.chorus_send = v; kwargs["chorus"] = v
        else:
            part.reverb_send = v; kwargs["reverb"] = v
        juno = self.juno
        if juno is not None:
            try:
                if hasattr(juno, "set_perf_part_fx"):
                    juno.set_perf_part_fx(int(part_index), **kwargs)
            except Exception as e:
                logger.debug(f"setPartFx: synth write failed: {e}")
        if int(which) in (1, 2):
            send = "chorus_send" if int(which) == 1 else "reverb_send"
            self._rebaseDirect([(f"part.{send}@{int(part_index)}", v)])
        self.perfPartsChanged.emit()

    @pyqtSlot(int, int, int)
    def setPartOutput(self, part_index: int, assign: int, mfx_select: int) -> None:
        """Set per-part output assign (0..13) + MFX select (0..2)."""
        if not 1 <= int(part_index) <= 16:
            return
        part = self.patch_state.perf_parts[int(part_index) - 1]
        part.output_assign = max(0, min(13, int(assign)))
        part.mfx_select = max(0, min(2, int(mfx_select)))
        juno = self.juno
        if juno is not None:
            try:
                if hasattr(juno, "set_perf_part_output"):
                    juno.set_perf_part_output(int(part_index), assign=part.output_assign,
                                              mfx_select=part.mfx_select)
            except Exception as e:
                logger.debug(f"setPartOutput: synth write failed: {e}")
        self.perfPartsChanged.emit()

    @pyqtSlot(int, int)
    def setPartMfxSelect(self, part_index: int, slot: int) -> None:
        """Tiny MFX 1/2/3 switcher on mixer strips (slot 0..2 from QML)."""
        if not 1 <= int(part_index) <= 16:
            return
        s = max(0, min(2, int(slot)))
        part = self.patch_state.perf_parts[int(part_index) - 1]
        part.mfx_select = s
        juno = self.juno
        if juno is not None:
            try:
                if hasattr(juno, "set_perf_part_output"):
                    juno.set_perf_part_output(int(part_index), mfx_select=s)
            except Exception as e:
                logger.debug(f"setPartMfxSelect: synth write failed: {e}")
        self.perfPartsChanged.emit()

    def _apply_patch_state_to_editors(self, state, part_index: int) -> None:
        """Apply a decoded PatchState to editors and emit all refresh signals."""
        try:
            self.patch_state.tones = state.tones
            self.patch_state.effects = state.effects
            self.patch_state.common = state.common
            if getattr(state, "common", None) and getattr(state.common, "name", ""):
                self._patch_name = state.common.name
            if len(state.tones) >= 4:
                self.vector.tone_levels = (
                    state.tones[0].level,
                    state.tones[1].level,
                    state.tones[2].level,
                    state.tones[3].level,
                )
                self.patch_state.custom_detune_cache = [t.fine_tune for t in state.tones]
            self._refresh_tone_waves()
        except Exception as e:
            logger.debug(f"_apply_patch_state_to_editors error: {e}")

        try:
            self._part_fx_cache[int(part_index)] = copy.deepcopy(state.effects)
        except Exception:
            pass

        try:
            self._emit_all_state_signals()  # includes perfPartsChanged
        except Exception as e:
            logger.debug(f"_emit_all_state_signals error: {e}")
            self.perfPartsChanged.emit()

    def _on_part_state_read(self, part_index: int, state) -> None:
        # Guard against the user switching part while reading
        if getattr(self.patch_state, "active_perf_part", 1) == int(part_index):
            self._apply_patch_state_to_editors(state, int(part_index))

    def _refresh_editors_for_part(self, part_index: int, async_mode: bool = True) -> bool:
        """Reload tones/effects for the newly selected part.

        1. Instantly loads from local snapshot/file if cached.
        2. Queries hardware temp patch buffer (11..14..) asynchronously.
        3. Updates wave and engine levels and emits _emit_all_state_signals so all QML editors update.

        Returns True when a cached sound was applied (all signals already emitted).
        """
        p_idx = int(part_index)
        if not 1 <= p_idx <= 16:
            return False

        # Fast-path: if we have a snapshot or linked file for this part, apply it immediately
        snap = (getattr(self, "_part_snapshots", None) or {}).get(str(p_idx))
        link = ""
        if hasattr(self, "patch_state") and hasattr(self.patch_state, "perf_parts"):
            if 0 <= p_idx - 1 < len(self.patch_state.perf_parts):
                link = str(getattr(self.patch_state.perf_parts[p_idx - 1], "patch_file", "") or "")

        cached_state = None
        if link and Path(link).is_file():
            try:
                cached_state = load_spectre(link).get("patch_state")
            except Exception as e:
                logger.debug(f"_refresh_editors_for_part: cached link unreadable: {e}")
        if cached_state is None and isinstance(snap, dict):
            try:
                cached_state = patch_state_from_dict(snap)
            except Exception as e:
                logger.debug(f"_refresh_editors_for_part: cached snap unreadable: {e}")

        if cached_state is not None:
            self._apply_patch_state_to_editors(cached_state, p_idx)

        juno = self.juno
        if juno is None or not hasattr(juno, "read_full_patch"):
            return cached_state is not None

        shown = cached_state

        def _worker():
            try:
                state = juno.read_full_patch(timeout=1.5)
                if state is None:
                    return
                # Same sound as the snapshot already shown: skip a second
                # full editor refresh (the costly part on a Pi)
                if shown is not None and getattr(shown, "raw_regions", None) \
                        and state.raw_regions and hasattr(juno, "patch_image_mismatches"):
                    try:
                        if not juno.patch_image_mismatches(state, shown.raw_regions):
                            return
                    except Exception:
                        pass
                if async_mode:
                    self.partStateRead.emit(p_idx, state)  # applied on the UI thread
                else:
                    self._on_part_state_read(p_idx, state)
            except Exception as e:
                logger.debug(f"_refresh_editors_for_part worker failed: {e}")

        if async_mode:
            threading.Thread(target=_worker, daemon=True).start()
        else:
            _worker()
        return cached_state is not None

    @pyqtSlot(int)
    def editPerfPart(self, part_index: int) -> None:
        """Select which performance part patch editors target (deep edit)."""
        if 1 <= part_index <= 16:
            # The part we leave may have been edited: macros re-read it when needed
            self.__dict__.setdefault("_macro_part_states", {}).pop(
                int(self.patch_state.active_perf_part), None)
            self.patch_state.active_perf_part = part_index
            if self._active_seq_track != part_index - 1:
                self._seq_set_cursor(part_index - 1)  # one part/track cursor
            juno = self.juno
            if juno is not None:
                try:
                    juno.set_active_perf_part(part_index)
                except Exception as e:
                    logger.debug(f"editPerfPart: {e}")
            mfx = self._part_mfx(part_index)
            if mfx and mfx != self.editingPerfMfx:
                self.setEditingPerfMfx(mfx)  # the MFX the part's sound enters
            if not self._refresh_editors_for_part(int(part_index), async_mode=True):
                self.perfPartsChanged.emit()

    def _part_mfx(self, part_index: int) -> int:
        """MFX (1..3) a part's sound enters, 0 when the part bypasses the MFX."""
        try:
            part = self.patch_state.perf_parts[int(part_index) - 1]
        except (IndexError, ValueError):
            return 0
        if is_direct(int(getattr(part, "output_assign", 13))):
            return 0
        return max(0, min(2, int(getattr(part, "mfx_select", 0)))) + 1

    @pyqtSlot()
    def openEditTarget(self) -> None:
        """Header picker: which part and which MFX the editors work on (PERFORM)."""
        if self._in_perform():
            self.requestOpenEditTarget.emit()

    def _in_perform(self) -> bool:
        return str(getattr(self, "_sound_mode", "PATCH")).upper() == "PERFORM"

    def _perf_slot(self, slot: int):
        fx = getattr(self.patch_state, "perf_fx", None)
        if fx is None:
            return None
        s = max(1, min(3, int(slot)))
        return (fx.mfx1, fx.mfx2, fx.mfx3)[s - 1]

    def _fx_origin(self, block: str, slot: int | None = None) -> int:
        """The performance FX origin of a block: 0 = PERFORM, n = PART n."""
        fx = self.patch_state.perf_fx
        if block == "mfx":
            return int(self._perf_slot(slot or self._editing_perf_mfx).source)
        return int(fx.chorus_source if block == "chorus" else fx.reverb_source)

    def _origin_target(self, block: str, slot: int | None = None, fetch: bool = False) -> FxTarget:
        """The performance-side target of a block (by origin, whatever the mode).

        A PART n target has store None while that part's FX are not cached;
        fetch=True reads them from the synth first.
        """
        origin = self._fx_origin(block, slot)
        if origin == 0:
            if block == "mfx":
                s = max(1, min(3, int(slot or self._editing_perf_mfx)))
                return FxTarget("perf", s, self._perf_slot(s))
            return FxTarget("perf", 0, self.patch_state.perf_fx)
        n = max(1, min(16, origin))
        if fetch:
            self._ensure_part_fx_cache(n)
        return FxTarget("part", n, self._part_fx_cache.get(n))

    def _fx_target(self, block: str, slot: int | None = None, fetch: bool = False) -> FxTarget:
        """Where an MFX / chorus / reverb edit lands (see fx_target): the patch
        FX in PATCH mode, else the origin's (block: "mfx" | "chorus" | "reverb";
        slot: MFX slot 1..3, default the one being edited)."""
        if not self._in_perform():
            return FxTarget("patch", 0, self.patch_state.effects)
        return self._origin_target(block, slot, fetch)

    def _fx_edit_target(self, block: str, fetch: bool = True) -> FxTarget:
        """The editors' target: a part not readable falls back to the edited
        patch's FX (what the editors show offline)."""
        t = self._fx_target(block, fetch=fetch)
        if t.store is None:
            return FxTarget("patch", 0, self.patch_state.effects)
        return t



    def _refresh_part_fx_cache(self, part_index: int) -> bool:
        """Best-effort hardware read of one part-patch FX into the cache."""
        juno = self.juno
        if juno is None:
            return False
        try:
            self._part_fx_cache[int(part_index)] = juno.read_part_fx(int(part_index), timeout=1.0)
            return True
        except Exception as e:
            logger.debug(f"_refresh_part_fx_cache({part_index}) failed: {e}")
        return False

    def _ensure_part_fx_cache(self, part_index: int) -> None:
        """Fill the cache for a PARTn target (no-op when already cached)."""
        n = max(1, min(16, int(part_index)))
        if n not in self._part_fx_cache:
            self._refresh_part_fx_cache(n)

    def _emit_fx_editor_signals(self) -> None:
        for sig in (self.mfxParamsChanged, self.mfxValuesChanged,
                    self.chorusParamsChanged, self.reverbParamsChanged,
                    self.routingChanged, self.perfFxChanged):
            try:
                sig.emit()
            except Exception:
                pass

    def _mfx_view(self):
        """Resolved (type_shown, bypassed, dry, cho, rev, params) for MFX Studio."""
        t = self._fx_edit_target("mfx", fetch=False)
        return (t.mfx_shown_type, t.mfx_bypassed, int(t.mfx("dry")), int(t.mfx("chorus")),
                int(t.mfx("reverb")), list(t.mfx("params")[:32]))

    def _cho_view(self):
        """Resolved (type, level, toReverb, rate, depth, predelay, feedback)."""
        s = self._fx_edit_target("chorus", fetch=False).store
        return tuple(int(getattr(s, a)) for a in CHORUS_ATTRS)

    def _rev_view(self):
        """Resolved (type, level, predelay, time, damp, diffusion, tone)."""
        s = self._fx_edit_target("reverb", fetch=False).store
        return tuple(int(getattr(s, a)) for a in REVERB_ATTRS)

    @pyqtSlot(str)
    def setSoundMode(self, mode: str) -> None:
        """Switch synth sound mode PATCH/PERFORM (Setup 01 00 00 00).

        The synth keeps separate patch and performance memories, so the app is
        the truth for both: entering PERFORM pushes the app's performance, and
        entering PATCH pushes the sound the editors show (the edited part).
        Edited parts are read back before leaving PERFORM.
        """
        m = str(mode or "").upper()
        if m not in ("PATCH", "PERFORM"):
            return
        prev = str(getattr(self, "_sound_mode", "")).upper()
        juno = self.juno
        if juno is not None:
            origin = getattr(self, "_patch_origin", None)
            self._patch_origin = None
            if prev == "PATCH" and m == "PERFORM" and origin is not None:
                self._fold_patch_edits_into_part(juno, origin)
            edited_image = None
            if prev == "PERFORM" and m == "PATCH":
                if any(p.modified for p in self.patch_state.perf_parts):
                    try:
                        self._part_snapshots = self._capture_part_snapshots()
                    except Exception as e:
                        logger.debug(f"setSoundMode: part snapshot failed: {e}")
                edited_image = self._read_part_image(self.activePerfPart)
                if not isinstance(edited_image, PatchState):
                    edited_image = None
            try:
                juno.set_sound_mode(SoundMode[m])
            except Exception as e:
                logger.debug(f"setSoundMode: synth write failed: {e}")
            if edited_image is not None:
                try:
                    juno.write_patch_regions(edited_image, ADDR_TEMP_PATCH_PART_1)
                except Exception as e:
                    logger.debug(f"setSoundMode: patch push failed: {e}")
                # Editors show exactly what PATCH mode now sounds
                self._apply_patch_state_to_editors(edited_image, self.activePerfPart)
                # Edits made in PATCH mode follow the sound back to this part,
                # unless another sound is loaded meanwhile (state/common replaced).
                self._patch_origin = (self.activePerfPart, edited_image,
                                      self.patch_state, self.patch_state.common)
            if m == "PERFORM" and prev != "PERFORM":
                try:
                    self._queue_push_jobs(self._perf_push_jobs(), replace=True)
                except Exception as e:
                    logger.debug(f"setSoundMode: performance push failed: {e}")
        if m != str(getattr(self, "_sound_mode", "")).upper():
            # Bases belong to one mode's sounds; re-capture them in the new one
            self._resetMacroBases()
        self._sound_mode = m
        self.patch_state.sound_mode = m
        self._capture_loaded()
        self.patchInfoChanged.emit(self._patch_name, self._sound_mode)
        self.perfPartsChanged.emit()
        try:
            self._emit_fx_editor_signals()
        except Exception:
            pass

    def _fold_patch_edits_into_part(self, juno, origin) -> None:
        """PATCH -> PERFORM: an edited PATCH-mode sound becomes its part's edited sound.

        Only when the PATCH-mode sound still descends from the part (no load
        replaced the app's state). Compares the synth's temp patch with the
        image pushed on entry, so panel edits count too. The performance push
        that follows sends the new snapshot into the part.
        """
        part_index, image, state_obj, common_obj = origin
        if self.patch_state is not state_obj or self.patch_state.common is not common_obj:
            return
        try:
            current = juno.read_patch_at(ADDR_TEMP_PATCH_PART_1)
            if not juno.patch_image_mismatches(image, current.raw_regions):
                return
            self._part_snapshots[str(part_index)] = patch_state_to_dict(current)
            self.patch_state.perf_parts[int(part_index) - 1].modified = True
            logger.info(f"PATCH-mode edits carried into part {part_index}")
        except Exception as e:
            logger.debug(f"fold patch edits: {e}")

    @pyqtSlot(int)
    def setEditingPerfMfx(self, slot: int) -> None:
        """Editing radio: which shared MFX the MFX Studio shows/edits (1..3)."""
        self._editing_perf_mfx = max(1, min(3, int(slot)))
        self._fx_target("mfx", fetch=True)
        self._emit_fx_editor_signals()

    @pyqtSlot(str, int)
    def setPerfSource(self, which: str, origin: int) -> None:
        """Set FX origin: which mfx1/mfx2/mfx3/chorus/reverb, origin 0=PERFORM 1..16=PARTn."""
        o = max(0, min(16, int(origin)))
        fx = getattr(self.patch_state, "perf_fx", None)
        if fx is not None:
            k = str(which or "").lower()
            try:
                if k == "mfx1": fx.mfx1.source = o
                elif k == "mfx2": fx.mfx2.source = o
                elif k == "mfx3": fx.mfx3.source = o
                elif k in ("chorus", "cho"): fx.chorus_source = o
                elif k in ("reverb", "rev"): fx.reverb_source = o
            except Exception:
                pass
        juno = self.juno
        if juno is not None:
            try:
                if hasattr(juno, "set_perf_source"):
                    juno.set_perf_source(str(which), o)
            except Exception as e:
                logger.debug(f"setPerfSource: synth write failed: {e}")
        try:
            if o != 0:
                self._ensure_part_fx_cache(o)
            self._emit_fx_editor_signals()
        except Exception:
            pass

    @pyqtSlot(int)
    def setPerfStructure(self, structure: int) -> None:
        """Set MFX Structure TYPE01..16 (0..15 on the wire)."""
        fx = getattr(self.patch_state, "perf_fx", None)
        if fx is not None:
            fx.mfx_structure = max(0, min(15, int(structure)))
        juno = self.juno
        if juno is not None:
            try:
                if hasattr(juno, "set_perf_structure"):
                    juno.set_perf_structure(int(structure))
            except Exception as e:
                logger.debug(f"setPerfStructure: synth write failed: {e}")
        try:
            self.perfFxChanged.emit()
        except Exception:
            pass

    @pyqtSlot(int, int, int, int, int)
    def setPerfMfx(self, slot: int, mfx_type: int, dry: int, chorus: int, reverb: int) -> None:
        """Rail MFX card write: targets the sounding processor (origin-resolved).

        PERFORM-owned slots write Performance Common; PART-sourced slots write
        that part's patch (same as MFX Studio would).
        """
        s = max(1, min(3, int(slot)))
        t = self._fx_target("mfx", slot=s, fetch=True)
        if t.store is None:  # the part could not be read: the rail shows the slot
            t = FxTarget("perf", s, self._perf_slot(s))
        values = {"type": max(0, min(80, int(mfx_type))), "dry": max(0, min(127, int(dry))),
                  "chorus": max(0, min(127, int(chorus))), "reverb": max(0, min(127, int(reverb)))}
        for name, v in values.items():
            t.set_mfx(name, v)
        if self.juno is not None:
            try:
                t.write_mfx(self.juno, values["type"], values["dry"], values["chorus"], values["reverb"])
            except Exception as e:
                logger.debug(f"setPerfMfx: synth write failed: {e}")
        for send in ("dry", "chorus", "reverb"):
            self._rebasePerfFx(f"mfx{s}", send, values[send])
        self._emit_fx_editor_signals()

    def setPerfMfxSlotSend(self, slot: int, send: str, val: int) -> None:
        """One send (dry/chorus/reverb) of MFX slot 1..3, origin-resolved (macros)."""
        s = max(1, min(3, int(slot)))
        if send not in ("dry", "chorus", "reverb"):
            return
        v = max(0, min(127, int(val)))
        t = self._fx_target("mfx", slot=s, fetch=True)
        if t.store is None:
            return
        t.set_mfx(send, v)
        if self.juno is not None:
            try:
                t.write_mfx(self.juno, **{send: v})
            except Exception as e:
                logger.debug(f"setPerfMfxSlotSend: synth write failed: {e}")
        self._rebasePerfFx(f"mfx{s}", send, v)
        self._emit_fx_editor_signals()

    @pyqtSlot(str)
    def copyOriginToPerform(self, which: str) -> bool:
        """Copy the sourced part's FX block to PERFORM and switch origin to PERFORM.

        Head-start for FX editing: the source part's patch MFX/chorus/reverb
        (not the edited part's) goes into the perf-common block, then
        source=PERFORM. MFX is copied on the synth byte for byte; chorus and
        reverb are written from the part's cached values. Offline without a
        cached copy of that part, only the source switches. Returns True on success.
        """
        k = {"cho": "chorus", "rev": "reverb"}.get(str(which or "").lower(), str(which or "").lower())
        if k not in ("mfx1", "mfx2", "mfx3", "chorus", "reverb"):
            return False
        fx = self.patch_state.perf_fx
        juno = self.juno
        if k.startswith("mfx"):
            s = int(k[3])
            src = self._origin_target("mfx", slot=s, fetch=True)
            if src.kind != "part":
                return True  # already PERFORM
            if juno is not None:
                try:
                    addr = add_address(temp_perf_patch_base(src.index), OFFSET_PATCH_COMMON_MFX)
                    raw = juno.request_data(addr, PERF_MFX_BLOCK_SIZE, timeout=1.0)
                    if raw is not None and len(raw) >= 4:
                        juno.send_data(perf_common_fx_base(s), list(bytes(raw)))
                except Exception as e:
                    logger.debug(f"copyOriginToPerform mfx HW copy failed: {e}")
            holder = self._perf_slot(s)
            if src.store is not None:
                dst = FxTarget("perf", s, holder)
                for name in ("type", "dry", "chorus", "reverb", "last"):
                    dst.set_mfx(name, int(src.mfx(name)))
                holder.params = list(src.mfx("params")[:32])
            holder.source = 0
        else:
            src = self._origin_target(k, fetch=True)
            if src.kind != "part":
                return True
            dst = FxTarget("perf", 0, fx)
            if src.store is not None:
                for a in CHORUS_ATTRS if k == "chorus" else REVERB_ATTRS:
                    setattr(fx, a, int(getattr(src.store, a)))
            setattr(fx, f"{k}_source", 0)
            if juno is not None:
                try:
                    if src.store is not None and k == "chorus":
                        dst.write_chorus(juno)
                        for param, val in (("predelay", fx.chorus_predelay), ("rate", fx.chorus_rate),
                                           ("depth", fx.chorus_depth), ("feedback", fx.chorus_feedback)):
                            dst.write_chorus_detail(juno, param, int(val))
                    elif src.store is not None:
                        dst.write_reverb(juno)
                        for param, val in (("predelay", fx.reverb_predelay), ("time", fx.reverb_time),
                                           ("damp", fx.reverb_damp), ("diffusion", fx.reverb_diffusion),
                                           ("tone", fx.reverb_tone)):
                            dst.write_reverb_detail(juno, param, int(val))
                except Exception as e:
                    logger.debug(f"copyOriginToPerform {k} HW failed: {e}")
        if juno is not None:
            try:
                juno.set_perf_source(k, 0)
            except Exception as e:
                logger.debug(f"copyOriginToPerform {k} source write failed: {e}")
        self._emit_fx_editor_signals()
        return True

    @pyqtSlot()
    @pyqtSlot(bool)
    def syncPerformanceFromSynth(self, async_mode: bool = False) -> None:
        """Read the performance name, 16 part mixer blocks and shared FX from
        the synth. async_mode reads on the job worker and applies on the UI
        thread. Never touches the patch editors directly (the edited part is
        re-read after)."""
        juno = self.juno
        if juno is None:
            logger.info("Cannot sync performance: no synthesizer connected.")
            return
        if self._sync_busy:
            logger.info("Hardware sync already in progress, ignoring request.")
            return
        self._set_sync_busy(True)
        kept_names = [p.patch_name or p.name for p in self.patch_state.perf_parts]
        active = int(self.patch_state.active_perf_part)

        def read(progress=None) -> dict:
            return self._read_synth_performance(juno, kept_names, active)

        if not async_mode:
            self._apply_synth_performance(read(), wait_editors=True)
        elif not self._start_job("sync", "Reading the performance…", read,
                                 done=self._apply_synth_performance):
            logger.info("Sync skipped: another synth job is running.")
            self._set_sync_busy(False)

    def _read_synth_performance(self, juno, kept_names: list, active: int) -> dict:
        """The synth's performance name, parts (names resolved) and FX (worker)."""
        out: dict = {}
        try:
            out["name"] = juno.get_perf_name(timeout=1.0)
        except Exception as e:
            logger.debug(f"syncPerformance: name read failed: {e}")
        try:
            parts = juno.get_perf_parts(timeout=1.0)
            if parts and len(parts) == 16:
                repo = self._librarian_repo
                for i, p in enumerate(parts):
                    if repo is not None:
                        p.patch_name = repo.resolve_patch_name(p.patch_msb, p.patch_lsb, p.patch_pc)
                    # The edited part, or one the library doesn't know: ask the synth
                    if p.part_index == active or not p.patch_name:
                        try:
                            p.patch_name = juno.get_perf_part_patch_name(p.part_index, timeout=0.25) \
                                or p.patch_name
                        except Exception as e:
                            logger.debug(f"part {p.part_index} name read failed: {e}")
                    if not p.patch_name and kept_names[i] and not kept_names[i].startswith("Part "):
                        p.patch_name = kept_names[i]
                    p.patch_name = p.patch_name or f"Part {p.part_index}"
                out["parts"] = parts
        except Exception as e:
            logger.debug(f"syncPerformance: parts read failed: {e}")
        try:
            out["fx"] = juno.get_perf_fx(timeout=1.0)
        except Exception as e:
            logger.debug(f"syncPerformance: fx read failed: {e}")
        return out

    def _apply_synth_performance(self, out, wait_editors: bool = False) -> None:
        """Take a performance read from the synth into the app (UI thread)."""
        try:
            if not isinstance(out, dict):
                return
            name = out.get("name")
            if isinstance(name, str) and name:
                self.patch_state.perf_name = name[:12]
                self._patch_name = name
            if out.get("parts"):
                self.patch_state.perf_parts = out["parts"]
            if out.get("fx") is not None:
                self.patch_state.perf_fx = out["fx"]
            self._sound_mode = "PERFORM"
            self.patch_state.sound_mode = "PERFORM"
            self.patchInfoChanged.emit(self._patch_name, self._sound_mode)
            self.perfPartsChanged.emit()
            self._emit_fx_editor_signals()
            self._refresh_editors_for_part(self.patch_state.active_perf_part, async_mode=not wait_editors)
        finally:
            self._set_sync_busy(False)

    @pyqtSlot()
    def initPerformance(self) -> None:
        """Reset the temporary performance to a fresh song (RAM only, nothing saved).

        P1 plays the JUNO SPECTRE template and P2 the factory grand piano, both
        Kbd-on so they layer. P10 gets a drum kit (Kbd off) for the sequencer's
        drum track. Other parts keep their sounds; every part's mixer, routing
        and Kbd switch go back to defaults, as do the shared MFX, chorus and
        reverb. The sequencer song is cleared (tracks, clips, tempo).
        """

        logger.info("Initializing performance in RAM to INIT PERF...")
        state = PatchState.from_template_file() or PatchState()
        state.sound_mode = "PERFORM"
        state.perf_name = INIT_PERF_NAME
        state.active_perf_part = 1
        state.perf_fx = PerfFxState()

        old_parts = self.patch_state.perf_parts
        old_snaps = getattr(self, "_part_snapshots", None) or {}
        snaps = {"1": patch_state_to_dict(state)}
        parts = []
        for i in range(1, 17):
            p = PerfPartState(part_index=i, name=f"Part {i}", zone_switch=i in (1, INIT_PERF_PIANO_PART))
            if i == 1:
                # Sounds from the template image pushed below, not from a slot
                p.patch_name = state.common.name
                p.modified = True
                p.memory_only = True
            elif i in (INIT_PERF_PIANO_PART, INIT_PERF_DRUM_PART):
                ref = INIT_PERF_PIANO if i == INIT_PERF_PIANO_PART else INIT_PERF_DRUMS
                p.patch_msb, p.patch_lsb, p.patch_pc, p.patch_name = ref
            elif i - 1 < len(old_parts):
                o = old_parts[i - 1]
                p.patch_msb, p.patch_lsb, p.patch_pc = o.patch_msb, o.patch_lsb, o.patch_pc
                p.patch_name, p.patch_file, p.modified = o.patch_name, o.patch_file, o.modified
                p.memory_only = o.memory_only
                if (p.patch_file or p.modified) and isinstance(old_snaps.get(str(i)), dict):
                    snaps[str(i)] = old_snaps[str(i)]
            parts.append(p)
        state.perf_parts = parts

        motion_was_playing = self.vector.motion.state == RecorderState.PLAYING
        if motion_was_playing:
            self.vector.motion.pause()
            self.transportStateChanged.emit(self.vector.motion.state.value)
        try:
            with self.vector.hold_hardware_writes():
                if not self._apply_song_state(patch_state_to_dict(state), INIT_PERF_NAME, snaps):
                    return
                self.patch_state.macros = state.macros
                self._resetMacroBases()
                self._push_perf_fx_details()
                self._reset_vector_to_patch_state()
        finally:
            if motion_was_playing and self.vector.motion.state != RecorderState.PLAYING:
                self.vector.motion.play()
                self.transportStateChanged.emit(self.vector.motion.state.value)

        self._restore_song_sequence(default_sequencer_song().to_dict())
        if hasattr(self, "seqSelectTrack"):
            self.seqSelectTrack(0)
        self._emit_all_state_signals()
        self.perfPartsChanged.emit()
        try:
            self._emit_fx_editor_signals()
        except Exception as e:
            logger.debug(f"initPerformance: fx editor signal emit failed: {e}")
        self._clear_current_ref()  # fresh RAM performance: no slot or file origin
        self.patchInitialized.emit()
        logger.info("Performance initialization complete.")

    def _push_perf_fx_details(self) -> None:
        """Send the shared chorus/reverb detail parameters (song loads send type/level only)."""
        juno = self.juno
        fx = getattr(self.patch_state, "perf_fx", None)
        if juno is None or fx is None:
            return
        try:
            for param, val in (("predelay", fx.chorus_predelay), ("rate", fx.chorus_rate),
                               ("depth", fx.chorus_depth), ("feedback", fx.chorus_feedback)):
                juno.set_perf_chorus_param(param, int(val))
            for param, val in (("predelay", fx.reverb_predelay), ("time", fx.reverb_time),
                               ("damp", fx.reverb_damp), ("diffusion", fx.reverb_diffusion),
                               ("tone", fx.reverb_tone)):
                juno.set_perf_reverb_param(param, int(val))
        except Exception as e:
            logger.debug(f"perf fx detail push failed: {e}")

    @pyqtProperty(int, notify=librarianPickChanged)
    def librarianPickTarget(self) -> int:
        return self._pick_target

    @pyqtSlot(int)
    def openPartPicker(self, part_index: int) -> None:
        """Open the Librarian to pick a patch for performance part 1..16."""
        if 1 <= int(part_index) <= 16:
            self._pick_target = int(part_index)
            self.editPerfPart(int(part_index))
            self.librarianPickChanged.emit()
            self.setActiveView("LIBRARIAN")

    @pyqtSlot(int, int, int, str, str, str, result=bool)
    def pickPartPatch(self, msb: int, lsb: int, pc: int,
                      path: str, name: str, kind: str) -> bool:
        """Assign the picked library row to the pick-target part.

        Hardware-resolvable rows select via Bank/PC; Pi-only files queue a
        background image push. Stays in the Librarian, still picking for the
        same part; OK proposes the mixer.
        """
        target = int(self._pick_target)
        if not 1 <= target <= 16:
            return False
        if str(kind or "").lower() in ("performance", "playlist"):
            return False  # containers can't sound inside a part
        part = self.patch_state.perf_parts[target - 1]
        display = str(name or "")[:24] or f"Part {target}"
        file_path = str(path or "")
        is_file = file_path.endswith(".spectre")
        juno = self.juno
        try:
            if int(msb) >= 0:
                # Hardware-resolvable (slot or file with synth_ref).
                part.patch_msb, part.patch_lsb, part.patch_pc = int(msb), int(lsb), int(pc)
                part.patch_name = display
                part.patch_file = file_path if is_file else ""
                part.modified = False
                part.memory_only = False
                self._part_snapshots.pop(str(target), None)
                if juno is not None:
                    try:
                        juno.set_perf_part_patch(target, int(msb), int(lsb), int(pc))
                    except Exception as e:
                        logger.debug(f"pickPartPatch: part select failed: {e}")
            elif is_file:
                # Pi-only file: queue its image into the part buffer (background,
                # with progress) and remember the link + a snapshot fallback.
                loaded = load_spectre(file_path)
                ref = loaded.get("synth_ref") or {}
                if ref.get("source") in ("factory", "synth-user"):
                    part.patch_msb = int(ref.get("msb", part.patch_msb))
                    part.patch_lsb = int(ref.get("lsb", part.patch_lsb))
                    part.patch_pc = int(ref.get("pc", part.patch_pc))
                    if juno is not None:
                        try:
                            juno.set_perf_part_patch(target, part.patch_msb,
                                                     part.patch_lsb, part.patch_pc)
                        except Exception as e:
                            logger.debug(f"pickPartPatch: part select failed: {e}")
                if juno is not None:
                    self._queue_push_jobs([("image", target, loaded["patch_state"])])
                try:
                    self._part_snapshots[str(target)] = patch_state_to_dict(loaded["patch_state"])
                except Exception as e:
                    logger.debug(f"pickPartPatch: snapshot failed: {e}")
                part.patch_name = display
                part.patch_file = file_path
                part.modified = False
                part.memory_only = False
            else:
                return False
        except Exception as e:
            logger.warning(f"pickPartPatch failed: {e}")
            return False
        self._forgetMacroPart(target)
        # A freshly assigned sound should answer the keyboard (Kbd switch on).
        if not part.zone_switch:
            self.setPartZoneSwitch(target, True)
        # Picking stays on: further taps audition other sounds on the same part
        # until OK (keep) or CANCEL (revert).
        self.perfPartsChanged.emit()
        try:
            self.refreshPartFileStatus()
        except Exception:
            pass
        self._pending_view = "PERFORMANCE"
        return True

    def _perf_push_jobs(self, state=None, part_snapshots: dict | None = None) -> list:
        """Jobs that send a performance (default: the app's) to the synth: the
        mixer, zones, shared FX and solo first (one 'perf' job, ~280 DT1s), then
        the part images of Pi-only / edited parts. Copies, so the UI can go on
        editing."""
        state = state if state is not None else self.patch_state
        snapshots = part_snapshots if part_snapshots is not None else self._part_snapshots
        jobs = [("perf", copy.deepcopy(state.perf_parts), copy.deepcopy(state.perf_fx))]
        for p in state.perf_parts:
            image = self._part_restore_image(p, snapshots)
            if image is not None:
                jobs.append(("image", p.part_index, image))
        return jobs

    @staticmethod
    def _send_perf_mixer(juno, parts: list, fx) -> None:
        """Send a performance's mixer, zones, shared FX and solo (push worker)."""
        for p in parts:
            try:
                juno.set_perf_part_patch(p.part_index, p.patch_msb, p.patch_lsb, p.patch_pc)
                juno.set_perf_part_level(p.part_index, p.volume)
                juno.set_perf_part_pan(p.part_index, p.pan)
                juno.set_perf_part_mute(p.part_index, p.muted)
                juno.set_perf_part_fx(p.part_index, dry=p.dry_send, chorus=p.chorus_send,
                                      reverb=p.reverb_send)
                juno.set_perf_part_output(p.part_index, assign=p.output_assign,
                                          mfx_select=p.mfx_select)
                juno.set_perf_zone(p.part_index, p.key_low, p.key_high, p.zone_switch, p.zone_octave)
            except Exception as e:
                logger.debug(f"perf push: part {p.part_index} push failed: {e}")
                return
        try:
            for which, origin in (("mfx1", fx.mfx1.source), ("mfx2", fx.mfx2.source),
                                  ("mfx3", fx.mfx3.source), ("chorus", fx.chorus_source),
                                  ("reverb", fx.reverb_source)):
                juno.set_perf_source(which, int(origin))
            juno.set_perf_structure(int(fx.mfx_structure))
            for s, slot in ((1, fx.mfx1), (2, fx.mfx2), (3, fx.mfx3)):
                juno.set_perf_mfx(s, mfx_type=int(slot.mfx_type), dry_send=int(slot.dry_send),
                                  chorus_send=int(slot.chorus_send), reverb_send=int(slot.reverb_send))
                if int(slot.source) == 0 and int(slot.mfx_type) > 0:
                    # Every parameter the type uses, zeros included: the synth
                    # may still hold another song's values there.
                    algo = get_mfx_algo(int(slot.mfx_type))
                    n = len(algo.get("params", [])) if algo else 0
                    if n:
                        juno.set_perf_mfx_params_bulk(s, list(slot.params)[:n])
            juno.set_perf_chorus(int(fx.chorus_type), level=int(fx.chorus_level),
                                 output_select=int(fx.chorus_to_reverb))
            juno.set_perf_reverb(int(fx.reverb_type), level=int(fx.reverb_level))
            solos = [p.part_index for p in parts if p.solo]
            juno.set_perf_solo(solos[-1] if solos else 0)
        except Exception as e:
            logger.debug(f"perf push: shared FX push failed: {e}")

    def _apply_song_state(self, patch_dict: dict, entry_name: str = "",
                          part_snapshots: dict | None = None) -> bool:
        """Swap in a cached/loaded performance image and push the mixer live.

        Mixer selects + levels go synchronously (fast); part sound images for
        Pi-only/edited parts and file links restore in the background with progress.
        The song's own macros come with it (assignments, values and the bases
        they were saved against): the image already sounds base + macro, so
        nothing is recomputed.
        """
        self._forget_loaded()          # a new performance: new loaded values

        try:
            state = patch_state_from_dict(patch_dict)
        except Exception as e:
            logger.warning(f"song load: bad snapshot: {e}")
            return False
        self.patch_state = state
        self._macro_part_states = {}
        self._auto_forget()
        self.patch_state.sound_mode = "PERFORM"
        self._sound_mode = "PERFORM"
        self._patch_name = getattr(state, "perf_name", "") or entry_name or self._patch_name
        if isinstance(part_snapshots, dict):
            self._part_snapshots = {str(k): v for k, v in part_snapshots.items()
                                    if isinstance(v, dict)}
        juno = self.juno
        if juno is not None:
            try:
                juno.set_sound_mode(SoundMode.PERFORM)
            except Exception as e:
                logger.debug(f"song load: mode switch failed: {e}")
            jobs = self._perf_push_jobs()
            if state.raw_regions:
                active = max(1, min(16, int(state.active_perf_part)))
                jobs.append(("image", active, copy.deepcopy(state)))
            self._queue_push_jobs(jobs, replace=True)
        try:
            self.refreshPartFileStatus()
        except Exception:
            pass
        self._emit_all_state_signals()
        return True

    def _load_song(self, patch_dict: dict, name: str, extras: dict | None,
                   path: str = "", fallback_bpm: float | None = None) -> bool:
        """Make a saved song sound: the one path for setlist songs and song files.

        Stops the sequencer and sends a panic first, then the performance
        (mixer, FX, part sounds, macros), the sequence + tempo and the arp.
        `extras` is the file's spectre block (or a setlist entry, same keys);
        `path` is the song file it came from ('' for a snapshot).
        """
        extras = extras if isinstance(extras, dict) else {}
        if hasattr(self, "sequencer") and self.sequencer.is_playing:
            self.seqStop()
        midi = getattr(self.juno, "midi", None) if self.juno is not None else None
        if midi is not None:
            try:
                midi.send_all_notes_off(include_reset=True)
            except Exception as e:
                logger.debug(f"song load: panic failed: {e}")
        snaps = extras.get("part_snapshots")
        if not self._apply_song_state(patch_dict, name, snaps if isinstance(snaps, dict) else {}):
            return False
        seq_raw = extras.get("sequencer")
        if isinstance(seq_raw, dict):
            self._restore_song_sequence(seq_raw)
        elif fallback_bpm:
            self._apply_tempo(float(fallback_bpm))
        self._apply_arp_extras(extras)
        if path:
            self._set_current_file_ref(path, "performance")
        else:
            self._clear_current_ref()
        return True

    _ENGINE_VIEWS = ("JUNO PCM", "VECTOR", "WAVETABLE", "VA", "LIVE", "SEQUENCER", "SETLIST", "PERFORMANCE", "MACROS")

    @staticmethod
    def _engine_view_for(extras) -> str:
        """Saved engine view for a patch file (JUNO PCM fallback)."""
        try:
            v = str((extras or {}).get("engine_mode") or "JUNO PCM").upper().strip()
        except Exception:
            return "JUNO PCM"
        return v if v in PerformanceBridgeMixin._ENGINE_VIEWS else "JUNO PCM"

    def _set_current_file_ref(self, path: str, kind: str) -> None:
        self._current_ref = {"source": "file", "kind": kind, "path": str(path)}
        try:
            self.currentRefChanged.emit()
        except Exception:
            pass

    def _restore_song_sequence(self, seq_raw: dict) -> None:
        """Swap in a saved sequencer song (stops playback, applies its tempo)."""
        if not hasattr(self, "sequencer"):
            return
        try:
            song = SequencerSong.from_dict(seq_raw)
        except Exception as e:
            logger.warning(f"song load: bad sequence: {e}")
            return
        self.sequencer.stop()
        self.sequencer.song = song
        self._apply_tempo(song.bpm)
        if hasattr(self, "_seq_retarget_recorder"):
            self._seq_retarget_recorder()
        if hasattr(self, "_audio_song_changed"):
            self._audio_song_changed()
        self.seqTracksChanged.emit()
        self.seqActiveClipChanged.emit()
        self.seqStateChanged.emit()

    @pyqtSlot(str, result=bool)
    def loadSpectreFile(self, path: str) -> bool:
        """Load a Pi .spectre file so it actually sounds (stays in Librarian).

        kind=performance proposes PERFORMANCE on OK; patch-like kinds propose
        the saved engine view. The image is always DT1-pushed, so Pi-only
        files never degrade to a header rename.
        """
        self._forget_loaded()          # a new sound: new loaded values
        try:
            loaded = load_spectre(path)
        except Exception as e:
            logger.warning(f"loadSpectreFile failed for {path}: {e}")
            return False
        kind = str(loaded.get("kind") or "patch")
        if kind == "playlist":
            ok = self.loadSetlist(path)
            if ok:
                self._pending_view = "SETLIST"
            return ok
        if kind == "performance":
            # One file = the whole song: 16-part performance, part sounds,
            # macros and (when saved with one) the sequence + tempo.
            name = str((loaded.get("meta") or {}).get("name") or "")
            if not self._load_song(patch_state_to_dict(loaded["patch_state"]), name,
                                   loaded.get("spectre"), path=path):
                return False
            self._pending_view = "PERFORMANCE"
            return True
        # Single-patch sound: swap state, push image to the temp buffer.
        self.patch_state = loaded["patch_state"]
        self.patch_state.sound_mode = "PATCH"
        self._sound_mode = "PATCH"
        self._patch_name = self.patch_state.common.name
        juno = self.juno
        if juno is not None:
            try:
                juno.set_sound_mode(SoundMode.PATCH)
                juno.set_active_perf_part(1)
                juno.write_patch_regions(self.patch_state, ADDR_TEMP_PATCH_PART_1)
            except Exception as e:
                logger.debug(f"loadSpectreFile: synth push failed: {e}")
        self._apply_arp_extras(loaded.get("spectre"))
        self._refresh_tone_waves()
        self._set_current_file_ref(path, kind)
        self._emit_all_state_signals()
        self._pending_view = self._engine_view_for(loaded.get("spectre"))
        return True

