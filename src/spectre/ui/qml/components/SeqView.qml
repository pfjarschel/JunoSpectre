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

    property int selectedStepIdx: 0
    // Notes shown as step pads or as a piano roll
    property bool rollView: false
    property int currentStepPage: 0 // 16 steps per page: 0: steps 0-15 ... 7: steps 112-127

    readonly property var trackColors: Theme.trackColors
    readonly property var activeTrackData: (Bridge.seqTracks && Bridge.seqTracks.length > Bridge.seqActiveTrack)
                                           ? Bridge.seqTracks[Bridge.seqActiveTrack] : null
    readonly property color currentTrackColor: trackColors[Bridge.seqActiveTrack % trackColors.length]
    // Tracks sending to the rhythm part show drum names and drum buttons
    readonly property bool isDrumTrack: activeTrackData ? activeTrackData.isDrum : false
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

    // Sorted part numbers as "P2 P5–P8 P11": runs of three or more become ranges
    function formatParts(parts) {
        const out = [];
        let i = 0;
        while (i < parts.length) {
            let j = i;
            while (j + 1 < parts.length && parts[j + 1] === parts[j] + 1) j++;
            if (j - i >= 2) {
                out.push("P" + parts[i] + "–P" + parts[j]);
            } else {
                for (let k = i; k <= j; k++) out.push("P" + parts[k]);
            }
            i = j + 1;
        }
        return out.join(" ");
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
                color: Theme.pageAccent
            }

            Text {
                text: "STEP SEQUENCER & MOTION"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(12)
                font.letterSpacing: 1.2
                color: Theme.textPrimary
            }

            // Note tracks (step pads or piano roll) or automation lanes
            Row {
                spacing: ScaleMetrics.dp(3)
                Repeater {
                    model: [ { label: "STEPS", motion: false, roll: false },
                             { label: "ROLL", motion: false, roll: true },
                             { label: "MOTION", motion: true, roll: false } ]
                    delegate: SpButton {
                        implicitHeight: ScaleMetrics.dp(26)
                        implicitWidth: ScaleMetrics.dp(64)
                        text: modelData.label
                        fontSize: 8
                        checked: Bridge.seqMotionMode === modelData.motion
                                 && (modelData.motion || root.rollView === modelData.roll)
                        onClicked: {
                            if (!modelData.motion) root.rollView = modelData.roll;
                            Bridge.seqSetMotionMode(modelData.motion);
                        }
                    }
                }
            }

            Item { Layout.fillWidth: true }

            // Keyboard plays a different part than the active track sends to
            KbdPartHint { suppressed: Bridge.seqMotionMode }

            // Step Rec Toggle: notes (keyboard) or, in MOTION mode, the selected lane
            Rectangle {
                readonly property bool on: Bridge.seqMotionMode ? Bridge.seqLaneStepRec : Bridge.seqStepRecordEnabled
                height: ScaleMetrics.dp(28)
                width: ScaleMetrics.dp(90)
                radius: 4
                color: on ? Theme.tint(Theme.recording, 0.25) : Theme.bgApp
                border.color: on ? Theme.recording : Theme.borderCard
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: ScaleMetrics.dp(4)
                    Rectangle {
                        width: ScaleMetrics.dp(6); height: ScaleMetrics.dp(6); radius: 3
                        color: parent.parent.on ? Theme.recording : Theme.textDim
                    }
                    Text {
                        text: "STEP REC"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: parent.parent.on ? Theme.recording : Theme.textDim
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        if (Bridge.seqMotionMode)
                            Bridge.seqSetLaneStepRec(!Bridge.seqLaneStepRec, motionView.selectedStepIdx);
                        else
                            Bridge.seqToggleStepRecord(!Bridge.seqStepRecordEnabled);
                    }
                }
            }

            Rectangle { width: 1; height: ScaleMetrics.dp(20); color: Theme.borderCard }

            // Switch to Live Session Matrix
            Rectangle {
                height: ScaleMetrics.dp(28)
                width: ScaleMetrics.dp(105)
                radius: 4
                color: Theme.bgApp
                border.color: Theme.pageAccent
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: ScaleMetrics.dp(4)
                    Icon { name: "screens"; size: 12; color: Theme.pageAccent }
                    Text {
                        text: "LIVE MATRIX"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Theme.pageAccent
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: Bridge.setActiveView("LIVE")
                }
            }
        }

        // Notes mode: rows 2-5. Motion mode (automation lanes) replaces them.
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: !Bridge.seqMotionMode
            spacing: ScaleMetrics.dp(6)

            // =====================================================================
            // 2. TRACK SELECTION STRIP & TRACK SETTINGS
            // =====================================================================
            RowLayout {
                Layout.fillWidth: true
                spacing: ScaleMetrics.dp(6)

                // Track Tabs (long-press to rename)
                RowLayout {
                    spacing: ScaleMetrics.dp(3)
                    Repeater {
                        model: Bridge.seqTracks ? Bridge.seqTracks.length : 0
                        delegate: SpButton {
                            readonly property string trackName: Bridge.seqTracks[index] ? Bridge.seqTracks[index].name : ""
                            implicitHeight: ScaleMetrics.dp(26)
                            implicitWidth: ScaleMetrics.dp(58)
                            text: trackName
                            fontSize: 8
                            variant: "outline"
                            accent: root.trackColors[index]
                            checked: Bridge.seqActiveTrack === index
                            onClicked: Bridge.seqSelectTrack(index)
                            onPressAndHold: {
                                Bridge.seqSelectTrack(index);
                                trackRename.openTrack(index, trackName);
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

                // Layers: extra parts this track also sends to (tap to edit).
                // Grows into the free space before DIV / SWING / DICE; elides past that.
                SpButton {
                    id: layerChip
                    objectName: "layerChip"
                    readonly property var layers: (root.activeTrackData && root.activeTrackData.layerParts) ? root.activeTrackData.layerParts : []
                    implicitHeight: ScaleMetrics.dp(30)
                    Layout.fillWidth: true
                    Layout.preferredWidth: label.implicitWidth + ScaleMetrics.dp(16)
                    Layout.maximumWidth: label.implicitWidth + ScaleMetrics.dp(16)
                    text: layerChip.layers.length > 0 ? "+ " + root.formatParts(layerChip.layers) : "+ LAYER"
                    fontSize: 8
                    variant: layers.length > 0 ? "outline" : "neutral"
                    accent: root.currentTrackColor
                    checked: partPicker.visible
                    onClicked: partPicker.open(Bridge.seqActiveTrack, "layers", layerChip)
                }

                // DIV, SWING and DICE sit at the right edge
                Item { Layout.fillWidth: true }

                // Clock Divider (ordered shortest -> longest step)
                SeqStepper {
                    readonly property var divs: ["1/32", "1/16T", "1/16", "1/8T", "1/8", "1/4"]
                    label: "DIV:"
                    count: divs.length
                    index: Math.max(0, divs.indexOf(root.activeTrackData ? root.activeTrackData.clockDivider : "1/16"))
                    valueText: divs[index]
                    valueColor: Theme.pageAccent
                    pxPerStep: ScaleMetrics.dp(18)
                    onRequested: (i) => Bridge.seqSetTrackClockDivider(Bridge.seqActiveTrack, divs[i])
                }

                // Swing: 50% = straight, 66% ≈ triplet shuffle, 75% = hard swing (1% steps)
                SeqStepper {
                    label: "SWING:"
                    count: 26
                    index: Math.round(((root.activeTrackData ? root.activeTrackData.swing : 0.50) - 0.50) * 100)
                    valueText: (50 + index) + "%"
                    valueColor: Theme.pageAccent
                    pxPerStep: ScaleMetrics.dp(8)
                    onRequested: (i) => Bridge.seqSetTrackSwing(Bridge.seqActiveTrack, 0.50 + i / 100)
                }

                // Dice (humanize): random timing / velocity per note (tap to edit)
                SpButton {
                    id: diceChip
                    objectName: "diceChip"
                    readonly property bool on: root.activeTrackData ? (root.activeTrackData.diceTiming > 0 || root.activeTrackData.diceVelocity > 0) : false
                    implicitHeight: ScaleMetrics.dp(30)
                    implicitWidth: ScaleMetrics.dp(56)
                    text: "DICE"
                    fontSize: 8
                    variant: on ? "outline" : "neutral"
                    accent: root.currentTrackColor
                    checked: dicePicker.visible
                    onClicked: dicePicker.open(Bridge.seqActiveTrack, diceChip)
                }
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
                                color: playing ? Theme.playing : Theme.warning
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
                    valueColor: Theme.pageAccent
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
                        delegate: SpButton {
                            implicitHeight: ScaleMetrics.dp(26)
                            implicitWidth: ScaleMetrics.dp(42)
                            text: ((index * 16) + 1) + "-" + ((index + 1) * 16)
                            fontSize: 8
                            accent: root.currentTrackColor
                            checked: root.currentStepPage === index
                            onClicked: root.currentStepPage = index
                        }
                    }
                }

                Item { Layout.fillWidth: true }

                // Clear Clip Button
                Rectangle {
                    height: ScaleMetrics.dp(26)
                    width: ScaleMetrics.dp(95)
                    radius: 3
                    color: clearClipMouse.pressed ? Theme.tint(Theme.recording, 0.35) : Theme.bgApp
                    border.color: clearClipMouse.containsPress ? Theme.recording : Theme.borderCard
                    border.width: 1

                    RowLayout {
                        anchors.centerIn: parent
                        spacing: ScaleMetrics.dp(4)
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
            // 4. 16-STEP GRID MATRIX (2 Rows of 8 Steps) or PIANO ROLL
            // =====================================================================
            SeqPianoRoll {
                Layout.fillWidth: true
                Layout.fillHeight: true
                visible: root.rollView
                stepsList: root.stepsList
                page: root.currentStepPage
                trackColor: root.currentTrackColor
                isDrum: root.isDrumTrack
                playhead: Bridge.seqIsPlaying ? root.currentPlayhead : -1
                cursorStep: Bridge.seqStepRecordEnabled ? Bridge.seqCursorStep : -1
                selectedStep: root.selectedStepIdx
                selectedPitch: root.selNote ? root.selNote.pitch : -1
                pitchLabel: (p) => root.formatPitch(p, root.isDrumTrack)
                onNoteSelected: (step, pitch) => root.selectNote(step, pitch)
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                visible: !root.rollView
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
                        color: Bridge.seqStepRecordEnabled ? Theme.tint(Theme.recording, 0.25) : Theme.bgSurface
                        border.color: Bridge.seqStepRecordEnabled ? Theme.recording : Theme.borderCard
                        border.width: 1

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: ScaleMetrics.dp(3)
                            spacing: ScaleMetrics.dp(2)

                            Text {
                                text: Bridge.seqStepRecordEnabled ? "STEP REC CURSOR: " + (Bridge.seqCursorStep + 1) : "STEP REC: OFF"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(8)
                                color: Bridge.seqStepRecordEnabled ? Theme.recording : Theme.textDim
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                spacing: ScaleMetrics.dp(3)

                                SpButton {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    text: "REST"
                                    fontSize: 10
                                    onClicked: Bridge.seqRecordRest()
                                }

                                SpButton {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    text: "TIE"
                                    fontSize: 10
                                    onClicked: Bridge.seqRecordTie()
                                }

                                SpButton {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    text: "CLEAR"
                                    fontSize: 10
                                    variant: "danger"
                                    onClicked: Bridge.seqClearStep(Bridge.seqCursorStep)
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                spacing: ScaleMetrics.dp(3)
                                SpButton {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    icon: "left"
                                    text: "PREV"
                                    onClicked: Bridge.seqSetCursorStep(Math.max(0, Bridge.seqCursorStep - 1))
                                }
                                SpButton {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    icon: "right"
                                    iconAfter: true
                                    text: "NEXT"
                                    onClicked: Bridge.seqSetCursorStep(Bridge.seqCursorStep + 1)
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
                            valStr: root.selNote ? root.formatPitch(root.selNote.pitch, root.isDrumTrack) : "--"
                            accent: Theme.pageAccent
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
                                    visible: root.isDrumTrack
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    spacing: 2
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        spacing: 2
                                        Repeater {
                                            model: [ { name: "BD", p: 36 }, { name: "SD", p: 38 }, { name: "CH", p: 42 } ]
                                            delegate: SpButton {
                                                Layout.fillWidth: true
                                                Layout.fillHeight: true
                                                text: modelData.name
                                                checked: (root.selNote && root.selNote.pitch === modelData.p)
                                                onClicked: root.setSelNotePitch(modelData.p)
                                            }
                                        }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        spacing: 2
                                        Repeater {
                                            model: [ { name: "OH", p: 46 }, { name: "CP", p: 39 }, { name: "CY", p: 49 } ]
                                            delegate: SpButton {
                                                Layout.fillWidth: true
                                                Layout.fillHeight: true
                                                text: modelData.name
                                                checked: (root.selNote && root.selNote.pitch === modelData.p)
                                                onClicked: root.setSelNotePitch(modelData.p)
                                            }
                                        }
                                    }
                                }

                                // Melodic Tracks: -1, +1, -OCT, +OCT
                                ColumnLayout {
                                    visible: !root.isDrumTrack
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    spacing: 2
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        spacing: 2
                                        SpButton {
                                            Layout.fillWidth: true
                                            Layout.fillHeight: true
                                            text: "-1"
                                            fontSize: 10
                                            onClicked: root.nudgeSelNote(-1)
                                        }
                                        SpButton {
                                            Layout.fillWidth: true
                                            Layout.fillHeight: true
                                            text: "+1"
                                            fontSize: 10
                                            onClicked: root.nudgeSelNote(1)
                                        }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        spacing: 2
                                        SpButton {
                                            Layout.fillWidth: true
                                            Layout.fillHeight: true
                                            text: "-OCT"
                                            variant: "outline"
                                            onClicked: root.nudgeSelNote(-12)
                                        }
                                        SpButton {
                                            Layout.fillWidth: true
                                            Layout.fillHeight: true
                                            text: "+OCT"
                                            variant: "outline"
                                            onClicked: root.nudgeSelNote(12)
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
                            accent: Theme.pageAccent
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
                            accent: Theme.pageAccent
                            onAdjust: (delta) => {
                                if (selStep) {
                                    const curr = selStep.microTiming || 0;
                                    Bridge.seqSetStepParam(root.selectedStepIdx, "microTiming", Math.max(-24, Math.min(24, curr + delta)));
                                }
                            }
                        }

                        // Strum: ticks between a chord's notes (↑ low -> high, ↓ high -> low); a flam on drums
                        InspectorParam {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            title: "STRUM"
                            valStr: selStep && selStep.strum ? (selStep.strum > 0 ? "↑" : "↓") + Math.abs(selStep.strum) + "t" : "OFF"
                            accent: Theme.pageAccent
                            onAdjust: (delta) => {
                                if (selStep) {
                                    const curr = selStep.strum || 0;
                                    Bridge.seqSetStepParam(root.selectedStepIdx, "strum", Math.max(-24, Math.min(24, curr + delta)));
                                }
                            }
                        }

                        // Probability
                        InspectorParam {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            title: "PROB"
                            valStr: selStep ? Math.round(selStep.probability * 100) + "%" : "100%"
                            accent: Theme.pageAccent
                            onAdjust: (delta) => {
                                if (selStep) {
                                    const curr = selStep.probability || 1.0;
                                    Bridge.seqSetStepParam(root.selectedStepIdx, "probability", Math.max(0.0, Math.min(1.0, curr + delta * 0.1)));
                                }
                            }
                        }

                        // Length: steps the selected note is held (a tie, per note)
                        InspectorParam {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            title: "LENGTH"
                            valStr: root.selNote ? root.selNote.length + (root.selNote.length === 1 ? " STEP" : " STEPS") : "--"
                            accent: Theme.pageAccent
                            lit: root.selNote !== null && root.selNote.length > 1
                            onAdjust: (delta) => {
                                if (root.selNote)
                                    Bridge.seqSetNoteLength(root.selectedStepIdx, root.selNote.pitch, root.selNote.length + delta);
                            }
                        }

                        // Clear Step
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: ScaleMetrics.dp(4)
                            color: clearStepMouse.pressed ? Theme.tint(Theme.recording, 0.35) : Theme.bgSurface
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

        SeqMotionView {
            id: motionView
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: Bridge.seqMotionMode
        }
    }

    // Main part / layers picker (opened from the LAYER chip)
    PartPicker {
        id: partPicker
    }

    // Dice (humanize) settings (opened from the DICE chip)
    DicePicker {
        id: dicePicker
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
                        : ((stepOffset % 4 === 0) ? Theme.bgCardActive : Theme.bgSurface)
        border.color: isCurrentPlayhead ? Theme.textPrimary
                                        : (isCursorStep ? Theme.recording
                                                        : (isSelected ? root.currentTrackColor : Theme.borderCard))
        border.width: (isCurrentPlayhead || isCursorStep || isSelected) ? 2 : 1

        readonly property var notes: (stepData && stepData.notes) ? stepData.notes : []
        readonly property bool isDrum: root.isDrumTrack

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
                    color: (stepOffset % 4 === 0) ? Theme.pageAccent : Theme.textSecondary
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
                // Notes from earlier steps are still held here
                Text {
                    visible: stepData && stepData.held > 0
                    text: "—"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(10)
                    color: Theme.pageAccent
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
                        // Held past its step (length > 1)
                        Rectangle {
                            visible: cell.note !== null && cell.note.length > 1
                            anchors.bottom: parent.bottom
                            anchors.horizontalCenter: parent.horizontalCenter
                            width: parent.width * 0.6
                            height: 2
                            color: cell.isSel ? Theme.bgApp : root.currentTrackColor
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
                    color: isCurrentPlayhead ? Theme.textPrimary : root.currentTrackColor
                }
            }
        }
    }

    RenameModal {
        id: trackRename
    }
}
