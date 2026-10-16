pragma ValueTypeBehavior: Copy
import QtQuick
import QtQuick.Layouts
import JunoSpectre
import "components"

// The whole workstation UI: header, pages and global modals. main.qml loads
// it into the window (after the splash frame on the appliance, see app.py).
Item {
    id: appContent

    // A page is built the first time it is shown and then stays (keeping its
    // local state): startup builds only the boot page, and pages never opened
    // don't re-evaluate their bindings on every state broadcast.
    component Page: Loader {
        id: page
        required property int pageIndex
        active: false
        function show() {
            if (!active && workspaceStack.currentIndex === pageIndex)
                active = true;
        }
        Component.onCompleted: show()
        Connections {
            target: workspaceStack
            function onCurrentIndexChanged() { page.show(); }
        }
    }

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
            Page {
                pageIndex: 0
                sourceComponent: PatchEditView { objectName: "pcmView" }
            }

            // View 1 VECTOR: 2D vector touch pad & morph orbit
            Page {
                pageIndex: 1
                sourceComponent: VectorPad { objectName: "padView" }
            }

            // View 2 WAVETABLE: 1D wavetable morph slider & scope
            Page {
                pageIndex: 2
                sourceComponent: WavetableSlider { objectName: "wtView" }
            }

            // View 3 VA: 4-osc virtual analog console
            Page {
                pageIndex: 3
                sourceComponent: VaView { objectName: "vaView" }
            }

            // =================================================================
            // 2. MODULATION & FX
            // =================================================================

            // View 4 MOD MATRIX: 4 matrix controllers
            Page {
                pageIndex: 4
                sourceComponent: ModMatrixView { objectName: "modMatrixView" }
            }

            // View 5 STEP LFO: 16-step pattern LFO
            Page {
                pageIndex: 5
                sourceComponent: StepLfoView { objectName: "stepLfoView" }
            }

            // View 6 MSEG ENVELOPES: TVF / TVA / PITCH envelope editor
            Page {
                pageIndex: 6
                sourceComponent: EnvEditorView { objectName: "envEditorView" }
            }

            // View 7 MFX: multi-effects studio (80 algorithms)
            Page {
                pageIndex: 7
                sourceComponent: MfxView { objectName: "mfxView" }
            }

            // View 8 ROUTING: tone & FX routing graph
            Page {
                pageIndex: 8
                sourceComponent: RoutingView { objectName: "routingView" }
            }

            // View 9 MASTER FX: chorus & reverb
            Page {
                pageIndex: 9
                sourceComponent: MasterFxView { objectName: "masterFxView" }
            }

            // =================================================================
            // 3. PERFORMANCE & PLAY
            // =================================================================

            // View 10 LIVE: live session matrix & macros
            Page {
                pageIndex: 10
                sourceComponent: LiveModeView { objectName: "liveView" }
            }

            // View 11 SEQUENCER: polyphonic step sequencer & motion
            Page {
                pageIndex: 11
                sourceComponent: SeqView { objectName: "seqView" }
            }

            // View 12 SETLIST: setlist & repertoire
            Page {
                pageIndex: 12
                sourceComponent: SetlistView { objectName: "setlistView" }
            }

            // View 13 PERFORMANCE: 16-part mixer, zones & layers
            Page {
                pageIndex: 13
                sourceComponent: PerfMixerView { objectName: "mixerView" }
            }

            // View 14 MACROS: macro play deck (8 large dials)
            Page {
                pageIndex: 14
                sourceComponent: MacroDeck { objectName: "macroView" }
            }

            // =================================================================
            // 4. SYSTEM & UTILITIES
            // =================================================================

            // View 15 LIBRARIAN: patches, performances & songs
            Page {
                pageIndex: 15
                sourceComponent: LibrarianView { objectName: "librarianView" }
            }

            // View 16 MIDI LEARN: controller bindings
            Page {
                pageIndex: 16
                sourceComponent: MidiLearnView { objectName: "midiLearnView" }
            }

            // View 17 HARDWARE: Juno-DS & external controllers
            Page {
                pageIndex: 17
                sourceComponent: HardwareConfigView { objectName: "hardwareView" }
            }

            // View 18 SYSTEM: Pi telemetry, brightness, Wi-Fi, updates
            Page {
                pageIndex: 18
                sourceComponent: SystemView { objectName: "systemView" }
            }

            // View 19 ARPEGGIO: synth arp + MIDI clock out
            Page {
                pageIndex: 19
                sourceComponent: ArpView { objectName: "arpView" }
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
