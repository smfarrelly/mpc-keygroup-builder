"""Make five short MPC rehearsals from the same notes as their stereo previews."""

import argparse
from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import wave

from mpc_keygroup_builder import sdk_package
from mpc_keygroup_builder.midi_writer import MidiNote, MidiTrack, render_standard_midi
from mpc_keygroup_builder.pad_recorder import _new_folder, receipt
from mpc_keygroup_builder.publication import publish_directory

HERE = Path(__file__).resolve().parent
PPQ = 480
RATE = 44100
PLUGINS = {
    "Drum Seat": "DrumSeat",
    "Ghost Wire": "GhostWire",
    "Rudiment Keys": "RudimentKeys",
    "Rest Reply": "RestReply",
    "Split Cycle": "SplitCycle",
}


@dataclass(frozen=True)
class Take:
    title: str
    instrument: str
    tempo: int
    bars: int
    notes: tuple[MidiNote, ...]
    insert: str | None = None


def hit(beat, key, velocity, length=0.1):
    return MidiNote(round(beat * PPQ), round(length * PPQ), key, velocity, 1)


def drummer():
    notes = []
    for bar in range(8):
        start = 4 * bar
        # Leave beat four open on alternate bars so the answering voice can finish.
        phrase = [(0, 45, 110), (0.5, 46, 61), (1, 39, 116), (1.5, 46, 67), (2, 45, 92)]
        if bar % 2 == 0:
            phrase += [(2.5, 46, 62), (3, 38, 115), (3.5, 46, 57)]
        if bar:
            phrase += [(0.75, 36, 38), (1.75, 37, 47), (2.25, 36, 33)]
        if bar in (3, 6):
            notes.append(hit(start + 1.5, 40, 79, 0.44))
        if bar == 5:
            notes.append(hit(start, 55, 96))
        for offset, key, vel in phrase:
            notes.append(hit(start + offset, key, vel))
    return Take("01 Drum Seat - ghost line", "Drum Seat", 100, 8, tuple(notes))


def cycles():
    # The two repeating lanes supply the notes between these gestures.
    events = [
        (0, 36, 112),
        (0.49, 37, 83),
        (0.74, 38, 55),
        (1, 39, 40),
        (8.25, 40, 73),
        (12, 42, 100),
        (16, 42, 100),
        (20, 47, 100),
        (22, 44, 100),
        (24.75, 41, 61),
        (28, 43, 100),
        (30, 43, 100),
    ]
    return Take(
        "02 Split Cycle - three against four",
        "Split Cycle",
        104,
        8,
        tuple(hit(t, k, v) for t, k, v in events),
    )


def sticking():
    phrase = [
        (36, 115),
        (37, 83),
        (36, 77),
        (36, 79),
        (37, 110),
        (36, 75),
        (37, 82),
        (37, 78),
    ]
    notes = []
    for bar in range(4):
        for i, (key, velocity) in enumerate(phrase):
            gesture = (
                2 if bar == 2 and i in (0, 4) else 4 if bar == 3 and i in (2, 6) else 0
            )
            notes.append(hit(bar * 4 + i / 2, key + gesture, velocity))
        notes.append(hit(bar * 4 + 1.75, 36, 32))
        notes.append(hit(bar * 4 + 2.75, 37, 39))
        if bar == 2:
            notes.append(hit(bar * 4, 55, 99))
    return Take("03 Rudiment Keys - paradiddle", "Rudiment Keys", 104, 4, tuple(notes))


def rolls():
    notes = []
    for bar in range(4):
        t = 4 * bar
        notes += [
            hit(t, 45, 110),
            hit(t + 0.5, 36, 44),
            hit(t + 1, 39, 111),
            hit(t + 1.5, 37, 40),
            hit(t + 2, 45, 93),
            hit(t + 2.25, 40 + bar % 2, 86, 0.38 + 0.12 * bar),
            hit(t + 3, 38, 106),
            hit(t + 3.5, 47, 67),
            hit(t + 3.75, 46, 68),
        ]
    return Take("04 Ghost Wire - press and release", "Ghost Wire", 104, 4, tuple(notes))


