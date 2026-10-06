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

    all_views = [
        "JUNO PCM", "VECTOR", "WAVETABLE", "VA",
        "MOD MATRIX", "STEP LFO", "MSEG ENVELOPES", "MFX", "ROUTING", "MASTER FX",
        "MACROS", "PERF MIXER", "SEQUENCER",
        "LIBRARIAN", "MIDI LEARN", "HARDWARE", "SYSTEM"
    ]
    for v in all_views:
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
    assert len(sources) == 19
    assert "CC01 MOD WHEEL" in sources
    assert "PITCH BEND" in sources

    destinations = matrix_view.property("destinations").toVariant()
    assert len(destinations) == 34
    assert "OFF" in destinations
    assert "TVF CUTOFF" in destinations
    assert "TMT" in destinations

    assert matrix_view.property("pickerVisible") is False

    # Test openPicker invocation
    matrix_view.setProperty("pickerVisible", True)
    assert matrix_view.property("pickerVisible") is True
    matrix_view.setProperty("pickerVisible", False)
    assert matrix_view.property("pickerVisible") is False


def test_modmatrix_tone_switches():
    """Verify Bridge matrix controller tone switch properties and slots."""
    engine = VectorEngine()
    app, qml_engine, bridge = create_application(engine=engine, platform="offscreen")

    ctrl1 = bridge.matrixCtrl1
    assert "dest1_sw" in ctrl1
    assert ctrl1["dest1_sw"] == [1, 1, 1, 1]
    assert "dest_sw" in ctrl1

    # Toggle Tone 1, Ctrl 1, Dest 1 to OFF
    bridge.setToneMatrixSwitch(1, 1, 1, False)
    ctrl1_updated = bridge.matrixCtrl1
    assert ctrl1_updated["dest1_sw"] == [0, 1, 1, 1]
    assert bridge.patch_state.tones[0].matrix_switches[0][0] == 0

    # Toggle it back to ON
    bridge.setToneMatrixSwitch(1, 1, 1, True)
    assert bridge.matrixCtrl1["dest1_sw"] == [1, 1, 1, 1]
    assert bridge.patch_state.tones[0].matrix_switches[0][0] == 1


