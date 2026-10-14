pragma ValueTypeBehavior: Copy
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import JunoSpectre
import ".."

// Picks the audio file of the selected clip: the media folder (LIBRARY) or a
// USB stick (its files are copied into the library first).
Rectangle {
    id: root
    property string file: ""             // the clip's current file (highlighted)
    property color trackColor: Theme.pageAccent
    property bool closable: true
    signal picked()
    signal closed()

    // Position: source "" = the media folder, else a USB volume path
    property string source: ""
    property string sub: ""
    property var listing: ({ "dirs": [], "files": [], "root": "" })
    property var sources: [{ "label": "LIBRARY", "path": "", "usb": false }]

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
    function pick(name) {
        Bridge.seqSetClipAudioFile(source, sub === "" ? name : sub + "/" + name);
        picked();
    }

    color: Theme.bgCard
    radius: ScaleMetrics.dp(6)
    border.color: root.trackColor
    border.width: 1

    onVisibleChanged: if (visible) refresh()
    Component.onCompleted: refresh()
    Connections {
        target: Bridge
        function onAudioChanged() { if (root.visible) root.listing = Bridge.audioBrowse(root.source, root.sub) }
    }
    // Swallow taps so nothing under the pop-up reacts
    MouseArea { anchors.fill: parent }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: ScaleMetrics.dp(8)
        spacing: ScaleMetrics.dp(6)

        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(4)
            Text {
                text: "PICK A FILE"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(10)
                color: root.trackColor
                Layout.rightMargin: ScaleMetrics.dp(8)
            }
            // Sources: the library, then each USB stick
            Repeater {
                model: root.sources
                delegate: SpButton {
                    implicitHeight: ScaleMetrics.dp(28)
                    text: (modelData.usb ? "USB: " : "") + modelData.label
                    fontSize: 8
                    checked: root.source === modelData.path
                    onClicked: { root.source = modelData.path; root.sub = ""; root.refresh(); }
                }
            }
            SpButton {
                implicitHeight: ScaleMetrics.dp(28)
                icon: "sync"
                compact: true
                onClicked: root.refresh()
            }
            Item { Layout.fillWidth: true }
            Text {
                visible: (Bridge.audioStatus.importing || "") !== ""
                text: "COPYING " + (Bridge.audioStatus.importing || "") + "…"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(8)
                color: Theme.warning
            }
            SpButton {
                visible: root.closable
                implicitHeight: ScaleMetrics.dp(28)
                icon: "close"
                text: "CLOSE"
                fontSize: 8
                onClicked: root.closed()
            }
        }

        // Where we are (‹ goes up)
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
                text: (root.source === "" ? "LIBRARY  ·  " + root.listing.root : "USB")
                      + (root.sub !== "" ? "  /  " + root.sub.split("/").join(" / ") : "")
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(8)
                color: Theme.textSecondary
                elide: Text.ElideLeft
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
                height: ScaleMetrics.dp(32)
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
                font.pixelSize: ScaleMetrics.sp(9)
                color: Theme.textDim
            }
        }
    }
}
