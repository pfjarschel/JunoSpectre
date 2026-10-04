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

    property var steps: Bridge.stepLfoSteps
    property int currentPlayhead: 0
    property int curveType: Bridge.stepLfoCurve
    property int syncRateIdx: Bridge.stepLfoRateIdx
    property var syncRates: ["OFF (Hz)", "1/32", "1/16", "1/8", "1/4", "1/2", "1/1"]
    property int destIdx: Bridge.stepLfoDestIdx
    property var destNames: ["PITCH", "TVF CUTOFF", "TVA LEVEL", "PAN"]
    property int depthVal: Bridge.stepLfoDepth

    // Internal simulation timer for playhead animation
    Timer {
        id: playheadTimer
        interval: 120
        running: true
        repeat: true
        onTriggered: root.currentPlayhead = (root.currentPlayhead + 1) % 16
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: ScaleMetrics.dp(10)
        spacing: ScaleMetrics.dp(8)

        // Header and Controls
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(8)

            Rectangle {
                width: ScaleMetrics.dp(8); height: ScaleMetrics.dp(8); radius: 4
                color: "#10b981"
            }
            Text {
                text: "16-STEP PATTERN LFO"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(12)
                font.letterSpacing: 1.2
                color: Theme.textPrimary
            }
            Item { Layout.fillWidth: true }

            // Target Chip
            Rectangle {
                height: ScaleMetrics.dp(24)
                implicitWidth: ScaleMetrics.dp(110)
                radius: 4
                color: "#10141d"
                border.color: "#10b981"
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: 4
                    Text { text: "DEST:"; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textDim }
                    Text {
                        text: root.destNames[root.destIdx]
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: "#10b981"
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: Bridge.setStepLfoParam("dest", (root.destIdx + 1) % root.destNames.length)
                }
            }

            // Sync Rate Chip
            Rectangle {
                height: ScaleMetrics.dp(24)
                implicitWidth: ScaleMetrics.dp(90)
                radius: 4
                color: "#10141d"
                border.color: Theme.borderCard
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: 4
                    Text { text: "RATE:"; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textDim }
                    Text {
                        text: root.syncRates[root.syncRateIdx]
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Theme.textPrimary
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: Bridge.setStepLfoParam("rate", (root.syncRateIdx + 1) % root.syncRates.length)
                }
            }

            // Curve Mode
            Rectangle {
                height: ScaleMetrics.dp(24)
                implicitWidth: ScaleMetrics.dp(85)
                radius: 4
                color: "#10141d"
                border.color: Theme.borderCard
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: 4
                    Text { text: "CURVE:"; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textDim }
                    Text {
                        text: root.curveType === 0 ? "HOLD" : (root.curveType === 1 ? "LINEAR" : "SMOOTH")
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Theme.tone1
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: Bridge.setStepLfoParam("curve", (root.curveType + 1) % 3)
                }
            }
        }

        // Preset Toolbar
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(4)

            Text {
                text: "SHAPES:"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(8)
                color: Theme.textDim
            }

            Repeater {
                model: [
                    { name: "SINE", fn: () => {
                        var a = [];
                        for(var i=0; i<16; i++) {
                            var v = Math.round(Math.sin((i/16.0)*Math.PI*2) * 60);
                            a.push(v);
                            Bridge.setStepLfoStep(i, v);
                        }
                        root.steps = a;
                    }},
                    { name: "SAW UP", fn: () => {
                        var a = [];
                        for(var i=0; i<16; i++) {
                            var v = Math.round(-60 + (i/15.0)*120);
                            a.push(v);
                            Bridge.setStepLfoStep(i, v);
                        }
                        root.steps = a;
                    }},
                    { name: "SAW DN", fn: () => {
                        var a = [];
                        for(var i=0; i<16; i++) {
                            var v = Math.round(60 - (i/15.0)*120);
                            a.push(v);
                            Bridge.setStepLfoStep(i, v);
                        }
                        root.steps = a;
                    }},
                    { name: "TRI", fn: () => {
                        var a = [];
                        for(var i=0; i<8; i++) {
                            var v1 = Math.round(-60 + (i/7.0)*120);
                            a.push(v1);
                            Bridge.setStepLfoStep(i, v1);
                        }
                        for(var j=8; j<16; j++) {
                            var v2 = Math.round(60 - ((j-8)/7.0)*120);
                            a.push(v2);
                            Bridge.setStepLfoStep(j, v2);
                        }
                        root.steps = a;
                    }},
                    { name: "RANDOM", fn: () => {
                        var a = [];
                        for(var i=0; i<16; i++) {
                            var v = Math.round((Math.random() - 0.5) * 120);
                            a.push(v);
                            Bridge.setStepLfoStep(i, v);
                        }
                        root.steps = a;
                    }},
                    { name: "CLEAR", fn: () => {
                        var a = [];
                        for(var i=0; i<16; i++) {
                            a.push(0);
                            Bridge.setStepLfoStep(i, 0);
                        }
                        root.steps = a;
                    }}
                ]

                delegate: Rectangle {
                    Layout.fillWidth: true
                    height: ScaleMetrics.dp(22)
                    radius: 3
                    color: Theme.bgApp
                    border.color: Theme.borderCard
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: modelData.name
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Theme.textSecondary
                    }
                    MouseArea {
                        anchors.fill: parent
                        onClicked: modelData.fn()
                    }
                }
            }
        }

        // Interactive 16-Step Drawing Grid
        Rectangle {
            id: gridBox
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: ScaleMetrics.dp(6)
            color: "#080b11"
            border.color: Theme.borderCard
            border.width: 1
            clip: true

            // Center zero line
            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                height: 1
                color: "#1e293b"
            }

            // 16 Step Columns
            Row {
                id: stepsRow
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(4)
                spacing: ScaleMetrics.dp(2)

                Repeater {
                    model: 16
                    delegate: Rectangle {
                        id: barCol
                        width: (stepsRow.width - 30) / 16.0
                        height: stepsRow.height
                        color: root.currentPlayhead === index ? Qt.rgba(0.06, 0.72, 0.51, 0.12) : "transparent"
                        radius: 2

                        property int stepVal: root.steps[index] !== undefined ? root.steps[index] : 0

                        // Step bar
                        Rectangle {
                            anchors.horizontalCenter: parent.horizontalCenter
                            width: parent.width - 2
                            property real norm: (barCol.stepVal + 63) / 126.0
                            y: norm >= 0.5 ? parent.height * 0.5 - height : parent.height * 0.5
                            height: Math.max(2, Math.abs((norm - 0.5) * parent.height))
                            color: root.currentPlayhead === index ? "#10b981" : (barCol.stepVal >= 0 ? "#059669" : "#0284c7")
                            radius: 1
                        }

                        // Step index label
                        Text {
                            anchors.bottom: parent.bottom
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: (index + 1).toString()
                            font.family: Theme.fontMono
                            font.pixelSize: ScaleMetrics.sp(7)
                            color: root.currentPlayhead === index ? "#10b981" : Theme.textDim
                        }

                        // Step value label
                        Text {
                            anchors.top: parent.top
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: barCol.stepVal > 0 ? "+" + barCol.stepVal : barCol.stepVal.toString()
                            font.family: Theme.fontMono
                            font.pixelSize: ScaleMetrics.sp(7)
                            color: root.currentPlayhead === index ? Theme.textPrimary : Theme.textDim
                        }
                    }
                }
            }

            // Touch Drag Layer: Allows dragging finger across all 16 bars to "paint" the waveform!
            MouseArea {
                anchors.fill: parent

                function updateStepAt(mx, my) {
                    var colWidth = width / 16.0;
                    var colIdx = Math.max(0, Math.min(15, Math.floor(mx / colWidth)));
                    var norm = 1.0 - (my / height); // 0 at bottom, 1 at top
                    var val = Math.round((norm - 0.5) * 126);
                    val = Math.max(-63, Math.min(63, val));

                    var arr = root.steps.slice();
                    arr[colIdx] = val;
                    root.steps = arr;
                    Bridge.setStepLfoStep(colIdx, val);
                }

                onPositionChanged: (mouse) => {
                    if (pressed) updateStepAt(mouse.x, mouse.y);
                }
                onPressed: (mouse) => updateStepAt(mouse.x, mouse.y)
            }
        }
    }
}
