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

    property int selectedTone: 1

    // ADSR Envelope interactive parameters (0..127)
    property int envAttack: Math.round((Bridge.masterAttack - 1) / 126.0 * 127)
    property int envDecay: 45
    property int envSustain: 80
    property int envRelease: Math.round((Bridge.masterRelease - 1) / 126.0 * 127)

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: ScaleMetrics.dp(12)
        spacing: ScaleMetrics.dp(10)

        // Header: Tone Selection Tabs
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(8)

            Text {
                text: "PATCH EDIT"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(13)
                font.letterSpacing: 1.2
                color: Theme.textSecondary
            }

            Item { Layout.fillWidth: true }

            Repeater {
                model: 4
                delegate: Rectangle {
                    property int tIdx: modelData + 1
                    property bool isSel: root.selectedTone === tIdx
                    width: ScaleMetrics.dp(70)
                    height: ScaleMetrics.dp(26)
                    radius: ScaleMetrics.dp(4)
                    color: isSel ? Theme.bgCardActive : Theme.bgApp
                    border.color: isSel ? (tIdx === 1 ? Theme.tone1 : tIdx === 2 ? Theme.tone2 : tIdx === 3 ? Theme.tone3 : Theme.tone4) : Theme.borderCard
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: "TONE " + parent.tIdx
                        font.bold: parent.isSel
                        font.pixelSize: ScaleMetrics.sp(10)
                        color: parent.isSel ? Theme.textPrimary : Theme.textDim
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: root.selectedTone = parent.tIdx
                    }
                }
            }
        }

        // Main Editor Area (Filter Curve + ADSR Envelope)
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: ScaleMetrics.dp(10)

            // Left: TVF Filter Response Canvas with Draggable Cutoff & Reso Node
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: ScaleMetrics.dp(6)
                color: Theme.bgApp
                border.color: Theme.borderCard
                border.width: 1
                clip: true

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(8)
                    spacing: ScaleMetrics.dp(4)

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "TVF FILTER FREQUENCY RESPONSE"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(10)
                            color: Theme.tone2
                        }
                        Item { Layout.fillWidth: true }
                        Text {
                            text: "DRAG NODE TO ADJUST CUTOFF & RESO"
                            font.pixelSize: ScaleMetrics.sp(9)
                            color: Theme.textDim
                        }
                    }

                    Item {
                        id: filterCanvasArea
                        Layout.fillWidth: true
                        Layout.fillHeight: true

                        Canvas {
                            id: filterCanvas
                            anchors.fill: parent

                            onPaint: {
                                const ctx = getContext("2d");
                                ctx.reset();
                                const w = width;
                                const h = height;

                                // Grid lines
                                ctx.strokeStyle = "#1e293b";
                                ctx.lineWidth = 1;
                                for (let gx = 0.25; gx < 1.0; gx += 0.25) {
                                    ctx.beginPath();
                                    ctx.moveTo(gx * w, 0);
                                    ctx.lineTo(gx * w, h);
                                    ctx.stroke();
                                }
                                for (let gy = 0.25; gy < 1.0; gy += 0.25) {
                                    ctx.beginPath();
                                    ctx.moveTo(0, gy * h);
                                    ctx.lineTo(w, gy * h);
                                    ctx.stroke();
                                }

                                // Normalized Cutoff & Reso
                                const normCutoff = (Bridge.masterCutoff - 1) / 126.0;
                                const normReso = (Bridge.masterReso - 1) / 126.0;

                                // Filter Cutoff and Resonance transfer function
                                const fc = Math.max(0.001, normCutoff);
                                const Q = 0.707 + Math.pow(normReso, 1.8) * 14.0; // Thin high-Q peak

                                ctx.beginPath();
                                let first = true;
                                const step = 4;
                                let peakX = fc * w;
                                let peakY = h * 0.95;

                                for (let x = 0; x <= w; x += step) {
                                    const f = x / w;
                                    const u = f / fc;
                                    // 4-pole low-pass filter magnitude transfer function
                                    const denom = Math.sqrt(Math.pow(1 - u * u, 2) + Math.pow(u / Q, 2));
                                    const mag = 1.0 / Math.max(0.01, denom);
                                    // Decibel scaling
                                    const dB = Math.min(26.0, Math.max(-48.0, 20.0 * Math.log10(mag)));
                                    const y = h * (1.0 - (dB + 48.0) / 74.0) * 0.85 + h * 0.08;

                                    if (first) {
                                        ctx.moveTo(x, y);
                                        first = false;
                                    } else {
                                        ctx.lineTo(x, y);
                                    }

                                    // Track peak node coordinates
                                    if (Math.abs(x - fc * w) < step) {
                                        peakX = x;
                                        peakY = y;
                                    }
                                }

                                // Stroke filter response curve
                                ctx.lineWidth = 3;
                                ctx.strokeStyle = Theme.tone2;
                                ctx.stroke();

                                // Fill under curve
                                ctx.lineTo(w, h);
                                ctx.lineTo(0, h);
                                ctx.closePath();
                                ctx.fillStyle = "rgba(56, 189, 248, 0.12)";
                                ctx.fill();

                                // Draw Handle Node Point
                                ctx.beginPath();
                                ctx.arc(peakX, peakY, 6, 0, 2 * Math.PI);
                                ctx.fillStyle = Theme.tone2;
                                ctx.fill();
                                ctx.lineWidth = 2;
                                ctx.strokeStyle = "#ffffff";
                                ctx.stroke();
                            }

                            Connections {
                                target: Bridge
                                function onMasterCutoffChanged() { if (root.visible) filterCanvas.requestPaint(); }
                                function onMasterResoChanged() { if (root.visible) filterCanvas.requestPaint(); }
                            }
                        }

                        // Interactive Drag MouseArea
                        MouseArea {
                            anchors.fill: parent
                            onPositionChanged: (mouse) => {
                                if (pressed) {
                                    const normX = Math.max(0.0, Math.min(1.0, mouse.x / width));
                                    const normY = Math.max(0.0, Math.min(1.0, 1.0 - (mouse.y / height)));
                                    Bridge.setMasterCutoff(Math.round(1 + normX * 126));
                                    Bridge.setMasterReso(Math.round(1 + normY * 126));
                                }
                            }
                            onPressed: (mouse) => {
                                const normX = Math.max(0.0, Math.min(1.0, mouse.x / width));
                                const normY = Math.max(0.0, Math.min(1.0, 1.0 - (mouse.y / height)));
                                Bridge.setMasterCutoff(Math.round(1 + normX * 126));
                                Bridge.setMasterReso(Math.round(1 + normY * 126));
                            }
                        }
                    }
                }
            }

            // Right: Interactive ADSR Envelope Visualization & Controls
            Rectangle {
                Layout.preferredWidth: ScaleMetrics.dp(260)
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
                        Text {
                            text: "TVA ENVELOPE (ADSR)"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(10)
                            color: Theme.tone3
                        }
                        Item { Layout.fillWidth: true }
                        Text {
                            text: "DRAG POINTS"
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: Theme.textDim
                        }
                    }

                    // ADSR Curve Canvas
                    Item {
                        Layout.fillWidth: true
                        Layout.fillHeight: true

                        Canvas {
                            id: adsrCanvas
                            anchors.fill: parent

                            onPaint: {
                                const ctx = getContext("2d");
                                ctx.reset();
                                const w = width;
                                const h = height;

                                const normA = Math.max(0.02, root.envAttack / 127.0);
                                const normD = Math.max(0.02, root.envDecay / 127.0);
                                const normS = Math.max(0.05, root.envSustain / 127.0);
                                const normR = Math.max(0.02, root.envRelease / 127.0);

                                const xA = w * 0.05 + normA * (w * 0.28);
                                const xD = xA + normD * (w * 0.28);
                                const xS = Math.min(w * 0.75, xD + w * 0.15);
                                const xR = Math.min(w * 0.96, xS + normR * (w * 0.22));

                                const yBase = h * 0.90;
                                const yPeak = h * 0.12;
                                const ySustain = yBase - normS * (yBase - yPeak);

                                ctx.beginPath();
                                ctx.moveTo(w * 0.04, yBase);
                                ctx.lineTo(xA, yPeak);
                                ctx.lineTo(xD, ySustain);
                                ctx.lineTo(xS, ySustain);
                                ctx.lineTo(xR, yBase);

                                ctx.lineWidth = 3;
                                ctx.strokeStyle = Theme.tone3;
                                ctx.stroke();

                                // Fill
                                ctx.lineTo(w * 0.04, yBase);
                                ctx.closePath();
                                ctx.fillStyle = "rgba(16, 185, 129, 0.12)";
                                ctx.fill();

                                // Handles
                                const handles = [
                                    { x: xA, y: yPeak },
                                    { x: xD, y: ySustain },
                                    { x: xS, y: ySustain },
                                    { x: xR, y: yBase }
                                ];
                                for (let i = 0; i < handles.length; i++) {
                                    ctx.beginPath();
                                    ctx.arc(handles[i].x, handles[i].y, 5, 0, 2 * Math.PI);
                                    ctx.fillStyle = Theme.tone3;
                                    ctx.fill();
                                    ctx.lineWidth = 2;
                                    ctx.strokeStyle = "#ffffff";
                                    ctx.stroke();
                                }
                            }

                            Connections {
                                target: root
                                function onEnvAttackChanged() { adsrCanvas.requestPaint(); }
                                function onEnvDecayChanged() { adsrCanvas.requestPaint(); }
                                function onEnvSustainChanged() { adsrCanvas.requestPaint(); }
                                function onEnvReleaseChanged() { adsrCanvas.requestPaint(); }
                            }
                        }

                        // Touch interaction on ADSR nodes
                        MouseArea {
                            anchors.fill: parent
                            property int activeHandle: 0 // 1: A, 2: D, 3: S, 4: R

                            onPressed: (mouse) => {
                                const normX = mouse.x / width;
                                if (normX < 0.3) {
                                    activeHandle = 1;
                                    const val = Math.round(Math.max(1, Math.min(127, (normX / 0.3) * 127)));
                                    Bridge.setMasterAttack(val);
                                } else if (normX < 0.55) {
                                    activeHandle = 2;
                                    root.envDecay = Math.round(Math.max(1, Math.min(127, ((normX - 0.3) / 0.25) * 127)));
                                } else if (normX < 0.75) {
                                    activeHandle = 3;
                                    const normY = Math.max(0.0, Math.min(1.0, 1.0 - (mouse.y / height)));
                                    root.envSustain = Math.round(normY * 127);
                                } else {
                                    activeHandle = 4;
                                    const val = Math.round(Math.max(1, Math.min(127, ((normX - 0.75) / 0.25) * 127)));
                                    Bridge.setMasterRelease(val);
                                }
                            }

                            onPositionChanged: (mouse) => {
                                if (pressed) {
                                    const normX = mouse.x / width;
                                    const normY = Math.max(0.0, Math.min(1.0, 1.0 - (mouse.y / height)));
                                    if (activeHandle === 1) {
                                        const val = Math.round(Math.max(1, Math.min(127, (normX / 0.3) * 127)));
                                        Bridge.setMasterAttack(val);
                                    } else if (activeHandle === 2) {
                                        root.envDecay = Math.round(Math.max(1, Math.min(127, Math.abs(normX - 0.3) / 0.25 * 127)));
                                    } else if (activeHandle === 3) {
                                        root.envSustain = Math.round(normY * 127);
                                    } else if (activeHandle === 4) {
                                        const val = Math.round(Math.max(1, Math.min(127, (normX - 0.75) / 0.25 * 127)));
                                        Bridge.setMasterRelease(val);
                                    }
                                }
                            }
                        }
                    }

                    // ADSR Numeric Labels
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "A: " + root.envAttack; font.bold: true; font.pixelSize: ScaleMetrics.sp(9); color: Theme.textPrimary; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter }
                        Text { text: "D: " + root.envDecay; font.bold: true; font.pixelSize: ScaleMetrics.sp(9); color: Theme.textPrimary; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter }
                        Text { text: "S: " + root.envSustain; font.bold: true; font.pixelSize: ScaleMetrics.sp(9); color: Theme.textPrimary; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter }
                        Text { text: "R: " + root.envRelease; font.bold: true; font.pixelSize: ScaleMetrics.sp(9); color: Theme.textPrimary; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter }
                    }
                }
            }
        }
    }
}
