"""Unit tests for FX and Tone Routing engine, presets, and pitfall detector."""

from unittest.mock import MagicMock

import pytest

from src.spectre.core.midi import MidiDeviceManager
from src.spectre.core.patch_state import PatchState
from src.spectre.core.protocol import JunoClient, SoundMode


@pytest.fixture
def mock_midi_mgr():
    mgr = MagicMock(spec=MidiDeviceManager)
    return mgr


def test_juno_client_set_tone_output(mock_midi_mgr):
    client = JunoClient(mock_midi_mgr)
    client._cached_sound_mode = SoundMode.PATCH

    # Set Tone 1 output assign = 0 (MFX), level = 100, chorus_send = 30, reverb_send = 40
    client.set_tone_output(
        tone_index=1,
        output_assign=0,
        output_level=100,
        chorus_send=30,
        reverb_send=40,
    )

    assert mock_midi_mgr.send_juno_sysex.call_count == 4
    sent_packets = [c[0][0] for c in mock_midi_mgr.send_juno_sysex.call_args_list]

    # Roland DT1 header: 41 10 00 00 3A 12 <addr 4 bytes> <data> <checksum>
    assert all(p[0:6] == [0x41, 0x10, 0x00, 0x00, 0x3A, 0x12] for p in sent_packets)


def test_juno_client_set_patch_output_assign(mock_midi_mgr):
    client = JunoClient(mock_midi_mgr)
    client._cached_sound_mode = SoundMode.PATCH

    client.set_patch_output_assign(13)  # TONE

    assert mock_midi_mgr.send_juno_sysex.call_count == 1
    packet = mock_midi_mgr.send_juno_sysex.call_args[0][0]
    assert packet[6:10] == [0x1F, 0x00, 0x00, 0x27]
    assert packet[10] == 13


def test_juno_client_writes_direct_send_pair(mock_midi_mgr):
    client = JunoClient(mock_midi_mgr)
    client._cached_sound_mode = SoundMode.PATCH
    client.set_tone_output(2, chorus_send_direct=30, reverb_send_direct=40)
    sent = [c[0][0] for c in mock_midi_mgr.send_juno_sysex.call_args_list]
    assert [(p[6:10], p[10]) for p in sent] == [
        ([0x1F, 0x00, 0x22, 0x0F], 30), ([0x1F, 0x00, 0x22, 0x10], 40)]


def test_patch_state_routing_defaults():
    state = PatchState()
    assert len(state.tones) == 4
    for t in state.tones:
        assert t.output_assign == 0
        assert t.output_level == 127
        assert t.chorus_send == 0
        assert t.reverb_send == 0
        assert t.chorus_send_direct == 0
        assert t.reverb_send_direct == 0
    assert state.common.patch_output_assign == 13
    assert (state.common.structure_12, state.common.structure_34) == (0, 0)
    assert state.effects.routing_preset == ""


def test_decode_reads_both_send_pairs_and_structure():
    a = bytearray(154)
    a[0x0C:0x12] = bytes([127, 50, 60, 30, 40, 5])
    t = PatchState._decode_tone(bytes(a), bytes(26), 1)
    assert (t.chorus_send, t.reverb_send, t.chorus_send_direct, t.reverb_send_direct) == (50, 60, 30, 40)
    assert t.output_assign == 5
    tmt = bytearray(41)
    tmt[0x00], tmt[0x02], tmt[0x05], tmt[0x0E] = 3, 0, 1, 0
    state = PatchState()
    PatchState.apply_tmt(bytes(tmt), state.common, state.tones)
    assert (state.common.structure_12, state.common.structure_34) == (3, 0)
    assert [t.muted for t in state.tones][:2] == [False, True]


# --- core.routing: follow the sound -----------------------------------------

from src.spectre.core import routing as R  # noqa: E402

_MFX = {"type": 15, "dry": 127, "cho": 0, "rev": 0}
_CHO = {"type": 1, "level": 100, "toReverb": 0}
_REV = {"type": 4, "level": 100}


