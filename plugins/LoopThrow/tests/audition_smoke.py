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
        with wave.open(str(source), "wb") as stream:
            stream.setparams((1, 2, 8000, 8000, "NONE", ""))
            stream.writeframes(frames)
        out = root / "comparison"
        command = [sys.executable, str(runner), str(source), "--sdk", str(sdk), "--bpm", "120",
                   "--beat", "1", "--length", ".25", "--tail", "1", "--output", str(out)]
        subprocess.run(command, check=True)
        dry, wet = pcm(out / "Dry.wav"), pcm(out / "Loop Throw.wav")
        assert len(dry) == len(wet) == 32000
        assert dry[:2] == wet[:2] == array("h", [8192, 8192])
        assert wet[:4000] == dry[:4000] and wet[4000] > 100 and wet[4000] == wet[4001]
        assert sum(map(abs, dry[2:])) == 0
        assert verify_bundle(out)["verified_files"] == 3
        assert subprocess.run(command, capture_output=True).returncode == 2
        assert verify_bundle(out)["verified_files"] == 3
    print("Passed mono-to-stereo expansion, dry comparison, echo timing, tail length and overwrite checks.")


if __name__ == "__main__":
    main()
