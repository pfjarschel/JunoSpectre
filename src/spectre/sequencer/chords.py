"""Chord naming for sequencer steps (pitch-class matching against common shapes)."""

from __future__ import annotations

from typing import Iterable, List

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Interval sets above the root, in priority order: earlier shapes win ties
# (e.g. {C, E, G, A} reads as C6 over Am7/C when C is the bass).
CHORD_SHAPES = [
    ("", (0, 4, 7)),
    ("m", (0, 3, 7)),
    ("7", (0, 4, 7, 10)),
    ("maj7", (0, 4, 7, 11)),
    ("m7", (0, 3, 7, 10)),
    ("5", (0, 7)),
    ("sus4", (0, 5, 7)),
    ("sus2", (0, 2, 7)),
    ("dim", (0, 3, 6)),
    ("aug", (0, 4, 8)),
    ("6", (0, 4, 7, 9)),
    ("m6", (0, 3, 7, 9)),
    ("m7b5", (0, 3, 6, 10)),
    ("dim7", (0, 3, 6, 9)),
    ("mMaj7", (0, 3, 7, 11)),
    ("7sus4", (0, 5, 7, 10)),
    ("add9", (0, 2, 4, 7)),
    ("madd9", (0, 2, 3, 7)),
    ("9", (0, 2, 4, 7, 10)),
    ("maj9", (0, 2, 4, 7, 11)),
    ("m9", (0, 2, 3, 7, 10)),
    # Sevenths with the fifth left out, as often voiced
    ("7", (0, 4, 10)),
    ("maj7", (0, 4, 11)),
    ("m7", (0, 3, 10)),
]
_SHAPES = [(suffix, frozenset(ivs)) for suffix, ivs in CHORD_SHAPES]


def chord_name(pitches: Iterable[int]) -> str:
    """Name the chord formed by MIDI pitches, or "" if it isn't a recognised shape.

    Octave doublings don't matter. The lowest note is preferred as the root;
    otherwise the chord is named as an inversion over its bass ("C/E").
    """
    ps = sorted(int(p) for p in pitches)
    classes = set(p % 12 for p in ps)
    if len(classes) < 2:
        return ""
    bass = ps[0] % 12
    # Bass first, then the remaining pitch classes from low to high
    roots: List[int] = [bass] + [c for c in dict.fromkeys(p % 12 for p in ps) if c != bass]
    for root in roots:
        ivs = frozenset((c - root) % 12 for c in classes)
        for suffix, shape in _SHAPES:
            if ivs == shape:
                name = NOTE_NAMES[root] + suffix
                return name if root == bass else f"{name}/{NOTE_NAMES[bass]}"
    return ""
