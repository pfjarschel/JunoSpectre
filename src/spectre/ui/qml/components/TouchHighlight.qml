pragma ValueTypeBehavior: Copy
import QtQuick
import JunoSpectre
import ".."

// Outline on a touchscreen control while the same parameter is under the
// hand on a hardware controller (Bridge.touchedKey). Fill the control with it
// and set ctlKey to the parameter it edits.
Rectangle {
    id: hl
    property string ctlKey: ""
    // "tone.2.pitch_fine" (one tone) and "tone.pitch_fine" (all tones) match
    // each other; two different tones don't
    readonly property bool hit: {
        const k = Bridge.touchedKey;
        if (ctlKey === "" || k === "")
            return false;
        const oneTone = /^tone\.[1-4]\./;
        return k === ctlKey || k.replace(oneTone, "tone.") === ctlKey || ctlKey.replace(oneTone, "tone.") === k;
    }
    // Effective visibility: false while the page or a parent is hidden
    readonly property bool counted: visible

    visible: hit
    z: 10
    color: Theme.tint(Theme.textPrimary, 0.08)
    border.width: ScaleMetrics.dp(2)
    border.color: Theme.textPrimary

    onCountedChanged: TouchHint.shown += counted ? 1 : -1
    Component.onDestruction: if (counted) TouchHint.shown -= 1
}