def test_mseg_env_editor_view():
    """Verify the full-page MSEG Envelope Editor (EnvEditorView) properties."""
    from PyQt6.QtCore import QObject

    engine = VectorEngine()
    app, qml_engine, bridge = create_application(engine=engine, platform="offscreen")
    root = qml_engine.rootObjects()[0]

    env_view = root.findChild(QObject, "envEditorView")
    assert env_view is not None

    # Full page now edits all three hardware MSEG envelopes (TVF default tab)
    assert env_view.property("activeEnv") == "TVF"
    env_view.setProperty("activeEnv", "PITCH")
    assert env_view.property("activeEnv") == "PITCH"

    assert env_view.property("t1") == 20
    assert env_view.property("l1") == 24
    assert env_view.property("draggedPoint") == -1

    # Verify Roland Dynamics & Velocity Sensitivity properties
    assert env_view.property("envDepth") == 12
    assert env_view.property("velSens") == 30
    assert env_view.property("t1VelSens") == 0
    assert env_view.property("t4VelSens") == 0
    assert env_view.property("timeKeyfollow") == 0

    # Test updating segment values
    env_view.setProperty("t1", 55)
    env_view.setProperty("l1", -15)
    assert env_view.property("t1") == 55
    assert env_view.property("l1") == -15

    # Test updating dynamics & velocity properties
    env_view.setProperty("envDepth", -6)
    env_view.setProperty("velSens", 45)
    env_view.setProperty("t1VelSens", 20)
    env_view.setProperty("t4VelSens", -15)
    env_view.setProperty("timeKeyfollow", 50)

    assert env_view.property("envDepth") == -6
    assert env_view.property("velSens") == 45
    assert env_view.property("t1VelSens") == 20
    assert env_view.property("t4VelSens") == -15
    assert env_view.property("timeKeyfollow") == 50

    # Test draggedPoint active state
    env_view.setProperty("draggedPoint", 1)
    assert env_view.property("draggedPoint") == 1
    env_view.setProperty("draggedPoint", -1)
    assert env_view.property("draggedPoint") == -1


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

    def to_py(v):
        return v.toVariant() if hasattr(v, "toVariant") else v

    curr_algo = to_py(mfx_view.property("currentAlgo"))
    assert curr_algo["id"] == 15
    assert "RING MOD" in curr_algo["name"]
    assert curr_algo["cat"] == "MOD"

    # Test category filtering
    mfx_view.setProperty("selectedCategory", "FILTER/EQ")
    filtered = to_py(mfx_view.property("filteredAlgos"))
    assert len(filtered) == 10
    assert filtered[0]["id"] == 1

    mfx_view.setProperty("selectedCategory", "CHORUS")
    filtered = to_py(mfx_view.property("filteredAlgos"))
    assert len(filtered) == 12
    assert all(item["cat"] == "CHORUS" for item in filtered)

    # Test search filtering
    mfx_view.setProperty("selectedCategory", "ALL")
    mfx_view.setProperty("searchQuery", "phaser")
    filtered = to_py(mfx_view.property("filteredAlgos"))
    assert len(filtered) == 4  # 11, 12, 13, 14
    assert any(item["id"] == 11 for item in filtered)
    assert any(item["id"] == 12 for item in filtered)

    # Search by ID
    mfx_view.setProperty("searchQuery", "20")
    filtered = to_py(mfx_view.property("filteredAlgos"))
    assert any(item["id"] == 20 for item in filtered)

    # Test selecting an algorithm
    bridge.setMfxAlgoId(80)
    curr_algo = to_py(mfx_view.property("currentAlgo"))
    assert curr_algo["id"] == 80
    assert "BIT CRUSHER" in curr_algo["name"]
    assert len(curr_algo["params"]) == 4

    # Test setting an individual MFX parameter
    bridge.setMfxParam(0, 95)
    assert bridge.patch_state.effects.mfx_params[0] == 95

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

    env_view = root.findChild(QObject, "envEditorView")
    env_view.setProperty("envDepth", 12)

    # Execute initPatch
    patch_init_signal_received = False
    def on_patch_init():
        nonlocal patch_init_signal_received
        patch_init_signal_received = True
    bridge.patchInitialized.connect(on_patch_init)

    bridge.initPatch()
    assert patch_init_signal_received is True

    # Verify bridge state has reset to the golden template (decoded from init_template.json)
    assert bridge.patchName == "JUNO SPECTRE"
    assert bridge.masterCutoff == 127
    assert bridge.masterReso == 0
    assert bridge.tvfEnvDepth == 0
    assert bridge.tvfAttack == 0
    assert bridge.tvfDecay == 10        # captured keyboard-init TVF T2
    assert bridge.tvfSustain == 127
    assert bridge.tvfRelease == 64      # captured keyboard-init TVF T4
    assert bridge.tvaSustain == 127
    assert bridge.masterAttack == 0
    assert bridge.portamentoSwitch is False
    assert bridge.lfo1PitchDepth == 0
    assert bridge.lfo2TvfDepth == 0
    assert bridge.patch_state.effects.routing_preset == ""  # raw template patch, no preset
    assert bridge.macro7 == bridge.patch_state.effects.chorus_level
    assert bridge.macro8 == bridge.patch_state.effects.reverb_level

    # Verify tone waves set to JUNO SPECTRE 4-osc defaults
    waves = bridge.toneWaveData
    assert len(waves) == 4
    assert waves[0]["id"] == 579
    assert waves[1]["id"] == 600
    assert waves[2]["id"] == 622
    assert waves[3]["id"] == 625

    # Verify QML views reacted via onPatchInitialized
    assert mfx_view.property("isBypassed") is True
    assert master_fx_view.property("chorusLevel") == bridge.patch_state.effects.chorus_level
    assert master_fx_view.property("reverbLevel") == bridge.patch_state.effects.reverb_level
    assert master_fx_view.property("eqLowGain") == 0
    assert env_view.property("envDepth") == 0


