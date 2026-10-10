pragma ValueTypeBehavior: Copy
import QtQuick
import QtQuick.Layouts
import ".."

Rectangle {
    id: root

    property color accentColor: Theme.tone1
    // When true, a SHIFT key toggles A-Z / a-z (needed for Wi-Fi passwords).
    // Existing callers leave this false and keep the legacy uppercase layout.
    property bool allowLower: false
    property bool isLower: true
    // When true, an extra row of password-friendly symbols is shown.
    property bool allowSymbols: false
    signal keyClicked(string key)
    signal backspaceClicked()
    signal clearClicked()
    signal closeClicked()

    color: Theme.bgSurface
    radius: ScaleMetrics.dp(8)
    border.color: Theme.borderCard
    border.width: 1

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: ScaleMetrics.dp(6)
        spacing: ScaleMetrics.dp(3)

        // Row 1: Numbers (0-9), Dash (-), and Backspace (⌫)
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: ScaleMetrics.dp(3)

            Repeater {
                model: ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-"]
                KeyButton {
                    text: modelData
                    onClicked: root.keyClicked(modelData)
                }
            }

            // Backspace Key with auto-repeat
            Rectangle {
                id: bsKey
                implicitWidth: ScaleMetrics.dp(60)
                implicitHeight: ScaleMetrics.dp(26)
                Layout.fillWidth: true
                Layout.preferredWidth: ScaleMetrics.dp(60)
                Layout.fillHeight: true
                radius: ScaleMetrics.dp(4)
                color: bsArea.pressed ? Qt.rgba(0.8, 0.2, 0.2, 0.3) : Theme.bgApp
                border.color: bsArea.pressed ? Theme.recording : Theme.borderCard
                border.width: 1

                Text {
                    anchors.centerIn: parent
                    text: "⌫"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(13)
                    color: Theme.recording
                }

                Timer {
                    id: bsRepeatTimer
                    interval: 70
                    repeat: true
                    running: false
                    onTriggered: root.backspaceClicked()
                }

                Timer {
                    id: bsInitialDelay
                    interval: 350
                    repeat: false
                    running: false
                    onTriggered: bsRepeatTimer.start()
                }

                MouseArea {
                    id: bsArea
                    anchors.fill: parent
                    onPressed: {
                        root.backspaceClicked();
                        bsInitialDelay.start();
                    }
                    onReleased: {
                        bsInitialDelay.stop();
                        bsRepeatTimer.stop();
                    }
                    onCanceled: {
                        bsInitialDelay.stop();
                        bsRepeatTimer.stop();
                    }
                }
            }
        }

        // Row 2: QWERTYUIOP (case follows SHIFT when allowLower)
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: ScaleMetrics.dp(3)

            Repeater {
                model: (root.allowLower && root.isLower)
                    ? ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p"]
                    : ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"]
                KeyButton {
                    text: modelData
                    onClicked: root.keyClicked(modelData)
                }
            }
        }

        // Row 3: ASDFGHJKL (indented with side spacers)
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: ScaleMetrics.dp(3)

            Item {
                implicitWidth: ScaleMetrics.dp(16)
                Layout.preferredWidth: ScaleMetrics.dp(16)
                Layout.fillHeight: true
            }

            Repeater {
                model: (root.allowLower && root.isLower)
                    ? ["a", "s", "d", "f", "g", "h", "j", "k", "l"]
                    : ["A", "S", "D", "F", "G", "H", "J", "K", "L"]
                KeyButton {
                    text: modelData
                    onClicked: root.keyClicked(modelData)
                }
            }

            Item {
                implicitWidth: ScaleMetrics.dp(16)
                Layout.preferredWidth: ScaleMetrics.dp(16)
                Layout.fillHeight: true
            }
        }

        // Row 4: SHIFT + ZXCVBNM (SHIFT only when allowLower)
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: ScaleMetrics.dp(3)

            KeyButton {
                visible: root.allowLower
                implicitWidth: ScaleMetrics.dp(72)
                Layout.preferredWidth: ScaleMetrics.dp(72)
                text: root.isLower ? "⇧ abc" : "⇧ ABC"
                textColor: root.isLower ? Theme.textSecondary : root.accentColor
                onClicked: root.isLower = !root.isLower
            }
            Item {
                visible: !root.allowLower
                implicitWidth: ScaleMetrics.dp(36)
                Layout.preferredWidth: ScaleMetrics.dp(36)
                Layout.fillHeight: true
            }

            Repeater {
                model: (root.allowLower && root.isLower)
                    ? ["z", "x", "c", "v", "b", "n", "m"]
                    : ["Z", "X", "C", "V", "B", "N", "M"]
                KeyButton {
                    text: modelData
                    onClicked: root.keyClicked(modelData)
                }
            }

            Item {
                implicitWidth: ScaleMetrics.dp(36)
                Layout.preferredWidth: ScaleMetrics.dp(36)
                Layout.fillHeight: true
            }
        }

        // Row 4b: password symbols (Wi-Fi passphrases etc.)
        RowLayout {
            visible: root.allowSymbols
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: ScaleMetrics.dp(3)

            Repeater {
                model: ["_", ".", "-", "@", "!", "#", "$", "%", "&", "*", "/", ":"]
                KeyButton {
                    text: modelData
                    onClicked: root.keyClicked(modelData)
                }
            }
        }

        // Row 5: Action & Utility Controls (CLR, SPACE, HIDE)
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: ScaleMetrics.dp(3)

            // Clear Button
            KeyButton {
                implicitWidth: ScaleMetrics.dp(110)
                Layout.preferredWidth: ScaleMetrics.dp(110)
                text: "CLEAR"
                textColor: Theme.warning
                onClicked: root.clearClicked()
            }

            // Space Bar
            KeyButton {
                implicitWidth: ScaleMetrics.dp(400)
                Layout.preferredWidth: ScaleMetrics.dp(400)
                text: "SPACE"
                textColor: Theme.textSecondary
                onClicked: root.keyClicked(" ")
            }

            // Hide Keyboard Button
            KeyButton {
                implicitWidth: ScaleMetrics.dp(110)
                Layout.preferredWidth: ScaleMetrics.dp(110)
                text: "HIDE ⌨"
                textColor: root.accentColor
                onClicked: root.closeClicked()
            }
        }
    }

    // Reusable single key button
    component KeyButton: Rectangle {
        id: btn
        property alias text: label.text
        property color textColor: Theme.textPrimary
        signal clicked()

        implicitWidth: ScaleMetrics.dp(42)
        implicitHeight: ScaleMetrics.dp(26)
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.preferredWidth: implicitWidth

        radius: ScaleMetrics.dp(4)
        color: mArea.pressed ? Theme.bgCardActive : Theme.bgApp
        border.color: mArea.pressed ? root.accentColor : Theme.borderCard
        border.width: 1

        Text {
            id: label
            anchors.centerIn: parent
            font.bold: true
            font.pixelSize: ScaleMetrics.sp(12)
            font.family: Theme.fontSans
            color: btn.textColor
        }

        MouseArea {
            id: mArea
            anchors.fill: parent
            onClicked: btn.clicked()
        }
    }
}
