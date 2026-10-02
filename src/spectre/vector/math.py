"""Mathematical interpolation engine for 2D Vector and 1D Wavetable morphing.

Calculates real-time TVA level distributions (0..127) across Roland Tones 1-4
using Cartesian 2D coordinates and 1D progressive wavetable scanning.
"""

from __future__ import annotations

import enum
import math
from typing import Tuple


class CrossfadeCurve(str, enum.Enum):
    """Interpolation curve profile for tone crossfading."""
    LINEAR = "linear"
    EQUAL_POWER = "equal_power"


def clamp_coordinate(val: float) -> float:
    """Clamp coordinate to normalized unit interval [0.0, 1.0]."""
    return max(0.0, min(1.0, float(val)))


def calculate_cartesian_levels(
    x: float,
    y: float,
    curve: CrossfadeCurve = CrossfadeCurve.LINEAR,
    max_level: int = 127,
) -> Tuple[int, int, int, int]:
    """Calculate 4 Roland TVA levels from 2D Cartesian coordinates (X, Y).

    Coordinate mapping:
        - NW: Tone 1 (X=0.0, Y=1.0)
        - NE: Tone 2 (X=1.0, Y=1.0)
        - SW: Tone 3 (X=0.0, Y=0.0)
        - SE: Tone 4 (X=1.0, Y=0.0)

    Weights:
        w1 = (1 - X) * Y
        w2 = X * Y
        w3 = (1 - X) * (1 - Y)
        w4 = X * (1 - Y)

    Returns:
        Tuple of (tone_1, tone_2, tone_3, tone_4) levels clamped to [0, max_level].
    """
    cx = clamp_coordinate(x)
    cy = clamp_coordinate(y)

    w1 = (1.0 - cx) * cy
    w2 = cx * cy
    w3 = (1.0 - cx) * (1.0 - cy)
    w4 = cx * (1.0 - cy)

    if curve == CrossfadeCurve.EQUAL_POWER:
        # Equal power uses square-root scaling
        w1 = math.sqrt(max(0.0, w1))
        w2 = math.sqrt(max(0.0, w2))
        w3 = math.sqrt(max(0.0, w3))
        w4 = math.sqrt(max(0.0, w4))

    l1 = max(0, min(max_level, round(w1 * max_level)))
    l2 = max(0, min(max_level, round(w2 * max_level)))
    l3 = max(0, min(max_level, round(w3 * max_level)))
    l4 = max(0, min(max_level, round(w4 * max_level)))

    return (l1, l2, l3, l4)


def calculate_wavetable_levels(
    w: float,
    curve: CrossfadeCurve = CrossfadeCurve.LINEAR,
    max_level: int = 127,
) -> Tuple[int, int, int, int]:
    """Calculate 4 Roland TVA levels from 1D progressive wavetable position W.

    Sequential morphing path:
        W = 0.00 -> 100% Tone 1
        W = 0.33 -> 100% Tone 2
        W = 0.67 -> 100% Tone 3
        W = 1.00 -> 100% Tone 4

    Between nodes, only adjacent tones crossfade while non-adjacent tones remain at 0.

    Returns:
        Tuple of (tone_1, tone_2, tone_3, tone_4) levels clamped to [0, max_level].
    """
    cw = clamp_coordinate(w)

    w1, w2, w3, w4 = 0.0, 0.0, 0.0, 0.0

    if cw <= 1.0 / 3.0:
        # Segment 1: Tone 1 -> Tone 2
        t = cw * 3.0
        w1 = 1.0 - t
        w2 = t
    elif cw <= 2.0 / 3.0:
        # Segment 2: Tone 2 -> Tone 3
        t = (cw - 1.0 / 3.0) * 3.0
        w2 = 1.0 - t
        w3 = t
    else:
        # Segment 3: Tone 3 -> Tone 4
        t = (cw - 2.0 / 3.0) * 3.0
        w3 = 1.0 - t
        w4 = t

    if curve == CrossfadeCurve.EQUAL_POWER:
        w1 = math.sqrt(max(0.0, w1))
        w2 = math.sqrt(max(0.0, w2))
        w3 = math.sqrt(max(0.0, w3))
        w4 = math.sqrt(max(0.0, w4))

    l1 = max(0, min(max_level, round(w1 * max_level)))
    l2 = max(0, min(max_level, round(w2 * max_level)))
    l3 = max(0, min(max_level, round(w3 * max_level)))
    l4 = max(0, min(max_level, round(w4 * max_level)))

    return (l1, l2, l3, l4)