def test_init_patch_preserves_motion_playback():
    """Init holds engine traffic during the restore and resumes prior playback."""
    from unittest.mock import MagicMock

    from src.spectre.vector.motion import AutomatorType, RecorderState

    engine = VectorEngine()
    app, qml_engine, bridge = create_application(engine=engine, platform="offscreen")
    bridge.engine.motion.automator = AutomatorType.CIRCLE
    bridge.engine.motion.play()
    assert bridge.engine.motion.state is RecorderState.PLAYING

    bridge.engine.juno = MagicMock()
    bridge.engine.juno.init_patch.return_value = True
    bridge.initPatch()

    assert bridge.engine.motion.state is RecorderState.PLAYING
    assert bridge.patch_state.effects.routing_preset == ""


def test_pcm_sound_designer_enhancements():
    engine = VectorEngine()
    app, qml_engine, bridge = create_application(engine=engine, platform="offscreen")

    # 1. Test tvaLevel and tone switching
    bridge.setToneLevel(1, 105)
    bridge.setToneLevel(2, 75)
    bridge.setSelectedTone(1)
    assert bridge.tvaLevel == 105

    bridge.setSelectedTone(2)
    assert bridge.tvaLevel == 75

    # 2. Test setTvaLevel affects active tone
    bridge.setTvaLevel(90)
    assert bridge.tone2Level == 90
    assert bridge.tvaLevel == 90

    # 3. Test linkedMode
    bridge.setLinkedMode(True)
    bridge.setTvaLevel(110)
    assert bridge.tone1Level == 110
    assert bridge.tone2Level == 110
    assert bridge.tone3Level == 110
    assert bridge.tone4Level == 110
    bridge.setLinkedMode(False)

    # 4. Test TVA Attack and Release
    bridge.setTvaAttack(15)
    assert bridge.tvaAttack == 15
    bridge.setTvaRelease(45)
    assert bridge.tvaRelease == 45

    # 5. Test Legato Switch
    bridge.setLegatoSwitch(True)
    assert bridge.legatoSwitch is True
    assert bridge.patch_state.common.mono_poly == 0  # MONO
    assert bridge.patch_state.common.portamento_mode == 1  # LEGATO
    bridge.setLegatoSwitch(False)
    assert bridge.legatoSwitch is False
    assert bridge.patch_state.common.mono_poly == 1  # POLY
    assert bridge.patch_state.common.portamento_mode == 0  # NORMAL

    # 6. Test Macro dispatches
    bridge.setMacro(1, 80)
    assert bridge.macro1 == 80
    assert bridge.masterCutoff == 80
    bridge.setMacro(5, 40)
    assert bridge.macro5 == 40
    assert bridge.portamentoTime == 40
    bridge.setMacro(6, 60)
    assert bridge.macro6 == 60
    assert bridge.analogFeel == 60
    bridge.setMacro(7, 35)
    assert bridge.macro7 == 35
    assert bridge.patch_state.effects.chorus_level == 35
    bridge.setMacro(8, 55)
    assert bridge.macro8 == 55
    assert bridge.patch_state.effects.reverb_level == 55


def test_analog_feel_dedicated_control_syncs_macro6():
    """setAnalogFeel updates analog_feel + Macro 6; setMacro(6) syncs analog_feel."""
    engine = VectorEngine()
    app, qml_engine, bridge = create_application(engine=engine, platform="offscreen")

    # Dedicated control keeps macro 6 in sync
    bridge.setAnalogFeel(90)
    assert bridge.analogFeel == 90
    assert bridge.macro6 == 90
    assert bridge.patch_state.common.analog_feel == 90

    # Reverse direction: macro 6 drives analog_feel
    bridge.setMacro(6, 42)
    assert bridge.analogFeel == 42
    assert bridge.patch_state.common.analog_feel == 42

    # Clamping
    bridge.setAnalogFeel(200)
    assert bridge.analogFeel == 127
    bridge.setAnalogFeel(-5)
    assert bridge.analogFeel == 0


