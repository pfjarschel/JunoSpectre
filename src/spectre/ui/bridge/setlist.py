"""Setlist bridge mixin: the song repertoire, .spectre playlist files and song changes."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

from PyQt6.QtCore import pyqtProperty, pyqtSignal, pyqtSlot

from ...core.spectre_format import (
    entry_song_path,
    load_playlist,
    load_spectre,
    make_playlist_entry,
    patch_state_to_dict,
    playlist_entry_status,
    refresh_entry_snapshot,
    save_playlist,
)
from .base import BridgeBaseMixin

logger = logging.getLogger(__name__)


class SetlistBridgeMixin(BridgeBaseMixin):
    """Bridge mixin for the Setlist page, the setlist MIDI actions and playlist files."""

    setlistChanged = pyqtSignal()
    songActivated = pyqtSignal(int)

    def _init_setlist(self) -> None:
        """Initialize setlist state."""
        self._setlist_entries: List[Dict[str, Any]] = []
        self._setlist_index: int = -1  # the song sounding now (-1: none activated)
        self._setlist_path: str = ""
        # Link health per entry (by identity): each check reads the song file,
        # so it runs on changes and when the page opens, not on every read.
        self._setlist_status: Dict[int, str] = {}

    def _setlist_changed(self, recheck: bool = False) -> None:
        if recheck:
            self._setlist_status = {}
        self.setlistChanged.emit()

    def _setlist_recheck(self) -> None:
        """Song files may have changed on disk: re-check the link badges."""
        if self._setlist_entries:
            self._setlist_changed(recheck=True)

    # -------------------------------------------------------------------------
    # QML Properties
    # -------------------------------------------------------------------------

    @pyqtProperty("QVariantList", notify=setlistChanged)
    def setlistEntries(self) -> list:
        out = []
        for i, e in enumerate(self._setlist_entries):
            status = self._setlist_status.get(id(e))
            if status is None:
                status = playlist_entry_status(e)
                self._setlist_status[id(e)] = status
            path = entry_song_path(e)
            out.append({
                "index": i,
                "name": str(e.get("name") or f"Song {i+1}"),
                "songPath": path,
                "songFile": Path(path).name if path else "",
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
        """Basename of the setlist file ('' when never saved)."""
        try:
            return Path(str(self._setlist_path or "")).name
        except Exception:
            return ""

    # -------------------------------------------------------------------------
    # QML Setlist File & Entry Operations
    # -------------------------------------------------------------------------

    @pyqtSlot()
    def newSetlist(self) -> None:
        """Clear the setlist (files on disk untouched)."""
        self._setlist_entries = []
        self._setlist_index = -1
        self._setlist_path = ""
        self._setlist_changed(recheck=True)

    @pyqtSlot(str, result=bool)
    def loadSetlist(self, path: str) -> bool:
        """Load a .spectre playlist file. Nothing sounds until a song is activated."""
        try:
            data = load_playlist(path)
        except Exception as e:
            logger.warning(f"loadSetlist failed: {e}")
            return False
        self._setlist_entries = data.get("entries", [])
        self._setlist_index = -1
        self._setlist_path = str(path)
        self._setlist_changed(recheck=True)
        return True

    @pyqtSlot(str, result=bool)
    def saveSetlist(self, path: str) -> bool:
        """Save the setlist to a .spectre playlist file (and index it in the Librarian)."""
        try:
            p = save_playlist(
                path,
                entries=self._setlist_entries,
                index=self._setlist_index,
                name=Path(path).stem,
                patch_state=self.patch_state,
            )
        except Exception as e:
            logger.warning(f"saveSetlist failed: {e}")
            return False
        self._setlist_path = str(p)
        repo = self._librarian()
        if repo is not None:
            try:
                repo.touch_file_row(str(p))
                repo._conn.commit()
                self.librarianChanged.emit()
            except Exception as e:
                logger.debug(f"saveSetlist: index refresh failed: {e}")
        self._setlist_changed()
        return True

    @pyqtSlot(result=bool)
    def saveSetlistAuto(self) -> bool:
        """SAVE: overwrite the loaded file, else create 'Setlist N' in the user library."""
        if str(self._setlist_path or ""):
            return self.saveSetlist(str(self._setlist_path))
        repo = self._librarian()
        base = Path(repo.user_dir) if repo is not None else Path(".")
        n = 1
        while (base / f"Setlist {n}.spectre").exists():
            n += 1
        return self.saveSetlist(str(base / f"Setlist {n}.spectre"))

    @pyqtSlot(str, result=bool)
    def addCurrentToSetlist(self, name: str = "") -> bool:
        """Add the current song to the end of the setlist.

        A song loaded from (or saved to) a file links that file and snapshots
        what the file holds; anything else snapshots the live state.
        """
        try:
            song_name = name.strip() or self._patch_name or f"Song {len(self._setlist_entries) + 1}"
            origin = self._current_ref or {}
            song_path = ""
            if (origin.get("source"), origin.get("kind")) == ("file", "performance"):
                song_path = str(origin.get("path") or "")
            entry = None
            if song_path and Path(song_path).is_file():
                try:
                    entry = refresh_entry_snapshot(make_playlist_entry(song_name, song_path=song_path))
                except Exception as e:
                    logger.info(f"addCurrentToSetlist: song file unreadable, snapshotting live: {e}")
            if entry is None:
                extras: Dict[str, Any] = {"part_snapshots": self._capture_part_snapshots(),
                                          **self._arp_extras()}
                if hasattr(self, "sequencer"):
                    extras["sequencer"] = self.sequencer.song.to_dict()
                entry = make_playlist_entry(song_name, patch_state_to_dict(self.patch_state),
                                            spectre=extras)
        except Exception as e:
            logger.warning(f"addCurrentToSetlist failed: {e}")
            return False
        self._setlist_entries.append(entry)
        if self._setlist_index < 0:
            self._setlist_index = len(self._setlist_entries) - 1  # it is what sounds now
        self._setlist_changed()
        return True

    @pyqtSlot(int, result=bool)
    def refreshSetlistEntry(self, index: int) -> bool:
        """Re-read the linked song file into the entry snapshot (UPDATED badge)."""
        if not 0 <= int(index) < len(self._setlist_entries):
            return False
        entry = self._setlist_entries[int(index)]
        try:
            refresh_entry_snapshot(entry)
        except Exception as e:
            logger.warning(f"refreshSetlistEntry failed: {e}")
            return False
        self._setlist_status.pop(id(entry), None)
        self._setlist_changed()
        return True

    @pyqtSlot(int, result=bool)
    def removeSetlistEntry(self, index: int) -> bool:
        if not 0 <= int(index) < len(self._setlist_entries):
            return False
        idx = int(index)
        entry = self._setlist_entries.pop(idx)
        self._setlist_status.pop(id(entry), None)
        if self._setlist_index == idx:
            self._setlist_index = -1  # the sounding song is gone from the list
        elif self._setlist_index > idx:
            self._setlist_index -= 1
        self._setlist_changed()
        return True

    @pyqtSlot(int, int, result=bool)
    def reorderSetlistEntry(self, from_idx: int, to_idx: int) -> bool:
        """Move a song; the sounding-song highlight follows it."""
        n = len(self._setlist_entries)
        if not (0 <= from_idx < n and 0 <= to_idx < n and from_idx != to_idx):
            return False
        current = self._setlist_entries[self._setlist_index] if 0 <= self._setlist_index < n else None
        item = self._setlist_entries.pop(from_idx)
        self._setlist_entries.insert(to_idx, item)
        if current is not None:
            # By identity: two entries of the same song compare equal
            self._setlist_index = next(i for i, e in enumerate(self._setlist_entries) if e is current)
        self._setlist_changed()
        return True

    # -------------------------------------------------------------------------
    # Song changes
    # -------------------------------------------------------------------------

    @pyqtSlot(int, result=bool)
    def activateSong(self, index: int) -> bool:
        """Make a setlist song sound: its linked file when readable, else the snapshot."""
        if not 0 <= int(index) < len(self._setlist_entries):
            return False
        idx = int(index)
        entry = self._setlist_entries[idx]
        name = str(entry.get("name") or "Song")

        song_path = entry_song_path(entry)
        if song_path and Path(song_path).is_file():
            try:
                loaded = load_spectre(song_path)
                if loaded.get("kind") != "performance":
                    raise ValueError(f"not a song (kind={loaded.get('kind')!r})")
                ok = self._load_song(patch_state_to_dict(loaded["patch_state"]), name,
                                     loaded.get("spectre"), path=song_path)
            except Exception as e:
                logger.info(f"activateSong: linked file unreadable, using the snapshot: {e}")
                ok = None
        else:
            ok = None
        if ok is None:
            if not isinstance(entry.get("cached"), dict):
                logger.warning("activateSong: no readable song file or snapshot.")
                return False
            ok = self._load_song(entry["cached"], name, entry,
                                 fallback_bpm=float(entry.get("bpm") or 120.0))
        if not ok:
            return False

        self._setlist_index = idx
        self._setlist_changed()
        self.songActivated.emit(idx)
        return True

    @pyqtSlot(result=bool)
    def nextSong(self) -> bool:
        """Next song (stops at the last one: no surprise jump back to the opener)."""
        if self._setlist_index + 1 < len(self._setlist_entries):
            return self.activateSong(self._setlist_index + 1)
        return False

    @pyqtSlot(result=bool)
    def prevSong(self) -> bool:
        if self._setlist_index > 0:
            return self.activateSong(self._setlist_index - 1)
        return False
