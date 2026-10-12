pragma ValueTypeBehavior: Copy
import QtQuick
import JunoSpectre
import ".."

// A Phosphor icon by semantic name (see Icons.qml). It is a Text, so color,
// font.pixelSize, anchors and layouts work as for any label.
Text {
    property string name: ""
    // Icon size in dp (the glyph box is square)
    property real size: 14
    // Fill weight (transport icons and dots default to filled; see Icons.qml)
    property bool filled: Icons.isFilled(name)

    text: name !== "" ? Icons.glyph(name) : ""
    font.family: filled ? Theme.fontIconsFill : Theme.fontIcons
    font.pixelSize: ScaleMetrics.dp(size)
    font.bold: false
    color: Theme.textSecondary
    horizontalAlignment: Text.AlignHCenter
    verticalAlignment: Text.AlignVCenter
}
