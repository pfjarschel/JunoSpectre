pragma ValueTypeBehavior: Copy
import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

// Global modal: the patch's Tone Mix Table. STRUCTURE = how tones 1&2 / 3&4
// combine (types 1-10, booster); ZONES = where on the keyboard and at which
// velocity each tone sounds. Opened from every synth-engine page.
Rectangle {
    id: root
    anchors.fill: parent
    visible: false
    z: 998
    color: "#e60a0c10"

    property string tab: "STRUCTURE"
    readonly property var tmt: Bridge.tmt
    readonly property var toneColors: [Theme.tone1, Theme.tone2, Theme.tone3, Theme.tone4]
    readonly property var noteNames: ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    // Velocity ranges only pick tones with VELOCITY CONTROL ON, or as Matrix
    // Control value ranges with the TMT CONTROL switch on
    readonly property bool veloRangesLive: tmt.veloControl === 1 || tmt.ctrlSwitch

    function open(t) {
        tab = (t === "ZONES") ? "ZONES" : "STRUCTURE";
        visible = true;
    }
    function close() {
        visible = false;
    }
    function noteName(n) {
        return noteNames[n % 12] + (Math.floor(n / 12) - 1);
    }
    function muted(i) {
        return [Bridge.tone1Muted, Bridge.tone2Muted, Bridge.tone3Muted, Bridge.tone4Muted][i];
    }

    MouseArea {
        anchors.fill: parent
        onClicked: root.close()
    }

    Rectangle {
        id: card
        width: Math.min(parent.width - ScaleMetrics.dp(24), ScaleMetrics.dp(1000))
        height: Math.min(parent.height - ScaleMetrics.dp(20), ScaleMetrics.dp(580))
        anchors.centerIn: parent
        radius: ScaleMetrics.dp(10)
        color: Theme.bgCard
        border.color: Theme.borderActive
        border.width: 1

        MouseArea {
            anchors.fill: parent
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(12)
            spacing: ScaleMetrics.dp(8)

            RowLayout {
                Layout.fillWidth: true
                spacing: ScaleMetrics.dp(8)

                Text {
                    text: "TONE MIX TABLE"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(13)
                    font.letterSpacing: 1.2
                    color: Theme.textPrimary
                }

                Repeater {
                    model: ["STRUCTURE", "ZONES"]
                    delegate: Rectangle {
                        required property string modelData
                        readonly property bool sel: root.tab === modelData
                        width: ScaleMetrics.dp(110)
                        height: ScaleMetrics.dp(28)
                        radius: ScaleMetrics.dp(4)
                        color: sel ? Theme.primary : (tabArea.pressed ? Theme.bgCardActive : Theme.bgApp)
                        border.color: sel ? "transparent" : Theme.borderCard
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: parent.modelData
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(9)
                            color: parent.sel ? "#ffffff" : Theme.textSecondary
                        }
                        MouseArea {
                            id: tabArea
                            anchors.fill: parent
                            onClicked: root.tab = parent.modelData
                        }
                    }
                }

                Item { Layout.fillWidth: true }

                Rectangle {
                    width: ScaleMetrics.dp(36)
                    height: ScaleMetrics.dp(26)
                    radius: ScaleMetrics.dp(6)
                    color: closeArea.pressed ? "#3f1a1a" : Theme.bgApp
                    border.color: Theme.borderCard
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: "✕"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(13)
                        color: closeArea.pressed ? Theme.recording : Theme.textSecondary
                    }
                    MouseArea {
                        id: closeArea
                        anchors.fill: parent
                        onClicked: root.close()
                    }
                }
            }

            // =================================================================
            // STRUCTURE: the two tone pairs
            // =================================================================
            RowLayout {
                visible: root.tab === "STRUCTURE"
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: ScaleMetrics.dp(10)

                TmtStructureCard {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    pair: 1
                }
                TmtStructureCard {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    pair: 2
                }
            }

            // =================================================================
            // ZONES: key and velocity ranges per tone
            // =================================================================
            ColumnLayout {
                visible: root.tab === "ZONES"
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: ScaleMetrics.dp(6)

                // Tone selection mode
                RowLayout {
                    Layout.fillWidth: true
                    spacing: ScaleMetrics.dp(4)

                    Text {
                        text: "VELOCITY CONTROL"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Theme.textSecondary
                        Layout.rightMargin: ScaleMetrics.dp(4)
                    }
                    Repeater {
                        model: Bridge.tmtVelocityControlLabels
                        delegate: Rectangle {
                            required property int index
                            required property string modelData
                            readonly property bool sel: root.tmt.veloControl === index
                            width: ScaleMetrics.dp(70)
                            height: ScaleMetrics.dp(28)
                            radius: ScaleMetrics.dp(4)
                            color: sel ? Theme.primary : (vcArea.pressed ? Theme.bgCardActive : Theme.bgApp)
                            border.color: sel ? "transparent" : Theme.borderCard
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: parent.modelData
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(8)
                                color: parent.sel ? "#ffffff" : Theme.textSecondary
                            }
                            MouseArea {
                                id: vcArea
                                anchors.fill: parent
                                onClicked: Bridge.setTmtVelocityControl(index)
                            }
                        }
                    }

                    Item { Layout.preferredWidth: ScaleMetrics.dp(12) }

                    Rectangle {
                        width: ScaleMetrics.dp(150)
                        height: ScaleMetrics.dp(28)
                        radius: ScaleMetrics.dp(4)
                        color: root.tmt.ctrlSwitch ? Theme.bgCardActive : Theme.bgApp
                        border.color: root.tmt.ctrlSwitch ? "#38bdf8" : Theme.borderCard
                        border.width: 1
                        RowLayout {
                            anchors.centerIn: parent
                            spacing: 4
                            Rectangle {
                                width: 6; height: 6; radius: 3
                                color: root.tmt.ctrlSwitch ? "#38bdf8" : Theme.textDim
                            }
                            Text {
                                text: root.tmt.ctrlSwitch ? "MATRIX PICKS TONES: ON" : "MATRIX PICKS TONES: OFF"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(8)
                                color: root.tmt.ctrlSwitch ? Theme.textPrimary : Theme.textDim
                            }
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: Bridge.setTmtControlSwitch(!root.tmt.ctrlSwitch)
                        }
                    }

                    Text {
                        Layout.fillWidth: true
                        Layout.leftMargin: ScaleMetrics.dp(8)
                        text: {
                            const vc = root.tmt.veloControl;
                            if (root.tmt.ctrlSwitch)
                                return "A Matrix Control source picks the tones, using the velocity ranges as its value ranges.";
                            if (vc === 1) return "Velocity picks which tones sound (velocity ranges below).";
                            if (vc === 2) return "Each note plays a random tone; velocity ranges are ignored.";
                            if (vc === 3) return "Notes cycle through the tones in turn; velocity ranges are ignored.";
                            return "All tones play at every velocity; velocity ranges are ignored.";
                        }
                        wrapMode: Text.WordWrap
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Theme.textMuted
                    }
                }

                RangeSection {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    kind: "key"
                    title: "KEY RANGE"
                    live: true
                }
                RangeSection {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    kind: "velo"
                    title: root.tmt.ctrlSwitch ? "MATRIX CONTROL RANGE" : "VELOCITY RANGE"
                    live: root.veloRangesLive
                }

                Text {
                    Layout.fillWidth: true
                    text: "Drag the top corners to move a range's edges, the feet of the ramps to set its fades, the middle to slide it. Hold a tone chip to reset its range. Where only one tone of a merged pair sounds, it plays as type 1."
                    wrapMode: Text.WordWrap
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: Theme.textDim
                }
            }
        }
    }

    // Four tone lanes for one kind of range ("key" or "velo")
    component RangeSection: Rectangle {
        id: section
        property string kind: "key"
        property string title: ""
        property bool live: true
        readonly property bool isKey: kind === "key"
        readonly property real laneLeft: ScaleMetrics.dp(44)
        readonly property real laneRight: ScaleMetrics.dp(150)

        radius: ScaleMetrics.dp(6)
        color: Theme.bgApp
        border.color: Theme.borderCard
        border.width: 1

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(6)
            spacing: ScaleMetrics.dp(3)

            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: section.title
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(9)
                    font.letterSpacing: 1.1
                    color: section.live ? Theme.textPrimary : Theme.textDim
                }
                Text {
                    visible: !section.live
                    text: "(no effect with this VELOCITY CONTROL)"
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: Theme.textDim
                }
                Item { Layout.fillWidth: true }
                Rectangle {
                    width: ScaleMetrics.dp(80)
                    height: ScaleMetrics.dp(20)
                    radius: ScaleMetrics.dp(4)
                    color: resetAll.pressed ? Theme.bgCardActive : Theme.bgSurface
                    border.color: Theme.borderCard
                    border.width: 1
                    Text {
                        anchors.centerIn: parent
                        text: "RESET ALL"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Theme.textSecondary
                    }
                    MouseArea {
                        id: resetAll
                        anchors.fill: parent
                        onClicked: Bridge.resetToneRange(0, section.kind)
                    }
                }
            }

            Repeater {
                model: 4
                delegate: RowLayout {
                    id: laneRow
                    required property int index
                    readonly property var t: root.tmt.tones[index]
                    readonly property bool off: root.muted(index)
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: ScaleMetrics.dp(6)
                    opacity: off ? 0.45 : 1.0

                    // Tone chip: tap to reset this lane
                    Rectangle {
                        Layout.preferredWidth: section.laneLeft - ScaleMetrics.dp(6)
                        Layout.fillHeight: true
                        radius: ScaleMetrics.dp(4)
                        color: chipArea.pressed ? Theme.bgCardActive : Theme.bgSurface
                        border.color: root.toneColors[laneRow.index]
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: "T" + (laneRow.index + 1)
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(9)
                            color: root.toneColors[laneRow.index]
                        }
                        MouseArea {
                            id: chipArea
                            anchors.fill: parent
                            onPressAndHold: Bridge.resetToneRange(laneRow.index + 1, section.kind)
                        }
                    }

                    TmtRangeLane {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        minV: section.isKey ? 0 : 1
                        lower: section.isKey ? laneRow.t.keyLower : laneRow.t.veloLower
                        upper: section.isKey ? laneRow.t.keyUpper : laneRow.t.veloUpper
                        fadeLower: section.isKey ? laneRow.t.keyFadeLower : laneRow.t.veloFadeLower
                        fadeUpper: section.isKey ? laneRow.t.keyFadeUpper : laneRow.t.veloFadeUpper
                        barColor: root.toneColors[laneRow.index]
                        active: section.live && !laneRow.off
                        onEdit: (which, value) => Bridge.setToneRange(laneRow.index + 1, section.kind + which, value)
                        onSlide: (lo, hi) => Bridge.setToneRangeSpan(laneRow.index + 1, section.kind, lo, hi)
                    }

                    Text {
                        Layout.preferredWidth: section.laneRight - ScaleMetrics.dp(6)
                        text: {
                            const t = laneRow.t;
                            const lo = section.isKey ? root.noteName(t.keyLower) : t.veloLower;
                            const hi = section.isKey ? root.noteName(t.keyUpper) : t.veloUpper;
                            const fl = section.isKey ? t.keyFadeLower : t.veloFadeLower;
                            const fu = section.isKey ? t.keyFadeUpper : t.veloFadeUpper;
                            return lo + " – " + hi + "\nfade " + fl + " / " + fu;
                        }
                        font.pixelSize: ScaleMetrics.sp(8)
                        font.family: Theme.fontMono
                        color: Theme.textSecondary
                    }
                }
            }

            // Scale under the lanes
            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: ScaleMetrics.dp(12)
                Repeater {
                    model: section.isKey ? [0, 12, 24, 36, 48, 60, 72, 84, 96, 108, 120] : [1, 32, 64, 96, 127]
                    delegate: Text {
                        required property int modelData
                        readonly property real laneW: section.width - ScaleMetrics.dp(12) - section.laneLeft - section.laneRight
                        x: section.laneLeft + laneW * (modelData - (section.isKey ? 0 : 1)) / (section.isKey ? 128 : 127) - width / 2
                        text: section.isKey ? root.noteName(modelData) : modelData.toString()
                        font.pixelSize: ScaleMetrics.sp(7)
                        font.family: Theme.fontMono
                        color: Theme.textDim
                    }
                }
            }
        }
    }
}
