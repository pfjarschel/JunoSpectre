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
                text: "PERFORMANCE MIXER (PARTS 1 - 8)"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(13)
                font.letterSpacing: 1.2
                color: Theme.textSecondary
            }
            Item { Layout.fillWidth: true }
            Text {
                text: "ROLAND 16-PART MULTI-TIMBRAL ENGINE"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(10)
                color: Theme.textDim
            }
        }

        // 8 Channel Strips Row
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: ScaleMetrics.dp(8)

            Repeater {
                model: 8
                delegate: ChannelStrip {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    partIndex: modelData + 1
                    partName: modelData === 0 ? "Grand Pno" : modelData === 1 ? "Warm Strings" : modelData === 2 ? "Synth Bass" : "Part " + (modelData + 1)
                }
            }
        }
    }

    // Performance Channel Strip Component
    component ChannelStrip: Rectangle {
        id: chan
        property int partIndex: 1
        property string partName: "Part 1"
        property int volume: partIndex === 1 ? 110 : partIndex === 2 ? 85 : 0
        property bool isMuted: false
        property bool isSolo: false

        radius: ScaleMetrics.dp(6)
        color: Theme.bgApp
        border.color: Theme.borderCard
        border.width: 1

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(6)
            spacing: ScaleMetrics.dp(4)

            // Part Number Badge
            Rectangle {
                Layout.fillWidth: true
                height: ScaleMetrics.dp(20)
                radius: ScaleMetrics.dp(4)
                color: chan.partIndex === 1 ? Theme.bgCardActive : "#1e293b"

                Text {
                    anchors.centerIn: parent
                    text: "P" + chan.partIndex
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(9)
                    color: chan.partIndex === 1 ? Theme.tone1 : Theme.textSecondary
                }
            }

            // Patch Name
            Text {
                Layout.fillWidth: true
                text: chan.partName
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(9)
                color: Theme.textDim
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter
            }

            // Mute / Solo Buttons
            RowLayout {
                Layout.fillWidth: true
                spacing: ScaleMetrics.dp(2)

                Rectangle {
                    Layout.fillWidth: true
                    height: ScaleMetrics.dp(16)
                    radius: ScaleMetrics.dp(3)
                    color: chan.isMuted ? Theme.recording : "#1e293b"

                    Text {
                        anchors.centerIn: parent
                        text: "M"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: chan.isMuted ? "#ffffff" : Theme.textDim
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: chan.isMuted = !chan.isMuted
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: ScaleMetrics.dp(16)
                    radius: ScaleMetrics.dp(3)
                    color: chan.isSolo ? Theme.tone3 : "#1e293b"

                    Text {
                        anchors.centerIn: parent
                        text: "S"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: chan.isSolo ? "#ffffff" : Theme.textDim
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: chan.isSolo = !chan.isSolo
                    }
                }
            }

            // Vertical Fader Track
            Rectangle {
                id: faderTrack
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: ScaleMetrics.dp(4)
                color: "#0f172a"
                border.color: Theme.borderCard
                border.width: 1

                // Center slot groove
                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    anchors.topMargin: ScaleMetrics.dp(8)
                    anchors.bottomMargin: ScaleMetrics.dp(8)
                    width: ScaleMetrics.dp(4)
                    radius: 2
                    color: "#1e293b"
                }

                // Fader Cap (Handle)
                Rectangle {
                    id: faderCap
                    anchors.horizontalCenter: parent.horizontalCenter
                    y: Math.max(0, Math.min(faderTrack.height - height, (1.0 - (chan.volume / 127.0)) * (faderTrack.height - height)))
                    width: faderTrack.width - ScaleMetrics.dp(8)
                    height: ScaleMetrics.dp(24)
                    radius: ScaleMetrics.dp(4)
                    color: faderMouse.containsPress ? Theme.tone2 : Theme.bgCardActive
                    border.color: Theme.tone2
                    border.width: 1

                    // Cap grip line
                    Rectangle {
                        anchors.centerIn: parent
                        width: parent.width - ScaleMetrics.dp(6)
                        height: ScaleMetrics.dp(2)
                        color: "#ffffff"
                    }
                }

                MouseArea {
                    id: faderMouse
                    anchors.fill: parent
                    onPositionChanged: (mouse) => {
                        if (pressed) {
                            const norm = Math.max(0.0, Math.min(1.0, 1.0 - (mouse.y / height)));
                            chan.volume = Math.round(norm * 127);
                        }
                    }
                }
            }

            // Numeric volume level
            Text {
                text: chan.volume.toString()
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(10)
                font.family: Theme.fontMono
                color: chan.volume > 0 ? Theme.textPrimary : Theme.textDim
                Layout.alignment: Qt.AlignHCenter
            }
        }
    }
}
