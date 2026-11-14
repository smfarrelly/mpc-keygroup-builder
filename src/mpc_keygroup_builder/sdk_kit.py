"""Sample individual notes of a trusted native SDK instrument into a portable drum kit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
import tomllib
import wave

from . import drum_builder, sdk_params, sdk_review
from .bundle_verify import sha256, verify_bundle
from .publication import publish_directory
from .testing import test_program
from .wave_io import inspect_pcm_file


def load_kit(path: Path) -> tuple[drum_builder.DrumManifest, dict, dict[int, int]]:
    manifest = drum_builder.load_manifest(path)
    with path.open("rb") as stream:
        data = tomllib.load(stream)
    if data.get("schema_version") != 1 or "extends" in data or manifest.sources:
        raise ValueError("SDK kit requires schema_version 1 with each pad declared in this recipe")
    if not all(isinstance(data.get(k), str) and data[k].strip() for k in ("plugin", "vendor")) or type(data.get("uid_int")) is not int:
        raise ValueError("SDK kit requires plugin, vendor and integer uid_int")
    notes = {}
    filenames = set()
    for row in data["pads"]:
        note, name = row.get("note"), row.get("sample")
        if type(row["pad"]) is not int or type(note) is not int or not 0 <= note <= 127:
            raise ValueError(f"pad {row['pad']}: note must be a MIDI number from 0 to 127")
        if not isinstance(name, str) or not name.lower().endswith(".wav"):
            raise ValueError(f"pad {row['pad']}: provide a single WAV basename")
        drum_builder.validate_program_name(name)
        if name.casefold() in filenames:
            raise ValueError(f"pad {row['pad']}: duplicate sample filename {name}")
        filenames.add(name.casefold())
        notes[row["pad"]] = note
    return manifest, {key: data[key] for key in ("plugin", "vendor", "uid_int")}, notes


def trim_hit(source: Path, destination: Path) -> dict:
    """Remove exact digital silence in whole stereo frames without changing the hit."""
    info = inspect_pcm_file(source)
    if (info["sample_rate"], info["channels"], info["sample_width_bytes"], info["frames"]) != (44100, 2, 2, 88200):
        raise ValueError("expected a complete two-second stereo PCM16 simulator render")
    with wave.open(str(source), "rb") as stream:
        data = stream.readframes(info["frames"])
    start = (len(data) - len(data.lstrip(b"\0"))) // 4
    stop = (len(data.rstrip(b"\0")) + 3) // 4
    if start >= stop:
        raise ValueError(f"silent render for {destination.name}; check the requested MIDI note")
    with wave.open(str(destination), "wb") as stream:
        stream.setparams((2, 2, 44100, stop - start, "NONE", ""))
        stream.writeframes(data[start * 4:stop * 4])
    return {"render_pcm_sha256": info["pcm_sha256"], "first_frame": start,
            "frames": stop - start, "reaches_render_end": stop == info["frames"]}


def build(recipe: Path, native: Path, host: Path, output: Path) -> Path:
    recipe_hash = sha256(recipe)
    manifest, expected, notes = load_kit(recipe)
    native, host = (p.expanduser().resolve(strict=True) for p in (native, host))
    output = output.expanduser().absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"choose a new kit folder: {output}")
    hashes = {"native_sha256": sha256(native), "host_sha256": sha256(host), "recipe_sha256": recipe_hash}
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".sdk-kit-") as scratch:
        root = Path(scratch)
        dump = sdk_review.run_host(host, native, ["dump"], 60)
        if dump.returncode:
            raise ValueError(f"host_sim dump failed: {dump.stderr[-600:]}")
        params = root / "params.json"
        params.write_text(dump.stdout, encoding="utf-8")
        plugin = sdk_params.read_dump(params)
        actual = {"plugin": plugin["name"], "vendor": plugin["vendor"], "uid_int": plugin["uidInt"]}
        if actual != expected or not plugin["isInstrument"]:
            raise ValueError(f"expected SDK instrument {expected}, found {actual} (instrument={plugin['isInstrument']})")
        samples = root / "samples"
        samples.mkdir()
        pads = []
        for pad in manifest.pads:
            wav = root / "render.wav"
            note = notes[pad.pad]
            run = sdk_review.run_host(host, native, ["test", "--playing", "--notes", str(note),
                                      "--seconds", "2", "--sr", "44100", "--wav", str(wav)], 60)
            result = sdk_review.simulator_result(run)
            if result["status"] != "pass":
                raise ValueError(f"pad {pad.pad} note {note}: simulator {result['status']}: {(run.stdout + run.stderr)[-800:]}")
            if not wav.is_file() or wav.is_symlink():
                raise ValueError(f"pad {pad.pad}: simulator did not write render.wav")
            timing = trim_hit(wav, samples / pad.sample)
            wav.unlink()
            pads.append({"pad": pad.pad, "source_note": note, "sample": pad.sample,
                         "mute_group": pad.mute_group, "color_category": pad.color_category, **timing})
        template = root / "template.xpm"
        drum_builder.write_drum_template(template)
        with tempfile.TemporaryDirectory(dir=output.parent, prefix=".sdk-kit-publish-") as staging:
            folder = Path(staging)
            program = drum_builder.build_drum_program(manifest, template, samples, folder)
            simulation = test_program(program, folder)
            if simulation.verdict != "pass":
                raise ValueError(f"generated Drum Program failed simulation: {simulation.issues}")
            if any(sha256(path) != hashes[key] for path, key in
                   ((native, "native_sha256"), (host, "host_sha256"), (recipe, "recipe_sha256"))):
                raise ValueError("kit source changed during rendering; retry with stable files")
            result = {"schema_version": 1, "kind": "mpc-sdk-sampled-kit", **actual, **hashes,
                      "program": program.name, "pads": pads, "software_status": "pass", "hardware_status": "untested"}
            (folder / "kit.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            checksums = {p.name: sha256(p) for p in sorted(folder.iterdir())}
            (folder / "checksums.json").write_text(json.dumps(checksums, indent=2) + "\n", encoding="utf-8")
            verify_bundle(folder)
            publish_directory(folder, output)
    return output / program.name


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recipe", type=Path, help="TOML declaring plugin identity, MIDI notes and physical pads")
    parser.add_argument("native", type=Path, help="trusted desktop SDK instrument build")
    parser.add_argument("--host-sim", required=True, type=Path, help="trusted local Akai simulator executable")
    parser.add_argument("--output", required=True, type=Path, help="new folder for the XPM, WAVs and receipt")
    args = parser.parse_args(argv)
    program = build(args.recipe, args.native, args.host_sim, args.output)
    print(f"Drum Program: {program}\nSoftware checks passed · hardware untested")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
