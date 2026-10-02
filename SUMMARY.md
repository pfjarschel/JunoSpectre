# PROJECT JUNO SPECTRE
### Open-Source Next-Gen Brain & Tactile Extension for Roland Juno-DS / XPS Synthesizers

---

## 1. Project Identity & Vision

* **Primary Codename:** **Juno Spectre**
  * *Naming Rationale:* Roland names its flagship workstations after apparitions (**Fantom**) and celestial bodies (**Juno**, **Jupiter**). *Juno Spectre* keeps the heritage of Asteroid 3 Juno while directly claiming the territory of the flagship Fantom at a fraction of the cost.
  * *Alternative Astrological Sub-Codenames:* **Juno Umbra** (the darkest shadow of a celestial eclipse) or **Juno Eidolon** (the classical astral spirit).
* **Mission:** Transform mid-tier Roland PCM synthesis platforms (Roland XPS-30, Juno-DS61, Juno-DS88) into open, tactile, vector-morphing workstations rivaling flagship instruments through an external Linux SBC (Raspberry Pi 4 / PC / Handheld), a capacitive touch interface, and generic MIDI controller support.

---

## 2. High-Level System Architecture

```text
  ┌────────────────────────────────────────────────────────────────────────┐
  │                           JUNO SPECTRE CORE                            │
  │                                                                        │
  │  ┌───────────────────────┐             ┌────────────────────────────┐  │
  │  │  Capacitive Touch UI  │             │   Generic Controller In    │  │
  │  │   (1024x600 Display)  │             │   (Launch Control, etc.)   │  │
  │  └───────────┬───────────┘             └─────────────┬──────────────┘  │
  │              │ Touch Events                          │ CC / Notes      │
  │              ▼                                       ▼                 │
  │  ┌───────────────────────┐             ┌────────────────────────────┐  │
  │  │   2D Vector Engine    │             │     MIDI Learn &           │  │
  │  │  & Motion Automator   │             │     Smooth Scaler          │  │
  │  └───────────┬───────────┘             └─────────────┬──────────────┘  │
  │              │ Normalized Parameters (0.0 - 1.0)     │                 │
  │              └───────────────────┬───────────────────┘                 │
  │                                  ▼                                     │
  │                  ┌───────────────────────────────┐                     │
  │                  │       SysEx / MIDI Engine     │                     │
  │                  │  • Roland DT1/RQ1 Translation │                     │
  │                  │  • Checksum Calculation       │                     │
  │                  │  • Temp Buffer Addressing     │                     │
  │                  └───────────────┬───────────────┘                     │
  │                                  │ Bidirectional USB-MIDI              │
  └──────────────────────────────────┼─────────────────────────────────────┘
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

### Module 1: Roland SysEx Engine (`spectre.sysex`)
* **Protocol Support:** Roland DT1 (Data Set 1, command `0x12`) and RQ1 (Request Data 1, command `0x11`).
* **Hardware Abstraction:**
  * Dynamic Model ID headers: User-selectable between Juno-DS (`00 00 00 37`) and XPS-30 regional variants.
  * Device ID configurable (defaults to `0x10` / 17).
* **Buffer Safety:**
  * All real-time performance tweaks route exclusively to the **Temporary Patch/Performance RAM Buffer**.
  * Prevents flash write lockouts, audio dropouts, and DSP voice resets.
* **Auto Checksum Generation:**
  $$\text{Checksum} = 128 - \left(\sum(\text{Address Bytes} + \text{Data Bytes}) \pmod{128}\right)$$

### Module 2: Hardware-Agnostic MIDI Learn & Smooth Scaling (`spectre.control`)
* **Open Hardware Support:** Zero hard-coded controller bindings. Out-of-the-box templates provided for Novation Launch Control XL, Launchkey, and Akai Midimix, with an integrated listener to bind any external CC/channel to any internal parameter.
* **Controller Profiles (`/profiles/*.json`):**
  * Serialized mappings of CC numbers, channels, and control types (Potentiometer, Continuous Encoder, Fader, Momentary Button, Toggle).
* **Smooth Value Scaling Engine:**
  * Resolves parameter jumping on non-motorized faders during preset or bank switches.
  * Proportional scaling formula dynamically closes the gap between physical position ($P$) and synth value ($V$) without dead zones:
    * Moving Up: $\Delta V = \Delta P \times \frac{127 - V_{\text{current}}}{127 - P_{\text{last}}}$
    * Moving Down: $\Delta V = \vert{}\Delta P\vert{} \times \frac{V_{\text{current}}}{P_{\text{last}}}$
    * Guaranteed convergence at extremes ($0$ and $127$).

### Module 3: 2D Vector & Wavetable Morphing Engine (`spectre.vector`)
* **Cartesian 4-Tone Interpolation:**
  * Maps an X/Y coordinate ($0.0 \le X, Y \le 1.0$) into four Roland TVA Level values:
    $$\text{Tone 1 (NW)} = (1 - X) \times Y \times 127$$
    $$\text{Tone 2 (NE)} = X \times Y \times 127$$
    $$\text{Tone 3 (SW)} = (1 - X) \times (1 - Y) \times 127$$
    $$\text{Tone 4 (SE)} = X \times (1 - Y) \times 127$$
* **1D Linear Wavetable Scanner:**
  * Single fader/knob sweeps across Tone 1 $\to$ Tone 2 $\to$ Tone 3 $\to$ Tone 4 sequentially to simulate progressive wavetable evolution.
* **Motion Recording:**
  * Touch gesture loop recorder: captures continuous X/Y trajectories up to 16 bars and loops the parameter modulation automatically.

### Module 4: Patch Librarian & Snapshot Engine (`spectre.librarian`)
* **Storage Independence:** Bypasses the 256 internal User Patch limit by maintaining a local `.syx` patch database on the Linux host filesystem.
* **Instant Auditioning:**
  * Sends patch dumps directly to the temporary edit buffer via DT1. Audition sounds in $< 15\text{ ms}$ without burning flash slots.
* **Live Snapshot Utility:**
  * Issues RQ1 to pull the active Temporary Patch block and saves the complete tone configuration to disk with user metadata and tags.

### Module 5: Lightweight Step Sequencer (`spectre.sequencer`)
* **Form Factor:** 16-step polyphonic and modulation sequencer designed for direct finger-tapping on small screens.
* **Clock & Timing Engine:**
  * Monotonic nanosecond accumulator (`time.perf_counter_ns`) or hardware ALSA MIDI clock slave (locking to external drum machines or the Roland SH-4d).
  * Avoids Python GIL timing jitter.
* **Tracks:**
  * **Track 1:** Internal XPS-30 / Juno PCM synth channel.
  * **Track 2:** External / Headless VST channel.
  * **Track 3:** Vector parameter automation lane.

### Module 6: Headless Sound Expansion (`spectre.vst`)
* **Host Engine:** Headless Carla instance managed via internal IPC/CLI.
* **Audio Routing:** Routes 24-bit digital audio directly through the XPS-30 USB audio interface using PipeWire/ALSA low-latency drivers, eliminating external DACs.
* **Target Plugins:** Native Linux VSTs / LV2 (Dexed for 6-operator FM, Surge XT for hybrid digital/analog synthesis).

---

## 4. Suggested Repository Structure

```text
juno-spectre/
├── config/
│   ├── hardware_profiles/       # JSON maps for MIDI controllers
│   │   ├── novation_lc_xl.json
│   │   └── default_generic.json
│   └── default_settings.yaml   # Audio drivers, Model ID, MIDI Ports
├── patches/                    # Unlimited .syx patch library
│   ├── leads/
│   ├── pads/
│   └── vector_sets/
├── src/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── sysex.py            # Roland DT1/RQ1, checksums, offsets
│   │   ├── midi_learn.py       # Dynamic hardware event binder
│   │   └── smooth_scaler.py    # Parameter catch-up & smooth scaling
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── vector.py           # 2D crossfade math & motion loops
│   │   ├── sequencer.py        # Micro-step nanosecond MIDI sequencer
│   │   └── librarian.py        # Sysex save/load/audition
│   ├── vst/
│   │   └── carla_bridge.py     # Headless Carla daemon supervisor
│   └── ui/
│       ├── __init__.py
│       ├── components/         # VectorPad, StepGrid, KnobDisplay
│       └── app.py              # Main Kivy / Pygame touch interface
├── scripts/
│   ├── install_dependencies.sh
│   └── start_spectre.sh        # Systemd boot / appliance auto-launch
├── README.md
└── requirements.txt
```

---

## 5. Development Roadmap for Antigravity

* [x] **Phase 1: SysEx Core & Sniffer**
  * Establish bidirectional communication with XPS-30/Juno-DS over ALSA.
  * Verify Model ID handshake and test Temporary Buffer write on TVA Level 1–4.
* [x] **Phase 2: MIDI Learn Engine & Smooth Scaler**
  * Create generic controller listener: intercept incoming CCs and map dynamically to Roland parameter offsets.
  * Implement and benchmark the Smooth Scaling mathematical algorithm.
* [ ] **Phase 3: Vector Synthesis Touch Engine**
  * Build the 2D touch canvas ($1024 \times 600$) with real-time X/Y Cartesian calculation and SysEx output.
* [ ] **Phase 4: Patch Librarian**
  * Implement RQ1 patch memory dump, local `.syx` file storage, and instant-load temporary auditioning.
* [ ] **Phase 5: Carla / VST Integration & Sequencer**
  * Set up headless daemon management for Dexed/Surge XT over USB Audio.
  * Implement the 16-step polyphonic trigger grid with external MIDI clock sync.
