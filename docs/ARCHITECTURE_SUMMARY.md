# Juno Spectre architecture

A map of the code as it is today (v1.0), for finding your way around. The
project overview, features and install steps are in the [README](../README.md);
the Launch Control XL3 surface is specified in [LCXL3_LAYOUT.md](LCXL3_LAYOUT.md).

## 1. The big picture

```text
 QML pages (src/spectre/ui/qml)          MIDI controllers (LCXL3, any learned device)
          │  Bridge.<property / slot>                │  rtmidi callbacks
          ▼                                          ▼
 SpectreBridge (ui/bridge): one QObject made of ~17 domain mixins
   state: PatchState (core/patch_state.py) + sequencer song + macros + settings
          │  DT1 / RQ1 through JunoClient (core/protocol*.py)
          ▼
 JunoClient ── MidiDeviceManager (core/midi.py) ── USB-MIDI ── JUNO-DS / XPS-30
                                                   USB audio ◄── audio worker process
```

- The app only writes the synth's **temporary** buffers, never its flash
  unless the user saves to a user slot.
- `scripts/start_spectre.sh` (Qt platform: eglfs on the Pi) →
  `scripts/spectre_app.py` → `launcher.py` `main()` (MIDI manager, port
  watcher, initial sync, splash, signal handling) → `ui/app.py`
  `create_application()` (QML engine + bridge). The `juno-spectre` command
  of a pip install calls the same `main()`.

## 2. Packages

| Package | What lives there |
|---|---|
| `core/sysex.py` | Roland DT1/RQ1 framing, checksums, the address map, nibble packing |
| `core/protocol*.py` | `JunoClient` = `BaseProtocolMixin` (transport, pacing, writer thread, RQ1) + `PerformanceProtocolMixin` + `PatchProtocolMixin` + `FlashProtocolMixin` (user slots, patch image transfers, init template) + `FxBlockWriterMixin` (`protocol_fx.py`: one writer for the patch, performance and part MFX/chorus/reverb blocks). `protocol.py` itself only composes them |
| `core/patch_state.py` | The data model: patch common, 4 tones, effects, TMT, matrix, macros, performance parts and FX, and the one decoder per FX block layout |
| `core/spectre_format.py` | The `.spectre` file envelope (patches, performances/songs, setlists) |
| `core/routing.py`, `mfx_catalog.py`, `categories.py`, `waves.py`, `env_shape.py`, `env_presets.py`, `macro_targets.py` | Synth knowledge: signal routing rules, the 80 MFX types, patch categories, the wave catalog, envelope mapping, the macro target catalog |
| `core/panel_follow.py`, `arpeggio.py` | Following panel changes on the synth; arp settings and MIDI clock out |
| `core/updater.py`, `wifi.py`, `backlight.py`, `telemetry.py` | Pi appliance services (git-release updater, NetworkManager, display, system stats) |
| `control/` | Controller binding model (`mapping.py`) and the LCXL3 screen/LED messages (`lcxl3.py`) |
| `vector/` | The vector pad feature: wavetable maths, the motion recorder and automators, `VectorEngine` (pad moves only; the patch owns tone levels and mutes) |
| `sequencer/` | PPQN clock thread, playback engine (tracks, clips, launch quantization), models, step/live recording, automation lanes, chord names |
| `audio/` | Audio clips: media folder and conversion cache, the worker process that owns the sound device, the sequencer-side player, clock drift lock |
| `librarian/` | `PatchRepository` (user files + SQLite index) and the shipped factory catalog |
| `ui/bridge/` | The QML-facing mixins, one per area: patch, performance, macros, sequencer, automation, audio, setlist, librarian, sync, view, vector, controllers, hardware, follow, tmt, arpeggio, system, jobs. Each sets up its state in its own `_init_<area>()`. Helpers: `fx_target.py` (where an FX edit lands: patch, part or performance FX), `context_knobs.py` (the 8 context knobs per page) |
| `ui/qml/` | `main.qml`, `AppContent.qml` (one `StackLayout` page per view, indexed by `Bridge.activeView`; each page is built the first time it is shown), `components/`, singletons `Theme`, `ScaleMetrics`, `Icons`, `Notes`, `TouchHint` |
| `assets/` | `init_template.json`, `mfx_catalog.json`, wave catalogs, `librarian/factory.db`, controller presets, the splash picture |

## 3. Synth addresses the app uses

| Buffer | Address |
|---|---|
| Model ID (JUNO-DS / XPS-30) | `00 00 3A`, device ID `10` by default |
| Setup (sound mode, ...) | `01 00 00 00` |
| System | `02 00 00 00` |
| Temporary performance (common, FX, parts, zones) | `10 00 00 00` |
| Part patches 1..16 (PERFORM) | `11 00 00 00`, `11 20 00 00`, ... `14 60 00 00` |
| Temporary patch (PATCH mode) | `1F 00 00 00` |

`JunoClient.get_active_patch_base()` picks the right patch buffer for the
sound mode and edited part. Hardware facts found by testing (arp part,
voice use, USB audio mode) are kept in the code comments next to the code
that depends on them.

## 4. Threads and processes

| Where | What |
|---|---|
| UI thread | QML, every bridge slot, all model changes |
| `juno-writer` (`protocol_base.py`) | Sends DT1s queued inside `juno.coalesced_writes()`; the latest value per address wins. Used for continuous controls (macros, automation, vector morphing, tone edits). A read sends the queue first |
| Jobs (`ui/bridge/jobs.py` `_start_job`) | Long synth round-trips (reads, pushes) with progress in the header |
| `part-push` (`_queue_push_jobs`) | A job queue: a performance's mixer, zones and FX, then part images, after a song change or entering PERFORM. A new performance replaces the jobs still waiting |
| MIDI input worker (`core/midi.py`) | Demuxes the Juno input to listeners |
| `SequencerPPQNClock` | The tick thread; sleeps to the tick and yields |
| `midi-clock-out`, `midi-port-watch`, panel follow, arp read, macro part loader | Small dedicated threads |
| Audio worker process (`audio/worker.py`) | Owns the sound device and mixes clips; talks to the app over pipes |

The rule to keep: workers read the synth or do slow work; results are
applied on the UI thread through queued signals, or a job's `done`
callback (the header SYNC runs that way). The launcher installs a
`sys.excepthook` that logs an exception escaping a slot instead of letting
PyQt6 abort the app.

Every direct `send_data` waits for the DT1 pacing gap (~4 ms), so a slot
that sends many writes blocks the UI for that long. Continuous controls go
through `coalesced_writes()` for that reason.

## 5. Data on disk

| Path | Contents |
|---|---|
| `~/.local/share/JunoSpectre/` (or `$JUNOSPECTRE_DATA_DIR`) | `hardware.json` (settings), `librarian.db`, `patches/` (user `.spectre` files), `controller_presets/`, `audio_cache/` |
| `~/SpectreAudio/` (or `audio_dir` in `hardware.json`) | The audio clip media folder |
| `src/spectre/assets/controller_presets/` | Bundled controller presets (LCXL3) |

## 6. Tests

`pytest` from the repo root. `tests/conftest.py` points `HOME` and
`JUNOSPECTRE_DATA_DIR` at a scratch folder for the whole run, so tests never
touch real settings or libraries. Bridge tests use `FakeJuno`
(`tests/test_librarian_bridge.py`), an in-memory synth that answers RQ1s from
what was written.
