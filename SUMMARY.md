# PROJECT JUNO SPECTRE
### Open-Source Next-Gen Brain & Tactile Workstation OS for Roland Juno-DS / XPS Synthesizers

---

## 1. Project Identity & Vision

* **Primary Codename:** **Juno Spectre**
  * *Naming Rationale:* Roland names its flagship workstations after apparitions (**Fantom**) and celestial bodies (**Juno**, **Jupiter**). *Juno Spectre* preserves the heritage of Asteroid 3 Juno while bringing flagship Fantom-class tactile workflows, deep touch editing, vector synthesis, and unlimited sound expansion to mid-tier Roland PCM platforms at a fraction of the cost.
  * *Alternative Astrological Sub-Codenames:* **Juno Umbra** (the darkest shadow of a celestial eclipse) or **Juno Eidolon** (the classical astral spirit).
* **Mission:** Transform Roland PCM synthesis platforms (Roland XPS-30, Juno-DS61, Juno-DS76, Juno-DS88) into open, tactile, vector-morphing workstations through an external Linux SBC (Raspberry Pi 4 / 5 or PC), a 7" capacitive touch interface ($1024 \times 600$), and generic MIDI controller integration (such as the Novation Launch Control XL).

---

## 2. High-Level System Architecture

```text
  ┌────────────────────────────────────────────────────────────────────────┐
  │                           JUNO SPECTRE CORE                            │
  │                                                                        │
  │  ┌───────────────────────┐             ┌────────────────────────────┐  │
  │  │   Qt Quick / QML UI   │             │   Generic Controller In    │  │
  │  │  (1024x600 Touchscreen│             │  (Launch Control XL, etc.) │  │
  │  └───────────┬───────────┘             └─────────────┬──────────────┘  │
  │              │ Touch Events & Actions                │ CC / Notes      │
  │              ▼                                       ▼                 │
  │  ┌──────────────────────────────────────────────────────────────────┐  │
  │  │                      CENTRAL SYNTH STORE                         │  │
  │  │  • Active SoundMode (Patch / Performance)                        │  │
  │  │  • Patch Common & 4x Tone State (TVF, TVA, Pitch, LFO, Wave)     │  │
  │  │  • Performance State (Parts 1-16, Split/Layer Zones)             │  │
  │  │  • 8 Multi-Parameter Macros & Motion Loops                       │  │
  │  │  • Contextual & Direct Hardware Controller Mappings              │  │
  │  └──────────────────────────────────┬───────────────────────────────┘  │
  │                                     │ Dispatch with Rate Limiter (50Hz)│
  │                                     ▼                                  │
  │                  ┌───────────────────────────────────┐                 │
  │                  │        SysEx / MIDI Engine        │                 │
  │                  │   • Roland DT1/RQ1 Translation    │                 │
  │                  │   • Checksum Calculation          │                 │
  │                  │   • Temp Buffer Addressing        │                 │
  │                  │     (Patch: 1F / Perf Parts: 19)  │                 │
  │                  └──────────────────┬────────────────┘                 │
  │                                     │ Bidirectional USB-MIDI           │
  └─────────────────────────────────────┼──────────────────────────────────┘
                                        │
                    ┌───────────────────┴───────────────────┐
                    │                                       │
                    ▼                                       ▼
         [Roland XPS-30 / Juno-DS]              [Carla Headless VST Host]
         • 4-Tone PCM Sound Generator           • Dexed (Yamaha DX7 FM)
         • Integrated 24-bit USB Audio Out ────► • Surge XT (Hybrid Wavetable)
```

---

## 3. Core Software Modules & Functional Specs

### Module 1: Roland SysEx Engine (`spectre.core`)
* **Protocol Support:** Roland DT1 (Data Set 1, command `0x12`) and RQ1 (Request Data 1, command `0x11`).
* **Hardware Abstraction:**
  * Dynamic Model ID headers: User-selectable between Juno-DS (`00 00 00 37`) and XPS-30 regional variants.
  * Device ID configurable (defaults to `0x10` / 17).
