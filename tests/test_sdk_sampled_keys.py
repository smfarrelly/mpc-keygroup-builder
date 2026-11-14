import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

from mpc_keygroup_builder.bundle_verify import verify_bundle
from mpc_keygroup_builder.cli import read_xpm
from tests import test_workflow

STUDY = Path(__file__).resolve().parents[1] / "plugins/SimpleSynthStudy"


def load_sampler():
    with patch.dict(sys.modules), patch.object(sys, "path", [str(STUDY), *sys.path]):
        spec = importlib.util.spec_from_file_location("sample_keys", STUDY / "sample_keys.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


class SampledKeysTests(unittest.TestCase):
    def setUp(self):
        self.sampler = load_sampler()

    def test_tail_cleanup_preserves_attack_fades_endpoint_and_rejects_silence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "root.wav"
            for audible in (True, False):
                with wave.open(str(path), "wb") as w:
                    w.setparams((1, 2, 44100, 0, "NONE", ""))
                    w.writeframes((b"\x25\x01" if audible else b"\0\0") * 300 + b"\0\0" * 100)
                if not audible:
                    with self.assertRaisesRegex(ValueError, "silent"):
                        self.sampler.finish_sample(path)
                else:
                    self.assertEqual(self.sampler.finish_sample(path), 300)
                    with wave.open(str(path)) as w:
                        pcm = w.readframes(300)
                        self.assertEqual(pcm[:2], b"\x25\x01")
                        self.assertEqual(pcm[-2:], b"\0\0")

    @unittest.skipUnless(os.environ.get("MPC_TEST_SDK"), "needs a local Akai SDK checkout")
    def test_real_sdk_roots_cover_keyboard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            template = root / "template.xpm"
            test_workflow.WorkflowTests.write_template(template)
            page = self.sampler.build(Path(os.environ["MPC_TEST_SDK"]), template, root / "set", ["Pluck"])
            report = json.loads((page.parent / "instruments.json").read_text())["instruments"][0]
            self.assertEqual((report["playable_notes"], report["dead_cells"], report["stacked_cells"]), (128, 0, 0))
            self.assertEqual(report["notes"], list(range(12, 121, 6)))
            program = page.parent / report["name"] / report["program"]
            data = read_xpm(program)[1]["data"]
            layers = [i["layersv"][0] for i in data["drum"]["instruments"][1:]]
            self.assertEqual([l["rootNote"] for l in layers], report["notes"])
            self.assertTrue(all(l["keyTrackEnable"] and not l["loop"] for l in layers))
            self.assertEqual(verify_bundle(page.parent)["verified_files"], 24)
            with self.assertRaises(FileExistsError):
                self.sampler.build(Path(os.environ["MPC_TEST_SDK"]), template, page.parent, ["Pluck"])
