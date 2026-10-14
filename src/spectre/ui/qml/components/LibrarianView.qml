pragma ValueTypeBehavior: Copy
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
    property var kinds: ["", "patch", "drum", "performance", "playlist"]
    property var kindLabels: ["ALL", "PATCH", "DRUM", "PERF", "SETLIST"]
    // Library model. Bound declaratively (onCompleted proved unreliable for
    // nested views): app.py always sets the `patchLibrary` context property,
    // to an empty model when the library fails (Bridge.libraryError says why).
    readonly property var patchModel: patchLibrary
    property string searchText: ""

    Component.onCompleted: {
        // Model arrives pre-refreshed from app.py; just re-apply local state.
        root.applyFilter()
    }

    function applyFilter() {
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
                color: Theme.pageAccent
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
                visible: (Bridge.libraryError || "") !== ""
                color: Theme.tint(Theme.favorite, 0.2)
                radius: 3
                border.color: Theme.favorite
                border.width: 1
                Layout.preferredWidth: ScaleMetrics.dp(280)
                height: ScaleMetrics.dp(22)
                Text {
                    anchors.centerIn: parent
                    width: parent.width - ScaleMetrics.dp(8)
                    text: "LIBRARY OFFLINE: " + Bridge.libraryError
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(7)
                    color: Theme.favorite
                    elide: Text.ElideRight
                }
            }
            Text {
                text: "DISK & SYSEX STORAGE"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(9)
                color: Theme.textDim
            }
            Item { width: ScaleMetrics.dp(4) }
            // CANCEL: back to the previous view, no destination change
            SpButton {
                implicitWidth: ScaleMetrics.dp(72)
                implicitHeight: ScaleMetrics.dp(26)
                text: "CANCEL"
                onClicked: Bridge.cancelLibrarian()
            }
            // OK: close into the auditioned context (mixer / engine view)
            SpButton {
                implicitWidth: ScaleMetrics.dp(56)
                implicitHeight: ScaleMetrics.dp(26)
                icon: "check"
                text: "OK"
                variant: "outline"
                onClicked: Bridge.toggleLibrarian()
            }
        }

        // Part-pick banner (pick mode: taps assign, CANCEL above aborts, OK goes to mixer)
        Rectangle {
            visible: Bridge.librarianPickTarget > 0
            Layout.fillWidth: true
            Layout.preferredHeight: Bridge.librarianPickTarget > 0 ? ScaleMetrics.dp(30) : 0
            height: ScaleMetrics.dp(30)
            radius: ScaleMetrics.dp(4)
            color: Theme.tint(Theme.stagePart)
            border.color: Theme.stagePart
            border.width: 1
            Text {
                anchors.fill: parent
                anchors.leftMargin: ScaleMetrics.dp(10)
                anchors.rightMargin: ScaleMetrics.dp(10)
                verticalAlignment: Text.AlignVCenter
                text: "PICKING PATCH FOR PART " + Bridge.librarianPickTarget + " — taps audition & assign, OK when done"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(9)
                color: Theme.stagePart
                elide: Text.ElideRight
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
                delegate: SpButton {
                    implicitWidth: ScaleMetrics.dp(64)
                    implicitHeight: ScaleMetrics.dp(24)
                    text: modelData
                    fontSize: 8
                    checked: root.activeKindIdx === index
                    onClicked: { root.activeKindIdx = index; root.applyFilter() }
                }
            }
            SpButton {
                implicitWidth: ScaleMetrics.dp(76)
                implicitHeight: ScaleMetrics.dp(24)
                text: "USER SLOTS"
                fontSize: 8
                checked: root.userSlotsOnly
                onClicked: root.setSourceFilter("slots")
            }
            SpButton {
                implicitWidth: ScaleMetrics.dp(76)
                implicitHeight: ScaleMetrics.dp(24)
                text: "USER FILES"
                fontSize: 8
                checked: root.userFilesOnly
                onClicked: root.setSourceFilter("files")
            }
            Item { Layout.fillWidth: true }
            Text {
                text: root.rowCountText()
                font.pixelSize: ScaleMetrics.sp(8)
                color: Theme.textSecondary
            }
            SpButton {
                implicitWidth: ScaleMetrics.dp(52)
                implicitHeight: ScaleMetrics.dp(24)
                icon: "favorite"
                iconFilled: root.favOnly
                text: "Fav"
                fontSize: 8
                accent: Theme.favorite
                checked: root.favOnly
                onClicked: { root.favOnly = !root.favOnly; root.applyFilter() }
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
                            color: isActive ? Theme.tint(Theme.pageAccent) : Theme.bgControl
                            border.color: isActive ? Theme.pageAccent : Theme.borderCard
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
                                    color: isActive ? Theme.pageAccent : Theme.textSecondary
                                }
                                Text {
                                    text: label
                                    font.pixelSize: ScaleMetrics.sp(8)
                                    color: isActive ? Theme.pageAccent : Theme.textSecondary
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
            color: Theme.bgControl
            border.color: Theme.borderCard
            border.width: 1
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: ScaleMetrics.dp(8)
                anchors.rightMargin: ScaleMetrics.dp(6)
                spacing: ScaleMetrics.dp(6)
                Icon {
                    name: "search"
                    size: 13
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
                Icon {
                    visible: searchField.text.length > 0
                    name: "close"
                    size: 13
                    color: Theme.textDim
                    MouseArea {
                        anchors.fill: parent
                        onClicked: { searchField.text = ""; root.searchText = ""; root.applyFilter() }
                    }
                }
                SpButton {
                    implicitWidth: ScaleMetrics.dp(28)
                    implicitHeight: ScaleMetrics.dp(22)
                    icon: "keyboard"
                    fontSize: 12
                    checked: root.searchKbVisible
                    onClicked: { root.searchKbVisible = !root.searchKbVisible; if (root.searchKbVisible) searchField.forceActiveFocus() }
                }
            }
        }

        // Touch keyboard for search (below search, above list; list shrinks)
        VirtualKeyboard {
            Layout.fillWidth: true
            Layout.preferredHeight: ScaleMetrics.dp(140)
            visible: root.searchKbVisible
            accentColor: Theme.pageAccent
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
                    model: root.patchModel
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
                            color: parent.pressed ? Theme.pageAccent : Theme.borderActive
                            opacity: 0.9
                        }
                        background: Rectangle {
                            radius: width / 2
                            color: Theme.bgControl
                            opacity: 0.7
                        }
                    }

                    delegate: Rectangle {
                        width: ListView.view.width - ScaleMetrics.dp(16)
                        height: ScaleMetrics.dp(48)
                        radius: 4
                        color: rowMouse.pressed ? Theme.bgCardActive : Theme.bgControl
                        border.color: _selected ? Theme.pageAccent : Theme.borderCard
                        border.width: _selected ? 2 : 1

                        // PatchListModel roles: name/category/favorite/msb/lsb/pc/source/path/kind
                        property bool _selected: root.selectedPath !== "" && root.selectedPath === path
                        property string _num: msb >= 0 ? (lsb + ":" + pc) : "FILE"
                        property string _name: name
                        property string _cat: (category || "—") + (kind && kind !== "patch" ? " " + kind : "") + (source ? " • " + source : "")
                        property bool _fav: favorite

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: ScaleMetrics.dp(8)
                            spacing: ScaleMetrics.dp(8)

                            Text {
                                text: parent.parent._num
                                font.family: Theme.fontMono
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(9)
                                color: Theme.pageAccent
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
                            Icon {
                                name: "favorite"
                                filled: parent.parent._fav
                                size: 16
                                color: parent.parent._fav ? Theme.favorite : Theme.textDim
                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: function(mouse) {
                                        mouse.accepted = true
                                        root.patchModel.toggleFavorite(index)
                                    }
                                }
                            }
                        }
                        MouseArea {
                            id: rowMouse
                            anchors.fill: parent
                            onClicked: {
                                root.selectedPath = path
                                root.selectedIndex = index
                                root.selectedRow = root.patchModel.get(index)
                                root.pendingAction = ""
                                var ok = true
                                var wasPicking = Bridge.librarianPickTarget > 0
                                if (wasPicking) {
                                    if (kind === "performance" || kind === "playlist") {
                                        root.statusText = "Pick a patch or drum for Part " + Bridge.librarianPickTarget + " — not a " + kind + "."
                                    } else {
                                        var tgt = Bridge.librarianPickTarget
                                        ok = Bridge.pickPartPatch(msb, lsb, pc, path, name, kind)
                                        root.statusText = ok ? ("Part " + tgt + " ← " + name + ".") : "Assign failed."
                                    }
                                } else if (kind !== undefined && kind === "playlist") {
                                    ok = Bridge.loadSpectreFile(path)
                                    root.statusText = ok ? "Setlist loaded — OK opens the SETLIST page." : "Setlist load failed."
                                } else if (kind !== undefined && kind === "performance"
                                           && path !== undefined && String(path).slice(-8) === ".spectre") {
                                    // Pi file: the whole song (parts, snapshots, sequence)
                                    ok = Bridge.loadSpectreFile(path)
                                } else if (msb !== undefined && msb >= 0) {
                                    // Bank/PC audition + full read: a background job;
                                    // the result lands in onJobFinished("load")
                                    var isPerf = kind !== undefined && kind === "performance"
                                    if (Bridge.startLibraryLoad(isPerf ? "performance" : "patch", msb, lsb, pc, name)) {
                                        root.statusText = "Loading " + name + "…"
                                        return
                                    }
                                    root.statusText = "Busy with another keyboard job — try again in a moment."
                                    return
                                } else if (path !== undefined && String(path).slice(-8) === ".spectre") {
                                    ok = Bridge.loadSpectreFile(path)
                                } else {
                                    Bridge.setPatchName(name, "PATCH")
                                }
                                if (!wasPicking) {
                                    root.statusText = ok ? "" : "No synthesizer connected — browsing only."
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

                    LibBtn { text: "INITIALIZE ACTIVE PATCH (RAM)"; accent: Theme.warning; onClicked: { root.pendingAction = ""; Bridge.openInitPatchModal() } }
                    LibBtn {
                        text: "RENAME SELECTED"
                        accent: Theme.pageAccent
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
                        accent: Theme.recording
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
                        accent: Theme.warning
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
                        text: root.refreshingSlots
                              ? (Bridge.jobProgress >= 0 ? "READING SLOTS… " + Math.round(Bridge.jobProgress * 100) + "%" : "READING SLOTS…")
                              : "REFRESH USER SLOTS"
                        accent: Theme.pageAccent
                        onClicked: {
                            if (root.refreshingSlots) return
                            root.pendingAction = ""
                            root.refreshingSlots = Bridge.startSlotNameRefresh("patch")
                            root.statusText = root.refreshingSlots ? "Reading 256 user slots from keyboard…"
                                                                   : "Busy with another keyboard job — try again in a moment."
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
                        color: Theme.bgControl
                        border.color: Theme.borderCard
                        border.width: 1
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 4
                            Text { text: "ACTIVE SOUND:"; font.pixelSize: ScaleMetrics.sp(7); color: Theme.textDim }
                            Text { text: Bridge.patchName; font.bold: true; font.pixelSize: ScaleMetrics.sp(9); color: Theme.pageAccent; elide: Text.ElideRight }
                        }
                    }
                }
            }
        }
    }

    // Background jobs started here report back through jobFinished.
    Connections {
        target: Bridge
        function onJobFinished(name, result) {
            if (name === "slotNames" && root.refreshingSlots) {
                root.refreshingSlots = false
                if (result < 0) root.statusText = "No synthesizer connected."
                else root.statusText = result === 0 ? "User slots already up to date." : ("Updated " + result + " slot(s).")
                root.applyFilter()
            } else if (name === "load") {
                root.statusText = result ? "" : "No synthesizer connected — browsing only."
            }
        }
    }

    RenameModal {
        id: renameModal
    }

    component LibBtn: SpButton {
        variant: "outline"
        fontSize: Theme.fontXs
        Layout.fillWidth: true
        implicitHeight: ScaleMetrics.dp(34)
    }
}
