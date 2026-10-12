pragma ValueTypeBehavior: Copy
import QtQuick
import JunoSpectre
import ".."

// One tone's key or velocity range: a plateau from lower to upper with fade
// ramps outside it (Parameter Guide p.7). Drag the top corners to move the
// edges, the feet of the ramps to set the fades, the middle to slide it.
Item {
    id: root
    property int minV: 0                 // 0 for keys, 1 for velocity
    property int maxV: 127
    property int lower: 0
    property int upper: 127
    property int fadeLower: 0
    property int fadeUpper: 0
    property color barColor: Theme.tone1
    property bool active: true           // dim when the range has no effect
    signal edit(string which, int value) // "Lower" | "Upper" | "FadeLower" | "FadeUpper"
    signal slide(int lower, int upper)

    readonly property int slots: maxV - minV + 1
    readonly property real slotW: width / slots
    // Edges sit on slot boundaries: lower at its left, upper at its right
    function xAt(v) { return Math.max(0, Math.min(width, (v - minV) * slotW)); }
    function boundaryAt(x) { return Math.round(x / slotW) + minV; }

    readonly property real xLower: xAt(lower)
    readonly property real xUpper: xAt(upper + 1)
    readonly property real xFadeLower: xAt(lower - fadeLower)
    readonly property real xFadeUpper: xAt(upper + 1 + fadeUpper)
    readonly property real yTop: ScaleMetrics.dp(5)
    readonly property real yBottom: height - ScaleMetrics.dp(5)
    readonly property color fill: Qt.rgba(barColor.r, barColor.g, barColor.b, active ? 0.45 : 0.15)

    // Track
    Rectangle {
        anchors.fill: parent
        radius: ScaleMetrics.dp(3)
        color: "#10141d"
        border.color: area.pressed ? root.barColor : Theme.borderCard
        border.width: 1
    }

    // Fade ramps (gradient from silent to full) + plateau
    Rectangle {
        x: root.xFadeLower; y: root.yTop
        width: root.xLower - root.xFadeLower; height: root.yBottom - root.yTop
        visible: width > 0
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: "transparent" }
            GradientStop { position: 1.0; color: root.fill }
        }
    }
    Rectangle {
        x: root.xLower; y: root.yTop
        width: Math.max(1, root.xUpper - root.xLower); height: root.yBottom - root.yTop
        color: root.fill
        border.color: root.active ? root.barColor : Qt.rgba(root.barColor.r, root.barColor.g, root.barColor.b, 0.4)
        border.width: 1
    }
    Rectangle {
        x: root.xUpper; y: root.yTop
        width: root.xFadeUpper - root.xUpper; height: root.yBottom - root.yTop
        visible: width > 0
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: root.fill }
            GradientStop { position: 1.0; color: "transparent" }
        }
    }

    // Handles: edges at the top, fade feet at the bottom
    Repeater {
        model: [
            { x: root.xLower, y: root.yTop, fade: false },
            { x: root.xUpper, y: root.yTop, fade: false },
            { x: root.xFadeLower, y: root.yBottom, fade: true },
            { x: root.xFadeUpper, y: root.yBottom, fade: true }
        ]
        delegate: Rectangle {
            required property var modelData
            width: ScaleMetrics.dp(modelData.fade ? 8 : 10)
            height: width
            radius: width / 2
            x: modelData.x - width / 2
            y: modelData.y - height / 2
            color: modelData.fade ? Theme.bgApp : root.barColor
            border.color: root.barColor
            border.width: 1
            opacity: root.active ? 1.0 : 0.5
        }
    }

    MouseArea {
        id: area
        anchors.fill: parent
        preventStealing: true
        property string mode: ""
        property real pressX: 0
        property int startLower: 0
        property int startUpper: 0

        function nearest(x, a, b) { return Math.abs(x - a) <= Math.abs(x - b) ? 0 : 1; }

        onPressed: (mouse) => {
            const grab = ScaleMetrics.dp(22);
            pressX = mouse.x;
            startLower = root.lower;
            startUpper = root.upper;
            const inside = mouse.x > root.xLower + grab && mouse.x < root.xUpper - grab;
            if (mouse.y >= height / 2) {
                // Bottom half: fade feet, unless pressing inside the plateau
                const i = nearest(mouse.x, root.xFadeLower, root.xFadeUpper);
                const d = Math.abs(mouse.x - (i === 0 ? root.xFadeLower : root.xFadeUpper));
                if (d <= grab && !inside) { mode = i === 0 ? "FadeLower" : "FadeUpper"; return; }
            }
            if (inside) { mode = "slide"; return; }
            mode = nearest(mouse.x, root.xLower, root.xUpper) === 0 ? "Lower" : "Upper";
            positionChanged(mouse);
        }
        onPositionChanged: (mouse) => {
            if (!pressed)
                return;
            const b = root.boundaryAt(Math.max(0, Math.min(width, mouse.x)));
            if (mode === "Lower") {
                const v = Math.max(root.minV, Math.min(root.maxV, b));
                if (v !== root.lower) root.edit("Lower", v);
            } else if (mode === "Upper") {
                const v = Math.max(root.minV, Math.min(root.maxV, b - 1));
                if (v !== root.upper) root.edit("Upper", v);
            } else if (mode === "FadeLower") {
                const v = Math.max(0, Math.min(127, root.lower - b));
                if (v !== root.fadeLower) root.edit("FadeLower", v);
            } else if (mode === "FadeUpper") {
                const v = Math.max(0, Math.min(127, b - (root.upper + 1)));
                if (v !== root.fadeUpper) root.edit("FadeUpper", v);
            } else if (mode === "slide") {
                let d = Math.round((mouse.x - pressX) / root.slotW);
                d = Math.max(root.minV - startLower, Math.min(root.maxV - startUpper, d));
                if (startLower + d !== root.lower)
                    root.slide(startLower + d, startUpper + d);
            }
        }
        onReleased: mode = ""
    }
}
