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
         [Roland XPS-30 / Juno-DS]              [Embedded Soft Synth Engine]
         • 4-Tone PCM Sound Generator           • VSTs / Custom Software Synth
         • Integrated 24-bit USB Audio In/Out ◄►• Digital USB Audio Streaming
         • SysEx Local Control Decoupling
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

### Module 3: 2D Vector, 1D Wavetable & 4-OSC Virtual Analog (VA) Engine (`spectre.vector` & `spectre.va`)
* **Cartesian 4-Tone Interpolation:**
  * Maps an X/Y coordinate ($0.0 \le X, Y \le 1.0$) into four Roland TVA Level values:
    $$\text{Tone 1 (NW)} = (1 - X) \times Y \times 127$$
    $$\text{Tone 2 (NE)} = X \times Y \times 127$$
    $$\text{Tone 3 (SW)} = (1 - X) \times (1 - Y) \times 127$$
    $$\text{Tone 4 (SE)} = X \times (1 - Y) \times 127$$
  * Supports Linear and Constant-Power (Equal-Power) crossfade laws.
* **1D Linear Wavetable Scanner:**
  * Smooth sequential crossfade across Tone 1 $\to$ Tone 2 $\to$ Tone 3 $\to$ Tone 4 ($A \to B \to C \to D$).
* **Logarithmic Volume Normalization Curve:**
  * Roland TVA gain behaves exponentially ($dB$), causing single tones or combinations to deviate in perceived volume.
  * Real-time normalization applies an acoustic loudness compensation exponent ($w^{0.29}$) to maintain consistent perceived volume across single-tone corners and mixed centers.
* **4-OSC Virtual Analog (VA) Engine:**
  * Classic multi-oscillator Virtual Analog workflow.
  * **Hardwired Ganged Master Filter & Envelopes:** Master TVF Cutoff, Resonance, and Master TVA/TVF ADSR envelopes are internally ganged by design—no toggle needed in this view.
  * **Oscillator Detune & Mixer:** 4 oscillators with curated analog waveforms (Sine, Tri, Saw, Square, Pulse-Widths, sync-like waves), coarse tune (octaves/semitones), fine tune (cents detune), and individual levels.
* **Motion Recording & Orbital Automators:**
  * Touch gesture loop recorder: captures continuous X/Y trajectories up to 16 bars with tempo sync (BPM), speed scaling (0.25x–4x), and loop modes (Forward, Ping-Pong, Reverse).
  * Built-in geometric motion automators: Circles, Lissajous figures, and Brownian Chaos walks.

### Module 4: Wave Database & Harvester Engine (`spectre.wave_harvester`)
* **Roland Waveform Database (`config/waveforms.json`):**
  * 2,382+ waveforms parsed, verified, and indexed across INTA, INTB, and Axial expansions.
  * Tag-based categorical taxonomy (Analog, Keys, Bass, Strings, Brass, Perc, FX).
  * Prioritized bread-and-butter synth collection (ARP Sine, Sine, JD Tri, VS-Tri, Juno SAW HD, JP-8 Saw, MG Saw HD, P5 Saw HD, Juno Sqr HD, JP-8 Sqr, MG Sqr HD, P5 Sqr HD, JP-8 Pulse widths).
* **Virtual Touch Keyboard & Wave Browser Drawer:**
  * Integrated 5-row responsive touch virtual keyboard for fast search and filtering directly on the touch screen.
  * Live wave preview and instant audition into the temporary buffer.

### Module 5: Touch UI Workstation OS (`spectre.ui`)
* **Engine:** Built with **Qt Quick (QML)** using hardware-accelerated OpenGL scene graphs on the Raspberry Pi (VideoCore GPU) and PC, delivering locked 60 FPS touch response.
* **Canvas Optimization & Self-Contained Architecture:**
  * **Reclaimed $1000\text{px}+ \times 506\text{dp}$ Workspace:** The fixed right-hand 4-tone strip and fixed bottom morph toolbar are eliminated from the global shell. Each engine manages its own canvas width and height, freeing generous space for confident touch targets.
  * **Context Strip (8 Encoders):** Persists below the Top Bar for fast physical knob interaction, but automatically hides on System & Utility views (`HARDWARE`, `SYSTEM`, `LIBRARIAN`, `MIDI LEARN`) expanding vertical canvas to 556dp.
  * **Zero Screen Hopping & Zero Hidden Drawers:** Filter and envelope shaping are directly accessible inside each engine view via dedicated on-panel controls or the Right Flank `SculptorPanel.qml` (~360dp, 100% visible, no hidden drawers).
  * **App Launcher Overlay (`ScreensOverlay.qml`):** Replaced cramped horizontal tabs with a single `[ ⊞ SCREENS: <ACTIVE_VIEW> ▼ ]` button in `HeaderBar.qml` opening a categorized modal overlay presenting 16 touch tiles grouped across 4 distinct categories.