def _graph(state, mfx=None, cho=None, rev=None, part=None):
    return R.build_graph(state, mfx=mfx or _MFX, chorus=cho or _CHO, reverb=rev or _REV, part=part)


def _active(g):
    return {k for k, e in g["edges"].items() if e["active"]}


def test_graph_tones_into_mfx_dry_only():
    g = _graph(PatchState())
    assert _active(g) == {"in->mfx", "mfx->out"}
    assert g["edges"]["in->mfx"]["tones"] == [1, 2, 3, 4]
    assert not g["nodes"]["cho"]["hasInput"]


def test_graph_mfx_sends_only_light_when_mfx_has_input():
    state = PatchState()
    for t in state.tones:
        t.output_assign = R.ASSIGN_LR
    g = _graph(state, mfx={"type": 15, "dry": 127, "cho": 90, "rev": 90})
    assert _active(g) == {"in->out"}


def test_graph_direct_tone_uses_direct_send_pair():
    state = PatchState()
    t = state.tones[0]
    t.output_assign = R.ASSIGN_LR
    t.chorus_send, t.chorus_send_direct = 0, 80   # MFX pair silent, direct pair live
    g = _graph(state)
    assert g["edges"]["in->cho"]["tones"] == [1]
    assert "cho->out" in _active(g)
    # Back into the MFX: the MFX pair (0) applies, chorus goes quiet
    t.output_assign = R.ASSIGN_MFX
    assert "in->cho" not in _active(_graph(state))


def test_graph_patch_assign_overrides_tones():
    state = PatchState()
    state.tones[0].output_assign = R.ASSIGN_LR
    state.common.patch_output_assign = R.ASSIGN_MFX
    g = _graph(state)
    assert "in->out" not in _active(g)
    assert g["tones"][0]["lockedBy"] == "patch"
    assert any(n["type"] == "PATCH_OVERRIDE" for n in g["notes"])


def test_graph_structure_tone1_follows_tone2():
    state = PatchState()
    state.common.structure_12 = 2
    state.tones[0].output_assign = R.ASSIGN_LR    # ignored: tone 2 decides
    g = _graph(state)
    assert g["tones"][0]["owner"] == 2 and g["tones"][0]["route"] == R.ASSIGN_MFX
    assert "in->out" not in _active(g)
    assert any(n["type"] == "STRUCTURE" for n in g["notes"])


def test_graph_mfx_thru_still_passes():
    g = _graph(PatchState(), mfx={"type": 0, "dry": 127, "cho": 0, "rev": 0})
    assert "mfx->out" in _active(g)
    assert g["nodes"]["mfx"]["thru"]


def test_graph_chorus_off_flags_dead_sends():
    state = PatchState()
    g = _graph(state, mfx={"type": 15, "dry": 127, "cho": 80, "rev": 0},
               cho={"type": 0, "level": 100, "toReverb": 0})
    assert "mfx->cho" in _active(g) and "cho->out" not in _active(g)
    assert any(n["type"] == "CHORUS_OFF" for n in g["notes"])


def test_graph_chorus_output_select_and_reverb_stack():
    state = PatchState()
    g = _graph(state, mfx={"type": 15, "dry": 0, "cho": 127, "rev": 60},
               cho={"type": 1, "level": 80, "toReverb": 2})
    assert {"cho->out", "cho->rev", "rev->out"} <= _active(g)
    types = {n["type"] for n in g["notes"]}
    assert {"REVERB_STACK", "CHORUS_MONO_SUM"} <= types


def test_graph_muted_tones_and_no_output():
    state = PatchState()
    for t in state.tones[1:]:
        t.muted = True
    g = _graph(state, mfx={"type": 15, "dry": 0, "cho": 0, "rev": 0})
    assert g["edges"]["in->mfx"]["tones"] == [1]
    assert any(n["type"] == "NO_OUTPUT" for n in g["notes"])


