"""Unit tests for VectorEngine, rate-limiting, and subscriber events."""

from unittest.mock import MagicMock

from spectre.vector.engine import MorphMode, VectorEngine
from spectre.vector.math import CrossfadeCurve


def test_vector_engine_initial_state():
    engine = VectorEngine()
    state = engine.get_state()
    assert state.mode == MorphMode.VECTOR_2D
    assert state.x == 0.5
    assert state.y == 0.5
    assert state.tone_levels == (85, 85, 85, 85)

    # Linear curve produces 32
    lin_engine = VectorEngine(curve=CrossfadeCurve.LINEAR)
    assert lin_engine.get_state().tone_levels == (32, 32, 32, 32)


def test_vector_engine_coordinates_and_subscribers():
    engine = VectorEngine()
    events = []
    engine.subscribe(lambda s: events.append(s))

    # Move to Corner NW (Tone 1)
    engine.set_coordinates(0.0, 1.0)
    engine.flush()

    assert len(events) >= 1
    last_event = events[-1]
    assert last_event.x == 0.0
    assert last_event.y == 1.0
    assert last_event.tone_levels == (127, 0, 0, 0)


def test_vector_engine_rate_limiting_with_mock_client():
    mock_send = MagicMock()
    # High rate limit for testing
    engine = VectorEngine(send=mock_send, max_update_hz=10.0)

    # First dispatch works via set_coordinates
    engine.set_coordinates(0.0, 0.0)
    assert mock_send.call_count == 1

    # Rapid calls without flush should be throttled if within same tick
    engine.set_coordinates(0.1, 0.1)
    engine.set_coordinates(0.2, 0.2)
    # Shouldn't trigger immediate additional calls because of 10Hz limit
    assert mock_send.call_count == 1

    # Flush forces transmission
    engine.flush()
    assert mock_send.call_count >= 2


def test_vector_engine_wavetable_mode():
    engine = VectorEngine()
    engine.set_mode(MorphMode.WAVETABLE_1D)
    engine.set_wavetable_pos(0.01)
    engine.set_wavetable_pos(0.0)
    assert engine.tone_levels == (127, 0, 0, 0)

    engine.set_wavetable_pos(1.0)
    assert engine.tone_levels == (0, 0, 0, 127)


def test_vector_move_inside_the_rate_window_is_sent_after_it():
    import time

    mock_send = MagicMock()
    engine = VectorEngine(send=mock_send, max_update_hz=20.0)
    engine.set_coordinates(0.0, 0.0)
    engine.set_coordinates(0.0, 1.0)  # inside the 50 ms window
    assert mock_send.call_count == 1
    time.sleep(0.15)
    assert mock_send.call_count == 2
    assert mock_send.call_args.args[0] == (127, 0, 0, 0)


def test_a_read_sends_queued_writes_first():
    from spectre.core.midi import MidiDeviceManager
    from spectre.core.protocol import JunoClient

    midi = MagicMock(spec=MidiDeviceManager)
    midi.iter_juno_messages.return_value = iter(())
    juno = JunoClient(midi)
    juno._ensure_writer = lambda: None  # keep the writes queued until the read
    with juno.coalesced_writes():
        juno.send_data((0x1F, 0x00, 0x20, 0x00), [10])
        juno.send_data((0x1F, 0x00, 0x22, 0x00), [20])
    juno.request_data((0x1F, 0x00, 0x00, 0x00), (0, 0, 0, 1), timeout=0.01)
    cmds = [c.args[0][5] for c in midi.send_juno_sysex.call_args_list]
    assert cmds == [0x12, 0x12, 0x11]  # both DT1s, then the RQ1


def test_mode_and_curve_send_nothing_until_the_next_move():
    send = MagicMock()
    engine = VectorEngine(send=send, max_update_hz=1000.0)
    engine.set_mode(MorphMode.WAVETABLE_1D)
    engine.set_curve(CrossfadeCurve.LINEAR)
    engine.set_mode(MorphMode.VECTOR_2D)
    assert send.call_count == 0
    engine.set_coordinates(0.0, 1.0)
    assert send.call_args.args[0] == (127, 0, 0, 0)