* **17 Workstation Apps Across 4 Categories:**
  1. **SYNTH ENGINES:**
     - **Juno PCM (`PatchEditView.qml`, Default Boot Screen / Index 0):** Full-screen 4-Tone Roland sound designer with stereo Wave L / Wave R selection per tone, dual interactive envelopes (TVF Filter Env with Depth -63..+63 & TVA Amp Env), Portamento Time & Switch, and a master `[LINK ALL TONES: ON/OFF]` toggle button.
     - **2D Vector (`VectorPad.qml`):** 3-column layout featuring automated wave motion orbit controls (Left, ~140dp), 2D morph pad with live oscilloscope and corner badges (Center, >520dp), and Master TVF/TVA/LFO/Pitch `SculptorPanel` (Right, ~360dp).
     - **1D Wavetable (`WavetableSlider.qml`):** 3-column layout featuring sweep automators (Left), 1D linear slider and 3D waterfall scope (Center), and `SculptorPanel` (Right).
     - **4-OSC VA (`VaView.qml`):** 3-column virtual analog console with 4-oscillator mixer/detune (Col 1), master TVF filter & env (Col 2), and master TVA amp with Portamento & Legato (Col 3).
  2. **MODULATION & FX:**
     - **Mod Matrix (`ModMatrixView.qml`):** 4 Roland matrix controllers with source selectors, 4 destinations per controller, and -63..+63 bipolar sensitivities.
     - **Step LFO (`StepLfoView.qml`):** 16-step pattern modulator with horizontal touch drawing grid, tempo sync, glide curves, and live playhead.
     - **Pitch Env (`PitchEnvView.qml`):** Bi-polar multi-segment pitch envelope canvas ($T_1..T_4$, $L_0..L_4$), depth, velocity sensitivity, and quick preset shapes.
     - **Routing (`RoutingView.qml`):** Dedicated signal flow matrix and topology presets (Serial Chain, Studio Aux, Vintage Synth, Ambient Wash) with interactive schematic, live pitfall detection (comb filtering / multi-reverb overload warnings), and 4-column manual sends strips.
     - **MFX Studio (`MfxView.qml`):** Dedicated multi-effects studio for all 80 Roland MFX algorithms with parameter sliders and bypass.
     - **Master FX (`MasterFxView.qml`):** Master Chorus and Master Reverb (no Master EQ: not addressable via SysEx on JUNO-DS).
     - **MFX Studio (`MfxView.qml` + `EqCurvePanel.qml`):** all 80 MFX algorithms with curve editors for 01 EQUALIZER (4-band parametric) and 02 SPECTRUM (8-band graphic).
  3. **PERFORMANCE & PLAY:**
     - **Macro Deck (`MacroDeck.qml`):** 8 large touch dials assigned to physical encoders, with note monitor and panic button.
     - **Perf Mixer (`PerfMixerView.qml`):** 16-part multi-timbral faders, pans, mutes, and split/layer zone editor.
     - **Sequencer (`SeqView.qml`):** 16-step polyphonic trigger grid with arpeggiator styles and octave range.
  4. **SYSTEM & UTILITIES:**
     - **Librarian (`LibrarianView.qml`):** Category-filtered `.spectre` and `.syx` patch database with instant audition, export, and USB import.
     - **MIDI Learn (`MidiLearnView.qml`):** Interactive CC controller surface mapping with live MIDI learn detection.
     - **Hardware Config (`HardwareConfigView.qml`):** Roland Juno-DS / XPS-30 device configuration, SysEx throttling, Local Control switch, and USB controller surfaces.
     - **System Control (`SystemView.qml`):** Appliance system control with fast app restart, display brightness slider, Pi hardware telemetry, Wi-Fi manager with virtual keyboard, and apt system updater.

