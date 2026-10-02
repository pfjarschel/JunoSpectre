import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

Rectangle {
    id: root
    height: ScaleMetrics.dp(44)
    color: Theme.bgCard
    border.color: Theme.borderCard
    border.width: 1

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: ScaleMetrics.dp(12)
        anchors.rightMargin: ScaleMetrics.dp(12)
        spacing: ScaleMetrics.dp(10)

        // Logo / Title
        RowLayout {
            spacing: ScaleMetrics.dp(6)
            Rectangle {
                width: ScaleMetrics.dp(8)
                height: ScaleMetrics.dp(8)
                radius: width / 2
                color: Theme.tone1
            }
            Text {
                text: "JUNO SPECTRE"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(12)
                font.letterSpacing: 1.2
                color: Theme.textPrimary
            }
        }

        // Synth Mode Badge
        Rectangle {
            height: ScaleMetrics.dp(24)
            width: ScaleMetrics.dp(56)
            radius: ScaleMetrics.dp(4)
            color: Bridge.soundMode === "PATCH" ? "#1e293b" : "#2d1b4e"
            border.color: Bridge.soundMode === "PATCH" ? Theme.primary : Theme.tone2
            border.width: 1

            Text {
                anchors.centerIn: parent
                text: Bridge.soundMode
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(10)
                color: Bridge.soundMode === "PATCH" ? Theme.primary : Theme.tone2
            }
        }

        // Active Patch Name Display
        Rectangle {
            Layout.preferredWidth: ScaleMetrics.dp(150)
            Layout.fillWidth: false
            height: ScaleMetrics.dp(28)
            radius: ScaleMetrics.dp(4)
            color: Theme.bgApp
            border.color: Theme.borderCard
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: ScaleMetrics.dp(8)
                anchors.rightMargin: ScaleMetrics.dp(8)

                Text {
                    Layout.fillWidth: true
                    text: Bridge.patchName
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(11)
                    color: Theme.textPrimary
                    elide: Text.ElideRight
                }
            }
        }

        // View Navigation Tabs
        Rectangle {
            Layout.fillWidth: true
            height: ScaleMetrics.dp(32)
            radius: ScaleMetrics.dp(6)
            color: Theme.bgApp
            border.color: Theme.borderCard
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.margins: 2
                spacing: 2

                NavTab {
                    Layout.fillWidth: true
                    viewKey: "VECTOR"
                    label: "VECTOR"
                    activeColor: Theme.tone1
                }

                NavTab {
                    Layout.fillWidth: true
                    viewKey: "WAVETABLE"
                    label: "WAVETABLE"
                    activeColor: Theme.tone3
                }

                NavTab {
                    Layout.fillWidth: true
                    viewKey: "MACROS"
                    label: "MACROS"
                    activeColor: Theme.tone2
                }

                NavTab {
                    Layout.fillWidth: true
                    viewKey: "PATCH EDIT"
                    label: "PATCH EDIT"
                    activeColor: "#38bdf8"
                }

                NavTab {
                    Layout.fillWidth: true
                    viewKey: "PERF MIXER"
                    label: "PERF MIXER"
                    activeColor: "#a855f7"
                }

                NavTab {
                    Layout.fillWidth: true
                    viewKey: "EFFECTS"
                    label: "EFFECTS"
                    activeColor: "#ec4899"
                }
            }
        }

        // BPM Display
        Rectangle {
            height: ScaleMetrics.dp(28)
            width: ScaleMetrics.dp(68)
            radius: ScaleMetrics.dp(4)
            color: Theme.bgApp
            border.color: Theme.borderCard
            border.width: 1

            RowLayout {
                anchors.centerIn: parent
                spacing: ScaleMetrics.dp(4)

                Text {
                    text: "BPM"
                    font.pixelSize: ScaleMetrics.sp(9)
                    font.bold: true
                    color: Theme.textDim
                }
                Text {
                    text: Math.round(Bridge.bpm)
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(12)
                    color: Theme.tone3
                }
            }
        }

        // Panic Button (All Notes Off)
        Rectangle {
            height: ScaleMetrics.dp(28)
            width: ScaleMetrics.dp(54)
            radius: ScaleMetrics.dp(4)
            color: "#3f1a1a"
            border.color: Theme.recording
            border.width: 1

            Text {
                anchors.centerIn: parent
                text: "PANIC"
                font.bold: true
                font.pixelSize: ScaleMetrics.sp(9)
                color: Theme.recording
            }

            MouseArea {
                anchors.fill: parent
                onClicked: Bridge.panic()
            }
        }
    }

    // Reusable Navigation Tab Component
    component NavTab: Rectangle {
        id: tabRoot
        property string viewKey: "VECTOR"
        property string label: "VECTOR"
        property color activeColor: Theme.primary

        property bool isActive: Bridge.activeView === viewKey

        Layout.fillHeight: true
        radius: ScaleMetrics.dp(4)
        color: isActive ? Theme.bgCardActive : "transparent"
        border.color: isActive ? activeColor : "transparent"
        border.width: 1

        Text {
            anchors.centerIn: parent
            text: tabRoot.label
            font.bold: tabRoot.isActive
            font.pixelSize: ScaleMetrics.sp(10)
            color: tabRoot.isActive ? Theme.textPrimary : Theme.textMuted
        }

        Rectangle {
            anchors.bottom: parent.bottom
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width * 0.6
            height: ScaleMetrics.dp(2)
            radius: 1
            color: tabRoot.activeColor
            visible: tabRoot.isActive
        }

        MouseArea {
            anchors.fill: parent
            onClicked: Bridge.setActiveView(tabRoot.viewKey)
        }
    }
}
