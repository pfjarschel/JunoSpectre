"""Versioned `.spectre` preset envelope (format v1).

Design (see Patch Librarian proposal):
- Files on disk are the source of truth for user patches.
- SQLite is only a rebuildable index/cache over them.
- HW (Roland) params and Spectre-only params live in separate namespaces
  so future engine modes (vector/wavetable/VA/sequencer/macros) never break
  old files: unknown keys are preserved on load/save (forward compat).
- `raw_regions` (exact device bytes) always round-trips for unmodeled residue.

Layout:
{
  "format_version": 1,
  "kind": "patch" | "performance" | "vector_set" | "session",
  "meta": {"name","category","tags","favorite","rating","comment","author","created","modified"},
  "hw_patch": {...PatchState as dict, raw_regions as lists...},
  "spectre": {...opaque engine extras...},
  "synth_ref": {"source": "factory|synth-user|null", "msb","lsb","pc"} | None,
  + any unknown top-level keys preserved verbatim
}
"""

from __future__ import annotations

import copy
import dataclasses
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .patch_state import PatchState

FORMAT_VERSION = 1
KINDS = ("patch", "performance", "vector_set", "session", "playlist")
SOURCES = ("factory", "synth-user", "file", None)

_TOP_LEVEL_KNOWN = {"format_version", "kind", "meta", "hw_patch", "spectre", "synth_ref"}


def default_meta(name: str = "JUNO SPECTRE", category: str = "") -> Dict[str, Any]:
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return {
        "name": name,
        "category": category,
        "tags": [],
        "favorite": False,
        "rating": 0,
        "comment": "",
        "author": "",
        "created": now,
        "modified": now,
    }


def _raw_regions_to_json(raw: Dict[str, list[bytes]]) -> Dict[str, list[list[int]]]:
    out: Dict[str, list[list[int]]] = {}
    for key, chunks in (raw or {}).items():
        out[key] = [list(bytes(c)) for c in chunks]
    return out


def _raw_regions_from_json(raw: Any) -> Dict[str, list[bytes]]:
    out: Dict[str, list[bytes]] = {}
    if not isinstance(raw, dict):
        return out
    for key, chunks in raw.items():
        try:
            out[str(key)] = [bytes(list(c)) for c in chunks]
        except (TypeError, ValueError):
            continue
    return out


def patch_state_to_dict(ps: PatchState) -> Dict[str, Any]:
    """Serialize PatchState to plain JSON-safe dict (bytes -> lists)."""
    d = dataclasses.asdict(ps)
    d["raw_regions"] = _raw_regions_to_json(ps.raw_regions)
    return d


def _safe_construct(cls: Any, data: Any, default: Any) -> Any:
    """Build dataclass `cls` from dict, dropping unknown keys, keeping defaults."""
    if not isinstance(data, dict):
        return copy.deepcopy(default)
    try:
        fields = {f.name for f in dataclasses.fields(cls)}
        kwargs = {k: v for k, v in data.items() if k in fields}
        return cls(**kwargs)
    except Exception:
        return copy.deepcopy(default)


