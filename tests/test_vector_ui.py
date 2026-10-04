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


def test_modmatrix_picker():
    """Verify ModMatrixView sources, destinations, and modal picker overlay state."""
    from PyQt6.QtCore import QObject

    engine = VectorEngine()
    app, qml_engine, bridge = create_application(engine=engine, platform="offscreen")
    root = qml_engine.rootObjects()[0]

    matrix_view = root.findChild(QObject, "modMatrixView")
    assert matrix_view is not None

    sources = matrix_view.property("sources").toVariant()
    assert len(sources) == 11
    assert "CC01 MOD WHEEL" in sources
    assert "STEP LFO" in sources

    destinations = matrix_view.property("destinations").toVariant()
    assert len(destinations) == 11
    assert "OFF" in destinations
    assert "TVF CUTOFF" in destinations

    assert matrix_view.property("pickerVisible") is False

    # Test openPicker invocation
    matrix_view.setProperty("pickerVisible", True)
    assert matrix_view.property("pickerVisible") is True
    matrix_view.setProperty("pickerVisible", False)
    assert matrix_view.property("pickerVisible") is False


def test_pitchenv_draggable_mseg():
    """Verify PitchEnvView properties and MSEG getPoints calculation."""
    from PyQt6.QtCore import QObject

    engine = VectorEngine()
    app, qml_engine, bridge = create_application(engine=engine, platform="offscreen")
    root = qml_engine.rootObjects()[0]

    pitch_view = root.findChild(QObject, "pitchEnvView")
    assert pitch_view is not None

    assert pitch_view.property("t1") == 20
    assert pitch_view.property("l1") == 24
    assert pitch_view.property("draggedPoint") == -1

    # Verify Roland Dynamics & Velocity Sensitivity properties
    assert pitch_view.property("envDepth") == 12
    assert pitch_view.property("velSens") == 30
    assert pitch_view.property("t1VelSens") == 0
    assert pitch_view.property("t4VelSens") == 0
    assert pitch_view.property("timeKeyfollow") == 0

    # Test updating segment values
    pitch_view.setProperty("t1", 55)
    pitch_view.setProperty("l1", -15)
    assert pitch_view.property("t1") == 55
    assert pitch_view.property("l1") == -15

    # Test updating dynamics & velocity properties
    pitch_view.setProperty("envDepth", -6)
    pitch_view.setProperty("velSens", 45)
    pitch_view.setProperty("t1VelSens", 20)
    pitch_view.setProperty("t4VelSens", -15)
    pitch_view.setProperty("timeKeyfollow", 50)

    assert pitch_view.property("envDepth") == -6
    assert pitch_view.property("velSens") == 45
    assert pitch_view.property("t1VelSens") == 20
    assert pitch_view.property("t4VelSens") == -15
    assert pitch_view.property("timeKeyfollow") == 50

    # Test draggedPoint active state
    pitch_view.setProperty("draggedPoint", 1)
    assert pitch_view.property("draggedPoint") == 1
    pitch_view.setProperty("draggedPoint", -1)
    assert pitch_view.property("draggedPoint") == -1


