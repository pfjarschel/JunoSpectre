"""MIDI controller bindings: mapping math, learn, targets, presets."""

import json
import time
from pathlib import Path

import pytest

from src.spectre.control.mapping import Binding, Resolver
from src.spectre.ui.app import create_application
from src.spectre.vector.engine import VectorEngine

PORT = "LCXL3 1:LCXL3 1 MIDI In"
DAW = "LCXL3 1:LCXL3 1 DAW In"
PRESET = Path(__file__).resolve().parents[1] / "config" / "controller_presets" / "novation_lcxl3.json"


def _b(**kw):
    d = dict(port=PORT, channel=0, kind="cc", number=13, target="tone.all.tvf_cutoff")
    d.update(kw)
    return Binding(**d)


# -- mapping ------------------------------------------------------------------

def test_pickup_waits_until_the_control_crosses_the_value():
    r, b = Resolver(), _b()
    assert r.resolve(b, 0, 0.5) is None
    assert r.resolve(b, 40, 0.5) is None
    t = r.resolve(b, 70, 0.5)                 # crossed 0.5 between 40 and 70
    assert t == pytest.approx(70 / 127)
    assert r.resolve(b, 71, t) == pytest.approx(71 / 127)


def test_pickup_is_lost_when_the_target_moves_elsewhere():
    r, b = Resolver(), _b(takeover="pickup")
    r.resolve(b, 64, 64 / 127)
    assert r.resolve(b, 65, 0.1) is None      # e.g. a patch load changed it
    assert r.pending_pickup(b)


def test_jump_applies_immediately_and_range_inverts():
    r = Resolver()
    assert r.resolve(_b(takeover="jump"), 127, 0.0) == 1.0
    assert r.resolve(_b(takeover="jump", lo=1.0, hi=0.0), 127, 0.5) == 0.0
    assert r.resolve(_b(takeover="jump", lo=0.5, hi=1.0), 0, 0.0) == 0.5


def test_momentary_and_toggle_buttons():
    r = Resolver()
    m = _b(behavior="momentary")
    assert r.resolve(m, 127, 0.0) == 1.0
    assert r.resolve(m, 127, 1.0) is None     # still held
    assert r.resolve(m, 0, 1.0) == 0.0
    t = _b(behavior="toggle", number=37)
    assert r.resolve(t, 127, 0.0) == 1.0
    assert r.resolve(t, 0, 1.0) is None        # release does nothing
    assert r.resolve(t, 127, 1.0) == 0.0
    assert r.resolve(t, 0, 0.0) is None
    assert r.resolve(t, 127, 0.9) == 0.0       # flips relative to where the target is


def test_binding_round_trip_and_bad_data():
    b = _b(behavior="toggle", lo=0.5)
    assert Binding.from_dict(b.to_dict()) == b
    assert Binding.from_dict({"channel": 0}) is None
    assert Binding.from_dict({**b.to_dict(), "behavior": "weird"}).behavior == "absolute"


def test_bundled_lcxl3_preset_targets_exist():
    from src.spectre.core.macro_targets import get_macro_catalog
    from src.spectre.ui.bridge.controllers import ACTIONS

    keys = {e["key"] for e in get_macro_catalog()} | {a["key"] for a in ACTIONS}
    d = json.loads(PRESET.read_text())
    bindings = [Binding.from_dict(x) for x in d["bindings"]]
    assert all(bindings)
    for b in bindings:
        assert b.target.split("@")[0] in keys or b.target.startswith("macro."), b.target
    # One binding per control and scope
    seen = {(b.channel, b.number, b.context, x.get("port_hint", "")) for b, x in zip(bindings, d["bindings"])}
    assert len(seen) == len(bindings)
    assert d["device"]["on_quit"][0]["send"] == ["9F 0C 00"]


def test_most_specific_context_wins():
    from src.spectre.control.mapping import pick_bindings

    every = _b(target="macro.1")
    perform = _b(target="part.level@1", context="MODE:PERFORM")
    seq = _b(target="action.seq.scene.1", context="SEQUENCER")
    bs = [every, perform, seq]
    assert pick_bindings(bs, PORT, 0, "cc", 13, "JUNO PCM", "PATCH") == [every]
    assert pick_bindings(bs, PORT, 0, "cc", 13, "JUNO PCM", "PERFORM") == [perform]
    assert pick_bindings(bs, PORT, 0, "cc", 13, "SEQUENCER", "PERFORM") == [seq]
    assert pick_bindings([perform], PORT, 0, "cc", 13, "JUNO PCM", "PATCH") == []


# -- bridge -------------------------------------------------------------------



