pragma ValueTypeBehavior: Copy
import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

// Opens the Tone Mix Table overlay (structure types, booster, key/velocity
// ranges). Shown on every synth-engine page; lights up when a pair is merged.
Rectangle {
    id: root
    readonly property var tmt: Bridge.tmt
    readonly property int s12: tmt.structure12
    readonly property int s34: tmt.structure34
    readonly property bool merged: s12 > 0 || s34 > 0

    implicitWidth: ScaleMetrics.dp(118)
    height: ScaleMetrics.dp(26)
    radius: ScaleMetrics.dp(4)
    color: area.pressed ? Theme.bgCardActive : (merged ? Theme.tint(Theme.pageAccent) : Theme.bgControl)
    border.color: merged ? Theme.warning : Theme.borderCard
    border.width: 1

    RowLayout {
        anchors.centerIn: parent
        spacing: ScaleMetrics.dp(6)
        Text {
            text: "STRUCTURE"
            font.bold: true
            font.pixelSize: ScaleMetrics.sp(8)
            color: root.merged ? Theme.textPrimary : Theme.textSecondary
        }
        Text {
            text: (root.s12 + 1) + "·" + (root.s34 + 1)
            font.bold: true
            font.pixelSize: ScaleMetrics.sp(8)
            font.family: Theme.fontMono
            color: root.merged ? Theme.warning : Theme.textDim
        }
    }

    MouseArea {
        id: area
        anchors.fill: parent
        onClicked: Bridge.openTmtOverlay("STRUCTURE")
    }
}