### Module 6: Preset & Snapshot Architecture (`.spectre`)
* **Universal Preset Format (`.spectre`):**
  * JSON-packaged preset storing the complete Roland temporary patch dump along with Spectre engine states (Active Engine Mode, Vector coordinates, motion loops, macro mappings, and controller bindings).
* **Snapshot & Compare Engine:**
  * Instant A/B state compare and non-destructive live snapshot recall.
  * Clean "Init Spectre Patch" generator for 1-touch blank-slate sound design.

### Module 7: Future Expansion Engines (v2.0 & v3.0)
* **16-Partial Additive Engine (v2.0):**
  * Utilizes 4 Parts (16 tones total) tuned to harmonic ratios ($1f, 2f, 3f, \dots, 16f$).
  * Touch screen allows user to draw single-cycle waveforms; Pi calculates real-time 16-harmonic FFT and pushes TVA levels.
  * Dynamic wavetable sweeps across custom additive frames.
* **EX Mode (Embedded Soft Synth in v3.0):**
  * Embedded soft synth engine (VSTs and/or custom software synthesizer running on Pi).
  * Streams 24-bit digital audio directly into the Juno-DS over bidirectional USB Audio.
  * Automated MIDI isolation: sends SysEx `Local Control = OFF` when entering EX mode so the keyboard triggers only the soft synth, and restores `Local Control = ON` for native patches.

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
│   │   ├── va/                    # 4-OSC Virtual Analog engine logic & detuning
│   │   ├── store/                 # Central Reactive Synth Store & Actions
│   │   │   ├── synth_state.py
│   │   │   └── actions.py
│   │   ├── sequencer/             # 16-step micro-step nanosecond sequencer
│   │   ├── librarian/             # Sysex & .spectre save/load/audition & snapshots
│   │   ├── ex/                    # Embedded Soft Synth Engine supervisor (v3.0)
│   │   └── ui/                    # Qt Quick / QML Touch Application
│   │       ├── main.qml
│   │       ├── components/        # VectorPad.qml, EnvCurve.qml, WaveDrawer.qml, etc.
│   │       ├── views/             # VectorView, WaveView, VaView, EditView, PlayView, PerfView, SeqView
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

### Phase 1: SysEx Core & Communication [Complete]
* [x] Establish bidirectional communication with XPS-30/Juno-DS over ALSA/USB-MIDI.
* [x] Verify Model ID handshake (Juno-DS `00 00 00 37` & XPS-30 variants).
* [x] Temporary Buffer read/write (DT1/RQ1) for TVA Levels, TVF, Envelopes, Wave selection.

### Phase 2: MIDI Learn Engine & Smooth Scaler [Complete]
* [x] Intercept incoming CCs and map dynamically to Roland parameter offsets.
* [x] Implement and benchmark the Smooth Scaling mathematical algorithm.
* [x] Build hardware profiles for Novation Launch Control XL, Midimix, nanoKONTROL2, BeatStep, etc.

### Phase 3: Waveform Database & Touch Virtual Keyboard [Complete]
* [x] Extract all 2,382+ official waveforms from the Roland manual into `config/waveforms.json`.
* [x] Categorize waveforms into tags (Analog, Keys, Bass, Strings, Brass, Perc, FX).
* [x] Prioritize bread-and-butter synth waveforms (ARP Sine, Sine, JD Tri, VS-Tri, Juno/JP8/MG/P5 Saws & Squares, Pulse widths).
* [x] 5-row responsive touch virtual keyboard with search & real-time filtering.

---

### v1.0: The Tactile Vector, Wavetable & VA Workstation (Native Engine)
* [x] **2D Vector Morphing Engine:**
  * Cartesian 4-tone interpolation (Linear and Equal-Power).
  * Real-time 60 FPS morphing oscilloscope preview.
  * Motion loop recorder (1–16 bars, tempo sync, speed scaling, ping-pong, reverse) & geometric automators.
