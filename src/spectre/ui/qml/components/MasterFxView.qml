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

    property int chorusType: 1 // 1: Chorus 1
    property int chorusRate: 40
    property int chorusDepth: 65
    property int chorusFeedback: 20
    property int chorusLevel: 80

    property int reverbType: 4 // 4: Hall 1
    property int reverbTime: 70
    property int reverbDamp: 45
    property int reverbPreDelay: 15
    property int reverbLevel: 60

    property int eqLowGain: 2 // dB (-15..+15)
    property int eqMidGain: -3
    property int eqMidFreq: 1200 // Hz
    property int eqHighGain: 4

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: ScaleMetrics.dp(10)
        spacing: ScaleMetrics.dp(8)

        // Header
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(8)

            Rectangle {
                width: ScaleMetrics.dp(8); height: ScaleMetrics.dp(8); radius: 4
                color: "#a855f7"
            }
            Text {
                text: "MASTER FX (CHORUS, REVERB & 3-BAND MASTER EQ)"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(12)
                font.letterSpacing: 1.2
                color: Theme.textPrimary
            }
            Item { Layout.fillWidth: true }
            Text {
                text: "GLOBAL MASTER OUTPUT BUS"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(9)
                color: Theme.textDim
            }
        }

        // 3 Cards: Chorus, Reverb, 3-Band EQ
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: ScaleMetrics.dp(8)

            // Card 1: Master Chorus (~300dp)
            Rectangle {
                Layout.preferredWidth: ScaleMetrics.dp(300)
                Layout.fillHeight: true
                radius: ScaleMetrics.dp(6)
                color: Theme.bgApp
                border.color: Theme.borderCard
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(8)
                    spacing: ScaleMetrics.dp(6)

                    RowLayout {
                        Layout.fillWidth: true
                        Rectangle { width: 6; height: 6; radius: 3; color: "#38bdf8" }
                        Text { text: "MASTER CHORUS"; font.bold: true; font.pixelSize: ScaleMetrics.sp(10); color: "#38bdf8" }
                    }

                    // Chorus Type Selector
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Repeater {
                            model: ["OFF", "CHO 1", "CHO 2", "CHO 3", "FB-CHO", "FLANG"]
                            delegate: Rectangle {
                                Layout.fillWidth: true
                                height: ScaleMetrics.dp(20)
                                radius: 3
                                color: root.chorusType === index ? Theme.bgCardActive : "#10141d"
                                border.color: root.chorusType === index ? "#38bdf8" : Theme.borderCard
                                border.width: 1
                                Text {
                                    anchors.centerIn: parent
                                    text: modelData
                                    font.bold: root.chorusType === index
                                    font.pixelSize: ScaleMetrics.sp(7)
                                    color: root.chorusType === index ? "#38bdf8" : Theme.textDim
                                }
                                MouseArea { anchors.fill: parent; onClicked: root.chorusType = index }
                            }
                        }
                    }

                    FxSlider { Layout.fillWidth: true; label: "RATE"; val: root.chorusRate; accent: "#38bdf8"; onMoved: (v) => root.chorusRate = v }
                    FxSlider { Layout.fillWidth: true; label: "DEPTH"; val: root.chorusDepth; accent: "#38bdf8"; onMoved: (v) => root.chorusDepth = v }
                    FxSlider { Layout.fillWidth: true; label: "FEEDBACK"; val: root.chorusFeedback; accent: "#38bdf8"; onMoved: (v) => root.chorusFeedback = v }
                    FxSlider { Layout.fillWidth: true; label: "LEVEL"; val: root.chorusLevel; accent: "#38bdf8"; onMoved: (v) => root.chorusLevel = v }
                    Item { Layout.fillHeight: true }
                }
            }

            // Card 2: Master Reverb (~300dp)
            Rectangle {
                Layout.preferredWidth: ScaleMetrics.dp(300)
                Layout.fillHeight: true
                radius: ScaleMetrics.dp(6)
                color: Theme.bgApp
                border.color: Theme.borderCard
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(8)
                    spacing: ScaleMetrics.dp(6)

                    RowLayout {
                        Layout.fillWidth: true
                        Rectangle { width: 6; height: 6; radius: 3; color: "#a855f7" }
                        Text { text: "MASTER REVERB"; font.bold: true; font.pixelSize: ScaleMetrics.sp(10); color: "#a855f7" }
                    }

                    // Reverb Type Selector
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Repeater {
                            model: ["OFF", "ROOM 1", "ROOM 2", "HALL 1", "HALL 2", "PLATE"]
                            delegate: Rectangle {
                                Layout.fillWidth: true
                                height: ScaleMetrics.dp(20)
                                radius: 3
                                color: root.reverbType === index ? Theme.bgCardActive : "#10141d"
                                border.color: root.reverbType === index ? "#a855f7" : Theme.borderCard
                                border.width: 1
                                Text {
                                    anchors.centerIn: parent
                                    text: modelData
                                    font.bold: root.reverbType === index
                                    font.pixelSize: ScaleMetrics.sp(7)
                                    color: root.reverbType === index ? "#a855f7" : Theme.textDim
                                }
                                MouseArea { anchors.fill: parent; onClicked: root.reverbType = index }
                            }
                        }
                    }

                    FxSlider { Layout.fillWidth: true; label: "TIME"; val: root.reverbTime; accent: "#a855f7"; onMoved: (v) => root.reverbTime = v }
                    FxSlider { Layout.fillWidth: true; label: "HF DAMP"; val: root.reverbDamp; accent: "#a855f7"; onMoved: (v) => root.reverbDamp = v }
                    FxSlider { Layout.fillWidth: true; label: "PRE-DELAY"; val: root.reverbPreDelay; accent: "#a855f7"; onMoved: (v) => root.reverbPreDelay = v }
                    FxSlider { Layout.fillWidth: true; label: "LEVEL"; val: root.reverbLevel; accent: "#a855f7"; onMoved: (v) => root.reverbLevel = v }
                    Item { Layout.fillHeight: true }
                }
            }

            // Card 3: 3-Band Master Parametric EQ
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: ScaleMetrics.dp(6)
                color: Theme.bgApp
                border.color: Theme.borderCard
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(8)
                    spacing: ScaleMetrics.dp(6)

                    RowLayout {
                        Layout.fillWidth: true
                        Rectangle { width: 6; height: 6; radius: 3; color: "#10b981" }
                        Text { text: "3-BAND MASTER EQ"; font.bold: true; font.pixelSize: ScaleMetrics.sp(10); color: "#10b981" }
                    }

                    // Interactive EQ Canvas
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: ScaleMetrics.dp(80)
                        radius: 4
                        color: "#080b11"
                        border.color: Theme.borderCard
                        border.width: 1
                        clip: true

                        Canvas {
                            id: eqCanvas
                            anchors.fill: parent
                            anchors.margins: 4

                            onPaint: {
                                var ctx = getContext("2d");
                                ctx.reset();
                                var w = width, h = height;
                                var midY = h * 0.5;

                                ctx.strokeStyle = "#1e293b";
                                ctx.lineWidth = 1;
                                ctx.beginPath();
                                ctx.moveTo(0, midY); ctx.lineTo(w, midY);
                                ctx.stroke();

                                // Curve
                                ctx.strokeStyle = "#10b981";
                                ctx.lineWidth = 2;
                                ctx.beginPath();
                                for (var x = 0; x <= w; x += 4) {
                                    var normX = x / w;
                                    var dy = 0;
                                    // Low shelf (left 30%)
                                    if (normX < 0.35) dy += (root.eqLowGain / 15.0) * (midY * 0.7) * (1.0 - normX / 0.35);
                                    // Mid bell (around 50%)
                                    var midDist = Math.abs(normX - 0.5);
                                    if (midDist < 0.3) dy += (root.eqMidGain / 15.0) * (midY * 0.7) * Math.cos(midDist / 0.3 * Math.PI * 0.5);
                                    // High shelf (right 35%)
                                    if (normX > 0.65) dy += (root.eqHighGain / 15.0) * (midY * 0.7) * ((normX - 0.65) / 0.35);

                                    var y = midY - dy;
                                    if (x === 0) ctx.moveTo(x, y);
                                    else ctx.lineTo(x, y);
                                }
                                ctx.stroke();
                            }
                        }
                    }

                    // EQ Gain Controls
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        EqKnob {
                            Layout.fillWidth: true
                            label: "LOW"
                            gainVal: root.eqLowGain
                            accent: "#10b981"
                            onMoved: (g) => { root.eqLowGain = g; eqCanvas.requestPaint(); }
                        }

                        EqKnob {
                            Layout.fillWidth: true
                            label: "MID"
                            gainVal: root.eqMidGain
                            accent: "#10b981"
                            onMoved: (g) => { root.eqMidGain = g; eqCanvas.requestPaint(); }
                        }

                        EqKnob {
                            Layout.fillWidth: true
                            label: "HIGH"
                            gainVal: root.eqHighGain
                            accent: "#10b981"
                            onMoved: (g) => { root.eqHighGain = g; eqCanvas.requestPaint(); }
                        }
                    }
                    Item { Layout.fillHeight: true }
                }
            }
        }
    }

    component FxSlider: Rectangle {
        id: fs
        property string label: "PARAM"
        property int val: 50
        property color accent: Theme.primary
        signal moved(int v)

        height: ScaleMetrics.dp(24)
        radius: 3
        color: "#10141d"
        border.color: Theme.borderCard
        border.width: 1

        Rectangle {
            x: 0; y: 0
            width: parent.width * (fs.val / 127.0)
            height: parent.height
            radius: 3
            color: Qt.rgba(fs.accent.r, fs.accent.g, fs.accent.b, 0.35)
        }

        RowLayout {
            anchors.fill: parent
            anchors.margins: 4
            Text { text: fs.label; font.bold: true; font.pixelSize: ScaleMetrics.sp(7); color: Theme.textDim }
            Item { Layout.fillWidth: true }
            Text { text: fs.val.toString(); font.family: Theme.fontMono; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textPrimary }
        }

        MouseArea {
            anchors.fill: parent
            onPositionChanged: (mouse) => {
                if (pressed) fs.moved(Math.max(0, Math.min(127, Math.round((mouse.x / width) * 127))));
            }
            onPressed: (mouse) => {
                fs.moved(Math.max(0, Math.min(127, Math.round((mouse.x / width) * 127))));
            }
        }
    }

    component EqKnob: Rectangle {
        id: ek
        property string label: "BAND"
        property int gainVal: 0
        property color accent: Theme.primary
        signal moved(int g)

        height: ScaleMetrics.dp(36)
        radius: 3
        color: "#10141d"
        border.color: Theme.borderCard
        border.width: 1

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 2
            spacing: 0
            Text { text: ek.label; font.bold: true; font.pixelSize: ScaleMetrics.sp(7); color: Theme.textDim }
            Item { Layout.fillHeight: true }
            Text {
                text: (ek.gainVal > 0 ? "+" + ek.gainVal : ek.gainVal.toString()) + " dB"
                font.family: Theme.fontMono
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(8)
                color: ek.gainVal !== 0 ? ek.accent : Theme.textDim
            }
        }

        MouseArea {
            anchors.fill: parent
            onPositionChanged: (mouse) => {
                if (pressed) {
                    var g = Math.round((mouse.x / width) * 30 - 15);
                    ek.moved(Math.max(-15, Math.min(15, g)));
                }
            }
            onPressed: (mouse) => {
                var g = Math.round((mouse.x / width) * 30 - 15);
                ek.moved(Math.max(-15, Math.min(15, g)));
            }
        }
    }
}
