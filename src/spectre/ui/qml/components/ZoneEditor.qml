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

    property var partColors: ["#f87171", "#fb923c", "#fbbf24", "#a3e635", "#34d399", "#2dd4bf",
        "#38bdf8", "#818cf8", "#a78bfa", "#e879f9", "#f472b6", "#fb7185",
        "#facc15", "#4ade80", "#22d3ee", "#c084fc"]

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
        if (count === 0) return "#0f172a"
        if (count > 1) return "#ffffff"
        return root.partColors[found % 16]
    }

    function applyTap(n) {
        var p = root.partAt(root.activePart)
        if (!p) return
        if (root.handleLow) Bridge.setPartZone(p.index, Math.min(n, p.keyHigh), Math.max(n, p.keyHigh))
        else Bridge.setPartZone(p.index, Math.min(p.keyLow, n), Math.max(p.keyLow, n))
    }

    function noteName(n) {
        var names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        return names[n % 12] + (Math.floor(n / 12) - 1)
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
                delegate: Rectangle {
                    property int pIdx: index + 1
                    property var pp: root.partAt(pIdx)
                    width: ScaleMetrics.dp(52)
                    height: ScaleMetrics.dp(28)
                    radius: ScaleMetrics.dp(4)
                    color: root.activePart === pIdx ? root.partColors[index % 16] : "#0d1017"
                    border.color: root.activePart === pIdx ? "#ffffff" : Theme.borderCard
                    border.width: root.activePart === pIdx ? 2 : 1
                    opacity: (pp && !pp.zoneOn) ? 0.45 : 1.0
                    Text {
                        anchors.centerIn: parent
                        text: "P" + pIdx
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(10)
                        color: root.activePart === pIdx ? "#000000" : Theme.textSecondary
                    }
                    MouseArea {
                        anchors.fill: parent
                        enabled: !root.pushBusyRef
                        onClicked: Bridge.editPerfPart(pIdx)
                    }
                }
            }
        }
    }
    property bool pushBusyRef: Bridge.perfPushProgress >= 0

    // All-parts coverage lane (128 notes, equal slices)
    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: ScaleMetrics.dp(14)
        radius: ScaleMetrics.dp(3)
        color: "#0f172a"
        border.color: Theme.borderCard
        border.width: 1
        RowLayout {
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(2)
            spacing: 0
            Repeater {
                model: 128
                delegate: Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: root.coverColor(index)
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
        Rectangle {
            width: ScaleMetrics.dp(64); height: ScaleMetrics.dp(40)
            radius: ScaleMetrics.dp(4)
            color: root.handleLow ? "#0c2f3f" : Theme.bgApp
            border.color: "#38bdf8"; border.width: 1
            Text {
                anchors.centerIn: parent
                text: "LOW\n" + root.noteName((root.partAt(root.activePart) || { keyLow: 0 }).keyLow)
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(9)
                horizontalAlignment: Text.AlignHCenter
                color: "#38bdf8"
            }
            MouseArea { anchors.fill: parent; onClicked: root.handleLow = true }
        }
        Rectangle {
            width: ScaleMetrics.dp(64); height: ScaleMetrics.dp(40)
            radius: ScaleMetrics.dp(4)
            color: !root.handleLow ? "#3a2f10" : Theme.bgApp
            border.color: "#f59e0b"; border.width: 1
            Text {
                anchors.centerIn: parent
                text: "HIGH\n" + root.noteName((root.partAt(root.activePart) || { keyHigh: 127 }).keyHigh)
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(9)
                horizontalAlignment: Text.AlignHCenter
                color: "#f59e0b"
            }
            MouseArea { anchors.fill: parent; onClicked: root.handleLow = false }
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
                Rectangle {
                    width: ScaleMetrics.dp(32); height: ScaleMetrics.dp(30)
                    radius: 3; color: octDown.pressed ? Theme.bgCardActive : Theme.bgSurface
                    border.color: Theme.borderCard; border.width: 1
                    Text { anchors.centerIn: parent; text: "−"; font.bold: true; font.pixelSize: ScaleMetrics.sp(12); color: Theme.textSecondary }
                    MouseArea {
                        id: octDown; anchors.fill: parent
                        onClicked: {
                            var p = root.partAt(root.activePart)
                            if (p) Bridge.setPartZoneOctave(p.index, p.zoneOctave - 1)
                        }
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
                Rectangle {
                    width: ScaleMetrics.dp(32); height: ScaleMetrics.dp(30)
                    radius: 3; color: octUp.pressed ? Theme.bgCardActive : Theme.bgSurface
                    border.color: Theme.borderCard; border.width: 1
                    Text { anchors.centerIn: parent; text: "+"; font.bold: true; font.pixelSize: ScaleMetrics.sp(12); color: Theme.textSecondary }
                    MouseArea {
                        id: octUp; anchors.fill: parent
                        onClicked: {
                            var p = root.partAt(root.activePart)
                            if (p) Bridge.setPartZoneOctave(p.index, p.zoneOctave + 1)
                        }
                    }
                }
            }
        }
        // Zone ON/OFF
        Rectangle {
            width: ScaleMetrics.dp(64); height: ScaleMetrics.dp(40)
            radius: ScaleMetrics.dp(4)
            color: (root.partAt(root.activePart) || { zoneOn: true }).zoneOn ? "#0d2b1a" : "#3f1a1a"
            border.color: (root.partAt(root.activePart) || { zoneOn: true }).zoneOn ? "#10b981" : Theme.recording
            border.width: 1
            Text {
                anchors.centerIn: parent
                text: (root.partAt(root.activePart) || { zoneOn: true }).zoneOn ? "ZONE\nON" : "ZONE\nOFF"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(9)
                horizontalAlignment: Text.AlignHCenter
                color: (root.partAt(root.activePart) || { zoneOn: true }).zoneOn ? "#10b981" : Theme.recording
            }
            MouseArea {
                anchors.fill: parent
                onClicked: {
                    var p = root.partAt(root.activePart)
                    if (p) Bridge.setPartZoneSwitch(p.index, !p.zoneOn)
                }
            }
        }
        // FULL range reset
        Rectangle {
            width: ScaleMetrics.dp(56); height: ScaleMetrics.dp(40)
            radius: ScaleMetrics.dp(4)
            color: fullMouse.pressed ? Theme.bgCardActive : Theme.bgSurface
            border.color: Theme.borderCard; border.width: 1
            Text { anchors.centerIn: parent; text: "FULL"; font.bold: true; font.pixelSize: ScaleMetrics.sp(9); color: Theme.textSecondary }
            MouseArea {
                id: fullMouse; anchors.fill: parent
                onClicked: {
                    var p = root.partAt(root.activePart)
                    if (p) Bridge.setPartZone(p.index, 0, 127)
                }
            }
        }
        // Keyboard scroll reach
        Rectangle {
            width: ScaleMetrics.dp(44); height: ScaleMetrics.dp(40)
            radius: ScaleMetrics.dp(4)
            color: Theme.bgSurface
            border.color: Theme.borderCard; border.width: 1
            Text { anchors.centerIn: parent; text: "◀"; font.bold: true; font.pixelSize: ScaleMetrics.sp(12); color: Theme.textSecondary }
            MouseArea { anchors.fill: parent; onClicked: piano.scrollKeys(-280) }
        }
        Rectangle {
            width: ScaleMetrics.dp(44); height: ScaleMetrics.dp(40)
            radius: ScaleMetrics.dp(4)
            color: Theme.bgSurface
            border.color: Theme.borderCard; border.width: 1
            Text { anchors.centerIn: parent; text: "▶"; font.bold: true; font.pixelSize: ScaleMetrics.sp(12); color: Theme.textSecondary }
            MouseArea { anchors.fill: parent; onClicked: piano.scrollKeys(280) }
        }
    }
}