def patch_state_from_dict(d: Dict[str, Any]) -> PatchState:
    """Tolerant decode: unknown keys ignored, missing keys fall back to defaults."""
    from .patch_state import (
        EffectsState,
        PatchCommonState,
        PatchState as PS,
        PerfFxState,
        PerfMfxSlotState,
        PerfPartState,
        StepLfoState,
        ToneState,
        default_macro_slots,
    )
    from .patch_state import MacroLink, MacroSlot

    base = PS()
    if not isinstance(d, dict):
        return base
    try:
        out = PS()
        out.sound_mode = str(d.get("sound_mode", out.sound_mode))
        out.common = _safe_construct(PatchCommonState, d.get("common"), base.common)
        # matrix_ctrls need explicit rebuild (list of dataclasses)
        try:
            from .patch_state import MatrixCtrlState

            raw_mats = (d.get("common") or {}).get("matrix_ctrls") if isinstance(d.get("common"), dict) else None
            if isinstance(raw_mats, list) and raw_mats:
                mats = []
                for m in raw_mats[:4]:
                    mats.append(_safe_construct(MatrixCtrlState, m, MatrixCtrlState()))
                while len(mats) < 4:
                    mats.append(MatrixCtrlState())
                out.common.matrix_ctrls = mats
        except Exception:
            pass
        raw_tones = d.get("tones")
        if isinstance(raw_tones, list) and raw_tones:
            tones = []
            for i, t in enumerate(raw_tones[:4], start=1):
                tone = _safe_construct(ToneState, t, ToneState(tone_index=i))
                tone.tone_index = i
                # step lists / matrix switches may be missing -> keep dataclass defaults
                tones.append(tone)
            while len(tones) < 4:
                tones.append(ToneState(tone_index=len(tones) + 1))
            out.tones = tones
        out.effects = _safe_construct(EffectsState, d.get("effects"), base.effects)
        out.step_lfo = _safe_construct(StepLfoState, d.get("step_lfo"), base.step_lfo)
        raw_parts = d.get("perf_parts")
        if isinstance(raw_parts, list) and raw_parts:
            parts = [_safe_construct(PerfPartState, p, PerfPartState()) for p in raw_parts[:16]]
            if len(parts) == 16:
                out.perf_parts = parts
        raw_fx = d.get("perf_fx")
        if isinstance(raw_fx, dict):
            fx = _safe_construct(PerfFxState, raw_fx, PerfFxState())
            try:
                for slot_name in ("mfx1", "mfx2", "mfx3"):
                    raw_slot = raw_fx.get(slot_name)
                    if isinstance(raw_slot, dict):
                        setattr(fx, slot_name,
                                _safe_construct(PerfMfxSlotState, raw_slot, PerfMfxSlotState()))
            except Exception:
                pass
            out.perf_fx = fx
        for key in ("auto_detune", "auto_detune_cents"):
            if key in d:
                try:
                    setattr(out, key, d[key])
                except Exception:
                    pass
        if isinstance(d.get("perf_name"), str) and d["perf_name"]:
            out.perf_name = str(d["perf_name"])[:12]
        if isinstance(d.get("active_perf_part"), int):
            try:
                out.active_perf_part = max(1, min(16, int(d["active_perf_part"])))
            except (TypeError, ValueError):
                pass
        for key in ("custom_detune_cache", "va_pw", "va_pwm"):
            if isinstance(d.get(key), list):
                try:
                    setattr(out, key, list(d[key]))
                except Exception:
                    pass
        # macros: list of {name, value, links:[{target_key,polarity,depth}]}
        if isinstance(d.get("macros"), list) and d["macros"]:
            try:
                slots = []
                for m in d["macros"][:16]:
                    if not isinstance(m, dict):
                        continue
                    links = []
                    for lk in (m.get("links") or [])[:16]:
                        if isinstance(lk, dict):
                            links.append(_safe_construct(MacroLink, lk, MacroLink()))
                    slot = MacroSlot(
                        name=str(m.get("name", "MACRO"))[:14] or "MACRO",
                        value=float(m.get("value", 0.0)),
                        links=links,
                    )
                    slots.append(slot)
                if slots:
                    out.macros = slots
            except Exception:
                out.macros = default_macro_slots()
        if isinstance(d.get("macro_bases"), dict):
            try:
                out.macro_bases = {str(k): float(v) for k, v in d["macro_bases"].items()}
            except Exception:
                out.macro_bases = {}
        out.raw_regions = _raw_regions_from_json(d.get("raw_regions"))
        return out
    except Exception:
        return base


