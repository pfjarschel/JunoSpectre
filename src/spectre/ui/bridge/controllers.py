"""External MIDI controllers: ports, learn, bindings -> app targets.

Controller input ports are opened with a mido callback (rtmidi thread).
Events queue up and are applied on the UI thread at most every
DRAIN_MS: a knob's run of values collapses to the latest one, while
buttons (momentary/toggle bindings) keep every press and release.

A binding to a catalog target acts like moving that control in the UI:
when macros drive the target, the controller sets the base they add to.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import deque
from pathlib import Path
from typing import Optional

import mido
from PyQt6.QtCore import QTimer, pyqtProperty, pyqtSignal, pyqtSlot

from ...control import lcxl3
from ...control.mapping import BEHAVIORS, TAKEOVERS, Binding, Resolver, pick_bindings
from ...core.arpeggio import FIELD_LABELS as ARP_FIELD_LABELS
from ...core.macro_targets import filter_macro_targets, get_macro_categories
from ...core.midi import port_key
from ...sequencer.models import NUM_TRACKS, TRACK_BANK_SIZE
from .base import BridgeBaseMixin
from .hardware import save_hardware_settings

logger = logging.getLogger(__name__)

DRAIN_MS = 15
FEEDBACK_MS = 100
# LCXL3 touch events: channel 15 (0-based 14), the control's CC, 127 on touch / 0 on release
TOUCH_CH = 14
# Touchscreen hint: kept this long after the touch ends (twice after a move without touch)
TOUCH_LINGER_MS = 700
# Alt layer button: released sooner than this, with nothing used meanwhile, is a tap (latch)
ALT_TAP_S = 0.35
# A knob that moved this recently is the source of its value: no feedback
FEEDBACK_HOLD_S = 0.3
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
BUNDLED_PRESET_DIR = _PROJECT_ROOT / "config" / "controller_presets"


def user_preset_dir() -> Path:
    from ...librarian.repository import data_root

    return data_root() / "controller_presets"


def _action(key: str, title: str) -> dict:
    return {"key": f"action.{key}", "title": title, "category": "ACTION",
            "min": 0.0, "max": 1.0, "span": 1.0}


# Button actions: run on press. "toggle" ones flip app state (mute, play...).
ACTIONS: list[dict] = (
    [_action("seq.toggle_play", "Sequencer Play/Stop"), _action("seq.play", "Sequencer Play"),
     _action("seq.stop", "Sequencer Stop"), _action("seq.live_record", "Sequencer Record On/Off (track or lane)")]
    + [_action(f"seq.scene.{n}", f"Launch Scene {n}") for n in range(1, 9)]
    + [_action(f"seq.stop_track.{n}", f"Stop Track {n}") for n in range(1, NUM_TRACKS + 1)]
    + [_action("seq.track_bank", "Track Bank 1-8 / 9-16")]
    + [_action(f"seq.clip.{n}", f"Launch Clip {n} of Selected Track") for n in range(1, 9)]
    + [_action("seq.stop_selected", "Stop Selected Track"), _action("seq.stop_all", "Stop All Clips")]
    + [_action("none", "Nothing (blocks wider scopes)"),
       _action("layer.alt", "Alt Layer (tap: latch, hold: while held)"),
       _action("scene.next", "Next Scene"), _action("scene.prev", "Previous Scene"),
       _action("seq.scene_launch", "Launch Selected Scene"), _action("seq.scene_stop", "Stop Selected Scene")]
    + [_action("motion.toggle_play", "Motion Play/Stop"), _action("motion.toggle_record", "Motion Record On/Off")]
    + [_action(f"tone.mute.{n}", f"Tone {n} Mute On/Off") for n in range(1, 5)]
    + [_action(f"tone.select.{n}", f"Select Tone {n}") for n in range(1, 5)]
    + [_action(f"part.mute.{n}", f"Part {n} Mute On/Off") for n in range(1, 17)]
    + [_action(f"part.solo.{n}", f"Part {n} Solo On/Off") for n in range(1, 17)]
    + [_action(f"part.edit.{n}", f"Edit Part {n}") for n in range(1, 17)]
    + [_action(f"mfx.edit.{n}", f"Edit MFX {n}") for n in range(1, 4)]
    + [_action("mfx.next", "Next MFX"), _action("mfx.prev", "Previous MFX"),
       _action("edit_target.open", "Part / MFX Picker")]
    + [_action("playlist.next", "Setlist Next"), _action("playlist.prev", "Setlist Previous"),
       _action("panic", "Panic (All Notes Off)"),
       _action("view.next", "Next Page"), _action("view.prev", "Previous Page"),
       _action("select.next", "Next Part / Track"), _action("select.prev", "Previous Part / Track"),
       _action("bank.next", "Part / Track Bank 9-16"), _action("bank.prev", "Part / Track Bank 1-8"),
       _action("arp.toggle", "Arpeggio On/Off"), _action("arp.hold", "Arp Hold On/Off")]
)
_PAGE_TITLES = {"JUNO PCM": "PCM Editor", "PERFORMANCE": "Perf Mixer", "LIVE": "Live Mode",
                "SETLIST": "Set List", "MACROS": "Macro Deck", "MSEG ENVELOPES": "Envelopes",
                "MFX": "MFX Studio", "ARPEGGIO": "Arpeggiator"}

# Learn scopes offered in the UI
CONTEXT_TITLES = {"": "EVERYWHERE", "MODE:PATCH": "PATCH MODE", "MODE:PERFORM": "PERFORM MODE"}
_TOKEN_TITLES = {"LAYER:MIXER": "MIXER", "LAYER:CONTROL": "CONTROL", "ALT:ON": "ALT LAYER",
                 "BANK:1": "PARTS 1-8", "BANK:2": "PARTS 9-16"}


def context_title(context: str) -> str:
    """"LAYER:MIXER&MODE:PERFORM&BANK:2" -> "MIXER · PERFORM MODE · PARTS 9-16"."""
    if not context:
        return CONTEXT_TITLES[""]
    return " · ".join(CONTEXT_TITLES.get(t, _TOKEN_TITLES.get(t, t)) for t in context.split("&"))


# App pages a binding can belong to (activeView keys)
# (in launcher order, so Next/Previous Page steps through them as the Screens overlay shows them)
CONTEXT_PAGES = ["JUNO PCM", "VECTOR", "WAVETABLE", "VA", "MOD MATRIX", "STEP LFO", "MSEG ENVELOPES",
                 "ROUTING", "MFX", "MASTER FX", "MACROS", "ARPEGGIO", "PERFORMANCE", "SEQUENCER", "LIVE",
                 "SETLIST"]
# Page shortcut LEDs: the UI's page category accents (Theme.qml), in LED units 0..127
_CAT_RGB = {"synth": (28, 94, 124), "modfx": (64, 70, 124), "perform": (104, 70, 125), "system": (113, 116, 120)}
_VIEW_CAT = {**{v: "synth" for v in ("JUNO PCM", "VECTOR", "WAVETABLE", "VA")},
             **{v: "modfx" for v in ("MOD MATRIX", "STEP LFO", "MSEG ENVELOPES", "ROUTING", "MFX", "MASTER FX")},
             **{v: "perform" for v in ("MACROS", "ARPEGGIO", "PERFORMANCE", "SEQUENCER", "LIVE", "SETLIST")}}


def _view_rgb(view: str) -> tuple:
    return _CAT_RGB[_VIEW_CAT.get(view, "system")]


# The 8 context knobs of each page (on-screen strip; controllers bind "context.N").
# "" = unused. Keys are macro catalog targets, "macro.N", or the editor-following
# and stepped targets below.
_TONE_SEL = "tone.sel."
CONTEXT_KNOBS: dict[str, list[str]] = {
    "JUNO PCM": [_TONE_SEL + p for p in ("tvf_cutoff", "tvf_resonance", "tvf_env_depth", "tva_level",
                                         "tva_pan", "pitch_coarse", "pitch_fine", "lfo1_rate")],
    "VECTOR": ["vector.x", "vector.y", "vector.orbit_x", "vector.orbit_y", "vector.speed",
               "step.automator", "step.curve", "vector.bpm"],
    "WAVETABLE": ["vector.w", "vector.speed", "step.sweep", "step.curve"]
                 + [f"tone.{i}.tva_level" for i in range(1, 5)],
    "VA": [f"tone.{i}.tva_level" for i in range(1, 5)] + [f"tone.{i}.pitch_fine" for i in range(1, 5)],
    "MOD MATRIX": [f"common.matrix{c}_sens{d}" for d in (1, 2) for c in range(1, 5)],
    "STEP LFO": [_TONE_SEL + f"lfo{l}_{p}" for l in (1, 2) for p in ("rate", "pitch_depth", "tvf_depth", "tva_depth")],
    "MSEG ENVELOPES": [_TONE_SEL + p for p in ("pitch_env_depth", "pitch_env_attack", "pitch_env_decay",
                                               "pitch_env_release", "tvf_env_depth", "tvf_cutoff",
                                               "tvf_resonance", "tva_level")],
    "MFX": [f"mfx.p.{n}" for n in range(1, 9)],
    "ROUTING": [f"tone.{i}.chorus_send" for i in range(1, 5)] + [f"tone.{i}.reverb_send" for i in range(1, 5)],
    "MASTER FX": ["effects.chorus_level", "effects.chorus_rate", "effects.chorus_depth", "effects.chorus_feedback",
                  "effects.reverb_level", "effects.reverb_time", "effects.reverb_damp", "effects.reverb_predelay"],
    "LIVE": [f"macro.{n}" for n in range(1, 9)],
    # SEQUENCER: bank 1 shown here; it follows the track bank (_context_knob_targets)
    "SEQUENCER": [f"seq.swing.{n}" for n in range(1, 9)],
    "ARPEGGIO": [f"arp.{f}" for f in ("style", "motif", "grid", "duration", "octave", "accent",
                                      "velocity", "step")],
    "PERFORMANCE": [f"part.level@{n}" for n in range(1, 9)],
    "MACROS": [f"macro.{n}" for n in range(1, 9)],
}

# Stepped (enum) targets: key -> (title, values, bridge property, bridge setter)
STEPPED = {
    "step.automator": ("Automator", ["none", "circle", "lissajous", "spiral", "chaos"], "automator", "setAutomator"),
    "step.curve": ("Crossfade Curve", ["linear", "equal_power", "normalized"], "curve", "setCurve"),
    "step.sweep": ("Sweep Mode", ["manual", "sine", "triangle", "ramp", "random_step", "chaos"],
                   "wavetableSweepMode", "setWavetableSweepMode"),
}
# Arp knobs step through the synth's own value names (bridge/arpeggio.py)
STEPPED.update({f"arp.{f}": ("Arp " + ("Oct Range" if f == "octave" else f.title()), labels,
                             f"_arp_text_{f}", f"_set_arp_text_{f}")
                for f, labels in ARP_FIELD_LABELS.items()})

# Detune targets the edited-tone fine tune turns into (_ctl_resolve):
# key -> (title, min, max, bridge property, setter)
DETUNE = {
    "detune.master": ("Master Fine Tune", -50, 50, "masterFine", "sculptPitchFine"),
    "detune.auto": ("Auto Detune", 0, 50, "autoDetuneCents", "setAutoDetuneCents"),
}

ACTIONS += [_action(f"view.goto.{v}", "Go to " + _PAGE_TITLES.get(v, v.title()))
            for v in CONTEXT_PAGES]
# Clip launchers: one per track and clip slot (their own CLIP category in the picker)
CLIP_ACTIONS: list[dict] = [{**_action(f"seq.launch.{t}.{c}", f"Launch Track {t} Clip {c}"), "category": "CLIP"}
                            for t in range(1, NUM_TRACKS + 1) for c in range(1, 9)]
_ACTION_TITLES = {a["key"]: a["title"] for a in ACTIONS + CLIP_ACTIONS}



def default_controller_port(key: str) -> bool:
    """Inputs listened to unless switched off: not the synth's, loopback, DAW or our own."""
    return not (any(k in key for k in ("JUNO", "XPS", "Midi Through", "DAW"))
                or key.startswith(("RtMidiIn Client", "RtMidiOut Client")))