def replies():
    notes = []
    for bar in range(4):
        t = 4 * bar
        notes += [hit(t, 45, 110), hit(t + 0.25, 36, 60), hit(t + 1, 39, 104)]
        if bar % 2:
            notes.append(hit(t + 1.5, 42, 75))
    return Take(
        "05 Rest Reply - trade phrases", "Ghost Wire", 96, 4, tuple(notes), "Rest Reply"
    )


def binary(name):
    path = (
        HERE.parent
        / PLUGINS[name]
        / "build/native"
        / (name.lower().replace(" ", "-") + ".so")
    )
    if not path.is_file():
        raise ValueError(f"build the native {name} plugin first: {path}")
    return path


def write_wave(raw, dest, frames):
    data = raw.read_bytes()
    if len(data) != frames * 4:
        raise ValueError(f"incomplete stereo render: {dest.name}")
    with wave.open(str(dest), "wb") as w:
        w.setparams((2, 2, RATE, 0, "NONE", ""))
        w.writeframes(data)


def build(sdk, folder, scratch):
    runner = scratch / "render"
    subprocess.run(
        [
            "c++",
            "-std=c++17",
            "-O2",
            "-I",
            str(sdk / "framework"),
            str(HERE / "tests/render.cpp"),
            "-ldl",
            "-o",
            str(runner),
        ],
        check=True,
    )
    for take in (drummer(), cycles(), sticking(), rolls(), replies()):
        ticks = take.bars * 4 * PPQ

        def frame(tick):
            return round(tick * RATE * 60 / (PPQ * take.tempo))

        # Process note-offs before new attacks. The MIDI writer orders simultaneous note-ons by key.
        midi = MidiTrack(take.instrument, take.notes)
        score = []
        for n in midi.notes:
            if not 0 <= n.tick < n.tick + n.duration_ticks <= ticks:
                raise ValueError(f"note outside {take.title}")
            score += [
                (n.tick, 2, n.note, n.velocity, 144),
                (n.tick + n.duration_ticks, 1, n.note, 0, 128),
            ]
        schedule = scratch / "score.tsv"
        schedule.write_text(
            "".join(f"{frame(t)} {k} {v} {s}\n" for t, _, k, v, s in sorted(score))
        )
        # Format 0 keeps the player gestures on one note track.
        (folder / (take.title + ".mid")).write_bytes(
            render_standard_midi(
                (midi,), tempo=take.tempo, ppq=PPQ, end_tick=ticks, midi_format=0
            )
        )
        raw = scratch / "stereo.pcm"
        cmd = [
            str(runner),
            str(binary(take.instrument)),
            str(frame(ticks)),
            str(take.tempo),
            str(schedule),
            str(raw),
        ]
        if take.insert:
            cmd += [str(binary(take.insert)), str(scratch / "dry.pcm")]
        subprocess.run(cmd, check=True)
        write_wave(raw, folder / (take.title + ".wav"), frame(ticks))
        if take.insert:
            write_wave(
                scratch / "dry.pcm",
                folder / "05 Rest Reply - dry drums.wav",
                frame(ticks),
            )
    shutil.copyfile(HERE / "START HERE.txt", folder / "00 START HERE.txt")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sdk", type=Path, required=True, help="local checkout of the pinned Akai SDK"
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="new folder for the MIDI and WAV files",
    )
    parser.add_argument(
        "--include-plugins",
        action="store_true",
        help="include both validated ARM builds and put the rehearsals under Projects/Drum Hands",
    )
    args = parser.parse_args()
    output = _new_folder(args.output)
    with TemporaryDirectory(dir=output.parent) as stage, TemporaryDirectory() as work:
        folder = Path(stage)
        rehearsals = folder
        if args.include_plugins:
            for name, source in PLUGINS.items():
                build_dir = HERE.parent / source / "build"
                package = f"FG Scratchpad - VST - {name}"
                dest = folder / "VST2 Plugins" / package
                shutil.copytree(build_dir / package, dest, symlinks=True)
                for target in ("arm32", "arm64"):
                    sdk_package.inspect(dest, target, build_dir / "params.json")
            rehearsals = folder / "Projects/Drum Hands"
            rehearsals.mkdir(parents=True)
        build(args.sdk.resolve(), rehearsals, Path(work))
        receipt(folder)
        publish_directory(folder, output)
    print(output)


if __name__ == "__main__":
    main()
