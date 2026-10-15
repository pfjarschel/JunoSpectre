pragma ValueTypeBehavior: Copy
import QtQuick
import QtQuick.Layouts
import JunoSpectre
import ".."

// ADSR switch for one envelope (next to its EnvThumb). On: the curve is a
// plain ADSR. Turning it on keeps the patch's curve; turning it off brings
// that curve back. Off with nothing kept (the patch came as ADSR): disabled.
SpButton {
    id: root
    property string env: "TVF"
    property var seg: ({ adsr: false, restorable: false })

    compact: true
    implicitHeight: ScaleMetrics.dp(22)
    fontSize: 8
    text: "ADSR"
    checked: seg.adsr
    enabled: !seg.adsr || seg.restorable
    opacity: enabled ? 1.0 : 0.45
    onClicked: Bridge.setEnvAdsr(env, !seg.adsr)

    function refresh() {
        var s = Bridge.getEnvSegments(env);
        seg = { adsr: s.adsr, restorable: s.restorable };
    }

    Connections {
        target: Bridge
        function onEnvShapeChanged(e) {
            if (e === root.env) {
                root.refresh();
            }
        }
    }

    Component.onCompleted: refresh()
    onEnvChanged: refresh()
}
