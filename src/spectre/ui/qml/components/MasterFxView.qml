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

    property int chorusType: Bridge.chorusType
    property int chorusRate: Bridge.chorusRate
    property int chorusDepth: Bridge.chorusDepth
    property int chorusPreDelay: Bridge.chorusPreDelay
    property int chorusFeedback: Bridge.chorusFeedback
    property int chorusToReverb: Bridge.chorusToReverb
    property int chorusLevel: Bridge.chorusLevel

    property int reverbType: Bridge.reverbType
    property int reverbTime: Bridge.reverbTime
    property int reverbDamp: Bridge.reverbDamp
    property int reverbPreDelay: Bridge.reverbPreDelay
    property int reverbDiffusion: Bridge.reverbDiffusion
    property int reverbTone: Bridge.reverbTone
    property int reverbLevel: Bridge.reverbLevel

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: ScaleMetrics.dp(10)
        spacing: ScaleMetrics.dp(8)

        // Header
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(8)

            Rectangle {
                width: ScaleMetrics.dp(8); height: ScaleMetrics.dp(8); radius: 4
                color: "#a855f7"
            }
            Text {
                Layout.fillWidth: true
                text: "MASTER FX (CHORUS & REVERB)"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(12)
                font.letterSpacing: 1.2
                color: Theme.textPrimary
                elide: Text.ElideRight
            }
            Rectangle {
                height: ScaleMetrics.dp(18)
                Layout.preferredWidth: Math.min(choTarget.implicitWidth + ScaleMetrics.dp(12), ScaleMetrics.dp(100))
                Layout.maximumWidth: ScaleMetrics.dp(100)
                radius: 3
                color: "#0d2838"
                border.color: "#38bdf8"
                border.width: 1
                clip: true
                Text {
                    id: choTarget
                    anchors.fill: parent
                    anchors.leftMargin: ScaleMetrics.dp(6)
                    anchors.rightMargin: ScaleMetrics.dp(6)
                    verticalAlignment: Text.AlignVCenter
                    horizontalAlignment: Text.AlignHCenter
                    text: Bridge.choEditTargetLabel
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(7)
                    font.family: Theme.fontMono
                    color: "#38bdf8"
                    elide: Text.ElideRight
                }
            }
            Rectangle {
                height: ScaleMetrics.dp(18)
                Layout.preferredWidth: Math.min(revTarget.implicitWidth + ScaleMetrics.dp(12), ScaleMetrics.dp(100))
                Layout.maximumWidth: ScaleMetrics.dp(100)
                radius: 3
                color: "#1c0d28"
                border.color: "#a855f7"
                border.width: 1
                clip: true
                Text {
                    id: revTarget
                    anchors.fill: parent
                    anchors.leftMargin: ScaleMetrics.dp(6)
                    anchors.rightMargin: ScaleMetrics.dp(6)
                    verticalAlignment: Text.AlignVCenter
                    horizontalAlignment: Text.AlignHCenter
                    text: Bridge.revEditTargetLabel
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(7)
                    font.family: Theme.fontMono
                    color: "#a855f7"
                    elide: Text.ElideRight
                }
            }
        }

        // 2 Cards: Chorus, Reverb (Master EQ removed: no SysEx control on JUNO-DS)
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: ScaleMetrics.dp(8)

            // Card 1: Master Chorus
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: ScaleMetrics.dp(6)
                color: Theme.bgApp
                border.color: Theme.borderCard
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(8)
                    spacing: ScaleMetrics.dp(5)

                    // Card Header
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: ScaleMetrics.dp(6)
                        Rectangle { width: 6; height: 6; radius: 3; color: "#38bdf8" }
                        Text { text: "MASTER CHORUS"; font.bold: true; font.pixelSize: ScaleMetrics.sp(10); color: "#38bdf8" }
                        Item { Layout.fillWidth: true }
                        Rectangle {
                            height: ScaleMetrics.dp(18)
                            width: ScaleMetrics.dp(48)
                            radius: 3
                            color: root.chorusType === 0 ? "#2b1b1b" : "#0d2838"
                            border.color: root.chorusType === 0 ? Theme.recording : "#38bdf8"
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: root.chorusType === 0 ? "OFF" : "ON"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(8)
                                color: root.chorusType === 0 ? Theme.recording : "#38bdf8"
                            }
                        }
                    }

                    // Chorus Type Selector Chips
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Repeater {
                            model: ["OFF", "CHORUS", "DELAY", "GM2 CHO"]
                            delegate: Rectangle {
                                Layout.fillWidth: true
                                height: ScaleMetrics.dp(24)
                                radius: 3
                                color: root.chorusType === index ? Theme.bgCardActive : "#10141d"
                                border.color: root.chorusType === index ? "#38bdf8" : Theme.borderCard
                                border.width: 1
                                Text {
                                    anchors.centerIn: parent
                                    text: modelData
                                    font.bold: root.chorusType === index
                                    font.pixelSize: ScaleMetrics.sp(8)
                                    color: root.chorusType === index ? "#38bdf8" : Theme.textDim
                                }
                                MouseArea { anchors.fill: parent; onClicked: Bridge.setChorusParam("type", index) }
                            }
                        }
                    }

                    // Chorus Output Routing Selector Chips
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: ScaleMetrics.dp(4)
                        Text {
                            text: "OUTPUT:"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: Theme.textDim
                        }
                        Item { Layout.fillWidth: true }
                        Repeater {
                            model: ["MAIN", "REV", "MAIN+REV"]
                            delegate: Rectangle {
                                Layout.preferredWidth: ScaleMetrics.dp(60)
                                height: ScaleMetrics.dp(20)
                                radius: 3
                                color: root.chorusToReverb === index ? "#0284c7" : "#10141d"
                                border.color: root.chorusToReverb === index ? "#38bdf8" : Theme.borderCard
                                border.width: 1
                                Text {
                                    anchors.centerIn: parent
                                    text: modelData
                                    font.bold: root.chorusToReverb === index
                                    font.pixelSize: ScaleMetrics.sp(7)
                                    color: root.chorusToReverb === index ? "#ffffff" : Theme.textDim
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: Bridge.setChorusParam("toReverb", index)
                                }
                            }
                        }
                    }

                    // 5 Full Scaled Chorus Sliders
                    FxSlider { Layout.fillWidth: true; Layout.fillHeight: true; label: "RATE"; val: root.chorusRate; accent: "#38bdf8"; isDimmed: root.chorusType === 0; onMoved: (v) => Bridge.setChorusParam("rate", v) }
                    FxSlider { Layout.fillWidth: true; Layout.fillHeight: true; label: "DEPTH"; val: root.chorusDepth; accent: "#38bdf8"; isDimmed: root.chorusType === 0; onMoved: (v) => Bridge.setChorusParam("depth", v) }
                    FxSlider { Layout.fillWidth: true; Layout.fillHeight: true; label: "PRE-DELAY"; val: root.chorusPreDelay; unitText: "ms"; accent: "#38bdf8"; isDimmed: root.chorusType === 0; onMoved: (v) => Bridge.setChorusParam("preDelay", v) }
                    FxSlider { Layout.fillWidth: true; Layout.fillHeight: true; label: "FEEDBACK"; val: root.chorusFeedback; unitText: "%"; accent: "#38bdf8"; isDimmed: root.chorusType === 0; onMoved: (v) => Bridge.setChorusParam("feedback", v) }
                    FxSlider { Layout.fillWidth: true; Layout.fillHeight: true; label: "LEVEL"; val: root.chorusLevel; accent: "#38bdf8"; isDimmed: root.chorusType === 0; onMoved: (v) => Bridge.setChorusParam("level", v) }

                    // Routing status
                    Rectangle {
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(22)
                        radius: 3
                        color: "#10141d"
                        border.color: Theme.borderCard
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: root.chorusType === 0 ? "CHORUS BYPASSED (DRY ROUTED)" : ("ROUTING: TONES ➔ CHORUS ➔ " + (root.chorusToReverb === 0 ? "MAIN" : root.chorusToReverb === 1 ? "REV" : "MAIN + REV"))
                            font.family: Theme.fontMono
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(7)
                            color: root.chorusType === 0 ? Theme.textDim : "#38bdf8"
                        }
                    }
                }
            }

            // Card 2: Master Reverb
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: ScaleMetrics.dp(6)
                color: Theme.bgApp
                border.color: Theme.borderCard
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(8)
                    spacing: ScaleMetrics.dp(5)

                    // Card Header
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: ScaleMetrics.dp(6)
                        Rectangle { width: 6; height: 6; radius: 3; color: "#a855f7" }
                        Text { text: "MASTER REVERB"; font.bold: true; font.pixelSize: ScaleMetrics.sp(10); color: "#a855f7" }
                        Item { Layout.fillWidth: true }
                        Rectangle {
                            height: ScaleMetrics.dp(18)
                            width: ScaleMetrics.dp(48)
                            radius: 3
                            color: root.reverbType === 0 ? "#2b1b1b" : "#231535"
                            border.color: root.reverbType === 0 ? Theme.recording : "#a855f7"
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: root.reverbType === 0 ? "OFF" : "ON"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(8)
                                color: root.reverbType === 0 ? Theme.recording : "#a855f7"
                            }
                        }
                    }

                    // Reverb Type Selector Chips
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Repeater {
                            model: ["OFF", "REVERB", "ROOM", "HALL", "PLATE", "GM2"]
                            delegate: Rectangle {
                                Layout.fillWidth: true
                                height: ScaleMetrics.dp(24)
                                radius: 3
                                color: root.reverbType === index ? Theme.bgCardActive : "#10141d"
                                border.color: root.reverbType === index ? "#a855f7" : Theme.borderCard
                                border.width: 1
                                Text {
                                    anchors.centerIn: parent
                                    text: modelData
                                    font.bold: root.reverbType === index
                                    font.pixelSize: ScaleMetrics.sp(8)
                                    color: root.reverbType === index ? "#a855f7" : Theme.textDim
                                }
                                MouseArea { anchors.fill: parent; onClicked: Bridge.setReverbParam("type", index) }
                            }
                        }
                    }

                    // 6 Full Scaled Reverb Sliders
                    FxSlider { Layout.fillWidth: true; Layout.fillHeight: true; label: "TIME"; val: root.reverbTime; unitText: "s"; accent: "#a855f7"; isDimmed: root.reverbType === 0; onMoved: (v) => Bridge.setReverbParam("time", v) }
                    FxSlider { Layout.fillWidth: true; Layout.fillHeight: true; label: "HF DAMP"; val: root.reverbDamp; accent: "#a855f7"; isDimmed: root.reverbType === 0; onMoved: (v) => Bridge.setReverbParam("damp", v) }
                    FxSlider { Layout.fillWidth: true; Layout.fillHeight: true; label: "PRE-DELAY"; val: root.reverbPreDelay; unitText: "ms"; accent: "#a855f7"; isDimmed: root.reverbType === 0; onMoved: (v) => Bridge.setReverbParam("preDelay", v) }
                    FxSlider { Layout.fillWidth: true; Layout.fillHeight: true; label: "DIFFUSION"; val: root.reverbDiffusion; accent: "#a855f7"; isDimmed: root.reverbType === 0; onMoved: (v) => Bridge.setReverbParam("diffusion", v) }
                    FxSlider { Layout.fillWidth: true; Layout.fillHeight: true; label: "LOW CUT / TONE"; val: root.reverbTone; accent: "#a855f7"; isDimmed: root.reverbType === 0; onMoved: (v) => Bridge.setReverbParam("tone", v) }
                    FxSlider { Layout.fillWidth: true; Layout.fillHeight: true; label: "LEVEL"; val: root.reverbLevel; accent: "#a855f7"; isDimmed: root.reverbType === 0; onMoved: (v) => Bridge.setReverbParam("level", v) }

                    // Routing status
                    Rectangle {
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(22)
                        radius: 3
                        color: "#10141d"
                        border.color: Theme.borderCard
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: root.reverbType === 0 ? "REVERB BYPASSED (DRY ROUTED)" : "ROUTING: BUS ➔ REVERB ➔ MASTER OUT"
                            font.family: Theme.fontMono
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(7)
                            color: root.reverbType === 0 ? Theme.textDim : "#a855f7"
                        }
                    }
                }
            }

        }
    }

    // Reusable Scaled FX Slider Component
    component FxSlider: Rectangle {
        id: fs
        property string label: "PARAM"
        property int val: 50
        property int minVal: 0
        property int maxVal: 127
        property string unitText: ""
        property color accent: Theme.primary
        property bool isDimmed: false
        signal moved(int v)

        height: ScaleMetrics.dp(38)
        radius: 4
        color: "#10141d"
        border.color: Theme.borderCard
        border.width: 1
        opacity: isDimmed ? 0.35 : 1.0

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(5)
            spacing: 2

            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: fs.label
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: Theme.textSecondary
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                Text {
                    text: fs.val.toString() + (fs.unitText !== "" ? " " + fs.unitText : "")
                    font.family: Theme.fontMono
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(9)
                    color: fs.accent
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
                    width: parent.width * Math.max(0.0, Math.min(1.0, (fs.val - fs.minVal) / Math.max(1, fs.maxVal - fs.minVal)))
                    height: parent.height
                    radius: 3
                    color: fs.accent
                    opacity: 0.38
                }

                function updateVal(mouseX) {
                    var norm = Math.max(0.0, Math.min(1.0, mouseX / width));
                    var v = Math.round(fs.minVal + norm * (fs.maxVal - fs.minVal));
                    fs.moved(v);
                }

                MouseArea {
                    anchors.fill: parent
                    enabled: !fs.isDimmed
                    onPositionChanged: (mouse) => {
                        if (pressed) parent.updateVal(mouse.x);
                    }
                    onPressed: (mouse) => {
                        parent.updateVal(mouse.x);
                    }
                }
            }
        }
    }

}
