"""Automation lane math: the value a clip outputs at a position, and how many
SysEx writes per second a playing clip costs.

Values travel as integer levels 0..LEVELS over the target's range: a change
of level is one write per concrete parameter, the same level twice is none.
Empty steps hold the last set value; a gliding step ramps from its value to
the next set step's, arriving as that step starts.
"""

from __future__ import annotations

import math
import random
from typing import Optional, Tuple

from ..core.protocol_base import MIN_DT1_GAP_S
from .models import AutomationClip

LEVELS = 127
# Mid-glide a lane sends at most one value per this interval (a stepped value
# always goes out on its step). 20 ms = 50 Hz, smooth for filter sweeps.
GLIDE_MIN_INTERVAL_S = 0.020
# Lanes send ahead of the beat so a stepped value is in place when the notes
# of that step sound (SysEx goes UI thread -> writer thread -> 4 ms paced wire).
LOOKAHEAD_S = 0.010
# The wire carries at most one DT1 per MIN_DT1_GAP_S; half of it is left to
# live control (knobs, macros, the vector pad).
WIRE_WRITES_PER_S = 1.0 / MIN_DT1_GAP_S
AUTOMATION_BUDGET_WPS = WIRE_WRITES_PER_S / 2


def level_of(value: float) -> int:
    return max(0, min(LEVELS, int(round(float(value) * LEVELS))))


def seconds_to_ticks(seconds: float, tick_s: float) -> int:
    return max(1, math.ceil(seconds / tick_s - 1e-9)) if tick_s > 0 else 1


# A segment: the set step a position follows and where it ramps to.
# (start_step, start_level, end_level, span_ticks); span 0 = hold.
Segment = Tuple[int, int, int, int]


def segment_at(clip: AutomationClip, step_idx: int, step_ticks: int) -> Optional[Segment]:
    """The segment step_idx lies in, or None when the clip has no set step."""
    n = clip.length
    steps = clip.steps
    start = next(((step_idx - back) % n for back in range(n) if steps[(step_idx - back) % n].is_set), None)
    if start is None:
        return None
    s = steps[start]
    lvl = level_of(s.value)
    if not s.glide:
        return start, lvl, lvl, 0
    ahead = next((d for d in range(1, n + 1) if steps[(start + d) % n].is_set), n)
    nxt = steps[(start + ahead) % n]
    return start, lvl, level_of(nxt.value), ahead * step_ticks


def level_in_segment(seg: Segment, n: int, step_idx: int, tick_in_step: int, step_ticks: int) -> Tuple[int, bool]:
    """(level, mid_glide) at a position inside its segment."""
    start, a, b, span = seg
    if not span or a == b:
        return a, False
    since = ((step_idx - start) % n) * step_ticks + tick_in_step
    return int(round(a + (b - a) * since / span)), since > 0


def clip_writes_per_loop(clip: AutomationClip, step_ticks: int, cap_ticks: int) -> int:
    """Value changes one pass of the clip sends (looping: the last value
    leads into the first)."""
    n = clip.length
    set_idx = [i for i, s in enumerate(clip.steps[:n]) if s.is_set]
    if not set_idx:
        return 0
    writes = 0
    for j, i in enumerate(set_idx):
        s = clip.steps[i]
        nxt = set_idx[(j + 1) % len(set_idx)]
        gap = ((nxt - i) % n) or n
        here, there = level_of(s.value), level_of(clip.steps[nxt].value)
        prev = level_of(clip.steps[set_idx[j - 1]].value)
        prev_glides = clip.steps[set_idx[j - 1]].glide
        # Arriving on this step: a jump unless the previous segment glided here
        if here != prev and not (prev_glides and len(set_idx) > 1):
            writes += 1
        if s.glide and here != there:
            writes += min(abs(there - here), math.ceil(gap * step_ticks / cap_ticks))
    return writes


def clip_writes_per_second(clip: AutomationClip, step_ticks: int, tick_s: float) -> float:
    """Average value changes per second while the clip loops."""
    loop_s = clip.length * step_ticks * tick_s
    if loop_s <= 0:
        return 0.0
    cap = seconds_to_ticks(GLIDE_MIN_INTERVAL_S, tick_s)
    return clip_writes_per_loop(clip, step_ticks, cap) / loop_s


def clip_curve(clip: AutomationClip) -> list[Optional[Tuple[float, float]]]:
    """What the clip plays across each step, as (start, end) in 0..1: flat
    on held steps, sloped on glides. None everywhere when nothing is set."""
    n = clip.length
    out: list[Optional[Tuple[float, float]]] = []
    for i in range(n):
        seg = segment_at(clip, i, 1)
        if seg is None:
            return [None] * n
        a = level_in_segment(seg, n, i, 0, 1)[0]
        b = level_in_segment(seg, n, i, 1, 1)[0] if seg[3] else a
        out.append((a / LEVELS, b / LEVELS))
    return out


def shape_values(shape: str, n: int) -> list[Tuple[float, bool]]:
    """(value, glide) for every step of an n-step clip."""

    def at(i: int) -> float:
        x = i / n
        if shape == "RAMP UP":
            return i / max(1, n - 1)
        if shape == "RAMP DN":
            return 1.0 - i / max(1, n - 1)
        if shape == "TRI":
            return 1.0 - abs(2.0 * x - 1.0)
        if shape == "SINE":
            return 0.5 + 0.5 * math.sin(2.0 * math.pi * x)
        if shape == "SQUARE":
            return 1.0 if x < 0.5 else 0.0
        return random.random()

    glide = shape not in ("SQUARE", "RANDOM")   # hard edges; random = sample & hold
    return [(round(at(i), 4), glide) for i in range(n)]
