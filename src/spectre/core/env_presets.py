"""Preset shapes for the hardware multi-segment envelopes (TVF / TVA / Pitch).

Pitch level values are signed (-63..+63, matching setPitchEnvParam semantics).
TVF levels are raw 0..127 blocks [L0..L4]; TVA levels are raw 0..127 [L1..L3].
Canonical ADSR shapes keep L0=0, L1=127, L2=L3, L4=0 (TVF) or L1=127, L2=L3 (TVA)
so the quick ADSR faders still describe them exactly; deliberately custom
presets showcase the multi-segment shapes (UI shows a CUSTOM badge).
"""

from __future__ import annotations

from typing import Dict, List

# Preset name -> segment values (times first, then levels)
ENV_PRESETS: Dict[str, List[dict]] = {
    "PITCH": [
        {"name": "FLAT / INIT", "t": [0, 0, 0, 0], "l": [0, 0, 0, 0, 0]},
        {"name": "BRASS BITE", "t": [15, 30, 40, 20], "l": [-8, 12, 0, 0, 0]},
        {"name": "LASER ZAP", "t": [5, 45, 20, 20], "l": [48, 30, 0, 0, 0]},
        {"name": "KICK THUMP", "t": [2, 25, 10, 15], "l": [60, 0, 0, 0, 0]},
        {"name": "SLOW DIVE", "t": [40, 60, 80, 60], "l": [10, 20, -15, -30, -50]},
        {"name": "DEEP DOWN", "t": [4, 40, 0, 20], "l": [-40, 0, 0, 0, 0]},
        {"name": "BOING", "t": [6, 25, 25, 25], "l": [0, 24, -18, 0, 0]},
    ],
    "TVF": [
        {"name": "INIT FLAT", "t": [0, 0, 0, 0], "l": [0, 127, 127, 127, 0]},
        {"name": "PLUCK", "t": [2, 40, 0, 12], "l": [0, 127, 50, 50, 0]},
        {"name": "SWELL", "t": [70, 0, 0, 40], "l": [0, 127, 127, 127, 0]},
        {"name": "TWO STEP", "t": [5, 50, 60, 20], "l": [0, 127, 30, 95, 0]},
        {"name": "PERC STAB", "t": [0, 15, 0, 6], "l": [0, 127, 8, 8, 0]},
        {"name": "FILTER ZAP", "t": [0, 20, 0, 10], "l": [127, 127, 0, 0, 0]},
    ],
    "TVA": [
        {"name": "INIT GATE", "t": [0, 0, 0, 0], "l": [127, 127, 127]},
        {"name": "ADSR", "t": [10, 40, 0, 30], "l": [127, 80, 80]},
        {"name": "PAD", "t": [80, 30, 40, 60], "l": [127, 96, 110]},
        {"name": "PLUCK", "t": [0, 30, 0, 10], "l": [127, 0, 0]},
        {"name": "E PIANO", "t": [2, 45, 60, 40], "l": [127, 70, 40]},
    ],
}


def env_preset_names(env: str) -> List[str]:
    """Ordered preset names for an envelope ('PITCH' | 'TVF' | 'TVA')."""
    return [p["name"] for p in ENV_PRESETS.get(env.upper(), [])]


def get_env_preset(env: str, name: str) -> dict:
    """Fetch a preset dict by envelope and name, or an empty dict."""
    for p in ENV_PRESETS.get(env.upper(), []):
        if p["name"] == name:
            return p
    return {}
