"""Unit tests for VectorEngine, rate-limiting, and subscriber events."""

from unittest.mock import MagicMock

from src.spectre.vector.engine import MorphMode, VectorEngine
from src.spectre.vector.math import CrossfadeCurve


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
    mock_juno = MagicMock()
    # High rate limit for testing
    engine = VectorEngine(juno_client=mock_juno, max_update_hz=10.0)

    # First dispatch works via set_coordinates
    engine.set_coordinates(0.0, 0.0)
    assert mock_juno.set_tone_levels.call_count == 1

    # Rapid calls without flush should be throttled if within same tick
    engine.set_coordinates(0.1, 0.1)
    engine.set_coordinates(0.2, 0.2)
    # Shouldn't trigger immediate additional calls because of 10Hz limit
    assert mock_juno.set_tone_levels.call_count == 1

    # Flush forces transmission
    engine.flush()
    assert mock_juno.set_tone_levels.call_count >= 2


def test_vector_engine_wavetable_mode():
    engine = VectorEngine()
    engine.set_mode(MorphMode.WAVETABLE_1D)
    engine.set_wavetable_pos(0.0)
    assert engine.tone_levels == (127, 0, 0, 0)

    engine.set_wavetable_pos(1.0)
    assert engine.tone_levels == (0, 0, 0, 127)


def test_vector_engine_tone_mutes():
    engine = VectorEngine()
    engine.set_coordinates(0.0, 1.0)  # Corner NW: Tone 1 = 127, others 0
    assert engine.tone_levels == (127, 0, 0, 0)

    # Mute tone 1
    engine.set_tone_mute(1, True)
    assert engine.tone_levels == (0, 0, 0, 0)

    engine.set_tone_mute(1, False)
    assert engine.tone_levels == (127, 0, 0, 0)


def test_vector_engine_hold_suppresses_hardware_dispatch():
    from src.spectre.vector.motion import AutomatorType, RecorderState

    mock_juno = MagicMock()
    engine = VectorEngine(juno_client=mock_juno, max_update_hz=1000.0)
    engine.motion.automator = AutomatorType.CIRCLE
    engine.motion.play()
    assert engine.motion.state is RecorderState.PLAYING

    with engine.hold_hardware_writes():
        engine.update(0.016)
        engine.set_coordinates(0.0, 0.0)
        engine.flush()
        assert mock_juno.set_tone_levels.call_count == 0
        assert engine.motion.state is RecorderState.PLAYING

    engine.flush()
    assert mock_juno.set_tone_levels.call_count >= 1


def test_vector_dispatch_goes_through_the_writer_queue():
    from src.spectre.core.midi import MidiDeviceManager
    from src.spectre.core.protocol import JunoClient

    midi = MagicMock(spec=MidiDeviceManager)
    juno = JunoClient(midi)
    juno.get_active_patch_base = lambda timeout=1.0: (0x1F, 0x00, 0x00, 0x00)
    engine = VectorEngine(juno_client=juno, max_update_hz=1000.0)
    engine.set_coordinates(0.0, 1.0)
    assert juno.flush_writes(timeout=2.0)
    sent = [c.args[0] for c in midi.send_juno_sysex.call_args_list if c.args[0][5] == 0x12]
    assert len(sent) == 4
    assert [pkt[-2] for pkt in sent] == [127, 0, 0, 0]


def test_vector_move_inside_the_rate_window_is_sent_after_it():
    import time

    mock_juno = MagicMock()
    engine = VectorEngine(juno_client=mock_juno, max_update_hz=20.0)
    engine.set_coordinates(0.0, 0.0)
    engine.set_coordinates(0.0, 1.0)  # inside the 50 ms window
    assert mock_juno.set_tone_levels.call_count == 1
    time.sleep(0.15)
    assert mock_juno.set_tone_levels.call_count == 2
    assert mock_juno.set_tone_levels.call_args.args[0] == (127, 0, 0, 0)
