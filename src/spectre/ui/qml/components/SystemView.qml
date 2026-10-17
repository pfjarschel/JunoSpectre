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
                color: Theme.pageAccent
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

                    Text { text: "APPLIANCE & POWER"; font.bold: true; font.pixelSize: ScaleMetrics.sp(10); color: Theme.pageAccent }

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
                            color: Theme.bgControl
                            border.color: Theme.borderCard
                            border.width: 1
                            Rectangle {
                                width: parent.width * (Bridge.brightness / 100.0)
                                height: parent.height
                                radius: 3
                                color: Theme.tint(Theme.pageAccent, Theme.fillAlpha)
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
                        color: restartBtn.confirmAction ? Theme.tint(Theme.warning, 0.2) : (restartMouse.pressed ? Theme.bgCardActive : Theme.bgControl)
                        border.color: restartBtn.confirmAction ? Theme.warning : Theme.pageAccent
                        border.width: 1

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: 6
                            Icon { name: restartBtn.confirmAction ? "warning" : "restart"; size: 18; color: restartBtn.confirmAction ? Theme.warning : Theme.pageAccent }
                            Text { text: restartBtn.confirmAction ? "TAP AGAIN TO RESTART" : "RESTART APPLICATION"; font.bold: true; font.pixelSize: ScaleMetrics.sp(9); color: restartBtn.confirmAction ? Theme.warning : Theme.pageAccent }
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
                        color: quitBtn.confirmAction ? Theme.tint(Theme.warning, 0.2) : (quitMouse.pressed ? Theme.bgCardActive : Theme.bgControl)
                        border.color: quitBtn.confirmAction ? Theme.warning : Theme.borderCard
                        border.width: 1

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: 6
                            Icon { name: quitBtn.confirmAction ? "warning" : "close"; size: 16; color: quitBtn.confirmAction ? Theme.warning : Theme.textSecondary }
                            Text { text: quitBtn.confirmAction ? "TAP AGAIN TO QUIT" : "QUIT APPLICATION"; font.bold: true; font.pixelSize: ScaleMetrics.sp(9); color: quitBtn.confirmAction ? Theme.warning : Theme.textSecondary }
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
                        color: rebootBtn.confirmAction ? Theme.tint(Theme.recording, 0.25) : (rebootMouse.pressed ? Theme.tint(Theme.recording, 0.25) : Theme.bgControl)
                        border.color: rebootBtn.confirmAction ? Theme.recording : Theme.borderCard
                        border.width: 1

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: 6
                            Icon { name: rebootBtn.confirmAction ? "warning" : "reboot"; size: 16; color: rebootBtn.confirmAction ? Theme.recording : Theme.textSecondary }
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
                        color: shutBtn.confirmAction ? Theme.tint(Theme.recording, 0.3) : (shutMouse.pressed ? Theme.tint(Theme.recording, 0.3) : Theme.tint(Theme.recording, 0.08))
                        border.color: Theme.recording
                        border.width: 1

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: 6
                            Icon { name: shutBtn.confirmAction ? "warning" : "power"; size: 16; color: Theme.recording }
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

                    Text { text: "HARDWARE TELEMETRY"; font.bold: true; font.pixelSize: ScaleMetrics.sp(10); color: Theme.pageAccent }

                    StatBar { label: "CPU LOAD"; stat: Bridge.cpuLoadText; norm: Bridge.cpuLoadNorm; color: Theme.pageAccent }
                    StatBar { label: "CPU TEMPERATURE"; stat: Bridge.cpuTempText; norm: Bridge.cpuTempNorm; color: Theme.pageAccent }
                    StatBar { label: "RAM ALLOCATION"; stat: Bridge.ramText; norm: Bridge.ramNorm; color: Theme.pageAccent }
                    StatBar { label: "EMMC DISK SPACE"; stat: Bridge.diskText; norm: Bridge.diskNorm; color: Theme.pageAccent }

                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderCard }

                    Text { text: "MIDI & CONTROL LINK"; font.bold: true; font.pixelSize: ScaleMetrics.sp(9); color: Theme.textDim }
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "SYSEX RATE:"; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textDim }
                        Item { Layout.fillWidth: true }
                        Text { text: Bridge.sysexRateText; font.family: Theme.fontMono; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textPrimary }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "SYNTH LINK:"; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textDim }
                        Item { Layout.fillWidth: true }
                        Text { text: Bridge.midiLinkText; font.family: Theme.fontMono; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textPrimary }
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

                    Text { text: "NETWORK & SYSTEM UPDATES"; font.bold: true; font.pixelSize: ScaleMetrics.sp(10); color: Theme.pageAccent }

                    // Wi-Fi Status Bar (live: Bridge.wifi* via NetworkManager)
                    Rectangle {
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(44)
                        radius: 4
                        color: Theme.bgControl
                        border.color: Bridge.wifiConnected ? Theme.playing : Theme.borderCard
                        border.width: 1

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: ScaleMetrics.dp(8)
                            spacing: ScaleMetrics.dp(6)
                            Icon {
                                name: "wifi"
                                size: 18
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
                                    color: Bridge.wifiConnected ? Theme.playing : Theme.textDim
                                    elide: Text.ElideRight
                                }
                            }
                            SpButton {
                                implicitWidth: ScaleMetrics.dp(26)
                                implicitHeight: ScaleMetrics.dp(24)
                                icon: "restart"
                                fontSize: 11
                                enabled: !Bridge.wifiBusy
                                onClicked: Bridge.refreshWifiStatus()
                            }
                            SpButton {
                                implicitWidth: ScaleMetrics.dp(60)
                                implicitHeight: ScaleMetrics.dp(24)
                                text: "MANAGE"
                                fontSize: 8
                                variant: "outline"
                                onClicked: {
                                    if (root.selectedSsid === "" && Bridge.wifiSsid !== "")
                                        root.selectedSsid = Bridge.wifiSsid;
                                    root.showWifiModal = true;
                                }
                            }
                        }
                    }

                    // Wi-Fi quick actions: radio toggle / rescan / disconnect
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: ScaleMetrics.dp(6)
                        opacity: Bridge.wifiBusy ? 0.55 : 1.0

                        SpButton {
                            Layout.fillWidth: true
                            implicitHeight: ScaleMetrics.dp(24)
                            text: Bridge.wifiEnabled ? "RADIO: ON" : "RADIO: OFF"
                            fontSize: 8
                            checked: Bridge.wifiEnabled
                            enabled: !Bridge.wifiBusy && Bridge.wifiAvailable
                            onClicked: Bridge.setWifiEnabled(!Bridge.wifiEnabled)
                        }
                        SpButton {
                            Layout.fillWidth: true
                            implicitHeight: ScaleMetrics.dp(24)
                            text: "RESCAN"
                            fontSize: 8
                            enabled: !Bridge.wifiBusy && Bridge.wifiEnabled
                            onClicked: Bridge.scanWifi(true)
                        }
                        SpButton {
                            Layout.fillWidth: true
                            implicitHeight: ScaleMetrics.dp(24)
                            visible: Bridge.wifiConnected
                            text: "DISCONNECT"
                            fontSize: 8
                            variant: "danger"
                            enabled: !Bridge.wifiBusy
                            onClicked: Bridge.disconnectWifi()
                        }
                        Text {
                            visible: Bridge.wifiBusy
                            text: "WORKING…"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(7)
                            color: Theme.pageAccent
                        }
                    }

                    // System Update Terminal Box
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: 4
                        color: Theme.bgTrack
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
                                Text { text: "JUNO-SPECTRE-OS"; font.family: Theme.fontMono; font.pixelSize: ScaleMetrics.sp(7); color: Theme.pageAccent }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                radius: 2
                                color: Theme.bgTrack
                                border.color: Theme.borderCard
                                border.width: 1
                                Text {
                                    anchors.fill: parent
                                    anchors.margins: 4
                                    text: "$ uname -a\nLinux juno-spectre-pi 6.1.21-v8+ aarch64\n$ git describe --tags\n" + Bridge.version + "\n" + Bridge.updaterLog
                                    font.family: Theme.fontMono
                                    font.pixelSize: ScaleMetrics.sp(8)
                                    color: Theme.playing
                                }
                            }

                            // Check for Releases Button
                            SpButton {
                                Layout.fillWidth: true
                                implicitHeight: ScaleMetrics.dp(28)
                                text: Bridge.updaterBusy ? "CONTACTING RELEASE CHANNEL..." : "CHECK FOR SPECTRE RELEASES"
                                fontSize: 8
                                variant: "outline"
                                enabled: !Bridge.updaterBusy
                                onClicked: Bridge.checkForUpdates()
                            }

                            // Install Latest Release Button (toggles to RESTART when done)
                            SpButton {
                                Layout.fillWidth: true
                                implicitHeight: ScaleMetrics.dp(28)
                                visible: Bridge.updateAvailable || Bridge.updateApplied
                                text: Bridge.updateApplied ? "RESTART NOW TO RUN " + Bridge.version : "INSTALL RELEASE " + Bridge.latestVersion
                                fontSize: 8
                                variant: "outline"
                                enabled: !Bridge.updaterBusy
                                onClicked: {
                                    if (Bridge.updateApplied)
                                        Bridge.restartApp();
                                    else
                                        Bridge.applyLatestRelease();
                                }
                            }

                            // Rollback to Previous Release Button
                            SpButton {
                                Layout.fillWidth: true
                                implicitHeight: ScaleMetrics.dp(28)
                                text: "ROLLBACK TO PREVIOUS RELEASE"
                                fontSize: 8
                                enabled: !Bridge.updaterBusy
                                onClicked: Bridge.rollbackRelease()
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
        color: Theme.scrim
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
            border.color: Theme.pageAccent
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(10)
                spacing: ScaleMetrics.dp(6)

                // Header
                RowLayout {
                    Layout.fillWidth: true
                    spacing: ScaleMetrics.dp(6)
                    Text { text: "WI-FI NETWORKS"; font.bold: true; font.pixelSize: ScaleMetrics.sp(11); color: Theme.pageAccent }
                    Text {
                        text: Bridge.wifiBusy ? "WORKING…" : ("SCAN: " + Bridge.wifiLastScan)
                        font.pixelSize: ScaleMetrics.sp(7)
                        color: Bridge.wifiBusy ? Theme.pageAccent : Theme.textDim
                    }
                    Item { Layout.fillWidth: true }
                    Text {
                        text: Bridge.wifiStatusText
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Bridge.wifiConnected ? Theme.playing : Theme.textDim
                    }
                    SpButton {
                        implicitWidth: ScaleMetrics.dp(24)
                        implicitHeight: ScaleMetrics.dp(24)
                        icon: "close"
                        onClicked: root.showWifiModal = false
                    }
                }

                // Live status + error lines
                Text {
                    Layout.fillWidth: true
                    text: Bridge.wifiDetailText
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: Bridge.wifiConnected ? Theme.playing : Theme.textSecondary
                    elide: Text.ElideRight
                }
                Text {
                    Layout.fillWidth: true
                    visible: Bridge.wifiError !== ""
                    text: Bridge.wifiError
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: Theme.recording
                    wrapMode: Text.Wrap
                }

                // Radio + rescan controls
                RowLayout {
                    Layout.fillWidth: true
                    spacing: ScaleMetrics.dp(6)
                    opacity: Bridge.wifiBusy ? 0.55 : 1.0

                    SpButton {
                        Layout.preferredWidth: ScaleMetrics.dp(130)
                        implicitHeight: ScaleMetrics.dp(26)
                        text: Bridge.wifiEnabled ? "RADIO: ON" : "RADIO: OFF"
                        fontSize: 8
                        checked: Bridge.wifiEnabled
                        enabled: !Bridge.wifiBusy && Bridge.wifiAvailable
                        onClicked: Bridge.setWifiEnabled(!Bridge.wifiEnabled)
                    }
                    SpButton {
                        Layout.fillWidth: true
                        implicitHeight: ScaleMetrics.dp(26)
                        text: Bridge.wifiBusy ? "SCANNING…" : "RESCAN NETWORKS"
                        fontSize: 8
                        variant: "outline"
                        enabled: !Bridge.wifiBusy && Bridge.wifiEnabled
                        onClicked: Bridge.scanWifi(true)
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
                        color: Theme.bgTrack
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
                                        ? Theme.tint(Theme.pageAccent)
                                        : (netMouse.pressed ? Theme.bgCardActive : Theme.bgControl)
                                    border.color: modelData.inUse
                                        ? Theme.playing
                                        : (modelData.ssid === root.selectedSsid ? Theme.pageAccent : Theme.borderCard)
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
                                                text: modelData.ssid
                                                font.bold: true
                                                font.pixelSize: ScaleMetrics.sp(9)
                                                color: modelData.inUse ? Theme.playing : Theme.textPrimary
                                                elide: Text.ElideRight
                                            }
                                            Icon {
                                                name: modelData.secured ? "lock" : "dot"
                                                size: 12
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
                            color: Theme.bgTrack
                            border.color: root.wifiActiveField === "ssid" ? Theme.pageAccent : Theme.borderCard
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
                                color: Theme.bgTrack
                                border.color: root.wifiActiveField === "password" ? Theme.pageAccent : Theme.borderCard
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
                            SpButton {
                                Layout.preferredWidth: ScaleMetrics.dp(52)
                                implicitHeight: ScaleMetrics.dp(30)
                                text: root.wifiShowPassword ? "HIDE" : "SHOW"
                                fontSize: 8
                                onClicked: root.wifiShowPassword = !root.wifiShowPassword
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
                        SpButton {
                            Layout.fillWidth: true
                            implicitHeight: ScaleMetrics.dp(30)
                            text: Bridge.wifiBusy ? "WORKING…" : (root.selectedSsid === "" ? "SELECT A NETWORK" : "CONNECT TO " + root.selectedSsid)
                            fontSize: 8
                            variant: "outline"
                            enabled: root.selectedSsid !== "" && !Bridge.wifiBusy
                            onClicked: {
                                Bridge.connectWifi(root.selectedSsid, root.wifiPassword);
                                root.wifiPassword = "";
                            }
                        }

                        // Disconnect + forget
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: ScaleMetrics.dp(6)
                            SpButton {
                                Layout.fillWidth: true
                                implicitHeight: ScaleMetrics.dp(26)
                                visible: Bridge.wifiConnected
                                text: "DISCONNECT"
                                fontSize: 8
                                variant: "danger"
                                enabled: !Bridge.wifiBusy
                                onClicked: Bridge.disconnectWifi()
                            }
                            SpButton {
                                Layout.fillWidth: true
                                implicitHeight: ScaleMetrics.dp(26)
                                text: "FORGET SAVED"
                                fontSize: 8
                                enabled: root.selectedSsid !== "" && !Bridge.wifiBusy
                                onClicked: Bridge.forgetWifi(root.selectedSsid)
                            }
                        }

                        // Touch keyboard (case + symbols enabled for passphrases)
                        VirtualKeyboard {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            accentColor: Theme.pageAccent
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
        property color color: Theme.pageAccent
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
            color: Theme.bgControl
            Rectangle {
                width: parent.width * Math.max(0, Math.min(1.0, sb.norm))
                height: parent.height
                radius: 2
                color: sb.color
            }
        }
    }
}
