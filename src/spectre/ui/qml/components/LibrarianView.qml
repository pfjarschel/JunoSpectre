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

    property int activeCatIdx: 0
    property int activeKindIdx: 0
    property bool favOnly: false
    property string selectedPath: ""
    property int selectedIndex: -1
    property var selectedRow: null
    property string pendingAction: ""
    property string statusText: ""
    property bool showAllCats: false
    property string activeCode: ""
    property var kinds: ["", "patch", "drum", "performance"]
    property var kindLabels: ["ALL", "PATCH", "DRUM", "PERF"]
    property var categories: ["ALL", "ACOUSTIC PIANO", "E.PIANO", "SYNTH LEAD", "SYNTH PAD", "BASS", "STRINGS", "USER CUSTOM"]
    // Live library model (PatchListModel) when provided via context property
    // `patchLibrary` from app.py; null = fall back to the hardcoded demo list.
    property var patchModel: null
    property string searchText: ""
    property var patchList: [
        { num: "0001", name: "Grand Pno DS", cat: "ACOUSTIC PIANO", fav: true },
        { num: "0002", name: "Bright Grand", cat: "ACOUSTIC PIANO", fav: false },
        { num: "0025", name: "Pure EP", cat: "E.PIANO", fav: true },
        { num: "0104", name: "Juno 106 Lead", cat: "SYNTH LEAD", fav: true },
        { num: "0112", name: "JP-8000 Saw", cat: "SYNTH LEAD", fav: false },
        { num: "0180", name: "Warm Lush Pad", cat: "SYNTH PAD", fav: true },
        { num: "0210", name: "Spectre Vector 1", cat: "USER CUSTOM", fav: true },
        { num: "0211", name: "Wavetable Morph A", cat: "USER CUSTOM", fav: false }
    ]
    // Filtered fallback view (keeps old behavior when no live model is bound)
    property var filteredFallback: {
        if (root.activeCatIdx === 0) return root.patchList
        var cat = root.categories[root.activeCatIdx]
        return root.patchList.filter(function(p) { return p.cat === cat })
    }

    Component.onCompleted: {
        try {
            if (typeof patchLibrary !== "undefined" && patchLibrary) {
                root.patchModel = patchLibrary
                patchLibrary.refresh("", "ALL", false, "", 2500)
            }
        } catch (e) { root.patchModel = null }
    }

    // Roland 3-letter category codes per chip (mirrors core/categories.py).
    // USER CUSTOM is source-based (user files), not a category.
    property var chipCodes: {
        "ALL": [],
        "ACOUSTIC PIANO": ["PNO"],
        "E.PIANO": ["EP"],
        "SYNTH LEAD": ["HLD", "SLD"],
        "SYNTH PAD": ["BPD", "SPD"],
        "BASS": ["BS", "SBS"],
        "STRINGS": ["STR", "ORC"],
        "USER CUSTOM": []
    }

    function applyFilter() {
        if (!root.patchModel) return
        var chip = root.categories[root.activeCatIdx]
        var kind = root.kinds[root.activeKindIdx]
        var source = (chip === "USER CUSTOM") ? "file" : ""
        var codes = []
        if (root.activeCode !== "") {
            codes = [root.activeCode]
        } else if (chip !== "USER CUSTOM") {
            codes = root.chipCodes[chip] || []
        }
        root.patchModel.refresh(root.searchText, "ALL", root.favOnly, source, 2500, codes.join(","), kind)
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
                visible: root.patchModel === null
                color: "#3a2f10"
                radius: 3
                border.color: "#fbbf24"
                border.width: 1
                Layout.preferredWidth: ScaleMetrics.dp(220)
                height: ScaleMetrics.dp(22)
                Text {
                    anchors.centerIn: parent
                    text: "DEMO DATA — LIBRARY OFFLINE"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: "#fbbf24"
                }
            }
            Text {
                visible: root.patchModel !== null
                text: "DISK & SYSEX STORAGE"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(9)
                color: Theme.textDim
            }
        }

        // Category Filter Chips
        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(4)
            Repeater {
                model: root.categories
                delegate: Rectangle {
                    Layout.fillWidth: true
                    height: ScaleMetrics.dp(24)
                    radius: 3
                    color: root.activeCatIdx === index ? Theme.bgCardActive : "#10141d"
                    border.color: root.activeCatIdx === index ? "#60a5fa" : Theme.borderCard
                    border.width: 1
                    Text {
                        anchors.centerIn: parent
                        text: modelData
                        font.bold: root.activeCatIdx === index
                        font.pixelSize: ScaleMetrics.sp(8)
                        color: root.activeCatIdx === index ? "#60a5fa" : Theme.textDim
                    }
                    MouseArea { anchors.fill: parent; onClicked: { root.activeCatIdx = index; root.activeCode = ""; root.applyFilter() } }
                }
            }
        }

        // Kind tabs + full-category toggle + result count + favorites-only
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
                width: ScaleMetrics.dp(64)
                height: ScaleMetrics.dp(24)
                radius: 3
                color: root.showAllCats ? Theme.bgCardActive : "#10141d"
                border.color: root.showAllCats ? "#60a5fa" : Theme.borderCard
                border.width: 1
                Text {
                    anchors.centerIn: parent
                    text: root.activeCode !== "" ? root.activeCode : "CATS ≡"
                    font.bold: root.showAllCats || root.activeCode !== ""
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: (root.showAllCats || root.activeCode !== "") ? "#60a5fa" : Theme.textDim
                }
                MouseArea { anchors.fill: parent; onClicked: { root.showAllCats = !root.showAllCats } }
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

        // Full Roland category grid (all 38 codes; tap again to clear)
        Rectangle {
            Layout.fillWidth: true
            height: ScaleMetrics.dp(64)
            radius: 4
            color: Theme.bgApp
            border.color: Theme.borderCard
            border.width: 1
            visible: root.showAllCats && root.patchModel !== null
            Flickable {
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(5)
                contentWidth: catFlow.width
                contentHeight: catFlow.height
                clip: true
                interactive: true
                Flow {
                    id: catFlow
                    width: parent.width
                    spacing: ScaleMetrics.dp(4)
                    Repeater {
                        model: ["PNO","EP","KEY","BEL","MLT","ORG","ACD","HRM","AGT","EGT","DGT","BS","SBS","STR","ORC","HIT","WND","FLT","BRS","SBR","SAX","HLD","SLD","TEK","PLS","FX","SYN","BPD","SPD","VOX","PLK","ETH","FRT","PRC","SFX","BTS","DRM","CMB"]
                        delegate: Rectangle {
                            width: ScaleMetrics.dp(46); height: ScaleMetrics.dp(24)
                            radius: 3
                            color: root.activeCode === modelData ? Theme.bgCardActive : "#10141d"
                            border.color: root.activeCode === modelData ? "#60a5fa" : Theme.borderCard
                            border.width: 1
                            Text { anchors.centerIn: parent; text: modelData; font.bold: root.activeCode === modelData; font.pixelSize: ScaleMetrics.sp(8); color: root.activeCode === modelData ? "#60a5fa" : Theme.textDim }
                            MouseArea { anchors.fill: parent; onClicked: root.toggleCode(modelData) }
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
            TextInput {
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(6)
                verticalAlignment: Text.AlignVCenter
                font.pixelSize: ScaleMetrics.sp(10)
                color: Theme.textPrimary
                clip: true
                onTextChanged: { root.searchText = text; root.applyFilter() }
                Text {
                    anchors.fill: parent
                    verticalAlignment: Text.AlignVCenter
                    text: "Search patches…"
                    font.pixelSize: ScaleMetrics.sp(10)
                    color: Theme.textDim
                    visible: parent.text === ""
                }
            }
        }

        // Main List & Action Side-column
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: ScaleMetrics.dp(10)

            // Patch List Table
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: ScaleMetrics.dp(6)
                color: Theme.bgApp
                border.color: Theme.borderCard
                border.width: 1

                ListView {
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(6)
                    clip: true
                    model: root.patchModel !== null ? root.patchModel : root.filteredFallback
                    spacing: ScaleMetrics.dp(4)

                    delegate: Rectangle {
                        width: ListView.view.width
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

            // Right Action Column (~240dp)
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
