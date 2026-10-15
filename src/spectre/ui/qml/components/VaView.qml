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

    property int osc1Wave: Bridge.vaOsc1Wave
    property int osc2Wave: Bridge.vaOsc2Wave
    property int osc3Wave: Bridge.vaOsc3Wave
    property int osc4Wave: Bridge.vaOsc4Wave
    property int osc1Coarse: Bridge.vaOsc1Coarse
    property int osc2Coarse: Bridge.vaOsc2Coarse
    property int osc3Coarse: Bridge.vaOsc3Coarse
    property int osc4Coarse: Bridge.vaOsc4Coarse
    property int osc1Fine: Bridge.vaOsc1Fine
    property int osc2Fine: Bridge.vaOsc2Fine
    property int osc3Fine: Bridge.vaOsc3Fine
    property int osc4Fine: Bridge.vaOsc4Fine
    property int osc1Level: Bridge.tone1Level
    property int osc2Level: Bridge.tone2Level
    property int osc3Level: Bridge.tone3Level
    property int osc4Level: Bridge.tone4Level
    property int osc1Pw: Bridge.vaOsc1Pw
    property int osc2Pw: Bridge.vaOsc2Pw
    property int osc3Pw: Bridge.vaOsc3Pw
    property int osc4Pw: Bridge.vaOsc4Pw
    property int osc1Pwm: Bridge.vaOsc1Pwm
    property int osc2Pwm: Bridge.vaOsc2Pwm
    property int osc3Pwm: Bridge.vaOsc3Pwm
    property int osc4Pwm: Bridge.vaOsc4Pwm
    property bool unisonActive: Bridge.autoDetune
    property var waveNames: (Bridge.toneWaveData || []).map(w => w ? w.name : "")
    property int unisonDetune: Bridge.autoDetuneCents

    RowLayout {
        anchors.fill: parent
        anchors.margins: ScaleMetrics.dp(8)
        spacing: ScaleMetrics.dp(8)

        // =====================================================================
        // COLUMN 1: 4-OSC ANALOG GENERATOR (2x2 GRID) (~640dp)
        // =====================================================================
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
                spacing: ScaleMetrics.dp(6)

                // Top Header: Title + Unison Switch + Unison Detune
                RowLayout {
                    Layout.fillWidth: true
                    spacing: ScaleMetrics.dp(6)

                    PageTitle { text: "4-OSC VIRTUAL ANALOG" }

                    StructureButton {
                        Layout.leftMargin: ScaleMetrics.dp(6)
                    }

                    Item { Layout.fillWidth: true }

                    // Auto Detune Button
                    Rectangle {
                        width: ScaleMetrics.dp(125)
                        height: ScaleMetrics.dp(26)
                        radius: ScaleMetrics.dp(4)
                        color: root.unisonActive ? Theme.tint(Theme.pageAccent) : Theme.bgControl
                        border.color: root.unisonActive ? Theme.pageAccent : Theme.borderCard
                        border.width: root.unisonActive ? 1.5 : 1

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: 4
                            Rectangle {
                                width: 5; height: 5; radius: 2.5
                                color: root.unisonActive ? Theme.pageAccent : Theme.textDim
                            }
                            Text {
                                text: root.unisonActive ? "AUTO DETUNE: ON" : "AUTO DETUNE: OFF"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(8)
                                color: root.unisonActive ? Theme.textPrimary : Theme.textDim
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: Bridge.setAutoDetune(!root.unisonActive)
                        }
                    }

                    // Unison Detune Mini-Fader (Faded when Unison is OFF)
                    Rectangle {
                        width: ScaleMetrics.dp(110)
                        height: ScaleMetrics.dp(26)
                        radius: ScaleMetrics.dp(4)
                        color: Theme.bgControl
                        border.color: root.unisonActive ? Theme.pageAccent : Theme.borderCard
                        border.width: root.unisonActive ? 1.5 : 1
                        opacity: root.unisonActive ? 1.0 : 0.35

                        Rectangle {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            width: parent.width * (root.unisonDetune / 50.0)
                            radius: ScaleMetrics.dp(3)
                            color: Theme.tint(Theme.pageAccent, root.unisonActive ? 0.55 : 0.15)
                        }

                        TouchHighlight {
                            anchors.fill: parent
                            radius: parent.radius
                            ctlKey: "detune.auto"
                        }

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: ScaleMetrics.dp(4)
                            Text {
                                text: "DETUNE"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(7)
                                color: root.unisonActive ? Theme.textSecondary : Theme.textDim
                            }
                            Item { Layout.fillWidth: true }
                            Text {
                                text: root.unisonDetune.toString()
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(8)
                                font.family: Theme.fontMono
                                color: root.unisonActive ? Theme.textPrimary : Theme.textDim
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            enabled: root.unisonActive
                            onPressed: (mouse) => {
                                const norm = Math.max(0.0, Math.min(1.0, mouse.x / width));
                                Bridge.setAutoDetuneCents(Math.round(norm * 50));
                            }
                            onPositionChanged: (mouse) => {
                                if (pressed) {
                                    const norm = Math.max(0.0, Math.min(1.0, mouse.x / width));
                                    Bridge.setAutoDetuneCents(Math.round(norm * 50));
                                }
                            }
                        }
                    }
                }

                // 2x2 Grid of the 4 Oscillators
                GridLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    columns: 2
                    rows: 2
                    rowSpacing: ScaleMetrics.dp(6)
                    columnSpacing: ScaleMetrics.dp(6)

                    // OSC 1 (Top Left)
                    OscCard {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        oscIndex: 1
                        title: "OSC 1"
                        accent: Theme.tone1
                        autoDetuneActive: root.unisonActive
                        waveIdx: root.osc1Wave
                        waveName: root.waveNames[0] || ""
                        coarseVal: root.osc1Coarse
                        fineVal: root.osc1Fine
                        lvlVal: root.osc1Level
                        pwVal: root.osc1Pw
                        pwmVal: root.osc1Pwm
                        onCoarseChanged: (c) => Bridge.setVaOscCoarse(1, c)
                        onFineChanged: (f) => Bridge.setVaOscFine(1, f)
                        onLvlChanged: (l) => Bridge.setVaOscLevel(1, l)
                        onPwChanged: (p) => Bridge.setVaOscPw(1, p)
                        onPwmChanged: (m) => Bridge.setVaOscPwm(1, m)
                    }

                    // OSC 2 (Top Right)
                    OscCard {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        oscIndex: 2
                        title: "OSC 2"
                        accent: Theme.tone2
                        autoDetuneActive: root.unisonActive
                        waveIdx: root.osc2Wave
                        waveName: root.waveNames[1] || ""
                        coarseVal: root.osc2Coarse
                        fineVal: root.osc2Fine
                        lvlVal: root.osc2Level
                        pwVal: root.osc2Pw
                        pwmVal: root.osc2Pwm
                        onCoarseChanged: (c) => Bridge.setVaOscCoarse(2, c)
                        onFineChanged: (f) => Bridge.setVaOscFine(2, f)
                        onLvlChanged: (l) => Bridge.setVaOscLevel(2, l)
                        onPwChanged: (p) => Bridge.setVaOscPw(2, p)
                        onPwmChanged: (m) => Bridge.setVaOscPwm(2, m)
                    }

                    // OSC 3 (Bottom Left)
                    OscCard {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        oscIndex: 3
                        title: "OSC 3"
                        accent: Theme.tone3
                        autoDetuneActive: root.unisonActive
                        waveIdx: root.osc3Wave
                        waveName: root.waveNames[2] || ""
                        coarseVal: root.osc3Coarse
                        fineVal: root.osc3Fine
                        lvlVal: root.osc3Level
                        pwVal: root.osc3Pw
                        pwmVal: root.osc3Pwm
                        onCoarseChanged: (c) => Bridge.setVaOscCoarse(3, c)
                        onFineChanged: (f) => Bridge.setVaOscFine(3, f)
                        onLvlChanged: (l) => Bridge.setVaOscLevel(3, l)
                        onPwChanged: (p) => Bridge.setVaOscPw(3, p)
                        onPwmChanged: (m) => Bridge.setVaOscPwm(3, m)
                    }

                    // OSC 4 (Bottom Right)
                    OscCard {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        oscIndex: 4
                        title: "OSC 4"
                        accent: Theme.tone4
                        autoDetuneActive: root.unisonActive
                        waveIdx: root.osc4Wave
                        waveName: root.waveNames[3] || ""
                        coarseVal: root.osc4Coarse
                        fineVal: root.osc4Fine
                        lvlVal: root.osc4Level
                        pwVal: root.osc4Pw
                        pwmVal: root.osc4Pwm
                        onCoarseChanged: (c) => Bridge.setVaOscCoarse(4, c)
                        onFineChanged: (f) => Bridge.setVaOscFine(4, f)
                        onLvlChanged: (l) => Bridge.setVaOscLevel(4, l)
                        onPwChanged: (p) => Bridge.setVaOscPw(4, p)
                        onPwmChanged: (m) => Bridge.setVaOscPwm(4, m)
                    }
                }
            }
        }

        // =====================================================================
        // COLUMN 2: TABBED MASTER SCULPTOR PANEL (~360dp)
        // =====================================================================
        SculptorPanel {
            Layout.preferredWidth: ScaleMetrics.dp(360)
            Layout.fillHeight: true
        }
    }

    // =========================================================================
    // REUSABLE OSCILLATOR CARD COMPONENT (2x2 Grid)
    // =========================================================================
    component OscCard: Rectangle {
        id: osc
        property int oscIndex: 1
        property string title: "OSC"
        property color accent: Theme.tone1
        property bool autoDetuneActive: false
        property int waveIdx: 0          // chip index; 5 = PLUS (any other wave)
        property string waveName: ""
        property int coarseVal: 0
        property int fineVal: 0
        property int lvlVal: 100
        property int pwVal: 50
        property int pwmVal: 0
        signal coarseChanged(int c)
        signal fineChanged(int f)
        signal lvlChanged(int l)
        signal pwChanged(int p)
        signal pwmChanged(int m)

        readonly property var pwSteps: [10, 15, 25, 30, 40, 45, 50]

        function getPwText() {
            if (osc.waveIdx !== 1) return "—";
            if (osc.pwmVal >= 20) return "AUTO (PWM)";
            if (osc.pwVal === 50) return "50% (SQR)";
            return osc.pwVal + "%";
        }

        function getPwmText() {
            if (osc.waveIdx !== 1) return "—";
            if (osc.pwmVal < 20) return "OFF (" + osc.pwmVal + "%)";
            if (osc.pwmVal < 40) return "PWM A (" + osc.pwmVal + "%)";
            if (osc.pwmVal < 60) return "PWM B (" + osc.pwmVal + "%)";
            if (osc.pwmVal < 80) return "PWM C (" + osc.pwmVal + "%)";
            return "PWM WAVE (" + osc.pwmVal + "%)";
        }

        radius: ScaleMetrics.dp(6)
        color: Theme.bgControl
        border.color: Theme.borderCard
        border.width: 1

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(6)
            spacing: ScaleMetrics.dp(3)

            // Card Header
            RowLayout {
                Layout.fillWidth: true
                spacing: 4

                Rectangle {
                    width: 6; height: 6; radius: 3
                    color: osc.accent
                }

                Text {
                    text: osc.title
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(9)
                    color: osc.accent
                }

                Text {
                    Layout.fillWidth: true
                    text: osc.waveIdx === 5 ? osc.waveName : ""
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: Theme.textPrimary
                    elide: Text.ElideRight
                }

                Text {
                    text: "VOL: " + osc.lvlVal
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(8)
                    font.family: Theme.fontMono
                    color: Theme.textDim
                }
            }

            // Waveform Selector Chips
            RowLayout {
                Layout.fillWidth: true
                spacing: 2
                Repeater {
                    model: ["SAW", "SQR", "TRI", "SIN", "NOISE"]
                    delegate: SpButton {
                        Layout.fillWidth: true
                        implicitHeight: ScaleMetrics.dp(20)
                        text: modelData
                        fontSize: 8
                        accent: osc.accent
                        checked: osc.waveIdx === index
                        onClicked: Bridge.setVaOscWave(osc.oscIndex, index)
                    }
                }
                // PLUS: any Juno wave, from the wave browser
                SpButton {
                    implicitHeight: ScaleMetrics.dp(20)
                    implicitWidth: ScaleMetrics.dp(28)
                    icon: "add"
                    iconSize: 11
                    accent: osc.accent
                    checked: osc.waveIdx === 5
                    onClicked: Bridge.openWaveBrowser(osc.oscIndex)
                }
            }

            // Sliders: Coarse, Fine, Level, PW, PWM
            TouchFader {
                Layout.fillWidth: true
                Layout.preferredHeight: ScaleMetrics.dp(24)
                label: "COARSE"
                ctlKey: "tone." + osc.oscIndex + ".pitch_coarse"
                valText: (osc.coarseVal > 0 ? "+" + osc.coarseVal : osc.coarseVal.toString()) + " st"
                normVal: (osc.coarseVal + 24) / 48.0
                isBipolar: true
                barColor: osc.accent
                onMoved: (n) => osc.coarseChanged(Math.round(n * 48 - 24))
            }

            TouchFader {
                Layout.fillWidth: true
                Layout.preferredHeight: ScaleMetrics.dp(24)
                label: osc.autoDetuneActive ? "FINE (AUTO)" : "FINE"
                ctlKey: "tone." + osc.oscIndex + ".pitch_fine"
                valText: (osc.fineVal > 0 ? "+" + osc.fineVal : osc.fineVal.toString()) + " c"
                normVal: (osc.fineVal + 50) / 100.0
                isBipolar: true
                barColor: osc.accent
                enabled: !osc.autoDetuneActive
                opacity: osc.autoDetuneActive ? 0.45 : 1.0
                onMoved: (n) => osc.fineChanged(Math.round(n * 100 - 50))
            }

            TouchFader {
                Layout.fillWidth: true
                Layout.preferredHeight: ScaleMetrics.dp(24)
                label: "LEVEL"
                ctlKey: "tone." + osc.oscIndex + ".tva_level"
                valText: osc.lvlVal.toString()
                normVal: osc.lvlVal / 127.0
                barColor: osc.accent
                onMoved: (n) => osc.lvlChanged(Math.round(n * 127))
            }

            TouchFader {
                Layout.fillWidth: true
                Layout.preferredHeight: ScaleMetrics.dp(24)
                label: "PULSE WIDTH"
                valText: osc.getPwText()
                normVal: osc.pwVal / 50.0
                barColor: osc.accent
                enabled: osc.waveIdx === 1 && osc.pwmVal < 20
                opacity: (osc.waveIdx === 1 && osc.pwmVal < 20) ? 1.0 : 0.25
                onMoved: (n) => {
                    const idx = Math.min(osc.pwSteps.length - 1, Math.max(0, Math.floor(n * osc.pwSteps.length)));
                    osc.pwChanged(osc.pwSteps[idx]);
                }
            }

            TouchFader {
                Layout.fillWidth: true
                Layout.preferredHeight: ScaleMetrics.dp(24)
                label: "PWM"
                valText: osc.getPwmText()
                normVal: osc.pwmVal / 100.0
                barColor: osc.accent
                enabled: osc.waveIdx === 1
                opacity: osc.waveIdx === 1 ? 1.0 : 0.25
                onMoved: (n) => {
                    osc.pwmChanged(Math.round(n * 100));
                }
            }

            Item { Layout.fillHeight: true }
        }
    }
}
