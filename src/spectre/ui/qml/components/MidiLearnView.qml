pragma ValueTypeBehavior: Copy
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

    property bool isLearning: false
    property var mappings: [
        { param: "VECTOR X MORPH", cc: 16, ch: 1, min: 0, max: 127, target: "ENGINE" },
        { param: "VECTOR Y MORPH", cc: 17, ch: 1, min: 0, max: 127, target: "ENGINE" },
        { param: "MASTER CUTOFF", cc: 74, ch: 1, min: 0, max: 127, target: "FILTER" },
        { param: "MASTER RESONANCE", cc: 71, ch: 1, min: 0, max: 127, target: "FILTER" },
        { param: "AMP ATTACK TIME", cc: 73, ch: 1, min: 0, max: 127, target: "AMP" },
        { param: "AMP RELEASE TIME", cc: 72, ch: 1, min: 0, max: 127, target: "AMP" },
        { param: "MACRO KNOB 1", cc: 20, ch: 1, min: 0, max: 127, target: "MACRO" },
        { param: "MACRO KNOB 2", cc: 21, ch: 1, min: 0, max: 127, target: "MACRO" },
        { param: "PORTAMENTO TIME", cc: 5, ch: 1, min: 0, max: 127, target: "GLIDE" }
    ]

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: ScaleMetrics.dp(10)
        spacing: ScaleMetrics.dp(8)

        // Header
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(8)

            Rectangle {
                width: ScaleMetrics.dp(8); height: ScaleMetrics.dp(8); radius: 4
                color: "#f59e0b"
            }
            Text {
                text: "MIDI LEARN & CC SURFACE MAPPING"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(12)
                font.letterSpacing: 1.2
                color: Theme.textPrimary
            }
            Item { Layout.fillWidth: true }

            // Learn Mode Toggle
            Rectangle {
                height: ScaleMetrics.dp(28)
                implicitWidth: ScaleMetrics.dp(140)
                radius: 4
                color: root.isLearning ? "#451a1a" : Theme.bgCardActive
                border.color: root.isLearning ? Theme.recording : "#f59e0b"
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: 6
                    Rectangle {
                        width: 8; height: 8; radius: 4
                        color: root.isLearning ? Theme.recording : "#f59e0b"
                    }
                    Text {
                        text: root.isLearning ? "WAITING FOR CC..." : "ENTER LEARN MODE"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: root.isLearning ? Theme.recording : "#f59e0b"
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: root.isLearning = !root.isLearning
                }
            }
        }

        // Mappings Table
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: ScaleMetrics.dp(6)
            color: Theme.bgApp
            border.color: Theme.borderCard
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(8)
                spacing: ScaleMetrics.dp(4)

                // Table Header
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "PARAMETER"; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textDim; Layout.preferredWidth: ScaleMetrics.dp(200) }
                    Text { text: "TARGET"; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textDim; Layout.preferredWidth: ScaleMetrics.dp(100) }
                    Text { text: "CC #"; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textDim; Layout.preferredWidth: ScaleMetrics.dp(80) }
                    Text { text: "CH"; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textDim; Layout.preferredWidth: ScaleMetrics.dp(60) }
                    Text { text: "RANGE (MIN..MAX)"; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textDim; Layout.fillWidth: true }
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderCard }

                ListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: root.mappings
                    spacing: 2

                    delegate: Rectangle {
                        width: ListView.view.width
                        height: ScaleMetrics.dp(28)
                        radius: 3
                        color: index % 2 === 0 ? "#0a0d14" : "#10141d"

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 4; anchors.rightMargin: 4
                            Text {
                                text: modelData.param
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(8)
                                color: Theme.textPrimary
                                Layout.preferredWidth: ScaleMetrics.dp(200)
                            }
                            Text {
                                text: modelData.target
                                font.pixelSize: ScaleMetrics.sp(8)
                                color: "#f59e0b"
                                Layout.preferredWidth: ScaleMetrics.dp(100)
                            }
                            Text {
                                text: "CC " + modelData.cc
                                font.family: Theme.fontMono
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(8)
                                color: Theme.tone1
                                Layout.preferredWidth: ScaleMetrics.dp(80)
                            }
                            Text {
                                text: "CH " + modelData.ch
                                font.family: Theme.fontMono
                                font.pixelSize: ScaleMetrics.sp(8)
                                color: Theme.textDim
                                Layout.preferredWidth: ScaleMetrics.dp(60)
                            }
                            Text {
                                text: modelData.min + " .. " + modelData.max
                                font.family: Theme.fontMono
                                font.pixelSize: ScaleMetrics.sp(8)
                                color: Theme.textDim
                                Layout.fillWidth: true
                            }
                        }
                    }
                }
            }
        }
    }
}