def test_sculptor_mutates_all_four_tones():
    """Verify that Sculptor methods sculpt ALL 4 tones regardless of selectedTone or linkedMode."""
    engine = VectorEngine()
    app, qml_engine, bridge = create_application(engine=engine, platform="offscreen")

    # Tone 2 is selected on Juno PCM, linkedMode is False
    bridge.setSelectedTone(2)
    bridge.setLinkedMode(False)
    assert bridge.selectedTone == 2
    assert bridge.linkedMode is False

    # Sculpt TVF Cutoff
    bridge.sculptCutoff(110)
    for t in bridge.patch_state.tones:
        assert t.tvf_cutoff == 110
    assert bridge.masterCutoff == 110

    # Sculpt TVF Resonance
    bridge.sculptReso(95)
    for t in bridge.patch_state.tones:
        assert t.tvf_resonance == 95
    assert bridge.masterReso == 95

    # Sculpt TVF Attack
    bridge.sculptTvfAttack(42)
    for t in bridge.patch_state.tones:
        assert t.tvf_attack == 42
    assert bridge.tvfAttack == 42

    # Sculpt TVA Release
    bridge.sculptTvaRelease(55)
    for t in bridge.patch_state.tones:
        assert t.tva_release == 55
    assert bridge.masterRelease == 55

    # Sculpt LFO1 Rate
    bridge.sculptLfoParam(1, "rate", 88)
    for t in bridge.patch_state.tones:
        assert t.lfo1_rate == 88

    # Sculpt Pitch Coarse (+12 semitones = 76 raw)
    bridge.sculptPitchCoarse(12)
    for t in bridge.patch_state.tones:
        assert t.coarse_tune == 76
    assert bridge.pitchCoarse == 12


def test_va_auto_detune_mode():
    """Verify Auto Detune mode caches custom fine tunes, locks faders, and restores them when disabled."""
    engine = VectorEngine()
    app, qml_engine, bridge = create_application(engine=engine, platform="offscreen")

    # 1. Initial state is OFF
    assert bridge.autoDetune is False

    # 2. Set custom manual fine tunes on OSC 1..4
    bridge.setVaOscFine(1, 0)
    bridge.setVaOscFine(2, -5)
    bridge.setVaOscFine(3, 12)
    bridge.setVaOscFine(4, -8)

    assert bridge.vaOsc1Fine == 0
    assert bridge.vaOsc2Fine == -5
    assert bridge.vaOsc3Fine == 12
    assert bridge.vaOsc4Fine == -8

    # 3. Engage Auto Detune mode
    bridge.setAutoDetune(True)
    assert bridge.autoDetune is True

    # 4. Set auto detune spread to 20 cents
    bridge.setAutoDetuneCents(20)
    assert bridge.autoDetuneCents == 20
    # Formula: [-d, d, -(d // 2), (d // 2)]
    assert bridge.vaOsc1Fine == -20
    assert bridge.vaOsc2Fine == 20
    assert bridge.vaOsc3Fine == -10
    assert bridge.vaOsc4Fine == 10

    # 5. Manual setVaOscFine must be ignored while Auto Detune is active
    bridge.setVaOscFine(1, 45)
    assert bridge.vaOsc1Fine == -20

    # 6. Disengage Auto Detune mode -> must restore custom fine tunes from memory cache
    bridge.setAutoDetune(False)
    assert bridge.autoDetune is False
    assert bridge.vaOsc1Fine == 0
    assert bridge.vaOsc2Fine == -5
    assert bridge.vaOsc3Fine == 12
    assert bridge.vaOsc4Fine == -8

    # 7. Manual editing works again
    bridge.setVaOscFine(1, 15)
    assert bridge.vaOsc1Fine == 15


