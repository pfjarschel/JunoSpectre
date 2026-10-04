"""Unit tests for Qt Quick / QML Touch UI application offscreen."""

import pytest

from src.spectre.ui.app import create_application
from src.spectre.vector.engine import MorphMode, VectorEngine


def test_ui_application_creation():
    engine = VectorEngine()
    app, qml_engine, bridge = create_application(engine=engine, platform="offscreen")

    assert len(qml_engine.rootObjects()) == 1
    root = qml_engine.rootObjects()[0]

    assert root.property("title") == "Juno Spectre - Touch Workstation"
    assert root.property("width") == 1024
    assert root.property("height") == 600


def test_ui_bridge_slots_and_properties():
    engine = VectorEngine()
    app, qml_engine, bridge = create_application(engine=engine, platform="offscreen")

    # Test coordinate update via slot
    bridge.setCoordinates(0.25, 0.75)
    assert pytest.approx(bridge.vectorX, 0.01) == 0.25
    assert pytest.approx(bridge.vectorY, 0.01) == 0.75

    # Test wavetable pos update
    bridge.setWavetablePos(0.66)
    assert pytest.approx(bridge.wavetablePos, 0.01) == 0.66

    # Test mode toggle
    bridge.setMorphMode("wavetable_1d")
    assert bridge.morphMode == "wavetable_1d"
    bridge.setMorphMode("vector_2d")
    assert bridge.morphMode == "vector_2d"

    # Test transport slots
    bridge.startRecording()
    assert bridge.recorderState == "recording"
    bridge.stopRecording()
    assert bridge.recorderState in ("playing", "stopped")

    bridge.setAutomator("circle")
    assert bridge.automator == "circle"

    bridge.setSpeed(2.0)
    assert pytest.approx(bridge.speed, 0.01) == 2.0

    # Test Workstation activeView
    bridge.setActiveView("MACROS")
    assert bridge.activeView == "MACROS"
    bridge.setActiveView("VECTOR")
    assert bridge.activeView == "VECTOR"
    assert bridge.morphMode == "vector_2d"

    # Test Tone Mute slots
    bridge.toggleToneMute(1)
    assert bridge.tone1Muted is True
    bridge.toggleToneMute(1)
    assert bridge.tone1Muted is False

    # Test Tone Direct Level Setting
    bridge.setToneLevel(1, 120)
    assert bridge.tone1Level == 120

    # Test Master Controls
    bridge.setMasterCutoff(80)
    assert bridge.masterCutoff == 80
    bridge.setMasterReso(50)
    assert bridge.masterReso == 50
    bridge.setMasterAttack(70)
    assert bridge.masterAttack == 70
    bridge.setMasterRelease(90)
    assert bridge.masterRelease == 90
    bridge.setMasterLevel(115)
    assert bridge.masterLevel == 115

    # Test Macros
    bridge.setMacro(1, 99)
    assert bridge.macro1 == 99


def test_workstation_views_switching():
    engine = VectorEngine()
    app, qml_engine, bridge = create_application(engine=engine, platform="offscreen")

    # Initial boot view must be JUNO PCM
    assert bridge.activeView == "JUNO PCM"

    all_16_views = [
        "JUNO PCM", "VECTOR", "WAVETABLE", "VA",
        "MOD MATRIX", "STEP LFO", "PITCH ENV", "MFX", "MASTER FX",
        "MACROS", "PERF MIXER", "SEQUENCER",
        "LIBRARIAN", "MIDI LEARN", "HARDWARE", "SYSTEM"
    ]
    for v in all_16_views:
        bridge.setActiveView(v)
        assert bridge.activeView == v
        if v == "VECTOR":
            assert bridge.morphMode == "vector_2d"
        elif v == "WAVETABLE":
            assert bridge.morphMode == "wavetable_1d"

    # Test legacy aliases normalize cleanly
    bridge.setActiveView("PATCH EDIT")
    assert bridge.activeView == "JUNO PCM"
    bridge.setActiveView("EFFECTS")
    assert bridge.activeView == "MFX"
    bridge.setActiveView("4-OSC VA")
    assert bridge.activeView == "VA"


