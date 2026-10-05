import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import JunoSpectre
import ".."

Rectangle {
    id: root
    color: Theme.bgCard
    radius: ScaleMetrics.dp(8)
    border.color: Theme.borderCard
    border.width: 1

    // Curated Roland Matrix Sources with official hardware IDs
    property var sourceList: [
        { id: 0,   name: "OFF" },
        { id: 1,   name: "CC01 MOD WHEEL" },
        { id: 2,   name: "CC02 BREATH" },
        { id: 4,   name: "CC04 FOOT" },
        { id: 11,  name: "CC11 EXPRESSION" },
        { id: 96,  name: "PITCH BEND" },
        { id: 97,  name: "AFTERTOUCH" },
        { id: 98,  name: "SYS CTRL 1" },
        { id: 99,  name: "SYS CTRL 2" },
        { id: 100, name: "SYS CTRL 3" },
        { id: 101, name: "SYS CTRL 4" },
        { id: 102, name: "VELOCITY" },
        { id: 103, name: "KEYFOLLOW" },
        { id: 104, name: "TEMPO" },
        { id: 105, name: "LFO 1" },
        { id: 106, name: "LFO 2" },
        { id: 107, name: "PITCH ENV" },
        { id: 108, name: "TVF ENV" },
        { id: 109, name: "TVA ENV" }
    ]

    // Complete Roland Matrix Destinations with official hardware IDs
    property var destList: [
        { id: 0,  name: "OFF" },
        { id: 1,  name: "PITCH" },
        { id: 2,  name: "TVF CUTOFF" },
        { id: 3,  name: "TVF RESO" },
        { id: 4,  name: "TVA LEVEL" },
        { id: 5,  name: "PAN" },
        { id: 6,  name: "DRY LEVEL" },
        { id: 7,  name: "CHORUS SEND" },
        { id: 8,  name: "REVERB SEND" },
        { id: 9,  name: "LFO1 PIT-DEP" },
        { id: 10, name: "LFO2 PIT-DEP" },
        { id: 11, name: "LFO1 TVF-DEP" },
        { id: 12, name: "LFO2 TVF-DEP" },
        { id: 13, name: "LFO1 TVA-DEP" },
        { id: 14, name: "LFO2 TVA-DEP" },
        { id: 15, name: "LFO1 PAN-DEP" },
        { id: 16, name: "LFO2 PAN-DEP" },
        { id: 17, name: "LFO1 RATE" },
        { id: 18, name: "LFO2 RATE" },
        { id: 19, name: "PIT ATK" },
        { id: 20, name: "PIT DCY" },
        { id: 21, name: "PIT REL" },
        { id: 22, name: "TVF ATK" },
        { id: 23, name: "TVF DCY" },
        { id: 24, name: "TVF REL" },
        { id: 25, name: "TVA ATK" },
        { id: 26, name: "TVA DCY" },
        { id: 27, name: "TVA REL" },
        { id: 28, name: "TMT" },
        { id: 29, name: "FXM DEPTH" },
        { id: 30, name: "MFX CTRL 1" },
        { id: 31, name: "MFX CTRL 2" },
        { id: 32, name: "MFX CTRL 3" },
        { id: 33, name: "MFX CTRL 4" }
    ]

    // String arrays for backwards compatibility with tests and properties
    property var sources: sourceList.map(function(item) { return item.name; })
    property var destinations: destList.map(function(item) { return item.name; })

    function getSourceName(id) {
        for (var i = 0; i < sourceList.length; i++) {
            if (sourceList[i].id === id) return sourceList[i].name;
        }
        if (id >= 1 && id <= 95) return "CC " + id;
        return id === 0 ? "OFF" : "SRC " + id;
    }

    function getDestName(id) {
        for (var i = 0; i < destList.length; i++) {
            if (destList[i].id === id) return destList[i].name;
        }
        return id === 0 ? "OFF" : "DEST " + id;
    }

    property bool pickerVisible: false
    property string pickerTitle: ""
    property string pickerSubtitle: ""
    property color pickerAccent: "#c084fc"
    property var pickerItems: []
    property int pickerCurrentId: 0
    property var pickerCallback: null

    function openPicker(title, subtitle, accent, items, currentId, callback) {
        pickerTitle = title;
        pickerSubtitle = subtitle;
        pickerAccent = accent;
        pickerItems = items;
        pickerCurrentId = currentId;
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
                color: "#c084fc"
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

        // 4 Matrix Controller Columns (Purple / Violet Gradient Palette)
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: ScaleMetrics.dp(8)

            Repeater {
                model: [
                    { id: 1, name: "MATRIX CTRL 1", defaultSrc: 1,   accent: "#d8b4fe", defaultDest1: 1 },
                    { id: 2, name: "MATRIX CTRL 2", defaultSrc: 96,  accent: "#c084fc", defaultDest1: 2 },
                    { id: 3, name: "MATRIX CTRL 3", defaultSrc: 102, accent: "#a855f7", defaultDest1: 4 },
                    { id: 4, name: "MATRIX CTRL 4", defaultSrc: 105, accent: "#7c3aed", defaultDest1: 2 }
                ]

                delegate: Rectangle {
                    id: ctrlCol
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: ScaleMetrics.dp(6)
                    color: Theme.bgApp
                    border.color: Theme.borderCard
                    border.width: 1

                    property int ctrlId: modelData.id
                    property color accentColor: modelData.accent
                    property var ctrlData: root.getCtrlData(modelData.id)
                    property int srcId: ctrlData && ctrlData.source !== undefined ? ctrlData.source : modelData.defaultSrc
                    property var destIndices: ctrlData ? [ctrlData.dest1, ctrlData.dest2, ctrlData.dest3, ctrlData.dest4] : [modelData.defaultDest1, 0, 0, 0]
                    property var sensValues: ctrlData ? [ctrlData.sens1, ctrlData.sens2, ctrlData.sens3, ctrlData.sens4] : [30, 0, 0, 0]

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
                                        text: root.getSourceName(ctrlCol.srcId)
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
                                        root.sourceList,
                                        ctrlCol.srcId,
                                        function(newId) {
                                            Bridge.setMatrixCtrlParam(ctrlCol.ctrlId, "source", newId);
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
                                    property int dId: ctrlCol.destIndices[slotIdx]
                                    property int sens: ctrlCol.sensValues[slotIdx]
                                    property var swStates: (ctrlCol.ctrlData && ctrlCol.ctrlData.dest_sw) ? ctrlCol.ctrlData.dest_sw[slotIdx] : [1, 1, 1, 1]

                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: ScaleMetrics.dp(4)
                                        spacing: ScaleMetrics.dp(3)

                                        // Destination Selector Box
                                        Rectangle {
                                            id: destSelector
                                            Layout.fillWidth: true
                                            height: ScaleMetrics.dp(28)
                                            radius: ScaleMetrics.dp(4)
                                            color: destMouse.pressed ? Qt.rgba(ctrlCol.accentColor.r, ctrlCol.accentColor.g, ctrlCol.accentColor.b, 0.15) : "#10141d"
                                            border.color: destMouse.pressed ? ctrlCol.accentColor :
                                                          (slotBox.dId === 0 ? Theme.borderCard : Qt.rgba(ctrlCol.accentColor.r, ctrlCol.accentColor.g, ctrlCol.accentColor.b, 0.45))
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
                                                        text: root.getDestName(slotBox.dId)
                                                        font.bold: true
                                                        font.pixelSize: ScaleMetrics.sp(8.5)
                                                        color: slotBox.dId === 0 ? Theme.textDim : ctrlCol.accentColor
                                                        elide: Text.ElideRight
                                                    }
                                                }

                                                Text {
                                                    text: "▾"
                                                    font.pixelSize: ScaleMetrics.sp(9)
                                                    color: slotBox.dId === 0 ? Theme.textDim : ctrlCol.accentColor
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
                                                        root.destList,
                                                        slotBox.dId,
                                                        function(newId) {
                                                            Bridge.setMatrixCtrlParam(ctrlCol.ctrlId, "dest" + (slotBox.slotIdx + 1), newId);
                                                        }
                                                    );
                                                }
                                            }
                                        }

                                        // Bipolar Sensitivity Slider (-63..+63)
                                        Rectangle {
                                            Layout.fillWidth: true
                                            height: ScaleMetrics.dp(18)
                                            radius: 3
                                            color: "#10141d"
                                            border.color: Theme.borderCard
                                            border.width: 1
                                            opacity: slotBox.dId === 0 ? 0.35 : 1.0

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
                                                enabled: slotBox.dId !== 0
                                                onPositionChanged: (mouse) => {
                                                    if (pressed) {
                                                        var val = Math.round((mouse.x / width) * 126 - 63);
                                                        var clamped = Math.max(-63, Math.min(63, val));
                                                        Bridge.setMatrixCtrlParam(ctrlCol.ctrlId, "sens" + (slotBox.slotIdx + 1), clamped);
                                                    }
                                                }
                                                onPressed: (mouse) => {
                                                    var val = Math.round((mouse.x / width) * 126 - 63);
                                                    var clamped = Math.max(-63, Math.min(63, val));
                                                    Bridge.setMatrixCtrlParam(ctrlCol.ctrlId, "sens" + (slotBox.slotIdx + 1), clamped);
                                                }
                                            }
                                        }

                                        // Tone Control Switches: [T1] [T2] [T3] [T4]
                                        RowLayout {
                                            Layout.fillWidth: true
                                            height: ScaleMetrics.dp(18)
                                            spacing: ScaleMetrics.dp(3)
                                            opacity: slotBox.dId === 0 ? 0.35 : 1.0

                                            Repeater {
                                                model: [
                                                    { tone: 1, name: "T1", color: Theme.tone1 },
                                                    { tone: 2, name: "T2", color: Theme.tone2 },
                                                    { tone: 3, name: "T3", color: Theme.tone3 },
                                                    { tone: 4, name: "T4", color: Theme.tone4 }
                                                ]

                                                delegate: Rectangle {
                                                    id: tonePill
                                                    Layout.fillWidth: true
                                                    Layout.fillHeight: true
                                                    radius: ScaleMetrics.dp(3)

                                                    property bool isOn: slotBox.swStates ? (slotBox.swStates[modelData.tone - 1] === 1) : true
                                                    property color tColor: modelData.color

                                                    color: isOn ? Qt.rgba(tColor.r, tColor.g, tColor.b, 0.22) : "#10141d"
                                                    border.color: isOn ? tColor : Theme.borderCard
                                                    border.width: isOn ? 1.5 : 1

                                                    Text {
                                                        anchors.centerIn: parent
                                                        text: modelData.name
                                                        font.family: Theme.fontMono
                                                        font.bold: true
                                                        font.pixelSize: ScaleMetrics.sp(7.5)
                                                        color: tonePill.isOn ? tonePill.tColor : Theme.textDim
                                                    }

                                                    MouseArea {
                                                        anchors.fill: parent
                                                        enabled: slotBox.dId !== 0
                                                        onClicked: {
                                                            var nextVal = !tonePill.isOn;
                                                            Bridge.setToneMatrixSwitch(modelData.tone, ctrlCol.ctrlId, slotBox.slotIdx + 1, nextVal);
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
        }
    }

    // =========================================================================
    // MODAL PICKER OVERLAY (Scrollable Grid for Sources and Destinations)
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
            width: ScaleMetrics.dp(520)
            height: Math.min(parent.height - ScaleMetrics.dp(24), ScaleMetrics.dp(350))
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

                // Scrollable Grid of Items (3 columns)
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true

                    Flickable {
                        id: pickerFlick
                        anchors.fill: parent
                        contentWidth: width
                        contentHeight: pickerGrid.implicitHeight + ScaleMetrics.dp(8)
                        boundsBehavior: Flickable.StopAtBounds

                        ScrollBar.vertical: ScrollBar {
                            anchors.right: parent.right
                            policy: ScrollBar.AsNeeded
                        }

                        GridLayout {
                            id: pickerGrid
                            width: parent.width - ScaleMetrics.dp(10)
                            columns: 3
                            rowSpacing: ScaleMetrics.dp(6)
                            columnSpacing: ScaleMetrics.dp(6)

                            Repeater {
                                model: root.pickerItems
                                delegate: Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: ScaleMetrics.dp(38)
                                    radius: ScaleMetrics.dp(4)

                                    property bool isSelected: modelData.id === root.pickerCurrentId

                                    color: isSelected ?
                                           Qt.rgba(root.pickerAccent.r, root.pickerAccent.g, root.pickerAccent.b, 0.28) :
                                           (itemMouse.pressed ? Qt.rgba(root.pickerAccent.r, root.pickerAccent.g, root.pickerAccent.b, 0.15) : "#141a26")
                                    border.color: isSelected ?
                                                  root.pickerAccent :
                                                  (itemMouse.pressed ? root.pickerAccent : Theme.borderCard)
                                    border.width: isSelected ? 1.5 : 1

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.margins: ScaleMetrics.dp(6)
                                        spacing: ScaleMetrics.dp(6)

                                        // Active selection radio indicator dot
                                        Rectangle {
                                            width: ScaleMetrics.dp(6); height: ScaleMetrics.dp(6); radius: 3
                                            color: isSelected ? root.pickerAccent : "transparent"
                                            border.color: isSelected ? root.pickerAccent : Theme.borderCard
                                            border.width: 1
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: modelData.name
                                            font.bold: isSelected
                                            font.pixelSize: ScaleMetrics.sp(8.5)
                                            color: isSelected ? Theme.textPrimary :
                                                   (modelData.id === 0 ? Theme.textDim : Theme.textSecondary)
                                            elide: Text.ElideRight
                                        }
                                    }

                                    MouseArea {
                                        id: itemMouse
                                        anchors.fill: parent
                                        onClicked: {
                                            if (root.pickerCallback) {
                                                root.pickerCallback(modelData.id);
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
    }
}
