# Juno Spectre — Code Review & Cleanup Plan

Review date: 2026-10-08. Baseline: `pytest` → **269 passed** (13.7 s), so the core logic is in decent shape. The problems below are about structure, hygiene and robustness rather than known failing behaviour.

Findings are tagged **[High]**, **[Med]** or **[Low]**. Line numbers are approximate and will drift.

---

## 1. Structural problems

### 1.1 `SpectreBridge` is a god object — [High]
[bridge.py](src/spectre/ui/bridge.py) is **7,345 lines**. One class (`SpectreBridge`) has **~494 methods**, about 89 slots/properties/signals, and owns patch editing, performance mode, librarian, Wi-Fi, updater, backlight, vector/motion, macros, MIDI learn, routing, telemetry and flash writes.

Consequences: hard to navigate, hard to test (UI tests need the whole bridge), merge conflicts, and every change risks side effects.

Proposed split (keep `SpectreBridge` as a thin facade at first so QML does not change):
- `bridge/patch.py` (patch/tone editing)
- `bridge/performance.py`
- `bridge/librarian.py`
- `bridge/system.py` (wifi, updater, backlight, telemetry)
- `bridge/vector.py` (vector pad, motion, macros)
- `bridge/midi_control.py` (learn, hardware profiles)
- Register each as its own QML context object/singleton once stable.

### 1.2 `JunoClient` in `protocol.py` — [High]
[protocol.py](src/spectre/core/protocol.py) is 3,232 lines and `JunoClient` is ~2,940 lines with 130 methods. It mixes address maps/constants, low-level DT1/RQ1 I/O, patch read/write, performance parts, MFX, flash-write/verify and init-patch logic.

Proposed: `addresses.py` (constants), `transport.py` (send/recv/retry), and separate modules for patch, performance, effects and flash-write. The module also has ~25 unused imported constants (see 3.1).

### 1.3 Other oversized units — [Med]
- `ToneState` (51 methods) and `PatchState` in [patch_state.py](src/spectre/core/patch_state.py) (1,014 lines) combine data model, SysEx decode and mutation logic.
- `PatchRepository` ([repository.py](src/spectre/librarian/repository.py), 841 lines) mixes schema/migrations, scanning, search and file I/O.
- QML: `PatchEditView.qml` (1,260), `RoutingView.qml` (992), `SystemView.qml` (973), `VectorPad.qml` (836), `SculptorPanel.qml` (801), `LibrarianView.qml` (775). Split into sub-components.

### 1.4 Layering violations — [Med]
- The bridge calls private members of other layers: `repo._touch_file_row(...)` (bridge ~L5684, L6527), `juno._write_patch_regions(...)`, `juno._verify_patch_regions(...)` (~L6583–6590). Make these public API on `PatchRepository` / `JunoClient`.
- Flash write/verify/restore sequences live in the bridge (~L6500–6600) with their own `sleep`s. They belong in the protocol layer, which already owns `FLASH_SETTLE_S`.
- `hasattr`/`getattr(..., default)` is used **198 times** in the bridge, including chains such as `getattr(getattr(getattr(self.engine, "juno"...)))` (~L1002–1007). This hides typos and missing attributes and indicates unclear object contracts. Give those objects defined interfaces (dataclasses/Protocols) and drop the defensive access.

---

## 2. Correctness & robustness risks

### 2.1 Swallowed exceptions — [High]
About **100** `except` blocks in `src/`, and **~64 of them just `pass`/`continue`**. Many `except Exception` handlers log at `debug` only (e.g. backlight, telemetry and Wi-Fi poll in the bridge). On an appliance this makes field failures invisible.

To do:
- Catch specific exceptions.
- Log at `warning`/`exception` for anything that affects state or hardware writes.
- Surface hardware write failures to the UI instead of silently continuing.
- Audit with `ruff` rules `BLE001`, `S110`, `S112`, `SIM105`.

### 2.2 Threading — [High]
Only a few threads are spawned (`bridge.py` ~L1877, L7088, L7215), plus `_push_lock` (L210), but the bridge is a `QObject` with 494 methods and a lot of mutable state.
- Verify that worker threads never touch QObject state or emit signals un-queued (PyQt signals are thread-safe, but plain attribute mutation is not).
- Lock coverage is a single `_push_lock`; MIDI I/O (`protocol.py` sends/receives, `time.sleep(0.005)` polling loops at ~L355/L392) is not clearly serialized across the UI thread, the worker threads and the control engine.
- Replace sleep-polling with a condition/queue-based receive.
- Replace ad-hoc `threading.Thread(...daemon=True)` with a small task runner (`QThreadPool`/`QRunnable` or one executor) with cancel/shutdown handling.

