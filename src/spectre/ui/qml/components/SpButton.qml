pragma ValueTypeBehavior: Copy
import QtQuick
import JunoSpectre
import ".."

// The one button: actions, chips, tabs and toggles. It sets the style only;
// the screen sets the size (implicit size fits the label).
//   variant "neutral"  grey outline, grey text (default)
//           "outline"  accent outline + accent text
//           "primary"  solid accent, dark text (one main action per area)
//           "danger"   red outline (delete, clear, panic)
//           "warning"  amber outline (overwrites: init, save to keyboard)
//   checked            selected chip / tab / toggle: tinted fill + outline
//   icon               Icons.qml name, drawn before the text (or alone);
//                      iconAfter puts it after (next arrows, dropdowns)
Rectangle {
    id: btn

    property string text: ""
    property string icon: ""
    property real iconSize: compact ? 12 : 14
    property bool iconFilled: Icons.isFilled(icon)
    property bool iconAfter: false
    property string variant: "neutral"
    property color accent: Theme.pageAccent
    property bool checked: false
    property bool compact: false
    property real fontSize: compact ? Theme.fontXs : Theme.fontSm
    property bool mono: false
    property int horizontalPadding: ScaleMetrics.dp(compact ? 8 : 12)
    readonly property alias pressed: area.pressed
    readonly property alias label: label

    signal clicked()
    signal pressAndHold()

    readonly property color tone: variant === "danger" ? Theme.recording
                                  : variant === "warning" ? Theme.warning : accent
    readonly property bool _lit: checked || (variant !== "neutral" && variant !== "primary")

    readonly property real _gap: (icon !== "" && text !== "") ? ScaleMetrics.dp(5) : 0
    readonly property real _iconW: icon !== "" ? glyph.implicitWidth : 0

    implicitWidth: _iconW + _gap + (text !== "" ? label.implicitWidth : 0) + 2 * horizontalPadding
    implicitHeight: ScaleMetrics.dp(compact ? 22 : 30)
    radius: ScaleMetrics.dp(Theme.radius)
    opacity: enabled ? 1.0 : Theme.disabledOpacity

    color: variant === "primary" ? (area.pressed ? Qt.darker(tone, 1.3) : tone)
           : checked ? Theme.tint(tone, area.pressed ? 0.3 : Theme.tintAlpha)
           : area.pressed ? Theme.bgCardActive : Theme.bgControl
    border.width: 1
    border.color: variant === "primary" || _lit ? tone
                  : area.pressed ? Theme.borderActive : Theme.borderCard

    Row {
        anchors.centerIn: parent
        spacing: btn._gap
        layoutDirection: btn.iconAfter ? Qt.RightToLeft : Qt.LeftToRight

        Icon {
            id: glyph
            anchors.verticalCenter: parent.verticalCenter
            visible: btn.icon !== ""
            name: btn.icon
            size: btn.iconSize
        filled: btn.iconFilled
            color: label.color
        }

        Text {
            id: label
            anchors.verticalCenter: parent.verticalCenter
            visible: btn.text !== ""
            // Tight layouts: shrink the label to fit before eliding it
            width: Math.max(0, Math.min(implicitWidth, btn.width - 2 * ScaleMetrics.dp(2) - btn._iconW - btn._gap))
            horizontalAlignment: Text.AlignHCenter
            fontSizeMode: Text.HorizontalFit
            minimumPixelSize: 6
            elide: Text.ElideRight
            text: btn.text
            font.bold: true
            font.family: btn.mono ? Theme.fontMono : Theme.fontSans
            font.pixelSize: ScaleMetrics.sp(btn.fontSize)
            font.letterSpacing: 0.4
            color: btn.variant === "primary" ? Theme.textOnFill
                   : btn._lit ? btn.tone
                   : btn.pressed ? Theme.textPrimary : Theme.textSecondary
        }
    }

    MouseArea {
        id: area
        anchors.fill: parent
        enabled: btn.enabled
        onClicked: btn.clicked()
        onPressAndHold: btn.pressAndHold()
    }
}
