pragma ValueTypeBehavior: Copy
import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

// Piano roll of one 16-step page of the selected clip. Tap a free cell to add a
// one-step note, tap a note to select it, double-tap a note to delete it, drag
// sideways to set a note's length (from a free cell: add it and draw its length).
// Drag up/down to scroll the pitches. Values are edited in the inspector below.
Rectangle {
    id: roll

    property var stepsList: []
    property int page: 0
    property color trackColor: Theme.pageAccent
    property bool isDrum: false
    property int playhead: -1          // -1 when not playing
    property int cursorStep: -1        // step-record cursor, -1 when off
    property int selectedStep: -1
    property int selectedPitch: -1
    property var pitchLabel: (p) => String(p)
    signal noteSelected(int step, int pitch)

    readonly property int pageStart: page * 16
    readonly property int clipLength: stepsList ? stepsList.length : 0
    readonly property real keyWidth: ScaleMetrics.dp(40)
    readonly property real headerHeight: ScaleMetrics.dp(14)
    readonly property real gridWidth: Math.max(1, width - keyWidth)
    readonly property real colWidth: gridWidth / 16
    readonly property int visibleRows: Math.max(4, Math.floor((height - headerHeight) / ScaleMetrics.dp(22)))
    readonly property real rowHeight: (height - headerHeight) / visibleRows
    // Pitch in the middle of the view (kept when the height changes); rows run down from topPitch
    property int centerPitch: 66
    readonly property int topPitch: Math.max(visibleRows - 1, Math.min(127, Math.round(centerPitch + visibleRows / 2)))
    readonly property int bottomPitch: topPitch - visibleRows + 1

    // Every note of the clip as {step, pitch, length, velocity, gate}
    readonly property var clipNotes: {
        const out = [];
        const steps = stepsList || [];
        for (let i = 0; i < steps.length; i++) {
            const notes = steps[i].notes || [];
            for (let j = 0; j < notes.length; j++)
                out.push({ step: i, pitch: notes[j].pitch, length: Math.min(notes[j].length, steps.length - i),
                           velocity: notes[j].velocity, gate: steps[i].gateLength });
        }
        return out;
    }
    // Notes reaching into this page
    readonly property var pageNotes: clipNotes.filter(n => n.step < pageStart + 16 && n.step + n.length > pageStart)

    function isBlack(p) { return [1, 3, 6, 8, 10].indexOf(p % 12) >= 0; }

    // Scroll so the view's middle lands on pitch p (within 0..127)
    function scrollTo(p) {
        centerPitch = Math.max(Math.floor(visibleRows / 2), Math.min(127 - Math.ceil(visibleRows / 2), Math.round(p)));
    }

    // Show the clip's notes (or a default range) centred
    function fitToNotes() {
        let lo = 128, hi = -1;
        for (let i = 0; i < clipNotes.length; i++) {
            lo = Math.min(lo, clipNotes[i].pitch);
            hi = Math.max(hi, clipNotes[i].pitch);
        }
        if (hi < 0) { lo = isDrum ? 35 : 60; hi = isDrum ? 51 : 72; }
        scrollTo((lo + hi) / 2);
    }

    // Refit when shown and when another track or clip is picked (not on edits)
    property string fitKey: ""
    function refit(force) {
        const key = Bridge.seqActiveTrack + ":" + Bridge.seqActiveClip;
        if (force || key !== fitKey) {
            fitKey = key;
            Qt.callLater(fitToNotes);  // after stepsList follows the new clip
        }
    }
    onVisibleChanged: if (visible) refit(true)
    Connections {
        target: Bridge
        function onSeqActiveTrackChanged() { if (roll.visible) roll.refit(false); }
        function onSeqActiveClipChanged() { if (roll.visible) roll.refit(false); }
    }

    // The note sounding at (step, pitch), or null
    function noteAt(step, pitch) {
        for (let i = 0; i < clipNotes.length; i++) {
            const n = clipNotes[i];
            if (n.pitch === pitch && n.step <= step && step < n.step + n.length) return n;
        }
        return null;
    }

    radius: ScaleMetrics.dp(6)
    color: Theme.bgApp
    border.color: Theme.borderCard
    border.width: 1
    clip: true

    // Step numbers
    Repeater {
        model: 16
        delegate: Text {
            x: roll.keyWidth + index * roll.colWidth
            width: roll.colWidth
            height: roll.headerHeight
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            text: roll.pageStart + index + 1
            font.family: Theme.fontMono
            font.bold: index % 4 === 0
            font.pixelSize: ScaleMetrics.sp(Theme.fontXs)
            color: index % 4 === 0 ? Theme.pageAccent : Theme.textDim
            opacity: roll.pageStart + index < roll.clipLength ? 1 : 0.3
        }
    }

    // Pitch rows: key label + lane
    Repeater {
        model: roll.visibleRows
        delegate: Item {
            readonly property int pitch: roll.topPitch - index
            readonly property bool black: !roll.isDrum && roll.isBlack(pitch)
            y: roll.headerHeight + index * roll.rowHeight
            width: roll.width
            height: roll.rowHeight

            Rectangle {
                width: roll.keyWidth - 2
                height: parent.height - 1
                color: parent.black ? Theme.keyBlack : Theme.bgControl
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left
                    anchors.leftMargin: ScaleMetrics.dp(4)
                    text: roll.pitchLabel(parent.parent.pitch)
                    font.family: Theme.fontMono
                    font.bold: parent.parent.pitch % 12 === 0
                    font.pixelSize: ScaleMetrics.sp(Theme.fontXs)
                    color: parent.parent.pitch % 12 === 0 && !roll.isDrum ? Theme.textPrimary : Theme.textMuted
                }
            }
            Rectangle {
                x: roll.keyWidth
                width: roll.gridWidth
                height: parent.height - 1
                color: parent.black ? Theme.bgTrack : Theme.bgSurface
            }
        }
    }

    // Beat lines (bold every 4 steps), cursor and playhead columns
    Repeater {
        model: 16
        delegate: Rectangle {
            x: roll.keyWidth + index * roll.colWidth
            y: roll.headerHeight
            width: index % 4 === 0 ? 2 : 1
            height: roll.height - roll.headerHeight
            color: index % 4 === 0 ? Theme.borderActive : Theme.gridLine
        }
    }
    Rectangle {
        readonly property int col: roll.cursorStep - roll.pageStart
        visible: col >= 0 && col < 16
        x: roll.keyWidth + col * roll.colWidth
        y: roll.headerHeight
        width: roll.colWidth
        height: roll.height - roll.headerHeight
        color: Theme.tint(Theme.recording, 0.12)
        border.color: Theme.recording
        border.width: 1
    }
    // Steps past the clip end (a 16-step page is never partial, but stay safe)
    Rectangle {
        readonly property int used: Math.max(0, Math.min(16, roll.clipLength - roll.pageStart))
        visible: used < 16
        x: roll.keyWidth + used * roll.colWidth
        y: roll.headerHeight
        width: (16 - used) * roll.colWidth
        height: roll.height - roll.headerHeight
        color: Theme.scrim
    }

    // Notes (the last step is cut by the step's gate, like it sounds)
    Repeater {
        model: roll.pageNotes
        delegate: Rectangle {
            readonly property var n: modelData
            readonly property int from: Math.max(n.step, roll.pageStart)
            readonly property real span: Math.min(n.step + n.length - 1 + n.gate, roll.pageStart + 16) - from
            readonly property bool sel: n.step === roll.selectedStep && n.pitch === roll.selectedPitch
            readonly property bool startsHere: n.step >= roll.pageStart
            visible: n.pitch <= roll.topPitch && n.pitch >= roll.bottomPitch
            x: roll.keyWidth + (from - roll.pageStart) * roll.colWidth + (startsHere ? 2 : 0)
            y: roll.headerHeight + (roll.topPitch - n.pitch) * roll.rowHeight + 2
            width: Math.max(ScaleMetrics.dp(6), span * roll.colWidth - (startsHere ? 4 : 2))
            height: roll.rowHeight - 5
            radius: ScaleMetrics.dp(3)
            color: sel ? roll.trackColor
                       : Qt.rgba(roll.trackColor.r, roll.trackColor.g, roll.trackColor.b, 0.35 + 0.45 * n.velocity / 127)
            border.color: sel ? Theme.textPrimary : roll.trackColor
            border.width: sel ? 2 : 1
        }
    }

    Rectangle {
        readonly property int col: roll.playhead - roll.pageStart
        visible: roll.playhead >= 0 && col >= 0 && col < 16
        x: roll.keyWidth + col * roll.colWidth
        y: roll.headerHeight
        width: 2
        height: roll.height - roll.headerHeight
        color: Theme.textPrimary
    }

    // One gesture area: tap / double-tap / drag sideways (length) / drag up-down (scroll)
    MouseArea {
        id: gesture
        x: roll.keyWidth
        y: roll.headerHeight
        width: roll.gridWidth
        height: roll.height - roll.headerHeight
        preventStealing: true

        property string mode: ""        // "", "scroll", "length"
        property real pressX: 0
        property real pressY: 0
        property int pressStep: 0
        property int pressPitch: 0
        property int baseCenter: 0
        property var target: null      // {step, pitch} whose length the drag sets
        property bool swallow: false   // the release that ends a double-tap
        property bool justAdded: false // a tap that added a note mustn't let its double-tap delete it
        property string lastTap: ""    // cell of the last tap; a double-tap elsewhere is two taps

        function stepAt(x) { return roll.pageStart + Math.max(0, Math.min(15, Math.floor(x / roll.colWidth))); }
        function pitchAt(y) { return roll.topPitch - Math.max(0, Math.min(roll.visibleRows - 1, Math.floor(y / roll.rowHeight))); }

        function addAt(step, pitch) {
            if (step >= roll.clipLength) return null;
            const p = Bridge.seqAddRollNote(step, pitch);
            if (p < 0) return null;
            roll.noteSelected(step, p);
            return { step: step, pitch: p };
        }

        onPressed: (mouse) => {
            mode = "";
            target = null;
            pressX = mouse.x;
            pressY = mouse.y;
            pressStep = stepAt(mouse.x);
            pressPitch = pitchAt(mouse.y);
            baseCenter = roll.centerPitch;
        }
        onPositionChanged: (mouse) => {
            const dx = mouse.x - pressX, dy = mouse.y - pressY;
            const slop = ScaleMetrics.dp(8);
            if (mode === "") {
                if (Math.abs(dy) > slop && Math.abs(dy) > Math.abs(dx)) {
                    mode = "scroll";
                } else if (Math.abs(dx) > slop) {
                    mode = "length";
                    const hit = roll.noteAt(pressStep, pressPitch);
                    if (hit) {
                        target = { step: hit.step, pitch: hit.pitch };
                        roll.noteSelected(hit.step, hit.pitch);
                    } else {
                        target = addAt(pressStep, pressPitch);
                    }
                }
            }
            if (mode === "scroll") {
                roll.scrollTo(baseCenter + dy / roll.rowHeight);
            } else if (mode === "length" && target) {
                Bridge.seqSetNoteLength(target.step, target.pitch, stepAt(mouse.x) - target.step + 1);
            }
        }
        onReleased: {
            if (swallow) {
                swallow = false;
                return;
            }
            if (mode !== "") return;
            justAdded = false;
            lastTap = pressStep + ":" + pressPitch;
            const hit = roll.noteAt(pressStep, pressPitch);
            if (hit) {
                roll.noteSelected(hit.step, hit.pitch);
            } else if (addAt(pressStep, pressPitch)) {
                justAdded = true;
            }
        }
        onDoubleClicked: {
            if (lastTap !== pressStep + ":" + pressPitch) return;
            swallow = true;
            if (justAdded) {
                justAdded = false;
                return;
            }
            const hit = roll.noteAt(pressStep, pressPitch);
            if (hit) Bridge.seqDeleteStepNote(hit.step, hit.pitch);
        }
    }

    // Key column: drag to scroll too
    MouseArea {
        width: roll.keyWidth
        y: roll.headerHeight
        height: roll.height - roll.headerHeight
        preventStealing: true
        property real pressY: 0
        property int baseCenter: 0
        onPressed: (mouse) => { pressY = mouse.y; baseCenter = roll.centerPitch; }
        onPositionChanged: (mouse) => roll.scrollTo(baseCenter + (mouse.y - pressY) / roll.rowHeight)
    }
}
