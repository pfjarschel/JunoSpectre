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
    readonly property var lfoData: activeLfoTab === 1 ? {
        rate: Bridge.lfo1Rate,
        wave: Bridge.lfo1Wave,
        pitchDepth: Bridge.lfo1PitchDepth,
        tvfDepth: Bridge.lfo1TvfDepth,
        tvaDepth: Bridge.lfo1TvaDepth,
        panDepth: Bridge.lfo1PanDepth,
        delayTime: Bridge.lfo1DelayTime,
        fadeMode: Bridge.lfo1FadeMode,
        fadeTime: Bridge.lfo1FadeTime,
        sync: Bridge.lfo1Sync
    } : {
        rate: Bridge.lfo2Rate,
        wave: Bridge.lfo2Wave,
        pitchDepth: Bridge.lfo2PitchDepth,
        tvfDepth: Bridge.lfo2TvfDepth,
        tvaDepth: Bridge.lfo2TvaDepth,
        panDepth: Bridge.lfo2PanDepth,
        delayTime: Bridge.lfo2DelayTime,
        fadeMode: Bridge.lfo2FadeMode,
        fadeTime: Bridge.lfo2FadeTime,
        sync: Bridge.lfo2Sync
    }

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

                TouchFader {
                    ctlKey: "tone.tvf_cutoff"
                    Layout.fillWidth: true
                    label: "CUTOFF"
                    valText: Bridge.masterCutoff.toString()
                    normVal: (Bridge.masterCutoff - 1) / 126.0
                    onMoved: (norm) => Bridge.sculptCutoff(Math.round(1 + norm * 126))
                }

                TouchFader {
                    ctlKey: "tone.tvf_resonance"
                    Layout.fillWidth: true
                    label: "RESONANCE"
                    valText: Bridge.masterReso.toString()
                    normVal: (Bridge.masterReso - 1) / 126.0
                    onMoved: (norm) => Bridge.sculptReso(Math.round(1 + norm * 126))
                }

                TouchFader {
                    ctlKey: "tone.tvf_keyfollow"
                    Layout.fillWidth: true
                    label: "KEY FOLLOW"
                    valText: (Bridge.tvfKeyFollow >= 0 ? "+" : "") + Bridge.tvfKeyFollow + "%"
                    normVal: (Bridge.tvfKeyFollow + 100) / 200.0
                    isBipolar: true
                    onMoved: (norm) => Bridge.sculptTvfKeyFollow(Math.round(norm * 200 - 100))
                }

                TouchFader {
                    ctlKey: "tone.tvf_env_depth"
                    Layout.fillWidth: true
                    label: "ENV DEPTH"
                    valText: (Bridge.tvfEnvDepth >= 0 ? "+" : "") + Bridge.tvfEnvDepth
                    normVal: (Bridge.tvfEnvDepth + 63) / 126.0
                    isBipolar: true
                    onMoved: (norm) => Bridge.sculptTvfEnvDepth(Math.round(norm * 126 - 63))
                }

                TouchFader {
                    Layout.fillWidth: true
                    label: "VELO SENS"
                    valText: Bridge.tvfVeloSens.toString()
                    normVal: Bridge.tvfVeloSens / 127.0
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

                TouchFader {
                    ctlKey: "tone.tvf_attack"
                    Layout.fillWidth: true
                    label: "ATTACK (A)"
                    valText: Bridge.tvfAttack.toString()
                    normVal: Bridge.tvfAttack / 127.0
                    onMoved: (norm) => Bridge.sculptTvfAttack(Math.round(norm * 127))
                }

                TouchFader {
                    ctlKey: "tone.tvf_decay"
                    Layout.fillWidth: true
                    label: "DECAY (D)"
                    valText: Bridge.tvfDecay.toString()
                    normVal: Bridge.tvfDecay / 127.0
                    onMoved: (norm) => Bridge.sculptTvfDecay(Math.round(norm * 127))
                }

                TouchFader {
                    ctlKey: "tone.tvf_sustain"
                    Layout.fillWidth: true
                    label: "SUSTAIN (S)"
                    valText: Bridge.tvfSustain.toString()
                    normVal: Bridge.tvfSustain / 127.0
                    onMoved: (norm) => Bridge.sculptTvfSustain(Math.round(norm * 127))
                }

                TouchFader {
                    ctlKey: "tone.tvf_release"
                    Layout.fillWidth: true
                    label: "RELEASE (R)"
                    valText: Bridge.tvfRelease.toString()
                    normVal: Bridge.tvfRelease / 127.0
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

                TouchFader {
                    ctlKey: "common.level"
                    Layout.fillWidth: true
                    label: "LEVEL"
                    valText: Bridge.masterLevel.toString()
                    normVal: Bridge.masterLevel / 127.0
                    onMoved: (norm) => Bridge.setMasterLevel(Math.round(norm * 127))
                }

                TouchFader {
                    ctlKey: "tone.tva_pan"
                    Layout.fillWidth: true
                    label: "PAN"
                    valText: Bridge.tvaPan === 0 ? "CENTER" : (Bridge.tvaPan < 0 ? ("L" + Math.abs(Bridge.tvaPan)) : ("R" + Bridge.tvaPan))
                    normVal: (Bridge.tvaPan + 64) / 127.0
                    isBipolar: true
                    onMoved: (norm) => Bridge.sculptTvaPan(Math.round(norm * 127 - 64))
                }

                TouchFader {
                    Layout.fillWidth: true
                    label: "VELO SENS"
                    valText: Bridge.tvaVeloSens.toString()
                    normVal: Bridge.tvaVeloSens / 127.0
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

                TouchFader {
                    ctlKey: "tone.tva_attack"
                    Layout.fillWidth: true
                    label: "ATTACK (A)"
                    valText: Bridge.masterAttack.toString()
                    normVal: (Bridge.masterAttack - 1) / 126.0
                    onMoved: (norm) => Bridge.sculptTvaAttack(Math.round(1 + norm * 126))
                }

                TouchFader {
                    ctlKey: "tone.tva_decay"
                    Layout.fillWidth: true
                    label: "DECAY (D)"
                    valText: Bridge.tvaDecay.toString()
                    normVal: Bridge.tvaDecay / 127.0
                    onMoved: (norm) => Bridge.sculptTvaDecay(Math.round(norm * 127))
                }

                TouchFader {
                    ctlKey: "tone.tva_sustain"
                    Layout.fillWidth: true
                    label: "SUSTAIN (S)"
                    valText: Bridge.tvaSustain.toString()
                    normVal: Bridge.tvaSustain / 127.0
                    onMoved: (norm) => Bridge.sculptTvaSustain(Math.round(norm * 127))
                }

                TouchFader {
                    ctlKey: "tone.tva_release"
                    Layout.fillWidth: true
                    label: "RELEASE (R)"
                    valText: Bridge.masterRelease.toString()
                    normVal: (Bridge.masterRelease - 1) / 126.0
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

                TouchFader {
                    ctlKey: "tone.lfo" + root.activeLfoTab + "_rate"
                    Layout.fillWidth: true
                    label: "RATE"
                    valText: root.lfoData.rate.toString()
                    normVal: root.lfoData.rate / 127.0
                    onMoved: (norm) => Bridge.sculptLfoParam(root.activeLfoTab, "rate", Math.round(norm * 127))
                }

                TouchFader {
                    ctlKey: "tone.lfo" + root.activeLfoTab + "_pitch_depth"
                    Layout.fillWidth: true
                    label: "PITCH DEPTH"
                    valText: (root.lfoData.pitchDepth >= 0 ? "+" : "") + root.lfoData.pitchDepth
                    normVal: (root.lfoData.pitchDepth + 63) / 126.0
                    isBipolar: true
                    onMoved: (norm) => Bridge.sculptLfoParam(root.activeLfoTab, "pitch_depth", Math.round(norm * 126 - 63))
                }

                TouchFader {
                    ctlKey: "tone.lfo" + root.activeLfoTab + "_tvf_depth"
                    Layout.fillWidth: true
                    label: "FILTER DEPTH"
                    valText: (root.lfoData.tvfDepth >= 0 ? "+" : "") + root.lfoData.tvfDepth
                    normVal: (root.lfoData.tvfDepth + 63) / 126.0
                    isBipolar: true
                    onMoved: (norm) => Bridge.sculptLfoParam(root.activeLfoTab, "tvf_depth", Math.round(norm * 126 - 63))
                }

                TouchFader {
                    ctlKey: "tone.lfo" + root.activeLfoTab + "_tva_depth"
                    Layout.fillWidth: true
                    label: "AMP DEPTH"
                    valText: (root.lfoData.tvaDepth >= 0 ? "+" : "") + root.lfoData.tvaDepth
                    normVal: (root.lfoData.tvaDepth + 63) / 126.0
                    isBipolar: true
                    onMoved: (norm) => Bridge.sculptLfoParam(root.activeLfoTab, "tva_depth", Math.round(norm * 126 - 63))
                }

                TouchFader {
                    ctlKey: "tone.lfo" + root.activeLfoTab + "_pan_depth"
                    Layout.fillWidth: true
                    label: "PAN DEPTH"
                    valText: (root.lfoData.panDepth >= 0 ? "+" : "") + root.lfoData.panDepth
                    normVal: (root.lfoData.panDepth + 63) / 126.0
                    isBipolar: true
                    onMoved: (norm) => Bridge.sculptLfoParam(root.activeLfoTab, "pan_depth", Math.round(norm * 126 - 63))
                }

                TouchFader {
                    Layout.fillWidth: true
                    label: "DELAY TIME"
                    valText: root.lfoData.delayTime.toString()
                    normVal: root.lfoData.delayTime / 127.0
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

                TouchFader {
                    Layout.fillWidth: true
                    label: "FADE TIME"
                    valText: root.lfoData.fadeTime.toString()
                    normVal: root.lfoData.fadeTime / 127.0
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

                TouchFader {
                    ctlKey: "tone.pitch_coarse"
                    Layout.fillWidth: true
                    label: "COARSE TUNE"
                    valText: (Bridge.pitchCoarse >= 0 ? "+" : "") + Bridge.pitchCoarse + " st"
                    normVal: (Bridge.pitchCoarse + 24) / 48.0
                    isBipolar: true
                    onMoved: (norm) => Bridge.sculptPitchCoarse(Math.round(norm * 48 - 24))
                }

                TouchFader {
                    ctlKey: "tone.pitch_fine"
                    Layout.fillWidth: true
                    label: "FINE TUNE"
                    valText: (Bridge.pitchFine >= 0 ? "+" : "") + Bridge.pitchFine + " c"
                    normVal: (Bridge.pitchFine + 50) / 100.0
                    isBipolar: true
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

                TouchFader {
                    ctlKey: "tone.pitch_env_depth"
                    Layout.fillWidth: true
                    label: "ENV DEPTH"
                    valText: (Bridge.pitchEnvDepth >= 0 ? "+" : "") + Bridge.pitchEnvDepth + " st"
                    normVal: (Bridge.pitchEnvDepth + 12) / 24.0
                    isBipolar: true
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

                TouchFader {
                    ctlKey: "common.portamento_time"
                    Layout.fillWidth: true
                    label: "PORTAMENTO TIME"
                    valText: Bridge.portamentoTime.toString()
                    normVal: Bridge.portamentoTime / 127.0
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

                TouchFader {
                    ctlKey: "common.analog_feel"
                    Layout.fillWidth: true
                    label: "1/f MOD DEPTH"
                    valText: Bridge.analogFeel.toString()
                    normVal: Bridge.analogFeel / 127.0
                    barColor: Theme.pageAccent
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
