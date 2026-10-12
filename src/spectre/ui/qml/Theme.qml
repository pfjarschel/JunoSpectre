pragma ValueTypeBehavior: Copy
import QtQuick
import JunoSpectre

pragma Singleton

// Colour roles. Every colour has exactly one job:
//   identity - tones, tracks, macros: "this belongs to T2 / track 5 / M3"
//   status   - record/destructive, playing/ok, warning/edited
//   accent   - the page's category colour, for its own (non-identity) controls
//   neutral  - backgrounds, borders, text
// Never use an identity or status colour as page decoration, and never use a
// raw hex literal in a view: add a role here instead.
QtObject {
    // ---- Neutrals: backgrounds, darkest to lightest ----
    readonly property color bgTrack: "#080b11"       // slider troughs, scopes, wells
    readonly property color bgApp: "#0a0c10"
    readonly property color bgControl: "#10141d"     // idle buttons, chips, sliders
    readonly property color bgCard: "#13161c"
    readonly property color bgSurface: "#181b22"
    readonly property color bgCardActive: "#1a1e26"  // pressed / hovered
    readonly property color bgRaised: "#1e293b"      // inactive toggles inside cards
    readonly property color scrim: "#e60a0c10"       // behind modals
    readonly property color gridLine: "#172033"      // grids inside pads, scopes, graphs
    readonly property color keyWhite: "#e8edf3"      // on-screen piano keys
    readonly property color keyBlack: "#11151d"
    readonly property color borderCard: "#222733"
    readonly property color borderActive: "#3a4454"

    // ---- Neutrals: text ----
    readonly property color textPrimary: "#f8fafc"
    readonly property color textSecondary: "#94a3b8"
    readonly property color textMuted: "#64748b"
    readonly property color textDim: "#475569"
    readonly property color textOnFill: "#0a0c10"    // text on a solid accent/identity fill

    // ---- Identity: tones T1..T4 ----
    readonly property color tone1: "#00e5ff"  // Cyan
    readonly property color tone2: "#ff007f"  // Magenta
    readonly property color tone3: "#ffb300"  // Amber
    readonly property color tone4: "#00e676"  // Lime
    readonly property var toneColors: [tone1, tone2, tone3, tone4]

    // Sequencer tracks T1..T8. T8 (the default drum track) is burnt orange:
    // clear of tone3 amber and of the amber "queued" marker. No violets, which
    // would vanish on the mixer's editingFill.
    readonly property var trackColors: [tone1, tone2, tone3, tone4, "#60a5fa", "#fb7185", "#bef264", "#c2410c"]
    // 16 performance parts (zone map)
    readonly property var partColors: ["#f87171", "#fb923c", "#fbbf24", "#a3e635", "#34d399", "#2dd4bf",
        "#38bdf8", "#818cf8", "#a78bfa", "#e879f9", "#f472b6", "#fb7185",
        "#facc15", "#4ade80", "#22d3ee", "#c084fc"]
    // Mixer part being edited (badge fill; dark so track-colored labels read on it)
    readonly property color editingFill: "#4c1d95"
    // Edited part outline / EDIT button lines
    readonly property color editingAccent: "#8b5cf6"

    // ---- Status ----
    readonly property color recording: "#ef4444"  // record, panic, delete, clear, errors
    readonly property color playing: "#10b981"    // playing, connected, ok
    readonly property color warning: "#f59e0b"    // warning, out of sync, queued
    readonly property color modified: "#60a5fa"   // edited since loaded/saved (part badge, pencil marks)
    readonly property color favorite: "#fbbf24"   // favourite stars

    // ---- Accents: one per launcher category ----
    readonly property color catSynth: "#38bdf8"    // sky
    readonly property color catModFx: "#818cf8"    // indigo
    readonly property color catPerform: "#d08cfb"  // orchid
    readonly property color catSystem: "#e2e8f0"   // silver
    // App-wide default accent (header bar)
    readonly property color primary: catSynth

    // ---- Identity: signal stages (Routing diagram, MFX chain, FX rail, header P/MFX tag) ----
    readonly property color stageTones: tone1
    readonly property color stagePart: catPerform
    readonly property color stageMfx: catModFx
    readonly property color stageChorus: catSynth
    readonly property color stageReverb: catSystem
    readonly property color stageOutput: playing

    function viewCategory(view) {
        switch (view) {
        case "JUNO PCM": case "VECTOR": case "WAVETABLE": case "VA":
            return "synth";
        case "MOD MATRIX": case "STEP LFO": case "MSEG ENVELOPES":
        case "ROUTING": case "MFX": case "MASTER FX":
            return "modfx";
        case "MACROS": case "ARPEGGIO": case "PERFORMANCE":
        case "SEQUENCER": case "LIVE": case "SETLIST":
            return "perform";
        case "LIBRARIAN": case "MIDI LEARN": case "HARDWARE": case "SYSTEM":
            return "system";
        }
        return "synth";
    }

    function viewAccent(view) {
        switch (viewCategory(view)) {
        case "modfx": return catModFx;
        case "perform": return catPerform;
        case "system": return catSystem;
        }
        return catSynth;
    }

    // Accent of the page on screen; shared controls default to it.
    readonly property color pageAccent: viewAccent(Bridge.activeView)

    // Selected state = tinted fill + outline in the same colour.
    readonly property real tintAlpha: 0.16
    // Value fill inside sliders / bars.
    readonly property real fillAlpha: 0.32
    // Disabled controls, everywhere.
    readonly property real disabledOpacity: 0.4

    function tint(c, a) {
        return Qt.rgba(c.r, c.g, c.b, a === undefined ? tintAlpha : a);
    }

    // Corner radii (dp): chips/bars, buttons, cards, panels
    readonly property int radiusSmall: 3
    readonly property int radius: 4
    readonly property int radiusCard: 6
    readonly property int radiusPanel: 8

    // Type scale (sp). ScaleMetrics.sp() never goes below 8, so 8 is the floor.
    readonly property real fontXs: 8     // labels, chips, captions
    readonly property real fontSm: 9     // values, buttons
    readonly property real fontMd: 10    // section titles, big buttons
    readonly property real fontLg: 12    // card titles
    readonly property real fontXl: 14    // page titles, big readouts

    // Fonts
    // Bundled in ui/fonts and registered at startup (app.py)
    readonly property string fontMono: "Noto Sans Mono"
    readonly property string fontSans: "Noto Sans"
    readonly property string fontIcons: "Phosphor"
    readonly property string fontIconsFill: "Phosphor-Fill"
}
