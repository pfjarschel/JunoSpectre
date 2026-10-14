"""Audio tracks: track kind, audio clips, the media browser / USB import and worker status.

The sequencer engine plays audio clips through an AudioPlayer (its AudioSink);
this mixin owns the player, keeps the song's files prepared and exposes
clip editing to QML. Nothing starts until the song has an AUDIO track.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtProperty, pyqtSignal, pyqtSlot

from ...audio import media
from ...audio.client import AudioClient
from ...audio.player import AudioPlayer
from ...sequencer.models import (
    AUDIO_CENTS,
    AUDIO_GAIN_RANGE,
    AUDIO_MODE_SYNC,
    AUDIO_MODES,
    AUDIO_SEMITONES,
    TRACK_KINDS,
    AudioClip,
)
from .base import BridgeBaseMixin

logger = logging.getLogger(__name__)

# Clip names a file assignment may replace (the defaults, not user names)
_DEFAULT_CLIP_PREFIXES = ("Scene ", "Pattern ", "Clip")


class AudioBridgeMixin(BridgeBaseMixin):
    audioChanged = pyqtSignal()
    # From player threads to the GUI thread
    _audioSync = pyqtSignal()
    _audioEnded = pyqtSignal(int)
    # USB import finished: (track, clip, rel path or "" on failure)
    _audioImported = pyqtSignal(int, int, str)

    def _init_audio(self) -> None:
        hw = getattr(self, "_hw_settings", {}) or {}
        client = AudioClient(device=str(hw.get("audio_device", "")),
                             block=int(hw.get("audio_block", 512)),
                             latency=float(hw.get("audio_latency", 0.03)))
        self.audio_player = AudioPlayer(media.audio_dir(hw), client=client,
                                        on_change=self._audioSync.emit, on_ended=self._audioEnded.emit)
        self.audio_player.offset_s = float(hw.get("audio_offset_ms", 0.0)) / 1000.0
        self._audio_importing = ""
        self._audioSync.connect(self._on_audio_sync, Qt.ConnectionType.QueuedConnection)
        self._audioEnded.connect(self._on_audio_ended, Qt.ConnectionType.QueuedConnection)
        self._audioImported.connect(self._on_audio_imported, Qt.ConnectionType.QueuedConnection)
        # Edits that change a stretch/transpose render are applied once they settle
        self._audio_render_timer = QTimer(self)
        self._audio_render_timer.setSingleShot(True)
        self._audio_render_timer.setInterval(600)
        self._audio_render_timer.timeout.connect(self.audio_player.refresh_renders)
        self.bpmChanged.connect(self._on_audio_bpm)
        if hasattr(self, "sequencer"):
            self.sequencer.audio = self.audio_player
            self.audio_player.song_bpm = self.sequencer.bpm
        self._audio_song_changed()

    def _on_audio_bpm(self, bpm: float) -> None:
        self.audio_player.song_bpm = float(bpm)
        self._audio_render_timer.start()
        self.seqTracksChanged.emit()          # clip tempos / stretch amounts shown

    def close_audio(self) -> None:
        if hasattr(self, "audio_player"):
            self.audio_player.close()

    def _on_audio_sync(self) -> None:
        self.audioChanged.emit()
        self.seqTracksChanged.emit()

    def _on_audio_ended(self, track_idx: int) -> None:
        if self.sequencer.audio_ended(track_idx):
            self.seqTracksChanged.emit()

    def _audio_song_changed(self) -> None:
        """A song was loaded (or a track became AUDIO): get its files ready."""
        player = getattr(self, "audio_player", None)
        if player is None or not hasattr(self, "sequencer"):
            return
        audio_tracks = [t for t in self.sequencer.song.tracks if t.is_audio]
        player.song_bpm = self.sequencer.bpm
        player.set_clips([c for t in audio_tracks for c in t.clips if c.audio is not None and c.audio.file])
        if audio_tracks:
            player.ensure_worker()

    # -- QML: status -------------------------------------------------------------

    @pyqtProperty("QVariantMap", notify=audioChanged)
    def audioStatus(self) -> dict:
        p = getattr(self, "audio_player", None)
        if p is None:
            return {}
        return {"ready": p.ready, "device": p.client.device_name, "error": p.client.error,
                "xruns": p.client.xruns, "folder": str(p.folder), "importing": self._audio_importing}

    def _audio_clip_dict(self, clip) -> dict:
        """Audio fields of a clip for seqTracks (empty slot when it has none)."""
        a = clip.audio
        if a is None or not a.file:
            return {"audioFile": "", "audioName": "", "audioMode": a.mode if a else "loop",
                    "audioSync": a.sync if a else True, "audioState": "", "audioSeconds": 0.0,
                    "audioGainDb": a.gain_db if a else 0.0}
        p = self.audio_player
        st = p.clip_state(clip)
        frames = p.base_frames(clip)
        file_frames = p.file_state(a.file)["frames"]
        spec = p.render_spec(clip)
        return {"audioFile": a.file, "audioName": Path(a.file).stem, "audioMode": a.mode, "audioSync": a.sync,
                "audioState": st["state"], "audioError": st["error"],
                "audioSeconds": round(frames / media.SAMPLE_RATE, 3), "audioGainDb": a.gain_db,
                "audioFileFrames": file_frames, "audioStart": a.start,
                "audioEnd": (min(a.end, file_frames) if a.end > 0 else file_frames),
                "audioBars": p.clip_bars(clip), "audioBarsAuto": a.bars == 0,
                "audioBpm": round(p.clip_bpm(clip), 2), "audioStretch": a.stretch,
                "audioTempo": spec[0] if spec else 1.0, "audioSemitones": a.semitones, "audioCents": a.cents}

    # -- QML: track kind -----------------------------------------------------------

    @pyqtSlot(int, str)
    def seqSetTrackKind(self, track_idx: int, kind: str) -> None:
        """NOTES or AUDIO. Clips keep both their steps and their audio; the track stops."""
        tracks = self.sequencer.song.tracks
        if kind not in TRACK_KINDS or not 0 <= track_idx < len(tracks) or tracks[track_idx].kind == kind:
            return
        with self.sequencer.lock:
            track = tracks[track_idx]
            if track.is_audio:
                self.audio_player.stop(track_idx, None)
            track.kind = kind
            track.active_clip_idx = -1
            track.queued_clip_idx = -1
        self._audio_song_changed()
        self.seqTracksChanged.emit()
        self.seqActiveClipChanged.emit()

    # -- QML: media browser ------------------------------------------------------

    @pyqtSlot(result="QVariantList")
    def audioSources(self) -> list:
        """Where files can be picked: the media folder, then each USB stick."""
        out = [{"label": "LIBRARY", "path": "", "usb": False}]
        out += [{"label": p.name.upper(), "path": str(p), "usb": True} for p in media.usb_volumes()]
        return out

    @pyqtSlot(str, str, result="QVariantMap")
    def audioBrowse(self, source: str, sub: str) -> dict:
        """One folder level of a source ("" = the media folder, created on first use)."""
        root = Path(source) if source else self.audio_player.folder
        if not source:
            try:
                root.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass
        sub = sub.strip("/")
        if sub and ".." in Path(sub).parts:
            sub = ""
        listing = media.list_audio(root, sub)
        return {"source": source, "sub": sub, "dirs": listing["dirs"], "files": listing["files"],
                "root": str(root)}

    def _audio_edit_clip(self):
        """(track index, clip) the clip editor works on: the active track's selected clip."""
        t_idx = getattr(self, "_active_seq_track", 0)
        tracks = self.sequencer.song.tracks
        if 0 <= t_idx < len(tracks):
            track = tracks[t_idx]
            c_idx = track.selected_clip_idx
            if 0 <= c_idx < len(track.clips):
                return t_idx, c_idx, track.clips[c_idx]
        return t_idx, -1, None

    @pyqtSlot(str, str)
    def seqSetClipAudioFile(self, source: str, rel: str) -> None:
        """Put a file in the selected clip. From a USB stick it is copied into the
        media folder first (in the background)."""
        t_idx, c_idx, clip = self._audio_edit_clip()
        if clip is None or not rel:
            return
        if not source:
            self._audio_assign(t_idx, c_idx, rel)
            return
        src = Path(source) / rel
        self._audio_importing = src.name
        self.audioChanged.emit()

        def run():
            try:
                dest = media.import_file(src, self.audio_player.folder)
                self._audioImported.emit(t_idx, c_idx, media.relative_name(self.audio_player.folder, dest))
            except OSError as e:
                logger.warning("audio import of %s failed: %s", src, e)
                self._audioImported.emit(t_idx, c_idx, "")

        threading.Thread(target=run, daemon=True, name="AudioImport").start()

    def _on_audio_imported(self, t_idx: int, c_idx: int, rel: str) -> None:
        self._audio_importing = ""
        if rel:
            self._audio_assign(t_idx, c_idx, rel)
        self.audioChanged.emit()

    def _audio_assign(self, t_idx: int, c_idx: int, rel: str) -> None:
        clip = self.sequencer.song.tracks[t_idx].clips[c_idx]
        if clip.audio is None:
            clip.audio = AudioClip()
        clip.audio.file = rel
        clip.audio.start = clip.audio.end = clip.audio.bars = 0
        if clip.name.startswith(_DEFAULT_CLIP_PREFIXES):
            clip.name = Path(rel).stem[:16]
        self.audio_player.forget_missing()
        self._audio_song_changed()
        self.audio_player.ensure_worker()
        self.seqTracksChanged.emit()
        self.seqActiveClipChanged.emit()

    @pyqtSlot()
    def seqClearClipAudio(self) -> None:
        t_idx, c_idx, clip = self._audio_edit_clip()
        if clip is None or clip.audio is None:
            return
        with self.sequencer.lock:
            track = self.sequencer.song.tracks[t_idx]
            if track.active_clip_idx == c_idx and track.is_audio:
                self.audio_player.stop(t_idx, None)
                track.active_clip_idx = -1
            clip.audio.file = ""
        self._audio_song_changed()
        self.seqTracksChanged.emit()
        self.seqActiveClipChanged.emit()

    @pyqtSlot(str, "QVariant")
    def seqSetClipAudio(self, param: str, value) -> None:
        """Edit the selected audio clip: mode (also sets its default sync), sync, gainDb."""
        t_idx, c_idx, clip = self._audio_edit_clip()
        if clip is None:
            return
        if clip.audio is None:
            clip.audio = AudioClip()
        a = clip.audio
        frames = self.audio_player.file_state(a.file)["frames"]
        render = False                         # changes what a stretch/transpose render holds
        if param == "mode" and value in AUDIO_MODES:
            a.mode = str(value)
            a.sync = AUDIO_MODE_SYNC[a.mode]
        elif param == "sync":
            a.sync = bool(value)
        elif param == "gainDb":
            lo, hi = AUDIO_GAIN_RANGE
            a.gain_db = round(max(lo, min(hi, float(value))), 1)
            if self.sequencer.song.tracks[t_idx].active_clip_idx == c_idx:
                self.audio_player.set_gain(t_idx, a.gain_db)
        elif param == "start":
            end = a.end if a.end > 0 else frames
            a.start = max(0, min(int(value), end - 1))
            render = True
        elif param == "end":
            v = max(a.start + 1, int(value))
            a.end = 0 if frames and v >= frames else v
            render = True
        elif param == "bars":
            a.bars = max(0, min(1024, int(value)))
            render = True
        elif param == "stretch":
            a.stretch = bool(value)
            render = True
        elif param == "semitones":
            a.semitones = max(-AUDIO_SEMITONES, min(AUDIO_SEMITONES, int(value)))
            render = True
        elif param == "cents":
            a.cents = max(-AUDIO_CENTS, min(AUDIO_CENTS, int(value)))
            render = True
        else:
            return
        if render:
            self._audio_render_timer.start()
        self.seqTracksChanged.emit()
        self.seqActiveClipChanged.emit()

    @pyqtSlot()
    def seqFitClipEnd(self) -> None:
        """FIT END: the slice ends its bars after the start, at the song tempo."""
        t_idx, c_idx, clip = self._audio_edit_clip()
        if clip is None or clip.audio is None:
            return
        p = self.audio_player
        bars = p.clip_bars(clip) or 1
        clip.audio.bars = bars
        end = clip.audio.start + round(bars * 240.0 / self.sequencer.bpm * media.SAMPLE_RATE)
        self.seqSetClipAudio("end", end)

    @pyqtSlot()
    def seqSetSongBpmFromClip(self) -> None:
        """SET SONG BPM: the song takes the selected clip's tempo."""
        t_idx, c_idx, clip = self._audio_edit_clip()
        if clip is not None and clip.audio is not None:
            bpm = self.audio_player.clip_bpm(clip)
            if bpm > 0:
                self.setBpm(round(bpm, 2))

    # -- QML: waveform, audition, playhead -----------------------------------------

    @pyqtSlot(int, int, int, result="QVariantList")
    def audioPeaks(self, begin: int, end: int, columns: int) -> list:
        """Waveform of the selected clip's file, frames [begin, end): [min0, max0, min1, ...]."""
        t_idx, c_idx, clip = self._audio_edit_clip()
        if clip is None or clip.audio is None:
            return []
        st = self.audio_player.file_state(clip.audio.file)
        if st["state"] != "ready":
            return []
        pk = media.peaks_window(st["key"], begin, end, columns, self.audio_player.cache)
        return [round(float(v), 4) for v in pk.reshape(-1)]

    @pyqtSlot(bool)
    def audioAudition(self, on: bool) -> None:
        """Play the selected clip at once (editor preview), or stop it."""
        t_idx, c_idx, clip = self._audio_edit_clip()
        if clip is not None and clip.audio is not None:
            self.audio_player.audition(clip, on)
        self.audioChanged.emit()

    @pyqtProperty(bool, notify=audioChanged)
    def audioAuditioning(self) -> bool:
        t_idx, c_idx, clip = self._audio_edit_clip()
        return bool(clip is not None and self.audio_player.auditioning == clip.clip_id)

    @pyqtSlot(result=int)
    def audioPlayhead(self) -> int:
        """Frame of the selected clip's file playing now (audition or its track), -1 = none."""
        t_idx, c_idx, clip = self._audio_edit_clip()
        if clip is None or clip.audio is None:
            return -1
        p = self.audio_player
        track = self.sequencer.song.tracks[t_idx]
        slot = "pv" if p.auditioning == clip.clip_id else (
            f"t{t_idx}" if track.is_audio and track.active_clip_idx == c_idx else "")
        pos = p.position(slot) if slot else -1
        if pos < 0:
            return -1
        a = clip.audio
        spec = p.render_spec(clip)
        length = max(1, p.base_frames(clip))
        # Renders start at the slice start and run `tempo` times faster
        offset = (pos * spec[0] if spec else pos - a.start)
        if a.mode == "loop":
            offset %= length
        return int(a.start + min(offset, length))
