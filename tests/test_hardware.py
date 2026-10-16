"""Hardware page: synth port watch, auto-attach, offline detection, ping."""

import json
import time
from types import SimpleNamespace

import pytest

from src.spectre.core.midi import port_key
from src.spectre.ui.app import create_application

pytestmark = pytest.mark.ui

SYNTH = "JUNO-DS:JUNO-DS MIDI 1 32:0"
IDENTITY = [0x7E, 0x10, 0x06, 0x02, 0x41, 0x3A, 0x02, 0x03, 0x00, 0x00, 0x03, 0x00, 0x00]


class FakePort:
    def __init__(self, name):
        self.name, self.closed = name, False


class FakeMidi:
    """Stands in for MidiDeviceManager: one synth port that answers identity requests."""

    def __init__(self, present=True, answers=True):
        self.present, self.answers = present, answers
        self.juno_in = self.juno_out = None
        self.juno_port_pref = ""
        self.connects = 0
        self._replies = []

    @property
    def is_juno_connected(self):
        return self.juno_out is not None and not self.juno_out.closed

    def connect_juno(self, port=None):
        if not self.present:
            raise ConnectionError("no synth")
        self.connects += 1
        self.juno_in, self.juno_out = FakePort(SYNTH), FakePort(SYNTH)
        return SYNTH, SYNTH

    def close_juno(self):
        self.juno_in = self.juno_out = None

    def reconnect_juno(self, port=None):
        self.close_juno()
        try:
            self.connect_juno()
            return True
        except ConnectionError:
            return False

    def send_juno_sysex(self, data):
        if list(data[:4]) == [0x7E, 0x7F, 0x06, 0x01] and self.answers:
            self._replies.append(SimpleNamespace(type="sysex", data=IDENTITY))

    def iter_juno_messages(self):
        while self._replies:
            yield self._replies.pop(0)

    def add_note_listener(self, fn):
        pass


@pytest.fixture
def ui(monkeypatch, tmp_path):
    monkeypatch.setenv("JUNOSPECTRE_DATA_DIR", str(tmp_path))
    app, qml_engine, bridge = create_application(platform="offscreen")
    syncs = []
    bridge.syncPatchFromSynth = lambda async_mode=False: syncs.append(async_mode)
    yield app, bridge, syncs, tmp_path
    del qml_engine


def _settle(app, bridge, timeout=3.0):
    end = time.time() + timeout
    while time.time() < end:
        app.processEvents()
        if not bridge.jobBusy:
            return
        time.sleep(0.005)


def test_port_key_drops_alsa_numbers():
    assert port_key(SYNTH) == "JUNO-DS:JUNO-DS MIDI 1"
    assert port_key("LCXL3 1:LCXL3 1 MIDI In 36:0") == "LCXL3 1:LCXL3 1 MIDI In"


def test_synth_powered_on_later_is_attached(ui):
    app, bridge, syncs, _ = ui
    midi = FakeMidi()
    bridge.attach_midi_manager(midi, watch=False)
    assert not bridge.synthConnected
    bridge._on_ports_scanned([SYNTH], [SYNTH])
    _settle(app, bridge)
    assert bridge.synthConnected
    assert bridge.juno is not None and bridge.juno.midi is midi
    assert bridge.sequencer.midi is midi
    assert bridge.synthIdentity.startswith("JUNO-DS / XPS-30 · device ID 17")
    assert bridge.pingText.startswith("OK")
    assert syncs == [True]


def test_unplugged_synth_goes_offline(ui):
    app, bridge, _, _ = ui
    midi = FakeMidi()
    bridge.attach_midi_manager(midi, watch=False)
    bridge._on_ports_scanned([SYNTH], [SYNTH])
    _settle(app, bridge)
    assert bridge.synthConnected
    midi.present = False
    bridge._on_ports_scanned([], [])
    assert not bridge.synthConnected
    assert bridge.synthIdentity == ""


def test_silent_port_is_not_retried_until_ports_change(ui):
    app, bridge, syncs, _ = ui
    midi = FakeMidi(answers=False)
    bridge.attach_midi_manager(midi, watch=False)
    bridge._on_ports_scanned([SYNTH], [SYNTH])
    _settle(app, bridge)
    assert midi.connects == 1 and not syncs
    assert "did not answer" in bridge.pingText
    bridge._on_ports_scanned([SYNTH], [SYNTH])
    _settle(app, bridge)
    assert midi.connects == 1                       # same ports: no retry
    midi.answers = True
    bridge._on_ports_scanned([SYNTH, "X:Y 40:0"], [SYNTH])
    _settle(app, bridge)
    assert midi.connects == 2 and syncs == [True]


def test_port_list_merges_directions_and_hides_internal_ports(ui):
    app, bridge, _, _ = ui
    midi = FakeMidi()
    bridge.attach_midi_manager(midi, watch=False)
    bridge._on_ports_scanned(
        [SYNTH, "Midi Through:Midi Through Port-0 14:0", "RtMidiOut Client:RtMidi output 130:0",
         "LCXL3 1:LCXL3 1 MIDI In 36:0"],
        [SYNTH, "LCXL3 1:LCXL3 1 MIDI In 36:0", "LCXL3 1:LCXL3 1 To DIN Out 36:2"])
    _settle(app, bridge)
    ports = {p["key"]: p for p in bridge.midiPorts}
    assert set(ports) == {"JUNO-DS:JUNO-DS MIDI 1", "LCXL3 1:LCXL3 1 MIDI In", "LCXL3 1:LCXL3 1 To DIN Out"}
    assert ports["JUNO-DS:JUNO-DS MIDI 1"]["synth"]
    assert ports["LCXL3 1:LCXL3 1 To DIN Out"] == {
        "key": "LCXL3 1:LCXL3 1 To DIN Out", "input": False, "output": True, "synth": False}


def test_picked_synth_port_is_saved(ui):
    app, bridge, _, data = ui
    midi = FakeMidi()
    bridge.attach_midi_manager(midi, watch=False)
    bridge.setSynthPort("UM-ONE:UM-ONE MIDI 1")
    _settle(app, bridge)
    assert midi.juno_port_pref == "UM-ONE:UM-ONE MIDI 1"
    assert json.loads((data / "hardware.json").read_text())["synth_port"] == "UM-ONE:UM-ONE MIDI 1"
