import QtQuick
import QtQuick.Shapes
import JunoSpectre
import ".."

Item {
    id: root
    clip: true

    // Visual background container
    Rectangle {
        id: bg
        anchors.fill: parent
        color: Theme.bgCard
        radius: ScaleMetrics.dp(8)
        border.color: Theme.borderCard
        border.width: 1

        // Grid lines
        Shape {
            anchors.fill: parent
            asynchronous: true

            // Horizontal center line
            ShapePath {
                strokeColor: Theme.borderCard
                strokeWidth: 1
                strokeStyle: ShapePath.DashLine
                dashPattern: [4, 4]
                startX: 0
                startY: bg.height / 2
                PathLine { x: bg.width; y: bg.height / 2 }
            }

            // Vertical center line
            ShapePath {
                strokeColor: Theme.borderCard
                strokeWidth: 1
                strokeStyle: ShapePath.DashLine
                dashPattern: [4, 4]
                startX: bg.width / 2
                startY: 0
                PathLine { x: bg.width / 2; y: bg.height }
            }
        }

        // Corner 1: Tone 1 (NW)
        CornerGlowBadge {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.margins: ScaleMetrics.dp(10)
            toneName: "TONE 1"
            toneSub: "NORTH-WEST"
            toneColor: Theme.tone1
            level: Bridge.tone1Level
        }

        // Corner 2: Tone 2 (NE)
        CornerGlowBadge {
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.margins: ScaleMetrics.dp(10)
            toneName: "TONE 2"
            toneSub: "NORTH-EAST"
            toneColor: Theme.tone2
            level: Bridge.tone2Level
            alignRight: true
        }

        // Corner 3: Tone 3 (SW)
        CornerGlowBadge {
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.margins: ScaleMetrics.dp(10)
            toneName: "TONE 3"
            toneSub: "SOUTH-WEST"
            toneColor: Theme.tone3
            level: Bridge.tone3Level
        }

        // Corner 4: Tone 4 (SE)
        CornerGlowBadge {
            anchors.bottom: parent.bottom
            anchors.right: parent.right
            anchors.margins: ScaleMetrics.dp(10)
            toneName: "TONE 4"
            toneSub: "SOUTH-EAST"
            toneColor: Theme.tone4
            level: Bridge.tone4Level
            alignRight: true
        }

        // Touch Cursor Puck
        Item {
            id: puck
            // Pixel mapping: X 0..1 -> 0..width, Y 0..1 -> height..0
            x: Math.max(0, Math.min(bg.width - width, Bridge.vectorX * bg.width - width / 2))
            y: Math.max(0, Math.min(bg.height - height, (1.0 - Bridge.vectorY) * bg.height - height / 2))
            width: ScaleMetrics.dp(48)
            height: ScaleMetrics.dp(48)

            // Outer glowing halo
            Rectangle {
                anchors.centerIn: parent
                width: parent.width * 1.5
                height: parent.height * 1.5
                radius: width / 2
                color: Theme.primary
                opacity: 0.22
            }

            // Middle ring
            Rectangle {
                anchors.centerIn: parent
                width: parent.width
                height: parent.height
                radius: width / 2
                color: "#182642"
                border.color: Theme.primary
                border.width: ScaleMetrics.dp(2)

                // Center core point
                Rectangle {
                    anchors.centerIn: parent
                    width: ScaleMetrics.dp(12)
                    height: ScaleMetrics.dp(12)
                    radius: width / 2
                    color: Theme.textPrimary
                }
            }

            // Coordinate readout badge floating above puck
            Rectangle {
                anchors.bottom: parent.top
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottomMargin: ScaleMetrics.dp(6)
                width: ScaleMetrics.dp(82)
                height: ScaleMetrics.dp(20)
                radius: ScaleMetrics.dp(4)
                color: "#0f172a"
                border.color: Theme.borderCard
                border.width: 1

                Text {
                    anchors.centerIn: parent
                    text: Bridge.vectorX.toFixed(2) + ", " + Bridge.vectorY.toFixed(2)
                    font.pixelSize: ScaleMetrics.sp(10)
                    font.family: Theme.fontMono
                    font.bold: true
                    color: Theme.textPrimary
                }
            }
        }

        // Gravitational Attractor Pulsar (Visible in ORBIT mode)
        Rectangle {
            id: attractorPulsar
            visible: Bridge.automator === "circle"
            x: Bridge.attractorX * bg.width - width / 2
            y: (1.0 - Bridge.attractorY) * bg.height - height / 2
            width: ScaleMetrics.dp(24)
            height: ScaleMetrics.dp(24)
            radius: width / 2
            color: "transparent"
            border.color: "#fbbf24"
            border.width: 2
            opacity: 0.85

            Rectangle {
                anchors.centerIn: parent
                width: ScaleMetrics.dp(8)
                height: ScaleMetrics.dp(8)
                radius: width / 2
                color: "#fbbf24"
            }

            Text {
                anchors.top: parent.bottom
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.topMargin: 2
                text: "ATTRACTOR"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(8)
                color: "#fbbf24"
            }
        }

        // Mouse and Touch Interaction Area
        MouseArea {
            anchors.fill: parent
            preventStealing: true

            property real startX: 0
            property real startY: 0
            property real startTime: 0

            onPressed: (mouse) => {
                startX = mouse.x
                startY = mouse.y
                startTime = Date.now()

                var normX = Math.max(0.0, Math.min(1.0, mouse.x / bg.width))
                var normY = Math.max(0.0, Math.min(1.0, 1.0 - (mouse.y / bg.height)))
                if (Bridge.automator === "circle") {
                    Bridge.setOrbitAttractor(normX, normY)
                } else {
                    Bridge.setCoordinates(normX, normY)
                }
            }

            onPositionChanged: (mouse) => {
                if (pressed) {
                    var normX = Math.max(0.0, Math.min(1.0, mouse.x / bg.width))
                    var normY = Math.max(0.0, Math.min(1.0, 1.0 - (mouse.y / bg.height)))
                    Bridge.setCoordinates(normX, normY)
                }
            }

            onReleased: (mouse) => {
                var now = Date.now()
                var dt = Math.max(16, now - startTime) / 1000.0
                var totalDist = Math.hypot(mouse.x - startX, mouse.y - startY)

                var normX = Math.max(0.0, Math.min(1.0, mouse.x / bg.width))
                var normY = Math.max(0.0, Math.min(1.0, 1.0 - (mouse.y / bg.height)))

                if (Bridge.automator === "circle") {
                    if (totalDist >= ScaleMetrics.dp(16)) {
                        // Fling gesture: compute release velocity vector
                        var dx = (mouse.x - startX) / bg.width
                        var dy = -(mouse.y - startY) / bg.height // invert Y
                        var vx = (dx / dt) * 0.45
                        var vy = (dy / dt) * 0.45
                        Bridge.fling(normX, normY, vx, vy)
                    } else {
                        // Stationary tap: relocate attractor center
                        Bridge.setOrbitAttractor(normX, normY)
                    }
                }
            }
        }
    }

    // Corner badge component with reactive glow
    component CornerGlowBadge: Rectangle {
        id: cRoot
        property string toneName: "TONE"
        property string toneSub: "CORNER"
        property color toneColor: Theme.tone1
        property int level: 0
        property bool alignRight: false

        width: ScaleMetrics.dp(95)
        height: ScaleMetrics.dp(42)
        radius: ScaleMetrics.dp(6)
        color: Qt.rgba(cRoot.toneColor.r, cRoot.toneColor.g, cRoot.toneColor.b, 0.08 + (cRoot.level / 127) * 0.22)
        border.color: Qt.rgba(cRoot.toneColor.r, cRoot.toneColor.g, cRoot.toneColor.b, 0.25 + (cRoot.level / 127) * 0.75)
        border.width: ScaleMetrics.dp(1)

        Column {
            anchors.centerIn: parent
            spacing: ScaleMetrics.dp(2)

            Text {
                text: cRoot.toneName
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(12)
                color: cRoot.toneColor
                horizontalAlignment: cRoot.alignRight ? Text.AlignRight : Text.AlignLeft
            }
            Text {
                text: cRoot.toneSub + " (" + cRoot.level + ")"
                font.pixelSize: ScaleMetrics.sp(8)
                font.family: Theme.fontMono
                color: Theme.textSecondary
                horizontalAlignment: cRoot.alignRight ? Text.AlignRight : Text.AlignLeft
            }
        }
    }
}
