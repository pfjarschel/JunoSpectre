"""Juno Spectre launcher: the touch workstation app.

Unified entry point for Raspberry Pi appliance and desktop PC: always probes
for the Roland synth and MIDI controllers, and keeps the full UI usable
offline (patch editing, saving, librarian) when no hardware is present.

Started by scripts/start_spectre.sh (which picks the Qt platform, eglfs on the
Pi, then runs scripts/spectre_app.py) or, after a pip install, by the
`juno-spectre` command (desktop: Qt picks the platform, or pass --platform).
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Optional, Sequence

from PyQt6.QtCore import QTimer

from .core.midi import MidiDeviceManager, port_key
from .core.protocol import JunoClient
from .ui.app import create_application, quit_boot_splash

logger = logging.getLogger("spectre_app")


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Juno Spectre Touch Workstation Launcher")
    parser.add_argument("--fullscreen", action="store_true", help="Launch in fullscreen mode")
    parser.add_argument("--windowed", action="store_true", help="Force windowed mode (overrides --fullscreen)")
    parser.add_argument("--platform", type=str, default=None, help="Qt platform plugin (e.g. eglfs, wayland, xcb)")
    parser.add_argument("--juno-port", type=str, default=None, help="MIDI port name for Roland synth")
    parser.add_argument("--list-ports", action="store_true", help="List detected MIDI ports and exit (no UI)")
    parser.add_argument("--no-splash", action="store_true", help="Build the UI right away, without the startup splash")
    parser.add_argument("--exit-after", type=float, default=None, help="Exit after N seconds (testing)")
    return parser.parse_args(argv)


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

    print("MIDI inputs:")
    for name in inputs:
        print(f"  - {name}")
    print("MIDI outputs:")
    for name in outputs:
        print(f"  - {name}")
    print(f"Roland synth: in={juno_in!r} out={juno_out!r}")
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


def main(argv: Optional[Sequence[str]] = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    args = parse_args(argv)

    if args.list_ports:
        return list_ports()

    logger.info("Initializing Juno Spectre Touch Workstation...")

    juno_client: Optional[JunoClient] = None
    midi_mgr: Optional[MidiDeviceManager] = None

    try:
        midi_mgr = MidiDeviceManager()

        # Attempt to connect to Roland synth
        try:
            if args.juno_port:
                logger.info(f"Connecting to user-specified Roland synth port: {args.juno_port}...")
                midi_mgr.connect_juno(port_key(args.juno_port))
            else:
                logger.info("Scanning for Roland synth (JUNO-DS / XPS-30)...")
                in_n, out_n = midi_mgr.connect_juno()
                logger.info(f"Connected to Roland synth (in: {in_n}, out: {out_n})")

            juno_client = JunoClient(midi_mgr)
            try:
                info = juno_client.ping(timeout=1.0)
                if info:
                    logger.info(f"Roland synth verified via SysEx ping: {info}")
                    juno_client.adopt_device_id(info.device_id)
                    juno_client._startup_identity = info
                    p_name = juno_client.get_patch_name(timeout=1.0)
                    logger.info(f"Active synth patch: '{p_name}'")
            except Exception as ping_ex:
                logger.warning(f"SysEx ping query note: {ping_ex}")

            logger.info("Roland JunoClient operational.")
        except Exception as e:
            logger.warning(f"Roland synth not connected ({e}). Available ports: {_describe_ports()}")

    except Exception as e:
        logger.warning(f"Hardware initialization failed, continuing offline (UI remains editable): {e}")

    if juno_client is None:
        logger.info("No MIDI hardware detected: running offline, full editing/saving remains available.")

    # Launch Qt Quick Application
    app, qml_engine, bridge = create_application(
        juno=juno_client,
        platform=args.platform,
        splash=not args.no_splash,
    )

    # Hardware page: port watcher, reconnect, and attaching a synth powered on later
    bridge.attach_midi_manager(midi_mgr)

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

    import signal

    def _sig_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful teardown...")
        try:
            bridge._perform_appliance_cleanup("signal")
        except Exception:
            pass
        if midi_mgr:
            try:
                midi_mgr.send_all_notes_off()
                midi_mgr.close()
            except Exception:
                pass
        app.quit()

    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)

    # Allow Python to process OS signals while Qt event loop is active
    sig_timer = QTimer()
    sig_timer.timeout.connect(lambda: None)
    sig_timer.start(500)

    if args.exit_after is not None:
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(app.quit)
        timer.start(int(args.exit_after * 1000))

    from .ui.stall_watchdog import maybe_start as _start_stall_log
    _stall_log = _start_stall_log(app)  # noqa: F841 (kept alive with the app)

    quit_boot_splash()  # last thing before the first frame (see app.py)
    logger.info("Juno Spectre UI started successfully.")
    try:
        return app.exec()
    finally:
        sig_timer.stop()
        bridge.stop_hardware_watch()
        try:
            bridge._perform_appliance_cleanup("exit")
        except Exception:
            pass
        if midi_mgr:
            try:
                midi_mgr.close()
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
