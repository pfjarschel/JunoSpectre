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
sound mode; any other value is an app page (activeView, e.g. "SEQUENCER").
For one control the most specific matching context wins: page, then
mode, then everywhere (see pick_bindings).
Takeover (absolute only):
  pickup     ignore the control until it reaches/crosses the target's
             current value, so moving a fader never jumps the sound
  jump       apply immediately
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional

BEHAVIORS = ("absolute", "momentary", "toggle", "latch")
TAKEOVERS = ("pickup", "jump")
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


def context_rank(context: str, view: str, mode: str) -> int:
    """How specifically a binding's context matches: 2 page, 1 mode, 0 everywhere, -1 no."""
    if not context:
        return 0
    if context.startswith("MODE:"):
        return 1 if context[5:] == mode else -1
    return 2 if context == view else -1


def pick_bindings(bindings, port: str, channel: int, kind: str, number: int,
                  view: str, mode: str) -> list:
    """The bindings a control drives right now (all of the most specific context)."""
    best, out = -1, []
    for b in bindings:
        if not b.matches(port, channel, kind, number):
            continue
        r = context_rank(b.context, view, mode)
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

    def resolve(self, b: Binding, raw: int, current: Optional[float]) -> Optional[float]:
        """t to write, or None to leave the target alone.

        current: the target's t right now (None when unknown; pickup then
        takes over immediately).
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
        if b.takeover == "jump" or current is None:
            st.picked, st.prev_t, st.last_sent = True, t, t
            return t
        if st.picked and st.last_sent is not None and abs(current - st.last_sent) > _MOVED:
            st.picked = False          # moved elsewhere: pick it up again
        if not st.picked:
            crossed = st.prev_t is not None and (st.prev_t - current) * (t - current) <= 0
            if abs(t - current) <= _CATCH or crossed:
                st.picked = True
        st.prev_t = t
        if not st.picked:
            return None
        st.last_sent = t
        return t

    def pending_pickup(self, b: Binding) -> bool:
        st = self.states.get(id(b))
        return b.behavior == "absolute" and b.takeover == "pickup" and not (st and st.picked)
