pragma ValueTypeBehavior: Copy
import QtQuick
import JunoSpectre
import ".."

// Engine-page parameter row (label inside the bar). Kept for its API; the
// look lives in SpSlider.
SpSlider {
    property string valText: "0"
    property real normVal: 0.5
    property bool isBipolar: false
    property color barColor: Theme.pageAccent

    valueText: valText
    norm: normVal
    bipolar: isBipolar
    accent: barColor
}
