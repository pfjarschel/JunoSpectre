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

    views = ["VECTOR", "WAVETABLE", "MACROS", "PATCH EDIT", "PERF MIXER", "EFFECTS"]
    for v in views:
        bridge.setActiveView(v)
        assert bridge.activeView == v
        if v == "VECTOR":
            assert bridge.morphMode == "vector_2d"
        elif v == "WAVETABLE":
            assert bridge.morphMode == "wavetable_1d"

