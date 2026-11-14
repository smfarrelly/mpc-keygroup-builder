"""Run a local retrospective MIDI recorder using the playable Scratchpad's samples."""

import argparse
from copy import deepcopy
import gzip
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import wave
from pathlib import Path
import shutil
import struct
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit
import webbrowser

from . import xpj
from .midi_writer import variable_length
from .publication import publish_directory
from .wave_io import complete_riff_view

END = 15360
ASSETS = Path(__file__).with_name("keep_studio")


def catalog(project):
    companion = project.with_name(project.stem + "_[ProjectData]")
    instruments, samples = {}, []
    ids = {}
    rates = {}
    data = xpj.load(project).data
    sequences = data.get("sequences", [])
    if len(sequences) != 1 or sequences[0]["value"]["lengthBars"] != 4:
        raise ValueError("Choose the four-bar Scratchpad demo XPJ.")
    clips = sequences[0]["value"]["trackClipMaps"][0]
    if not any(
        e["type"] == 3 for row in clips for e in row["value"]["eventList"]["events"]
    ):
        raise ValueError(
            "Choose the performed demo, 02 Four Bar Jam.xpj, for its native note template."
        )
    for track in data["tracks"]:
        program = track["program"]
        kind = program["type"]
        if kind not in (0, 1):
            continue
        zones = []
        for index, inst in enumerate(program["drum"]["instruments"]):
            if kind == 1 and index == 0:  # MPC's common keygroup settings
                continue
            for layer in inst["layersv"]:
                if not layer["active"] or not layer["sampleName"]:
                    continue
                filename = layer["sampleFile"] or (layer["sampleName"] + ".wav")
                path = (companion / filename).resolve()
                if path.parent != companion.resolve() or not path.is_file():
                    raise ValueError(
                        f"{track['name']}: missing local sample {filename}"
                    )
                if path not in ids:
                    ids[path] = len(samples)
                    samples.append(path)
                    with (
                        path.open("rb") as source,
                        wave.open(complete_riff_view(source)) as wav,
                    ):
                        rates[path] = wav.getframerate()
                note = (
                    program["padNoteMap"]["noteForPad"][f"value{index}"]
                    if kind == 0
                    else layer["rootNote"]
                )
                tune = (
                    inst.get("coarseTune", 0)
                    + layer.get("coarseTune", 0)
                    + (inst.get("fineTune", 0) + layer.get("fineTune", 0)) / 100
                )
                zones.append(
                    dict(
                        id=ids[path],
                        rate=rates[path],
                        pad=index if kind == 0 else None,
                        mono=kind == 0 and inst.get("monophonic", False),
                        lo=note if kind == 0 else inst["lowNote"],
                        hi=note if kind == 0 else inst["highNote"],
                        root=note,
                        tune=tune,
                        low=layer["velocityStart"],
                        high=layer["velocityEnd"],
                        start=layer["sliceInfo"]["Start"],
                        end=layer["sliceInfo"]["End"],
                        group=inst.get("whichMuteGroup", 0) if kind == 0 else 0,
                    )
                )
        if zones:
            instruments[track["name"]] = dict(drum=kind == 0, zones=zones)
    return instruments, samples


