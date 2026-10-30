"""Dry source-region comparisons, without claiming an MPC conversion."""
import argparse
import hashlib
from html import escape
from io import BytesIO
import json
from pathlib import Path
import tempfile
import wave

from . import ableton
from .ableton_wave import infer_pack_root
from .audition import read_pcm_mono, trim_sample, write_wav, resample
from .publication import publish_directory

LIMITATIONS = (
    "Unpitched mono source excerpts, capped at three seconds, with equal fixed gain. "
    "No loops, detune, envelopes, effects, warp, or MPC behavior are rendered. "
    "These are comparison audio files, not converted instruments or hardware passes."
)


def review_html(report: dict) -> str:
    cards = []
    for zone in report['zones']:
        full, region = escape(zone['full_preview'], quote=True), escape(zone['region_preview'], quote=True)
        cards.append(f'''<section aria-labelledby="zone-{zone['zone']}">
<h2 id="zone-{zone['zone']}">Zone {zone['zone']}</h2>
<p class="sample">{escape(zone['sample'])}</p>
<p>Selected source frames: <strong>{zone['start']}–{zone['end']}</strong> inclusive,
from {zone['source_frames']} total frames.</p>
<div class="pair"><div><h3>From WAV beginning</h3>
<audio controls preload="none" aria-label="Zone {zone['zone']} from WAV beginning" src="{full}"></audio>
<p><a href="{full}">Open full-start excerpt</a></p></div>
<div><h3>From selected region</h3>
<audio controls preload="none" aria-label="Zone {zone['zone']} selected region" src="{region}"></audio>
<p><a href="{region}">Open region excerpt</a></p></div></div>
<details><summary>Original settings omitted from playback</summary>
<pre>{escape(json.dumps(zone['source_settings'], indent=2))}</pre></details></section>''')
    return '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Source region comparison</title><style>
body{font:17px/1.5 system-ui,sans-serif;background:#f4f5f7;color:#17202a;margin:0}
main{max-width:960px;margin:auto;padding:24px}h1,h2,h3{line-height:1.2}
section,.notice{background:white;border:1px solid #bac2cc;border-radius:10px;padding:20px;margin:20px 0}
.notice{border-left:6px solid #705000}.pair{display:grid;grid-template-columns:1fr 1fr;gap:24px}
audio{width:100%}a{color:#164c99}pre,.sample{overflow-wrap:anywhere;white-space:pre-wrap}
summary{cursor:pointer}details{margin-top:16px}h3{font-size:1rem}
@media(max-width:640px){.pair{grid-template-columns:1fr}main{padding:12px}}
</style><main><h1>Compare the source region</h1><p>''' + escape(report['preset']) + '''</p>
<div class="notice"><strong>Reference audio — not an MPC instrument</strong><p>''' + escape(report['limitations']) + '''</p></div>
<p>Play one excerpt, pause it, then play the other at the same volume. Listen for
the attack that is removed or changed. Keep this folder together for offline playback.</p>
''' + ''.join(cards) + '''<p><a href="comparison.json">Inspect complete comparison metadata</a></p>
<p>Generated audio may contain licensed samples. Keep these comparisons private.</p></main></html>'''


def compare(preset: Path, source_root: Path, output: Path) -> dict:
    source_root = source_root.resolve(strict=True)
    preset = preset.resolve(strict=True)
    output = output.absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"choose a new output folder: {output}")
    if not preset.is_relative_to(source_root):
        raise ValueError("preset must be inside the selected source root")
    if output.resolve().is_relative_to(source_root):
        raise ValueError("output must be outside the source library")
    inspected = ableton.inspect(preset)
    zones = [z for z in inspected.get('zones', []) if z.get('isactive') is not False]
    if not 1 <= len(zones) <= 16:
        raise ValueError("choose a preset with 1..16 active zones for a focused comparison")
    pack = infer_pack_root(preset, source_root, inspected).resolve()
    prepared = []
    for index, zone in enumerate(zones, 1):
        sample_info = zone.get('sample')
        reference = sample_info.get('relative_path') if isinstance(sample_info, dict) else None
        if not isinstance(reference, str) or not reference:
            raise ValueError(f"zone {index} has no relative sample path")
        sample = (pack / reference).resolve(strict=True)
        if not sample.is_relative_to(pack) or not sample.is_relative_to(source_root):
            raise ValueError(f"zone {index} sample escapes the source library")
        if sample.suffix.lower() != '.wav' or sample.stat().st_size > 32 * 1024 * 1024:
            raise ValueError(f"zone {index} requires a WAV no larger than 32 MiB")
        with wave.open(str(sample)) as stream:
            frames, rate = stream.getnframes(), stream.getframerate()
            if not 1 <= frames <= 2_000_000:
                raise ValueError(f"zone {index} exceeds the 2,000,000-frame preview limit")
        prepared.append((index, zone, sample, frames, rate))
    output.parent.mkdir(parents=True, exist_ok=True)
    records = []
    with tempfile.TemporaryDirectory(prefix='.source-regions-', dir=output.parent) as temporary:
        stage = Path(temporary)
        for index, zone, sample, frames, rate in prepared:
            with sample.open('rb') as stream:
                snapshot = stream.read(32 * 1024 * 1024 + 1)
            if len(snapshot) > 32 * 1024 * 1024:
                raise ValueError(f"zone {index} WAV grew beyond the 32 MiB preview limit")
            with wave.open(BytesIO(snapshot), 'rb') as stream:
                if stream.getnframes() != frames or stream.getframerate() != rate:
                    raise ValueError(f"zone {index} WAV changed before preview decoding")
            samples, decoded_rate = read_pcm_mono(BytesIO(snapshot))
            if len(samples) != frames or decoded_rate != rate:
                raise ValueError(f"zone {index} WAV is truncated or changed during preview")
            trimmed, start, end = trim_sample(samples, zone.get('samplestart'), zone.get('sampleend'))
            full_name, trim_name = f'{index:02d}-full.wav', f'{index:02d}-region.wav'
            for name, audio in ((full_name, samples), (trim_name, trimmed)):
                write_wav(stage / name, resample(audio[:rate * 3], rate, 0))
            records.append(dict(zone=index, sample=str(sample.relative_to(source_root)),
                                sample_sha256=hashlib.sha256(snapshot).hexdigest(),
                                start=start, end=end, source_frames=frames,
                                full_preview=full_name, region_preview=trim_name,
                                source_settings={key: zone.get(key) for key in
                                                 ('rootkey', 'detune', 'volume', 'panorama',
                                                  'sustain_loop', 'release_loop', 'warped')}))
        report = dict(preset=str(preset.relative_to(source_root)), limitations=LIMITATIONS, zones=records)
        (stage / 'comparison.json').write_text(json.dumps(report, indent=2) + '\n')
        (stage / 'review.html').write_text(review_html(report), encoding='utf-8')
        (stage / 'README.txt').write_text(
            'SOURCE REGION COMPARISON\n\n' + LIMITATIONS + '\n\n'
            'Open review.html for paired audio players and region details.\n'
            'For each numbered zone, compare full.wav with region.wav at the same volume.\n'
            'Read comparison.json for the original region and omitted settings.\n'
        )
        publish_directory(stage, output)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('preset', type=Path)
    parser.add_argument('--source-root', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path, help='new comparison folder outside the source library')
    args = parser.parse_args(argv)
    report = compare(args.preset, args.source_root, args.output)
    print(f"Wrote {len(report['zones'])} source-region pairs: {args.output}")
    print(LIMITATIONS)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
