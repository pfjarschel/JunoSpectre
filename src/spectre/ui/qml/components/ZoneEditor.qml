pragma ValueTypeBehavior: Copy
import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

// Key-zone editor for the PERFORMANCE screen: part chips, all-parts
// coverage lane, visual piano, bound/octave/switch controls. Zones live
// per MIDI channel on the synth; parts address them via Rx channel.
ColumnLayout {
    id: root
    spacing: ScaleMetrics.dp(6)

    property var allParts: Bridge.perfParts
    property int activePart: Bridge.activePerfPart
    property bool handleLow: true

    property var partColors: Theme.partColors

    function partAt(idx) {
        if (root.allParts && root.allParts.length >= idx) return root.allParts[idx - 1]
        return null
    }

    function coverColor(n) {
        var found = -1
        var count = 0
        for (var i = 0; i < root.allParts.length; i++) {
            var p = root.allParts[i]
            if (!p.zoneOn) continue
            if (n >= p.keyLow && n <= p.keyHigh) { count++; found = i }
        }
        if (count === 0) return Theme.bgControl
        if (count > 1) return Theme.textPrimary
        return root.partColors[found % 16]
    }

    function applyTap(n) {
        var p = root.partAt(root.activePart)
        if (!p) return
        if (root.handleLow) Bridge.setPartZone(p.index, Math.min(n, p.keyHigh), Math.max(n, p.keyHigh))
        else Bridge.setPartZone(p.index, Math.min(p.keyLow, n), Math.max(p.keyLow, n))
    }


    // Part selector chips
    Flickable {
        Layout.fillWidth: true
        Layout.preferredHeight: ScaleMetrics.dp(30)
        contentWidth: partChips.width
        clip: true
        RowLayout {
            id: partChips
            spacing: ScaleMetrics.dp(4)
            height: ScaleMetrics.dp(30)
            Repeater {
                model: 16
                delegate: SpButton {
                    property int pIdx: index + 1
                    property var pp: root.partAt(pIdx)
                    implicitWidth: ScaleMetrics.dp(52)
                    implicitHeight: ScaleMetrics.dp(28)
                    text: "P" + pIdx
                    fontSize: 10
                    accent: root.partColors[index % 16]
                    checked: root.activePart === pIdx
                    opacity: (pp && !pp.zoneOn) ? 0.45 : 1.0
                    enabled: !root.pushBusyRef
                    onClicked: Bridge.editPerfPart(pIdx)
                }
            }
        }
    }
    property bool pushBusyRef: Bridge.perfPushProgress >= 0

    // All-parts coverage lane (128 notes, equal slices). One canvas pass
    // per change; it repaints only while visible.
    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: ScaleMetrics.dp(14)
        radius: ScaleMetrics.dp(3)
        color: Theme.bgControl
        border.color: Theme.borderCard
        border.width: 1
        Canvas {
            id: coverLane
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(2)
            property var parts: root.allParts
            onPartsChanged: requestPaint()
            onWidthChanged: requestPaint()
            onVisibleChanged: if (visible) requestPaint()
            onPaint: {
                var ctx = getContext("2d");
                ctx.clearRect(0, 0, width, height);
                if (!visible || !parts) return;
                var slice = width / 128;
                for (var n = 0; n < 128; ++n) {
                    var c = root.coverColor(n);
                    if (c === Theme.bgControl) continue;
                    ctx.fillStyle = c;
                    ctx.fillRect(Math.floor(n * slice), 0, Math.ceil(slice), height);
                }
            }
        }
    }

    // Piano
    PianoKeyboard {
        id: piano
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.minimumHeight: ScaleMetrics.dp(140)
        rangeLow: (root.partAt(root.activePart) || { keyLow: 0 }).keyLow
        rangeHigh: (root.partAt(root.activePart) || { keyHigh: 127 }).keyHigh
        rangeColor: root.partColors[(root.activePart - 1) % 16]
        onKeyTapped: (n) => root.applyTap(n)
    }

    // Controls row
    RowLayout {
        Layout.fillWidth: true
        spacing: ScaleMetrics.dp(6)

        // LOW / HIGH handle toggle
        SpButton {
            implicitWidth: ScaleMetrics.dp(64)
            implicitHeight: ScaleMetrics.dp(40)
            text: "LOW\n" + Notes.name((root.partAt(root.activePart) || { keyLow: 0 }).keyLow)
            variant: "outline"
            checked: root.handleLow
            onClicked: root.handleLow = true
        }
        SpButton {
            implicitWidth: ScaleMetrics.dp(64)
            implicitHeight: ScaleMetrics.dp(40)
            text: "HIGH\n" + Notes.name((root.partAt(root.activePart) || { keyHigh: 127 }).keyHigh)
            variant: "outline"
            checked: !root.handleLow
            onClicked: root.handleLow = false
        }
        // Octave shift stepper
        Rectangle {
            Layout.fillWidth: true
            height: ScaleMetrics.dp(40)
            radius: ScaleMetrics.dp(4)
            color: Theme.bgApp
            border.color: Theme.borderCard; border.width: 1
            RowLayout {
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(4)
                spacing: ScaleMetrics.dp(4)
                Text { text: "OCT"; font.bold: true; font.pixelSize: ScaleMetrics.sp(9); color: Theme.textDim }
                SpButton {
                    implicitWidth: ScaleMetrics.dp(32)
                    implicitHeight: ScaleMetrics.dp(30)
                    text: "−"
                    fontSize: 12
                    onClicked: {
                        var p = root.partAt(root.activePart)
                        if (p) Bridge.setPartZoneOctave(p.index, p.zoneOctave - 1)
                    }
                }
                Text {
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignHCenter
                    text: {
                        var p = root.partAt(root.activePart)
                        var o = p ? (p.zoneOctave - 64) : 0
                        return (o > 0 ? "+" : "") + o
                    }
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(13)
                    font.family: Theme.fontMono
                    color: Theme.textPrimary
                }
                SpButton {
                    implicitWidth: ScaleMetrics.dp(32)
                    implicitHeight: ScaleMetrics.dp(30)
                    text: "+"
                    fontSize: 12
                    onClicked: {
                        var p = root.partAt(root.activePart)
                        if (p) Bridge.setPartZoneOctave(p.index, p.zoneOctave + 1)
                    }
                }
            }
        }
        // Zone ON/OFF
        SpButton {
            implicitWidth: ScaleMetrics.dp(64)
            implicitHeight: ScaleMetrics.dp(40)
            text: (root.partAt(root.activePart) || { zoneOn: true }).zoneOn ? "ZONE\nON" : "ZONE\nOFF"
            accent: (root.partAt(root.activePart) || { zoneOn: true }).zoneOn ? Theme.pageAccent : Theme.recording
            checked: true
            onClicked: {
                var p = root.partAt(root.activePart)
                if (p) Bridge.setPartZoneSwitch(p.index, !p.zoneOn)
            }
        }
        // FULL range reset
        SpButton {
            implicitWidth: ScaleMetrics.dp(56)
            implicitHeight: ScaleMetrics.dp(40)
            text: "FULL"
            onClicked: {
                var p = root.partAt(root.activePart)
                if (p) Bridge.setPartZone(p.index, 0, 127)
            }
        }
        // Keyboard scroll reach
        SpButton {
            implicitWidth: ScaleMetrics.dp(44)
            implicitHeight: ScaleMetrics.dp(40)
            icon: "left"
            fontSize: 12
            onClicked: piano.scrollKeys(-280)
        }
        SpButton {
            implicitWidth: ScaleMetrics.dp(44)
            implicitHeight: ScaleMetrics.dp(40)
            icon: "right"
            fontSize: 12
            onClicked: piano.scrollKeys(280)
        }
    }
}
