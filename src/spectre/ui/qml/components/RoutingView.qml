import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

// Signal routing. The schematic draws Bridge.routingGraph (core.routing):
// a wire lights only when sound actually travels it.
Rectangle {
    id: root
    objectName: "routingView"
    color: Theme.bgCard
    radius: ScaleMetrics.dp(8)
    border.color: Theme.borderCard
    border.width: 1

    property var graph: Bridge.routingGraph
    property bool perform: !!(graph && graph.perform)
    property var notes: Bridge.routingPitfalls
    property int selectedToneTab: 0 // 0: ALL, 1..4: tone

    readonly property color cMfx: "#ec4899"
    readonly property color cCho: "#38bdf8"
    readonly property color cRev: "#a855f7"
    readonly property color cOut: "#10b981"
    readonly property color cPart: "#f59e0b"

    // Output assign choices (wire values; see core.routing)
    readonly property var toneAssigns: [
        { id: 0, label: "MFX" }, { id: 1, label: "L+R" }, { id: 5, label: "L" }, { id: 6, label: "R" }
    ]

    function edge(k) {
        return (graph && graph.edges && graph.edges[k]) ? graph.edges[k] : { active: false, level: 0, tones: [] };
    }
    function node(k) {
        return (graph && graph.nodes && graph.nodes[k]) ? graph.nodes[k] : { label: "", hasInput: false, on: false };
    }
    function tone(i) {
        return (graph && graph.tones && graph.tones.length >= i) ? graph.tones[i - 1] : null;
    }
    // Tone shown by the editor: the selected tab, or for ALL the first tone
    // that uses its own output settings
    function shownTone() {
        if (root.selectedToneTab > 0) return tone(root.selectedToneTab);
        for (var i = 1; i <= 4; ++i) {
            var t = tone(i);
            if (t && t.owner === t.index) return t;
        }
        return tone(1);
    }
    function allSame(key) {
        if (!graph || !graph.tones) return true;
        for (var i = 1; i < graph.tones.length; ++i)
            if (graph.tones[i][key] !== graph.tones[0][key]) return false;
        return true;
    }
    function lockText(t) {
        if (!t) return "";
        if (t.lockedBy === "part") return "SET BY PART OUT";
        if (t.lockedBy === "patch") return "SET BY PATCH OUT";
        if (t.lockedBy === "structure") return "FOLLOWS T" + t.owner;
        return "";
    }

    // Node positions settle after layout (mode switch, part node shown or
    // hidden, page shown): repaint once they have, never from stale ones.
    function repaint() { Qt.callLater(schematicCanvas.requestPaint); }
    onGraphChanged: repaint()
    onVisibleChanged: if (visible) repaint()
    onPerformChanged: repaint()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: ScaleMetrics.dp(10)
        spacing: ScaleMetrics.dp(8)

        // =====================================================================
        // 1. TITLE & PRESETS
        // =====================================================================
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(8)

            Rectangle {
                width: ScaleMetrics.dp(8)
                height: ScaleMetrics.dp(8)
                radius: 4
                color: "#06b6d4"
            }
            Text {
                text: root.perform && root.graph.part ? "SIGNAL ROUTING · PART " + root.graph.part.index : "SIGNAL ROUTING"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(11)
                font.letterSpacing: 1.1
                color: Theme.textPrimary
            }
            Item { Layout.fillWidth: true }

            Repeater {
                model: [
                    { id: "SERIAL_CHAIN", label: "SERIAL", desc: "Tones ➔ MFX ➔ Chorus ➔ Reverb ➔ Out" },
                    { id: "STUDIO_AUX", label: "STUDIO AUX", desc: "MFX insert, MFX feeds chorus & reverb" },
                    { id: "VINTAGE_SYNTH", label: "VINTAGE", desc: "Tones direct + their own chorus & reverb sends" },
                    { id: "AMBIENT_WASH", label: "AMBIENT", desc: "Mostly wet MFX, chorus into a big reverb" },
                    { id: "SPLIT_PATH", label: "SPLIT", desc: "T1-2 through MFX, T3-4 direct with sends" },
                    { id: "CLEAN_DIRECT", label: "CLEAN", desc: "Tones direct, no effects" }
                ]
                delegate: Rectangle {
                    readonly property bool sel: Bridge.routingPreset === modelData.id
                    height: ScaleMetrics.dp(26)
                    width: ScaleMetrics.dp(78)
                    radius: ScaleMetrics.dp(4)
                    color: sel ? "#0e3a47" : (presetMa.pressed ? Theme.bgCardActive : Theme.bgApp)
                    border.color: sel ? "#06b6d4" : Theme.borderCard
                    border.width: 1
                    Text {
                        anchors.centerIn: parent
                        text: modelData.label
                        font.bold: parent.sel
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: parent.sel ? "#ffffff" : Theme.textSecondary
                    }
                    MouseArea {
                        id: presetMa
                        anchors.fill: parent
                        onClicked: Bridge.applyRoutingPreset(modelData.id)
                    }
                }
            }
        }

        // =====================================================================
        // 2. SCHEMATIC + NOTES
        // =====================================================================
        Rectangle {
            id: schematicCard
            Layout.fillWidth: true
            Layout.preferredHeight: ScaleMetrics.dp(205)
            radius: ScaleMetrics.dp(6)
            color: "#070a0f"
            border.color: Theme.borderCard
            border.width: 1
            clip: true

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(6)
                spacing: ScaleMetrics.dp(4)

                Item {
                    id: schematicArea
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    Canvas {
                        id: schematicCanvas
                        anchors.fill: parent
                        renderTarget: Canvas.FramebufferObject
                        onWidthChanged: root.repaint()
                        onHeightChanged: root.repaint()

                        onPaint: {
                            var ctx = getContext("2d");
                            ctx.clearRect(0, 0, width, height);
                            if (!root.graph || !root.graph.edges || !root.visible) return;
                            if (nodeOut.x <= nodeTones.x || (root.perform && (!nodePart.visible || nodePart.x <= nodeTones.x)))
                                return root.repaint();  // layout not settled yet

                            // Node centers in canvas coordinates (layout-safe)
                            function c(item) {
                                var p = item.mapToItem(schematicCanvas, item.width / 2, item.height / 2);
                                return { x: p.x, y: p.y, w: item.width, h: item.height };
                            }
                            var nIn = c(root.perform ? nodePart : nodeTones);
                            var nTones = c(nodeTones);
                            var nMfx = c(nodeMfx), nCho = c(nodeCho), nRev = c(nodeRev), nOut = c(nodeOut);
                            var top = nTones.y - nTones.h / 2, bot = nTones.y + nTones.h / 2;
                            var dp = ScaleMetrics.dp(1);
                            var r = 6 * dp, arrow = 3.5 * dp;

                            function width4(level) { return (1.4 + 1.6 * Math.min(127, level) / 127) * dp; }

                            function label(x, y, text, color) {
                                ctx.font = "bold " + Math.round(7 * dp) + "px monospace";
                                ctx.fillStyle = color;
                                ctx.textAlign = "center";
                                ctx.fillText(text, x, y - 2 * dp);
                            }

                            function straight(a, b, e, color) {
                                var x1 = a.x + a.w / 2, x2 = b.x - b.w / 2;
                                ctx.beginPath();
                                ctx.strokeStyle = e.active ? color : "#161d28";
                                ctx.lineWidth = e.active ? width4(e.level) : 1.2 * dp;
                                ctx.lineCap = "round";
                                ctx.moveTo(x1, a.y);
                                ctx.lineTo(x2, b.y);
                                ctx.stroke();
                                ctx.fillStyle = e.active ? color : "#222c3d";
                                ctx.beginPath();
                                ctx.moveTo(x2, b.y);
                                ctx.lineTo(x2 - arrow * 1.5, b.y - arrow);
                                ctx.lineTo(x2 - arrow * 1.5, b.y + arrow);
                                ctx.closePath();
                                ctx.fill();
                                if (e.active && e.level < 127)
                                    label((x1 + x2) / 2, a.y, e.level, color);
                            }

                            // Up/down out of a node, along a bus track, into another
                            function bus(x1, y1, trackY, x2, y2, e, color, fromTop) {
                                ctx.beginPath();
                                ctx.strokeStyle = e.active ? color : "#161d28";
                                ctx.lineWidth = e.active ? width4(e.level) : 1.0 * dp;
                                ctx.lineCap = "round";
                                ctx.lineJoin = "round";
                                ctx.moveTo(x1, y1);
                                ctx.arcTo(x1, trackY, x2, trackY, r);
                                ctx.arcTo(x2, trackY, x2, y2, r);
                                ctx.lineTo(x2, y2);
                                ctx.stroke();
                                ctx.fillStyle = e.active ? color : "#222c3d";
                                ctx.beginPath();
                                var d = fromTop ? -1 : 1;
                                ctx.moveTo(x2, y2);
                                ctx.lineTo(x2 - arrow, y2 + d * arrow * 1.5);
                                ctx.lineTo(x2 + arrow, y2 + d * arrow * 1.5);
                                ctx.closePath();
                                ctx.fill();
                                if (e.active)
                                    label((x1 + x2) / 2, trackY + (fromTop ? 0 : 9 * dp), e.level, color);
                            }

                            // Inactive first so live wires draw on top
                            var wires = [
                                function() { bus(nIn.x, top, top - 36 * dp, nOut.x - 16 * dp, top, root.edge("in->out"), Theme.tone1, true); },
                                function() { bus(nMfx.x, top, top - 24 * dp, nOut.x, top, root.edge("mfx->out"), root.cOut, true); },
                                function() { bus(nCho.x, top, top - 12 * dp, nOut.x + 16 * dp, top, root.edge("cho->out"), root.cCho, true); },
                                function() { bus(nIn.x - 10 * dp, bot, bot + 12 * dp, nCho.x, bot, root.edge("in->cho"), root.cCho, false); },
                                function() { bus(nMfx.x, bot, bot + 24 * dp, nRev.x + 10 * dp, bot, root.edge("mfx->rev"), root.cRev, false); },
                                function() { bus(nIn.x + 10 * dp, bot, bot + 36 * dp, nRev.x - 10 * dp, bot, root.edge("in->rev"), "#c084fc", false); },
                                function() { straight(nIn, nMfx, root.edge("in->mfx"), Theme.tone1); },
                                function() { straight(nMfx, nCho, root.edge("mfx->cho"), root.cMfx); },
                                function() { straight(nCho, nRev, root.edge("cho->rev"), root.cRev); },
                                function() { straight(nRev, nOut, root.edge("rev->out"), root.cOut); }
                            ];
                            var keys = ["in->out", "mfx->out", "cho->out", "in->cho", "mfx->rev", "in->rev",
                                        "in->mfx", "mfx->cho", "cho->rev", "rev->out"];
                            if (root.perform)
                                straight(nTones, nIn, root.edge("in->part"), root.cPart);
                            for (var pass = 0; pass < 2; ++pass)
                                for (var i = 0; i < wires.length; ++i)
                                    if (root.edge(keys[i]).active === (pass === 1)) wires[i]();
                        }
                    }

                    RowLayout {
                        id: nodesRow
                        anchors.fill: parent
                        anchors.leftMargin: ScaleMetrics.dp(24)
                        anchors.rightMargin: ScaleMetrics.dp(24)
                        spacing: 0
                        onWidthChanged: root.repaint()

                        // TONES: one chip per tone, colored by its route
                        Rectangle {
                            id: nodeTones
                            onXChanged: root.repaint()
                            onYChanged: root.repaint()
                            Layout.preferredWidth: ScaleMetrics.dp(86)
                            Layout.preferredHeight: ScaleMetrics.dp(34)
                            radius: ScaleMetrics.dp(4)
                            color: "#0f141f"
                            border.color: Theme.tone1
                            border.width: 1
                            ColumnLayout {
                                anchors.centerIn: parent
                                spacing: ScaleMetrics.dp(2)
                                Text {
                                    Layout.alignment: Qt.AlignHCenter
                                    text: "TONES"
                                    font.bold: true
                                    font.pixelSize: ScaleMetrics.sp(8)
                                    font.letterSpacing: 1.0
                                    color: Theme.tone1
                                }
                                Row {
                                    Layout.alignment: Qt.AlignHCenter
                                    spacing: ScaleMetrics.dp(2)
                                    Repeater {
                                        model: 4
                                        delegate: Rectangle {
                                            readonly property var t: root.tone(index + 1)
                                            width: ScaleMetrics.dp(17)
                                            height: ScaleMetrics.dp(11)
                                            radius: 2
                                            color: !t || !t.sounding ? "#161d28" : (t.direct ? "#0b3a2a" : "#0e3a47")
                                            border.color: !t || !t.sounding ? "#222c3d" : (t.direct ? root.cOut : Theme.tone1)
                                            border.width: 1
                                            Text {
                                                anchors.centerIn: parent
                                                text: (index + 1) + (parent.t && parent.t.sounding ? (parent.t.direct ? "D" : "M") : "")
                                                font.family: Theme.fontMono
                                                font.pixelSize: ScaleMetrics.sp(6)
                                                font.bold: true
                                                color: parent.t && parent.t.sounding ? Theme.textPrimary : Theme.textDim
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        Item { Layout.fillWidth: true; visible: root.perform }

                        SchematicNode {
                            id: nodePart
                            visible: root.perform
                            title: root.perform && root.graph.part ? "PART " + root.graph.part.index : "PART"
                            sub: {
                                if (!root.perform || !root.graph.part) return "";
                                var a = root.graph.part.assign;
                                return a === 13 ? "OUT: PATCH" : "OUT: " + (a === 0 ? "MFX" : a === 1 ? "L+R" : a === 5 ? "L" : "R");
                            }
                            accentColor: root.cPart
                            live: root.edge("in->part").active
                        }

                        Item { Layout.fillWidth: true }

                        SchematicNode {
                            id: nodeMfx
                            title: root.node("mfx").label || "MFX"
                            sub: (root.node("mfx").sub || "") + (root.node("mfx").source ? " · " + root.node("mfx").source : "")
                            accentColor: root.cMfx
                            live: root.node("mfx").hasInput
                        }

                        Item { Layout.fillWidth: true }

                        SchematicNode {
                            id: nodeCho
                            title: "CHORUS"
                            sub: (root.node("cho").sub || "") + (root.node("cho").source ? " · " + root.node("cho").source : "")
                            accentColor: root.cCho
                            live: root.node("cho").hasInput && root.node("cho").on
                            off: !root.node("cho").on
                        }

                        Item { Layout.fillWidth: true }

                        SchematicNode {
                            id: nodeRev
                            title: "REVERB"
                            sub: (root.node("rev").sub || "") + (root.node("rev").source ? " · " + root.node("rev").source : "")
                            accentColor: root.cRev
                            live: root.node("rev").hasInput && root.node("rev").on
                            off: !root.node("rev").on
                        }

                        Item { Layout.fillWidth: true }

                        SchematicNode {
                            id: nodeOut
                            title: "OUTPUT"
                            sub: "MAIN " + Bridge.masterLevel
                            accentColor: root.cOut
                            live: root.node("out").hasInput
                        }
                    }
                }

                // Notes: most severe first; tap to step through
                Rectangle {
                    id: noteStrip
                    property int idx: 0
                    readonly property var n: root.notes && root.notes.length > 0 ? root.notes[Math.min(idx, root.notes.length - 1)] : null
                    Layout.fillWidth: true
                    Layout.preferredHeight: ScaleMetrics.dp(24)
                    radius: ScaleMetrics.dp(3)
                    color: !n ? "#092419" : n.severity === "warning" ? "#3b1212" : n.severity === "caution" ? "#2d2305" : "#0b202e"
                    border.color: !n ? "#10b981" : n.severity === "warning" ? Theme.recording : n.severity === "caution" ? Theme.warning : "#06b6d4"
                    border.width: 1
                    Connections {
                        target: root
                        function onNotesChanged() { noteStrip.idx = 0; }
                    }
                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: ScaleMetrics.dp(8)
                        anchors.rightMargin: ScaleMetrics.dp(8)
                        spacing: ScaleMetrics.dp(6)
                        Text {
                            text: !noteStrip.n ? "✓" : noteStrip.n.severity === "info" ? "ℹ️" : "⚠️"
                            font.pixelSize: ScaleMetrics.sp(10)
                            color: "#86efac"
                        }
                        Text {
                            Layout.fillWidth: true
                            text: noteStrip.n ? noteStrip.n.title + " — " + noteStrip.n.description : "Signal reaches the output as drawn."
                            elide: Text.ElideRight
                            font.family: Theme.fontMono
                            font.pixelSize: ScaleMetrics.sp(8)
                            font.bold: true
                            color: !noteStrip.n ? "#86efac" : noteStrip.n.severity === "warning" ? "#fca5a5" : noteStrip.n.severity === "caution" ? "#fef08a" : "#67e8f9"
                        }
                        Text {
                            visible: root.notes && root.notes.length > 1
                            text: (noteStrip.idx + 1) + "/" + (root.notes ? root.notes.length : 0) + " ▸"
                            font.family: Theme.fontMono
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: Theme.textSecondary
                        }
                    }
                    MouseArea {
                        anchors.fill: parent
                        enabled: root.notes && root.notes.length > 1
                        onClicked: noteStrip.idx = (noteStrip.idx + 1) % root.notes.length
                    }
                }
            }
        }

        // =====================================================================
        // 3. STAGE EDITORS
        // =====================================================================
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: ScaleMetrics.dp(8)

            // ---------------------------------------------------------------
            // TONES (+ patch output)
            // ---------------------------------------------------------------
            RoutingStageCard {
                Layout.fillWidth: true
                Layout.preferredWidth: 4
                Layout.fillHeight: true
                stageTitle: "TONES"
                accentColor: Theme.tone1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(8)
                    spacing: ScaleMetrics.dp(5)

                    ChoiceRow {
                        label: "PATCH OUT"
                        model: [{ id: 13, label: "TONE" }].concat(root.toneAssigns)
                        current: Bridge.patchOutputAssign
                        onPicked: (v) => Bridge.setPatchOutputAssign(v)
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Repeater {
                            model: ["ALL", "T1", "T2", "T3", "T4"]
                            delegate: Rectangle {
                                readonly property var t: index > 0 ? root.tone(index) : null
                                readonly property bool follows: !!(t && t.owner !== t.index)
                                Layout.fillWidth: true
                                height: ScaleMetrics.dp(20)
                                radius: 2
                                color: root.selectedToneTab === index ? Theme.tone1 : "#131922"
                                border.color: root.selectedToneTab === index ? "#ffffff" : Theme.borderCard
                                border.width: 1
                                Text {
                                    anchors.centerIn: parent
                                    text: parent.follows ? modelData + "→" + parent.t.owner : modelData
                                    font.bold: true
                                    font.pixelSize: ScaleMetrics.sp(7)
                                    color: root.selectedToneTab === index ? "#000000" : (parent.follows ? Theme.warning : Theme.textDim)
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: root.selectedToneTab = index
                                }
                            }
                        }
                    }

                    ChoiceRow {
                        id: assignRow
                        readonly property var t: root.shownTone()
                        readonly property string lock: root.lockText(t)
                        label: "ASSIGN"
                        model: root.toneAssigns
                        current: !t ? -1 : (root.selectedToneTab === 0 && !root.allSame("assign")) ? -1 : t.assign
                        enabled: lock === ""
                        lockLabel: lock
                        onPicked: (v) => Bridge.setToneRoutingParam(root.selectedToneTab, "assign", v)
                    }

                    SendSlider {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        readonly property var t: root.shownTone()
                        label: "OUT LEVEL"
                        accent: Theme.tone1
                        val: t ? t.level : 127
                        enabled: !t || t.lockedBy !== "structure"
                        onMoved: (v) => Bridge.setToneRoutingParam(root.selectedToneTab, "level", v)
                    }
                    SendSlider {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        readonly property var t: root.shownTone()
                        label: !t ? "CHORUS SEND" : t.lockedBy === "part" ? "CHORUS SEND · PART SENDS APPLY"
                               : "CHORUS SEND" + (t.pairDirect ? " · DIRECT" : " · VIA MFX")
                        accent: root.cCho
                        val: t ? t.chorusSend : 0
                        enabled: !t || (t.lockedBy !== "structure" && t.lockedBy !== "part")
                        onMoved: (v) => Bridge.setToneRoutingParam(root.selectedToneTab, "chorusSend", v)
                    }
                    SendSlider {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        readonly property var t: root.shownTone()
                        label: !t ? "REVERB SEND" : t.lockedBy === "part" ? "REVERB SEND · PART SENDS APPLY"
                               : "REVERB SEND" + (t.pairDirect ? " · DIRECT" : " · VIA MFX")
                        accent: root.cRev
                        val: t ? t.reverbSend : 0
                        enabled: !t || (t.lockedBy !== "structure" && t.lockedBy !== "part")
                        onMoved: (v) => Bridge.setToneRoutingParam(root.selectedToneTab, "reverbSend", v)
                    }
                    Item { Layout.fillHeight: true }
                }
            }

            // ---------------------------------------------------------------
            // PART (PERFORM only)
            // ---------------------------------------------------------------
            RoutingStageCard {
                visible: root.perform
                Layout.fillWidth: true
                Layout.preferredWidth: 3
                Layout.fillHeight: true
                stageTitle: root.perform && root.graph.part ? "PART " + root.graph.part.index : "PART"
                accentColor: root.cPart

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(8)
                    spacing: ScaleMetrics.dp(5)
                    readonly property var p: root.perform ? root.graph.part : null

                    ChoiceRow {
                        label: "OUT"
                        model: [{ id: 13, label: "PAT" }].concat(root.toneAssigns)
                        current: parent.p ? parent.p.assign : 13
                        onPicked: (v) => Bridge.setRoutingPartParam("assign", v)
                    }
                    ChoiceRow {
                        label: "MFX"
                        model: [{ id: 1, label: "MFX1" }, { id: 2, label: "MFX2" }, { id: 3, label: "MFX3" }]
                        current: parent.p ? parent.p.mfxSelect : 1
                        onPicked: (v) => Bridge.setRoutingPartParam("mfxSelect", v)
                    }
                    SendSlider {
                        Layout.fillWidth: true
                        label: "OUT LEVEL"
                        accent: root.cPart
                        val: parent.p ? parent.p.level : 127
                        onMoved: (v) => Bridge.setRoutingPartParam("level", v)
                    }
                    SendSlider {
                        Layout.fillWidth: true
                        label: "CHORUS SEND"
                        accent: root.cCho
                        val: parent.p ? parent.p.chorusSend : 0
                        onMoved: (v) => Bridge.setRoutingPartParam("chorusSend", v)
                    }
                    SendSlider {
                        Layout.fillWidth: true
                        label: "REVERB SEND"
                        accent: root.cRev
                        val: parent.p ? parent.p.reverbSend : 0
                        onMoved: (v) => Bridge.setRoutingPartParam("reverbSend", v)
                    }
                    Item { Layout.fillHeight: true }
                }
            }

            // ---------------------------------------------------------------
            // MFX (in PERFORM: the one the editing radio picks)
            // ---------------------------------------------------------------
            RoutingStageCard {
                Layout.fillWidth: true
                Layout.preferredWidth: 3
                Layout.fillHeight: true
                stageTitle: root.perform ? "MFX" + Bridge.editingPerfMfx : "MFX"
                accentColor: root.cMfx

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(8)
                    spacing: ScaleMetrics.dp(5)

                    Rectangle {
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(20)
                        radius: 3
                        color: "#1c0d16"
                        border.color: root.cMfx
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            width: parent.width - ScaleMetrics.dp(8)
                            horizontalAlignment: Text.AlignHCenter
                            text: Bridge.mfxBypassed ? "THRU (PASSES DRY)" : Bridge.mfxAlgoName
                            font.family: Theme.fontMono
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: root.cMfx
                            elide: Text.ElideRight
                        }
                    }

                    // The part reaches a different MFX than the one edited here
                    Rectangle {
                        visible: !!(root.graph && root.graph.mfxMismatch)
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(22)
                        radius: 3
                        color: mmMa.pressed ? "#3d2a05" : "#2d2305"
                        border.color: Theme.warning
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: "PART USES MFX" + (root.graph ? root.graph.mfxEnd : "") + " · EDIT IT"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(7)
                            color: "#fef08a"
                        }
                        MouseArea {
                            id: mmMa
                            anchors.fill: parent
                            onClicked: Bridge.editRoutedMfx()
                        }
                    }

                    SendSlider {
                        Layout.fillWidth: true
                        label: "OUT LEVEL"
                        accent: root.cOut
                        val: Bridge.mfxDrySend
                        onMoved: (v) => Bridge.setMfxSend("dry", v)
                    }
                    SendSlider {
                        Layout.fillWidth: true
                        label: "CHORUS SEND"
                        accent: root.cCho
                        val: Bridge.mfxChorusSend
                        onMoved: (v) => Bridge.setMfxSend("chorus", v)
                    }
                    SendSlider {
                        Layout.fillWidth: true
                        label: "REVERB SEND"
                        accent: root.cRev
                        val: Bridge.mfxReverbSend
                        onMoved: (v) => Bridge.setMfxSend("reverb", v)
                    }
                    Item { Layout.fillHeight: true }
                }
            }

            // ---------------------------------------------------------------
            // CHORUS
            // ---------------------------------------------------------------
            RoutingStageCard {
                Layout.fillWidth: true
                Layout.preferredWidth: 3
                Layout.fillHeight: true
                stageTitle: "CHORUS"
                accentColor: root.cCho

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(8)
                    spacing: ScaleMetrics.dp(5)

                    Rectangle {
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(20)
                        radius: 3
                        color: "#081d28"
                        border.color: Bridge.chorusTypeName === "OFF" ? Theme.warning : root.cCho
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: Bridge.chorusTypeName
                            font.family: Theme.fontMono
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: Bridge.chorusTypeName === "OFF" ? Theme.warning : root.cCho
                        }
                    }
                    SendSlider {
                        Layout.fillWidth: true
                        label: "LEVEL"
                        accent: root.cCho
                        val: Bridge.chorusLevel
                        onMoved: (v) => Bridge.setChorusParam("level", v)
                    }
                    ChoiceRow {
                        label: "OUT"
                        model: [{ id: 0, label: "MAIN" }, { id: 1, label: "REV" }, { id: 2, label: "M+R" }]
                        current: Bridge.chorusToReverb
                        onPicked: (v) => Bridge.setChorusParam("toReverb", v)
                    }
                    Text {
                        Layout.fillWidth: true
                        horizontalAlignment: Text.AlignHCenter
                        text: Bridge.chorusToReverb === 0 ? "STEREO ➔ MAIN" : (Bridge.chorusToReverb === 1 ? "MONO ➔ REVERB ONLY" : "STEREO MAIN + MONO REVERB")
                        font.family: Theme.fontMono
                        font.pixelSize: ScaleMetrics.sp(7)
                        color: root.cCho
                    }
                    Item { Layout.fillHeight: true }
                }
            }

            // ---------------------------------------------------------------
            // REVERB
            // ---------------------------------------------------------------
            RoutingStageCard {
                Layout.fillWidth: true
                Layout.preferredWidth: 3
                Layout.fillHeight: true
                stageTitle: "REVERB"
                accentColor: root.cRev

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(8)
                    spacing: ScaleMetrics.dp(5)

                    Rectangle {
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(20)
                        radius: 3
                        color: "#1c0d28"
                        border.color: Bridge.reverbTypeName === "OFF" ? Theme.warning : root.cRev
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: Bridge.reverbTypeName
                            font.family: Theme.fontMono
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: Bridge.reverbTypeName === "OFF" ? Theme.warning : root.cRev
                        }
                    }
                    SendSlider {
                        Layout.fillWidth: true
                        label: "LEVEL"
                        accent: root.cRev
                        val: Bridge.reverbLevel
                        onMoved: (v) => Bridge.setReverbParam("level", v)
                    }
                    Item { Layout.fillHeight: true }
                }
            }
        }
    }

    // =========================================================================
    // SUB-COMPONENTS
    // =========================================================================

    component RoutingStageCard: Rectangle {
        property string stageTitle: "STAGE"
        property color accentColor: Theme.tone1
        default property alias content: innerContainer.data

        radius: ScaleMetrics.dp(6)
        color: Theme.bgApp
        border.color: Theme.borderCard
        border.width: 1

        ColumnLayout {
            anchors.fill: parent
            spacing: 0
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
                    spacing: ScaleMetrics.dp(6)
                    Rectangle {
                        width: ScaleMetrics.dp(8)
                        height: ScaleMetrics.dp(8)
                        radius: 2
                        color: accentColor
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

    // Schematic node: title + small subtitle; dim without signal, amber when OFF
    component SchematicNode: Rectangle {
        property string title: "NODE"
        property string sub: ""
        property color accentColor: Theme.tone1
        property bool live: true
        property bool off: false

        Layout.preferredWidth: ScaleMetrics.dp(86)
        Layout.preferredHeight: ScaleMetrics.dp(34)
        radius: ScaleMetrics.dp(4)
        color: "#0f141f"
        border.color: off ? Theme.warning : accentColor
        onXChanged: root.repaint()
        onYChanged: root.repaint()
        onVisibleChanged: root.repaint()
        border.width: 1
        opacity: live ? 1.0 : 0.55

        ColumnLayout {
            anchors.centerIn: parent
            width: parent.width - ScaleMetrics.dp(6)
            spacing: 0
            Text {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                text: title
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(8)
                font.letterSpacing: 1.0
                color: accentColor
                elide: Text.ElideRight
            }
            Text {
                Layout.fillWidth: true
                visible: sub !== ""
                horizontalAlignment: Text.AlignHCenter
                text: sub
                font.family: Theme.fontMono
                font.pixelSize: ScaleMetrics.sp(6)
                color: off ? Theme.warning : Theme.textSecondary
                elide: Text.ElideRight
            }
        }
    }

    // Row of exclusive choices; lockLabel replaces it when not editable
    component ChoiceRow: RowLayout {
        id: cr
        property string label: ""
        property var model: []
        property int current: -1
        property string lockLabel: ""
        signal picked(int v)

        Layout.fillWidth: true
        spacing: ScaleMetrics.dp(3)

        Text {
            text: cr.label
            font.bold: true
            font.pixelSize: ScaleMetrics.sp(7)
            color: Theme.textDim
            Layout.preferredWidth: ScaleMetrics.dp(44)
        }
        Rectangle {
            visible: cr.lockLabel !== ""
            Layout.fillWidth: true
            height: ScaleMetrics.dp(20)
            radius: 3
            color: "#10141d"
            border.color: Theme.borderCard
            border.width: 1
            Text {
                anchors.centerIn: parent
                text: "🔒 " + cr.lockLabel
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(7)
                color: Theme.textSecondary
            }
        }
        Repeater {
            model: cr.lockLabel === "" ? cr.model : []
            delegate: Rectangle {
                readonly property bool sel: cr.current === modelData.id
                Layout.fillWidth: true
                height: ScaleMetrics.dp(20)
                radius: 3
                color: sel ? "#00e5ff" : (chMa.pressed ? Theme.bgCardActive : "#10141d")
                border.color: sel ? "#ffffff" : Theme.borderCard
                border.width: 1
                Text {
                    anchors.centerIn: parent
                    text: modelData.label
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(7)
                    color: parent.sel ? "#000000" : Theme.textDim
                }
                MouseArea {
                    id: chMa
                    anchors.fill: parent
                    enabled: cr.enabled
                    onClicked: cr.picked(modelData.id)
                }
            }
        }
    }

    component SendSlider: Item {
        id: ss
        property string label: "SEND"
        property int val: 0
        property int minVal: 0
        property int maxVal: 127
        property color accent: Theme.tone1
        signal moved(int v)

        Layout.preferredHeight: ScaleMetrics.dp(36)
        opacity: enabled ? 1.0 : 0.4

        ColumnLayout {
            anchors.fill: parent
            spacing: ScaleMetrics.dp(2)
            RowLayout {
                Layout.fillWidth: true
                Text {
                    Layout.fillWidth: true
                    text: ss.label
                    elide: Text.ElideRight
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(7)
                    color: Theme.textDim
                }
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
                    width: parent.width * Math.max(0.0, Math.min(1.0, (ss.val - ss.minVal) / Math.max(1, ss.maxVal - ss.minVal)))
                    height: parent.height
                    radius: 3
                    color: ss.accent
                    opacity: 0.40
                }
                function updateVal(mouseX) {
                    var norm = Math.max(0.0, Math.min(1.0, mouseX / width));
                    ss.moved(Math.round(ss.minVal + norm * (ss.maxVal - ss.minVal)));
                }
                MouseArea {
                    anchors.fill: parent
                    enabled: ss.enabled
                    preventStealing: true
                    onPositionChanged: (mouse) => { if (pressed) parent.updateVal(mouse.x); }
                    onPressed: (mouse) => { parent.updateVal(mouse.x); }
                }
            }
        }
    }
}
