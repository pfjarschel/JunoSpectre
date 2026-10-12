#!/usr/bin/env bash
# Juno Spectre boot splash for Raspberry Pi OS (Plymouth).
#
# Usage: sudo bash scripts/boot-splash/install.sh [--enable|--disable|--uninstall]
#
#   (no option)  install Plymouth + the Spectre theme, normal boot unchanged,
#                and prepare a one-off test boot:  sudo reboot '0 tryboot'
#                (if that boot misbehaves, a power cycle boots normally again)
#   --enable     use the splash on every boot (after a good test boot)
#   --disable    back to the plain boot (Plymouth stays installed, inactive)
#   --uninstall  --disable, then remove Plymouth and everything added here
#
# How it fits together:
#   - Plymouth is kept out of the initramfs (hook below): it starts from the
#     root filesystem once the vc4 display driver is up, so it draws at the
#     panel's real mode (the EDID override is not in the initramfs).
#   - Plymouth only runs when cmdline.txt has "splash" (systemd drop-in), so
#     installing it changes nothing until --enable or the test boot.
#   - Handover: start_spectre.sh deactivates Plymouth (its picture stays on
#     screen) so the app becomes DRM master; the app quits Plymouth just
#     before its first frame (app.py) and opens on the same picture. The
#     plymouth-quit drop-in waits for that, up to 30 s.
#   - getty@tty1 is skipped on splash boots: it waits for Plymouth to quit,
#     so it would start after the app took the display, and resetting tty1
#     then breaks the app's page flips (black screen). Ctrl+Alt+F2 still
#     opens a local login; normal boots keep it.
set -euo pipefail

BOOT=/boot/firmware
CMDLINE=$BOOT/cmdline.txt
CONFIG=$BOOT/config.txt
TRY_CONFIG=$BOOT/tryboot.txt
TRY_CMDLINE_NAME=cmdline_tryboot.txt
THEME_DIR=/usr/share/plymouth/themes/spectre
HOOK=/etc/initramfs-tools/hooks/zz-spectre-no-plymouth
DROPIN_ALL=/etc/systemd/system/plymouth-.service.d/spectre-splash-only.conf
DROPIN_QUIT=/etc/systemd/system/plymouth-quit.service.d/spectre-handover.conf
DROPIN_GETTY=/etc/systemd/system/getty@tty1.service.d/spectre-splash.conf
MARK="# Juno Spectre boot splash"
SPLASH_ARGS=(quiet splash plymouth.ignore-serial-consoles logo.nologo vt.global_cursor_default=0)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/../.." && pwd)"
PICTURE="$REPO/src/spectre/assets/splash_1024x600.jpg"

usage() {
    echo "Usage: sudo bash $0 [--enable|--disable|--uninstall]" >&2
    exit 1
}

if [[ $(id -u) -ne 0 ]]; then
    echo "Run as root: sudo bash $0 $*" >&2
    exit 1
fi
if [[ ! -f $CMDLINE || ! -f $CONFIG ]]; then
    echo "$CMDLINE / $CONFIG not found: is this Raspberry Pi OS?" >&2
    exit 1
fi

backup() {
    [[ -e "$1.spectre-bak" ]] || cp -p "$1" "$1.spectre-bak"
}

# cmdline with the splash arguments added (stdin -> stdout, one line).
# Console output moves to tty3 (not shown), so early messages such as the
# initramfs root fsck do not print over the picture.
with_splash_args() {
    local cmd a
    cmd=" $(tr -d '\n') "
    cmd="${cmd// console=tty1 / console=tty3 }"
    for a in "${SPLASH_ARGS[@]}"; do
        grep -qwF -- "$a" <<< "$cmd" || cmd="$cmd $a"
    done
    echo "$cmd" | tr -s ' ' | sed -E 's/^ +| +$//g' | tr -d '\n'
}

# cmdline with the splash arguments removed
without_splash_args() {
    local cmd a
    cmd=" $(tr -d '\n') "
    for a in "${SPLASH_ARGS[@]}"; do
        cmd="${cmd// $a / }"
    done
    cmd="${cmd// console=tty3 / console=tty1 }"
    echo "$cmd" | tr -s ' ' | sed -E 's/^ +| +$//g' | tr -d '\n'
}

remove_config_block() {
    sed -i "/^$MARK\$/,+2d" "$1"
}

install_files() {
    if [[ ! -f $PICTURE ]]; then
        echo "$PICTURE missing (make it with tools/make_splash.py)" >&2
        exit 1
    fi

    # Before the package: its postinst rebuilds the initramfs
    cat > "$HOOK" <<'EOF'
#!/bin/sh
# Juno Spectre: keep Plymouth out of the initramfs. It starts from the root
# filesystem once the vc4 display driver is up (scripts/boot-splash).
# Plymouth's hook also adds the DRM drivers: those go too, so vc4 keeps
# loading from the root filesystem, where the drm.edid_firmware file is
# (in the initramfs it cannot find it and the panel comes up at 1920x1080).
PREREQ=""
prereqs() { echo "$PREREQ"; }
case $1 in prereqs) prereqs; exit 0 ;; esac
rm -f "$DESTDIR/scripts/init-premount/plymouth" "$DESTDIR/scripts/init-bottom/plymouth" \
      "$DESTDIR/scripts/panic/plymouth" "$DESTDIR/usr/bin/plymouth" "$DESTDIR/usr/sbin/plymouthd"
