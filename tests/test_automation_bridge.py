"""Sequencer automation lanes in the bridge: writes, macros, restore, knobs, load."""

import pytest

from spectre.control.mapping import Binding
from spectre.ui.app import create_application

PORT = "LCXL3 1:LCXL3 1 MIDI In"
CUTOFF = "tone.1.tvf_cutoff"


@pytest.fixture
def ui(monkeypatch, tmp_path):
    monkeypatch.setenv("JUNOSPECTRE_DATA_DIR", str(tmp_path))
    app, qml_engine, bridge = create_application(platform="offscreen")
    yield app, bridge
    bridge.sequencer.stop()
    del qml_engine


def _tick(app, bridge, start, end=None):
    """Drive the sequencer clock by hand, then let the GUI thread apply."""
    for t in range(start, (start + 1) if end is None else end):
        bridge.sequencer._on_clock_tick(t % 384, t)
    app.processEvents()


def _hold(bridge, lane, step, value):
    """A hard step (painted steps glide by default)."""
    bridge.seqSetLaneStep(lane, step, value)
    bridge.seqSetLaneStepGlide(lane, step, False)


def _stop(app, bridge):
    bridge.sequencer.stop()
    app.processEvents()


@pytest.mark.ui
def test_lane_writes_its_target_and_restores_it_on_stop(ui):
    app, bridge = ui
    tone = bridge.patch_state.tones[0]
    before = tone.tvf_cutoff
    bridge.seqSetLaneTarget(0, CUTOFF)
    _hold(bridge, 0, 0, 0.25)
    _hold(bridge, 0, 4, 1.0)
    _tick(app, bridge, 0)
    assert tone.tvf_cutoff == round(0.25 * 127)
    _tick(app, bridge, 1, 100)
    assert tone.tvf_cutoff == 127
    _stop(app, bridge)
    assert tone.tvf_cutoff == before


@pytest.mark.ui
def test_lane_sets_the_base_and_macros_still_add_on_top(ui):
    app, bridge = ui
    bridge.addMacroTarget(1, CUTOFF)
    bridge.setMacro(1, 0.5)
    base_before = bridge.patch_state.macro_bases[CUTOFF]
    bridge.seqSetLaneTarget(0, CUTOFF)
    bridge.seqSetLaneStep(0, 0, 40 / 127)
    _tick(app, bridge, 0)
    assert bridge.patch_state.macro_bases[CUTOFF] == pytest.approx(40)
    assert bridge.patch_state.tones[0].tvf_cutoff > 40          # base + macro
    _stop(app, bridge)
    assert bridge.patch_state.macro_bases[CUTOFF] == pytest.approx(base_before, abs=0.5)


@pytest.mark.ui
def test_lane_on_a_macro_moves_the_macro(ui):
    app, bridge = ui
    bridge.addMacroTarget(2, CUTOFF)
    bridge.seqSetLaneTarget(0, "macro.2")
    bridge.seqSetLaneStep(0, 0, 1.0)
    _tick(app, bridge, 0)
    assert bridge.patch_state.macros[1].value == pytest.approx(1.0)
    _stop(app, bridge)
    assert bridge.patch_state.macros[1].value == pytest.approx(0.0, abs=0.01)


@pytest.mark.ui
def test_knobs_on_an_automated_target_are_ignored(ui):
    app, bridge = ui
    bridge._ctl_open[PORT] = object()
    bridge._ctl_bindings = [Binding(port=PORT, channel=0, kind="cc", number=13,
                                    target=CUTOFF, takeover="jump")]
    bridge.seqSetLaneTarget(0, CUTOFF)
    bridge.seqSetLaneStep(0, 0, 0.5)
    _tick(app, bridge, 0)
    bridge._ctl_handle((PORT, 0, "cc", 13, 10))
    assert bridge.patch_state.tones[0].tvf_cutoff == 64
    assert "(automated)" in bridge.controlActivity
    _stop(app, bridge)                                 # the lane let go: the knob works again
    bridge._ctl_handle((PORT, 0, "cc", 13, 10))
    assert bridge.patch_state.tones[0].tvf_cutoff == 10
    bridge._ctl_open.clear()


