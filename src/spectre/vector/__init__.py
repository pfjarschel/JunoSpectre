"""Vector synthesis, wavetable morphing, and motion gesture engine."""

from .engine import MorphMode, VectorEngine, VectorState
from .math import (
    CrossfadeCurve,
    calculate_cartesian_levels,
    calculate_wavetable_levels,
    clamp_coordinate,
)
from .motion import (
    AutomatorType,
    LoopMode,
    MotionRecorder,
    RecorderState,
    TrajectoryPoint,
)

__all__ = [
    "CrossfadeCurve",
    "calculate_cartesian_levels",
    "calculate_wavetable_levels",
    "clamp_coordinate",
    "MorphMode",
    "VectorEngine",
    "VectorState",
    "AutomatorType",
    "LoopMode",
    "MotionRecorder",
    "RecorderState",
    "TrajectoryPoint",
]