def test_needs_tick_only_while_something_moves():
    from spectre.vector.motion import AutomatorType, WavetableSweepMode

    engine = VectorEngine()
    assert not engine.needs_tick
    engine.motion.automator = AutomatorType.CIRCLE
    engine.motion.play()
    assert engine.needs_tick
    engine.motion.stop()
    engine.motion.wavetable_sweep = WavetableSweepMode.SINE
    assert not engine.needs_tick  # the sweep runs on the WAVETABLE page only
    engine.set_mode(MorphMode.WAVETABLE_1D)
    assert engine.needs_tick


# --- the bridge: the patch owns tone levels and mutes; the pad only moves them ---

def _bridge(levels=(127, 100, 60, 30)):
    from spectre.core.patch_state import PatchState
    from spectre.ui.bridge import SpectreBridge

    bridge = SpectreBridge()
    state = PatchState()
    for t, level in zip(state.tones, levels):
        t.level = level
    bridge.patch_state = state
    bridge.juno = MagicMock()
    return bridge


def _levels(bridge):
    return [t.level for t in bridge.patch_state.tones]


def test_tone_mute_round_trip_keeps_every_level():
    """Shift+Tone off and on: only that tone is written, the others keep their levels."""
    bridge = _bridge()
    juno = bridge.juno
    bridge.toggleToneMute(2)
    assert _levels(bridge) == [127, 100, 60, 30]
    assert juno.set_tone_level.call_args_list == [((2, 0),)]
    bridge.toggleToneMute(2)
    assert _levels(bridge) == [127, 100, 60, 30]
    assert juno.set_tone_level.call_args.args == (2, 100)
    assert juno.set_tone_levels.call_count == 0


def test_level_edit_while_muted_comes_back_on_unmute():
    bridge = _bridge()
    bridge.toggleToneMute(2)
    bridge.setToneLevel(2, 50)
    assert bridge.juno.set_tone_level.call_args.args == (2, 0)  # still silent
    bridge.toggleToneMute(2)
    assert bridge.juno.set_tone_level.call_args.args == (2, 50)


def test_opening_the_vector_pages_sends_nothing():
    bridge = _bridge()
    bridge.setActiveView("WAVETABLE")
    bridge.setActiveView("VECTOR")
    assert _levels(bridge) == [127, 100, 60, 30]
    assert bridge.juno.set_tone_level.call_count == 0


def test_patch_init_keeps_the_pad_out_of_the_new_levels():
    bridge = _bridge()
    bridge.setCoordinates(0.1, 0.9)
    bridge.juno = None
    bridge.initPatch()
    template = [t.level for t in bridge.patch_state.__class__.from_template_file().tones]
    assert _levels(bridge) == template


def test_pad_move_sets_the_patch_levels_and_skips_muted_tones():
    bridge = _bridge()
    bridge.vector.max_update_hz = 1000.0
    juno = bridge.juno
    bridge.toggleToneMute(2)
    juno.reset_mock()
    bridge.setCoordinates(0.0, 1.0)  # tone 1 corner
    assert _levels(bridge) == [127, 0, 0, 0]
    assert [c.args for c in juno.set_tone_level.call_args_list] == [(1, 127), (3, 0), (4, 0)]


def test_pad_levels_go_through_the_writer_queue():
    from spectre.core.midi import MidiDeviceManager
    from spectre.core.protocol import JunoClient

    bridge = _bridge()
    bridge.vector.max_update_hz = 1000.0
    midi = MagicMock(spec=MidiDeviceManager)
    juno = JunoClient(midi)
    juno.get_active_patch_base = lambda timeout=1.0: (0x1F, 0x00, 0x00, 0x00)
    bridge.juno = juno
    bridge.setCoordinates(0.0, 1.0)
    assert juno.flush_writes(timeout=2.0)
    sent = [c.args[0] for c in midi.send_juno_sysex.call_args_list if c.args[0][5] == 0x12]
    assert [pkt[-2] for pkt in sent] == [127, 0, 0, 0]


def test_motion_timer_runs_only_while_motion_plays():
    bridge = _bridge()
    assert not bridge._timer.isActive()
    bridge.setAutomator("circle")
    assert bridge._timer.isActive()
    bridge.stopMotion()
    assert not bridge._timer.isActive()
