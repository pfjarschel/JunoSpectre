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

    // Read once per change (each Bridge read rebuilds every entry)
    readonly property var entries: Bridge.setlistEntries
    // The song LOAD & ACTIVATE plays; follows the sounding song on every change
    property int selectedIndex: Math.max(0, Bridge.setlistIndex)

    Connections {
        target: Bridge
        function onSongActivated(index) { root.selectedIndex = index }
        function onSetlistChanged() {
            root.selectedIndex = Math.max(0, Math.min(root.selectedIndex, Bridge.setlistCount - 1))
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: ScaleMetrics.dp(10)
        spacing: ScaleMetrics.dp(8)

        // 1. Top Header Bar
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(8)

            PageTitle { text: "SETLIST" }
            Text {
                Layout.fillWidth: true
                text: "• " + (Bridge.setlistPath !== "" ? Bridge.setlistPath : "Unsaved setlist")
                font.pixelSize: ScaleMetrics.sp(9)
                font.italic: true
                color: Theme.pageAccent
                elide: Text.ElideRight
            }

            // + Add Current Song
            SpButton {
                implicitHeight: ScaleMetrics.dp(28)
                icon: "add"
                text: "ADD CURRENT"
                fontSize: 8
                variant: "outline"
                onClicked: {
                    if (Bridge.addCurrentToSetlist(""))
                        root.selectedIndex = Bridge.setlistCount - 1
                }
            }

            // New Setlist
            SpButton {
                implicitHeight: ScaleMetrics.dp(28)
                implicitWidth: ScaleMetrics.dp(60)
                text: "NEW"
                fontSize: 8
                onClicked: Bridge.newSetlist()
            }

            // Save Setlist
            SpButton {
                implicitHeight: ScaleMetrics.dp(28)
                implicitWidth: ScaleMetrics.dp(60)
                text: "SAVE"
                fontSize: 8
                onClicked: Bridge.saveSetlistAuto()
            }

            Rectangle { width: 1; height: ScaleMetrics.dp(20); color: Theme.borderCard }

            PageLinks { group: "perform" }
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
                    model: root.entries
                    boundsBehavior: Flickable.StopAtBounds

                    delegate: Rectangle {
                        width: songList.width
                        height: ScaleMetrics.dp(44)
                        radius: ScaleMetrics.dp(4)
                        color: {
                            if (modelData.isCurrent) return Theme.tint(Theme.pageAccent, 0.25) // active sounding song purple
                            if (root.selectedIndex === modelData.index) return Theme.bgCardActive
                            return Theme.bgSurface
                        }
                        border.color: {
                            if (modelData.isCurrent) return Theme.pageAccent
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
                                color: modelData.isCurrent ? Theme.pageAccent : Theme.bgRaised
                                Text {
                                    anchors.centerIn: parent
                                    text: "" + (modelData.index + 1)
                                    font.bold: true
                                    font.pixelSize: ScaleMetrics.sp(8)
                                    color: modelData.isCurrent ? Theme.textPrimary : Theme.textDim
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
                                    color: modelData.isCurrent ? Theme.textPrimary : Theme.textPrimary
                                    elide: Text.ElideRight
                                }
                                Text {
                                    text: modelData.songFile !== "" ? modelData.songFile : "Snapshot only (no song file)"
                                    font.pixelSize: ScaleMetrics.sp(7)
                                    color: Theme.textDim
                                    elide: Text.ElideRight
                                }
                            }

                            // BPM badge
                            Rectangle {
                                width: ScaleMetrics.dp(50); height: ScaleMetrics.dp(20); radius: 3
                                color: Theme.bgControl
                                border.color: Theme.borderCard; border.width: 1
                                Text {
                                    anchors.centerIn: parent
                                    text: Math.round(modelData.bpm) + " BPM"
                                    font.pixelSize: ScaleMetrics.sp(7)
                                    font.bold: true
                                    color: Theme.pageAccent
                                }
                            }

                            // Link health badge (UPDATED: tap to take the song file's new version)
                            Rectangle {
                                width: ScaleMetrics.dp(56); height: ScaleMetrics.dp(20); radius: 3
                                MouseArea {
                                    anchors.fill: parent
                                    enabled: modelData.status === "updated"
                                    onClicked: Bridge.refreshSetlistEntry(modelData.index)
                                }
                                color: {
                                    if (modelData.status === "ok") return Theme.tint(Theme.playing, 0.25)
                                    if (modelData.status === "updated") return Theme.tint(Theme.warning, 0.25)
                                    if (modelData.status === "missing") return Theme.tint(Theme.recording, 0.25)
                                    return Theme.bgRaised
                                }
                                Text {
                                    anchors.centerIn: parent
                                    text: modelData.status.toUpperCase()
                                    font.bold: true
                                    font.pixelSize: ScaleMetrics.sp(6)
                                    color: {
                                        if (modelData.status === "ok") return Theme.playing
                                        if (modelData.status === "updated") return Theme.warning
                                        if (modelData.status === "missing") return Theme.recording
                                        return Theme.textDim
                                    }
                                }
                            }

                            // Reorder buttons: Up / Down
                            SpButton {
                                implicitWidth: ScaleMetrics.dp(22)
                                implicitHeight: ScaleMetrics.dp(22)
                                icon: "up"
                                fontSize: 8
                                onClicked: {
                                    if (modelData.index > 0) {
                                        Bridge.reorderSetlistEntry(modelData.index, modelData.index - 1)
                                        root.selectedIndex = modelData.index - 1
                                    }
                                }
                            }
                            SpButton {
                                implicitWidth: ScaleMetrics.dp(22)
                                implicitHeight: ScaleMetrics.dp(22)
                                icon: "down"
                                fontSize: 8
                                onClicked: {
                                    if (modelData.index + 1 < Bridge.setlistCount) {
                                        Bridge.reorderSetlistEntry(modelData.index, modelData.index + 1)
                                        root.selectedIndex = modelData.index + 1
                                    }
                                }
                            }

                            // Delete button
                            SpButton {
                                implicitWidth: ScaleMetrics.dp(22)
                                implicitHeight: ScaleMetrics.dp(22)
                                icon: "close"
                                fontSize: 8
                                variant: "danger"
                                onClicked: Bridge.removeSetlistEntry(modelData.index)
                            }
                        }
                    }

                    Text {
                        anchors.centerIn: parent
                        visible: Bridge.setlistCount === 0
                        text: "Setlist is empty.\nTap ADD CURRENT to add the song playing now."
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
                                text: root.selectedIndex < root.entries.length
                                      ? root.entries[root.selectedIndex].name
                                      : "No Song Selected"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(12)
                                color: Theme.textPrimary
                            }
                            Text {
                                text: Bridge.setlistIndex === root.selectedIndex
                                      ? "CURRENTLY SOUNDING LIVE"
                                      : "STAGED FOR SELECTION"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(7)
                                color: Bridge.setlistIndex === root.selectedIndex ? Theme.pageAccent : Theme.textDim
                            }
                        }
                    }

                    // ACTIVATE & LOAD SONG (Big Button)
                    Rectangle {
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(48)
                        radius: ScaleMetrics.dp(6)
                        color: activateMouse.pressed ? Theme.tint(Theme.pageAccent, 0.5) : Theme.pageAccent
                        border.color: Theme.pageAccent
                        border.width: 1

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: ScaleMetrics.dp(8)
                            Icon { name: "load"; size: 18; color: Theme.textOnFill }
                            Text {
                                text: "LOAD & ACTIVATE SONG"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(10)
                                font.letterSpacing: 1.2
                                color: Theme.textOnFill
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
                                Icon { name: "left"; size: 12; color: Theme.pageAccent }
                                Text { text: "PREV SONG"; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textPrimary }
                            }
                            MouseArea {
                                id: prevMouse
                                anchors.fill: parent
                                onClicked: Bridge.prevSong()
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
                                Icon { name: "right"; size: 12; color: Theme.pageAccent }
                            }
                            MouseArea {
                                id: nextMouse
                                anchors.fill: parent
                                onClicked: Bridge.nextSong()
                            }
                        }
                    }

                    Item { Layout.fillHeight: true }
                }
            }
        }
    }
}
