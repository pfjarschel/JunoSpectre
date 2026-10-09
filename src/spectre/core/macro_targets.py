"""Customizable relative-macro target catalog + pure offset resolver math.

Target key taxonomy (all continuous numerics; enums excluded):
  common.<param>            Patch Common (level, pan, offsets, porta, analog)
  effects.<param>            Chorus/Reverb/MFX sends + times/depths
  tone.<i>.<param>           Per-tone i=1..4 (tvf_*, tva_*, pitch, lfo, sends)
  tone.all.<param>           Fan-out alias: same delta applied to each tone's own base
  vector.<param>             x, y (0..1), speed, bpm

Each entry: {key, title, category, min, max, span}.
span = full-scale delta for macro=+1 @ depth=1 (sounding = base + pol*depth*span*value).
"""

from __future__ import annotations


def _trio(key: str, title: str, category: str, lo: float, hi: float, span: float) -> dict:
    return {"key": key, "title": title, "category": category,
            "min": lo, "max": hi, "span": float(span)}


def build_macro_catalog() -> list[dict]:
    cat: list[dict] = []
    # --- COMMON ---
    cat += [
        _trio("common.level", "Master Level", "COMMON", 0, 127, 127),
        _trio("common.pan", "Master Pan", "COMMON", 0, 127, 63),
        _trio("common.cutoff_offset", "Filter Cutoff Offset", "COMMON", 1, 127, 63),
        _trio("common.resonance_offset", "Filter Reso Offset", "COMMON", 1, 127, 63),
        _trio("common.attack_offset", "Amp Attack Offset", "COMMON", 1, 127, 63),
        _trio("common.release_offset", "Amp Release Offset", "COMMON", 1, 127, 63),
        _trio("common.portamento_time", "Portamento Time", "COMMON", 0, 127, 127),
        _trio("common.analog_feel", "Analog Feel", "COMMON", 0, 127, 127),
    ]
    # --- FX ---
    cat += [
        _trio("effects.chorus_level", "Chorus Level", "FX", 0, 127, 127),
        _trio("effects.chorus_rate", "Chorus Rate", "FX", 0, 127, 127),
        _trio("effects.chorus_depth", "Chorus Depth", "FX", 0, 127, 127),
        _trio("effects.chorus_predelay", "Chorus PreDelay", "FX", 0, 127, 127),
        _trio("effects.chorus_feedback", "Chorus Feedback", "FX", 0, 127, 127),
        _trio("effects.reverb_level", "Reverb Level", "FX", 0, 127, 127),
        _trio("effects.reverb_time", "Reverb Time", "FX", 0, 127, 127),
        _trio("effects.reverb_damp", "Reverb Damp", "FX", 0, 127, 127),
        _trio("effects.reverb_predelay", "Reverb PreDelay", "FX", 0, 127, 127),
        _trio("effects.reverb_diffusion", "Reverb Diffusion", "FX", 0, 127, 127),
        _trio("effects.reverb_tone", "Reverb Tone", "FX", 0, 127, 127),
        _trio("effects.mfx_dry_send", "MFX Dry Send", "FX", 0, 127, 127),
        _trio("effects.mfx_chorus_send", "MFX Chorus Send", "FX", 0, 127, 127),
        _trio("effects.mfx_reverb_send", "MFX Reverb Send", "FX", 0, 127, 127),
    ]
    # --- PER-TONE + ALL ---
    per_tone = [
        ("tvf_cutoff", "Cutoff", "FILTER", 0, 127, 127),
        ("tvf_resonance", "Resonance", "FILTER", 0, 127, 127),
        ("tvf_env_depth", "Filter Env Depth", "FILTER", 1, 127, 63),
        ("tvf_attack", "Filter Attack", "FILTER", 0, 127, 127),
        ("tvf_decay", "Filter Decay", "FILTER", 0, 127, 127),
        ("tvf_sustain", "Filter Sustain", "FILTER", 0, 127, 127),
        ("tvf_release", "Filter Release", "FILTER", 0, 127, 127),
        ("tva_level", "Amp Level", "AMP", 0, 127, 127),
        ("tva_pan", "Pan", "AMP", 0, 127, 63),
        ("tva_attack", "Amp Attack", "AMP", 0, 127, 127),
        ("tva_decay", "Amp Decay", "AMP", 0, 127, 127),
        ("tva_sustain", "Amp Sustain", "AMP", 0, 127, 127),
        ("tva_release", "Amp Release", "AMP", 0, 127, 127),
        ("pitch_coarse", "Coarse Tune", "PITCH", 16, 112, 48),
        ("pitch_fine", "Fine Tune", "PITCH", 14, 114, 50),
        ("lfo1_rate", "LFO1 Rate", "LFO", 0, 127, 127),
        ("lfo1_pitch_depth", "LFO1 Pitch Depth", "LFO", 1, 127, 63),
        ("lfo1_tvf_depth", "LFO1 Filter Depth", "LFO", 1, 127, 63),
        ("lfo1_tva_depth", "LFO1 Amp Depth", "LFO", 1, 127, 63),
        ("lfo1_pan_depth", "LFO1 Pan Depth", "LFO", 1, 127, 63),
        ("lfo2_rate", "LFO2 Rate", "LFO", 0, 127, 127),
        ("lfo2_pitch_depth", "LFO2 Pitch Depth", "LFO", 1, 127, 63),
        ("lfo2_tvf_depth", "LFO2 Filter Depth", "LFO", 1, 127, 63),
        ("lfo2_tva_depth", "LFO2 Amp Depth", "LFO", 1, 127, 63),
        ("lfo2_pan_depth", "LFO2 Pan Depth", "LFO", 1, 127, 63),
        ("chorus_send", "Chorus Send", "FX", 0, 127, 127),
        ("reverb_send", "Reverb Send", "FX", 0, 127, 127),
        ("output_level", "Output Level", "AMP", 0, 127, 127),
    ]
    for i in range(1, 5):
        for param, title, category, lo, hi, span in per_tone:
            cat.append(_trio("tobe_placeholder", "", "", 0, 0, 0))  # placeholder removed below
            cat.pop()
            cat.append(_trio(f"tone.{i}.{param}", f"T{i} {title}", category, lo, hi, span))
    for param, title, category, lo, hi, span in per_tone:
        cat.append(_trio(f"tone.all.{param}", f"All {title}", category, lo, hi, span))
    # --- MORPH (2D vector / wavetable morphing) ---
    cat += [
        _trio("vector.x", "Morph X", "MORPH", 0.0, 1.0, 1.0),
        _trio("vector.y", "Morph Y", "MORPH", 0.0, 1.0, 1.0),
        _trio("vector.w", "Wavetable Pos", "MORPH", 0.0, 1.0, 1.0),
        _trio("vector.speed", "Motion Speed", "MORPH", 0.25, 4.0, 1.75),
        _trio("vector.bpm", "Tempo BPM", "MORPH", 20.0, 300.0, 140.0),
    ]
    # --- PERFORMANCE (Parts 1..16 mixer & offsets) ---
    for p in range(1, 17):
        cat += [
            _trio(f"perf.part.{p}.level", f"Part {p} Level", "PERFORMANCE", 0, 127, 127),
            _trio(f"perf.part.{p}.pan", f"Part {p} Pan", "PERFORMANCE", 0, 127, 63),
            _trio(f"perf.part.{p}.chorus_send", f"Part {p} Chorus Send", "PERFORMANCE", 0, 127, 127),
            _trio(f"perf.part.{p}.reverb_send", f"Part {p} Reverb Send", "PERFORMANCE", 0, 127, 127),
            _trio(f"perf.part.{p}.cutoff_offset", f"Part {p} Cutoff", "PERFORMANCE", 1, 127, 63),
            _trio(f"perf.part.{p}.resonance_offset", f"Part {p} Resonance", "PERFORMANCE", 1, 127, 63),
        ]
    return cat


_CATALOG: list[dict] | None = None


def get_macro_catalog() -> list[dict]:
    global _CATALOG
    if _CATALOG is None:
        _CATALOG = build_macro_catalog()
    return _CATALOG


def get_macro_categories() -> list[str]:
    return ["ALL", "FILTER", "AMP", "PITCH", "LFO", "FX", "COMMON", "MORPH", "PERFORMANCE"]


def filter_macro_targets(category: str = "ALL", query: str = "") -> list[dict]:
    q = (query or "").strip().lower()
    out = []
    for e in get_macro_catalog():
        if category and category != "ALL" and e["category"] != category:
            continue
        if q and q not in e["title"].lower() and q not in e["key"].lower():
            continue
        out.append(e)
    return out


def macro_delta(span: float, polarity: int, depth: float, value: float) -> float:
    """Pure offset math: exact inputs, no clamping (clamp at write)."""
    pol = 1 if polarity >= 0 else -1
    return pol * max(0.0, min(1.0, depth)) * span * max(-1.0, min(1.0, value))


def resolve_sounding(base: float, contributions: list[float], lo: float, hi: float) -> float:
    """Sum exact contributions, clamp only the output. Integer targets round at write."""
    return max(lo, min(hi, base + sum(contributions)))
