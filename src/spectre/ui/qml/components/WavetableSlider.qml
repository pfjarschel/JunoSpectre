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
        anchors.margins: ScaleMetrics.dp(16)
        spacing: ScaleMetrics.dp(12)

        // Title and readout
        RowLayout {
            Layout.fillWidth: true
            Text {
                text: "1D LINEAR WAVETABLE MORPH SCANNER"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(13)
                color: Theme.textPrimary
            }
            Item { Layout.fillWidth: true }
            Text {
                text: "W: " + Bridge.wavetablePos.toFixed(3)
                font.bold: true
                font.family: Theme.fontMono
                font.pixelSize: ScaleMetrics.sp(12)
                color: Theme.tone3
            }
        }

        // Live Morphing Waveform Visualizer Screen
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: ScaleMetrics.dp(6)
            color: "#07090d"
            border.color: Theme.borderCard
            border.width: 1
            clip: true

            // Grid lines
            Rectangle {
                anchors.centerIn: parent
                width: parent.width
                height: 1
                color: "#1e293b"
            }

            // Real-time canvas drawing the morphed wave
            Canvas {
                id: waveCanvas
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(8)
                renderStrategy: Canvas.Immediate

                Component.onCompleted: requestPaint()
                onVisibleChanged: if (visible) requestPaint()
                onWidthChanged: requestPaint()
                onHeightChanged: requestPaint()

                // Re-render when slider moves
                Connections {
                    target: Bridge
                    function onWavetablePosChanged() {
                        if (root.visible) waveCanvas.requestPaint();
                    }
                }

                onPaint: {
                    var ctx = getContext("2d")
                    if (!ctx) return
                    ctx.clearRect(0, 0, width, height)

                    var w = Bridge.wavetablePos
                    var cy = height / 2
                    var amp = height * 0.38
                    var step = 2
                    var pts = []

                    // Generate morphed waveform cycle:
                    // Tone 1: Saw, Tone 2: Square, Tone 3: Triangle, Tone 4: Sine
                    for (var x = 0; x <= width; x += step) {
                        var phase = (x / width) * 2.0 * Math.PI // 0 .. 2pi
                        var normPhase = (phase / (2.0 * Math.PI)) // 0 .. 1

                        // Base waveforms
                        var saw = 2.0 * (normPhase - Math.floor(normPhase + 0.5))
                        var sqr = normPhase < 0.5 ? 1.0 : -1.0
                        var tri = 2.0 * Math.abs(2.0 * (normPhase - Math.floor(normPhase + 0.5))) - 1.0
                        var sin = Math.sin(phase)

                        // Interpolated morph based on W
                        var sample = 0.0
                        if (w <= 1.0 / 3.0) {
                            var t = w * 3.0
                            sample = (1.0 - t) * saw + t * sqr
                        } else if (w <= 2.0 / 3.0) {
                            var t = (w - 1.0 / 3.0) * 3.0
                            sample = (1.0 - t) * sqr + t * tri
                        } else {
                            var t = (w - 2.0 / 3.0) * 3.0
                            sample = (1.0 - t) * tri + t * sin
                        }

                        pts.push({ x: x, y: cy - sample * amp })
                    }

                    if (pts.length < 2) return

                    // Pass 1: Wide ambient glow
                    ctx.beginPath()
                    ctx.lineWidth = 6
                    ctx.strokeStyle = "rgba(14, 165, 233, 0.35)"
                    for (var i = 0; i < pts.length; i++) {
                        if (i === 0) ctx.moveTo(pts[i].x, pts[i].y)
                        else ctx.lineTo(pts[i].x, pts[i].y)
                    }
                    ctx.stroke()

                    // Pass 2: Crisp bright core wave
                    ctx.beginPath()
                    ctx.lineWidth = 2.5
                    ctx.strokeStyle = "#38bdf8"
                    for (var j = 0; j < pts.length; j++) {
                        if (j === 0) ctx.moveTo(pts[j].x, pts[j].y)
                        else ctx.lineTo(pts[j].x, pts[j].y)
                    }
                    ctx.stroke()
                }
            }

            // Current sound stage label
            Text {
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.margins: ScaleMetrics.dp(8)
                text: {
                    var w = Bridge.wavetablePos
                    if (w < 0.33) return "MORPHING: TONE 1 (SAW) ➔ TONE 2 (SQUARE)"
                    if (w < 0.67) return "MORPHING: TONE 2 (SQUARE) ➔ TONE 3 (TRIANGLE)"
                    return "MORPHING: TONE 3 (TRIANGLE) ➔ TONE 4 (SINE)"
                }
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(10)
                font.family: Theme.fontMono
                color: Theme.textSecondary
            }
        }

        // Node preview labels & mini wave icons above slider track
        RowLayout {
            Layout.fillWidth: true

            WaveNodeBadge {
                toneNumber: 1
                toneName: "TONE 1"
                waveType: "SAW"
                toneColor: Theme.tone1
                level: Bridge.tone1Level
            }
            Item { Layout.fillWidth: true }
            WaveNodeBadge {
                toneNumber: 2
                toneName: "TONE 2"
                waveType: "SQUARE"
                toneColor: Theme.tone2
                level: Bridge.tone2Level
            }
            Item { Layout.fillWidth: true }
            WaveNodeBadge {
                toneNumber: 3
                toneName: "TONE 3"
                waveType: "TRIANGLE"
                toneColor: Theme.tone3
                level: Bridge.tone3Level
            }
            Item { Layout.fillWidth: true }
            WaveNodeBadge {
                toneNumber: 4
                toneName: "TONE 4"
                waveType: "SINE"
                toneColor: Theme.tone4
                level: Bridge.tone4Level
            }
        }

        // Horizontal Slider Track
        Rectangle {
            id: track
            Layout.fillWidth: true
            height: ScaleMetrics.dp(40)
            radius: ScaleMetrics.dp(20)
            color: Theme.bgApp
            border.color: Theme.borderActive
            border.width: 1

            // 3 Color Gradient Zones
            Row {
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(3)
                spacing: ScaleMetrics.dp(3)

                // Zone 1: T1 -> T2
                Rectangle {
                    width: (parent.width - ScaleMetrics.dp(6)) / 3
                    height: parent.height
                    radius: ScaleMetrics.dp(16)
                    gradient: Gradient {
                        orientation: Gradient.Horizontal
                        GradientStop { position: 0.0; color: Qt.rgba(Theme.tone1.r, Theme.tone1.g, Theme.tone1.b, 0.35) }
                        GradientStop { position: 1.0; color: Qt.rgba(Theme.tone2.r, Theme.tone2.g, Theme.tone2.b, 0.35) }
                    }
                }

                // Zone 2: T2 -> T3
                Rectangle {
                    width: (parent.width - ScaleMetrics.dp(6)) / 3
                    height: parent.height
                    radius: ScaleMetrics.dp(16)
                    gradient: Gradient {
                        orientation: Gradient.Horizontal
                        GradientStop { position: 0.0; color: Qt.rgba(Theme.tone2.r, Theme.tone2.g, Theme.tone2.b, 0.35) }
                        GradientStop { position: 1.0; color: Qt.rgba(Theme.tone3.r, Theme.tone3.g, Theme.tone3.b, 0.35) }
                    }
                }

                // Zone 3: T3 -> T4
                Rectangle {
                    width: (parent.width - ScaleMetrics.dp(6)) / 3
                    height: parent.height
                    radius: ScaleMetrics.dp(16)
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
                width: ScaleMetrics.dp(52)
                height: ScaleMetrics.dp(52)
                radius: width / 2
                color: "#1e293b"
                border.color: Theme.tone3
                border.width: ScaleMetrics.dp(3)

                Rectangle {
                    anchors.centerIn: parent
                    width: ScaleMetrics.dp(16)
                    height: ScaleMetrics.dp(16)
                    radius: width / 2
                    color: Theme.textPrimary
                }
            }

            // Mouse and Touch Area on Track
            MouseArea {
                anchors.fill: parent
                preventStealing: true

                function updatePos(mouse) {
                    var usableW = track.width - handle.width
                    var norm = Math.max(0.0, Math.min(1.0, (mouse.x - handle.width / 2) / usableW))
                    Bridge.setWavetablePos(norm)
                }

                onPressed: (mouse) => updatePos(mouse)
                onPositionChanged: (mouse) => {
                    if (pressed) {
                        updatePos(mouse)
                    }
                }
            }
        }
    }

    // Node badge component with mini waveform preview
    component WaveNodeBadge: Row {
        id: bRoot
        property int toneNumber: 1
        property string toneName: "TONE"
        property string waveType: "SAW"
        property color toneColor: Theme.tone1
        property int level: 0

        spacing: ScaleMetrics.dp(6)

        // Miniature Waveform Glyph
        Canvas {
            id: miniCanvas
            width: ScaleMetrics.dp(24)
            height: ScaleMetrics.dp(18)
            anchors.verticalCenter: parent.verticalCenter
            renderStrategy: Canvas.Immediate

            onPaint: {
                const ctx = getContext("2d");
                if (!ctx) return;
                ctx.clearRect(0, 0, width, height);
                ctx.strokeStyle = bRoot.toneColor;
                ctx.lineWidth = 1.5;
                ctx.lineCap = "round";
                ctx.lineJoin = "round";
                ctx.beginPath();
                const midY = height / 2;
                const amp = height * 0.42;

                const wt = bRoot.waveType.toUpperCase();
                if (wt === "SAW") {
                    ctx.moveTo(0, midY + amp);
                    ctx.lineTo(width / 2, midY - amp);
                    ctx.lineTo(width / 2, midY + amp);
                    ctx.lineTo(width, midY - amp);
                    ctx.lineTo(width, midY + amp);
                } else if (wt === "SQUARE") {
                    ctx.moveTo(0, midY - amp);
                    ctx.lineTo(width * 0.25, midY - amp);
                    ctx.lineTo(width * 0.25, midY + amp);
                    ctx.lineTo(width * 0.75, midY + amp);
                    ctx.lineTo(width * 0.75, midY - amp);
                    ctx.lineTo(width, midY - amp);
                } else if (wt === "TRIANGLE") {
                    ctx.moveTo(0, midY);
                    ctx.lineTo(width * 0.25, midY - amp);
                    ctx.lineTo(width * 0.75, midY + amp);
                    ctx.lineTo(width, midY);
                } else if (wt === "SINE") {
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
                target: bRoot
                function onToneColorChanged() { miniCanvas.requestPaint(); }
                function onWaveTypeChanged() { miniCanvas.requestPaint(); }
            }
        }

        Column {
            anchors.verticalCenter: parent.verticalCenter
            spacing: ScaleMetrics.dp(2)
            Text {
                text: bRoot.toneName + " (" + bRoot.waveType + ")"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(11)
                color: bRoot.toneColor
            }
            Text {
                text: "LVL: " + bRoot.level
                font.pixelSize: ScaleMetrics.sp(9)
                font.family: Theme.fontMono
                color: bRoot.level > 0 ? bRoot.toneColor : Theme.textMuted
            }
        }
    }
}
