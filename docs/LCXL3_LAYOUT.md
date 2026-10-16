# Launch Control XL3 layout

Design spec for the Novation Launch Control XL3 surface. Device messages: `src/spectre/control/lcxl3.py`
and Novation's *Launch Control XL 3 Programmer's Reference Guide*.

## Principle

**One position, one meaning.** A control does the same thing on every app page. The only thing
that changes a control's meaning is something you do on purpose and can see:

- the device's own **DAW Control / DAW Mixer** mode buttons (sound shaping vs mixing);
- the **Novation button** layer (context knobs, page shortcuts, scenes, pitch envelope).

The screen and LEDs always say what is under your hand, and moving a control shows its name
and value.

## Global navigation (both modes)

| Control | Normal | Novation layer |
|---|---|---|
| Page ◀▶ | Part/track bank 1–8 / 9–16 | Previous / next app page |
| Track ◀▶ | Previous / next part/track | Previous / next scene |
| Play | Transport play/stop | Launch the selected scene |
| Record | Record | Stop the selected scene |

- **The bank is global.** Perform, Sequencer, Live and the mixer all show the same bank, and the
  faders/strips follow it.
- **The cursor keeps its slot across banks:** part 3 selected + Page ▶ → part 11. Track ▶ from
  slot 8 goes to slot 9 and turns the bank (and back), so the selection is always on screen.
- **One cursor for parts and tracks:** part n and track n are selected together (the default
  track → part pairing). Track ◀▶ never selects tones; tones have their own buttons.
- **Stop scene** stops only the clips of that scene; other clips keep playing.

## DAW Control mode (sound)

### Knobs

| | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| **Row A** | Macro 1 | Macro 2 | Macro 3 | Macro 4 | Macro 5 | Macro 6 | Macro 7 | Macro 8 |
| **Row B** | LFO1 Rate | LFO1 Pitch | LFO1 Filter | LFO1 Amp | LFO2 Rate | LFO2 Pitch | LFO2 Filter | LFO2 Amp |
| **Row C** | Cutoff | Resonance | Key Follow | Filter Env Depth | Pitch Env Depth | Fine Tune | Portamento | Analog Feel |

- Row C is the row nearest the hand, so it holds the most-used controls.
- The filter knobs (Cutoff, Resonance, Key Follow, Filter Env Depth) write the tones' own filter
  values (`tone.sel.*`), not the patch offsets: on JUNO PCM the selected tone, or all tones when
  the page's link switch is on; on VA, Wavetable and Vector every tone (their filter is a master
  filter). Key Follow sits next to Cutoff/Resonance so the two env depths stay side by side.
