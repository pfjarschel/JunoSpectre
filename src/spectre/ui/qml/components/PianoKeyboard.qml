pragma ValueTypeBehavior: Copy
import QtQuick
import ".."

// Full-range touch piano (A0–C8, MIDI 21–108) for key-zone editing.
// Tap or slide to set the active bound; the selected part range is tinted,
// C keys are labeled. Keys win over flick-scroll (preventStealing); reach
// distant octaves with scrollKeys() (◀ KEYS / KEYS ▶ buttons).
Item {
    id: root

    property int rangeLow: 0
    property int rangeHigh: 127
    property color rangeColor: "#a855f7"
    property int whiteWidth: ScaleMetrics.dp(28)

    signal keyTapped(int note)

    readonly property int firstNote: 21
    readonly property int lastNote: 108
    property var whiteNotes: []
    property var blackBoxes: []
    property var hitBoxes: [] // {n, x, w}, black (narrow) first for hit wins

    function isWhite(n) {
        var pc = n % 12
        return pc === 0 || pc === 2 || pc === 4 || pc === 5 || pc === 7 || pc === 9 || pc === 11
    }

    function noteName(n) {
        var names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        return names[n % 12] + (Math.floor(n / 12) - 1)
    }

    function buildGeometry() {
        var whites = []
        var blacks = []
        var boxes = []
        var x = 0
        var bw = whiteWidth * 0.62
        var wi = 0
        for (var n = firstNote; n <= lastNote; n++) {
            if (isWhite(n)) {
                whites.push({ n: n, x: x })
                boxes.push({ n: n, x: x, w: whiteWidth })
                x += whiteWidth
                wi++
            } else {
                var bx = wi * whiteWidth
                var blk = { n: n, x: bx - bw / 2, w: bw }
                blacks.push(blk)
                boxes.push(blk)
            }
        }
        boxes.sort(function(a, b) { return a.w - b.w })
        whiteNotes = whites
        blackBoxes = blacks
        hitBoxes = boxes
        pianoContent.width = x
    }

    function noteAt(px) {
        for (var i = 0; i < hitBoxes.length; i++) {
            var b = hitBoxes[i]
            if (px >= b.x && px < b.x + b.w) return b.n
        }
        return -1
    }

    function scrollKeys(dx) {
        flick.contentX = Math.max(0, Math.min(pianoContent.width - flick.width, flick.contentX + dx))
    }

    function centerOn(note) {
        var target = 0
        for (var i = 0; i < whiteNotes.length; i++) {
            if (whiteNotes[i].n <= note) target = whiteNotes[i].x
        }
        flick.contentX = Math.max(0, Math.min(pianoContent.width - flick.width, target - flick.width / 2))
    }

    Component.onCompleted: {
        buildGeometry()
        centerTimer.start()
    }

    // One-shot: center middle-C after layout gives the flick a real width.
    Timer {
        id: centerTimer
        interval: 120
        repeat: false
        running: false
        onTriggered: root.centerOn(60)
    }

    Flickable {
        id: flick
        anchors.fill: parent
        contentWidth: pianoContent.width
        contentHeight: height
        clip: true

        Item {
            id: pianoContent
            height: flick.height

            // White bed
            Repeater {
                model: root.whiteNotes
                delegate: Rectangle {
                    x: modelData.x
                    width: root.whiteWidth - 1
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    radius: 2
                    color: (modelData.n >= root.rangeLow && modelData.n <= root.rangeHigh)
                           ? Qt.lighter(root.rangeColor, 1.35) : "#e8edf3"
                    border.color: "#0f172a"
                    border.width: 1
                    Text {
                        visible: (modelData.n % 12) === 0
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: ScaleMetrics.dp(4)
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: root.noteName(modelData.n)
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: (modelData.n >= root.rangeLow && modelData.n <= root.rangeHigh) ? "#ffffff" : "#475569"
                    }
                }
            }

            // Black overlays
            Repeater {
                model: root.blackBoxes
                delegate: Rectangle {
                    x: modelData.x
                    width: modelData.w
                    anchors.top: parent.top
                    height: parent.height * 0.62
                    radius: 2
                    color: (modelData.n >= root.rangeLow && modelData.n <= root.rangeHigh)
                           ? root.rangeColor : "#11151d"
                    border.color: "#000000"
                    border.width: 1
                }
            }

            // Low (blue) / High (amber) bound markers
            Repeater {
                model: [{ n: root.rangeLow, c: "#38bdf8" }, { n: root.rangeHigh, c: "#f59e0b" }]
                delegate: Rectangle {
                    property int markNote: modelData.n
                    property var box: (function() {
                        for (var i = 0; i < root.hitBoxes.length; i++)
                            if (root.hitBoxes[i].n === markNote) return root.hitBoxes[i]
                        return null
                    })()
                    x: box ? box.x + box.w / 2 - width / 2 : 0
                    width: ScaleMetrics.dp(4)
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    radius: 2
                    color: modelData.c
                }
            }

            MouseArea {
                anchors.fill: parent
                preventStealing: true
                function applyAt(mx) {
                    var n = root.noteAt(mx)
                    if (n >= 0) root.keyTapped(n)
                }
                onPressed: (mouse) => applyAt(mouse.x)
                onPositionChanged: (mouse) => { if (pressed) applyAt(mouse.x) }
            }
        }
    }
}
