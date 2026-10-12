pragma ValueTypeBehavior: Copy
import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

// Full-page MSEG Envelope Editor: envelope picker (TVF / TVA / PITCH),
// shared multi-segment canvas + preset bar, and the pitch dynamics card.
// Also embedded by the quick-edit EnvEditOverlay modal.
Rectangle {
    id: root
    color: Theme.bgCard
    radius: ScaleMetrics.dp(8)
    border.color: Theme.borderCard
    border.width: 1

    property string activeEnv: "TVF"

    // Pitch envelope bindings (dynamics card + external/test contracts)
    property int envDepth: Bridge.pitchEnvDepth
    property int velSens: Bridge.pitchEnvVelSens
    property int timeKeyfollow: Bridge.pitchEnvTimeKeyfollow
    property int t1VelSens: Bridge.pitchEnvT1VelSens
    property int t4VelSens: Bridge.pitchEnvT4VelSens
    property int t1: Bridge.pitchEnvT1
    property int t2: Bridge.pitchEnvT2
    property int t3: Bridge.pitchEnvT3
    property int t4: Bridge.pitchEnvT4
    property int l0: Bridge.pitchEnvL0
    property int l1: Bridge.pitchEnvL1
    property int l2: Bridge.pitchEnvL2
    property int l3: Bridge.pitchEnvL3
    property int l4: Bridge.pitchEnvL4

    property alias draggedPoint: envMseg.draggedPoint

    function refresh() {
        envMseg.refresh();
    }

    function chipAccent(env) {
        return Theme.pageAccent;
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: ScaleMetrics.dp(10)
        spacing: ScaleMetrics.dp(8)

        // Envelope selector chips
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(6)

            Text {
                text: "ENVELOPE:"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(9)
                font.letterSpacing: 1.0
                color: Theme.textDim
            }

            Repeater {
                model: ["TVF", "TVA", "PITCH"]
                delegate: SpButton {
                    Layout.preferredWidth: label.implicitWidth + ScaleMetrics.dp(18)
                    Layout.preferredHeight: ScaleMetrics.dp(26)
                    text: modelData
                    accent: root.chipAccent(modelData)
                    checked: root.activeEnv === modelData
                    onClicked: {
                        root.activeEnv = modelData;
                        root.refresh();
                    }
                }
            }

            Item { Layout.fillWidth: true }

            Text {
                text: "T1..T4 / LEVELS • DRAG NODES OR USE PRESETS"
                font.pixelSize: ScaleMetrics.sp(8)
                font.letterSpacing: 1.0
                color: Theme.textDim
            }
        }

        // Shared interactive MSEG editor (presets, canvas, T/L matrix)
        EnvMsegView {
            id: envMseg
            Layout.fillWidth: true
            Layout.fillHeight: true
            env: root.activeEnv
            color: "transparent"
            border.width: 0
        }

    }
}