def test_graph_part_layer():
    from src.spectre.core.patch_state import PerfPartState
    state = PatchState()
    state.tones[0].reverb_send = 70
    part = PerfPartState(part_index=3)
    g = _graph(state, part=part)
    # PATCH assign: the patch routes, part sends (0) don't gate tone sends
    assert {"in->part", "in->mfx", "in->rev"} <= _active(g)
    part.output_assign, part.reverb_send = R.ASSIGN_LR, 0
    g = _graph(state, part=part)
    assert "in->out" in _active(g) and "in->mfx" not in _active(g)
    assert "in->rev" not in _active(g)            # part sends replace tone sends
    assert g["tones"][0]["lockedBy"] == "part"
    part.muted = True
    assert not ({"in->out", "in->mfx"} & _active(_graph(state, part=part)))


def test_mfx_chain_follows_structure():
    assert R.mfx_chain(1, 0) == [1]
    assert R.mfx_chain(1, 10) == [1, 2, 3]       # TYPE11
    assert R.mfx_chain(2, 7) == [2, 3]           # TYPE08
    assert R.mfx_chain(3, 15) == [3, 2, 1]       # TYPE16


# --- bridge ------------------------------------------------------------------

def test_bridge_routing_presets():
    from src.spectre.ui.bridge import SpectreBridge
    from src.spectre.vector.engine import VectorEngine

    bridge = SpectreBridge(VectorEngine())
    assert bridge.routingPreset == ""

    bridge.setPatchOutputAssign(0)
    bridge.applyRoutingPreset("SERIAL_CHAIN")
    assert bridge.routingPreset == "SERIAL_CHAIN"
    assert bridge.patchOutputAssign == 13          # presets route per tone
    assert bridge.toneOutputAssigns == [0, 0, 0, 0]
    assert (bridge.mfxDrySend, bridge.mfxChorusSend, bridge.mfxReverbSend) == (0, 127, 0)
    assert bridge.chorusToReverb == 1
    g = bridge.routingGraph
    assert g["edges"]["mfx->cho"]["active"] and g["edges"]["cho->rev"]["active"]
    assert g["edges"]["rev->out"]["active"] and not g["edges"]["mfx->out"]["active"]

    bridge.applyRoutingPreset("VINTAGE_SYNTH")
    assert bridge.toneOutputAssigns == [1, 1, 1, 1]
    assert bridge.toneChorusSends == [70] * 4      # the direct pair, the one that plays
    assert [t.chorus_send_direct for t in bridge.patch_state.tones] == [70] * 4
    assert [t.chorus_send for t in bridge.patch_state.tones] == [0] * 4
    g = bridge.routingGraph
    assert g["edges"]["in->out"]["active"] and g["edges"]["in->cho"]["active"]
    assert not g["edges"]["in->mfx"]["active"]

    bridge.applyRoutingPreset("SPLIT_PATH")
    g = bridge.routingGraph
    assert g["edges"]["in->mfx"]["tones"] == [1, 2]
    assert g["edges"]["in->out"]["tones"] == [3, 4]

    bridge.applyRoutingPreset("CLEAN_DIRECT")
    g = bridge.routingGraph
    assert {k for k, e in g["edges"].items() if e["active"]} == {"in->out"}

    # Presets that need chorus/reverb turn them on
    bridge.setChorusParam("type", 0)
    bridge.setReverbParam("type", 0)
    bridge.applyRoutingPreset("AMBIENT_WASH")
    assert bridge.chorusTypeName != "OFF" and bridge.reverbTypeName != "OFF"

    bridge.setToneRoutingParam(0, "level", 95)
    assert bridge.toneOutputLevels == [95, 95, 95, 95]
    assert bridge.routingPreset == "CUSTOM"


