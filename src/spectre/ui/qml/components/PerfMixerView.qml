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

    property int page: 1 // 1 = parts 1-8, 2 = parts 9-16
    property var allParts: Bridge.perfParts

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: ScaleMetrics.dp(10)
        spacing: ScaleMetrics.dp(8)

        // Header: perf name + pager + mode + sync
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(6)

            Text {
                text: "PERF MIXER"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(12)
                font.letterSpacing: 1.2
                color: Theme.textSecondary
            }
            Text {
                Layout.fillWidth: true
                text: Bridge.perfName
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(11)
                color: Theme.textPrimary
                elide: Text.ElideRight
            }
            // Pager 1-8 / 9-16
            Rectangle {
                width: ScaleMetrics.dp(76); height: ScaleMetrics.dp(26)
                radius: ScaleMetrics.dp(4)
                color: pageMouse.pressed ? Theme.bgCardActive : Theme.bgApp
                border.color: Theme.borderCard; border.width: 1
                Text {
                    anchors.centerIn: parent
                    text: root.page === 1 ? "1–8  ▶" : "◀  9–16"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(9)
                    color: Theme.textSecondary
                }
                MouseArea {
                    id: pageMouse
                    anchors.fill: parent
                    onClicked: root.page = (root.page === 1 ? 2 : 1)
                }
            }
            // Mode switch PATCH / PERFORM
            Rectangle {
                width: ScaleMetrics.dp(86); height: ScaleMetrics.dp(26)
                radius: ScaleMetrics.dp(4)
                color: Bridge.soundMode === "PERFORM" ? "#2d1b4e" : "#1e293b"
                border.color: Bridge.soundMode === "PERFORM" ? Theme.tone2 : Theme.primary
                border.width: 1
                Text {
                    anchors.centerIn: parent
                    text: Bridge.soundMode === "PERFORM" ? "PERFORM ✓" : "GO PERFORM"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: Bridge.soundMode === "PERFORM" ? Theme.tone2 : Theme.primary
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: Bridge.setSoundMode(Bridge.soundMode === "PERFORM" ? "PATCH" : "PERFORM")
                }
            }
            // Sync performance from synth
            Rectangle {
                width: ScaleMetrics.dp(64); height: ScaleMetrics.dp(26)
                radius: ScaleMetrics.dp(4)
                color: syncMouse.pressed ? Theme.bgCardActive : Theme.bgSurface
                border.color: syncMouse.pressed ? Theme.tone1 : Theme.borderCard
                border.width: 1
                Text {
                    anchors.centerIn: parent
                    text: "⟳ SYNC"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: Theme.textSecondary
                }
                MouseArea {
                    id: syncMouse
                    anchors.fill: parent
                    onClicked: Bridge.syncPerformanceFromSynth()
                }
            }
        }

        // Live setlist strip (songs = performance snapshots, tap or ◀/▶)
        PlaylistStrip {
            Layout.fillWidth: true
            Layout.preferredHeight: ScaleMetrics.dp(84)
        }

        // 8 Channel Strips Row (paged over 16 parts)
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: ScaleMetrics.dp(6)
            Repeater {
                model: 8
                delegate: ChannelStrip {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    property var _p: (root.allParts && root.allParts.length > ((root.page - 1) * 8 + index))
                                     ? root.allParts[(root.page - 1) * 8 + index]
                                     : null
                    partIndex: _p ? _p.index : ((root.page - 1) * 8 + index + 1)
                    partName: _p ? (_p.name || ("Part " + partIndex)) : ("Part " + partIndex)
                    volume: _p ? _p.volume : 0
                    pan: _p ? _p.pan : 64
                    isMuted: _p ? _p.muted : false
                    isSolo: _p ? _p.solo : false
                    isActive: Bridge.activePerfPart === partIndex
                }
            }
        }
    }

    // Performance Channel Strip Component
    component ChannelStrip: Rectangle {
        id: chan
        property int partIndex: 1
        property string partName: "Part 1"
        property int volume: 100
        property int pan: 64
        property bool isMuted: false
        property bool isSolo: false
        property bool isActive: false

        radius: ScaleMetrics.dp(6)
        color: chan.isActive ? "#1c1533" : Theme.bgApp
        border.color: chan.isActive ? Theme.tone2 : Theme.borderCard
        border.width: chan.isActive ? 2 : 1

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(5)
            spacing: ScaleMetrics.dp(3)

            // Part Number Badge
            Rectangle {
                Layout.fillWidth: true
                height: ScaleMetrics.dp(18)
                radius: ScaleMetrics.dp(4)
                color: chan.isActive ? Theme.tone2 : (chan.partIndex <= 2 ? Theme.bgCardActive : "#1e293b")

                Text {
                    anchors.centerIn: parent
                    text: "P" + chan.partIndex
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(9)
                    color: chan.isActive ? "#ffffff" : (chan.partIndex === 1 ? Theme.tone1 : Theme.textSecondary)
                }
            }

            // Patch Name
            Text {
                Layout.fillWidth: true
                Layout.preferredHeight: ScaleMetrics.dp(22)
                text: chan.partName
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(8)
                color: Theme.textDim
                elide: Text.ElideRight
                wrapMode: Text.NoWrap
                horizontalAlignment: Text.AlignHCenter
                maximumLineCount: 2
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
                        onClicked: Bridge.setPartMute(chan.partIndex, !chan.isMuted)
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
                        onClicked: Bridge.setPartSolo(chan.partIndex, !chan.isSolo)
                    }
                }
            }

            // Vertical Fader Track
            Rectangle {
                id: faderTrack
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: ScaleMetrics.dp(60)
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
                    height: ScaleMetrics.dp(22)
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
                    function updateVol(my) {
                        const norm = Math.max(0.0, Math.min(1.0, 1.0 - (my / height)));
                        Bridge.setPartVolume(chan.partIndex, Math.round(norm * 127));
                    }
                    onPressed: (mouse) => updateVol(mouse.y)
                    onPositionChanged: (mouse) => {
                        if (pressed) updateVol(mouse.y);
                    }
                }
            }

            // Numeric volume level
            Text {
                text: chan.volume.toString()
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(9)
                font.family: Theme.fontMono
                color: chan.volume > 0 ? Theme.textPrimary : Theme.textDim
                Layout.alignment: Qt.AlignHCenter
            }

            // Pan mini-slider (L64..63R, 64=center)
            Rectangle {
                Layout.fillWidth: true
                height: ScaleMetrics.dp(16)
                radius: ScaleMetrics.dp(3)
                color: "#0f172a"
                border.color: Theme.borderCard
                border.width: 1

                // Center tick
                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    width: 1
                    color: "#475569"
                }
                // Pan thumb
                Rectangle {
                    x: Math.max(0, Math.min(parent.width - width, (chan.pan / 127.0) * parent.width - width / 2))
                    anchors.verticalCenter: parent.verticalCenter
                    width: ScaleMetrics.dp(10)
                    height: parent.height - ScaleMetrics.dp(4)
                    radius: ScaleMetrics.dp(2)
                    color: panMouse.containsPress ? Theme.tone1 : Theme.bgCardActive
                    border.color: Theme.tone1
                    border.width: 1
                }
                Text {
                    anchors.centerIn: parent
                    text: "PAN"
                    font.pixelSize: ScaleMetrics.sp(6)
                    color: Theme.textDim
                }
                MouseArea {
                    id: panMouse
                    anchors.fill: parent
                    function updatePan(mx) {
                        const norm = Math.max(0.0, Math.min(1.0, mx / width));
                        Bridge.setPartPan(chan.partIndex, Math.round(norm * 127));
                    }
                    onPressed: (mouse) => updatePan(mouse.x)
                    onPositionChanged: (mouse) => {
                        if (pressed) updatePan(mouse.x);
                    }
                }
            }

            // EDIT button: target this part in patch editors
            Rectangle {
                Layout.fillWidth: true
                height: ScaleMetrics.dp(20)
                radius: ScaleMetrics.dp(4)
                color: chan.isActive ? Theme.tone2 : Theme.bgSurface
                border.color: chan.isActive ? "#ffffff" : Theme.tone2
                border.width: 1
                Text {
                    anchors.centerIn: parent
                    text: chan.isActive ? "● EDITING" : "EDIT"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: chan.isActive ? "#ffffff" : Theme.tone2
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: Bridge.editPerfPart(chan.partIndex)
                }
            }
        }
    }
}
