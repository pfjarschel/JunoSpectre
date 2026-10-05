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
    readonly property var lfoWaveforms: [
        "SIN", "TRI", "SAW-UP", "SAW-DW", "SQR", "RND",
        "BEND-UP", "BEND-DW", "TRP", "S&H", "CHS", "VSIN", "STEP"
    ]

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
                    color: Theme.tone1
                }
                Text {
                    text: "JUNO PCM SOUND DESIGNER"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(12)
                    font.letterSpacing: 1.2
                    color: Theme.textPrimary
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
                    color: Bridge.portamentoSwitch ? Theme.bgCardActive : "#10141d"
                    border.color: Bridge.portamentoSwitch ? "#38bdf8" : Theme.borderCard
                    border.width: 1

                    RowLayout {
                        anchors.centerIn: parent
                        spacing: 4
                        Rectangle {
                            width: 6; height: 6; radius: 3
                            color: Bridge.portamentoSwitch ? "#38bdf8" : Theme.textDim
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
                    color: Bridge.legatoSwitch ? Theme.bgCardActive : "#10141d"
                    border.color: Bridge.legatoSwitch ? "#38bdf8" : Theme.borderCard
                    border.width: 1

                    RowLayout {
                        anchors.centerIn: parent
                        spacing: 4
                        Rectangle {
                            width: 6; height: 6; radius: 3
                            color: Bridge.legatoSwitch ? "#38bdf8" : Theme.textDim
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
                    color: "#10141d"
                    border.color: Theme.borderCard
                    border.width: 1

                    Rectangle {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        width: parent.width * (Bridge.portamentoTime / 127.0)
                        radius: ScaleMetrics.dp(4)
                        color: Qt.rgba(0.22, 0.74, 0.97, 0.3)
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

            // LINK ALL TONES TOGGLE
            Rectangle {
                width: ScaleMetrics.dp(135)
                height: ScaleMetrics.dp(26)
                radius: ScaleMetrics.dp(4)
                color: Bridge.linkedMode ? Theme.bgCardActive : "#10141d"
                border.color: Bridge.linkedMode ? "#38bdf8" : Theme.borderCard
                border.width: Bridge.linkedMode ? 2 : 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: ScaleMetrics.dp(4)

                    Rectangle {
                        width: ScaleMetrics.dp(6)
                        height: ScaleMetrics.dp(6)
                        radius: 3
                        color: Bridge.linkedMode ? "#38bdf8" : Theme.textDim
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
                            color: "#10141d"
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

                    Text {
                        text: "PITCH & TUNING"
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
                        onMoved: (norm) => Bridge.setPitchCoarse(Math.round(norm * 48 - 24))
                    }

                    TouchFader {
                        Layout.fillWidth: true
                        label: "FINE TUNE"
                        valText: (Bridge.pitchFine >= 0 ? "+" : "") + Bridge.pitchFine + " c"
                        normVal: (Bridge.pitchFine + 50) / 100.0
                        isBipolar: true
                        onMoved: (norm) => Bridge.setPitchFine(Math.round(norm * 100 - 50))
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
                                    onClicked: Bridge.setTvfType(modelData)
                                }
                            }
                        }
                    }

                    TouchFader {
                        Layout.fillWidth: true
                        label: "CUTOFF"
                        valText: Bridge.masterCutoff.toString()
                        normVal: (Bridge.masterCutoff - 1) / 126.0
                        onMoved: (norm) => Bridge.setMasterCutoff(Math.round(1 + norm * 126))
                    }

                    TouchFader {
                        Layout.fillWidth: true
                        label: "RESONANCE"
                        valText: Bridge.masterReso.toString()
                        normVal: (Bridge.masterReso - 1) / 126.0
                        onMoved: (norm) => Bridge.setMasterReso(Math.round(1 + norm * 126))
                    }

                    TouchFader {
                        Layout.fillWidth: true
                        label: "KEY FOLLOW"
                        valText: (Bridge.tvfKeyFollow >= 0 ? "+" : "") + Bridge.tvfKeyFollow + "%"
                        normVal: (Bridge.tvfKeyFollow + 100) / 200.0
                        isBipolar: true
                        onMoved: (norm) => Bridge.setTvfKeyFollow(Math.round(norm * 200 - 100))
                    }

                    TouchFader {
                        Layout.fillWidth: true
                        label: "ENV DEPTH"
                        valText: (Bridge.tvfEnvDepth >= 0 ? "+" : "") + Bridge.tvfEnvDepth
                        normVal: (Bridge.tvfEnvDepth + 63) / 126.0
                        isBipolar: true
                        onMoved: (norm) => Bridge.setTvfEnvDepth(Math.round(norm * 126 - 63))
                    }

                    TouchFader {
                        Layout.fillWidth: true
                        label: "VELO SENS"
                        valText: Bridge.tvfVeloSens.toString()
                        normVal: Bridge.tvfVeloSens / 127.0
                        onMoved: (norm) => Bridge.setTvfVeloSens(Math.round(norm * 127))
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: Theme.borderCard
                    }

                    Text {
                        text: "TVF ENVELOPE (ADSR)"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Theme.textDim
                    }

                    TouchFader {
                        Layout.fillWidth: true
                        label: "ATTACK (A)"
                        valText: Bridge.tvfAttack.toString()
                        normVal: Bridge.tvfAttack / 127.0
                        onMoved: (norm) => Bridge.setTvfAttack(Math.round(norm * 127))
                    }

                    TouchFader {
                        Layout.fillWidth: true
                        label: "DECAY (D)"
                        valText: Bridge.tvfDecay.toString()
                        normVal: Bridge.tvfDecay / 127.0
                        onMoved: (norm) => Bridge.setTvfDecay(Math.round(norm * 127))
                    }

                    TouchFader {
                        Layout.fillWidth: true
                        label: "SUSTAIN (S)"
                        valText: Bridge.tvfSustain.toString()
                        normVal: Bridge.tvfSustain / 127.0
                        onMoved: (norm) => Bridge.setTvfSustain(Math.round(norm * 127))
                    }

                    TouchFader {
                        Layout.fillWidth: true
                        label: "RELEASE (R)"
                        valText: Bridge.tvfRelease.toString()
                        normVal: Bridge.tvfRelease / 127.0
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

                    TouchFader {
                        Layout.fillWidth: true
                        label: "LEVEL"
                        valText: Bridge.tvaLevel.toString()
                        normVal: Bridge.tvaLevel / 127.0
                        onMoved: (norm) => Bridge.setTvaLevel(Math.round(norm * 127))
                    }

                    TouchFader {
                        Layout.fillWidth: true
                        label: "PAN"
                        valText: Bridge.tvaPan === 0 ? "CENTER" : (Bridge.tvaPan < 0 ? ("L" + Math.abs(Bridge.tvaPan)) : ("R" + Bridge.tvaPan))
                        normVal: (Bridge.tvaPan + 64) / 127.0
                        isBipolar: true
                        onMoved: (norm) => Bridge.setTvaPan(Math.round(norm * 127 - 64))
                    }

                    TouchFader {
                        Layout.fillWidth: true
                        label: "VELO SENS"
                        valText: Bridge.tvaVeloSens.toString()
                        normVal: Bridge.tvaVeloSens / 127.0
                        onMoved: (norm) => Bridge.setTvaVeloSens(Math.round(norm * 127))
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: Theme.borderCard
                    }

                    Text {
                        text: "TVA ENVELOPE (ADSR)"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Theme.textDim
                    }

                    TouchFader {
                        Layout.fillWidth: true
                        label: "ATTACK (A)"
                        valText: Bridge.tvaAttack.toString()
                        normVal: Bridge.tvaAttack / 127.0
                        onMoved: (norm) => Bridge.setTvaAttack(Math.round(norm * 127))
                    }

                    TouchFader {
                        Layout.fillWidth: true
                        label: "DECAY (D)"
                        valText: Bridge.tvaDecay.toString()
                        normVal: Bridge.tvaDecay / 127.0
                        onMoved: (norm) => Bridge.setTvaDecay(Math.round(norm * 127))
                    }

                    TouchFader {
                        Layout.fillWidth: true
                        label: "SUSTAIN (S)"
                        valText: Bridge.tvaSustain.toString()
                        normVal: Bridge.tvaSustain / 127.0
                        onMoved: (norm) => Bridge.setTvaSustain(Math.round(norm * 127))
                    }

                    TouchFader {
                        Layout.fillWidth: true
                        label: "RELEASE (R)"
                        valText: Bridge.tvaRelease.toString()
                        normVal: Bridge.tvaRelease / 127.0
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

                    // Interactive Wave Selector: [<] [ WAVE NAME (idx/13) ▼ ] [>]
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: ScaleMetrics.dp(4)

                        // Prev Wave Button
                        Rectangle {
                            width: ScaleMetrics.dp(28)
                            height: ScaleMetrics.dp(24)
                            radius: 3
                            color: prevWaveArea.pressed ? Theme.bgCardActive : "#10141d"
                            border.color: prevWaveArea.pressed ? "#38bdf8" : Theme.borderCard
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: "◀"
                                font.pixelSize: ScaleMetrics.sp(8)
                                color: Theme.textPrimary
                            }

                            MouseArea {
                                id: prevWaveArea
                                anchors.fill: parent
                                onClicked: {
                                    let idx = root.lfoWaveforms.indexOf(root.lfoData.wave);
                                    if (idx <= 0) idx = root.lfoWaveforms.length - 1;
                                    else idx--;
                                    Bridge.setLfoParam(root.activeLfoTab, "wave", root.lfoWaveforms[idx]);
                                }
                            }
                        }

                        // Current Wave Button (Taps to open Wave Picker Modal)
                        Rectangle {
                            Layout.fillWidth: true
                            height: ScaleMetrics.dp(24)
                            radius: 3
                            color: currentWaveArea.pressed ? "#162032" : Theme.bgCardActive
                            border.color: "#38bdf8"
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
                                    color: "#38bdf8"
                                }

                                Text {
                                    text: "▼"
                                    font.pixelSize: ScaleMetrics.sp(7)
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
                        Rectangle {
                            width: ScaleMetrics.dp(28)
                            height: ScaleMetrics.dp(24)
                            radius: 3
                            color: nextWaveArea.pressed ? Theme.bgCardActive : "#10141d"
                            border.color: nextWaveArea.pressed ? "#38bdf8" : Theme.borderCard
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: "▶"
                                font.pixelSize: ScaleMetrics.sp(8)
                                color: Theme.textPrimary
                            }

                            MouseArea {
                                id: nextWaveArea
                                anchors.fill: parent
                                onClicked: {
                                    let idx = root.lfoWaveforms.indexOf(root.lfoData.wave);
                                    if (idx < 0 || idx >= root.lfoWaveforms.length - 1) idx = 0;
                                    else idx++;
                                    Bridge.setLfoParam(root.activeLfoTab, "wave", root.lfoWaveforms[idx]);
                                }
                            }
                        }
                    }

                    TouchFader {
                        Layout.fillWidth: true
                        label: "RATE"
                        valText: root.lfoData.rate.toString()
                        normVal: root.lfoData.rate / 127.0
                        onMoved: (norm) => Bridge.setLfoParam(root.activeLfoTab, "rate", Math.round(norm * 127))
                    }

                    TouchFader {
                        Layout.fillWidth: true
                        label: "PITCH DEPTH"
                        valText: (root.lfoData.pitchDepth >= 0 ? "+" : "") + root.lfoData.pitchDepth
                        normVal: (root.lfoData.pitchDepth + 63) / 126.0
                        isBipolar: true
                        onMoved: (norm) => Bridge.setLfoParam(root.activeLfoTab, "pitch_depth", Math.round(norm * 126 - 63))
                    }

                    TouchFader {
                        Layout.fillWidth: true
                        label: "FILTER DEPTH"
                        valText: (root.lfoData.tvfDepth >= 0 ? "+" : "") + root.lfoData.tvfDepth
                        normVal: (root.lfoData.tvfDepth + 63) / 126.0
                        isBipolar: true
                        onMoved: (norm) => Bridge.setLfoParam(root.activeLfoTab, "tvf_depth", Math.round(norm * 126 - 63))
                    }

                    TouchFader {
                        Layout.fillWidth: true
                        label: "AMP DEPTH"
                        valText: (root.lfoData.tvaDepth >= 0 ? "+" : "") + root.lfoData.tvaDepth
                        normVal: (root.lfoData.tvaDepth + 63) / 126.0
                        isBipolar: true
                        onMoved: (norm) => Bridge.setLfoParam(root.activeLfoTab, "tva_depth", Math.round(norm * 126 - 63))
                    }

                    TouchFader {
                        Layout.fillWidth: true
                        label: "PAN DEPTH"
                        valText: (root.lfoData.panDepth >= 0 ? "+" : "") + root.lfoData.panDepth
                        normVal: (root.lfoData.panDepth + 63) / 126.0
                        isBipolar: true
                        onMoved: (norm) => Bridge.setLfoParam(root.activeLfoTab, "pan_depth", Math.round(norm * 126 - 63))
                    }

                    TouchFader {
                        Layout.fillWidth: true
                        label: "DELAY TIME"
                        valText: root.lfoData.delayTime.toString()
                        normVal: root.lfoData.delayTime / 127.0
                        onMoved: (norm) => Bridge.setLfoParam(root.activeLfoTab, "delay_time", Math.round(norm * 127))
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
                                    onClicked: Bridge.setLfoParam(root.activeLfoTab, "fade_mode", modelData)
                                }
                            }
                        }
                    }

                    TouchFader {
                        Layout.fillWidth: true
                        label: "FADE TIME"
                        valText: root.lfoData.fadeTime.toString()
                        normVal: root.lfoData.fadeTime / 127.0
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
        color: isSelected ? Theme.bgCardActive : "#0f172a"
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
            Rectangle {
                z: 2
                width: ScaleMetrics.dp(34)
                height: ScaleMetrics.dp(26)
                radius: ScaleMetrics.dp(4)
                color: tb.isMuted ? Theme.recording : (tb.toneLevel > 0 ? Theme.bgSurface : "#10141d")
                border.color: tb.isMuted ? Theme.recording : (tb.toneLevel > 0 ? tb.toneColor : Theme.borderCard)
                border.width: 1

                Text {
                    anchors.centerIn: parent
                    text: tb.isMuted ? "MUTE" : "ON"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: tb.isMuted ? "#ffffff" : (tb.toneLevel > 0 ? tb.toneColor : Theme.textDim)
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        tb.selected();
                        Bridge.toggleToneMute(tb.toneNumber);
                    }
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
                    color: "#1e293b"
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

                        function updateLevel(mouse) {
                            tb.selected();
                            let norm = Math.max(0.0, Math.min(1.0, mouse.x / levelTrack.width));
                            let newLvl = Math.round(norm * 127);
                            Bridge.setToneLevel(tb.toneNumber, newLvl);
                        }

                        onPressed: (mouse) => updateLevel(mouse)
                        onPositionChanged: (mouse) => {
                            if (pressed) updateLevel(mouse)
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
        color: "#10141d"
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
                    color: "#38bdf8"
                }

                Text {
                    Layout.fillWidth: true
                    text: wc.waveData ? (wc.waveData.bank + " " + wc.waveData.number + ": " + wc.waveData.name) : "INTA 579: Juno Saw HD"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: Theme.textPrimary
                    elide: Text.ElideRight
                }

                Rectangle {
                    width: ScaleMetrics.dp(48)
                    height: ScaleMetrics.dp(22)
                    radius: 3
                    color: Theme.bgCardActive
                    border.color: "#38bdf8"
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: "BROWSE"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: "#38bdf8"
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: Bridge.openWaveBrowser(wc.toneIdx)
                    }
                }
            }
        }
    }

    // LFO Wave Picker Overlay Modal
    Rectangle {
        id: wavePickerModal
        anchors.fill: parent
        z: 999
        color: Qt.rgba(0, 0, 0, 0.75)
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
            color: "#0f172a"
            border.color: "#38bdf8"
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
                    Rectangle {
                        width: ScaleMetrics.dp(24)
                        height: ScaleMetrics.dp(24)
                        radius: 4
                        color: "#1e293b"
                        border.color: Theme.borderCard
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: "✕"
                            color: Theme.textDim
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(10)
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: root.lfoWavePickerOpen = false
                        }
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
                        delegate: Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: ScaleMetrics.dp(4)
                            color: root.lfoData.wave === modelData ? Theme.bgCardActive : "#10141d"
                            border.color: root.lfoData.wave === modelData ? "#38bdf8" : Theme.borderCard
                            border.width: root.lfoData.wave === modelData ? 2 : 1

                            Text {
                                anchors.centerIn: parent
                                text: modelData
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(9)
                                color: root.lfoData.wave === modelData ? "#38bdf8" : Theme.textPrimary
                            }

                            MouseArea {
                                anchors.fill: parent
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
}
