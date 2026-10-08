"""EQ curve presets: data validity vs the MFX catalog + apply round-trip.

The chips in EqCurvePanel.qml render from Bridge.eqParametricPresets /
spectrumPresets and write through Bridge.setMfxParam (origin-resolved).
Repeater delegate contents are not introspectable headlessly, so these
tests cover everything around that boundary: data shape, catalog bounds,
bridge exposure, and the exact write sequences applyPreset() performs.
"""

import pytest

from src.spectre.core.mfx_catalog import (
    EQ_PARAMETRIC_PRESETS,
    SPECTRUM_PRESETS,
    get_mfx_algo,
)


def _opts(algo_id, idx):
    algo = get_mfx_algo(algo_id)
    return next(p["options"] for p in algo["params"] if p["idx"] == idx)


def test_parametric_preset_shapes():
    assert len(EQ_PARAMETRIC_PRESETS) == 7
    names = [p["name"] for p in EQ_PARAMETRIC_PRESETS]
    assert len(set(names)) == len(names)
    assert names[0] == "FLAT"
    lo, mids, hi, qs = _opts(1, 0), _opts(1, 2), _opts(1, 8), _opts(1, 4)
    assert [len(lo), len(mids), len(hi), len(qs)] == [2, 17, 3, 5]
    for p in EQ_PARAMETRIC_PRESETS:
        assert len(p["g"]) == 4
        assert all(-15 <= v <= 15 for v in p["g"])
        if p["f"] is not None:
            assert len(p["f"]) == 4
            for v, opts in zip(p["f"], (lo, mids, mids, hi)):
                assert 0 <= v < len(opts), (p["name"], v)
        if p["q"] is not None:
            assert len(p["q"]) == 4
            for v in p["q"]:
                assert v == -1 or 0 <= v < len(qs), (p["name"], v)


def test_spectrum_preset_shapes():
    assert len(SPECTRUM_PRESETS) == 7
    names = [p["name"] for p in SPECTRUM_PRESETS]
    assert len(set(names)) == len(names)
    assert names[0] == "FLAT"
    for p in SPECTRUM_PRESETS:
        assert len(p["g"]) == 8
        assert all(-15 <= v <= 15 for v in p["g"])
        assert p["q"] in (-1, 0, 1, 2, 3, 4), p["name"]


def test_flat_presets_are_gain_only_zero():
    for p in EQ_PARAMETRIC_PRESETS + SPECTRUM_PRESETS:
        if p["name"] == "FLAT":
            assert all(v == 0 for v in p["g"])
            assert p.get("f") is None
            assert p.get("q") in (None, -1)


def _apply_parametric(bridge, preset):
    G, F, Q = [1, 3, 6, 9], [0, 2, 5, 8], [-1, 4, 7, -1]
    for b in range(4):
        bridge.setMfxParam(G[b], preset["g"][b])
    if preset["f"] is not None:
        for b in range(4):
            bridge.setMfxParam(F[b], preset["f"][b])
    if preset["q"] is not None:
        for b in range(4):
            if preset["q"][b] >= 0:
                bridge.setMfxParam(Q[b], preset["q"][b])


def _apply_spectrum(bridge, preset):
    for i in range(8):
        bridge.setMfxParam(i, preset["g"][i])
    if preset["q"] is not None and preset["q"] >= 0:
        bridge.setMfxParam(8, preset["q"])


def _offline_bridge():
    from src.spectre.ui.bridge import SpectreBridge
    from src.spectre.vector.engine import VectorEngine

    return SpectreBridge(VectorEngine())


def test_bridge_exposes_presets():
    bridge = _offline_bridge()
    assert [p["name"] for p in bridge.eqParametricPresets] == [
        p["name"] for p in EQ_PARAMETRIC_PRESETS]
    assert [p["name"] for p in bridge.spectrumPresets] == [
        p["name"] for p in SPECTRUM_PRESETS]


def test_every_parametric_preset_round_trips():
    bridge = _offline_bridge()
    for preset in EQ_PARAMETRIC_PRESETS:
        _apply_parametric(bridge, preset)
        for i, want in enumerate(preset["g"]):
            assert bridge.mfxParamValues[[1, 3, 6, 9][i]] == want, preset["name"]
        if preset["f"] is not None:
            for i, want in enumerate(preset["f"]):
                assert bridge.mfxParamValues[[0, 2, 5, 8][i]] == want, preset["name"]


def test_every_spectrum_preset_round_trips():
    bridge = _offline_bridge()
    for preset in SPECTRUM_PRESETS:
        _apply_spectrum(bridge, preset)
        for i, want in enumerate(preset["g"]):
            assert bridge.mfxParamValues[i] == want, preset["name"]
