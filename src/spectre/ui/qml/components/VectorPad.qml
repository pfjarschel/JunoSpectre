import QtQuick
import QtQuick.Layouts
import QtQuick.Shapes
import JunoSpectre
import ".."

Item {
    id: root
    objectName: "vectorPad"
    clip: true

    // Cached tone wave info & 64-point arrays to eliminate Python bridge queries during rendering
    property var cachedToneWaves: []
    property var toneSamples: [null, null, null, null]

    function updateCachedWaves() {
        const tw = Bridge.toneWaveData;
        cachedToneWaves = tw || [];
        toneSamples = [
            (tw && tw.length > 0) ? tw[0].samples_64 : null,
            (tw && tw.length > 1) ? tw[1].samples_64 : null,
            (tw && tw.length > 2) ? tw[2].samples_64 : null,
            (tw && tw.length > 3) ? tw[3].samples_64 : null
        ];
    }

    Component.onCompleted: updateCachedWaves()

    RowLayout {
        anchors.fill: parent
        spacing: ScaleMetrics.dp(8)

        // =====================================================================
        // COLUMN 1: AUTOMATED WAVE MOTION CONTROLS (~140dp)
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

                // Header
                Text {
                    text: "WAVE MOTION"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(10)
                    font.letterSpacing: 1.2
                    color: Theme.tone1
                    Layout.alignment: Qt.AlignHCenter
                }

                // REC Button
                Rectangle {
                    Layout.fillWidth: true
                    height: ScaleMetrics.dp(34)
                    radius: ScaleMetrics.dp(5)
                    color: Bridge.recorderState === "recording" ? Theme.recording : Theme.bgApp
                    border.color: Bridge.recorderState === "recording" ? Theme.recording : Theme.borderCard
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: "● REC GESTURE"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(9)
                        color: Bridge.recorderState === "recording" ? "#ffffff" : Theme.textPrimary
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            if (Bridge.recorderState === "recording") Bridge.stopRecording();
                            else Bridge.startRecording();
                        }
                    }
                }

                // PLAY / PAUSE Button
                Rectangle {
                    Layout.fillWidth: true
                    height: ScaleMetrics.dp(34)
                    radius: ScaleMetrics.dp(5)
                    color: Bridge.recorderState === "playing" ? Theme.playing : Theme.bgApp
                    border.color: Bridge.recorderState === "playing" ? Theme.playing : Theme.borderCard
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: Bridge.recorderState === "playing" ? "❚❚ PAUSE" : "▶ PLAY MOTION"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(9)
                        color: Bridge.recorderState === "playing" ? "#000000" : Theme.textPrimary
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            if (Bridge.recorderState === "playing") Bridge.pauseMotion();
                            else Bridge.playMotion();
                        }
                    }
                }

                // Reset & Clear Buttons Row
                RowLayout {
                    Layout.fillWidth: true
                    spacing: ScaleMetrics.dp(4)

                    Rectangle {
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(28)
                        radius: ScaleMetrics.dp(4)
                        color: Theme.bgApp
                        border.color: Theme.borderCard
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: "■ RESET"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: Theme.textSecondary
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: Bridge.stopMotion()
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(28)
                        radius: ScaleMetrics.dp(4)
                        color: Theme.bgApp
                        border.color: Theme.borderCard
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: "⌫ CLEAR"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: Theme.textSecondary
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: Bridge.clearMotion()
                        }
                    }
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderCard }

                // Loop Modes
                Text {
                    text: "LOOP MODE"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: Theme.textDim
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: ScaleMetrics.dp(3)

                    LoopPill {
                        Layout.fillWidth: true
                        text: "FWD"
                        isActive: Bridge.loopMode === "forward"
                        onClicked: Bridge.setLoopMode("forward")
                    }
                    LoopPill {
                        Layout.fillWidth: true
                        text: "PONG"
                        isActive: Bridge.loopMode === "ping_pong"
                        onClicked: Bridge.setLoopMode("ping_pong")
                    }
                    LoopPill {
                        Layout.fillWidth: true
                        text: "REV"
                        isActive: Bridge.loopMode === "reverse"
                        onClicked: Bridge.setLoopMode("reverse")
                    }
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderCard }

                // Automators
                Text {
                    text: "AUTOMATOR"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: Theme.textDim
                }

                GridLayout {
                    Layout.fillWidth: true
                    columns: 2
                    rowSpacing: ScaleMetrics.dp(4)
                    columnSpacing: ScaleMetrics.dp(4)

                    LoopPill {
                        Layout.fillWidth: true
                        text: "MANUAL"
                        isActive: Bridge.automator === "none"
                        onClicked: Bridge.setAutomator("none")
                    }
                    LoopPill {
                        Layout.fillWidth: true
                        text: "ORBIT"
                        isActive: Bridge.automator === "circle"
                        onClicked: Bridge.setAutomator("circle")
                    }
                    LoopPill {
                        Layout.fillWidth: true
                        text: "LISS"
                        isActive: Bridge.automator === "lissajous"
                        onClicked: Bridge.setAutomator("lissajous")
                    }
                    LoopPill {
                        Layout.fillWidth: true
                        text: "CHAOS"
                        isActive: Bridge.automator === "chaos"
                        onClicked: Bridge.setAutomator("chaos")
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

                // Curve Pill Toggle
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
        // COLUMN 2: 2D VECTOR MORPH PAD (CENTER CANVAS)
        // =====================================================================
        Rectangle {
            id: bg
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: Theme.bgCard
            radius: ScaleMetrics.dp(8)
            border.color: Theme.borderCard
            border.width: 1
            clip: true

            // Ambient Real-Time Waveform Preview Canvas (subtle background oscilloscope)
            Canvas {
                id: vectorWaveCanvas
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(12)
                renderStrategy: Canvas.Immediate
                opacity: 0.50

                onPaint: {
                    const ctx = getContext("2d");
                    if (!ctx) return;
                    ctx.clearRect(0, 0, width, height);

                    const vx = Math.max(0.0, Math.min(1.0, Bridge.vectorX));
                    const vy = Math.max(0.0, Math.min(1.0, Bridge.vectorY));

                    // Tone mute factors
                    const m1 = Bridge.tone1Muted ? 0.0 : 1.0;
                    const m2 = Bridge.tone2Muted ? 0.0 : 1.0;
                    const m3 = Bridge.tone3Muted ? 0.0 : 1.0;
                    const m4 = Bridge.tone4Muted ? 0.0 : 1.0;

                    // 2D Vector bilinear weights (NW: Tone 1, NE: Tone 2, SW: Tone 3, SE: Tone 4)
                    const w1 = (1.0 - vx) * vy * m1;
                    const w2 = vx * vy * m2;
                    const w3 = (1.0 - vx) * (1.0 - vy) * m3;
                    const w4 = vx * (1.0 - vy) * m4;

                    const totalWeight = w1 + w2 + w3 + w4;
                    if (totalWeight < 0.001) return;

                    ctx.lineWidth = 2.5;
                    ctx.beginPath();

                    const s0 = root.toneSamples[0];
                    const s1 = root.toneSamples[1];
                    const s2 = root.toneSamples[2];
                    const s3 = root.toneSamples[3];

                    const step = 4;
                    const centerY = height / 2.0;
                    const amp = height * 0.35;
                    const points = [];
                    for (let x = 0; x <= width; x += step) {
                        const phase = (x / width) * 2.0 * Math.PI * 2.0; // 2 cycles
                        const normPhase = ((phase / (2.0 * Math.PI)) % 1.0 + 1.0) % 1.0;

                        function getToneSample(s, tIdx) {
                            if (s && s.length >= 64) {
                                const idxF = normPhase * 63.0;
                                const i0 = Math.floor(idxF);
                                const frac = idxF - i0;
                                const i1 = (i0 < 63) ? i0 + 1 : 63;
                                return (1.0 - frac) * s[i0] + frac * s[i1];
                            }
                            if (tIdx === 0) return 2.0 * (normPhase - Math.floor(normPhase + 0.5));
                            if (tIdx === 1) return normPhase < 0.5 ? 0.9 : -0.9;
                            if (tIdx === 2) return 2.0 * Math.abs(2.0 * (normPhase - Math.floor(normPhase + 0.5))) - 1.0;
                            return Math.sin(normPhase * 2.0 * Math.PI);
                        }

                        const t1 = getToneSample(s0, 0);
                        const t2 = getToneSample(s1, 1);
                        const t3 = getToneSample(s2, 2);
                        const t4 = getToneSample(s3, 3);

                        const mixed = (w1 * t1 + w2 * t2 + w3 * t3 + w4 * t4) / Math.max(1.0, Math.sqrt(totalWeight));
                        const y = centerY - mixed * amp;
                        points.push({ x: x, y: y });
                    }

                    if (points.length < 2) return;

                    // Pass 1: Ambient cyan glow
                    ctx.beginPath();
                    ctx.moveTo(points[0].x, points[0].y);
                    for (let i = 1; i < points.length; i++) {
                        ctx.lineTo(points[i].x, points[i].y);
                    }
                    ctx.lineWidth = 5.0;
                    ctx.strokeStyle = "rgba(14, 165, 233, 0.35)";
                    ctx.lineCap = "round";
                    ctx.lineJoin = "round";
                    ctx.stroke();

                    // Pass 2: Crisp bright core wave
                    ctx.beginPath();
                    ctx.moveTo(points[0].x, points[0].y);
                    for (let j = 1; j < points.length; j++) {
                        ctx.lineTo(points[j].x, points[j].y);
                    }
                    ctx.lineWidth = 2.5;
                    ctx.strokeStyle = "#38bdf8";
                    ctx.lineCap = "round";
                    ctx.lineJoin = "round";
                    ctx.stroke();
                }

                Connections {
                    target: Bridge
                    function onCoordinatesChanged() { vectorWaveCanvas.requestPaint(); }
                    function onToneWavesChanged() {
                        root.updateCachedWaves();
                        vectorWaveCanvas.requestPaint();
                    }
                    function onToneMutesChanged() { vectorWaveCanvas.requestPaint(); }
                }
            }

            // Grid Lines & Crosshairs
            Shape {
                anchors.fill: parent
                opacity: 0.25

                ShapePath {
                    strokeColor: Theme.borderCard
                    strokeWidth: 1
                    startX: bg.width / 2; startY: 0
                    PathLine { x: bg.width / 2; y: bg.height }
                }
                ShapePath {
                    strokeColor: Theme.borderCard
                    strokeWidth: 1
                    startX: 0; startY: bg.height / 2
                    PathLine { x: bg.width; y: bg.height / 2 }
                }
                ShapePath {
                    strokeColor: "#172033"
                    strokeWidth: 1
                    startX: bg.width * 0.25; startY: 0
                    PathLine { x: bg.width * 0.25; y: bg.height }
                }
                ShapePath {
                    strokeColor: "#172033"
                    strokeWidth: 1
                    startX: bg.width * 0.75; startY: 0
                    PathLine { x: bg.width * 0.75; y: bg.height }
                }
                ShapePath {
                    strokeColor: "#172033"
                    strokeWidth: 1
                    startX: 0; startY: bg.height * 0.25
                    PathLine { x: bg.width; y: bg.height * 0.25 }
                }
                ShapePath {
                    strokeColor: "#172033"
                    strokeWidth: 1
                    startX: 0; startY: bg.height * 0.75
                    PathLine { x: bg.width; y: bg.height * 0.75 }
                }
            }

            // Dynamic Motion Path Trail Canvas
            Canvas {
                id: trailCanvas
                anchors.fill: parent
                renderStrategy: Canvas.Immediate

                onPaint: {
                    const ctx = getContext("2d");
                    if (!ctx) return;
                    ctx.clearRect(0, 0, width, height);

                    const pts = Bridge.getMotionPath();
                    if (!pts || pts.length < 2) return;

                    ctx.lineWidth = 2.5;
                    ctx.strokeStyle = Qt.rgba(0.24, 0.49, 1.0, 0.75);
                    ctx.beginPath();
                    ctx.moveTo(pts[0][0] * width, (1.0 - pts[0][1]) * height);
                    for (let i = 1; i < pts.length; i++) {
                        ctx.lineTo(pts[i][0] * width, (1.0 - pts[i][1]) * height);
                    }
                    ctx.stroke();
                }

                Connections {
                    target: Bridge
                    function onMotionPointsChanged() { trailCanvas.requestPaint(); }
                }
            }

            // Corner Glow Badges for the 4 Tones
            CornerGlowBadge {
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.margins: ScaleMetrics.dp(8)
                toneIndex: 0
                toneColor: Theme.tone1
                level: Bridge.tone1Level
            }

            CornerGlowBadge {
                anchors.top: parent.top
                anchors.right: parent.right
                anchors.margins: ScaleMetrics.dp(8)
                toneIndex: 1
                toneColor: Theme.tone2
                level: Bridge.tone2Level
                alignRight: true
            }

            CornerGlowBadge {
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.margins: ScaleMetrics.dp(8)
                toneIndex: 2
                toneColor: Theme.tone3
                level: Bridge.tone3Level
            }

            CornerGlowBadge {
                anchors.bottom: parent.bottom
                anchors.right: parent.right
                anchors.margins: ScaleMetrics.dp(8)
                toneIndex: 3
                toneColor: Theme.tone4
                level: Bridge.tone4Level
                alignRight: true
            }

            // Touch Puck (Position Indicator)
            Item {
                id: puck
                x: Bridge.vectorX * bg.width - width / 2
                y: (1.0 - Bridge.vectorY) * bg.height - height / 2
                width: ScaleMetrics.dp(52)
                height: ScaleMetrics.dp(52)
                z: 20

                // Outer Halo Glow
                Rectangle {
                    anchors.centerIn: parent
                    width: parent.width + ScaleMetrics.dp(16)
                    height: parent.height + ScaleMetrics.dp(16)
                    radius: width / 2
                    color: Qt.rgba(0.24, 0.49, 1.0, 0.22)
                }

                // Middle Ring
                Rectangle {
                    anchors.centerIn: parent
                    width: parent.width
                    height: parent.height
                    radius: width / 2
                    color: "#182642"
                    border.color: Theme.primary
                    border.width: ScaleMetrics.dp(2)

                    Rectangle {
                        anchors.centerIn: parent
                        width: ScaleMetrics.dp(12)
                        height: ScaleMetrics.dp(12)
                        radius: width / 2
                        color: Theme.textPrimary
                    }
                }

                // Coordinate Readout Badge
                Rectangle {
                    anchors.bottom: parent.top
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.bottomMargin: ScaleMetrics.dp(4)
                    width: ScaleMetrics.dp(82)
                    height: ScaleMetrics.dp(18)
                    radius: ScaleMetrics.dp(3)
                    color: "#0f172a"
                    border.color: Theme.borderCard
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: Bridge.vectorX.toFixed(2) + ", " + Bridge.vectorY.toFixed(2)
                        font.pixelSize: ScaleMetrics.sp(9)
                        font.family: Theme.fontMono
                        font.bold: true
                        color: Theme.textPrimary
                    }
                }
            }

            // Gravitational Attractor Pulsar (in ORBIT mode)
            Rectangle {
                id: attractorPulsar
                visible: Bridge.automator === "circle"
                x: Bridge.attractorX * bg.width - width / 2
                y: (1.0 - Bridge.attractorY) * bg.height - height / 2
                width: ScaleMetrics.dp(24)
                height: ScaleMetrics.dp(24)
                radius: width / 2
                color: "transparent"
                border.color: "#fbbf24"
                border.width: 2
                z: 15

                Rectangle {
                    anchors.centerIn: parent
                    width: ScaleMetrics.dp(8)
                    height: ScaleMetrics.dp(8)
                    radius: width / 2
                    color: "#fbbf24"
                }

                Text {
                    anchors.top: parent.bottom
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.topMargin: 2
                    text: "ATTRACTOR"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: "#fbbf24"
                }
            }

            // Interactive Touch MouseArea
            MouseArea {
                anchors.fill: parent
                preventStealing: true

                property real startX: 0
                property real startY: 0
                property real startTime: 0

                onPressed: (mouse) => {
                    startX = mouse.x;
                    startY = mouse.y;
                    startTime = Date.now();

                    const normX = Math.max(0.0, Math.min(1.0, mouse.x / bg.width));
                    const normY = Math.max(0.0, Math.min(1.0, 1.0 - (mouse.y / bg.height)));
                    if (Bridge.automator === "circle") {
                        Bridge.setOrbitAttractor(normX, normY);
                    } else {
                        Bridge.setCoordinates(normX, normY);
                    }
                }

                onPositionChanged: (mouse) => {
                    if (pressed) {
                        const normX = Math.max(0.0, Math.min(1.0, mouse.x / bg.width));
                        const normY = Math.max(0.0, Math.min(1.0, 1.0 - (mouse.y / bg.height)));
                        if (Bridge.automator === "circle") {
                            Bridge.setOrbitAttractor(normX, normY);
                        } else {
                            Bridge.setCoordinates(normX, normY);
                        }
                    }
                }

                onReleased: (mouse) => {
                    const now = Date.now();
                    const dt = Math.max(16, now - startTime) / 1000.0;
                    const totalDist = Math.hypot(mouse.x - startX, mouse.y - startY);
                    const normX = Math.max(0.0, Math.min(1.0, mouse.x / bg.width));
                    const normY = Math.max(0.0, Math.min(1.0, 1.0 - (mouse.y / bg.height)));

                    if (Bridge.automator === "circle") {
                        if (totalDist >= ScaleMetrics.dp(24) && dt < 0.35) {
                            const dx = (mouse.x - startX) / bg.width;
                            const dy = -(mouse.y - startY) / bg.height;
                            const vx = (dx / dt) * 0.35;
                            const vy = (dy / dt) * 0.35;
                            Bridge.fling(Bridge.vectorX, Bridge.vectorY, vx, vy);
                        } else {
                            Bridge.setOrbitAttractor(normX, normY);
                        }
                    } else {
                        Bridge.setCoordinates(normX, normY);
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

    // Mini Pill Button for Left Motion Column
    component LoopPill: Rectangle {
        id: lpRoot
        property string text: "BTN"
        property bool isActive: false
        signal clicked()

        height: ScaleMetrics.dp(24)
        radius: ScaleMetrics.dp(4)
        color: isActive ? Theme.bgCardActive : "#10141d"
        border.color: isActive ? Theme.tone1 : Theme.borderCard
        border.width: 1

        Text {
            anchors.centerIn: parent
            text: lpRoot.text
            font.bold: lpRoot.isActive
            font.pixelSize: ScaleMetrics.sp(8)
            color: lpRoot.isActive ? Theme.textPrimary : Theme.textDim
        }

        MouseArea {
            anchors.fill: parent
            onClicked: lpRoot.clicked()
        }
    }

    // Corner badge component with reactive glow and waveform / category preview
    component CornerGlowBadge: Rectangle {
        id: cRoot
        z: 10
        property int toneIndex: 0
        property var waveInfo: (root.cachedToneWaves && root.cachedToneWaves.length > toneIndex) ? root.cachedToneWaves[toneIndex] : null
        property string toneName: "TONE " + (toneIndex + 1)
        property string toneSub: waveInfo ? waveInfo.name : "WAVE"
        property color toneColor: Theme.tone1
        property int level: 0
        property bool alignRight: false

        width: ScaleMetrics.dp(115)
        height: ScaleMetrics.dp(40)
        radius: ScaleMetrics.dp(6)
        color: Qt.rgba(cRoot.toneColor.r, cRoot.toneColor.g, cRoot.toneColor.b, 0.08 + (cRoot.level / 127) * 0.22)
        border.color: Qt.rgba(cRoot.toneColor.r, cRoot.toneColor.g, cRoot.toneColor.b, 0.25 + (cRoot.level / 127) * 0.75)
        border.width: ScaleMetrics.dp(1)

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: ScaleMetrics.dp(6)
            anchors.rightMargin: ScaleMetrics.dp(6)
            spacing: ScaleMetrics.dp(4)
            layoutDirection: cRoot.alignRight ? Qt.RightToLeft : Qt.LeftToRight

            CategoryGlyph {
                Layout.preferredWidth: ScaleMetrics.dp(22)
                Layout.preferredHeight: ScaleMetrics.dp(16)
                Layout.alignment: Qt.AlignVCenter
                toneIndex: cRoot.toneIndex
                category: cRoot.waveInfo ? cRoot.waveInfo.category : "synth_wave"
                isSingleCycle: cRoot.waveInfo ? cRoot.waveInfo.is_single_cycle : true
                samples64: cRoot.waveInfo ? cRoot.waveInfo.samples_64 : null
                color: cRoot.toneColor
            }

            Column {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignVCenter
                spacing: 1

                Text {
                    text: cRoot.toneName
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(10)
                    color: cRoot.toneColor
                    horizontalAlignment: cRoot.alignRight ? Text.AlignRight : Text.AlignLeft
                    width: parent.width
                }
                Text {
                    text: cRoot.toneSub + " (" + cRoot.level + ")"
                    font.pixelSize: ScaleMetrics.sp(8)
                    font.family: Theme.fontMono
                    color: Theme.textSecondary
                    horizontalAlignment: cRoot.alignRight ? Text.AlignRight : Text.AlignLeft
                    width: parent.width
                    elide: Text.ElideRight
                }
            }
        }

        MouseArea {
            anchors.fill: parent
            onClicked: {
                Bridge.openWaveBrowser(cRoot.toneIndex + 1);
            }
        }
    }
}