### 2.3 Blocking sleeps on hot paths — [Med]
`time.sleep` calls in the bridge (~L5994–6083, 6501, 6589) and in `protocol.py` (flash settle 0.4 s etc.). Confirm none run on the Qt GUI thread; if any do, the UI freezes during writes.

### 2.4 Wi-Fi helper: password on argv & backend choice — [Med] (feature stays; only hardening/portability)
The Wi-Fi UI is a deliberate convenience for RPi/minimal-OS appliances, and [wifi.py](src/spectre/core/wifi.py) already degrades gracefully (`available=False` when nmcli/iface are missing) with an injectable runner for tests. Keep it. Two improvements:

1. **Password visible in `ps`** (L384–385: `nmcli ... password <pw>`). Fixes, easiest first:
   - `nmcli --ask dev wifi connect <ssid>` and feed the password on **stdin** (no argv exposure; minimal change, still testable via the runner);
   - or create the profile via the NetworkManager **D-Bus API**, which avoids argv and text parsing entirely.
   - Either way, ensure the password is never logged or stored in UI state longer than needed.
2. **Backend coupling to NetworkManager.** "Minimal OS" often means no NM (Raspberry Pi OS Lite *Bookworm+* and Ubuntu desktop have it; Alpine, DietPi, Buildroot, older Raspbian typically use `wpa_supplicant`/`dhcpcd`, `iwd`, `connman` or `systemd-networkd`). Options:
   - **(Recommended) keep nmcli as the default and put it behind a small `WifiBackend` interface** (`scan/status/connect/disconnect/forget/radio`), so a `wpa_cli`/`iwctl` backend can be added later if a target OS needs it. The bridge/QML keep talking to `WifiManager` only.
   - Switch to NM D-Bus (via `QtDBus`, already in PyQt6): more robust (signals instead of polling every ~6 s, structured data, secrets handled properly) but still NM-only and more code.
   - A first-boot **AP/captive-portal provisioning** mode is the other common appliance pattern, but it is a bigger feature and only needed for headless units without a screen — not applicable here since you have a touch UI.

   I'd do: stdin password now (small), backend interface when a non-NM target actually shows up.

### 2.5 Updater — [Med]
[updater.py](src/spectre/core/updater.py) is git-based (describe/tag/status/checkout). Confirm that:
- dirty-tree handling (`status --untracked-files=no`) cannot lose local changes;
- an update that fails mid-way leaves a bootable state (rollback to the previous tag);
- local-only, gitignored files (wavs, `scratch/`, `Resources/`) are not touched by an update.

### 2.6 MIDI I/O error handling — [Med]
There is no clear policy for device disconnect/reconnect, partial SysEx, or timeouts (`read_*` return paths). Define one (exceptions vs. `None`) and apply it consistently.

### 2.7 Hardware Sync blocks GUI thread — [High]
`syncPatchFromSynth()` in `bridge.py` is invoked as a `@pyqtSlot` directly on the Qt GUI thread when tapping "SYNC". It calls `read_full_patch(timeout=1.0)` which makes 10+ sequential SysEx RQ1 roundtrips. When the synth is slow, busy or times out, the 60 FPS UI freezes for 1–10 seconds. Move sync off-thread with a non-blocking busy state in QML.

### 2.8 Hot-plug / MIDI disconnect recovery — [Med]
`MidiDeviceManager` connects at launch only. If a USB cable is bumped or power-cycled, sends raise unhandled `ConnectionError` / `rtmidi.SystemError` and the application never reconnects. Add an auto-reconnect background heartbeat or recovery on failed send/receive.

### 2.9 Signal handling & stuck notes panic — [Med]
When terminated via `SIGTERM` or `SIGINT` (systemd, process manager), the app exits without sending `All Notes Off` (Panic) or releasing ALSA ports, often leaving sustained hanging notes on the hardware synthesizer. Register signal handlers in the launcher.

---

## 3. Redundancy & dead code

