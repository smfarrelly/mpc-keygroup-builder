"""Evolve native MPC 3 note sequences while retaining their project context."""

import argparse
from collections import defaultdict
from copy import deepcopy
from dataclasses import astuple
import gzip
import hashlib
import json
from pathlib import Path, PureWindowsPath
import shutil
from tempfile import mkdtemp

from . import xpj
from .publication import publish_directory


def score(seed, track, lane, tick):
    identity = json.dumps([seed, track, lane, tick]).encode()
    return int.from_bytes(hashlib.sha256(identity).digest()[:8], "big") % 100


def morph_clip(clip, style, amount, seed, track, lane):
    events = clip["eventList"]["events"]
    groups = defaultdict(list)
    for event in events:
        if event["type"] == 3:
            groups[event["time"]].append(event)
    if not groups or not amount:
        return 0
    signatures = clip.get("timeSignatureList", {}).get("timeSignatures", [])
    if len(signatures) != 1 or signatures[0]["barStart"] != 0:
        raise ValueError(f"{track}: morphing needs a single meter starting at bar 1")
    beat = signatures[0]["beatLength"]
    bar = beat * signatures[0]["beatsPerBar"]
    if beat < 4 or bar <= 0:
        raise ValueError(f"{track}: invalid meter")
    start, end = clip["startPulses"], clip["endPulses"]
    if clip.get("loop"):
        start = max(start, clip["loopStartPulses"])
        end = min(end, clip["loopEndPulses"])
    ticks = sorted(groups)
    anchors = set()
    first_in_bar = {}
    strongest = {}
    for tick in ticks:
        if start <= tick < end and any(not e.get("muted") for e in groups[tick]):
            number = tick // bar
            first_in_bar.setdefault(number, tick)
            strength = max(e["note"]["velocity"] for e in groups[tick] if not e.get("muted"))
            if number not in strongest or strength > strongest[number][0]:
                strongest[number] = strength, tick
    anchors.update(first_in_bar.values())
    anchors.update(t for _, t in strongest.values())
    removed, added = set(), []
    sounding_until = {}
    changed = 0
    for i, tick in enumerate(ticks):
        notes = groups[tick]
        for e in notes:
            n = e["note"]
            pitch = (e.get("channel", 0), n["note"])
            sounding_until[pitch] = max(sounding_until.get(pitch, 0), tick + n["length"])
        if not start <= tick < end or any(e.get("muted") for e in notes):
            continue
        if score(seed, track, lane, tick) >= amount:
            continue
        if style == "space":
            if tick not in anchors:
                removed.add(tick)
                changed += 1
            continue
        step = beat // 4
        release = max(sounding_until[e.get("channel", 0), e["note"]["note"]] for e in notes)
        delay = max(2 * step, ((release - tick + step - 1) // step) * step)
        at = tick + delay
        stop = min(end, (tick // bar + 1) * bar, ticks[i + 1] if i + 1 < len(ticks) else end)
        if stop - at < step // 2:
            continue
        for event in notes:
            echo = deepcopy(event)
            echo["time"] = at
            note = echo["note"]
            note["length"] = min(max(1, note["length"]), stop - at, step)
            note["velocity"] *= 0.65
            added.append(echo)
        changed += 1
    if changed:
        kept = [e for e in events if e["type"] != 3 or e["time"] not in removed]
        clip["eventList"]["events"] = sorted(kept + added, key=lambda e: e["time"])
    return changed


def evolve(data, sequence, tracks, style, amounts, seed):
    sequences = data["sequences"]
    matches = [s for s in sequences if (
        s["key"] == data["currentSequence"] if sequence is None else s["value"]["name"] == sequence
    )]
    if len(matches) != 1:
        raise ValueError("Select a uniquely named sequence with --sequence")
    source = matches[0]["value"]
    eligible = {t["name"] for t in data["tracks"] if t["program"]["type"] in (0, 1, 3, 4)}
    selected = set(tracks) or eligible
    if selected - eligible:
        raise ValueError(f"Unknown or unsupported tracks: {sorted(selected - eligible)}")
    if style not in ("answer", "space") or not amounts or len(set(amounts)) != len(amounts) or any(
        type(a) is not int or not 0 <= a <= 100 for a in amounts
    ):
        raise ValueError("Choose answer or space and distinct integer amounts from 0 to 100")
    played = {r["key"] for lane in source["trackClipMaps"] for r in lane
              if any(e["type"] == 3 and not e.get("muted") for e in r["value"]["eventList"]["events"])}
    if not selected & played or set(tracks) - played:
        raise ValueError("Choose tracks containing played notes in the selected sequence")
    used = {s["key"] for s in sequences}
    slots = [i for i in range(128) if i not in used]
    if len(slots) < len(amounts):
        raise ValueError("The project has too few free sequence slots")
    names = {s["value"]["name"] for s in sequences}
    report = []
    for slot, amount in zip(slots, amounts):
        variant = deepcopy(source)
        base = f"{style.title()} {amount}%"
        name = base
        suffix = 2
        while name in names:
            name = f"{base} ({suffix})"
            suffix += 1
        names.add(name)
        variant["name"] = name
        counts = defaultdict(int)
        for index, lane in enumerate(variant["trackClipMaps"]):
            for row in lane:
                track = row["key"]
                if track in selected & played:
                    counts[track] += morph_clip(row["value"], style, amount, seed, track, index)
        sequences.append({"key": slot, "value": variant})
        report.append((name, dict(counts)))
    return report


def build(source, output, sequence, tracks, style, amounts, seed):
    project = xpj.load(source)
    if project.generation != 3:
        raise ValueError("Save the source as an MPC 3 project first")
    report = evolve(project.data, sequence, tracks, style, amounts, seed)
    companion = source.with_name(source.stem + "_[ProjectData]")
    if output.exists() or output.is_symlink():
        raise ValueError(f"Choose a new output folder: {output}")
    if output.resolve().is_relative_to(companion.resolve()):
        raise ValueError("Choose an output folder outside the source ProjectData")
    if companion.is_symlink() or (companion.exists() and not companion.is_dir()):
        raise ValueError("Expected a regular ProjectData directory")
    for p in companion.rglob("*"):
        if p.is_symlink() or not (p.is_file() or p.is_dir()):
            raise ValueError(f"Unsupported ProjectData entry: {p}")
    for sample in project.data.get("samples", []):
        path = PureWindowsPath(sample["path"])
        if path.anchor or ".." in path.parts or not companion.joinpath(*path.parts).is_file():
            raise ValueError(f"Save a self-contained project with its samples first: {path}")
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(mkdtemp(prefix=".sequence-morph-", dir=output.parent))
    try:
        if companion.exists():
            shutil.copytree(companion, stage / companion.name)
        target = stage / source.name
        payload = "\n".join(astuple(project.header)) + "\n" + json.dumps(project.document, separators=(",", ":"))
        target.write_bytes(gzip.compress(payload.encode(), mtime=0))
        if xpj.load(target).document != project.document:
            raise ValueError("Output project failed readback")
        publish_directory(stage, output)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="self-contained MPC 3 .xpj")
    parser.add_argument("--output", required=True, type=Path, help="new folder for the playable copy")
    parser.add_argument("--sequence", help="sequence name (default: currently selected sequence)")
    parser.add_argument("--track", action="append", default=[], help="track name, repeat to select several")
    parser.add_argument("--style", choices=["answer", "space"], default="answer")
    parser.add_argument("--amount", type=int, nargs="+", default=[30, 65, 100], help="distinct strengths, 0 to 100")
    parser.add_argument("--seed", type=int, default=37, help="repeatable choice of onsets")
    args = parser.parse_args()
    for name, counts in build(args.project, args.output, args.sequence, args.track, args.style, args.amount, args.seed):
        print(name, "— changed onsets:", ", ".join(f"{track} {n}" for track, n in counts.items()))
    print(args.output / args.project.name)
