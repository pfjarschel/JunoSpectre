pragma ValueTypeBehavior: Copy
import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

// Index-based value stepper for the sequencer toolbar:
//   ◀ / ▶      tap to step, hold to auto-repeat (clamped at the ends)
//   centre      drag horizontally to scrub, tap to cycle forward (wraps)
Rectangle {
    id: st
    property string label: ""
    property string valueText: ""
    property color valueColor: Theme.textPrimary
    property int index: 0
    property int count: 1
    property real pxPerStep: ScaleMetrics.dp(12)
    signal requested(int newIndex)

    height: ScaleMetrics.dp(30)
    width: ScaleMetrics.dp(112)
    radius: 3
    color: Theme.bgApp
    border.color: centreMouse.dragging ? st.valueColor : Theme.borderCard
    border.width: 1

    function stepBy(delta) {
        const n = Math.max(0, Math.min(st.count - 1, st.index + delta));
        if (n !== st.index) st.requested(n);
    }

    Timer {
        id: repeatTimer
        property int dir: 0
        interval: 380
        repeat: true
        onTriggered: { interval = 90; st.stepBy(dir); }
    }

    component Arrow: Rectangle {
        id: arrow
        property int dir: 1
        Layout.preferredWidth: ScaleMetrics.dp(26)
        Layout.fillHeight: true
        radius: 3
        color: arrowMouse.pressed ? Qt.rgba(st.valueColor.r, st.valueColor.g, st.valueColor.b, 0.25) : "transparent"
        opacity: (dir < 0 ? st.index > 0 : st.index < st.count - 1) ? 1.0 : 0.3
        Text {
            anchors.centerIn: parent
            text: arrow.dir < 0 ? "◀" : "▶"
            font.pixelSize: ScaleMetrics.sp(9)
            color: Theme.textDim
        }
        MouseArea {
            id: arrowMouse
            anchors.fill: parent
            onPressed: {
                st.stepBy(arrow.dir);
                repeatTimer.dir = arrow.dir;
                repeatTimer.interval = 380;
                repeatTimer.restart();
            }
            onReleased: repeatTimer.stop()
            onCanceled: repeatTimer.stop()
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 1
        spacing: 0

        Arrow { dir: -1 }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            RowLayout {
                anchors.centerIn: parent
                spacing: ScaleMetrics.dp(3)
                Text { text: st.label; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textDim }
                Text { text: st.valueText; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: st.valueColor }
            }
            MouseArea {
                id: centreMouse
                anchors.fill: parent
                preventStealing: true
                property real startX: 0
                property int startIndex: 0
                property bool dragging: false
                onPressed: (mouse) => {
                    startX = mouse.x;
                    startIndex = st.index;
                    dragging = false;
                }
                onPositionChanged: (mouse) => {
                    const dx = mouse.x - startX;
                    if (!dragging && Math.abs(dx) < ScaleMetrics.dp(6)) return;
                    dragging = true;
                    const n = Math.max(0, Math.min(st.count - 1, startIndex + Math.round(dx / st.pxPerStep)));
                    if (n !== st.index) st.requested(n);
                }
                onReleased: {
                    if (!dragging) st.requested((st.index + 1) % st.count);
                    dragging = false;
                }
                onCanceled: dragging = false
            }
        }

        Arrow { dir: 1 }
    }
}
