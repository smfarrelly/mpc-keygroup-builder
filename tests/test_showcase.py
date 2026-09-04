import json
import tempfile
import unittest
from importlib import resources
from pathlib import Path

from mpc_keygroup_builder.midi_groove import parse_midi
from mpc_keygroup_builder.showcase import RECIPE_FILES, build_showcase


class ShowcaseTests(unittest.TestCase):
    def test_builds_three_complete_compositions_with_deferred_hardware_status(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "showcase"
            report = build_showcase(output)
            self.assertEqual(report["software_status"], "pass")
            self.assertEqual(report["hardware_status"], "deferred")
            self.assertEqual([item["id"] for item in report["compositions"]], [
                "dusty", "ambient", "electro"
            ])
            self.assertEqual(len({item["digest"] for item in report["compositions"]}), 3)
            self.assertTrue((output / "Instrument/FG Portable Cross Kit.xpm").is_file())
            for item in report["compositions"]:
                root = output / "Compositions" / item["id"]
                self.assertEqual(
                    sorted(path.stem for path in (root / "Sequences").glob("*.mid")),
                    ["breakdown", "build", "main", "main-b", "outro"],
                )
                source, events = parse_midi(root / "idea.mid")
                self.assertEqual((source.midi_format, source.tracks, source.ppq), (1, 5, 480))
                self.assertTrue(events)
                self.assertEqual({event.channel for event in events}, {1, 2, 3, 10})
            checklist = (output / "HARDWARE_CHECKLIST.md").read_text(encoding="utf-8")
            self.assertEqual(checklist.count("Verdict: [ ] pass"), 3)
            self.assertIn("hardware-pending", checklist)
            with self.assertRaises(FileExistsError):
                build_showcase(output)

    def test_same_specs_produce_identical_portable_bundle_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "one"
            second = root / "two"
            build_showcase(first)
            build_showcase(second)
            self.assertEqual(
                (first / "checksums.json").read_bytes(),
                (second / "checksums.json").read_bytes(),
            )
            rendered = "\n".join(
                path.read_text(encoding="utf-8")
                for path in first.rglob("*")
                if path.is_file() and path.suffix in {".json", ".md", ".toml", ".txt"}
            )
            self.assertNotIn(str(first), rendered)
            self.assertNotIn(".staging-", rendered)

    def test_packaged_showcase_recipes_match_repository_sources(self):
        repository = Path(__file__).resolve().parents[1] / "recipes"
        packaged = resources.files("mpc_keygroup_builder.data.showcase_recipes")
        for relative in RECIPE_FILES:
            with self.subTest(recipe=relative):
                self.assertEqual(
                    packaged.joinpath(relative).read_text(encoding="utf-8"),
                    (repository / relative).read_text(encoding="utf-8"),
                )


if __name__ == "__main__":
    unittest.main()
