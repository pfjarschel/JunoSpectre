"""Panel following: messages from the synth, own-traffic filter, bridge re-reads."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import mido
import pytest

from spectre.core.midi import MidiDeviceManager
from spectre.core.panel_follow import FollowPlan, PanelFollower
from spectre.core.patch_state import PatchState, PerfPartState
from spectre.core.protocol import JunoClient, SoundMode
from spectre.core.sysex import RolandSysEx


def _dt1(addr, data):
    return mido.Message("sysex", data=RolandSysEx().build_dt1(addr, data))


def _pc(channel, msb, lsb, pc):
    return [mido.Message("control_change", channel=channel, control=0, value=msb),
            mido.Message("control_change", channel=channel, control=32, value=lsb),
            mido.Message("program_change", channel=channel, program=pc)]


def _feed_all(follower, msgs):
    return [e for e in (follower.feed(m) for m in msgs) if e is not None]


def test_follower_events():
    f = PanelFollower()
    assert _feed_all(f, _pc(15, 85, 64, 6)) == [("perf", 85, 64, 6)]
    assert _feed_all(f, _pc(0, 87, 64, 3)) == [("program", 0, 87, 64, 3)]
    assert _feed_all(f, _pc(15, 87, 0, 1)) == [("program", 15, 87, 0, 1)]  # part 16's patch
    assert f.feed(_dt1((0x11, 0x00, 0x20, 0x49), [5])) == ("edit", (0x11, 0x00, 0x20, 0x49), b"\x05")
    assert f.feed(mido.Message("control_change", channel=0, control=74, value=3)) is None
    bad = RolandSysEx().build_dt1((0x01, 0, 0, 0x19), [1])
    bad[-1] ^= 1
    assert f.feed(mido.Message("sysex", data=bad)) is None


def test_follower_drops_own_traffic():
    f = PanelFollower(is_own=lambda addr, data: tuple(addr) == (0x1F, 0, 0, 0))
    assert f.feed(_dt1((0x1F, 0, 0, 0), [1])) is None
    assert f.feed(_dt1((0x1F, 0, 0, 1), [1])) is not None


def test_plan_sorts_edits():
    p = FollowPlan()
    assert p.empty()
    p.add(("edit", (0x01, 0, 0, 0x00), b"\x01"))
    p.add(("edit", (0x01, 0, 0, 0x19), b"\x01"))
    p.add(("edit", (0x10, 0, 0x02, 0x05), b"\x00"))
    p.add(("edit", (0x10, 0, 0x23, 0x00), b"\x00"))
    p.add(("edit", (0x10, 0, 0x60, 0x18), b"\x00"))   # controller block: not followed
    p.add(("edit", (0x11, 0x00, 0x20, 0x49), b"\x00"))  # part 1, tone 1
    p.add(("edit", (0x11, 0x20, 0x00, 0x05), b"\x00"))  # part 2
    p.add(("edit", (0x14, 0x60, 0x00, 0x00), b"\x00"))  # part 16
    p.add(("edit", (0x1F, 0x00, 0x20, 0x00), b"\x00"))
    assert (p.mode, p.arp, p.perf_fx, p.parts, p.patch) == (1, True, True, True, True)
    assert p.part_patches == {1, 2, 16}


def test_client_tells_own_traffic():
    mgr = MagicMock(spec=MidiDeviceManager)
    mgr.iter_juno_messages.return_value = iter(())
    client = JunoClient(mgr)
    client.send_data((0x10, 0, 0x20, 0x00), [90])
    assert client.is_own_traffic((0x10, 0, 0x20, 0x00), b"\x5a")      # echo
    assert not client.is_own_traffic((0x10, 0, 0x20, 0x00), b"\x10")  # someone else's value
    client.request_data((0x10, 0, 0, 0), (0, 0, 0, 0x0C), timeout=0.01)
    assert client.is_own_traffic((0x10, 0, 0, 0), b"ANY NAME    ")    # reply
    assert not client.is_own_traffic((0x11, 0, 0, 0), b"\x00")


@pytest.fixture
def bridge(monkeypatch, tmp_path):
    from spectre.ui.bridge import SpectreBridge, follow

    class SyncThread:
        def __init__(self, target, args=(), **kw):
            self.target, self.args = target, args

        def start(self):
            self.target(*self.args)

    monkeypatch.setenv("JUNOSPECTRE_DATA_DIR", str(tmp_path))  # settings saves land here
    monkeypatch.setattr(follow, "threading", SimpleNamespace(Thread=SyncThread))
    mgr = MagicMock(spec=MidiDeviceManager)
    client = JunoClient(mgr)
    client._cached_sound_mode = SoundMode.PERFORM
    b = SpectreBridge(client)
    b._hw_settings = {}
    b._sound_mode = "PERFORM"
    mgr.send_juno_sysex.reset_mock()
    return b, client, mgr


def _send(b, msgs):
    for m in msgs:
        e = b._follower.feed(m)
        if e is not None:
            b._on_follow_event(e)
    b._follow_timer.stop()
    b._follow_fire()


def test_panel_part_edit_marks_and_refreshes_the_shown_part(bridge):
    b, client, _ = bridge
    image = PatchState()
    image.common.name = "PANEL EDIT"
    reads = []
    b._read_part_image = lambda part: reads.append(part) or image
    b.patch_state.active_perf_part = 2
    _send(b, [_dt1((0x11, 0x20, 0x20, 0x49), [5]), _dt1((0x11, 0x00, 0x00, 0x10), [1])])
    parts = b.patch_state.perf_parts
    assert parts[0].modified and parts[1].modified and not parts[2].modified
    assert reads == [2]  # only the part the editors show is re-read
    assert b.patch_state.common.name == "PANEL EDIT"


def test_panel_mixer_edit_keeps_unchanged_sounds(bridge):
    b, client, _ = bridge
    parts = b.patch_state.perf_parts
    parts[0].patch_file, parts[0].modified, parts[0].patch_name = "/a.spectre", True, "MINE"
    parts[1].patch_file, parts[1].patch_name = "/b.spectre", "OLD"
    b._part_snapshots = {"2": {"x": 1}}
    fresh = [PerfPartState(part_index=i, volume=50, patch_msb=p.patch_msb,
                           patch_lsb=p.patch_lsb, patch_pc=p.patch_pc)
             for i, p in enumerate(parts, start=1)]
    fresh[1].patch_pc = (fresh[1].patch_pc + 1) % 128  # part 2 got another sound
    client.get_perf_parts = lambda timeout=1.0: fresh
    client.get_perf_part_patch_name = lambda part, timeout=0.25: "NEW SOUND"
    b._librarian_repo = None
    _send(b, [_dt1((0x10, 0x00, 0x20, 0x00), [50])])
    p1, p2 = b.patch_state.perf_parts[:2]
    assert p1.volume == 50 and p1.patch_file == "/a.spectre" and p1.modified and p1.patch_name == "MINE"
    assert p2.patch_file == "" and not p2.modified and p2.patch_name == "NEW SOUND"
    assert "2" not in b._part_snapshots


def test_panel_perf_pick_loads_it_without_navigating(bridge):
    b, client, _ = bridge
    calls = []
    b._adopt_synth_performance = lambda *a, **kw: calls.append((a, kw)) or True
    started = []
    b._start_job = lambda name, text, fn: started.append(name) or fn(lambda *x: None)
    _send(b, _pc(15, 85, 0, 4))
    assert started == ["follow"] and calls == [((85, 0, 4), {"navigate": False})]


def test_panel_patch_pick_in_patch_mode(bridge):
    b, client, _ = bridge
    b._sound_mode = "PATCH"
    calls = []
    b._adopt_synth_patch = lambda *a, **kw: calls.append(a) or True
    b._start_job = lambda name, text, fn: fn(lambda *x: None)
    _send(b, _pc(0, 87, 64, 9))
    assert calls == [(87, 64, 9)]


def test_panel_mode_switch_is_followed_not_pushed(bridge):
    b, client, mgr = bridge
    image = PatchState()
    client.read_patch_at = lambda base, timeout=1.5: image
    _send(b, [_dt1((0x01, 0, 0, 0), [0])])
    assert b._sound_mode == "PATCH" and client._cached_sound_mode == SoundMode.PATCH
    assert not mgr.send_juno_sysex.called or all(
        c[0][0][5] == 0x11 for c in mgr.send_juno_sysex.call_args_list)  # reads only


def test_follow_off_ignores_the_panel(bridge):
    b, client, _ = bridge
    b.setFollowPanel(False)
    b._follow_on_midi(_dt1((0x11, 0x00, 0x00, 0x10), [1]))
    assert b._follow_plan.empty()


def test_patch_sync_keeps_the_performance(bridge):
    b, client, _ = bridge
    b.patch_state.perf_parts[0].volume = 33
    b.patch_state.perf_name = "MY SONG"
    client.read_full_patch = lambda timeout=1.0: PatchState()
    b.syncPatchFromSynth()
    assert b.patch_state.perf_parts[0].volume == 33 and b.patch_state.perf_name == "MY SONG"
