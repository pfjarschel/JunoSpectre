"""Audio clips: media folder + cache conversion, the worker's mixer and the client/worker pipe."""

import threading
import time

import numpy as np
import pytest

from src.spectre.audio import media
from src.spectre.audio.client import AudioClient
from src.spectre.audio.worker import FADE_IN, FADE_OUT, Mixer

RATE = media.SAMPLE_RATE


def _ramp(frames: int) -> np.ndarray:
    """Stereo source whose sample value tells its frame index (L = R)."""
    x = (np.arange(frames, dtype=np.float32) + 1) / 1e6
    return np.stack([x, x], axis=1)


def _mixer_with(frames: int = 10000) -> Mixer:
    m = Mixer()
    m.sources["a"] = _ramp(frames)
    m.sources["b"] = np.full((frames, 2), 0.5, dtype=np.float32)
    return m


# -- media ---------------------------------------------------------------------

def test_convert_resamples_to_44k_stereo(tmp_path):
    sf = pytest.importorskip("soundfile")
    src = tmp_path / "tone.wav"
    t = np.arange(48000) / 48000
    sf.write(src, (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32), 48000)  # 1 s mono 48k
    key = media.cache_key(src)
    info = media.convert(src, key, tmp_path / "cache")
    assert info["frames"] == RATE and info["source_rate"] == 48000 and info["source_channels"] == 1
    data = np.load(media.cache_paths(key, tmp_path / "cache")["audio"], mmap_mode="r")
    assert data.shape == (RATE, 2) and data.dtype == np.float32
    assert np.allclose(data[:, 0], data[:, 1]) and 0.45 < np.abs(data).max() < 0.55
    pk = np.load(media.cache_paths(key, tmp_path / "cache")["peaks"])
    assert pk.shape == (media.PEAK_COLUMNS, 2) and pk[:, 0].min() < -0.4 and pk[:, 1].max() > 0.4
    assert media.cache_info(key, tmp_path / "cache")["frames"] == RATE
    # Another render of the same file is another entry; an edited file too
    assert media.cache_key(src, "x1.05") != key
    time.sleep(0.01)
    src.write_bytes(src.read_bytes())
    assert media.cache_key(src) != key


def test_convert_runs_in_its_own_process(tmp_path):
    sf = pytest.importorskip("soundfile")
    src = tmp_path / "s.flac"
    sf.write(src, np.zeros((22050, 2), dtype=np.float32), 22050)
    proc = media.convert_in_subprocess(src, "k1", tmp_path / "cache")
    assert proc.wait(60) == 0, proc.stderr.read()
    assert media.cache_info("k1", tmp_path / "cache")["frames"] == RATE
    bad = media.convert_in_subprocess(tmp_path / "missing.wav", "k2", tmp_path / "cache")
    assert bad.wait(60) == 1 and media.cache_info("k2", tmp_path / "cache") is None


def test_media_folder_names_and_import(tmp_path):
    folder = tmp_path / "SpectreAudio"
    (folder / "Song A").mkdir(parents=True)
    (folder / "Song A" / "drums.wav").write_bytes(b"x")
    (folder / "notes.txt").write_bytes(b"x")
    (folder / ".hidden.wav").write_bytes(b"x")
    assert media.list_audio(folder) == {"dirs": ["Song A"], "files": []}
    assert media.list_audio(folder, "Song A") == {"dirs": [], "files": ["drums.wav"]}
    assert media.relative_name(folder, folder / "Song A" / "drums.wav") == "Song A/drums.wav"
    assert media.resolve(folder, "Song A/drums.wav") == (folder / "Song A" / "drums.wav").resolve()
    assert media.resolve(folder, "Song A/gone.wav") is None
    assert media.resolve(folder, "../outside.wav") is None
    stick = tmp_path / "stick"
    stick.mkdir()
    (stick / "drums.wav").write_bytes(b"y")
    assert media.import_file(stick / "drums.wav", folder, "Song A").name == "drums (2).wav"
    assert media.audio_dir({"audio_dir": str(tmp_path / "x")}) == tmp_path / "x"
    assert media.audio_dir({}) == media.DEFAULT_AUDIO_DIR


# -- mixer ---------------------------------------------------------------------

def test_voice_starts_on_its_exact_frame():
    m = _mixer_with()
    t0 = 100.0
    m.submit({"cmd": "play", "slot": "t1", "key": "b", "at": t0 + 300 / RATE})
    out = m.render(512, t0)
    assert not out[:300].any()
    assert out[300, 0] == pytest.approx(0.5 / FADE_IN)        # fade-in starts
    assert out[300 + FADE_IN:, 0] == pytest.approx(0.5)
    assert m.events.popleft() == {"ev": "started", "slot": "t1", "id": 0}


