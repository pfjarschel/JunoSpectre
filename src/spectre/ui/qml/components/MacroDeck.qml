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

    readonly property var knobColors: [Theme.tone1, Theme.tone2, Theme.tone3, Theme.tone4,
        "#f59e0b", "#38bdf8", "#a855f7", "#ec4899"]

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: ScaleMetrics.dp(12)
        spacing: ScaleMetrics.dp(10)

        // Header Title
        RowLayout {
            Layout.fillWidth: true
            Text {
                text: "MACRO PLAY DECK"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(13)
                font.letterSpacing: 1.2
                color: Theme.textSecondary
            }
            Item { Layout.fillWidth: true }
            Text {
                text: "RELATIVE • EDIT TO CUSTOMIZE • DOUBLE-TAP KNOB TO CENTER"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(9)
                color: Theme.textDim
            }
        }

        // 4x2 Grid of 8 Bipolar Touch Macro Dials
        GridLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            columns: 4
            rowSpacing: ScaleMetrics.dp(10)
            columnSpacing: ScaleMetrics.dp(10)

            Repeater {
                model: 8
                delegate: MacroKnob {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    macroIndex: modelData + 1
                    macroTitle: (Bridge.macroNames && Bridge.macroNames.length > modelData)
                                ? Bridge.macroNames[modelData] : ("M" + (modelData + 1))
                    macroColor: root.knobColors[modelData]
                    macroValue01: (Bridge.macroValues && Bridge.macroValues.length > modelData)
                                  ? Bridge.macroValues[modelData] : 0.0
                    linkCount: (Bridge.macroLinkCounts && Bridge.macroLinkCounts.length > modelData)
                               ? Bridge.macroLinkCounts[modelData] : 0
                }
            }
        }
    }

    // Bipolar Relative Macro Knob Component (value in [-1, 1], 0 = neutral)
    component MacroKnob: Rectangle {
        id: knobRoot
        property int macroIndex: 1
        property string macroTitle: "MACRO"
        property color macroColor: Theme.primary
        property real macroValue01: 0.0
        property int linkCount: 0

        radius: ScaleMetrics.dp(8)
        color: Theme.bgApp
        border.color: knobMouse.containsPress ? knobRoot.macroColor : Theme.borderCard
        border.width: 1

        // Drag / double-tap layer (declared first so the title edit tap sits above it)
        MouseArea {
            id: knobMouse
            anchors.fill: parent
            property real startY: 0
            property real startVal: 0

            onPressed: (mouse) => {
                startY = mouse.y;
                startVal = knobRoot.macroValue01;
            }

            onPositionChanged: (mouse) => {
                if (pressed) {
                    const dy = startY - mouse.y;
                    const newVal = Math.max(-1.0, Math.min(1.0, startVal + dy / ScaleMetrics.dp(70)));
                    Bridge.setMacro(knobRoot.macroIndex, newVal);
                }
            }

            onDoubleClicked: {
                Bridge.setMacro(knobRoot.macroIndex, 0.0);
            }
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(8)
            spacing: ScaleMetrics.dp(4)

            // Title (tap to edit assignments + rename)
            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: "M" + knobRoot.macroIndex
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(10)
                    color: knobRoot.macroColor
                }
                Text {
                    Layout.fillWidth: true
                    text: knobRoot.macroTitle
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(10)
                    color: Theme.textSecondary
                    elide: Text.ElideRight
                }
                Rectangle {
                    visible: knobRoot.linkCount > 1
                    width: ScaleMetrics.dp(30)
                    height: ScaleMetrics.dp(16)
                    radius: ScaleMetrics.dp(8)
                    color: Theme.bgCardActive
                    Text {
                        anchors.centerIn: parent
                        text: knobRoot.linkCount + "×"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(9)
                        color: knobRoot.macroColor
                    }
                }
                Rectangle {
                    width: ScaleMetrics.dp(38)
                    height: ScaleMetrics.dp(18)
                    radius: ScaleMetrics.dp(4)
                    color: editArea.pressed ? Theme.bgCardActive : Theme.bgSurface
                    border.color: knobRoot.macroColor
                    border.width: 1
                    Text {
                        anchors.centerIn: parent
                        text: "EDIT"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: knobRoot.macroColor
                    }
                    MouseArea {
                        id: editArea
                        anchors.fill: parent
                        onClicked: Bridge.openMacroAssign(knobRoot.macroIndex)
                    }
                }
            }

            // Dial Visualizer (center-out bipolar arc)
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                Canvas {
                    id: arcCanvas
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(4)

                    onPaint: {
                        const ctx = getContext("2d");
                        ctx.reset();
                        const cx = width / 2;
                        const cy = height / 2;
                        const radius = Math.min(cx, cy) - 6;
                        if (radius <= 0) {
                            return;
                        }

                        const startAngle = 0.75 * Math.PI;
                        const endAngle = 2.25 * Math.PI;
                        const totalAngle = endAngle - startAngle;
                        const centerAngle = startAngle + totalAngle / 2;
                        const v = Math.max(-1.0, Math.min(1.0, knobRoot.macroValue01));
                        const currentAngle = centerAngle + v * (totalAngle / 2);

                        // Background arc track
                        ctx.beginPath();
                        ctx.arc(cx, cy, radius, startAngle, endAngle);
                        ctx.lineWidth = 6;
                        ctx.strokeStyle = "#1e293b";
                        ctx.lineCap = "round";
                        ctx.stroke();

                        // Center tick
                        ctx.beginPath();
                        ctx.arc(cx, cy, radius, centerAngle - 0.02, centerAngle + 0.02);
                        ctx.lineWidth = 8;
                        ctx.strokeStyle = "#475569";
                        ctx.lineCap = "round";
                        ctx.stroke();

                        // Active center-out arc
                        if (Math.abs(v) > 0.005) {
                            ctx.beginPath();
                            if (v >= 0) {
                                ctx.arc(cx, cy, radius, centerAngle, currentAngle);
                            } else {
                                ctx.arc(cx, cy, radius, currentAngle, centerAngle);
                            }
                            ctx.lineWidth = 6;
                            ctx.strokeStyle = knobRoot.macroColor;
                            ctx.lineCap = "round";
                            ctx.stroke();
                        }
                    }

                    Connections {
                        target: knobRoot
                        function onMacroValue01Changed() { arcCanvas.requestPaint(); }
                    }
                    Component.onCompleted: arcCanvas.requestPaint()
                }

                // Percent readout in center of arc
                Text {
                    anchors.centerIn: parent
                    text: {
                        const pct = Math.round(knobRoot.macroValue01 * 100);
                        return (pct > 0 ? "+" : "") + pct;
                    }
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(14)
                    font.family: Theme.fontMono
                    color: Math.abs(knobRoot.macroValue01) < 0.005 ? Theme.textDim : Theme.textPrimary
                }
            }
        }
    }
}
