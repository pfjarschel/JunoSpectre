"""MIDI controller bindings: mapping math, learn, targets, presets."""

import json
import time
from pathlib import Path

import pytest

from src.spectre.control.mapping import Binding, Resolver
from src.spectre.ui.app import create_application

PORT = "LCXL3 1:LCXL3 1 MIDI In"
DAW = "LCXL3 1:LCXL3 1 DAW In"
PRESET = (Path(__file__).resolve().parents[1] / "src" / "spectre" / "assets" / "controller_presets"
          / "novation_lcxl3.json")


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


def test_pickup_tolerates_a_coarse_targets_rounding():
    # Pitch env depth: 25 values, ~5 control steps per value. The target only
    # takes whole values, so the control sits up to half a value from it.
    r, b, step = Resolver(), _b(target="tone.all.pitch_env_depth"), 1 / 24
    assert Resolver().resolve(b, 66, 0.5) is None          # without the step: never caught
    assert r.resolve(b, 66, 0.5, step) == pytest.approx(66 / 127)
    assert r.resolve(b, 67, 0.5, step) == pytest.approx(67 / 127)   # still the same value: stays picked
    assert not r.pending_pickup(b)


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


def _valid_target(target, keys):
    if target.startswith("tone.sel."):
        return "tone.1." + target[9:] in keys
    if target.startswith(("mfx.p.", "context.")):
        return 1 <= int(target.rsplit(".", 1)[1]) <= 8
    return target.split("@")[0] in keys or target.startswith("macro.")


def test_bundled_lcxl3_preset_targets_exist():
    from src.spectre.core.macro_targets import get_macro_catalog
    from src.spectre.ui.bridge.controllers import ACTIONS

    keys = {e["key"] for e in get_macro_catalog()} | {a["key"] for a in ACTIONS}
    d = json.loads(PRESET.read_text())
    bindings = [Binding.from_dict(x) for x in d["bindings"]]
    assert all(bindings)
    for b in bindings:
        assert _valid_target(b.target, keys), b.target
    # One binding per control and scope
    seen = {(b.channel, b.number, b.context, x.get("port_hint", "")) for b, x in zip(bindings, d["bindings"])}
    assert len(seen) == len(bindings)
    assert d["device"]["on_quit"][0]["send"] == ["9F 0C 00"]


def test_most_specific_context_wins():
    from src.spectre.control.mapping import pick_bindings

    every = _b(target="macro.1")
    perform = _b(target="part.level@1", context="MODE:PERFORM")
    seq = _b(target="action.seq.scene.1", context="SEQUENCER")
    mixer = _b(target="part.pan@1", context="LAYER:MIXER&MODE:PERFORM&BANK:1")
    mixer2 = _b(target="part.pan@9", context="LAYER:MIXER&MODE:PERFORM&BANK:2")
    bs = [every, perform, seq, mixer, mixer2]

    def st(page, mode, layer="", bank=1):
        return {"PAGE": page, "MODE": mode, "LAYER": layer, "BANK": str(bank)}

    assert pick_bindings(bs, PORT, 0, "cc", 13, st("JUNO PCM", "PATCH")) == [every]
    assert pick_bindings(bs, PORT, 0, "cc", 13, st("JUNO PCM", "PERFORM")) == [perform]
    assert pick_bindings(bs, PORT, 0, "cc", 13, st("SEQUENCER", "PERFORM")) == [seq]
    assert pick_bindings(bs, PORT, 0, "cc", 13, st("SEQUENCER", "PERFORM", "MIXER")) == [mixer]
    assert pick_bindings(bs, PORT, 0, "cc", 13, st("SEQUENCER", "PERFORM", "MIXER", 2)) == [mixer2]
    assert pick_bindings(bs, PORT, 0, "cc", 13, st("JUNO PCM", "PATCH", "MIXER")) == [every]
    assert pick_bindings([perform], PORT, 0, "cc", 13, st("JUNO PCM", "PATCH")) == []


# -- bridge -------------------------------------------------------------------



@pytest.fixture
def ui(monkeypatch, tmp_path):
    monkeypatch.setenv("JUNOSPECTRE_DATA_DIR", str(tmp_path))
    app, qml_engine, bridge = create_application(platform="offscreen")
    bridge._ctl_open[PORT] = object()          # pretend the LCXL3 is connected
    yield app, bridge, tmp_path
    bridge._ctl_open.clear()
    del qml_engine


def _send(app, bridge, *events, port=PORT):
    for ev in events:
        bridge._ctl_on_message(port, ev)
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
def test_feedback_leaves_a_knob_on_a_coarse_targets_value(ui):
    app, bridge, _ = ui
    sent = []
    bridge._ctl_send = lambda key, msg: sent.append((msg.control, msg.value))
    bridge._ctl_feedback[PORT] = True
    bridge._ctl_bindings = [_b(target="tone.1.pitch_env_depth")]
    bridge.patch_state.tones[0].pitch_env_depth = 64      # 0 st: knob position 64
    bridge._ctl_feedback_tick()
    assert sent == [(13, 64)]
    _send(app, bridge, _cc(13, 65))                        # one slow step: still 0 st
    assert bridge.patch_state.tones[0].pitch_env_depth == 64
    bridge._ctl_moved[(PORT, 0, "cc", 13)] = (65, 0.0)     # the hold time is over
    bridge._ctl_feedback_tick()
    assert sent == [(13, 64)]       # not snapped back to 64: further slow steps add up
    _send(app, bridge, _cc(13, 66))
    _send(app, bridge, _cc(13, 67))
    assert bridge.patch_state.tones[0].pitch_env_depth == 65   # the next value: +1 st


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


SURFACE = PRESET.with_name("novation_lcxl3_surface.json")


