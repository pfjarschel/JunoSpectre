"""Roland patch category table (JUNO-DS / XPS-30 Parameter Guide p.5).

Each patch stores its category as one byte at Patch Common offset 0x0C:
index into this ordered list (0 = no-assign). Drums and performances carry
no category byte: drums are implicitly DRM, performances have none.
"""

from __future__ import annotations

# (3-letter code, display label), index = raw byte value.
CATEGORIES: list[tuple[str, str]] = [
    ("---", "No assign"),      # 0
    ("PNO", "Acoustic Piano"),  # 1
    ("EP", "Electric Piano"),  # 2
    ("KEY", "Keyboards"),      # 3
    ("BEL", "Bell"),           # 4
    ("MLT", "Mallet"),         # 5
    ("ORG", "Organ"),          # 6
    ("ACD", "Accordion"),      # 7
    ("HRM", "Harmonica"),      # 8
    ("AGT", "Acoustic Guitar"),  # 9
    ("EGT", "Electric Guitar"),  # 10
    ("DGT", "Distortion Guitar"),  # 11
    ("BS", "Bass"),            # 12
    ("SBS", "Synth Bass"),     # 13
    ("STR", "Strings"),        # 14
    ("ORC", "Orchestra"),      # 15
    ("HIT", "Hit & Stab"),     # 16
    ("WND", "Wind"),           # 17
    ("FLT", "Flute"),          # 18
    ("BRS", "Acoustic Brass"),  # 19
    ("SBR", "Synth Brass"),    # 20
    ("SAX", "Sax"),            # 21
    ("HLD", "Hard Lead"),      # 22
    ("SLD", "Soft Lead"),      # 23
    ("TEK", "Techno Synth"),   # 24
    ("PLS", "Pulsating Synth"),  # 25
    ("FX", "Synth FX"),        # 26
    ("SYN", "Poly Synth"),     # 27
    ("BPD", "Bright Pad"),     # 28
    ("SPD", "Soft Pad"),       # 29
    ("VOX", "Vox / Choir"),    # 30
    ("PLK", "Plucked"),        # 31
    ("ETH", "Ethnic"),         # 32
    ("FRT", "Fretted"),        # 33
    ("PRC", "Percussion"),     # 34
    ("SFX", "Sound FX"),       # 35
    ("BTS", "Beat & Groove"),  # 36
    ("DRM", "Drums"),          # 37
    ("CMB", "Combination"),    # 38
]

CODE_TO_INDEX = {code: i for i, (code, _) in enumerate(CATEGORIES)}
CODE_TO_LABEL = {code: label for code, label in CATEGORIES}

# Librarian touch chips (8 fit the 1024px bar) -> Roland codes.
# "USER CUSTOM" is source-based (user files), not a category: handled in QML
# by filtering source='file' instead.
CHIP_TO_CODES: dict[str, list[str]] = {
    "ALL": [],
    "ACOUSTIC PIANO": ["PNO"],
    "E.PIANO": ["EP"],
    "SYNTH LEAD": ["HLD", "SLD"],
    "SYNTH PAD": ["BPD", "SPD"],
    "BASS": ["BS", "SBS"],
    "STRINGS": ["STR", "ORC"],
    "USER CUSTOM": [],
}


def code_from_index(i: int) -> str:
    """Map a raw category byte to its 3-letter code (unknown -> '')."""
    try:
        i = int(i)
        if i < 0:
            return ""
        return CATEGORIES[i][0]
    except (IndexError, ValueError, TypeError):
        return ""


def label_from_code(code: str) -> str:
    return CODE_TO_LABEL.get(code, code)


def decode_common_block(block: bytes | bytearray | list[int]) -> tuple[str, str]:
    """Extract (name, category_code) from an 80-byte Patch Common block."""
    try:
        name = bytes(block[0:12]).decode("latin1", errors="replace").strip()
    except (IndexError, ValueError, TypeError):
        name = ""
    try:
        cat = code_from_index(block[0x0C])
    except (IndexError, TypeError):
        cat = ""
    return name, cat
