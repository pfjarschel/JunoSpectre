import QtQuick
import QtQuick.Layouts
import QtQuick.Shapes
import JunoSpectre
import ".."

Item {
    id: root
    clip: true

    // Visual background container
    Rectangle {
        id: bg
        anchors.fill: parent
        color: Theme.bgCard
        radius: ScaleMetrics.dp(8)
        border.color: Theme.borderCard
        border.width: 1

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

                const l1 = Bridge.tone1Level / 127.0;
                const l2 = Bridge.tone2Level / 127.0;
                const l3 = Bridge.tone3Level / 127.0;
                const l4 = Bridge.tone4Level / 127.0;
                const sum = l1 + l2 + l3 + l4;
                if (sum < 0.01) return;

                const w = width;
                const h = height;
                const cy = h / 2;
                const amp = h * 0.32;
                const normSum = Math.max(0.5, sum);
                const step = 4;

                ctx.beginPath();
                let first = true;

                // Render 2 full wave cycles across the pad
                const cycles = 2.0;
                for (let x = 0; x <= w; x += step) {
                    const phase = (x / w) * cycles * 2.0 * Math.PI;
                    const normPhase = ((phase / (2.0 * Math.PI)) % 1.0 + 1.0) % 1.0;

                    // Base waveforms: Saw, Square, Triangle, Sine
                    const saw = 2.0 * (normPhase - Math.floor(normPhase + 0.5));
                    const sqr = normPhase < 0.5 ? 0.85 : -0.85;
                    const tri = 2.0 * Math.abs(2.0 * (normPhase - Math.floor(normPhase + 0.5))) - 1.0;
                    const sin = Math.sin(phase);

                    // Weighted morph composite
                    const sample = (l1 * saw + l2 * sqr + l3 * tri + l4 * sin) / normSum;
                    const y = cy - sample * amp;

                    if (first) {
                        ctx.moveTo(x, y);
                        first = false;
                    } else {
                        ctx.lineTo(x, y);
                    }
                }

                ctx.lineWidth = ScaleMetrics.dp(2);
                ctx.strokeStyle = Theme.primary;
                ctx.lineCap = "round";
                ctx.lineJoin = "round";
                ctx.stroke();
            }

            Component.onCompleted: requestPaint()
            onVisibleChanged: if (visible) requestPaint()
            onWidthChanged: requestPaint()
            onHeightChanged: requestPaint()

            // Repaint only when tone levels change while on VECTOR screen
            Connections {
                target: Bridge
                function onToneLevelsChanged() {
                    if (root.visible) vectorWaveCanvas.requestPaint();
                }
            }
        }

        // Grid lines
        Shape {
            anchors.fill: parent
            asynchronous: true

            // Horizontal center line
            ShapePath {
                strokeColor: Theme.borderCard
                strokeWidth: 1
                strokeStyle: ShapePath.DashLine
                dashPattern: [4, 4]
                startX: 0
                startY: bg.height / 2
                PathLine { x: bg.width; y: bg.height / 2 }
            }

            // Vertical center line
            ShapePath {
                strokeColor: Theme.borderCard
                strokeWidth: 1
                strokeStyle: ShapePath.DashLine
                dashPattern: [4, 4]
                startX: bg.width / 2
                startY: 0
                PathLine { x: bg.width / 2; y: bg.height }
            }
        }

        // Corner 1: Tone 1 (NW)
        CornerGlowBadge {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.margins: ScaleMetrics.dp(10)
            toneName: "TONE 1"
            toneSub: "NORTH-WEST"
            waveType: "saw"
            toneColor: Theme.tone1
            level: Bridge.tone1Level
        }

        // Corner 2: Tone 2 (NE)
        CornerGlowBadge {
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.margins: ScaleMetrics.dp(10)
            toneName: "TONE 2"
            toneSub: "NORTH-EAST"
            waveType: "square"
            toneColor: Theme.tone2
            level: Bridge.tone2Level
            alignRight: true
        }

        // Corner 3: Tone 3 (SW)
        CornerGlowBadge {
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.margins: ScaleMetrics.dp(10)
            toneName: "TONE 3"
            toneSub: "SOUTH-WEST"
            waveType: "triangle"
            toneColor: Theme.tone3
            level: Bridge.tone3Level
        }

        // Corner 4: Tone 4 (SE)
        CornerGlowBadge {
            anchors.bottom: parent.bottom
            anchors.right: parent.right
            anchors.margins: ScaleMetrics.dp(10)
            toneName: "TONE 4"
            toneSub: "SOUTH-EAST"
            waveType: "sine"
            toneColor: Theme.tone4
            level: Bridge.tone4Level
            alignRight: true
        }

        // Touch Cursor Puck
        Item {
            id: puck
            // Pixel mapping: X 0..1 -> 0..width, Y 0..1 -> height..0
            x: Math.max(0, Math.min(bg.width - width, Bridge.vectorX * bg.width - width / 2))
            y: Math.max(0, Math.min(bg.height - height, (1.0 - Bridge.vectorY) * bg.height - height / 2))
            width: ScaleMetrics.dp(48)
            height: ScaleMetrics.dp(48)

            // Outer glowing halo
            Rectangle {
                anchors.centerIn: parent
                width: parent.width * 1.5
                height: parent.height * 1.5
                radius: width / 2
                color: Theme.primary
                opacity: 0.22
            }

            // Middle ring
            Rectangle {
                anchors.centerIn: parent
                width: parent.width
                height: parent.height
                radius: width / 2
                color: "#182642"
                border.color: Theme.primary
                border.width: ScaleMetrics.dp(2)

                // Center core point
                Rectangle {
                    anchors.centerIn: parent
                    width: ScaleMetrics.dp(12)
                    height: ScaleMetrics.dp(12)
                    radius: width / 2
                    color: Theme.textPrimary
                }
            }

            // Coordinate readout badge floating above puck
            Rectangle {
                anchors.bottom: parent.top
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottomMargin: ScaleMetrics.dp(6)
                width: ScaleMetrics.dp(82)
                height: ScaleMetrics.dp(20)
                radius: ScaleMetrics.dp(4)
                color: "#0f172a"
                border.color: Theme.borderCard
                border.width: 1

                Text {
                    anchors.centerIn: parent
                    text: Bridge.vectorX.toFixed(2) + ", " + Bridge.vectorY.toFixed(2)
                    font.pixelSize: ScaleMetrics.sp(10)
                    font.family: Theme.fontMono
                    font.bold: true
                    color: Theme.textPrimary
                }
            }
        }

        // Gravitational Attractor Pulsar (Visible in ORBIT mode)
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
            opacity: 0.85

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

        // Mouse and Touch Interaction Area
        MouseArea {
            anchors.fill: parent
            preventStealing: true

            property real startX: 0
            property real startY: 0
            property real startTime: 0

            onPressed: (mouse) => {
                startX = mouse.x
                startY = mouse.y
                startTime = Date.now()

                var normX = Math.max(0.0, Math.min(1.0, mouse.x / bg.width))
                var normY = Math.max(0.0, Math.min(1.0, 1.0 - (mouse.y / bg.height)))
                if (Bridge.automator === "circle") {
                    Bridge.setOrbitAttractor(normX, normY)
                } else {
                    Bridge.setCoordinates(normX, normY)
                }
            }

            onPositionChanged: (mouse) => {
                if (pressed) {
                    var normX = Math.max(0.0, Math.min(1.0, mouse.x / bg.width))
                    var normY = Math.max(0.0, Math.min(1.0, 1.0 - (mouse.y / bg.height)))
                    if (Bridge.automator === "circle") {
                        // In ORBIT mode, dragging moves the attractor (the Sun), and the body follows!
                        Bridge.setOrbitAttractor(normX, normY)
                    } else {
                        Bridge.setCoordinates(normX, normY)
                    }
                }
            }

            onReleased: (mouse) => {
                var now = Date.now()
                var dt = Math.max(16, now - startTime) / 1000.0
                var totalDist = Math.hypot(mouse.x - startX, mouse.y - startY)

                var normX = Math.max(0.0, Math.min(1.0, mouse.x / bg.width))
                var normY = Math.max(0.0, Math.min(1.0, 1.0 - (mouse.y / bg.height)))

                if (Bridge.automator === "circle") {
                    // If released with a fast swipe/flick gesture, give momentum impulse to body
                    if (totalDist >= ScaleMetrics.dp(24) && dt < 0.35) {
                        var dx = (mouse.x - startX) / bg.width
                        var dy = -(mouse.y - startY) / bg.height
                        var vx = (dx / dt) * 0.35
                        var vy = (dy / dt) * 0.35
                        Bridge.fling(Bridge.vectorX, Bridge.vectorY, vx, vy)
                    } else {
                        Bridge.setOrbitAttractor(normX, normY)
                    }
                }
            }
        }
    }

    // Corner badge component with reactive glow and mini waveform glyph
    component CornerGlowBadge: Rectangle {
        id: cRoot
        property string toneName: "TONE"
        property string toneSub: "CORNER"
        property string waveType: "saw"
        property color toneColor: Theme.tone1
        property int level: 0
        property bool alignRight: false

        width: ScaleMetrics.dp(112)
        height: ScaleMetrics.dp(44)
        radius: ScaleMetrics.dp(6)
        color: Qt.rgba(cRoot.toneColor.r, cRoot.toneColor.g, cRoot.toneColor.b, 0.08 + (cRoot.level / 127) * 0.22)
        border.color: Qt.rgba(cRoot.toneColor.r, cRoot.toneColor.g, cRoot.toneColor.b, 0.25 + (cRoot.level / 127) * 0.75)
        border.width: ScaleMetrics.dp(1)

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: ScaleMetrics.dp(8)
            anchors.rightMargin: ScaleMetrics.dp(8)
            spacing: ScaleMetrics.dp(6)
            layoutDirection: cRoot.alignRight ? Qt.RightToLeft : Qt.LeftToRight

            // Miniature Waveform Glyph
            Canvas {
                id: miniWaveCanvas
                Layout.preferredWidth: ScaleMetrics.dp(22)
                Layout.preferredHeight: ScaleMetrics.dp(16)
                Layout.alignment: Qt.AlignVCenter
                renderStrategy: Canvas.Immediate

                onPaint: {
                    const ctx = getContext("2d");
                    if (!ctx) return;
                    ctx.clearRect(0, 0, width, height);
                    ctx.strokeStyle = cRoot.toneColor;
                    ctx.lineWidth = 1.5;
                    ctx.lineCap = "round";
                    ctx.lineJoin = "round";
                    ctx.beginPath();
                    const midY = height / 2;
                    const amp = height * 0.42;

                    if (cRoot.waveType === "saw") {
                        // 2 Saw cycles
                        ctx.moveTo(0, midY + amp);
                        ctx.lineTo(width / 2, midY - amp);
                        ctx.lineTo(width / 2, midY + amp);
                        ctx.lineTo(width, midY - amp);
                        ctx.lineTo(width, midY + amp);
                    } else if (cRoot.waveType === "square") {
                        // 1.5 Square cycles
                        ctx.moveTo(0, midY - amp);
                        ctx.lineTo(width * 0.25, midY - amp);
                        ctx.lineTo(width * 0.25, midY + amp);
                        ctx.lineTo(width * 0.75, midY + amp);
                        ctx.lineTo(width * 0.75, midY - amp);
                        ctx.lineTo(width, midY - amp);
                    } else if (cRoot.waveType === "triangle") {
                        // 1 Triangle cycle
                        ctx.moveTo(0, midY);
                        ctx.lineTo(width * 0.25, midY - amp);
                        ctx.lineTo(width * 0.75, midY + amp);
                        ctx.lineTo(width, midY);
                    } else if (cRoot.waveType === "sine") {
                        // 1 Sine cycle
                        ctx.moveTo(0, midY);
                        for (let x = 0; x <= width; x += 2) {
                            const phase = (x / width) * 2.0 * Math.PI;
                            ctx.lineTo(x, midY - Math.sin(phase) * amp);
                        }
                    }
                    ctx.stroke();
                }

                Component.onCompleted: requestPaint()
                Connections {
                    target: cRoot
                    function onToneColorChanged() { miniWaveCanvas.requestPaint(); }
                    function onWaveTypeChanged() { miniWaveCanvas.requestPaint(); }
                }
            }

            Column {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignVCenter
                spacing: ScaleMetrics.dp(2)

                Text {
                    text: cRoot.toneName
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(11)
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
                }
            }
        }
    }
}
