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

from ...control.mapping import BEHAVIORS, TAKEOVERS, Binding, Resolver, pick_bindings
from ...core.macro_targets import filter_macro_targets, get_macro_categories
from ...core.midi import port_key
from .base import BridgeBaseMixin
from .hardware import save_hardware_settings

logger = logging.getLogger(__name__)

DRAIN_MS = 15
FEEDBACK_MS = 100
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
     _action("seq.stop", "Sequencer Stop"), _action("seq.live_record", "Sequencer Overdub On/Off")]
    + [_action(f"seq.scene.{n}", f"Launch Scene {n}") for n in range(1, 9)]
    + [_action(f"seq.stop_track.{n}", f"Stop Track {n}") for n in range(1, 9)]
    + [_action("motion.toggle_play", "Motion Play/Stop"), _action("motion.toggle_record", "Motion Record On/Off")]
    + [_action(f"tone.mute.{n}", f"Tone {n} Mute On/Off") for n in range(1, 5)]
    + [_action(f"tone.select.{n}", f"Select Tone {n}") for n in range(1, 5)]
    + [_action(f"part.mute.{n}", f"Part {n} Mute On/Off") for n in range(1, 17)]
    + [_action(f"part.solo.{n}", f"Part {n} Solo On/Off") for n in range(1, 17)]
    + [_action(f"part.edit.{n}", f"Edit Part {n}") for n in range(1, 17)]
    + [_action("playlist.next", "Playlist Next"), _action("playlist.prev", "Playlist Previous"),
       _action("panic", "Panic (All Notes Off)")]
)
_ACTION_TITLES = {a["key"]: a["title"] for a in ACTIONS}

# Learn scopes offered in the UI
CONTEXT_TITLES = {"": "EVERYWHERE", "MODE:PATCH": "PATCH MODE", "MODE:PERFORM": "PERFORM MODE"}
# App pages a binding can belong to (activeView keys)
CONTEXT_PAGES = ["JUNO PCM", "VECTOR", "WAVETABLE", "VA", "MOD MATRIX", "STEP LFO", "MSEG ENVELOPES",
                 "ROUTING", "MFX", "MASTER FX", "LIVE", "SEQUENCER", "SETLIST", "PERFORMANCE", "MACROS"]


def default_controller_port(key: str) -> bool:
    """Inputs listened to unless switched off: not the synth's, loopback, DAW or our own."""
    return not (any(k in key for k in ("JUNO", "XPS", "Midi Through", "DAW"))
                or key.startswith(("RtMidiIn Client", "RtMidiOut Client")))


