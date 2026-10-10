pragma ValueTypeBehavior: Copy
import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

// Generic interactive multi-segment envelope editor (T1..T4 / L0..L4).
// Shared by the MSEG ENVELOPES full page, the quick-edit overlay, and
// anywhere a full MSEG shape editor is needed. Kinds: "PITCH" | "TVF" | "TVA".
Rectangle {
    id: root
    color: Theme.bgCard
    radius: ScaleMetrics.dp(8)
    border.color: Theme.borderCard
    border.width: 1

    property string env: "TVF"
    property var seg: ({
        times: [0, 0, 0, 0], levels: [0, 127, 127, 127, 0],
        bipolar: false, custom: false,
        mods: { velSens: 0, t1VelSens: 0, t4VelSens: 0, timeKf: 0 }
    })

    // Per-envelope signed modifier rows shown in the shared modifiers card
    function modList() {
        var items = [];
        if (env === "PITCH") {
            items.push({ key: "depth", param: "depth", label: "DEPTH", min: -12, max: 12, suffix: " st" });
        }
        if (env === "TVF") {
            items.push({ key: "envDepth", param: "envDepth", label: "ENV DEPTH", min: -63, max: 63, suffix: "" });
        }
        items.push({ key: "velSens", param: "velSens", label: "VEL SENS", min: -63, max: 63, suffix: "" });
        items.push({ key: "t1VelSens", param: "t1VelSens", label: "T1 VEL SENS", min: -63, max: 63, suffix: "" });
        items.push({ key: "t4VelSens", param: "t4VelSens", label: "T4 VEL SENS", min: -63, max: 63, suffix: "" });
        items.push({ key: "timeKf", param: "timeKeyfollow", label: "TIME KF", min: -100, max: 100, suffix: "%" });
        return items;
    }

    readonly property var mods: seg && seg.mods ? seg.mods : ({})

    function modsValue(key) {
        var m = root.mods;
        return (m && m[key] !== undefined) ? m[key] : 0;
    }

    readonly property color accent: env === "PITCH" ? "#fbbf24" : (env === "TVF" ? "#38bdf8" : "#10b981")
    readonly property string envTitle:
        env === "PITCH" ? "MULTI-SEGMENT PITCH ENVELOPE (T1..T4 / L0..L4)" :
        (env === "TVF" ? "TVF FILTER ENVELOPE (T1..T4 / L0..L4)" : "TVA AMP ENVELOPE (T1..T4 / L1..L3)")

    property int draggedPoint: -1
    property real dragStartX: 0
    property real dragStartY: 0
    property int dragStartT: 0
    property int dragStartL: 0
    property real dragLastX: 0
    property real dragTimeF: 0

    function refresh() {
        seg = Bridge.getEnvSegments(env);
        envCanvas.requestPaint();
    }

    // Levels for drawing: TVA pins start/end at 0 (hardware has only L1..L3).
    function drawLevels() {
        if (env === "TVA") {
            return [0].concat(seg.levels).concat([0]);
        }
        return seg.levels;
    }

    function isFixedPoint(i) {
        if (env === "TVA" && (i === 0 || i === 4)) return true;
        return false;
    }

    function levelToY(l, h) {
        var midY = h * 0.5;
        if (seg.bipolar) {
            return midY - (l / 63.0) * (midY - 14);
        }
        var baseY = h - 6;
        return baseY - (l / 127.0) * (baseY - 14);
    }

    function getPoints() {
        var w = envCanvas.width;
        var h = envCanvas.height;
        var dl = drawLevels();
        var times = seg.times;
        var totalT = Math.max(20, times[0] + times[1] + times[2] + times[3] + 30);
        var scaleX = (w * 0.85) / totalT;

        var p0x = 0;
        var p1x = Math.max(16, times[0] * scaleX);
        var p2x = p1x + Math.max(16, times[1] * scaleX);
        var p3x = p2x + Math.max(16, times[2] * scaleX);
        var p4x = Math.min(w, p3x + Math.max(16, times[3] * scaleX));

        var xs = [p0x, p1x, p2x, p3x, p4x];
        var labels = env === "TVA" ? ["0", "PEAK", "BRK", "SUS", "0"] : ["START", "PEAK", "BRK", "SUS", "END"];
        if (env === "PITCH") labels = ["L0", "P1", "P2", "SUS", "END"];

        var pts = [];
        for (var i = 0; i < 5; i++) {
            pts.push({
                x: xs[i],
                y: levelToY(dl[i], h),
                label: labels[i],
                t: i >= 1 ? times[i - 1] : 0,
                l: dl[i]
            });
        }
        return pts;
    }

    Connections {
        target: Bridge
        function onEnvShapeChanged(e) {
            if (e === root.env) {
                refresh();
            }
        }
    }

    Component.onCompleted: refresh()
    onEnvChanged: refresh()

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
                color: root.accent
            }
            Text {
                text: root.envTitle
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(12)
                font.letterSpacing: 1.2
                color: Theme.textPrimary
            }
            Item { Layout.fillWidth: true }

            Rectangle {
                visible: root.seg.custom
                Layout.preferredHeight: ScaleMetrics.dp(16)
                width: customLabel.width + ScaleMetrics.dp(10)
                radius: 3
                color: "#2a1b06"
                border.color: root.accent
                border.width: 1

                Text {
                    id: customLabel
                    anchors.centerIn: parent
                    text: "CUSTOM SHAPE"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(7)
                    color: root.accent
                }
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
                model: Bridge.envPresetNames(root.env)

                delegate: Rectangle {
                    Layout.fillWidth: true
                    height: ScaleMetrics.dp(22)
                    radius: 3
                    color: Theme.bgApp
                    border.color: Theme.borderCard
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: modelData
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Theme.textSecondary
                    }
                    MouseArea {
                        anchors.fill: parent
                        onClicked: Bridge.applyEnvPreset(root.env, modelData)
                    }
                }
            }
        }

        // Main Interactive Envelope Canvas
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: ScaleMetrics.dp(120)
            radius: ScaleMetrics.dp(6)
            color: "#080b11"
            border.color: Theme.borderCard
            border.width: 1
            clip: true

            Canvas {
                id: envCanvas
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(12)

                onPaint: {
                    var ctx = getContext("2d");
                    ctx.reset();
                    var w = width;
                    var h = height;
                    var midY = h * 0.5;
                    var baseY = h - 6;

                    ctx.strokeStyle = "#162032";
                    ctx.lineWidth = 1;
                    ctx.setLineDash([3, 3]);
                    ctx.beginPath();
                    if (root.seg.bipolar) {
                        ctx.moveTo(0, midY - (32 / 63.0) * (midY - 14)); ctx.lineTo(w, midY - (32 / 63.0) * (midY - 14));
                        ctx.moveTo(0, midY - (-32 / 63.0) * (midY - 14)); ctx.lineTo(w, midY - (-32 / 63.0) * (midY - 14));
                    } else {
                        ctx.moveTo(0, root.levelToY(64, h)); ctx.lineTo(w, root.levelToY(64, h));
                        ctx.moveTo(0, root.levelToY(127, h)); ctx.lineTo(w, root.levelToY(127, h));
                    }
                    ctx.stroke();

                    // Reference line: 0 for bipolar envelopes, baseline otherwise
                    ctx.strokeStyle = "#1e293b";
                    ctx.setLineDash([]);
                    ctx.lineWidth = 1.5;
                    ctx.beginPath();
                    var refY = root.seg.bipolar ? midY : baseY;
                    ctx.moveTo(0, refY); ctx.lineTo(w, refY);
                    ctx.stroke();

                    var pts = root.getPoints();
                    var p0 = pts[0], p1 = pts[1], p2 = pts[2], p3 = pts[3], p4 = pts[4];

                    ctx.fillStyle = Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.15);
                    ctx.beginPath();
                    ctx.moveTo(p0.x, refY);
                    ctx.lineTo(p0.x, p0.y);
                    ctx.lineTo(p1.x, p1.y);
                    ctx.lineTo(p2.x, p2.y);
                    ctx.lineTo(p3.x, p3.y);
                    ctx.lineTo(p4.x, p4.y);
                    ctx.lineTo(p4.x, refY);
                    ctx.closePath();
                    ctx.fill();

                    ctx.strokeStyle = root.accent;
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

                    for (var i = 0; i < pts.length; i++) {
                        var pt = pts[i];
                        var isDragged = (root.draggedPoint === i);
                        var isFixed = root.isFixedPoint(i);

                        if (isDragged) {
                            ctx.fillStyle = Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.25);
                            ctx.beginPath();
                            ctx.arc(pt.x, pt.y, 14, 0, Math.PI * 2);
                            ctx.fill();

                            ctx.strokeStyle = root.accent;
                            ctx.lineWidth = 2;
                            ctx.beginPath();
                            ctx.arc(pt.x, pt.y, 9, 0, Math.PI * 2);
                            ctx.stroke();

                            ctx.fillStyle = "#ffffff";
                            ctx.beginPath();
                            ctx.arc(pt.x, pt.y, 5, 0, Math.PI * 2);
                            ctx.fill();

                            var lText = root.seg.bipolar && pt.l > 0 ? "+" + pt.l : "" + pt.l;
                            var infoText = (i === 0) ? ("L: " + lText) : (pt.label + " • T:" + pt.t + "  L:" + lText);
                            ctx.font = "bold 10px monospace";
                            var textW = ctx.measureText(infoText).width;
                            var badgeW = textW + 16;
                            var badgeH = 20;
                            var badgeX = Math.max(6, Math.min(w - badgeW - 6, pt.x - badgeW * 0.5));
                            var badgeY = Math.max(22, pt.y - 18);

                            ctx.fillStyle = "#10141d";
                            ctx.fillRect(badgeX, badgeY - 14, badgeW, badgeH);
                            ctx.strokeStyle = root.accent;
                            ctx.lineWidth = 1;
                            ctx.strokeRect(badgeX, badgeY - 14, badgeW, badgeH);

                            ctx.fillStyle = root.accent;
                            ctx.fillText(infoText, badgeX + 8, badgeY);
                        } else {
                            ctx.fillStyle = isFixed ? "#334155" : root.accent;
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
                anchors.fill: envCanvas
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
                        root.dragStartT = (bestIdx >= 1) ? root.seg.times[bestIdx - 1] : 0;
                        root.dragStartL = root.drawLevels()[bestIdx];
                        root.dragLastX = mouse.x;
                        root.dragTimeF = root.dragStartT;
                        envCanvas.requestPaint();
                    } else {
                        root.draggedPoint = -1;
                    }
                }

                onPositionChanged: (mouse) => {
                    if (pressed && root.draggedPoint >= 0) {
                        var i = root.draggedPoint;
                        var h = envCanvas.height;

                        var newL = root.seg.bipolar ?
                            Math.round(((h * 0.5 - mouse.y) / (h * 0.5 - 14)) * 63.0) :
                            Math.round(((h - 6 - mouse.y) / (h - 6 - 14)) * 127.0);
                        newL = root.seg.bipolar ? Math.max(-63, Math.min(63, newL)) : Math.max(0, Math.min(127, newL));

                        if (!root.isFixedPoint(i)) {
                            Bridge.setEnvSegment(root.env, "l" + i, newL);
                        }

                        if (i >= 1 && i <= 4) {
                            // Map finger px -> time units through the derivative of
                            // the node's cumulative x position (d/dt of sum(max(16, tk*S/(T+30))))
                            // so the node tracks the finger ~1:1 even while the
                            // total-time rescale compresses the axis mid-drag.
                            var dx = mouse.x - root.dragLastX;
                            root.dragLastX = mouse.x;
                            var times = root.seg.times;
                            var j = i - 1;
                            var total = 0, suffix = 0;
                            for (var k = 0; k < 4; k++) {
                                total += times[k];
                                if (k > j) suffix += times[k];
                            }
                            var scaleSum = Math.max(20, total + 30);
                            var pxPerUnit = (envCanvas.width * 0.85) * (suffix + 30) / (scaleSum * scaleSum);
                            if (pxPerUnit > 0.01) {
                                root.dragTimeF += dx / pxPerUnit;
                            }
                            root.dragTimeF = Math.max(0, Math.min(127, root.dragTimeF));
                            Bridge.setEnvSegment(root.env, "t" + i, Math.round(root.dragTimeF));
                        }

                        root.seg = Bridge.getEnvSegments(root.env);
                        envCanvas.requestPaint();
                    }
                }

                onReleased: (mouse) => {
                    root.draggedPoint = -1;
                    envCanvas.requestPaint();
                }

                onCanceled: () => {
                    root.draggedPoint = -1;
                    envCanvas.requestPaint();
                }
            }
        }

        // Envelope Modifiers Card (depth / velocity / time key follow)
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: ScaleMetrics.dp(56)
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
                        color: root.accent
                    }
                    Text {
                        text: root.env === "PITCH" ? "PITCH & TIME DYNAMICS / VELOCITY SENSITIVITY" : "ENVELOPE MODIFIERS / VELOCITY SENSITIVITY"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        font.letterSpacing: 1.0
                        color: Theme.textSecondary
                    }
                    Item { Layout.fillWidth: true }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: ScaleMetrics.dp(6)

                    Repeater {
                        model: root.modList()
                        delegate: EnvParam {
                            Layout.fillWidth: true
                            label: modelData.label
                            labelColor: root.accent
                            val: root.modsValue(modelData.key)
                            norm: (root.modsValue(modelData.key) - modelData.min) / (modelData.max - modelData.min)
                            isBipolar: true
                            barColor: root.accent
                            customText: {
                                var v = root.modsValue(modelData.key);
                                return (v > 0 ? "+" + v : v) + modelData.suffix;
                            }
                            onMoved: (n) => {
                                var v = Math.round(modelData.min + n * (modelData.max - modelData.min));
                                Bridge.setEnvModParam(root.env, modelData.param, v);
                            }
                        }
                    }
                }
            }
        }

        // Sliders Matrix: Times (T1..T4) and Levels
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(8)

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
                    Text { text: "SEGMENT TIMES (0..127)"; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: root.accent }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        Repeater {
                            model: 4
                            delegate: EnvParam {
                                Layout.fillWidth: true
                                label: "T" + (index + 1)
                                labelColor: root.accent
                                val: root.seg.times[index]
                                norm: root.seg.times[index] / 127.0
                                barColor: root.accent
                                onMoved: (n) => Bridge.setEnvSegment(root.env, "t" + (index + 1), Math.round(n * 127))
                            }
                        }
                    }
                }
            }

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
                    Text {
                        text: root.seg.bipolar ? "PITCH LEVELS (-63..+63)" : "LEVELS (0..127)"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: root.accent
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        Repeater {
                            model: root.seg.bipolar || root.env === "TVF" ? ["l0", "l1", "l2", "l3", "l4"] : ["l1", "l2", "l3"]
                            delegate: EnvParam {
                                Layout.fillWidth: true
                                readonly property int lvlIdx: Number(modelData.substring(1))
                                readonly property int lvlVal: root.seg.levels[lvlIdx - (root.env === "TVA" ? 1 : 0)]
                                label: modelData.toUpperCase()
                                labelColor: root.accent
                                val: lvlVal
                                norm: root.seg.bipolar ? (lvlVal + 63) / 126.0 : lvlVal / 127.0
                                isBipolar: root.seg.bipolar
                                barColor: root.accent
                                onMoved: (n) => Bridge.setEnvSegment(
                                    root.env, modelData,
                                    root.seg.bipolar ? Math.round(n * 126 - 63) : Math.round(n * 127))
                            }
                        }
                    }
                }
            }
        }
    }
}
