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
    property string selectedSsid: ""
    property string wifiPassword: ""
    property string wifiActiveField: "password" // "ssid" | "password"
    property bool wifiShowPassword: false

    function wifiSecurityFor(ssid) {
        var nets = Bridge.wifiNetworks;
        for (var i = 0; i < nets.length; i++) {
            if (nets[i].ssid === ssid)
                return nets[i].security || "";
        }
        return "";
    }
    function wifiIsOpen(ssid) {
        var sec = root.wifiSecurityFor(ssid);
        return sec === "" || sec === "OPEN" || sec === "--";
    }

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

                    // Restart App Button (Safe, Graceful Restart - two-tap confirm)
                    Rectangle {
                        id: restartBtn
                        property bool confirmAction: false
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(36)
                        radius: ScaleMetrics.dp(4)
                        color: restartBtn.confirmAction ? "#1e3a2f" : (restartMouse.pressed ? Theme.bgCardActive : "#161d2b")
                        border.color: restartBtn.confirmAction ? "#10b981" : Theme.tone1
                        border.width: 1

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: 6
                            Text { text: restartBtn.confirmAction ? "⚠" : "↻"; font.bold: true; font.pixelSize: ScaleMetrics.sp(14); color: restartBtn.confirmAction ? "#10b981" : Theme.tone1 }
                            Text { text: restartBtn.confirmAction ? "TAP AGAIN TO RESTART" : "RESTART APPLICATION"; font.bold: true; font.pixelSize: ScaleMetrics.sp(9); color: restartBtn.confirmAction ? "#10b981" : Theme.tone1 }
                        }
                        Timer { id: restartReset; interval: 3000; onTriggered: restartBtn.confirmAction = false }
                        MouseArea {
                            id: restartMouse
                            anchors.fill: parent
                            onClicked: {
                                if (!restartBtn.confirmAction) { restartBtn.confirmAction = true; restartReset.restart(); }
                                else { restartBtn.confirmAction = false; Bridge.restartApp(); }
                            }
                        }
                    }

                    // Quit App Button (graceful exit to desktop - two-tap confirm)
                    Rectangle {
                        id: quitBtn
                        property bool confirmAction: false
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(36)
                        radius: ScaleMetrics.dp(4)
                        color: quitBtn.confirmAction ? "#1e3a2f" : (quitMouse.pressed ? Theme.bgCardActive : "#161d2b")
                        border.color: quitBtn.confirmAction ? "#10b981" : Theme.borderCard
                        border.width: 1

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: 6
                            Text { text: quitBtn.confirmAction ? "⚠" : "✕"; font.bold: true; font.pixelSize: ScaleMetrics.sp(12); color: quitBtn.confirmAction ? "#10b981" : Theme.textSecondary }
                            Text { text: quitBtn.confirmAction ? "TAP AGAIN TO QUIT" : "QUIT APPLICATION"; font.bold: true; font.pixelSize: ScaleMetrics.sp(9); color: quitBtn.confirmAction ? "#10b981" : Theme.textSecondary }
                        }
                        Timer { id: quitReset; interval: 3000; onTriggered: quitBtn.confirmAction = false }
                        MouseArea {
                            id: quitMouse
                            anchors.fill: parent
                            onClicked: {
                                if (!quitBtn.confirmAction) { quitBtn.confirmAction = true; quitReset.restart(); }
                                else { quitBtn.confirmAction = false; Bridge.quitApp(); }
                            }
                        }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderCard }

                    // Reboot System Button (two-tap confirm -> systemctl reboot)
                    Rectangle {
                        id: rebootBtn
                        property bool confirmAction: false
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(36)
                        radius: ScaleMetrics.dp(4)
                        color: rebootBtn.confirmAction ? "#451a1a" : (rebootMouse.pressed ? "#451a1a" : "#10141d")
                        border.color: rebootBtn.confirmAction ? Theme.recording : Theme.borderCard
                        border.width: 1

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: 6
                            Text { text: rebootBtn.confirmAction ? "⚠" : "⚡"; font.bold: true; font.pixelSize: ScaleMetrics.sp(12); color: rebootBtn.confirmAction ? Theme.recording : Theme.textSecondary }
                            Text { text: rebootBtn.confirmAction ? "TAP AGAIN TO REBOOT" : "REBOOT WORKSTATION (PI)"; font.bold: true; font.pixelSize: ScaleMetrics.sp(9); color: rebootBtn.confirmAction ? Theme.recording : Theme.textSecondary }
                        }
                        Timer { id: rebootReset; interval: 3000; onTriggered: rebootBtn.confirmAction = false }
                        MouseArea {
                            id: rebootMouse
                            anchors.fill: parent
                            onClicked: {
                                if (!rebootBtn.confirmAction) { rebootBtn.confirmAction = true; rebootReset.restart(); }
                                else { rebootBtn.confirmAction = false; Bridge.rebootSystem(); }
                            }
                        }
                    }

                    // Shutdown System Button (two-tap confirm -> systemctl poweroff)
                    Rectangle {
                        id: shutBtn
                        property bool confirmAction: false
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(36)
                        radius: ScaleMetrics.dp(4)
                        color: shutBtn.confirmAction ? "#591c1c" : (shutMouse.pressed ? "#591c1c" : "#1a1215")
                        border.color: Theme.recording
                        border.width: 1

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: 6
                            Text { text: shutBtn.confirmAction ? "⚠" : "⏻"; font.bold: true; font.pixelSize: ScaleMetrics.sp(12); color: Theme.recording }
                            Text { text: shutBtn.confirmAction ? "TAP AGAIN TO SHUTDOWN" : "SAFE SHUTDOWN"; font.bold: true; font.pixelSize: ScaleMetrics.sp(9); color: Theme.recording }
                        }
                        Timer { id: shutReset; interval: 3000; onTriggered: shutBtn.confirmAction = false }
                        MouseArea {
                            id: shutMouse
                            anchors.fill: parent
                            onClicked: {
                                if (!shutBtn.confirmAction) { shutBtn.confirmAction = true; shutReset.restart(); }
                                else { shutBtn.confirmAction = false; Bridge.shutdownSystem(); }
                            }
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

                    StatBar { label: "CPU LOAD"; stat: Bridge.cpuLoadText; norm: Bridge.cpuLoadNorm; color: Theme.tone1 }
                    StatBar { label: "CPU TEMPERATURE"; stat: Bridge.cpuTempText; norm: Bridge.cpuTempNorm; color: "#10b981" }
                    StatBar { label: "RAM ALLOCATION"; stat: Bridge.ramText; norm: Bridge.ramNorm; color: Theme.tone2 }
                    StatBar { label: "EMMC DISK SPACE"; stat: Bridge.diskText; norm: Bridge.diskNorm; color: Theme.tone3 }

                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderCard }

                    Text { text: "MIDI & CONTROL LINK"; font.bold: true; font.pixelSize: ScaleMetrics.sp(9); color: Theme.textDim }
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "CONTROL RATE:"; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textDim }
                        Item { Layout.fillWidth: true }
                        Text { text: Bridge.controlRateText; font.family: Theme.fontMono; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textPrimary }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "SYNTH LINK:"; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textDim }
                        Item { Layout.fillWidth: true }
                        Text { text: Bridge.midiLinkText; font.family: Theme.fontMono; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: "#10b981" }
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

                    // Wi-Fi Status Bar (live: Bridge.wifi* via NetworkManager)
                    Rectangle {
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(44)
                        radius: 4
                        color: "#10141d"
                        border.color: Bridge.wifiConnected ? "#10b981" : Theme.borderCard
                        border.width: 1

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: ScaleMetrics.dp(8)
                            spacing: ScaleMetrics.dp(6)
                            Text {
                                text: "📶"
                                font.pixelSize: ScaleMetrics.sp(14)
                                opacity: Bridge.wifiConnected ? 1.0 : 0.45
                            }
                            ColumnLayout {
                                spacing: 1
                                Layout.fillWidth: true
                                Text {
                                    text: Bridge.wifiConnected
                                        ? ("WI-FI: " + Bridge.wifiSsid)
                                        : ("WI-FI: " + Bridge.wifiStatusText)
                                    font.bold: true
                                    font.pixelSize: ScaleMetrics.sp(9)
                                    color: Theme.textPrimary
                                    elide: Text.ElideRight
                                }
                                Text {
                                    text: Bridge.wifiDetailText
                                    font.pixelSize: ScaleMetrics.sp(7)
                                    color: Bridge.wifiConnected ? "#10b981" : Theme.textDim
                                    elide: Text.ElideRight
                                }
                            }
                            Rectangle {
                                width: ScaleMetrics.dp(26)
                                height: ScaleMetrics.dp(24)
                                radius: 3
                                color: refMouse.pressed ? Theme.bgCardActive : "#10141d"
                                border.color: Theme.borderCard
                                border.width: 1
                                opacity: Bridge.wifiBusy ? 0.4 : 1.0
                                Text { anchors.centerIn: parent; text: "↻"; font.bold: true; font.pixelSize: ScaleMetrics.sp(11); color: Theme.textSecondary }
                                MouseArea {
                                    id: refMouse
                                    anchors.fill: parent
                                    enabled: !Bridge.wifiBusy
                                    onClicked: Bridge.refreshWifiStatus()
                                }
                            }
                            Rectangle {
                                width: ScaleMetrics.dp(60)
                                height: ScaleMetrics.dp(24)
                                radius: 3
                                color: Theme.bgCardActive
                                border.color: "#60a5fa"
                                border.width: 1
                                Text { anchors.centerIn: parent; text: "MANAGE"; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: "#60a5fa" }
                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: {
                                        if (root.selectedSsid === "" && Bridge.wifiSsid !== "")
                                            root.selectedSsid = Bridge.wifiSsid;
                                        root.showWifiModal = true;
                                    }
                                }
                            }
                        }
                    }

                    // Wi-Fi quick actions: radio toggle / rescan / disconnect
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: ScaleMetrics.dp(6)
                        opacity: Bridge.wifiBusy ? 0.55 : 1.0

                        Rectangle {
                            Layout.fillWidth: true
                            height: ScaleMetrics.dp(24)
                            radius: 3
                            color: "#10141d"
                            border.color: Bridge.wifiEnabled ? "#10b981" : Theme.borderCard
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: Bridge.wifiEnabled ? "RADIO: ON" : "RADIO: OFF"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(7)
                                color: Bridge.wifiEnabled ? "#10b981" : Theme.textDim
                            }
                            MouseArea {
                                anchors.fill: parent
                                enabled: !Bridge.wifiBusy && Bridge.wifiAvailable
                                onClicked: Bridge.setWifiEnabled(!Bridge.wifiEnabled)
                            }
                        }
                        Rectangle {
                            Layout.fillWidth: true
                            height: ScaleMetrics.dp(24)
                            radius: 3
                            color: "#10141d"
                            border.color: Theme.borderCard
                            border.width: 1
                            Text { anchors.centerIn: parent; text: "RESCAN"; font.bold: true; font.pixelSize: ScaleMetrics.sp(7); color: Theme.textSecondary }
                            MouseArea {
                                anchors.fill: parent
                                enabled: !Bridge.wifiBusy && Bridge.wifiEnabled
                                onClicked: Bridge.scanWifi(true)
                            }
                        }
                        Rectangle {
                            Layout.fillWidth: true
                            height: ScaleMetrics.dp(24)
                            radius: 3
                            visible: Bridge.wifiConnected
                            color: "#10141d"
                            border.color: Theme.recording
                            border.width: 1
                            Text { anchors.centerIn: parent; text: "DISCONNECT"; font.bold: true; font.pixelSize: ScaleMetrics.sp(7); color: Theme.recording }
                            MouseArea {
                                anchors.fill: parent
                                enabled: !Bridge.wifiBusy
                                onClicked: Bridge.disconnectWifi()
                            }
                        }
                        Text {
                            visible: Bridge.wifiBusy
                            text: "WORKING…"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(7)
                            color: "#60a5fa"
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
                                    text: "$ uname -a\nLinux juno-spectre-pi 6.1.21-v8+ aarch64\n$ git describe --tags\n" + Bridge.version + "\n" + Bridge.updaterLog
                                    font.family: Theme.fontMono
                                    font.pixelSize: ScaleMetrics.sp(8)
                                    color: "#6ee7b7"
                                }
                            }

                            // Check for Releases Button
                            Rectangle {
                                Layout.fillWidth: true
                                height: ScaleMetrics.dp(28)
                                radius: 3
                                color: Bridge.updaterBusy ? "#10141d" : (updMouse.pressed ? Theme.bgCardActive : "#10141d")
                                border.color: "#60a5fa"
                                border.width: 1
                                opacity: Bridge.updaterBusy ? 0.5 : 1.0
                                Text {
                                    anchors.centerIn: parent
                                    text: Bridge.updaterBusy ? "CONTACTING RELEASE CHANNEL..." : "CHECK FOR SPECTRE RELEASES"
                                    font.bold: true
                                    font.pixelSize: ScaleMetrics.sp(8)
                                    color: "#60a5fa"
                                }
                                MouseArea {
                                    id: updMouse
                                    anchors.fill: parent
                                    enabled: !Bridge.updaterBusy
                                    onClicked: Bridge.checkForUpdates()
                                }
                            }

                            // Install Latest Release Button (toggles to RESTART when done)
                            Rectangle {
                                Layout.fillWidth: true
                                height: ScaleMetrics.dp(28)
                                radius: 3
                                visible: Bridge.updateAvailable || Bridge.updateApplied
                                color: instMouse.pressed ? "#14532d" : "#10141d"
                                border.color: "#10b981"
                                border.width: 1
                                Text {
                                    anchors.centerIn: parent
                                    text: Bridge.updateApplied
                                        ? "RESTART NOW TO RUN " + Bridge.version
                                        : "INSTALL RELEASE " + Bridge.latestVersion
                                    font.bold: true
                                    font.pixelSize: ScaleMetrics.sp(8)
                                    color: "#10b981"
                                }
                                MouseArea {
                                    id: instMouse
                                    anchors.fill: parent
                                    enabled: !Bridge.updaterBusy
                                    onClicked: {
                                        if (Bridge.updateApplied)
                                            Bridge.restartApp();
                                        else
                                            Bridge.applyLatestRelease();
                                    }
                                }
                            }

                            // Rollback to Previous Release Button
                            Rectangle {
                                Layout.fillWidth: true
                                height: ScaleMetrics.dp(28)
                                radius: 3
                                color: rbMouse.pressed ? "#451a1a" : "#10141d"
                                border.color: Theme.borderCard
                                border.width: 1
                                Text {
                                    anchors.centerIn: parent
                                    text: "ROLLBACK TO PREVIOUS RELEASE"
                                    font.bold: true
                                    font.pixelSize: ScaleMetrics.sp(8)
                                    color: Theme.textSecondary
                                }
                                MouseArea {
                                    id: rbMouse
                                    anchors.fill: parent
                                    enabled: !Bridge.updaterBusy
                                    onClicked: Bridge.rollbackRelease()
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // Wi-Fi Manager Modal: live scan list + connect / disconnect / forget + radio
    Rectangle {
        visible: root.showWifiModal
        anchors.fill: parent
        color: "#e6080b11"
        z: 99
        onVisibleChanged: {
            if (visible) {
                root.wifiPassword = "";
                root.wifiShowPassword = false;
                root.wifiActiveField = "password";
                if (root.selectedSsid === "" && Bridge.wifiSsid !== "")
                    root.selectedSsid = Bridge.wifiSsid;
                Bridge.scanWifi(true);
            }
        }

        Rectangle {
            width: Math.min(parent.width - 24, ScaleMetrics.dp(840))
            height: Math.min(parent.height - 24, ScaleMetrics.dp(500))
            anchors.centerIn: parent
            radius: 8
            color: Theme.bgCard
            border.color: "#60a5fa"
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(10)
                spacing: ScaleMetrics.dp(6)

                // Header
                RowLayout {
                    Layout.fillWidth: true
                    spacing: ScaleMetrics.dp(6)
                    Text { text: "WI-FI NETWORKS"; font.bold: true; font.pixelSize: ScaleMetrics.sp(11); color: "#60a5fa" }
                    Text {
                        text: Bridge.wifiBusy ? "WORKING…" : ("SCAN: " + Bridge.wifiLastScan)
                        font.pixelSize: ScaleMetrics.sp(7)
                        color: Bridge.wifiBusy ? "#60a5fa" : Theme.textDim
                    }
                    Item { Layout.fillWidth: true }
                    Text {
                        text: Bridge.wifiStatusText
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Bridge.wifiConnected ? "#10b981" : Theme.textDim
                    }
                    Rectangle {
                        width: ScaleMetrics.dp(24); height: ScaleMetrics.dp(24); radius: 3; color: "#10141d"
                        border.color: Theme.borderCard; border.width: 1
                        Text { anchors.centerIn: parent; text: "✕"; color: Theme.textDim }
                        MouseArea { anchors.fill: parent; onClicked: root.showWifiModal = false }
                    }
                }

                // Live status + error lines
                Text {
                    Layout.fillWidth: true
                    text: Bridge.wifiDetailText
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: Bridge.wifiConnected ? "#10b981" : Theme.textSecondary
                    elide: Text.ElideRight
                }
                Text {
                    Layout.fillWidth: true
                    visible: Bridge.wifiError !== ""
                    text: "⚠ " + Bridge.wifiError
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: Theme.recording
                    wrapMode: Text.Wrap
                }

                // Radio + rescan controls
                RowLayout {
                    Layout.fillWidth: true
                    spacing: ScaleMetrics.dp(6)
                    opacity: Bridge.wifiBusy ? 0.55 : 1.0

                    Rectangle {
                        Layout.preferredWidth: ScaleMetrics.dp(130)
                        height: ScaleMetrics.dp(26)
                        radius: 3
                        color: "#10141d"
                        border.color: Bridge.wifiEnabled ? "#10b981" : Theme.borderCard
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: Bridge.wifiEnabled ? "RADIO: ON" : "RADIO: OFF"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: Bridge.wifiEnabled ? "#10b981" : Theme.textDim
                        }
                        MouseArea {
                            anchors.fill: parent
                            enabled: !Bridge.wifiBusy && Bridge.wifiAvailable
                            onClicked: Bridge.setWifiEnabled(!Bridge.wifiEnabled)
                        }
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(26)
                        radius: 3
                        color: rsMouse.pressed ? Theme.bgCardActive : "#10141d"
                        border.color: "#60a5fa"
                        border.width: 1
                        Text { anchors.centerIn: parent; text: Bridge.wifiBusy ? "SCANNING…" : "RESCAN NETWORKS"; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: "#60a5fa" }
                        MouseArea {
                            id: rsMouse
                            anchors.fill: parent
                            enabled: !Bridge.wifiBusy && Bridge.wifiEnabled
                            onClicked: Bridge.scanWifi(true)
                        }
                    }
                }

                // Body: network list (left) + connect panel (right)
                RowLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: ScaleMetrics.dp(8)

                    // Nearby networks
                    Rectangle {
                        Layout.preferredWidth: ScaleMetrics.dp(270)
                        Layout.fillHeight: true
                        radius: 4
                        color: "#080b11"
                        border.color: Theme.borderCard
                        border.width: 1

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: ScaleMetrics.dp(6)
                            spacing: ScaleMetrics.dp(4)

                            Text { text: "NEARBY (TAP TO SELECT)"; font.bold: true; font.pixelSize: ScaleMetrics.sp(7); color: Theme.textDim }

                            ListView {
                                id: wifiList
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                spacing: 4
                                model: Bridge.wifiNetworks
                                delegate: Rectangle {
                                    width: wifiList.width
                                    height: ScaleMetrics.dp(38)
                                    radius: 3
                                    color: modelData.ssid === root.selectedSsid
                                        ? "#1b2740"
                                        : (netMouse.pressed ? Theme.bgCardActive : "#10141d")
                                    border.color: modelData.inUse
                                        ? "#10b981"
                                        : (modelData.ssid === root.selectedSsid ? "#60a5fa" : Theme.borderCard)
                                    border.width: 1

                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: ScaleMetrics.dp(5)
                                        spacing: 0
                                        RowLayout {
                                            Layout.fillWidth: true
                                            spacing: 4
                                            Text {
                                                Layout.fillWidth: true
                                                text: (modelData.inUse ? "● " : "") + modelData.ssid
                                                font.bold: true
                                                font.pixelSize: ScaleMetrics.sp(9)
                                                color: modelData.inUse ? "#10b981" : Theme.textPrimary
                                                elide: Text.ElideRight
                                            }
                                            Text {
                                                text: modelData.secured ? "🔒" : "○"
                                                font.pixelSize: ScaleMetrics.sp(9)
                                            }
                                        }
                                        Text {
                                            text: modelData.signal + "% • " + modelData.quality + " • " + modelData.security
                                            font.pixelSize: ScaleMetrics.sp(7)
                                            color: Theme.textDim
                                            elide: Text.ElideRight
                                        }
                                    }
                                    MouseArea {
                                        id: netMouse
                                        anchors.fill: parent
                                        onClicked: {
                                            root.selectedSsid = modelData.ssid;
                                            root.wifiPassword = "";
                                            root.wifiActiveField = modelData.secured ? "password" : "ssid";
                                        }
                                    }
                                }
                            }

                            Text {
                                visible: Bridge.wifiNetworks.length === 0 && !Bridge.wifiBusy
                                text: Bridge.wifiEnabled ? "No networks yet — tap RESCAN." : "Radio is off."
                                font.pixelSize: ScaleMetrics.sp(7)
                                color: Theme.textDim
                                wrapMode: Text.Wrap
                            }
                        }
                    }

                    // Connect panel
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: ScaleMetrics.dp(4)

                        Text { text: "NETWORK (SSID — EDITABLE FOR HIDDEN NETS)"; font.bold: true; font.pixelSize: ScaleMetrics.sp(7); color: Theme.textDim }
                        Rectangle {
                            Layout.fillWidth: true
                            height: ScaleMetrics.dp(30)
                            radius: 4
                            color: "#080b11"
                            border.color: root.wifiActiveField === "ssid" ? "#60a5fa" : Theme.borderCard
                            border.width: 1
                            TextInput {
                                id: ssidField
                                anchors.fill: parent
                                anchors.margins: ScaleMetrics.dp(6)
                                text: root.selectedSsid
                                maximumLength: 32
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(10)
                                color: Theme.textPrimary
                                clip: true
                                onTextEdited: root.selectedSsid = text
                                onActiveFocusChanged: if (activeFocus) root.wifiActiveField = "ssid"
                            }
                            MouseArea {
                                anchors.fill: parent
                                onClicked: { root.wifiActiveField = "ssid"; ssidField.forceActiveFocus(); }
                            }
                        }

                        Text { text: "PASSWORD / PASSPHRASE"; font.bold: true; font.pixelSize: ScaleMetrics.sp(7); color: Theme.textDim }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: ScaleMetrics.dp(6)
                            Rectangle {
                                Layout.fillWidth: true
                                height: ScaleMetrics.dp(30)
                                radius: 4
                                color: "#080b11"
                                border.color: root.wifiActiveField === "password" ? "#60a5fa" : Theme.borderCard
                                border.width: 1
                                TextInput {
                                    id: passField
                                    anchors.fill: parent
                                    anchors.margins: ScaleMetrics.dp(6)
                                    text: root.wifiPassword
                                    maximumLength: 63
                                    font.pixelSize: ScaleMetrics.sp(10)
                                    color: Theme.textPrimary
                                    clip: true
                                    echoMode: root.wifiShowPassword ? TextInput.Normal : TextInput.Password
                                    passwordCharacter: "•"
                                    onTextEdited: root.wifiPassword = text
                                    onActiveFocusChanged: if (activeFocus) root.wifiActiveField = "password"
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: { root.wifiActiveField = "password"; passField.forceActiveFocus(); }
                                }
                            }
                            Rectangle {
                                Layout.preferredWidth: ScaleMetrics.dp(52)
                                height: ScaleMetrics.dp(30)
                                radius: 3
                                color: "#10141d"
                                border.color: Theme.borderCard
                                border.width: 1
                                Text { anchors.centerIn: parent; text: root.wifiShowPassword ? "HIDE" : "SHOW"; font.bold: true; font.pixelSize: ScaleMetrics.sp(7); color: Theme.textSecondary }
                                MouseArea { anchors.fill: parent; onClicked: root.wifiShowPassword = !root.wifiShowPassword }
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            text: root.selectedSsid === ""
                                ? "Pick a network on the left, or type a hidden SSID above."
                                : (root.wifiIsOpen(root.selectedSsid)
                                    ? "Open network — just tap CONNECT."
                                    : ("Security: " + root.wifiSecurityFor(root.selectedSsid) + " — enter the passphrase."))
                            font.pixelSize: ScaleMetrics.sp(7)
                            color: Theme.textDim
                            elide: Text.ElideRight
                        }

                        // Connect button
                        Rectangle {
                            Layout.fillWidth: true
                            height: ScaleMetrics.dp(30)
                            radius: 3
                            color: connMouse.pressed ? "#14532d" : "#10141d"
                            border.color: "#10b981"
                            border.width: 1
                            opacity: (root.selectedSsid === "" || Bridge.wifiBusy) ? 0.45 : 1.0
                            Text {
                                anchors.centerIn: parent
                                text: Bridge.wifiBusy
                                    ? "WORKING…"
                                    : (root.selectedSsid === "" ? "SELECT A NETWORK" : "CONNECT TO " + root.selectedSsid)
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(8)
                                color: "#10b981"
                            }
                            MouseArea {
                                id: connMouse
                                anchors.fill: parent
                                enabled: root.selectedSsid !== "" && !Bridge.wifiBusy
                                onClicked: {
                                    Bridge.connectWifi(root.selectedSsid, root.wifiPassword);
                                    root.wifiPassword = "";
                                }
                            }
                        }

                        // Disconnect + forget
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: ScaleMetrics.dp(6)
                            Rectangle {
                                Layout.fillWidth: true
                                height: ScaleMetrics.dp(26)
                                radius: 3
                                visible: Bridge.wifiConnected
                                color: "#10141d"
                                border.color: Theme.recording
                                border.width: 1
                                opacity: Bridge.wifiBusy ? 0.45 : 1.0
                                Text { anchors.centerIn: parent; text: "DISCONNECT"; font.bold: true; font.pixelSize: ScaleMetrics.sp(7); color: Theme.recording }
                                MouseArea {
                                    anchors.fill: parent
                                    enabled: !Bridge.wifiBusy
                                    onClicked: Bridge.disconnectWifi()
                                }
                            }
                            Rectangle {
                                Layout.fillWidth: true
                                height: ScaleMetrics.dp(26)
                                radius: 3
                                color: "#10141d"
                                border.color: Theme.borderCard
                                border.width: 1
                                opacity: (root.selectedSsid === "" || Bridge.wifiBusy) ? 0.45 : 1.0
                                Text { anchors.centerIn: parent; text: "FORGET SAVED"; font.bold: true; font.pixelSize: ScaleMetrics.sp(7); color: Theme.textSecondary }
                                MouseArea {
                                    anchors.fill: parent
                                    enabled: root.selectedSsid !== "" && !Bridge.wifiBusy
                                    onClicked: Bridge.forgetWifi(root.selectedSsid)
                                }
                            }
                        }

                        // Touch keyboard (case + symbols enabled for passphrases)
                        VirtualKeyboard {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            accentColor: "#60a5fa"
                            allowLower: true
                            allowSymbols: true
                            onKeyClicked: (k) => {
                                if (root.wifiActiveField === "ssid") {
                                    if (root.selectedSsid.length < 32) root.selectedSsid += k;
                                } else {
                                    if (root.wifiPassword.length < 63) root.wifiPassword += k;
                                }
                            }
                            onBackspaceClicked: {
                                if (root.wifiActiveField === "ssid") root.selectedSsid = root.selectedSsid.slice(0, -1);
                                else root.wifiPassword = root.wifiPassword.slice(0, -1);
                            }
                            onClearClicked: {
                                if (root.wifiActiveField === "ssid") root.selectedSsid = "";
                                else root.wifiPassword = "";
                            }
                            onCloseClicked: root.showWifiModal = false
                        }
                    }
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
