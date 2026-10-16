"""Tone Mix Table: decode, old snapshots, protocol writes and the bridge."""

from unittest.mock import MagicMock

import pytest

from spectre.core.midi import MidiDeviceManager
from spectre.core.patch_state import PatchState
from spectre.core.protocol import JunoClient, SoundMode


@pytest.fixture
def mock_midi_mgr():
    return MagicMock(spec=MidiDeviceManager)


def _tmt_image() -> bytearray:
    tmt = bytearray(0x29)
    tmt[0x00:0x05] = bytes([3, 2, 7, 1, 1])        # struct 4, +12 dB, struct 8, +6 dB, vel ON
    for off in (0x05, 0x0E, 0x17, 0x20):
        tmt[off:off + 9] = bytes([1, 0, 127, 0, 0, 1, 127, 0, 0])
    tmt[0x06:0x0E] = bytes([36, 59, 0, 12, 1, 100, 0, 20])  # tone 1
    tmt[0x17] = 0                                      # tone 3 off
    return tmt


def test_apply_tmt_decodes_whole_block():
    st = PatchState()
    PatchState.apply_tmt(bytes(_tmt_image()), st.common, st.tones)
    c = st.common
    assert (c.structure_12, c.booster_12, c.structure_34, c.booster_34) == (3, 2, 7, 1)
    assert c.tmt_velocity_control == 1
    t1 = st.tones[0]
    assert (t1.key_range_lower, t1.key_range_upper, t1.key_fade_lower, t1.key_fade_upper) == (36, 59, 0, 12)
    assert (t1.velo_range_lower, t1.velo_range_upper, t1.velo_fade_lower, t1.velo_fade_upper) == (1, 100, 0, 20)
    assert st.tones[2].muted and not st.tones[1].muted
    assert st.tones[3].key_range_upper == 127


def test_decode_common_reads_tmt_control_switch():
    common = bytearray(80)
    common[0:12] = b"TEST        "
    common[0x28] = 1
    assert PatchState._decode_common(bytes(common)).tmt_control_switch == 1


def test_old_snapshots_get_tmt_from_their_image():
    from spectre.core.spectre_format import patch_state_from_dict

    common = bytearray(80)
    common[0x28] = 1
    d = {"common": {"name": "OLD", "structure_12": 3, "structure_34": 7},
         "tones": [{"muted": False}] * 4,
         "raw_regions": {"tmt": [list(_tmt_image())], "common": [list(common)]}}
    st = patch_state_from_dict(d)
    assert (st.common.booster_12, st.common.booster_34, st.common.tmt_velocity_control) == (2, 1, 1)
    assert st.common.tmt_control_switch == 1
    assert st.tones[0].key_range_upper == 59 and st.tones[0].velo_fade_upper == 20
    assert not st.tones[2].muted  # saved mutes win over the image

    # Saved values win once the fields exist
    d["common"]["booster_12"] = 0
    d["tones"] = [{"key_range_upper": 100}] * 4
    st = patch_state_from_dict(d)
    assert st.common.booster_12 == 0 and st.tones[0].key_range_upper == 100
    assert st.tones[0].key_range_lower == 36  # still missing -> from the image


def test_new_fields_round_trip():
    from spectre.core.spectre_format import patch_state_from_dict, patch_state_to_dict

    st = PatchState()
    st.common.booster_34 = 3
    st.common.tmt_control_switch = 1
    st.tones[1].velo_range_lower = 64
    back = patch_state_from_dict(patch_state_to_dict(st))
    assert back.common.booster_34 == 3 and back.common.tmt_control_switch == 1
    assert back.tones[1].velo_range_lower == 64


def test_client_tmt_writes(mock_midi_mgr):
    client = JunoClient(mock_midi_mgr)
    client._cached_sound_mode = SoundMode.PATCH
    client.set_tmt_param(0x01, 3)
    client.set_tmt_control_switch(True)
    sent = [c[0][0] for c in mock_midi_mgr.send_juno_sysex.call_args_list]
    assert [(p[6:10], p[10]) for p in sent] == [
        ([0x1F, 0x00, 0x10, 0x01], 3), ([0x1F, 0x00, 0x00, 0x28], 1)]
    with pytest.raises(ValueError):
        client.set_tmt_param(0x29, 0)


