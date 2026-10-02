#!/usr/bin/env python3
"""Interactive touch appliance launcher for Juno Spectre Vector Engine.

Supports launching the hardware-accelerated Qt Quick touch UI on the Raspberry Pi
(via KMS/DRM eglfs or desktop) or PC, connecting to Roland synth and MIDI controllers.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys
import time

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PyQt6.QtCore import QTimer

from src.spectre.core.midi import MidiDeviceManager
from src.spectre.core.protocol import JunoClient
from src.spectre.control import MidiControllerEngine, ProfileManager
from src.spectre.ui.app import run_app, create_application
from src.spectre.vector.engine import VectorEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("spectre_vector")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Juno Spectre Touch Workstation Launcher")
    parser.add_argument("--mock", action="store_true", help="Force mock offline mode (no hardware required)")
    parser.add_argument("--fullscreen", action="store_true", help="Launch in fullscreen mode")
    parser.add_argument("--platform", type=str, default=None, help="Qt platform plugin (e.g. eglfs, wayland, xcb)")
    parser.add_argument("--juno-port", type=str, default=None, help="MIDI port name for Roland synth")
    parser.add_argument("--controller-port", type=str, default=None, help="MIDI port name for hardware controller")
    parser.add_argument("--profile", type=str, default="novation_lc_xl", help="Hardware controller profile name")
    parser.add_argument("--exit-after", type=float, default=None, help="Exit after N seconds (testing)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logger.info("Initializing Juno Spectre Touch Workstation...")

    juno_client: Optional[JunoClient] = None
    midi_mgr: Optional[MidiDeviceManager] = None
    ctrl_engine: Optional[MidiControllerEngine] = None

    if not args.mock:
        try:
            midi_mgr = MidiDeviceManager()
            midi_mgr.scan_devices()

            # Attempt to connect to Roland synth
            juno_in, juno_out = midi_mgr.find_juno_ports()
            if juno_in or juno_out or args.juno_port:
                logger.info(f"Connecting to Roland synth (in: {juno_in}, out: {juno_out})...")
                midi_mgr.open_juno(juno_in or args.juno_port, juno_out or args.juno_port)
                juno_client = JunoClient(midi_mgr)
                logger.info("Roland JunoClient connected.")
            else:
                logger.warning("No Roland synth found. Running in standalone mode.")

            # Attempt to connect to hardware controller
            lc_in, lc_out = midi_mgr.find_launch_control_ports()
            if lc_in or lc_out or args.controller_port:
                logger.info(f"Connecting to controller (in: {lc_in}, out: {lc_out})...")
                midi_mgr.open_launch_control(lc_in or args.controller_port, lc_out or args.controller_port)
                ctrl_engine = MidiControllerEngine(midi_mgr=midi_mgr, juno_client=juno_client)
                ctrl_engine.load_profile(args.profile)
                logger.info(f"Loaded controller profile '{args.profile}'.")
        except Exception as e:
            logger.warning(f"Hardware initialization failed, falling back to mock mode: {e}")

    # Initialize VectorEngine
    vector_engine = VectorEngine(juno_client=juno_client)

    # Link controller engine if available
    if ctrl_engine:
        def on_control_event(evt):
            # If controller moves vector X or Y, update vector engine
            if evt.target and evt.target.param_name == "vector_x":
                vector_engine.set_coordinates(evt.normalized_value, vector_engine.y)
            elif evt.target and evt.target.param_name == "vector_y":
                vector_engine.set_coordinates(vector_engine.x, evt.normalized_value)
            elif evt.target and evt.target.param_name == "wavetable_pos":
                vector_engine.set_wavetable_pos(evt.normalized_value)
        ctrl_engine.subscribe(on_control_event)

    # Launch Qt Quick Application
    app, qml_engine, bridge = create_application(
        engine=vector_engine,
        platform=args.platform,
    )

    if args.fullscreen and qml_engine.rootObjects():
        root_obj = qml_engine.rootObjects()[0]
        if hasattr(root_obj, "showFullScreen"):
            root_obj.showFullScreen()

    if args.exit_after is not None:
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(app.quit)
        timer.start(int(args.exit_after * 1000))

    logger.info("Juno Spectre UI started successfully.")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
