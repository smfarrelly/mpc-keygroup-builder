"""Assemble a private, self-contained Scratchpad from the owner's known-good captures."""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

import audio
from projects import build_projects
from controls import worksheet
from listening import previews
from mpc_keygroup_builder import pad_recorder, sdk_package
from mpc_keygroup_builder.publication import publish_directory


def build(args):
    output = pad_recorder._new_folder(args.output)
    packages = {}
    with TemporaryDirectory(dir=output.parent) as stage, TemporaryDirectory() as tmp:
        folder, scratch = Path(stage), Path(tmp)
        probe = audio.compile_probe(args.sdk, scratch)
        for plugin in ("PocketLayers", "BloomKeys", "BeatCatch"):
            build_dir = audio.HERE.parent / plugin / "build"
            (package,) = build_dir.glob("* - VST - *")
            dest = folder / "VST2 Plugins" / package.name
            shutil.copytree(package, dest)
            if plugin == "PocketLayers":
                content = dest
                layout = audio.pack(args.layered, dest / "Content/kit.bin")
            packages[plugin] = [
                sdk_package.inspect(dest, arch, build_dir / "params.json")
                for arch in ("arm32", "arm64")
            ]
            (native,) = (build_dir / "native").glob("*.so")
            result = subprocess.run(
                [
                    str(args.sdk / ".sdk-tools/host_sim"),
                    str(native),
                    "test",
                    "--notes",
                    "36",
                    "--playing",
                ],
                check=True,
                capture_output=True,
                text=True,
                env=dict(os.environ, MPC_PLUGIN_FOLDER=str(dest)),
            )
            (folder / (plugin + " simulator.txt")).write_text(
                result.stdout + result.stderr
            )
        worksheet(folder)
        projects = build_projects(
            probe, scratch, content, layout, args.master, args.jam, args.boot, folder
        )
        listening = previews(probe, scratch, content, args.vinyl, args.layered, folder)
        shutil.copyfile(audio.HERE / "index.html", folder / "index.html")
        report = {
            "packages": packages,
            "projects": projects,
            "drum_comparison": listening,
            "hardware": "untested",
        }
        (folder / "build.json").write_text(json.dumps(report, indent=2) + "\n")
        pad_recorder.receipt(folder)
        publish_directory(folder, output)
    print(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("sdk", "vinyl", "layered", "master", "jam", "boot", "output"):
        parser.add_argument("--" + arg, type=Path, required=True)
    build(parser.parse_args())