@pytest.mark.ui
def test_changing_the_target_lets_go_of_the_old_one(ui):
    app, bridge = ui
    tones = bridge.patch_state.tones
    before = tones[0].tvf_cutoff
    bridge.seqSetLaneTarget(0, CUTOFF)
    bridge.seqSetLaneStep(0, 0, 0.0)
    _tick(app, bridge, 0)
    assert tones[0].tvf_cutoff == 0
    bridge.seqSetLaneTarget(0, "tone.1.tvf_resonance")
    _tick(app, bridge, 1)
    assert tones[0].tvf_cutoff == before
    assert tones[0].tvf_resonance == 0


@pytest.mark.ui
def test_lane_editing_slots_and_load(ui):
    app, bridge = ui
    bridge.seqSetLaneTarget(0, "not.a.target")
    assert bridge.seqAutomationLanes[0]["target"] == ""
    bridge.seqSetLaneTarget(0, "tone.all.tvf_cutoff")
    lane = bridge.seqAutomationLanes[0]
    assert lane["title"] and lane["clockDivider"] == "1/16" and len(lane["clips"]) == 8
    for i in range(16):
        _hold(bridge, 0, i, float(i % 2))
    # 16 changes per 2 s loop at 120 BPM, 4 tones each
    assert bridge.seqAutomationLoad == pytest.approx(32.0)
    assert bridge.seqAutomationBudget == pytest.approx(125.0)
    bridge.setBpm(60.0)
    assert bridge.seqAutomationLoad == pytest.approx(16.0)
    bridge.seqSetLaneStep(0, 1, -1)
    bridge.seqSetLaneStepGlide(0, 0, True)
    steps = bridge.seqLaneSteps(0)
    assert (steps[1]["value"], steps[1]["glide"]) == (-1.0, False)
    assert (steps[0]["value"], steps[0]["glide"]) == (0.0, True)
    # The curve: step 0 glides from 0 across the emptied step 1 to step 2's 1.0
    bridge.seqSetLaneStep(0, 2, 1.0)
    steps = bridge.seqLaneSteps(0)
    assert (steps[0]["start"], steps[0]["end"]) == (0.0, pytest.approx(64 / 127))
    assert (steps[1]["start"], steps[1]["end"]) == (pytest.approx(64 / 127), 1.0)
    assert steps[2]["start"] == steps[2]["end"] == 1.0
    bridge.seqSetLaneClipLength(0, 8)
    assert len(bridge.seqLaneSteps(0)) == 8
    bridge.seqClearLaneClip(0)
    assert bridge.seqAutomationLoad == 0.0
    assert not bridge.seqAutomationLanes[0]["clips"][0]["hasValues"]


# -- PERFORM: parts, layers, track links ------------------------------------------

from contextlib import contextmanager
from unittest.mock import MagicMock

from spectre.core.patch_state import PatchCommonState, ToneState


@pytest.fixture
def perf(ui):
    app, bridge = ui
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
    juno.coalesced_writes = None
    juno.set_patch_offsets.side_effect = lambda **kw: juno.writes.append((juno.scope, kw))
    juno.read_patch_common.side_effect = lambda timeout=1.0: PatchCommonState(cutoff_offset=50)
    juno.read_all_tones.side_effect = lambda timeout=1.0: [ToneState(tone_index=i) for i in range(1, 5)]
    bridge.juno = juno
    bridge._sound_mode = "PERFORM"
    bridge.patch_state.sound_mode = "PERFORM"
    bridge.patch_state.active_perf_part = 1
    bridge.patch_state.common.cutoff_offset = 64
    bridge._macro_part_states = {}
    bridge._macro_async_parts = False
    return app, bridge, juno


