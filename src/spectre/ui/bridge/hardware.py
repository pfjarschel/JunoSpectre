"""Hardware page: synth connection (ports, reconnect, identity ping).

A watcher thread scans the MIDI ports every 2 s (about 3 ms on the Pi).
When the synth's port disappears the connection is marked offline; when a
synth port shows up while offline, the app attaches to it and re-reads the
sound, so the JUNO-DS can be powered on after the app.
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path

from PyQt6.QtCore import pyqtProperty, pyqtSignal, pyqtSlot

from ...core.midi import MidiDeviceManager, port_key
from .base import BridgeBaseMixin

logger = logging.getLogger(__name__)

SCAN_INTERVAL_S = 2.0


def hardware_settings_path() -> Path:
    from ...librarian.repository import data_root

    return data_root() / "hardware.json"


def load_hardware_settings() -> dict:
    try:
        return dict(json.loads(hardware_settings_path().read_text()))
    except (OSError, ValueError, TypeError):
        return {}


def save_hardware_settings(settings: dict) -> None:
    path = hardware_settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(settings, indent=2))
        tmp.replace(path)
    except OSError as e:
        logger.warning(f"hardware settings not saved: {e}")


class HardwareBridgeMixin(BridgeBaseMixin):
    hardwareChanged = pyqtSignal()
    _portsScanned = pyqtSignal(list, list)  # watcher thread -> UI thread

    _midi_mgr: MidiDeviceManager | None = None
    _hw_inputs: list = []
    _hw_outputs: list = []
    _synth_identity: str = ""
    _ping_text: str = ""
    _hw_watch_stop: threading.Event | None = None
    _hw_auto_failed: tuple | None = None
    _hw_auto_pending: tuple | None = None

    def _init_hardware(self) -> None:
        self._hw_settings = load_hardware_settings()
        self._portsScanned.connect(self._on_ports_scanned)
        self.jobFinished.connect(self._on_hardware_job)

    def attach_midi_manager(self, midi_mgr: MidiDeviceManager | None, watch: bool = True) -> None:
        """Called at startup with the app's MIDI manager (also when the synth is absent)."""
        self._midi_mgr = midi_mgr
        if midi_mgr is not None:
            midi_mgr.juno_port_pref = str(self._hw_settings.get("synth_port", ""))
            self._follow_attach(midi_mgr)
        juno = self.juno
        if juno is not None:
            self._note_identity(getattr(juno, "_startup_identity", None), juno.last_ping_ms)
        if watch and self._hw_watch_stop is None:
            self._hw_watch_stop = threading.Event()
            threading.Thread(target=self._port_watch_loop, name="midi-port-watch",
                             daemon=True).start()

    def stop_hardware_watch(self) -> None:
        if self._hw_watch_stop is not None:
            self._hw_watch_stop.set()
        self.close_controllers()
        if hasattr(self, "close_audio"):
            self.close_audio()

    # -- port watcher ------------------------------------------------------

    @staticmethod
    def _scan_ports() -> tuple[list, list]:
        try:
            return list(MidiDeviceManager.get_input_names()), list(MidiDeviceManager.get_output_names())
        except Exception as e:
            logger.debug(f"MIDI port scan failed: {e}")
            return [], []

    def _port_watch_loop(self) -> None:
        stop = self._hw_watch_stop
        while stop is not None and not stop.is_set():
            ins, outs = self._scan_ports()
            try:
                self._portsScanned.emit(ins, outs)
            except RuntimeError:
                return  # bridge gone
            stop.wait(SCAN_INTERVAL_S)

    @pyqtSlot(list, list)
    def _on_ports_scanned(self, ins: list, outs: list) -> None:
        changed = ins != self._hw_inputs or outs != self._hw_outputs
        self._hw_inputs, self._hw_outputs = ins, outs
        mgr = self._midi_mgr
        juno = self.juno
        if juno is not None and juno.is_connected and mgr is not None:
            in_name = getattr(mgr.juno_in, "name", "")
            if in_name and port_key(in_name) not in {port_key(n) for n in ins}:
                logger.warning(f"Synth port '{in_name}' disappeared; marking offline")
                mgr.close_juno()
                self._synth_identity, self._ping_text = "", ""
                changed = True
        elif (mgr is not None and not self.jobBusy and self._synth_port_available(ins, outs)
              and self._hw_auto_failed != (ins, outs)):
            # Auto-attach; after a failure, wait for the port list to change
            self._hw_auto_pending = (ins, outs)
            self.reconnectSynth()
        self._ctl_sync_ports(ins)
        if changed:
            self.hardwareChanged.emit()
            self.controllersChanged.emit()

    def _synth_port_available(self, ins: list, outs: list) -> bool:
        pref = self._midi_mgr.juno_port_pref if self._midi_mgr else ""
        if pref:
            return pref in {port_key(n) for n in ins} and pref in {port_key(n) for n in outs}
        keys = ("JUNO", "XPS")
        return any(k in n for n in ins for k in keys) and any(k in n for n in outs for k in keys)

    # -- QML API -------------------------------------------------------------

    @pyqtProperty(bool, notify=hardwareChanged)
    def synthConnected(self) -> bool:
        juno = self.juno
        return bool(juno is not None and juno.is_connected)

    @pyqtProperty(str, notify=hardwareChanged)
    def synthPort(self) -> str:
        mgr = self._midi_mgr
        out = getattr(mgr, "juno_out", None) if mgr is not None else None
        if out is None or getattr(out, "closed", True):
            return ""
        return port_key(getattr(out, "name", ""))

    @pyqtProperty(str, notify=hardwareChanged)
    def synthPortPref(self) -> str:
        return self._midi_mgr.juno_port_pref if self._midi_mgr else ""

    @pyqtProperty(str, notify=hardwareChanged)
    def synthIdentity(self) -> str:
        return self._synth_identity

    @pyqtProperty(str, notify=hardwareChanged)
    def pingText(self) -> str:
        return self._ping_text

    @pyqtProperty("QVariantList", notify=hardwareChanged)
    def midiPorts(self) -> list:
        """Every port by name: [{key, input, output, synth}] (synth = in use by the synth)."""
        synth = self.synthPort
        keys: dict[str, dict] = {}
        for n in self._hw_inputs:
            k = port_key(n)
            keys.setdefault(k, {"key": k, "input": False, "output": False, "synth": k == synth})["input"] = True
        for n in self._hw_outputs:
            k = port_key(n)
            keys.setdefault(k, {"key": k, "input": False, "output": False, "synth": k == synth})["output"] = True
        # Hide ALSA's loopback and this app's own rtmidi client ports
        return [v for k, v in keys.items()
                if "Midi Through" not in k and not k.startswith(("RtMidiIn Client", "RtMidiOut Client"))]

    @pyqtSlot()
    def refreshPorts(self) -> None:
        self._on_ports_scanned(*self._scan_ports())
        self.hardwareChanged.emit()

    @pyqtSlot(str)
    def setSynthPort(self, key: str) -> None:
        """Pick the synth port by name ("" = auto-detect) and reconnect."""
        key = str(key or "")
        self._hw_settings["synth_port"] = key
        save_hardware_settings(self._hw_settings)
        if self._midi_mgr is not None:
            self._midi_mgr.juno_port_pref = key
        self.hardwareChanged.emit()
        self.reconnectSynth()

    @pyqtSlot(result=bool)
    def reconnectSynth(self) -> bool:
        """(Re)open the synth ports, ping, and re-read the sound. jobFinished("connect", {ok, error})."""
        if self._midi_mgr is None:
            self._midi_mgr = MidiDeviceManager()
            self._midi_mgr.juno_port_pref = str(self._hw_settings.get("synth_port", ""))
        mgr = self._midi_mgr
        existing = self.juno

        def run(progress):
            from ...core.protocol import JunoClient

            if existing is None:
                mgr.close_juno()
                try:
                    mgr.connect_juno(mgr.juno_port_pref)
                except Exception as e:
                    return {"ok": False, "error": str(e)}
                client = JunoClient(mgr)
            else:
                if not mgr.reconnect_juno():
                    return {"ok": False, "error": "Synth ports not found."}
                existing.invalidate_cache()
                client = existing
            info = client.ping(timeout=1.0)
            if info is None:
                return {"ok": False, "error": "Ports open, but the synth did not answer the identity request."}
            client.adopt_device_id(info.device_id)
            self._new_client = client if existing is None else None
            return {"ok": True, "identity": self._identity_text(info), "ms": client.last_ping_ms}

        return self._start_job("connect", "Connecting to the synth…", run)

    @pyqtSlot(result=bool)
    def pingSynth(self) -> bool:
        """Identity request round trip. jobFinished("ping", {ok, ms, identity})."""
        juno = self.juno
        if juno is None or not juno.is_connected:
            self._ping_text = "NOT CONNECTED"
            self.hardwareChanged.emit()
            return False

        def run(progress):
            info = juno.ping(timeout=1.0)
            if info is None:
                return {"ok": False, "error": "No reply within 1 s."}
            juno.adopt_device_id(info.device_id)
            return {"ok": True, "identity": self._identity_text(info), "ms": juno.last_ping_ms}

        return self._start_job("ping", "Pinging the synth…", run)

    @staticmethod
    def _identity_text(info) -> str:
        name = "JUNO-DS / XPS-30" if info.is_juno_ds_or_xps else (
            f"Roland family {info.family_code[0]:02X} {info.family_code[1]:02X}")
        rev = ".".join(str(b) for b in info.software_revision)
        return f"{name} · device ID {info.device_id + 1} · rev {rev}"

    def _note_identity(self, info, ms: float) -> None:
        if info is None:
            return
        self._synth_identity = self._identity_text(info)
        self._ping_text = f"OK · {ms:.1f} ms"

    def _on_hardware_job(self, name: str, result) -> None:
        if name not in ("connect", "ping"):
            return
        result = result if isinstance(result, dict) else {}
        if name == "connect":
            self._hw_auto_failed = None if result.get("ok") else self._hw_auto_pending
            self._hw_auto_pending = None
        if result.get("ok"):
            self._synth_identity = str(result.get("identity", ""))
            self._ping_text = f"OK · {float(result.get('ms', 0.0)):.1f} ms"
        else:
            self._ping_text = str(result.get("error", "") or "FAILED")
        if name == "connect" and result.get("ok"):
            client = getattr(self, "_new_client", None)
            self._new_client = None
            if client is not None:
                self.juno = client
                self._attach_seq_midi(self._midi_mgr)
            logger.info(f"Synth connected: {self._synth_identity}")
            self.syncPatchFromSynth(async_mode=True)
        self.hardwareChanged.emit()
