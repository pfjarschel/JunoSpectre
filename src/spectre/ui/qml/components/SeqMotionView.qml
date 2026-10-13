pragma ValueTypeBehavior: Copy
import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

// Sequencer page, MOTION mode: the 8 automation lanes. Same layout as the
// note tracks (lane strip, clip strip, grid, inspector), but each lane drives
// one parameter: the grid paints values, the inspector edits value / glide.
Item {
    id: root

    property int selectedStepIdx: 0
    property int currentStepPage: 0

    readonly property int laneIdx: Bridge.seqActiveLane
    readonly property var lanes: Bridge.seqAutomationLanes || []
    readonly property var lane: lanes.length > laneIdx ? lanes[laneIdx] : null
    readonly property color laneColor: Theme.trackColors[laneIdx % Theme.trackColors.length]
    readonly property bool linked: lane ? lane.linkTrack >= 0 : false
    readonly property bool hasTarget: lane ? lane.target !== "" : false
    readonly property string recState: Bridge.seqLaneRecStates.length > laneIdx ? Bridge.seqLaneRecStates[laneIdx] : ""
    readonly property bool stepRec: Bridge.seqLaneStepRec
    readonly property int cursor: stepRec ? Bridge.seqLaneCursor : -1
    // The selection follows the step-record cursor (VALUE shows what it records)
    onCursorChanged: if (cursor >= 0) {
        selectedStepIdx = cursor;
        currentStepPage = Math.floor(cursor / 16);
    }
    readonly property real load: Bridge.seqAutomationLoad
    readonly property real budget: Bridge.seqAutomationBudget

    property var steps: []
    function refresh() { steps = Bridge.seqLaneSteps(Bridge.seqActiveLane); }
    Component.onCompleted: refresh()
    Connections {
        target: Bridge
        function onSeqAutomationChanged() { root.refresh(); }
        function onSeqActiveLaneChanged() { root.refresh(); }
    }

    readonly property int stepPageCount: Math.max(1, Math.ceil((steps.length || 16) / 16))
    onStepPageCountChanged: if (currentStepPage >= stepPageCount) currentStepPage = 0
    readonly property var selStep: steps.length > selectedStepIdx ? steps[selectedStepIdx] : null
    // The playhead shows only on the clip that is playing
    readonly property int playhead: (Bridge.seqIsPlaying && lane && lane.activeClipIdx === lane.selectedClipIdx
                                     && Bridge.seqLanePlayheads.length > laneIdx)
                                    ? Bridge.seqLanePlayheads[laneIdx] : -1

    function formatParts(parts) {
        return parts.map(p => "P" + p).join("+");
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: ScaleMetrics.dp(6)

        // =====================================================================
        // LANE STRIP & LANE SETTINGS
        // =====================================================================
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(6)

            RowLayout {
                spacing: ScaleMetrics.dp(3)
                Repeater {
                    model: root.lanes.length
                    delegate: SpButton {
                        readonly property var laneData: root.lanes[index]
                        implicitHeight: ScaleMetrics.dp(26)
                        implicitWidth: ScaleMetrics.dp(58)
                        text: laneData && laneData.tabName ? laneData.tabName : "LANE " + (index + 1)
                        fontSize: 8
                        variant: laneData && laneData.target ? "outline" : "neutral"
                        accent: Theme.trackColors[index % Theme.trackColors.length]
                        checked: root.laneIdx === index
                        onClicked: Bridge.seqSelectLane(index)

                        // Armed (ring) / recording (solid)
                        Rectangle {
                            readonly property string rec: Bridge.seqLaneRecStates.length > index
                                                          ? Bridge.seqLaneRecStates[index] : ""
                            visible: rec !== ""
                            anchors.top: parent.top
                            anchors.right: parent.right
                            anchors.margins: ScaleMetrics.dp(3)
                            width: ScaleMetrics.dp(6)
                            height: width
                            radius: width / 2
                            color: rec === "recording" ? Theme.recording : "transparent"
                            border.color: Theme.recording
                            border.width: 1
                        }
                    }
                }
            }

            Rectangle { width: 1; height: ScaleMetrics.dp(20); color: Theme.borderCard }

            // The parameter (opens the browser)
            SpButton {
                id: targetChip
                Layout.fillWidth: true
                Layout.minimumWidth: ScaleMetrics.dp(80)
                implicitHeight: ScaleMetrics.dp(30)
                text: root.hasTarget ? root.lane.title : "+ PARAMETER"
                fontSize: 8
                variant: root.hasTarget ? "outline" : "neutral"
                accent: root.laneColor
                checked: targetPicker.visible
                onClicked: targetPicker.open(root.laneIdx + 1, root.laneColor)
            }

            // Follow a note track's clip launches (and its parts)
            SeqStepper {
                label: "LINK:"
                count: 9
                index: root.lane ? root.lane.linkTrack + 1 : 0
                valueText: index === 0 ? "OFF" : "T" + index
                valueColor: index === 0 ? Theme.textSecondary : Theme.trackColors[(index - 1) % Theme.trackColors.length]
                pxPerStep: ScaleMetrics.dp(14)
                onRequested: (i) => Bridge.seqSetLaneLink(root.laneIdx, i - 1)
            }

            // Parts a part-scoped parameter is written to; a linked lane uses its track's
            SpButton {
                id: partsChip
                readonly property var parts: root.lane ? [root.lane.targetPart].concat(root.lane.layerParts) : []
                implicitHeight: ScaleMetrics.dp(30)
                implicitWidth: Math.max(ScaleMetrics.dp(56), label.implicitWidth + ScaleMetrics.dp(16))
                visible: root.lane ? root.lane.partScoped : false
                enabled: !root.linked
                text: root.formatParts(parts)
                fontSize: 8
                variant: "outline"
                accent: root.laneColor
                checked: partPicker.visible
                onClicked: partPicker.open(root.laneIdx, "main", partsChip)
            }

            SeqStepper {
                readonly property var divs: ["1/32", "1/16T", "1/16", "1/8T", "1/8", "1/4"]
                label: "DIV:"
                count: divs.length
                index: Math.max(0, divs.indexOf(root.lane ? root.lane.clockDivider : "1/16"))
                valueText: divs[index]
                valueColor: Theme.pageAccent
                pxPerStep: ScaleMetrics.dp(18)
                onRequested: (i) => Bridge.seqSetLaneDivider(root.laneIdx, divs[i])
            }
        }

        // =====================================================================
        // CLIP STRIP
        // =====================================================================
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(6)

            RowLayout {
                spacing: ScaleMetrics.dp(3)
                Repeater {
                    model: 8
                    delegate: Rectangle {
                        readonly property bool isSel: root.lane && root.lane.selectedClipIdx === index
                        readonly property var clip: root.lane && root.lane.clips.length > index ? root.lane.clips[index] : null
                        height: ScaleMetrics.dp(26)
                        width: ScaleMetrics.dp(36)
                        radius: 3
                        color: isSel ? Theme.bgCardActive : Theme.bgApp
                        border.color: isSel ? root.laneColor : Theme.borderCard
                        border.width: isSel ? 2 : 1

                        Text {
                            anchors.centerIn: parent
                            text: "C" + (index + 1)
                            font.bold: parent.isSel || (parent.clip && parent.clip.hasValues)
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: parent.isSel ? root.laneColor
                                   : (parent.clip && parent.clip.hasValues ? Theme.textSecondary : Theme.textDim)
                        }
                        // Playing (green) / queued (amber), the linked track's for a linked lane
                        Rectangle {
                            readonly property bool playing: Bridge.seqIsPlaying && root.lane && root.lane.activeClipIdx === index
                            readonly property bool queued: root.lane && root.lane.queuedClipIdx === index
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
                                Bridge.seqSelectLaneClip(root.laneIdx, index);
                                // Unlinked lanes play the clip they edit, like note tracks;
                                // a linked lane plays what its track plays.
                                if (!root.linked) Bridge.seqLaunchLaneClip(root.laneIdx, index);
                            }
                        }
                    }
                }
            }

            Rectangle { width: 1; height: ScaleMetrics.dp(20); color: Theme.borderCard }

            SeqStepper {
                readonly property var lens: [16, 32, 64, 128]
                label: "LEN:"
                count: lens.length
                index: Math.max(0, lens.indexOf(root.steps.length || 16))
                valueText: lens[index] + "S"
                valueColor: Theme.pageAccent
                pxPerStep: ScaleMetrics.dp(20)
                onRequested: (i) => {
                    root.currentStepPage = 0;
                    Bridge.seqSetLaneClipLength(root.laneIdx, lens[i]);
                }
            }

            Rectangle { width: 1; height: ScaleMetrics.dp(20); color: Theme.borderCard }

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
                        accent: root.laneColor
                        checked: root.currentStepPage === index
                        onClicked: root.currentStepPage = index
                    }
                }
            }

            Item { Layout.fillWidth: true }

            // Loop recording status of this lane
            Text {
                visible: root.recState !== ""
                text: root.recState === "recording" ? "RECORDING ONE LOOP…" : "REC ARMED · MOVE THE PARAMETER"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(8)
                color: Theme.recording
            }

            // Estimated SysEx load of all lanes: amber past 80% of the budget, red past it
            RowLayout {
                spacing: ScaleMetrics.dp(4)
                Text {
                    text: "LOAD"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: Theme.textDim
                }
                Rectangle {
                    Layout.preferredWidth: ScaleMetrics.dp(70)
                    height: ScaleMetrics.dp(8)
                    radius: 2
                    color: Theme.bgApp
                    border.color: Theme.borderCard
                    border.width: 1
                    Rectangle {
                        readonly property real frac: root.budget > 0 ? root.load / root.budget : 0
                        width: parent.width * Math.min(1, frac)
                        height: parent.height
                        radius: 2
                        color: frac > 1 ? Theme.recording : (frac > 0.8 ? Theme.warning : Theme.playing)
                    }
                }
                Text {
                    text: Math.round(root.load) + "/" + Math.round(root.budget) + " msg/s"
                    font.family: Theme.fontMono
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: root.load > root.budget ? Theme.recording : Theme.textSecondary
                }
            }

            SpButton {
                implicitHeight: ScaleMetrics.dp(26)
                implicitWidth: ScaleMetrics.dp(95)
                text: "CLEAR CLIP"
                fontSize: 8
                variant: "danger"
                onClicked: Bridge.seqClearLaneClip(root.laneIdx)
            }
        }

        // =====================================================================
        // VALUE GRID: drag to paint, double-tap a step to empty it
        // =====================================================================
        Rectangle {
            id: gridBox
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: ScaleMetrics.dp(6)
            color: Theme.bgApp
            border.color: Theme.borderCard
            border.width: 1

            readonly property real pad: ScaleMetrics.dp(6)
            readonly property real numbersH: ScaleMetrics.dp(18)

            Item {
                id: graph
                anchors.fill: parent
                anchors.margins: gridBox.pad
                anchors.bottomMargin: gridBox.pad + gridBox.numbersH
                readonly property real colW: width / 16

                // Step columns: beat shading, selection, playhead, set values
                Repeater {
                    model: 16
                    delegate: Rectangle {
                        readonly property int stepIdx: root.currentStepPage * 16 + index
                        readonly property var step: root.steps.length > stepIdx ? root.steps[stepIdx] : null
                        readonly property bool isSet: step !== null && step.value >= 0
                        x: index * graph.colW + 1
                        width: graph.colW - 2
                        height: graph.height
                        radius: 3
                        visible: step !== null
                        color: stepIdx === root.playhead ? Theme.tint(Theme.textPrimary, 0.12)
                               : (stepIdx % 4 === 0 ? Theme.bgCardActive : Theme.bgSurface)
                        border.color: stepIdx === root.playhead ? Theme.textPrimary
                                      : stepIdx === root.cursor ? Theme.recording
                                      : (stepIdx === root.selectedStepIdx ? root.laneColor : "transparent")
                        border.width: (stepIdx === root.playhead || stepIdx === root.cursor
                                       || stepIdx === root.selectedStepIdx) ? 2 : 0

                        // A set step: bar up to its value
                        Rectangle {
                            visible: parent.isSet
                            anchors.bottom: parent.bottom
                            anchors.horizontalCenter: parent.horizontalCenter
                            width: parent.width * 0.5
                            height: parent.isSet ? Math.max(2, parent.step.value * parent.height) : 0
                            radius: 2
                            color: Theme.tint(root.laneColor, 0.35)
                            border.color: root.laneColor
                            border.width: 1
                        }
                    }
                }

                // What plays: flat holds, sloped glides (the engine's own curve)
                Canvas {
                    id: curve
                    anchors.fill: parent
                    property var steps: root.steps
                    property int page: root.currentStepPage
                    property color stroke: root.laneColor
                    onStepsChanged: requestPaint()
                    onPageChanged: requestPaint()
                    onStrokeChanged: requestPaint()
                    onWidthChanged: requestPaint()
                    onHeightChanged: requestPaint()
                    onPaint: {
                        const ctx = getContext("2d");
                        ctx.reset();
                        const w = width / 16;
                        ctx.strokeStyle = stroke;
                        ctx.lineWidth = ScaleMetrics.dp(2);
                        ctx.beginPath();
                        let drawing = false;
                        for (let i = 0; i < 16; i++) {
                            const s = steps[page * 16 + i];
                            if (!s || s.start < 0) { drawing = false; continue; }
                            const y0 = height * (1 - s.start), y1 = height * (1 - s.end);
                            if (drawing) ctx.lineTo(i * w, y0); else ctx.moveTo(i * w, y0);
                            ctx.lineTo((i + 1) * w, y1);
                            drawing = true;
                        }
                        ctx.stroke();
                    }
                }

                Text {
                    anchors.centerIn: parent
                    visible: !root.hasTarget
                    text: "PICK A PARAMETER TO AUTOMATE"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(10)
                    font.letterSpacing: 1.0
                    color: Theme.textDim
                }

                MouseArea {
                    id: paint
                    anchors.fill: parent
                    preventStealing: true
                    property int lastStep: -1

                    function stepAt(mx) {
                        const i = root.currentStepPage * 16 + Math.max(0, Math.min(15, Math.floor(mx / graph.colW)));
                        return i < root.steps.length ? i : -1;
                    }
                    function paintAt(mx, my) {
                        const i = stepAt(mx);
                        if (i < 0) return;
                        const v = Math.max(0, Math.min(1, 1 - my / height));
                        root.selectedStepIdx = i;
                        if (root.stepRec) Bridge.seqSetLaneCursor(i);
                        lastStep = i;
                        Bridge.seqSetLaneStep(root.laneIdx, i, v);
                    }
                    onPressed: (mouse) => paintAt(mouse.x, mouse.y)
                    onPositionChanged: (mouse) => { if (pressed) paintAt(mouse.x, mouse.y); }
                    onDoubleClicked: (mouse) => {
                        const i = stepAt(mouse.x);
                        if (i >= 0) Bridge.seqSetLaneStep(root.laneIdx, i, -1);
                    }
                }
            }

            // Step numbers: tap to select a step without changing it
            Row {
                anchors.left: graph.left
                anchors.right: graph.right
                anchors.top: graph.bottom
                height: gridBox.numbersH
                Repeater {
                    model: 16
                    delegate: Item {
                        readonly property int stepIdx: root.currentStepPage * 16 + index
                        width: graph.colW
                        height: parent.height
                        visible: stepIdx < root.steps.length
                        Text {
                            anchors.centerIn: parent
                            text: (parent.stepIdx + 1).toString()
                            font.family: Theme.fontMono
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(9)
                            color: parent.stepIdx === root.selectedStepIdx ? root.laneColor
                                   : (parent.stepIdx % 4 === 0 ? Theme.pageAccent : Theme.textSecondary)
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                root.selectedStepIdx = parent.stepIdx;
                                if (root.stepRec) Bridge.seqSetLaneCursor(parent.stepIdx);
                            }
                        }
                    }
                }
            }
        }

        // =====================================================================
        // LANE SUMMARY, LOAD & STEP INSPECTOR
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

                // Step recording: cursor controls, always here like the note tracks' step recorder
                Rectangle {
                    Layout.preferredWidth: ScaleMetrics.dp(250)
                    Layout.fillHeight: true
                    radius: ScaleMetrics.dp(4)
                    color: root.stepRec ? Theme.tint(Theme.recording, 0.25) : Theme.bgSurface
                    border.color: root.stepRec ? Theme.recording : Theme.borderCard
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: ScaleMetrics.dp(3)
                        spacing: ScaleMetrics.dp(2)

                        Text {
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                            text: root.stepRec ? "STEP REC CURSOR: " + (root.cursor + 1) + " · MOVE THE PARAMETER"
                                               : "STEP REC: OFF"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: root.stepRec ? Theme.recording : Theme.textDim
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            spacing: ScaleMetrics.dp(3)
                            enabled: root.stepRec
                            SpButton {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                icon: "left"
                                text: "PREV"
                                onClicked: Bridge.seqMoveLaneCursor(-1)
                            }
                            SpButton {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                text: "CLEAR"
                                variant: "danger"
                                onClicked: Bridge.seqSetLaneStep(root.laneIdx, root.cursor, -1)
                            }
                            SpButton {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                icon: "right"
                                iconAfter: true
                                text: "NEXT"
                                onClicked: Bridge.seqMoveLaneCursor(1)
                            }
                        }
                    }
                }

                InspectorParam {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    title: "VALUE"
                    valStr: root.selStep && root.selStep.value >= 0
                            ? Bridge.seqLaneValueText(root.laneIdx, root.selStep.value) : "--"
                    accent: root.laneColor
                    onAdjust: (delta) => {
                        const v = root.selStep && root.selStep.value >= 0 ? root.selStep.value
                                  : (root.selStep && root.selStep.start >= 0 ? root.selStep.start : 0.5);
                        Bridge.seqSetLaneStep(root.laneIdx, root.selectedStepIdx,
                                              Math.max(0, Math.min(1, v + delta / 127)));
                    }
                }

                // Ramp from this value to the next set step's
                InspectorParam {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    title: "GLIDE"
                    readonly property bool on: root.selStep ? root.selStep.glide : false
                    valStr: on ? "ON" : "OFF"
                    lit: on
                    accent: Theme.pageAccent
                    enabled: root.selStep ? root.selStep.value >= 0 : false
                    opacity: enabled ? 1.0 : Theme.disabledOpacity
                    onTapped: Bridge.seqSetLaneStepGlide(root.laneIdx, root.selectedStepIdx, !on)
                }

                InspectorParam {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    title: "STEP"
                    valStr: "CLEAR"
                    accent: Theme.recording
                    onTapped: Bridge.seqSetLaneStep(root.laneIdx, root.selectedStepIdx, -1)
                }

                // Fill the clip with a shape
                Rectangle {
                    Layout.preferredWidth: ScaleMetrics.dp(200)
                    Layout.fillHeight: true
                    radius: ScaleMetrics.dp(4)
                    color: Theme.bgSurface
                    border.color: Theme.borderCard
                    border.width: 1

                    GridLayout {
                        anchors.fill: parent
                        anchors.margins: ScaleMetrics.dp(3)
                        columns: 3
                        rowSpacing: ScaleMetrics.dp(2)
                        columnSpacing: ScaleMetrics.dp(2)
                        Repeater {
                            model: ["RAMP UP", "RAMP DN", "TRI", "SINE", "SQUARE", "RANDOM"]
                            delegate: SpButton {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                text: modelData
                                fontSize: 8
                                onClicked: Bridge.seqLaneShape(root.laneIdx, modelData)
                            }
                        }
                    }
                }
            }
        }
    }

    PartPicker {
        id: partPicker
        laneMode: true
    }

    MacroTargetPicker {
        id: targetPicker
        laneMode: true
        assignedKeys: root.lane && root.lane.target ? [root.lane.target] : []
        onAddRequested: (key) => {
            targetPicker.close();
            Bridge.seqSetLaneTarget(root.laneIdx, key);
        }
        onCloseRequested: targetPicker.close()
    }
}