def normalize_meta(meta: Any, fallback_name: str = "", fallback_category: str = "") -> Dict[str, Any]:
    m = default_meta()
    if isinstance(meta, dict):
        for key in ("name", "category", "comment", "author", "created", "modified"):
            if key in meta and meta[key] is not None:
                m[key] = str(meta[key])
        if isinstance(meta.get("tags"), list):
            m["tags"] = [str(t)[:32] for t in meta["tags"][:16]]
        m["favorite"] = bool(meta.get("favorite", False))
        try:
            m["rating"] = max(0, min(5, int(meta.get("rating", 0))))
        except (TypeError, ValueError):
            m["rating"] = 0
    if fallback_name and not m["name"]:
        m["name"] = fallback_name
    if fallback_category and not m["category"]:
        m["category"] = fallback_category
    return m


def normalize_synth_ref(ref: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(ref, dict):
        return None
    source = ref.get("source")
    if source not in ("factory", "synth-user"):
        return None
    try:
        return {
            "source": source,
            "msb": int(ref.get("msb", 87)),
            "lsb": int(ref.get("lsb", 64)),
            "pc": int(ref.get("pc", 0)),
        }
    except (TypeError, ValueError):
        return None


def save_spectre(
    path: str | Path,
    patch_state: PatchState,
    meta: Optional[Dict[str, Any]] = None,
    spectre: Optional[Dict[str, Any]] = None,
    synth_ref: Optional[Dict[str, Any]] = None,
    kind: str = "patch",
    extra: Optional[Dict[str, Any]] = None,
) -> Path:
    """Write a versioned `.spectre` file. Returns the path written."""
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}, got {kind!r}")
    p = Path(path)
    if p.suffix != ".spectre":
        p = p.with_suffix(".spectre")
    m = normalize_meta(meta, fallback_name=patch_state.common.name)
    # Keep meta.name and hw name in sync (meta wins on load, hw wins on sounding)
    hw = patch_state_to_dict(patch_state)
    payload: Dict[str, Any] = {}
    if isinstance(extra, dict):
        for k, v in extra.items():
            if k not in _TOP_LEVEL_KNOWN:
                payload[k] = v
    payload.update(
        {
            "format_version": FORMAT_VERSION,
            "kind": kind,
            "meta": m,
            "hw_patch": hw,
            "spectre": dict(spectre) if isinstance(spectre, dict) else {},
            "synth_ref": normalize_synth_ref(synth_ref),
        }
    )
    p.parent.mkdir(parents=True, exist_ok=True)
    # Touch modified timestamp
    payload["meta"]["modified"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return p


def load_spectre(path: str | Path) -> Dict[str, Any]:
    """Load a `.spectre` file.

    Returns dict with keys: patch_state, meta, spectre, synth_ref, kind,
    format_version, extra (unknown top-level keys), path.
    Raises ValueError/FileNotFoundError on bad input.
    """
    p = Path(path)
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{p}: top-level JSON must be an object")
    version = raw.get("format_version", 0)
    if version != FORMAT_VERSION:
        raise ValueError(f"{p}: unsupported format_version {version!r} (expected {FORMAT_VERSION})")
    kind = raw.get("kind", "patch")
    if kind not in KINDS:
        raise ValueError(f"{p}: unsupported kind {kind!r}")
    hw = raw.get("hw_patch")
    if not isinstance(hw, dict):
        raise ValueError(f"{p}: missing 'hw_patch' object")
    ps = patch_state_from_dict(hw)
    meta = normalize_meta(raw.get("meta"), fallback_name=ps.common.name)
    # meta.name is the display truth -> mirror into hw state for sounding consistency
    if meta.get("name"):
        ps.common.name = str(meta["name"])[:12]
    spectre = dict(raw["spectre"]) if isinstance(raw.get("spectre"), dict) else {}
    extra = {k: v for k, v in raw.items() if k not in _TOP_LEVEL_KNOWN}
    return {
        "patch_state": ps,
        "meta": meta,
        "spectre": spectre,
        "synth_ref": normalize_synth_ref(raw.get("synth_ref")),
        "kind": kind,
        "format_version": version,
        "extra": extra,
        "path": str(p),
    }


def describe_for_index(loaded: Dict[str, Any]) -> Tuple[str, str, list[str], bool, int, int]:
    """Extract (name, category, tags, favorite, rating, format_version) for DB indexing."""
    meta = loaded.get("meta", {})
    return (
        str(meta.get("name", "")),
        str(meta.get("category", "")),
        list(meta.get("tags", [])) if isinstance(meta.get("tags"), list) else [],
        bool(meta.get("favorite", False)),
        int(meta.get("rating", 0) or 0),
        int(loaded.get("format_version", FORMAT_VERSION) or FORMAT_VERSION),
    )


# ---------------------------------------------------------------------------
# Playlists (kind="playlist"): ordered songs for live use.
# Hybrid link + snapshot design: each entry links a performance file AND embeds
# a snapshot of it, so a moved/deleted file degrades to a stale badge instead
# of a dead song. Entry shape:
# {
#   "name": "Song title", "perf_path": "/path/to/perf.spectre" | "",
#   "synth_ref": {...} | None, "snapshot_hash": "sha1:..." | "",
#   "cached": {<patch_state dict>} | None,   # embedded fallback image
#   "macros": [...],                          # song-local macro values
#   "seq_pattern": [bool x16] | None,
# }
# ---------------------------------------------------------------------------

def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def snapshot_hash_of(patch_dict: Any) -> str:
    """Stable content hash for a patch-state dict (link/stale detection)."""
    import hashlib

    try:
        return "sha1:" + hashlib.sha1(_canonical_json(patch_dict).encode("utf-8")).hexdigest()
    except Exception:
        return ""


def make_playlist_entry(name: str, patch_dict: Optional[Dict[str, Any]] = None,
                        perf_path: str = "",
                        synth_ref: Optional[Dict[str, Any]] = None,
                        macros: Optional[list] = None,
                        seq_pattern: Optional[list] = None) -> Dict[str, Any]:
    """Build one playlist entry with an embedded snapshot of the performance."""
    cached = copy.deepcopy(patch_dict) if isinstance(patch_dict, dict) else None
    return {
        "name": str(name or "Untitled")[:48],
        "perf_path": str(perf_path or ""),
        "synth_ref": normalize_synth_ref(synth_ref),
        "snapshot_hash": snapshot_hash_of(cached) if cached is not None else "",
        "cached": cached,
        "macros": list(macros) if isinstance(macros, list) else [],
        "seq_pattern": [bool(x) for x in seq_pattern[:16]] if isinstance(seq_pattern, list) else None,
    }


def playlist_entry_status(entry: Dict[str, Any]) -> str:
    """Link health of one entry: 'ok' | 'updated' | 'missing' | 'unsaved'.

    'ok' = linked file present and hash matches snapshot.
    'updated' = file present but changed since the snapshot (refresh offered).
    'missing' = linked file gone (embedded snapshot still playable).
    'unsaved' = entry was never linked to a file (snapshot only).
    """
    if not isinstance(entry, dict):
        return "unsaved"
    path = str(entry.get("perf_path") or "")
    if not path:
        return "unsaved" if entry.get("cached") is not None else "missing"
    p = Path(path)
    if not p.is_file():
        return "missing"
    try:
        loaded = load_spectre(p)
        live_hash = snapshot_hash_of(patch_state_to_dict(loaded["patch_state"]))
        return "ok" if live_hash == str(entry.get("snapshot_hash") or "") else "updated"
    except Exception:
        return "missing"


def refresh_entry_snapshot(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Re-read the linked file into the entry snapshot. Returns the entry."""
    path = str(entry.get("perf_path") or "")
    loaded = load_spectre(path)  # raises when unreadable; caller reports
    cached = patch_state_to_dict(loaded["patch_state"])
    entry["cached"] = cached
    entry["snapshot_hash"] = snapshot_hash_of(cached)
    entry["synth_ref"] = normalize_synth_ref(loaded.get("synth_ref"))
    if not str(entry.get("name") or ""):
        entry["name"] = str((loaded.get("meta") or {}).get("name") or "Untitled")[:48]
    return entry