def test_surface_preset_targets_exist():
    from src.spectre.core.macro_targets import get_macro_catalog
    from src.spectre.ui.bridge.controllers import ACTIONS

    keys = {e["key"] for e in get_macro_catalog()} | {a["key"] for a in ACTIONS}
    d = json.loads(SURFACE.read_text())
    assert d["device"]["surface"] == "lcxl3"
    for x in d["bindings"]:
        b = Binding.from_dict(x)
        assert _valid_target(b.target, keys), b.target
        assert x["port_hint"] == "DAW In"
        assert b.channel == (15 if 5 <= b.number <= 36 else 0)


def test_value_text():
    from src.spectre.control.lcxl3 import format_value

    assert format_value("macro.1", -0.5, -1, 1) == "-50%"
    assert format_value("common.cutoff_offset", 70, 1, 127) == "+6"
    assert format_value("tone.1.tva_pan", 64, 0, 127) == "C"
    assert format_value("tone.1.tva_pan", 40, 0, 127) == "L24"
    assert format_value("vector.x", 0.25, 0, 1) == "25%"
    assert format_value("tone.all.tvf_keyfollow", 74, 44, 84) == "+100%"
    assert format_value("part.level@3", 100, 0, 127) == "100"


@pytest.mark.ui
def test_surface_shows_names_values_and_leds(ui):
    from src.spectre.control import lcxl3

    app, bridge, _ = ui
    bridge._ctl_open[DAW] = object()
    sent = []
    bridge._ctl_send = lambda key, msg: sent.append((key, msg.hex()))
    bridge._hw_outputs = [PORT + " 36:0", DAW + " 36:1"]
    bridge._ctl_sync_ports = lambda ins: None
    assert bridge.loadControlPreset(str(SURFACE)) == ""
    assert sent[:2] == [(DAW, "9F 0C 7F"), (DAW, "B6 1E 02")]
    bridge._ctl_feedback_tick()
    msgs = [m for _, m in sent]
    text = lambda cc, field, t: lcxl3.display_text(cc, field, t).hex()
    assert text(13, 0, "MACRO 1") in msgs                    # knob A1 = macro 1
    assert text(13, 1, "CUTOFF OFS") in msgs
    assert text(13, 2, "+0%") in msgs
    assert lcxl3.led_rgb(13, lcxl3.by_value(lcxl3.CATEGORY_COLORS["MACRO"], 0.5)).hex() in msgs
    assert text(21, 0, "ALL TONES") in msgs                  # row B = LFOs, on every page
    assert text(21, 1, "LFO1 Rate") in msgs
    assert text(31, 1, "Flt Key Follow") in msgs              # row C = sound core
    assert text(34, 0, "TONE 1") in msgs                     # fine tune: the edited tone
    assert lcxl3.led_rgb(45, lcxl3.OFF).hex() in msgs        # clip row: empty clip
    bridge.setActiveView("SETLIST")
    bridge._ctl_feedback_tick()
    assert text(21, 1, "LFO1 Rate") not in [m for _, m in sent[len(msgs):]]   # nothing changed
    # Moving a knob updates only its value
    sent.clear()
    bridge._ctl_bindings = [b for b in bridge._ctl_bindings]
    for b in bridge._ctl_bindings:
        b.takeover = "jump"
    bridge._ctl_on_message(DAW, _cc(13, 127, ch=15))
    _send(app, bridge)
    assert [m for _, m in sent] == [text(13, 2, "+100%"),
                                    lcxl3.led_rgb(13, lcxl3.CATEGORY_COLORS["MACRO"]).hex()]
    # Page buttons flip the part/track bank, Track buttons step the cursor
    bridge.setActiveView("JUNO PCM")
    _send(app, bridge, _cc(107, 127), _cc(107, 0), port=DAW)
    assert (bridge._active_view, bridge.seqTrackBank) == ("JUNO PCM", 1)
    _send(app, bridge, _cc(103, 127), _cc(103, 0), port=DAW)
    assert bridge.seqActiveTrack == 7


def test_screen_text_is_ascii_and_fits():
    from src.spectre.control import lcxl3

    assert lcxl3.ascii_bytes("PATCH · TONE 1") == list(b"PATCH - TONE 1")
    m = lcxl3.display_text(13, 1, "Filter Cutoff Offset")
    assert bytes(m.data[8:]) == b"Filter Cutoff "          # 14 on the large lines
    m = lcxl3.display_text(13, 0, "SPECTRE PERFORM MODE")
    assert len(m.data[8:]) == 16
    assert lcxl3.led_category("common.cutoff_offset", "COMMON") == "FILTER"
    assert lcxl3.led_category("common.level", "COMMON") == "COMMON"


def test_screen_names_fit_for_every_target():
    from src.spectre.control.lcxl3 import screen_names
    from src.spectre.core.macro_targets import get_macro_catalog

    assert screen_names("tone.all.lfo1_tvf_depth", "All LFO1 Filter Depth", "LFO") == ("ALL TONES", "LFO1 Flt Dep")
    assert screen_names("tone.3.tvf_cutoff", "T3 Cutoff", "FILTER") == ("TONE 3", "Cutoff")
    assert screen_names("part.level@5", "Part 5 Level", "PART") == ("PART 5", "Level")
    assert screen_names("common.cutoff_offset", "Filter Cutoff Offset", "COMMON") == ("COMMON", "Cutoff Ofs")
    for e in get_macro_catalog():
        title, name = screen_names(e["key"], e["title"], e["category"])
        assert len(title) <= 16 and len(name) <= 14, (e["key"], name)


