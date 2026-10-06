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
                color: "#38bdf8"
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
                color: "#1e293b"
                border.color: "#38bdf8"
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: 4
                    Rectangle {
                        width: 5; height: 5; radius: 2.5
                        color: "#38bdf8"
                    }
                    Text {
                        text: "LINKED (4 TONES)"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: "#38bdf8"
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
                        model: ["OFF", "LPF", "BPF", "HPF", "PKG"]
                        delegate: Rectangle {
                            Layout.fillWidth: true
                            height: ScaleMetrics.dp(22)
                            radius: 3
                            color: Bridge.tvfType === modelData ? Theme.bgCardActive : "#10141d"
                            border.color: Bridge.tvfType === modelData ? "#38bdf8" : Theme.borderCard
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: modelData
                                font.bold: Bridge.tvfType === modelData
                                font.pixelSize: ScaleMetrics.sp(7)
                                color: Bridge.tvfType === modelData ? Theme.textPrimary : Theme.textDim
                            }
                            MouseArea {
                                anchors.fill: parent
                                onClicked: Bridge.sculptTvfType(modelData)
                            }
                        }
                    }
                }

                TouchFader {
                    Layout.fillWidth: true
                    label: "CUTOFF"
                    valText: Bridge.masterCutoff.toString()
                    normVal: (Bridge.masterCutoff - 1) / 126.0
                    onMoved: (norm) => Bridge.sculptCutoff(Math.round(1 + norm * 126))
                }

                TouchFader {
                    Layout.fillWidth: true
                    label: "RESONANCE"
                    valText: Bridge.masterReso.toString()
                    normVal: (Bridge.masterReso - 1) / 126.0
                    onMoved: (norm) => Bridge.sculptReso(Math.round(1 + norm * 126))
                }

                TouchFader {
                    Layout.fillWidth: true
                    label: "KEY FOLLOW"
                    valText: (Bridge.tvfKeyFollow >= 0 ? "+" : "") + Bridge.tvfKeyFollow + "%"
                    normVal: (Bridge.tvfKeyFollow + 100) / 200.0
                    isBipolar: true
                    onMoved: (norm) => Bridge.sculptTvfKeyFollow(Math.round(norm * 200 - 100))
                }

                TouchFader {
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
                        text: "TVF ENVELOPE (ADSR)"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Theme.textDim
                    }
                    Item { Layout.fillWidth: true }
                    EnvThumb {
                        objectName: "sculptTvfEnvThumb"
                        env: "TVF"
                    }
                }

                TouchFader {
                    Layout.fillWidth: true
                    label: "ATTACK (A)"
                    valText: Bridge.tvfAttack.toString()
                    normVal: Bridge.tvfAttack / 127.0
                    onMoved: (norm) => Bridge.sculptTvfAttack(Math.round(norm * 127))
                }

                TouchFader {
                    Layout.fillWidth: true
                    label: "DECAY (D)"
                    valText: Bridge.tvfDecay.toString()
                    normVal: Bridge.tvfDecay / 127.0
                    onMoved: (norm) => Bridge.sculptTvfDecay(Math.round(norm * 127))
                }

                TouchFader {
                    Layout.fillWidth: true
                    label: "SUSTAIN (S)"
                    valText: Bridge.tvfSustain.toString()
                    normVal: Bridge.tvfSustain / 127.0
                    onMoved: (norm) => Bridge.sculptTvfSustain(Math.round(norm * 127))
                }

                TouchFader {
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
                    Layout.fillWidth: true
                    label: "LEVEL"
                    valText: Bridge.masterLevel.toString()
                    normVal: Bridge.masterLevel / 127.0
                    onMoved: (norm) => Bridge.setMasterLevel(Math.round(norm * 127))
                }

                TouchFader {
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
                        text: "TVA ENVELOPE (ADSR)"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Theme.textDim
                    }
                    Item { Layout.fillWidth: true }
                    EnvThumb {
                        objectName: "sculptTvaEnvThumb"
                        env: "TVA"
                    }
                }

                TouchFader {
                    Layout.fillWidth: true
                    label: "ATTACK (A)"
                    valText: Bridge.masterAttack.toString()
                    normVal: (Bridge.masterAttack - 1) / 126.0
                    onMoved: (norm) => Bridge.sculptTvaAttack(Math.round(1 + norm * 126))
                }

                TouchFader {
                    Layout.fillWidth: true
                    label: "DECAY (D)"
                    valText: Bridge.tvaDecay.toString()
                    normVal: Bridge.tvaDecay / 127.0
                    onMoved: (norm) => Bridge.sculptTvaDecay(Math.round(norm * 127))
                }

                TouchFader {
                    Layout.fillWidth: true
                    label: "SUSTAIN (S)"
                    valText: Bridge.tvaSustain.toString()
                    normVal: Bridge.tvaSustain / 127.0
                    onMoved: (norm) => Bridge.sculptTvaSustain(Math.round(norm * 127))
                }

                TouchFader {
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
                        Rectangle {
                            width: ScaleMetrics.dp(45)
                            height: ScaleMetrics.dp(22)
                            radius: 3
                            color: root.activeLfoTab === 1 ? Theme.bgCardActive : "#10141d"
                            border.color: root.activeLfoTab === 1 ? "#38bdf8" : Theme.borderCard
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: "LFO 1"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(8)
                                color: root.activeLfoTab === 1 ? Theme.textPrimary : Theme.textDim
                            }
                            MouseArea { anchors.fill: parent; onClicked: root.activeLfoTab = 1 }
                        }
                        Rectangle {
                            width: ScaleMetrics.dp(45)
                            height: ScaleMetrics.dp(22)
                            radius: 3
                            color: root.activeLfoTab === 2 ? Theme.bgCardActive : "#10141d"
                            border.color: root.activeLfoTab === 2 ? "#38bdf8" : Theme.borderCard
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: "LFO 2"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(8)
                                color: root.activeLfoTab === 2 ? Theme.textPrimary : Theme.textDim
                            }
                            MouseArea { anchors.fill: parent; onClicked: root.activeLfoTab = 2 }
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
                        delegate: Rectangle {
                            Layout.fillWidth: true
                            height: ScaleMetrics.dp(20)
                            radius: 3
                            color: root.lfoData.wave === modelData ? Theme.bgCardActive : "#10141d"
                            border.color: root.lfoData.wave === modelData ? "#38bdf8" : Theme.borderCard
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: modelData
                                font.bold: root.lfoData.wave === modelData
                                font.pixelSize: ScaleMetrics.sp(7)
                                color: root.lfoData.wave === modelData ? Theme.textPrimary : Theme.textDim
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: Bridge.sculptLfoParam(root.activeLfoTab, "wave", modelData)
                            }
                        }
                    }
                }

                TouchFader {
                    Layout.fillWidth: true
                    label: "RATE"
                    valText: root.lfoData.rate.toString()
                    normVal: root.lfoData.rate / 127.0
                    onMoved: (norm) => Bridge.sculptLfoParam(root.activeLfoTab, "rate", Math.round(norm * 127))
                }

                TouchFader {
                    Layout.fillWidth: true
                    label: "PITCH DEPTH"
                    valText: (root.lfoData.pitchDepth >= 0 ? "+" : "") + root.lfoData.pitchDepth
                    normVal: (root.lfoData.pitchDepth + 63) / 126.0
                    isBipolar: true
                    onMoved: (norm) => Bridge.sculptLfoParam(root.activeLfoTab, "pitch_depth", Math.round(norm * 126 - 63))
                }

                TouchFader {
                    Layout.fillWidth: true
                    label: "FILTER DEPTH"
                    valText: (root.lfoData.tvfDepth >= 0 ? "+" : "") + root.lfoData.tvfDepth
                    normVal: (root.lfoData.tvfDepth + 63) / 126.0
                    isBipolar: true
                    onMoved: (norm) => Bridge.sculptLfoParam(root.activeLfoTab, "tvf_depth", Math.round(norm * 126 - 63))
                }

                TouchFader {
                    Layout.fillWidth: true
                    label: "AMP DEPTH"
                    valText: (root.lfoData.tvaDepth >= 0 ? "+" : "") + root.lfoData.tvaDepth
                    normVal: (root.lfoData.tvaDepth + 63) / 126.0
                    isBipolar: true
                    onMoved: (norm) => Bridge.sculptLfoParam(root.activeLfoTab, "tva_depth", Math.round(norm * 126 - 63))
                }

                TouchFader {
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
                        delegate: Rectangle {
                            Layout.fillWidth: true
                            height: ScaleMetrics.dp(18)
                            radius: 2
                            color: root.lfoData.fadeMode === modelData ? Theme.bgCardActive : "#10141d"
                            border.color: root.lfoData.fadeMode === modelData ? "#38bdf8" : Theme.borderCard
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: modelData
                                font.bold: root.lfoData.fadeMode === modelData
                                font.pixelSize: ScaleMetrics.sp(6)
                                color: root.lfoData.fadeMode === modelData ? Theme.textPrimary : Theme.textDim
                            }
                            MouseArea {
                                anchors.fill: parent
                                onClicked: Bridge.sculptLfoParam(root.activeLfoTab, "fade_mode", modelData)
                            }
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
                    Layout.fillWidth: true
                    label: "COARSE TUNE"
                    valText: (Bridge.pitchCoarse >= 0 ? "+" : "") + Bridge.pitchCoarse + " st"
                    normVal: (Bridge.pitchCoarse + 24) / 48.0
                    isBipolar: true
                    onMoved: (norm) => Bridge.sculptPitchCoarse(Math.round(norm * 48 - 24))
                }

                TouchFader {
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
                        text: "PITCH ENVELOPE (MSEG)"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Theme.textDim
                    }
                    Item { Layout.fillWidth: true }
                    EnvThumb {
                        objectName: "sculptPitchEnvThumb"
                        env: "PITCH"
                    }
                }

                TouchFader {
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
                        color: Bridge.portamentoSwitch ? Theme.bgCardActive : "#10141d"
                        border.color: Bridge.portamentoSwitch ? "#38bdf8" : Theme.borderCard
                        border.width: 1

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: 4
                            Rectangle {
                                width: 5; height: 5; radius: 2.5
                                color: Bridge.portamentoSwitch ? "#38bdf8" : Theme.textDim
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
                        color: Bridge.legatoSwitch ? Theme.bgCardActive : "#10141d"
                        border.color: Bridge.legatoSwitch ? "#38bdf8" : Theme.borderCard
                        border.width: 1

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: 4
                            Rectangle {
                                width: 5; height: 5; radius: 2.5
                                color: Bridge.legatoSwitch ? "#38bdf8" : Theme.textDim
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
                    Layout.fillWidth: true
                    label: "1/f MOD DEPTH"
                    valText: Bridge.analogFeel.toString()
                    normVal: Bridge.analogFeel / 127.0
                    barColor: "#f59e0b"
                    onMoved: (norm) => Bridge.setAnalogFeel(Math.round(norm * 127))
                }

                Item { Layout.fillHeight: true }
            }
        }
    }

    // Category Tab Button Component
    component CategoryTabButton: Rectangle {
        id: ctb
        property string tabTitle: "TAB"
        property bool isSelected: false
        signal clicked()

        height: ScaleMetrics.dp(26)
        radius: ScaleMetrics.dp(4)
        color: ctb.isSelected ? Theme.bgCardActive : "#10141d"
        border.color: ctb.isSelected ? "#38bdf8" : Theme.borderCard
        border.width: ctb.isSelected ? 1.5 : 1

        RowLayout {
            anchors.centerIn: parent
            spacing: ScaleMetrics.dp(3)

            Rectangle {
                visible: ctb.isSelected
                width: ScaleMetrics.dp(4)
                height: ScaleMetrics.dp(4)
                radius: 2
                color: "#38bdf8"
            }

            Text {
                text: ctb.tabTitle
                font.bold: ctb.isSelected
                font.pixelSize: ScaleMetrics.sp(8)
                color: ctb.isSelected ? Theme.textPrimary : Theme.textDim
            }
        }

        MouseArea {
            anchors.fill: parent
            onClicked: ctb.clicked()
        }
    }
}
