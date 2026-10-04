import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

Rectangle {
    id: root
    anchors.fill: parent
    color: Qt.rgba(0.02, 0.03, 0.04, 0.85)
    visible: false
    z: 1000

    property int targetTone: 1
    readonly property color toneColor: targetTone === 1 ? Theme.tone1 :
                                        targetTone === 2 ? Theme.tone2 :
                                        targetTone === 3 ? Theme.tone3 : Theme.tone4

    property string selectedBank: "ALL"
    property string selectedCategory: "ALL"
    property string searchText: ""
    property var waveList: []
    property bool virtualKeyboardVisible: false

    // Current active wave on this tone
    readonly property var currentActiveWave: (Bridge.toneWaveData && Bridge.toneWaveData.length >= targetTone) ?
                                             Bridge.toneWaveData[targetTone - 1] : null

    function open(toneIndex) {
        targetTone = Math.max(1, Math.min(4, toneIndex));
        searchText = "";
        searchField.text = "";
        virtualKeyboardVisible = false;
        refreshWaves();
        visible = true;
    }

    function close() {
        visible = false;
    }

    function refreshWaves() {
        waveList = Bridge.getFilteredWaves(selectedCategory, selectedBank, searchText);
    }

    // Dim background overlay touch catcher (absorbs clicks to prevent leaking to underlying views)
    MouseArea {
        id: backdropArea
        anchors.fill: parent
        onClicked: (mouse) => {
            var cardPos = card.mapToItem(root, 0, 0);
            var inCard = (mouse.x >= cardPos.x && mouse.x <= cardPos.x + card.width &&
                          mouse.y >= cardPos.y && mouse.y <= cardPos.y + card.height);
            if (!inCard) {
                root.close();
            }
        }
    }

    // Modal Card
    Rectangle {
        id: card
        width: Math.min(parent.width - ScaleMetrics.dp(40), ScaleMetrics.dp(880))
        height: Math.min(parent.height - ScaleMetrics.dp(30), ScaleMetrics.dp(540))
        anchors.centerIn: parent
        color: Theme.bgCard
        radius: ScaleMetrics.dp(10)
        border.color: Theme.borderCard
        border.width: 1
        clip: true

        // Absorb touches inside card so they never reach the backdrop dismiss
        MouseArea {
            anchors.fill: parent
        }

        // Glow header border with tone color
        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: ScaleMetrics.dp(3)
            color: root.toneColor
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(12)
            spacing: ScaleMetrics.dp(8)

            // Header Row: Tone badge, Title, Wave count, Close button
            RowLayout {
                Layout.fillWidth: true
                spacing: ScaleMetrics.dp(8)

                Rectangle {
                    width: ScaleMetrics.dp(70)
                    height: ScaleMetrics.dp(26)
                    radius: ScaleMetrics.dp(4)
                    color: root.toneColor
                    Text {
                        anchors.centerIn: parent
                        text: "TONE " + root.targetTone
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(11)
                        color: "#000000"
                    }
                }

                Text {
                    text: "SELECT WAVEFORM"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(13)
                    font.letterSpacing: 1.2
                    color: Theme.textPrimary
                }

                // Currently active wave badge
                Rectangle {
                    visible: root.currentActiveWave !== null
                    height: ScaleMetrics.dp(24)
                    Layout.preferredWidth: currRow.implicitWidth + ScaleMetrics.dp(12)
                    radius: ScaleMetrics.dp(4)
                    color: Theme.bgSurface
                    border.color: root.toneColor
                    border.width: 1

                    RowLayout {
                        id: currRow
                        anchors.centerIn: parent
                        spacing: ScaleMetrics.dp(6)
                        Text {
                            text: "ACTIVE: " + (root.currentActiveWave ? root.currentActiveWave.name : "")
                            font.pixelSize: ScaleMetrics.sp(10)
                            font.bold: true
                            color: root.toneColor
                        }
                    }
                }

                Item { Layout.fillWidth: true }

                Text {
                    text: root.waveList.length + " WAVES"
                    font.pixelSize: ScaleMetrics.sp(10)
                    font.bold: true
                    color: Theme.textDim
                }

                // Close Button
                Rectangle {
                    width: ScaleMetrics.dp(30)
                    height: ScaleMetrics.dp(30)
                    radius: ScaleMetrics.dp(6)
                    color: Theme.bgSurface
                    border.color: Theme.borderCard
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: "✕"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(14)
                        color: Theme.textSecondary
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: root.close()
                    }
                }
            }

            // Bank Selector & Search Bar Row
            RowLayout {
                Layout.fillWidth: true
                spacing: ScaleMetrics.dp(8)

                // Bank Segmented Toggle (INTA / INTB / ALL)
                RowLayout {
                    spacing: ScaleMetrics.dp(4)
                    Repeater {
                        model: ["INTA", "INTB", "ALL"]
                        delegate: Rectangle {
                            id: bankBtn
                            property bool isSel: root.selectedBank === modelData
                            width: ScaleMetrics.dp(56)
                            height: ScaleMetrics.dp(28)
                            radius: ScaleMetrics.dp(4)
                            color: isSel ? Theme.bgCardActive : Theme.bgApp
                            border.color: isSel ? root.toneColor : Theme.borderCard
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: modelData
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(10)
                                color: bankBtn.isSel ? root.toneColor : Theme.textDim
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    root.selectedBank = modelData;
                                    root.refreshWaves();
                                }
                            }
                        }
                    }
                }

                // Search Input Box
                Rectangle {
                    Layout.fillWidth: true
                    height: ScaleMetrics.dp(28)
                    radius: ScaleMetrics.dp(4)
                    color: Theme.bgApp
                    border.color: searchField.activeFocus ? root.toneColor : Theme.borderCard
                    border.width: 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: ScaleMetrics.dp(8)
                        anchors.rightMargin: ScaleMetrics.dp(8)
                        spacing: ScaleMetrics.dp(6)

                        Text {
                            text: "🔍"
                            font.pixelSize: ScaleMetrics.sp(10)
                            color: Theme.textDim
                        }

                        TextInput {
                            id: searchField
                            Layout.fillWidth: true
                            font.pixelSize: ScaleMetrics.sp(11)
                            font.family: Theme.fontSans
                            color: Theme.textPrimary
                            clip: true

                            Text {
                                text: "Search name or # (e.g. Saw, Juno, 579)..."
                                font.pixelSize: ScaleMetrics.sp(11)
                                color: Theme.textDim
                                visible: !searchField.text && !searchField.activeFocus
                            }

                            onTextChanged: {
                                root.searchText = text;
                                root.refreshWaves();
                            }

                            onActiveFocusChanged: {
                                if (activeFocus) {
                                    root.virtualKeyboardVisible = true;
                                }
                            }
                        }

                        Text {
                            visible: searchField.text.length > 0
                            text: "✕"
                            font.pixelSize: ScaleMetrics.sp(11)
                            color: Theme.textDim
                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    searchField.text = "";
                                    root.searchText = "";
                                    root.refreshWaves();
                                }
                            }
                        }

                        // Virtual Keyboard Toggle Button
                        Rectangle {
                            width: ScaleMetrics.dp(28)
                            height: ScaleMetrics.dp(22)
                            radius: ScaleMetrics.dp(4)
                            color: root.virtualKeyboardVisible ? root.toneColor : Theme.bgSurface
                            border.color: root.virtualKeyboardVisible ? root.toneColor : Theme.borderCard
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: "⌨"
                                font.pixelSize: ScaleMetrics.sp(12)
                                color: root.virtualKeyboardVisible ? "#000000" : Theme.textSecondary
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: root.virtualKeyboardVisible = !root.virtualKeyboardVisible
                            }
                        }
                    }
                }
            }

            // Horizontal Category Selector Chips
            Flickable {
                Layout.fillWidth: true
                height: ScaleMetrics.dp(32)
                contentWidth: categoryRow.implicitWidth
                clip: true
                boundsBehavior: Flickable.StopAtBounds

                RowLayout {
                    id: categoryRow
                    spacing: ScaleMetrics.dp(4)

                    readonly property var categories: [
                        { id: "ALL", label: "ALL" },
                        { id: "synth_wave", label: "SYNTH OSC" },
                        { id: "synth_lead", label: "SYNTH LEAD" },
                        { id: "piano", label: "PIANO" },
                        { id: "bass", label: "BASS" },
                        { id: "guitar", label: "GUITAR" },
                        { id: "strings", label: "STRINGS" },
                        { id: "brass", label: "BRASS" },
                        { id: "organ", label: "ORGAN" },
                        { id: "vocal", label: "VOCAL" },
                        { id: "drums", label: "DRUMS" },
                        { id: "sfx", label: "SFX" },
                        { id: "world", label: "WORLD" }
                    ]

                    Repeater {
                        model: categoryRow.categories
                        delegate: Rectangle {
                            id: catChip
                            property bool isSel: root.selectedCategory === modelData.id
                            height: ScaleMetrics.dp(26)
                            Layout.preferredWidth: catText.implicitWidth + ScaleMetrics.dp(16)
                            radius: ScaleMetrics.dp(13)
                            color: isSel ? Theme.bgCardActive : Theme.bgApp
                            border.color: isSel ? root.toneColor : Theme.borderCard
                            border.width: 1

                            Text {
                                id: catText
                                anchors.centerIn: parent
                                text: modelData.label
                                font.bold: catChip.isSel
                                font.pixelSize: ScaleMetrics.sp(9)
                                font.letterSpacing: 0.5
                                color: catChip.isSel ? root.toneColor : Theme.textSecondary
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    root.selectedCategory = modelData.id;
                                    root.refreshWaves();
                                }
                            }
                        }
                    }
                }
            }

            // Waveform Grid/List (2 Columns for touch efficiency)
            GridView {
                id: waveGrid
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                cellWidth: width / 2
                cellHeight: ScaleMetrics.dp(48)
                model: root.waveList

                delegate: Rectangle {
                    id: waveDelegate
                    width: waveGrid.cellWidth - ScaleMetrics.dp(4)
                    height: ScaleMetrics.dp(44)
                    radius: ScaleMetrics.dp(6)

                    readonly property bool isActive: root.currentActiveWave &&
                                                      root.currentActiveWave.bank === modelData.bank &&
                                                      root.currentActiveWave.id === modelData.id

                    color: isActive ? Theme.bgCardActive : (touchArea.pressed ? Theme.bgSurface : Theme.bgApp)
                    border.color: isActive ? root.toneColor : Theme.borderCard
                    border.width: isActive ? 1.5 : 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: ScaleMetrics.dp(6)
                        spacing: ScaleMetrics.dp(8)

                        // Miniature Waveform / Category Glyph Preview
                        CategoryGlyph {
                            Layout.preferredWidth: ScaleMetrics.dp(34)
                            Layout.preferredHeight: ScaleMetrics.dp(24)
                            category: modelData.category || "synth_wave"
                            isSingleCycle: modelData.is_single_cycle || false
                            samples64: modelData.samples_64 || null
                            toneIndex: root.targetTone - 1
                            color: waveDelegate.isActive ? root.toneColor : Theme.textPrimary
                        }

                        // Wave Number & Name
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 1

                            RowLayout {
                                spacing: ScaleMetrics.dp(4)
                                Text {
                                    text: modelData.bank + " " + String(modelData.id).padStart(4, "0")
                                    font.pixelSize: ScaleMetrics.sp(9)
                                    font.family: Theme.fontMono
                                    color: waveDelegate.isActive ? root.toneColor : Theme.textDim
                                }
                                Text {
                                    visible: modelData.is_single_cycle
                                    text: "• OSC"
                                    font.bold: true
                                    font.pixelSize: ScaleMetrics.sp(8)
                                    color: Theme.playing
                                }
                            }

                            Text {
                                Layout.fillWidth: true
                                text: modelData.name
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(11)
                                color: waveDelegate.isActive ? root.toneColor : Theme.textPrimary
                                elide: Text.ElideRight
                            }
                        }

                        // Active Indicator / Select Button
                        Rectangle {
                            Layout.preferredWidth: ScaleMetrics.dp(24)
                            Layout.preferredHeight: ScaleMetrics.dp(24)
                            radius: width / 2
                            color: waveDelegate.isActive ? root.toneColor : "transparent"
                            border.color: waveDelegate.isActive ? root.toneColor : Theme.borderCard
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: waveDelegate.isActive ? "✓" : ""
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(11)
                                color: "#000000"
                            }
                        }
                    }

                    MouseArea {
                        id: touchArea
                        anchors.fill: parent
                        onClicked: {
                            Bridge.setToneWave(root.targetTone, modelData.bank, modelData.id);
                        }
                    }
                }
            }

            // On-screen Virtual Keyboard
            VirtualKeyboard {
                id: virtualKeyboard
                objectName: "virtualKeyboard"
                Layout.fillWidth: true
                Layout.preferredHeight: ScaleMetrics.dp(165)
                visible: root.virtualKeyboardVisible
                accentColor: root.toneColor

                onKeyClicked: (key) => {
                    searchField.text += key;
                }
                onBackspaceClicked: {
                    if (searchField.text.length > 0) {
                        searchField.text = searchField.text.slice(0, -1);
                    }
                }
                onClearClicked: {
                    searchField.text = "";
                }
                onCloseClicked: {
                    root.virtualKeyboardVisible = false;
                }
            }

            // Footer: Live Audition Hint & Done Button
            RowLayout {
                Layout.fillWidth: true
                spacing: ScaleMetrics.dp(8)

                Text {
                    text: "Tap any wave to immediately assign and audition on Roland synth."
                    font.pixelSize: ScaleMetrics.sp(9)
                    color: Theme.textDim
                    Layout.fillWidth: true
                }

                Rectangle {
                    width: ScaleMetrics.dp(90)
                    height: ScaleMetrics.dp(30)
                    radius: ScaleMetrics.dp(5)
                    color: root.toneColor

                    Text {
                        anchors.centerIn: parent
                        text: "DONE"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(11)
                        color: "#000000"
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: root.close()
                    }
                }
            }
        }
    }
}
