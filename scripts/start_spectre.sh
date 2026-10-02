#!/usr/bin/env bash
# Juno Spectre Appliance Auto-Launcher for Raspberry Pi
# Launches hardware-accelerated Qt Quick touch UI via KMS/DRM (eglfs) directly to the screen

# Change to project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.." || exit 1

export QT_QPA_PLATFORM=eglfs
export QT_QPA_EGLFS_KMS_CONFIG="$SCRIPT_DIR/eglfs.json"
export QT_QPA_EGLFS_ALWAYS_SET_MODE=1
export QT_QPA_EGLFS_HIDECURSOR=1
export QT_LOGGING_RULES="qt.qpa.*=false"

echo "Starting Juno Spectre Touch Workstation..."
exec python3 scripts/spectre_vector.py --fullscreen "$@"
