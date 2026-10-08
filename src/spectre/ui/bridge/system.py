"""System bridge mixin: telemetry, updater, wifi, backlight, and power management."""

from __future__ import annotations

import logging
import threading
import time

from PyQt6.QtCore import pyqtProperty, pyqtSignal, pyqtSlot

from ...core.updater import UpdaterError
from ...core.wifi import WifiStatus
from .base import BridgeBaseMixin

logger = logging.getLogger(__name__)


class SystemBridgeMixin(BridgeBaseMixin):
    """Appliance update, Wi-Fi networking, host telemetry, and power actions."""

    versionChanged = pyqtSignal(str)
    updaterBusyChanged = pyqtSignal(bool)
    updaterLogChanged = pyqtSignal(str)
    updateAvailableChanged = pyqtSignal(bool)
    latestVersionChanged = pyqtSignal(str)
    updateAppliedChanged = pyqtSignal(bool)
    wifiChanged = pyqtSignal()
    wifiNetworksChanged = pyqtSignal()
    wifiBusyChanged = pyqtSignal(bool)
    brightnessChanged = pyqtSignal(int)
    powerActionChanged = pyqtSignal(str)
    telemetryChanged = pyqtSignal()


    def _poll_telemetry(self) -> None:
        """Refresh host stats; timer-gated to the SYSTEM view only."""
        if self._active_view != "SYSTEM":
            return
        try:
            from ...core.telemetry import read_telemetry

            snap, self._telemetry_prev_cpu = read_telemetry(self._telemetry_prev_cpu)
            self._telemetry = snap
            self.telemetryChanged.emit()
        except Exception as e:
            logger.debug(f"Telemetry poll failed: {e}")
        # Wi-Fi status is cheap to query but involves subprocesses, so refresh
        # it on a slower cadence (~6 s) and only when no wifi task is running.
        try:
            now = time.monotonic()
            if not self._wifi_busy and now - self._wifi_last_status_poll > 6.0:
                self._wifi_last_status_poll = now
                self.refreshWifiStatus()
        except Exception as e:
            logger.debug(f"Wi-Fi background poll failed: {e}")

    def _update_telemetry_polling(self) -> None:
        """Start/stop the 1.5 s telemetry timer based on active view."""
        try:
            if self._active_view == "SYSTEM":
                self._poll_telemetry()  # immediate refresh, no stale mock
                if not self._telemetry_timer.isActive():
                    self._telemetry_timer.start()
                # Entering SYSTEM: make sure wifi state is fresh; auto-scan
                # once so the network list is not empty on first open.
                try:
                    self.refreshWifiStatus()
                    if not self._wifi_networks:
                        self.scanWifi(rescan=False)
                except Exception as e:
                    logger.debug(f"Wi-Fi enter-view refresh failed: {e}")
            else:
                if self._telemetry_timer.isActive():
                    self._telemetry_timer.stop()
        except Exception as e:
            logger.debug(f"Telemetry timer update failed: {e}")

    @pyqtProperty(str, notify=latestVersionChanged)
    def latestVersion(self) -> str:
        return self._latest_version

    @pyqtProperty(bool, notify=updateAppliedChanged)
    def updateApplied(self) -> bool:
        return self._update_applied

    @pyqtProperty(int, notify=brightnessChanged)
    def brightness(self) -> int:
        return self._brightness

    @pyqtProperty(str, notify=brightnessChanged)
    def brightnessMethod(self) -> str:
        return str(getattr(getattr(self, "_backlight", None), "method", "none"))

    @pyqtProperty(str, notify=telemetryChanged)
    def cpuLoadText(self) -> str:
        return f"{self._telemetry.cpu_percent:.0f}%"

    @pyqtProperty(float, notify=telemetryChanged)
    def cpuLoadNorm(self) -> float:
        return max(0.0, min(1.0, self._telemetry.cpu_percent / 100.0))

    @pyqtProperty(str, notify=telemetryChanged)
    def cpuTempText(self) -> str:
        t = self._telemetry.cpu_temp_c
        return f"{t:.1f} °C" if t is not None else "N/A"

    @pyqtProperty(float, notify=telemetryChanged)
    def cpuTempNorm(self) -> float:
        t = self._telemetry.cpu_temp_c
        return max(0.0, min(1.0, t / 100.0)) if t is not None else 0.0

    @pyqtProperty(str, notify=telemetryChanged)
    def ramText(self) -> str:
        return f"{self._telemetry.mem_used_mb} MB / {self._telemetry.mem_total_mb} MB"

    @pyqtProperty(float, notify=telemetryChanged)
    def ramNorm(self) -> float:
        total = self._telemetry.mem_total_mb
        if total <= 0:
            return 0.0
        return max(0.0, min(1.0, self._telemetry.mem_used_mb / total))

    @pyqtProperty(str, notify=telemetryChanged)
    def diskText(self) -> str:
        return f"{self._telemetry.disk_free_gb:.1f} GB FREE"

    @pyqtProperty(float, notify=telemetryChanged)
    def diskNorm(self) -> float:
        total = self._telemetry.disk_total_gb
        if total <= 0:
            return 0.0
        used = max(0.0, total - self._telemetry.disk_free_gb)
        return max(0.0, min(1.0, used / total))

    @pyqtProperty(str, notify=telemetryChanged)
    def controlRateText(self) -> str:
        try:
            hz = float(getattr(self.engine, "max_update_hz", 50.0))
        except (TypeError, ValueError):
            hz = 50.0
        if hz <= 0:
            hz = 50.0
        return f"{hz:.0f} Hz SysEx dispatch ({1000.0 / hz:.0f} ms)"

    @pyqtProperty(str, notify=telemetryChanged)
    def midiLinkText(self) -> str:
        try:
            juno = self.juno
            midi = getattr(juno, "midi", None) if juno is not None else None
            out = getattr(midi, "juno_out", None) if midi is not None else None
            if out is None or getattr(out, "closed", True):
                return "OFFLINE"
            name = str(getattr(out, "name", "") or "").strip()
            return f"USB-MIDI CONNECTED ({name})" if name else "USB-MIDI CONNECTED"
        except Exception:
            return "OFFLINE"

    @pyqtProperty(bool, notify=wifiChanged)
    def wifiAvailable(self) -> bool:
        return bool(self._wifi_status.available)

    @pyqtProperty(bool, notify=wifiChanged)
    def wifiEnabled(self) -> bool:
        return bool(self._wifi_status.enabled)

    @pyqtProperty(bool, notify=wifiChanged)
    def wifiConnected(self) -> bool:
        return bool(self._wifi_status.connected)

    @pyqtProperty(str, notify=wifiChanged)
    def wifiSsid(self) -> str:
        return str(self._wifi_status.ssid or "")

    @pyqtProperty(str, notify=wifiChanged)
    def wifiIp(self) -> str:
        return str(self._wifi_status.ip or "")

    @pyqtProperty(int, notify=wifiChanged)
    def wifiSignal(self) -> int:
        s = self._wifi_status.signal
        return int(s) if s is not None else -1

    @pyqtProperty(str, notify=wifiChanged)
    def wifiSignalText(self) -> str:
        return str(self._wifi_status.signal_text)

    @pyqtProperty(str, notify=wifiChanged)
    def wifiQuality(self) -> str:
        return str(self._wifi_status.quality)

    @pyqtProperty(str, notify=wifiChanged)
    def wifiStatusText(self) -> str:
        return str(self._wifi_status.status_text)

    @pyqtProperty(str, notify=wifiChanged)
    def wifiDetailText(self) -> str:
        return str(self._wifi_status.detail_text)

    @pyqtProperty(str, notify=wifiChanged)
    def wifiIface(self) -> str:
        return str(self._wifi_status.iface or "")

    @pyqtProperty(str, notify=wifiChanged)
    def wifiError(self) -> str:
        # Explicit action errors take precedence over the status snapshot.
        if self._wifi_error:
            return str(self._wifi_error)
        return str(self._wifi_status.error or "")

    @pyqtProperty(str, notify=wifiNetworksChanged)
    def wifiLastScan(self) -> str:
        return str(self._wifi_last_scan or "")

    @pyqtProperty("QVariantList", notify=wifiNetworksChanged)
    def wifiNetworks(self) -> list:
        return list(self._wifi_networks)

    @pyqtProperty(bool, notify=wifiBusyChanged)
    def wifiBusy(self) -> bool:
        return bool(self._wifi_busy)

    @pyqtProperty(str, notify=versionChanged)
    def version(self) -> str:
        return self._version

    @pyqtProperty(bool, notify=updaterBusyChanged)
    def updaterBusy(self) -> bool:
        return self._updater_busy

    @pyqtProperty(str, notify=updaterLogChanged)
    def updaterLog(self) -> str:
        return self._updater_log

    @pyqtProperty(bool, notify=updateAvailableChanged)
    def updateAvailable(self) -> bool:
        return self._update_available

    @pyqtSlot()
    def checkForUpdates(self) -> None:
        """Fetch origin tags and publish latest release availability to the UI."""

        def on_ok(info: dict) -> None:
            if self._latest_version != info["latest"]:
                self._latest_version = info["latest"]
                self.latestVersionChanged.emit(self._latest_version)
            if self._update_available != info["available"]:
                self._update_available = info["available"]
                self.updateAvailableChanged.emit(self._update_available)
            if info["available"]:
                self._set_updater_log(
                    f"UPDATE AVAILABLE • {info['current']} → {info['latest']} "
                    f"({info['behind_commits']} COMMITS)"
                )
            else:
                self._set_updater_log(f"UP TO DATE • {info['current']}")
            self._set_update_applied(False)
            self._set_updater_busy(False)

        self._start_updater_task("git fetch --tags", lambda: self._updater.check(), on_ok)

    @pyqtSlot()
    def applyLatestRelease(self) -> None:
        """Check out the newest release tag, then require an explicit app restart."""

        def on_ok(result: dict) -> None:
            self._update_available = False
            self.updateAvailableChanged.emit(False)
            if result["changed"]:
                self._set_updater_log(
                    f"RELEASE {result['to']} INSTALLED ({result['from']} → {result['to']}) "
                    f"• TAP RESTART APPLICATION"
                )
                self._set_update_applied(True)
            else:
                self._set_updater_log(f"ALREADY ON RELEASE {result['to']}")
            self._set_updater_busy(False)

        self._start_updater_task("git checkout release", self._updater.apply, on_ok)

    @pyqtSlot()
    def rollbackRelease(self) -> None:
        """Fall back to the previous release tag (detached HEAD checkout)."""

        def on_ok(result: dict) -> None:
            self._set_updater_log(
                f"ROLLED BACK {result['from']} → {result['to']} • TAP RESTART APPLICATION"
            )
            self._update_available = False
            self.updateAvailableChanged.emit(False)
            self._set_update_applied(True)
            self._set_updater_busy(False)

        self._start_updater_task("git rollback", self._updater.rollback, on_ok)

    def _set_wifi_busy(self, val: bool) -> None:
        if self._wifi_busy != val:
            self._wifi_busy = val
            try:
                self.wifiBusyChanged.emit(val)
            except RuntimeError:
                pass  # bridge already torn down (tests / shutdown)

    def _set_wifi_error(self, msg: str) -> None:
        if self._wifi_error != msg:
            self._wifi_error = msg
            try:
                self.wifiChanged.emit()
            except RuntimeError:
                pass  # bridge already torn down (tests / shutdown)

    def _apply_wifi_status(self, status: WifiStatus) -> None:
        self._wifi_status = status
        # A fresh snapshot clears stale action errors unless the snapshot
        # itself carries one.
        if not status.error:
            self._wifi_error = ""
        try:
            self.wifiChanged.emit()
        except RuntimeError:
            pass  # bridge already torn down (tests / shutdown)

    def _emit_wifi_networks(self) -> None:
        try:
            self.wifiNetworksChanged.emit()
        except RuntimeError:
            pass  # bridge already torn down (tests / shutdown)

    def _start_wifi_task(self, work, on_success) -> bool:
        """Run blocking nmcli work on a worker thread. False when busy."""
        if self._wifi_busy:
            logger.debug("Wi-Fi task already running, ignoring request")
            return False
        self._set_wifi_busy(True)
        self._set_wifi_error("")

        def runner() -> None:
            try:
                result = work()
            except Exception as e:
                # Includes RuntimeError when the bridge was torn down
                # mid-flight (tests / shutdown): helpers swallow emit errors.
                logger.warning(f"Wi-Fi task failed: {e}")
                self._set_wifi_error(str(e))
                self._set_wifi_busy(False)
                return
            try:
                on_success(result)
            except RuntimeError:
                pass  # bridge torn down mid-flight; nothing to update
            except Exception as e:
                logger.exception("Wi-Fi task follow-up crashed")
                self._set_wifi_error(str(e))
            finally:
                try:
                    self._set_wifi_busy(False)
                except RuntimeError:
                    pass

        threading.Thread(target=runner, daemon=True).start()
        return True

    @pyqtSlot()
    def refreshWifiStatus(self) -> None:
        """Refresh connection status snapshot (SSID, IP, signal)."""

        def on_ok(status: WifiStatus) -> None:
            self._apply_wifi_status(status)
            if status.error and not status.available:
                self._set_wifi_error(status.error)

        self._start_wifi_task(lambda: self._wifi.status(), on_ok)

    @pyqtSlot()
    @pyqtSlot(bool)
    def scanWifi(self, rescan: bool = True) -> None:
        """Scan nearby networks into wifiNetworks (strongest first)."""
        import datetime

        do_rescan = bool(rescan)

        def on_ok(nets) -> None:
            self._wifi_networks = [n.to_dict() for n in nets]
            self._emit_wifi_networks()
            try:
                self._wifi_last_scan = datetime.datetime.now().strftime("%H:%M:%S")
            except Exception:
                self._wifi_last_scan = "JUST NOW"
            self._emit_wifi_networks()
            # A scan also tells us which network is in use — fold that into
            # the status snapshot without a full re-poll when possible.
            try:
                for n in nets:
                    if n.in_use:
                        st = self._wifi_status
                        if st.ssid != n.ssid or st.signal != n.signal:
                            st.ssid = n.ssid
                            st.signal = n.signal
                            st.connected = True
                            self._apply_wifi_status(st)
                        break
            except Exception as e:
                logger.debug(f"Wi-Fi scan status fold-in failed: {e}")

        def work():
            from ...core.wifi import WifiError as _WE

            try:
                return self._wifi.scan(rescan=do_rescan)
            except _WE:
                if do_rescan:
                    # A forced rescan can fail on busy drivers; fall back to
                    # the cached scan so the list is still useful.
                    logger.debug("Wi-Fi rescan failed, retrying from cache")
                    return self._wifi.scan(rescan=False)
                raise

        self._start_wifi_task(work, on_ok)

    @pyqtSlot(str, str)
    def connectWifi(self, ssid: str, password: str = "") -> None:
        """Join a network, then refresh status + network list."""
        ssid = (ssid or "").strip()

        def on_ok(_result: dict) -> None:
            self._set_wifi_error("")
            # Re-poll status synchronously in this worker so the UI flips
            # to CONNECTED without waiting for the 6 s background poll.
            try:
                self._apply_wifi_status(self._wifi.status())
            except Exception as e:
                logger.debug(f"Wi-Fi post-connect status failed: {e}")
            try:
                nets = self._wifi.scan(rescan=False)
                self._wifi_networks = [n.to_dict() for n in nets]
                self._emit_wifi_networks()
            except Exception as e:
                logger.debug(f"Wi-Fi post-connect scan failed: {e}")

        self._start_wifi_task(lambda: self._wifi.connect(ssid, password or ""), on_ok)

    @pyqtSlot()
    def disconnectWifi(self) -> None:
        """Drop the current Wi-Fi connection (profiles are kept)."""

        def on_ok(_result: dict) -> None:
            try:
                self._apply_wifi_status(self._wifi.status())
            except Exception as e:
                logger.debug(f"Wi-Fi post-disconnect status failed: {e}")

        self._start_wifi_task(lambda: self._wifi.disconnect(), on_ok)

    @pyqtSlot(str)
    def forgetWifi(self, ssid: str) -> None:
        """Delete the saved profile for an SSID, then refresh the list."""
        ssid = (ssid or "").strip()

        def on_ok(_result: dict) -> None:
            try:
                nets = self._wifi.scan(rescan=False)
                self._wifi_networks = [n.to_dict() for n in nets]
                self._emit_wifi_networks()
            except Exception as e:
                logger.debug(f"Wi-Fi post-forget scan failed: {e}")
            try:
                self._apply_wifi_status(self._wifi.status())
            except Exception as e:
                logger.debug(f"Wi-Fi post-forget status failed: {e}")

        self._start_wifi_task(lambda: self._wifi.forget(ssid), on_ok)

    @pyqtSlot(bool)
    def setWifiEnabled(self, enabled: bool) -> None:
        """Turn the Wi-Fi radio on/off, then refresh status."""

        def on_ok(_result: dict) -> None:
            try:
                self._apply_wifi_status(self._wifi.status())
            except Exception as e:
                logger.debug(f"Wi-Fi post-radio status failed: {e}")
            if enabled:
                try:
                    nets = self._wifi.scan(rescan=False)
                    self._wifi_networks = [n.to_dict() for n in nets]
                    self._emit_wifi_networks()
                except Exception as e:
                    logger.debug(f"Wi-Fi post-radio scan failed: {e}")

        self._start_wifi_task(lambda: self._wifi.set_enabled(bool(enabled)), on_ok)

    @pyqtSlot(int)
    def setBrightness(self, val: int) -> None:
        clamped = max(10, min(100, int(val)))
        if self._brightness != clamped:
            self._brightness = clamped
            self.brightnessChanged.emit(self._brightness)
        try:
            backlight = getattr(self, "_backlight", None)
            if backlight is not None:
                if not backlight.set_percent(clamped):
                    logger.debug(
                        f"Brightness {clamped}% UI-only "
                        f"(method={getattr(backlight, 'method', 'none')})"
                    )
        except Exception as e:
            logger.debug(f"Brightness hardware apply failed: {e}")

    @pyqtSlot()
    def restartApp(self) -> None:
        """Graceful in-place restart: silence synth, close MIDI, then exec.

        Does NOT quit first — os.execv() replaces the process on success and
        never returns. If exec fails the app keeps running instead of
        black-screening the appliance.
        """
        import os
        import sys

        exe = sys.executable
        if not exe or not os.path.exists(exe):
            logger.error(f"Restart aborted: invalid python executable {exe!r}")
            return
        logger.info("Restarting application...")
        self.powerActionChanged.emit("restarting")
        self._perform_appliance_cleanup("restart")
        argv = [exe] + sys.argv
        try:
            os.execv(exe, argv)
        except Exception as e:
            logger.error(f"Restart execv failed ({argv}): {e}")
            self.powerActionChanged.emit("")
            try:
                if hasattr(self, "_timer") and not self._timer.isActive():
                    self._timer.start()
            except Exception:
                pass

    @pyqtSlot()
    def rebootSystem(self) -> None:
        """Reboot the host OS (Pi appliance). Safe no-op with warning off Linux."""
        self._host_power("reboot")

    @pyqtSlot()
    def quitApp(self) -> None:
        """Quit to desktop: silence synth, close MIDI, then exit Qt loop."""
        from PyQt6.QtGui import QGuiApplication

        logger.info("Quitting application...")
        self.powerActionChanged.emit("quitting")
        self._perform_appliance_cleanup("quit")
        try:
            app = QGuiApplication.instance()
            if app:
                app.quit()
        except Exception as e:
            logger.debug(f"Qt quit failed: {e}")

    @pyqtSlot()
    def shutdownSystem(self) -> None:
        """Power off the host OS (Pi appliance). Safe no-op with warning off Linux."""
        self._host_power("poweroff")

    def _perform_appliance_cleanup(self, reason: str) -> None:
        """Best-effort graceful teardown before restart/reboot/shutdown."""
        try:
            if hasattr(self, "_timer") and self._timer.isActive():
                self._timer.stop()
        except Exception as e:
            logger.debug(f"Cleanup ({reason}): timer stop failed: {e}")
        try:
            juno = self.juno
            midi = getattr(juno, "midi", None) if juno is not None else None
            if midi is not None:
                try:
                    if hasattr(midi, "send_all_notes_off"):
                        midi.send_all_notes_off()
                except Exception as e:
                    logger.debug(f"Cleanup ({reason}): panic failed: {e}")
                try:
                    if hasattr(midi, "close"):
                        midi.close()
                except Exception as e:
                    logger.debug(f"Cleanup ({reason}): MIDI close failed: {e}")
        except Exception as e:
            logger.debug(f"Cleanup ({reason}) failed: {e}")
        try:
            for handler in logging.getLogger().handlers:
                try:
                    handler.flush()
                except Exception:
                    pass
        except Exception:
            pass

    def _host_power(self, action: str, dry_run: bool = False) -> str:
        """Shared systemctl reboot/poweroff helper. Returns outcome string.

        `dry_run=True` performs cleanup-free validation only (for tests).
        """
        import subprocess
        import sys

        if action not in ("reboot", "poweroff"):
            raise ValueError(f"Unknown power action: {action}")
        if dry_run:
            return "dry-run"
        if sys.platform != "linux":
            logger.warning(
                f"{action.upper()} ignored: host power control is Linux-only "
                f"(running on {sys.platform})."
            )
            return "unsupported-platform"
        from PyQt6.QtGui import QGuiApplication

        logger.info(f"Host {action} requested...")
        self.powerActionChanged.emit(action + "ing")
        self._perform_appliance_cleanup(action)
        cmds = [["systemctl", action], ["sudo", "-n", "systemctl", action]]
        last_err = ""
        for cmd in cmds:
            try:
                proc = subprocess.run(cmd, timeout=15, capture_output=True, text=True)
            except FileNotFoundError as e:
                last_err = str(e)
                continue
            except subprocess.TimeoutExpired:
                last_err = f"{' '.join(cmd)} timed out"
                continue
            except Exception as e:
                last_err = str(e)
                continue
            if proc.returncode == 0:
                break
            last_err = (proc.stderr or proc.stdout or f"exit {proc.returncode}").strip()
        else:
            logger.error(f"Host {action} failed: {last_err}")
            self.powerActionChanged.emit("")
            try:
                if hasattr(self, "_timer") and not self._timer.isActive():
                    self._timer.start()
            except Exception:
                pass
            return f"failed: {last_err}"
        try:
            app = QGuiApplication.instance()
            if app:
                app.quit()
        except Exception as e:
            logger.debug(f"Qt quit after {action} failed: {e}")
        return "ok"

    def _set_updater_busy(self, val: bool) -> None:
        if self._updater_busy != val:
            self._updater_busy = val
            self.updaterBusyChanged.emit(val)

    def _set_updater_log(self, msg: str) -> None:
        if self._updater_log != msg:
            self._updater_log = msg
            self.updaterLogChanged.emit(msg)

    def _set_update_applied(self, val: bool) -> None:
        if self._update_applied != val:
            self._update_applied = val
            self.updateAppliedChanged.emit(val)

    def _refresh_version(self) -> None:
        new_version = self._updater.version
        if new_version != self._version:
            self._version = new_version
            self.versionChanged.emit(self._version)

    def _start_updater_task(self, action: str, work, on_success) -> None:
        """Run a blocking git updater call on a worker thread, reporting via signals."""
        if self._updater_busy:
            logger.debug("Updater task already running, ignoring request")
            return
        self._set_updater_busy(True)
        self._set_updater_log(f"$ {action} ...")

        def finish(log_line: str) -> None:
            self._set_updater_log(log_line)
            self._set_updater_busy(False)

        def runner() -> None:
            try:
                result = work()
            except UpdaterError as e:
                logger.warning(f"Updater '{action}' failed: {e}")
                finish(f"ERROR • {str(e).upper()}")
                return
            except Exception as e:
                logger.exception(f"Updater '{action}' crashed")
                finish(f"ERROR • {str(e).upper()}")
                return
            on_success(result)
            self._refresh_version()

        threading.Thread(target=runner, daemon=True).start()