def test_ui_bridge_step_lfo():
    engine = VectorEngine()
    app, qml_engine, bridge = create_application(engine=engine, platform="offscreen")

    # Initial state on Tone 1
    bridge.setSelectedTone(1)
    assert bridge.selectedTone == 1
    assert bridge.stepLfoCurve == 0
    assert bridge.stepLfoSteps == [0] * 16

    # 1. Update single step on active tone (Tone 1)
    bridge.setStepLfoStep(0, 36)
    assert bridge.stepLfoSteps[0] == 36
    assert bridge.patch_state.tones[0].step_lfo_steps[0] == 36
    # Other tones must not be affected when linkedMode is False
    assert bridge.patch_state.tones[1].step_lfo_steps[0] == 0

    # 2. Clamping step values to -36..+36
    bridge.setStepLfoStep(1, 100)
    assert bridge.stepLfoSteps[1] == 36
    bridge.setStepLfoStep(2, -100)
    assert bridge.stepLfoSteps[2] == -36

    # 3. Update Step Type (curve)
    bridge.setStepLfoParam("curve", 1) # GLIDE
    assert bridge.stepLfoCurve == 1
    assert bridge.patch_state.tones[0].step_lfo_type == 1

    # 4. Switch to Tone 2
    bridge.setSelectedTone(2)
    assert bridge.selectedTone == 2
    assert bridge.stepLfoCurve == 0 # Tone 2 is still STEP (0)
    assert bridge.stepLfoSteps[0] == 0 # Tone 2 step 0 is 0

    # 5. Test setStepLfoAllSteps
    new_shape = [i * 2 for i in range(16)]
    bridge.setStepLfoAllSteps(new_shape)
    assert bridge.stepLfoSteps == [i * 2 for i in range(16)]

    # 6. Test Linked Mode across all 4 tones
    bridge.setLinkedMode(True)
    assert bridge.linkedMode is True
    bridge.setStepLfoStep(5, -20)
    for t in bridge.patch_state.tones:
        assert t.step_lfo_steps[5] == -20

    # 7. Test Quick Assign to LFO 1 and LFO 2
    bridge.setLinkedMode(False)
    bridge.setSelectedTone(1)
    assert bridge.lfo1Wave != "STEP"
    bridge.assignStepLfoToLfo(1)
    assert bridge.lfo1Wave == "STEP"
    assert bridge.patch_state.tones[0].lfo1_waveform == 12

    # Toggle off
    bridge.assignStepLfoToLfo(1)
    assert bridge.lfo1Wave != "STEP"
    assert bridge.patch_state.tones[0].lfo1_waveform == 1 # TRI













def test_envelope_overlay_bridge_api():
    """Generic MSEG editing API: segments, lossless rules, presets, overlay request."""
    from PyQt6.QtCore import QObject

    engine = VectorEngine()
    app, qml_engine, bridge = create_application(engine=engine, platform="offscreen")
    root = qml_engine.rootObjects()[0]

    # Global overlay + thumbnails are instantiated
    assert root.findChild(QObject, "envEditOverlay") is not None
    assert root.findChild(QObject, "pcmTvfEnvThumb") is not None
    assert root.findChild(QObject, "pcmTvaEnvThumb") is not None
    assert root.findChild(QObject, "pcmPitchEnvThumb") is not None
    assert root.findChild(QObject, "sculptTvfEnvThumb") is not None
    assert root.findChild(QObject, "sculptPitchEnvThumb") is not None

    tone = bridge.patch_state.tones[0]

    # Defaults read as canonical (non-custom) shapes
    tvf = bridge.getEnvSegments("TVF")
    assert tvf["times"] == [0, 0, 0, 0]
    assert tvf["levels"] == [0, 127, 127, 127, 0]
    assert tvf["bipolar"] is False
    assert tvf["custom"] is False

    # Raw break-level edit makes a custom shape without touching ADSR sustain
    bridge.setEnvSegment("TVF", "l2", 40)
    assert tone.tvf_l2 == 40
    assert tone.tvf_l3 == 127
    assert bridge.tvfSustain == 127
    assert bridge.getEnvSegments("TVF")["custom"] is True

    # With L2 untied, ADSR sustain must only move L3 (lossless rule)
    bridge.setTvfSustain(100)
    assert tone.tvf_l2 == 40
    assert tone.tvf_l3 == 100

    # TVF preset applies a canonical ADSR-shaped MSEG that ADSR faders describe
    assert "PLUCK" in bridge.envPresetNames("TVF")
    bridge.applyEnvPreset("TVF", "PLUCK")
    seg = bridge.getEnvSegments("TVF")
    assert seg["times"] == [2, 40, 0, 12]
    assert seg["levels"] == [0, 127, 50, 50, 0]
    assert seg["custom"] is False
    assert bridge.tvfAttack == 2
    assert bridge.tvfDecay == 40
    assert bridge.tvfSustain == 50
    assert bridge.tvfRelease == 12

    # TVA preset with L2 != L3 flags custom and preserves 3-level hardware map
    bridge.applyEnvPreset("TVA", "PAD")
    assert (tone.tva_t1, tone.tva_t2, tone.tva_t3, tone.tva_t4) == (80, 30, 40, 60)
    assert (tone.tva_l1, tone.tva_l2, tone.tva_l3) == (127, 96, 110)
    tva = bridge.getEnvSegments("TVA")
    assert tva["custom"] is True
    assert tva["levels"] == [127, 96, 110]
    assert bridge.tvaSustain == 110

    # PITCH levels keep signed semantics through the generic API
    bridge.setEnvSegment("PITCH", "l1", -15)
    assert tone.pitch_env_l1 == 49  # raw 64-15
    assert bridge.pitchEnvL1 == -15
    assert bridge.getEnvSegments("PITCH")["bipolar"] is True

    bridge.applyEnvPreset("PITCH", "KICK THUMP")
    assert tone.pitch_env_l0 == 124  # +60 signed -> raw
    assert (tone.pitch_env_t1, tone.pitch_env_t2, tone.pitch_env_t3, tone.pitch_env_t4) == (2, 25, 10, 15)

    # Overlay open request reaches QML layer with normalized env name
    captured = []
    bridge.requestOpenEnvOverlay.connect(lambda e: captured.append(e))
    bridge.openEnvOverlay("tva")
    assert captured == ["TVA"]


