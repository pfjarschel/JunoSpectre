"""Base mixin providing common typed accessors for all SpectreBridge mixins."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ...core.patch_state import PatchState
    from ...core.protocol import JunoClient
    from ...vector.engine import VectorEngine


class BridgeBaseMixin:
    """Base mixin with core accessors shared by all bridge mixin domains."""

    vector: VectorEngine
    patch_state: PatchState

    @property
    def juno(self) -> Optional[JunoClient]:
        """The connected synth, or None when offline."""
        return getattr(self, "_juno", None)

    @juno.setter
    def juno(self, client: Optional[JunoClient]) -> None:
        """Attach (or drop) the synth; the vector engine sends tone levels through it."""
        self._juno = client
        self.vector.juno = client
        if client is not None and getattr(client, "on_perf_part_write", None) is None:
            client.on_perf_part_write = self._on_perf_part_write
