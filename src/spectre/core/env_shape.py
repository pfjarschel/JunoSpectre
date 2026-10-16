"""A/D/S/R controls over the Juno's 4-time / 5-level envelopes.

An envelope is (times, levels): times = [T1..T4] (0..127, strongly
exponential), levels = [L0..L4] (TVA: L0 = L4 = 0, fixed). T1 runs L0 -> L1,
T2 L1 -> L2, T3 L2 -> L3 (held while the key is down), T4 L3 -> L4.

Each control moves a group of segments around the peak (whichever of L1/L2
lies further from the centre: 0, or 64 for the bipolar pitch envelope):

  A  every time up to the peak     (T1, plus T2 when L2 is the peak)
  D  every time from the peak to L3 (T2 + T3, or T3 alone)
  S  L3; L2 keeps its relative place between the peak and L3 (a level
     outside that range, e.g. a dip below sustain, keeps its distance to L3)
  R  T4

Times of 0 are instant steps, not segments, and stay 0 (unless a group has
nothing else). All times of a group move by the same delta: on an
exponential time scale that is close to scaling their durations by one
factor, so a curve keeps its character. A group's value is its longest time.
Moves are taken from a snapshot of the curve (`base`), so clamping at 0/127
never flattens the shape over repeated moves.

On a plain ADSR shape (L1 at the top, T3 = 0, L2 = L3, ends at the centre)
every group is one segment and the controls are exactly A = T1, D = T2,
S = L2 = L3, R = T4.
"""

from __future__ import annotations

TOP = 127


def peak_index(levels: list[int], center: int) -> int:
    """1 or 2: the level the attack rises to (the earlier one on a tie)."""
    return 2 if abs(levels[2] - center) > abs(levels[1] - center) else 1


def group(stage: str, times: list[int], levels: list[int], center: int) -> list[int]:
    """Indices into `times` a time control (attack/decay/release) moves."""
    if stage == "release":
        return [3]
    peak = peak_index(levels, center)
    if stage == "attack":
        members = [0] if peak == 1 else [0, 1]
    else:
        members = [1, 2] if peak == 1 else [2]
    return [m for m in members if times[m] > 0] or members[:1]


def value(stage: str, times: list[int], levels: list[int], center: int) -> int:
    """What a control shows: the group's longest time, or L3 for sustain."""
    if stage == "sustain":
        return levels[3]
    return max(times[m] for m in group(stage, times, levels, center))


def apply(stage: str, val: int, cur: tuple, base: tuple, center: int,
          level_range: tuple[int, int]) -> tuple[list[int], list[int]]:
    """New (times, levels) for a control set to `val`.

    cur: the curve now; base: the snapshot the move is taken from. Only the
    stage's own segments change; everything else keeps its current value.
    """
    times, levels = list(cur[0]), list(cur[1])
    b_times, b_levels = base
    if stage == "sustain":
        lo, hi = level_range
        new = max(lo, min(hi, int(val)))
        levels[3] = new
        if peak_index(b_levels, center) == 1:
            peak, l2, l3 = b_levels[1], b_levels[2], b_levels[3]
            if min(peak, l3) <= l2 <= max(peak, l3) and peak != l3:
                levels[2] = round(new + (l2 - l3) / (peak - l3) * (peak - new))
            else:
                levels[2] = l2 + new - l3
            levels[2] = max(lo, min(hi, levels[2]))
        return times, levels
    members = group(stage, b_times, b_levels, center)
    delta = int(val) - max(b_times[m] for m in members)
    for m in members:
        times[m] = max(0, min(127, b_times[m] + delta))
    return times, levels


def is_adsr(times: list[int], levels: list[int], center: int) -> bool:
    return (times[2] == 0 and levels[0] == center and levels[1] == TOP
            and levels[2] == levels[3] and levels[4] == center)


def to_adsr(times: list[int], levels: list[int], center: int) -> tuple[list[int], list[int]]:
    """The plain ADSR that sounds closest: A/D take their group's longest time."""
    a, d = value("attack", times, levels, center), value("decay", times, levels, center)
    s = levels[3]
    return [a, d, 0, times[3]], [center, TOP, s, s, center]
