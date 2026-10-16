pragma ValueTypeBehavior: Copy
import QtQuick
import QtQuick.Layouts
import JunoSpectre
import "components"

// The whole workstation UI: header, pages and global modals. main.qml loads
// it into the window (after the splash frame on the appliance, see app.py).
Item {
    id: appContent

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // 1. Top Header Bar
        HeaderBar {
            Layout.fillWidth: true
        }

        // 2. 8-Encoder Context Strip (only on pages that define context knobs)
        ContextStrip {
            Layout.fillWidth: true
            visible: Bridge.contextKnobsAvailable
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
                    case "MSEG ENVELOPES": return 6;
                    case "MFX": return 7;
                    case "ROUTING": return 8;
                    case "MASTER FX": return 9;
                    case "LIVE": return 10;
                    case "SEQUENCER": return 11;
                    case "SETLIST": return 12;
                    case "PERFORMANCE": return 13;
                    case "MACROS": return 14;
                    case "LIBRARIAN": return 15;
                    case "MIDI LEARN": return 16;
                    case "HARDWARE": return 17;
                    case "SYSTEM": return 18;
                    case "ARPEGGIO": return 19;
                    default: return 0;
                }
            }

            // =================================================================
            // 1. SYNTH ENGINES
            // =================================================================

            // View 0 JUNO PCM: 4-tone PCM sound designer (boot screen)
            PatchEditView {
                id: pcmView
                objectName: "pcmView"
            }

            // View 1 VECTOR: 2D vector touch pad & morph orbit
            VectorPad {
                id: padView
                objectName: "padView"
            }

            // View 2 WAVETABLE: 1D wavetable morph slider & scope
            WavetableSlider {
                id: wtView
                objectName: "wtView"
            }

            // View 3 VA: 4-osc virtual analog console
            VaView {
                id: vaView
                objectName: "vaView"
            }

            // =================================================================
            // 2. MODULATION & FX
            // =================================================================

            // View 4 MOD MATRIX: 4 matrix controllers
            ModMatrixView {
                id: modMatrixView
                objectName: "modMatrixView"
            }

            // View 5 STEP LFO: 16-step pattern LFO
            StepLfoView {
                id: stepLfoView
                objectName: "stepLfoView"
            }

            // View 6 MSEG ENVELOPES: TVF / TVA / PITCH envelope editor
            EnvEditorView {
                id: envEditorView
                objectName: "envEditorView"
            }

            // View 7 MFX: multi-effects studio (80 algorithms)
            MfxView {
                id: mfxView
                objectName: "mfxView"
            }

            // View 8 ROUTING: tone & FX routing graph
            RoutingView {
                id: routingView
                objectName: "routingView"
            }

            // View 9 MASTER FX: chorus & reverb
            MasterFxView {
                id: masterFxView
                objectName: "masterFxView"
            }

            // =================================================================
            // 3. PERFORMANCE & PLAY
            // =================================================================

            // View 10 LIVE: live session matrix & macros
            LiveModeView {
                id: liveView
                objectName: "liveView"
            }

            // View 11 SEQUENCER: polyphonic step sequencer & motion
            SeqView {
                id: seqView
                objectName: "seqView"
            }

            // View 12 SETLIST: setlist & repertoire
            SetlistView {
                id: setlistView
                objectName: "setlistView"
            }

            // View 13 PERFORMANCE: 16-part mixer, zones & layers
            PerfMixerView {
                id: mixerView
                objectName: "mixerView"
            }

            // View 14 MACROS: macro play deck (8 large dials)
            MacroDeck {
                id: macroView
                objectName: "macroView"
            }

            // =================================================================
            // 4. SYSTEM & UTILITIES
            // =================================================================

            // View 15 LIBRARIAN: patches, performances & songs
            LibrarianView {
                id: librarianView
                objectName: "librarianView"
            }

            // View 16 MIDI LEARN: controller bindings
            MidiLearnView {
                id: midiLearnView
                objectName: "midiLearnView"
            }

            // View 17 HARDWARE: Juno-DS & external controllers
            HardwareConfigView {
                id: hardwareView
                objectName: "hardwareView"
            }

            // View 18 SYSTEM: Pi telemetry, brightness, Wi-Fi, updates
            SystemView {
                id: systemView
                objectName: "systemView"
            }

            // View 19 ARPEGGIO: synth arp + MIDI clock out
            ArpView {
                id: arpView
                objectName: "arpView"
            }
        }
    }

    // Global modal: screens launcher overlay
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

    // Global Modal: Save Sound (Pi-always + optional keyboard slot)
    SavePatchModal {
        id: savePatchModal
        objectName: "savePatchModal"
    }

    // Global Modal: Macro Assign / Edit (customizable relative macros)
    MacroEditModal {
        id: macroEditModal
        objectName: "macroEditModal"
    }

    // Global Modal: Quick-Edit Envelope Overlay (TVF / TVA / PITCH)
    EnvEditOverlay {
        id: envEditOverlay
        objectName: "envEditOverlay"
    }

    // Global Modal: Tone Mix Table (structure types, booster, key/velocity ranges)
    TmtOverlay {
        id: tmtOverlay
        objectName: "tmtOverlay"
    }

    // Global Modal: part + MFX being edited (PERFORM), from the header tag
    EditTargetPicker {
        id: editTargetPicker
        objectName: "editTargetPicker"
    }

    // Hardware control under the hand, when the page can't highlight it
    TouchToast {
        objectName: "touchToast"
        anchors.horizontalCenter: parent.horizontalCenter
        y: ScaleMetrics.dp(62)
        z: 50
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
        function onRequestOpenSavePatchModal() {
            savePatchModal.open();
        }
        function onRequestOpenMacroAssign(macroIndex) {
            macroEditModal.open(macroIndex);
        }
        function onRequestOpenEnvOverlay(env) {
            envEditOverlay.open(env);
        }
        function onRequestOpenTmtOverlay(tab) {
            tmtOverlay.open(tab);
        }
        function onRequestOpenEditTarget() {
            editTargetPicker.open();
        }
    }
}
