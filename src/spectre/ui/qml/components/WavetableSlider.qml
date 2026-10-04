import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

Item {
    id: root
    clip: true

    property bool is3DView: true

    // Cached tone wave info & 64-point arrays to eliminate Python bridge queries during rendering
    property var cachedToneWaves: []
    property var toneSamples: [null, null, null, null]

    function updateCachedWaves() {
        var tw = Bridge.toneWaveData;
        cachedToneWaves = tw || [];
        toneSamples = [
            (tw && tw.length > 0) ? tw[0].samples_64 : null,
            (tw && tw.length > 1) ? tw[1].samples_64 : null,
            (tw && tw.length > 2) ? tw[2].samples_64 : null,
            (tw && tw.length > 3) ? tw[3].samples_64 : null
        ];
    }

    function sampleTone(s, tIdx, normPhase) {
        if (s && s.length >= 64) {
            var idxF = normPhase * 63.0;
            var i0 = Math.floor(idxF);
            var frac = idxF - i0;
            var i1 = (i0 < 63) ? i0 + 1 : 63;
            return (1.0 - frac) * s[i0] + frac * s[i1];
        }
        if (tIdx === 0) return 2.0 * (normPhase - Math.floor(normPhase + 0.5));
        if (tIdx === 1) return normPhase < 0.5 ? 0.9 : -0.9;
        if (tIdx === 2) return 2.0 * Math.abs(2.0 * (normPhase - Math.floor(normPhase + 0.5))) - 1.0;
        return Math.sin(normPhase * 2.0 * Math.PI);
    }

    function sampleAt(phase, z) {
        var normPhase = ((phase / (2.0 * Math.PI)) % 1.0 + 1.0) % 1.0;
        var s0 = root.toneSamples[0];
        var s1 = root.toneSamples[1];
        var s2 = root.toneSamples[2];
        var s3 = root.toneSamples[3];

        var m1 = Bridge.tone1Muted ? 0.0 : 1.0;
        var m2 = Bridge.tone2Muted ? 0.0 : 1.0;
        var m3 = Bridge.tone3Muted ? 0.0 : 1.0;
        var m4 = Bridge.tone4Muted ? 0.0 : 1.0;

        var t1 = sampleTone(s0, 0, normPhase) * m1;
        var t2 = sampleTone(s1, 1, normPhase) * m2;
        var t3 = sampleTone(s2, 2, normPhase) * m3;
        var t4 = sampleTone(s3, 3, normPhase) * m4;

        if (z <= 0.333333) {
            var t = z * 3.0;
            return (1.0 - t) * t1 + t * t2;
        } else if (z <= 0.666667) {
            var t = (z - 0.333333) * 3.0;
            return (1.0 - t) * t2 + t * t3;
        } else {
            var t = (z - 0.666667) * 3.0;
            return (1.0 - t) * t3 + t * t4;
        }
    }

    Component.onCompleted: updateCachedWaves()

    RowLayout {
        anchors.fill: parent
        spacing: ScaleMetrics.dp(8)

        // =====================================================================
        // COLUMN 1: LEFT SWEEP CONTROLS (~140dp)
        // =====================================================================
        Rectangle {
            Layout.preferredWidth: ScaleMetrics.dp(140)
            Layout.fillHeight: true
            color: Theme.bgCard
            radius: ScaleMetrics.dp(8)
            border.color: Theme.borderCard
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(8)
                spacing: ScaleMetrics.dp(6)

                Text {
                    text: "WAVE SWEEP"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(10)
                    font.letterSpacing: 1.2
                    color: Theme.tone3
                    Layout.alignment: Qt.AlignHCenter
                }

                // 2D / 3D Scope Toggle
                Rectangle {
                    Layout.fillWidth: true
                    height: ScaleMetrics.dp(26)
                    radius: ScaleMetrics.dp(4)
                    color: Theme.bgApp
                    border.color: Theme.borderCard
                    border.width: 1

                    Row {
                        anchors.fill: parent
                        anchors.margins: 2

                        Rectangle {
                            width: parent.width / 2
                            height: parent.height
                            radius: ScaleMetrics.dp(3)
                            color: !root.is3DView ? Theme.bgCardActive : "transparent"
                            border.color: !root.is3DView ? Theme.tone1 : "transparent"
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: "2D SCOPE"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(8)
                                color: !root.is3DView ? Theme.textPrimary : Theme.textDim
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    root.is3DView = false;
                                    waveCanvas.requestPaint();
                                }
                            }
                        }

                        Rectangle {
                            width: parent.width / 2
                            height: parent.height
                            radius: ScaleMetrics.dp(3)
                            color: root.is3DView ? Theme.bgCardActive : "transparent"
                            border.color: root.is3DView ? Theme.tone1 : "transparent"
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: "3D WATER"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(8)
                                color: root.is3DView ? Theme.textPrimary : Theme.textDim
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    root.is3DView = true;
                                    waveCanvas.requestPaint();
                                }
                            }
                        }
                    }
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderCard }

                // Sweep Mode Selector
                Text {
                    text: "SWEEP MODE"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: Theme.textDim
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: ScaleMetrics.dp(4)

                    SweepPill {
                        Layout.fillWidth: true
                        text: "MANUAL"
                        isActive: Bridge.wavetableSweepMode === "manual"
                        onClicked: Bridge.setWavetableSweepMode("manual")
                    }
                    SweepPill {
                        Layout.fillWidth: true
                        text: "SINE"
                        isActive: Bridge.wavetableSweepMode === "sine"
                        onClicked: Bridge.setWavetableSweepMode("sine")
                    }
                    SweepPill {
                        Layout.fillWidth: true
                        text: "TRIANGLE"
                        isActive: Bridge.wavetableSweepMode === "triangle"
                        onClicked: Bridge.setWavetableSweepMode("triangle")
                    }
                    SweepPill {
                        Layout.fillWidth: true
                        text: "RAMP UP"
                        isActive: Bridge.wavetableSweepMode === "ramp"
                        onClicked: Bridge.setWavetableSweepMode("ramp")
                    }
                    SweepPill {
                        Layout.fillWidth: true
                        text: "RANDOM S&H"
                        isActive: Bridge.wavetableSweepMode === "random_step"
                        onClicked: Bridge.setWavetableSweepMode("random_step")
                    }
                    SweepPill {
                        Layout.fillWidth: true
                        text: "CHAOS"
                        isActive: Bridge.wavetableSweepMode === "chaos"
                        onClicked: Bridge.setWavetableSweepMode("chaos")
                    }
                }

                Item { Layout.fillHeight: true }

                // Speed Slider
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: ScaleMetrics.dp(2)

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "SPEED"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: Theme.textDim
                        }
                        Item { Layout.fillWidth: true }
                        Text {
                            text: Bridge.speed.toFixed(2) + "x"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            font.family: Theme.fontMono
                            color: Theme.tone3
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(16)
                        radius: ScaleMetrics.dp(3)
                        color: "#0f172a"
                        border.color: Theme.borderCard
                        border.width: 1
                        clip: true

                        property real norm: Math.max(0.0, Math.min(1.0, (Bridge.speed - 0.25) / 1.75))

                        Rectangle {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            width: parent.width * parent.norm
                            color: Theme.tone3
                        }

                        MouseArea {
                            anchors.fill: parent
                            onPressed: (mouse) => {
                                const frac = Math.max(0.0, Math.min(1.0, mouse.x / width));
                                Bridge.setSpeed(0.25 + frac * 1.75);
                            }
                            onPositionChanged: (mouse) => {
                                if (pressed) {
                                    const frac = Math.max(0.0, Math.min(1.0, mouse.x / width));
                                    Bridge.setSpeed(0.25 + frac * 1.75);
                                }
                            }
                        }
                    }
                }

                // Curve Toggle
                Rectangle {
                    Layout.fillWidth: true
                    height: ScaleMetrics.dp(24)
                    radius: ScaleMetrics.dp(4)
                    color: Theme.bgApp
                    border.color: Theme.borderCard
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: Bridge.curve === "equal_power" ? "CURVE: EQ-PWR" : "CURVE: LINEAR"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Theme.textSecondary
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: Bridge.setCurve(Bridge.curve === "equal_power" ? "linear" : "equal_power")
                    }
                }
            }
        }

        // =====================================================================
        // COLUMN 2: 1D MORPH WORKSPACE (CENTER CANVAS)
        // =====================================================================
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: Theme.bgCard
            radius: ScaleMetrics.dp(8)
            border.color: Theme.borderCard
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(10)
                spacing: ScaleMetrics.dp(8)

                // Header Readout
                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: "1D LINEAR WAVETABLE MORPH SCANNER"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(11)
                        color: Theme.textPrimary
                    }
                    Item { Layout.fillWidth: true }
                    Text {
                        text: "POS: " + Bridge.wavetablePos.toFixed(3)
                        font.bold: true
                        font.family: Theme.fontMono
                        font.pixelSize: ScaleMetrics.sp(11)
                        color: Theme.tone3
                    }
                }

                // Visualizer Canvas Screen
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: ScaleMetrics.dp(6)
                    color: "#07090d"
                    border.color: Theme.borderCard
                    border.width: 1
                    clip: true

                    // Grid lines (visible in 2D mode)
                    Rectangle {
                        anchors.centerIn: parent
                        width: parent.width
                        height: 1
                        color: "#1e293b"
                        visible: !root.is3DView
                    }

                    // Real-time canvas drawing either 2D Scope or 3D Isometric Waterfall
                    Canvas {
                        id: waveCanvas
                        anchors.fill: parent
                        anchors.margins: ScaleMetrics.dp(8)
                        renderStrategy: Canvas.Immediate

                        Component.onCompleted: requestPaint()
                        onVisibleChanged: if (visible) requestPaint()
                        onWidthChanged: requestPaint()
                        onHeightChanged: requestPaint()

                        Connections {
                            target: Bridge
                            function onWavetablePosChanged() { if (root.visible) waveCanvas.requestPaint(); }
                            function onToneWavesChanged() {
                                root.updateCachedWaves();
                                if (root.visible) waveCanvas.requestPaint();
                            }
                            function onToneMutesChanged() { if (root.visible) waveCanvas.requestPaint(); }
                        }

                        onPaint: {
                            var ctx = getContext("2d");
                            if (!ctx) return;
                            ctx.clearRect(0, 0, width, height);

                            var curW = Math.max(0.0, Math.min(1.0, Bridge.wavetablePos));

                            if (!root.is3DView) {
                                // ==========================================
                                // 2D SCOPE: SINGLE-COLOR CYAN GLOW + CORE
                                // ==========================================
                                var cy = height / 2.0;
                                var amp2d = height * 0.38;
                                var step2d = 3;
                                var pts2d = [];

                                for (var x = 0; x <= width; x += step2d) {
                                    var phase = (x / width) * 2.0 * Math.PI * 2.0;
                                    var sample = root.sampleAt(phase, curW);
                                    pts2d.push({ x: x, y: cy - sample * amp2d });
                                }

                                if (pts2d.length < 2) return;

                                // Pass 1: Wide ambient cyan glow
                                ctx.beginPath();
                                ctx.moveTo(pts2d[0].x, pts2d[0].y);
                                for (var i = 1; i < pts2d.length; i++) {
                                    ctx.lineTo(pts2d[i].x, pts2d[i].y);
                                }
                                ctx.lineWidth = 6;
                                ctx.strokeStyle = "rgba(14, 165, 233, 0.35)";
                                ctx.lineCap = "round";
                                ctx.lineJoin = "round";
                                ctx.stroke();

                                // Pass 2: Crisp bright core wave
                                ctx.beginPath();
                                ctx.moveTo(pts2d[0].x, pts2d[0].y);
                                for (var j = 1; j < pts2d.length; j++) {
                                    ctx.lineTo(pts2d[j].x, pts2d[j].y);
                                }
                                ctx.lineWidth = 2.5;
                                ctx.strokeStyle = "#38bdf8";
                                ctx.lineCap = "round";
                                ctx.lineJoin = "round";
                                ctx.stroke();

                            } else {
                                // ==========================================
                                // 3D WATERFALL ISOMETRIC VIEW
                                // ==========================================
                                var numSlices = 16;
                                var dxDepth = width * 0.22;
                                var dyDepth = height * 0.52;
                                var amp3d = height * 0.14;
                                var step3d = 3;

                                function computeSlice(z) {
                                    var wSlice = width * 0.72 * (1.0 - z * 0.12);
                                    var x0 = width * 0.05 + z * dxDepth;
                                    var yBase = height * 0.78 - z * dyDepth;

                                    var slicePts = [];
                                    for (var sx = 0; sx <= wSlice; sx += step3d) {
                                        var p = (sx / wSlice) * 2.0 * Math.PI;
                                        var smp = root.sampleAt(p, z);
                                        slicePts.push({ x: x0 + sx, y: yBase - smp * amp3d });
                                    }
                                    return {
                                        z: z,
                                        pts: slicePts,
                                        x0: x0,
                                        yBase: yBase,
                                        wSlice: wSlice
                                    };
                                }

                                var activeSliceData = computeSlice(curW);

                                function drawWireSlice(slice) {
                                    var slicePts = slice.pts;
                                    var z = slice.z;
                                    if (slicePts.length < 2) return;

                                    ctx.beginPath();
                                    ctx.lineWidth = 2.0; // User specified: 2px wireframe
                                    ctx.lineCap = "round";
                                    ctx.lineJoin = "round";
                                    var alpha = 0.36 + (1.0 - z) * 0.12;
                                    ctx.strokeStyle = "rgba(56, 189, 248, " + alpha.toFixed(2) + ")";
                                    ctx.moveTo(slicePts[0].x, slicePts[0].y);
                                    for (var wIdx = 1; wIdx < slicePts.length; wIdx++) {
                                        ctx.lineTo(slicePts[wIdx].x, slicePts[wIdx].y);
                                    }
                                    ctx.stroke();
                                }

                                // Render wireframe slices from back (z = 1) to front (z = 0)
                                for (var k = numSlices - 1; k >= 0; k--) {
                                    var zSlice = k / (numSlices - 1);
                                    if (Math.abs(zSlice - curW) > 0.035) {
                                        var wireSlice = computeSlice(zSlice);
                                        drawWireSlice(wireSlice);
                                    }
                                }

                                // ==========================================
                                // DEDICATED TOP OVERLAY PASS FOR ACTIVE HIGHLIGHT
                                // Bright highlight matching wireframe color scheme:
                                // Neon cyan bloom glow + white-hot sharp core
                                // ==========================================
                                if (activeSliceData && activeSliceData.pts.length > 1) {
                                    var aPts = activeSliceData.pts;

                                    // Pass 1: Neon bloom glow (same cyan color as wireframe)
                                    ctx.beginPath();
                                    ctx.moveTo(aPts[0].x, aPts[0].y);
                                    for (var g = 1; g < aPts.length; g++) {
                                        ctx.lineTo(aPts[g].x, aPts[g].y);
                                    }
                                    ctx.lineWidth = 5.5;
                                    ctx.strokeStyle = "rgba(56, 189, 248, 0.65)";
                                    ctx.lineCap = "round";
                                    ctx.lineJoin = "round";
                                    ctx.stroke();

                                    // Pass 2: White-hot sharp core
                                    ctx.beginPath();
                                    ctx.moveTo(aPts[0].x, aPts[0].y);
                                    for (var c = 1; c < aPts.length; c++) {
                                        ctx.lineTo(aPts[c].x, aPts[c].y);
                                    }
                                    ctx.lineWidth = 2.4;
                                    ctx.strokeStyle = "#ffffff";
                                    ctx.lineCap = "round";
                                    ctx.lineJoin = "round";
                                    ctx.stroke();
                                }
                            }
                        }
                    }
                }

                // Tone Badges Row (T1, T2, T3, T4)
                RowLayout {
                    Layout.fillWidth: true

                    WaveNodeBadge {
                        toneIndex: 0
                        toneColor: Theme.tone1
                        level: Bridge.tone1Level
                    }

                    Item { Layout.fillWidth: true }

                    WaveNodeBadge {
                        toneIndex: 1
                        toneColor: Theme.tone2
                        level: Bridge.tone2Level
                    }

                    Item { Layout.fillWidth: true }

                    WaveNodeBadge {
                        toneIndex: 2
                        toneColor: Theme.tone3
                        level: Bridge.tone3Level
                    }

                    Item { Layout.fillWidth: true }

                    WaveNodeBadge {
                        toneIndex: 3
                        toneColor: Theme.tone4
                        level: Bridge.tone4Level
                    }
                }

                // 1D Linear Morph Track
                Rectangle {
                    id: track
                    Layout.fillWidth: true
                    height: ScaleMetrics.dp(44)
                    radius: ScaleMetrics.dp(8)
                    color: Theme.bgApp
                    border.color: Theme.borderCard
                    border.width: 1
                    clip: false

                    // Zone Gradients
                    Row {
                        anchors.fill: parent
                        anchors.margins: ScaleMetrics.dp(3)
                        spacing: ScaleMetrics.dp(2)

                        Rectangle {
                            width: (parent.width - ScaleMetrics.dp(4)) / 3
                            height: parent.height
                            radius: ScaleMetrics.dp(6)
                            gradient: Gradient {
                                orientation: Gradient.Horizontal
                                GradientStop { position: 0.0; color: Qt.rgba(Theme.tone1.r, Theme.tone1.g, Theme.tone1.b, 0.35) }
                                GradientStop { position: 1.0; color: Qt.rgba(Theme.tone2.r, Theme.tone2.g, Theme.tone2.b, 0.35) }
                            }
                        }

                        Rectangle {
                            width: (parent.width - ScaleMetrics.dp(4)) / 3
                            height: parent.height
                            radius: ScaleMetrics.dp(6)
                            gradient: Gradient {
                                orientation: Gradient.Horizontal
                                GradientStop { position: 0.0; color: Qt.rgba(Theme.tone2.r, Theme.tone2.g, Theme.tone2.b, 0.35) }
                                GradientStop { position: 1.0; color: Qt.rgba(Theme.tone3.r, Theme.tone3.g, Theme.tone3.b, 0.35) }
                            }
                        }

                        Rectangle {
                            width: (parent.width - ScaleMetrics.dp(4)) / 3
                            height: parent.height
                            radius: ScaleMetrics.dp(6)
                            gradient: Gradient {
                                orientation: Gradient.Horizontal
                                GradientStop { position: 0.0; color: Qt.rgba(Theme.tone3.r, Theme.tone3.g, Theme.tone3.b, 0.35) }
                                GradientStop { position: 1.0; color: Qt.rgba(Theme.tone4.r, Theme.tone4.g, Theme.tone4.b, 0.35) }
                            }
                        }
                    }

                    // Draggable Knob / Handle
                    Rectangle {
                        id: handle
                        x: Math.max(0, Math.min(track.width - width, Bridge.wavetablePos * (track.width - width)))
                        anchors.verticalCenter: parent.verticalCenter
                        width: ScaleMetrics.dp(46)
                        height: ScaleMetrics.dp(46)
                        radius: width / 2
                        color: "#1e293b"
                        border.color: Theme.tone3
                        border.width: ScaleMetrics.dp(3)
                        z: 10

                        Rectangle {
                            anchors.centerIn: parent
                            width: ScaleMetrics.dp(14)
                            height: ScaleMetrics.dp(14)
                            radius: width / 2
                            color: Theme.textPrimary
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        preventStealing: true

                        function updatePos(mouse) {
                            var usableW = track.width - handle.width;
                            var norm = Math.max(0.0, Math.min(1.0, (mouse.x - handle.width / 2) / usableW));
                            Bridge.setWavetablePos(norm);
                        }

                        onPressed: (mouse) => updatePos(mouse)
                        onPositionChanged: (mouse) => {
                            if (pressed) updatePos(mouse);
                        }
                    }
                }
            }
        }

        // =====================================================================
        // COLUMN 3: RIGHT FLANK MASTER SCULPTOR PANEL (~360dp)
        // =====================================================================
        SculptorPanel {
            Layout.preferredWidth: ScaleMetrics.dp(360)
            Layout.fillHeight: true
        }
    }

    // Mini Pill Button Component
    component SweepPill: Rectangle {
        id: spRoot
        property string text: "PILL"
        property bool isActive: false
        signal clicked()

        height: ScaleMetrics.dp(26)
        radius: ScaleMetrics.dp(4)
        color: isActive ? Theme.bgCardActive : "#10141d"
        border.color: isActive ? Theme.tone3 : Theme.borderCard
        border.width: 1

        Text {
            anchors.centerIn: parent
            text: spRoot.text
            font.bold: spRoot.isActive
            font.pixelSize: ScaleMetrics.sp(8)
            color: spRoot.isActive ? Theme.textPrimary : Theme.textDim
        }

        MouseArea {
            anchors.fill: parent
            onClicked: spRoot.clicked()
        }
    }

    // Node badge component with mini waveform / category icon preview
    component WaveNodeBadge: Item {
        id: bRoot
        property int toneIndex: 0
        property var waveInfo: (root.cachedToneWaves && root.cachedToneWaves.length > toneIndex) ? root.cachedToneWaves[toneIndex] : null
        property string toneName: "T" + (toneIndex + 1)
        property string waveName: waveInfo ? waveInfo.name : "WAVE"
        property color toneColor: Theme.tone1
        property int level: 0

        implicitWidth: badgeRow.implicitWidth
        implicitHeight: badgeRow.implicitHeight

        Row {
            id: badgeRow
            anchors.fill: parent
            spacing: ScaleMetrics.dp(4)

            CategoryGlyph {
                width: ScaleMetrics.dp(20)
                height: ScaleMetrics.dp(14)
                anchors.verticalCenter: parent.verticalCenter
                toneIndex: bRoot.toneIndex
                category: bRoot.waveInfo ? bRoot.waveInfo.category : "synth_wave"
                isSingleCycle: bRoot.waveInfo ? bRoot.waveInfo.is_single_cycle : true
                samples64: bRoot.waveInfo ? bRoot.waveInfo.samples_64 : null
                color: bRoot.toneColor
            }

            Column {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 1
                Text {
                    text: bRoot.toneName + ": " + bRoot.waveName
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(9)
                    color: bRoot.toneColor
                    elide: Text.ElideRight
                }
                Text {
                    text: "LVL: " + bRoot.level
                    font.pixelSize: ScaleMetrics.sp(8)
                    font.family: Theme.fontMono
                    color: bRoot.level > 0 ? bRoot.toneColor : Theme.textMuted
                }
            }
        }

        MouseArea {
            anchors.fill: parent
            onClicked: {
                Bridge.openWaveBrowser(bRoot.toneIndex + 1);
            }
        }
    }
}
