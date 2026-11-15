"""Render one performance three ways through the native plugin and export its exact MIDI."""

import argparse
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import wave

from mpc_keygroup_builder.midi_writer import MidiNote, MidiTrack, render_standard_midi
from mpc_keygroup_builder.pad_recorder import _new_folder, receipt
from mpc_keygroup_builder.publication import publish_directory

HERE = Path(__file__).resolve().parent
PPQ = 480
BAR = 4 * PPQ
RATE = 44100


def score():
    # A two-bar phrase: slightly late snare, two light hats, pickup into bar two.
    strokes = [
        (0, 36, 118),
        (235, 38, 76),
        (493, 37, 110),
        (720, 38, 56),
        (953, 36, 100),
        (1224, 38, 69),
        (1443, 37, 99),
        (1674, 39, 84),
        (1920, 36, 118),
        (2169, 38, 60),
        (2416, 37, 110),
        (2640, 38, 54),
        (2770, 38, 36),
        (2880, 36, 92),
        (3120, 39, 88),
        (3374, 37, 100),
        (3600, 38, 61),
    ]
    notes = []
    for section, pad in enumerate((None, 41, 42)):
        start = section * 2 * BAR
        notes.append(MidiNote(start, 3, 40, 100, 1))
        if pad:
            notes.append(MidiNote(start, 2 * BAR - 1, pad, 100, 1))
        for t, k, v in strokes:
            notes.append(MidiNote(start + t + 6, 50, k, v, 1))
    return notes


def build(folder, sdk, content):
    path = _new_folder(folder)
    env = os.environ.copy()
    with (
        TemporaryDirectory() as tmp,
        TemporaryDirectory(dir=path.parent, prefix=".relay-demo-") as temp,
    ):
        tmp = Path(tmp)
        stage = Path(temp)
        if content:
            if not (content / "pair.brk").is_file():
                raise ValueError("Content needs pair.brk")
            (tmp / "Content").symlink_to(content.resolve(), target_is_directory=True)
        env["MPC_PLUGIN_FOLDER"] = str(tmp)
        runner = tmp / "render"
        subprocess.run(
            [
                "c++",
                "-O2",
                "-std=c++17",
                "-I",
                sdk / "framework",
                HERE.parent / "DrumHands/tests/render.cpp",
                "-ldl",
                "-o",
                runner,
            ],
            check=True,
        )
        notes = score()
        data = render_standard_midi(
            (MidiTrack("Break Relay", tuple(notes)),),
            tempo=120,
            ppq=PPQ,
            end_tick=6 * BAR,
            midi_format=0,
        )
        (stage / "01 Same hands - Home, Borrow, Away.mid").write_bytes(data)
        schedule = []
        for n in notes:
            schedule.extend(
                [
                    (n.tick, n.note, n.velocity, 144),
                    (n.tick + n.duration_ticks, n.note, 0, 128),
                ]
            )
        events = tmp / "events"
        events.write_text(
            "".join(
                f"{round(t * RATE / (2 * PPQ))} {k} {v} {s}\n"
                for t, k, v, s in sorted(schedule)
            )
        )
        raw = tmp / "raw"
        subprocess.run(
            [
                runner,
                HERE / "build/native/break-relay.so",
                str(RATE * 12),
                "120",
                events,
                raw,
            ],
            env=env,
            check=True,
        )
        audio = raw.read_bytes()
        if (
            len(audio) != 12 * RATE * 4
            or len(
                {
                    audio[i : i + 4 * RATE * 4]
                    for i in range(0, len(audio), 4 * RATE * 4)
                }
            )
            != 3
        ):
            raise ValueError("Expected three distinct four-second passes")
        with wave.open(
            str(stage / "01 Same hands - Home, Borrow, Away.wav"), "wb"
        ) as wav:
            wav.setparams((2, 2, RATE, 0, "NONE", "not compressed"))
            wav.writeframes(audio)
        (stage / "Start here.txt").write_text(
            "Add External Plugins > Break Relay on a Plugin track. MIDI 36 kick, 37 snare, 38 hat, 39 pickup. Tap 40 for Home. Hold 41 for Borrow or 42 for Away. Hold a key from MIDI 48 upward to tune new hits; 60 is original pitch. The WAV and MIDI play three four-second passes of the same strokes at 120 BPM. Assign the MIDI track to Break Relay.\n"
        )
        receipt(stage)
        publish_directory(stage, path)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sdk", type=Path, required=True)
    p.add_argument("--content", type=Path)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    build(a.output, a.sdk, a.content)
