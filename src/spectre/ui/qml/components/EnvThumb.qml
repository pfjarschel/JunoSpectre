import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

// Read-only mini envelope curve button. Tap to open the quick-edit overlay.
Rectangle {
    id: root
    property string env: "TVF"
    property var seg: ({ times: [0, 0, 0, 0], levels: [0, 127, 127, 127, 0], bipolar: false, custom: false })

    readonly property color accent: env === "PITCH" ? "#fbbf24" : (env === "TVF" ? "#38bdf8" : "#10b981")

    Layout.preferredWidth: ScaleMetrics.dp(58)
    Layout.preferredHeight: ScaleMetrics.dp(26)
    implicitWidth: Layout.preferredWidth
    implicitHeight: Layout.preferredHeight
    radius: 3
    color: thumbArea.pressed ? Theme.bgCardActive : "#10141d"
    border.color: Theme.borderCard
    border.width: 1

    function refresh() {
        seg = Bridge.getEnvSegments(env);
        thumbCanvas.requestPaint();
    }

    function drawLevels() {
        if (env === "TVA") {
            return [0].concat(seg.levels).concat([0]);
        }
        return seg.levels;
    }

    Connections {
        target: Bridge
        function onEnvShapeChanged(e) {
            if (e === root.env) {
                refresh();
            }
        }
    }

    Component.onCompleted: refresh()
    onEnvChanged: refresh()

    Canvas {
        id: thumbCanvas
        anchors.fill: parent
        anchors.margins: 3

        onPaint: {
            var ctx = getContext("2d");
            ctx.reset();
            var w = width;
            var h = height;
            var dl = root.drawLevels();
            var times = root.seg.times;
            var totalT = Math.max(20, times[0] + times[1] + times[2] + times[3] + 30);
            var scaleX = (w * 0.95) / totalT;

            var xs = [0,
                Math.max(2, times[0] * scaleX),
                0, 0, 0];
            xs[2] = xs[1] + Math.max(2, times[1] * scaleX);
            xs[3] = xs[2] + Math.max(2, times[2] * scaleX);
            xs[4] = Math.min(w, xs[3] + Math.max(2, times[3] * scaleX));

            function yFor(l) {
                if (root.seg.bipolar) {
                    var midY = h * 0.5;
                    return midY - (l / 63.0) * (midY - 1);
                }
                return h - 1 - (l / 127.0) * (h - 2);
            }

            // Reference line
            ctx.strokeStyle = "#1e293b";
            ctx.lineWidth = 1;
            ctx.beginPath();
            var refY = root.seg.bipolar ? h * 0.5 : h - 1;
            ctx.moveTo(0, refY); ctx.lineTo(w, refY);
            ctx.stroke();

            ctx.strokeStyle = root.accent;
            ctx.lineWidth = 1.5;
            ctx.lineCap = "round";
            ctx.lineJoin = "round";
            ctx.beginPath();
            ctx.moveTo(xs[0], yFor(dl[0]));
            for (var i = 1; i < 5; i++) {
                ctx.lineTo(xs[i], yFor(dl[i]));
            }
            ctx.stroke();
        }
    }

    // CUSTOM indicator dot
    Rectangle {
        visible: root.seg.custom
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 2
        width: 5; height: 5; radius: 2.5
        color: "#f59e0b"
    }

    Text {
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 2
        text: "⤢"
        font.pixelSize: ScaleMetrics.sp(8)
        color: Theme.textDim
    }

    MouseArea {
        id: thumbArea
        anchors.fill: parent
        onClicked: Bridge.openEnvOverlay(root.env)
    }
}
