"""High-level Roland JUNO-DS / XPS-30 client protocol.

Provides typed, safe methods to query and control synth parameters
targeting the Temporary RAM Edit Buffers exclusively. Address constants
and SysEx helpers live in core.sysex.
"""

from __future__ import annotations

from .protocol_base import BaseProtocolMixin, SoundMode
from .protocol_flash import FlashProtocolMixin
from .protocol_patch import PatchProtocolMixin
from .protocol_performance import PerformanceProtocolMixin


class JunoClient(
    BaseProtocolMixin,
    PerformanceProtocolMixin,
    PatchProtocolMixin,
    FlashProtocolMixin,
):
    """Client for bidirectional communication with Roland JUNO-DS / XPS-30.

    Inherits from domain mixins for transport, performance mode, patch editing,
    and user flash slot management.
    """


__all__ = ["JunoClient", "SoundMode"]
