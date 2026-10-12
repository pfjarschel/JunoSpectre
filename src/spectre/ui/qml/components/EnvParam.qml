pragma ValueTypeBehavior: Copy
import QtQuick
import JunoSpectre
import ".."

// Envelope editor parameter (MSEG times / levels / modifiers). Kept for its
// API; the look lives in SpSlider.
SpSlider {
    id: ep
    property color labelColor: Theme.textSecondary  // unused; the shared look sets label colours
    property int val: 0
    property bool isBipolar: false
    property color barColor: Theme.pageAccent
    property string customText: ""

    implicitHeight: ScaleMetrics.dp(30)
    bipolar: isBipolar
    accent: barColor
    valueText: customText !== "" ? customText : (isBipolar && val > 0 ? "+" + val : val.toString())
}
