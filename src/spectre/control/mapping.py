"""MIDI controller bindings: a physical control -> an app target.

Targets share the macro catalog (core.macro_targets), plus "macro.N" for
macro knob N. Values travel as t in 0..1 over the target's range
(catalog min..max; -1..+1 for a macro), so the mapping math never needs
to know what the target is.

Behaviors:
  absolute   0..127 -> lo..hi
  momentary  press (>= 64) -> hi, release -> lo
  toggle     each press flips between lo and hi
  latch      for buttons that latch on the device (127 on one press, 0 on
             the next): on -> hi, off -> lo; for actions every change is a press
Context: "" applies everywhere; "MODE:PATCH" / "MODE:PERFORM" only in that
sound mode; "LAYER:MIXER" / "LAYER:CONTROL" by the surface's mode; "ALT:ON"
while the alt layer is on (the LCXL3's Novation button); "BANK:2" in part
bank 2; a bare word is an app page (activeView, e.g. "SEQUENCER"). Tokens
combine with "&". For one control the most specific active context wins
(see context_rank).
Takeover (absolute only):
  pickup     ignore the control until it reaches/crosses the target's
             current value, so moving a fader never jumps the sound
  scale      move the target proportionally toward the end the control is
             heading for, so both reach it together; 1:1 once they meet
             (for faders, which can't be moved by the app)
  jump       apply immediately
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional

BEHAVIORS = ("absolute", "momentary", "toggle", "latch")
TAKEOVERS = ("pickup", "scale", "jump")
# A target that moved by more than this since our last write was changed
# elsewhere (UI, macro, patch load): the control has to pick it up again.
_MOVED = 1.5 / 127.0
_CATCH = 2.0 / 127.0


@dataclass
class Binding:
    port: str                 # core.midi.port_key(); "" = any port
    channel: int              # 0..15
    kind: str                 # "cc" | "note"
    number: int               # CC or note number
    target: str               # catalog key or "macro.N"
    lo: float = 0.0           # t at control minimum (lo > hi inverts)
    hi: float = 1.0
    behavior: str = "absolute"
    takeover: str = "pickup"
    context: str = ""

    def matches(self, port: str, channel: int, kind: str, number: int) -> bool:
        return ((not self.port or self.port == port) and self.channel == channel
                and self.kind == kind and self.number == number)

    def same_control(self, other: "Binding") -> bool:
        return (self.port, self.channel, self.kind, self.number) == (
            other.port, other.channel, other.kind, other.number)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> Optional["Binding"]:
        try:
            b = cls(port=str(d.get("port", "")), channel=int(d["channel"]) & 0x0F,
                    kind="note" if d.get("kind") == "note" else "cc",
                    number=int(d["number"]) & 0x7F, target=str(d["target"]),
                    lo=_unit(d.get("lo", 0.0)), hi=_unit(d.get("hi", 1.0)),
                    behavior=str(d.get("behavior", "absolute")),
                    takeover=str(d.get("takeover", "pickup")),
                    context=str(d.get("context", "") or ""))
        except (KeyError, TypeError, ValueError):
            return None
        if b.behavior not in BEHAVIORS:
            b.behavior = "absolute"
        if b.takeover not in TAKEOVERS:
            b.takeover = "pickup"
        return b if b.target else None


# Context tokens and how specific they are. A context is tokens joined by
# "&" (e.g. "LAYER:MIXER&MODE:PERFORM&BANK:2"); a bare token is an app page.
_TOKEN_WEIGHT = {"ALT": 16, "LAYER": 8, "BANK": 1, "MODE": 1}
PAGE_WEIGHT = 2


def context_rank(context: str, state: dict) -> int:
    """Specificity of a context in `state` ({PAGE, MODE, LAYER, ALT, BANK}); -1 = not active.

    Every token must hold. A layer (e.g. the LCXL3's DAW Mixer mode)
    outranks everything else, so it takes over the controls it binds; the
    alt layer outranks that.
    """
    if not context:
        return 0
    rank = 0
    for token in context.split("&"):
        kind, sep, value = token.partition(":")
        if not sep:
            if token != state.get("PAGE", ""):
                return -1
            rank += PAGE_WEIGHT
        elif str(state.get(kind, "")) == value:
            rank += _TOKEN_WEIGHT.get(kind, 1)
        else:
            return -1
    return rank


def pick_bindings(bindings, port: str, channel: int, kind: str, number: int, state: dict) -> list:
    """The bindings a control drives right now (all of the most specific context)."""
    best, out = -1, []
    for b in bindings:
        if not b.matches(port, channel, kind, number):
            continue
        r = context_rank(b.context, state)
        if r > best:
            best, out = r, [b]
        elif r == best and r >= 0:
            out.append(b)
    return out if best >= 0 else []


def _unit(v) -> float:
    return max(0.0, min(1.0, float(v)))


@dataclass
class BindingState:
    """Runtime state of one binding (not saved)."""

    picked: bool = False
    last_sent: Optional[float] = None
    prev_t: Optional[float] = None
    pressed: bool = False


@dataclass
class Resolver:
    """Turns raw controller values into target values for one binding."""

    states: dict = field(default_factory=dict)  # id(binding) -> BindingState

    def state(self, b: Binding) -> BindingState:
        return self.states.setdefault(id(b), BindingState())

    def forget(self, b: Binding) -> None:
        self.states.pop(id(b), None)

    def resolve(self, b: Binding, raw: int, current: Optional[float],
                step: float = 0.0) -> Optional[float]:
        """t to write, or None to leave the target alone.

        current: the target's t right now (None when unknown; pickup then
        takes over immediately). step: t size of one target value when the
        target is coarser than the control (pitch env depth: 1/24), so
        rounding to the nearest value doesn't count as moved elsewhere.
        """
        st = self.state(b)
        raw = max(0, min(127, int(raw)))
        if b.behavior in ("momentary", "latch"):
            down = raw >= 64
            if down == st.pressed and st.last_sent is not None:
                return None
            st.pressed = down
            st.last_sent = b.hi if down else b.lo
            return st.last_sent
        if b.behavior == "toggle":
            down = raw >= 64
            was = st.pressed
            st.pressed = down
            if not down or was:
                return None
            # Flip relative to where the target is now (it may have moved)
            ref = current if current is not None else (st.last_sent if st.last_sent is not None else b.lo)
            st.last_sent = b.lo if abs(ref - b.hi) < abs(ref - b.lo) else b.hi
            return st.last_sent

        t = b.lo + (b.hi - b.lo) * raw / 127.0
        slack = max(0.0, float(step)) / 2      # rounding to the target's own steps
        if b.takeover == "scale" and current is not None:
            return self._scale(b, st, raw / 127.0, current, slack)
        if b.takeover == "jump" or current is None:
            st.picked, st.prev_t, st.last_sent = True, t, t
            return t
        if st.picked and st.last_sent is not None and abs(current - st.last_sent) > _MOVED + slack:
            st.picked = False          # moved elsewhere: pick it up again
        if not st.picked:
            crossed = st.prev_t is not None and (st.prev_t - current) * (t - current) <= 0
            if abs(t - current) <= _CATCH + slack or crossed:
                st.picked = True
        st.prev_t = t
        if not st.picked:
            return None
        st.last_sent = t
        return t

    @staticmethod
    def _scale(b: Binding, st: BindingState, u: float, current: float,
               slack: float = 0.0) -> Optional[float]:
        """Smooth scaling, in control space u (0..1 along the control's travel)."""
        span = b.hi - b.lo
        if span == 0:
            return None
        cur_u = max(0.0, min(1.0, (current - b.lo) / span))
        prev = st.prev_t
        st.prev_t = u
        if st.picked and st.last_sent is not None and abs(current - st.last_sent) > _MOVED + slack:
            st.picked = False          # moved elsewhere: converge again
        # Lock 1:1 only where the control meets the value (never snap it back)
        met = (abs(u - cur_u) < 0.5 / 127.0 + slack / abs(span)
               or (prev is not None and (prev - cur_u) * (u - cur_u) <= 0))
        if not st.picked and met:
            st.picked = True
        if st.picked:
            new_u = u
        elif prev is None or u == prev:
            return None                # need a direction first
        elif u > prev:
            new_u = cur_u + (1.0 - cur_u) * (u - prev) / max(1e-6, 1.0 - prev)
        else:
            new_u = cur_u - cur_u * (prev - u) / max(1e-6, prev)
        new_u = max(0.0, min(1.0, new_u))
        if abs(new_u - u) < 0.5 / 127.0:
            st.picked = True
        st.last_sent = b.lo + span * new_u
        return st.last_sent

    def pending_pickup(self, b: Binding) -> bool:
        st = self.states.get(id(b))
        return b.behavior == "absolute" and b.takeover == "pickup" and not (st and st.picked)
