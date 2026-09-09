# Live-control responsibility model

The rig is most playable when each control surface owns the work it does best.
The Launch Control XL 3 is not a universal replacement panel for every device.
Its job is to remove friction inside the MPC, while dedicated hardware remains
hands-on and the LiveTrak L6 remains the physical-device mixer.

## Control ownership

- **MPC Key 37:** sequencing, quantized capture, looping, track selection,
  program playback, and sequence launching from its pads.
- **Launch Control XL 3:** MPC-internal track/program balance, a small number of
  high-value plugin controls, buried MPC effect/performance parameters, and
  occasional gestures that need to be recorded as MIDI CC automation.
- **Zoom LiveTrak L6:** levels between physical devices, the MPC stereo feed,
  mutes/solos, aux sends, and external-effects routing.
- **Volcas, UltraTap, Qi Etherealizer, NTS-3, and similar boxes:** their native
  knobs and performance controls when the device is within reach.

The XL 3 faders retain one stable convention: they primarily balance tracks or
submixes *inside* the MPC. The L6 can control the overall MPC stereo return, but
cannot independently rebalance every MPC plugin unless the MPC is deliberately
routed to multiple outputs. Duplicating L6 channel controls on the XL 3 adds
another layer without solving that internal-mix problem.

## What earns an XL 3 mapping

A proposed page should answer all of these questions before it becomes a
maintained performance layout:

1. What touchscreen, menu, or Q-Link paging does it avoid during a performance?
2. Is the control musically useful often enough to deserve a fixed position?
3. Does the hardware already expose an equally reachable native control?
4. Must its gesture be captured and replayed by the MPC?
5. Can the page retain the stable fader and physical-position vocabulary?
6. Did a short jam prove that it is easier to use than the native alternative?

Prefer eight memorable controls over an exhaustive parameter mirror. A complete
parameter catalog is still valuable as searchable evidence, but it is an input
to page design rather than the page itself. OPx-4, Jura, Fabric/Fabric XL, and
other deep MPC plugins are strong candidates because useful parameters are
otherwise split across touchscreen and Q-Link pages.

## Default and conditional paths

The default live path is:

```text
MPC programs/plugins ← Launch Control XL 3 → MPC internal mix
                                            │
                                            └─ MPC stereo → LiveTrak L6
Volcas / PO-33 / external effects → LiveTrak L6 → aux/hardware FX
```

Direct Volca Custom Modes remain useful reference implementations and optional
automation pages. They are not the default performance surface when the Volca
panel is within reach. Use them when a specific CC gesture must be recorded,
when the device is physically inaccessible, or when a coordinated macro move
has been tested and proved useful.

Flavor Pro is an MPC insert effect. It can process an MPC track, submix, or
master. Processing a live Volca through it requires routing that Volca's audio
through the MPC; that is a deliberate resampling or sound-design topology, not
the default external-effects path.

## Composition workflow

The primary workflow is played-in, sequence-based composition:

1. Audition and perform a part on keys or pads.
2. Capture it with suitable quantization or snapping.
3. Loop the sequence while adding or evolving another part.
4. Use the MPC pads and Next Sequence view to launch structural changes.
5. Reach for the XL 3 only when it makes an internal MPC action faster or more
   performable.

A large step grid may still be useful in a specialized workflow, but it is not
a current product gap. Ordinary MIDI Learn does not expose Next Sequence as a
simple XL 3 target, and the MPC pads already provide the more direct launching
surface.

## Evidence boundary

Declarative maps can prove channels, endpoints, collisions, and assignment
coverage. They cannot prove that a page deserves space in a live set. Keep
full catalogs and experimental pages as software evidence; promote only a
small performance core after a musician can identify the avoided friction and
confirm it in a short hardware session.
