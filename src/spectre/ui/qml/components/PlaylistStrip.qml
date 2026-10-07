import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

// Live setlist strip: tap a song to load it, ◀/▶ to step through.
// Status dot per song: green = linked & fresh, amber = file changed
// (tap ↻ to refresh snapshot), red = file missing (plays from snapshot),
// grey = snapshot only. Touch-only; slots are named for MIDI mapping later.
Rectangle {
    id: root
    color: Theme.bgApp
    radius: ScaleMetrics.dp(6)
    border.color: Theme.borderCard
    border.width: 1

    property var entries: Bridge.playlistEntries

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: ScaleMetrics.dp(6)
        spacing: ScaleMetrics.dp(4)

        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(6)

            Text {
                text: "SETLIST"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(9)
                font.letterSpacing: 1.2
                color: Theme.textDim
            }
            Text {
                visible: root.entries.length === 0
                Layout.fillWidth: true
                text: "Empty — tap + to snapshot the current performance as song 1."
                font.pixelSize: ScaleMetrics.sp(8)
                font.italic: true
                color: Theme.textDim
                elide: Text.ElideRight
            }
            Item { visible: root.entries.length > 0; Layout.fillWidth: true }

            // Prev arrow
            Rectangle {
                visible: root.entries.length > 0
                width: ScaleMetrics.dp(44); height: ScaleMetrics.dp(28)
                radius: ScaleMetrics.dp(4)
                color: prevMouse.pressed ? Theme.bgCardActive : Theme.bgSurface
                border.color: Theme.tone2; border.width: 1
                Text { anchors.centerIn: parent; text: "◀"; font.bold: true; font.pixelSize: ScaleMetrics.sp(12); color: Theme.tone2 }
                MouseArea { id: prevMouse; anchors.fill: parent; onClicked: Bridge.prevPlaylistEntry() }
            }
            // Next arrow
            Rectangle {
                visible: root.entries.length > 0
                width: ScaleMetrics.dp(44); height: ScaleMetrics.dp(28)
                radius: ScaleMetrics.dp(4)
                color: nextMouse.pressed ? Theme.bgCardActive : Theme.bgSurface
                border.color: Theme.tone2; border.width: 1
                Text { anchors.centerIn: parent; text: "▶"; font.bold: true; font.pixelSize: ScaleMetrics.sp(12); color: Theme.tone2 }
                MouseArea { id: nextMouse; anchors.fill: parent; onClicked: Bridge.nextPlaylistEntry() }
            }
            // Add current performance as song
            Rectangle {
                width: ScaleMetrics.dp(44); height: ScaleMetrics.dp(28)
                radius: ScaleMetrics.dp(4)
                color: addMouse.pressed ? Theme.bgCardActive : Theme.bgSurface
                border.color: Theme.tone1; border.width: 1
                Text { anchors.centerIn: parent; text: "+"; font.bold: true; font.pixelSize: ScaleMetrics.sp(14); color: Theme.tone1 }
                MouseArea { id: addMouse; anchors.fill: parent; onClicked: Bridge.addCurrentToPlaylist() }
            }
        }

        // Horizontal song chips
        Flickable {
            visible: root.entries.length > 0
            Layout.fillWidth: true
            Layout.preferredHeight: ScaleMetrics.dp(34)
            contentWidth: chipRow.width
            clip: true
            interactive: true
            RowLayout {
                id: chipRow
                spacing: ScaleMetrics.dp(6)
                height: ScaleMetrics.dp(34)
                Repeater {
                    model: root.entries
                    delegate: Rectangle {
                        width: Math.max(ScaleMetrics.dp(120), chipText.implicitWidth + ScaleMetrics.dp(52))
                        height: ScaleMetrics.dp(32)
                        radius: ScaleMetrics.dp(16)
                        color: modelData.current ? "#2d1b4e" : "#0d1017"
                        border.color: modelData.current ? Theme.tone2 : Theme.borderCard
                        border.width: modelData.current ? 2 : 1
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: ScaleMetrics.dp(10)
                            anchors.rightMargin: ScaleMetrics.dp(6)
                            spacing: ScaleMetrics.dp(6)
                            // Status dot
                            Rectangle {
                                width: ScaleMetrics.dp(8); height: ScaleMetrics.dp(8); radius: 4
                                color: modelData.status === "ok" ? "#10b981"
                                     : modelData.status === "updated" ? "#fbbf24"
                                     : modelData.status === "missing" ? "#ef4444" : "#64748b"
                            }
                            Text {
                                id: chipText
                                Layout.fillWidth: true
                                text: (index + 1) + ". " + modelData.name
                                font.bold: modelData.current
                                font.pixelSize: ScaleMetrics.sp(9)
                                color: modelData.current ? "#ffffff" : Theme.textSecondary
                                elide: Text.ElideRight
                            }
                            // Refresh action for stale links
                            Rectangle {
                                visible: modelData.status === "updated"
                                width: ScaleMetrics.dp(24); height: ScaleMetrics.dp(20)
                                radius: ScaleMetrics.dp(4)
                                color: refrMouse.pressed ? Theme.bgCardActive : "#3a2f10"
                                border.color: "#fbbf24"; border.width: 1
                                Text { anchors.centerIn: parent; text: "↻"; font.bold: true; font.pixelSize: ScaleMetrics.sp(10); color: "#fbbf24" }
                                MouseArea {
                                    id: refrMouse
                                    anchors.fill: parent
                                    onClicked: (mouse) => { mouse.accepted = true; Bridge.refreshPlaylistEntry(modelData.index) }
                                }
                            }
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: Bridge.loadPlaylistEntry(modelData.index)
                        }
                    }
                }
            }
        }
    }
}