@pytest.fixture
def bridge_and_mgr(mock_midi_mgr):
    from spectre.ui.bridge import SpectreBridge

    client = JunoClient(mock_midi_mgr)
    client._cached_sound_mode = SoundMode.PATCH
    bridge = SpectreBridge(client)
    mock_midi_mgr.send_juno_sysex.reset_mock()
    return bridge, mock_midi_mgr


def _writes(mgr):
    # DT1s only: the bridge's background arp read sends an RQ1 at any moment
    return [(tuple(c[0][0][6:10]), c[0][0][10]) for c in mgr.send_juno_sysex.call_args_list
            if c[0][0][5] == 0x12]


def test_bridge_structure_booster_and_velocity_control(bridge_and_mgr):
    bridge, mgr = bridge_and_mgr
    routed = []
    bridge.routingChanged.connect(lambda: routed.append(1))
    bridge.setTmtStructure(2, 4)
    bridge.setTmtBooster(1, 2)
    bridge.setTmtVelocityControl(3)
    bridge.setTmtControlSwitch(True)
    assert _writes(mgr) == [((0x1F, 0x00, 0x10, 0x02), 4), ((0x1F, 0x00, 0x10, 0x01), 2),
                            ((0x1F, 0x00, 0x10, 0x04), 3), ((0x1F, 0x00, 0x00, 0x28), 1)]
    assert routed  # structure moves tone 3 onto tone 4's output
    t = bridge.tmt
    assert (t["structure34"], t["booster12"], t["veloControl"], t["ctrlSwitch"]) == (4, 2, 3, True)
    mgr.send_juno_sysex.reset_mock()
    bridge.setTmtStructure(2, 4)  # unchanged -> no write
    assert not mgr.send_juno_sysex.called


def test_bridge_range_edges_push_each_other(bridge_and_mgr):
    bridge, mgr = bridge_and_mgr
    bridge.setToneRange(2, "keyUpper", 60)
    bridge.setToneRange(2, "keyLower", 72)  # past the upper edge: drags it along
    assert _writes(mgr) == [((0x1F, 0x00, 0x10, 0x10), 60), ((0x1F, 0x00, 0x10, 0x0F), 72),
                            ((0x1F, 0x00, 0x10, 0x10), 72)]
    tone = bridge.tmt["tones"][1]
    assert (tone["keyLower"], tone["keyUpper"]) == (72, 72)
    bridge.setToneRange(4, "veloLower", 0)  # velocity floor is 1
    assert bridge.patch_state.tones[3].velo_range_lower == 1


def test_bridge_range_span_and_reset(bridge_and_mgr):
    bridge, mgr = bridge_and_mgr
    bridge.setToneRangeSpan(3, "velo", 40, 90)
    bridge.setToneRange(3, "veloFadeUpper", 15)
    t3 = bridge.patch_state.tones[2]
    assert (t3.velo_range_lower, t3.velo_range_upper, t3.velo_fade_upper) == (40, 90, 15)
    assert ((0x1F, 0x00, 0x10, 0x1C), 40) in _writes(mgr)  # TMT3 velocity lower
    bridge.resetToneRange(0, "velo")
    assert (t3.velo_range_lower, t3.velo_range_upper, t3.velo_fade_upper) == (1, 127, 0)


def test_structure_types_are_well_formed():
    from spectre.ui.bridge.tmt import STRUCTURE_TYPES

    assert len(STRUCTURE_TYPES) == 10
    for st in STRUCTURE_TYPES:
        n = len(st["nodes"])
        assert all(0 <= a < n and 0 <= b < n for a, b in st["edges"])
        assert all(0 <= o < n for o in st["out"])
    assert [i for i, st in enumerate(STRUCTURE_TYPES) if st["booster"]] == [2, 3]
