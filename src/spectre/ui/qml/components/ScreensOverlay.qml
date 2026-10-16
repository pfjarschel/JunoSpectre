pragma ValueTypeBehavior: Copy
import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

Rectangle {
    id: root
    anchors.fill: parent
    visible: false
    z: 999
    color: Theme.scrim // Deep translucent backdrop

    function open() {
        visible = true;
    }

    function close() {
        visible = false;
    }

    MouseArea {
        anchors.fill: parent
        // Block clicks through to underlying view
        onClicked: root.close()
    }

    // Modal Card Container
    Rectangle {
        id: card
        width: Math.min(parent.width - ScaleMetrics.dp(32), ScaleMetrics.dp(960))
        height: Math.min(parent.height - ScaleMetrics.dp(32), ScaleMetrics.dp(550))
        anchors.centerIn: parent
        radius: ScaleMetrics.dp(10)
        color: Theme.bgCard
        border.color: Theme.borderActive
        border.width: 1

        MouseArea {
            anchors.fill: parent
            // Prevent close on card background click
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(14)
            spacing: ScaleMetrics.dp(8)

            // Header Bar
            RowLayout {
                Layout.fillWidth: true
                spacing: ScaleMetrics.dp(8)

                Rectangle {
                    width: ScaleMetrics.dp(24)
                    height: ScaleMetrics.dp(24)
                    radius: ScaleMetrics.dp(4)
                    color: Theme.bgCardActive
                    Icon {
                        anchors.centerIn: parent
                        name: "screens"
                        size: 18
                        color: Theme.primary
                    }
                }

                ColumnLayout {
                    spacing: 1
                    Text {
                        text: "WORKSTATION SCREENS & APPS"
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(13)
                        font.letterSpacing: 1.2
                        color: Theme.textPrimary
                    }
                    Text {
                        text: "SELECT AN ENGINE, MODULATOR, MIXER OR SYSTEM UTILITY"
                        font.pixelSize: ScaleMetrics.sp(9)
                        color: Theme.textDim
                    }
                }

                Item { Layout.fillWidth: true }

                // Close Button
                SpButton {
                    implicitWidth: ScaleMetrics.dp(36)
                    implicitHeight: ScaleMetrics.dp(32)
                    icon: "close"
                    fontSize: 14
                    onClicked: root.close()
                }
            }

            // Scrollable App Grid Container
            Flickable {
                Layout.fillWidth: true
                Layout.fillHeight: true
                contentWidth: width
                contentHeight: contentCol.implicitHeight + ScaleMetrics.dp(16)
                boundsBehavior: Flickable.StopAtBounds
                clip: true

                ColumnLayout {
                    id: contentCol
                    width: parent.width
                    spacing: ScaleMetrics.dp(10)

                    // =========================================================
                    // 1. SYNTH ENGINES
                    // =========================================================
                    CategoryDivider {
                        title: "SYNTH ENGINES"
                        accent: Theme.catSynth
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: ScaleMetrics.dp(8)

                        AppTile {
                            Layout.fillWidth: true
                            viewKey: "JUNO PCM"
                            title: "JUNO PCM"
                            subtitle: "Standard 4-Tone Roland sound designer"
                            accentColor: Theme.catSynth
                        }

                        AppTile {
                            Layout.fillWidth: true
                            viewKey: "VECTOR"
                            title: "2D VECTOR"
                            subtitle: "4-Tone Cartesian morph pad & orbit"
                            accentColor: Theme.catSynth
                        }

                        AppTile {
                            Layout.fillWidth: true
                            viewKey: "WAVETABLE"
                            title: "1D WAVETABLE"
                            subtitle: "Linear crossfade, scope & 3D waterfall"
                            accentColor: Theme.catSynth
                        }

                        AppTile {
                            Layout.fillWidth: true
                            viewKey: "VA"
                            title: "4-OSC VA"
                            subtitle: "Classic virtual analog console & detuning"
                            accentColor: Theme.catSynth
                        }
                    }

                    // =========================================================
                    // 2. MODULATION & FX
                    // =========================================================
                    CategoryDivider {
                        title: "MODULATION & FX"
                        accent: Theme.catModFx
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: ScaleMetrics.dp(8)

                        AppTile {
                            Layout.fillWidth: true
                            viewKey: "MOD MATRIX"
                            title: "MOD MATRIX"
                            subtitle: "4 Matrix controllers & destinations"
                            accentColor: Theme.catModFx
                        }

                        AppTile {
                            Layout.fillWidth: true
                            viewKey: "STEP LFO"
                            title: "STEP LFO"
                            subtitle: "16-step touch pattern modulator & glide"
                            accentColor: Theme.catModFx
                        }

                        AppTile {
                            Layout.fillWidth: true
                            viewKey: "MSEG ENVELOPES"
                            title: "MSEG ENVELOPES"
                            subtitle: "TVF / TVA / Pitch multi-segment editors"
                            accentColor: Theme.catModFx
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: ScaleMetrics.dp(8)

                        AppTile {
                            Layout.fillWidth: true
                            viewKey: "ROUTING"
                            title: "ROUTING"
                            subtitle: "Signal flow presets & bus matrix"
                            accentColor: Theme.catModFx
                        }

                        AppTile {
                            Layout.fillWidth: true
                            viewKey: "MFX"
                            title: "MFX STUDIO"
                            subtitle: "80 multi-effects processors & params"
                            accentColor: Theme.catModFx
                        }

                        AppTile {
                            Layout.fillWidth: true
                            viewKey: "MASTER FX"
                            title: "MASTER FX"
                            subtitle: "Chorus & Hall/Room Reverb"
                            accentColor: Theme.catModFx
                        }
                    }

                    // =========================================================
                    // 3. PERFORMANCE & PLAY
                    // =========================================================
                    CategoryDivider {
                        title: "PERFORMANCE & PLAY"
                        accent: Theme.catPerform
                    }

                    // Top: shaping the sound while playing; bottom: the song workflow
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: ScaleMetrics.dp(8)

                        AppTile {
                            Layout.fillWidth: true
                            viewKey: "MACROS"
                            title: "MACRO DECK"
                            subtitle: "8 large touch dials assigned to knobs"
                            accentColor: Theme.catPerform
                        }

                        AppTile {
                            Layout.fillWidth: true
                            viewKey: "ARPEGGIO"
                            title: "ARPEGGIATOR"
                            subtitle: "Juno arp styles, motifs & MIDI clock"
                            accentColor: Theme.catPerform
                        }

                        AppTile {
                            Layout.fillWidth: true
                            viewKey: "PERFORMANCE"
                            title: "PERFORMANCE"
                            subtitle: "16-part multi-timbral mixer & key zones"
                            accentColor: Theme.catPerform
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: ScaleMetrics.dp(8)

                        AppTile {
                            Layout.fillWidth: true
                            viewKey: "SEQUENCER"
                            title: "SEQUENCER"
                            subtitle: "Polymetric step sequencer & motion"
                            accentColor: Theme.catPerform
                        }

                        AppTile {
                            Layout.fillWidth: true
                            viewKey: "LIVE"
                            title: "LIVE MODE"
                            subtitle: "16-track clip & scene launcher, motion lanes"
                            accentColor: Theme.catPerform
                        }

                        AppTile {
                            Layout.fillWidth: true
                            viewKey: "SETLIST"
                            title: "SETLIST"
                            subtitle: "Repertoire manager & seamless transitions"
                            accentColor: Theme.catPerform
                        }
                    }

                    // =========================================================
                    // 4. SYSTEM & UTILITIES
                    // =========================================================
                    CategoryDivider {
                        title: "SYSTEM & UTILITIES"
                        accent: Theme.catSystem
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: ScaleMetrics.dp(8)

                        AppTile {
                            Layout.fillWidth: true
                            viewKey: "LIBRARIAN"
                            title: "LIBRARIAN"
                            subtitle: ".spectre & .syx disk preset storage"
                            accentColor: Theme.catSystem
                        }

                        AppTile {
                            Layout.fillWidth: true
                            viewKey: "MIDI LEARN"
                            title: "MIDI LEARN"
                            subtitle: "Hardware controller surface mapping"
                            accentColor: Theme.catSystem
                        }

                        AppTile {
                            Layout.fillWidth: true
                            viewKey: "HARDWARE"
                            title: "HARDWARE"
                            subtitle: "Juno-DS / XPS-30 synth device config"
                            accentColor: Theme.catSystem
                        }

                        AppTile {
                            Layout.fillWidth: true
                            viewKey: "SYSTEM"
                            title: "SYSTEM"
                            subtitle: "Reboot, brightness, Pi stats & apt updater"
                            accentColor: Theme.catSystem
                        }
                    }
                }
            }
        }
    }

    // Horizontal Category Divider with Centered Title
    component CategoryDivider: RowLayout {
        id: divRoot
        property string title: "CATEGORY"
        property color accent: Theme.primary
        Layout.fillWidth: true
        spacing: ScaleMetrics.dp(8)

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Theme.borderCard
        }

        Text {
            text: divRoot.title
            font.bold: true
            font.pixelSize: ScaleMetrics.sp(10)
            font.letterSpacing: 1.5
            color: divRoot.accent
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Theme.borderCard
        }
    }

    // Touch App Tile Component
    component AppTile: Rectangle {
        id: tile
        property string viewKey: "JUNO PCM"
        property string title: "APP"
        property string subtitle: "Description"
        property color accentColor: Theme.primary
        property bool isActive: Bridge.activeView === viewKey

        height: ScaleMetrics.dp(56)
        radius: ScaleMetrics.dp(6)
        color: tileArea.pressed ? Theme.bgCardActive : (isActive ? Theme.tint(accentColor) : Theme.bgApp)
        border.color: isActive ? accentColor : (tileArea.pressed ? Theme.borderActive : Theme.borderCard)
        border.width: isActive ? 2 : 1

        RowLayout {
            anchors.fill: parent
            anchors.margins: ScaleMetrics.dp(6)
            spacing: ScaleMetrics.dp(8)

            // Glyph Icon Box
            Rectangle {
                width: ScaleMetrics.dp(36)
                height: ScaleMetrics.dp(36)
                radius: ScaleMetrics.dp(6)
                color: tile.isActive ? tile.accentColor : Theme.bgSurface
                border.width: 0

                Icon {
                    anchors.centerIn: parent
                    name: Icons.forView(tile.viewKey)
                    size: 20
                    color: tile.isActive ? Theme.textOnFill : tile.accentColor
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 1

                RowLayout {
                    spacing: ScaleMetrics.dp(4)
                    Text {
                        text: tile.title
                        font.bold: true
                        font.pixelSize: ScaleMetrics.sp(11)
                        color: tile.isActive ? Theme.textPrimary : Theme.textSecondary
                    }
                    Rectangle {
                        visible: tile.isActive
                        width: ScaleMetrics.dp(6)
                        height: ScaleMetrics.dp(6)
                        radius: 3
                        color: tile.accentColor
                    }
                }

                Text {
                    Layout.fillWidth: true
                    text: tile.subtitle
                    font.pixelSize: ScaleMetrics.sp(8)
                    color: Theme.textDim
                    elide: Text.ElideRight
                }
            }
        }

        MouseArea {
            id: tileArea
            anchors.fill: parent
            onClicked: {
                Bridge.setActiveView(tile.viewKey);
                root.close();
            }
        }
    }
}