def test_tone_switch_refreshes_env_shapes():
    """envShapeChanged fires on tone switch so thumbs/overlays repaint per tone."""
    engine = VectorEngine()
    app, qml_engine, bridge = create_application(engine=engine, platform="offscreen")

    received = []
    bridge.envShapeChanged.connect(lambda e: received.append(e))

    bridge.applyEnvPreset("TVF", "PLUCK")
    bridge.setSelectedTone(2)

    assert "TVF" in received
    assert received.count("TVF") >= 2
    # Tone 2 stays canonical after editing Tone 1
    assert bridge.getEnvSegments("TVF")["levels"] == [0, 127, 127, 127, 0]
    assert bridge.getEnvSegments("TVF")["custom"] is False


def test_env_modifier_bridge_api():
    """Shared signed-modifier API across TVF / TVA / Pitch envelopes."""
    engine = VectorEngine()
    app, qml_engine, bridge = create_application(engine=engine, platform="offscreen")
    tone = bridge.patch_state.tones[0]

    # TVF: signed input maps to raw 64-center, time-KF snaps to 10% steps
    bridge.setEnvModParam("TVF", "envDepth", -20)
    assert tone.tvf_env_depth == 44
    assert bridge.getEnvSegments("TVF")["mods"]["envDepth"] == -20

    bridge.setEnvModParam("TVF", "t1VelSens", 30)
    assert tone.tvf_env_t1_vel_sens == 94
    bridge.setEnvModParam("TVF", "t4VelSens", -10)
    assert tone.tvf_env_t4_vel_sens == 54
    bridge.setEnvModParam("TVF", "timeKeyfollow", 50)
    assert tone.tvf_env_time_keyfollow == 69
    assert bridge.getEnvSegments("TVF")["mods"]["timeKf"] == 50

    # TVA: velSens shares the main-page Level V-Sens raw value
    bridge.setEnvModParam("TVA", "velSens", 25)
    assert tone.tva_velo_sens == 89
    assert bridge.tvaVeloSens == 89
    assert bridge.getEnvSegments("TVA")["mods"]["velSens"] == 25
    bridge.setEnvModParam("TVA", "t4VelSens", -10)
    assert tone.tva_env_t4_vel_sens == 54

    # Pitch modifiers keep established signed semantics via delegation
    bridge.setEnvModParam("PITCH", "timeKeyfollow", -50)
    assert tone.pitch_env_time_keyfollow == 59
    assert bridge.getEnvSegments("PITCH")["mods"]["timeKf"] == -50
    bridge.setEnvModParam("PITCH", "depth", 6)
    assert bridge.pitchEnvDepth == 6

    # Emitted envShapeChanged carries the edited envelope name
    received = []
    bridge.envShapeChanged.connect(lambda e: received.append(e))
    bridge.setEnvModParam("TVF", "velSens", 10)
    bridge.setEnvModParam("TVA", "t1VelSens", -5)
    assert received == ["TVF", "TVA"]
