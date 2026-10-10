pragma ValueTypeBehavior: Copy
import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

Rectangle {
    id: tf
    property string label: "PARAM"
    property string valText: "0"
    property real normVal: 0.5
    property bool isBipolar: false
    property color barColor: "#38bdf8"
    signal moved(real norm)

    height: ScaleMetrics.dp(28)
    radius: ScaleMetrics.dp(3)
    color: "#10141d"
    border.color: (!tf.enabled) ? Theme.borderCard : (tfMouse.pressed ? tf.barColor : Theme.borderCard)
    border.width: 1

    // Track fill
    Rectangle {
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        x: tf.isBipolar ? (tf.normVal >= 0.5 ? parent.width * 0.5 : parent.width * Math.max(0.0, Math.min(1.0, tf.normVal))) : 0
        width: tf.isBipolar ? Math.abs(parent.width * (Math.max(0.0, Math.min(1.0, tf.normVal)) - 0.5)) : parent.width * Math.max(0.0, Math.min(1.0, tf.normVal))
        radius: ScaleMetrics.dp(2)
        color: tfMouse.pressed ? Qt.rgba(tf.barColor.r, tf.barColor.g, tf.barColor.b, 0.5) : Qt.rgba(tf.barColor.r, tf.barColor.g, tf.barColor.b, 0.3)
    }

    // Center tick for bipolar
    Rectangle {
        visible: tf.isBipolar
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 1
        color: Theme.borderCard
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: ScaleMetrics.dp(6)
        anchors.rightMargin: ScaleMetrics.dp(6)

        Text {
            text: tf.label
            font.bold: true
            font.pixelSize: ScaleMetrics.sp(8)
            color: tfMouse.pressed ? Theme.textPrimary : Theme.textSecondary
        }

        Item { Layout.fillWidth: true }

        Text {
            text: tf.valText
            font.bold: true
            font.pixelSize: ScaleMetrics.sp(9)
            font.family: Theme.fontMono
            color: Theme.textPrimary
        }
    }

    MouseArea {
        id: tfMouse
        anchors.fill: parent
        enabled: tf.enabled
        onPressed: (mouse) => {
            const norm = Math.max(0.0, Math.min(1.0, mouse.x / width));
            tf.moved(norm);
        }
        onPositionChanged: (mouse) => {
            if (pressed) {
                const norm = Math.max(0.0, Math.min(1.0, mouse.x / width));
                tf.moved(norm);
            }
        }
    }
}
