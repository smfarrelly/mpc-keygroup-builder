"""Build two private project copies from a captured Scratchpad, jam and XL3 template."""

from copy import deepcopy
import gzip
import json
from pathlib import Path
import shutil
import wave

from audio import RATE, render, values
from mpc_keygroup_builder import cli, xpj
from mpc_keygroup_builder.bundle_verify import sha256

DRUMS = "Pocket Layers Print"
KEYS = "Bloom Keys Print"
JAM_DRUMS = "Vinyl SP From Mars 01 FG COLORS"


def track_map(data):
    return {t["name"]: t for t in data["tracks"]}


def write_mono(path, stereo, gain=1.0):
    pcm = values(stereo)[::2]
    for i, sample in enumerate(pcm):
        pcm[i] = max(-32768, min(32767, round(sample * gain)))
    # A short fade at the end of a finite sample protects against a cutoff mid-cycle.
    fade = min(220, len(pcm))
    for i in range(fade):
        pcm[len(pcm) - fade + i] = round(
            pcm[len(pcm) - fade + i] * (fade - 1 - i) / max(1, fade - 1)
        )
    if not any(pcm):
        raise ValueError(f"empty performance print: {path.name}")
    import sys

    if sys.byteorder != "little":
        pcm.byteswap()
    with wave.open(str(path), "wb") as w:
        w.setparams((1, 2, RATE, 0, "NONE", ""))
        w.writeframes(pcm.tobytes())
    return len(pcm)


