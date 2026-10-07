import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import JunoSpectre
import ".."

Rectangle {
    id: root
    color: Theme.bgCard
    radius: ScaleMetrics.dp(8)
    border.color: Theme.borderCard
    border.width: 1

    property int activeKindIdx: 0
    property bool favOnly: false
    property bool userFilesOnly: false
    property bool userSlotsOnly: false
    property string selectedPath: ""
    property int selectedIndex: -1
    property var selectedRow: null
    property string pendingAction: ""
    property string statusText: ""
    property string activeCode: ""
    property bool searchKbVisible: false
    property bool refreshingSlots: false
    property var kinds: ["", "patch", "drum", "performance"]
    property var kindLabels: ["ALL", "PATCH", "DRUM", "PERF"]
    // Live library model. Bound declaratively (onCompleted proved unreliable
    // for nested views): app.py always sets the `patchLibrary` context
    // property, even to an empty model on failure. Null/undefined = demo.
    property var patchModel: (typeof patchLibrary !== "undefined") ? patchLibrary : null
    property string searchText: ""
    property var patchList: [
        { num: "0001", name: "Grand Pno DS", cat: "PNO", fav: true },
        { num: "0002", name: "Bright Grand", cat: "PNO", fav: false },
        { num: "0025", name: "Pure EP", cat: "EP", fav: true },
        { num: "0104", name: "Juno 106 Lead", cat: "HLD", fav: true },
        { num: "0112", name: "JP-8000 Saw", cat: "HLD", fav: false },
        { num: "0180", name: "Warm Lush Pad", cat: "SPD", fav: true },
        { num: "0210", name: "Spectre Vector 1", cat: "USER FILE", fav: true },
        { num: "0211", name: "Wavetable Morph A", cat: "USER FILE", fav: false }
    ]
    // Filtered fallback view (demo data only, when no live model is bound)
    property var filteredFallback: root.patchList

    Component.onCompleted: {
        // Model arrives pre-refreshed from app.py; just re-apply local state.
        root.applyFilter()
    }

    function applyFilter() {
        if (!root.patchModel) return
        var kind = root.kinds[root.activeKindIdx]
        var source = root.userSlotsOnly ? "synth-user" : (root.userFilesOnly ? "file" : "")
        var codes = root.activeCode !== "" ? [root.activeCode] : []
        root.patchModel.refresh(root.searchText, "ALL", root.favOnly, source, 2500, codes.join(","), kind)
    }

    function setSourceFilter(which) {
        // Radio behavior: only one source filter at a time ("" = all).
        if (which === "slots") {
            root.userSlotsOnly = !root.userSlotsOnly
            if (root.userSlotsOnly) root.userFilesOnly = false
        } else if (which === "files") {
            root.userFilesOnly = !root.userFilesOnly
            if (root.userFilesOnly) root.userSlotsOnly = false
        }
        root.applyFilter()
    }

    function toggleCode(code) {
        root.activeCode = (root.activeCode === code) ? "" : code
        root.applyFilter()
    }

    function rowCountText() {
        if (!root.patchModel) return root.filteredFallback.length + " patches"
        var n = root.patchModel.rowCount()
        return n + (n === 1 ? " sound" : " sounds")
    }

    function clearSelection() {
        root.selectedPath = ""
        root.selectedIndex = -1
        root.selectedRow = null
        root.pendingAction = ""
    }

    function isSpectreFileRow() {
        return root.selectedRow !== null && root.selectedRow.source === "file"
            && String(root.selectedRow.path).slice(-8) === ".spectre"
    }

    function isUserPatchRow() {
        return root.selectedRow !== null && root.selectedRow.source === "synth-user"
            && root.selectedRow.kind === "patch"
    }

    function firstUsbDrive() {
        var drives = []
        try { drives = Bridge.listUsbDrives() || [] } catch (e) { drives = [] }
        return drives.length > 0 ? drives[0] : ""
    }

    Connections {
        target: Bridge
        function onLibrarianChanged() { root.applyFilter() }
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
                color: "#60a5fa"
            }
            Text {
                text: "PRESET & PATCH LIBRARIAN"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(12)
                font.letterSpacing: 1.2
                color: Theme.textPrimary
            }
            Item { Layout.fillWidth: true }
            Rectangle {
                visible: root.patchModel === null || root.patchModel === undefined || (Bridge.libraryError || "") !== ""
                color: "#3a2f10"
                radius: 3
                border.color: "#fbbf24"
                border.width: 1
                Layout.preferredWidth: ScaleMetrics.dp(280)
                height: ScaleMetrics.dp(22)
                Text {
                    anchors.centerIn: parent
                    width: parent.width - ScaleMetrics.dp(8)
                    text: "DEMO DATA — LIBRARY OFFLINE" + (((Bridge.libraryError || "") !== "") ? (": " + Bridge.libraryError) : "")
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(7)
                    color: "#fbbf24"
                    elide: Text.ElideRight
                }
            }
            Text {
                visible: root.patchModel !== null
                text: "DISK & SYSEX STORAGE"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(9)
                color: Theme.textDim
            }
            Item { width: ScaleMetrics.dp(4) }
            Rectangle {
                width: ScaleMetrics.dp(26)
                height: ScaleMetrics.dp(26)
                radius: ScaleMetrics.dp(4)
                color: libCloseArea.pressed ? Theme.bgCardActive : "#10141d"
                border.color: Theme.borderCard
                border.width: 1
                Text {
                    anchors.centerIn: parent
                    text: "✕"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(10)
                    color: Theme.textSecondary
                }
                MouseArea {
                    id: libCloseArea
                    anchors.fill: parent
                    onClicked: Bridge.toggleLibrarian()
                }
            }
        }

        // Browser (left) + full-height actions (right)
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: ScaleMetrics.dp(10)

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: ScaleMetrics.dp(8)

        // Kind tabs + user-files toggle + result count + favorites-only
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(4)
            Repeater {
                model: root.kindLabels
                delegate: Rectangle {
                    width: ScaleMetrics.dp(64)
                    height: ScaleMetrics.dp(24)
                    radius: 3
                    color: root.activeKindIdx === index ? Theme.bgCardActive : "#10141d"
                    border.color: root.activeKindIdx === index ? "#60a5fa" : Theme.borderCard
                    border.width: 1
                    Text {
                        anchors.centerIn: parent
                        text: modelData
                        font.bold: root.activeKindIdx === index
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: root.activeKindIdx === index ? "#60a5fa" : Theme.textDim
                    }
                    MouseArea { anchors.fill: parent; onClicked: { root.activeKindIdx = index; root.applyFilter() } }
                }
            }
            Rectangle {
                width: ScaleMetrics.dp(76)
                height: ScaleMetrics.dp(24)
                radius: 3
                color: root.userSlotsOnly ? Theme.bgCardActive : "#10141d"
                border.color: root.userSlotsOnly ? "#60a5fa" : Theme.borderCard
                border.width: 1
                Text {
                    anchors.centerIn: parent
                    text: "USER SLOTS"
                    font.bold: root.userSlotsOnly
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: root.userSlotsOnly ? "#60a5fa" : Theme.textDim
                }
                MouseArea { anchors.fill: parent; onClicked: root.setSourceFilter("slots") }
            }
            Rectangle {
                width: ScaleMetrics.dp(76)
                height: ScaleMetrics.dp(24)
                radius: 3
                color: root.userFilesOnly ? Theme.bgCardActive : "#10141d"
                border.color: root.userFilesOnly ? "#60a5fa" : Theme.borderCard
                border.width: 1
                Text {
                    anchors.centerIn: parent
                    text: "USER FILES"
                    font.bold: root.userFilesOnly
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: root.userFilesOnly ? "#60a5fa" : Theme.textDim
                }
                MouseArea { anchors.fill: parent; onClicked: root.setSourceFilter("files") }
            }
            Item { Layout.fillWidth: true }
            Text {
                text: root.rowCountText()
                font.pixelSize: ScaleMetrics.sp(8)
                color: Theme.textDim
            }
            Rectangle {
                width: ScaleMetrics.dp(52)
                height: ScaleMetrics.dp(24)
                radius: 3
                color: root.favOnly ? "#3a2f10" : "#10141d"
                border.color: root.favOnly ? "#fbbf24" : Theme.borderCard
                border.width: 1
                Text {
                    anchors.centerIn: parent
                    text: "★ Fav"
                    font.bold: root.favOnly
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: root.favOnly ? "#fbbf24" : Theme.textDim
                }
                MouseArea { anchors.fill: parent; onClicked: { root.favOnly = !root.favOnly; root.applyFilter() } }
            }
        }

        // Roland category browser: all 38 with full names (tap again to clear)
        Rectangle {
            Layout.fillWidth: true
            height: ScaleMetrics.dp(96)
            radius: 4
            color: Theme.bgApp
            border.color: Theme.borderCard
            border.width: 1
            visible: root.patchModel !== null
            Flickable {
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(5)
                contentWidth: width
                contentHeight: catGrid.implicitHeight
                clip: true
                interactive: true
                ScrollBar.vertical: ScrollBar {
                    anchors.right: parent.right
                    policy: ScrollBar.AsNeeded
                    width: ScaleMetrics.dp(10)
                }
                GridLayout {
                    id: catGrid
                    width: parent.width - ScaleMetrics.dp(10)
                    columns: 4
                    rowSpacing: ScaleMetrics.dp(4)
                    columnSpacing: ScaleMetrics.dp(4)
                    Repeater {
                        model: ["PNO:Acoustic Piano","EP:Electric Piano","KEY:Keyboards","BEL:Bell","MLT:Mallet","ORG:Organ","ACD:Accordion","HRM:Harmonica","AGT:Acoustic Guitar","EGT:Electric Guitar","DGT:Distortion Guitar","BS:Bass","SBS:Synth Bass","STR:Strings","ORC:Orchestra","HIT:Hit & Stab","WND:Wind","FLT:Flute","BRS:Acoustic Brass","SBR:Synth Brass","SAX:Sax","HLD:Hard Lead","SLD:Soft Lead","TEK:Techno Synth","PLS:Pulsating Synth","FX:Synth FX","SYN:Poly Synth","BPD:Bright Pad","SPD:Soft Pad","VOX:Vox / Choir","PLK:Plucked","ETH:Ethnic","FRT:Fretted","PRC:Percussion","SFX:Sound FX","BTS:Beat & Groove","DRM:Drums","CMB:Combination"]
                        delegate: Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: ScaleMetrics.dp(28)
                            radius: 3
                            property string code: modelData.split(":")[0]
                            property string label: modelData.split(":").slice(1).join(":")
                            property bool isActive: root.activeCode === code
                            color: isActive ? Theme.bgCardActive : "#10141d"
                            border.color: isActive ? "#60a5fa" : Theme.borderCard
                            border.width: 1
                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: ScaleMetrics.dp(6)
                                anchors.rightMargin: ScaleMetrics.dp(6)
                                spacing: ScaleMetrics.dp(6)
                                Text {
                                    text: code
                                    font.family: Theme.fontMono
                                    font.bold: true
                                    font.pixelSize: ScaleMetrics.sp(8)
                                    color: isActive ? "#60a5fa" : Theme.tone1
                                }
                                Text {
                                    text: label
                                    font.pixelSize: ScaleMetrics.sp(8)
                                    color: isActive ? "#60a5fa" : Theme.textDim
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }
                            }
                            MouseArea { anchors.fill: parent; onClicked: root.toggleCode(code) }
                        }
                    }
                }
            }
        }

        // Search (live model) — filters name/tags via SQLite LIKE
        Rectangle {
            Layout.fillWidth: true
            height: ScaleMetrics.dp(28)
            radius: 4
            color: "#10141d"
            border.color: Theme.borderCard
            border.width: 1
            visible: root.patchModel !== null
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: ScaleMetrics.dp(8)
                anchors.rightMargin: ScaleMetrics.dp(6)
                spacing: ScaleMetrics.dp(6)
                Text {
                    text: "🔍"
                    font.pixelSize: ScaleMetrics.sp(10)
                    color: Theme.textDim
                }
                TextInput {
                    id: searchField
                    Layout.fillWidth: true
                    verticalAlignment: Text.AlignVCenter
                    font.pixelSize: ScaleMetrics.sp(10)
                    color: Theme.textPrimary
                    clip: true
                    onTextChanged: { root.searchText = text; root.applyFilter() }
                    onActiveFocusChanged: { if (activeFocus) root.searchKbVisible = true }
                    Text {
                        anchors.fill: parent
                        verticalAlignment: Text.AlignVCenter
                        text: "Search patches…"
                        font.pixelSize: ScaleMetrics.sp(10)
                        color: Theme.textDim
                        visible: parent.text === "" && !parent.activeFocus
                    }
                }
                Text {
                    visible: searchField.text.length > 0
                    text: "✕"
                    font.pixelSize: ScaleMetrics.sp(10)
                    color: Theme.textDim
                    MouseArea {
                        anchors.fill: parent
                        onClicked: { searchField.text = ""; root.searchText = ""; root.applyFilter() }
                    }
                }
                Rectangle {
                    width: ScaleMetrics.dp(28)
                    height: ScaleMetrics.dp(22)
                    radius: ScaleMetrics.dp(4)
                    color: root.searchKbVisible ? "#60a5fa" : Theme.bgSurface
                    border.color: Theme.borderCard
                    border.width: 1
                    Text {
                        anchors.centerIn: parent
                        text: "⌨"
                        font.pixelSize: ScaleMetrics.sp(12)
                        color: root.searchKbVisible ? "#000000" : Theme.textSecondary
                    }
                    MouseArea { anchors.fill: parent; onClicked: { root.searchKbVisible = !root.searchKbVisible; if (root.searchKbVisible) searchField.forceActiveFocus() } }
                }
            }
        }

        // Touch keyboard for search (below search, above list; list shrinks)
        VirtualKeyboard {
            Layout.fillWidth: true
            Layout.preferredHeight: ScaleMetrics.dp(140)
            visible: root.searchKbVisible && root.patchModel !== null
            accentColor: "#60a5fa"
            onKeyClicked: (key) => {
                searchField.text += key
                root.searchText = searchField.text
                root.applyFilter()
            }
            onBackspaceClicked: {
                if (searchField.text.length > 0) {
                    searchField.text = searchField.text.slice(0, -1)
                    root.searchText = searchField.text
                    root.applyFilter()
                }
            }
            onClearClicked: { searchField.text = ""; root.searchText = ""; root.applyFilter() }
            onCloseClicked: { root.searchKbVisible = false }
        }

        // Patch List Table (fills the left column's remaining height)
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: ScaleMetrics.dp(6)
                color: Theme.bgApp
                border.color: Theme.borderCard
                border.width: 1

                ListView {
                    id: patchListView
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(6)
                    clip: true
                    model: root.patchModel !== null ? root.patchModel : root.filteredFallback
                    spacing: ScaleMetrics.dp(4)

                    // Always-visible touch scrollbar: drag the thumb to jump
                    // anywhere in the (up to ~2500-row) library.
                    ScrollBar.vertical: ScrollBar {
                        anchors.right: parent.right
                        anchors.rightMargin: ScaleMetrics.dp(1)
                        policy: ScrollBar.AlwaysOn
                        width: ScaleMetrics.dp(14)
                        minimumSize: 0.04
                        contentItem: Rectangle {
                            radius: width / 2
                            color: parent.pressed ? "#60a5fa" : "#3b82a6"
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
                        height: ScaleMetrics.dp(48)
                        radius: 4
                        color: rowMouse.pressed ? Theme.bgCardActive : "#0d1017"
                        border.color: _selected ? "#60a5fa" : Theme.borderCard
                        border.width: _selected ? 2 : 1

                        // Resolve display fields for both models:
                        // - live PatchListModel roles: name/category/favorite/msb/lsb/pc/source/path/kind
                        // - fallback JS array: modelData.{num,name,cat,fav}
                        property bool _live: root.patchModel !== null
                        property string _path: _live ? path : ""
                        property bool _selected: _live && root.selectedPath !== "" && root.selectedPath === path
                        property string _num: _live ? (msb >= 0 ? (lsb + ":" + pc) : "FILE") : modelData.num
                        property string _name: _live ? name : modelData.name
                        property string _cat: _live ? (((category || "—") + (kind && kind !== "patch" ? " " + kind : "") + (source ? " • " + source : ""))) : modelData.cat
                        property bool _fav: _live ? favorite : modelData.fav

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: ScaleMetrics.dp(8)
                            spacing: ScaleMetrics.dp(8)

                            Text {
                                text: parent.parent._num
                                font.family: Theme.fontMono
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(9)
                                color: Theme.tone1
                            }
                            Text {
                                text: parent.parent._name
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(10)
                                color: Theme.textPrimary
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                            Text {
                                text: parent.parent._cat
                                font.pixelSize: ScaleMetrics.sp(8)
                                color: Theme.textDim
                                elide: Text.ElideRight
                            }
                            Text {
                                text: parent.parent._fav ? "★" : "☆"
                                font.pixelSize: ScaleMetrics.sp(12)
                                color: parent.parent._fav ? "#fbbf24" : Theme.textDim
                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: function(mouse) {
                                        mouse.accepted = true
                                        if (root.patchModel !== null) root.patchModel.toggleFavorite(index)
                                    }
                                }
                            }
                        }
                        MouseArea {
                            id: rowMouse
                            anchors.fill: parent
                            onClicked: {
                                if (root.patchModel !== null) {
                                    root.selectedPath = path
                                    root.selectedIndex = index
                                    root.selectedRow = root.patchModel.get(index)
                                    root.pendingAction = ""
                                    var ok = true
                                    if (kind !== undefined && kind === "performance") {
                                        ok = Bridge.selectLibraryPerformance(msb, lsb, pc)
                                    } else if (msb !== undefined && msb >= 0) {
                                        ok = Bridge.selectLibraryPatch(msb, lsb, pc)
                                    } else {
                                        Bridge.setPatchName(name, "PATCH")
                                    }
                                    root.statusText = ok ? "" : "No synthesizer connected — browsing only."
                                } else {
                                    Bridge.setPatchName(modelData.num + " " + modelData.name, "PATCH")
                                }
                            }
                        }
                    }
                }
            }

            // End of left browser column; action column spans the full height.
            }

            // Right Action Column (~240dp, full height)
            Rectangle {
                Layout.preferredWidth: ScaleMetrics.dp(240)
                Layout.fillHeight: true
                radius: ScaleMetrics.dp(6)
                color: Theme.bgApp
                border.color: Theme.borderCard
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(10)
                    spacing: ScaleMetrics.dp(8)

                    Text { text: "PRESET ACTIONS"; font.bold: true; font.pixelSize: ScaleMetrics.sp(9); color: Theme.textDim }

                    LibBtn { text: "INITIALIZE ACTIVE PATCH (RAM)"; accent: "#fbbf24"; onClicked: { root.pendingAction = ""; Bridge.openInitPatchModal() } }
                    LibBtn { text: "SAVE CURRENT SOUND"; accent: "#38bdf8"; onClicked: { root.pendingAction = ""; Bridge.openSavePatchModal() } }
                    LibBtn {
                        text: "RENAME SELECTED"
                        accent: Theme.tone2
                        opacity: (root.isSpectreFileRow() || root.isUserPatchRow()) ? 1.0 : 0.4
                        onClicked: {
                            root.pendingAction = ""
                            if (root.isSpectreFileRow()) {
                                renameModal.openFile(root.selectedRow.path, root.selectedRow.name)
                            } else if (root.isUserPatchRow()) {
                                renameModal.openSlot(root.selectedRow.msb, root.selectedRow.lsb, root.selectedRow.pc, root.selectedRow.name)
                            } else {
                                root.statusText = "Select a Pi file or user slot to rename."
                            }
                        }
                    }
                    LibBtn {
                        text: root.pendingAction === "delete" ? "TAP AGAIN TO DELETE" : "DELETE SELECTED FILE"
                        accent: "#ef4444"
                        opacity: root.selectedRow !== null && root.selectedRow.source === "file" ? 1.0 : 0.4
                        onClicked: {
                            if (!(root.selectedRow !== null && root.selectedRow.source === "file")) {
                                root.statusText = "Select a Pi file first."
                                return
                            }
                            if (root.pendingAction !== "delete") { root.pendingAction = "delete"; return }
                            root.pendingAction = ""
                            if (Bridge.deleteLibraryFile(root.selectedRow.path)) {
                                root.statusText = "Deleted."
                                root.clearSelection()
                                root.applyFilter()
                            } else {
                                root.statusText = "Delete failed."
                            }
                        }
                    }
                    LibBtn {
                        text: root.pendingAction === "reinit" ? "TAP AGAIN TO REINIT" : "REINIT SELECTED SLOT"
                        accent: "#fbbf24"
                        opacity: root.isUserPatchRow() ? 1.0 : 0.4
                        onClicked: {
                            if (!root.isUserPatchRow()) {
                                root.statusText = "Select a keyboard user slot first."
                                return
                            }
                            if (root.pendingAction !== "reinit") {
                                root.pendingAction = "reinit"
                                root.statusText = "Slot auto-backs up to Pi first."
                                return
                            }
                            root.pendingAction = ""
                            var err = Bridge.reinitUserSlot(root.selectedRow.msb, root.selectedRow.lsb, root.selectedRow.pc)
                            root.statusText = err === "" ? "Slot reinitialized (backup kept)." : err
                        }
                    }
                    LibBtn {
                        text: "EXPORT SELECTED .SPECTRE"
                        accent: "#38bdf8"
                        opacity: root.isSpectreFileRow() ? 1.0 : 0.4
                        onClicked: {
                            root.pendingAction = ""
                            if (!root.isSpectreFileRow()) { root.statusText = "Select a Pi file first."; return }
                            var drive = root.firstUsbDrive()
                            if (drive === "") { root.statusText = "No USB drive found."; return }
                            var err = Bridge.exportLibraryFile(root.selectedRow.path, drive, "")
                            root.statusText = err === "" ? ("Exported to " + drive) : err
                        }
                    }
                    LibBtn {
                        text: "EXPORT LIVE .SYX"
                        accent: "#10b981"
                        onClicked: {
                            root.pendingAction = ""
                            var drive = root.firstUsbDrive()
                            if (drive === "") { root.statusText = "No USB drive found."; return }
                            var err = Bridge.exportLiveSyx(drive, Bridge.patchName)
                            root.statusText = err === "" ? ("Exported to " + drive) : err
                        }
                    }
                    LibBtn {
                        text: "IMPORT ALL FROM USB"
                        accent: "#fbbf24"
                        onClicked: {
                            root.pendingAction = ""
                            var drive = root.firstUsbDrive()
                            if (drive === "") { root.statusText = "No USB drive found."; return }
                            var n = Bridge.importUsbAll(drive)
                            root.statusText = "Imported " + n + " file(s)."
                            root.applyFilter()
                        }
                    }
                    LibBtn {
                        text: root.refreshingSlots ? "READING SLOTS…" : "REFRESH USER SLOTS"
                        accent: Theme.tone1
                        onClicked: {
                            if (root.refreshingSlots) return
                            root.pendingAction = ""
                            root.refreshingSlots = true
                            root.statusText = "Reading 256 user slots from keyboard…"
                            slotRefreshTimer.start()
                        }
                    }

                    Text {
                        Layout.fillWidth: true
                        visible: root.statusText !== ""
                        text: root.statusText
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: Theme.textDim
                        wrapMode: Text.Wrap
                        maximumLineCount: 3
                        elide: Text.ElideRight
                    }

                    Item { Layout.fillHeight: true }

                    Rectangle {
                        Layout.fillWidth: true
                        height: ScaleMetrics.dp(40)
                        radius: 4
                        color: "#10141d"
                        border.color: Theme.borderCard
                        border.width: 1
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 4
                            Text { text: "ACTIVE SOUND:"; font.pixelSize: ScaleMetrics.sp(7); color: Theme.textDim }
                            Text { text: Bridge.patchName; font.bold: true; font.pixelSize: ScaleMetrics.sp(9); color: Theme.tone1; elide: Text.ElideRight }
                        }
                    }
                }
            }
        }
    }

    // Deferred slot refresh (blocking ~256 reads; lets the status paint first).
    Timer {
        id: slotRefreshTimer
        interval: 80
        repeat: false
        running: false
        onTriggered: {
            var n = -1
            try { n = Bridge.refreshUserSlotNames() } catch (e) { n = -1 }
            root.refreshingSlots = false
            if (n < 0) {
                root.statusText = "No synthesizer connected."
            } else {
                root.statusText = n === 0 ? "User slots already up to date." : ("Updated " + n + " slot(s).")
            }
            root.applyFilter()
        }
    }

    RenameModal {
        id: renameModal
    }

    component LibBtn: Rectangle {
        id: lb
        property string text: "ACTION"
        property color accent: Theme.primary
        signal clicked()

        Layout.fillWidth: true
        height: ScaleMetrics.dp(34)
        radius: 4
        color: lbMouse.pressed ? Theme.bgCardActive : "#10141d"
        border.color: lb.accent
        border.width: 1

        Text {
            anchors.centerIn: parent
            text: lb.text
            font.bold: true
            font.pixelSize: ScaleMetrics.sp(8)
            color: lb.accent
        }
        MouseArea {
            id: lbMouse
            anchors.fill: parent
            onClicked: lb.clicked()
        }
    }
}
