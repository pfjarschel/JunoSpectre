"""Background jobs: long synth round-trips run off the UI thread."""

import threading
import time

import pytest

from src.spectre.ui.app import create_application
from src.spectre.vector.engine import VectorEngine

pytestmark = pytest.mark.ui


@pytest.fixture
def ui():
    app, qml_engine, bridge = create_application(engine=VectorEngine(), platform="offscreen")
    yield app, bridge
    del qml_engine


def _wait(app, bridge, name, timeout=3.0):
    got = []
    bridge.jobFinished.connect(lambda n, r: got.append((n, r)))
    end = time.time() + timeout
    while time.time() < end and not any(n == name for n, _ in got):
        app.processEvents()
        time.sleep(0.005)
    return [r for n, r in got if n == name]


def test_job_runs_off_thread_reports_progress_and_finishes(ui):
    app, bridge = ui
    seen = {}
    release = threading.Event()

    def work(progress):
        seen["thread"] = threading.current_thread().name
        progress(0.5, "halfway")
        release.wait(2.0)
        return 42

    assert bridge._start_job("demo", "Working…", work)
    assert bridge.jobBusy and bridge.jobName == "demo"
    assert not bridge._start_job("other", "x", lambda p: 0)   # one at a time
    end = time.time() + 2
    while bridge.jobProgress != 0.5 and time.time() < end:
        app.processEvents()
    assert (bridge.jobProgress, bridge.jobText) == (0.5, "halfway")
    release.set()
    assert _wait(app, bridge, "demo") == [42]
    assert seen["thread"] == "job-demo"
    assert not bridge.jobBusy and bridge.jobProgress == -1.0


def test_failing_job_reports_error_and_frees_runner(ui):
    app, bridge = ui

    def boom(progress):
        raise RuntimeError("cable pulled")

    assert bridge._start_job("bad", "x", boom)
    assert _wait(app, bridge, "bad") == [{"error": "cable pulled"}]
    assert not bridge.jobBusy


def test_offline_library_load_and_slot_refresh(ui):
    app, bridge = ui
    assert bridge.startLibraryLoad("patch", 87, 64, 0, "Grand Pno DS")
    assert _wait(app, bridge, "load") == [True]
    assert bridge.startSlotNameRefresh("patch")
    assert _wait(app, bridge, "slotNames") == [-1]      # no synth / no repo


def test_save_job_reports_pi_failure_offline(ui):
    app, bridge = ui
    assert bridge.startSave({"name": "TEST", "toDevice": False})
    (result,) = _wait(app, bridge, "save")
    assert result["saved"] is False and result["error"]


def test_save_job_writes_library_from_worker_thread(tmp_path):
    """The librarian DB is shared with the worker (SQLite opened without
    Python's same-thread check)."""
    from PyQt6.QtGui import QGuiApplication

    from tests.test_performance import _bridge_rig

    bridge, juno, repo = _bridge_rig(tmp_path)
    app = QGuiApplication.instance()
    assert bridge.startSave({"name": "THREADSAVE", "toDevice": False})
    (result,) = _wait(app, bridge, "save")
    assert result["saved"] and not result["error"], result
    assert any(r.get("name") == "THREADSAVE" for r in repo.search("THREADSAVE", limit=10))