### 3.1 Unused imports/constants — [Low]
Found with a quick AST scan (no linter is installed in the env):
- `core/protocol.py`: `PerfMfxSlotState` and ~24 constants (`ADDR_PERF_MFX1-3`, `OFFSET_PERF_*`, `TONE_PARAM_TVA_*`, `TONE_PARAM_TVF_*`, `CHORUS/REVERB_PARAM_DATA_START`, ...). Note some may be re-exported on purpose; if so, define `__all__` or import from the true source.
- `ui/bridge.py`: `EffectsState`, `MatrixCtrlState`, `PatchCommonState`, `PerfPartState`, `StepLfoState`, `get_mfx_catalog`.
- `control/engine.py`: `ControlDefinition`, `ScaleMode`. `control/models.py`: `Any`, `Callable`. `control/smooth_scaler.py`: `Optional`. `core/waves.py`: `Dict`. `core/wifi.py`: `field`.
- Scripts: `spectre_probe.py` (`Text`, `SoundMode`), `spectre_control.py` (4 unused names), `spectre_vector.py` (`ProfileManager`, `run_app`), `sampler_test.py` (`os`, `TONE_PARAM_TVA_LEVEL`), `dump_waveforms.py`, `build_wave_catalog.py` (`sys`).
- Function-local `import time as _time` in the bridge (~L5994, L6081) while `time` is already imported at the top.

Fix: add `ruff` and run `ruff check --fix`.

### 3.2 `mfx_catalog.py` is an 11,000-line Python literal — [Med] (data is valuable; only the storage format is the issue)
[mfx_catalog.py](src/spectre/core/mfx_catalog.py) is pretty-printed data (one value per line). The problem is not the data but that it lives as source code. Options:

| Option | Pros | Cons |
|---|---|---|
| **A. Compact JSON asset** (`assets/mfx_catalog.json`), loaded lazily + schema-validated | Same shape the code already uses (`get_mfx_catalog()` returns the nested dicts, QML consumes them whole); text file so git diffs/reviews work; zero new code besides a loader | No ad-hoc querying (not needed today) |
| **B. SQLite** (tables `mfx_algo`, `mfx_param`, `mfx_option`) | Consistent with the existing librarian DB; queryable; typed columns/constraints | Binary file → opaque diffs; data is read whole at startup, so queries add no benefit; needs a generator/migration step and a schema (3 normalized tables for a nested structure); **must not go into `factory.db`**, which is regenerated by `dump_factory_catalog.py` with a different lifecycle — it would need its own file/table set |

**Recommendation:** A (JSON) unless you foresee queries like "all algos with a param of unit X" or per-user editable catalogs. If B is preferred, keep a JSON/CSV source of truth in the repo and *build* the `.db` from it, so the data stays reviewable.

Also, the generator for this data is `scratch/build_accurate_mfx.py`, which is **gitignored** (see 3.4), next to `scripts/scan_mfx_patches.py` / `probe_mfx_ranges.py`. If you want users/contributors to be able to regenerate or fix the catalog, promote one documented generator into `tools/`; otherwise just note in the docs that the data is hand-curated.

### 3.3 Scripts overlap and rot — [Low/Med]
- `scripts/` mixes runtime launchers (`start_spectre.sh`, `eglfs.json`, `release.sh`), CLI tools (`spectre_control.py`, `spectre_probe.py`, `spectre_vector.py`), and one-off dev/dump tools (`dump_waveforms.py` 708 lines, `dump_factory_catalog.py`, `sampler_test.py`, `capture_init_template.py`, ...).
- Each script re-implements `sys.path.insert(...)` bootstrapping (`spectre_probe`, `spectre_control`, `spectre_vector`, `sampler_test`). Fix by making the package installable (`pip install -e .`) and using `[project.scripts]` entry points.
- Split into `scripts/` (user-facing), `tools/` (dev/data generation) and delete or move experiments.

### 3.4 `scratch/` — **Not an action item (decided)**
> `scratch/` is an intentional, gitignored dev sandbox. Nothing to do. Only caveat: make sure nothing in `scripts/`, tests or docs depends on files inside it, since it won't exist on a fresh clone.

