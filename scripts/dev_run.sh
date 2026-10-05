#!/usr/bin/env bash
# Juno Spectre dev-PC launcher (mock mode, no touchscreen hardware required)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.." || exit 1
exec python scripts/spectre_vector.py --mock "$@"
