#!/usr/bin/env python3
"""Interactive touch appliance launcher for Juno Spectre Vector Engine.

Unified entry point for Raspberry Pi appliance and desktop PC: always probes
for the Roland synth and MIDI controllers, and keeps the full UI usable
offline (patch editing, saving, librarian) when no hardware is present.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys
from typing import Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PyQt6.QtCore import QTimer
import mido

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
    parser.add_argument("--fullscreen", action="store_true", help="Launch in fullscreen mode")
    parser.add_argument("--windowed", action="store_true", help="Force windowed mode (overrides --fullscreen)")
    parser.add_argument("--platform", type=str, default=None, help="Qt platform plugin (e.g. eglfs, wayland, xcb)")
    parser.add_argument("--juno-port", type=str, default=None, help="MIDI port name for Roland synth")
    parser.add_argument("--controller-port", type=str, default=None, help="MIDI port name for hardware controller")
    parser.add_argument("--profile", type=str, default="novation_lc_xl", help="Hardware controller profile name")
    parser.add_argument("--list-ports", action="store_true", help="List detected MIDI ports and exit (no UI)")
    parser.add_argument("--exit-after", type=float, default=None, help="Exit after N seconds (testing)")
    return parser.parse_args()


def list_ports() -> int:
    try:
        inputs = MidiDeviceManager.get_input_names()
    except Exception as e:
        logger.warning(f"Could not enumerate MIDI inputs: {e}")
        inputs = []
    try:
        outputs = MidiDeviceManager.get_output_names()
    except Exception as e:
        logger.warning(f"Could not enumerate MIDI outputs: {e}")
        outputs = []
    juno_in, juno_out = MidiDeviceManager.find_juno_ports()
    lc_in, lc_out = MidiDeviceManager.find_launch_control_ports()

    print("MIDI inputs:")
    for name in inputs:
        print(f"  - {name}")
    print("MIDI outputs:")
    for name in outputs:
        print(f"  - {name}")
    print(f"Roland synth: in={juno_in!r} out={juno_out!r}")
    print(f"Controller:   in={lc_in!r} out={lc_out!r}")
    if not inputs and not outputs:
        print("No MIDI ports detected (offline UI mode still fully usable).")
    return 0


def _describe_ports() -> str:
    try:
        return (
            f"inputs={MidiDeviceManager.get_input_names()}, "
            f"outputs={MidiDeviceManager.get_output_names()}"
        )
    except Exception as e:
        return f"<port enumeration failed: {e}>"


def main() -> int:
    args = parse_args()

    if args.list_ports:
        return list_ports()

    logger.info("Initializing Juno Spectre Touch Workstation...")

    juno_client: Optional[JunoClient] = None
    midi_mgr: Optional[MidiDeviceManager] = None
    ctrl_engine: Optional[MidiControllerEngine] = None

    try:
        midi_mgr = MidiDeviceManager()

        # Attempt to connect to Roland synth
        try:
            if args.juno_port:
                logger.info(f"Connecting to user-specified Roland synth port: {args.juno_port}...")
                midi_mgr.juno_in = mido.open_input(args.juno_port)
                midi_mgr.juno_out = mido.open_output(args.juno_port)
            else:
                logger.info("Scanning for Roland synth (JUNO-DS / XPS-30)...")
                in_n, out_n = midi_mgr.connect_juno()
                logger.info(f"Connected to Roland synth (in: {in_n}, out: {out_n})")

            juno_client = JunoClient(midi_mgr)
            try:
                info = juno_client.ping(timeout=1.0)
                if info:
                    logger.info(f"Roland synth verified via SysEx ping: {info}")
                    p_name = juno_client.get_patch_name(timeout=1.0)
                    logger.info(f"Active synth patch: '{p_name}'")
            except Exception as ping_ex:
                logger.warning(f"SysEx ping query note: {ping_ex}")

            logger.info("Roland JunoClient operational.")
        except Exception as e:
            logger.warning(f"Roland synth not connected ({e}). Available ports: {_describe_ports()}")

        # Attempt to connect to hardware controller
        try:
            if args.controller_port:
                logger.info(f"Connecting to controller port: {args.controller_port}...")
                midi_mgr.connect_controller(args.controller_port)
            else:
                midi_mgr.connect_launch_control()
            ctrl_engine = MidiControllerEngine(midi_mgr=midi_mgr, juno_client=juno_client)
            ctrl_engine.load_profile(args.profile)
            logger.info(f"Loaded controller profile '{args.profile}'.")
        except Exception as e:
            logger.info(f"No hardware controller connected ({e}). Available ports: {_describe_ports()}")

    except Exception as e:
        logger.warning(f"Hardware initialization failed, continuing offline (UI remains editable): {e}")

    if juno_client is None and ctrl_engine is None:
        logger.info("No MIDI hardware detected: running offline, full editing/saving remains available.")

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

    # Auto-detect patch and waveform state from connected Roland synth
    if juno_client:
        try:
            logger.info("Auto-syncing patch state and waveforms from Roland synthesizer...")
            bridge.syncPatchFromSynth()
        except Exception as e:
            logger.warning(f"Initial synth sync failed: {e}")

    fullscreen = args.fullscreen and not args.windowed
    if fullscreen and qml_engine.rootObjects():
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
