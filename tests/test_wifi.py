"""Unit tests for the NetworkManager-backed wifi manager (fake nmcli)."""

import time

import pytest

from src.spectre.core.wifi import (
    WifiManager,
    WifiError,
    WifiNetwork,
    WifiStatus,
    quality_label,
    _split_terse,
)


def _proc(returncode=0, stdout="", stderr=""):
    from types import SimpleNamespace

    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


class FakeNmcli:
    """Maps argv-prefix to canned responses; records calls."""

    def __init__(self, routes: dict):
        # routes: tuple(argv) -> SimpleNamespace proc
        self.routes = routes
        self.calls: list[list[str]] = []

    def __call__(self, argv, timeout=8):
        self.calls.append(list(argv))
        key = tuple(argv)
        if key in self.routes:
            return self.routes[key]
        # Prefix fallback: match startswith for iw link etc.
        for route_key, proc in self.routes.items():
            if len(key) >= len(route_key) and tuple(key[: len(route_key)]) == route_key:
                return proc
        return _proc(returncode=1, stderr="unexpected call: " + " ".join(argv))


def _status_routes(*, connected=True, radio="enabled", iface="wlan0"):
    state = "connected" if connected else "disconnected"
    conn = "Studio-5GHz" if connected else ""
    active = "Studio-5GHz:802-11-wireless:wlan0" if connected else ""
    ip_out = "IP4.ADDRESS[1]:192.168.1.50/24\n" if connected else "\n"
    scan_out = (
        "*:Studio-5GHz:82:WPA2\n"
        ":Cafe-Guest:45:WPA1 WPA2\n"
        ":OpenNet:30:--\n"
        "::20:WPA2\n"  # hidden -> skipped
    )
    iw_out = (
        "Connected to aa:bb:cc:dd:ee:ff (on wlan0)\n\tSSID: Studio-5GHz\n"
        "\tsignal: -48 dBm\n\ttx bitrate: 270 Mbit/s\n"
        if connected
        else "Not connected.\n"
    )
    return {
        ("nmcli", "-t", "-f", "DEVICE,TYPE", "dev", "status"): _proc(
            stdout=f"{iface}:wifi\neth0:ethernet\n"
        ),
        ("nmcli", "radio", "wifi"): _proc(stdout=radio + "\n"),
        ("nmcli", "-t", "-f", "DEVICE,STATE,CONNECTION", "dev", "status"): _proc(
            stdout=f"{iface}:{state}:{conn}\neth0:connected:Wired\n"
        ),
        ("nmcli", "-t", "-f", "NAME,TYPE,DEVICE", "connection", "show", "--active"): _proc(
            stdout=active + "\n" if active else "\n"
        ),
        ("nmcli", "-t", "-f", "IP4.ADDRESS", "dev", "show", iface): _proc(stdout=ip_out),
        (
            "nmcli",
            "-t",
            "-f",
            "IN-USE,SSID,SIGNAL,SECURITY",
            "dev",
            "wifi",
            "list",
            "--rescan",
            "no",
        ): _proc(stdout=scan_out),
        ("iw", "dev", iface, "link"): _proc(stdout=iw_out),
    }


def test_split_terse_handles_escaped_colons():
    assert _split_terse("*:My\\:Net:80:WPA2") == ["*", "My:Net", "80", "WPA2"]
    assert _split_terse(":Cafe:45:WPA1 WPA2") == ["", "Cafe", "45", "WPA1 WPA2"]


def test_quality_buckets():
    assert quality_label(90) == "EXCELLENT"
    assert quality_label(60) == "GOOD"
    assert quality_label(40) == "FAIR"
    assert quality_label(10) == "WEAK"
    assert quality_label(None) == "—"


def test_status_connected_reports_ssid_ip_signal_dbm():
    mgr = WifiManager(runner=FakeNmcli(_status_routes(connected=True)))
    st = mgr.status()
    assert st.available and st.enabled and st.connected
    assert st.ssid == "Studio-5GHz"
    assert st.ip == "192.168.1.50"
    assert st.signal == 82
    assert st.signal_dbm == -48
    assert "192.168.1.50" in st.detail_text
    assert st.status_text.startswith("CONNECTED")


def test_status_disconnected():
    mgr = WifiManager(runner=FakeNmcli(_status_routes(connected=False)))
    st = mgr.status()
    assert st.available and st.enabled and not st.connected
    assert st.ssid == ""
    assert st.status_text == "DISCONNECTED"


