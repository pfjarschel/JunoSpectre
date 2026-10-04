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

    property bool isPlaying: false
    property int currentStep: 0
    property int arpStyle: 0
    property var arpStyles: ["UP", "DOWN", "UP & DOWN", "RANDOM", "NOTE ORDER"]
    property int arpOctave: 2
    property var pattern: [true, false, false, true, true, false, true, false, true, false, false, true, false, true, true, false]

    Timer {
        interval: 125 // 120 BPM 16th notes
        running: root.isPlaying
        repeat: true
        onTriggered: root.currentStep = (root.currentStep + 1) % 16
    }

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
                color: "#10b981"
            }
            Text {
                text: "PATTERN SEQUENCER & ARPEGGIATOR"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(12)
                font.letterSpacing: 1.2
                color: Theme.textPrimary
            }
            Item { Layout.fillWidth: true }

            // Play / Stop Button
            Rectangle {
                height: ScaleMetrics.dp(28)
                implicitWidth: ScaleMetrics.dp(100)
                radius: 4
                color: root.isPlaying ? "#064e3b" : Theme.bgCardActive
                border.color: "#10b981"
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: 4
                    Text { text: root.isPlaying ? "■" : "▶"; font.pixelSize: ScaleMetrics.sp(10); color: "#10b981" }
                    Text { text: root.isPlaying ? "STOP" : "RUN SEQ"; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: "#10b981" }
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: root.isPlaying = !root.isPlaying
                }
            }
        }

        // Toolbar: Arp Settings
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(6)

            Text { text: "ARP STYLE:"; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textDim }
            Repeater {
                model: root.arpStyles
                delegate: Rectangle {
                    Layout.fillWidth: true
                    height: ScaleMetrics.dp(22)
                    radius: 3
                    color: root.arpStyle === index ? Theme.bgCardActive : "#10141d"
                    border.color: root.arpStyle === index ? "#10b981" : Theme.borderCard
                    border.width: 1
                    Text {
                        anchors.centerIn: parent
                        text: modelData
                        font.bold: root.arpStyle === index
                        font.pixelSize: ScaleMetrics.sp(7)
                        color: root.arpStyle === index ? "#10b981" : Theme.textDim
                    }
                    MouseArea { anchors.fill: parent; onClicked: root.arpStyle = index }
                }
            }

            Rectangle { width: 1; height: ScaleMetrics.dp(20); color: Theme.borderCard }

            Text { text: "OCTAVE: " + root.arpOctave; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: Theme.tone1 }
            Rectangle {
                width: ScaleMetrics.dp(40)
                height: ScaleMetrics.dp(22)
                radius: 3
                color: "#10141d"
                border.color: Theme.borderCard
                border.width: 1
                Text { anchors.centerIn: parent; text: "1-4"; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textDim }
                MouseArea {
                    anchors.fill: parent
                    onClicked: root.arpOctave = (root.arpOctave % 4) + 1
                }
            }
        }

        // 16-Step Trigger Grid
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: ScaleMetrics.dp(6)
            color: Theme.bgApp
            border.color: Theme.borderCard
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(10)
                spacing: ScaleMetrics.dp(8)

                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "16-STEP TRIGGER MATRIX"; font.bold: true; font.pixelSize: ScaleMetrics.sp(9); color: Theme.textDim }
                    Item { Layout.fillWidth: true }
                    Text { text: "STEP: " + (root.currentStep + 1) + " / 16"; font.family: Theme.fontMono; font.bold: true; font.pixelSize: ScaleMetrics.sp(9); color: "#10b981" }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: ScaleMetrics.dp(4)

                    Repeater {
                        model: 16
                        delegate: Rectangle {
                            id: stepBox
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: ScaleMetrics.dp(4)
                            color: root.currentStep === index ? (root.pattern[index] ? "#10b981" : "#1e293b") : (root.pattern[index] ? "#047857" : "#0d1017")
                            border.color: root.currentStep === index ? "#ffffff" : Theme.borderCard
                            border.width: root.currentStep === index ? 2 : 1

                            ColumnLayout {
                                anchors.centerIn: parent
                                spacing: 4
                                Text {
                                    Layout.alignment: Qt.AlignHCenter
                                    text: (index + 1).toString()
                                    font.family: Theme.fontMono
                                    font.bold: true
                                    font.pixelSize: ScaleMetrics.sp(8)
                                    color: root.pattern[index] ? "#ffffff" : Theme.textDim
                                }
                                Rectangle {
                                    Layout.alignment: Qt.AlignHCenter
                                    width: ScaleMetrics.dp(8)
                                    height: ScaleMetrics.dp(8)
                                    radius: 4
                                    color: root.pattern[index] ? "#ffffff" : "transparent"
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    var arr = root.pattern.slice();
                                    arr[index] = !arr[index];
                                    root.pattern = arr;
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
