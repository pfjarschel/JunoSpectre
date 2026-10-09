import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

// Macro edit modal: rename (virtual keyboard) + assigned-target list with
// polarity toggle, stepped depth (25/50/75/100), remove; full-width ADD opens
// the parameter picker overlay; DONE closes.
Rectangle {
    id: root
    anchors.fill: parent
    color: Qt.rgba(0.02, 0.03, 0.04, 0.85)
    visible: false
    z: 1000

    property int targetMacro: 1
    property color macroColor: Theme.primary
    property var linkList: []
    property bool keyboardVisible: false
    readonly property var depthSteps: [0.25, 0.5, 0.75, 1.0]
    readonly property bool perform: Bridge.soundMode === "PERFORM"

    function open(macroIndex) {
        targetMacro = Math.max(1, Math.min(8, macroIndex));
        const colors = [Theme.tone1, Theme.tone2, Theme.tone3, Theme.tone4,
            "#f59e0b", "#38bdf8", "#a855f7", "#ec4899"];
        macroColor = colors[targetMacro - 1];
        keyboardVisible = false;
        refreshLinks();
        visible = true;
    }

    function close() {
        visible = false;
        keyboardVisible = false;
        picker.close();
        partPicker.close();
    }

    // Part target label: [] = edited part, [0] = sounding parts, else P1 P3 / P2–P5
    function partsLabel(parts) {
        if (!parts || parts.length === 0) return "EDIT";
        if (parts.indexOf(0) >= 0) return "ALL";
        const out = [];
        let i = 0;
        while (i < parts.length) {
            let j = i;
            while (j + 1 < parts.length && parts[j + 1] === parts[j] + 1) j++;
            if (j - i >= 2) {
                out.push("P" + parts[i] + "–P" + parts[j]);
            } else {
                for (let k = i; k <= j; k++) out.push("P" + parts[k]);
            }
            i = j + 1;
        }
        return out.join(" ");
    }

    function linkAt(pos) {
        for (let i = 0; i < linkList.length; i++)
            if (linkList[i].pos === pos) return linkList[i];
        return null;
    }

    function refreshLinks() {
        linkList = Bridge.getMacroLinks(targetMacro);
        nameField.text = currentMacroName();
    }

    function currentMacroName() {
        if (Bridge.macroNames && Bridge.macroNames.length >= targetMacro)
            return Bridge.macroNames[targetMacro - 1];
        return "M" + targetMacro;
    }

    function depthLabel(d) {
        return Math.round(d * 100) + "%";
    }

    function nextDepth(d) {
        for (let i = 0; i < depthSteps.length; i++) {
            if (d < depthSteps[i] - 0.001) return depthSteps[i];
        }
        return depthSteps[0];
    }

    function fmtParam(x, hi) {
        return hi <= 1.5 ? (Math.round(x * 100) / 100).toFixed(2) : String(Math.round(x));
    }

    // Sounding endpoints in knob-travel order: value at -1 first, value at +1
    // second (so negative polarity reads high…low), clamped to the limits.
    function sweepRange(link) {
        let v = 0.0;
        if (Bridge.macroValues && Bridge.macroValues.length >= targetMacro)
            v = Bridge.macroValues[targetMacro - 1];
        const sd = (link.polarity >= 0 ? 1 : -1) * link.depth * link.span;
        const atMinus = Math.max(link.min, Math.min(link.max, link.liveValue + sd * (-1 - v)));
        const atPlus = Math.max(link.min, Math.min(link.max, link.liveValue + sd * (1 - v)));
        return fmtParam(atMinus, link.max) + "…" + fmtParam(atPlus, link.max);
    }

    function assignedKeyList() {
        const keys = [];
        for (let i = 0; i < linkList.length; i++) keys.push(linkList[i].key);
        return keys;
    }

    MouseArea {
        anchors.fill: parent
        onClicked: (mouse) => {
            var p = card.mapToItem(root, 0, 0);
            var inside = mouse.x >= p.x && mouse.x <= p.x + card.width
                      && mouse.y >= p.y && mouse.y <= p.y + card.height;
            if (!inside) root.close();
        }
    }

    Rectangle {
        id: card
        width: Math.min(parent.width - ScaleMetrics.dp(40), ScaleMetrics.dp(760))
        height: Math.min(parent.height - ScaleMetrics.dp(30), ScaleMetrics.dp(540))
        anchors.centerIn: parent
        color: Theme.bgCard
        radius: ScaleMetrics.dp(10)
        border.color: root.macroColor
        border.width: 1
        clip: true

        MouseArea { anchors.fill: parent }

        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: ScaleMetrics.dp(3)
            color: root.macroColor
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(12)
            spacing: ScaleMetrics.dp(8)

            // Header
            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: "MACRO M" + root.targetMacro + " — EDIT"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(13)
                    font.letterSpacing: 1.2
                    color: Theme.textPrimary
                }
                Item { Layout.fillWidth: true }
                Text {
                    text: root.linkList.length + " TARGETS"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(10)
                    color: Theme.textDim
                }
                Rectangle {
                    width: ScaleMetrics.dp(30)
                    height: ScaleMetrics.dp(30)
                    radius: ScaleMetrics.dp(6)
                    color: Theme.bgSurface
                    border.color: Theme.borderCard
                    border.width: 1
                    Text {
                        anchors.centerIn: parent
                        text: "✕"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(14)
                        color: Theme.textSecondary
                    }
                    MouseArea { anchors.fill: parent; onClicked: root.close() }
                }
            }

            // Rename row
            RowLayout {
                Layout.fillWidth: true
                spacing: ScaleMetrics.dp(8)
                Text {
                    text: "NAME"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(10)
                    color: Theme.textDim
                }
                Rectangle {
                    Layout.fillWidth: true
                    height: ScaleMetrics.dp(32)
                    radius: ScaleMetrics.dp(4)
                    color: Theme.bgApp
                    border.color: nameField.activeFocus ? root.macroColor : Theme.borderCard
                    border.width: 1
                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: ScaleMetrics.dp(8)
                        anchors.rightMargin: ScaleMetrics.dp(8)
                        TextInput {
                            id: nameField
                            Layout.fillWidth: true
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(13)
                            font.letterSpacing: 1.0
                            color: root.macroColor
                            maximumLength: 14
                            clip: true
                            onTextEdited: {
                                Bridge.setMacroName(root.targetMacro, text);
                            }
                            onActiveFocusChanged: {
                                if (activeFocus) root.keyboardVisible = true;
                            }
                        }
                        Rectangle {
                            width: ScaleMetrics.dp(28)
                            height: ScaleMetrics.dp(22)
                            radius: ScaleMetrics.dp(4)
                            color: root.keyboardVisible ? root.macroColor : Theme.bgSurface
                            border.color: Theme.borderCard
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: "⌨"
                                font.pixelSize: ScaleMetrics.sp(12)
                                color: root.keyboardVisible ? "#000000" : Theme.textSecondary
                            }
                            MouseArea {
                                anchors.fill: parent
                                onClicked: root.keyboardVisible = !root.keyboardVisible
                            }
                        }
                    }
                }
            }

            // Assigned targets: DIR = offset direction, AMT = offset amount, DEL = remove link
            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: ScaleMetrics.dp(6)
                Layout.rightMargin: ScaleMetrics.dp(6)
                spacing: ScaleMetrics.dp(6)
                visible: root.linkList.length > 0

                Item { Layout.fillWidth: true }
                Text {
                    visible: root.perform
                    Layout.preferredWidth: ScaleMetrics.dp(96)
                    text: "PARTS"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: Theme.textDim
                    horizontalAlignment: Text.AlignHCenter
                }
                Text {
                    Layout.preferredWidth: ScaleMetrics.dp(36)
                    text: "DIR"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: Theme.textDim
                    horizontalAlignment: Text.AlignHCenter
                }
                Text {
                    Layout.preferredWidth: ScaleMetrics.dp(64)
                    text: "AMT"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: Theme.textDim
                    horizontalAlignment: Text.AlignHCenter
                }
                Text {
                    Layout.preferredWidth: ScaleMetrics.dp(32)
                    text: "DEL"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: Theme.textDim
                    horizontalAlignment: Text.AlignHCenter
                }
            }

            ListView {
                id: linkView
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: ScaleMetrics.dp(4)
                model: root.linkList

                delegate: Rectangle {
                    width: ListView.view.width
                    height: ScaleMetrics.dp(48)
                    radius: ScaleMetrics.dp(6)
                    color: Theme.bgApp
                    border.color: Theme.borderCard
                    border.width: 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: ScaleMetrics.dp(6)
                        spacing: ScaleMetrics.dp(6)

                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.alignment: Qt.AlignVCenter
                            spacing: 1
                            Text {
                                Layout.fillWidth: true
                                text: modelData.title
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(11)
                                color: Theme.textPrimary
                                elide: Text.ElideRight
                            }
                            Text {
                                Layout.fillWidth: true
                                text: (!root.perform && modelData.perfOnly)
                                      ? modelData.category + " • performance mode only"
                                      : modelData.category + " • live " + root.fmtParam(modelData.liveValue, modelData.max)
                                        + " • " + root.sweepRange(modelData)
                                font.pixelSize: ScaleMetrics.sp(8)
                                font.family: Theme.fontMono
                                color: Theme.textDim
                            }
                        }

                        // Part target (PERFORM, part params only): EDIT / ALL / fixed parts
                        Item {
                            visible: root.perform
                            Layout.preferredWidth: ScaleMetrics.dp(96)
                            Layout.preferredHeight: ScaleMetrics.dp(28)
                            Rectangle {
                                id: partChip
                                anchors.fill: parent
                                visible: modelData.partScoped
                                radius: ScaleMetrics.dp(4)
                                readonly property bool fixed: modelData.parts.length > 0
                                color: Theme.bgSurface
                                border.color: fixed || (partPicker.visible && partPicker.linkPos === modelData.pos)
                                              ? root.macroColor : Theme.borderCard
                                border.width: 1
                                Text {
                                    anchors.fill: parent
                                    anchors.leftMargin: ScaleMetrics.dp(4)
                                    anchors.rightMargin: ScaleMetrics.dp(4)
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                    text: root.partsLabel(modelData.parts)
                                    elide: Text.ElideRight
                                    font.bold: true
                                    font.pixelSize: ScaleMetrics.sp(9)
                                    font.family: Theme.fontMono
                                    color: partChip.fixed ? root.macroColor : Theme.textSecondary
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: partPicker.open(modelData.pos, partChip)
                                }
                            }
                            Text {
                                anchors.centerIn: parent
                                visible: !modelData.partScoped
                                text: "—"
                                font.pixelSize: ScaleMetrics.sp(10)
                                color: Theme.textDim
                            }
                        }

                        // Polarity toggle
                        Rectangle {
                            width: ScaleMetrics.dp(36)
                            height: ScaleMetrics.dp(28)
                            radius: ScaleMetrics.dp(4)
                            color: modelData.polarity >= 0 ? root.macroColor : Theme.bgSurface
                            border.color: root.macroColor
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: modelData.polarity >= 0 ? "+" : "−"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(14)
                                color: modelData.polarity >= 0 ? "#000000" : root.macroColor
                            }
                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    Bridge.setMacroLink(root.targetMacro, modelData.pos,
                                        modelData.polarity >= 0 ? -1 : 1, modelData.depth);
                                    root.refreshLinks();
                                }
                            }
                        }

                        // Depth stepper (25/50/75/100)
                        Rectangle {
                            width: ScaleMetrics.dp(64)
                            height: ScaleMetrics.dp(28)
                            radius: ScaleMetrics.dp(4)
                            color: Theme.bgSurface
                            border.color: Theme.borderCard
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: root.depthLabel(modelData.depth)
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(11)
                                font.family: Theme.fontMono
                                color: Theme.textPrimary
                            }
                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    Bridge.setMacroLink(root.targetMacro, modelData.pos,
                                        modelData.polarity, root.nextDepth(modelData.depth));
                                    root.refreshLinks();
                                }
                            }
                        }

                        // Remove link (×, kept visually apart from DIR so it never reads as "minus")
                        Rectangle {
                            width: ScaleMetrics.dp(32)
                            height: ScaleMetrics.dp(28)
                            radius: ScaleMetrics.dp(4)
                            color: rmArea.pressed ? "#3f1a1a" : "#1c1214"
                            border.color: rmArea.pressed ? Theme.recording : "#7f2d2d"
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: "×"
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(14)
                                color: Theme.recording
                            }
                            MouseArea {
                                id: rmArea
                                anchors.fill: parent
                                onClicked: {
                                    Bridge.removeMacroTarget(root.targetMacro, modelData.pos);
                                    root.refreshLinks();
                                }
                            }
                        }
                    }
                }
            }

            Text {
                visible: root.linkList.length === 0
                Layout.fillWidth: true
                text: "No parameters — tap + ADD PARAMETER below."
                font.pixelSize: ScaleMetrics.sp(10)
                color: Theme.textDim
                horizontalAlignment: Text.AlignHCenter
            }

            // Full-width ADD
            Rectangle {
                Layout.fillWidth: true
                height: ScaleMetrics.dp(36)
                radius: ScaleMetrics.dp(6)
                color: addArea.pressed ? Theme.bgCardActive : Theme.bgApp
                border.color: root.macroColor
                border.width: 1
                Text {
                    anchors.centerIn: parent
                    text: "+  ADD PARAMETER"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(11)
                    font.letterSpacing: 1.0
                    color: root.macroColor
                }
                MouseArea {
                    id: addArea
                    anchors.fill: parent
                    onClicked: {
                        picker.assignedKeys = root.assignedKeyList();
                        picker.open(root.targetMacro, root.macroColor);
                    }
                }
            }

            VirtualKeyboard {
                Layout.fillWidth: true
                Layout.preferredHeight: ScaleMetrics.dp(165)
                visible: root.keyboardVisible && !picker.visible
                accentColor: root.macroColor
                onKeyClicked: (key) => {
                    if (nameField.text.length < 14) {
                        nameField.text += key.toUpperCase();
                        Bridge.setMacroName(root.targetMacro, nameField.text);
                    }
                }
                onBackspaceClicked: {
                    if (nameField.text.length > 0) {
                        nameField.text = nameField.text.slice(0, -1);
                        Bridge.setMacroName(root.targetMacro, nameField.text);
                    }
                }
                onClearClicked: {
                    nameField.text = "";
                    Bridge.setMacroName(root.targetMacro, nameField.text);
                }
                onCloseClicked: { root.keyboardVisible = false; }
            }

            // Footer
            RowLayout {
                Layout.fillWidth: true
                Text {
                    Layout.fillWidth: true
                    text: "Knob −1..1 • value ±% • double-tap centers • 0 = base sound"
                    font.pixelSize: ScaleMetrics.sp(9)
                    color: Theme.textDim
                }
                Rectangle {
                    width: ScaleMetrics.dp(90)
                    height: ScaleMetrics.dp(30)
                    radius: ScaleMetrics.dp(5)
                    color: root.macroColor
                    Text {
                        anchors.centerIn: parent
                        text: "DONE"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(11)
                        color: "#000000"
                    }
                    MouseArea { anchors.fill: parent; onClicked: root.close() }
                }
            }
        }

        // Part target picker (opened from a link's PARTS chip)
        Item {
            id: partPicker
            anchors.fill: parent
            visible: false
            z: 60

            property int linkPos: -1
            readonly property var parts: {
                const l = root.linkAt(linkPos);
                return l ? l.parts : [];
            }
            readonly property bool editMode: parts.length === 0
            readonly property bool allMode: parts.indexOf(0) >= 0

            // Open below anchorItem (above it if there's no room), kept inside the card
            function open(pos, anchorItem) {
                linkPos = pos;
                const margin = ScaleMetrics.dp(8);
                const below = anchorItem.mapToItem(partPicker, 0, anchorItem.height + ScaleMetrics.dp(4));
                partPanel.x = Math.max(margin, Math.min(below.x + anchorItem.width - partPanel.width,
                                                        partPicker.width - partPanel.width - margin));
                const y = (below.y + partPanel.height <= partPicker.height - margin)
                          ? below.y
                          : anchorItem.mapToItem(partPicker, 0, 0).y - partPanel.height - ScaleMetrics.dp(4);
                partPanel.y = Math.max(margin, Math.min(y, partPicker.height - partPanel.height - margin));
                visible = true;
            }

            function close() {
                visible = false;
            }

            MouseArea {
                anchors.fill: parent
                onClicked: partPicker.close()
            }

            Rectangle {
                id: partPanel
                width: ScaleMetrics.dp(8 * 34 + 16)
                height: partCol.implicitHeight + ScaleMetrics.dp(16)
                radius: ScaleMetrics.dp(6)
                color: Theme.bgSurface
                border.color: root.macroColor
                border.width: 1

                MouseArea { anchors.fill: parent }  // swallow taps between buttons

                ColumnLayout {
                    id: partCol
                    anchors.fill: parent
                    anchors.margins: ScaleMetrics.dp(8)
                    spacing: ScaleMetrics.dp(6)

                    // EDIT = follows the edited part; ALL = every sounding part
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: ScaleMetrics.dp(4)
                        Repeater {
                            model: [ { key: "edit", label: "EDIT PART" }, { key: "all", label: "ALL SOUNDING" } ]
                            delegate: Rectangle {
                                readonly property bool active: modelData.key === "edit" ? partPicker.editMode
                                                                                        : partPicker.allMode
                                Layout.fillWidth: true
                                height: ScaleMetrics.dp(26)
                                radius: 3
                                color: active ? root.macroColor : Theme.bgApp
                                border.color: active ? root.macroColor : Theme.borderCard
                                border.width: 1
                                Text {
                                    anchors.centerIn: parent
                                    text: modelData.label
                                    font.bold: true
                                    font.pixelSize: ScaleMetrics.sp(8)
                                    color: parent.active ? Theme.bgApp : Theme.textSecondary
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: {
                                        Bridge.setMacroLinkPartMode(root.targetMacro, partPicker.linkPos, modelData.key);
                                        root.refreshLinks();
                                    }
                                }
                            }
                        }
                    }

                    Text {
                        text: "OR FIXED PARTS"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(8)
                        font.letterSpacing: 1.0
                        color: Theme.textDim
                    }

                    GridLayout {
                        columns: 8
                        rowSpacing: ScaleMetrics.dp(4)
                        columnSpacing: ScaleMetrics.dp(4)
                        Repeater {
                            model: 16
                            delegate: Rectangle {
                                readonly property int part: index + 1
                                readonly property bool isOn: partPicker.parts.indexOf(part) >= 0
                                width: ScaleMetrics.dp(30)
                                height: ScaleMetrics.dp(30)
                                radius: 3
                                color: isOn ? root.macroColor : Theme.bgApp
                                border.color: isOn ? root.macroColor : Theme.borderCard
                                border.width: 1
                                Text {
                                    anchors.centerIn: parent
                                    text: "P" + parent.part
                                    font.bold: true
                                    font.pixelSize: ScaleMetrics.sp(8)
                                    color: parent.isOn ? Theme.bgApp : Theme.textSecondary
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: {
                                        Bridge.toggleMacroLinkPart(root.targetMacro, partPicker.linkPos, parent.part);
                                        root.refreshLinks();
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        // Embedded picker overlay
        MacroTargetPicker {            id: picker
            onAddRequested: (key) => {
                Bridge.addMacroTarget(root.targetMacro, key);
                root.refreshLinks();
                picker.assignedKeys = root.assignedKeyList();
                picker.refreshTargets();
            }
            onCloseRequested: { picker.close(); }
        }
    }
}
