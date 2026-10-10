"""JUNO-DS signal routing model (Parameter Guide p17/p23, MIDI Implementation).

Hardware facts (verified on a JUNO-DS, 2026-10-10):
- Output assign wire values: 0=MFX, 1=L+R, 5=L, 6=R (2..4 and 7..12 unused).
  Patch Output Assign 13=TONE defers to each tone; Part Output Assign 13=PATCH
  defers to the patch.
- Each tone stores two chorus/reverb send pairs: 0x0D/0x0E apply while its
  sound goes into the MFX, 0x0F/0x10 while it goes direct. The route in
  effect picks the pair; the panel only shows that one.
- Structure types 2..10 (wire 1..9) merge tone 1 into tone 2 and tone 3 into
  tone 4, so tones 1 and 3 follow tone 2's and tone 4's output settings.
- An MFX of type THRU still passes its input through its output level/sends.
- PERFORM: a part assign other than PATCH overrides the patch route, and
  then the part's chorus/reverb sends apply instead of the tone sends.

build_graph() follows the signal from the tones to the output; a wire is
active only when sound actually travels it.
"""

from __future__ import annotations

from typing import Any, Optional

ASSIGN_MFX = 0
ASSIGN_LR = 1
ASSIGN_L = 5
ASSIGN_R = 6
ASSIGN_DEFER = 13  # patch: TONE, part: PATCH
DIRECT_ASSIGNS = (ASSIGN_LR, ASSIGN_L, ASSIGN_R)
TONE_ASSIGNS = (ASSIGN_MFX, ASSIGN_LR, ASSIGN_L, ASSIGN_R)
ASSIGN_LABELS = {ASSIGN_MFX: "MFX", ASSIGN_LR: "L+R", ASSIGN_L: "L", ASSIGN_R: "R"}

# Tone send pair offsets by route: into MFX / direct
TONE_SEND_OFFSETS = {False: (0x0D, 0x0E), True: (0x0F, 0x10)}
TONE_SEND_ATTRS = {False: ("chorus_send", "reverb_send"),
                   True: ("chorus_send_direct", "reverb_send_direct")}

# Performance MFX Structure TYPE01..16 (wire 0..15): unit -> unit it feeds
# in series (Parameter Guide p24). Every unit feeds at most one other.
MFX_STRUCTURE_NEXT: list[dict[int, int]] = [
    {}, {1: 2}, {1: 3}, {2: 3}, {2: 1}, {3: 1}, {3: 2},
    {1: 3, 2: 3}, {2: 1, 3: 1}, {1: 2, 3: 2},
    {1: 2, 2: 3}, {1: 3, 3: 2}, {2: 3, 3: 1}, {2: 1, 1: 3}, {3: 1, 1: 2}, {3: 2, 2: 1},
]

CHORUS_TO_MAIN = (0, 2)
CHORUS_TO_REVERB = (1, 2)


def normalize_assign(value: int) -> int:
    """Wire value as one of MFX/L+R/L/R (unused values read as MFX)."""
    v = int(value)
    return v if v in DIRECT_ASSIGNS else ASSIGN_MFX


def is_direct(assign: int) -> bool:
    return int(assign) in DIRECT_ASSIGNS


def output_owner(tone_index: int, structure_12: int, structure_34: int) -> int:
    """Tone whose output settings a tone actually uses (structure pairs)."""
    if tone_index == 1 and int(structure_12) > 0:
        return 2
    if tone_index == 3 and int(structure_34) > 0:
        return 4
    return tone_index


def patch_route(common, tone) -> int:
    """Route a tone's sound takes inside its patch (patch assign, else tone assign)."""
    pa = int(getattr(common, "patch_output_assign", ASSIGN_DEFER))
    if pa != ASSIGN_DEFER:
        return normalize_assign(pa)
    return normalize_assign(tone.output_assign)


def tone_send_attrs(common, tone) -> tuple[str, str]:
    """ToneState attributes holding the send pair the Juno uses right now."""
    return TONE_SEND_ATTRS[is_direct(patch_route(common, tone))]


def tone_send_offsets(common, tone) -> tuple[int, int]:
    return TONE_SEND_OFFSETS[is_direct(patch_route(common, tone))]


def tone_sends(common, tone) -> tuple[int, int]:
    cho, rev = tone_send_attrs(common, tone)
    return int(getattr(tone, cho)), int(getattr(tone, rev))


def mfx_chain(entry_slot: int, structure: int) -> list[int]:
    """MFX units the signal passes through from entry_slot (1..3)."""
    nxt = MFX_STRUCTURE_NEXT[max(0, min(15, int(structure)))]
    chain = [max(1, min(3, int(entry_slot)))]
    while chain[-1] in nxt and nxt[chain[-1]] not in chain:
        chain.append(nxt[chain[-1]])
    return chain


