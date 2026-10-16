"""Where an FX edit lands.

MFX Studio, Master FX, the rail cards and macros edit one of three stores,
picked by the sound mode and the FX origin:

- "patch": the sounding patch's FX (PATCH mode), patch_state.effects;
- "part":  a part's patch FX (PERFORM, origin PART n), the part FX cache;
- "perf":  the performance common FX (PERFORM, origin PERFORM): perf_fx for
  chorus/reverb, its MFX slot for MFX.

FxTarget hides the stores' field names and sends each write to the matching
synth block, so the bridge setters have one path instead of three.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

from ...core.patch_state import EffectsState

# MFX field -> (EffectsState attribute, PerfMfxSlotState attribute)
_MFX_FIELDS = {
    "type": ("mfx_type", "mfx_type"),
    "dry": ("mfx_dry_send", "dry_send"),
    "chorus": ("mfx_chorus_send", "chorus_send"),
    "reverb": ("mfx_reverb_send", "reverb_send"),
    "params": ("mfx_params", "params"),
    "last": ("mfx_last_active_type", "last_active_type"),
}

# Chorus / reverb attributes (same names on EffectsState and PerfFxState)
CHORUS_ATTRS = ("chorus_type", "chorus_level", "chorus_to_reverb", "chorus_rate",
                "chorus_depth", "chorus_predelay", "chorus_feedback")
REVERB_ATTRS = ("reverb_type", "reverb_level", "reverb_predelay", "reverb_time",
                "reverb_damp", "reverb_diffusion", "reverb_tone")


@dataclass
class FxTarget:
    kind: str                # "patch" | "part" | "perf"
    index: int = 0           # part number ("part") or MFX slot 1..3 ("perf" MFX)
    store: Any = None        # EffectsState, PerfFxState or PerfMfxSlotState; None = part not read yet

    # -- MFX fields -----------------------------------------------------
    def _mfx_attr(self, name: str) -> str:
        return _MFX_FIELDS[name][0 if isinstance(self.store, EffectsState) else 1]

    def mfx(self, name: str):
        return getattr(self.store, self._mfx_attr(name))

    def set_mfx(self, name: str, value) -> None:
        setattr(self.store, self._mfx_attr(name), value)
        if name == "type" and isinstance(self.store, EffectsState):
            self.store.mfx_bypassed = int(value) == 0

    @property
    def mfx_bypassed(self) -> bool:
        if isinstance(self.store, EffectsState):
            return bool(self.store.mfx_bypassed)
        return int(self.store.mfx_type) == 0

    @property
    def mfx_shown_type(self) -> int:
        """The algorithm MFX Studio shows: the last active one while bypassed."""
        return int(self.mfx("last") or 15) if self.mfx_bypassed else int(self.mfx("type"))

    # -- synth writes ---------------------------------------------------
    def write_mfx(self, juno, mfx_type: Optional[int] = None, dry: Optional[int] = None,
                  chorus: Optional[int] = None, reverb: Optional[int] = None) -> None:
        """Type and/or sends (only the ones given)."""
        sends = {k: v for k, v in (("dry_send", dry), ("chorus_send", chorus),
                                   ("reverb_send", reverb)) if v is not None}
        if self.kind == "patch":
            juno.set_mfx(int(self.mfx("type")) if mfx_type is None else mfx_type, **sends)
            return
        if mfx_type is not None:
            sends["mfx_type"] = mfx_type
        if self.kind == "part":
            juno.set_part_patch_mfx(self.index, **sends)
        else:
            juno.set_perf_mfx(self.index, **sends)

    def write_mfx_sends(self, juno) -> None:
        self.write_mfx(juno, dry=int(self.mfx("dry")), chorus=int(self.mfx("chorus")),
                       reverb=int(self.mfx("reverb")))

    def write_mfx_params(self, juno, values: Sequence[int], start: int = 0) -> None:
        if self.kind == "patch":
            juno.set_mfx_params_bulk(values, start)
        elif self.kind == "part":
            juno.set_part_patch_mfx_params_bulk(self.index, values, start)
        else:
            juno.set_perf_mfx_params_bulk(self.index, values, start)

    def write_chorus(self, juno) -> None:
        """Type, level and output select from the store."""
        s = self.store
        if self.kind == "patch":
            juno.set_chorus(s.chorus_type, level=s.chorus_level, output_select=s.chorus_to_reverb)
        elif self.kind == "part":
            juno.set_part_patch_chorus(self.index, chorus_type=s.chorus_type,
                                       level=s.chorus_level, output_select=s.chorus_to_reverb)
        else:
            juno.set_perf_chorus(s.chorus_type, level=s.chorus_level,
                                 output_select=s.chorus_to_reverb)

    def write_chorus_detail(self, juno, param: str, value: int) -> None:
        if self.kind == "patch":
            juno.set_chorus_param(param, value)
        elif self.kind == "part":
            juno.set_part_patch_chorus_param(self.index, param, value)
        else:
            juno.set_perf_chorus_param(param, value)

    def write_reverb(self, juno) -> None:
        """Type and level from the store."""
        s = self.store
        if self.kind == "patch":
            juno.set_reverb(s.reverb_type, level=s.reverb_level)
        elif self.kind == "part":
            juno.set_part_patch_reverb(self.index, reverb_type=s.reverb_type, level=s.reverb_level)
        else:
            juno.set_perf_reverb(s.reverb_type, level=s.reverb_level)

    def write_reverb_detail(self, juno, param: str, value: int) -> None:
        if self.kind == "patch":
            juno.set_reverb_param(param, value)
        elif self.kind == "part":
            juno.set_part_patch_reverb_param(self.index, param, value)
        else:
            juno.set_perf_reverb_param(param, value)