@pytest.fixture
def ui(monkeypatch, tmp_path):
    monkeypatch.setenv("JUNOSPECTRE_DATA_DIR", str(tmp_path))
    app, qml_engine, bridge = create_application(engine=VectorEngine(), platform="offscreen")
    bridge._ctl_open[PORT] = object()          # pretend the LCXL3 is connected
    yield app, bridge, tmp_path
    bridge._ctl_open.clear()
    del qml_engine


def _send(app, bridge, *events):
    for ev in events:
        bridge._ctl_on_message(PORT, ev)
    end = time.time() + 1.0
    while time.time() < end:
        app.processEvents()
        if not bridge._ctl_scheduled:
            break
        time.sleep(0.005)
    app.processEvents()


def _cc(num, val, ch=0):
    import mido

    return mido.Message("control_change", channel=ch, control=num, value=val)


@pytest.mark.ui
def test_learn_binds_the_next_moved_control(ui):
    app, bridge, data = ui
    bridge.startControlLearn("tone.all.tvf_cutoff")
    assert bridge.controlLearnTitle == "All Cutoff"
    _send(app, bridge, _cc(13, 0), _cc(13, 1))   # 0 is ignored (release / at minimum)
    assert bridge.controlLearnTarget == ""
    (b,) = bridge.controlBindings
    assert (b["target"], b["behavior"], b["port"]) == ("tone.all.tvf_cutoff", "absolute", PORT)
    assert b["control"] == "Knob A1 · CH1 CC 13"
    saved = json.loads((data / "hardware.json").read_text())["controllers"]["bindings"]
    assert saved[0]["number"] == 13
    # A press of 127 is a button: toggle; relearning a control replaces its binding
    bridge.startControlLearn("macro.2")
    _send(app, bridge, _cc(13, 127))
    assert [(b["target"], b["behavior"]) for b in bridge.controlBindings] == [("macro.2", "toggle")]


@pytest.mark.ui
def test_knob_sets_every_tone_like_the_ui(ui):
    app, bridge, _ = ui
    bridge._ctl_bindings = [_b(takeover="jump")]
    _send(app, bridge, _cc(13, 10), _cc(13, 50), _cc(13, 100))
    assert [t.tvf_cutoff for t in bridge.patch_state.tones] == [100] * 4
    assert "All Cutoff" in bridge.controlActivity


@pytest.mark.ui
def test_knob_values_coalesce_but_button_edges_do_not(ui):
    app, bridge, _ = ui
    seen = []
    bridge._ctl_bindings = [_b(takeover="jump"), _b(number=37, target="macro.1", behavior="momentary")]
    orig = bridge._ctl_apply
    bridge._ctl_apply = lambda target, t: (seen.append((target, round(t, 3))), orig(target, t))
    _send(app, bridge, _cc(13, 10), _cc(37, 127), _cc(13, 20), _cc(37, 0), _cc(13, 30))
    assert seen == [("tone.all.tvf_cutoff", round(30 / 127, 3)), ("macro.1", 1.0), ("macro.1", 0.0)]


@pytest.mark.ui
def test_macro_binding_and_controller_sets_the_base_under_a_macro(ui):
    app, bridge, _ = ui
    bridge.addMacroTarget(1, "tone.1.tvf_cutoff")
    bridge.setMacro(1, 0.0)
    bridge._ctl_bindings = [_b(number=5, target="macro.1", takeover="jump"),
                            _b(target="tone.1.tvf_cutoff", takeover="jump")]
    _send(app, bridge, _cc(13, 40))
    assert bridge.patch_state.macro_bases["tone.1.tvf_cutoff"] == pytest.approx(40)
    _send(app, bridge, _cc(5, 127))              # macro 1 to +1 adds on top of the base
    assert bridge.patch_state.macros[0].value == pytest.approx(1.0)
    assert bridge.patch_state.tones[0].tvf_cutoff > 40


@pytest.mark.ui
def test_targets_include_macros_and_the_catalog(ui):
    app, bridge, _ = ui
    cats = bridge.getControlCategories()
    assert cats[:2] == ["ALL", "MACRO"]
    macros = bridge.getControlTargets("MACRO", "")
    assert [m["key"] for m in macros] == [f"macro.{i}" for i in range(1, 9)]
    keys = [t["key"] for t in bridge.getControlTargets("ALL", "")]
    assert "tone.all.tvf_cutoff" in keys and "macro.8" in keys


