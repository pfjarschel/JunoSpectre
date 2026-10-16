pragma ValueTypeBehavior: Copy
import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

Rectangle {
    id: root
    width: ScaleMetrics.dp(360)
    color: Theme.bgCard
    radius: ScaleMetrics.dp(8)
    border.color: Theme.borderCard
    border.width: 1

    property int activeTab: 0 // 0: TVF, 1: TVA, 2: LFOs, 3: PITCH / PORTA
    property int activeLfoTab: 1 // 1: LFO 1, 2: LFO 2

    // Active LFO properties helper
    readonly property var lfoData: activeLfoTab === 1 ? Bridge.lfo1Data : Bridge.lfo2Data

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: ScaleMetrics.dp(8)
        spacing: ScaleMetrics.dp(6)

        // =====================================================================
        // 1. TOP HEADER: TITLE + LINKED 4 TONES INDICATOR
        // =====================================================================
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(6)

            Rectangle {
                width: ScaleMetrics.dp(8)
                height: ScaleMetrics.dp(8)
                radius: 4
                color: Theme.pageAccent
            }

            Text {
                text: "SCULPTOR"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(11)
                font.letterSpacing: 1.2
                color: Theme.textPrimary
            }

            Item { Layout.fillWidth: true }

            Rectangle {
                height: ScaleMetrics.dp(20)
                implicitWidth: ScaleMetrics.dp(105)
                radius: ScaleMetrics.dp(3)
                color: Theme.bgRaised
                border.color: Theme.pageAccent
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: 4
                    Rectangle {
                        width: 5; height: 5; radius: 2.5
                        color: Theme.pageAccent
                    }
                    Text {
                        text: "LINKED (4 TONES)"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Theme.pageAccent
                    }
                }
            }
        }

        // =====================================================================
        // 2. MASTER CATEGORY TABS: [ TVF ] [ TVA ] [ LFOs ] [ PITCH / PORTA ]
        // =====================================================================
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(4)

            CategoryTabButton {
                Layout.fillWidth: true
                tabTitle: "TVF"
                isSelected: root.activeTab === 0
                onClicked: root.activeTab = 0
            }

            CategoryTabButton {
                Layout.fillWidth: true
                tabTitle: "TVA"
                isSelected: root.activeTab === 1
                onClicked: root.activeTab = 1
            }

            CategoryTabButton {
                Layout.fillWidth: true
                tabTitle: "LFOs"
                isSelected: root.activeTab === 2
                onClicked: root.activeTab = 2
            }

            CategoryTabButton {
                Layout.fillWidth: true
                tabTitle: "PITCH/PORTA"
                isSelected: root.activeTab === 3
                onClicked: root.activeTab = 3
            }
        }

        // =====================================================================
        // 3. TAB WORKSPACE CONTAINER (NEUTRAL SLATE STYLING, NO CURVES)
        // =====================================================================
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: ScaleMetrics.dp(6)
            color: Theme.bgApp
            border.color: Theme.borderCard
            border.width: 1
            clip: true

            // -----------------------------------------------------------------
            // TAB 0: TVF FILTER & ENVELOPE
            // -----------------------------------------------------------------
            ColumnLayout {
                visible: root.activeTab === 0
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(8)
                spacing: ScaleMetrics.dp(4)

                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: "TVF FILTER & ENVELOPE"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(10)
                        color: Theme.textPrimary
                    }
                    Item { Layout.fillWidth: true }
                }

                // Filter Type Selector Chips
                RowLayout {
                    Layout.fillWidth: true
                    spacing: ScaleMetrics.dp(3)
                    Repeater {
                        model: ["OFF", "LPF", "LPF2", "LPF3", "BPF", "HPF", "PKG"]
                        delegate: SpButton {
                            Layout.fillWidth: true
                            implicitHeight: ScaleMetrics.dp(22)
                            text: modelData
                            fontSize: 8
                            checked: Bridge.tvfType === modelData
                            onClicked: Bridge.sculptTvfType(modelData)
                        }
                    }
                }

                SpSlider {
                    ctlKey: "tone.tvf_cutoff"
                    Layout.fillWidth: true
                    label: "CUTOFF"
                    valueText: Bridge.masterCutoff.toString()
                    norm: (Bridge.masterCutoff - 1) / 126.0
                    onMoved: (norm) => Bridge.sculptCutoff(Math.round(1 + norm * 126))
                }

                SpSlider {
                    ctlKey: "tone.tvf_resonance"
                    Layout.fillWidth: true
                    label: "RESONANCE"
                    valueText: Bridge.masterReso.toString()
                    norm: (Bridge.masterReso - 1) / 126.0
                    onMoved: (norm) => Bridge.sculptReso(Math.round(1 + norm * 126))
                }

                SpSlider {
                    ctlKey: "tone.tvf_keyfollow"
                    Layout.fillWidth: true
                    label: "KEY FOLLOW"
                    valueText: (Bridge.tvfKeyFollow >= 0 ? "+" : "") + Bridge.tvfKeyFollow + "%"
                    norm: (Bridge.tvfKeyFollow + 100) / 200.0
                    bipolar: true
                    onMoved: (norm) => Bridge.sculptTvfKeyFollow(Math.round(norm * 200 - 100))
                }

                SpSlider {
                    ctlKey: "tone.tvf_env_depth"
                    Layout.fillWidth: true
                    label: "ENV DEPTH"
                    valueText: (Bridge.tvfEnvDepth >= 0 ? "+" : "") + Bridge.tvfEnvDepth
                    norm: (Bridge.tvfEnvDepth + 63) / 126.0
                    bipolar: true
                    onMoved: (norm) => Bridge.sculptTvfEnvDepth(Math.round(norm * 126 - 63))
                }

                SpSlider {
                    Layout.fillWidth: true
                    label: "VELO SENS"
                    valueText: Bridge.tvfVeloSens.toString()
                    norm: Bridge.tvfVeloSens / 127.0
                    onMoved: (norm) => Bridge.sculptTvfVeloSens(Math.round(norm * 127))
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.borderCard
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: ScaleMetrics.dp(4)
                    Text {
                        text: "TVF ENVELOPE"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Theme.textDim
                    }
                    Item { Layout.fillWidth: true }
                    EnvModeChip {
                        objectName: "sculptTvfEnvMode"
                        env: "TVF"
                    }
                    EnvThumb {
                        objectName: "sculptTvfEnvThumb"
                        env: "TVF"
                    }
                }

                SpSlider {
                    ctlKey: "tone.tvf_attack"
                    Layout.fillWidth: true
                    label: "ATTACK (A)"
                    valueText: Bridge.tvfAttack.toString()
                    norm: Bridge.tvfAttack / 127.0
                    onMoved: (norm) => Bridge.sculptTvfAttack(Math.round(norm * 127))
                }

                SpSlider {
                    ctlKey: "tone.tvf_decay"
                    Layout.fillWidth: true
                    label: "DECAY (D)"
                    valueText: Bridge.tvfDecay.toString()
                    norm: Bridge.tvfDecay / 127.0
                    onMoved: (norm) => Bridge.sculptTvfDecay(Math.round(norm * 127))
                }

                SpSlider {
                    ctlKey: "tone.tvf_sustain"
                    Layout.fillWidth: true
                    label: "SUSTAIN (S)"
                    valueText: Bridge.tvfSustain.toString()
                    norm: Bridge.tvfSustain / 127.0
                    onMoved: (norm) => Bridge.sculptTvfSustain(Math.round(norm * 127))
                }

                SpSlider {
                    ctlKey: "tone.tvf_release"
                    Layout.fillWidth: true
                    label: "RELEASE (R)"
                    valueText: Bridge.tvfRelease.toString()
                    norm: Bridge.tvfRelease / 127.0
                    onMoved: (norm) => Bridge.sculptTvfRelease(Math.round(norm * 127))
                }

                Item { Layout.fillHeight: true }
            }

            // -----------------------------------------------------------------
            // TAB 1: TVA AMPLIFIER & ENVELOPE
            // -----------------------------------------------------------------
            ColumnLayout {
                visible: root.activeTab === 1
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(8)
                spacing: ScaleMetrics.dp(4)

                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: "TVA AMPLIFIER & ENVELOPE"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(10)
                        color: Theme.textPrimary
                    }
                    Item { Layout.fillWidth: true }
                }

                SpSlider {
                    ctlKey: "common.level"
                    Layout.fillWidth: true
                    label: "LEVEL"
                    valueText: Bridge.masterLevel.toString()
                    norm: Bridge.masterLevel / 127.0
                    onMoved: (norm) => Bridge.setMasterLevel(Math.round(norm * 127))
                }

                SpSlider {
                    ctlKey: "tone.tva_pan"
                    Layout.fillWidth: true
                    label: "PAN"
                    valueText: Bridge.tvaPan === 0 ? "CENTER" : (Bridge.tvaPan < 0 ? ("L" + Math.abs(Bridge.tvaPan)) : ("R" + Bridge.tvaPan))
                    norm: (Bridge.tvaPan + 64) / 127.0
                    bipolar: true
                    onMoved: (norm) => Bridge.sculptTvaPan(Math.round(norm * 127 - 64))
                }

                SpSlider {
                    Layout.fillWidth: true
                    label: "VELO SENS"
                    valueText: Bridge.tvaVeloSens.toString()
                    norm: Bridge.tvaVeloSens / 127.0
                    onMoved: (norm) => Bridge.sculptTvaVeloSens(Math.round(norm * 127))
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.borderCard
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: ScaleMetrics.dp(4)
                    Text {
                        text: "TVA ENVELOPE"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Theme.textDim
                    }
                    Item { Layout.fillWidth: true }
                    EnvModeChip {
                        objectName: "sculptTvaEnvMode"
                        env: "TVA"
                    }
                    EnvThumb {
                        objectName: "sculptTvaEnvThumb"
                        env: "TVA"
                    }
                }

                SpSlider {
                    ctlKey: "tone.tva_attack"
                    Layout.fillWidth: true
                    label: "ATTACK (A)"
                    valueText: Bridge.masterAttack.toString()
                    norm: (Bridge.masterAttack - 1) / 126.0
                    onMoved: (norm) => Bridge.sculptTvaAttack(Math.round(1 + norm * 126))
                }

                SpSlider {
                    ctlKey: "tone.tva_decay"
                    Layout.fillWidth: true
                    label: "DECAY (D)"
                    valueText: Bridge.tvaDecay.toString()
                    norm: Bridge.tvaDecay / 127.0
                    onMoved: (norm) => Bridge.sculptTvaDecay(Math.round(norm * 127))
                }

                SpSlider {
                    ctlKey: "tone.tva_sustain"
                    Layout.fillWidth: true
                    label: "SUSTAIN (S)"
                    valueText: Bridge.tvaSustain.toString()
                    norm: Bridge.tvaSustain / 127.0
                    onMoved: (norm) => Bridge.sculptTvaSustain(Math.round(norm * 127))
                }

                SpSlider {
                    ctlKey: "tone.tva_release"
                    Layout.fillWidth: true
                    label: "RELEASE (R)"
                    valueText: Bridge.masterRelease.toString()
                    norm: (Bridge.masterRelease - 1) / 126.0
                    onMoved: (norm) => Bridge.sculptTvaRelease(Math.round(1 + norm * 126))
                }

                Item { Layout.fillHeight: true }
            }

            // -----------------------------------------------------------------
            // TAB 2: LFO 1 & 2 MODULATOR
            // -----------------------------------------------------------------
            ColumnLayout {
                visible: root.activeTab === 2
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(8)
                spacing: ScaleMetrics.dp(4)

                // Header with LFO 1 / LFO 2 Subtabs
                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: "LFO MODULATOR"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(10)
                        color: Theme.textPrimary
                    }
                    Item { Layout.fillWidth: true }

                    Row {
                        spacing: 3
                        SpButton {
                            implicitWidth: ScaleMetrics.dp(45)
                            implicitHeight: ScaleMetrics.dp(22)
                            text: "LFO 1"
                            fontSize: 8
                            checked: root.activeLfoTab === 1
                            onClicked: root.activeLfoTab = 1
                        }
                        SpButton {
                            implicitWidth: ScaleMetrics.dp(45)
                            implicitHeight: ScaleMetrics.dp(22)
                            text: "LFO 2"
                            fontSize: 8
                            checked: root.activeLfoTab === 2
                            onClicked: root.activeLfoTab = 2
                        }
                    }
                }

                // 8 Waveform Grid
                GridLayout {
                    Layout.fillWidth: true
                    columns: 4
                    rowSpacing: 2; columnSpacing: 2
                    Repeater {
                        model: ["TRI", "SIN", "SAW", "SQR", "TRP", "S&H", "RND", "CHS"]
                        delegate: SpButton {
                            Layout.fillWidth: true
                            implicitHeight: ScaleMetrics.dp(20)
                            text: modelData
                            fontSize: 8
                            checked: root.lfoData.wave === modelData
                            onClicked: Bridge.sculptLfoParam(root.activeLfoTab, "wave", modelData)
                        }
                    }
                }

                SpSlider {
                    ctlKey: "tone.lfo" + root.activeLfoTab + "_rate"
                    Layout.fillWidth: true
                    label: "RATE"
                    valueText: root.lfoData.rate.toString()
                    norm: root.lfoData.rate / 127.0
                    onMoved: (norm) => Bridge.sculptLfoParam(root.activeLfoTab, "rate", Math.round(norm * 127))
                }

                SpSlider {
                    ctlKey: "tone.lfo" + root.activeLfoTab + "_pitch_depth"
                    Layout.fillWidth: true
                    label: "PITCH DEPTH"
                    valueText: (root.lfoData.pitchDepth >= 0 ? "+" : "") + root.lfoData.pitchDepth
                    norm: (root.lfoData.pitchDepth + 63) / 126.0
                    bipolar: true
                    onMoved: (norm) => Bridge.sculptLfoParam(root.activeLfoTab, "pitch_depth", Math.round(norm * 126 - 63))
                }

                SpSlider {
                    ctlKey: "tone.lfo" + root.activeLfoTab + "_tvf_depth"
                    Layout.fillWidth: true
                    label: "FILTER DEPTH"
                    valueText: (root.lfoData.tvfDepth >= 0 ? "+" : "") + root.lfoData.tvfDepth
                    norm: (root.lfoData.tvfDepth + 63) / 126.0
                    bipolar: true
                    onMoved: (norm) => Bridge.sculptLfoParam(root.activeLfoTab, "tvf_depth", Math.round(norm * 126 - 63))
                }

                SpSlider {
                    ctlKey: "tone.lfo" + root.activeLfoTab + "_tva_depth"
                    Layout.fillWidth: true
                    label: "AMP DEPTH"
                    valueText: (root.lfoData.tvaDepth >= 0 ? "+" : "") + root.lfoData.tvaDepth
                    norm: (root.lfoData.tvaDepth + 63) / 126.0
                    bipolar: true
                    onMoved: (norm) => Bridge.sculptLfoParam(root.activeLfoTab, "tva_depth", Math.round(norm * 126 - 63))
                }

                SpSlider {
                    ctlKey: "tone.lfo" + root.activeLfoTab + "_pan_depth"
                    Layout.fillWidth: true
                    label: "PAN DEPTH"
                    valueText: (root.lfoData.panDepth >= 0 ? "+" : "") + root.lfoData.panDepth
                    norm: (root.lfoData.panDepth + 63) / 126.0
                    bipolar: true
                    onMoved: (norm) => Bridge.sculptLfoParam(root.activeLfoTab, "pan_depth", Math.round(norm * 126 - 63))
                }

                SpSlider {
                    Layout.fillWidth: true
                    label: "DELAY TIME"
                    valueText: root.lfoData.delayTime.toString()
                    norm: root.lfoData.delayTime / 127.0
                    onMoved: (norm) => Bridge.sculptLfoParam(root.activeLfoTab, "delay_time", Math.round(norm * 127))
                }

                // Fade Mode Chips
                RowLayout {
                    Layout.fillWidth: true
                    spacing: ScaleMetrics.dp(2)
                    Repeater {
                        model: ["ON-IN", "ON-OUT", "OFF-IN", "OFF-OUT"]
                        delegate: SpButton {
                            Layout.fillWidth: true
                            implicitHeight: ScaleMetrics.dp(18)
                            text: modelData
                            fontSize: 8
                            checked: root.lfoData.fadeMode === modelData
                            onClicked: Bridge.sculptLfoParam(root.activeLfoTab, "fade_mode", modelData)
                        }
                    }
                }

                SpSlider {
                    Layout.fillWidth: true
                    label: "FADE TIME"
                    valueText: root.lfoData.fadeTime.toString()
                    norm: root.lfoData.fadeTime / 127.0
                    onMoved: (norm) => Bridge.sculptLfoParam(root.activeLfoTab, "fade_time", Math.round(norm * 127))
                }

                Item { Layout.fillHeight: true }
            }

            // -----------------------------------------------------------------
            // TAB 3: PITCH TUNING & PORTAMENTO
            // -----------------------------------------------------------------
            ColumnLayout {
                visible: root.activeTab === 3
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(8)
                spacing: ScaleMetrics.dp(5)

                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: "PITCH & PORTAMENTO"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(10)
                        color: Theme.textPrimary
                    }
                    Item { Layout.fillWidth: true }
                }

                Text {
                    text: "MASTER TUNING"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: Theme.textDim
                }

                SpSlider {
                    ctlKey: "tone.pitch_coarse"
                    Layout.fillWidth: true
                    label: "COARSE TUNE"
                    valueText: (Bridge.pitchCoarse >= 0 ? "+" : "") + Bridge.pitchCoarse + " st"
                    norm: (Bridge.pitchCoarse + 24) / 48.0
                    bipolar: true
                    onMoved: (norm) => Bridge.sculptPitchCoarse(Math.round(norm * 48 - 24))
                }

                // Master fine tune: moves all tones together, their detune kept
                SpSlider {
                    ctlKey: "detune.master"
                    Layout.fillWidth: true
                    label: "FINE TUNE"
                    valueText: (Bridge.masterFine >= 0 ? "+" : "") + Bridge.masterFine + " c"
                    norm: (Bridge.masterFine + 50) / 100.0
                    bipolar: true
                    onMoved: (norm) => Bridge.sculptPitchFine(Math.round(norm * 100 - 50))
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.borderCard
                }

                // Pitch Envelope quick access: depth fader + curve thumbnail
                RowLayout {
                    Layout.fillWidth: true
                    spacing: ScaleMetrics.dp(4)
                    Text {
                        text: "PITCH ENVELOPE"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Theme.textDim
                    }
                    Item { Layout.fillWidth: true }
                    EnvModeChip {
                        objectName: "sculptPitchEnvMode"
                        env: "PITCH"
                    }
                    EnvThumb {
                        objectName: "sculptPitchEnvThumb"
                        env: "PITCH"
                    }
                }

                SpSlider {
                    ctlKey: "tone.pitch_env_depth"
                    Layout.fillWidth: true
                    label: "ENV DEPTH"
                    valueText: (Bridge.pitchEnvDepth >= 0 ? "+" : "") + Bridge.pitchEnvDepth + " st"
                    norm: (Bridge.pitchEnvDepth + 12) / 24.0
                    bipolar: true
                    onMoved: (norm) => Bridge.setPitchEnvParam("depth", Math.round(norm * 24 - 12))
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.borderCard
                }

                Text {
                    text: "PORTAMENTO / GLIDE"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: Theme.textDim
                }

                // Portamento and Legato Toggles
                RowLayout {
                    Layout.fillWidth: true
                    spacing: ScaleMetrics.dp(6)

                    Rectangle {
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(26)
                        radius: ScaleMetrics.dp(4)
                        color: Bridge.portamentoSwitch ? Theme.tint(Theme.pageAccent) : Theme.bgControl
                        border.color: Bridge.portamentoSwitch ? Theme.pageAccent : Theme.borderCard
                        border.width: 1

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: 4
                            Rectangle {
                                width: 5; height: 5; radius: 2.5
                                color: Bridge.portamentoSwitch ? Theme.pageAccent : Theme.textDim
                            }
                            Text {
                                text: Bridge.portamentoSwitch ? "PORTAMENTO: ON" : "PORTAMENTO: OFF"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(7)
                                color: Bridge.portamentoSwitch ? Theme.textPrimary : Theme.textDim
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: Bridge.setPortamentoSwitch(!Bridge.portamentoSwitch)
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(26)
                        radius: ScaleMetrics.dp(4)
                        color: Bridge.legatoSwitch ? Theme.tint(Theme.pageAccent) : Theme.bgControl
                        border.color: Bridge.legatoSwitch ? Theme.pageAccent : Theme.borderCard
                        border.width: 1

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: 4
                            Rectangle {
                                width: 5; height: 5; radius: 2.5
                                color: Bridge.legatoSwitch ? Theme.pageAccent : Theme.textDim
                            }
                            Text {
                                text: Bridge.legatoSwitch ? "LEGATO: ON" : "LEGATO: OFF"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(7)
                                color: Bridge.legatoSwitch ? Theme.textPrimary : Theme.textDim
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: Bridge.setLegatoSwitch(!Bridge.legatoSwitch)
                        }
                    }
                }

                SpSlider {
                    ctlKey: "common.portamento_time"
                    Layout.fillWidth: true
                    label: "PORTAMENTO TIME"
                    valueText: Bridge.portamentoTime.toString()
                    norm: Bridge.portamentoTime / 127.0
                    onMoved: (norm) => Bridge.setPortamentoTime(Math.round(norm * 127))
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.borderCard
                }

                Text {
                    text: "ANALOG FEEL"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: Theme.textDim
                }

                SpSlider {
                    ctlKey: "common.analog_feel"
                    Layout.fillWidth: true
                    label: "1/f MOD DEPTH"
                    valueText: Bridge.analogFeel.toString()
                    norm: Bridge.analogFeel / 127.0
                    accent: Theme.pageAccent
                    onMoved: (norm) => Bridge.setAnalogFeel(Math.round(norm * 127))
                }

                Item { Layout.fillHeight: true }
            }
        }
    }

    // Category Tab Button Component
    component CategoryTabButton: SpButton {
        property string tabTitle: "TAB"
        property bool isSelected: false
        text: tabTitle
        checked: isSelected
        compact: true
        implicitHeight: ScaleMetrics.dp(26)
    }
}
