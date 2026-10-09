import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import JunoSpectre
import ".."

Rectangle {
    id: root
    anchors.fill: parent
    visible: false
    z: 999
    color: "#e60a0c10"

    property string patchName: ""
    property string category: ""
    property string tagsText: ""
    property bool favorite: false
    property bool saveToDevice: false
    property var slotList: []
    property int slotIndex: -1
    property bool confirmArmed: false
    property string errorText: ""
    property bool busy: false
    property bool readingSlots: false
    property bool keyboardVisible: false
    property string activeField: "name"
    // PERFORM: edited parts ({part, name, target, label}) and the write-back choice
    property var editedParts: []
    property bool updateSources: false
    readonly property bool isPerf: Bridge.soundMode === "PERFORM"
    // Why the performance can't go to the keyboard ("" = it can); edited
    // user-slot parts count as fixed when they're being written back first.
    property string perfBlockers: (visible && isPerf) ? Bridge.perfKeyboardBlockers(updateSources) : ""
    onPerfBlockersChanged: if (perfBlockers !== "") { saveToDevice = false; disarm() }

    function writableCount() {
        var n = 0
        for (var i = 0; i < editedParts.length; i++) if (editedParts[i].target !== "") n++
        return n
    }

    function editedSummary() {
        var rows = []
        for (var i = 0; i < editedParts.length; i++) {
            var e = editedParts[i]
            rows.push("P" + e.part + " " + e.name + " → " + e.label)
        }
        return rows.join("  ·  ")
    }

    // Mirrors core/categories.py (without "---" no-assign; NONE chip covers it).
    property var catCodes: ["PNO","EP","KEY","BEL","MLT","ORG","ACD","HRM","AGT","EGT","DGT","BS","SBS","STR","ORC","HIT","WND","FLT","BRS","SBR","SAX","HLD","SLD","TEK","PLS","FX","SYN","BPD","SPD","VOX","PLK","ETH","FRT","PRC","SFX","BTS","DRM","CMB"]

    function open() {
        patchName = Bridge.soundMode === "PERFORM" ? Bridge.perfName : Bridge.patchName
        category = Bridge.currentCategoryCode()
        tagsText = ""
        favorite = false
        saveToDevice = Bridge.soundMode === "PERFORM" ? false : Bridge.currentIsUserSlot
        editedParts = Bridge.soundMode === "PERFORM" ? (Bridge.perfEditedParts() || []) : []
        updateSources = false
        slotList = []
        slotIndex = -1
        confirmArmed = false
        errorText = ""
        busy = false
        keyboardVisible = false
        visible = true
        if (saveToDevice) loadSlots()
    }

    function close() {
        visible = false
        keyboardVisible = false
    }

    function loadSlots() {
        var list = []
        try { list = (isPerf ? Bridge.getUserPerfSlots() : Bridge.getUserSlotIndex()) || [] } catch (e) { list = [] }
        root.slotList = list
        // Self-healing: a machine that never ran the dump has an empty
        // index — pull the names live from the keyboard instead.
        if (list.length < (isPerf ? 128 : 256) && !root.readingSlots) {
            root.readingSlots = true
            slotRefreshTimer.start()
            return
        }
        // Default: current slot when overwriting, else first free slot.
        var defIdx = -1
        if (!isPerf && Bridge.currentIsUserSlot) {
            for (var i = 0; i < list.length; i++) {
                if (list[i].msb === Bridge.currentMsb && list[i].lsb === Bridge.currentLsb && list[i].pc === Bridge.currentPc) {
                    defIdx = i
                    break
                }
            }
        }
        if (defIdx < 0) {
            for (var j = 0; j < list.length; j++) {
                if (list[j].free) { defIdx = j; break }
            }
        }
        if (defIdx < 0 && list.length > 0) defIdx = 0
        root.slotIndex = defIdx
        if (defIdx >= 0) slotView.positionViewAtIndex(defIdx, ListView.Center)
    }

    function safeFileName() {
        var s = (patchName || "Untitled").replace(/[^A-Za-z0-9\-_ ]/g, "_").trim()
        if (s === "") s = "Untitled"
        return s + ".spectre"
    }

    function selectedSlot() {
        if (slotIndex >= 0 && slotIndex < slotList.length) return slotList[slotIndex]
        return null
    }

    function slotOccupied() {
        var s = selectedSlot()
        return s !== null && !s.free
    }

    function slotIsOrigin() {
        var s = selectedSlot()
        return s !== null && !isPerf && Bridge.currentIsUserSlot && s.msb === Bridge.currentMsb && s.lsb === Bridge.currentLsb && s.pc === Bridge.currentPc
    }

    function disarm() { confirmArmed = false }

    MouseArea {
        anchors.fill: parent
        onClicked: { if (!root.busy && !root.readingSlots) root.close() }
    }

    Rectangle {
        id: card
        width: Math.min(parent.width - ScaleMetrics.dp(32), ScaleMetrics.dp(660))
        height: Math.min(parent.height - ScaleMetrics.dp(24), ScaleMetrics.dp(548))
        anchors.centerIn: parent
        radius: ScaleMetrics.dp(8)
        color: Theme.bgCard
        border.color: "#38bdf8"
        border.width: 1

        MouseArea { anchors.fill: parent }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(14)
            spacing: ScaleMetrics.dp(8)

            // Header
            RowLayout {
                Layout.fillWidth: true
                spacing: ScaleMetrics.dp(8)
                Text {
                    text: "💾 SAVE SOUND"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(11)
                    font.letterSpacing: 1.1
                    color: Theme.textPrimary
                }
                Text {
                    text: Bridge.currentRefLabel
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: Theme.textDim
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                Rectangle {
                    width: ScaleMetrics.dp(26); height: ScaleMetrics.dp(26)
                    radius: ScaleMetrics.dp(4)
                    color: closeArea.pressed ? Theme.bgCardActive : "#10141d"
                    border.color: Theme.borderCard; border.width: 1
                    Text { anchors.centerIn: parent; text: "✕"; font.bold: true; font.pixelSize: ScaleMetrics.sp(10); color: Theme.textSecondary }
                    MouseArea { id: closeArea; anchors.fill: parent; onClicked: { if (!root.busy && !root.readingSlots) root.close() } }
                }
            }

            // Name + favorite
            RowLayout {
                Layout.fillWidth: true
                spacing: ScaleMetrics.dp(8)
                Rectangle {
                    Layout.fillWidth: true
                    height: ScaleMetrics.dp(36)
                    radius: ScaleMetrics.dp(4)
                    color: Theme.bgApp
                    border.color: nameField.activeFocus ? "#38bdf8" : Theme.borderCard
                    border.width: 1
                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: ScaleMetrics.dp(8)
                        anchors.rightMargin: ScaleMetrics.dp(8)
                        spacing: ScaleMetrics.dp(6)
                        TextInput {
                            id: nameField
                            Layout.fillWidth: true
                            text: root.patchName
                            maximumLength: 12
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(13)
                            color: Theme.textPrimary
                            clip: true
                            onTextEdited: { root.patchName = text; root.disarm() }
                            onActiveFocusChanged: { if (activeFocus) { root.activeField = "name"; root.keyboardVisible = true } }
                        }
                        Text {
                            text: (root.patchName || "").length + "/12"
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: Theme.textDim
                        }
                        Rectangle {
                            width: ScaleMetrics.dp(28); height: ScaleMetrics.dp(22)
                            radius: ScaleMetrics.dp(4)
                            color: root.keyboardVisible && root.activeField === "name" ? "#38bdf8" : Theme.bgSurface
                            border.color: Theme.borderCard; border.width: 1
                            Text { anchors.centerIn: parent; text: "⌨"; font.pixelSize: ScaleMetrics.sp(12); color: Theme.textSecondary }
                            MouseArea { anchors.fill: parent; onClicked: { root.activeField = "name"; root.keyboardVisible = !root.keyboardVisible } }
                        }
                    }
                }
                Rectangle {
                    width: ScaleMetrics.dp(44); height: ScaleMetrics.dp(36)
                    radius: ScaleMetrics.dp(4)
                    color: root.favorite ? "#3a2f10" : Theme.bgApp
                    border.color: root.favorite ? "#fbbf24" : Theme.borderCard
                    border.width: 1
                    Text { anchors.centerIn: parent; text: "★"; font.pixelSize: ScaleMetrics.sp(16); color: root.favorite ? "#fbbf24" : Theme.textDim }
                    MouseArea { anchors.fill: parent; onClicked: { root.favorite = !root.favorite } }
                }
            }

            // Category strip (Flickable: 38 codes + NONE)
            Flickable {
                Layout.fillWidth: true
                height: ScaleMetrics.dp(30)
                contentWidth: catRow.width
                clip: true
                interactive: true
                RowLayout {
                    id: catRow
                    spacing: ScaleMetrics.dp(4)
                    height: ScaleMetrics.dp(30)
                    Rectangle {
                        width: ScaleMetrics.dp(52); height: ScaleMetrics.dp(26)
                        radius: 3
                        color: root.category === "" ? Theme.bgCardActive : "#10141d"
                        border.color: root.category === "" ? "#38bdf8" : Theme.borderCard
                        border.width: 1
                        Text { anchors.centerIn: parent; text: "NONE"; font.bold: root.category === ""; font.pixelSize: ScaleMetrics.sp(8); color: root.category === "" ? "#38bdf8" : Theme.textDim }
                        MouseArea { anchors.fill: parent; onClicked: { root.category = "" } }
                    }
                    Repeater {
                        model: root.catCodes
                        delegate: Rectangle {
                            width: ScaleMetrics.dp(46); height: ScaleMetrics.dp(26)
                            radius: 3
                            color: root.category === modelData ? Theme.bgCardActive : "#10141d"
                            border.color: root.category === modelData ? "#38bdf8" : Theme.borderCard
                            border.width: 1
                            Text { anchors.centerIn: parent; text: modelData; font.bold: root.category === modelData; font.pixelSize: ScaleMetrics.sp(8); color: root.category === modelData ? "#38bdf8" : Theme.textDim }
                            MouseArea { anchors.fill: parent; onClicked: { root.category = modelData } }
                        }
                    }
                }
            }

            // Tags
            Rectangle {
                Layout.fillWidth: true
                height: ScaleMetrics.dp(30)
                radius: ScaleMetrics.dp(4)
                color: Theme.bgApp
                border.color: tagsField.activeFocus ? "#38bdf8" : Theme.borderCard
                border.width: 1
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: ScaleMetrics.dp(8)
                    anchors.rightMargin: ScaleMetrics.dp(8)
                    spacing: ScaleMetrics.dp(6)
                    TextInput {
                        id: tagsField
                        Layout.fillWidth: true
                        text: root.tagsText
                        font.pixelSize: ScaleMetrics.sp(10)
                        color: Theme.textPrimary
                        clip: true
                        onTextEdited: { root.tagsText = text }
                        onActiveFocusChanged: { if (activeFocus) { root.activeField = "tags"; root.keyboardVisible = true } }
                        Text {
                            anchors.fill: parent
                            verticalAlignment: Text.AlignVCenter
                            text: "tags, comma separated…"
                            font.pixelSize: ScaleMetrics.sp(10)
                            color: Theme.textDim
                            visible: !tagsField.text && !tagsField.activeFocus
                        }
                    }
                    Rectangle {
                        width: ScaleMetrics.dp(28); height: ScaleMetrics.dp(22)
                        radius: ScaleMetrics.dp(4)
                        color: root.keyboardVisible && root.activeField === "tags" ? "#38bdf8" : Theme.bgSurface
                        border.color: Theme.borderCard; border.width: 1
                        Text { anchors.centerIn: parent; text: "⌨"; font.pixelSize: ScaleMetrics.sp(12); color: Theme.textSecondary }
                        MouseArea { anchors.fill: parent; onClicked: { root.activeField = "tags"; root.keyboardVisible = !root.keyboardVisible } }
                    }
                }
            }

            // Pi-always info line (no checkbox: Pi save is unconditional)
            Text {
                Layout.fillWidth: true
                text: "Saved locally as \"" + root.safeFileName() + "\""
                font.pixelSize: ScaleMetrics.sp(8)
                font.italic: true
                color: Theme.textDim
                elide: Text.ElideRight
            }

            // Edited parts (PERFORM): optionally overwrite their source patches
            Rectangle {
                visible: root.writableCount() > 0
                Layout.fillWidth: true
                Layout.preferredHeight: visible ? ScaleMetrics.dp(30) : 0
                height: ScaleMetrics.dp(30)
                radius: ScaleMetrics.dp(4)
                color: srcArea.pressed ? Theme.bgCardActive : "#10141d"
                border.color: root.updateSources ? "#fbbf24" : Theme.borderCard
                border.width: 1
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: ScaleMetrics.dp(8)
                    anchors.rightMargin: ScaleMetrics.dp(8)
                    spacing: ScaleMetrics.dp(8)
                    Rectangle {
                        width: ScaleMetrics.dp(16); height: ScaleMetrics.dp(16)
                        radius: 3
                        color: root.updateSources ? "#fbbf24" : "transparent"
                        border.color: "#fbbf24"; border.width: 1
                        Text { anchors.centerIn: parent; text: "✓"; font.bold: true; font.pixelSize: ScaleMetrics.sp(10); color: "#000000"; visible: root.updateSources }
                    }
                    Text {
                        text: "Also update source patches (" + root.writableCount() + " edited)"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(9)
                        color: root.updateSources ? "#fbbf24" : Theme.textSecondary
                    }
                }
                MouseArea {
                    id: srcArea
                    anchors.fill: parent
                    onClicked: { if (!root.busy) root.updateSources = !root.updateSources }
                }
            }
            Text {
                visible: root.editedParts.length > 0
                Layout.fillWidth: true
                text: "Edited: " + root.editedSummary()
                font.pixelSize: ScaleMetrics.sp(8)
                color: Theme.textDim
                wrapMode: Text.Wrap
                maximumLineCount: 3
                elide: Text.ElideRight
            }

            // Device checkbox (performances: only when every part has a keyboard equivalent)
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: ScaleMetrics.dp(30)
                height: ScaleMetrics.dp(30)
                opacity: root.perfBlockers === "" ? 1.0 : 0.45
                radius: ScaleMetrics.dp(4)
                color: devArea.pressed ? Theme.bgCardActive : "#10141d"
                border.color: root.saveToDevice ? "#fbbf24" : Theme.borderCard
                border.width: 1
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: ScaleMetrics.dp(8)
                    anchors.rightMargin: ScaleMetrics.dp(8)
                    spacing: ScaleMetrics.dp(8)
                    Rectangle {
                        width: ScaleMetrics.dp(16); height: ScaleMetrics.dp(16)
                        radius: 3
                        color: root.saveToDevice ? "#fbbf24" : "transparent"
                        border.color: "#fbbf24"; border.width: 1
                        Text { anchors.centerIn: parent; text: "✓"; font.bold: true; font.pixelSize: ScaleMetrics.sp(10); color: "#000000"; visible: root.saveToDevice }
                    }
                    Text {
                        text: root.isPerf ? "Also save to keyboard (user performance)" : "Also save to keyboard (user slot)"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(9)
                        color: root.saveToDevice ? "#fbbf24" : Theme.textSecondary
                    }
                }
                MouseArea {
                    id: devArea
                    anchors.fill: parent
                    onClicked: {
                        if (root.busy || root.perfBlockers !== "") return
                        root.saveToDevice = !root.saveToDevice
                        root.disarm()
                        if (root.saveToDevice && root.slotList.length === 0) root.loadSlots()
                    }
                }
            }

            Text {
                visible: root.perfBlockers !== ""
                Layout.fillWidth: true
                text: "Keyboard save needs every part on an unedited keyboard patch. Not possible for: " + root.perfBlockers
                font.pixelSize: ScaleMetrics.sp(8)
                color: Theme.textDim
                wrapMode: Text.Wrap
                maximumLineCount: 3
                elide: Text.ElideRight
            }

            // Slot list header: count + manual refresh from keyboard
            RowLayout {
                Layout.fillWidth: true
                spacing: ScaleMetrics.dp(8)
                visible: root.saveToDevice
                Text {
                    text: (root.isPerf ? "USER PERFORMANCE" : "USER SLOT")
                          + (root.slotList.length > 0 ? (" (" + root.slotList.length + (root.isPerf ? "/128)" : "/256)")) : "")
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(9)
                    color: Theme.textDim
                    Layout.fillWidth: true
                }
                Text {
                    visible: root.readingSlots
                    text: "Reading slots…"
                    font.pixelSize: ScaleMetrics.sp(8)
                    font.italic: true
                    color: "#fbbf24"
                }
                Rectangle {
                    width: ScaleMetrics.dp(30); height: ScaleMetrics.dp(24)
                    radius: ScaleMetrics.dp(4)
                    color: refreshArea.pressed ? Theme.bgCardActive : "#10141d"
                    border.color: Theme.borderCard; border.width: 1
                    Text { anchors.centerIn: parent; text: "⟳"; font.bold: true; font.pixelSize: ScaleMetrics.sp(11); color: Theme.tone1 }
                    MouseArea {
                        id: refreshArea
                        anchors.fill: parent
                        onClicked: {
                            if (root.readingSlots || root.busy) return
                            root.readingSlots = true
                            slotRefreshTimer.start()
                        }
                    }
                }
            }

            // Slot list (scrollable, tap to select). Yields height while the
            // keyboard is open so the footer stays inside the fixed card.
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: root.keyboardVisible ? ScaleMetrics.dp(64) : ScaleMetrics.dp(110)
                radius: ScaleMetrics.dp(6)
                color: Theme.bgApp
                border.color: Theme.borderCard
                border.width: 1
                visible: root.saveToDevice
                ListView {
                    id: slotView
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(6)
                    clip: true
                    spacing: ScaleMetrics.dp(3)
                    model: root.slotList
                    ScrollBar.vertical: ScrollBar {
                        anchors.right: parent.right
                        anchors.rightMargin: ScaleMetrics.dp(1)
                        policy: ScrollBar.AlwaysOn
                        width: ScaleMetrics.dp(14)
                        minimumSize: 0.06
                        contentItem: Rectangle {
                            radius: width / 2
                            color: parent.pressed ? "#fbbf24" : "#a67c3b"
                            opacity: 0.9
                        }
                        background: Rectangle {
                            radius: width / 2
                            color: "#10141d"
                            opacity: 0.7
                        }
                    }
                    delegate: Rectangle {
                        width: ListView.view.width - ScaleMetrics.dp(16)
                        height: ScaleMetrics.dp(30)
                        radius: 3
                        color: root.slotIndex === index ? Theme.bgCardActive : "#0d1017"
                        border.color: root.slotIndex === index ? "#fbbf24" : Theme.borderCard
                        border.width: 1
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: ScaleMetrics.dp(8)
                            anchors.rightMargin: ScaleMetrics.dp(8)
                            spacing: ScaleMetrics.dp(8)
                            Text {
                                text: modelData.number
                                font.family: Theme.fontMono
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(9)
                                color: Theme.tone1
                            }
                            Text {
                                text: modelData.name || "?"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(10)
                                color: Theme.textPrimary
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                            Rectangle {
                                width: ScaleMetrics.dp(44); height: ScaleMetrics.dp(18)
                                radius: 3
                                color: modelData.free ? "#0d2b1a" : "transparent"
                                border.color: modelData.free ? "#10b981" : Theme.borderCard
                                border.width: 1
                                visible: modelData.free || (root.slotIndex === index && root.slotOccupied())
                                Text {
                                    anchors.centerIn: parent
                                    text: modelData.free ? "FREE" : "FULL"
                                    font.bold: true
                                    font.pixelSize: ScaleMetrics.sp(7)
                                    color: modelData.free ? "#10b981" : Theme.textDim
                                }
                            }
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: { root.slotIndex = index; root.disarm() }
                        }
                    }
                }
            }

            // Error line
            Text {
                Layout.fillWidth: true
                visible: root.errorText !== ""
                text: root.errorText
                font.pixelSize: ScaleMetrics.sp(8)
                color: "#ef4444"
                wrapMode: Text.Wrap
                maximumLineCount: 2
                elide: Text.ElideRight
            }

            // Virtual keyboard (shared by name + tags fields)
            VirtualKeyboard {
                Layout.fillWidth: true
                Layout.preferredHeight: ScaleMetrics.dp(140)
                visible: root.keyboardVisible
                accentColor: "#38bdf8"
                onKeyClicked: (key) => {
                    if (root.activeField === "tags") {
                        tagsField.text += key.toLowerCase();
                        root.tagsText = tagsField.text;
                    } else if (nameField.text.length < 12) {
                        nameField.text += key.toUpperCase();
                        root.patchName = nameField.text;
                        root.disarm();
                    }
                }
                onBackspaceClicked: {
                    if (root.activeField === "tags" && tagsField.text.length > 0) {
                        tagsField.text = tagsField.text.slice(0, -1);
                        root.tagsText = tagsField.text;
                    } else if (nameField.text.length > 0) {
                        nameField.text = nameField.text.slice(0, -1);
                        root.patchName = nameField.text;
                        root.disarm();
                    }
                }
                onClearClicked: {
                    if (root.activeField === "tags") { tagsField.text = ""; root.tagsText = "" }
                    else { nameField.text = ""; root.patchName = ""; root.disarm() }
                }
                onCloseClicked: { root.keyboardVisible = false }
            }

            // Footer
            RowLayout {
                Layout.fillWidth: true
                spacing: ScaleMetrics.dp(8)
                Rectangle {
                    Layout.preferredWidth: ScaleMetrics.dp(110)
                    height: ScaleMetrics.dp(36)
                    radius: ScaleMetrics.dp(4)
                    color: cancelArea.pressed ? Theme.bgCardActive : "#10141d"
                    border.color: Theme.borderCard; border.width: 1
                    Text { anchors.centerIn: parent; text: "CANCEL"; font.bold: true; font.pixelSize: ScaleMetrics.sp(9); color: Theme.textSecondary }
                    MouseArea { id: cancelArea; anchors.fill: parent; onClicked: { if (!root.busy && !root.readingSlots) root.close() } }
                }
                Rectangle {
                    Layout.fillWidth: true
                    height: ScaleMetrics.dp(36)
                    radius: ScaleMetrics.dp(4)
                    color: root.busy ? Theme.bgSurface : (root.confirmArmed ? "#3f1a1a" : "#0c2f3f")
                    border.color: root.confirmArmed ? "#ef4444" : "#38bdf8"
                    border.width: 1
                    Text {
                        anchors.centerIn: parent
                        text: root.busy ? "WRITING… DO NOT POWER OFF" : (root.confirmArmed ? "TAP AGAIN TO OVERWRITE" : "SAVE")
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(9)
                        color: root.confirmArmed ? "#ef4444" : "#38bdf8"
                    }
                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            if (root.busy || root.readingSlots) return
                            if ((root.patchName || "").trim() === "") { root.errorText = "Give the sound a name."; return }
                            if (root.saveToDevice) {
                                var s = root.selectedSlot()
                                if (s === null) { root.errorText = "Pick a user slot first."; return }
                                if (root.slotOccupied() && !root.slotIsOrigin() && !root.confirmArmed) {
                                    root.confirmArmed = true
                                    root.errorText = "Slot " + s.number + " holds \"" + s.name + "\" — tap SAVE again to overwrite (auto-backup first)."
                                    return
                                }
                            }
                            root.busy = true
                            root.errorText = ""
                            saveTimer.start()
                        }
                    }
                }
            }
        }

        // Deferred blocking save (lets the busy state paint first).
        Timer {
            id: slotRefreshTimer
            interval: 80
            repeat: false
            running: false
            onTriggered: {
                var n = -1
                try { n = root.isPerf ? Bridge.refreshUserPerfNames() : Bridge.refreshUserSlotNames() } catch (e) { n = -1 }
                root.readingSlots = false
                if (n < 0) {
                    root.errorText = "No synthesizer connected — slot names unavailable."
                }
                root.loadSlots()
            }
        }

        // Deferred blocking save (lets the busy state paint first).
        Timer {
            id: saveTimer
            interval: 80
            repeat: false
            running: false
            onTriggered: {
                // Sources first, so the saved song references them clean.
                var srcErr = root.updateSources ? Bridge.writeBackEditedParts() : ""
                var piPath = Bridge.saveCurrentToFile(root.patchName, root.category, root.tagsText, root.favorite, "")
                if (piPath === "") {
                    root.busy = false
                    root.errorText = "Pi save failed (no synth connected?)."
                    return
                }
                if (srcErr !== "") {
                    // The song is saved (edited sounds ride its snapshots); say what wasn't updated.
                    root.busy = false
                    root.updateSources = false
                    root.editedParts = Bridge.perfEditedParts() || []
                    root.errorText = "Saved. Not updated: " + srcErr
                    return
                }
                if (root.saveToDevice) {
                    var s = root.selectedSlot()
                    var err = root.isPerf ? Bridge.savePerfToDevice(s.number, root.patchName)
                                          : Bridge.saveCurrentToDevice(s.msb, s.lsb, s.pc, root.patchName)
                    root.busy = false
                    if (err !== "") { root.errorText = err; root.disarm(); return }
                } else {
                    root.busy = false
                }
                root.close()
            }
        }
    }
}