def test_late_voice_skips_ahead_to_stay_in_time():
    m = _mixer_with()
    t0 = 100.0
    m.submit({"cmd": "play", "slot": "t1", "key": "a", "at": t0 - 1000 / RATE})
    out = m.render(256, t0)
    # Frame 0 of this block plays source frame 1000 (fade-in aside)
    assert out[FADE_IN, 0] == pytest.approx((1000 + FADE_IN + 1) / 1e6)


def test_loop_region_wraps_and_one_shot_ends():
    m = _mixer_with()
    m.submit({"cmd": "play", "slot": "L", "key": "a", "at": None, "begin": 100, "end": 200, "loop": True})
    out = m.render(512, 0.0)
    assert out[150, 0] == pytest.approx((100 + 150 - 100 + 1) / 1e6)   # second pass: frame 150
    m.submit({"cmd": "play", "slot": "S", "key": "b", "at": None, "begin": 0, "end": 300})
    out = m.render(512, 512 / RATE)
    assert m.positions() == {"L": 100 + (1024 % 100)}
    assert {"ev": "ended", "slot": "S", "id": 0} in list(m.events)
    assert out[400:, 0].max() < 0.01                              # only the loop is left


def test_new_clip_replaces_the_slot_on_its_start_frame():
    m = _mixer_with(100000)
    m.submit({"cmd": "play", "slot": "t1", "key": "b", "at": None, "loop": True})
    m.render(512, 0.0)
    t0 = 512 / RATE
    m.submit({"cmd": "play", "slot": "t1", "key": "a", "at": t0 + 100 / RATE})
    out = m.render(512, t0)
    assert out[99, 0] == pytest.approx(0.5)                      # old clip until the switch
    assert out[100 + FADE_OUT + FADE_IN, 0] < 0.01                # then only the ramp source
    assert len(m.voices) == 1 and m.voices[0].source is m.sources["a"]


