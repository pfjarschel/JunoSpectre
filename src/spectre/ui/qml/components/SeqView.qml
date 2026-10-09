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

    property int selectedStepIdx: 0
    property int currentStepPage: 0 // 16 steps per page: 0: steps 0-15 ... 7: steps 112-127
    property bool layerPickerOpen: false

    readonly property var trackColors: Theme.trackColors
    readonly property var trackNames: ["T1 SYNTH", "T2 SYNTH", "T3 SYNTH", "T4 SYNTH", "RHYTHM"]

    readonly property var activeTrackData: (Bridge.seqTracks && Bridge.seqTracks.length > Bridge.seqActiveTrack)
                                           ? Bridge.seqTracks[Bridge.seqActiveTrack] : null
    readonly property color currentTrackColor: trackColors[Bridge.seqActiveTrack % trackColors.length]
    readonly property var stepsList: Bridge.seqActiveClipSteps || []
    readonly property int currentPlayhead: (Bridge.seqPlayheads && Bridge.seqPlayheads.length > Bridge.seqActiveTrack)
                                           ? Bridge.seqPlayheads[Bridge.seqActiveTrack] : 0
    readonly property int stepPageCount: Math.max(1, Math.ceil((stepsList.length || 16) / 16))
    // Switching to a shorter clip/track must not leave the view on a page that no longer exists
    onStepPageCountChanged: if (currentStepPage >= stepPageCount) currentStepPage = 0
    readonly property var selStep: (stepsList && stepsList.length > selectedStepIdx)
                                   ? stepsList[selectedStepIdx] : null
    // The note the inspector's PITCH / VELOCITY edit: the one picked on the pad
    // if the step still has it, else the step's lowest note
    property int selectedNotePitch: -1
    readonly property var selNote: {
        const notes = (selStep && selStep.notes) ? selStep.notes : [];
        for (let i = 0; i < notes.length; i++)
            if (notes[i].pitch === selectedNotePitch) return notes[i];
        return notes.length > 0 ? notes[0] : null;
    }

    function selectNote(stepIdx, pitch) {
        selectedStepIdx = stepIdx;
        selectedNotePitch = pitch;
        Bridge.seqSetCursorStep(stepIdx);
    }

    // Move the selected note; on an empty step, add one instead
    function nudgeSelNote(semitones) {
        if (selNote)
            selectedNotePitch = Bridge.seqNudgeNotePitch(selectedStepIdx, selNote.pitch, semitones);
        else if (selStep)
            selectedNotePitch = Bridge.seqAddStepNote(selectedStepIdx);
    }

    // Drum quick buttons: turn the selected hit into another one
    function setSelNotePitch(pitch) {
        const p = Bridge.seqSetNotePitch(selectedStepIdx, selNote ? selNote.pitch : -1, pitch);
        if (p >= 0) selectedNotePitch = p;
    }

    // Pitch to Note Name Helper
    function formatPitch(pitch, isDrum) {
        if (pitch < 0) return "--";
        if (isDrum) {
            switch (pitch) {
                case 35: case 36: return "BD";
                case 38: case 40: return "SD";
                case 42: case 44: return "CH";
                case 46: return "OH";
                case 49: case 57: return "CY";
                case 51: case 59: return "RD";
                case 37: return "SS";
                case 39: return "CP";
                default: return "D" + pitch;
            }
        }
        const noteNames = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
        const octave = Math.floor(pitch / 12) - 1;
        return noteNames[pitch % 12] + octave;
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: ScaleMetrics.dp(8)
        spacing: ScaleMetrics.dp(6)

        // =====================================================================
        // 1. TOP HEADER & TRANSPORT CONTROLS
        // =====================================================================
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(8)

            Rectangle {
                width: ScaleMetrics.dp(8)
                height: ScaleMetrics.dp(8)
                radius: 4
                color: "#10b981"
            }

            Text {
                text: "STEP SEQUENCER & MOTION"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(12)
                font.letterSpacing: 1.2
                color: Theme.textPrimary
            }

            Item { Layout.fillWidth: true }

            // Keyboard plays a different part than the active track sends to
            KbdPartHint {}

            // Step Rec Toggle
            Rectangle {
                height: ScaleMetrics.dp(28)
                width: ScaleMetrics.dp(90)
                radius: 4
                color: Bridge.seqStepRecordEnabled ? "#450a0a" : Theme.bgApp
                border.color: Bridge.seqStepRecordEnabled ? Theme.recording : Theme.borderCard
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: ScaleMetrics.dp(4)
                    Rectangle {
                        width: ScaleMetrics.dp(6); height: ScaleMetrics.dp(6); radius: 3
                        color: Bridge.seqStepRecordEnabled ? Theme.recording : Theme.textDim
                    }
                    Text {
                        text: "STEP REC"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Bridge.seqStepRecordEnabled ? Theme.recording : Theme.textDim
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: Bridge.seqToggleStepRecord(!Bridge.seqStepRecordEnabled)
                }
            }

            Rectangle { width: 1; height: ScaleMetrics.dp(20); color: Theme.borderCard }

            // Switch to Live Session Matrix
            Rectangle {
                height: ScaleMetrics.dp(28)
                width: ScaleMetrics.dp(105)
                radius: 4
                color: Theme.bgApp
                border.color: Theme.tone1
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: ScaleMetrics.dp(4)
                    Text { text: "⊞"; font.pixelSize: ScaleMetrics.sp(9); color: Theme.tone1 }
                    Text {
                        text: "LIVE MATRIX"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Theme.tone1
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: Bridge.setActiveView("LIVE")
                }
            }
        }

        // =====================================================================
        // 2. TRACK SELECTION STRIP & TRACK SETTINGS
        // =====================================================================
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(6)

            // 5 Track Tabs
            RowLayout {
                spacing: ScaleMetrics.dp(4)
                Repeater {
                    model: 5
                    delegate: Rectangle {
                        height: ScaleMetrics.dp(26)
                        width: ScaleMetrics.dp(72)
                        radius: 3
                        color: Bridge.seqActiveTrack === index ? root.trackColors[index] : Theme.bgApp
                        border.color: root.trackColors[index]
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: ["T1 LEAD", "T2 POLY", "T3 BASS", "T4 PAD", "RHYTHM"][index]
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: Bridge.seqActiveTrack === index ? "#ffffff" : Theme.textSecondary
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: Bridge.seqSelectTrack(index)
                        }
                    }
                }
            }

            Rectangle { width: 1; height: ScaleMetrics.dp(20); color: Theme.borderCard }

            // Target Part Selector
            SeqStepper {
                label: "PART:"
                count: 16
                index: (root.activeTrackData && root.activeTrackData.targetPart ? root.activeTrackData.targetPart : (Bridge.seqActiveTrack + 1)) - 1
                valueText: "P" + (index + 1)
                valueColor: root.currentTrackColor
                onRequested: (i) => Bridge.seqSetTrackTargetPart(Bridge.seqActiveTrack, i + 1)
            }

            // Layers: extra parts this track also sends to (tap to edit)
            Rectangle {
                id: layerChip
                readonly property var layers: (root.activeTrackData && root.activeTrackData.layerParts)
                                              ? root.activeTrackData.layerParts : []
                height: ScaleMetrics.dp(30)
                width: Math.min(ScaleMetrics.dp(110), layerText.implicitWidth + ScaleMetrics.dp(16))
                radius: 3
                color: root.layerPickerOpen ? Theme.bgCardActive : Theme.bgApp
                border.color: layers.length > 0 || root.layerPickerOpen ? root.currentTrackColor : Theme.borderCard
                border.width: 1

                Text {
                    id: layerText
                    anchors.centerIn: parent
                    width: Math.min(implicitWidth, parent.width - ScaleMetrics.dp(8))
                    text: layerChip.layers.length > 0
                          ? "+ " + layerChip.layers.map(p => "P" + p).join(" ")
                          : "+ LAYER"
                    elide: Text.ElideRight
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: layerChip.layers.length > 0 ? root.currentTrackColor : Theme.textDim
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        const pos = layerChip.mapToItem(root, 0, layerChip.height + ScaleMetrics.dp(4));
                        layerPicker.x = Math.min(pos.x, root.width - layerPicker.width - ScaleMetrics.dp(8));
                        layerPicker.y = pos.y;
                        root.layerPickerOpen = !root.layerPickerOpen;
                    }
                }
            }

            // Clock Divider (ordered shortest -> longest step)
            SeqStepper {
                readonly property var divs: ["1/32", "1/16T", "1/16", "1/8T", "1/8", "1/4"]
                label: "DIV:"
                count: divs.length
                index: Math.max(0, divs.indexOf(root.activeTrackData ? root.activeTrackData.clockDivider : "1/16"))
                valueText: divs[index]
                valueColor: "#38bdf8"
                pxPerStep: ScaleMetrics.dp(18)
                onRequested: (i) => Bridge.seqSetTrackClockDivider(Bridge.seqActiveTrack, divs[i])
            }

            // Swing: 50% = straight, 66% ≈ triplet shuffle, 75% = hard swing (1% steps)
            SeqStepper {
                label: "SWING:"
                count: 26
                index: Math.round(((root.activeTrackData ? root.activeTrackData.swing : 0.50) - 0.50) * 100)
                valueText: (50 + index) + "%"
                valueColor: "#fbbf24"
                pxPerStep: ScaleMetrics.dp(8)
                onRequested: (i) => Bridge.seqSetTrackSwing(Bridge.seqActiveTrack, 0.50 + i / 100)
            }

            Item { Layout.fillWidth: true }
        }

        // =====================================================================
        // 3. CLIP SELECTION & PATTERN SETTINGS STRIP
        // =====================================================================
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(6)

            // 8 Clip Tabs
            RowLayout {
                spacing: ScaleMetrics.dp(3)
                Repeater {
                    model: 8
                    delegate: Rectangle {
                        height: ScaleMetrics.dp(26)
                        width: ScaleMetrics.dp(36)
                        radius: 3
                        color: Bridge.seqActiveClip === index ? Theme.bgCardActive : Theme.bgApp
                        border.color: Bridge.seqActiveClip === index ? root.currentTrackColor : Theme.borderCard
                        border.width: Bridge.seqActiveClip === index ? 2 : 1

                        Text {
                            anchors.centerIn: parent
                            text: "C" + (index + 1)
                            font.bold: Bridge.seqActiveClip === index
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: Bridge.seqActiveClip === index ? root.currentTrackColor : Theme.textDim
                        }
                        // Playing (green) / queued (amber) marker for this track's clips
                        Rectangle {
                            readonly property bool playing: Bridge.seqIsPlaying && root.activeTrackData
                                                            && root.activeTrackData.activeClipIdx === index
                            readonly property bool queued: root.activeTrackData && root.activeTrackData.queuedClipIdx === index
                            visible: playing || queued
                            anchors.top: parent.top
                            anchors.right: parent.right
                            anchors.margins: ScaleMetrics.dp(3)
                            width: ScaleMetrics.dp(5)
                            height: width
                            radius: width / 2
                            color: playing ? "#10b981" : "#f59e0b"
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                Bridge.seqSelectClip(index);
                                // Editing a clip also makes it the track's playing clip
                                // (applied on the next bar when running, at Play when stopped).
                                Bridge.seqLaunchClip(Bridge.seqActiveTrack, index);
                            }
                        }
                    }
                }
            }

            Rectangle { width: 1; height: ScaleMetrics.dp(20); color: Theme.borderCard }

            // Clip Length
            SeqStepper {
                readonly property var lens: [16, 32, 64, 128]
                label: "LEN:"
                count: lens.length
                index: Math.max(0, lens.indexOf(root.stepsList ? root.stepsList.length : 16))
                valueText: lens[index] + "S"
                valueColor: "#10b981"
                pxPerStep: ScaleMetrics.dp(20)
                onRequested: (i) => {
                    root.currentStepPage = 0;
                    Bridge.seqSetClipLength(lens[i]);
                }
            }

            // Bar Pages (always shown, one tab per 16 steps)
            Rectangle {
                width: 1
                height: ScaleMetrics.dp(20)
                color: Theme.borderCard
            }

            RowLayout {
                spacing: ScaleMetrics.dp(4)
                Text {
                    text: "PAGES:"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: Theme.textDim
                }
                Repeater {
                    model: root.stepPageCount
                    delegate: Rectangle {
                        height: ScaleMetrics.dp(26)
                        width: ScaleMetrics.dp(42)
                        radius: 3
                        color: root.currentStepPage === index ? root.currentTrackColor : Theme.bgApp
                        border.color: root.currentStepPage === index ? root.currentTrackColor : Theme.borderCard
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: ((index * 16) + 1) + "-" + ((index + 1) * 16)
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: root.currentStepPage === index ? "#ffffff" : Theme.textDim
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: root.currentStepPage = index
                        }
                    }
                }
            }

            Item { Layout.fillWidth: true }

            // Clear Clip Button
            Rectangle {
                height: ScaleMetrics.dp(26)
                width: ScaleMetrics.dp(95)
                radius: 3
                color: clearClipMouse.pressed ? "#7f1d1d" : Theme.bgApp
                border.color: clearClipMouse.containsPress ? Theme.recording : Theme.borderCard
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: ScaleMetrics.dp(4)
                    Text { text: "🗑"; font.pixelSize: ScaleMetrics.sp(8); color: Theme.recording }
                    Text {
                        text: "CLEAR CLIP"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Theme.recording
                    }
                }
                MouseArea {
                    id: clearClipMouse
                    anchors.fill: parent
                    onClicked: Bridge.seqClearActiveClip()
                }
            }
        }

        // =====================================================================
        // 4. 16-STEP GRID MATRIX (2 Rows of 8 Steps)
        // =====================================================================
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: ScaleMetrics.dp(6)
            color: Theme.bgApp
            border.color: Theme.borderCard
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(6)
                spacing: ScaleMetrics.dp(6)

                // Row 1: Steps 0-7 of current page
                RowLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: ScaleMetrics.dp(6)
                    Repeater {
                        model: 8
                        delegate: StepTile {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            stepOffset: (root.currentStepPage * 16) + index
                        }
                    }
                }

                // Row 2: Steps 8-15 of current page
                RowLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: ScaleMetrics.dp(6)
                    Repeater {
                        model: 8
                        delegate: StepTile {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            stepOffset: (root.currentStepPage * 16) + 8 + index
                        }
                    }
                }
            }
        }

        // =====================================================================
        // 5. STEP RECORD CONTROLS & STEP PARAMETER INSPECTOR
        // =====================================================================
        Rectangle {
            Layout.fillWidth: true
            height: ScaleMetrics.dp(82)
            radius: ScaleMetrics.dp(6)
            color: Theme.bgApp
            border.color: Theme.borderCard
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(5)
                spacing: ScaleMetrics.dp(4)

                // Step-Record Controls (Active when Step Record is On)
                Rectangle {
                    Layout.preferredWidth: ScaleMetrics.dp(250)
                    Layout.fillHeight: true
                    radius: ScaleMetrics.dp(4)
                    color: Bridge.seqStepRecordEnabled ? "#3f1a1a" : Theme.bgSurface
                    border.color: Bridge.seqStepRecordEnabled ? Theme.recording : Theme.borderCard
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: ScaleMetrics.dp(3)
                        spacing: ScaleMetrics.dp(2)

                        Text {
                            text: Bridge.seqStepRecordEnabled ? "● STEP REC CURSOR: " + (Bridge.seqCursorStep + 1) : "STEP REC: OFF"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: Bridge.seqStepRecordEnabled ? Theme.recording : Theme.textDim
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            spacing: ScaleMetrics.dp(3)

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                radius: 2
                                color: Theme.bgApp
                                border.color: Theme.borderCard
                                border.width: 1
                                Text { anchors.centerIn: parent; text: "REST"; font.bold: true; font.pixelSize: ScaleMetrics.sp(10); color: Theme.textSecondary }
                                MouseArea { anchors.fill: parent; onClicked: Bridge.seqRecordRest() }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                radius: 2
                                color: Theme.bgApp
                                border.color: Theme.borderCard
                                border.width: 1
                                Text { anchors.centerIn: parent; text: "TIE"; font.bold: true; font.pixelSize: ScaleMetrics.sp(10); color: Theme.textSecondary }
                                MouseArea { anchors.fill: parent; onClicked: Bridge.seqRecordTie() }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                radius: 2
                                color: Theme.bgApp
                                border.color: Theme.borderCard
                                border.width: 1
                                Text { anchors.centerIn: parent; text: "CLEAR"; font.bold: true; font.pixelSize: ScaleMetrics.sp(10); color: Theme.recording }
                                MouseArea { anchors.fill: parent; onClicked: Bridge.seqClearStep(Bridge.seqCursorStep) }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            spacing: ScaleMetrics.dp(3)
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                radius: 2
                                color: Theme.bgApp
                                Text { anchors.centerIn: parent; text: "◀ PREV"; font.bold: true; font.pixelSize: ScaleMetrics.sp(9); color: Theme.textSecondary }
                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: Bridge.seqSetCursorStep(Math.max(0, Bridge.seqCursorStep - 1))
                                }
                            }
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                radius: 2
                                color: Theme.bgApp
                                Text { anchors.centerIn: parent; text: "NEXT ▶"; font.bold: true; font.pixelSize: ScaleMetrics.sp(9); color: Theme.textSecondary }
                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: Bridge.seqSetCursorStep(Bridge.seqCursorStep + 1)
                                }
                            }
                        }
                    }
                }

                // Inspector Controls
                RowLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: ScaleMetrics.dp(4)

                    // Pitch Scrubber
                    InspectorParam {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        title: "PITCH"
                        valStr: root.selNote ? root.formatPitch(root.selNote.pitch, Bridge.seqActiveTrack === 4) : "--"
                        accent: "#e879f9"
                        onAdjust: (delta) => root.nudgeSelNote(delta)
                    }

                    // Pitch Semitone / Octave / Drum Quick Buttons
                    Rectangle {
                        width: ScaleMetrics.dp(95)
                        Layout.fillHeight: true
                        radius: ScaleMetrics.dp(4)
                        color: Theme.bgSurface
                        border.color: Theme.borderCard
                        border.width: 1

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: ScaleMetrics.dp(3)
                            spacing: ScaleMetrics.dp(2)

                            // Drum Track: BD, SD, CH, OH, CP, CY
                            ColumnLayout {
                                visible: Bridge.seqActiveTrack === 4
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                spacing: 2
                                RowLayout {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    spacing: 2
                                    Repeater {
                                        model: [ { name: "BD", p: 36 }, { name: "SD", p: 38 }, { name: "CH", p: 42 } ]
                                        delegate: Rectangle {
                                            Layout.fillWidth: true
                                            Layout.fillHeight: true
                                            radius: 2
                                            color: (root.selNote && root.selNote.pitch === modelData.p) ? "#f59e0b" : Theme.bgApp
                                            Text {
                                                anchors.centerIn: parent
                                                text: modelData.name
                                                font.bold: true
                                                font.pixelSize: ScaleMetrics.sp(9)
                                                color: (root.selNote && root.selNote.pitch === modelData.p) ? "#000000" : Theme.textSecondary
                                            }
                                            MouseArea {
                                                anchors.fill: parent
                                                onClicked: root.setSelNotePitch(modelData.p)
                                            }
                                        }
                                    }
                                }
                                RowLayout {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    spacing: 2
                                    Repeater {
                                        model: [ { name: "OH", p: 46 }, { name: "CP", p: 39 }, { name: "CY", p: 49 } ]
                                        delegate: Rectangle {
                                            Layout.fillWidth: true
                                            Layout.fillHeight: true
                                            radius: 2
                                            color: (root.selNote && root.selNote.pitch === modelData.p) ? "#f59e0b" : Theme.bgApp
                                            Text {
                                                anchors.centerIn: parent
                                                text: modelData.name
                                                font.bold: true
                                                font.pixelSize: ScaleMetrics.sp(9)
                                                color: (root.selNote && root.selNote.pitch === modelData.p) ? "#000000" : Theme.textSecondary
                                            }
                                            MouseArea {
                                                anchors.fill: parent
                                                onClicked: root.setSelNotePitch(modelData.p)
                                            }
                                        }
                                    }
                                }
                            }

                            // Melodic Tracks: -1, +1, -OCT, +OCT
                            ColumnLayout {
                                visible: Bridge.seqActiveTrack !== 4
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                spacing: 2
                                RowLayout {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    spacing: 2
                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        radius: 2
                                        color: Theme.bgApp
                                        Text { anchors.centerIn: parent; text: "-1"; font.bold: true; font.pixelSize: ScaleMetrics.sp(10); color: Theme.textSecondary }
                                        MouseArea { anchors.fill: parent; onClicked: root.nudgeSelNote(-1) }
                                    }
                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        radius: 2
                                        color: Theme.bgApp
                                        Text { anchors.centerIn: parent; text: "+1"; font.bold: true; font.pixelSize: ScaleMetrics.sp(10); color: Theme.textSecondary }
                                        MouseArea { anchors.fill: parent; onClicked: root.nudgeSelNote(1) }
                                    }
                                }
                                RowLayout {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    spacing: 2
                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        radius: 2
                                        color: Theme.bgApp
                                        Text { anchors.centerIn: parent; text: "-OCT"; font.bold: true; font.pixelSize: ScaleMetrics.sp(9); color: "#38bdf8" }
                                        MouseArea { anchors.fill: parent; onClicked: root.nudgeSelNote(-12) }
                                    }
                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        radius: 2
                                        color: Theme.bgApp
                                        Text { anchors.centerIn: parent; text: "+OCT"; font.bold: true; font.pixelSize: ScaleMetrics.sp(9); color: "#38bdf8" }
                                        MouseArea { anchors.fill: parent; onClicked: root.nudgeSelNote(12) }
                                    }
                                }
                            }
                        }
                    }

                    // Velocity Dial / Drag
                    InspectorParam {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        title: "VELOCITY"
                        valStr: root.selNote ? root.selNote.velocity.toString() : "--"
                        accent: root.currentTrackColor
                        onAdjust: (delta) => {
                            if (root.selNote) {
                                Bridge.seqSetNoteVelocity(root.selectedStepIdx, root.selNote.pitch,
                                                          Math.max(1, Math.min(127, root.selNote.velocity + delta * 2)));
                            }
                        }
                    }

                    // Gate Length
                    InspectorParam {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        title: "GATE"
                        valStr: selStep ? Math.round(selStep.gateLength * 100) + "%" : "80%"
                        accent: "#10b981"
                        onAdjust: (delta) => {
                            if (selStep) {
                                const curr = selStep.gateLength || 0.8;
                                Bridge.seqSetStepParam(root.selectedStepIdx, "gateLength", Math.max(0.05, Math.min(1.0, curr + delta * 0.05)));
                            }
                        }
                    }

                    // Micro-Timing
                    InspectorParam {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        title: "MICRO"
                        valStr: selStep ? (selStep.microTiming >= 0 ? "+" : "") + selStep.microTiming + "t" : "0t"
                        accent: "#38bdf8"
                        onAdjust: (delta) => {
                            if (selStep) {
                                const curr = selStep.microTiming || 0;
                                Bridge.seqSetStepParam(root.selectedStepIdx, "microTiming", Math.max(-24, Math.min(24, curr + delta)));
                            }
                        }
                    }

                    // Probability
                    InspectorParam {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        title: "PROB"
                        valStr: selStep ? Math.round(selStep.probability * 100) + "%" : "100%"
                        accent: "#fbbf24"
                        onAdjust: (delta) => {
                            if (selStep) {
                                const curr = selStep.probability || 1.0;
                                Bridge.seqSetStepParam(root.selectedStepIdx, "probability", Math.max(0.0, Math.min(1.0, curr + delta * 0.1)));
                            }
                        }
                    }

                    // Tie Toggle (sized and laid out like the drag tiles)
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: ScaleMetrics.dp(4)
                        color: selStep && selStep.tie ? "#1e3a5f" : Theme.bgSurface
                        border.color: selStep && selStep.tie ? "#38bdf8" : Theme.borderCard
                        border.width: 1

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: ScaleMetrics.dp(4)
                            spacing: 2
                            Text {
                                Layout.alignment: Qt.AlignHCenter
                                text: "TIE"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(9)
                                color: selStep && selStep.tie ? "#38bdf8" : Theme.textDim
                            }
                            Item { Layout.fillHeight: true }
                            Text {
                                Layout.alignment: Qt.AlignHCenter
                                text: selStep && selStep.tie ? "ON" : "OFF"
                                font.family: Theme.fontMono
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(14)
                                color: selStep && selStep.tie ? "#ffffff" : Theme.textSecondary
                            }
                            Item { Layout.fillHeight: true }
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                if (selStep) {
                                    Bridge.seqSetStepParam(root.selectedStepIdx, "tie", selStep.tie ? 0 : 1);
                                }
                            }
                        }
                    }

                    // Clear Step
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: ScaleMetrics.dp(4)
                        color: clearStepMouse.pressed ? "#7f1d1d" : Theme.bgSurface
                        border.color: Theme.borderCard
                        border.width: 1

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: ScaleMetrics.dp(4)
                            spacing: 2
                            Text {
                                Layout.alignment: Qt.AlignHCenter
                                text: "STEP"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(9)
                                color: Theme.textDim
                            }
                            Item { Layout.fillHeight: true }
                            Text {
                                Layout.alignment: Qt.AlignHCenter
                                text: "CLEAR"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(14)
                                color: Theme.recording
                            }
                            Item { Layout.fillHeight: true }
                        }

                        MouseArea {
                            id: clearStepMouse
                            anchors.fill: parent
                            onClicked: Bridge.seqClearStep(root.selectedStepIdx)
                        }
                    }
                }
            }
        }
    }

    // Layer picker: tap outside to close
    MouseArea {
        anchors.fill: parent
        visible: root.layerPickerOpen
        z: 50
        onClicked: root.layerPickerOpen = false
    }
    Rectangle {
        id: layerPicker
        visible: root.layerPickerOpen
        z: 51
        width: ScaleMetrics.dp(8 * 34 + 16)
        height: pickerCol.implicitHeight + ScaleMetrics.dp(16)
        radius: ScaleMetrics.dp(6)
        color: Theme.bgSurface
        border.color: root.currentTrackColor
        border.width: 1

        readonly property int mainPart: (root.activeTrackData && root.activeTrackData.targetPart)
                                        ? root.activeTrackData.targetPart : (Bridge.seqActiveTrack + 1)
        readonly property var layers: (root.activeTrackData && root.activeTrackData.layerParts)
                                       ? root.activeTrackData.layerParts : []

        MouseArea { anchors.fill: parent }  // swallow taps between buttons

        ColumnLayout {
            id: pickerCol
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(8)
            spacing: ScaleMetrics.dp(6)

            Text {
                text: "ALSO SEND TO (main: P" + layerPicker.mainPart + ")"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(8)
                font.letterSpacing: 1.0
                color: Theme.textDim
            }
            GridLayout {
                columns: 8
                rowSpacing: ScaleMetrics.dp(4)
                columnSpacing: ScaleMetrics.dp(4)
                Repeater {
                    model: 16
                    delegate: Rectangle {
                        readonly property int part: index + 1
                        readonly property bool isMain: part === layerPicker.mainPart
                        readonly property bool isLayer: layerPicker.layers.indexOf(part) >= 0
                        width: ScaleMetrics.dp(30)
                        height: ScaleMetrics.dp(30)
                        radius: 3
                        color: isMain ? root.currentTrackColor : (isLayer ? Theme.bgCardActive : Theme.bgApp)
                        border.color: isMain || isLayer ? root.currentTrackColor : Theme.borderCard
                        border.width: isLayer ? 2 : 1
                        opacity: isMain ? 0.6 : 1.0
                        Text {
                            anchors.centerIn: parent
                            text: "P" + parent.part
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: parent.isMain ? "#ffffff" : (parent.isLayer ? root.currentTrackColor : Theme.textSecondary)
                        }
                        MouseArea {
                            anchors.fill: parent
                            enabled: !parent.isMain
                            onClicked: Bridge.seqToggleTrackLayer(Bridge.seqActiveTrack, parent.part)
                        }
                    }
                }
            }
        }
    }


    // =========================================================================
    // Step Tile Component
    // =========================================================================
    component StepTile: Rectangle {
        id: stepRoot
        property int stepOffset: 0
        readonly property var stepData: (root.stepsList && root.stepsList.length > stepOffset)
                                        ? root.stepsList[stepOffset] : null
        readonly property bool isActive: stepData ? stepData.isActive : false
        readonly property bool isCurrentPlayhead: Bridge.seqIsPlaying && root.currentPlayhead === stepOffset
        readonly property bool isCursorStep: Bridge.seqStepRecordEnabled && Bridge.seqCursorStep === stepOffset
        readonly property bool isSelected: root.selectedStepIdx === stepOffset

        radius: ScaleMetrics.dp(4)
        color: isActive ? Qt.rgba(root.currentTrackColor.r, root.currentTrackColor.g, root.currentTrackColor.b, 0.22)
                        : ((stepOffset % 4 === 0) ? "#161b26" : Theme.bgSurface)
        border.color: isCurrentPlayhead ? "#ffffff"
                                        : (isCursorStep ? Theme.recording
                                                        : (isSelected ? root.currentTrackColor : Theme.borderCard))
        border.width: (isCurrentPlayhead || isCursorStep || isSelected) ? 2 : 1

        readonly property var notes: (stepData && stepData.notes) ? stepData.notes : []
        readonly property bool isDrum: Bridge.seqActiveTrack === 4

        // Taps outside the note grid just select the step
        MouseArea {
            anchors.fill: parent
            onClicked: root.selectNote(stepOffset, -1)
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(4)
            spacing: ScaleMetrics.dp(3)

            // Top Row: Step Number, Chord Name & Tie
            RowLayout {
                Layout.fillWidth: true
                spacing: ScaleMetrics.dp(4)
                Text {
                    text: (stepOffset + 1).toString()
                    font.family: Theme.fontMono
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(10)
                    color: (stepOffset % 4 === 0) ? Theme.primary : Theme.textSecondary
                }
                Text {
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignRight
                    elide: Text.ElideRight
                    text: stepData ? stepData.chordName : ""
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(10)
                    color: Theme.textPrimary
                }
                Text {
                    visible: stepData && stepData.tie
                    text: "—"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(10)
                    color: "#38bdf8"
                }
            }

            // Note Grid: 3 x 4, sorted low to high (left-right, top-bottom).
            // Tap a note to edit it, double-tap to delete it; on the selected pad, tap a free cell to add one.
            GridLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                columns: 3
                rowSpacing: ScaleMetrics.dp(2)
                columnSpacing: ScaleMetrics.dp(2)

                Repeater {
                    model: 12
                    delegate: Rectangle {
                        id: cell
                        readonly property var note: index < stepRoot.notes.length ? stepRoot.notes[index] : null
                        readonly property bool isSel: note !== null && stepRoot.isSelected
                                                      && root.selNote !== null && root.selNote.pitch === note.pitch
                        // Where a tap adds the next note, shown on the selected step only
                        readonly property bool showAdd: note === null && index === stepRoot.notes.length
                                                        && stepRoot.isSelected && !Bridge.seqStepRecordEnabled
                        readonly property real vel: note ? note.velocity / 127.0 : 0
                        // The tap that added a note mustn't let its double-tap delete it
                        property bool justAdded: false

                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredWidth: 1
                        Layout.preferredHeight: 1
                        radius: 2
                        color: isSel ? root.currentTrackColor
                                     : (note ? Qt.rgba(root.currentTrackColor.r, root.currentTrackColor.g,
                                                       root.currentTrackColor.b, 0.08 + 0.27 * vel)
                                             : "transparent")
                        border.color: showAdd ? Theme.borderCard : "transparent"
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: cell.note ? root.formatPitch(cell.note.pitch, stepRoot.isDrum) : (cell.showAdd ? "+" : "")
                            font.family: Theme.fontMono
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(11)
                            // Softer notes read dimmer
                            color: cell.isSel ? Theme.bgApp : (cell.note ? root.currentTrackColor : Theme.textSecondary)
                            opacity: (cell.note && !cell.isSel) ? 0.5 + 0.5 * cell.vel : 1.0
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                cell.justAdded = false;
                                if (cell.note) {
                                    root.selectNote(stepOffset, cell.note.pitch);
                                    return;
                                }
                                // The first tap only selects the pad; free cells add notes once it's selected
                                const wasSelected = stepRoot.isSelected;
                                root.selectNote(stepOffset, -1);
                                if (wasSelected && !Bridge.seqStepRecordEnabled) {
                                    const p = Bridge.seqAddStepNote(stepOffset);
                                    if (p >= 0) {
                                        root.selectedNotePitch = p;
                                        cell.justAdded = true;
                                    }
                                }
                            }
                            onDoubleClicked: {
                                if (cell.justAdded)
                                    cell.justAdded = false;
                                else if (cell.note)
                                    Bridge.seqDeleteStepNote(stepOffset, cell.note.pitch);
                            }
                        }
                    }
                }
            }

            // Bottom: Velocity Bar (loudest note)
            Rectangle {
                Layout.fillWidth: true
                height: ScaleMetrics.dp(4)
                radius: 1
                color: Theme.bgApp
                clip: true

                Rectangle {
                    height: parent.height
                    width: isActive && stepData ? (parent.width * (stepData.maxVelocity / 127.0)) : 0
                    color: isCurrentPlayhead ? "#ffffff" : root.currentTrackColor
                }
            }
        }
    }

    // =========================================================================
    // Inspector Parameter Drag Component
    // =========================================================================
    component InspectorParam: Rectangle {
        id: ipRoot
        property string title: "PARAM"
        property string valStr: "--"
        property color accent: Theme.primary
        signal adjust(int delta)

        radius: ScaleMetrics.dp(4)
        color: Theme.bgSurface
        border.color: ipMouse.containsPress ? ipRoot.accent : Theme.borderCard
        border.width: 1

        MouseArea {
            id: ipMouse
            anchors.fill: parent
            preventStealing: true
            // Drag right/up to increase, left/down to decrease: a tile at the
            // screen's bottom edge still has the horizontal axis free.
            property real lastX: 0
            property real lastY: 0
            onPressed: (mouse) => { lastX = mouse.x; lastY = mouse.y; }
            onPositionChanged: (mouse) => {
                if (pressed) {
                    const d = (mouse.x - lastX) + (lastY - mouse.y);
                    if (Math.abs(d) > ScaleMetrics.dp(4)) {
                        ipRoot.adjust(d > 0 ? 1 : -1);
                        lastX = mouse.x;
                        lastY = mouse.y;
                    }
                }
            }
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(4)
            spacing: 2
            Text {
                Layout.alignment: Qt.AlignHCenter
                text: ipRoot.title
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(9)
                color: Theme.textDim
            }
            Item { Layout.fillHeight: true }
            Text {
                Layout.alignment: Qt.AlignHCenter
                text: ipRoot.valStr
                font.family: Theme.fontMono
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(14)
                color: ipRoot.accent
            }
            Item { Layout.fillHeight: true }
        }
    }
}
