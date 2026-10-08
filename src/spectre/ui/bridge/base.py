"""Base mixin providing common typed accessors for all SpectreBridge mixins."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ...core.patch_state import PatchState
    from ...core.protocol import JunoClient
    from ...vector.engine import VectorEngine


class BridgeBaseMixin:
    """Base mixin with core accessors shared by all bridge mixin domains."""

    engine: Optional[VectorEngine]
    patch_state: PatchState

    @property
    def juno(self) -> Optional[JunoClient]:
        """Direct accessor for the connected JunoClient protocol instance."""
        engine = getattr(self, "engine", None)
        return getattr(engine, "juno", None) if engine is not None else None
