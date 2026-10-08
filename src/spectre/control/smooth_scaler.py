"""Smooth value scaling and parameter convergence engine.

Resolves parameter jumping on non-motorized controllers during preset switches
using proportional homothety scaling, pickup/catch-up, relative delta, and endless encoder modes.
"""

from __future__ import annotations

import logging
from typing import Tuple

from .models import RelativeEncoderEncoding, ScaleMode

logger = logging.getLogger(__name__)


class SmoothScaler:
    """Controls parameter scaling and eliminates parameter jumping."""

    def __init__(
        self,
        initial_physical: int = 64,
        initial_synth: float = 64.0,
        mode: ScaleMode = ScaleMode.SMOOTH,
        min_value: float = 0.0,
        max_value: float = 127.0,
        sensitivity: float = 1.0,
        encoding: RelativeEncoderEncoding = RelativeEncoderEncoding.BINARY_OFFSET,
    ):
        self.mode = mode
        self.min_value = float(min_value)
        self.max_value = float(max_value)
        self.sensitivity = float(sensitivity)
        self.encoding = encoding

        self._physical_pos: int = int(initial_physical)
        self._synth_val_float: float = float(initial_synth)
        self._last_emitted_int: int = int(round(self._synth_val_float))

        # Initial convergence state
        self._is_converged: bool = (abs(self._physical_pos - self._synth_val_float) < 0.5)

    @property
    def physical_pos(self) -> int:
        """Last received physical MIDI controller position (0..127)."""
        return self._physical_pos

    @property
    def synth_value_float(self) -> float:
        """Current target synth parameter value with floating-point precision."""
        return self._synth_val_float

    @property
    def synth_value(self) -> int:
        """Current target synth parameter value rounded to nearest integer."""
        return int(round(self._synth_val_float))

    @property
    def is_converged(self) -> bool:
        """Whether physical position and synth parameter have converged to 1:1 tracking."""
        return self._is_converged

    def sync_synth_value(self, new_val: float) -> None:
        """Update internal synth value when presets load or parameters are polled.

        Decouples convergence if physical position differs from the new synth value.
        """
        clamped = max(self.min_value, min(self.max_value, float(new_val)))
        self._synth_val_float = clamped
        self._last_emitted_int = int(round(clamped))

        if self.mode == ScaleMode.SMOOTH:
            self._is_converged = (abs(self._physical_pos - self._synth_val_float) < 0.5)
        elif self.mode == ScaleMode.CATCH_UP:
            self._is_converged = (abs(self._physical_pos - self._synth_val_float) < 0.5)

    def reset_physical_pos(self, pos: int) -> None:
        """Directly update known physical position without altering synth value."""
        self._physical_pos = max(0, min(127, int(pos)))
        if self.mode in (ScaleMode.SMOOTH, ScaleMode.CATCH_UP):
            self._is_converged = (abs(self._physical_pos - self._synth_val_float) < 0.5)

    def process(self, physical_input: int) -> Tuple[int, bool, bool]:
        """Process incoming physical MIDI control value.

        Returns:
            Tuple of (current_synth_int, has_value_changed, needs_recenter)
        """
        needs_recenter = False
        prev_int = self._last_emitted_int

        if self.mode == ScaleMode.JUMP:
            self._physical_pos = max(0, min(127, physical_input))
            # Map physical 0..127 to min_value..max_value
            norm = self._physical_pos / 127.0
            self._synth_val_float = self.min_value + norm * (self.max_value - self.min_value)
            self._is_converged = True

        elif self.mode == ScaleMode.SMOOTH:
            p_new = max(0, min(127, physical_input))
            dp = p_new - self._physical_pos
            p_last = self._physical_pos

            if dp != 0:
                if self._is_converged:
                    # Direct 1:1 tracking
                    norm = p_new / 127.0
                    self._synth_val_float = self.min_value + norm * (self.max_value - self.min_value)
                else:
                    # Extreme boundary convergence guarantees
                    if p_new == 127:
                        self._synth_val_float = self.max_value
                        self._is_converged = True
                    elif p_new == 0:
                        self._synth_val_float = self.min_value
                        self._is_converged = True
                    else:
                        v_curr = self._synth_val_float
                        v_max = self.max_value
                        v_min = self.min_value

                        if dp > 0:
                            # Moving Up: dV = dP * (V_max - V_curr) / (P_max - P_last)
                            denom = 127.0 - p_last
                            if denom > 0:
                                dv = dp * ((v_max - v_curr) / denom)
                            else:
                                dv = 0.0
                            v_cand = v_curr + dv
                        else:
                            # Moving Down: dV = |dP| * (V_curr - V_min) / (P_last - P_min)
                            denom = float(p_last)
                            if denom > 0:
                                dv = abs(dp) * ((v_curr - v_min) / denom)
                            else:
                                dv = 0.0
                            v_cand = v_curr - dv

                        # Check for meeting or crossing
                        # If crossing occurred: (p_last - v_curr) and (p_new - v_cand) have different signs
                        # Normalize both to 0..127 for crossing comparison
                        span = max(1e-6, v_max - v_min)
                        v_curr_norm = (v_curr - v_min) / span * 127.0
                        v_cand_norm = (v_cand - v_min) / span * 127.0

                        diff_last = p_last - v_curr_norm
                        diff_new = p_new - v_cand_norm

                        if (diff_last * diff_new <= 0) or abs(diff_new) < 0.5:
                            self._is_converged = True
                            norm = p_new / 127.0
                            self._synth_val_float = v_min + norm * span
                        else:
                            self._synth_val_float = max(v_min, min(v_max, v_cand))

                self._physical_pos = p_new

        elif self.mode == ScaleMode.CATCH_UP:
            p_new = max(0, min(127, physical_input))
            span = max(1e-6, self.max_value - self.min_value)
            v_norm = (self._synth_val_float - self.min_value) / span * 127.0

            if self._is_converged:
                norm = p_new / 127.0
                self._synth_val_float = self.min_value + norm * span
            else:
                p_last = self._physical_pos
                # Did we cross v_norm?
                diff_last = p_last - v_norm
                diff_new = p_new - v_norm
                if (diff_last * diff_new <= 0) or abs(diff_new) < 1.0:
                    self._is_converged = True
                    norm = p_new / 127.0
                    self._synth_val_float = self.min_value + norm * span

            self._physical_pos = p_new

        elif self.mode == ScaleMode.RELATIVE_DELTA:
            p_new = max(0, min(127, physical_input))
            dp = p_new - self._physical_pos
            if dp != 0:
                self._synth_val_float = max(
                    self.min_value,
                    min(self.max_value, self._synth_val_float + (dp * self.sensitivity)),
                )
                self._physical_pos = p_new

        elif self.mode == ScaleMode.RELATIVE_CENTER_RESET:
            # Controller knob centered at 64
            val = max(0, min(127, physical_input))
            delta = val - 64
            if delta != 0:
                self._synth_val_float = max(
                    self.min_value,
                    min(self.max_value, self._synth_val_float + (delta * self.sensitivity)),
                )
                needs_recenter = True
            self._physical_pos = 64

        elif self.mode == ScaleMode.RELATIVE_ENCODER:
            # Decode relative CC value
            raw = max(0, min(127, physical_input))
            if self.encoding == RelativeEncoderEncoding.BINARY_OFFSET:
                delta = raw - 64
            elif self.encoding == RelativeEncoderEncoding.TWOS_COMPLEMENT:
                delta = raw if raw < 64 else raw - 128
            elif self.encoding == RelativeEncoderEncoding.SIGN_MAGNITUDE:
                delta = raw if raw < 64 else -(raw - 64)
            else:
                delta = raw - 64

            if delta != 0:
                self._synth_val_float = max(
                    self.min_value,
                    min(self.max_value, self._synth_val_float + (delta * self.sensitivity)),
                )
            self._physical_pos = raw

        new_int = int(round(self._synth_val_float))
        changed = (new_int != prev_int)
        self._last_emitted_int = new_int

        return (new_int, changed, needs_recenter)
