"""Build an eight-bar duet and editable MIDI from the two native instruments."""

import argparse
from array import array
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import wave

from mpc_keygroup_builder.midi_groove import parse_midi
from mpc_keygroup_builder.midi_writer import MidiNote, MidiTrack, render_standard_midi
from mpc_keygroup_builder.pad_recorder import _new_folder, receipt
from mpc_keygroup_builder.publication import publish_directory
from print_take import PPQ, print_take

HERE = Path(__file__).resolve().parent
BPM = 100
RATE = 44100
BAR = 4 * PPQ
END = 8 * BAR
FRAMES = round(END * 60 * RATE / (PPQ * BPM))


def note(t, key, vel, length=90):
    return MidiNote(t, length, key, vel, 1)


def midi(path, tracks, end=END):
    path.write_bytes(
        render_standard_midi(
            tuple(tracks),
            tempo=BPM,
            ppq=PPQ,
            end_tick=end,
            midi_format=0 if len(tracks) == 1 else 1,
        )
    )


def render(runner, scratch, folder, plugin, track, title):
    native = (
        HERE.parent
        / plugin.replace(" ", "")
        / "build/native"
        / (plugin.lower().replace(" ", "-") + ".so")
    )
    schedule = scratch / "events.tsv"
    events = []
    for n in track.notes:
        events.extend(
            (
                (n.tick, 2, n.note, n.velocity, 144),
                (n.tick + n.duration_ticks, 1, n.note, 0, 128),
            )
        )
    schedule.write_text(
        "".join(
            f"{round(t * 60 * RATE / (BPM * PPQ))} {k} {v} {s}\n"
            for t, _, k, v, s in sorted(events)
        )
    )
    raw = scratch / "output.pcm"
    subprocess.run([runner, native, str(FRAMES), str(BPM), schedule, raw], check=True)
    data = raw.read_bytes()
    if len(data) != 4 * FRAMES:
        raise ValueError(f"incomplete render for {plugin}")
    wavefile(folder / (title + ".wav"), data)
    midi(folder / (title + ".mid"), [track])
    pcm = array("h")
    pcm.frombytes(data)
    if sys.byteorder != "little":
        pcm.byteswap()
    return pcm


def wavefile(path, raw):
    with wave.open(str(path), "wb") as w:
        w.setparams((2, 2, RATE, 0, "NONE", ""))
        w.writeframes(raw)


def build(folder, scratch, sdk, seed=None):
    runner = scratch / "render"
    subprocess.run(
        [
            "c++",
            "-std=c++17",
            "-O2",
            "-I",
            sdk / "framework",
            HERE.parent / "DrumHands/tests/render.cpp",
            "-ldl",
            "-o",
            runner,
        ],
        check=True,
    )
    source = [
        note(i * 120 + offset, 36 + lane, v)
        for i, lane, v, offset in (
            (0, 0, 117, 0),
            (2, 2, 66, 8),
            (4, 1, 109, 0),
            (6, 3, 63, -10),
            (7, 2, 33, 4),
            (9, 0, 88, 7),
            (10, 3, 77, 0),
            (12, 1, 105, 0),
            (14, 2, 61, 6),
        )
    ]
    if seed is not None:
        meta, events = parse_midi(seed)
        source = [
            note(
                min(BAR - 1, round(event.tick * PPQ / meta.ppq)),
                event.note,
                event.velocity,
                1,
            )
            for event in events
            if event.tick < 4 * meta.ppq and 36 <= event.note <= 39
        ]
        if not source:
            raise ValueError(
                "the seed needs drum notes 36–39 within its first four beats"
            )
        # A capture cue starts the bar even when the player's first stroke is a pickup.
        source.insert(0, note(0, 35, 100, 1))
    midi(folder / "Source groove.mid", [MidiTrack("Source", tuple(source))], BAR)
    printed = folder / "Editable variations"
    print_take(folder / "Source groove.mid", printed, [36, 37, 38, 39], 1, BPM, 43)
    # The player holds one scene pad for each variation; note-offs return to the original.
    drums = source + [
        note(b * BAR, 39 + scene, 100, BAR - 1)
        for b, scene in ((2, 1), (3, 2), (4, 3), (5, 2), (6, 3))
    ]
    keys = [
        note(BAR, 67, 64),
        note(BAR + 2, 36, 90, 450),
        note(BAR + 40, 42, 100),
        note(BAR + PPQ, 40, 100),
        note(2 * BAR, 70, 80),
        note(2 * BAR + 1, 37, 100, 450),
        note(2 * BAR + 40, 43, 100),
        note(2 * BAR + PPQ, 41, 100),
        note(4 * BAR, 40, 100),
        note(6 * BAR, 41, 100),
        note(7 * BAR, 44, 100),
    ]
    # Hand the actual printed answers to the keyboard player in bar five and bar seven.
    _, canon = parse_midi(printed / "Canon.mid")
    for b in (4, 6):
        for e in canon:
            if e.channel == 1:
                keys.append(note(b * BAR + e.tick, e.note, e.velocity, 90))
    for b in (2, 3, 4, 5, 6):
        keys.extend(
            note(b * BAR + i * 120, 39, v)
            for i, v in ((2, 66), (6, 91), (11, 39), (14, 76))
        )
    left = MidiTrack("Shadow Steps", tuple(drums))
    right = MidiTrack("Common Tone", tuple(keys))
    drum = render(runner, scratch, folder, "Shadow Steps", left, "01 Shadow Steps")
    harmony = render(runner, scratch, folder, "Common Tone", right, "02 Common Tone")
    mix = array(
        "h", (round(0.60 * d + 0.40 * h) for d, h in zip(drum, harmony, strict=True))
    )
    if sys.byteorder != "little":
        mix.byteswap()
    wavefile(folder / "03 Two Track Jam.wav", mix.tobytes())
    # Distinct MIDI channels keep the two parts separately routable.
    routed = tuple(
        MidiNote(n.tick, n.duration_ticks, n.note, n.velocity, 2) for n in keys
    )
    midi(folder / "03 Two Track Jam.mid", [left, MidiTrack("Common Tone", routed)])
    shutil.copyfile(HERE / "START HERE.txt", folder / "00 START HERE.txt")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sdk", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path, help="new rehearsal folder")
    p.add_argument(
        "--seed",
        type=Path,
        help="use the first 4/4 bar of a Play in Shadow Steps.mid file as the drum part",
    )
    args = p.parse_args()
    out = _new_folder(args.output)
    with TemporaryDirectory(dir=out.parent) as tmp, TemporaryDirectory() as work:
        stage = Path(tmp)
        build(stage, Path(work), args.sdk.resolve(), args.seed)
        receipt(stage)
        publish_directory(stage, out)
    print(out)


if __name__ == "__main__":
    main()
