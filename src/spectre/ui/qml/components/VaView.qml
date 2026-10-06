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

                    Rectangle {
                        width: ScaleMetrics.dp(8)
                        height: ScaleMetrics.dp(8)
                        radius: 4
                        color: "#38bdf8"
                    }

                    Text {
                        text: "4-OSC VIRTUAL ANALOG"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(11)
                        font.letterSpacing: 1.1
                        color: Theme.textPrimary
                    }

                    Item { Layout.fillWidth: true }

                    // Auto Detune Button
                    Rectangle {
                        width: ScaleMetrics.dp(125)
                        height: ScaleMetrics.dp(26)
                        radius: ScaleMetrics.dp(4)
                        color: root.unisonActive ? Theme.bgCardActive : "#10141d"
                        border.color: root.unisonActive ? "#38bdf8" : Theme.borderCard
                        border.width: root.unisonActive ? 1.5 : 1

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: 4
                            Rectangle {
                                width: 5; height: 5; radius: 2.5
                                color: root.unisonActive ? "#38bdf8" : Theme.textDim
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
                        color: "#10141d"
                        border.color: root.unisonActive ? "#38bdf8" : Theme.borderCard
                        border.width: root.unisonActive ? 1.5 : 1
                        opacity: root.unisonActive ? 1.0 : 0.35

                        Rectangle {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            width: parent.width * (root.unisonDetune / 50.0)
                            radius: ScaleMetrics.dp(3)
                            color: root.unisonActive ? Qt.rgba(0.22, 0.74, 0.97, 0.55) : Qt.rgba(0.22, 0.74, 0.97, 0.15)
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
                        coarseVal: root.osc1Coarse
                        fineVal: root.osc1Fine
                        lvlVal: root.osc1Level
                        pwVal: root.osc1Pw
                        pwmVal: root.osc1Pwm
                        onWaveChanged: (w) => Bridge.setVaOscWave(1, w)
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
                        coarseVal: root.osc2Coarse
                        fineVal: root.osc2Fine
                        lvlVal: root.osc2Level
                        pwVal: root.osc2Pw
                        pwmVal: root.osc2Pwm
                        onWaveChanged: (w) => Bridge.setVaOscWave(2, w)
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
                        coarseVal: root.osc3Coarse
                        fineVal: root.osc3Fine
                        lvlVal: root.osc3Level
                        pwVal: root.osc3Pw
                        pwmVal: root.osc3Pwm
                        onWaveChanged: (w) => Bridge.setVaOscWave(3, w)
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
                        coarseVal: root.osc4Coarse
                        fineVal: root.osc4Fine
                        lvlVal: root.osc4Level
                        pwVal: root.osc4Pw
                        pwmVal: root.osc4Pwm
                        onWaveChanged: (w) => Bridge.setVaOscWave(4, w)
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
        property int waveIdx: 0
        property int coarseVal: 0
        property int fineVal: 0
        property int lvlVal: 100
        property int pwVal: 50
        property int pwmVal: 0
        signal waveChanged(int w)
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

        function resolveWaveId() {
            if (osc.waveIdx === 0) return 579; // Juno Saw HD
            if (osc.waveIdx === 1) {
                if (osc.pwmVal >= 20) {
                    if (osc.pwmVal < 40) return 1326; // PWM Wave A
                    if (osc.pwmVal < 60) return 1327; // PWM Wave B
                    if (osc.pwmVal < 80) return 1328; // PWM Wave C
                    return 1329;                     // PWM Wave
                } else {
                    const pwMap = {
                        10: 612, // JP8 Pls 10HD
                        15: 613, // JP8 Pls 15HD
                        25: 614, // JP8 Pls 25HD
                        30: 615, // JP8 Pls 30HD
                        40: 616, // JP8 Pls 40HD
                        45: 617, // JP8 Pls 45HD
                        50: 600  // Juno Sqr HD
                    };
                    return pwMap[osc.pwVal] || 600;
                }
            }
            if (osc.waveIdx === 2) return 621; // Syn Triangle
            if (osc.waveIdx === 3) return 1322; // ARP Sine HD
            if (osc.waveIdx === 4) return 637; // Pink Noise
            return 579;
        }

        function dispatchWave() {
            if (typeof Bridge !== "undefined" && Bridge.setToneWave) {
                Bridge.setToneWave(osc.oscIndex, "INTA", resolveWaveId());
            }
        }

        radius: ScaleMetrics.dp(6)
        color: "#10141d"
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

                Item { Layout.fillWidth: true }

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
                    delegate: Rectangle {
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(20)
                        radius: 3
                        color: osc.waveIdx === index ? Theme.bgCardActive : "#0a0d14"
                        border.color: osc.waveIdx === index ? osc.accent : Theme.borderCard
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: modelData
                            font.bold: osc.waveIdx === index
                            font.pixelSize: ScaleMetrics.sp(7)
                            color: osc.waveIdx === index ? osc.accent : Theme.textDim
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                osc.waveChanged(index);
                                osc.dispatchWave();
                            }
                        }
                    }
                }
            }

            // Sliders: Coarse, Fine, Level, PW, PWM
            TouchFader {
                Layout.fillWidth: true
                Layout.preferredHeight: ScaleMetrics.dp(24)
                label: "COARSE"
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
                    osc.dispatchWave();
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
                    osc.dispatchWave();
                }
            }

            Item { Layout.fillHeight: true }
        }
    }
}
