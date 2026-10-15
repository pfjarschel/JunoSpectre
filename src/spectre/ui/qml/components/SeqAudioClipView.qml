pragma ValueTypeBehavior: Copy
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import JunoSpectre
import ".."

// AUDIO track clip editor (in place of the step grid): the waveform with the
// slice's start (beat 1) / end markers, its beat grid and where a synced
// loop's bar restart cuts it, then the clip's
// mode, start, gain, bars / tempo, stretch and transpose. FILE opens the
// browser (the media folder or a USB stick; files from USB are copied in).
Item {
    id: root
    property var clipData: null
    property color trackColor: Theme.pageAccent

    // Notes clips carry no audio fields (the view is hidden then): read with fallbacks
    readonly property string file: (clipData && clipData.audioFile) || ""
    readonly property bool hasFile: file !== ""
    readonly property string state_: (clipData && clipData.audioState) || ""
    readonly property int fileFrames: (clipData && clipData.audioFileFrames) || 0
    readonly property int startFrame: (clipData && clipData.audioStart) || 0
    readonly property int endFrame: (clipData && clipData.audioEnd) || fileFrames
    readonly property int bars: (clipData && clipData.audioBars) || 0
    readonly property real clipBpm: (clipData && clipData.audioBpm) || 0
    readonly property real tempo: (clipData && clipData.audioTempo) || 1.0
    readonly property bool stretch: !!(clipData && clipData.audioStretch)
    // A synced loop restarts on its bar: past this frame the slice never plays (0 = whole)
    readonly property int cutFrame: (clipData && clipData.audioCutFrame) || 0
    readonly property real rate: 44100

    // Stretch amount colour: fine up to 10%, amber to 20%, red beyond
    readonly property real stretchDev: Math.abs(tempo - 1.0)
    readonly property color stretchColor: stretchDev > 0.2 ? Theme.recording
                                          : (stretchDev > 0.1 ? Theme.warning : trackColor)

    property bool browserOpen: false

    function seconds(frames) {
        const s = frames / rate;
        const m = Math.floor(s / 60);
        return m + ":" + (s - 60 * m).toFixed(3).padStart(6, "0");
    }
    function stateText() {
        switch (state_) {
        case "ready": return (clipData.audioSeconds || 0).toFixed(2) + " s";
        case "converting": return "PREPARING…";
        case "rendering": return "STRETCHING…";
        case "missing": return "MISSING";
        case "error": return (clipData.audioError || "CAN'T READ FILE").toUpperCase();
        default: return "";
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: ScaleMetrics.dp(6)

        // ---- Header: clip, file, state, actions -------------------------
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(6)
            Icon { name: "track.audio"; size: 13; color: root.trackColor }
            Text {
                text: root.clipData ? root.clipData.name : ""
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(11)
                color: root.trackColor
            }
            Text {
                Layout.fillWidth: true
                text: root.hasFile ? root.file : "Empty clip"
                font.pixelSize: ScaleMetrics.sp(8)
                color: Theme.textDim
                elide: Text.ElideMiddle
            }
            Text {
                text: root.stateText()
                font.bold: true
                font.family: Theme.fontMono
                font.pixelSize: ScaleMetrics.sp(8)
                color: root.state_ === "ready" ? Theme.textSecondary
                       : (root.state_ === "converting" || root.state_ === "rendering" ? Theme.warning : Theme.recording)
                elide: Text.ElideRight
                Layout.maximumWidth: ScaleMetrics.dp(260)
            }
            SpButton {
                implicitHeight: ScaleMetrics.dp(28)
                text: root.hasFile ? "FILE…" : "PICK FILE…"
                fontSize: 8
                variant: root.hasFile ? "neutral" : "outline"
                onClicked: root.browserOpen = true
            }
            SpButton {
                implicitHeight: ScaleMetrics.dp(28)
                icon: Bridge.audioAuditioning ? "stop" : "play"
                text: "AUDITION"
                fontSize: 8
                checked: Bridge.audioAuditioning
                enabled: root.state_ === "ready"
                onClicked: Bridge.audioAudition(!Bridge.audioAuditioning)
            }
            SpButton {
                implicitHeight: ScaleMetrics.dp(28)
                icon: "play"
                text: "LAUNCH"
                fontSize: 8
                variant: "outline"
                accent: Theme.playing
                enabled: root.state_ === "ready"
                onClicked: Bridge.seqLaunchClip(Bridge.seqActiveTrack, Bridge.seqActiveClip)
            }
            SpButton {
                implicitHeight: ScaleMetrics.dp(28)
                icon: "stop"
                fontSize: 8
                onClicked: { Bridge.audioAudition(false); Bridge.seqStopTrack(Bridge.seqActiveTrack); }
            }
            SpButton {
                implicitHeight: ScaleMetrics.dp(28)
                icon: "close"
                fontSize: 8
                variant: "danger"
                enabled: root.hasFile
                onClicked: Bridge.seqClearClipAudio()
            }
        }

        // ---- Waveform ----------------------------------------------------
        Waveform {
            id: wave
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: ScaleMetrics.dp(110)
        }

        // ---- Markers + zoom ----------------------------------------------
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(4)
            FieldLabel { text: "MARKER" }
            Repeater {
                model: [["start", "START · BEAT 1"], ["end", "END"]]
                delegate: SpButton {
                    implicitHeight: ScaleMetrics.dp(28)
                    text: modelData[1]
                    fontSize: 8
                    accent: root.trackColor
                    checked: wave.marker === modelData[0]
                    onClicked: wave.marker = modelData[0]
                }
            }
            Repeater {
                // nudge the selected marker: 10 ms / 1 ms
                model: [[-441, "«"], [-44, "‹"], [44, "›"], [441, "»"]]
                delegate: SpButton {
                    implicitHeight: ScaleMetrics.dp(28)
                    implicitWidth: ScaleMetrics.dp(30)
                    text: modelData[1]
                    fontSize: 10
                    enabled: root.hasFile
                    onClicked: wave.nudge(modelData[0])
                }
            }
            Text {
                text: root.seconds(wave.marker === "start" ? root.startFrame : root.endFrame)
                font.family: Theme.fontMono
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(8)
                color: root.trackColor
                Layout.leftMargin: ScaleMetrics.dp(4)
            }
            Item { Layout.fillWidth: true }
            FieldLabel { text: "ZOOM" }
            Repeater {
                model: [[1, "ALL"], [4, "×4"], [16, "×16"], [64, "×64"], [256, "×256"]]
                delegate: SpButton {
                    implicitHeight: ScaleMetrics.dp(28)
                    text: modelData[1]
                    fontSize: 8
                    checked: wave.zoom === modelData[0]
                    onClicked: wave.zoom = modelData[0]
                }
            }
        }

        // ---- Mode, start, gain ---------------------------------------------
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(4)
            FieldLabel { text: "MODE" }
            Repeater {
                model: [["loop", "LOOP"], ["oneshot", "ONE-SHOT"], ["full", "FULL TRACK"]]
                delegate: SpButton {
                    implicitHeight: ScaleMetrics.dp(28)
                    text: modelData[1]
                    fontSize: 8
                    accent: root.trackColor
                    checked: root.clipData ? root.clipData.audioMode === modelData[0] : false
                    onClicked: Bridge.seqSetClipAudio("mode", modelData[0])
                }
            }
            Item { width: ScaleMetrics.dp(8) }
            FieldLabel { text: "START" }
            Repeater {
                model: [[true, "ON THE BAR"], [false, "AT ONCE"]]
                delegate: SpButton {
                    implicitHeight: ScaleMetrics.dp(28)
                    text: modelData[1]
                    fontSize: 8
                    accent: root.trackColor
                    checked: root.clipData ? root.clipData.audioSync === modelData[0] : false
                    onClicked: Bridge.seqSetClipAudio("sync", modelData[0])
                }
            }
            Item { Layout.fillWidth: true }
            SeqStepper {
                label: "GAIN:"
                count: 67
                index: Math.round(((root.clipData && root.clipData.audioGainDb) || 0) + 60)
                valueText: (index - 60 > 0 ? "+" : "") + (index - 60) + " dB"
                valueColor: root.trackColor
                pxPerStep: ScaleMetrics.dp(6)
                onRequested: (i) => Bridge.seqSetClipAudio("gainDb", i - 60)
            }
        }

        // ---- Bars, tempo, stretch, transpose -------------------------------
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(4)
            SeqStepper {
                label: "BARS:"
                count: 65
                index: (root.clipData && !root.clipData.audioBarsAuto) ? root.bars : 0
                valueText: index === 0 ? "AUTO " + root.bars : index
                valueColor: root.trackColor
                pxPerStep: ScaleMetrics.dp(10)
                onRequested: (i) => Bridge.seqSetClipAudio("bars", i)
            }
            SpButton {
                implicitHeight: ScaleMetrics.dp(28)
                text: "FIT END @ " + Math.round(Bridge.bpm * 100) / 100
                fontSize: 8
                enabled: root.state_ !== "" && root.fileFrames > 0
                onClicked: Bridge.seqFitClipEnd()
            }
            Item { width: ScaleMetrics.dp(6) }
            Text {
                readonly property bool off: root.clipBpm > 0 && Math.abs(root.clipBpm - Bridge.bpm) > 0.05
                text: root.clipBpm > 0 ? "CLIP " + root.clipBpm.toFixed(2) + " BPM" : "CLIP — BPM"
                font.bold: true
                font.family: Theme.fontMono
                font.pixelSize: ScaleMetrics.sp(8)
                color: off && !root.stretch ? Theme.warning : Theme.textSecondary
            }
            SpButton {
                implicitHeight: ScaleMetrics.dp(28)
                text: "SET SONG BPM"
                fontSize: 8
                enabled: root.clipBpm > 0 && Math.abs(root.clipBpm - Bridge.bpm) > 0.005
                onClicked: Bridge.seqSetSongBpmFromClip()
            }
            SpButton {
                implicitHeight: ScaleMetrics.dp(28)
                text: "MATCH SONG" + (root.stretch && root.stretchDev > 0.0005
                                      ? "  " + (root.tempo >= 1 ? "+" : "") + ((root.tempo - 1) * 100).toFixed(1) + "%" : "")
                fontSize: 8
                accent: root.stretchColor
                checked: root.stretch
                enabled: root.hasFile
                onClicked: Bridge.seqSetClipAudio("stretch", !root.stretch)
            }
            Item { Layout.fillWidth: true }
            SeqStepper {
                label: "PITCH:"
                count: 25
                index: ((root.clipData && root.clipData.audioSemitones) || 0) + 12
                valueText: (index - 12 > 0 ? "+" : "") + (index - 12) + " st"
                valueColor: root.trackColor
                pxPerStep: ScaleMetrics.dp(10)
                onRequested: (i) => Bridge.seqSetClipAudio("semitones", i - 12)
            }
            SeqStepper {
                label: "FINE:"
                count: 101
                index: ((root.clipData && root.clipData.audioCents) || 0) + 50
                valueText: (index - 50 > 0 ? "+" : "") + (index - 50) + " ct"
                valueColor: root.trackColor
                pxPerStep: ScaleMetrics.dp(5)
                onRequested: (i) => Bridge.seqSetClipAudio("cents", i - 50)
            }
        }
    }

    // ---- File browser (pop-up over the editor) ------------------------------
    AudioFileBrowser {
        anchors.fill: parent
        visible: root.browserOpen || (root.clipData !== null && !root.hasFile)
        file: root.file
        trackColor: root.trackColor
        closable: root.hasFile
        onPicked: root.browserOpen = false
        onClosed: root.browserOpen = false
    }

    // =========================================================================
    // Waveform: the file with the slice markers, its beat grid and the playhead.
    // Press near a marker to drag it (anywhere else moves the selected one);
    // zoom centres on the selected marker.
    // =========================================================================
    component Waveform: Rectangle {
        id: wv
        property string marker: "start"
        property int zoom: 1
        property var peaks: []
        // dragging: the frame shown until release commits it
        property int dragFrame: -1
        property int playhead: -1

        readonly property int markerFrame: dragFrame >= 0 ? dragFrame
                                           : (marker === "start" ? root.startFrame : root.endFrame)
        readonly property real span: Math.max(1, root.fileFrames / zoom)
        readonly property real viewStart: zoom === 1 ? 0
                                          : Math.max(0, Math.min(root.fileFrames - span, markerFrame - span / 2))
        readonly property real viewEnd: viewStart + span

        function xOf(f) { return (f - viewStart) / (viewEnd - viewStart) * width; }
        function frameAt(x) { return Math.round(viewStart + Math.max(0, Math.min(width, x)) / width * (viewEnd - viewStart)); }
        function nudge(d) {
            Bridge.seqSetClipAudio(marker, (marker === "start" ? root.startFrame : root.endFrame) + d);
        }
        function reload() {
            peaks = (root.state_ !== "" && root.fileFrames > 0 && width > 0)
                    ? Bridge.audioPeaks(Math.floor(viewStart), Math.ceil(viewEnd), Math.floor(width)) : [];
            waveCanvas.requestPaint();
        }

        radius: ScaleMetrics.dp(6)
        color: Theme.bgApp
        border.color: Theme.borderCard
        border.width: 1
        clip: true

        onViewStartChanged: reloadTimer.restart()
        onSpanChanged: reloadTimer.restart()
        onWidthChanged: reloadTimer.restart()
        Connections {
            target: root
            function onFileChanged() { wv.zoom = 1; reloadTimer.restart(); }
            function onFileFramesChanged() { reloadTimer.restart(); }
            // The slice colours repaint once a marker settles (drags show on the overlays)
            function onStartFrameChanged() { waveCanvas.requestPaint(); gridCanvas.requestPaint(); }
            function onEndFrameChanged() { waveCanvas.requestPaint(); gridCanvas.requestPaint(); }
            function onBarsChanged() { gridCanvas.requestPaint(); }
        }
        Timer { id: reloadTimer; interval: 30; onTriggered: { wv.reload(); gridCanvas.requestPaint(); } }

        // Playhead: polled while something of this clip plays
        Timer {
            interval: 33
            repeat: true
            running: root.visible && root.hasFile && (Bridge.audioAuditioning || Bridge.seqIsPlaying)
            onTriggered: wv.playhead = Bridge.audioPlayhead()
            onRunningChanged: if (!running) wv.playhead = -1
        }

        Canvas {
            id: waveCanvas
            anchors.fill: parent
            onPaint: {
                const ctx = getContext("2d");
                ctx.reset();
                const p = wv.peaks, n = p.length / 2, mid = height / 2, amp = height / 2 - 4;
                if (!n)
                    return;
                const s = wv.xOf(root.startFrame), e = wv.xOf(root.endFrame);
                for (let i = 0; i < n; i++) {
                    const inside = i >= s && i <= e;
                    ctx.fillStyle = inside ? root.trackColor : Theme.textDim;
                    const y0 = mid - p[2 * i + 1] * amp, y1 = mid - p[2 * i] * amp;
                    ctx.fillRect(i, y0, 1, Math.max(1, y1 - y0));
                }
            }
        }
        // Outside the slice: dimmed
        Rectangle {
            x: 0; y: 0; height: parent.height
            width: Math.max(0, Math.min(parent.width, wv.xOf(wv.marker === "start" && wv.dragFrame >= 0 ? wv.dragFrame : root.startFrame)))
            color: Qt.rgba(0, 0, 0, 0.45)
        }
        Rectangle {
            readonly property real ex: wv.xOf(wv.marker === "end" && wv.dragFrame >= 0 ? wv.dragFrame : root.endFrame)
            x: Math.max(0, Math.min(parent.width, ex)); y: 0; height: parent.height
            width: Math.max(0, parent.width - x)
            color: Qt.rgba(0, 0, 0, 0.45)
        }
        // Cut by the bar restart: the slice's tail that never plays
        Item {
            readonly property real cx: wv.xOf(root.cutFrame)
            visible: root.cutFrame > 0 && cx < parent.width
            x: Math.max(0, cx)
            width: Math.max(0, Math.min(parent.width, wv.xOf(root.endFrame)) - x)
            height: parent.height
            Rectangle { anchors.fill: parent; color: Theme.recording; opacity: 0.18 }
            Rectangle { visible: parent.cx >= 0; width: ScaleMetrics.dp(1); height: parent.height; color: Theme.recording }
            Rectangle {
                visible: parent.cx >= 0
                y: ScaleMetrics.dp(16)
                width: cutText.implicitWidth + ScaleMetrics.dp(6); height: ScaleMetrics.dp(14)
                color: Theme.recording
                Text {
                    id: cutText
                    anchors.centerIn: parent
                    text: "CUT"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(7)
                    color: Theme.bgApp
                }
            }
        }
        // Beat grid of the slice: its bars split into beats (bars brighter)
        Canvas {
            id: gridCanvas
            anchors.fill: parent
            onPaint: {
                const ctx = getContext("2d");
                ctx.reset();
                const beats = root.bars * 4;
                if (beats <= 0 || root.endFrame <= root.startFrame)
                    return;
                const step = (root.endFrame - root.startFrame) / beats;
                const showBeats = (wv.xOf(root.startFrame + step) - wv.xOf(root.startFrame)) >= 6;
                for (let k = 0; k <= beats; k++) {
                    if (k % 4 !== 0 && !showBeats)
                        continue;
                    const x = Math.round(wv.xOf(root.startFrame + k * step)) + 0.5;
                    if (x < 0 || x > width)
                        continue;
                    ctx.strokeStyle = k % 4 === 0 ? Qt.rgba(1, 1, 1, 0.35) : Qt.rgba(1, 1, 1, 0.12);
                    ctx.beginPath();
                    ctx.moveTo(x, 0);
                    ctx.lineTo(x, height);
                    ctx.stroke();
                    if (k % 4 === 0 && k < beats) {
                        ctx.fillStyle = Qt.rgba(1, 1, 1, 0.5);
                        ctx.font = "bold " + Math.round(ScaleMetrics.sp(7)) + "px sans-serif";
                        ctx.fillText(String(k / 4 + 1), x + 3, height - 4);
                    }
                }
            }
        }
        // Markers
        Repeater {
            model: ["start", "end"]
            delegate: Item {
                readonly property int f: (wv.dragFrame >= 0 && wv.marker === modelData) ? wv.dragFrame
                                         : (modelData === "start" ? root.startFrame : root.endFrame)
                readonly property bool sel: wv.marker === modelData
                visible: root.fileFrames > 0
                x: wv.xOf(f) - width / 2
                width: ScaleMetrics.dp(2)
                height: wv.height
                Rectangle { anchors.fill: parent; color: sel ? root.trackColor : Theme.textSecondary }
                Rectangle {
                    y: 0
                    x: modelData === "start" ? 0 : -width + parent.width
                    width: ScaleMetrics.dp(16); height: ScaleMetrics.dp(14)
                    color: sel ? root.trackColor : Theme.textSecondary
                    Text {
                        anchors.centerIn: parent
                        text: modelData === "start" ? "1" : "E"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(7)
                        color: Theme.bgApp
                    }
                }
            }
        }
        // Playhead
        Rectangle {
            visible: wv.playhead >= 0 && wv.xOf(wv.playhead) >= 0 && wv.xOf(wv.playhead) <= wv.width
            x: wv.xOf(wv.playhead)
            width: 1
            height: parent.height
            color: Theme.textPrimary
        }

        MouseArea {
            anchors.fill: parent
            enabled: root.fileFrames > 0
            onPressed: (mouse) => {
                const grab = ScaleMetrics.dp(24);
                const ds = Math.abs(mouse.x - wv.xOf(root.startFrame));
                const de = Math.abs(mouse.x - wv.xOf(root.endFrame));
                if (Math.min(ds, de) <= grab)
                    wv.marker = ds <= de ? "start" : "end";
                wv.dragFrame = wv.frameAt(mouse.x);
            }
            onPositionChanged: (mouse) => { if (pressed) wv.dragFrame = wv.frameAt(mouse.x); }
            onReleased: {
                const f = wv.dragFrame;
                wv.dragFrame = -1;
                if (f >= 0)
                    Bridge.seqSetClipAudio(wv.marker, f);
            }
            onCanceled: wv.dragFrame = -1
        }

        Text {
            anchors.centerIn: parent
            visible: root.fileFrames <= 0
            text: root.hasFile ? root.stateText() : ""
            font.bold: true
            font.pixelSize: ScaleMetrics.sp(9)
            color: Theme.textDim
        }
    }

    component FieldLabel: Text {
        font.bold: true
        font.pixelSize: ScaleMetrics.sp(7)
        font.letterSpacing: 1
        color: Theme.textDim
    }
}
