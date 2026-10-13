pragma ValueTypeBehavior: Copy
import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

// Sequencer inspector tile: title + value. Drag right/up to increase,
// left/down to decrease (adjust(+1 / -1)); a tap without a drag is tapped().
Rectangle {
    id: ipRoot
    property string title: "PARAM"
    property string valStr: "--"
    property color accent: Theme.pageAccent
    property bool lit: false
    signal adjust(int delta)
    signal tapped()

    radius: ScaleMetrics.dp(4)
    color: lit ? Theme.tint(ipRoot.accent) : Theme.bgSurface
    border.color: (ipMouse.containsPress || lit) ? ipRoot.accent : Theme.borderCard
    border.width: 1

    MouseArea {
        id: ipMouse
        anchors.fill: parent
        preventStealing: true
        // A tile at the screen's bottom edge still has the horizontal axis free.
        property real lastX: 0
        property real lastY: 0
        property bool moved: false
        onPressed: (mouse) => { lastX = mouse.x; lastY = mouse.y; moved = false; }
        onPositionChanged: (mouse) => {
            if (pressed) {
                const d = (mouse.x - lastX) + (lastY - mouse.y);
                if (Math.abs(d) > ScaleMetrics.dp(4)) {
                    ipRoot.adjust(d > 0 ? 1 : -1);
                    moved = true;
                    lastX = mouse.x;
                    lastY = mouse.y;
                }
            }
        }
        onClicked: if (!moved) ipRoot.tapped()
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
            color: ipRoot.lit ? ipRoot.accent : Theme.textDim
        }
        Item { Layout.fillHeight: true }
        Text {
            Layout.alignment: Qt.AlignHCenter
            Layout.maximumWidth: ipRoot.width - ScaleMetrics.dp(6)
            text: ipRoot.valStr
            elide: Text.ElideRight
            font.family: Theme.fontMono
            font.bold: true
            font.pixelSize: ScaleMetrics.sp(14)
            color: ipRoot.accent
        }
        Item { Layout.fillHeight: true }
    }
}
