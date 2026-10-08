"""MIDI port discovery and hardware transport layer.

Handles device matching for Roland JUNO-DS / XPS-30 and Novation Launch Control XL,
providing safe ALSA port opening, message sending, and non-blocking polling.
"""

from __future__ import annotations

import logging
from typing import Generator, Optional, Tuple

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

    def send_all_notes_off(self, include_reset: bool = True) -> int:
        """Panic: All Notes Off (CC 123) + Reset All Controllers (CC 121) on all 16 channels.

        Returns number of messages actually sent. No-op (with warning) when
        the Juno output port is not connected, so the UI panic button is
        always safe to press.
        """
        if not self.juno_out or getattr(self.juno_out, "closed", False):
            logger.warning("PANIC ignored: JUNO-DS output port is not connected.")
            return 0
        sent = 0
        for channel in range(16):
            try:
                self.juno_out.send(
                    mido.Message("control_change", channel=channel, control=123, value=0)
                )
                sent += 1
                if include_reset:
                    self.juno_out.send(
                        mido.Message("control_change", channel=channel, control=121, value=0)
                    )
                    sent += 1
            except Exception as e:
                logger.warning(f"PANIC send failed on ch {channel}: {e}")
                break
        logger.info(f"PANIC: Sent All Notes Off (+Reset) on 16 channels ({sent} msgs)")
        return sent

    def iter_juno_messages(self) -> Generator[mido.Message, None, None]:
        """Iterate over pending messages from the JUNO-DS."""
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
