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
                text: "ASSIGNED TO PHYSICAL ENCODERS 1 - 8"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(10)
                color: Theme.textDim
            }
        }

        // 4x2 Grid of 8 Large Touch Macro Dials
        GridLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            columns: 4
            rowSpacing: ScaleMetrics.dp(10)
            columnSpacing: ScaleMetrics.dp(10)

            MacroKnob {
                Layout.fillWidth: true
                Layout.fillHeight: true
                macroIndex: 1
                macroTitle: "BRIGHTNESS"
                macroColor: Theme.tone1
                macroValue: Bridge.macro1
            }

            MacroKnob {
                Layout.fillWidth: true
                Layout.fillHeight: true
                macroIndex: 2
                macroTitle: "WARMTH"
                macroColor: Theme.tone2
                macroValue: Bridge.macro2
            }

            MacroKnob {
                Layout.fillWidth: true
                Layout.fillHeight: true
                macroIndex: 3
                macroTitle: "SUB OSC"
                macroColor: Theme.tone3
                macroValue: Bridge.macro3
            }

            MacroKnob {
                Layout.fillWidth: true
                Layout.fillHeight: true
                macroIndex: 4
                macroTitle: "AIR"
                macroColor: Theme.tone4
                macroValue: Bridge.macro4
            }

            MacroKnob {
                Layout.fillWidth: true
                Layout.fillHeight: true
                macroIndex: 5
                macroTitle: "DRIVE"
                macroColor: "#f59e0b"
                macroValue: Bridge.macro5
            }

            MacroKnob {
                Layout.fillWidth: true
                Layout.fillHeight: true
                macroIndex: 6
                macroTitle: "SPACE"
                macroColor: "#38bdf8"
                macroValue: Bridge.macro6
            }

            MacroKnob {
                Layout.fillWidth: true
                Layout.fillHeight: true
                macroIndex: 7
                macroTitle: "MOTION"
                macroColor: "#a855f7"
                macroValue: Bridge.macro7
            }

            MacroKnob {
                Layout.fillWidth: true
                Layout.fillHeight: true
                macroIndex: 8
                macroTitle: "ATTACK"
                macroColor: "#ec4899"
                macroValue: Bridge.macro8
            }
        }
    }

    // Touch Macro Knob Component
    component MacroKnob: Rectangle {
        id: knobRoot
        property int macroIndex: 1
        property string macroTitle: "MACRO"
        property color macroColor: Theme.primary
        property int macroValue: 64

        radius: ScaleMetrics.dp(8)
        color: Theme.bgApp
        border.color: knobMouse.containsPress ? knobRoot.macroColor : Theme.borderCard
        border.width: 1

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(8)
            spacing: ScaleMetrics.dp(4)

            // Title
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
            }

            // Dial Visualizer (Canvas arc)
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

                        const startAngle = 0.75 * Math.PI;
                        const endAngle = 2.25 * Math.PI;
                        const totalAngle = endAngle - startAngle;
                        const norm = knobRoot.macroValue / 127.0;
                        const currentAngle = startAngle + norm * totalAngle;

                        // Background arc track
                        ctx.beginPath();
                        ctx.arc(cx, cy, radius, startAngle, endAngle);
                        ctx.lineWidth = 6;
                        ctx.strokeStyle = "#1e293b";
                        ctx.lineCap = "round";
                        ctx.stroke();

                        // Active arc value
                        ctx.beginPath();
                        ctx.arc(cx, cy, radius, startAngle, currentAngle);
                        ctx.lineWidth = 6;
                        ctx.strokeStyle = knobRoot.macroColor;
                        ctx.lineCap = "round";
                        ctx.stroke();
                    }

                    Connections {
                        target: knobRoot
                        function onMacroValueChanged() { arcCanvas.requestPaint(); }
                    }
                }

                // Numeric Readout in center of arc
                Text {
                    anchors.centerIn: parent
                    text: knobRoot.macroValue
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(15)
                    font.family: Theme.fontMono
                    color: Theme.textPrimary
                }
            }
        }

        MouseArea {
            id: knobMouse
            anchors.fill: parent
            property real startY: 0
            property int startVal: 0

            onPressed: (mouse) => {
                startY = mouse.y;
                startVal = knobRoot.macroValue;
            }

            onPositionChanged: (mouse) => {
                if (pressed) {
                    const dy = startY - mouse.y;
                    const deltaVal = Math.round(dy * 0.8);
                    const newVal = Math.max(0, Math.min(127, startVal + deltaVal));
                    Bridge.setMacro(knobRoot.macroIndex, newVal);
                }
            }
        }
    }
}
