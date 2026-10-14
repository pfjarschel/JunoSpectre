pragma ValueTypeBehavior: Copy
import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

Rectangle {
    id: root
    height: ScaleMetrics.dp(54)
    color: Theme.bgCard
    border.color: Theme.borderCard
    border.width: 1

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: ScaleMetrics.dp(12)
        anchors.rightMargin: ScaleMetrics.dp(12)
        spacing: ScaleMetrics.dp(10)

        // Screens Launcher Trigger Button (fixed width in every mode)
        Rectangle {
            id: screensBtn
            Layout.preferredWidth: ScaleMetrics.dp(170)
            height: ScaleMetrics.dp(40)
            radius: ScaleMetrics.dp(6)
            color: screensArea.pressed ? Theme.bgCardActive : Theme.bgApp
            border.color: screensArea.pressed ? Theme.primary : Theme.borderCard
            border.width: 1

            readonly property color viewAccent: Theme.viewAccent(Bridge.activeView)

            RowLayout {
                anchors.centerIn: parent
                spacing: ScaleMetrics.dp(8)

                Rectangle {
                    width: ScaleMetrics.dp(20)
                    height: ScaleMetrics.dp(20)
                    radius: ScaleMetrics.dp(4)
                    color: Theme.bgSurface
                    Icon {
                        anchors.centerIn: parent
                        name: Icons.forView(Bridge.activeView)
                        size: 14
                        color: screensBtn.viewAccent
                    }
                }

                Text {
                    Layout.maximumWidth: screensBtn.width - ScaleMetrics.dp(60)
                    elide: Text.ElideRight
                    text: Bridge.activeView
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(11)
                    color: screensBtn.viewAccent
                }

                Icon {
                    name: "down"
                    size: 11
                    color: Theme.textSecondary
                }
            }

            MouseArea {
                id: screensArea
                anchors.fill: parent
                onClicked: Bridge.openScreensOverlay()
            }
        }

        // Synth Mode toggle (tap: PATCH <-> PERFORM)
        SpButton {
            implicitHeight: ScaleMetrics.dp(32)
            implicitWidth: ScaleMetrics.dp(60)
            text: Bridge.soundMode
            fontSize: 10
            accent: Bridge.soundMode === "PATCH" ? Theme.catSynth : Theme.catPerform
            checked: true
            onClicked: Bridge.setSoundMode(Bridge.soundMode === "PERFORM" ? "PATCH" : "PERFORM")
        }

        // Active Patch Name Display with Sync, Init and Save Buttons
        // (takes the spare width in every mode, so the header never resizes)
        Rectangle {
            Layout.fillWidth: true
            height: ScaleMetrics.dp(38)
            radius: ScaleMetrics.dp(4)
            color: Theme.bgApp
            border.color: Theme.borderCard
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: ScaleMetrics.dp(8)
                anchors.rightMargin: ScaleMetrics.dp(4)
                spacing: ScaleMetrics.dp(4)

                // PERFORM: "PERF NAME  patch name"; both open the Librarian like in PATCH.
                Text {
                    visible: Bridge.soundMode === "PERFORM"
                    Layout.maximumWidth: ScaleMetrics.dp(150)
                    text: Bridge.perfHeader.perf
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(11)
                    color: Theme.textSecondary
                    elide: Text.ElideRight
                    MouseArea {
                        anchors.fill: parent
                        onClicked: Bridge.toggleLibrarian()
                    }
                }
                Text {
                    visible: Bridge.soundMode === "PERFORM"
                    text: "/"
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(11)
                    color: Theme.textDim
                }
                Text {
                    Layout.fillWidth: true
                    text: Bridge.soundMode === "PERFORM" ? Bridge.perfHeader.patch : Bridge.patchName
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(11)
                    color: Theme.textPrimary
                    elide: Text.ElideRight
                    MouseArea {
                        anchors.fill: parent
                        onClicked: Bridge.toggleLibrarian()
                    }
                }

                // PERFORM: part + MFX being edited; opens the picker
                Rectangle {
                    id: editTag
                    visible: Bridge.soundMode === "PERFORM"
                    implicitWidth: tagRow.implicitWidth + ScaleMetrics.dp(12)
                    implicitHeight: ScaleMetrics.dp(30)
                    radius: ScaleMetrics.dp(3)
                    color: tagMouse.pressed ? Theme.bgCardActive : Theme.bgSurface
                    border.color: tagMouse.pressed ? Theme.catPerform : Theme.borderCard
                    border.width: 1
                    Row {
                        id: tagRow
                        anchors.centerIn: parent
                        spacing: ScaleMetrics.dp(5)
                        Text {
                            text: "P" + Bridge.perfHeader.part
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(10)
                            color: Theme.catPerform
                        }
                        Text {
                            text: "MFX" + Bridge.editingPerfMfx
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: Theme.catModFx
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Icon {
                            name: "down"
                            size: 12
                            color: Theme.textDim
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                    MouseArea {
                        id: tagMouse
                        anchors.fill: parent
                        onClicked: Bridge.openEditTarget()
                    }
                }

                // Sync: reads the patch in PATCH mode, the whole performance in PERFORM
                Rectangle {
                    id: syncBtn
                    width: ScaleMetrics.dp(Bridge.syncBusy ? 54 : 46)
                    height: ScaleMetrics.dp(30)
                    radius: ScaleMetrics.dp(3)
                    color: syncArea.pressed ? Theme.bgCardActive : Theme.bgSurface
                    border.color: syncArea.pressed ? Theme.primary : Theme.borderCard
                    border.width: 1
                    enabled: !Bridge.syncBusy
                    opacity: enabled ? 1.0 : 0.35

                    RowLayout {
                        anchors.centerIn: parent
                        spacing: 2
                        Icon {
                            name: Bridge.syncBusy ? "busy" : "sync"
                            size: 14
                            color: Theme.primary
                        }
                        Text {
                            text: Bridge.syncBusy ? "SYNC..." : "SYNC"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: Theme.textSecondary
                        }
                    }

                    MouseArea {
                        id: syncArea
                        anchors.fill: parent
                        enabled: syncBtn.enabled
                        onClicked: {
                            if (Bridge.soundMode === "PERFORM")
                                Bridge.syncPerformanceFromSynth(true);
                            else
                                Bridge.syncPatchFromSynth(true);
                        }
                    }
                }

                // Init: patch template in PATCH mode, INIT PERF song in PERFORM (modal confirms)
                Rectangle {
                    id: initBtn
                    width: ScaleMetrics.dp(44)
                    height: ScaleMetrics.dp(30)
                    radius: ScaleMetrics.dp(3)
                    color: initArea.pressed ? Theme.bgCardActive : Theme.bgSurface
                    border.color: initArea.pressed ? Theme.warning : Theme.borderCard
                    border.width: 1

                    RowLayout {
                        anchors.centerIn: parent
                        spacing: 2
                        Icon {
                            name: "init"
                            size: 13
                            color: Theme.warning
                        }
                        Text {
                            text: "INIT"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: Theme.textSecondary
                        }
                    }

                    MouseArea {
                        id: initArea
                        anchors.fill: parent
                        onClicked: {
                            Bridge.openInitPatchModal();
                        }
                    }
                }

                // Save button (Pi-always + optional keyboard slot)
                Rectangle {
                    id: saveBtn
                    width: ScaleMetrics.dp(48)
                    height: ScaleMetrics.dp(30)
                    radius: ScaleMetrics.dp(3)
                    color: saveArea.pressed ? Theme.bgCardActive : Theme.bgSurface
                    border.color: saveArea.pressed ? Theme.primary : Theme.borderCard
                    border.width: 1

                    RowLayout {
                        anchors.centerIn: parent
                        spacing: 2
                        Icon {
                            name: "save"
                            size: 13
                            color: Theme.primary
                        }
                        Text {
                            text: "SAVE"
                            font.bold: true
                            font.pixelSize: ScaleMetrics.sp(8)
                            color: Theme.textSecondary
                        }
                    }

                    MouseArea {
                        id: saveArea
                        anchors.fill: parent
                        onClicked: {
                            Bridge.openSavePatchModal();
                        }
                    }
                }
            }
        }

        // BPM (the one global tempo). A change asked for while synced audio plays
        // waits for it to stop: shown as "120 → 124", tap to cancel it.
        Rectangle {
            readonly property bool pending: Bridge.pendingBpm > 0
            height: ScaleMetrics.dp(38)
            width: ScaleMetrics.dp(pending ? 104 : 70)
            Layout.preferredWidth: width
            radius: ScaleMetrics.dp(4)
            color: Theme.bgApp
            border.color: bpmArea.pressed ? Theme.catPerform : Theme.borderCard
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
                    color: Theme.catPerform
                }
                Text {
                    visible: Bridge.pendingBpm > 0
                    text: "→ " + Math.round(Bridge.pendingBpm)
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(12)
                    color: Theme.warning
                }
            }

            // Global tempo (sequencer + vector motion): drag right/up or left/down, 1 BPM per 4px
            MouseArea {
                id: bpmArea
                anchors.fill: parent
                preventStealing: true
                property real startX: 0
                property real startY: 0
                property real startBpm: 120
                property bool moved: false
                // Drags start from the held value when there is one
                readonly property real shownBpm: Bridge.pendingBpm > 0 ? Bridge.pendingBpm : Bridge.bpm
                onPressed: (mouse) => { startX = mouse.x; startY = mouse.y; startBpm = Math.round(shownBpm); moved = false; }
                onPositionChanged: (mouse) => {
                    // Right/up increases: at the top edge the horizontal axis is always free
                    const d = (mouse.x - startX) + (startY - mouse.y);
                    if (Math.abs(d) >= ScaleMetrics.dp(4)) moved = true;
                    const next = Math.max(20, Math.min(300, startBpm + Math.round(d / ScaleMetrics.dp(4))));
                    if (next !== Math.round(shownBpm)) Bridge.setBpm(next);
                }
                onReleased: if (!moved && Bridge.pendingBpm > 0) Bridge.cancelPendingBpm()
            }
        }

        // Master Transport: sequencer record arm (doubles as the REC indicator on
        // every screen, naming what it records into: note track and/or lanes)
        // and Play/Stop. Arms the active note track, or the active lane in MOTION mode.
        Rectangle {
            id: recBtn
            readonly property bool armed: Bridge.seqRecArmed
            height: ScaleMetrics.dp(38)
            width: ScaleMetrics.dp(54)
            radius: ScaleMetrics.dp(4)
            color: armed ? Theme.tint(Theme.recording, 0.25) : (recArea.pressed ? Theme.bgCardActive : Theme.bgApp)
            border.color: armed ? Theme.recording : Theme.borderCard
            border.width: 1

            ColumnLayout {
                anchors.centerIn: parent
                spacing: 0
                Row {
                    Layout.alignment: Qt.AlignHCenter
                    spacing: ScaleMetrics.dp(3)
                    Icon {
                        anchors.verticalCenter: parent.verticalCenter
                        name: "record"
                        size: 11
                        color: recBtn.armed ? Theme.recording : Theme.textDim
                    }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "REC"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(9)
                        color: recBtn.armed ? Theme.recording : Theme.textDim
                    }
                }
                Text {
                    Layout.alignment: Qt.AlignHCenter
                    visible: recBtn.armed
                    text: Bridge.seqRecText
                    font.bold: true
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: Bridge.seqLiveRecordWaiting ? Theme.warning : Theme.textPrimary
                }
            }

            MouseArea {
                id: recArea
                anchors.fill: parent
                onClicked: Bridge.seqToggleRecord()
            }
        }

        // Play/Stop. Hold = PANIC: stop everything, all notes off (flashes red)
        Rectangle {
            id: playBtn
            property bool flash: false
            height: ScaleMetrics.dp(38)
            width: ScaleMetrics.dp(46)
            radius: ScaleMetrics.dp(4)
            color: flash ? Theme.tint(Theme.recording, 0.3)
                   : Bridge.seqIsPlaying ? Theme.tint(Theme.playing, 0.25) : (playArea.pressed ? Theme.bgCardActive : Theme.bgApp)
            border.color: flash || playArea.holding ? Theme.recording
                          : Bridge.seqIsPlaying ? Theme.playing : Theme.borderCard
            border.width: 1

            Icon {
                anchors.centerIn: parent
                name: playBtn.flash ? "panic" : Bridge.seqIsPlaying ? "stop" : "play"
                size: 20
                color: playBtn.flash ? Theme.recording : Bridge.seqIsPlaying ? Theme.playing : Theme.textPrimary
            }

            // Fills while held, so the hold reads as "arming" panic
            Rectangle {
                anchors.left: parent.left
                anchors.bottom: parent.bottom
                anchors.margins: 2
                height: ScaleMetrics.dp(3)
                radius: height / 2
                color: Theme.recording
                width: playArea.holding ? parent.width - 4 : 0
                visible: playArea.pressed
                Behavior on width {
                    NumberAnimation { duration: playArea.holding ? playArea.pressAndHoldInterval - 120 : 0 }
                }
            }

            Timer {
                id: flashTimer
                interval: 700
                onTriggered: playBtn.flash = false
            }

            MouseArea {
                id: playArea
                property bool holding: false
                property bool fired: false
                anchors.fill: parent
                pressAndHoldInterval: 600
                onPressed: { fired = false; holdStart.restart(); }
                onReleased: { holdStart.stop(); holding = false; }
                onCanceled: { holdStart.stop(); holding = false; }
                onPressAndHold: {
                    fired = true;
                    holding = false;
                    Bridge.panic();
                    playBtn.flash = true;
                    flashTimer.restart();
                }
                onClicked: if (!fired) Bridge.seqTogglePlay()
                // Show the fill only once it's clearly a hold, not a tap
                Timer {
                    id: holdStart
                    interval: 120
                    onTriggered: playArea.holding = true
                }
            }
        }
    }

    // Background keyboard job (slot reads, saves, library loads): a thin
    // bar along the header's bottom edge, visible from every screen.
    Rectangle {
        visible: Bridge.jobBusy
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: ScaleMetrics.dp(3)
        color: Theme.bgRaised
        Rectangle {
            id: jobFill
            height: parent.height
            color: Theme.primary
            width: Bridge.jobProgress >= 0 ? parent.width * Bridge.jobProgress : parent.width * 0.25
            // Indeterminate: a segment sweeping back and forth
            x: 0
            SequentialAnimation on x {
                running: Bridge.jobBusy && Bridge.jobProgress < 0
                loops: Animation.Infinite
                onRunningChanged: if (!running) jobFill.x = 0
                NumberAnimation { from: 0; to: jobFill.parent.width * 0.75; duration: 900; easing.type: Easing.InOutQuad }
                NumberAnimation { from: jobFill.parent.width * 0.75; to: 0; duration: 900; easing.type: Easing.InOutQuad }
            }
        }
    }
}
