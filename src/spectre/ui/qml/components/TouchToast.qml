pragma ValueTypeBehavior: Copy
import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

// The hardware control under the hand, when the page has no control of its
// own to highlight for it (TouchHighlight).
Rectangle {
    id: toast
    readonly property var info: Bridge.touchedControl
    readonly property bool showing: Bridge.touchedKey !== "" && TouchHint.shown === 0

    width: row.implicitWidth + ScaleMetrics.dp(24)
    height: ScaleMetrics.dp(46)
    radius: ScaleMetrics.dp(8)
    color: Theme.bgRaised
    border.color: Theme.pageAccent
    border.width: 1
    opacity: showing ? 1.0 : 0.0
    visible: opacity > 0
    Behavior on opacity { NumberAnimation { duration: toast.showing ? 80 : 250 } }

    RowLayout {
        id: row
        anchors.centerIn: parent
        spacing: ScaleMetrics.dp(10)
        Text {
            text: toast.info.group || ""
            font.bold: true
            font.pixelSize: ScaleMetrics.sp(Theme.fontSm)
            color: Theme.textDim
        }
        Text {
            text: toast.info.name || ""
            font.bold: true
            font.pixelSize: ScaleMetrics.sp(15)
            color: Theme.textPrimary
        }
        Text {
            text: toast.info.value || ""
            font.family: Theme.fontMono
            font.bold: true
            font.pixelSize: ScaleMetrics.sp(15)
            color: Theme.pageAccent
        }
    }
}
