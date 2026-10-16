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

    property int selectedTone: Bridge.selectedTone
    property int activeLfoTab: 1 // 1 or 2
    property bool lfoWavePickerOpen: false
    readonly property var lfoWaveforms: Bridge.lfoWaveNames

    // Active LFO properties helpers
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
        // 1. TOP HEADER: TITLE + PORTAMENTO + LINK ALL TONES TOGGLE
        // =====================================================================
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(8)

            RowLayout {
                spacing: ScaleMetrics.dp(6)
                Rectangle {
                    width: ScaleMetrics.dp(8)
                    height: ScaleMetrics.dp(8)
                    radius: 4
                    color: Theme.pageAccent
                }
                Text {
                    text: "JUNO PCM SOUND DESIGNER"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(12)
                    font.letterSpacing: 1.2
                    color: Theme.textPrimary
                }

                StructureButton {
                    Layout.leftMargin: ScaleMetrics.dp(6)
                }
            }

            Item { Layout.fillWidth: true }

            // Portamento & Legato Controls
            RowLayout {
                spacing: ScaleMetrics.dp(6)

                // Portamento Switch
                Rectangle {
                    width: ScaleMetrics.dp(110)
                    height: ScaleMetrics.dp(26)
                    radius: ScaleMetrics.dp(4)
                    color: Bridge.portamentoSwitch ? Theme.tint(Theme.pageAccent) : Theme.bgControl
                    border.color: Bridge.portamentoSwitch ? Theme.pageAccent : Theme.borderCard
                    border.width: 1

                    RowLayout {
                        anchors.centerIn: parent
                        spacing: 4
                        Rectangle {
                            width: 6; height: 6; radius: 3
                            color: Bridge.portamentoSwitch ? Theme.pageAccent : Theme.textDim
                        }
                        Text {
                            text: Bridge.portamentoSwitch ? "PORTAMENTO: ON" : "PORTAMENTO: OFF"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: Bridge.portamentoSwitch ? Theme.textPrimary : Theme.textDim
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: Bridge.setPortamentoSwitch(!Bridge.portamentoSwitch)
                    }
                }

                // Legato Switch
                Rectangle {
                    width: ScaleMetrics.dp(90)
                    height: ScaleMetrics.dp(26)
                    radius: ScaleMetrics.dp(4)
                    color: Bridge.legatoSwitch ? Theme.tint(Theme.pageAccent) : Theme.bgControl
                    border.color: Bridge.legatoSwitch ? Theme.pageAccent : Theme.borderCard
                    border.width: 1

                    RowLayout {
                        anchors.centerIn: parent
                        spacing: 4
                        Rectangle {
                            width: 6; height: 6; radius: 3
                            color: Bridge.legatoSwitch ? Theme.pageAccent : Theme.textDim
                        }
                        Text {
                            text: Bridge.legatoSwitch ? "LEGATO: ON" : "LEGATO: OFF"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: Bridge.legatoSwitch ? Theme.textPrimary : Theme.textDim
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: Bridge.setLegatoSwitch(!Bridge.legatoSwitch)
                    }
                }

                // Portamento Time Mini-Slider
                Rectangle {
                    width: ScaleMetrics.dp(95)
                    height: ScaleMetrics.dp(26)
                    radius: ScaleMetrics.dp(4)
                    color: Theme.bgControl
                    border.color: Theme.borderCard
                    border.width: 1

                    Rectangle {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        width: parent.width * (Bridge.portamentoTime / 127.0)
                        radius: ScaleMetrics.dp(4)
                        color: Theme.tint(Theme.pageAccent, 0.3)
                    }

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: ScaleMetrics.dp(4)
                        Text { text: "TIME"; font.bold: true; font.pixelSize: ScaleMetrics.sp(7); color: Theme.textDim }
                        Item { Layout.fillWidth: true }
                        Text {
                            text: Bridge.portamentoTime.toString()
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            font.family: Theme.fontMono
                            color: Theme.textPrimary
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        onPressed: (mouse) => {
                            const norm = Math.max(0.0, Math.min(1.0, mouse.x / width));
                            Bridge.setPortamentoTime(Math.round(norm * 127));
                        }
                        onPositionChanged: (mouse) => {
                            if (pressed) {
                                const norm = Math.max(0.0, Math.min(1.0, mouse.x / width));
                                Bridge.setPortamentoTime(Math.round(norm * 127));
                            }
                        }
                    }
                }
            }

            // ANALOG FEEL Mini-Slider (1/f drift / analog instability)
            Rectangle {
                width: ScaleMetrics.dp(112)
                height: ScaleMetrics.dp(26)
                radius: ScaleMetrics.dp(4)
                color: Theme.bgControl
                border.color: Theme.borderCard
                border.width: 1

                Rectangle {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    width: parent.width * (Bridge.analogFeel / 127.0)
                    radius: ScaleMetrics.dp(4)
                    color: Theme.tint(Theme.pageAccent, 0.3)
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(4)
                    Text { text: "ANALOG FEEL"; font.bold: true; font.pixelSize: ScaleMetrics.sp(7); color: Theme.textSecondary; elide: Text.ElideRight }
                    Item { Layout.fillWidth: true }
                    Text {
                        text: Bridge.analogFeel.toString()
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        font.family: Theme.fontMono
                        color: Theme.textPrimary
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    onPressed: (mouse) => {
                        const norm = Math.max(0.0, Math.min(1.0, mouse.x / width));
                        Bridge.setAnalogFeel(Math.round(norm * 127));
                    }
                    onPositionChanged: (mouse) => {
                        if (pressed) {
                            const norm = Math.max(0.0, Math.min(1.0, mouse.x / width));
                            Bridge.setAnalogFeel(Math.round(norm * 127));
                        }
                    }
                }
            }

            // LINK ALL TONES TOGGLE
            Rectangle {
                width: ScaleMetrics.dp(135)
                height: ScaleMetrics.dp(26)
                radius: ScaleMetrics.dp(4)
                color: Bridge.linkedMode ? Theme.tint(Theme.pageAccent) : Theme.bgControl
                border.color: Bridge.linkedMode ? Theme.pageAccent : Theme.borderCard
                border.width: Bridge.linkedMode ? 2 : 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: ScaleMetrics.dp(4)

                    Rectangle {
                        width: ScaleMetrics.dp(6)
                        height: ScaleMetrics.dp(6)
                        radius: 3
                        color: Bridge.linkedMode ? Theme.pageAccent : Theme.textDim
                    }

                    Text {
                        text: Bridge.linkedMode ? "LINK ALL TONES: ON" : "LINK ALL TONES: OFF"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Bridge.linkedMode ? Theme.textPrimary : Theme.textDim
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: Bridge.setLinkedMode(!Bridge.linkedMode)
                }
            }
        }

        // =====================================================================
        // 2. TONE TABS STRIP (TONE 1 - 4 + LEVEL METERS + MUTES)
        // ONLY PLACE WHERE TONE COLORS ARE APPLIED FOR DISCRIMINATION
        // =====================================================================
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(8)

            Repeater {
                model: 4
                delegate: ToneTabButton {
                    Layout.fillWidth: true
                    toneNumber: modelData + 1
                    isSelected: root.selectedTone === (modelData + 1)
                    toneColor: modelData === 0 ? Theme.tone1 : modelData === 1 ? Theme.tone2 : modelData === 2 ? Theme.tone3 : Theme.tone4
                    toneLevel: modelData === 0 ? Bridge.tone1Level : modelData === 1 ? Bridge.tone2Level : modelData === 2 ? Bridge.tone3Level : Bridge.tone4Level
                    isMuted: modelData === 0 ? Bridge.tone1Muted : modelData === 1 ? Bridge.tone2Muted : modelData === 2 ? Bridge.tone3Muted : Bridge.tone4Muted
                    onSelected: {
                        root.selectedTone = toneNumber;
                        Bridge.setSelectedTone(toneNumber);
                    }
                }
            }
        }

        // =====================================================================
        // 3. MAIN WORKSPACE: 4 NEUTRAL INSTRUMENT PANELS
        // =====================================================================
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: ScaleMetrics.dp(8)

            // -----------------------------------------------------------------
            // PANEL 1: PCM OSCILLATOR / STEREO WAVE ASSIGNMENT (~230dp)
            // -----------------------------------------------------------------
            Rectangle {
                Layout.preferredWidth: ScaleMetrics.dp(230)
                Layout.fillHeight: true
                radius: ScaleMetrics.dp(6)
                color: Theme.bgApp
                border.color: Theme.borderCard
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(8)
                    spacing: ScaleMetrics.dp(5)

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "PCM OSCILLATOR"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(10)
                            color: Theme.textPrimary
                        }
                        Item { Layout.fillWidth: true }
                        // Tone badge
                        Rectangle {
                            height: ScaleMetrics.dp(18)
                            implicitWidth: ScaleMetrics.dp(55)
                            radius: 3
                            color: Theme.bgControl
                            border.color: root.selectedTone === 1 ? Theme.tone1 : root.selectedTone === 2 ? Theme.tone2 : root.selectedTone === 3 ? Theme.tone3 : Theme.tone4
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: "TONE " + root.selectedTone
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(8)
                                color: root.selectedTone === 1 ? Theme.tone1 : root.selectedTone === 2 ? Theme.tone2 : root.selectedTone === 3 ? Theme.tone3 : Theme.tone4
                            }
                        }
                    }

                    // WAVE LEFT
                    WaveCard {
                        Layout.fillWidth: true
                        channelLabel: "WAVE L (LEFT / MONO)"
                        toneIdx: root.selectedTone
                    }

                    // WAVE RIGHT
                    WaveCard {
                        Layout.fillWidth: true
                        channelLabel: "WAVE R (RIGHT / EXP)"
                        toneIdx: root.selectedTone
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
                            text: "PITCH & TUNING"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: Theme.textDim
                        }
                        Item { Layout.fillWidth: true }
                        // Auto Detune: spreads the 4 tones' fine tunes; the
                        // FINE TUNE row below becomes its amount while on
                        SpButton {
                            objectName: "pcmAutoDetune"
                            compact: true
                            implicitHeight: ScaleMetrics.dp(22)
                            fontSize: 8
                            text: "AUTO DETUNE"
                            checked: Bridge.autoDetune
                            onClicked: Bridge.setAutoDetune(!Bridge.autoDetune)
                        }
                    }

                    SpSlider {
                        ctlKey: "tone.pitch_coarse"
                        Layout.fillWidth: true
                        label: "COARSE TUNE"
                        valueText: (Bridge.pitchCoarse >= 0 ? "+" : "") + Bridge.pitchCoarse + " st"
                        norm: (Bridge.pitchCoarse + 24) / 48.0
                        bipolar: true
                        onMoved: (norm) => Bridge.setPitchCoarse(Math.round(norm * 48 - 24))
                    }

                    SpSlider {
                        visible: !Bridge.autoDetune
                        ctlKey: "tone.pitch_fine"
                        Layout.fillWidth: true
                        label: "FINE TUNE"
                        valueText: (Bridge.pitchFine >= 0 ? "+" : "") + Bridge.pitchFine + " c"
                        norm: (Bridge.pitchFine + 50) / 100.0
                        bipolar: true
                        onMoved: (norm) => Bridge.setPitchFine(Math.round(norm * 100 - 50))
                    }

                    SpSlider {
                        visible: Bridge.autoDetune
                        ctlKey: "detune.auto"
                        Layout.fillWidth: true
                        label: "AUTO DETUNE"
                        valueText: Bridge.autoDetuneCents + " c"
                        norm: Bridge.autoDetuneCents / 50.0
                        onMoved: (norm) => Bridge.setAutoDetuneCents(Math.round(norm * 50))
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
                            objectName: "pcmPitchEnvMode"
                            env: "PITCH"
                        }
                        EnvThumb {
                            objectName: "pcmPitchEnvThumb"
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

                    Item { Layout.fillHeight: true }
                }
            }

            // -----------------------------------------------------------------
            // PANEL 2: TVF FILTER & ENVELOPE (~255dp)
            // -----------------------------------------------------------------
            Rectangle {
                Layout.preferredWidth: ScaleMetrics.dp(255)
                Layout.fillHeight: true
                radius: ScaleMetrics.dp(6)
                color: Theme.bgApp
                border.color: Theme.borderCard
                border.width: 1

                ColumnLayout {
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

                    // TVF Type Selector Chips
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
                                onClicked: Bridge.setTvfType(modelData)
                            }
                        }
                    }

                    SpSlider {
                        ctlKey: "tone.tvf_cutoff"
                        Layout.fillWidth: true
                        label: "CUTOFF"
                        valueText: Bridge.masterCutoff.toString()
                        norm: (Bridge.masterCutoff - 1) / 126.0
                        onMoved: (norm) => Bridge.setMasterCutoff(Math.round(1 + norm * 126))
                    }

                    SpSlider {
                        ctlKey: "tone.tvf_resonance"
                        Layout.fillWidth: true
                        label: "RESONANCE"
                        valueText: Bridge.masterReso.toString()
                        norm: (Bridge.masterReso - 1) / 126.0
                        onMoved: (norm) => Bridge.setMasterReso(Math.round(1 + norm * 126))
                    }

                    SpSlider {
                        ctlKey: "tone.tvf_keyfollow"
                        Layout.fillWidth: true
                        label: "KEY FOLLOW"
                        valueText: (Bridge.tvfKeyFollow >= 0 ? "+" : "") + Bridge.tvfKeyFollow + "%"
                        norm: (Bridge.tvfKeyFollow + 100) / 200.0
                        bipolar: true
                        onMoved: (norm) => Bridge.setTvfKeyFollow(Math.round(norm * 200 - 100))
                    }

                    SpSlider {
                        ctlKey: "tone.tvf_env_depth"
                        Layout.fillWidth: true
                        label: "ENV DEPTH"
                        valueText: (Bridge.tvfEnvDepth >= 0 ? "+" : "") + Bridge.tvfEnvDepth
                        norm: (Bridge.tvfEnvDepth + 63) / 126.0
                        bipolar: true
                        onMoved: (norm) => Bridge.setTvfEnvDepth(Math.round(norm * 126 - 63))
                    }

                    SpSlider {
                        Layout.fillWidth: true
                        label: "VELO SENS"
                        valueText: Bridge.tvfVeloSens.toString()
                        norm: Bridge.tvfVeloSens / 127.0
                        onMoved: (norm) => Bridge.setTvfVeloSens(Math.round(norm * 127))
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
                            objectName: "pcmTvfEnvMode"
                            env: "TVF"
                        }
                        EnvThumb {
                            objectName: "pcmTvfEnvThumb"
                            env: "TVF"
                        }
                    }

                    SpSlider {
                        ctlKey: "tone.tvf_attack"
                        Layout.fillWidth: true
                        label: "ATTACK (A)"
                        valueText: Bridge.tvfAttack.toString()
                        norm: Bridge.tvfAttack / 127.0
                        onMoved: (norm) => Bridge.setTvfAttack(Math.round(norm * 127))
                    }

                    SpSlider {
                        ctlKey: "tone.tvf_decay"
                        Layout.fillWidth: true
                        label: "DECAY (D)"
                        valueText: Bridge.tvfDecay.toString()
                        norm: Bridge.tvfDecay / 127.0
                        onMoved: (norm) => Bridge.setTvfDecay(Math.round(norm * 127))
                    }

                    SpSlider {
                        ctlKey: "tone.tvf_sustain"
                        Layout.fillWidth: true
                        label: "SUSTAIN (S)"
                        valueText: Bridge.tvfSustain.toString()
                        norm: Bridge.tvfSustain / 127.0
                        onMoved: (norm) => Bridge.setTvfSustain(Math.round(norm * 127))
                    }

                    SpSlider {
                        ctlKey: "tone.tvf_release"
                        Layout.fillWidth: true
                        label: "RELEASE (R)"
                        valueText: Bridge.tvfRelease.toString()
                        norm: Bridge.tvfRelease / 127.0
                        onMoved: (norm) => Bridge.setTvfRelease(Math.round(norm * 127))
                    }

                    Item { Layout.fillHeight: true }
                }
            }

            // -----------------------------------------------------------------
            // PANEL 3: TVA AMPLIFIER & ENVELOPE (~245dp)
            // -----------------------------------------------------------------
            Rectangle {
                Layout.preferredWidth: ScaleMetrics.dp(245)
                Layout.fillHeight: true
                radius: ScaleMetrics.dp(6)
                color: Theme.bgApp
                border.color: Theme.borderCard
                border.width: 1

                ColumnLayout {
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
                        ctlKey: "tone.tva_level"
                        Layout.fillWidth: true
                        label: "LEVEL"
                        valueText: Bridge.tvaLevel.toString()
                        norm: Bridge.tvaLevel / 127.0
                        onMoved: (norm) => Bridge.setTvaLevel(Math.round(norm * 127))
                    }

                    SpSlider {
                        ctlKey: "tone.tva_pan"
                        Layout.fillWidth: true
                        label: "PAN"
                        valueText: Bridge.tvaPan === 0 ? "CENTER" : (Bridge.tvaPan < 0 ? ("L" + Math.abs(Bridge.tvaPan)) : ("R" + Bridge.tvaPan))
                        norm: (Bridge.tvaPan + 64) / 127.0
                        bipolar: true
                        onMoved: (norm) => Bridge.setTvaPan(Math.round(norm * 127 - 64))
                    }

                    SpSlider {
                        Layout.fillWidth: true
                        label: "VELO SENS"
                        valueText: Bridge.tvaVeloSens.toString()
                        norm: Bridge.tvaVeloSens / 127.0
                        onMoved: (norm) => Bridge.setTvaVeloSens(Math.round(norm * 127))
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
                            objectName: "pcmTvaEnvMode"
                            env: "TVA"
                        }
                        EnvThumb {
                            objectName: "pcmTvaEnvThumb"
                            env: "TVA"
                        }
                    }

                    SpSlider {
                        ctlKey: "tone.tva_attack"
                        Layout.fillWidth: true
                        label: "ATTACK (A)"
                        valueText: Bridge.tvaAttack.toString()
                        norm: Bridge.tvaAttack / 127.0
                        onMoved: (norm) => Bridge.setTvaAttack(Math.round(norm * 127))
                    }

                    SpSlider {
                        ctlKey: "tone.tva_decay"
                        Layout.fillWidth: true
                        label: "DECAY (D)"
                        valueText: Bridge.tvaDecay.toString()
                        norm: Bridge.tvaDecay / 127.0
                        onMoved: (norm) => Bridge.setTvaDecay(Math.round(norm * 127))
                    }

                    SpSlider {
                        ctlKey: "tone.tva_sustain"
                        Layout.fillWidth: true
                        label: "SUSTAIN (S)"
                        valueText: Bridge.tvaSustain.toString()
                        norm: Bridge.tvaSustain / 127.0
                        onMoved: (norm) => Bridge.setTvaSustain(Math.round(norm * 127))
                    }

                    SpSlider {
                        ctlKey: "tone.tva_release"
                        Layout.fillWidth: true
                        label: "RELEASE (R)"
                        valueText: Bridge.tvaRelease.toString()
                        norm: Bridge.tvaRelease / 127.0
                        onMoved: (norm) => Bridge.setTvaRelease(Math.round(norm * 127))
                    }

                    Item { Layout.fillHeight: true }
                }
            }

            // -----------------------------------------------------------------
            // PANEL 4: LFO 1 & 2 MODULATOR (~260dp)
            // -----------------------------------------------------------------
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
                    spacing: ScaleMetrics.dp(4)

                    // Header with LFO 1 / LFO 2 Tabs
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

                    // Interactive Wave Selector: [<] [ WAVE NAME (idx/13) ▼ ] [>]
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: ScaleMetrics.dp(4)

                        // Prev Wave Button
                        SpButton {
                            implicitWidth: ScaleMetrics.dp(28)
                            implicitHeight: ScaleMetrics.dp(24)
                            icon: "left"
                            fontSize: 8
                            onClicked: {
                                let idx = root.lfoWaveforms.indexOf(root.lfoData.wave);
                                if (idx <= 0) idx = root.lfoWaveforms.length - 1;
                                else idx--;
                                Bridge.setLfoParam(root.activeLfoTab, "wave", root.lfoWaveforms[idx]);
                            }
                        }

                        // Current Wave Button (Taps to open Wave Picker Modal)
                        Rectangle {
                            Layout.fillWidth: true
                            height: ScaleMetrics.dp(24)
                            radius: 3
                            color: currentWaveArea.pressed ? Theme.tint(Theme.pageAccent, 0.25) : Theme.bgCardActive
                            border.color: Theme.pageAccent
                            border.width: 1

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: ScaleMetrics.dp(8)
                                anchors.rightMargin: ScaleMetrics.dp(8)

                                Text {
                                    text: "WAVE"
                                    font.bold: true
                                    font.pixelSize: ScaleMetrics.sp(7)
                                    color: Theme.textDim
                                }

                                Item { Layout.fillWidth: true }

                                Text {
                                    text: root.lfoData.wave
                                    font.bold: true
                                    font.pixelSize: ScaleMetrics.sp(9)
                                    color: Theme.pageAccent
                                }

                                Icon {
                                    name: "down"
                                    size: 12
                                    color: Theme.textDim
                                }
                            }

                            MouseArea {
                                id: currentWaveArea
                                anchors.fill: parent
                                onClicked: root.lfoWavePickerOpen = !root.lfoWavePickerOpen
                            }
                        }

                        // Next Wave Button
                        SpButton {
                            implicitWidth: ScaleMetrics.dp(28)
                            implicitHeight: ScaleMetrics.dp(24)
                            icon: "right"
                            fontSize: 8
                            onClicked: {
                                let idx = root.lfoWaveforms.indexOf(root.lfoData.wave);
                                if (idx < 0 || idx >= root.lfoWaveforms.length - 1) idx = 0;
                                else idx++;
                                Bridge.setLfoParam(root.activeLfoTab, "wave", root.lfoWaveforms[idx]);
                            }
                        }
                    }

                    SpSlider {
                        ctlKey: "tone.lfo" + root.activeLfoTab + "_rate"
                        Layout.fillWidth: true
                        label: "RATE"
                        valueText: root.lfoData.rate.toString()
                        norm: root.lfoData.rate / 127.0
                        onMoved: (norm) => Bridge.setLfoParam(root.activeLfoTab, "rate", Math.round(norm * 127))
                    }

                    SpSlider {
                        ctlKey: "tone.lfo" + root.activeLfoTab + "_pitch_depth"
                        Layout.fillWidth: true
                        label: "PITCH DEPTH"
                        valueText: (root.lfoData.pitchDepth >= 0 ? "+" : "") + root.lfoData.pitchDepth
                        norm: (root.lfoData.pitchDepth + 63) / 126.0
                        bipolar: true
                        onMoved: (norm) => Bridge.setLfoParam(root.activeLfoTab, "pitch_depth", Math.round(norm * 126 - 63))
                    }

                    SpSlider {
                        ctlKey: "tone.lfo" + root.activeLfoTab + "_tvf_depth"
                        Layout.fillWidth: true
                        label: "FILTER DEPTH"
                        valueText: (root.lfoData.tvfDepth >= 0 ? "+" : "") + root.lfoData.tvfDepth
                        norm: (root.lfoData.tvfDepth + 63) / 126.0
                        bipolar: true
                        onMoved: (norm) => Bridge.setLfoParam(root.activeLfoTab, "tvf_depth", Math.round(norm * 126 - 63))
                    }

                    SpSlider {
                        ctlKey: "tone.lfo" + root.activeLfoTab + "_tva_depth"
                        Layout.fillWidth: true
                        label: "AMP DEPTH"
                        valueText: (root.lfoData.tvaDepth >= 0 ? "+" : "") + root.lfoData.tvaDepth
                        norm: (root.lfoData.tvaDepth + 63) / 126.0
                        bipolar: true
                        onMoved: (norm) => Bridge.setLfoParam(root.activeLfoTab, "tva_depth", Math.round(norm * 126 - 63))
                    }

                    SpSlider {
                        ctlKey: "tone.lfo" + root.activeLfoTab + "_pan_depth"
                        Layout.fillWidth: true
                        label: "PAN DEPTH"
                        valueText: (root.lfoData.panDepth >= 0 ? "+" : "") + root.lfoData.panDepth
                        norm: (root.lfoData.panDepth + 63) / 126.0
                        bipolar: true
                        onMoved: (norm) => Bridge.setLfoParam(root.activeLfoTab, "pan_depth", Math.round(norm * 126 - 63))
                    }

                    SpSlider {
                        Layout.fillWidth: true
                        label: "DELAY TIME"
                        valueText: root.lfoData.delayTime.toString()
                        norm: root.lfoData.delayTime / 127.0
                        onMoved: (norm) => Bridge.setLfoParam(root.activeLfoTab, "delay_time", Math.round(norm * 127))
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
                                onClicked: Bridge.setLfoParam(root.activeLfoTab, "fade_mode", modelData)
                            }
                        }
                    }

                    SpSlider {
                        Layout.fillWidth: true
                        label: "FADE TIME"
                        valueText: root.lfoData.fadeTime.toString()
                        norm: root.lfoData.fadeTime / 127.0
                        onMoved: (norm) => Bridge.setLfoParam(root.activeLfoTab, "fade_time", Math.round(norm * 127))
                    }

                    Item { Layout.fillHeight: true }
                }
            }
        }
    }

    // =========================================================================
    // SUB-COMPONENTS
    // =========================================================================

    // Tone Tab Button Component (Mute, VU Meter, Wave readout, selection)
    component ToneTabButton: Rectangle {
        id: tb
        property int toneNumber: 1
        property bool isSelected: false
        property color toneColor: Theme.tone1
        property int toneLevel: 100
        property bool isMuted: false
        signal selected()

        height: ScaleMetrics.dp(38)
        radius: ScaleMetrics.dp(5)
        color: isSelected ? Theme.bgCardActive : Theme.bgControl
        border.color: isSelected ? toneColor : Theme.borderCard
        border.width: isSelected ? 2 : 1

        // Base mouse area to select tab on clicking background
        MouseArea {
            anchors.fill: parent
            onClicked: tb.selected()
        }

        RowLayout {
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(5)
            spacing: ScaleMetrics.dp(6)

            // Mute / On Button
            SpButton {
                z: 2
                implicitWidth: ScaleMetrics.dp(34)
                implicitHeight: ScaleMetrics.dp(26)
                text: tb.isMuted ? "MUTE" : "ON"
                fontSize: 8
                variant: "outline"
                accent: tb.isMuted ? Theme.recording : (tb.toneLevel > 0 ? tb.toneColor : Theme.textDim)
                checked: tb.isMuted
                onClicked: {
                    tb.selected();
                    Bridge.toggleToneMute(tb.toneNumber);
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2

                RowLayout {
                    Text {
                        text: "TONE " + tb.toneNumber
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(10)
                        color: tb.isSelected ? tb.toneColor : Theme.textPrimary
                    }
                    Item { Layout.fillWidth: true }
                    Text {
                        text: tb.isMuted ? "OFF" : ("LVL " + tb.toneLevel)
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        font.family: Theme.fontMono
                        color: tb.isMuted ? Theme.textDim : tb.toneColor
                    }
                }

                // Interactive horizontal level bar
                Rectangle {
                    id: levelTrack
                    z: 2
                    Layout.fillWidth: true
                    height: ScaleMetrics.dp(7)
                    radius: 3
                    color: Theme.bgRaised
                    clip: true

                    Rectangle {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        width: parent.width * (tb.isMuted ? 0 : (tb.toneLevel / 127.0))
                        color: tb.toneColor
                    }

                    MouseArea {
                        anchors.fill: parent
                        preventStealing: true
                        property real pressX: 0
                        property bool editing: false

                        function updateLevel(mouse) {
                            tb.selected();
                            let norm = Math.max(0.0, Math.min(1.0, mouse.x / levelTrack.width));
                            let newLvl = Math.round(norm * 127);
                            Bridge.setToneLevel(tb.toneNumber, newLvl);
                        }

                        onPressed: (mouse) => {
                            pressX = mouse.x;
                            editing = false;
                            tb.selected();
                        }
                        onPositionChanged: (mouse) => {
                            if (pressed) {
                                if (!editing && Math.abs(mouse.x - pressX) > ScaleMetrics.dp(5))
                                    editing = true;
                                if (editing) updateLevel(mouse);
                            }
                        }
                    }
                }
            }
        }
    }

    // Wave Card Component (Wave L / Wave R)
    component WaveCard: Rectangle {
        id: wc
        property string channelLabel: "WAVE L"
        property int toneIdx: 1
        property var waveData: (Bridge.toneWaveData && Bridge.toneWaveData.length >= toneIdx) ? Bridge.toneWaveData[toneIdx - 1] : null

        height: ScaleMetrics.dp(58)
        radius: ScaleMetrics.dp(4)
        color: Theme.bgControl
        border.color: Theme.borderCard
        border.width: 1

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(5)
            spacing: 2

            Text {
                text: wc.channelLabel
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(8)
                color: Theme.textDim
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: ScaleMetrics.dp(4)

                CategoryGlyph {
                    Layout.preferredWidth: ScaleMetrics.dp(20)
                    Layout.preferredHeight: ScaleMetrics.dp(14)
                    toneIndex: wc.toneIdx - 1
                    category: wc.waveData ? wc.waveData.category : "synth_wave"
                    isSingleCycle: wc.waveData ? wc.waveData.is_single_cycle : true
                    samples64: wc.waveData ? wc.waveData.samples_64 : null
                    color: Theme.pageAccent
                }

                Text {
                    Layout.fillWidth: true
                    text: wc.waveData ? wc.waveData.name : "Juno Saw HD"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: Theme.textPrimary
                    elide: Text.ElideRight
                }

                SpButton {
                    implicitWidth: ScaleMetrics.dp(48)
                    implicitHeight: ScaleMetrics.dp(22)
                    text: "BROWSE"
                    fontSize: 8
                    variant: "outline"
                    onClicked: Bridge.openWaveBrowser(wc.toneIdx)
                }
            }
        }
    }

    // LFO Wave Picker Overlay Modal
    Rectangle {
        id: wavePickerModal
        anchors.fill: parent
        z: 999
        color: Theme.scrim
        visible: root.lfoWavePickerOpen

        MouseArea {
            anchors.fill: parent
            onClicked: root.lfoWavePickerOpen = false
        }

        Rectangle {
            anchors.centerIn: parent
            width: Math.min(parent.width - ScaleMetrics.dp(40), ScaleMetrics.dp(380))
            height: ScaleMetrics.dp(250)
            radius: ScaleMetrics.dp(8)
            color: Theme.bgControl
            border.color: Theme.pageAccent
            border.width: 1

            MouseArea {
                anchors.fill: parent
                // Prevent dismissing modal on clicking inside the card
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(12)
                spacing: ScaleMetrics.dp(10)

                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: "SELECT LFO " + root.activeLfoTab + " WAVEFORM"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(10)
                        color: Theme.textPrimary
                    }
                    Item { Layout.fillWidth: true }
                    SpButton {
                        implicitWidth: ScaleMetrics.dp(24)
                        implicitHeight: ScaleMetrics.dp(24)
                        icon: "close"
                        fontSize: 10
                        onClicked: root.lfoWavePickerOpen = false
                    }
                }

                GridLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    columns: 4
                    rowSpacing: ScaleMetrics.dp(6)
                    columnSpacing: ScaleMetrics.dp(6)

                    Repeater {
                        model: root.lfoWaveforms
                        delegate: SpButton {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            text: modelData
                            checked: root.lfoData.wave === modelData
                            onClicked: {
                                Bridge.setLfoParam(root.activeLfoTab, "wave", modelData);
                                root.lfoWavePickerOpen = false;
                            }
                        }
                    }
                }
            }
        }
    }
}
