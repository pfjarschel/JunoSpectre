import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

Rectangle {
    id: root
    width: ScaleMetrics.dp(195)
    color: Theme.bgCard
    radius: ScaleMetrics.dp(8)
    border.color: Theme.borderCard
    border.width: 1

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: ScaleMetrics.dp(8)
        anchors.rightMargin: ScaleMetrics.dp(8)
        anchors.topMargin: ScaleMetrics.dp(8)
        anchors.bottomMargin: ScaleMetrics.dp(8)
        spacing: ScaleMetrics.dp(6)

        // 1. Header Title
        RowLayout {
            Layout.fillWidth: true
            Text {
                text: "TONES 1 - 4"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(11)
                font.letterSpacing: 1.2
                color: Theme.textSecondary
            }
            Item { Layout.fillWidth: true }
            Text {
                text: Bridge.curve === "equal_power" ? "EQ-PWR" : "LINEAR"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(9)
                color: Theme.textDim
            }
        }

        // 2. Four Tone Channels (T1 - T4)
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: ScaleMetrics.dp(6)

            ToneChannel {
                toneNumber: 1
                toneName: "T1 (NW)"
                toneColor: Theme.tone1
                level: Bridge.tone1Level
                isMuted: Bridge.tone1Muted
            }

            ToneChannel {
                toneNumber: 2
                toneName: "T2 (NE)"
                toneColor: Theme.tone2
                level: Bridge.tone2Level
                isMuted: Bridge.tone2Muted
            }

            ToneChannel {
                toneNumber: 3
                toneName: "T3 (SW)"
                toneColor: Theme.tone3
                level: Bridge.tone3Level
                isMuted: Bridge.tone3Muted
            }

            ToneChannel {
                toneNumber: 4
                toneName: "T4 (SE)"
                toneColor: Theme.tone4
                level: Bridge.tone4Level
                isMuted: Bridge.tone4Muted
            }
        }

        // 3. Separator
        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Theme.borderCard
        }

        // 4. Master Patch Section (Cutoff, Reso, Level)
        ColumnLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(4)

            // Cutoff Offset Slider
            MasterParamSlider {
                Layout.fillWidth: true
                label: "CUTOFF"
                displayVal: (Bridge.masterCutoff >= 64 ? "+" : "") + (Bridge.masterCutoff - 64)
                normVal: (Bridge.masterCutoff - 1) / 126.0
                trackColor: Theme.tone2
                onValueChanged: (norm) => {
                    Bridge.setMasterCutoff(Math.round(1 + norm * 126));
                }
            }

            // Resonance Offset Slider
            MasterParamSlider {
                Layout.fillWidth: true
                label: "RESO"
                displayVal: (Bridge.masterReso >= 64 ? "+" : "") + (Bridge.masterReso - 64)
                normVal: (Bridge.masterReso - 1) / 126.0
                trackColor: Theme.tone3
                onValueChanged: (norm) => {
                    Bridge.setMasterReso(Math.round(1 + norm * 126));
                }
            }

            // Master Volume / Level Slider
            MasterParamSlider {
                Layout.fillWidth: true
                label: "LEVEL"
                displayVal: Bridge.masterLevel.toString()
                normVal: Bridge.masterLevel / 127.0
                trackColor: Theme.primary
                onValueChanged: (norm) => {
                    Bridge.setMasterLevel(Math.round(norm * 127));
                }
            }
        }
    }

    // Component for single vertical tone channel (Mute button + Meter + Readout)
    component ToneChannel: ColumnLayout {
        id: chanRoot
        property int toneNumber: 1
        property string toneName: "T1"
        property color toneColor: Theme.tone1
        property int level: 0
        property bool isMuted: false

        Layout.fillWidth: true
        Layout.fillHeight: true
        spacing: ScaleMetrics.dp(3)

        // ON / MUTE Button
        Rectangle {
            Layout.fillWidth: true
            height: ScaleMetrics.dp(20)
            radius: ScaleMetrics.dp(4)
            color: chanRoot.isMuted ? "#3f1a1a" : (chanRoot.level > 0 ? Theme.bgCardActive : Theme.bgApp)
            border.color: chanRoot.isMuted ? Theme.recording : (chanRoot.level > 0 ? chanRoot.toneColor : Theme.borderCard)
            border.width: 1

            Text {
                anchors.centerIn: parent
                text: chanRoot.isMuted ? "MUTE" : "ON"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(9)
                color: chanRoot.isMuted ? Theme.recording : (chanRoot.level > 0 ? chanRoot.toneColor : Theme.textDim)
            }

            MouseArea {
                anchors.fill: parent
                onClicked: Bridge.toggleToneMute(chanRoot.toneNumber)
            }
        }

        // Numeric level readout
        Text {
            text: chanRoot.isMuted ? "OFF" : chanRoot.level
            font.bold: true
            font.pixelSize: ScaleMetrics.sp(10)
            font.family: Theme.fontMono
            color: chanRoot.isMuted ? Theme.textDim : (chanRoot.level > 0 ? chanRoot.toneColor : Theme.textDim)
            Layout.alignment: Qt.AlignHCenter
        }

        // Meter Track Background
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: ScaleMetrics.dp(4)
            color: Theme.bgApp
            border.color: Theme.borderCard
            border.width: 1
            clip: true

            // Meter Fill Bar (animates height)
            Rectangle {
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                height: chanRoot.isMuted ? 0 : Math.max(0, (parent.height * chanRoot.level) / 127)
                radius: ScaleMetrics.dp(3)
                color: chanRoot.toneColor

                Behavior on height {
                    NumberAnimation { duration: 50; easing.type: Easing.OutQuad }
                }

                // Inner glow bar
                Rectangle {
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    height: ScaleMetrics.dp(3)
                    color: "#ffffff"
                    opacity: (!chanRoot.isMuted && chanRoot.level > 0) ? 0.35 : 0.0
                }
            }
        }

        // Tone Label Badge
        Text {
            text: chanRoot.toneName
            font.bold: true
            font.pixelSize: ScaleMetrics.sp(9)
            color: chanRoot.toneColor
            Layout.alignment: Qt.AlignHCenter
        }
    }

    // Mini Master Parameter Horizontal Slider
    component MasterParamSlider: RowLayout {
        id: sliderRoot
        property string label: "PARAM"
        property string displayVal: "0"
        property real normVal: 0.5
        property color trackColor: Theme.primary
        signal valueChanged(real val)

        spacing: ScaleMetrics.dp(6)

        Text {
            text: sliderRoot.label
            font.bold: true
            font.pixelSize: ScaleMetrics.sp(9)
            color: Theme.textSecondary
            Layout.preferredWidth: ScaleMetrics.dp(42)
        }

        // Slider Track
        Rectangle {
            id: track
            Layout.fillWidth: true
            height: ScaleMetrics.dp(14)
            radius: ScaleMetrics.dp(3)
            color: Theme.bgApp
            border.color: Theme.borderCard
            border.width: 1
            clip: true

            Rectangle {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                width: parent.width * Math.max(0.0, Math.min(1.0, sliderRoot.normVal))
                radius: ScaleMetrics.dp(3)
                color: sliderRoot.trackColor
                opacity: 0.85
            }

            MouseArea {
                anchors.fill: parent
                onPressed: (mouse) => {
                    const norm = Math.max(0.0, Math.min(1.0, mouse.x / width));
                    sliderRoot.valueChanged(norm);
                }
                onPositionChanged: (mouse) => {
                    if (pressed) {
                        const norm = Math.max(0.0, Math.min(1.0, mouse.x / width));
                        sliderRoot.valueChanged(norm);
                    }
                }
            }
        }

        Text {
            text: sliderRoot.displayVal
            font.bold: true
            font.pixelSize: ScaleMetrics.sp(9)
            font.family: Theme.fontMono
            color: Theme.textPrimary
            Layout.preferredWidth: ScaleMetrics.dp(32)
            horizontalAlignment: Text.AlignRight
        }
    }
}
