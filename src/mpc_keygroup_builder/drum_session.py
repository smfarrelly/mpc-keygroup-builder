"""Build an offline listening session with MIDI and rendered loops for one drum kit."""

from __future__ import annotations

import argparse
from html import escape
import json
from pathlib import Path
import tempfile

from . import ideas, pattern_audio
from .bundle_verify import sha256, verify_bundle
from .model import from_xpm
from .publication import publish_directory


def _page(report: dict) -> str:
    cards = []
    for item in report["patterns"]:
        base = item["folder"]
        cards.append(f'''<section><h2>{escape(item["name"])}</h2>
<p>{item["bars"]} bars · {item["events"]} hits · seed {item["seed"]}</p>
<audio controls loop preload="none" aria-label="{escape(item["name"], quote=True)} loop" src="{base}/listen.wav"></audio>
<div><a href="{base}/pattern.mid" download>Save MIDI</a> · <a href="{base}/pattern.json">Pattern</a>
 · <a href="{base}/listen.json">Sample timings</a></div></section>''')
    return f'''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(report["program"])} · Drum session</title>
<style>
:root {{font:17px/1.45 "DM Sans",system-ui,sans-serif;background:#181b19;color:#f4f0e6}}
main {{max-width:65rem;margin:auto;padding:clamp(1rem,4vw,3rem)}}
h1,h2 {{line-height:1.1;letter-spacing:-.035em}} h1 {{font-size:clamp(2rem,6vw,4rem);margin:.4em 0}}
.grid {{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,18rem),1fr));gap:1rem}}
section {{background:#25322c;padding:1.2rem;border:1px solid #546456;border-radius:.5rem}}
h2 {{margin:0}} audio {{width:100%;margin:.4rem 0 .9rem}} a {{color:#c9e8b1}} p {{color:#d5d6cb}}
</style><main><h1>{escape(report["program"])}</h1>
<p>{report["tempo"]:g} BPM · Dry drum loops</p><p>Play a loop to audition the pattern. Save its MIDI to use with this kit.</p>
<div class="grid">{"".join(cards)}</div></main>
<script>document.addEventListener("play", event => {{
  for (const player of document.querySelectorAll("audio")) if (player !== event.target) player.pause();
}}, true);</script></html>'''


def build(program: Path, recipes: list[Path], output: Path, *, tempo: float = 96, seed: int = 37) -> dict:
    output = output.expanduser().absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"choose a new drum session folder: {output}")
    if not recipes:
        raise ValueError("choose at least one drum recipe")
    program = program.expanduser().resolve(strict=True)
    original = sha256(program)
    model = from_xpm(program)
    if model.kind != "drum" or model.source_format != "xml":
        raise ValueError("choose an XML Drum Program for a listening session")
    report = {"kind": "mpc-drum-listening-session", "schema_version": 1, "program": model.name,
              "program_sha256": original, "tempo": tempo, "patterns": [], "hardware_status": "untested"}
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".drum-session-") as tmp:
        stage = Path(tmp)
        for index, path in enumerate(recipes, 1):
            source = sha256(path)
            recipe = ideas.load_recipe(path)
            try:
                idea = ideas.generate_idea(recipe, model, seed=seed, tempo=tempo)
            except ValueError as exc:
                raise ValueError(f"{path}: {exc}") from exc
            folder = stage / f"pattern-{index:02d}"
            pattern, _ = ideas.write_outputs(folder / "pattern", [path, program], json.dumps(idea.to_dict(), indent=2) + "\n",
                                             ideas.render_midi(idea), force=False)
            preview = pattern_audio.render_pattern(program, pattern, folder / "listen.wav")
            if sha256(path) != source:
                raise ValueError(f"recipe changed during rendering: {path}")
            report["patterns"].append({"folder": folder.name, "name": recipe.name, "recipe": recipe.id,
                                       "recipe_sha256": source, "seed": seed, "bars": idea.bars,
                                       "events": len(idea.events), "frames": preview["frames"]})
        if sha256(program) != original:
            raise ValueError("drum program changed during rendering")
        (stage / "session.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        (stage / "index.html").write_text(_page(report), encoding="utf-8")
        checksums = {p.relative_to(stage).as_posix(): sha256(p) for p in sorted(stage.rglob("*")) if p.is_file()}
        (stage / "checksums.json").write_text(json.dumps(checksums, indent=2) + "\n", encoding="utf-8")
        verify_bundle(stage)
        publish_directory(stage, output)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("program", type=Path, help="XML Drum Program with accessible WAV samples")
    parser.add_argument("recipes", nargs="+", type=Path, help="one or more mpc-drum-idea pattern recipes")
    parser.add_argument("--output", type=Path, required=True, help="new session folder")
    parser.add_argument("--tempo", type=float, default=96, help="beats per minute, default 96")
    parser.add_argument("--seed", type=int, default=37, help="reproducible pattern variation, default 37")
    args = parser.parse_args(argv)
    report = build(args.program, args.recipes, args.output, tempo=args.tempo, seed=args.seed)
    print(f'{len(report["patterns"])} loops · {args.tempo:g} BPM\nOpen {(args.output / "index.html").resolve()}')
    return 0
