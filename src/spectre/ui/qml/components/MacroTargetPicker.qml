import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

// Parameter selector: category chips (ALL first) + search with virtual
// keyboard + single-column target list. Emits addRequested(key).
Rectangle {
    id: root
    anchors.fill: parent
    color: "#e60a0c10"
    visible: false
    z: 20

    property int targetMacro: 1
    property color macroColor: Theme.primary
    property string selectedCategory: "ALL"
    property string searchText: ""
    property var targetList: []
    property var assignedKeys: []
    property bool keyboardVisible: false

    signal addRequested(string key)
    signal closeRequested()

    function open(macroIndex, color) {
        targetMacro = macroIndex;
        macroColor = color;
        selectedCategory = "ALL";
        searchText = "";
        searchField.text = "";
        keyboardVisible = false;
        refreshTargets();
        visible = true;
    }

    function close() {
        visible = false;
        keyboardVisible = false;
    }

    function refreshTargets() {
        targetList = Bridge.getMacroTargets(selectedCategory, searchText);
    }

    function isAssigned(key) {
        for (let i = 0; i < assignedKeys.length; i++) {
            if (assignedKeys[i] === key) return true;
        }
        return false;
    }

    MouseArea {
        anchors.fill: parent
        onClicked: root.closeRequested()
    }

    Rectangle {
        id: card
        width: Math.min(parent.width - ScaleMetrics.dp(80), ScaleMetrics.dp(720))
        height: Math.min(parent.height - ScaleMetrics.dp(40), ScaleMetrics.dp(460))
        anchors.centerIn: parent
        color: Theme.bgCard
        radius: ScaleMetrics.dp(10)
        border.color: root.macroColor
        border.width: 1
        clip: true

        MouseArea { anchors.fill: parent }

        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: ScaleMetrics.dp(3)
            color: root.macroColor
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(12)
            spacing: ScaleMetrics.dp(8)

            // Header
            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: "ADD PARAMETER • M" + root.targetMacro
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(12)
                    font.letterSpacing: 1.0
                    color: Theme.textPrimary
                }
                Item { Layout.fillWidth: true }
                Text {
                    text: root.targetList.length + " TARGETS"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(10)
                    color: Theme.textDim
                }
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
                    MouseArea { anchors.fill: parent; onClicked: root.closeRequested() }
                }
            }

            // Search row
            Rectangle {
                Layout.fillWidth: true
                height: ScaleMetrics.dp(28)
                radius: ScaleMetrics.dp(4)
                color: Theme.bgApp
                border.color: searchField.activeFocus ? root.macroColor : Theme.borderCard
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: ScaleMetrics.dp(8)
                    anchors.rightMargin: ScaleMetrics.dp(8)
                    spacing: ScaleMetrics.dp(6)

                    Text { text: "🔍"; font.pixelSize: ScaleMetrics.sp(10); color: Theme.textDim }

                    TextInput {
                        id: searchField
                        Layout.fillWidth: true
                        font.pixelSize: ScaleMetrics.sp(11)
                        color: Theme.textPrimary
                        clip: true
                        Text {
                            text: "Search (e.g. cutoff, chorus, T2)..."
                            font.pixelSize: ScaleMetrics.sp(11)
                            color: Theme.textDim
                            visible: !searchField.text && !searchField.activeFocus
                        }
                        onTextChanged: {
                            root.searchText = text;
                            root.refreshTargets();
                        }
                        onActiveFocusChanged: {
                            if (activeFocus) root.keyboardVisible = true;
                        }
                    }

                    Text {
                        visible: searchField.text.length > 0
                        text: "✕"
                        font.pixelSize: ScaleMetrics.sp(11)
                        color: Theme.textDim
                        MouseArea {
                            anchors.fill: parent
                            onClicked: { searchField.text = ""; }
                        }
                    }

                    Rectangle {
                        width: ScaleMetrics.dp(28)
                        height: ScaleMetrics.dp(22)
                        radius: ScaleMetrics.dp(4)
                        color: root.keyboardVisible ? root.macroColor : Theme.bgSurface
                        border.color: Theme.borderCard
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: "⌨"
                            font.pixelSize: ScaleMetrics.sp(12)
                            color: root.keyboardVisible ? "#000000" : Theme.textSecondary
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: root.keyboardVisible = !root.keyboardVisible
                        }
                    }
                }
            }

            // Category chips
            Flickable {
                Layout.fillWidth: true
                height: ScaleMetrics.dp(32)
                contentWidth: categoryRow.implicitWidth
                clip: true
                boundsBehavior: Flickable.StopAtBounds

                RowLayout {
                    id: categoryRow
                    spacing: ScaleMetrics.dp(4)
                    readonly property var categories: ["ALL", "FILTER", "AMP", "PITCH", "LFO", "FX", "COMMON", "MORPH", "PART"]

                    Repeater {
                        model: categoryRow.categories
                        delegate: Rectangle {
                            property bool isSel: root.selectedCategory === modelData
                            height: ScaleMetrics.dp(26)
                            Layout.preferredWidth: catText.implicitWidth + ScaleMetrics.dp(16)
                            radius: ScaleMetrics.dp(13)
                            color: isSel ? Theme.bgCardActive : Theme.bgApp
                            border.color: isSel ? root.macroColor : Theme.borderCard
                            border.width: 1
                            Text {
                                id: catText
                                anchors.centerIn: parent
                                text: modelData
                                font.bold: parent.isSel
                                font.pixelSize: ScaleMetrics.sp(9)
                                color: parent.isSel ? root.macroColor : Theme.textSecondary
                            }
                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    root.selectedCategory = modelData;
                                    root.refreshTargets();
                                }
                            }
                        }
                    }
                }
            }

            // Target list
            ListView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: ScaleMetrics.dp(4)
                model: root.targetList

                delegate: Rectangle {
                    width: ListView.view.width
                    height: ScaleMetrics.dp(44)
                    radius: ScaleMetrics.dp(6)
                    color: touchArea.pressed ? Theme.bgSurface : Theme.bgApp
                    border.color: Theme.borderCard
                    border.width: 1
                    readonly property bool assigned: root.isAssigned(modelData.key)

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: ScaleMetrics.dp(8)
                        spacing: ScaleMetrics.dp(8)

                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.alignment: Qt.AlignVCenter
                            spacing: 1
                            Text {
                                Layout.fillWidth: true
                                text: modelData.title
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(11)
                                color: Theme.textPrimary
                                elide: Text.ElideRight
                            }
                            Text {
                                Layout.fillWidth: true
                                text: modelData.category + " • " + modelData.key
                                font.pixelSize: ScaleMetrics.sp(8)
                                font.family: Theme.fontMono
                                color: Theme.textDim
                                elide: Text.ElideRight
                            }
                        }

                        Rectangle {
                            Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                            Layout.preferredWidth: ScaleMetrics.dp(64)
                            Layout.preferredHeight: ScaleMetrics.dp(28)
                            width: ScaleMetrics.dp(64)
                            height: ScaleMetrics.dp(28)
                            radius: ScaleMetrics.dp(4)
                            color: assigned ? Theme.bgSurface : root.macroColor
                            border.color: assigned ? Theme.borderCard : root.macroColor
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: assigned ? "✓" : "+ ADD"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(10)
                                color: assigned ? Theme.textDim : "#000000"
                            }
                        }
                    }

                    MouseArea {
                        id: touchArea
                        anchors.fill: parent
                        enabled: !assigned
                        onClicked: root.addRequested(modelData.key)
                    }
                }
            }

            VirtualKeyboard {
                Layout.fillWidth: true
                Layout.preferredHeight: ScaleMetrics.dp(165)
                visible: root.keyboardVisible
                accentColor: root.macroColor
                onKeyClicked: (key) => { searchField.text += key; }
                onBackspaceClicked: {
                    if (searchField.text.length > 0)
                        searchField.text = searchField.text.slice(0, -1);
                }
                onClearClicked: { searchField.text = ""; }
                onCloseClicked: { root.keyboardVisible = false; }
            }
        }
    }
}