def test_status_radio_off():
    mgr = WifiManager(runner=FakeNmcli(_status_routes(radio="disabled")))
    st = mgr.status()
    assert st.available and not st.enabled
    assert st.status_text == "WI-FI RADIO OFF"


def test_status_no_iface():
    routes = {
        ("nmcli", "-t", "-f", "DEVICE,TYPE", "dev", "status"): _proc(
            stdout="eth0:ethernet\n"
        ),
    }
    mgr = WifiManager(runner=FakeNmcli(routes))
    st = mgr.status()
    assert not st.available


def test_scan_dedups_and_sorts_skips_hidden():
    mgr = WifiManager(
        runner=FakeNmcli(
            {
                (
                    "nmcli",
                    "-t",
                    "-f",
                    "IN-USE,SSID,SIGNAL,SECURITY",
                    "dev",
                    "wifi",
                    "list",
                    "--rescan",
                    "yes",
                ): _proc(
                    stdout=":Cafe:40:WPA2\n:Cafe:72:WPA2\n*:Home:72:WPA2\n::50:WPA2\n"
                ),
            }
        )
    )
    nets = mgr.scan(rescan=True)
    assert [n.ssid for n in nets] == ["Home", "Cafe"]  # in-use first, hidden skipped
    assert nets[1].signal == 72  # strongest duplicate wins
    assert nets[0].in_use


def test_scan_failure_raises():
    mgr = WifiManager(
        runner=FakeNmcli(
            {
                (
                    "nmcli",
                    "-t",
                    "-f",
                    "IN-USE,SSID,SIGNAL,SECURITY",
                    "dev",
                    "wifi",
                    "list",
                    "--rescan",
                    "yes",
                ): _proc(returncode=1, stderr="scan failed"),
            }
        )
    )
    with pytest.raises(WifiError):
        mgr.scan()


def test_connect_builds_argv_with_password_and_iface():
    fake = FakeNmcli(
        {
            ("nmcli", "-t", "-f", "DEVICE,TYPE", "dev", "status"): _proc(
                stdout="wlan0:wifi\n"
            ),
            (
                "nmcli",
                "dev",
                "wifi",
                "connect",
                "Studio",
                "password",
                "s3cr3t",
                "ifname",
                "wlan0",
            ): _proc(stdout="success\n"),
        }
    )
    mgr = WifiManager(runner=fake)
    assert mgr.connect("Studio", "s3cr3t") == {"ssid": "Studio", "changed": True}
    assert any("connect" in c for c in fake.calls)


def test_connect_requires_ssid_and_surfaces_wrong_password():
    mgr = WifiManager(runner=FakeNmcli({}))
    with pytest.raises(WifiError, match="select a network"):
        mgr.connect("")
    fake = FakeNmcli(
        {
            ("nmcli", "-t", "-f", "DEVICE,TYPE", "dev", "status"): _proc(stdout="wlan0:wifi\n"),
            ("nmcli",): _proc(returncode=1, stderr="Error: Secrets were required, but not provided."),
        }
    )
    mgr2 = WifiManager(runner=fake)
    with pytest.raises(WifiError, match="Wrong or missing password"):
        mgr2.connect("Studio", "bad")


def test_forget_deletes_by_uuid():
    fake = FakeNmcli(
        {
            ("nmcli", "-t", "-f", "NAME,UUID,TYPE", "connection", "show"): _proc(
                stdout="Studio:uuid-1:802-11-wireless\nWired:uuid-2:802-3-ethernet\n"
            ),
            ("nmcli", "connection", "delete", "uuid-1"): _proc(stdout="deleted\n"),
        }
    )
    mgr = WifiManager(runner=fake)
    assert mgr.forget("Studio")["changed"] is True


def test_forget_without_profile_raises():
    fake = FakeNmcli(
        {
            ("nmcli", "-t", "-f", "NAME,UUID,TYPE", "connection", "show"): _proc(
                stdout="Other:uuid-9:802-11-wireless\n"
            ),
        }
    )
    with pytest.raises(WifiError, match="no saved profile"):
        WifiManager(runner=fake).forget("Ghost")


def test_disconnect_and_power():
    fake = FakeNmcli(
        {
            ("nmcli", "-t", "-f", "DEVICE,TYPE", "dev", "status"): _proc(stdout="wlan0:wifi\n"),
            ("nmcli", "dev", "disconnect", "wlan0"): _proc(stdout="ok\n"),
            ("nmcli", "radio", "wifi", "off"): _proc(stdout=""),
        }
    )
    mgr = WifiManager(runner=fake)
    assert mgr.disconnect()["iface"] == "wlan0"
    assert mgr.set_enabled(False) == {"enabled": False}


