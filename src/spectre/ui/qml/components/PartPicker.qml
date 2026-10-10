pragma ValueTypeBehavior: Copy
import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

// Pick the parts a sequencer track sends to. MAIN sets the part the track
// plays (and closes); LAYERS toggles extra parts it also sends to.
// Fills its parent to catch taps outside the panel, which close it.
Item {
    id: root
    anchors.fill: parent
    visible: false
    z: 50

    property int trackIdx: 0
    property string mode: "main"  // "main" | "layers"

    readonly property var trackData: (Bridge.seqTracks && Bridge.seqTracks.length > trackIdx)
                                     ? Bridge.seqTracks[trackIdx] : null
    readonly property color trackColor: Theme.trackColors[trackIdx % Theme.trackColors.length]
    readonly property int mainPart: (trackData && trackData.targetPart) ? trackData.targetPart : (trackIdx + 1)
    readonly property var layers: (trackData && trackData.layerParts) ? trackData.layerParts : []

    // Open below anchorItem (above it if there's no room), kept inside the parent
    function open(idx, pickMode, anchorItem) {
        trackIdx = idx;
        mode = pickMode;
        const margin = ScaleMetrics.dp(8);
        const below = anchorItem.mapToItem(root, 0, anchorItem.height + ScaleMetrics.dp(4));
        panel.x = Math.max(margin, Math.min(below.x, root.width - panel.width - margin));
        const y = (below.y + panel.height <= root.height - margin)
                  ? below.y
                  : anchorItem.mapToItem(root, 0, 0).y - panel.height - ScaleMetrics.dp(4);
        panel.y = Math.max(margin, Math.min(y, root.height - panel.height - margin));
        visible = true;
    }

    function close() {
        visible = false;
    }

    MouseArea {
        anchors.fill: parent
        onClicked: root.close()
    }

    Rectangle {
        id: panel
        width: ScaleMetrics.dp(8 * 34 + 16)
        height: pickerCol.implicitHeight + ScaleMetrics.dp(16)
        radius: ScaleMetrics.dp(6)
        color: Theme.bgSurface
        border.color: root.trackColor
        border.width: 1

        MouseArea { anchors.fill: parent }  // swallow taps between buttons

        ColumnLayout {
            id: pickerCol
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(8)
            spacing: ScaleMetrics.dp(6)

            // Track name + MAIN / LAYERS switch
            RowLayout {
                Layout.fillWidth: true
                spacing: ScaleMetrics.dp(4)

                Text {
                    Layout.fillWidth: true
                    text: root.trackData ? root.trackData.name : ""
                    elide: Text.ElideRight
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(9)
                    color: root.trackColor
                }

                Repeater {
                    model: [ { key: "main", label: "MAIN" }, { key: "layers", label: "LAYERS" } ]
                    delegate: Rectangle {
                        readonly property bool active: root.mode === modelData.key
                        width: ScaleMetrics.dp(64)
                        height: ScaleMetrics.dp(26)
                        radius: 3
                        color: active ? root.trackColor : Theme.bgApp
                        border.color: active ? root.trackColor : Theme.borderCard
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: modelData.label
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: parent.active ? Theme.bgApp : Theme.textSecondary
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: root.mode = modelData.key
                        }
                    }
                }
            }

            Text {
                text: root.mode === "main" ? "PLAYS ON"
                                           : "ALSO SEND TO (main: P" + root.mainPart + ")"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(8)
                font.letterSpacing: 1.0
                color: Theme.textDim
            }

            GridLayout {
                columns: 8
                rowSpacing: ScaleMetrics.dp(4)
                columnSpacing: ScaleMetrics.dp(4)
                Repeater {
                    model: 16
                    delegate: Rectangle {
                        readonly property int part: index + 1
                        readonly property bool isMain: part === root.mainPart
                        readonly property bool isLayer: root.layers.indexOf(part) >= 0
                        // In LAYERS mode the main part is shown but can't be toggled
                        readonly property bool locked: root.mode === "layers" && isMain
                        width: ScaleMetrics.dp(30)
                        height: ScaleMetrics.dp(30)
                        radius: 3
                        color: isMain ? root.trackColor : (isLayer ? Theme.bgCardActive : Theme.bgApp)
                        border.color: isMain || isLayer ? root.trackColor : Theme.borderCard
                        border.width: isLayer ? 2 : 1
                        opacity: locked ? 0.6 : 1.0
                        Text {
                            anchors.centerIn: parent
                            text: "P" + parent.part
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: parent.isMain ? Theme.bgApp : (parent.isLayer ? root.trackColor : Theme.textSecondary)
                        }
                        MouseArea {
                            anchors.fill: parent
                            enabled: !parent.locked
                            onClicked: {
                                if (root.mode === "main") {
                                    Bridge.seqSetTrackTargetPart(root.trackIdx, parent.part);
                                    root.close();
                                } else {
                                    Bridge.seqToggleTrackLayer(root.trackIdx, parent.part);
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
