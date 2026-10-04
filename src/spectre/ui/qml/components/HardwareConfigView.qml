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

    property string midiInPort: "JUNO-DS MIDI 1"
    property string midiOutPort: "JUNO-DS MIDI 1"
    property int deviceId: 16
    property int sysexDelayMs: 15
    property bool localControl: false
    property string clockSource: "INTERNAL (120 BPM)"
    property bool isHardwarePinged: true

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
                color: "#94a3b8"
            }
            Text {
                text: "HARDWARE CONFIGURATION (JUNO-DS & CONTROLLERS)"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(12)
                font.letterSpacing: 1.2
                color: Theme.textPrimary
            }
            Item { Layout.fillWidth: true }
            Text {
                text: "DEVICE MIDI & USB INTERFACE"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(9)
                color: Theme.textDim
            }
        }

        // 2 Columns: Roland Juno Hardware & External Controllers
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: ScaleMetrics.dp(10)

            // Column 1: Roland Synth Device
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
                    spacing: ScaleMetrics.dp(8)

                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "ROLAND JUNO-DS / XPS-30 HARDWARE"; font.bold: true; font.pixelSize: ScaleMetrics.sp(10); color: Theme.tone1 }
                        Item { Layout.fillWidth: true }
                        // Status badge
                        Rectangle {
                            height: ScaleMetrics.dp(20)
                            implicitWidth: ScaleMetrics.dp(90)
                            radius: 3
                            color: root.isHardwarePinged ? "#064e3b" : "#451a1a"
                            border.color: root.isHardwarePinged ? "#10b981" : Theme.recording
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: root.isHardwarePinged ? "● CONNECTED" : "○ OFFLINE"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(7)
                                color: root.isHardwarePinged ? "#6ee7b7" : "#fca5a5"
                            }
                        }
                    }

                    // Port selectors
                    SettingRow { label: "MIDI IN PORT"; value: root.midiInPort; onClicked: root.midiInPort = (root.midiInPort === "JUNO-DS MIDI 1" ? "USB MIDI IN" : "JUNO-DS MIDI 1") }
                    SettingRow { label: "MIDI OUT PORT"; value: root.midiOutPort; onClicked: root.midiOutPort = (root.midiOutPort === "JUNO-DS MIDI 1" ? "USB MIDI OUT" : "JUNO-DS MIDI 1") }
                    SettingRow { label: "DEVICE ID (SYSEX)"; value: root.deviceId.toString() + " (0x10 Default)"; onClicked: root.deviceId = (root.deviceId === 16 ? 17 : 16) }

                    // Local Control Toggle
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "LOCAL CONTROL"; font.bold: true; font.pixelSize: ScaleMetrics.sp(9); color: Theme.textPrimary }
                        Item { Layout.fillWidth: true }
                        Rectangle {
                            width: ScaleMetrics.dp(70)
                            height: ScaleMetrics.dp(24)
                            radius: 3
                            color: root.localControl ? Theme.bgCardActive : "#10141d"
                            border.color: root.localControl ? Theme.tone1 : Theme.borderCard
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: root.localControl ? "ON (LOCAL)" : "OFF (MIDI)"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(8)
                                color: root.localControl ? Theme.tone1 : Theme.textDim
                            }
                            MouseArea { anchors.fill: parent; onClicked: root.localControl = !root.localControl }
                        }
                    }

                    // SysEx Delay Slider
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "SYSEX PACKET THROTTLING"; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textDim }
                            Item { Layout.fillWidth: true }
                            Text { text: root.sysexDelayMs.toString() + " ms"; font.family: Theme.fontMono; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textPrimary }
                        }
                        Rectangle {
                            Layout.fillWidth: true
                            height: ScaleMetrics.dp(20)
                            radius: 3
                            color: "#10141d"
                            border.color: Theme.borderCard
                            border.width: 1
                            Rectangle {
                                width: parent.width * ((root.sysexDelayMs - 5) / 45.0)
                                height: parent.height
                                radius: 3
                                color: Qt.rgba(0.22, 0.74, 0.97, 0.35)
                            }
                            MouseArea {
                                anchors.fill: parent
                                onPositionChanged: (mouse) => {
                                    if (pressed) root.sysexDelayMs = Math.max(5, Math.min(50, Math.round(5 + (mouse.x / width) * 45)));
                                }
                                onPressed: (mouse) => {
                                    root.sysexDelayMs = Math.max(5, Math.min(50, Math.round(5 + (mouse.x / width) * 45)));
                                }
                            }
                        }
                    }

                    Item { Layout.fillHeight: true }

                    // Ping Button
                    Rectangle {
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(32)
                        radius: ScaleMetrics.dp(4)
                        color: pingMouse.pressed ? Theme.bgCardActive : "#10141d"
                        border.color: Theme.tone1
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: "PING HARDWARE / SYSEX IDENTITY REQUEST"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(9)
                            color: Theme.tone1
                        }
                        MouseArea {
                            id: pingMouse
                            anchors.fill: parent
                            onClicked: {
                                root.isHardwarePinged = true;
                            }
                        }
                    }
                }
            }

            // Column 2: External USB MIDI Controllers & Clock
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
                    spacing: ScaleMetrics.dp(8)

                    Text { text: "CONNECTED MIDI CONTROLLERS & SURFACES"; font.bold: true; font.pixelSize: ScaleMetrics.sp(10); color: Theme.tone2 }

                    // List of USB controllers
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        Repeater {
                            model: [
                                { name: "KORG nanoKONTROL2", status: "Active (Ch 1)", icon: "🎛" },
                                { name: "Novation Launchkey Mini MK3", status: "Active (Ch 1)", icon: "🎹" },
                                { name: "Roland USB MIDI Interface", status: "Active (Ch 1)", icon: "🔌" }
                            ]
                            delegate: Rectangle {
                                Layout.fillWidth: true
                                height: ScaleMetrics.dp(32)
                                radius: 4
                                color: "#10141d"
                                border.color: Theme.borderCard
                                border.width: 1
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: ScaleMetrics.dp(6)
                                    spacing: 6
                                    Text { text: modelData.icon; font.pixelSize: ScaleMetrics.sp(12) }
                                    Text { text: modelData.name; font.bold: true; font.pixelSize: ScaleMetrics.sp(9); color: Theme.textPrimary }
                                    Item { Layout.fillWidth: true }
                                    Text { text: modelData.status; font.pixelSize: ScaleMetrics.sp(8); color: "#10b981" }
                                }
                            }
                        }
                    }

                    SettingRow {
                        label: "CLOCK SYNC SOURCE"
                        value: root.clockSource
                        onClicked: {
                            if (root.clockSource.startsWith("INTERNAL")) root.clockSource = "USB MIDI CLOCK";
                            else if (root.clockSource.startsWith("USB")) root.clockSource = "MIDI DIN CLOCK";
                            else root.clockSource = "INTERNAL (120 BPM)";
                        }
                    }

                    Item { Layout.fillHeight: true }

                    // Panic Button
                    Rectangle {
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(32)
                        radius: ScaleMetrics.dp(4)
                        color: panicMouse.pressed ? "#451a1a" : "#10141d"
                        border.color: Theme.recording
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: "SEND ALL NOTES OFF (PANIC)"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(9)
                            color: Theme.recording
                        }
                        MouseArea {
                            id: panicMouse
                            anchors.fill: parent
                            onClicked: Bridge.panic()
                        }
                    }
                }
            }
        }
    }

    component SettingRow: Rectangle {
        id: sr
        property string label: "SETTING"
        property string value: "VALUE"
        signal clicked()

        Layout.fillWidth: true
        height: ScaleMetrics.dp(32)
        radius: 4
        color: "#10141d"
        border.color: Theme.borderCard
        border.width: 1

        RowLayout {
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(6)
            Text { text: sr.label; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textDim }
            Item { Layout.fillWidth: true }
            Text { text: sr.value; font.bold: true; font.pixelSize: ScaleMetrics.sp(9); color: Theme.tone1 }
            Text { text: "▼"; font.pixelSize: ScaleMetrics.sp(7); color: Theme.textDim }
        }

        MouseArea {
            anchors.fill: parent
            onClicked: sr.clicked()
        }
    }
}
