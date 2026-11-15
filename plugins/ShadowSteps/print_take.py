"""Print four editable arrangements from a 4/4 bar of MIDI or a saved MPC 3 sequence."""

import argparse
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from mpc_keygroup_builder import xpj
from mpc_keygroup_builder.midi_groove import MidiNoteEvent, parse_midi
from mpc_keygroup_builder.midi_writer import MidiNote, MidiTrack, render_standard_midi
from mpc_keygroup_builder.pad_recorder import _new_folder, receipt
from mpc_keygroup_builder.publication import publish_directory

HERE = Path(__file__).resolve().parent
SCENES = ("Original", "Offbeat", "Holes", "Canon")
PPQ = 480


def named(rows, key, value, label):
    choices = [row[key] for row in rows]
    found = [row for row in rows if row[key] == value]
    if len(found) == 1:
        return found[0]
    if not choices:
        raise ValueError(f"the project selection has no stored {label}s")
    if len(found) > 1:
        raise ValueError(
            f"multiple entries match {label} {value!r}; export the intended clip as MIDI"
        )
    if value is None and len(rows) == 1:
        return rows[0]
    raise ValueError(f"choose a unique --{label} from: {', '.join(choices)}")


def read_strokes(source, sequence, track):
    if source.suffix.lower() != ".xpj":
        if sequence or track:
            raise ValueError("--sequence and --track select a clip in an XPJ project")
        meta, events = parse_midi(source)
        return meta.ppq, 100, events
    data = xpj.load(source).data
    seq = named(
        [item["value"] for item in data["sequences"]], "name", sequence, "sequence"
    )
    rows = [row for group in seq["trackClipMaps"] for row in group]
    clip = named(rows, "key", track, "track")["value"]
    signatures = (
        clip.get("timeSignatureList", {}).get("timeSignatures")
        or seq["timeSignatureTrack"]["timeSignatures"]
    )
    if not signatures or any(
        row["beatsPerBar"] != 4 or row["beatLength"] != 960 for row in signatures
    ):
        raise ValueError("choose a clip with a fixed 4/4 meter")
    events = []
    for event in clip["eventList"]["events"]:
        if event.get("type") != 3 or event.get("muted") or "note" not in event:
            continue
        n = event["note"]
        velocity = round(n["velocity"] * 127)
        if velocity > 0:
            if not 0 <= n["note"] <= 127 or velocity > 127:
                raise ValueError("invalid stored note or velocity")
            events.append(
                MidiNoteEvent(
                    event["time"], 1, event["channel"] + 1, n["note"], velocity
                )
            )
    tempo = data["masterTempo"] if data["masterTempoEnabled"] else seq["bpm"]
    return 960, tempo, events


