pragma ValueTypeBehavior: Copy
import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

// Live setlist strip: tap a song to load it, ◀/▶ to step through,
// + adds the current performance, − removes the highlighted song.
// Long-press a chip to pick it up, drag to a new spot (or tap the
// destination chip), DONE to finish. Status dot per song: green = linked
// & fresh, amber = file changed (tap ↻ to refresh snapshot), red = file
// missing (plays from snapshot), grey = snapshot only.
Rectangle {
    id: root
    color: Theme.bgApp
    radius: ScaleMetrics.dp(6)
    border.color: Theme.borderCard
    border.width: 1

    property var entries: Bridge.playlistEntries
    property int reorderIndex: -1
    property real ghostX: 0
    property string ghostName: ""
    property bool suppressClick: false

    onEntriesChanged: root.reorderIndex = -1

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
                visible: Bridge.playlistPath !== ""
                text: Bridge.playlistPath
                font.pixelSize: ScaleMetrics.sp(8)
                font.italic: true
                color: Theme.pageAccent
                elide: Text.ElideRight
                Layout.preferredWidth: ScaleMetrics.dp(140)
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
            Item { visible: root.entries.length > 0 && root.reorderIndex < 0; Layout.fillWidth: true }

            // Reorder hint (replaces transport buttons while dragging)
            Text {
                visible: root.reorderIndex >= 0
                Layout.fillWidth: true
                text: "Drag to a new spot, tap it, or DONE"
                font.pixelSize: ScaleMetrics.sp(8)
                font.italic: true
                color: Theme.pageAccent
                elide: Text.ElideRight
            }
            // DONE: leave reorder mode
            SpButton {
                visible: root.reorderIndex >= 0
                implicitWidth: ScaleMetrics.dp(64)
                implicitHeight: ScaleMetrics.dp(28)
                text: "DONE"
                fontSize: 8
                variant: "outline"
                onClicked: root.reorderIndex = -1
            }
            // Prev arrow
            SpButton {
                visible: root.entries.length > 0 && root.reorderIndex < 0
                implicitWidth: ScaleMetrics.dp(44)
                implicitHeight: ScaleMetrics.dp(28)
                icon: "left"
                fontSize: 12
                variant: "outline"
                onClicked: Bridge.prevPlaylistEntry()
            }
            // Next arrow
            SpButton {
                visible: root.entries.length > 0 && root.reorderIndex < 0
                implicitWidth: ScaleMetrics.dp(44)
                implicitHeight: ScaleMetrics.dp(28)
                icon: "right"
                fontSize: 12
                variant: "outline"
                onClicked: Bridge.nextPlaylistEntry()
            }
            // Add current performance as song
            SpButton {
                visible: root.reorderIndex < 0
                implicitWidth: ScaleMetrics.dp(44)
                implicitHeight: ScaleMetrics.dp(28)
                text: "+"
                fontSize: 14
                variant: "outline"
                onClicked: Bridge.addCurrentToPlaylist()
            }
            // Remove highlighted song from the setlist (file on disk untouched)
            SpButton {
                visible: root.entries.length > 0 && root.reorderIndex < 0
                implicitWidth: ScaleMetrics.dp(44)
                implicitHeight: ScaleMetrics.dp(28)
                text: "−"
                fontSize: 14
                variant: "danger"
                onClicked: Bridge.removePlaylistEntry(Bridge.playlistIndex)
            }
            // Save setlist (overwrite loaded path, else new Setlist N file)
            SpButton {
                visible: root.reorderIndex < 0
                implicitWidth: ScaleMetrics.dp(52)
                implicitHeight: ScaleMetrics.dp(28)
                text: "SAVE"
                fontSize: 8
                variant: "outline"
                onClicked: Bridge.savePlaylistAuto()
            }
            // New empty setlist (files on disk untouched)
            SpButton {
                visible: root.reorderIndex < 0
                implicitWidth: ScaleMetrics.dp(44)
                implicitHeight: ScaleMetrics.dp(28)
                text: "NEW"
                fontSize: 8
                onClicked: Bridge.newPlaylist()
            }
        }

        // Horizontal song chips (long-press picks one up, drag to re-spot)
        Flickable {
            id: chipFlick
            visible: root.entries.length > 0
            Layout.fillWidth: true
            Layout.preferredHeight: ScaleMetrics.dp(34)
            contentWidth: chipRow.width
            clip: true
            interactive: root.reorderIndex < 0
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
                        opacity: root.reorderIndex === modelData.index ? 0.35 : 1.0
                        color: root.reorderIndex === modelData.index ? Theme.tint(Theme.pageAccent, 0.4) : (modelData.current ? Theme.tint(Theme.pageAccent) : Theme.bgControl)
                        border.color: modelData.current ? Theme.pageAccent : Theme.borderCard
                        border.width: modelData.current ? 2 : 1
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: ScaleMetrics.dp(10)
                            anchors.rightMargin: ScaleMetrics.dp(6)
                            spacing: ScaleMetrics.dp(6)
                            // Status dot
                            Rectangle {
                                width: ScaleMetrics.dp(8); height: ScaleMetrics.dp(8); radius: 4
                                color: modelData.status === "ok" ? Theme.playing
                                     : modelData.status === "updated" ? Theme.warning
                                     : modelData.status === "missing" ? Theme.recording : Theme.textMuted
                            }
                            Text {
                                id: chipText
                                Layout.fillWidth: true
                                text: (index + 1) + ". " + modelData.name
                                font.bold: modelData.current
                                font.pixelSize: ScaleMetrics.sp(9)
                                color: modelData.current ? Theme.textPrimary : Theme.textSecondary
                                elide: Text.ElideRight
                            }
                            // Refresh action for stale links
                            SpButton {
                                visible: modelData.status === "updated"
                                implicitWidth: ScaleMetrics.dp(24)
                                implicitHeight: ScaleMetrics.dp(20)
                                icon: "restart"
                                fontSize: 10
                                variant: "warning"
                                onClicked: (mouse) => { mouse.accepted = true; Bridge.refreshPlaylistEntry(modelData.index) }
                            }
                        }
                        MouseArea {
                            id: chipMouse
                            anchors.fill: parent
                            property real pressX: 0
                            property bool dragging: false
                            onPressed: (mouse) => { pressX = mouse.x; dragging = false }
                            onPressAndHold: (mouse) => {
                                root.reorderIndex = modelData.index
                                root.ghostName = (modelData.index + 1) + ". " + modelData.name
                                var p = chipMouse.mapToItem(root, mouse.x, mouse.y)
                                root.ghostX = p.x
                                mouse.accepted = true
                            }
                            onPositionChanged: (mouse) => {
                                if (root.reorderIndex === modelData.index && pressed) {
                                    if (Math.abs(mouse.x - pressX) > 8) dragging = true
                                    if (dragging) {
                                        var p = chipMouse.mapToItem(root, mouse.x, mouse.y)
                                        root.ghostX = p.x
                                    }
                                }
                            }
                            onReleased: (mouse) => {
                                if (root.reorderIndex === modelData.index && dragging) {
                                    var lp = chipMouse.mapToItem(chipRow, mouse.x, mouse.y)
                                    var pos = 0
                                    var target = root.entries.length - 1
                                    for (var i = 0; i < chipRow.children.length; i++) {
                                        var c = chipRow.children[i]
                                        if (c.x === undefined || c.width === undefined) continue
                                        if (lp.x < c.x + c.width / 2) { target = pos; break }
                                        pos++
                                    }
                                    root.suppressClick = true
                                    if (target !== root.reorderIndex) Bridge.movePlaylistEntry(root.reorderIndex, target)
                                    root.reorderIndex = -1
                                    dragging = false
                                }
                            }
                            onClicked: {
                                if (root.suppressClick) { root.suppressClick = false; return }
                                if (root.reorderIndex >= 0) {
                                    // Reorder mode: tap another chip to move there,
                                    // tap the held chip (or DONE) to stay put.
                                    if (root.reorderIndex !== modelData.index) {
                                        Bridge.movePlaylistEntry(root.reorderIndex, modelData.index)
                                        root.reorderIndex = -1
                                    }
                                } else {
                                    Bridge.loadPlaylistEntry(modelData.index)
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // Floating drag ghost (follows the finger while reordering)
    Rectangle {
        visible: root.reorderIndex >= 0
        width: ScaleMetrics.dp(160)
        height: ScaleMetrics.dp(30)
        x: Math.max(0, Math.min(root.width - width, root.ghostX - width / 2))
        y: root.height - ScaleMetrics.dp(40)
        z: 10
        radius: ScaleMetrics.dp(15)
        color: Theme.tint(Theme.pageAccent)
        border.color: Theme.pageAccent
        border.width: 2
        Text {
            anchors.fill: parent
            anchors.leftMargin: ScaleMetrics.dp(12)
            anchors.rightMargin: ScaleMetrics.dp(12)
            verticalAlignment: Text.AlignVCenter
            text: root.ghostName
            font.bold: true
            font.pixelSize: ScaleMetrics.sp(9)
            color: Theme.textPrimary
            elide: Text.ElideRight
        }
    }
}
