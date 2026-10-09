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
    property string subView: "mixer" // "mixer" | "zones"
    property var allParts: Bridge.perfParts
    readonly property bool pushBusy: Bridge.perfPushProgress >= 0

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: ScaleMetrics.dp(10)
        spacing: ScaleMetrics.dp(8)

        // Header: perf name + pager + mode + sync
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(6)

            Text {
                text: "PERFORMANCE"
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
                visible: root.subView === "mixer"
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
            // MIXER | ZONES sub-view toggle
            Rectangle {
                width: ScaleMetrics.dp(104); height: ScaleMetrics.dp(26)
                radius: ScaleMetrics.dp(4)
                color: subMouse.pressed ? Theme.bgCardActive : Theme.bgApp
                border.color: root.subView === "zones" ? Theme.tone1 : Theme.borderCard
                border.width: 1
                Text {
                    anchors.centerIn: parent
                    text: root.subView === "mixer" ? "MIXER  ▶" : "◀  ZONES"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: root.subView === "zones" ? Theme.tone1 : Theme.textSecondary
                }
                MouseArea {
                    id: subMouse
                    anchors.fill: parent
                    onClicked: root.subView = (root.subView === "mixer" ? "zones" : "mixer")
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
            // Sync performance from synth (mixer-only read, never touches editors)
            Rectangle {
                width: ScaleMetrics.dp(92); height: ScaleMetrics.dp(26)
                radius: ScaleMetrics.dp(4)
                color: syncMouse.pressed ? Theme.bgCardActive : Theme.bgSurface
                border.color: syncMouse.pressed ? Theme.tone1 : Theme.borderCard
                border.width: 1
                enabled: !Bridge.syncBusy
                opacity: enabled ? 1.0 : 0.4
                Text {
                    anchors.centerIn: parent
                    text: Bridge.syncBusy ? "⏳ SYNCING..." : "⟳ SYNC PERF"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: Theme.textSecondary
                }
                MouseArea {
                    id: syncMouse
                    anchors.fill: parent
                    enabled: !Bridge.syncBusy
                    onClicked: Bridge.syncPerformanceFromSynth(true)
                }
            }

            // Open Setlist View
            Rectangle {
                width: ScaleMetrics.dp(80); height: ScaleMetrics.dp(26)
                radius: ScaleMetrics.dp(4)
                color: setlistMouse.pressed ? Theme.bgCardActive : Theme.bgSurface
                border.color: "#f59e0b"
                border.width: 1
                RowLayout {
                    anchors.centerIn: parent
                    spacing: ScaleMetrics.dp(4)
                    Text { text: "📋"; font.pixelSize: ScaleMetrics.sp(8); color: "#f59e0b" }
                    Text {
                        text: "SETLIST"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: "#f59e0b"
                    }
                }
                MouseArea {
                    id: setlistMouse
                    anchors.fill: parent
                    onClicked: Bridge.setActiveView("SETLIST")
                }
            }
        }

        // Background part-image push progress (thin bar, controls lock meanwhile)
        Rectangle {
            visible: root.pushBusy
            Layout.fillWidth: true
            Layout.preferredHeight: root.pushBusy ? ScaleMetrics.dp(14) : 0
            height: ScaleMetrics.dp(14)
            radius: ScaleMetrics.dp(7)
            color: "#0f172a"
            border.color: Theme.tone2
            border.width: 1
            Rectangle {
                width: parent.width * Math.max(0, Math.min(1, Bridge.perfPushProgress))
                height: parent.height
                radius: ScaleMetrics.dp(7)
                color: Theme.tone2
            }
            Text {
                anchors.centerIn: parent
                text: "PUSHING PART SOUNDS " + Math.round(Math.max(0, Bridge.perfPushProgress) * 100) + "%"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(7)
                color: "#ffffff"
            }
        }

        // Mixer + permanent FX rail (strips shrink ~15% to fund 160px rail)
        RowLayout {
            visible: root.subView === "mixer"
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: ScaleMetrics.dp(6)
            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: ScaleMetrics.dp(5)
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
                        mfxSelect: _p ? (_p.mfxSelect || 0) : 0
                        feedsEditing: _p ? ((_p.mfxSelect || 0) === (Bridge.editingPerfMfx - 1)) : false
                        partStatus: (Bridge.partFileStatus && Bridge.partFileStatus.length >= partIndex)
                                    ? Bridge.partFileStatus[partIndex - 1] : ""
                    }
                }
            }
            PerfFxRail {
                Layout.preferredWidth: ScaleMetrics.dp(160)
                Layout.maximumWidth: ScaleMetrics.dp(160)
                Layout.fillHeight: true
            }
        }

        // Key-zone editor (same canvas slot as the strips)
        ZoneEditor {
            visible: root.subView === "zones"
            Layout.fillWidth: true
            Layout.fillHeight: true
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
        property string partStatus: ""
        property int mfxSelect: 0
        property bool feedsEditing: false

        radius: ScaleMetrics.dp(6)
        color: chan.isActive ? "#1c1533" : Theme.bgApp
        border.color: chan.isActive ? Theme.tone2 : Theme.borderCard
        border.width: chan.isActive ? 2 : 1

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(5)
            spacing: ScaleMetrics.dp(3)

            // Part Number Badge + file-link health dot
            RowLayout {
                Layout.fillWidth: true
                spacing: ScaleMetrics.dp(4)
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
                // File-link health: green fresh, amber changed, red missing. Tap to re-push.
                Rectangle {
                    visible: chan.partStatus !== ""
                    width: ScaleMetrics.dp(18); height: ScaleMetrics.dp(18)
                    radius: 9
                    color: chan.partStatus === "ok" ? "#10b981"
                         : chan.partStatus === "updated" ? "#fbbf24" : "#ef4444"
                    border.color: "#ffffff"; border.width: 1
                    Text {
                        anchors.centerIn: parent
                        text: chan.partStatus === "ok" ? "✓" : "!"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(9)
                        color: "#000000"
                    }
                    MouseArea {
                        anchors.fill: parent
                        enabled: !root.pushBusy && (chan.partStatus === "updated" || chan.partStatus === "missing")
                        onClicked: Bridge.refreshPartFile(chan.partIndex)
                    }
                }
            }

            // Patch Name (tap to pick a library patch for this part)
            Text {
                Layout.fillWidth: true
                Layout.preferredHeight: ScaleMetrics.dp(22)
                text: chan.partName
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(8)
                font.underline: true
                color: nameMouse.pressed ? Theme.tone1 : Theme.textDim
                elide: Text.ElideRight
                wrapMode: Text.NoWrap
                horizontalAlignment: Text.AlignHCenter
                maximumLineCount: 2
                MouseArea {
                    id: nameMouse
                    anchors.fill: parent
                    enabled: !root.pushBusy
                    onClicked: Bridge.openPartPicker(chan.partIndex)
                }
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
                        enabled: !root.pushBusy
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
                        enabled: !root.pushBusy
                        onClicked: Bridge.setPartSolo(chan.partIndex, !chan.isSolo)
                    }
                }
            }

            // MFX selector: label row + 1/2/3 segmented switch
            // (spacer above separates it from the M/S buttons)
            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: ScaleMetrics.dp(4)
            }
            Text {
                text: "MFX"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(7)
                font.letterSpacing: 1.0
                color: Theme.textDim
                Layout.alignment: Qt.AlignHCenter
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: 1
                Repeater {
                    model: [0, 1, 2]
                    delegate: Rectangle {
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(16)
                        radius: 2
                        color: chan.mfxSelect === modelData ? Theme.tone2 : "#1e293b"
                        border.color: chan.mfxSelect === modelData ? "#ffffff" : Theme.borderCard
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: (modelData + 1)
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(7)
                            color: chan.mfxSelect === modelData ? "#ffffff" : Theme.textDim
                        }
                        MouseArea {
                            anchors.fill: parent
                            enabled: !root.pushBusy
                            onClicked: Bridge.setPartMfxSelect(chan.partIndex, modelData)
                        }
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
                    enabled: !root.pushBusy
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
                    enabled: !root.pushBusy
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
                    enabled: !root.pushBusy
                    onClicked: Bridge.editPerfPart(chan.partIndex)
                }
            }
        }
    }
}
