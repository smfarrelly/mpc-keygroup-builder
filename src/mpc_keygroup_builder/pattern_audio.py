"""Render a generated Drum Idea at its saved tempo with sample and velocity evidence."""

from array import array
import json
from pathlib import Path

from . import audition
from .program_io import read_payload, xml_root
from .report_io import write_json
from .testing import _audio_index, _boolean, _integer


def _integer_in(value, low, high, name):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"drum idea requires {name} in {low}..{high}")
    return value


def render_pattern(program: Path, pattern: Path, output: Path) -> dict:
    output, receipt = audition.output_paths(program, output)
    if pattern.resolve() in (receipt, output):
        raise ValueError("choose a different output stem to keep the source drum idea JSON")
    idea = json.loads(pattern.read_text(encoding="utf-8"))
    if not isinstance(idea, dict) or idea.get("schema_version") != 1:
        raise ValueError("expected an mpc-drum-idea JSON file with schema_version=1")
    raw, compressed = read_payload(program)
    if compressed:
        raise ValueError("pattern audition requires an XML Drum Program")
    instrument = xml_root(raw).find("Program")
    if instrument is None or instrument.get("type") != "Drum":
        raise ValueError("pattern audition requires an XML Drum Program")
    ppq = _integer_in(idea.get("ppq"), 1, 32767, "ppq")
    bars = _integer_in(idea.get("bars"), 1, 64, "bars")
    tempo = idea.get("tempo")
    if type(tempo) not in (int, float) or not 20 <= tempo <= 300:
        raise ValueError("drum idea tempo must be 20..300 BPM")
    if idea.get("program") != instrument.findtext("ProgramName"):
        raise ValueError("idea names a different program; use the corresponding XPM")
    events = idea.get("events")
    if not isinstance(events, list):
        raise ValueError("drum idea requires an events list")
    frames_per_tick = 60 * audition.OUTPUT_RATE / (tempo * ppq)
    end_tick = bars * 4 * ppq
    frames = round(end_tick * frames_per_tick)
    pads = {int(node.attrib["number"]): node for node in instrument.findall("./Instruments/Instrument")}
    notes = {int(node.attrib["number"]): _integer(node.findtext("Note"), -1)
             for node in instrument.findall("./PadNoteMap/PadNote")}
    indexes = _audio_index(program.parent, recursive=True)
    if output.exists():
        references = {(layer.findtext("SampleFile") or layer.findtext("SampleName") or "").strip()
                      for layer in instrument.iter("Layer")}
        audition.protect_sample_output(output, references, indexes)
    selected = []
    for event in events:
        if not isinstance(event, dict):
            raise ValueError("each drum idea event must be an object")
        tick = _integer_in(event.get("tick"), 0, end_tick - 1, "tick")
        pad = _integer_in(event.get("pad"), 1, 128, "pad")
        velocity = _integer_in(event.get("velocity"), 1, 127, "velocity")
        note = _integer_in(event.get("midi_note"), 0, 127, "midi_note")
        node = pads.get(pad)
        if node is None or notes.get(pad) != note:
            raise ValueError(f"pad {pad}: MIDI note differs from the program; check the idea's layout")
        layers = [(l, (l.findtext("SampleFile") or l.findtext("SampleName") or "").strip())
                  for l in node.iter("Layer") if l.findtext("Active", "True").casefold() not in ("false", "0")]
        layers = [(l, ref) for l, ref in layers if ref]
        if not layers or layers[0][1] != event.get("sample"):
            raise ValueError(f"pad {pad}: idea sample differs from the program; check the kit or layout")
        matches = [(l, ref) for l, ref in layers
                   if _integer(l.findtext("VelStart"), 0) <= velocity <= _integer(l.findtext("VelEnd"), 127)]
        if len(matches) != 1:
            raise ValueError(f"pad {pad}: expected one matching layer at velocity {velocity}, found {len(matches)}")
        duration = _integer_in(event.get("duration_ticks"), 1, end_tick, "duration_ticks")
        layer, reference = matches[0]
        selected.append((tick, pad, velocity, duration, node, layer, reference))

    # Walk backwards so each voice knows when a later hit on the same mono pad or
    # mute group will cut it off. Equal-tick events retain file order.
    mix = array("f", [0]) * frames
    next_pad, next_group, cache = {}, {}, {}
    log = []
    for tick, pad, velocity, duration, node, layer, reference in reversed(sorted(selected, key=lambda row: row[0])):
        start = round(tick * frames_per_tick)
        stop = frames
        if not _boolean(node.findtext("OneShot", "False")):
            stop = min(stop, round((tick + duration) * frames_per_tick))
        if _boolean(node.findtext("Mono")):
            stop = min(stop, next_pad.get(pad, frames))
        next_pad[pad] = start
        group = _integer(node.findtext("MuteGroup"), 0)
        if group:
            stop = min(stop, next_group.get(group, frames))
            next_group[group] = start
        if layer not in cache:
            samples, rate, _, _, pitch = audition.drum_layer_audio(layer, reference, indexes)
            cache[layer] = audition.resample(samples, rate, pitch)
        clip = cache[layer]
        count = min(len(clip), stop - start)
        for i in range(count):
            mix[start + i] += clip[i] * velocity / 127
        log.append({"tick": tick, "pad": pad, "velocity": velocity, "sample": reference,
                    "start_frame": start, "played_frames": count})
    output.parent.mkdir(parents=True, exist_ok=True)
    audition.write_wav(output, mix)
    result = {"kind": "mpc-drum-idea-audition", "program": idea["program"], "recipe": idea.get("recipe"),
              "bars": bars, "tempo": tempo, "sample_rate": audition.OUTPUT_RATE, "frames": frames,
              "events": list(reversed(log)), "hardware_status": "untested",
              "limitations": "Dry mono sum with velocity scaling, mono retrigger and mute groups. Tails stop at the loop boundary. MPC effects, envelopes and mixer processing are omitted."}
    write_json(result, receipt, (program, pattern, output))
    return result
