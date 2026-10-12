pragma ValueTypeBehavior: Copy
import QtQuick
import JunoSpectre
import ".."

// Page title: accent dot + title, the same on every page.
Row {
    id: pt
    property string text: ""
    property color accent: Theme.pageAccent

    spacing: ScaleMetrics.dp(6)

    Rectangle {
        anchors.verticalCenter: parent.verticalCenter
        width: ScaleMetrics.dp(8)
        height: ScaleMetrics.dp(8)
        radius: width / 2
        color: pt.accent
    }
    Text {
        anchors.verticalCenter: parent.verticalCenter
        text: pt.text
        font.bold: true
        font.pixelSize: ScaleMetrics.sp(Theme.fontLg)
        font.letterSpacing: 1.2
        color: Theme.textPrimary
    }
}