def _edge(active: bool, level: int = 0, tones: Optional[list[int]] = None) -> dict:
    return {"active": bool(active), "level": int(level) if active else 0,
            "tones": list(tones or [])}


def _scaled(a: int, b: int) -> int:
    return (int(a) * int(b) + 63) // 127


def build_graph(state, *, mfx: dict, chorus: dict, reverb: dict,
                part=None, mfx_label: str = "MFX") -> dict[str, Any]:
    """Follow the sound of `state` (a PatchState) to the output.

    mfx: {type, dry, cho, rev} of the unit whose outputs reach the mixer
    (the end of the chain in PERFORM). chorus: {type, level, toReverb}.
    reverb: {type, level}. part: the PerfPartState in PERFORM, else None.

    Edge keys: in->part (PERFORM), in->mfx, in->out, in->cho, in->rev,
    mfx->out, mfx->cho, mfx->rev, cho->out, cho->rev, rev->out. "in" is
    the tones in PATCH mode and the part in PERFORM.
    """
    common = state.common
    s12 = int(getattr(common, "structure_12", 0))
    s34 = int(getattr(common, "structure_34", 0))
    patch_assign = int(getattr(common, "patch_output_assign", ASSIGN_DEFER))
    part_assign = int(getattr(part, "output_assign", ASSIGN_DEFER)) if part is not None else ASSIGN_DEFER
    part_on = part is None or (not getattr(part, "muted", False) and int(getattr(part, "volume", 127)) > 0)
    part_dry = int(getattr(part, "dry_send", 127)) if part is not None else 127
    # Part sends replace the tone sends only while the part assign overrides
    # the patch; with PATCH the patch's own sends play (factory performances
    # keep part sends at 0 and still have reverb).
    part_override = part_assign != ASSIGN_DEFER

    tones_out = []
    to_mfx, to_out, to_cho, to_rev = [], [], [], []
    lv = {"mfx": 0, "out": 0, "cho": 0, "rev": 0}
    for t in state.tones:
        i = int(t.tone_index)
        owner_i = output_owner(i, s12, s34)
        owner = state.tones[owner_i - 1]
        route_in_patch = patch_route(common, owner)
        route = normalize_assign(part_assign) if part_override else route_in_patch
        cho, rev = tone_sends(common, owner)
        sounding = part_on and not t.muted and int(t.level) > 0
        if part_override:
            locked_by = "part"
        elif patch_assign != ASSIGN_DEFER:
            locked_by = "patch"
        elif owner_i != i:
            locked_by = "structure"
        else:
            locked_by = ""
        tones_out.append({
            "index": i, "sounding": sounding, "owner": owner_i, "lockedBy": locked_by,
            "assign": normalize_assign(t.output_assign), "route": route,
            "routeLabel": ASSIGN_LABELS[route], "direct": is_direct(route),
            "pairDirect": is_direct(route_in_patch),
            "level": int(owner.output_level), "chorusSend": cho, "reverbSend": rev,
        })
        if not sounding:
            continue
        out_level = _scaled(owner.output_level, part_dry)
        if out_level > 0:
            if is_direct(route):
                to_out.append(i); lv["out"] = max(lv["out"], out_level)
            else:
                to_mfx.append(i); lv["mfx"] = max(lv["mfx"], out_level)
        if part_override:
            c, r = int(getattr(part, "chorus_send", 0)), int(getattr(part, "reverb_send", 0))
        else:
            c, r = cho, rev
        if c > 0:
            to_cho.append(i); lv["cho"] = max(lv["cho"], c)
        if r > 0:
            to_rev.append(i); lv["rev"] = max(lv["rev"], r)

    any_sound = any(t["sounding"] for t in tones_out)
    edges = {
        "in->mfx": _edge(bool(to_mfx), lv["mfx"], to_mfx),
        "in->out": _edge(bool(to_out), lv["out"], to_out),
        "in->cho": _edge(bool(to_cho), lv["cho"], to_cho),
        "in->rev": _edge(bool(to_rev), lv["rev"], to_rev),
    }
    if part is not None:
        edges["in->part"] = _edge(any_sound, 127, [t["index"] for t in tones_out if t["sounding"]])

    # MFX passes its input even as THRU
    mfx_in = edges["in->mfx"]["active"]
    m_dry, m_cho, m_rev = int(mfx.get("dry", 0)), int(mfx.get("cho", 0)), int(mfx.get("rev", 0))
    edges["mfx->out"] = _edge(mfx_in and m_dry > 0, m_dry)
    edges["mfx->cho"] = _edge(mfx_in and m_cho > 0, m_cho)
    edges["mfx->rev"] = _edge(mfx_in and m_rev > 0, m_rev)

    cho_in = edges["in->cho"]["active"] or edges["mfx->cho"]["active"]
    c_type, c_level, c_sel = int(chorus.get("type", 0)), int(chorus.get("level", 0)), int(chorus.get("toReverb", 0))
    cho_on = c_type > 0 and c_level > 0
    edges["cho->out"] = _edge(cho_in and cho_on and c_sel in CHORUS_TO_MAIN, c_level)
    edges["cho->rev"] = _edge(cho_in and cho_on and c_sel in CHORUS_TO_REVERB, c_level)

    rev_in = edges["in->rev"]["active"] or edges["mfx->rev"]["active"] or edges["cho->rev"]["active"]
    r_type, r_level = int(reverb.get("type", 0)), int(reverb.get("level", 0))
    rev_on = r_type > 0 and r_level > 0
    edges["rev->out"] = _edge(rev_in and rev_on, r_level)

    nodes = {
        "mfx": {"label": mfx_label, "hasInput": mfx_in, "on": True, "thru": int(mfx.get("type", 0)) == 0},
        "cho": {"label": "CHORUS", "hasInput": cho_in, "on": cho_on},
        "rev": {"label": "REVERB", "hasInput": rev_in, "on": rev_on},
        "out": {"label": "OUTPUT", "hasInput": any(
            edges[k]["active"] for k in ("in->out", "mfx->out", "cho->out", "rev->out"))},
    }
    graph = {"perform": part is not None, "tones": tones_out, "edges": edges, "nodes": nodes,
             "patchAssign": patch_assign, "partAssign": part_assign,
             "structure12": s12, "structure34": s34}
    graph["notes"] = _notes(graph, any_sound, part)
    return graph


