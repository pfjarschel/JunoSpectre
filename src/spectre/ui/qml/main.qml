pragma ValueTypeBehavior: Copy
import QtQuick
import QtQuick.Window
import JunoSpectre

Window {
    id: window
    visible: true
    width: 1024
    height: 600
    minimumWidth: 800
    minimumHeight: 480
    title: "Juno Spectre - Touch Workstation"
    color: Theme.bgApp

    // Startup splash (set by app.py on launch, off in tests): the first frame
    // is the splash picture and the UI is built after it (that takes seconds
    // on the Pi). splashShown is set by app.py once that frame is on screen;
    // the fallback timer covers a missed frame signal. The splash stays up at
    // least splashMinMs, so a fast PC still shows it.
    property bool splashStartup: false
    property bool splashShown: false
    property bool splashHeld: true
    readonly property int splashMinMs: 3000

    // Bind dynamic dimensions to ScaleMetrics singleton
    Component.onCompleted: {
        ScaleMetrics.rootWidth = width
        ScaleMetrics.rootHeight = height
    }
    onWidthChanged: ScaleMetrics.rootWidth = width
    onHeightChanged: ScaleMetrics.rootHeight = height

    Loader {
        id: content
        anchors.fill: parent
        focus: true
        active: !window.splashStartup || window.splashShown
        source: "AppContent.qml"
    }

    Image {
        id: splash
        // Sized from the window: the content item can still be 0x0 when the
        // first frame is drawn, and that frame must be the picture
        width: window.width
        height: window.height
        visible: window.splashStartup && opacity > 0
        source: visible ? "../../assets/splash_1024x600.jpg" : ""
        fillMode: Image.PreserveAspectCrop
        // Fade into the UI once it is built
        opacity: content.status === Loader.Ready && !window.splashHeld ? 0 : 1
        Behavior on opacity { NumberAnimation { duration: 400; easing.type: Easing.InOutQuad } }

        // Swallow touches while the UI is still being built
        MouseArea { anchors.fill: parent }
    }

    Timer {
        interval: 2000
        running: window.splashStartup && !window.splashShown
        onTriggered: window.splashShown = true
    }

    // Minimum splash time, counted from the first frame (on the Pi the UI
    // build alone takes longer, so this adds nothing there)
    Timer {
        interval: window.splashMinMs
        running: window.splashStartup && window.splashShown && window.splashHeld
        onTriggered: window.splashHeld = false
    }
}
