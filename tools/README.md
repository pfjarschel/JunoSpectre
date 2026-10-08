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
