pragma ValueTypeBehavior: Copy
import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

// 4-band parametric EQ curve editor for MFX 01 EQUALIZER,
// 8-band graphic EQ curve editor for MFX 02 SPECTRUM.
// Log-frequency response curve with draggable band nodes:
// parametric drags gain (vertical) + frequency snapped to catalog options,
// graphic drags gain only (fixed band frequencies).
//
// Data-driven from the MFX catalog via `algo` (params looked up by idx):
//   Low shelf:  freq idx 0, gain idx 1
//   Mid1 bell:  freq idx 2, gain idx 3, Q idx 4
//   Mid2 bell:  freq idx 5, gain idx 6, Q idx 7
//   High shelf: freq idx 8, gain idx 9
// Gains are catalog 0..30 (dB = v - 15); freq/Q via param `options` lists.
//
// Values come from Bridge.mfxParamValues and writes go through
// Bridge.setMfxParam, so the panel edits the rail-selected target
// (PERFORM slot vs PARTn patch) with no extra wiring.
//
// NOTE: all cross-item references are id-qualified (panel.xxx).
Rectangle {
    id: panel
    objectName: "eqCurvePanel"
    color: "#070a0f"
    radius: ScaleMetrics.dp(6)
    border.color: Theme.borderCard
    border.width: 1
    clip: true

    property var algo: null
    property bool isDimmed: false
    property int draggedBand: -1 // parametric 0-3: Low/Mid1/Mid2/High; graphic 0-7
    property string lastPreset: ""
    property int lastPresetAlgo: -1 // algo id the highlight belongs to (1/2)
    // Highlight only when name AND algo match: both lists share names
    // (e.g. BRIGHT) with unrelated settings.
    function isPresetActive(name) {
        return panel.lastPreset === name
            && panel.lastPresetAlgo === (panel.graphic ? 2 : 1);
    }
    function currentPresetName() {
        if (panel.lastPreset !== "" && panel.lastPresetAlgo === (panel.graphic ? 2 : 1))
            return panel.lastPreset;
        return "";
    }
    // Preset list follows the algo (data lives in mfx_catalog, via Bridge).
    property var presets: panel.graphic ? Bridge.spectrumPresets : Bridge.eqParametricPresets
    // Grab offset: node sits at the TOTAL curve value, but dragging writes the
    // band's OWN gain. Without this, touching a node snaps its gain to the
    // displayed total (shelves read half at the corner; wide-Q bleed adds up).
    property real grabOffsetDb: 0
    // Graphic mode (02 SPECTRUM): 8 fixed bands, gain-drag only, shared Q.
    readonly property bool graphic: panel.algo && panel.algo.id === 2
    readonly property int bandCount: panel.graphic ? 8 : 4
    readonly property var graphicFreqs: [250, 500, 1000, 1250, 2000, 3150, 4000, 8000]
    opacity: panel.isDimmed ? 0.45 : 1.0

    Connections {
        target: Bridge
        function onMfxValuesChanged() { eqCurveCanvas.requestPaint(); }
        function onMfxParamsChanged() { eqCurveCanvas.requestPaint(); }
    }

    function _paramByIdx(idx) {
        if (!panel.algo || !panel.algo.params) return null;
        for (var i = 0; i < panel.algo.params.length; ++i) {
            if (panel.algo.params[i].idx === idx) return panel.algo.params[i];
        }
        return null;
    }
    function _freqOptions(idx) {
        var p = panel._paramByIdx(idx);
        if (!p || !p.options) return [];
        var out = [];
        for (var i = 0; i < p.options.length; ++i) out.push(Number(p.options[i]));
        return out;
    }
    function _qOptions(idx) {
        var p = panel._paramByIdx(idx);
        if (!p || !p.options) return [1.0];
        var out = [];
        for (var i = 0; i < p.options.length; ++i) out.push(parseFloat(p.options[i]));
        return out;
    }
    function _val(idx, fallback) {
        var vals = Bridge.mfxParamValues;
        if (vals && idx >= 0 && idx < vals.length) return vals[idx];
        var p = panel._paramByIdx(idx);
        if (p && p.val !== undefined) return p.val;
        return fallback;
    }
    function _gainDb(idx) { return panel._val(idx, 0); }
    function _freqHz(freqIdx) {
        var opts = panel._freqOptions(freqIdx);
        if (opts.length === 0) return 1000;
        var v = panel._val(freqIdx, 0);
        return opts[Math.max(0, Math.min(opts.length - 1, v))];
    }
    function _qVal(qIdx) {
        var opts = panel._qOptions(qIdx);
        var v = panel._val(qIdx, 0);
        return opts[Math.max(0, Math.min(opts.length - 1, v))];
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
    function _bellDb(freq, f0, q, gainDb) {
        if (f0 <= 0 || q <= 0) return 0;
        var ratio = freq / f0;
        return gainDb / (1.0 + Math.pow(q * (ratio - 1.0 / ratio), 2));
    }
    function calcDbAtFreq(freq) {
        if (panel.graphic) {
            var total = 0;
            var gq = panel._qVal(8);
            for (var gb = 0; gb < 8; ++gb)
                total += panel._bellDb(freq, panel.graphicFreqs[gb], gq, panel._gainDb(gb));
            return total;
        }
        var lowDb = panel._gainDb(1) / (1.0 + Math.pow(freq / Math.max(1, panel._freqHz(0)), 2));
        var highF = Math.max(1, panel._freqHz(8));
        var highDb = panel._gainDb(9) * Math.pow(freq / highF, 2) / (1.0 + Math.pow(freq / highF, 2));
        var mid1Db = panel._bellDb(freq, panel._freqHz(2), panel._qVal(4), panel._gainDb(3));
        var mid2Db = panel._bellDb(freq, panel._freqHz(5), panel._qVal(7), panel._gainDb(6));
        return lowDb + mid1Db + mid2Db + highDb;
    }
    function _bandFreq(b) {
        if (panel.graphic) return panel.graphicFreqs[b];
        return [panel._freqHz(0), panel._freqHz(2), panel._freqHz(5), panel._freqHz(8)][b];
    }
    function _bandGainIdx(b) {
        if (panel.graphic) return b;
        return [1, 3, 6, 9][b];
    }
    function _bandFreqIdx(b) {
        if (panel.graphic) return -1;
        return [0, 2, 5, 8][b];
    }
    function _bandTag(b) {
        var gdb = Math.round(panel._gainDb(panel._bandGainIdx(b)));
        var gtxt = (gdb > 0 ? "+" + gdb : "" + gdb);
        if (panel.graphic)
            return ["250", "500", "1k", "1.25k", "2k", "3.15k", "4k", "8k"][b] + " " + gtxt;
        return ["L", "M1", "M2", "H"][b] + " " + Math.round(panel._bandFreq(b)) + " " + gtxt;
    }
    function _dbToY(db, h) {
        var midY = h * 0.5;
        return midY - (db / 16.0) * (midY - 8);
    }
    // Node position, clamped into the canvas. The ±16dB view is fixed
    // (matches the ±15dB gain range); stacked boosts can exceed it, so a
    // clamped node renders amber to signal "value beyond view" instead of
    // disappearing. Hit-testing uses the same position, so touch matches.
    function _nodeAt(b, w, h) {
        var r = 8;
        var bx = panel.freqToX(panel._bandFreq(b), w);
        var rawY = panel._dbToY(panel.calcDbAtFreq(panel._bandFreq(b)), h);
        var cy = Math.max(r, Math.min(h - r, rawY));
        return { x: bx, y: cy, clipped: cy !== rawY };
    }
    // Write one preset through the origin-resolved MFX param path.
    function applyPreset(p) {
        if (panel.graphic) {
            for (var i = 0; i < 8; ++i) Bridge.setMfxParam(i, p.g[i]);
            if (p.q !== undefined && p.q !== null && p.q >= 0) Bridge.setMfxParam(8, p.q);
        } else {
            var G = [1, 3, 6, 9], F = [0, 2, 5, 8], Q = [-1, 4, 7, -1];
            for (var b = 0; b < 4; ++b) Bridge.setMfxParam(G[b], p.g[b]);
            if (p.f !== undefined && p.f !== null)
                for (var fb = 0; fb < 4; ++fb) Bridge.setMfxParam(F[fb], p.f[fb]);
            if (p.q !== undefined && p.q !== null)
                for (var qb = 0; qb < 4; ++qb)
                    if (p.q[qb] !== undefined && p.q[qb] !== null && p.q[qb] >= 0)
                        Bridge.setMfxParam(Q[qb], p.q[qb]);
        }
        panel.lastPreset = p.name;
        panel.lastPresetAlgo = panel.graphic ? 2 : 1;
        eqCurveCanvas.requestPaint();
    }
    function _nearestFreqOption(freqIdx, hz) {
        var opts = panel._freqOptions(freqIdx);
        if (opts.length === 0) return 0;
        var best = 0, minD = Math.abs(hz - opts[0]);
        for (var i = 1; i < opts.length; ++i) {
            var d = Math.abs(hz - opts[i]);
            if (d < minD) { minD = d; best = i; }
        }
        return best;
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: ScaleMetrics.dp(6)
        spacing: ScaleMetrics.dp(4)

        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(6)
            Text {
                text: panel.graphic ? "8-BAND GRAPHIC CURVE" : "4-BAND PARAMETRIC CURVE"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(8)
                font.letterSpacing: 1.0
                color: "#ec4899"
            }
            Item { Layout.fillWidth: true }
            Text {
                text: panel.currentPresetName()
                font.pixelSize: ScaleMetrics.sp(7)
                font.family: Theme.fontMono
                color: Theme.textDim
            }
        }

        // Preset chips (FLAT first), horizontal scroll if overflowing
        Flickable {
            Layout.fillWidth: true
            Layout.preferredHeight: ScaleMetrics.dp(24)
            contentWidth: presetRow.width
            contentHeight: height
            clip: true
            interactive: contentWidth > width
            RowLayout {
                id: presetRow
                height: parent.height
                spacing: ScaleMetrics.dp(4)
                Repeater {
                    model: panel.presets
                    delegate: Rectangle {
                        id: presetChip
                        Layout.preferredWidth: Math.min(presetLabel.implicitWidth + ScaleMetrics.dp(12), ScaleMetrics.dp(88))
                        Layout.maximumWidth: ScaleMetrics.dp(88)
                        Layout.fillHeight: true
                        radius: 3
                        color: panel.isPresetActive(modelData.name) ? "#3a1030" : Theme.bgSurface
                        border.color: panel.isPresetActive(modelData.name) ? "#ec4899" : Theme.borderCard
                        border.width: 1
                        clip: true
                        Text {
                            id: presetLabel
                            anchors.fill: parent
                            anchors.leftMargin: ScaleMetrics.dp(6)
                            anchors.rightMargin: ScaleMetrics.dp(6)
                            verticalAlignment: Text.AlignVCenter
                            horizontalAlignment: Text.AlignHCenter
                            text: modelData.name
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(7)
                            color: panel.isPresetActive(modelData.name) ? "#ec4899" : Theme.textSecondary
                            elide: Text.ElideRight
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: panel.applyPreset(modelData)
                        }
                    }
                }
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            Canvas {
                id: eqCurveCanvas
                anchors.fill: parent
                renderTarget: Canvas.FramebufferObject

                onPaint: {
                    var ctx = getContext("2d");
                    var w = width, h = height;
                    ctx.clearRect(0, 0, w, h);
                    var midY = h * 0.5;

                    // Grid: 0 dB center + octave lines
                    ctx.strokeStyle = "#222c3d";
                    ctx.lineWidth = 1;
                    ctx.beginPath();
                    ctx.moveTo(0, midY);
                    ctx.lineTo(w, midY);
                    ctx.stroke();
                    var gridF = [100, 1000, 10000];
                    ctx.fillStyle = "#222c3d";
                    ctx.font = "8px monospace";
                    for (var gi = 0; gi < gridF.length; ++gi) {
                        var gx = panel.freqToX(gridF[gi], w);
                        ctx.beginPath();
                        ctx.moveTo(gx, 0);
                        ctx.lineTo(gx, h);
                        ctx.stroke();
                        ctx.fillText(gridF[gi] >= 1000 ? (gridF[gi] / 1000) + "k" : "" + gridF[gi], gx + 2, 9);
                    }

                    // Response curve (±16 dB headroom)
                    ctx.beginPath();
                    ctx.strokeStyle = "#ec4899";
                    ctx.lineWidth = ScaleMetrics.dp(2);
                    for (var x = 0; x <= w; x += 2) {
                        var f = panel.xToFreq(x, w);
                        var db = panel.calcDbAtFreq(f);
                        var y = midY - (db / 16.0) * (midY - 8);
                        if (x === 0) ctx.moveTo(x, y);
                        else ctx.lineTo(x, y);
                    }
                    ctx.stroke();

                    // Band nodes (clamped into view; amber = value beyond view)
                    var cols = ["#38bdf8", "#10b981", "#fbbf24", "#ec4899",
                                "#38bdf8", "#10b981", "#fbbf24", "#ec4899"];
                    for (var b = 0; b < panel.bandCount; ++b) {
                        var np = panel._nodeAt(b, w, h);
                        ctx.beginPath();
                        if (panel.draggedBand === b) ctx.fillStyle = "#ffffff";
                        else if (np.clipped) ctx.fillStyle = "#fbbf24";
                        else ctx.fillStyle = cols[b];
                        ctx.arc(np.x, np.y, panel.draggedBand === b ? 7 : 5, 0, Math.PI * 2);
                        ctx.fill();
                        ctx.fillStyle = np.clipped ? "#fbbf24" : cols[b];
                        var tagY = Math.max(10, Math.min(h - 2, np.y - 6));
                        ctx.fillText(panel._bandTag(b), Math.max(0, Math.min(w - 40, np.x + 8)), tagY);
                    }
                }
            }

            MouseArea {
                anchors.fill: parent
                onPressed: (mouse) => {
                    var w = width, h = height;
                    var best = -1, minD = ScaleMetrics.dp(36);
                    for (var b = 0; b < panel.bandCount; ++b) {
                        var np = panel._nodeAt(b, w, h);
                        var d = Math.hypot(mouse.x - np.x, mouse.y - np.y);
                        if (d < minD) { minD = d; best = b; }
                    }
                    panel.draggedBand = best;
                    panel.grabOffsetDb = 0;
                    if (best >= 0) {
                        var shown = panel.calcDbAtFreq(panel._bandFreq(best));
                        panel.grabOffsetDb = shown - panel._gainDb(panel._bandGainIdx(best));
                    }
                    eqCurveCanvas.requestPaint();
                }
                onPositionChanged: (mouse) => {
                    if (pressed && panel.draggedBand >= 0) {
                        var h = height, midY = h * 0.5;
                        var ptrDb = ((midY - mouse.y) / (midY - 8)) * 16.0;
                        var newDb = Math.round(ptrDb - panel.grabOffsetDb);
                        newDb = Math.max(-15, Math.min(15, newDb));
                        var b = panel.draggedBand;
                        panel.lastPreset = "";
                        panel.lastPresetAlgo = -1;
                        Bridge.setMfxParam(panel._bandGainIdx(b), newDb);
                        if (!panel.graphic) {
                            var newHz = panel.xToFreq(mouse.x, width);
                            Bridge.setMfxParam(panel._bandFreqIdx(b),
                                           panel._nearestFreqOption(panel._bandFreqIdx(b), newHz));
                        }
                        eqCurveCanvas.requestPaint();
                    }
                }
                onReleased: { panel.draggedBand = -1; eqCurveCanvas.requestPaint(); }
                onCanceled: { panel.draggedBand = -1; eqCurveCanvas.requestPaint(); }
            }
        }
    }
}