@pytest.mark.ui
def test_mixer_layer_follows_the_device_and_banks_parts(ui):
    app, bridge, _ = ui
    bridge._ctl_open[DAW] = object()
    bridge._ctl_send = lambda key, msg: None
    bridge._hw_outputs = [PORT + " 36:0", DAW + " 36:1"]
    bridge._ctl_sync_ports = lambda ins: None
    assert bridge.loadControlPreset(str(SURFACE)) == ""
    for b in bridge._ctl_bindings:
        b.takeover = "jump"
    bridge._in_perform = lambda: True
    _send(app, bridge, _cc(30, 1, ch=6), port=DAW)          # device: DAW Mixer mode
    assert bridge._ctl_layer == "MIXER"
    _send(app, bridge, _cc(5, 90, ch=15), port=DAW)         # fader 1 = part 1 level
    assert bridge.patch_state.perf_parts[0].volume == 90
    _send(app, bridge, _cc(107, 127), _cc(107, 0), port=DAW)   # Page > = parts 9-16
    _send(app, bridge, _cc(5, 33, ch=15), port=DAW)
    assert bridge.patch_state.perf_parts[8].volume == 33
    _send(app, bridge, _cc(30, 2, ch=6), port=DAW)          # back to DAW Control
    assert bridge._ctl_layer == ""
    assert any(b["contextTitle"] == "MIXER · PERFORM MODE · PARTS 9-16" for b in bridge.controlBindings)


def _sweep(r, b, start_raw, end_raw, cur):
    """Move a control step by step; the target follows what the resolver sends."""
    step = 1 if end_raw > start_raw else -1
    trace = []
    for raw in range(start_raw, end_raw + step, step):
        t = r.resolve(b, raw, cur)
        if t is not None:
            cur = t
        trace.append((raw, cur))
    return cur, trace


def test_scale_takeover_converges_at_the_end_of_travel():
    r, b = Resolver(), _b(takeover="scale")
    cur, trace = _sweep(r, b, 25, 127, 0.6)            # fader 20% -> top, value at 60%
    assert cur == pytest.approx(1.0)
    values = [v for _, v in trace]
    assert all(b >= a - 0.5 / 127 for a, b in zip(values, values[1:]))   # never steps back
    mid = dict(trace)[76]                              # fader at ~60%: value about 80%
    assert mid == pytest.approx(0.8, abs=0.03)
    assert r.resolve(b, 100, cur) == pytest.approx(100 / 127)   # locked 1:1 now


def test_scale_takeover_going_down():
    r, b = Resolver(), _b(takeover="scale")
    cur, trace = _sweep(r, b, 25, 0, 0.6)              # fader 20% -> bottom, value 60% -> 0
    assert cur == pytest.approx(0.0)
    assert dict(trace)[13] == pytest.approx(0.3, abs=0.04)      # half way down: value halved



@pytest.mark.ui
def test_edited_tone_targets_follow_the_editor(ui):
    app, bridge, _ = ui
    bridge._ctl_bindings = [_b(number=21, target="tone.sel.tvf_cutoff", takeover="jump")]
    bridge.setSelectedTone(3)
    _send(app, bridge, _cc(21, 20))
    assert [t.tvf_cutoff for t in bridge.patch_state.tones][2] == 20
    assert bridge.patch_state.tones[0].tvf_cutoff != 20
    assert bridge.controlBindings[0]["title"] == "Edited Tone Cutoff"


@pytest.mark.ui
def test_mfx_param_targets_use_the_edited_mfx(ui):
    app, bridge, _ = ui
    bridge.setMfxAlgoId(1)                                    # 01 EQUALIZER: P2 = LOW GAIN -15..15 dB
    bridge._ctl_bindings = [_b(number=21, target="mfx.p.2", takeover="jump")]
    assert bridge._ctl_target_title("mfx.p.2") == "MFX Low Gain"
    _send(app, bridge, _cc(21, 127))
    assert bridge.mfxParamValues[1] == 15
    assert bridge._surface_value("mfx.p.2") == "15 dB"
    assert bridge._surface_value("mfx.p.1") in ("200 Hz", "400 Hz")


@pytest.mark.ui
def test_new_catalog_targets(ui):
    app, bridge, _ = ui
    bridge._ctl_bindings = [_b(number=21, target="seq.swing.3", takeover="jump"),
                            _b(number=22, target="vector.orbit_x", takeover="jump"),
                            _b(number=23, target="common.matrix2_sens1", takeover="jump"),
                            _b(number=24, target="tone.1.pitch_env_depth", takeover="jump")]
    _send(app, bridge, _cc(21, 127), _cc(22, 0), _cc(23, 127), _cc(24, 0))
    assert bridge.sequencer.song.tracks[2].swing == pytest.approx(0.75)
    assert bridge.vector.motion.center_x == pytest.approx(0.0)
    assert bridge.patch_state.common.matrix_ctrls[1].sens1 == 127
    assert bridge.patch_state.tones[0].pitch_env_depth == 52



@pytest.mark.ui
def test_context_knobs_follow_the_page(ui):
    app, bridge, _ = ui
    bridge.setActiveView("VECTOR")
    bridge._ctx_refresh()
    titles = [k["title"] for k in bridge.contextKnobs]
    assert titles[:2] == ["Morph X", "Morph Y"] and titles[5] == "Automator"
    bridge.setContextKnob(1, 0.25)
    assert bridge.vector.x == pytest.approx(0.25)
    bridge.setContextKnob(6, 1.0)                              # stepped: last automator
    assert bridge.automator == "chaos"
    bridge._ctx_refresh()
    assert bridge.contextKnobs[5]["text"] == "CHAOS"
    bridge.setContextKnob(6, 0.0)                              # back to none (chaos moves X)
    # A controller's context knob drives the same thing, and follows page changes
    bridge._ctl_bindings = [_b(number=21, target="context.1", takeover="jump")]
    _send(app, bridge, _cc(21, 127))
    assert bridge.vector.x == pytest.approx(1.0)
    bridge.setActiveView("MASTER FX")
    _send(app, bridge, _cc(21, 0))
    assert bridge.patch_state.effects.chorus_level == 0
    bridge.setActiveView("SETLIST")
    bridge._ctx_refresh()
    assert not any(k["active"] for k in bridge.contextKnobs)
    assert not bridge.contextKnobsAvailable
    bridge.setActiveView("WAVETABLE")
    assert bridge.contextKnobsAvailable
    # A physical knob on a stepped target switches without pickup
    bridge._ctl_bindings = [_b(number=21, target="context.3")]  # pickup binding
    _send(app, bridge, _cc(21, 127))
    assert bridge.wavetableSweepMode == "chaos"
    _send(app, bridge, _cc(21, 40))
    assert bridge.wavetableSweepMode == "triangle"


