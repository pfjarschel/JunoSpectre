pragma ValueTypeBehavior: Copy
import QtQuick
import JunoSpectre
import ".."

// The one parameter slider: a horizontal value bar, tap or drag to set.
// It sets the style only; the screen sets the size.
//   stacked: false  label left / value right inside the bar
//   stacked: true   label + value on a row above the bar
//   bipolar         fill grows from the centre
//   from/to/integer moved() reports from..to (rounded if integer); the
//                   default 0..1 reports the normalized position
//   scrollView      parent Flickable: a horizontal-first drag holds it so
//                   vertical drift can't steal the gesture; a vertical-first
//                   drag is left to the Flickable
Item {
    id: sl

    property string label: ""
    property string valueText: ""
    property real norm: 0.0
    property bool bipolar: false
    property bool stacked: false
    property color accent: Theme.pageAccent
    property var scrollView: null
    property real from: 0.0
    property real to: 1.0
    property bool integer: false
    readonly property alias pressed: area.pressed

    signal moved(real value)

    readonly property real _n: Math.max(0.0, Math.min(1.0, norm))

    implicitWidth: ScaleMetrics.dp(120)
    implicitHeight: ScaleMetrics.dp(stacked ? 38 : 28)
    opacity: enabled ? 1.0 : Theme.disabledOpacity

    // Stacked header row
    Item {
        id: header
        visible: sl.stacked
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: sl.stacked ? ScaleMetrics.dp(13) : 0
        Text {
            anchors.left: parent.left
            anchors.right: headerValue.left
            anchors.rightMargin: ScaleMetrics.dp(6)
            anchors.verticalCenter: parent.verticalCenter
            text: sl.label
            elide: Text.ElideRight
            font.bold: true
            font.pixelSize: ScaleMetrics.sp(Theme.fontXs)
            color: sl.pressed ? Theme.textPrimary : Theme.textSecondary
        }
        Text {
            id: headerValue
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            text: sl.valueText
            font.family: Theme.fontMono
            font.bold: true
            font.pixelSize: ScaleMetrics.sp(Theme.fontSm)
            color: Theme.textPrimary
        }
    }

    Rectangle {
        id: bar
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: header.bottom
        anchors.topMargin: sl.stacked ? ScaleMetrics.dp(3) : 0
        anchors.bottom: parent.bottom
        radius: ScaleMetrics.dp(Theme.radiusSmall)
        color: Theme.bgControl
        border.width: 1
        border.color: sl.pressed ? sl.accent : Theme.borderCard
        clip: true

        Rectangle {
            id: fill
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.margins: 1
            x: sl.bipolar ? (sl._n >= 0.5 ? bar.width * 0.5 : bar.width * sl._n) : 1
            width: sl.bipolar ? Math.abs(bar.width * (sl._n - 0.5)) : Math.max(0, (bar.width - 2) * sl._n)
            radius: ScaleMetrics.dp(2)
            color: Theme.tint(sl.accent, sl.pressed ? 0.5 : Theme.fillAlpha)
        }

        Rectangle {
            visible: sl.bipolar
            x: Math.round(bar.width * 0.5)
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: 1
            color: Theme.borderActive
        }

        Text {
            visible: !sl.stacked
            anchors.left: parent.left
            anchors.right: inlineValue.left
            anchors.leftMargin: ScaleMetrics.dp(6)
            anchors.rightMargin: ScaleMetrics.dp(6)
            anchors.verticalCenter: parent.verticalCenter
            text: sl.label
            elide: Text.ElideRight
            font.bold: true
            font.pixelSize: ScaleMetrics.sp(Theme.fontXs)
            color: sl.pressed ? Theme.textPrimary : Theme.textSecondary
        }
        Text {
            id: inlineValue
            visible: !sl.stacked
            anchors.right: parent.right
            anchors.rightMargin: ScaleMetrics.dp(6)
            anchors.verticalCenter: parent.verticalCenter
            text: sl.valueText
            font.family: Theme.fontMono
            font.bold: true
            font.pixelSize: ScaleMetrics.sp(Theme.fontSm)
            color: Theme.textPrimary
        }

        MouseArea {
            id: area
            anchors.fill: parent
            enabled: sl.enabled
            preventStealing: sl.scrollView === null
            property real startX: 0
            property real startY: 0
            property string lockDir: ""

            function emitAt(x) {
                const n = Math.max(0.0, Math.min(1.0, x / width));
                const v = sl.from + n * (sl.to - sl.from);
                sl.moved(sl.integer ? Math.round(v) : v);
            }
            function releaseLock() {
                if (sl.scrollView) sl.scrollView.interactive = true;
                lockDir = "";
            }

            onPressed: (mouse) => {
                startX = mouse.x; startY = mouse.y; lockDir = "";
                emitAt(mouse.x);
            }
            onPositionChanged: (mouse) => {
                if (!pressed) return;
                if (sl.scrollView && lockDir === "") {
                    const dx = Math.abs(mouse.x - startX), dy = Math.abs(mouse.y - startY);
                    if (dx < ScaleMetrics.dp(10) && dy < ScaleMetrics.dp(10)) return;
                    lockDir = dx >= dy ? "h" : "v";
                    if (lockDir === "h") sl.scrollView.interactive = false;
                }
                if (lockDir !== "v") emitAt(mouse.x);
            }
            onReleased: releaseLock()
            onCanceled: releaseLock()
        }
    }
}
