#!/usr/bin/env python3
"""Play audio through the JunoSpectre audio worker (first hardware check).

Converts a file into the playback cache (in its own process, as the app does),
starts the worker on the JUNO's USB audio and plays it. Without a file it
plays a generated click: 4 bars at 120 BPM, a high click on each bar's beat 1.

    python tools/audio_play_test.py                     # click, 8 s
    python tools/audio_play_test.py song.mp3 -s 20      # 20 s of a file
    python tools/audio_play_test.py loop.wav --loop 0 2 # loop the first 2 s
    python tools/audio_play_test.py song.wav --voices 8 # 8 copies at once (CPU check)

Prints the device, xruns (underruns: should stay 0), the worker's CPU use and
the DAC rate measured against the Pi clock (the drift the drift lock corrects).
The JUNO must be in USB Driver VENDOR mode.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.spectre.audio import media  # noqa: E402
from src.spectre.audio.client import AudioClient  # noqa: E402


def click_track(path: Path, bpm: float = 120.0, bars: int = 4) -> None:
    import soundfile as sf

    beat = int(round(60.0 / bpm * media.SAMPLE_RATE))
    data = np.zeros((beat * 4 * bars, 2), dtype=np.float32)
    t = np.arange(int(0.03 * media.SAMPLE_RATE)) / media.SAMPLE_RATE
    for b in range(4 * bars):
        freq = 1760.0 if b % 4 == 0 else 880.0
        blip = (0.5 * np.sin(2 * np.pi * freq * t) * np.exp(-t * 120)).astype(np.float32)
        data[b * beat:b * beat + len(blip)] += blip[:, None]
    sf.write(path, data, media.SAMPLE_RATE)


def cpu_seconds(pid: int) -> float:
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return (int(fields[11]) + int(fields[12])) / os.sysconf("SC_CLK_TCK")
    except (OSError, IndexError, ValueError):
        return 0.0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", nargs="?", help="audio file (default: generated click)")
    ap.add_argument("-s", "--seconds", type=float, default=8.0)
    ap.add_argument("--device", default="", help="output device name part (default: JUNO, else system default)")
    ap.add_argument("--loop", nargs=2, type=float, metavar=("START", "END"), help="loop this region (seconds)")
    ap.add_argument("--voices", type=int, default=1, help="play this many copies at once")
    ap.add_argument("--block", type=int, default=512)
    ap.add_argument("--latency", type=float, default=0.03)
    args = ap.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        src = Path(args.file) if args.file else tmp / "click.wav"
        if not args.file:
            click_track(src)
        print(f"converting {src.name} ...")
        t = time.perf_counter()
        proc = media.convert_in_subprocess(src, "test", tmp)
        if proc.wait() != 0:
            print("conversion failed:", proc.stderr.read().strip())
            return 1
        info = media.cache_info("test", tmp)
        print(f"  {info['seconds']:.1f} s, source {info['source_rate']} Hz x {info['source_channels']} ch,"
              f" converted in {time.perf_counter() - t:.1f} s")

        client = AudioClient(device=args.device, block=args.block, latency=args.latency)
        if not client.start(10.0):
            print("audio worker failed:", client.error)
            return 1
        print(f"device: {client.device_name}  latency {client.latency * 1000:.1f} ms  block {args.block}")
        client.load("test", media.cache_paths("test", tmp)["audio"])
        begin = end = 0
        if args.loop:
            begin, end = (int(x * media.SAMPLE_RATE) for x in args.loop)
        start = time.perf_counter() + 0.2
        gain = 1.0 / max(1, args.voices)
        for v in range(max(1, args.voices)):
            client.play(f"v{v}", "test", at=start, begin=begin, end=end, loop=bool(args.loop), gain=gain)
        cpu0, t0 = cpu_seconds(client.proc.pid), time.perf_counter()
        try:
            time.sleep(args.seconds)
        except KeyboardInterrupt:
            pass
        cpu = (cpu_seconds(client.proc.pid) - cpu0) / (time.perf_counter() - t0) * 100
        client.stop_all()
        time.sleep(0.1)
        rate = ""
        if len(client.clock) >= 2:
            (f0, d0), (f1, d1) = client.clock[0], client.clock[-1]
            if d1 > d0:
                measured = (f1 - f0) / (d1 - d0)
                rate = f"  DAC rate {measured:.1f} Hz ({(measured / media.SAMPLE_RATE - 1) * 1e6:+.0f} ppm)"
        print(f"xruns {client.xruns}  worker CPU {cpu:.1f}% of one core{rate}")
        if client.error:
            print("error:", client.error)
        client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
