pragma ValueTypeBehavior: Copy
import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

// Global modal (PERFORM): which part the editors work on and which MFX
// MFX Studio edits. Opened from the header's "P3 · MFX2" tag. Picking a part
// also picks the MFX its sound enters; one tap and it closes.
Rectangle {
    id: root
    anchors.fill: parent
    visible: false
    z: 998
    color: "#e60a0c10"

    readonly property color partColor: "#c084fc"
    readonly property color mfxColor: "#ec4899"
    readonly property var parts: Bridge.perfParts
    readonly property var status: Bridge.partFileStatus
    readonly property var mfxSlots: Bridge.perfFxSlots
    readonly property int activePart: Bridge.activePerfPart
    readonly property int editingMfx: Bridge.editingPerfMfx
    readonly property int structure: Bridge.perfStructure

    function open() {
        visible = true;
    }
    function close() {
        visible = false;
    }
    // MFX (1..3) a part enters, 0 = direct to the output
    function entryOf(p) {
        if (!p) return 0;
        var a = p.outputAssign;
        if (a === 1 || a === 5 || a === 6) return 0;
        return (p.mfxSelect || 0) + 1;
    }
    function routeText(p) {
        var a = p.outputAssign;
        if (a === 1) return "L+R";
        if (a === 5) return "OUT L";
        if (a === 6) return "OUT R";
        return "→ MFX" + entryOf(p);
    }

    MouseArea {
        anchors.fill: parent
        onClicked: root.close()
    }

    Rectangle {
        id: card
        width: Math.min(parent.width - ScaleMetrics.dp(24), ScaleMetrics.dp(820))
        height: content.implicitHeight + ScaleMetrics.dp(28)
        anchors.centerIn: parent
        radius: ScaleMetrics.dp(10)
        color: Theme.bgCard
        border.color: Theme.borderActive
        border.width: 1

        MouseArea {
            anchors.fill: parent
        }

        ColumnLayout {
            id: content
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: ScaleMetrics.dp(14)
            spacing: ScaleMetrics.dp(8)

            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: "EDIT"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(12)
                    color: Theme.textPrimary
                }
                Text {
                    Layout.fillWidth: true
                    text: "Editors work on this part, MFX Studio on this MFX. A part brings its MFX along."
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: Theme.textDim
                    elide: Text.ElideRight
                }
                Rectangle {
                    implicitWidth: ScaleMetrics.dp(34)
                    implicitHeight: ScaleMetrics.dp(28)
                    radius: ScaleMetrics.dp(4)
                    color: "#10141d"
                    border.color: Theme.borderCard
                    Text {
                        anchors.centerIn: parent
                        text: "✕"
                        font.pixelSize: ScaleMetrics.sp(11)
                        color: Theme.textSecondary
                    }
                    MouseArea {
                        anchors.fill: parent
                        onClicked: root.close()
                    }
                }
            }

            Text {
                text: "PART"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(8)
                color: root.partColor
            }
            GridLayout {
                Layout.fillWidth: true
                columns: 8
                rowSpacing: ScaleMetrics.dp(5)
                columnSpacing: ScaleMetrics.dp(5)
                Repeater {
                    model: root.parts
                    delegate: Rectangle {
                        id: tile
                        required property var modelData
                        required property int index
                        readonly property bool active: modelData.index === root.activePart
                        readonly property bool edited: root.status && root.status[index] === "edited"
                        Layout.fillWidth: true
                        Layout.preferredHeight: ScaleMetrics.dp(66)
                        radius: ScaleMetrics.dp(5)
                        color: active ? Theme.bgCardActive : (tileMouse.pressed ? "#1a1f2b" : "#10141d")
                        border.color: active ? root.partColor : Theme.borderCard
                        border.width: active ? 2 : 1
                        opacity: modelData.muted ? 0.45 : 1.0

                        Text {
                            x: ScaleMetrics.dp(6); y: ScaleMetrics.dp(4)
                            text: "P" + tile.modelData.index
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(9)
                            color: root.partColor
                        }
                        Text {
                            anchors.right: parent.right
                            anchors.rightMargin: ScaleMetrics.dp(6)
                            y: ScaleMetrics.dp(4)
                            visible: tile.edited || tile.modelData.muted
                            text: tile.modelData.muted ? "MUTE" : "✎"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(7)
                            color: tile.modelData.muted ? Theme.recording : "#60a5fa"
                        }
                        Text {
                            x: ScaleMetrics.dp(6)
                            y: ScaleMetrics.dp(20)
                            width: parent.width - ScaleMetrics.dp(12)
                            text: tile.modelData.name
                            wrapMode: Text.WrapAnywhere
                            maximumLineCount: 2
                            elide: Text.ElideRight
                            font.bold: tile.active
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: tile.active ? Theme.textPrimary : Theme.textSecondary
                        }
                        Text {
                            x: ScaleMetrics.dp(6)
                            anchors.bottom: parent.bottom
                            anchors.bottomMargin: ScaleMetrics.dp(4)
                            text: root.routeText(tile.modelData)
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(7)
                            color: root.entryOf(tile.modelData) ? root.mfxColor : Theme.textDim
                        }
                        MouseArea {
                            id: tileMouse
                            anchors.fill: parent
                            onClicked: {
                                Bridge.editPerfPart(tile.modelData.index);
                                root.close();
                            }
                        }
                    }
                }
            }

            Text {
                text: "MFX"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(8)
                color: root.mfxColor
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: ScaleMetrics.dp(6)
                Repeater {
                    model: [1, 2, 3]
                    delegate: Rectangle {
                        id: mfxBtn
                        required property int modelData
                        readonly property var slot: root.mfxSlots.length >= 3 ? root.mfxSlots[modelData - 1] : null
                        readonly property bool active: modelData === root.editingMfx
                        readonly property bool entered: root.entryOf(root.parts[root.activePart - 1]) === modelData
                        Layout.fillWidth: true
                        Layout.preferredHeight: ScaleMetrics.dp(52)
                        radius: ScaleMetrics.dp(5)
                        color: active ? Theme.bgCardActive : (mfxMouse.pressed ? "#1a1f2b" : "#10141d")
                        border.color: active ? root.mfxColor : Theme.borderCard
                        border.width: active ? 2 : 1
                        Column {
                            anchors.left: parent.left
                            anchors.leftMargin: ScaleMetrics.dp(8)
                            anchors.right: parent.right
                            anchors.rightMargin: ScaleMetrics.dp(8)
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: ScaleMetrics.dp(2)
                            Row {
                                spacing: ScaleMetrics.dp(6)
                                Text {
                                    text: "MFX" + mfxBtn.modelData
                                    font.bold: true
                                    font.pixelSize: ScaleMetrics.sp(10)
                                    color: root.mfxColor
                                }
                                Text {
                                    visible: mfxBtn.entered
                                    text: "← P" + root.activePart
                                    font.bold: true
                                    font.pixelSize: ScaleMetrics.sp(8)
                                    color: root.partColor
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                                Text {
                                    visible: mfxBtn.slot !== null && mfxBtn.slot.source > 0
                                    text: "FROM PART " + (mfxBtn.slot ? mfxBtn.slot.source : 0)
                                    font.pixelSize: ScaleMetrics.sp(7)
                                    color: Theme.textDim
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }
                            Text {
                                width: parent.width
                                text: mfxBtn.slot ? mfxBtn.slot.name : ""
                                elide: Text.ElideRight
                                font.pixelSize: ScaleMetrics.sp(8)
                                color: mfxBtn.active ? Theme.textPrimary : Theme.textSecondary
                            }
                        }
                        MouseArea {
                            id: mfxMouse
                            anchors.fill: parent
                            onClicked: {
                                Bridge.setEditingPerfMfx(mfxBtn.modelData);
                                root.close();
                            }
                        }
                    }
                }
                // Chain structure: where the part enters and what it passes through
                MfxChainDiagram {
                    visible: root.structure > 0
                    Layout.preferredWidth: ScaleMetrics.dp(130)
                    Layout.preferredHeight: ScaleMetrics.dp(52)
                    layout: root.structure > 0 ? Bridge.perfMfxStructures[root.structure] : null
                    entry: root.entryOf(root.parts[root.activePart - 1])
                    accent: root.mfxColor
                }
            }
        }
    }
}
