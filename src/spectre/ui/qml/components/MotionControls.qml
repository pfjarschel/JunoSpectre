import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

Rectangle {
    id: root
    height: ScaleMetrics.dp(60)
    color: Theme.bgCard
    border.color: Theme.borderCard
    border.width: 1

    Flickable {
        anchors.fill: parent
        contentWidth: mainRow.implicitWidth + ScaleMetrics.dp(24)
        contentHeight: parent.height
        boundsBehavior: Flickable.StopAtBounds
        clip: true

        RowLayout {
            id: mainRow
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: parent.left
            anchors.leftMargin: ScaleMetrics.dp(12)
            spacing: ScaleMetrics.dp(12)

            // =================================================================
            // 2D Vector Controls (Visible in vector_2d mode)
            // =================================================================
            RowLayout {
                visible: Bridge.morphMode === "vector_2d"
                spacing: ScaleMetrics.dp(12)

                // Transport Controls Group (Fixed Widths, Zero Overlap)
                RowLayout {
                    spacing: ScaleMetrics.dp(6)

                    // REC Button
                    TouchButton {
                        text: "● REC"
                        isPrimary: Bridge.recorderState === "recording"
                        activeColor: Theme.recording
                        onClicked: {
                            if (Bridge.recorderState === "recording") {
                                Bridge.stopRecording()
                            } else {
                                Bridge.startRecording()
                            }
                        }
                    }

                    // PLAY / PAUSE Button (Exact same width to prevent shifting)
                    TouchButton {
                        text: Bridge.recorderState === "playing" ? "❚❚ PAUSE" : "▶ PLAY"
                        isPrimary: Bridge.recorderState === "playing"
                        activeColor: Theme.playing
                        onClicked: {
                            if (Bridge.recorderState === "playing") {
                                Bridge.pauseMotion()
                            } else {
                                Bridge.playMotion()
                            }
                        }
                    }

                    // STOP Button
                    TouchButton {
                        text: "■ STOP"
                        onClicked: Bridge.stopMotion()
                    }

                    // CLEAR Button
                    TouchButton {
                        text: "⌫ CLR"
                        onClicked: Bridge.clearMotion()
                    }
                }

                // Divider
                Rectangle {
                    width: 1
                    height: ScaleMetrics.dp(32)
                    color: Theme.borderCard
                }

                // Loop Mode Selector
                RowLayout {
                    spacing: ScaleMetrics.dp(5)

                    PillButton {
                        text: "FWD"
                        isActive: Bridge.loopMode === "forward"
                        onClicked: Bridge.setLoopMode("forward")
                    }
                    PillButton {
                        text: "P-PONG"
                        isActive: Bridge.loopMode === "ping_pong"
                        onClicked: Bridge.setLoopMode("ping_pong")
                    }
                    PillButton {
                        text: "REV"
                        isActive: Bridge.loopMode === "reverse"
                        onClicked: Bridge.setLoopMode("reverse")
                    }
                }

                // Divider
                Rectangle {
                    width: 1
                    height: ScaleMetrics.dp(32)
                    color: Theme.borderCard
                }

                // Continuous Speed Slider
                SpeedSlider {}

                // Divider
                Rectangle {
                    width: 1
                    height: ScaleMetrics.dp(32)
                    color: Theme.borderCard
                }

                // Orbital Automator Selector (MAN, ORBIT, LISS, CHAOS)
                RowLayout {
                    spacing: ScaleMetrics.dp(5)

                    PillButton {
                        text: "MAN"
                        isActive: Bridge.automator === "none"
                        onClicked: Bridge.setAutomator("none")
                    }
                    PillButton {
                        text: "ORBIT"
                        isActive: Bridge.automator === "circle"
                        onClicked: Bridge.setAutomator("circle")
                    }
                    PillButton {
                        text: "LISS"
                        isActive: Bridge.automator === "lissajous"
                        onClicked: Bridge.setAutomator("lissajous")
                    }
                    PillButton {
                        text: "CHAOS"
                        isActive: Bridge.automator === "chaos"
                        onClicked: Bridge.setAutomator("chaos")
                    }
                }
            }

            // =================================================================
            // 1D Wavetable Controls (Visible in wavetable_1d mode)
            // =================================================================
            RowLayout {
                visible: Bridge.morphMode === "wavetable_1d"
                spacing: ScaleMetrics.dp(12)

                Text {
                    text: "SWEEP MODES:"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(10)
                    color: Theme.textDim
                }

                RowLayout {
                    spacing: ScaleMetrics.dp(6)

                    PillButton {
                        text: "MANUAL"
                        isActive: Bridge.wavetableSweepMode === "manual"
                        onClicked: Bridge.setWavetableSweepMode("manual")
                    }
                    PillButton {
                        text: "SINE"
                        isActive: Bridge.wavetableSweepMode === "sine"
                        onClicked: Bridge.setWavetableSweepMode("sine")
                    }
                    PillButton {
                        text: "TRIANGLE"
                        isActive: Bridge.wavetableSweepMode === "triangle"
                        onClicked: Bridge.setWavetableSweepMode("triangle")
                    }
                    PillButton {
                        text: "RAMP UP"
                        isActive: Bridge.wavetableSweepMode === "ramp"
                        onClicked: Bridge.setWavetableSweepMode("ramp")
                    }
                    PillButton {
                        text: "RANDOM S&H"
                        isActive: Bridge.wavetableSweepMode === "random_step"
                        onClicked: Bridge.setWavetableSweepMode("random_step")
                    }
                }

                // Divider
                Rectangle {
                    width: 1
                    height: ScaleMetrics.dp(32)
                    color: Theme.borderCard
                }

                // Continuous Speed Slider for 1D Sweeps
                SpeedSlider {}
            }
        }
    }

    // Touch Button Component (Fixed Width to prevent overlap)
    component TouchButton: Rectangle {
        id: tbRoot
        property string text: "BTN"
        property bool isPrimary: false
        property color activeColor: Theme.primary
        signal clicked()

        Layout.preferredWidth: ScaleMetrics.dp(84)
        Layout.preferredHeight: ScaleMetrics.dp(40)
        radius: ScaleMetrics.dp(6)
        color: isPrimary ? activeColor : Theme.bgApp
        border.color: isPrimary ? activeColor : Theme.borderCard
        border.width: 1

        Text {
            id: label
            anchors.centerIn: parent
            text: tbRoot.text
            font.bold: true
            font.pixelSize: ScaleMetrics.sp(11)
            horizontalAlignment: Text.AlignHCenter
            color: tbRoot.isPrimary ? "#000000" : Theme.textPrimary
        }

        MouseArea {
            anchors.fill: parent
            onClicked: tbRoot.clicked()
        }
    }

    // Pill Button Component
    component PillButton: Rectangle {
        id: pbRoot
        property string text: "PILL"
        property bool isActive: false
        signal clicked()

        Layout.preferredHeight: ScaleMetrics.dp(36)
        Layout.preferredWidth: Math.max(ScaleMetrics.dp(58), labelPill.implicitWidth + ScaleMetrics.dp(18))
        radius: ScaleMetrics.dp(5)
        color: isActive ? Theme.bgCardActive : "transparent"
        border.color: isActive ? Theme.primary : Theme.borderCard
        border.width: 1

        Text {
            id: labelPill
            anchors.centerIn: parent
            text: pbRoot.text
            font.bold: pbRoot.isActive
            font.pixelSize: ScaleMetrics.sp(11)
            horizontalAlignment: Text.AlignHCenter
            color: pbRoot.isActive ? Theme.textPrimary : Theme.textMuted
        }

        MouseArea {
            anchors.fill: parent
            onClicked: pbRoot.clicked()
        }
    }

    // Continuous Speed Slider Component
    component SpeedSlider: Rectangle {
        id: ssRoot
        Layout.preferredWidth: ScaleMetrics.dp(140)
        Layout.preferredHeight: ScaleMetrics.dp(42)
        color: Theme.bgApp
        border.color: Theme.borderCard
        border.width: 1
        radius: ScaleMetrics.dp(6)

        property real norm: Math.max(0.0, Math.min(1.0, (Bridge.speed - 0.25) / 1.75))

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(4)
            spacing: ScaleMetrics.dp(2)

            Text {
                text: "SPEED: " + Bridge.speed.toFixed(2) + "x"
                font.bold: true
                font.family: Theme.fontMono
                font.pixelSize: ScaleMetrics.sp(9)
                color: Theme.tone3
                Layout.alignment: Qt.AlignHCenter
            }

            Rectangle {
                id: track
                Layout.fillWidth: true
                Layout.preferredHeight: ScaleMetrics.dp(12)
                radius: ScaleMetrics.dp(6)
                color: "#1e293b"

                Rectangle {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    width: parent.width * ssRoot.norm
                    radius: ScaleMetrics.dp(6)
                    gradient: Gradient {
                        orientation: Gradient.Horizontal
                        GradientStop { position: 0.0; color: Theme.tone3 }
                        GradientStop { position: 1.0; color: Theme.tone1 }
                    }
                }

                Rectangle {
                    id: thumb
                    x: Math.max(0, Math.min(track.width - width, ssRoot.norm * (track.width - width)))
                    anchors.verticalCenter: parent.verticalCenter
                    width: ScaleMetrics.dp(16)
                    height: ScaleMetrics.dp(16)
                    radius: width / 2
                    color: "#ffffff"
                    border.color: Theme.tone3
                    border.width: 1
                }

                MouseArea {
                    anchors.fill: parent
                    preventStealing: true

                    function updateSpeed(mouse) {
                        var frac = Math.max(0.0, Math.min(1.0, mouse.x / track.width))
                        var spd = 0.25 + frac * 1.75
                        Bridge.setSpeed(spd)
                    }

                    onPressed: (mouse) => updateSpeed(mouse)
                    onPositionChanged: (mouse) => {
                        if (pressed) updateSpeed(mouse)
                    }
                }
            }
        }
    }
}
