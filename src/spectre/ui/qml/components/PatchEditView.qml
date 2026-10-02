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

                                const cx = Math.max(0.1, Math.min(0.9, normCutoff)) * w;
                                const peakY = (1.0 - (0.4 + normReso * 0.45)) * h;
                                const basePassY = 0.65 * h;

                                // Filter Curve Path
                                ctx.beginPath();
                                ctx.moveTo(0, basePassY);
                                ctx.lineTo(cx * 0.7, basePassY);
                                ctx.quadraticCurveTo(cx, peakY, cx + (w - cx) * 0.2, h * 0.9);
                                ctx.lineTo(w, h * 0.95);

                                // Stroke
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
                                ctx.arc(cx, peakY, 7, 0, 2 * Math.PI);
                                ctx.fillStyle = Theme.tone2;
                                ctx.fill();
                                ctx.lineWidth = 2;
                                ctx.strokeStyle = "#ffffff";
                                ctx.stroke();
                            }

                            Connections {
                                target: Bridge
                                function onMasterCutoffChanged() { filterCanvas.requestPaint(); }
                                function onMasterResoChanged() { filterCanvas.requestPaint(); }
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
                        }
                    }
                }
            }

            // Right: ADSR Envelope Visualization & Controls
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

                    Text {
                        text: "TVA AMPLITUDE ENVELOPE (ADSR)"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(10)
                        color: Theme.tone3
                    }

                    // ADSR Curve Canvas
                    Canvas {
                        id: adsrCanvas
                        Layout.fillWidth: true
                        Layout.fillHeight: true

                        onPaint: {
                            const ctx = getContext("2d");
                            ctx.reset();
                            const w = width;
                            const h = height;

                            // ADSR curve
                            const p0 = { x: 0, y: h * 0.9 };
                            const pAttack = { x: w * 0.2, y: h * 0.15 };
                            const pDecay = { x: w * 0.5, y: h * 0.45 };
                            const pSustain = { x: w * 0.75, y: h * 0.45 };
                            const pRelease = { x: w * 0.95, y: h * 0.9 };

                            ctx.beginPath();
                            ctx.moveTo(p0.x, p0.y);
                            ctx.lineTo(pAttack.x, pAttack.y);
                            ctx.lineTo(pDecay.x, pDecay.y);
                            ctx.lineTo(pSustain.x, pSustain.y);
                            ctx.lineTo(pRelease.x, pRelease.y);

                            ctx.lineWidth = 3;
                            ctx.strokeStyle = Theme.tone3;
                            ctx.stroke();

                            // Fill
                            ctx.lineTo(w, h);
                            ctx.lineTo(0, h);
                            ctx.closePath();
                            ctx.fillStyle = "rgba(16, 185, 129, 0.12)";
                            ctx.fill();
                        }
                    }

                    // ADSR Labels
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "A: 15"; font.pixelSize: ScaleMetrics.sp(9); color: Theme.textDim; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter }
                        Text { text: "D: 45"; font.pixelSize: ScaleMetrics.sp(9); color: Theme.textDim; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter }
                        Text { text: "S: 80"; font.pixelSize: ScaleMetrics.sp(9); color: Theme.textDim; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter }
                        Text { text: "R: 30"; font.pixelSize: ScaleMetrics.sp(9); color: Theme.textDim; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter }
                    }
                }
            }
        }
    }
}
