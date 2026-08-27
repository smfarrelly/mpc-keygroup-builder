# MPC Key 37 field review

**Review unit:** Steve Farrelly's MPC Key 37

**Review status:** Living document, updated from hands-on testing

**Current observation window:** August 25–27, 2026

**Observed MPC firmware:** 3.9.1.2

**Hardware acceptance posture:** New acceptance sessions are deferred; completed
results remain authoritative.

## What this review is

This is a descriptive review of the MPC Key 37 as it is actually being used:
as a standalone Scratchpad, a host for converted sample instruments, a Drum
Program performance surface, and the MIDI center of a small Volca rig. It is
not a specification recap or a claim that every MPC feature has been tested.

The review separates three kinds of evidence:

- **Observed:** directly heard or operated on the Key 37.
- **Inspected:** confirmed afterward in saved MPC projects or program files.
- **Deferred:** useful follow-up that has deliberately not been treated as a
  failure.

That distinction matters. Several apparent problems during testing were not
broken programs: pad colors were hidden while Browser remained open, large
Keygroups took longer to load than expected, some factory-derived kits really
contained only 12 pads, and several melodic programs were simply mapped below
the Key 37's default physical register.

## Overall assessment so far

The Key 37 is already succeeding at the central job: it can move quickly from
sound selection to a saved multi-part idea without a computer timeline. Drum
Programs, Keygroups, semantic pad colors, velocity layers, MIDI tracks, and
external clock have all worked in practical tests. A four-bar Scratchpad idea
was recorded quickly, and later project inspection confirmed saved drum, bass,
and Wurli events.

Its strongest quality is breadth without requiring the laptop during music
making. The same unit can provide a full keybed instrument, a banked drum and
one-shot surface, a sequencer, and the master clock for external instruments.
The cost of that breadth is contextual behavior: the selected track, input
port, record-arm mode, Browser state, pad bank, and device-level preferences
can all change what the same physical control appears to do.

The practical verdict is positive but specific: the Key 37 is an excellent
idea-generation center once a known-good project and routing posture exist. It
is less convincing when approached as though its pads and keyboard were two
permanently independent controllers. They can be separated usefully, but the
selected-track context still matters.

## Sound-library and program experience

### Drum Programs

Drum Program compatibility has been the most consistently successful area.
The original Vinyl SP, Vinyl Drums, and Vinyl Drum Machines programs all load
and play correctly. Vinyl SP From Mars 01 remains the selected main kit, while
the other two are strong alternatives rather than failed runners-up.

The custom color work survives real use. Kicks, snares, hats, claps, rims,
cymbals, percussion, and effects can carry distinct semantic colors, and those
colors persist after saving and reloading. The important usability detail is
that the physical pads may continue to look generic while Browser is open.
Leaving Browser reveals the assigned colors. Early reports that every pad was
yellow or green were therefore UI-context observations, not serialization
failures.

`FG Vinyl Shots 04 Eight Bank` is a complete success. All 128 pads across Banks
A–H passed, including the dedicated kick/snare and closed/open-hat banks. Its
colors, samples, choke behavior, and saved sequence survived reload. It is the
selected one-shot/accent program for the Scratchpad.

`FG Vinyl Kit Banks 01` also validates the bank-as-kit idea. All eight source
families worked, the same recorded pattern played successfully on Banks A, B,
C, and G, and the result was musically impressive. This test also answered a
design question: preserving each source kit's native pad order is useful enough
that a stricter normalized layout is unnecessary.

The Ableton conversion wave produced 27 Drum Programs. Twenty-five were
accepted as passes. The two warnings—Modern Oddities Hardware Glitch and S950
Hard Glitch—preserve ambiguous choke behavior from their source racks rather
than exposing broken MPC conversion. The two SP-1200 Factory kits contain 12
intentional source pads; empty A13–A16 positions are not missing data.

### Velocity-layered drums

Velocity-layered pads are one of the most promising musical findings. The first
layered kit made an immediately favorable impression, even though the hat choke
test was difficult to hear. The concept was described as excellent: playing
harder can move through related timbres instead of merely changing volume.

`FG Vinyl Layered Main 02` improved the coherence of those transitions and is
retained as an expressive alternate. It did not replace Vinyl SP as the main
kit, which is a useful editorial outcome: expressiveness and immediacy are
different roles, and the project does not need to force one program to win both.

The newer `FG Vinyl Layered Banks 03` extends the design across four banks but
has not been hardware-reviewed. Its local and on-card structural results are
strong; its musical acceptance is explicitly deferred.

