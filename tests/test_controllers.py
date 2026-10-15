"""MIDI controller bindings: mapping math, learn, targets, presets."""

import json
import time
from pathlib import Path

import pytest

from src.spectre.control.mapping import Binding, Resolver
from src.spectre.ui.app import create_application

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
    assert text(21, 0, "TONE 1") in msgs                     # row B = context knobs: PCM page = edited tone
    assert text(21, 1, "Cutoff") in msgs
    bridge.setActiveView("SETLIST")
    bridge._ctl_feedback_tick()
    assert lcxl3.led_rgb(21, lcxl3.OFF).hex() in [m for _, m in sent]   # no context knobs there
    bridge.setActiveView("JUNO PCM")
    bridge._ctl_feedback_tick()
    # Moving a knob updates only its value
    sent.clear()
    bridge._ctl_bindings = [b for b in bridge._ctl_bindings]
    for b in bridge._ctl_bindings:
        b.takeover = "jump"
    bridge._ctl_on_message(DAW, _cc(13, 127, ch=15))
    _send(app, bridge)
    assert [m for _, m in sent] == [text(13, 2, "+100%"),
                                    lcxl3.led_rgb(13, lcxl3.CATEGORY_COLORS["MACRO"]).hex()]
    # Page buttons switch the app page; the stationary screen follows
    sent.clear()
    bridge.setActiveView("JUNO PCM")
    _send(app, bridge, _cc(107, 127), _cc(107, 0), port=DAW)
    assert bridge._active_view == "VECTOR"
    bridge._ctl_feedback_tick()
    assert lcxl3.display_text(lcxl3.STATIONARY, 1, "VECTOR").hex() in [m for _, m in sent]


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
    from src.spectre.ui.bridge.controllers import ACTIONS

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
    _send(app, bridge, _cc(102, 127), _cc(102, 0), port=DAW)   # Track > = parts 9-16
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
    assert "CLIP" in b.getControlCategories()
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
