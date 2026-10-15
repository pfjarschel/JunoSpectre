"""Novation Launch Control XL3 surface: screen text and LED messages.

Used when a controller preset declares "surface": "lcxl3" and runs the
device in DAW Control mode (verified on hardware, see the programmer's
reference guide in Resources/):
  - every message goes to the DAW port;
  - display targets and LED indices are the controls' CC numbers
    (faders 5..12, knobs 13..36, buttons 37..52, transport 116/118);
  - in DAW Control mode a configured knob/fader display pops up by itself
    on touch/turn, and its value field can be rewritten live.

Pure helpers only: building messages and formatting values.
"""

from __future__ import annotations

import re

import mido

HEADER = [0x00, 0x20, 0x29, 0x02, 0x15]
STATIONARY = 0x35
# Display config: auto popup on change + on touch, arrangement 2 (title, name, value)
_POPUP_3_LINES = 0x40 | 0x20 | 0x02
_STATIONARY_3_LINES = 0x02
# Field 0 (title) uses the small font: 16 characters; fields 1-2 are larger: 14
TEXT_MAX = (16, 14, 14)
_ASCII = {"·": "-", "–": "-", "—": "-", "…": "...", "±": "+-", "◀": "<", "▶": ">"}

FADERS = range(5, 13)
KNOBS = range(13, 37)
BUTTONS = range(37, 53)

# Target category -> knob LED colour (RGB, 0..127 per channel)
CATEGORY_COLORS = {
    "MACRO": (0, 40, 127),
    "FILTER": (127, 40, 0),
    "AMP": (0, 127, 20),
    "PITCH": (127, 0, 90),
    "LFO": (100, 0, 127),
    "FX": (0, 110, 127),
    "COMMON": (127, 110, 0),
    "MORPH": (127, 127, 127),
    "PART": (127, 60, 60),
    "ACTION": (60, 60, 60),
}
OFF = (0, 0, 0)
# Catalog COMMON targets that read as filter / amp controls on the panel
_LED_CATEGORY = {
    "common.cutoff_offset": "FILTER", "common.resonance_offset": "FILTER",
    "common.attack_offset": "AMP", "common.release_offset": "AMP",
}


def led_category(target: str, catalog_category: str) -> str:
    if target.startswith("macro."):
        return "MACRO"
    return _LED_CATEGORY.get(target, catalog_category or "ACTION")


def sysex(*data: int) -> mido.Message:
    return mido.Message("sysex", data=HEADER + [int(d) & 0x7F for d in data])


def ascii_bytes(text: str, limit: int = 16) -> list[int]:
    """The screen's character set is plain ASCII (20h..7Eh)."""
    plain = "".join(_ASCII.get(c, c) for c in str(text))
    return [ord(c) if 0x20 <= ord(c) <= 0x7E else 0x3F for c in plain[:limit]]


def display_config(target: int, stationary: bool = False) -> mido.Message:
    return sysex(0x04, target, _STATIONARY_3_LINES if stationary else _POPUP_3_LINES)


def display_text(target: int, field: int, text: str) -> mido.Message:
    return sysex(0x06, target, field, *ascii_bytes(text, TEXT_MAX[min(field, 2)]))


def display_show(target: int) -> mido.Message:
    return sysex(0x04, target, 0x7F)


def led_rgb(index: int, rgb: tuple[int, int, int]) -> mido.Message:
    r, g, b = (max(0, min(127, int(v))) for v in rgb)
    return sysex(0x01, 0x53, index, r, g, b)


def dim(rgb: tuple[int, int, int], factor: float = 0.12) -> tuple[int, int, int]:
    return tuple(int(v * factor) for v in rgb)


def by_value(rgb: tuple[int, int, int], t: float | None) -> tuple[int, int, int]:
    """Knob LED: its colour, brighter with the value (16 steps, never fully dark)."""
    if t is None:
        return rgb
    step = round(max(0.0, min(1.0, t)) * 15) / 15
    return dim(rgb, 0.08 + 0.92 * step)


_SHORT = (("Filter Cutoff", "Cutoff"), ("Filter Reso", "Reso"), ("Filter Env Depth", "Flt Env Dep"),
          ("Filter ", "Flt "), (" Offset", " Ofs"), ("Resonance", "Reso"), (" Depth", " Dep"),
          ("Release Ofs", "Rel Ofs"), ("Wavetable", "Wtbl"), ("Portamento", "Porta"),
          ("Chorus", "Cho"), ("Reverb", "Rev"), ("Pitch Env", "PEnv"), ("Attractor", "Attr"))


def short_title(title: str) -> str:
    """Catalog titles shortened for the 14-character screen lines."""
    if len(title) <= TEXT_MAX[1]:
        return title
    for a, b in _SHORT:
        title = title.replace(a, b)
    return title


def screen_names(target: str, title: str, category: str) -> tuple[str, str]:
    """(small title line, large name line) for a control's popup.

    The title line says what the parameter belongs to (tone, part, macro),
    so the name line only needs the parameter itself.
    """
    base, _, part = target.partition("@")
    if target.startswith("macro."):
        n = target[6:]
        return f"MACRO {n}", title or f"MACRO {n}"
    if base.startswith("tone.all."):
        return "ALL TONES", short_title(title.removeprefix("All "))
    m = re.match(r"tone\.(\d)\.", base)
    if m:
        return f"TONE {m.group(1)}", short_title(title.removeprefix(f"T{m.group(1)} "))
    m = re.match(r"common\.matrix(\d)_sens(\d)", base)
    if m:
        return f"MATRIX CTRL {m.group(1)}", f"Dest {m.group(2)} Sens"
    if base.startswith("seq.swing."):
        return f"TRACK {base[10:]}", "Swing"
    if base.startswith("part."):
        if part:
            return f"PART {part}", short_title(title.replace(f"Part {part} ", "", 1))
        return "EDITED PART", short_title(title.replace("Part ", "", 1))
    return category or "SPECTRE", short_title(title)


def format_value(target: str, value: float, lo: float, hi: float) -> str:
    """Panel-style text for a target value."""
    if target.startswith("macro."):
        return f"{value * 100:+.0f}%"
    if target.startswith("vector.") and hi <= 1.0:
        return f"{value * 100:.0f}%"
    if target == "vector.bpm":
        return f"{value:.0f} BPM"
    if target == "vector.speed":
        return f"x{value:.2f}"
    base = target.split("@")[0]
    if base.startswith("seq.swing."):
        return f"{value * 100:.0f}%"
    if base.endswith("pitch_env_depth"):
        return f"{int(round(value)) - 64:+d} st"
    if base.endswith("tvf_keyfollow"):
        return f"{(int(round(value)) - 64) * 10:+d}%"
    if base.endswith("pan"):
        v = int(round(value)) - 64
        return "C" if v == 0 else (f"L{-v}" if v < 0 else f"R{v}")
    if lo == 1 and hi == 127:          # centred offsets/depths (64 = 0)
        v = int(round(value)) - 64
        return f"{v:+d}"
    if base.endswith("pitch_coarse"):
        return f"{int(round(value)) - 64:+d} st"
    if base.endswith("pitch_fine"):
        return f"{int(round(value)) - 64:+d} c"
    return str(int(round(value)))
