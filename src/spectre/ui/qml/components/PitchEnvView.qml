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

    property int draggedPoint: -1
    property real dragStartX: 0
    property real dragStartY: 0
    property int dragStartT: 0
    property int dragStartL: 0

    Connections {
        target: Bridge
        function onPitchEnvChanged() {
            pitchCanvas.requestPaint();
        }
    }

    onEnvDepthChanged: pitchCanvas.requestPaint()
    onT1Changed: pitchCanvas.requestPaint()
    onT2Changed: pitchCanvas.requestPaint()
    onT3Changed: pitchCanvas.requestPaint()
    onT4Changed: pitchCanvas.requestPaint()
    onL0Changed: pitchCanvas.requestPaint()
    onL1Changed: pitchCanvas.requestPaint()
    onL2Changed: pitchCanvas.requestPaint()
    onL3Changed: pitchCanvas.requestPaint()
    onL4Changed: pitchCanvas.requestPaint()

    function getPoints() {
        var w = pitchCanvas.width;
        var h = pitchCanvas.height;
        var midY = h * 0.5;
        var totalT = Math.max(20, root.t1 + root.t2 + root.t3 + root.t4 + 30);
        var scaleX = (w * 0.85) / totalT;

        var p0x = 0;
        var p0y = midY - (root.l0 / 63.0) * (midY - 14);

        var p1x = Math.max(16, root.t1 * scaleX);
        var p1y = midY - (root.l1 / 63.0) * (midY - 14);

        var p2x = p1x + Math.max(16, root.t2 * scaleX);
        var p2y = midY - (root.l2 / 63.0) * (midY - 14);

        var p3x = p2x + Math.max(16, root.t3 * scaleX);
        var p3y = midY - (root.l3 / 63.0) * (midY - 14);

        var p4x = Math.min(w, p3x + Math.max(16, root.t4 * scaleX));
        var p4y = midY - (root.l4 / 63.0) * (midY - 14);

        return [
            { x: p0x, y: p0y, label: "L0", t: 0, l: root.l0 },
            { x: p1x, y: p1y, label: "P1", t: root.t1, l: root.l1 },
            { x: p2x, y: p2y, label: "P2", t: root.t2, l: root.l2 },
            { x: p3x, y: p3y, label: "SUS", t: root.t3, l: root.l3 },
            { x: p4x, y: p4y, label: "END", t: root.t4, l: root.l4 }
        ];
    }

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
                text: "DEPTH: " + (root.envDepth > 0 ? "+" + root.envDepth : root.envDepth) + " st"
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
                            Bridge.setPitchEnvParam("t1", modelData.t1);
                            Bridge.setPitchEnvParam("t2", modelData.t2);
                            Bridge.setPitchEnvParam("t3", modelData.t3);
                            Bridge.setPitchEnvParam("t4", modelData.t4);
                            Bridge.setPitchEnvParam("l0", modelData.l0);
                            Bridge.setPitchEnvParam("l1", modelData.l1);
                            Bridge.setPitchEnvParam("l2", modelData.l2);
                            Bridge.setPitchEnvParam("l3", modelData.l3);
                            Bridge.setPitchEnvParam("l4", modelData.l4);
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

                    // Draw Subtle Grid Lines (+32, 0, -32 semitones)
                    ctx.strokeStyle = "#162032";
                    ctx.lineWidth = 1;
                    ctx.setLineDash([3, 3]);

                    var yPlus32 = midY - (32 / 63.0) * (midY - 14);
                    var yMinus32 = midY - (-32 / 63.0) * (midY - 14);

                    ctx.beginPath();
                    ctx.moveTo(0, yPlus32); ctx.lineTo(w, yPlus32);
                    ctx.moveTo(0, yMinus32); ctx.lineTo(w, yMinus32);
                    ctx.stroke();

                    // Solid Center Pitch Line (0 semitones)
                    ctx.strokeStyle = "#1e293b";
                    ctx.setLineDash([]);
                    ctx.lineWidth = 1.5;
                    ctx.beginPath();
                    ctx.moveTo(0, midY); ctx.lineTo(w, midY);
                    ctx.stroke();

                    var pts = root.getPoints();
                    var p0 = pts[0], p1 = pts[1], p2 = pts[2], p3 = pts[3], p4 = pts[4];

                    // Area Fill to Midline
                    ctx.fillStyle = Qt.rgba(0.98, 0.75, 0.14, 0.15);
                    ctx.beginPath();
                    ctx.moveTo(p0.x, midY);
                    ctx.lineTo(p0.x, p0.y);
                    ctx.lineTo(p1.x, p1.y);
                    ctx.lineTo(p2.x, p2.y);
                    ctx.lineTo(p3.x, p3.y);
                    ctx.lineTo(p4.x, p4.y);
                    ctx.lineTo(p4.x, midY);
                    ctx.closePath();
                    ctx.fill();

                    // Curve Stroke
                    ctx.strokeStyle = "#fbbf24";
                    ctx.lineWidth = 2.5;
                    ctx.lineCap = "round";
                    ctx.lineJoin = "round";
                    ctx.beginPath();
                    ctx.moveTo(p0.x, p0.y);
                    ctx.lineTo(p1.x, p1.y);
                    ctx.lineTo(p2.x, p2.y);
                    ctx.lineTo(p3.x, p3.y);
                    ctx.lineTo(p4.x, p4.y);
                    ctx.stroke();

                    // Draw control handle dots & labels
                    for (var i = 0; i < pts.length; i++) {
                        var pt = pts[i];
                        var isDragged = (root.draggedPoint === i);

                        if (isDragged) {
                            // Glowing outer touch halo
                            ctx.fillStyle = Qt.rgba(0.98, 0.75, 0.14, 0.25);
                            ctx.beginPath();
                            ctx.arc(pt.x, pt.y, 14, 0, Math.PI * 2);
                            ctx.fill();

                            ctx.strokeStyle = "#fbbf24";
                            ctx.lineWidth = 2;
                            ctx.beginPath();
                            ctx.arc(pt.x, pt.y, 9, 0, Math.PI * 2);
                            ctx.stroke();

                            // Center core
                            ctx.fillStyle = "#ffffff";
                            ctx.beginPath();
                            ctx.arc(pt.x, pt.y, 5, 0, Math.PI * 2);
                            ctx.fill();

                            // Floating value badge above touch point
                            var infoText = (i === 0) ?
                                ("L0: " + (pt.l > 0 ? "+" + pt.l : pt.l)) :
                                (pt.label + " • T:" + pt.t + "  L:" + (pt.l > 0 ? "+" + pt.l : pt.l));
                            ctx.font = "bold 10px monospace";
                            var textW = ctx.measureText(infoText).width;
                            var badgeW = textW + 16;
                            var badgeH = 20;
                            var badgeX = Math.max(6, Math.min(w - badgeW - 6, pt.x - badgeW * 0.5));
                            var badgeY = Math.max(22, pt.y - 18);

                            ctx.fillStyle = "#10141d";
                            ctx.fillRect(badgeX, badgeY - 14, badgeW, badgeH);
                            ctx.strokeStyle = "#fbbf24";
                            ctx.lineWidth = 1;
                            ctx.strokeRect(badgeX, badgeY - 14, badgeW, badgeH);

                            ctx.fillStyle = "#fbbf24";
                            ctx.fillText(infoText, badgeX + 8, badgeY);
                        } else {
                            // Normal handle dot
                            ctx.fillStyle = "#fbbf24";
                            ctx.beginPath();
                            ctx.arc(pt.x, pt.y, 5.5, 0, Math.PI * 2);
                            ctx.fill();

                            ctx.fillStyle = "#080b11";
                            ctx.beginPath();
                            ctx.arc(pt.x, pt.y, 2.5, 0, Math.PI * 2);
                            ctx.fill();

                            ctx.fillStyle = "#94a3b8";
                            ctx.font = "bold 9px monospace";
                            ctx.fillText(pt.label, pt.x - 8, pt.y - 9);
                        }
                    }
                }
            }

            // Draggable Touch Area
            MouseArea {
                id: canvasTouchArea
                anchors.fill: pitchCanvas
                hoverEnabled: true

                onPressed: (mouse) => {
                    var pts = root.getPoints();
                    var bestIdx = -1;
                    var bestDist = 999999;
                    var hitRadius = ScaleMetrics.dp(36);

                    for (var i = 0; i < pts.length; i++) {
                        var d = Math.hypot(pts[i].x - mouse.x, pts[i].y - mouse.y);
                        if (d < bestDist) {
                            bestDist = d;
                            bestIdx = i;
                        }
                    }

                    if (bestDist <= hitRadius) {
                        root.draggedPoint = bestIdx;
                        root.dragStartX = mouse.x;
                        root.dragStartY = mouse.y;
                        root.dragStartT = (bestIdx === 1 ? root.t1 : bestIdx === 2 ? root.t2 : bestIdx === 3 ? root.t3 : bestIdx === 4 ? root.t4 : 0);
                        root.dragStartL = (bestIdx === 0 ? root.l0 : bestIdx === 1 ? root.l1 : bestIdx === 2 ? root.l2 : bestIdx === 3 ? root.l3 : root.l4);
                        pitchCanvas.requestPaint();
                    } else {
                        root.draggedPoint = -1;
                    }
                }

                onPositionChanged: (mouse) => {
                    if (pressed && root.draggedPoint >= 0) {
                        var midY = pitchCanvas.height * 0.5;
                        var maxAmpY = midY - 14;
                        var newL = Math.round(((midY - mouse.y) / maxAmpY) * 63.0);
                        newL = Math.max(-63, Math.min(63, newL));

                        if (root.draggedPoint === 0) { root.l0 = newL; Bridge.setPitchEnvParam("l0", newL); }
                        else if (root.draggedPoint === 1) root.l1 = newL;
                        else if (root.draggedPoint === 2) root.l2 = newL;
                        else if (root.draggedPoint === 3) root.l3 = newL;
                        else if (root.draggedPoint === 4) root.l4 = newL;

                        if (root.draggedPoint >= 1 && root.draggedPoint <= 4) {
                            var deltaX = mouse.x - root.dragStartX;
                            var sensitivity = 127.0 / (pitchCanvas.width * 0.35);
                            var newT = Math.max(0, Math.min(127, Math.round(root.dragStartT + deltaX * sensitivity)));

                            if (root.draggedPoint === 1) { root.t1 = newT; Bridge.setPitchEnvParam("t1", newT); Bridge.setPitchEnvParam("l1", newL); }
                            else if (root.draggedPoint === 2) { root.t2 = newT; Bridge.setPitchEnvParam("t2", newT); Bridge.setPitchEnvParam("l2", newL); }
                            else if (root.draggedPoint === 3) { root.t3 = newT; Bridge.setPitchEnvParam("t3", newT); Bridge.setPitchEnvParam("l3", newL); }
                            else if (root.draggedPoint === 4) { root.t4 = newT; Bridge.setPitchEnvParam("t4", newT); Bridge.setPitchEnvParam("l4", newL); }
                        }

                        pitchCanvas.requestPaint();
                    }
                }

                onReleased: (mouse) => {
                    root.draggedPoint = -1;
                    pitchCanvas.requestPaint();
                }

                onCanceled: () => {
                    root.draggedPoint = -1;
                    pitchCanvas.requestPaint();
                }
            }
        }

        // Envelope Dynamics & Velocity Tracking Card
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: ScaleMetrics.dp(68)
            radius: ScaleMetrics.dp(4)
            color: Theme.bgApp
            border.color: Theme.borderCard
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(6)
                spacing: 2

                RowLayout {
                    Layout.fillWidth: true
                    spacing: ScaleMetrics.dp(6)

                    Rectangle {
                        width: ScaleMetrics.dp(6); height: ScaleMetrics.dp(6); radius: 3
                        color: "#fbbf24"
                    }
                    Text {
                        text: "PITCH & TIME DYNAMICS / VELOCITY SENSITIVITY"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        font.letterSpacing: 1.0
                        color: Theme.textSecondary
                    }
                    Item { Layout.fillWidth: true }
                    Text {
                        text: "DEPTH: " + (root.envDepth > 0 ? "+" + root.envDepth : root.envDepth) + " st"
                        font.family: Theme.fontMono
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: "#fbbf24"
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: ScaleMetrics.dp(6)

                    // 1. DEPTH (-12 .. +12 st)
                    EnvParam {
                        Layout.fillWidth: true
                        label: "DEPTH"
                        labelColor: "#fbbf24"
                        val: root.envDepth
                        norm: (root.envDepth + 12) / 24.0
                        isBipolar: true
                        barColor: "#fbbf24"
                        customText: (root.envDepth > 0 ? "+" + root.envDepth : root.envDepth) + " st"
                        onMoved: (n) => {
                            Bridge.setPitchEnvParam("depth", Math.round(n * 24 - 12));
                            pitchCanvas.requestPaint();
                        }
                    }

                    // 2. VEL SENS (-63 .. +63)
                    EnvParam {
                        Layout.fillWidth: true
                        label: "VEL SENS"
                        labelColor: "#fbbf24"
                        val: root.velSens
                        norm: (root.velSens + 63) / 126.0
                        isBipolar: true
                        barColor: "#fbbf24"
                        onMoved: (n) => {
                            Bridge.setPitchEnvParam("velSens", Math.round(n * 126 - 63));
                        }
                    }

                    // 3. T1 VEL SENS (-63 .. +63)
                    EnvParam {
                        Layout.fillWidth: true
                        label: "T1 VEL SENS"
                        labelColor: Theme.tone1
                        val: root.t1VelSens
                        norm: (root.t1VelSens + 63) / 126.0
                        isBipolar: true
                        barColor: Theme.tone1
                        onMoved: (n) => {
                            Bridge.setPitchEnvParam("t1VelSens", Math.round(n * 126 - 63));
                        }
                    }

                    // 4. T4 VEL SENS (-63 .. +63)
                    EnvParam {
                        Layout.fillWidth: true
                        label: "T4 VEL SENS"
                        labelColor: Theme.tone1
                        val: root.t4VelSens
                        norm: (root.t4VelSens + 63) / 126.0
                        isBipolar: true
                        barColor: Theme.tone1
                        onMoved: (n) => {
                            Bridge.setPitchEnvParam("t4VelSens", Math.round(n * 126 - 63));
                        }
                    }

                    // 5. TIME KEYFOLLOW (-100 .. +100)
                    EnvParam {
                        Layout.fillWidth: true
                        label: "TIME KF"
                        labelColor: Theme.tone1
                        val: root.timeKeyfollow
                        norm: (root.timeKeyfollow + 100) / 200.0
                        isBipolar: true
                        barColor: Theme.tone1
                        customText: (root.timeKeyfollow > 0 ? "+" + root.timeKeyfollow : root.timeKeyfollow) + "%"
                        onMoved: (n) => {
                            Bridge.setPitchEnvParam("timeKeyfollow", Math.round(n * 200 - 100));
                        }
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
                Layout.preferredHeight: ScaleMetrics.dp(72)
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
                        EnvParam { Layout.fillWidth: true; label: "T1"; labelColor: Theme.tone1; val: root.t1; norm: root.t1/127.0; barColor: Theme.tone1; onMoved: (n) => { Bridge.setPitchEnvParam("t1", Math.round(n*127)); pitchCanvas.requestPaint(); } }
                        EnvParam { Layout.fillWidth: true; label: "T2"; labelColor: Theme.tone1; val: root.t2; norm: root.t2/127.0; barColor: Theme.tone1; onMoved: (n) => { Bridge.setPitchEnvParam("t2", Math.round(n*127)); pitchCanvas.requestPaint(); } }
                        EnvParam { Layout.fillWidth: true; label: "T3"; labelColor: Theme.tone1; val: root.t3; norm: root.t3/127.0; barColor: Theme.tone1; onMoved: (n) => { Bridge.setPitchEnvParam("t3", Math.round(n*127)); pitchCanvas.requestPaint(); } }
                        EnvParam { Layout.fillWidth: true; label: "T4"; labelColor: Theme.tone1; val: root.t4; norm: root.t4/127.0; barColor: Theme.tone1; onMoved: (n) => { Bridge.setPitchEnvParam("t4", Math.round(n*127)); pitchCanvas.requestPaint(); } }
                    }
                }
            }

            // Levels Card (Bipolar -63..+63)
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: ScaleMetrics.dp(72)
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
                        EnvParam { Layout.fillWidth: true; label: "L0"; labelColor: "#fbbf24"; val: root.l0; norm: (root.l0+63)/126.0; isBipolar: true; barColor: "#fbbf24"; onMoved: (n) => { Bridge.setPitchEnvParam("l0", Math.round(n*126 - 63)); pitchCanvas.requestPaint(); } }
                        EnvParam { Layout.fillWidth: true; label: "L1"; labelColor: "#fbbf24"; val: root.l1; norm: (root.l1+63)/126.0; isBipolar: true; barColor: "#fbbf24"; onMoved: (n) => { Bridge.setPitchEnvParam("l1", Math.round(n*126 - 63)); pitchCanvas.requestPaint(); } }
                        EnvParam { Layout.fillWidth: true; label: "L2"; labelColor: "#fbbf24"; val: root.l2; norm: (root.l2+63)/126.0; isBipolar: true; barColor: "#fbbf24"; onMoved: (n) => { Bridge.setPitchEnvParam("l2", Math.round(n*126 - 63)); pitchCanvas.requestPaint(); } }
                        EnvParam { Layout.fillWidth: true; label: "L3"; labelColor: "#fbbf24"; val: root.l3; norm: (root.l3+63)/126.0; isBipolar: true; barColor: "#fbbf24"; onMoved: (n) => { Bridge.setPitchEnvParam("l3", Math.round(n*126 - 63)); pitchCanvas.requestPaint(); } }
                        EnvParam { Layout.fillWidth: true; label: "L4"; labelColor: "#fbbf24"; val: root.l4; norm: (root.l4+63)/126.0; isBipolar: true; barColor: "#fbbf24"; onMoved: (n) => { Bridge.setPitchEnvParam("l4", Math.round(n*126 - 63)); pitchCanvas.requestPaint(); } }
                    }
                }
            }
        }
    }

    // Mini Param Slider Component
    component EnvParam: Rectangle {
        id: ep
        property string label: "P"
        property color labelColor: Theme.textDim
        property int val: 0
        property real norm: 0.5
        property bool isBipolar: false
        property color barColor: "#fbbf24"
        property string customText: ""
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
            color: Qt.rgba(ep.barColor.r, ep.barColor.g, ep.barColor.b, 0.28)
        }

        Rectangle {
            visible: ep.isBipolar
            x: Math.round(parent.width * 0.5)
            y: 0
            width: 1
            height: parent.height
            color: Qt.rgba(1, 1, 1, 0.15)
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 2
            spacing: 0
            Text {
                text: ep.label
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(7)
                color: ep.labelColor
            }
            Item { Layout.fillHeight: true }
            Text {
                text: ep.customText !== "" ? ep.customText : (ep.isBipolar && ep.val > 0 ? "+" + ep.val : ep.val.toString())
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
