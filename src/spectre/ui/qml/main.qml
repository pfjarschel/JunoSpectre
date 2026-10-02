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

        // 2. 8-Encoder Context Strip
        ContextStrip {
            Layout.fillWidth: true
        }

        // 3. Main Central Workspace
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.leftMargin: ScaleMetrics.dp(12)
            Layout.rightMargin: ScaleMetrics.dp(20)
            Layout.topMargin: ScaleMetrics.dp(6)
            Layout.bottomMargin: ScaleMetrics.dp(6)
            spacing: ScaleMetrics.dp(10)

            // Primary Interactive Canvas (Multi-View Workspace)
            StackLayout {
                id: workspaceStack
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentIndex: {
                    switch (Bridge.activeView) {
                        case "VECTOR": return 0;
                        case "WAVETABLE": return 1;
                        case "MACROS": return 2;
                        case "PATCH EDIT": return 3;
                        case "PERF MIXER": return 4;
                        case "EFFECTS": return 5;
                        default: return 0;
                    }
                }

                // View 0: 2D Vector Touch Pad
                VectorPad {
                    id: padView
                }

                // View 1: 1D Wavetable Morph Slider
                WavetableSlider {
                    id: wtView
                }

                // View 2: Macro Play Deck (8 Large Touch Knobs)
                MacroDeck {
                    id: macroView
                }

                // View 3: Patch & Tone Editor (Filter Curve & ADSR)
                PatchEditView {
                    id: patchView
                }

                // View 4: Performance Layer & Zone Mixer
                PerfMixerView {
                    id: mixerView
                }

                // View 5: Effects (MFX) Studio
                EffectsView {
                    id: fxView
                }
            }

            // Persistent 4-Tone Strip (VU Meters, On/Mute toggles & Master controls)
            PersistentToneStrip {
                Layout.fillHeight: true
            }
        }

        // 4. Bottom Motion & Automator Toolbar
        MotionControls {
            Layout.fillWidth: true
        }
    }
}
