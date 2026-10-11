pragma ValueTypeBehavior: Copy
import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

// JUNO-DS arpeggiator: the synth's own arp (global Setup settings; the app
// saves them with patches and performances). Three panels: style browser,
// pattern (motif, grid), feel (duration and the numeric settings).
Rectangle {
    id: root
    color: Theme.bgCard
    radius: ScaleMetrics.dp(8)
    border.color: Theme.borderCard
    border.width: 1

    readonly property var arp: Bridge.arp
    readonly property var lists: Bridge.arpLists
    readonly property bool perform: Bridge.soundMode === "PERFORM"
    readonly property color accent: "#22d3ee"

    // Style categories (Parameter Guide p.86): [title, first, last]
    readonly property var categories: [["BASIC", 0, 5], ["SEQ PTN", 6, 65], ["BASSLINE", 66, 106],
                                       ["SLICED", 107, 116], ["GTR/KEYS", 117, 127]]
    // Browsed category: follows the style when it changes (knob, file load)
    property int category: 0
    property int followedStyle: -1
    function categoryOf(style) {
        for (let i = 0; i < categories.length; i++)
            if (style >= categories[i][1] && style <= categories[i][2]) return i;
        return 0;
    }
    readonly property var categoryStyles: {
        const c = categories[category];
        const out = [];
        for (let i = c[1]; i <= c[2]; i++) out.push(i);
        return out;
    }
    function followStyle() {
        if (arp.style !== followedStyle) {
            followedStyle = arp.style;
            category = categoryOf(arp.style);
        }
    }
    onArpChanged: followStyle()
    Component.onCompleted: followStyle()

    component Chip: Rectangle {
        id: chip
        property string text: ""
        property bool selected: false
        property color tint: root.accent
        signal clicked()
        Layout.fillWidth: true
        Layout.preferredHeight: ScaleMetrics.dp(36)
        radius: 4
        color: selected ? Qt.rgba(tint.r, tint.g, tint.b, 0.22) : (chipMouse.pressed ? Theme.bgCardActive : Theme.bgApp)
        border.color: selected ? tint : Theme.borderCard
        border.width: 1
        Text {
            anchors.fill: parent
            anchors.leftMargin: ScaleMetrics.dp(3)
            anchors.rightMargin: ScaleMetrics.dp(3)
            text: chip.text
            font.bold: true
            font.pixelSize: ScaleMetrics.sp(10)
            color: chip.selected ? chip.tint : Theme.textSecondary
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        MouseArea { id: chipMouse; anchors.fill: parent; onClicked: chip.clicked() }
    }

    component SectionLabel: Text {
        font.bold: true
        font.pixelSize: ScaleMetrics.sp(9)
        font.letterSpacing: 1.0
        color: Theme.textDim
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: ScaleMetrics.dp(10)
        spacing: ScaleMetrics.dp(8)

        // Header: power, hold, part, clock
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(8)

            Rectangle {
                width: ScaleMetrics.dp(8); height: ScaleMetrics.dp(8); radius: 4
                color: root.arp.switch ? Theme.playing : Theme.textDim
            }
            Text {
                text: "ARPEGGIATOR"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(12)
                font.letterSpacing: 1.2
                color: Theme.textPrimary
            }

            Chip {
                Layout.fillWidth: false
                Layout.preferredWidth: ScaleMetrics.dp(64)
                Layout.preferredHeight: ScaleMetrics.dp(30)
                text: root.arp.switch ? "ON" : "OFF"
                selected: root.arp.switch
                tint: Theme.playing
                onClicked: Bridge.toggleArp()
            }
            Chip {
                Layout.fillWidth: false
                Layout.preferredWidth: ScaleMetrics.dp(64)
                Layout.preferredHeight: ScaleMetrics.dp(30)
                text: "HOLD"
                selected: root.arp.hold
                tint: Theme.warning
                onClicked: Bridge.toggleArpHold()
            }

            // PERFORM: the part the arp plays can only be set on the Juno (no SysEx for it)
            Text {
                visible: root.perform
                text: "PART: SET ON THE JUNO'S ARPEGGIO SCREEN"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(9)
                color: Theme.textDim
            }

            Item { Layout.fillWidth: true }

            Text {
                visible: !root.arp.known
                text: "NOT READ FROM SYNTH"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(8)
                color: Theme.warning
                MouseArea { anchors.fill: parent; anchors.margins: -ScaleMetrics.dp(6); onClicked: Bridge.refreshArp() }
            }

            Chip {
                Layout.fillWidth: false
                Layout.preferredWidth: ScaleMetrics.dp(150)
                Layout.preferredHeight: ScaleMetrics.dp(30)
                text: "CLOCK OUT " + (Bridge.midiClockOut ? Math.round(Bridge.bpm) + " BPM" : "OFF")
                selected: Bridge.midiClockOut
                tint: "#38bdf8"
                onClicked: Bridge.setMidiClockOut(!Bridge.midiClockOut)
            }
        }

        RowLayout {
            id: body
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: ScaleMetrics.dp(8)
            readonly property real share: width - 2 * spacing

            component Panel: Rectangle {
                Layout.fillHeight: true
                radius: ScaleMetrics.dp(6)
                color: Theme.bgApp
                border.color: Theme.borderCard
                border.width: 1
            }

            // 1. Style browser
            Panel {
                Layout.preferredWidth: body.share * 0.38

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(8)
                    spacing: ScaleMetrics.dp(6)

                    SectionLabel { text: "STYLE" }
                    Text {
                        Layout.fillWidth: true
                        text: root.arp.styleText
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(13)
                        color: root.accent
                        elide: Text.ElideRight
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 3
                        rowSpacing: ScaleMetrics.dp(4)
                        columnSpacing: ScaleMetrics.dp(4)
                        Repeater {
                            model: root.categories.length
                            delegate: Chip {
                                required property int index
                                Layout.preferredHeight: ScaleMetrics.dp(32)
                                text: root.categories[index][0]
                                selected: root.category === index
                                onClicked: root.category = index
                            }
                        }
                    }

                    GridView {
                        id: styleGrid
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        cellWidth: width / 3
                        cellHeight: ScaleMetrics.dp(40)
                        model: root.categoryStyles
                        delegate: Item {
                            id: cell
                            required property int modelData
                            readonly property string label: root.lists.styles[modelData]
                            readonly property bool current: root.arp.style === modelData
                            width: styleGrid.cellWidth
                            height: styleGrid.cellHeight
                            Rectangle {
                                anchors.fill: parent
                                anchors.margins: ScaleMetrics.dp(2)
                                radius: 4
                                color: cell.current ? Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.22)
                                                    : (tileMouse.pressed ? Theme.bgCardActive : Theme.bgCard)
                                border.color: cell.current ? root.accent : Theme.borderCard
                                border.width: 1
                                Column {
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.verticalCenter: parent.verticalCenter
                                    anchors.leftMargin: ScaleMetrics.dp(6)
                                    anchors.rightMargin: ScaleMetrics.dp(4)
                                    spacing: 0
                                    Text {
                                        text: cell.label.substring(0, 3)
                                        font.family: Theme.fontMono
                                        font.pixelSize: ScaleMetrics.sp(8)
                                        color: Theme.textDim
                                    }
                                    Text {
                                        width: parent.width
                                        text: cell.label.substring(4)
                                        font.bold: true
                                        font.pixelSize: ScaleMetrics.sp(9)
                                        color: cell.current ? root.accent : Theme.textPrimary
                                        elide: Text.ElideRight
                                    }
                                }
                                MouseArea {
                                    id: tileMouse
                                    anchors.fill: parent
                                    onClicked: Bridge.setArpField("style", cell.modelData)
                                }
                            }
                        }
                    }

                    SectionLabel {
                        Layout.fillWidth: true
                        text: "(n) KEYS TO HOLD · (a) ANY · (p) ONE KEY, MOTIF PHRASE"
                        font.pixelSize: ScaleMetrics.sp(8)
                        elide: Text.ElideRight
                    }
                }
            }

            // 2. Pattern: motif and grid
            Panel {
                Layout.preferredWidth: body.share * 0.34

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(8)
                    spacing: ScaleMetrics.dp(6)

                    SectionLabel { text: "MOTIF" }
                    GridLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredHeight: 4
                        columns: 3
                        rowSpacing: ScaleMetrics.dp(4)
                        columnSpacing: ScaleMetrics.dp(4)
                        Repeater {
                            model: root.lists.motifs
                            delegate: Chip {
                                required property int index
                                required property string modelData
                                text: modelData
                                Layout.fillHeight: true
                                Layout.maximumHeight: ScaleMetrics.dp(64)
                                selected: root.arp.motif === index
                                onClicked: Bridge.setArpField("motif", index)
                            }
                        }
                    }

                    SectionLabel { text: "GRID · SHARED WITH RHYTHM PATTERNS" }
                    GridLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredHeight: 3
                        columns: 3
                        rowSpacing: ScaleMetrics.dp(4)
                        columnSpacing: ScaleMetrics.dp(4)
                        Repeater {
                            model: root.lists.grids
                            delegate: Chip {
                                required property int index
                                required property string modelData
                                text: modelData
                                Layout.fillHeight: true
                                Layout.maximumHeight: ScaleMetrics.dp(64)
                                selected: root.arp.grid === index
                                onClicked: Bridge.setArpField("grid", index)
                            }
                        }
                    }
                }
            }

            // 3. Feel: duration and the numeric settings
            Panel {
                Layout.fillWidth: true

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(8)
                    spacing: ScaleMetrics.dp(6)

                    SectionLabel { text: "DURATION" }
                    GridLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        columns: 5
                        rowSpacing: ScaleMetrics.dp(4)
                        columnSpacing: ScaleMetrics.dp(4)
                        Repeater {
                            model: root.lists.durations
                            delegate: Chip {
                                required property int index
                                required property string modelData
                                text: modelData
                                Layout.fillHeight: true
                                Layout.maximumHeight: ScaleMetrics.dp(64)
                                selected: root.arp.duration === index
                                onClicked: Bridge.setArpField("duration", index)
                            }
                        }
                    }

                    component Stepper: SeqStepper {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumHeight: ScaleMetrics.dp(42)
                        Layout.maximumHeight: ScaleMetrics.dp(56)
                        textPx: ScaleMetrics.sp(11)
                        valueColor: root.accent
                    }
                    Stepper {
                        label: "OCT RANGE:"
                        count: 7
                        index: root.arp.octave + 3
                        valueText: root.arp.octaveText
                        pxPerStep: ScaleMetrics.dp(20)
                        onRequested: (i) => Bridge.setArpField("octave", i - 3)
                    }
                    Stepper {
                        label: "ACCENT:"
                        count: 101
                        index: root.arp.accent
                        valueText: root.arp.accentText
                        pxPerStep: ScaleMetrics.dp(3)
                        onRequested: (i) => Bridge.setArpField("accent", i)
                    }
                    Stepper {
                        label: "VELOCITY:"
                        count: 128
                        index: root.arp.velocity
                        valueText: root.arp.velocityText
                        pxPerStep: ScaleMetrics.dp(3)
                        onRequested: (i) => Bridge.setArpField("velocity", i)
                    }
                    Stepper {
                        label: "STEP:"
                        count: 33
                        index: root.arp.step
                        valueText: root.arp.stepText
                        pxPerStep: ScaleMetrics.dp(8)
                        onRequested: (i) => Bridge.setArpField("step", i)
                    }

                    Text {
                        Layout.fillWidth: true
                        visible: Bridge.midiClockOut
                        text: "Follows the app tempo with the Juno on SYSTEM › SYNC/TEMPO › Sync Mode SLAVE, Clock Source USB."
                        wrapMode: Text.WordWrap
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Theme.textMuted
                    }
                }
            }
        }
    }
}
