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
                color: Bridge.seqIsPlaying ? "#10b981" : Theme.primary
            }

            Text {
                text: "LIVE SESSION MATRIX"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(12)
                font.letterSpacing: 1.2
                color: Theme.textPrimary
            }

            Item { Layout.fillWidth: true }

            // Keyboard plays a different part than the active track sends to
            KbdPartHint {}

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
                        color: Bridge.seqMasterResync > 0 ? "#38bdf8" : Theme.textSecondary
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

            // Switch to Step Editor
            Rectangle {
                height: ScaleMetrics.dp(28)
                width: ScaleMetrics.dp(100)
                radius: 4
                color: Theme.bgApp
                border.color: "#10b981"
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: ScaleMetrics.dp(4)
                    Text { text: "⏱"; font.pixelSize: ScaleMetrics.sp(9); color: "#10b981" }
                    Text {
                        text: "STEP EDITOR"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: "#10b981"
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
                border.color: "#f59e0b"
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: ScaleMetrics.dp(4)
                    Text { text: "📋"; font.pixelSize: ScaleMetrics.sp(9); color: "#f59e0b" }
                    Text {
                        text: "SETLIST"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: "#f59e0b"
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: Bridge.setActiveView("SETLIST")
                }
            }
        }

        // =====================================================================
        // 2. SESSION MATRIX: 8 TRACKS + SCENE LAUNCH COLUMN
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
                    model: Bridge.seqTracks ? Bridge.seqTracks.length : 0
                    delegate: TrackColumn {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1  // equal columns whatever the names
                        Layout.fillHeight: true
                        trackIdx: index
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
                            color: stopAllMouse.pressed ? "#7f1d1d" : Theme.bgSurface
                            border.color: stopAllMouse.containsPress ? Theme.recording : Theme.borderCard
                            border.width: 1

                            Column {
                                anchors.centerIn: parent
                                spacing: 1
                                Text {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    text: "■ STOP"
                                    font.bold: true
                                    font.pixelSize: ScaleMetrics.sp(8)
                                    color: Theme.recording
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
                                    const n = Bridge.seqTracks ? Bridge.seqTracks.length : 0;
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
                                color: sceneMouse.pressed ? "#047857" : Theme.bgSurface
                                border.color: sceneMouse.containsPress ? "#10b981" : Theme.borderCard
                                border.width: 1

                                RowLayout {
                                    anchors.centerIn: parent
                                    spacing: ScaleMetrics.dp(4)
                                    Text {
                                        text: "▶"
                                        font.pixelSize: ScaleMetrics.sp(8)
                                        color: "#10b981"
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

        // =====================================================================
        // 3. LIVE MACROS: compact cards like the encoder strip
        // (drag to change, double-tap to center; deep edit in the Macro Deck)
        // =====================================================================
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: false
            Layout.preferredHeight: ScaleMetrics.dp(40)
            spacing: ScaleMetrics.dp(6)

            Repeater {
                model: 8
                delegate: LiveMacroDial {
                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    Layout.fillHeight: true
                    macroIndex: modelData + 1
                    macroTitle: (Bridge.macroNames && Bridge.macroNames.length > modelData)
                                ? Bridge.macroNames[modelData] : ("M" + (modelData + 1))
                    macroColor: root.trackColors[modelData % root.trackColors.length]
                    macroValue01: (Bridge.macroValues && Bridge.macroValues.length > modelData)
                                  ? Bridge.macroValues[modelData] : 0.0
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
        readonly property var trackData: (Bridge.seqTracks && Bridge.seqTracks.length > trackIdx)
                                         ? Bridge.seqTracks[trackIdx] : null
        readonly property int currentPlayhead: (Bridge.seqPlayheads && Bridge.seqPlayheads.length > trackIdx)
                                               ? Bridge.seqPlayheads[trackIdx] : 0
        readonly property color trackColor: root.trackColors[trackIdx % root.trackColors.length]
        readonly property int mainPart: (trackData && trackData.targetPart) ? trackData.targetPart : (trackIdx + 1)
        readonly property int layerCount: (trackData && trackData.layerParts) ? trackData.layerParts.length : 0
        readonly property bool kbdOn: (Bridge.perfParts && Bridge.perfParts.length >= mainPart)
                                      ? Bridge.perfParts[mainPart - 1].zoneOn : false

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

                        // Parts: main part + layer count; tap to pick them
                        Rectangle {
                            id: partBadge
                            objectName: "partBadge"
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 2
                            color: Theme.bgApp
                            border.color: Theme.borderCard
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: "P" + colRoot.mainPart + (colRoot.layerCount > 0 ? "+" + colRoot.layerCount : "")
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(7)
                                color: colRoot.trackColor
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: partPicker.open(colRoot.trackIdx, "main", partBadge)
                            }
                        }

                        // Kbd switch of the track's part(s): also play them from the keyboard
                        Rectangle {
                            Layout.preferredWidth: ScaleMetrics.dp(26)
                            Layout.fillHeight: true
                            radius: 2
                            color: colRoot.kbdOn ? "#0d2b1a" : Theme.bgApp
                            border.color: colRoot.kbdOn ? "#10b981" : Theme.borderCard
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: "KBD"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(6)
                                color: colRoot.kbdOn ? "#10b981" : Theme.textDim
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: Bridge.seqSetTrackKbd(colRoot.trackIdx, !colRoot.kbdOn)
                            }
                        }

                        // Track stop button
                        Rectangle {
                            Layout.preferredWidth: ScaleMetrics.dp(16)
                            Layout.fillHeight: true
                            radius: 2
                            color: stopTrackMouse.pressed ? "#7f1d1d" : Theme.bgApp
                            border.color: Theme.borderCard
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: "■"
                                font.pixelSize: ScaleMetrics.sp(7)
                                color: Theme.textDim
                            }

                            MouseArea {
                                id: stopTrackMouse
                                anchors.fill: parent
                                onClicked: Bridge.seqStopTrack(colRoot.trackIdx)
                            }
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
        property color trackColor: Theme.primary
        property var trackData: null

        readonly property var clipData: (trackData && trackData.clips && trackData.clips.length > clipIndex)
                                        ? trackData.clips[clipIndex] : null
        readonly property bool hasNotes: clipData ? clipData.hasNotes : false
        readonly property bool isPlaying: trackData ? (trackData.activeClipIdx === clipIndex && Bridge.seqIsPlaying) : false
        readonly property bool isQueued: trackData ? (trackData.queuedClipIdx === clipIndex) : false
        readonly property bool isSelected: trackData ? trackData.selectedClipIdx === clipIndex : false

        radius: ScaleMetrics.dp(4)
        color: isPlaying ? Qt.rgba(trackColor.r, trackColor.g, trackColor.b, 0.25)
                         : (hasNotes ? Theme.bgSurface : Theme.bgApp)
        border.color: isPlaying ? trackColor
                                : (isQueued ? "#f59e0b"
                                            : (isSelected ? Theme.textPrimary : Theme.borderCard))
        border.width: (isPlaying || isQueued || isSelected) ? 2 : 1

        RowLayout {
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(4)
            spacing: ScaleMetrics.dp(4)

            // Play / launch icon
            Text {
                text: isPlaying ? "▶" : (isQueued ? "⏳" : (hasNotes ? "•" : ""))
                font.pixelSize: ScaleMetrics.sp(8)
                color: isPlaying ? trackColor : (isQueued ? "#f59e0b" : Theme.textDim)
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
                visible: isQueued || isPlaying
                text: isQueued ? "QUEUED" : "PLAY"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(6)
                color: isQueued ? "#f59e0b" : trackColor
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
    // Compact Live Macro Card: name on top, value in the middle, a bipolar bar
    // filling from the center. Drag up/right to raise, down/left to lower;
    // double-tap to center.
    // =========================================================================
    component LiveMacroDial: Rectangle {
        id: dialRoot
        property int macroIndex: 1
        property string macroTitle: "MACRO"
        property color macroColor: Theme.primary
        property real macroValue01: 0.0

        radius: ScaleMetrics.dp(6)
        color: Theme.bgApp
        border.color: dialMouse.containsPress ? dialRoot.macroColor : Theme.borderCard
        border.width: 1

        MouseArea {
            id: dialMouse
            anchors.fill: parent
            preventStealing: true
            property real startX: 0
            property real startY: 0
            property real startVal: 0

            onPressed: (mouse) => {
                startX = mouse.x;
                startY = mouse.y;
                startVal = dialRoot.macroValue01;
            }

            onPositionChanged: (mouse) => {
                if (pressed) {
                    const d = (mouse.x - startX) + (startY - mouse.y);
                    Bridge.setMacro(dialRoot.macroIndex, Math.max(-1.0, Math.min(1.0, startVal + d / ScaleMetrics.dp(60))));
                }
            }

            onDoubleClicked: Bridge.setMacro(dialRoot.macroIndex, 0.0)
        }

        // Header: macro tag + name
        Item {
            id: macroHeader
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: ScaleMetrics.dp(3)
            height: ScaleMetrics.dp(12)

            Rectangle {
                id: macroTag
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                width: ScaleMetrics.dp(18)
                height: ScaleMetrics.dp(12)
                radius: ScaleMetrics.dp(3)
                color: Theme.bgCardActive

                Text {
                    anchors.centerIn: parent
                    text: "M" + dialRoot.macroIndex
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: dialRoot.macroColor
                }
            }

            Text {
                anchors.left: macroTag.right
                anchors.right: parent.right
                anchors.leftMargin: ScaleMetrics.dp(4)
                anchors.verticalCenter: parent.verticalCenter
                text: dialRoot.macroTitle
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(9)
                color: Theme.textSecondary
                elide: Text.ElideRight
            }
        }

        // Value (-100 .. +100)
        Text {
            anchors.top: macroHeader.bottom
            anchors.bottom: macroBar.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottomMargin: ScaleMetrics.dp(2)
            text: {
                const pct = Math.round(dialRoot.macroValue01 * 100);
                return (pct > 0 ? "+" : "") + pct;
            }
            font.bold: true
            font.pixelSize: ScaleMetrics.sp(8)
            font.family: Theme.fontMono
            color: Theme.textPrimary
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }

        // Bipolar bar, filling out from the center
        Rectangle {
            id: macroBar
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.leftMargin: ScaleMetrics.dp(3)
            anchors.rightMargin: ScaleMetrics.dp(3)
            anchors.bottomMargin: ScaleMetrics.dp(6)
            height: ScaleMetrics.dp(3)
            radius: ScaleMetrics.dp(2)
            color: "#1e293b"

            Rectangle {
                height: parent.height
                radius: ScaleMetrics.dp(2)
                color: dialRoot.macroColor
                x: dialRoot.macroValue01 >= 0 ? parent.width / 2
                                              : parent.width / 2 * (1 + dialRoot.macroValue01)
                width: Math.abs(dialRoot.macroValue01) * parent.width / 2
            }

            // Center tick
            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.verticalCenter: parent.verticalCenter
                width: 1
                height: parent.height + ScaleMetrics.dp(4)
                color: Theme.textDim
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