class ControllersBridgeMixin(BridgeBaseMixin):
    controllersChanged = pyqtSignal()
    controlActivityChanged = pyqtSignal()
    _ctlPending = pyqtSignal()   # rtmidi thread -> UI thread

    def _init_controllers(self) -> None:
        cfg = dict(self._hw_settings.get("controllers", {}) or {})
        self._ctl_enabled: dict[str, bool] = {str(k): bool(v) for k, v in dict(cfg.get("enabled", {})).items()}
        self._ctl_bindings: list[Binding] = [b for b in map(Binding.from_dict, cfg.get("bindings", [])) if b]
        self._ctl_resolver = Resolver()
        self._ctl_open: dict[str, object] = {}      # port key -> mido input
        self._ctl_events: deque = deque(maxlen=4096)
        self._ctl_lock = threading.Lock()
        self._ctl_scheduled = False
        self._ctl_learn_target = ""
        self._ctl_learn_context = ""
        self._ctl_activity = ""
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
        self._ctlPending.connect(self._ctl_schedule_drain)
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
        # Knobs: only the latest value per control. Buttons: every edge.
        latest: dict = {}
        ordered = []
        for ev in events:
            ctl = ev[:4]
            if self._ctl_is_button(ctl):
                ordered.append(ev)
            else:
                if ctl not in latest:
                    ordered.append(ctl)
                latest[ctl] = ev
        with self._macroWrites():
            for item in ordered:
                ev = latest[item] if len(item) == 4 else item
                self._ctl_handle(ev)

    def _ctl_is_button(self, ctl: tuple) -> bool:
        return any(b.behavior != "absolute" or b.target.startswith("action.") for b in self._ctl_pick(*ctl))

    def _ctl_mode(self) -> str:
        return "PERFORM" if self._in_perform() else "PATCH"

    def _ctl_pick(self, port, ch, kind, num) -> list:
        return pick_bindings(self._ctl_bindings, port, ch, kind, num,
                             str(getattr(self, "_active_view", "")), self._ctl_mode())

    # -- events --------------------------------------------------------------

    def _ctl_handle(self, ev: tuple) -> None:
        port, ch, kind, num, raw = ev
        self._ctl_moved[(port, ch, kind, num)] = (raw, time.monotonic())
        if self._ctl_learn_target:
            if raw == 0:
                return        # a release or a control at its minimum: wait for a real move
            self._ctl_finish_learn(port, ch, kind, num, raw)
            return
        label = self._ctl_control_label(port, ch, kind, num)
        hits = self._ctl_pick(port, ch, kind, num)
        if not hits:
            self._ctl_set_activity(f"{label} = {raw}  (not assigned)")
            return
        for b in hits:
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
            t = self._ctl_resolver.resolve(b, raw, self._ctl_current(b.target))
            title = self._ctl_target_title(b.target)
            if t is None:
                if self._ctl_resolver.pending_pickup(b):
                    self._ctl_set_activity(f"{label} = {raw} → {title}  (move to pick up)")
                continue
            self._ctl_apply(b.target, t)
            self._ctl_set_activity(f"{label} = {raw} → {title}")

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
        for old in [o for o in self._ctl_bindings if o.same_control(b) and o.context == b.context]:
            self._ctl_bindings.remove(old)
            self._ctl_resolver.forget(old)
        self._ctl_bindings.append(b)
        self._ctl_save()
        self._ctl_set_activity(f"Learned {self._ctl_control_label(port, ch, kind, num)} → "
                               f"{self._ctl_target_title(target)}")
        self.controllersChanged.emit()

    # -- targets -------------------------------------------------------------

    def _ctl_range(self, target: str) -> tuple[float, float]:
        if target.startswith("macro."):
            return -1.0, 1.0
        entry = self._macroEntry(target)
        return (float(entry["min"]), float(entry["max"])) if entry else (0.0, 127.0)

    def _ctl_keys(self, target: str) -> list[str]:
        """Concrete keys a direct edit of `target` touches right now (edited part)."""
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
        lo, hi = self._ctl_range(target)
        if target.startswith("macro."):
            idx = int(target[6:]) - 1
            if not 0 <= idx < len(self.patch_state.macros):
                return None
            v = self.patch_state.macros[idx].value
        else:
            keys = self._ctl_keys(target)
            if not keys:
                return None
            k = keys[0]
            bases = self.patch_state.macro_bases
            v = bases[k] if (k in bases and self._macroLinksFor(k)) else self._readAbsolute(k)
        return max(0.0, min(1.0, (float(v) - lo) / ((hi - lo) or 1.0)))

    def _ctl_apply(self, target: str, t: float) -> None:
        lo, hi = self._ctl_range(target)
        value = lo + (hi - lo) * t
        if target.startswith("macro."):
            if abs(value) <= 1.0 / 127.0:
                value = 0.0      # 0..127 has no middle: CC 63/64 is the macro's center
            try:
                self.setMacro(int(target[6:]), value)
            except ValueError:
                pass
            return
        touched = set()
        for k in self._ctl_keys(target):
            if self._macroLinksFor(k):
                self.patch_state.macro_bases[k] = value
                self._recomputeTarget(k)
            else:
                self._applyAbsolute(k, value)
            touched.add(k)
        if touched:
            self._emitForMacroKeys(touched)

    def _ctl_target_title(self, target: str) -> str:
        if target.startswith("action."):
            return _ACTION_TITLES.get(target, target)
        if target.startswith("macro."):
            try:
                idx = int(target[6:])
                name = self.patch_state.macros[idx - 1].name
            except (ValueError, IndexError):
                return target
            return f"Macro {idx}" + (f" ({name})" if name and name != f"MACRO {idx}" else "")
        entry = self._macroEntry(target)
        base, part = self._splitPart(target)
        if entry and part and base.startswith("part."):
            return entry["title"].replace("Part", f"Part {part}", 1)
        return entry["title"] if entry else target

    def _ctl_control_label(self, port: str, ch: int, kind: str, num: int) -> str:
        if port not in self._ctl_names:
            self._ctl_names[port] = self._ctl_names_for(port)
        name = self._ctl_names[port].get(f"{kind}:{num}")
        base = f"CH{ch + 1} {'CC' if kind == 'cc' else 'NOTE'} {num}"
        return f"{name} · {base}" if name else base

    # -- feedback --------------------------------------------------------------

    def _ctl_update_feedback_timer(self) -> None:
        want = any(self._ctl_feedback_on(k) for k in self._ctl_open)
        if want and not self._ctl_fb_timer.isActive():
            self._ctl_fb_timer.start()
        elif not want and self._ctl_fb_timer.isActive():
            self._ctl_fb_timer.stop()

    def _ctl_feedback_tick(self) -> None:
        """Send each absolute knob its target's value, so it never jumps (endless knobs)."""
        now = time.monotonic()
        view, mode = str(getattr(self, "_active_view", "")), self._ctl_mode()
        for b in self._ctl_bindings:
            if (b.kind != "cc" or b.behavior != "absolute" or b.target.startswith("action.")
                    or b.port not in self._ctl_open or not self._ctl_feedback_on(b.port)):
                continue
            ctl = (b.port, b.channel, b.kind, b.number)
            if b not in pick_bindings(self._ctl_bindings, *ctl, view, mode):
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
                self.seqToggleLiveRecord(not self.seqLiveRecordEnabled)
            elif action.startswith("seq.scene."):
                self.seqLaunchScene(n - 1)
            elif action.startswith("seq.stop_track."):
                self.seqStopTrack(n - 1)
            elif action == "motion.toggle_play":
                state = self.engine.motion.state.value
                self.stopMotion() if state == "playing" else self.playMotion()
            elif action == "motion.toggle_record":
                state = self.engine.motion.state.value
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
            elif action == "playlist.next":
                self.nextPlaylistEntry()
            elif action == "playlist.prev":
                self.prevPlaylistEntry()
            elif action == "panic":
                self.panic()
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
        for i, b in enumerate(self._ctl_bindings):
            out.append({
                "index": i, "control": self._ctl_control_label(b.port, b.channel, b.kind, b.number),
                "port": b.port or "ANY PORT", "online": (not b.port) or b.port in self._ctl_open,
                "target": b.target, "title": self._ctl_target_title(b.target),
                "macro": b.target.startswith("macro."),
                "behavior": b.behavior, "takeover": b.takeover, "lo": b.lo, "hi": b.hi,
                "action": b.target.startswith("action."),
                "context": b.context, "contextTitle": CONTEXT_TITLES.get(b.context, b.context),
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
        actions = []
        if category in ("ALL", "ACTION", ""):
            actions = [a for a in ACTIONS if not q or q in a["title"].lower() or q in a["key"]]
        if category == "MACRO":
            return macros
        if category == "ACTION":
            return actions
        # Fixed parts for mixer-style controls (the catalog's part.* follow the edited part)
        fixed = []
        if category in ("ALL", "PART", ""):
            for e in filter_macro_targets("PART", ""):
                for n in range(1, 17):
                    title = e["title"].replace("Part", f"Part {n}", 1)
                    if not q or q in title.lower():
                        fixed.append({**e, "key": f"{e['key']}@{n}", "title": title})
        return macros + filter_macro_targets(category, query) + fixed + actions

    @pyqtSlot(result="QVariantList")
    def getControlCategories(self) -> list:
        cats = get_macro_categories()
        return cats[:1] + ["MACRO", "ACTION"] + cats[1:]

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
