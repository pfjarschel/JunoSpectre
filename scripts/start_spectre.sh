#!/usr/bin/env bash
# Juno Spectre unified launcher (Raspberry Pi appliance + desktop PC)
#
# Usage: ./scripts/start_spectre.sh [--fullscreen] [--windowed] [--platform NAME] [...]
#   All extra args are passed through to scripts/spectre_vector.py
#   (--juno-port, --controller-port, --profile, --list-ports, --exit-after, ...).
#
# Behaviour:
#   - Desktop (DISPLAY / WAYLAND_DISPLAY / XDG_SESSION_TYPE=x11|wayland present):
#     windowed, Qt picks its own platform (xcb/wayland). Pass --fullscreen for fullscreen.
#   - Appliance (no display server, DRM /dev/dri/card* present, e.g. Pi KMS console):
#     eglfs + KMS config, fullscreen unless --windowed is given.
#   - Headless/SSH (neither display nor DRM): no QT_QPA_PLATFORM override.
#   - Explicit QT_QPA_PLATFORM env or --platform arg always wins.
#   - Hardware (Juno synth + MIDI controller) is always probed; when absent the UI
#     stays fully usable offline (editing/saving/librarian work, no MIDI I/O).
set -euo pipefail

# Change to project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.." || exit 1

# --- Python resolver: prefer repo venv, fall back to python3 -------------------
PYTHON="python3"
if [[ -x "$PWD/.venv/bin/python" ]]; then
    PYTHON="$PWD/.venv/bin/python"
fi

# --- Scan args for launcher-relevant flags (without consuming them) ------------
WANT_FULLSCREEN=0
WANT_WINDOWED=0
WANT_PLATFORM=""
PREV=""
for arg in "$@"; do
    case "$arg" in
        --fullscreen) WANT_FULLSCREEN=1 ;;
        --windowed) WANT_WINDOWED=1 ;;
        --platform=*) WANT_PLATFORM="${arg#--platform=}" ;;
        --platform)
            PREV="platform"
            ;;
        *)
            if [[ "$PREV" == "platform" ]]; then
                WANT_PLATFORM="$arg"
            fi
            PREV=""
            ;;
    esac
done

HAS_DISPLAY=0
if [[ -n "${DISPLAY:-}" || -n "${WAYLAND_DISPLAY:-}" ]]; then
    HAS_DISPLAY=1
fi
case "${XDG_SESSION_TYPE:-}" in
    x11|wayland) HAS_DISPLAY=1 ;;
esac

HAS_DRM=0
if compgen -G "/dev/dri/card*" > /dev/null; then
    HAS_DRM=1
fi

# Explicit platform request (env or CLI) always wins over auto-detection.
if [[ -n "${QT_QPA_PLATFORM:-}" ]]; then
    MODE="explicit (QT_QPA_PLATFORM=$QT_QPA_PLATFORM)"
elif [[ -n "$WANT_PLATFORM" ]]; then
    export QT_QPA_PLATFORM="$WANT_PLATFORM"
    MODE="explicit (--platform $WANT_PLATFORM)"
elif [[ "$HAS_DISPLAY" -eq 1 ]]; then
    MODE="desktop"
    unset QT_QPA_PLATFORM || true
    unset QT_QPA_EGLFS_KMS_CONFIG || true
elif [[ "$HAS_DRM" -eq 1 ]]; then
    MODE="appliance (eglfs)"
    export QT_QPA_PLATFORM=eglfs
    export QT_QPA_EGLFS_ALWAYS_SET_MODE=1
    export QT_QPA_EGLFS_HIDECURSOR=1
    export QT_LOGGING_RULES="qt.qpa.*=false"
    # Resolve KMS config: fall back to the first present DRM card when the
    # shipped config points at a missing device (Pi4 card0 vs Pi5 card1, etc).
    KMS_CONFIG="$SCRIPT_DIR/eglfs.json"
    if [[ -f "$KMS_CONFIG" ]]; then
        CONFIGURED_DEV="$(grep -o '"/dev/dri/[^"]*"' "$KMS_CONFIG" | head -n 1 | tr -d '"')"
        if [[ -n "${CONFIGURED_DEV:-}" && ! -e "$CONFIGURED_DEV" ]]; then
            FIRST_CARD="$(compgen -G "/dev/dri/card*" | sort | head -n 1)"
            if [[ -n "${FIRST_CARD:-}" ]]; then
                TMP_KMS="$(mktemp /tmp/spectre-eglfs-XXXXXX.json)"
                sed "s|$CONFIGURED_DEV|$FIRST_CARD|g" "$KMS_CONFIG" > "$TMP_KMS"
                KMS_CONFIG="$TMP_KMS"
                echo "Note: $CONFIGURED_DEV missing, using $FIRST_CARD via $TMP_KMS" >&2
            else
                echo "Warning: no /dev/dri/card* found; eglfs may fail." >&2
            fi
        fi
    else
        echo "Warning: $KMS_CONFIG not found; running eglfs without KMS config." >&2
        KMS_CONFIG=""
    fi
    if [[ -n "${KMS_CONFIG:-}" ]]; then
        export QT_QPA_EGLFS_KMS_CONFIG="$KMS_CONFIG"
    else
        unset QT_QPA_EGLFS_KMS_CONFIG || true
    fi
else
    MODE="headless"
    unset QT_QPA_PLATFORM || true
    unset QT_QPA_EGLFS_KMS_CONFIG || true
fi

# --- Fullscreen default: on for appliance/eglfs, off for desktop/headless ----
EXTRA_ARGS=()
if [[ "$MODE" == appliance* && "$WANT_FULLSCREEN" -eq 0 && "$WANT_WINDOWED" -eq 0 ]]; then
    EXTRA_ARGS+=(--fullscreen)
fi

echo "Starting Juno Spectre Touch Workstation ($MODE)..."
echo "  python : $PYTHON"
echo "  qt     : ${QT_QPA_PLATFORM:-(auto)}"
if [[ -n "${QT_QPA_EGLFS_KMS_CONFIG:-}" ]]; then
    echo "  kms    : $QT_QPA_EGLFS_KMS_CONFIG"
fi
exec "$PYTHON" scripts/spectre_vector.py "${EXTRA_ARGS[@]}" "$@"