@pytest.mark.ui
def test_manual_entry_binds_a_typed_in_control(ui):
    app, bridge, data = ui
    # Starts from the control that moved last
    _send(app, bridge, _cc(21, 5, ch=2))
    assert bridge.controlManualStart(-1) == {"port": PORT, "channel": 3, "kind": "cc", "number": 21}
    assert bridge.controlManualPorts("")[0] == {"key": "", "title": "ANY PORT"}
    bridge.addControlBinding("tone.all.tvf_cutoff", "", "", 3, "cc", 21, False)
    (b,) = bridge.controlBindings
    assert (b["target"], b["behavior"], b["port"], b["control"]) == (
        "tone.all.tvf_cutoff", "absolute", "ANY PORT", "CH3 CC 21")
    assert json.loads((data / "hardware.json").read_text())["controllers"]["bindings"][0]["channel"] == 2
    # It works like a learned binding
    bridge._ctl_bindings[0].takeover = "jump"
    _send(app, bridge, _cc(21, 100, ch=2))
    assert [t.tvf_cutoff for t in bridge.patch_state.tones] == [100] * 4
    # Buttons and actions press; the same control + scope replaces the old binding
    assert bridge.controlBoundTo("", 3, "cc", 21, "", -1) == "All Cutoff"
    assert bridge.controlBoundTo("", 3, "cc", 21, "SEQUENCER", -1) == ""
    bridge.addControlBinding("action.seq.toggle_play", "", "", 3, "cc", 21, False)
    assert [(b["target"], b["behavior"]) for b in bridge.controlBindings] == [("action.seq.toggle_play", "toggle")]


@pytest.mark.ui
def test_changing_a_bindings_control_keeps_its_options(ui):
    app, bridge, _ = ui
    bridge._ctl_bindings = [_b(number=13, takeover="scale", lo=1.0, hi=0.0, context="VA"),
                            _b(number=14, target="macro.1", context="VA")]
    assert bridge.controlManualStart(0) == {"port": PORT, "channel": 1, "kind": "cc", "number": 13}
    assert bridge.controlBoundTo(PORT, 1, "cc", 13, "VA", 0) == ""      # its own control
    bridge.setControlBindingControl(0, PORT, 16, "note", 60)
    first = bridge.controlBindings[0]
    assert (first["control"], first["takeover"], first["lo"], first["context"]) == (
        "CH16 NOTE 60", "scale", 1.0, "VA")
    # Moving it onto the other binding's control replaces that one, in place
    bridge.setControlBindingControl(0, PORT, 1, "cc", 14)
    assert [b["target"] for b in bridge.controlBindings] == ["tone.all.tvf_cutoff"]
    assert bridge.controlLabel(PORT, 1, "cc", 13) == "Knob A1 · CH1 CC 13"


@pytest.mark.ui
def test_macros_are_named_after_their_links_until_renamed(ui):
    from src.spectre.core.patch_state import auto_macro_name

    app, bridge, _ = ui
    assert bridge.macroNames[0] == "CUTOFF OFS"
    assert bridge.macroCustomNames[0] == ""
    assert bridge._ctl_target_title("macro.1") == "M1 CUTOFF OFS"
    # The name follows the links
    bridge.removeMacroTarget(1, 0)
    assert bridge.macroNames[0] == "M1"
    assert bridge._ctl_target_title("macro.1") == "M1"
    bridge.addMacroTarget(1, "tone.1.tvf_cutoff")
    assert bridge.macroNames[0] == "T1 CUTOFF"
    bridge.addMacroTarget(1, "tone.2.tvf_cutoff")
    assert bridge.macroNames[0] == "T1 CUTOFF +1"
    # A typed name sticks; clearing it goes back to automatic
    bridge.setMacroName(1, "wobble")
    assert (bridge.macroNames[0], bridge.macroCustomNames[0]) == ("WOBBLE", "WOBBLE")
    assert bridge._ctl_target_title("macro.1") == "M1 WOBBLE"
    bridge.setMacroName(1, "  ")
    assert (bridge.macroNames[0], bridge.macroCustomNames[0]) == ("T1 CUTOFF +1", "")
    assert bridge._short_target_name("part.level") == "Part Level"
    assert bridge._short_target_name("part.level@3") == "P3 Level"
    assert auto_macro_name(2, ["Cutoff", "Reso"]) == "CUTOFF+RESO"
    assert auto_macro_name(2, ["T2 LFO1 Pitch Dep"]) == "T2 LFO1 PITCH"


def test_automatic_macro_names_survive_save_and_load():
    from src.spectre.core.patch_state import PatchState
    from src.spectre.core.spectre_format import patch_state_from_dict, patch_state_to_dict

    ps = PatchState()
    ps.macros[1].name = "WOBBLE"
    back = patch_state_from_dict(patch_state_to_dict(ps))
    assert [m.name for m in back.macros[:2]] == ["", "WOBBLE"]


def test_clip_launch_actions(tmp_path, monkeypatch):
    monkeypatch.setenv("JUNOSPECTRE_DATA_DIR", str(tmp_path))
    from src.spectre.ui.bridge import SpectreBridge

    b = SpectreBridge()
    clips = b.getControlTargets("CLIP", "")
    assert len(clips) == 16 * 8 and clips[0]["key"] == "action.seq.launch.1.1"
    assert clips[-1]["title"] == "Launch Track 16 Clip 8"
    assert any(a["key"] == "action.seq.launch.12.3" for a in b.getControlTargets("ALL", "track 12 clip 3"))
    b._ctl_run_action("seq.launch.12.3")
    track = b.sequencer.song.tracks[11]
    assert (track.queued_clip_idx, track.selected_clip_idx) == (2, 2)
    b.close_audio()


