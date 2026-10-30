# Deferred Keygroup conversion priorities

October 30, 2026. The historical local source index has 191 deferred records.
They are not 191 missing SD instruments: two are deliberate duplicate/aggregate
omissions and eight have known downstream builder rejections. An existing
program elsewhere on the card can also cover the same musical role.

Fresh source recheck: all 181 remaining records still fail preflight, even with
the existing loop/endpoint/key-range comparison allowances. The eight known
builder exclusions and two intentional omissions were retained, not retried as
valid builds. No new program was generated. Private results and the recheck
script are in `work/instrument-audit-2026-10-30/deferred-recheck.json` and
`recheck_deferred.py`.

## What must be preserved

The old first-error summary counted 81 detune blockers, 38 sample-start
blockers, and 13 panorama blockers. Those groups are not complete descriptions
of each source: several settings can coexist. The preflight diagnostic now
reports coexisting settings, with bounded output, rather than stopping at the
first detune/sample-start/panorama field.

Other deferred sources span multiple sample folders, reuse WAV basenames, or
have incompatible velocity/key topology. Copying all WAVs to one folder or
widening all key ranges can change the instrument. A successful comparison
preflight is not proof that the downstream builder or the MPC will reproduce it.

## Next implementation priorities

1. Preserve per-zone detune with documented units and a reference XPM. Prove
   positive and negative pitch offsets in software and compare on hardware
   before promoting converted instruments.
2. Preserve sample-start offsets together with endpoints and loops. Verify
   frame units, stereo handling, and loop/start ordering; changing the attack
   can change the identity of a sound.
3. Preserve panorama using a verified scale. Keep it separate from volume and
   from any stereo processing already present in the sample.
4. Support explicit per-zone sample paths and collision-safe packaging before
   flattening multi-directory sources. Resolve differing velocity schemas
   without silently filling source gaps or removing overlaps.

These are preservation tasks, not requests to bypass current guards. They can
be developed with fixtures while hardware listening is deferred. Do not build
another large batch until one complete source can be preserved end to end.

## Databenders shortlist

Crackle & Whine and Digi Stab are already represented in the reference catalog.
The October 30 card inventory places them at:

- `Programs/Keygroups/SFM REFERENCE INSTRUMENTS/13 Other Instruments/Databenders Toolkit/Crackle & Whine.xpm`
- `Programs/Keygroups/SFM REFERENCE INSTRUMENTS/13 Other Instruments/Databenders Toolkit/Digi Stab.xpm`

These remain reference/software-test instruments, not new favorites or new
hardware passes. Sine FX was intentionally omitted as a duplicate of Crackle
& Whine. Blip Underwater, Bowed Bytes Wet, Data Piano, Sub, Sub 2, and Throaty
Clan need detune preservation; Bowed Bytes, Chaos, and Far East need source
offset preservation. Hack Saw has a velocity-topology blocker. A fresh source
inspection confirms that Blip Underwater also starts at frame 1109 and Bowed
Bytes Wet at frame 11381: preserving detune alone would still lose their
attacks. Far East has nonzero starts on both of its active zones (1707 and 615).

The separate Found Transitions pad candidate already fills a small transition
role without stripping unsupported Keygroup settings. Continue using the
[accepted role guide](../docs/instrument-role-guide.md) for everyday playing.
