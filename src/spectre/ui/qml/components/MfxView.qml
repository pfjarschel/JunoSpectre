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

    property int activeAlgoId: Bridge.mfxAlgoId
    property bool isBypassed: Bridge.mfxBypassed
    property string selectedCategory: "ALL"
    property string searchQuery: ""
    property bool virtualKeyboardVisible: false

    Connections {
        target: Bridge
        function onMfxParamsChanged() {
            root.activeAlgoId = Bridge.mfxAlgoId;
            root.isBypassed = Bridge.mfxBypassed;
        }
    }

    property var categories: Bridge.mfxCategories && Bridge.mfxCategories.length > 0 ?
        Bridge.mfxCategories :
        ["ALL", "FILTER/EQ", "MOD", "CHORUS", "DRIVE", "DYNAMICS", "DELAY", "LO-FI", "PITCH", "REVERB", "COMBINATION", "SPECIAL"]

    property var algoList: Bridge.mfxCatalog ? Bridge.mfxCatalog : []

    // Full info (with params) for the active algorithm only; fetched on demand from Python.
    property var currentAlgo: Bridge.getMfxAlgoInfo(root.activeAlgoId)
    onActiveAlgoIdChanged: currentAlgo = Bridge.getMfxAlgoInfo(root.activeAlgoId)

    function getFilteredAlgos() {
        return Bridge.filterMfxAlgos(root.selectedCategory, root.searchQuery);
    }

    property var filteredAlgos: getFilteredAlgos()
    onSearchQueryChanged: filteredAlgos = getFilteredAlgos()
    onSelectedCategoryChanged: filteredAlgos = getFilteredAlgos()

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: ScaleMetrics.dp(10)
        anchors.rightMargin: ScaleMetrics.dp(10)
        anchors.topMargin: ScaleMetrics.dp(10)
        anchors.bottomMargin: root.virtualKeyboardVisible ? ScaleMetrics.dp(170) : ScaleMetrics.dp(10)
        spacing: ScaleMetrics.dp(10)

        // Column 1: Algorithm Browser List (~310dp)
        Rectangle {
            Layout.preferredWidth: ScaleMetrics.dp(310)
            Layout.fillHeight: true
            radius: ScaleMetrics.dp(6)
            color: Theme.bgApp
            border.color: Theme.borderCard
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(8)
                spacing: ScaleMetrics.dp(6)

                // Header & Count Badge
                RowLayout {
                    Layout.fillWidth: true
                    spacing: ScaleMetrics.dp(6)

                    Rectangle {
                        width: ScaleMetrics.dp(8); height: ScaleMetrics.dp(8); radius: 4
                        color: "#ec4899"
                    }
                    Text {
                        text: "MFX ALGORITHMS"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(10)
                        font.letterSpacing: 1.1
                        color: Theme.textPrimary
                    }
                    Item { Layout.fillWidth: true }
                    Text {
                        text: root.filteredAlgos.length + " / " + root.algoList.length
                        font.family: Theme.fontMono
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: "#ec4899"
                    }
                }

                // Search Input Box
                Rectangle {
                    Layout.fillWidth: true
                    height: ScaleMetrics.dp(28)
                    radius: ScaleMetrics.dp(4)
                    color: "#0a0d14"
                    border.color: mfxSearchField.activeFocus || root.virtualKeyboardVisible ? "#ec4899" : Theme.borderCard
                    border.width: 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: ScaleMetrics.dp(8)
                        anchors.rightMargin: ScaleMetrics.dp(6)
                        spacing: ScaleMetrics.dp(6)

                        Text {
                            text: "🔍"
                            font.pixelSize: ScaleMetrics.sp(9)
                            color: Theme.textDim
                        }

                        TextInput {
                            id: mfxSearchField
                            Layout.fillWidth: true
                            font.pixelSize: ScaleMetrics.sp(10)
                            font.family: Theme.fontSans
                            color: Theme.textPrimary
                            clip: true

                            Text {
                                text: "Search (e.g. Echo, Phaser, 15)..."
                                font.pixelSize: ScaleMetrics.sp(9)
                                color: Theme.textDim
                                visible: !mfxSearchField.text && !mfxSearchField.activeFocus
                            }

                            onTextChanged: {
                                root.searchQuery = text;
                            }

                            onActiveFocusChanged: {
                                if (activeFocus) {
                                    root.virtualKeyboardVisible = true;
                                }
                            }
                        }

                        // Toggle Keyboard Button
                        Rectangle {
                            width: ScaleMetrics.dp(22)
                            height: ScaleMetrics.dp(20)
                            radius: 3
                            color: root.virtualKeyboardVisible ? "#ec4899" : "#1a2233"

                            Text {
                                anchors.centerIn: parent
                                text: "⌨"
                                font.pixelSize: ScaleMetrics.sp(10)
                                color: root.virtualKeyboardVisible ? "#ffffff" : Theme.textSecondary
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    root.virtualKeyboardVisible = !root.virtualKeyboardVisible;
                                    if (root.virtualKeyboardVisible) {
                                        mfxSearchField.forceActiveFocus();
                                    }
                                }
                            }
                        }

                        // Clear Button
                        Text {
                            visible: mfxSearchField.text.length > 0
                            text: "✕"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(11)
                            color: Theme.textDim
                            MouseArea {
                                anchors.fill: parent
                                anchors.margins: -4
                                onClicked: {
                                    mfxSearchField.text = "";
                                    root.searchQuery = "";
                                }
                            }
                        }
                    }

                    // Tapping anywhere in the search input box triggers focus and opens keyboard
                    MouseArea {
                        anchors.fill: parent
                        anchors.rightMargin: ScaleMetrics.dp(50) // Leave room for ⌨ and ✕ buttons
                        onClicked: {
                            mfxSearchField.forceActiveFocus();
                            root.virtualKeyboardVisible = true;
                        }
                    }
                }

                // Category Chips (Horizontal Flickable)
                Flickable {
                    Layout.fillWidth: true
                    height: ScaleMetrics.dp(26)
                    contentWidth: catRow.implicitWidth
                    contentHeight: height
                    flickableDirection: Flickable.HorizontalFlick
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds

                    RowLayout {
                        id: catRow
                        height: parent.height
                        spacing: ScaleMetrics.dp(4)

                        Repeater {
                            model: root.categories
                            delegate: Rectangle {
                                id: catChip
                                property bool isSel: root.selectedCategory === modelData
                                height: ScaleMetrics.dp(22)
                                width: catText.implicitWidth + ScaleMetrics.dp(14)
                                radius: ScaleMetrics.dp(11)
                                color: isSel ? "#ec4899" : (chipMouse.pressed ? "#1e293b" : "#10141d")
                                border.color: isSel ? "#f472b6" : Theme.borderCard
                                border.width: 1

                                Text {
                                    id: catText
                                    anchors.centerIn: parent
                                    text: modelData
                                    font.bold: catChip.isSel
                                    font.pixelSize: ScaleMetrics.sp(8)
                                    color: catChip.isSel ? "#ffffff" : Theme.textSecondary
                                }

                                MouseArea {
                                    id: chipMouse
                                    anchors.fill: parent
                                    onClicked: {
                                        root.selectedCategory = modelData;
                                    }
                                }
                            }
                        }
                    }
                }

                // Algorithm List View
                ListView {
                    id: algoListView
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: root.filteredAlgos
                    spacing: ScaleMetrics.dp(3)
                    boundsBehavior: Flickable.StopAtBounds

                    delegate: Rectangle {
                        width: ListView.view.width
                        height: ScaleMetrics.dp(34)
                        radius: 4
                        color: root.activeAlgoId === modelData.id ? Theme.bgCardActive : (itemMouse.pressed ? "#161c28" : "#0d1017")
                        border.color: root.activeAlgoId === modelData.id ? "#ec4899" : Theme.borderCard
                        border.width: root.activeAlgoId === modelData.id ? 1.5 : 1

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: ScaleMetrics.dp(6)
                            spacing: ScaleMetrics.dp(6)

                            Rectangle {
                                width: ScaleMetrics.dp(22)
                                height: ScaleMetrics.dp(20)
                                radius: 3
                                color: root.activeAlgoId === modelData.id ? "#ec4899" : "#1a2233"
                                Text {
                                    anchors.centerIn: parent
                                    text: modelData.id.toString()
                                    font.bold: true
                                    font.family: Theme.fontMono
                                    font.pixelSize: ScaleMetrics.sp(8)
                                    color: root.activeAlgoId === modelData.id ? "#ffffff" : Theme.textSecondary
                                }
                            }

                            Text {
                                text: modelData.name.replace(/^[0-9]+\s*/, "")
                                font.bold: root.activeAlgoId === modelData.id
                                font.pixelSize: ScaleMetrics.sp(9)
                                color: root.activeAlgoId === modelData.id ? Theme.textPrimary : Theme.textSecondary
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }

                            Rectangle {
                                width: ScaleMetrics.dp(52)
                                height: ScaleMetrics.dp(16)
                                radius: 2
                                color: "#10141d"
                                Text {
                                    anchors.centerIn: parent
                                    text: modelData.cat
                                    font.pixelSize: ScaleMetrics.sp(7)
                                    font.bold: true
                                    color: "#ec4899"
                                }
                            }
                        }

                        MouseArea {
                            id: itemMouse
                            anchors.fill: parent
                            onClicked: {
                                root.activeAlgoId = modelData.id;
                                Bridge.setMfxAlgoId(modelData.id);
                            }
                        }
                    }
                }
            }
        }

        // Column 2: Parameters & Signal Flow Console
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: ScaleMetrics.dp(6)
            color: Theme.bgApp
            border.color: Theme.borderCard
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(12)
                spacing: ScaleMetrics.dp(10)

                // Header with Bypass Toggle
                RowLayout {
                    Layout.fillWidth: true
                    ColumnLayout {
                        spacing: 2
                        Text {
                            text: root.currentAlgo ? root.currentAlgo.name : "NO EFFECT SELECTED"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(14)
                            color: "#ec4899"
                        }
                        Text {
                            text: root.currentAlgo ?
                                ("CATEGORY: " + root.currentAlgo.cat + " • " + (root.currentAlgo.params ? root.currentAlgo.params.length : 0) + " DYNAMIC PARAMETERS") :
                                "ROLAND MULTI-EFFECTS ENGINE"
                            font.pixelSize: ScaleMetrics.sp(9)
                            color: Theme.textDim
                        }
                    }
                    Item { Layout.fillWidth: true }

                    // Bypass Button
                    Rectangle {
                        width: ScaleMetrics.dp(84)
                        height: ScaleMetrics.dp(30)
                        radius: ScaleMetrics.dp(4)
                        color: root.isBypassed ? "#3f1a1a" : Theme.bgCardActive
                        border.color: root.isBypassed ? Theme.recording : "#ec4899"
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: root.isBypassed ? "BYPASS" : "ACTIVE"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(9)
                            color: root.isBypassed ? Theme.recording : "#ec4899"
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: Bridge.setMfxBypass(!Bridge.mfxBypassed)
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.borderCard
                }

                // Flexible Parameter Grid (Scrollable if needed)
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    Flickable {
                        id: paramFlickable
                        anchors.fill: parent
                        contentWidth: width
                        contentHeight: paramGrid.implicitHeight
                        clip: true
                        boundsBehavior: Flickable.StopAtBounds

                        GridLayout {
                            id: paramGrid
                            width: parent.width
                            columns: 2
                            rowSpacing: ScaleMetrics.dp(6)
                            columnSpacing: ScaleMetrics.dp(8)

                            Repeater {
                                model: root.currentAlgo && root.currentAlgo.params ? root.currentAlgo.params : []

                                delegate: MfxSlider {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: ScaleMetrics.dp(52)
                                    paramIdx: modelData.idx
                                    label: modelData.label
                                    val: (Bridge.mfxParamValues && modelData.idx < Bridge.mfxParamValues.length) ?
                                            Bridge.mfxParamValues[modelData.idx] :
                                            modelData.val
                                    minVal: (modelData.min !== undefined) ? modelData.min : 0
                                    maxVal: (modelData.max !== undefined) ? modelData.max : 127
                                    unitText: (modelData.unit !== undefined) ? modelData.unit : ""
                                    options: (modelData.options !== undefined) ? modelData.options : []
                                    accent: "#ec4899"
                                    isDimmed: root.isBypassed
                                    onUserModified: (newVal) => {
                                        Bridge.setMfxParam(modelData.idx, newVal);
                                    }
                                }
                            }
                        }
                    }

                    // Subtle vertical scroll indicator
                    Rectangle {
                        anchors.right: parent.right
                        anchors.rightMargin: ScaleMetrics.dp(1)
                        y: paramFlickable.visibleArea.yPosition * paramFlickable.height
                        width: ScaleMetrics.dp(3)
                        height: Math.max(ScaleMetrics.dp(18), paramFlickable.visibleArea.heightRatio * paramFlickable.height)
                        radius: 1.5
                        color: "#ec4899"
                        opacity: paramFlickable.visibleArea.heightRatio < 0.99 ? 0.6 : 0.0
                    }
                }

                // Routing & Send Row
                RowLayout {
                    Layout.fillWidth: true
                    spacing: ScaleMetrics.dp(8)

                    Text {
                        text: "ROUTING:"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Theme.textDim
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(26)
                        radius: 3
                        color: "#10141d"
                        border.color: Theme.borderCard
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: root.isBypassed ?
                                "TONES 1-4 ➔ [MFX BYPASS: DRY DIRECT] ➔ CHORUS / REVERB SENDS" :
                                ("TONES 1-4 ➔ [MFX: " + (root.currentAlgo ? root.currentAlgo.name : "THRU") + "] ➔ CHORUS / REVERB SENDS")
                            font.family: Theme.fontMono
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: root.isBypassed ? Theme.recording : Theme.textSecondary
                        }
                    }
                }
            }
        }
    }

    component MfxSlider: Rectangle {
        id: ms
        property int paramIdx: 0
        property string label: "PARAM"
        property int val: 64
        property int minVal: 0
        property int maxVal: 127
        property string unitText: ""
        property var options: []
        property color accent: Theme.primary
        property bool isDimmed: false

        signal userModified(int newVal)

        radius: ScaleMetrics.dp(4)
        color: "#10141d"
        border.color: Theme.borderCard
        border.width: 1
        opacity: isDimmed ? 0.45 : 1.0

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(5)
            spacing: ScaleMetrics.dp(2)

            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: ms.label
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(8.5)
                    color: Theme.textPrimary
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                Text {
                    text: {
                        if (ms.options && ms.options.length > 0) {
                            var optIdx = ms.val;
                            if (optIdx >= 600) optIdx -= 600;
                            if (optIdx >= 0 && optIdx < ms.options.length) {
                                return ms.options[optIdx];
                            }
                        }
                        return ms.val.toString() + (ms.unitText !== "" ? " " + ms.unitText : "");
                    }
                    font.family: Theme.fontMono
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(8.5)
                    color: ms.accent
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 3
                color: "#0a0d14"
                border.color: Theme.borderCard
                border.width: 1

                Rectangle {
                    x: 0; y: 0
                    width: {
                        var v = ms.val;
                        if (ms.options && ms.options.length > 0 && v >= 600) v -= 600;
                        return parent.width * Math.max(0.0, Math.min(1.0, (v - ms.minVal) / Math.max(1, ms.maxVal - ms.minVal)));
                    }
                    height: parent.height
                    radius: 3
                    color: Qt.rgba(ms.accent.r, ms.accent.g, ms.accent.b, 0.35)
                }

                function updateVal(mouseX) {
                    var norm = Math.max(0.0, Math.min(1.0, mouseX / width));
                    var newVal = Math.round(ms.minVal + norm * (ms.maxVal - ms.minVal));
                    if (newVal !== ms.val) {
                        ms.userModified(newVal);
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    enabled: !ms.isDimmed
                    onPositionChanged: (mouse) => {
                        if (pressed) parent.updateVal(mouse.x);
                    }
                    onPressed: (mouse) => {
                        parent.updateVal(mouse.x);
                    }
                }
            }
        }
    }

    // On-screen Virtual Keyboard
    VirtualKeyboard {
        id: mfxVirtualKeyboard
        objectName: "mfxVirtualKeyboard"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: ScaleMetrics.dp(8)
        height: ScaleMetrics.dp(158)
        visible: root.virtualKeyboardVisible
        z: 99
        accentColor: "#ec4899"

        onKeyClicked: (key) => {
            mfxSearchField.text += key;
        }
        onBackspaceClicked: {
            if (mfxSearchField.text.length > 0) {
                mfxSearchField.text = mfxSearchField.text.slice(0, -1);
            }
        }
        onClearClicked: {
            mfxSearchField.text = "";
            root.searchQuery = "";
        }
        onCloseClicked: {
            root.virtualKeyboardVisible = false;
        }
    }
}

