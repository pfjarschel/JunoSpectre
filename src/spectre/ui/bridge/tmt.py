"""Tone Mix Table: structure types, booster and the tones' key/velocity ranges.

The TMT belongs to the patch voice, so all four engines (PCM, Vector,
Wavetable, VA) share it; each engine page opens the same overlay.

Structure types 2..10 merge tone 1 into tone 2 (tone 3 into tone 4). The
first tone's TVA then sets how much of it enters the mix / booster / ring
modulator, and the second tone's TVA is the pair's output.

Edits go straight to the live patch; saves read the image back from the
synth, so files pick them up like any other edit.
"""

from __future__ import annotations

import logging

from PyQt6.QtCore import pyqtProperty, pyqtSignal, pyqtSlot

from ...core.sysex import (
    TMT_PARAM_BOOSTER_12,
    TMT_PARAM_BOOSTER_34,
    TMT_PARAM_STRUCTURE_12,
    TMT_PARAM_STRUCTURE_34,
    TMT_PARAM_VELOCITY_CONTROL,
    TMT_TONE_RANGE_FIELDS,
)
from .base import BridgeBaseMixin

logger = logging.getLogger(__name__)

TMT_TONE_OFFSETS = (0x05, 0x0E, 0x17, 0x20)  # each tone's switch byte

# Diagram nodes: [label, column, lane, owner] (lane 0 = first tone, 1 = second,
# 0.5 = merged; owner 1/2 = which tone the block belongs to, 0 = shared).
# Edges index the nodes; "out" lists the nodes that leave the pair.
# Drawn from Parameter Guide p.6-7.
_W1, _W2 = ["WG", 0, 0, 1], ["WG", 0, 1, 2]
STRUCTURE_TYPES = [
    {"name": "INDEPENDENT", "role": "VOLUME", "booster": False,
     "text": "The two tones play side by side, each through its own filter and amp.",
     "nodes": [_W1, ["TVF", 2, 0, 1], ["TVA", 4, 0, 1], _W2, ["TVF", 2, 1, 2], ["TVA", 4, 1, 2]],
     "edges": [[0, 1], [1, 2], [3, 4], [4, 5]], "out": [2, 5]},
    {"name": "STACKED FILTERS", "role": "BALANCE", "booster": False,
     "text": "Both waves are mixed, then run through both filters in a row for a steeper, stronger filter.",
     "nodes": [_W1, ["TVA", 1, 0, 1], _W2, ["+", 2, 0.5, 0], ["TVF", 3, 0.5, 1],
               ["TVF", 4, 0.5, 2], ["TVA", 5, 0.5, 2]],
     "edges": [[0, 1], [1, 3], [2, 3], [3, 4], [4, 5], [5, 6]], "out": [6]},
    {"name": "FILTER + BOOST", "role": "BALANCE", "booster": True,
     "text": "Both waves are mixed, filtered, distorted by the booster, then filtered again.",
     "nodes": [_W1, ["TVA", 1, 0, 1], _W2, ["+", 2, 0.5, 0], ["TVF", 3, 0.5, 1],
               ["BOOST", 4, 0.5, 0], ["TVF", 5, 0.5, 2], ["TVA", 6, 0.5, 2]],
     "edges": [[0, 1], [1, 3], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7]], "out": [7]},
    {"name": "BOOST + FILTERS", "role": "DRIVE", "booster": True,
     "text": "Both waves drive the booster together, then go through both filters.",
     "nodes": [_W1, ["TVA", 1, 0, 1], _W2, ["BOOST", 2, 0.5, 0], ["TVF", 3, 0.5, 1],
               ["TVF", 4, 0.5, 2], ["TVA", 5, 0.5, 2]],
     "edges": [[0, 1], [1, 3], [2, 3], [3, 4], [4, 5], [5, 6]], "out": [6]},
    {"name": "RING MOD", "role": "RING DEPTH", "booster": False,
     "text": "The waves are ring-modulated (multiplied) for metallic overtones, then go through both filters.",
     "nodes": [_W1, ["TVA", 1, 0, 1], _W2, ["RING", 2, 0.5, 0], ["TVF", 3, 0.5, 1],
               ["TVF", 4, 0.5, 2], ["TVA", 5, 0.5, 2]],
     "edges": [[0, 1], [1, 3], [2, 3], [3, 4], [4, 5], [5, 6]], "out": [6]},
    {"name": "RING + DRY", "role": "RING AMOUNT", "booster": False,
     "text": "Like RING MOD, with the clean second wave mixed back in before the filters.",
     "nodes": [_W1, ["TVA", 1, 0, 1], _W2, ["RING", 2, 0.5, 0], ["+", 3, 0.5, 0],
               ["TVF", 4, 0.5, 1], ["TVF", 5, 0.5, 2], ["TVA", 6, 0.5, 2]],
     "edges": [[0, 1], [1, 3], [2, 3], [3, 4], [2, 4], [4, 5], [5, 6], [6, 7]], "out": [7]},
    {"name": "FILTERED RING", "role": "RING DEPTH", "booster": False,
     "text": "The first tone is filtered, then ring-modulates the raw second wave; the result goes through the second filter.",
     "nodes": [_W1, ["TVF", 1, 0, 1], ["TVA", 2, 0, 1], _W2, ["RING", 3, 0.5, 0],
               ["TVF", 4, 0.5, 2], ["TVA", 5, 0.5, 2]],
     "edges": [[0, 1], [1, 2], [2, 4], [3, 4], [4, 5], [5, 6]], "out": [6]},
    {"name": "FILTERED RING + DRY", "role": "RING AMOUNT", "booster": False,
     "text": "Like FILTERED RING, with the clean second wave mixed back in before the second filter.",
     "nodes": [_W1, ["TVF", 1, 0, 1], ["TVA", 2, 0, 1], _W2, ["RING", 3, 0.5, 0],
               ["+", 4, 0.5, 0], ["TVF", 5, 0.5, 2], ["TVA", 6, 0.5, 2]],
     "edges": [[0, 1], [1, 2], [2, 4], [3, 4], [4, 5], [3, 5], [5, 6], [6, 7]], "out": [7]},
    {"name": "DUAL-FILTER RING", "role": "RING DEPTH", "booster": False,
     "text": "Each tone is filtered on its own, then the two are ring-modulated.",
     "nodes": [_W1, ["TVF", 1, 0, 1], ["TVA", 2, 0, 1], _W2, ["TVF", 1, 1, 2],
               ["RING", 3, 0.5, 0], ["TVA", 4, 0.5, 2]],
     "edges": [[0, 1], [1, 2], [2, 5], [3, 4], [4, 5], [5, 6]], "out": [6]},
    {"name": "DUAL-FILTER RING + DRY", "role": "RING AMOUNT", "booster": False,
     "text": "Like DUAL-FILTER RING, with the filtered second tone mixed back in.",
     "nodes": [_W1, ["TVF", 1, 0, 1], ["TVA", 2, 0, 1], _W2, ["TVF", 1, 1, 2],
               ["RING", 3, 0.5, 0], ["+", 4, 0.5, 0], ["TVA", 5, 0.5, 2]],
     "edges": [[0, 1], [1, 2], [2, 5], [3, 4], [4, 5], [5, 6], [4, 6], [6, 7]], "out": [7]},
]

