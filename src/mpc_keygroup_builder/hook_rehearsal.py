"""Turn a four-bar rehearsal take into Hook, Verse and Return."""

import argparse
from copy import deepcopy
from pathlib import Path

from . import xpj
from .sequence_morph import publish_project


def arrange(data, drums="Break Relay", keys="Wurli"):
    sequences = data["sequences"]
    selected = [s["value"] for s in sequences if s["key"] == data["currentSequence"]]
    if len(selected) != 1:
        raise ValueError("Select a four-bar sequence before saving the project")
    source = selected[0]
    if source["lengthBars"] != 4 or len(source["trackClipMaps"]) != 1:
        raise ValueError("Select a four-bar sequence with one clip lane")
    names = {s["value"]["name"].casefold() for s in sequences if s["value"] is not source}
    if names.intersection({"hook", "verse", "return"}):
        raise ValueError("Select a fresh take without existing Hook, Verse or Return sections")
    used = {s["key"] for s in sequences}
    slots = [i for i in range(128) if i not in used]
    if len(slots) < 2 or drums == keys:
        raise ValueError("Choose distinct drum and keys tracks and leave two free sequence slots")
    verse, returning = deepcopy(source), deepcopy(source)
    for name in (drums, keys):
        clips = [r["value"] for r in verse["trackClipMaps"][0] if r["key"] == name]
        if len(clips) != 1:
            raise ValueError(f"Expected one clip on {name}")
        clip = clips[0]
        sig = clip["timeSignatureList"]["timeSignatures"]
        if len(sig) != 1 or sig[0]["barStart"] != 0 or sig[0]["beatsPerBar"] != 4:
            raise ValueError(f"{name}: use a four-bar 4/4 clip")
        beat = sig[0]["beatLength"]
        end = source["lengthPulses"]
        if (beat <= 0 or end != 16 * beat or clip["startPulses"] != 0 or clip["endPulses"] != end
                or (clip["loop"] and (clip["loopStartPulses"], clip["loopEndPulses"]) != (0, end))):
            raise ValueError(f"{name}: use a clip spanning the entire sequence")
        events = clip["eventList"]["events"]
        played = [e for e in events if e["type"] == 3 and not e.get("muted") and 0 <= e["time"] < end]
        if not played:
            raise ValueError(f"Record a part on {name} first")
        if name == drums:
            strokes = [e for e in played if 36 <= e["note"]["note"] <= 39]
            if not strokes:
                raise ValueError("Use Break Relay drum notes 36–39")
            events[:] = [e for e in events if e["type"] != 3 or e["note"]["note"] != 38]
            back = next(r["value"] for r in returning["trackClipMaps"][0] if r["key"] == name)
            hits = back["eventList"]["events"]
            last_beat = [e for e in strokes if e["time"] >= end - beat]
            if not any(e["note"]["note"] == 39 for e in last_beat):
                at = end - beat if not last_beat else max(
                    end - max(1, beat // 4), max(e["time"] for e in last_beat) + 1
                )
                if at >= end:
                    raise ValueError("Leave room after the final drum stroke for a pickup")
                cue = deepcopy(min(strokes, key=lambda e: abs(e["time"] - at)))
                cue.update(time=at, muted=False)
                cue["note"].update(note=39, length=min(end - at, max(1, beat // 4)), probability=100, ratchet=1)
                hits.append(cue)
                hits.sort(key=lambda e: e["time"])
        else:
            first = min(e["time"] for e in played)
            cutoff = (first // (4 * beat) + 1) * 4 * beat
            events[:] = [e for e in events if e["type"] != 3 or e["time"] < cutoff]
            for event in events:
                if event["type"] == 3:
                    event["note"]["length"] = min(event["note"]["length"], cutoff - event["time"])
    source["name"] = "Hook"
    for slot, section, name in zip(slots, (verse, returning), ("Verse", "Return")):
        section["name"] = name
        sequences.append({"key": slot, "value": section})


def verify_samples(project):
    """Check track registries and active layers against this project's own media."""
    folder = project.path.with_name(project.path.stem + "_[ProjectData]")
    registered = {s["name"]: s["path"] for s in project.data["samples"]}
    for track in project.data["tracks"]:
        program = track["program"]
        local = {s["name"]: s["path"] for s in program.get("samples", [])}
        for name, path in local.items():
            if (registered.get(name) != path or not path or Path(path).name != path
                    or "\\" in path or not (folder / path).is_file()):
                raise ValueError(f"{track['name']}: unresolved sample {name!r} ({path})")
        for inst in program.get("drum", {}).get("instruments", []):
            for layer in inst["layersv"]:
                name = layer["sampleName"]
                if layer["active"] and name and (
                    name not in local or layer["sampleFile"] not in ("", local[name])
                ):
                    raise ValueError(f"{track['name']}: unresolved layer {name!r}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--output", required=True, type=Path, help="new project folder")
    parser.add_argument("--drums", default="Break Relay", help="drum track using notes 36–39")
    parser.add_argument("--keys", default="Wurli", help="keys track to thin in Verse")
    args = parser.parse_args()
    project = xpj.load(args.project)
    verify_samples(project)
    arrange(project.data, args.drums, args.keys)
    publish_project(project, args.output)
    print(args.output / args.project.name)
