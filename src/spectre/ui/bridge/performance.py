"""Performance bridge mixin: 16-part mixer, performance FX, routing, and playlists."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from PyQt6.QtCore import pyqtProperty, pyqtSignal, pyqtSlot

from .base import BridgeBaseMixin

logger = logging.getLogger(__name__)


class PerformanceBridgeMixin(BridgeBaseMixin):
    """Performance 16-part mixer, common FX, part-pick mode, and live setlists."""

    perfPartsChanged = pyqtSignal()
    perfFxChanged = pyqtSignal()
    playlistChanged = pyqtSignal()
    librarianPickChanged = pyqtSignal()
    perfPushChanged = pyqtSignal(float)
    partFileStatusChanged = pyqtSignal()

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
            }
            for p in self.patch_state.perf_parts[:16]
        ]

    def _rail_mfx_entry(self, n: int) -> dict:
        """Rail card content: the sounding processor (origin-resolved)."""
        holder = self._perf_slot(n)
        source = int(getattr(holder, "source", 0)) if holder is not None else 0
        shown = {"type": 0, "drySend": 127, "chorusSend": 0, "reverbSend": 0}
        if source != 0 and self._in_perform():
            cached = self._part_cached(source)
            if cached is not None:
                m = cached["mfx"]
                shown = {"type": int(m["type"]), "drySend": int(m["dry"]),
                         "chorusSend": int(m["chorus"]), "reverbSend": int(m["reverb"])}
            elif holder is not None:
                shown = {"type": int(holder.mfx_type), "drySend": int(holder.dry_send),
                         "chorusSend": int(holder.chorus_send), "reverbSend": int(holder.reverb_send)}
        elif holder is not None:
            shown = {"type": int(holder.mfx_type), "drySend": int(holder.dry_send),
                     "chorusSend": int(holder.chorus_send), "reverbSend": int(holder.reverb_send)}
        return {"kind": f"MFX{n}", "slot": n, **shown, "source": source,
                "editing": int(getattr(self, "_editing_perf_mfx", 1)) == n}

    def _rail_cho_entry(self) -> dict:
        fx = getattr(self.patch_state, "perf_fx", None)
        source = int(getattr(fx, "chorus_source", 0)) if fx is not None else 0
        if source != 0 and self._in_perform():
            cached = self._part_cached(source)
            if cached is not None:
                c = cached["chorus"]
                return {"kind": "CHORUS", "type": int(c["type"]), "level": int(c["level"]),
                        "toReverb": int(c["toReverb"]), "source": source}
        return {"kind": "CHORUS", "type": int(fx.chorus_type),
                "level": int(fx.chorus_level), "toReverb": int(fx.chorus_to_reverb),
                "source": source} if fx is not None else {"kind": "CHORUS", "type": 0,
                "level": 0, "toReverb": 0, "source": 0}

    def _rail_rev_entry(self) -> dict:
        fx = getattr(self.patch_state, "perf_fx", None)
        source = int(getattr(fx, "reverb_source", 0)) if fx is not None else 0
        if source != 0 and self._in_perform():
            cached = self._part_cached(source)
            if cached is not None:
                r = cached["reverb"]
                return {"kind": "REVERB", "type": int(r["type"]), "level": int(r["level"]),
                        "source": source}
        return {"kind": "REVERB", "type": int(fx.reverb_type),
                "level": int(fx.reverb_level), "source": source} if fx is not None else {
                "kind": "REVERB", "type": 0, "level": 0, "source": 0}

    @pyqtProperty("QVariantList", notify=perfFxChanged)
    def perfFxSlots(self) -> list:
        """5 shared FX cards: MFX1-3 + chorus + reverb (origin-resolved content)."""
        fx = getattr(self.patch_state, "perf_fx", None)
        if fx is None:
            return []
        return [self._rail_mfx_entry(1), self._rail_mfx_entry(2),
                self._rail_mfx_entry(3), self._rail_cho_entry(),
                self._rail_rev_entry()]

    @pyqtProperty("QVariantMap", notify=perfFxChanged)
    def perfFxSources(self) -> dict:
        fx = getattr(self.patch_state, "perf_fx", None)
        if fx is None:
            return {"mfx1": 0, "mfx2": 0, "mfx3": 0, "chorus": 0, "reverb": 0, "structure": 0}
        return {"mfx1": int(fx.mfx1.source), "mfx2": int(fx.mfx2.source),
                "mfx3": int(fx.mfx3.source), "chorus": int(fx.chorus_source),
                "reverb": int(fx.reverb_source), "structure": int(fx.mfx_structure)}

    @pyqtProperty(int, notify=perfFxChanged)
    def editingPerfMfx(self) -> int:
        return max(1, min(3, int(getattr(self, "_editing_perf_mfx", 1))))

    @staticmethod
    def _origin_text(origin: int) -> str:
        return "PERFORM" if int(origin) == 0 else f"PART {int(origin)}"

    @pyqtProperty(str, notify=perfFxChanged)
    def mfxEditTargetLabel(self) -> str:
        """MFX Studio context chip: which MFX + origin it shows/edits (compact)."""
        tgt = self._mfx_target()
        if tgt[0] == "perf":
            return f"MFX{tgt[1]}\u00b7PERF"
        if tgt[0] == "part":
            s = max(1, min(3, int(getattr(self, "_editing_perf_mfx", 1))))
            return f"MFX{s}\u00b7P{tgt[1]}"
        return "PATCH"

    @pyqtProperty(str, notify=perfFxChanged)
    def choEditTargetLabel(self) -> str:
        """Master FX chorus context chip (compact)."""
        tgt = self._cho_target()
        if tgt[0] == "perf":
            return "CHO\u00b7PERF"
        if tgt[0] == "part":
            return f"CHO\u00b7P{tgt[1]}"
        return "PATCH"

    @pyqtProperty(str, notify=perfFxChanged)
    def revEditTargetLabel(self) -> str:
        """Master FX reverb context chip (compact)."""
        tgt = self._rev_target()
        if tgt[0] == "perf":
            return "REV\u00b7PERF"
        if tgt[0] == "part":
            return f"REV\u00b7P{tgt[1]}"
        return "PATCH"

    @pyqtProperty(int, notify=perfFxChanged)
    def perfStructure(self) -> int:
        fx = getattr(self.patch_state, "perf_fx", None)
        return int(getattr(fx, "mfx_structure", 0)) if fx is not None else 0

    @pyqtProperty(str, notify=perfPartsChanged)
    def perfName(self) -> str:
        return getattr(self.patch_state, "perf_name", "SPECTRE PERF")

    @pyqtProperty(int, notify=perfPartsChanged)
    def activePerfPart(self) -> int:
        return max(1, min(16, int(getattr(self.patch_state, "active_perf_part", 1))))

    @pyqtProperty(str, notify=perfPartsChanged)
    def perfContext(self) -> str:
        """Header context in PERFORM: 'PERFNAME / N-PATCHNAME', else ''."""
        if str(self._sound_mode).upper() != "PERFORM":
            return ""
        perf = str(getattr(self.patch_state, "perf_name", "") or self._patch_name or "")
        idx = max(1, min(16, int(getattr(self.patch_state, "active_perf_part", 1))))
        try:
            part = self.patch_state.perf_parts[idx - 1]
            pname = str(part.patch_name or part.name or f"Part {idx}")
        except Exception:
            pname = f"Part {idx}"
        if perf:
            return f"{perf} / {idx}-{pname}"
        return f"{idx}-{pname}"

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
        from ...core.spectre_format import load_spectre, patch_state_to_dict, snapshot_hash_of
        statuses = []
        for i, part in enumerate(self.patch_state.perf_parts[:16]):
            link = str(getattr(part, "patch_file", "") or "")
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
                live = patch_state_to_dict(load_spectre(link)["patch_state"])
                statuses.append("ok" if snapshot_hash_of(live) == snapshot_hash_of(snap) else "updated")
            except Exception:
                statuses.append("missing" if snap is not None else "missing-dead")
        self._part_file_status = statuses
        try:
            self.partFileStatusChanged.emit()
        except Exception:
            pass

    def _queue_push_jobs(self, jobs: list) -> None:
        """Run part-sound jobs in a worker thread (images are slow on SysEx).

        Job: ('image', part_index, PatchState) or ('select', part_index, msb, lsb, pc).
        """
        if not jobs:
            return
        if float(self._perf_push_progress) >= 0.0:
            logger.info("push already running; new jobs dropped")
            return
        self._set_push_progress(0.0)
        worker = threading.Thread(target=self._push_parts_worker, args=(list(jobs),), daemon=True)
        worker.start()

    def _push_parts_worker(self, jobs: list) -> None:
        juno = self.juno
        try:
            if juno is None:
                return
            total = max(1, len(jobs))
            with self._push_lock:
                for done, job in enumerate(jobs):
                    try:
                        if job[0] == "image":
                            _, part, state = job
                            fails = juno.push_patch_to_perf_part(state, int(part))
                            if fails:
                                logger.warning(f"part {part}: {fails} DT1 failures")
                        elif job[0] == "select":
                            _, part, msb, lsb, pc = job
                            juno.set_perf_part_patch(int(part), int(msb), int(lsb), int(pc))
                    except Exception as e:
                        logger.debug(f"part push job failed: {e}")
                    self._set_push_progress((done + 1) / total)
        finally:
            self._set_push_progress(-1.0)
            try:
                self.refreshPartFileStatus()
            except Exception:
                pass

    @pyqtSlot(int, result=bool)
    def refreshPartFile(self, part_index: int) -> bool:
        """Re-push a file-linked part: fresh file image when healthy, else snapshot."""
        if not 1 <= int(part_index) <= 16:
            return False
        from ...core.spectre_format import load_spectre, patch_state_from_dict
        part = self.patch_state.perf_parts[int(part_index) - 1]
        link = str(getattr(part, "patch_file", "") or "")
        snap = (self._part_snapshots or {}).get(str(part.part_index))
        state = None
        if link and Path(link).is_file():
            try:
                state = load_spectre(link)["patch_state"]
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

    def _part_zone_channel(self, part_index: int) -> int:
        """Performance zone index (zones 1..16 at 0x50..0x5F correspond directly to parts 1..16)."""
        return max(1, min(16, int(part_index)))

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
            for idx in range(min(4, len(state.tones))):
                t = state.tones[idx]
                if idx < len(self._tone_waves):
                    self._tone_waves[idx] = (t.wave_bank_l, t.wave_num_l)
            if len(state.tones) >= 4:
                self.engine.tone_levels = (
                    state.tones[0].level,
                    state.tones[1].level,
                    state.tones[2].level,
                    state.tones[3].level,
                )
                self.patch_state.custom_detune_cache = [t.fine_tune for t in state.tones]
            if hasattr(self, "_wave_catalog") and hasattr(self, "_tone_waves"):
                self._cached_tone_wave_data = [
                    self._wave_catalog.get_wave(b, n) for b, n in self._tone_waves
                ]
        except Exception as e:
            logger.debug(f"_apply_patch_state_to_editors error: {e}")

        try:
            self._part_fx_cache[int(part_index)] = self._cache_from_effects(state.effects)
        except Exception:
            pass

        try:
            self._emit_all_state_signals()
        except Exception as e:
            logger.debug(f"_emit_all_state_signals error: {e}")
        self.perfPartsChanged.emit()

    def _refresh_editors_for_part(self, part_index: int, async_mode: bool = True) -> None:
        """Reload tones/effects for the newly selected part.

        1. Instantly loads from local snapshot/file if cached.
        2. Queries hardware temp patch buffer (11..14..) asynchronously.
        3. Updates wave and engine levels and emits _emit_all_state_signals so all QML editors update.
        """
        p_idx = int(part_index)
        if not 1 <= p_idx <= 16:
            return

        # Fast-path: if we have a snapshot or linked file for this part, apply it immediately
        snap = (getattr(self, "_part_snapshots", None) or {}).get(str(p_idx))
        link = ""
        if hasattr(self, "patch_state") and hasattr(self.patch_state, "perf_parts"):
            if 0 <= p_idx - 1 < len(self.patch_state.perf_parts):
                link = str(getattr(self.patch_state.perf_parts[p_idx - 1], "patch_file", "") or "")

        cached_state = None
        if link and Path(link).is_file():
            try:
                from ...core.spectre_format import load_spectre
                cached_state = load_spectre(link).get("patch_state")
            except Exception as e:
                logger.debug(f"_refresh_editors_for_part: cached link unreadable: {e}")
        if cached_state is None and isinstance(snap, dict):
            try:
                from ...core.spectre_format import patch_state_from_dict
                cached_state = patch_state_from_dict(snap)
            except Exception as e:
                logger.debug(f"_refresh_editors_for_part: cached snap unreadable: {e}")

        if cached_state is not None:
            self._apply_patch_state_to_editors(cached_state, p_idx)

        juno = self.juno
        if juno is None or not hasattr(juno, "read_full_patch"):
            return

        def _worker():
            try:
                state = juno.read_full_patch(timeout=1.5)
                if state is not None:
                    # Guard against user switching part while reading
                    if getattr(self.patch_state, "active_perf_part", 1) == p_idx:
                        self._apply_patch_state_to_editors(state, p_idx)
            except Exception as e:
                logger.debug(f"_refresh_editors_for_part worker failed: {e}")

        if async_mode:
            threading.Thread(target=_worker, daemon=True).start()
        else:
            _worker()

    @pyqtSlot(int)
    def editPerfPart(self, part_index: int) -> None:
        """Select which performance part patch editors target (deep edit)."""
        if 1 <= part_index <= 16:
            self.patch_state.active_perf_part = part_index
            juno = self.juno
            if juno is not None:
                try:
                    juno.set_active_perf_part(part_index)
                except Exception as e:
                    logger.debug(f"editPerfPart: {e}")
            self.perfPartsChanged.emit()
            self._refresh_editors_for_part(int(part_index), async_mode=True)

    def _in_perform(self) -> bool:
        return str(getattr(self, "_sound_mode", "PATCH")).upper() == "PERFORM"

    def _perf_slot(self, slot: int):
        fx = getattr(self.patch_state, "perf_fx", None)
        if fx is None:
            return None
        s = max(1, min(3, int(slot)))
        return (fx.mfx1, fx.mfx2, fx.mfx3)[s - 1]

    def _mfx_target(self):
        """Where MFX Studio edits: ('perf', slot) | ('part', n) | ('patch',)."""
        if not self._in_perform():
            return ("patch",)
        s = max(1, min(3, int(getattr(self, "_editing_perf_mfx", 1))))
        holder = self._perf_slot(s)
        origin = int(getattr(holder, "source", 0)) if holder is not None else 0
        if origin == 0:
            return ("perf", s)
        return ("part", max(1, min(16, origin)))

    def _cho_target(self):
        """Where Master FX chorus edits: ('perf',) | ('part', n) | ('patch',)."""
        if not self._in_perform():
            return ("patch",)
        fx = getattr(self.patch_state, "perf_fx", None)
        origin = int(getattr(fx, "chorus_source", 0)) if fx is not None else 0
        if origin == 0:
            return ("perf",)
        return ("part", max(1, min(16, origin)))

    def _rev_target(self):
        """Where Master FX reverb edits: ('perf',) | ('part', n) | ('patch',)."""
        if not self._in_perform():
            return ("patch",)
        fx = getattr(self.patch_state, "perf_fx", None)
        origin = int(getattr(fx, "reverb_source", 0)) if fx is not None else 0
        if origin == 0:
            return ("perf",)
        return ("part", max(1, min(16, origin)))

    @staticmethod
    def _cache_from_effects(eff) -> dict:
        """Build a read_part_fx-shaped cache entry from an EffectsState."""
        try:
            params = list(eff.mfx_params[:32])
        except Exception:
            params = [0] * 32
        return {
            "mfx": {"type": int(eff.mfx_type), "dry": int(eff.mfx_dry_send),
                    "chorus": int(eff.mfx_chorus_send), "reverb": int(eff.mfx_reverb_send),
                    "params": params + [0] * (32 - len(params)),
                    "lastActive": int(getattr(eff, "mfx_last_active_type", 15) or 15)},
            "chorus": {"type": int(eff.chorus_type), "level": int(eff.chorus_level),
                       "toReverb": int(eff.chorus_to_reverb),
                       "predelay": int(eff.chorus_predelay), "rate": int(eff.chorus_rate),
                       "depth": int(eff.chorus_depth), "feedback": int(eff.chorus_feedback)},
            "reverb": {"type": int(eff.reverb_type), "level": int(eff.reverb_level),
                       "predelay": int(eff.reverb_predelay), "time": int(eff.reverb_time),
                       "damp": int(eff.reverb_damp), "diffusion": int(eff.reverb_diffusion),
                       "tone": int(eff.reverb_tone)},
        }

    def _refresh_part_fx_cache(self, part_index: int) -> bool:
        """Best-effort hardware read of one part-patch FX into the cache."""
        juno = self.juno
        if juno is None or not hasattr(juno, "read_part_fx"):
            return False
        try:
            data = juno.read_part_fx(int(part_index), timeout=1.0)
            if isinstance(data, dict) and "mfx" in data:
                data["mfx"].setdefault("lastActive", int(data["mfx"].get("type") or 15) or 15)
                if int(data["mfx"].get("type") or 0) > 0:
                    data["mfx"]["lastActive"] = int(data["mfx"]["type"])
                self._part_fx_cache[int(part_index)] = data
                return True
        except Exception as e:
            logger.debug(f"_refresh_part_fx_cache({part_index}) failed: {e}")
        return False

    def _ensure_part_fx_cache(self, part_index: int) -> None:
        """Fill the cache for a PARTn target (no-op when already cached)."""
        n = max(1, min(16, int(part_index)))
        if n not in self._part_fx_cache:
            self._refresh_part_fx_cache(n)

    def _part_cached(self, part_index: int):
        return self._part_fx_cache.get(max(1, min(16, int(part_index))))

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
        tgt = self._mfx_target()
        eff = self.patch_state.effects
        if tgt[0] == "perf":
            holder = self._perf_slot(tgt[1])
            mtype = int(holder.mfx_type)
            last = int(getattr(holder, "last_active_type", 15) or 15)
            try:
                params = list(holder.params[:32])
            except Exception:
                params = [0] * 32
            shown = mtype if mtype != 0 else last
            return (shown, mtype == 0, int(holder.dry_send),
                    int(holder.chorus_send), int(holder.reverb_send), params)
        if tgt[0] == "part":
            cached = self._part_cached(tgt[1])
            if cached is not None:
                m = cached["mfx"]
                shown = int(m["type"]) if int(m["type"]) != 0 else int(m.get("lastActive") or 15)
                return (shown, int(m["type"]) == 0, int(m["dry"]),
                        int(m["chorus"]), int(m["reverb"]), list(m["params"][:32]))
        shown = eff.mfx_type if not eff.mfx_bypassed else eff.mfx_last_active_type
        return (shown, bool(eff.mfx_bypassed), int(eff.mfx_dry_send),
                int(eff.mfx_chorus_send), int(eff.mfx_reverb_send),
                list(eff.mfx_params[:32]))

    def _cho_view(self):
        """Resolved (type, level, toReverb, rate, depth, predelay, feedback)."""
        tgt = self._cho_target()
        eff = self.patch_state.effects
        if tgt[0] == "perf":
            fx = self.patch_state.perf_fx
            return (int(fx.chorus_type), int(fx.chorus_level), int(fx.chorus_to_reverb),
                    int(fx.chorus_rate), int(fx.chorus_depth),
                    int(fx.chorus_predelay), int(fx.chorus_feedback))
        if tgt[0] == "part":
            cached = self._part_cached(tgt[1])
            if cached is not None:
                c = cached["chorus"]
                return (int(c["type"]), int(c["level"]), int(c["toReverb"]),
                        int(c["rate"]), int(c["depth"]),
                        int(c["predelay"]), int(c["feedback"]))
        return (int(eff.chorus_type), int(eff.chorus_level), int(eff.chorus_to_reverb),
                int(eff.chorus_rate), int(eff.chorus_depth),
                int(eff.chorus_predelay), int(eff.chorus_feedback))

    def _rev_view(self):
        """Resolved (type, level, predelay, time, damp, diffusion, tone)."""
        tgt = self._rev_target()
        eff = self.patch_state.effects
        if tgt[0] == "perf":
            fx = self.patch_state.perf_fx
            return (int(fx.reverb_type), int(fx.reverb_level),
                    int(fx.reverb_predelay), int(fx.reverb_time),
                    int(fx.reverb_damp), int(fx.reverb_diffusion), int(fx.reverb_tone))
        if tgt[0] == "part":
            cached = self._part_cached(tgt[1])
            if cached is not None:
                r = cached["reverb"]
                return (int(r["type"]), int(r["level"]), int(r["predelay"]),
                        int(r["time"]), int(r["damp"]),
                        int(r["diffusion"]), int(r["tone"]))
        return (int(eff.reverb_type), int(eff.reverb_level),
                int(eff.reverb_predelay), int(eff.reverb_time),
                int(eff.reverb_damp), int(eff.reverb_diffusion), int(eff.reverb_tone))

    @pyqtSlot(str)
    def setSoundMode(self, mode: str) -> None:
        """Switch synth sound mode PATCH/PERFORM (Setup 01 00 00 00)."""
        m = str(mode or "").upper()
        if m not in ("PATCH", "PERFORM"):
            return
        juno = self.juno
        if juno is not None:
            try:
                from ...core.protocol import SoundMode
                juno.set_sound_mode(SoundMode[m])
            except Exception as e:
                logger.debug(f"setSoundMode: synth write failed: {e}")
        self._sound_mode = m
        self.patch_state.sound_mode = m
        self.patchInfoChanged.emit(self._patch_name, self._sound_mode)
        self.perfPartsChanged.emit()
        try:
            self._emit_fx_editor_signals()
        except Exception:
            pass

    @pyqtSlot(int)
    def setEditingPerfMfx(self, slot: int) -> None:
        """Editing radio: which shared MFX the MFX Studio shows/edits (1..3)."""
        self._editing_perf_mfx = max(1, min(3, int(slot)))
        try:
            tgt = self._mfx_target()
            if tgt[0] == "part":
                self._ensure_part_fx_cache(tgt[1])
            self._emit_fx_editor_signals()
        except Exception:
            pass

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
        fx = getattr(self.patch_state, "perf_fx", None)
        holder = (fx.mfx1, fx.mfx2, fx.mfx3)[s - 1] if fx is not None else None
        origin = int(getattr(holder, "source", 0)) if holder is not None else 0
        juno = self.juno
        if self._in_perform() and origin != 0:
            cached = self._part_cached(origin)
            if cached is None:
                self._ensure_part_fx_cache(origin)
                cached = self._part_cached(origin)
            if cached is not None:
                m = cached["mfx"]
                m["type"] = max(0, min(80, int(mfx_type)))
                m["dry"] = max(0, min(127, int(dry)))
                m["chorus"] = max(0, min(127, int(chorus)))
                m["reverb"] = max(0, min(127, int(reverb)))
                if juno is not None and hasattr(juno, "set_part_patch_mfx"):
                    try:
                        juno.set_part_patch_mfx(origin, mfx_type=m["type"], dry_send=m["dry"],
                                                chorus_send=m["chorus"], reverb_send=m["reverb"])
                    except Exception as e:
                        logger.debug(f"setPerfMfx: part synth write failed: {e}")
                self._emit_fx_editor_signals()
                return
        if holder is not None:
            holder.mfx_type = max(0, min(80, int(mfx_type)))
            holder.dry_send = max(0, min(127, int(dry)))
            holder.chorus_send = max(0, min(127, int(chorus)))
            holder.reverb_send = max(0, min(127, int(reverb)))
        if juno is not None:
            try:
                if hasattr(juno, "set_perf_mfx"):
                    juno.set_perf_mfx(s, mfx_type=int(mfx_type), dry_send=int(dry),
                                      chorus_send=int(chorus), reverb_send=int(reverb))
            except Exception as e:
                logger.debug(f"setPerfMfx: synth write failed: {e}")
        try:
            self.perfFxChanged.emit(); self.mfxParamsChanged.emit(); self.routingChanged.emit()
        except Exception:
            pass

    @pyqtSlot(str)
    def copyOriginToPerform(self, which: str) -> bool:
        """Copy current origin block to PERFORM and switch origin to PERFORM.

        Head-start for MFX editing: reads the sourced block (part patch when
        PARTn, perf-common when already PERFORM) and writes it into the
        perf-common block, then sets source=PERFORM. Returns True on success.
        Offline: copies state only.
        """
        k = str(which or "").lower()
        fx = getattr(self.patch_state, "perf_fx", None)
        juno = self.juno
        try:
            if k in ("mfx1", "mfx2", "mfx3"):
                s = {"mfx1": 1, "mfx2": 2, "mfx3": 3}[k]
                holder = (fx.mfx1, fx.mfx2, fx.mfx3)[s - 1] if fx is not None else None
                origin = int(getattr(holder, "source", 0)) if holder is not None else 0
                if origin == 0:
                    return True  # already PERFORM
                # Try hardware copy: part patch MFX -> perf common MFX slot.
                if juno is not None and hasattr(juno, "request_data"):
                    try:
                        from ...core.protocol import temp_perf_patch_base as _ppb
                        from ...core.sysex import OFFSET_PATCH_COMMON_MFX as _MFX
                        from ...core.sysex import PERF_MFX_BLOCK_SIZE as _SZ
                        from ...core.sysex import add_address as _add
                        src = _add(_ppb(origin), _MFX)
                        raw = juno.request_data(src, _SZ, timeout=1.0)
                        if raw is not None and len(raw) >= 4:
                            juno.send_data(__import__("src.spectre.core.sysex", fromlist=["perf_common_fx_base"]).perf_common_fx_base(s), list(bytes(raw)))
                    except Exception as e:
                        logger.debug(f"copyOriginToPerform mfx HW copy failed: {e}")
                # State copy: mirror active part editor MFX into the slot.
                if fx is not None and holder is not None:
                    try:
                        eff = self.patch_state.effects
                        holder.mfx_type = int(eff.mfx_type)
                        holder.dry_send = int(eff.mfx_dry_send)
                        holder.chorus_send = int(eff.mfx_chorus_send)
                        holder.reverb_send = int(eff.mfx_reverb_send)
                        holder.params = list(eff.mfx_params[:32])
                        holder.source = 0
                    except Exception:
                        holder.source = 0
                if juno is not None and hasattr(juno, "set_perf_source"):
                    try:
                        juno.set_perf_source(k, 0)
                    except Exception:
                        pass
                try:
                    self._emit_fx_editor_signals()
                except Exception:
                    pass
                return True
            elif k in ("chorus", "cho", "reverb", "rev"):
                is_cho = k in ("chorus", "cho")
                origin = int(fx.chorus_source if is_cho else fx.reverb_source) if fx is not None else 0
                if origin == 0:
                    return True
                if fx is not None:
                    try:
                        eff = self.patch_state.effects
                        if is_cho:
                            fx.chorus_type = int(eff.chorus_type); fx.chorus_level = int(eff.chorus_level)
                            fx.chorus_to_reverb = int(eff.chorus_to_reverb); fx.chorus_source = 0
                        else:
                            fx.reverb_type = int(eff.reverb_type); fx.reverb_level = int(eff.reverb_level)
                            fx.reverb_source = 0
                    except Exception:
                        pass
                if juno is not None:
                    try:
                        if is_cho and hasattr(juno, "set_perf_chorus") and fx is not None:
                            juno.set_perf_chorus(fx.chorus_type, level=fx.chorus_level,
                                                 output_select=fx.chorus_to_reverb)
                        elif not is_cho and hasattr(juno, "set_perf_reverb") and fx is not None:
                            juno.set_perf_reverb(fx.reverb_type, level=fx.reverb_level)
                        if hasattr(juno, "set_perf_source"):
                            juno.set_perf_source("chorus" if is_cho else "reverb", 0)
                    except Exception as e:
                        logger.debug(f"copyOriginToPerform {'cho' if is_cho else 'rev'} HW failed: {e}")
                try:
                    self._emit_fx_editor_signals()
                except Exception:
                    pass
                return True
        except Exception as e:
            logger.debug(f"copyOriginToPerform failed: {e}")
            return False
        return False

    @pyqtSlot()
    @pyqtSlot(bool)
    def syncPerformanceFromSynth(self, async_mode: bool = False) -> None:
        """Read performance name + 16 part mixer blocks from hardware.

        Disabled-safe offline (logs only). Never touches patch editors.
        """
        juno = self.juno
        if juno is None:
            logger.info("Cannot sync performance: no synthesizer connected.")
            return

        if getattr(self, "_sync_busy", False):
            logger.info("Hardware sync already in progress, ignoring request.")
            return

        def _do_sync() -> None:
            self._set_sync_busy(True)
            try:
                try:
                    name = juno.get_perf_name(timeout=1.0)
                    if isinstance(name, str) and name:
                        self.patch_state.perf_name = name[:12]
                        self._patch_name = name
                except Exception as e:
                    logger.debug(f"syncPerformance: name read failed: {e}")
                try:
                    repo = getattr(self, "_librarian_repo", None)
                    if repo is None:
                        try:
                            from ...librarian.repository import PatchRepository
                            repo = PatchRepository()
                        except Exception:
                            repo = None

                    parts = juno.get_perf_parts(timeout=1.0)
                    if parts and len(parts) == 16:
                        kept_names = [p.patch_name or p.name for p in self.patch_state.perf_parts]
                        self.patch_state.perf_parts = parts
                        for i, p in enumerate(self.patch_state.perf_parts):
                            # 1. Resolve from DB catalog (user + factory)
                            if repo is not None:
                                try:
                                    resolved = repo.resolve_patch_name(p.patch_msb, p.patch_lsb, p.patch_pc)
                                    if resolved:
                                        p.patch_name = resolved
                                except Exception as e:
                                    logger.debug(f"resolve_patch_name failed for part {p.part_index}: {e}")
                            # 2. For active part or if still empty, query live synth buffer if supported
                            if (p.part_index == self.patch_state.active_perf_part or not p.patch_name) and hasattr(juno, "get_perf_part_patch_name"):
                                try:
                                    live_name = juno.get_perf_part_patch_name(p.part_index, timeout=0.25)
                                    if live_name:
                                        p.patch_name = live_name
                                except Exception as e:
                                    logger.debug(f"get_perf_part_patch_name failed for part {p.part_index}: {e}")
                            # 3. Fallback to previously kept name if descriptive
                            if not p.patch_name and i < len(kept_names) and kept_names[i] and not kept_names[i].startswith("Part "):
                                p.patch_name = kept_names[i]
                            if not p.patch_name:
                                p.patch_name = f"Part {p.part_index}"
                except Exception as e:
                    logger.debug(f"syncPerformance: parts read failed: {e}")
                try:
                    if hasattr(juno, "get_perf_fx"):
                        fx = juno.get_perf_fx(timeout=1.0)
                        if fx is not None:
                            self.patch_state.perf_fx = fx
                except Exception as e:
                    logger.debug(f"syncPerformance: fx read failed: {e}")
                self._sound_mode = "PERFORM"
                self.patch_state.sound_mode = "PERFORM"
                self.patchInfoChanged.emit(self._patch_name, self._sound_mode)
                self.perfPartsChanged.emit()
                try:
                    self._emit_fx_editor_signals()
                except Exception as e:
                    logger.debug(f"syncPerformance: fx editor signal emit failed: {e}")
                try:
                    self._refresh_editors_for_part(self.patch_state.active_perf_part, async_mode=False)
                except Exception as e:
                    logger.debug(f"syncPerformance: part editor refresh failed: {e}")
            except Exception as e:
                logger.warning(f"syncPerformanceFromSynth failed: {e}")
            finally:
                self._set_sync_busy(False)

        if async_mode:
            threading.Thread(target=_do_sync, daemon=True).start()
        else:
            _do_sync()

    @pyqtProperty("QVariantList", notify=playlistChanged)
    def playlistEntries(self) -> list:
        from ...core.spectre_format import playlist_entry_status

        out = []
        for i, e in enumerate(self._playlist):
            if not isinstance(e, dict):
                continue
            try:
                status = playlist_entry_status(e)
            except Exception:
                status = "unsaved"
            out.append({
                "index": i,
                "name": str(e.get("name") or "Untitled"),
                "status": status,
                "current": (i == self._playlist_index),
            })
        return out

    @pyqtProperty(int, notify=playlistChanged)
    def playlistIndex(self) -> int:
        return self._playlist_index

    @pyqtProperty(int, notify=playlistChanged)
    def playlistCount(self) -> int:
        return len(self._playlist)

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

    @pyqtSlot()
    def cancelPartPick(self) -> None:
        """Leave pick mode and close the Librarian back to the previous view."""
        self.cancelLibrarian()

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
                if juno is not None:
                    try:
                        juno.set_perf_part_patch(target, int(msb), int(lsb), int(pc))
                    except Exception as e:
                        logger.debug(f"pickPartPatch: part select failed: {e}")
            elif is_file:
                # Pi-only file: queue its image into the part buffer (background,
                # with progress) and remember the link + a snapshot fallback.
                from ...core.spectre_format import load_spectre, patch_state_to_dict
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
            else:
                return False
        except Exception as e:
            logger.warning(f"pickPartPatch failed: {e}")
            return False
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

    def _apply_playlist_state(self, patch_dict: dict, entry_name: str = "",
                              part_snapshots: dict | None = None) -> bool:
        """Swap in a cached/loaded performance image and push the mixer live.

        Mixer selects + levels go synchronously (fast); part sound images for
        Pi-only/missing links restore in the background with progress.
        """
        from ...core.spectre_format import load_spectre, patch_state_from_dict

        try:
            state = patch_state_from_dict(patch_dict)
        except Exception as e:
            logger.warning(f"playlist load: bad snapshot: {e}")
            return False
        kept_macros = self.patch_state.macros
        state.macros = kept_macros if kept_macros else state.macros
        self.patch_state = state
        self.patch_state.sound_mode = "PERFORM"
        self._sound_mode = "PERFORM"
        self._patch_name = getattr(state, "perf_name", "") or entry_name or self._patch_name
        if isinstance(part_snapshots, dict):
            self._part_snapshots = {str(k): v for k, v in part_snapshots.items()
                                    if isinstance(v, dict)}
        juno = self.juno
        image_jobs = []
        if juno is not None:
            try:
                from ...core.protocol import SoundMode
                juno.set_sound_mode(SoundMode.PERFORM)
            except Exception as e:
                logger.debug(f"playlist load: mode switch failed: {e}")
            for p in self.patch_state.perf_parts:
                try:
                    juno.set_perf_part_patch(p.part_index, p.patch_msb, p.patch_lsb, p.patch_pc)
                    juno.set_perf_part_level(p.part_index, p.volume)
                    juno.set_perf_part_pan(p.part_index, p.pan)
                    juno.set_perf_part_mute(p.part_index, p.muted)
                    if hasattr(juno, "set_perf_part_fx"):
                        try:
                            juno.set_perf_part_fx(p.part_index, dry=int(getattr(p, "dry_send", 127)),
                                                  chorus=int(getattr(p, "chorus_send", 0)),
                                                  reverb=int(getattr(p, "reverb_send", 0)))
                        except Exception as e:
                            logger.debug(f"playlist load: part {p.part_index} fx push failed: {e}")
                    if hasattr(juno, "set_perf_part_output"):
                        try:
                            juno.set_perf_part_output(p.part_index,
                                                      assign=int(getattr(p, "output_assign", 13)),
                                                      mfx_select=int(getattr(p, "mfx_select", 0)))
                        except Exception as e:
                            logger.debug(f"playlist load: part {p.part_index} output push failed: {e}")
                    juno.set_perf_zone(p.part_index,
                                       p.key_low, p.key_high, p.zone_switch, p.zone_octave)
                except Exception as e:
                    logger.debug(f"playlist load: part {p.part_index} push failed: {e}")
                    break
                link = str(getattr(p, "patch_file", "") or "")
                if link and Path(link).is_file():
                    try:
                        image_jobs.append(("image", p.part_index, load_spectre(link)["patch_state"]))
                        continue
                    except Exception as e:
                        logger.debug(f"playlist load: part link unreadable: {e}")
                if link:
                    snap = (self._part_snapshots or {}).get(str(p.part_index))
                    if isinstance(snap, dict):
                        try:
                            from ...core.spectre_format import patch_state_from_dict as _from_dict
                            image_jobs.append(("image", p.part_index, _from_dict(snap)))
                        except Exception as e:
                            logger.debug(f"playlist load: bad part snapshot: {e}")
            try:
                fx = getattr(self.patch_state, "perf_fx", None)
                if fx is not None:
                    if hasattr(juno, "set_perf_source"):
                        for _w, _o in (("mfx1", int(fx.mfx1.source)), ("mfx2", int(fx.mfx2.source)),
                                       ("mfx3", int(fx.mfx3.source)), ("chorus", int(fx.chorus_source)),
                                       ("reverb", int(fx.reverb_source))):
                            try:
                                juno.set_perf_source(_w, _o)
                            except Exception as e:
                                logger.debug(f"playlist load: source {_w} push failed: {e}")
                    if hasattr(juno, "set_perf_structure"):
                        try:
                            juno.set_perf_structure(int(fx.mfx_structure))
                        except Exception as e:
                            logger.debug(f"playlist load: structure push failed: {e}")
                    if hasattr(juno, "set_perf_mfx"):
                        for _s, _h in ((1, fx.mfx1), (2, fx.mfx2), (3, fx.mfx3)):
                            try:
                                juno.set_perf_mfx(_s, mfx_type=int(_h.mfx_type),
                                                  dry_send=int(_h.dry_send),
                                                  chorus_send=int(_h.chorus_send),
                                                  reverb_send=int(_h.reverb_send))
                            except Exception as e:
                                logger.debug(f"playlist load: mfx{_s} push failed: {e}")
                            if int(_h.source) == 0 and hasattr(juno, "set_perf_mfx_param"):
                                try:
                                    for _pi, _pv in enumerate(list(getattr(_h, "params", []) or [])[:32]):
                                        if int(_pv) != 0:
                                            juno.set_perf_mfx_param(_s, _pi, int(_pv))
                                except Exception as e:
                                    logger.debug(f"playlist load: mfx{_s} params push failed: {e}")
                    if hasattr(juno, "set_perf_chorus"):
                        try:
                            juno.set_perf_chorus(int(fx.chorus_type), level=int(fx.chorus_level),
                                                 output_select=int(fx.chorus_to_reverb))
                        except Exception as e:
                            logger.debug(f"playlist load: chorus push failed: {e}")
                    if hasattr(juno, "set_perf_reverb"):
                        try:
                            juno.set_perf_reverb(int(fx.reverb_type), level=int(fx.reverb_level))
                        except Exception as e:
                            logger.debug(f"playlist load: reverb push failed: {e}")
            except Exception as e:
                logger.debug(f"playlist load: perf fx push failed: {e}")
            try:
                solos = [p.part_index for p in self.patch_state.perf_parts if p.solo]
                juno.set_perf_solo(solos[-1] if solos else 0)
            except Exception as e:
                logger.debug(f"playlist load: solo push failed: {e}")
            if getattr(state, "raw_regions", None):
                try:
                    active = max(1, min(16, int(getattr(state, "active_perf_part", 1))))
                    image_jobs.append(("image", active, state))
                except Exception as e:
                    logger.debug(f"playlist load: active image job failed: {e}")
            self._queue_push_jobs(image_jobs)
        try:
            self.refreshPartFileStatus()
        except Exception:
            pass
        self._emit_all_state_signals()
        self.playlistChanged.emit()
        return True

    @pyqtSlot(result=bool)
    def addCurrentToPlaylist(self) -> bool:
        """Snapshot the current performance to the end of the playlist."""
        from ...core.spectre_format import make_playlist_entry, patch_state_to_dict

        try:
            origin = self._current_ref or {}
            perf_path = str(origin.get("path") or "") if origin.get("source") == "file" else ""
            name = (getattr(self.patch_state, "perf_name", "") or self._patch_name
                    or f"Song {len(self._playlist) + 1}")
            entry = make_playlist_entry(
                name, patch_state_to_dict(self.patch_state), perf_path=perf_path,
                macros=[float(s.value) for s in self.patch_state.macros],
                seq_pattern=list(getattr(self.patch_state.step_lfo, "steps", []) or []),
            )
            self._playlist.append(entry)
            if self._playlist_index < 0:
                self._playlist_index = 0
            self.playlistChanged.emit()
            return True
        except Exception as e:
            logger.warning(f"addCurrentToPlaylist failed: {e}")
            return False

    @pyqtSlot(int, result=bool)
    def loadPlaylistEntry(self, index: int) -> bool:
        """Load song by index: linked file when healthy, else embedded snapshot."""
        if not 0 <= int(index) < len(self._playlist):
            return False
        entry = self._playlist[int(index)]
        patch_dict = None
        path = str(entry.get("perf_path") or "")
        if path:
            try:
                from ...core.spectre_format import load_spectre, patch_state_to_dict
                loaded = load_spectre(path)
                patch_dict = patch_state_to_dict(loaded["patch_state"])
            except Exception as e:
                logger.info(f"playlist: linked file unreadable, using snapshot: {e}")
        if patch_dict is None:
            patch_dict = entry.get("cached")
        if not isinstance(patch_dict, dict):
            return False
        ok = self._apply_playlist_state(patch_dict, str(entry.get("name") or ""))
        if ok:
            self._playlist_index = int(index)
            self.playlistChanged.emit()
        return ok

    @pyqtSlot(result=bool)
    def nextPlaylistEntry(self) -> bool:
        """Named live action (touch arrows now, MIDI-mappable later)."""
        if not self._playlist:
            return False
        nxt = (self._playlist_index + 1) % len(self._playlist) if self._playlist_index >= 0 else 0
        return self.loadPlaylistEntry(nxt)

    @pyqtSlot(result=bool)
    def prevPlaylistEntry(self) -> bool:
        """Named live action (touch arrows now, MIDI-mappable later)."""
        if not self._playlist:
            return False
        prv = ((self._playlist_index - 1) % len(self._playlist)
               if self._playlist_index >= 0 else len(self._playlist) - 1)
        return self.loadPlaylistEntry(prv)

    @pyqtSlot(int, result=bool)
    def refreshPlaylistEntry(self, index: int) -> bool:
        """Re-read the linked file into the entry snapshot (amber badge action)."""
        if not 0 <= int(index) < len(self._playlist):
            return False
        try:
            from ...core.spectre_format import refresh_entry_snapshot
            refresh_entry_snapshot(self._playlist[int(index)])
            self.playlistChanged.emit()
            return True
        except Exception as e:
            logger.warning(f"refreshPlaylistEntry failed: {e}")
            return False

    @pyqtSlot(int, result=bool)
    def removePlaylistEntry(self, index: int) -> bool:
        if not 0 <= int(index) < len(self._playlist):
            return False
        current = self._playlist[self._playlist_index] \
            if 0 <= self._playlist_index < len(self._playlist) else None
        self._playlist.pop(int(index))
        self._playlist_index = self._index_of_entry(current)
        self.playlistChanged.emit()
        return True

    @pyqtSlot(int, int, result=bool)
    def movePlaylistEntry(self, from_index: int, to_index: int) -> bool:
        """Drag-reorder a setlist song (highlight follows the moved song)."""
        frm, to = int(from_index), int(to_index)
        n = len(self._playlist)
        if not 0 <= frm < n or not 0 <= to < n or frm == to:
            return False
        current = self._playlist[self._playlist_index] \
            if 0 <= self._playlist_index < n else None
        entry = self._playlist.pop(frm)
        self._playlist.insert(to, entry)
        self._playlist_index = self._index_of_entry(current)
        self.playlistChanged.emit()
        return True

    def _index_of_entry(self, entry) -> int:
        """Index of a playlist entry by identity (-1 when gone/empty)."""
        if entry is None or not self._playlist:
            return -1
        for i, e in enumerate(self._playlist):
            if e is entry:
                return i
        return -1 if len(self._playlist) == 0 else min(self._playlist_index, len(self._playlist) - 1)

    @pyqtSlot(str, result=bool)
    def savePlaylist(self, path: str) -> bool:
        """Persist the playlist as a kind='playlist' .spectre file (Pi only)."""
        try:
            from ...core.spectre_format import default_meta, save_spectre
            name = Path(path).stem or "Setlist"
            self._playlist_path = str(path)
            save_spectre(path, self.patch_state,
                         meta=default_meta(name, "playlist"),
                         spectre={"playlist": {"entries": self._playlist,
                                               "index": self._playlist_index}},
                         kind="playlist")
            repo = self._librarian()
            if repo is not None:
                try:
                    repo.touch_file_row(str(path))
                    repo._conn.commit()
                except Exception as e:
                    logger.debug(f"savePlaylist: index refresh failed: {e}")
                try:
                    self.librarianChanged.emit()
                except Exception:
                    pass
            return True
        except Exception as e:
            logger.warning(f"savePlaylist failed: {e}")
            return False

    @pyqtSlot(str, result=bool)
    def loadPlaylist(self, path: str) -> bool:
        """Load a kind='playlist' .spectre file into the setlist (no auto-play).

        Navigates to the mixer so the songs are immediately at hand.
        """
        try:
            from ...core.spectre_format import load_spectre
            loaded = load_spectre(path)
            entries = (loaded.get("spectre") or {}).get("playlist", {}).get("entries", [])
            self._playlist = [e for e in entries if isinstance(e, dict)]
            idx = (loaded.get("spectre") or {}).get("playlist", {}).get("index", -1)
            self._playlist_index = int(idx) if isinstance(idx, int) else -1
            self._playlist_path = str(path)
            self.playlistChanged.emit()
            self._pending_view = "PERFORMANCE"
            return True
        except Exception as e:
            logger.warning(f"loadPlaylist failed: {e}")
            return False

    @pyqtProperty(str, notify=playlistChanged)
    def playlistPath(self) -> str:
        """Basename of the loaded playlist file ('' when never saved)."""
        try:
            return Path(str(self._playlist_path or "")).name
        except Exception:
            return ""

    @pyqtSlot(result=bool)
    def savePlaylistAuto(self) -> bool:
        """SAVE SETLIST: overwrite the loaded path, else create 'Setlist N'."""
        if str(self._playlist_path or ""):
            ok = self.savePlaylist(str(self._playlist_path))
        else:
            repo = self._librarian()
            base = repo.user_dir if repo is not None else Path(".")
            n = 1
            while (Path(base) / f"Setlist {n}.spectre").exists():
                n += 1
            ok = self.savePlaylist(str(Path(base) / f"Setlist {n}.spectre"))
        if ok:
            self.playlistChanged.emit()
        return ok

    @pyqtSlot()
    def newPlaylist(self) -> None:
        """Clear the setlist (files on disk untouched)."""
        self._playlist = []
        self._playlist_index = -1
        self._playlist_path = ""
        self.playlistChanged.emit()

    _ENGINE_VIEWS = ("JUNO PCM", "VECTOR", "WAVETABLE", "VA", "LIVE", "SEQUENCER", "SETLIST", "PERFORMANCE", "MACROS")

    @staticmethod
    def _engine_view_for(extras) -> str:
        """Saved engine view for a patch file (JUNO PCM fallback)."""
        try:
            v = str((extras or {}).get("engine_mode") or "JUNO PCM").upper().strip()
        except Exception:
            return "JUNO PCM"
        aliases = {
            "PATCH EDIT": "JUNO PCM", "JUNO-DS": "JUNO PCM", "JUNO_PCM": "JUNO PCM",
            "4-OSC VA": "VA", "4OSC VA": "VA", "VA ENGINE": "VA",
            "LIVE MODE": "LIVE", "SESSION": "LIVE",
            "STEP EDITOR": "SEQUENCER", "SEQ": "SEQUENCER",
            "SET LIST": "SETLIST", "PLAYLIST": "SETLIST",
            "PERF MIXER": "PERFORMANCE",
            "MACRO DECK": "MACROS",
        }
        v = aliases.get(v, v)
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
            from ...sequencer.models import SequencerSong
            song = SequencerSong.from_dict(seq_raw)
        except Exception as e:
            logger.warning(f"song load: bad sequence: {e}")
            return
        self.sequencer.stop()
        self.sequencer.song = song
        self._apply_tempo(song.bpm)
        if hasattr(self, "_seq_retarget_recorder"):
            self._seq_retarget_recorder()
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
        try:
            from ...core.spectre_format import load_spectre, patch_state_to_dict
            loaded = load_spectre(path)
        except Exception as e:
            logger.warning(f"loadSpectreFile failed for {path}: {e}")
            return False
        kind = str(loaded.get("kind") or "patch")
        if kind == "playlist":
            ok = self.loadSetlist(path) if hasattr(self, "loadSetlist") else self.loadPlaylist(path)
            if ok:
                self._pending_view = "SETLIST"
            return ok
        if kind == "performance":
            # One file = the whole song: 16-part performance, part sounds
            # and (when saved with one) the sequence + tempo.
            spectre = loaded.get("spectre") or {}
            try:
                name = str((loaded.get("meta") or {}).get("name") or "")
                snapshots = spectre.get("part_snapshots") or {}
            except Exception:
                name, snapshots = "", {}
            ok = self._apply_playlist_state(patch_state_to_dict(loaded["patch_state"]),
                                            name, snapshots if isinstance(snapshots, dict) else {})
            if not ok:
                return False
            seq_raw = spectre.get("sequencer")
            if isinstance(seq_raw, dict):
                self._restore_song_sequence(seq_raw)
            self._set_current_file_ref(path, "performance")
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
                from ...core.protocol import SoundMode
                juno.set_sound_mode(SoundMode.PATCH)
                juno.set_active_perf_part(1)
                blob = juno.encode_patch_sysex(self.patch_state)
                juno.apply_sysex_blob(blob)
            except Exception as e:
                logger.debug(f"loadSpectreFile: synth push failed: {e}")
        try:
            self._tone_waves = [(t.wave_bank_l, t.wave_num_l) for t in self.patch_state.tones]
            self._cached_tone_wave_data = [
                self._wave_catalog.get_wave(b, n) for b, n in self._tone_waves
            ]
        except Exception:
            pass
        self._set_current_file_ref(path, kind)
        self._emit_all_state_signals()
        self._pending_view = self._engine_view_for(loaded.get("spectre"))
        return True

