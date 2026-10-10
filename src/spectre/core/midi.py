"""MIDI port discovery and hardware transport layer.

Handles device matching for Roland JUNO-DS / XPS-30 and Novation Launch Control XL,
providing safe ALSA port opening, message sending, and non-blocking polling.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from typing import Callable, Generator, List, Optional, Tuple

import mido

logger = logging.getLogger(__name__)


class MidiDeviceManager:
    """Manages discovery and lifecycle of MIDI hardware ports."""

    @staticmethod
    def get_input_names() -> list[str]:
        """Return available ALSA MIDI input port names."""
        return mido.get_input_names()

    @staticmethod
    def get_output_names() -> list[str]:
        """Return available ALSA MIDI output port names."""
        return mido.get_output_names()

    @classmethod
    def find_juno_ports(cls) -> Tuple[Optional[str], Optional[str]]:
        """Find JUNO-DS or XPS-30 MIDI In and Out ports.

        Prefers 'MIDI 1' (sound engine) over 'MIDI 2' (DAW control).
        """
        inputs = cls.get_input_names()
        outputs = cls.get_output_names()

        target_keywords = ["JUNO-DS", "XPS-30", "JUNO", "XPS"]

        in_port: Optional[str] = None
        out_port: Optional[str] = None

        # Look for MIDI 1 specifically first
        for name in inputs:
            if any(k in name for k in target_keywords) and "MIDI 1" in name:
                in_port = name
                break
        if not in_port:
            for name in inputs:
                if any(k in name for k in target_keywords):
                    in_port = name
                    break

        for name in outputs:
            if any(k in name for k in target_keywords) and "MIDI 1" in name:
                out_port = name
                break
        if not out_port:
            for name in outputs:
                if any(k in name for k in target_keywords):
                    out_port = name
                    break

        return in_port, out_port

    @classmethod
    def find_launch_control_ports(cls) -> Tuple[Optional[str], Optional[str]]:
        """Find Novation Launch Control XL MIDI ports.

        Prefers standard MIDI In/Out over DAW In/Out.
        """
        inputs = cls.get_input_names()
        outputs = cls.get_output_names()

        target_keywords = ["LCXL", "Launch Control"]

        in_port: Optional[str] = None
        out_port: Optional[str] = None

        for name in inputs:
            if any(k in name for k in target_keywords) and "MIDI In" in name:
                in_port = name
                break
        if not in_port:
            for name in inputs:
                if any(k in name for k in target_keywords) and "DAW" not in name:
                    in_port = name
                    break

        for name in outputs:
            if any(k in name for k in target_keywords) and "MIDI Out" in name:
                out_port = name
                break
        if not out_port:
            for name in outputs:
                if any(k in name for k in target_keywords) and "DAW" not in name:
                    out_port = name
                    break

        return in_port, out_port

    def __init__(self):
        self.juno_in: Optional[mido.ports.BaseInput] = None
        self.juno_out: Optional[mido.ports.BaseOutput] = None
        self.lcxl_in: Optional[mido.ports.BaseInput] = None
        self.lcxl_out: Optional[mido.ports.BaseOutput] = None

        self._note_listeners: List[Callable[[mido.Message], None]] = []
        # SysEx replies for request/response reads; bounded so unread traffic can't pile up.
        self._sysex_queue: queue.Queue = queue.Queue(maxsize=256)
        self._worker_thread: Optional[threading.Thread] = None
        self._worker_running: bool = False

    def connect_juno(self) -> Tuple[str, str]:
        """Open bidirectional MIDI connection to JUNO-DS / XPS-30."""
        in_name, out_name = self.find_juno_ports()
        if not in_name or not out_name:
            raise ConnectionError(
                f"Could not find Roland synth ports. Available inputs: {self.get_input_names()}, "
                f"outputs: {self.get_output_names()}"
            )

        self.juno_in = mido.open_input(in_name)
        self.juno_out = mido.open_output(out_name)
        logger.info(f"Connected to Synth: In='{in_name}', Out='{out_name}'")
        return in_name, out_name

    def connect_launch_control(self) -> Tuple[str, Optional[str]]:
        """Open bidirectional MIDI connection to Novation Launch Control XL."""
        in_name, out_name = self.find_launch_control_ports()
        if not in_name:
            raise ConnectionError(
                f"Could not find Launch Control XL port. Available inputs: {self.get_input_names()}"
            )
        self.lcxl_in = mido.open_input(in_name)
        if out_name:
            try:
                self.lcxl_out = mido.open_output(out_name)
                logger.info(f"Connected to Launch Control XL Out: '{out_name}'")
            except Exception as e:
                logger.warning(f"Could not open Launch Control XL output '{out_name}': {e}")
        logger.info(f"Connected to Launch Control XL In: '{in_name}'")
        return in_name, out_name

    def connect_controller(
        self,
        in_port_name: str,
        out_port_name: Optional[str] = None,
    ) -> None:
        """Connect to an arbitrary MIDI controller input and optional output."""
        self.lcxl_in = mido.open_input(in_port_name)
        if out_port_name:
            try:
                self.lcxl_out = mido.open_output(out_port_name)
            except Exception as e:
                logger.warning(f"Could not open controller output '{out_port_name}': {e}")

    def send_controller_message(self, msg: mido.Message) -> None:
        """Send a MIDI message to the active controller (for feedback / LED / sync)."""
        if self.lcxl_out and not self.lcxl_out.closed:
            self.lcxl_out.send(msg)

    def send_controller_cc(self, control: int, value: int, channel: int = 0) -> None:
        """Send a Control Change message to the active controller."""
        msg = mido.Message("control_change", channel=channel, control=control, value=max(0, min(127, value)))
        self.send_controller_message(msg)

    @property
    def is_juno_connected(self) -> bool:
        """True if bidirectional Juno ports are currently open and valid."""
        return bool(
            self.juno_in is not None
            and not getattr(self.juno_in, "closed", True)
            and self.juno_out is not None
            and not getattr(self.juno_out, "closed", True)
        )

    def close_juno(self) -> None:
        """Close opened Juno ports cleanly."""
        for port in [self.juno_in, self.juno_out]:
            if port and not getattr(port, "closed", True):
                try:
                    port.close()
                except Exception as e:
                    logger.debug(f"Error closing Juno port {port}: {e}")
        self.juno_in = None
        self.juno_out = None

    def reconnect_juno(self) -> bool:
        """Attempt to re-establish connection to Juno synth ports if disconnected."""
        try:
            self.close_juno()
            self.connect_juno()
            return True
        except Exception as e:
            logger.debug(f"reconnect_juno attempt failed: {e}")
            return False

    def send_juno_sysex(self, data: list[int]) -> None:
        """Send a SysEx message to the Roland synth with disconnect recovery."""
        if not self.juno_out or getattr(self.juno_out, "closed", False):
            raise ConnectionError("JUNO-DS output port is not connected.")
        msg = mido.Message("sysex", data=data)
        try:
            self.juno_out.send(msg)
        except Exception as e:
            logger.warning(f"Error sending SysEx to Juno: {e}")
            self.close_juno()
            raise ConnectionError(f"Error sending SysEx to Juno: {e}") from e

    def send_juno_cc(self, control: int, value: int, channel: int = 0) -> None:
        """Send a Control Change message to the Roland synth with disconnect recovery."""
        if not self.juno_out or getattr(self.juno_out, "closed", False):
            raise ConnectionError("JUNO-DS output port is not connected.")
        msg = mido.Message(
            "control_change",
            channel=int(channel) & 0x0F,
            control=int(control) & 0x7F,
            value=max(0, min(127, int(value))),
        )
        try:
            self.juno_out.send(msg)
        except Exception as e:
            logger.warning(f"Error sending CC to Juno: {e}")
            self.close_juno()
            raise ConnectionError(f"Error sending CC to Juno: {e}") from e

    def send_all_notes_off(self, include_reset: bool = True, cut_sound: bool = False) -> int:
        """Panic: All Notes Off (CC 123) on all 16 channels.

        include_reset adds Reset All Controllers (CC 121) first, which also
        releases Hold 1 / Sostenuto so the note-offs are not held. cut_sound
        adds All Sound Off (CC 120), which kills release tails immediately
        (verified on the JUNO-DS; CC 123 alone lets the release ring).

        Returns number of messages actually sent. No-op (with warning) when
        the Juno output port is not connected, so the UI panic button is
        always safe to press.
        """
        if not self.juno_out or getattr(self.juno_out, "closed", False):
            logger.warning("PANIC ignored: JUNO-DS output port is not connected.")
            return 0
        controls = ([121] if include_reset else []) + ([120] if cut_sound else []) + [123]
        sent = 0
        try:
            for channel in range(16):
                for control in controls:
                    self.juno_out.send(
                        mido.Message("control_change", channel=channel, control=control, value=0)
                    )
                    sent += 1
        except Exception as e:
            logger.warning(f"PANIC send failed on ch {channel}: {e}")
        logger.info(f"PANIC: Sent CC {controls} on 16 channels ({sent} msgs)")
        return sent

    def add_note_listener(self, listener: Callable[[mido.Message], None]) -> None:
        """Register a callback for incoming NoteOn/NoteOff events."""
        if listener not in self._note_listeners:
            self._note_listeners.append(listener)

    def remove_note_listener(self, listener: Callable[[mido.Message], None]) -> None:
        """Unregister a note callback."""
        if listener in self._note_listeners:
            self._note_listeners.remove(listener)

    def start_input_worker(self) -> None:
        """Start asynchronous MIDI input demuxer thread."""
        if self._worker_running:
            return
        self._worker_running = True
        self._worker_thread = threading.Thread(
            target=self._input_loop, daemon=True, name="JunoMidiDemuxer"
        )
        self._worker_thread.start()

    def stop_input_worker(self) -> None:
        """Stop asynchronous MIDI input demuxer thread."""
        self._worker_running = False
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=0.2)
        self._worker_thread = None

    def _input_loop(self) -> None:
        """Demuxer loop: routes notes to listeners and queues SysEx replies."""
        while self._worker_running:
            if not self.juno_in or getattr(self.juno_in, "closed", False):
                time.sleep(0.02)
                continue
            has_msg = False
            try:
                for msg in self.juno_in.iter_pending():
                    has_msg = True
                    if msg.type in ("note_on", "note_off"):
                        for listener in list(self._note_listeners):
                            try:
                                listener(msg)
                            except Exception as e:
                                logger.error(f"Error in note listener: {e}")
                    elif msg.type == "sysex":
                        # Only SysEx is ever consumed (RQ1/identity replies); other
                        # traffic is dropped. When full, the oldest reply goes first.
                        if self._sysex_queue.full():
                            try:
                                self._sysex_queue.get_nowait()
                            except queue.Empty:
                                pass
                        self._sysex_queue.put_nowait(msg)
            except Exception as e:
                logger.debug(f"Midi input loop error: {e}")
            if not has_msg:
                time.sleep(0.002)

    def iter_juno_messages(self) -> Generator[mido.Message, None, None]:
        """Iterate over pending messages from the JUNO-DS."""
        if self._worker_running:
            while not self._sysex_queue.empty():
                try:
                    yield self._sysex_queue.get_nowait()
                except queue.Empty:
                    break
            return

        if not self.juno_in:
            return
        yield from self.juno_in.iter_pending()

    def iter_lcxl_messages(self) -> Generator[mido.Message, None, None]:
        """Iterate over pending messages from the Launch Control XL."""
        if not self.lcxl_in:
            return
        yield from self.lcxl_in.iter_pending()

    def close(self) -> None:
        """Close all opened MIDI ports cleanly."""
        self.stop_input_worker()
        for port in [self.juno_in, self.juno_out, self.lcxl_in, self.lcxl_out]:
            if port and not port.closed:
                try:
                    port.close()
                except Exception as e:
                    logger.warning(f"Error closing port {port}: {e}")
        self.juno_in = None
        self.juno_out = None
        self.lcxl_in = None
        self.lcxl_out = None

    def __enter__(self) -> MidiDeviceManager:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
