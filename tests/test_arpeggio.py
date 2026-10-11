"""Arpeggiator: settings model, SysEx addresses, clock out, bridge save/load."""

import time
from unittest.mock import MagicMock

import pytest

from src.spectre.core.arpeggio import (
    ARP_SETUP_SIZE,
    STYLE_NAMES,
    ArpSettings,
    MidiClockOut,
    field_from_label,
    field_label,
)
from src.spectre.core.midi import MidiDeviceManager
from src.spectre.core.protocol import JunoClient
from src.spectre.core.spectre_format import load_spectre, save_spectre
from src.spectre.ui.app import create_application
from src.spectre.vector.engine import VectorEngine


def test_style_list_matches_the_parameter_guide():
    assert len(STYLE_NAMES) == 128
    assert STYLE_NAMES[0] == "Basic 1 (a)"
    assert STYLE_NAMES[35] == "Seq Ptn 30 (5)"
    assert STYLE_NAMES[66] == "Bassline 1 (1)"
    assert STYLE_NAMES[117] == "Gtr Arp 1 (4)"
    assert STYLE_NAMES[127] == "1/4 Note Trg (1)"


def test_settings_clamp_and_round_trip():
    s = ArpSettings(style=300, octave=-9, accent=150, switch=1)
    c = s.clamped()
    assert (c.style, c.octave, c.accent, c.switch) == (127, -3, 100, True)
    assert ArpSettings.from_dict(c.to_dict()) == c
    assert ArpSettings.from_dict({"style": 5, "bogus": 1}).style == 5
    assert ArpSettings.from_dict({"style": 5, "part": 3}).style == 5   # v0.11 files
    assert ArpSettings.from_dict("nope") is None


def test_setup_bytes_parse_back():
    s = ArpSettings(switch=True, style=70, motif=11, grid=3, duration=9, octave=-2,
                    hold=True, accent=40, velocity=0, step=16)
    raw = bytearray(ARP_SETUP_SIZE)
    for off, v in s.setup_bytes().items():
        raw[off - 0x17] = v
    assert raw[0x1D - 0x17] == 62          # octave -2 -> 62
    assert ArpSettings.from_setup(bytes(raw)) == s


def test_labels():
    s = ArpSettings(octave=2, velocity=0, step=0, motif=2)
    assert field_label(s, "octave") == "+2"
    assert field_label(s, "velocity") == "REAL"
    assert field_label(s, "step") == "AUTO"
    assert field_label(s, "motif") == "Up (_)"
    assert field_from_label("octave", "-3") == -3
    assert field_from_label("style", "002 Basic 2 (a)") == 1
    assert field_from_label("grid", "nope") is None


@pytest.fixture
def client():
    mgr = MagicMock(spec=MidiDeviceManager)
    c = JunoClient(mgr)
    c._min_send_interval_s = 0.0
    return c, mgr


def _sent(mgr):
    return [(tuple(p[6:10]), p[10]) for (p,), _ in mgr.send_juno_sysex.call_args_list]


def test_write_arp_addresses(client):
    c, mgr = client
    s = ArpSettings(switch=True, style=70, octave=1)
    c.write_arp_field(s, "style")
    c.write_arp_field(s, "octave")
    assert _sent(mgr) == [((0x01, 0, 0, 0x1B), 70), ((0x01, 0, 0, 0x1D), 65)]
    mgr.send_juno_sysex.reset_mock()
    c.write_arp(s)
    sent = _sent(mgr)
    assert len(sent) == 10 and all(addr[0] == 0x01 for addr, _ in sent)   # Setup only
    assert sent[-1] == ((0x01, 0, 0, 0x19), 1)      # switch last


def test_read_arp(client, monkeypatch):
    c, _ = client
    want = ArpSettings(switch=True, style=9, grid=1, octave=3)
    raw = bytearray(ARP_SETUP_SIZE)
    for off, v in want.setup_bytes().items():
        raw[off - 0x17] = v

    def fake_request(addr, size, timeout=1.0):
        assert tuple(addr) == (0x01, 0, 0, 0x17)
        return bytes(raw)

    monkeypatch.setattr(c, "request_data", fake_request)
    assert c.read_arp() == want


def test_clock_out_rate_and_switch():
    pulses = []
    clock = MidiClockOut(lambda: pulses.append(time.perf_counter()) or True, bpm=240.0)
    try:
        clock.set_enabled(True)
        time.sleep(0.5)
        clock.set_enabled(False)
        n = len(pulses)
        assert 40 <= n <= 56                 # 96 pulses/s at 240 BPM
        time.sleep(0.15)
        assert len(pulses) <= n + 1
    finally:
        clock.close()


# -- bridge -------------------------------------------------------------------

@pytest.fixture
def ui(monkeypatch, tmp_path):
    monkeypatch.setenv("JUNOSPECTRE_DATA_DIR", str(tmp_path))
    app, qml_engine, bridge = create_application(engine=VectorEngine(), platform="offscreen")
    yield app, bridge, tmp_path
    bridge._clock_out.close()
    del qml_engine


def test_unknown_arp_is_not_saved(ui):
    _, bridge, _ = ui
    assert "arp" not in bridge._live_spectre_extras()
    bridge.setArpField("style", 12)
    assert bridge._live_spectre_extras()["arp"]["style"] == 12


def test_patch_file_carries_and_restores_the_arp(ui):
    _, bridge, tmp = ui
    bridge.setArpField("switch", 1)
    bridge.setArpField("motif", 11)
    # what saveCurrentToFile writes (it needs a synth for the live state)
    path = save_spectre(tmp / "arp.spectre", bridge.patch_state, spectre=bridge._live_spectre_extras())
    assert load_spectre(path)["spectre"]["arp"]["motif"] == 11

    bridge.setArpField("motif", 0)
    bridge.setArpField("switch", 0)
    fake = MagicMock()
    bridge.engine.juno = fake
    assert bridge.loadSpectreFile(path)
    assert bridge.arp["motif"] == 11 and bridge.arp["switch"] is True
    fake.write_arp.assert_called_once()


def test_arp_knobs_and_actions(ui):
    _, bridge, _ = ui
    bridge.setActiveView("ARP")
    assert bridge.activeView == "ARPEGGIO"
    bridge._ctx_refresh()
    titles = [k["title"] for k in bridge.contextKnobs]
    assert titles[0] == "Arp Style" and titles[4] == "Arp Oct Range"
    bridge.setContextKnob(5, 0.0)
    assert bridge.arp["octave"] == -3
    bridge.setContextKnob(2, 1.0)
    assert bridge.arp["motifText"] == "Phrase"
    bridge._ctl_run_action("arp.toggle")
    assert bridge.arp["switch"] is True