def test_stop_fades_out_and_ends_the_voice():
    m = _mixer_with(100000)
    m.submit({"cmd": "play", "slot": "t1", "key": "b", "at": None, "loop": True})
    m.render(512, 0.0)
    t0 = 512 / RATE
    m.submit({"cmd": "stop", "slot": "t1", "at": t0 + 50 / RATE})
    out = m.render(512, t0)
    assert out[49, 0] == pytest.approx(0.5)
    assert 0.0 < out[50 + FADE_OUT // 2, 0] < 0.5
    assert not out[50 + FADE_OUT:].any()
    assert m.voices == []


def test_retarget_keeps_the_place_since_the_slice_start():
    m = _mixer_with(100000)
    m.submit({"cmd": "play", "slot": "t1", "key": "a", "at": None, "begin": 1000, "end": 5000, "loop": True,
              "id": 7})
    m.render(512, 0.0)                                       # 512 frames past the start
    # Only the end moved: the voice carries on in place, no crossfade
    m.submit({"cmd": "retarget", "slot": "t1", "key": "a", "begin": 1000, "end": 1600})
    out = m.render(128, 512 / RATE)
    assert len(m.voices) == 1 and m.voices[0].pos == 1000 + (512 + 128) % 600
    assert out[0, 0] == pytest.approx((1000 + 512 + 1) / 1e6)
    # A new start: crossfade to the same distance past it
    m.submit({"cmd": "retarget", "slot": "t1", "key": "a", "begin": 3000, "end": 9000})
    out = m.render(512, 640 / RATE)
    new = [v for v in m.voices if v.vid == 7]
    assert len(new) == 1 and out[FADE_OUT + 10, 0] == pytest.approx((3000 + 40 + FADE_OUT + 10 + 1) / 1e6)
    assert len(m.voices) == 1                                # the old one faded out silently
    assert not [e for e in m.events if e["ev"] == "ended"]


def test_retarget_past_a_one_shot_end_ends_it():
    m = _mixer_with(100000)
    m.submit({"cmd": "play", "slot": "t1", "key": "b", "at": None, "begin": 0, "end": 5000, "id": 3})
    m.render(1024, 0.0)
    m.submit({"cmd": "retarget", "slot": "t1", "key": "b", "begin": 0, "end": 800})
    out = m.render(512, 1024 / RATE)
    assert not out[FADE_OUT:].any() and m.voices == []
    assert {"ev": "ended", "slot": "t1", "id": 3} in list(m.events)


def test_newer_launch_cancels_a_waiting_voice():
    m = _mixer_with()
    m.submit({"cmd": "play", "slot": "t1", "key": "a", "at": 10.0, "id": 1})
    m.submit({"cmd": "play", "slot": "t1", "key": "b", "at": 10.0, "id": 2})
    m.render(512, 10.0)
    assert [v.vid for v in m.voices] == [2]
    assert list(m.events) == [{"ev": "started", "slot": "t1", "id": 2}]


def test_stop_before_start_drops_the_waiting_voice():
    m = _mixer_with()
    m.submit({"cmd": "play", "slot": "t1", "key": "b", "at": 10.0})
    m.submit({"cmd": "stop", "slot": "t1", "at": None})
    assert not m.render(512, 9.99).any() and m.voices == []


def test_gain_ramps_and_master():
    m = _mixer_with()
    m.submit({"cmd": "play", "slot": "t1", "key": "b", "at": None, "loop": True, "gain": 1.0})
    m.render(512, 0.0)
    m.submit({"cmd": "gain", "slot": "t1", "gain": 0.0})
    out = m.render(512, 1.0)
    assert out[0, 0] == pytest.approx(0.5, abs=0.01) and out[-1, 0] == pytest.approx(0.0, abs=0.01)
    m.submit({"cmd": "gain", "slot": "t1", "gain": 1.0})
    m.submit({"cmd": "master", "gain": 0.5})
    m.render(512, 2.0)
    assert m.render(512, 3.0)[0, 0] == pytest.approx(0.25)


def test_unknown_source_reports_an_error():
    m = _mixer_with()
    m.submit({"cmd": "play", "slot": "t1", "key": "nope"})
    m.render(64, 0.0)
    assert m.events.popleft()["ev"] == "error"


# -- client <-> worker process -------------------------------------------------

def test_client_drives_a_worker_process(tmp_path):
    path = tmp_path / "b.npy"
    np.save(path, np.full((4410, 2), 0.25, dtype=np.float32))     # 0.1 s
    events = []
    got = threading.Event()

    def on_event(ev):
        events.append(ev)
        if ev.get("ev") == "ended":
            got.set()

    client = AudioClient(null=True, on_event=on_event)
    try:
        assert client.start(10.0), client.error
        assert client.device_name == "null"
        client.load("b", path)
        client.play("t3", "b", at=time.perf_counter() + 0.05)
        assert got.wait(5.0)
        kinds = [e["ev"] for e in events]
        assert kinds.index("started") < kinds.index("ended")
        deadline = time.time() + 2
        while not client.clock and time.time() < deadline:
            time.sleep(0.05)
        assert client.clock and client.clock[-1][0] > 0
    finally:
        client.close()
    assert not client.running


# -- engine scheduling (fake sink) ---------------------------------------------

from src.spectre.audio.player import AudioPlayer  # noqa: E402
from src.spectre.sequencer.engine import AUDIO_LOOKAHEAD_TICKS, SequencerEngine  # noqa: E402
from src.spectre.sequencer.models import AudioClip  # noqa: E402


class FakeSink:
    def __init__(self, frames=RATE * 2):
        self.calls = []
        self.frames = frames

    def clip_frames(self, clip):
        return self.frames

    def start(self, t, clip, at, loop):
        self.calls.append(("start", t, clip.name, at, loop))

    def stop(self, t, at):
        self.calls.append(("stop", t, at))

    def stop_all(self):
        self.calls.append(("stop_all",))


def _audio_engine(mode="loop", sync=True, bars=0):
    eng = SequencerEngine()
    eng._dispatch_ui = lambda force=False: None
    eng.audio = FakeSink()
    track = eng.song.tracks[2]
    track.kind = "audio"
    track.active_clip_idx = -1
    for i, c in enumerate(track.clips):
        c.name = f"c{i}"
        c.audio = AudioClip(file=f"f{i}.wav", mode=mode, sync=sync, bars=bars)
    return eng, track


def _run_ticks(eng, start, count):
    """Tick the engine as the clock would: tick n is due at time n * interval."""
    for n in range(start, start + count):
        eng.clock.tick_time = n * eng.clock.tick_interval
        eng._on_clock_tick(n % 384, n)


def test_bar_launch_is_sent_one_eighth_ahead_with_the_downbeat_time():
    eng, track = _audio_engine()
    eng.launch_clip(2, 1)
    _run_ticks(eng, 0, 384 - AUDIO_LOOKAHEAD_TICKS)          # tick 0 applied nothing new yet...
    eng.audio.calls.clear()
    track.queued_clip_idx = 3
    _run_ticks(eng, 384 - AUDIO_LOOKAHEAD_TICKS, AUDIO_LOOKAHEAD_TICKS + 1)
    starts = [c for c in eng.audio.calls if c[0] == "start"]
    assert starts == [("start", 2, "c3", pytest.approx(384 * eng.clock.tick_interval), True)]
    assert track.active_clip_idx == 3                          # applied on the downbeat


def test_synced_loop_restarts_on_its_bar_every_cycle():
    eng, track = _audio_engine(bars=1)
    track.queued_clip_idx = 0
    _run_ticks(eng, 0, 384 * 3 + 1)
    times = [round(c[3] / eng.clock.tick_interval) for c in eng.audio.calls if c[0] == "start"]
    assert times == [0, 384, 768, 1152]


def test_auto_cycle_rounds_the_slice_to_whole_bars():
    eng, track = _audio_engine()
    eng.audio.frames = int(RATE * 4.1)                       # ~2 bars at 120 BPM
    track.queued_clip_idx = 0
    _run_ticks(eng, 0, 384 * 4 + 1)
    times = [round(c[3] / eng.clock.tick_interval) for c in eng.audio.calls if c[0] == "start"]
    assert times == [0, 768, 1536]


def test_unsynced_clip_starts_and_stops_at_once():
    eng, track = _audio_engine(mode="oneshot", sync=False)
    eng.launch_clip(2, 4)
    assert eng.audio.calls == [("start", 2, "c4", None, False)]
    assert track.active_clip_idx == 4 and track.queued_clip_idx == -1
    eng.stop_track(2)
    assert eng.audio.calls[-1] == ("stop", 2, None) and track.active_clip_idx == -1
    # The worker reports the end of a one-shot: the track stops
    eng.launch_clip(2, 4)
    assert eng.audio_ended(2) and track.active_clip_idx == -1


def test_scene_launch_leaves_a_full_backing_track_playing(monkeypatch):
    eng, track = _audio_engine(mode="full")
    track.active_clip_idx = 0
    monkeypatch.setattr(type(eng), "is_playing", property(lambda self: True))
    eng.launch_scene(5)
    assert track.queued_clip_idx == -1 and eng.song.tracks[0].queued_clip_idx == 5


def test_play_prerolls_so_synced_audio_starts_on_tick_zero(monkeypatch):
    eng, track = _audio_engine()
    track.selected_clip_idx = 2
    pad = eng.song.tracks[5]
    pad.kind = "audio"
    pad.clips[0].audio = AudioClip(file="hit.wav", mode="oneshot", sync=False)
    started = []
    monkeypatch.setattr(eng.clock, "start", lambda at=None: started.append(at))
    t = time.perf_counter()
    eng.play()
    assert started and started[0] > t + 0.1
    assert eng.audio.calls == [("start", 2, "c2", started[0], True)]
    assert pad.active_clip_idx == -1                           # pads wait for a tap
    eng.audio.calls.clear()
    _run_ticks(eng, 0, 2)                                      # tick 0 doesn't send it again
    assert eng.audio.calls == []


def test_empty_slot_launch_stops_the_track():
    eng, track = _audio_engine()
    track.clips[6].audio = None
    track.queued_clip_idx = 6
    _run_ticks(eng, 0, 1)
    assert eng.audio.calls == [("stop", 2, 0.0)]


# -- player ----------------------------------------------------------------------

class FakeClient:
    def __init__(self):
        self.sent = []
        self.ready, self.device_name, self.error, self.xruns = True, "fake", "", 0
        self.on_event = None

    running = True

    def start(self, wait=5.0):
        return True

    def close(self):
        pass

    def load(self, key, path):
        self.sent.append(("load", key))
        return True

    def play(self, slot, key, **kw):
        self.sent.append(("play", slot, key, kw))
        return True

    def stop(self, slot, at=None):
        self.sent.append(("stop", slot, at))
        return True

    def retarget(self, slot, key, begin=0, end=0):
        self.sent.append(("retarget", slot, key, begin, end))
        return True

    def stop_all(self):
        return True

    def set_gain(self, slot, gain):
        return True


def test_player_prepares_files_and_plays_slices(tmp_path):
    sf = pytest.importorskip("soundfile")
    folder = tmp_path / "SpectreAudio"
    folder.mkdir()
    sf.write(folder / "loop.wav", np.zeros((RATE, 2), dtype=np.float32), RATE)
    changed = threading.Event()
    player = AudioPlayer(folder, tmp_path / "cache", client=FakeClient(), on_change=changed.set)
    player.offset_s = 0.01
    player.prepare("gone.wav")
    assert player.file_state("gone.wav")["state"] == "missing"
    player.prepare("loop.wav")
    deadline = time.time() + 30
    while player.file_state("loop.wav")["state"] != "ready" and time.time() < deadline:
        time.sleep(0.05)
    assert player.file_state("loop.wav")["frames"] == RATE
    key = player.file_state("loop.wav")["key"]
    assert ("load", key) in player.client.sent

    from src.spectre.sequencer.models import Clip
    clip = Clip(audio=AudioClip(file="loop.wav", start=1000, end=0, gain_db=-6.0))
    assert player.clip_frames(clip) == RATE - 1000
    player.start(3, clip, 5.0, True)
    kind, slot, k, kw = player.client.sent[-1]
    assert (kind, slot, k, kw["at"], kw["begin"], kw["loop"]) == ("play", "t3", key, 5.01, 1000, True)
    assert kw["gain"] == pytest.approx(0.501, abs=0.001)
    # Slice edits reach the voice playing the clip at once
    player._clips = {clip.clip_id: clip}
    clip.audio.end = 20000
    player.retarget(clip)
    assert player.client.sent[-1] == ("retarget", "t3", key, 1000, 20000)
    n = len(player.client.sent)
    player.retarget_all()                                    # nothing changed: nothing sent
    assert len(player.client.sent) == n
    # Only the current voice's end reports the track stopping
    ended = []
    player.on_ended = ended.append
    player._on_event({"ev": "ended", "slot": "t3", "id": kw["vid"] - 1})
    player._on_event({"ev": "ended", "slot": "t3", "id": kw["vid"]})
    assert ended == [3]
    n = len(player.client.sent)
    clip.audio.end = 0
    player.retarget(clip)                                    # not playing any more
    assert len(player.client.sent) == n
    # A clip whose file isn't ready silences its slot instead
    player.start(4, Clip(audio=AudioClip(file="gone.wav")), 6.0, False)
    assert player.client.sent[-1] == ("stop", "t4", 6.01)


# -- bridge ----------------------------------------------------------------------

def test_bridge_audio_track_and_clip_editing(tmp_path):
    from src.spectre.ui.bridge import SpectreBridge
    from tests.test_sequencer_bridge import DummyJuno

    b = SpectreBridge(DummyJuno())
    player = b.audio_player
    player.client = FakeClient()
    player.folder = tmp_path / "SpectreAudio"
    player.cache = tmp_path / "cache"
    (player.folder / "Song").mkdir(parents=True)
    (player.folder / "Song" / "stem.wav").write_bytes(b"not audio")
    stick = tmp_path / "stick"
    stick.mkdir()
    (stick / "hit.wav").write_bytes(b"x")

    b.seqSelectTrack(4)
    b.seqSetTrackKind(4, "audio")
    track = b.sequencer.song.tracks[4]
    assert track.is_audio and b.seqTracks[4]["kind"] == "audio"
    assert b.seqTracks[4]["clips"][0]["audioFile"] == ""

    assert b.audioBrowse("", "") == {"source": "", "sub": "", "dirs": ["Song"], "files": [],
                                     "root": str(player.folder)}
    assert b.audioBrowse("", "Song")["files"] == ["stem.wav"]
    assert b.audioBrowse("", "../..")["sub"] == ""

    b.seqSelectClip(1)
    b.seqSetClipAudioFile("", "Song/stem.wav")
    clip = track.clips[1]
    assert clip.audio.file == "Song/stem.wav" and clip.name == "stem"
    info = b.seqTracks[4]["clips"][1]
    assert info["audioName"] == "stem" and info["audioState"] in ("converting", "error")

    b.seqSetClipAudio("mode", "oneshot")
    assert (clip.audio.mode, clip.audio.sync) == ("oneshot", False)
    b.seqSetClipAudio("sync", True)
    b.seqSetClipAudio("gainDb", -99)
    assert clip.audio.sync and clip.audio.gain_db == -60.0

    # From a USB stick the file is copied into the media folder, then assigned
    b.seqSelectClip(2)
    b.seqSetClipAudioFile(str(stick), "hit.wav")
    deadline = time.time() + 5
    while track.clips[2].audio is None and time.time() < deadline:
        from PyQt6.QtCore import QCoreApplication
        QCoreApplication.processEvents()
        time.sleep(0.02)
    assert track.clips[2].audio.file == "hit.wav" and (player.folder / "hit.wav").is_file()

    # Clips keep their audio when the track goes back to notes
    b.seqSetTrackKind(4, "notes")
    assert not track.is_audio and clip.audio.file == "Song/stem.wav"
    assert "audioFile" not in b.seqTracks[4]["clips"][1]
    b.seqSelectClip(1)
    b.seqClearClipAudio()
    assert clip.audio.file == ""
    b.close_audio()


def test_play_starts_audio_in_a_real_worker(tmp_path):
    """Bridge -> engine -> player -> worker process (no device): Play sounds the clip."""
    sf = pytest.importorskip("soundfile")
    from PyQt6.QtCore import QCoreApplication

    from src.spectre.ui.bridge import SpectreBridge
    from tests.test_sequencer_bridge import DummyJuno

    b = SpectreBridge(DummyJuno())
    player = b.audio_player
    player.close()
    events = []
    player.client = AudioClient(null=True)
    player.client.on_event = lambda ev: (events.append(ev), player._on_event(ev))
    player.on_change, player.on_ended = b._audioSync.emit, b._audioEnded.emit
    player.folder, player.cache = tmp_path / "lib", tmp_path / "cache"
    player.folder.mkdir()
    sf.write(player.folder / "loop.wav", np.full((RATE // 2, 2), 0.1, dtype=np.float32), RATE)
    try:
        b.seqSelectTrack(3)
        b.seqSetTrackKind(3, "audio")
        b.seqSetClipAudioFile("", "loop.wav")
        deadline = time.time() + 30
        while not (player.ready and player.file_state("loop.wav")["state"] == "ready") and time.time() < deadline:
            QCoreApplication.processEvents()
            time.sleep(0.05)
        assert player.ready and b.seqTracks[3]["clips"][0]["audioState"] == "ready"
        b.seqPlay()
        deadline = time.time() + 5
        while not any(e.get("ev") == "started" for e in events) and time.time() < deadline:
            time.sleep(0.02)
        assert any(e.get("ev") == "started" and e.get("slot") == "t3" for e in events)
        b.seqStop()
    finally:
        b.close_audio()


# -- clip tempo, renders, waveform -------------------------------------------------

def _player_with_file(tmp_path, seconds=4.0, name="loop.wav"):
    sf = pytest.importorskip("soundfile")
    folder = tmp_path / "lib"
    folder.mkdir(exist_ok=True)
    t = np.arange(int(RATE * seconds)) / RATE
    sf.write(folder / name, np.stack([np.sin(t * 600), np.sin(t * 600)], axis=1).astype(np.float32) * 0.5, RATE)
    player = AudioPlayer(folder, tmp_path / "cache", client=FakeClient())
    player.prepare(name)
    deadline = time.time() + 30
    while player.file_state(name)["state"] != "ready" and time.time() < deadline:
        time.sleep(0.05)
    return player


class _FakeRender:
    """Stands in for a Rubber Band render: writes the slice, timed by the tempo factor."""
    calls = []

    def __init__(self, base_key, begin, end, tempo, pitch, key, folder):
        _FakeRender.calls.append((tempo, pitch))
        base = np.load(media.cache_paths(base_key, folder)["audio"])
        end = len(base) if end <= 0 else end
        n = int(round((end - begin) / tempo))
        media._save_entry(np.resize(base[begin:end], (n, 2)).astype(np.float32), key, folder, {})
        self.stderr = None

    def wait(self):
        return 0


def test_clip_tempo_and_stretch_spec(tmp_path, monkeypatch):
    from src.spectre.sequencer.models import Clip
    player = _player_with_file(tmp_path, seconds=4.0)
    clip = Clip(audio=AudioClip(file="loop.wav"))
    player.song_bpm = 120.0
    assert player.clip_bars(clip) == 2 and player.clip_bpm(clip) == pytest.approx(120.0)
    assert player.render_spec(clip) is None
    clip.audio.bars = 2
    clip.audio.end = int(RATE * 4 * 120 / 125)              # 2 bars at 125 BPM
    assert player.clip_bpm(clip) == pytest.approx(125.0, abs=0.01)
    clip.audio.stretch = True
    assert player.render_spec(clip) == (pytest.approx(0.96, abs=1e-4), 0.0)
    clip.audio.semitones, clip.audio.cents = -2, 25
    assert player.render_spec(clip)[1] == pytest.approx(-1.75)
    player.song_bpm = 400.0                                 # clamped to 1.5x
    assert player.render_spec(clip)[0] == 1.5

    # Renders run in the background; the clip plays the newest ready one
    monkeypatch.setattr(media, "render_in_subprocess", _FakeRender)
    player.song_bpm = 120.0
    player.set_clips([clip])
    deadline = time.time() + 10
    while player.clip_state(clip)["state"] != "ready" and time.time() < deadline:
        time.sleep(0.02)
    assert player.clip_state(clip)["state"] == "ready"
    first = player.clip_frames(clip)
    assert first == pytest.approx(clip.audio.end / 0.96, abs=2)
    player.song_bpm = 100.0
    player.refresh_renders()
    assert player.clip_frames(clip) == first                # old render plays meanwhile
    deadline = time.time() + 10
    while player.clip_state(clip)["state"] != "ready" and time.time() < deadline:
        time.sleep(0.02)
    assert player.clip_frames(clip) == pytest.approx(clip.audio.end / 0.8, abs=2)


def test_render_reports_a_missing_rubberband(tmp_path, monkeypatch):
    player = _player_with_file(tmp_path, seconds=0.5)
    key = player.file_state("loop.wav")["key"]
    monkeypatch.setattr(media, "rubberband_path", lambda: None)
    with pytest.raises(RuntimeError, match="needs Rubber Band"):
        media.render(key, 0, 0, 1.1, 0.0, "r1", player.cache)


@pytest.mark.skipif(media.rubberband_path() is None, reason="rubberband not installed")
def test_rubberband_render_keeps_length_by_tempo(tmp_path):
    player = _player_with_file(tmp_path, seconds=2.0)
    key = player.file_state("loop.wav")["key"]
    info = media.render(key, 0, RATE, 1.25, 0.0, "r2", player.cache)
    assert info["frames"] == pytest.approx(RATE / 1.25, rel=0.02)


def test_peaks_window_zooms_into_the_audio(tmp_path):
    player = _player_with_file(tmp_path, seconds=2.0)
    key = player.file_state("loop.wav")["key"]
    wide = media.peaks_window(key, 0, 0, 500, player.cache)
    assert wide.shape == (500, 2) and wide[:, 1].max() > 0.45
    close = media.peaks_window(key, 1000, 1400, 400, player.cache)   # 1 frame per column
    data = np.load(media.cache_paths(key, player.cache)["audio"])
    assert close[:, 1] == pytest.approx(data[1000:1400].mean(axis=1), abs=1e-6)
    assert media.peaks_window("nope", 0, 0, 10, player.cache).shape == (10, 2)


def test_bridge_fit_end_and_song_bpm_from_clip(tmp_path):
    from src.spectre.ui.bridge import SpectreBridge
    from tests.test_sequencer_bridge import DummyJuno

    b = SpectreBridge(DummyJuno())
    b.close_audio()
    player = _player_with_file(tmp_path, seconds=5.0)
    b.audio_player = player
    b.sequencer.audio = player
    try:
        b.seqSelectTrack(0)
        b.seqSetTrackKind(0, "audio")
        b.seqSetClipAudioFile("", "loop.wav")
        b.seqSetClipAudio("start", RATE // 2)
        b.seqSetClipAudio("bars", 2)
        b.seqFitClipEnd()                                   # 2 bars at 120 BPM = 4 s
        clip = b.sequencer.song.tracks[0].clips[0]
        assert clip.audio.end == RATE // 2 + 4 * RATE
        info = b.seqTracks[0]["clips"][0]
        assert (info["audioBars"], info["audioBpm"], info["audioBarsAuto"]) == (2, 120.0, False)
        b.seqSetClipAudio("end", RATE // 2 + int(4.2 * RATE))   # longer slice: slower clip
        b.seqSetSongBpmFromClip()
        assert b.bpm == pytest.approx(114.29, abs=0.01)
        # A synced loop of 4.2 s restarts every 2 bars (4 s) at 120 BPM: the tail is cut
        b.setBpm(120)
        b.seqSetClipAudio("bars", 0)
        assert b.seqTracks[0]["clips"][0]["audioCutFrame"] == RATE // 2 + 4 * RATE
        b.seqSetClipAudio("mode", "oneshot")
        assert b.seqTracks[0]["clips"][0]["audioCutFrame"] == 0
        b.seqSetClipAudio("end", 10 * RATE)                  # past the file end = to the end
        assert clip.audio.end == 0
        assert len(b.audioPeaks(0, 0, 100)) == 200
    finally:
        player.close()


# -- step 5: drift lock, held tempo, offset ----------------------------------------

from src.spectre.audio.drift import DriftEstimator  # noqa: E402


def test_drift_estimator_measures_ppm_through_jitter():
    rng = np.random.default_rng(1)
    est = DriftEstimator(RATE)
    true_rate = RATE * (1 + 37e-6)                       # device 37 ppm fast
    for i in range(4 * 120):                             # 2 minutes at 4 reports/s
        dac = 1000.0 + i * 0.25
        frames = int((dac - 1000.0) * true_rate)
        est.add(frames, dac + rng.normal(0, 0.0005))     # 0.5 ms timestamp jitter
        if i == 4 * 20:
            assert est.ppm() is None                     # under 30 s: no correction yet
    assert est.ppm() == pytest.approx(37, abs=3)
    assert est.ratio() == pytest.approx(1 + 37e-6, abs=3e-6)
    est.add(frames + 100, dac + 0.3, xruns=1)            # an underrun starts over
    assert est.ppm() is None and len(est.points) == 1


def test_clock_trim_scales_the_tick_interval():
    from src.spectre.sequencer.clock import SequencerClock
    c = SequencerClock(bpm=120)
    nominal = c.tick_interval
    c.set_rate_trim(1.00005)
    assert c.tick_interval == pytest.approx(nominal / 1.00005)
    c.set_rate_trim(1.5)                                 # clamped to 0.1%
    assert c.rate_trim == 1.001


def test_tempo_waits_while_synced_audio_plays(tmp_path, monkeypatch):
    monkeypatch.setenv("JUNOSPECTRE_DATA_DIR", str(tmp_path))
    from src.spectre.ui.bridge import SpectreBridge
    from tests.test_sequencer_bridge import DummyJuno

    b = SpectreBridge(DummyJuno())
    b.close_audio()
    eng = b.sequencer
    track = eng.song.tracks[2]
    track.kind = "audio"
    track.clips[0].audio = AudioClip(file="x.wav", sync=True)
    track.active_clip_idx = 0
    monkeypatch.setattr(type(eng), "is_playing", property(lambda self: playing[0]))
    playing = [True]
    b.setBpm(130)
    assert b.bpm == 120 and b.pendingBpm == 130          # held
    b.cancelPendingBpm()
    b.setBpm(128)
    playing[0] = False
    b._audio_release_tempo()
    assert b.bpm == 128 and b.pendingBpm == 0            # applied once audio stopped
    # Pads (AT ONCE clips) don't hold the tempo
    playing[0] = True
    track.clips[0].audio.sync = False
    b.setBpm(110)
    assert b.bpm == 110


def test_offset_and_drift_lock_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("JUNOSPECTRE_DATA_DIR", str(tmp_path))
    from src.spectre.ui.bridge import SpectreBridge
    from src.spectre.ui.bridge.hardware import load_hardware_settings
    from tests.test_sequencer_bridge import DummyJuno

    b = SpectreBridge(DummyJuno())
    b.close_audio()
    b.setAudioOffsetMs(12.34)
    assert b.audio_player.offset_s == pytest.approx(0.0123) and b.audioStatus["offsetMs"] == 12.3
    b.setAudioOffsetMs(9999)
    assert b.audioStatus["offsetMs"] == 300.0
    b.setAudioDriftLock(False)
    assert load_hardware_settings()["audio_drift_lock"] is False
    assert b._audio_cal_target()[1] in (37, 84)


def test_calibration_clicks_audio_and_juno_together(tmp_path, monkeypatch):
    monkeypatch.setenv("JUNOSPECTRE_DATA_DIR", str(tmp_path))
    from src.spectre.ui.bridge import SpectreBridge
    from tests.test_sequencer_bridge import DummyJuno

    b = SpectreBridge(DummyJuno())
    player = b.audio_player
    player.close()
    events = []
    player.client = AudioClient(null=True)
    player.client.on_event = lambda ev: (events.append(ev), player._on_event(ev))
    player.cache = tmp_path / "cache"
    notes = []
    monkeypatch.setattr(b.sequencer, "_send_note_on", lambda ch, n, v: notes.append((time.perf_counter(), ch, n)))
    monkeypatch.setattr(b.sequencer, "_send_note_off", lambda ch, n: None)
    try:
        b.audioCalibrate(True)
        assert b.audioStatus["calibrating"]
        deadline = time.time() + 8
        while len(notes) < 3 and time.time() < deadline:
            time.sleep(0.05)
        b.audioCalibrate(False)
        assert len(notes) >= 3
        gaps = [notes[i + 1][0] - notes[i][0] for i in range(2)]
        assert gaps == [pytest.approx(0.5, abs=0.01)] * 2
        assert sum(1 for e in events if e.get("ev") == "started" and e.get("slot") == "cal") >= 2
    finally:
        b.close_audio()
