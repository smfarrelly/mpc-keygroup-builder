"""Run the offline renderer against a generated mono impulse and verify the pair."""

from array import array
from pathlib import Path
import subprocess
import sys
import tempfile
import wave

from mpc_keygroup_builder.bundle_verify import verify_bundle


def pcm(path):
    with wave.open(str(path), "rb") as stream:
        assert (stream.getnchannels(), stream.getsampwidth(), stream.getframerate()) == (2, 2, 8000)
        data = array("h", stream.readframes(stream.getnframes()))
    if sys.byteorder == "big":
        data.byteswap()
    return data


def main():
    sdk = Path(sys.argv[1]).resolve()
    runner = Path(__file__).resolve().parents[1] / "tools/audition.py"
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "impulse.wav"
        frames = bytearray(16000)
        frames[0:2] = (8192).to_bytes(2, "little")
        frames[8000:8002] = (4096).to_bytes(2, "little")
        with wave.open(str(source), "wb") as stream:
            stream.setparams((1, 2, 8000, 8000, "NONE", ""))
            stream.writeframes(frames)
        out = root / "comparison"
        command = [sys.executable, str(runner), str(source), "--sdk", str(sdk), "--bpm", "120",
                   "--beat", "1", "--also-beat", "1.95", "--length", ".25", "--tail", "1", "--output", str(out)]
        subprocess.run(command, check=True)
        dry, wet = pcm(out / "Dry.wav"), pcm(out / "Loop Throw.wav")
        assert len(dry) == len(wet) == 32000
        assert dry[:2] == wet[:2] == array("h", [8192, 8192])
        assert wet[:4000] == dry[:4000] and wet[4000] > 100 and wet[4000] == wet[4001]
        assert dry[8000:8002] == array("h", [4096, 4096])
        # Beat two captures the second impulse. Compare with a single-window render.
        single = root / "single"
        baseline = command.copy()
        index = baseline.index("--also-beat")
        del baseline[index:index + 2]
        baseline[-1] = str(single)
        subprocess.run(baseline, check=True)
        single_wet = pcm(single / "Loop Throw.wav")
        assert wet[12000] > single_wet[12000] + 100
        assert wet[:12000] == single_wet[:12000]
        assert (out / "index.html").is_file()
        assert verify_bundle(out)["verified_files"] == 4
        assert subprocess.run(command, capture_output=True).returncode == 2
        assert verify_bundle(out)["verified_files"] == 4
    print("Passed mono-to-stereo expansion, dry comparison, echo timing, tail length and overwrite checks.")


if __name__ == "__main__":
    main()
