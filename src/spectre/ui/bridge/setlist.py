"""Dedicated Setlist bridge mixin managing repertoire, .spectre playlist files and safe transitions."""

from __future__ import annotations

import copy
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import pyqtProperty, pyqtSignal, pyqtSlot

from ...core.patch_state import PatchState
from ...core.spectre_format import (
    load_playlist,
    load_song,
    patch_state_from_dict,
    patch_state_to_dict,
    playlist_entry_status,
    refresh_entry_snapshot,
    save_playlist,
    save_song,
    snapshot_hash_of,
)
from .base import BridgeBaseMixin

logger = logging.getLogger(__name__)


class SetlistBridgeMixin(BridgeBaseMixin):
    """Bridge mixin for dedicated Setlist repertoire management and safe transitions."""

    setlistChanged = pyqtSignal()
    songActivated = pyqtSignal(int)

    def _init_setlist(self) -> None:
        """Initialize setlist state."""
        self._setlist_entries: List[Dict[str, Any]] = []
        self._setlist_index: int = -1
        self._setlist_path: str = ""
        self._setlist_title: str = "Untitled Setlist"

    # -------------------------------------------------------------------------
    # QML Properties
    # -------------------------------------------------------------------------

    @pyqtProperty("QVariantList", notify=setlistChanged)
    def setlistEntries(self) -> list:
        out = []
        for i, e in enumerate(self._setlist_entries):
            status = playlist_entry_status(e)
            out.append({
                "index": i,
                "name": str(e.get("name") or f"Song {i+1}"),
                "songPath": str(e.get("song_path") or e.get("perf_path") or ""),
                "status": status,
                "bpm": float(e.get("bpm") or 120.0),
                "isCurrent": (i == self._setlist_index),
                "hasSnapshot": (e.get("cached") is not None),
            })
        return out

    @pyqtProperty(int, notify=setlistChanged)
    def setlistIndex(self) -> int:
        return self._setlist_index

    @pyqtProperty(int, notify=setlistChanged)
    def setlistCount(self) -> int:
        return len(self._setlist_entries)

    @pyqtProperty(str, notify=setlistChanged)
    def setlistPath(self) -> str:
        try:
            return Path(str(self._setlist_path or "")).name
        except Exception:
            return ""

    @pyqtProperty(str, notify=setlistChanged)
    def setlistTitle(self) -> str:
        return self._setlist_title

    @pyqtProperty(str, notify=setlistChanged)
    def setlistCurrentSongName(self) -> str:
        if 0 <= self._setlist_index < len(self._setlist_entries):
            return str(self._setlist_entries[self._setlist_index].get("name") or "")
        return ""

    # -------------------------------------------------------------------------
    # QML Setlist File & Entry Operations
    # -------------------------------------------------------------------------

    @pyqtSlot()
    def newSetlist(self) -> None:
        self._setlist_entries.clear()
        self._setlist_index = -1
        self._setlist_path = ""
        self._setlist_title = "New Setlist"
        self.setlistChanged.emit()

    @pyqtSlot(str, result=bool)
    def loadSetlist(self, path: str) -> bool:
        """Load a .spectre playlist file."""
        try:
            data = load_playlist(path)
            self._setlist_entries = data.get("entries", [])
            self._setlist_index = data.get("index", -1)
            self._setlist_path = str(path)
            self._setlist_title = data.get("meta", {}).get("name") or Path(path).stem
            self.setlistChanged.emit()
            return True
        except Exception as e:
            logger.warning(f"loadSetlist failed: {e}")
            return False

    @pyqtSlot(str, result=bool)
    def saveSetlist(self, path: str) -> bool:
        """Save the setlist to a .spectre playlist file."""
        try:
            p = save_playlist(
                path,
                entries=self._setlist_entries,
                index=self._setlist_index,
                name=Path(path).stem,
                patch_state=self.patch_state,
            )
            self._setlist_path = str(p)
            self._setlist_title = Path(p).stem
            self.setlistChanged.emit()
            return True
        except Exception as e:
            logger.warning(f"saveSetlist failed: {e}")
            return False

    @pyqtSlot(str, result=bool)
    def addCurrentToSetlist(self, name: str = "") -> bool:
        """Snapshot current performance and sequencer state to the end of the setlist."""
        try:
            song_name = name.strip() or self._patch_name or f"Song {len(self._setlist_entries) + 1}"
            cached_hw = patch_state_to_dict(self.patch_state)
            seq_dict = self.sequencer.song.to_dict() if hasattr(self, "sequencer") else {}

            entry = {
                "name": song_name[:48],
                "song_path": "",
                "snapshot_hash": snapshot_hash_of(cached_hw),
                "cached": cached_hw,
                "sequencer": seq_dict,
                "bpm": self.sequencer.bpm if hasattr(self, "sequencer") else 120.0,
                "macros": [m.value for m in getattr(self.patch_state, "macros", [])],
            }
            self._setlist_entries.append(entry)
            if self._setlist_index < 0:
                self._setlist_index = 0
            self.setlistChanged.emit()
            return True
        except Exception as e:
            logger.warning(f"addCurrentToSetlist failed: {e}")
            return False

    @pyqtSlot(int, result=bool)
    def removeSetlistEntry(self, index: int) -> bool:
        if not 0 <= int(index) < len(self._setlist_entries):
            return False
        idx = int(index)
        del self._setlist_entries[idx]
        if self._setlist_index == idx:
            self._setlist_index = min(idx, len(self._setlist_entries) - 1)
        elif self._setlist_index > idx:
            self._setlist_index -= 1
        self.setlistChanged.emit()
        return True

    @pyqtSlot(int, int, result=bool)
    def reorderSetlistEntry(self, from_idx: int, to_idx: int) -> bool:
        n = len(self._setlist_entries)
        if not (0 <= from_idx < n and 0 <= to_idx < n and from_idx != to_idx):
            return False
        active_entry = self._setlist_entries[self._setlist_index] if 0 <= self._setlist_index < n else None
        item = self._setlist_entries.pop(from_idx)
        self._setlist_entries.insert(to_idx, item)
        if active_entry and active_entry in self._setlist_entries:
            self._setlist_index = self._setlist_entries.index(active_entry)
        self.setlistChanged.emit()
        return True

    # -------------------------------------------------------------------------
    # Safe Transition Protocol
    # -------------------------------------------------------------------------

    @pyqtSlot(int, result=bool)
    def activateSong(self, index: int) -> bool:
        """Execute the Safe Transition Protocol to load and stage a song."""
        if not 0 <= int(index) < len(self._setlist_entries):
            return False

        idx = int(index)
        entry = self._setlist_entries[idx]

        # 1. Stop sequencer playback immediately
        if hasattr(self, "sequencer"):
            self.sequencer.stop()

        # 2. Emit MIDI Panic down channels 1-16: CC 123 (All Notes Off) + CC 121 (Reset Controllers)
        juno_mgr = getattr(self.engine, "juno", None)
        midi_mgr = getattr(juno_mgr, "midi", None) if juno_mgr else None
        if midi_mgr:
            try:
                midi_mgr.send_all_notes_off(include_reset=True)
            except Exception as e:
                logger.debug(f"Panic emission failed: {e}")

        # 3. Load song state: prioritize linked file, fall back to embedded snapshot
        song_path = str(entry.get("song_path") or entry.get("perf_path") or "")
        loaded_song: Optional[Dict[str, Any]] = None

        if song_path and Path(song_path).is_file():
            try:
                loaded_song = load_song(song_path)
            except Exception as e:
                logger.info(f"activateSong: linked file unreadable, falling back to snapshot: {e}")

        if loaded_song is not None:
            new_patch_state = loaded_song["patch_state"]
            new_seq_song = loaded_song.get("sequencer_song")
        elif entry.get("cached") is not None:
            try:
                new_patch_state = patch_state_from_dict(entry["cached"])
                from ...sequencer.models import SequencerSong
                seq_raw = entry.get("sequencer")
                new_seq_song = SequencerSong.from_dict(seq_raw) if seq_raw else None
            except Exception as e:
                logger.warning(f"activateSong: corrupt cached snapshot: {e}")
                return False
        else:
            logger.warning("activateSong: no valid song file or cached snapshot.")
            return False

        # 4. Hydrate patch state & push Roland Performance SysEx
        self.patch_state = new_patch_state
        self.patch_state.sound_mode = "PERFORM"
        self._sound_mode = "PERFORM"
        self._patch_name = str(entry.get("name") or "Song")

        juno = self.juno
        if juno is not None:
            try:
                from ...core.protocol import SoundMode
                juno.set_sound_mode(SoundMode.PERFORM)
                for p in self.patch_state.perf_parts:
                    juno.set_perf_part_patch(p.part_index, p.patch_msb, p.patch_lsb, p.patch_pc)
                    juno.set_perf_part_level(p.part_index, p.volume)
                    juno.set_perf_part_pan(p.part_index, p.pan)
                    juno.set_perf_part_mute(p.part_index, p.muted)
                    juno.set_perf_zone(
                        p.part_index,
                        p.key_low, p.key_high, p.zone_switch, p.zone_octave,
                    )
            except Exception as e:
                logger.debug(f"activateSong: hardware SysEx push error: {e}")

        # 5. Hydrate 5-track Sequencer State & reset playheads
        if hasattr(self, "sequencer"):
            if new_seq_song is not None:
                self.sequencer.song = new_seq_song
                self._apply_tempo(new_seq_song.bpm)
            else:
                self._apply_tempo(float(entry.get("bpm") or 120.0))
            self.sequencer.stop()

        # 6. Apply macro values
        macro_vals = entry.get("macros", [])
        if isinstance(macro_vals, list) and hasattr(self.patch_state, "macros"):
            for i, val in enumerate(macro_vals):
                if i < len(self.patch_state.macros):
                    self.patch_state.macros[i].value = float(val)

        self._setlist_index = idx
        self.setlistChanged.emit()
        self.songActivated.emit(idx)
        return True

    @pyqtSlot(result=bool)
    def nextSong(self) -> bool:
        if self._setlist_index + 1 < len(self._setlist_entries):
            return self.activateSong(self._setlist_index + 1)
        return False

    @pyqtSlot(result=bool)
    def prevSong(self) -> bool:
        if self._setlist_index > 0:
            return self.activateSong(self._setlist_index - 1)
        return False
