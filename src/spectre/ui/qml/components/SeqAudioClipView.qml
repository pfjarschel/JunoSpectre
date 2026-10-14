pragma ValueTypeBehavior: Copy
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import JunoSpectre
import ".."

// AUDIO track editor (in place of the step grid): a file browser on the
// left (the media folder or a USB stick; a tap puts the file in the selected
// clip, copying it in from USB first) and the selected clip's settings.
Item {
    id: root
    property var clipData: null
    property color trackColor: Theme.pageAccent

    // Browser position: source "" = the media folder, else a USB volume path
    property string source: ""
    property string sub: ""
    property var listing: ({ "dirs": [], "files": [], "root": "" })
    property var sources: [{ "label": "LIBRARY", "path": "", "usb": false }]

    // Notes clips carry no audio fields (the view is hidden then): read with fallbacks
    readonly property string file: (clipData && clipData.audioFile) || ""
    readonly property bool hasFile: file !== ""
    readonly property string state_: (clipData && clipData.audioState) || ""

    function refresh() {
        sources = Bridge.audioSources();
        if (source !== "" && !sources.some(s => s.path === source)) {
            source = "";
            sub = "";
        }
        listing = Bridge.audioBrowse(source, sub);
    }
    function enter(dir) {
        sub = sub === "" ? dir : sub + "/" + dir;
        refresh();
    }
    function up() {
        const i = sub.lastIndexOf("/");
        sub = i < 0 ? "" : sub.substring(0, i);
        refresh();
    }
    function pick(file) {
        Bridge.seqSetClipAudioFile(source, sub === "" ? file : sub + "/" + file);
    }
    function stateText() {
        switch (state_) {
        case "ready": return (clipData.audioSeconds || 0).toFixed(1) + " s";
        case "converting": return "PREPARING…";
        case "missing": return "MISSING";
        case "error": return "CAN'T READ FILE";
        default: return "";
        }
    }

    Component.onCompleted: refresh()
    onVisibleChanged: if (visible) refresh()
    Connections {
        target: Bridge
        function onAudioChanged() { if (root.visible) root.listing = Bridge.audioBrowse(root.source, root.sub) }
    }

    RowLayout {
        anchors.fill: parent
        spacing: ScaleMetrics.dp(8)

        // ---- File browser ------------------------------------------------
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredWidth: 55
            radius: ScaleMetrics.dp(6)
            color: Theme.bgApp
            border.color: Theme.borderCard
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(6)
                spacing: ScaleMetrics.dp(6)

                // Sources: the library, then each USB stick
                RowLayout {
                    Layout.fillWidth: true
                    spacing: ScaleMetrics.dp(4)
                    Repeater {
                        model: root.sources
                        delegate: SpButton {
                            implicitHeight: ScaleMetrics.dp(26)
                            text: (modelData.usb ? "USB: " : "") + modelData.label
                            fontSize: 8
                            checked: root.source === modelData.path
                            onClicked: { root.source = modelData.path; root.sub = ""; root.refresh(); }
                        }
                    }
                    Item { Layout.fillWidth: true }
                    SpButton {
                        implicitHeight: ScaleMetrics.dp(26)
                        icon: "sync"
                        compact: true
                        onClicked: root.refresh()
                    }
                }

                // Where we are (tap ‹ to go up)
                RowLayout {
                    Layout.fillWidth: true
                    spacing: ScaleMetrics.dp(6)
                    SpButton {
                        implicitHeight: ScaleMetrics.dp(26)
                        icon: "back"
                        compact: true
                        enabled: root.sub !== ""
                        onClicked: root.up()
                    }
                    Text {
                        Layout.fillWidth: true
                        text: (root.source === "" ? "LIBRARY" : "USB") + (root.sub !== "" ? " / " + root.sub.split("/").join(" / ") : "")
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Theme.textSecondary
                        elide: Text.ElideLeft
                    }
                    Text {
                        visible: (Bridge.audioStatus.importing || "") !== ""
                        text: "COPYING " + (Bridge.audioStatus.importing || "") + "…"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(7)
                        color: Theme.warning
                    }
                }

                ListView {
                    id: list
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: ScaleMetrics.dp(3)
                    model: root.listing.dirs.map(d => ({ "name": d, "dir": true }))
                           .concat(root.listing.files.map(f => ({ "name": f, "dir": false })))
                    ScrollBar.vertical: ScrollBar { policy: list.contentHeight > list.height ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff }

                    delegate: Rectangle {
                        readonly property string rel: root.sub === "" ? modelData.name : root.sub + "/" + modelData.name
                        readonly property bool current: !modelData.dir && root.source === "" && root.file === rel
                        width: list.width - ScaleMetrics.dp(10)
                        height: ScaleMetrics.dp(30)
                        radius: 3
                        color: rowMouse.pressed ? Theme.bgCardActive : (current ? Theme.tint(root.trackColor, 0.18) : Theme.bgSurface)
                        border.color: current ? root.trackColor : Theme.borderCard
                        border.width: 1

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: ScaleMetrics.dp(8)
                            anchors.rightMargin: ScaleMetrics.dp(8)
                            spacing: ScaleMetrics.dp(6)
                            Icon {
                                name: modelData.dir ? "right" : "track.audio"
                                size: 11
                                color: modelData.dir ? Theme.textDim : (current ? root.trackColor : Theme.textSecondary)
                            }
                            Text {
                                Layout.fillWidth: true
                                text: modelData.name + (modelData.dir ? " /" : "")
                                font.bold: modelData.dir || current
                                font.pixelSize: ScaleMetrics.sp(8)
                                color: modelData.dir ? Theme.textPrimary : (current ? root.trackColor : Theme.textSecondary)
                                elide: Text.ElideMiddle
                            }
                            Text {
                                visible: !modelData.dir && root.source !== ""
                                text: "IMPORT"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(7)
                                color: Theme.pageAccent
                            }
                        }
                        MouseArea {
                            id: rowMouse
                            anchors.fill: parent
                            onClicked: modelData.dir ? root.enter(modelData.name) : root.pick(modelData.name)
                        }
                    }

                    Text {
                        anchors.centerIn: parent
                        width: parent.width - ScaleMetrics.dp(24)
                        visible: list.count === 0
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                        text: root.source === ""
                              ? "No audio files here.\nCopy WAV, FLAC, OGG or MP3 files into\n" + root.listing.root
                              : "No audio files on this stick."
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Theme.textDim
                    }
                }
            }
        }

        // ---- Selected clip ------------------------------------------------
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredWidth: 45
            radius: ScaleMetrics.dp(6)
            color: Theme.bgApp
            border.color: Theme.borderCard
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(10)
                spacing: ScaleMetrics.dp(8)

                RowLayout {
                    Layout.fillWidth: true
                    spacing: ScaleMetrics.dp(6)
                    Text {
                        Layout.fillWidth: true
                        text: root.clipData ? root.clipData.name : ""
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(11)
                        color: root.trackColor
                        elide: Text.ElideRight
                    }
                    Text {
                        text: root.stateText()
                        font.bold: true
                        font.family: Theme.fontMono
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: root.state_ === "ready" ? Theme.textSecondary
                               : (root.state_ === "converting" ? Theme.warning : Theme.recording)
                    }
                }
                Text {
                    Layout.fillWidth: true
                    text: root.hasFile ? root.file : "Empty: pick a file on the left"
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: Theme.textDim
                    elide: Text.ElideMiddle
                }

                FieldLabel { text: "MODE" }
                RowLayout {
                    spacing: ScaleMetrics.dp(4)
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
                }
                Text {
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    text: {
                        const m = root.clipData ? root.clipData.audioMode : "loop";
                        return m === "loop" ? "Repeats until stopped or replaced."
                             : m === "oneshot" ? "Plays once, like a pad."
                             : "Plays once and keeps playing through scene launches.";
                    }
                    font.pixelSize: ScaleMetrics.sp(7)
                    color: Theme.textDim
                }

                FieldLabel { text: "START" }
                RowLayout {
                    spacing: ScaleMetrics.dp(4)
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
                }

                RowLayout {
                    spacing: ScaleMetrics.dp(8)
                    SeqStepper {
                        label: "GAIN:"
                        count: 67
                        index: Math.round((root.clipData ? root.clipData.audioGainDb : 0) + 60)
                        valueText: (index - 60 > 0 ? "+" : "") + (index - 60) + " dB"
                        valueColor: root.trackColor
                        pxPerStep: ScaleMetrics.dp(6)
                        onRequested: (i) => Bridge.seqSetClipAudio("gainDb", i - 60)
                    }
                }

                Item { Layout.fillHeight: true }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: ScaleMetrics.dp(6)
                    SpButton {
                        implicitHeight: ScaleMetrics.dp(30)
                        icon: "play"
                        text: "LAUNCH"
                        fontSize: 8
                        variant: "outline"
                        accent: Theme.playing
                        enabled: root.state_ === "ready"
                        onClicked: Bridge.seqLaunchClip(Bridge.seqActiveTrack, Bridge.seqActiveClip)
                    }
                    SpButton {
                        implicitHeight: ScaleMetrics.dp(30)
                        icon: "stop"
                        text: "STOP"
                        fontSize: 8
                        onClicked: Bridge.seqStopTrack(Bridge.seqActiveTrack)
                    }
                    Item { Layout.fillWidth: true }
                    SpButton {
                        implicitHeight: ScaleMetrics.dp(30)
                        text: "REMOVE FILE"
                        fontSize: 8
                        variant: "danger"
                        enabled: root.hasFile
                        onClicked: Bridge.seqClearClipAudio()
                    }
                }
            }
        }
    }

    component FieldLabel: Text {
        font.bold: true
        font.pixelSize: ScaleMetrics.sp(7)
        font.letterSpacing: 1
        color: Theme.textDim
    }
}