BOOSTER_LABELS = ["0 dB", "+6 dB", "+12 dB", "+18 dB"]
VELOCITY_CONTROL_LABELS = ["OFF", "ON", "RANDOM", "CYCLE"]

# QML field name -> (ToneState attribute, minimum)
_RANGE_FIELDS = {
    "keyLower": ("key_range_lower", 0), "keyUpper": ("key_range_upper", 0),
    "keyFadeLower": ("key_fade_lower", 0), "keyFadeUpper": ("key_fade_upper", 0),
    "veloLower": ("velo_range_lower", 1), "veloUpper": ("velo_range_upper", 1),
    "veloFadeLower": ("velo_fade_lower", 0), "veloFadeUpper": ("velo_fade_upper", 0),
}
# A range's partner edge: the Juno drags the other edge along rather than cross
_PARTNER = {"key_range_lower": "key_range_upper", "key_range_upper": "key_range_lower",
            "velo_range_lower": "velo_range_upper", "velo_range_upper": "velo_range_lower"}


class TmtBridgeMixin(BridgeBaseMixin):
    tmtChanged = pyqtSignal()
    requestOpenTmtOverlay = pyqtSignal(str)

    def _init_tmt(self) -> None:
        self._tmt_cache = None

    def _tmt_emit(self) -> None:
        self._tmt_cache = None
        self.tmtChanged.emit()

    def _tmt_write(self, offset: int, value: int) -> None:
        juno = self.juno
        if juno is None:
            return
        try:
            juno.set_tmt_param(offset, value)
        except Exception as e:
            logger.error(f"TMT write 0x{offset:02X} failed: {e}")

    # -- state -----------------------------------------------------------------

    @pyqtProperty("QVariantMap", notify=tmtChanged)
    def tmt(self) -> dict:
        # Built once per change (Qt 6.8 re-reads Python containers per access)
        if self._tmt_cache is None:
            c = self.patch_state.common
            self._tmt_cache = {
                "structure12": int(c.structure_12), "structure34": int(c.structure_34),
                "booster12": int(c.booster_12), "booster34": int(c.booster_34),
                "veloControl": int(c.tmt_velocity_control),
                "ctrlSwitch": bool(c.tmt_control_switch),
                "tones": [{q: int(getattr(t, attr)) for q, (attr, _lo) in _RANGE_FIELDS.items()}
                          for t in self.patch_state.tones],
            }
        return self._tmt_cache

    @pyqtProperty("QVariantList", constant=True)
    def tmtStructureTypes(self) -> list:
        return STRUCTURE_TYPES

    @pyqtProperty("QVariantList", constant=True)
    def tmtBoosterLabels(self) -> list:
        return BOOSTER_LABELS

    @pyqtProperty("QVariantList", constant=True)
    def tmtVelocityControlLabels(self) -> list:
        return VELOCITY_CONTROL_LABELS

    @pyqtSlot(str)
    def openTmtOverlay(self, tab: str = "STRUCTURE") -> None:
        self.requestOpenTmtOverlay.emit((tab or "STRUCTURE").upper())

    # -- pair settings -----------------------------------------------------------

    @pyqtSlot(int, int)
    def setTmtStructure(self, pair: int, type_index: int) -> None:
        """pair 1 = tones 1&2, 2 = tones 3&4; type_index 0..9 = TYPE 1..10."""
        v = max(0, min(9, int(type_index)))
        attr, off = ("structure_12", TMT_PARAM_STRUCTURE_12) if pair == 1 else \
            ("structure_34", TMT_PARAM_STRUCTURE_34)
        if getattr(self.patch_state.common, attr) == v:
            return
        setattr(self.patch_state.common, attr, v)
        self._tmt_write(off, v)
        self._tmt_emit()
        self.routingChanged.emit()  # types 2..10 move tone 1/3 onto tone 2/4's output

    @pyqtSlot(int, int)
    def setTmtBooster(self, pair: int, value: int) -> None:
        v = max(0, min(3, int(value)))
        attr, off = ("booster_12", TMT_PARAM_BOOSTER_12) if pair == 1 else \
            ("booster_34", TMT_PARAM_BOOSTER_34)
        if getattr(self.patch_state.common, attr) == v:
            return
        setattr(self.patch_state.common, attr, v)
        self._tmt_write(off, v)
        self._tmt_emit()

    @pyqtSlot(int)
    def setTmtVelocityControl(self, value: int) -> None:
        v = max(0, min(3, int(value)))
        if self.patch_state.common.tmt_velocity_control == v:
            return
        self.patch_state.common.tmt_velocity_control = v
        self._tmt_write(TMT_PARAM_VELOCITY_CONTROL, v)
        self._tmt_emit()

    @pyqtSlot(bool)
    def setTmtControlSwitch(self, enabled: bool) -> None:
        v = 1 if enabled else 0
        if self.patch_state.common.tmt_control_switch == v:
            return
        self.patch_state.common.tmt_control_switch = v
        juno = self.juno
        if juno is not None:
            try:
                juno.set_tmt_control_switch(bool(v))
            except Exception as e:
                logger.error(f"TMT control switch write failed: {e}")
        self._tmt_emit()

    # -- tone ranges -------------------------------------------------------------

    def _tone_range_set(self, tone, attr: str, value: int) -> bool:
        """Set one range byte; returns True when it changed (writes it)."""
        if getattr(tone, attr) == value:
            return False
        setattr(tone, attr, value)
        off = TMT_TONE_OFFSETS[tone.tone_index - 1] + 1 + TMT_TONE_RANGE_FIELDS.index(attr)
        self._tmt_write(off, value)
        return True

    @pyqtSlot(int, str, int)
    def setToneRange(self, tone_number: int, field: str, value: int) -> None:
        """One range field (keyLower, keyUpper, keyFadeLower, ..., veloFadeUpper).

        Like the Juno, pushing a lower edge past the upper one drags it along.
        """
        spec = _RANGE_FIELDS.get(field)
        if spec is None or not 1 <= int(tone_number) <= 4:
            return
        attr, lo = spec
        v = max(lo, min(127, int(value)))
        tone = self.patch_state.tones[int(tone_number) - 1]
        changed = self._tone_range_set(tone, attr, v)
        partner = _PARTNER.get(attr)
        if partner:
            p = getattr(tone, partner)
            if (attr.endswith("lower") and p < v) or (attr.endswith("upper") and p > v):
                changed = self._tone_range_set(tone, partner, v) or changed
        if changed:
            self._tmt_emit()

    @pyqtSlot(int, str, int, int)
    def setToneRangeSpan(self, tone_number: int, kind: str, lower: int, upper: int) -> None:
        """Move a whole key ("key") or velocity ("velo") range at once."""
        if kind not in ("key", "velo") or not 1 <= int(tone_number) <= 4:
            return
        floor = 0 if kind == "key" else 1
        lo = max(floor, min(127, int(lower)))
        hi = max(lo, min(127, int(upper)))
        tone = self.patch_state.tones[int(tone_number) - 1]
        changed = self._tone_range_set(tone, f"{kind}_range_lower", lo)
        changed = self._tone_range_set(tone, f"{kind}_range_upper", hi) or changed
        if changed:
            self._tmt_emit()

    @pyqtSlot(int, str)
    def resetToneRange(self, tone_number: int, kind: str) -> None:
        """Full range, no fades, for "key" or "velo" (tone 0 = all four)."""
        if kind not in ("key", "velo"):
            return
        tones = self.patch_state.tones if int(tone_number) == 0 else \
            [self.patch_state.tones[max(1, min(4, int(tone_number))) - 1]]
        floor = 0 if kind == "key" else 1
        changed = False
        for tone in tones:
            for attr, v in ((f"{kind}_range_lower", floor), (f"{kind}_range_upper", 127),
                            (f"{kind}_fade_lower", 0), (f"{kind}_fade_upper", 0)):
                changed = self._tone_range_set(tone, attr, v) or changed
        if changed:
            self._tmt_emit()