class ControllersBridgeMixin(BridgeBaseMixin):
    controllersChanged = pyqtSignal()
    contextKnobsChanged = pyqtSignal()
    controlActivityChanged = pyqtSignal()
    touchedControlChanged = pyqtSignal()
    _ctlPending = pyqtSignal()   # rtmidi thread -> UI thread

    def _init_controllers(self) -> None:
        cfg = dict(self._hw_settings.get("controllers", {}) or {})
        self._ctl_enabled: dict[str, bool] = {str(k): bool(v) for k, v in dict(cfg.get("enabled", {})).items()}
        self._ctl_bindings: list[Binding] = [b for b in map(Binding.from_dict, cfg.get("bindings", [])) if b]
        self._ctl_resolver = Resolver()
        # _ctl_pick memo: bindings version (bumped on controllersChanged) + context
        self._ctl_version = 0
        self._ctl_pick_key: tuple = ()
        self._ctl_pick_list: list = []
        self._ctl_pick_memo: dict = {}
        self.controllersChanged.connect(self._ctl_bump_version)
        self._ctl_open: dict[str, object] = {}      # port key -> mido input
        self._ctl_events: deque = deque(maxlen=4096)
        self._ctl_lock = threading.Lock()
        self._ctl_scheduled = False
        self._ctl_learn_target = ""
        self._ctl_learn_context = ""
        self._ctl_activity = ""
        # Surface layer ("MIXER" while the LCXL3 is in DAW Mixer mode); the part
        # bank is the app's one (seqTrackBank)
        self._ctl_layer = ""
        # Alt layer (Novation button): on while held or latched by a tap
        self._alt_held = self._alt_latched = self._alt_used = self._alt_was = self._alt_shown = False
        self._alt_t0 = 0.0
        self._ctl_scene = 0                         # scene the alt layer's Play/Record act on
        self._ctl_touched: set = set()              # (port, CC) of surface controls being touched
        # Touchscreen hint for the control under the hand: highlighted where it
        # is on screen, a toast otherwise (QML). Hidden a moment after the last
        # move, or after the touch ends.
        self._touch_key = ""
        self._touch_info: dict = {}
        self._touch_timer = QTimer(self)
        self._touch_timer.setSingleShot(True)
        self._touch_timer.timeout.connect(self._touch_hide)
        self._ctl_names: dict[str, dict] = {}       # port key -> {"cc:13": "Knob A1"}
        # Device setups from presets: [{match, listen, feedback, on_connect, on_quit}]
        self._ctl_devices: list[dict] = [dict(d) for d in cfg.get("devices", []) if isinstance(d, dict)]
        self._ctl_feedback: dict[str, bool] = {str(k): bool(v) for k, v in dict(cfg.get("feedback", {})).items()}
        self._ctl_out: dict[str, object] = {}       # port key -> mido output
        self._ctl_connected_devices: set = set()    # (device index, client) set up
        self._ctl_fb_sent: dict = {}                # control -> raw last sent back
        self._ctl_moved: dict = {}                  # control -> (raw, time) last received
        self._ctl_fb_timer = QTimer(self)
        self._ctl_fb_timer.setInterval(FEEDBACK_MS)
        self._ctl_fb_timer.timeout.connect(self._ctl_feedback_tick)
        # On-screen context strip: values change from many places (editors,
        # macros, patch loads), so it is refreshed on a light timer
        self._ctx_knobs: list = []
        self._ctx_timer = QTimer(self)
        self._ctx_timer.setInterval(FEEDBACK_MS)
        self._ctx_timer.timeout.connect(self._ctx_refresh)
        self._ctx_timer.start()
        self.activeViewChanged.connect(self._ctx_refresh)
        self._ctlPending.connect(self._ctl_schedule_drain)
        # Which bindings are active depends on the page and the sound mode
        self.activeViewChanged.connect(self._ctl_context_changed)
        self.patchInfoChanged.connect(self._ctl_context_changed)
        self.seqActiveTrackChanged.connect(self._ctl_context_changed)
        self._ctl_load_names()

    def _ctl_save(self) -> None:
        self._hw_settings["controllers"] = {
            "enabled": dict(self._ctl_enabled),
            "feedback": dict(self._ctl_feedback),
            "devices": list(self._ctl_devices),
            "bindings": [b.to_dict() for b in self._ctl_bindings],
        }
        save_hardware_settings(self._hw_settings)

    # -- ports ---------------------------------------------------------------

    def _ctl_device(self, key: str) -> tuple[int, dict] | tuple[None, None]:
        for i, d in enumerate(self._ctl_devices):
            if any(m and m in key for m in d.get("match", [])):
                return i, d
        return None, None

    def _ctl_port_enabled(self, key: str) -> bool:
        if key in self._ctl_enabled:
            return self._ctl_enabled[key]
        _, dev = self._ctl_device(key)
        if dev and any(h in key for h in dev.get("listen", [])):
            return True
        return default_controller_port(key)

    def _ctl_feedback_on(self, key: str) -> bool:
        if key in self._ctl_feedback:
            return self._ctl_feedback[key]
        _, dev = self._ctl_device(key)
        return bool(dev and dev.get("feedback"))

    def _ctl_output(self, key: str):
        """Output port with the same name as controller input `key` (opened lazily)."""
        out = self._ctl_out.get(key)
        if out is not None and not getattr(out, "closed", False):
            return out
        name = next((n for n in self._hw_outputs if port_key(n) == key), None)
        if name is None:
            return None
        try:
            out = mido.open_output(name)
        except Exception as e:
            logger.warning(f"Could not open controller output {key}: {e}")
            return None
        self._ctl_out[key] = out
        return out

    def _ctl_send(self, key: str, msg) -> None:
        out = self._ctl_output(key)
        if out is None:
            return
        try:
            out.send(msg)
        except Exception as e:
            logger.debug(f"controller send to {key} failed: {e}")
            self._ctl_out.pop(key, None)

    def _ctl_device_messages(self, client: str, steps: list) -> None:
        """Send a device's setup steps [{port: hint, send: [hex, ...]}] to its ports."""
        outs = [port_key(n) for n in self._hw_outputs if port_key(n).split(":")[0] == client]
        for step in steps or []:
            hint = str(step.get("port", ""))
            key = next((k for k in outs if hint in k), None)
            if key is None:
                logger.warning(f"{client}: no output port matching '{hint}'")
                continue
            for hx in step.get("send", []):
                try:
                    self._ctl_send(key, mido.Message.from_hex(str(hx)))
                except ValueError as e:
                    logger.warning(f"bad setup message {hx!r}: {e}")

    def _ctl_setup_devices(self) -> None:
        """Run on_connect for devices that just appeared; forget ones that left."""
        live = set()
        for k in self._ctl_open:
            i, dev = self._ctl_device(k)
            if dev is not None:
                live.add((i, k.split(":")[0]))
        for i, client in sorted(live - self._ctl_connected_devices):
            logger.info(f"Controller setup: {client}")
            for k in [k for k in self.__dict__.get("_surface_state", {}) if k.split(":")[0] == client]:
                del self._surface_state[k]
            self._ctl_layer = ""                      # on_connect starts the device fresh
            self._alt_held = self._alt_latched = self._alt_shown = False
            self._ctl_device_messages(client, self._ctl_devices[i].get("on_connect", []))
        self._ctl_connected_devices = live

    def _ctl_sync_ports(self, ins: list) -> None:
        """Open enabled controller inputs, close vanished/disabled ones."""
        synth = self.synthPort
        wanted = {}
        for name in ins:
            k = port_key(name)
            if k != synth and self._ctl_port_enabled(k) and not k.startswith(("RtMidiIn Client", "RtMidiOut Client")):
                wanted.setdefault(k, name)
        changed = False
        for k in [k for k in self._ctl_open if k not in wanted]:
            port = self._ctl_open.pop(k)
            try:
                port.close()
            except Exception:
                pass
            logger.info(f"Controller port closed: {k}")
            changed = True
        for k, name in wanted.items():
            if k in self._ctl_open:
                continue
            try:
                self._ctl_open[k] = mido.open_input(name, callback=lambda m, k=k: self._ctl_on_message(k, m))
                logger.info(f"Controller port open: {k}")
                changed = True
            except Exception as e:
                logger.warning(f"Could not open controller port {k}: {e}")
        for k in [k for k in self._ctl_out if k not in {port_key(n) for n in self._hw_outputs}]:
            self._ctl_out.pop(k, None)
        if changed:
            self._ctl_setup_devices()
            self._ctl_fb_sent.clear()
            self.controllersChanged.emit()
        self._ctl_update_feedback_timer()

    def close_controllers(self) -> None:
        """App exit: run on_quit for set-up devices, then close every port."""
        for i, client in sorted(self._ctl_connected_devices):
            if i < len(self._ctl_devices):
                self._ctl_device_messages(client, self._ctl_devices[i].get("on_quit", []))
        self._ctl_connected_devices = set()
        self._ctl_fb_timer.stop()
        for port in list(self._ctl_out.values()):
            try:
                port.close()
            except Exception:
                pass
        self._ctl_out.clear()
        for port in self._ctl_open.values():
            try:
                port.close()
            except Exception:
                pass
        self._ctl_open.clear()

    def _ctl_on_message(self, port: str, msg) -> None:
        """rtmidi thread: queue CC / note events."""
        if msg.type == "control_change":
            ev = (port, msg.channel, "cc", msg.control, msg.value)
        elif msg.type == "note_on":
            ev = (port, msg.channel, "note", msg.note, msg.velocity)
        elif msg.type == "note_off":
            ev = (port, msg.channel, "note", msg.note, 0)
        else:
            return
        with self._ctl_lock:
            self._ctl_events.append(ev)
            if self._ctl_scheduled:
                return
            self._ctl_scheduled = True
        try:
            self._ctlPending.emit()
        except RuntimeError:
            pass

    @pyqtSlot()
    def _ctl_schedule_drain(self) -> None:
        QTimer.singleShot(DRAIN_MS, self._ctl_drain)

    def _ctl_drain(self) -> None:
        with self._ctl_lock:
            events = list(self._ctl_events)
            self._ctl_events.clear()
            self._ctl_scheduled = False
        if not events:
            return
        # Knobs: only the latest value per control. Buttons and touches: every edge.
        latest: dict = {}
        ordered = []
        for ev in events:
            ctl = ev[:4]
            if ctl[1] == TOUCH_CH or self._ctl_is_button(ctl):
                ordered.append(ev)
            else:
                if ctl not in latest:
                    ordered.append(ctl)
                latest[ctl] = ev
        with self._macroWrites():
            for item in ordered:
                ev = latest[item] if len(item) == 4 else item
                self._ctl_handle(ev)
        # Moved controls show their new value on the device screen right away
        self._surface_tick({ev[:4] if len(ev) == 5 else ev for ev in ordered})

    def _ctl_is_button(self, ctl: tuple) -> bool:
        return any(b.behavior != "absolute" or b.target.startswith("action.") for b in self._ctl_pick(*ctl))

    def _ctl_mode(self) -> str:
        return "PERFORM" if self._in_perform() else "PATCH"

    def _ctl_state(self) -> dict:
        """What binding contexts are matched against right now."""
        return {"PAGE": str(getattr(self, "_active_view", "")), "MODE": self._ctl_mode(),
                "LAYER": self._ctl_layer or "CONTROL", "ALT": "ON" if self._alt_on() else "",
                "BANK": str(self.seqTrackBank + 1)}

    def _alt_on(self) -> bool:
        return self._alt_held or self._alt_latched

    def _ctl_alt_edge(self, down: bool) -> None:
        """Alt layer button. It turns the layer on at press; on release a tap
        (short, nothing used meanwhile) latches it on or off, anything else
        puts it back as it was before the press."""
        now = time.monotonic()
        if down:
            if self._alt_held:
                return
            self._alt_held, self._alt_used, self._alt_t0 = True, False, now
            self._alt_was = self._alt_latched
        else:
            if not self._alt_held:
                return
            self._alt_held = False
            tap = not self._alt_used and now - self._alt_t0 < ALT_TAP_S
            self._alt_latched = (not self._alt_was) if tap else self._alt_was
        on = self._alt_on()
        if on != self._alt_shown:
            self._alt_shown = on
            self._ctl_fb_sent.clear()       # the layer's controls send their positions
            self.controllersChanged.emit()

    def _ctl_pick(self, port, ch, kind, num) -> tuple:
        """The bindings a control drives now, memoized per bindings + context.

        The feedback and surface ticks ask for every bound control 10 times
        a second; each pick scans all bindings, which kept the Pi's UI
        thread ~25% busy with ~200 bindings. Every binding change emits
        controllersChanged (bumps the version); a new list resets it too.
        """
        state = self._ctl_state()
        key = (self._ctl_version, *state.values())
        if key != self._ctl_pick_key or self._ctl_pick_list is not self._ctl_bindings:
            self._ctl_pick_key, self._ctl_pick_list, self._ctl_pick_memo = key, self._ctl_bindings, {}
        ctl = (port, ch, kind, num)
        hits = self._ctl_pick_memo.get(ctl)
        if hits is None:
            hits = self._ctl_pick_memo[ctl] = tuple(
                pick_bindings(self._ctl_bindings, port, ch, kind, num, state))
        return hits

    def _ctl_bump_version(self, *_args) -> None:
        self._ctl_version += 1

    # -- events --------------------------------------------------------------

    def _ctl_handle(self, ev: tuple) -> None:
        port, ch, kind, num, raw = ev
        if ch in (6, TOUCH_CH) and any(p == port for p, _ in self._surfaces()):
            if ch == TOUCH_CH:
                if kind == "cc":
                    self._ctl_touch(port, num, raw >= 64)
            # LCXL3 feature channel: mode reports, not controls. DAW Mixer = mixer layer.
            elif kind == "cc" and num == 30:
                self._ctl_set_layer("MIXER" if raw == 1 else "")
            return
        self._ctl_moved[(port, ch, kind, num)] = (raw, time.monotonic())
        if self._ctl_learn_target:
            if raw == 0:
                return        # a release or a control at its minimum: wait for a real move
            self._ctl_finish_learn(port, ch, kind, num, raw)
            return
        label = self._ctl_control_label(port, ch, kind, num)
        hits = self._ctl_pick(port, ch, kind, num)
        if self._alt_held and not any(b.target == "action.layer.alt" for b in hits):
            self._alt_used = True           # used while held: the layer is momentary
        if not hits:
            self._ctl_set_activity(f"{label} = {raw}  (not assigned)")
            return
        for b in hits:
            if b.target == "action.layer.alt":
                st = self._ctl_resolver.state(b)
                down = raw >= 64
                if down != st.pressed:
                    st.pressed = down
                    self._ctl_alt_edge(down)
                continue
            if b.target.startswith("action."):
                st = self._ctl_resolver.state(b)
                down = raw >= 64
                # Latching buttons send one message per press (127, then 0)
                fire = (down != st.pressed) if b.behavior == "latch" else (down and not st.pressed)
                if fire:
                    self._ctl_run_action(b.target[7:])
                    self._ctl_set_activity(f"{label} → {self._ctl_target_title(b.target)}")
                st.pressed = down
                continue
            eff = self._ctl_resolve(b.target)
            if not eff:
                self._ctl_set_activity(f"{label} = {raw} → {self._ctl_target_title(b.target)}  (unused on this page)")
                continue
            if self._auto_owns(eff):
                self._ctl_set_activity(f"{label} = {raw} → {self._ctl_target_title(eff)}  (automated)")
                continue
            # Stepped targets switch right away: their value is quantized, so
            # pickup would always see it as "moved elsewhere"
            current = None if eff in STEPPED else self._ctl_current(eff)
            t = self._ctl_resolver.resolve(b, raw, current)
            title = self._ctl_target_title(eff)
            if t is None:
                if self._ctl_resolver.pending_pickup(b):
                    self._ctl_set_activity(f"{label} = {raw} → {title}  (move to pick up)")
                continue
            self._ctl_apply(eff, t)
            self._ctl_set_activity(f"{label} = {raw} → {title}")
            self._touch_show(eff)

    def _ctl_touch(self, port: str, num: int, on: bool) -> None:
        """A surface knob/fader touched or let go (never a control value, never learned)."""
        if not on:
            self._ctl_touched.discard((port, num))
            if not self._ctl_touched:
                self._touch_timer.start(TOUCH_LINGER_MS)
            return
        self._ctl_touched.add((port, num))
        hits = self._ctl_pick(port, 15, "cc", num)
        if hits:
            self._touch_show(hits[0].target)
        if self._alt_held:
            self._alt_used = True           # touched while held: the alt layer is momentary
        # A new grab: takeover starts over from where the target is now
        for b in self._ctl_pick(port, 15, "cc", num):
            self._ctl_resolver.forget(b)

    def _touch_norm(self, target: str) -> str:
        """Key a touchscreen control is tagged with (ctlKey): "tone.tvf_cutoff" when
        all tones move, "tone.2.pitch_fine" for one tone; edited-part targets
        name the part. TouchHighlight matches a one-tone key to an all-tones
        control and the reverse."""
        eff = self._ctl_resolve(target)
        if eff.startswith("tone."):
            _, which, param = eff.split(".", 2)
            if which == "sel":
                tones = self._ctl_sel_tones(param)
                which = str(tones[0].tone_index) if len(tones) == 1 else "all"
            return f"tone.{param}" if which == "all" else f"tone.{which}.{param}"
        if eff.startswith("part.") and "@" not in eff:
            return f"{eff}@{self._editedPart()}"
        return eff

    def _touch_show(self, target: str) -> None:
        eff = self._ctl_resolve(target)
        if not eff or eff.startswith("action."):
            return
        title = self._macro_name(int(eff[6:])) if eff.startswith("macro.") else self._ctl_target_title(eff)
        group, name = self._surface_names(eff, title)
        info = {"key": self._touch_norm(eff), "group": group, "name": name, "value": self._surface_value(eff)}
        if info != self._touch_info or info["key"] != self._touch_key:
            self._touch_info, self._touch_key = info, info["key"]
            self.touchedControlChanged.emit()
        if not self._ctl_touched:
            self._touch_timer.start(TOUCH_LINGER_MS * 2)   # moved without a touch report
        else:
            self._touch_timer.stop()

    def _touch_hide(self) -> None:
        if self._touch_key:
            self._touch_key = ""
            self.touchedControlChanged.emit()

    @pyqtProperty(str, notify=touchedControlChanged)
    def touchedKey(self) -> str:
        """ctlKey of the control under the hand ("" = none): on-screen controls highlight."""
        return self._touch_key

    @pyqtProperty("QVariantMap", notify=touchedControlChanged)
    def touchedControl(self) -> dict:
        """{key, group, name, value} for the toast (shown when nothing on screen highlights)."""
        return self._touch_info

    def _ctl_set_activity(self, text: str) -> None:
        if text != self._ctl_activity:
            self._ctl_activity = text
            self.controlActivityChanged.emit()

    def _ctl_finish_learn(self, port, ch, kind, num, raw) -> None:
        target = self._ctl_learn_target
        self._ctl_learn_target = ""
        # A first value of 127 is a button press; knobs and faders send steps
        behavior = "toggle" if (kind == "note" or raw == 127) else "absolute"
        b = Binding(port=port, channel=ch, kind=kind, number=num, target=target, behavior=behavior,
                    context=self._ctl_learn_context)
        self._ctl_put_binding(b)
        self._ctl_set_activity(f"Learned {self._ctl_control_label(port, ch, kind, num)} → "
                               f"{self._ctl_target_title(target)}")

    def _ctl_put_binding(self, b: Binding, index: int = -1) -> None:
        """Add `b`, or put it at `index` in place of that binding.

        A control has one binding per context, so another binding of the
        same control and context is replaced.
        """
        keep = self._ctl_bindings[index] if 0 <= index < len(self._ctl_bindings) else None
        for old in [o for o in self._ctl_bindings
                    if o is not keep and o.same_control(b) and o.context == b.context]:
            self._ctl_bindings.remove(old)
            self._ctl_resolver.forget(old)
        if keep is None:
            self._ctl_bindings.append(b)
        else:
            self._ctl_resolver.forget(keep)
            self._ctl_bindings[self._ctl_bindings.index(keep)] = b
        self._ctl_save()
        self.controllersChanged.emit()

    # -- targets -------------------------------------------------------------

    def _ctl_resolve(self, target: str) -> str:
        """"context.N" -> the current page's knob N target ("" when unused).

        The edited tone's fine tune follows what the page offers: the master
        fine tune on Wavetable / Vector (no per-tone tuning there), the Auto
        Detune amount while Auto Detune is on (PCM, VA)."""
        if target.startswith("context."):
            # Pages without context knobs: the alt layer's row stays on the macros
            knobs = self._context_knob_targets() or [f"macro.{n}" for n in range(1, 9)]
            try:
                n = int(target[8:])
            except ValueError:
                return ""
            target = knobs[n - 1] if 1 <= n <= len(knobs) else ""
        if target == "tone.sel.pitch_fine":
            if str(getattr(self, "_active_view", "")) in ("WAVETABLE", "VECTOR"):
                return "detune.master"
            if self.patch_state.auto_detune:
                return "detune.auto"
        return "" if target == "action.none" else target

    def _ctl_entry(self, target: str):
        """Catalog entry for a target (edited-tone targets use tone 1's)."""
        target = self._ctl_resolve(target)
        if target in DETUNE:
            title, lo, hi, _, _ = DETUNE[target]
            return {"key": target, "title": title, "category": "PITCH", "min": lo, "max": hi, "span": hi - lo}
        if target.startswith("tone.sel."):
            target = "tone.1." + target[len("tone.sel."):]
        return self._macroEntry(target)

    def _ctl_mfx_param(self, target: str) -> dict | None:
        """Definition of MFX parameter N ("mfx.p.N") of the MFX being edited."""
        try:
            from ...core.mfx_catalog import get_mfx_algo

            algo = get_mfx_algo(int(self.mfxAlgoId)) or {}
            idx = int(target[6:]) - 1
            return next((p for p in algo.get("params", []) if p.get("idx") == idx), None)
        except (ValueError, TypeError):
            return None

    def _ctl_range(self, target: str) -> tuple[float, float]:
        target = self._ctl_resolve(target)
        if target in STEPPED:
            return 0.0, float(len(STEPPED[target][1]) - 1)
        if target in DETUNE:
            return float(DETUNE[target][1]), float(DETUNE[target][2])
        if target.startswith("macro."):
            return -1.0, 1.0
        if target.startswith("mfx.p."):
            p = self._ctl_mfx_param(target) or {}
            return float(p.get("min", 0)), float(p.get("max", 127))
        entry = self._ctl_entry(target)
        return (float(entry["min"]), float(entry["max"])) if entry else (0.0, 127.0)

    def _ctl_sel_tones(self, param: str) -> list:
        """Tones a "tone.sel.<param>" target edits: on JUNO PCM the selected tone
        (all when linked); VA/Wavetable/Vector ignore the PCM link, and their
        filter is a master filter over every tone."""
        if not self._sculpt_view():
            return self._target_tones()
        if param.startswith("tvf_"):
            return list(self.patch_state.tones)
        return [self._active_tone()]

    def _ctl_keys(self, target: str) -> list[str]:
        """Concrete keys a direct edit of `target` touches right now (edited part)."""
        if target.startswith("tone.sel."):     # the tone(s) the editors are on
            param = target[len("tone.sel."):]
            return [self._scopedKey(f"tone.{t.tone_index}.{param}") for t in self._ctl_sel_tones(param)]
        if "@" in target:      # a fixed part ("part.level@3"): PERFORM only
            return [target] if self._in_perform() else []
        out = []
        for k in self._expandKey(target):
            if k.startswith("part."):
                if not self._in_perform():
                    continue
                k = f"{k}@{self._editedPart()}"
            out.append(self._scopedKey(k))
        return out

    def _ctl_current(self, target: str) -> Optional[float]:
        target = self._ctl_resolve(target)
        if not target:
            return None
        lo, hi = self._ctl_range(target)
        if target in STEPPED:
            _, values, prop, _ = STEPPED[target]
            cur = str(getattr(self, prop, ""))
            return values.index(cur) / (len(values) - 1) if cur in values else None
        if target in DETUNE:
            return (float(getattr(self, DETUNE[target][3])) - lo) / (hi - lo)
        if target.startswith("macro."):
            idx = int(target[6:]) - 1
            if not 0 <= idx < len(self.patch_state.macros):
                return None
            v = self.patch_state.macros[idx].value
        elif target.startswith("mfx.p."):
            p = self._ctl_mfx_param(target)
            vals = self.mfxParamValues
            idx = int(target[6:]) - 1
            if p is None or idx >= len(vals):
                return None
            v = vals[idx]
        else:
            keys = self._ctl_keys(target)
            if not keys:
                return None
            k = keys[0]
            bases = self.patch_state.macro_bases
            v = bases[k] if (k in bases and self._macroLinksFor(k)) else self._readAbsolute(k)
        return max(0.0, min(1.0, (float(v) - lo) / ((hi - lo) or 1.0)))

    def _ctl_apply(self, target: str, t: float) -> None:
        target = self._ctl_resolve(target)
        if not target:
            return
        lo, hi = self._ctl_range(target)
        value = lo + (hi - lo) * t
        if target in STEPPED:
            _, values, _, setter = STEPPED[target]
            getattr(self, setter)(values[max(0, min(len(values) - 1, int(round(value))))])
            return
        if target in DETUNE:
            getattr(self, DETUNE[target][4])(int(round(value)))
            return
        if target.startswith("macro."):
            if abs(value) <= 1.0 / 127.0:
                value = 0.0      # 0..127 has no middle: CC 63/64 is the macro's center
            try:
                self.setMacro(int(target[6:]), value)
            except ValueError:
                pass
            return
        if target.startswith("mfx.p."):
            if self._ctl_mfx_param(target) is not None:
                self.setMfxParam(int(target[6:]) - 1, int(round(value)))
            return
        if target.endswith("pitch_fine") and self.patch_state.auto_detune:
            return      # Auto Detune owns the fine tunes (the screen's are locked too)
        touched, linked = set(), False
        for k in self._ctl_keys(target):
            if self._macroLinksFor(k):
                self.patch_state.macro_bases[k] = value
                self._recomputeTarget(k)
                linked = True
            else:
                self._applyAbsolute(k, value)
            touched.add(k)
        if touched:
            self._emitForMacroKeys(touched, macros=linked)

    def _ctl_target_title(self, target: str) -> str:
        if target.startswith("context."):
            return f"Context Knob {target[8:]}"
        if target in STEPPED:
            return STEPPED[target][0]
        if target in DETUNE:
            return DETUNE[target][0]
        if target.startswith("action."):
            return _ACTION_TITLES.get(target, target)
        if target.startswith("tone.sel."):
            entry = self._ctl_entry(target)
            return "Edited Tone " + (entry["title"][3:] if entry else target[9:])
        if target.startswith("mfx.p."):
            p = self._ctl_mfx_param(target)
            return f"MFX {p['label'].title()}" if p else f"MFX Param {target[6:]}"
        if target.startswith("macro."):
            try:
                idx = int(target[6:])
            except ValueError:
                return target
            return self._macro_title(idx) if 1 <= idx <= len(self.patch_state.macros) else target
        entry = self._macroEntry(target)
        base, part = self._splitPart(target)
        if entry and part and base.startswith("part."):
            return entry["title"].replace("Part", f"Part {part}", 1)
        return entry["title"] if entry else target

    def _short_target_name(self, target: str) -> str:
        """Compact name of a target (lane tabs, strip cards, macro names):
        "T1 Cutoff", "ALL Reso", "P3 Level", "MX2 Dest 1 Sens", "M2 WOBBLE"."""
        if target.startswith("macro."):
            return self._ctl_target_title(target)
        if target in DETUNE:
            return self._surface_names(target, "")[1]
        scope, name = self._surface_names(target, self._ctl_target_title(target))
        for prefix, short in (("TONE ", "T"), ("PART ", "P"), ("MATRIX CTRL ", "MX"), ("TRACK ", "TR")):
            if scope.startswith(prefix):
                return f"{short}{scope[len(prefix):]} {name}"
        return {"ALL TONES": f"ALL {name}", "EDITED PART": f"Part {name}"}.get(scope, name)

    def _ctl_control_label(self, port: str, ch: int, kind: str, num: int) -> str:
        if port not in self._ctl_names:
            self._ctl_names[port] = self._ctl_names_for(port)
        name = self._ctl_names[port].get(f"{kind}:{num}")
        base = f"CH{ch + 1} {'CC' if kind == 'cc' else 'NOTE'} {num}"
        return f"{name} · {base}" if name else base

    # -- feedback --------------------------------------------------------------

    def _ctl_update_feedback_timer(self) -> None:
        want = any(self._ctl_feedback_on(k) for k in self._ctl_open) or bool(self._surfaces())
        if want and not self._ctl_fb_timer.isActive():
            self._ctl_fb_timer.start()
        elif not want and self._ctl_fb_timer.isActive():
            self._ctl_fb_timer.stop()

    def _ctl_feedback_tick(self) -> None:
        """Send each absolute knob its target's value, so it never jumps (endless knobs)."""
        now = time.monotonic()
        fb_ports = {k for k in self._ctl_open if self._ctl_feedback_on(k)}
        for b in self._ctl_bindings:
            if (b.kind != "cc" or b.behavior != "absolute" or b.target.startswith("action.")
                    or b.port not in fb_ports):
                continue
            ctl = (b.port, b.channel, b.kind, b.number)
            if b not in self._ctl_pick(*ctl):
                continue        # another context owns this control right now
            moved = self._ctl_moved.get(ctl)
            if moved and now - moved[1] < FEEDBACK_HOLD_S:
                self._ctl_fb_sent[ctl] = moved[0]
                continue
            t = self._ctl_current(b.target)
            if t is None or b.hi == b.lo:
                continue
            raw = int(round(max(0.0, min(1.0, (t - b.lo) / (b.hi - b.lo))) * 127))
            if self._ctl_fb_sent.get(ctl) == raw:
                continue
            self._ctl_fb_sent[ctl] = raw
            self._ctl_send(b.port, mido.Message("control_change", channel=b.channel,
                                                control=b.number, value=raw))
        self._surface_tick()

    # -- LCXL3 surface (screen + LEDs; preset device "surface": "lcxl3") -------------

    _TONE_RGB = [(0, 110, 127), (127, 0, 110), (127, 90, 0), (0, 127, 50)]

    def _surfaces(self) -> list[tuple[str, dict]]:
        """(DAW port key, state) per connected surface device."""
        out = []
        st_all = self.__dict__.setdefault("_surface_state", {})
        for i, client in self._ctl_connected_devices:
            dev = self._ctl_devices[i] if i < len(self._ctl_devices) else {}
            if dev.get("surface") != "lcxl3":
                continue
            port = next((k for k in self._ctl_open if k.split(":")[0] == client and "DAW" in k), None)
            if port:
                out.append((port, st_all.setdefault(port, {"names": {}, "values": {}, "leds": {}, "stat": None})))
        return out

    def _surface_binding(self, port: str, number: int):
        ch = 0 if number in lcxl3.BUTTONS or number > 100 else 15
        hits = self._ctl_pick(port, ch, "cc", number)
        return hits[0] if hits else None

    # Clip row LEDs by clip state
    _CLIP_RGB = {"empty": lcxl3.OFF, "loaded": (20, 20, 20), "queued": (127, 80, 0), "playing": (0, 127, 0)}

    def _seq_clip_state_any(self, track_idx: int) -> bool:
        """Whether a track plays or has a clip queued (its stop button lights)."""
        track = self.sequencer.song.tracks[track_idx]
        return any(self._seq_clip_state(track_idx, c) in ("playing", "queued") for c in range(len(track.clips)))

    def _surface_button_rgb(self, b) -> tuple:
        if b is None or b.target == "action.none":
            return lcxl3.OFF
        t = b.target
        n = int(t.rsplit(".", 1)[1]) if t.rsplit(".", 1)[-1].isdigit() else 0
        ps = self.patch_state
        on, color = False, (40, 40, 40)
        if t.startswith("action.part.mute."):
            on, color = ps.perf_parts[n - 1].muted, (127, 0, 0)
        elif t.startswith("action.part.solo."):
            on, color = ps.perf_parts[n - 1].solo, (127, 100, 0)
        elif t.startswith("action.part.edit."):
            on, color = self._editedPart() == n, (127, 127, 127)
        elif t.startswith("action.mfx.edit."):
            on, color = self.editingPerfMfx == n, (127, 0, 127)
        elif t.startswith("action.tone.mute."):
            on, color = ps.tones[n - 1].muted, (127, 0, 0)
        elif t.startswith("action.tone.select."):
            on, color = int(self._selected_tone) == n, self._TONE_RGB[n - 1]
        elif t in ("action.seq.toggle_play", "action.seq.play"):
            on, color = bool(getattr(self.sequencer, "is_playing", False)), (0, 127, 0)
        elif t == "action.seq.live_record":
            on, color = bool(self.seqRecArmed), (127, 0, 0)
        elif t.startswith("action.view.goto."):
            view = t[len("action.view.goto."):]
            on, color = str(getattr(self, "_active_view", "")) == view, _view_rgb(view)
        elif t == "action.seq.scene_launch":
            on, color = any(tr.active_clip_idx == self._ctl_scene for tr in self.sequencer.song.tracks) \
                and self.sequencer.is_playing, (127, 127, 127)
        elif t == "action.seq.scene_stop":
            color = (127, 40, 0)
        elif t.startswith("action.seq.scene."):
            color = (0, 127, 0)
        elif t.startswith("action.seq.stop_track."):
            color = (127, 0, 0)
        elif t.startswith("action.seq.clip."):
            return self._CLIP_RGB[self._seq_clip_state(self._active_seq_track, n - 1)]
        elif t == "action.seq.stop_selected":
            on, color = self._seq_clip_state_any(self._active_seq_track), (127, 0, 0)
        elif t == "action.seq.stop_all":
            on = any(self._seq_clip_state_any(i) for i in range(len(self.sequencer.song.tracks)))
            color = (127, 0, 0)
        elif t.startswith("action.seq.launch."):
            tr, c = (int(x) - 1 for x in t.split(".")[3:5])
            track = self.sequencer.song.tracks[tr]
            on, color = track.active_clip_idx == c, (0, 127, 0)
            on = on and (self.sequencer.is_playing or self.sequencer._audio_active_clip(track) is not None)
        elif t == "action.seq.track_bank":
            on, color = self.seqTrackBank == 1, (110, 110, 127)
        elif t == "action.motion.toggle_play":
            on, color = self.vector.motion.state.value == "playing", (0, 127, 0)
        elif t == "action.motion.toggle_record":
            on, color = self.vector.motion.state.value == "recording", (127, 0, 0)
        elif t == "action.arp.toggle":
            on, color = self._arp.switch, (0, 100, 127)
        elif t == "action.arp.hold":
            on, color = self._arp.hold, (0, 100, 127)
        elif not t.startswith("action."):
            cur = self._ctl_current(t)
            entry = self._macroEntry(t)
            color = lcxl3.CATEGORY_COLORS.get(lcxl3.led_category(t, (entry or {}).get("category", "")),
                                              (60, 60, 60))
            on = cur is not None and cur >= 0.5
        return color if on else lcxl3.dim(color)

    def _ctl_context_changed(self, *_args) -> None:
        # patchInfoChanged also fires on every patch/part change; only a new
        # page, mode or bank changes which bindings are active
        state = (str(getattr(self, "_active_view", "")), self._ctl_mode(), self.seqTrackBank)
        last = getattr(self, "_ctl_last_context", None)
        if state == last:
            return
        if last is not None and state[2] != last[2]:
            self._ctl_fb_sent.clear()   # the new bank's bindings send their positions
        self._ctl_last_context = state
        self.controllersChanged.emit()

    def _ctl_set_layer(self, layer: str) -> None:
        if layer == self._ctl_layer:
            return
        self._ctl_layer = layer
        self._ctl_fb_sent.clear()       # the newly active bindings send their positions
        self.controllersChanged.emit()

    def _surface_names(self, target: str, title: str) -> tuple[str, str]:
        if target.startswith("context."):
            target = self._ctl_resolve(target)
            if not target:
                return "SPECTRE", "-"
            title = self._ctl_target_title(target)
        if target in STEPPED:
            return "SPECTRE", STEPPED[target][0]
        if target in DETUNE:
            return "ALL TONES", {"detune.master": "Master Fine", "detune.auto": "Auto Detune"}[target]
        if target.startswith("tone.sel."):
            tones = self._ctl_sel_tones(target[len("tone.sel."):])
            scope = f"TONE {tones[0].tone_index}" if len(tones) == 1 else "LINKED TONES"
            return scope, lcxl3.short_title(title.removeprefix("Edited Tone "))
        if target.startswith("mfx.p."):
            p = self._ctl_mfx_param(target)
            return "MFX", (str(p.get("label", "")).title() if p else "-")
        entry = self._ctl_entry(target)
        return lcxl3.screen_names(target, title, (entry or {}).get("category", ""))

    def _surface_value(self, target: str) -> str:
        target = self._ctl_resolve(target)
        if not target or target.startswith("action."):
            return ""
        if target in STEPPED:
            _, values, prop, _ = STEPPED[target]
            text = str(getattr(self, prop, ""))
            # Arp values are the synth's own names: "Up (_)" keeps its underscore
            return (text if target.startswith("arp.") else text.replace("_", " ")).upper()
        if target in DETUNE:
            v = int(getattr(self, DETUNE[target][3]))
            return f"{v:+d} c" if target == "detune.master" else f"{v} c"
        cur = self._ctl_current(target)
        if cur is None:
            return ""
        lo, hi = self._ctl_range(target)
        value = lo + (hi - lo) * cur
        if target.startswith("mfx.p."):
            p = self._ctl_mfx_param(target) or {}
            v = int(round(value))
            opts = p.get("options")
            if opts and 0 <= v - int(p.get("min", 0)) < len(opts):
                return f"{opts[v - int(p.get('min', 0))]} {p.get('unit', '')}".strip()
            return f"{v} {p.get('unit', '')}".strip()
        return lcxl3.format_value(target.replace("tone.sel.", "tone.1."), value, lo, hi)

    def _surface_tick(self, moved: set | None = None) -> None:
        """Bring each surface's screen and LEDs up to date (only diffs are sent)."""
        for port, st in self._surfaces():
            msgs = []
            controls = list(lcxl3.FADERS) + list(lcxl3.KNOBS)
            if moved is not None:
                controls = [c for c in controls if (port, 15, "cc", c) in moved]
            for num in controls:
                b = self._surface_binding(port, num)
                eff = self._ctl_resolve(b.target) if b is not None else ""
                if not eff:
                    names, value = ("SPECTRE", "-"), ""
                else:
                    if eff.startswith("macro."):
                        idx = eff[6:]
                        title = self._macro_name(int(idx)) if idx.isdigit() else ""
                    elif eff.startswith("action."):
                        title = lcxl3.short_title(self._ctl_target_title(eff))
                    else:
                        title = self._ctl_target_title(eff)
                    names = self._surface_names(eff, title)
                    value = self._surface_value(eff)
                if st["names"].get(num) != names:
                    if num not in st["names"]:
                        msgs.append(lcxl3.display_config(num))
                    msgs += [lcxl3.display_text(num, 0, names[0]), lcxl3.display_text(num, 1, names[1])]
                    st["names"][num] = names
                if st["values"].get(num) != value:
                    msgs.append(lcxl3.display_text(num, 2, value))
                    st["values"][num] = value
                if num in lcxl3.KNOBS:
                    rgb = lcxl3.OFF
                    eff = self._ctl_resolve(b.target) if b is not None else ""
                    if eff:
                        entry = self._ctl_entry(eff)
                        cat = lcxl3.led_category(eff, "FX" if eff.startswith("mfx.p.")
                                                 else ("MORPH" if eff in STEPPED else (entry or {}).get("category", "")))
                        rgb = lcxl3.CATEGORY_COLORS.get(cat, (60, 60, 60))
                        if not eff.startswith("action."):
                            rgb = lcxl3.by_value(rgb, self._ctl_current(eff))
                    if st["leds"].get(num) != rgb:
                        msgs.append(lcxl3.led_rgb(num, rgb))
                        st["leds"][num] = rgb
            if moved is None:
                for num in list(lcxl3.BUTTONS) + [116, 118]:
                    rgb = self._surface_button_rgb(self._surface_binding(port, num))
                    if st["leds"].get(num) != rgb:
                        msgs.append(lcxl3.led_rgb(num, rgb))
                        st["leds"][num] = rgb
                sel = (f"PART {self._editedPart()}" if self._in_perform()
                       else f"TONE {int(self._selected_tone)}")
                page = str(getattr(self, "_active_view", ""))
                if self._ctl_layer == "MIXER":
                    page = "MIXER " + ("9-16" if self.seqTrackBank == 1 else "1-8") if self._in_perform() else "MIXER"
                if self._alt_on():
                    page = f"CTX · SCENE {self._ctl_scene + 1}"
                stat = (str(getattr(self, "_patch_name", "") or "JUNO SPECTRE"), page,
                        f"{self._ctl_mode()} · {sel}")
                if st["stat"] != stat:
                    if st["stat"] is None:
                        msgs.append(lcxl3.display_config(lcxl3.STATIONARY, stationary=True))
                    msgs += [lcxl3.display_text(lcxl3.STATIONARY, i, line) for i, line in enumerate(stat)]
                    msgs.append(lcxl3.display_show(lcxl3.STATIONARY))
                    st["stat"] = stat
            for m in msgs:
                self._ctl_send(port, m)

    # -- on-screen context strip ------------------------------------------------

    def _context_knob_targets(self) -> list:
        """The current page's 8 knob targets. The sequencer follows the visible track bank."""
        view = str(getattr(self, "_active_view", ""))
        if view == "SEQUENCER" and hasattr(self, "sequencer"):
            first = self.seqTrackBank * TRACK_BANK_SIZE
            last = min(len(self.sequencer.song.tracks), first + TRACK_BANK_SIZE)
            return [f"seq.swing.{i + 1}" for i in range(first, last)]
        return CONTEXT_KNOBS.get(view, [])

    def _ctx_compute(self) -> list:
        out = []
        knobs = self._context_knob_targets()
        for n in range(1, 9):
            target = knobs[n - 1] if n <= len(knobs) else ""
            if not target:
                out.append({"key": "", "title": "-", "text": "", "norm": 0.0, "active": False,
                            "bipolar": False, "touchKey": ""})
                continue
            target = self._ctl_resolve(target)   # e.g. fine tune -> Auto Detune amount
            title = self._short_target_name(target)
            cur = self._ctl_current(target)
            out.append({"key": target, "title": title, "text": self._surface_value(target),
                        "norm": round(cur, 4) if cur is not None else 0.0, "active": cur is not None,
                        "bipolar": target.startswith("macro."), "touchKey": self._touch_norm(target)})
        return out

    def _ctx_refresh(self, *_args) -> None:
        knobs = self._ctx_compute()
        if knobs != self._ctx_knobs:
            self._ctx_knobs = knobs
            self.contextKnobsChanged.emit()

    @pyqtProperty("QVariantList", notify=contextKnobsChanged)
    def contextKnobs(self) -> list:
        """The current page's 8 context knobs: [{key, title, text, norm, active, bipolar}]."""
        return self._ctx_knobs

    @pyqtProperty(bool, notify=contextKnobsChanged)
    def contextKnobsAvailable(self) -> bool:
        """Whether the current page has context knobs (the strip is hidden otherwise)."""
        return any(CONTEXT_KNOBS.get(str(getattr(self, "_active_view", "")), []))

    @pyqtSlot(int, float)
    def setContextKnob(self, index: int, norm: float) -> None:
        """Touch drag on strip card `index` (1..8), norm 0..1."""
        target = self._ctl_resolve(f"context.{int(index)}")
        if not target:
            return
        with self._macroWrites():
            self._ctl_apply(target, max(0.0, min(1.0, float(norm))))
        self._ctx_refresh()

    def _ctl_run_action(self, action: str) -> None:
        parts = action.split(".")
        n = int(parts[-1]) if parts[-1].isdigit() else 0
        try:
            if action == "seq.toggle_play":
                self.seqTogglePlay()
            elif action == "seq.play":
                self.seqPlay()
            elif action == "seq.stop":
                self.seqStop()
            elif action == "seq.live_record":
                self.seqToggleRecord()
            elif action.startswith("seq.scene."):
                self.seqLaunchScene(n - 1)
            elif action.startswith("seq.stop_track."):
                self.seqStopTrack(n - 1)
            elif action.startswith("seq.clip."):
                self.seqLaunchClip(self._active_seq_track, n - 1)
            elif action == "seq.stop_selected":
                self.seqStopTrack(self._active_seq_track)
            elif action == "seq.stop_all":
                self.seqStopAllClips()
            elif action in ("scene.next", "scene.prev"):
                scenes = max(len(t.clips) for t in self.sequencer.song.tracks)
                step = 1 if action == "scene.next" else -1
                self._ctl_scene = max(0, min(scenes - 1, self._ctl_scene + step))
            elif action == "seq.scene_launch":
                self.seqLaunchScene(self._ctl_scene)
            elif action == "seq.scene_stop":
                self.seqStopScene(self._ctl_scene)
            elif action.startswith("seq.launch.") and len(parts) == 4:
                self.seqLaunchClip(int(parts[2]) - 1, n - 1)
            elif action == "seq.track_bank":
                self.seqSetTrackBank(1 - self.seqTrackBank)
            elif action == "motion.toggle_play":
                state = self.vector.motion.state.value
                self.stopMotion() if state == "playing" else self.playMotion()
            elif action == "motion.toggle_record":
                state = self.vector.motion.state.value
                self.stopRecording() if state == "recording" else self.startRecording()
            elif action.startswith("tone.mute."):
                self.toggleToneMute(n)
            elif action.startswith("tone.select."):
                self.setSelectedTone(n)
            elif action.startswith("part.mute."):
                self.setPartMute(n, not self.patch_state.perf_parts[n - 1].muted)
            elif action.startswith("part.solo."):
                self.setPartSolo(n, not self.patch_state.perf_parts[n - 1].solo)
            elif action.startswith("part.edit."):
                self.editPerfPart(n)
            elif action.startswith("mfx.edit."):
                self.setEditingPerfMfx(n)
            elif action in ("mfx.next", "mfx.prev"):
                step = 1 if action == "mfx.next" else -1
                self.setEditingPerfMfx((self.editingPerfMfx - 1 + step) % 3 + 1)
            elif action == "edit_target.open":
                self.openEditTarget()
            elif action == "playlist.next":
                self.nextSong()
            elif action == "playlist.prev":
                self.prevSong()
            elif action == "panic":
                self.panic()
            elif action == "arp.toggle":
                self.toggleArp()
            elif action == "arp.hold":
                self.toggleArpHold()
            elif action.startswith("view.goto."):
                self.setActiveView(action[len("view.goto."):])
            elif action in ("view.next", "view.prev"):
                view = str(getattr(self, "_active_view", ""))
                i = CONTEXT_PAGES.index(view) if view in CONTEXT_PAGES else -1
                step = 1 if action == "view.next" else -1
                self.setActiveView(CONTEXT_PAGES[(i + step) % len(CONTEXT_PAGES)])
            elif action in ("bank.next", "bank.prev"):
                self.seqSetTrackBank(1 if action == "bank.next" else 0)
            elif action in ("select.next", "select.prev"):
                self.selectNextTrack(1 if action == "select.next" else -1)
        except Exception as e:
            logger.warning(f"controller action {action} failed: {e}")

    # -- presets -------------------------------------------------------------

    @staticmethod
    def _ctl_preset_files() -> list[tuple[str, Path]]:
        out = []
        for source, folder in (("bundled", BUNDLED_PRESET_DIR), ("user", user_preset_dir())):
            if folder.is_dir():
                out += [(source, p) for p in sorted(folder.glob("*.json"))]
        return out

    @staticmethod
    def _ctl_read_preset(path: Path) -> dict:
        try:
            return dict(json.loads(path.read_text()))
        except (OSError, ValueError, TypeError):
            return {}

    def _ctl_load_names(self) -> None:
        """Control names ("Knob A1") from presets, for every open port they match."""
        self._ctl_preset_names = []
        for _, path in self._ctl_preset_files():
            d = self._ctl_read_preset(path)
            if d.get("controls") and d.get("match"):
                self._ctl_preset_names.append((list(d["match"]), dict(d["controls"])))

    def _ctl_names_for(self, port: str) -> dict:
        for match, names in getattr(self, "_ctl_preset_names", []):
            if any(m in port for m in match):
                return names
        return {}

    # -- QML API -------------------------------------------------------------

    @pyqtProperty("QVariantList", notify=controllersChanged)
    def controllerPorts(self) -> list:
        """Input ports that can act as controllers: [{key, enabled, open}]."""
        synth = self.synthPort
        seen = []
        for name in self._hw_inputs:
            k = port_key(name)
            if k == synth or k in seen or "Midi Through" in k or k.startswith(("RtMidiIn Client", "RtMidiOut Client")):
                continue
            seen.append(k)
        return [{"key": k, "enabled": self._ctl_port_enabled(k), "open": k in self._ctl_open,
                 "feedback": self._ctl_feedback_on(k)} for k in seen]

    @pyqtSlot(str, bool)
    def setControllerFeedback(self, key: str, enabled: bool) -> None:
        """Send bound knobs their target's value (endless knobs follow the app)."""
        self._ctl_feedback[str(key)] = bool(enabled)
        self._ctl_fb_sent.clear()
        self._ctl_save()
        self._ctl_update_feedback_timer()
        self.controllersChanged.emit()

    @pyqtSlot(result="QVariantList")
    def controlContexts(self) -> list:
        """Learn scopes: everywhere, a sound mode, or the current page."""
        return ([{"key": k, "title": t} for k, t in CONTEXT_TITLES.items()]
                + [{"key": v, "title": v} for v in CONTEXT_PAGES])

    @pyqtSlot(str, bool)
    def setControllerPortEnabled(self, key: str, enabled: bool) -> None:
        self._ctl_enabled[str(key)] = bool(enabled)
        self._ctl_save()
        self._ctl_sync_ports(self._hw_inputs)
        self.controllersChanged.emit()

    @pyqtProperty("QVariantList", notify=controllersChanged)
    def controlBindings(self) -> list:
        out = []
        state = self._ctl_state()
        # Bucket by control (an any-port binding competes with every port's)
        by_control: dict = {}
        for b in self._ctl_bindings:
            by_control.setdefault((b.channel, b.kind, b.number), []).append(b)
        active_ids: set = set()
        for (ch, kind, num), group in by_control.items():
            for port in {b.port for b in group}:
                active_ids.update(id(b) for b in pick_bindings(group, port, ch, kind, num, state)
                                  if b.port == port)
        for i, b in enumerate(self._ctl_bindings):
            out.append({
                "active": id(b) in active_ids,
                "index": i, "control": self._ctl_control_label(b.port, b.channel, b.kind, b.number),
                "port": b.port or "ANY PORT", "online": (not b.port) or b.port in self._ctl_open,
                "target": b.target, "title": self._ctl_target_title(b.target),
                "macro": b.target.startswith("macro."),
                "behavior": b.behavior, "takeover": b.takeover, "lo": b.lo, "hi": b.hi,
                "action": b.target.startswith("action."),
                "context": b.context, "contextTitle": context_title(b.context),
            })
        return out

    @pyqtProperty(str, notify=controlActivityChanged)
    def controlActivity(self) -> str:
        return self._ctl_activity

    @pyqtProperty(str, notify=controllersChanged)
    def controlLearnTarget(self) -> str:
        return self._ctl_learn_target

    @pyqtProperty(str, notify=controllersChanged)
    def controlLearnTitle(self) -> str:
        return self._ctl_target_title(self._ctl_learn_target) if self._ctl_learn_target else ""

    @pyqtSlot(str)
    @pyqtSlot(str, str)
    def startControlLearn(self, target: str, context: str = "") -> None:
        """Bind the next control that moves to `target` ("" cancels) in `context`."""
        self._ctl_learn_target = str(target or "")
        self._ctl_learn_context = str(context or "")
        with self._ctl_lock:
            self._ctl_events.clear()
        self.controllersChanged.emit()

    # Manual entry: a control typed in by channel and number instead of learned

    @pyqtSlot(int, result="QVariantMap")
    def controlManualStart(self, index: int) -> dict:
        """Starting values for the manual entry panel (channel 1..16).

        A binding's own control when editing one (index >= 0), else the
        control that moved last, else CH1 CC 1 on any port.
        """
        if 0 <= index < len(self._ctl_bindings):
            b = self._ctl_bindings[index]
            port, ch, kind, num = b.port, b.channel, b.kind, b.number
        elif self._ctl_moved:
            port, ch, kind, num = max(self._ctl_moved, key=lambda c: self._ctl_moved[c][1])
        else:
            port, ch, kind, num = "", 0, "cc", 1
        return {"port": port, "channel": ch + 1, "kind": kind, "number": num}

    @pyqtSlot(str, result="QVariantList")
    def controlManualPorts(self, current: str = "") -> list:
        """Ports a typed-in control can listen on: any port, then each controller input."""
        keys = [p["key"] for p in self.controllerPorts if p["enabled"]]
        if current and current not in keys:
            keys.append(current)
        return [{"key": "", "title": "ANY PORT"}] + [{"key": k, "title": k} for k in keys]

    @pyqtSlot(str, int, str, int, result=str)
    def controlLabel(self, port: str, channel: int, kind: str, number: int) -> str:
        """"Knob A1 · CH1 CC 13" for channel 1..16."""
        return self._ctl_control_label(str(port or ""), (int(channel) - 1) & 0x0F,
                                       "note" if kind == "note" else "cc", int(number) & 0x7F)

    @pyqtSlot(str, int, str, int, str, int, result=str)
    def controlBoundTo(self, port: str, channel: int, kind: str, number: int, context: str, index: int) -> str:
        """Title of the binding a manual entry would replace ("" = none)."""
        probe = Binding(port=str(port or ""), channel=(int(channel) - 1) & 0x0F,
                        kind="note" if kind == "note" else "cc", number=int(number) & 0x7F,
                        target="-", context=str(context or ""))
        for i, b in enumerate(self._ctl_bindings):
            if i != index and b.same_control(probe) and b.context == probe.context:
                return self._ctl_target_title(b.target)
        return ""

    @pyqtSlot(str, str, str, int, str, int, bool)
    def addControlBinding(self, target: str, context: str, port: str, channel: int, kind: str,
                          number: int, button: bool) -> None:
        """Bind a typed-in control (channel 1..16) to `target`, as learn would."""
        if not target:
            return
        kind = "note" if kind == "note" else "cc"
        behavior = "toggle" if (button or target.startswith("action.")) else "absolute"
        b = Binding(port=str(port or ""), channel=(int(channel) - 1) & 0x0F, kind=kind,
                    number=int(number) & 0x7F, target=str(target), behavior=behavior,
                    context=str(context or ""))
        self._ctl_put_binding(b)
        self._ctl_set_activity(f"Assigned {self._ctl_control_label(b.port, b.channel, kind, b.number)} → "
                               f"{self._ctl_target_title(b.target)}")

    @pyqtSlot(int, str, int, str, int)
    def setControlBindingControl(self, index: int, port: str, channel: int, kind: str, number: int) -> None:
        """Move binding `index` to another control (channel 1..16); its options stay."""
        if not 0 <= index < len(self._ctl_bindings):
            return
        old = self._ctl_bindings[index]
        b = Binding(**{**old.to_dict(), "port": str(port or ""), "channel": (int(channel) - 1) & 0x0F,
                       "kind": "note" if kind == "note" else "cc", "number": int(number) & 0x7F})
        self._ctl_put_binding(b, index)

    @pyqtSlot(str, str, result="QVariantList")
    def getControlTargets(self, category: str = "ALL", query: str = "") -> list:
        """The macro catalog plus the 8 macros (category MACRO)."""
        q = (query or "").strip().lower()
        macros = []
        if category in ("ALL", "MACRO", ""):
            for i in range(1, len(self.patch_state.macros) + 1):
                title = self._ctl_target_title(f"macro.{i}")
                if q and q not in title.lower() and q not in f"macro.{i}":
                    continue
                macros.append({"key": f"macro.{i}", "title": title, "category": "MACRO",
                               "min": -1.0, "max": 1.0, "span": 2.0})
        editor = []
        if category in ("ALL", "EDITOR", ""):
            for e in filter_macro_targets("ALL", ""):
                if e["key"].startswith("tone.1."):
                    key = "tone.sel." + e["key"][7:]
                    title = "Edited Tone " + e["title"][3:]
                    if not q or q in title.lower():
                        editor.append({**e, "key": key, "title": title, "category": "EDITOR"})
            for n in range(1, 9):
                title = f"Context Knob {n} (follows the page)"
                if not q or q in title.lower():
                    editor.append({"key": f"context.{n}", "title": title, "category": "EDITOR",
                                   "min": 0.0, "max": 1.0, "span": 1.0})
            for n in range(1, 9):
                title = f"MFX Param {n} (edited MFX)"
                if not q or q in title.lower():
                    editor.append({"key": f"mfx.p.{n}", "title": title, "category": "EDITOR",
                                   "min": 0.0, "max": 127.0, "span": 127.0})
        if category == "EDITOR":
            return editor
        actions = []
        if category in ("ALL", "ACTION", "CLIP", ""):
            pool = {"ACTION": ACTIONS, "CLIP": CLIP_ACTIONS}.get(category, ACTIONS + CLIP_ACTIONS)
            actions = [a for a in pool if not q or q in a["title"].lower() or q in a["key"]]
        if category == "MACRO":
            return macros
        if category in ("ACTION", "CLIP"):
            return actions
        # Fixed parts for mixer-style controls (the catalog's part.* follow the edited part)
        fixed = []
        if category in ("ALL", "PART", ""):
            for e in filter_macro_targets("PART", ""):
                for n in range(1, 17):
                    title = e["title"].replace("Part", f"Part {n}", 1)
                    if not q or q in title.lower():
                        fixed.append({**e, "key": f"{e['key']}@{n}", "title": title})
        return macros + editor + filter_macro_targets(category, query) + fixed + actions

    @pyqtSlot(result="QVariantList")
    def getControlCategories(self) -> list:
        cats = get_macro_categories()
        return cats[:1] + ["MACRO", "EDITOR", "ACTION", "CLIP"] + cats[1:]

    @pyqtSlot(int, str, str)
    def setControlBindingOption(self, index: int, option: str, value: str) -> None:
        """option: behavior | takeover | range ("full", "invert", "upper", "lower") | context."""
        if not 0 <= index < len(self._ctl_bindings):
            return
        b = self._ctl_bindings[index]
        if option == "behavior" and value in BEHAVIORS:
            b.behavior = value
        elif option == "takeover" and value in TAKEOVERS:
            b.takeover = value
        elif option == "context":
            b.context = str(value or "")
        elif option == "range":
            b.lo, b.hi = {"full": (0.0, 1.0), "invert": (1.0, 0.0),
                          "upper": (0.5, 1.0), "lower": (0.5, 0.0)}.get(value, (b.lo, b.hi))
        else:
            return
        self._ctl_resolver.forget(b)
        self._ctl_save()
        self.controllersChanged.emit()

    @pyqtSlot(int)
    def removeControlBinding(self, index: int) -> None:
        if 0 <= index < len(self._ctl_bindings):
            self._ctl_resolver.forget(self._ctl_bindings.pop(index))
            self._ctl_save()
            self.controllersChanged.emit()

    @pyqtSlot()
    def clearControlBindings(self) -> None:
        self._ctl_bindings = []
        self._ctl_resolver = Resolver()
        self._ctl_save()
        self.controllersChanged.emit()

    @pyqtSlot(result="QVariantList")
    def controlPresets(self) -> list:
        out = []
        for source, path in self._ctl_preset_files():
            d = self._ctl_read_preset(path)
            if d.get("bindings"):
                out.append({"file": str(path), "name": str(d.get("name", path.stem)), "source": source,
                            "description": str(d.get("description", "")), "count": len(d["bindings"])})
        return out

    @pyqtSlot(str, result=str)
    def loadControlPreset(self, file: str) -> str:
        """Replace the bindings with a preset's, aimed at the device ports it matches.

        A preset may carry a "device" setup (ports to listen to, knob
        feedback, messages on connect/quit) and bindings with a "port_hint"
        for a second port of the same device (e.g. "DAW").
        """
        d = self._ctl_read_preset(Path(file))
        raw = [x for x in d.get("bindings", []) if isinstance(x, dict)]
        bindings = [Binding.from_dict(x) for x in raw]
        if not any(bindings):
            return "Preset has no bindings."
        match = [str(m) for m in d.get("match", []) if m]
        device = d.get("device")
        if isinstance(device, dict) and match:
            dev = {**device, "match": match}
            self._ctl_devices = [x for x in self._ctl_devices if x.get("match") != match] + [dev]
            # Fresh setup: listen/feedback come from the device, on_connect runs again
            for k in [k for k in self._ctl_enabled if any(m in k for m in match)]:
                del self._ctl_enabled[k]
            for k in [k for k in self._ctl_feedback if any(m in k for m in match)]:
                del self._ctl_feedback[k]
            self._ctl_connected_devices = {c for c in self._ctl_connected_devices
                                           if not any(m in c[1] for m in match)}
            self._ctl_sync_ports(self._hw_inputs)
            self._ctl_setup_devices()
        ports = [k for k in self._ctl_open if any(m in k for m in match)] if match else []
        main = next(iter(ports), "")
        out = []
        for b, x in zip(bindings, raw):
            if b is None:
                continue
            hint = str(x.get("port_hint", "") or "")
            if not b.port:
                b.port = next((k for k in ports if hint and hint in k), "") if hint else main
                if hint and not b.port:
                    continue    # that port isn't there
            out.append(b)
        self._ctl_bindings = out
        self._ctl_resolver = Resolver()
        self._ctl_fb_sent.clear()
        self._ctl_save()
        self._ctl_update_feedback_timer()
        self.controllersChanged.emit()
        return "" if main or not match else "Controller not connected: bound to any port."

    @pyqtSlot(str, result=str)
    def saveControlPreset(self, name: str) -> str:
        """Save the current bindings as a user preset (port names are dropped)."""
        name = " ".join(str(name or "").split()) or "My controller"
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)[:60]
        ports = {b.port for b in self._ctl_bindings if b.port}
        match = sorted({p.split(":")[0] for p in ports})
        clients = {p.split(":")[0] for p in ports}
        # Per device, the port most bindings use is the main one; others get a port_hint
        counts: dict[str, int] = {}
        for b in self._ctl_bindings:
            if b.port:
                counts[b.port] = counts.get(b.port, 0) + 1
        main = {c: max((p for p in counts if p.split(":")[0] == c), key=counts.get) for c in clients}
        out = []
        for b in self._ctl_bindings:
            d = {**b.to_dict(), "port": ""}
            if b.port and b.port != main.get(b.port.split(":")[0]):
                d["port_hint"] = b.port.split(":", 1)[-1].replace(b.port.split(":")[0], "").strip()
            out.append(d)
        data = {"name": name, "match": match, "bindings": out}
        dev = next((self._ctl_device(p)[1] for p in ports if self._ctl_device(p)[1]), None)
        if dev:
            data["device"] = {k: v for k, v in dev.items() if k != "match"}
        folder = user_preset_dir()
        try:
            folder.mkdir(parents=True, exist_ok=True)
            (folder / f"{safe}.json").write_text(json.dumps(data, indent=2))
        except OSError as e:
            return f"Could not save: {e}"
        return ""