# -- Bridge slots ---------------------------------------------------------


class FakeWifiBackend:
    """In-memory stand-in for WifiManager driving the Bridge slots."""

    def __init__(self):
        self.connected_ssid = ""
        self.enabled = True
        self.calls: list[tuple] = []

    def status(self):
        connected = bool(self.connected_ssid)
        return WifiStatus(
            available=True,
            enabled=self.enabled,
            connected=connected,
            ssid=self.connected_ssid,
            signal=80 if connected else None,
            signal_dbm=-45 if connected else None,
            ip="192.168.1.5" if connected else "",
            iface="wlan0",
            state="connected" if connected else "disconnected",
        )

    def scan(self, rescan=True):
        nets = [
            WifiNetwork(ssid="Home", signal=80, security="WPA2", in_use=self.connected_ssid == "Home"),
            WifiNetwork(ssid="Cafe", signal=45, security="WPA1 WPA2", in_use=False),
        ]
        if self.connected_ssid == "Cafe":
            nets[1].in_use = True
        return nets

    def connect(self, ssid, password=""):
        self.calls.append(("connect", ssid, password))
        if not ssid:
            raise WifiError("select a network first")
        if ssid == "Cafe" and password != "right-horse":
            raise WifiError("Wrong or missing password")
        self.connected_ssid = ssid
        return {"ssid": ssid, "changed": True}

    def disconnect(self):
        self.calls.append(("disconnect",))
        self.connected_ssid = ""
        return {"iface": "wlan0", "changed": True}

    def forget(self, ssid):
        self.calls.append(("forget", ssid))
        if ssid not in ("Home", "Cafe"):
            raise WifiError(f"no saved profile for '{ssid}'")
        return {"ssid": ssid, "changed": True}

    def set_enabled(self, enabled):
        self.calls.append(("radio", enabled))
        self.enabled = bool(enabled)
        return {"enabled": self.enabled}


def _wait_for(cond, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if cond():
            return True
        time.sleep(0.02)
    return cond()


@pytest.fixture()
def wifi_bridge():
    from src.spectre.ui.bridge import SpectreBridge
    from src.spectre.vector.engine import VectorEngine

    bridge = SpectreBridge(VectorEngine())
    bridge._wifi = FakeWifiBackend()
    yield bridge


def test_bridge_refresh_reports_offline_initially(wifi_bridge):
    assert wifi_bridge.wifiAvailable is False  # no snapshot yet
    assert wifi_bridge.wifiBusy is False


def test_bridge_status_scan_connect_disconnect_flow(wifi_bridge):
    b = wifi_bridge
    b.refreshWifiStatus()
    assert _wait_for(lambda: not b.wifiBusy and b.wifiAvailable)
    assert b.wifiConnected is False
    assert b.wifiStatusText == "DISCONNECTED"

    b.scanWifi()
    assert _wait_for(lambda: not b.wifiBusy and len(b.wifiNetworks) == 2)
    assert b.wifiNetworks[0]["ssid"] == "Home"

    b.connectWifi("Home", "s3cret")
    assert _wait_for(lambda: not b.wifiBusy and b.wifiConnected)
    assert b.wifiSsid == "Home"
    assert b.wifiIp == "192.168.1.5"
    assert b.wifiSignal == 80
    assert "Home" in b.wifiStatusText
    assert b.wifiError == ""

    b.disconnectWifi()
    assert _wait_for(lambda: not b.wifiBusy and not b.wifiConnected)
    assert b.wifiSsid == ""


def test_bridge_connect_wrong_password_surfaces_error(wifi_bridge):
    b = wifi_bridge
    b.connectWifi("Cafe", "wrong")
    assert _wait_for(lambda: not b.wifiBusy and b.wifiError != "")
    assert "password" in b.wifiError.lower()
    assert b.wifiConnected is False


def test_bridge_forget_and_radio_toggle(wifi_bridge):
    b = wifi_bridge
    b.forgetWifi("Ghost")
    assert _wait_for(lambda: not b.wifiBusy and b.wifiError != "")
    assert "no saved profile" in b.wifiError

    b.setWifiEnabled(False)
    assert _wait_for(lambda: not b.wifiBusy and not b.wifiEnabled)
    assert b.wifiStatusText == "WI-FI RADIO OFF"
