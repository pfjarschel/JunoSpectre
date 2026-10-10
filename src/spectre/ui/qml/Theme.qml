pragma ValueTypeBehavior: Copy
import QtQuick

pragma Singleton

QtObject {
    // Backgrounds
    readonly property color bgApp: "#0a0c10"
    readonly property color bgCard: "#13161c"
    readonly property color bgCardActive: "#1a1e26"
    readonly property color bgSurface: "#181b22"
    readonly property color borderCard: "#222733"
    readonly property color borderActive: "#3a4454"

    // Roland 4-Tone Neon Accents
    readonly property color tone1: "#00e5ff"  // Cyan (NW)
    readonly property color tone2: "#ff007f"  // Magenta (NE)
    readonly property color tone3: "#ffb300"  // Amber (SW)
    readonly property color tone4: "#00e676"  // Lime (SE)

    // Sequencer tracks T1..T8. T8 (the default drum track) is burnt orange:
    // clear of tone3 amber and of the amber "queued" marker. No violets, which
    // would vanish on the mixer's editingFill.
    readonly property var trackColors: [tone1, tone2, tone3, tone4, "#60a5fa", "#fb7185", "#bef264", "#c2410c"]
    // Mixer part being edited (badge fill; dark so track-colored labels read on it)
    readonly property color editingFill: "#4c1d95"
    // Edited part outline / EDIT button lines
    readonly property color editingAccent: "#8b5cf6"

    // Interactive & Status Colors
    readonly property color primary: "#3d7eff"
    readonly property color primaryGlow: "#1e40af"
    readonly property color recording: "#ef4444"
    readonly property color playing: "#10b981"
    readonly property color warning: "#f59e0b"

    // Typography Colors
    readonly property color textPrimary: "#f8fafc"
    readonly property color textSecondary: "#94a3b8"
    readonly property color textMuted: "#64748b"
    readonly property color textDim: "#475569"

    // Fonts
    readonly property string fontMono: "monospace"
    readonly property string fontSans: "sans-serif"
}
