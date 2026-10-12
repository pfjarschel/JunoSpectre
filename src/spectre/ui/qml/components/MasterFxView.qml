pragma ValueTypeBehavior: Copy
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
                color: Theme.pageAccent
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
                color: Theme.tint(Theme.pageAccent)
                border.color: Theme.pageAccent
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
                    color: Theme.pageAccent
                    elide: Text.ElideRight
                }
            }
            Rectangle {
                height: ScaleMetrics.dp(18)
                Layout.preferredWidth: Math.min(revTarget.implicitWidth + ScaleMetrics.dp(12), ScaleMetrics.dp(100))
                Layout.maximumWidth: ScaleMetrics.dp(100)
                radius: 3
                color: Theme.tint(Theme.pageAccent)
                border.color: Theme.pageAccent
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
                    color: Theme.pageAccent
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
                        Rectangle { width: 6; height: 6; radius: 3; color: Theme.pageAccent }
                        Text { text: "MASTER CHORUS"; font.bold: true; font.pixelSize: ScaleMetrics.sp(10); color: Theme.pageAccent }
                        Item { Layout.fillWidth: true }
                        Rectangle {
                            height: ScaleMetrics.dp(18)
                            width: ScaleMetrics.dp(48)
                            radius: 3
                            color: root.chorusType === 0 ? Theme.tint(Theme.recording, 0.15) : Theme.tint(Theme.pageAccent)
                            border.color: root.chorusType === 0 ? Theme.recording : Theme.pageAccent
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: root.chorusType === 0 ? "OFF" : "ON"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(8)
                                color: root.chorusType === 0 ? Theme.recording : Theme.pageAccent
                            }
                        }
                    }

                    // Chorus Type Selector Chips
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Repeater {
                            model: ["OFF", "CHORUS", "DELAY", "GM2 CHO"]
                            delegate: SpButton {
                                Layout.fillWidth: true
                                implicitHeight: ScaleMetrics.dp(24)
                                text: modelData
                                fontSize: 8
                                checked: root.chorusType === index
                                onClicked: Bridge.setChorusParam("type", index)
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
                            delegate: SpButton {
                                Layout.preferredWidth: ScaleMetrics.dp(60)
                                implicitHeight: ScaleMetrics.dp(20)
                                text: modelData
                                fontSize: 8
                                checked: root.chorusToReverb === index
                                onClicked: Bridge.setChorusParam("toReverb", index)
                            }
                        }
                    }

                    // 5 Full Scaled Chorus Sliders
                    FxSlider { Layout.fillWidth: true; Layout.fillHeight: true; label: "RATE"; val: root.chorusRate; accent: Theme.pageAccent; isDimmed: root.chorusType === 0; onMoved: (v) => Bridge.setChorusParam("rate", v) }
                    FxSlider { Layout.fillWidth: true; Layout.fillHeight: true; label: "DEPTH"; val: root.chorusDepth; accent: Theme.pageAccent; isDimmed: root.chorusType === 0; onMoved: (v) => Bridge.setChorusParam("depth", v) }
                    FxSlider { Layout.fillWidth: true; Layout.fillHeight: true; label: "PRE-DELAY"; val: root.chorusPreDelay; unitText: "ms"; accent: Theme.pageAccent; isDimmed: root.chorusType === 0; onMoved: (v) => Bridge.setChorusParam("preDelay", v) }
                    FxSlider { Layout.fillWidth: true; Layout.fillHeight: true; label: "FEEDBACK"; val: root.chorusFeedback; unitText: "%"; accent: Theme.pageAccent; isDimmed: root.chorusType === 0; onMoved: (v) => Bridge.setChorusParam("feedback", v) }
                    FxSlider { Layout.fillWidth: true; Layout.fillHeight: true; label: "LEVEL"; val: root.chorusLevel; accent: Theme.pageAccent; isDimmed: root.chorusType === 0; onMoved: (v) => Bridge.setChorusParam("level", v) }

                    // Routing status
                    Rectangle {
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(22)
                        radius: 3
                        color: Theme.bgControl
                        border.color: Theme.borderCard
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: root.chorusType === 0 ? "CHORUS BYPASSED (DRY ROUTED)" : ("ROUTING: TONES → CHORUS → " + (root.chorusToReverb === 0 ? "MAIN" : root.chorusToReverb === 1 ? "REV" : "MAIN + REV"))
                            font.family: Theme.fontMono
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(7)
                            color: root.chorusType === 0 ? Theme.textDim : Theme.pageAccent
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
                        Rectangle { width: 6; height: 6; radius: 3; color: Theme.pageAccent }
                        Text { text: "MASTER REVERB"; font.bold: true; font.pixelSize: ScaleMetrics.sp(10); color: Theme.pageAccent }
                        Item { Layout.fillWidth: true }
                        Rectangle {
                            height: ScaleMetrics.dp(18)
                            width: ScaleMetrics.dp(48)
                            radius: 3
                            color: root.reverbType === 0 ? Theme.tint(Theme.recording, 0.15) : Theme.tint(Theme.pageAccent)
                            border.color: root.reverbType === 0 ? Theme.recording : Theme.pageAccent
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: root.reverbType === 0 ? "OFF" : "ON"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(8)
                                color: root.reverbType === 0 ? Theme.recording : Theme.pageAccent
                            }
                        }
                    }

                    // Reverb Type Selector Chips
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Repeater {
                            model: ["OFF", "REVERB", "ROOM", "HALL", "PLATE", "GM2"]
                            delegate: SpButton {
                                Layout.fillWidth: true
                                implicitHeight: ScaleMetrics.dp(24)
                                text: modelData
                                fontSize: 8
                                checked: root.reverbType === index
                                onClicked: Bridge.setReverbParam("type", index)
                            }
                        }
                    }

                    // 6 Full Scaled Reverb Sliders
                    FxSlider { Layout.fillWidth: true; Layout.fillHeight: true; label: "TIME"; val: root.reverbTime; unitText: "s"; accent: Theme.pageAccent; isDimmed: root.reverbType === 0; onMoved: (v) => Bridge.setReverbParam("time", v) }
                    FxSlider { Layout.fillWidth: true; Layout.fillHeight: true; label: "HF DAMP"; val: root.reverbDamp; accent: Theme.pageAccent; isDimmed: root.reverbType === 0; onMoved: (v) => Bridge.setReverbParam("damp", v) }
                    FxSlider { Layout.fillWidth: true; Layout.fillHeight: true; label: "PRE-DELAY"; val: root.reverbPreDelay; unitText: "ms"; accent: Theme.pageAccent; isDimmed: root.reverbType === 0; onMoved: (v) => Bridge.setReverbParam("preDelay", v) }
                    FxSlider { Layout.fillWidth: true; Layout.fillHeight: true; label: "DIFFUSION"; val: root.reverbDiffusion; accent: Theme.pageAccent; isDimmed: root.reverbType === 0; onMoved: (v) => Bridge.setReverbParam("diffusion", v) }
                    FxSlider { Layout.fillWidth: true; Layout.fillHeight: true; label: "LOW CUT / TONE"; val: root.reverbTone; accent: Theme.pageAccent; isDimmed: root.reverbType === 0; onMoved: (v) => Bridge.setReverbParam("tone", v) }
                    FxSlider { Layout.fillWidth: true; Layout.fillHeight: true; label: "LEVEL"; val: root.reverbLevel; accent: Theme.pageAccent; isDimmed: root.reverbType === 0; onMoved: (v) => Bridge.setReverbParam("level", v) }

                    // Routing status
                    Rectangle {
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(22)
                        radius: 3
                        color: Theme.bgControl
                        border.color: Theme.borderCard
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: root.reverbType === 0 ? "REVERB BYPASSED (DRY ROUTED)" : "ROUTING: BUS → REVERB → MASTER OUT"
                            font.family: Theme.fontMono
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(7)
                            color: root.reverbType === 0 ? Theme.textDim : Theme.pageAccent
                        }
                    }
                }
            }

        }
    }

    // Reusable Scaled FX Slider Component
    component FxSlider: SpSlider {
        property int val: 50
        property int minVal: 0
        property int maxVal: 127
        property string unitText: ""
        property bool isDimmed: false

        stacked: true
        enabled: !isDimmed
        from: minVal
        to: maxVal
        integer: true
        norm: (val - minVal) / Math.max(1, maxVal - minVal)
        valueText: val.toString() + (unitText !== "" ? " " + unitText : "")
    }

}
