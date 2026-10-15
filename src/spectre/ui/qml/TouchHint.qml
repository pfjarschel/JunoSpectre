pragma Singleton
pragma ValueTypeBehavior: Copy
import QtQuick

// How many on-screen controls are highlighting the control under the hand
// (TouchHighlight). None: the toast shows it instead (TouchToast).
QtObject {
    property int shown: 0
}