### Keygroups and the 37-key register

The keybed has been effective for choosing sounds by feel rather than by name.
The resulting Scratchpad palette is:

- Mirage Pluck Bass as the primary bass.
- Juno Sub Smooth as a slower bass-pad layer.
- Mirage Wurli as the principal keys/chord sound.
- Emulator Dark FM as the lead.
- Kawaii Dreams Glass Howl as the dedicated pad.

Several alternatives remain memorable rather than discarded. Mirage Upright
Bass has breathy, vinyl-like character; Echo Square is a strong additional
bass; Muted Guitar works better as a lead voice than its name initially
suggested; Mirage Dark Piano and OB Warm Keys were also liked.

Register placement is the main Keygroup caveat. Warm Bass only began to speak
after transposing down three octaves, and the first five SP-1200 chromatic
conversions showed the same low-register behavior. Their samples were intact;
the mapping simply placed useful roots below the default physical range. A
+24-semitone rebuild moved them close to the desired position, and listening
suggested moving them one more octave to the right. A +36-semitone NR2 set was
built as the intended promotion target, but its final hardware acceptance is
deferred.

Large programs can also create a misleading pause. Loading the Keygroup named
Ultimate initially appeared to hang, then completed normally. For this unit,
an ambiguous loading interval should not be called a crash until the operation
has been given adequate time.

## Scratchpad workflow

The minimal Scratchpad proved the core premise. With dedicated inputs and Multi
record arm, a short four-bar idea was captured with drums, bass, and keys.
Saved project inspection confirmed actual sequence events rather than only live
monitoring. This is the most important test result because it measures the
instrument as a composition environment, not merely as a program browser.

The current protected master contains two Drum tracks, five selected Keygroup
tracks, a placeholder Keygroup named Clip, and an Audio track. The placeholder
is not a real MPC 3 Clip track and should be removed or repurposed only in a
disposable Jam copy. MPC Pro Pack is not owned, so modern Clip Workflow is
purchase-gated rather than malfunctioning.

Default project behavior deserves attention. Factory sounds such as Hype
Almighty and Trap Kit may appear as automatically supplied tracks when starting
from a default project. Exact-track tests therefore need to verify what the MPC
created automatically instead of assuming every visible track was added by the
user.

The protected Scratchpad master and its companion ProjectData remain intact.
Completed test projects were removed from the live card only after verified
external backup, leaving a much clearer Projects folder.

## Pads, keyboard, and routing

Routing is the area where the Key 37 requires the most learned procedure.

Drum Split does not mean "pads play drums while keys play the selected melodic
track." It divides MIDI note ranges. In the controlled test, Bank A pads played
Vinyl SP, other pad banks reached low Wurli notes, and low keyboard notes played
drums. That can be musically usable, but it is not permanent physical-controller
separation.

The closest known-good posture is more explicit:

- Melodic track input: `MPC Keyboard`.
- Drum track input: `MPC Pads`.
- Rec Arm Behaviour: `Multi`.
- Drum Split: off.
- Keep the Drum track selected while using independent pads and keys.

With the Drum track selected, pads play the Drum Program and keys play Wurli as
intended. With Wurli selected, the pads follow the melodic context: Bank A can
sound Wurli notes, other banks are not useful as the drum surface, and the Drum
Program's colors are absent. Disabling the device-level MPC Pads `Global`
preference did not make all pad banks permanently independent.

Saved project inspection confirms that the dedicated input-port assignments
persist in the XPJ. The MPC Pads `Global` choice does not appear to be stored
there; it should be treated as a machine preference that may need separate
verification after reload.

This behavior is not a reason to reject the Key 37. It changes the design of a
good template: make the desired routing explicit, preserve a known selected
track, and avoid promising that track focus has no effect.

## Saving, reloading, and storage

Save/reload behavior has been reliable in the workflows that matter most.
Samples, Drum Program colors, bank layouts, mute groups, and recorded sequence
material have returned correctly. The right-handed layout comparison also
survived reload with its semantic colors and sample assignments intact.

The removable-card workflow required one repair episode. The exFAT card was
clean after `fsck.exfat`, remounted read/write, and subsequently passed sustained
write/read/hash/delete probes. Transactional deployment and checksum comparison
prevented an interrupted USB-reader write from being mistaken for a complete
package.

Navigation improved substantially after completed test trees and obsolete test
projects were moved into a recoverable external quarantine. The SD now has a
shallow Scratchpad layout guide and a Drum Alternates index. This matters on the
MPC because a technically organized computer hierarchy can still be tedious to
navigate from the hardware Browser.