def test_mfx_view_features():
    """Verify MfxView category filtering, search, 4-8 param grid, and bypass state."""
    from PyQt6.QtCore import QObject

    engine = VectorEngine()
    app, qml_engine, bridge = create_application(engine=engine, platform="offscreen")
    root = qml_engine.rootObjects()[0]

    mfx_view = root.findChild(QObject, "mfxView")
    assert mfx_view is not None

    # Check default active algorithm (15 Tape Echo)
    assert mfx_view.property("activeAlgoId") == 15
    assert mfx_view.property("isBypassed") is False
    assert mfx_view.property("selectedCategory") == "ALL"

    curr_algo = mfx_view.property("currentAlgo").toVariant()
    assert curr_algo["id"] == 15
    assert "TAPE ECHO" in curr_algo["name"]
    assert curr_algo["cat"] == "DELAY"
    assert len(curr_algo["params"]) == 8

    # Test category filtering
    mfx_view.setProperty("selectedCategory", "FILTER/EQ")
    filtered = mfx_view.property("filteredAlgos").toVariant()
    assert len(filtered) == 1
    assert filtered[0]["id"] == 1

    mfx_view.setProperty("selectedCategory", "CHORUS")
    filtered = mfx_view.property("filteredAlgos").toVariant()
    assert len(filtered) == 2
    assert all(item["cat"] == "CHORUS" for item in filtered)

    # Test search filtering
    mfx_view.setProperty("selectedCategory", "ALL")
    mfx_view.setProperty("searchQuery", "phaser")
    filtered = mfx_view.property("filteredAlgos").toVariant()
    assert len(filtered) == 2  # 11 Phaser and 45 Step Phaser
    assert any(item["id"] == 11 for item in filtered)
    assert any(item["id"] == 45 for item in filtered)

    # Search by ID
    mfx_view.setProperty("searchQuery", "68")
    filtered = mfx_view.property("filteredAlgos").toVariant()
    assert len(filtered) == 1
    assert filtered[0]["id"] == 68
    assert "SLICER" in filtered[0]["name"]

    # Test selecting an algorithm
    mfx_view.setProperty("activeAlgoId", 68)
    curr_algo = mfx_view.property("currentAlgo").toVariant()
    assert curr_algo["id"] == 68
    assert "SLICER" in curr_algo["name"]
    assert len(curr_algo["params"]) == 6

    # Test bypass toggle
    mfx_view.setProperty("isBypassed", True)
    assert mfx_view.property("isBypassed") is True
    mfx_view.setProperty("isBypassed", False)
    assert mfx_view.property("isBypassed") is False

    # Test Virtual Keyboard integration
    assert mfx_view.property("virtualKeyboardVisible") is False
    vk = mfx_view.findChild(QObject, "mfxVirtualKeyboard")
    assert vk is not None

    mfx_view.setProperty("virtualKeyboardVisible", True)
    assert mfx_view.property("virtualKeyboardVisible") is True
    mfx_view.setProperty("virtualKeyboardVisible", False)
    assert mfx_view.property("virtualKeyboardVisible") is False


def test_master_fx_view_controls():
    """Verify MasterFxView scaled sliders, chorus/reverb controls, and parametric EQ."""
    from PyQt6.QtCore import QObject

    engine = VectorEngine()
    app, qml_engine, bridge = create_application(engine=engine, platform="offscreen")
    root = qml_engine.rootObjects()[0]

    master_fx_view = root.findChild(QObject, "masterFxView")
    assert master_fx_view is not None

    # Check chorus properties
    assert master_fx_view.property("chorusType") == 1
    assert master_fx_view.property("chorusRate") == 40
    assert master_fx_view.property("chorusDepth") == 65
    assert master_fx_view.property("chorusPreDelay") == 12
    assert master_fx_view.property("chorusFeedback") == 20
    assert master_fx_view.property("chorusToReverb") == 0
    assert master_fx_view.property("chorusLevel") == 80

    # Check reverb properties
    assert master_fx_view.property("reverbType") == 4
    assert master_fx_view.property("reverbTime") == 70
    assert master_fx_view.property("reverbDamp") == 45
    assert master_fx_view.property("reverbPreDelay") == 15
    assert master_fx_view.property("reverbDiffusion") == 60
    assert master_fx_view.property("reverbTone") == 64
    assert master_fx_view.property("reverbLevel") == 60

    # Check EQ properties
    assert master_fx_view.property("eqLowGain") == 2
    assert master_fx_view.property("eqLowFreq") == 400
    assert master_fx_view.property("eqMidGain") == -3
    assert master_fx_view.property("eqMidFreq") == 1200
    assert master_fx_view.property("eqMidQ") == 1.0
    assert master_fx_view.property("eqHighGain") == 4
    assert master_fx_view.property("eqHighFreq") == 4000
    assert master_fx_view.property("eqMasterLevel") == 100

    # Test modifying chorus parameters
    master_fx_view.setProperty("chorusRate", 85)
    master_fx_view.setProperty("chorusToReverb", 40)
    assert master_fx_view.property("chorusRate") == 85
    assert master_fx_view.property("chorusToReverb") == 40

    # Test modifying reverb parameters
    master_fx_view.setProperty("reverbTime", 95)
    master_fx_view.setProperty("reverbDiffusion", 80)
    assert master_fx_view.property("reverbTime") == 95
    assert master_fx_view.property("reverbDiffusion") == 80

    # Test modifying EQ parameters
    master_fx_view.setProperty("eqLowGain", 6)
    master_fx_view.setProperty("eqMidGain", 0)
    master_fx_view.setProperty("eqMidQ", 2.0)
    master_fx_view.setProperty("eqHighGain", -5)
    assert master_fx_view.property("eqLowGain") == 6
    assert master_fx_view.property("eqMidGain") == 0
    assert master_fx_view.property("eqMidQ") == 2.0
    assert master_fx_view.property("eqHighGain") == -5

    # Test drag interaction state
    assert master_fx_view.property("draggedEqBand") == -1
    master_fx_view.setProperty("draggedEqBand", 1)
    assert master_fx_view.property("draggedEqBand") == 1
    master_fx_view.setProperty("draggedEqBand", -1)
    assert master_fx_view.property("draggedEqBand") == -1


