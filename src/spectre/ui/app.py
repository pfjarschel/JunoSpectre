"""Qt Quick / QML Application runner for Juno Spectre.

Sets up the QML application engine, registers the Python-QML bridge,
and executes the 60 FPS touch UI.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import sys
from typing import Optional

from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQml import QQmlApplicationEngine, qmlRegisterSingletonInstance

from ..vector.engine import VectorEngine
from .bridge import SpectreBridge

logger = logging.getLogger(__name__)


def create_application(
    engine: Optional[VectorEngine] = None,
    platform: Optional[str] = None,
) -> tuple[QGuiApplication, QQmlApplicationEngine, SpectreBridge]:
    """Initialize Qt application and QML engine without entering exec loop."""
    if platform:
        os.environ["QT_QPA_PLATFORM"] = platform

    if engine is None:
        engine = VectorEngine()

    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv)

    qml_engine = QQmlApplicationEngine()

    # Create bridge with qml_engine as parent to prevent GC
    bridge = SpectreBridge(engine, parent=qml_engine)
    qml_engine._bridge = bridge

    # Register as global QML singleton 'Bridge' in module 'JunoSpectre'
    qmlRegisterSingletonInstance("JunoSpectre", 1, 0, "Bridge", bridge)
    qml_engine.rootContext().setContextProperty("bridge", bridge)

    # Set QML import path for singletons (Theme, ScaleMetrics)
    qml_dir = Path(__file__).resolve().parent / "qml"
    qml_engine.addImportPath(str(qml_dir))

    main_qml = qml_dir / "main.qml"
    qml_engine.load(QUrl.fromLocalFile(str(main_qml)))

    if not qml_engine.rootObjects():
        raise RuntimeError("Failed to load root QML object from main.qml")

    return app, qml_engine, bridge


def run_app(
    engine: Optional[VectorEngine] = None,
    fullscreen: bool = False,
    platform: Optional[str] = None,
) -> int:
    """Launch the Juno Spectre QML Touch Application."""
    app, qml_engine, bridge = create_application(engine=engine, platform=platform)

    # Hide mouse cursor for touch appliance
    app.setOverrideCursor(Qt.CursorShape.BlankCursor)

    if fullscreen and qml_engine.rootObjects():
        root_obj = qml_engine.rootObjects()[0]
        if hasattr(root_obj, "showFullScreen"):
            root_obj.showFullScreen()

    return app.exec()