* **Buffer Safety & Direct Multi-Part Access:**
  * Performance tweaks route exclusively to Temporary RAM Buffers (prevents flash wear and voice dropouts).
  * **Patch Mode:** Targets Temporary Patch Buffer (`0x1F 0x00 0x00 0x00`).
  * **Performance Mode:** Targets individual Part Temporary Buffers (`Part 1: 0x19 0x00 0x00 0x00`, `Part 2: 0x19 0x02 0x00 0x00`, ... `Part 16: 0x19 0x1E 0x00 0x00`), allowing **deep patch editing of any layer directly inside Performance Mode** without changing synth modes!
* **Auto Checksum Generation:**
  $$\text{Checksum} = 128 - \left(\sum(\text{Address Bytes} + \text{Data Bytes}) \pmod{128}\right)$$

### Module 2: Hardware-Agnostic MIDI Learn & Smooth Scaling (`spectre.control`)
* **Controller Modes:**
  * **Expanded Mode (for 24-knob surfaces like Launch Control XL):** 8 dedicated knobs for Macros, 8 knobs for active Tone TVF/TVA, 8 knobs for LFO/FX, 8 faders for Tone levels + Master, 16 buttons for Mute/Solo and Tab selection.
  * **Context / Focus Mode (for compact 8-knob controllers):** Physical encoders dynamically bind to the Context Strip of the currently active touchscreen view.
* **Controller Profiles (`/config/hardware_profiles/*.json`):**
  * Serialized mappings of CC numbers, channels, and control types (Potentiometer, Continuous Encoder, Fader, Momentary Button, Toggle).
* **Smooth Value Scaling Engine:**
  * Proportional scaling formula dynamically closes the gap between physical position ($P$) and synth value ($V$) without dead zones:
    * Moving Up: $\Delta V = \Delta P \times \frac{127 - V_{\text{current}}}{127 - P_{\text{last}}}$
    * Moving Down: $\Delta V = \vert{}\Delta P\vert{} \times \frac{V_{\text{current}}}{P_{\text{last}}}$

### Module 3: 2D Vector & Wavetable Morphing Engine (`spectre.vector`)
* **Cartesian 4-Tone Interpolation:**
  * Maps an X/Y coordinate ($0.0 \le X, Y \le 1.0$) into four Roland TVA Level values:
    $$\text{Tone 1 (NW)} = (1 - X) \times Y \times 127$$
    $$\text{Tone 2 (NE)} = X \times Y \times 127$$
    $$\text{Tone 3 (SW)} = (1 - X) \times (1 - Y) \times 127$$
    $$\text{Tone 4 (SE)} = X \times (1 - Y) \times 127$$
  * Supports Linear and Constant-Power (Equal-Power) crossfade laws.
* **1D Linear Wavetable Scanner:**
  * Smooth sequential crossfade across Tone 1 $\to$ Tone 2 $\to$ Tone 3 $\to$ Tone 4 ($A \to B \to C \to D$).
* **Motion Recording & Orbital Automators:**
  * Touch gesture loop recorder: captures continuous X/Y trajectories up to 16 bars with tempo sync (BPM), speed scaling (0.25x–4x), and loop modes (Forward, Ping-Pong, Reverse).
  * Built-in geometric motion automators: Circles, Lissajous figures, and Brownian Chaos walks.

### Module 4: Wave Harvester & Sound Profiler (`spectre.wave_harvester`)
* **Automated Wave Profiling Script (`scripts/wave_harvester.py`):**
  * Initializes a clean, unmodulated test patch in the synth temporary buffer (Tone 1 active, TVF bypassed, instant square envelope, effects at 0).
  * Rapidly steps through all 2,402 internal ROM waves (INTA, INTB) and Axial expansion waves (EXP-01..10).
  * Triggers ultra-short audition bursts (80–100 ms Middle C).
  * Performs fast pitch/periodicity autocorrelation ($R(\tau) \ge 0.98$) to automatically classify waveforms:
    1. Single-Cycle Looping Waves (extracts 1-period vector SVG for the UI)
    2. Sustained Multi-Cycle Synth / Pad Waves
    3. Decaying Acoustic PCM Samples
    4. One-Shot Percussion & Transients
    5. Complex / FX Textures
* **Database & Wave Browser:**
  * Extracted Roland wave database stored in `config/waveforms.json`.
  * Touch drawer on the Patch Edit screen for instant categorized selection, search, and live audition.

