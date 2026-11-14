import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import wave
import xml.etree.ElementTree as ET

from mpc_keygroup_builder import bundle_verify, sdk_kit


ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT / "midi/sdk-kits/drum-synth.toml"


class SDKKitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.native = self.root / "drum.so"
        self.native.write_bytes(b"native")
        self.host = self.root / "sim"
        self.host.write_bytes(b"host")
        self.output = self.root / "kit"
        self.dump = dict(name="Drum Synth", vendor="MPC SDK Examples", uid="MxDr", uidInt=1299727474,
                         version=1, isInstrument=True, numInputs=0, numOutputs=4, numPrograms=1, params=[])
        self.silent = False

    def simulate(self, host, native, args, timeout):
        if args == ["dump"]:
            return subprocess.CompletedProcess([], 0, json.dumps(self.dump), "")
        data = bytearray(4 * 88200)
        if not self.silent:
            data[4410 * 4 + 1] = 20
            data[4415 * 4 + 2] = 1
        with wave.open(args[args.index("--wav") + 1], "wb") as stream:
            stream.setparams((2, 2, 44100, 88200, "NONE", ""))
            stream.writeframes(data)
        return subprocess.CompletedProcess([], 0, "Result: PASS (15 passed, 0 warnings, 0 failures)", "")

    def build(self):
        with patch.object(sdk_kit.sdk_review, "run_host", side_effect=self.simulate):
            return sdk_kit.build(RECIPE, self.native, self.host, self.output)

    def test_portable_kit_frames_colors_chokes_and_checksums(self):
        program = self.build()
        data = json.loads((self.output / "kit.json").read_text())
        self.assertEqual(len(data["pads"]), 8)
        self.assertEqual(data["hardware_status"], "untested")
        self.assertEqual([r["source_note"] for r in data["pads"]], list(range(36, 44)))
        for row in data["pads"]:
            self.assertEqual((row["first_frame"], row["frames"]), (4410, 6))
            with wave.open(str(self.output / row["sample"])) as wav:
                pcm = wav.readframes(6)
                self.assertEqual((pcm[1], pcm[-2]), (20, 1))
        instrument = ET.parse(program).find("./Program/Instruments/Instrument[@number='4']")
        self.assertEqual(instrument.findtext("MuteGroup"), "1")
        self.assertEqual(instrument.findtext("./Layers/Layer/SampleFile"), "Closed Hat.wav")
        colors = json.loads(ET.parse(program).findtext("./Program/ProgramPads"))["ProgramPads"]["pads"]
        self.assertNotEqual(colors["value0"], colors["value1"])
        self.assertEqual(bundle_verify.verify_bundle(self.output)["verified_files"], 10)
        with self.assertRaises(FileExistsError):
            self.build()

    def test_wrong_plugin_and_silent_note_leave_no_output(self):
        self.dump["isInstrument"] = False
        with self.assertRaisesRegex(ValueError, "expected SDK instrument"):
            self.build()
        self.dump["isInstrument"] = True
        self.silent = True
        with self.assertRaisesRegex(ValueError, "silent render"):
            self.build()
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.root.glob(".sdk-kit-*")))

    def test_bad_recipe_rejected_before_host_execution(self):
        for old, new in [('note = 36', 'note = true'), ('Kick.wav', '../Kick.wav'), ('Kick.wav', 'Snare.wav')]:
            recipe = self.root / "kit.toml"
            recipe.write_text(RECIPE.read_text().replace(old, new))
            with self.subTest(new=new), self.assertRaises(ValueError):
                sdk_kit.load_kit(recipe)
