import QtQuick
import QtQuick.Window
import QtQuick.Layouts
import JunoSpectre
import "components"

Window {
    id: window
    visible: true
    width: 1024
    height: 600
    minimumWidth: 800
    minimumHeight: 480
    title: "Juno Spectre - Touch Workstation"
    color: Theme.bgApp

    // Bind dynamic dimensions to ScaleMetrics singleton
    Component.onCompleted: {
        ScaleMetrics.rootWidth = width
        ScaleMetrics.rootHeight = height
    }
    onWidthChanged: ScaleMetrics.rootWidth = width
    onHeightChanged: ScaleMetrics.rootHeight = height

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // 1. Top Header Bar
        HeaderBar {
            Layout.fillWidth: true
        }

        // 2. 8-Encoder Context Strip (Hidden on System & Utility screens to maximize workspace)
        ContextStrip {
            Layout.fillWidth: true
            visible: Bridge.activeView !== "HARDWARE" &&
                     Bridge.activeView !== "SYSTEM" &&
                     Bridge.activeView !== "LIBRARIAN" &&
                     Bridge.activeView !== "MIDI LEARN"
        }

        // 3. Main Central Workspace (Self-Contained Full Canvas)
        StackLayout {
            id: workspaceStack
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.leftMargin: ScaleMetrics.dp(10)
            Layout.rightMargin: ScaleMetrics.dp(10)
            Layout.topMargin: ScaleMetrics.dp(6)
            Layout.bottomMargin: ScaleMetrics.dp(8)

            currentIndex: {
                switch (Bridge.activeView) {
                    case "JUNO PCM": return 0;
                    case "VECTOR": return 1;
                    case "WAVETABLE": return 2;
                    case "VA": return 3;
                    case "MOD MATRIX": return 4;
                    case "STEP LFO": return 5;
                    case "PITCH ENV": return 6;
                    case "MFX": return 7;
                    case "MASTER FX": return 8;
                    case "MACROS": return 9;
                    case "PERF MIXER": return 10;
                    case "SEQUENCER": return 11;
                    case "LIBRARIAN": return 12;
                    case "MIDI LEARN": return 13;
                    case "HARDWARE": return 14;
                    case "SYSTEM": return 15;
                    default: return 0;
                }
            }

            // =================================================================
            // 1. SYNTH ENGINES
            // =================================================================

            // View 0: Standard 4-Tone Juno PCM Sound Designer (Default Boot Screen)
            PatchEditView {
                id: pcmView
                objectName: "pcmView"
            }

            // View 1: 2D Vector Touch Pad & Morph Orbit
            VectorPad {
                id: padView
                objectName: "padView"
            }

            // View 2: 1D Wavetable Morph Slider & Scope
            WavetableSlider {
                id: wtView
                objectName: "wtView"
            }

            // View 3: 4-OSC Virtual Analog Console
            VaView {
                id: vaView
                objectName: "vaView"
            }

            // =================================================================
            // 2. MODULATION & FX
            // =================================================================

            // View 4: Modulation Matrix (4 Matrix Controllers)
            ModMatrixView {
                id: modMatrixView
                objectName: "modMatrixView"
            }

            // View 5: 16-Step Pattern LFO Modulator
            StepLfoView {
                id: stepLfoView
                objectName: "stepLfoView"
            }

            // View 6: Multi-Segment Bipolar Pitch Envelope
            PitchEnvView {
                id: pitchEnvView
                objectName: "pitchEnvView"
            }

            // View 7: Dedicated Multi-Effects (MFX) Studio (80 Algorithms)
            MfxView {
                id: mfxView
                objectName: "mfxView"
            }

            // View 8: Master Chorus, Reverb & 3-Band Parametric EQ
            MasterFxView {
                id: masterFxView
                objectName: "masterFxView"
            }

            // =================================================================
            // 3. PERFORMANCE & PLAY
            // =================================================================

            // View 9: Macro Play Deck (8 Large Touch Dials)
            MacroDeck {
                id: macroView
                objectName: "macroView"
            }

            // View 10: Performance Multi-Zone & Layer Mixer
            PerfMixerView {
                id: mixerView
                objectName: "mixerView"
            }

            // View 11: 16-Step Trigger Sequencer & Arpeggiator
            SeqView {
                id: seqView
                objectName: "seqView"
            }

            // =================================================================
            // 4. SYSTEM & UTILITIES
            // =================================================================

            // View 12: Preset & Patch Librarian
            LibrarianView {
                id: librarianView
                objectName: "librarianView"
            }

            // View 13: MIDI Learn & CC Controller Surface Mapping
            MidiLearnView {
                id: midiLearnView
                objectName: "midiLearnView"
            }

            // View 14: Hardware Configuration (Juno-DS & External Controllers)
            HardwareConfigView {
                id: hardwareView
                objectName: "hardwareView"
            }

            // View 15: Appliance System Control (Pi Telemetry, Brightness, Restart)
            SystemView {
                id: systemView
                objectName: "systemView"
            }
        }
    }

    // Global Modal: 16-App Screens Launcher Overlay
    ScreensOverlay {
        id: screensOverlay
        objectName: "screensOverlay"
    }

    // Global Modal: Interactive Waveform Browser
    WaveBrowserModal {
        id: waveBrowserModal
        objectName: "waveBrowserModal"
    }

    // Global Modal: Patch Initialization Confirmation
    InitPatchModal {
        id: initPatchModal
        objectName: "initPatchModal"
    }

    // Global Bridge signal listeners
    Connections {
        target: Bridge
        function onRequestOpenScreensOverlay() {
            screensOverlay.open();
        }
        function onRequestOpenWaveBrowser(toneIndex) {
            waveBrowserModal.open(toneIndex);
        }
        function onRequestOpenInitPatchModal() {
            initPatchModal.open();
        }
    }
}
