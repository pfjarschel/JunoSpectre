#!/usr/bin/env python3
"""Build Roland XPS-30 / JUNO-DS Waveform Name & Category Catalogs.

Parses the official Roland Parameter Guide PDF (in Resources/) to extract
all 2,198 INTA and 184 INTB waveform names, maps each wave to an instrument
category and UI icon, and marks whether each wave is a true single-cycle synth
oscillator waveform or an acoustic/percussive multi-sample.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PDF_PATH = PROJECT_ROOT / "Resources" / "JUNO-DS_88_76_61_ParamGuide_eng01_W.pdf"
OUT_DIR = PROJECT_ROOT / "src" / "spectre" / "assets" / "waveforms"

VERIFIED_SINGLE_CYCLE_INTA_IDS = set([
    # Core Analog Oscillators (579 - 625): Saws, Squares, Pulses, Triangles, Sines, Ramps
    *range(579, 626),
    # Vintage Analog Oscillators (1304 - 1329): JP-8, JP-6, P5, Moog, TB-303, PWM
    *range(1304, 1330),
    # Additional Analog Oscillators: Triangle 1, Low Sine, TB Dist Saws, Prophet Sync, JP Hollows, TB Sqr
    835, 843, 848, 849, 850, 1211, 1221, 1222, 1223, 1224, 1956,
    # Roland JD-800 / JV / Digital Single-Cycle Waves & Formants
    561, 562, 564, 565, 566, 567, 568, 570, 571, 573, 574, 575, 576, 577, 578,
    626, 628, 629, 630, 634, 638, 639, 640, 641, 642, 643, 644, 646,
    1303, 1320, 1330, 1331, 1332, 1333, 1334, 1335,
])

ACOUSTIC_CATEGORIES = [
    ("drums", "drum", [
        "kick", "snr", "sd", "rim", "tom", "chh", "phh", "ohh", "cym", "crash",
        "ride", "clap", "snap", "cwbl", "cowbell", "tamb", "timbale", "bongo",
        "conga", "tabla", "flam", "hat", "shaker", "maracas", "guiro", "cabasa",
        "dof", "dholak", "tapan", "rek", "riq", "sak", "castanet", "open triangl",
        "triangle 2", "triangle 3", "triangle 4", "steel drums", "kalimba", "marimba",
        "gamelan", "vibraphone", "glocken", "bell", "chime", "ceng", "gong"
    ]),
    ("sfx", "sfx", [
        "hit", "applause", "river", "thunder", "stream", "bird", "dog", "phone",
        "car", "gun", "siren", "train", "copter", "laser", "scratch", "noise",
        "ptn", "loop", "lp", "creak", "slam", "laugh", "scream", "punch",
        "heartbeat", "footstep", "bubble", "gallop", "swish", "click", "beep"
    ]),
    ("organ", "organ", [
        "organ", "org", "rotary", "rtry", "positive", "accordion", "accord", "musette",
        "bandoneon", "harmonica"
    ]),
    ("guitar", "guitar", [
        "gtr", "nylon", "steel gtr", "sitar", "banjo", "harp", "santur", "koto",
        "shamisen", "berimbau", "overdrive", "dist chord", "clean gtr"
    ]),
    ("bass", "bass", [
        "bass", "bs", "fretless", "slap", "pul.e", "fatacbs", "fng.eb", "ac.bass", "e.bass"
    ]),
    ("strings", "strings", [
        "violin", "viola", "cello", "str", "orch", "pizz", "marcato", "vl sect", "vc sect"
    ]),
    ("brass", "brass", [
        "tp", "trumpet", "trombone", "horn", "sax", "flute", "piccolo", "clarinet",
        "oboe", "bassoon", "recorder", "brass", "shakuhachi", "bagpipe", "gajde", "qudi"
    ]),
    ("vocal", "vocal", [
        "vox", "ahs", "oos", "hum", "doos", "voice", "choir", "female", "male", "soprano"
    ]),
    ("synth_lead", "synth", [
        "saw", "super saw", "trance", "unison", "sh-101", "tb303", "mg bass", "mc bass",
        "tb dst", "syn bass", "atk syn", "juno", "jp-8", "d-50", "p5", "ob2", "gr-300",
        "fantasynth", "pad", "stack"
    ]),
]

PIANO_RE = re.compile(r"(\b|_|^)p\*|piano|pno|grandp|clav|harpsi|wurly|rhodes|tine|dyno|ep\.", re.IGNORECASE)


def classify_wave(name: str, bank: str = "INTA", num: int = 1) -> tuple[str, str, bool]:
    """Classify wave into (category, icon, is_single_cycle)."""
    # 1. Rigorous single-cycle synthesizer oscillator identification
    if bank == "INTA" and num in VERIFIED_SINGLE_CYCLE_INTA_IDS:
        return "synth_wave", "wave", True

    n_lower = name.lower()

    # 2. Piano detection via word boundary regex
    if PIANO_RE.search(name):
        return "piano", "piano", False

    # 3. Acoustic instrument categories
    for cat, icon, keywords in ACOUSTIC_CATEGORIES:
        if any(k in n_lower for k in keywords):
            return cat, icon, False

    return "world", "world", False


def extract_layout_text() -> str:
    """Run pdftotext -layout to get column-preserved ASCII text from the PDF."""
    txt_path = Path("/tmp/param_guide_layout.txt")
    if not txt_path.exists():
        print(f"Extracting layout text from {PDF_PATH}...")
        subprocess.run(["pdftotext", "-layout", str(PDF_PATH), str(txt_path)], check=True)
    with open(txt_path, "r", encoding="latin1") as f:
        return f.read()


def build_catalogs() -> None:
    text = extract_layout_text()
    lines = text.splitlines()

    # Find INTA and INTB line boundaries
    inta_start = 5898
    intb_start = None
    patch_start = None

    for idx in range(inta_start, len(lines)):
        if "INTB" in lines[idx] and intb_start is None:
            intb_start = idx
        elif "Patch List" in lines[idx]:
            patch_start = idx
            break

    if not intb_start or not patch_start:
        raise ValueError("Could not find section boundaries in layout text")

    # Regex matching '0001   Name'
    entry_re = re.compile(
        r"(\d{4})\s+([A-Za-z0-9\.\*\+\-\'\$\&\#\/_!:][A-Za-z0-9\.\*\+\-\'\$\&\#\/_!:\s]{1,14}?)(?=\s{2,}\d{4}|\s*$)"
    )

    def parse_section(start_idx: int, end_idx: int, bank_name: str, max_count: int) -> dict[str, dict]:
        catalog = {}
        for line in lines[start_idx:end_idx]:
            if "Waveform List" in line or bank_name in line or "No." in line or not line.strip():
                continue
            matches = entry_re.findall(line)
            for num_str, name in matches:
                num = int(num_str)
                if 1 <= num <= max_count:
                    cleaned_name = name.strip()
                    cat, icon, is_sc = classify_wave(cleaned_name, bank=bank_name, num=num)
                    catalog[str(num)] = {
                        "id": num,
                        "bank": bank_name,
                        "name": cleaned_name,
                        "category": cat,
                        "icon": icon,
                        "is_single_cycle": is_sc,
                        "freq_hz": 0.0,
                        "peak": 0.0,
                        "samples_64": None,
                    }
        return catalog

    inta = parse_section(inta_start, intb_start, "INTA", 2198)
    intb = parse_section(intb_start, patch_start, "INTB", 184)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    inta_path = OUT_DIR / "inta_catalog.json"
    intb_path = OUT_DIR / "intb_catalog.json"

    # Merge with any existing audio extraction data if present
    for path, cat_data in [(inta_path, inta), (intb_path, intb)]:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                for k, v in existing.items():
                    if k in cat_data:
                        if v.get("samples_64") and any(x != 0.0 for x in v["samples_64"]):
                            cat_data[k]["samples_64"] = v["samples_64"]
                            cat_data[k]["freq_hz"] = v.get("freq_hz", 0.0)
                            cat_data[k]["peak"] = v.get("peak", 0.0)
            except Exception as e:
                print(f"Warning reading existing {path}: {e}")

        with open(path, "w", encoding="utf-8") as f:
            json.dump(cat_data, f, indent=2)

    sc_inta = sum(1 for v in inta.values() if v["is_single_cycle"])
    sc_intb = sum(1 for v in intb.values() if v["is_single_cycle"])

    print(f"\n=======================================================")
    print(f" WAVEFORM CATALOGS GENERATED SUCCESSFULLY")
    print(f"=======================================================")
    print(f" INTA: {len(inta)} total waves -> {sc_inta} single-cycle synth waveforms")
    print(f" INTB: {len(intb)} total waves -> {sc_intb} single-cycle synth waveforms")
    print(f" Saved to:")
    print(f"   {inta_path}")
    print(f"   {intb_path}\n")


if __name__ == "__main__":
    build_catalogs()
