"""Accompany a saved drum take with bass and chords from Akai's SDK Simple Synth."""

import argparse
from array import array
from contextlib import ExitStack
from dataclasses import replace
from html import escape
import json
from math import lcm
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import wave

from mpc_keygroup_builder import harmony, pad_recorder, pattern_audio
from mpc_keygroup_builder.bundle_verify import sha256
from mpc_keygroup_builder.midi_writer import MidiNote, MidiTrack, render_standard_midi
from mpc_keygroup_builder.publication import publish_directory

HERE = Path(__file__).resolve().parent
RATE = 44100
PRESETS = ("Init Saw", "Fat Bass", "Soft Pad", "Pluck")
PARTS = ("Drums", "Bass", "Chords")
MIX_GAIN = (0.50, 0.30, 0.20)


def compile_host(sdk, scratch):
    source = sdk / "examples/SimpleSynth/src/SimpleSynth.cpp"
    if not source.is_file():
        raise ValueError("choose an Akai SDK checkout containing examples/SimpleSynth/src/SimpleSynth.cpp")
    binary = scratch / "render"
    subprocess.run(["c++", "-std=c++17", "-O2", "-I", str(sdk / "framework"), "-I", str(source.parent),
                    str(HERE / "render.cpp"), "-o", str(binary)], check=True, timeout=120)
    return binary


def render_synth(binary, preset, notes, tempo, end_tick, destination):
    def frame(tick):
        return round(tick * RATE * 60 / (tempo * 480))

    frames = frame(end_tick)
    rows = [f"{frame(n.tick)} {frame(n.tick + n.duration_ticks)} {n.note} {n.velocity}" for n in notes]
    with tempfile.TemporaryFile() as pcm:
        subprocess.run([str(binary), preset, str(frames), str(tempo)], input="\n".join(rows), text=True,
                       stdout=pcm, check=True, timeout=max(30, 2 * frames / RATE))
        if pcm.tell() != frames * 2:
            raise ValueError(f"{preset}: incomplete PCM render")
        pcm.seek(0)
        with wave.open(str(destination), "wb") as wav:
            wav.setparams((1, 2, RATE, frames, "NONE", ""))
            while block := pcm.read(65536):
                wav.writeframesraw(block)


def mix_stems(folder, expected):
    peaks = [0, 0, 0, 0]
    with ExitStack() as context:
        streams = [context.enter_context(wave.open(str(folder / (name + ".wav")))) for name in PARTS]
        out = context.enter_context(wave.open(str(folder / "Mix.wav"), "wb"))
        for name, wav in zip(PARTS, streams, strict=True):
            if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getnframes()) != (1, 2, RATE, expected):
                raise ValueError(f"{name}: stem format or loop length mismatch")
        out.setparams((1, 2, RATE, expected, "NONE", ""))
        for pos in range(0, expected, 8192):
            count = min(8192, expected - pos)
            blocks = [array("h", w.readframes(count)) for w in streams]
            for i, values in enumerate(blocks):
                if sys.byteorder != "little":
                    values.byteswap()
                if len(values) != count:
                    raise ValueError("incomplete audio stem")
                peaks[i] = max(peaks[i], max(map(abs, values)))
            mix = array("h", (round(a*MIX_GAIN[0] + b*MIX_GAIN[1] + c*MIX_GAIN[2])
                              for a,b,c in zip(*blocks, strict=True)))
            peaks[3] = max(peaks[3], max(map(abs, mix)))
            if sys.byteorder != "little":
                mix.byteswap()
            out.writeframesraw(mix.tobytes())
    return dict(zip((*PARTS, "Mix"), peaks, strict=True))


def repeat_notes(events, channel, part_bars, bars):
    return tuple(MidiNote(e.tick + pos * 1920, e.duration_ticks, e.midi_note, e.velocity, channel)
                 for pos in range(0, bars, part_bars) for e in events)