def test_sound_sculptor_and_mod_properties():
    engine = VectorEngine()
    app, qml_engine, bridge = create_application(engine=engine, platform="offscreen")

    # TVF Envelope & Filter
    bridge.setTvfType("BPF")
    assert bridge.tvfType == "BPF"
    bridge.setTvfKeyFollow(50)
    assert bridge.tvfKeyFollow == 50
    bridge.setTvfVeloSens(64)
    assert bridge.tvfVeloSens == 64
    bridge.setTvfEnvDepth(35)
    assert bridge.tvfEnvDepth == 35
    bridge.setTvfAttack(50)
    assert bridge.tvfAttack == 50
    bridge.setTvfDecay(45)
    assert bridge.tvfDecay == 45
    bridge.setTvfSustain(80)
    assert bridge.tvfSustain == 80
    bridge.setTvfRelease(60)
    assert bridge.tvfRelease == 60

    # TVA Amplifier & Envelope
    bridge.setTvaPan(-25)
    assert bridge.tvaPan == -25
    bridge.setTvaVeloSens(40)
    assert bridge.tvaVeloSens == 40
    bridge.setTvaDecay(55)
    assert bridge.tvaDecay == 55
    bridge.setTvaSustain(75)
    assert bridge.tvaSustain == 75

    # Pitch & Portamento
    bridge.setPitchCoarse(-12)
    assert bridge.pitchCoarse == -12
    bridge.setPitchFine(15)
    assert bridge.pitchFine == 15
    bridge.setPortamentoTime(45)
    assert bridge.portamentoTime == 45
    bridge.setPortamentoSwitch(True)
    assert bridge.portamentoSwitch is True
    bridge.setLegatoSwitch(True)
    assert bridge.legatoSwitch is True

    # Linked Mode
    bridge.setLinkedMode(True)
    assert bridge.linkedMode is True

    # LFO Params
    bridge.setLfoParam(1, "wave", "SQR")
    assert bridge.lfo1Wave == "SQR"
    bridge.setLfoParam(1, "pan_depth", 30)
    assert bridge.lfo1PanDepth == 30
    bridge.setLfoParam(1, "delay_time", 20)
    assert bridge.lfo1DelayTime == 20
    bridge.setLfoParam(1, "fade_mode", "ON-OUT")
    assert bridge.lfo1FadeMode == "ON-OUT"
    bridge.setLfoParam(1, "fade_time", 40)
    assert bridge.lfo1FadeTime == 40
    bridge.setLfoParam(2, "rate", 99)
    assert bridge.lfo2Rate == 99

    # Brightness
    bridge.setBrightness(75)
    assert bridge.brightness == 75

    # Screens Overlay Signal
    signal_received = []
    bridge.requestOpenScreensOverlay.connect(lambda: signal_received.append(True))
    bridge.openScreensOverlay()
    assert len(signal_received) == 1


def test_ui_rendering_performance():
    """Verify coordinate and wavetable changes process rapidly without bridge bottlenecks."""
    import time
    engine = VectorEngine()
    app, qml_engine, bridge = create_application(engine=engine, platform="offscreen")

    t0 = time.perf_counter()
    for i in range(60):
        bridge.setCoordinates(i / 60.0, (60 - i) / 60.0)
        app.processEvents()
    elapsed_coords = time.perf_counter() - t0

    # 60 frames must complete in under 1.5s even under CPU software rasterization on Pi
    # (on desktop this takes ~0.02s; previously took 49+ seconds due to bridge querying in loops)
    assert elapsed_coords < 1.5

    bridge.setActiveView("WAVETABLE")
    app.processEvents()

    t1 = time.perf_counter()
    for i in range(60):
        bridge.setWavetablePos(i / 60.0)
        app.processEvents()
    elapsed_wt = time.perf_counter() - t1
    # 60 frames of 16-slice 3D waterfall software rendering on ARM CPU takes ~2.3s
    assert elapsed_wt < 3.5