## MIDI files and layout translation

The layout engine's right-handed performance variant is preferred over Classic,
although the audible difference is modest for a library dominated by varied
one-shots. Save/reload and color persistence passed, closing the core layout
test.

MIDI import exposed a concrete format distinction. The initial format-0 files
caused a brief load flicker but created no new sequence. Regenerating them as
MPC-targeted format 1—with conductor and note tracks—worked. The semantic source
and Classic patterns sounded close enough to pass, with the caveat that diverse
one-shots make exact auditory equivalence hard to judge.

## External MIDI and the Volcas

The Key 37 works well as an external MIDI master in the tests completed so far:

- Volca Bass passed individually on channel 1.
- Volca Keys passed individually on channel 2.
- Volca Drum passed in single-channel mode on channel 10.
- MPC pads A01–A06 successfully addressed Volca Drum Parts 1–6.
- The custom pad map persisted in captured projects.
- Volca Drum followed MPC clock, tempo, start, and stop.

One subtle result is especially useful. Pressing MPC Play started the pattern
already stored on the Volca Drum, but later XPJ inspection found no note events
on the MPC MIDI tracks. The sound was the Volca following clock and transport,
not an MPC-authored duplicate sequence. A reusable MPC-master setup should use
an empty Volca pattern and explicitly record MIDI notes on the MPC track.

Simultaneous three-device isolation, drift, and audio gain remain deferred until
the CME MIDI Thru5 WC is incorporated. The Launch Control XL 3 has arrived, but
its mapping is also intentionally deferred.

## Plugins

Fabric and Jura are confirmed installed on MPC internal storage. Their absence
from the SD's Synths folder is therefore expected. The SD contains substantial
content for Iona, OPx-4, AIR Flavor Pro, and several AIR effects, but filesystem
content alone does not prove activation or executable availability.

Mini D and Studio Strings have not been purchased and are deferred. Ordinary
plugin project persistence is accepted without a dedicated audit project and
will be reopened only if a real composition loses plugin state.

## Friction and limitations observed

- Pad colors are obscured by Browser context, which can look like failed color
  serialization until Browser is closed.
- Track selection still influences the physical pads despite dedicated keyboard
  and pad input assignments.
- Drum Split is a note-range feature, not physical pad/key separation.
- Some device preferences are not saved in the project.
- Keygroups with low source roots can require extreme octave transposition unless
  rebuilt for the 37-key register.
- Large programs may load slowly without enough feedback to distinguish delay
  from a hang immediately.
- Default projects may add factory tracks that complicate minimal-project tests.
- Format-0 MIDI import was ineffective on the observed MPC 3 build; format 1
  worked.
- Modern Clip Workflow is unavailable without Pro Pack.
- Hardware Browser navigation rewards shallow, purpose-named folders more than
  deep computer-oriented taxonomies.

## What remains deliberately deferred

Deferral means "not currently worth interrupting development for," not failure.

- Hardware acceptance of Drum Alternates 06–09.
- Detailed boundary and choke testing for the expanded layered program.
- Final NR2 chromatic Keygroup register acceptance.
- Cold-start timing.
- A revised Scratchpad Jam copy with an inspected lead phrase.
- MPC-authored Volca sequence save/reload and simultaneous three-Volca testing.
- Launch Control XL 3 mapping and persistence.
- Clip Workflow unless Pro Pack is purchased.
- Mini D and Studio Strings unless purchased.

## Evolving verdict

The MPC Key 37 is proving most valuable not as a generic workstation with every
feature enabled, but as a carefully curated standalone instrument. Its program
formats and save/reload behavior are dependable enough to support a reusable
library. Its pads are especially effective with banked Drum Programs, semantic
colors, and expressive velocity layers. Its keybed turns the same project into
a credible melodic Scratchpad, and its physical MIDI output makes it a useful
center for external hardware.

The main design lesson is that a good Key 37 workflow should reduce context,
not add options. Shallow folders, selected favorites, explicit track inputs,
known pad maps, and a protected starting project do more for immediacy than a
larger uncurated library. The ongoing software work should continue making
those states visible and reproducible.

## How future observations are added

Each new test should add a dated paragraph to the relevant section containing:

- what was loaded or connected;
- the exact action performed;
- what was heard or seen;
- whether save/reload was involved;
- the interpretation, including whether an apparent failure was actually UI,
  mapping, source-content, or device behavior;
- the resulting role or workflow decision.

The detailed pass/warn/fail ledger and remaining checklist remain separate.
This review records what those results mean in practice.
