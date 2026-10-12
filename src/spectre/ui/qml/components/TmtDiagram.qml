pragma ValueTypeBehavior: Copy
import QtQuick
import JunoSpectre
import ".."

// Signal-flow drawing of one TMT structure type (nodes/edges from
// Bridge.tmtStructureTypes, after Parameter Guide p.6-7).
Canvas {
    id: root
    property var structure: null     // one entry of Bridge.tmtStructureTypes
    property int toneA: 1            // first tone of the pair (1 or 3)
    property color colorA: Theme.tone1
    property color colorB: Theme.tone2
    property string boosterText: ""
    property bool dimmed: false      // pair falls back to type 1 (a tone is off)

    onStructureChanged: requestPaint()
    onBoosterTextChanged: requestPaint()
    onDimmedChanged: requestPaint()
    onWidthChanged: requestPaint()
    onVisibleChanged: if (visible) requestPaint()
    onHeightChanged: requestPaint()

    function _hex(c, a) {
        return Qt.rgba(c.r, c.g, c.b, a);
    }

    onPaint: {
        var ctx = getContext("2d");
        ctx.reset();
        var s = root.structure;
        if (!s || width <= 0 || height <= 0)
            return;
        var nodes = s.nodes, edges = s.edges, outs = s.out;
        var label = ScaleMetrics.dp(46);           // lane labels on the left
        var outW = ScaleMetrics.dp(34);            // OUT arrow on the right
        var cols = 7;
        var colW = (width - label - outW) / cols;
        var nodeW = Math.min(colW - ScaleMetrics.dp(8), ScaleMetrics.dp(50));
        var nodeH = ScaleMetrics.dp(22);
        var laneY = [height * 0.2, height * 0.8];
        function nx(n) { return label + colW * (n[1] + 0.5); }
        function ny(n) { return laneY[0] + (laneY[1] - laneY[0]) * n[2]; }
        var mixR = ScaleMetrics.dp(9);
        // Half width: lines meet the "+" circle, not an invisible box
        function hw(n) { return n[0] === "+" ? mixR : nodeW / 2; }
        function ownerColor(n) {
            return n[3] === 1 ? root.colorA : (n[3] === 2 ? root.colorB : Theme.textPrimary);
        }
        var alpha = root.dimmed ? 0.35 : 1.0;
        ctx.globalAlpha = alpha;

        // Lane labels
        ctx.font = "bold " + ScaleMetrics.sp(8) + "px sans-serif";
        ctx.textAlign = "left";
        ctx.textBaseline = "middle";
        ctx.fillStyle = root.colorA;
        ctx.fillText("TONE " + root.toneA, 0, laneY[0]);
        ctx.fillStyle = root.colorB;
        ctx.fillText("TONE " + (root.toneA + 1), 0, laneY[1]);

        // Edges: run along the source lane, then bend into the target
        ctx.lineWidth = Math.max(1.5, ScaleMetrics.dp(1.6));
        ctx.strokeStyle = Theme.textSecondary;
        for (var i = 0; i < edges.length; ++i) {
            var a = nodes[edges[i][0]], b = nodes[edges[i][1]];
            var x1 = nx(a) + hw(a), y1 = ny(a);
            var x2 = nx(b) - hw(b), y2 = ny(b);
            ctx.beginPath();
            ctx.moveTo(x1, y1);
            if (Math.abs(y1 - y2) > 1) {
                var bend = Math.max(x1, x2 - colW * 0.45);
                ctx.lineTo(bend, y1);
            }
            ctx.lineTo(x2, y2);
            ctx.stroke();
        }

        // Outputs
        ctx.strokeStyle = Theme.textPrimary;
        ctx.fillStyle = Theme.textPrimary;
        for (var o = 0; o < outs.length; ++o) {
            var n = nodes[outs[o]];
            var ox = nx(n) + hw(n), oy = ny(n), ex = width - ScaleMetrics.dp(4);
            ctx.beginPath();
            ctx.moveTo(ox, oy);
            ctx.lineTo(ex, oy);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(ex, oy);
            ctx.lineTo(ex - ScaleMetrics.dp(6), oy - ScaleMetrics.dp(4));
            ctx.lineTo(ex - ScaleMetrics.dp(6), oy + ScaleMetrics.dp(4));
            ctx.closePath();
            ctx.fill();
        }

        // Nodes
        ctx.textAlign = "center";
        for (var k = 0; k < nodes.length; ++k) {
            var nd = nodes[k];
            var cx = nx(nd), cy = ny(nd), lab = nd[0];
            if (lab === "+") {
                ctx.beginPath();
                ctx.arc(cx, cy, mixR, 0, Math.PI * 2);
                ctx.fillStyle = Theme.bgApp;
                ctx.fill();
                ctx.strokeStyle = Theme.textPrimary;
                ctx.stroke();
                ctx.fillStyle = Theme.textPrimary;
                ctx.font = "bold " + ScaleMetrics.sp(11) + "px sans-serif";
                ctx.fillText("+", cx, cy);
                continue;
            }
            var special = (lab === "BOOST" || lab === "RING");
            var col = special ? (lab === "BOOST" ? Theme.warning : Theme.recording) : ownerColor(nd);
            ctx.fillStyle = special ? root._hex(col, 0.85) : Theme.bgApp;
            ctx.strokeStyle = col;
            ctx.beginPath();
            ctx.rect(cx - nodeW / 2, cy - nodeH / 2, nodeW, nodeH);
            ctx.fill();
            ctx.stroke();
            ctx.fillStyle = special ? Theme.textOnFill : col;
            ctx.font = "bold " + ScaleMetrics.sp(8) + "px sans-serif";
            ctx.fillText(lab === "RING" ? "RING ×" : lab, cx, cy);
            if (lab === "BOOST" && root.boosterText !== "") {
                ctx.fillStyle = Theme.warning;
                ctx.fillText(root.boosterText, cx, cy + nodeH);
            }
        }
    }
}
