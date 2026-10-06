"""Host hardware telemetry for the System page (stdlib only, no psutil).

Reads Linux procfs/sysfs directly so the Pi appliance needs no extra
dependencies. Every function is best-effort and returns None/0 when the
underlying file is missing (containers, macOS dev machines, offscreen tests).

CPU load needs two /proc/stat samples: pass the previous (idle, total)
tuple back in; first call returns 0.0 and primes the baseline.
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

PROC_STAT = Path("/proc/stat")
PROC_MEMINFO = Path("/proc/meminfo")
THERMAL_ROOT = Path("/sys/class/thermal")


@dataclass
class SystemTelemetry:
    """One snapshot of host stats; None text fields mean 'unavailable'."""

    cpu_percent: float = 0.0
    cpu_temp_c: Optional[float] = None
    mem_used_mb: int = 0
    mem_total_mb: int = 0
    disk_free_gb: float = 0.0
    disk_total_gb: float = 0.0


def read_cpu_times() -> Optional[Tuple[int, int]]:
    """Return (idle, total) jiffies from /proc/stat aggregate line."""
    try:
        line = PROC_STAT.read_text().splitlines()[0].split()
        if not line or line[0] != "cpu":
            return None
        nums = [int(x) for x in line[1:]]
        idle = nums[3] + (nums[4] if len(nums) > 4 else 0)  # idle + iowait
        return idle, sum(nums)
    except (OSError, ValueError, IndexError) as e:
        logger.debug(f"Telemetry /proc/stat unreadable: {e}")
        return None


def cpu_percent_from(prev: Optional[Tuple[int, int]]) -> Tuple[float, Optional[Tuple[int, int]]]:
    """Compute CPU % since prev sample. First call returns (0.0, baseline)."""
    cur = read_cpu_times()
    if cur is None or prev is None:
        return 0.0, cur
    prev_idle, prev_total = prev
    cur_idle, cur_total = cur
    total_d = cur_total - prev_total
    idle_d = cur_idle - prev_idle
    if total_d <= 0:
        return 0.0, cur
    pct = (total_d - idle_d) * 100.0 / total_d
    return max(0.0, min(100.0, pct)), cur


def read_mem() -> Tuple[int, int]:
    """Return (used_mb, total_mb) from /proc/meminfo."""
    try:
        info: dict[str, int] = {}
        for line in PROC_MEMINFO.read_text().splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0].rstrip(":") in ("MemTotal", "MemAvailable"):
                info[parts[0].rstrip(":")] = int(parts[1])  # kB
        total_kb = info.get("MemTotal", 0)
        avail_kb = info.get("MemAvailable", 0)
        total_mb = total_kb // 1024
        used_mb = max(0, (total_kb - avail_kb) // 1024)
        return used_mb, total_mb
    except (OSError, ValueError) as e:
        logger.debug(f"Telemetry /proc/meminfo unreadable: {e}")
        return 0, 0


def read_cpu_temp() -> Optional[float]:
    """Return CPU temp in °C from thermal zones, or None."""
    try:
        if not THERMAL_ROOT.is_dir():
            return None
        for zone in sorted(THERMAL_ROOT.glob("thermal_zone*")):
            try:
                kind = (zone / "type").read_text().strip().lower()
                raw = int((zone / "temp").read_text().strip())
            except (OSError, ValueError):
                continue
            # Prefer Pi SoC / package sensors; fall back to first sane zone.
            if any(k in kind for k in ("cpu", "soc", "package", "bcm", "thermal")) or raw > 0:
                temp_c = raw / 1000.0
                if -40.0 < temp_c < 125.0:
                    # Prefer explicitly CPU-named zones when present.
                    if "cpu" in kind or "soc" in kind or "package" in kind:
                        return temp_c
                    # Otherwise keep first sane reading as fallback.
                    first = temp_c
                    # Continue scanning for a better-named zone.
                    try:
                        return _prefer_cpu_zone(first)
                    except Exception:
                        return first
        return None
    except OSError as e:
        logger.debug(f"Telemetry thermal unreadable: {e}")
        return None


def _prefer_cpu_zone(fallback: float) -> float:
    for zone in sorted(THERMAL_ROOT.glob("thermal_zone*")):
        try:
            kind = (zone / "type").read_text().strip().lower()
            if any(k in kind for k in ("cpu", "soc", "package", "bcm2835", "bcm2711", "bcm2712")):
                raw = int((zone / "temp").read_text().strip())
                temp_c = raw / 1000.0
                if -40.0 < temp_c < 125.0:
                    return temp_c
        except (OSError, ValueError):
            continue
    return fallback


def read_disk(path: str = "/") -> Tuple[float, float]:
    """Return (free_gb, total_gb) for the given mount."""
    try:
        usage = shutil.disk_usage(path)
        return usage.free / 1e9, usage.total / 1e9
    except OSError as e:
        logger.debug(f"Telemetry disk unreadable ({path}): {e}")
        return 0.0, 0.0


def read_telemetry(
    prev_cpu: Optional[Tuple[int, int]] = None,
) -> Tuple[SystemTelemetry, Optional[Tuple[int, int]]]:
    """Take one snapshot; returns (telemetry, new_cpu_baseline)."""
    cpu_pct, new_prev = cpu_percent_from(prev_cpu)
    temp = read_cpu_temp()
    mem_used, mem_total = read_mem()
    disk_free, disk_total = read_disk("/")
    return (
        SystemTelemetry(
            cpu_percent=cpu_pct,
            cpu_temp_c=temp,
            mem_used_mb=mem_used,
            mem_total_mb=mem_total,
            disk_free_gb=disk_free,
            disk_total_gb=disk_total,
        ),
        new_prev,
    )