@pytest.mark.ui
def test_linked_lane_writes_to_its_tracks_parts(perf):
    app, bridge, juno = perf
    bridge.seqSetTrackTargetPart(0, 3)
    bridge.seqToggleTrackLayer(0, 5)
    bridge.seqSetLaneTarget(0, "common.cutoff_offset")
    lane = bridge.seqAutomationLanes[0]
    assert (lane["linkTrack"], lane["targetPart"], lane["layerParts"]) == (0, 3, [5])
    _hold(bridge, 0, 0, 1.0)
    _tick(app, bridge, 0)
    assert (3, {"cutoff": 127}) in juno.writes and (5, {"cutoff": 127}) in juno.writes
    _hold(bridge, 0, 8, 0.0)      # 2 changes per 2 s loop, on 2 parts
    assert bridge.seqAutomationLoad == pytest.approx(2.0)
    # Dropping the track's layer lets go of part 5 (back to its own 50)
    juno.writes.clear()
    bridge.seqToggleTrackLayer(0, 5)
    _tick(app, bridge, 1)
    assert juno.writes == [(5, {"cutoff": 50})]
    _stop(app, bridge)
    assert (3, {"cutoff": 50}) in juno.writes


@pytest.mark.ui
def test_unlinked_lane_keeps_the_parts_and_has_its_own(perf):
    app, bridge, juno = perf
    bridge.seqSetTrackTargetPart(1, 4)
    bridge.seqSetLaneTarget(1, "common.cutoff_offset")
    bridge.seqSetLaneLink(1, -1)
    lane = bridge.seqAutomationLanes[1]
    assert (lane["linkTrack"], lane["targetPart"]) == (-1, 4)       # nothing jumps
    bridge.seqToggleLaneLayer(1, 2)
    bridge.seqSetLanePart(1, 6)
    assert (bridge.seqAutomationLanes[1]["targetPart"],
            bridge.seqAutomationLanes[1]["layerParts"]) == (6, [2])
    bridge.seqSetLaneStep(1, 0, 0.0)
    _tick(app, bridge, 0)
    assert (6, {"cutoff": 1}) in juno.writes and (2, {"cutoff": 1}) in juno.writes
    # Linked lanes ignore their own part edits and clip launches
    bridge.seqSetLaneLink(1, 1)
    bridge.seqSetLanePart(1, 9)
    assert bridge.seqAutomationLanes[1]["targetPart"] == 4
    bridge.seqLaunchLaneClip(1, 3)
    assert bridge.sequencer.song.automation[1].queued_clip_idx == -1


@pytest.mark.ui
def test_knob_on_the_edited_part_is_locked_only_when_a_lane_drives_that_part(perf):
    app, bridge, juno = perf
    bridge._ctl_open[PORT] = object()
    bridge._ctl_bindings = [Binding(port=PORT, channel=0, kind="cc", number=13,
                                    target="common.cutoff_offset", takeover="jump")]
    bridge.seqSetLaneTarget(0, "common.cutoff_offset")   # track 1 -> part 1 = the edited part
    bridge.seqSetLaneStep(0, 0, 0.5)
    _tick(app, bridge, 0)
    bridge._ctl_handle((PORT, 0, "cc", 13, 127))
    assert "(automated)" in bridge.controlActivity
    bridge.seqSetTrackTargetPart(0, 7)                   # now the lane drives part 7
    _tick(app, bridge, 1)
    bridge._ctl_handle((PORT, 0, "cc", 13, 127))
    assert bridge.patch_state.common.cutoff_offset == 127
    bridge._ctl_open.clear()


