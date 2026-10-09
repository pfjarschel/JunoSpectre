import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


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
