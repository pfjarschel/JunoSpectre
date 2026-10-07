import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

// Rename a user sound. Factory ROM rows can never be renamed:
// the caller only opens this modal for file rows and synth-user slots.
Rectangle {
    id: root
    anchors.fill: parent
    visible: false
    z: 998
    color: "#e60a0c10"

    property string mode: "file" // "file" | "slot"
    property string path: ""
    property int msb: -1
    property int lsb: -1
    property int pc: -1
    property string newName: ""
    property string errorText: ""
    property bool busy: false
    property bool keyboardVisible: false

    function openFile(filePath, currentName) {
        mode = "file"
        path = filePath
        newName = currentName
        errorText = ""
        busy = false
        visible = true
    }

    function openSlot(slotMsb, slotLsb, slotPc, currentName) {
        mode = "slot"
        msb = slotMsb
        lsb = slotLsb
        pc = slotPc
        newName = currentName
        errorText = ""
        busy = false
        visible = true
    }

    function close() {
        visible = false
        keyboardVisible = false
    }

    MouseArea {
        anchors.fill: parent
        onClicked: { if (!root.busy) root.close() }
    }

    Rectangle {
        width: Math.min(parent.width - ScaleMetrics.dp(32), ScaleMetrics.dp(480))
        height: ScaleMetrics.dp(380)
        anchors.centerIn: parent
        radius: ScaleMetrics.dp(8)
        color: Theme.bgCard
        border.color: Theme.tone2
        border.width: 1

        MouseArea { anchors.fill: parent }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(14)
            spacing: ScaleMetrics.dp(10)

            RowLayout {
                Layout.fillWidth: true
                spacing: ScaleMetrics.dp(8)
                Text {
                    text: "✏ RENAME"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(11)
                    font.letterSpacing: 1.1
                    color: Theme.textPrimary
                }
                Item { Layout.fillWidth: true }
                Rectangle {
                    width: ScaleMetrics.dp(26); height: ScaleMetrics.dp(26)
                    radius: ScaleMetrics.dp(4)
                    color: closeArea.pressed ? Theme.bgCardActive : "#10141d"
                    border.color: Theme.borderCard; border.width: 1
                    Text { anchors.centerIn: parent; text: "✕"; font.bold: true; font.pixelSize: ScaleMetrics.sp(10); color: Theme.textSecondary }
                    MouseArea { id: closeArea; anchors.fill: parent; onClicked: { if (!root.busy) root.close() } }
                }
            }

            Text {
                Layout.fillWidth: true
                text: root.mode === "slot" ? ("User slot " + (501 + root.lsb * 128 + root.pc) + " on the keyboard") : "Pi file (travels with the patch)"
                font.pixelSize: ScaleMetrics.sp(8)
                color: Theme.textDim
            }

            Rectangle {
                Layout.fillWidth: true
                height: ScaleMetrics.dp(40)
                radius: ScaleMetrics.dp(4)
                color: Theme.bgApp
                border.color: nameField.activeFocus ? Theme.tone2 : Theme.borderCard
                border.width: 1
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: ScaleMetrics.dp(8)
                    anchors.rightMargin: ScaleMetrics.dp(8)
                    spacing: ScaleMetrics.dp(6)
                    TextInput {
                        id: nameField
                        Layout.fillWidth: true
                        text: root.newName
                        maximumLength: 12
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(14)
                        color: Theme.textPrimary
                        clip: true
                        onTextEdited: { root.newName = text }
                        onActiveFocusChanged: { if (activeFocus) root.keyboardVisible = true }
                    }
                    Text {
                        text: (root.newName || "").length + "/12"
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Theme.textDim
                    }
                    Rectangle {
                        width: ScaleMetrics.dp(28); height: ScaleMetrics.dp(22)
                        radius: ScaleMetrics.dp(4)
                        color: root.keyboardVisible ? Theme.tone2 : Theme.bgSurface
                        border.color: Theme.borderCard; border.width: 1
                        Text { anchors.centerIn: parent; text: "⌨"; font.pixelSize: ScaleMetrics.sp(12); color: Theme.textSecondary }
                        MouseArea { anchors.fill: parent; onClicked: { root.keyboardVisible = !root.keyboardVisible } }
                    }
                }
            }

            Text {
                Layout.fillWidth: true
                visible: root.errorText !== ""
                text: root.errorText
                font.pixelSize: ScaleMetrics.sp(8)
                color: "#ef4444"
                wrapMode: Text.Wrap
            }

            VirtualKeyboard {
                Layout.fillWidth: true
                Layout.preferredHeight: ScaleMetrics.dp(140)
                visible: root.keyboardVisible
                accentColor: Theme.tone2
                onKeyClicked: (key) => {
                    if (nameField.text.length < 12) {
                        nameField.text += key.toUpperCase();
                        root.newName = nameField.text;
                    }
                }
                onBackspaceClicked: {
                    if (nameField.text.length > 0) {
                        nameField.text = nameField.text.slice(0, -1);
                        root.newName = nameField.text;
                    }
                }
                onClearClicked: { nameField.text = ""; root.newName = "" }
                onCloseClicked: { root.keyboardVisible = false }
            }

            Item { Layout.fillHeight: true }

            RowLayout {
                Layout.fillWidth: true
                spacing: ScaleMetrics.dp(8)
                Rectangle {
                    Layout.preferredWidth: ScaleMetrics.dp(110)
                    height: ScaleMetrics.dp(36)
                    radius: ScaleMetrics.dp(4)
                    color: cancelArea.pressed ? Theme.bgCardActive : "#10141d"
                    border.color: Theme.borderCard; border.width: 1
                    Text { anchors.centerIn: parent; text: "CANCEL"; font.bold: true; font.pixelSize: ScaleMetrics.sp(9); color: Theme.textSecondary }
                    MouseArea { id: cancelArea; anchors.fill: parent; onClicked: { if (!root.busy) root.close() } }
                }
                Rectangle {
                    Layout.fillWidth: true
                    height: ScaleMetrics.dp(36)
                    radius: ScaleMetrics.dp(4)
                    color: root.busy ? Theme.bgSurface : "#1c2433"
                    border.color: Theme.tone2; border.width: 1
                    Text { anchors.centerIn: parent; text: root.busy ? "WORKING…" : "RENAME"; font.bold: true; font.pixelSize: ScaleMetrics.sp(9); color: Theme.tone2 }
                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            if (root.busy) return
                            if ((root.newName || "").trim() === "") { root.errorText = "Give it a name."; return }
                            root.busy = true
                            root.errorText = ""
                            renameTimer.start()
                        }
                    }
                }
            }
        }

        Timer {
            id: renameTimer
            interval: 80
            repeat: false
            running: false
            onTriggered: {
                var ok = false
                if (root.mode === "slot") {
                    ok = Bridge.renameUserSlot(root.msb, root.lsb, root.pc, root.newName)
                    if (!ok) root.errorText = "Rename failed (synth unreachable?)."
                } else {
                    ok = Bridge.renameLibraryFile(root.path, root.newName)
                    if (!ok) root.errorText = "Rename failed."
                }
                root.busy = false
                if (ok) root.close()
            }
        }
    }
}