def validate(take, instruments):
    if not isinstance(take, dict) or take.get("format") != "keep-that-take/1":
        raise ValueError("Choose a Keep That Take JSON file.")
    seconds = take.get("seconds")
    if type(seconds) not in (int, float) or not 0.05 <= seconds <= 120:
        raise ValueError("The loop must be between 0.05 and 120 seconds.")
    if not isinstance(take.get("name"), str) or not 1 <= len(take["name"]) <= 64:
        raise ValueError("Give the idea a name of 1 to 64 characters.")
    bpm = take.get("tempo", 120)
    if type(bpm) not in (int, float) or not 20 <= bpm <= 300:
        raise ValueError("Choose a tempo between 20 and 300 BPM.")
    snap = take.get("snap", 0)
    if (
        type(snap) not in (int, float)
        or not 0 <= snap <= 100
        or any(type(take[k]) != bool for k in ("click", "free") if k in take)
    ):
        raise ValueError("Invalid playback settings.")
    layers = take.get("layers")
    if not isinstance(layers, list) or not 1 <= len(layers) <= 128:
        raise ValueError("Keep between 1 and 128 layers before saving.")
    for layer in layers:
        if (
            not isinstance(layer, dict)
            or not isinstance(layer.get("track"), str)
            or layer["track"] not in instruments
        ):
            raise ValueError("A layer requires an instrument in this Scratchpad.")
        alt = layer.get("audition")
        if alt is not None and (
            not isinstance(alt, str)
            or alt not in instruments
            or not instruments[alt]["drum"]
            or not instruments[layer["track"]]["drum"]
        ):
            raise ValueError("Choose a drum instrument for the audition kit.")
        events = layer.get("events")
        if not isinstance(events, list) or not 1 <= len(events) <= 100000:
            raise ValueError("Invalid MIDI event list.")
        held = set()
        pedal = 0
        previous = 0
        for e in events:
            if not isinstance(e, list) or len(e) != 4 or any(type(x) != int for x in e):
                raise ValueError("Malformed MIDI event.")
            tick, status, key, value = e
            if (
                not previous <= tick <= END
                or not 0 <= key <= 127
                or not 0 <= value <= 127
            ):
                raise ValueError("Invalid MIDI time or value.")
            if not (
                status == 128
                or status == 144
                and value > 0
                and tick < END
                or status == 176
                and key == 64
            ):
                raise ValueError("Expected note on, note off or sustain pedal.")
            if status == 144:
                held.add(key)
            elif status == 128:
                held.discard(key)
            else:
                pedal = value
            previous = tick
        if held or pedal >= 64:
            raise ValueError(
                "The layer must release its notes and pedal at the loop end."
            )
        if not any(e[1] == 144 for e in events):
            raise ValueError("The layer contains no notes.")
    return take


def sounding(events):
    """Bake pedal into XPJ note durations. Preserve the original CC stream in MIDI."""
    held, ringing, notes = {}, {}, []
    pedal = False

    def finish(active, key, tick):
        if key in active:
            start, velocity = active.pop(key)
            notes.append((start, max(1, tick - start), key, velocity))

    for tick, status, key, value in events:
        if status == 176:
            pedal = value >= 64
            if not pedal:
                for k in list(ringing):
                    finish(ringing, k, tick)
        elif status == 144:
            finish(held, key, tick)
            finish(ringing, key, tick)
            held[key] = (tick, value)
        elif key in held:
            if pedal:
                ringing[key] = held.pop(key)
            else:
                finish(held, key, tick)
    for active in (held, ringing):
        for key in list(active):
            finish(active, key, END)
    return sorted(notes)


