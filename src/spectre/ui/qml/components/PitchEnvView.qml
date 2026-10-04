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

    property int envDepth: 12
    property int velSens: 30
    property int timeKeyfollow: 0
    property int t1: 20
    property int t2: 40
    property int t3: 50
    property int t4: 35
    property int l0: 0
    property int l1: 24
    property int l2: 10
    property int l3: 0
    property int l4: 0

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
                color: "#fbbf24"
            }
            Text {
                text: "MULTI-SEGMENT PITCH ENVELOPE (T1..T4 / L0..L4)"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(12)
                font.letterSpacing: 1.2
                color: Theme.textPrimary
            }
            Item { Layout.fillWidth: true }

            Text {
                text: "DEPTH: " + (root.envDepth > 0 ? "+" + root.envDepth : root.envDepth)
                font.family: Theme.fontMono
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(10)
                color: root.envDepth !== 0 ? "#fbbf24" : Theme.textDim
            }
        }

        // Preset Shapes Toolbar
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(4)

            Text {
                text: "PRESETS:"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(8)
                color: Theme.textDim
            }

            Repeater {
                model: [
                    { name: "FLAT / INIT", t1: 0, t2: 0, t3: 0, t4: 0, l0: 0, l1: 0, l2: 0, l3: 0, l4: 0 },
                    { name: "BRASS BITE", t1: 15, t2: 30, t3: 40, t4: 20, l0: -8, l1: 12, l2: 0, l3: 0, l4: 0 },
                    { name: "LASER ZAP", t1: 5, t2: 45, t3: 20, t4: 20, l0: 48, l1: 30, l2: 0, l3: 0, l4: 0 },
                    { name: "KICK THUMP", t1: 2, t2: 25, t3: 10, t4: 15, l0: 60, l1: 0, l2: 0, l3: 0, l4: 0 },
                    { name: "SLOW DIVE", t1: 40, t2: 60, t3: 80, t4: 60, l0: 10, l1: 20, l2: -15, l3: -30, l4: -50 }
                ]

                delegate: Rectangle {
                    Layout.fillWidth: true
                    height: ScaleMetrics.dp(22)
                    radius: 3
                    color: Theme.bgApp
                    border.color: Theme.borderCard
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: modelData.name
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Theme.textSecondary
                    }
                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            root.t1 = modelData.t1; root.t2 = modelData.t2;
                            root.t3 = modelData.t3; root.t4 = modelData.t4;
                            root.l0 = modelData.l0; root.l1 = modelData.l1;
                            root.l2 = modelData.l2; root.l3 = modelData.l3; root.l4 = modelData.l4;
                            pitchCanvas.requestPaint();
                        }
                    }
                }
            }
        }

        // Main Interactive Bipolar Pitch Envelope Canvas
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: ScaleMetrics.dp(6)
            color: "#080b11"
            border.color: Theme.borderCard
            border.width: 1
            clip: true

            Canvas {
                id: pitchCanvas
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(12)

                onPaint: {
                    var ctx = getContext("2d");
                    ctx.reset();
                    var w = width;
                    var h = height;
                    var midY = h * 0.5;

                    // Draw Center Pitch Line (0 semitones)
                    ctx.strokeStyle = "#1e293b";
                    ctx.lineWidth = 1;
                    ctx.beginPath();
                    ctx.moveTo(0, midY); ctx.lineTo(w, midY);
                    ctx.stroke();

                    // Calculate stage segment x positions
                    var totalT = Math.max(20, root.t1 + root.t2 + root.t3 + root.t4 + 30);
                    var scaleX = (w * 0.85) / totalT;

                    var p0x = 0;
                    var p0y = midY - (root.l0 / 63.0) * (midY - 10);

                    var p1x = Math.max(10, root.t1 * scaleX);
                    var p1y = midY - (root.l1 / 63.0) * (midY - 10);

                    var p2x = p1x + Math.max(10, root.t2 * scaleX);
                    var p2y = midY - (root.l2 / 63.0) * (midY - 10);

                    var p3x = p2x + Math.max(10, root.t3 * scaleX);
                    var p3y = midY - (root.l3 / 63.0) * (midY - 10);

                    var p4x = Math.min(w, p3x + Math.max(10, root.t4 * scaleX));
                    var p4y = midY - (root.l4 / 63.0) * (midY - 10);

                    // Area Fill to Midline
                    ctx.fillStyle = Qt.rgba(0.98, 0.75, 0.14, 0.18);
                    ctx.beginPath();
                    ctx.moveTo(p0x, midY);
                    ctx.lineTo(p0x, p0y);
                    ctx.lineTo(p1x, p1y);
                    ctx.lineTo(p2x, p2y);
                    ctx.lineTo(p3x, p3y);
                    ctx.lineTo(p4x, p4y);
                    ctx.lineTo(p4x, midY);
                    ctx.closePath();
                    ctx.fill();

                    // Curve Stroke
                    ctx.strokeStyle = "#fbbf24";
                    ctx.lineWidth = 2.5;
                    ctx.beginPath();
                    ctx.moveTo(p0x, p0y);
                    ctx.lineTo(p1x, p1y);
                    ctx.lineTo(p2x, p2y);
                    ctx.lineTo(p3x, p3y);
                    ctx.lineTo(p4x, p4y);
                    ctx.stroke();

                    // Draw control handle dots
                    var pts = [
                        { x: p0x, y: p0y, label: "L0" },
                        { x: p1x, y: p1y, label: "P1" },
                        { x: p2x, y: p2y, label: "P2" },
                        { x: p3x, y: p3y, label: "SUS" },
                        { x: p4x, y: p4y, label: "END" }
                    ];

                    for (var i = 0; i < pts.length; i++) {
                        ctx.fillStyle = "#fbbf24";
                        ctx.beginPath();
                        ctx.arc(pts[i].x, pts[i].y, 5, 0, Math.PI * 2);
                        ctx.fill();

                        ctx.fillStyle = "#ffffff";
                        ctx.font = "9px monospace";
                        ctx.fillText(pts[i].label, pts[i].x - 8, pts[i].y - 8);
                    }
                }
            }
        }

        // Sliders Matrix: Times (T1..T4) and Levels (L0..L4)
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(8)

            // Times Card
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: ScaleMetrics.dp(75)
                radius: ScaleMetrics.dp(4)
                color: Theme.bgApp
                border.color: Theme.borderCard
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(6)
                    spacing: 2
                    Text { text: "SEGMENT TIMES (0..127)"; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: Theme.tone1 }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        EnvParam { Layout.fillWidth: true; label: "T1"; val: root.t1; norm: root.t1/127.0; onMoved: (n) => { root.t1 = Math.round(n*127); pitchCanvas.requestPaint(); } }
                        EnvParam { Layout.fillWidth: true; label: "T2"; val: root.t2; norm: root.t2/127.0; onMoved: (n) => { root.t2 = Math.round(n*127); pitchCanvas.requestPaint(); } }
                        EnvParam { Layout.fillWidth: true; label: "T3"; val: root.t3; norm: root.t3/127.0; onMoved: (n) => { root.t3 = Math.round(n*127); pitchCanvas.requestPaint(); } }
                        EnvParam { Layout.fillWidth: true; label: "T4"; val: root.t4; norm: root.t4/127.0; onMoved: (n) => { root.t4 = Math.round(n*127); pitchCanvas.requestPaint(); } }
                    }
                }
            }

            // Levels Card (Bipolar -63..+63)
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: ScaleMetrics.dp(75)
                radius: ScaleMetrics.dp(4)
                color: Theme.bgApp
                border.color: Theme.borderCard
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(6)
                    spacing: 2
                    Text { text: "PITCH LEVELS (-63..+63)"; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: "#fbbf24" }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        EnvParam { Layout.fillWidth: true; label: "L0"; val: root.l0; norm: (root.l0+63)/126.0; isBipolar: true; onMoved: (n) => { root.l0 = Math.round(n*126 - 63); pitchCanvas.requestPaint(); } }
                        EnvParam { Layout.fillWidth: true; label: "L1"; val: root.l1; norm: (root.l1+63)/126.0; isBipolar: true; onMoved: (n) => { root.l1 = Math.round(n*126 - 63); pitchCanvas.requestPaint(); } }
                        EnvParam { Layout.fillWidth: true; label: "L2"; val: root.l2; norm: (root.l2+63)/126.0; isBipolar: true; onMoved: (n) => { root.l2 = Math.round(n*126 - 63); pitchCanvas.requestPaint(); } }
                        EnvParam { Layout.fillWidth: true; label: "L3"; val: root.l3; norm: (root.l3+63)/126.0; isBipolar: true; onMoved: (n) => { root.l3 = Math.round(n*126 - 63); pitchCanvas.requestPaint(); } }
                        EnvParam { Layout.fillWidth: true; label: "L4"; val: root.l4; norm: (root.l4+63)/126.0; isBipolar: true; onMoved: (n) => { root.l4 = Math.round(n*126 - 63); pitchCanvas.requestPaint(); } }
                    }
                }
            }
        }
    }

    // Mini Param Slider Component
    component EnvParam: Rectangle {
        id: ep
        property string label: "P"
        property int val: 0
        property real norm: 0.5
        property bool isBipolar: false
        signal moved(real norm)

        height: ScaleMetrics.dp(34)
        radius: 3
        color: "#10141d"
        border.color: Theme.borderCard
        border.width: 1

        Rectangle {
            x: ep.isBipolar ? (ep.norm >= 0.5 ? parent.width * 0.5 : parent.width * ep.norm) : 0
            width: ep.isBipolar ? Math.abs(parent.width * (ep.norm - 0.5)) : parent.width * ep.norm
            height: parent.height
            color: Qt.rgba(0.98, 0.75, 0.14, 0.3)
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 2
            spacing: 0
            Text { text: ep.label; font.bold: true; font.pixelSize: ScaleMetrics.sp(7); color: Theme.textDim }
            Item { Layout.fillHeight: true }
            Text {
                text: ep.isBipolar && ep.val > 0 ? "+" + ep.val : ep.val.toString()
                font.family: Theme.fontMono
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(8)
                color: Theme.textPrimary
            }
        }

        MouseArea {
            anchors.fill: parent
            onPositionChanged: (mouse) => {
                if (pressed) {
                    var n = Math.max(0.0, Math.min(1.0, mouse.x / width));
                    ep.moved(n);
                }
            }
            onPressed: (mouse) => {
                var n = Math.max(0.0, Math.min(1.0, mouse.x / width));
                ep.moved(n);
            }
        }
    }
}
