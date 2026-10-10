pragma ValueTypeBehavior: Copy
import QtQuick

pragma Singleton

QtObject {
    // Reference baseline resolution (Juno Spectre 7" Touchscreen Standard)
    readonly property real baseWidth: 1024.0
    readonly property real baseHeight: 600.0

    // Dynamic root dimensions updated by main window
    property real rootWidth: 1024.0
    property real rootHeight: 600.0

    // Uniform scale factor: 1.0 for 1024x600 native display
    readonly property real scale: 1.0

    // Helper functions for resolution-independent dimensions
    function dp(value) {
        return Math.max(1, Math.round(value * scale))
    }

    function sp(fontSize) {
        return Math.max(8, Math.round(fontSize * scale))
    }

    function touchSize(value) {
        return Math.max(36, Math.round(value * scale))
    }
}
