"""Macro bridge mixin: macro links, offset engine and per-part macro mirrors."""

from __future__ import annotations

import logging
import threading
from contextlib import contextmanager

from PyQt6.QtCore import QTimer, pyqtProperty, pyqtSignal, pyqtSlot

from ...core.macro_targets import (
    filter_macro_targets,
    get_macro_catalog,
    macro_delta,
    resolve_sounding,
)
from ...core.patch_state import PatchState, ToneState, auto_macro_name
from ...core.routing import tone_send_attrs, tone_sends
from .base import BridgeBaseMixin

logger = logging.getLogger(__name__)

# Controller-driven part mixer moves refresh the part strips at most this often
PARTS_EMIT_MS = 50


class MacroBridgeMixin(BridgeBaseMixin):
    """Macro deck: links, offsets on top of a base, part-scoped targets."""

    # A non-edited part's macro mirror finished loading (emitted off-thread)
    macroPartLoaded = pyqtSignal(int)

    macrosChanged = pyqtSignal()
    requestOpenMacroAssign = pyqtSignal(int)

    _macro_catalog_by_key: dict | None = None

    # Targets that live in a part (patch params + performance mixer). In
    # PERFORM mode their concrete keys carry the part: "tone.1.tvf_cutoff@3".
    _PART_SCOPED_PREFIXES = ("common.", "tone.", "part.")

    # Non-edited parts' patches are read from the synth off the UI thread:
    # a macro on ALL may need 15 parts (~9 reads each). Until a part's
    # mirror arrives its keys are skipped; it joins on macroPartLoaded.
    _macro_async_parts = True

    # FX macro key -> (block, param). In PERFORM mode these act on the
    # assigned processor (perf FX or source part); MFX keys pick a fixed slot.
    _PERF_FX_MACROS: dict[str, tuple[str, str]] = {
        "effects.chorus_level": ("chorus", "level"),
        "effects.chorus_rate": ("chorus", "rate"),
        "effects.chorus_depth": ("chorus", "depth"),
        "effects.chorus_predelay": ("chorus", "preDelay"),
        "effects.chorus_feedback": ("chorus", "feedback"),
        "effects.reverb_level": ("reverb", "level"),
        "effects.reverb_predelay": ("reverb", "preDelay"),
        "effects.reverb_time": ("reverb", "time"),
        "effects.reverb_damp": ("reverb", "damp"),
        "effects.reverb_diffusion": ("reverb", "diffusion"),
        "effects.reverb_tone": ("reverb", "tone"),
        **{f"effects.mfx{'' if n == 1 else n}_{send}_send": (f"mfx{n}", send)
           for n in (1, 2, 3) for send in ("dry", "chorus", "reverb")},
    }

    _PERF_FX_KEYS: dict[tuple[str, str], str] = {v: k for k, v in _PERF_FX_MACROS.items()}

    # Index of each param in the _cho_view / _rev_view tuples
    _CHO_VIEW_IDX = {"level": 1, "rate": 3, "depth": 4, "preDelay": 5, "feedback": 6}

    _REV_VIEW_IDX = {"level": 1, "preDelay": 2, "time": 3, "damp": 4, "diffusion": 5, "tone": 6}

    def _init_macros(self) -> None:
        # Macro part mirrors load off-thread; join them on the UI thread
        self.macroPartLoaded.connect(self._onMacroPartLoaded)

    @classmethod
    def _macroEntry(cls, key: str) -> dict | None:
        if cls._macro_catalog_by_key is None:
            cls._macro_catalog_by_key = {e["key"]: e for e in get_macro_catalog()}
        return cls._macro_catalog_by_key.get(cls._splitPart(key)[0])

    @staticmethod
    def _splitPart(key: str) -> tuple[str, int]:
        """"tone.1.tvf_cutoff@3" -> ("tone.1.tvf_cutoff", 3); no suffix -> (key, 0)."""
        base, sep, part = key.partition("@")
        if sep:
            try:
                return base, max(1, min(16, int(part)))
            except ValueError:
                pass
        return base, 0

    def _editedPart(self) -> int:
        return max(1, min(16, int(getattr(self.patch_state, "active_perf_part", 1) or 1)))

    def _linkParts(self, link, key: str) -> list[int]:
        """Parts a link drives in PERFORM: [] = edited part, [0] = sounding parts."""
        parts = list(getattr(link, "parts", []) or [])
        if not parts:
            return [self._editedPart()]
        if 0 in parts:
            # Sounding = unmuted with level > 0 (a level macro may take a part
            # to 0, so level targets only skip muted parts)
            return [p.part_index for p in self.patch_state.perf_parts[:16]
                    if not p.muted and (p.volume > 0 or key == "part.level")]
        return [n for n in parts if 1 <= n <= 16]

    def _concreteKeys(self, link) -> list[str]:
        """Concrete keys a link drives right now (tone.all fan-out + parts)."""
        key = link.target_key
        keys = self._expandKey(key)
        if not key.startswith(self._PART_SCOPED_PREFIXES):
            return keys
        if not self._in_perform():
            return [] if key.startswith("part.") else keys
        return [f"{k}@{n}" for n in self._linkParts(link, key) for k in keys]

    def _scopedKey(self, key: str) -> str:
        """Direct edits of the edited part's params rebase that part's key in PERFORM."""
        if "@" in key or not key.startswith(("common.", "tone.")) or not self._in_perform():
            return key
        return f"{key}@{self._editedPart()}"

    @staticmethod
    def _expandKey(key: str) -> list[str]:
        if key.startswith("tone.all."):
            suffix = key[len("tone.all."):]
            return [f"tone.{i}.{suffix}" for i in range(1, 5)]
        return [key]

    def _macroLinksFor(self, key: str) -> list[tuple[int, object]]:
        """All (macro_idx, link) pairs addressing a concrete key (incl. via tone.all.*)."""
        out = []
        for mi, slot in enumerate(self.patch_state.macros):
            for link in slot.links:
                if key in self._concreteKeys(link):
                    out.append((mi, link))
        return out

    def _readAbsolute(self, key: str, ps=None) -> float:
        """Current value of `key` (ps: read the edited part's sound from this
        state instead, e.g. the loaded-value snapshot)."""
        ps = ps if ps is not None else self.patch_state
        key, part = self._splitPart(key)
        if part:
            if key.startswith("part."):
                p = ps.perf_parts[part - 1]
                return float({"level": p.volume, "pan": p.pan, "chorus_send": p.chorus_send,
                              "reverb_send": p.reverb_send}.get(key[5:], 0))
            if part != self._editedPart():
                ps = self._macroPartState(part)   # (never a snapshot: those are the edited part's)
        try:
            if key == "common.level":
                return float(ps.common.level)
            if key == "common.pan":
                return float(ps.common.pan)
            if key == "common.cutoff_offset":
                return float(ps.common.cutoff_offset)
            if key == "common.resonance_offset":
                return float(ps.common.resonance_offset)
            if key == "common.attack_offset":
                return float(ps.common.attack_offset)
            if key == "common.release_offset":
                return float(ps.common.release_offset)
            if key == "common.portamento_time":
                return float(ps.common.portamento_time)
            if key == "common.analog_feel":
                return float(ps.common.analog_feel)
            if key.startswith("common.matrix"):
                c, d = int(key[13]), int(key[-1])
                return float(getattr(ps.common.matrix_ctrls[c - 1], f"sens{d}"))
            if key.startswith("effects."):
                if key in self._PERF_FX_MACROS and self._in_perform():
                    return float(self._perfFxMacroValue(key))
                return float(getattr(ps.effects, key.split(".", 1)[1], 0.0))
            if key.startswith("tone."):
                _, idx, param = key.split(".", 2)
                t = ps.get_tone(int(idx))
                if param in ("chorus_send", "reverb_send"):
                    # The pair the tone's route uses (core.routing)
                    return float(tone_sends(ps.common, t)[param == "reverb_send"])
                return float(self._toneParam(t, param))
            if key == "vector.x":
                return float(self.vector.x)
            if key == "vector.y":
                return float(self.vector.y)
            if key == "vector.w":
                return float(self.vector.w)
            if key == "vector.orbit_x":
                return float(self.vector.motion.center_x)
            if key == "vector.orbit_y":
                return float(self.vector.motion.center_y)
            if key.startswith("seq.swing."):
                return float(self.sequencer.song.tracks[int(key[10:]) - 1].swing)
            if key == "vector.speed":
                return float(self.vector.motion.speed)
            if key == "vector.bpm":
                return float(self.bpm)
        except (ValueError, AttributeError, IndexError):
            pass
        return 0.0

    @staticmethod
    def _toneParam(t: ToneState, param: str) -> float:
        mapping = {
            "tvf_cutoff": t.tvf_cutoff, "tvf_resonance": t.tvf_resonance,
            "tvf_env_depth": t.tvf_env_depth, "tvf_keyfollow": t.tvf_cutoff_keyfollow,
            "tvf_attack": t.tvf_attack,
            "tvf_decay": t.tvf_decay, "tvf_sustain": t.tvf_sustain, "tvf_release": t.tvf_release,
            "tva_level": t.level, "tva_pan": t.pan,
            "tva_attack": t.tva_attack, "tva_decay": t.tva_decay,
            "tva_sustain": t.tva_sustain, "tva_release": t.tva_release,
            "pitch_coarse": t.coarse_tune, "pitch_fine": t.fine_tune,
            "lfo1_rate": t.lfo1_rate, "lfo1_pitch_depth": t.lfo1_pitch_depth,
            "lfo1_tvf_depth": t.lfo1_tvf_depth, "lfo1_tva_depth": t.lfo1_tva_depth,
            "lfo1_pan_depth": t.lfo1_pan_depth, "lfo2_rate": t.lfo2_rate,
            "lfo2_pitch_depth": t.lfo2_pitch_depth, "lfo2_tvf_depth": t.lfo2_tvf_depth,
            "lfo2_tva_depth": t.lfo2_tva_depth, "lfo2_pan_depth": t.lfo2_pan_depth,
            "output_level": t.output_level,
            "pitch_env_depth": t.pitch_env_depth, "pitch_env_attack": t.pitch_env_attack,
            "pitch_env_decay": t.pitch_env_decay, "pitch_env_release": t.pitch_env_release,
            "pitch_env_sustain": t.pitch_env_sustain,
        }
        return float(mapping.get(param, 0.0))

    def _ensureBase(self, key: str) -> float:
        bases = self.patch_state.macro_bases
        if key not in bases:
            bases[key] = float(self._readAbsolute(key))
        return float(bases[key])

    def _contributions(self, key: str) -> list[float]:
        entry = self._macroEntry(key)
        span = float(entry["span"]) if entry else 127.0
        out = []
        for mi, link in self._macroLinksFor(key):
            v = self.patch_state.macros[mi].value
            out.append(macro_delta(span, link.polarity, link.depth, v))
        return out

    def _recomputeTarget(self, key: str) -> float:
        entry = self._macroEntry(key)
        lo = float(entry["min"]) if entry else 0.0
        hi = float(entry["max"]) if entry else 127.0
        base = self._ensureBase(key)
        sounding = resolve_sounding(base, self._contributions(key), lo, hi)
        self._applyAbsolute(key, sounding)
        return sounding

    def _applyAbsolute(self, key: str, sounding: float) -> None:
        """Write sounding value to patch_state + synth. Never touches bases."""
        base_key, part = self._splitPart(key)
        if part:
            self._applyPartKey(base_key, part, int(round(max(0, sounding))))
            return
        ps = self.patch_state
        is_int = not key.startswith(("vector.", "seq."))
        val = sounding
        if key.startswith("seq.swing."):
            self.seqSetTrackSwing(int(key[10:]) - 1, val)
            return
        if key in ("vector.orbit_x", "vector.orbit_y"):
            m = self.vector.motion
            x = max(0.0, min(1.0, val)) if key == "vector.orbit_x" else m.center_x
            y = max(0.0, min(1.0, val)) if key == "vector.orbit_y" else m.center_y
            m.set_orbit_center(x, y)
            self.attractorChanged.emit(m.center_x, m.center_y)
            return
        if key.startswith("vector."):
            if key == "vector.x":
                self.vector.set_coordinates(max(0.0, min(1.0, val)), self.vector.y)
            elif key == "vector.y":
                self.vector.set_coordinates(self.vector.x, max(0.0, min(1.0, val)))
            elif key == "vector.w":
                self.vector.set_wavetable_pos(max(0.0, min(1.0, val)))
            elif key == "vector.speed":
                self.vector.motion.speed = max(0.25, min(4.0, val))
                self.speedChanged.emit(self.vector.motion.speed)
            elif key == "vector.bpm":
                if not (hasattr(self, "_audio_hold_tempo") and self._audio_hold_tempo(val)):
                    self._apply_tempo(val)
            return
        iv = int(round(max(0, val))) if is_int else val
        if key in self._PERF_FX_MACROS and self._in_perform():
            self._pushPerfFxMacro(key, max(0, min(127, iv)))
            return
        if key.startswith("effects."):
            field = key.split(".", 1)[1]
            if hasattr(ps.effects, field):
                setattr(ps.effects, field, max(0, min(127, iv)))
                self._pushEffect(key, iv)
            return
        self._applyPatchKey(key, iv, ps)

    def _applyPartKey(self, key: str, part: int, iv: int) -> None:
        """PERFORM: write a part-scoped macro value to performance part `part`."""
        if key.startswith("part."):
            self._applyMixerMacro(key[5:], part, iv)
            return
        if part == self._editedPart():
            self._applyPatchKey(key, iv, self.patch_state)
            return
        # Another part: its own mirrored state, synth writes aimed at its buffer
        st = self._macroPartState(part)
        juno = self.juno
        if juno is None:
            self._applyPatchKey(key, iv, st, edited=False)
            return
        with juno.part_scope(part):
            self._applyPatchKey(key, iv, st, edited=False)

    def _applyMixerMacro(self, param: str, part: int, iv: int) -> None:
        p = self.patch_state.perf_parts[part - 1]
        v = max(0, min(127, iv))
        juno = self.juno
        try:
            if param == "level":
                p.volume = v
                if juno:
                    juno.set_perf_part_level(part, v)
            elif param == "pan":
                p.pan = v
                if juno:
                    juno.set_perf_part_pan(part, v)
            elif param == "chorus_send":
                p.chorus_send = v
                if juno:
                    juno.set_perf_part_fx(part, chorus=v)
            elif param == "reverb_send":
                p.reverb_send = v
                if juno:
                    juno.set_perf_part_fx(part, reverb=v)
        except Exception as e:
            logger.debug(f"macro mixer push failed for part {part} {param}: {e}")
        self._emitPerfPartsThrottled()

    def _emitPerfPartsThrottled(self) -> None:
        """perfPartsChanged at most every PARTS_EMIT_MS while a control moves.

        Every emit rebuilds the part strips and the routing graph (~30 ms on
        the Pi), too much per fader step. The first move shows at once, the
        last one when the interval ends.
        """
        timer = self.__dict__.get("_parts_emit_timer")
        if timer is None:
            timer = self._parts_emit_timer = QTimer(self)
            timer.setSingleShot(True)
            timer.setInterval(PARTS_EMIT_MS)
            timer.timeout.connect(self._flushPerfParts)
            self._parts_emit_pending = False
        if timer.isActive():
            self._parts_emit_pending = True
            return
        self.perfPartsChanged.emit()
        timer.start()

    def _flushPerfParts(self) -> None:
        if self._parts_emit_pending:
            self._parts_emit_pending = False
            self.perfPartsChanged.emit()
            self._parts_emit_timer.start()

    def _macroPartState(self, part: int):
        """Mirror of a non-edited part's patch for macro bases and writes.

        Read once from the part's temp buffer; falls back to its saved
        snapshot, then to defaults. Dropped by _forgetMacroPart / resets.
        """
        cache = self.__dict__.setdefault("_macro_part_states", {})
        st = cache.get(part)
        if st is None:
            st = cache[part] = self._readMacroPart(part)
        return st

    def _readMacroPart(self, part: int):
        st = None
        juno = self.juno
        if juno is not None:
            try:
                with juno.part_scope(part):
                    common = juno.read_patch_common(timeout=1.0)
                    tones = juno.read_all_tones(timeout=1.0)
                if common is not None and tones:
                    st = PatchState()
                    st.common = common
                    st.tones = list(tones)
            except Exception as e:
                logger.debug(f"macro: reading part {part} failed: {e}")
                st = None
        if st is None:
            snap = (getattr(self, "_part_snapshots", None) or {}).get(str(part))
            if isinstance(snap, dict):
                try:
                    from ...core.spectre_format import patch_state_from_dict
                    st = patch_state_from_dict(snap)
                except Exception:
                    st = None
        return st if st is not None else PatchState()

    def _macroKeyReady(self, key: str) -> bool:
        """False while a non-edited part's mirror is still loading."""
        base_key, part = self._splitPart(key)
        if not part or base_key.startswith("part.") or part == self._editedPart():
            return True
        if part in self.__dict__.setdefault("_macro_part_states", {}):
            return True
        if not self._macro_async_parts or self.juno is None:
            self._macroPartState(part)
            return True
        self._queueMacroPartLoad(part)
        return False

    def _queueMacroPartLoad(self, part: int) -> None:
        lock = self.__dict__.setdefault("_macro_load_lock", threading.Lock())
        with lock:
            pending = self.__dict__.setdefault("_macro_part_pending", set())
            pending.add(int(part))
            t = self.__dict__.get("_macro_loader")
            if t is not None and t.is_alive():
                return
            t = threading.Thread(target=self._macroPartLoader, name="macro-parts", daemon=True)
            self._macro_loader = t
            t.start()

    def _macroPartLoader(self) -> None:
        lock = self._macro_load_lock
        cache = self.__dict__.setdefault("_macro_part_states", {})
        while True:
            with lock:
                pending = self._macro_part_pending
                pending.difference_update(cache.keys())
                if not pending:
                    return
                part = min(pending)
            cache[part] = self._readMacroPart(part)
            with lock:
                self._macro_part_pending.discard(part)
            try:
                self.macroPartLoaded.emit(part)
            except RuntimeError:
                return  # bridge gone

    @pyqtSlot(int)
    def _onMacroPartLoaded(self, part: int) -> None:
        """A part's mirror arrived: bring it into every macro that targets it."""
        suffix = f"@{int(part)}"
        hit = False
        with self._macroWrites():
            for mi, slot in enumerate(self.patch_state.macros):
                if any(k.endswith(suffix) for link in slot.links for k in self._concreteKeys(link)):
                    self._recomputeForMacro(mi)
                    hit = True
        if hit:
            self.macrosChanged.emit()
        self._auto_kick()

    @contextmanager
    def _macroWrites(self):
        """Macro synth writes go through the coalescing writer (no UI waits)."""
        juno = self.juno
        cw = getattr(juno, "coalesced_writes", None) if juno is not None else None
        if cw is None:
            yield
            return
        with cw():
            yield

    def _forgetMacroPart(self, part: int) -> None:
        """A part's sound changed: drop its mirror and its macro bases."""
        self.__dict__.setdefault("_macro_part_states", {}).pop(int(part), None)
        self._forget_loaded(int(part))
        suffix = f"@{int(part)}"
        bases = self.patch_state.macro_bases
        for k in [k for k in bases if k.endswith(suffix) and not k.startswith("part.")]:
            del bases[k]

    def _resetMacroBases(self) -> None:
        """Re-capture every macro base from the synth (e.g. after a mode switch)."""
        self.patch_state.macro_bases = {}
        self._macro_part_states = {}
        self._auto_forget()
        self._forget_loaded()

    def _applyPatchKey(self, key: str, iv: int, ps, edited: bool = True) -> None:
        """Common/tone macro write into `ps` + the synth's current patch base."""
        juno = self.juno
        try:
            if key == "common.level":
                ps.common.level = max(0, min(127, iv))
                if juno:
                    juno.set_patch_param("level", ps.common.level)
            elif key == "common.pan":
                ps.common.pan = max(0, min(127, iv))
            elif key == "common.cutoff_offset":
                ps.common.cutoff_offset = max(1, min(127, iv))
                for t in ps.tones:
                    pass
                if juno:
                    juno.set_patch_offsets(cutoff=ps.common.cutoff_offset)
            elif key == "common.resonance_offset":
                ps.common.resonance_offset = max(1, min(127, iv))
                if juno:
                    juno.set_patch_offsets(resonance=ps.common.resonance_offset)
            elif key == "common.attack_offset":
                ps.common.attack_offset = max(1, min(127, iv))
                if juno:
                    juno.set_patch_offsets(attack=ps.common.attack_offset)
            elif key == "common.release_offset":
                ps.common.release_offset = max(1, min(127, iv))
                if juno:
                    juno.set_patch_offsets(release=ps.common.release_offset)
            elif key == "common.portamento_time":
                ps.common.portamento_time = max(0, min(127, iv))
                if juno:
                    juno.set_portamento(ps.common.portamento_switch, time=ps.common.portamento_time)
            elif key == "common.analog_feel":
                ps.common.analog_feel = max(0, min(127, iv))
                if juno:
                    juno.set_patch_analog_feel(ps.common.analog_feel)
            elif key.startswith("common.matrix"):
                c = ps.common.matrix_ctrls[int(key[13]) - 1]
                setattr(c, f"sens{key[-1]}", max(1, min(127, iv)))
                if juno:
                    juno.set_matrix_control(
                        int(key[13]), source=c.source,
                        dest1=c.dest1, sens1=c.sens1, dest2=c.dest2, sens2=c.sens2,
                        dest3=c.dest3, sens3=c.sens3, dest4=c.dest4, sens4=c.sens4)
            elif key.startswith("tone."):
                _, idx, param = key.split(".", 2)
                self._applyToneParam(int(idx), param, iv, ps=ps, edited=edited)
        except (ValueError, AttributeError, IndexError) as e:
            logger.debug(f"macro apply failed for {key}: {e}")

    def _perfFxMacroValue(self, key: str) -> int:
        block, param = self._PERF_FX_MACROS[key]
        if block == "chorus":
            return int(self._cho_view()[self._CHO_VIEW_IDX[param]])
        if block == "reverb":
            return int(self._rev_view()[self._REV_VIEW_IDX[param]])
        entry = self._rail_mfx_entry(int(block[3]))
        return int(entry[{"dry": "drySend", "chorus": "chorusSend", "reverb": "reverbSend"}[param]])

    def _pushPerfFxMacro(self, key: str, iv: int) -> None:
        """Write a macro value to the assigned processor (never the part patch FX)."""
        block, param = self._PERF_FX_MACROS[key]
        self._macro_pushing = True
        try:
            if block.startswith("mfx"):
                self.setPerfMfxSlotSend(int(block[3]), param, iv)
                return
            target = self._cho_target() if block == "chorus" else self._rev_target()
            if target[0] == "part":
                # Without the source part's FX cached the setters would fall back
                # to the edited part's patch FX; skip instead.
                self._ensure_part_fx_cache(target[1])
                if self._part_cached(target[1]) is None:
                    return
            if block == "chorus":
                self.setChorusParam(param, iv)
            else:
                self.setReverbParam(param, iv)
        finally:
            self._macro_pushing = False

    def _rebasePerfFx(self, block: str, param: str, value: int) -> None:
        """Manual PERFORM FX edit = new macro base (skipped for macro-driven writes)."""
        if getattr(self, "_macro_pushing", False):
            return
        key = self._PERF_FX_KEYS.get((block, param))
        if key:
            self._rebaseDirect([(key, value)])

    def _pushEffect(self, key: str, iv: int) -> None:
        juno = self.juno
        if not juno:
            return
        try:
            eff = self.patch_state.effects
            if key == "effects.chorus_level":
                juno.set_chorus(eff.chorus_type, level=eff.chorus_level)
            elif key == "effects.reverb_level":
                juno.set_reverb(eff.reverb_type, level=eff.reverb_level)
            elif key.startswith("effects.chorus_"):
                juno.set_chorus_param(key.split("_", 1)[1], iv)
            elif key.startswith("effects.reverb_"):
                juno.set_reverb_param(key.split("_", 1)[1], iv)
            elif key.startswith("effects.mfx_"):
                send = {"effects.mfx_dry_send": "dry", "effects.mfx_chorus_send": "chorus",
                        "effects.mfx_reverb_send": "reverb"}.get(key)
                if send:
                    juno.set_mfx(eff.mfx_type, **{f"{send}_send": iv})
        except Exception as e:
            logger.debug(f"macro effect push failed for {key}: {e}")

    def _applyToneParam(self, tone_idx: int, param: str, iv: int,
                        ps=None, edited: bool = True) -> None:
        """Tone macro write; edited=False for a non-edited part's mirror."""
        ps = ps if ps is not None else self.patch_state
        t = ps.get_tone(tone_idx)
        juno = self.juno
        if param == "tvf_cutoff":
            t.tvf_cutoff = max(0, min(127, iv))
            if juno:
                juno.set_tone_tvf(tone_idx, cutoff=t.tvf_cutoff)
        elif param == "tvf_resonance":
            t.tvf_resonance = max(0, min(127, iv))
            if juno:
                juno.set_tone_tvf(tone_idx, resonance=t.tvf_resonance)
        elif param == "tvf_env_depth":
            t.tvf_env_depth = max(1, min(127, iv))
            if juno:
                juno.set_tone_tvf(tone_idx, env_depth=t.tvf_env_depth)
        elif param == "tvf_keyfollow":
            t.tvf_cutoff_keyfollow = max(44, min(84, iv))
            if juno:
                juno.set_tone_tvf(tone_idx, key_follow=t.tvf_cutoff_keyfollow)
        elif param in ("tvf_attack", "tvf_decay", "tvf_sustain", "tvf_release"):
            setattr(t, param, max(0, min(127, iv)))
            self._push_tvf_env(t)
        elif param == "tva_level":
            t.level = max(0, min(127, iv))
            if not t.muted:
                if edited:
                    self.vector.set_tone_level(tone_idx, t.level)
                if juno:
                    juno.set_tone_level(tone_idx, t.level)
        elif param == "tva_pan":
            t.pan = max(0, min(127, iv))
            if juno:
                juno.set_tone_tva(tone_idx, pan=t.pan)
        elif param in ("tva_attack", "tva_decay", "tva_sustain", "tva_release"):
            # The properties, so sustain moves L2 with L3 like the filter does
            setattr(t, param, max(0, min(127, iv)))
            self._push_tva_env(t)
        elif param == "pitch_coarse":
            t.coarse_tune = max(16, min(112, iv))
            if juno:
                juno.set_tone_pitch(tone_idx, coarse=t.coarse_tune)
        elif param == "pitch_fine":
            t.fine_tune = max(14, min(114, iv))
            if not ps.auto_detune:      # the custom detune Auto Detune gives back
                ps.custom_detune_cache[tone_idx - 1] = t.fine_tune
            if juno:
                juno.set_tone_pitch(tone_idx, fine=t.fine_tune)
        elif param.startswith("lfo1_") or param.startswith("lfo2_"):
            self._applyLfoParam(t, param, iv)
        elif param in ("chorus_send", "reverb_send"):
            # Write the pair the tone's route uses, like the Juno panel
            attr = tone_send_attrs(ps.common, t)[param == "reverb_send"]
            setattr(t, attr, max(0, min(127, iv)))
            if juno:
                juno.set_tone_output(tone_idx, **{attr: getattr(t, attr)})
        elif param == "output_level":
            t.output_level = max(0, min(127, iv))
            if juno:
                juno.set_tone_param(tone_idx, 0x000C, t.output_level)
        elif param.startswith("pitch_env_"):
            if param == "pitch_env_depth":
                t.pitch_env_depth = max(52, min(76, iv))
            elif param in ("pitch_env_attack", "pitch_env_decay", "pitch_env_sustain", "pitch_env_release"):
                setattr(t, param, iv)       # the A/D/S/R properties (core.env_shape)
            else:
                return
            self._push_pitch_env(t)

    def _applyLfoParam(self, t: ToneState, param: str, iv: int) -> None:
        juno = self.juno
        lfo = 1 if param.startswith("lfo1_") else 2
        kind = param.split("_", 1)[1]
        if kind == "rate":
            if lfo == 1:
                t.lfo1_rate = max(0, min(127, iv))
            else:
                t.lfo2_rate = max(0, min(127, iv))
            if juno:
                juno.set_tone_lfo(t.tone_index, lfo_index=lfo,
                                  rate=t.lfo1_rate if lfo == 1 else t.lfo2_rate)
        else:
            depth = max(1, min(127, iv))
            attr = f"lfo{lfo}_{kind}"
            if hasattr(t, attr):
                setattr(t, attr, depth)
            if juno:
                juno.set_tone_lfo(t.tone_index, lfo_index=lfo, **{kind: depth})

    def _rebaseDirect(self, keys_bases: list[tuple[str, float]]) -> None:
        """Treat direct edits as new bases (semantics ii). No-op for unlinked keys."""
        touched: set[str] = set()
        for key, new_base in keys_bases:
            key = self._scopedKey(key)
            if not self._macroLinksFor(key):
                continue
            entry = self._macroEntry(key)
            lo = float(entry["min"]) if entry else 0.0
            hi = float(entry["max"]) if entry else 127.0
            self.patch_state.macro_bases[key] = max(lo, min(hi, float(new_base)))
            self._recomputeTarget(key)
            touched.add(key)
        if touched:
            self._emitForMacroKeys(touched)

    def _rebaseLfoParam(self, lfo_idx: int, param: str, targets: list) -> None:
        """Rebase helper for setLfoParam (depths raw=centered, rate absolute)."""
        if param in ("wave", "delay_time", "fade_mode", "fade_time"):
            return
        pairs = []
        for t in targets:
            if param == "rate":
                key = f"tone.{t.tone_index}.lfo{lfo_idx}_rate"
                base = t.lfo1_rate if lfo_idx == 1 else t.lfo2_rate
            else:
                key = f"tone.{t.tone_index}.lfo{lfo_idx}_{param}"
                attr = f"lfo{lfo_idx}_{param}"
                base = float(getattr(t, attr, 64))
            pairs.append((key, base))
        if pairs:
            self._rebaseDirect(pairs)

    def _rebaseChorusParam(self, param: str) -> None:
        mapping = {"level": ("effects.chorus_level", self.patch_state.effects.chorus_level),
                   "rate": ("effects.chorus_rate", self.patch_state.effects.chorus_rate),
                   "depth": ("effects.chorus_depth", self.patch_state.effects.chorus_depth),
                   "preDelay": ("effects.chorus_predelay", self.patch_state.effects.chorus_predelay),
                   "feedback": ("effects.chorus_feedback", self.patch_state.effects.chorus_feedback)}
        if param in mapping:
            key, base = mapping[param]
            self._rebaseDirect([(key, base)])

    def _rebaseReverbParam(self, param: str) -> None:
        mapping = {"level": ("effects.reverb_level", self.patch_state.effects.reverb_level),
                   "time": ("effects.reverb_time", self.patch_state.effects.reverb_time),
                   "damp": ("effects.reverb_damp", self.patch_state.effects.reverb_damp),
                   "preDelay": ("effects.reverb_predelay", self.patch_state.effects.reverb_predelay),
                   "diffusion": ("effects.reverb_diffusion", self.patch_state.effects.reverb_diffusion),
                   "tone": ("effects.reverb_tone", self.patch_state.effects.reverb_tone)}
        if param in mapping:
            key, base = mapping[param]
            self._rebaseDirect([(key, base)])

    # Tone params whose editor property has its own notify signal
    _TONE_PARAM_SIGNALS = {
        "tvf_env_depth": "tvfEnvDepth", "tva_pan": "tvaPan",
        "tvf_attack": "tvfAttack", "tvf_decay": "tvfDecay", "tvf_sustain": "tvfSustain", "tvf_release": "tvfRelease",
        "tva_attack": "tvaAttack", "tva_decay": "tvaDecay", "tva_sustain": "tvaSustain", "tva_release": "tvaRelease",
    }

    def _emitForMacroKeys(self, keys: set[str], macros: bool = True) -> None:
        """Refresh the editors showing `keys`.

        macros=False when the caller emits macrosChanged itself, or no macro
        drives the keys (it re-reads every macro list: ~7 ms on the Pi).
        """
        # Editors only show the edited part; other parts need no refresh
        edited = self._editedPart()
        keys = {b for b, n in map(self._splitPart, keys) if n in (0, edited)}
        if any(k.startswith("tone.") and ".tvf_" in k or k.startswith("common.cutoff") or k.startswith("common.resonance") for k in keys):
            try:
                self.masterCutoffChanged.emit(self.masterCutoff)
                self.masterResoChanged.emit(self.masterReso)
            except Exception:
                pass
        if any("tva_" in k or "tva-level" in k or k.endswith("tva_level") or "attack" in k or "release" in k for k in keys):
            try:
                self.masterAttackChanged.emit(self.masterAttack)
                self.masterReleaseChanged.emit(self.masterRelease)
                self.tvaLevelChanged.emit(self.tvaLevel)
            except Exception:
                pass
        params = {k.split(".", 2)[2] for k in keys if k.startswith("tone.") and k.count(".") >= 2}
        for param in params & self._TONE_PARAM_SIGNALS.keys():
            prop = self._TONE_PARAM_SIGNALS[param]
            getattr(self, prop + "Changed").emit(getattr(self, prop))
        if any(p.startswith("tvf_") and p not in ("tvf_cutoff", "tvf_resonance", "tvf_keyfollow") for p in params):
            self.envShapeChanged.emit("TVF")
        if any(p in ("tva_attack", "tva_decay", "tva_sustain", "tva_release") for p in params):
            self.envShapeChanged.emit("TVA")
        if params & {"output_level", "chorus_send", "reverb_send"}:
            self.routingChanged.emit()
        if any(k.endswith(".tvf_keyfollow") for k in keys):
            self.tvfKeyFollowChanged.emit(self.tvfKeyFollow)
        if "common.level" in keys:
            self.masterLevelChanged.emit(self.masterLevel)
        if "common.portamento_time" in keys:
            self.portamentoTimeChanged.emit(self.portamentoTime)
        if "common.analog_feel" in keys:
            self.analogFeelChanged.emit(self.analogFeel)
        if any(k.startswith("common.matrix") for k in keys):
            self.matrixCtrlChanged.emit()
        if any(".pitch_env_" in k for k in keys):
            self.pitchEnvChanged.emit()
            self.envShapeChanged.emit("PITCH")
        if any(k.startswith("effects.chorus") for k in keys):
            self.chorusParamsChanged.emit()
        if any(k.startswith("effects.reverb") for k in keys):
            self.reverbParamsChanged.emit()
        if any(k.startswith("effects.mfx") for k in keys):
            self.mfxParamsChanged.emit()
        if any(k.startswith("tone.") for k in keys):
            try:
                self.toneLevelsChanged.emit(*[t.level for t in self.patch_state.tones])
            except Exception:
                pass
            self.lfoParamsChanged.emit()
            self.pitchCoarseChanged.emit(self.pitchCoarse)
            self.pitchFineChanged.emit(self.pitchFine)
            if any(k.endswith(".pitch_fine") for k in keys):
                self.vaParamsChanged.emit()     # master fine / oscillator tunes
        if macros:
            self.macrosChanged.emit()

    def _macro_name(self, index: int) -> str:
        """Shown name of macro `index` (1-based): its own, else named after its links."""
        try:
            slot = self.patch_state.macros[index - 1]
        except IndexError:
            return f"M{index}"
        if slot.name:
            return slot.name
        return auto_macro_name(index, [self._short_target_name(lk.target_key) for lk in slot.links])

    def _macro_title(self, index: int) -> str:
        """"M1 CUTOFF OFS" (just "M1" while it has no name and no link)."""
        name = self._macro_name(index)
        return name if name == f"M{index}" else f"M{index} {name}"

    @pyqtProperty("QVariantList", notify=macrosChanged)
    def macroNames(self) -> list:
        return [self._macro_name(i) for i in range(1, len(self.patch_state.macros) + 1)]

    @pyqtProperty("QVariantList", notify=macrosChanged)
    def macroCustomNames(self) -> list:
        """Names typed by the user ("" = automatic)."""
        return [s.name for s in self.patch_state.macros]

    @pyqtProperty("QVariantList", notify=macrosChanged)
    def macroValues(self) -> list:
        return [float(s.value) for s in self.patch_state.macros]

    @pyqtProperty("QVariantList", notify=macrosChanged)
    def macroLinkCounts(self) -> list:
        return [len(s.links) for s in self.patch_state.macros]

    @pyqtSlot(int, result="QVariantList")
    def getMacroLinks(self, index: int) -> list:
        """Assigned targets for macro 1..8 with live sounding values."""
        if not (1 <= index <= len(self.patch_state.macros)):
            return []
        out = []
        for pos, link in enumerate(self.patch_state.macros[index - 1].links):
            entry = self._macroEntry(link.target_key)
            # One row per link; tone.all / multi-part links show the first live value
            concretes = self._concreteKeys(link)
            concrete = concretes[0] if concretes else link.target_key
            out.append({
                "pos": pos,
                "key": link.target_key,
                "concrete": concrete,
                "title": entry["title"] if entry else link.target_key,
                "category": entry["category"] if entry else "",
                "polarity": link.polarity,
                "depth": link.depth,
                "span": float(entry["span"]) if entry else 127.0,
                "min": float(entry["min"]) if entry else 0.0,
                "max": float(entry["max"]) if entry else 127.0,
                "liveValue": self._readAbsolute(concrete) if concretes else 0.0,
                "partScoped": link.target_key.startswith(self._PART_SCOPED_PREFIXES),
                "perfOnly": link.target_key.startswith(("part.", "effects.mfx2_", "effects.mfx3_")),
                "parts": list(link.parts),
            })
        return out

    @pyqtSlot(str, str, result="QVariantList")
    def getMacroTargets(self, category: str = "ALL", query: str = "") -> list:
        return filter_macro_targets(category, query)

    @pyqtSlot(int, str)
    def setMacroName(self, index: int, name: str) -> None:
        if 1 <= index <= len(self.patch_state.macros):
            clean = (name or "").strip().upper()[:14]      # "" = automatic
            self.patch_state.macros[index - 1].name = clean
            self.macrosChanged.emit()

    @pyqtSlot(int, str)
    def addMacroTarget(self, index: int, key: str) -> None:
        """Add link with defaults (polarity +, depth 50%). No duplicates."""
        if not (1 <= index <= len(self.patch_state.macros)):
            return
        if self._macroEntry(key) is None:
            return
        slot = self.patch_state.macros[index - 1]
        if any(li.target_key == key for li in slot.links):
            return
        from ...core.patch_state import MacroLink

        slot.links.append(MacroLink(key, 1, 0.5))
        with self._macroWrites():
            for concrete in self._concreteKeys(slot.links[-1]):
                if self._macroKeyReady(concrete):
                    self._ensureBase(concrete)
            self._recomputeForMacro(index - 1)
        self.macrosChanged.emit()

    @pyqtSlot(int, int)
    def removeMacroTarget(self, index: int, pos: int) -> None:
        if 1 <= index <= len(self.patch_state.macros):
            slot = self.patch_state.macros[index - 1]
            if 0 <= pos < len(slot.links):
                dropped = self._concreteKeys(slot.links[pos])
                slot.links.pop(pos)
                with self._macroWrites():
                    self._releaseKeys(dropped)
                self.macrosChanged.emit()

    def _releaseKeys(self, keys: list[str]) -> None:
        """Params a link stopped driving go back to base + remaining macros."""
        for key in keys:
            if key in self.patch_state.macro_bases:
                self._recomputeTarget(key)
        if keys:
            self._emitForMacroKeys(set(keys))

    def _setLinkParts(self, index: int, pos: int, parts: list[int]) -> None:
        if not 1 <= index <= len(self.patch_state.macros):
            return
        slot = self.patch_state.macros[index - 1]
        if not 0 <= pos < len(slot.links):
            return
        link = slot.links[pos]
        before = self._concreteKeys(link)
        link.parts = parts
        link.__post_init__()  # normalize
        after = set(self._concreteKeys(link))
        with self._macroWrites():
            self._releaseKeys([k for k in before if k not in after])
            self._recomputeForMacro(index - 1)
        self.macrosChanged.emit()

    @pyqtSlot(int, int, str)
    def setMacroLinkPartMode(self, index: int, pos: int, mode: str) -> None:
        """Part target of a link: "edit" (edited part) or "all" (sounding parts)."""
        self._setLinkParts(index, pos, [0] if str(mode).lower() == "all" else [])

    @pyqtSlot(int, int, int)
    def toggleMacroLinkPart(self, index: int, pos: int, part: int) -> None:
        """Toggle one fixed part (1..16); none left falls back to the edited part."""
        if not 1 <= index <= len(self.patch_state.macros):
            return
        links = self.patch_state.macros[index - 1].links
        if not 0 <= pos < len(links) or not 1 <= int(part) <= 16:
            return
        current = [p for p in links[pos].parts if p != 0]
        n = int(part)
        self._setLinkParts(index, pos, [p for p in current if p != n] if n in current else current + [n])

    @pyqtSlot(int, int, int, float)
    def setMacroLink(self, index: int, pos: int, polarity: int, depth: float) -> None:
        if 1 <= index <= len(self.patch_state.macros):
            slot = self.patch_state.macros[index - 1]
            if 0 <= pos < len(slot.links):
                link = slot.links[pos]
                link.polarity = 1 if polarity >= 0 else -1
                link.depth = max(0.0, min(1.0, float(depth)))
                self._recomputeForMacro(index - 1)
                self.macrosChanged.emit()

    @pyqtSlot(int, float)
    def setMacro(self, index: int, value: float) -> None:
        """Drive macro knob 1..8 (value in [-1, 1]) with summed fan-out."""
        if not (1 <= index <= len(self.patch_state.macros)):
            return
        slot = self.patch_state.macros[index - 1]
        slot.value = max(-1.0, min(1.0, float(value)))
        with self._macroWrites():
            self._recomputeForMacro(index - 1)
        self.macrosChanged.emit()

    def _recomputeForMacro(self, macro_idx: int) -> None:
        touched: set[str] = set()
        for link in self.patch_state.macros[macro_idx].links:
            for concrete in self._concreteKeys(link):
                if not self._macroKeyReady(concrete):
                    continue
                self._ensureBase(concrete)
                self._recomputeTarget(concrete)
                touched.add(concrete)
        if touched:
            self._emitForMacroKeys(touched, macros=False)   # every caller emits macrosChanged

    @pyqtSlot(int)
    def openMacroAssign(self, index: int) -> None:
        self.requestOpenMacroAssign.emit(max(1, min(8, int(index))))
