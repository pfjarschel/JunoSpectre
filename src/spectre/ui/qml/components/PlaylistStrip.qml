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
                color: Theme.tone1
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
                color: Theme.tone2
                elide: Text.ElideRight
            }
            // DONE: leave reorder mode
            Rectangle {
                visible: root.reorderIndex >= 0
                width: ScaleMetrics.dp(64); height: ScaleMetrics.dp(28)
                radius: ScaleMetrics.dp(4)
                color: doneMouse.pressed ? Theme.bgCardActive : Theme.bgSurface
                border.color: Theme.tone2; border.width: 1
                Text { anchors.centerIn: parent; text: "DONE"; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: Theme.tone2 }
                MouseArea { id: doneMouse; anchors.fill: parent; onClicked: root.reorderIndex = -1 }
            }
            // Prev arrow
            Rectangle {
                visible: root.entries.length > 0 && root.reorderIndex < 0
                width: ScaleMetrics.dp(44); height: ScaleMetrics.dp(28)
                radius: ScaleMetrics.dp(4)
                color: prevMouse.pressed ? Theme.bgCardActive : Theme.bgSurface
                border.color: Theme.tone2; border.width: 1
                Text { anchors.centerIn: parent; text: "◀"; font.bold: true; font.pixelSize: ScaleMetrics.sp(12); color: Theme.tone2 }
                MouseArea { id: prevMouse; anchors.fill: parent; onClicked: Bridge.prevPlaylistEntry() }
            }
            // Next arrow
            Rectangle {
                visible: root.entries.length > 0 && root.reorderIndex < 0
                width: ScaleMetrics.dp(44); height: ScaleMetrics.dp(28)
                radius: ScaleMetrics.dp(4)
                color: nextMouse.pressed ? Theme.bgCardActive : Theme.bgSurface
                border.color: Theme.tone2; border.width: 1
                Text { anchors.centerIn: parent; text: "▶"; font.bold: true; font.pixelSize: ScaleMetrics.sp(12); color: Theme.tone2 }
                MouseArea { id: nextMouse; anchors.fill: parent; onClicked: Bridge.nextPlaylistEntry() }
            }
            // Add current performance as song
            Rectangle {
                visible: root.reorderIndex < 0
                width: ScaleMetrics.dp(44); height: ScaleMetrics.dp(28)
                radius: ScaleMetrics.dp(4)
                color: addMouse.pressed ? Theme.bgCardActive : Theme.bgSurface
                border.color: Theme.tone1; border.width: 1
                Text { anchors.centerIn: parent; text: "+"; font.bold: true; font.pixelSize: ScaleMetrics.sp(14); color: Theme.tone1 }
                MouseArea { id: addMouse; anchors.fill: parent; onClicked: Bridge.addCurrentToPlaylist() }
            }
            // Remove highlighted song from the setlist (file on disk untouched)
            Rectangle {
                visible: root.entries.length > 0 && root.reorderIndex < 0
                width: ScaleMetrics.dp(44); height: ScaleMetrics.dp(28)
                radius: ScaleMetrics.dp(4)
                color: delMouse.pressed ? Theme.bgCardActive : Theme.bgSurface
                border.color: "#ef4444"; border.width: 1
                Text { anchors.centerIn: parent; text: "−"; font.bold: true; font.pixelSize: ScaleMetrics.sp(14); color: "#ef4444" }
                MouseArea { id: delMouse; anchors.fill: parent; onClicked: Bridge.removePlaylistEntry(Bridge.playlistIndex) }
            }
            // Save setlist (overwrite loaded path, else new Setlist N file)
            Rectangle {
                visible: root.reorderIndex < 0
                width: ScaleMetrics.dp(52); height: ScaleMetrics.dp(28)
                radius: ScaleMetrics.dp(4)
                color: savePlMouse.pressed ? Theme.bgCardActive : Theme.bgSurface
                border.color: "#38bdf8"; border.width: 1
                Text { anchors.centerIn: parent; text: "SAVE"; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: "#38bdf8" }
                MouseArea { id: savePlMouse; anchors.fill: parent; onClicked: Bridge.savePlaylistAuto() }
            }
            // New empty setlist (files on disk untouched)
            Rectangle {
                visible: root.reorderIndex < 0
                width: ScaleMetrics.dp(44); height: ScaleMetrics.dp(28)
                radius: ScaleMetrics.dp(4)
                color: newPlMouse.pressed ? Theme.bgCardActive : Theme.bgSurface
                border.color: Theme.borderCard; border.width: 1
                Text { anchors.centerIn: parent; text: "NEW"; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textSecondary }
                MouseArea { id: newPlMouse; anchors.fill: parent; onClicked: Bridge.newPlaylist() }
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
                        color: root.reorderIndex === modelData.index ? Theme.tone2 : (modelData.current ? "#2d1b4e" : "#0d1017")
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
        color: "#2d1b4e"
        border.color: Theme.tone2
        border.width: 2
        Text {
            anchors.fill: parent
            anchors.leftMargin: ScaleMetrics.dp(12)
            anchors.rightMargin: ScaleMetrics.dp(12)
            verticalAlignment: Text.AlignVCenter
            text: "✥ " + root.ghostName
            font.bold: true
            font.pixelSize: ScaleMetrics.sp(9)
            color: "#ffffff"
            elide: Text.ElideRight
        }
    }
}