def test_init_patch_workflow():
    """Verify Patch Init modal, Bridge.initPatch state reset, and QML view synchronization."""
    from PyQt6.QtCore import QObject

    engine = VectorEngine()
    app, qml_engine, bridge = create_application(engine=engine, platform="offscreen")
    root = qml_engine.rootObjects()[0]

    # Check modal exists
    init_modal = root.findChild(QObject, "initPatchModal")
    assert init_modal is not None
    assert init_modal.property("visible") is False

    # Check opening modal via bridge slot
    modal_opened = False
    def on_modal_req():
        nonlocal modal_opened
        modal_opened = True
    bridge.requestOpenInitPatchModal.connect(on_modal_req)

    bridge.openInitPatchModal()
    assert modal_opened is True

    # Test modal open/close methods
    init_modal.setProperty("visible", True)
    assert init_modal.property("visible") is True
    init_modal.setProperty("visible", False)
    assert init_modal.property("visible") is False

    # Mutate parameters to non-default values first
    bridge.setPatchName("Custom Lead", "PATCH")
    bridge.setMasterCutoff(45)
    bridge.setMasterReso(80)
    bridge.setTvfEnvDepth(35)
    bridge.setTvaSustain(40)
    bridge.setPortamentoSwitch(True)
    bridge.setToneWave(1, "INTA", 100)

    mfx_view = root.findChild(QObject, "mfxView")
    mfx_view.setProperty("isBypassed", False)

    master_fx_view = root.findChild(QObject, "masterFxView")
    master_fx_view.setProperty("chorusLevel", 90)
    master_fx_view.setProperty("reverbLevel", 75)
    master_fx_view.setProperty("eqLowGain", 8)

    pitch_view = root.findChild(QObject, "pitchEnvView")
    pitch_view.setProperty("envDepth", 12)

    # Execute initPatch
    patch_init_signal_received = False
    def on_patch_init():
        nonlocal patch_init_signal_received
        patch_init_signal_received = True
    bridge.patchInitialized.connect(on_patch_init)

    bridge.initPatch()
    assert patch_init_signal_received is True

    # Verify bridge state has reset to clean template
    assert bridge.patchName == "JUNO SPECTRE"
    assert bridge.masterCutoff == 127
    assert bridge.masterReso == 0
    assert bridge.tvfEnvDepth == 0
    assert bridge.tvfAttack == 0
    assert bridge.tvfDecay == 0
    assert bridge.tvfSustain == 127
    assert bridge.tvfRelease == 0
    assert bridge.tvaSustain == 127
    assert bridge.masterAttack == 0
    assert bridge.portamentoSwitch is False
    assert bridge.lfo1PitchDepth == 0
    assert bridge.lfo2TvfDepth == 0

    # Verify tone waves set to JUNO SPECTRE 4-osc defaults
    waves = bridge.toneWaveData
    assert len(waves) == 4
    assert waves[0]["id"] == 579
    assert waves[1]["id"] == 600
    assert waves[2]["id"] == 622
    assert waves[3]["id"] == 625

    # Verify QML views reacted via onPatchInitialized
    assert mfx_view.property("isBypassed") is True
    assert master_fx_view.property("chorusLevel") == 0
    assert master_fx_view.property("reverbLevel") == 0
    assert master_fx_view.property("eqLowGain") == 0
    assert pitch_view.property("envDepth") == 0