@pytest.mark.ui
def test_picked_bindings_follow_binding_and_context_changes(ui):
    app, bridge, _ = ui
    bridge._ctl_bindings = [_b(number=13), _b(number=13, target="macro.1", context="VA")]
    ctl = (PORT, 0, "cc", 13)
    bridge.setActiveView("JUNO PCM")
    assert [b.target for b in bridge._ctl_pick(*ctl)] == ["tone.all.tvf_cutoff"]
    bridge.setActiveView("VA")
    assert [b.target for b in bridge._ctl_pick(*ctl)] == ["macro.1"]
    bridge.setControlBindingOption(1, "context", "MIXER")
    assert [b.target for b in bridge._ctl_pick(*ctl)] == ["tone.all.tvf_cutoff"]
    bridge.removeControlBinding(0)
    assert bridge._ctl_pick(*ctl) == ()


@pytest.mark.ui
def test_alt_layer_tap_latches_and_hold_is_momentary(ui, monkeypatch):
    from src.spectre.ui.bridge import controllers as ctl_mod

    app, bridge, _ = ui
    bridge._ctl_open[DAW] = object()
    bridge._ctl_send = lambda key, msg: None
    bridge._hw_outputs = [PORT + " 36:0", DAW + " 36:1"]
    bridge._ctl_sync_ports = lambda ins: None
    assert bridge.loadControlPreset(str(SURFACE)) == ""
    for b in bridge._ctl_bindings:
        b.takeover = "jump"
    clock = [100.0]
    monkeypatch.setattr(ctl_mod.time, "monotonic", lambda: clock[0])

    def nov(down, hold=0.1):
        if not down:
            clock[0] += hold
        _send(app, bridge, _cc(104, 127 if down else 0), port=DAW)

    alt = lambda: bridge._ctl_state()["ALT"] == "ON"
    row_a = lambda: bridge._ctl_resolve(bridge._surface_binding(DAW, 13).target)

    bridge.setActiveView("JUNO PCM")
    assert row_a() == "macro.1"
    nov(1); nov(0)                                         # tap: latched
    assert alt()
    assert row_a() == "tone.sel.tvf_cutoff"                # row A = the page's context knobs
    _send(app, bridge, _cc(41, 127), _cc(41, 0), port=DAW)  # button 5 = Mod Matrix page
    assert bridge._active_view == "MOD MATRIX"
    bridge.setActiveView("SETLIST")
    assert row_a() == "macro.1"                            # no context on this page: macros stay
    _send(app, bridge, _cc(107, 127), _cc(107, 0), port=DAW)   # Page > = next app page
    assert bridge._active_view == "JUNO PCM"
    nov(1); nov(0)                                         # tap again: off
    assert not alt() and row_a() == "macro.1"

    nov(1)                                                 # hold and use: only while held
    assert alt()
    _send(app, bridge, _cc(5, 30, ch=15), port=DAW)        # fader 1 = pitch env attack
    assert [t.pitch_env_t1 for t in bridge.patch_state.tones] == [30] * 4
    nov(0, hold=0.1)
    assert not alt()
    nov(1); nov(0, hold=1.0)                               # long press, nothing used: momentary
    assert not alt()

    # Scenes: Track > selects, Play launches, Record stops
    nov(1)
    _send(app, bridge, _cc(102, 127), _cc(102, 0), _cc(102, 127), _cc(102, 0), port=DAW)
    assert bridge._ctl_scene == 2
    _send(app, bridge, _cc(116, 127), _cc(116, 0), port=DAW)
    assert all(t.queued_clip_idx == 2 for t in bridge.sequencer.song.tracks)
    _send(app, bridge, _cc(118, 127), _cc(118, 0), port=DAW)
    assert all(t.queued_clip_idx == -1 for t in bridge.sequencer.song.tracks)
    nov(0)

    # Mixer: the alt layer keeps the faders as levels
    bridge._in_perform = lambda: True
    _send(app, bridge, _cc(30, 1, ch=6), port=DAW)
    nov(1)
    _send(app, bridge, _cc(5, 77, ch=15), port=DAW)
    assert bridge.patch_state.perf_parts[0].volume == 77
    nov(0)


@pytest.mark.ui
def test_touch_events_are_not_controls(ui, monkeypatch):
    from src.spectre.ui.bridge import controllers as ctl_mod

    monkeypatch.setattr(ctl_mod.time, "monotonic", lambda: 100.0)   # every press is a quick tap
    app, bridge, _ = ui
    bridge._ctl_open[DAW] = object()
    sent = []
    bridge._ctl_send = lambda key, msg: sent.append(msg.hex())
    bridge._hw_outputs = [PORT + " 36:0", DAW + " 36:1"]
    bridge._ctl_sync_ports = lambda ins: None
    assert bridge.loadControlPreset(str(SURFACE)) == ""
    assert "B6 47 00" in sent      # touch events off: the LCXL3 sends them on move start/stop
    before = bridge.patch_state.common.cutoff_offset
    _send(app, bridge, _cc(29, 127, ch=14), port=DAW)      # touch knob C1 (cutoff)
    assert bridge.patch_state.common.cutoff_offset == before
    assert (DAW, 29) in bridge._ctl_touched
    _send(app, bridge, _cc(29, 0, ch=14), port=DAW)
    assert not bridge._ctl_touched
    # Never learned: learn waits for a real move
    bridge.startControlLearn("macro.3")
    _send(app, bridge, _cc(29, 127, ch=14), port=DAW)
    assert bridge.controlLearnTarget == "macro.3"
    _send(app, bridge, _cc(29, 0, ch=14), port=DAW)
    # Touching a control while the alt button is held makes the layer momentary
    bridge._ctl_learn_target = ""
    _send(app, bridge, _cc(104, 127), port=DAW)
    _send(app, bridge, _cc(5, 127, ch=14), _cc(5, 0, ch=14), port=DAW)
    _send(app, bridge, _cc(104, 0), port=DAW)
    assert bridge._ctl_state()["ALT"] == ""


