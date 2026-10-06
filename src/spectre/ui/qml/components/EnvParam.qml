import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

// Compact horizontal drag param pill shared by the envelope editors.
Rectangle {
    id: ep
    property string label: "P"
    property color labelColor: Theme.textDim
    property int val: 0
    property real norm: 0.5
    property bool isBipolar: false
    property color barColor: "#fbbf24"
    property string customText: ""
    signal moved(real norm)

    height: ScaleMetrics.dp(34)
    radius: 3
    color: "#10141d"
    border.color: Theme.borderCard
    border.width: 1

    Rectangle {
        x: ep.isBipolar ? (ep.norm >= 0.5 ? parent.width * 0.5 : parent.width * ep.norm) : 0
        width: ep.isBipolar ? Math.abs(parent.width * (ep.norm - 0.5)) : parent.width * ep.norm
        height: parent.height
        color: Qt.rgba(ep.barColor.r, ep.barColor.g, ep.barColor.b, 0.28)
    }

    Rectangle {
        visible: ep.isBipolar
        x: Math.round(parent.width * 0.5)
        y: 0
        width: 1
        height: parent.height
        color: Qt.rgba(1, 1, 1, 0.15)
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 2
        spacing: 0
        Text {
            text: ep.label
            font.bold: true
            font.pixelSize: ScaleMetrics.sp(7)
            color: ep.labelColor
        }
        Item { Layout.fillHeight: true }
        Text {
            text: ep.customText !== "" ? ep.customText : (ep.isBipolar && ep.val > 0 ? "+" + ep.val : ep.val.toString())
            font.family: Theme.fontMono
            font.bold: true
            font.pixelSize: ScaleMetrics.sp(8)
            color: Theme.textPrimary
        }
    }

    MouseArea {
        anchors.fill: parent
        onPositionChanged: (mouse) => {
            if (pressed) {
                var n = Math.max(0.0, Math.min(1.0, mouse.x / width));
                ep.moved(n);
            }
        }
        onPressed: (mouse) => {
            var n = Math.max(0.0, Math.min(1.0, mouse.x / width));
            ep.moved(n);
        }
    }
}
