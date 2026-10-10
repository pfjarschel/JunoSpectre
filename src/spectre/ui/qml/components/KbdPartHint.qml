pragma ValueTypeBehavior: Copy
import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

// Non-blocking hint when the keyboard plays a different part than the active
// track sends to. The keyboard part is learned from the channel of played
// keys (the panel's current part can't be read over SysEx).
//   "Playing P3 · track sends to P1"  [USE P3]
Rectangle {
    id: hint
    property color accent: Theme.tone1

    readonly property var track: (Bridge.seqTracks && Bridge.seqTracks.length > Bridge.seqActiveTrack)
                                 ? Bridge.seqTracks[Bridge.seqActiveTrack] : null
    readonly property var trackParts: track ? track.targetParts : []
    readonly property int mainPart: (track && track.targetPart) ? track.targetPart : (Bridge.seqActiveTrack + 1)

    // Part listening on the played channel; the track's own part wins a shared channel.
    readonly property int kbdPart: {
        const ch = Bridge.seqKbdChannel;
        const parts = Bridge.perfParts || [];
        if (ch < 0) return 0;
        let first = 0;
        for (let i = 0; i < parts.length; i++) {
            const p = parts[i];
            if (!p.rxOn || p.rxChannel !== ch) continue;
            if (hint.trackParts.indexOf(p.index) >= 0) return p.index;
            if (first === 0) first = p.index;
        }
        return first;
    }

    visible: kbdPart > 0 && trackParts.indexOf(kbdPart) < 0
    height: ScaleMetrics.dp(26)
    implicitWidth: row.implicitWidth + ScaleMetrics.dp(12)
    width: implicitWidth
    radius: 4
    color: "#2a1f06"
    border.color: "#f59e0b"
    border.width: 1

    RowLayout {
        id: row
        anchors.centerIn: parent
        spacing: ScaleMetrics.dp(6)

        Text {
            text: "Playing P" + hint.kbdPart + " · track sends to P" + hint.mainPart
            font.pixelSize: ScaleMetrics.sp(8)
            color: "#fbbf24"
        }
        Rectangle {
            width: useText.implicitWidth + ScaleMetrics.dp(10)
            height: ScaleMetrics.dp(18)
            radius: 3
            color: useMouse.pressed ? "#f59e0b" : "#3d2c08"
            border.color: "#f59e0b"
            border.width: 1
            Text {
                id: useText
                anchors.centerIn: parent
                text: "USE P" + hint.kbdPart
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(8)
                color: useMouse.pressed ? "#000000" : "#fbbf24"
            }
            MouseArea {
                id: useMouse
                anchors.fill: parent
                onClicked: Bridge.seqSetTrackTargetPart(Bridge.seqActiveTrack, hint.kbdPart)
            }
        }
    }
}