* [x] **1D Wavetable Morphing Engine:**
  * Sequential 4-tone crossfade ($A \to B \to C \to D$).
  * Real-time 2D waveform scope & 3D waterfall display.
* [x] **Acoustic Loudness Normalization:**
  * Perceived loudness compensation curve ($w^{0.29}$) preserving balanced levels between single tones and complex mixes.
* [x] **4-OSC Virtual Analog (VA) Engine:**
  * Multi-oscillator Virtual Analog workflow.
  * Internally hardwired/always ganged master TVF filter & master TVA/TVF ADSR envelopes.
  * 4-oscillator detune & mixer (octaves, semitones, cents detune, analog bread-and-butter waveforms).
* [ ] **Dynamic Buffer Target Router:**
  * Automatic SysEx target routing between Patch mode (`0x1F`) and Performance parts (`0x19 [PartOffset]`).
* [ ] **MIDI Program Change Auto-Sync:**
  * Detect patch/performance changes initiated on the keyboard and update UI state.
* [ ] **Clean "Init Patch" Generator:**
  * 1-touch clean template for unmodulated sound sculpting.
* [ ] **UI Screens & Shell Revamp (1024×600 Touch - Self-Contained Synth Architecture):**
  * [x] Base QML touch shell & persistent Top Bar (sync, patch name, LEDs)
  * [x] Screen Real Estate Revamp: Remove fixed right-hand tone strip and fixed bottom row to liberate full $1024 \times 540$ canvas; make tone mixer contextual/on-demand
  * [x] Vector View Revamped (Large $>400\text{px}$ 2D pad, left orbit/loop panel, right-flank Quick Sculptor touch faders, curve drawer)
  * [x] Wavetable View Revamped (1D slider, 2D scope, 3D waterfall, left loop/scan panel, right-flank Quick Sculptor touch faders)
  * [x] 4-OSC VA View (dedicated 3-column analog synth console: 4-OSC mixer/detune $\to$ Master TVF $\to$ Master ADSR)
  * [x] Standard 4-Tone View (classic Roland 4-tone sound designer, wave browser, velocity splits, optional Gang/Link toggle)
  * [x] Wave Browser Modal with touch virtual keyboard
  * [ ] Performance Layer & Zone Mixer (16-part volume/pan/mutes, patch selector per part, direct Part "EDIT" buttons)
  * [ ] Macro Play Deck (8 customizable macro dials, panic button)
  * [x] Effects (MFX) Studio (visual signal chain & parameters)
  * [ ] MIDI Controller Map & Quick-Touch Learn Screen
  * [ ] Patch Librarian & Preset Browser (`.spectre` and `.syx` management)
  * [ ] Appliance Options & Maintenance Screen (touch reboot/shutdown, brightness, system update)
  * [ ] Splash / Startup Screen

---

### v2.0: Multi-Part & The Additive Frontier
* [ ] **Multi-Part Performance Engine:**
  * Layering Vector + Wavetable + 4-OSC VA + PCM across Roland Parts 1–16 simultaneously.
* [ ] **16-Partial Additive Synth Engine:**
  * Utilizes 4 Roland Parts (16 tones total) tuned to harmonic ratios ($1f, 2f, 3f, \dots, 16f$).
* [ ] **Touch Waveform Drawing Canvas:**
  * Real-time finger drawing of single-cycle waves with instant FFT harmonic calculation pushing Roland TVA levels.
* [ ] **Custom Harmonic Wavetable Sweeps:**
  * Morphing across user-drawn additive wave tables.

---

### v3.0: EX Mode (Hybrid Software Expansion)
* [ ] **Embedded Soft Synth Engine:**
  * Embedded soft synth host (VSTs and/or custom software synthesizer running on Pi).
* [ ] **Integrated 24-bit USB Audio Streaming:**
  * High-fidelity, low-latency digital audio stream from Pi directly through the Juno-DS DAC and headphone jacks.
* [ ] **Automated SysEx Local Control Decoupling:**
  * Sends `Local Control = OFF` when entering EX mode (keybed triggers soft synth only, internal sound engine silenced).
  * Restores `Local Control = ON` when returning to native Roland patches.
* [ ] **Custom Sample & SoundFont Playback on Pi**
