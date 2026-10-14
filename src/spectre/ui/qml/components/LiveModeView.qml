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

    readonly property var trackColors: Theme.trackColors
    // Read once per change; every track column uses it (each Bridge read
    // rebuilds and converts all 16 parts)
    readonly property var perfParts: Bridge.perfParts
    readonly property var seqTracks: Bridge.seqTracks || []
    // MOTION shows the 8 automation lanes instead of the note tracks
    // (shares the sequencer page's mode)
    readonly property bool motion: Bridge.seqMotionMode
    readonly property var lanes: Bridge.seqAutomationLanes || []
    // Track headers and the scene column's STOP ALL share this height (keeps rows aligned)
    readonly property real trackHeaderHeight: ScaleMetrics.dp(40)

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: ScaleMetrics.dp(10)
        spacing: ScaleMetrics.dp(8)

        // =====================================================================
        // 1. TOP TRANSPORT & SESSION CONTROLS
        // =====================================================================
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(8)

            Rectangle {
                width: ScaleMetrics.dp(8)
                height: ScaleMetrics.dp(8)
                radius: 4
                color: Bridge.seqIsPlaying ? Theme.playing : Theme.pageAccent
            }

            Text {
                text: "LIVE SESSION MATRIX"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(12)
                font.letterSpacing: 1.2
                color: Theme.textPrimary
            }

            // Note tracks or automation lanes
            Row {
                spacing: ScaleMetrics.dp(3)
                Repeater {
                    model: [ { label: "NOTES", motion: false }, { label: "MOTION", motion: true } ]
                    delegate: SpButton {
                        implicitHeight: ScaleMetrics.dp(28)
                        implicitWidth: ScaleMetrics.dp(64)
                        text: modelData.label
                        fontSize: 8
                        checked: root.motion === modelData.motion
                        onClicked: Bridge.seqSetMotionMode(modelData.motion)
                    }
                }
            }

            Item { Layout.fillWidth: true }

            // Keyboard plays a different part than the active track sends to
            KbdPartHint { suppressed: root.motion }

            // Track bank: the grid shows tracks 1-8 or 9-16
            RowLayout {
                visible: !root.motion
                spacing: ScaleMetrics.dp(3)
                Text {
                    text: "TRACKS"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: Theme.textDim
                }
                Repeater {
                    model: 2
                    delegate: SpButton {
                        implicitHeight: ScaleMetrics.dp(28)
                        implicitWidth: ScaleMetrics.dp(40)
                        text: index === 0 ? "1-8" : "9-16"
                        fontSize: 8
                        checked: Bridge.seqTrackBank === index
                        onClicked: Bridge.seqSetTrackBank(index)
                    }
                }
            }

            // Realign: every N bars all tracks restart from step 1 together
            // (pulls polymetric / triplet tracks back in line)
            Rectangle {
                height: ScaleMetrics.dp(28)
                width: ScaleMetrics.dp(112)
                radius: 4
                color: Theme.bgApp
                border.color: Theme.borderCard
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: ScaleMetrics.dp(4)
                    Text {
                        text: "REALIGN"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Theme.textDim
                    }
                    Text {
                        text: Bridge.seqMasterResync === 0 ? "OFF" : (Bridge.seqMasterResync + " BAR")
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(9)
                        color: Bridge.seqMasterResync > 0 ? Theme.pageAccent : Theme.textSecondary
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        const options = [0, 1, 2, 4, 8, 16, 32];
                        const curr = Bridge.seqMasterResync;
                        const idx = options.indexOf(curr);
                        const next = options[(idx + 1) % options.length];
                        Bridge.seqSetMasterResync(next);
                    }
                }
            }

            // Switch to Sequencer
            Rectangle {
                height: ScaleMetrics.dp(28)
                width: ScaleMetrics.dp(100)
                radius: 4
                color: Theme.bgApp
                border.color: Theme.pageAccent
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: ScaleMetrics.dp(4)
                    Icon { name: "screen.seq"; size: 12; color: Theme.pageAccent }
                    Text {
                        text: "SEQUENCER"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Theme.pageAccent
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: Bridge.setActiveView("SEQUENCER")
                }
            }

            // Switch to Setlist
            Rectangle {
                height: ScaleMetrics.dp(28)
                width: ScaleMetrics.dp(75)
                radius: 4
                color: Theme.bgApp
                border.color: Theme.pageAccent
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: ScaleMetrics.dp(4)
                    Icon { name: "screen.setlist"; size: 12; color: Theme.pageAccent }
                    Text {
                        text: "SETLIST"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Theme.pageAccent
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: Bridge.setActiveView("SETLIST")
                }
            }
        }

        // =====================================================================
        // 2. SESSION MATRIX: THE SHOWN BANK'S 8 TRACKS + SCENE LAUNCH COLUMN
        // The scene column copies a track column's header height, margins and
        // spacing so each scene button lines up with its row of clips.
        // =====================================================================
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: ScaleMetrics.dp(6)
            color: Theme.bgApp
            border.color: Theme.borderCard
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(6)
                spacing: ScaleMetrics.dp(4)

                Repeater {
                    model: root.motion ? 0 : 8
                    delegate: TrackColumn {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1  // equal columns whatever the names
                        Layout.fillHeight: true
                        trackIdx: Bridge.seqTrackBank * 8 + index
                    }
                }

                Repeater {
                    model: root.motion ? root.lanes.length : 0
                    delegate: LaneColumn {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        Layout.fillHeight: true
                        laneIdx: index
                    }
                }

                // Scene Launch Column
                Rectangle {
                    Layout.preferredWidth: ScaleMetrics.dp(62)
                    Layout.fillHeight: true
                    radius: ScaleMetrics.dp(4)
                    color: Theme.bgCard
                    border.color: Theme.borderCard
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: ScaleMetrics.dp(4)
                        spacing: ScaleMetrics.dp(3)

                        // Stop All Tracks (in the header row)
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: root.trackHeaderHeight
                            radius: ScaleMetrics.dp(3)
                            color: stopAllMouse.pressed ? Theme.tint(Theme.recording, 0.35) : Theme.bgSurface
                            border.color: stopAllMouse.containsPress ? Theme.recording : Theme.borderCard
                            border.width: 1

                            Column {
                                anchors.centerIn: parent
                                spacing: 1
                                Row {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    spacing: ScaleMetrics.dp(3)
                                    Icon {
                                        anchors.verticalCenter: parent.verticalCenter
                                        name: "stop"
                                        size: 11
                                        color: Theme.recording
                                    }
                                    Text {
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: "STOP"
                                        font.bold: true
                                        font.pixelSize: ScaleMetrics.sp(8)
                                        color: Theme.recording
                                    }
                                }
                                Text {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    text: "ALL"
                                    font.bold: true
                                    font.pixelSize: ScaleMetrics.sp(8)
                                    color: Theme.recording
                                }
                            }

                            MouseArea {
                                id: stopAllMouse
                                anchors.fill: parent
                                onClicked: {
                                    if (root.motion) {
                                        for (let i = 0; i < root.lanes.length; i++)
                                            Bridge.seqStopLane(i);   // linked lanes follow their tracks
                                        return;
                                    }
                                    const n = root.seqTracks.length;
                                    for (let i = 0; i < n; i++)
                                        Bridge.seqStopTrack(i);
                                }
                            }
                        }

                        // 8 Scene Launch Buttons, one per clip row
                        Repeater {
                            model: 8
                            delegate: Rectangle {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                Layout.preferredHeight: 1
                                radius: ScaleMetrics.dp(4)
                                color: sceneMouse.pressed ? Theme.tint(Theme.playing, 0.35) : Theme.bgSurface
                                border.color: sceneMouse.containsPress ? Theme.playing : Theme.borderCard
                                border.width: 1

                                RowLayout {
                                    anchors.centerIn: parent
                                    spacing: ScaleMetrics.dp(4)
                                    Icon {
                                        name: "play"
                                        size: 12
                                        color: Theme.playing
                                    }
                                    Text {
                                        text: "S" + (index + 1)
                                        font.bold: true
                                        font.pixelSize: ScaleMetrics.sp(9)
                                        color: Theme.textPrimary
                                    }
                                }

                                MouseArea {
                                    id: sceneMouse
                                    anchors.fill: parent
                                    onClicked: Bridge.seqLaunchScene(index)
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // =========================================================================
    // Track Column Component (2-row Header + 8 Clip Slots)
    // =========================================================================
    component TrackColumn: Rectangle {
        id: colRoot
        property int trackIdx: 0
        readonly property var trackData: root.seqTracks.length > trackIdx ? root.seqTracks[trackIdx] : null
        readonly property int currentPlayhead: (Bridge.seqPlayheads && Bridge.seqPlayheads.length > trackIdx)
                                               ? Bridge.seqPlayheads[trackIdx] : 0
        readonly property color trackColor: root.trackColors[trackIdx % root.trackColors.length]
        readonly property int mainPart: (trackData && trackData.targetPart) ? trackData.targetPart : (trackIdx + 1)
        readonly property int layerCount: (trackData && trackData.layerParts) ? trackData.layerParts.length : 0
        readonly property bool isAudio: trackData ? trackData.kind === "audio" : false
        readonly property bool kbdOn: (root.perfParts && root.perfParts.length >= mainPart)
                                      ? root.perfParts[mainPart - 1].zoneOn : false

        radius: ScaleMetrics.dp(4)
        color: Theme.bgCard
        border.color: Bridge.seqActiveTrack === trackIdx ? colRoot.trackColor : Theme.borderCard
        border.width: Bridge.seqActiveTrack === trackIdx ? 2 : 1

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(4)
            spacing: ScaleMetrics.dp(3)

            // Track Header: name on top, part / KBD / stop below.
            // Tap to select the track, long-press to rename it.
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: root.trackHeaderHeight
                radius: ScaleMetrics.dp(3)
                color: Theme.bgSurface
                border.color: Theme.borderCard
                border.width: 1

                MouseArea {
                    anchors.fill: parent
                    onClicked: Bridge.seqSelectTrack(colRoot.trackIdx)
                    onPressAndHold: {
                        Bridge.seqSelectTrack(colRoot.trackIdx);
                        trackRename.openTrack(colRoot.trackIdx, colRoot.trackData ? colRoot.trackData.name : "");
                    }
                }

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(3)
                    spacing: ScaleMetrics.dp(2)

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: ScaleMetrics.dp(4)

                        Rectangle {
                            width: ScaleMetrics.dp(6)
                            height: ScaleMetrics.dp(6)
                            radius: 3
                            color: colRoot.trackColor
                        }

                        Text {
                            Layout.fillWidth: true
                            text: colRoot.trackData ? colRoot.trackData.name : ""
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: Theme.textPrimary
                            elide: Text.ElideRight
                        }

                        // Step playhead display
                        Text {
                            visible: Bridge.seqIsPlaying && colRoot.trackData && colRoot.trackData.activeClipIdx >= 0
                            text: (colRoot.currentPlayhead + 1).toString()
                            font.family: Theme.fontMono
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(7)
                            color: colRoot.trackColor
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: ScaleMetrics.dp(3)

                        // Audio tracks play files, not parts
                        SpButton {
                            visible: colRoot.isAudio
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            icon: "track.audio"
                            iconSize: 11
                            text: "AUDIO"
                            fontSize: 8
                            variant: "outline"
                            accent: colRoot.trackColor
                            onClicked: Bridge.seqSelectTrack(colRoot.trackIdx)
                        }

                        // Parts: main part + layer count; tap to pick them
                        SpButton {
                            id: partBadge
                            objectName: "partBadge"
                            visible: !colRoot.isAudio
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            text: "P" + colRoot.mainPart + (colRoot.layerCount > 0 ? "+" + colRoot.layerCount : "")
                            fontSize: 8
                            variant: "outline"
                            accent: colRoot.trackColor
                            onClicked: partPicker.open(colRoot.trackIdx, "main", partBadge)
                        }

                        // Kbd switch of the track's part(s): also play them from the keyboard
                        SpButton {
                            visible: !colRoot.isAudio
                            Layout.preferredWidth: ScaleMetrics.dp(26)
                            Layout.fillHeight: true
                            text: "KBD"
                            fontSize: 8
                            checked: colRoot.kbdOn
                            onClicked: Bridge.seqSetTrackKbd(colRoot.trackIdx, !colRoot.kbdOn)
                        }

                        // Track stop button
                        SpButton {
                            Layout.preferredWidth: ScaleMetrics.dp(16)
                            Layout.fillHeight: true
                            icon: "stop"
                            fontSize: 8
                            onClicked: Bridge.seqStopTrack(colRoot.trackIdx)
                        }
                    }
                }
            }

            // 8 Clip Tiles
            Repeater {
                model: 8
                delegate: ClipTile {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredHeight: 1
                    trackIndex: colRoot.trackIdx
                    clipIndex: index
                    trackColor: colRoot.trackColor
                    trackData: colRoot.trackData
                }
            }
        }
    }


    // =========================================================================
    // Clip Tile Component
    // =========================================================================
    component ClipTile: Rectangle {
        id: tileRoot
        property int trackIndex: 0
        property int clipIndex: 0
        property color trackColor: Theme.pageAccent
        property var trackData: null

        readonly property var clipData: (trackData && trackData.clips && trackData.clips.length > clipIndex)
                                        ? trackData.clips[clipIndex] : null
        readonly property bool isAudio: trackData ? trackData.kind === "audio" : false
        // An audio clip with a file counts as content; its state can flag a problem
        readonly property string audioState: (isAudio && clipData && clipData.audioState) || ""
        readonly property bool audioProblem: audioState === "missing" || audioState === "error"
        readonly property bool hasNotes: clipData ? (isAudio ? !!clipData.audioFile : clipData.hasNotes) : false
        // Audio clips that start at once (pads) play without the transport
        readonly property bool isPlaying: trackData ? (trackData.activeClipIdx === clipIndex
                                                       && (Bridge.seqIsPlaying || (isAudio && clipData && !clipData.audioSync))) : false
        readonly property bool isQueued: trackData ? (trackData.queuedClipIdx === clipIndex) : false
        readonly property bool isSelected: trackData ? trackData.selectedClipIdx === clipIndex : false

        radius: ScaleMetrics.dp(4)
        color: isPlaying ? Qt.rgba(trackColor.r, trackColor.g, trackColor.b, 0.25)
                         : (hasNotes ? Theme.bgSurface : Theme.bgApp)
        border.color: isPlaying ? trackColor
                                : (isQueued ? Theme.warning
                                            : (isSelected ? Theme.textPrimary : Theme.borderCard))
        border.width: (isPlaying || isQueued || isSelected) ? 2 : 1

        RowLayout {
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(4)
            spacing: ScaleMetrics.dp(4)

            // Play / launch icon
            Icon {
                name: isPlaying ? "play" : (isQueued ? "busy" : (hasNotes ? (isAudio ? "track.audio" : "dotFilled") : ""))
                size: hasNotes && !isPlaying && !isQueued && !isAudio ? 7 : 11
                color: isPlaying ? trackColor : (isQueued ? Theme.warning : Theme.textDim)
            }

            // Clip Name
            Text {
                Layout.fillWidth: true
                text: clipData ? (clipData.name || ("Clip " + (clipIndex + 1))) : ("C" + (clipIndex + 1))
                font.bold: isPlaying || hasNotes
                font.pixelSize: ScaleMetrics.sp(8)
                color: isPlaying ? Theme.textPrimary : (hasNotes ? Theme.textSecondary : Theme.textDim)
                elide: Text.ElideRight
            }

            // Status label
            Text {
                visible: isQueued || isPlaying || audioProblem || audioState === "converting"
                text: isQueued ? "QUEUED" : (isPlaying ? "PLAY"
                      : (audioState === "converting" ? "PREP" : (audioState === "missing" ? "MISSING" : "ERROR")))
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(6)
                color: isQueued || audioState === "converting" ? Theme.warning
                       : (audioProblem && !isPlaying ? Theme.recording : trackColor)
            }
        }

        MouseArea {
            anchors.fill: parent
            onClicked: {
                Bridge.seqSelectTrack(trackIndex);
                Bridge.seqSelectClip(clipIndex);
                Bridge.seqLaunchClip(trackIndex, clipIndex);
            }
            onDoubleClicked: {
                Bridge.seqSelectTrack(trackIndex);
                Bridge.seqSelectClip(clipIndex);
                Bridge.setActiveView("SEQUENCER");
            }
        }
    }

    // =========================================================================
    // Lane Column Component (MOTION): lane header + 8 automation clip slots.
    // A linked lane launches with its track, so its tiles only select.
    // =========================================================================
    component LaneColumn: Rectangle {
        id: laneRoot
        property int laneIdx: 0
        readonly property var laneData: root.lanes.length > laneIdx ? root.lanes[laneIdx] : null
        readonly property color laneColor: root.trackColors[laneIdx % root.trackColors.length]
        readonly property bool linked: laneData ? laneData.linkTrack >= 0 : false
        readonly property bool hasTarget: laneData ? laneData.target !== "" : false
        readonly property int playhead: (Bridge.seqLanePlayheads && Bridge.seqLanePlayheads.length > laneIdx)
                                        ? Bridge.seqLanePlayheads[laneIdx] : 0

        radius: ScaleMetrics.dp(4)
        color: Theme.bgCard
        border.color: Bridge.seqActiveLane === laneIdx ? laneRoot.laneColor : Theme.borderCard
        border.width: Bridge.seqActiveLane === laneIdx ? 2 : 1

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(4)
            spacing: ScaleMetrics.dp(3)

            // Lane header: parameter on top, link / stop below. Tap to select the lane.
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: root.trackHeaderHeight
                radius: ScaleMetrics.dp(3)
                color: Theme.bgSurface
                border.color: Theme.borderCard
                border.width: 1

                MouseArea {
                    anchors.fill: parent
                    onClicked: Bridge.seqSelectLane(laneRoot.laneIdx)
                }

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(3)
                    spacing: ScaleMetrics.dp(2)

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: ScaleMetrics.dp(4)

                        Rectangle {
                            width: ScaleMetrics.dp(6)
                            height: ScaleMetrics.dp(6)
                            radius: 3
                            color: laneRoot.laneColor
                        }

                        Text {
                            Layout.fillWidth: true
                            text: laneRoot.hasTarget ? laneRoot.laneData.tabName : "LANE " + (laneRoot.laneIdx + 1)
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: laneRoot.hasTarget ? Theme.textPrimary : Theme.textDim
                            elide: Text.ElideRight
                        }

                        Text {
                            visible: Bridge.seqIsPlaying && laneRoot.laneData && laneRoot.laneData.activeClipIdx >= 0
                            text: (laneRoot.playhead + 1).toString()
                            font.family: Theme.fontMono
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(7)
                            color: laneRoot.laneColor
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: ScaleMetrics.dp(3)

                        // The note track it launches with (as on the sequencer's LINK)
                        SpButton {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            text: laneRoot.linked ? "LINK T" + (laneRoot.laneData.linkTrack + 1) : "LINK OFF"
                            fontSize: 8
                            variant: laneRoot.linked ? "outline" : "neutral"
                            accent: laneRoot.linked
                                    ? root.trackColors[laneRoot.laneData.linkTrack % root.trackColors.length]
                                    : Theme.pageAccent
                            onClicked: Bridge.seqSelectLane(laneRoot.laneIdx)
                        }

                        SpButton {
                            Layout.preferredWidth: ScaleMetrics.dp(16)
                            Layout.fillHeight: true
                            enabled: !laneRoot.linked
                            opacity: enabled ? 1.0 : 0.35
                            icon: "stop"
                            fontSize: 8
                            onClicked: Bridge.seqStopLane(laneRoot.laneIdx)
                        }
                    }
                }
            }

            // 8 Clip Tiles
            Repeater {
                model: 8
                delegate: LaneTile {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredHeight: 1
                    laneIndex: laneRoot.laneIdx
                    clipIndex: index
                    laneColor: laneRoot.laneColor
                    laneData: laneRoot.laneData
                }
            }
        }
    }

    component LaneTile: Rectangle {
        id: laneTile
        property int laneIndex: 0
        property int clipIndex: 0
        property color laneColor: Theme.pageAccent
        property var laneData: null

        readonly property var clipData: (laneData && laneData.clips && laneData.clips.length > clipIndex)
                                        ? laneData.clips[clipIndex] : null
        readonly property bool linked: laneData ? laneData.linkTrack >= 0 : false
        readonly property bool hasValues: clipData ? clipData.hasValues : false
        // A linked lane shows its track's launches
        readonly property bool isPlaying: laneData ? (Bridge.seqIsPlaying && laneData.activeClipIdx === clipIndex) : false
        readonly property bool isQueued: laneData ? laneData.queuedClipIdx === clipIndex : false
        readonly property bool isSelected: laneData ? laneData.selectedClipIdx === clipIndex : false

        radius: ScaleMetrics.dp(4)
        opacity: linked && !isPlaying && !isQueued ? 0.5 : 1.0
        color: isPlaying ? Qt.rgba(laneColor.r, laneColor.g, laneColor.b, 0.25)
                         : (hasValues ? Theme.bgSurface : Theme.bgApp)
        border.color: isPlaying ? laneColor
                                : (isQueued ? Theme.warning
                                            : (isSelected ? Theme.textPrimary : Theme.borderCard))
        border.width: (isPlaying || isQueued || isSelected) ? 2 : 1

        RowLayout {
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(4)
            spacing: ScaleMetrics.dp(4)

            Icon {
                name: laneTile.isPlaying ? "play" : (laneTile.isQueued ? "busy" : (laneTile.hasValues ? "dotFilled" : ""))
                size: laneTile.hasValues && !laneTile.isPlaying && !laneTile.isQueued ? 7 : 11
                color: laneTile.isPlaying ? laneTile.laneColor : (laneTile.isQueued ? Theme.warning : Theme.textDim)
            }

            Text {
                Layout.fillWidth: true
                text: laneTile.clipData ? (laneTile.clipData.name || ("Clip " + (laneTile.clipIndex + 1)))
                                        : ("C" + (laneTile.clipIndex + 1))
                font.bold: laneTile.isPlaying || laneTile.hasValues
                font.pixelSize: ScaleMetrics.sp(8)
                color: laneTile.isPlaying ? Theme.textPrimary : (laneTile.hasValues ? Theme.textSecondary : Theme.textDim)
                elide: Text.ElideRight
            }

            Text {
                visible: laneTile.isQueued || laneTile.isPlaying
                text: laneTile.isQueued ? "QUEUED" : "PLAY"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(6)
                color: laneTile.isQueued ? Theme.warning : laneTile.laneColor
            }
        }

        MouseArea {
            anchors.fill: parent
            onClicked: {
                Bridge.seqSelectLane(laneTile.laneIndex);
                Bridge.seqSelectLaneClip(laneTile.laneIndex, laneTile.clipIndex);
                if (!laneTile.linked)
                    Bridge.seqLaunchLaneClip(laneTile.laneIndex, laneTile.clipIndex);
            }
            onDoubleClicked: {
                Bridge.seqSelectLane(laneTile.laneIndex);
                Bridge.seqSelectLaneClip(laneTile.laneIndex, laneTile.clipIndex);
                Bridge.setActiveView("SEQUENCER");
            }
        }
    }

    PartPicker {
        id: partPicker
    }

    RenameModal {
        id: trackRename
    }
}