def print_take(
    source,
    output,
    pads,
    bar,
    tempo,
    root,
    channel=None,
    *,
    strike_note=None,
    sequence=None,
    track=None,
):
    if pads is not None and strike_note is not None:
        raise ValueError("choose --pads or --strike-note")
    if strike_note is not None and not 0 <= strike_note <= 127:
        raise ValueError("--strike-note must be from 0 to 127")
    if pads is None:
        pads = [36, 38, 42, 46] if strike_note is not None else [36, 37, 38, 39]
    if len(set(pads)) != 4 or len(pads) != 4 or any(n < 0 or n > 127 for n in pads):
        raise ValueError("choose four distinct MIDI note numbers from 0 to 127")
    ppq, source_tempo, events = read_strokes(source, sequence, track)
    if tempo is None:
        tempo = source_tempo
    if bar < 1 or not 20 <= tempo <= 300 or not 30 <= root <= 79:
        raise ValueError(
            "use a positive bar, a tempo from 20 to 300 and a root from 30 to 79"
        )
    if channel is not None and not 1 <= channel <= 16:
        raise ValueError("channel must be from 1 to 16")
    start = (bar - 1) * 4 * ppq
    grid = [[0] * 4 for _ in range(16)]
    for event in sorted(events, key=lambda event: event.tick):
        tick = event.tick - start
        if not 0 <= tick < 4 * ppq or channel not in (None, event.channel):
            continue
        if strike_note is not None:
            if event.note != strike_note:
                continue
            lane = sum(event.velocity < boundary for boundary in (48, 80, 105))
        elif event.note in pads:
            lane = pads.index(event.note)
        else:
            continue
        cell = ((8 * tick + ppq) // (2 * ppq)) % 16
        grid[cell][lane] = event.velocity
    if not any(any(row) for row in grid):
        raise ValueError(
            f"no matching strokes in 4/4 bar {bar}; check --pads, --bar and --channel"
        )
    output = _new_folder(output)
    with (
        TemporaryDirectory() as scratch,
        TemporaryDirectory(dir=output.parent) as stage,
    ):
        binary = Path(scratch) / "print"
        subprocess.run(
            ["c++", "-std=c++17", "-O2", str(HERE / "print.cpp"), "-o", str(binary)],
            check=True,
        )
        data = " ".join(str(v) for row in grid for v in row)
        rendered = subprocess.check_output(
            [str(binary)], text=True, input=f"{root} {data}\n"
        )
        scores = [[[], []] for _ in SCENES]
        for line in rendered.splitlines():
            scene, step, melodic, lane, pitch, velocity = map(int, line.split())
            key = pitch if melodic else pads[lane]
            scores[scene][melodic].append(
                MidiNote(step * 120, 110, key, velocity, 1 if melodic else 10)
            )
        folder = Path(stage)
        for name, (kit, keys) in zip(SCENES, scores, strict=True):
            tracks = (MidiTrack("Drums", tuple(kit)), MidiTrack("Answer", tuple(keys)))
            midi = render_standard_midi(tracks, tempo=tempo, ppq=PPQ, end_tick=4 * PPQ)
            (folder / (name + ".mid")).write_bytes(midi)
        triggers = (MidiNote(0, 1, 35, 100, 1),) + tuple(
            MidiNote(i * 120, 110, 36 + lane, vel, 1)
            for i, row in enumerate(grid)
            for lane, vel in enumerate(row)
            if vel
        )
        (folder / "Play in Shadow Steps.mid").write_bytes(
            render_standard_midi(
                (MidiTrack("Shadow Steps", triggers),),
                tempo=tempo,
                ppq=PPQ,
                end_tick=4 * PPQ,
                midi_format=0,
            )
        )
        receipt(folder)
        publish_directory(folder, output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source", type=Path, help="Standard MIDI format 0 or 1, or an MPC 3 XPJ"
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="new folder for the four MIDI arrangements",
    )
    parser.add_argument("--sequence", help="XPJ sequence name")
    parser.add_argument("--track", help="XPJ track name")
    mapping = parser.add_mutually_exclusive_group()
    mapping.add_argument(
        "--strike-note",
        type=int,
        help="split one source note into four sounds by velocity",
    )
    mapping.add_argument(
        "--pads", type=int, nargs=4, metavar=("LOW", "MID", "WOOD", "METAL")
    )
    parser.add_argument(
        "--channel", type=int, help="source channel, 1–16 (default: all)"
    )
    parser.add_argument(
        "--bar", type=int, default=1, help="4/4 bar to capture, starting at 1"
    )
    parser.add_argument(
        "--tempo",
        type=float,
        help="output BPM (default: project tempo for XPJ, 100 for MIDI)",
    )
    parser.add_argument(
        "--root", type=int, default=43, help="tonic MIDI note (default: 43)"
    )
    args = parser.parse_args()
    try:
        print_take(
            args.source,
            args.output,
            args.pads,
            args.bar,
            args.tempo,
            args.root,
            args.channel,
            strike_note=args.strike_note,
            sequence=args.sequence,
            track=args.track,
        )
    except (
        ValueError,
        OSError,
        KeyError,
        TypeError,
        subprocess.CalledProcessError,
    ) as error:
        parser.exit(2, f"{parser.prog}: {error}\n")
    print(args.output)


if __name__ == "__main__":
    main()
