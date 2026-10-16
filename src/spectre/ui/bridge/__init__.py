"""Unified SpectreBridge facade uniting domain sub-bridges for QML integration."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QObject

from ...core.patch_state import PatchState
from ...core.protocol import JunoClient
from ...vector.engine import VectorEngine
from .arpeggio import ArpBridgeMixin
from .audio import AudioBridgeMixin
from .automation import AutomationBridgeMixin
from .controllers import ControllersBridgeMixin
from .follow import FollowBridgeMixin
from .hardware import HardwareBridgeMixin
from .jobs import JobsBridgeMixin
from .librarian import LibrarianBridgeMixin
from .macros import MacroBridgeMixin
from .patch import PatchBridgeMixin
from .performance import PerformanceBridgeMixin
from .sequencer import SequencerBridgeMixin
from .setlist import SetlistBridgeMixin
from .sync import SyncBridgeMixin
from .system import SystemBridgeMixin
from .tmt import TmtBridgeMixin
from .vector import VectorBridgeMixin
from .view import ViewBridgeMixin


class SpectreBridge(
    SequencerBridgeMixin,
    AudioBridgeMixin,
    AutomationBridgeMixin,
    SetlistBridgeMixin,
    SystemBridgeMixin,
    SyncBridgeMixin,
    ViewBridgeMixin,
    VectorBridgeMixin,
    MacroBridgeMixin,
    PerformanceBridgeMixin,
    LibrarianBridgeMixin,
    PatchBridgeMixin,
    JobsBridgeMixin,
    HardwareBridgeMixin,
    ControllersBridgeMixin,
    ArpBridgeMixin,
    TmtBridgeMixin,
    FollowBridgeMixin,
    QObject,
):
    """Unified bridge exposing the synth, patch, performance, feature engines and system state to QML."""

    def __init__(self, juno: Optional[JunoClient] = None, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.vector = VectorEngine()
        self.juno = juno
        self.patch_state: PatchState = PatchState()  # the in-memory synth state
        # Each mixin sets up its own state
        self._init_jobs()
        self._init_patch()
        self._init_sequencer()
        self._init_setlist()
        self._init_librarian()
        self._init_performance()
        self._init_view()
        self._init_system()
        self._init_macros()
        self._init_hardware()
        self._init_controllers()
        self._init_automation()
        self._init_arp()
        self._init_tmt()
        self._init_follow()
        self._init_audio()
        self._init_vector()
