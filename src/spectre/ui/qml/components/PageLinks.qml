pragma ValueTypeBehavior: Copy
import QtQuick
import JunoSpectre
import ".."

// Jump buttons between a family of related pages: the same row on each of
// them, at the right end of the page header, the current page lit. Icon only
// (the header bar names the page; the icons are the Screens overlay's).
Row {
    id: links
    property string group: ""
    readonly property var groups: ({
        "perform": ["PERFORMANCE", "SEQUENCER", "LIVE", "SETLIST"]
    })

    spacing: ScaleMetrics.dp(3)

    Repeater {
        model: links.groups[links.group] || []
        delegate: SpButton {
            implicitHeight: ScaleMetrics.dp(28)
            implicitWidth: ScaleMetrics.dp(36)
            icon: Icons.forView(modelData)
            checked: Bridge.activeView === modelData
            onClicked: if (!checked) Bridge.setActiveView(modelData)
        }
    }
}