def build(program, take_path, recipe_path, sdk, output, *, bass="Fat Bass", chords="Soft Pad", seed=37):
    output = pad_recorder._new_folder(output)
    take_raw = take_path.read_bytes()
    take = json.loads(take_raw)
    if not isinstance(take, dict):
        raise ValueError("choose a saved pad take JSON")
    layout, _ = pad_recorder.bank_data(program, take.get("bank"))
    drums = pad_recorder.validate_take(take, layout)
    if not drums.events:
        raise ValueError("record at least one drum hit or start with a drum recipe")
    recipe_hash = sha256(recipe_path)
    recipe = harmony.load_recipe(recipe_path)
    if recipe.beats_per_bar != 4:
        raise ValueError("choose a 4/4 harmony recipe to accompany this drum take")
    bars = lcm(drums.bars, recipe.bars)
    if bars > 64:
        raise ValueError(f"the parts first line up after {bars} bars; choose lengths that meet within 64 bars")
    pitched = harmony.generate_idea(recipe, seed=seed, tempo=drums.tempo)
    total_ticks = bars * 1920
    frames = round(total_ticks * RATE * 60 / (drums.tempo * 480))
    tracks = [MidiTrack("Drums", repeat_notes(drums.events, drums.channel, drums.bars, bars))]
    for part, channel in (("bass", recipe.bass_channel), ("chords", recipe.chord_channel)):
        events = [e for e in pitched.events if e.part == part]
        tracks.append(MidiTrack(part.title(), repeat_notes(events, channel, recipe.bars, bars)))
    midi_args = dict(tempo=drums.tempo, ppq=480, end_tick=total_ticks)
    with tempfile.TemporaryDirectory(dir=output.parent) as work, tempfile.TemporaryDirectory(dir=output.parent) as stage:
        scratch, folder = Path(work), Path(stage)
        binary = compile_host(sdk, scratch)
        repeated = replace(drums, bars=bars, events=tuple(
            replace(e, tick=e.tick + pos * 1920, step=e.step + pos * 16)
            for pos in range(0, bars, drums.bars) for e in drums.events))
        pattern = folder / "Drums.pattern.json"
        pattern.write_text(json.dumps(repeated.to_dict(), indent=2) + "\n")
        pattern_audio.render_pattern(program, pattern, folder / "Drums.wav")
        for track, preset in zip(tracks[1:], (bass, chords), strict=True):
            render_synth(binary, preset, track.notes, drums.tempo, total_ticks, folder / (track.name + ".wav"))
        for track in tracks:
            (folder / (track.name + ".mid")).write_bytes(render_standard_midi((track,), **midi_args))
        (folder / "Sketch.mid").write_bytes(render_standard_midi(tuple(tracks), **midi_args))
        peaks = mix_stems(folder, frames)
        if not all(peaks.values()):
            raise ValueError(f"a rendered part is silent: {peaks}")
        (folder / "performance.take.json").write_bytes(take_raw)
        shutil.copyfile(recipe_path, folder / "harmony.toml")
        if sha256(folder / "harmony.toml") != recipe_hash or sha256(program) != layout["program_sha256"]:
            raise ValueError("input changed while rendering the sketch")
        info = {"kind": "sdk-rhythm-section", "version": 1, "name": drums.recipe, "program": drums.program,
                "bank": layout["bank"], "program_sha256": layout["program_sha256"], "bank_fingerprint": layout["fingerprint"],
                "sdk_synth_sha256": sha256(sdk / "examples/SimpleSynth/src/SimpleSynth.cpp"),
                "host_source_sha256": sha256(HERE / "render.cpp"),
                "bars": bars, "tempo": drums.tempo, "frames": frames, "sample_rate": RATE, "seed": seed,
                "key": recipe.key, "scale": recipe.scale, "harmony": recipe.name,
                "stems": [{"part": t.name, "sound": sound, "channel": t.notes[0].channel,
                           "notes": len(t.notes), "mix_gain": gain} for t, sound, gain in
                          zip(tracks, (drums.program, bass, chords), MIX_GAIN, strict=True)],
                "pcm16_absolute_peaks": peaks, "hardware_status": "untested"}
        (folder / "sketch.json").write_text(json.dumps(info, indent=2) + "\n")
        page = (HERE / "listen.html").read_text().replace("{{name}}", escape(drums.recipe))
        details = f"{bars} bars · {drums.tempo:g} BPM · {recipe.key} {recipe.scale}"
        page = page.replace("{{details}}", escape(details))
        page = page.replace("{{sounds}}", escape(f"{drums.program} · {bass} · {chords}"))
        (folder / "index.html").write_text(page, encoding="utf-8")
        pad_recorder.receipt(folder)
        publish_directory(folder, output)
    return output / "index.html"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("program", type=Path)
    parser.add_argument("take", type=Path)
    parser.add_argument("--harmony", type=Path, required=True)
    parser.add_argument("--sdk", type=Path, required=True)
    parser.add_argument("--bass", choices=PRESETS, default="Fat Bass")
    parser.add_argument("--chords", choices=PRESETS, default="Soft Pad")
    parser.add_argument("--seed", type=int, default=37)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(build(args.program, args.take, args.harmony, args.sdk, args.output,
                    bass=args.bass, chords=args.chords, seed=args.seed))
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.exit(2, f"{parser.prog}: {error}\n")


if __name__ == "__main__":
    main()