def export(take, project, output, instruments):
    validate(take, instruments)
    # Pick a meter-preserving length for free-time material. Short pickups may
    # need trailing silence at the maximum supported MPC tempo.
    seconds = take["seconds"]
    bars = min(
        range(1, 151), key=lambda n: (not 20 <= 240 * n / seconds <= 300, abs(n - 4))
    )
    if seconds < 0.8:
        bars = 1
    bpm = max(20, min(300, 240 * bars / seconds))
    ticks = round(seconds * bpm * 960 / 60)
    length = bars * 3840

    def scale(t):
        return min(length, round(t * ticks / END))

    master = xpj.load(project)
    data = master.data
    seq = data["sequences"][0]["value"]
    rows = seq["trackClipMaps"][0]
    template = next(
        e for row in rows for e in row["value"]["eventList"]["events"] if e["type"] == 3
    )
    clips = {r["key"]: r["value"] for r in rows}
    for clip in clips.values():
        clip["eventList"]["events"] = []
        clip["endPulses"] = clip["loopEndPulses"] = length
    seq.update(
        name=take["name"],
        bpm=bpm,
        lengthBars=bars,
        loopEndBar=bars,
        lengthPulses=length,
        loopEndPulses=length,
    )
    data["masterTempo"] = bpm

    def chunk(raw):
        return b"MTrk" + struct.pack(">I", len(raw)) + raw

    tempo = round(60_000_000 / bpm).to_bytes(3, "big")
    chunks = [
        chunk(
            b"\0\xff\x51\x03"
            + tempo
            + b"\0\xff\x58\x04\x04\x02\x18\x08"
            + variable_length(length)
            + b"\xff\x2f\0"
        )
    ]
    for i, layer in enumerate(take["layers"]):
        name = layer["track"]
        for start, duration, key, velocity in sounding(layer["events"]):
            event = deepcopy(template)
            pos = min(length - 1, scale(start))
            event.update(time=pos, channel=0)
            event["note"].update(
                note=key,
                length=min(length - pos, max(1, scale(start + duration) - pos)),
                velocity=velocity / 127,
            )
            clips[name]["eventList"]["events"].append(event)
        label = f"{i + 1} {name}".encode()
        raw = bytearray(b"\0\xff\x03" + variable_length(len(label)) + label)
        raw.extend(
            bytes([0, 255, 33, 1, i // 16])
        )  # MIDI port per group of sixteen layers
        prev = 0
        for tick, status, key, value in layer["events"]:
            pos = scale(tick)
            raw.extend(
                variable_length(pos - prev) + bytes([status | (i % 16), key, value])
            )
            prev = pos
        raw.extend(variable_length(length - prev) + b"\xff\x2f\0")
        chunks.append(chunk(raw))
    for clip in clips.values():
        clip["eventList"]["events"].sort(key=lambda e: e["time"])
    header = "\n".join(vars(master.header).values()) + "\n"
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output) as tmp:
        folder = Path(tmp)
        title = (
            "".join(c for c in take["name"] if c.isalnum() or c in " -_").strip()
            or "My idea"
        )
        (folder / (title + ".xpj")).write_bytes(
            gzip.compress((header + json.dumps(master.document)).encode(), mtime=0)
        )
        (folder / (title + ".mid")).write_bytes(
            b"MThd" + struct.pack(">IHHH", 6, 1, len(chunks), 960) + b"".join(chunks)
        )
        (folder / "take.json").write_text(json.dumps(take))
        companion = project.with_name(project.stem + "_[ProjectData]").resolve()
        dest_samples = folder / (title + "_[ProjectData]")
        dest_samples.mkdir()
        for row in data["samples"]:
            filename = row["path"]
            src = (companion / filename).resolve()
            if (
                not filename
                or Path(filename).name != filename
                or src.parent != companion
            ):
                raise ValueError(f"Expected a local ProjectData sample: {filename}")
            shutil.copyfile(src, dest_samples / filename)
        if xpj.load(folder / (title + ".xpj")).data != data:
            raise ValueError("Project failed reload.")
        for i in range(1, 10000):
            dest = output / (title if i == 1 else f"{title} {i}")
            try:
                publish_directory(folder, dest)
            except FileExistsError:
                continue
            return dest
        raise ValueError("Choose a new idea name.")


def serve(project, output, port, open_browser):
    instruments, samples = catalog(project)

    class Handler(BaseHTTPRequestHandler):
        def send(self, status, data, kind):
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def local(self):
            return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

        def do_GET(self):
            if not self.local():
                return self.send_error(403)
            path = urlsplit(self.path).path
            if path in ("/", "/capture.js", "/studio.js"):
                asset = ASSETS / ("index.html" if path == "/" else path[1:])
                return self.send(
                    200,
                    asset.read_bytes(),
                    "text/html" if path == "/" else "application/javascript",
                )
            if path == "/catalog":
                return self.send(
                    200, json.dumps(instruments).encode(), "application/json"
                )
            if (
                path.startswith("/sample/")
                and path[8:].isascii()
                and path[8:].isdigit()
            ):
                idx = int(path[8:])
                if idx < len(samples):
                    return self.send(200, samples[idx].read_bytes(), "audio/wav")
            self.send_error(404)

        def do_POST(self):
            if (
                not self.local()
                or self.headers.get("Origin") != "http://" + self.headers["Host"]
            ):
                return self.send_error(403)
            if self.path not in ("/validate", "/export"):
                return self.send_error(404)
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 4_000_000:
                    raise ValueError("Invalid take size.")
                take = validate(json.loads(self.rfile.read(size)), instruments)
                result = (
                    str(export(take, project, output, instruments))
                    if self.path == "/export"
                    else "ok"
                )
                self.send(200, json.dumps(result).encode(), "application/json")
            except (ValueError, OSError, KeyError) as error:
                self.send(400, str(error).encode(), "text/plain")

    with ThreadingHTTPServer(("127.0.0.1", port), Handler) as server:
        url = f"http://127.0.0.1:{server.server_port}/"
        print(url, flush=True)
        if open_browser:
            webbrowser.open(url)
        server.serve_forever()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--project",
        type=Path,
        default=Path(
            "work/Playable Scratchpad/Projects/Playable Scratchpad/02 Four Bar Jam.xpj"
        ),
        help="four-bar Scratchpad demo with its ProjectData folder",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=Path("work/Kept Ideas"),
        help="new projects are saved under this folder",
    )
    p.add_argument("--port", type=int, default=8737)
    p.add_argument(
        "--open", action="store_true", help="open the studio in your browser"
    )
    args = p.parse_args(argv)
    if not args.project.is_file():
        p.error(f"cannot find demo XPJ: {args.project}")
    try:
        serve(args.project.resolve(), args.output.resolve(), args.port, args.open)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
