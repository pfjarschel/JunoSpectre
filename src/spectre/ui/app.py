"""Qt Quick / QML Application runner for Juno Spectre.

Sets up the QML application engine, registers the Python-QML bridge,
and executes the 60 FPS touch UI.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QFont, QFontDatabase, QGuiApplication
from PyQt6.QtQml import QQmlApplicationEngine, qmlRegisterSingletonInstance
from PyQt6.QtQuick import QQuickWindow

from ..core.protocol import JunoClient
from .bridge import SpectreBridge

logger = logging.getLogger(__name__)

FONTS_DIR = Path(__file__).parent / "fonts"


def load_fonts(app: QGuiApplication) -> None:
    """Register the bundled fonts so the Pi renders exactly like the PC.

    Noto Sans is the UI font (Noto Sans Mono covers its missing arrows);
    Phosphor holds the icon glyphs (see qml/Icons.qml).
    """
    for path in sorted(FONTS_DIR.glob("*.ttf")):
        if QFontDatabase.addApplicationFont(str(path)) < 0:
            logger.warning("Could not load font %s", path.name)
    QFont.insertSubstitution("Noto Sans", "Noto Sans Mono")
    app.setFont(QFont("Noto Sans"))


def quit_boot_splash() -> None:
    """Close the Plymouth boot splash (scripts/boot-splash). Call right before
    the event loop starts, i.e. before the first frame.

    start_spectre.sh deactivated Plymouth (and set SPECTRE_QUIT_PLYMOUTH) so
    eglfs could become DRM master. Quitting it hands the VT back to the
    console, which resets the display; eglfs sets its mode on its first page
    flip, so this has to happen before that flip: after it, every flip fails
    and the screen stays black.
    """
    if os.environ.pop("SPECTRE_QUIT_PLYMOUTH", "") != "1":
        return
    try:
        subprocess.run(["sudo", "-n", "plymouth", "quit", "--retain-splash"],
                       timeout=5, capture_output=True)
        for _ in range(30):  # until plymouthd is gone (it resets the VT on exit)
            if subprocess.run(["sudo", "-n", "plymouth", "--ping"],
                              timeout=2, capture_output=True).returncode != 0:
                break
            time.sleep(0.1)
    except (OSError, subprocess.SubprocessError):
        logger.warning("Could not quit the boot splash", exc_info=True)


def _show_ui_after_splash(window: QQuickWindow) -> None:
    """Build the UI once the splash frame is on screen (see main.qml).

    frameSwapped comes from the render thread, hence the queued connection;
    it is dropped after the first frame.
    """

    def on_first_frame() -> None:
        try:
            window.frameSwapped.disconnect(on_first_frame)
        except TypeError:
            return  # a second queued frame: already handled
        window.setProperty("splashShown", True)

    window.frameSwapped.connect(on_first_frame, Qt.ConnectionType.QueuedConnection)


def create_application(
    juno: Optional[JunoClient] = None,
    platform: Optional[str] = None,
    splash: bool = False,
) -> tuple[QGuiApplication, QQmlApplicationEngine, SpectreBridge]:
    """Initialize Qt application and QML engine without entering exec loop.

    With ``splash`` the window opens on the splash picture and builds the UI
    after that first frame, so the event loop must run before the UI exists.
    """
    if platform:
        os.environ["QT_QPA_PLATFORM"] = platform

    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv)
    load_fonts(app)

    qml_engine = QQmlApplicationEngine()

    # Create bridge with qml_engine as parent to prevent GC
    bridge = SpectreBridge(juno, parent=qml_engine)
    qml_engine._bridge = bridge

    # Patch Librarian: file-backed user patches + SQLite index over them.
    # Non-fatal: the UI must still boot when the librarian fails (e.g. RO home).
    # The failure reason is kept on bridge._library_error and shown in the
    # Librarian view instead of failing silently (silent mock confused users).
    bridge._library_error = ""
    try:
        from ..librarian.repository import PatchRepository
        from .librarian_model import PatchListModel

        _repo = PatchRepository()
        try:
            stats = _repo.rescan_files()
            logger.info(f"Librarian rescan: {stats}")
        except Exception:
            logger.exception("Librarian rescan failed")
        _library = PatchListModel(_repo, parent=qml_engine)
        try:
            n = _library.refresh("", "ALL", False, "", 2500)
            logger.info(f"Librarian bound: {n} rows from {_repo.db_path}")
        except Exception:
            logger.exception("Librarian initial refresh failed")
        qml_engine._librarian_repo = _repo
        qml_engine._librarian_model = _library
        bridge._librarian_repo = _repo
        bridge._librarian_model = _library
        qml_engine.rootContext().setContextProperty("patchLibrary", _library)
    except Exception as e:
        logger.exception("Patch librarian unavailable")
        bridge._library_error = f"{type(e).__name__}: {e}"
        try:
            from .librarian_model import PatchListModel as _EmptyModel

            # Bind an empty model anyway: the view binds declaratively and
            # shows the offline banner via Bridge.libraryError instead of
            # silently falling back to demo data.
            _empty = _EmptyModel(None, parent=qml_engine)
            qml_engine._librarian_model = _empty
            qml_engine.rootContext().setContextProperty("patchLibrary", _empty)
        except Exception:
            logger.exception("Could not bind empty library model")
        try:
            bridge.libraryErrorChanged.emit()
        except Exception:
            pass

    # Register as global QML singleton 'Bridge' in module 'JunoSpectre'
    qmlRegisterSingletonInstance("JunoSpectre", 1, 0, "Bridge", bridge)
    qml_engine.rootContext().setContextProperty("bridge", bridge)

    # Set QML import path for singletons (Theme, ScaleMetrics)
    qml_dir = Path(__file__).resolve().parent / "qml"
    qml_engine.addImportPath(str(qml_dir))

    main_qml = qml_dir / "main.qml"
    if splash:
        qml_engine.setInitialProperties({"splashStartup": True})
    qml_engine.load(QUrl.fromLocalFile(str(main_qml)))

    if not qml_engine.rootObjects():
        raise RuntimeError("Failed to load root QML object from main.qml")
    root = qml_engine.rootObjects()[0]
    if splash and isinstance(root, QQuickWindow):
        _show_ui_after_splash(root)

    return app, qml_engine, bridge


def run_app(
    juno: Optional[JunoClient] = None,
    fullscreen: bool = False,
    platform: Optional[str] = None,
) -> int:
    """Launch the Juno Spectre QML Touch Application."""
    app, qml_engine, bridge = create_application(juno=juno, platform=platform, splash=True)

    # Hide mouse cursor for touch appliance
    app.setOverrideCursor(Qt.CursorShape.BlankCursor)

    if fullscreen and qml_engine.rootObjects():
        root_obj = qml_engine.rootObjects()[0]
        if hasattr(root_obj, "showFullScreen"):
            root_obj.showFullScreen()

    quit_boot_splash()
    try:
        return app.exec()
    finally:
        try:
            bridge._perform_appliance_cleanup("app_exit")
        except Exception:
            pass
