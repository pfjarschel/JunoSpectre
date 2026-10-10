pragma ValueTypeBehavior: Copy
import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

// Global modal: quick-edit envelope overlay with envelope picker
// (TVF / TVA / PITCH). Opened from the envelope thumbnails on the PCM page
// and the Sculptor panel, or directly via Bridge.openEnvOverlay(env).
Rectangle {
    id: root
    anchors.fill: parent
    visible: false
    z: 998
    color: "#e60a0c10"

    function open(env) {
        var e = (env === undefined || env === null) ? "TVF" : String(env).toUpperCase();
        envEditor.activeEnv = (e === "TVA" || e === "PITCH") ? e : "TVF";
        visible = true;
        envEditor.refresh();
    }

    function close() {
        visible = false;
    }

    MouseArea {
        anchors.fill: parent
        onClicked: root.close()
    }

    Rectangle {
        id: card
        width: Math.min(parent.width - ScaleMetrics.dp(32), ScaleMetrics.dp(900))
        height: Math.min(parent.height - ScaleMetrics.dp(28), ScaleMetrics.dp(520))
        anchors.centerIn: parent
        radius: ScaleMetrics.dp(10)
        color: Theme.bgCard
        border.color: Theme.borderActive
        border.width: 1

        MouseArea {
            anchors.fill: parent
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(12)
            spacing: ScaleMetrics.dp(8)

            RowLayout {
                Layout.fillWidth: true
                spacing: ScaleMetrics.dp(8)

                Text {
                    text: "ENVELOPE EDITOR"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(13)
                    font.letterSpacing: 1.2
                    color: Theme.textPrimary
                }

                Item { Layout.fillWidth: true }

                Rectangle {
                    width: ScaleMetrics.dp(36)
                    height: ScaleMetrics.dp(26)
                    radius: ScaleMetrics.dp(6)
                    color: closeArea.pressed ? "#3f1a1a" : Theme.bgApp
                    border.color: Theme.borderCard
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: "✕"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(13)
                        color: closeArea.pressed ? Theme.recording : Theme.textSecondary
                    }
                    MouseArea {
                        id: closeArea
                        anchors.fill: parent
                        onClicked: root.close()
                    }
                }
            }

            EnvEditorView {
                id: envEditor
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: "transparent"
                border.width: 0
            }
        }
    }
}
