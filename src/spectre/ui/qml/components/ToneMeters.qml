import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

Rectangle {
    id: root
    width: ScaleMetrics.dp(195)
    color: Theme.bgCard
    radius: ScaleMetrics.dp(8)
    border.color: Theme.borderCard
    border.width: 1

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: ScaleMetrics.dp(10)
        anchors.rightMargin: ScaleMetrics.dp(10)
        anchors.topMargin: ScaleMetrics.dp(10)
        anchors.bottomMargin: ScaleMetrics.dp(10)
        spacing: ScaleMetrics.dp(6)

        Text {
            text: "TONE LEVELS"
            font.bold: true
            font.pixelSize: ScaleMetrics.sp(11)
            font.letterSpacing: 1.2
            color: Theme.textSecondary
            Layout.alignment: Qt.AlignHCenter
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: ScaleMetrics.dp(8)

            // Tone 1 (NW)
            ToneBar {
                toneNumber: 1
                toneName: "T1 (NW)"
                toneColor: Theme.tone1
                level: Bridge.tone1Level
            }

            // Tone 2 (NE)
            ToneBar {
                toneNumber: 2
                toneName: "T2 (NE)"
                toneColor: Theme.tone2
                level: Bridge.tone2Level
            }

            // Tone 3 (SW)
            ToneBar {
                toneNumber: 3
                toneName: "T3 (SW)"
                toneColor: Theme.tone3
                level: Bridge.tone3Level
            }

            // Tone 4 (SE)
            ToneBar {
                toneNumber: 4
                toneName: "T4 (SE)"
                toneColor: Theme.tone4
                level: Bridge.tone4Level
            }
        }
    }

    // Component for single vertical tone meter
    component ToneBar: ColumnLayout {
        id: barRoot
        property int toneNumber: 1
        property string toneName: "T1"
        property color toneColor: Theme.tone1
        property int level: 0

        Layout.fillWidth: true
        Layout.fillHeight: true
        spacing: ScaleMetrics.dp(4)

        // Numeric level readout
        Text {
            text: barRoot.level
            font.bold: true
            font.pixelSize: ScaleMetrics.sp(11)
            font.family: Theme.fontMono
            color: barRoot.level > 0 ? barRoot.toneColor : Theme.textDim
            Layout.alignment: Qt.AlignHCenter
        }

        // Meter Track Background
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: ScaleMetrics.dp(4)
            color: Theme.bgApp
            border.color: Theme.borderCard
            border.width: 1
            clip: true

            // Meter Fill Bar (animates height)
            Rectangle {
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                height: Math.max(0, (parent.height * barRoot.level) / 127)
                radius: ScaleMetrics.dp(3)
                color: barRoot.toneColor

                Behavior on height {
                    NumberAnimation { duration: 50; easing.type: Easing.OutQuad }
                }

                // Subtle inner glow
                Rectangle {
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    height: ScaleMetrics.dp(4)
                    color: "#ffffff"
                    opacity: barRoot.level > 0 ? 0.35 : 0.0
                }
            }
        }

        // Tone Label Badge
        Text {
            text: barRoot.toneName
            font.bold: true
            font.pixelSize: ScaleMetrics.sp(9)
            color: barRoot.toneColor
            Layout.alignment: Qt.AlignHCenter
        }
    }
}
