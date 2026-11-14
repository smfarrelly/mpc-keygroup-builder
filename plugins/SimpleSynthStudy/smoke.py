"""Exercise real Simple Synth timing, MIDI export and aligned audio from a drum take."""
import argparse
from array import array
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import wave

from build import build, compile_host
from mpc_keygroup_builder import pad_recorder
from mpc_keygroup_builder.bundle_verify import verify_bundle
from mpc_keygroup_builder.midi_groove import parse_midi

ROOT = Path(__file__).resolve().parents[2]


def check(sdk, kit):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        binary = compile_host(sdk, root)
        def note(preset, velocity, end):
            result = subprocess.check_output([str(binary), preset, "22050", "96"],
                                             input=f"137 {end} 40 {velocity}\n".encode())
            signal = array("h", result)
            if sys.byteorder != "little":
                signal.byteswap()
            assert len(signal) == 22050 and not any(signal[:137]) and any(signal[137:170])
            return signal
        bass = note("Fat Bass", 100, 3000)
        assert bass == note("Fat Bass", 100, 3000)
        assert bass != note("Pluck", 100, 3000)
        assert bass != note("Fat Bass", 60, 3000)
        held = note("Fat Bass", 100, 14000)
        assert bass[:3000] == held[:3000] and bass[3000:] != held[3000:]
        layout, _ = pad_recorder.bank_data(kit, "A")
        take = pad_recorder.initial_take(layout, 103, 1)
        take["events"] = [dict(tick=53, duration_ticks=60, pad=layout["pads"][0]["pad"], velocity=40)]
        path = root / "take.json"
        path.write_text(json.dumps(take))
        page = build(kit, path, ROOT / "recipes/harmony/dusty-dorian.toml", sdk, root / "sketch")
        folder = page.parent
        verify_bundle(folder)
        assert json.loads((folder / "performance.take.json").read_text()) == take
        report = json.loads((folder / "sketch.json").read_text())
        assert report["bars"] == 4 and report["frames"] == round(16 * 60 / 103 * 44100)
        assert all(0 < peak < 32767 for peak in report["pcm16_absolute_peaks"].values())
        source, combined = parse_midi(folder / "Sketch.mid")
        assert source.tracks == 4
        for track, name in enumerate(("Drums", "Bass", "Chords"), 2):
            _, events = parse_midi(folder / (name + ".mid"))
            expected = [(e.tick, e.channel, e.note, e.velocity) for e in combined if e.track == track]
            assert expected == [(e.tick, e.channel, e.note, e.velocity) for e in events]
            if name == "Drums":
                assert [e.tick for e in events] == [53 + bar * 1920 for bar in range(4)]
            with wave.open(str(folder / (name + ".wav"))) as w:
                assert w.getnframes() == report["frames"]
        print("Verified 137-frame onset, note release, velocity, presets, repeated off-grid take, aligned stems and exported MIDI.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sdk", type=Path)
    parser.add_argument("kit", type=Path)
    args = parser.parse_args()
    check(args.sdk, args.kit)
