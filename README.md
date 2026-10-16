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
| **MIDI controllers** | Learn any knob, fader or button to any macro target, macro or action; per-page and mixer-layer scopes, pickup / smooth scaling, knob position feedback. Launch Control XL3 surface with names, values and LED colours. |
| **Effects & modulation** | MFX Studio (80 algorithms), Master FX, Mod Matrix, Step LFO, Advanced Pitch/TVA/TVF Envelope editors, Routing view and Analog Feel controls. |
| **Appliance-ready** | Boots straight into the Qt UI via KMS/DRM (`eglfs`), with system tools such as brightness, Wi-Fi and an updater. |

### 🎛️ Workstation apps

The UI is organised as a launcher with four categories:

- **Synth Engines:** Juno PCM (4-tone editor), 2D Vector, 1D Wavetable, 4-OSC VA
- **Modulation & FX:** Mod Matrix, Step LFO Editor, Envelopes Editor, Routing, MFX Studio, Master FX
- **Performance & Play:** Macro Deck, Arpeggiator, Performance (16-part mixer and key zones), Sequencer, Live Mode (clip and scene launcher with automation lanes and audio clips), Setlist
- **System & Utilities:** Librarian, MIDI Learn, Hardware Config, System Control

---

## 🧠 How it works

```text
  Touch UI (Qt Quick / QML)        MIDI controller (Launch Control XL3, ...)
            │                                   │
            └───────────────┬───────────────────┘
                            ▼
           Python↔QML bridge + patch / performance state
                            │   paced DT1 writes (continuous controls coalesced)
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

Edits go only to temporary RAM buffers: the temporary Patch (`1F 00 00 00`) or a Performance part's patch (`11 00 00 00` for part 1 … `14 60 00 00` for part 16). Your stored patches stay untouched and there are no voice dropouts.

---

## 🧰 Hardware

**Synth (any of these):** Roland Juno-DS or XPS-30, 61 / 76 / 88 keys.

**Brain:** a Raspberry Pi 4/5, or any PC. Tailored for Linux in general, but specially for a RPi with a touchscreen. Does it work in windows? 🤷 

**Display:** a at least 7" capacitive touchscreen at 1024×600 is recommended.

**Optional controller:** any MIDI controller with knobs, faders or buttons, mapped with MIDI Learn. A ready-made preset ships for the Novation Launch Control XL3, including its screen, LED colours and knob feedback.

---

## 🚀 Getting started

### Requirements

- Python 3.11+ (developed on 3.13)
- ALSA / USB-MIDI access on Linux
- The Python packages in [requirements.txt](requirements.txt) (`PyQt6` for the UI)
- For audio clips: PortAudio and, for stretch/transpose, Rubber Band

### Install

```bash
git clone https://github.com/pfjarschel/JunoSpectre.git
cd JunoSpectre
./scripts/setup_venv.sh
```

This creates `.venv` and installs the requirements into it. It first installs
the system packages listed under `[tool.spectre.system-packages]` in
[pyproject.toml](pyproject.toml) (PortAudio, Rubber Band), asking for your sudo
password if needed. It detects the distro and uses apt (Debian, Ubuntu,
Raspberry Pi OS), dnf (Fedora) or pacman (Arch). On immutable Fedora
(Silverblue, Kinoite, Bazzite, Aurora) it prints the `rpm-ostree install`
command instead. On the Pi the venv also uses the apt `PyQt6`, which is built
for the Pi's own Qt and display; elsewhere pip installs it.

The launcher always runs from `.venv`, and the in-app updater installs each
release's new requirements into it before switching to that release.

### Run (desktop PC and Raspberry Pi)

One unified launcher, with automatic hardware detection. No touchscreen or
synth needed — when nothing is connected the full UI still works offline
(patch editing, saving, librarian), it just doesn't send/receive MIDI:

```bash
./scripts/start_spectre.sh
# equivalent to: python scripts/spectre_app.py
```

Behavior: on a desktop (X11/Wayland) it opens windowed and lets Qt pick the
platform; on a Pi console (no display server, DRM/KMS present) it uses `eglfs`
fullscreen. Useful flags:

```bash
./scripts/start_spectre.sh --list-ports          # show MIDI ports and exit
./scripts/start_spectre.sh --fullscreen          # force fullscreen on desktop
./scripts/start_spectre.sh --windowed            # force windowed on Pi
./scripts/start_spectre.sh --platform xcb        # override Qt platform
./scripts/start_spectre.sh --juno-port NAME      # pick the synth's MIDI port
```

You can also add this to a `systemd` service to boot straight into Spectre.

#### Boot splash (Raspberry Pi OS)

The app opens on a splash picture while the UI loads. To show the same picture
during boot (via Plymouth) instead of the rainbow square and boot text:

```bash
sudo bash scripts/boot-splash/install.sh           # installs; normal boot unchanged
sudo reboot '0 tryboot'                            # one-off test boot with the splash
sudo bash scripts/boot-splash/install.sh --enable  # if the test looked right
```

If the test boot misbehaves, a power cycle boots normally again. `--disable`
returns to the plain boot and `--uninstall` removes everything; the original
`cmdline.txt` and `config.txt` are kept as `*.spectre-bak`. On splash boots the
`tty1` login prompt is skipped (Ctrl+Alt+F2 still opens a local login; ssh is
unaffected).

### Entry Points & CLI

| Script | Purpose |
|--------|---------|
| `scripts/start_spectre.sh` | Production launch wrapper with display/platform detection |
| `scripts/spectre_app.py` | Main touch UI launcher (what `start_spectre.sh` runs) |
| `scripts/spectre_probe.py` | SysEx device probe and identity verification |

### Developer & Data Tools (`tools/`)

| Tool | Purpose |
|------|---------|
| `tools/dump_waveforms.py` | Automated waveform sampler and periodicity classifier |
| `tools/build_wave_catalog.py` | Roland Parameter Guide PDF waveform catalog compiler |
| `tools/dump_factory_catalog.py` | Factory ROM preset dumper and `factory.db` builder |
| `tools/capture_init_template.py` | Captures golden initialized patch template over SysEx |
| `tools/probe_mfx_ranges.py` | Probes MFX parameter ranges and boundaries |
| `tools/scan_mfx_patches.py` | Scans ROM presets for MFX type distribution |
| `tools/sampler_test.py` | Audio input latency and threshold test harness |
| `tools/audio_play_test.py` | Plays a file through the audio worker (audio clip hardware check) |
| `tools/voice_count_test.py` | Polyphony test: does a level-0 tone still cost a voice? |
| `tools/lcxl3_probe.py` | Launch Control XL3 DAW-mode probe: prints every message, sets LEDs and screen |
| `tools/make_splash.py` | Builds the startup splash from the master picture |

### Tests

```bash
pytest
```

---

## 🗂️ Project layout

```text
JunoSpectre/
├── config/
│   └── controller_presets/    # MIDI controller binding presets (e.g. Launch Control XL3)
├── scripts/                   # Production launchers and runtime scripts
├── tools/                     # Offline data dumpers and asset compilers
├── src/spectre/
│   ├── core/                  # SysEx, protocol, MIDI, patch state, MFX, waves, updater
│   ├── control/               # Controller bindings and surface drivers
│   ├── vector/                # Vector maths, motion, engine
│   ├── sequencer/             # Clock, step/clip engine, recording, automation lanes
│   ├── audio/                 # Audio clips: media folder, playback worker, mixer
│   ├── librarian/             # SQLite patch indexing, repository, tagging
│   ├── ui/                    # Qt Quick app, modular Python↔QML bridge, QML views
│   └── assets/                # JSON catalogs, factory DB, waveform metadata
├── tests/                     # pytest suite
└── Resources/                 # Roland reference PDFs (param guide, MIDI implementation)
```

---

## 🗺️ Roadmap

- ✅ **Phase 1:** SysEx core and bidirectional communication
- ✅ **Phase 2:** MIDI learn engine and smooth scaler
- ✅ **Phase 3:** Waveform database and touch keyboard
- ✅ **v1.0:** Vector, wavetable and 4-OSC VA workstation: the engines, Juno PCM editor, MFX, Master FX, Routing, Performance mixer, macros, librarian, sequencer and Live Mode with audio clips, setlists, arpeggiator, Launch Control XL3 surface, Pi appliance (boot splash, Wi-Fi, updater).
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
