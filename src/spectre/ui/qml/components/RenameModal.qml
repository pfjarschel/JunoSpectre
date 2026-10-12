pragma ValueTypeBehavior: Copy
import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

// Rename a user sound or a sequencer track. Factory ROM rows can never be renamed:
// the caller only opens this modal for file rows and synth-user slots.
Rectangle {
    id: root
    anchors.fill: parent
    visible: false
    z: 998
    color: Theme.scrim

    property string mode: "file" // "file" | "slot" | "track" | "ctlpreset"
    property int trackIdx: -1
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

    function openTrack(idx, currentName) {
        mode = "track"
        trackIdx = idx
        newName = currentName
        errorText = ""
        busy = false
        keyboardVisible = true
        visible = true
    }

    function openControlPreset(currentName) {
        mode = "ctlpreset"
        newName = currentName
        errorText = ""
        busy = false
        keyboardVisible = true
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
        border.color: Theme.pageAccent
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
                    text: root.mode === "ctlpreset" ? "SAVE CONTROLLER PRESET" : "RENAME"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(11)
                    font.letterSpacing: 1.1
                    color: Theme.textPrimary
                }
                Item { Layout.fillWidth: true }
                SpButton {
                    implicitWidth: ScaleMetrics.dp(26)
                    implicitHeight: ScaleMetrics.dp(26)
                    icon: "close"
                    fontSize: 10
                    onClicked: { if (!root.busy) root.close() }
                }
            }

            Text {
                Layout.fillWidth: true
                text: root.mode === "slot" ? ("User slot " + (501 + root.lsb * 128 + root.pc) + " on the keyboard")
                      : (root.mode === "track" ? ("Sequencer track " + (root.trackIdx + 1) + " (saved with the song)")
                      : (root.mode === "ctlpreset" ? "Current MIDI control bindings, saved on the Pi"
                                               : "Pi file (travels with the patch)"))
                font.pixelSize: ScaleMetrics.sp(8)
                color: Theme.textDim
            }

            Rectangle {
                Layout.fillWidth: true
                height: ScaleMetrics.dp(40)
                radius: ScaleMetrics.dp(4)
                color: Theme.bgApp
                border.color: nameField.activeFocus ? Theme.pageAccent : Theme.borderCard
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
                    SpButton {
                        implicitWidth: ScaleMetrics.dp(28)
                        implicitHeight: ScaleMetrics.dp(22)
                        icon: "keyboard"
                        fontSize: 12
                        checked: root.keyboardVisible
                        onClicked: { root.keyboardVisible = !root.keyboardVisible }
                    }
                }
            }

            Text {
                Layout.fillWidth: true
                visible: root.errorText !== ""
                text: root.errorText
                font.pixelSize: ScaleMetrics.sp(8)
                color: Theme.recording
                wrapMode: Text.Wrap
            }

            VirtualKeyboard {
                Layout.fillWidth: true
                Layout.preferredHeight: ScaleMetrics.dp(140)
                visible: root.keyboardVisible
                accentColor: Theme.pageAccent
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
                SpButton {
                    Layout.preferredWidth: ScaleMetrics.dp(110)
                    implicitHeight: ScaleMetrics.dp(36)
                    text: "CANCEL"
                    onClicked: { if (!root.busy) root.close() }
                }
                SpButton {
                    Layout.fillWidth: true
                    implicitHeight: ScaleMetrics.dp(36)
                    text: root.busy ? "WORKING…" : "RENAME"
                    variant: "outline"
                    checked: root.busy
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

        Timer {
            id: renameTimer
            interval: 80
            repeat: false
            running: false
            onTriggered: {
                var ok = false
                if (root.mode === "track") {
                    Bridge.seqRenameTrack(root.trackIdx, root.newName)
                    ok = true
                } else if (root.mode === "ctlpreset") {
                    root.errorText = Bridge.saveControlPreset(root.newName)
                    ok = root.errorText === ""
                } else if (root.mode === "slot") {
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
