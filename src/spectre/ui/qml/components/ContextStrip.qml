pragma ValueTypeBehavior: Copy
import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

Rectangle {
    id: root
    height: ScaleMetrics.dp(40)
    color: Theme.bgCard
    border.color: Theme.borderCard
    border.width: 1

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: ScaleMetrics.dp(10)
        anchors.rightMargin: ScaleMetrics.dp(10)
        spacing: ScaleMetrics.dp(6)

        Repeater {
            model: 8
            delegate: EncoderCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                knobIndex: modelData + 1
            }
        }
    }

    // The page's 8 context knobs come from the bridge (CONTEXT_KNOBS in
    // bridge/controllers.py); a controller's "Context Knob N" drives the same.
    property var knobs: Bridge.contextKnobs

    component EncoderCard: Rectangle {
        id: card
        property int knobIndex: 1
        readonly property var knob: (root.knobs && root.knobs.length >= knobIndex) ? root.knobs[knobIndex - 1] : null
        readonly property bool active: knob !== null && knob.active
        readonly property string paramName: knob ? knob.title : "-"
        readonly property real normValue: knob ? knob.norm : 0.0
        readonly property string displayString: knob ? knob.text : ""
        // Tone-specific knobs ("T2 Level") take the tone colour, the rest the page accent
        readonly property color knobColor: {
            const m = /^T([1-4]) /.exec(paramName);
            return m ? Theme.toneColors[parseInt(m[1]) - 1] : Theme.pageAccent;
        }

        radius: ScaleMetrics.dp(6)
        color: Theme.bgApp
        border.color: mouseArea.containsPress ? card.knobColor : Theme.borderCard
        border.width: 1
        opacity: active ? 1.0 : 0.35

        function applyNormValue(nv: real) {
            if (card.active) Bridge.setContextKnob(card.knobIndex, Math.max(0.0, Math.min(1.0, nv)))
        }

        // Header: Knob tag + Param Name (Zero-overhead anchored positioning)
        Item {
            id: headerRow
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: ScaleMetrics.dp(3)
            height: ScaleMetrics.dp(12)

            Rectangle {
                id: tagBadge
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                width: ScaleMetrics.dp(18)
                height: ScaleMetrics.dp(12)
                radius: ScaleMetrics.dp(3)
                color: Theme.bgCardActive

                Text {
                    anchors.centerIn: parent
                    text: "K" + card.knobIndex
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: Theme.textSecondary
                }
            }

            Text {
                anchors.left: tagBadge.right
                anchors.right: parent.right
                anchors.leftMargin: ScaleMetrics.dp(4)
                anchors.verticalCenter: parent.verticalCenter
                text: card.paramName
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(9)
                color: Theme.textSecondary
                elide: Text.ElideRight
            }
        }

        // Numeric Readout Value
        Text {
            anchors.top: headerRow.bottom
            anchors.bottom: barBg.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.topMargin: ScaleMetrics.dp(0)
            anchors.bottomMargin: ScaleMetrics.dp(2)
            text: card.displayString
            font.bold: true
            font.pixelSize: ScaleMetrics.sp(8)
            font.family: Theme.fontMono
            color: Theme.textPrimary
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }

        // Progress bar / meter indicator
        Rectangle {
            id: barBg
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.leftMargin: ScaleMetrics.dp(3)
            anchors.rightMargin: ScaleMetrics.dp(3)
            anchors.bottomMargin: ScaleMetrics.dp(6)
            height: ScaleMetrics.dp(3)
            radius: ScaleMetrics.dp(2)
            color: Theme.bgRaised
            clip: true

            Rectangle {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                width: parent.width * Math.max(0.0, Math.min(1.0, card.normValue))
                radius: ScaleMetrics.dp(2)
                color: card.knobColor
            }
        }

        // Direct Touch and Drag Interaction
        MouseArea {
            id: mouseArea
            anchors.fill: parent
            enabled: card.active
            property real startX: 0
            property real startY: 0
            property real startNorm: 0

            onPressed: (mouse) => {
                startX = mouse.x;
                startY = mouse.y;
                startNorm = card.normValue;
                card.applyNormValue(mouse.x / width);
            }

            onPositionChanged: (mouse) => {
                if (pressed) {
                    const dx = mouse.x - startX;
                    const dy = startY - mouse.y;
                    if (Math.abs(dy) > Math.abs(dx) * 1.2) {
                        card.applyNormValue(startNorm + dy / ScaleMetrics.dp(70));
                    } else {
                        card.applyNormValue(mouse.x / width);
                    }
                }
            }
        }
    }
}