rm -rf "$DESTDIR/usr/share/plymouth"
# Modules are queued (manual_add_modules) and copied after all hooks ran:
# drop the queued DRM ones
if [ -n "${__MODULES_TO_ADD:-}" ] && [ -s "$__MODULES_TO_ADD" ]; then
    keep="$(mktemp)"
    while read -r m; do
        case "$(modinfo -k "$version" -n "$m" 2>/dev/null)" in
            */kernel/drivers/gpu/drm/*) ;;
            *) echo "$m" ;;
        esac
    done < "$__MODULES_TO_ADD" > "$keep"
    cat "$keep" > "$__MODULES_TO_ADD"
    rm -f "$keep"
fi
exit 0
EOF
    chmod 755 "$HOOK"

    mkdir -p "$(dirname "$DROPIN_ALL")" "$(dirname "$DROPIN_QUIT")" "$(dirname "$DROPIN_GETTY")"
    cat > "$DROPIN_ALL" <<'EOF'
# Juno Spectre: Plymouth only runs when cmdline.txt has "splash"
[Unit]
ConditionKernelCommandLine=splash
EOF
    cat > "$DROPIN_QUIT" <<'EOF'
# Juno Spectre: the app takes the screen from Plymouth and quits it before
# its first frame (start_spectre.sh, app.py); quit it here only if that has
# not happened within 30 s
[Service]
ExecStartPre=-/bin/sh -c 'i=0; while [ $i -lt 300 ] && /usr/bin/plymouth --ping; do sleep 0.1; i=$((i+1)); done'
TimeoutSec=60
EOF
    cat > "$DROPIN_GETTY" <<'EOF'
# Juno Spectre: no tty1 login prompt on splash boots. It would start after
# the app took the display (it waits for Plymouth) and break it.
[Unit]
ConditionKernelCommandLine=!splash
EOF
    systemctl daemon-reload

    if ! command -v plymouthd > /dev/null; then
        echo "Installing plymouth"
        export DEBIAN_FRONTEND=noninteractive
        apt-get update -qq
        apt-get install -y -qq --no-install-recommends plymouth
    else
        update-initramfs -u -k all
    fi

    mkdir -p "$THEME_DIR"
    cp "$SCRIPT_DIR/spectre.plymouth" "$SCRIPT_DIR/spectre.script" "$THEME_DIR/"
    # Plymouth reads PNG only; PyQt6 is there for the app anyway
    python3 - "$PICTURE" "$THEME_DIR/splash.png" <<'EOF'
import sys
from PyQt6.QtGui import QImage
img = QImage(sys.argv[1])
if img.isNull() or not img.save(sys.argv[2], "PNG"):
    sys.exit(f"could not convert {sys.argv[1]}")
EOF
    plymouth-set-default-theme spectre

    local listing
    listing="$(lsinitramfs "$BOOT/initramfs8")"
    if grep -q -E 'plymouthd$|/vc4\.ko' <<< "$listing"; then
        echo "Error: plymouth or vc4 ended up in the initramfs; not preparing the test boot" >&2
        exit 1
    fi
}

prepare_tryboot() {
    with_splash_args < "$CMDLINE" > "$BOOT/$TRY_CMDLINE_NAME"
    cp "$CONFIG" "$TRY_CONFIG"
    remove_config_block "$TRY_CONFIG"
    printf '\n%s\n[all]\ncmdline=%s\n' "$MARK" "$TRY_CMDLINE_NAME" >> "$TRY_CONFIG"
    echo "disable_splash=1" >> "$TRY_CONFIG"
}

remove_tryboot() {
    rm -f "$TRY_CONFIG" "$BOOT/$TRY_CMDLINE_NAME"
}

enable() {
    if [[ ! -d $THEME_DIR ]]; then
        echo "Install first: sudo bash $0" >&2
        exit 1
    fi
    backup "$CMDLINE"
    backup "$CONFIG"
    local cmd
    cmd="$(with_splash_args < "$CMDLINE")"
    printf '%s' "$cmd" > "$CMDLINE"
    if ! grep -q "^$MARK\$" "$CONFIG"; then
        printf '\n%s\n[all]\ndisable_splash=1\n' "$MARK" >> "$CONFIG"
    fi
    remove_tryboot
    echo "Boot splash enabled (originals in *.spectre-bak). Undo: sudo bash $0 --disable"
}

disable() {
    local cmd
    cmd="$(without_splash_args < "$CMDLINE")"
    printf '%s' "$cmd" > "$CMDLINE"
    remove_config_block "$CONFIG"
    remove_tryboot
    echo "Boot splash disabled."
}

uninstall() {
    disable
    rm -f "$DROPIN_ALL" "$DROPIN_QUIT" "$DROPIN_GETTY"
    rmdir --ignore-fail-on-non-empty "$(dirname "$DROPIN_ALL")" "$(dirname "$DROPIN_QUIT")" \
        "$(dirname "$DROPIN_GETTY")"
    systemctl daemon-reload
    rm -rf "$THEME_DIR"
    if dpkg -s plymouth > /dev/null 2>&1; then
        DEBIAN_FRONTEND=noninteractive apt-get purge -y -qq plymouth
    fi
    rm -f "$HOOK"
    update-initramfs -u -k all
    echo "Boot splash removed."
}

case "${1:-}" in
    "")
        install_files
        prepare_tryboot
        echo
        echo "Installed; the normal boot is unchanged. Test the splash once with:"
        echo "    sudo reboot '0 tryboot'"
        echo "If that boot is good: sudo bash $0 --enable"
        echo "If not: power cycle (boots normally), then sudo bash $0 --uninstall"
        ;;
    --enable) enable ;;
    --disable) disable ;;
    --uninstall) uninstall ;;
    *) usage ;;
esac