### Module 5: Touch UI Workstation OS (`spectre.ui`)
* **Engine:** Built with **Qt Quick (QML)** using hardware-accelerated OpenGL scene graphs on the Raspberry Pi (VideoCore GPU) and PC, delivering locked 60 FPS touch response.
* **Screens ($1024 \times 600$ Touch Display):**
  1. **Top Bar (Persistent):** Mode [PATCH / PERF], Patch Name, Active Part/Layer, BPM / Tap Tempo, MIDI Activity LEDs.
  2. **Context Strip:** Visual reflection of the 8 physical encoders for the current view.
  3. **Vector & Morph Pad:** Glowing 2D touch puck, animated trajectory trails, corner tone badges with real-time level glow.
  4. **Wavetable Scanner:** 1D linear slider with 4-zone crossfade visualization.
  5. **Macro Play Deck:** 8 customizable multi-parameter macro dials, chord/note monitor, octave/transpose, and Panic button.
  6. **Patch & Tone Editor (Zero Menu Diving):**
     - Master Patch Common (Cutoff offset, Reso offset, Level, Pan, Sends).
     - 4 Tone Tabs with Mute/Solo, Level VU meters, and Wave badge.
     - Interactive TVF Filter curve display with draggable cutoff & resonance.
     - Interactive TVF & TVA ADSR envelope curve drag points.
     - Dual LFO modulation matrix.
  7. **Performance Layer & Zone Mixer:**
     - 16-Part mixer (levels, pans, mutes).
     - Visual 61/88-key split/layer zone editor.
     - Instant jump to edit any Part's patch buffer without leaving Performance Mode.
  8. **Effects (MFX) Studio:** Visual signal flow (Tones $\to$ MFX $\to$ Chorus $\to$ Reverb) with graphical parameter controls.
  9. **Patch Librarian & Snapshots:** Unlimited `.syx` patch database on disk, tag-based browsing, instant audition (< 15 ms), and one-touch live snapshot saving.
  10. **Step Sequencer:** 16-step polyphonic trigger grid, Euclidean rhythm generator, and parameter modulation lane.

---

## 4. Suggested Repository Structure

```text
juno-spectre/
├── config/
│   ├── hardware_profiles/          # JSON maps for MIDI controllers (LCXL, Midimix, etc.)
│   ├── waveforms.json             # Complete categorized Roland wave database
│   └── default_settings.yaml      # Audio drivers, Model ID, MIDI Ports
├── patches/                       # Unlimited .syx patch library
│   ├── leads/
│   ├── pads/
│   └── vector_sets/
├── src/
│   ├── spectre/
│   │   ├── core/                  # Protocol, SysEx, Checksums, MIDI Device Manager
│   │   │   ├── sysex.py
│   │   │   ├── midi.py
│   │   │   ├── protocol.py
│   │   │   └── wave_table.py      # Waveform lookup & category queries
│   │   ├── control/               # Hardware profiles, MIDI learn, smooth scaling
│   │   │   ├── models.py
│   │   │   ├── profiles.py
│   │   │   ├── smooth_scaler.py
│   │   │   ├── midi_learn.py
│   │   │   └── engine.py
│   │   ├── vector/                # 2D crossfade math, 1D wavetable, motion loops
│   │   │   ├── math.py
│   │   │   ├── motion.py
│   │   │   └── engine.py
│   │   ├── store/                 # Central Reactive Synth Store & Actions
│   │   │   ├── synth_state.py
│   │   │   └── actions.py
│   │   ├── sequencer/             # 16-step micro-step nanosecond sequencer
│   │   ├── librarian/             # Sysex save/load/audition & snapshots
│   │   ├── vst/                   # Headless Carla daemon supervisor
│   │   └── ui/                    # Qt Quick / QML Touch Application
│   │       ├── main.qml
│   │       ├── components/        # VectorPad.qml, EnvCurve.qml, WaveDrawer.qml, etc.
│   │       ├── views/             # VectorView, EditView, PlayView, PerfView, SeqView
│   │       └── bridge.py          # Python-QML reactive properties bridge
├── scripts/
│   ├── spectre_control.py         # Hardware profile inspector & MIDI learn CLI
│   ├── spectre_vector.py          # Vector Touch Appliance launcher
│   ├── wave_harvester.py          # Automated audio sampling & wave classifier
│   └── extract_wave_names.py      # PDF manual wave table parser
├── tests/
│   ├── test_sysex.py
│   ├── test_protocol.py
│   ├── test_smooth_scaler.py
│   ├── test_vector_math.py
│   ├── test_vector_motion.py
│   └── test_synth_store.py
├── README.md
└── requirements.txt
```

