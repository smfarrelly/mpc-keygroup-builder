"""Build a private offline drum recorder and render its saved performances."""

from __future__ import annotations

import argparse
import base64
from dataclasses import replace
import hashlib
from html import escape
import io
import json
from pathlib import Path
from string import Template
import tempfile
import wave

from . import ideas, pattern_audio
from .bundle_verify import sha256, verify_bundle
from .model import from_xpm
from .program_io import read_payload, xml_root
from .publication import publish_directory
from .testing import _audio_index, _integer, _resolve
from .wave_io import complete_riff_view

PPQ = 480
ASSETS = Path(__file__).parent


def _integer_range(value, low, high, field):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{field} must be an integer in {low}..{high}")
    return value


def _sample(path, layer):
    try:
        return _wav_region(path, layer)
    except (wave.Error, EOFError) as error:
        raise ValueError(f"{path.name}: expected a readable PCM WAV ({error})") from error


def _wav_region(path, layer):
    with path.open("rb") as source, wave.open(complete_riff_view(source), "rb") as stream:
        if stream.getnchannels() not in (1, 2) or stream.getsampwidth() not in (1, 2, 3, 4):
            raise ValueError(f"{path.name}: expected mono or stereo PCM with 8 to 32 bits per sample")
        frames = stream.getnframes()
        start = int(layer.findtext("SliceStart", layer.findtext("SampleStart", "0")))
        end = int(layer.findtext("SliceEnd", layer.findtext("SampleEnd", str(frames - 1))))
        if not 0 <= start <= end < frames:
            raise ValueError(f"{path.name}: invalid source region {start}..{end} for {frames} frames")
        stream.setpos(start)
        pcm = stream.readframes(end - start + 1)
        if len(pcm) != (end - start + 1) * stream.getsampwidth() * stream.getnchannels():
            raise ValueError(f"{path.name}: incomplete PCM region")
        memory = io.BytesIO()
        with wave.open(memory, "wb") as result:
            result.setparams(stream.getparams())
            result.writeframes(pcm)
    return memory.getvalue()


def bank_data(program, bank):
    if bank not in tuple("ABCDEFGH"):
        raise ValueError("bank must be A through H")
    raw, compressed = read_payload(program)
    if compressed:
        raise ValueError("choose an XML Drum Program")
    tree = xml_root(raw).find("Program")
    if tree is None or tree.get("type") != "Drum":
        raise ValueError("choose an XML Drum Program")
    model = from_xpm(program)
    indexes = _audio_index(program.parent, recursive=True)
    nodes = {int(n.get("number")): n for n in tree.findall("./Instruments/Instrument")}
    first = 1 + 16 * "ABCDEFGH".index(bank)
    assets, pads = {}, []
    for zone in model.zones:
        if not first <= zone.pad < first + 16:
            continue
        node = nodes[zone.pad]
        layers = []
        for layer in node.iter("Layer"):
            name = (layer.findtext("SampleFile") or layer.findtext("SampleName") or "").strip()
            if not name or layer.findtext("Active", "True").casefold() in ("false", "0"):
                continue
            paths = _resolve(name, indexes)
            if len(paths) != 1:
                raise ValueError(f"pad {zone.pad}: {name} resolves to {len(paths)} files")
            audio = _sample(paths[0], layer)
            key = hashlib.sha256(audio).hexdigest()
            if key not in assets:
                assets[key] = base64.b64encode(audio).decode("ascii")
            lo = int(layer.findtext("VelStart", "0"))
            hi = int(layer.findtext("VelEnd", "127"))
            if not 0 <= lo <= hi <= 127:
                raise ValueError(f"pad {zone.pad}: invalid velocity range {lo}..{hi}")
            pitch = _integer(layer.findtext("TuneCoarse"), 0) + _integer(layer.findtext("TuneFine"), 0) / 100
            layers.append({"sample": name, "low": lo, "high": hi, "audio": key, "pitch": pitch})
        if not layers:
            continue
        _integer_range(zone.midi_note, 0, 127, f"pad {zone.pad} MIDI note")
        for v in range(1, 128):
            if sum(l["low"] <= v <= l["high"] for l in layers) != 1:
                raise ValueError(f"pad {zone.pad}: requires a unique active layer for velocity {v}")
        pads.append({"pad": zone.pad, "note": zone.midi_note, "role": zone.role, "color": zone.color,
                     "oneShot": zone.playback_mode == "one-shot", "mono": zone.monophonic, "group": zone.mute_group, "layers": layers})
    if not pads:
        raise ValueError(f"no playable pads in bank {bank}")
    layout = {"program": model.name, "program_sha256": sha256(program), "bank": bank, "pads": pads}
    layout["fingerprint"] = hashlib.sha256(json.dumps(layout, sort_keys=True).encode()).hexdigest()
    return layout, assets


