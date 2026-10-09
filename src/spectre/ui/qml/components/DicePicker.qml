import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

// Dice (humanize) settings of a sequencer track: every note gets a fresh
// random timing offset (+/- ticks) and velocity nudge (+/- % of 127).
// Fills its parent to catch taps outside the panel, which close it.
Item {
    id: root
    anchors.fill: parent
    visible: false
    z: 50

    property int trackIdx: 0

    readonly property var trackData: (Bridge.seqTracks && Bridge.seqTracks.length > trackIdx)
                                     ? Bridge.seqTracks[trackIdx] : null
    readonly property color trackColor: Theme.trackColors[trackIdx % Theme.trackColors.length]
    readonly property int timing: trackData ? (trackData.diceTiming || 0) : 0
    readonly property int velocity: trackData ? (trackData.diceVelocity || 0) : 0

    // Open below anchorItem (above it if there's no room), kept inside the parent
    function open(idx, anchorItem) {
        trackIdx = idx;
        const margin = ScaleMetrics.dp(8);
        const below = anchorItem.mapToItem(root, 0, anchorItem.height + ScaleMetrics.dp(4));
        panel.x = Math.max(margin, Math.min(below.x + anchorItem.width - panel.width, root.width - panel.width - margin));
        const y = (below.y + panel.height <= root.height - margin)
                  ? below.y
                  : anchorItem.mapToItem(root, 0, 0).y - panel.height - ScaleMetrics.dp(4);
        panel.y = Math.max(margin, Math.min(y, root.height - panel.height - margin));
        visible = true;
    }

    function close() {
        visible = false;
    }

    MouseArea {
        anchors.fill: parent
        onClicked: root.close()
    }

    Rectangle {
        id: panel
        width: ScaleMetrics.dp(2 * 140 + 24)
        height: diceCol.implicitHeight + ScaleMetrics.dp(16)
        radius: ScaleMetrics.dp(6)
        color: Theme.bgSurface
        border.color: root.trackColor
        border.width: 1

        MouseArea { anchors.fill: parent }  // swallow taps between controls

        ColumnLayout {
            id: diceCol
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(8)
            spacing: ScaleMetrics.dp(6)

            RowLayout {
                Layout.fillWidth: true
                Text {
                    Layout.fillWidth: true
                    text: "DICE · " + (root.trackData ? root.trackData.name : "")
                    elide: Text.ElideRight
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(9)
                    color: root.trackColor
                }
                Text {
                    text: "OFF"
                    visible: root.timing > 0 || root.velocity > 0
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: Theme.textDim
                    MouseArea {
                        anchors.fill: parent
                        anchors.margins: -ScaleMetrics.dp(6)
                        onClicked: Bridge.seqSetTrackDice(root.trackIdx, 0, 0)
                    }
                }
            }

            Text {
                text: "RANDOM PER NOTE, EVERY PASS"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(8)
                font.letterSpacing: 1.0
                color: Theme.textDim
            }

            RowLayout {
                spacing: ScaleMetrics.dp(8)

                // Timing: +/- clock ticks (same units as step micro-timing)
                SeqStepper {
                    width: ScaleMetrics.dp(140)
                    label: "TIME:"
                    count: 25
                    index: root.timing
                    valueText: index > 0 ? "±" + index + "t" : "OFF"
                    valueColor: "#38bdf8"
                    onRequested: (i) => Bridge.seqSetTrackDice(root.trackIdx, i, root.velocity)
                }

                // Velocity: +/- % of the maximum (127)
                SeqStepper {
                    width: ScaleMetrics.dp(140)
                    label: "VEL:"
                    count: 51
                    index: root.velocity
                    valueText: index > 0 ? "±" + index + "%" : "OFF"
                    valueColor: "#a3e635"
                    pxPerStep: ScaleMetrics.dp(6)
                    onRequested: (i) => Bridge.seqSetTrackDice(root.trackIdx, root.timing, i)
                }
            }
        }
    }
}
