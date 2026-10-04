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
    property var categories: ["ALL", "ACOUSTIC PIANO", "E.PIANO", "SYNTH LEAD", "SYNTH PAD", "BASS", "STRINGS", "USER CUSTOM"]
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
            Text {
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
                    MouseArea { anchors.fill: parent; onClicked: root.activeCatIdx = index }
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
                    model: root.patchList
                    spacing: ScaleMetrics.dp(4)

                    delegate: Rectangle {
                        width: ListView.view.width
                        height: ScaleMetrics.dp(36)
                        radius: 4
                        color: rowMouse.pressed ? Theme.bgCardActive : "#0d1017"
                        border.color: Theme.borderCard
                        border.width: 1

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: ScaleMetrics.dp(8)
                            spacing: ScaleMetrics.dp(8)

                            Text {
                                text: modelData.num
                                font.family: Theme.fontMono
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(9)
                                color: Theme.tone1
                            }
                            Text {
                                text: modelData.name
                                font.bold: true
                                font.pixelSize: ScaleMetrics.sp(10)
                                color: Theme.textPrimary
                            }
                            Item { Layout.fillWidth: true }
                            Text {
                                text: modelData.cat
                                font.pixelSize: ScaleMetrics.sp(8)
                                color: Theme.textDim
                            }
                            Text {
                                text: modelData.fav ? "★" : "☆"
                                font.pixelSize: ScaleMetrics.sp(12)
                                color: modelData.fav ? "#fbbf24" : Theme.textDim
                            }
                        }
                        MouseArea {
                            id: rowMouse
                            anchors.fill: parent
                            onClicked: Bridge.setPatchName(modelData.num + " " + modelData.name, "PATCH")
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

                    LibBtn { text: "STORE / WRITE TO USER MEM"; accent: Theme.tone1 }
                    LibBtn { text: "RENAME CURRENT PATCH"; accent: Theme.tone2 }
                    LibBtn { text: "EXPORT AS .SYX SYSEX"; accent: "#10b981" }
                    LibBtn { text: "EXPORT AS .SPECTRE BUNDLE"; accent: "#38bdf8" }
                    LibBtn { text: "IMPORT FROM USB DRIVE"; accent: "#fbbf24" }

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

    component LibBtn: Rectangle {
        id: lb
        property string text: "ACTION"
        property color accent: Theme.primary

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
        }
    }
}
