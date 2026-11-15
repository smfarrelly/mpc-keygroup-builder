# Three effects for a played hook

On the Key 37, use an audio insert on the **track** or submix you want to transform. Select the named effect under **External Plugins**. Start with a single instrument so you can hear which source is driving the effect. The listening examples are in **SD / Projects / Performance Effects /**.

## Ghost Fader

Insert **Ghost Fader** on a Vinyl SP snare or a velocity-layered drum track. Play four accented backbeats with a pair of quiet doubles between them. Center **Balance** for the original. Turn left to hear the doubles, then right for the backbeats. Record the Balance move into a copied sequence for a verse.

The detector compares a hit’s first nine milliseconds with the strongest of the preceding eight detected hits. It holds that classification through the decay. **Split** sets where an attack changes from ghost to accent. **Isolation** controls how far the other group recedes. Raise **Sensitivity** if quiet hits escape detection. One loud and one soft instrument landing together produce a single stereo attack. **01 Ghost Fader - Dry, Ghosts, Accents.wav** plays three four-second passes at a shared gain.

## Rhythm Imprint

Insert **Rhythm Imprint** on a held Wurli chord or Glass Howl. Start transport and choose **Groove slot 1** from the presets. Adjust **Depth** and **Release**. Short releases produce distinct attacks; longer ones let neighboring notes join. The four slots on this SD use the first four quarter notes of CR-78 Disco Slow Rock, MPC60 16 Swing 57, SP 1200 16 Swing 63, and CR-78 Shuffle A respectively. **02 Rhythm Imprint - Dry, Imprinted.wav** compares the Wurli dry and through slot 1.

**Teach it your own audio on the MPC.** Insert Rhythm Imprint on the drum track, select **Learned** on its Source page and switch **Learn** on. With transport running it listens from the next four-quarter boundary through one complete bar. Leave Learn on just past the following downbeat. Monitoring is dry while learning. Switch Learn off and save the effect preset from the MPC’s preset menu. Load that user preset into a second Rhythm Imprint on the keys track. The groove is in the preset’s state. The software host test teaches one instance and reopens its state in another. The Key 37 preset-menu round trip still needs a physical check.

The grid is four quarter notes aligned to song position zero. Up to 64 attacks retain their relative dynamics and phase at 1/4096 of the cycle. A silent take preserves the previous groove. Transport stop releases the gate. A seek during capture discards the partial take. Source slots read the package’s Content files at instantiation. Use the same bank when moving a slot-based project to another MPC. An absent or invalid slot passes the input through.

**Prepare different slots from your library.** Install the toolkit on the laptop. Run this with one to four Standard MIDI files in slot order.

```bash
uv run mpc-imprint-bank "Grooves/CR-78 Shuffle A.mid" "Grooves/MPC60 16 Swing 57.mid" \
  --bar 1 --output "work/My groove bank/Content"
```

Copy the generated slot files into **SD / VST2 Plugins / FG Scratchpad - VST - Rhythm Imprint / Content /**. Reopen the effect. Simultaneous attacks use the strongest velocity. Add `--note 38` to isolate one drum. The files contain timing and levels only. Keep personal library-derived banks out of public releases.

## Tail Choir

Insert **Tail Choir** on Mirage Wurli. Play three separate short notes, leaving enough time between attacks to capture each decay, then lift your hands. The dry notes pass immediately. A quiet stereo bed continues underneath. **Wait** chooses how far after the attack capture starts; **Grain** chooses the fragment length. **Bed** mixes in up to three overlapping, crossfaded loops. Hold **Clear** to fade them and prevent new captures, then release it to begin again. Try the **Vinyl dust** preset on a snare with a noisy tail. **03 Tail Choir - Dry, Choir.wav** uses the same three Wurli attacks in both passes.

The bed is live audio memory. Resample its output to keep a particular texture as audio. Project recall restores the controls; a fresh instance starts with an empty bed. Closely spaced hits can restart a pending capture before it has gathered a full grain.

## Building and auditioning

All three include ARM32 and ARM64 builds. The original Key 37 uses ARM32. Enable External Plugin Support in MPC OS 3.10.1 or later. From the repository with the project environment installed and Akai’s SDK checked out locally, run

```bash
sdk=/path/to/mpc-plugin-builder-sdk
for plugin in GhostFader RhythmImprint TailChoir; do
  python3 "$sdk/tools/build.py" "plugins/$plugin" --target all
done
uv run python plugins/PerformanceEffects/audition.py --sdk "$sdk" \
  --snare "/my/samples/snare.wav" --keys "/my/samples/electric-piano.wav" \
  --bank "work/My groove bank/Content" --output "work/My effect audition"
```

The audition driver uses a Linux C++17 host, the built native binaries, and your own mono/stereo PCM WAVs. Omit `--bank` to audition the built-in learned groove. [Akai plugin SDK](https://github.com/inmusic-software/mpc-plugin-builder-sdk)

## Next uses for Samples From Mars

1. **Body Print — use a one-shot as the body of another sound.** The offline **04 Body Print study - Dry, Rim, Tape Clap.wav** plays the same Wurli chords dry, through a CR-78 Vinyl SP rim, and through Clap Tape Crunch Vinyl SP. The study takes 48 signed reflections from 3–63 ms after the donor’s attack and uses them as a short convolution filter. The donor contributes timbre each time the keys sound. Candidate insert controls are Body A/B, Length and Blend. First decision: can you distinguish both donors at comparable loudness, and would you keep either under a verse?
2. **Break Envelope — use the shape inside each hit.** Rhythm Imprint transfers attack positions and strengths. A next insert could extract low, mid and high energy curves from a CR-78, DMX or Modular Drum Loop, then shape the corresponding bands of a sustained chord. A snare buzz or hat decay would open the high end for its original duration. Compare a real break against its attack-only imprint using the same chord.
3. **Wear Pair — borrow the difference between two recordings.** Start with the *same* drum hit recorded clean and through a sampler or tape path, where the library supplies a credible matched pair. Level- and time-align the candidates before estimating their spectral difference. A control could introduce that difference on an MPC submix. First find and audition real pairs; two different snares would measure the instruments as well as the recording path.

To reproduce the first study without an SDK build, run

```bash
uv run python plugins/PerformanceEffects/body_study.py --keys "/my/samples/Wurli.wav" \
  --responses "/my/samples/Rim.wav" "/my/samples/Tape Clap.wav" --output "work/body-study.wav"
```

The body study is an offline experiment. Break Envelope and Wear Pair are proposed experiments. [Local Samples From Mars inventory](../../inventory/samples-from-mars-mpc-backlog.md)
