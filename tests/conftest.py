import os
import shutil
import tempfile

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Keep every test away from the real data: settings (hardware.json), the
# librarian DB and ~/SpectreAudio all resolve under this scratch dir. Set at
# import time, before any spectre module computes a path from HOME. Tests that
# need their own dir still monkeypatch JUNOSPECTRE_DATA_DIR on top of this.
_SCRATCH = tempfile.mkdtemp(prefix="spectre-tests-")
os.environ["HOME"] = os.path.join(_SCRATCH, "home")
os.environ["JUNOSPECTRE_DATA_DIR"] = os.path.join(_SCRATCH, "data")
os.makedirs(os.environ["HOME"], exist_ok=True)


@pytest.fixture(scope="session", autouse=True)
def _scratch_dir():
    yield _SCRATCH
    shutil.rmtree(_SCRATCH, ignore_errors=True)


@pytest.fixture(scope="session", autouse=True)
def qt_app():
    """One Qt application for the whole run.

    Tests that created their own QCoreApplication without keeping it let it be
    garbage-collected mid-suite, destroying the event dispatcher under live
    QObjects. Bridges created afterwards could then lose their C++ object while
    still in use ("wrapped C/C++ object ... has been deleted"), making tests flaky.
    Creating it up front makes every `QCoreApplication.instance()` reuse this one.
    """
    from PyQt6.QtGui import QGuiApplication

    app = QGuiApplication.instance() or QGuiApplication([])
    yield app
