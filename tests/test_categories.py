"""Tests for the Roland category table (Parameter Guide p.5)."""

from src.spectre.core.categories import (
    CATEGORIES,
    CHIP_TO_CODES,
    code_from_index,
    decode_common_block,
    label_from_code,
)


def test_table_shape_and_spot_checks():
    assert len(CATEGORIES) == 39  # 0 = no-assign + 38 real
    assert CATEGORIES[0][0] == "---"
    assert CATEGORIES[1] == ("PNO", "Acoustic Piano")
    assert CATEGORIES[20] == ("SBR", "Synth Brass")
    assert CATEGORIES[29] == ("SPD", "Soft Pad")
    assert CATEGORIES[38] == ("CMB", "Combination")


def test_live_probe_vectors():
    # Verified live against the XPS-30 during catalog work.
    assert code_from_index(1) == "PNO"    # Grand Pno DS
    assert code_from_index(20) == "SBR"   # J-Pop Brass
    assert code_from_index(29) == "SPD"   # JP-8 Phase
    assert code_from_index(0) == "---"
    assert code_from_index(999) == ""
    assert code_from_index(-1) == ""


def test_decode_common_block():
    block = bytes([ord("A")] * 12 + [20] + [0] * 67)
    assert decode_common_block(block) == ("AAAAAAAAAAAA", "SBR")
    assert label_from_code("PNO") == "Acoustic Piano"


def test_chip_mapping_covers_all_ui_chips():
    # Must stay in sync with LibrarianView.qml `categories` + `chipCodes`.
    expected_chips = ["ALL", "ACOUSTIC PIANO", "E.PIANO", "SYNTH LEAD",
                      "SYNTH PAD", "BASS", "STRINGS", "USER CUSTOM"]
    assert sorted(CHIP_TO_CODES.keys()) == sorted(expected_chips)
    assert CHIP_TO_CODES["SYNTH LEAD"] == ["HLD", "SLD"]
    assert CHIP_TO_CODES["BASS"] == ["BS", "SBS"]
    assert CHIP_TO_CODES["ALL"] == []
    codes = {c for i, (c, _) in enumerate(CATEGORIES)}
    for chip, lst in CHIP_TO_CODES.items():
        for code in lst:
            assert code in codes, f"{chip} -> unknown code {code}"


def test_qml_full_grid_matches_category_table():
    """The Librarian 'CATS' grid must list every Roland code exactly once."""
    import re
    from pathlib import Path

    qml = Path(__file__).resolve().parent.parent / "src" / "spectre" / "ui" / "qml" \
        / "components" / "LibrarianView.qml"
    text = qml.read_text(encoding="utf-8")
    grids = [re.findall(r'"([A-Z]{2,3})"', m) for m in re.findall(r"model:\s*\[([^\]]+)\]", text)]
    expected = [c for c, _ in CATEGORIES if c != "---"]
    assert any(sorted(g) == sorted(expected) for g in grids), (
        "no QML model lists all 38 Roland codes; found: "
        + "; ".join(",".join(g) for g in grids))
