pragma ValueTypeBehavior: Copy
import QtQuick
import ".."

Item {
    id: root
    property string category: "synth_wave"
    property color color: Theme.primary
    property var samples64: null
    property bool isSingleCycle: true
    property int toneIndex: 0 // fallback shape 0=saw, 1=sqr, 2=tri, 3=sin

    implicitWidth: 24
    implicitHeight: 18

    Canvas {
        id: canvas
        anchors.fill: parent
        renderStrategy: Canvas.Immediate

        onPaint: {
            const ctx = getContext("2d");
            if (!ctx) return;
            ctx.clearRect(0, 0, width, height);

            const midY = height / 2;
            const midX = width / 2;
            const amp = height * 0.42;

            if (root.samples64 && root.samples64.length >= 64) {
                // Real sampled 64-point curve
                ctx.strokeStyle = root.color;
                ctx.lineWidth = 1.5;
                ctx.lineCap = "round";
                ctx.lineJoin = "round";
                ctx.beginPath();

                for (let i = 0; i < root.samples64.length; i++) {
                    const px = (i / (root.samples64.length - 1)) * width;
                    const py = midY - root.samples64[i] * amp;
                    if (i === 0) ctx.moveTo(px, py);
                    else ctx.lineTo(px, py);
                }
                ctx.stroke();
            } else if (root.isSingleCycle) {
                // Fallback geometric waveforms
                ctx.strokeStyle = root.color;
                ctx.lineWidth = 1.5;
                ctx.lineCap = "round";
                ctx.lineJoin = "round";
                ctx.beginPath();

                if (root.toneIndex === 0) {
                    ctx.moveTo(0, midY + amp);
                    ctx.lineTo(width / 2, midY - amp);
                    ctx.lineTo(width / 2, midY + amp);
                    ctx.lineTo(width, midY - amp);
                    ctx.lineTo(width, midY + amp);
                } else if (root.toneIndex === 1) {
                    ctx.moveTo(0, midY - amp);
                    ctx.lineTo(width * 0.25, midY - amp);
                    ctx.lineTo(width * 0.25, midY + amp);
                    ctx.lineTo(width * 0.75, midY + amp);
                    ctx.lineTo(width * 0.75, midY - amp);
                    ctx.lineTo(width, midY - amp);
                } else if (root.toneIndex === 2) {
                    ctx.moveTo(0, midY);
                    ctx.lineTo(width * 0.25, midY - amp);
                    ctx.lineTo(width * 0.75, midY + amp);
                    ctx.lineTo(width, midY);
                } else {
                    ctx.moveTo(0, midY);
                    for (let x = 0; x <= width; x += 2) {
                        const phase = (x / width) * 2.0 * Math.PI;
                        ctx.lineTo(x, midY - Math.sin(phase) * amp);
                    }
                }
                ctx.stroke();
            } else {
                // Non-single-cycle instrument category icon
                ctx.save();
                ctx.strokeStyle = root.color;
                ctx.fillStyle = root.color;
                ctx.lineWidth = 1.2;
                ctx.lineCap = "round";
                ctx.lineJoin = "round";

                switch (root.category) {
                    case "piano":
                        ctx.strokeRect(2, 2, width - 4, height - 4);
                        ctx.beginPath();
                        ctx.moveTo(2 + (width - 4) / 3, 2);
                        ctx.lineTo(2 + (width - 4) / 3, height - 2);
                        ctx.moveTo(2 + 2 * (width - 4) / 3, 2);
                        ctx.lineTo(2 + 2 * (width - 4) / 3, height - 2);
                        ctx.stroke();
                        ctx.fillRect(2 + (width - 4) / 3 - 1.5, 2, 3, (height - 4) * 0.55);
                        ctx.fillRect(2 + 2 * (width - 4) / 3 - 1.5, 2, 3, (height - 4) * 0.55);
                        break;

                    case "organ":
                        const barW = (width - 8) / 4;
                        const hts = [height * 0.8, height * 0.65, height * 0.5, height * 0.35];
                        for (let i = 0; i < 4; i++) {
                            ctx.fillRect(2 + i * (barW + 1.5), height - 2 - hts[i], barW, hts[i]);
                        }
                        break;

                    case "guitar":
                        ctx.beginPath();
                        ctx.arc(midX - 3, midY + 2, 3.5, 0, 2 * Math.PI);
                        ctx.arc(midX - 1, midY - 2, 2.5, 0, 2 * Math.PI);
                        ctx.fill();
                        ctx.beginPath();
                        ctx.moveTo(midX, midY - 3);
                        ctx.lineTo(width - 2, 2);
                        ctx.stroke();
                        break;

                    case "bass":
                        for (let i = 0; i < 4; i++) {
                            const y = 3 + i * ((height - 6) / 3);
                            ctx.beginPath();
                            ctx.moveTo(2, y);
                            ctx.lineTo(width - 2, y);
                            ctx.stroke();
                        }
                        break;

                    case "strings":
                        ctx.beginPath();
                        ctx.arc(midX - 2, 3, 1.5, 0, Math.PI * 2);
                        ctx.fill();
                        ctx.beginPath();
                        ctx.moveTo(midX - 2, 4);
                        ctx.bezierCurveTo(midX + 4, midY - 2, midX - 6, midY + 2, midX + 2, height - 4);
                        ctx.stroke();
                        ctx.beginPath();
                        ctx.arc(midX + 2, height - 3, 1.5, 0, Math.PI * 2);
                        ctx.fill();
                        break;

                    case "brass":
                        ctx.beginPath();
                        ctx.moveTo(2, midY - 1);
                        ctx.lineTo(width * 0.5, midY - 1);
                        ctx.lineTo(width - 2, 2);
                        ctx.lineTo(width - 2, height - 2);
                        ctx.lineTo(width * 0.5, midY + 1);
                        ctx.lineTo(2, midY + 1);
                        ctx.closePath();
                        ctx.stroke();
                        break;

                    case "vocal":
                        ctx.beginPath();
                        ctx.arc(midX - 2, midY, 3.5, 0, Math.PI * 2);
                        ctx.stroke();
                        ctx.beginPath();
                        ctx.arc(midX - 2, midY, 6.5, -Math.PI * 0.35, Math.PI * 0.35);
                        ctx.stroke();
                        break;

                    case "drums":
                        ctx.beginPath();
                        ctx.ellipse(midX, midY, width * 0.35, height * 0.25, 0, 0, 2 * Math.PI);
                        ctx.stroke();
                        ctx.beginPath();
                        ctx.moveTo(3, 3);
                        ctx.lineTo(width - 3, height - 3);
                        ctx.moveTo(width - 3, 3);
                        ctx.lineTo(3, height - 3);
                        ctx.stroke();
                        break;

                    case "sfx":
                        ctx.beginPath();
                        ctx.moveTo(midX, 2);
                        ctx.quadraticCurveTo(midX, midY, width - 2, midY);
                        ctx.quadraticCurveTo(midX, midY, midX, height - 2);
                        ctx.quadraticCurveTo(midX, midY, 2, midY);
                        ctx.quadraticCurveTo(midX, midY, midX, 2);
                        ctx.fill();
                        break;

                    case "synth_lead":
                        ctx.beginPath();
                        ctx.moveTo(2, height - 2);
                        ctx.lineTo(width * 0.35, height - 2);
                        ctx.lineTo(width * 0.35, 2);
                        ctx.lineTo(width * 0.65, 2);
                        ctx.lineTo(width * 0.65, height - 2);
                        ctx.lineTo(width - 2, height - 2);
                        ctx.stroke();
                        break;

                    default:
                        ctx.beginPath();
                        ctx.arc(midX, midY, Math.min(midX, midY) - 2, 0, 2 * Math.PI);
                        ctx.stroke();
                        ctx.beginPath();
                        ctx.moveTo(midX - 5, midY);
                        ctx.lineTo(midX + 5, midY);
                        ctx.moveTo(midX, midY - 5);
                        ctx.lineTo(midX, midY + 5);
                        ctx.stroke();
                        break;
                }
                ctx.restore();
            }
        }

        Component.onCompleted: requestPaint()
        Connections {
            target: root
            function onCategoryChanged() { canvas.requestPaint(); }
            function onColorChanged() { canvas.requestPaint(); }
            function onSamples64Changed() { canvas.requestPaint(); }
            function onIsSingleCycleChanged() { canvas.requestPaint(); }
        }
    }
}