### 3.5 Repeated patterns — [Med]
Spot-check candidates to de-duplicate (not exhaustively verified):
- The many near-identical `setXxxParam`/`getXxx` bridge slots (e.g. `setChorusParam` 91 lines) for Chorus/Reverb/MFX1-3. Replace with a table-driven slot (`setEffectParam(block, key, value)`).
- Per-tone/per-part copies of the same dict-building code (e.g. `getattr(p, "dry_send", 127)` blocks around bridge ~L1678).
- QML: ~**199 hard-coded `color: "#xxxxxx"`** literals, despite a `Theme.qml`. Many `width: <number>` values rather than `ScaleMetrics`. Move colors/sizes to the theme.

---

## 4. Packaging, config & repo hygiene

### 4.1 Version numbers disagree — [High]
- `VERSION` file: `0.7.0`
- `src/spectre/__init__.py`: `__version__ = "0.1.0"`
- `updater.py` docstring mentions `v0.2.0` and git tags provide a third source.

Pick one source of truth (git tag or `VERSION`) and read it everywhere.

### 4.2 Missing/incorrect dependencies — [High]
[requirements.txt](requirements.txt) lists `mido`, `python-rtmidi`, `pydantic`, `pytest`, `rich`, but:
- **`PyQt6` is not listed** (README tells users to `pip install PyQt6` separately).
- **`numpy` and `scipy`** are imported by `scripts/sampler_test.py` and `scripts/dump_waveforms.py` but not declared.
- `pytest` is a dev dependency in the runtime file.
- `rich` is only used by CLI scripts; `pydantic` only in `control/models.py`.
- The environment also has **PySide6** installed alongside PyQt6; make sure only one is used (the code uses PyQt6 only, which is GPL — compatible with the GPLv3 license, but worth noting for any future relicensing).
- No version upper bounds/lockfile → a Raspberry Pi install is not reproducible.

Fix: add a `pyproject.toml` with `dependencies`, `optional-dependencies` (`ui`, `cli`, `dev`, `tools`), pinned/locked versions, and entry points.

### 4.3 Runtime assets vs `.gitignore` — ~~[High]~~ **Not an action item (decided)**
> **Decision:** the `.wav` files are hardware dumps and cannot be shipped for copyright reasons, so `*.wav` stays gitignored. What ships is the simplified waveform data (`inta_catalog.json` / `intb_catalog.json`, tracked). The scripts that produce it (`scripts/dump_waveforms.py`, `scripts/build_wave_catalog.py`) **will keep shipping** so users can reproduce and tweak the process.
>
> Remaining small to-dos only: (a) make sure the app never needs the raw `.wav` files at runtime (the `waves.py` loader only reads the catalog JSONs, so this looks fine); (b) document in the README/tool docstrings that the dump script needs a connected Juno-DS and writes the wavs to the gitignored folder, and that `build_wave_catalog.py` needs the Roland param-guide PDF in `Resources/`; (c) move both under `tools/` (see 3.3). Revisit only if the architecture changes to need the raw audio at runtime.

Original note (superseded, kept for context): `.gitignore` contains `*.wav`, but `src/spectre/assets/waveforms/**` (~14 MB of `.wav`) exists locally. Still relevant: `src/spectre/assets/librarian/factory.db` is a tracked binary; document how it is regenerated.
`.gitignore` contains `*.wav`, but `src/spectre/assets/waveforms/**` (~14 MB of `.wav`) is **loaded at runtime** by `core/waves.py` (`ASSETS_DIR`). On a fresh clone, or via the git-based updater, the waveform previews would be missing. Either track them (Git LFS or a release artifact) or provide a documented download/generate step with a clear startup warning. Also `src/spectre/assets/librarian/factory.db` is a tracked binary; document how it is regenerated.

### 4.4 Ignored docs that the project relies on — [Med]
`SUMMARY.md` (23 KB design doc), `ideas.md` and `Resources/` (10 MB Roland PDFs) are gitignored. The design doc is useful and not secret; consider tracking `SUMMARY.md` (moved to `docs/`) and keep Roland PDFs ignored (copyright) with a note on where to obtain them. Check that SUMMARY.md and README don't contradict the current architecture.

### 4.5 `.gitignore` gaps — [Low]
No entries for `.venv/`, `venv/`, `*.egg-info/`, `.ruff_cache/`, `.mypy_cache/`, `dist/`, `build/`, `.idea/`, `.vscode/`.

