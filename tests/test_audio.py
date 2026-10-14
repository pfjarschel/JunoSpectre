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
    assert m.events.popleft() == {"ev": "started", "slot": "t1"}


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
    assert {"ev": "ended", "slot": "S"} in list(m.events)
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