- Fine Tune follows what the page offers:

  | Page | Auto Detune off | Auto Detune on |
  |---|---|---|
  | PCM | Selected tone (all when the page's link switch is on) | Auto Detune amount |
  | VA | Selected oscillator (the PCM link switch doesn't apply) | Auto Detune amount |
  | Wavetable / Vector | Master fine tune | Master fine tune |

  The master fine tune moves all tones together and keeps their detune; Auto Detune spreads
  around it. The PCM page has its own Auto Detune switch: while on, its FINE TUNE row is the
  detune amount, like the knob.
- LFO depths and the other per-tone rows act on all tones (`tone.all.*`).
- Macro parameter stacks replace per-page MFX knobs.

### Faders

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|
| Filter A | Filter D | Filter S | Filter R | Amp A | Amp D | Amp S | Amp R |

See [Envelope faders](#envelope-faders) for what A/D/S/R mean on the Juno's envelopes.

### Buttons

| | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| **Top** | Tone 1 | Tone 2 | Tone 3 | Tone 4 | Stop selected track | Stop all clips | Setlist ◀ | Setlist ▶ |
| **Bottom** | Clip 1 | Clip 2 | Clip 3 | Clip 4 | Clip 5 | Clip 6 | Clip 7 | Clip 8 |

- Tone buttons select the tone to edit.
- Clips are the 8 clips of the **selected track**; LEDs show empty / loaded / playing / queued.
  A track holding one-shot samples turns this row into a pad bank.
- Stop all clips keeps the transport running.
- Dropped on purpose: scene launch / stop-track rows (the Live page covers them), page-jump
  buttons (Novation layer), tone mute (faders and the screen cover it), panic (the touchscreen is
  closer), arpeggio (the Juno has its own button).

## DAW Mixer mode (balance)

Same physical layout in Patch and Perform mode. Slots are tones 1–4 in Patch mode and the parts of
the current bank in Perform mode.

| Control | Meaning |
|---|---|
| Faders | Level per slot |
| Row A | Pan per slot |
| Row B | The 8 routing/send/output sliders of the **selected** tone/part (as on the Routing page) |
| Row C | Master FX: Chorus Rate, Depth, Feedback, Predelay · Reverb Time, Damp, Tone, Predelay |
| Top buttons | Solo / select per slot |
| Bottom buttons | Mute per slot |

- Chorus and reverb levels are not on row C: the routing sets them.
- Reverb diffusion is left out (least audible).
- In Patch mode, faders 5–8 are MFX out, chorus level, reverb level and patch level; knob A8 is the
  patch pan. The other slot 5–8 controls do nothing in the mixer.
- Row B in Perform mode: tone output level, then the part's chorus/reverb sends (they apply instead of
  the tone's), MFX out/chorus/reverb sends, chorus and reverb levels. In Patch mode the tone's own
  sends take slots 2–3.

## Novation button layer

The Novation button (CC 104) turns on one layer. It is the same layer however it is turned on.

### Tap vs hold

- The layer turns on **at press**, so a control used at once already acts on the layer.
- On release:
  - **tap** (under ~350 ms, nothing touched or moved) → the layer latches on, or off if it was latched;
  - **long press, or any control touched/moved while held** → momentary: the layer turns off.

### What changes

| Control | In the layer |
|---|---|
| Row A | The current page's 8 context knobs (pages without context: unchanged) |
| Faders 1–4 | DAW Control mode: pitch envelope A/D/S/R (faders 5–8 stay on the amp envelope); DAW Mixer mode: unchanged (levels) |
| 16 buttons | Page shortcuts (below) |
| Page ◀▶, Track ◀▶, Play, Record | See [Global navigation](#global-navigation-both-modes) |

While latched, the transport is not available: leave the layer to stop the song.

### Page shortcuts

Same order as the touchscreen's page menu, lit in the page category colours.

| | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| **Top** | Juno PCM | Vector | Wavetable | VA | Mod Matrix | Step LFO | MSEG | Routing |
| **Bottom** | MFX | Master FX | Macros | Arpeggio | Performance | Sequencer | Live | Setlist |

Librarian, MIDI Learn, Hardware and System have no shortcut (touchscreen).

### Showing the layer

The Novation button has no LED, so the layer shows itself through:

- **Page buttons** in their category colour: Synth sky `#38bdf8`, Mod & FX indigo `#818cf8`,
  Perform orchid `#d08cfb`;
- **Context knobs** in a colour macros never use;
- **Play / Record** in colours that cannot be mistaken for transport play / record;
- **The permanent screen line**, e.g. `CTX · SCENE 3` (title field, 16 characters; the scene
  number alone if it doesn't fit).

## Touch events

**Off.** The LCXL3 can report touch on/off (feature message `B6 47 7F`, CC 127/0 on channel 15,
numbered like the control), but tested on hardware (2026-10-15) its knobs have no touch sensor:
"touch on" comes when a control starts moving and "touch off" when it stops, a pair around every
step or two of a slow turn. Treated as grabs they reset the takeover on every step, so the app
sends `B6 47 00` at connect.

What touch was meant for works from movement instead:

- **Moving shows** the control's name and value on the LCXL3 screen. On the touchscreen, the
  matching control of the current page (slider, context strip card, mixer strip) gets a white
  outline; when the page has none, a toast shows the name and value. Both stay a moment after the
  last move.
- **Takeover** works from the values alone (pickup / scale).
- **Envelope faders** keep their shape snapshot until the curve changes some other way (editor,
  patch load), so no grab signal is needed.
- **The Novation hold rule** counts a control moved while held.

The app still understands touch messages, for a device with real touch sensing.

## Envelope faders

The Juno envelopes have 4 times and 5 levels: T1 L0→L1, T2 L1→L2, T3 L2→L3 (sustain), T4 L3→L4
(release). Time values are strongly exponential.

Each envelope (filter, amp, pitch) is in one of two modes, with a switch next to its preview on
the UI. The switch follows the selected tone, or all tones when tones are linked (always linked in
Wavetable, Vector and VA).

### ADSR mode

The envelope is a plain ADSR: L0 = 0, L1 = max, T1 = A, T2 = D, T3 = 0, L2 = L3 = S, T4 = R,
L4 = 0. The faders write these directly.

Pitch (bipolar levels): L0 = 0 (centre), L1 = +max, L2 = L3 = S, L4 = 0; Pitch Env Depth (row C)
scales and inverts the whole envelope.

### Normal mode

The patch's own curve is kept and the faders move **groups of segments** around the peak
(the higher of L1 and L2):

| Fader | Moves |
|---|---|
| A | Every time up to the peak (T1, plus T2 when L2 is the peak) |
| D | Every time from the peak to sustain (T2 + T3, or T3 alone) |
| S | L3; L2 keeps its relative position between the peak and L3 |
| R | T4 |

All times in a group move by the **same delta**, which keeps the curve's character (the time scale
is exponential, so equal deltas ≈ equal ratios). Deltas apply to a **snapshot of the curve**
(kept until the curve changes some other way), so clamping at 0/127 never flattens the shape over repeated moves.

### Switching

- **The mode is derived from the curve**: an envelope with the ADSR shape is in ADSR mode. Patches
  loaded from the Juno need no stored flag.
- **Normal → ADSR** stores the original curve (app patch file and session; not in the Juno's
  memory) and converts: A and D take the longest segment of their group, S = L3, R = T4.
- **ADSR → Normal** restores the original exactly; edits made in ADSR mode are dropped.
- **A stored original exists only while in ADSR mode, and only if the switch put it there.**
  - A curve-editor edit that keeps the ADSR shape keeps the mode and the stored original.
  - An edit that breaks the shape makes the envelope Normal and **discards** the stored original
    (the edited curve is the new original).
  - Shaping a Normal curve into exact ADSR form turns the switch on, with nothing stored.
- Saving a patch to the Juno while in ADSR mode saves the ADSR curve; the UI should say the
  original is kept only in Spectre's file.
- INIT / new patches start in ADSR mode.

## Build order

Each step is usable on its own:

1. Catalog and fixes: filter key follow target; amp sustain must move L2 like the filter path does
   (`ui/bridge/macros.py` writes `tva_l3` directly).
2. Global bank + one part/track cursor; Page ◀▶ / Track ◀▶ in both modes.
3. New preset layout (Control and Mixer), clip row with clip-state LEDs, stop track / stop all.
4. Novation layer: tap/hold, context row, page shortcuts, scene select/launch/stop, LEDs, screen line.
5. Touch events (later turned off: the LCXL3 has no touch sensor, see above).
6. Envelope modes: ADSR switch, segment groups, snapshots, stored originals; pitch envelope on the layer.

## Not yet verified on hardware

`tools/lcxl3_probe.py` puts the device in DAW mode and prints everything it sends. Open points:

- whether Shift and the Solo / Mute buttons report in DAW mode;
- whether Play / Record take LED colours;
- how much of the permanent screen's title line is visible.
