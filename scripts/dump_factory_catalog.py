#!/usr/bin/env python3
"""Dump the full JUNO-DS / XPS-30 sound catalog (metadata only) from hardware.

Covers everything in one pass so the script never needs re-running:
- Preset patches  MSB 87 LSB 64..72  (1088, ROM)
- DS patches      MSB 87 LSB 73..74  (184, ROM)
- GM2 patches     MSB 121 LSB 0      (128, ROM)
- EXP patches     MSB 93 LSB 1..26   (populated slots only, ROM)
- User patches    MSB 87 LSB 0..1    (256, direct memory reads, no disruption)
- Preset/DS drums MSB 86 LSB 64/65   (21+9, ROM)
- User drums      8 slots            (direct memory reads)
- Preset perfs    MSB 85 LSB 64      (64, via PERFORM mode + control ch 16)
- User perfs      128 slots          (direct memory reads)

Patch-like rows carry the Roland 3-letter category (common block byte 0x0C,
see src/spectre/core/categories.py). Drums store category DRM, performances
carry no category. Only names + bank/program addresses are stored; audition
is via Bank Select + Program Change, so no SysEx blobs are needed.

NOTE: bank-select dumping replaces the synth's temp buffer. The script
restores PATCH sound mode at the end but the temp buffer will hold the last
dumped patch -- re-sync afterwards if you had unsaved edits.

Usage:
    python scripts/dump_factory_catalog.py --out /tmp/catalog.json --write-db
    python scripts/dump_factory_catalog.py --banks preset --pc-limit 4 --out /tmp/t.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import mido

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from spectre.core.categories import decode_common_block  # noqa: E402
from spectre.core.midi import MidiDeviceManager  # noqa: E402
from spectre.core.protocol import JunoClient  # noqa: E402
from spectre.core.sysex import ADDR_SETUP, OFFSET_PATCH_COMMON, add_address  # noqa: E402
from spectre.librarian.repository import PatchRepository  # noqa: E402

# (msb, lsb, num_pcs, kind, label)
PATCH_BANKS: list[tuple[int, int, int, str, str]] = [
    *[(87, lsb, 128, "patch", "preset") for lsb in range(64, 72)],
    (87, 72, 64, "patch", "preset"),
    (87, 73, 128, "patch", "ds"),
    (87, 74, 56, "patch", "ds"),
    (121, 0, 128, "patch", "gm"),
]
DRUM_BANKS: list[tuple[int, int, int, str]] = [
    (86, 64, 21, "preset-drums"),
    (86, 65, 9, "ds-drums"),
]
PERF_PRESET = (85, 64, 64)
PERF_CONTROL_CHANNEL = 15  # 0-indexed ch 16
EXP_MSB = 93
EXP_PROBE_PCS = (0, 1, 64, 127)


def load_resume_set(out_path: str) -> set[tuple]:
    """Load already-dumped (source, kind, msb, lsb, pc) tuples to skip them."""
    try:
        rows = json.loads(Path(out_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    items = rows if isinstance(rows, list) else []
    return {(r.get("source"), r.get("kind"), r.get("msb"), r.get("lsb"), r.get("pc")) for r in items}


def load_done_rows(out_path: str) -> list[dict]:
    try:
        rows = json.loads(Path(out_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return rows if isinstance(rows, list) else []


# Skip-set for --resume: (source, kind, msb, lsb, pc) tuples already dumped.
_RESUME: set[tuple] = set()


def _done(source: str, kind: str, msb: int, lsb: int, pc: int) -> bool:
    return (source, kind, msb, lsb, pc) in _RESUME


def select_patch(midi: MidiDeviceManager, msb: int, lsb: int, pc: int, ch: int = 0) -> None:
    midi.juno_out.send(mido.Message("control_change", channel=ch, control=0, value=msb))
    midi.juno_out.send(mido.Message("control_change", channel=ch, control=32, value=lsb))
    midi.juno_out.send(mido.Message("program_change", channel=ch, program=pc))


def read_temp_common(juno: JunoClient, timeout: float = 1.0) -> bytes | None:
    """Read the 80-byte patch common block from the temp buffer (name + category)."""
    juno._cached_patch_base = None
    juno._cached_sound_mode = None
    try:
        base = juno.get_active_patch_base(timeout=timeout)
    except Exception:
        return None
    addr = add_address(base, OFFSET_PATCH_COMMON)
    try:
        raw = juno.request_data(addr, (0x00, 0x00, 0x00, 0x50), timeout=timeout)
    except Exception:
        return None
    return bytes(raw) if raw and len(raw) >= 80 else None


def dump_patch_banks(juno: JunoClient, midi: MidiDeviceManager, delay: float,
                     pc_limit: int | None, timeout: float,
                     banks: list[tuple[int, int, int, str, str]] | None = None) -> list[dict]:
    rows: list[dict] = []
    for msb, lsb, count, kind, label in (banks if banks is not None else PATCH_BANKS):
        n = count if pc_limit is None else min(count, pc_limit)
        missing = sum(1 for pc in range(n) if not _done("factory", "patch", msb, lsb, pc))
        if missing == 0:
            print(f"[{label}] {msb}/{lsb} complete, skipped", flush=True)
            continue
        print(f"[{label}] {msb}/{lsb} x{n} ({missing} missing) ...", flush=True)
        for pc in range(n):
            if _done("factory", "patch", msb, lsb, pc):
                continue
            select_patch(midi, msb, lsb, pc)
            time.sleep(delay)
            raw = read_temp_common(juno, timeout=timeout)
            if raw is None:  # one retry after extra settle time
                time.sleep(delay)
                raw = read_temp_common(juno, timeout=timeout)
            if raw is None:
                print(f"  ERR {msb}/{lsb} pc {pc}: no common reply", flush=True)
                continue
            name, cat = decode_common_block(raw)
            rows.append({"source": "factory", "kind": "patch", "msb": msb,
                         "lsb": lsb, "pc": pc, "name": name,
                         "category": cat, "tags": []})
    return rows


def dump_exp_banks(juno: JunoClient, midi: MidiDeviceManager, delay: float,
                   pc_limit: int | None, timeout: float) -> list[dict]:
    """Dump populated EXP slots. Empty slots echo the GM bank: detect and skip."""
    gm_names: dict[int, str] = {}
    for pc in EXP_PROBE_PCS:
        select_patch(midi, 121, 0, pc)
        time.sleep(delay)
        raw = read_temp_common(juno, timeout=timeout)
        gm_names[pc] = decode_common_block(raw)[0] if raw else ""
    rows: list[dict] = []
    for lsb in range(1, 27):
        populated = False
        for pc in EXP_PROBE_PCS:
            select_patch(midi, EXP_MSB, lsb, pc)
            time.sleep(delay)
            raw = read_temp_common(juno, timeout=timeout)
            name = decode_common_block(raw)[0] if raw else None
            if name is not None and name != gm_names[pc]:
                populated = True
                break
        if not populated:
            print(f"[exp] 93/{lsb}: empty (echoes GM), skipped", flush=True)
            continue
        print(f"[exp] 93/{lsb} populated, dumping ...", flush=True)
        n = 128 if pc_limit is None else min(128, pc_limit)
        for pc in range(n):
            if _done("factory", "patch", EXP_MSB, lsb, pc):
                continue
            select_patch(midi, EXP_MSB, lsb, pc)
            time.sleep(delay)
            raw = read_temp_common(juno, timeout=timeout)
            if raw is None:
                print(f"  ERR 93/{lsb} pc {pc}", flush=True)
                continue
            name, cat = decode_common_block(raw)
            rows.append({"source": "factory", "kind": "patch", "msb": EXP_MSB,
                         "lsb": lsb, "pc": pc, "name": name,
                         "category": cat, "tags": []})
    return rows


def dump_user_patches(juno: JunoClient) -> list[dict]:
    """Direct memory reads at 0x30/0x31: no bank-select disruption."""
    rows: list[dict] = []
    for idx in range(256):
        msb, lsb, pc = 87, (0 if idx < 128 else 1), idx % 128
        if _done("synth-user", "patch", msb, lsb, pc):
            continue
        addr = (0x30 if idx < 128 else 0x31, idx % 128, 0x00, 0x00)
        try:
            raw = juno.request_data(addr, (0x00, 0x00, 0x00, 0x50), timeout=1.0)
        except Exception:
            raw = None
        if not raw or len(raw) < 80:
            print(f"  ERR user patch {idx + 501}", flush=True)
            continue
        name, cat = decode_common_block(bytes(raw))
        rows.append({"source": "synth-user", "kind": "patch", "msb": msb,
                     "lsb": lsb, "pc": pc, "name": name,
                     "category": cat, "tags": []})
    print(f"[user-patch] {len(rows)} slots", flush=True)
    return rows


def dump_drums(juno: JunoClient, midi: MidiDeviceManager, delay: float,
               pc_limit: int | None, timeout: float) -> list[dict]:
    rows: list[dict] = []
    for msb, lsb, count, label in DRUM_BANKS:
        n = count if pc_limit is None else min(count, pc_limit)
        print(f"[{label}] {msb}/{lsb} x{n} ...", flush=True)
        for pc in range(n):
            if _done("factory", "drum", msb, lsb, pc):
                continue
            select_patch(midi, msb, lsb, pc)
            time.sleep(delay)
            juno._cached_patch_base = None
            juno._cached_sound_mode = None
            try:
                base = juno.get_active_patch_base(timeout=timeout)
                addr = add_address(base, (0x00, 0x10, 0x00, 0x00))  # Temporary Drum
                raw = juno.request_data(addr, (0x00, 0x00, 0x00, 0x0C), timeout=timeout)
            except Exception:
                raw = None
            if not raw:
                print(f"  ERR drum {msb}/{lsb} pc {pc}", flush=True)
                continue
            rows.append({"source": "factory", "kind": "drum", "msb": msb,
                         "lsb": lsb, "pc": pc,
                         "name": bytes(raw[:12]).decode("latin1", errors="replace").strip(),
                         "category": "DRM", "tags": []})
    # User drums: direct reads at 0x40 stride 0x10 (8 kits, R501..R508).
    print("[user-drums] direct ...", flush=True)
    for i in range(8):
        if _done("synth-user", "drum", 86, 0, i):
            continue
        try:
            raw = juno.request_data((0x40, i * 0x10, 0x00, 0x00), (0x00, 0x00, 0x00, 0x0C), timeout=1.0)
        except Exception:
            raw = None
        if not raw:
            print(f"  ERR user drum R{501 + i}", flush=True)
            continue
        rows.append({"source": "synth-user", "kind": "drum", "msb": 86,
                     "lsb": 0, "pc": i,
                     "name": bytes(raw[:12]).decode("latin1", errors="replace").strip(),
                     "category": "DRM", "tags": []})
    return rows


def dump_performances(juno: JunoClient, midi: MidiDeviceManager, delay: float,
                      pc_limit: int | None, timeout: float) -> list[dict]:
    rows: list[dict] = []
    # User performances: direct reads at 0x20 (no mode switch needed).
    print("[user-perf] direct x128 ...", flush=True)
    for i in range(128 if pc_limit is None else min(128, pc_limit)):
        if _done("synth-user", "performance", 85, 0, i):
            continue
        try:
            raw = juno.request_data((0x20, i, 0x00, 0x00), (0x00, 0x00, 0x00, 0x0C), timeout=1.0)
        except Exception:
            raw = None
        if not raw:
            print(f"  ERR user perf {i + 1}", flush=True)
            continue
        rows.append({"source": "synth-user", "kind": "performance", "msb": 85,
                     "lsb": 0, "pc": i,
                     "name": bytes(raw[:12]).decode("latin1", errors="replace").strip(),
                     "category": "", "tags": []})
    # Preset performances: PERFORM mode + control channel (ch 16) bank-select.
    msb, lsb, count = PERF_PRESET
    n = count if pc_limit is None else min(count, pc_limit)
    print(f"[preset-perf] PERFORM mode {msb}/{lsb} x{n} ...", flush=True)
    juno.send_data(ADDR_SETUP, [1])  # PERFORM
    time.sleep(0.5)
    try:
        for pc in range(n):
            if _done("factory", "performance", msb, lsb, pc):
                continue
            midi.juno_out.send(mido.Message("control_change", channel=PERF_CONTROL_CHANNEL, control=0, value=msb))
            midi.juno_out.send(mido.Message("control_change", channel=PERF_CONTROL_CHANNEL, control=32, value=lsb))
            midi.juno_out.send(mido.Message("program_change", channel=PERF_CONTROL_CHANNEL, program=pc))
            time.sleep(delay + 0.3)  # performances load slower
            try:
                raw = juno.request_data((0x10, 0x00, 0x00, 0x00), (0x00, 0x00, 0x00, 0x0C), timeout=timeout)
            except Exception:
                raw = None
            if not raw:
                print(f"  ERR preset perf pc {pc}", flush=True)
                continue
            rows.append({"source": "factory", "kind": "performance", "msb": msb,
                         "lsb": lsb, "pc": pc,
                         "name": bytes(raw[:12]).decode("latin1", errors="replace").strip(),
                         "category": "", "tags": []})
    finally:
        juno.send_data(ADDR_SETUP, [0])  # back to PATCH
        time.sleep(0.4)
        juno._cached_patch_base = None
        juno._cached_sound_mode = None
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description="Dump full JUNO-DS/XPS-30 catalog from hardware.")
    ap.add_argument("--out", default="/tmp/juno_catalog.json")
    ap.add_argument("--banks", choices=["all", "preset", "ds", "gm", "exp", "user", "drums", "perfs"],
                    default="all")
    ap.add_argument("--delay", type=float, default=0.12)
    ap.add_argument("--timeout", type=float, default=1.0)
    ap.add_argument("--pc-limit", type=int, default=None)
    ap.add_argument("--write-db", action="store_true")
    ap.add_argument("--db", default=None,
                    help="user DB path (synth-user rows go here)")
    ap.add_argument("--factory-db", default=None,
                    help="factory DB path (ROM rows go here via builder)."
                    " Defaults to src/spectre/assets/librarian/factory.db")
    ap.add_argument("--model-variant", default="xps30",
                    help="hardware preset variant being dumped (xps30, juno-ds, ...)")
    ap.add_argument("--resume", action="store_true",
                    help="skip (source,kind,msb,lsb,pc) already present in --out; appends new rows")
    ap.add_argument("--only-banks", default=None,
                    help="restrict bank-select banks to comma list like '87/64,87/65'")
    args = ap.parse_args()

    global _RESUME
    done_rows: list[dict] = []
    if args.resume:
        done_rows = load_done_rows(args.out)
        _RESUME = {(r.get("source"), r.get("kind"), r.get("msb"), r.get("lsb"), r.get("pc"))
                   for r in done_rows}
        print(f"Resume: {len(done_rows)} rows already in {args.out}", flush=True)

    midi = MidiDeviceManager()
    midi.connect_juno()
    juno = JunoClient(midi)
    all_rows: list[dict] = []
    try:
        print(f"Sound mode: {juno.get_sound_mode(timeout=1.0)}")
        if args.banks in ("all", "preset", "ds", "gm"):
            banks = [b for b in PATCH_BANKS if args.banks == "all" or b[4] == args.banks]
            if args.only_banks:
                want = {tuple(int(x) for x in s.split("/")) for s in args.only_banks.split(",")}
                banks = [b for b in banks if (b[0], b[1]) in want]
            all_rows += dump_patch_banks(juno, midi, args.delay, args.pc_limit, args.timeout, banks)
        if args.banks in ("all", "exp"):
            all_rows += dump_exp_banks(juno, midi, args.delay, args.pc_limit, args.timeout)
        if args.banks in ("all", "user"):
            all_rows += dump_user_patches(juno)
        if args.banks in ("all", "drums"):
            all_rows += dump_drums(juno, midi, args.delay, args.pc_limit, args.timeout)
        if args.banks in ("all", "perfs"):
            all_rows += dump_performances(juno, midi, args.delay, args.pc_limit, args.timeout)
        all_rows = done_rows + all_rows
        Path(args.out).write_text(json.dumps(all_rows, indent=2), encoding="utf-8")
        kinds: dict[str, int] = {}
        for r in all_rows:
            kinds[f"{r['source']}/{r['kind']}"] = kinds.get(f"{r['source']}/{r['kind']}", 0) + 1
        print(f"Wrote {len(all_rows)} rows -> {args.out} {kinds}")
        if args.write_db:
            from spectre.librarian.factory import build_factory_db
            from spectre.librarian.repository import PatchRepository

            factory_rows = [r for r in all_rows if r.get("source") == "factory"]
            user_rows = [r for r in all_rows if r.get("source") != "factory"]
            if factory_rows:
                default_assets = (PROJECT_ROOT / "src" / "spectre" / "assets"
                                  / "librarian" / "factory.db")
                fdb = Path(args.factory_db) if args.factory_db else default_assets
                n = build_factory_db(fdb, factory_rows, args.model_variant)
                print(f"Factory catalog: {n} rows ({args.model_variant}) -> {fdb}")
            if user_rows:
                repo = PatchRepository(db_path=args.db) if args.db else PatchRepository()
                n = repo.bulk_upsert_factory(user_rows)
                print(f"User DB upserted {n}: synth-user={repo.count('synth-user')}")
                repo.close()
    finally:
        try:
            juno.send_data(ADDR_SETUP, [0])  # ensure PATCH mode
        except Exception:
            pass
        midi.close()
        print("NOTE: temp buffer holds the last dumped sound; re-sync if you had unsaved edits.")


if __name__ == "__main__":
    main()
