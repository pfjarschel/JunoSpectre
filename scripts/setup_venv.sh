#!/usr/bin/env bash
# Create the app venv (.venv) and install this checkout's requirements:
# system packages via apt/dnf/pacman (asks for the sudo password), then pip.
#
# Run once per machine; afterwards the in-app updater installs each release's
# new requirements into the venv itself, and start_spectre.sh always uses it.
# --system-site-packages lets the venv see apt's PyQt6 (on the Pi it's built
# against the system Qt with eglfs/KMS); everything else is pip-managed here.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [[ ! -x .venv/bin/python ]]; then
    if ! python3 -c "import ensurepip" 2> /dev/null && command -v apt-get > /dev/null; then
        sudo apt-get install -y python3-venv
    fi
    python3 -m venv --system-site-packages .venv
fi
exec .venv/bin/python src/spectre/core/updater.py install-deps
