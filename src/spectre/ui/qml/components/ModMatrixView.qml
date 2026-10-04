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

    property var sources: [
        "CC01 MOD WHEEL", "CC02 BREATH", "CC04 FOOT", "CC11 EXPRESSION",
        "PITCH BEND", "AFTERTOUCH", "VELOCITY", "KEYFOLLOW", "LFO 1", "LFO 2", "STEP LFO"
    ]
    property var destinations: [
        "OFF", "PITCH", "TVF CUTOFF", "TVF RESO", "TVA LEVEL", "PAN",
        "LFO1 RATE", "LFO1 P-DEP", "LFO1 F-DEP", "LFO2 RATE", "LFO2 P-DEP"
    ]

    property bool pickerVisible: false
    property string pickerTitle: ""
    property string pickerSubtitle: ""
    property color pickerAccent: Theme.tone1
    property var pickerItems: []
    property int pickerCurrentIdx: 0
    property var pickerCallback: null

    function openPicker(title, subtitle, accent, items, currentIndex, callback) {
        pickerTitle = title;
        pickerSubtitle = subtitle;
        pickerAccent = accent;
        pickerItems = items;
        pickerCurrentIdx = currentIndex;
        pickerCallback = callback;
        pickerVisible = true;
    }

    function getCtrlData(idx) {
        if (idx === 1) return Bridge.matrixCtrl1;
        if (idx === 2) return Bridge.matrixCtrl2;
        if (idx === 3) return Bridge.matrixCtrl3;
        if (idx === 4) return Bridge.matrixCtrl4;
        return null;
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: ScaleMetrics.dp(10)
        spacing: ScaleMetrics.dp(8)

        // Header
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(8)

            Rectangle {
                width: ScaleMetrics.dp(8); height: ScaleMetrics.dp(8); radius: 4
                color: Theme.tone1
            }
            Text {
                text: "MODULATION MATRIX (4 MATRIX CONTROLLERS)"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(12)
                font.letterSpacing: 1.2
                color: Theme.textPrimary
            }
            Item { Layout.fillWidth: true }
            Text {
                text: "ROLAND PATCH MATRIX ROUTING"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(9)
                color: Theme.textDim
            }
        }

        // 4 Matrix Controller Columns
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: ScaleMetrics.dp(8)

            Repeater {
                model: [
                    { id: 1, name: "MATRIX CTRL 1", defaultSrc: 0, accent: Theme.tone1 },
                    { id: 2, name: "MATRIX CTRL 2", defaultSrc: 4, accent: Theme.tone2 },
                    { id: 3, name: "MATRIX CTRL 3", defaultSrc: 6, accent: Theme.tone3 },
                    { id: 4, name: "MATRIX CTRL 4", defaultSrc: 8, accent: Theme.tone4 }
                ]

                delegate: Rectangle {
                    id: ctrlCol
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: ScaleMetrics.dp(6)
                    color: Theme.bgApp
                    border.color: Theme.borderCard
                    border.width: 1

                    property color accentColor: modelData.accent
                    property var ctrlData: root.getCtrlData(modelData.id)
                    property int srcIdx: ctrlData && ctrlData.source !== undefined ? ctrlData.source : modelData.defaultSrc
                    property var destIndices: ctrlData ? [ctrlData.dest1, ctrlData.dest2, ctrlData.dest3, ctrlData.dest4] : [1, 2, 0, 0]
                    property var sensValues: ctrlData ? [ctrlData.sens1, ctrlData.sens2, ctrlData.sens3, ctrlData.sens4] : [30, -25, 0, 0]

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: ScaleMetrics.dp(8)
                        spacing: ScaleMetrics.dp(6)

                        // Ctrl Header
                        RowLayout {
                            Layout.fillWidth: true
                            Rectangle {
                                width: ScaleMetrics.dp(6); height: ScaleMetrics.dp(6); radius: 3
                                color: ctrlCol.accentColor
                            }
                            Text {
                                text: modelData.name
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(10)
                                color: ctrlCol.accentColor
                            }
                        }

                        // Source Selector Box (Interactive Overlay Trigger)
                        Rectangle {
                            id: srcBox
                            Layout.fillWidth: true
                            height: ScaleMetrics.dp(36)
                            radius: ScaleMetrics.dp(4)
                            color: srcMouse.pressed ? Qt.rgba(ctrlCol.accentColor.r, ctrlCol.accentColor.g, ctrlCol.accentColor.b, 0.15) : "#10141d"
                            border.color: ctrlCol.accentColor
                            border.width: 1

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: ScaleMetrics.dp(4)
                                anchors.leftMargin: ScaleMetrics.dp(6)
                                anchors.rightMargin: ScaleMetrics.dp(6)
                                spacing: ScaleMetrics.dp(4)

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 1
                                    Text {
                                        text: "SOURCE"
                                        font.bold: true
                                        font.pixelSize: ScaleMetrics.sp(7)
                                        color: Theme.textDim
                                    }
                                    Text {
                                        text: root.sources[ctrlCol.srcIdx]
                                        font.bold: true
                                        font.pixelSize: ScaleMetrics.sp(9)
                                        color: Theme.textPrimary
                                        elide: Text.ElideRight
                                    }
                                }

                                Text {
                                    text: "▾"
                                    font.pixelSize: ScaleMetrics.sp(10)
                                    color: ctrlCol.accentColor
                                }
                            }

                            MouseArea {
                                id: srcMouse
                                anchors.fill: parent
                                onClicked: {
                                    root.openPicker(
                                        "SELECT SOURCE",
                                        modelData.name,
                                        ctrlCol.accentColor,
                                        root.sources,
                                        ctrlCol.srcIdx,
                                        function(newIdx) {
                                            ctrlCol.srcIdx = newIdx;
                                            Bridge.setMatrixCtrlParam(modelData.id, "source", newIdx);
                                        }
                                    );
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 1
                            color: Theme.borderCard
                        }

                        // 4 Destinations
                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            spacing: ScaleMetrics.dp(4)

                            Repeater {
                                model: 4
                                delegate: Rectangle {
                                    id: slotBox
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    radius: ScaleMetrics.dp(4)
                                    color: "#0a0d14"
                                    border.color: Theme.borderCard
                                    border.width: 1

                                    property int slotIdx: index
                                    property int dIdx: ctrlCol.destIndices[slotIdx]
                                    property int sens: ctrlCol.sensValues[slotIdx]

                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: ScaleMetrics.dp(4)
                                        spacing: ScaleMetrics.dp(3)

                                        // Destination Selector Box (Styled like Source with lighter accent border)
                                        Rectangle {
                                            id: destSelector
                                            Layout.fillWidth: true
                                            height: ScaleMetrics.dp(30)
                                            radius: ScaleMetrics.dp(4)
                                            color: destMouse.pressed ? Qt.rgba(ctrlCol.accentColor.r, ctrlCol.accentColor.g, ctrlCol.accentColor.b, 0.15) : "#10141d"
                                            border.color: destMouse.pressed ? ctrlCol.accentColor :
                                                          (slotBox.dIdx === 0 ? Theme.borderCard : Qt.rgba(ctrlCol.accentColor.r, ctrlCol.accentColor.g, ctrlCol.accentColor.b, 0.45))
                                            border.width: 1

                                            RowLayout {
                                                anchors.fill: parent
                                                anchors.leftMargin: ScaleMetrics.dp(6)
                                                anchors.rightMargin: ScaleMetrics.dp(6)
                                                spacing: ScaleMetrics.dp(4)

                                                ColumnLayout {
                                                    Layout.fillWidth: true
                                                    spacing: 1

                                                    Text {
                                                        text: "DEST " + (slotBox.slotIdx + 1)
                                                        font.bold: true
                                                        font.pixelSize: ScaleMetrics.sp(6.5)
                                                        color: Theme.textDim
                                                    }

                                                    Text {
                                                        text: root.destinations[slotBox.dIdx]
                                                        font.bold: true
                                                        font.pixelSize: ScaleMetrics.sp(8.5)
                                                        color: slotBox.dIdx === 0 ? Theme.textDim : ctrlCol.accentColor
                                                        elide: Text.ElideRight
                                                    }
                                                }

                                                Text {
                                                    text: "▾"
                                                    font.pixelSize: ScaleMetrics.sp(9)
                                                    color: slotBox.dIdx === 0 ? Theme.textDim : ctrlCol.accentColor
                                                }
                                            }

                                            MouseArea {
                                                id: destMouse
                                                anchors.fill: parent
                                                onClicked: {
                                                    root.openPicker(
                                                        "SELECT DESTINATION",
                                                        modelData.name + " • DEST " + (slotBox.slotIdx + 1),
                                                        ctrlCol.accentColor,
                                                        root.destinations,
                                                        slotBox.dIdx,
                                                        function(newIdx) {
                                                            var arr = ctrlCol.destIndices.slice();
                                                            arr[slotBox.slotIdx] = newIdx;
                                                            ctrlCol.destIndices = arr;
                                                            Bridge.setMatrixCtrlParam(modelData.id, "dest" + (slotBox.slotIdx + 1), newIdx);
                                                        }
                                                    );
                                                }
                                            }
                                        }

                                        // Bipolar Sensitivity Slider (-63..+63)
                                        Rectangle {
                                            Layout.fillWidth: true
                                            height: ScaleMetrics.dp(20)
                                            radius: 3
                                            color: "#10141d"
                                            border.color: Theme.borderCard
                                            border.width: 1
                                            opacity: slotBox.dIdx === 0 ? 0.35 : 1.0

                                            // Center line
                                            Rectangle {
                                                anchors.horizontalCenter: parent.horizontalCenter
                                                width: 1; height: parent.height
                                                color: Theme.borderCard
                                            }

                                            // Fill
                                            Rectangle {
                                                property real norm: (slotBox.sens + 63) / 126.0
                                                x: norm >= 0.5 ? parent.width * 0.5 : parent.width * norm
                                                width: Math.abs(parent.width * (norm - 0.5))
                                                height: parent.height
                                                color: Qt.rgba(ctrlCol.accentColor.r, ctrlCol.accentColor.g, ctrlCol.accentColor.b, 0.45)
                                            }

                                            Text {
                                                anchors.centerIn: parent
                                                text: "SENS: " + (slotBox.sens > 0 ? "+" + slotBox.sens : slotBox.sens.toString())
                                                font.family: Theme.fontMono
                                                font.bold: true
                                                font.pixelSize: ScaleMetrics.sp(7)
                                                color: Theme.textPrimary
                                            }

                                            MouseArea {
                                                anchors.fill: parent
                                                enabled: slotBox.dIdx !== 0
                                                onPositionChanged: (mouse) => {
                                                    if (pressed) {
                                                        var val = Math.round((mouse.x / width) * 126 - 63);
                                                        var clamped = Math.max(-63, Math.min(63, val));
                                                        var arr = ctrlCol.sensValues.slice();
                                                        arr[slotBox.slotIdx] = clamped;
                                                        ctrlCol.sensValues = arr;
                                                        Bridge.setMatrixCtrlParam(modelData.id, "sens" + (slotBox.slotIdx + 1), clamped);
                                                    }
                                                }
                                                onPressed: (mouse) => {
                                                    var val = Math.round((mouse.x / width) * 126 - 63);
                                                    var clamped = Math.max(-63, Math.min(63, val));
                                                    var arr = ctrlCol.sensValues.slice();
                                                    arr[slotBox.slotIdx] = clamped;
                                                    ctrlCol.sensValues = arr;
                                                    Bridge.setMatrixCtrlParam(modelData.id, "sens" + (slotBox.slotIdx + 1), clamped);
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // =========================================================================
    // MODAL PICKER OVERLAY (For Sources and Destinations)
    // =========================================================================
    Rectangle {
        id: pickerOverlay
        anchors.fill: parent
        color: Qt.rgba(0.02, 0.03, 0.05, 0.82)
        visible: opacity > 0
        opacity: root.pickerVisible ? 1.0 : 0.0
        z: 999

        Behavior on opacity {
            NumberAnimation { duration: 150 }
        }

        // Dismiss when tapping the backdrop outside card
        MouseArea {
            anchors.fill: parent
            enabled: root.pickerVisible
            onClicked: (mouse) => {
                var pos = pickerCard.mapToItem(pickerOverlay, 0, 0);
                if (mouse.x < pos.x || mouse.x > pos.x + pickerCard.width ||
                    mouse.y < pos.y || mouse.y > pos.y + pickerCard.height) {
                    root.pickerVisible = false;
                }
            }
        }

        Rectangle {
            id: pickerCard
            anchors.centerIn: parent
            width: ScaleMetrics.dp(480)
            height: ScaleMetrics.dp(290)
            radius: ScaleMetrics.dp(8)
            color: "#0e131d"
            border.color: root.pickerAccent
            border.width: 1.5
            scale: root.pickerVisible ? 1.0 : 0.95

            Behavior on scale {
                NumberAnimation { duration: 150; easing.type: Easing.OutQuad }
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(12)
                spacing: ScaleMetrics.dp(8)

                // Header
                RowLayout {
                    Layout.fillWidth: true
                    spacing: ScaleMetrics.dp(8)

                    Rectangle {
                        width: ScaleMetrics.dp(8); height: ScaleMetrics.dp(8); radius: 4
                        color: root.pickerAccent
                    }

                    ColumnLayout {
                        spacing: 1
                        Text {
                            text: root.pickerTitle
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(11)
                            font.letterSpacing: 1.1
                            color: Theme.textPrimary
                        }
                        Text {
                            text: root.pickerSubtitle
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8.5)
                            color: root.pickerAccent
                        }
                    }

                    Item { Layout.fillWidth: true }

                    // Close Button
                    Rectangle {
                        width: ScaleMetrics.dp(26)
                        height: ScaleMetrics.dp(26)
                        radius: ScaleMetrics.dp(13)
                        color: closeMouse.pressed ? "#ef4444" : "#192231"
                        border.color: Theme.borderCard
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: "✕"
                            font.pixelSize: ScaleMetrics.sp(10)
                            color: closeMouse.pressed ? "#ffffff" : Theme.textSecondary
                        }

                        MouseArea {
                            id: closeMouse
                            anchors.fill: parent
                            onClicked: root.pickerVisible = false
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.borderCard
                }

                // Grid of items (3 columns)
                GridLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    columns: 3
                    rowSpacing: ScaleMetrics.dp(6)
                    columnSpacing: ScaleMetrics.dp(6)

                    Repeater {
                        model: root.pickerItems
                        delegate: Rectangle {
                            id: itemBtn
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.preferredHeight: ScaleMetrics.dp(44)
                            radius: ScaleMetrics.dp(4)
                            color: (root.pickerCurrentIdx === index) ?
                                   Qt.rgba(root.pickerAccent.r, root.pickerAccent.g, root.pickerAccent.b, 0.28) :
                                   (itemMouse.pressed ? Qt.rgba(root.pickerAccent.r, root.pickerAccent.g, root.pickerAccent.b, 0.15) : "#141a26")
                            border.color: (root.pickerCurrentIdx === index) ?
                                          root.pickerAccent :
                                          (itemMouse.pressed ? root.pickerAccent : Theme.borderCard)
                            border.width: (root.pickerCurrentIdx === index) ? 1.5 : 1

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: ScaleMetrics.dp(6)
                                spacing: ScaleMetrics.dp(6)

                                // Active selection radio indicator dot
                                Rectangle {
                                    width: ScaleMetrics.dp(6); height: ScaleMetrics.dp(6); radius: 3
                                    color: (root.pickerCurrentIdx === index) ? root.pickerAccent : "transparent"
                                    border.color: (root.pickerCurrentIdx === index) ? root.pickerAccent : Theme.borderCard
                                    border.width: 1
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: modelData
                                    font.bold: root.pickerCurrentIdx === index
                                    font.pixelSize: ScaleMetrics.sp(8.5)
                                    color: (root.pickerCurrentIdx === index) ? Theme.textPrimary :
                                           (modelData === "OFF" ? Theme.textDim : Theme.textSecondary)
                                    elide: Text.ElideRight
                                }
                            }

                            MouseArea {
                                id: itemMouse
                                anchors.fill: parent
                                onClicked: {
                                    if (root.pickerCallback) {
                                        root.pickerCallback(index);
                                    }
                                    root.pickerVisible = false;
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
