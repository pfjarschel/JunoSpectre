import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

Rectangle {
    id: root
    height: ScaleMetrics.dp(54)
    color: Theme.bgCard
    border.color: Theme.borderCard
    border.width: 1

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: ScaleMetrics.dp(12)
        anchors.rightMargin: ScaleMetrics.dp(12)
        spacing: ScaleMetrics.dp(10)

        // Logo / Title (text hidden in PERFORM to make room for Perf/Part context)
        RowLayout {
            spacing: ScaleMetrics.dp(6)
            Text {
                text: "🌑"
                font.pixelSize: ScaleMetrics.sp(16)
            }
            Text {
                visible: Bridge.soundMode !== "PERFORM"
                text: "JUNO SPECTRE"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(12)
                font.letterSpacing: 1.2
                color: Theme.textPrimary
            }
        }

        // Screens Launcher Trigger Button (narrower in PERFORM for context room)
        Rectangle {
            id: screensBtn
            Layout.fillWidth: true
            Layout.preferredWidth: Bridge.soundMode === "PERFORM" ? ScaleMetrics.dp(150) : ScaleMetrics.dp(240)
            Layout.maximumWidth: Bridge.soundMode === "PERFORM" ? ScaleMetrics.dp(190) : ScaleMetrics.dp(320)
            height: ScaleMetrics.dp(40)
            radius: ScaleMetrics.dp(6)
            color: screensArea.pressed ? Theme.bgCardActive : Theme.bgApp
            border.color: screensArea.pressed ? Theme.primary : Theme.borderCard
            border.width: 1

            readonly property color viewAccent: {
                const v = Bridge.activeView;
                if (v === "JUNO PCM" || v === "VECTOR") return Theme.tone1;
                if (v === "WAVETABLE") return Theme.tone3;
                if (v === "VA" || v === "MACROS") return Theme.tone2;
                if (v === "MOD MATRIX" || v === "PATCH EDIT") return "#38bdf8";
                if (v === "STEP LFO" || v === "SEQUENCER") return "#10b981";
                if (v === "MSEG ENVELOPES") return "#fbbf24";
                if (v === "MFX") return "#ec4899";
                if (v === "ROUTING") return "#06b6d4";
                if (v === "MASTER FX" || v === "PERFORMANCE") return "#a855f7";
                if (v === "LIBRARIAN") return "#60a5fa";
                if (v === "MIDI LEARN") return "#f59e0b";
                if (v === "HARDWARE") return "#94a3b8";
                if (v === "SYSTEM") return "#ef4444";
                return Theme.primary;
            }

            RowLayout {
                anchors.centerIn: parent
                spacing: ScaleMetrics.dp(8)

                Rectangle {
                    width: ScaleMetrics.dp(20)
                    height: ScaleMetrics.dp(20)
                    radius: ScaleMetrics.dp(4)
                    color: Theme.bgSurface
                    Text {
                        anchors.centerIn: parent
                        text: "⊞"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(11)
                        color: screensBtn.viewAccent
                    }
                }

                Text {
                    text: "SCREENS:"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(9)
                    color: Theme.textDim
                }

                Text {
                    text: Bridge.activeView
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(11)
                    color: screensBtn.viewAccent
                }

                Text {
                    text: "▼"
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: Theme.textSecondary
                }
            }

            MouseArea {
                id: screensArea
                anchors.fill: parent
                onClicked: Bridge.openScreensOverlay()
            }
        }

        // Synth Mode Badge
        Rectangle {
            height: ScaleMetrics.dp(32)
            width: ScaleMetrics.dp(60)
            radius: ScaleMetrics.dp(4)
            color: Bridge.soundMode === "PATCH" ? "#1e293b" : "#2d1b4e"
            border.color: Bridge.soundMode === "PATCH" ? Theme.primary : Theme.tone2
            border.width: 1

            Text {
                anchors.centerIn: parent
                text: Bridge.soundMode
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(10)
                color: Bridge.soundMode === "PATCH" ? Theme.primary : Theme.tone2
            }
        }

        // Active Patch Name Display with Sync, Init and Save Buttons
        // (stretches in PERFORM to show "PERFNAME / N-PATCHNAME" context)
        Rectangle {
            Layout.preferredWidth: ScaleMetrics.dp(279)
            Layout.fillWidth: Bridge.soundMode === "PERFORM"
            height: ScaleMetrics.dp(38)
            radius: ScaleMetrics.dp(4)
            color: Theme.bgApp
            border.color: Theme.borderCard
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: ScaleMetrics.dp(8)
                anchors.rightMargin: ScaleMetrics.dp(4)
                spacing: ScaleMetrics.dp(4)

                Text {
                    Layout.fillWidth: true
                    text: (Bridge.soundMode === "PERFORM" && Bridge.perfContext !== "") ? Bridge.perfContext : Bridge.patchName
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(11)
                    color: Theme.textPrimary
                    elide: Text.ElideRight
                    MouseArea {
                        anchors.fill: parent
                        onClicked: Bridge.toggleLibrarian()
                    }
                }

                // Sync button (patch only — disabled in PERFORM, perf has its own sync)
                Rectangle {
                    id: syncBtn
                    width: ScaleMetrics.dp(46)
                    height: ScaleMetrics.dp(30)
                    radius: ScaleMetrics.dp(3)
                    color: syncArea.pressed ? Theme.bgCardActive : Theme.bgSurface
                    border.color: syncArea.pressed ? Theme.tone1 : Theme.borderCard
                    border.width: 1
                    enabled: Bridge.soundMode !== "PERFORM"
                    opacity: enabled ? 1.0 : 0.35

                    RowLayout {
                        anchors.centerIn: parent
                        spacing: 2
                        Text {
                            text: "⟳"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(11)
                            color: Theme.tone1
                        }
                        Text {
                            text: "SYNC"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: Theme.textSecondary
                        }
                    }

                    MouseArea {
                        id: syncArea
                        anchors.fill: parent
                        enabled: syncBtn.enabled
                        onClicked: {
                            Bridge.syncPatchFromSynth();
                        }
                    }
                }

                // Init button (patch only — disabled in PERFORM)
                Rectangle {
                    id: initBtn
                    width: ScaleMetrics.dp(44)
                    height: ScaleMetrics.dp(30)
                    radius: ScaleMetrics.dp(3)
                    color: initArea.pressed ? Theme.bgCardActive : Theme.bgSurface
                    border.color: initArea.pressed ? "#fbbf24" : Theme.borderCard
                    border.width: 1
                    enabled: Bridge.soundMode !== "PERFORM"
                    opacity: enabled ? 1.0 : 0.35

                    RowLayout {
                        anchors.centerIn: parent
                        spacing: 2
                        Text {
                            text: "✦"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(10)
                            color: "#fbbf24"
                        }
                        Text {
                            text: "INIT"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: Theme.textSecondary
                        }
                    }

                    MouseArea {
                        id: initArea
                        anchors.fill: parent
                        enabled: initBtn.enabled
                        onClicked: {
                            Bridge.openInitPatchModal();
                        }
                    }
                }

                // Save button (Pi-always + optional keyboard slot)
                Rectangle {
                    id: saveBtn
                    width: ScaleMetrics.dp(48)
                    height: ScaleMetrics.dp(30)
                    radius: ScaleMetrics.dp(3)
                    color: saveArea.pressed ? Theme.bgCardActive : Theme.bgSurface
                    border.color: saveArea.pressed ? "#38bdf8" : Theme.borderCard
                    border.width: 1

                    RowLayout {
                        anchors.centerIn: parent
                        spacing: 2
                        Text {
                            text: "💾"
                            font.pixelSize: ScaleMetrics.sp(10)
                            color: "#38bdf8"
                        }
                        Text {
                            text: "SAVE"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: Theme.textSecondary
                        }
                    }

                    MouseArea {
                        id: saveArea
                        anchors.fill: parent
                        onClicked: {
                            Bridge.openSavePatchModal();
                        }
                    }
                }
            }
        }

        // BPM Display
        Rectangle {
            height: ScaleMetrics.dp(38)
            width: ScaleMetrics.dp(70)
            radius: ScaleMetrics.dp(4)
            color: Theme.bgApp
            border.color: Theme.borderCard
            border.width: 1

            RowLayout {
                anchors.centerIn: parent
                spacing: ScaleMetrics.dp(4)

                Text {
                    text: "BPM"
                    font.pixelSize: ScaleMetrics.sp(9)
                    font.bold: true
                    color: Theme.textDim
                }
                Text {
                    text: Math.round(Bridge.bpm)
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(12)
                    color: Theme.tone3
                }
            }
        }

        // Panic Button (All Notes Off)
        Rectangle {
            height: ScaleMetrics.dp(38)
            width: ScaleMetrics.dp(60)
            radius: ScaleMetrics.dp(4)
            color: panicArea.pressed ? "#591c1c" : "#3f1a1a"
            border.color: Theme.recording
            border.width: 1

            Text {
                anchors.centerIn: parent
                text: "PANIC"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(9)
                color: Theme.recording
            }

            MouseArea {
                id: panicArea
                anchors.fill: parent
                onClicked: Bridge.panic()
            }
        }
    }
}