### 4.6 `pytest.ini` — [Low]
`pythonpath = .` makes imports work only because tests do `from src.spectre...` or similar. Migrate to a `src/` layout with an editable install and drop the path hack.

---

## 5. Tests

- Good: 269 tests, protocol/vector/wifi/updater/librarian are covered.
- Gaps — [Med]:
  - The 494-method bridge has relatively few direct tests (`test_librarian_bridge`, `test_vector_ui`, `test_performance`, `test_routing`). Add contract tests per sub-bridge as part of the split (1.1).
  - No QML tests/lint (`qmllint`, `qmltestrunner`); add `qmllint` to CI.
  - `mfx_catalog` data has no schema validation test (ranges, option counts).
  - No test for a failing/disconnecting MIDI device (see 2.6).
- No CI configuration at all (no `.github/workflows`). Add: `pytest`, `ruff`, `mypy` (at least on `core/` and `control/`), `qmllint`.

---

## 6. Typing, style, logging

- Type hints are partial; `Optional`/`Dict`/`List` (typing) mix with modern syntax. Standardize on Python 3.11+ (`X | None`, `list[...]`) and enable `mypy`/`pyright` incrementally.
- Logging uses f-strings in `logger.*` calls (e.g. bridge ~L225, L239) — switch to lazy `%s` formatting; and check for stray `print()` calls in library code (the scan counted none in `src/` — keep it that way).
- Magic numbers (`64`, `127`, `13`, `50.0`, sleep durations) scattered in bridge/protocol; name them as constants.
- Mixed naming: camelCase QML-facing slots vs snake_case Python is expected, but make sure the boundary is thin and consistently applied (right now the bridge mixes both in the same class and both layers).
- Add `ruff format` (or `black`) for consistent formatting.

---

## 7. Suggested order of work

1. **Quick wins (≈ half a day) — [Phase 1 Completed]**
   - [x] Introduce `pyproject.toml` (deps incl. PyQt6/numpy/scipy, extras, entry points); unify version (4.1, 4.2).
   - [x] Add `ruff` + `.gitignore` additions; run autofix for unused imports & variables (3.1, 4.5).
   - [x] Tag UI tests with `@pytest.mark.ui` for fast sub-5s unit testing (`pytest -m "not ui"`).
   - [ ] Reorganize `scripts/` vs `tools/`; keep `dump_waveforms.py` / `build_wave_catalog.py` shipped and documented (3.3, 4.3).
   - (`scratch/` stays as is — decided, see 3.4.)
2. **Safety (≈ 1–2 days) — [Next: Phase 2]**
   - Audit swallowed exceptions; make hardware-write failures visible (2.1).
   - Wi-Fi password off argv: stdin pipe via `nmcli --ask` (2.4).
   - Thread/MIDI I/O audit and serialization (2.2, 2.3, 2.6).
   - Make `syncPatchFromSynth()` async to avoid blocking GUI thread (2.7).
   - MIDI disconnect & hotplug recovery (2.8).
   - Signal handling (`SIGTERM`/`SIGINT`) to prevent stuck notes on synth teardown (2.9).
   - Updater rollback check (2.5).
3. **Data cleanup (≈ half a day)**
   - Move `mfx_catalog.py` data to a JSON asset (or SQLite, your call — see 3.2) + schema test.
4. **Structural refactor (multi-day, incremental, tests green at each step)**
   - Make private repo/protocol methods public; move flash sequences out of the bridge (1.4).
   - Split `protocol.py` (1.2), then `patch_state.py`/`repository.py` (1.3).
   - Split `SpectreBridge` into sub-bridges (1.1); table-drive repeated effect slots (3.5).
   - Split large QML views and migrate hard-coded colors/sizes to `Theme`/`ScaleMetrics` (3.5, 1.3).
5. **Continuous**
   - CI (pytest, ruff, mypy, qmllint), type hints, new tests per refactor (5, 6).

## 8. Caveats on this review

- Findings come from static scans (AST/grep), file sizes, and a test run — I did **not** read all 17k lines of QML or every bridge method. Items marked "verify"/"confirm" need a closer look before changing.
- I could not run the UI or talk to hardware, so thread-safety and blocking-on-GUI-thread concerns are risks to check, not confirmed bugs.
- The unused-import list is from a simple AST heuristic; names re-exported intentionally may appear as false positives.