def validate_take(take, layout):
    if not isinstance(take, dict) or take.get("kind") != "mpc-pad-take" or type(take.get("version")) is not int or take["version"] != 1:
        raise ValueError("choose a version 1 MPC pad take JSON file")
    if any(take.get(key) != layout[key] for key in ("fingerprint", "program", "bank")):
        raise ValueError("take belongs to a different kit, sample set or bank")
    tempo = take.get("tempo")
    if type(tempo) not in (int, float) or not 20 <= tempo <= 300:
        raise ValueError("tempo must be 20..300 BPM")
    bars = _integer_range(take.get("bars"), 1, 64, "bars")
    channel = _integer_range(take.get("channel"), 1, 16, "channel")
    if take.get("ppq") != PPQ or not isinstance(take.get("events"), list):
        raise ValueError("take requires 480 PPQ and an events list")
    name = take.get("name")
    if not isinstance(name, str) or not name.strip() or len(name) > 120:
        raise ValueError("take name must contain 1..120 characters")
    pads = {p["pad"]: p for p in layout["pads"]}
    events = []
    end = bars * 4 * PPQ
    for item in take["events"]:
        if not isinstance(item, dict):
            raise ValueError("each recorded hit must be an object")
        tick = _integer_range(item.get("tick"), 0, end - 1, "tick")
        duration = _integer_range(item.get("duration_ticks"), 1, end - tick, "duration_ticks")
        pad = _integer_range(item.get("pad"), 1, 128, "pad")
        velocity = _integer_range(item.get("velocity"), 1, 127, "velocity")
        if pad not in pads:
            raise ValueError(f"pad {pad} unavailable on this bank")
        p = pads[pad]
        events.append(ideas.DrumEvent(tick // 120, tick, duration, p["role"], pad, ideas._label(pad),
                                      p["note"], velocity, p["layers"][0]["sample"]))
    events.sort(key=lambda event: event.tick)
    return ideas.DrumIdea(1, name, layout["program"], None, 0, tempo, 1.0, bars, 16,
                          0.5, channel, PPQ, tuple(events))


def receipt(folder):
    hashes = {p.relative_to(folder).as_posix(): sha256(p) for p in sorted(folder.rglob("*")) if p.is_file()}
    (folder / "checksums.json").write_text(json.dumps(hashes, indent=2) + "\n")
    verify_bundle(folder)


def _new_folder(output):
    output = output.expanduser().absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"choose a new output folder: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    return output


def initial_take(layout, tempo, bars, recipe=None, seed=37, program=None):
    events = []
    name = "My groove"
    if recipe:
        r = ideas.load_recipe(recipe)
        model = from_xpm(program)
        pads = {p["pad"] for p in layout["pads"]}
        model = replace(model, zones=tuple(z for z in model.zones if z.pad in pads))
        pattern = ideas.generate_idea(r, model, seed=seed, tempo=tempo)
        bars, name = pattern.bars, r.name
        events = [{field: getattr(e, field) for field in ("tick", "pad", "velocity", "duration_ticks")}
                  for e in pattern.events]
        for hit in events:
            hit["duration_ticks"] = min(hit["duration_ticks"], bars * 4 * PPQ - hit["tick"])
    take = {"kind": "mpc-pad-take", "version": 1, "fingerprint": layout["fingerprint"], "bank": layout["bank"],
            "program": layout["program"], "name": name, "bars": bars, "tempo": tempo, "ppq": PPQ,
            "channel": r.channel if recipe else 10, "events": events}
    validate_take(take, layout)
    return take


def build(program, output, *, bank="A", tempo=96, bars=2, recipe=None, seed=37):
    output = _new_folder(output)
    layout, samples = bank_data(program, bank)
    take = initial_take(layout, tempo, bars, recipe, seed, program)
    data = json.dumps({"layout": layout, "samples": samples, "initial": take}, separators=(",", ":"))
    template = Template((ASSETS / "pad_recorder.html").read_text())
    page = template.substitute(program=escape(layout["program"]), bank=bank,
                               data=data.replace("<", "\\u003c"),
                               script=(ASSETS / "pad_recorder.js").read_text())
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".pad-recorder-") as tmp:
        folder = Path(tmp)
        (folder / "index.html").write_text(page, encoding="utf-8")
        (folder / "starter.take.json").write_text(json.dumps(take, indent=2) + "\n")
        receipt(folder)
        publish_directory(folder, output)
    return output / "index.html"


def render(program, take_path, output):
    output = _new_folder(output)
    take = json.loads(take_path.read_text(encoding="utf-8"))
    if not isinstance(take, dict):
        raise ValueError("expected a take JSON object")
    layout, _ = bank_data(program, take.get("bank"))
    idea = validate_take(take, layout)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".pad-take-") as tmp:
        folder = Path(tmp)
        pattern, _ = ideas.write_outputs(folder / "pattern", [program, take_path],
                                         json.dumps(idea.to_dict(), indent=2) + "\n", ideas.render_midi(idea), force=False)
        pattern_audio.render_pattern(program, pattern, folder / "listen.wav")
        (folder / "performance.take.json").write_text(json.dumps(take, indent=2) + "\n")
        receipt(folder)
        publish_directory(folder, output)
    return output / "listen.wav"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    make = commands.add_parser("build", help="build a standalone browser page from one bank")
    make.add_argument("program", type=Path)
    make.add_argument("--bank", type=str.upper, choices=tuple("ABCDEFGH"), default="A")
    make.add_argument("--tempo", type=float, default=96)
    make.add_argument("--bars", type=int, default=2, help="empty take length in 4/4 bars")
    make.add_argument("--recipe", type=Path, help="start with this drum recipe and its bar length")
    make.add_argument("--seed", type=int, default=37)
    make.add_argument("--output", type=Path, required=True, help="new folder for offline recorder")
    save = commands.add_parser("render", help="turn a downloaded take into WAV, MIDI and a timing report")
    save.add_argument("program", type=Path)
    save.add_argument("take", type=Path)
    save.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "build":
        print(build(args.program, args.output, bank=args.bank, tempo=args.tempo, bars=args.bars,
                    recipe=args.recipe, seed=args.seed))
    else:
        print(render(args.program, args.take, args.output))
    return 0
