"""Unified SpectreBridge facade uniting domain sub-bridges for QML integration."""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, QTimer

from ...core.patch_state import PatchState
from ...core.updater import GitUpdater, UpdaterError
from ...core.waves import WaveCatalogManager
from ...core.wifi import WifiManager, WifiStatus
from ...vector.engine import VectorEngine
from .librarian import LibrarianBridgeMixin
from .patch import PatchBridgeMixin
from .performance import PerformanceBridgeMixin
from .system import SystemBridgeMixin
from .vector import VectorBridgeMixin

logger = logging.getLogger(__name__)


class SpectreBridge(
    SystemBridgeMixin,
    VectorBridgeMixin,
    PerformanceBridgeMixin,
    LibrarianBridgeMixin,
    PatchBridgeMixin,
    QObject,
):
    """Unified bridge exposing workstation engine, patch, performance and system state to QML."""

    def __init__(self, engine: VectorEngine, parent: Optional[QObject] = None):

        super().__init__(parent)
        self.engine = engine
        self._sync_busy: bool = False

        # Waveform catalog & active tone waveforms (Bank, WaveNum)
        self._wave_catalog = WaveCatalogManager.get_instance()

        # In-memory synth state
        self.patch_state: PatchState = PatchState()
        self._selected_tone: int = 1
        self._linked_mode: bool = False

        self._tone_waves: list[tuple[str, int]] = [
            (t.wave_bank_l, t.wave_num_l) for t in self.patch_state.tones
        ]
        self._cached_tone_wave_data: list[dict] = [
            self._wave_catalog.get_wave(b, n) for b, n in self._tone_waves
        ]

        # Cached properties
        self._patch_name: str = self.patch_state.common.name
        self._sound_mode: str = self.patch_state.sound_mode
        self._last_tick_time: float = time.perf_counter()

        # Librarian origin tracking: where the current temp sound came from.
        # None = edited/unknown (e.g. after INIT). Shape:
        # {source, kind, msb, lsb, pc} for slots, or {source: "file", path}
        # for Pi files. Drives the save dialog defaults.
        self._current_ref: Optional[dict] = None
        # Playlist / live setlist: ordered song entries (see spectre_format
        # make_playlist_entry). Pure data; persisted as kind="playlist" files.
        self._playlist: list = []
        self._playlist_index: int = -1
        self._playlist_path: str = ""
        # Librarian pick mode: 0 = normal audition, N = picking a patch for part N.
        self._pick_target: int = 0
        # Destination view proposed after Librarian closes (set by auditions,
        # consumed by toggleLibrarian; Cancel clears it and goes back).
        self._pending_view: str = ""
        # Sound snapshot taken on Librarian entry; Cancel restores it.
        self._librarian_entry_snapshot: dict | None = None
        # Performance part file links: embedded snapshots from the last loaded
        # performance file (part index str -> patch_state dict), link health,
        # and background SysEx push progress (-1.0 = idle).
        self._part_snapshots: dict = {}
        self._part_file_status: list = [""] * 16
        # Deep FX cache: part index -> read_part_fx() dict for PARTn origins.
        # Lets MFX Studio / Master FX display a non-active part's patch FX
        # without blocking QML getters on hardware reads.
        self._part_fx_cache: dict = {}
        self._perf_push_progress: float = -1.0
        self._editing_perf_mfx: int = 1
        self._push_lock = threading.Lock()
        # Set by app.py (non-fatal when absent, e.g. unit tests).
        self._librarian_repo = None
        self._librarian_model = None
        self._library_error: str = ""

        # Workstation Shell State
        self._active_view: str = "JUNO PCM"
        self._view_before_librarian: str = "JUNO PCM"
        self._brightness: int = 85
        try:
            from ...core.backlight import BacklightController

            self._backlight = BacklightController()
        except Exception as e:
            logger.debug(f"Backlight controller unavailable: {e}")
            self._backlight = None

        # Appliance git-release self updater
        self._updater = GitUpdater(Path(__file__).resolve().parents[3])
        self._updater_busy: bool = False
        self._updater_log: str = "IDLE • RELEASE CHANNEL: GIT TAGS"
        self._latest_version: str = ""
        self._update_available: bool = False
        self._update_applied: bool = False
        try:
            self._version: str = self._updater.version
        except UpdaterError as e:
            self._version = "DEV"
            logger.warning(f"Updater unavailable: {e}")

        # Wi-Fi manager (NetworkManager / nmcli; graceful offline on dev PCs)
        self._wifi = WifiManager()
        self._wifi_status: WifiStatus = WifiStatus()
        self._wifi_networks: list[dict] = []
        self._wifi_busy: bool = False
        self._wifi_error: str = ""
        self._wifi_last_scan: str = "NEVER"
        self._wifi_last_status_poll: float = 0.0

        # Engine state tracking for dirty checks
        self._last_x: float = self.engine.x
        self._last_y: float = self.engine.y
        self._last_w: float = self.engine.w
        self._last_tone_levels: tuple[int, int, int, int] = self.engine.tone_levels
        self._last_transport: str = self.engine.motion.state.value

        # Subscribe to engine state updates
        self.engine.subscribe(self._on_engine_state_changed)

        # 60 FPS animation/transport timer
        self._timer = QTimer(self)
        self._timer.setInterval(16)  # ~60 Hz
        self._timer.timeout.connect(self._on_timer_tick)
        self._timer.start()

        # Hardware telemetry (System page only, ~1.5 s cadence)
        from ...core.telemetry import SystemTelemetry

        self._telemetry: SystemTelemetry = SystemTelemetry()
        self._telemetry_prev_cpu = None
        self._telemetry_timer = QTimer(self)
        self._telemetry_timer.setInterval(1500)
        self._telemetry_timer.timeout.connect(self._poll_telemetry)

    @property
    def juno(self):
        """Direct, typed accessor for the connected JunoClient protocol instance."""
        engine = getattr(self, "engine", None)
        return getattr(engine, "juno", None) if engine is not None else None
