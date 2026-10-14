pragma ValueTypeBehavior: Copy
import QtQuick

pragma Singleton

// Icon names -> Phosphor (regular) glyphs. Views use the semantic names
// below through Icon { name: "save" } or SpButton { icon: "save" };
// to restyle an icon, change it here. Phosphor names: phosphoricons.com
QtObject {
    readonly property var glyphs: ({
        // Screens
        "screen.pcm": "\ue9c8",  // piano-keys
        "screen.vector": "\uea5e",  // joystick
        "screen.wavetable": "\ue802",  // waveform
        "screen.va": "\uea9c",  // wave-sawtooth
        "screen.modmatrix": "\uec8c",  // grid-nine
        "screen.steplfo": "\ue150",  // chart-bar
        "screen.mseg": "\ue6d4",  // line-segments
        "screen.routing": "\ue6ec",  // flow-arrow
        "screen.mfx": "\ue6a2",  // sparkle
        "screen.masterfx": "\uebbc",  // equalizer
        "screen.macros": "\ue628",  // gauge
        "screen.arp": "\ue340",  // music-notes
        "screen.perf": "\ue228",  // faders
        "screen.seq": "\ue1fc",  // dots-nine
        "screen.live": "\ue296",  // grid-four
        "screen.setlist": "\ue6aa",  // playlist
        "screen.librarian": "\ue758",  // books
        "screen.midilearn": "\ueb5a",  // plugs-connected
        "screen.hardware": "\ue610",  // cpu
        "screen.system": "\ue272",  // gear-six
        // Header & transport
        "screens": "\ue464",  // squares-four
        "sync": "\ue094",  // arrows-clockwise
        "init": "\ue236",  // file-plus
        "save": "\ue248",  // floppy-disk
        "play": "\ue3d0",  // play
        "pause": "\ue39e",  // pause
        "stop": "\ue46c",  // stop
        "record": "\ue3ee",  // record
        "panic": "\ue4e4",  // warning-octagon
        "tempo": "\uec8e",  // metronome
        // Editing
        "edit": "\ue3b4",  // pencil-simple
        "add": "\ue3d4",  // plus
        "remove": "\ue32a",  // minus
        "copy": "\ue1ca",  // copy
        "close": "\ue4f6",  // x
        "check": "\ue182",  // check
        "back": "\ue058",  // arrow-left
        "search": "\ue30c",  // magnifying-glass
        "keyboard": "\ue2d8",  // keyboard
        "backspace": "\ue0ae",  // backspace
        "shift": "\ue52e",  // arrow-fat-up
        "drag": "\ueae2",  // dots-six-vertical
        "expand": "\ue0a6",  // arrows-out-simple
        "favorite": "\ue46a",  // star
        "lock": "\ue308",  // lock-simple
        "layer": "\ue466",  // stack
        "dice": "\ue1ee",  // dice-five
        "eraser": "\ue21e",  // eraser
        "link": "\ue2e2",  // link
        // Status & system
        "info": "\ue2ce",  // info
        "warning": "\ue4e0",  // warning
        "busy": "\ue2b2",  // hourglass
        "power": "\ue3da",  // power
        "restart": "\ue036",  // arrow-clockwise
        "reboot": "\ue2de",  // lightning
        "load": "\ue2de",  // lightning
        "wifi": "\ue4ea",  // wifi-high
        "dot": "\ue18a",  // circle
        "dotFilled": "\ue18a",  // circle (filled)
        // Navigation
        "left": "\ue138",  // caret-left
        "right": "\ue13a",  // caret-right
        "up": "\ue13c",  // caret-up
        "down": "\ue136",  // caret-down
        "forward": "\ue06c",  // arrow-right
        // Waves
        "track.notes": "\ue340",  // music-notes (NOTES track)
        "track.audio": "\ue802",  // waveform (AUDIO track / audio file)
        "wave.sine": "\uea9a",  // wave-sine
        "wave.saw": "\uea9c",  // wave-sawtooth
        "wave.square": "\uea9e",  // wave-square
        "wave.triangle": "\ueaa0",  // wave-triangle
    })

    // Drawn with the Phosphor Fill weight by default (transport + dots)
    readonly property var filledByDefault: ({ "play": true, "pause": true, "stop": true, "record": true, "dotFilled": true })

    function isFilled(name) {
        return filledByDefault[name] === true;
    }

    // Icon name of each app page (Bridge.activeView keys)
    readonly property var viewIcons: ({
        "JUNO PCM": "screen.pcm", "VECTOR": "screen.vector", "WAVETABLE": "screen.wavetable", "VA": "screen.va",
        "MOD MATRIX": "screen.modmatrix", "STEP LFO": "screen.steplfo", "MSEG ENVELOPES": "screen.mseg",
        "ROUTING": "screen.routing", "MFX": "screen.mfx", "MASTER FX": "screen.masterfx",
        "MACROS": "screen.macros", "ARPEGGIO": "screen.arp", "PERFORMANCE": "screen.perf",
        "SEQUENCER": "screen.seq", "LIVE": "screen.live", "SETLIST": "screen.setlist",
        "LIBRARIAN": "screen.librarian", "MIDI LEARN": "screen.midilearn", "HARDWARE": "screen.hardware",
        "SYSTEM": "screen.system"
    })

    function forView(view) {
        return viewIcons[view] || "screens";
    }

    function glyph(name) {
        const g = glyphs[name];
        if (g === undefined) {
            console.warn("Icons: unknown icon '" + name + "'");
            return "";
        }
        return g;
    }
}
