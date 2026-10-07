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

    property int chorusType: Bridge.chorusType
    property int chorusRate: Bridge.chorusRate
    property int chorusDepth: Bridge.chorusDepth
    property int chorusPreDelay: Bridge.chorusPreDelay
    property int chorusFeedback: Bridge.chorusFeedback
    property int chorusToReverb: Bridge.chorusToReverb
    property int chorusLevel: Bridge.chorusLevel

    property int reverbType: Bridge.reverbType
    property int reverbTime: Bridge.reverbTime
    property int reverbDamp: Bridge.reverbDamp
    property int reverbPreDelay: Bridge.reverbPreDelay
    property int reverbDiffusion: Bridge.reverbDiffusion
    property int reverbTone: Bridge.reverbTone
    property int reverbLevel: Bridge.reverbLevel

    property bool eqSwitch: Bridge.eqSwitch
    property int eqLowGain: Bridge.eqLowGain
    property int eqLowFreq: Bridge.eqLowFreq
    property int eqMidGain: Bridge.eqMidGain
    property int eqMidFreq: Bridge.eqMidFreq
    property real eqMidQ: Bridge.eqMidQ
    property int eqHighGain: Bridge.eqHighGain
    property int eqHighFreq: Bridge.eqHighFreq
    property int eqMasterLevel: Bridge.eqMasterLevel

    property int draggedEqBand: -1 // 0: Low, 1: Mid, 2: High

    readonly property var midFreqs: [200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000]

    onEqSwitchChanged: eqCanvas.requestPaint()
    onEqLowGainChanged: eqCanvas.requestPaint()
    onEqLowFreqChanged: eqCanvas.requestPaint()
    onEqMidGainChanged: eqCanvas.requestPaint()
    onEqMidFreqChanged: eqCanvas.requestPaint()
    onEqMidQChanged: eqCanvas.requestPaint()
    onEqHighGainChanged: eqCanvas.requestPaint()
    onEqHighFreqChanged: eqCanvas.requestPaint()

    function setLowFreq(f) {
        var val = f <= 300 ? 200 : 400;
        Bridge.setMasterEqParam("lowFreq", val);
        eqCanvas.requestPaint();
    }

    function setMidFreq(f) {
        var best = root.midFreqs[0];
        var minDiff = Math.abs(f - best);
        for (var i = 1; i < root.midFreqs.length; i++) {
            var d = Math.abs(f - root.midFreqs[i]);
            if (d < minDiff) {
                minDiff = d;
                best = root.midFreqs[i];
            }
        }
        Bridge.setMasterEqParam("midFreq", best);
        eqCanvas.requestPaint();
    }

    function setHighFreq(f) {
        var val = 4000;
        if (f <= 3000) val = 2000;
        else if (f <= 6000) val = 4000;
        else val = 8000;
        Bridge.setMasterEqParam("highFreq", val);
        eqCanvas.requestPaint();
    }

    Connections {
        target: Bridge
        function onMasterEqChanged() {
            eqCanvas.requestPaint();
        }
    }

    function freqToX(freq, w) {
        var minF = 20.0, maxF = 20000.0;
        var norm = (Math.log10(freq) - Math.log10(minF)) / (Math.log10(maxF) - Math.log10(minF));
        return Math.max(0, Math.min(w, norm * w));
    }

    function xToFreq(x, w) {
        var minF = 20.0, maxF = 20000.0;
        var norm = Math.max(0.0, Math.min(1.0, x / w));
        return Math.round(Math.pow(10, Math.log10(minF) + norm * (Math.log10(maxF) - Math.log10(minF))));
    }

    function calcDbAtFreq(freq) {
        var lowEffect = 1.0 / (1.0 + Math.pow(freq / Math.max(1, root.eqLowFreq), 2));
        var lowDb = root.eqLowGain * lowEffect;

        var highEffect = Math.pow(freq / Math.max(1, root.eqHighFreq), 2) / (1.0 + Math.pow(freq / Math.max(1, root.eqHighFreq), 2));
        var highDb = root.eqHighGain * highEffect;

        var ratio = freq / Math.max(1, root.eqMidFreq);
        var midEffect = 1.0 / (1.0 + Math.pow(root.eqMidQ * (ratio - 1.0 / ratio), 2));
        var midDb = root.eqMidGain * midEffect;

        return lowDb + midDb + highDb;
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
                color: "#a855f7"
            }
            Text {
                Layout.fillWidth: true
                text: "MASTER FX (CHORUS, REVERB & 3-BAND MASTER PARAMETRIC EQ)"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(12)
                font.letterSpacing: 1.2
                color: Theme.textPrimary
                elide: Text.ElideRight
            }
            Rectangle {
                height: ScaleMetrics.dp(18)
                Layout.preferredWidth: Math.min(choTarget.implicitWidth + ScaleMetrics.dp(12), ScaleMetrics.dp(100))
                Layout.maximumWidth: ScaleMetrics.dp(100)
                radius: 3
                color: "#0d2838"
                border.color: "#38bdf8"
                border.width: 1
                clip: true
                Text {
                    id: choTarget
                    anchors.fill: parent
                    anchors.leftMargin: ScaleMetrics.dp(6)
                    anchors.rightMargin: ScaleMetrics.dp(6)
                    verticalAlignment: Text.AlignVCenter
                    horizontalAlignment: Text.AlignHCenter
                    text: Bridge.choEditTargetLabel
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(7)
                    font.family: Theme.fontMono
                    color: "#38bdf8"
                    elide: Text.ElideRight
                }
            }
            Rectangle {
                height: ScaleMetrics.dp(18)
                Layout.preferredWidth: Math.min(revTarget.implicitWidth + ScaleMetrics.dp(12), ScaleMetrics.dp(100))
                Layout.maximumWidth: ScaleMetrics.dp(100)
                radius: 3
                color: "#1c0d28"
                border.color: "#a855f7"
                border.width: 1
                clip: true
                Text {
                    id: revTarget
                    anchors.fill: parent
                    anchors.leftMargin: ScaleMetrics.dp(6)
                    anchors.rightMargin: ScaleMetrics.dp(6)
                    verticalAlignment: Text.AlignVCenter
                    horizontalAlignment: Text.AlignHCenter
                    text: Bridge.revEditTargetLabel
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(7)
                    font.family: Theme.fontMono
                    color: "#a855f7"
                    elide: Text.ElideRight
                }
            }
        }

        // 3 Cards: Chorus, Reverb, 3-Band Parametric EQ
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: ScaleMetrics.dp(8)

            // Card 1: Master Chorus (~275dp)
            Rectangle {
                Layout.preferredWidth: ScaleMetrics.dp(275)
                Layout.fillHeight: true
                radius: ScaleMetrics.dp(6)
                color: Theme.bgApp
                border.color: Theme.borderCard
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(8)
                    spacing: ScaleMetrics.dp(5)

                    // Card Header
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: ScaleMetrics.dp(6)
                        Rectangle { width: 6; height: 6; radius: 3; color: "#38bdf8" }
                        Text { text: "MASTER CHORUS"; font.bold: true; font.pixelSize: ScaleMetrics.sp(10); color: "#38bdf8" }
                        Item { Layout.fillWidth: true }
                        Rectangle {
                            height: ScaleMetrics.dp(18)
                            width: ScaleMetrics.dp(48)
                            radius: 3
                            color: root.chorusType === 0 ? "#2b1b1b" : "#0d2838"
                            border.color: root.chorusType === 0 ? Theme.recording : "#38bdf8"
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: root.chorusType === 0 ? "OFF" : "ON"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(8)
                                color: root.chorusType === 0 ? Theme.recording : "#38bdf8"
                            }
                        }
                    }

                    // Chorus Type Selector Chips
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Repeater {
                            model: ["OFF", "CHORUS", "DELAY", "GM2 CHO"]
                            delegate: Rectangle {
                                Layout.fillWidth: true
                                height: ScaleMetrics.dp(24)
                                radius: 3
                                color: root.chorusType === index ? Theme.bgCardActive : "#10141d"
                                border.color: root.chorusType === index ? "#38bdf8" : Theme.borderCard
                                border.width: 1
                                Text {
                                    anchors.centerIn: parent
                                    text: modelData
                                    font.bold: root.chorusType === index
                                    font.pixelSize: ScaleMetrics.sp(8)
                                    color: root.chorusType === index ? "#38bdf8" : Theme.textDim
                                }
                                MouseArea { anchors.fill: parent; onClicked: Bridge.setChorusParam("type", index) }
                            }
                        }
                    }

                    // Chorus Output Routing Selector Chips
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: ScaleMetrics.dp(4)
                        Text {
                            text: "OUTPUT:"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: Theme.textDim
                        }
                        Item { Layout.fillWidth: true }
                        Repeater {
                            model: ["MAIN", "REV", "MAIN+REV"]
                            delegate: Rectangle {
                                Layout.preferredWidth: ScaleMetrics.dp(60)
                                height: ScaleMetrics.dp(20)
                                radius: 3
                                color: root.chorusToReverb === index ? "#0284c7" : "#10141d"
                                border.color: root.chorusToReverb === index ? "#38bdf8" : Theme.borderCard
                                border.width: 1
                                Text {
                                    anchors.centerIn: parent
                                    text: modelData
                                    font.bold: root.chorusToReverb === index
                                    font.pixelSize: ScaleMetrics.sp(7)
                                    color: root.chorusToReverb === index ? "#ffffff" : Theme.textDim
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: Bridge.setChorusParam("toReverb", index)
                                }
                            }
                        }
                    }

                    // 5 Full Scaled Chorus Sliders
                    FxSlider { Layout.fillWidth: true; Layout.fillHeight: true; label: "RATE"; val: root.chorusRate; accent: "#38bdf8"; isDimmed: root.chorusType === 0; onMoved: (v) => Bridge.setChorusParam("rate", v) }
                    FxSlider { Layout.fillWidth: true; Layout.fillHeight: true; label: "DEPTH"; val: root.chorusDepth; accent: "#38bdf8"; isDimmed: root.chorusType === 0; onMoved: (v) => Bridge.setChorusParam("depth", v) }
                    FxSlider { Layout.fillWidth: true; Layout.fillHeight: true; label: "PRE-DELAY"; val: root.chorusPreDelay; unitText: "ms"; accent: "#38bdf8"; isDimmed: root.chorusType === 0; onMoved: (v) => Bridge.setChorusParam("preDelay", v) }
                    FxSlider { Layout.fillWidth: true; Layout.fillHeight: true; label: "FEEDBACK"; val: root.chorusFeedback; unitText: "%"; accent: "#38bdf8"; isDimmed: root.chorusType === 0; onMoved: (v) => Bridge.setChorusParam("feedback", v) }
                    FxSlider { Layout.fillWidth: true; Layout.fillHeight: true; label: "LEVEL"; val: root.chorusLevel; accent: "#38bdf8"; isDimmed: root.chorusType === 0; onMoved: (v) => Bridge.setChorusParam("level", v) }

                    // Routing status
                    Rectangle {
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(22)
                        radius: 3
                        color: "#10141d"
                        border.color: Theme.borderCard
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: root.chorusType === 0 ? "CHORUS BYPASSED (DRY ROUTED)" : ("ROUTING: TONES ➔ CHORUS ➔ " + (root.chorusToReverb === 0 ? "MAIN" : root.chorusToReverb === 1 ? "REV" : "MAIN + REV"))
                            font.family: Theme.fontMono
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(7)
                            color: root.chorusType === 0 ? Theme.textDim : "#38bdf8"
                        }
                    }
                }
            }

            // Card 2: Master Reverb (~275dp)
            Rectangle {
                Layout.preferredWidth: ScaleMetrics.dp(275)
                Layout.fillHeight: true
                radius: ScaleMetrics.dp(6)
                color: Theme.bgApp
                border.color: Theme.borderCard
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(8)
                    spacing: ScaleMetrics.dp(5)

                    // Card Header
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: ScaleMetrics.dp(6)
                        Rectangle { width: 6; height: 6; radius: 3; color: "#a855f7" }
                        Text { text: "MASTER REVERB"; font.bold: true; font.pixelSize: ScaleMetrics.sp(10); color: "#a855f7" }
                        Item { Layout.fillWidth: true }
                        Rectangle {
                            height: ScaleMetrics.dp(18)
                            width: ScaleMetrics.dp(48)
                            radius: 3
                            color: root.reverbType === 0 ? "#2b1b1b" : "#231535"
                            border.color: root.reverbType === 0 ? Theme.recording : "#a855f7"
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: root.reverbType === 0 ? "OFF" : "ON"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(8)
                                color: root.reverbType === 0 ? Theme.recording : "#a855f7"
                            }
                        }
                    }

                    // Reverb Type Selector Chips
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Repeater {
                            model: ["OFF", "REVERB", "ROOM", "HALL", "PLATE", "GM2"]
                            delegate: Rectangle {
                                Layout.fillWidth: true
                                height: ScaleMetrics.dp(24)
                                radius: 3
                                color: root.reverbType === index ? Theme.bgCardActive : "#10141d"
                                border.color: root.reverbType === index ? "#a855f7" : Theme.borderCard
                                border.width: 1
                                Text {
                                    anchors.centerIn: parent
                                    text: modelData
                                    font.bold: root.reverbType === index
                                    font.pixelSize: ScaleMetrics.sp(8)
                                    color: root.reverbType === index ? "#a855f7" : Theme.textDim
                                }
                                MouseArea { anchors.fill: parent; onClicked: Bridge.setReverbParam("type", index) }
                            }
                        }
                    }

                    // 6 Full Scaled Reverb Sliders
                    FxSlider { Layout.fillWidth: true; Layout.fillHeight: true; label: "TIME"; val: root.reverbTime; unitText: "s"; accent: "#a855f7"; isDimmed: root.reverbType === 0; onMoved: (v) => Bridge.setReverbParam("time", v) }
                    FxSlider { Layout.fillWidth: true; Layout.fillHeight: true; label: "HF DAMP"; val: root.reverbDamp; accent: "#a855f7"; isDimmed: root.reverbType === 0; onMoved: (v) => Bridge.setReverbParam("damp", v) }
                    FxSlider { Layout.fillWidth: true; Layout.fillHeight: true; label: "PRE-DELAY"; val: root.reverbPreDelay; unitText: "ms"; accent: "#a855f7"; isDimmed: root.reverbType === 0; onMoved: (v) => Bridge.setReverbParam("preDelay", v) }
                    FxSlider { Layout.fillWidth: true; Layout.fillHeight: true; label: "DIFFUSION"; val: root.reverbDiffusion; accent: "#a855f7"; isDimmed: root.reverbType === 0; onMoved: (v) => Bridge.setReverbParam("diffusion", v) }
                    FxSlider { Layout.fillWidth: true; Layout.fillHeight: true; label: "LOW CUT / TONE"; val: root.reverbTone; accent: "#a855f7"; isDimmed: root.reverbType === 0; onMoved: (v) => Bridge.setReverbParam("tone", v) }
                    FxSlider { Layout.fillWidth: true; Layout.fillHeight: true; label: "LEVEL"; val: root.reverbLevel; accent: "#a855f7"; isDimmed: root.reverbType === 0; onMoved: (v) => Bridge.setReverbParam("level", v) }

                    // Routing status
                    Rectangle {
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(22)
                        radius: 3
                        color: "#10141d"
                        border.color: Theme.borderCard
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: root.reverbType === 0 ? "REVERB BYPASSED (DRY ROUTED)" : "ROUTING: BUS ➔ REVERB ➔ MASTER OUT"
                            font.family: Theme.fontMono
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(7)
                            color: root.reverbType === 0 ? Theme.textDim : "#a855f7"
                        }
                    }
                }
            }

            // Card 3: 3-Band Parametric Master EQ
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: ScaleMetrics.dp(6)
                color: Theme.bgApp
                border.color: Theme.borderCard
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(8)
                    spacing: ScaleMetrics.dp(6)

                    // Header & Flat Reset Button
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: ScaleMetrics.dp(6)
                        Rectangle { width: 6; height: 6; radius: 3; color: root.eqSwitch ? "#10b981" : Theme.recording }
                        Text { text: "3-BAND MASTER PARAMETRIC EQ"; font.bold: true; font.pixelSize: ScaleMetrics.sp(10); color: root.eqSwitch ? "#10b981" : Theme.recording }
                        Rectangle {
                            height: ScaleMetrics.dp(18)
                            width: ScaleMetrics.dp(44)
                            radius: 3
                            color: !root.eqSwitch ? "#2b1b1b" : "#0d3828"
                            border.color: !root.eqSwitch ? Theme.recording : "#10b981"
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: !root.eqSwitch ? "OFF" : "ON"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(8)
                                color: !root.eqSwitch ? Theme.recording : "#10b981"
                            }
                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    Bridge.setMasterEqParam("switch", !root.eqSwitch);
                                    eqCanvas.requestPaint();
                                }
                            }
                        }
                        Item { Layout.fillWidth: true }
                        Rectangle {
                            height: ScaleMetrics.dp(20)
                            width: ScaleMetrics.dp(70)
                            radius: 3
                            color: "#10141d"
                            border.color: Theme.borderCard
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: "FLAT / RESET"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(7)
                                color: Theme.textSecondary
                            }
                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    Bridge.setMasterEqParam("lowGain", 0);
                                    Bridge.setMasterEqParam("midGain", 0);
                                    Bridge.setMasterEqParam("highGain", 0);
                                    Bridge.setMasterEqParam("lowFreq", 400);
                                    Bridge.setMasterEqParam("midFreq", 1250);
                                    Bridge.setMasterEqParam("midQ", 1.0);
                                    Bridge.setMasterEqParam("highFreq", 4000);
                                    Bridge.setMasterEqParam("masterLevel", 100);
                                    eqCanvas.requestPaint();
                                }
                            }
                        }
                    }

                    // Expanded Interactive Parametric EQ Canvas (~95dp)
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: ScaleMetrics.dp(95)
                        radius: 4
                        color: "#080b11"
                        border.color: Theme.borderCard
                        border.width: 1
                        clip: true

                        Canvas {
                            id: eqCanvas
                            anchors.fill: parent
                            anchors.margins: ScaleMetrics.dp(6)

                            onPaint: {
                                var ctx = getContext("2d");
                                ctx.reset();
                                var w = width, h = height;
                                var midY = h * 0.5;

                                // Faint Frequency Grid Lines (100 Hz, 1 kHz, 10 kHz)
                                ctx.strokeStyle = "#162032";
                                ctx.lineWidth = 1;
                                ctx.setLineDash([2, 3]);

                                var x100 = root.freqToX(100, w);
                                var x1k = root.freqToX(1000, w);
                                var x10k = root.freqToX(10000, w);

                                ctx.beginPath();
                                ctx.moveTo(x100, 0); ctx.lineTo(x100, h);
                                ctx.moveTo(x1k, 0); ctx.lineTo(x1k, h);
                                ctx.moveTo(x10k, 0); ctx.lineTo(x10k, h);
                                ctx.stroke();

                                // Faint dB Grid Lines (+12 dB, -12 dB)
                                var yPlus12 = midY - (12.0 / 15.0) * (midY - 14);
                                var yMinus12 = midY - (-12.0 / 15.0) * (midY - 14);

                                ctx.beginPath();
                                ctx.moveTo(0, yPlus12); ctx.lineTo(w, yPlus12);
                                ctx.moveTo(0, yMinus12); ctx.lineTo(w, yMinus12);
                                ctx.stroke();

                                // Solid Center 0 dB Line
                                ctx.strokeStyle = "#1e293b";
                                ctx.setLineDash([]);
                                ctx.lineWidth = 1.5;
                                ctx.beginPath();
                                ctx.moveTo(0, midY); ctx.lineTo(w, midY);
                                ctx.stroke();

                                // Frequency & dB labels
                                ctx.font = "8px monospace";
                                ctx.fillStyle = "#475569";
                                ctx.fillText("+12", 4, yPlus12 - 2);
                                ctx.fillText("0dB", 4, midY - 2);
                                ctx.fillText("-12", 4, yMinus12 + 8);
                                ctx.fillText("100Hz", x100 - 12, h - 3);
                                ctx.fillText("1kHz", x1k - 10, h - 3);
                                ctx.fillText("10kHz", x10k - 12, h - 3);

                                // Compute Parametric Curve Points
                                var step = 3;
                                var pts = [];
                                for (var x = 0; x <= w; x += step) {
                                    var f = root.xToFreq(x, w);
                                    var db = root.calcDbAtFreq(f);
                                    var y = midY - (db / 15.0) * (midY - 14);
                                    pts.push({ x: x, y: y });
                                }

                                // Area Fill to Midline
                                ctx.fillStyle = Qt.rgba(0.06, 0.73, 0.51, 0.16);
                                ctx.beginPath();
                                ctx.moveTo(0, midY);
                                for (var i = 0; i < pts.length; i++) {
                                    ctx.lineTo(pts[i].x, pts[i].y);
                                }
                                ctx.lineTo(w, midY);
                                ctx.closePath();
                                ctx.fill();

                                // Bright Curve Stroke
                                ctx.strokeStyle = "#10b981";
                                ctx.lineWidth = 2.5;
                                ctx.lineCap = "round";
                                ctx.lineJoin = "round";
                                ctx.beginPath();
                                for (var j = 0; j < pts.length; j++) {
                                    if (j === 0) ctx.moveTo(pts[j].x, pts[j].y);
                                    else ctx.lineTo(pts[j].x, pts[j].y);
                                }
                                ctx.stroke();

                                // Control Handles for LOW, MID, HIGH (Color-Coded)
                                var bands = [
                                    { label: "LOW", freq: root.eqLowFreq, gain: root.eqLowGain, color: "#38bdf8" },
                                    { label: "MID", freq: root.eqMidFreq, gain: root.eqMidGain, color: "#10b981" },
                                    { label: "HIGH", freq: root.eqHighFreq, gain: root.eqHighGain, color: "#fbbf24" }
                                ];

                                for (var b = 0; b < bands.length; b++) {
                                    var bInfo = bands[b];
                                    var bx = root.freqToX(bInfo.freq, w);
                                    var by = midY - (root.calcDbAtFreq(bInfo.freq) / 15.0) * (midY - 14);
                                    var isDragged = (root.draggedEqBand === b);

                                    if (isDragged) {
                                        ctx.fillStyle = Qt.rgba(0.06, 0.73, 0.51, 0.3);
                                        ctx.beginPath();
                                        ctx.arc(bx, by, 14, 0, Math.PI * 2);
                                        ctx.fill();

                                        ctx.strokeStyle = bInfo.color;
                                        ctx.lineWidth = 2;
                                        ctx.beginPath();
                                        ctx.arc(bx, by, 8, 0, Math.PI * 2);
                                        ctx.stroke();

                                        ctx.fillStyle = "#ffffff";
                                        ctx.beginPath();
                                        ctx.arc(bx, by, 4, 0, Math.PI * 2);
                                        ctx.fill();

                                        // HUD readout badge
                                        var hud = bInfo.label + ": " + (bInfo.gain > 0 ? "+" + bInfo.gain : bInfo.gain) + " dB @ " +
                                            (bInfo.freq >= 1000 ? (bInfo.freq / 1000.0).toFixed(1) + "k" : bInfo.freq) + "Hz";
                                        ctx.font = "bold 9px monospace";
                                        var tw = ctx.measureText(hud).width;
                                        var badgeX = Math.max(4, Math.min(w - tw - 12, bx - tw * 0.5));
                                        var badgeY = Math.max(16, by - 16);

                                        ctx.fillStyle = "#0c131f";
                                        ctx.fillRect(badgeX - 4, badgeY - 10, tw + 8, 16);
                                        ctx.strokeStyle = bInfo.color;
                                        ctx.lineWidth = 1;
                                        ctx.strokeRect(badgeX - 4, badgeY - 10, tw + 8, 16);

                                        ctx.fillStyle = bInfo.color;
                                        ctx.fillText(hud, badgeX, badgeY + 2);
                                    } else {
                                        ctx.fillStyle = bInfo.color;
                                        ctx.beginPath();
                                        ctx.arc(bx, by, 5, 0, Math.PI * 2);
                                        ctx.fill();

                                        ctx.fillStyle = "#080b11";
                                        ctx.beginPath();
                                        ctx.arc(bx, by, 2.5, 0, Math.PI * 2);
                                        ctx.fill();

                                        ctx.fillStyle = bInfo.color;
                                        ctx.font = "bold 8px monospace";
                                        ctx.fillText(bInfo.label, bx - 8, by - 8);
                                    }
                                }
                            }
                        }

                        // Touch Draggable Area on Canvas
                        MouseArea {
                            anchors.fill: parent
                            onPressed: (mouse) => {
                                var w = width;
                                var h = height;
                                var midY = h * 0.5;

                                var b0x = root.freqToX(root.eqLowFreq, w);
                                var b0y = midY - (root.calcDbAtFreq(root.eqLowFreq) / 15.0) * (midY - 14);

                                var b1x = root.freqToX(root.eqMidFreq, w);
                                var b1y = midY - (root.calcDbAtFreq(root.eqMidFreq) / 15.0) * (midY - 14);

                                var b2x = root.freqToX(root.eqHighFreq, w);
                                var b2y = midY - (root.calcDbAtFreq(root.eqHighFreq) / 15.0) * (midY - 14);

                                var d0 = Math.hypot(mouse.x - b0x, mouse.y - b0y);
                                var d1 = Math.hypot(mouse.x - b1x, mouse.y - b1y);
                                var d2 = Math.hypot(mouse.x - b2x, mouse.y - b2y);

                                var hitRadius = ScaleMetrics.dp(36);
                                var best = -1;
                                var minD = hitRadius;

                                if (d0 < minD) { minD = d0; best = 0; }
                                if (d1 < minD) { minD = d1; best = 1; }
                                if (d2 < minD) { minD = d2; best = 2; }

                                root.draggedEqBand = best;
                                eqCanvas.requestPaint();
                            }

                            onPositionChanged: (mouse) => {
                                if (pressed && root.draggedEqBand >= 0) {
                                    var h = height;
                                    var midY = h * 0.5;
                                    var newG = Math.round(((midY - mouse.y) / (midY - 14)) * 15.0);
                                    newG = Math.max(-15, Math.min(15, newG));
                                    var newF = root.xToFreq(mouse.x, width);

                                    if (root.draggedEqBand === 0) {
                                        Bridge.setMasterEqParam("lowGain", newG);
                                        root.setLowFreq(newF);
                                    } else if (root.draggedEqBand === 1) {
                                        Bridge.setMasterEqParam("midGain", newG);
                                        root.setMidFreq(newF);
                                    } else if (root.draggedEqBand === 2) {
                                        Bridge.setMasterEqParam("highGain", newG);
                                        root.setHighFreq(newF);
                                    }
                                    eqCanvas.requestPaint();
                                }
                            }

                            onReleased: {
                                root.draggedEqBand = -1;
                                eqCanvas.requestPaint();
                            }
                            onCanceled: {
                                root.draggedEqBand = -1;
                                eqCanvas.requestPaint();
                            }
                        }
                    }

                    // 3 Band Control Sections: LOW, MID, HIGH (Stacked Cards with Full-Width Sliders)
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: ScaleMetrics.dp(5)

                        // LOW Band Card
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: ScaleMetrics.dp(64)
                            radius: ScaleMetrics.dp(4)
                            color: "#10141d"
                            border.color: Theme.borderCard
                            border.width: 1

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: ScaleMetrics.dp(5)
                                spacing: ScaleMetrics.dp(3)

                                // Header row
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: ScaleMetrics.dp(4)
                                    Rectangle { width: 6; height: 6; radius: 3; color: "#38bdf8" }
                                    Text { text: "LOW SHELF"; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: "#38bdf8" }
                                    Item { Layout.fillWidth: true }
                                    Text { text: "200 / 400 Hz"; font.family: Theme.fontMono; font.pixelSize: ScaleMetrics.sp(7); color: Theme.textDim }
                                }

                                // Low Freq Discrete Chips
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: ScaleMetrics.dp(4)

                                    Text {
                                        text: "FREQ:"
                                        font.bold: true
                                        font.pixelSize: ScaleMetrics.sp(8)
                                        color: Theme.textDim
                                    }

                                    Item { Layout.fillWidth: true }

                                    Repeater {
                                        model: [
                                            { label: "200 Hz", val: 200 },
                                            { label: "400 Hz", val: 400 }
                                        ]
                                        delegate: Rectangle {
                                            Layout.preferredWidth: ScaleMetrics.dp(70)
                                            height: ScaleMetrics.dp(20)
                                            radius: 3
                                            property bool isSelected: (root.eqLowFreq <= 300 && modelData.val === 200) || (root.eqLowFreq > 300 && modelData.val === 400)
                                            color: isSelected ? "#0284c7" : "#080b11"
                                            border.color: isSelected ? "#38bdf8" : Theme.borderCard
                                            border.width: 1
                                            Text {
                                                anchors.centerIn: parent
                                                text: modelData.label
                                                font.pixelSize: ScaleMetrics.sp(7)
                                                font.bold: parent.isSelected
                                                color: parent.isSelected ? "#ffffff" : Theme.textDim
                                            }
                                            MouseArea {
                                                anchors.fill: parent
                                                onClicked: root.setLowFreq(modelData.val)
                                            }
                                        }
                                    }
                                }

                                // Low Gain Slider (-15 .. +15 dB)
                                EqGainSlider {
                                    Layout.fillWidth: true
                                    label: "LOW GAIN"
                                    gainVal: root.eqLowGain
                                    accent: "#38bdf8"
                                    onMoved: (g) => { Bridge.setMasterEqParam("lowGain", g); eqCanvas.requestPaint(); }
                                }
                            }
                        }

                        // MID Band Card (Parametric Frequency + Q + Gain)
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: ScaleMetrics.dp(92)
                            radius: ScaleMetrics.dp(4)
                            color: "#10141d"
                            border.color: Theme.borderCard
                            border.width: 1

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: ScaleMetrics.dp(5)
                                spacing: ScaleMetrics.dp(3)

                                // Header row
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: ScaleMetrics.dp(4)
                                    Rectangle { width: 6; height: 6; radius: 3; color: "#10b981" }
                                    Text { text: "MID PARAMETRIC"; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: "#10b981" }
                                    Item { Layout.fillWidth: true }
                                    Text { text: "18 DISCRETE STEPS (200..8000 Hz)"; font.family: Theme.fontMono; font.pixelSize: ScaleMetrics.sp(7); color: Theme.textDim }
                                }

                                // Mid Freq Slider (snapped to 18 discrete steps 200..8000 Hz)
                                EqFreqSlider {
                                    Layout.fillWidth: true
                                    label: "MID FREQ"
                                    minFreq: 200
                                    maxFreq: 8000
                                    freqVal: root.eqMidFreq
                                    accent: "#10b981"
                                    onMoved: (f) => root.setMidFreq(f)
                                }

                                // Mid Gain Slider (-15 .. +15 dB)
                                EqGainSlider {
                                    Layout.fillWidth: true
                                    label: "MID GAIN"
                                    gainVal: root.eqMidGain
                                    accent: "#10b981"
                                    onMoved: (g) => { Bridge.setMasterEqParam("midGain", g); eqCanvas.requestPaint(); }
                                }

                                // Q Bandwidth Chips (8 discrete steps: 0.5, 0.7, 1.0, 1.4, 2.0, 4.0, 8.0, 16.0)
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 2

                                    Text {
                                        text: "Q:"
                                        font.bold: true
                                        font.pixelSize: ScaleMetrics.sp(8)
                                        color: Theme.textDim
                                    }

                                    Item { Layout.fillWidth: true }

                                    Repeater {
                                        model: [0.5, 0.7, 1.0, 1.4, 2.0, 4.0, 8.0, 16.0]
                                        delegate: Rectangle {
                                            Layout.fillWidth: true
                                            height: ScaleMetrics.dp(18)
                                            radius: 2
                                            property bool isSelected: Math.abs(root.eqMidQ - modelData) < 0.05
                                            color: isSelected ? "#10b981" : "#080b11"
                                            border.color: isSelected ? "#10b981" : Theme.borderCard
                                            border.width: 1
                                            Text {
                                                anchors.centerIn: parent
                                                text: modelData >= 10 ? modelData.toFixed(0) : modelData.toFixed(1)
                                                font.pixelSize: ScaleMetrics.sp(7)
                                                font.bold: parent.isSelected
                                                color: parent.isSelected ? "#000000" : Theme.textDim
                                            }
                                            MouseArea {
                                                anchors.fill: parent
                                                onClicked: {
                                                    Bridge.setMasterEqParam("midQ", modelData);
                                                    eqCanvas.requestPaint();
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        // HIGH Band Card
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: ScaleMetrics.dp(64)
                            radius: ScaleMetrics.dp(4)
                            color: "#10141d"
                            border.color: Theme.borderCard
                            border.width: 1

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: ScaleMetrics.dp(5)
                                spacing: ScaleMetrics.dp(3)

                                // Header row
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: ScaleMetrics.dp(4)
                                    Rectangle { width: 6; height: 6; radius: 3; color: "#fbbf24" }
                                    Text { text: "HIGH SHELF"; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: "#fbbf24" }
                                    Item { Layout.fillWidth: true }
                                    Text { text: "2.0 / 4.0 / 8.0 kHz"; font.family: Theme.fontMono; font.pixelSize: ScaleMetrics.sp(7); color: Theme.textDim }
                                }

                                // High Freq Discrete Chips
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: ScaleMetrics.dp(4)

                                    Text {
                                        text: "FREQ:"
                                        font.bold: true
                                        font.pixelSize: ScaleMetrics.sp(8)
                                        color: Theme.textDim
                                    }

                                    Item { Layout.fillWidth: true }

                                    Repeater {
                                        model: [
                                            { label: "2 kHz", val: 2000 },
                                            { label: "4 kHz", val: 4000 },
                                            { label: "8 kHz", val: 8000 }
                                        ]
                                        delegate: Rectangle {
                                            Layout.preferredWidth: ScaleMetrics.dp(50)
                                            height: ScaleMetrics.dp(20)
                                            radius: 3
                                            property bool isSelected: (root.eqHighFreq <= 3000 && modelData.val === 2000) ||
                                                                      (root.eqHighFreq > 3000 && root.eqHighFreq <= 6000 && modelData.val === 4000) ||
                                                                      (root.eqHighFreq > 6000 && modelData.val === 8000)
                                            color: isSelected ? "#d97706" : "#080b11"
                                            border.color: isSelected ? "#fbbf24" : Theme.borderCard
                                            border.width: 1
                                            Text {
                                                anchors.centerIn: parent
                                                text: modelData.label
                                                font.pixelSize: ScaleMetrics.sp(7)
                                                font.bold: parent.isSelected
                                                color: parent.isSelected ? "#ffffff" : Theme.textDim
                                            }
                                            MouseArea {
                                                anchors.fill: parent
                                                onClicked: root.setHighFreq(modelData.val)
                                            }
                                        }
                                    }
                                }

                                // High Gain Slider (-15 .. +15 dB)
                                EqGainSlider {
                                    Layout.fillWidth: true
                                    label: "HIGH GAIN"
                                    gainVal: root.eqHighGain
                                    accent: "#fbbf24"
                                    onMoved: (g) => { Bridge.setMasterEqParam("highGain", g); eqCanvas.requestPaint(); }
                                }
                            }
                        }
                    }

                    // Bottom EQ Master Level
                    FxSlider {
                        Layout.fillWidth: true
                        Layout.preferredHeight: ScaleMetrics.dp(32)
                        label: "EQ MASTER LEVEL"
                        val: root.eqMasterLevel
                        accent: "#10b981"
                        onMoved: (v) => Bridge.setMasterEqParam("masterLevel", v)
                    }
                }
            }
        }
    }

    // Reusable Scaled FX Slider Component
    component FxSlider: Rectangle {
        id: fs
        property string label: "PARAM"
        property int val: 50
        property int minVal: 0
        property int maxVal: 127
        property string unitText: ""
        property color accent: Theme.primary
        property bool isDimmed: false
        signal moved(int v)

        height: ScaleMetrics.dp(38)
        radius: 4
        color: "#10141d"
        border.color: Theme.borderCard
        border.width: 1
        opacity: isDimmed ? 0.35 : 1.0

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(5)
            spacing: 2

            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: fs.label
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: Theme.textSecondary
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                Text {
                    text: fs.val.toString() + (fs.unitText !== "" ? " " + fs.unitText : "")
                    font.family: Theme.fontMono
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(9)
                    color: fs.accent
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 3
                color: "#080b11"
                border.color: Theme.borderCard
                border.width: 1

                Rectangle {
                    x: 0; y: 0
                    width: parent.width * Math.max(0.0, Math.min(1.0, (fs.val - fs.minVal) / Math.max(1, fs.maxVal - fs.minVal)))
                    height: parent.height
                    radius: 3
                    color: fs.accent
                    opacity: 0.38
                }

                function updateVal(mouseX) {
                    var norm = Math.max(0.0, Math.min(1.0, mouseX / width));
                    var v = Math.round(fs.minVal + norm * (fs.maxVal - fs.minVal));
                    fs.moved(v);
                }

                MouseArea {
                    anchors.fill: parent
                    enabled: !fs.isDimmed
                    onPositionChanged: (mouse) => {
                        if (pressed) parent.updateVal(mouse.x);
                    }
                    onPressed: (mouse) => {
                        parent.updateVal(mouse.x);
                    }
                }
            }
        }
    }

    // Reusable Logarithmic Frequency Slider Component
    component EqFreqSlider: Rectangle {
        id: efs
        property string label: "FREQ"
        property int freqVal: 1000
        property int minFreq: 100
        property int maxFreq: 10000
        property color accent: "#10b981"
        signal moved(int f)

        implicitWidth: ScaleMetrics.dp(160)
        implicitHeight: ScaleMetrics.dp(22)
        Layout.fillWidth: true
        height: ScaleMetrics.dp(22)
        radius: 3
        color: "#080b11"
        border.color: Theme.borderCard
        border.width: 1

        function getNorm() {
            var lMin = Math.log10(efs.minFreq);
            var lMax = Math.log10(efs.maxFreq);
            var lCur = Math.log10(Math.max(efs.minFreq, Math.min(efs.maxFreq, efs.freqVal)));
            return Math.max(0.0, Math.min(1.0, (lCur - lMin) / (lMax - lMin)));
        }

        // Fill track
        Rectangle {
            x: 0; y: 0
            width: parent.width * efs.getNorm()
            height: parent.height
            radius: 2
            color: efs.accent
            opacity: 0.32
        }

        // Slider Handle Indicator Line
        Rectangle {
            x: Math.max(0, Math.min(parent.width - 2, parent.width * efs.getNorm() - 1))
            y: 0
            width: 2
            height: parent.height
            color: efs.accent
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: ScaleMetrics.dp(8)
            anchors.rightMargin: ScaleMetrics.dp(8)

            Text {
                text: efs.label
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(8)
                color: Theme.textDim
            }

            Item { Layout.fillWidth: true }

            Text {
                text: efs.freqVal >= 1000 ? (efs.freqVal / 1000.0).toFixed(1) + " kHz" : efs.freqVal + " Hz"
                font.family: Theme.fontMono
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(9)
                color: efs.accent
            }
        }

        function updateFromMouse(mouseX) {
            var norm = Math.max(0.0, Math.min(1.0, mouseX / width));
            var lMin = Math.log10(efs.minFreq);
            var lMax = Math.log10(efs.maxFreq);
            var f = Math.round(Math.pow(10, lMin + norm * (lMax - lMin)));
            efs.moved(f);
        }

        MouseArea {
            anchors.fill: parent
            onPositionChanged: (mouse) => { if (pressed) parent.updateFromMouse(mouse.x); }
            onPressed: (mouse) => { parent.updateFromMouse(mouse.x); }
        }
    }

    // Reusable Bipolar Gain Slider Component (-15 .. +15 dB)
    component EqGainSlider: Rectangle {
        id: egs
        property string label: "GAIN"
        property int gainVal: 0 // -15 .. +15 dB
        property color accent: "#10b981"
        signal moved(int g)

        implicitWidth: ScaleMetrics.dp(160)
        implicitHeight: ScaleMetrics.dp(22)
        Layout.fillWidth: true
        height: ScaleMetrics.dp(22)
        radius: 3
        color: "#080b11"
        border.color: Theme.borderCard
        border.width: 1

        // Center zero line
        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: 1
            color: Qt.rgba(1, 1, 1, 0.25)
        }

        // Bipolar fill bar
        Rectangle {
            property real norm: Math.max(0.0, Math.min(1.0, (egs.gainVal + 15) / 30.0))
            x: norm >= 0.5 ? parent.width * 0.5 : parent.width * norm
            width: Math.abs(parent.width * (norm - 0.5))
            height: parent.height
            radius: 2
            color: egs.accent
            opacity: 0.40
        }

        // Current value tick mark
        Rectangle {
            property real norm: Math.max(0.0, Math.min(1.0, (egs.gainVal + 15) / 30.0))
            x: Math.max(0, Math.min(parent.width - 2, parent.width * norm - 1))
            y: 0
            width: 2
            height: parent.height
            color: egs.accent
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: ScaleMetrics.dp(8)
            anchors.rightMargin: ScaleMetrics.dp(8)

            Text {
                text: egs.label
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(8)
                color: Theme.textDim
            }

            Item { Layout.fillWidth: true }

            Text {
                text: (egs.gainVal > 0 ? "+" + egs.gainVal : egs.gainVal.toString()) + " dB"
                font.family: Theme.fontMono
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(9)
                color: egs.gainVal !== 0 ? egs.accent : Theme.textDim
            }
        }

        function updateFromMouse(mouseX) {
            var norm = Math.max(0.0, Math.min(1.0, mouseX / width));
            var g = Math.round(norm * 30 - 15);
            egs.moved(Math.max(-15, Math.min(15, g)));
        }

        MouseArea {
            anchors.fill: parent
            onPositionChanged: (mouse) => { if (pressed) parent.updateFromMouse(mouse.x); }
            onPressed: (mouse) => { parent.updateFromMouse(mouse.x); }
        }
    }
}
