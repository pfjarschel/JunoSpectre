pragma ValueTypeBehavior: Copy
import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

// Permanent right-flank FX rail for the PERFORMANCE screen.
// 5 compact cards (MFX1-3 + chorus + reverb) with Origin selectors,
// MFX "Editing" radio (target for MFX Studio), copy-to-PERFORM head-start,
// and per-slot part counts.
//
// NOTE: all cross-item references are id-qualified (choCard._src, ...).
// Bare-name lookups do not resolve across plain-item boundaries here.
Rectangle {
    id: rail
    color: Theme.bgApp
    radius: ScaleMetrics.dp(6)
    border.color: Theme.borderCard
    border.width: 1

    property var fxSlots: Bridge.perfFxSlots
    property var allParts: Bridge.perfParts
    property int editingSlot: Bridge.editingPerfMfx
    readonly property bool busy: Bridge.perfPushProgress >= 0

    // Defensive refresh: re-pull lists when the bridge signals change,
    // so card bindings never stick to a stale JS object.
    Connections {
        target: Bridge
        function onPerfFxChanged() {
            rail.fxSlots = Bridge.perfFxSlots;
            rail.editingSlot = Bridge.editingPerfMfx;
        }
        function onPerfPartsChanged() {
            rail.allParts = Bridge.perfParts;
        }
    }

    function feedsCount(slot) {
        var n = 0;
        if (!rail.allParts) return 0;
        for (var i = 0; i < rail.allParts.length; ++i) {
            if (rail.allParts[i].mfxSelect === (slot - 1)) n++;
        }
        return n;
    }
    function cycleOrigin(kind, cur) {
        // PERFORM(0) -> 1 -> 2 ... -> 16 -> PERFORM
        var nxt = (cur + 1) % 17;
        Bridge.setPerfSource(kind, nxt);
    }
    function mfxEntry(slot) {
        if (rail.fxSlots && rail.fxSlots.length >= slot && rail.fxSlots[slot - 1]
                && rail.fxSlots[slot - 1].kind === ("MFX" + slot))
            return rail.fxSlots[slot - 1];
        return null;
    }
    function choEntry() {
        if (rail.fxSlots && rail.fxSlots.length > 3 && rail.fxSlots[3]
                && rail.fxSlots[3].kind === "CHORUS")
            return rail.fxSlots[3];
        return null;
    }
    function revEntry() {
        if (rail.fxSlots && rail.fxSlots.length > 4 && rail.fxSlots[4]
                && rail.fxSlots[4].kind === "REVERB")
            return rail.fxSlots[4];
        return null;
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: ScaleMetrics.dp(5)
        contentWidth: width
        contentHeight: contentCol.height
        clip: true
        interactive: contentHeight > height

        ColumnLayout {
            id: contentCol
            width: parent.width
            spacing: ScaleMetrics.dp(4)

            Text {
                text: "PERF FX"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(8)
                font.letterSpacing: 1.0
                color: Theme.textSecondary
                Layout.alignment: Qt.AlignHCenter
            }

            // MFX cards
            Repeater {
                model: [1, 2, 3]
                delegate: Rectangle {
                    id: mfxCard
                    Layout.fillWidth: true
                    height: ScaleMetrics.dp(58)
                    radius: ScaleMetrics.dp(4)
                    color: rail.editingSlot === modelData ? "#1c1533" : "#0f172a"
                    border.color: rail.editingSlot === modelData ? Theme.tone2 : Theme.borderCard
                    border.width: rail.editingSlot === modelData ? 2 : 1
                    property var entry: rail.mfxEntry(modelData)
                    property int src: mfxCard.entry ? mfxCard.entry.source : 0
                    property int feeds: rail.feedsCount(modelData)

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: ScaleMetrics.dp(4)
                        spacing: ScaleMetrics.dp(2)
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: ScaleMetrics.dp(3)
                            Rectangle {
                                width: ScaleMetrics.dp(16); height: ScaleMetrics.dp(14)
                                radius: 2
                                color: rail.editingSlot === modelData ? Theme.tone2 : "#1e293b"
                                Text {
                                    anchors.centerIn: parent
                                    text: "●"
                                    font.pixelSize: ScaleMetrics.sp(7)
                                    color: rail.editingSlot === modelData ? "#fff" : Theme.textDim
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    enabled: !rail.busy
                                    onClicked: Bridge.setEditingPerfMfx(modelData)
                                }
                            }
                            Text {
                                text: "MFX" + modelData + " T" + (mfxCard.entry ? mfxCard.entry.type : 0)
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(8)
                                font.family: Theme.fontMono
                                color: Theme.textPrimary
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }
                            Text {
                                text: mfxCard.feeds + " PARTS"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(6)
                                font.family: Theme.fontMono
                                color: mfxCard.feeds > 0 ? Theme.tone2 : Theme.textDim
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: ScaleMetrics.dp(3)
                            Rectangle {
                                Layout.fillWidth: true
                                height: ScaleMetrics.dp(18)
                                radius: 3
                                color: mfxCard.src === 0 ? "#0e3a47" : "#2e1a06"
                                border.color: mfxCard.src === 0 ? "#06b6d4" : Theme.warning
                                border.width: 1
                                Text {
                                    anchors.centerIn: parent
                                    text: mfxCard.src === 0 ? "PERFORM" : "PART " + mfxCard.src
                                    font.bold: true
                                    font.pixelSize: ScaleMetrics.sp(7)
                                    color: mfxCard.src === 0 ? "#67e8f9" : Theme.warning
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    enabled: !rail.busy
                                    onClicked: rail.cycleOrigin("mfx" + modelData, mfxCard.src)
                                }
                            }
                            Rectangle {
                                visible: mfxCard.src !== 0
                                width: ScaleMetrics.dp(44); height: ScaleMetrics.dp(18)
                                radius: 3
                                color: Theme.bgSurface
                                border.color: Theme.tone1
                                border.width: 1
                                Text {
                                    anchors.centerIn: parent
                                    text: "⧉→PERF"
                                    font.bold: true
                                    font.pixelSize: ScaleMetrics.sp(6)
                                    color: Theme.tone1
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    enabled: !rail.busy
                                    onClicked: Bridge.copyOriginToPerform("mfx" + modelData)
                                }
                            }
                        }
                    }
                }
            }

            // Chorus card
            Rectangle {
                id: choCard
                Layout.fillWidth: true
                height: ScaleMetrics.dp(50)
                radius: ScaleMetrics.dp(4)
                color: "#0f172a"
                border.color: Theme.borderCard
                border.width: 1
                property var entry: rail.choEntry()
                property int src: choCard.entry ? choCard.entry.source : 0
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(4)
                    spacing: ScaleMetrics.dp(2)
                    Text {
                        text: "CHORUS T" + (choCard.entry ? choCard.entry.type : 0)
                              + " Lv" + (choCard.entry ? choCard.entry.level : 0)
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        font.family: Theme.fontMono
                        color: Theme.textPrimary
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: ScaleMetrics.dp(3)
                        Rectangle {
                            Layout.fillWidth: true
                            height: ScaleMetrics.dp(18)
                            radius: 3
                            color: choCard.src === 0 ? "#0e3a47" : "#2e1a06"
                            border.color: choCard.src === 0 ? "#06b6d4" : Theme.warning
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: choCard.src === 0 ? "PERFORM" : "PART " + choCard.src
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(7)
                                color: choCard.src === 0 ? "#67e8f9" : Theme.warning
                            }
                            MouseArea {
                                anchors.fill: parent
                                enabled: !rail.busy
                                onClicked: rail.cycleOrigin("chorus", choCard.src)
                            }
                        }
                        Rectangle {
                            visible: choCard.src !== 0
                            width: ScaleMetrics.dp(44); height: ScaleMetrics.dp(18)
                            radius: 3
                            color: Theme.bgSurface
                            border.color: Theme.tone1
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: "⧉→PERF"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(6)
                                color: Theme.tone1
                            }
                            MouseArea {
                                anchors.fill: parent
                                enabled: !rail.busy
                                onClicked: Bridge.copyOriginToPerform("chorus")
                            }
                        }
                    }
                }
            }

            // Reverb card
            Rectangle {
                id: revCard
                Layout.fillWidth: true
                height: ScaleMetrics.dp(50)
                radius: ScaleMetrics.dp(4)
                color: "#0f172a"
                border.color: Theme.borderCard
                border.width: 1
                property var entry: rail.revEntry()
                property int src: revCard.entry ? revCard.entry.source : 0
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(4)
                    spacing: ScaleMetrics.dp(2)
                    Text {
                        text: "REVERB T" + (revCard.entry ? revCard.entry.type : 0)
                              + " Lv" + (revCard.entry ? revCard.entry.level : 0)
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        font.family: Theme.fontMono
                        color: Theme.textPrimary
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: ScaleMetrics.dp(3)
                        Rectangle {
                            Layout.fillWidth: true
                            height: ScaleMetrics.dp(18)
                            radius: 3
                            color: revCard.src === 0 ? "#0e3a47" : "#2e1a06"
                            border.color: revCard.src === 0 ? "#06b6d4" : Theme.warning
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: revCard.src === 0 ? "PERFORM" : "PART " + revCard.src
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(7)
                                color: revCard.src === 0 ? "#67e8f9" : Theme.warning
                            }
                            MouseArea {
                                anchors.fill: parent
                                enabled: !rail.busy
                                onClicked: rail.cycleOrigin("reverb", revCard.src)
                            }
                        }
                        Rectangle {
                            visible: revCard.src !== 0
                            width: ScaleMetrics.dp(44); height: ScaleMetrics.dp(18)
                            radius: 3
                            color: Theme.bgSurface
                            border.color: Theme.tone1
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: "⧉→PERF"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(6)
                                color: Theme.tone1
                            }
                            MouseArea {
                                anchors.fill: parent
                                enabled: !rail.busy
                                onClicked: Bridge.copyOriginToPerform("reverb")
                            }
                        }
                    }
                }
            }
        }
    }
}
