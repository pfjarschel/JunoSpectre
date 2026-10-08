"""Wi-Fi management for the Juno Spectre appliance (NetworkManager / nmcli).

The System screen used to show a hard-coded SSID/IP placeholder. This module
provides the real backend: connection status, nearby-network scans, connect /
disconnect / forget, and radio on/off — all via ``nmcli`` terse output so it
works on Raspberry Pi OS (Bookworm, NetworkManager) and degrades gracefully
on desktops without Wi-Fi or without nmcli (mock/dev machines, CI).

All subprocess access goes through an injectable ``runner`` so unit tests can
fake nmcli without hardware.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Callable, Optional

logger = logging.getLogger(__name__)

NMCLI_TIMEOUT = 8
SCAN_TIMEOUT = 25
CONNECT_TIMEOUT = 30

# Matches `signal: -48 dBm` in `iw dev <iface> link` output.
_IW_SIGNAL_RE = re.compile(r"^\s*signal:\s*(-?\d+)\s*dBm", re.MULTILINE)
_IW_SSID_RE = re.compile(r"^\s*SSID:\s*(.+?)\s*$", re.MULTILINE)
_IPV4_RE = re.compile(r"(\d{1,3}(?:\.\d{1,3}){3})(?:/\d+)?")


def quality_label(signal_pct: Optional[int]) -> str:
    """Human quality bucket from a 0-100 signal percent (nmcli SIGNAL)."""
    if signal_pct is None or signal_pct < 0:
        return "—"
    if signal_pct >= 75:
        return "EXCELLENT"
    if signal_pct >= 55:
        return "GOOD"
    if signal_pct >= 35:
        return "FAIR"
    if signal_pct > 0:
        return "WEAK"
    return "NO SIGNAL"


def _split_terse(line: str) -> list[str]:
    """Split an nmcli ``-t`` (colon-separated) line honouring ``\\:`` escapes."""
    # Split on colons not preceded by a backslash, then unescape.
    parts = re.split(r"(?<!\\):", line.rstrip("\n"))
    out = []
    for p in parts:
        out.append(p.replace("\\:", ":").replace("\\\\", "\\"))
    return out


@dataclass
class WifiNetwork:
    ssid: str
    signal: int = 0  # 0-100 percent (nmcli SIGNAL)
    security: str = ""  # e.g. "WPA2", "WPA3", "" = open
    in_use: bool = False

    @property
    def secured(self) -> bool:
        s = (self.security or "").strip()
        return bool(s) and s != "--"

    @property
    def quality(self) -> str:
        return quality_label(self.signal)

    def to_dict(self) -> dict:
        return {
            "ssid": self.ssid,
            "signal": int(self.signal),
            "security": self.security or ("OPEN" if not self.secured else self.security),
            "secured": self.secured,
            "inUse": self.in_use,
            "quality": self.quality,
        }


@dataclass
class WifiStatus:
    available: bool = False  # nmcli + a wifi iface exist
    enabled: bool = False  # radio on
    connected: bool = False
    ssid: str = ""
    signal: Optional[int] = None  # 0-100 percent, None when unknown
    signal_dbm: Optional[int] = None  # from `iw link`, when connected
    ip: str = ""
    iface: str = ""
    state: str = ""  # raw nmcli device STATE, e.g. "connected"
    error: str = ""

    @property
    def quality(self) -> str:
        return quality_label(self.signal)

    @property
    def signal_text(self) -> str:
        if not self.connected:
            return "—"
        parts = []
        if self.signal is not None and self.signal >= 0:
            parts.append(f"{self.signal}%")
        if self.signal_dbm is not None:
            parts.append(f"{self.signal_dbm} dBm")
        if parts:
            return " • ".join(parts)
        return "—"

    @property
    def status_text(self) -> str:
        if not self.available:
            return "NO WI-FI ADAPTER"
        if not self.enabled:
            return "WI-FI RADIO OFF"
        if self.connected and self.ssid:
            return f"CONNECTED • {self.ssid}"
        if self.connected:
            return "CONNECTED"
        return "DISCONNECTED"

    @property
    def detail_text(self) -> str:
        """Second-line detail for the System card, e.g. IP + signal + quality."""
        if not self.available:
            return self.error or "nmcli not found / no wireless interface"
        if not self.enabled:
            return "Turn the radio on to scan & connect"
        if self.connected:
            bits = []
            if self.ip:
                bits.append(f"IP: {self.ip}")
            sig = self.signal_text
            if sig != "—":
                bits.append(f"SIGNAL: {sig} ({self.quality})")
            else:
                bits.append(self.state.upper() if self.state else "CONNECTED")
            return " • ".join(bits) if bits else "CONNECTED"
        return "Not connected — open MANAGE to join a network"

    def to_dict(self) -> dict:
        return {
            "available": self.available,
            "enabled": self.enabled,
            "connected": self.connected,
            "ssid": self.ssid,
            "signal": self.signal if self.signal is not None else -1,
            "signalDbm": self.signal_dbm if self.signal_dbm is not None else 0,
            "hasDbm": self.signal_dbm is not None,
            "signalText": self.signal_text,
            "quality": self.quality,
            "ip": self.ip,
            "iface": self.iface,
            "state": self.state,
            "statusText": self.status_text,
            "detailText": self.detail_text,
            "error": self.error,
        }


# Runner signature: (argv, timeout) -> CompletedProcess-like with
# .returncode / .stdout / .stderr. Injected in tests.
Runner = Callable[..., subprocess.CompletedProcess]


def _default_runner(argv: list[str], timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True, timeout=timeout)


class WifiError(RuntimeError):
    """Raised when an nmcli operation fails with a human-readable message."""


class WifiManager:
    """Thin wrapper around nmcli with an injectable subprocess runner."""

    def __init__(self, runner: Optional[Runner] = None):
        self._run: Runner = runner or _default_runner

    # -- low level ------------------------------------------------------
    def _nmcli(self, *args: str, timeout: int = NMCLI_TIMEOUT) -> subprocess.CompletedProcess:
        if shutil.which("nmcli") is None:
            raise WifiError("nmcli not found on this system")
        try:
            return self._run(["nmcli", *args], timeout=timeout)
        except FileNotFoundError as exc:
            raise WifiError("nmcli not found on this system") from exc
        except subprocess.TimeoutExpired as exc:
            raise WifiError(f"nmcli {' '.join(args)} timed out") from exc
        except OSError as exc:
            raise WifiError(str(exc)) from exc

    # -- queries --------------------------------------------------------
    def wifi_iface(self) -> str:
        """First wireless device name (e.g. wlan0), or '' when none."""
        proc = self._nmcli("-t", "-f", "DEVICE,TYPE", "dev", "status")
        if proc.returncode != 0:
            raise WifiError((proc.stderr or proc.stdout or "dev status failed").strip())
        for line in proc.stdout.splitlines():
            parts = _split_terse(line)
            if len(parts) >= 2 and parts[1].strip() in ("wifi", "wlan"):
                if parts[0].strip():
                    return parts[0].strip()
        return ""

    def is_radio_enabled(self) -> bool:
        proc = self._nmcli("radio", "wifi")
        if proc.returncode != 0:
            raise WifiError((proc.stderr or proc.stdout or "radio query failed").strip())
        return proc.stdout.strip().lower().startswith("enabled")

    def _active_wifi_connection(self, iface: str) -> str:
        """Profile/SSID of the active wifi connection on iface, or ''."""
        proc = self._nmcli(
            "-t", "-f", "NAME,TYPE,DEVICE", "connection", "show", "--active"
        )
        if proc.returncode != 0:
            return ""
        for line in proc.stdout.splitlines():
            parts = _split_terse(line)
            if len(parts) >= 3 and parts[1].strip() == "802-11-wireless":
                if not iface or parts[2].strip() in (iface, ""):
                    return parts[0].strip()
        return ""

    def _iface_ip(self, iface: str) -> str:
        proc = self._nmcli("-t", "-f", "IP4.ADDRESS", "dev", "show", iface)
        if proc.returncode != 0:
            return ""
        m = _IPV4_RE.search(proc.stdout or "")
        return m.group(1) if m else ""

    def _iface_state(self, iface: str) -> tuple[str, str]:
        """(state, connection) for iface from `dev status`, e.g. ('connected', ssid)."""
        proc = self._nmcli("-t", "-f", "DEVICE,STATE,CONNECTION", "dev", "status")
        if proc.returncode != 0:
            return "", ""
        for line in proc.stdout.splitlines():
            parts = _split_terse(line)
            if len(parts) >= 2 and parts[0].strip() == iface:
                state = parts[1].strip() if len(parts) > 1 else ""
                conn = parts[2].strip() if len(parts) > 2 else ""
                # Normalise "connected (externally)" etc.
                if state.startswith("connected"):
                    state = "connected"
                return state, conn
        return "", ""

    def _iw_link(self, iface: str) -> tuple[str, Optional[int]]:
        """(ssid, signal_dbm) from `iw dev <iface> link`; ('', None) when down."""
        if shutil.which("iw") is None:
            return "", None
        try:
            proc = self._run(["iw", "dev", iface, "link"], timeout=NMCLI_TIMEOUT)
        except (OSError, subprocess.TimeoutExpired) as e:
            logger.debug(f"iw link failed: {e}")
            return "", None
        out = getattr(proc, "stdout", "") or ""
        if "Not connected" in out:
            return "", None
        ssid_m = _IW_SSID_RE.search(out)
        sig_m = _IW_SIGNAL_RE.search(out)
        ssid = ssid_m.group(1).strip() if ssid_m else ""
        dbm = int(sig_m.group(1)) if sig_m else None
        return ssid, dbm

    def status(self) -> WifiStatus:
        """Best-effort snapshot; never raises — failures land in .error."""
        try:
            iface = self.wifi_iface()
        except WifiError as e:
            return WifiStatus(available=False, error=str(e))
        if not iface:
            return WifiStatus(available=False, error="no wireless interface found")
        try:
            enabled = self.is_radio_enabled()
        except WifiError as e:
            return WifiStatus(available=True, iface=iface, error=str(e))
        if not enabled:
            return WifiStatus(available=True, enabled=False, iface=iface)
        state, conn = self._iface_state(iface)
        active = self._active_wifi_connection(iface)
        ssid = active or conn
        connected = state == "connected" and bool(ssid) and ssid != "--"
        ip = self._iface_ip(iface) if connected else ""
        signal_pct: Optional[int] = None
        signal_dbm: Optional[int] = None
        if connected:
            iw_ssid, iw_dbm = self._iw_link(iface)
            if iw_ssid and not ssid:
                ssid = iw_ssid
            signal_dbm = iw_dbm
            # Signal % comes from the scan cache (cheap, no rescan).
            try:
                for net in self.scan(rescan=False):
                    if net.ssid == ssid:
                        signal_pct = net.signal
                        break
                    if net.in_use:
                        signal_pct = net.signal
            except WifiError as e:
                logger.debug(f"wifi signal lookup failed: {e}")
        return WifiStatus(
            available=True,
            enabled=True,
            connected=connected,
            ssid=ssid if connected else "",
            signal=signal_pct,
            signal_dbm=signal_dbm,
            ip=ip,
            iface=iface,
            state=state,
        )

    def scan(self, rescan: bool = True) -> list[WifiNetwork]:
        """Nearby networks, strongest first, de-duplicated by SSID.

        Empty (hidden) SSIDs are skipped — use connect() with an explicit
        SSID to join those.
        """
        flag = "yes" if rescan else "no"
        proc = self._nmcli(
            "-t",
            "-f",
            "IN-USE,SSID,SIGNAL,SECURITY",
            "dev",
            "wifi",
            "list",
            "--rescan",
            flag,
            timeout=SCAN_TIMEOUT if rescan else NMCLI_TIMEOUT,
        )
        if proc.returncode != 0:
            raise WifiError(
                (proc.stderr or proc.stdout or "Wi-Fi scan failed").strip()
            )
        best: dict[str, WifiNetwork] = {}
        for line in proc.stdout.splitlines():
            if not line.strip():
                continue
            parts = _split_terse(line)
            while len(parts) < 4:
                parts.append("")
            in_use = parts[0].strip() == "*"
            ssid = parts[1].strip()
            if not ssid:
                continue  # hidden network
            try:
                signal = max(0, min(100, int(parts[2].strip() or 0)))
            except ValueError:
                signal = 0
            security = parts[3].strip()
            prev = best.get(ssid)
            if prev is None or signal > prev.signal or (in_use and not prev.in_use):
                best[ssid] = WifiNetwork(
                    ssid=ssid, signal=signal, security=security, in_use=in_use
                )
            elif prev is not None and in_use:
                prev.in_use = True
        nets = list(best.values())
        nets.sort(key=lambda n: (n.in_use, n.signal), reverse=True)
        return nets

    # -- actions --------------------------------------------------------
    def connect(
        self, ssid: str, password: str = "", iface: str = ""
    ) -> dict:
        """Join a network. Returns {'ssid', 'changed'}; raises WifiError."""
        ssid = (ssid or "").strip()
        if not ssid:
            raise WifiError("select a network first")
        if not iface:
            try:
                iface = self.wifi_iface()
            except WifiError:
                iface = ""
        argv = ["dev", "wifi", "connect", ssid]
        if password:
            argv += ["password", password]
        if iface:
            argv += ["ifname", iface]
        proc = self._nmcli(*argv, timeout=CONNECT_TIMEOUT)
        if proc.returncode != 0:
            msg = (proc.stderr or proc.stdout or "connection failed").strip()
            raise WifiError(_friendly_connect_error(msg))
        return {"ssid": ssid, "changed": True}

    def disconnect(self, iface: str = "") -> dict:
        if not iface:
            try:
                iface = self.wifi_iface()
            except WifiError:
                iface = ""
        if not iface:
            raise WifiError("no wireless interface found")
        proc = self._nmcli("dev", "disconnect", iface)
        if proc.returncode != 0:
            raise WifiError(
                (proc.stderr or proc.stdout or "disconnect failed").strip()
            )
        return {"iface": iface, "changed": True}

    def forget(self, ssid: str) -> dict:
        """Delete saved profile(s) for an SSID. Raises WifiError when none."""
        ssid = (ssid or "").strip()
        if not ssid:
            raise WifiError("select a network first")
        proc = self._nmcli("-t", "-f", "NAME,UUID,TYPE", "connection", "show")
        if proc.returncode != 0:
            raise WifiError((proc.stderr or proc.stdout or "lookup failed").strip())
        targets: list[str] = []
        for line in proc.stdout.splitlines():
            parts = _split_terse(line)
            if len(parts) >= 3 and parts[2].strip() == "802-11-wireless":
                if parts[0].strip() == ssid and parts[1].strip():
                    targets.append(parts[1].strip())  # delete by UUID (exact)
        if not targets:
            raise WifiError(f"no saved profile for '{ssid}'")
        for uuid in targets:
            proc = self._nmcli("connection", "delete", uuid)
            if proc.returncode != 0:
                raise WifiError(
                    (proc.stderr or proc.stdout or "forget failed").strip()
                )
        return {"ssid": ssid, "changed": True}

    def set_enabled(self, enabled: bool) -> dict:
        proc = self._nmcli("radio", "wifi", "on" if enabled else "off")
        if proc.returncode != 0:
            raise WifiError((proc.stderr or proc.stdout or "radio change failed").strip())
        return {"enabled": bool(enabled)}


def _friendly_connect_error(msg: str) -> str:
    """Map nmcli stderr to a short touch-screen friendly message."""
    low = msg.lower()
    if "secrets were required" in low or "no secrets" in low or "password" in low and "required" in low:
        return "Wrong or missing password"
    if "not found" in low and "network" in low:
        return "Network not found — rescan and retry"
    if "timeout" in low:
        return "Connection timed out — check password / move closer"
    if "not authorized" in low or "permission" in low or "not permitted" in low:
        return "Not permitted — appliance needs NetworkManager permission"
    if "already" in low and "activ" in low:
        return "Already connecting — wait a moment"
    # Keep it to one line for the small display.
    first = msg.splitlines()[0] if msg else "Connection failed"
    return first[:120]