@pytest.mark.ui
def test_motion_page_helpers(ui):
    app, bridge = ui
    assert bridge.seqMotionMode is False
    bridge.seqSetMotionMode(True)
    bridge.seqSelectLane(3)
    assert bridge.seqMotionMode and bridge.seqActiveLane == 3
    assert bridge.seqLaneValueText(3, 0.5) == "--"              # no target yet
    bridge.seqSetLaneTarget(3, "tone.2.tva_pan")
    assert bridge.seqAutomationLanes[3]["tabName"] == "T2 Pan"
    assert bridge.seqLaneValueText(3, 0.0) == "L64"
    bridge.seqSetLaneTarget(3, "macro.2")
    assert bridge.seqLaneValueText(3, 1.0) == "+100%"
    assert bridge.seqLaneSteps(3)[0]["start"] == -1.0            # empty clip: no curve
    bridge.seqLaneShape(3, "RAMP UP")
    steps = bridge.seqLaneSteps(3)
    assert steps[0]["value"] == 0.0 and steps[-1]["value"] == 1.0
    assert all(s["glide"] for s in steps)
    bridge.seqLaneShape(3, "RANDOM")
    assert not any(s["glide"] for s in bridge.seqLaneSteps(3))
    bridge.seqLaneShape(3, "SQUARE")
    values = [s["value"] for s in bridge.seqLaneSteps(3)]
    assert values == [1.0] * 8 + [0.0] * 8
    # A newly set step glides by default; repainting keeps its glide setting
    bridge.seqSetLaneStep(5, 2, 0.3)
    assert bridge.seqLaneSteps(5)[2]["glide"] is True
    bridge.seqSetLaneStepGlide(5, 2, False)
    bridge.seqSetLaneStep(5, 2, 0.6)
    assert bridge.seqLaneSteps(5)[2]["glide"] is False
    targets = bridge.getLaneTargets("ALL", "")
    keys = [t["key"] for t in targets]
    assert keys[0] == "macro.1" and "tone.1.tvf_cutoff" in keys
    assert all(t["category"] == "MACRO" for t in bridge.getLaneTargets("MACRO", ""))


# -- recording ------------------------------------------------------------------------

def _rolling(bridge):
    """The transport counts as running; ticks are driven by hand."""
    bridge.sequencer.play()
    bridge.sequencer.clock.stop()
    bridge.sequencer.clock._running = True


def _knob(bridge, t):
    bridge._ctl_open[PORT] = object()
    bridge._ctl_bindings = [Binding(port=PORT, channel=0, kind="cc", number=13,
                                    target=CUTOFF, takeover="jump")]
    bridge._ctl_handle((PORT, 0, "cc", 13, round(t * 127)))


@pytest.mark.ui
def test_armed_lane_records_one_loop_from_the_first_move(ui):
    app, bridge = ui
    clip = bridge.sequencer.song.automation[0].clips[0]
    bridge.seqSetLaneTarget(0, CUTOFF)
    bridge.seqSetLaneStep(0, 0, 0.25)                # plays a flat 0.25
    _rolling(bridge)
    _tick(app, bridge, 0, 100)                       # step 4
    bridge.seqToggleLaneRec(0)
    assert bridge.seqLaneRecStates[0] == "armed"
    bridge._auto_rec_poll()                          # untouched: nothing happens
    assert bridge.seqLaneRecStates[0] == "armed"
    _knob(bridge, 100 / 127)                         # an armed lane lets the knob through
    assert bridge.patch_state.tones[0].tvf_cutoff == 100
    bridge._auto_rec_poll()
    assert bridge.seqLaneRecStates[0] == "recording"
    start = bridge.sequencer.lane_steps[0]
    assert clip.steps[start].value == pytest.approx(100 / 127, abs=0.01) and clip.steps[start].glide
    # The lane doesn't fight the hand while recording
    _tick(app, bridge, 100, 130)
    assert bridge.patch_state.tones[0].tvf_cutoff == 100
    # Each step reached gets the value at its start; skipped polls fill the gap
    _knob(bridge, 20 / 127)
    _tick(app, bridge, 130, 200)
    bridge._auto_rec_poll()
    reached = bridge.sequencer.lane_steps[0]
    assert all(clip.steps[s].value == pytest.approx(20 / 127, abs=0.01)
               for s in range(start + 1, reached + 1))
    # Around the loop and back to the first step: done, disarmed, playing the take
    _tick(app, bridge, 200, 100 + 384 + 5)
    bridge._auto_rec_poll()
    assert bridge.seqLaneRecStates[0] == ""
    assert clip.steps[start].value == pytest.approx(100 / 127, abs=0.01)   # not overwritten
    assert clip.steps[0].value == pytest.approx(20 / 127, abs=0.01)
    bridge._ctl_open.clear()


