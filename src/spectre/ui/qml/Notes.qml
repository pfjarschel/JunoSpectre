pragma ValueTypeBehavior: Copy
import QtQuick

pragma Singleton

// MIDI note names, C4 = 60 (Roland numbering).
QtObject {
    readonly property var names: ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

    function name(n) {
        return names[n % 12] + (Math.floor(n / 12) - 1)
    }
}
