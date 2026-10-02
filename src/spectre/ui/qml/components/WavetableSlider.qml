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

    property bool is3DView: true

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: ScaleMetrics.dp(16)
        spacing: ScaleMetrics.dp(12)

        // Title, 2D/3D Mode Selector, and Readout
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(10)

            Text {
                text: "1D LINEAR WAVETABLE MORPH SCANNER"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(13)
                color: Theme.textPrimary
            }

            Item { Layout.fillWidth: true }

            // 2D / 3D Mode Selector Pill
            Rectangle {
                width: ScaleMetrics.dp(150)
                height: ScaleMetrics.dp(24)
                radius: ScaleMetrics.dp(12)
                color: Theme.bgApp
                border.color: Theme.borderCard
                border.width: 1

                Row {
                    anchors.fill: parent
                    anchors.margins: 2

                    // 2D Button
                    Rectangle {
                        width: (parent.width - 2) / 2
                        height: parent.height
                        radius: ScaleMetrics.dp(10)
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
                                root.is3DView = false
                                waveCanvas.requestPaint()
                            }
                        }
                    }

                    // 3D Button
                    Rectangle {
                        width: (parent.width - 2) / 2
                        height: parent.height
                        radius: ScaleMetrics.dp(10)
                        color: root.is3DView ? Theme.bgCardActive : "transparent"
                        border.color: root.is3DView ? Theme.tone1 : "transparent"
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: "3D WATERFALL"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: root.is3DView ? Theme.textPrimary : Theme.textDim
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                root.is3DView = true
                                waveCanvas.requestPaint()
                            }
                        }
                    }
                }
            }

            Text {
                text: "W: " + Bridge.wavetablePos.toFixed(3)
                font.bold: true
                font.family: Theme.fontMono
                font.pixelSize: ScaleMetrics.sp(12)
                color: Theme.tone3
            }
        }

        // Live Morphing Waveform Visualizer Screen (2D Scope / 3D Waterfall)
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

            // Real-time canvas drawing either 2D or 3D waveform
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

                    var curW = Bridge.wavetablePos

                    // Helper: compute wave sample at phase and morph position z
                    function sampleAt(phase, z) {
                        var normPhase = ((phase / (2.0 * Math.PI)) % 1.0 + 1.0) % 1.0
                        var saw = 2.0 * (normPhase - Math.floor(normPhase + 0.5))
                        var sqr = normPhase < 0.5 ? 0.9 : -0.9
                        var tri = 2.0 * Math.abs(2.0 * (normPhase - Math.floor(normPhase + 0.5))) - 1.0
                        var sin = Math.sin(phase)

                        if (z <= 1.0 / 3.0) {
                            var t = z * 3.0
                            return (1.0 - t) * saw + t * sqr
                        } else if (z <= 2.0 / 3.0) {
                            var t = (z - 1.0 / 3.0) * 3.0
                            return (1.0 - t) * sqr + t * tri
                        } else {
                            var t = (z - 2.0 / 3.0) * 3.0
                            return (1.0 - t) * tri + t * sin
                        }
                    }

                    if (!root.is3DView) {
                        // ==========================================
                        // 2D HIGH-PRECISION OSCILLOSCOPE VIEW
                        // ==========================================
                        var cy = height / 2
                        var amp = height * 0.38
                        var step = 2
                        var pts = []

                        for (var x = 0; x <= width; x += step) {
                            var phase = (x / width) * 2.0 * Math.PI
                            var s = sampleAt(phase, curW)
                            pts.push({ x: x, y: cy - s * amp })
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

                    } else {
                        // ==========================================
                        // 3D SERUM-STYLE ISOMETRIC WATERFALL VIEW
                        // ==========================================
                        var numSlices = 16
                        var dxDepth = width * 0.22
                        var dyDepth = height * 0.52
                        var amp3d = height * 0.14
                        var step3d = 3

                        function computeSlice(z) {
                            var wSlice = width * 0.72 * (1.0 - z * 0.12)
                            var x0 = width * 0.05 + z * dxDepth
                            var yBase = height * 0.78 - z * dyDepth

                            var slicePts = []
                            for (var sx = 0; sx <= wSlice; sx += step3d) {
                                var p = (sx / wSlice) * 2.0 * Math.PI
                                var smp = sampleAt(p, z)
                                slicePts.push({ x: x0 + sx, y: yBase - smp * amp3d })
                            }
                            return {
                                z: z,
                                pts: slicePts,
                                x0: x0,
                                yBase: yBase,
                                wSlice: wSlice
                            }
                        }

                        var activeSliceData = computeSlice(curW)

                        function drawWireSlice(slice) {
                            var slicePts = slice.pts
                            var z = slice.z
                            if (slicePts.length < 2) return

                            ctx.beginPath()
                            ctx.lineWidth = 1.8
                            ctx.lineCap = "round"
                            ctx.lineJoin = "round"
                            var alpha = 0.36 + (1.0 - z) * 0.12
                            ctx.strokeStyle = "rgba(56, 189, 248, " + alpha.toFixed(2) + ")"
                            for (var wIdx = 0; wIdx < slicePts.length; wIdx++) {
                                if (wIdx === 0) ctx.moveTo(slicePts[wIdx].x, slicePts[wIdx].y)
                                else ctx.lineTo(slicePts[wIdx].x, slicePts[wIdx].y)
                            }
                            ctx.stroke()
                        }

                        // Render wireframe slices from back (z = 1) to front (z = 0)
                        for (var k = numSlices - 1; k >= 0; k--) {
                            var zSlice = k / (numSlices - 1)
                            if (Math.abs(zSlice - curW) > 0.035) {
                                var wireSlice = computeSlice(zSlice)
                                drawWireSlice(wireSlice)
                            }
                        }

                        // ==========================================
                        // DEDICATED TOP OVERLAY PASS FOR ACTIVE HIGHLIGHT
                        // Guarantees the glowing active waveform is never obscured
                        // by foreground wave slices when curW is in the back
                        // ==========================================
                        if (activeSliceData && activeSliceData.pts.length > 1) {
                            var aPts = activeSliceData.pts
                            var ax0 = activeSliceData.x0
                            var ayBase = activeSliceData.yBase
                            var aw = activeSliceData.wSlice

                            // Pass 1: Neon bloom glow
                            ctx.beginPath()
                            ctx.lineWidth = 5.5
                            ctx.strokeStyle = "rgba(56, 189, 248, 0.65)"
                            ctx.lineCap = "round"
                            ctx.lineJoin = "round"
                            for (var g = 0; g < aPts.length; g++) {
                                if (g === 0) ctx.moveTo(aPts[g].x, aPts[g].y)
                                else ctx.lineTo(aPts[g].x, aPts[g].y)
                            }
                            ctx.stroke()

                            // Pass 2: White-hot sharp core
                            ctx.beginPath()
                            ctx.lineWidth = 2.4
                            ctx.strokeStyle = "#ffffff"
                            ctx.lineCap = "round"
                            ctx.lineJoin = "round"
                            for (var c = 0; c < aPts.length; c++) {
                                if (c === 0) ctx.moveTo(aPts[c].x, aPts[c].y)
                                else ctx.lineTo(aPts[c].x, aPts[c].y)
                            }
                            ctx.stroke()

                            // Active slice depth marker cursor on left edge
                            ctx.fillStyle = "#38bdf8"
                            ctx.fillRect(ax0 - 5, ayBase - 7, 4, 14)
                        }

                    }
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
