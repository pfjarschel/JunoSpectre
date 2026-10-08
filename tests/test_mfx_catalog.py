"""Schema and integrity tests for MFX catalog JSON asset."""

from src.spectre.core.mfx_catalog import (
    EQ_PARAMETRIC_PRESETS,
    SPECTRUM_PRESETS,
    get_mfx_algo,
    get_mfx_catalog,
    get_mfx_categories,
    get_mfx_light_catalog,
)


def test_mfx_categories_defined():
    cats = get_mfx_categories()
    assert len(cats) >= 10
    assert cats[0] == "ALL"
    assert "FILTER/EQ" in cats
    assert "DRIVE" in cats
    assert "DELAY" in cats
    assert "REVERB" in cats


def test_mfx_algorithms_count_and_ids():
    catalog = get_mfx_catalog()
    assert len(catalog) == 80
    ids = [a["id"] for a in catalog]
    assert ids == list(range(1, 81))


def test_mfx_algorithm_schema_and_param_ranges():
    cats = set(get_mfx_categories())
    for algo in get_mfx_catalog():
        assert isinstance(algo["id"], int)
        assert isinstance(algo["name"], str) and len(algo["name"]) > 0
        assert algo["cat"] in cats

        params = algo.get("params", [])
        assert isinstance(params, list)
        assert 1 <= len(params) <= 32

        seen_indices = set()
        for p in params:
            assert isinstance(p["idx"], int)
            assert 0 <= p["idx"] < 32
            assert p["idx"] not in seen_indices
            seen_indices.add(p["idx"])

            assert isinstance(p["label"], str) and len(p["label"]) > 0
            assert isinstance(p["min"], int)
            assert isinstance(p["max"], int)
            assert p["min"] <= p["max"]
            assert isinstance(p["val"], int)
            assert p["min"] <= p["val"] <= p["max"], (
                f"Algo {algo['id']} param {p['label']} val {p['val']} out of range [{p['min']}, {p['max']}]"
            )

            if "options" in p:
                opts = p["options"]
                assert isinstance(opts, list)
                assert len(opts) > 0
                assert p["max"] - p["min"] + 1 == len(opts)


def test_mfx_light_catalog_filtering():
    all_light = get_mfx_light_catalog("ALL")
    assert len(all_light) == 80
    assert all(set(item.keys()) == {"id", "name", "cat"} for item in all_light)

    drive_light = get_mfx_light_catalog("DRIVE")
    assert len(drive_light) > 0
    assert all(item["cat"] == "DRIVE" for item in drive_light)

    assert get_mfx_light_catalog("NONEXISTENT") == all_light


def test_get_mfx_algo_by_id():
    a1 = get_mfx_algo(1)
    assert a1 is not None
    assert "EQUALIZER" in a1["name"]

    a80 = get_mfx_algo(80)
    assert a80 is not None

    assert get_mfx_algo(0) is None
    assert get_mfx_algo(81) is None


def test_eq_and_spectrum_presets_present():
    assert len(EQ_PARAMETRIC_PRESETS) > 0
    assert any(p["name"] == "FLAT" for p in EQ_PARAMETRIC_PRESETS)
    assert len(SPECTRUM_PRESETS) > 0
    assert any(p["name"] == "FLAT" for p in SPECTRUM_PRESETS)