def test_bridge_get_filtered_waves():
    """Verify getFilteredWaves filters accurately across categories, banks, and search."""
    engine = VectorEngine()
    app, qml_engine, bridge = create_application(engine=engine, platform="offscreen")

    # 1. Filter by category
    pianos = bridge.getFilteredWaves("piano", "ALL", "")
    assert len(pianos) > 0
    assert all(w["category"] == "piano" for w in pianos)

    # 2. Filter by bank
    intb_all = bridge.getFilteredWaves("ALL", "INTB", "")
    assert len(intb_all) == 184
    assert all(w["bank"] == "INTB" for w in intb_all)

    # 3. Filter by search string
    juno_saws = bridge.getFilteredWaves("ALL", "ALL", "Juno Saw")
    assert len(juno_saws) >= 1
    assert any("Juno Saw HD" in w["name"] for w in juno_saws)


def test_bridge_sync_patch_from_synth():
    """Verify syncPatchFromSynth updates patch name and tone waveforms from JunoClient."""
    from unittest.mock import MagicMock
    from src.spectre.core.protocol import JunoClient, SoundMode

    mock_client = MagicMock(spec=JunoClient)
    mock_client.get_patch_name.return_value = "Test Patch"
    mock_client.get_sound_mode.return_value = SoundMode.PATCH
    mock_client.get_all_tone_waves.return_value = [
        ("INTA", 579),
        ("INTA", 1),
        ("INTA", 242),
        ("INTA", 1816),
    ]

    engine = VectorEngine(juno_client=mock_client)
    app, qml_engine, bridge = create_application(engine=engine, platform="offscreen")

    bridge.syncPatchFromSynth()
    assert bridge.patchName == "Test Patch"
    assert bridge.soundMode == "PATCH"
    waves = bridge.toneWaveData
    assert len(waves) == 4
    assert waves[0]["name"] == "Juno Saw HD"
    assert waves[1]["name"] == "Ult.P*mp A L"  # INTA 1
    assert waves[2]["name"] == "Nasty Gtr"     # INTA 242
    assert waves[3]["name"] == "Open Triangl"  # INTA 1816


def test_wave_modal_and_virtual_keyboard():
    """Verify WaveBrowserModal and VirtualKeyboard integrate properly into QML tree."""
    from PyQt6.QtCore import QObject

    engine = VectorEngine()
    app, qml_engine, bridge = create_application(engine=engine, platform="offscreen")
    root = qml_engine.rootObjects()[0]

    modal = root.findChild(QObject, "waveBrowserModal")
    assert modal is not None
    assert modal.property("selectedBank") == "ALL"
    assert modal.property("visible") is False

    # Open modal for Tone 2
    modal.open(2)
    assert modal.property("visible") is True
    assert modal.property("targetTone") == 2
    assert modal.property("selectedBank") == "ALL"
    assert modal.property("virtualKeyboardVisible") is False

    # Virtual keyboard child check
    vk = modal.findChild(QObject, "virtualKeyboard")
    assert vk is not None

    # Toggle keyboard visible
    modal.setProperty("virtualKeyboardVisible", True)
    assert vk.property("visible") is True

    # Close modal
    modal.close()
    assert modal.property("visible") is False


def test_bridge_open_wave_browser():
    """Verify Bridge.openWaveBrowser emits signal and opens waveBrowserModal in QML."""
    from PyQt6.QtCore import QObject

    engine = VectorEngine()
    app, qml_engine, bridge = create_application(engine=engine, platform="offscreen")
    root = qml_engine.rootObjects()[0]

    modal = root.findChild(QObject, "waveBrowserModal")
    assert modal is not None
    assert modal.property("visible") is False

    # Trigger bridge slot for Tone 3
    bridge.openWaveBrowser(3)
    assert modal.property("visible") is True
    assert modal.property("targetTone") == 3

def test_vaview_pw_pwm():
    """Verify VaView properties and PWM/PW initial state."""
    from PyQt6.QtCore import QObject

    engine = VectorEngine()
    app, qml_engine, bridge = create_application(engine=engine, platform="offscreen")
    root = qml_engine.rootObjects()[0]

    va_view = root.findChild(QObject, "vaView")
    assert va_view is not None
    assert va_view.property("osc1Pw") == 50
    assert va_view.property("osc1Pwm") == 0
    assert va_view.property("osc2Pwm") == 0
    assert va_view.property("osc3Pwm") == 0
    assert va_view.property("osc4Pwm") == 0

    va_view.setProperty("osc1Pwm", 35)
    assert va_view.property("osc1Pwm") == 35
