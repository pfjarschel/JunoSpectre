#!/usr/bin/env python3
"""Run the Juno Spectre app from a checkout (see src/spectre/launcher.py).

scripts/start_spectre.sh picks the Qt platform and starts this; arguments
pass through to the launcher.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from spectre.launcher import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
