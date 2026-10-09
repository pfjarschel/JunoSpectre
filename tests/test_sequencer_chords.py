"""Tests for chord naming of sequencer steps."""

import pytest

from src.spectre.sequencer.chords import chord_name


@pytest.mark.parametrize("pitches, name", [
    ((60, 64, 67), "C"),
    ((57, 60, 64), "Am"),
    ((60, 64, 67, 70), "C7"),
    ((62, 65, 69, 72), "Dm7"),
    ((65, 69, 72, 76), "Fmaj7"),
    ((59, 62, 65, 69), "Bm7b5"),
    ((60, 65, 67), "Csus4"),
    ((60, 62, 67), "Csus2"),
    ((40, 47), "E5"),
    ((60, 62, 64, 67), "Cadd9"),
    ((60, 64, 70), "C7"),              # fifth left out
    ((60, 64, 67, 72, 76), "C"),       # doublings don't matter
    ((60, 64, 67, 69), "C6"),          # bass decides between C6 and Am7/C
    ((57, 60, 64, 67), "Am7"),
    ((64, 67, 72), "C/E"),             # inversions name the bass
    ((55, 60, 64), "C/G"),
    ((61, 65, 68), "C#"),
])
def test_recognised_chords(pitches, name):
    assert chord_name(pitches) == name
    assert chord_name(reversed(pitches)) == name  # order doesn't matter


@pytest.mark.parametrize("pitches", [(), (60,), (60, 72), (60, 61), (60, 62, 64, 65, 67)])
def test_unrecognised_sets_have_no_name(pitches):
    assert chord_name(pitches) == ""