def drum_print(binary, scratch, content, layout, track, folder):
    t = deepcopy(track)
    t["name"] = t["program"]["name"] = DRUMS
    p = t["program"]
    sample_template = p["samples"][0]
    samples = []
    for i, instrument in enumerate(p["drum"]["instruments"]):
        for layer in instrument["layersv"]:
            cli.disable_layer(layer)
        p["programPads"]["pads"][f"value{i}"] = 0
    for pad in layout["pads"]:
        n = pad["pad"]
        instrument = p["drum"]["instruments"][n - 1]
        p["padNoteMap"]["noteForPad"][f"value{n - 1}"] = pad["note"]
        p["programPads"]["pads"][f"value{n - 1}"] = pad["color"] or 0
        instrument["whichMuteGroup"] = pad["group"]
        instrument["monophonic"] = True
        instrument["coarseTune"] = instrument["fineTune"] = 0
        layers = sorted(pad["layers"], key=lambda layer: layer["low"])
        if len(layers) > len(instrument["layersv"]):
            raise ValueError(f"template has too few velocity layers for pad {n}")
        # Pocket Layers moves the top layer boundary to velocity 96 by default.
        top = layers[-2]["high"] + 1 if len(layers) > 1 else 96
        bands = [[] for layer in layers]
        for velocity in range(1, 128):
            mapped = (
                1 + (velocity - 1) * (top - 1) // 95
                if velocity < 96
                else top + (velocity - 96) * (127 - top) // 31
            )
            index = next(k for k, layer in enumerate(layers) if mapped <= layer["high"])
            bands[index].append(velocity)
        for j, velocities in enumerate(bands):
            if not velocities:
                raise ValueError(f"inaudible velocity layer on pad {n}")
            vel = velocities[len(velocities) // 2]
            name = f"FG Pocket Pad {n:02} Layer {j + 1}.wav"
            raw = render(
                binary,
                scratch,
                "PocketLayers",
                RATE * 2,
                [(0, "on", 35 + n, vel)],
                content=content,
            )
            frames = write_mono(folder / name, raw, 127 / vel)
            l = instrument["layersv"][j]
            cli.configure_layer(
                l,
                cli.Sample(
                    0, folder / name, frames, velocities[0] if j else 0, velocities[-1]
                ),
            )
            l.update(
                keyTrackEnable=False,
                pitch=0.0,
                coarseTune=0,
                fineTune=0,
                loop=False,
                loopMode=0,
            )
            l["sliceInfo"]["LoopMode"] = 0
            entry = deepcopy(sample_template)
            entry.update(name=Path(name).stem, path=name)
            entry["metadata"].update(rootNote=0, tune=0.0, tempo=0.0, key="")
            samples.append(entry)
    p["samples"] = samples
    return t


def keys_print(binary, scratch, track, folder):
    t = deepcopy(track)
    t["name"] = t["program"]["name"] = KEYS
    p = t["program"]
    universal, template = p["drum"]["instruments"][:2]
    groups = []
    for key in range(12, 121, 6):
        path = folder / f"FG Bloom Root {key:03}.wav"
        raw = render(
            binary,
            scratch,
            "BloomKeys",
            RATE * 4,
            [(0, "on", key, 100), (3 * RATE, "off", key, 0)],
        )
        frames = write_mono(path, raw)
        groups.append(cli.SampleGroup(key, (cli.Sample(key, path, frames),)))
    instruments = []
    for group, (low, high) in zip(groups, cli.note_ranges(groups), strict=True):
        i = deepcopy(template)
        cli.configure_instrument(i, group)
        i.update(lowNote=low, highNote=high, coarseTune=0, fineTune=0, warpEnable=False)
        l = i["layersv"][0]
        l.update(pitch=0.0, coarseTune=0, fineTune=0, loop=False, loopMode=0)
        l["sliceInfo"]["LoopMode"] = 0
        instruments.append(i)
    cli.configure_instrument(universal, groups[0])
    universal["lowNote"] = universal["highNote"] = groups[0].note
    p["drum"]["instruments"] = [universal, *instruments]
    p["keygroup"]["numKeygroups"] = len(groups)
    p["samples"] = [
        dict(
            version=1,
            name=g.layers[0].path.stem,
            path=g.layers[0].path.name,
            loadImpl=0,
            metadata=dict(tempo=0.0, rootNote=g.note, tune=0.0, key=""),
        )
        for g in groups
    ]
    return t


def sequence(data, jam, demo):
    source = jam["sequences"][0]
    s = deepcopy(source)
    v = s["value"]
    if (
        v["lengthBars"] != 4
        or v["lengthPulses"] != 15360
        or len(v["trackClipMaps"]) != 1
    ):
        raise ValueError("use a four-bar 4/4 MPC jam capture")
    donor = {row["key"]: row["value"] for row in v["trackClipMaps"][0]}
    voices = {"Main Drums": JAM_DRUMS, "Pluck Bass": "Pluck Bass", "Wurli": "Wurli"}
    original_drums = track_map(jam)[JAM_DRUMS]["program"]
    main = track_map(data)["Main Drums"]["program"]
    if main["padNoteMap"] != original_drums["padNoteMap"]:
        raise ValueError("the captured performance uses a different main drum note map")
    rows = []
    counts = {}
    for track in data["tracks"]:
        name = track["name"]
        clip = deepcopy(donor.get(voices.get(name, name), donor["Wurli"]))
        clip["name"] = name
        events = clip["eventList"]["events"]
        clip["eventList"]["events"] = [
            e
            for e in events
            if demo and name in voices and e["type"] == 3 and "note" in e
        ]
        counts[name] = len(clip["eventList"]["events"])
        rows.append({"key": name, "value": clip})
    if demo and any(counts[n] == 0 for n in voices):
        raise ValueError("expected recorded drum, bass and Wurli notes")
    v["trackClipMaps"] = [sorted(rows, key=lambda r: r["key"])]
    v["name"] = "Four-bar jam" if demo else "First idea"
    data["sequences"] = [s]
    data["currentSequence"] = s["key"]
    data["masterTempo"] = jam["masterTempo"]
    data["masterTempoEnabled"] = jam["masterTempoEnabled"]
    return {n: k for n, k in counts.items() if k}


def build_projects(
    binary, scratch, content, layout, master_path, jam_path, boot_path, output
):
    master = xpj.load(master_path)
    data = master.data
    jam = xpj.load(jam_path).data
    boot = xpj.load(boot_path).data
    by_name = track_map(data)
    if data["sequences"] or any(
        t["arrangementClipMap"] or t["sharedClipMap"] for t in data["tracks"]
    ):
        raise ValueError("use the unsequenced v02 master capture")
    for name in ("Clip", "Audio 001"):
        if by_name[name]["program"]["samples"]:
            raise ValueError(f"expected empty placeholder: {name}")
    origin = master_path.with_name(master_path.stem + "_[ProjectData]")
    fresh = scratch / "prints"
    fresh.mkdir()
    drums = drum_print(binary, scratch, content, layout, by_name["Main Drums"], fresh)
    keys = keys_print(binary, scratch, by_name["Pluck Bass"], fresh)
    replacements = {"Clip": drums, "Audio 001": keys}
    data["tracks"] = [replacements.get(t["name"], t) for t in data["tracks"]]
    for item in data["clipPlayerData"]["trackClipTransportMap"]:
        if item["key"] in replacements:
            item["key"] = replacements[item["key"]]["name"]
    # Use the actual three bus routes and existing mixer Learn bindings from Boot.
    routes = track_map(boot)
    for t in data["tracks"]:
        name = t["name"]
        t["recordArm"] = name == "Main Drums"
        if name in {"Main Drums", "Shots", DRUMS}:
            role = "3 - Vinyl SP From Mars"
        elif name in {"Pluck Bass", "Sub Smooth", KEYS}:
            role = "4 - Sub Smooth"
        elif name in {"Wurli", "Dark FM", "Glass Howl"}:
            role = "2 - Jura"
        else:
            continue
        t["program"]["mixable"]["audioRoute"] = deepcopy(
            routes[role]["program"]["mixable"]["audioRoute"]
        )
    mixer_names = {"Submix 1", "Submix 2", "Submix 3", "Out 1/2"}
    controls = [
        c
        for c in boot["midiLearnSettings"]["controls"]
        if c["mapping"]["channel"] == 16
        and c["control"]["targetData"]
        and all(t.get("track") in mixer_names for t in c["control"]["targetData"])
    ]
    if {
        c["control"]["name"]
        for c in controls
        if c["control"]["name"].endswith("(Volume)")
    } != {n + " (Volume)" for n in mixer_names}:
        raise ValueError("missing Boot mixer volume bindings")
    data["midiLearnSettings"]["controls"] = deepcopy(controls)
    data["currentTrackIndex"] = next(
        i for i, t in enumerate(data["tracks"]) if t["name"] == "Main Drums"
    )
    data["engineMode"] = jam["engineMode"]
    sources = {}
    registry = list(data["samples"])
    for row in registry:
        name = row["path"]
        if (
            Path(name).name != name
            or "\\" in name
            or not name
            or (origin / name).is_symlink()
            or not (origin / name).is_file()
        ):
            raise ValueError(f"unavailable project sample: {name}")
        sources[name] = origin / name
    for t in (drums, keys):
        for row in t["program"]["samples"]:
            name = row["path"]
            if name.casefold() in {n.casefold() for n in sources}:
                raise ValueError(f"sample collision: {name}")
            sources[name] = fresh / name
            registry.append(row)
    data["samples"] = registry
    hashes = {name: sha256(path) for name, path in sources.items()}
    target = output / "Projects" / "Playable Scratchpad"
    target.mkdir(parents=True)
    header = "\n".join(vars(master.header).values()) + "\n"
    results = {}
    for title, demo in [("01 Sit Down", False), ("02 Four Bar Jam", True)]:
        notes = sequence(data, jam, demo)
        companion = target / (title + "_[ProjectData]")
        companion.mkdir()
        for name, source in sources.items():
            dest = companion / name
            shutil.copyfile(source, dest)
            if sha256(dest) != hashes[name]:
                raise ValueError(f"sample copy mismatch: {name}")
        p = target / (title + ".xpj")
        p.write_bytes(
            gzip.compress(
                (
                    header
                    + json.dumps(
                        master.document, ensure_ascii=False, separators=(",", ":")
                    )
                ).encode(),
                mtime=0,
            )
        )
        saved = xpj.load(p).data
        if saved != data:
            raise ValueError("XPJ did not round-trip")
        sample_names = {sample["name"] for sample in saved["samples"]}
        for t in saved["tracks"]:
            for instrument in t["program"].get("drum", {}).get("instruments", []):
                for layer in instrument["layersv"]:
                    if (
                        layer["active"]
                        and layer["sampleName"]
                        and layer["sampleName"] not in sample_names
                    ):
                        raise ValueError(
                            f"{t['name']}: unresolved layer {layer['sampleName']}"
                        )
            for row in t["program"]["samples"]:
                if row["path"] not in sources:
                    raise ValueError(f"unresolved track sample: {row['path']}")
        results[title] = {
            "file": p.relative_to(output).as_posix(),
            "samples": len(sources),
            "notes": notes,
            "selected": data["tracks"][data["currentTrackIndex"]]["name"],
        }
    return results
