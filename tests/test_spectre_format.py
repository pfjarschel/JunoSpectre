"""Tests for versioned .spectre envelope (format v1)."""

import json

import pytest

from src.spectre.core.patch_state import PatchState
from src.spectre.core.spectre_format import (
    FORMAT_VERSION,
    load_spectre,
    patch_state_from_dict,
    patch_state_to_dict,
    save_spectre,
)


def test_hw_roundtrip_preserves_params_and_raw_regions(tmp_path):
    ps = PatchState.create_init_patch()
    ps.common.name = "ROUNDTRIP"
    ps.tones[0].tvf_cutoff = 100
    ps.tones[2].muted = True
    ps.effects.mfx_type = 15
    ps.raw_regions = {"common": [bytes([1, 2, 3])], "tone_1": [bytes([4]), bytes([5, 6])]}
    ps.macros[0].value = 0.5

    out = save_spectre(
        tmp_path / "r.spectre", ps,
        meta={"name": "ROUNDTRIP", "category": "SYNTH LEAD", "tags": ["fat"], "favorite": True, "rating": 4},
        spectre={"engine_mode": "vector", "vector": {"x": 0.25, "y": 0.75}},
        synth_ref={"source": "factory", "msb": 87, "lsb": 64, "pc": 5},
    )
    loaded = load_spectre(out)
    assert loaded["format_version"] == FORMAT_VERSION
    assert loaded["kind"] == "patch"
    assert loaded["meta"]["name"] == "ROUNDTRIP"
    assert loaded["meta"]["category"] == "SYNTH LEAD"
    assert loaded["meta"]["tags"] == ["fat"]
    assert loaded["meta"]["favorite"] is True
    assert loaded["spectre"]["vector"] == {"x": 0.25, "y": 0.75}
    assert loaded["synth_ref"] == {"source": "factory", "msb": 87, "lsb": 64, "pc": 5}
    rt = loaded["patch_state"]
    assert rt.common.name == "ROUNDTRIP"
    assert rt.tones[0].tvf_cutoff == 100
    assert rt.tones[2].muted is True
    assert rt.effects.mfx_type == 15
    assert rt.raw_regions == {"common": [b"\x01\x02\x03"], "tone_1": [b"\x04", b"\x05\x06"]}
    assert rt.macros[0].value == pytest.approx(0.5)


def test_unknown_fields_preserved_forward_compat(tmp_path):
    ps = PatchState.create_init_patch()
    p = tmp_path / "f.spectre"
    save_spectre(p, ps, spectre={"engine_mode": "va"})
    raw = json.loads(p.read_text())
    raw["future_top"] = {"hello": 1}
    raw["spectre"]["future_engine"] = [1, 2, 3]
    raw["hw_patch"]["future_hw"] = 999
    p.write_text(json.dumps(raw))
    loaded = load_spectre(p)
    assert loaded["extra"] == {"future_top": {"hello": 1}}
    assert loaded["spectre"]["future_engine"] == [1, 2, 3]
    # unknown hw keys must not crash decode
    assert loaded["patch_state"].common.name == ps.common.name
    # re-save keeps the unknown top-level key
    save_spectre(p, loaded["patch_state"], meta=loaded["meta"],
                 spectre=loaded["spectre"], extra=loaded["extra"])
    raw2 = json.loads(p.read_text())
    assert raw2["future_top"] == {"hello": 1}


def test_bad_version_and_kind_rejected(tmp_path):
    ps = PatchState.create_init_patch()
    p = tmp_path / "b.spectre"
    save_spectre(p, ps)
    raw = json.loads(p.read_text())
    raw["format_version"] = 999
    p.write_text(json.dumps(raw))
    with pytest.raises(ValueError):
        load_spectre(p)
    raw["format_version"] = FORMAT_VERSION
    raw["kind"] = "starship"
    p.write_text(json.dumps(raw))
    with pytest.raises(ValueError):
        load_spectre(p)


def test_tolerant_decode_survives_missing_keys():
    ps = patch_state_from_dict({"common": {"name": "HALF"}, "tones": [{"level": 10}]})
    assert ps.common.name == "HALF"
    assert ps.tones[0].level == 10
    assert len(ps.tones) == 4
    assert patch_state_to_dict(ps)["common"]["name"] == "HALF"
