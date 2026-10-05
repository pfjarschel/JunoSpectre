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
    property int curveType: Bridge.stepLfoCurve
    property int selectedTone: Bridge.selectedTone
    property bool isLinked: Bridge.linkedMode
    property string lfo1Wave: Bridge.lfo1Wave
    property string lfo2Wave: Bridge.lfo2Wave

    Connections {
        target: Bridge
        function onStepLfoChanged() {
            root.steps = Bridge.stepLfoSteps;
            root.curveType = Bridge.stepLfoCurve;
        }
        function onSelectedToneChanged() {
            root.selectedTone = Bridge.selectedTone;
            root.steps = Bridge.stepLfoSteps;
            root.curveType = Bridge.stepLfoCurve;
        }
        function onLinkedModeChanged() {
            root.isLinked = Bridge.linkedMode;
        }
        function onLfoParamsChanged() {
            root.lfo1Wave = Bridge.lfo1Wave;
            root.lfo2Wave = Bridge.lfo2Wave;
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: ScaleMetrics.dp(10)
        spacing: ScaleMetrics.dp(8)

        // =====================================================================
        // Header and Controls
        // =====================================================================
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

            // Tone Selector Pills
            RowLayout {
                spacing: ScaleMetrics.dp(4)
                Text {
                    text: "TONE:"
                    font.pixelSize: ScaleMetrics.sp(8)
                    font.bold: true
                    color: Theme.textDim
                }

                Repeater {
                    model: [
                        { id: 1, label: "T1", col: Theme.tone1 },
                        { id: 2, label: "T2", col: Theme.tone2 },
                        { id: 3, label: "T3", col: Theme.tone3 },
                        { id: 4, label: "T4", col: Theme.tone4 }
                    ]
                    delegate: Rectangle {
                        height: ScaleMetrics.dp(24)
                        implicitWidth: ScaleMetrics.dp(28)
                        radius: 4
                        property bool isSel: root.selectedTone === modelData.id
                        color: isSel ? Qt.rgba(modelData.col.r, modelData.col.g, modelData.col.b, 0.25) : "#10141d"
                        border.color: isSel ? modelData.col : Theme.borderCard
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: modelData.label
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: parent.isSel ? modelData.col : Theme.textDim
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: Bridge.setSelectedTone(modelData.id)
                        }
                    }
                }

                Rectangle {
                    height: ScaleMetrics.dp(24)
                    implicitWidth: ScaleMetrics.dp(64)
                    radius: 4
                    color: root.isLinked ? Qt.rgba(0.66, 0.33, 0.97, 0.25) : "#10141d"
                    border.color: root.isLinked ? "#a855f7" : Theme.borderCard
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: "LINK ALL"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: root.isLinked ? "#c084fc" : Theme.textDim
                    }
                    MouseArea {
                        anchors.fill: parent
                        onClicked: Bridge.setLinkedMode(!Bridge.linkedMode)
                    }
                }
            }

            // Quick Assign Pills
            RowLayout {
                spacing: ScaleMetrics.dp(4)
                Text {
                    text: "ASSIGN:"
                    font.pixelSize: ScaleMetrics.sp(8)
                    font.bold: true
                    color: Theme.textDim
                }

                Rectangle {
                    height: ScaleMetrics.dp(24)
                    implicitWidth: ScaleMetrics.dp(46)
                    radius: 4
                    property bool isActive: root.lfo1Wave === "STEP"
                    color: isActive ? Qt.rgba(0.06, 0.72, 0.51, 0.25) : "#10141d"
                    border.color: isActive ? "#10b981" : Theme.borderCard
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: "LFO 1"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: parent.isActive ? "#10b981" : Theme.textDim
                    }
                    MouseArea {
                        anchors.fill: parent
                        onClicked: Bridge.assignStepLfoToLfo(1)
                    }
                }

                Rectangle {
                    height: ScaleMetrics.dp(24)
                    implicitWidth: ScaleMetrics.dp(46)
                    radius: 4
                    property bool isActive: root.lfo2Wave === "STEP"
                    color: isActive ? Qt.rgba(0.06, 0.72, 0.51, 0.25) : "#10141d"
                    border.color: isActive ? "#10b981" : Theme.borderCard
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: "LFO 2"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: parent.isActive ? "#10b981" : Theme.textDim
                    }
                    MouseArea {
                        anchors.fill: parent
                        onClicked: Bridge.assignStepLfoToLfo(2)
                    }
                }
            }

            // Step Type (Curve) Toggle Chip
            Rectangle {
                height: ScaleMetrics.dp(24)
                implicitWidth: ScaleMetrics.dp(120)
                radius: 4
                color: "#10141d"
                border.color: root.curveType === 0 ? Theme.tone1 : Theme.tone2
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: 4
                    Text { text: "TYPE:"; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textDim }
                    Text {
                        text: root.curveType === 0 ? "STEP (HOLD)" : "GLIDE (SMOOTH)"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: root.curveType === 0 ? Theme.tone1 : Theme.tone2
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: Bridge.setStepLfoParam("curve", root.curveType === 0 ? 1 : 0)
                }
            }
        }

        // =====================================================================
        // Preset Toolbar
        // =====================================================================
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
                            var v = Math.round(Math.sin((i/16.0)*Math.PI*2) * 36);
                            a.push(v);
                        }
                        root.steps = a;
                        Bridge.setStepLfoAllSteps(a);
                    }},
                    { name: "SAW UP", fn: () => {
                        var a = [];
                        for(var i=0; i<16; i++) {
                            var v = Math.round(-36 + (i/15.0)*72);
                            a.push(v);
                        }
                        root.steps = a;
                        Bridge.setStepLfoAllSteps(a);
                    }},
                    { name: "SAW DN", fn: () => {
                        var a = [];
                        for(var i=0; i<16; i++) {
                            var v = Math.round(36 - (i/15.0)*72);
                            a.push(v);
                        }
                        root.steps = a;
                        Bridge.setStepLfoAllSteps(a);
                    }},
                    { name: "TRI", fn: () => {
                        var a = [];
                        for(var i=0; i<8; i++) {
                            var v1 = Math.round(-36 + (i/7.0)*72);
                            a.push(v1);
                        }
                        for(var j=8; j<16; j++) {
                            var v2 = Math.round(36 - ((j-8)/7.0)*72);
                            a.push(v2);
                        }
                        root.steps = a;
                        Bridge.setStepLfoAllSteps(a);
                    }},
                    { name: "RANDOM", fn: () => {
                        var a = [];
                        for(var i=0; i<16; i++) {
                            var v = Math.round((Math.random() - 0.5) * 72);
                            a.push(v);
                        }
                        root.steps = a;
                        Bridge.setStepLfoAllSteps(a);
                    }},
                    { name: "CLEAR", fn: () => {
                        var a = [];
                        for(var i=0; i<16; i++) {
                            a.push(0);
                        }
                        root.steps = a;
                        Bridge.setStepLfoAllSteps(a);
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

        // =====================================================================
        // Interactive 16-Step Drawing Grid
        // =====================================================================
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
                        width: (stepsRow.width - (15 * ScaleMetrics.dp(2))) / 16.0
                        height: stepsRow.height
                        color: "transparent"
                        radius: 2

                        property int stepVal: (root.steps && root.steps[index] !== undefined) ? root.steps[index] : 0

                        // Step bar
                        Rectangle {
                            anchors.horizontalCenter: parent.horizontalCenter
                            width: Math.max(4, parent.width - 2)
                            property real norm: (barCol.stepVal + 36.0) / 72.0
                            y: norm >= 0.5 ? parent.height * 0.5 - height : parent.height * 0.5
                            height: Math.max(2, Math.abs((norm - 0.5) * parent.height))
                            color: barCol.stepVal > 0 ? "#10b981" : (barCol.stepVal < 0 ? "#0284c7" : "#334155")
                            radius: 1
                        }

                        // Step index label
                        Text {
                            anchors.bottom: parent.bottom
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: (index + 1).toString()
                            font.family: Theme.fontMono
                            font.pixelSize: ScaleMetrics.sp(7)
                            color: Theme.textDim
                        }

                        // Step value label
                        Text {
                            anchors.top: parent.top
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: barCol.stepVal > 0 ? "+" + barCol.stepVal : barCol.stepVal.toString()
                            font.family: Theme.fontMono
                            font.pixelSize: ScaleMetrics.sp(7)
                            color: barCol.stepVal !== 0 ? Theme.textPrimary : Theme.textDim
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
                    var val = Math.round((norm - 0.5) * 72);
                    val = Math.max(-36, Math.min(36, val));

                    var arr = (root.steps ? root.steps.slice() : new Array(16).fill(0));
                    if (arr[colIdx] !== val) {
                        arr[colIdx] = val;
                        root.steps = arr;
                        Bridge.setStepLfoStep(colIdx, val);
                    }
                }

                onPositionChanged: (mouse) => {
                    if (pressed) updateStepAt(mouse.x, mouse.y);
                }
                onPressed: (mouse) => updateStepAt(mouse.x, mouse.y)
            }
        }
    }
}