@pytest.mark.ui
def test_preset_load_and_save(ui):
    app, bridge, data = ui
    assert any(p["name"].startswith("Launch Control XL3") for p in bridge.controlPresets())
    bridge._ctl_open[DAW] = object()
    sent = []
    bridge._ctl_send = lambda key, msg: sent.append((key, msg.hex()))
    bridge._hw_outputs = [PORT + " 36:0", DAW + " 36:1"]
    bridge._ctl_sync_ports = lambda ins: None
    assert bridge.loadControlPreset(str(PRESET)) == ""
    n = len(json.loads(PRESET.read_text())["bindings"])
    assert len(bridge.controlBindings) == n
    ports = {b["port"] for b in bridge.controlBindings}
    assert ports == {PORT, DAW}
    play = [b for b in bridge.controlBindings if b["target"] == "action.seq.toggle_play"]
    assert play[0]["port"] == DAW
    # Device setup ran on the DAW port: DAW mode on, then custom mode 1
    assert sent == [(DAW, "9F 0C 7F"), (DAW, "B6 1E 06")]
    assert bridge.saveControlPreset("Live set") == ""
    saved = json.loads((data / "controller_presets" / "Live_set.json").read_text())
    assert saved["match"] == ["LCXL3 1"] and len(saved["bindings"]) == n
    assert all(b["port"] == "" for b in saved["bindings"])
    assert [b.get("port_hint") for b in saved["bindings"] if b["number"] == 116] == ["DAW In"]
    assert saved["device"]["feedback"] is True
    sent.clear()
    bridge.close_controllers()
    assert sent == [(DAW, "9F 0C 00")]


@pytest.mark.ui
def test_macro_center_snaps_to_zero(ui):
    app, bridge, _ = ui
    bridge._ctl_bindings = [_b(number=5, target="macro.3", takeover="jump")]
    _send(app, bridge, _cc(5, 64))
    assert bridge.patch_state.macros[2].value == 0.0
    _send(app, bridge, _cc(5, 63))
    assert bridge.patch_state.macros[2].value == 0.0


@pytest.mark.ui
def test_actions_run_on_press_only(ui):
    app, bridge, _ = ui
    bridge._ctl_bindings = [_b(number=37, target="action.tone.mute.2", behavior="toggle")]
    assert not bridge.patch_state.tones[1].muted
    _send(app, bridge, _cc(37, 127), _cc(37, 0))
    assert bridge.patch_state.tones[1].muted
    _send(app, bridge, _cc(37, 127), _cc(37, 0))
    assert not bridge.patch_state.tones[1].muted
    assert "Tone 2 Mute" in bridge.controlActivity


@pytest.mark.ui
def test_feedback_sends_target_values_but_not_back_to_a_moving_knob(ui):
    app, bridge, _ = ui
    sent = []
    bridge._ctl_send = lambda key, msg: sent.append((msg.control, msg.value))
    bridge._ctl_feedback[PORT] = True
    bridge._ctl_bindings = [_b(target="tone.1.tvf_cutoff", takeover="jump")]
    bridge.patch_state.tones[0].tvf_cutoff = 100
    bridge._ctl_feedback_tick()
    assert sent == [(13, 100)]
    bridge._ctl_feedback_tick()
    assert sent == [(13, 100)]                   # unchanged: nothing new
    _send(app, bridge, _cc(13, 30))
    bridge._ctl_feedback_tick()
    assert sent == [(13, 100)]                   # the knob itself just moved it
    bridge._ctl_moved.clear()
    bridge.patch_state.tones[0].tvf_cutoff = 64  # e.g. a patch load
    bridge._ctl_feedback_tick()
    assert sent[-1] == (13, 64)


@pytest.mark.ui
def test_fixed_part_targets(ui):
    app, bridge, _ = ui
    titles = {t["key"]: t["title"] for t in bridge.getControlTargets("PART", "")}
    assert titles["part.level@3"] == "Part 3 Level"
    bridge._in_perform = lambda: True
    bridge._ctl_bindings = [_b(number=5, target="part.level@3", takeover="jump")]
    _send(app, bridge, _cc(5, 90))
    assert bridge.patch_state.perf_parts[2].volume == 90


@pytest.mark.ui
def test_latching_button_fires_an_action_on_every_press(ui):
    app, bridge, _ = ui
    bridge._ctl_bindings = [_b(number=45, target="action.tone.mute.1", behavior="latch")]
    _send(app, bridge, _cc(45, 127))          # press 1: device latches on
    assert bridge.patch_state.tones[0].muted
    _send(app, bridge, _cc(45, 0))            # press 2: device latches off
    assert not bridge.patch_state.tones[0].muted


def test_latch_follows_the_button_state_for_values():
    r, b = Resolver(), _b(behavior="latch")
    assert r.resolve(b, 127, 0.0) == 1.0
    assert r.resolve(b, 0, 1.0) == 0.0
