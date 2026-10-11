pragma ValueTypeBehavior: Copy
import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

// Hardware page: the synth connection (port, identity ping, reconnect) and
// the MIDI ports seen on this machine. Ports are rescanned every 2 s; a
// synth that appears while offline is attached automatically.
Rectangle {
    id: root
    color: Theme.bgCard
    radius: ScaleMetrics.dp(8)
    border.color: Theme.borderCard
    border.width: 1

    property bool connected: Bridge.synthConnected
    property var ports: Bridge.midiPorts
    property var ctlPorts: Bridge.controllerPorts

    function ctlState(key) {
        for (var i = 0; i < ctlPorts.length; i++)
            if (ctlPorts[i].key === key) return ctlPorts[i]
        return null
    }
    property bool busy: Bridge.jobBusy
    property bool hwJob: busy && (Bridge.jobName === "connect" || Bridge.jobName === "ping")

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: ScaleMetrics.dp(10)
        spacing: ScaleMetrics.dp(8)

        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(8)
            Rectangle {
                width: ScaleMetrics.dp(8); height: ScaleMetrics.dp(8); radius: 4
                color: "#94a3b8"
            }
            Text {
                text: "HARDWARE"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(12)
                font.letterSpacing: 1.2
                color: Theme.textPrimary
            }
            Item { Layout.fillWidth: true }
            Text {
                text: "PORTS RESCAN EVERY 2 S"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(9)
                color: Theme.textDim
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: ScaleMetrics.dp(10)

            // Synth
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
                        Text { text: "ROLAND JUNO-DS / XPS-30"; font.bold: true; font.pixelSize: ScaleMetrics.sp(10); color: Theme.tone1 }
                        Item { Layout.fillWidth: true }
                        Rectangle {
                            height: ScaleMetrics.dp(20)
                            implicitWidth: ScaleMetrics.dp(90)
                            radius: 3
                            color: root.connected ? "#064e3b" : "#451a1a"
                            border.color: root.connected ? "#10b981" : Theme.recording
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: root.connected ? "● CONNECTED" : "○ OFFLINE"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(7)
                                color: root.connected ? "#6ee7b7" : "#fca5a5"
                            }
                        }
                    }

                    InfoRow { label: "PORT"; value: Bridge.synthPort || "—" }
                    InfoRow { label: "IDENTITY"; value: Bridge.synthIdentity || "—" }
                    InfoRow {
                        label: "LAST PING"
                        value: root.hwJob ? Bridge.jobText : (Bridge.pingText || "—")
                        valueColor: (Bridge.pingText.indexOf("OK") === 0 || root.hwJob) ? Theme.tone1 : Theme.recording
                    }

                    Text { text: "SYNTH PORT"; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textDim }
                    Flow {
                        Layout.fillWidth: true
                        spacing: ScaleMetrics.dp(4)
                        Chip {
                            text: "AUTO"
                            active: Bridge.synthPortPref === ""
                            onClicked: Bridge.setSynthPort("")
                        }
                        Repeater {
                            model: root.ports
                            delegate: Chip {
                                required property var modelData
                                visible: modelData.input && modelData.output
                                text: modelData.key.split(":").pop()
                                active: Bridge.synthPortPref === modelData.key
                                onClicked: Bridge.setSynthPort(modelData.key)
                            }
                        }
                    }
                    Text {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: "AUTO picks the JUNO-DS / XPS-30 USB port (MIDI 1). Pick another port to reach the synth through a MIDI interface."
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Theme.textDim
                    }

                    Item { Layout.fillHeight: true }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: ScaleMetrics.dp(6)
                        ActionButton {
                            text: "PING"
                            accent: Theme.tone1
                            enabled: !root.busy && root.connected
                            onClicked: Bridge.pingSynth()
                        }
                        ActionButton {
                            text: "RECONNECT"
                            accent: Theme.tone1
                            enabled: !root.busy
                            onClicked: Bridge.reconnectSynth()
                        }
                    }
                }
            }

            // MIDI ports (controllers come here)
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

                    Text { text: "MIDI PORTS"; font.bold: true; font.pixelSize: ScaleMetrics.sp(10); color: Theme.tone2 }
                    Text {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: "Inputs marked CONTROLLER are listened to for MIDI Control bindings (MIDI Learn page). FEEDBACK sends each bound knob its target's value, so endless knobs follow patch changes."
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Theme.textDim
                    }

                    ListView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 4
                        model: root.ports
                        delegate: Rectangle {
                            id: portRow
                            required property var modelData
                            property var ctl: root.ctlState(modelData.key)
                            width: ListView.view.width
                            height: ScaleMetrics.dp(32)
                            radius: 4
                            color: "#10141d"
                            border.color: modelData.synth ? Theme.tone1 : Theme.borderCard
                            border.width: 1
                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: ScaleMetrics.dp(6)
                                spacing: 6
                                Text {
                                    Layout.fillWidth: true
                                    text: portRow.modelData.key
                                    elide: Text.ElideRight
                                    font.bold: true
                                    font.pixelSize: ScaleMetrics.sp(9)
                                    color: Theme.textPrimary
                                }
                                Tag { visible: portRow.modelData.synth; text: "SYNTH"; tint: Theme.tone1 }
                                Rectangle {
                                    visible: portRow.ctl !== null && portRow.ctl.enabled
                                    implicitWidth: fbLabel.implicitWidth + ScaleMetrics.dp(14)
                                    implicitHeight: ScaleMetrics.dp(22)
                                    radius: 3
                                    color: "transparent"
                                    border.color: portRow.ctl && portRow.ctl.feedback ? Theme.tone2 : Theme.borderCard
                                    border.width: 1
                                    Text {
                                        id: fbLabel
                                        anchors.centerIn: parent
                                        text: portRow.ctl && portRow.ctl.feedback ? "FEEDBACK" : "NO FEEDBACK"
                                        font.bold: true
                                        font.pixelSize: ScaleMetrics.sp(7)
                                        color: portRow.ctl && portRow.ctl.feedback ? Theme.tone2 : Theme.textDim
                                    }
                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: Bridge.setControllerFeedback(portRow.modelData.key, !portRow.ctl.feedback)
                                    }
                                }
                                Rectangle {
                                    visible: portRow.ctl !== null
                                    implicitWidth: ctlLabel.implicitWidth + ScaleMetrics.dp(14)
                                    implicitHeight: ScaleMetrics.dp(22)
                                    radius: 3
                                    color: portRow.ctl && portRow.ctl.enabled ? "#2a1f08" : "transparent"
                                    border.color: portRow.ctl && portRow.ctl.enabled ? Theme.warning : Theme.borderCard
                                    border.width: 1
                                    Text {
                                        id: ctlLabel
                                        anchors.centerIn: parent
                                        text: portRow.ctl && portRow.ctl.enabled ? (portRow.ctl.open ? "CONTROLLER ●" : "CONTROLLER") : "CONTROLLER OFF"
                                        font.bold: true
                                        font.pixelSize: ScaleMetrics.sp(7)
                                        color: portRow.ctl && portRow.ctl.enabled ? Theme.warning : Theme.textDim
                                    }
                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: Bridge.setControllerPortEnabled(portRow.modelData.key, !portRow.ctl.enabled)
                                    }
                                }
                                Tag { visible: portRow.modelData.input; text: "IN"; tint: Theme.textSecondary }
                                Tag { visible: portRow.modelData.output; text: "OUT"; tint: Theme.textSecondary }
                            }
                        }
                        Text {
                            anchors.centerIn: parent
                            visible: root.ports.length === 0
                            text: "No MIDI ports found"
                            font.pixelSize: ScaleMetrics.sp(9)
                            color: Theme.textDim
                        }
                    }

                    ActionButton {
                        Layout.fillWidth: true
                        text: "SEND ALL NOTES OFF (PANIC)"
                        accent: Theme.recording
                        onClicked: Bridge.panic()
                    }
                }
            }
        }
    }

    component InfoRow: Rectangle {
        id: ir
        property string label: ""
        property string value: ""
        property color valueColor: Theme.tone1
        Layout.fillWidth: true
        height: ScaleMetrics.dp(30)
        radius: 4
        color: "#10141d"
        border.color: Theme.borderCard
        border.width: 1
        RowLayout {
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(6)
            spacing: ScaleMetrics.dp(8)
            Text { text: ir.label; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textDim }
            Text {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignRight
                elide: Text.ElideLeft
                text: ir.value
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(9)
                color: ir.valueColor
            }
        }
    }

    component Chip: Rectangle {
        id: chip
        property string text: ""
        property bool active: false
        signal clicked()
        width: chipLabel.implicitWidth + ScaleMetrics.dp(16)
        height: ScaleMetrics.dp(26)
        radius: 3
        color: active ? Theme.bgCardActive : "#10141d"
        border.color: active ? Theme.tone1 : Theme.borderCard
        border.width: 1
        opacity: root.busy ? 0.5 : 1.0
        Text {
            id: chipLabel
            anchors.centerIn: parent
            text: chip.text
            font.bold: true
            font.pixelSize: ScaleMetrics.sp(8)
            color: chip.active ? Theme.tone1 : Theme.textSecondary
        }
        MouseArea { anchors.fill: parent; enabled: !root.busy; onClicked: chip.clicked() }
    }

    component Tag: Rectangle {
        id: tag
        property string text: ""
        property color tint: Theme.textSecondary
        implicitWidth: tagLabel.implicitWidth + ScaleMetrics.dp(10)
        implicitHeight: ScaleMetrics.dp(18)
        radius: 3
        color: "transparent"
        border.color: tint
        border.width: 1
        Text {
            id: tagLabel
            anchors.centerIn: parent
            text: tag.text
            font.bold: true
            font.pixelSize: ScaleMetrics.sp(7)
            color: tag.tint
        }
    }

    component ActionButton: Rectangle {
        id: ab
        property string text: ""
        property color accent: Theme.tone1
        signal clicked()
        Layout.fillWidth: true
        height: ScaleMetrics.dp(32)
        radius: ScaleMetrics.dp(4)
        color: abMouse.pressed ? Theme.bgCardActive : "#10141d"
        border.color: ab.accent
        border.width: 1
        opacity: enabled ? 1.0 : 0.4
        Text {
            anchors.centerIn: parent
            text: ab.text
            font.bold: true
            font.pixelSize: ScaleMetrics.sp(9)
            color: ab.accent
        }
        MouseArea {
            id: abMouse
            anchors.fill: parent
            enabled: ab.enabled
            onClicked: ab.clicked()
        }
    }
}
