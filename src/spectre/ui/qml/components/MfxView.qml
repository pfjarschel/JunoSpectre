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
                        color: Theme.pageAccent
                    }
                    Text {
                        text: "MFX ALGORITHMS"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(10)
                        font.letterSpacing: 1.1
                        color: Theme.textPrimary
                    }
                    Item { Layout.fillWidth: true }
                    Rectangle {
                        objectName: "mfxTargetChip"
                        height: ScaleMetrics.dp(18)
                        Layout.preferredWidth: Math.min(targetLabel.implicitWidth + ScaleMetrics.dp(12), ScaleMetrics.dp(110))
                        Layout.maximumWidth: ScaleMetrics.dp(110)
                        Layout.minimumWidth: ScaleMetrics.dp(52)
                        radius: 3
                        color: Theme.tint(Theme.pageAccent)
                        border.color: Theme.pageAccent
                        border.width: 1
                        clip: true
                        Text {
                            id: targetLabel
                            objectName: "mfxTargetLabel"
                            anchors.fill: parent
                            anchors.leftMargin: ScaleMetrics.dp(6)
                            anchors.rightMargin: ScaleMetrics.dp(6)
                            verticalAlignment: Text.AlignVCenter
                            horizontalAlignment: Text.AlignHCenter
                            text: Bridge.mfxEditTargetLabel
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(7)
                            font.family: Theme.fontMono
                            color: Theme.pageAccent
                            elide: Text.ElideRight
                        }
                    }
                    Text {
                        text: root.filteredAlgos.length + " / " + root.algoList.length
                        font.family: Theme.fontMono
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Theme.pageAccent
                    }
                }

                // Search Input Box
                Rectangle {
                    Layout.fillWidth: true
                    height: ScaleMetrics.dp(28)
                    radius: ScaleMetrics.dp(4)
                    color: Theme.bgTrack
                    border.color: mfxSearchField.activeFocus || root.virtualKeyboardVisible ? Theme.pageAccent : Theme.borderCard
                    border.width: 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: ScaleMetrics.dp(8)
                        anchors.rightMargin: ScaleMetrics.dp(6)
                        spacing: ScaleMetrics.dp(6)

                        Icon {
                            name: "search"
                            size: 12
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
                        SpButton {
                            implicitWidth: ScaleMetrics.dp(22)
                            implicitHeight: ScaleMetrics.dp(20)
                            icon: "keyboard"
                            fontSize: 10
                            checked: root.virtualKeyboardVisible
                            onClicked: {
                                root.virtualKeyboardVisible = !root.virtualKeyboardVisible;
                                if (root.virtualKeyboardVisible) {
                                    mfxSearchField.forceActiveFocus();
                                }
                            }
                        }

                        // Clear Button
                        Icon {
                            visible: mfxSearchField.text.length > 0
                            name: "close"
                            size: 14
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
                        anchors.rightMargin: ScaleMetrics.dp(50) // Leave room for the keyboard and close buttons
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
                            delegate: SpButton {
                                id: catChip
                                property bool isSel: root.selectedCategory === modelData
                                implicitHeight: ScaleMetrics.dp(22)
                                implicitWidth: label.implicitWidth + ScaleMetrics.dp(14)
                                text: modelData
                                fontSize: 8
                                checked: isSel
                                onClicked: {
                                    root.selectedCategory = modelData;
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
                        color: root.activeAlgoId === modelData.id ? Theme.bgCardActive : (itemMouse.pressed ? Theme.bgCardActive : Theme.bgControl)
                        border.color: root.activeAlgoId === modelData.id ? Theme.pageAccent : Theme.borderCard
                        border.width: root.activeAlgoId === modelData.id ? 1.5 : 1

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: ScaleMetrics.dp(6)
                            spacing: ScaleMetrics.dp(6)

                            Rectangle {
                                width: ScaleMetrics.dp(22)
                                height: ScaleMetrics.dp(20)
                                radius: 3
                                color: root.activeAlgoId === modelData.id ? Theme.pageAccent : Theme.bgRaised
                                Text {
                                    anchors.centerIn: parent
                                    text: modelData.id.toString()
                                    font.bold: true
                                    font.family: Theme.fontMono
                                    font.pixelSize: ScaleMetrics.sp(8)
                                    color: root.activeAlgoId === modelData.id ? Theme.textPrimary : Theme.textSecondary
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
                                color: Theme.bgControl
                                Text {
                                    anchors.centerIn: parent
                                    text: modelData.cat
                                    font.pixelSize: ScaleMetrics.sp(7)
                                    font.bold: true
                                    color: Theme.pageAccent
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
                            color: Theme.pageAccent
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

                    // PERFORM: MFX1-3 are chained (Performance MFX Structure); tap for Routing
                    SpButton {
                        objectName: "mfxChainTag"
                        readonly property int st: Bridge.perfStructure
                        visible: Bridge.soundMode === "PERFORM" && st > 0
                        implicitWidth: label.implicitWidth + ScaleMetrics.dp(16)
                        implicitHeight: ScaleMetrics.dp(30)
                        text: "MFX CHAIN · TYPE " + (st + 1) + " · " + Bridge.perfMfxStructures[st].label
                        fontSize: 8
                        variant: "outline"
                        onClicked: Bridge.setActiveView("ROUTING")
                    }

                    // Bypass Button
                    SpButton {
                        implicitWidth: ScaleMetrics.dp(84)
                        implicitHeight: ScaleMetrics.dp(30)
                        text: root.isBypassed ? "BYPASS" : "ACTIVE"
                        variant: "outline"
                        accent: root.isBypassed ? Theme.recording : Theme.pageAccent
                        checked: root.isBypassed
                        onClicked: Bridge.setMfxBypass(!Bridge.mfxBypassed)
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.borderCard
                }

                // Curve editor (MFX 01 EQUALIZER / 02 SPECTRUM only, above sliders)
                EqCurvePanel {
                    visible: root.activeAlgoId === 1 || root.activeAlgoId === 2
                    Layout.fillWidth: true
                    Layout.preferredHeight: visible ? ScaleMetrics.dp(232) : 0
                    algo: root.currentAlgo
                    isDimmed: root.isBypassed
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
                                    scrollView: paramFlickable
                                    paramIdx: modelData.idx
                                    label: modelData.label
                                    val: (Bridge.mfxParamValues && modelData.idx < Bridge.mfxParamValues.length) ?
                                            Bridge.mfxParamValues[modelData.idx] :
                                            modelData.val
                                    minVal: (modelData.min !== undefined) ? modelData.min : 0
                                    maxVal: (modelData.max !== undefined) ? modelData.max : 127
                                    unitText: (modelData.unit !== undefined) ? modelData.unit : ""
                                    options: (modelData.options !== undefined) ? modelData.options : []
                                    accent: Theme.pageAccent
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
                        color: Theme.pageAccent
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
                        color: Theme.bgControl
                        border.color: Theme.borderCard
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: root.isBypassed ?
                                "TONES 1-4 → [MFX BYPASS: DRY DIRECT] → CHORUS / REVERB SENDS" :
                                ("TONES 1-4 → [MFX: " + (root.currentAlgo ? root.currentAlgo.name : "THRU") + "] → CHORUS / REVERB SENDS")
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

    component MfxSlider: SpSlider {
        id: ms
        property int paramIdx: 0
        property int val: 64
        property int minVal: 0
        property int maxVal: 127
        property string unitText: ""
        property var options: []
        property bool isDimmed: false
        // Option-list values may arrive offset by 600 (wire encoding)
        readonly property int _v: (options && options.length > 0 && val >= 600) ? val - 600 : val

        signal userModified(int newVal)

        stacked: true
        enabled: !isDimmed
        from: minVal
        to: maxVal
        integer: true
        norm: (_v - minVal) / Math.max(1, maxVal - minVal)
        valueText: (options && options.length > 0 && _v >= 0 && _v < options.length)
                   ? options[_v] : val.toString() + (unitText !== "" ? " " + unitText : "")
        onMoved: (v) => { if (v !== ms.val) ms.userModified(v); }
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
        accentColor: Theme.pageAccent

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

