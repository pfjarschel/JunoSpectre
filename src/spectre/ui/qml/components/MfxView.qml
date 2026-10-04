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

    property int activeAlgoIdx: 3 // Tape Echo
    property bool isBypassed: false
    property var algoList: [
        { id: 1, name: "01 EQUALIZER", cat: "FILTER/EQ", p1: "LOW GAIN", v1: 64, p2: "MID GAIN", v2: 68, p3: "MID FREQ", v3: 50, p4: "HIGH GAIN", v4: 64 },
        { id: 4, name: "04 DISTORTION", cat: "DRIVE", p1: "DRIVE", v1: 85, p2: "TYPE", v2: 2, p3: "TONE", v3: 72, p4: "LEVEL", v4: 90 },
        { id: 11, name: "11 PHASER", cat: "MOD", p1: "MODE", v1: 4, p2: "RATE", v2: 45, p3: "DEPTH", v3: 80, p4: "FEEDBACK", v4: 60 },
        { id: 15, name: "15 TAPE ECHO", cat: "DELAY", p1: "TIME", v1: 75, p2: "FEEDBACK", v2: 65, p3: "WOW/FLUTTER", v3: 40, p4: "HF DAMP", v4: 55 },
        { id: 16, name: "16 SPACE-D", cat: "CHORUS", p1: "RATE", v1: 30, p2: "DEPTH", v3: 90, p3: "PHASE", v3: 90, p4: "LEVEL", v4: 100 },
        { id: 25, name: "25 ROTARY", cat: "MOD", p1: "SPEED", v1: 80, p2: "WOOFER", v2: 64, p3: "TWEETER", v3: 70, p4: "TRANSITION", v4: 45 },
        { id: 33, name: "33 SBF-325 FLANGER", cat: "CHORUS", p1: "RATE", v1: 25, p2: "DEPTH", v2: 70, p3: "FEEDBACK", v3: 85, p4: "CROSS FEED", v4: 40 },
        { id: 45, name: "45 STEP PHASER", cat: "MOD", p1: "STEP RATE", v1: 60, p2: "DEPTH", v2: 80, p3: "RESONANCE", v3: 65, p4: "MIX", v4: 90 },
        { id: 56, name: "56 PITCH SHIFTER", cat: "PITCH", p1: "COARSE", v1: 76, p2: "FINE", v2: 64, p3: "FEEDBACK", v3: 30, p4: "BALANCE", v4: 64 },
        { id: 68, name: "68 SLICER", cat: "SPECIAL", p1: "TIMING", v1: 80, p2: "PATTERN", v2: 12, p3: "ATTACK", v3: 40, p4: "RESET", v4: 0 }
    ]

    readonly property var currentAlgo: algoList[activeAlgoIdx]

    RowLayout {
        anchors.fill: parent
        anchors.margins: ScaleMetrics.dp(10)
        spacing: ScaleMetrics.dp(10)

        // Column 1: Algorithm Browser List (~300dp)
        Rectangle {
            Layout.preferredWidth: ScaleMetrics.dp(300)
            Layout.fillHeight: true
            radius: ScaleMetrics.dp(6)
            color: Theme.bgApp
            border.color: Theme.borderCard
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(8)
                spacing: ScaleMetrics.dp(6)

                RowLayout {
                    Layout.fillWidth: true
                    Rectangle {
                        width: ScaleMetrics.dp(8); height: ScaleMetrics.dp(8); radius: 4
                        color: "#ec4899"
                    }
                    Text {
                        text: "MFX ALGORITHM (80 TYPES)"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(10)
                        font.letterSpacing: 1.1
                        color: Theme.textPrimary
                    }
                }

                ListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: root.algoList
                    spacing: ScaleMetrics.dp(3)

                    delegate: Rectangle {
                        width: ListView.view.width
                        height: ScaleMetrics.dp(34)
                        radius: 4
                        color: root.activeAlgoIdx === index ? Theme.bgCardActive : (itemMouse.pressed ? "#161c28" : "#0d1017")
                        border.color: root.activeAlgoIdx === index ? "#ec4899" : Theme.borderCard
                        border.width: root.activeAlgoIdx === index ? 1.5 : 1

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: ScaleMetrics.dp(6)
                            spacing: ScaleMetrics.dp(6)

                            Text {
                                text: modelData.name
                                font.bold: root.activeAlgoIdx === index
                                font.pixelSize: ScaleMetrics.sp(9)
                                color: root.activeAlgoIdx === index ? Theme.textPrimary : Theme.textSecondary
                            }
                            Item { Layout.fillWidth: true }
                            Rectangle {
                                width: ScaleMetrics.dp(48)
                                height: ScaleMetrics.dp(16)
                                radius: 2
                                color: "#10141d"
                                Text {
                                    anchors.centerIn: parent
                                    text: modelData.cat
                                    font.pixelSize: ScaleMetrics.sp(7)
                                    color: "#ec4899"
                                }
                            }
                        }

                        MouseArea {
                            id: itemMouse
                            anchors.fill: parent
                            onClicked: root.activeAlgoIdx = index
                        }
                    }
                }
            }
        }

        // Column 2: Parameters & Signal Flow Console
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: ScaleMetrics.dp(6)
            color: Theme.bgApp
            border.color: Theme.borderCard
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(12)
                spacing: ScaleMetrics.dp(10)

                // Header with Bypass Toggle
                RowLayout {
                    Layout.fillWidth: true
                    ColumnLayout {
                        spacing: 2
                        Text {
                            text: root.currentAlgo.name
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(14)
                            color: "#ec4899"
                        }
                        Text {
                            text: "CATEGORY: " + root.currentAlgo.cat + " • ROLAND MULTI-EFFECTS ENGINE"
                            font.pixelSize: ScaleMetrics.sp(9)
                            color: Theme.textDim
                        }
                    }
                    Item { Layout.fillWidth: true }

                    // Bypass Button
                    Rectangle {
                        width: ScaleMetrics.dp(80)
                        height: ScaleMetrics.dp(30)
                        radius: ScaleMetrics.dp(4)
                        color: root.isBypassed ? "#3f1a1a" : Theme.bgCardActive
                        border.color: root.isBypassed ? Theme.recording : "#ec4899"
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: root.isBypassed ? "BYPASS" : "ACTIVE"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(9)
                            color: root.isBypassed ? Theme.recording : "#ec4899"
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: root.isBypassed = !root.isBypassed
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.borderCard
                }

                // 4 Dynamic Parameter Sliders
                GridLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    columns: 2
                    rowSpacing: ScaleMetrics.dp(10)
                    columnSpacing: ScaleMetrics.dp(10)

                    MfxSlider {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        label: root.currentAlgo.p1
                        val: root.currentAlgo.v1
                        accent: "#ec4899"
                    }

                    MfxSlider {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        label: root.currentAlgo.p2
                        val: root.currentAlgo.v2
                        accent: "#ec4899"
                    }

                    MfxSlider {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        label: root.currentAlgo.p3
                        val: root.currentAlgo.v3
                        accent: "#ec4899"
                    }

                    MfxSlider {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        label: root.currentAlgo.p4
                        val: root.currentAlgo.v4
                        accent: "#ec4899"
                    }
                }

                // Routing & Send Row
                RowLayout {
                    Layout.fillWidth: true
                    spacing: ScaleMetrics.dp(8)

                    Text {
                        text: "ROUTING:"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Theme.textDim
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(26)
                        radius: 3
                        color: "#10141d"
                        border.color: Theme.borderCard
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: "TONES 1-4 ➔ [MFX PROCESSOR] ➔ CHORUS / REVERB SENDS"
                            font.family: Theme.fontMono
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: Theme.textSecondary
                        }
                    }
                }
            }
        }
    }

    component MfxSlider: Rectangle {
        id: ms
        property string label: "PARAM"
        property int val: 64
        property color accent: Theme.primary

        radius: ScaleMetrics.dp(4)
        color: "#10141d"
        border.color: Theme.borderCard
        border.width: 1

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(8)
            spacing: ScaleMetrics.dp(4)

            RowLayout {
                Layout.fillWidth: true
                Text { text: ms.label; font.bold: true; font.pixelSize: ScaleMetrics.sp(9); color: Theme.textPrimary }
                Item { Layout.fillWidth: true }
                Text { text: ms.val.toString(); font.family: Theme.fontMono; font.bold: true; font.pixelSize: ScaleMetrics.sp(10); color: ms.accent }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 3
                color: "#0a0d14"
                border.color: Theme.borderCard
                border.width: 1

                Rectangle {
                    x: 0; y: 0
                    width: parent.width * (ms.val / 127.0)
                    height: parent.height
                    radius: 3
                    color: Qt.rgba(ms.accent.r, ms.accent.g, ms.accent.b, 0.4)
                }

                MouseArea {
                    anchors.fill: parent
                    onPositionChanged: (mouse) => {
                        if (pressed) ms.val = Math.max(0, Math.min(127, Math.round((mouse.x / width) * 127)));
                    }
                    onPressed: (mouse) => {
                        ms.val = Math.max(0, Math.min(127, Math.round((mouse.x / width) * 127)));
                    }
                }
            }
        }
    }
}