def _notes(g: dict, any_sound: bool, part) -> list[dict]:
    e, n = g["edges"], g["nodes"]
    notes: list[dict] = []

    def add(kind, severity, title, description):
        notes.append({"type": kind, "severity": severity, "title": title, "description": description})

    if part is not None and (getattr(part, "muted", False) or int(getattr(part, "volume", 127)) == 0):
        add("PART_SILENT", "caution", "Part is silent",
            "This part is muted or at level 0, so nothing below is heard.")
    elif any_sound and not n["out"]["hasInput"]:
        add("NO_OUTPUT", "warning", "Nothing reaches the output",
            "Every path ends at a level of 0 or at an effect that is OFF.")
    if n["cho"]["hasInput"] and not n["cho"]["on"]:
        add("CHORUS_OFF", "caution", "Chorus is OFF",
            "Sound is sent to the chorus, but its type is OFF or its level is 0, so those sends are silent.")
    if n["rev"]["hasInput"] and not n["rev"]["on"]:
        add("REVERB_OFF", "caution", "Reverb is OFF",
            "Sound is sent to the reverb, but its type is OFF or its level is 0, so those sends are silent.")
    if g["partAssign"] != ASSIGN_DEFER:
        add("PART_OVERRIDE", "info", "Part output overrides the patch",
            f"Part output is {ASSIGN_LABELS[normalize_assign(g['partAssign'])]}: "
            "the patch and tone routing is ignored and the part's own sends apply.")
    elif g["patchAssign"] != ASSIGN_DEFER:
        add("PATCH_OVERRIDE", "info", "Patch output overrides the tones",
            f"Patch output is {ASSIGN_LABELS[normalize_assign(g['patchAssign'])]}: "
            "tone output assigns are ignored (set it to TONE to route tones separately).")
    for t, s in ((1, g["structure12"]), (3, g["structure34"])):
        if s > 0:
            add("STRUCTURE", "info", f"Tone {t} follows Tone {t + 1}",
                f"Structure type {s + 1} merges tones {t} and {t + 1}: tone {t} uses tone {t + 1}'s output settings.")
    feeds = [k for k in ("in->rev", "mfx->rev", "cho->rev") if e[k]["active"]]
    if len(feeds) >= 2 and n["rev"]["on"]:
        names = {"in->rev": "tones", "mfx->rev": "MFX", "cho->rev": "chorus"}
        add("REVERB_STACK", "info", "Reverb fed from several places",
            "Reverb receives " + ", ".join(names[k] for k in feeds) + "; their levels add up.")
    if e["cho->rev"]["active"]:
        add("CHORUS_MONO_SUM", "info", "Chorus feeds the reverb in mono",
            "The chorus output sent to the reverb is summed to mono.")
    return notes
