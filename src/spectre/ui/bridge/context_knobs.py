"""The context knobs: what the 8 on-screen knobs (and a controller's
"context.N" bindings) control on each page."""

from __future__ import annotations

from ...core.arpeggio import FIELD_LABELS as ARP_FIELD_LABELS

# The 8 context knobs of each page (on-screen strip; controllers bind "context.N").
# "" = unused. Keys are macro catalog targets, "macro.N", or the editor-following
# and stepped targets below.
_TONE_SEL = "tone.sel."
CONTEXT_KNOBS: dict[str, list[str]] = {
    "JUNO PCM": [_TONE_SEL + p for p in ("tvf_cutoff", "tvf_resonance", "tvf_env_depth", "tva_level",
                                         "tva_pan", "pitch_coarse", "pitch_fine", "lfo1_rate")],
    "VECTOR": ["vector.x", "vector.y", "vector.orbit_x", "vector.orbit_y", "vector.speed",
               "step.automator", "step.curve", "vector.bpm"],
    "WAVETABLE": ["vector.w", "vector.speed", "step.sweep", "step.curve"]
                 + [f"tone.{i}.tva_level" for i in range(1, 5)],
    "VA": [f"tone.{i}.tva_level" for i in range(1, 5)] + [f"tone.{i}.pitch_fine" for i in range(1, 5)],
    "MOD MATRIX": [f"common.matrix{c}_sens{d}" for d in (1, 2) for c in range(1, 5)],
    "STEP LFO": [_TONE_SEL + f"lfo{n}_{p}" for n in (1, 2) for p in ("rate", "pitch_depth", "tvf_depth", "tva_depth")],
    "MSEG ENVELOPES": [_TONE_SEL + p for p in ("pitch_env_depth", "pitch_env_attack", "pitch_env_decay",
                                               "pitch_env_release", "tvf_env_depth", "tvf_cutoff",
                                               "tvf_resonance", "tva_level")],
    "MFX": [f"mfx.p.{n}" for n in range(1, 9)],
    "ROUTING": [f"tone.{i}.chorus_send" for i in range(1, 5)] + [f"tone.{i}.reverb_send" for i in range(1, 5)],
    "MASTER FX": ["effects.chorus_level", "effects.chorus_rate", "effects.chorus_depth", "effects.chorus_feedback",
                  "effects.reverb_level", "effects.reverb_time", "effects.reverb_damp", "effects.reverb_predelay"],
    "LIVE": [f"macro.{n}" for n in range(1, 9)],
    # SEQUENCER: bank 1 shown here; it follows the track bank (_context_knob_targets)
    "SEQUENCER": [f"seq.swing.{n}" for n in range(1, 9)],
    "ARPEGGIO": [f"arp.{f}" for f in ("style", "motif", "grid", "duration", "octave", "accent",
                                      "velocity", "step")],
    "PERFORMANCE": [f"part.level@{n}" for n in range(1, 9)],
    "MACROS": [f"macro.{n}" for n in range(1, 9)],
}

# Stepped (enum) targets: key -> (title, values, bridge property, bridge setter)
STEPPED = {
    "step.automator": ("Automator", ["none", "circle", "lissajous", "spiral", "chaos"], "automator", "setAutomator"),
    "step.curve": ("Crossfade Curve", ["linear", "equal_power", "normalized"], "curve", "setCurve"),
    "step.sweep": ("Sweep Mode", ["manual", "sine", "triangle", "ramp", "random_step", "chaos"],
                   "wavetableSweepMode", "setWavetableSweepMode"),
}
# Arp knobs step through the synth's own value names (bridge/arpeggio.py)
STEPPED.update({f"arp.{f}": ("Arp " + ("Oct Range" if f == "octave" else f.title()), labels,
                             f"_arp_text_{f}", f"_set_arp_text_{f}")
                for f, labels in ARP_FIELD_LABELS.items()})

# Detune targets the edited-tone fine tune turns into (_ctl_resolve):
# key -> (title, min, max, bridge property, setter)
DETUNE = {
    "detune.master": ("Master Fine Tune", -50, 50, "masterFine", "sculptPitchFine"),
    "detune.auto": ("Auto Detune", 0, 50, "autoDetuneCents", "setAutoDetuneCents"),
}
