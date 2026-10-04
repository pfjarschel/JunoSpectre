import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

Rectangle {
    id: root
    anchors.fill: parent
    visible: false
    z: 999
    color: "#e60a0c10" // Deep translucent backdrop

    function open() {
        visible = true;
    }

    function close() {
        visible = false;
    }

    MouseArea {
        anchors.fill: parent
        onClicked: root.close()
    }

    // Modal Card Container
    Rectangle {
        id: card
        width: Math.min(parent.width - ScaleMetrics.dp(32), ScaleMetrics.dp(480))
        height: ScaleMetrics.dp(290)
        anchors.centerIn: parent
        radius: ScaleMetrics.dp(8)
        color: Theme.bgCard
        border.color: "#fbbf24"
        border.width: 1

        MouseArea {
            anchors.fill: parent
            // Prevent close on card background click
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(14)
            spacing: ScaleMetrics.dp(10)

            // Header Bar
            RowLayout {
                Layout.fillWidth: true
                spacing: ScaleMetrics.dp(8)

                Rectangle {
                    width: ScaleMetrics.dp(24)
                    height: ScaleMetrics.dp(24)
                    radius: ScaleMetrics.dp(4)
                    color: "#2a2210"
                    border.color: "#fbbf24"
                    border.width: 1
                    Text {
                        anchors.centerIn: parent
                        text: "✦"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(12)
                        color: "#fbbf24"
                    }
                }

                Text {
                    text: "INITIALIZE ACTIVE SOUND (RAM)"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(11)
                    font.letterSpacing: 1.1
                    color: Theme.textPrimary
                }

                Item { Layout.fillWidth: true }

                Rectangle {
                    width: ScaleMetrics.dp(26)
                    height: ScaleMetrics.dp(26)
                    radius: ScaleMetrics.dp(4)
                    color: closeArea.pressed ? Theme.bgCardActive : "#10141d"
                    border.color: Theme.borderCard
                    border.width: 1
                    Text {
                        anchors.centerIn: parent
                        text: "✕"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(10)
                        color: Theme.textSecondary
                    }
                    MouseArea {
                        id: closeArea
                        anchors.fill: parent
                        onClicked: root.close()
                    }
                }
            }

            // Description / Template Spec Box
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: ScaleMetrics.dp(6)
                color: "#0d1017"
                border.color: Theme.borderCard
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(10)
                    spacing: ScaleMetrics.dp(5)

                    Text {
                        text: "Reset current sound in RAM to clean JUNO SPECTRE template:"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(9)
                        color: Theme.textPrimary
                    }

                    ColumnLayout {
                        spacing: ScaleMetrics.dp(3)
                        Layout.leftMargin: ScaleMetrics.dp(4)

                        Text {
                            text: "• TVF: Max Cutoff (127), 0 Resonance, 0 Env Depth, LPF"
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: Theme.textSecondary
                        }
                        Text {
                            text: "• TVA: Instant Attack (0), 0 Decay, 100% Sustain, 0 Release"
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: Theme.textSecondary
                        }
                        Text {
                            text: "• Modulation: All LFO 1 & 2 depths and Pitch Env zeroed"
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: Theme.textSecondary
                        }
                        Text {
                            text: "• Effects: MFX bypassed, Chorus & Reverb off, Master EQ flat"
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: Theme.textSecondary
                        }
                        Text {
                            text: "• Tone Waves: Restored to 4 'JUNO SPECTRE' core waves"
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: Theme.tone1
                        }
                    }

                    Item { Layout.fillHeight: true }

                    Text {
                        text: "Note: Saved flash memory is untouched. Edits apply only to active RAM."
                        font.pixelSize: ScaleMetrics.sp(7)
                        font.italic: true
                        color: Theme.textDim
                    }
                }
            }

            // Action Buttons Row
            RowLayout {
                Layout.fillWidth: true
                spacing: ScaleMetrics.dp(8)

                Rectangle {
                    Layout.preferredWidth: ScaleMetrics.dp(120)
                    height: ScaleMetrics.dp(36)
                    radius: ScaleMetrics.dp(4)
                    color: cancelArea.pressed ? Theme.bgCardActive : "#10141d"
                    border.color: Theme.borderCard
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: "CANCEL"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(9)
                        color: Theme.textSecondary
                    }

                    MouseArea {
                        id: cancelArea
                        anchors.fill: parent
                        onClicked: root.close()
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: ScaleMetrics.dp(36)
                    radius: ScaleMetrics.dp(4)
                    color: confirmArea.pressed ? "#45320d" : "#2a2210"
                    border.color: "#fbbf24"
                    border.width: 1

                    RowLayout {
                        anchors.centerIn: parent
                        spacing: ScaleMetrics.dp(6)

                        Text {
                            text: "✦"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(10)
                            color: "#fbbf24"
                        }
                        Text {
                            text: "INITIALIZE NOW (RAM)"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(9)
                            font.letterSpacing: 0.8
                            color: "#fbbf24"
                        }
                    }

                    MouseArea {
                        id: confirmArea
                        anchors.fill: parent
                        onClicked: {
                            Bridge.initPatch();
                            root.close();
                        }
                    }
                }
            }
        }
    }
}
