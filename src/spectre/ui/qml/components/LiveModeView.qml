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

    readonly property var trackColors: [Theme.tone1, Theme.tone2, Theme.tone3, Theme.tone4, "#f59e0b"]
    readonly property var trackNames: ["T1 SYNTH", "T2 SYNTH", "T3 SYNTH", "T4 SYNTH", "RHYTHM"]

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

            // Master Resync Selector
            Rectangle {
                height: ScaleMetrics.dp(28)
                width: ScaleMetrics.dp(85)
                radius: 4
                color: Theme.bgApp
                border.color: Theme.borderCard
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: ScaleMetrics.dp(4)
                    Text {
                        text: "SYNC"
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
                        const options = [0, 1, 2, 4, 8];
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
        // 2. SESSION MATRIX: 5 TRACKS + SCENE LAUNCH FLANK
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
                spacing: ScaleMetrics.dp(6)

                // 5 Track Columns
                Repeater {
                    model: 5
                    delegate: TrackColumn {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        trackIdx: index
                    }
                }

                // Scene Launch Column
                Rectangle {
                    width: ScaleMetrics.dp(85)
                    Layout.fillHeight: true
                    radius: ScaleMetrics.dp(4)
                    color: Theme.bgCard
                    border.color: Theme.borderCard
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: ScaleMetrics.dp(4)
                        spacing: ScaleMetrics.dp(3)

                        // Scenes Header
                        Rectangle {
                            Layout.fillWidth: true
                            height: ScaleMetrics.dp(24)
                            color: "transparent"
                            Text {
                                anchors.centerIn: parent
                                text: "SCENES"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(8)
                                font.letterSpacing: 1.0
                                color: Theme.textDim
                            }
                        }

                        // 8 Scene Launch Buttons
                        Repeater {
                            model: 8
                            delegate: Rectangle {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
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
                                        text: "S " + (index + 1)
                                        font.bold: true
                                        font.pixelSize: ScaleMetrics.sp(8)
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

                        // Stop All Tracks
                        Rectangle {
                            Layout.fillWidth: true
                            height: ScaleMetrics.dp(22)
                            radius: ScaleMetrics.dp(3)
                            color: stopAllMouse.pressed ? "#7f1d1d" : Theme.bgSurface
                            border.color: stopAllMouse.containsPress ? Theme.recording : Theme.borderCard
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: "■ STOP ALL"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(7)
                                color: Theme.recording
                            }

                            MouseArea {
                                id: stopAllMouse
                                anchors.fill: parent
                                onClicked: {
                                    for (let i = 0; i < 5; i++) {
                                        Bridge.seqStopTrack(i);
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        // =====================================================================
        // 3. BOTTOM LIVE MACRO STRIP (8 Dials connected to MacroDeck)
        // =====================================================================
        Rectangle {
            Layout.fillWidth: true
            height: ScaleMetrics.dp(98)
            radius: ScaleMetrics.dp(6)
            color: Theme.bgApp
            border.color: Theme.borderCard
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(6)
                spacing: ScaleMetrics.dp(4)

                // Macro Strip Label
                RowLayout {
                    Layout.fillWidth: true
                    spacing: ScaleMetrics.dp(6)

                    Text {
                        text: "LIVE MACROS"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        font.letterSpacing: 1.0
                        color: Theme.textDim
                    }

                    Text {
                        text: "DRAG VERTICALLY • DOUBLE-TAP TO CENTER"
                        font.pixelSize: ScaleMetrics.sp(7)
                        color: Theme.textDim
                    }

                    Item { Layout.fillWidth: true }

                    Text {
                        text: "DEEP EDIT IN MACRO DECK ➜"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(7)
                        color: Theme.tone2

                        MouseArea {
                            anchors.fill: parent
                            onClicked: Bridge.setActiveView("MACROS")
                        }
                    }
                }

                // 8 Macro Knobs Row
                RowLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: ScaleMetrics.dp(6)

                    Repeater {
                        model: 8
                        delegate: LiveMacroDial {
                            Layout.fillWidth: true
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
        }
    }

    // =========================================================================
    // Track Column Component (Header + 8 Clip Slots)
    // =========================================================================
    component TrackColumn: Rectangle {
        id: colRoot
        property int trackIdx: 0
        readonly property var trackData: (Bridge.seqTracks && Bridge.seqTracks.length > trackIdx)
                                         ? Bridge.seqTracks[trackIdx] : null
        readonly property int currentPlayhead: (Bridge.seqPlayheads && Bridge.seqPlayheads.length > trackIdx)
                                               ? Bridge.seqPlayheads[trackIdx] : 0
        readonly property color trackColor: root.trackColors[trackIdx % root.trackColors.length]

        radius: ScaleMetrics.dp(4)
        color: Theme.bgCard
        border.color: Bridge.seqActiveTrack === trackIdx ? colRoot.trackColor : Theme.borderCard
        border.width: Bridge.seqActiveTrack === trackIdx ? 2 : 1

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(4)
            spacing: ScaleMetrics.dp(3)

            // Track Header
            Rectangle {
                Layout.fillWidth: true
                height: ScaleMetrics.dp(24)
                radius: ScaleMetrics.dp(3)
                color: Theme.bgSurface
                border.color: Theme.borderCard
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(4)
                    spacing: ScaleMetrics.dp(4)

                    Rectangle {
                        width: ScaleMetrics.dp(6)
                        height: ScaleMetrics.dp(6)
                        radius: 3
                        color: colRoot.trackColor
                    }

                    Text {
                        text: root.trackNames[trackIdx]
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Theme.textPrimary
                        elide: Text.ElideRight
                    }

                    Item { Layout.fillWidth: true }

                    // Part Selector
                    Rectangle {
                        width: ScaleMetrics.dp(22)
                        height: ScaleMetrics.dp(16)
                        radius: 2
                        color: Theme.bgApp
                        border.color: Theme.borderCard
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: "P" + (colRoot.trackData && colRoot.trackData.targetPart ? colRoot.trackData.targetPart : (colRoot.trackIdx + 1))
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(7)
                            color: colRoot.trackColor
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                const curr = colRoot.trackData && colRoot.trackData.targetPart ? colRoot.trackData.targetPart : (colRoot.trackIdx + 1);
                                const nextPart = (curr % 16) + 1;
                                Bridge.seqSetTrackTargetPart(colRoot.trackIdx, nextPart);
                            }
                        }
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

                    // Track stop button
                    Rectangle {
                        width: ScaleMetrics.dp(16)
                        height: ScaleMetrics.dp(16)
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
                            onClicked: Bridge.seqStopTrack(trackIdx)
                        }
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    z: -1
                    onClicked: Bridge.seqSelectTrack(trackIdx)
                }
            }

            // 8 Clip Tiles
            Repeater {
                model: 8
                delegate: ClipTile {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
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
    // Compact Live Macro Dial Component
    // =========================================================================
    component LiveMacroDial: Rectangle {
        id: dialRoot
        property int macroIndex: 1
        property string macroTitle: "MACRO"
        property color macroColor: Theme.primary
        property real macroValue01: 0.0

        radius: ScaleMetrics.dp(4)
        color: Theme.bgSurface
        border.color: dialMouse.containsPress ? dialRoot.macroColor : Theme.borderCard
        border.width: 1

        MouseArea {
            id: dialMouse
            anchors.fill: parent
            property real startY: 0
            property real startVal: 0

            onPressed: (mouse) => {
                startY = mouse.y;
                startVal = dialRoot.macroValue01;
            }

            onPositionChanged: (mouse) => {
                if (pressed) {
                    const dy = startY - mouse.y;
                    const newVal = Math.max(-1.0, Math.min(1.0, startVal + dy / ScaleMetrics.dp(50)));
                    Bridge.setMacro(dialRoot.macroIndex, newVal);
                }
            }

            onDoubleClicked: {
                Bridge.setMacro(dialRoot.macroIndex, 0.0);
            }
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(4)
            spacing: ScaleMetrics.dp(2)

            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: "M" + dialRoot.macroIndex
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(7)
                    color: dialRoot.macroColor
                }
                Text {
                    Layout.fillWidth: true
                    text: dialRoot.macroTitle
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(7)
                    color: Theme.textSecondary
                    elide: Text.ElideRight
                }
            }

            // Bipolar Value Bar
            Rectangle {
                Layout.fillWidth: true
                height: ScaleMetrics.dp(12)
                radius: 2
                color: Theme.bgApp
                border.color: Theme.borderCard
                border.width: 1
                clip: true

                // Center divider
                Rectangle {
                    width: 1
                    height: parent.height
                    anchors.horizontalCenter: parent.horizontalCenter
                    color: Theme.borderCard
                }

                // Active bipolar bar
                Rectangle {
                    height: parent.height
                    color: dialRoot.macroColor
                    x: dialRoot.macroValue01 >= 0
                       ? parent.width / 2
                       : (parent.width / 2) + (dialRoot.macroValue01 * (parent.width / 2))
                    width: Math.abs(dialRoot.macroValue01) * (parent.width / 2)
                }
            }

            // Value text
            Text {
                Layout.alignment: Qt.AlignHCenter
                text: (dialRoot.macroValue01 >= 0 ? "+" : "") + dialRoot.macroValue01.toFixed(2)
                font.family: Theme.fontMono
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(7)
                color: Theme.textPrimary
            }
        }
    }
}
