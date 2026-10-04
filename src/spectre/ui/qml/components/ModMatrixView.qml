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

    property var sources: [
        "CC01 MOD WHEEL", "CC02 BREATH", "CC04 FOOT", "CC11 EXPRESSION",
        "PITCH BEND", "AFTERTOUCH", "VELOCITY", "KEYFOLLOW", "LFO 1", "LFO 2", "STEP LFO"
    ]
    property var destinations: [
        "OFF", "PITCH", "TVF CUTOFF", "TVF RESO", "TVA LEVEL", "PAN",
        "LFO1 RATE", "LFO1 P-DEP", "LFO1 F-DEP", "LFO2 RATE", "LFO2 P-DEP"
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
                color: "#38bdf8"
            }
            Text {
                text: "MODULATION MATRIX (4 MATRIX CONTROLLERS)"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(12)
                font.letterSpacing: 1.2
                color: Theme.textPrimary
            }
            Item { Layout.fillWidth: true }
            Text {
                text: "ROLAND PATCH MATRIX ROUTING"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(9)
                color: Theme.textDim
            }
        }

        // 4 Matrix Controller Columns
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: ScaleMetrics.dp(8)

            Repeater {
                model: [
                    { id: 1, name: "MATRIX CTRL 1", defaultSrc: 0, accent: "#38bdf8" },
                    { id: 2, name: "MATRIX CTRL 2", defaultSrc: 4, accent: "#818cf8" },
                    { id: 3, name: "MATRIX CTRL 3", defaultSrc: 6, accent: "#10b981" },
                    { id: 4, name: "MATRIX CTRL 4", defaultSrc: 8, accent: "#fbbf24" }
                ]

                delegate: Rectangle {
                    id: ctrlCol
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: ScaleMetrics.dp(6)
                    color: Theme.bgApp
                    border.color: Theme.borderCard
                    border.width: 1

                    property color accentColor: modelData.accent
                    property int srcIdx: modelData.defaultSrc
                    property var destIndices: [1, 2, 0, 0]
                    property var sensValues: [30, -25, 0, 0]

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: ScaleMetrics.dp(8)
                        spacing: ScaleMetrics.dp(6)

                        // Ctrl Header
                        RowLayout {
                            Layout.fillWidth: true
                            Rectangle {
                                width: ScaleMetrics.dp(6); height: ScaleMetrics.dp(6); radius: 3
                                color: ctrlCol.accentColor
                            }
                            Text {
                                text: modelData.name
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(10)
                                color: ctrlCol.accentColor
                            }
                        }

                        // Source Selector Box
                        Rectangle {
                            Layout.fillWidth: true
                            height: ScaleMetrics.dp(36)
                            radius: ScaleMetrics.dp(4)
                            color: "#10141d"
                            border.color: ctrlCol.accentColor
                            border.width: 1

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: ScaleMetrics.dp(4)
                                spacing: 1
                                Text {
                                    text: "SOURCE"
                                    font.bold: true
                                    font.pixelSize: ScaleMetrics.sp(7)
                                    color: Theme.textDim
                                }
                                Text {
                                    text: root.sources[ctrlCol.srcIdx]
                                    font.bold: true
                                    font.pixelSize: ScaleMetrics.sp(9)
                                    color: Theme.textPrimary
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: ctrlCol.srcIdx = (ctrlCol.srcIdx + 1) % root.sources.length
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 1
                            color: Theme.borderCard
                        }

                        // 4 Destinations
                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            spacing: ScaleMetrics.dp(4)

                            Repeater {
                                model: 4
                                delegate: Rectangle {
                                    id: slotBox
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    radius: ScaleMetrics.dp(4)
                                    color: "#0a0d14"
                                    border.color: Theme.borderCard
                                    border.width: 1

                                    property int slotIdx: index
                                    property int dIdx: ctrlCol.destIndices[slotIdx]
                                    property int sens: ctrlCol.sensValues[slotIdx]

                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: ScaleMetrics.dp(4)
                                        spacing: 2

                                        // Dest picker
                                        RowLayout {
                                            Layout.fillWidth: true
                                            Text {
                                                text: "DEST " + (slotBox.slotIdx + 1) + ":"
                                                font.bold: true
                                                font.pixelSize: ScaleMetrics.sp(8)
                                                color: Theme.textDim
                                            }
                                            Text {
                                                Layout.fillWidth: true
                                                text: root.destinations[slotBox.dIdx]
                                                font.bold: true
                                                font.pixelSize: ScaleMetrics.sp(8)
                                                color: slotBox.dIdx === 0 ? Theme.textDim : ctrlCol.accentColor
                                                elide: Text.ElideRight
                                            }
                                        }

                                        MouseArea {
                                            Layout.fillWidth: true
                                            height: ScaleMetrics.dp(16)
                                            onClicked: {
                                                var arr = ctrlCol.destIndices.slice();
                                                arr[slotBox.slotIdx] = (arr[slotBox.slotIdx] + 1) % root.destinations.length;
                                                ctrlCol.destIndices = arr;
                                            }
                                        }

                                        // Bipolar Sensitivity Slider (-63..+63)
                                        Rectangle {
                                            Layout.fillWidth: true
                                            height: ScaleMetrics.dp(20)
                                            radius: 3
                                            color: "#10141d"
                                            border.color: Theme.borderCard
                                            border.width: 1

                                            // Center line
                                            Rectangle {
                                                anchors.horizontalCenter: parent.horizontalCenter
                                                width: 1; height: parent.height
                                                color: Theme.borderCard
                                            }

                                            // Fill
                                            Rectangle {
                                                property real norm: (slotBox.sens + 63) / 126.0
                                                x: norm >= 0.5 ? parent.width * 0.5 : parent.width * norm
                                                width: Math.abs(parent.width * (norm - 0.5))
                                                height: parent.height
                                                color: Qt.rgba(ctrlCol.accentColor.r, ctrlCol.accentColor.g, ctrlCol.accentColor.b, 0.4)
                                            }

                                            Text {
                                                anchors.centerIn: parent
                                                text: "SENS: " + (slotBox.sens > 0 ? "+" + slotBox.sens : slotBox.sens.toString())
                                                font.family: Theme.fontMono
                                                font.bold: true
                                                font.pixelSize: ScaleMetrics.sp(7)
                                                color: Theme.textPrimary
                                            }

                                            MouseArea {
                                                anchors.fill: parent
                                                onPositionChanged: (mouse) => {
                                                    if (pressed) {
                                                        var val = Math.round((mouse.x / width) * 126 - 63);
                                                        var arr = ctrlCol.sensValues.slice();
                                                        arr[slotBox.slotIdx] = Math.max(-63, Math.min(63, val));
                                                        ctrlCol.sensValues = arr;
                                                    }
                                                }
                                                onPressed: (mouse) => {
                                                    var val = Math.round((mouse.x / width) * 126 - 63);
                                                    var arr = ctrlCol.sensValues.slice();
                                                    arr[slotBox.slotIdx] = Math.max(-63, Math.min(63, val));
                                                    ctrlCol.sensValues = arr;
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