@pytest.mark.ui
def test_touched_control_highlights_or_toasts(ui):
    from PyQt6.QtCore import QObject

    app, bridge, _ = ui
    bridge._ctl_open[DAW] = object()
    bridge._ctl_send = lambda key, msg: None
    bridge._hw_outputs = [PORT + " 36:0", DAW + " 36:1"]
    bridge._ctl_sync_ports = lambda ins: None
    assert bridge.loadControlPreset(str(SURFACE)) == ""
    toast = next(w.findChild(QObject, "touchToast") for w in app.topLevelWindows()
                 if w.findChild(QObject, "touchToast"))
    bridge.setActiveView("JUNO PCM")

    def settle():
        for _ in range(5):
            app.processEvents()

    # Portamento (knob C7) has no slider on the PCM page: the toast shows it
    _send(app, bridge, _cc(35, 127, ch=14), port=DAW)
    settle()
    assert bridge.touchedKey == "common.portamento_time"
    assert bridge.touchedControl["name"] == "Porta Time"
    assert toast.property("showing")
    _send(app, bridge, _cc(35, 0, ch=14), port=DAW)
    assert bridge._touch_timer.isActive()        # lingers a moment, then hides
    bridge._touch_hide()
    settle()
    assert bridge.touchedKey == "" and not toast.property("showing")

    # Key follow (knob C3) is on the page: highlighted there, no toast
    _send(app, bridge, _cc(31, 127, ch=14), port=DAW)
    settle()
    assert bridge.touchedKey == "tone.1.tvf_keyfollow"
    assert not toast.property("showing")
    _send(app, bridge, _cc(31, 0, ch=14), port=DAW)
    bridge._touch_hide()

    # A move without a touch report shows it too (and its new value)
    for b in bridge._ctl_bindings:
        b.takeover = "jump"
    _send(app, bridge, _cc(29, 127, ch=15), port=DAW)
    settle()
    # Cutoff writes the selected tone's own filter (not the patch offset)
    assert bridge.touchedKey == "tone.1.tvf_cutoff" and bridge.touchedControl["value"] == "127"
    assert bridge.patch_state.tones[0].tvf_cutoff == 127
    assert bridge._touch_timer.isActive()


@pytest.mark.ui
def test_va_page_tone_targets_ignore_the_pcm_link(ui):
    app, bridge, _ = ui
    bridge._ctl_open[DAW] = object()
    bridge._ctl_send = lambda key, msg: None
    bridge._hw_outputs = [PORT + " 36:0", DAW + " 36:1"]
    bridge._ctl_sync_ports = lambda ins: None
    assert bridge.loadControlPreset(str(SURFACE)) == ""
    for b in bridge._ctl_bindings:
        b.takeover = "jump"
    bridge.patch_state.auto_detune = False
    tones = bridge.patch_state.tones
    for t in tones:
        t.fine_tune = 64
    bridge.setActiveView("VA")
    bridge.setLinkedMode(True)                 # the PCM page's link switch
    bridge.setSelectedTone(2)

    # Fine tune (knob C6) detunes only the selected oscillator
    _send(app, bridge, _cc(34, 0, ch=15), port=DAW)
    assert [t.fine_tune for t in tones] == [64, 14, 64, 64]
    assert bridge.patch_state.custom_detune_cache[1] == 14
    assert bridge.touchedKey == "tone.2.pitch_fine"
    for _ in range(5):
        app.processEvents()
    def items(item):
        yield item
        for child in item.childItems():
            yield from items(child)

    lit = sorted((o.property("ctlKey"), o.parentItem().metaObject().className().split("_")[0])
                 for w in app.topLevelWindows() for o in items(w.contentItem())
                 if o.metaObject().className().startswith("TouchHighlight") and o.property("visible"))
    # Oscillator 2's FINE and the context strip's T2 fine card, not all four oscillators
    assert lit == [("tone.2.pitch_fine", "EncoderCard"), ("tone.2.pitch_fine", "TouchFader")]

    # With Auto Detune on, the same knob sets its amount
    bridge.setAutoDetune(True)
    _send(app, bridge, _cc(34, 127, ch=15), port=DAW)
    assert bridge.autoDetuneCents == 50

    # The sculptor's ADSR switch converts all four tones, link switch or not
    bridge.setLinkedMode(False)
    for t in tones:
        t.set_env_curve("tvf", [10, 30, 50, 40], [0, 127, 90, 60, 0])
    bridge.setEnvAdsr("TVF", True)
    assert all(t.env_is_adsr("tvf") for t in tones)


@pytest.mark.ui
def test_fine_tune_knob_follows_the_page_and_auto_detune(ui):
    app, bridge, _ = ui
    ps = bridge.patch_state
    bridge.setAutoDetune(False)
    for t, f in zip(ps.tones, (60, 68, 64, 64)):           # a manual detune around 0
        t.fine_tune = f
    ps.custom_detune_cache = [t.fine_tune for t in ps.tones]

    # Wavetable / Vector: the master fine tune, which keeps the detune
    bridge.setActiveView("VECTOR")
    assert bridge._ctl_resolve("tone.sel.pitch_fine") == "detune.master"
    bridge._ctl_apply("tone.sel.pitch_fine", 60 / 100)    # -50..+50 -> +10
    assert bridge.masterFine == 10
    assert [t.fine_tune for t in ps.tones] == [70, 78, 74, 74]
    assert bridge._surface_names("detune.master", "") == ("ALL TONES", "Master Fine")
    assert bridge._surface_value("detune.master") == "+10 c"

    # Auto Detune spreads around the master; moving the master shifts the saved manual detune too
    bridge.setAutoDetune(True)
    bridge.setAutoDetuneCents(20)
    assert [t.fine_tune for t in ps.tones] == [54, 94, 64, 84]
    bridge.sculptPitchFine(0)
    assert [t.fine_tune for t in ps.tones] == [44, 84, 54, 74]
    assert bridge._ctl_resolve("tone.sel.pitch_fine") == "detune.master"   # still master here

    # PCM / VA: the Auto Detune amount while it is on, the selected tone otherwise
    bridge.setActiveView("JUNO PCM")
    assert bridge._ctl_resolve("tone.sel.pitch_fine") == "detune.auto"
    bridge._ctl_apply("tone.sel.pitch_fine", 0.2)          # 0..50 -> 10
    assert bridge.autoDetuneCents == 10
    assert [t.fine_tune for t in ps.tones] == [54, 74, 59, 69]
    bridge.setPitchFine(30)                                # the PCM fine tune is locked meanwhile
    assert ps.tones[0].fine_tune == 54
    bridge._ctx_refresh()
    assert "Auto Detune" in [k["title"] for k in bridge.contextKnobs]   # the strip's fine card too
    bridge.setAutoDetune(False)
    assert [t.fine_tune for t in ps.tones] == [60, 68, 64, 64]          # the manual detune, re-centred
    assert bridge._ctl_resolve("tone.sel.pitch_fine") == "tone.sel.pitch_fine"
    bridge.setActiveView("VA")
    assert bridge._ctl_resolve("tone.sel.pitch_fine") == "tone.sel.pitch_fine"


