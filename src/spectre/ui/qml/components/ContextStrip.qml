import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

Rectangle {
    id: root
    height: ScaleMetrics.dp(50)
    color: Theme.bgCard
    border.color: Theme.borderCard
    border.width: 1

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: ScaleMetrics.dp(10)
        anchors.rightMargin: ScaleMetrics.dp(10)
        spacing: ScaleMetrics.dp(6)

        Repeater {
            model: 8
            delegate: EncoderCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                knobIndex: modelData + 1
            }
        }
    }

    // Individual Encoder Touch Card Component
    component EncoderCard: Rectangle {
        id: card
        property int knobIndex: 1
        readonly property string currentView: Bridge.activeView

        // State property for mock FX and Mixer params
        property real internalVal: 0.5

        radius: ScaleMetrics.dp(6)
        color: Theme.bgApp
        border.color: mouseArea.containsPress ? Theme.primary : Theme.borderCard
        border.width: 1

        // Parameter Name based on active view and knob index
        readonly property string paramName: {
            if (currentView === "VECTOR") {
                const names = ["X POS", "Y POS", "ATTR X", "ATTR Y", "SPEED", "MODE", "CURVE", "BPM"];
                return names[knobIndex - 1] || "PARAM";
            } else if (currentView === "WAVETABLE") {
                const names = ["MORPH", "SPEED", "SWEEP", "CURVE", "T1 LVL", "T2 LVL", "T3 LVL", "T4 LVL"];
                return names[knobIndex - 1] || "PARAM";
            } else if (currentView === "MACROS") {
                const names = ["BRIGHT", "WARMTH", "SUB OSC", "AIR", "DRIVE", "SPACE", "MOTION", "ATTACK"];
                return names[knobIndex - 1] || "MACRO";
            } else if (currentView === "PATCH EDIT") {
                const names = ["CUTOFF", "RESO", "ATTACK", "RELEASE", "T1 LVL", "T2 LVL", "T3 LVL", "T4 LVL"];
                return names[knobIndex - 1] || "EDIT";
            } else if (currentView === "PERF MIXER") {
                return "P" + knobIndex + " VOL";
            } else if (currentView === "EFFECTS") {
                const names = ["MFX TYPE", "CTRL 1", "CTRL 2", "WET/DRY", "CHORUS", "REVERB", "REV TIME", "MAST EQ"];
                return names[knobIndex - 1] || "FX";
            }
            return "ENC " + knobIndex;
        }

        // Normalized value (0.0 .. 1.0) with localized property tracking
        readonly property real normValue: {
            if (currentView === "VECTOR") {
                switch (knobIndex) {
                    case 1: return Bridge.vectorX;
                    case 2: return Bridge.vectorY;
                    case 3: return Bridge.attractorX;
                    case 4: return Bridge.attractorY;
                    case 5: return Math.max(0.0, Math.min(1.0, (Bridge.speed - 0.25) / 1.75));
                    case 6: {
                        const m = Bridge.automator;
                        return m === "circle" ? 0.33 : m === "lissajous" ? 0.66 : m === "chaos" ? 1.0 : 0.0;
                    }
                    case 7: return Bridge.curve === "equal_power" ? 1.0 : 0.0;
                    case 8: return Math.max(0.0, Math.min(1.0, (Bridge.bpm - 20) / 280));
                }
            } else if (currentView === "WAVETABLE") {
                switch (knobIndex) {
                    case 1: return Bridge.wavetablePos;
                    case 2: return Math.max(0.0, Math.min(1.0, (Bridge.speed - 0.25) / 1.75));
                    case 3: {
                        const sm = Bridge.wavetableSweepMode;
                        return sm === "sine" ? 0.25 : sm === "triangle" ? 0.5 : sm === "ramp" ? 0.75 : sm === "random_step" ? 1.0 : 0.0;
                    }
                    case 4: return Bridge.curve === "equal_power" ? 1.0 : 0.0;
                    case 5: return Bridge.tone1Level / 127.0;
                    case 6: return Bridge.tone2Level / 127.0;
                    case 7: return Bridge.tone3Level / 127.0;
                    case 8: return Bridge.tone4Level / 127.0;
                }
            } else if (currentView === "MACROS") {
                const val = knobIndex === 1 ? Bridge.macro1 :
                            knobIndex === 2 ? Bridge.macro2 :
                            knobIndex === 3 ? Bridge.macro3 :
                            knobIndex === 4 ? Bridge.macro4 :
                            knobIndex === 5 ? Bridge.macro5 :
                            knobIndex === 6 ? Bridge.macro6 :
                            knobIndex === 7 ? Bridge.macro7 : Bridge.macro8;
                return val / 127.0;
            } else if (currentView === "PATCH EDIT") {
                switch (knobIndex) {
                    case 1: return (Bridge.masterCutoff - 1) / 126.0;
                    case 2: return (Bridge.masterReso - 1) / 126.0;
                    case 3: return (Bridge.masterAttack - 1) / 126.0;
                    case 4: return (Bridge.masterRelease - 1) / 126.0;
                    case 5: return Bridge.tone1Level / 127.0;
                    case 6: return Bridge.tone2Level / 127.0;
                    case 7: return Bridge.tone3Level / 127.0;
                    case 8: return Bridge.tone4Level / 127.0;
                }
            }
            return card.internalVal;
        }

        // Display string for the readout
        readonly property string displayString: {
            if (currentView === "VECTOR") {
                switch (knobIndex) {
                    case 1: return Bridge.vectorX.toFixed(2);
                    case 2: return Bridge.vectorY.toFixed(2);
                    case 3: return Bridge.attractorX.toFixed(2);
                    case 4: return Bridge.attractorY.toFixed(2);
                    case 5: return Bridge.speed.toFixed(2) + "x";
                    case 6: return Bridge.automator.toUpperCase();
                    case 7: return Bridge.curve === "equal_power" ? "EQ-PWR" : "LINEAR";
                    case 8: return Math.round(Bridge.bpm).toString();
                }
            } else if (currentView === "WAVETABLE") {
                switch (knobIndex) {
                    case 1: return Bridge.wavetablePos.toFixed(2);
                    case 2: return Bridge.speed.toFixed(2) + "x";
                    case 3: return Bridge.wavetableSweepMode.toUpperCase();
                    case 4: return Bridge.curve === "equal_power" ? "EQ-PWR" : "LINEAR";
                    case 5: return Bridge.tone1Level.toString();
                    case 6: return Bridge.tone2Level.toString();
                    case 7: return Bridge.tone3Level.toString();
                    case 8: return Bridge.tone4Level.toString();
                }
            } else if (currentView === "MACROS") {
                const val = knobIndex === 1 ? Bridge.macro1 :
                            knobIndex === 2 ? Bridge.macro2 :
                            knobIndex === 3 ? Bridge.macro3 :
                            knobIndex === 4 ? Bridge.macro4 :
                            knobIndex === 5 ? Bridge.macro5 :
                            knobIndex === 6 ? Bridge.macro6 :
                            knobIndex === 7 ? Bridge.macro7 : Bridge.macro8;
                return val.toString();
            } else if (currentView === "PATCH EDIT") {
                switch (knobIndex) {
                    case 1: return (Bridge.masterCutoff >= 64 ? "+" : "") + (Bridge.masterCutoff - 64);
                    case 2: return (Bridge.masterReso >= 64 ? "+" : "") + (Bridge.masterReso - 64);
                    case 3: return (Bridge.masterAttack >= 64 ? "+" : "") + (Bridge.masterAttack - 64);
                    case 4: return (Bridge.masterRelease >= 64 ? "+" : "") + (Bridge.masterRelease - 64);
                    case 5: return Bridge.tone1Level.toString();
                    case 6: return Bridge.tone2Level.toString();
                    case 7: return Bridge.tone3Level.toString();
                    case 8: return Bridge.tone4Level.toString();
                }
            } else if (currentView === "PERF MIXER") {
                return Math.round(card.internalVal * 127).toString();
            } else if (currentView === "EFFECTS") {
                if (knobIndex === 1) return Math.round(1 + card.internalVal * 78).toString();
                return Math.round(card.internalVal * 127).toString();
            }
            return "64";
        }

        // Apply updated normalized value (0.0 .. 1.0)
        function applyNormValue(nv: real) {
            const clamped = Math.max(0.0, Math.min(1.0, nv));
            card.internalVal = clamped;

            if (currentView === "VECTOR") {
                if (knobIndex === 1) Bridge.setCoordinates(clamped, Bridge.vectorY);
                else if (knobIndex === 2) Bridge.setCoordinates(Bridge.vectorX, clamped);
                else if (knobIndex === 3) Bridge.setOrbitAttractor(clamped, Bridge.attractorY);
                else if (knobIndex === 4) Bridge.setOrbitAttractor(Bridge.attractorX, clamped);
                else if (knobIndex === 5) Bridge.setSpeed(0.25 + clamped * 1.75);
                else if (knobIndex === 6) {
                    const autos = ["none", "circle", "lissajous", "chaos"];
                    const idx = Math.min(3, Math.floor(clamped * 4));
                    Bridge.setAutomator(autos[idx]);
                }
                else if (knobIndex === 7) Bridge.setCurve(clamped < 0.5 ? "linear" : "equal_power");
                else if (knobIndex === 8) Bridge.setBpm(20 + clamped * 280);
            } else if (currentView === "WAVETABLE") {
                if (knobIndex === 1) Bridge.setWavetablePos(clamped);
                else if (knobIndex === 2) Bridge.setSpeed(0.25 + clamped * 1.75);
                else if (knobIndex === 3) {
                    const sweeps = ["manual", "sine", "triangle", "ramp", "random_step"];
                    const idx = Math.min(4, Math.floor(clamped * 5));
                    Bridge.setWavetableSweepMode(sweeps[idx]);
                }
                else if (knobIndex === 4) Bridge.setCurve(clamped < 0.5 ? "linear" : "equal_power");
                else if (knobIndex >= 5 && knobIndex <= 8) {
                    Bridge.setToneLevel(knobIndex - 4, Math.round(clamped * 127));
                }
            } else if (currentView === "MACROS") {
                Bridge.setMacro(knobIndex, Math.round(clamped * 127));
            } else if (currentView === "PATCH EDIT") {
                if (knobIndex === 1) Bridge.setMasterCutoff(Math.round(1 + clamped * 126));
                else if (knobIndex === 2) Bridge.setMasterReso(Math.round(1 + clamped * 126));
                else if (knobIndex === 3) Bridge.setMasterAttack(Math.round(1 + clamped * 126));
                else if (knobIndex === 4) Bridge.setMasterRelease(Math.round(1 + clamped * 126));
                else if (knobIndex >= 5 && knobIndex <= 8) {
                    Bridge.setToneLevel(knobIndex - 4, Math.round(clamped * 127));
                }
            }
        }

        // Header: Knob tag + Param Name (Zero-overhead anchored positioning)
        Item {
            id: headerRow
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: ScaleMetrics.dp(4)
            height: ScaleMetrics.dp(14)

            Rectangle {
                id: tagBadge
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                width: ScaleMetrics.dp(18)
                height: ScaleMetrics.dp(14)
                radius: ScaleMetrics.dp(3)
                color: Theme.bgCardActive

                Text {
                    anchors.centerIn: parent
                    text: "K" + card.knobIndex
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: Theme.tone1
                }
            }

            Text {
                anchors.left: tagBadge.right
                anchors.right: parent.right
                anchors.leftMargin: ScaleMetrics.dp(4)
                anchors.verticalCenter: parent.verticalCenter
                text: card.paramName
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(9)
                color: Theme.textSecondary
                elide: Text.ElideRight
            }
        }

        // Numeric Readout Value
        Text {
            anchors.top: headerRow.bottom
            anchors.bottom: barBg.top
            anchors.left: parent.left
            anchors.right: parent.right
            text: card.displayString
            font.bold: true
            font.pixelSize: ScaleMetrics.sp(11)
            font.family: Theme.fontMono
            color: Theme.textPrimary
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }

        // Progress bar / meter indicator
        Rectangle {
            id: barBg
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: ScaleMetrics.dp(4)
            height: ScaleMetrics.dp(4)
            radius: ScaleMetrics.dp(2)
            color: "#1e293b"
            clip: true

            Rectangle {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                width: parent.width * Math.max(0.0, Math.min(1.0, card.normValue))
                radius: ScaleMetrics.dp(2)
                color: card.knobIndex <= 4 ? Theme.tone1 : Theme.tone3
            }
        }

        // Direct Touch and Drag Interaction
        MouseArea {
            id: mouseArea
            anchors.fill: parent
            property real startX: 0
            property real startY: 0
            property real startNorm: 0

            onPressed: (mouse) => {
                startX = mouse.x;
                startY = mouse.y;
                startNorm = card.getNormValue();
                card.applyNormValue(mouse.x / width);
            }

            onPositionChanged: (mouse) => {
                if (pressed) {
                    const dx = mouse.x - startX;
                    const dy = startY - mouse.y;
                    if (Math.abs(dy) > Math.abs(dx) * 1.2) {
                        card.applyNormValue(startNorm + dy / ScaleMetrics.dp(70));
                    } else {
                        card.applyNormValue(mouse.x / width);
                    }
                }
            }
        }
    }
}
