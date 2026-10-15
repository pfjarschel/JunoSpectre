# JunoSpectre Developer & Hardware Tooling

This directory contains offline data extraction, hardware inspection, and asset generation utilities for JunoSpectre.

---

## Tool Index

### 1. `dump_waveforms.py`
Automated waveform sampler and empirical periodicity classifier.
- **Requirements:** Connected Roland JUNO-DS / XPS-30 via USB MIDI and USB Audio interface.
- **Function:** Automates SysEx patch initialization, iterates through wave IDs, triggers 80ms note bursts, and classifies waves into single-cycle oscillators vs acoustic samples via cross-correlation and autocorrelation.
- **Audio Output:** Writes raw `.wav` recordings to local development folders (gitignored for copyright reasons). Generates preview data for UI visualization.

```bash
python tools/dump_waveforms.py --bank INTA --start 579 --end 625
```

### 2. `build_wave_catalog.py`
Builds `inta_catalog.json` and `intb_catalog.json` assets from the Roland Parameter Guide.
- **Requirements:** `Resources/JUNO-DS_88_76_61_ParamGuide_eng01_W.pdf` in the repository root.
- **Function:** Extracts waveform names and categories, correlates with verified single-cycle lists, and outputs structured JSON metadata used by `WaveCatalogManager`.

```bash
python tools/build_wave_catalog.py
```

### 3. `dump_factory_catalog.py`
ROM Preset Catalog generator.
- **Requirements:** Connected Roland synth over MIDI.
- **Function:** Queries preset banks over SysEx to index factory patch metadata (Bank Select MSB/LSB, PC, Tone Names, Categories) and builds/populates `src/spectre/assets/librarian/factory.db`.

```bash
python tools/dump_factory_catalog.py --out /tmp/catalog.json --write-db
```

### 4. `capture_init_template.py`
Golden Init Patch template generator.
- **Requirements:** Connected Roland synth over MIDI.
- **Function:** Reads an initialized patch from the synth's temporary edit buffer and serializes the complete binary SysEx image to `src/spectre/assets/init_template.json`.

```bash
python tools/capture_init_template.py
```

### 5. `probe_mfx_ranges.py` & `scan_mfx_patches.py`
MFX parameter inspection and ROM preset MFX type scanner.
- **Function:** Probes MFX parameter ranges and scans presets to identify MFX types and routing configurations.

```bash
python tools/probe_mfx_ranges.py
python tools/scan_mfx_patches.py
```

### 6. `sampler_test.py`
Audio input and sampling test script for verifying soundcard capture latency and level thresholding.

### 7. `voice_count_test.py`
Polyphony test: does a tone at level 0 still use a voice?
- **Requirements:** Connected Roland synth over USB MIDI, plus the USB audio input (same capture setup as `dump_waveforms.py`). Overwrites the temporary patch and switches to PATCH mode.
- **Function:** Holds a low sine probe note, then adds quiet high notes until the probe's voice is stolen (Patch Priority LAST). This is measured for tones 2-4 at level 127, at level 0, and switched off, and reports the voices used per note in each case.

```bash
python tools/voice_count_test.py            # recorded and analysed
python tools/voice_count_test.py --listen   # no audio capture: listen for the low C dropping out
python tools/voice_count_test.py --switch   # listen: what a Tone Switch change does to held notes
```

### 8. `make_splash.py`
Startup splash generator.
- **Requirements:** Pillow.
- **Function:** Scales the master picture (`docs/images/JunoSpectre_splash.jpg`) to cover 1024x600, centre-crops it and writes the app splash `src/spectre/assets/splash_1024x600.jpg` (shown by `main.qml` while the UI loads).

```bash
python tools/make_splash.py [master.jpg]
```

### 9. `audio_play_test.py`
Audio clip playback check.
- **Requirements:** `soundfile` + `sounddevice` (and `libportaudio2` on the Pi); the JUNO in USB Driver VENDOR mode.
- **Function:** Converts a file into the playback cache (in its own process, like the app), starts the audio worker on the JUNO's USB audio and plays it. Without a file it plays a generated 120 BPM click. Reports underruns, the worker's CPU use and the DAC rate against the Pi clock.

```bash
python tools/audio_play_test.py                      # click, 8 s
python tools/audio_play_test.py song.mp3 -s 20       # 20 s of a file
python tools/audio_play_test.py loop.wav --loop 0 2  # loop the first 2 s
python tools/audio_play_test.py song.wav --voices 8  # 8 copies at once (CPU check)
```

### 10. `lcxl3_probe.py`
Launch Control XL3 DAW-mode probe (checks for `docs/LCXL3_LAYOUT.md`).
- **Requirements:** the LCXL3 over USB; the app closed (it uses the same ports).
- **Function:** Puts the LCXL3 in DAW Control (or Mixer) mode, optionally turns on touch events, sets LED colours and the permanent screen's title, and prints every message from both its ports. Ctrl+C leaves DAW mode.

```bash
python tools/lcxl3_probe.py                         # DAW Control mode, print everything
python tools/lcxl3_probe.py --touch                 # + touch events
python tools/lcxl3_probe.py --led 116 45 --led 118 5  # Play blue, Record red
python tools/lcxl3_probe.py --screen "CTX - SCENE 3"  # permanent screen title line
```
