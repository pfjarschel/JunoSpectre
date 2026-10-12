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
                color: Theme.textSecondary
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
                        Text { text: "ROLAND JUNO-DS / XPS-30"; font.bold: true; font.pixelSize: ScaleMetrics.sp(10); color: Theme.pageAccent }
                        Item { Layout.fillWidth: true }
                        Rectangle {
                            height: ScaleMetrics.dp(20)
                            implicitWidth: ScaleMetrics.dp(90)
                            radius: 3
                            color: Theme.tint(root.connected ? Theme.playing : Theme.recording, 0.25)
                            border.color: root.connected ? Theme.playing : Theme.recording
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: root.connected ? "CONNECTED" : "OFFLINE"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(7)
                                color: root.connected ? Theme.playing : Theme.recording
                            }
                        }
                    }

                    InfoRow { label: "PORT"; value: Bridge.synthPort || "—" }
                    InfoRow { label: "IDENTITY"; value: Bridge.synthIdentity || "—" }
                    InfoRow {
                        label: "LAST PING"
                        value: root.hwJob ? Bridge.jobText : (Bridge.pingText || "—")
                        valueColor: (Bridge.pingText.indexOf("OK") === 0 || root.hwJob) ? Theme.pageAccent : Theme.recording
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

                    Text { text: "FOLLOW THE JUNO PANEL"; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textDim }
                    Flow {
                        Layout.fillWidth: true
                        spacing: ScaleMetrics.dp(4)
                        Chip { text: "ON"; active: Bridge.followPanel; onClicked: Bridge.setFollowPanel(true) }
                        Chip { text: "OFF"; active: !Bridge.followPanel; onClicked: Bridge.setFollowPanel(false) }
                    }
                    Text {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: "Performances and patches picked on the Juno load into the app. To follow edits made on the Juno too, set SYSTEM > MIDI > Transmit Edit Data to ON there."
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Theme.textDim
                    }

                    Item { Layout.fillHeight: true }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: ScaleMetrics.dp(6)
                        ActionButton {
                            text: "PING"
                            accent: Theme.pageAccent
                            enabled: !root.busy && root.connected
                            onClicked: Bridge.pingSynth()
                        }
                        ActionButton {
                            text: "RECONNECT"
                            accent: Theme.pageAccent
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

                    Text { text: "MIDI PORTS"; font.bold: true; font.pixelSize: ScaleMetrics.sp(10); color: Theme.pageAccent }
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
                            color: Theme.bgControl
                            border.color: modelData.synth ? Theme.pageAccent : Theme.borderCard
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
                                Tag { visible: portRow.modelData.synth; text: "SYNTH"; tint: Theme.pageAccent }
                                SpButton {
                                    visible: portRow.ctl !== null && portRow.ctl.enabled
                                    implicitWidth: label.implicitWidth + ScaleMetrics.dp(14)
                                    implicitHeight: ScaleMetrics.dp(22)
                                    text: portRow.ctl && portRow.ctl.feedback ? "FEEDBACK" : "NO FEEDBACK"
                                    fontSize: 8
                                    checked: portRow.ctl && portRow.ctl.feedback
                                    onClicked: Bridge.setControllerFeedback(portRow.modelData.key, !portRow.ctl.feedback)
                                }
                                SpButton {
                                    visible: portRow.ctl !== null
                                    implicitHeight: ScaleMetrics.dp(22)
                                    compact: true
                                    icon: portRow.ctl && portRow.ctl.enabled && portRow.ctl.open ? "dotFilled" : ""
                                    iconSize: 8
                                    text: portRow.ctl && portRow.ctl.enabled ? "CONTROLLER" : "CONTROLLER OFF"
                                    fontSize: 8
                                    checked: portRow.ctl && portRow.ctl.enabled
                                    onClicked: Bridge.setControllerPortEnabled(portRow.modelData.key, !portRow.ctl.enabled)
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
        property color valueColor: Theme.pageAccent
        Layout.fillWidth: true
        height: ScaleMetrics.dp(30)
        radius: 4
        color: Theme.bgControl
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

    component Chip: SpButton {
        property bool active: false
        checked: active
        compact: true
        enabled: !root.busy
        implicitHeight: ScaleMetrics.dp(26)
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

    component ActionButton: SpButton {
        variant: "outline"
        Layout.fillWidth: true
        implicitHeight: ScaleMetrics.dp(32)
    }
}