@pytest.mark.ui
def test_sculpt_page_filter_knobs_move_every_tone(ui):
    app, bridge, _ = ui
    tones = bridge.patch_state.tones
    for t in tones:
        t.tvf_cutoff = 64
    bridge.setLinkedMode(False)
    bridge.setSelectedTone(2)
    bridge.setActiveView("JUNO PCM")            # the selected tone only
    bridge._ctl_apply("tone.sel.tvf_cutoff", 1.0)
    assert [t.tvf_cutoff for t in tones] == [64, 127, 64, 64]
    bridge.setActiveView("VA")                  # master filter: every tone
    bridge._ctl_apply("tone.sel.tvf_cutoff", 0.0)
    assert [t.tvf_cutoff for t in tones] == [0, 0, 0, 0]
    bridge._ctl_apply("tone.sel.pitch_fine", 0.0)   # oscillator params stay per tone
    assert [t.fine_tune for t in tones].count(14) == 1


@pytest.mark.ui
def test_controller_moves_notify_the_editors(ui):
    app, bridge, _ = ui
    bridge.setActiveView("JUNO PCM")
    fired = []
    for sig in ("tvfEnvDepthChanged", "tvaPanChanged", "tvfAttackChanged", "tvaSustainChanged",
                "envShapeChanged", "routingChanged", "macrosChanged"):
        getattr(bridge, sig).connect(lambda *a, s=sig: fired.append((s,) + a))

    def moved(target, t=0.9):
        fired.clear()
        bridge._ctl_apply(target, t)
        return {f[0] for f in fired}

    assert {"tvfEnvDepthChanged", "envShapeChanged"} <= moved("tone.sel.tvf_env_depth")
    assert ("envShapeChanged", "TVF") in fired
    assert "tvaPanChanged" in moved("tone.1.tva_pan")
    assert "tvfAttackChanged" in moved("tone.all.tvf_attack")
    assert "tvaSustainChanged" in moved("tone.all.tva_sustain")
    assert ("envShapeChanged", "TVA") in fired
    assert "routingChanged" in moved("tone.sel.chorus_send")
    # macrosChanged re-reads every macro list (~7 ms on the Pi): only when a macro drives it
    assert "macrosChanged" not in moved("tone.all.lfo2_rate")
    assert "macrosChanged" in moved("common.analog_feel")     # macro 6 of the default deck
    fired.clear()
    bridge.setMacro(1, 0.5)
    assert [f[0] for f in fired].count("macrosChanged") == 1


@pytest.mark.ui
def test_part_mixer_moves_refresh_the_strips_throttled(ui):
    app, bridge, _ = ui
    bridge._sound_mode = "PERFORM"
    count = []
    bridge.perfPartsChanged.connect(lambda: count.append(1))
    for i in range(20):
        bridge._ctl_apply("part.level@1", i / 40)
    assert len(count) == 1                      # the first move shows at once
    assert bridge.patch_state.perf_parts[0].volume == round(19 / 40 * 127)
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline and len(count) < 2:
        app.processEvents()
    assert len(count) == 2                      # and the last one when the interval ends


@pytest.mark.ui
def test_solo_mute_and_shift_buttons(ui, monkeypatch):
    from src.spectre.ui.bridge import controllers as ctl_mod

    clock = [100.0]
    monkeypatch.setattr(ctl_mod.time, "monotonic", lambda: clock[0])
    app, bridge, _ = ui
    bridge._ctl_open[DAW] = object()
    bridge._ctl_send = lambda key, msg: None
    bridge._hw_outputs = [PORT + " 36:0", DAW + " 36:1"]
    bridge._ctl_sync_ports = lambda ins: None
    assert bridge.loadControlPreset(str(SURFACE)) == ""
    press = lambda num: _send(app, bridge, _cc(num, 127), _cc(num, 0), port=DAW)  # noqa: E731
    shift = lambda on: _send(app, bridge, _cc(63, 127 if on else 0, ch=6), port=DAW)  # noqa: E731
    tones = bridge.patch_state.tones
    muted = lambda: [t.muted for t in tones]  # noqa: E731
    bridge.setSelectedTone(2)

    # PATCH mode: Solo/Mute act on the selected tone; a second Solo gives the old mutes back
    press(65)
    assert muted() == [True, False, True, True]
    press(65)
    assert muted() == [False, False, False, False]
    press(66)
    assert muted() == [False, True, False, False]
    shift(True)
    press(66)                                   # Shift + Mute: unmute all
    assert muted() == [False, False, False, False]
    press(39)                                   # Shift + tone button 3: mute tone 3, keep the selection
    assert muted() == [False, False, True, False] and bridge.selectedTone == 2
    bpm = bridge.bpm
    press(102)                                  # Shift + Track >: tempo +1
    assert bridge.bpm == bpm + 1
    press(116)                                  # Shift + Play: tap tempo
    clock[0] += 0.5
    press(116)
    assert bridge.bpm == 120.0
    shift(False)
    press(39)                                   # without Shift: select tone 3 again
    assert bridge.selectedTone == 3

    # PERFORM mode: the edited part
    bridge._in_perform = lambda: True
    part = bridge.patch_state.perf_parts[bridge._editedPart() - 1]
    press(65)
    assert part.solo
    shift(True)
    press(65)                                   # Shift + Solo: clear all solos
    shift(False)
    assert not any(p.solo for p in bridge.patch_state.perf_parts)


