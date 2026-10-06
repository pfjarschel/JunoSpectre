# 🌌 Juno Spectre

### An open-source tactile brain & workstation OS for Roland Juno-DS / XPS-30 synthesizers

![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Qt](https://img.shields.io/badge/UI-Qt%20Quick%20%2F%20QML-41CD52?logo=qt&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20Raspberry%20Pi-lightgrey)

**Juno Spectre** turns a mid-tier Roland JUNO-DS/XPS-30 PCM synth into something much closer to a flagship workstation. A Raspberry Pi (or any Linux PC), a 7" 1024×600 touchscreen and, optionally, a generic MIDI controller become a deep editor for the synth's 4-tone engine. On top of that sit vector synthesis, wavetable-style morphing, a 4-oscillator virtual-analog mode, motion recording, a full effects studio and more. The whole thing talks to the synth over USB-MIDI using Roland SysEx.

> The name follows Roland's tradition of apparitions (*Fantom*) and celestial bodies (*Juno*, *Jupiter*): the heritage of the asteroid Juno, plus a ghost in the machine that is definitely not a *f*antom.

The idea for this came to me one day when I saw a picture of a D-50 and the associated programmer, and thought: I have the JUNO-DS lying here gathering dust... It would be so cool if it had a programmer like that!

---

## ✨ Features

| Area | What you get |
|------|--------------|
| **SysEx engine** | Roland DT1/RQ1 translation, automatic checksums, configurable Device/Model ID, writes to *temporary* buffers only (no flash wear). |
| **2D Vector morphing** | Drag a point on an XY pad to crossfade the four Tones, with linear or equal-power laws and a live oscilloscope preview. |
| **1D Wavetable scanner** | Sweep A → B → C → D smoothly, with 2D scope and 3D waterfall display. |
| **Loudness normalization** | Perceptual compensation (`w^0.29`) keeps the volume consistent between single-tone corners and blended centers. |
| **4-OSC Virtual Analog** | A classic analog-style console with a ganged master filter and envelopes, per-oscillator detune and level. |
| **Motion recorder** | Record touch gestures for vector wave morphing, 0.25×–4× speed and forward/ping-pong/reverse loops. Includes circle, Lissajous and Brownian automators. |
| **Waveform catalog** | 2,382+ Roland waveforms indexed and tagged (Analog, Keys, Bass, Strings, Brass, Perc, FX), with a touch keyboard for fast search. |
| **MIDI Learn & smooth scaling** | Hardware profiles for common controllers, plus jump-free "proportional catch-up" knob scaling. |
| **Effects & modulation** | MFX Studio (80 algorithms), Master FX, Mod Matrix, Step LFO, Advanced Pitch/TVA/TVF Envelope editors, Routing view and Analog Feel controls. |
| **Appliance-ready** | Boots straight into the Qt UI via KMS/DRM (`eglfs`), with system tools such as brightness, Wi-Fi and an updater. |

### 🎛️ Workstation apps

The UI is organised as a launcher with four categories:

- **Synth Engines:** Juno PCM (4-tone editor), 2D Vector, 1D Wavetable, 4-OSC VA
- **Modulation & FX:** Mod Matrix, Step LFO Editor, Envelopes Editor, Routing, MFX Studio, Master FX
- **Performance & Play:** Macro Deck, Performance Control, Sequencer
- **System & Utilities:** Librarian, MIDI Learn, Hardware Config, System Control

> Some of these apps are still in progress. See the [Roadmap](#-roadmap).

---

## 🧠 How it works

```text
  Touch UI (Qt Quick / QML)        MIDI controller (Launch Control XL, ...)
            │                                   │
            └───────────────┬───────────────────┘
                            ▼
                 Central synth state store
                            │   rate-limited dispatch (~50 Hz)
                            ▼
                  SysEx / MIDI engine (DT1 / RQ1)
                            │   bidirectional USB-MIDI
                            ▼
              Roland Juno-DS / XPS-30 (4-tone PCM engine)
```

### The vector maths

A point `(X, Y)` in the unit square is mapped to the four Tone levels:

```
Tone 1 (NW) = (1 − X) · Y
Tone 2 (NE) =  X · Y
Tone 3 (SW) = (1 − X) · (1 − Y)
Tone 4 (SE) =  X · (1 − Y)
```

Each level is scaled to 0–127 and sent as a TVA level, after loudness normalization.

### Checksums

Roland SysEx checksums are computed automatically:

```
checksum = 128 − (sum(address bytes + data bytes) mod 128)
```

### Buffer safety

Edits go only to temporary RAM buffers: the temporary Patch (`1F 00 00 00`) or a Performance Part (`19 xx 00 00`). Your stored patches stay untouched and there are no voice dropouts.

---

## 🧰 Hardware

**Synth (any of these):** Roland Juno-DS or XPS-30, 61 / 76 / 88 keys.

**Brain:** a Raspberry Pi 4/5, or any PC. Tailored for Linux in general, but specially for a RPi with a touchscreen. Does it work in windows? 🤷 

**Display:** a at least 7" capacitive touchscreen at 1024×600 is recommended.

**Optional controller:** any MIDI controller with knobs or faders. Profiles are included for:

- Novation Launch Control XL and Launchkey
- Akai MIDImix
- Korg nanoKONTROL2 and nanoKONTROL Studio
- Behringer X-Touch Mini
- Arturia BeatStep
- A generic default profile

---

## 🚀 Getting started

### Requirements

- Python 3.11+ (developed on 3.13)
- ALSA / USB-MIDI access on Linux
- `PyQt6` for the UI, plus the packages in [requirements.txt](requirements.txt)

### Install

```bash
git clone https://github.com/pfjarschel/JunoSpectre.git
cd JunoSpectre
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install PyQt6   # needed by the UI launcher
```

### Run on a desktop (mock mode)

No touchscreen or synth needed:

```bash
./scripts/dev_run.sh
# equivalent to: python scripts/spectre_vector.py --mock
```

### Run as an appliance (Raspberry Pi)

Launches fullscreen directly on the display via `eglfs`:

```bash
./scripts/start_spectre.sh
```

You can also add this to a `systemd` service to boot straight into Spectre.

### Other tools

| Script | Purpose |
|--------|---------|
| `scripts/spectre_vector.py` | Main touch UI launcher |
| `scripts/spectre_control.py` | Hardware profile inspector and MIDI learn CLI |
| `scripts/spectre_probe.py` | Probe the connected synth |
| `scripts/build_wave_catalog.py` | Build the waveform catalog |
| `scripts/dump_waveforms.py` | Dump waveform data |
| `scripts/probe_mfx_ranges.py`, `scan_mfx_patches.py` | Explore MFX parameter ranges |

### Tests

```bash
pytest
```

---

## 🗂️ Project layout

```text
JunoSpectre/
├── config/
│   └── hardware_profiles/     # JSON maps for MIDI controllers
├── scripts/                   # Launchers and developer tools
├── src/spectre/
│   ├── core/                  # SysEx, protocol, MIDI, patch state, MFX, waves, updater
│   ├── control/               # Hardware profiles, MIDI learn, smooth scaler
│   ├── vector/                # Vector maths, motion, engine
│   ├── ui/                    # Qt Quick app, Python↔QML bridge, QML views
│   └── assets/waveforms/      # Waveform catalog
├── tests/                     # pytest suite
└── Resources/                 # Roland reference PDFs (MIDI implementation, parameter guide)
```

---

## 🗺️ Roadmap

- ✅ **Phase 1:** SysEx core and bidirectional communication
- ✅ **Phase 2:** MIDI learn engine and smooth scaler
- ✅ **Phase 3:** Waveform database and touch keyboard
- 🚧 **v1.0:** Vector, wavetable and 4-OSC VA workstation. Done: the engines, Juno PCM editor, MFX, Master FX, Routing. Remaining: dynamic buffer router for Performance parts, Program Change auto-sync, Init Patch generator, Performance control, Macro deck, Librarian, splash screen.
- 🔮 **v2.0:** Multi-part performance engine, 16-partial additive synth with touch-drawn waveforms and custom harmonic sweeps
- 🔮 **v3.0 (EX Mode):** Embedded soft synth host, 24-bit USB audio streaming into the synth, automatic Local Control switching, SoundFont/sample playback. Likely not going to happen, except maybe for the sample playing part.

---

## 🤝 Contributing

Contributions, bug reports and ideas are welcome. Please open an issue to discuss larger changes first, and run `pytest` before sending a pull request.

## ⚠️ Disclaimer

Juno Spectre is an independent project and is **not affiliated with or endorsed by Roland Corporation**. Roland, Juno-DS and XPS-30 are trademarks of their respective owners. The included reference PDFs are Roland's documentation and remain their property. SysEx is sent to your instrument at your own risk, so back up your user patches first.

## 📜 License

Juno Spectre is free software, released under the **GNU General Public License v3.0**. See [LICENSE](LICENSE) for the full text.

```
Copyright (C) 2026 pfjarschel

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
```
