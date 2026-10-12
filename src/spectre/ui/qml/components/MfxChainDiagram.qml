pragma ValueTypeBehavior: Copy
import QtQuick
import JunoSpectre
import ".."

// Small drawing of one Performance MFX Structure type (how MFX1-3 connect),
// from Bridge.perfMfxStructures. The part's entry unit and the units its
// sound passes through are lit.
Canvas {
    id: root
    property var layout: null        // {rows, merge, next}
    property int entry: 0            // MFX the part enters (1..3), 0 = none
    property color accent: "#ec4899"
    property color entryColor: "#f59e0b"

    onLayoutChanged: requestPaint()
    onEntryChanged: requestPaint()
    onWidthChanged: requestPaint()
    onVisibleChanged: if (visible) requestPaint()
    onHeightChanged: requestPaint()

    // Units the part's sound passes through, in order
    function path() {
        var out = [];
        if (!layout || entry < 1) return out;
        var u = entry;
        while (u && out.indexOf(u) < 0) {
            out.push(u);
            u = layout.next[String(u)];
        }
        return out;
    }

    onPaint: {
        var ctx = getContext("2d");
        ctx.reset();
        if (!layout || width <= 0 || height <= 0) return;
        var lit = path();
        var dp = ScaleMetrics.dp(1);
        var rows = layout.rows, merge = layout.merge;
        var cols = merge ? 2 : 3;
        var stub = 8 * dp, tail = 10 * dp;
        var colW = (width - stub - tail) / cols;
        var boxW = Math.min(colW - 6 * dp, 34 * dp), boxH = Math.min(16 * dp, height / 3 - 3 * dp);
        var nRows = rows.length;
        function rowY(i) { return height * (i + 0.5) / nRows; }
        function colX(c) { return stub + colW * (c + 0.5); }
        function isLit(u) { return lit.indexOf(u) >= 0; }
        function litEdge(a, b) { var i = lit.indexOf(a); return i >= 0 && lit[i + 1] === b; }

        ctx.lineWidth = 1.4 * dp;
        function line(x1, y1, x2, y2, on) {
            ctx.strokeStyle = on ? root.accent : Theme.textDim;
            ctx.beginPath();
            ctx.moveTo(x1, y1);
            if (Math.abs(y1 - y2) > 1) {
                var mx = (x1 + x2) / 2;
                ctx.lineTo(mx, y1);
                ctx.lineTo(mx, y2);
            }
            ctx.lineTo(x2, y2);
            ctx.stroke();
        }
        function box(u, cx, cy) {
            var on = isLit(u);
            ctx.fillStyle = on ? root.accent : Theme.bgApp;
            ctx.strokeStyle = u === root.entry ? root.entryColor : (on ? root.accent : Theme.textSecondary);
            ctx.lineWidth = (u === root.entry ? 2 : 1.2) * dp;
            ctx.beginPath();
            ctx.rect(cx - boxW / 2, cy - boxH / 2, boxW, boxH);
            ctx.fill();
            ctx.stroke();
            ctx.lineWidth = 1.4 * dp;
            ctx.fillStyle = on ? "#000000" : Theme.textSecondary;
            ctx.font = "bold " + Math.round(8 * dp) + "px monospace";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(String(u), cx, cy);
        }

        // Inputs into each row's first unit (the part's entry in amber)
        for (var r = 0; r < nRows; ++r) {
            var head = rows[r][0], y = rowY(r);
            ctx.strokeStyle = head === root.entry ? root.entryColor : Theme.textDim;
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(colX(0) - boxW / 2, y);
            ctx.stroke();
        }
        if (merge) {
            var my = height / 2, mx = colX(1);
            for (var m = 0; m < nRows; ++m)
                line(colX(0) + boxW / 2, rowY(m), mx - boxW / 2, my, litEdge(rows[m][0], merge));
            line(mx + boxW / 2, my, width, my, isLit(merge));
            for (var k = 0; k < nRows; ++k) box(rows[k][0], colX(0), rowY(k));
            box(merge, mx, my);
            return;
        }
        for (var i = 0; i < nRows; ++i) {
            var row = rows[i], yy = rowY(i);
            for (var j = 0; j + 1 < row.length; ++j)
                line(colX(j) + boxW / 2, yy, colX(j + 1) - boxW / 2, yy, litEdge(row[j], row[j + 1]));
            line(colX(row.length - 1) + boxW / 2, yy, width, yy, isLit(row[row.length - 1]));
            for (var b = 0; b < row.length; ++b) box(row[b], colX(b), yy);
        }
    }
}
