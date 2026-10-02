import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

Rectangle {
    id: root
    color: Theme.bgCard
    radius: ScaleMetrics.dp(8)
    border.color: Theme.borderCard
    border.width: 1

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: ScaleMetrics.dp(12)
        spacing: ScaleMetrics.dp(10)

        // Header Title
        RowLayout {
            Layout.fillWidth: true
            Text {
                text: "EFFECTS (MFX) STUDIO"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(13)
                font.letterSpacing: 1.2
                color: Theme.textSecondary
            }
            Item { Layout.fillWidth: true }
            Text {
                text: "ROLAND SIGNAL FLOW ARCHITECTURE"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(10)
                color: Theme.textDim
            }
        }

        // Signal Flow Blocks
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: ScaleMetrics.dp(8)

            // Block 1: Tone Generator Source
            EffectBlock {
                Layout.preferredWidth: ScaleMetrics.dp(120)
                Layout.fillHeight: true
                title: "SOURCE"
                subTitle: "4 TONES"
                accentColor: Theme.tone1
                isSource: true
            }

            // Arrow
            SignalArrow {}

            // Block 2: MFX Multi-Effects Processor
            EffectBlock {
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: "MFX PROCESSOR"
                subTitle: "TYPE: 15 TAPE ECHO"
                accentColor: "#ec4899"
                param1Name: "FEEDBACK"
                param1Val: 65
                param2Name: "TIME"
                param2Val: 80
            }

            // Arrow
            SignalArrow {}

            // Block 3: Chorus / Flanger
            EffectBlock {
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: "CHORUS"
                subTitle: "STEREO CHORUS"
                accentColor: "#38bdf8"
                param1Name: "RATE"
                param1Val: 40
                param2Name: "DEPTH"
                param2Val: 75
            }

            // Arrow
            SignalArrow {}

            // Block 4: Reverb
            EffectBlock {
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: "REVERB"
                subTitle: "HALL 1"
                accentColor: "#a855f7"
                param1Name: "TIME"
                param1Val: 85
                param2Name: "LEVEL"
                param2Val: 60
            }
        }
    }

    // Connecting Signal Arrow
    component SignalArrow: Item {
        width: ScaleMetrics.dp(16)
        Layout.fillHeight: true

        Text {
            anchors.centerIn: parent
            text: "▶"
            font.pixelSize: ScaleMetrics.sp(14)
            color: Theme.borderCard
        }
    }

    // Effect Unit Block Component
    component EffectBlock: Rectangle {
        id: block
        property string title: "EFFECT"
        property string subTitle: "SUB"
        property color accentColor: Theme.primary
        property bool isSource: false
        property string param1Name: "P1"
        property int param1Val: 50
        property string param2Name: "P2"
        property int param2Val: 50
        property bool isBypassed: false

        radius: ScaleMetrics.dp(6)
        color: Theme.bgApp
        border.color: isBypassed ? Theme.borderCard : accentColor
        border.width: 1

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(8)
            spacing: ScaleMetrics.dp(6)

            // Header
            RowLayout {
                Layout.fillWidth: true
                Rectangle {
                    width: ScaleMetrics.dp(8)
                    height: ScaleMetrics.dp(8)
                    radius: 4
                    color: block.isBypassed ? Theme.textDim : block.accentColor
                }
                Text {
                    Layout.fillWidth: true
                    text: block.title
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(10)
                    color: block.isBypassed ? Theme.textDim : Theme.textPrimary
                    elide: Text.ElideRight
                }
            }

            Text {
                text: block.subTitle
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(9)
                color: block.accentColor
            }

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: Theme.borderCard
            }

            // Parameters
            ColumnLayout {
                visible: !block.isSource
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: ScaleMetrics.dp(6)

                RowLayout {
                    Layout.fillWidth: true
                    Text { text: block.param1Name; font.pixelSize: ScaleMetrics.sp(9); color: Theme.textDim; Layout.fillWidth: true }
                    Text { text: block.param1Val.toString(); font.pixelSize: ScaleMetrics.sp(9); font.family: Theme.fontMono; color: Theme.textPrimary }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Text { text: block.param2Name; font.pixelSize: ScaleMetrics.sp(9); color: Theme.textDim; Layout.fillWidth: true }
                    Text { text: block.param2Val.toString(); font.pixelSize: ScaleMetrics.sp(9); font.family: Theme.fontMono; color: Theme.textPrimary }
                }

                Item { Layout.fillHeight: true }

                // Bypass Toggle Button
                Rectangle {
                    Layout.fillWidth: true
                    height: ScaleMetrics.dp(22)
                    radius: ScaleMetrics.dp(4)
                    color: block.isBypassed ? "#3f1a1a" : Theme.bgCardActive
                    border.color: block.isBypassed ? Theme.recording : block.accentColor
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: block.isBypassed ? "BYPASS" : "ACTIVE"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(9)
                        color: block.isBypassed ? Theme.recording : block.accentColor
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: block.isBypassed = !block.isBypassed
                    }
                }
            }

            Item {
                visible: block.isSource
                Layout.fillHeight: true
            }
        }
    }
}
