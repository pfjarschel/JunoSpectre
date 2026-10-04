import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

Rectangle {
    id: root
    height: ScaleMetrics.dp(44)
    color: Theme.bgCard
    border.color: Theme.borderCard
    border.width: 1

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: ScaleMetrics.dp(12)
        anchors.rightMargin: ScaleMetrics.dp(12)
        spacing: ScaleMetrics.dp(10)

        // Logo / Title
        RowLayout {
            spacing: ScaleMetrics.dp(6)
            Rectangle {
                width: ScaleMetrics.dp(8)
                height: ScaleMetrics.dp(8)
                radius: width / 2
                color: Theme.tone1
            }
            Text {
                text: "JUNO SPECTRE"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(12)
                font.letterSpacing: 1.2
                color: Theme.textPrimary
            }
        }

        // Synth Mode Badge
        Rectangle {
            height: ScaleMetrics.dp(24)
            width: ScaleMetrics.dp(56)
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

        // Active Patch Name Display with Sync Button
        Rectangle {
            Layout.preferredWidth: ScaleMetrics.dp(185)
            Layout.fillWidth: false
            height: ScaleMetrics.dp(28)
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
                    text: Bridge.patchName
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(11)
                    color: Theme.textPrimary
                    elide: Text.ElideRight
                }

                // Sync button
                Rectangle {
                    id: syncBtn
                    width: ScaleMetrics.dp(42)
                    height: ScaleMetrics.dp(22)
                    radius: ScaleMetrics.dp(3)
                    color: syncArea.pressed ? Theme.bgCardActive : Theme.bgSurface
                    border.color: syncArea.pressed ? Theme.tone1 : Theme.borderCard
                    border.width: 1

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
                        onClicked: {
                            Bridge.syncPatchFromSynth();
                        }
                    }
                }
            }
        }

        // Screens Launcher Trigger Button
        Rectangle {
            id: screensBtn
            Layout.fillWidth: true
            Layout.preferredWidth: ScaleMetrics.dp(240)
            Layout.maximumWidth: ScaleMetrics.dp(320)
            height: ScaleMetrics.dp(32)
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
                if (v === "PITCH ENV") return "#fbbf24";
                if (v === "MFX") return "#ec4899";
                if (v === "MASTER FX" || v === "PERF MIXER") return "#a855f7";
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

        // BPM Display
        Rectangle {
            height: ScaleMetrics.dp(28)
            width: ScaleMetrics.dp(68)
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
            height: ScaleMetrics.dp(28)
            width: ScaleMetrics.dp(54)
            radius: ScaleMetrics.dp(4)
            color: "#3f1a1a"
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
                anchors.fill: parent
                onClicked: Bridge.panic()
            }
        }
    }
}

