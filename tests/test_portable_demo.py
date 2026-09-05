import json
import tempfile
import unittest
import wave
from pathlib import Path

from mpc_keygroup_builder.portable_demo import build_demo, verify_demo


class PortableDemoTests(unittest.TestCase):
    def test_builds_complete_redistributable_workflow(self):
        repository = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "portable"
            report = build_demo(output, repository / "recipes")
            self.assertEqual(report["cross_kit_simulation"], "pass")
            self.assertEqual(report["generated_samples"], 16)
            self.assertEqual(len(report["arrangement_sections"]), 5)
            self.assertTrue((output / "Cross Kit/FG Portable Cross Kit.xpm").is_file())
            self.assertTrue((output / "Creative MIDI/portable-demo.mid").is_file())
            self.assertTrue((output / "Arrangements/main-b.mid").is_file())
            checksums = json.loads((output / "checksums.json").read_text())
            self.assertIn("Cross Kit/FG Portable Cross Kit.xpm", checksums)
            selection = json.loads((output / "Selection/selection.json").read_text())
            self.assertFalse(any(".staging-" in str(value) for value in selection.values()))
            idea = json.loads((output / "Creative MIDI/portable-demo.json").read_text())
            self.assertEqual(
                idea["drum_program_file"],
                "Cross Kit/FG Portable Cross Kit.xpm",
            )
            self.assertTrue((output / "LICENSE-GENERATED-AUDIO.txt").is_file())
            wavs = sorted((output / "Synthetic Audio").glob("*.wav"))
            self.assertEqual(len(wavs), 16)
            with wave.open(str(wavs[0]), "rb") as stream:
                self.assertEqual(stream.getframerate(), 44_100)
                self.assertGreater(stream.getnframes(), 0)
            with self.assertRaises(FileExistsError):
                build_demo(output, repository / "recipes")

    def test_output_is_reproducible_across_destination_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "first"
            second = root / "nested" / "second"
            build_demo(first, None)
            build_demo(second, None)
            first_files = {
                path.relative_to(first).as_posix(): path.read_bytes()
                for path in first.rglob("*")
                if path.is_file()
            }
            second_files = {
                path.relative_to(second).as_posix(): path.read_bytes()
                for path in second.rglob("*")
                if path.is_file()
            }
            self.assertEqual(first_files, second_files)

    def test_verifies_moved_demo_and_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / "original"
            build_demo(original, None)
            moved = root / "moved"
            original.rename(moved)

            report = verify_demo(moved)
            self.assertGreater(report["verified_files"], 20)
            self.assertEqual(report["cross_kit_simulation"], "pass")
            self.assertEqual(report["hardware_status"], "deferred")

            sample = next((moved / "Synthetic Audio").glob("*.wav"))
            sample.write_bytes(sample.read_bytes() + b"tampered")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                verify_demo(moved)

    def test_verifier_rejects_unrecorded_and_unsafe_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "portable"
            build_demo(output, None)
            (output / "unexpected.txt").write_text("not in the receipt")
            with self.assertRaisesRegex(ValueError, "unrecorded files"):
                verify_demo(output)

            (output / "unexpected.txt").unlink()
            receipt_path = output / "checksums.json"
            receipt = json.loads(receipt_path.read_text())
            receipt["../outside"] = "0" * 64
            receipt_path.write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError, "unsafe.*path"):
                verify_demo(output)

    def test_verifier_rejects_broken_and_receipt_symbolic_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "portable"
            build_demo(output, None)
            broken = output / "unrecorded-broken-link"
            broken.symlink_to(output / "missing-target")
            with self.assertRaisesRegex(ValueError, "symbolic links"):
                verify_demo(output)

            broken.unlink()
            receipt = output / "checksums.json"
            external_receipt = root / "external-checksums.json"
            receipt.replace(external_receipt)
            receipt.symlink_to(external_receipt)
            with self.assertRaisesRegex(ValueError, "receipt.*symbolic link"):
                verify_demo(output)

    def test_builds_with_packaged_recipe_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "installed-style-demo"
            report = build_demo(output, None)
            self.assertEqual(report["cross_kit_simulation"], "pass")
            self.assertTrue((output / "Recipes/drums/dusty-pocket.toml").is_file())
            self.assertTrue((output / "Recipes/harmony/dusty-dorian.toml").is_file())
            self.assertTrue((output / "Recipes/melody/dusty-answer.toml").is_file())


if __name__ == "__main__":
    unittest.main()