def test_bridge_tone_assign_rejects_fake_values():
    from src.spectre.ui.bridge import SpectreBridge
    from src.spectre.vector.engine import VectorEngine

    bridge = SpectreBridge(VectorEngine())
    bridge.setToneRoutingParam(1, "assign", 2)     # old fake "BOTH"
    assert bridge.toneOutputAssigns[0] == 0
    bridge.setToneRoutingParam(1, "assign", 6)     # R
    assert bridge.toneOutputAssigns[0] == 6
    bridge.setPatchOutputAssign(4)                 # unused wire value
    assert bridge.patchOutputAssign == 13


def test_bridge_routing_hardware_sysex_transmission(mock_midi_mgr):
    from src.spectre.ui.bridge import SpectreBridge
    from src.spectre.vector.engine import VectorEngine

    client = JunoClient(mock_midi_mgr)
    client._cached_sound_mode = SoundMode.PATCH
    engine = VectorEngine(juno_client=client)
    bridge = SpectreBridge(engine)

    mock_midi_mgr.send_juno_sysex.reset_mock()
    bridge.applyRoutingPreset("SERIAL_CHAIN")
    assert mock_midi_mgr.send_juno_sysex.call_count > 0

    def last():
        pkt = mock_midi_mgr.send_juno_sysex.call_args[0][0]
        return pkt[6:10], pkt[10]

    mock_midi_mgr.send_juno_sysex.reset_mock()
    bridge.setToneRoutingParam(1, "assign", 0)
    assert mock_midi_mgr.send_juno_sysex.call_count == 1
    assert last() == ([0x1F, 0x00, 0x20, 0x11], 0)

    mock_midi_mgr.send_juno_sysex.reset_mock()
    bridge.setToneRoutingParam(2, "level", 110)
    assert last() == ([0x1F, 0x00, 0x22, 0x0C], 110)

    # Tone 3 goes into the MFX: its chorus send is the MFX pair (0x0D)
    mock_midi_mgr.send_juno_sysex.reset_mock()
    bridge.setToneRoutingParam(3, "chorusSend", 75)
    assert mock_midi_mgr.send_juno_sysex.call_count == 1
    assert last() == ([0x1F, 0x00, 0x24, 0x0D], 75)

    # Tone 4 goes direct: its reverb send is the direct pair (0x10)
    bridge.setToneRoutingParam(4, "assign", 1)
    mock_midi_mgr.send_juno_sysex.reset_mock()
    bridge.setToneRoutingParam(4, "reverbSend", 90)
    assert last() == ([0x1F, 0x00, 0x26, 0x10], 90)

    # Patch assign override: tone 3 now plays direct, so the direct pair
    bridge.setPatchOutputAssign(1)
    assert last() == ([0x1F, 0x00, 0x00, 0x27], 1)
    bridge.setToneRoutingParam(3, "chorusSend", 33)
    assert last() == ([0x1F, 0x00, 0x24, 0x0F], 33)

    mock_midi_mgr.send_juno_sysex.reset_mock()
    bridge.setMfxSend("dry", 85)
    assert mock_midi_mgr.send_juno_sysex.call_count >= 2
    mock_midi_mgr.send_juno_sysex.reset_mock()
    bridge.setChorusParam("toReverb", 2)
    assert mock_midi_mgr.send_juno_sysex.call_count >= 1
    mock_midi_mgr.send_juno_sysex.reset_mock()
    bridge.setReverbParam("level", 80)
    assert mock_midi_mgr.send_juno_sysex.call_count >= 1


