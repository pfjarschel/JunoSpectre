pragma ValueTypeBehavior: Copy
import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

Rectangle {
    id: root
    color: Theme.bgCard
    radius: ScaleMetrics.dp(8)
    border.color: Theme.borderCard
    border.width: 1

    property int selectedIndex: Bridge.setlistIndex >= 0 ? Bridge.setlistIndex : 0

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: ScaleMetrics.dp(10)
        spacing: ScaleMetrics.dp(8)

        // 1. Top Header Bar
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(8)

            Rectangle {
                width: ScaleMetrics.dp(8); height: ScaleMetrics.dp(8); radius: 4
                color: Theme.tone2
            }
            Text {
                text: "SETLIST & REPERTOIRE"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(12)
                font.letterSpacing: 1.2
                color: Theme.textPrimary
            }
            Text {
                text: "• " + (Bridge.setlistPath !== "" ? Bridge.setlistPath : "Untitled Setlist")
                font.pixelSize: ScaleMetrics.sp(9)
                font.italic: true
                color: Theme.tone2
            }
            Item { Layout.fillWidth: true }

            // + Add Current Song
            Rectangle {
                height: ScaleMetrics.dp(28)
                implicitWidth: ScaleMetrics.dp(120)
                radius: 4
                color: addMouse.pressed ? Theme.bgCardActive : Theme.bgSurface
                border.color: Theme.tone2
                border.width: 1
                RowLayout {
                    anchors.centerIn: parent
                    spacing: 4
                    Text { text: "+"; font.bold: true; font.pixelSize: ScaleMetrics.sp(11); color: Theme.tone2 }
                    Text { text: "ADD CURRENT"; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: Theme.tone2 }
                }
                MouseArea {
                    id: addMouse
                    anchors.fill: parent
                    onClicked: {
                        Bridge.addCurrentToSetlist("")
                        root.selectedIndex = Bridge.setlistCount - 1
                    }
                }
            }

            // New Setlist
            Rectangle {
                height: ScaleMetrics.dp(28)
                implicitWidth: ScaleMetrics.dp(60)
                radius: 4
                color: newMouse.pressed ? Theme.bgCardActive : Theme.bgSurface
                border.color: Theme.borderCard
                border.width: 1
                Text { anchors.centerIn: parent; text: "NEW"; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textDim }
                MouseArea { id: newMouse; anchors.fill: parent; onClicked: Bridge.newSetlist() }
            }

            // Save Setlist
            Rectangle {
                height: ScaleMetrics.dp(28)
                implicitWidth: ScaleMetrics.dp(60)
                radius: 4
                color: saveMouse.pressed ? Theme.bgCardActive : Theme.bgSurface
                border.color: Theme.borderCard
                border.width: 1
                Text { anchors.centerIn: parent; text: "SAVE"; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textDim }
                MouseArea { id: saveMouse; anchors.fill: parent; onClicked: Bridge.saveSetlistAuto() }
            }
        }

        // 2. Main Workspace: 2-Column Layout
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: ScaleMetrics.dp(10)

            // Column 1: Song List (Left, ~65% width)
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: ScaleMetrics.dp(6)
                color: Theme.bgApp
                border.color: Theme.borderCard
                border.width: 1
                clip: true

                ListView {
                    id: songList
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(6)
                    spacing: ScaleMetrics.dp(5)
                    model: Bridge.setlistEntries
                    boundsBehavior: Flickable.StopAtBounds

                    delegate: Rectangle {
                        width: songList.width
                        height: ScaleMetrics.dp(44)
                        radius: ScaleMetrics.dp(4)
                        color: {
                            if (modelData.isCurrent) return "#2e1065" // active sounding song purple
                            if (root.selectedIndex === modelData.index) return Theme.bgCardActive
                            return Theme.bgSurface
                        }
                        border.color: {
                            if (modelData.isCurrent) return Theme.tone2
                            if (root.selectedIndex === modelData.index) return Theme.borderActive
                            return Theme.borderCard
                        }
                        border.width: 1

                        MouseArea {
                            anchors.fill: parent
                            onClicked: root.selectedIndex = modelData.index
                            onDoubleClicked: {
                                root.selectedIndex = modelData.index
                                Bridge.activateSong(modelData.index)
                            }
                        }

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: ScaleMetrics.dp(8)
                            anchors.rightMargin: ScaleMetrics.dp(8)
                            spacing: ScaleMetrics.dp(8)

                            // Index badge
                            Rectangle {
                                width: ScaleMetrics.dp(22); height: ScaleMetrics.dp(22); radius: 11
                                color: modelData.isCurrent ? Theme.tone2 : "#1e293b"
                                Text {
                                    anchors.centerIn: parent
                                    text: "" + (modelData.index + 1)
                                    font.bold: true
                                    font.pixelSize: ScaleMetrics.sp(8)
                                    color: modelData.isCurrent ? "#ffffff" : Theme.textDim
                                }
                            }

                            // Song title + path
                            ColumnLayout {
                                spacing: 1
                                Layout.fillWidth: true
                                Text {
                                    text: modelData.name
                                    font.bold: true
                                    font.pixelSize: ScaleMetrics.sp(10)
                                    color: modelData.isCurrent ? "#ffffff" : Theme.textPrimary
                                    elide: Text.ElideRight
                                }
                                Text {
                                    text: modelData.songPath !== "" ? modelData.songPath : "Embedded Snapshot"
                                    font.pixelSize: ScaleMetrics.sp(7)
                                    color: Theme.textDim
                                    elide: Text.ElideRight
                                }
                            }

                            // BPM badge
                            Rectangle {
                                width: ScaleMetrics.dp(50); height: ScaleMetrics.dp(20); radius: 3
                                color: "#0f172a"
                                border.color: Theme.borderCard; border.width: 1
                                Text {
                                    anchors.centerIn: parent
                                    text: Math.round(modelData.bpm) + " BPM"
                                    font.pixelSize: ScaleMetrics.sp(7)
                                    font.bold: true
                                    color: Theme.tone1
                                }
                            }

                            // Health status badge
                            Rectangle {
                                width: ScaleMetrics.dp(56); height: ScaleMetrics.dp(20); radius: 3
                                color: {
                                    if (modelData.status === "ok") return "#064e3b"
                                    if (modelData.status === "updated") return "#78350f"
                                    if (modelData.status === "missing") return "#7f1d1d"
                                    return "#1e293b"
                                }
                                Text {
                                    anchors.centerIn: parent
                                    text: modelData.status.toUpperCase()
                                    font.bold: true
                                    font.pixelSize: ScaleMetrics.sp(6)
                                    color: {
                                        if (modelData.status === "ok") return "#10b981"
                                        if (modelData.status === "updated") return "#f59e0b"
                                        if (modelData.status === "missing") return "#ef4444"
                                        return Theme.textDim
                                    }
                                }
                            }

                            // Reorder buttons: Up / Down
                            Rectangle {
                                width: ScaleMetrics.dp(22); height: ScaleMetrics.dp(22); radius: 3
                                color: Theme.bgApp; border.color: Theme.borderCard; border.width: 1
                                Text { anchors.centerIn: parent; text: "▲"; font.pixelSize: ScaleMetrics.sp(7); color: Theme.textDim }
                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: {
                                        if (modelData.index > 0) {
                                            Bridge.reorderSetlistEntry(modelData.index, modelData.index - 1)
                                            root.selectedIndex = modelData.index - 1
                                        }
                                    }
                                }
                            }
                            Rectangle {
                                width: ScaleMetrics.dp(22); height: ScaleMetrics.dp(22); radius: 3
                                color: Theme.bgApp; border.color: Theme.borderCard; border.width: 1
                                Text { anchors.centerIn: parent; text: "▼"; font.pixelSize: ScaleMetrics.sp(7); color: Theme.textDim }
                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: {
                                        if (modelData.index + 1 < Bridge.setlistCount) {
                                            Bridge.reorderSetlistEntry(modelData.index, modelData.index + 1)
                                            root.selectedIndex = modelData.index + 1
                                        }
                                    }
                                }
                            }

                            // Delete button
                            Rectangle {
                                width: ScaleMetrics.dp(22); height: ScaleMetrics.dp(22); radius: 3
                                color: "#3f1a1a"; border.color: Theme.borderCard; border.width: 1
                                Text { anchors.centerIn: parent; text: "✕"; font.pixelSize: ScaleMetrics.sp(7); color: "#ef4444" }
                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: Bridge.removeSetlistEntry(modelData.index)
                                }
                            }
                        }
                    }

                    Text {
                        anchors.centerIn: parent
                        visible: Bridge.setlistCount === 0
                        text: "Setlist is empty.\nTap '+ ADD CURRENT' to snapshot active songs into this repertoire."
                        font.pixelSize: ScaleMetrics.sp(9)
                        font.italic: true
                        color: Theme.textDim
                        horizontalAlignment: Text.AlignHCenter
                    }
                }
            }

            // Column 2: Stage Controller Panel (Right, ~35% width)
            Rectangle {
                Layout.preferredWidth: ScaleMetrics.dp(320)
                Layout.fillHeight: true
                radius: ScaleMetrics.dp(6)
                color: Theme.bgApp
                border.color: Theme.borderCard
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(12)
                    spacing: ScaleMetrics.dp(10)

                    Text {
                        text: "STAGE CONTROL"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(9)
                        font.letterSpacing: 1.2
                        color: Theme.textDim
                    }

                    // Selected Song Banner
                    Rectangle {
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(60)
                        radius: ScaleMetrics.dp(4)
                        color: Theme.bgSurface
                        border.color: Theme.borderCard
                        border.width: 1

                        ColumnLayout {
                            anchors.centerIn: parent
                            spacing: 2
                            Text {
                                text: Bridge.setlistCount > 0 && root.selectedIndex < Bridge.setlistCount
                                      ? Bridge.setlistEntries[root.selectedIndex].name
                                      : "No Song Selected"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(12)
                                color: Theme.textPrimary
                            }
                            Text {
                                text: Bridge.setlistIndex === root.selectedIndex
                                      ? "● CURRENTLY SOUNDING LIVE"
                                      : "STAGED FOR SELECTION"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(7)
                                color: Bridge.setlistIndex === root.selectedIndex ? Theme.tone2 : Theme.textDim
                            }
                        }
                    }

                    // ACTIVATE & LOAD SONG (Big Button)
                    Rectangle {
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(48)
                        radius: ScaleMetrics.dp(6)
                        color: activateMouse.pressed ? "#581c87" : Theme.tone2
                        border.color: "#c084fc"
                        border.width: 1

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: ScaleMetrics.dp(8)
                            Text { text: "⚡"; font.pixelSize: ScaleMetrics.sp(14); color: "#ffffff" }
                            Text {
                                text: "LOAD & ACTIVATE SONG"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(10)
                                font.letterSpacing: 1.2
                                color: "#ffffff"
                            }
                        }

                        MouseArea {
                            id: activateMouse
                            anchors.fill: parent
                            onClicked: {
                                if (Bridge.setlistCount > 0 && root.selectedIndex < Bridge.setlistCount) {
                                    Bridge.activateSong(root.selectedIndex)
                                }
                            }
                        }
                    }

                    // Stepper: ◀ PREV / NEXT ▶
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: ScaleMetrics.dp(8)

                        Rectangle {
                            Layout.fillWidth: true
                            height: ScaleMetrics.dp(38)
                            radius: ScaleMetrics.dp(4)
                            color: prevMouse.pressed ? Theme.bgCardActive : Theme.bgSurface
                            border.color: Theme.borderCard; border.width: 1
                            RowLayout {
                                anchors.centerIn: parent; spacing: 4
                                Text { text: "◀"; font.pixelSize: ScaleMetrics.sp(9); color: Theme.tone2 }
                                Text { text: "PREV SONG"; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textPrimary }
                            }
                            MouseArea {
                                id: prevMouse
                                anchors.fill: parent
                                onClicked: {
                                    if (root.selectedIndex > 0) root.selectedIndex--
                                    Bridge.prevSong()
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: ScaleMetrics.dp(38)
                            radius: ScaleMetrics.dp(4)
                            color: nextMouse.pressed ? Theme.bgCardActive : Theme.bgSurface
                            border.color: Theme.borderCard; border.width: 1
                            RowLayout {
                                anchors.centerIn: parent; spacing: 4
                                Text { text: "NEXT SONG"; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textPrimary }
                                Text { text: "▶"; font.pixelSize: ScaleMetrics.sp(9); color: Theme.tone2 }
                            }
                            MouseArea {
                                id: nextMouse
                                anchors.fill: parent
                                onClicked: {
                                    if (root.selectedIndex + 1 < Bridge.setlistCount) root.selectedIndex++
                                    Bridge.nextSong()
                                }
                            }
                        }
                    }

                    Item { Layout.fillHeight: true }

                    // Navigation Quick Links
                    Rectangle { width: parent.width; height: 1; color: Theme.borderCard }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: ScaleMetrics.dp(6)

                        Rectangle {
                            Layout.fillWidth: true
                            height: ScaleMetrics.dp(32)
                            radius: 4
                            color: Theme.bgSurface
                            border.color: Theme.tone1; border.width: 1
                            Text { anchors.centerIn: parent; text: "▶ LIVE MODE"; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: Theme.tone1 }
                            MouseArea { anchors.fill: parent; onClicked: Bridge.setActiveView("LIVE") }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: ScaleMetrics.dp(32)
                            radius: 4
                            color: Theme.bgSurface
                            border.color: Theme.borderCard; border.width: 1
                            Text { anchors.centerIn: parent; text: "🎛 MIXER"; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textDim }
                            MouseArea { anchors.fill: parent; onClicked: Bridge.setActiveView("PERFORMANCE") }
                        }
                    }
                }
            }
        }
    }
}