@pytest.mark.ui
def test_shift_move_resets_to_the_loaded_value(ui):
    app, bridge, _ = ui
    bridge._ctl_open[DAW] = object()
    bridge._ctl_send = lambda key, msg: None
    bridge._hw_outputs = [PORT + " 36:0", DAW + " 36:1"]
    bridge._ctl_sync_ports = lambda ins: None
    assert bridge.loadControlPreset(str(SURFACE)) == ""
    for b in bridge._ctl_bindings:
        b.takeover = "jump"
    shift = lambda on: _send(app, bridge, _cc(63, 127 if on else 0, ch=6), port=DAW)  # noqa: E731
    tones = bridge.patch_state.tones
    bridge.setActiveView("JUNO PCM")
    bridge.setLinkedMode(True)
    for t, c in zip(tones, (100, 50, 70, 90)):
        t.tvf_cutoff = c
    bridge._emit_all_state_signals()             # a load: this is the loaded sound
    loaded_macro = bridge.patch_state.macros[0].value

    _send(app, bridge, _cc(29, 0, ch=15), port=DAW)     # cutoff (all linked tones) down
    _send(app, bridge, _cc(13, 127, ch=15), port=DAW)   # macro 1 up
    assert [t.tvf_cutoff for t in tones] == [0, 0, 0, 0]
    shift(True)
    _send(app, bridge, _cc(29, 5, ch=15), port=DAW)     # Shift + move: each tone its own loaded value
    _send(app, bridge, _cc(13, 20, ch=15), port=DAW)
    shift(False)
    assert [t.tvf_cutoff for t in tones] == [100, 50, 70, 90]
    assert bridge.patch_state.macros[0].value == loaded_macro

    # A save makes the saved state the loaded one
    _send(app, bridge, _cc(29, 127, ch=15), port=DAW)
    bridge._saved_as_loaded()
    _send(app, bridge, _cc(29, 0, ch=15), port=DAW)
    shift(True)
    _send(app, bridge, _cc(29, 5, ch=15), port=DAW)
    shift(False)
    assert [t.tvf_cutoff for t in tones] == [127, 127, 127, 127]

    # PERFORM: part levels come from the performance as loaded; an edited
    # part keeps the copy from before its edits when it is shown again
    bridge._in_perform = lambda: True
    bridge.patch_state.perf_parts[0].volume = 90
    bridge._forget_loaded()
    bridge._emit_all_state_signals()
    bridge._ctl_apply("part.level@1", 0.0)
    assert bridge._ctl_reset("part.level@1")
    assert bridge.patch_state.perf_parts[0].volume == 90
    part = bridge.patch_state.perf_parts[bridge._editedPart() - 1]
    tones[0].tvf_cutoff = 10
    part.modified = True
    bridge._emit_all_state_signals()             # e.g. switching back to this edited part
    assert bridge._loaded_value(bridge._ctl_keys("tone.1.tvf_cutoff")[0]) == 127


@pytest.mark.ui
def test_shift_tap_arms_a_reset_for_the_next_moved_knob(ui, monkeypatch):
    from src.spectre.control import lcxl3
    from src.spectre.ui.bridge import controllers as ctl_mod

    clock = [100.0]
    monkeypatch.setattr(ctl_mod.time, "monotonic", lambda: clock[0])
    app, bridge, _ = ui
    bridge._ctl_open[DAW] = object()
    sent = []
    bridge._ctl_send = lambda key, msg: sent.append(msg.hex())
    bridge._hw_outputs = [PORT + " 36:0", DAW + " 36:1"]
    bridge._ctl_sync_ports = lambda ins: None
    assert bridge.loadControlPreset(str(SURFACE)) == ""
    for b in bridge._ctl_bindings:
        b.takeover = "jump"
    tone = bridge.patch_state.tones[0]
    bridge.setActiveView("JUNO PCM")
    bridge.setLinkedMode(False)
    bridge.setSelectedTone(1)
    tone.tvf_cutoff = 100
    bridge._emit_all_state_signals()                       # loaded: cutoff 100

    def tap(hold=0.1):
        _send(app, bridge, _cc(63, 127, ch=6), port=DAW)
        clock[0] += hold
        _send(app, bridge, _cc(63, 0, ch=6), port=DAW)

    def turn(*values, gap=0.05):
        for v in values:
            clock[0] += gap
            _send(app, bridge, _cc(29, v, ch=15), port=DAW)

    turn(10)
    assert tone.tvf_cutoff == 10
    tap()                                                  # armed: the screen says so
    assert bridge._reset_armed()
    assert lcxl3.display_text(lcxl3.STATIONARY, 1, "MOVE TO RESET").hex() in sent
    turn(11, 12, 13)                                       # the whole turn is the reset
    assert tone.tvf_cutoff == 100 and not bridge._reset_armed()
    clock[0] += 1.0                                        # rested: the knob works again
    turn(20)
    assert tone.tvf_cutoff == 20

    tap()
    clock[0] += 3.5                                        # too late: it expired
    turn(21)
    assert tone.tvf_cutoff == 21
    tap()
    tap()                                                  # a second tap cancels
    assert not bridge._reset_armed()
    tap(hold=1.0)                                          # a long press is no tap
    assert not bridge._reset_armed()
