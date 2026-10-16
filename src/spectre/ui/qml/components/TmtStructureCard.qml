pragma ValueTypeBehavior: Copy
import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

// One TMT pair (tones 1&2 or 3&4): structure type, diagram, booster and the
// two tone levels, whose job changes with the type.
Rectangle {
    id: root
    property int pair: 1                         // 1 = tones 1&2, 2 = tones 3&4
    readonly property int toneA: pair === 1 ? 1 : 3
    readonly property int toneB: toneA + 1
    readonly property color colorA: pair === 1 ? Theme.tone1 : Theme.tone3
    readonly property color colorB: pair === 1 ? Theme.tone2 : Theme.tone4

    readonly property var tmt: Bridge.tmt
    readonly property var types: Bridge.tmtStructureTypes
    readonly property int typeIndex: pair === 1 ? tmt.structure12 : tmt.structure34
    readonly property int booster: pair === 1 ? tmt.booster12 : tmt.booster34
    readonly property var info: types[typeIndex]
    readonly property bool merged: typeIndex > 0

    readonly property int levelA: pair === 1 ? Bridge.tone1Level : Bridge.tone3Level
    readonly property int levelB: pair === 1 ? Bridge.tone2Level : Bridge.tone4Level
    readonly property bool mutedA: pair === 1 ? Bridge.tone1Muted : Bridge.tone3Muted
    readonly property bool mutedB: pair === 1 ? Bridge.tone2Muted : Bridge.tone4Muted
    readonly property bool fallsBack: merged && (mutedA || mutedB)

    radius: ScaleMetrics.dp(6)
    color: Theme.bgApp
    border.color: merged ? Theme.warning : Theme.borderCard
    border.width: 1

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: ScaleMetrics.dp(8)
        spacing: ScaleMetrics.dp(6)

        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(6)
            Text {
                text: "TONES " + root.toneA + " & " + root.toneB
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(11)
                font.letterSpacing: 1.1
                color: Theme.textPrimary
            }
            Item { Layout.fillWidth: true }
            Text {
                text: "TYPE " + (root.typeIndex + 1) + " · " + root.info.name
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(9)
                color: root.merged ? Theme.warning : Theme.textSecondary
            }
        }

        // Type picker
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(4)
            Repeater {
                model: 10
                delegate: SpButton {
                    required property int index
                    readonly property bool sel: root.typeIndex === index
                    Layout.fillWidth: true
                    implicitHeight: ScaleMetrics.dp(30)
                    text: (index + 1).toString()
                    fontSize: 11
                    mono: true
                    accent: index > 0 ? Theme.warning : Theme.pageAccent
                    checked: sel
                    onClicked: Bridge.setTmtStructure(root.pair, index)
                }
            }
        }

        Text {
            Layout.fillWidth: true
            Layout.preferredHeight: ScaleMetrics.dp(26)
            text: root.info.text
            wrapMode: Text.WordWrap
            font.pixelSize: ScaleMetrics.sp(9)
            color: Theme.textSecondary
            verticalAlignment: Text.AlignTop
        }

        TmtDiagram {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: ScaleMetrics.dp(80)
            structure: root.info
            toneA: root.toneA
            colorA: root.colorA
            colorB: root.colorB
            dimmed: root.fallsBack
            boosterText: root.info.booster ? Bridge.tmtBoosterLabels[root.booster] : ""
        }

        Text {
            Layout.fillWidth: true
            visible: root.fallsBack
            text: "Tone " + (root.mutedA ? root.toneA : root.toneB) + " is off, so the Juno plays this pair as type 1."
            wrapMode: Text.WordWrap
            font.pixelSize: ScaleMetrics.sp(9)
            font.bold: true
            color: Theme.warning
        }

        // Booster
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(4)
            opacity: root.info.booster ? 1.0 : 0.4
            Text {
                Layout.preferredWidth: ScaleMetrics.dp(64)
                text: "BOOSTER"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(8)
                color: root.info.booster ? Theme.warning : Theme.textDim
            }
            Repeater {
                model: Bridge.tmtBoosterLabels
                delegate: SpButton {
                    required property int index
                    required property string modelData
                    readonly property bool sel: root.booster === index
                    Layout.fillWidth: true
                    implicitHeight: ScaleMetrics.dp(26)
                    text: modelData
                    fontSize: 8
                    accent: index > 0 ? Theme.warning : Theme.pageAccent
                    checked: sel
                    onClicked: Bridge.setTmtBooster(root.pair, index)
                }
            }
        }

        // Tone levels: the first tone's TVA becomes the effect amount
        SpSlider {
            Layout.fillWidth: true
            label: "TONE " + root.toneA + " LEVEL · " + root.info.role
            valueText: root.levelA.toString()
            norm: root.levelA / 127.0
            accent: root.colorA
            enabled: !root.mutedA
            onMoved: (norm) => Bridge.setToneLevel(root.toneA, Math.round(norm * 127))
        }
        SpSlider {
            Layout.fillWidth: true
            label: "TONE " + root.toneB + " LEVEL · " + (root.merged ? "PAIR OUTPUT" : "VOLUME")
            valueText: root.levelB.toString()
            norm: root.levelB / 127.0
            accent: root.colorB
            enabled: !root.mutedB
            onMoved: (norm) => Bridge.setToneLevel(root.toneB, Math.round(norm * 127))
        }
    }
}
