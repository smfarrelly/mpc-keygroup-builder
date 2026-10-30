"""Dry source-region comparisons, without claiming an MPC conversion."""
import argparse
import hashlib
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
            samples, decoded_rate = read_pcm_mono(sample)
            if len(samples) != frames or decoded_rate != rate:
                raise ValueError(f"zone {index} WAV is truncated or changed during preview")
            trimmed, start, end = trim_sample(samples, zone.get('samplestart'), zone.get('sampleend'))
            full_name, trim_name = f'{index:02d}-full.wav', f'{index:02d}-region.wav'
            for name, audio in ((full_name, samples), (trim_name, trimmed)):
                write_wav(stage / name, resample(audio[:rate * 3], rate, 0))
            records.append(dict(zone=index, sample=str(sample.relative_to(source_root)),
                                sample_sha256=hashlib.sha256(sample.read_bytes()).hexdigest(),
                                start=start, end=end, source_frames=frames,
                                full_preview=full_name, region_preview=trim_name,
                                source_settings={key: zone.get(key) for key in
                                                 ('rootkey', 'detune', 'volume', 'panorama',
                                                  'sustain_loop', 'release_loop', 'warped')}))
        report = dict(preset=str(preset.relative_to(source_root)), limitations=LIMITATIONS, zones=records)
        (stage / 'comparison.json').write_text(json.dumps(report, indent=2) + '\n')
        (stage / 'README.txt').write_text(
            'SOURCE REGION COMPARISON\n\n' + LIMITATIONS + '\n\n'
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
