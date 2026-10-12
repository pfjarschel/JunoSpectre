pragma ValueTypeBehavior: Copy
import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

// MIDI controller bindings: pick a target (same catalog as macros, plus
// the macros themselves), move a control, done. Each binding can be
// absolute / momentary / toggle, pickup or jump, with a range.
Rectangle {
    id: root
    color: Theme.bgCard
    radius: ScaleMetrics.dp(8)
    border.color: Theme.borderCard
    border.width: 1

    property var bindings: Bridge.controlBindings
    property bool showAll: false
    property var shown: {
        if (root.showAll) return root.bindings
        var out = []
        for (var i = 0; i < root.bindings.length; i++)
            if (root.bindings[i].active) out.push(root.bindings[i])
        return out
    }
    property string learnTitle: Bridge.controlLearnTitle
    property bool learning: Bridge.controlLearnTarget !== ""
    property var presets: []
    property bool presetsOpen: false
    property string presetMessage: ""
    // Scope for new bindings ("" everywhere, "MODE:PATCH", "MODE:PERFORM" or a page)
    property string learnContext: ""
    property string learnContextTitle: "EVERYWHERE"
    property var contexts: []
    property int contextFor: -2          // -1 = learn scope, >= 0 = binding row, -2 = closed

    function openContexts(forIndex) {
        root.contexts = Bridge.controlContexts()
        root.contextFor = forIndex
    }

    readonly property color accent: Theme.pageAccent

    function rangeName(lo, hi) {
        if (lo === 0 && hi === 1) return "full"
        if (lo === 1 && hi === 0) return "invert"
        if (lo === 0.5 && hi === 1) return "upper"
        if (lo === 0.5 && hi === 0) return "lower"
        return "custom"
    }
    function rangeLabel(b) {
        var r = rangeName(b.lo, b.hi)
        if (b.macro) return { full: "−1…+1", invert: "+1…−1", upper: "0…+1", lower: "0…−1", custom: "CUSTOM" }[r]
        return { full: "FULL", invert: "INVERT", upper: "UPPER HALF", lower: "LOWER HALF", custom: "CUSTOM" }[r]
    }
    function nextRange(b) {
        var order = ["full", "invert", "upper", "lower"]
        var i = order.indexOf(rangeName(b.lo, b.hi))
        return order[(i + 1) % order.length]
    }
    function nextBehavior(v) {
        return { absolute: "momentary", momentary: "toggle", toggle: "latch", latch: "absolute" }[v]
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: ScaleMetrics.dp(10)
        spacing: ScaleMetrics.dp(8)

        RowLayout {
            Layout.fillWidth: true
            spacing: ScaleMetrics.dp(8)
            Rectangle {
                width: ScaleMetrics.dp(8); height: ScaleMetrics.dp(8); radius: 4
                color: root.accent
            }
            Text {
                text: "MIDI CONTROL"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(12)
                font.letterSpacing: 1.2
                color: Theme.textPrimary
            }
            HeadButton {
                text: root.showAll ? ("ALL " + root.bindings.length) : ("ACTIVE NOW " + root.shown.length + "/" + root.bindings.length)
                tint: root.showAll ? Theme.textSecondary : Theme.pageAccent
                onClicked: root.showAll = !root.showAll
            }
            Item { Layout.fillWidth: true }
            Text { text: "NEW:"; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textDim }
            HeadButton {
                text: root.learnContextTitle
                icon: "down"
                iconAfter: true
                tint: Theme.textSecondary
                onClicked: root.openContexts(-1)
            }
            HeadButton {
                text: "+ ASSIGN"
                tint: root.accent
                onClicked: { picker.open(0, root.accent) }
            }
            HeadButton {
                text: "PRESETS"
                tint: Theme.pageAccent
                onClicked: { root.presets = Bridge.controlPresets(); root.presetMessage = ""; root.presetsOpen = true }
            }
            HeadButton {
                text: "CLEAR ALL"
                tint: Theme.recording
                enabled: root.bindings.length > 0
                onClicked: clearConfirm.visible = true
            }
        }

        // Learn banner
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: ScaleMetrics.dp(36)
            visible: root.learning
            radius: ScaleMetrics.dp(4)
            color: Theme.tint(Theme.warning, 0.12)
            border.color: Theme.warning
            border.width: 1
            RowLayout {
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(8)
                spacing: ScaleMetrics.dp(8)
                Rectangle {
                    width: ScaleMetrics.dp(10); height: width; radius: width / 2
                    color: root.accent
                    SequentialAnimation on opacity {
                        running: root.learning
                        loops: Animation.Infinite
                        NumberAnimation { to: 0.2; duration: 450 }
                        NumberAnimation { to: 1.0; duration: 450 }
                    }
                }
                Text {
                    Layout.fillWidth: true
                    text: "MOVE A KNOB, FADER OR BUTTON FOR  " + root.learnTitle + "  ·  " + root.learnContextTitle
                    elide: Text.ElideRight
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(10)
                    color: root.accent
                }
                HeadButton { text: "CANCEL"; tint: Theme.textSecondary; onClicked: Bridge.startControlLearn("") }
            }
        }

        // Live activity
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: ScaleMetrics.dp(26)
            radius: ScaleMetrics.dp(4)
            color: Theme.bgTrack
            border.color: Theme.borderCard
            border.width: 1
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: ScaleMetrics.dp(8)
                anchors.rightMargin: ScaleMetrics.dp(8)
                Text { text: "LAST"; font.bold: true; font.pixelSize: ScaleMetrics.sp(8); color: Theme.textDim }
                Text {
                    Layout.fillWidth: true
                    text: Bridge.controlActivity || "Move a control on an enabled controller (Hardware page)"
                    elide: Text.ElideRight
                    font.family: Theme.fontMono
                    font.pixelSize: ScaleMetrics.sp(9)
                    color: Bridge.controlActivity ? Theme.textPrimary : Theme.textDim
                }
            }
        }

        // Bindings
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: ScaleMetrics.dp(6)
            color: Theme.bgApp
            border.color: Theme.borderCard
            border.width: 1

            ListView {
                id: list
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(6)
                clip: true
                spacing: 3
                model: root.shown
                boundsBehavior: Flickable.StopAtBounds

                delegate: Rectangle {
                    id: row
                    required property var modelData
                    property int index: modelData.index      // position in the full binding list
                    width: ListView.view.width
                    height: ScaleMetrics.dp(38)
                    radius: 3
                    color: index % 2 === 0 ? Theme.bgTrack : Theme.bgControl
                    opacity: (modelData.online ? 1.0 : 0.5) * (modelData.active ? 1.0 : 0.6)

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: ScaleMetrics.dp(8)
                        anchors.rightMargin: ScaleMetrics.dp(4)
                        spacing: ScaleMetrics.dp(6)

                        Text {
                            Layout.preferredWidth: ScaleMetrics.dp(190)
                            text: row.modelData.control
                            elide: Text.ElideRight
                            font.family: Theme.fontMono
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(9)
                            color: Theme.textPrimary
                        }
                        Text { text: "→"; font.pixelSize: ScaleMetrics.sp(10); color: Theme.textDim }
                        Text {
                            Layout.fillWidth: true
                            text: row.modelData.title
                            elide: Text.ElideRight
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(10)
                            color: row.modelData.macro ? Theme.catPerform : (row.modelData.action ? Theme.textPrimary : root.accent)
                        }
                        RowChip {
                            text: row.modelData.contextTitle
                            tint: row.modelData.context === "" ? Theme.textDim : Theme.pageAccent
                            onClicked: root.openContexts(row.index)
                        }
                        RowChip {
                            visible: row.modelData.action
                            text: row.modelData.behavior === "latch" ? "LATCH" : "PRESS"
                            onClicked: Bridge.setControlBindingOption(row.index, "behavior",
                                                                      row.modelData.behavior === "latch" ? "toggle" : "latch")
                        }
                        RowChip {
                            visible: !row.modelData.action
                            text: row.modelData.behavior.toUpperCase()
                            onClicked: Bridge.setControlBindingOption(row.index, "behavior", root.nextBehavior(row.modelData.behavior))
                        }
                        RowChip {
                            visible: !row.modelData.action && row.modelData.behavior === "absolute"
                            text: row.modelData.takeover.toUpperCase()
                            onClicked: Bridge.setControlBindingOption(row.index, "takeover",
                                { pickup: "scale", scale: "jump", jump: "pickup" }[row.modelData.takeover])
                        }
                        RowChip {
                            visible: !row.modelData.action
                            text: root.rangeLabel(row.modelData)
                            onClicked: Bridge.setControlBindingOption(row.index, "range", root.nextRange(row.modelData))
                        }
                        RowChip {
                            icon: "close"
                            tint: Theme.recording
                            onClicked: Bridge.removeControlBinding(row.index)
                        }
                    }
                }

                Text {
                    anchors.centerIn: parent
                    width: parent.width * 0.7
                    visible: root.shown.length === 0
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                    text: root.bindings.length === 0
                          ? "No bindings yet.\n+ ASSIGN picks a target, then move a control. PRESETS loads a ready layout."
                          : "No binding is active on this page and mode.\nTap ACTIVE NOW to show all."
                    font.pixelSize: ScaleMetrics.sp(10)
                    color: Theme.textDim
                }
            }
        }
    }

    MacroTargetPicker {
        id: picker
        midiMode: true
        onAddRequested: (key) => {
            picker.close()
            Bridge.startControlLearn(key, root.learnContext)
        }
        onCloseRequested: picker.close()
    }

    // Presets
    Rectangle {
        anchors.fill: parent
        visible: root.presetsOpen
        color: Theme.scrim
        z: 20
        MouseArea { anchors.fill: parent; onClicked: root.presetsOpen = false }
        Rectangle {
            width: Math.min(parent.width - ScaleMetrics.dp(60), ScaleMetrics.dp(560))
            height: Math.min(parent.height - ScaleMetrics.dp(40), ScaleMetrics.dp(400))
            anchors.centerIn: parent
            radius: ScaleMetrics.dp(10)
            color: Theme.bgCard
            border.color: Theme.pageAccent
            border.width: 1
            MouseArea { anchors.fill: parent }
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(12)
                spacing: ScaleMetrics.dp(8)
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "CONTROLLER PRESETS"; font.bold: true; font.pixelSize: ScaleMetrics.sp(11); color: Theme.textPrimary }
                    Item { Layout.fillWidth: true }
                    HeadButton {
                        text: "SAVE CURRENT…"
                        tint: Theme.pageAccent
                        enabled: root.bindings.length > 0
                        onClicked: { root.presetsOpen = false; presetName.openControlPreset("My layout") }
                    }
                    HeadButton { icon: "close"; tint: Theme.textSecondary; onClicked: root.presetsOpen = false }
                }
                Text {
                    Layout.fillWidth: true
                    text: "Loading replaces all current bindings."
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: Theme.textDim
                }
                Text {
                    Layout.fillWidth: true
                    visible: root.presetMessage !== ""
                    text: root.presetMessage
                    wrapMode: Text.WordWrap
                    font.pixelSize: ScaleMetrics.sp(9)
                    color: Theme.warning
                }
                ListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: 4
                    model: root.presets
                    delegate: Rectangle {
                        id: prow
                        required property var modelData
                        width: ListView.view.width
                        height: ScaleMetrics.dp(52)
                        radius: 4
                        color: Theme.bgControl
                        border.color: Theme.borderCard
                        border.width: 1
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: ScaleMetrics.dp(8)
                            spacing: ScaleMetrics.dp(8)
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Text {
                                    Layout.fillWidth: true
                                    text: prow.modelData.name + "  ·  " + prow.modelData.count + " bindings"
                                          + (prow.modelData.source === "user" ? "  ·  YOURS" : "")
                                    elide: Text.ElideRight
                                    font.bold: true
                                    font.pixelSize: ScaleMetrics.sp(10)
                                    color: Theme.textPrimary
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: prow.modelData.description
                                    elide: Text.ElideRight
                                    font.pixelSize: ScaleMetrics.sp(8)
                                    color: Theme.textDim
                                }
                            }
                            HeadButton {
                                text: "LOAD"
                                tint: Theme.pageAccent
                                onClicked: {
                                    root.presetMessage = Bridge.loadControlPreset(prow.modelData.file)
                                    if (root.presetMessage === "") root.presetsOpen = false
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // Clear confirmation
    Rectangle {
        id: clearConfirm
        anchors.fill: parent
        visible: false
        color: Theme.scrim
        z: 21
        MouseArea { anchors.fill: parent; onClicked: clearConfirm.visible = false }
        Rectangle {
            width: ScaleMetrics.dp(340); height: ScaleMetrics.dp(130)
            anchors.centerIn: parent
            radius: ScaleMetrics.dp(8)
            color: Theme.bgCard
            border.color: Theme.recording
            border.width: 1
            MouseArea { anchors.fill: parent }
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: ScaleMetrics.dp(14)
                Text {
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    text: "Remove all " + root.bindings.length + " bindings?"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(11)
                    color: Theme.textPrimary
                }
                RowLayout {
                    Layout.fillWidth: true
                    Item { Layout.fillWidth: true }
                    HeadButton { text: "KEEP"; tint: Theme.textSecondary; onClicked: clearConfirm.visible = false }
                    HeadButton {
                        text: "REMOVE ALL"
                        tint: Theme.recording
                        onClicked: { Bridge.clearControlBindings(); clearConfirm.visible = false }
                    }
                }
            }
        }
    }

    // Context chooser (learn scope or one binding)
    Rectangle {
        anchors.fill: parent
        visible: root.contextFor > -2
        color: Theme.scrim
        z: 21
        MouseArea { anchors.fill: parent; onClicked: root.contextFor = -2 }
        Rectangle {
            width: Math.min(parent.width - ScaleMetrics.dp(60), ScaleMetrics.dp(560))
            height: ctxCol.implicitHeight + ScaleMetrics.dp(24)
            anchors.centerIn: parent
            radius: ScaleMetrics.dp(10)
            color: Theme.bgCard
            border.color: Theme.pageAccent
            border.width: 1
            MouseArea { anchors.fill: parent }
            ColumnLayout {
                id: ctxCol
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: ScaleMetrics.dp(12)
                spacing: ScaleMetrics.dp(8)
                Text {
                    text: root.contextFor === -1 ? "NEW BINDINGS APPLY…" : "THIS BINDING APPLIES…"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(11)
                    color: Theme.textPrimary
                }
                Text {
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    text: "A control can have one binding per scope. On a page, its page binding wins, then the sound mode's, then the everywhere one."
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: Theme.textDim
                }
                Flow {
                    Layout.fillWidth: true
                    spacing: ScaleMetrics.dp(4)
                    Repeater {
                        model: root.contexts
                        delegate: SpButton {
                            id: cchip
                            required property var modelData
                            property bool sel: root.contextFor === -1 ? root.learnContext === modelData.key : (root.contextFor >= 0 && root.bindings[root.contextFor]
                            && root.bindings[root.contextFor].context === modelData.key)
                            implicitWidth: label.implicitWidth + ScaleMetrics.dp(16)
                            implicitHeight: ScaleMetrics.dp(28)
                            text: cchip.modelData.title
                            fontSize: 8
                            checked: sel
                            onClicked: {
                                if (root.contextFor === -1) {
                                    root.learnContext = cchip.modelData.key
                                    root.learnContextTitle = cchip.modelData.title
                                } else {
                                    Bridge.setControlBindingOption(root.contextFor, "context", cchip.modelData.key)
                                }
                                root.contextFor = -2
                            }
                        }
                    }
                }
            }
        }
    }

    RenameModal {
        id: presetName
        anchors.fill: parent
        visible: false
        z: 22
    }

    component HeadButton: SpButton {
        property color tint: Theme.textSecondary
        accent: tint
        variant: "outline"
        implicitHeight: ScaleMetrics.dp(28)
        horizontalPadding: ScaleMetrics.dp(10)
    }

    component RowChip: SpButton {
        property color tint: Theme.textSecondary
        accent: tint
        variant: "outline"
        compact: true
        implicitWidth: Math.max(ScaleMetrics.dp(30), label.implicitWidth + ScaleMetrics.dp(14))
        implicitHeight: ScaleMetrics.dp(28)
    }
}
