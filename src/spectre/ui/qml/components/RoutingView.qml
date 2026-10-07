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

    property string activePreset: Bridge.routingPreset
    property bool isManualUnlocked: Bridge.manualRoutingUnlocked
    property var pitfalls: Bridge.routingPitfalls
    property int selectedToneTab: 0 // 0: Link All, 1: Tone 1, 2: Tone 2, 3: Tone 3, 4: Tone 4

    Connections {
        target: Bridge
        function onRoutingChanged() {
            root.activePreset = Bridge.routingPreset;
            root.isManualUnlocked = Bridge.manualRoutingUnlocked;
            root.pitfalls = Bridge.routingPitfalls;
            schematicCanvas.requestPaint();
        }
        function onMfxParamsChanged() {
            schematicCanvas.requestPaint();
        }
        function onChorusParamsChanged() {
            schematicCanvas.requestPaint();
        }
        function onReverbParamsChanged() {
            schematicCanvas.requestPaint();
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: ScaleMetrics.dp(10)
        spacing: ScaleMetrics.dp(8)

        // =====================================================================
        // 1. TOP BAR: TITLE, PRESETS & MANUAL UNLOCK
        // =====================================================================
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(8)

            // Header Indicator
            Rectangle {
                width: ScaleMetrics.dp(8)
                height: ScaleMetrics.dp(8)
                radius: 4
                color: "#06b6d4" // Cyan
            }

            Text {
                text: "SIGNAL ROUTING & BUS MATRIX"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(11)
                font.letterSpacing: 1.1
                color: Theme.textPrimary
            }

            Item { Layout.fillWidth: true }

            // Preset Algorithm Chips
            RowLayout {
                spacing: ScaleMetrics.dp(4)

                Repeater {
                    model: [
                        { id: "SERIAL_CHAIN", label: "SERIAL CHAIN", glyph: "🔗", desc: "Tones ➔ MFX ➔ Chorus ➔ Reverb ➔ Out" },
                        { id: "STUDIO_AUX", label: "STUDIO AUX", glyph: "🔀", desc: "MFX Insert + Parallel Cho & Rev Sends" },
                        { id: "VINTAGE_SYNTH", label: "VINTAGE SYNTH", glyph: "⚡", desc: "Direct Out + Parallel Sends (MFX Muted)" },
                        { id: "AMBIENT_WASH", label: "AMBIENT WASH", glyph: "🌌", desc: "Chorus 100% into Reverb Tank" }
                    ]

                    delegate: Rectangle {
                        height: ScaleMetrics.dp(26)
                        width: ScaleMetrics.dp(124)
                        radius: ScaleMetrics.dp(4)
                        color: root.activePreset === modelData.id ? "#0e3a47" : Theme.bgApp
                        border.color: root.activePreset === modelData.id ? "#06b6d4" : Theme.borderCard
                        border.width: 1

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: ScaleMetrics.dp(4)

                            Text {
                                text: modelData.glyph
                                font.pixelSize: ScaleMetrics.sp(9)
                            }
                            Text {
                                text: modelData.label
                                font.bold: root.activePreset === modelData.id
                                font.pixelSize: ScaleMetrics.sp(8)
                                color: root.activePreset === modelData.id ? "#ffffff" : Theme.textSecondary
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: Bridge.applyRoutingPreset(modelData.id)
                        }
                    }
                }
            }

            // Manual Mode Unlock Toggle Button
            Rectangle {
                height: ScaleMetrics.dp(26)
                width: ScaleMetrics.dp(130)
                radius: ScaleMetrics.dp(4)
                color: root.isManualUnlocked ? "#2e1a06" : Theme.bgApp
                border.color: root.isManualUnlocked ? Theme.warning : Theme.borderCard
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: ScaleMetrics.dp(4)

                    Text {
                        text: root.isManualUnlocked ? "🔓" : "🔒"
                        font.pixelSize: ScaleMetrics.sp(10)
                    }
                    Text {
                        text: root.isManualUnlocked ? "MANUAL: UNLOCKED" : "MANUAL: LOCKED"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: root.isManualUnlocked ? Theme.warning : Theme.textDim
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: Bridge.setManualRoutingUnlocked(!root.isManualUnlocked)
                }
            }
        }

        // =====================================================================
        // 2. INTERACTIVE SIGNAL FLOW SCHEMATIC & PITFALL DETECTOR
        // =====================================================================
        Rectangle {
            id: schematicCard
            Layout.fillWidth: true
            height: ScaleMetrics.dp(195)
            radius: ScaleMetrics.dp(6)
            color: "#070a0f"
            border.color: Theme.borderCard
            border.width: 1
            clip: true

            // Compute active warning (prioritizing true warning/caution over info)
            property var activeWarning: {
                if (!root.pitfalls || root.pitfalls.length === 0) return null;
                for (var i = 0; i < root.pitfalls.length; ++i) {
                    if (root.pitfalls[i].severity === "warning") return root.pitfalls[i];
                }
                for (var j = 0; j < root.pitfalls.length; ++j) {
                    if (root.pitfalls[j].severity === "caution") return root.pitfalls[j];
                }
                return null;
            }

            property var activeInfo: {
                if (!root.pitfalls || root.pitfalls.length === 0) return null;
                for (var i = 0; i < root.pitfalls.length; ++i) {
                    if (root.pitfalls[i].severity === "info") return root.pitfalls[i];
                }
                return null;
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(6)
                spacing: ScaleMetrics.dp(4)

                // Schematic Canvas Area
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    Canvas {
                        id: schematicCanvas
                        anchors.fill: parent
                        renderTarget: Canvas.FramebufferObject

                        onPaint: {
                            var ctx = getContext("2d");
                            ctx.clearRect(0, 0, width, height);

                            var nodeW = nodeTones.width;
                            var nodeH = nodeTones.height;

                            var nTones = { x: nodeTones.x + nodesRow.x + nodeW / 2, y: nodeTones.y + nodesRow.y + nodeH / 2, w: nodeW, h: nodeH };
                            var nMfx   = { x: nodeMfx.x   + nodesRow.x + nodeW / 2, y: nodeMfx.y   + nodesRow.y + nodeH / 2, w: nodeW, h: nodeH };
                            var nCho   = { x: nodeCho.x   + nodesRow.x + nodeW / 2, y: nodeCho.y   + nodesRow.y + nodeH / 2, w: nodeW, h: nodeH };
                            var nRev   = { x: nodeRev.x   + nodesRow.x + nodeW / 2, y: nodeRev.y   + nodesRow.y + nodeH / 2, w: nodeW, h: nodeH };
                            var nOut   = { x: nodeOut.x   + nodesRow.x + nodeW / 2, y: nodeOut.y   + nodesRow.y + nodeH / 2, w: nodeW, h: nodeH };

                            var mfxDry = Bridge.mfxDrySend;
                            var mfxCho = Bridge.mfxChorusSend;
                            var mfxRev = Bridge.mfxReverbSend;
                            var choToRev = Bridge.chorusToReverb;
                            var choLvl = Bridge.chorusLevel;
                            var revLvl = Bridge.reverbLevel;
                            var mfxBypassed = Bridge.mfxBypassed;

                            var tones = Bridge.toneOutputAssigns;
                            var toneCho = Bridge.toneChorusSends;
                            var toneRev = Bridge.toneReverbSends;

                            var toneToMfx = false;
                            var toneToOut = false;
                            var toneToCho = false;
                            var toneToRev = false;

                            if (tones && tones.length) {
                                for (var i = 0; i < tones.length; i++) {
                                    if (tones[i] === 0 || tones[i] === 2) toneToMfx = true;
                                    if (tones[i] === 1 || tones[i] === 2) toneToOut = true;
                                    if (toneCho && toneCho[i] > 0) toneToCho = true;
                                    if (toneRev && toneRev[i] > 0) toneToRev = true;
                                }
                            }

                            // Dedicated Bus Tracks (Non-overlapping horizontal coordinates)
                            var nodeTop = nTones.y - nodeH / 2;
                            var nodeBot = nTones.y + nodeH / 2;

                            var trackTop1 = nodeTop - ScaleMetrics.dp(36); // Tones Direct Out
                            var trackTop2 = nodeTop - ScaleMetrics.dp(24); // MFX Dry Out
                            var trackTop3 = nodeTop - ScaleMetrics.dp(12); // Chorus Main Out

                            var trackBot1 = nodeBot + ScaleMetrics.dp(12); // Tones -> Chorus Send
                            var trackBot2 = nodeBot + ScaleMetrics.dp(24); // MFX -> Reverb Send
                            var trackBot3 = nodeBot + ScaleMetrics.dp(36); // Tones -> Reverb Send

                            var r = ScaleMetrics.dp(6);
                            var arrowSize = ScaleMetrics.dp(3.5);

                            // Helper: Draw straight horizontal wire between adjacent nodes
                            function drawStraightWire(x1, y1, x2, y2, active, colorHex) {
                                ctx.beginPath();
                                ctx.strokeStyle = active ? colorHex : "#161d28";
                                ctx.lineWidth = active ? ScaleMetrics.dp(2.5) : ScaleMetrics.dp(1.2);
                                ctx.lineCap = "round";
                                ctx.moveTo(x1, y1);
                                ctx.lineTo(x2, y2);
                                ctx.stroke();

                                // Arrowhead
                                ctx.fillStyle = active ? colorHex : "#222c3d";
                                ctx.beginPath();
                                ctx.moveTo(x2, y2);
                                ctx.lineTo(x2 - arrowSize * 1.5, y2 - arrowSize);
                                ctx.lineTo(x2 - arrowSize * 1.5, y2 + arrowSize);
                                ctx.closePath();
                                ctx.fill();
                            }

                            // Helper: Draw orthogonal Manhattan wire with rounded 90-degree corners
                            function drawManhattanWire(x1, y1, trackY, x2, y2, active, colorHex, enterFromTop, enterFromBottom) {
                                ctx.beginPath();
                                ctx.strokeStyle = active ? colorHex : "#161d28";
                                ctx.lineWidth = active ? ScaleMetrics.dp(2.0) : ScaleMetrics.dp(1.0);
                                ctx.lineCap = "round";
                                ctx.lineJoin = "round";

                                ctx.moveTo(x1, y1);
                                ctx.arcTo(x1, trackY, x2, trackY, r);
                                ctx.arcTo(x2, trackY, x2, y2, r);
                                ctx.lineTo(x2, y2);
                                ctx.stroke();

                                // Arrowhead
                                ctx.fillStyle = active ? colorHex : "#222c3d";
                                ctx.beginPath();
                                if (enterFromTop) {
                                    ctx.moveTo(x2, y2);
                                    ctx.lineTo(x2 - arrowSize, y2 - arrowSize * 1.5);
                                    ctx.lineTo(x2 + arrowSize, y2 - arrowSize * 1.5);
                                } else if (enterFromBottom) {
                                    ctx.moveTo(x2, y2);
                                    ctx.lineTo(x2 - arrowSize, y2 + arrowSize * 1.5);
                                    ctx.lineTo(x2 + arrowSize, y2 + arrowSize * 1.5);
                                }
                                ctx.closePath();
                                ctx.fill();
                            }

                            // --- UPPER BUS TRACKS (BYPASS ROUTES TO OUTPUT) ---
                            // 1. Tones -> Direct Out (Track Top 1)
                            drawManhattanWire(nTones.x, nodeTop, trackTop1, nOut.x - ScaleMetrics.dp(16), nodeTop, toneToOut, "#00e5ff", true, false);

                            // 2. MFX -> Output Dry (Track Top 2)
                            drawManhattanWire(nMfx.x, nodeTop, trackTop2, nOut.x, nodeTop, mfxDry > 0 && !mfxBypassed, "#10b981", true, false);

                            // 3. Chorus -> Main Out (Track Top 3)
                            var choToMain = (choToRev === 0 || choToRev === 2) && choLvl > 0 && Bridge.chorusType > 0;
                            drawManhattanWire(nCho.x, nodeTop, trackTop3, nOut.x + ScaleMetrics.dp(16), nodeTop, choToMain, "#38bdf8", true, false);

                            // --- LOWER BUS TRACKS (AUX SENDS) ---
                            // 4. Tones -> Chorus Send (Track Bot 1)
                            drawManhattanWire(nTones.x - ScaleMetrics.dp(10), nodeBot, trackBot1, nCho.x, nodeBot, toneToCho, "#38bdf8", false, true);

                            // 5. MFX -> Reverb Send (Track Bot 2)
                            drawManhattanWire(nMfx.x, nodeBot, trackBot2, nRev.x + ScaleMetrics.dp(10), nodeBot, mfxRev > 0 && !mfxBypassed, "#a855f7", false, true);

                            // 6. Tones -> Reverb Send (Track Bot 3)
                            drawManhattanWire(nTones.x + ScaleMetrics.dp(10), nodeBot, trackBot3, nRev.x - ScaleMetrics.dp(10), nodeBot, toneToRev, "#c084fc", false, true);

                            // --- MAIN SERIAL HORIZONTAL MIDLINE ---
                            // 7. Tones -> MFX
                            drawStraightWire(nTones.x + nodeW / 2, nTones.y, nMfx.x - nodeW / 2, nMfx.y, toneToMfx, "#00e5ff");

                            // 8. MFX -> Chorus
                            drawStraightWire(nMfx.x + nodeW / 2, nMfx.y, nCho.x - nodeW / 2, nCho.y, mfxCho > 0 && !mfxBypassed, "#ec4899");

                            // 9. Chorus -> Reverb
                            var choToRevActive = (choToRev === 1 || choToRev === 2) && choLvl > 0 && Bridge.chorusType > 0;
                            drawStraightWire(nCho.x + nodeW / 2, nCho.y, nRev.x - nodeW / 2, nRev.y, choToRevActive, "#a855f7");

                            // 10. Reverb -> Main Out
                            var revToOutActive = revLvl > 0 && Bridge.reverbType > 0;
                            drawStraightWire(nRev.x + nodeW / 2, nRev.y, nOut.x - nodeW / 2, nOut.y, revToOutActive, "#10b981");
                        }
                    }

                    // Interactive Node Cards
                    RowLayout {
                        id: nodesRow
                        anchors.fill: parent
                        anchors.leftMargin: ScaleMetrics.dp(24)
                        anchors.rightMargin: ScaleMetrics.dp(24)
                        spacing: 0

                        SchematicNode {
                            id: nodeTones
                            Layout.preferredWidth: ScaleMetrics.dp(74)
                            height: ScaleMetrics.dp(26)
                            title: "TONES"
                            accentColor: "#00e5ff"
                        }

                        Item { Layout.fillWidth: true }

                        SchematicNode {
                            id: nodeMfx
                            Layout.preferredWidth: ScaleMetrics.dp(74)
                            height: ScaleMetrics.dp(26)
                            title: "MFX"
                            accentColor: "#ec4899"
                        }

                        Item { Layout.fillWidth: true }

                        SchematicNode {
                            id: nodeCho
                            Layout.preferredWidth: ScaleMetrics.dp(74)
                            height: ScaleMetrics.dp(26)
                            title: "CHORUS"
                            accentColor: "#38bdf8"
                        }

                        Item { Layout.fillWidth: true }

                        SchematicNode {
                            id: nodeRev
                            Layout.preferredWidth: ScaleMetrics.dp(74)
                            height: ScaleMetrics.dp(26)
                            title: "REVERB"
                            accentColor: "#a855f7"
                        }

                        Item { Layout.fillWidth: true }

                        SchematicNode {
                            id: nodeOut
                            Layout.preferredWidth: ScaleMetrics.dp(74)
                            height: ScaleMetrics.dp(26)
                            title: "OUTPUT"
                            accentColor: "#10b981"
                        }
                    }
                }

                // Diagnostics / Pitfalls Alert Strip
                Rectangle {
                    Layout.fillWidth: true
                    height: ScaleMetrics.dp(24)
                    radius: ScaleMetrics.dp(3)
                    color: schematicCard.activeWarning ?
                        (schematicCard.activeWarning.severity === "warning" ? "#3b1212" : "#2d2305") :
                        (schematicCard.activeInfo ? "#0b202e" : "#092419")
                    border.color: schematicCard.activeWarning ?
                        (schematicCard.activeWarning.severity === "warning" ? Theme.recording : Theme.warning) :
                        (schematicCard.activeInfo ? "#06b6d4" : "#10b981")
                    border.width: 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: ScaleMetrics.dp(8)
                        anchors.rightMargin: ScaleMetrics.dp(8)
                        spacing: ScaleMetrics.dp(6)

                        Text {
                            text: schematicCard.activeWarning ? "⚠️" : (schematicCard.activeInfo ? "ℹ️" : "✓")
                            font.pixelSize: ScaleMetrics.sp(10)
                        }

                        Text {
                            Layout.fillWidth: true
                            text: schematicCard.activeWarning ?
                                (schematicCard.activeWarning.title + " — " + schematicCard.activeWarning.description) :
                                (schematicCard.activeInfo ?
                                    (schematicCard.activeInfo.title + " — " + schematicCard.activeInfo.description) :
                                    "CLEAN SIGNAL ROUTING — No parallel phase cancellation or reverb overloading detected.")
                            font.family: Theme.fontMono
                            font.pixelSize: ScaleMetrics.sp(8)
                            font.bold: true
                            color: schematicCard.activeWarning ?
                                (schematicCard.activeWarning.severity === "warning" ? "#fca5a5" : "#fef08a") :
                                (schematicCard.activeInfo ? "#67e8f9" : "#86efac")
                        }
                    }
                }
            }
        }

        // =====================================================================
        // 3. 4-STAGE COLUMN CHANNEL STRIPS (MANUAL SENDS EDITOR)
        // =====================================================================
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: ScaleMetrics.dp(8)
            opacity: root.isManualUnlocked ? 1.0 : 0.65

            // -----------------------------------------------------------------
            // STAGE 1: TONES
            // -----------------------------------------------------------------
            RoutingStageCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                stageNumber: "1"
                stageTitle: "TONES (1-4)"
                accentColor: "#00e5ff"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(8)
                    spacing: ScaleMetrics.dp(6)

                    // Sub-tab: Link All vs Tone 1..4
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 2

                        Repeater {
                            model: ["ALL", "T1", "T2", "T3", "T4"]
                            delegate: Rectangle {
                                Layout.fillWidth: true
                                height: ScaleMetrics.dp(20)
                                radius: 2
                                color: root.selectedToneTab === index ? "#00e5ff" : "#131922"
                                border.color: root.selectedToneTab === index ? "#ffffff" : Theme.borderCard
                                border.width: 1

                                Text {
                                    anchors.centerIn: parent
                                    text: modelData
                                    font.bold: true
                                    font.pixelSize: ScaleMetrics.sp(7)
                                    color: root.selectedToneTab === index ? "#000000" : Theme.textDim
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: root.selectedToneTab = index
                                }
                            }
                        }
                    }

                    // Output Assign Selector
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: ScaleMetrics.dp(4)

                        Text {
                            text: "ASSIGN:"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: Theme.textDim
                        }
                        Item { Layout.fillWidth: true }

                        Repeater {
                            model: [
                                { id: 0, label: "MFX" },
                                { id: 1, label: "DIRECT" },
                                { id: 2, label: "BOTH" }
                            ]
                            delegate: Rectangle {
                                Layout.preferredWidth: ScaleMetrics.dp(44)
                                height: ScaleMetrics.dp(20)
                                radius: 3
                                property int curAssign: {
                                    if (!Bridge.toneOutputAssigns || Bridge.toneOutputAssigns.length === 0) return 0;
                                    if (root.selectedToneTab === 0) {
                                        var a = Bridge.toneOutputAssigns;
                                        var hasMfx = false, hasDirect = false;
                                        for (var i = 0; i < a.length; ++i) {
                                            if (a[i] === 0) hasMfx = true;
                                            else if (a[i] === 1) hasDirect = true;
                                            else if (a[i] === 2) { hasMfx = true; hasDirect = true; }
                                        }
                                        if (hasMfx && hasDirect) return 2; // BOTH
                                        if (hasDirect) return 1;
                                        return 0;
                                    }
                                    return Bridge.toneOutputAssigns[root.selectedToneTab - 1];
                                }
                                color: curAssign === modelData.id ? "#00e5ff" : "#10141d"
                                border.color: curAssign === modelData.id ? "#ffffff" : Theme.borderCard
                                border.width: 1

                                Text {
                                    anchors.centerIn: parent
                                    text: modelData.label
                                    font.bold: true
                                    font.pixelSize: ScaleMetrics.sp(7)
                                    color: parent.curAssign === modelData.id ? "#000000" : Theme.textDim
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    enabled: root.isManualUnlocked
                                    onClicked: Bridge.setToneRoutingParam(root.selectedToneTab, "assign", modelData.id)
                                }
                            }
                        }
                    }

                    // Tone Output Level Slider
                    SendSlider {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        label: "OUT LEVEL"
                        accent: "#00e5ff"
                        val: {
                            if (!Bridge.toneOutputLevels || Bridge.toneOutputLevels.length === 0) return 127;
                            return root.selectedToneTab === 0 ? Bridge.toneOutputLevels[0] : Bridge.toneOutputLevels[root.selectedToneTab - 1];
                        }
                        enabled: root.isManualUnlocked
                        onMoved: (v) => Bridge.setToneRoutingParam(root.selectedToneTab, "level", v)
                    }

                    // Tone Chorus Send Slider
                    SendSlider {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        label: "CHORUS SEND"
                        accent: "#38bdf8"
                        val: {
                            if (!Bridge.toneChorusSends || Bridge.toneChorusSends.length === 0) return 0;
                            return root.selectedToneTab === 0 ? Bridge.toneChorusSends[0] : Bridge.toneChorusSends[root.selectedToneTab - 1];
                        }
                        enabled: root.isManualUnlocked
                        onMoved: (v) => Bridge.setToneRoutingParam(root.selectedToneTab, "chorusSend", v)
                    }

                    // Tone Reverb Send Slider
                    SendSlider {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        label: "REVERB SEND"
                        accent: "#a855f7"
                        val: {
                            if (!Bridge.toneReverbSends || Bridge.toneReverbSends.length === 0) return 0;
                            return root.selectedToneTab === 0 ? Bridge.toneReverbSends[0] : Bridge.toneReverbSends[root.selectedToneTab - 1];
                        }
                        enabled: root.isManualUnlocked
                        onMoved: (v) => Bridge.setToneRoutingParam(root.selectedToneTab, "reverbSend", v)
                    }
                }
            }

            // -----------------------------------------------------------------
            // STAGE 2: MFX
            // -----------------------------------------------------------------
            RoutingStageCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                stageNumber: "2"
                stageTitle: "MFX PROCESSOR"
                accentColor: "#ec4899"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(8)
                    spacing: ScaleMetrics.dp(6)

                    // Algo Info Badge
                    Rectangle {
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(20)
                        radius: 3
                        color: "#1c0d16"
                        border.color: "#ec4899"
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: Bridge.mfxBypassed ? "BYPASSED (THRU)" : Bridge.mfxAlgoName
                            font.family: Theme.fontMono
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: "#ec4899"
                            elide: Text.ElideRight
                        }
                    }

                    // MFX Dry / Main Out Level Slider
                    SendSlider {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        label: "MAIN OUT LVL"
                        accent: "#10b981"
                        val: Bridge.mfxDrySend
                        enabled: root.isManualUnlocked
                        onMoved: (v) => Bridge.setMfxSend("dry", v)
                    }

                    // MFX Chorus Send Slider
                    SendSlider {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        label: "CHORUS SEND"
                        accent: "#38bdf8"
                        val: Bridge.mfxChorusSend
                        enabled: root.isManualUnlocked
                        onMoved: (v) => Bridge.setMfxSend("chorus", v)
                    }

                    // MFX Reverb Send Slider
                    SendSlider {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        label: "REVERB SEND"
                        accent: "#a855f7"
                        val: Bridge.mfxReverbSend
                        enabled: root.isManualUnlocked
                        onMoved: (v) => Bridge.setMfxSend("reverb", v)
                    }
                }
            }

            // -----------------------------------------------------------------
            // STAGE 3: CHORUS
            // -----------------------------------------------------------------
            RoutingStageCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                stageNumber: "3"
                stageTitle: "MASTER CHORUS"
                accentColor: "#38bdf8"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(8)
                    spacing: ScaleMetrics.dp(6)

                    // Chorus Type Badge
                    Rectangle {
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(20)
                        radius: 3
                        color: "#081d28"
                        border.color: "#38bdf8"
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: Bridge.chorusTypeName
                            font.family: Theme.fontMono
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: "#38bdf8"
                        }
                    }

                    // Chorus Output Level Slider
                    SendSlider {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        label: "CHORUS LEVEL"
                        accent: "#38bdf8"
                        val: Bridge.chorusLevel
                        enabled: root.isManualUnlocked
                        onMoved: (v) => Bridge.setChorusParam("level", v)
                    }

                    // Output Destination Selector
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: ScaleMetrics.dp(4)

                        Text {
                            text: "DEST:"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: Theme.textDim
                        }
                        Item { Layout.fillWidth: true }

                        Repeater {
                            model: ["MAIN", "REV", "MAIN+REV"]
                            delegate: Rectangle {
                                Layout.preferredWidth: ScaleMetrics.dp(48)
                                height: ScaleMetrics.dp(20)
                                radius: 3
                                color: Bridge.chorusToReverb === index ? "#38bdf8" : "#10141d"
                                border.color: Bridge.chorusToReverb === index ? "#ffffff" : Theme.borderCard
                                border.width: 1

                                Text {
                                    anchors.centerIn: parent
                                    text: modelData
                                    font.bold: true
                                    font.pixelSize: ScaleMetrics.sp(7)
                                    color: Bridge.chorusToReverb === index ? "#000000" : Theme.textDim
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    enabled: root.isManualUnlocked
                                    onClicked: Bridge.setChorusParam("toReverb", index)
                                }
                            }
                        }
                    }

                    // Explanation Note
                    Rectangle {
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(22)
                        radius: 3
                        color: "#0a0e17"
                        border.color: Theme.borderCard
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: Bridge.chorusToReverb === 0 ? "STEREO ➔ MAIN OUT" : (Bridge.chorusToReverb === 1 ? "MONO ➔ REVERB ONLY" : "STEREO OUT + MONO REVERB")
                            font.family: Theme.fontMono
                            font.pixelSize: ScaleMetrics.sp(7)
                            color: "#38bdf8"
                        }
                    }
                }
            }

            // -----------------------------------------------------------------
            // STAGE 4: REVERB & MASTER
            // -----------------------------------------------------------------
            RoutingStageCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                stageNumber: "4"
                stageTitle: "REVERB & OUT"
                accentColor: "#a855f7"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(8)
                    spacing: ScaleMetrics.dp(6)

                    // Reverb Type Badge
                    Rectangle {
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(20)
                        radius: 3
                        color: "#1c0d28"
                        border.color: "#a855f7"
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: Bridge.reverbTypeName
                            font.family: Theme.fontMono
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: "#a855f7"
                        }
                    }

                    // Reverb Level Slider
                    SendSlider {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        label: "REVERB LEVEL"
                        accent: "#a855f7"
                        val: Bridge.reverbLevel
                        enabled: root.isManualUnlocked
                        onMoved: (v) => Bridge.setReverbParam("level", v)
                    }

                    // Master Output Readout (patch level, real SysEx param)
                    Rectangle {
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(22)
                        radius: 3
                        color: "#0a0e17"
                        border.color: Theme.borderCard
                        border.width: 1

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: ScaleMetrics.dp(4)
                            Text {
                                text: "MAIN GAIN: " + Bridge.masterLevel + " / 127"
                                font.family: Theme.fontMono
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(7)
                                color: Theme.textSecondary
                            }
                        }
                    }
                }
            }
        }
    }

    // =========================================================================
    // SUB-COMPONENTS
    // =========================================================================

    // Stage Column Container Card
    component RoutingStageCard: Rectangle {
        property string stageNumber: "1"
        property string stageTitle: "STAGE"
        property color accentColor: "#00e5ff"
        default property alias content: innerContainer.data

        radius: ScaleMetrics.dp(6)
        color: Theme.bgApp
        border.color: Theme.borderCard
        border.width: 1

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            // Stage Header
            Rectangle {
                Layout.fillWidth: true
                height: ScaleMetrics.dp(24)
                color: "#0b0f16"
                border.color: Theme.borderCard
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: ScaleMetrics.dp(8)
                    anchors.rightMargin: ScaleMetrics.dp(8)
                    spacing: ScaleMetrics.dp(4)

                    Rectangle {
                        width: ScaleMetrics.dp(14)
                        height: ScaleMetrics.dp(14)
                        radius: 2
                        color: accentColor
                        Text {
                            anchors.centerIn: parent
                            text: stageNumber
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: "#000000"
                        }
                    }

                    Text {
                        text: stageTitle
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        font.letterSpacing: 1.0
                        color: Theme.textPrimary
                    }
                }
            }

            Item {
                id: innerContainer
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
        }
    }

    // Schematic Visual Node Chip
    component SchematicNode: Rectangle {
        property string title: "NODE"
        property color accentColor: "#00e5ff"

        radius: ScaleMetrics.dp(4)
        color: "#0f141f"
        border.color: accentColor
        border.width: 1

        Text {
            anchors.centerIn: parent
            text: title
            font.bold: true
            font.pixelSize: ScaleMetrics.sp(8)
            font.letterSpacing: 1.0
            color: accentColor
            horizontalAlignment: Text.AlignHCenter
        }
    }

    // Reusable Send / Level Slider
    component SendSlider: Item {
        id: ss
        property string label: "SEND"
        property int val: 0
        property int minVal: 0
        property int maxVal: 127
        property color accent: "#00e5ff"
        signal moved(int v)

        implicitHeight: ScaleMetrics.dp(36)

        ColumnLayout {
            anchors.fill: parent
            spacing: ScaleMetrics.dp(2)

            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: ss.label
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(7)
                    color: Theme.textDim
                }
                Item { Layout.fillWidth: true }
                Text {
                    text: ss.val.toString()
                    font.family: Theme.fontMono
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: ss.accent
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
                    width: parent.width * Math.max(0.0, Math.min(1.0, (ss.val - ss.minVal) / Math.max(1, ss.maxVal - ss.minVal)))
                    height: parent.height
                    radius: 3
                    color: ss.accent
                    opacity: 0.40
                }

                function updateVal(mouseX) {
                    var norm = Math.max(0.0, Math.min(1.0, mouseX / width));
                    var v = Math.round(ss.minVal + norm * (ss.maxVal - ss.minVal));
                    ss.moved(v);
                }

                MouseArea {
                    anchors.fill: parent
                    enabled: ss.enabled
                    onPositionChanged: (mouse) => { if (pressed) parent.updateVal(mouse.x); }
                    onPressed: (mouse) => { parent.updateVal(mouse.x); }
                }
            }
        }
    }
}
