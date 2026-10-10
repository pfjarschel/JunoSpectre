"""Performance-mode macro part targeting (MacroLink.parts) and FX macro routing."""

from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest

from src.spectre.core.midi import MidiDeviceManager
from src.spectre.core.patch_state import MacroLink, MacroSlot, PatchCommonState, ToneState
from src.spectre.core.protocol import JunoClient, SoundMode
from src.spectre.core.sysex import temp_perf_patch_base
from src.spectre.ui.app import create_application
from src.spectre.vector.engine import VectorEngine

pytestmark = pytest.mark.ui



def _fake_juno(other_cutoff=50):
    juno = MagicMock()
    juno.scope = None
    juno.writes = []

    @contextmanager
    def part_scope(part):
        prev, juno.scope = juno.scope, part
        try:
            yield juno
        finally:
            juno.scope = prev

    juno.part_scope = part_scope
    juno.set_patch_offsets.side_effect = lambda **kw: juno.writes.append((juno.scope, kw))
    juno.read_patch_common.side_effect = lambda timeout=1.0: PatchCommonState(cutoff_offset=other_cutoff)
    juno.read_all_tones.side_effect = lambda timeout=1.0: [ToneState(tone_index=i) for i in range(1, 5)]
    return juno


@pytest.fixture
def perf_bridge():
    app, qml_engine, bridge = create_application(engine=VectorEngine(), platform="offscreen")
    juno = _fake_juno()
    bridge.engine.juno = juno
    bridge._sound_mode = "PERFORM"
    ps = bridge.patch_state
    ps.sound_mode = "PERFORM"
    ps.active_perf_part = 1
    ps.common.cutoff_offset = 64
    ps.macro_bases = {}
    bridge._macro_part_states = {}
    bridge._macro_async_parts = False  # async loading has its own test
    yield bridge, juno
    del app, qml_engine  # keep the Qt objects alive until the test is done


def _link(bridge, key, parts=None, depth=1.0):
    bridge.patch_state.macros[0] = MacroSlot(name="T", links=[MacroLink(key, 1, depth, parts or [])])


def test_fixed_parts_drive_each_part_from_its_own_base(perf_bridge):
    bridge, juno = perf_bridge
    _link(bridge, "common.cutoff_offset", [1, 3])
    bridge.setMacro(1, 0.5)  # +0.5 * 63 = +31.5
    assert bridge.patch_state.common.cutoff_offset == 96          # edited part: 64 + 31.5
    assert (None, {"cutoff": 96}) in juno.writes
    assert (3, {"cutoff": 82}) in juno.writes                       # part 3: 50 + 31.5
    assert bridge.patch_state.macro_bases["common.cutoff_offset@3"] == 50


def test_edit_mode_follows_the_edited_part(perf_bridge):
    bridge, juno = perf_bridge
    _link(bridge, "common.cutoff_offset")
    bridge.patch_state.active_perf_part = 4
    bridge.setMacro(1, 0.5)
    assert "common.cutoff_offset@4" in bridge.patch_state.macro_bases
    assert all(scope is None for scope, _ in juno.writes)  # edited part = default base


def test_all_means_sounding_parts(perf_bridge):
    bridge, juno = perf_bridge
    parts = bridge.patch_state.perf_parts
    for p in parts:
        p.volume, p.muted = 0, False
    parts[1].volume = 100
    parts[4].volume = 90
    parts[4].muted = True     # muted: skipped
    parts[6].volume = 80
    _link(bridge, "common.cutoff_offset", [0])
    bridge.setMacro(1, 0.2)
    assert sorted(scope for scope, _ in juno.writes) == [2, 7]


def test_part_mixer_targets(perf_bridge):
    bridge, juno = perf_bridge
    bridge.patch_state.perf_parts[2].reverb_send = 20
    _link(bridge, "part.reverb_send", [3], depth=0.5)
    bridge.setMacro(1, 1.0)  # +0.5 * 127
    assert bridge.patch_state.perf_parts[2].reverb_send == 84
    juno.set_perf_part_fx.assert_called_with(3, reverb=84)


def test_part_targets_do_nothing_in_patch_mode(perf_bridge):
    bridge, juno = perf_bridge
    bridge._sound_mode = "PATCH"
    _link(bridge, "part.level", [3])
    bridge.setMacro(1, 1.0)
    juno.set_perf_part_level.assert_not_called()