@pytest.mark.ui
def test_recording_ends_on_stop_and_needs_a_target(ui):
    app, bridge = ui
    bridge.seqToggleLaneRec(2)                       # no parameter: can't arm
    assert bridge.seqLaneRecStates[2] == ""
    bridge.seqSetLaneTarget(0, CUTOFF)
    _rolling(bridge)
    _tick(app, bridge, 0)
    bridge.seqToggleLaneRec(0)
    bridge._auto_rec_poll()                          # empty clip: learns the resting value
    bridge.setMasterCutoff(30)                       # a screen edit (filter page, tone 1)
    bridge._auto_rec_poll()
    assert bridge.seqLaneRecStates[0] == "recording"
    step = bridge.sequencer.lane_steps[0]
    assert bridge.sequencer.song.automation[0].clips[0].steps[step].value == pytest.approx(30 / 127, abs=0.01)
    _stop(app, bridge)
    bridge._auto_rec_poll()
    assert bridge.seqLaneRecStates[0] == ""          # stop ends it, keeping what was written
    assert bridge.sequencer.song.automation[0].clips[0].has_values


@pytest.mark.ui
def test_lane_step_recording_writes_the_cursor_step(ui):
    app, bridge = ui
    clip = bridge.sequencer.song.automation[0].clips[0]
    bridge.seqSetLaneTarget(0, CUTOFF)
    bridge.seqSetLaneStepRec(True, 14)
    assert bridge.seqLaneStepRec and bridge.seqLaneCursor == 14
    bridge._auto_rec_poll()                          # learns the resting value
    bridge.setMasterCutoff(40)
    bridge._auto_rec_poll()
    bridge.setMasterCutoff(90)                        # the latest value stays
    bridge._auto_rec_poll()
    assert clip.steps[14].value == pytest.approx(90 / 127, abs=0.01)
    bridge.seqMoveLaneCursor(1)
    bridge.seqMoveLaneCursor(1)                       # wraps around the clip
    assert bridge.seqLaneCursor == 0
    bridge.setMasterCutoff(10)
    bridge._auto_rec_poll()
    assert clip.steps[0].value == pytest.approx(10 / 127, abs=0.01)
    assert clip.steps[15].value is None               # stepped over: untouched
    # While stepping the lane doesn't play, and knobs on it work
    _rolling(bridge)
    _tick(app, bridge, 0)
    assert bridge.patch_state.tones[0].tvf_cutoff == 10
    _knob(bridge, 70 / 127)
    assert bridge.patch_state.tones[0].tvf_cutoff == 70
    bridge.seqSetLaneStepRec(False, 0)                # off: the lane plays again
    app.processEvents()
    assert bridge.patch_state.tones[0].tvf_cutoff == 10
    bridge._ctl_open.clear()


@pytest.mark.ui
def test_header_rec_arms_what_is_selected(ui):
    app, bridge = ui
    bridge.seqSetLaneTarget(2, CUTOFF)
    bridge.seqToggleRecord()                          # NOTES mode: overdub on the active track
    assert bridge.seqLiveRecordEnabled and bridge.seqRecText == "T1"
    bridge.seqSetMotionMode(True)
    bridge.seqSelectLane(2)
    bridge.seqToggleRecord()                          # MOTION mode: the active lane
    assert bridge.seqLaneRecStates[2] == "armed"
    assert bridge.seqRecArmed and bridge.seqRecText in ("T1 L3", "WAIT L3")
    bridge.seqSetMotionMode(False)
    bridge.seqToggleRecord()
    assert not bridge.seqLiveRecordEnabled and bridge.seqRecText == "L3"
    assert bridge.seqRecArmed                         # a lane is still armed