def test_bridge_perform_routing_part_stage(tmp_path):
    from tests.test_performance import _perform_bridge

    bridge, juno = _perform_bridge(tmp_path)
    g = bridge.routingGraph
    assert g["perform"] and g["part"]["index"] == bridge.activePerfPart
    assert g["edges"]["in->part"]["active"]

    bridge.setRoutingPartParam("mfxSelect", 2)
    part = bridge.patch_state.perf_parts[bridge.activePerfPart - 1]
    assert part.mfx_select == 1
    g = bridge.routingGraph
    assert g["nodes"]["mfx"]["label"] == "MFX2"
    assert g["mfxMismatch"]                       # radio still on MFX1
    bridge.editRoutedMfx()
    assert bridge.editingPerfMfx == 2 and not bridge.routingGraph["mfxMismatch"]

    bridge.setPerfStructure(10)                   # TYPE11: MFX1 -> MFX2 -> MFX3
    assert bridge.routingGraph["nodes"]["mfx"]["label"] == "MFX2→MFX3"

    bridge.setRoutingPartParam("assign", 1)
    assert part.output_assign == 1
    g = bridge.routingGraph
    assert g["edges"]["in->out"]["active"] and not g["edges"]["in->mfx"]["active"]
    bridge.setRoutingPartParam("reverbSend", 50)
    assert part.reverb_send == 50 and bridge.routingGraph["edges"]["in->rev"]["active"]

    # Presets hand routing back to the patch
    bridge.applyRoutingPreset("STUDIO_AUX")
    assert part.output_assign == 13


def _sent_addrs(mgr):
    return [tuple(c[0][0][6:10]) for c in mgr.send_juno_sysex.call_args_list]


def _fx_writes(client):
    client.set_mfx(5, dry_send=10, chorus_send=20, reverb_send=30)
    client.set_mfx_param(0, 1)
    client.set_mfx_params_bulk([1, 2])
    client.set_chorus(0, level=50, output_select=1)
    client.set_chorus_param("rate", 40)
    client.set_reverb(0, level=60)
    client.set_reverb_param("time", 70)


def test_patch_mode_fx_writes_mirror_to_perf_common(mock_midi_mgr):
    client = JunoClient(mock_midi_mgr)
    client._cached_sound_mode = SoundMode.PATCH
    _fx_writes(client)
    addrs = _sent_addrs(mock_midi_mgr)
    assert any(a[:3] == (0x10, 0x00, 0x02) for a in addrs)
    assert any(a[:3] == (0x10, 0x00, 0x04) for a in addrs)
    assert any(a[:3] == (0x10, 0x00, 0x06) for a in addrs)


def test_perform_mode_part_fx_writes_leave_shared_fx_alone(mock_midi_mgr):
    """Editing a part patch's FX must not overwrite the performance's shared
    MFX1/chorus/reverb or flip the global chorus/reverb switches."""
    from src.spectre.core.sysex import ADDR_SETUP_CHORUS_SWITCH, ADDR_SETUP_REVERB_SWITCH

    client = JunoClient(mock_midi_mgr)
    client._cached_sound_mode = SoundMode.PERFORM
    client.set_active_perf_part(3)
    _fx_writes(client)
    addrs = _sent_addrs(mock_midi_mgr)
    assert addrs and all(a[0] == 0x11 for a in addrs), addrs
    assert tuple(ADDR_SETUP_CHORUS_SWITCH) not in addrs
    assert tuple(ADDR_SETUP_REVERB_SWITCH) not in addrs


def test_old_snapshots_get_routing_from_their_image():
    """Snapshots saved before the routing model carry structure + direct sends
    only in the raw image."""
    from src.spectre.core.spectre_format import patch_state_from_dict

    tone = bytearray(154)
    tone[0x0F], tone[0x10] = 33, 44
    tmt = bytearray(41)
    tmt[0x00], tmt[0x02] = 2, 1
    d = {"common": {"name": "OLD"}, "tones": [{"chorus_send": 5}] * 4,
         "raw_regions": {"tmt": [list(tmt)], "tone_1": [list(tone), [0] * 26]}}
    st = patch_state_from_dict(d)
    assert (st.common.structure_12, st.common.structure_34) == (2, 1)
    assert (st.tones[0].chorus_send_direct, st.tones[0].reverb_send_direct) == (33, 44)
    # Saved values win over the image once the fields exist
    d["common"]["structure_12"] = 0
    d["tones"] = [{"chorus_send_direct": 7}] * 4
    st = patch_state_from_dict(d)
    assert st.common.structure_12 == 0 and st.tones[0].chorus_send_direct == 7