def test_mfx2_macro_writes_its_slot(perf_bridge):
    bridge, juno = perf_bridge
    fx = bridge.patch_state.perf_fx
    fx.mfx2.source = 0
    fx.mfx2.dry_send = 40
    bridge._editing_perf_mfx = 1  # the editing radio must not matter
    _link(bridge, "effects.mfx2_dry_send", depth=0.5)
    bridge.setMacro(1, 0.4)  # +0.4 * 0.5 * 127 = +25.4
    assert fx.mfx2.dry_send == 65
    juno.set_perf_mfx.assert_called_with(2, dry_send=65)


def test_manual_perf_fx_edit_rebases_macro(perf_bridge):
    bridge, juno = perf_bridge
    fx = bridge.patch_state.perf_fx
    fx.chorus_source = 0
    fx.chorus_level = 50
    _link(bridge, "effects.chorus_level", depth=0.5)
    bridge.setMacro(1, 0.2)                      # 50 + 12.7
    assert fx.chorus_level == 63
    bridge.setChorusParam("level", 90)           # manual edit = new base
    assert bridge.patch_state.macro_bases["effects.chorus_level"] == 90
    assert fx.chorus_level == 103


def test_mode_switch_clears_bases(perf_bridge):
    bridge, juno = perf_bridge
    _link(bridge, "common.cutoff_offset", [3])
    bridge.setMacro(1, 0.5)
    assert bridge.patch_state.macro_bases
    bridge.setSoundMode("PATCH")
    assert bridge.patch_state.macro_bases == {}


def test_unpicking_a_part_restores_its_base(perf_bridge):
    bridge, juno = perf_bridge
    _link(bridge, "common.cutoff_offset", [1, 3])
    bridge.setMacro(1, 0.5)
    juno.writes.clear()
    bridge.toggleMacroLinkPart(1, 0, 3)
    assert (3, {"cutoff": 50}) in juno.writes
    assert bridge.patch_state.macros[0].links[0].parts == [1]
    bridge.toggleMacroLinkPart(1, 0, 1)          # none left -> edited part
    assert bridge.patch_state.macros[0].links[0].parts == []


def test_part_scope_addresses_the_part_buffer():
    mgr = MagicMock(spec=MidiDeviceManager)
    client = JunoClient(mgr)
    client._cached_sound_mode = SoundMode.PERFORM
    client.set_active_perf_part(1)
    with client.part_scope(3):
        assert client.get_active_patch_base() == temp_perf_patch_base(3)
    assert client.get_active_patch_base() == temp_perf_patch_base(1)


def test_macro_link_parts_roundtrip():
    from src.spectre.core.patch_state import PatchState
    from src.spectre.core.spectre_format import patch_state_from_dict, patch_state_to_dict

    ps = PatchState()
    ps.macros[0] = MacroSlot(name="X", links=[MacroLink("common.cutoff_offset", 1, 0.5, [6, 2, 2])])
    back = patch_state_from_dict(patch_state_to_dict(ps))
    assert back.macros[0].links[0].parts == [2, 6]
    assert MacroLink("common.level", 1, 0.5, [3, 0]).parts == [0]


def test_all_parts_load_off_thread_then_join(perf_bridge):
    """Picking ALL must not block on reading every part: parts whose mirror
    is still loading are skipped, then join when it arrives."""
    import threading
    import time

    bridge, juno = perf_bridge
    bridge._macro_async_parts = True
    release = threading.Event()
    reads = []

    def slow_common(timeout=1.0):
        reads.append(threading.current_thread().name)
        release.wait(2.0)
        return PatchCommonState(cutoff_offset=50)

    juno.read_patch_common.side_effect = slow_common
    _link(bridge, "common.cutoff_offset", parts=[1, 3])
    bridge.setMacro(1, 0.5)
    # Edited part 1 moved at once; part 3 is still loading, nothing written for it
    assert bridge.patch_state.common.cutoff_offset > 64
    assert all(scope != 3 for scope, _ in juno.writes)

    release.set()
    app = __import__("PyQt6.QtWidgets", fromlist=["QApplication"]).QApplication.instance() \
        or __import__("PyQt6.QtGui", fromlist=["QGuiApplication"]).QGuiApplication.instance()
    end = time.time() + 3
    while time.time() < end and not any(scope == 3 for scope, _ in juno.writes):
        app.processEvents()
        time.sleep(0.01)
    assert reads and all(name == "macro-parts" for name in reads)
    assert any(scope == 3 for scope, _ in juno.writes)
    assert bridge.patch_state.macro_bases["common.cutoff_offset@3"] == 50
