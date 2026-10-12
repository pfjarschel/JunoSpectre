"""Header part/MFX picker: the MFX follows the part, MFX actions, header pieces."""

from unittest.mock import MagicMock

import pytest

from src.spectre.core.midi import MidiDeviceManager
from src.spectre.core.protocol import JunoClient, SoundMode


@pytest.fixture
def bridge(monkeypatch, tmp_path):
    from src.spectre.ui.bridge import SpectreBridge
    from src.spectre.vector.engine import VectorEngine

    monkeypatch.setenv("JUNOSPECTRE_DATA_DIR", str(tmp_path))
    client = JunoClient(MagicMock(spec=MidiDeviceManager))
    client._cached_sound_mode = SoundMode.PERFORM
    b = SpectreBridge(VectorEngine(juno_client=client))
    b._sound_mode = "PERFORM"
    b._refresh_editors_for_part = lambda part, async_mode=True: True
    return b


def test_picking_a_part_picks_its_mfx(bridge):
    parts = bridge.patch_state.perf_parts
    parts[2].mfx_select, parts[2].output_assign = 1, 13   # P3 enters MFX2 (patch decides)
    parts[3].mfx_select, parts[3].output_assign = 2, 1    # P4 goes direct to L+R
    bridge.editPerfPart(3)
    assert bridge.editingPerfMfx == 2
    bridge.editPerfPart(4)
    assert bridge.activePerfPart == 4 and bridge.editingPerfMfx == 2  # direct part: MFX stays
    bridge.setEditingPerfMfx(3)
    bridge.editPerfPart(1)
    assert bridge.editingPerfMfx == 1


def test_mfx_actions(bridge):
    bridge._ctl_run_action("mfx.edit.3")
    assert bridge.editingPerfMfx == 3
    bridge._ctl_run_action("mfx.next")
    assert bridge.editingPerfMfx == 1
    bridge._ctl_run_action("mfx.prev")
    assert bridge.editingPerfMfx == 3
    opened = []
    bridge.requestOpenEditTarget.connect(lambda: opened.append(1))
    bridge._ctl_run_action("edit_target.open")
    assert opened


def test_picker_opens_only_in_perform(bridge):
    opened = []
    bridge.requestOpenEditTarget.connect(lambda: opened.append(1))
    bridge._sound_mode = "PATCH"
    bridge.openEditTarget()
    assert not opened


def test_header_pieces(bridge):
    bridge.patch_state.perf_name = "MY SONG"
    bridge.patch_state.perf_parts[2].patch_name = "Warm Pad"
    bridge.editPerfPart(3)
    assert bridge.perfHeader == {"perf": "MY SONG", "part": 3, "patch": "Warm Pad"}
    assert all("name" in s for s in bridge.perfFxSlots[:3])
