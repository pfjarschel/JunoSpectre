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

    // 1 = parts 1-8, 2 = parts 9-16: the app's one part/track bank
    readonly property int page: Bridge.seqTrackBank + 1
    property string subView: "mixer" // "mixer" | "zones"
    property var allParts: Bridge.perfParts
    readonly property bool pushBusy: Bridge.perfPushProgress >= 0
    // Parts the selected sequencer track plays/records (main + layers)
    readonly property var recordParts: (Bridge.seqTracks && Bridge.seqTracks.length > Bridge.seqActiveTrack)
                                       ? Bridge.seqTracks[Bridge.seqActiveTrack].targetParts : []

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: ScaleMetrics.dp(10)
        spacing: ScaleMetrics.dp(8)

        // Header: perf name + pager + mode + sync
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(6)

            PageTitle { text: "PERFORMANCE" }
            Text {
                Layout.fillWidth: true
                text: Bridge.perfName
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(11)
                color: Theme.textPrimary
                elide: Text.ElideRight
            }
            // Pager 1-8 / 9-16
            SpButton {
                visible: root.subView === "mixer"
                implicitWidth: ScaleMetrics.dp(76)
                implicitHeight: ScaleMetrics.dp(26)
                icon: root.page === 1 ? "right" : "left"
                iconAfter: root.page === 1
                text: root.page === 1 ? "1–8" : "9–16"
                onClicked: Bridge.seqSetTrackBank(root.page === 1 ? 1 : 0)
            }
            // MIXER | ZONES sub-view toggle
            SpButton {
                implicitWidth: ScaleMetrics.dp(104)
                implicitHeight: ScaleMetrics.dp(26)
                icon: root.subView === "mixer" ? "right" : "left"
                iconAfter: root.subView === "mixer"
                text: root.subView === "mixer" ? "MIXER" : "ZONES"
                fontSize: 8
                checked: root.subView === "zones"
                onClicked: root.subView = (root.subView === "mixer" ? "zones" : "mixer")
            }
            // Mode switch PATCH / PERFORM
            SpButton {
                implicitWidth: ScaleMetrics.dp(86)
                implicitHeight: ScaleMetrics.dp(26)
                icon: Bridge.soundMode === "PERFORM" ? "check" : ""
                text: Bridge.soundMode === "PERFORM" ? "PERFORM" : "GO PERFORM"
                fontSize: 8
                variant: "outline"
                accent: Bridge.soundMode === "PERFORM" ? Theme.catPerform : Theme.catSynth
                checked: Bridge.soundMode === "PERFORM"
                onClicked: Bridge.setSoundMode(Bridge.soundMode === "PERFORM" ? "PATCH" : "PERFORM")
            }
            PageLinks { group: "perform" }
        }

        // Background part-image push progress (thin bar, controls lock meanwhile)
        Rectangle {
            visible: root.pushBusy
            Layout.fillWidth: true
            Layout.preferredHeight: root.pushBusy ? ScaleMetrics.dp(14) : 0
            height: ScaleMetrics.dp(14)
            radius: ScaleMetrics.dp(7)
            color: Theme.bgControl
            border.color: Theme.pageAccent
            border.width: 1
            Rectangle {
                width: parent.width * Math.max(0, Math.min(1, Bridge.perfPushProgress))
                height: parent.height
                radius: ScaleMetrics.dp(7)
                color: Theme.pageAccent
            }
            Text {
                anchors.centerIn: parent
                text: "PUSHING PART SOUNDS " + Math.round(Math.max(0, Bridge.perfPushProgress) * 100) + "%"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(7)
                color: Theme.textPrimary
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
                        kbdOn: _p ? _p.zoneOn : false
                        isActive: Bridge.activePerfPart === partIndex
                        trackColor: root.recordParts.indexOf(partIndex) >= 0
                                    ? Theme.trackColors[Bridge.seqActiveTrack % Theme.trackColors.length]
                                    : "transparent"
                        mfxSelect: _p ? (_p.mfxSelect || 0) : 0
                        feedsEditing: _p ? ((_p.mfxSelect || 0) === (Bridge.editingPerfMfx - 1)) : false
                        partStatus: (Bridge.partFileStatus && Bridge.partFileStatus.length >= partIndex)
                                    ? Bridge.partFileStatus[partIndex - 1] : ""
                        hasFile: _p ? !!_p.hasFile : false
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
        property bool kbdOn: false
        property bool isActive: false
        // Selected sequencer track's color when it plays/records this part
        property color trackColor: "transparent"
        property string partStatus: ""
        property bool hasFile: false
        property int mfxSelect: 0
        property bool feedsEditing: false

        radius: ScaleMetrics.dp(6)
        color: chan.isActive ? Theme.tint(Theme.editingAccent) : Theme.bgApp
        border.color: chan.isActive ? Theme.editingAccent : Theme.borderCard
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
                    color: chan.isActive ? Theme.editingFill : Theme.bgRaised

                    Text {
                        anchors.centerIn: parent
                        text: "P" + chan.partIndex
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(9)
                        color: chan.trackColor.a > 0 ? chan.trackColor
                             : (chan.isActive ? Theme.textPrimary : Theme.textSecondary)
                    }
                    // Tap the badge to edit this part (same as EDIT)
                    MouseArea {
                        anchors.fill: parent
                        enabled: !root.pushBusy
                        onClicked: Bridge.editPerfPart(chan.partIndex)
                    }
                }
                // Sound health: green fresh, amber file changed, red file missing,
                // blue edited (differs from its slot/file). Tap reloads from the file.
                Rectangle {
                    visible: chan.partStatus !== ""
                    width: ScaleMetrics.dp(18); height: ScaleMetrics.dp(18)
                    radius: 9
                    color: chan.partStatus === "ok" ? Theme.playing
                         : chan.partStatus === "updated" ? Theme.warning
                         : chan.partStatus === "edited" ? Theme.modified : Theme.recording
                    border.color: Theme.textPrimary; border.width: 1
                    Icon {
                        anchors.centerIn: parent
                        name: chan.partStatus === "ok" ? "check" : chan.partStatus === "edited" ? "edit" : "warning"
                        size: 11
                        color: Theme.textOnFill
                    }
                    MouseArea {
                        anchors.fill: parent
                        enabled: !root.pushBusy && (chan.partStatus === "updated" || chan.partStatus === "missing"
                                                    || (chan.partStatus === "edited" && chan.hasFile))
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
                color: nameMouse.pressed ? Theme.pageAccent : Theme.textDim
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

                SpButton {
                    Layout.fillWidth: true
                    implicitHeight: ScaleMetrics.dp(16)
                    text: "M"
                    fontSize: 8
                    accent: Theme.recording
                    checked: chan.isMuted
                    enabled: !root.pushBusy
                    onClicked: Bridge.setPartMute(chan.partIndex, !chan.isMuted)
                }

                SpButton {
                    Layout.fillWidth: true
                    implicitHeight: ScaleMetrics.dp(16)
                    text: "S"
                    fontSize: 8
                    accent: Theme.warning
                    checked: chan.isSolo
                    enabled: !root.pushBusy
                    onClicked: Bridge.setPartSolo(chan.partIndex, !chan.isSolo)
                }

                // Kbd switch: the part also sounds from the keyboard
                SpButton {
                    Layout.fillWidth: true
                    implicitHeight: ScaleMetrics.dp(16)
                    text: "KBD"
                    fontSize: 8
                    checked: chan.kbdOn
                    enabled: !root.pushBusy
                    onClicked: Bridge.setPartZoneSwitch(chan.partIndex, !chan.kbdOn)
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
                    delegate: SpButton {
                        Layout.fillWidth: true
                        implicitHeight: ScaleMetrics.dp(16)
                        text: (modelData + 1)
                        fontSize: 8
                        accent: Theme.stageMfx
                        checked: chan.mfxSelect === modelData
                        enabled: !root.pushBusy
                        onClicked: Bridge.setPartMfxSelect(chan.partIndex, modelData)
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
                color: Theme.bgControl
                border.color: Theme.borderCard
                border.width: 1

                TouchHighlight {
                    anchors.fill: parent
                    radius: parent.radius
                    ctlKey: "part.level@" + chan.partIndex
                }

                // Center slot groove
                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    anchors.topMargin: ScaleMetrics.dp(8)
                    anchors.bottomMargin: ScaleMetrics.dp(8)
                    width: ScaleMetrics.dp(4)
                    radius: 2
                    color: Theme.bgRaised
                }

                // Fader Cap (Handle)
                Rectangle {
                    id: faderCap
                    anchors.horizontalCenter: parent.horizontalCenter
                    y: Math.max(0, Math.min(faderTrack.height - height, (1.0 - (chan.volume / 127.0)) * (faderTrack.height - height)))
                    width: faderTrack.width - ScaleMetrics.dp(8)
                    height: ScaleMetrics.dp(22)
                    radius: ScaleMetrics.dp(4)
                    color: faderMouse.containsPress ? Theme.tint(Theme.pageAccent, 0.4) : Theme.bgCardActive
                    border.color: Theme.pageAccent
                    border.width: 1

                    // Cap grip line
                    Rectangle {
                        anchors.centerIn: parent
                        width: parent.width - ScaleMetrics.dp(6)
                        height: ScaleMetrics.dp(2)
                        color: Theme.textPrimary
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
                color: Theme.bgControl
                border.color: Theme.borderCard
                border.width: 1

                TouchHighlight {
                    anchors.fill: parent
                    radius: parent.radius
                    ctlKey: "part.pan@" + chan.partIndex
                }

                // Center tick
                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    width: 1
                    color: Theme.textDim
                }
                // Pan thumb
                Rectangle {
                    x: Math.max(0, Math.min(parent.width - width, (chan.pan / 127.0) * parent.width - width / 2))
                    anchors.verticalCenter: parent.verticalCenter
                    width: ScaleMetrics.dp(10)
                    height: parent.height - ScaleMetrics.dp(4)
                    radius: ScaleMetrics.dp(2)
                    color: panMouse.containsPress ? Theme.tint(Theme.pageAccent, 0.4) : Theme.bgCardActive
                    border.color: Theme.pageAccent
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
            SpButton {
                Layout.fillWidth: true
                implicitHeight: ScaleMetrics.dp(20)
                icon: chan.isActive ? "dotFilled" : ""
                iconSize: 8
                text: chan.isActive ? "EDITING" : "EDIT"
                fontSize: 8
                variant: "outline"
                accent: Theme.editingAccent
                checked: chan.isActive
                enabled: !root.pushBusy
                onClicked: Bridge.editPerfPart(chan.partIndex)
            }
        }
    }
}
