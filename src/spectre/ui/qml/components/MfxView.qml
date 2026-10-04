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
    property int activeAlgoIdx: 3
    property bool isBypassed: Bridge.mfxBypassed
    property string selectedCategory: "ALL"
    property string searchQuery: ""
    property bool virtualKeyboardVisible: false

    Connections {
        target: Bridge
        function onMfxParamsChanged() {
        }
    }

    onActiveAlgoIdxChanged: {
        if (activeAlgoIdx >= 0 && activeAlgoIdx < algoList.length) {
            activeAlgoId = algoList[activeAlgoIdx].id;
        }
    }

    readonly property var categories: [
        "ALL", "FILTER/EQ", "DRIVE", "MOD", "CHORUS", "DELAY", "PITCH", "SPECIAL"
    ]

    property var algoList: [
        {
            id: 1,
            name: "01 EQUALIZER",
            cat: "FILTER/EQ",
            params: [
                { label: "LOW GAIN", val: 64, min: 0, max: 127, unit: "dB" },
                { label: "LOW FREQ", val: 32, min: 0, max: 127, unit: "Hz" },
                { label: "MID GAIN", val: 68, min: 0, max: 127, unit: "dB" },
                { label: "MID FREQ", val: 50, min: 0, max: 127, unit: "Hz" },
                { label: "MID Q", val: 40, min: 0, max: 127, unit: "" },
                { label: "HIGH GAIN", val: 64, min: 0, max: 127, unit: "dB" },
                { label: "HIGH FREQ", val: 96, min: 0, max: 127, unit: "Hz" },
                { label: "LEVEL", val: 100, min: 0, max: 127, unit: "" }
            ]
        },
        {
            id: 4,
            name: "04 DISTORTION",
            cat: "DRIVE",
            params: [
                { label: "DRIVE", val: 85, min: 0, max: 127, unit: "" },
                { label: "TYPE", val: 2, min: 0, max: 5, unit: "" },
                { label: "TONE", val: 72, min: 0, max: 127, unit: "" },
                { label: "BOTTOM", val: 55, min: 0, max: 127, unit: "" },
                { label: "PRESENCE", val: 60, min: 0, max: 127, unit: "" },
                { label: "LEVEL", val: 90, min: 0, max: 127, unit: "" }
            ]
        },
        {
            id: 11,
            name: "11 PHASER",
            cat: "MOD",
            params: [
                { label: "MODE", val: 4, min: 0, max: 7, unit: "STAGES" },
                { label: "RATE", val: 45, min: 0, max: 127, unit: "Hz" },
                { label: "DEPTH", val: 80, min: 0, max: 127, unit: "" },
                { label: "MANUAL", val: 60, min: 0, max: 127, unit: "" },
                { label: "FEEDBACK", val: 60, min: 0, max: 127, unit: "%" },
                { label: "MIX", val: 85, min: 0, max: 127, unit: "%" }
            ]
        },
        {
            id: 15,
            name: "15 TAPE ECHO",
            cat: "DELAY",
            params: [
                { label: "TIME", val: 75, min: 0, max: 127, unit: "ms" },
                { label: "FEEDBACK", val: 65, min: 0, max: 127, unit: "%" },
                { label: "WOW/FLUTTER", val: 40, min: 0, max: 127, unit: "" },
                { label: "BASS", val: 64, min: 0, max: 127, unit: "dB" },
                { label: "TREBLE", val: 64, min: 0, max: 127, unit: "dB" },
                { label: "HF DAMP", val: 55, min: 0, max: 127, unit: "Hz" },
                { label: "PAN", val: 64, min: 0, max: 127, unit: "" },
                { label: "DRY/WET", val: 70, min: 0, max: 127, unit: "%" }
            ]
        },
        {
            id: 16,
            name: "16 SPACE-D",
            cat: "CHORUS",
            params: [
                { label: "RATE", val: 30, min: 0, max: 127, unit: "Hz" },
                { label: "DEPTH", val: 90, min: 0, max: 127, unit: "" },
                { label: "MANUAL", val: 45, min: 0, max: 127, unit: "" },
                { label: "PHASE", val: 90, min: 0, max: 180, unit: "deg" },
                { label: "BALANCE", val: 80, min: 0, max: 127, unit: "%" },
                { label: "LEVEL", val: 100, min: 0, max: 127, unit: "" }
            ]
        },
        {
            id: 25,
            name: "25 ROTARY",
            cat: "MOD",
            params: [
                { label: "SPEED", val: 80, min: 0, max: 127, unit: "Hz" },
                { label: "ACCEL", val: 60, min: 0, max: 127, unit: "" },
                { label: "WOOFER", val: 64, min: 0, max: 127, unit: "" },
                { label: "TWEETER", val: 70, min: 0, max: 127, unit: "" },
                { label: "SEPARATION", val: 90, min: 0, max: 127, unit: "deg" },
                { label: "DRIVE", val: 30, min: 0, max: 127, unit: "" },
                { label: "LEVEL", val: 95, min: 0, max: 127, unit: "" }
            ]
        },
        {
            id: 33,
            name: "33 SBF-325 FLANGER",
            cat: "CHORUS",
            params: [
                { label: "RATE", val: 25, min: 0, max: 127, unit: "Hz" },
                { label: "DEPTH", val: 70, min: 0, max: 127, unit: "" },
                { label: "MANUAL", val: 50, min: 0, max: 127, unit: "" },
                { label: "FEEDBACK", val: 85, min: 0, max: 127, unit: "%" },
                { label: "CROSS FEED", val: 40, min: 0, max: 127, unit: "%" },
                { label: "MIX", val: 80, min: 0, max: 127, unit: "%" }
            ]
        },
        {
            id: 45,
            name: "45 STEP PHASER",
            cat: "MOD",
            params: [
                { label: "STEP RATE", val: 60, min: 0, max: 127, unit: "Hz" },
                { label: "PHASER RATE", val: 35, min: 0, max: 127, unit: "Hz" },
                { label: "DEPTH", val: 80, min: 0, max: 127, unit: "" },
                { label: "RESONANCE", val: 65, min: 0, max: 127, unit: "" },
                { label: "STEP RESET", val: 0, min: 0, max: 1, unit: "" },
                { label: "MIX", val: 90, min: 0, max: 127, unit: "%" }
            ]
        },
        {
            id: 56,
            name: "56 PITCH SHIFTER",
            cat: "PITCH",
            params: [
                { label: "COARSE", val: 76, min: 0, max: 127, unit: "st" },
                { label: "FINE", val: 64, min: 0, max: 127, unit: "c" },
                { label: "FEEDBACK", val: 30, min: 0, max: 127, unit: "%" },
                { label: "DELAY TIME", val: 45, min: 0, max: 127, unit: "ms" },
                { label: "PAN", val: 64, min: 0, max: 127, unit: "" },
                { label: "BALANCE", val: 64, min: 0, max: 127, unit: "%" }
            ]
        },
        {
            id: 68,
            name: "68 SLICER",
            cat: "SPECIAL",
            params: [
                { label: "TIMING", val: 80, min: 0, max: 127, unit: "BPM" },
                { label: "PATTERN", val: 12, min: 1, max: 20, unit: "" },
                { label: "ATTACK", val: 40, min: 0, max: 127, unit: "" },
                { label: "SHUFFLE", val: 25, min: 0, max: 127, unit: "%" },
                { label: "RESET", val: 0, min: 0, max: 1, unit: "" },
                { label: "LEVEL", val: 100, min: 0, max: 127, unit: "" }
            ]
        }
    ]

    function getAlgoById(targetId) {
        for (var i = 0; i < root.algoList.length; i++) {
            if (root.algoList[i].id === targetId) return root.algoList[i];
        }
        return root.algoList[0];
    }

    readonly property var currentAlgo: getAlgoById(root.activeAlgoId)

    function getFilteredAlgos() {
        var query = root.searchQuery.trim().toLowerCase();
        var cat = root.selectedCategory;
        var res = [];
        for (var i = 0; i < root.algoList.length; i++) {
            var item = root.algoList[i];
            var matchCat = (cat === "ALL" || item.cat === cat);
            var matchQuery = (query === "" ||
                              item.name.toLowerCase().indexOf(query) !== -1 ||
                              item.cat.toLowerCase().indexOf(query) !== -1 ||
                              item.id.toString().indexOf(query) !== -1);
            if (matchCat && matchQuery) {
                res.push(item);
            }
        }
        return res;
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

                // Flexible 4-to-8 Parameter Grid (Scrollable if needed)
                Flickable {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    contentWidth: width
                    contentHeight: paramGrid.implicitHeight
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds

                    GridLayout {
                        id: paramGrid
                        width: parent.width
                        columns: 2
                        rowSpacing: ScaleMetrics.dp(8)
                        columnSpacing: ScaleMetrics.dp(8)

                        Repeater {
                            model: root.currentAlgo && root.currentAlgo.params ? root.currentAlgo.params : []

                            delegate: MfxSlider {
                                Layout.fillWidth: true
                                Layout.preferredHeight: ScaleMetrics.dp(66)
                                label: modelData.label
                                val: modelData.val
                                minVal: (modelData.min !== undefined) ? modelData.min : 0
                                maxVal: (modelData.max !== undefined) ? modelData.max : 127
                                unitText: (modelData.unit !== undefined) ? modelData.unit : ""
                                accent: "#ec4899"
                                isDimmed: root.isBypassed
                                onValChanged: {
                                    modelData.val = val;
                                }
                            }
                        }
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
        property string label: "PARAM"
        property int val: 64
        property int minVal: 0
        property int maxVal: 127
        property string unitText: ""
        property color accent: Theme.primary
        property bool isDimmed: false

        radius: ScaleMetrics.dp(4)
        color: "#10141d"
        border.color: Theme.borderCard
        border.width: 1
        opacity: isDimmed ? 0.45 : 1.0

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(6)
            spacing: ScaleMetrics.dp(4)

            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: ms.label
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(9)
                    color: Theme.textPrimary
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                Text {
                    text: ms.val.toString() + (ms.unitText !== "" ? " " + ms.unitText : "")
                    font.family: Theme.fontMono
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(9)
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
                    width: parent.width * Math.max(0.0, Math.min(1.0, (ms.val - ms.minVal) / Math.max(1, ms.maxVal - ms.minVal)))
                    height: parent.height
                    radius: 3
                    color: Qt.rgba(ms.accent.r, ms.accent.g, ms.accent.b, 0.35)
                }

                function updateVal(mouseX) {
                    var norm = Math.max(0.0, Math.min(1.0, mouseX / width));
                    ms.val = Math.round(ms.minVal + norm * (ms.maxVal - ms.minVal));
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

