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

    property bool showWifiModal: false
    property string selectedSsid: "Studio-5GHz"
    property string wifiPassword: ""
    property string updateStatus: "SYSTEM READY • VERSION 1.4.2 (RELEASE)"

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: ScaleMetrics.dp(10)
        spacing: ScaleMetrics.dp(8)

        // Header
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(8)

            Rectangle {
                width: ScaleMetrics.dp(8); height: ScaleMetrics.dp(8); radius: 4
                color: "#ef4444"
            }
            Text {
                text: "SYSTEM & APPLIANCE CONTROL PANEL"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(12)
                font.letterSpacing: 1.2
                color: Theme.textPrimary
            }
            Item { Layout.fillWidth: true }
            Text {
                text: "RASPBERRY PI / EMBEDDED LINUX HOST"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(9)
                color: Theme.textDim
            }
        }

        // 3 Cards: Appliance Actions & Display, Telemetry, Wi-Fi & Updates
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: ScaleMetrics.dp(10)

            // Card 1: Appliance & Power Controls (~300dp)
            Rectangle {
                Layout.preferredWidth: ScaleMetrics.dp(300)
                Layout.fillHeight: true
                radius: ScaleMetrics.dp(6)
                color: Theme.bgApp
                border.color: Theme.borderCard
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(12)
                    spacing: ScaleMetrics.dp(10)

                    Text { text: "APPLIANCE & POWER"; font.bold: true; font.pixelSize: ScaleMetrics.sp(10); color: "#ef4444" }

                    // Display Brightness Slider
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "DISPLAY BRIGHTNESS"; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textDim }
                            Item { Layout.fillWidth: true }
                            Text { text: Bridge.brightness.toString() + "%"; font.family: Theme.fontMono; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textPrimary }
                        }
                        Rectangle {
                            Layout.fillWidth: true
                            height: ScaleMetrics.dp(24)
                            radius: 3
                            color: "#10141d"
                            border.color: Theme.borderCard
                            border.width: 1
                            Rectangle {
                                width: parent.width * (Bridge.brightness / 100.0)
                                height: parent.height
                                radius: 3
                                color: Qt.rgba(0.94, 0.27, 0.27, 0.35)
                            }
                            MouseArea {
                                anchors.fill: parent
                                onPositionChanged: (mouse) => {
                                    if (pressed) Bridge.setBrightness(Math.max(10, Math.min(100, Math.round((mouse.x / width) * 100))));
                                }
                                onPressed: (mouse) => {
                                    Bridge.setBrightness(Math.max(10, Math.min(100, Math.round((mouse.x / width) * 100))));
                                }
                            }
                        }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderCard }

                    // Restart App Button (Safe, Fast Restart)
                    Rectangle {
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(36)
                        radius: ScaleMetrics.dp(4)
                        color: restartMouse.pressed ? Theme.bgCardActive : "#161d2b"
                        border.color: Theme.tone1
                        border.width: 1

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: 6
                            Text { text: "↻"; font.bold: true; font.pixelSize: ScaleMetrics.sp(14); color: Theme.tone1 }
                            Text { text: "RESTART APPLICATION"; font.bold: true; font.pixelSize: ScaleMetrics.sp(9); color: Theme.tone1 }
                        }
                        MouseArea {
                            id: restartMouse
                            anchors.fill: parent
                            onClicked: Bridge.restartApp()
                        }
                    }

                    // Reboot System Button
                    Rectangle {
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(36)
                        radius: ScaleMetrics.dp(4)
                        color: rebootMouse.pressed ? "#451a1a" : "#10141d"
                        border.color: Theme.borderCard
                        border.width: 1

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: 6
                            Text { text: "⚡"; font.bold: true; font.pixelSize: ScaleMetrics.sp(12); color: Theme.textSecondary }
                            Text { text: "REBOOT WORKSTATION (PI)"; font.bold: true; font.pixelSize: ScaleMetrics.sp(9); color: Theme.textSecondary }
                        }
                        MouseArea {
                            id: rebootMouse
                            anchors.fill: parent
                        }
                    }

                    // Shutdown System Button
                    Rectangle {
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(36)
                        radius: ScaleMetrics.dp(4)
                        color: shutMouse.pressed ? "#591c1c" : "#1a1215"
                        border.color: Theme.recording
                        border.width: 1

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: 6
                            Text { text: "⏻"; font.bold: true; font.pixelSize: ScaleMetrics.sp(12); color: Theme.recording }
                            Text { text: "SAFE SHUTDOWN"; font.bold: true; font.pixelSize: ScaleMetrics.sp(9); color: Theme.recording }
                        }
                        MouseArea {
                            id: shutMouse
                            anchors.fill: parent
                        }
                    }

                    Item { Layout.fillHeight: true }
                }
            }

            // Card 2: Telemetry & Performance (~300dp)
            Rectangle {
                Layout.preferredWidth: ScaleMetrics.dp(300)
                Layout.fillHeight: true
                radius: ScaleMetrics.dp(6)
                color: Theme.bgApp
                border.color: Theme.borderCard
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(12)
                    spacing: ScaleMetrics.dp(8)

                    Text { text: "HARDWARE TELEMETRY"; font.bold: true; font.pixelSize: ScaleMetrics.sp(10); color: Theme.tone3 }

                    StatBar { label: "CPU LOAD"; stat: "14%"; norm: 0.14; color: Theme.tone1 }
                    StatBar { label: "CPU TEMPERATURE"; stat: "47.2 °C"; norm: 0.47; color: "#10b981" }
                    StatBar { label: "RAM ALLOCATION"; stat: "420 MB / 4096 MB"; norm: 0.10; color: Theme.tone2 }
                    StatBar { label: "EMMC DISK SPACE"; stat: "18.4 GB FREE"; norm: 0.65; color: Theme.tone3 }

                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderCard }

                    Text { text: "DSP & AUDIO LATENCY"; font.bold: true; font.pixelSize: ScaleMetrics.sp(9); color: Theme.textDim }
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "BUFFER SIZE:"; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textDim }
                        Item { Layout.fillWidth: true }
                        Text { text: "64 samples @ 44.1 kHz"; font.family: Theme.fontMono; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textPrimary }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "ROUNDTRIP LATENCY:"; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textDim }
                        Item { Layout.fillWidth: true }
                        Text { text: "1.45 ms (ALSA / JACK)"; font.family: Theme.fontMono; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: "#10b981" }
                    }

                    Item { Layout.fillHeight: true }
                }
            }

            // Card 3: Network & System Updates
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: ScaleMetrics.dp(6)
                color: Theme.bgApp
                border.color: Theme.borderCard
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(12)
                    spacing: ScaleMetrics.dp(8)

                    Text { text: "NETWORK & SYSTEM UPDATES"; font.bold: true; font.pixelSize: ScaleMetrics.sp(10); color: "#60a5fa" }

                    // Wi-Fi Status Bar
                    Rectangle {
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(40)
                        radius: 4
                        color: "#10141d"
                        border.color: Theme.borderCard
                        border.width: 1

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: ScaleMetrics.dp(8)
                            Text { text: "📶"; font.pixelSize: ScaleMetrics.sp(14) }
                            ColumnLayout {
                                spacing: 1
                                Text { text: "WI-FI: " + root.selectedSsid; font.bold: true; font.pixelSize: ScaleMetrics.sp(9); color: Theme.textPrimary }
                                Text { text: "IP: 192.168.1.140 • SIGNAL: -48 dBm (EXCELLENT)"; font.pixelSize: ScaleMetrics.sp(7); color: "#10b981" }
                            }
                            Item { Layout.fillWidth: true }
                            Rectangle {
                                width: ScaleMetrics.dp(60)
                                height: ScaleMetrics.dp(24)
                                radius: 3
                                color: Theme.bgCardActive
                                border.color: "#60a5fa"
                                border.width: 1
                                Text { anchors.centerIn: parent; text: "MANAGE"; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: "#60a5fa" }
                                MouseArea { anchors.fill: parent; onClicked: root.showWifiModal = true }
                            }
                        }
                    }

                    // System Update Terminal Box
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: 4
                        color: "#080b11"
                        border.color: Theme.borderCard
                        border.width: 1

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: ScaleMetrics.dp(8)
                            spacing: 4

                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "TERMINAL / APT UPDATER"; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textDim }
                                Item { Layout.fillWidth: true }
                                Text { text: "JUNO-SPECTRE-OS"; font.family: Theme.fontMono; font.pixelSize: ScaleMetrics.sp(7); color: Theme.tone1 }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                radius: 2
                                color: "#040609"
                                border.color: "#151b27"
                                border.width: 1
                                Text {
                                    anchors.fill: parent
                                    anchors.margins: 4
                                    text: "$ uname -a\nLinux juno-spectre-pi 6.1.21-v8+ aarch64\n$ apt-check: 0 updates available\n" + root.updateStatus
                                    font.family: Theme.fontMono
                                    font.pixelSize: ScaleMetrics.sp(8)
                                    color: "#6ee7b7"
                                }
                            }

                            // Check Updates Button
                            Rectangle {
                                Layout.fillWidth: true
                                height: ScaleMetrics.dp(28)
                                radius: 3
                                color: updMouse.pressed ? Theme.bgCardActive : "#10141d"
                                border.color: "#60a5fa"
                                border.width: 1
                                Text {
                                    anchors.centerIn: parent
                                    text: "CHECK FOR OS & SPECTRE UPDATES"
                                    font.bold: true
                                    font.pixelSize: ScaleMetrics.sp(8)
                                    color: "#60a5fa"
                                }
                                MouseArea {
                                    id: updMouse
                                    anchors.fill: parent
                                    onClicked: {
                                        root.updateStatus = "ALL SPECTRE PACKAGES UP TO DATE (OK)";
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // Wi-Fi Connect Modal Overlay with Virtual Keyboard
    Rectangle {
        visible: root.showWifiModal
        anchors.fill: parent
        color: "#e6080b11"
        z: 99

        Rectangle {
            width: Math.min(parent.width - 40, ScaleMetrics.dp(700))
            height: Math.min(parent.height - 40, ScaleMetrics.dp(440))
            anchors.centerIn: parent
            radius: 8
            color: Theme.bgCard
            border.color: "#60a5fa"
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 6

                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "CONNECT TO WI-FI NETWORK: " + root.selectedSsid; font.bold: true; font.pixelSize: ScaleMetrics.sp(11); color: "#60a5fa" }
                    Item { Layout.fillWidth: true }
                    Rectangle {
                        width: 24; height: 24; radius: 3; color: "#10141d"
                        Text { anchors.centerIn: parent; text: "✕"; color: Theme.textDim }
                        MouseArea { anchors.fill: parent; onClicked: root.showWifiModal = false }
                    }
                }

                // Password Display
                Rectangle {
                    Layout.fillWidth: true
                    height: ScaleMetrics.dp(32)
                    radius: 4
                    color: "#080b11"
                    border.color: Theme.borderCard
                    border.width: 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 6
                        Text { text: "PASSWORD: "; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textDim }
                        Text {
                            text: root.wifiPassword.length > 0 ? "••••••••••••" : "(Type with on-screen keyboard)"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(9)
                            color: root.wifiPassword.length > 0 ? Theme.textPrimary : Theme.textDim
                        }
                    }
                }

                // Virtual Keyboard
                VirtualKeyboard {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    accentColor: "#60a5fa"
                    onKeyClicked: (k) => root.wifiPassword += k
                    onBackspaceClicked: root.wifiPassword = root.wifiPassword.slice(0, -1)
                    onClearClicked: root.wifiPassword = ""
                    onCloseClicked: root.showWifiModal = false
                }
            }
        }
    }

    component StatBar: ColumnLayout {
        id: sb
        property string label: "STAT"
        property string stat: "0"
        property real norm: 0.5
        property color color: Theme.primary
        Layout.fillWidth: true
        spacing: 2

        RowLayout {
            Layout.fillWidth: true
            Text { text: sb.label; font.bold: true; font.pixelSize: ScaleMetrics.sp(7); color: Theme.textDim }
            Item { Layout.fillWidth: true }
            Text { text: sb.stat; font.family: Theme.fontMono; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textPrimary }
        }

        Rectangle {
            Layout.fillWidth: true
            height: ScaleMetrics.dp(10)
            radius: 2
            color: "#10141d"
            Rectangle {
                width: parent.width * Math.max(0, Math.min(1.0, sb.norm))
                height: parent.height
                radius: 2
                color: sb.color
            }
        }
    }
}
