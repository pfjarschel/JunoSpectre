"""Arpeggiator page: the JUNO-DS arp settings and the app's MIDI clock out.

The arp settings are global on the synth and can't be saved there, so the
app saves them in patch and performance files ("arp" in the spectre
extras) and pushes them on load. They are read back from the synth on
connect and whenever the page opens (the panel's [ARPEGGIO] button changes
them behind the app's back). Until they were read or set once, nothing is
saved, so a file never stores made-up defaults.

The part the arp plays (PERFORM) can only be set on the Juno's panel.
"""

from __future__ import annotations

import logging
import threading

import mido
from PyQt6.QtCore import pyqtProperty, pyqtSignal, pyqtSlot

from ...core.arpeggio import (
    DURATIONS,
    FIELD_LABELS,
    GRIDS,
    MOTIFS,
    SETUP_OFFSETS,
    ArpSettings,
    MidiClockOut,
    field_from_label,
    field_label,
)
from .base import BridgeBaseMixin
from .hardware import save_hardware_settings

logger = logging.getLogger(__name__)

ARP_VIEW = "ARPEGGIO"
_CLOCK = mido.Message("clock")
_INT_FIELDS = ("style", "motif", "grid", "duration", "octave", "accent", "velocity", "step")


class ArpBridgeMixin(BridgeBaseMixin):
    arpChanged = pyqtSignal()
    _arpRead = pyqtSignal(object)      # reader thread -> UI thread

    def _init_arp(self) -> None:
        self._arp = ArpSettings()
        self._arp_known = False
        self._arp_reading = False
        self._arpRead.connect(self._on_arp_read)
        self._clock_out = MidiClockOut(self._send_clock, bpm=self.bpm)
        self._clock_out.set_enabled(bool(self._hw_settings.get("midi_clock_out", True)))
        self.bpmChanged.connect(self._clock_out.set_bpm)
        self.activeViewChanged.connect(self._arp_on_view)
        self.jobFinished.connect(self._arp_on_job)
        self.refreshArp()

    def _send_clock(self) -> bool:
        mgr = self._midi_mgr or getattr(self.juno, "midi", None)
        out = getattr(mgr, "juno_out", None)
        if out is None or getattr(out, "closed", True):
            return False
        out.send(_CLOCK)
        return True

    # -- reading -------------------------------------------------------------

    @pyqtSlot()
    def refreshArp(self) -> None:
        """Re-read the arp from the synth (background; arpChanged when done)."""
        juno = self.juno
        if juno is None or not getattr(juno, "is_connected", False) or self._arp_reading:
            return
        self._arp_reading = True

        def run():
            try:
                settings = juno.read_arp()
            except Exception as e:
                logger.debug(f"arp read failed: {e}")
                settings = None
            try:
                self._arpRead.emit(settings)
            except RuntimeError:
                pass  # bridge gone

        threading.Thread(target=run, name="arp-read", daemon=True).start()

    def _on_arp_read(self, settings) -> None:
        self._arp_reading = False
        if isinstance(settings, ArpSettings):
            self._arp = settings
            self._arp_known = True
            self.arpChanged.emit()

    def _arp_on_view(self, view: str) -> None:
        if view == ARP_VIEW:
            self.refreshArp()

    def _arp_on_job(self, name: str, result) -> None:
        if name == "connect" and isinstance(result, dict) and result.get("ok"):
            self.refreshArp()

    # -- QML -------------------------------------------------------------------

    @pyqtProperty("QVariantMap", notify=arpChanged)
    def arp(self) -> dict:
        a = self._arp
        out = a.to_dict()
        out.update({f + "Text": field_label(a, f) for f in FIELD_LABELS})
        out["known"] = self._arp_known
        return out

    @pyqtProperty("QVariantMap", constant=True)
    def arpLists(self) -> dict:
        return {"styles": FIELD_LABELS["style"], "motifs": MOTIFS, "grids": GRIDS, "durations": DURATIONS}

    @pyqtProperty(bool, notify=arpChanged)
    def midiClockOut(self) -> bool:
        return self._clock_out.enabled

    @pyqtSlot(bool)
    def setMidiClockOut(self, on: bool) -> None:
        self._clock_out.set_enabled(bool(on))
        self._hw_settings["midi_clock_out"] = bool(on)
        save_hardware_settings(self._hw_settings)
        self.arpChanged.emit()

    @pyqtSlot(str, int)
    def setArpField(self, field: str, value: int) -> None:
        """Set one field: switch/hold (0/1) or an int field (see ArpSettings)."""
        if field in ("switch", "hold"):
            new = bool(value)
        elif field in _INT_FIELDS:
            new = int(value)
        else:
            return
        settings = ArpSettings(**{**self._arp.to_dict(), field: new}).clamped()
        if getattr(settings, field) == getattr(self._arp, field) and self._arp_known:
            return
        self._arp = settings
        self._arp_known = True
        juno = self.juno
        if juno is not None:
            try:
                with juno.coalesced_writes():
                    juno.write_arp_field(settings, field)
            except Exception as e:
                logger.debug(f"arp write {field} failed: {e}")
        self.arpChanged.emit()

    @pyqtSlot()
    def toggleArp(self) -> None:
        self.setArpField("switch", int(not self._arp.switch))

    @pyqtSlot()
    def toggleArpHold(self) -> None:
        self.setArpField("hold", int(not self._arp.hold))

    # -- files -----------------------------------------------------------------

    def _arp_extras(self) -> dict:
        """{"arp": settings} for a file being saved; {} until they are known."""
        return {"arp": self._arp.to_dict()} if self._arp_known else {}

    def _apply_arp_extras(self, spectre) -> None:
        """Load a file's arp settings (if it has any) and push them."""
        settings = ArpSettings.from_dict((spectre or {}).get("arp")) if isinstance(spectre, dict) else None
        if settings is None:
            return
        self._arp = settings
        self._arp_known = True
        juno = self.juno
        if juno is not None:
            try:
                juno.write_arp(settings)
            except Exception as e:
                logger.debug(f"arp push failed: {e}")
        self.arpChanged.emit()

    def _arp_resync_clock(self) -> None:
        """Sequencer started: restart the clock grid so the beats line up."""
        clock = self._clock_out
        if clock is not None:
            clock.resync()


# Knob targets (bridge/context_knobs.py STEPPED): "_arp_text_<field>" reads the
# value label, "_set_arp_text_<field>" sets it from one.
def _label_accessors(field: str):
    def get(self) -> str:
        return field_label(self._arp, field)

    def set_(self, label: str) -> None:
        value = field_from_label(field, str(label))
        if value is not None:
            self.setArpField(field, value)

    return property(get), set_


for _field in FIELD_LABELS:
    _get, _set = _label_accessors(_field)
    setattr(ArpBridgeMixin, f"_arp_text_{_field}", _get)
    setattr(ArpBridgeMixin, f"_set_arp_text_{_field}", _set)

assert set(FIELD_LABELS) <= set(SETUP_OFFSETS)
