# Make another part from a hook you played

## Start on the Key 37

Open **SD / Projects / Phrase Lab / 02 Four Bar Jam.xpj**. Play **Four-bar jam**, then select **Ghost choir**, **Trade rhythms**, or **Pass the phrase**. All fifteen sequences use the project’s existing instruments. Open Grid on Wurli to edit a result. In Trade and Pass, the Pluck Bass notes change too.

For a quick listen from the browser, the same folder contains four WAV comparisons. Each section runs eight seconds at 120 BPM. The comparisons use dry laptop renders of the actual samples. The last section in the second WAV is the fourth pass of the extended sequence.

## Play a phrase from the pads

On a standalone Plugin track select **External Plugins → Phrase Hands**. The factory phrase makes the pads playable immediately. To teach another phrase, hold MIDI **40**, play up to eight keyboard notes **48–127** in order, then release **40**. The instrument stores one pitch per attack. Input in excess of eight still sounds live. Releasing Learn without entering notes keeps your previous phrase.

- **36** advances one note on each strike. Your velocity and timing become the performance.
- **37** walks backward. **38** alternates between the two ends of the melody.
- **39** selects the position in the learned phrase by strike strength. Tap softly to pick near the start. Hit hard to pick near the end.
- **41** returns the shared playback cursor to the first step. Record a reset just before the first strike in a sequence to make the pattern restart predictably. All four striking pads share the cursor.
- **42 Land** in Phrase Hands 1.1 remembers the most recently held keyboard note. Hold a destination, tap Land, then release the key. The next three pad strikes travel one third, two thirds and all the way from their phrase pitches toward the destination. Further strikes play the destination until **41 Home** restores the melody. Land with no held destination does nothing. Hear the six-second take at **SD / Projects / Phrase Hands Land / 01 Land on G.wav**. The adjacent MIDI includes the teaching and landing gestures.
- Keys from **48** upward audition pitches directly. Decay, Brightness, Register and Level shape the mallet sound. Try the Bass knocks preset.

These are MIDI note numbers. Use a pad note layout that sends those numbers. Project save stores the last completed phrase. The recorded strikes operate this instrument’s own voices. Use the XPJ tool below to play the result on a sampled instrument, an installed MPC synth or an external MIDI track. To hear your saved hook through the plug-in, use **SD / Projects / Phrase Lab / Play this hook on Phrase Hands.mid** on a track assigned to Phrase Hands. Bar 1 teaches the upper voice of the first eight attacks. The following four passes play the drum take forward, backward, outside-in, and by strike strength. The standalone package is in **SD / VST2 Plugins / FG Scratchpad - VST - Phrase Hands /**. The project example works independently of this plug-in.

## Fourteen ways to reuse the same notes

Each selection below is a separate copy of the source sequence. “Target” means the pitched track you want to change. “Guide” supplies a played rhythm. “Partner” is a second pitched instrument.

1. **Melody in your hands** (`hands`). Pour the target’s ordered notes and chords into the guide’s attacks. The guide’s velocity becomes the strength of each voicing. Try your drum part as the guide for a Wurli melody.
2. **Ghost choir** (`ghost`). Voice just the softest third of the guide’s attack levels, including ties at the cutoff and excluding the loudest level. Each ghost plays the next pitch of the target’s opening chord. With a single opening note, the first distinct pitches of the melody supply the chord. The guide keeps playing.
3. **Wait for the rest** (`reply`). After two or more attacks, wait until all sounding target notes release. A gap of half a beat or longer gets a quiet two-hit answer using the last two voicings in reverse order. Sustained notes can suppress the answer entirely.
4. **Hook silhouette** (`outline`). Keep openings, endings and the longest holds of at least one beat. A beat of actual silence divides phrases. Use this as a verse that hints at the hook.
5. **New destination** (`resolve`). Aim the lowest voice of the final chord at a MIDI note you choose. The final three attacks progressively take on that transposition. The chord retains its intervals within the MIDI range.
6. **Fourth time around** (`fourth`). Build a sequence four times as long. On pass four, interrupt the target for the last beat and bring its final voicing back on the offbeat. The rest of the band plays through. For Four Bar Jam, listen to bar 16.
7. **Trade rhythms** (`trade`). The target plays its own voicings on the partner’s attacks and vice versa. Each line cycles when it runs out of notes. Both tracks take the dynamics of their new rhythm.
8. **Play the gaps** (`negative`). Use the instant a note or chord finishes ringing as the start of another phrase. Each reply borrows the just-released voicing. Only the replies occupy the target track. Overlapping holds count as occupied space.
9. **Mirror the hook** (`mirror`). Reflect the lowest note of each voicing around the opening pitch. An upward leap becomes an equally large downward leap. Each chord moves intact, so its internal intervals survive. The result can introduce chromatic notes.
10. **Outside in** (`fold`). Hear the first chord, the last, the second, the next-to-last. Your accents and attack positions stay in place. A phrase’s ending becomes the answer to its opening.
11. **Slipping gears** (`phase`). Keep the rhythms fixed and advance the pitch order one extra position per bar. Listen to the same syncopation picking up a different note as the sequence goes on.
12. **Pass the phrase** (`hocket`). Combine both instruments’ attack times, then alternate them between the two players. One melody zigzags between the target register and the partner’s opening register. Simultaneous attacks become a single handoff.
13. **Touch becomes pitch** (`pressure`). Sort the target’s played voicings by pitch. The guide’s softest hit chooses the bottom, the loudest chooses the top, and intermediate hits choose positions in between. Play a crescendo on one drum and hear the keys climb.
14. **Half speed memory** (`stretch`). Expand the opening half of the target across the whole sequence. Attacks and note lengths double while the rhythm section continues at its original speed.

## Build these from your own project

From the laptop repository, run

```bash
uv run mpc-sequence-morph "/path/to/My Jam.xpj" --list
uv run mpc-phrase-lab "/path/to/My Jam.xpj" --track "Wurli" \
  --guide "Main Drums" --partner "Pluck Bass" --destination 65 --hands-midi \
  --output "work/My Phrase Lab"
```

Use exact names from the listing. The example lands on MIDI 65 (F). By default the currently selected sequence supplies all fourteen variations. Add `--sequence "Four-bar jam"` to select another. For just the duet and the melody outline, add `--mode hocket --mode outline`. Solo modes need only a target. A fixed-velocity guide produces silence on the Ghost target and a single repeated voicing on Pressure. The optional `--hands-midi` emits a 4/4, fixed-tempo performance for the instrument alongside the XPJ. Low teaching phrases are raised by whole octaves to reach the learning register.

The output is a new project folder with a full independent copy of its local sample media. Existing sequences keep their slots. Non-note events and muted notes stay on their tracks. Fourth repeats the entire sequence event timeline and requires note-based material with full-length clips. Use full-span clips starting at zero in a single-meter MPC 3 sequence. Pitched transforms can take an external instrument or a narrowly sampled patch outside its playable register. Plugin and MIDI tracks keep their original routing and dependencies.