---

## 5. Revised Phased Development Roadmap

* [x] **Phase 1: SysEx Core & Sniffer**
  * Establish bidirectional communication with XPS-30/Juno-DS over ALSA/USB-MIDI.
  * Verify Model ID handshake and test Temporary Buffer write on TVA Level 1–4.
* [x] **Phase 2: MIDI Learn Engine & Smooth Scaler**
  * Intercept incoming CCs and map dynamically to Roland parameter offsets.
  * Implement and benchmark the Smooth Scaling mathematical algorithm.
  * Build hardware profiles for Novation Launch Control XL, Midimix, nanoKONTROL2, BeatStep, etc.
* [ ] **Phase 3A: Waveform Database & Harvester Engine**
  * Extract all official waveform names and numbers from the Roland manual into `config/waveforms.json`.
  * Categorize waveforms into tags (Analog, Keys, Bass, Strings, Brass, Perc, FX).
  * Add wave query (`get_tone_wave_info`) and wave set (`set_tone_wave`) methods to `JunoClient`.
  * Build the automated `wave_harvester.py` utility for 100 ms audio profiling and single-cycle detection.
* [ ] **Phase 3B: Reactive Synth Store & Controller Context Engine**
  * Implement centralized `SynthStore` managing SoundMode, Patch Common, 4x Tones, Performance Parts 1–16, and 8 Macros.
  * Implement Dual Controller Mapping: Expanded (24-knob direct) vs Focus (8-knob contextual).
  * Rate-limited SysEx dispatch queue (50Hz) with dirty-state byte deduplication.
* [ ] **Phase 3C: 2D Vector & 1D Wavetable Morphing Engine**
  * Implement Cartesian 4-tone interpolation (Linear and Equal-Power).
  * Implement 1D sequential wavetable morphing ($A \to B \to C \to D$).
  * Implement gesture motion loop recorder (1–16 bars, tempo sync, speed scaling, ping-pong, reverse).
  * Implement geometric automators (Circle, Lissajous, Chaos walk).
* [ ] **Phase 3D: Qt Quick / QML Touch UI Shell & Vector View (1024×600)**
  * Set up hardware-accelerated Qt Quick runtime for Raspberry Pi and PC.
  * Build persistent Top Bar, Context Strip, and Persistent Tone VU/Mute Strip.
  * Build the interactive Vector Pad with glowing puck, trajectory trails, and animated playback.
* [ ] **Phase 3E: Macro Play Deck & Contextual Encoders**
  * Build the 8-Macro touch interface with customizable multi-destination parameter mapping.
  * Add chord/note display, transpose, and Panic button.
* [ ] **Phase 3F: Tactile Patch & Tone Editor (Zero Menu Diving)**
  * Interactive TVF Filter curve display and draggable Cutoff/Reso points.
  * Interactive TVF & TVA ADSR envelope curve editors.
  * Slide-out Wave Browser with categories, search, and live audition.
* [ ] **Phase 3G: Performance Layer & Zone Mixer**
  * 16-Part volume/pan mixer and visual 61/88-key split/layer zone editor.
  * Direct jump to edit any layer's patch buffer (`0x19 0x00...`) inside Performance Mode.
* [ ] **Phase 4: Patch Librarian & Snapshot Manager**
  * RQ1 patch memory dump and unlimited local `.syx` patch database.
  * Instant temporary audition (< 15 ms via DT1) and live snapshot utility.
* [ ] **Phase 5: Workstation Step Sequencer**
  * 16-step polyphonic trigger grid with external ALSA MIDI clock synchronization.
  * Multi-track routing: Roland Synth, External VST, and Parameter modulation lanes.
* [ ] **Phase 6: Headless Carla VST Host (Dexed / Surge XT)**
  * Headless Carla daemon integration over Roland 24-bit USB audio interface.
