"""Display backlight control with graceful fallbacks.

Detection order:
  1. Linux sysfs backlight (/sys/class/backlight/*) — real hardware PWM,
     works for DSI panels and some HDMI bridges (e.g. rpi_backlight).
  2. ddcutil (DDC/CI VCP 0x10) — for HDMI monitors that support it.
  3. xrandr software dimming — gamma only, X11/desktop dev sessions.
  4. none — UI-only fallback, slider still moves, logs a warning.

All entry points are best-effort and never raise for missing hardware or
permissions, so the QML slider can never freeze the touch UI.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SYSFS_BACKLIGHT_ROOT = Path("/sys/class/backlight")
MIN_PERCENT = 10
MAX_PERCENT = 100


@dataclass
class SysfsBacklightDevice:
    """A writable sysfs backlight node."""

    name: str
    path: Path
    max_brightness: int


def find_sysfs_device(root: Path = SYSFS_BACKLIGHT_ROOT) -> Optional[SysfsBacklightDevice]:
    """Return the first usable sysfs backlight device, or None."""
    try:
        if not root.is_dir():
            return None
        candidates = sorted(p for p in root.iterdir() if p.is_dir())
    except OSError as e:
        logger.debug(f"Backlight scan failed ({root}): {e}")
        return None
    for dev_path in candidates:
        try:
            max_raw = int((dev_path / "max_brightness").read_text().strip())
            if max_raw <= 0:
                continue
            # Must be writable (or at least readable) to be useful.
            brightness_file = dev_path / "brightness"
            if not brightness_file.exists():
                continue
            if not os.access(brightness_file, os.W_OK | os.R_OK):
                # Still return it — write will fail gracefully later with a
                # permission hint, and detection stays truthful.
                pass
            return SysfsBacklightDevice(
                name=dev_path.name, path=dev_path, max_brightness=max_raw
            )
        except (OSError, ValueError) as e:
            logger.debug(f"Backlight device {dev_path} unusable: {e}")
            continue
    return None


def percent_to_raw(percent: int, max_raw: int) -> int:
    """Map 10..100% onto 1..max_raw (never 0, avoids blackout)."""
    pct = max(MIN_PERCENT, min(MAX_PERCENT, int(percent)))
    raw = round(max_raw * pct / 100.0)
    return max(1, min(max_raw, raw))


def set_sysfs(device: SysfsBacklightDevice, percent: int) -> bool:
    """Write a brightness percent to a sysfs device. Returns success."""
    try:
        raw = percent_to_raw(percent, device.max_brightness)
        (device.path / "brightness").write_text(str(raw))
        logger.info(f"Backlight (sysfs:{device.name}) set {percent}% (raw {raw})")
        return True
    except PermissionError:
        logger.warning(
            f"Backlight permission denied on {device.path}/brightness. "
            "Add user to video/backlight group or install udev rule: "
            'SUBSYSTEM==\"backlight\", GROUP=\"video\", MODE=\"0664\"'
        )
        return False
    except OSError as e:
        logger.warning(f"Backlight sysfs write failed ({device.name}): {e}")
        return False


def set_ddcutil(percent: int, timeout: float = 4.0) -> bool:
    """Set HDMI monitor brightness via DDC/CI. Returns success."""
    if shutil.which("ddcutil") is None:
        return False
    pct = max(MIN_PERCENT, min(MAX_PERCENT, int(percent)))
    try:
        proc = subprocess.run(
            ["ddcutil", "setvcp", "10", str(pct)],
            timeout=timeout,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return False
    except subprocess.TimeoutExpired:
        logger.warning("Backlight ddcutil timed out (monitor may not support DDC/CI)")
        return False
    except OSError as e:
        logger.debug(f"Backlight ddcutil failed: {e}")
        return False
    if proc.returncode == 0:
        logger.info(f"Backlight (ddcutil VCP 0x10) set {pct}%")
        return True
    logger.debug(f"Backlight ddcutil rejected: {(proc.stderr or proc.stdout).strip()}")
    return False


def set_xrandr(percent: int, output: Optional[str] = None, timeout: float = 5.0) -> bool:
    """Software dim via xrandr gamma. X11 only; no-op under eglfs/Wayland."""
    if os.environ.get("QT_QPA_PLATFORM") == "eglfs":
        return False
    if not os.environ.get("DISPLAY"):
        return False
    if shutil.which("xrandr") is None:
        return False
    pct = max(MIN_PERCENT, min(MAX_PERCENT, int(percent)))
    level = pct / 100.0
    targets = [output] if output else _xrandr_connected_outputs(timeout=timeout)
    if not targets:
        return False
    ok = False
    for out in targets:
        try:
            proc = subprocess.run(
                ["xrandr", "--output", out, "--brightness", f"{level:.2f}"],
                timeout=timeout,
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.TimeoutExpired) as e:
            logger.debug(f"Backlight xrandr failed ({out}): {e}")
            continue
        if proc.returncode == 0:
            ok = True
        else:
            logger.debug(f"xrandr {out} rejected: {(proc.stderr or '').strip()}")
    if ok:
        logger.info(f"Backlight (xrandr software dim) set {pct}%")
    return ok


def _xrandr_connected_outputs(timeout: float = 5.0) -> list[str]:
    try:
        proc = subprocess.run(
            ["xrandr", "--query"], timeout=timeout, capture_output=True, text=True
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0:
        return []
    outputs = []
    for line in proc.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "connected":
            outputs.append(parts[0])
    return outputs


class BacklightController:
    """Best-effort display brightness with full fallback chain."""

    def __init__(
        self,
        sysfs_root: Path = SYSFS_BACKLIGHT_ROOT,
        xrandr_output: Optional[str] = None,
        enable_ddcutil: bool = True,
        enable_xrandr: bool = True,
    ):
        self._sysfs_root = sysfs_root
        self._xrandr_output = xrandr_output
        self._enable_ddcutil = enable_ddcutil
        self._enable_xrandr = enable_xrandr
        self._sysfs_device = find_sysfs_device(sysfs_root)
        if self._sysfs_device is not None:
            self.method = f"sysfs:{self._sysfs_device.name}"
        elif enable_ddcutil and shutil.which("ddcutil") is not None:
            # ddcutil present; actual monitor support proven at set time.
            self.method = "ddcutil"
        elif (
            enable_xrandr
            and shutil.which("xrandr") is not None
            and os.environ.get("DISPLAY")
            and os.environ.get("QT_QPA_PLATFORM") != "eglfs"
        ):
            self.method = "xrandr"
        else:
            self.method = "none"

    @property
    def available(self) -> bool:
        """True when some hardware/software path is (likely) usable."""
        return self.method != "none"

    def set_percent(self, percent: int) -> bool:
        """Apply brightness 10..100%. Never raises; False = UI-only."""
        pct = max(MIN_PERCENT, min(MAX_PERCENT, int(percent)))
        # Always try sysfs first (re-scan: device can appear late on boot).
        dev = self._sysfs_device or find_sysfs_device(self._sysfs_root)
        if dev is not None:
            self._sysfs_device = dev
            self.method = f"sysfs:{dev.name}"
            return set_sysfs(dev, pct)
        if self._enable_ddcutil and set_ddcutil(pct):
            self.method = "ddcutil"
            return True
        if self._enable_xrandr and set_xrandr(pct, output=self._xrandr_output):
            self.method = "xrandr"
            return True
        logger.debug(f"Backlight {pct}% has no hardware path (UI-only)")
        return False

    def get_percent(self) -> Optional[int]:
        """Read current sysfs brightness as percent, or None if unknown."""
        dev = self._sysfs_device or find_sysfs_device(self._sysfs_root)
        if dev is None:
            return None
        try:
            raw = int((dev.path / "brightness").read_text().strip())
            return max(MIN_PERCENT, min(MAX_PERCENT, round(raw * 100.0 / dev.max_brightness)))
        except (OSError, ValueError):
            return None
